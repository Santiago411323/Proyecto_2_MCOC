import copy,json,math
from decimal import Decimal
from pathlib import Path
import pytest
from therma.comparacion_f02 import aggregate,Evidence,ROOT,fixed_histories
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


def test_all_published_studies_imported_without_running_solver(evidence):
    assert sum(len(c['plans'][p]['runs']) for c in evidence.cohorts.values() if 'exploracion_' in c['title'] for p in c['plans'])==104
    assert any('tuberías' in c['title'] for c in evidence.cohorts.values())
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
    for p in evidence.cohorts['tuberias-42']['plans'].values():assert len(p['runs'])==1
    # Una configuración física distinta bajo igual nombre se separa; no se mezcla su peso.
    e=Evidence.__new__(Evidence);e.runs={};e.cohorts={};c=e.cohort('test','test');plan=dict(id='p',name='p')
    e.add(c,plan,dict(scenario_id='0'),dict(k=2));e.add(c,plan,dict(scenario_id='1'),dict(k=3))
    assert len(c['plans'])==2


def test_recent_summary_without_volume_is_explicit_and_reproducible(evidence):
    p=next(iter(evidence.cohorts['tuberias-42']['plans'].values()));d=evidence.detail(p['runs'][0])
    assert d['config_available'] and not d['fields_available']
    assert d['history'] and d['history'][0]['Tmax_C']==8
    assert all(h['Tmin_S25_C'] is None for h in d['history'])
    assert d['archive_figure']=='tuberias'


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
