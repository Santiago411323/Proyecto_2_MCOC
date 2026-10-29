"""Compara el motor JavaScript del HTML contra el solver Python del proyecto."""
import json
from pathlib import Path
import shutil
import subprocess
import numpy as np
import pytest
from termico_cartesiano import TermicoCartesiano
from calibrar_qmax import evolucion

BASE = Path(__file__).resolve().parents[1]
NODE = shutil.which('node')
pytestmark = pytest.mark.skipif(NODE is None, reason='Node no disponible para verificar el motor web')


def javascript(p):
    programa = "const s=require('./panel/solver.js');let x='';process.stdin.on('data',d=>x+=d);process.stdin.on('end',()=>{let r=s.solve(JSON.parse(x));console.log(JSON.stringify({dt:r.dt,dtMax:r.dtMax,qmax:r.qmax,maxCenter:r.maxCenter,final:r.history.at(-1),field:Array.from(r.fields.at(-1)),exact:r.exactError}));});"
    return json.loads(subprocess.run([NODE, '-e', programa], input=json.dumps(p), text=True,
                      cwd=BASE, capture_output=True, check=True).stdout)


def config(dim, tipo):
    return dict(dim=dim, L=[3., 3., .6], n=[10, 8, 4], k=2., rho=2400., cp=900.,
                initial=20., initialType='uniform', amplitude=30., source='pulse',
                period=2*86400., qmax=1900., calibrate=False, target=70., days=3.,
                dtMode='auto', dt=300., factor=.7, frames=20,
                faces=[dict(type=tipo, temp=30., flux=3., h=10., R=.15) for _ in range(6)])


@pytest.mark.parametrize('dim', [1, 2, 3])
@pytest.mark.parametrize('tipo', ['D', 'N', 'R', 'mixto'])
def test_panel_coincide_con_python(dim, tipo):
    p = config(dim, tipo if tipo != 'mixto' else 'D')
    if tipo == 'mixto':
        p['faces'][0]['type'] = 'N'
        p['faces'][1]['type'] = 'R'
    js = javascript(p)
    bordes = {}
    for a in range(dim):
        for s in range(2):
            b = p['faces'][2*a+s]
            bordes[f"{'xyz'[a]}{'+' if s else '-'}"] = {
                'type': None, 'tipo': {'D': 'dirichlet', 'N': 'neumann', 'R': 'robin'}[b['type']],
                'temperatura_C': b['temp'], 'flujo_saliente_W_m2': b['flux'],
                'h_W_m2K': b['h'], 'R_m2K_W': b['R']}
    m = TermicoCartesiano(p['n'][:dim], p['L'][:dim], k=p['k'], rho=p['rho'], cp=p['cp'], bordes=bordes)
    r = evolucion(m, p['period'], p['days']*86400, js['dt'], qmax=p['qmax'], inicial=p['initial'])
    assert js['dtMax'] == pytest.approx(m.dt_max, rel=1e-12)
    assert js['final']['center'] == pytest.approx(r['centro_C'][-1], abs=1e-9)
    campo_js = np.array(js['field']).reshape(tuple(reversed(p['n'][:dim]))).transpose(tuple(reversed(range(dim))))
    np.testing.assert_allclose(campo_js, r['T_final'], atol=2e-5, rtol=0)


def test_panel_calibracion_adiabatica_exacta():
    p = config(3, 'N')
    for b in p['faces']: b['flux'] = 0.
    p['calibrate'] = True
    js = javascript(p)
    assert js['qmax'] == pytest.approx(1250, rel=1e-10)
    assert js['maxCenter'] == pytest.approx(70, abs=1e-9)
    assert js['final']['center'] == pytest.approx(70, abs=1e-9)


def test_panel_sinusoidal_error_exacto():
    p = config(2, 'D')
    p.update(L=[1., 1., 1.], n=[16, 16, 8], initialType='sine', amplitude=10., source='none', days=.03/86400, k=1., rho=1., cp=1.)
    for b in p['faces']: b['temp'] = 20.
    js = javascript(p)
    assert 0 < js['exact'] < .01
