"""Repite el mismo caso candidato sin alterar propiedades entre refinamientos."""
import copy,json
from pathlib import Path
from therma.lotes import preparar_config,run_one,write_json,write_csv
from therma.cierre_f02 import evaluar_horizonte


def main():
    out=Path('resultados/cierre_f02/sensibilidad')
    cat=json.loads(Path('resultados/cierre_f02/catalogo_congelado.json').read_text(encoding='utf-8'))
    plan=next(p for p in cat['plans'] if p['id']=='t8_eps100_base1');scenario=cat['scenarios'][-1]
    results=[]
    for name,mesh,dt in [('500',[36,36,7],900.),('375',[48,48,9],900.),('250',[72,72,14],900.),('375_z110',[48,48,30],900.),('500_dt450',[36,36,7],450.)]:
        ccat=copy.deepcopy(cat);ccat['base_config']['days']=42.
        config=preparar_config(ccat,plan,scenario,mesh=mesh,dt=dt)
        config['environment']['soil']['contact_R_m2K_W']+=plan['basal_R_added']
        print('SENSITIVITY',name,flush=True)
        r=run_one(config,Path('resultados/cierre_f02/cache'));r.update(case=name,source_id=scenario['source_id'],plan_id=plan['id'])
        if r['status']=='COMPLETED':
            s=json.loads((Path(r['snapshot_folder'])/'s25_ifc.json').read_text(encoding='utf-8'))
            r['horizon_audit']=evaluar_horizonte(s['history'],max(p['start_h'] for p in config['construction']['pours']))
        results.append(r);write_json(out/'comparacion.json',results);write_csv(out/'comparacion.csv',results)
        print(json.dumps({k:r.get(k) for k in ('status','error','Tmax_C','Delta_estimate_C','missing_points_max','wall_time_s')}),flush=True)


if __name__=='__main__':main()
