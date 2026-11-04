"""Verifica el álgebra visible contra flujos del motor oficial, sin otra PDE."""
import json
from pathlib import Path
import shutil
import subprocess
import numpy as np
import pytest
from termico_cartesiano import TermicoCartesiano

ROOT=Path(__file__).resolve().parents[1]


def js(expression, payload):
    code="const M=require('./panel/ecuaciones_modelo.js'),p=JSON.parse(require('fs').readFileSync(0,'utf8'));console.log(JSON.stringify("+expression+"));"
    return json.loads(subprocess.run([shutil.which('node'),'-e',code],input=json.dumps(payload),encoding='utf-8',text=True,capture_output=True,check=True,cwd=ROOT).stdout)


def config(kind='R', **kw):
    return dict(dim=3,geometry='block',n=[2,3,4],L=[1.,3.,2.],origin=[0,0,0],mask=None,k=2.,
        faces=[dict(type=kind,temp=20.,flux=150.,h=12.,R=0.,**kw) for _ in range(6)])


@pytest.mark.parametrize('Tb',[20.,15.,-5.])
def test_dirichlet_live_temperature_no_invented_flux(Tb):
    p=config('D');p['faces'][0]['temp']=Tb
    v=js('M.describe(p,0)',p)
    assert v['type']=='D' and v['flux'] is None
    assert v['rows'][0][2]==Tb and v['rows'][0][3]=='°C'
    assert str(int(Tb)) in v['substitution']


@pytest.mark.parametrize('q,word',[(150.,'pierde'),(0.,'adiabática'),(-150.,'entra')])
def test_neumann_sign_and_normal_gradient(q,word):
    p=config('N');p['faces'][0]['flux']=q
    v=js('M.describe(p,0)',p)
    assert v['flux']==q and word in v['explanation']
    assert '−k ∇T · n' in v['formula']
    assert any(row[3]=='K/m' for row in v['rows'])


@pytest.mark.parametrize('h,R,T',[(12.,0.,35.),(20.,.4,35.),(10.,0.,10.),(10.,2.,20.),(0.,0.,35.)])
def test_discrete_robin_matches_actual_python_boundary_power(h,R,T):
    p=config();p['faces'][0].update(h=h,R=R)
    v=js('M.describe(p,0,{cellTemperature:'+str(T)+'})',p)
    motor=TermicoCartesiano((2,3,4),p['L'],k=2.,rho=2400.,cp=900.,bordes={'x-':dict(tipo='robin',h_W_m2K=h,R_m2K_W=R,temperatura_C=20.)})
    cell=(0,1,1);area=motor.volumen/motor.dx[0]
    inward=motor.P_borde_constante[cell]-motor.G_borde[cell]*T
    assert v['flux']==pytest.approx(-inward/area)
    assert all(row[2] is None for row in v['rows'] if row[0]=='T_s')


def test_surface_unknown_is_not_replaced_by_initial_or_voxel_temperature():
    p=config();p['initial']=35.
    v=js('M.describe(p,0)',p)
    assert v['flux'] is None and 'T_s' in v['substitution']
    assert next(row[2] for row in v['rows'] if row[0]=='T_celda') is None


def test_protection_decomposition_and_disabling_changes_same_resistance():
    parts=[dict(enabled=True,e=.02,k=.15),dict(enabled=True,e=.03,k=.04)]
    total=js('M.layers(p)',parts)
    assert total==pytest.approx(.02/.15+.03/.04)
    parts[1]['e']=.06;assert js('M.layers(p)',parts)==pytest.approx(.02/.15+.06/.04)
    parts[0]['enabled']=False;assert js('M.layers(p)',parts)==pytest.approx(.06/.04)
    # Deshabilitar una protección cambia R; no crea un evento de retiro temporal.
    parts[1]['enabled']=False;assert js('M.layers(p)',parts)==0


def test_soil_uses_reservoir_resistance_not_air_film():
    p=config();p['environment']=dict(soil=dict(temperature_C=10.,depth_m=1.,conductivity_W_mK=1.5,contact_R_m2K_W=.2))
    v=js('M.describe(p,4,{cellTemperature:40})',p)
    assert v['type']=='soil'
    assert v['flux']==pytest.approx(30/(.5/(2*2)+.2+1/1.5))
    p['faces'][4]['h']=9999
    assert js('M.describe(p,4,{cellTemperature:40})',p)['flux']==v['flux']


def dataset():
    return dict(n=[2,3,4],L=[1,3,2],dx=[.5,1,.5],config=config(),fields=[[30]*24],activeFrames=[[1]*24])


def test_face_classification_internal_cut_air_and_unplaced():
    r=dataset()
    assert js('M.faceClass(p,0,0,0)',r)=='air'
    assert js('M.faceClass(p,0,1,0)',r)=='internal'
    r['activeFrames'][0][1]=0
    assert js('M.faceClass(p,0,1,0)',r)=='air'
    assert js('M.faceClass(p,1,0,0)',r)=='inactive'
    r['config']['environment']={'soil':{}}
    assert js('M.faceClass(p,0,4,0)',r)=='soil'


def test_internal_and_inactive_do_not_apply_exterior_controls():
    for cls in ('internal','inactive'):
        p=config()
        v=js("M.describe(p,0,{cellTemperature:99,classification:'"+cls+"'})",p)
        assert v['flux'] is None and v['type']==cls


def test_old_temperature_not_compatible_after_mesh_change():
    r=dataset();c=config()
    assert js('M.compatible(p.c,p.r)',dict(c=c,r=r))
    c['n'][0]=4
    assert not js('M.compatible(p.c,p.r)',dict(c=c,r=r))


def test_inputs_update_and_equation_controls_do_not_execute_solver():
    # Evitar la regresión de ejecutar una PDE desde el visor algebraico.
    ui=(ROOT/'panel/ecuaciones.js').read_text(encoding='utf-8')
    assert '.run(' not in ui and 'fetch(' not in ui and 'new Worker' not in ui
    assert "target.dispatchEvent(new Event('input',{bubbles:true}))" in ui
    app=(ROOT/'panel/app.js').read_text(encoding='utf-8')
    assert "execution('STALE'" in app and "new Event('therma:inputs')" in app


def test_offline_generation_includes_equations_and_no_remote_math_dependency():
    html=(ROOT/'panel_termico.html').read_text(encoding='utf-8')
    assert '/*__EQUATION' not in html
    assert 'id="equationViewer"' in html and 'id="openEquation"' in html
    assert 'Math/MathML' in html
    for file in ('ecuaciones.js','ecuaciones_modelo.js'):
        subprocess.run([shutil.which('node'),'--check',str(ROOT/'panel'/file)],capture_output=True,check=True)
