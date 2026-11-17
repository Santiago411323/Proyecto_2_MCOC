"""Mide error de reconstrucción EN el IFC real con campos conocidos.

No confunde este ensayo con una cota del error físico del FV staircase.
"""
import argparse
from pathlib import Path
import numpy as np
from panel.exportar_ifc import datos_ifc
from therma.superficies_ifc import cargar_superficies
from therma.reconstruccion_s25 import Reconstruccion
from therma.lotes import write_json,write_csv,sha


def campo(x,kind):
    if kind=='affine':return 20+.4*x[...,0]-.2*x[...,1]+3*x[...,2]
    if kind=='smooth':return 35+8*np.cos(x[...,0]/3)*np.cos(x[...,1]/4)*np.exp(-x[...,2]/2)
    # Capa límite vertical fuerte de 0,10 m, no supuesta solución del caso real.
    return 20+35*(1-np.exp(-np.maximum(x[...,2],0)/.10))


def ejecutar(output):
    path=Path('modelo_e02.ifc');g=cargar_superficies(str(path.resolve()),path.stat().st_mtime_ns,1.5)
    rows=[];geometric=[];boundary_areas=[]
    for n in ([36,36,7],[48,48,9],[72,72,14]):
        d=datos_ifc(path,formas=[tuple(n)]);grid=d['mallas'][0];dx=np.array(grid['dx']);origin=np.array(d['min'])
        ids=np.array(grid['ids']).reshape(n[::-1]).transpose(2,1,0)
        xyz=np.stack(np.meshgrid(*[origin[a]+(np.arange(n[a])+.5)*dx[a] for a in range(3)],indexing='ij'),axis=-1)
        true_volume=sum(c['volumen_m3'] for c in d['capas'])
        geometric.append(dict(shape=n,spacing_m=dx.tolist(),volume_m3=grid['volumen_m3'],
            IFC_volume_m3=true_volume,volume_error_percent=100*(grid['volumen_m3']/true_volume-1)))
        for stage in ((1,),(1,2),(1,2,3)):
            s=g.at(stage);active=np.isin(ids,stage)
            staircase=0.;basal=0.
            for axis in range(3):
                for side in (-1,1):
                    neighbor=np.zeros_like(active);lo=[slice(None)]*3;hi=lo.copy()
                    lo[axis]=slice(None,-1);hi[axis]=slice(1,None);lo,hi=tuple(lo),tuple(hi)
                    if side>0:neighbor[lo]=active[hi]
                    else:neighbor[hi]=active[lo]
                    exposed=active&~neighbor;area=float(np.prod(np.delete(dx,axis)))
                    staircase+=int(exposed.sum())*area
                    if axis==2 and side==-1:basal+=int(exposed[:,:,0].sum())*area
            true_area=float(s['area'].sum());true_soil=float(s['area'][np.array(s['region'])=='soil'].sum())
            boundary_areas.append(dict(shape=n,stage=list(stage),IFC_area_m2=true_area,
                staircase_area_m2=staircase,area_error_percent=100*(staircase/true_area-1),
                IFC_air_m2=true_area-true_soil,staircase_air_m2=staircase-basal,
                scope='Diferencia geométrica de áreas, NO cota del error térmico.'))
            R=Reconstruccion(s['points'],active,origin,dx,cell_ids=ids,point_ids=s['point_owner'],allow_partial=True)
            for kind in ('affine','smooth','sharp_layer'):
                error=np.abs(R.evaluate(campo(xyz,kind))-campo(s['points'],kind));finite=np.isfinite(error)
                for region in ('air','soil'):
                    select=np.array(s['region'])==region;ok=finite&select;area=s['area']
                    rows.append(dict(shape=n,spacing_m=dx.tolist(),stage=list(stage),field=kind,region=region,
                        points=int(select.sum()),unknown=int((select&~finite).sum()),
                        covered_area_percent=float(100*area[ok].sum()/area[select].sum()) if select.any() else None,
                        maximum_error_C=float(error[ok].max()) if ok.any() else None,
                        area_weighted_error_C=float(np.average(error[ok],weights=area[ok])) if ok.any() else None,
                        scope='Error de reconstrucción con valores exactos en centros. NO incluye error de PDE/borde.'))
        print('IFC reconstruction',n,flush=True)
    write_csv(output/'errores_reconstruccion_ifc.csv',rows);write_csv(output/'error_volumen_ifc.csv',geometric)
    write_csv(output/'error_area_frontera_ifc.csv',boundary_areas)
    write_json(output/'validacion.json',dict(IFC_sha256=sha(path),reconstruction=rows,geometry=geometric,boundary_areas=boundary_areas,
        physical_boundary_validated=False,status='NOT VALIDATED',
        reason='Campos manufacturados aíslan reconstrucción; falta acotar error del flujo staircase y muestreo superficial entre puntos. No se transfieren estos errores al caso térmico sin prueba.'))
    return rows


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--salida',type=Path,default=Path('resultados/cierre_f02/validacion'))
    ejecutar(p.parse_args().salida)
