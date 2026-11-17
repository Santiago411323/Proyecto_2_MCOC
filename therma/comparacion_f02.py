"""Catálogo de evidencia F02: lectura, agrupación y agregación; no simula física."""
from pathlib import Path
from functools import lru_cache
import csv, json, hashlib, math, copy
from decimal import Decimal
from .riesgo import resumen_riesgo
from .fuentes_vigentes import RETIRADA_PINN_SHA256
ROOT=Path(__file__).resolve().parents[1]


def read(path,default=None):
    try:return json.loads(Path(path).read_text(encoding='utf-8-sig'))
    except (OSError,ValueError):return default


def rows(path):
    try:
        with Path(path).open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
    except OSError:return []


def number(v):
    try:r=float(v);return r if math.isfinite(r) else None
    except (ValueError,TypeError):return None


def truth(v):return v is True or v=='True'

def digest(v):return hashlib.sha256(json.dumps(v,sort_keys=True,default=str).encode()).hexdigest()


def aggregate(records,expected,weights_fixed=True):
    """Mismo catálogo previo para todos los planes; jamás normalizar faltantes."""
    why=[];events=[];seen=set();expected_map={s['id']:s for s in expected}
    try:
        weights=[Decimal(str(s['weight'])) for s in expected]
        if not weights_fixed or not weights or len(expected_map)!=len(expected) or any(not w.is_finite() or w<0 for w in weights) or sum(weights)!=1:raise ValueError()
    except (ValueError,TypeError,KeyError,ArithmeticError):
        return dict(P_T=None,P_Delta=None,P_f=None,compliance='INDETERMINADO',weights_valid=False,weight_sum=None,missing=[],warnings=['Pesos no fundamentados o catálogo de escenarios incompleto.'])
    for r in records:
        try:
            declared=Decimal(str(r.get('weight'))) if r.get('weight') is not None else None
            if declared is not None and (not declared.is_finite() or declared<0):raise ValueError()
        except (ValueError,ArithmeticError):
            why.append('Peso de corrida inválido.');continue
        if r['scenario_id'] in seen:why.append('Corridas duplicadas para un mismo escenario.')
        if r['scenario_id'] not in expected_map:why.append('Escenario ajeno al catálogo.')
        seen.add(r['scenario_id'])
        if r.get('weight') is not None and declared!=Decimal(str(expected_map.get(r['scenario_id'],{}).get('weight',-1))):why.append('Peso distinto al fijado en el catálogo.')
    missing=[s['id'] for s in expected if s['id'] not in seen]
    if why:return dict(P_T=None,P_Delta=None,P_f=None,compliance='INDETERMINADO',weights_valid=False,weight_sum=1.,missing=missing,warnings=why)
    by={r['scenario_id']:r for r in records}
    for s in expected:
        r=by.get(s['id'],{});ok=r.get('status')=='COMPLETED' and r.get('numerical_checks') is True and r.get('horizon_captured') is True
        t=r.get('Tmax_C');delta=r.get('DeltaTmax_validated_C');valid=r.get('s25_validated') is True
        events.append(dict(scenario_id=s['id'],weight=s['weight'],status='COMPLETED' if ok else 'UNKNOWN',
            I_T=t>70 if ok and t is not None else None,I_Delta=delta>20 if ok and valid and delta is not None else None))
    result=resumen_riesgo(events)
    # Una estimación no se convierte en una probabilidad conjunta oficial.
    if not result['fully_evaluated']:result['P_f']=None
    result.update(weights_valid=True,weight_sum=1.,completed_weight_sum=float(sum((Decimal(str(expected_map[r['scenario_id']]['weight'])) for r in records if r.get('status')=='COMPLETED'),Decimal(0))),missing=missing,warnings=why)
    return result


def safe_folder(path):
    p=Path(path or '').resolve()
    return p if p.is_relative_to((ROOT/'resultados').resolve()) and p.is_dir() else None


def aggregate_estimated(records,expected):
    """Riesgo del modelo aproximado, separado de la evaluación S25 validada."""
    checked=aggregate(records,expected)
    if not checked['weights_valid']:
        return dict(checked,is_estimate=True)
    by={r['scenario_id']:r for r in records};events=[]
    for s in expected:
        r=by.get(s['id'],{})
        ok=r.get('status')=='COMPLETED' and r.get('numerical_checks') is True and r.get('horizon_captured') is True
        t=number(r.get('Tmax_C'));d=number(r.get('Delta_estimate_C'))
        covered=number(r.get('coverage'))==1.
        events.append(dict(scenario_id=s['id'],weight=s['weight'],status='COMPLETED' if ok else 'UNKNOWN',
                           I_T=t>70 if ok and t is not None else None,
                           I_Delta=d>20 if ok and covered and d is not None else None))
    result=resumen_riesgo(events)
    result.update(is_estimate=True,weights_valid=True,weight_sum=checked['weight_sum'],
                  missing=checked['missing'],warnings=['S25 aproximado: no constituye evaluación formal ni probabilidad de obra calibrada.'])
    return result


@lru_cache(maxsize=4)
def ifc_bounds(expected_hash,mtime):
    import numpy as np
    from voxelizar import cargar_geometria
    file=ROOT/'modelo_e02.ifc'
    if expected_hash and hashlib.sha256(file.read_bytes()).hexdigest()!=expected_hash:
        raise ValueError('El IFC actual no coincide con el catálogo archivado.')
    solids=cargar_geometria(file);points=np.concatenate([s['vertices'] for s in solids])
    return points.min(0).tolist(),(points.max(0)-points.min(0)).tolist()


def op_config(cat,plan,source_id,shape=None,days=None,dt=None):
    """Recupera una entrada declarada, no crea un plan nuevo."""
    if not cat or not plan:return None
    scenario=next((s for s in cat.get('scenarios',[]) if s['source_id']==source_id),None)
    if not scenario:return None
    source=next((s for s in cat.get('sources',[]) if s['id']==source_id),None)
    climate=next((s for s in cat.get('climates',[]) if s['id']==scenario['climate_id']),None)
    if not source or not climate:return None
    c=copy.deepcopy(cat['base_config'])
    if not c.get('L') or not c.get('origin'):
        try:origin,lengths=ifc_bounds(cat.get('geometry',{}).get('ifc_sha256'),(ROOT/'modelo_e02.ifc').stat().st_mtime_ns)
        except (OSError,ValueError):return None
        c.update(L=lengths,origin=origin)
    for k,v in plan.get('physical_overrides',{}).items():
        if v is None:c.pop(k,None)
        else:c[k]=copy.deepcopy(v)
    c['weather']=copy.deepcopy(climate['weather'])
    c['construction']=dict(model='tabulated_source',curve=copy.deepcopy(source['curve']),parameter_source=source['provenance'],pours=[dict(id=o['id'],start_h=o['start_h'],placement_C=plan['placement_C']) for o in plan['operations']])
    if shape:c.update(meshIndex=2,n=list(shape))
    if days is not None:c['days']=days
    if dt is not None:c.update(dtMode='manual',dt=dt)
    if plan.get('basal_R_added'):
        c['environment']['soil']['contact_R_m2K_W']+=plan['basal_R_added']
        c['environment']['soil']['parameter_source']=plan.get('basal_hypothesis','Hipótesis basal adicional.')
    return c



class Evidence:
    def __init__(self,local_output=None):
        self.cohorts={};self.runs={};self.local_output=Path(local_output or ROOT/'resultados/servidor_therma')
        self.exploration();self.defense();self.improvements();self.cooling();self.closure();self.local()
        self._summarize()

    def cohort(self,key,title,cat=None,**extra):
        c=self.cohorts.setdefault(key,dict(id=key,title=title,plans={},expected=(cat or {}).get('scenarios',[]),
            scope=(cat or {}).get('probability_scope','Sensibilidad descriptiva; sin probabilidades de obra.'),historical=False,_catalog=cat,**extra))
        return c

    def add(self,c,plan,r,config=None,folder=None,**extra):
        pid=plan['id']
        physical=copy.deepcopy(config)
        if physical and physical.get('construction'):
            physical['construction'].pop('curve',None);physical['construction'].pop('parameter_source',None)
        physics=digest(physical)
        if pid in c['plans'] and c['plans'][pid].get('_physics')!=physics:pid+='__'+physics[:8]
        p=c['plans'].setdefault(pid,dict(id=pid,name=plan.get('name',pid),D_h=number(plan.get('D_h')),operations=plan.get('operations',[]),rate_m3_h=plan.get('rate_m3_h'),thermal_approximation=plan.get('thermal_approximation','Activación instantánea por pieza IFC; duración física separada.'),runs=[]))
        p.setdefault('_physics',physics)
        uid=digest([c['id'],pid,r.get('scenario_id'),r.get('simulation_id'),r.get('cache_key'),extra.get('case')])[:24]
        raw=dict(r);n=raw.get('shape')
        if isinstance(n,str):n=read_value(n)
        tmax=number(raw.get('Tmax_C'));delta=number(raw.get('Delta_estimate_C'))
        curve=(config or {}).get('construction',{}).get('curve',{})
        retired=curve.get('raw_sha256')==RETIRADA_PINN_SHA256
        item=dict(uid=uid,plan_id=pid,plan_name=p['name'],cohort_id=c['id'],source_id=raw.get('source_id','NO DECLARADA'),climate_id=raw.get('climate_id','NO DECLARADO'),
            scenario_id=raw.get('scenario_id',uid),weight=raw.get('weight'),simulation_id=raw.get('simulation_id'),status=raw.get('status','COMPLETED'),
            Tmax_C=tmax,Delta_estimate_C=delta,Tmax_time_h=number(raw.get('Tmax_time_h')),Delta_time_h=number(raw.get('Delta_time_h')),
            numerical_checks=truth(raw.get('numerical_checks')),horizon_captured=truth(raw.get('horizon_captured')),
            s25_validated=raw.get('S25_validation')=='VALIDATED',DeltaTmax_validated_C=number(raw.get('DeltaTmax_C')),
            S25_validation=raw.get('S25_validation') or 'NOT VALIDATED',coverage=number(raw.get('coverage_air_min_fraction')),
            shape=n or (config or {}).get('n'),days=c.get('days') or (config or {}).get('days'),dt_s=number(raw.get('dt_s')) or (config or {}).get('dt'),
            configuration_hash=raw.get('configuration_hash'),engine=raw.get('engine_fingerprint') or c.get('engine','NO DOCUMENTADO'),
            code_sha=raw.get('code_sha'),retired=retired,peak_S25=read_value(raw.get('peak_S25')),
            hot_xyz=raw.get('hot_xyz'),cold_xyz=raw.get('cold_xyz'),max_xyz=raw.get('max_xyz'),
            _config=config,_folder=safe_folder(folder),_raw=raw,**extra)
        if retired:item.update(numerical_checks=False,status='RETIRED')
        item['I_T']=tmax>70 if item['status']=='COMPLETED' and item['numerical_checks'] and item['horizon_captured'] and tmax is not None else None
        item['I_Delta']=item['DeltaTmax_validated_C']>20 if item['s25_validated'] and item['DeltaTmax_validated_C'] is not None and item['numerical_checks'] and item['horizon_captured'] else None
        item['I_F']=True if item['I_T'] is True or item['I_Delta'] is True else False if item['I_T'] is False and item['I_Delta'] is False else None
        item['I_Delta_estimated']=delta>20 if item['status']=='COMPLETED' and item['numerical_checks'] and item['horizon_captured'] and item['coverage']==1 and delta is not None else None
        item['I_F_estimated']=True if item['I_T'] is True or item['I_Delta_estimated'] is True else False if item['I_T'] is False and item['I_Delta_estimated'] is False else None
        p['runs'].append(uid);self.runs[uid]=item
        if config and 'parameters' not in p:
            p['thermal_starts']={str(v['id']):v['start_h'] for v in config.get('construction',{}).get('pours',[])}
            p['parameters']=dict(physical_pours=plan.get('construction_pours',1 if plan.get('continuous_operation') else len(plan.get('operations',[]))),IFC_pieces=len(config.get('construction',{}).get('pours',[])),shape=item['shape'],days=item['days'],placement=[v['placement_C'] for v in config.get('construction',{}).get('pours',[])],formwork=config.get('formwork'),cooling=config.get('cooling'),soil=config.get('environment'),faces=config.get('faces'),source_hash=curve.get('raw_sha256'),geometry=config.get('foundation_parameters') or 'IFC de referencia',start_utc=config.get('weather',{}).get('start_utc'))

    def exploration(self):
        base=ROOT/'docs/exploracion/evidencia';data=rows(base/'corridas.csv')
        for r in data:
            lot=r['lote'];cat=read(base/(lot+'_catalogo_congelado.json'),{});plan=next((p for p in cat.get('plans',[]) if p['id']==r['plan_id']),None)
            if not plan:continue
            n=read_value(r.get('shape'));folder=safe_folder(r.get('snapshot_folder'));engine=r.get('engine_fingerprint')
            # Versión, malla, horizonte, geometría y familia nunca se mezclan.
            key='explore-'+digest([lot,engine,n,cat.get('base_config',{}).get('days'),cat.get('geometry')])[:12]
            c=self.cohort(key,'Histórico · '+lot+' · '+r['mesh_xy_mm']+' mm',cat,days=cat.get('base_config',{}).get('days',14),engine=engine)
            c['historical']=True
            cfg=read(folder/'config.json') if folder else None
            if cfg is None:cfg=op_config(cat,plan,r['source_id'],n,days=c['days'])
            self.add(c,plan,r,cfg,folder)

    def defense(self):
        base=ROOT/'docs/defensa/evidencia';cat=read(base/'catalogo_congelado.json',{})
        for r in rows(base/'tabla_corridas.csv'):
            plan=next((p for p in cat.get('plans',[]) if p['id']==r['plan_id']),None)
            if not plan:continue
            folder=safe_folder(r.get('snapshot_folder'));cfg=read(folder/'config.json') if folder else None
            shape=read_value(r.get('shape'));key='defense-'+digest([r.get('code_sha'),shape,cat.get('geometry')])[:12]
            c=self.cohort(key,'Histórico · lote inicial de defensa · '+str(shape),cat,days=(cfg or cat.get('base_config',{})).get('days',14),engine=r.get('code_sha'))
            c['historical']=True
            self.add(c,plan,r,cfg or op_config(cat,plan,r['source_id'],shape,days=c['days']),folder,legacy_s25=True)

    def improvements(self):
        base=ROOT/'docs/mejoras_f02';cat=read(base/'catalogo.json',{});provenance=read(base/'procedencia_codigo.json',{});engine=provenance.get('engine_fingerprint','VERSION NO DOCUMENTADA')
        self.latest_cat=cat
        for row in rows(base/'corridas.csv'):
            phase=row['fase'];plan=next((p for p in cat.get('plans',[]) if p['id']==row['plan']),None)
            if not plan:continue
            shape=[48,48,30] if phase=='fuentes_finas' else [36,36,7]
            for days in [42,14]:
                key=f'mejoras-{phase}-{days}';c=self.cohort(key,f'19 noviembre · {phase} · {days} días · '+('375/375/110 mm' if phase=='fuentes_finas' else '500 mm'),cat,days=days,engine=engine)
                if phase=='piloto':c['expected']=[dict(cat['scenarios'][-1],weight='1')];c['scope']='Piloto condicionado a M4 SS, peso 1 fijado para sensibilidad; no representa las cuatro fuentes.'
                expected=next(s for s in c['expected'] if s['source_id']==row['fuente']);cache=row['cache_key'];folder=ROOT/'resultados/mejoras_f02/cache'/cache
                actual=read(folder/'batch_result.json',{})
                cfg=op_config(cat,plan,row['fuente'],shape,days=42,dt=900.)
                r=dict(actual,cache_key=cache,simulation_id=cache[:32],scenario_id=expected['id'],source_id=row['fuente'],climate_id=expected['climate_id'],weight=expected['weight'],
                    status='COMPLETED',Tmax_C=row[f'Tmax{days}_C'],Delta_estimate_C=row[f'Delta{days}_estimado_C'],
                    Tmax_time_h=row['t_Tmax_h'] if days==42 else None,Delta_time_h=row['t_Delta_h'] if days==42 else None,
                    horizon_captured=truth(row['horizonte_capturado']) if days==42 else False,numerical_checks=number(row['balance_relativo']) is not None and number(row['balance_relativo'])<1e-10,
                    energy_residual_relative=number(row['balance_relativo']),coverage_air_min_fraction=(number(row['cobertura_aire_pct']) or 0)/100,
                    S25_validation='NOT VALIDATED',shape=shape,dt_s=900.,engine_fingerprint=engine,
                    max_xyz=read_value(row['xyz_Tmax_m']) if days==42 else None,hot_xyz=read_value(row['xyz_caliente_Delta_m']) if days==42 else None,cold_xyz=read_value(row['xyz_frio_Delta_m']) if days==42 else None)
                self.add(c,plan,r,cfg,folder,partial_horizon=days==14,cache_key=cache,
                    doc_history='docs/mejoras_f02/historia_candidato.csv' if plan['id']=='t8_eps100_base1' and phase=='fuentes_finas' and row['fuente']=='fv_M4_SS' else None,
                    fixed_points='docs/mejoras_f02/puntos_fijos.csv' if plan['id']=='t8_eps100_base1' and phase=='fuentes_finas' and row['fuente']=='fv_M4_SS' else None)
        candidate=next((p for p in cat.get('plans',[]) if p['id']=='t8_eps100_base1'),None)
        if not candidate:return
        for row in rows(base/'mallas.csv'):
            case=row['caso'];shapes=dict(h500=[36,36,7],h375=[48,48,9],h250=[72,72,14],z110=[48,48,30],dt900_21d=[72,72,14],dt450_21d=[72,72,14],dt450_h375=[48,48,9]);shape=shapes.get(case)
            days=21 if '21d' in case else 42;cfg=op_config(cat,candidate,'fv_M4_SS',shape,days=days,dt=number(row['dt_s']))
            key='malla-'+case;c=self.cohort(key,'Sensibilidad de malla/paso · '+case+' · '+str(days)+' días',cat,days=days,engine=engine);c['expected']=[dict(cat['scenarios'][-1],weight='1')]
            raw=dict(scenario_id=c['expected'][0]['id'],source_id='fv_M4_SS',climate_id=cat['climates'][0]['id'],weight='1',status='COMPLETED',Tmax_C=row['Tmax_C'],Delta_estimate_C=row['Delta_estimado_C'],shape=shape,dt_s=row['dt_s'],S25_validation='NOT VALIDATED',numerical_checks=False,horizon_captured=False)
            folder=ROOT/'resultados/mejoras_f02/malla'/case
            self.add(c,candidate,raw,cfg,None,case=case,metrics_only=True)
        for row in rows(base/'sensibilidad_clima.csv'):
            shift=number(row['climate_shift_C']);cfg=op_config(cat,candidate,'fv_M4_SS',[48,48,30],days=42,dt=900.)
            if cfg:
                cfg['weather']['temperature_C']=[t+shift for t in cfg['weather']['temperature_C']]
                cfg['weather']['provenance']['sensitivity_shift_C']=shift
            c=self.cohort('clima-'+str(shift),'Sensibilidad climática · desplazamiento '+str(shift)+' °C',days=42,engine=engine);c['expected']=[]
            self.add(c,candidate,dict(scenario_id='M4_shift_'+str(shift),source_id='fv_M4_SS',climate_id='shift_'+str(shift),status='COMPLETED',Tmax_C=row['Tmax_C'],Delta_estimate_C=row['Delta_estimate_C'],shape=[48,48,30],horizon_captured=truth(row['horizon_captured']),S25_validation='NOT VALIDATED'),cfg,None,metrics_only=True)

    def cooling(self):
        base=ROOT/'docs/tuberias_f02';cat=self.latest_cat
        original=next((p for p in cat.get('plans',[]) if p['id']=='t8_eps100_base1'),{})
        c=self.cohort('tuberias-42','19 noviembre · tuberías / sin tuberías · 42 días',cat,days=42,engine='a20109b · modelo tuberías (fingerprint no publicado en esta tabla)');c['expected']=[dict(cat['scenarios'][-1],weight='1')] if cat else []
        for r in read(base/'resultados.json',[]):
            case=r['caso'];cfg=read(base/(case+'_config.json'));plan=dict(original,id=case,name='Candidato '+('con tuberías' if case=='con_tuberias' else 'sin tuberías'))
            raw=dict(status='COMPLETED',simulation_id=r['simulation_id'],scenario_id=c['expected'][0]['id'],source_id='fv_M4_SS',climate_id=cat['climates'][0]['id'],weight='1',Tmax_C=r['Tmax_C'],Delta_estimate_C=r['Delta_S25_estimado_C'],Tmax_time_h=r['t_Tmax_h'],Delta_time_h=r['t_Delta_h'],numerical_checks=False,horizon_captured=False,S25_validation='NOT VALIDATED',coverage_air_min_fraction=1. if r['S25_completo'] else None,shape=cfg['n'],dt_s=cfg['dt'])
            folder=self.local_output/r['simulation_id'];self.add(c,plan,raw,cfg,folder,doc_history=f'docs/tuberias_f02/{case}_historia.csv')

    def closure(self):
        base=ROOT/'resultados/cierre_f02';cat=read(base/'catalogo_congelado.json')
        published=ROOT/'docs/cierre_f02/evidencia'
        if not cat:cat=read(published/'catalogo_congelado.json')
        if not cat:return
        plans={p['id']:p for p in cat['plans']}
        records=read(base/'progreso.json')
        if records is None:records=rows(published/'tabla_corridas.csv')
        for original in records:
            r=dict(original)
            r['shape']=r.get('shape') if isinstance(r.get('shape'),list) else read_value(r.get('shape'))
            r['days']=number(r.get('days'))
            if r.get('plan_id') not in plans:continue
            key='cierre-'+digest([r.get('engine_fingerprint'),r.get('shape'),r.get('days')])[:12]
            c=self.cohort(key,'Cierre F02 · clima fijo 19 noviembre · '+str(r.get('days'))+' días',cat,
                          days=r.get('days'),engine=r.get('engine_fingerprint'))
            folder=safe_folder(r.get('snapshot_folder'));cfg=read(folder/'config.json') if folder else None
            if cfg is None:cfg=op_config(cat,plans[r['plan_id']],r['source_id'],r.get('shape'),r['days'],number(r.get('dt_s')))
            self.add(c,plans[r['plan_id']],r,cfg,folder)

    def local(self):
        # Corridas propias se conservan como casos individuales sin inventar D ni pesos.
        known={r.get('simulation_id') for r in self.runs.values()}
        for file in self.local_output.glob('*/metadata.json'):
            if file.parent.name in known:continue
            m=read(file,{})
            if not isinstance(m,dict) or m.get('config',{}).get('geometry')!='foundation':continue
            p=m['config'];source=p.get('construction',{}).get('curve',{}).get('column','didáctica');ident=m.get('simulation_id')
            if not ident:continue
            retired=p.get('construction',{}).get('curve',{}).get('raw_sha256')==RETIRADA_PINN_SHA256
            key='local-'+digest([retired,p.get('n'),p.get('days'),m.get('commit'),m.get('provenance',{}).get('ifc'),p.get('weather',{}).get('start_utc')])[:12]
            c=self.cohort(key,('Antecedente PINN retirado · ' if retired else 'Corridas locales · ')+str(p.get('n'))+' · '+str(p.get('days'))+' días',days=p.get('days'),engine=m.get('commit'));c['expected']=[]
            if retired:c['historical']=True
            metrics=m.get('metrics',{});s=m.get('s25_ifc',{});peak=s.get('peak_estimate',{})
            plan=dict(id=ident,name='Corrida propia '+ident[:8],D_h=None,operations=[])
            r=dict(simulation_id=ident,status=m.get('status'),source_id=source,scenario_id=ident,climate_id=p.get('weather',{}).get('start_utc','constante'),Tmax_C=metrics.get('maxField'),Tmax_time_h=(metrics.get('global_peak_time_s') or 0)/3600,Delta_estimate_C=peak.get('DeltaT_estimate_C'),Delta_time_h=peak.get('time_s',0)/3600,S25_validation=s.get('validation'),shape=p['n'],dt_s=metrics.get('dt'),peak_S25=peak)
            self.add(c,plan,r,p,file.parent)

    def _summarize(self):
        for c in self.cohorts.values():
            for p in c['plans'].values():
                rr=[self.runs[k] for k in p['runs']]
                p['risk']=aggregate(rr,c['expected']);p['evaluated']=len(rr);p['expected']=len(c['expected'])
                p['estimated_risk']=aggregate_estimated(rr,c['expected'])
                p['Tmax_C']=max((r['Tmax_C'] for r in rr if r['Tmax_C'] is not None),default=None)
                p['Delta_estimate_C']=max((r['Delta_estimate_C'] for r in rr if r['Delta_estimate_C'] is not None),default=None)
                p['configuration_id']=digest([r.get('configuration_hash') or digest(r.get('_config')) for r in rr])[:16]

    def public(self):
        clean=lambda r:{k:v for k,v in r.items() if not k.startswith('_')}
        cohorts=[]
        for c in self.cohorts.values():
            plans=[dict({k:v for k,v in p.items() if not k.startswith('_')},runs=[clean(self.runs[k]) for k in p['runs']]) for p in c['plans'].values()]
            cohorts.append(dict({k:v for k,v in c.items() if not k.startswith('_')},plans=plans,pending_configurations=self.pending(c['id'])))
        counts=dict(cohorts=len(cohorts),plan_groups=sum(len(c['plans']) for c in self.cohorts.values()),scenario_rows=len(self.runs),unique_identified_executions=len({r['simulation_id'] for r in self.runs.values() if r.get('simulation_id')}),rows_without_execution_id=sum(not r.get('simulation_id') for r in self.runs.values()))
        return dict(version='1.0',counts=counts,cohorts=cohorts,warning='S25 ESTIMADO / NO VALIDADO. Probabilidades condicionadas a catálogos provisionales; no certifican riesgo de obra.')

    def pending(self,cohort_id):
        c=self.cohorts[cohort_id]
        if not c.get('_catalog'):return []
        reference=read(ROOT/'docs/defensa/evidencia/catalogo_congelado.json',{})
        available={p['id']:p for p in reference.get('plans',[])}
        available.update({p['id']:p for p in c['_catalog'].get('plans',[])})
        return [dict(id=k,name=available[k]['name'],D_h=available[k]['D_h']) for k in ('continua','propuesto','rapido','lento') if k not in c['plans'] and k in available]

    def prepare(self,cohort_id,plan_id):
        c=self.cohorts.get(cohort_id)
        if not c or plan_id not in [p['id'] for p in self.pending(cohort_id)]:raise ValueError('Plan pendiente no definido en los catálogos.')
        cat=c['_catalog'];reference=read(ROOT/'docs/defensa/evidencia/catalogo_congelado.json',{})
        definition=next((p for p in cat.get('plans',[]) if p['id']==plan_id),None) or next(p for p in reference['plans'] if p['id']==plan_id)
        representative=self.runs[next(iter(c['plans'].values()))['runs'][0]]
        source=next((s['source_id'] for s in c['expected'] if 'M4_SS' in s['source_id']),c['expected'][0]['source_id'])
        config=op_config(cat,definition,source,representative['shape'],days=c['days'],dt=representative['dt_s'])
        if config is None:raise ValueError('Configuración no recuperable.')
        return dict(config=config,plan=definition,source_id=source,note='Se recupera un cronograma existente con el clima, malla y horizonte de este conjunto. La ejecución usará el código actual y será una nueva corrida. Preparación de una fuente; el resto de escenarios sigue pendiente.')

    def get(self,uid):
        if uid not in self.runs:raise ValueError('Corrida no encontrada en el catálogo.')
        return self.runs[uid]

    def artifact(self,ident,name):
        if name not in ('metadata.json','config.json','fields.bin','active.bin','campos.npz','s25_ifc_history.csv'):return None
        for r in self.runs.values():
            if r.get('simulation_id')!=ident:continue
            folder=r.get('_folder')
            if folder and (folder/name).is_file():return folder/name
        return None

    def detail(self,uid):
        r=self.get(uid);folder=r.get('_folder');m=read(folder/'metadata.json',{}) if folder else {}
        config=m.get('config') or r.get('_config');s=m.get('s25_ifc',{});h=m.get('history',[]);history=[]
        if s.get('history'):
            history=[dict(time_s=v['time_s'],Tmax_C=v['Tmax_C'],Tmin_S25_C=v.get('Tmin_S25_estimate_C'),Delta_C=v.get('DeltaT_estimate_C')) for v in s['history']]
        elif r.get('doc_history'):
            for v in rows(ROOT/r['doc_history']):
                history.append(dict(time_s=number(v.get('time_s',v.get('t'))),Tmax_C=number(v.get('Tmax_C',v.get('max'))),Tmin_S25_C=number(v.get('Tmin_S25_estimate_C')),Delta_C=number(v.get('DeltaT_estimate_C'))))
        elif h:history=[dict(time_s=v['t'],Tmax_C=v['max'],Tmin_S25_C=None,Delta_C=None) for v in h]
        if history and r.get('days'):history=[v for v in history if v['time_s'] is not None and v['time_s']<=r['days']*86400+1e-7]
        fixed=[]
        if r.get('fixed_points'):
            points={}
            for v in rows(ROOT/r['fixed_points']):
                points.setdefault(v['punto'],dict(name=v['punto'],position=read_value(v['xyz_m']),kind='centro de celda fijo; NO S25',values=[]))['values'].append([number(v['tiempo_h'])*3600,number(v['T_C'])])
            fixed=list(points.values())
        if m and folder:
            fixed.extend(fixed_histories(m,folder))
        if not fixed and r.get('doc_history') and config and config.get('n'):
            raw_history=rows(ROOT/r['doc_history'])
            if raw_history and 'center' in raw_history[0]:
                n=config['n'];position=[o+(v//2+.5)*L/v for o,L,v in zip(config.get('origin',[0,0,0]),config['L'],n)]
                fixed.append(dict(name='Interior fijo · centro del dominio',position=position,kind='Centro del voxel definido por el solver; historia CSV archivada, NO envolvente',values=[[number(v.get('t')),number(v.get('center'))] for v in raw_history]))
        if r.get('days'):
            for point in fixed:point['values']=[v for v in point['values'] if v[0]<=r['days']*86400+1e-7]
        peak=s.get('critical_pair');fallback=r.get('peak_S25');plan=self.cohorts[r['cohort_id']]['plans'][r['plan_id']]
        available=not r.get('partial_horizon') and bool(folder and m.get('simulation_id')==r.get('simulation_id') and (folder/'fields.bin').is_file() and (m.get('geometry',{}).get('active_static') is not False or (folder/'active.bin').is_file()))
        metric=m.get('metrics',{});hot=metric.get('hottest_xyz');xyz=None
        if hot and m.get('geometry'):xyz=[o+(i+.5)*dx for o,i,dx in zip(m['geometry']['origin_m'],hot,m['geometry']['spacing_m'])]
        return dict(run={k:v for k,v in r.items() if not k.startswith('_')},plan=plan,history=history,fixed=fixed,critical_pair=peak,peak_S25=fallback,
            max_xyz=xyz or r.get('max_xyz'),fields_available=available,config_available=config is not None and not r.get('retired'),
            field_horizon_days=m.get('config',{}).get('days'),metadata=m if available else None,
            curve_warning='Historias de sensores fijos sólo cuando existen. Tmin S25 es una envolvente móvil; no un sensor fijo. Centros exteriores no equivalen a 25 mm.',
            config=config,archive_figure='tuberias' if r['cohort_id']=='tuberias-42' else None)


def read_value(v):
    if isinstance(v,(dict,list)):return v
    try:return json.loads(v) if v else None
    except (ValueError,TypeError):return None


def fixed_histories(meta,folder):
    """Extraer centros reales y reutilizar el stencil MLS ya exportado, sin solver."""
    import numpy as np
    g=meta['geometry'];n=g['shape_xyz'];out=[];times=meta['fields']['times_s'];count=math.prod(n)
    path=folder/'fields.bin'
    if not path.is_file() or path.stat().st_size!=len(times)*count*4:return []
    fields=np.memmap(path,dtype='<f4',mode='r',shape=(len(times),count))
    active=None
    if g.get('active_static') is False:
        ap=folder/'active.bin'
        if not ap.exists() or ap.stat().st_size!=len(times)*count:return []
        active=np.memmap(ap,dtype='u1',mode='r',shape=(len(times),count))
    ijk=[v//2 for v in n];idx=ijk[0]+n[0]*(ijk[1]+n[1]*ijk[2]);pos=[o+(i+.5)*h for o,i,h in zip(g['origin_m'],ijk,g['spacing_m'])]
    vals=[[t,float(fields[j,idx]) if (active is None or active[j,idx]) and (not g.get('cell_ids') or g['cell_ids'][idx]) else None] for j,t in enumerate(times)]
    out.append(dict(name='Interior fijo · centro del dominio',position=pos,kind='Centro de voxel, NO máximo móvil',values=vals))
    s=meta.get('s25_ifc',{});pair=s.get('critical_pair',{});stencil=pair.get('reconstruction',{});indices=stencil.get('neighbors_ijk');weights=stencil.get('weights')
    if indices and weights and stencil.get('supported') and len(indices)==len(weights):
        ids=np.array([i+n[0]*(j+n[1]*k) for i,j,k in indices]);w=np.array(weights)
        stages=meta.get('construction',{}).get('snapshots',[]);critical=next((h for h in s.get('history',[]) if abs(h['time_s']-pair['time_s'])<1e-6),{}).get('active_pours')
        if critical is not None and stages:
            values=[]
            for j,t in enumerate(times):
                same=sorted(stages[j]['active_pour_ids'])==sorted(critical)
                ok=same and (active is None or np.all(active[j,ids]))
                values.append([t,float(fields[j,ids]@w) if ok else None])
            out.append(dict(name='S25 fijo · punto del par crítico',position=pair['cold']['xyz_m'],kind='Reconstrucción MLS ESTIMADA a 25 mm; stencil guardado, sólo misma etapa constructiva que el par crítico',values=values))
    del fields
    if active is not None:del active
    return out


def signature(local_output):
    files=list((ROOT/'docs/exploracion/evidencia').glob('*.csv'))+list((ROOT/'docs/exploracion/evidencia').glob('*catalogo*.json'))+list((ROOT/'docs/defensa/evidencia').glob('tabla_corridas.csv'))+list((ROOT/'docs/mejoras_f02').glob('*.csv'))+list((ROOT/'docs/mejoras_f02').glob('*.json'))+list((ROOT/'docs/defensa/evidencia').glob('catalogo*.json'))+list((ROOT/'docs/tuberias_f02').glob('*.json'))+list(Path(local_output).glob('*/metadata.json'))
    files+=list((ROOT/'resultados/cierre_f02').glob('*.json'))
    files+=list((ROOT/'docs/cierre_f02/evidencia').glob('*.json'))+list((ROOT/'docs/cierre_f02/evidencia').glob('*.csv'))
    return tuple((str(f),f.stat().st_mtime_ns) for f in files)

@lru_cache(maxsize=2)
def _load(local_output,stamp):return Evidence(local_output)

def load(local_output=None):
    local_output=str(local_output or ROOT/'resultados/servidor_therma')
    return _load(local_output,signature(local_output))
