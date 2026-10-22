from pathlib import Path
import ifcopenshell
import ifcopenshell.api
import pytest
from leer_ifc import leer_elementos, comparar

MODELO = Path(__file__).resolve().parents[1] / "modelo_e02.ifc"


def test_modelo_tiene_tres_bloques_identificables():
    elementos = leer_elementos(MODELO)
    assert len(elementos) == 3
    assert {e["nombre"] for e in elementos.values()} == {"Vertida_01", "Vertida_02", "Vertida_03"}
    assert {e["propiedades"]["VertidaID"] for e in elementos.values()} == {1, 2, 3}


def test_detecta_cambio_real_en_ifc_guardado(tmp_path):
    antes = leer_elementos(MODELO)
    modelo = ifcopenshell.open(str(MODELO))
    objeto = next(e for e in modelo.by_type("IfcElement") if e.Name == "Vertida_01")
    guid = objeto.GlobalId
    objeto.Name = "Vertida_01_modificada"
    ruta = tmp_path / "modificado.ifc"
    modelo.write(str(ruta))
    cambios = comparar(antes, leer_elementos(ruta))
    assert len(cambios) == 1
    assert cambios[0]["GlobalId"] == guid
    assert cambios[0]["despues"]["nombre"] == "Vertida_01_modificada"


def test_detecta_propiedad_constructiva_guardada(tmp_path):
    antes = leer_elementos(MODELO)
    modelo = ifcopenshell.open(str(MODELO))
    objeto = next(e for e in modelo.by_type("IfcElement") if e.Name == "Vertida_01")
    propiedades = ifcopenshell.util.element.get_psets(objeto)["Pset_HormigonMasivo"]
    ifcopenshell.api.run("pset.edit_pset", modelo, pset=modelo.by_id(propiedades["id"]),
                        properties={"TemperaturaColocacion_C": 16.})
    ruta = tmp_path / "propiedad.ifc"
    modelo.write(str(ruta))
    cambios = comparar(antes, leer_elementos(ruta))
    assert len(cambios) == 1
    assert cambios[0]["despues"]["propiedades"]["TemperaturaColocacion_C"] == 16.


def test_detecta_agrandar_base_xy_guardada(tmp_path):
    antes = leer_elementos(MODELO)
    modelo = ifcopenshell.open(str(MODELO))
    base = next(e for e in modelo.by_type("IfcElement") if e.Name == "Vertida_01")
    listas = [e for e in modelo.traverse(base.Representation) if e.is_a("IfcCartesianPointList3D")]
    assert listas
    for lista in listas:
        lista.CoordList = [(x*1.1, y*1.1, z) for x, y, z in lista.CoordList]
    ruta = tmp_path / "base_agrandada.ifc"
    modelo.write(str(ruta))
    cambios = comparar(antes, leer_elementos(ruta))
    assert len(cambios) == 1
    assert cambios[0]["GlobalId"] == base.GlobalId
    geometria = cambios[0]["despues"]["geometria"]
    assert geometria["dimensiones_m"] == {"X":19.8,"Y":19.8,"Z":1.1}
    assert geometria["volumen_m3"] == pytest.approx(antes[base.GlobalId]["geometria"]["volumen_m3"]*1.21,abs=1e-4)


def test_reabrir_sin_editar_no_genera_cambios(tmp_path):
    modelo = ifcopenshell.open(str(MODELO))
    ruta = tmp_path / "sin_editar.ifc"
    modelo.write(str(ruta))
    assert comparar(leer_elementos(MODELO), leer_elementos(ruta)) == []
