from pathlib import Path
import numpy as np
import pytest
from voxelizar import cargar_geometria, voxelizar, dentro_malla

MODELO = Path(__file__).resolve().parents[1]/"modelo_e02.ifc"


def test_geometria_y_clasificacion_fuera_dentro():
    solidos=cargar_geometria(MODELO)
    assert sum(s["volumen"] for s in solidos) == pytest.approx(487.0695,abs=.01)
    s=next(s for s in solidos if s["VertidaID"] == 1)
    np.testing.assert_array_equal(dentro_malla(np.array([[0.,0.,.55],[10.,0.,.55]]),s["triangulos"]),[True,False])


def test_identidad_volumen_y_activacion():
    solidos=cargar_geometria(MODELO)
    r=voxelizar(solidos,.8,0.)
    assert abs(r["V_h"]-r["V_geom"])/r["V_geom"] < .2
    assert set(np.unique(r["vertida_id"])) == {0,1,2,3}
    assert np.all(r["vertida_id"][r["active"]] == 1)
    assert np.all(r["T_inicial_C"][r["active"]] == 18.)
    assert not voxelizar(solidos,.8,-1.)["active"].any()
    final=voxelizar(solidos,.8,48.)
    np.testing.assert_array_equal(final["active"],final["occupied"])


def test_tres_resoluciones_y_error_de_volumen():
    solidos=cargar_geometria(MODELO)
    errores=[voxelizar(solidos,h)["error_volumen"] for h in (.8,.5,.25)]
    # Una frontera staircase no garantiza error monotono: importa la alineacion.
    assert all(e < .05 for e in errores)


def test_superposicion_es_rechazada():
    solidos=cargar_geometria(MODELO)
    with pytest.raises(ValueError,match="superpuestos"):
        voxelizar([solidos[0],solidos[0]],.5)
