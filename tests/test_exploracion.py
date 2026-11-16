import copy
import numpy as np
import pytest
from therma.exploracion import catalogo
from therma.lotes import preparar_config,validar_catalogo,run_one
from therma.s25_ifc import stencil_compartido
from types import SimpleNamespace


def test_exploration_preserves_geometry_rate_and_no_overlap():
    cat=catalogo();validar_catalogo(cat)
    assert len(cat['plans'])==20 and len(cat['scenarios'])==4
    totals=[]
    for p in cat['plans']:
        totals.append(sum(o['volume_m3'] for o in p['operations']))
        assert p['rate_m3_h']==20 and p['construction_pours'] in (1,2,3)
        assert p['D_h']==p['operations'][-1]['end_h']
        assert all(b['start_h']>=a['end_h'] for a,b in zip(p['operations'],p['operations'][1:]))
    assert max(totals)==min(totals)
    for wait in (0,6,12,18,24,36):
        p=next(p for p in cat['plans'] if p['id']=='espera'+str(wait))
        assert p['D_h']==pytest.approx(totals[0]/20+2*wait)


def test_protection_changes_actual_configuration_no_base_mutation():
    cat=catalogo();base=copy.deepcopy(cat['base_config']);s=cat['scenarios'][0]
    select=lambda ident:next(p for p in cat['plans'] if p['id']==ident)
    a=preparar_config(cat,select('propuesto'),s)
    b=preparar_config(cat,select('eps25'),s)
    assert b['faces'][0]['R']-a['faces'][0]['R']==pytest.approx(.025/.038)
    assert b['faces'][5]['R']-a['faces'][5]['R']==pytest.approx(.025/.038)
    assert b['faces'][4]['R']==a['faces'][4]['R']
    assert 'formwork' not in preparar_config(cat,select('sin_moldaje'),s)
    assert preparar_config(cat,select('retiro72'),s)['formwork']['remove_at_h']==72
    assert cat['base_config']==base
    with pytest.raises(ValueError):preparar_config(cat,dict(select('propuesto'),physical_overrides=dict(k=1)),s)


def test_shared_stencils_do_not_cache_temperature():
    active=np.ones((8,8,8),bool);m=SimpleNamespace(activo=active,ids=active.astype(int),dx=np.ones(3)/8)
    sample=dict(points=np.array([[.025,.4,.5]]),point_owner=np.array([1]))
    r=stencil_compartido(sample,m,dict(origin=[0,0,0]));r2=stencil_compartido(sample,m,dict(origin=[0,0,0]))
    assert r is r2
    assert r.evaluate(np.full(active.shape,30.))[0]==pytest.approx(30)
    assert r2.evaluate(np.full(active.shape,20.))[0]==pytest.approx(20)
    m.ids[0,0,0]=2
    assert stencil_compartido(sample,m,dict(origin=[0,0,0])) is not r


def test_ifc_batch_dispatch_and_indeterminate(tmp_path):
    cat=catalogo();p=preparar_config(cat,cat['plans'][1],cat['scenarios'][-1],mesh=[24,24,6],dt=900.)
    p['days']=2.2
    a=run_one(p,tmp_path);assert a['status']=='COMPLETED',a
    assert a['S25_validation']=='NOT VALIDATED' and a['P_f'] is None and a['I_Delta'] is None
    assert a['peak_S25']['DeltaT_estimate_C']==pytest.approx(a['Delta_estimate_C'])
    b=run_one(p,tmp_path);assert b['reused'] and b['cache_key']==a['cache_key']
    p['construction']['pours'][0]['placement_C']+=1
    c=run_one(p,tmp_path);assert c['cache_key']!=a['cache_key'] and not c['reused']


def test_published_results_registry_is_confined(tmp_path,monkeypatch):
    import json
    import servidor_therma as module
    monkeypatch.setattr(module,'ROOT',tmp_path)
    folder=tmp_path/'resultados/cache/run';folder.mkdir(parents=True);(folder/'metadata.json').write_text('{}')
    ident='a'*32;registry=tmp_path/'resultados/planes_publicados.json'
    registry.write_text(json.dumps({ident:dict(folder='resultados/cache/run',artifacts={'metadata.json':'hash'})}))
    assert module.resultado_publicado(ident,'metadata.json')==folder/'metadata.json'
    assert module.resultado_publicado(ident,'not_allowed.bin') is None
    registry.write_text(json.dumps({ident:dict(folder='../outside',artifacts={'metadata.json':'hash'})}))
    assert module.resultado_publicado(ident,'metadata.json') is None
    assert module.resultado_publicado('../secret','metadata.json') is None

def test_robin_closure_identifies_coplanar_normal_gradient_in_reference():
    from verificar_cierre_s25 import referencias
    rows=referencias()
    assert max(r['error_C'] for r in rows if 'linear' in r['case'])<1e-10
    assert max(abs(r['boundary_constraint_residual_W_m2']) for r in rows)<1e-10
    errors=[r['error_C'] for r in rows if r['case']=='transient_Robin_exact']
    assert all(a>b for a,b in zip(errors,errors[1:]))
    assert errors[-1]<.002
