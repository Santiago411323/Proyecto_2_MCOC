"""Diagnóstico en cada paso: superficies reconstruidas de la misma BC del motor.

Perfil lineal de media celda; no solución adicional refinada ni medición S25.
"""
import numpy as np
from .exportacion_vtk import puntos_fijos
from .moldaje import resistencia_extra


class Diagnostico:
    def __init__(self):
        self.rows=[];self.peak=None;self.field=None;self.points=None

    def __call__(self,m,p,history):
        if self.points is None:self.points=puntos_fijos(m.ids>0,p['origin'],m.dx)
        best=None;fixed_surface=None
        core_index=tuple(self.points['nucleo']['index_xyz']);ext_index=tuple(self.points['exterior']['index_xyz'])
        for a,d in enumerate(m.dx):
            for side in range(2):
                face=2*a+side
                if face==4:continue  # contacto basal: no superficie de aire
                neighbor=np.zeros(m.forma,bool)
                lo=[slice(None)]*3;hi=lo.copy();lo[a]=slice(None,-1);hi[a]=slice(1,None);lo,hi=tuple(lo),tuple(hi)
                if side:neighbor[lo]=m.activo[hi]
                else:neighbor[hi]=m.activo[lo]
                exposed=m.activo&~neighbor;b=p['faces'][face]
                if b['type']!='R':raise ValueError('Diagnóstico E12 requiere Robin en caras aéreas.')
                air=history['air_temperature_C'];h=b['h']
                resistance=b['R']+resistencia_extra(p,face,m.t)
                qout=np.zeros(m.forma) if h==0 else (m.T-air)/(d/(2*p['k'])+resistance+1/h)
                surface=m.T-qout*d/(2*p['k'])
                s25=m.T-qout*max(d/2-.025,0)/p['k']
                if face==1 and exposed[ext_index]:fixed_surface=float(surface[ext_index])
                for ident in np.unique(m.ids[exposed]):
                    cells=exposed&(m.ids==ident)
                    hot=np.unravel_index(np.argmax(np.where(m.activo&(m.ids==ident),m.T,-np.inf)),m.forma)
                    delta=np.where(cells,np.abs(m.T[hot]-surface),-np.inf)
                    index=np.unravel_index(np.argmax(delta),m.forma);value=float(delta[index])
                    if best is None or value>best['delta_C']:
                        position=np.array(p['origin'])+(np.array(index)+.5)*m.dx
                        position[a]+=(-1 if side==0 else 1)*d/2
                        best=dict(time_s=m.t,delta_C=value,pour_id=int(ident),core_index=list(map(int,hot)),
                            core_xyz_m=(np.array(p['origin'])+(np.array(hot)+.5)*m.dx).tolist(),
                            surface_cell_index=list(map(int,index)),surface_xyz_m=position.tolist(),face=face,
                            core_C=float(m.T[hot]),surface_C=float(surface[index]),S25_estimated_C=float(s25[index]),
                            delta_S25_estimated_C=float(abs(m.T[hot]-s25[index])))
        row=dict(time_s=m.t,Tmax_C=history['max'],air_C=history['air_temperature_C'],
                 core_fixed_C=float(m.T[core_index]) if m.activo[core_index] else None,
                 exterior_cell_C=float(m.T[ext_index]) if m.activo[ext_index] else None,
                 surface_fixed_C=fixed_surface,delta_envelope_C=best['delta_C'] if best else None)
        self.rows.append(row)
        if best and (self.peak is None or best['delta_C']>self.peak['delta_C']):
            self.peak=best;self.field=(m.T.copy(),m.activo.copy(),m.ids.copy())
