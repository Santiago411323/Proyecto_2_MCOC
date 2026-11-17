"""Reproduce el plan de 8 o 12 °C del cierre F02 con preenfriamiento mediante hielo."""
import argparse
import json

from therma.cierre_f02 import evaluar_horizonte
from therma.hielo import ROOT, CATALOG, balance
from therma.lotes import preparar_config, run_one, sha, validar_catalogo
from therma.comparacion_f02 import op_config


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--temperatura',type=int,choices=(8,12),default=12)
    parser.add_argument('--resolucion',type=int,choices=(250,500),default=500)
    parser.add_argument('--malla',nargs=3,type=int,help='Malla del estudio de convergencia; conserva las corridas previas.')
    parser.add_argument('--dt',type=float,default=900.)
    args=parser.parse_args()
    target=args.temperatura
    shape=args.malla or ([72,72,14] if args.resolucion==250 else [36,36,7])
    cat=json.loads(CATALOG.read_bytes())
    validar_catalogo(cat)
    if sha(ROOT/'modelo_e02.ifc') != cat['geometry']['ifc_sha256']:
        raise ValueError('El IFC actual difiere del plan congelado.')
    original=next(p for p in cat['plans'] if p['id']=={8:'t8_eps100_base1',12:'t12_eps100_base1.0'}[target])
    inputs=dict(mode='target',value=original['placement_C'],reference_C=18.,water_C=20.,ice_C=0.,water_kg_m3=160.)
    mix=balance(inputs,cat['base_config']['rho'],cat['base_config']['cp'],sum(p['volume_m3'] for p in original['operations']))
    plan=dict(original,id=f'hielo_t{target}_eps100_base1',name=f'Con hielo · Tcol {target} °C, EPS 100 mm, R basal adicional 1,0',
              placement_C=mix['placement_C'])
    runs=[]
    for s in cat['scenarios']:
        if args.malla:
            config=op_config(cat,plan,s['source_id'],shape,days=42,dt=args.dt)
        else:
            config=preparar_config(cat,plan,s,mesh=shape,dt=args.dt)
            config['environment']['soil']['contact_R_m2K_W']+=plan['basal_R_added']
        r=run_one(config,ROOT/'resultados/hielo_f02/cache')
        if r['status']!='COMPLETED':raise RuntimeError(r.get('error',r['status']))
        folder=ROOT/'resultados/hielo_f02/cache'/r['cache_key']
        history=json.loads((folder/'s25_ifc.json').read_bytes())['history']
        audit=evaluar_horizonte(history,max(p['start_h'] for p in config['construction']['pours']))
        r.update(horizon_captured=audit['captured'],extension_required=not audit['captured'],horizon_audit=audit,
                 scenario_id=s['id'],source_id=s['source_id'],climate_id=s['climate_id'],weight=s['weight'])
        r.pop('snapshot_folder')
        runs.append(r)
        print(s['source_id'],r['Tmax_C'],r['Delta_estimate_C'],flush=True)
    suffix='_estudiada' if args.malla else '_250' if args.resolucion==250 else ''
    output=ROOT/f'docs/hielo_f02/plan_{target}{suffix}.json'
    output.parent.mkdir(exist_ok=True)
    tmp=output.with_suffix('.tmp')
    tmp.write_text(json.dumps(dict(plan=plan,original_plan_id=original['id'],catalog_sha256=sha(CATALOG),
                                   inputs=inputs,mix=mix,runs=runs),ensure_ascii=False,indent=2),encoding='utf-8')
    tmp.replace(output)


if __name__=='__main__':
    main()
