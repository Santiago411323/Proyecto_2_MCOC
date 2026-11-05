"""Pruebas del contrato gráfico con campos Python asimétricos, sin GPU."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import threading
from urllib.request import urlopen
from urllib.error import HTTPError
import numpy as np
import pytest
from therma.resultados import a_xfast
from panel.exportar_ifc import datos_ifc
from servidor_therma import Servidor

ROOT=Path(__file__).resolve().parents[1]


def test_thermal_spread_uses_simultaneous_extremes_and_reports_peak_time():
    data=dict(stats=[dict(count=1,max=60,min=50),dict(count=1,max=40,min=10)],times=[0,7200],frame=0)
    v=js('console.log(JSON.stringify(D.thermalSpread(r.stats,r.times,r.frame)));',data)
    assert v['series']==[10,30] and v['current']==10
    assert v['peak']==30 and v['peakTime']==7200  # No 60 - 10 de tiempos distintos.
    assert v['official']=='NOT EVALUATED'


@pytest.mark.parametrize('delta,exceeds',[(20,False),(20.01,True)])
def test_thermal_spread_warns_above_twenty_without_clamping(delta,exceeds):
    v=js('console.log(JSON.stringify(D.thermalSpread(r.stats,[0],0)));',dict(stats=[dict(count=1,max=10+delta,min=10)]))
    assert v['current']==delta and v['exceeds'] is exceeds
    assert v['official']=='NOT EVALUATED'


def test_thermal_spread_has_no_temperature_for_unplaced_concrete():
    v=js('console.log(JSON.stringify(D.thermalSpread(r.stats,[0,1],0)));',dict(stats=[dict(count=0,max=999,min=-999),dict(count=1,max=18,min=18)]))
    assert v['series']==[None,0] and v['current'] is None and v['exceeds'] is None
    assert v['peak']==0 and v['peakIndex']==1


def test_thermal_spread_excludes_inactive_voxels_from_extremes():
    data=dict(n=[2,1,1],config=dict(mask=[1,1]),fields=[[1000,20],[30,25]],activeFrames=[[0,1],[1,1]])
    v=js('console.log(JSON.stringify(D.thermalSpread(r.fields.map((_,j)=>D.extrema(r,j)),[0,24],1)));',data)
    assert v['series']==[0,5] and v['current']==5


def js(code, data):
    node=shutil.which('node')
    assert node, 'Node es necesario para verificar la correspondencia Python/visor.'
    script="const D=require('./panel/visordatos.js');const r=JSON.parse(require('fs').readFileSync(0,'utf8'));"+code
    out=subprocess.run([node,'-e',script],input=json.dumps(data),text=True,cwd=ROOT,capture_output=True,check=True)
    return json.loads(out.stdout)


@pytest.fixture
def field():
    x,y,z=np.indices((3,4,5));f=100*x+10*y+z
    mask=np.ones_like(f);mask[2,3,4]=0
    return dict(n=[3,4,5],dx=[.5,.7,.9],config={'origin':[-2.,3.,4.],'mask':a_xfast(mask).tolist()},
                fields=[a_xfast(f).tolist(),a_xfast(f+7).tolist()],frameTimes=[0,90])


def test_asymmetric_python_javascript_every_cell(field):
    cells=js('console.log(JSON.stringify(r.fields[0].map((v,i)=>({i,ijk:D.ijk(i,r.n),back:D.index(...D.ijk(i,r.n),r.n),p:D.xyz(r,i),v}))));',field)
    for c in cells:
        x,y,z=c['ijk'];assert c['i']==c['back'];assert c['v']==100*x+10*y+z
        np.testing.assert_allclose(c['p'],[-2+(x+.5)*.5,3+(y+.5)*.7,4+(z+.5)*.9])


def test_instance_selection_mask_and_hottest(field):
    out=js('const ids=D.instanceIndices(r);console.log(JSON.stringify({ids,e:D.extrema(r,0),selected:ids.map(i=>D.ijk(i,r.n))}));',field)
    assert len(out['ids'])==59 and 59 not in out['ids']
    assert out['e']==dict(min=0,max=233,hot=47,count=59)
    for instance,i in enumerate(out['ids']):assert out['selected'][instance]==[i%3,(i//3)%4,i//12]


@pytest.mark.parametrize('axis',[0,1,2])
def test_clipping_xyz(field,axis):
    cuts=[dict(enabled=False,position=0) for _ in range(3)];cuts[axis]=dict(enabled=True,position=[-1.25,4.4,6.25][axis]);field['cuts']=cuts
    actual=js('console.log(JSON.stringify(D.instanceIndices(r).filter(i=>D.visible(r,i,r.cuts))));',field)
    expected=[]
    for i in range(59):
        xyz=[i%3,(i//3)%4,i//12];p=field['config']['origin'][axis]+(xyz[axis]+.5)*field['dx'][axis]
        if p<=cuts[axis]['position']+1e-8:expected.append(i)
    assert actual==expected


def test_color_fixed_auto_and_manual(field):
    out=js("console.log(JSON.stringify({fixed:D.limits(r,'fixed',20,80),auto:D.limits(r,'auto'),same:D.color(50,20,80),lo:D.color(-100,20,80),hi:D.color(999,20,80)}));",field)
    assert out['fixed']==[20,80] and out['auto']==[0,240]
    assert out['lo']==[.06,.22,.65];np.testing.assert_allclose(out['hi'],[.83,.08,.14])
    np.testing.assert_allclose(out['same'],[.98,.89,.24])
    assert js("let rejected=false;try{D.limits(r,'manual',80,20)}catch(e){rejected=true}console.log(JSON.stringify(rejected));",field)


def test_snapshot_selection_and_mask_restore(field):
    assert js('console.log(JSON.stringify([D.nearest(r.frameTimes,10),D.nearest(r.frameTimes,80),D.extrema(r,1).max]));',field)==[0,1,240]
    out=js('const before=D.instanceIndices(r);D.visible(r,0,[{enabled:true,position:-99},{enabled:false},{enabled:false}]);console.log(JSON.stringify({same:JSON.stringify(before)===JSON.stringify(D.instanceIndices(r)),f:r.fields[0][1]}));',field)
    assert out==dict(same=True,f=100)


def test_ifc_voxel_centers_match_layer_bounds():
    data=datos_ifc(ROOT/'modelo_e02.ifc');mesh=data['mallas'][0]
    r=dict(n=mesh['n'],dx=mesh['dx'],config={'origin':data['min'],'mask':mesh['ids']},fields=[mesh['ids']])
    points=js('console.log(JSON.stringify(D.instanceIndices(r).map(i=>({p:D.xyz(r,i),id:r.config.mask[i]}))));',r)
    assert len(points)==sum(mesh['capas_celdas'])
    for point in points:
        layer=next(c for c in data['capas'] if c['id']==point['id'])
        assert all(lo-1e-8<=p<=hi+1e-8 for lo,p,hi in zip(layer['min'],point['p'],layer['max']))


def test_generated_html_and_vendored_integrity():
    text=(ROOT/'panel_termico.html').read_text(encoding='utf-8')
    assert '/*__VIEW' not in text and 'id="thermal3d"' in text
    manifest=json.loads((ROOT/'panel/vendor/three/manifest.json').read_text())
    for name,digest in manifest['sha256'].items():assert hashlib.sha256((ROOT/'panel/vendor/three'/name).read_bytes()).hexdigest()==digest


def test_local_modules_allowlist_and_syntax(tmp_path):
    s=Servidor(('127.0.0.1',0),tmp_path);thread=threading.Thread(target=s.serve_forever,daemon=True);thread.start()
    try:
        for path in ('/panel/visor3d.js','/panel/vendor/three/three.module.js','/panel/vendor/three/OrbitControls.js'):
            with urlopen(f'http://127.0.0.1:{s.server_port}'+path) as r:
                assert r.status==200 and r.headers['Content-Type']=='application/javascript' and len(r.read())>100
        with pytest.raises(HTTPError) as error:urlopen(f'http://127.0.0.1:{s.server_port}/panel/../servidor_therma.py')
        assert error.value.code==404
    finally:s.shutdown();s.server_close();thread.join()
    subprocess.run([shutil.which('node'),'--input-type=module','--check'],input=(ROOT/'panel/visor3d.js').read_text(encoding='utf-8'),text=True,encoding='utf-8',check=True,capture_output=True)
