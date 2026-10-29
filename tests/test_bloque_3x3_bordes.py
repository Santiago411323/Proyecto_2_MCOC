import numpy as np
import pytest
from bloque_3x3_bordes import condiciones, modelo_bloque, calibrar_bordes


def test_robin_normal_exterior_enfria_y_beta_cero_aisla():
    m = modelo_bloque(condiciones('robin', beta_m_inv=2), (5, 5, 2))
    assert m.energia(m.paso(50., .5*m.dt_max)) < m.energia(50.)
    aislado = modelo_bloque(condiciones('robin', beta_m_inv=0), (5, 5, 2))
    np.testing.assert_allclose(aislado.paso(50., .5*aislado.dt_max), 50.)
    assert m.bordes['z+']['h_W_m2K'] == 4.


def test_calibracion_adiabatica_exacta_pulso_dos_dias():
    periodo = 2*86400
    r = calibrar_bordes(condiciones('neumann'), periodo, 3*86400, forma=(4, 4, 2))
    # DeltaT=Qmax*P/(2*rho*cp) -> Qmax=1250 W/m3.
    assert r['qmax_W_m3'] == pytest.approx(1250., rel=1e-10)
    np.testing.assert_allclose(r['centro_C'][r['tiempo_s'] >= periodo], 70., atol=1e-9)


def test_dirichlet_30_inicial_20_incluye_calentamiento_por_borde():
    r = calibrar_bordes(condiciones('dirichlet', 30), 86400, 4*86400, forma=(4, 4, 2))
    assert r['base_C'][0] == 20.
    assert r['base_C'][-1] > 29.
    assert r['centro_C'].max() == pytest.approx(70., abs=1e-8)
