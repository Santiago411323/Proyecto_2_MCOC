"""Casos matematicos de verificacion, sin hidratacion ni clima real."""
import numpy as np
from termico_cartesiano import TermicoCartesiano


def sinusoidal(dimension, n, fraccion_dt=.7):
    bordes = {f"{'xyz'[eje]}{s}":{"tipo":"dirichlet","temperatura_C":20.}
              for eje in range(dimension) for s in ("-", "+")}
    modelo = TermicoCartesiano((n,)*dimension, (1.,)*dimension, k=1., rho=1., cp=1., bordes=bordes)
    perfil = np.prod([np.sin(np.pi*x) for x in modelo.coordenadas], axis=0)
    inicial = 20+10*perfil
    duracion = .03
    dt = fraccion_dt*modelo.dt_max
    r = modelo.resolver(inicial, duracion, dt, guardar_en=[duracion/2])
    exacta = 20+10*perfil*np.exp(-dimension*np.pi**2*duracion)
    return modelo, r, exacta, dt
