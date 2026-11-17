"""Publica mediciones de sensibilidad sin convertirlas en una cota de error."""
import json
from estudiar_mallas_hielo import OUT, SPATIAL_TOLERANCE_C, TEMPORAL_TOLERANCE_C
from therma.hielo import ROOT
from therma.lotes import write_json,write_csv


def main():
    coverage=json.loads((OUT/'cobertura.json').read_bytes())
    records=[json.loads(p.read_bytes()) for p in OUT.glob('T*.json')]
    rows=[]
    for r in records:
        geo=next((g for g in coverage if g['shape']==r['shape']),{})
        rows.append(dict(temperature_C=r['temperature_C'],source_id=r['source_id'],shape=r['shape'],spacing_m=r['spacing_m'],
            cells_total=geo.get('total_cells'),cells_active=geo.get('active_cells'),dt_s=r['dt_requested_s'],
            Tmax_C=r['Tmax_C'],Delta_C=r['Delta_estimate_C'],unknown=r['missing_points_max'],
            volume_error_pct=geo.get('volume_error_pct'),coverage=r['coverage_air_min_fraction'],
            energy_residual_relative=r['energy_residual_relative'],stable=r['numerical_checks'],
            horizon_captured=r['horizon_captured'],engine=r['engine_fingerprint'],runtime_s=r['runtime_s']))
    rows.sort(key=lambda r:(r['temperature_C'],r['cells_total'] or 0,-r['dt_s']))
    assessments=[]
    for temperature in (8,12):
        cases=[r for r in rows if r['temperature_C']==temperature and r['dt_s']==1200 and r['shape'] in [[72,72,42],[84,84,48],[90,90,48]] and r['source_id']=='fv_M4_SS']
        temporal=next((r for r in rows if r['temperature_C']==temperature and r['shape']==[90,90,48] and r['dt_s']==1800 and r['source_id']=='fv_M4_SS'),None)
        if len(cases)!=3:
            assessments.append(dict(temperature_C=temperature,status='PENDING'));continue
        middle,fine=cases[-2:]
        spatial={k:abs(fine[k]-middle[k]) for k in ('Tmax_C','Delta_C')}
        time_error={k:abs(fine[k]-temporal[k]) for k in ('Tmax_C','Delta_C')} if temporal else None
        passed=all(v<=SPATIAL_TOLERANCE_C for v in spatial.values()) and temporal is not None and all(v<=TEMPORAL_TOLERANCE_C for v in time_error.values())
        assessments.append(dict(temperature_C=temperature,spatial_change_C=spatial,temporal_change_C=time_error,
                                status='SENSITIVITY_WITHIN_DECLARED_TOLERANCES' if passed else 'TOLERANCE_NOT_DEMONSTRATED'))
    result=dict(rows=rows,assessments=assessments,spatial_tolerance_C=SPATIAL_TOLERANCE_C,temporal_tolerance_C=TEMPORAL_TOLERANCE_C,
                note='Comparaciones del mismo caso M4_SS. Diferencias observadas, sin cota del error físico ni extrapolación de Richardson. Superficie FV escalonada y S25 no validado.')
    write_json(ROOT/'docs/hielo_f02/estudio_mallas.json',result)
    write_csv(OUT/'tabla_estudio.csv',rows)
    print(assessments,flush=True)


if __name__=='__main__':
    main()
