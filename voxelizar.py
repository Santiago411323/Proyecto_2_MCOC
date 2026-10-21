"""IFC triangulado -> grilla cartesiana por clasificacion del centro (G04).

Usa suma de angulos solidos para mallas cerradas orientadas. No es un solver 3D.
"""
import argparse
import csv
import json
from pathlib import Path
import numpy as np
import ifcopenshell
import ifcopenshell.geom
import ifcopenshell.util.element
import ifcopenshell.util.unit


def dentro_malla(puntos, triangulos):
    """Numero de enrollamiento: interior si |suma de angulos| > 2*pi."""
    resultado = np.zeros(len(puntos), dtype=bool)
    for inicio in range(0, len(puntos), 512):
        p = puntos[inicio:inicio+512, None, :]
        a, b, c = (triangulos[None, :, j, :] - p for j in range(3))
        la, lb, lc = (np.linalg.norm(v, axis=2) for v in (a, b, c))
        numerador = np.einsum("...i,...i->...", a, np.cross(b, c))
        denominador = (la*lb*lc + np.sum(a*b, axis=2)*lc
                       + np.sum(b*c, axis=2)*la + np.sum(c*a, axis=2)*lb)
        angulos = 2*np.arctan2(numerador, denominador)
        resultado[inicio:inicio+512] = np.abs(angulos.sum(axis=1)) > 2*np.pi
    return resultado


def cargar_geometria(ruta):
    modelo = ifcopenshell.open(str(ruta))
    if not np.isclose(ifcopenshell.util.unit.calculate_unit_scale(modelo), 1.):
        raise ValueError("Baseline requiere IFC en metros.")
    settings = ifcopenshell.geom.settings()
    settings.set(settings.USE_WORLD_COORDS, True)
    solidos = []
    for objeto in modelo.by_type("IfcElement"):
        if not objeto.Representation:
            continue
        props = ifcopenshell.util.element.get_psets(objeto).get("Pset_HormigonMasivo", {})
        for campo in ("VertidaID", "MaterialID", "Inicio_h", "TemperaturaColocacion_C"):
            if campo not in props:
                raise ValueError(f"Falta {campo} en {objeto.Name}")
        forma = ifcopenshell.geom.create_shape(settings, objeto)
        vertices = np.array(forma.geometry.verts).reshape(-1, 3)
        caras = np.array(forma.geometry.faces).reshape(-1, 3)
        aristas = np.sort(np.concatenate([caras[:, [0,1]], caras[:, [1,2]], caras[:, [2,0]]]), axis=1)
        _, cuentas = np.unique(aristas, axis=0, return_counts=True)
        if not np.all(cuentas == 2):
            raise ValueError(f"Malla no cerrada: {objeto.Name}")
        triangulos = vertices[caras]
        tri_local = triangulos - vertices.mean(axis=0)
        volumen = abs(np.einsum("ij,ij->i", tri_local[:,0],
            np.cross(tri_local[:,1], tri_local[:,2])).sum())/6
        solidos.append({"guid": objeto.GlobalId, "nombre": objeto.Name, **props,
                        "triangulos": triangulos, "vertices": vertices, "volumen": volumen})
    if not solidos:
        raise ValueError("No hay elementos con geometria.")
    ids = [s["VertidaID"] for s in solidos]
    if len(ids) != len(set(ids)) or min(ids) < 1:
        raise ValueError("VertidaID debe ser positivo y unico por objeto en este baseline.")
    return solidos


def voxelizar(solidos, h, tiempo_h=0.):
    if not np.isfinite(h) or h <= 0 or not np.isfinite(tiempo_h):
        raise ValueError("h debe ser positivo y los parametros finitos.")
    todos = np.concatenate([s["vertices"] for s in solidos])
    origen, extremo = todos.min(axis=0), todos.max(axis=0)
    dimensiones = np.ceil((extremo-origen)/h).astype(int)
    if np.prod(dimensiones.astype(float)) > 2_000_000:
        raise ValueError("Grilla demasiado grande para este baseline (max. 2 millones).")
    ejes = [origen[j] + (np.arange(dimensiones[j])+.5)*h for j in range(3)]
    centros = np.stack(np.meshgrid(*ejes, indexing="ij"), axis=-1).reshape(-1,3)
    vertida = np.zeros(len(centros), dtype=np.int32)
    material = np.zeros_like(vertida)
    inicio = np.full(len(centros), np.inf)
    colocacion = np.full(len(centros), np.nan)
    for solido in solidos:
        dentro = dentro_malla(centros, solido["triangulos"])
        if np.any(dentro & (vertida != 0)):
            raise ValueError("Solidos superpuestos: un centro pertenece a dos vertidas.")
        vertida[dentro] = solido["VertidaID"]
        material[dentro] = solido["MaterialID"]
        inicio[dentro] = solido["Inicio_h"]
        colocacion[dentro] = solido["TemperaturaColocacion_C"]
    ocupado = vertida > 0
    activo = ocupado & (tiempo_h >= inicio)
    volumen_geometrico = sum(s["volumen"] for s in solidos)
    volumen_voxel = int(ocupado.sum())*h**3
    return {"centros": centros.reshape(*dimensiones,3),
            "occupied": ocupado.reshape(dimensiones), "active": activo.reshape(dimensiones),
            "vertida_id": vertida.reshape(dimensiones), "material_id": material.reshape(dimensiones),
            "inicio_h": inicio.reshape(dimensiones),
            "T_colocacion_C": colocacion.reshape(dimensiones),
            "T_inicial_C": np.where(activo, colocacion, np.nan).reshape(dimensiones),
            "h": h, "tiempo_h": tiempo_h, "origen": origen,
            "V_geom": volumen_geometrico, "V_h": volumen_voxel,
            "error_volumen": abs(volumen_voxel-volumen_geometrico)/volumen_geometrico}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("archivo", nargs="?", default="modelo_e02.ifc")
    p.add_argument("--resoluciones", nargs="+", type=float, default=[.7,.4,.2])
    p.add_argument("--tiempo-h", type=float, default=0.)
    p.add_argument("--salida", type=Path, default=Path("resultados/voxeles"))
    args = p.parse_args()
    solidos = cargar_geometria(args.archivo)
    args.salida.mkdir(parents=True, exist_ok=True)
    filas = []
    for h in args.resoluciones:
        r = voxelizar(solidos,h,args.tiempo_h)
        fila = {"h_m": h, "N_ocupado": int(r["occupied"].sum()),
                "N_activo": int(r["active"].sum()), "V_geom_m3": r["V_geom"],
                "V_h_m3": r["V_h"], "error_relativo": r["error_volumen"]}
        filas.append(fila)
        print(json.dumps(fila))
        np.savez_compressed(args.salida/f"grilla_h{h:g}.npz", **r)
    with (args.salida/"convergencia_volumen.csv").open("w",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f,fieldnames=filas[0].keys()); w.writeheader(); w.writerows(filas)
    metadatos = [{k:v for k,v in s.items() if k not in ("vertices","triangulos")} for s in solidos]
    (args.salida/"vertidas.json").write_text(json.dumps(metadatos,indent=2),encoding="utf-8")
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, ax=plt.subplots(figsize=(8,3.5),layout="constrained")
    plano=r["vertida_id"][:,:,0].T
    imagen=ax.imshow(plano,origin="lower",extent=[r["origen"][0],r["origen"][0]+plano.shape[1]*h,
        r["origen"][1],r["origen"][1]+plano.shape[0]*h],interpolation="nearest",vmin=0,vmax=3)
    barra=fig.colorbar(imagen,ax=ax,ticks=[0,1,2,3])
    barra.ax.set_yticklabels(["Exterior","Vertida 01","Vertida 02","Vertida 03"])
    ax.set(xlabel="x [m]",ylabel="y [m]",title=f"IDs de vertida - primer corte z, h={h:g} m")
    fig.savefig(args.salida/"corte_voxeles.png",dpi=160); plt.close(fig)


if __name__ == "__main__":
    main()
