"""Figuras y evidencia offline a partir de lotes realmente terminados."""
import argparse
import csv
import json
import shutil
import subprocess
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from therma.lotes import write_csv, write_json, sha


def read(path):return json.loads(Path(path).read_text(encoding='utf-8'))


def history(folder):
    with (folder/'history_s25.csv').open(encoding='utf-8-sig') as f:
        return {k:np.array([float(r[k]) for r in rows]) for rows in [list(csv.DictReader(f))] for k in rows[0]}


def exportar(output,publish=None):
    output=Path(output)
    records=read(output/'tabla_corridas.json');plans=read(output/'resumen_planes.json');cat=read(output/'catalogo.json')
    good=[r for r in records if r['status']=='COMPLETED']
    fig,ax=plt.subplots(figsize=(10,5),layout='constrained')
    for i,p in enumerate(plans):
        D=p['D_h'];lo=p['P_f_lower']*100;hi=p['P_f_upper']*100
        if p['P_f'] is None:
            ax.vlines(D,lo,hi,color='#8096ac',lw=3,alpha=.55)
            ax.plot([D,D],[lo,hi],marker='_',color='#8096ac')
            ax.annotate(p['Plan'],(D,hi),xytext=(0,-20-20*(i%3)),textcoords='offset points',ha='center',fontsize=8)
        else:ax.scatter(D,100*p['P_f'],label=p['Plan'])
    ax.axhline(5,color='#c63d31',ls='--',label='Límite 5 %')
    ax.set(xlabel='Duración física de colocación D [h]',ylabel='Probabilidad conjunta de excedencia [%]',ylim=(-3,115),
           title='Riesgo conjunto no evaluado: rango de desconocimiento por S25 NO VALIDADO')
    ax.text(.5,.04,'Todos los planes: INDETERMINADO. Las barras NO son intervalos de confianza.',
            transform=ax.transAxes,ha='center',fontsize=8,bbox=dict(facecolor='white',edgecolor='none',alpha=.9))
    ax.grid(alpha=.2);ax.legend();fig.savefig(output/'D_vs_Pf.png',dpi=160);plt.close(fig)
    fig,axes=plt.subplots(2,1,figsize=(10,8),layout='constrained')
    selected=[r for r in good if r['plan_id']=='propuesto']
    for r in selected:
        h=history(Path(r['snapshot_folder']));t=h['time_s']/3600
        axes[0].plot(t,h['Tmax_C'],label=r['source_id'])
        axes[1].plot(t,h['Delta_estimate_C'],label=r['source_id'],ls='--')
    axes[0].axhline(70,color='red',ls=':',label='70 °C');axes[0].set_ylabel('Tmax [°C]')
    axes[1].axhline(20,color='red',ls=':',label='Referencia 20 °C');axes[1].set_ylabel('Delta S25 ESTIMADO [°C]')
    for ax in axes:ax.grid(alpha=.2);ax.legend();ax.set_xlabel('Tiempo desde t0 [h]')
    fig.suptitle('Plan propuesto · escenarios FV/SS · S25 NO VALIDADO')
    fig.savefig(output/'curvas_propuesto.png',dpi=160);plt.close(fig)
    # Mostrar comparación estimada en figura separada, sin confundirla con P_f oficial.
    fig,ax=plt.subplots(figsize=(9,5),layout='constrained')
    for r in good:
        D=next(p['D_h'] for p in plans if p['plan_id']==r['plan_id'])
        ax.scatter(D,r['Delta_estimate_C'],marker='x',color='#d06a2d')
    ax.axhline(20,color='red',ls='--');ax.set(xlabel='D [h]',ylabel='Delta S25 estimado [°C]',title='Exploración, no clasificación validada');ax.grid(alpha=.2)
    fig.savefig(output/'D_vs_delta_estimado.png',dpi=160);plt.close(fig)
    if good:
        representative=max(good,key=lambda r:r['Delta_estimate_C'])
        folder=Path(representative['snapshot_folder'])
        meta=read(folder/'metadata.json')
        with np.load(folder/'campos.npz') as data:
            temps=data['T_C'];active=data['active'];times=data['tiempo_s']
            j=int(np.argmax([np.max(T[A]) if A.any() else -np.inf for T,A in zip(temps,active)]))
            T=np.where(active[j],temps[j],np.nan)
        extent=meta['geometry']['origin_m'];lengths=meta['geometry']['lengths_m']
        fig,axes=plt.subplots(1,3,figsize=(13,4),layout='constrained')
        for a,ax in enumerate(axes):
            mid=T.shape[a]//2;field=np.take(T,mid,axis=a).T;other=[v for v in range(3) if v!=a]
            bounds=[extent[other[0]],extent[other[0]]+lengths[other[0]],extent[other[1]],extent[other[1]]+lengths[other[1]]]
            im=ax.imshow(field,origin='lower',extent=bounds,vmin=0,vmax=70,cmap='turbo',aspect='auto')
            ax.set(xlabel='xyz'[other[0]]+' [m]',ylabel='xyz'[other[1]]+' [m]',title='Corte '+'xyz'[a]+f' · t={times[j]/3600:.2f} h')
        fig.colorbar(im,ax=axes,label='Temperatura [°C]');fig.suptitle(representative['plan_id']+' / '+representative['source_id'])
        fig.savefig(output/'cortes_representativos.png',dpi=160);plt.close(fig)
        target=output/'representativo';target.mkdir(exist_ok=True)
        for name in ('config.json','metadata.json','campos.npz','history_s25.csv','s25_diagnostic.json','s25_peak.npz'):
            shutil.copy2(folder/name,target/name)
        from therma.exportacion_vtk import exportar as vtk
        vtk(target)
        write_json(target/'origen.json',representative)
    rows=[]
    for method in read(output/'auditoria_fuentes.json'):
        rows += [dict(method=method['method'],sha256=method['sha256'],**r) for r in method['curves']]
    write_csv(output/'comparacion_fuentes.csv',rows)
    params=[dict(parameter=k,value=v,source='Hipótesis de ensayo, salvo rho/cp del encabezado FV') for k,v in cat['base_config'].items() if k in ('k','rho','cp','days','dt')]
    params += [dict(parameter='R_moldaje',value='.02/.15 m2 K/W',source='Tablero hipotético del caso E12'),
               dict(parameter='tasa_colocacion',value=cat['plans'][0]['rate_m3_h'],source='Hipótesis, no capacidad acreditada de planta'),
               dict(parameter='volumen_IFC_m3',value=cat['geometry']['volume_m3'],source='IFC provisional'),
               dict(parameter='clima',value='forecast_12nov',source='Open-Meteo archivado, no observación')]
    write_csv(output/'parametros_y_fuentes.csv',params)
    # Sensibilidad a pesos: rangos sobre cualquier distribución de los estados admitidos.
    weight_rows=[]
    for p in plans:
        runs=[r for r in good if r['plan_id']==p['plan_id']]
        if len(runs)==len(cat['scenarios']):
            weight_rows.append(dict(plan=p['Plan'],P_T_any_weights_min=min(int(r['Tmax_C']>70) for r in runs),
                P_T_any_weights_max=max(int(r['Tmax_C']>70) for r in runs),
                P_delta_est_any_weights_min=min(int(r['I_Delta_estimate']) for r in runs),
                P_delta_est_any_weights_max=max(int(r['I_Delta_estimate']) for r in runs),
                official_joint='NOT FULLY EVALUATED'))
    write_csv(output/'sensibilidad_pesos.csv',weight_rows)
    rates=[]
    for rate in (10.,20.,40.):
        for p in cat['plans']:
            v=[o['volume_m3'] for o in p['operations']]
            starts=[0.,v[0]/rate,(v[0]+v[1])/rate] if p['continuous_operation'] else [o['start_h'] for o in p['operations']]
            feasible=all(starts[i+1]>=starts[i]+v[i]/rate-1e-9 for i in (0,1))
            rates.append(dict(plan=p['name'],rate_m3_h=rate,capacity_feasible=feasible,D_h=starts[-1]+v[-1]/rate if feasible else None,
                              warning='Sólo cronograma; NO se recalculó térmica a tasa distinta.'))
    write_csv(output/'sensibilidad_tasa_cronograma.csv',rates)
    tail=[]
    capacity=cat['base_config']['rho']*cat['base_config']['cp']
    for s in cat['sources']:
        curve=s['curve'];remaining=max(0.,cat['base_config']['days']*24-curve['time_h'][-1])
        bound=curve['Q_W_m3'][-1]*remaining*3600/capacity
        tail.append(dict(source=s['id'],constant_tail_vs_zero_bound_T_C=bound,
                         conservative_bound_delta_C=2*bound,
                         scope='Cota fuente positiva y esquema estable, sólo cola cero versus constante. No cubre otras colas ni error S25.'))
    write_csv(output/'sensibilidad_cola.csv',tail)
    from therma.lotes import ROOT,fingerprint
    command=['git','-c','safe.directory='+ROOT.as_posix()]
    git=subprocess.run(command+['rev-parse','HEAD'],capture_output=True,text=True,cwd=ROOT)
    patch=subprocess.run(command+['diff','--binary'],capture_output=True,cwd=ROOT)
    (output/'cambios_tracked.patch').write_bytes(patch.stdout)
    files=sorted((ROOT/'therma').glob('*.py'))+[ROOT/'termico_cartesiano.py',ROOT/'voxelizar.py',ROOT/'panel/exportar_ifc.py']
    write_json(output/'codigo_ejecutado.json',dict(base_git_sha=git.stdout.strip(),physical_fingerprint=fingerprint(),
        files={str(f.relative_to(ROOT)):sha(f) for f in files},
        note='Incluye módulos nuevos no confirmados. SHA base no sustituye estos hashes; guardar código F02 en commit antes de entregar.'))
    success=len(good);valid_s25=sum(r.get('S25_validation')=='VALIDATED' for r in good)
    report=['# Resumen automático F02','',f'Corridas del catálogo: {len(records)}; terminadas: {success}; S25 validado: {valid_s25}.',
            f'Planes: {len(plans)}. Climas: {len(cat["climates"])}. Fuentes: {len(cat["sources"])}.',
            '',(output/'tabla_planes.md').read_text(encoding='utf-8'),'',
            'No hay un plan más rápido factible DEMOSTRADO. S25 y el modelo de escenarios requieren validación.',
            'La operación continua se aproxima por tres activaciones al inicio de los bloques, no por llenado continuo.',
            'No hay intervalos de confianza Monte Carlo: es enumeración discreta con pesos hipotéticos.',
            'Se conserva geometría provisional 487,07 m³. No se resolvió la discrepancia de volumen.',
            'Las curvas PINN y FV NO se combinaron. Campaña 22A excluida del catálogo principal.',
            'Ventana ensayada: 13–27 noviembre. NO cubre construcción del 19 noviembre al 3 diciembre; requiere clima adicional fundamentado.',
            'No se representa cinética dependiente de temperatura ni radiación; viento no modifica h.',
            'Un horizonte marcado extension_required no permite declarar cumplimiento.']
    if (output/'sensibilidad/comparacion.json').exists():report+=['','Sensibilidad:','```json',json.dumps(read(output/'sensibilidad/comparacion.json'),ensure_ascii=False,indent=2),'```']
    (output/'RESUMEN_AUTOMATICO.md').write_text('\n'.join(report),encoding='utf-8')
    if publish:
        publish=Path(publish);publish.mkdir(parents=True,exist_ok=True)
        names=['tabla_planes.csv','tabla_planes.md','tabla_corridas.csv','tabla_corridas.json','resumen_planes.json','catalogo_congelado.json',
               'cronogramas.csv','comparacion_fuentes.csv','parametros_y_fuentes.csv','sensibilidad_pesos.csv','sensibilidad_tasa_cronograma.csv','sensibilidad_cola.csv','codigo_ejecutado.json','reproducibilidad.json',
               'D_vs_Pf.png','D_vs_delta_estimado.png','curvas_propuesto.png','cortes_representativos.png','RESUMEN_AUTOMATICO.md','seleccion.json','auditoria_fuentes.json']
        for name in names:
            if (output/name).exists():shutil.copy2(output/name,publish/name)
        for name in ('sensibilidad','verificacion_s25','sensibilidad_metodos'):
            if (output/name).exists():
                dest=publish/name;dest.mkdir(exist_ok=True)
                for file in (output/name).glob('*'):
                    if file.is_file():shutil.copy2(file,dest/file.name)
        write_json(publish/'manifiesto.json',dict(files={f.name:sha(f) for f in publish.iterdir() if f.is_file() and f.name!='manifiesto.json'},
            note='SHA base de Git y hash del código físico en cada cache_key; cambios locales F02 requieren commit posterior. Campos completos en resultados/defensa/representativo.'))
    print('Exportación completa:',output)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--salida',type=Path,default=Path('resultados/defensa'));p.add_argument('--publicar',type=Path)
    args=p.parse_args();exportar(args.salida,args.publicar)
