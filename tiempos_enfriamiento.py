"""Tiempos del modo sinusoidal exacto y cruces de umbral del solver.

El enfriamiento no tiene un instante único: se debe indicar la tolerancia
respecto de la temperatura del borde. Sin fuentes y con Dirichlet uniforme.
"""
import numpy as np


def tiempo_exacto(amplitud, alpha, longitudes, tolerancia):
    if not 0 < tolerancia < amplitud:
        raise ValueError("Se requiere 0 < tolerancia < amplitud.")
    lambda_ = sum((np.pi / L)**2 for L in longitudes)
    return float(np.log(amplitud/tolerancia)/(alpha*lambda_))


def resumen_enfriamiento(tiempos, temperaturas, borde, amplitud, alpha, longitudes,
                         tolerancia=.1):
    desviacion = np.max(np.abs(temperaturas-borde).reshape(len(tiempos), -1), axis=1)
    umbrales = sorted(set([20., 15., 10., 1., float(tolerancia)]), reverse=True)
    filas = []
    for umbral in umbrales:
        if umbral >= amplitud:
            continue
        indices = np.flatnonzero(desviacion <= umbral)
        # Primer fotograma que cumple: cota superior; no interpolar como si fuera exacta.
        filas.append({"diferencia_maxima_con_borde_C": umbral,
                      "temperatura_maxima_objetivo_C": borde+umbral,
                      "tiempo_exacto_dias": tiempo_exacto(amplitud, alpha, longitudes, umbral)/86400,
                      "primer_fotograma_que_cumple_dias":
                          float(tiempos[indices[0]]/86400) if len(indices) else None})
    return {"criterio": f"max(abs(T-Tb)) <= {tolerancia:g} °C",
            "tiempo_exacto_dias": tiempo_exacto(amplitud, alpha, longitudes, tolerancia)/86400,
            "umbrales": filas}
