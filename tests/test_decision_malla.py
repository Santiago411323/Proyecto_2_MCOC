import json

from publicar_decision_f02 import CAT, ICE, load_run, read


def test_resumen_acepta_solo_la_corrida_de_la_configuracion_solicitada(tmp_path):
    catalog = read(CAT / 'catalogo_congelado.json')
    scenario = next(s for s in catalog['scenarios'] if s['source_id'] == 'fv_M4_SS')
    plan = next(p for p in catalog['plans'] if p['id'] == 't8_eps100_base1')
    record = read(ICE / 'convergencia/T8_96x96x54_dt1200_fv_M4_SS.json')
    path = tmp_path / 'corrida.json'
    args = (path, scenario, plan, catalog, record['engine_fingerprint'])
    assert load_run(*args) == []
    path.write_text(json.dumps(record))
    assert load_run(*args)[0]['simulation_id'] == record['simulation_id']
    for change in (dict(shape=[36, 36, 7]), dict(configuration_hash='otro-plan'),
                   dict(engine_fingerprint='otra-version'), dict(horizon_audit={'end_h':336}),
                   dict(source_id='fv_M1_SS'), dict(status='FAILED')):
        path.write_text(json.dumps(dict(record, **change)))
        assert load_run(*args) == []
