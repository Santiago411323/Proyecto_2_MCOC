import json
import uuid
from pathlib import Path
import shutil
import subprocess
import numpy as np
import pytest
from test_construccion import config as construction_config
from therma.ejecutar import ejecutar,validar

ROOT=Path(__file__).resolve().parents[1]


def config(T=10.,mesh=0):
    p=construction_config();p['days']=14;p['meshIndex']=mesh
    p['environment']={'soil':dict(model='effective_basal_reservoir',temperature_C=T,depth_m=1.,
        conductivity_W_mK=1.5,contact_R_m2K_W=0.,parameter_source='Hipótesis didácticas de suelo, no valores medidos de Punta Arenas.')}
    return p


@pytest.fixture(scope='module')
def cases(tmp_path_factory):
    out=[]
    for T in (10.,5.):
        folder=tmp_path_factory.mktemp('soil_foundation');meta=ejecutar(config(T),uuid.uuid4().hex,folder);out.append((meta,folder))
    return out


def test_ground_and_air_energies_close_total_without_mixing(cases):
    meta,_=cases[0]
    assert meta['metrics']['energy_residual_relative']<1e-12
    assert meta['metrics']['final_soil_into_concrete_J']<0
    for h in meta['history']:
        assert h['boundary_J']==pytest.approx(h['soil_J']+h['air_J'],abs=1e-4,rel=1e-12)
        assert h['energy']==pytest.approx(h['placed_J']+h['source_J']+h['soil_J']+h['air_J'],abs=1e-4,rel=1e-12)
    assert meta['validity']['project_deltaT_25mm']=='NOT EVALUATED'
    assert meta['validity']['ground']=='EFFECTIVE_DIDACTIC_RESERVOIR'


def test_soil_only_on_geometric_base_for_every_pour_stage(cases):
    meta,folder=cases[0];env=meta['environment']
    with np.load(folder/'campos.npz') as z:
        assert z['soil_contact_geometry'][:,:,0].any() and not z['soil_contact_geometry'][:,:,1:].any()
        for snapshot in env['snapshots']:
            faces=snapshot['face_regions']
            assert faces['z-']['air']['faces']==0
            assert faces['z-']['soil']['faces']>0
            for key in ('x-','x+','y-','y+','z+'):assert faces[key]['soil']['faces']==0
    assert meta['geometry']['origin_m']==[-9.,-9.,0.]
    assert all(e['boundary_regions']['z-']['soil']['faces']>0 for e in meta['construction']['events'])


def test_colder_reservoir_never_warms_active_concrete_at_common_times(cases):
    (a,pa),(b,pb)=cases
    with np.load(pa/'campos.npz') as za,np.load(pb/'campos.npz') as zb:
        times_a=list(za['tiempo_s']);times_b=list(zb['tiempo_s']);common=set(times_a)&set(times_b)
        assert len(common)>=20
        for t in common:
            i,j=times_a.index(t),times_b.index(t);mask=za['active'][i]
            np.testing.assert_array_equal(mask,zb['active'][j])
            assert np.max(zb['T_C'][j][mask]-za['T_C'][i][mask])<1e-9
    assert b['metrics']['maxField']<=a['metrics']['maxField']


def test_exported_ground_diagnostics_reproducible_and_reference_is_explicit(cases):
    meta,folder=cases[0]
    stored=json.loads((folder/'metadata.json').read_text(encoding='utf-8'))
    assert stored['environment']['soil']['temperature_C']==10
    assert 'didácticas' in stored['provenance']['soil_parameter_source']
    assert stored['environment']['soil']['effective_resistance_m2K_W']==pytest.approx(2/3)
    with np.load(folder/'campos.npz') as z:
        np.testing.assert_allclose(z['soil_into_concrete_J'],[s['soil_into_concrete_J'] for s in meta['environment']['snapshots']])


def test_ground_config_rejects_unsupported_schedule_before_running():
    p=config();p['construction']['pours'][0]['start_h']=24;p['construction']['pours'][1]['start_h']=0
    with pytest.raises(ValueError,match='caras inferiores'):validar(p)


def test_ground_config_cannot_be_silently_used_on_a_static_example():
    p=config();p.pop('construction')
    with pytest.raises(ValueError,match='construcción'):validar(p)


@pytest.mark.parametrize('mesh',[0,1])
def test_both_existing_ifc_grids_satisfy_basal_contact_precondition(mesh):
    p=validar(config(mesh=mesh));assert p['n']==([24,24,6] if mesh==0 else [36,36,12])


def test_soil_case_temperature_contract_still_maps_exactly_to_javascript(cases):
    meta,folder=cases[0]
    code="""const fs=require('fs'),path=require('path'),vm=require('vm');global.window={};vm.runInThisContext(fs.readFileSync('panel/api.js','utf8'));const I=require('./panel/inteligencia.js'),D=require('./panel/visordatos.js');const dir=JSON.parse(fs.readFileSync(0,'utf8'));function buf(n){const b=fs.readFileSync(path.join(dir,n));return b.buffer.slice(b.byteOffset,b.byteOffset+b.byteLength);}const m=JSON.parse(fs.readFileSync(path.join(dir,'metadata.json'),'utf8')),r=window.ThermaContract.adaptar(m,buf('fields.bin'),buf('active.bin'));I.validate(r);const j=r.frameTimes.length-1;console.log(JSON.stringify({max:D.extrema(r,j).max,Tsoil:r.metadata.environment.soil.temperature_C}));"""
    proc=subprocess.run([shutil.which('node'),'-e',code],input=json.dumps(str(folder)),text=True,encoding='utf-8',capture_output=True,check=True,cwd=ROOT)
    result=json.loads(proc.stdout)
    with np.load(folder/'campos.npz') as z:assert result['max']==pytest.approx(z['T_C'][-1][z['active'][-1]].max(),abs=1e-5)
    assert result['Tsoil']==10
