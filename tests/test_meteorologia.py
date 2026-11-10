import json
from datetime import datetime,timezone
import numpy as np
import pytest
from therma.meteorologia import guardar_snapshot,cargar_snapshot,configuracion_snapshot,ForzanteAire,instante
from therma.ejecutar import ejecutar
from test_construccion import config
from test_nucleo_moldaje import formwork


def raw():
    t=int(instante('2026-11-10T00:00:00Z'))
    return json.dumps(dict(latitude=-52.8,longitude=-70.9,hourly_units=dict(time='unixtime',temperature_2m='°C',wind_speed_10m='m/s'),
        hourly=dict(time=[t+i*3600 for i in range(100)],temperature_2m=[5.+i%8 for i in range(100)],wind_speed_10m=[4.]*100))).encode()


def snapshot(tmp_path):
    return guardar_snapshot(raw(),tmp_path,dict(latitude=-52.82,longitude=-70.89,models='best_match'),'https://example.test/fixture')


def test_snapshot_preserves_bytes_unique_folder_and_detects_tampering(tmp_path):
    a=snapshot(tmp_path);b=snapshot(tmp_path)
    assert a!=b and (a/'forecast.json').read_bytes()==raw()
    assert cargar_snapshot(a)[2]['model_run_issued_at'] is None
    (a/'forecast.json').write_bytes(raw()+b' ')
    with pytest.raises(ValueError,match='alterado'):cargar_snapshot(a)


@pytest.mark.parametrize('alter',[lambda d:d['hourly']['time'].__setitem__(2,d['hourly']['time'][1]),
    lambda d:d['hourly']['temperature_2m'].__setitem__(3,None),
    lambda d:d['hourly_units'].__setitem__('temperature_2m','°F'),
    lambda d:d['hourly']['wind_speed_10m'].__setitem__(0,-1)])
def test_invalid_response_rejected(tmp_path,alter):
    d=json.loads(raw());alter(d)
    with pytest.raises(ValueError):guardar_snapshot(json.dumps(d).encode(),tmp_path,{},'fixture')


def test_utc_coverage_no_extrapolation_and_hourly_events(tmp_path):
    w=configuracion_snapshot(snapshot(tmp_path),'2026-11-10T00:00:00-03:00')
    f=ForzanteAire(w,86400)
    assert f.temperatura(0)==8. and f.siguiente(0)==3600 and f.temperatura(3600)==9.
    with pytest.raises(ValueError,match='cubre'):ForzanteAire(w,14*86400)
    with pytest.raises(ValueError):instante('2026-11-10T00:00:00')
    with pytest.raises(ValueError):f.temperatura(1e10)


def test_weather_reaches_physics_preserves_soil_and_energy(tmp_path):
    p=config((0,12,24));p['days']=2.
    p['weather']=configuracion_snapshot(snapshot(tmp_path/'snapshots'),'2026-11-10T00:00:00Z')
    p['environment']=dict(soil=dict(model='effective_basal_reservoir',temperature_C=8.,depth_m=1.,
        conductivity_W_mK=1.5,contact_R_m2K_W=.05,parameter_source='Suelo de ensayo declarado.'))
    a=ejecutar(p,'test_clima',tmp_path/'variable')
    q=json.loads(json.dumps(p));q.pop('weather')
    b=ejecutar(q,'test_constante',tmp_path/'constante')
    assert a['metrics']['maxField']!=pytest.approx(b['metrics']['maxField'],abs=.01)
    assert a['metrics']['energy_residual_relative']<1e-12
    assert a['environment']['soil']['temperature_C']==8.
    assert a['validity']['weather']=='FORECAST_BOUNDARY_SERIES'
    assert a['history'][0]['air_temperature_C']==5.
    times=[h['t'] for h in a['history']]
    assert all(t in times for t in range(0,2*86400+1,3600))


def test_removal_occurs_exactly_and_changes_solution(tmp_path):
    p=config((0,12,24));p['days']=2.;p['formwork']=formwork()
    protected=ejecutar(p,'protegido',tmp_path/'a')
    p['formwork']['remove_at_h']=18.25
    removed=ejecutar(p,'retirado',tmp_path/'b')
    t=18.25*3600
    assert t in removed['fields']['times_s'] and t-1 in removed['fields']['times_s']
    states=removed['history']
    assert all(h['formwork_present']==(h['t']<t) for h in states)
    assert removed['metrics']['energy_residual_relative']<1e-12
    assert removed['history'][-1]['energy']<protected['history'][-1]['energy']
    with np.load(tmp_path/'b'/'campos.npz') as fields:
        assert np.isfinite(fields['T_C']).all()
