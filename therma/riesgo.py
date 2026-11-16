"""Enumeración discreta ponderada. None significa desconocido, nunca éxito.

Los pesos son hipótesis del catálogo, no frecuencias inferidas ni Monte Carlo.
"""
from decimal import Decimal


def resumen_riesgo(rows):
    if not rows:
        raise ValueError('Catálogo vacío.')
    weights = [Decimal(str(r['weight'])) for r in rows]
    if any(not w.is_finite() or w < 0 for w in weights) or sum(weights) != Decimal(1):
        raise ValueError('Pesos finitos no negativos con suma exactamente 1.')
    ids = [r['scenario_id'] for r in rows]
    if len(set(ids)) != len(ids):
        raise ValueError('Escenarios duplicados.')
    events = []
    for r in rows:
        t = r.get('I_T') if r.get('status') == 'COMPLETED' else None
        d = r.get('I_Delta') if r.get('status') == 'COMPLETED' else None
        if t not in (None, False, True) or d not in (None, False, True):
            raise ValueError('Indicadores booleanos o desconocidos.')
        joint = True if t is True or d is True else False if t is False and d is False else None
        events.append((t, d, joint))
    result = {}
    for j, name in enumerate(('P_T', 'P_Delta', 'P_f')):
        lower = sum((w for w, e in zip(weights, events) if e[j] is True), Decimal(0))
        upper = lower + sum((w for w, e in zip(weights, events) if e[j] is None), Decimal(0))
        result[name] = float(lower) if lower == upper else None
        result[name + '_lower'] = float(lower)
        result[name + '_upper'] = float(upper)
    # Incluso con un rechazo demostrado por T, no certificar S25 ausente.
    fully = all(e[0] is not None and e[1] is not None for w, e in zip(weights, events) if w > 0)
    pf = sum((w for w, e in zip(weights, events) if e[2] is True), Decimal(0))
    result['compliance'] = ('CUMPLE' if pf <= Decimal('.05') else 'NO CUMPLE') if fully else 'INDETERMINADO'
    result['fully_evaluated'] = fully
    result['rejected_by_known_failures'] = Decimal(str(result['P_f_lower'])) > Decimal('.05')
    return result
