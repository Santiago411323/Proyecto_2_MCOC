"""Catálogo real y explicación del resultado sin mezclar entradas nuevas."""
import json, subprocess, shutil
from pathlib import Path
import pytest
from servidor_therma import catalogo_simulaciones
from test_fase1_python import server,request,completar,config
ROOT=Path(__file__).resolve().parents[1]


def test_catalog_http_lists_completed_real_run_only(server):
    assert json.loads(request(server,'/api/simulation-catalog')[1])['simulations']==[]
    job=completar(server,config(k=3.))
    assert job['status']=='COMPLETED'
    rows=json.loads(request(server,'/api/simulation-catalog')[1])['simulations']
    assert len(rows)==1 and rows[0]['simulation_id']==job['simulation_id']
    assert rows[0]['geometry']=='block' and rows[0]['dim']==1 and rows[0]['days']==1.
    assert rows[0]['lengths_m']==[1.]
    p=config();p.update(dtMode='manual',dt=1e12)
    assert completar(server,p)['status']=='FAILED'
    assert len(json.loads(request(server,'/api/simulation-catalog')[1])['simulations'])==1


def test_catalog_ignores_partial_corrupt_or_mismatched_files(tmp_path):
    for i,meta in enumerate([{'status':'RUNNING'},None,42,[],{'status':'COMPLETED','simulation_id':'wrong'}]):
        folder=tmp_path/(str(i)*32);folder.mkdir();(folder/'fields.bin').write_bytes(b'')
        (folder/'metadata.json').write_text('broken' if meta is None else json.dumps(meta))
    assert catalogo_simulaciones(tmp_path)==[]


def js(expression):
    node=shutil.which('node')
    if not node:pytest.skip('Node no disponible')
    script="const M=require('./panel/simulaciones.js');console.log(JSON.stringify("+expression+"));"
    return json.loads(subprocess.check_output([node,'-e',script],cwd=ROOT,encoding='utf-8'))


def test_explanation_uses_actual_result_geometry_and_saved_physical_inputs():
    r=dict(config=dict(geometry='foundation',dim=3,initial=12,k=2,rho=2476,cp=1023,
        construction=dict(model='tabulated_source',curve=dict(column='M4_SS'),pours=[dict(id=1,start_h=6,placement_C=12)]),weather={"provenance":{}},
        foundation_parameters={'width_m':16}),L=[20,16,2.6],n=[80,64,12],frameTimes=[0,3600,7200])
    rows=dict(js('M.facts('+json.dumps(r)+')'))
    assert rows['Dominio']=='Fundación IFC · variante geométrica'
    assert '20 × 16 × 2,6' in rows['Dimensiones y malla']
    assert rows['Colocación']=='V1: 6 h / 12 °C'
    assert rows['Calor y ambiente']=='M4_SS · clima horario cargado'
    assert '2 h · 3 campos' in rows['Horizonte disponible']


@pytest.mark.parametrize('state,has,label',[
    ('READY',False,'Sin resultados'),('STALE',True,'Resultados anteriores'),
    ('RUNNING',True,'Calculando en Python'),('FAILED',True,'Cálculo fallido'),('COMPLETED',True,'Resultado calculado')])
def test_explanation_separates_stale_error_execution_and_playback(state,has,label):
    assert js('M.status('+json.dumps(state)+','+json.dumps(has)+')')[0]==label


def test_loading_archived_fields_is_not_claimed_as_a_new_solver_run():
    assert js('M.status("RUNNING",true,"Cargando plan ya calculado")')[0]=='Cargando resultado'
