import numpy as np
import pytest
from therma.ejecutar import validar,preparar
from panel.exportar_ifc import datos_ifc
from test_construccion import config
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]


def test_custom_grid_is_revoxelized_from_ifc_not_client_mask():
    p=config();p.update(meshIndex=2,n=[20,20,10],mask=[999])
    v=validar(p);d=datos_ifc(ROOT/'modelo_e02.ifc',formas=[(20,20,10)])
    assert v['n']==[20,20,10] and v['mask']==d['mallas'][0]['ids']
    assert set(v['mask'])=={0,1,2,3}
    np.testing.assert_allclose(d['mallas'][0]['dx'],np.asarray(v['L'])/v['n'])


@pytest.mark.parametrize('n',[[1,20,10],[20.5,20,10],[True,20,10],[160,160,160]])
def test_custom_grid_limits_are_validated_before_voxelization(n):
    p=config();p.update(meshIndex=2,n=n)
    with pytest.raises(ValueError):validar(p)


def test_custom_grid_does_not_change_ifc_volume_or_bounds():
    a=datos_ifc(ROOT/'modelo_e02.ifc',formas=[(12,12,6)])
    b=datos_ifc(ROOT/'modelo_e02.ifc',formas=[(20,20,10)])
    assert a['sha256']==b['sha256'] and a['min']==b['min'] and a['max']==b['max']
    assert sum(c['volumen_m3'] for c in a['capas'])==sum(c['volumen_m3'] for c in b['capas'])
    for d in (a,b):
        m=d['mallas'][0]
        assert m['volumen_m3']==pytest.approx(sum(i>0 for i in m['ids'])*np.prod(m['dx']))
