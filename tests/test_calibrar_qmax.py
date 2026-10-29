import numpy as np
import pytest
from calibrar_qmax import pulso, integral_pulso, evolucion, calibrar
from termico_cartesiano import TermicoCartesiano


def test_pulso_y_calor_integrado():
    np.testing.assert_allclose(pulso(np.array([-1, 0, 2, 4, 5]), 4), [0, 0, 1, 0, 0], atol=1e-14)
    assert float(integral_pulso(10, 4)) == pytest.approx(2)


def test_pulso_adiabatico_respeta_calor_total_y_balance():
    m = TermicoCartesiano((4, 3), (1., 1.), k=1, rho=2, cp=3)
    r = evolucion(m, periodo_s=1, duracion_s=1.5, dt_s=.01, qmax=12, inicial=20)
    # Calor total por volumen = Qmax*T/2 = 6 J/m3; rho*cp=6 J/(m3 K).
    np.testing.assert_allclose(r['T_final'], 21, atol=1e-11)
    assert np.max(np.abs(r['residual_energia_J'])) < 1e-10


def test_calibracion_superposicion_y_paso_mas_fino():
    r = calibrar(86400, dimension=3, forma=(6, 4, 2))
    m = r['modelo']
    directo = evolucion(m, 86400, r['tiempo_s'][-1], r['dt_s'], qmax=r['qmax_W_m3'])
    assert 20+directo['centro_C'].max() == pytest.approx(70, abs=1e-8)
    fino = calibrar(86400, dimension=3, forma=(6, 4, 2), fraccion_dt=.35)
    assert abs(fino['qmax_W_m3']/r['qmax_W_m3']-1) < .01
