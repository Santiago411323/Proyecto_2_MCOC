import csv
import json

import pytest

from hpc import monte_carlo as mc


def test_sample_is_repeatable_and_uses_stable_child_streams(tmp_path):
    first, second = tmp_path / "a", tmp_path / "b"
    mc.sample(first, 5, 17)
    original = (first / "muestras.json").read_bytes()
    mc.sample(first, 5, 17)
    assert (first / "muestras.json").read_bytes() == original
    mc.sample(second, 8, 17)
    assert mc.read_manifest(first)["samples"] == mc.read_manifest(second)["samples"][:5]
    with pytest.raises(ValueError, match="Lote distinto"):
        mc.sample(first, 5, 99)


def test_aggregation_rejects_missing_rows_and_counts_union_once(tmp_path):
    mc.sample(tmp_path, 3, 11)
    manifest = mc.read_manifest(tmp_path)
    tag = mc.digest(manifest)
    rows = manifest["samples"]
    # Deliberately out of execution order. A tie at either limit is allowed.
    for i, hot, delta in [(2, 71., 21.), (0, 70., 20.)]:
        mc.save(mc.result_path(tmp_path, rows[i]), mc.encode(dict(
            rows[i], manifest=tag, Tmax_C=hot, Delta_C=delta, horizon_captured=True)))
    with pytest.raises(FileNotFoundError):
        mc.aggregate(tmp_path)
    row = dict(rows[1], manifest=tag, Tmax_C=69., Delta_C=21., horizon_captured=True)
    mc.save(mc.result_path(tmp_path, rows[1]), mc.encode(row))
    mc.aggregate(tmp_path)
    with (tmp_path / "resultados.csv").open(encoding="utf-8-sig") as f:
        values = list(csv.DictReader(f))
    assert [float(r["Pf_N"]) for r in values] == [0., .5, 2/3]
    assert json.loads((tmp_path / "resumen.json").read_bytes())["fallas"] == 2
    row["manifest"] = "otro"
    mc.save(mc.result_path(tmp_path, rows[1]), mc.encode(row))
    with pytest.raises(ValueError, match="otro lote"):
        mc.aggregate(tmp_path)
