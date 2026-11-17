import numpy as np
import pytest
from therma.cierre_f02 import evaluar_horizonte,indicadores


def history(peak=100):
    return [dict(time_s=t*3600,Tmax_C=50-abs(t-peak)*.01,DeltaT_estimate_C=15-abs(t-peak)*.005) for t in range(0,1009,6)]


def test_horizon_rejects_late_peak_and_periodic_tail():
    assert evaluar_horizonte(history(),48)['captured']
    assert not evaluar_horizonte(history(990),48)['captured']
    h=history();h[-5]['DeltaT_estimate_C']=30
    assert not evaluar_horizonte(h,48)['captured']
    assert not evaluar_horizonte(history(),990)['captured']


def test_horizon_checks_both_envelopes_and_order():
    h=history();h[-1]['DeltaT_estimate_C']=30
    assert not evaluar_horizonte(h,48)['checks']['DeltaT_estimate_C']['captured']
    with pytest.raises(ValueError):evaluar_horizonte(h[::-1],48)


def test_conditional_risk_unknown_delta_and_weight_sensitivity():
    s=[dict(id=str(i),weight='.25') for i in range(4)]
    r=[dict(scenario_id=str(i),weight='.25',status='COMPLETED',numerical_checks=True,horizon_captured=True,Tmax_C=60.) for i in range(4)]
    x=indicadores(r,s)
    assert x['P_T']==0 and x['P_f'] is None and x['P_Delta'] is None
    assert x['P_T_all_weights_bounds']==[0,0]
    r[-1]['Tmax_C']=71
    assert indicadores(r,s)['P_T']==.25
    assert indicadores(r,s)['P_T_all_weights_bounds']==[0,1]
    assert indicadores(r[:-1],s)['P_T'] is None
