"""Cierre trazable de horizontes y riesgo condicionado; no certifica S25."""
import math
import numpy as np
from .comparacion_f02 import aggregate


def evaluar_horizonte(history, latest_pour_h, window_h=72., tolerance_C=.05):
    """Comprueba ambas envolventes en una ventana final, no sólo dos muestras.

    Es un control de truncamiento del modelo y forzamiento declarados, no una
    garantía de que otro clima futuro no origine un máximo nuevo.
    """
    if len(history)<3:
        return dict(captured=False,reason='Historia insuficiente')
    t=np.array([r['time_s']/3600 for r in history],float)
    if not np.all(np.isfinite(t)) or np.any(np.diff(t)<=0):
        raise ValueError('Tiempos finitos estrictamente crecientes.')
    checks={};window=t>=t[-1]-window_h
    for key in ('Tmax_C','DeltaT_estimate_C'):
        v=np.array([r[key] for r in history],float)
        if not np.all(np.isfinite(v)):
            checks[key]=dict(captured=False,reason='Valores ausentes');continue
        peak=int(np.argmax(v));half=(t>=t[-1]-window_h/2)
        # Se exige que el máximo esté separado del final y que la mitad final
        # no supere la mitad anterior en más de la tolerancia declarada.
        first=window & ~half
        rise=float(np.max(v[half])-np.max(v[first])) if np.any(first) else math.inf
        margin=float(np.max(v)-np.max(v[window]))
        checks[key]=dict(captured=bool(t[peak]<t[-1]-window_h and rise<=tolerance_C),
                         peak_h=float(t[peak]),tail_rise_C=rise,peak_tail_margin_C=margin)
    ok=t[-1]-latest_pour_h>=window_h and all(c['captured'] for c in checks.values())
    return dict(captured=bool(ok),end_h=float(t[-1]),window_h=window_h,
                tolerance_C=tolerance_C,checks=checks,
                scope='Control de truncamiento; S25 estimado y cola climática hipotética.')


def indicadores(records, scenarios):
    result=aggregate(records,scenarios)
    # Sensibilidad a cualquier redistribución de pesos sobre los mismos estados.
    # No confundir este intervalo con un IC Monte Carlo ni con incertidumbre de clima.
    known=[r for r in records if r.get('status')=='COMPLETED' and r.get('numerical_checks') and r.get('horizon_captured')]
    complete=len(known)==len(scenarios) and {r['scenario_id'] for r in known}=={s['id'] for s in scenarios}
    flags=[int(r['Tmax_C']>70) for r in known]
    result['P_T_all_weights_bounds']=[min(flags),max(flags)] if complete else [0.,1.]
    result['weight_sensitivity_scope']='Todos los pesos no negativos sobre las mismas cuatro fuentes; no agrega historias climáticas.'
    return result
