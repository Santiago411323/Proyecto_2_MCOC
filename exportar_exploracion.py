"""Exporta tablas, efectos y enlaces a campos existentes; nunca recalcula probabilidades."""
import argparse,json,hashlib,shutil,copy
from pathlib import Path
from therma.lotes import ROOT,write_csv,write_json,sha


def main(lots,output):
    out=Path(output);out.mkdir(parents=True,exist_ok=True);rows=[];records=[];catalogs=[];registry_path=ROOT/'resultados/planes_publicados.json'
    registry=json.loads(registry_path.read_text(encoding='utf-8')) if registry_path.exists() else {}
    for directory in lots:
        data=json.loads((directory/'resumen.json').read_text(encoding='utf-8'))
        if data['partial']:raise ValueError('Lote aún incompleto: '+str(directory))
        cat=json.loads((directory/'catalogo_congelado.json').read_text(encoding='utf-8'));catalogs.append(cat)
        for name in ('catalogo_congelado.json','cronogramas.csv'):
            shutil.copy2(directory/name,out/(directory.name+'_'+name))
        rr=json.loads((directory/'progreso.json').read_text(encoding='utf-8'));step=cat['grid']['spacing_m'][0]*1000
        for r in rr:
            record=dict(r,lote=directory.name,mesh_xy_mm=step);records.append(record)
            if r['status']!='COMPLETED':continue
            ident=r['simulation_id'];folder=Path(r['snapshot_folder'])
            if not all(sha(folder/n)==h for n,h in r['artifacts'].items()):raise ValueError('Artefactos de corrida modificados: '+ident)
            registry[ident]=dict(folder=folder.relative_to(ROOT).as_posix(),artifacts=r['artifacts'],configuration_hash=r['configuration_hash'],engine_fingerprint=r['engine_fingerprint'])
        for r in data['plans']:rows.append(dict(r,lote=directory.name,mesh_xy_mm=step))
    engines=set(r['engine_fingerprint'] for r in records if r['status']=='COMPLETED')
    if len(engines)!=1:raise ValueError('No mezclar versiones del motor: '+str(engines))
    write_json(registry_path,registry);write_csv(out/'tabla_completa.csv',rows);write_csv(out/'corridas.csv',records)
    summary=dict(engine_fingerprint=list(engines)[0],evaluated_cases=len(records),new_runs=sum(not r.get('reused',False) for r in records),reused=sum(r.get('reused',False) for r in records),
        unique_simulations=len(set(r.get('cache_key') for r in records)),failed=sum(r['status']!='COMPLETED' for r in records),
        completed_horizon_warnings=sum(r['status']=='COMPLETED' and not r['horizon_captured'] for r in records),
        probability='INDETERMINATE',S25='ESTIMATED_NOT_VALIDATED',climates=1,sources=4)
    write_json(out/'ejecucion.json',summary)
    columns=['Plan','D_h','Tmax_worst_C','Delta_S25_est_worst_C','coverage_air_min_percent','all_horizons_captured','compliance']
    lines=['# Exploración constructiva S25 IFC','',f"{len(records)} casos; {summary['new_runs']} cálculos nuevos, {summary['reused']} reutilizados. Un clima, cuatro fuentes SS provisionales. P_T, P_Delta y P_f: INDETERMINADAS.",'']
    links=[]
    for directory in lots:
        selected=[r for r in rows if r['lote']==directory.name];lines+=['## '+directory.name,'','| '+' | '.join(columns)+' |','|'+'|'.join(['---']*len(columns))+'|']
        for row in selected:
            fmt=lambda v:'NO EVALUADO' if v is None else f'{v:.3f}' if isinstance(v,float) else str(v)
            lines.append('| '+' | '.join(fmt(row[c]) for c in columns)+' |')
            match=next((r for r in records if r['lote']==directory.name and r['plan_id']==row['plan_id'] and r['source_id'].endswith('M4_SS') and r['status']=='COMPLETED'),None)
            if match:
                url='http://127.0.0.1:8767/panel_termico.html?result='+match['simulation_id'];links.append(f"- [{row['Plan']} · {match['mesh_xy_mm']:.0f} mm · M4_SS]({url})")
                config=Path(match['snapshot_folder'])/'config.json';shutil.copy2(config,out/f"{directory.name}_{row['plan_id']}_M4_config.json")
    lines+=['','Máximos descriptivos entre cuatro curvas completas; no son probabilidades. S25 no validado, cobertura parcial en malla fina. Las advertencias de horizonte indican picos tardíos o aún crecientes; no se extiende con clima inventado.','', '## Abrir campos calculados en THERMA','',*links]
    (out/'TABLA_Y_PLANES.md').write_text('\n'.join(lines),encoding='utf-8')
    comparisons=[];coarse={ (r['plan_id'],r['source_id']):r for r in records if r['mesh_xy_mm']>.4*1000 and r['status']=='COMPLETED'}
    for r in records:
        a=coarse.get((r['plan_id'],r['source_id']))
        if r['mesh_xy_mm']<300 and a and r['status']=='COMPLETED':
            # Misma física salvo discretización. Se comprueba, no se supone.
            configs=[]
            for q in (a,r):
                c=json.loads((Path(q['snapshot_folder'])/'config.json').read_text(encoding='utf-8'))
                for k in ('n','meshIndex','mask'):c.pop(k,None)
                configs.append(c)
            if configs[0]!=configs[1]:raise ValueError('Sensibilidad con distinta física: '+r['plan_id'])
            comparisons.append(dict(plan_id=r['plan_id'],source=r['source_id'],Tmax_500_C=a['Tmax_C'],Tmax_250_C=r['Tmax_C'],dTmax_C=r['Tmax_C']-a['Tmax_C'],Delta_500_est_C=a['Delta_estimate_C'],Delta_250_est_C=r['Delta_estimate_C'],dDelta_est_C=r['Delta_estimate_C']-a['Delta_estimate_C'],note='Diferencia de mallas, no cota de error.'))
    write_csv(out/'comparacion_mallas.csv',comparisons)
    completed=[r for r in rows if r['completed']==r['expected']]
    per_mesh={}
    for step in sorted({r['mesh_xy_mm'] for r in completed},reverse=True):
        rr=[r for r in completed if r['mesh_xy_mm']==step]
        per_mesh[str(step)]=dict(fastest=min(rr,key=lambda r:r['D_h']),lowest_Tmax=min(rr,key=lambda r:r['Tmax_worst_C']),lowest_estimated_delta=min(rr,key=lambda r:r['Delta_S25_est_worst_C']),estimated_both_limits=[r['plan_id'] for r in rr if r['Tmax_worst_C']<=70 and r['Delta_S25_est_worst_C']<=20],official_feasible_plan=None)
    write_json(out/'respuestas.json',per_mesh)
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig,axes=plt.subplots(1,2,figsize=(12,5),layout='constrained')
    for ax,key,limit,title in zip(axes,['Tmax_worst_C','Delta_S25_est_worst_C'],[70,20],['Tmax [C] · peor SS','Delta S25 ESTIMADO [C] · NO VALIDADO']):
        for step in sorted({r['mesh_xy_mm'] for r in completed}):
            rr=[r for r in completed if r['mesh_xy_mm']==step];ax.scatter([r['D_h'] for r in rr],[r[key] for r in rr],marker='o' if step<300 else 'x',label=f'{step:.0f} mm')
            for r in rr:
                if r['plan_id'] in ('combinado','colocacion12','eps50','propuesto'):ax.annotate(r['plan_id'],(r['D_h'],r[key]),fontsize=7,xytext=(3,5),textcoords='offset points')
        ax.axhline(limit,c='red',ls='--',label=f'Referencia {limit} C');ax.set(xlabel='Duración física D [h]',ylabel=title);ax.grid(alpha=.2);ax.legend()
    fig.suptitle('Optimización exploratoria · no hay factibilidad térmica certificada');fig.savefig(out/'D_vs_indicadores.png',dpi=150);plt.close(fig)
    cat=catalogs[0];cr=[r for r in records if r['lote']==lots[0].name and r['status']=='COMPLETED']
    effects=[]
    baseline={r['source_id']:r for r in cr if r['plan_id']=='propuesto'}
    for r in cr:
        if r['plan_id'] in ('colocacion12','colocacion24','sin_moldaje','eps25','eps50','retiro72'):
            b=baseline[r['source_id']];effects.append(dict(plan_id=r['plan_id'],source=r['source_id'],dTmax_vs_proposed_C=r['Tmax_C']-b['Tmax_C'],dDelta_est_vs_proposed_C=r['Delta_estimate_C']-b['Delta_estimate_C'],D_h=r['D_h']))
    write_csv(out/'efectos_aislados.csv',effects)
    fig,axes=plt.subplots(1,3,figsize=(14,4.5),layout='constrained')
    for source in sorted(baseline):
        rr=sorted([r for r in cr if r['source_id']==source and r['plan_id'].startswith('espera')],key=lambda r:float(r['plan_id'][6:]));axes[0].plot([float(r['plan_id'][6:]) for r in rr],[r['Delta_estimate_C'] for r in rr],'o-',label=source)
        rr=sorted([r for r in cr if r['source_id']==source and r['plan_id'] in ('propuesto','colocacion12','colocacion24')],key=lambda r:next(p['placement_C'] for p in cat['plans'] if p['id']==r['plan_id']));axes[1].plot([next(p['placement_C'] for p in cat['plans'] if p['id']==r['plan_id']) for r in rr],[r['Delta_estimate_C'] for r in rr],'o-')
        names=['sin_moldaje','propuesto','retiro72','eps25','eps50'];rr=[next(r for r in cr if r['source_id']==source and r['plan_id']==name) for name in names];axes[2].plot(names,[r['Delta_estimate_C'] for r in rr],'o-')
    for ax,title in zip(axes,['Espera tras cada colocación [h]','Temperatura de colocación [C]','Protección superficial']):ax.axhline(20,color='red',ls='--');ax.set(xlabel=title,ylabel='Delta S25 ESTIMADO [C]');ax.grid(alpha=.2)
    axes[0].legend(fontsize=7);axes[2].tick_params(axis='x',rotation=35);fig.suptitle('Una variable por comparación · misma geometría, fuente y clima · malla 500 mm');fig.savefig(out/'efectos_comparados.png',dpi=150);plt.close(fig)
    print(json.dumps(summary,indent=2))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--lotes',nargs='+',type=Path,default=[Path('resultados/exploracion_constructiva'),Path('resultados/exploracion_refinada'),Path('resultados/exploracion_eps50_refinada')]);p.add_argument('--salida',type=Path,default=Path('docs/exploracion/evidencia'));a=p.parse_args();main(a.lotes,a.salida)
