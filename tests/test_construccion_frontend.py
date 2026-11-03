"""Contrato Python→JS: actividad, sensores y comparación de dos cronogramas."""
import json
from pathlib import Path
import shutil
import subprocess
import uuid
import pytest
from therma.ejecutar import ejecutar
from test_construccion import config

ROOT=Path(__file__).resolve().parents[1]


@pytest.fixture(scope='module')
def cases(tmp_path_factory):
    folders=[]
    for starts in [(0,24,48),(0,36,72)]:
        folder=tmp_path_factory.mktemp('sequence');ejecutar(config(starts),uuid.uuid4().hex,folder);folders.append(str(folder))
    return folders


def js(code,folders):
    program="""const fs=require('fs'),path=require('path'),vm=require('vm');global.window={};vm.runInThisContext(fs.readFileSync('panel/api.js','utf8'));const D=require('./panel/visordatos.js'),I=require('./panel/inteligencia.js');const folders=JSON.parse(fs.readFileSync(0,'utf8'));function buffer(file){const b=fs.readFileSync(file);return b.buffer.slice(b.byteOffset,b.byteOffset+b.byteLength);}function load(folder){const m=JSON.parse(fs.readFileSync(path.join(folder,'metadata.json'),'utf8'));return window.ThermaContract.adaptar(m,buffer(path.join(folder,'fields.bin')),buffer(path.join(folder,'active.bin')));}const a=load(folders[0]),b=load(folders[1]);"""+code
    r=subprocess.run([shutil.which('node'),'-e',program],input=json.dumps(folders),encoding='utf-8',text=True,cwd=ROOT,capture_output=True,check=True)
    return json.loads(r.stdout)


def test_dynamic_contract_and_sensor_not_yet_poured(cases):
    out=js("I.validate(a);const i=a.config.mask.indexOf(3),s=I.makeSensor(a,i,'V3','test');const h=I.sensorHistory(a,s),j=a.frameTimes.indexOf(172800);console.log(JSON.stringify({start:h[0],placed:h[j],temp:I.packSensors(a,[s],0).sensors[0].temperature_C,visible:D.visible(a,i,[],0),suggested:I.suggestions(a).map(v=>v.name)}));",cases)
    assert out['start']['temperature'] is None and out['temp'] is None and not out['visible']
    assert out['placed']==dict(t=172800,temperature=20)
    assert any('Vertida 3' in name for name in out['suggested'])


def test_comparison_only_on_cells_active_in_both(cases):
    out=js("const pair=I.commonTimes(a,b).find(p=>p.t>86400&&p.t<129600),diff=I.difference(a,b,pair),i=a.config.mask.indexOf(2),j=a.config.mask.indexOf(1);console.log(JSON.stringify({compatible:I.compatible(a,b).ok,future:Number.isNaN(diff[i]),active:diff[j],expected:b.fields[pair.b][j]-a.fields[pair.a][j],a:D.extrema(a,pair.a).count,b:D.extrema(b,pair.b).count}));",cases)
    assert out['compatible'] and out['future'] and out['a']>out['b']
    assert out['active']==pytest.approx(out['expected'],abs=1e-6)


def test_dynamic_mask_is_mandatory_and_must_stay_inside_geometry(cases):
    out=js("let missing=false,invalid=false;try{window.ThermaContract.adaptar(a.metadata,buffer(path.join(folders[0],'fields.bin')))}catch(e){missing=true;}const outside=a.config.mask.indexOf(0);a.activeFrames[0][outside]=1;try{I.validate(a)}catch(e){invalid=true;}console.log(JSON.stringify({missing,invalid}));",cases)
    assert out==dict(missing=True,invalid=True)


def test_empty_snapshot_has_no_false_zero_temperature():
    code="const D=require('./panel/visordatos.js');console.log(JSON.stringify(D.extrema({config:{mask:[1]},fields:[[0]],activeFrames:[[0]]},0)));"
    r=subprocess.run([shutil.which('node'),'-e',code],encoding='utf-8',text=True,capture_output=True,check=True,cwd=ROOT)
    assert json.loads(r.stdout)==dict(min=None,max=None,hot=-1,count=0)


@pytest.mark.parametrize('wrong',['age','mask'])
def test_reject_inconsistent_clock_or_event_mask(cases,wrong):
    code="a.metadata.construction.snapshots[0].pours[0].age_s=100;" if wrong=='age' else "a.metadata.construction.snapshots[0].active_pour_ids.push(2);"
    assert js(code+"let rejected=false;try{I.validate(a)}catch(e){rejected=true;}console.log(JSON.stringify(rejected));",cases)
