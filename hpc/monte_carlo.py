"""Monte Carlo reproducible para el plan F02 a 8 °C (local o array Slurm)."""
import argparse
import csv
import hashlib
import json
import math
import os
from concurrent.futures import ThreadPoolExecutor
from importlib.metadata import version
from pathlib import Path
import socket
import sys
import tempfile

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
ENGINE = ROOT / "docs/defensa_grupo9/escenarios_T8"
SOURCES = [f"M{i}_{campaign}" for campaign in ("SS", "22A") for i in range(1, 5)]
CLIMATES = ["OM16", "OM18", "Meteored18"]


def digest(obj):
    return hashlib.sha256(json.dumps(obj, sort_keys=True, allow_nan=False).encode()).hexdigest()


def physics_id():
    files = [ENGINE / "calcular.py", ROOT / "modelo_e02.ifc",
             ROOT / "docs/hielo_f02/refinamiento_xyz/config_T8_96x96x54.json",
             ROOT / "data/hydration/source_terms_fv_tikhonov.txt", Path(__file__).resolve()]
    files += list((ROOT / "therma").glob("*.py"))
    files += [ROOT / f for f in ("comparar_vertidas_pronostico.py", "termico_cartesiano.py",
                                  "voxelizar.py", "panel/exportar_ifc.py")]
    for folder in ("20261118T143552195128Z_ee51ca19", "meteored_20261118_punta_arenas"):
        files += [ROOT / "data/weather" / folder / name for name in ("forecast.json", "metadata.json")]
    # Normalize line endings so Windows/Linux checkouts share the same identity.
    checks = {p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes().replace(b"\r\n", b"\n")).hexdigest() for p in files}
    return digest(checks)


def save(path, data, immutable=False):
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as out:
        tmp = Path(out.name)
        out.write(data)
    try:
        if immutable:
            try:
                os.link(tmp, path)
            except FileExistsError:
                if path.read_bytes() != data:
                    raise ValueError(f"Lote distinto en {path}. Elegir otra carpeta.")
        else:
            os.replace(tmp, path)
    finally:
        tmp.unlink(missing_ok=True)


def encode(obj):
    return json.dumps(obj, ensure_ascii=False, indent=2, allow_nan=False).encode("utf8")


def sample(folder, n, seed):
    if n < 1 or seed < 0:
        raise ValueError("N debe ser positivo y la seed no negativa.")
    rows = []
    for index in range(n):
        seq = np.random.SeedSequence(seed, spawn_key=(index,))
        rng = np.random.Generator(np.random.PCG64(seq))
        rows.append(dict(id=index, spawn_key=[index], source=str(rng.choice(SOURCES)),
                         climate=str(rng.choice(CLIMATES))))
    config = dict(schema=1, seed=seed, rng="PCG64/SeedSequence", model="T8_96x96x54_42d",
                  physics_id=physics_id(), numpy=version("numpy"), sources=SOURCES,
                  climates=CLIMATES, distribution="iid_uniform_product_with_replacement", samples=rows)
    save(folder / "muestras.json", encode(config), immutable=True)
    print(f"{n} muestras, seed {seed}, manifiesto {digest(config)}", flush=True)


def read_manifest(folder):
    return json.loads((folder / "muestras.json").read_bytes())


def result_path(folder, row):
    return folder / "realizaciones" / f"{row['id']:06d}.json"


def checked(path, row, tag):
    data = json.loads(path.read_bytes())
    if data["manifest"] != tag or any(data[k] != v for k, v in row.items()):
        raise ValueError(f"Resultado de otro lote o muestra: {path}")
    if not all(math.isfinite(data[k]) for k in ("Tmax_C", "Delta_C")):
        raise ValueError(f"Métricas no finitas en {path}")
    return data


def run(folder, index, shards, workers):
    m = read_manifest(folder)
    if not (0 <= index < shards <= len(m["samples"])) or workers < 1:
        raise ValueError("Revisar índice, cantidad de tareas y workers.")
    if physics_id() != m["physics_id"] or version("numpy") != m["numpy"]:
        raise ValueError("Cambió el código, los insumos o NumPy desde el muestreo.")
    tag = digest(m)
    pending = []
    for row in m["samples"][index::shards]:
        path = result_path(folder, row)
        if path.exists():
            checked(path, row, tag)
        else:
            pending.append(row)
    if not pending:
        print("Este bloque ya está completo.")
        return
    sys.path.insert(0, str(ENGINE))
    import calcular
    if calcular.NAMES != SOURCES or calcular.CLIMATES != CLIMATES:
        raise ValueError("Catálogos inconsistentes.")

    def execute(row):
        wi = CLIMATES.index(row["climate"])
        si = SOURCES.index(row["source"])
        result = calcular.simulate((wi, si), output_dir=None)
        if result["source"] != row["source"] or result["climate"] != row["climate"]:
            raise ValueError("El solver ejecutó otra combinación.")
        result.update(row, manifest=tag, job=os.environ.get("SLURM_JOB_ID"),
                      task=os.environ.get("SLURM_ARRAY_TASK_ID"), host=socket.gethostname(),
                      numba=version("numba"))
        save(result_path(folder, row), encode(result))
        print(f"Muestra {row['id']} completa", flush=True)

    with ThreadPoolExecutor(max_workers=workers) as pool:
        list(pool.map(execute, pending))


def aggregate(folder):
    import io
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    m = read_manifest(folder)
    tag = digest(m)
    rows = []
    failures = 0
    for row in m["samples"]:
        result = checked(result_path(folder, row), row, tag)
        t_fail = result["Tmax_C"] > 70
        d_fail = result["Delta_C"] > 20
        failures += int(t_fail or d_fail)
        n = len(rows) + 1
        rows.append(dict(N=n, id=row["id"], source=row["source"], climate=row["climate"],
                         Tmax_C=result["Tmax_C"], Delta_C=result["Delta_C"], I_T=int(t_fail),
                         I_Delta=int(d_fail), I_F=int(t_fail or d_fail), fallas_acumuladas=failures,
                         Pf_N=failures/n, horizonte_capturado=result["horizon_captured"]))
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
    writer.writeheader()
    writer.writerows(rows)
    save(folder / "resultados.csv", stream.getvalue().encode("utf-8-sig"))
    fig, ax = plt.subplots(figsize=(7.8, 4.2), layout="constrained")
    ax.plot([r["N"] for r in rows], [100*r["Pf_N"] for r in rows], "o-", label="Frecuencia acumulada")
    ax.axhline(5, color="firebrick", linestyle="--", label="Criterio docente 5 %")
    ax.set(xlabel="Realizaciones en orden de ID", ylabel="Excedencia conjunta estimada [%]",
           title=f"Plan a 8 °C · N={n} · seed {m['seed']}")
    ax.legend()
    image = io.BytesIO()
    fig.savefig(image, format="png", dpi=150)
    plt.close(fig)
    save(folder / "Pf_N.png", image.getvalue())
    summary = dict(N=n, seed=m["seed"], manifest=tag, fallas=failures, Pf=failures/n,
                   horizontes_capturados=sum(r["horizonte_capturado"] for r in rows))
    if failures == 0:
        summary["cota_superior_binomial_unilateral_95"] = -math.expm1(math.log(.05)/n)
    save(folder / "resumen.json", encode(summary))
    print(json.dumps(summary))


if __name__ == "__main__":
    cli = argparse.ArgumentParser(description=__doc__)
    commands = cli.add_subparsers(dest="command", required=True)
    make = commands.add_parser("sample")
    make.add_argument("--n", type=int, required=True)
    make.add_argument("--seed", type=int, required=True)
    batch = commands.add_parser("run")
    batch.add_argument("--index", type=int, default=0)
    batch.add_argument("--shards", type=int, default=1)
    batch.add_argument("--workers", type=int, default=1)
    merge = commands.add_parser("aggregate")
    for cmd in (make, batch, merge):
        cmd.add_argument("--out", type=Path, required=True)
    args = cli.parse_args()
    if args.command == "sample":
        sample(args.out, args.n, args.seed)
    elif args.command == "run":
        run(args.out, args.index, args.shards, args.workers)
    else:
        aggregate(args.out)
