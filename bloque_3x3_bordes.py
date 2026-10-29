"""Herramientas para comparar bordes en el bloque 3 x 3 x 0.60 m.

Robin usa NORMAL EXTERIOR: dT/dn=-beta*(T-Tamb), beta>=0 [1/m].
No se fija beta ni la distribución de Dirichlet sin especificación del caso.
"""
import numpy as np
from termico_cartesiano import TermicoCartesiano
from calibrar_qmax import evolucion, pulso, integral_pulso, temperatura_centro

LONGITUDES_M = (3., 3., .60)
K_W_MK = 2.
RHO_KG_M3 = 2400.
CP_J_KGK = 900.
CARAS = tuple(f"{e}{s}" for e in "xyz" for s in ("-", "+"))


def condiciones(tipo, temperatura_C=20., beta_m_inv=None):
    if tipo == "dirichlet":
        return {c: {"tipo": "dirichlet", "temperatura_C": temperatura_C} for c in CARAS}
    if tipo == "neumann":
        return {c: {"tipo": "neumann", "flujo_saliente_W_m2": 0.} for c in CARAS}
    if tipo == "robin":
        if beta_m_inv is None or not np.isfinite(beta_m_inv) or beta_m_inv < 0:
            raise ValueError("Especificar beta >=0 [1/m], para normal exterior y signo negativo.")
        # Fourier: q_saliente=-k*dT/dn=k*beta*(T-Tamb)=h*(T-Tamb).
        return {c: {"tipo": "robin", "temperatura_C": temperatura_C,
                    "h_W_m2K": K_W_MK*beta_m_inv} for c in CARAS}
    raise ValueError("Tipo: dirichlet, neumann o robin.")


def modelo_bloque(bordes, forma=(30, 30, 6)):
    return TermicoCartesiano(forma, LONGITUDES_M, k=K_W_MK,
                            rho=RHO_KG_M3, cp=CP_J_KGK, bordes=bordes)


def calibrar_bordes(bordes, periodo_s, duracion_s, inicial_C=20., objetivo_C=70.,
                    forma=(30, 30, 6), fraccion_dt=.7):
    """Calibrar sin suponer que la temperatura inicial coincide con el borde.

Tcentro(t)=B(t)+Qmax*U(t). Se elige el mayor Qmax no negativo que
mantiene el centro <= objetivo durante todo el intervalo simulado.
"""
    if not np.isfinite(inicial_C+objetivo_C) or inicial_C >= objetivo_C:
        raise ValueError("La temperatura inicial debe ser menor que el objetivo.")
    if not 0 < fraccion_dt <= 1:
        raise ValueError("Usar 0 < fraccion_dt <= 1.")
    m = modelo_bloque(bordes, forma)
    homogeneos = {c: {**b, **({"temperatura_C": 0.} if b['tipo'] != 'neumann' else
                             {"flujo_saliente_W_m2": 0.})} for c, b in bordes.items()}
    unidad_m = modelo_bloque(homogeneos, forma)
    dt = min(fraccion_dt*m.dt_max, periodo_s/200.)
    base = evolucion(m, periodo_s, duracion_s, dt, qmax=0., inicial=inicial_C)
    unidad = evolucion(unidad_m, periodo_s, duracion_s, dt, qmax=1., inicial=0.)
    np.testing.assert_array_equal(base['tiempo_s'], unidad['tiempo_s'])
    if np.max(base['centro_C']) >= objetivo_C:
        raise ValueError("Los bordes por sí solos alcanzan el objetivo; no hay calibración positiva.")
    u = unidad['centro_C']
    validos = u > max(float(u.max())*1e-12, np.finfo(float).tiny)
    qmax = float(np.min((objetivo_C-base['centro_C'][validos])/u[validos]))
    centro = base['centro_C']+qmax*u
    i = int(np.argmax(centro))
    # El caso adiabático tiene una meseta: reportar su primer instante,
    # evitando que el redondeo seleccione un día posterior arbitrario.
    cercanos = np.flatnonzero(centro >= centro.max()-1e-8)
    i = int(cercanos[0])
    return {"modelo": m, "tiempo_s": base['tiempo_s'], "base_C": base['centro_C'],
            "respuesta_unidad": u, "centro_C": centro, "qmax_W_m3": qmax,
            "dt_s": dt, "tiempo_pico_s": float(base['tiempo_s'][i]),
            "nota": "Máximo central calibrado dentro del intervalo de simulación."}
