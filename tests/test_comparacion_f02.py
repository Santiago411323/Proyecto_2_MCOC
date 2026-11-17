import copy,json,math
from decimal import Decimal
from pathlib import Path
import pytest
from therma.comparacion_f02 import aggregate,aggregate_estimated,Evidence,ROOT,fixed_histories
from test_fase1_python import server,request


def r(i='a',w='1',T=30,D=10,valid=True,**kw):
    return dict(scenario_id=i,weight=w,status='COMPLETED',numerical_checks=True,horizon_captured=True,Tmax_C=T,DeltaTmax_validated_C=D,s25_validated=valid,**kw)

def scenarios(*weights):return [dict(id=str(i),weight=w) for i,w in enumerate(weights)]


@pytest.mark.parametrize('T,D,pt,pd,pf',[(71,10,1,0,1),(30,21,0,1,1),(71,21,1,1,1),(70,20,0,0,0)])
def test_union_and_strict_threshold(T,D,pt,pd,pf):
    v=aggregate([r('0',T=T,D=D)],scenarios('1'))
    assert (v['P_T'],v['P_Delta'],v['P_f'])==(pt,pd,pf)


@pytest.mark.parametrize('w,compliance',[('0.05','CUMPLE'),('0.050000000001','NO CUMPLE')])
def test_unequal_weights_and_no_rounded_compliance(w,compliance):
    other=str(Decimal(1)-Decimal(w));v=aggregate([r('0',w,T=71,D=21),r('1',other)],scenarios(w,other))
    assert v['compliance']==compliance and v['P_f']==float(w)


def test_s25_estimate_does_not_turn_into_zero_probability():
    v=aggregate([r('0',valid=False)],scenarios('1'))
    assert v['P_T']==0 and v['P_Delta'] is None and v['P_f'] is None
    assert v['compliance']=='INDETERMINADO'


def test_missing_failed_truncated_and_invalid_weights_are_unknown():
    v=aggregate([r('0','.5')],scenarios('.5','.5'));assert v['P_T'] is None and v['missing']==['1']
    for key,value in [('status','FAILED'),('horizon_captured',False),('numerical_checks',False)]:
        row=r('0');row[key]=value;assert aggregate([row],scenarios('1'))['P_T'] is None
    for weights in [('1.1','-.1'),('.5','.4'),('NaN','1')]:assert not aggregate([],scenarios(*weights))['weights_valid']
    assert not aggregate([r('0','NaN')],scenarios('1'))['weights_valid']
    assert not aggregate([r('0'),r('0')],scenarios('1'))['weights_valid']


@pytest.fixture(scope='module')
def evidence():return Evidence(ROOT/'resultados/empty_comparison_tests')


@pytest.mark.parametrize('target,original_id,dose',[(12,'t12_eps100_base1.0',36.39293),(8,'t8_eps100_base1',60.65489)])
def test_hielo_reproduce_plan_de_origen(evidence,target,original_id,dose):
    c=evidence.cohorts['hielo-eps100-42']
    p=c['plans'][f'hielo_t{target}_eps100_base1']
    original=next(group['plans'][original_id] for group in evidence.cohorts.values()
                  if group['id'].startswith('cierre-') and original_id in group['plans'])
    by_source={evidence.runs[uid]['source_id']:evidence.runs[uid] for uid in original['runs']}
    assert p['operations']==original['operations'] and len(p['runs'])==4
    assert p['parameters']['preenfriamiento']['balance']['dose_kg_m3']==pytest.approx(dose,abs=.0001)
    for uid in p['runs']:
        r=evidence.runs[uid];base=by_source[r['source_id']]
        assert r['simulation_id']!=base['simulation_id']
        assert r['Tmax_C']==pytest.approx(base['Tmax_C'])
        assert r['Delta_estimate_C']==pytest.approx(base['Delta_estimate_C'])
    assert p['estimated_risk']['P_f']==0 and p['risk']['P_f'] is None


def test_malla_fina_conserva_geometria_y_reporta_cobertura_incompleta(evidence):
    fine=evidence.cohorts['hielo-eps100-42_250']
    coarse=evidence.cohorts['hielo-eps100-42']
    assert len(fine['plans'])==2
    for key,p in fine['plans'].items():
        assert p['operations']==coarse['plans'][key]['operations']
        assert len(p['runs'])==4
        assert p['estimated_risk']['P_f'] is None
        for row in p['parameters']['mesh_comparison']:
            assert row['cells_total']==72*72*14
            assert row['cells_active']==32912
            assert row['volume_error_pct']==pytest.approx(-.452755,abs=.00001)
            assert row['missing_S25']==88
        for uid in p['runs']:
            run=evidence.runs[uid]
            assert run['shape']==[72,72,14] and run['numerical_checks']
            assert run['horizon_captured'] and run['coverage']<1


def test_all_published_studies_imported_without_running_solver(evidence):
    assert sum(len(c['plans'][p]['runs']) for c in evidence.cohorts.values() if 'exploracion_' in c['title'] for p in c['plans'])==104
    assert not any('tuberías' in c['title'] for c in evidence.cohorts.values())
    assert any(c['id']=='mejoras-fuentes_finas-42' for c in evidence.cohorts.values())
    assert any(c['id']=='malla-dt450_21d' for c in evidence.cohorts.values())
    assert all(p['risk']['P_f'] is None for c in evidence.cohorts.values() for p in c['plans'].values())
    first=next(c for c in evidence.cohorts.values() if 'exploracion_constructiva' in c['title'])
    assert {'continua','propuesto','rapido','lento'}<=set(first['plans'])
    assert all(p['risk']['weight_sum']==1 for p in first['plans'].values())


def test_source_physics_and_horizon_never_merge(evidence):
    a=evidence.cohorts['mejoras-confirmacion-42'];b=evidence.cohorts['mejoras-confirmacion-14']
    assert a['days']==42 and b['days']==14
    assert all(p['risk']['P_T'] is None for p in b['plans'].values())
    assert all(len(p['runs'])==4 for p in a['plans'].values())
    # Una configuración física distinta bajo igual nombre se separa; no se mezcla su peso.
    e=Evidence.__new__(Evidence);e.runs={};e.cohorts={};c=e.cohort('test','test');plan=dict(id='p',name='p')
    e.add(c,plan,dict(scenario_id='0'),dict(k=2));e.add(c,plan,dict(scenario_id='1'),dict(k=3))
    assert len(c['plans'])==2


def test_real_fields_fixed_sensor_and_critical_weights_match(evidence):
    candidates=[r for r in evidence.runs.values() if r['plan_id']=='propuesto' and r['source_id']=='fv_M4_SS' and 'exploracion_refinada' in evidence.cohorts[r['cohort_id']]['title']]
    if not candidates or not candidates[0].get('_folder'):pytest.skip('Campos locales no versionados')
    d=evidence.detail(candidates[0]['uid']);assert d['fields_available'];pair=d['critical_pair']
    fixed=next(v for v in d['fixed'] if v['name'].startswith('S25'))
    value=next(v for t,v in fixed['values'] if abs(t-pair['time_s'])<1e-7)
    assert value==pytest.approx(pair['cold']['temperature_C'],abs=1e-5)
    peak=max(d['history'],key=lambda h:h['Delta_C'])
    assert peak['Delta_C']==pytest.approx(peak['Tmax_C']-peak['Tmin_S25_C'])


def test_api_real_catalog_and_unknown_id(server):
    from urllib.error import HTTPError
    data=json.loads(request(server,'/api/comparison-f02')[1]);assert data['counts']['scenario_rows']>=187
    uid=next(p['runs'][0]['uid'] for c in data['cohorts'] for p in c['plans'] if p['runs'])
    d=json.loads(request(server,'/api/comparison-f02/'+uid)[1]);assert d['run']['uid']==uid
    with pytest.raises(HTTPError):request(server,'/api/comparison-f02/not-a-valid-id')



def test_pending_plan_preparation_uses_a_real_schedule_without_running(evidence):
    c=evidence.cohorts['mejoras-fuentes_finas-42']
    assert 'lento' in {p['id'] for p in evidence.pending(c['id'])}
    prepared=evidence.prepare(c['id'],'lento');p=prepared['config']
    assert p['n']==[48,48,30] and p['days']==42
    assert p['L']==pytest.approx([18,18,3.3]) and p['origin']==[-9,-9,0]
    assert p['construction']['pours'][-1]['start_h']==96
    assert p['weather']['start_utc']=='2026-11-19T10:00:00-03:00'
    assert prepared['plan']['D_h']>98
    assert 'actual' in prepared['note']


def test_completed_weights_are_not_confused_with_expected_sum():
    v=aggregate([r('0','.5')],scenarios('.5','.5'))
    assert v['weight_sum']==1 and v['completed_weight_sum']==.5


def test_estimated_probabilities_are_separate_and_do_not_validate_s25():
    records=[r(str(i),'.25',valid=False,Delta_estimate_C=18.,coverage=1.) for i in range(4)]
    before=copy.deepcopy(records);catalog=scenarios('.25','.25','.25','.25')
    estimate=aggregate_estimated(records,catalog)
    assert estimate['is_estimate'] and estimate['P_Delta']==0 and estimate['P_f']==0
    assert estimate['compliance']=='CUMPLE'
    assert aggregate(records,catalog)['P_f'] is None and records==before
    records[0].update(Tmax_C=71.,Delta_estimate_C=21.)
    records[1].update(Delta_estimate_C=21.)
    estimate=aggregate_estimated(records,catalog)
    assert estimate['P_T']==.25 and estimate['P_Delta']==.5 and estimate['P_f']==.5


@pytest.mark.parametrize('change',[dict(coverage=.99),dict(horizon_captured=False),dict(status='FAILED'),dict(numerical_checks=False)])
def test_approximation_does_not_turn_incomplete_results_into_success(change):
    records=[r('0',valid=False,Delta_estimate_C=18.,coverage=1.)]
    records[0].update(change)
    result=aggregate_estimated(records,scenarios('1'))
    assert result['P_f'] is None and result['compliance']=='INDETERMINADO'


def test_estimated_weights_are_checked_before_calculation():
    record=r('0',valid=False,Delta_estimate_C=18.,coverage=1.)
    assert not aggregate_estimated([record],scenarios('.9'))['weights_valid']
    assert aggregate_estimated([record,record],scenarios('1'))['P_f'] is None
