from pathlib import Path
import ifcopenshell
from leer_ifc import leer_elementos, comparar

MODELO = Path(__file__).resolve().parents[1] / "modelo_e02.ifc"


def test_modelo_tiene_tres_bloques_identificables():
    elementos = leer_elementos(MODELO)
    assert len(elementos) == 3
    assert {e["nombre"] for e in elementos.values()} == {"Bloque_A", "Bloque_B", "Bloque_C"}


def test_detecta_cambio_real_en_ifc_guardado(tmp_path):
    antes = leer_elementos(MODELO)
    modelo = ifcopenshell.open(str(MODELO))
    objeto = next(e for e in modelo.by_type("IfcElement") if e.Name == "Bloque_A")
    guid = objeto.GlobalId
    objeto.Name = "Bloque_A_modificado"
    ruta = tmp_path / "modificado.ifc"
    modelo.write(str(ruta))
    cambios = comparar(antes, leer_elementos(ruta))
    assert len(cambios) == 1
    assert cambios[0]["GlobalId"] == guid
    assert cambios[0]["despues"]["nombre"] == "Bloque_A_modificado"
