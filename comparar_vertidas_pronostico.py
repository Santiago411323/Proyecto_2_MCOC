"""Ensayos independientes con un pronóstico trazable y el solver oficial."""
import argparse
import json
import math
import uuid
from pathlib import Path

from therma.comparacion_f02 import op_config
from therma.ejecutar import ejecutar
from therma.hielo import CATALOG, preview
from therma.lotes import write_json
from therma.meteorologia import configuracion_snapshot, instante, utc

SHAPE = (96, 96, 54)
DAYS = 42
RATE_M3_H = 20
SOURCE = 'fv_M4_SS'


def weather_for_run(snapshot, start):
    weather = configuracion_snapshot(snapshot, start)
    last = instante(weather['time_utc'][-1])
    end = instante(start) + DAYS * 86400
    extension_hours = max(0, math.ceil((end - last) / 3600))
    if extension_hours:
        tail = weather['temperature_C'][-48:]
        weather['time_utc'].extend(utc(last + 3600 * (i + 1)) for i in range(extension_hours))
        weather['temperature_C'].extend(tail[i % 48] for i in range(extension_hours))
        weather.update(kind='scenario', provenance=dict(
            snapshot=weather['provenance'], observed_forecast_end_utc=utc(last),
            extension_start_utc=utc(last + 3600), extended_hours=extension_hours,
            extension='Repetición del último ciclo horario de 48 h como escenario hipotético.'))
    return weather


def run(snapshot, start, reference, count, wait_h):
    catalog = json.loads(CATALOG.read_bytes())
    plan = next(p for p in catalog['plans'] if p['id'] == 't8_eps100_base1')
    protection = dict(plan, basal_R_added=0)
    volume = sum(o['volume_m3'] for o in plan['operations'])
    mix = preview(dict(mode='target', value=min(reference, 8), reference_C=reference,
                       water_kg_m3=160, water_C=20, ice_C=0))
    cfg = op_config(catalog, protection, SOURCE, SHAPE, DAYS, 1200)
    cfg['weather'] = weather_for_run(snapshot, start)
    ident = uuid.uuid4().hex
    folder = Path('resultados/servidor_therma') / ident
    folder.mkdir(parents=True)
    print(f'{count} vertidas: {ident}', flush=True)
    if count == 1:
        print(f'Mezcla: {reference:g} °C; dosis de hielo: {mix["total_t"]:.2f} t', flush=True)
    else:
        print(f'Colocación: {reference:g} °C, sin hielo', flush=True)
    milestone = -1

    def progress(value):
        nonlocal milestone
        step = int(value * 10)
        if step > milestone:
            print(f'{count} vertidas: {step * 10} %', flush=True)
            milestone = step

    if count == 1:
        for layer in cfg['construction']['pours']:
            layer.update(start_h=0, placement_C=mix['placement_C'])
        schedule = [dict(id=1, start_h=0, end_h=volume / RATE_M3_H, volume_m3=volume)]
        meta = ejecutar(cfg, ident, folder, progress)
    else:
        from dividir_vertidas_ifc import ejecutar_seis
        meta, schedule = ejecutar_seis(cfg, ident, folder, reference, wait_h, RATE_M3_H, progress)
    peak = meta['s25_ifc']['peak_estimate']
    write_json(folder / 'ensayo_pronostico.json', dict(
        simulation_id=ident, plan_pours=count, placement_schedule=schedule,
        placement_rate_m3_h=RATE_M3_H, additional_wait_h=wait_h if count == 6 else 0,
        uncooled_mix_C=reference, ice_balance=mix if count == 1 else None,
        eps_mm=100, additional_basal_R_m2K_W=0, forecast_snapshot=str(snapshot),
        Tmax_C=meta['metrics']['maxField'], DeltaT_S25_estimate_C=peak['DeltaT_estimate_C'],
        S25_validation=meta['s25_ifc']['validation']))
    print(f'{count} vertidas: COMPLETED {ident} {meta["metrics"]["maxField"]:.4f} {peak["DeltaT_estimate_C"]:.4f}', flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('snapshot', type=Path)
    parser.add_argument('--start', default='2026-11-19T10:00:00-03:00')
    parser.add_argument('--reference', type=float, default=14)
    parser.add_argument('--pours', type=int, choices=(1, 6), required=True)
    parser.add_argument('--wait-h', type=float, default=0)
    args = parser.parse_args()
    run(args.snapshot, args.start, args.reference, args.pours, args.wait_h)
