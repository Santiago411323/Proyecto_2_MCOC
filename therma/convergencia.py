"""Estudio automático con preflight y omisiones explícitas por recursos."""
import copy
import time
from concurrent.futures import CancelledError
from pathlib import Path
import numpy as np
from .ejecutar import ejecutar,validar,ifc_actual,datos_fundacion,ROOT
from .resolucion import estimar
from .lotes import write_json,write_csv


def ejecutar_estudio(config,resolutions,folder,progress=lambda v:None,cancel=lambda *args:None):
    if not isinstance(resolutions,list) or not 1<=len(resolutions)<=8 or any(isinstance(v,bool) or not isinstance(v,(int,float)) or not np.isfinite(v) or not .01<=v<=2 for v in resolutions):
        raise ValueError('Selecciona de 1 a 8 resoluciones entre 0,01 y 2 m.')
    if not config.get('construction'):raise ValueError('Estudio IFC requiere construcción por vertidas.')
    folder=Path(folder);folder.mkdir(parents=True,exist_ok=True)
    ifc=datos_fundacion(config)
    L=np.subtract(ifc['max'],ifc['min']).tolist();volume=sum(c['volumen_m3'] for c in ifc['capas'])
    rows=[]
    for i,h in enumerate(resolutions):
        cancel()
        estimate=estimar(L,[h]*3,volume,k=config['k'],rho=config['rho'],cp=config['cp'],frames=config['frames'],days=config['days'],dt=config['dt'] if config['dtMode']=='manual' else 900.)
        row=dict(requested_m=h,shape=estimate['shape'],spacing_m=estimate['spacing_m'],total_cells=estimate['total_cells'],
                 active_cells_estimate=estimate['occupied_cells_estimate'],memory_estimate_bytes=estimate['memory_bytes_estimate'],
                 status='SKIPPED_RESOURCE' if not estimate['allowed'] else 'PENDING',reason='; '.join(estimate['reasons']))
        if estimate['allowed']:
            p=copy.deepcopy(config);p.update(meshIndex=2,n=estimate['shape'])
            p['s25']=p.get('s25') or dict(method='ifc_mls',depth_m=.025,surface_spacing_m=1.5)
            case=folder/f'case_{i:02d}'
            start=time.perf_counter()
            try:
                meta=ejecutar(p,f'mesh_{i}',case,progress=lambda v:progress((i+v)/len(resolutions)),observer=cancel)
                metric=meta['metrics'];s25=meta['s25_ifc']
                row.update(status='COMPLETED' if s25['complete_sampling'] else 'COMPLETED_S25_PARTIAL',
                           S25_complete_sampling=s25['complete_sampling'],unsupported_S25_max=max(r['unsupported_points'] for r in s25['history']),
                           Tmax_C=metric['maxField'],DeltaTmax_estimated_C=s25['peak_estimate']['DeltaT_estimate_C'],
                           DeltaTmax_validated_C=None,S25_validation=s25['validation'],voxel_volume_m3=metric['geometric_volume_m3'],
                           volume_error_percent=100*abs(metric['geometric_volume_m3']-volume)/volume,
                           active_cells=metric['N'],runtime_solver_s=metric['runtime_s'],wall_time_s=time.perf_counter()-start,
                           dt_limit_s=metric['dtMax'],energy_residual_relative=metric['energy_residual_relative'],case_folder=str(case.resolve()))
            except CancelledError:raise
            except Exception as e:row.update(status='FAILED',reason=str(e),wall_time_s=time.perf_counter()-start)
        rows.append(row);write_json(folder/'mesh_study.json',dict(rows=rows,status='RUNNING',S25_validation='NOT VALIDATED'))
        progress((i+1)/len(resolutions))
    successful=[r for r in rows if r['status'].startswith('COMPLETED')]
    previous=None
    for row in successful:
        row['Tmax_difference_previous_C']=None if previous is None else row['Tmax_C']-previous['Tmax_C']
        row['Delta_est_difference_previous_C']=None if previous is None else row['DeltaTmax_estimated_C']-previous['DeltaTmax_estimated_C']
        previous=row
    report=dict(rows=rows,status='COMPLETED',S25_validation='NOT VALIDATED',ifc_volume_m3=volume,
                note='Cambios de malla no son cotas de error; mismo modelo físico, sin AMR ni certificación de riesgo.')
    write_json(folder/'mesh_study.json',report);write_csv(folder/'mesh_study.csv',rows)
    graficar_estudio(report,folder)
    return report


def graficar_estudio(report,folder):
    folder=Path(folder)
    successful=[r for r in report['rows'] if r['status'].startswith('COMPLETED')]
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig,axes=plt.subplots(2,2,figsize=(11,7),layout='constrained')
    for ax,key,label in zip(axes.flat,('Tmax_C','DeltaTmax_estimated_C','volume_error_percent','wall_time_s'),('Tmax [°C]','Delta IFC estimado [°C] · NO VALIDADO','Error volumen IFC [%]','Tiempo MEDIDO [s]')):
        if successful:ax.plot([r['requested_m']*1000 for r in successful],[r[key] for r in successful],'o-')
        else:ax.text(.1,.5,'Ninguna resolución ejecutada',transform=ax.transAxes)
        if key=='DeltaTmax_estimated_C':
            for r in successful:
                if r.get('unsupported_S25_max'):
                    ax.annotate(f"Parcial: {r['unsupported_S25_max']} puntos desconocidos",(r['requested_m']*1000,r[key]),
                                xytext=(8,-22 if r['requested_m']>.3 else 10),textcoords='offset points',fontsize=8)
        ax.set(xlabel='Paso objetivo [mm]',ylabel=label);ax.grid(alpha=.2)
    fig.suptitle('Convergencia de malla · IFC provisional · S25 no validado')
    fig.savefig(folder/'mesh_study.png',dpi=150);plt.close(fig)
