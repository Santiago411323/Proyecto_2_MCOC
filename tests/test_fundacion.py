import json
from pathlib import Path
import numpy as np
import pytest
from voxelizar import cargar_geometria

BASE=Path(__file__).resolve().parents[1]


def test_dimensiones_y_continuidad():
    solidos=cargar_geometria(BASE/"modelo_e02.ifc")
    todos=np.concatenate([s["vertices"] for s in solidos])
    np.testing.assert_allclose(todos.max(axis=0)-todos.min(axis=0),[18.,18.,3.3],atol=1e-6)
    por_id={s["VertidaID"]:s for s in solidos}
    for i in (1,2):
        assert por_id[i]["vertices"][:,2].max() == pytest.approx(por_id[i+1]["vertices"][:,2].min())
    superior=por_id[3]["vertices"]
    assert superior[:,0].max()-superior[:,0].min() == pytest.approx(7.)
    assert superior[:,1].max()-superior[:,1].min() == pytest.approx(7.)


def test_base_octogonal_y_cilindro():
    s=cargar_geometria(BASE/"modelo_e02.ifc")
    c=json.loads((BASE/"geometria_fundacion.json").read_text())
    area=18**2-2*(9-c["semilado_tramo_recto_m"])**2
    assert s[0]["volumen"] == pytest.approx(area*1.1,abs=.001)
    assert s[2]["volumen"] == pytest.approx(np.pi*3.5**2*1.1,rel=.001)
    assert {x["nombre"] for x in s} == {"Vertida_01","Vertida_02","Vertida_03"}
