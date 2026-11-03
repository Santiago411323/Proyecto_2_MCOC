"""5A: circuitos térmicos analíticos, caras disjuntas y energía conservativa."""
import math
import numpy as np
import pytest
from termico_cartesiano import TermicoCartesiano
from therma.activacion import ConstruccionTermica
from therma.suelo import SueloEfectivo,clasificar_caras,resumen_caras,validar_entorno


def soil(T=10.,L=1.,k=1.5,R=0.):
    return SueloEfectivo(T,L,k,R,'Hipótesis didácticas declaradas, no propiedades medidas en Magallanes.')


def body(T=40.,ground=None,borders=None):
    return ConstruccionTermica(np.ones((1,1,1),int),[1.,1.,1.],
        [dict(id=1,inicio_s=0.,temperatura_C=T)],k=2.,rho=2.,cp=5.,bordes=borders,suelo=ground or soil())


@pytest.mark.parametrize('T,expected_sign',[(40.,-1),(5.,1),(10.,0)])
def test_heat_flow_sign_and_half_concrete_resistance(T,expected_sign):
    m=body(T);power=float((m.P_suelo-m.G_suelo*m.T).sum())
    expected=(10-T)/(.5/2+1/1.5)
    assert power==pytest.approx(expected)
    assert np.sign(power)==expected_sign
    before=m.energia();m.paso(.1)
    assert m.energia()-before==pytest.approx(.1*expected,abs=1e-12)
    assert m.energia_suelo_J==pytest.approx(.1*expected)
    assert abs(m.residual())<1e-12 and abs(m.energia_aire_J)<1e-12


def test_more_soil_resistance_reduces_same_instantaneous_flux():
    a,b=body(40,soil(L=.5)),body(40,soil(L=2.))
    qa=float((a.P_suelo-a.G_suelo*a.T).sum());qb=float((b.P_suelo-b.G_suelo*b.T).sum())
    assert abs(qa)>abs(qb)>0 and a.dt_max<b.dt_max


def test_contact_resistance_in_series_exactly_once():
    m=body(40,soil(R=.2));expected=1/(.5/2+1/1.5+.2)
    assert m.G_suelo.item()==pytest.approx(expected)
    assert m.modelo.G_borde.item()==pytest.approx(expected)


def test_corner_has_soil_and_five_air_faces_without_double_count():
    b={f'{axis}{s}':dict(tipo='robin',h_W_m2K=10.,R_m2K_W=0.,temperatura_C=20.) for axis in 'xyz' for s in '-+'}
    m=body(40,borders=b)
    Gsoil=1/(.25+1/1.5);Gair=1/(.25+1/10)
    assert m.modelo.G_borde.item()==pytest.approx(Gsoil+5*Gair)
    m.paso(.1)
    assert m.energia_suelo_J==pytest.approx(.1*Gsoil*(10-40))
    assert m.energia_aire_J==pytest.approx(.1*5*Gair*(20-40))
    assert m.energia_borde_J==pytest.approx(m.energia_suelo_J+m.energia_aire_J)
    assert abs(m.residual())<1e-12


def test_exact_steady_composite_slab_against_fourier_resistances():
    # Superficie superior a 40, reservorio inferior a 10. Perfil lineal exacto.
    ground=soil(R=.1);n=8;L=1.;kc=2.;dz=L/n
    active=np.ones(n,bool);b=ground.bordes(active,{'x+':dict(tipo='dirichlet',temperatura_C=40.)})
    m=TermicoCartesiano((n,),[L],k=kc,rho=2.,cp=5.,bordes=b)
    flux=(40-10)/(L/kc+ground.resistance_m2K_W)
    z=(np.arange(n)+.5)*dz;T=10+flux*(ground.resistance_m2K_W+z/kc)
    np.testing.assert_allclose(m.potencias(T),0.,atol=3e-13)
    G,P=ground.terminos_diagnosticos(m)
    assert float(np.sum(P-G*T))==pytest.approx(-flux)


def test_transient_single_cell_matches_ode_and_first_order_time_convergence():
    errors=[]
    for dt in (.1,.05,.025):
        m=body(40);G=m.G_suelo.item();exact=10+30*math.exp(-G*2/10)
        for _ in range(round(2/dt)):m.paso(dt)
        errors.append(abs(m.T.item()-exact));assert abs(m.residual())<1e-12
    assert 1.9<errors[0]/errors[1]<2.1 and 1.9<errors[1]/errors[2]<2.1


def test_face_classes_are_exhaustive_disjoint_and_distinguish_underside_air():
    active=np.zeros((2,2,3),bool);active[0,0,0]=True;active[0,0,1]=True;active[1,1,2]=True
    classes=clasificar_caras(active)
    for masks in classes.values():
        total=sum(v.astype(int) for v in masks.values())
        np.testing.assert_array_equal(total,active.astype(int))
    assert classes['z-']['soil'][0,0,0]
    assert classes['z-']['internal'][0,0,1]
    assert classes['z-']['air'][1,1,2]
    summary=resumen_caras(active,[.5,.5,.25]);assert summary['z-']['soil']['area_m2']==.25


def test_unsupported_floating_underside_is_rejected_not_assigned_soil():
    active=np.array([[[False,True]]])
    with pytest.raises(ValueError,match='caras inferiores'):soil().bordes(active,{})


def test_activation_rebuild_keeps_ground_contact_separate_from_internal_pour():
    m=ConstruccionTermica(np.array([[[1,2]]]),[1,1,2],
       [dict(id=1,inicio_s=0.,temperatura_C=10.),dict(id=2,inicio_s=1.,temperatura_C=30.)],
       k=2.,rho=2.,cp=5.,suelo=soil())
    m.paso(1.)
    assert m.G_suelo[0,0,0]>0 and m.G_suelo[0,0,1]==0
    assert m.modelo.pares[2][2].item()==2.
    for _ in range(5):m.paso(.1)
    assert abs(m.residual())<1e-12
    assert m.energia_borde_J==pytest.approx(m.energia_suelo_J+m.energia_aire_J)


def test_ground_cfl_rejects_unstable_time_step():
    m=body(40,soil(L=.001,k=1000))
    assert m.dt_max<3
    with pytest.raises(ValueError,match='inestable'):m.paso(m.dt_max*1.01)


@pytest.mark.parametrize('args',[dict(depth_m=0),dict(conductivity_W_mK=-1),dict(contact_R_m2K_W=-1),dict(temperature_C=float('nan')),dict(parameter_source=''),dict(temperature_C=True)])
def test_invalid_soil_inputs(args):
    p=dict(temperature_C=10.,depth_m=1.,conductivity_W_mK=1.5,contact_R_m2K_W=0.,parameter_source='Caso didáctico declarado.');p.update(args)
    with pytest.raises(ValueError):SueloEfectivo(**p)
