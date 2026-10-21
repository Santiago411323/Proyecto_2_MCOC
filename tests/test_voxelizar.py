from pathlib import Path
import numpy as np
import pytest
from voxelizar import cargar_geometria, voxelizar, dentro_malla

MODELO = Path(__file__).resolve().parents[1]/"modelo_e02.ifc"


def test_geometria_y_clasificacion_fuera_dentro():
    solidos=cargar_geometria(MODELO)
    assert sum(s["volumen"] for s in solidos) == pytest.approx(24.)
    s=next(s for s in solidos if s["VertidaID"] == 1)
    np.testing.assert_array_equal(dentro_malla(np.array([[1.,1.,1.],[3.,1.,1.]]),s["triangulos"]),[True,False])


def test_identidad_volumen_y_activacion():
    solidos=cargar_geometria(MODELO)
    r=voxelizar(solidos,.4,0.)
    assert r["V_h"] == pytest.approx(24.)
    assert set(np.unique(r["vertida_id"])) == {0,1,2,3}
    assert np.all(r["vertida_id"][r["active"]] == 1)
    assert np.all(r["T_inicial_C"][r["active"]] == 18.)
    assert not voxelizar(solidos,.4,-1.)["active"].any()
    final=voxelizar(solidos,.4,48.)
    np.testing.assert_array_equal(final["active"],final["occupied"])


def test_tres_resoluciones_y_error_de_volumen():
    solidos=cargar_geometria(MODELO)
    errores=[voxelizar(solidos,h)["error_volumen"] for h in (.7,.4,.2)]
    assert errores[0] > errores[1]
    assert errores[2] == pytest.approx(0.,abs=1e-12)


def test_superposicion_es_rechazada():
    solidos=cargar_geometria(MODELO)
    with pytest.raises(ValueError,match="superpuestos"):
        voxelizar([solidos[0],solidos[0]],.5)
