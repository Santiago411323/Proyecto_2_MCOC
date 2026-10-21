import numpy as np
import pytest
from difusion_1d_bordes import resolver

D={"tipo":"dirichlet","T":20.}
N={"tipo":"neumann","q_salida":0.}


def test_dirichlet_exacto():
    r=resolver(1.,.025,100.,86400.,lambda x:20+40*np.sin(np.pi*x),D,D)
    exacta=20+40*np.sin(np.pi*r["x"])*np.exp(-r["alpha"]*np.pi**2*86400.)
    assert np.max(np.abs(r["T"]-exacta))<.01


def test_neumann_energia_y_modo_exacto():
    r=resolver(1.,.025,100.,86400.,lambda x:30+10*np.cos(np.pi*x),N,N)
    np.testing.assert_allclose(r["energia_J_m2"],r["energia_J_m2"][0],rtol=1e-12)
    exacta=30+10*np.cos(np.pi*r["x"])*np.exp(-r["alpha"]*np.pi**2*86400.)
    assert np.max(np.abs(r["T"]-exacta))<.01


def test_fuente_adiabatica():
    r=resolver(1.,.05,100.,1000.,20.,N,N,fuente_W_m3=2160.)
    np.testing.assert_allclose(r["T"],21.,atol=1e-10)


def test_neumann_flujo_saliente_enfria_y_balance():
    salida={"tipo":"neumann","q_salida":10.}
    r=resolver(1.,.05,100.,1000.,30.,salida,salida)
    assert r["energia_J_m2"][-1]-r["energia_J_m2"][0]==pytest.approx(-20000.,abs=1e-6)


def test_robin_con_modo_analitico():
    # Modo simetrico de pared plana: mu*tan(mu)=h*a/k, a=L/2.
    mu=.7; a=.5; k=2.; h=k*mu*np.tan(mu)/a
    R={"tipo":"robin","h":h,"T_ambiente":20.}
    r=resolver(1.,.0125,25.,86400.,lambda x:20+10*np.cos(mu*(x-a)/a),R,R)
    exacta=20+10*np.cos(mu*(r["x"]-a)/a)*np.exp(-r["alpha"]*(mu/a)**2*86400.)
    assert np.max(np.abs(r["T"]-exacta))<.003
    assert r["energia_J_m2"][-1]<r["energia_J_m2"][0]


def test_robin_cero_equivale_adiabatico():
    R={"tipo":"robin","h":0.,"T_ambiente":0.}
    uno=resolver(1.,.05,100.,1000.,lambda x:20+x,N,N)
    dos=resolver(1.,.05,100.,1000.,lambda x:20+x,R,R)
    np.testing.assert_allclose(uno["T"],dos["T"])


def test_robin_rechaza_paso_inestable_y_snapshots_exactos():
    R={"tipo":"robin","h":100.,"T_ambiente":20.}
    with pytest.raises(ValueError,match="inestable"):
        resolver(1.,.05,1000.,1000.,30.,R,R)
    r=resolver(1.,.05,100.,1000.,20.,N,N,guardar_en=[333.])
    assert 333. in r["perfiles"]
