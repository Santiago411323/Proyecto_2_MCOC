"""E11: forecast real -> Robin -> simulación 3D corta -> VTK + gráficos."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

from therma.ejecutar import ejecutar
from therma.exportacion_vtk import exportar
from therma.meteorologia import cargar_snapshot, configuracion_snapshot, ForzanteAire, instante

ROOT = Path(__file__).resolve().parent


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('snapshot', type=Path)
    parser.add_argument('--inicio', required=True, help='ISO 8601 con zona horaria')
    parser.add_argument('--dias', type=float, default=3.)
    parser.add_argument('--salida', type=Path, default=ROOT / 'resultados' / 'e11')
    parser.add_argument('--abrir', action='store_true', help='Abrir visor interactivo al terminar')
    args = parser.parse_args()
    weather = configuracion_snapshot(args.snapshot, args.inicio)
    ForzanteAire(weather, args.dias * 86400)
    times, temperature, provenance = cargar_snapshot(args.snapshot)
    run = args.salida / datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    config = dict(geometry='foundation', meshIndex=0, source='none', calibrate=False,
        days=args.dias, frames=65, weather=weather,
        faces=[dict(type='R', temp=20., h=10., R=0., flux=0.) for _ in range(6)],
        construction=dict(model='exponential_adiabatic',
            parameter_source='E11: hidratación didáctica, no calibrada experimentalmente.',
            pours=[dict(id=i+1, start_h=24.*i, placement_C=18., theta_inf_C=40., tau_h=24.) for i in range(3)]),
        environment=dict(soil=dict(model='effective_basal_reservoir', temperature_C=8., depth_m=1.,
            conductivity_W_mK=1.5, contact_R_m2K_W=.05, parameter_source='E11: suelo hipotético.')),
        formwork=dict(model='fixed_resistance', thickness_m=.02, conductivity_W_mK=.15,
            faces=[True, True, True, True, False, False], parameter_source='E11: tablero hipotético de 20 mm.'))
    print('Ejecutando 3D con aire horario, h constante y tres vertidas...', flush=True)
    meta = ejecutar(config, 'e11_forecast_3d', run)
    manifest = exportar(run)
    h = (times - instante(args.inicio)) / 3600
    fig, ax = plt.subplots(figsize=(11, 4), layout='constrained')
    ax.step(h, temperature, where='post', label='Open-Meteo: temperatura del aire')
    ax.axvspan(0, args.dias * 24, color='orange', alpha=.2, label='Intervalo usado por el solver')
    ax.set(xlabel='Horas desde inicio de simulación', ylabel='Temperatura del aire [°C]',
           title='Forecast real archivado (no observación): ' + provenance['retrieved_at_utc'])
    ax.grid(alpha=.25); ax.legend()
    fig.savefig(run / 'temperatura_ambiente.png', dpi=150); plt.close(fig)

    with np.load(run / 'campos.npz') as data:
        fields, active, output_times = (data[key] for key in ('T_C', 'active', 'tiempo_s'))
        fig, ax = plt.subplots(figsize=(10, 5), layout='constrained')
        ax.plot([row['t']/3600 for row in meta['history']], [row['max'] for row in meta['history']], label='Máximo de todos los voxeles activos', color='red')
        for name, point in manifest['points'].items():
            index = (slice(None),) + tuple(point['index_xyz'])
            values = np.where(active[index], fields[index], np.nan)
            ax.plot(output_times/3600, values, label=name + ' (voxel fijo)', marker='.', markersize=3)
            point['final_T_C'] = float(fields[index][-1]) if active[index][-1] else None
        history = meta['history']
        ax.step([row['t']/3600 for row in history], [row['air_temperature_C'] for row in history], where='post', ls='--', label='Aire usado en Robin')
        for event in (24, 48):
            if event <= args.dias*24:
                ax.axvline(event, color='gray', ls=':', alpha=.6)
        ax.set(xlabel='Tiempo [h]', ylabel='Temperatura [°C]', title='Hidratación didáctica + clima real; puntos sin interpolar antes de activarse')
        ax.grid(alpha=.25); ax.legend()
        fig.savefig(run / 'temperaturas.png', dpi=150); plt.close(fig)
    from ver_resultados_3d import visualizar
    visualizar(run / 'vtk', captura=run / 'corte_3d.png')
    visualizar(run / 'vtk', captura=run / 'clipping_3d.png', clip=True)
    summary = dict(snapshot=str(args.snapshot.resolve()), weather_sha256=provenance['raw_sha256'],
        start_with_timezone=args.inicio, duration_h=args.dias*24, metrics=meta['metrics'],
        points=manifest['points'], frames=len(manifest['frames']),
        peak_frame=manifest['peak_frame'], final_volume_m3=manifest['frames'][-1]['volume_m3'],
        provenance_commit=meta['commit'], working_tree_dirty=meta['working_tree_dirty'],
        limits=['Forecast: no observaciones medidas.', 'Geometría IFC provisional e hidratación no calibrada.',
                'h constante: viento archivado, sin efecto físico; sin radiación solar/onda larga.',
                'Suelo como reservorio fijo a 8 °C; no almacenamiento de suelo.',
                'Puntos en centros de voxel: no temperatura exacta de superficie ni S25.'])
    (run / 'resumen.json').write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding='utf-8')
    (args.salida / 'ultima_corrida.json').write_text(json.dumps(dict(folder=run.name)), encoding='utf-8')
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    print('Resultados:', run)
    print('Visor: .\\.venv\\Scripts\\python.exe ver_resultados_3d.py', args.salida)
    if args.abrir:
        visualizar(run / 'vtk')


if __name__ == '__main__':
    main()
