import json
from pathlib import Path
import shutil
import subprocess
import uuid
import numpy as np
import pytest
from termico_cartesiano import TermicoCartesiano
from therma.moldaje import validar_moldaje,resistencia_extra
from therma.ejecutar import ejecutar
from test_construccion import config as construction_config

ROOT=Path(__file__).resolve().parents[1]


def formwork(e=.02):
    return dict(model='fixed_resistance',thickness_m=e,conductivity_W_mK=.15,
        faces=[True,True,True,True,False,False],parameter_source='Supuesto didáctico de moldaje, no material caracterizado.')


def js(code,payload):
    code="const N=require('./panel/nucleo_exterior.js'),F=require('./panel/moldaje_modelo.js'),M=require('./panel/ecuaciones_modelo.js'),p=JSON.parse(require('fs').readFileSync(0,'utf8'));"+code
    return json.loads(subprocess.run([shutil.which('node'),'-e',code],input=json.dumps(payload),encoding='utf-8',text=True,capture_output=True,check=True,cwd=ROOT).stdout)


def test_formwork_resistance_matches_python_and_equation_viewer_once():
    p=dict(geometry='foundation',dim=3,L=[1,1,1],n=[2,2,2],k=2.,formwork=formwork(),faces=[dict(type='R',temp=20,h=10,R=.3,flux=0) for _ in range(6)])
    validar_moldaje(p)
    v=js("console.log(JSON.stringify({R:F.extra(p,0),view:M.describe(p,0,{cellTemperature:40})}));",p)
    assert v['R']==pytest.approx(resistencia_extra(p,0))
    assert v['view']['flux']==pytest.approx(20/(.5/(2*2)+.3+.02/.15+1/10))
    assert resistencia_extra(p,5)==0


@pytest.mark.parametrize('change',[{'thickness_m':-1},{'conductivity_W_mK':0},{'faces':[1]*6},{'parameter_source':''}])
def test_invalid_formwork_rejected(change):
    p=dict(geometry='foundation',formwork={**formwork(),**change},faces=[dict(type='R') for _ in range(6)])
    with pytest.raises(ValueError):validar_moldaje(p)


def test_formwork_cannot_silently_override_dirichlet_or_ground():
    p=dict(geometry='foundation',formwork=formwork(),faces=[dict(type='D') for _ in range(6)])
    with pytest.raises(ValueError,match='Robin'):validar_moldaje(p)
    p['faces']=[dict(type='R') for _ in range(6)];p['formwork']['faces'][4]=True;p['environment']={'soil':{}}
    with pytest.raises(ValueError,match='base'):validar_moldaje(p)


def test_protected_surface_cools_slower_in_known_cooling_case_and_energy_closes():
    out=[]
    for R in (0.,.02/.15):
        borders={axis+sign:dict(tipo='robin',h_W_m2K=10.,R_m2K_W=R,temperatura_C=20.) for axis in 'xyz' for sign in '-+'}
        m=TermicoCartesiano((2,3,4),[1,1.5,2],k=2.,rho=2.,cp=5.,bordes=borders)
        T=np.full(m.forma,50.);E0=m.energia(T);boundary=0.;dt=.1
        for _ in range(20):
            boundary+=dt*np.sum(m.P_borde_constante-m.G_borde*T);T=m.paso(T,dt)
        assert m.energia(T)-E0==pytest.approx(boundary,abs=1e-10)
        out.append(T)
    assert np.all(out[1]>out[0])


def synthetic():
    n=[3,3,3];return dict(n=n,L=[3,3,3],dx=[1,1,1],config=dict(geometry='block',dim=3,origin=[0,0,0],mask=None),fields=[[0]*27,[0]*27],frameTimes=[0,10])


def test_fixed_core_and_exterior_are_geometry_based_not_hottest_or_coldest():
    r=synthetic();r['fields'][0][0]=1000
    v=js('console.log(JSON.stringify(N.defaults(p)));',r)
    assert v==dict(core=13,exterior=14,face=1)


def test_pair_history_uses_same_fixed_indices_ignores_other_extremes_and_missing_material():
    r=synthetic();r['fields'][0][13]=30;r['fields'][0][14]=20;r['fields'][0][0]=999
    r['fields'][1][13]=10;r['fields'][1][14]=35
    v=js('console.log(JSON.stringify(N.history(p,{core:13,exterior:14,face:1})));',r)
    assert v['delta']==[10,-25] and v['peak']==25 and v['peakTime']==10
    r['activeFrames']=[[1]*27,[1]*27];r['activeFrames'][0][13]=0
    v=js('console.log(JSON.stringify(N.history(p,{core:13,exterior:14,face:1})));',r)
    assert v['delta'][0] is None and v['core'][0] is None


def test_interior_voxel_cannot_be_labeled_as_exterior_and_soil_base_is_excluded():
    r=synthetic()
    v=js("let error=false;try{N.validatePair(p,{core:12,exterior:13,face:1});}catch(e){error=true;}console.log(JSON.stringify({error,base:N.exteriorFaces(p,4)}));",r)
    assert v['error'] and 4 not in v['base']
    errors=js("console.log(JSON.stringify([-1,27,1.5].map(core=>{try{N.validatePair(p,{core,exterior:14,face:1});return false;}catch(e){return true;}})));",r)
    assert errors==[True,True,True]


@pytest.fixture(scope='module')
def foundation_cases(tmp_path_factory):
    out=[]
    for protected in (False,True):
        p=construction_config();p['days']=14
        for v in p['construction']['pours']:v['placement_C']=18.
        if protected:p['formwork']=formwork()
        folder=tmp_path_factory.mktemp('formwork');m=ejecutar(p,uuid.uuid4().hex,folder);out.append((m,folder))
    return out


def read_pair(folder):
    code="""const fs=require('fs'),path=require('path'),vm=require('vm');global.window={};vm.runInThisContext(fs.readFileSync('panel/api.js','utf8'));function buf(name){const b=fs.readFileSync(path.join(p,name));return b.buffer.slice(b.byteOffset,b.byteOffset+b.byteLength);}const m=JSON.parse(fs.readFileSync(path.join(p,'metadata.json'),'utf8')),r=window.ThermaContract.adaptar(m,buf('fields.bin'),buf('active.bin')),pair=N.defaults(r),h=N.history(r,pair);console.log(JSON.stringify({pair,h,times:r.frameTimes}));"""
    return js(code,str(folder))


def test_real_ifc_pair_is_same_pour_and_repeatable_between_formwork_cases(foundation_cases):
    a,b=[read_pair(folder) for _,folder in foundation_cases]
    assert a['pair']==b['pair']
    ids=foundation_cases[0][0]['config']['mask'];pair=a['pair']
    assert ids[pair['core']]==ids[pair['exterior']]
    assert a['h']['delta'][0] is None  # Núcleo de vertida 2 todavía no colocado.
    common=set(a['times'])&set(b['times']);time=min(common,key=lambda t:abs(t-168*3600))
    j=a['times'].index(time);k=b['times'].index(time)
    assert b['h']['exterior'][k]>a['h']['exterior'][j]


def test_formwork_export_and_energy_are_traceable(foundation_cases):
    m,folder=foundation_cases[1]
    assert m['formwork']['resistance_m2K_W']==pytest.approx(.02/.15)
    assert m['metrics']['energy_residual_relative']<1e-12
    stored=json.loads((folder/'config.json').read_text(encoding='utf-8'))
    assert stored['formwork']==m['config']['formwork']
    assert m['validity']['project_deltaT_25mm']=='NOT EVALUATED'
