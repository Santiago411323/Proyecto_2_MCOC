import numpy as np
import pytest
from therma.hidratacion import AdiabaticaExponencial
from therma.activacion import ConstruccionTermica


def test_exponential_analytic_rate_and_integral():
    h=AdiabaticaExponencial(40.,86400.)
    assert h.elevacion(0)==0 and h.tasa_C_s(0)==40/86400
    assert h.elevacion(86400)==pytest.approx(40*(1-np.exp(-1)))
    assert h.fuente_media(0,86400,2400,900)*86400==pytest.approx(2400*900*h.elevacion(86400))


def test_each_pour_own_age_adiabatic_exact_evolution():
    # Dos piezas desconectadas: no hay conducción que oculte el reloj independiente.
    m=ConstruccionTermica([1,0,2],[3.],[dict(id=1,inicio_s=0,temperatura_C=10),dict(id=2,inicio_s=2,temperatura_C=20)],rho=2,cp=5)
    model=AdiabaticaExponencial(40.,10.)
    for _ in range(4):
        q=np.zeros(3)
        for ident in (1,2):
            active=(m.ids==ident)&m.activo
            q[active]=model.fuente_media(m.edad_s(ident),m.edad_s(ident)+1,2,5)
        m.paso(1,q)
    np.testing.assert_allclose(m.T[[0,2]],[10+model.elevacion(4),20+model.elevacion(2)],atol=1e-12)
    assert abs(m.residual())<1e-12


@pytest.mark.parametrize('theta,tau',[(40,0),(-1,100),(float('nan'),1),(40,float('inf'))])
def test_invalid_parameters(theta,tau):
    with pytest.raises(ValueError):AdiabaticaExponencial(theta,tau)


def test_invalid_age_and_zero_heat_case():
    h=AdiabaticaExponencial(0,1)
    assert h.elevacion(100)==0 and h.fuente_media(0,100,2,5)==0
    with pytest.raises(ValueError):h.elevacion(-1)
    with pytest.raises(ValueError):h.fuente_media(1,1,2,5)
