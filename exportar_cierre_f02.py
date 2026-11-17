"""Tablas y figuras de cierre; no altera ni certifica resultados."""
import argparse,json,shutil
from pathlib import Path
from therma.lotes import write_json,write_csv,sha


def main(folder,output):
    records=json.loads((folder/'progreso.json').read_text(encoding='utf-8'))
    summaries=json.loads((folder/'resumen_planes.json').read_text(encoding='utf-8'))
    cat=json.loads((folder/'catalogo_congelado.json').read_text(encoding='utf-8'))
    write_json(output/'catalogo_congelado.json',cat)
    table=[]
    for s in summaries:
        rr=[r for r in records if r['plan_id']==s['plan_id']]
        good=[r for r in rr if r['status']=='COMPLETED']
        table.append(dict(Plan=s['Plan'],D_h=s['D_h'],P_T_percent=None if s['P_T'] is None else 100*s['P_T'],
            P_Delta_percent=None,P_f_percent=None,compliance='INDETERMINADO',
            scenarios=len(good),expected=len(cat['scenarios']),
            Tmax_C=max((r['Tmax_C'] for r in good),default=None),
            Delta_S25_estimate_C=max((r['Delta_estimate_C'] for r in good),default=None),
            horizons_captured=len(good)==len(cat['scenarios']) and all(r['horizon_captured'] for r in good),
            max_days=max((r['days'] for r in good),default=None),
            P_T_any_weights=s['P_T_all_weights_bounds']))
    write_csv(output/'tabla_planes.csv',table);write_csv(output/'tabla_corridas.csv',records)
    sources={s['id']:s for s in cat['sources']};climates={c['id']:c for c in cat['climates']}
    write_csv(output/'escenarios_y_pesos.csv',[dict(id=s['id'],weight=s['weight'],source=s['source_id'],
        climate=s['climate_id'],source_sha256=sources[s['source_id']]['curve']['raw_sha256'],
        source_method=sources[s['source_id']]['method'],source_units='W/m3',
        source_last_age_h=sources[s['source_id']]['curve']['time_h'][-1],
        tail=sources[s['source_id']]['tail_assumption'],scope=cat['probability_scope']) for s in cat['scenarios']])
    write_csv(output/'cronogramas.csv',[dict(plan_id=p['id'],D_h=p['D_h'],rate_m3_h=p['rate_m3_h'],**o) for p in cat['plans'] for o in p['operations']])
    write_json(output/'procedencia.json',dict(policy=cat['closure_policy'],weight_rationale=cat['weight_rationale'],
        weather=[dict(id=c['id'],start_utc=c['weather']['start_utc'],provenance=c['weather']['provenance']) for c in cat['climates']]))
    write_json(output/'planes_configuracion.json',cat['plans'])
    cols=['Plan','D_h','P_T_percent','P_Delta_percent','P_f_percent','compliance']
    text=['| Plan | D [h] | P_T [%] | P_Delta [%] | P_f conjunta [%] | ¿Cumple? |','|---|---:|---:|---:|---:|---|']
    for r in table:
        text.append('| '+' | '.join('INDETERMINADO' if r[k] is None else f'{r[k]:.3f}' if isinstance(r[k],float) else str(r[k]) for k in cols)+' |')
    output.mkdir(parents=True,exist_ok=True)
    (output/'tabla_planes.md').write_text('\n'.join(text)+'\n\nModelo condicional de cuatro estados SS equiponderados. S25 estimado, NO VALIDADO.\n',encoding='utf-8')
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig,axes=plt.subplots(1,2,figsize=(13,5),layout='constrained')
    for ax,key,limit in zip(axes,('Tmax_C','Delta_S25_estimate_C'),(70,20)):
        for r in table:
            if r[key] is not None:ax.scatter(r['D_h'],r[key]);ax.annotate(r['Plan'],(r['D_h'],r[key]),fontsize=6)
        ax.axhline(limit,ls='--',color='red');ax.set(xlabel='Duración física D [h]',ylabel=key+' [°C]');ax.grid(alpha=.2)
    fig.suptitle('Cierre 42–56 días · S25 estimado · no certifica riesgo conjunto');fig.savefig(output/'planes.png',dpi=160);plt.close(fig)
    for source in ('validacion.json','errores_reconstruccion_ifc.csv','error_volumen_ifc.csv','error_area_frontera_ifc.csv'):
        p=folder/'validacion'/source
        if p.exists():shutil.copyfile(p,output/source)
    for source in ('frontera_staircase.csv','gradiente_pronunciado.csv'):
        p=folder/'validacion/frontera'/source
        if p.exists():shutil.copyfile(p,output/source)
    p=folder/'sensibilidad/comparacion.csv'
    if p.exists():shutil.copyfile(p,output/'sensibilidad_malla_paso.csv')
    p=folder/'validacion/frontera_ifc/errores.csv'
    if p.exists():shutil.copyfile(p,output/'errores_operador_frontera_ifc.csv')
    write_json(output/'estado.json',dict(plans=len(table),runs=len(records),
        completed=sum(r['status']=='COMPLETED' for r in records),horizons_pending=[r['cache_key'] for r in records if not r.get('horizon_captured')],
        numerical_checks=all(r.get('numerical_checks') for r in records),
        maximum_energy_residual=max((r.get('energy_residual_relative',0) for r in records),default=None),
        validation='NOT VALIDATED',scope=cat['probability_scope'],
        engine=cat['closure_policy']['engine'],input_hashes=cat['closure_policy']['input_hashes'],
        data_files={p.name:sha(p) for p in output.glob('*.csv')}))
    print(json.dumps(table,ensure_ascii=False,indent=2))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--entrada',type=Path,default=Path('resultados/cierre_f02'));p.add_argument('--salida',type=Path,default=Path('docs/cierre_f02/evidencia'));a=p.parse_args();main(a.entrada,a.salida)
