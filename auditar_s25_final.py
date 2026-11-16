"""Audita evidencia S25 sin rellenar puntos ni modificar corridas/tabla de riesgo."""
import argparse,json,csv,sys
from pathlib import Path
import numpy as np
from therma.lotes import write_json,write_csv,ROOT
from therma.superficies_ifc import cargar_superficies,SuperficiesIFC
from therma.reconstruccion_s25 import Reconstruccion
from therma.auditoria_geometrica import distancia_aristas


def main(study,output):
    p=ROOT/'modelo_e02.ifc';g=cargar_superficies(str(p),p.stat().st_mtime_ns,1.5)
    summaries=[];coverage=[];unknowns=[];critical=[]
    for case in sorted(study.glob('case_*')):
        meta=json.loads((case/'metadata.json').read_text(encoding='utf-8'));d=meta['s25_ifc'];dx=meta['geometry']['spacing_m']
        for j,stage in enumerate(d['stages']):
            ids=tuple(stage['active_pours']);s=g.at(ids)
            for row in stage['coverage_by_area']:
                coverage.append(dict(case=case.name,spacing_x_m=dx[0],active_pours=str(ids),**row))
            points=list(csv.DictReader((case/stage['points_file']).open(encoding='utf-8-sig')))
            missing=[r for r in points if r['reconstruction_available']=='False']
            details_path=case/f's25_unknown_{j}.csv'
            details=list(csv.DictReader(details_path.open(encoding='utf-8-sig'))) if details_path.exists() else []
            for row,detail in zip(missing,details):
                xyz=np.array([float(row[a]) for a in 'xyz']);surf=np.array([float(row['surface_'+a]) for a in 'xyz']);n=np.array([float(row['n'+a]) for a in 'xyz'])
                solid=next(v for v in g.solids if v['VertidaID']==int(row['surface_pour_id']))
                edge=distancia_aristas(surf,solid)
                unknowns.append(dict(case=case.name,stage=j,active_pours=str(ids),**detail,
                    inside_active=bool(g.inside([xyz],ids)[0]),outward_probe_inside=bool(g.inside([surf+1e-5*n],ids)[0]),
                    normal_length=float(np.linalg.norm(n)),normal_offset_m=float(np.linalg.norm(xyz-surf)),
                    distance_to_feature_edge_m=edge['distance_to_feature_edge_m'],
                    distance_to_V1_top_m=abs(float(xyz[2])-1.1),
                    diagnosis='Thin V2 staircase: same-pour centers are coplanar; normal derivative not identifiable from centers alone.'))
        final=d['stages'][-1];areas=final['coverage_by_area'];total=sum(v['area_m2'] for v in areas);computed=sum(v['computed_area_m2'] for v in areas)
        air=[v for v in areas if v['region']=='air'];airtotal=sum(v['area_m2'] for v in air);aircomputed=sum(v['computed_area_m2'] for v in air)
        c=d['critical_pair'];r=c['reconstruction'];window=c['temporal_audit']['near_peak']
        critical.append(dict(case=case.name,spacing_x_m=dx[0],time_h=c['time_s']/3600,
            Tmax_same_time_C=c['hot']['temperature_C'],hot_xyz_m=c['hot']['xyz_m'],hot_ijk=c['hot']['ijk'],hot_pour=c['hot']['pour_id'],
            Tmin_S25_C=c['cold']['temperature_C'],S25_xyz_m=c['cold']['xyz_m'],cold_pour=c['cold']['point_pour_id'],
            DeltaT_estimate_C=c['hot']['temperature_C']-c['cold']['temperature_C'],distance_IFC_m=c['geometry']['nearest_exterior_distance_m'],
            triangle_id=c['cold']['triangle_id'],guid=c['cold']['guid'],neighbors=len(r['neighbors_ijk']),degree=r['degree'],
            condition=r['condition'],weights_l1=r['weights_l1'],fit_RMSE_C=r['fit_rmse_C'],fit_max_residual_C=r['fit_max_residual_C'],
            staircase_area_factor=c['boundary']['staircase_area_factor'],
            nearest_cell_m=r['nearest_cell_m'],feature_edge_distance_m=c['geometry']['feature_edge']['distance_to_feature_edge_m'],
            same_cold_index_near_peak=len({v['cold_sample_index'] for v in window})==1,
            max_neighboring_delta_change_C=max(abs(a['DeltaT_estimate_C']-b['DeltaT_estimate_C']) for a,b in zip(window,window[1:])),
            activation_distance_h=c['temporal_audit']['activation_distance_h'],validated=False))
        write_csv(output/f'{case.name}_critical_neighbors.csv',[dict(i=v[0],j=v[1],k=v[2],x=w[0],y=w[1],z=w[2],temperature_C=T,weight=weight) for v,w,T,weight in zip(r['neighbors_ijk'],r['neighbors_xyz_m'],r['neighbors_temperature_C'],r['weights'])])
        summaries.append(dict(case=case.name,spacing_m=dx,missing_points=final['unsupported_points'],sample_count=final['points'],
            computed_area_percent=100*computed/total,computed_air_area_percent=100*aircomputed/airtotal,
            missing_area_m2=total-computed,thermal_validation='NOT VALIDATED',criterion='INDETERMINATE'))
    write_csv(output/'diagnostico_desconocidos.csv',unknowns);write_csv(output/'cobertura_superficies.csv',coverage)
    write_csv(output/'resumen_cobertura.csv',summaries);write_csv(output/'pares_criticos.csv',critical)
    # Valores analíticos: separa exactitud de reconstrucción y exactitud de la PDE.
    sys.path.insert(0,str(ROOT/'tests'))
    from test_s25_ifc_resolucion import transient_errors,cube,cylinder
    references=transient_errors('D',True)+transient_errors('R',True)
    for label,solid in [('inclined',cube(transform=[[1,0,0],[0,1,0],[.35,.2,1]])),('curved_faceted',cylinder()),('near_corner',cube())]:
        geom=SuperficiesIFC([solid],spacing=2.)
        for n in (6,10,16):
            lo=solid['vertices'].min(0);L=solid['vertices'].max(0)-lo;dx=L/n
            xyz=np.stack(np.meshgrid(*[lo[a]+(np.arange(n)+.5)*dx[a] for a in range(3)],indexing='ij'),axis=-1)
            active=geom.inside(xyz.reshape(-1,3),(1,)).reshape((n,)*3)
            points=np.array([[.025,.025,.025]]) if label=='near_corner' else geom.at((1,))['points']
            R=Reconstruccion(points,active,lo,dx,allow_partial=True)
            f=lambda x:20+x[...,0]+x[...,1]**2-.3*x[...,2]
            err=np.abs(R.evaluate(f(xyz))-f(points));finite=np.isfinite(err)
            references.append(dict(boundary=label,n=n,dx_m=float(max(dx)),total_error_C=None,
                reconstruction_only_error_C=float(np.max(err[finite])),propagated_solver_error_C=None,
                mean_absolute_reconstruction_error_C=float(np.mean(err[finite])),unknown=int((~finite).sum()),
                scope='Known quadratic field only; not validation of curved/inclined PDE boundary flux.'))
    write_csv(output/'errores_referencia.csv',references)
    report=dict(coverage=summaries,critical_pairs=critical,unknown_records=len(unknowns),
        references=references,assessment=dict(A_validated_exceedance='NOT DEMONSTRATED: no validated error bound for IFC field.',
        B_exceedances_excluded='NO: missing points, finite surface quadrature and unbounded boundary/field error.',
        status='INDETERMINATE',risk_table_updated=False))
    write_json(output/'auditoria.json',report);print(json.dumps(dict(coverage=summaries,assessment=report['assessment']),indent=2))

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--estudio',type=Path,default=Path('resultados/validacion_s25_final/estudio'));p.add_argument('--salida',type=Path,default=Path('resultados/validacion_s25_final/auditoria'))
    a=p.parse_args();main(a.estudio,a.salida)
