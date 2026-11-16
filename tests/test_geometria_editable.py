import copy,hashlib
from pathlib import Path
import numpy as np
import pytest
from therma.geometria_editable import validar_parametros,modelo,datos,ROOT
from therma.ejecutar import ejecutar,validar
from voxelizar import cargar_geometria


def parameters():return dict(length_m=20.,width_m=16.,heights_m=[.8,1.2,.6],top_diameter_m=6.,straight_ratio=3.728/9)

def test_geometry_validation_rejects_nonphysical_and_unknown_fields():
    for change in [dict(heights_m=[1,2]),dict(top_diameter_m=40),dict(length_m=-1),dict(straight_ratio=2),dict(file='outside.ifc')]:
        with pytest.raises(ValueError):validar_parametros(dict(parameters(),**change))


def test_derivative_ifc_preserves_base_guids_bounds_and_volume_scaling():
    baseline=ROOT/'modelo_e02.ifc';digest=hashlib.sha256(baseline.read_bytes()).hexdigest();p=parameters()
    path,key=modelo(p);a=datos(p,shape=(8,8,6));base=cargar_geometria(baseline)
    assert hash_bytes(baseline)==digest
    assert [v['guid'] for v in a['capas']]==[s['guid'] for s in sorted(base,key=lambda s:s['VertidaID'])]
    np.testing.assert_allclose(np.subtract(a['max'],a['min']),[20,16,2.6])
    assert [round(v['max'][2]-v['min'][2],8) for v in a['capas']]==[.8,1.2,.6]
    taller=copy.deepcopy(p);taller['heights_m']=[v*2 for v in p['heights_m']]
    b=datos(taller,shape=(8,8,6))
    assert sum(v['volumen_m3'] for v in b['capas'])==pytest.approx(2*sum(v['volumen_m3'] for v in a['capas']))
    assert modelo(p)[0]==path and modelo(p)[1]==key


def hash_bytes(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def test_custom_geometry_reaches_solver_and_s25(tmp_path):
    from test_construccion import config
    p=config();p.update(foundation_parameters=parameters(),meshIndex=2,n=[16,16,8],days=2.2)
    p['s25']=dict(method='ifc_mls',depth_m=.025,surface_spacing_m=1.5)
    meta=ejecutar(p,'edited',tmp_path/'edited')
    assert meta['config']['L']==pytest.approx([20,16,2.6])
    geom=meta['provenance']['ifc']['geometry'];assert geom['sha256']!=hash_bytes(ROOT/'modelo_e02.ifc')
    assert geom['parameters']['heights_m']==[.8,1.2,.6]
    assert meta['s25_ifc']['ifc_sha256']==geom['sha256']
    assert meta['s25_ifc']['validation']=='NOT VALIDATED'
    with np.load(tmp_path/'edited/campos.npz') as z:
        assert tuple(z['T_C'].shape[1:])==(16,16,8)
        assert set(np.unique(z['pour_ids']))=={0,1,2,3}
    assert meta['metrics']['energy_residual_relative']<1e-10


def test_geometry_http_roundtrip_and_invalid_input(tmp_path):
    import json, threading
    from urllib.request import Request, urlopen
    from urllib.error import HTTPError
    from servidor_therma import Servidor
    server=Servidor(('127.0.0.1',0),tmp_path)
    thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    root=f'http://127.0.0.1:{server.server_port}'
    def send(p):
        return urlopen(Request(root+'/api/foundation-geometry',data=json.dumps(p).encode(),headers={'Content-Type':'application/json'}),timeout=30)
    try:
        with send(parameters()) as response:d=json.loads(response.read())
        assert np.subtract(d['max'],d['min']).tolist()==pytest.approx([20,16,2.6])
        with urlopen(root+d['model_url'],timeout=15) as response:raw=response.read()
        assert hashlib.sha256(raw).hexdigest()==d['sha256']
        with pytest.raises(HTTPError) as error:send(dict(parameters(),heights_m=[1,-1,1]))
        assert error.value.code==422
        with urlopen(root+'/api/health') as response:assert response.status==200
    finally:
        server.shutdown();server.server_close();thread.join()
