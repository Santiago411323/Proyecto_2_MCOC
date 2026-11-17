"""Resume evidencia espacial y temporal sin confundir sensibilidad con validación."""
import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from therma.lotes import write_json,write_csv

BASE=Path('docs/hielo_f02/convergencia')
OUT=Path('docs/hielo_f02/refinamiento_xyz')

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    coverage=json.loads((BASE/'cobertura.json').read_bytes())
    shapes=[[60,60,36],[72,72,42],[84,84,48],[90,90,48],[96,96,54],[100,100,60]]
    rows=[];decisions=[]
    for temp in (8,12):
        selected=[]
        for shape in shapes:
            p=BASE/f'T{temp}_{"x".join(map(str,shape))}_dt1200_fv_M4_SS.json'
            if not p.exists():continue
            r=json.loads(p.read_bytes());g=next(v for v in coverage if v['shape']==shape)
            previous=selected[-1] if selected else None
            row=dict(temperature_C=temp,shape=shape,total_cells=g['total_cells'],active_cells=g['active_cells'],
                dx_m=r['spacing_m'][0],dz_m=r['spacing_m'][2],Tmax_C=r['Tmax_C'],Delta_est_C=r['Delta_estimate_C'],
                change_Tmax_C=None if previous is None else abs(r['Tmax_C']-previous['Tmax_C']),
                change_Delta_C=None if previous is None else abs(r['Delta_estimate_C']-previous['Delta_est_C']),
                unknown=r['missing_points_max'],volume_error_pct=g['volume_error_pct'],
                stable=r['numerical_checks'],horizon_captured=r['horizon_captured'],
                energy_residual_relative=r['energy_residual_relative'],engine=r['engine_fingerprint'],
                dt_s=r['dt_requested_s'],runtime_s=r['runtime_s'])
            selected.append(row);rows.append(row)
        final=selected[-2:]
        passed=len(selected)==len(shapes) and all(v['change_Tmax_C']<.1 and v['change_Delta_C']<.1 and v['unknown']==0 and v['stable'] and v['horizon_captured'] for v in final)
        decisions.append(dict(temperature_C=temp,status='SENSIBILIDAD_ESPACIAL_MENOR_0_10_C' if passed else 'CONVERGENCIA_NO_DEMOSTRADA',
            final_shape=selected[-1]['shape'],recent_changes=[dict(Tmax_C=v['change_Tmax_C'],Delta_C=v['change_Delta_C']) for v in final]))
    write_csv(OUT/'tabla.csv',rows);write_json(OUT/'evaluacion.json',dict(decisions=decisions,rows=rows))
    temporal=[]
    for temp in (8,12):
        file=BASE/f'T{temp}_100x100x60_dt900_fv_M4_SS.json'
        fine=next((r for r in rows if r['temperature_C']==temp and r['shape']==[100,100,60]),None)
        if file.exists() and fine:
            r=json.loads(file.read_bytes())
            temporal.append(dict(temperature_C=temp,shape=r['shape'],dt_coarse_s=1200,dt_fine_s=900,
                change_Tmax_C=abs(r['Tmax_C']-fine['Tmax_C']),change_Delta_C=abs(r['Delta_estimate_C']-fine['Delta_est_C']),
                stable=r['numerical_checks'],horizon_captured=r['horizon_captured']))
    write_json(OUT/'control_temporal.json',temporal)
    for temp in (8,12):
        file=BASE/f'T{temp}_96x96x54_dt1200_fv_M4_SS.json'
        if file.exists():
            record=json.loads(file.read_bytes());config_path=Path(record['snapshot_folder'])/'config.json'
            if config_path.exists():
                config=json.loads(config_path.read_bytes());config.pop('mask',None)
                write_json(OUT/f'config_T{temp}_96x96x54.json',config)
    fig,axes=plt.subplots(2,2,figsize=(11,7),layout='constrained')
    for temp,color in [(8,'#217a85'),(12,'#bf7034')]:
        rr=[r for r in rows if r['temperature_C']==temp]
        for ax,key in zip(axes[0],['Tmax_C','Delta_est_C']):ax.plot([r['total_cells'] for r in rr],[r[key] for r in rr],'o-',color=color,label=f'Colocación {temp} °C')
        for ax,key in zip(axes[1],['change_Tmax_C','change_Delta_C']):ax.plot([r['total_cells'] for r in rr[1:]],[r[key] for r in rr[1:]],'o-',color=color)
    for ax,title in zip(axes.flat,['T máxima [°C]','ΔT S25 estimado [°C]','Cambio Tmax [°C]','Cambio ΔT [°C]']):ax.set(xlabel='Celdas totales de la caja',ylabel=title);ax.grid(alpha=.2);ax.ticklabel_format(axis='x',style='sci',scilimits=(0,0))
    for ax in axes[1]:ax.axhline(.1,color='red',ls='--')
    axes[0,0].legend();fig.suptitle('Refinamiento XYZ · M4_SS · 42 días · dt=1200 s');fig.savefig(OUT/'refinamiento.png',dpi=160);plt.close(fig)
    lines=['# Continuación del estudio de mallas','',
        'Se conserva geometría IFC, fuente M4_SS, clima congelado y su cola hipotética, propiedades, aislación y cronograma. Se estudian colocaciones a 8 y 12 °C. Horizonte 42 días, dt solicitado 1200 s y 40 snapshots.',
        'Los resultados previos refinaban de 84×84×48 a 90×90×48 sin cambiar altura. Se añaden 96×96×54 y 100×100×60 para refinar los tres ejes. Se reporta sensibilidad; no se ajusta la malla para obtener cumplimiento.',
        '|T colocación|Malla|Voxeles activos|Tmax °C|ΔT estimado °C|Cambio Tmax °C|Cambio ΔT °C|Puntos sin soporte|Error volumen %|','|---|---|---|---|---|---|---|---|---|']
    for r in rows:
        fmt=lambda x:'—' if x is None else f'{x:.5f}'
        lines.append(f"|{r['temperature_C']}|{'×'.join(map(str,r['shape']))}|{r['active_cells']}|{fmt(r['Tmax_C'])}|{fmt(r['Delta_est_C'])}|{fmt(r['change_Tmax_C'])}|{fmt(r['change_Delta_C'])}|{r['unknown']}|{fmt(r['volume_error_pct'])}|")
    lines+=['','![Refinamiento](refinamiento.png)','',* [f"- Colocación {d['temperature_C']} °C: **{d['status']}**." for d in decisions],
        '', 'Criterio declarado: ambos cambios <0,10 °C en los últimos dos refinamientos, estabilidad, conservación energética, horizonte capturado y muestreo S25 completo. Una diferencia pequeña entre dos mallas no es una cota de error; el escalonamiento de frontera puede producir oscilaciones. No se aplica Richardson sin evidenciar régimen asintótico.',
        'El control temporal anterior (1200/1800 s) corresponde a 90×90×48. Se añade control 1200/900 s en 100×100×60 para el plan de 8 °C; ver control_temporal.json. La cobertura es la de los puntos muestreados, no garantía de todos los puntos de la superficie.',
        'La fuente no incorpora cinética dependiente de temperatura. Los resultados mantienen hipótesis constructivas y climáticas anteriores. La evaluación oficial de S25 sigue no validada.',
        '', 'Reproducir: `.venv/Scripts/python.exe continuar_convergencia_f02.py` y `.venv/Scripts/python.exe informar_refinamiento_xyz.py`. Evidencia individual en `docs/hielo_f02/convergencia/`; campos en `resultados/hielo_f02/cache/`. Recursos: 600.000 celdas, 1,5 GiB estimado y 3.000 millones de celda-pasos; corridas secuenciales.']
    if all(d['status']=='SENSIBILIDAD_ESPACIAL_MENOR_0_10_C' for d in decisions):
        lines+=['## Selección de malla',
            'Para estos planes y este escenario M4_SS se recomienda **96×96×54**, con Δx=Δy=187,5 mm y Δz=61,11 mm, **225.936 voxeles activos** y 497.664 celdas totales. Se usa **100×100×60** como comprobación más fina: su diferencia satisface la tolerancia elegida. La recomendación es un compromiso de costo y sensibilidad; la familia anisótropa y el borde escalonado impiden afirmar una tasa asintótica o un error absoluto garantizado.',
            'El estudio no prueba la misma precisión para las otras fuentes, otras protecciones o un clima distinto. Antes de publicar un nuevo plan, contrastar al menos su caso crítico en la malla de comprobación. Para el plan de 12 °C el margen térmico cercano a 20 °C exige cautela: la sensibilidad menor a 0,10 °C no convierte S25 en una evaluación formal validada.']
    if temporal:
        lines+=['## Paso temporal',* [f"- Colocación {t['temperature_C']} °C, 100×100×60, 1200→900 s: cambio Tmax={t['change_Tmax_C']:.6f} °C; cambio ΔT={t['change_Delta_C']:.6f} °C." for t in temporal]]
    lines+=['## Usar la malla en THERMA',
        'En **02 Configurar plan → Resolución de voxeles y S25**, seleccionar **Estudio M4_SS · 96×96×54**. Esta opción sólo cambia la malla de las entradas actuales; exige ejecutar Python de nuevo. Para reproducir el caso completo, usar **Cargar ajustes** con `config_T8_96x96x54.json` o `config_T12_96x96x54.json` de esta carpeta. Las corridas publicadas de otras fuentes no se sustituyen automáticamente.']
    (OUT/'INFORME.md').write_text('\n\n'.join(lines),encoding='utf-8')
    print(json.dumps(decisions,ensure_ascii=False),flush=True)

if __name__=='__main__':main()
