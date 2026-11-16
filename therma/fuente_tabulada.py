"""Fuente Q [W/m³] lineal por tramos, integral exacta y cola explícita."""
import numpy as np


class FuenteTabulada:
    recommended_step_s = 900.

    def __init__(self, config, rho, cp):
        from .fuentes_vigentes import comprobar_fuente
        comprobar_fuente(config)
        self.t = np.asarray(config['time_h'], dtype=float)*3600
        self.q = np.asarray(config['Q_W_m3'], dtype=float)
        if self.t.ndim != 1 or len(self.t)<2 or self.q.shape!=self.t.shape or self.t[0]!=0 or not np.all(np.diff(self.t)>0) or not np.isfinite(self.t).all() or not np.isfinite(self.q).all() or np.any(self.q<0):
            raise ValueError('Curva Q: tiempos crecientes desde cero y fuente finita no negativa.')
        if config.get('tail')!='constant_last' or not config.get('raw_sha256') or not config.get('column'):
            raise ValueError('Declarar cola constant_last, columna y hash original.')
        self.capacity=rho*cp
        self.integral=np.r_[0.,np.cumsum(np.diff(self.t)*(self.q[:-1]+self.q[1:])/2)]

    def energia_volumetrica(self, age):
        if not np.isfinite(age) or age<0:raise ValueError('Edad no negativa y finita.')
        if age>=self.t[-1]:return float(self.integral[-1]+self.q[-1]*(age-self.t[-1]))
        i=max(0,np.searchsorted(self.t,age,side='right')-1)
        dt=age-self.t[i];slope=(self.q[i+1]-self.q[i])/(self.t[i+1]-self.t[i])
        return float(self.integral[i]+self.q[i]*dt+slope*dt*dt/2)

    def tasa_C_s(self,age):
        self.energia_volumetrica(age)
        return float(np.interp(age,self.t,self.q))/self.capacity

    def elevacion(self,age):return self.energia_volumetrica(age)/self.capacity

    def fuente_media(self,a,b,rho,cp):
        if b<=a:raise ValueError('Intervalo de edad positivo requerido.')
        return (self.energia_volumetrica(b)-self.energia_volumetrica(a))/(b-a)
