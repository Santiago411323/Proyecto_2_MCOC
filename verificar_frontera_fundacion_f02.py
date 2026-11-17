"""Solución manufacturada estacionaria sobre el IFC real; no calibra resultados.

T=20+3z, q=0 y k=2. En cada cara real Robin se prescribe
Tamb=Ts+(k/h)*grad(T).n. Es una condición espacial de ensayo, NO clima.
La frontera cartesiana usa la resistencia de media celda del motor existente.
El error observado no es una cota transferible al caso de hidratación.
"""
from pathlib import Path
import numpy as np
from termico_cartesiano import TermicoCartesiano
from panel.exportar_ifc import datos_ifc
from therma.superficies_ifc import cargar_superficies
from therma.auditoria_geometrica import mas_cercano
from therma.reconstruccion_s25 import Reconstruccion
from therma.lotes import write_csv,write_json


def ejecutar():
    path=Path('modelo_e02.ifc').resolve();geom=cargar_superficies(str(path),path.stat().st_mtime_ns,1.5)
    sample=geom.at((1,2,3));triangles=[];normals=[]
    for solid in geom.solids:
        pid=solid['VertidaID']
        for face in np.unique(sample['triangle_id'][sample['owner']==pid]):
            triangles.append(solid['triangulos'][face])
            index=np.flatnonzero((sample['owner']==pid)&(sample['triangle_id']==face))[0]
            normals.append(sample['outward'][index])
    triangles=np.array(triangles);normals=np.array(normals);rows=[]
    for shape in ([36,36,7],[48,48,9],[72,72,14]):
        d=datos_ifc(path,formas=[tuple(shape)]);grid=d['mallas'][0];dx=np.array(grid['dx']);origin=np.array(d['min']);L=np.array(d['max'])-origin
        ids=np.array(grid['ids']).reshape(shape[::-1]).transpose(2,1,0);active=ids>0
        xyz=np.stack(np.meshgrid(*[origin[a]+(np.arange(shape[a])+.5)*dx[a] for a in range(3)],indexing='ij'),axis=-1)
        m=TermicoCartesiano(shape,L,k=2.,rho=1.,cp=1.,activo=active)
        # Por defecto el motor tiene flujo cero. Sólo se añaden las condiciones
        # analíticas de prueba, conservando sus pares y su avance oficial.
        for axis in range(3):
            for side in (-1,1):
                neighbor=np.zeros_like(active);lo=[slice(None)]*3;hi=lo.copy();lo[axis]=slice(None,-1);hi[axis]=slice(1,None);lo,hi=tuple(lo),tuple(hi)
                if side>0:neighbor[lo]=active[hi]
                else:neighbor[hi]=active[lo]
                exposed=active&~neighbor;A=float(np.prod(np.delete(dx,axis)))
                for idx in np.argwhere(exposed):
                    q=tuple(idx);face_center=xyz[q].copy();face_center[axis]+=side*dx[axis]/2
                    distances,closest=mas_cercano(face_center,triangles);f=int(np.argmin(distances));p=closest[f];normal=normals[f]
                    basal=axis==2 and side==-1 and idx[2]==0
                    if basal:G=2*2*A/dx[axis];ambient=20.
                    else:
                        h=10.;G=A/(dx[axis]/(2*2.)+1/h);ambient=20+3*p[2]+2/h*3*normal[2]
                    m.G_borde[q]+=G;m.P_borde_constante[q]+=G*ambient;m.suma_G[q]+=G
        m.dt_max=float(np.min(m.capacidad[active]/m.suma_G[active]))
        exact=20+3*xyz[...,2];T=np.where(active,exact,0.);initial=m.energia(T);net=0.;t=0.;steps=0
        residual0=float(np.max(np.abs(m.potencias(T)[active]/m.capacidad[active])))
        while t<1.-1e-12:
            dt=min(.7*m.dt_max,1.-t);net+=dt*float(np.sum((m.P_borde_constante-m.G_borde*T)*active))
            T=m.paso(T,dt);t+=dt;steps+=1
        R=Reconstruccion(sample['points'],active,origin,dx,cell_ids=ids,point_ids=sample['point_owner'],allow_partial=True)
        ref=20+3*sample['points'][:,2];err=np.abs(R.evaluate(T)-ref);finite=np.isfinite(err)
        rows.append(dict(shape=shape,time_s=t,steps=steps,initial_stationary_residual_K_s=residual0,
            max_cell_error_C=float(np.max(np.abs(T[active]-exact[active]))),
            max_S25_error_C=float(err[finite].max()),unknown_points=int((~finite).sum()),
            energy_residual_J=float(m.energia(T)-initial-net),
            scope='MMS lineal estacionaria en IFC real, Robin espacial prescrito; NO cota del caso climático.'))
        print(rows[-1],flush=True)
    out=Path('resultados/cierre_f02/validacion/frontera_ifc');write_csv(out/'errores.csv',rows)
    write_json(out/'validacion.json',dict(cases=rows,production_validated=False,
        note='No se impone estacionariedad artificial ni se modifican temperaturas de las corridas. El campo exacto revela error del operador de frontera.'))


if __name__=='__main__':ejecutar()
