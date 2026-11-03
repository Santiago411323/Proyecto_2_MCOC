"""Campos asimétricos, sensores persistidos y comparación sin remuestreo."""
import json
from pathlib import Path
import shutil
import subprocess
import uuid
import numpy as np
import pytest
from therma.ejecutar import ejecutar
from therma.resultados import a_xfast

ROOT=Path(__file__).resolve().parents[1]


def js(code,r):
    script="const I=require('./panel/inteligencia.js'),D=require('./panel/visordatos.js');const r=JSON.parse(require('fs').readFileSync(0,'utf8'));"+code
    out=subprocess.run([shutil.which('node'),'-e',script],input=json.dumps(r),text=True,encoding='utf-8',capture_output=True,cwd=ROOT,check=True)
    return json.loads(out.stdout)


@pytest.fixture
def field():
    x,y,z=np.indices((3,4,5));f=100*x+10*y+z
    mask=np.ones_like(f);mask[2,3,4]=0
    return dict(n=[3,4,5],L=[1.5,2.8,4.5],dx=[.5,.7,.9],config={'geometry':'block','origin':[-2,3,4],'mask':a_xfast(mask).tolist()},simulationId='run-a',fields=[a_xfast(f).tolist(),a_xfast(f+7).tolist()],frameTimes=[0,90])


def test_sensor_selection_value_history_coordinates(field):
    out=js("I.validate(r);const s=I.makeSensor(r,47,'Núcleo','test-s');console.log(JSON.stringify({s,history:I.sensorHistory(r,s)}));",field)
    assert out['s']['ijk']==[2,3,3] and out['s']['originScenario']=='run-a'
    np.testing.assert_allclose(out['s']['position'],[-.75,5.45,7.15])
    assert out['history']==[dict(t=0,temperature=233),dict(t=90,temperature=240)]


@pytest.mark.parametrize('index',[-1,59,60,1.5])
def test_reject_sensor_outside_active_domain(field,index):
    field['bad_index']=index
    assert js("let rejected=false;try{I.makeSensor(r,r.bad_index)}catch(e){rejected=true}console.log(JSON.stringify(rejected));",field)


def test_sensor_roundtrip_preserves_name_visibility_selection(field):
    out=js("const s=I.makeSensor(r,1,'Sensor renombrado','a');s.visible=false;s.selected=false;const stored=JSON.parse(JSON.stringify(I.packSensors(r,[s])));console.log(JSON.stringify(I.restoreSensors(r,stored)));",field)
    assert len(out)==1 and out[0]['id']=='a' and out[0]['name']=='Sensor renombrado'
    assert not out[0]['visible'] and not out[0]['selected']


def test_recovery_rejects_other_dataset_and_corrupt_sensor(field):
    out=js("const p=I.packSensors(r,[I.makeSensor(r,1,'A','id')]);const other={...r,simulationId:'run-b'};const wrong=I.restoreSensors(other,p);p.sensors[0].position[0]+=1;console.log(JSON.stringify([wrong,I.restoreSensors(r,p)]));",field)
    assert out==[[],[]]


def test_global_maximum_excludes_inactive_cell_and_timeline(field):
    out=js('console.log(JSON.stringify({peak:I.globalMaximum(r),pairs:I.commonTimes(r,{...r,frameTimes:[30,90]})}));',field)
    assert out['peak']==dict(value=240,index=47,frame=1,time=90)
    assert out['pairs']==[dict(t=90,a=1,b=1)]


def test_temporal_alignment_does_not_interpolate_or_extrapolate(field):
    out=js('console.log(JSON.stringify([I.commonTimes(r,{...r,frameTimes:[30,100]}),I.commonTimes(r,{...r,frameTimes:[0,30,90,200]})]));',field)
    assert out==[[],[dict(t=0,a=0,b=0),dict(t=90,a=1,b=2)]]


def test_difference_is_b_minus_a_at_same_instant_and_preserves_inputs(field):
    out=js("const b={...r,simulationId:'run-b',fields:r.fields.map(f=>f.map(v=>v+3.25))};const before=JSON.stringify(r);const diff=I.difference(r,b,I.commonTimes(r,b)[1]);console.log(JSON.stringify({values:Array.from(diff),same:before===JSON.stringify(r)}));",field)
    np.testing.assert_allclose(out['values'][:59],3.25);assert out['values'][59]==0 and out['same']


@pytest.mark.parametrize('change',[{'dx':[1,.7,.9]},{'L':[3,2.8,4.5]},{'n':[4,3,5]},{'config':{'geometry':'block','origin':[0,3,4],'mask':None}},{'config':{'geometry':'foundation','origin':[-2,3,4],'mask':None}}])
def test_incompatible_geometry_rejects_difference(field,change):
    field['change']=change
    out=js("const b={...r,...r.change};let rejected=false;try{I.difference(r,b,{t:0,a:0,b:0})}catch(e){rejected=true}console.log(JSON.stringify({ok:I.compatible(r,b).ok,rejected}));",field)
    assert out==dict(ok=False,rejected=True)


def test_difference_rejects_mismatched_times(field):
    assert js("let rejected=false;try{I.difference(r,r,{t:0,a:0,b:1})}catch(e){rejected=true}console.log(JSON.stringify(rejected));",field)


@pytest.mark.parametrize('change',[{'frameTimes':[0,0]},{'frameTimes':[0,-1]},{'fields':[[1,2],[3,4]]}])
def test_validation_rejects_invalid_fields_and_time(field,change):
    field.update(change)
    assert js("let rejected=false;try{I.validate(r)}catch(e){rejected=true}console.log(JSON.stringify(rejected));",field)


def test_geometric_suggestions_active_and_not_claim_25mm(field):
    out=js('console.log(JSON.stringify(I.suggestions(r)));',field)
    assert len(out)==3
    for s in out:assert field['config']['mask'][s['index']]>0 and s['depth']>0
    assert out[2]['index']//12==0


def test_delta_palette_zero_negative_positive_and_symmetric():
    out=js('console.log(JSON.stringify([I.deltaColor(-20,20),I.deltaColor(0,20),I.deltaColor(20,20)]));',{})
    np.testing.assert_allclose(out,[[.12,.42,.88],[.92,.94,.97],[.95,.31,.12]])


def test_actual_python_critical_step_field_exported(tmp_path):
    meta=ejecutar(dict(dim=3,geometry='block',n=[6,6,4],L=[3.,3.,.6],source='pulse',period=172800.,qmax=1000.,days=4,frames=20),uuid.uuid4().hex,tmp_path)
    peak=meta['metrics']['global_peak_time_s'];times=meta['fields']['times_s']
    assert meta['metrics']['global_peak_field_exported'] and peak in times
    with np.load(tmp_path/'campos.npz') as z:
        np.testing.assert_allclose(z['T_C'][times.index(peak)].max(),meta['metrics']['maxField'],rtol=0,atol=1e-10)
    assert meta['fields']['exact_global_peak_time_s']==peak
    assert len(times)==21  # critical field is additional to the 20 regular snapshots


def test_actual_python_contract_and_sensor_match_binary(tmp_path):
    meta=ejecutar(dict(dim=3,geometry='block',n=[4,3,2],L=[2.,1.5,1.],source='constant',qmax=100.,days=.1,frames=20),uuid.uuid4().hex,tmp_path)
    raw=np.fromfile(tmp_path/'fields.bin',dtype='<f4').reshape(meta['fields']['shape'])
    r=dict(metadata=meta,simulationId=meta['simulation_id'],n=meta['geometry']['shape_xyz'],L=meta['geometry']['lengths_m'],dx=meta['geometry']['spacing_m'],config=meta['config'],fields=raw.tolist(),frameTimes=meta['fields']['times_s'])
    out=js("I.validate(r);const s=I.makeSensor(r,5,'Python','s');console.log(JSON.stringify(I.sensorHistory(r,s)));",r)
    np.testing.assert_array_equal([v['temperature'] for v in out],raw[:,5])
    wrong=json.loads(json.dumps(r));wrong['metadata']['geometry']['origin_m'][0]=99
    assert js("let rejected=false;try{I.validate(r)}catch(e){rejected=true}console.log(JSON.stringify(rejected));",wrong)


@pytest.mark.parametrize('name',['comparador3d.js','investigacion.js','archivo_local.js','visor3d.js'])
def test_phase3_module_syntax(name):
    subprocess.run([shutil.which('node'),'--input-type=module','--check'],input=(ROOT/'panel'/name).read_text(encoding='utf-8'),encoding='utf-8',text=True,capture_output=True,check=True)


def test_persisted_sensor_temperature_and_time_are_same_snapshot(field):
    out=js("const s=I.makeSensor(r,1,'A','s');console.log(JSON.stringify(I.packSensors(r,[s],1)));",field)
    assert out['current_time_s']==90 and out['sensors'][0]['temperature_C']==107
    assert out['units']==dict(temperature='degC',time='s',position='m')
