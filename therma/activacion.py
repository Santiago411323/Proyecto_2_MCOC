"""4A: activación conservativa; reutiliza TermicoCartesiano, sin copiar sus ecuaciones.

Al cambiar el dominio se construye una nueva instancia del mismo motor oficial.
Así se regeneran pares, conductancias, fronteras y dt crítico con la máscara real.
La energía sensible se referencia a 0 °C, incluida la que aporta el material nuevo.
"""
import math
import numpy as np
from termico_cartesiano import TermicoCartesiano


class ConstruccionTermica:
    def __init__(self, vertida_ids, longitudes, vertidas, k=2., rho=2400., cp=900., bordes=None, suelo=None):
        raw=np.asarray(vertida_ids)
        if raw.ndim not in (1,2,3) or not np.isfinite(raw).all() or np.any(raw<0) or np.any(raw!=np.floor(raw)):
            raise ValueError('IDs geométricos enteros, no negativos y de 1D a 3D.')
        self.ids=raw.astype(np.int32);self.forma=self.ids.shape;self.longitudes=tuple(longitudes)
        if len(self.longitudes)!=raw.ndim or not np.isfinite(self.longitudes).all() or min(self.longitudes)<=0:
            raise ValueError('Longitudes positivas compatibles.')
        self.dx=np.asarray(longitudes)/self.forma;self.volumen=float(np.prod(self.dx))
        self.k=self._campo(k);self.rho=self._campo(rho);self.cp=self._campo(cp)
        if any(np.any(x<=0) for x in (self.k,self.rho,self.cp)):raise ValueError('Propiedades positivas.')
        self.capacidad=self.rho*self.cp*self.volumen;self.bordes=bordes or {}
        self.vertidas={int(v['id']):dict(v) for v in vertidas}
        if len(self.vertidas)!=len(vertidas) or set(self.vertidas)!=set(map(int,np.unique(self.ids[self.ids>0]))):
            raise ValueError('Se requiere exactamente una configuración por ID geométrico.')
        for v in self.vertidas.values():
            if not all(math.isfinite(v[key]) for key in ('inicio_s','temperatura_C')) or v['inicio_s']<0:
                raise ValueError('Horario no negativo y temperatura finita.')
        self.T=np.zeros(self.forma);self.activo=np.zeros(self.forma,dtype=bool);self.t=0.
        self.suelo=suelo;self.G_suelo=np.zeros(self.forma);self.P_suelo=np.zeros(self.forma);
        self.energia_suelo_J=0.;self.energia_aire_J=0.
        self.modelo=None;self.eventos=[];self.reconstrucciones=0
        self.energia_colocacion_J=0.;self.energia_fuente_J=0.;self.energia_borde_J=0.
        self.activar()

    def _campo(self,value):
        a=np.broadcast_to(np.asarray(value,dtype=float),self.forma).copy()
        if not np.isfinite(a).all():raise ValueError('Campo no finito.')
        return a

    def activar(self):
        nuevos=[]
        for ident,v in self.vertidas.items():
            cells=(self.ids==ident)&~self.activo
            if v['inicio_s']<=self.t+1e-9 and cells.any():
                E=float(np.sum(self.capacidad[cells]*v['temperatura_C']))
                self.T[cells]=v['temperatura_C'];self.activo[cells]=True;self.energia_colocacion_J+=E
                nuevos.append((ident,E,int(cells.sum())))
        if nuevos:
            # La máscara no se muta dentro de un motor con conexiones precalculadas.
            bordes=self.suelo.bordes(self.activo,self.bordes) if self.suelo else self.bordes
            self.modelo=TermicoCartesiano(self.forma,self.longitudes,self.k,self.rho,self.cp,bordes,self.activo)
            if self.suelo:self.G_suelo,self.P_suelo=self.suelo.terminos_diagnosticos(self.modelo)
            self.reconstrucciones+=1
            for ident,E,count in nuevos:
                self.eventos.append(dict(type='POUR_ACTIVATED',time_s=self.t,pour_id=ident,
                    guid=self.vertidas[ident].get('guid'),cells=count,placed_energy_J=E,
                    temperature_C=self.vertidas[ident]['temperatura_C'],interfaces_rebuilt=True,
                    exposed_areas_m2=self.areas_expuestas(),active_volume_m3=float(self.activo.sum()*self.volumen),
                    dt_max_s=None if not math.isfinite(self.dt_max) else self.dt_max))
            if self.suelo:
                from .suelo import resumen_caras
                for event in self.eventos[-len(nuevos):]:event["boundary_regions"]=resumen_caras(self.activo,self.dx)
        return nuevos

    @property
    def dt_max(self):return self.modelo.dt_max if self.modelo else math.inf

    @property
    def siguiente_evento_s(self):
        return min((v['inicio_s'] for ident,v in self.vertidas.items() if not np.any(self.activo&(self.ids==ident))),default=math.inf)

    def edad_s(self,ident):return max(0.,self.t-self.vertidas[ident]['inicio_s'])

    def energia(self):return self.modelo.energia(self.T) if self.modelo else 0.

    def residual(self):return self.energia()-self.energia_colocacion_J-self.energia_fuente_J-self.energia_borde_J

    def areas_expuestas(self):
        result={}
        for a,d in enumerate(self.dx):
            lo=[slice(None)]*self.ids.ndim;hi=lo.copy();lo[a]=slice(None,-1);hi[a]=slice(1,None);lo,hi=tuple(lo),tuple(hi)
            for sign in ('-','+'):
                neighbor=np.zeros(self.forma,dtype=bool)
                if sign=='+':neighbor[lo]=self.activo[hi]
                else:neighbor[hi]=self.activo[lo]
                result['xyz'[a]+sign]=float(np.count_nonzero(self.activo&~neighbor)*self.volumen/d)
        return result

    def paso(self,dt,fuente_W_m3=0.):
        if not math.isfinite(dt) or dt<=0 or dt>self.dt_max*(1+1e-12):raise ValueError('Paso inestable o inválido para la etapa activa.')
        if self.t+dt>self.siguiente_evento_s+1e-9:raise ValueError('El paso cruza una colocación; detenerlo en el evento.')
        q=self._campo(fuente_W_m3)
        if self.modelo is not None:
            boundary=float(np.sum((self.modelo.P_borde_constante-self.modelo.G_borde*self.T)*self.activo))
            soil=float(np.sum((self.P_suelo-self.G_suelo*self.T)*self.activo)) if self.suelo else 0.
            self.energia_suelo_J+=dt*soil;self.energia_aire_J+=dt*(boundary-soil)
            self.energia_borde_J+=dt*boundary
            self.energia_fuente_J+=dt*float(np.sum(q*self.volumen*self.activo))
            self.T=self.modelo.paso(self.T,dt,fuente_W_m3=q)
        self.t+=dt;self.activar()
        return self.T.copy()
