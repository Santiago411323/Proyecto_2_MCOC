import numpy as np
from tiempos_enfriamiento import tiempo_exacto, resumen_enfriamiento


def test_tiempo_enfriamiento_satisface_umbral_y_escala_geometrica():
    alpha = 2/(2400*900)
    t = tiempo_exacto(30, alpha, (4, 2, 1), .1)
    lambda_ = sum((np.pi/L)**2 for L in (4, 2, 1))
    assert np.isclose(30*np.exp(-alpha*lambda_*t), .1)
    assert np.isclose(tiempo_exacto(30, alpha, (8, 4, 2), .1), 4*t)


def test_primer_fotograma_es_cota_no_tiempo_interpolado():
    tiempos = np.array([0., 86400., 172800.])
    T = np.array([[50., 40.], [21., 20.5], [20.05, 20.02]])
    r = resumen_enfriamiento(tiempos, T, 20, 30, 1., (4.,), .1)
    fila = next(f for f in r['umbrales'] if f['diferencia_maxima_con_borde_C'] == .1)
    assert fila['primer_fotograma_que_cumple_dias'] == 2.
