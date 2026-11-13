import numpy as np
import pytest
from therma.fuente_tabulada import FuenteTabulada
from therma.ejecutar import ejecutar
from test_construccion import config


def curve():return dict(time_h=[0,1,2],Q_W_m3=[0,100,0],tail='constant_last',column='fixture',raw_sha256='test')


def test_exact_integral_crossing_knots_and_no_rho_multiplier():
    model=FuenteTabulada(curve(),2400,900)
    assert model.energia_volumetrica(7200)==pytest.approx(360000)
    assert model.fuente_media(1800,5400,1,1)==pytest.approx(75)
    assert model.elevacion(7200)==pytest.approx(1/6)
    assert model.energia_volumetrica(9000)==pytest.approx(360000)
    c=curve();c['Q_W_m3']=[100,100,100]
    assert FuenteTabulada(c,2400,900).energia_volumetrica(10800)==1080000


@pytest.mark.parametrize('key,value',[('Q_W_m3',[0,float('nan'),1]),('Q_W_m3',[0,-1,0]),('time_h',[0,0,1]),('tail','silent')])
def test_rejects_bad_curve(key,value):
    c=curve();c[key]=value
    with pytest.raises(ValueError):FuenteTabulada(c,2400,900)


def test_integration_observer_and_energy(tmp_path):
    p=config((0,1,2));p['days']=.15
    p['construction']=dict(model='tabulated_source',curve=curve(),parameter_source='Fuente tabulada de prueba.',
        pours=[dict(id=i+1,start_h=i,placement_C=18) for i in range(3)])
    observed=[]
    m=ejecutar(p,'table',tmp_path,observer=lambda solver,p,h:observed.append(h['t']))
    assert len(observed)==len(m['history'])
    assert m['metrics']['energy_residual_relative']<1e-12
    assert m['construction']['model']=='tabulated_source'


def test_surface_reconstruction_uses_robin_half_cell():
    from types import SimpleNamespace
    from therma.diagnostico_e12 import Diagnostico
    m=SimpleNamespace(ids=np.ones((2,2,2),int),activo=np.ones((2,2,2),bool),
        forma=(2,2,2),dx=np.ones(3),T=np.full((2,2,2),40.),t=0.)
    p=dict(origin=[0,0,0],k=2.,faces=[dict(type='R',h=10.,R=0.) for _ in range(6)])
    d=Diagnostico();d(m,p,dict(max=40.,air_temperature_C=10.))
    qout=30/(.5/2+1/10)
    assert d.peak['surface_C']==pytest.approx(40-qout*.5/2)
    assert d.peak['delta_C']==pytest.approx(qout*.5/2)
    assert d.peak['delta_S25_estimated_C']==pytest.approx(qout*(.5-.025)/2)


def test_panel_roundtrip_keeps_provided_source_instead_of_exponential():
    import json,shutil,subprocess
    from pathlib import Path
    node=shutil.which('node')
    if not node:pytest.skip('Node requerido para comprobar interfaz.')
    c=curve()
    script="""
    const elements={};function element(){return {value:'',checked:false,append(){},addEventListener(){},removeAttribute(){},setAttribute(){},querySelector(){return element();}};}
    global.document={getElementById(id){return elements[id]??=(element());},createElement(){return element();}};
    document.getElementById('foundation-data').textContent=JSON.stringify({capas:[{id:1,nombre:'V1',guid:'g',inicio_h:0,temperatura_colocacion_C:18}]});
    global.window={addEventListener(){}};
    document.getElementById('geometry').value='foundation';
    """
    script+=Path('panel/construccion.js').read_text(encoding='utf-8')
    script+="\nconst curve="+json.dumps(c)+"; window.ThermaConstructionUI.set({geometry:'foundation',construction:{model:'tabulated_source',curve,parameter_source:'fixture',pours:[{id:1,start_h:24,placement_C:18}]}}); console.log(JSON.stringify(window.ThermaConstructionUI.config()));"
    result=json.loads(subprocess.check_output([node,'-e',script],text=True))
    assert result['model']=='tabulated_source' and result['curve']==c
    assert result['pours']==[dict(id=1,start_h=24,placement_C=18)]
