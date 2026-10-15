"""Lee elementos IFC y compara snapshots por GlobalId."""
import argparse
import json
from pathlib import Path
import ifcopenshell


def leer_elementos(ruta):
    modelo = ifcopenshell.open(str(ruta))
    return {obj.GlobalId: {"nombre": obj.Name, "clase": obj.is_a()}
            for obj in modelo.by_type("IfcElement")}


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
    if args.comparar:
        antes = json.loads(args.comparar.read_text(encoding="utf-8"))
        cambios = comparar(antes, elementos)
        print(f"\nCambios detectados: {len(cambios)}")
        for cambio in cambios:
            print(json.dumps(cambio, ensure_ascii=False))
    if args.guardar:
        args.guardar.parent.mkdir(parents=True, exist_ok=True)
        args.guardar.write_text(json.dumps(elementos, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"Snapshot guardado: {args.guardar}")


if __name__ == "__main__":
    main()
