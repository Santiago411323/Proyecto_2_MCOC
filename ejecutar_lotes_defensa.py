"""F02: congelar catálogo y enumerar planes x fuentes x clima, sin navegador."""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import numpy as np
from panel.exportar_ifc import datos_ifc
from therma.lotes import ejecutar_catalogo, write_json, write_csv, ROOT, sha
from therma.meteorologia import configuracion_snapshot

NAMES=[f'M{i}_{c}' for c in ('SS','22A') for i in range(1,5)]


def audit_sources():
    audit=[]
    for file,method in [('retiradas/source_terms_pinn_obsoleto.txt','PINN'),('source_terms.txt','FV_Tikhonov_beta2.5')]:
        path=ROOT/'data/hydration'/file
        raw=np.loadtxt(path)
        rows=[]
        for j,name in enumerate(NAMES,1):
            valid=np.isfinite(raw[:,j])
            indices=np.flatnonzero(valid)
            if not len(indices) or not np.array_equal(indices,np.arange(len(indices))):
                raise ValueError('NaN interno o registro vacío: '+name)
            t=raw[valid,0];q=raw[valid,j]
            if np.any(np.diff(t)<=0) or np.any(q<0):
                raise ValueError('Tiempos o fuentes no físicos.')
            rows.append(dict(id=name,records=len(t),NaN=int((~valid).sum()),end_h=float(t[-1]),
                             peak_W_m3=float(q.max()),energy_MJ_m3=float(np.trapezoid(q,t*3600)/1e6),
                             theta_with_selected_capacity_C=float(np.trapezoid(q,t*3600)/(2476*1023)),last_W_m3=float(q[-1])))
        audit.append(dict(file=str(path.relative_to(ROOT)),sha256=sha(path),method=method,curves=rows,
                          status='RETIRED_INVALID_USER_DATA' if method=='PINN' else 'CURRENT_USER_PROVIDED',
                          header='\n'.join(l for l in path.read_text(encoding='utf-8').splitlines() if l.startswith('#'))))
    return audit


def build_catalog(method='fv',rate=20.):
    if method!='fv':raise ValueError('PINN fue retirado por el usuario. Sólo FV/Tikhonov es una fuente vigente.')
    file='source_terms.txt'
    raw_path=ROOT/'data/hydration'/file
    data=np.loadtxt(raw_path)
    sources=[]
    for j,name in enumerate(NAMES[:4],1):
        valid=np.isfinite(data[:,j]);t=data[valid,0];q=data[valid,j]
        sources.append(dict(id=method+'_'+name,method=method,provenance=f'{file}, {name}; escenarios epistemicos SS; igualdad de mezcla NO comprobada.',
            curve=dict(time_h=t.tolist(),Q_W_m3=q.tolist(),column=name+'_W_m3',raw_sha256=sha(raw_path),tail='constant_last',
                time_origin='Inicio de ventana retenida (+2 h) alineado a colocación; dos horas ausentes no reconstruidas.'),
            tail_assumption='Después del registro se mantiene el último Q. Hipótesis, no dato experimental; sensibilidad pendiente.'))
    weather=configuracion_snapshot(ROOT/'data/weather/20261112T124325279292Z_a139765f','2026-11-13T10:00:00-03:00')
    ifc=datos_ifc(ROOT/'modelo_e02.ifc')
    volumes=[v['volumen_m3'] for v in ifc['capas']]
    durations=[v/rate for v in volumes]
    plans=[]
    for ident,name,interval in [('continua','Una vertida continua',None),('propuesto','Propuesto',24.),('rapido','Más rápido',16.),('lento','Más lento',48.),('intervalo18','Intervalo 18 h',18.),('intervalo36','Intervalo 36 h',36.)]:
        starts=[0.,durations[0],durations[0]+durations[1]] if interval is None else [0.,interval,2*interval]
        ops=[dict(id=i+1,volume_m3=v,start_h=s,end_h=s+d) for i,(v,s,d) in enumerate(zip(volumes,starts,durations))]
        plans.append(dict(id=ident,name=name,rate_m3_h=rate,placement_C=18.,D_h=ops[-1]['end_h'],operations=ops,
            continuous_operation=interval is None,minimum_wait_h=0.,
            constraints='Un equipo, capacidad constante, orden inferior-superior, sin solapamiento; sin restricción resistente validada.',
            thermal_approximation='Tres bloques IFC activados al INICIO de colocar cada bloque, incluso en operación continua. No integración de llenado continuo.'))
    base=json.loads((ROOT/'docs/e12/evidencia/config.json').read_text(encoding='utf-8'))
    for key in ('mask','n','L','origin','weather','construction'):base.pop(key,None)
    base.update(rho=2476.,cp=1023.,k=2.,meshIndex=1,days=14.,frames=40,dtMode='manual',dt=900.)
    return dict(version=1,sources=sources,climates=[dict(id='forecast_12nov',weather=weather)],plans=plans,base_config=base,
        scenarios=[dict(id=s['id']+'__forecast_12nov',source_id=s['id'],climate_id='forecast_12nov',weight='0.25') for s in sources],
        weight_rationale='Cuatro estados de fuente SS equiponderados por hipótesis epistémica previa, NO frecuencias ni réplicas comprobadas. Un clima fijo peso 1. Sin independencia adicional inferida.',
        probability_scope='Condicionada al único forecast, método de inversión '+method+', cola constante, hipótesis SS equiponderada y parámetros declarados. No probabilidad de obra calibrada.',
        geometry=dict(ifc_sha256=ifc['sha256'],volume_m3=sum(volumes),provisional=True),
        construction_hypothesis='20 m3/h de ensayo (o --rate), no dato de proveedor. D físico incluye fin de colocación; tres activaciones discretas no modelan operación continua.',
        missing_F02='Pauta original no hallada localmente. Requisitos usados: transcripción del usuario en chat, 16-11-2026.',
        source_admissibility='SS de un solo método para sensibilidad de modelo. Identidad de mezcla común y pesos no demostrados experimentalmente. 22A excluida a priori por menor confianza declarada y menor cobertura; PINN NO mezclado con FV.')


def sensitivities(cat,output):
    # Mantener físicos idénticos: sólo cambiar grilla o dt. Fuente M4_SS fija.
    subset=copy.deepcopy(cat)
    subset['plans']=[next(p for p in cat['plans'] if p['id']=='propuesto')]
    subset['sources']=[cat['sources'][-1]]
    subset['scenarios']=[dict(cat['scenarios'][-1],weight='1')]
    rows=[]
    for name,mesh,dt in [('coarse',[24,24,6],900.),('fine',[36,36,12],900.),('fine_dt450',[36,36,12],450.),('finest',[48,48,18],900.)]:
        _,records=ejecutar_catalogo(subset,output/name,mesh,dt)
        rows.append(dict(case=name,**records[0]))
    write_csv(output/'sensibilidad.csv',rows)
    if all(r['status']=='COMPLETED' for r in rows):
        fine=rows[1]
        write_json(output/'comparacion.json',dict(
            spatial=dict(dTmax_C=abs(rows[0]['Tmax_C']-fine['Tmax_C']),dDelta_estimate_C=abs(rows[0]['Delta_estimate_C']-fine['Delta_estimate_C'])),
            temporal=dict(dTmax_C=abs(rows[2]['Tmax_C']-fine['Tmax_C']),dDelta_estimate_C=abs(rows[2]['Delta_estimate_C']-fine['Delta_estimate_C'])),
            spatial_finer=dict(dTmax_C=abs(rows[3]['Tmax_C']-fine['Tmax_C']),dDelta_estimate_C=abs(rows[3]['Delta_estimate_C']-fine['Delta_estimate_C'])),
            validation='NOT VALIDATED: refinamientos en un escenario no acotan error S25 en todo el catálogo. Geometría escalonada cambia con malla.'))
    return rows


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--salida',type=Path,default=ROOT/'resultados/defensa')
    parser.add_argument('--catalogo',type=Path)
    parser.add_argument('--preparar',action='store_true')
    parser.add_argument('--metodo',choices=('fv','pinn'),default='fv')
    parser.add_argument('--rate',type=float,default=20.)
    parser.add_argument('--malla',nargs=3,type=int)
    parser.add_argument('--dt',type=float)
    parser.add_argument('--sensibilidad',action='store_true')
    args=parser.parse_args()
    audit=audit_sources()
    cat=json.loads(args.catalogo.read_text(encoding='utf-8')) if args.catalogo else build_catalog(args.metodo,args.rate)
    from therma.lotes import validar_catalogo
    validar_catalogo(cat)
    write_json(args.salida/'auditoria_fuentes.json',audit)
    write_json(args.salida/'catalogo.json',cat)
    write_csv(args.salida/'cronogramas.csv',[dict(plan_id=p['id'],D_h=p['D_h'],rate_m3_h=p['rate_m3_h'],**o) for p in cat['plans'] for o in p['operations']])
    if args.preparar:
        print('Catálogo preparado sin ejecutar: ',args.salida)
        return
    summaries,records=ejecutar_catalogo(cat,args.salida,args.malla,args.dt)
    if args.sensibilidad:sensitivities(cat,args.salida/'sensibilidad')
    print(json.dumps(summaries,ensure_ascii=False,indent=2))


if __name__=='__main__':main()
