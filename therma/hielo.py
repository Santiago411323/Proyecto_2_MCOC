"""Preenfriamiento previo a descarga y comparación pareada del plan continuo F02."""
import copy
import hashlib
import json
import math
import uuid
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path

from .comparacion_f02 import op_config
from .ejecutar import ejecutar

ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / 'docs/cierre_f02/evidencia/catalogo_congelado.json'
LATENT, CP_WATER, CP_ICE = 334000., 4180., 2100.  # J/kg, J/(kg K), J/(kg K)


def balance(spec, rho, cp, volume):
    keys = {'mode', 'value', 'reference_C', 'water_C', 'ice_C', 'water_kg_m3'}
    if not isinstance(spec, dict) or set(spec) != keys or spec['mode'] not in ('dose', 'target'):
        raise ValueError('Selecciona dosis de hielo o temperatura objetivo.')
    for key in keys - {'mode'}:
        if type(spec[key]) not in (int, float) or not math.isfinite(spec[key]):
            raise ValueError('Completa los campos con valores numéricos finitos.')
    ref, water, ice, available = (spec[k] for k in ('reference_C', 'water_C', 'ice_C', 'water_kg_m3'))
    if not (0 < ref < 100 and 0 <= water < 100 and -273.15 < ice <= 0 and 0 < available < rho):
        raise ValueError('Revisa las temperaturas de fase y la masa de agua reemplazable.')
    enthalpy = LATENT + CP_WATER * water - CP_ICE * ice
    dose = spec['value'] if spec['mode'] == 'dose' else (ref - spec['value']) * rho * cp / enthalpy
    if not 0 <= dose <= available:
        raise ValueError('La dosis debe estar entre cero y el agua líquida reemplazable.')
    placement = ref - dose * enthalpy / (rho * cp)
    if placement <= 0:
        raise ValueError('La mezcla debe quedar sobre 0 °C para asumir fusión completa.')
    return dict(dose_kg_m3=dose, total_t=dose*volume/1000, liquid_kg_m3=available-dose,
                placement_C=placement, reduction_C=ref-placement, volume_m3=volume,
                replaced_pct=100*dose/available, enthalpy_J_kg=enthalpy)


@lru_cache(maxsize=1)
def reference():
    raw = CATALOG.read_bytes()
    catalog = json.loads(raw)
    plan = next(p for p in catalog['plans'] if p['id'] == 'continua')
    cfg = op_config(catalog, plan, 'fv_M4_SS', shape=(36,36,7), days=42, dt=900)
    path = ROOT / 'modelo_e02.ifc'
    if hashlib.sha256(path.read_bytes()).hexdigest() != catalog['geometry']['ifc_sha256']:
        raise ValueError('El IFC actual difiere del catálogo de referencia congelado.')
    volume = sum(v['volume_m3'] for v in plan['operations'])
    return cfg, volume, plan['operations'], hashlib.sha256(raw).hexdigest()


def preview(spec):
    cfg, volume, _, _ = reference()
    return balance(spec, cfg['rho'], cfg['cp'], volume)


def run_pair(spec, folder, progress, observe):
    cfg, volume, schedule, digest = reference()
    cases = []
    for index, label in enumerate(('Sin hielo', 'Con hielo')):
        inputs = spec if index else dict(spec, mode='dose', value=0.)
        mix = balance(inputs, cfg['rho'], cfg['cp'], volume)
        config = copy.deepcopy(cfg)
        for pour in config['construction']['pours']:
            pour['placement_C'] = mix['placement_C']
        ident = uuid.uuid4().hex
        dest = folder.parent / ident
        meta = ejecutar(config, ident, dest, lambda x: progress((index+x)/2), observer=observe)
        s25 = meta['s25_ifc']
        cases.append(dict(label=label, simulation_id=ident, config_sha256=meta['config_sha256'],
                          mix=mix, inputs=inputs, Tmax_C=meta['metrics']['maxField'],
                          peak_h=meta['metrics']['global_peak_time_s']/3600,
                          delta_C=s25['peak_estimate']['DeltaT_estimate_C'],
                          delta_h=s25['peak_estimate']['time_s']/3600, coverage_complete=s25['complete_sampling'],
                          series=[[r['time_s']/3600,r['Tmax_C'],r['DeltaT_estimate_C']] for r in s25['history']]))
    report = dict(version=1, created_utc=datetime.now(timezone.utc).isoformat(),
                  catalog_sha256=digest, inputs=spec, cases=cases, operations=schedule,
                  duration_h=schedule[-1]['end_h'], model='balance adiabático previo a colocación',
                  constants=dict(Lf_J_kg=LATENT, cp_water_J_kgK=CP_WATER, cp_ice_J_kgK=CP_ICE),
                  validation_S25='ESTIMADO / NO VALIDADO')
    folder.mkdir(parents=True, exist_ok=True)
    tmp = folder/'ice_study.tmp'
    tmp.write_text(json.dumps(report, ensure_ascii=False, allow_nan=False), encoding='utf-8')
    tmp.replace(folder/'ice_study.json')
