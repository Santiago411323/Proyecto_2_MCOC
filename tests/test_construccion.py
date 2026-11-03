import hashlib
import json
import uuid
import numpy as np
import pytest
from therma.ejecutar import ejecutar,validar
from therma.resultados import desde_xfast


def config(starts=(0.,24.,48.)):
    return dict(geometry='foundation',meshIndex=0,source='none',calibrate=False,days=4.,frames=20,
        faces=[dict(type='R',temp=20.,h=10.,R=0.,flux=0.) for _ in range(6)],
        construction=dict(model='exponential_adiabatic',parameter_source='Caso didáctico declarado: no mezcla real.',
            pours=[dict(id=i+1,start_h=t,placement_C=18.+i,theta_inf_C=40.,tau_h=24.) for i,t in enumerate(starts)]))


@pytest.fixture(scope='module')
def result(tmp_path_factory):
    out=tmp_path_factory.mktemp('construction');meta=ejecutar(config(),uuid.uuid4().hex,out)
    return meta,out


def test_activation_masks_events_exact_placement_and_guids(result):
    meta,out=result
    assert meta['schema_version']=='1.1' and not meta['geometry']['active_static']
    with np.load(out/'campos.npz') as z:
        ids=z['pour_ids'];times=z['tiempo_s'];T=z['T_C'];active=z['active']
        for j,t in enumerate(times):
            expected=(ids>0)&(z['placement_time_s']<=t+1e-8)
            np.testing.assert_array_equal(active[j],expected)
            assert np.all(T[j][~active[j]]==0)
        for i,t in enumerate((0,86400,172800)):
            j=list(times).index(t);np.testing.assert_array_equal(T[j][ids==i+1],18.+i)
    assert [e['time_s'] for e in meta['construction']['events']]==[0,86400,172800]
    assert all(e['guid'] and e['interfaces_rebuilt'] for e in meta['construction']['events'])
    assert meta['metrics']['connectivity_rebuilds']==3


def test_independent_sources_ages_and_no_heat_before_activation(result):
    meta,_=result;states=meta['construction']['snapshots']
    event=next(s for s in states if s['time_s']==86400)
    a,b,c=event['pours'];assert a['age_s']==86400 and b['age_s']==0 and c['age_s'] is None
    assert a['source_W_m3']==pytest.approx(b['source_W_m3']/np.e)
    assert c['source_W_m3']==0 and not c['active']


def test_conservative_energy_and_binary_axis_correspondence(result):
    meta,out=result
    assert meta['metrics']['energy_residual_relative']<1e-12
    for h in meta['history']:
        assert h['energy']==pytest.approx(h['placed_J']+h['source_J']+h['boundary_J'],rel=1e-12,abs=1e-5)
    raw=np.fromfile(out/'active.bin',dtype='uint8').reshape(meta['activation']['shape'])
    with np.load(out/'campos.npz') as z:
        for j in range(len(raw)):np.testing.assert_array_equal(desde_xfast(raw[j],meta['geometry']['shape_xyz']),z['active'][j])
    assert hashlib.sha256((out/'active.bin').read_bytes()).hexdigest()==meta['activation']['sha256']
    assert meta['validity']['project_deltaT_25mm']=='NOT EVALUATED'


def test_precise_critical_field_and_pre_post_event_snapshots(result):
    meta,out=result;times=meta['fields']['times_s']
    for t in (86400.,172800.):assert t in times and t-1 in times
    j=times.index(meta['metrics']['global_peak_time_s'])
    with np.load(out/'campos.npz') as z:
        assert z['T_C'][j][z['active'][j]].max()==pytest.approx(meta['metrics']['maxField'])


def test_delayed_first_pour_and_unplaced_last_layer(tmp_path):
    p=config((2.,24.,200.));p['days']=2
    meta=ejecutar(p,uuid.uuid4().hex,tmp_path)
    assert meta['history'][0]['max'] is None and meta['history'][0]['energy']==0
    assert meta['construction']['snapshots'][0]['active_pour_ids']==[]
    with np.load(tmp_path/'campos.npz') as z:assert not z['active'][-1][z['pour_ids']==3].any()


@pytest.mark.parametrize('change',[{'calibrate':True},{'source':'pulse'},{'geometry':'block'}])
def test_construction_rejects_wrong_domain_or_target_calibration(change):
    p=config();p.update(change)
    with pytest.raises(ValueError):validar(p)


def test_manual_step_cannot_violate_any_construction_stage(tmp_path):
    p=config();p.update(dtMode='manual',dt=1e10)
    with pytest.raises(ValueError,match='inestable'):ejecutar(p,uuid.uuid4().hex,tmp_path)


def test_parameter_provenance_required():
    p=config();p['construction']['parameter_source']=''
    with pytest.raises(ValueError,match='procedencia'):validar(p)
