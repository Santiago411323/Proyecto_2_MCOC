"""Agrega identidad y propiedades didacticas conservando geometria y GUID."""
from pathlib import Path
import ifcopenshell
import ifcopenshell.api
import ifcopenshell.util.element


def completar(modelo):
    objetos = sorted(modelo.by_type("IfcBuildingElementProxy"), key=lambda o: o.Name)
    for i, objeto in enumerate(objetos, start=1):
        objeto.Name = f"Vertida_{i:02d}"
        psets = ifcopenshell.util.element.get_psets(objeto)
        existente = psets.get("Pset_HormigonMasivo")
        pset = modelo.by_id(existente["id"]) if existente else ifcopenshell.api.run(
            "pset.add_pset", modelo, product=objeto, name="Pset_HormigonMasivo")
        ifcopenshell.api.run("pset.edit_pset", modelo, pset=pset, properties={
            "VertidaID": i, "TipoHormigon": "M1", "MaterialID": 1,
            "InicioPlanificado": f"2026-10-{21+i-1:02d}T08:00:00-03:00",
            "Inicio_h": float((i-1)*24), "TemperaturaColocacion_C": 18.,
            "Moldaje": "Panel de practica", "Aislacion": "Sin definir - ejemplo docente",
            "RetiroMoldaje_h": 72.,
        })
    return modelo


if __name__ == "__main__":
    ruta = Path(__file__).resolve().parent / "modelo_e02.ifc"
    completar(ifcopenshell.open(str(ruta))).write(str(ruta))
    print("Modelo actualizado; parametros de ejemplo, no plan constructivo validado.")
