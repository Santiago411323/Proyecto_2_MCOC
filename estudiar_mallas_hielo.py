"""Estudio reproducible de cobertura y sensibilidad, sin cambiar el motor físico."""
import argparse
import json
from pathlib import Path
import numpy as np
from panel.exportar_ifc import datos_ifc
from therma.superficies_ifc import cargar_superficies
from therma.reconstruccion_s25 import Reconstruccion
from therma.hielo import ROOT, CATALOG
from therma.lotes import write_json, write_csv, run_one
from therma.comparacion_f02 import op_config
from therma.cierre_f02 import evaluar_horizonte

OUT=ROOT/'docs/hielo_f02/convergencia'
# Umbrales de comparación elegidos para este estudio; no tolerancias de la pauta.
SPATIAL_TOLERANCE_C=.10
TEMPORAL_TOLERANCE_C=.05
SHAPES=[(32,32,16),(40,40,24),(48,48,30),(48,48,33),(54,54,27),(60,60,22)]


def coverage(shapes=SHAPES):
    path=ROOT/'modelo_e02.ifc'
    surfaces=cargar_superficies(str(path),path.stat().st_mtime_ns,1.5)
    previous=OUT/'cobertura.json'
    rows=json.loads(previous.read_bytes()) if previous.exists() else []
    for n in shapes:
        d=datos_ifc(path,formas=[n]);grid=d['mallas'][0];dx=np.array(grid['dx']);origin=np.array(d['min'])
        ids=np.asarray(grid['ids']).reshape(n[::-1]).transpose(2,1,0)
        stages=[]
        for stage in [(1,),(1,2),(1,2,3)]:
            s=surfaces.at(stage);active=np.isin(ids,stage)
            r=Reconstruccion(s['points'],active,origin,dx,cell_ids=ids,point_ids=s['point_owner'],allow_partial=True)
            stages.append(dict(pours=stage,unknown=int((~r.supported).sum()),
                               coverage_area=float(s['area'][r.supported].sum()/s['area'].sum())))
        volume=sum(c['volumen_m3'] for c in d['capas'])
        row=dict(shape=n,spacing_m=grid['dx'],total_cells=int(np.prod(n)),active_cells=int((ids>0).sum()),
                 volume_error_pct=100*(grid['volumen_m3']/volume-1),stages=stages,
                 full_coverage=all(s['unknown']==0 for s in stages))
        rows=[r for r in rows if list(r['shape'])!=list(n)]
        rows.append(row);write_json(OUT/'cobertura.json',rows)
        print(json.dumps(row),flush=True)
    return rows


def thermal(shapes,temperature,dt,sources):
    cat=json.loads(CATALOG.read_bytes())
    plan=next(p for p in cat['plans'] if p['id']=={8:'t8_eps100_base1',12:'t12_eps100_base1.0'}[temperature])
    records=[]
    for shape in shapes:
        for source in sources:
            cfg=op_config(cat,plan,source,shape,days=42,dt=dt)
            print('RUN',shape,temperature,source,dt,flush=True)
            r=run_one(cfg,ROOT/'resultados/hielo_f02/cache')
            if r['status']!='COMPLETED':raise RuntimeError(r.get('error',r))
            folder=Path(r['snapshot_folder'])
            s=json.loads((folder/'s25_ifc.json').read_bytes())
            audit=evaluar_horizonte(s['history'],max(v['start_h'] for v in cfg['construction']['pours']))
            r.update(horizon_captured=audit['captured'],horizon_audit=audit,temperature_C=temperature,source_id=source,dt_requested_s=dt)
            records.append(r)
            filename=f'T{temperature}_'+('x'.join(map(str,shape)))+f'_dt{dt:g}_{source}.json'
            write_json(OUT/filename,r)
            print(r['Tmax_C'],r['Delta_estimate_C'],r['missing_points_max'],audit['captured'],flush=True)
    return records


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--coverage',action='store_true')
    p.add_argument('--shape',nargs=3,type=int,action='append')
    p.add_argument('--temperatura',type=int,choices=(8,12),default=8)
    p.add_argument('--dt',type=float,default=1200.)
    p.add_argument('--sources',nargs='+',default=['fv_M4_SS'])
    args=p.parse_args()
    if args.coverage:coverage(args.shape or SHAPES)
    elif args.shape:thermal(args.shape,args.temperatura,args.dt,args.sources)
