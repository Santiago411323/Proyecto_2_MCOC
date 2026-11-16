"""Comparación controlada: mismo candidato F02 con/sin circuito de agua."""
import copy,json,uuid
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from therma.ejecutar import ejecutar
from therma.lotes import write_json,write_csv

OUT=Path('docs/tuberias_f02')

def main():
    config=json.loads(Path('docs/mejoras_f02/config_candidato.json').read_text(encoding='utf-8'))
    cooling=dict(model='parallel_x_pipes',inlet_C=10.,flow_kg_s=.1,water_cp_J_kgK=4180.,
        conductance_W_mK=8.,spacing_m=2.,levels_m=[.55,1.65,2.75],start_h=24.,stop_h=336.,
        parameter_source='Experimento F02: conductancia efectiva 8 W/(m K), no calibrada; agua acondicionada a 10 C; circuitos independientes.')
    records=[];histories=[]
    for label in ['sin_tuberias','con_tuberias']:
        p=copy.deepcopy(config)
        if label=='con_tuberias':p['cooling']=cooling
        else:p.pop('cooling',None)
        ident=uuid.uuid4().hex;folder=Path('resultados/servidor_therma')/ident
        print(label,ident,flush=True)
        meta=ejecutar(p,ident,folder,progress=lambda value:print(f'{label}: {value:.0%}',flush=True))
        h=meta['s25_ifc']['history'];histories.append((label,h));m=meta['metrics']
        record=dict(caso=label,simulation_id=ident,Tmax_C=m['maxField'],Delta_S25_estimado_C=meta['s25_ifc']['peak_estimate']['DeltaT_estimate_C'],
            t_Tmax_h=m['global_peak_time_s']/3600,t_Delta_h=meta['s25_ifc']['peak_estimate']['time_s']/3600,
            energia_extraida_MJ=meta.get('cooling',{}).get('extracted_energy_J',0)/1e6,
            error_balance_relativo=m['energy_residual_relative'],S25_completo=meta['s25_ifc']['complete_sampling'],
            folder=str(folder.resolve()),url=f'http://127.0.0.1:8767/?result={ident}')
        records.append(record);write_json(OUT/'resultados.json',records);write_csv(OUT/'comparacion.csv',records)
        saved=copy.deepcopy(p);saved.pop('mask',None);write_json(OUT/(label+'_config.json'),saved)
        write_csv(OUT/(label+'_historia.csv'),meta['history'])
        if label=='con_tuberias':write_json(OUT/'circuitos.json',meta['cooling'])
        print(record,flush=True)
    fig,axes=plt.subplots(2,1,figsize=(11,7),layout='constrained')
    for label,h in histories:
        for ax,key in zip(axes,['Tmax_C','DeltaT_estimate_C']):ax.plot([v['time_s']/86400 for v in h],[v[key] for v in h],label=label.replace('_',' '))
    for ax,limit,title in zip(axes,[70,20],['T máxima [°C]','ΔT S25 ESTIMADO [°C]']):
        ax.axhline(limit,color='red',ls='--');ax.axvline(14,color='grey',ls=':');ax.set(xlabel='Días desde t0',ylabel=title);ax.legend();ax.grid(alpha=.2)
    fig.savefig(OUT/'comparacion.png',dpi=150);plt.close(fig)
    (OUT/'README.md').write_text('# Enfriamiento por tuberías\n\nComparación del mismo candidato F02 con y sin tuberías: fuentes, clima, aislación exterior y basal, vertidas y malla se conservan. Agua 10 °C, 0,1 kg/s **por circuito**, Ul=8 W/(m K), separación lateral 2 m, cotas 0,55/1,65/2,75 m. Encendido a las 24 h y apagado a las 336 h; simulación continúa hasta 42 días. Parámetros hipotéticos, no diseño hidráulico validado.\n\n'+
        '\n'.join(f"- [{r['caso']}]({r['url']}): Tmax={r['Tmax_C']:.3f} °C; ΔT estimado={r['Delta_S25_estimado_C']:.3f} °C; calor neto extraído={r['energia_extraida_MJ']:.2f} MJ." for r in records)+
        '\n\n![Comparación](comparacion.png)\n\nEl modelo calcula la temperatura del agua a lo largo de cada circuito, supone entrada acondicionada constante y transfiere idéntica energía con signos contrarios. Conductancia efectiva desde temperatura media del voxel: no resuelve gradientes radiales junto al tubo, pared, bomba ni chiller. Las líneas cian del visor representan el trazado esquemático voxelizado, no diámetro real. El cumplimiento S25 sigue siendo estimado, no certificado.\n\nReproducir: `.venv/Scripts/python.exe simular_tuberias_f02.py`. Los JSON de configuración se pueden cargar en el panel.\n',encoding='utf-8')

if __name__=='__main__':main()
