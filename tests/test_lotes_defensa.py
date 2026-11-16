import copy
from decimal import Decimal
from types import SimpleNamespace
import numpy as np
import pytest
from therma.riesgo import resumen_riesgo
from therma.s25 import reconstruir, ObservadorS25
from therma.lotes import validar_catalogo, preparar_config, run_one
from ejecutar_lotes_defensa import build_catalog, audit_sources


def row(t,d,weight='1',ident='a',status='COMPLETED'):
    return dict(scenario_id=ident,weight=weight,status=status,I_T=t,I_Delta=d)


@pytest.mark.parametrize('t,d,pf',[(True,False,1),(False,True,1),(True,True,1),(False,False,0)])
def test_union_not_sum_or_product(t,d,pf):
    r=resumen_riesgo([row(t,d)])
    assert r['P_f']==pf
    assert r['compliance']==('NO CUMPLE' if pf else 'CUMPLE')


@pytest.mark.parametrize('w,expected',[('0.05','CUMPLE'),('0.050000000001','NO CUMPLE')])
def test_exact_threshold_without_rounding(w,expected):
    rows=[row(True,True,w),row(False,False,str(Decimal(1)-Decimal(w)),'b')]
    r=resumen_riesgo(rows)
    assert r['compliance']==expected
    assert r['P_f']==float(w)  # falla simultánea contada una vez


def test_unknown_and_failed_are_not_success():
    r=resumen_riesgo([row(False,None,'.7'),row(False,False,'.3','b',status='FAILED')])
    assert r['P_T'] is None and r['P_Delta'] is None and r['P_f'] is None
    assert r['P_f_lower']==0 and r['P_f_upper']==1 and r['compliance']=='INDETERMINADO'
    r=resumen_riesgo([row(True,None)])
    assert r['P_f']==1 and r['compliance']=='INDETERMINADO' and r['rejected_by_known_failures']


@pytest.mark.parametrize('rows',[[row(False,False,'.9')],[row(False,False,'NaN')],[row(False,False,'-.1'),row(False,False,'1.1','b')],[row(False,False,'.5'),row(False,False,'.5')]])
def test_invalid_weights_and_duplicates(rows):
    with pytest.raises(ValueError):resumen_riesgo(rows)


def test_unequal_weights():
    r=resumen_riesgo([row(True,False,'.1'),row(False,True,'.2','b'),row(False,False,'.7','c')])
    assert r['P_T']==.1 and r['P_Delta']==.2 and r['P_f']==.3


def test_s25_exact_linear_profile_resistance_and_refinement():
    # Flujo saliente constante 30 W/m²; Ts=10+q R, T(s)=Ts+q s/k.
    for d in (.5,.275,.1):
        q,R,k,air=30.,.2,2.,10.
        center=air+q*(R+d/(2*k))
        assert reconstruir(center,air,R,k,d)==pytest.approx(air+q*(R+.025/k))
    with pytest.raises(ValueError):reconstruir(20,10,.2,2,.02)


def test_transient_s25_error_decreases_for_exact_sinusoid():
    # T(x)=20+10 sin(pi x), Dirichlet 20; perfil curvo exacto conocido.
    exact=20+10*np.sin(np.pi*.025)
    errors=[]
    for spacing in (.5,.25,.125,.0625):
        value=reconstruir(20+10*np.sin(np.pi*spacing/2),20,0.,2.,spacing)
        errors.append(abs(value-exact))
    assert all(a>b for a,b in zip(errors,errors[1:]))
    assert errors[-1]<.001


def test_s25_global_same_time_dynamic_surface_and_inactive_cells():
    shape=(2,2,3)
    active=np.zeros(shape,bool);active[:,:,0]=True
    T=np.zeros(shape);T[:,:,0]=40;T[:,:,2]=1000  # no colocado
    m=SimpleNamespace(activo=active,forma=shape,dx=np.ones(3),T=T,t=0.,ids=np.ones(shape,int))
    p=dict(k=2.,origin=[0,0,0],faces=[dict(type='R',h=10.,R=0.,temp=20.,flux=0.) for _ in range(6)])
    observer=ObservadorS25();observer(m,p,dict(residual=0.))
    assert observer.rows[0]['Tmax_C']==40
    assert observer.rows[0]['Delta_estimate_C']==pytest.approx(40-reconstruir(40,20,.1,2.,1.))
    assert observer.peak['cold']['index'][2]==0
    active[:,:,1]=True;T[:,:,1]=18;m.t=3600
    observer(m,p,dict(residual=0.))
    assert observer.rows[-1]['Tmax_C']==40
    assert observer.rows[-1]['S25_min_estimate_C']<20
    assert observer.validation=='NOT VALIDATED'


def test_catalogue_full_curves_distinct_methods_and_physical_duration():
    cat=build_catalog()
    validar_catalogo(cat)
    assert len(cat['sources'])==4 and len(cat['climates'])==1
    assert len({s['curve']['raw_sha256'] for s in cat['sources']})==1
    assert len(cat['sources'][0]['curve']['time_h'])>1000
    continuous=cat['plans'][0]
    assert continuous['D_h']==pytest.approx(cat['geometry']['volume_m3']/20)
    assert continuous['operations'][-1]['end_h']>continuous['operations'][-1]['start_h']
    bad=copy.deepcopy(cat);bad['plans'][0]['operations'][1]['start_h']=0
    with pytest.raises(ValueError):validar_catalogo(bad)
    audit=audit_sources()
    assert audit[0]['sha256']!=audit[1]['sha256']
    assert audit[0]['curves'][0]['energy_MJ_m3']>2*audit[1]['curves'][0]['energy_MJ_m3']


def test_cache_reuses_only_integrity_checked_configuration(tmp_path):
    cat=build_catalog();p=preparar_config(cat,cat['plans'][1],cat['scenarios'][0],mesh=[6,6,6],dt=900.)
    p['days']=4.
    a=run_one(p,tmp_path)
    assert a['status']=='COMPLETED'
    b=run_one(p,tmp_path)
    assert b['reused'] and b['cache_key']==a['cache_key']
    from pathlib import Path
    (Path(a['snapshot_folder'])/'history_s25.csv').write_text('tampered')
    c=run_one(p,tmp_path)
    assert not c['reused']
    other=copy.deepcopy(p);other['k']=2.1
    d=run_one(other,tmp_path)
    assert d['cache_key']!=a['cache_key'] and not d['reused']


def test_batch_continues_after_failure_and_exports_unknowns(tmp_path,monkeypatch):
    import therma.lotes as module
    cat=build_catalog();cat['plans']=cat['plans'][:2]
    seen=[]
    def prepare(cat,plan,scenario,*args):
        seen.append((plan['id'],scenario['id'],scenario['weight']))
        if scenario['id']==cat['scenarios'][1]['id']:
            raise ValueError('Fallo de prueba antes del solver')
        return {}
    monkeypatch.setattr(module,'preparar_config',prepare)
    monkeypatch.setattr(module,'run_one',lambda *args:dict(status='COMPLETED',I_T=False,I_Delta=None,numerical_checks=True,horizon_captured=True))
    summaries,records=module.ejecutar_catalogo(cat,tmp_path)
    assert len(records)==8 and sum(r['status']=='FAILED' for r in records)==2
    assert [(sid,w) for p,sid,w in seen if p==cat['plans'][0]['id']]==[(sid,w) for p,sid,w in seen if p==cat['plans'][1]['id']]
    assert all(r['compliance']=='INDETERMINADO' for r in summaries)
    assert 'NO EVALUADO' in (tmp_path/'tabla_planes.md').read_text(encoding='utf-8')


def test_transient_solver_s25_verification_converges(tmp_path):
    from verificar_s25_defensa import verificar
    rows=verificar(tmp_path)
    assert rows[2]['absolute_error_C']<rows[1]['absolute_error_C']<rows[0]['absolute_error_C']
    assert rows[-1]['absolute_error_C']<.001


def test_transient_robin_s25_verification_converges(tmp_path):
    from verificar_s25_defensa import verificar_robin
    rows=verificar_robin(tmp_path)
    assert rows[2]['absolute_error_C']<rows[1]['absolute_error_C']<rows[0]['absolute_error_C']
    assert rows[-1]['absolute_error_C']<.01
