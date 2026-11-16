import copy
import numpy as np
import pytest
from therma.enfriamiento import CircuitoTuberias,validar_enfriamiento
from therma.activacion import ConstruccionTermica


def spec(**kw):
    return dict(model='parallel_x_pipes',inlet_C=10.,flow_kg_s=.1,water_cp_J_kgK=4180.,
        conductance_W_mK=8.,spacing_m=1.,levels_m=[.5],start_h=0.,stop_h=10.,parameter_source='Hipótesis de prueba',**kw)


def test_uniform_water_matches_exact_exponential_and_energy():
    ids=np.ones((10,1,1),int);c=CircuitoTuberias(ids,[10,1,1],[0,0,0],spec())
    power,d=c.exchange(np.full(ids.shape,40.),ids>0,0.)
    exact=40+(10-40)*np.exp(-8*10/(.1*4180))
    assert d['outlet_mean_C']==pytest.approx(exact)
    assert power.sum()==pytest.approx(.1*4180*(exact-10))
    assert power.sum()==pytest.approx(d['water_power_W'])


def test_concrete_water_balance_and_hydration_separate():
    ids=np.ones((4,1,1),int);c=CircuitoTuberias(ids,[4,1,1],[0,0,0],spec())
    m=ConstruccionTermica(ids,[4,1,1],[dict(id=1,inicio_s=0.,temperatura_C=40.)],cooling=c)
    initial=m.energia()
    for _ in range(10):m.paso(100,100.)
    assert m.energia_fuente_J==pytest.approx(100*4*1000)
    assert m.energia()==pytest.approx(initial+m.energia_fuente_J-m.energia_enfriamiento_J)
    assert m.energia_agua_J==pytest.approx(m.energia_enfriamiento_J)
    assert abs(m.residual())/initial<1e-12


def test_inactive_pours_and_off_window_have_no_exchange():
    ids=np.array([1,1,2,2]).reshape(4,1,1);s=spec();s.update(start_h=1.,stop_h=2.)
    c=CircuitoTuberias(ids,[4,1,1],[0,0,0],s);mask=ids==1;T=np.full(ids.shape,40.)
    assert c.exchange(T,mask,0)[0].sum()==0
    power,d=c.exchange(T,mask,3600)
    assert not power[~mask].any() and d['active_circuits']==1
    assert c.exchange(T,mask,7200)[0].sum()==0


def test_explicit_cfl_includes_pipe_and_preserves_temperature_bounds():
    ids=np.ones((1,1,1),int);s=spec();s['conductance_W_mK']=1e5
    c=CircuitoTuberias(ids,[1,1,1],[0,0,0],s)
    m=ConstruccionTermica(ids,[1,1,1],[dict(id=1,inicio_s=0.,temperatura_C=40.)],cooling=c)
    assert np.isfinite(m.dt_max)
    with pytest.raises(ValueError,match='inestable'):m.paso(m.dt_max*1.01)
    m.paso(m.dt_max*.9)
    assert 10<=m.T.item()<=40


def test_water_can_deliver_heat_and_steps_cannot_cross_switch():
    ids=np.ones((1,1,1),int);s=spec();s['start_h']=.1
    c=CircuitoTuberias(ids,[1,1,1],[0,0,0],s)
    m=ConstruccionTermica(ids,[1,1,1],[dict(id=1,inicio_s=0.,temperatura_C=5.)],cooling=c)
    with pytest.raises(ValueError,match='encendido'):m.paso(400)
    power,d=c.exchange(m.T,m.activo,360)
    assert power.sum()<0 and d['outlet_mean_C']<10


def test_validation_and_grid_aliasing_reject_invalid_inputs():
    p=dict(geometry='foundation',construction={'pours':[]},L=[4,1,1],cooling=spec())
    validar_enfriamiento(p)
    p['cooling']['flow_kg_s']=0
    with pytest.raises(ValueError):validar_enfriamiento(p)
    s=spec();s['levels_m']=[.4,.5]
    with pytest.raises(ValueError,match='gruesa'):CircuitoTuberias(np.ones((4,1,1),int),[4,1,1],[0,0,0],s)
