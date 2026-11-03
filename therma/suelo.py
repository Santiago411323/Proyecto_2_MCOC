"""5A: contacto basal efectivo, con clasificación geométrica comprobada.

No agrega voxeles de suelo ni una fuente ficticia. Un reservorio a Ts intercambia
calor a través de Rcontacto + Ls/ks. La media celda de hormigón la añade Robin
del motor oficial. Es una aproximación estacionaria declarada, sin almacenamiento
ni calibración geotécnica. Las demás caras conservan sus bordes originales.
"""
from dataclasses import dataclass
import math
import numpy as np
from termico_cartesiano import TermicoCartesiano


def clasificar_caras(activo):
    """Cada cara de celda activa es aire, suelo basal o interna; nunca dos.

    El plano del suelo es la cara inferior de la última coordenada de la grilla
    (z en 3D). Los huecos o caras inferiores elevadas se clasifican como aire.
    """
    active=np.asarray(activo,dtype=bool);axis=active.ndim-1
    basal=np.zeros_like(active);lower=[slice(None)]*active.ndim;lower[axis]=0
    basal[tuple(lower)]=True
    result={}
    for a in range(active.ndim):
        lo=[slice(None)]*active.ndim;hi=lo.copy();lo[a]=slice(None,-1);hi[a]=slice(1,None);lo,hi=tuple(lo),tuple(hi)
        for sign in ('-','+'):
            neighbor=np.zeros_like(active)
            if sign=='+':neighbor[lo]=active[hi]
            else:neighbor[hi]=active[lo]
            exposed=active&~neighbor
            soil=exposed&basal if a==axis and sign=='-' else np.zeros_like(active)
            result['xyz'[a]+sign]=dict(soil=soil,air=exposed&~soil,internal=active&neighbor)
    return result


def resumen_caras(activo,dx):
    volume=float(np.prod(dx));classes=clasificar_caras(activo);summary={}
    for name,masks in classes.items():
        area=volume/dx['xyz'.index(name[0])]
        summary[name]={key:dict(faces=int(mask.sum()),area_m2=float(mask.sum()*area)) for key,mask in masks.items()}
    return summary


@dataclass(frozen=True)
class SueloEfectivo:
    temperature_C: float
    depth_m: float
    conductivity_W_mK: float
    contact_R_m2K_W: float
    parameter_source: str
    model: str='effective_basal_reservoir'

    def __post_init__(self):
        values=(self.temperature_C,self.depth_m,self.conductivity_W_mK,self.contact_R_m2K_W)
        if self.model!='effective_basal_reservoir' or any(isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v) for v in values):
            raise ValueError('Modelo de suelo y parámetros finitos requeridos.')
        if self.depth_m<=0 or self.conductivity_W_mK<=0 or self.contact_R_m2K_W<0:
            raise ValueError('Suelo: espesor y conductividad positivos, resistencia de contacto no negativa.')
        if not isinstance(self.parameter_source,str) or not 5<=len(self.parameter_source)<=500:
            raise ValueError('Declarar procedencia de los parámetros del suelo.')

    @property
    def resistance_m2K_W(self):return self.contact_R_m2K_W+self.depth_m/self.conductivity_W_mK

    def robin(self):
        # h es una conductancia efectiva de suelo, NO convección con viento.
        return dict(tipo='robin',h_W_m2K=self.conductivity_W_mK/self.depth_m,
                    R_m2K_W=self.contact_R_m2K_W,temperatura_C=self.temperature_C)

    def bordes(self,activo,originales):
        key='xyz'[np.asarray(activo).ndim-1]+'-'
        if clasificar_caras(activo)[key]['air'].any():
            raise ValueError('Suelo efectivo no aplicable: hay caras inferiores expuestas al aire fuera del plano basal. Revisar geometría/orden de vertidas; no se asignará suelo a esas caras.')
        return {**originales,key:self.robin()}

    def terminos_diagnosticos(self,motor):
        """Extrae G/P basales de otra ensambladura oficial; no integra un solver.

        El resto de las caras se deja Neumann cero en esta ensambladura auxiliar.
        Se descartan pares/capacidades auxiliares; sólo se conservan G y P de suelo.
        Así las esquinas no se confunden con la suma de suelo + convección lateral.
        """
        key='xyz'[motor.ndim-1]+'-'
        diagnostic=TermicoCartesiano(motor.forma,motor.longitudes,motor.k,motor.rho,motor.cp,
                                    {key:self.robin()},motor.activo)
        return diagnostic.G_borde.copy(),diagnostic.P_borde_constante.copy()


def validar_entorno(p):
    env=p['environment']
    if not p.get('construction') or p['geometry']!='foundation':raise ValueError('El entorno 5A requiere construcción de la fundación IFC.')
    if not isinstance(env,dict) or set(env)!={'soil'} or not isinstance(env['soil'],dict):raise ValueError('5A admite únicamente environment.soil.')
    allowed={'model','temperature_C','depth_m','conductivity_W_mK','contact_R_m2K_W','parameter_source'}
    if set(env['soil'])!=allowed:raise ValueError('Parámetros de suelo incompletos o desconocidos.')
    model=SueloEfectivo(**env['soil'])
    shape=tuple(p['n']);ids=np.asarray(p['mask']).reshape(shape[::-1]).transpose(2,1,0)
    pours=p['construction']['pours']
    # Comprobar TODOS los estados, no sólo la fundación totalmente colocada.
    for t in sorted(set(v['start_h'] for v in pours)):
        placed=[v['id'] for v in pours if v['start_h']<=t]
        model.bordes(np.isin(ids,placed),{})
    return model
