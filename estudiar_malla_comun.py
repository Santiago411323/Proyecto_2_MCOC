"""Sensibilidad de una malla común. No cambia física ni certifica S25."""
import argparse
import json
import math
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
from therma.comparacion_f02 import ROOT, op_config
from therma.lotes import run_one, write_json, write_csv
from therma.cierre_f02 import evaluar_horizonte

OUT = ROOT / 'docs/malla_comun'
CAT = ROOT / 'docs/cierre_f02/evidencia/catalogo_congelado.json'


def assess(cases):
    """La cobertura por sí sola nunca prueba convergencia."""
    cases = sorted(cases, key=lambda r: __import__('math').prod(r['shape']))
    valid = len(cases) >= 3 and all(r.get('status') == 'COMPLETED' and r.get('missing_points_max') == 0
        and r.get('numerical_checks') and r.get('horizon_captured') for r in cases)
    valid = valid and len({r.get('engine_fingerprint') for r in cases}) == 1
    changes = {k: abs(cases[-1][k]-cases[-2][k]) for k in ('Tmax_C','Delta_estimate_C')} if valid else {}
    return dict(last_meshes=[r['shape'] for r in cases[-2:]], changes_C=changes,
        within_tolerance=bool(changes) and all(v <= .10 for v in changes.values()))


def task(spec):
    plan_id, shape, dt, source = spec
    cat = json.loads(CAT.read_bytes())
    plan = next(p for p in cat['plans'] if p['id'] == plan_id)
    cfg = op_config(cat, plan, source, shape, days=42, dt=dt)
    # Perfil exclusivo de este estudio CLI: nunca elimina la protección de RAM.
    # Permite un refinamiento adicional acotado sin cambiar el solver o el HTML.
    cells = math.prod(shape)
    memory = cells*(750+30*cfg['frames'])
    if cells > 550000 or memory > 1024**3 or cells*math.ceil(42*86400/dt) > 2000000000:
        raise ValueError('Estudio excede 550.000 celdas, 1 GiB o 2.000 millones de celda-pasos.')
    import therma.ejecutar as execution
    import therma.construccion as construction
    execution.MAX_CELLS = 550000
    execution.MAX_CELL_STEPS = construction.MAX_CELL_STEPS = 2000000000
    print('START', plan_id, shape, source, flush=True)
    r = run_one(cfg, ROOT / 'resultados/malla_comun/cache')
    r.update(plan_id=plan_id, source_id=source, dt_requested_s=dt)
    r['resource_profile'] = dict(max_cells=550000,max_memory_bytes=1024**3,max_cell_steps=2000000000,estimated_memory_bytes=memory)
    scenario = next(s for s in cat['scenarios'] if s['source_id'] == source)
    r.update(scenario_id=scenario['id'], climate_id=scenario['climate_id'], weight=scenario['weight'])
    if r['status'] == 'COMPLETED':
        s = json.loads((Path(r['snapshot_folder']) / 's25_ifc.json').read_bytes())
        audit = evaluar_horizonte(s['history'], max(p['start_h'] for p in cfg['construction']['pours']))
        r.update(horizon_captured=audit['captured'], horizon_audit=audit)
    name = f"{plan_id}_{'x'.join(map(str, shape))}_dt{dt:g}_{source}"
    write_json(OUT / 'corridas' / (name + '.json'), r)
    print(json.dumps({k: r.get(k) for k in ('plan_id','shape','source_id','status','Tmax_C','Delta_estimate_C','missing_points_max','runtime_s','error')}), flush=True)
    return r


def summarize():
    records = [json.loads(p.read_bytes()) for p in (OUT / 'corridas').glob('*.json')]
    assessments = []
    for pid in sorted({r['plan_id'] for r in records}):
        cases = [r for r in records if r['plan_id'] == pid and r['source_id'] == 'fv_M4_SS' and r['dt_requested_s'] == 1200
                 and r.get('shape') in [[72,72,42],[84,84,48],[90,90,48]]]
        cases.sort(key=lambda r: __import__('math').prod(r['shape']))
        if len(cases) < 3:
            continue
        assessments.append(dict(plan_id=pid, **assess(cases)))
    write_json(OUT / 'estudio.json', dict(spatial_tolerance_C=.10, assessments=assessments,
        note='Cambios observados; no cota del error físico. S25 sigue estimado. No seleccionar una malla solamente por cobertura.', runs=records))
    write_csv(OUT / 'resumen.csv', [{k:r.get(k) for k in ('plan_id','source_id','shape','dt_requested_s','Tmax_C','Delta_estimate_C','missing_points_max','numerical_checks','horizon_captured','runtime_s')} for r in records])
    print(json.dumps(assessments), flush=True)


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--plans', nargs='+', default=['continua','lento'])
    p.add_argument('--shape', nargs=3, type=int, action='append')
    p.add_argument('--sources', nargs='+', default=['fv_M4_SS'])
    p.add_argument('--dt', type=float, default=1200)
    p.add_argument('--workers', type=int, choices=range(1,5), default=3)
    p.add_argument('--summary-only', action='store_true')
    a = p.parse_args()
    if not a.summary_only:
        specs = [(pid,shape,a.dt,s) for pid in a.plans for shape in (a.shape or [[72,72,42],[84,84,48],[90,90,48]]) for s in a.sources]
        with ProcessPoolExecutor(max_workers=a.workers) as pool:
            list(pool.map(task, specs))
    summarize()
