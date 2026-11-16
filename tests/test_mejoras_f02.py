import copy
import numpy as np
from simular_mejoras_f02 import preparar
from therma.lotes import validar_catalogo
from therma.meteorologia import ForzanteAire, instante


def test_catalogo_conserva_fuentes_geometria_y_restricciones(tmp_path,monkeypatch):
    import simular_mejoras_f02 as study
    monkeypatch.setattr(study,'OUT',tmp_path)
    cat=preparar()
    validar_catalogo(cat)
    assert len({s['curve']['raw_sha256'] for s in cat['sources']})==1
    assert all(p['operations'][0]['start_h']==0 for p in cat['plans'])
    assert cat['base_config']['environment']['soil']['contact_R_m2K_W']==.05
    assert all(p['D_h']>24 for p in cat['plans'])


def test_cola_es_escenario_identificado_y_repite_ciclo_sin_huecos(tmp_path,monkeypatch):
    import simular_mejoras_f02 as study
    monkeypatch.setattr(study,'OUT',tmp_path)
    w=preparar()['climates'][0]['weather']
    assert w['kind']=='scenario'
    assert w['start_utc']=='2026-11-19T10:00:00-03:00'
    f=ForzanteAire(w,42*86400)
    end=instante(w['provenance']['observed_forecast_end_utc'])
    times=np.array([instante(t) for t in w['time_utc']]);i=np.flatnonzero(times==end)[0]
    assert np.all(np.diff(times)==3600)
    assert w['temperature_C'][i+1:i+49]==w['temperature_C'][i-47:i+1]
    assert np.isfinite(f.temperatura(42*86400))
