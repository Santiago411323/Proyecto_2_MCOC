"""Un caso determinista de 14 días, M1_SS, forecast archivado y diagnóstico."""
import argparse
import hashlib
import json
from pathlib import Path
import csv
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from therma.ejecutar import ejecutar
from therma.meteorologia import configuracion_snapshot,ForzanteAire
from therma.exportacion_vtk import exportar,malla_vtk
from therma.diagnostico_e12 import Diagnostico
from ver_resultados_3d import visualizar

ROOT=Path(__file__).resolve().parent


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--salida',type=Path,default=ROOT/'resultados/e12')
    args=parser.parse_args();folder=args.salida
    if folder.exists() and (folder/'resumen.json').exists():parser.error('La salida ya contiene una corrida; elegir otra carpeta.')
    raw=ROOT/'data/hydration/source_terms.txt';data=np.loadtxt(raw)
    curve=dict(time_h=data[:,0].tolist(),Q_W_m3=data[:,1].tolist(),column='M1_SS_W_m3',
        raw_sha256=hashlib.sha256(raw.read_bytes()).hexdigest(),tail='constant_last',
        time_origin='Edad 0 de vertida alineada al inicio de ventana retenida (registro +2 h); no se inventan las dos horas ausentes.')
    config=json.loads((ROOT/'docs/e11/evidencia/config.json').read_text(encoding='utf-8'))
    config.update(days=14.,meshIndex=1,frames=100)
    config.update(rho=2476.,cp=1023.)  # Propiedades del encabezado vigente FV/Tikhonov.
    for key in ('mask','n','L','origin'):config.pop(key,None)
    config['weather']=configuracion_snapshot(ROOT/'data/weather/20261112T124325279292Z_a139765f','2026-11-13T10:00:00-03:00')
    ForzanteAire(config['weather'],14*86400)
    config['construction']=dict(model='tabulated_source',curve=curve,
        parameter_source='Archivo entregado source_terms.txt: M1_SS, Q [W/m3], cola constante explícita.',
        pours=[dict(id=i+1,start_h=24.*i,placement_C=18.) for i in range(3)])
    diagnosis=Diagnostico()
    print('Ejecutando 14 días, M1_SS, malla 36x36x12...',flush=True)
    meta=ejecutar(config,'e12_M1_SS_14d',folder,observer=diagnosis)
    manifest=exportar(folder)
    with np.load(folder/'campos.npz') as fields:ids=fields['pour_ids']
    T,active,ids=diagnosis.field
    mesh=malla_vtk(T,active,ids,meta['geometry']['origin_m'],meta['geometry']['spacing_m'])
    mesh.field_data['tiempo_s']=np.array([diagnosis.peak['time_s']]);mesh.save(folder/'delta_critico.vtu')
    # El máximo de Delta se guarda incluso si cae entre snapshots regulares.
    critical_folder=folder/'critico_delta';critical_folder.mkdir(exist_ok=True)
    mesh.save(critical_folder/'campo.vtu')
    critical_manifest=dict(manifest,peak_frame=0,frames=[dict(file='campo.vtu',time_s=diagnosis.peak['time_s'],active_cells=mesh.n_cells)])
    (critical_folder/'manifest.json').write_text(json.dumps(critical_manifest,ensure_ascii=False,indent=2),encoding='utf-8')
    rows=diagnosis.rows
    with (folder/'historia.csv').open('w',encoding='utf-8',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=rows[0].keys());writer.writeheader();writer.writerows(rows)
    fig,axs=plt.subplots(3,1,figsize=(11,10),layout='constrained')
    hours=np.array([r['time_s']/3600 for r in rows])
    for key,label in [('Tmax_C','Máximo global'),('core_fixed_C','Núcleo fijo'),('surface_fixed_C','Superficie +X reconstruida, punto fijo'),('air_C','Aire forecast')]:
        axs[0].plot(hours,[np.nan if r[key] is None else r[key] for r in rows],label=label)
    axs[0].axhline(70,color='red',ls='--',label='70 °C');axs[0].set_ylabel('Temperatura [°C]')
    axs[1].plot(hours,[r['delta_envelope_C'] for r in rows],label='Máximo |Tnúcleo−Tsuperficie| por vertida')
    axs[1].axhline(20,color='red',ls='--',label='20 °C');axs[1].set_ylabel('Diferencial [°C]')
    axs[2].plot(data[:,0],data[:,1],label='M1_SS, archivo del profesor')
    axs[2].plot([data[-1,0],336],[data[-1,1]]*2,ls='--',label='Cola constante declarada')
    axs[2].set_ylabel('Q [W/m³]');axs[2].set_xlabel('Edad de vertida [h]')
    for ax in axs:ax.grid(alpha=.2);ax.legend()
    for ax in axs[:2]:ax.set_xlabel('Tiempo desde primera vertida [h]')
    fig.savefig(folder/'curvas.png',dpi=160);plt.close(fig)
    visualizar(folder/'vtk',captura=folder/'Tmax_3d.png',clip=True)
    visualizar(critical_folder,captura=folder/'delta_3d.png',clip=True)
    idx=meta['metrics']['hottest_xyz'];geometry=meta['geometry']
    summary=dict(status='COMPLETED_WITH_DECLARED_ASSUMPTIONS',start='2026-11-13T10:00:00-03:00',duration_days=14,
        metrics=meta['metrics'],Tmax_xyz_m=(np.array(geometry['origin_m'])+(np.array(idx)+.5)*geometry['spacing_m']).tolist(),
        differential=diagnosis.peak,points=diagnosis.points,weather=meta['weather']['provenance'],
        hydration={k:v for k,v in curve.items() if k not in ('time_h','Q_W_m3')},
        thermal_pass=bool(meta['metrics']['maxField']<=70),differential_pass=bool(diagnosis.peak['delta_C']<=20),
        surface_method='Perfil lineal en media celda usando el flujo Robin del solver; estimación, no S25 resuelto.',
        source_commit=meta['commit'])
    (folder/'resumen.json').write_text(json.dumps(summary,indent=2,ensure_ascii=False),encoding='utf-8')
    (folder/'weather_para_panel.json').write_text(json.dumps(config['weather'],indent=2,ensure_ascii=False),encoding='utf-8')
    print(json.dumps({k:v for k,v in summary.items() if k not in ('weather','points')},indent=2,ensure_ascii=False))


if __name__=='__main__':main()
