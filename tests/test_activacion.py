import numpy as np
import pytest
from therma.activacion import ConstruccionTermica


def layers(starts=(0.,1.),temps=(10.,30.),**kwargs):
    return ConstruccionTermica(np.arange(1,len(starts)+1),[len(starts)],
        [dict(id=i+1,inicio_s=t,temperatura_C=T,guid=f'guid-{i+1}') for i,(t,T) in enumerate(zip(starts,temps))],rho=2.,cp=5.,**kwargs)


def test_inactive_cells_no_source_no_capacity_before_event():
    m=layers();assert m.activo.tolist()==[True,False]
    m.paso(.5,[0,1e9]);assert m.T.tolist()==[10.,0.]
    assert m.energia()==100 and m.energia_fuente_J==0 and m.residual()==0


def test_event_exact_temperature_and_energy_of_fresh_material():
    m=layers();m.paso(1.)
    assert m.T.tolist()==[10.,30.] and m.activo.all()
    assert m.eventos[-1]['time_s']==1 and m.eventos[-1]['guid']=='guid-2'
    assert m.energia_colocacion_J==400 and m.residual()==0


def test_pair_rebuilt_and_manual_heat_transfer():
    m=layers(k=2.)
    assert m.modelo.pares[0][2].item()==0
    m.paso(1.);assert m.modelo.pares[0][2].item()==2
    m.paso(1.);np.testing.assert_allclose(m.T,[14.,26.]);assert m.residual()==0
    assert m.reconstrucciones==2


def test_exposed_face_becomes_internal():
    border={s:dict(tipo='robin',h_W_m2K=10.,temperatura_C=10.) for s in ('x-','x+')}
    m=layers(bordes=border);old=m.modelo.G_borde[0]
    assert m.areas_expuestas()=={'x-':1.,'x+':1.}
    m.paso(1.)
    assert m.modelo.G_borde[0]==pytest.approx(old/2)
    assert m.modelo.pares[0][2].item()>0
    m.paso(.5);assert abs(m.residual())<1e-12


def test_independent_ages_and_no_negative_age():
    m=layers(starts=(0.,2.,4.),temps=(10,20,30))
    assert [m.edad_s(i) for i in (1,2,3)]==[0,0,0]
    m.paso(2.);m.paso(1.)
    assert [m.edad_s(i) for i in (1,2,3)]==[3,1,0]
    assert m.activo.tolist()==[True,True,False]


def test_empty_initial_domain_and_delayed_first_pour():
    m=layers(starts=(2.,3.))
    assert m.modelo is None and m.energia()==0
    m.paso(2.,1e9);assert m.energia_fuente_J==0 and m.T.tolist()==[10.,0.]
    m.paso(1.);assert m.activo.all() and m.residual()==0


def test_cannot_step_across_event_and_rechecks_stability():
    m=layers(k=100.)
    with pytest.raises(ValueError,match='cruza'):m.paso(2.)
    m.paso(1.);assert m.dt_max==pytest.approx(.1)
    with pytest.raises(ValueError,match='inestable'):m.paso(1.)


def test_three_layers_source_and_boundary_energy_conservation():
    m=layers(starts=(0.,.5,1.),temps=(12,22,32),bordes={'x-':dict(tipo='neumann',flujo_saliente_W_m2=3.)})
    for _ in range(10):m.paso(.1,[10.,20.,30.])
    assert m.activo.all() and len(m.eventos)==3
    assert abs(m.residual())<1e-11
    # Sólo el primer material existe hasta 0.5 s y el segundo desde 0.5 s.
    assert m.energia_fuente_J==pytest.approx(20.)
    assert m.energia_borde_J==pytest.approx(-3.)


def test_heterogeneous_properties_keep_internal_energy_conservative():
    m=ConstruccionTermica([1,2],[2.],[dict(id=1,inicio_s=0,temperatura_C=10),dict(id=2,inicio_s=0,temperatura_C=30)],k=[2.,4.],rho=[2.,3.],cp=[5.,8.])
    assert m.modelo.pares[0][2].item()==pytest.approx(8/3)
    before=m.energia();m.paso(.1);assert m.energia()==pytest.approx(before)
    assert abs(m.residual())<1e-12
