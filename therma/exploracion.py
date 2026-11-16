"""Familia acotada de planes; sólo compara cálculos IFC S25 de una misma versión."""
import copy,json,time
from pathlib import Path
from .lotes import preparar_config,run_one,validar_catalogo,write_json,write_csv,fingerprint,sha,ROOT
from ejecutar_lotes_defensa import build_catalog

EPS_SOURCE='Knauf White EPS ETICS, ficha 12/2023, White EPS16 lambda=0.038 W/(m K). https://knauf.com/api/download-center/v1/assets/7d13a70b-0055-4d0b-a93f-41e6995ce7bc?download=true'

def catalogo(options=None):
    options=options or {};cat=build_catalog(rate=options.get('rate_m3_h',20.));base=cat['base_config'];base['s25']=dict(method='ifc_mls',depth_m=.025,surface_spacing_m=1.5)
    base['frames']=40
    plans=cat['plans'];proposed=copy.deepcopy(plans[1]);volumes=[v['volume_m3'] for v in proposed['operations']];rate=proposed['rate_m3_h']
    for p in plans:
        p['group_ids']=[[1,2,3]] if p['continuous_operation'] else [[1],[2],[3]]
        p['family']='reference';p['construction_pours']=len(p['group_ids'])
    def make(ident,name,wait=0.,groups=None,temperature=18.):
        groups=groups or [[1],[2],[3]];p=copy.deepcopy(proposed);p.update(id=ident,name=name,placement_C=temperature,group_ids=groups,
            family='exploration',construction_pours=len(groups),continuous_operation=len(groups)==1)
        operations=[];t=0.
        for j,group in enumerate(groups):
            if j:t+=wait
            for ident0 in group:
                d=volumes[ident0-1]/rate;operations.append(dict(id=ident0,volume_m3=volumes[ident0-1],start_h=t,end_h=t+d));t+=d
        p.update(operations=operations,D_h=t,wait_after_group_h=wait)
        p['thermal_approximation']='Each of 3 IFC pieces activated at start of physical placement. Continuous groups are not continuous-fill thermal simulation.'
        return p
    for wait in options.get('waits_h',[0,6,12,18,24,36]):plans.append(make('espera'+str(wait),f'Espera {wait} h',wait=wait))
    for temp in options.get('placement_C',[12,24]):
        p=copy.deepcopy(proposed);p.update(id='colocacion'+str(temp),name=f'Propuesto Tcol {temp} C',placement_C=temp,family='placement',group_ids=[[1],[2],[3]],construction_pours=3);plans.append(p)
    for name in ('sin_moldaje','eps25','eps50','retiro72'):
        p=copy.deepcopy(proposed);p.update(id=name,name={'sin_moldaje':'Propuesto sin moldaje','eps25':'Propuesto EPS 25 mm','eps50':'Propuesto EPS 50 mm','retiro72':'Propuesto retiro moldaje 72 h'}[name],family='protection',group_ids=[[1],[2],[3]],construction_pours=3)
        if name=='sin_moldaje':p['physical_overrides']=dict(formwork=None)
        elif name=='retiro72':
            form=copy.deepcopy(base['formwork']);form['remove_at_h']=72.;p['physical_overrides']=dict(formwork=form)
        else:
            thickness=.025 if name=='eps25' else .05;faces=copy.deepcopy(base['faces'])
            for i,b in enumerate(faces):
                if i!=4:b['R']+=thickness/.038
            p['physical_overrides']=dict(faces=faces);p['insulation']=dict(thickness_m=thickness,conductivity_W_mK=.038,source=EPS_SOURCE,scope='Todas las caras aire, incluidas superiores; no suelo. Permanente. Sin capacidad térmica.')
        plans.append(p)
    plans.append(make('dos_operaciones','Dos operaciones, espera 12 h',wait=12,groups=[[1,2],[3]]))
    combo=make('combinado','Tres piezas sin espera, Tcol12, EPS25',temperature=12.)
    eps=next(p for p in plans if p['id']=='eps25');combo.update(physical_overrides=copy.deepcopy(eps['physical_overrides']),insulation=copy.deepcopy(eps['insulation']));plans.append(combo)
    cat.update(exploration_options=options,probability_policy='INDETERMINATE: no numerical probabilities while IFC S25/source comparability remain unvalidated.',
        placement_source='12/18/24 C controlled-placement sensitivity hypotheses, not supplier measurements. All below ACI discharge ceiling 35 C; this does not establish field attainability. https://www.concrete.org/frequentlyaskedquestions.aspx?faqid=15',
        partition_scope='Only existing 3 IFC pieces. One/two/three physical operations aggregate contiguous pieces; thermal model always 3 piece activations. No new geometric pours.',
        selection_policy='Descriptive worst across same four FV SS curves and fixed climate; no validated optimum.')
    validar_catalogo(cat);return cat


def execute(cat,output,step=.5,only=None,pilot=False):
    from .resolucion import estimar
    out=Path(output);out.mkdir(parents=True,exist_ok=True)
    if only:cat=copy.deepcopy(cat);cat['plans']=[p for p in cat['plans'] if p['id'] in only]
    if pilot:
        cat=copy.deepcopy(cat);cat['sources']=cat['sources'][-1:];cat['scenarios']=[dict(cat['scenarios'][-1],weight='1')]
    validar_catalogo(cat)
    grid=estimar([18,18,3.3],[step]*3,cat['geometry']['volume_m3'],k=cat['base_config']['k'],rho=cat['base_config']['rho'],cp=cat['base_config']['cp'],frames=40,days=14,dt=900.)
    if not grid['allowed']:raise ValueError('Resolución bloqueada por recursos: '+str(grid['reasons']))
    count=len(cat['plans'])*len(cat['scenarios'])
    if count>100:raise ValueError('Primera batería limitada a 100 casos; acotar catálogo.')
    write_json(out/'catalogo_congelado.json',dict(**cat,engine_fingerprint=fingerprint(),grid=grid,planned_runs=count))
    write_csv(out/'cronogramas.csv',[dict(plan_id=p['id'],construction_pours=p['construction_pours'],rate_m3_h=p['rate_m3_h'],D_h=p['D_h'],placement_C=p['placement_C'],**o) for p in cat['plans'] for o in p['operations']])
    records=[]
    for p in cat['plans']:
        for s in cat['scenarios']:
            print(p['id'],s['source_id'],flush=True)
            config=preparar_config(cat,p,s,mesh=grid['shape'],dt=900.)
            r=run_one(config,out/'cache');r.update(plan_id=p['id'],plan_name=p['name'],D_h=p['D_h'],construction_pours=p['construction_pours'],source_id=s['source_id'],climate_id=s['climate_id'],scenario_id=s['id'],weight=s['weight'])
            records.append(r);write_json(out/'progreso.json',records)
            write_csv(out/'tabla_corridas.csv',records)
            summarize(cat,records,out,partial=len(records)<count)
    return summarize(cat,records,out)


def summarize(cat,records,out,partial=False):
    rows=[]
    for p in sorted(cat['plans'],key=lambda p:p['D_h']):
        rr=[r for r in records if r['plan_id']==p['id']];good=[r for r in rr if r['status']=='COMPLETED'];complete=len(good)==len(cat['scenarios'])
        rows.append(dict(Plan=p['name'],plan_id=p['id'],D_h=p['D_h'],vertidas_fisicas=p['construction_pours'],activaciones_IFC=3,
            temperature_placement_C=p['placement_C'],completed=len(good),expected=len(cat['scenarios']),
            Tmax_min_C=min((r['Tmax_C'] for r in good),default=None),Tmax_worst_C=max((r['Tmax_C'] for r in good),default=None),
            Delta_S25_est_min_C=min((r['Delta_estimate_C'] for r in good),default=None),Delta_S25_est_worst_C=max((r['Delta_estimate_C'] for r in good),default=None),
            coverage_air_min_percent=min((100*r['coverage_air_min_fraction'] for r in good),default=None),
            P_T=None,P_Delta=None,P_f=None,compliance='INDETERMINADO',S25='ESTIMADO · NO VALIDADO',
            all_horizons_captured=complete and all(r['horizon_captured'] for r in good),numerical_checks=complete and all(r['numerical_checks'] for r in good)))
    write_csv(out/'tabla_exploratoria.csv',rows);write_json(out/'resumen.json',dict(plans=rows,partial=partial,records=len(records),engine_fingerprints=sorted(set(r.get('engine_fingerprint','FAILED') for r in records))))
    cols=['Plan','D_h','Tmax_worst_C','Delta_S25_est_worst_C','coverage_air_min_percent','completed','compliance']
    def fmt(v):return 'NO EVALUADO' if v is None else f'{v:.3f}' if isinstance(v,float) else str(v)
    (out/'tabla_exploratoria.md').write_text('| '+' | '.join(cols)+' |\n|'+'|'.join(['---']*len(cols))+'|\n'+'\n'.join('| '+' | '.join(fmt(r[c]) for c in cols)+' |' for r in rows)+'\n\nS25 estimado sobre IFC a 25 mm, NO VALIDADO. Máximos descriptivos entre fuentes SS, no probabilidades ni plan óptimo certificado.\n',encoding='utf-8')
    return rows


def plots(output):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    out=Path(output);records=json.loads((out/'progreso.json').read_text(encoding='utf-8'));data=json.loads((out/'resumen.json').read_text(encoding='utf-8'));rows=data['plans']
    fig,ax=plt.subplots(1,2,figsize=(13,7),layout='constrained');y=list(range(len(rows)))
    for a,key,limit,title in zip(ax,['Tmax_worst_C','Delta_S25_est_worst_C'],[70,20],['Tmax [C] · peor fuente SS','Delta S25 ESTIMADO [C] · NO VALIDADO']):
        a.barh(y,[r[key] or 0 for r in rows],color='#318c99');a.axvline(limit,color='red',ls='--',label=f'Referencia {limit} C');a.set_yticks(y,[f"{r['Plan']} | D={r['D_h']:.1f} h" for r in rows],fontsize=8);a.invert_yaxis();a.set_title(title);a.grid(axis='x',alpha=.2);a.legend()
    fig.suptitle('Exploración constructiva · mismo clima y fuentes · sin certificación de cumplimiento');fig.savefig(out/'comparacion_planes.png',dpi=150);plt.close(fig)
    fig,axes=plt.subplots(2,1,figsize=(12,8),layout='constrained')
    for r in records:
        if r['status']!='COMPLETED' or not r['source_id'].endswith('M4_SS'):continue
        m=json.loads((Path(r['snapshot_folder'])/'s25_ifc.json').read_text(encoding='utf-8'));hist=m['history'];t=[v['time_s']/3600 for v in hist]
        for a,key in zip(axes,['Tmax_C','DeltaT_estimate_C']):a.plot(t,[v[key] for v in hist],label=r['plan_name'],lw=1)
    for a,limit,title in zip(axes,[70,20],['Tmax activo simultáneo [C]','Delta S25 ESTIMADO [C] · NO VALIDADO']):a.axhline(limit,color='red',ls='--');a.set(xlabel='Tiempo [h]',ylabel=title);a.grid(alpha=.2)
    axes[0].legend(fontsize=6,ncol=4);fig.savefig(out/'curvas_M4_SS.png',dpi=150);plt.close(fig)
