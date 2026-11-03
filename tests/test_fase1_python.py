import json
import threading
import time
import uuid
from urllib.request import Request, urlopen
from urllib.error import HTTPError
import numpy as np
import pytest
from termico_cartesiano import TermicoCartesiano
from therma.ejecutar import ejecutar,validar
from therma.resultados import a_xfast,desde_xfast,guardar
from therma.ejemplos import importar_3d
from servidor_therma import Servidor


def config(dim=1,k=2.):
    return dict(dim=dim,geometry='block',L=[1.,.7,.3],n=[10,6,4],k=k,
                initial=20.,initialType='sine',amplitude=10.,source='none',days=1.,frames=20)


def test_orden_3d_asimetrico_y_binario(tmp_path):
    xyz=np.indices((3,4,5));campo=100*xyz[0]+10*xyz[1]+xyz[2]
    datos=a_xfast(campo)
    assert datos[1]==100 and datos[3]==10 and datos[12]==1
    np.testing.assert_array_equal(desde_xfast(datos,(3,4,5)),campo)
    p={'dim':3,'L':[3.,4.,5.],'n':[3,4,5]}
    meta=guardar(tmp_path,uuid.uuid4().hex,p,np.array([campo,campo+1]),[0.,1.],[],{}, {})
    raw=np.fromfile(tmp_path/'fields.bin',dtype='<f4').reshape(2,-1)
    assert meta['geometry']['index_order'].startswith('x-fastest')
    np.testing.assert_array_equal(desde_xfast(raw[1],(3,4,5)),campo+1)


@pytest.mark.parametrize('dim',[1,2,3])
def test_resultado_api_motor_y_unidades(dim,tmp_path):
    p=config(dim)
    meta=ejecutar(p,uuid.uuid4().hex,tmp_path)
    c=meta['config'];m=TermicoCartesiano(c['n'][:dim],c['L'][:dim],k=2.,rho=2400.,cp=900.,
       bordes={f"{'xyz'[a]}{s}":{'tipo':'dirichlet','temperatura_C':20.} for a in range(dim) for s in ('-','+')})
    perfil=np.prod([np.sin(np.pi*x/L) for x,L in zip(m.coordenadas,m.longitudes)],axis=0)
    r=m.resolver(20+10*perfil,86400.,meta['metrics']['dt'])
    with np.load(tmp_path/'campos.npz') as z:np.testing.assert_allclose(z['T_C'][-1],r['T'],atol=1e-10)
    assert meta['engine']=='termico_cartesiano.py'
    assert meta['units']['source']=='W/m3' and meta['units']['time']=='s'
    assert meta['validity']['project_deltaT_25mm']=='NOT EVALUATED'


@pytest.mark.parametrize('bad',[{'k':0},{'days':-1},{'n':[2.5,2,2]},{'command':'whoami'}, {'k':float('nan')}, {'dim':True}])
def test_rechaza_parametros_peligrosos_o_invalidos(bad):
    with pytest.raises(ValueError):validar({**config(),**bad})


@pytest.fixture
def server(tmp_path):
    s=Servidor(('127.0.0.1',0),tmp_path);thread=threading.Thread(target=s.serve_forever,daemon=True);thread.start()
    yield s
    s.shutdown();s.server_close();thread.join()


def request(s,path,data=None,headers=None):
    req=Request(f'http://127.0.0.1:{s.server_port}'+path,
        data=None if data is None else json.dumps(data).encode(),headers=headers or {'Content-Type':'application/json'})
    with urlopen(req,timeout=15) as r:return r.status,r.read()


def completar(s,p):
    status,raw=request(s,'/api/simulations',p);assert status==202
    job=json.loads(raw)
    for _ in range(200):
        _,raw=request(s,job['status_url']);state=json.loads(raw)
        if state['status']!='RUNNING':return state
        time.sleep(.03)
    pytest.fail('El servidor no terminó el trabajo')


def test_servidor_cambio_parametro_resultados_nuevos(server):
    assert json.loads(request(server,'/api/health')[1])['engine']=='termico_cartesiano.py'
    a=completar(server,config(k=2.));b=completar(server,config(k=4.))
    assert a['status']==b['status']=='COMPLETED' and a['simulation_id']!=b['simulation_id']
    ma=json.loads(request(server,a['metadata_url'])[1]);mb=json.loads(request(server,b['metadata_url'])[1])
    assert ma['config_sha256']!=mb['config_sha256']
    assert ma['history'][-1]['center']>mb['history'][-1]['center']
    assert ma['simulation_id']==a['simulation_id']


def test_servidor_errores_no_rompen_servicio(server):
    with pytest.raises(HTTPError) as e:request(server,'/api/simulations',{'k':-1})
    assert e.value.code==422
    p=config();p.update(dtMode='manual',dt=1e12)
    job=completar(server,p)
    assert job['status']=='FAILED' and 'inestable' in job['message']
    with pytest.raises(HTTPError) as e:request(server,'/api/simulations',config(),{'Content-Type':'application/json','Origin':'https://otro-sitio.example'})
    assert e.value.code==403
    with pytest.raises(HTTPError):request(server,'/api/results/../../README.md')
    assert request(server,'/api/health')[0]==200


def test_importa_campos_3d_existentes_sin_modificarlos(tmp_path):
    archivo=tmp_path/'original.npz';out=tmp_path/'out'
    campos=np.arange(2*3*4*5,dtype=float).reshape(2,3,4,5)+20
    np.savez(archivo,numerica_C=campos,tiempo_s=[0,100])
    (tmp_path/'resumen.json').write_text(json.dumps({'longitudes_m':[3,4,5],'borde_C':20}),encoding='utf-8')
    meta=importar_3d(archivo,uuid.uuid4().hex,out)
    raw=np.fromfile(out/'fields.bin',dtype='<f4').reshape(2,-1)
    np.testing.assert_array_equal(desde_xfast(raw[1],(3,4,5)),campos[1])
    assert meta['engine']=='archivo Python NPZ preexistente'
    assert meta['metrics']['residual'] is None
