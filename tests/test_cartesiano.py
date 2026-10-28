import numpy as np
import pytest
from termico_cartesiano import TermicoCartesiano
from casos_verificacion import sinusoidal


@pytest.mark.parametrize("dimension", [1,2,3])
def test_sinusoidal_exacta_y_refinamiento(dimension):
    errores=[]
    for n in (8,16):
        modelo,r,exacta,dt=sinusoidal(dimension,n)
        errores.append(np.max(np.abs(r["T"]-exacta)))
        assert np.min(r["T"]) >= 20.
        assert np.max(r["T"]) <= 30.
    assert errores[1] < errores[0]/3.2
    assert errores[1] < .025


@pytest.mark.parametrize("dimension", [1,2,3])
def test_adiabatico_conserva_energia(dimension):
    modelo=TermicoCartesiano((6,)*dimension,(1.,)*dimension,k=1.,rho=2.,cp=3.)
    T=np.random.default_rng(17).uniform(10,50,modelo.forma)
    r=modelo.resolver(T,.1,.8*modelo.dt_max)
    np.testing.assert_allclose(r["energia_J"],r["energia_J"][0],rtol=1e-12)


@pytest.mark.parametrize("dimension", [1,2,3])
def test_fuente_uniforme_aumento_lineal(dimension):
    modelo=TermicoCartesiano((4,)*dimension,(1.,)*dimension,k=1.,rho=2.,cp=3.)
    r=modelo.resolver(20.,.1,.8*modelo.dt_max,fuente_W_m3=12.)
    np.testing.assert_allclose(r["T"],20.2,atol=1e-12)
    assert r["energia_J"][-1]-r["energia_J"][0] == pytest.approx(1.2)


@pytest.mark.parametrize("dimension", [1,2,3])
def test_neumann_flujo_saliente_signo_y_unidades(dimension):
    bordes={f"{'xyz'[a]}{s}":{"tipo":"neumann","flujo_saliente_W_m2":2.}
            for a in range(dimension) for s in ("-", "+")}
    modelo=TermicoCartesiano((4,)*dimension,(1.,)*dimension,k=1.,rho=2.,cp=3.,bordes=bordes)
    r=modelo.resolver(30.,.1,.8*modelo.dt_max)
    assert r["energia_J"][-1]-r["energia_J"][0] == pytest.approx(-.4*dimension)
    assert np.max(r["T"]) <= 30.


@pytest.mark.parametrize("dimension", [1,2,3])
def test_robin_solucion_analitica_pared(dimension):
    # Modo coseno: mu*tan(mu)=h*a/k; otras direcciones adiabaticas.
    mu=.7; a=.5; h=mu*np.tan(mu)/a
    R={"tipo":"robin","h_W_m2K":h,"temperatura_C":20.}
    modelo=TermicoCartesiano((32,)+(2,)*(dimension-1),(1.,)*dimension,k=1.,rho=1.,cp=1.,
                             bordes={"x-":R,"x+":R})
    perfil=np.cos(mu*(modelo.coordenadas[0]-a)/a)
    r=modelo.resolver(20+10*perfil,.1,.7*modelo.dt_max)
    exacta=20+10*perfil*np.exp(-(mu/a)**2*.1)
    assert np.max(np.abs(r["T"]-exacta)) < .003
    assert r["energia_J"][-1] < r["energia_J"][0]


def test_interfaz_dos_materiales_perfil_estacionario():
    n=20; x=(np.arange(n)+.5)/n
    k=np.where(x<.5,1.,4.)
    modelo=TermicoCartesiano((n,),(1.,),k=k,rho=1.,cp=1.,bordes={
        "x-":{"tipo":"dirichlet","temperatura_C":100.},
        "x+":{"tipo":"dirichlet","temperatura_C":0.}})
    q=100/(.5/1+.5/4)
    exacta=np.where(x<.5,100-q*x,100-q*.5-q*(x-.5)/4)
    np.testing.assert_allclose(modelo.potencias(exacta),0.,atol=1e-10)
    r=modelo.resolver(exacta,.05,.7*modelo.dt_max)
    np.testing.assert_allclose(r["T"],exacta,atol=1e-10)


def test_balance_global_con_robin_y_fuente():
    modelo=TermicoCartesiano((5,6,4),(1.,2.,.5),k=2.,rho=2.,cp=3.,bordes={
        "x+":{"tipo":"robin","h_W_m2K":5.,"temperatura_C":10.},
        "z-":{"tipo":"neumann","flujo_saliente_W_m2":1.}})
    r=modelo.resolver(30.,.1,.8*modelo.dt_max,fuente_W_m3=4.)
    np.testing.assert_allclose(r["energia_J"]-r["energia_J"][0],r["entrada_acumulada_J"],atol=1e-11)


def test_estabilidad_3d_limite_local_y_robin():
    modelo=TermicoCartesiano((5,5,5),(1.,1.,1.),k=1.,rho=1.,cp=1.)
    assert modelo.dt_max == pytest.approx(.2**2/6)
    with pytest.raises(ValueError,match="inestable"):
        modelo.resolver(20.,1.,modelo.dt_max*1.01)
    R={"tipo":"robin","h_W_m2K":1000.,"temperatura_C":0.}
    con_borde=TermicoCartesiano((5,5,5),(1.,1.,1.),k=1.,rho=1.,cp=1.,
        bordes={f"{a}{s}":R for a in "xyz" for s in ("-", "+")})
    assert con_borde.dt_max < modelo.dt_max


def test_mascara_sin_flujo_entre_componentes_desconectados():
    modelo=TermicoCartesiano((3,),(1.,),k=1.,rho=1.,cp=1.,activo=[True,False,True])
    np.testing.assert_allclose(modelo.paso([10,0,30],1.),[10,0,30])


def test_grilla_anisotropa_y_energia():
    modelo=TermicoCartesiano((4,5),(1.,3.),k=1.,rho=2.,cp=3.)
    r=modelo.resolver(20.,.17,.8*modelo.dt_max,fuente_W_m3=12.,guardar_en=[.013])
    np.testing.assert_allclose(r["T"],20+2*.17)
    assert .013 in r["snapshots"]
    assert r["energia_J"][-1]-r["energia_J"][0] == pytest.approx(12*3*.17)


@pytest.mark.parametrize("dimension",[1,2,3])
def test_refinamiento_temporal(dimension):
    modelo,r1,_,dt=sinusoidal(dimension,12,.8)
    coordenadas=modelo.coordenadas
    perfil=np.prod([np.sin(np.pi*x) for x in coordenadas],axis=0)
    # Solucion exacta del sistema espacial discretizado: aisla el error temporal.
    tasa=4*dimension*np.sin(np.pi/(2*12))**2/(1/12)**2
    exacta=20+10*perfil*np.exp(-tasa*.03)
    r2=modelo.resolver(20+10*perfil,.03,dt/4)
    assert np.max(np.abs(r2["T"]-exacta)) < np.max(np.abs(r1["T"]-exacta))/3.5
