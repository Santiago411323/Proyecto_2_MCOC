"""Lotes secuenciales del motor oficial, cache verificable y tablas sin ceros ficticios."""
import copy
import csv
import hashlib
import json
from pathlib import Path
import subprocess
from datetime import datetime, timezone
import numpy as np
from .ejecutar import ejecutar, validar, ROOT
from .s25 import ObservadorS25, METHOD
from .riesgo import resumen_riesgo


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False).encode('utf-8')


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonical(value))


def write_csv(path, rows):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        return
    keys = list(dict.fromkeys(k for r in rows for k in r))
    with path.open('w', encoding='utf-8-sig', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=keys)
        writer.writeheader()
        for row in rows:
            writer.writerow({k: json.dumps(v, ensure_ascii=False) if isinstance(v, (list, dict)) else v for k, v in row.items()})


def fingerprint():
    files = sorted((ROOT/'therma').glob('*.py')) + [ROOT/'termico_cartesiano.py', ROOT/'voxelizar.py', ROOT/'panel/exportar_ifc.py']
    return hashlib.sha256(canonical({str(f.relative_to(ROOT)): sha(f) for f in files})).hexdigest()


def validar_catalogo(cat):
    if cat.get('version') != 1 or not cat.get('weight_rationale'):
        raise ValueError('Versión y justificación previa de pesos requeridas.')
    for key in ('plans', 'sources', 'climates', 'scenarios'):
        ids = [v['id'] for v in cat[key]]
        if not ids or len(ids) != len(set(ids)):
            raise ValueError('Identificadores únicos en '+key)
    sources = {s['id'] for s in cat['sources']}
    climates = {s['id'] for s in cat['climates']}
    pairs = [(s['source_id'], s['climate_id']) for s in cat['scenarios']]
    if len(set(pairs)) != len(pairs) or set(pairs) != {(s,c) for s in sources for c in climates}:
        raise ValueError('Enumerar exactamente todo el producto de fuentes y climas.')
    resumen_riesgo([dict(scenario_id=s['id'], weight=s['weight'], status='PENDING') for s in cat['scenarios']])
    for plan in cat['plans']:
        operations = plan['operations']
        if plan['rate_m3_h'] <= 0 or len(operations) != 3:
            raise ValueError('Tasa positiva y tres partes IFC.')
        if {o['id'] for o in operations} != {1,2,3}:
            raise ValueError('Conservar IDs de las tres piezas IFC.')
        last = 0.
        for o in operations:
            if o['start_h'] < last-1e-9 or o['end_h'] <= o['start_h']:
                raise ValueError('Un único equipo: no solapar colocaciones.')
            if abs((o['end_h']-o['start_h'])*plan['rate_m3_h']-o['volume_m3']) > 1e-6:
                raise ValueError('Duración de colocación inconsistente con tasa y volumen.')
            last = o['end_h']
        if abs(plan['D_h']-last) > 1e-8 or operations[0]['start_h'] != 0:
            raise ValueError('D desde t0 común hasta fin físico de colocación.')
    volumes = [sum(o['volume_m3'] for o in p['operations']) for p in cat['plans']]
    if max(volumes)-min(volumes) > 1e-6:
        raise ValueError('Misma geometría y volumen final en todos los planes.')


def preparar_config(cat, plan, scenario, mesh=None, dt=None):
    sources = {s['id']:s for s in cat['sources']}
    climates = {s['id']:s for s in cat['climates']}
    source = sources[scenario['source_id']]
    climate = climates[scenario['climate_id']]
    p = copy.deepcopy(cat['base_config'])
    for key,value in plan.get('physical_overrides',{}).items():
        if key not in ('faces','formwork'):raise ValueError('Override físico no permitido: '+key)
        if value is None:p.pop(key,None)
        else:p[key]=copy.deepcopy(value)
    p['weather'] = copy.deepcopy(climate['weather'])
    p['construction'] = dict(model='tabulated_source', curve=copy.deepcopy(source['curve']),
        parameter_source=source['provenance'], pours=[dict(id=o['id'], start_h=o['start_h'], placement_C=plan['placement_C']) for o in plan['operations']])
    if mesh is not None:
        p['meshIndex']=2
        p['n']=list(mesh)
    if dt is not None:
        p.update(dtMode='manual',dt=float(dt))
    return validar(p)


def run_one(config, cache_root):
    if config.get('s25'):
        from .lotes_ifc import run_ifc
        return run_ifc(config,cache_root)
    key = hashlib.sha256(canonical(dict(config=config, engine=fingerprint(), ifc=sha(ROOT/'modelo_e02.ifc'), metric=METHOD))).hexdigest()
    folder = Path(cache_root)/key
    cached = folder/'batch_result.json'
    if cached.exists():
        record = json.loads(cached.read_text(encoding='utf-8'))
        if record.get('cache_key') == key and record.get('status') == 'COMPLETED' and all((folder/name).is_file() and sha(folder/name)==digest for name,digest in record['artifacts'].items()):
            return dict(record, reused=True)
    observer=ObservadorS25()
    try:
        metadata=ejecutar(config,key[:32],folder,observer=observer)
        metric=metadata['metrics']
        rows=observer.rows
        if not rows:
            raise ValueError('Sin observaciones de hormigón activo.')
        # Revisar también un pico tardío de Delta: no sólo Tmax.
        end=config['days']*86400
        latest_pour=max(v['start_h'] for v in config['construction']['pours'])*3600
        final_rising=len(rows)>1 and rows[-1]['Tmax_C']>rows[-2]['Tmax_C']+1e-6
        late=max(metric['global_peak_time_s'],observer.peak['time_s']) >= end-24*3600
        captured=not (final_rising or late or end-latest_pour<72*3600)
        stable=metric['dt'] <= metric['dtMax']*(1+1e-12)
        numerical=stable and metric['energy_residual_relative']<1e-10
        record=dict(status='COMPLETED',cache_key=key,reused=False,simulation_id=metadata['simulation_id'],
            Tmax_C=metric['maxField'],Tmax_time_h=metric['global_peak_time_s']/3600,
            Delta_estimate_C=observer.peak['Delta_estimate_C'],Delta_time_h=observer.peak['time_s']/3600,
            S25_validation=observer.validation,DeltaTmax_C=None,I_Delta=None,
            I_T=bool(metric['maxField']>70) if captured and numerical else None,
            I_Delta_estimate=bool(observer.peak['Delta_estimate_C']>20),
            horizon_captured=captured,numerical_checks=numerical,energy_residual_relative=metric['energy_residual_relative'],
            runtime_s=metric['runtime_s'],dt_s=metric['dt'],dt_limit_s=metric['dtMax'],
            shape=config['n'],spacing_m=metadata['geometry']['spacing_m'],volume_m3=metric['volume'],
            snapshot_folder=str(folder.resolve()),code_sha=metadata['commit'],peak_S25=observer.peak,
            assumption='Instantaneous activation at start of each placement; physical duration accounted separately.')
        write_csv(folder/'history_s25.csv',rows)
        write_json(folder/'s25_diagnostic.json',dict(method=METHOD,validation=observer.validation,peak=observer.peak))
        T,active,ids=observer.peak_field
        np.savez_compressed(folder/'s25_peak.npz',T_C=T,active=active,pour_ids=ids,time_s=observer.peak['time_s'])
        record['extension_required']=not captured
        record['artifacts']={name:sha(folder/name) for name in ('metadata.json','config.json','campos.npz','fields.bin','active.bin','history_s25.csv','s25_diagnostic.json','s25_peak.npz')}
        write_json(cached,record)
        return record
    except Exception as error:
        folder.mkdir(parents=True,exist_ok=True)
        record=dict(status='FAILED',cache_key=key,error=str(error),I_T=None,I_Delta=None,snapshot_folder=str(folder.resolve()))
        write_json(folder/'failed.json',record)
        return record


def resumir(cat, records):
    result=[]
    for plan in cat['plans']:
        selected=[r for r in records if r['plan_id']==plan['id']]
        risk=resumen_riesgo(selected)
        exploratory=resumen_riesgo([dict(r,I_Delta=r.get('I_Delta_estimate') if r.get('horizon_captured') and r.get('numerical_checks') else None) for r in selected])
        result.append(dict(plan_id=plan['id'],Plan=plan['name'],D_h=plan['D_h'],**risk,
                           P_f_exploratory=exploratory['P_f'],P_Delta_exploratory=exploratory['P_Delta'],
                           scope=cat['probability_scope']))
    return result


def export_tables(output, summaries, records):
    output=Path(output)
    write_csv(output/'tabla_corridas.csv',records)
    write_json(output/'tabla_corridas.json',records)
    write_json(output/'resumen_planes.json',summaries)
    table=[]
    def percent(value):return 'NO EVALUADO' if value is None else f'{100*value:.6g}'
    for row in summaries:
        table.append({'Plan':row['Plan'],'D [h]':f"{row['D_h']:.4f}",'P_T [%]':percent(row['P_T']),
                      'P_Delta [%]':percent(row['P_Delta']),'P_f conjunta [%]':percent(row['P_f']),
                      '¿Cumple?':row['compliance']})
    write_csv(output/'tabla_planes.csv',table)
    columns=list(table[0])
    lines=['| '+' | '.join(columns)+' |','|'+'|'.join(['---']*len(columns))+'|']
    lines+=['| '+' | '.join(str(r[k]) for k in columns)+' |' for r in table]
    lines+=['','Probabilidades de EXCEDENCIA, condicionadas al catálogo y sus pesos declarados.',
            'S25: NOT VALIDATED. La columna conjunta no certifica cumplimiento.',
            'P_f_exploratory en resumen_planes.json usa S25 aproximado y NO es el criterio oficial.']
    (output/'tabla_planes.md').write_text('\n'.join(lines),encoding='utf-8')


def ejecutar_catalogo(cat, output, mesh=None, dt=None):
    validar_catalogo(cat)
    output=Path(output)
    output.mkdir(parents=True,exist_ok=True)
    frozen=dict(cat)
    frozen['execution_override']=dict(mesh=mesh,dt=dt)
    frozen['frozen_at_utc']=datetime.now(timezone.utc).isoformat()
    write_json(output/'catalogo_congelado.json',frozen)
    records=[]
    for plan in cat['plans']:
        for scenario in cat['scenarios']:
            print(plan['id'],scenario['id'],flush=True)
            try:
                config=preparar_config(cat,plan,scenario,mesh,dt)
                record=run_one(config,output/'cache')
            except Exception as error:
                record=dict(status='FAILED',error=str(error),I_T=None,I_Delta=None)
            record.update(plan_id=plan['id'],scenario_id=scenario['id'],weight=scenario['weight'],source_id=scenario['source_id'],climate_id=scenario['climate_id'])
            records.append(record)
            write_json(output/'progreso.json',records)
    summaries=resumir(cat,records)
    export_tables(output,summaries,records)
    feasible=[s for s in summaries if s['compliance']=='CUMPLE']
    write_json(output/'seleccion.json',dict(status='EVALUATED' if feasible else 'NO_VALIDATED_FEASIBLE_PLAN',
        best=min(feasible,key=lambda s:s['D_h']) if feasible else None,
        scope='Sólo familia enumerada; no óptimo global. S25 no validado impide recomendar.',
        executed=sum(not r.get('reused',False) for r in records),reused=sum(r.get('reused',False) for r in records)))
    return summaries,records
