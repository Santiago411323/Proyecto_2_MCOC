"""Publica benchmarks verificables y separa reconstrucción, solver y geometría."""
import argparse
import json
import sys
from pathlib import Path
import numpy as np
from therma.lotes import write_json,write_csv,ROOT
from therma.superficies_ifc import SuperficiesIFC,cargar_superficies
from therma.reconstruccion_s25 import Reconstruccion


def main(output,study):
    # Reutiliza los mismos casos de control de la batería; no duplica un solver.
    sys.path.insert(0,str(ROOT/'tests'))
    from test_s25_ifc_resolucion import transient_errors,cylinder
    rows=transient_errors('D',details=True)+transient_errors('R',details=True)
    write_csv(output/'errores_reconstruccion_y_solver.csv',rows)
    geometry=[]
    for n in (32,64,128):
        g=SuperficiesIFC([cylinder(n)],spacing=2.)
        s=g.at((1,));side=np.abs(s['outward'][:,2])<.1
        true_depth=1-np.linalg.norm(s['points'][side,:2],axis=1)
        geometry.append(dict(facets=n,depth_m=.025,depth_error_vs_analytic_cylinder_max_m=float(np.max(np.abs(true_depth-.025))),
                             faceting_sagitta_bound_m=float(1-np.cos(np.pi/n))))
    write_csv(output/'error_geometrico_cilindro.csv',geometry)
    p=ROOT/'modelo_e02.ifc';g=cargar_superficies(str(p),p.stat().st_mtime_ns,1.5)
    stages=[]
    for ids in ((1,),(1,2),(1,2,3)):
        s=g.at(ids)
        stages.append(dict(active_pours=list(ids),samples=len(s['points']),
                           normal_offset_error_max_m=float(np.max(np.abs(np.linalg.norm(s['points']-s['surface'],axis=1)-.025))),
                           rejected_points=s['rejected_not_in_active_concrete'],excluded_internal=s['excluded_internal'],
                           soil_points=int(np.sum(s['region']=='soil')),air_points=int(np.sum(s['region']=='air'))))
    write_csv(output/'geometria_ifc_estados.csv',stages)
    quadrature=[]
    field_folder=study/'case_02'
    if (field_folder/'campos.npz').exists():
        meta=json.loads((field_folder/'metadata.json').read_text(encoding='utf-8'))
        with np.load(field_folder/'campos.npz') as z:
            T=z['T_C'][-1];active=z['active'][-1];t=float(z['tiempo_s'][-1]);ids=z['pour_ids']
        for pitch in (2.5,2.,1.5):
            geom=cargar_superficies(str(p),p.stat().st_mtime_ns,pitch);s=geom.at((1,2,3))
            reconstruction=Reconstruccion(s['points'],active,meta['geometry']['origin_m'],meta['geometry']['spacing_m'],cell_ids=ids,point_ids=s['point_owner'],allow_partial=True)
            values=reconstruction.evaluate(T)
            quadrature.append(dict(surface_spacing_m=pitch,samples=len(values),time_h=t/3600,
                                   unsupported_points=int(np.sum(~np.isfinite(values))),
                                   Tmin_S25_estimate_C=float(np.nanmin(values)),Delta_at_final_estimate_C=float(T[active].max()-np.nanmin(values)),
                                   note='Mismo campo final; no es máximo temporal ni cota del mínimo continuo.'))
        write_csv(output/'sensibilidad_muestreo_superficie.csv',quadrature)
    result=dict(official_validation='NOT VALIDATED',probability='NOT FULLY EVALUATED',compliance='INDETERMINATE',
                analytic_rows=rows,geometry_rows=geometry,ifc_stages=stages,quadrature_rows=quadrature,
                limitations=['Normales de triángulos IFC, sin afirmar equivalencia con una superficie curva analítica.',
                             'Errores reconstrucción y propagación de error FV separados sólo en casos analíticos.',
                             'No hay cota de error 3D para S25 en la fundación ni convergencia garantizada del mínimo superficial.'])
    write_json(output/'validacion_s25_ifc.json',result)
    print(json.dumps(result,ensure_ascii=False,indent=2))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--salida',type=Path,default=Path('resultados/validacion_s25_ifc'))
    p.add_argument('--estudio',type=Path,default=Path('resultados/convergencia_s25_ifc'))
    args=p.parse_args();main(args.salida,args.estudio)
