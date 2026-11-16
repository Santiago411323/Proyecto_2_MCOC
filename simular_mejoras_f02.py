"""Experimentos reproducibles F02; estimaciones S25, nunca certificación automática."""
import argparse
import copy
import json
from pathlib import Path
import numpy as np
from therma.exploracion import catalogo, summarize, plots
from therma.lotes import preparar_config, run_one, write_json, write_csv, sha
from therma.meteorologia import configuracion_snapshot, instante, utc

OUT=Path('resultados/mejoras_f02')
SNAP=Path('data/weather/20261116T214636704354Z_fade7ac1')

def preparar():
    cat=catalogo(); cat['base_config']['days']=42.
    w=configuracion_snapshot(SNAP,'2026-11-19T10:00:00-03:00')
    original=copy.deepcopy(w['provenance'])
    times=[instante(t) for t in w['time_utc']]; temperatures=w['temperature_C']
    cycle=temperatures[-48:]; last=times[-1]; end=instante(w['start_utc'])+56*86400
    i=0
    while times[-1]<end:
        times.append(last+(i+1)*3600); temperatures.append(cycle[i%48]); i+=1
    w.update(kind='scenario',time_utc=[utc(t) for t in times],provenance=dict(
        snapshot=original,observed_forecast_end_utc=utc(last),
        extension='Repetición del último ciclo de 48 horas. Escenario hipotético, NO forecast ni observación.',
        extension_start_utc=utc(last+3600),extended_hours=i))
    cat['climates']=[dict(id='forecast16nov_cola48h',weather=w)]
    for s in cat['scenarios']:
        s['climate_id']=cat['climates'][0]['id'];s['id']=s['source_id']+'__'+s['climate_id']
    cat['missing_F02']='Pauta recibida en attachments del usuario; t0 corregido a 19 noviembre 2026 10:00 -03.'
    cat['probability_scope']='Sensibilidad condicional; pesos SS hipotéticos. No probabilidad calibrada ni certificación S25.'
    reference=copy.deepcopy(next(p for p in cat['plans'] if p['id']=='propuesto'))
    fast=copy.deepcopy(next(p for p in cat['plans'] if p['id']=='espera0'))
    continuous=copy.deepcopy(next(p for p in cat['plans'] if p['id']=='continua'))
    plans=[reference,continuous]
    for temperature,thickness in [(12,.05),(12,.10),(12,.15),(12,.20),(8,.10),(8,.20)]:
        p=copy.deepcopy(fast);p.update(id=f't{temperature}_eps{int(thickness*1000)}',
            name=f'Sin espera, Tcol {temperature} °C, EPS {int(thickness*1000)} mm',placement_C=float(temperature))
        faces=copy.deepcopy(cat['base_config']['faces'])
        for j,b in enumerate(faces):
            if j!=4:b['R']+=thickness/.038
        p['physical_overrides']=dict(faces=faces)
        p['insulation']=dict(thickness_m=thickness,conductivity_W_mK=.038,
            scope='Caras al aire; suelo original sin aislación. Permanente durante el horizonte.',
            status='Hipótesis de diseño: verificar disponibilidad, ejecución y retiro antes de recomendar obra.')
        plans.append(p)
    cat['plans']=plans
    cold=copy.deepcopy(next(p for p in plans if p['id']=='t8_eps100'))
    cold.update(id='t5_eps100',name='Sin espera, Tcol 5 °C, EPS 100 mm',placement_C=5.)
    plans.append(cold)
    for extra in [.5,1.]:
        p=copy.deepcopy(next(p for p in plans if p['id']=='t12_eps100'))
        p.update(id=f't12_eps100_base{extra}',name=f'Tcol 12 °C, EPS 100 mm, R basal adicional {extra}',
            basal_R_added=extra,basal_hypothesis='Capa aislante adicional hipotética bajo la fundación. Requiere validación estructural/geotécnica; NO cambio de propiedad medida del suelo.')
        plans.append(p)
    p=copy.deepcopy(plans[-1]);p.update(id='t8_eps100_base1',name='Tcol 8 °C, EPS 100 mm, R basal adicional 1',placement_C=8.)
    plans.append(p)
    write_json(OUT/'catalogo.json',cat)
    write_json(OUT/'clima_escenario.json',w)
    return cat

def correr(cat,folder,plans,scenarios,mesh,dt=900.,days=42.):
    folder=Path(folder); selected=copy.deepcopy(cat);selected['plans']=plans;selected['scenarios']=scenarios
    records=[]
    for p in plans:
        for s in scenarios:
            print(f"INICIO {p['id']} {s['source_id']} n={mesh} dt={dt} días={days}",flush=True)
            limited=copy.deepcopy(cat);limited['base_config']['days']=days
            c=preparar_config(limited,p,s,mesh=mesh,dt=dt)
            if p.get('basal_R_added'):
                soil=c['environment']['soil'];soil['contact_R_m2K_W']+=p['basal_R_added']
                soil['parameter_source']=p['basal_hypothesis']+f" R adicional={p['basal_R_added']} m²K/W."
            r=run_one(c,OUT/'cache')
            r.update(plan_id=p['id'],plan_name=p['name'],D_h=p['D_h'],construction_pours=p['construction_pours'],
                source_id=s['source_id'],climate_id=s['climate_id'],scenario_id=s['id'],weight=s['weight'])
            records.append(r);write_json(folder/'progreso.json',records);write_csv(folder/'tabla_corridas.csv',records)
            print(json.dumps({k:r.get(k) for k in ['status','error','Tmax_C','Delta_estimate_C','horizon_captured','missing_points_max','wall_time_s']},ensure_ascii=False),flush=True)
            if r['status']!='COMPLETED':raise RuntimeError(r)
    summarize(selected,records,folder);plots(folder)
    return records

def main():
    a=argparse.ArgumentParser();a.add_argument('fase',choices=['piloto','confirmar','malla','fuentes_finas','clima']);a.add_argument('--plan');args=a.parse_args()
    cat=preparar() if args.fase=='piloto' else json.loads((OUT/'catalogo.json').read_text(encoding='utf-8'))
    if args.fase=='piloto':
        correr(cat,OUT/'piloto',cat['plans'],[dict(cat['scenarios'][-1],weight='1')],[36,36,7])
    else:
        p=next(p for p in cat['plans'] if p['id']==args.plan)
        if args.fase=='confirmar':correr(cat,OUT/'confirmacion', [cat['plans'][0],p],cat['scenarios'],[36,36,7])
        elif args.fase=='fuentes_finas':correr(cat,OUT/'fuentes_finas',[p],cat['scenarios'],[48,48,30])
        elif args.fase=='clima':
            results=[]
            for shift in [-3.,3.]:
                modified=copy.deepcopy(cat);w=modified['climates'][0]['weather']
                w['temperature_C']=[t+shift for t in w['temperature_C']]
                w['provenance']['sensitivity_shift_C']=shift
                w['provenance']['sensitivity_status']='Desplazamiento hipotético de toda la historia; NO percentil ni probabilidad.'
                results+=correr(modified,OUT/'clima'/str(shift),[p],[dict(cat['scenarios'][-1],weight='1')],[48,48,30])
                results[-1]['climate_shift_C']=shift
                write_json(OUT/'clima'/'sensibilidad.json',results)
        else:
            rows=[]
            for name,mesh,dt,days in [('h500',[36,36,7],900.,42.),('h375',[48,48,9],900.,42.),('h250',[72,72,14],900.,42.),('z110',[48,48,30],900.,42.),('dt900_21d',[72,72,14],900.,21.),('dt450_21d',[72,72,14],450.,21.),('dt450_h375',[48,48,9],450.,42.)]:
                r=correr(cat,OUT/'malla'/name,[p],[dict(cat['scenarios'][-1],weight='1')],mesh,dt,days)[0]
                meta=json.loads((Path(r['snapshot_folder'])/'metadata.json').read_text(encoding='utf-8'))
                r.update(case=name,active_cells=meta['metrics']['N'],total_cells=int(np.prod(mesh)),
                    volume_error_percent=100*abs(meta['metrics']['geometric_volume_m3']-cat['geometry']['volume_m3'])/cat['geometry']['volume_m3'])
                rows.append(r);write_json(OUT/'malla'/'comparacion.json',rows);write_csv(OUT/'malla'/'comparacion.csv',rows)

if __name__=='__main__':main()
