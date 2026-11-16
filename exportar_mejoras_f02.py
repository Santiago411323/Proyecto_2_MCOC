"""Tablas, figuras y diagnóstico del estudio; no convierte estimaciones en validación."""
import json
import shutil
import subprocess
import sys
import textwrap
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from therma.lotes import write_json, write_csv, sha, fingerprint
from simular_mejoras_f02 import OUT, SNAP
from therma.meteorologia import instante

DEST=Path('docs/mejoras_f02')

def read(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def table(rows,keys):
    def fmt(v):return f'{v:.3f}' if isinstance(v,float) else str(v)
    return '| '+' | '.join(keys)+' |\n|'+'|'.join(['---']*len(keys))+'|\n'+'\n'.join('| '+' | '.join(fmt(r.get(k,'')) for k in keys)+' |' for r in rows)

def main():
    DEST.mkdir(parents=True,exist_ok=True);cat=read(OUT/'catalogo.json')
    rows=[];all_records=[]
    for phase in ['piloto','confirmacion','fuentes_finas']:
        p=OUT/phase/'progreso.json'
        if not p.exists():continue
        records=read(p);all_records+=records
        for r in records:
            folder=Path(r['snapshot_folder']);meta=read(folder/'metadata.json');hist=meta['s25_ifc']['history']
            short=[h for h in hist if h['time_s']<=14*86400]
            peak14=max(short,key=lambda h:h['DeltaT_estimate_C'])
            peak=meta['s25_ifc']['critical_pair'];metric=meta['metrics']
            row=dict(fase=phase,plan=r['plan_id'],fuente=r['source_id'],D_h=r['D_h'],
                Tmax14_C=max(h['Tmax_C'] for h in short),Delta14_estimado_C=peak14['DeltaT_estimate_C'],
                Tmax42_C=r['Tmax_C'],Delta42_estimado_C=r['Delta_estimate_C'],
                t_Tmax_h=r['Tmax_time_h'],t_Delta_h=r['Delta_time_h'],
                xyz_Tmax_m=(np.asarray(meta['geometry']['origin_m'])+(np.array(metric['hottest_xyz'])+.5)*np.array(meta['geometry']['spacing_m'])).tolist(),
                xyz_caliente_Delta_m=peak['hot']['xyz_m'],xyz_frio_Delta_m=peak['cold']['xyz_m'],
                region_fria=r['peak_S25']['region'],horizonte_capturado=r['horizon_captured'],
                cobertura_aire_pct=100*r['coverage_air_min_fraction'],balance_relativo=r['energy_residual_relative'],
                estado='ESTIMADO; cumplimiento no certificado',cache_key=r['cache_key'])
            rows.append(row)
    write_csv(DEST/'corridas.csv',rows)
    shutil.copy2(OUT/'catalogo.json',DEST/'catalogo.json');shutil.copy2(OUT/'clima_escenario.json',DEST/'clima_escenario.json')
    shutil.copy2(SNAP/'metadata.json',DEST/'metadata_forecast.json')
    write_csv(DEST/'cronogramas.csv',[dict(plan=p['id'],D_h=p['D_h'],rate_m3_h=p['rate_m3_h'],placement_C=p['placement_C'],**o) for p in cat['plans'] for o in p['operations']])
    write_csv(DEST/'condiciones_borde.csv',[
        dict(region='Aire',modelo='Robin',ecuacion='q_saliente=(Tsuperficie-Taire)/(1/h+Rmoldaje+Raislacion)',parametros='h=10 W/m2K; Rmoldaje=0.02/0.15 lateral; Raislacion=e/0.038; serie horaria'),
        dict(region='Suelo',modelo='Reservorio efectivo',ecuacion='q_saliente=(Tsuperficie-8)/(0.05+1/1.5+Rbasal_adicional)',parametros='Rbasal adicional sólo en planes identificados; 0, 0.5 o 1 m2K/W'),
        dict(region='Interfaces colocadas',modelo='Contacto perfecto',ecuacion='Continuidad de flujo y temperatura',parametros='Mismo material; sin resistencia de contacto interna'),
        dict(region='Interior',modelo='Fuente volumétrica',ecuacion='rho cp dT/dt=div(k grad T)+Q(edad)',parametros='Curva completa FV; reinicio de edad por vertida; cola Q constante al último valor')])
    for name in ['comparacion_planes.png','curvas_M4_SS.png']:
        shutil.copy2(OUT/'piloto'/name,DEST/name)
    pilot=read(OUT/'piloto'/'resumen.json')['plans'];y=np.arange(len(pilot))
    fig,axes=plt.subplots(1,2,figsize=(13,9),sharey=True,layout='constrained')
    for ax,key,limit,title in zip(axes,['Tmax_worst_C','Delta_S25_est_worst_C'],[70,20],['T máxima [°C]','ΔT S25 estimado [°C]']):
        values=[r[key] for r in pilot];ax.barh(y,values,color='#318c99');ax.axvline(limit,color='red',ls='--')
        for i,v in enumerate(values):ax.text(v+.4,i,f'{v:.2f}',va='center',fontsize=8)
        ax.set(title=title,xlim=(0,max(limit,max(values))*1.12));ax.grid(axis='x',alpha=.2)
    axes[0].set_yticks(y,['\n'.join(textwrap.wrap(r['Plan'],40))+f" · D={r['D_h']:.1f} h" for r in pilot],fontsize=8);axes[0].invert_yaxis()
    fig.suptitle('Piloto M4_SS · 42 días · malla 50 cm\nComparación de estimaciones; no certificación de cumplimiento')
    fig.savefig(DEST/'comparacion_planes.png',dpi=150);plt.close(fig)
    weather=cat['climates'][0]['weather'];t=(np.array([instante(s) for s in weather['time_utc']])-instante(weather['start_utc']))/86400
    end=(instante(weather['provenance']['observed_forecast_end_utc'])-instante(weather['start_utc']))/86400
    fig,ax=plt.subplots(figsize=(11,3),layout='constrained');ax.plot(t,weather['temperature_C'],lw=.8);ax.axvspan(end,42,alpha=.15,color='orange',label='Cola hipotética: ciclo 48 h');ax.axvline(14,color='grey',ls='--');ax.set(xlim=(0,42),xlabel='Días desde 19/11 10:00 -03',ylabel='Aire [°C]');ax.legend();fig.savefig(DEST/'clima.png',dpi=150);plt.close(fig)
    mesh_path=OUT/'malla'/'comparacion.json';mesh=read(mesh_path) if mesh_path.exists() else []
    mesh_table=[]
    if mesh:
        for r in mesh:
            mesh_table.append(dict(caso=r['case'],voxeles_activos=r['active_cells'],celdas_caja=r['total_cells'],
                Tmax_C=r['Tmax_C'],Delta_estimado_C=r['Delta_estimate_C'],error_volumen_pct=r['volume_error_percent'],
                S25_sin_soporte=r['missing_points_max'],dt_s=r['dt_s'],tiempo_s=r['wall_time_s']))
        write_csv(DEST/'mallas.csv',mesh_table)
        spatial=[r for r in mesh if r['case'].startswith('h')]
        fig,axes=plt.subplots(1,3,figsize=(12,3.5),layout='constrained')
        for ax,key,title in zip(axes,['Tmax_C','Delta_estimate_C','volume_error_percent'],['Tmax [°C]','ΔT S25 estimado [°C]','Error de volumen [%]']):
            ax.plot([r['spacing_m'][0]*1000 for r in spatial],[r[key] for r in spatial],'o-',label='Refinamiento casi isotrópico')
            vertical=next((r for r in mesh if r['case']=='z110'),None)
            if vertical:ax.plot(vertical['spacing_m'][0]*1000,vertical[key],'*',ms=12,color='green',label='48×48×30; dz=110 mm')
            ax.set(xlabel='Paso horizontal [mm]',ylabel=title);ax.grid(alpha=.2)
        axes[0].legend(fontsize=7)
        fig.savefig(DEST/'convergencia.png',dpi=150);plt.close(fig)
        chosen=next((r for r in mesh if r['case']=='z110'),next((r for r in mesh if r['case']=='h250'),mesh[-1]))
    else:chosen=min(all_records,key=lambda r:r['Delta_estimate_C'])
    folder=Path(chosen['snapshot_folder']);meta=read(folder/'metadata.json');hist=meta['s25_ifc']['history']
    cfg=read(folder/'config.json');cfg.pop('mask',None);write_json(DEST/'config_candidato.json',cfg)
    write_json(DEST/'resultado_candidato.json',chosen)
    write_json(DEST/'par_critico.json',meta['s25_ifc']['critical_pair'])
    write_csv(DEST/'historia_candidato.csv',hist)
    fig,axes=plt.subplots(2,1,figsize=(11,7),layout='constrained')
    x=np.array([h['time_s'] for h in hist])/86400
    axes[0].plot(x,[h['Tmax_C'] for h in hist],label='Máximo activo (posición variable)')
    axes[0].plot(x,[h['Tmin_S25_estimate_C'] for h in hist],label='Mínimo S25 estimado (posición variable)')
    h=meta['history'];axes[0].plot(np.array([v['t'] for v in h])/86400,[v['center'] for v in h],label='Punto fijo central de la malla',ls=':')
    axes[0].axhline(70,color='red',ls='--');axes[0].set(ylabel='Temperatura [°C]');axes[0].legend(fontsize=8)
    axes[1].plot(x,[h['DeltaT_estimate_C'] for h in hist]);axes[1].axhline(20,color='red',ls='--');axes[1].set(xlabel='Días desde t0',ylabel='ΔT simultáneo S25 estimado [°C]')
    for ax in axes:ax.axvline(14,color='grey',ls='--');ax.grid(alpha=.2)
    fig.suptitle(f"{chosen['plan_id']} · {chosen['source_id']} · S25 NO VALIDADO");fig.savefig(DEST/'curvas_candidato.png',dpi=150);plt.close(fig)
    a=np.load(folder/'s25_ifc_critical.npz');T=a['T_C'];active=a['active'];dx=a['spacing_m'];origin=a['origin_m'];j=T.shape[1]//2
    from therma.exportacion_vtk import malla_vtk
    vtk=malla_vtk(T,active,a['pour_ids'],origin,dx)
    vtk.field_data['tiempo_s']=np.array([float(a['time_s'])]);vtk.save(DEST/'instante_Delta_max.vtu')
    with np.load(folder/'campos.npz') as data:
        frame=int(np.argmin(abs(data['tiempo_s']-meta['metrics']['global_peak_time_s'])))
        assert abs(data['tiempo_s'][frame]-meta['metrics']['global_peak_time_s'])<1e-6
        vtk=malla_vtk(data['T_C'][frame],data['active'][frame],data['pour_ids'],origin,dx)
        vtk.field_data['tiempo_s']=np.array([float(data['tiempo_s'][frame])]);vtk.save(DEST/'instante_Tmax.vtu')
        from therma.exportacion_vtk import puntos_fijos
        points_info=puntos_fijos(data['active'][-1],origin,dx);point_rows=[]
        fig,ax=plt.subplots(figsize=(10,3.5),layout='constrained')
        for label,point in points_info.items():
            idx=tuple(point['index_xyz']);values=[float(f[idx]) if mask[idx] else None for f,mask in zip(data['T_C'],data['active'])]
            ax.plot(data['tiempo_s']/86400,values,'o-',ms=2,label=f"{label}: centro de voxel {np.round(point['xyz_m'],3)} m")
            point_rows.extend(dict(punto=label,tiempo_h=float(t/3600),T_C=v,xyz_m=point['xyz_m']) for t,v in zip(data['tiempo_s'],values))
        ax.set(xlabel='Días desde t0',ylabel='Temperatura [°C]',title='Puntos fijos: el exterior NO representa exactamente S25');ax.legend(fontsize=8);ax.grid(alpha=.2)
        fig.savefig(DEST/'puntos_fijos.png',dpi=150);plt.close(fig);write_csv(DEST/'puntos_fijos.csv',point_rows)
    fig,axes=plt.subplots(1,2,figsize=(12,4),layout='constrained');field=np.ma.masked_where(~active[:,j,:],T[:,j,:])
    limits=dict(vmin=float(T[active].min()),vmax=float(T[active].max()))
    im=axes[0].imshow(field.T,origin='lower',extent=[origin[0],origin[0]+T.shape[0]*dx[0],origin[2],origin[2]+T.shape[2]*dx[2]],aspect='auto',cmap='inferno',**limits);fig.colorbar(im,ax=axes[0],label='°C');axes[0].set(xlabel='x [m]',ylabel='z [m]',title='Corte central en instante de ΔT máximo')
    axes[1].remove();ax=fig.add_subplot(122,projection='3d');coords=np.argwhere(active);points=origin+(coords+.5)*dx
    sc=ax.scatter(*points.T,c=T[active],s=2,cmap='inferno',rasterized=True,**limits);ax.set(xlabel='x [m]',ylabel='y [m]',zlabel='z [m]',title='Voxeles activos');ax.set_box_aspect([18,18,5]);fig.colorbar(sc,ax=ax,shrink=.65,label='°C');fig.savefig(DEST/'corte_y_voxeles.png',dpi=160);plt.close(fig)
    report=['# Simulaciones de mejora y estudio de malla — F02','',
        'Resultados de experimentos numéricos; **no constituyen todavía cumplimiento certificado**. Inicio común: 19/11/2026 10:00, UTC−03. Geometría y fuentes FV originales conservadas; no se ajusta la fuente para cumplir límites.',
        '', '## Diseño y trazabilidad',
        f"Snapshot Open-Meteo descargado {weather['provenance']['snapshot']['retrieved_at_utc']}; cobertura real hasta {weather['provenance']['observed_forecast_end_utc']}. Después se repite el último ciclo completo de 48 horas, explícitamente como hipótesis. Se comparan 14 y 42 días. No es un pronóstico real de 42 días.",
        'Fuentes: cuatro curvas SS completas, mismo material supuesto y misma curva en todas las vertidas. La identidad de mezcla no está demostrada; no se mezclan las 22A ni se seleccionan valores horarios. El piloto usa M4; la confirmación evalúa las cuatro SS. Pesos hipotéticos no equivalen a probabilidades de obra.',
        'k=2 W/(m K), ρ=2476 kg/m³, cp=1023 J/(kg K); aire Robin h=10 W/(m² K), sin viento ni radiación. Suelo reservorio 8 °C, profundidad efectiva 1 m, k=1,5, Rcontacto=0,05. Moldaje lateral 20 mm, k=0,15. Aislación exterior k=0,038, espesor por plan; permanece todo el horizonte. Su retiro requiere otro estudio.',
        'Tasa común 20 m³/h, un equipo, sin solapamiento. Sin esperas: D=24,3535 h. La activación térmica ocurre al inicio de cada una de las tres piezas; no reproduce llenado continuo. Los casos con resistencia basal adicional son hipótesis constructivas que requieren aprobación estructural/geotécnica; no se cambió arbitrariamente la temperatura ni conductividad del suelo.',
        '', '## Resultados', table(rows,['fase','plan','fuente','Tmax14_C','Delta14_estimado_C','Tmax42_C','Delta42_estimado_C','horizonte_capturado']),
        '', 'Los CSV incluyen tiempos, coordenadas y región fría. Los máximos de Tmax y ΔT ocurren en instantes distintos; el ΔT siempre resta temperaturas simultáneas.',
        '', '![Planes](comparacion_planes.png)','![Clima](clima.png)','![Curvas](curvas_candidato.png)','![Puntos fijos](puntos_fijos.png)','![Corte y voxelización](corte_y_voxeles.png)',
        'Archivos 3D inspeccionables: `instante_Tmax.vtu` e `instante_Delta_max.vtu`. En ParaView: Open, Apply, colorear por T_C y usar Slice o Clip. Sólo contienen hormigón activo; temperatura asociada a celdas.',
        '', '## Malla y paso temporal',table(mesh_table,['caso','voxeles_activos','celdas_caja','Tmax_C','Delta_estimado_C','error_volumen_pct','S25_sin_soporte','dt_s']),
        '', '![Convergencia](convergencia.png)' if mesh else 'Estudio de malla pendiente.',
        'Comparar h500/h375/h250 con dt=900 s y horizonte de 42 días. z110 conserva paso horizontal 375 mm y reduce el vertical a 110 mm. Comparar dt900_21d/dt450_21d con la MISMA malla y horizonte de 21 días; comparar h375/dt450_h375 para 42 días. Los máximos de 21 días no sustituyen los del horizonte extendido. Se informan cambios entre mallas, no una cota rigurosa de error ni convergencia asintótica demostrada.',
        'La reconstrucción S25 aproxima 25 mm bajo superficies IFC. Las zonas sin soporte, el escalonamiento de la frontera y la sensibilidad espacial impiden certificar Pf≤5 %. Residuo de energía pequeño demuestra conservación discreta, no exactitud física.',
        '', '## Reproducción',
        'Desde la raíz: `.venv/Scripts/python.exe simular_mejoras_f02.py piloto`; luego `confirmar --plan ID` y `malla --plan ID`; finalmente `.venv/Scripts/python.exe exportar_mejoras_f02.py`. Catálogo congelado, escenarios, metadata y config acompañan este informe. Resultados voluminosos en `resultados/mejoras_f02/cache/`. No se ha publicado un commit nuevo.',
        'La conclusión final debe separar candidato térmico, factibilidad constructiva y verificación numérica. Un valor estimado bajo el límite no autoriza a etiquetar el plan como CUMPLE.'
    ]
    fine=[r for r in rows if r['fase']=='fuentes_finas']
    if fine:
        report.extend(['## Candidato y decisión provisional',
            f"En la malla 48×48×30, entre {len(fine)} curvas SS evaluadas, Tmax máximo={max(r['Tmax42_C'] for r in fine):.3f} °C y ΔT estimado máximo={max(r['Delta42_estimado_C'] for r in fine):.3f} °C. Casos que exceden los límites estimados: {sum(r['Tmax42_C']>70 or r['Delta42_estimado_C']>20 for r in fine)}/{len(fine)}. Este recuento NO certifica una probabilidad de falla de obra ni reemplaza el criterio S25 validado.",
            'Usar provisionalmente 48×48×30 (Δx=Δy=0,375 m, Δz=0,11 m) para estudiar este candidato; contrastarla con 72×72×14. 31.212 voxeles activos, 69.120 celdas de caja. Resuelve más capas verticales y todos los puntos S25 muestreados en este caso. No se demuestra convergencia universal ni basta contar voxeles: el error de volumen y de frontera también importan.',
            'El candidato exige 8 °C de colocación, 100 mm de aislación exterior y R adicional basal=1 m²K/W; protección mantenida 42 días. No se ha demostrado factibilidad de refrigeración, capacidad portante de una capa basal, ni seguridad después del retiro. Q se conserva por edad sin corrección térmica; el cambio de cinética con la temperatura no se modela. Es una alternativa para validar, no una especificación constructiva aprobada.' ])
    climate_path=OUT/'clima'/'sensibilidad.json'
    if climate_path.exists():
        climates=read(climate_path);write_csv(DEST/'sensibilidad_clima.csv',climates)
        report.extend(['## Sensibilidad meteorológica',table(climates,['climate_shift_C','Tmax_C','Delta_estimate_C','horizon_captured']),
            'Desplazamientos de ±3 °C de toda la historia meteorológica, manteniendo ciclo y persistencia; no son percentiles ni tienen probabilidades asignadas. El suelo conserva 8 °C. Se evalúa M4 en la malla recomendada. No se han enumerado todas las combinaciones fuente×clima.'])
    (DEST/'INFORME.md').write_text('\n\n'.join(report),encoding='utf-8')
    write_json(DEST/'procedencia_codigo.json',dict(
        base_commit=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
        working_tree_dirty=bool(subprocess.check_output(['git','status','--porcelain'],text=True).strip()),
        python=sys.version,engine_fingerprint=fingerprint(),
        files={p:sha(p) for p in ['simular_mejoras_f02.py','exportar_mejoras_f02.py','requirements-lock.txt','requirements-viz-lock.txt','data/hydration/source_terms.txt','modelo_e02.ifc']},
        note='Resultados calculados con cambios locales. El SHA base no incorpora estos scripts hasta un commit posterior.'))
    write_json(DEST/'SHA256.json',{str(p.relative_to(DEST)):sha(p) for p in DEST.iterdir() if p.is_file() and p.name!='SHA256.json'})
    print(DEST/'INFORME.md')

if __name__=='__main__':main()
