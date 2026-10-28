"""Casos matematicos de verificacion, sin hidratacion ni clima real."""
import numpy as np
from termico_cartesiano import TermicoCartesiano


def sinusoidal(dimension, n, fraccion_dt=.7, *, longitudes=None, T0=20.,
               amplitud=10., alpha=1., rho=1., cp=1., duracion=.03, dt=None):
    if dimension not in (1,2,3): raise ValueError("Dimension debe ser 1, 2 o 3.")
    if not all(np.isfinite(v) for v in (T0,amplitud,alpha,rho,cp,duracion,fraccion_dt)):
        raise ValueError("Parametros finitos requeridos.")
    if min(alpha,rho,cp,fraccion_dt)<=0 or fraccion_dt>1 or duracion<0:
        raise ValueError("alpha, rho, cp positivos; 0<fraccion_dt<=1; duracion>=0.")
    forma=(n,)*dimension if np.isscalar(n) else tuple(n)
    longitudes=(1.,)*dimension if longitudes is None else tuple(longitudes)
    bordes = {f"{'xyz'[eje]}{s}":{"tipo":"dirichlet","temperatura_C":T0}
              for eje in range(dimension) for s in ("-", "+")}
    if len(forma)!=dimension or len(longitudes)!=dimension:
        raise ValueError("Usar una longitud y un numero de celdas por eje.")
    modelo = TermicoCartesiano(forma, longitudes, k=alpha*rho*cp, rho=rho, cp=cp, bordes=bordes)
    perfil = np.prod([np.sin(np.pi*x/L) for x,L in zip(modelo.coordenadas,longitudes)], axis=0)
    inicial = T0+amplitud*perfil
    dt = fraccion_dt*modelo.dt_max if dt is None else dt
    r = modelo.resolver(inicial, duracion, dt, guardar_en=[duracion/2])
    lambda_ = float(np.sum((np.pi/modelo.longitudes)**2))
    exacta = T0+amplitud*perfil*np.exp(-alpha*lambda_*duracion)
    return modelo, r, exacta, dt
