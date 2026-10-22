"""Lee elementos IFC y compara snapshots por GlobalId."""
import argparse
import json
from pathlib import Path
import ifcopenshell
import ifcopenshell.geom
import ifcopenshell.util.element
import numpy as np


def medir_geometria(objeto, settings):
    if not objeto.Representation:
        return None
    forma = ifcopenshell.geom.create_shape(settings, objeto)
    vertices = np.asarray(forma.geometry.verts).reshape(-1, 3)
    caras = np.asarray(forma.geometry.faces).reshape(-1, 3)
    triangulos = vertices[caras] - vertices.mean(axis=0)
    volumen = abs(np.einsum("ij,ij->i", triangulos[:, 0],
        np.cross(triangulos[:, 1], triangulos[:, 2])).sum()) / 6
    area = np.linalg.norm(np.cross(triangulos[:, 1]-triangulos[:, 0],
        triangulos[:, 2]-triangulos[:, 0]), axis=1).sum()/2
    minimo, maximo = vertices.min(axis=0), vertices.max(axis=0)
    # IfcOpenShell convierte a SI y aplica placements; redondear evita ruido numerico.
    return {"dimensiones_m": dict(zip("XYZ", np.round(maximo-minimo, 6).tolist())),
            "minimo_m": np.round(minimo, 6).tolist(),
            "maximo_m": np.round(maximo, 6).tolist(),
            "volumen_m3": round(float(volumen), 5), "area_m2": round(float(area), 5)}


def leer_elementos(ruta):
    modelo = ifcopenshell.open(str(ruta))
    settings = ifcopenshell.geom.settings()
    settings.set(settings.USE_WORLD_COORDS, True)
    elementos = {}
    for obj in modelo.by_type("IfcElement"):
        propiedades = ifcopenshell.util.element.get_psets(obj).get("Pset_HormigonMasivo", {}).copy()
        propiedades.pop("id", None)  # ID STEP local: puede cambiar al reexportar el mismo objeto.
        elementos[obj.GlobalId] = {"nombre": obj.Name, "clase": obj.is_a(),
                                  "propiedades": propiedades,
                                  "geometria": medir_geometria(obj, settings)}
    return elementos


def comparar(antes, despues):
    cambios = []
    for guid in sorted(antes.keys() | despues.keys()):
        if antes.get(guid) != despues.get(guid):
            cambios.append({"GlobalId": guid, "antes": antes.get(guid),
                            "despues": despues.get(guid)})
    return cambios


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archivo", nargs="?", type=Path, default=Path("modelo_e02.ifc"))
    parser.add_argument("--guardar", type=Path, help="Guardar snapshot JSON")
    parser.add_argument("--comparar", type=Path, help="Comparar con un snapshot anterior")
    args = parser.parse_args()
    elementos = leer_elementos(args.archivo)
    print(f"Archivo: {args.archivo.resolve()}\nElementos: {len(elementos)}")
    for guid, datos in sorted(elementos.items()):
        print(f"{guid} | {datos['clase']} | {datos['nombre']}")
        print(json.dumps(datos["propiedades"], ensure_ascii=False))
        if datos["geometria"]:
            print("Geometria:", json.dumps(datos["geometria"], ensure_ascii=False))
    if args.comparar:
        antes = json.loads(args.comparar.read_text(encoding="utf-8"))
        cambios = comparar(antes, elementos)
        print(f"\nCambios detectados: {len(cambios)}")
        for cambio in cambios:
            print(f"\nObjeto: {(cambio['despues'] or cambio['antes'])['nombre']} | GUID: {cambio['GlobalId']}")
            for campo in ("nombre", "clase", "propiedades", "geometria"):
                anterior = (cambio["antes"] or {}).get(campo)
                nuevo = (cambio["despues"] or {}).get(campo)
                if anterior != nuevo:
                    print(f"  {campo} ANTES: {json.dumps(anterior, ensure_ascii=False)}")
                    print(f"  {campo} DESPUES: {json.dumps(nuevo, ensure_ascii=False)}")
    if args.guardar:
        args.guardar.parent.mkdir(parents=True, exist_ok=True)
        args.guardar.write_text(json.dumps(elementos, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"Snapshot guardado: {args.guardar}")


if __name__ == "__main__":
    main()
