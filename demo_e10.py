"""E10 reproducible: aire horario + suelo efectivo + resistencia y retiro global."""
import argparse
import json
from pathlib import Path
from datetime import datetime,timezone
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from therma.meteorologia import cargar_snapshot,configuracion_snapshot,ForzanteAire
from therma.ejecutar import ejecutar

ROOT=Path(__file__).resolve().parent


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('snapshot',type=Path);p.add_argument('--inicio',required=True,help='Ejemplo 2026-11-11T08:00:00-03:00')
    p.add_argument('--dias',type=float,default=3.);p.add_argument('--retiro-h',type=float,default=48.)
    p.add_argument('--salida',type=Path,default=ROOT/'resultados'/'e10')
    args=p.parse_args()
    try:
        weather=configuracion_snapshot(args.snapshot,args.inicio)
        ForzanteAire(weather,args.dias*86400)
        config=dict(geometry='foundation',meshIndex=0,source='none',calibrate=False,days=args.dias,frames=65,
            weather=weather,faces=[dict(type='R',temp=20.,h=10.,R=0.,flux=0.) for _ in range(6)],
            construction=dict(model='exponential_adiabatic',parameter_source='E10: parámetros didácticos, no mezcla calibrada.',
                pours=[dict(id=i+1,start_h=24.*i,placement_C=18.,theta_inf_C=40.,tau_h=24.) for i in range(3)]),
            environment=dict(soil=dict(model='effective_basal_reservoir',temperature_C=8.,depth_m=1.,
                conductivity_W_mK=1.5,contact_R_m2K_W=.05,parameter_source='E10: suelo hipotético, sin campaña geotécnica.')),
            formwork=dict(model='fixed_resistance',thickness_m=.02,conductivity_W_mK=.15,
                faces=[True,True,True,True,False,False],parameter_source='E10: tablero hipotético de 20 mm, k=0.15 W/mK.'))
        run=args.salida/(datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'))
        results=[]
        for name,removal in [('protegido',None),('retiro',args.retiro_h)]:
            q=json.loads(json.dumps(config))
            if removal is not None:q['formwork']['remove_at_h']=removal
            meta=ejecutar(q,'e10_'+name,run/name);results.append((name,meta))
        fig,axes=plt.subplots(3,1,figsize=(10,10),layout='constrained')
        for name,m in results:
            h=m['history'];t=np.array([v['t'] for v in h])/3600
            axes[0].plot(t,[v['max'] for v in h],label=name)
            with np.load(run/name/'campos.npz') as fields:
                ids=fields['pour_ids'];n=ids.shape;g=m['geometry'];origin=np.array(g['origin_m']);dx=np.array(g['spacing_m'])
                xyz=np.stack(np.meshgrid(*[origin[a]+(np.arange(n[a])+.5)*dx[a] for a in range(3)],indexing='ij'),axis=-1)
                dist=np.sum((xyz-np.array([8.,0.,.55]))**2,axis=-1);dist[ids!=1]=np.inf
                index=np.unravel_index(np.argmin(dist),n)
                values=np.where(fields['active'][(slice(None),)+index],fields['T_C'][(slice(None),)+index],np.nan)
                axes[2].plot(fields['tiempo_s']/3600,values,label=name+' lateral V1 '+str(tuple(np.round(xyz[index],3))))
        h=results[0][1]['history'];t=np.array([v['t'] for v in h])/3600
        axes[1].step(t,[v['air_temperature_C'] for v in h],where='post',label='Forecast: temperatura del aire')
        axes[1].axhline(8,ls='--',label='Suelo hipotético, constante 8 °C')
        for ax in axes:ax.grid(alpha=.25);ax.legend();ax.set_xlabel('Tiempo desde primera vertida [h]')
        axes[0].set_ylabel('T máxima activa [°C]');axes[1].set_ylabel('Aire/suelo [°C]');axes[2].set_ylabel('T lateral [°C]')
        fig.suptitle('E10: forecast real; h, suelo, material e hidratación de ensayo')
        fig.savefig(run/'comparacion.png',dpi=150);plt.close(fig)
        summary=dict(snapshot_sha256=weather['provenance']['raw_sha256'],start_utc=args.inicio,
            cases={name:dict(Tmax_C=m['metrics']['maxField'],residual_relative=m['metrics']['energy_residual_relative'],final_boundary_J=m['history'][-1]['boundary_J'],final_energy_J=m['history'][-1]['energy']) for name,m in results},
            limits=['No usa viento para h ni radiación.','No valida propiedades ni fisuración.','No es una predicción del 27 de noviembre.'])
        (run/'resumen.json').write_text(json.dumps(summary,indent=2,ensure_ascii=False),encoding='utf-8')
        (run/'weather_para_panel.json').write_text(json.dumps(weather,ensure_ascii=False,indent=2),encoding='utf-8')
        print(json.dumps(summary,indent=2,ensure_ascii=False));print('Resultados:',run)
    except (ValueError,OSError,KeyError) as error:p.error(str(error))


if __name__=='__main__':main()
