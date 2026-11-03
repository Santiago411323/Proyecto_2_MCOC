"""Elevación adiabática exponencial por edad; no es una cinética calibrada.

Los parámetros se exigen explícitamente. El integrador usa el incremento exacto
en cada intervalo, evitando sustituir una fuente variable por su valor inicial.
La interfaz de incremento/tasa permite reemplazar este modelo posteriormente.
"""
from dataclasses import dataclass
import math
import numpy as np


@dataclass(frozen=True)
class AdiabaticaExponencial:
    theta_inf_C: float
    tau_s: float

    def __post_init__(self):
        if not math.isfinite(self.theta_inf_C) or self.theta_inf_C<0 or not math.isfinite(self.tau_s) or self.tau_s<=0:
            raise ValueError('theta_inf no negativo y tau positivo, ambos finitos.')

    def elevacion(self,edad_s):
        if not math.isfinite(edad_s) or edad_s<0:raise ValueError('Edad no negativa y finita.')
        return self.theta_inf_C*(-math.expm1(-edad_s/self.tau_s))

    def tasa_C_s(self,edad_s):
        self.elevacion(edad_s)
        return self.theta_inf_C/self.tau_s*math.exp(-edad_s/self.tau_s)

    def incremento(self,a,b):
        self.elevacion(a)
        if not math.isfinite(b) or b<a:raise ValueError('Intervalo de edad inválido.')
        return self.theta_inf_C*math.exp(-a/self.tau_s)*(-math.expm1(-(b-a)/self.tau_s))

    def fuente_media(self,a,b,rho,cp):
        if b<=a:raise ValueError('La duración debe ser positiva.')
        return np.asarray(rho)*np.asarray(cp)*self.incremento(a,b)/(b-a)
