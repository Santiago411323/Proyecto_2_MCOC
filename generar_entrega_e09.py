"""Genera evidencia E09 desde el IFC y el motor THERMA; no calibra al paper."""
from pathlib import Path
import hashlib
import json
import subprocess
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
from therma.ejecutar import ejecutar, ifc_actual
from voxelizar import cargar_geometria

ROOT = Path(__file__).resolve().parent
OUT = ROOT/'docs'/'entrega_e09'
RAW = ROOT/'resultados'/'entrega_e09'


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    RAW.mkdir(parents=True, exist_ok=True)
    config = dict(geometry='foundation', source='none', calibrate=False, days=14., frames=100,
        faces=[dict(type='R', temp=20., h=10., R=0., flux=0.) for _ in range(6)],
        construction=dict(model='exponential_adiabatic',
            parameter_source='Supuesto didáctico: theta_inf=40 C, tau=24 h; sin calibración experimental.',
            pours=[dict(id=i+1, start_h=i*24., placement_C=18., theta_inf_C=40., tau_h=24.) for i in range(3)]))
    (OUT/'configuracion.json').write_text(json.dumps(config, indent=2), encoding='utf-8')
    metas = []
    for mesh in (0, 1):
        p = dict(config, meshIndex=mesh)
        metas.append(ejecutar(p, f'e09_malla_{mesh}', RAW/f'malla_{mesh}'))
    m = metas[1]
    data = np.load(RAW/'malla_1'/'campos.npz')
    T, active, ids, ts = (data[k] for k in ('T_C', 'active', 'pour_ids', 'tiempo_s'))
    g = m['geometry']; shape = T.shape[1:]
    spacing = np.array(g['spacing_m']); origin = np.array(g['origin_m'])
    coords = np.stack(np.meshgrid(*[origin[a]+(np.arange(shape[a])+.5)*spacing[a]
                                  for a in range(3)], indexing='ij'), axis=-1)
    solids = cargar_geometria(ROOT/'modelo_e02.ifc')
    volume = sum(s['volumen'] for s in solids)
    reference = ifc_actual((ROOT/'modelo_e02.ifc').stat().st_mtime_ns, (48, 48, 18))
    volumes = []
    for meta in metas:
        v = meta['metrics']['geometric_volume_m3']
        volumes.append(dict(n=meta['geometry']['shape_xyz'], volume_m3=v, error_pct=100*abs(v-volume)/volume))
    v = reference['mallas'][0]['volumen_m3']
    volumes.append(dict(n=[48,48,18], volume_m3=v, error_pct=100*abs(v-volume)/volume))
    colors = ['#4c91b2', '#d3ac58', '#a96066']
    fig = plt.figure(figsize=(10,6), layout='constrained'); ax=fig.add_subplot(projection='3d')
    faces, tones = [], []
    solids = sorted(solids, key=lambda s: s['VertidaID'])
    for layer,(s,c) in enumerate(zip(solids,colors)):
        triangles = s['triangulos']
        keep = np.ones(len(triangles), dtype=bool)
        if layer > 0:
            keep &= ~np.all(np.isclose(triangles[:,:,2],s['vertices'][:,2].min()),axis=1)
        if layer < len(solids)-1:
            keep &= ~np.all(np.isclose(triangles[:,:,2],s['vertices'][:,2].max()),axis=1)
        faces.extend(triangles[keep]); tones.extend([c]*int(keep.sum()))
        ax.plot([],[],[],color=c,label=s['nombre'])
    ax.add_collection3d(Poly3DCollection(faces,facecolors=tones,edgecolors=tones,linewidths=0,alpha=1.,shade=True))
    ax.set(xlim=(-9,9),ylim=(-9,9),zlim=(0,3.3),xlabel='x [m]',ylabel='y [m]',zlabel='z [m]',
           title='Geometría del IFC: interpretación provisional de tres vertidas')
    ax.set_box_aspect((18,18,5)); ax.view_init(25,-55); ax.legend()
    fig.savefig(OUT/'01_bim.png',dpi=160); plt.close(fig)
    cmap=ListedColormap(colors)
    fig,axes=plt.subplots(1,3,figsize=(12,4),layout='constrained')
    for ax,t in zip(axes,[0,86400,172800]):
        j=int(np.argmin(abs(ts-t))); plane=np.ma.masked_where(~active[j,:,shape[1]//2,:],ids[:,shape[1]//2,:])
        ax.imshow(plane.T,origin='lower',extent=[-9,9,0,3.3],aspect='auto',cmap=cmap,vmin=1,vmax=3)
        ax.set(xlabel='x [m]',ylabel='z [m]',title=f'Activación: t={t/3600:.0f} h')
    fig.suptitle('Voxelización: corte XZ por centros próximos a y=0; blanco = no colocado/exterior')
    fig.savefig(OUT/'02_voxeles.png',dpi=160); plt.close(fig)
    hist=m['history']; hours=np.array([h['t'] for h in hist])/3600
    maxs=np.array([h['max'] for h in hist])
    points=[]; series=[]
    for label,requested in [('Centro V1',(0,0,.55)),('Centro V2',(0,0,1.65)),
                            ('Centro V3',(0,0,2.75)),('Lateral V1',(8,0,.55))]:
        dist=np.sum((coords-np.array(requested))**2,axis=-1); dist[ids==0]=np.inf
        index=np.unravel_index(np.argmin(dist),shape)
        values=np.where(active[(slice(None),)+index],T[(slice(None),)+index],np.nan)
        points.append(dict(nombre=label,xyz_m=coords[index].tolist(),indice=list(map(int,index)),
            max_muestreado_C=float(np.nanmax(values)),final_C=float(values[-1])))
        series.append(values)
    fig,axes=plt.subplots(1,2,figsize=(12,4.5),layout='constrained')
    for meta,label in zip(metas,['24×24×6','36×36×12']):
        axes[0].plot(np.array([h['t'] for h in meta['history']])/86400,[h['max'] for h in meta['history']],label=label)
    axes[0].axhline(70,color='r',ls='--',label='Criterio docente 70 °C')
    axes[0].set(xlabel='Tiempo desde primera vertida [días]',ylabel='T máxima activa [°C]',title='Tmax(t): todos los pasos del solver')
    for point,values in zip(points,series): axes[1].plot(ts/86400,values,label=point['nombre'])
    axes[1].set(xlabel='Tiempo [días]',ylabel='Temperatura [°C]',title='Puntos fijos: sin valor antes de colocación')
    for ax in axes: ax.grid(alpha=.25); ax.legend(fontsize=8)
    fig.savefig(OUT/'03_temperaturas.png',dpi=160); plt.close(fig)
    peak=m['metrics']['global_peak_time_s']; j=int(np.argmin(abs(ts-peak)))
    fig,axes=plt.subplots(1,2,figsize=(12,4.5),layout='constrained')
    for ax,a,b in [(axes[0],1,shape[1]//2),(axes[1],0,shape[0]//2)]:
        field=np.take(np.where(active[j],T[j],np.nan),b,axis=a)
        im=ax.imshow(field.T,origin='lower',extent=[-9,9,0,3.3],aspect='auto',vmin=18,vmax=60,cmap='inferno')
        coord=origin[a]+(b+.5)*spacing[a]
        ax.set(xlabel=('x [m]' if a==1 else 'y [m]'),ylabel='z [m]',title=f"Corte {'y' if a==1 else 'x'}={coord:.2f} m")
        fig.colorbar(im,ax=ax,label='T [°C]')
    fig.suptitle(f'Cortes del campo 3D al máximo global: día {peak/86400:.3f}')
    fig.savefig(OUT/'04_cortes.png',dpi=160); plt.close(fig)
    np.savetxt(OUT/'tmax.csv',np.column_stack([hours,maxs]),delimiter=',',header='tiempo_h,Tmax_C',comments='')
    np.savetxt(OUT/'sensores.csv',np.column_stack([ts/3600,*series]),delimiter=',',header='tiempo_h,centro_V1_C,centro_V2_C,centro_V3_C,lateral_V1_C',comments='')
    commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    patch=subprocess.check_output(['git','diff','--binary','HEAD','--','therma/resultados.py','tests/test_fase1_python.py'],cwd=ROOT)
    (OUT/'cambios_locales.patch').write_bytes(patch)
    summary=dict(commit_base=commit,arbol_con_cambios_locales=True,volumen_IFC_m3=volume,
                 volumenes=volumes,puntos=points,metricas=[v['metrics'] for v in metas])
    (OUT/'resumen.json').write_text(json.dumps(summary,indent=2,ensure_ascii=False),encoding='utf-8')
    for name in ['termico_cartesiano.py','therma/construccion.py','therma/activacion.py','therma/hidratacion.py','therma/resultados.py','modelo_e02.ifc','generar_entrega_e09.py']:
        summary.setdefault('sha256',{})[name]=hashlib.sha256((ROOT/name).read_bytes()).hexdigest()
    (OUT/'manifiesto.json').write_text(json.dumps(summary,indent=2,ensure_ascii=False),encoding='utf-8')
    rows='\n'.join(f"| {'×'.join(map(str,r['n']))} | {r['volume_m3']:.3f} | {r['error_pct']:.3f} % |" for r in volumes)
    sensor_rows='\n'.join(f"| {p['nombre']} | {', '.join(f'{v:.3f}' for v in p['xyz_m'])} | {p['max_muestreado_C']:.2f} | {p['final_C']:.2f} |" for p in points)
    coarse,fine=[v['metrics'] for v in metas]
    report=rf'''# E09 — Primera simulación 3D de la fundación

## Procedencia y reproducción

Repositorio: [Proyecto_2_MCOC](https://github.com/Santiago411323/Proyecto_2_MCOC).
Commit base de la corrida: `{commit}`. Corrida del 6 de noviembre de 2026 con la corrección de exportación sin Git y el script de evidencia incluidos en esta entrega. Se adjuntan el parche respecto de la base, configuración, CSV, resumen y hashes en `manifiesto.json`. Para identificar el commit que contiene esta entrega, ejecutar `git log -1 --format=%H -- docs/entrega_e09/ENTREGA.md`. Los resultados originales se generaron sobre árbol con cambios; el SHA base por sí solo no contiene esos cambios.

Reproducción desde la raíz, con dependencias de `requirements-lock.txt`:

```powershell
./.venv/Scripts/python.exe generar_entrega_e09.py
```

Los campos completos y metadatos se regeneran en `resultados/entrega_e09/malla_0` y `malla_1`. Las figuras y series quedan junto a este documento.

## Geometría, BIM y voxelización

Se usa `modelo_e02.ifc`, IFC4 con tres `IfcFooting` identificables por nombre y GUID. La envolvente mide 18×18×3,30 m, con base octagonal, transición inclinada y cilindro superior de diámetro 7 m. Es una **interpretación provisional del equipo**, no geometría oficial validada. Difiere de la simplificación de cinco vertidas y 4,30 m de altura de `GUIA_BONSAI_FUNDACION.md`; se requiere confirmar cuál acepta el profesor.

![Geometría BIM extraída del IFC](01_bim.png)

Se triangula el IFC y se clasifica el centro de cada celda dentro/fuera del sólido, conservando su vertida. Volumen geométrico: **{volume:.3f} m³**, calculado desde las mallas cerradas; no se usa el volumen de la caja envolvente. Se evalúa el volumen ocupado total, independientemente del horario de activación:

| Celdas de la caja | Volumen ocupado [m³] | Error absoluto relativo |
|---|---:|---:|
{rows}

Las dos primeras mallas también se simulan térmicamente; la tercera sólo verifica volumen. El error de volumen no disminuye monótonamente: depende de la alineación con las superficies. El refinamiento geométrico no constituye por sí solo convergencia térmica.

![Voxelización y activación de vertidas](02_voxeles.png)

## Vertidas y material

| Vertida | Intervalo z [m] | Inicio [h] | Colocación [°C] |
|---|---|---:|---:|
| 01 | 0–1,10 | 0 | 18 |
| 02 | 1,10–2,20 | 24 | 18 |
| 03 | 2,20–3,30 | 48 | 18 |

Cada pieza se activa instantáneamente. Antes de su colocación no conduce, genera ni almacena calor. Al activarse se inicializa a 18 °C y se reconstruyen interfaces y caras expuestas; el contacto entre vertidas es perfecto. M1 es una etiqueta didáctica: k=2 W/(m·K), ρ=2400 kg/m³ y cp=900 J/(kg·K), constantes. No hay dosificación ni grado resistente calibrado.

## Hidratación, ambiente y método

Para edad cronológica a desde la colocación de cada vertida:

$$\theta_{{ad}}(a)=40[1-\exp(-a/\tau)],\qquad \tau=24\ \mathrm{{h}}.$$

$$\dot q(a)=\rho c_p\frac{{40}}{{\tau}}\exp(-a/\tau).$$

En la fuente τ se convierte a segundos; q está en W/m³. La elevación final de 40 °C y τ son **hipótesis de ensayo**, no ajustes a 73 °C ni resultados calorimétricos. Cada vertida tiene su reloj y se integra exactamente el aporte de fuente por intervalo. No se representa la dependencia cinética con temperatura ni una fase de inducción.

Se simulan 14 días con balance explícito por celdas. En **todas** las caras exteriores, incluida la base, se usa Robin con ambiente constante de 20 °C, h=10 W/(m²·K) y resistencia adicional cero. La base recibe este intercambio efectivo simplificado: no se modela físicamente suelo. No hay clima real de Punta Arenas, radiación, moldaje ni retiro de protecciones. El paso automático respeta conductancias locales, eventos y resolución de hidratación. En la malla principal hay {fine['N']} celdas ocupadas, de 0,50×0,50×0,275 m; el paso máximo usado es {fine['dt']:.0f} s frente al límite local mínimo de {fine['dtMax']:.0f} s.

## Resultados e interpretación

En la malla principal 36×36×12, Tmax global es **{fine['maxField']:.2f} °C** a las **{fine['global_peak_time_s']/3600:.2f} h** ({fine['global_peak_time_s']/86400:.2f} días). El máximo se busca en todo el hormigón activo en cada paso, no sólo en un sensor. Con 24×24×6 se obtienen {coarse['maxField']:.2f} °C: diferencia de {abs(fine['maxField']-coarse['maxField']):.2f} °C; hacen falta más refinamientos y estudio temporal para afirmar independencia de malla.

![Máximo global y puntos representativos](03_temperaturas.png)

Los sensores corresponden a centros ocupados más próximos a posiciones solicitadas; las coordenadas efectivas son:

| Punto | x,y,z [m] | Máximo muestreado [°C] | T a 14 días [°C] |
|---|---|---:|---:|
{sensor_rows}

Los máximos de sensores usan los snapshots guardados, no todos los pasos. No se asigna temperatura física antes de activar la vertida. Los cortes muestran acumulación interior y disipación periférica:

![Cortes del volumen al máximo global](04_cortes.png)

El residual energético relativo máximo es {fine['energy_residual_relative']:.2e}, incluyendo energía de colocación, hidratación e intercambio. Pasaron 40 pruebas de hidratación, activación, construcción y exportación; conservación no equivale a validación experimental. Tmax queda bajo 70 °C en este escenario, pero no demuestra seguridad del plan. **No se evalúa ΔT a 25 mm**: los centros de esta grilla no representan esa profundidad.

## Comparación cualitativa con Ju y Lei

[Ju y Lei (2019)](https://doi.org/10.1155/2019/7029671) es la referencia física. La comparación se apoya en sus figuras descritas en la presentación del curso (diapositivas 3–5 y 13), sin digitalizar series del artículo. Se reproduce cualitativamente el calentamiento por hidratación, un máximo diferido durante los primeros días, posterior enfriamiento y un interior más caliente que las zonas expuestas. La activación incorpora además diferentes edades térmicas por vertida.

No se reproducen cuantitativamente los aproximadamente 73 °C alrededor del día 4 ni el diferencial vertical próximo a 35 °C del día 9 descritos en ese material. Tampoco se reproducen mezcla, cronograma, sensores, clima ni restricciones mecánicas experimentales. La ley exponencial, geometría provisional y bordes simplificados explican diferencias posibles, pero no identifican su contribución individual. Faltan calibración y validación para estimar fisuración o recomendar una construcción real.
'''
    (OUT/'ENTREGA.md').write_text(report,encoding='utf-8')
    print(json.dumps(summary,indent=2,ensure_ascii=False))


if __name__ == '__main__':
    main()
