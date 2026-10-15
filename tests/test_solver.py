import numpy as np
import pytest
from solver_1d import simular


def test_uniforme_con_bordes_a_la_misma_temperatura():
    r = simular(amplitud=0.)
    np.testing.assert_allclose(r["temperatura"], 20., atol=1e-12)


def test_solucion_exacta_y_principio_del_maximo():
    r = simular()
    assert r["error_max"] < .05
    assert np.min(r["temperatura"]) >= 20.
    assert np.max(r["temperatura"]) <= 60.


def test_refinamiento_reduce_error():
    grueso = simular(dx=.1, dt=1200.)
    fino = simular(dx=.05, dt=300.)
    assert fino["error_max"] < grueso["error_max"] / 3.


def test_rechaza_paso_inestable():
    with pytest.raises(ValueError, match="inestable"):
        simular(dx=.025, dt=600.)


def test_ultimo_paso_alcanza_duracion():
    r = simular(duracion=1000.)
    assert r["tiempos"][-1] == 1000.


def test_rechaza_grilla_incompatible():
    with pytest.raises(ValueError, match="dividir"):
        simular(dx=.3)
