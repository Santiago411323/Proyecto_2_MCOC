"""Reejecución acotada, congelada y reanudable para el cierre F02."""
import argparse,copy,json
from pathlib import Path
from therma.lotes import preparar_config,run_one,write_json,write_csv,fingerprint,sha
from therma.cierre_f02 import evaluar_horizonte,indicadores


def main():
    a=argparse.ArgumentParser(description=__doc__)
    a.add_argument('--planes',nargs='+',default=['continua','propuesto','rapido','lento','t8_eps100_base1'])
    a.add_argument('--todos',action='store_true',help='Seis referencias y doce alternativas recientes, sin duplicar IDs.')
    a.add_argument('--salida',type=Path,default=Path('resultados/cierre_f02'))
    a.add_argument('--malla',nargs=3,type=int,default=[36,36,7])
    a.add_argument('--horizontes',nargs='+',type=float,default=[42.,56.])
    args=a.parse_args()
    if sorted(set(args.horizontes))!=args.horizontes:raise ValueError('Horizontes crecientes y únicos.')
    cat=json.loads(Path('docs/mejoras_f02/catalogo.json').read_text(encoding='utf-8'))
    reference=json.loads(Path('docs/defensa/evidencia/catalogo_congelado.json').read_text(encoding='utf-8'))
    available={p['id']:p for p in reference['plans']};available.update({p['id']:p for p in cat['plans']})
    selected=list(available) if args.todos else args.planes
    cat['plans']=[copy.deepcopy(available[k]) for k in selected]
    cat['probability_scope']='Modelo epistémico condicional: cuatro fuentes FV/Tikhonov SS con pesos previos 1/4, un clima fijo peso 1. No frecuencias de obra. Comparabilidad de mezcla no confirmada; S25 sin cota validada.'
    cat['weight_rationale']='Equiponderación por ausencia de información discriminante, fijada antes de esta batería; sensibilidad adicional a todos los pesos sobre el mismo soporte. Autorización del equipo: 20 m³/h y cuatro SS provisionales.'
    cat['closure_policy']=dict(horizons_days=args.horizontes,shape=args.malla,dt_s=900.,engine=fingerprint(),
        weather_extension='Ciclo final de 48 h explícito; no pronóstico después del fin publicado.',
        source_tail='Último valor experimental constante, hipótesis no calibrada.',S25='NOT VALIDATED')
    cat['closure_policy']['input_hashes']={str(p):sha(p) for p in (Path('modelo_e02.ifc'),Path('data/hydration/source_terms.txt'),Path('docs/mejoras_f02/catalogo.json'))}
    write_json(args.salida/'catalogo_congelado.json',cat)
    records=[]
    for plan in cat['plans']:
        for scenario in cat['scenarios']:
            for days in args.horizontes:
                cfgcat=copy.deepcopy(cat);cfgcat['base_config']['days']=days
                cfg=preparar_config(cfgcat,plan,scenario,mesh=args.malla,dt=900.)
                if plan.get('basal_R_added'):
                    cfg['environment']['soil']['contact_R_m2K_W']+=plan['basal_R_added']
                print(f"RUN {plan['id']} {scenario['source_id']} {days:g} días",flush=True)
                r=run_one(cfg,args.salida/'cache')
                r.update(plan_id=plan['id'],plan_name=plan['name'],D_h=plan['D_h'],scenario_id=scenario['id'],
                         source_id=scenario['source_id'],climate_id=scenario['climate_id'],weight=scenario['weight'],days=days)
                if r['status']=='COMPLETED':
                    s=json.loads((Path(r['snapshot_folder'])/'s25_ifc.json').read_text(encoding='utf-8'))
                    audit=evaluar_horizonte(s['history'],max(p['start_h'] for p in cfg['construction']['pours']))
                    r['horizon_audit']=audit;r['horizon_captured']=audit['captured'];r['extension_required']=not audit['captured']
                write_json(args.salida/'attempts'/f"{plan['id']}_{scenario['source_id']}_{days:g}.json",r)
                print(json.dumps({k:r.get(k) for k in ('status','error','Tmax_C','Delta_estimate_C','horizon_captured','wall_time_s')},ensure_ascii=False),flush=True)
                if r['status']!='COMPLETED' or r['horizon_captured']:break
            records.append(r);write_json(args.salida/'progreso.json',records);write_csv(args.salida/'tabla_corridas.csv',records)
            tables=[]
            for p in cat['plans']:
                rr=[v for v in records if v['plan_id']==p['id']]
                tables.append(dict(plan_id=p['id'],Plan=p['name'],D_h=p['D_h'],**indicadores(rr,cat['scenarios'])))
            write_json(args.salida/'resumen_planes.json',tables);write_csv(args.salida/'tabla_planes.csv',tables)
    print('Resultados:',args.salida.resolve(),flush=True)


if __name__=='__main__':main()
