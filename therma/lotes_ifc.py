"""Rama IFC del gestor de lotes: S25 real, estimado; sin probabilidades ficticias."""
import hashlib,json,time
from pathlib import Path
from .lotes import canonical,fingerprint,sha,ROOT,write_json,write_csv
from .ejecutar import ejecutar

METHOD='IFC_TRIANGLES_QUADRATIC_MLS_exploration_v1'

def run_ifc(config,cache_root):
    engine=fingerprint();key=hashlib.sha256(canonical(dict(config=config,engine=engine,ifc=sha(ROOT/'modelo_e02.ifc'),metric=METHOD))).hexdigest()
    folder=Path(cache_root)/key;cached=folder/'batch_result.json'
    if cached.exists():
        r=json.loads(cached.read_text(encoding='utf-8'))
        if r.get('status')=='COMPLETED' and r.get('cache_key')==key and all((folder/n).is_file() and sha(folder/n)==h for n,h in r.get('artifacts',{}).items()):return dict(r,reused=True)
    start=time.perf_counter()
    try:
        meta=ejecutar(config,key[:32],folder);m=meta['metrics'];s=meta['s25_ifc'];peak=s['peak_estimate'];rows=s['history'];end=config['days']*86400
        latest=max(v['start_h'] for v in config['construction']['pours'])*3600
        captured=not(rows[-1]['Tmax_C']>rows[-2]['Tmax_C']+1e-6 or max(m['global_peak_time_s'],peak['time_s'])>=end-86400 or end-latest<72*3600)
        valid=m['dt']<=m['dtMax']*(1+1e-12) and m['energy_residual_relative']<1e-10
        coverage=[]
        for stage in s['stages']:
            air=[v for v in stage['coverage_by_area'] if v['region']=='air'];total=sum(v['area_m2'] for v in air)
            coverage.append(sum(v['computed_area_m2'] for v in air)/total if total else 0.)
        record=dict(status='COMPLETED',cache_key=key,configuration_hash=hashlib.sha256(canonical(config)).hexdigest(),engine_fingerprint=engine,
            reused=False,simulation_id=meta['simulation_id'],Tmax_C=m['maxField'],Tmax_time_h=m['global_peak_time_s']/3600,
            Delta_estimate_C=peak['DeltaT_estimate_C'],Delta_time_h=peak['time_s']/3600,
            S25_validation=s['validation'],I_T=None,I_Delta=None,P_T=None,P_Delta=None,P_f=None,compliance='INDETERMINADO',
            observed_T_exceeds=bool(m['maxField']>70),observed_Delta_estimate_exceeds=bool(peak['DeltaT_estimate_C']>20),
            probability_note='No probabilidades con S25 no validado; recuentos térmicos sólo descriptivos. Fuentes y pesos provisionales.',
            coverage_air_min_fraction=min(coverage),coverage_by_stage=[v['coverage_by_area'] for v in s['stages']],
            missing_points_max=max(v['unsupported_points'] for v in rows),complete_sampling=s['complete_sampling'],
            horizon_captured=captured,extension_required=not captured,numerical_checks=valid,energy_residual_relative=m['energy_residual_relative'],
            runtime_s=m['runtime_s'],wall_time_s=time.perf_counter()-start,dt_s=m['dt'],dt_limit_s=m['dtMax'],
            shape=config['n'],spacing_m=meta['geometry']['spacing_m'],volume_m3=m['volume'],
            snapshot_folder=str(folder.resolve()),code_sha=meta['commit'],peak_S25=peak,
            boundary_model='Unchanged Cartesian staircase. IFC S25 sampling does not correct boundary heat flux.',
            assumption='Physical placement durations separate; thermal activation at start of each IFC piece.')
        record['artifacts']={n:sha(folder/n) for n in ('metadata.json','config.json','campos.npz','fields.bin','active.bin','s25_ifc.json','s25_ifc_history.csv','s25_ifc_critical.npz')}
        write_json(cached,record);return record
    except Exception as e:
        r=dict(status='FAILED',cache_key=key,error=str(e),I_T=None,I_Delta=None,P_f=None,snapshot_folder=str(folder.resolve()))
        write_json(folder/'failed.json',r);return r
