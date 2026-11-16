"""Paso 1 E13: auditar las ocho fuentes entregadas, sin simular ni asignar pesos."""
import csv
import hashlib
import json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT=Path(__file__).resolve().parent
NAMES=[f'M{i}_{campaign}' for campaign in ('SS','22A') for i in range(1,5)]


def main():
    source=ROOT/'data/hydration/source_terms.txt'
    out=ROOT/'docs/e13/paso01_curvas';out.mkdir(parents=True,exist_ok=True)
    data=np.loadtxt(source);time=data[:,0]
    if data.shape[1]!=9 or not np.isfinite(time).all() or time[0]!=0 or not np.all(np.diff(time)>0):
        raise ValueError('Se requieren tiempo creciente desde cero y ocho columnas Q.')
    curves=[]
    for col,name in enumerate(NAMES,1):
        finite=np.isfinite(data[:,col]);indices=np.flatnonzero(finite)
        if len(indices)<2 or not np.array_equal(indices,np.arange(len(indices))):
            raise ValueError(name+': faltantes internos; no completar silenciosamente.')
        t=time[finite];q=data[finite,col]
        if np.any(q<0):raise ValueError(name+': fuente negativa por revisar.')
        curves.append((name,t,q))
    common_end=min(t[-1] for _,t,_ in curves)
    fig,axes=plt.subplots(2,1,figsize=(12,9),layout='constrained',sharex=True)
    rows=[]
    for i,(name,t,q) in enumerate(curves):
        seconds=t*3600
        energy=np.r_[0.,np.cumsum(np.diff(seconds)*(q[:-1]+q[1:])/2)]
        selected=t<=common_end
        common_energy=float(np.trapezoid(q[selected],seconds[selected]))
        peak=int(np.argmax(q));color=plt.get_cmap('tab10')(i%4)
        style='-' if i<4 else '--'
        axes[0].plot(t,q,color=color,ls=style,label=name)
        axes[1].plot(t,energy/1e6,color=color,ls=style,label=name)
        for ax,value in zip(axes,(q[-1],energy[-1]/1e6)):
            ax.plot(t[-1],value,marker='o',color=color,ms=4)
        rows.append(dict(curve=name,campaign='SS' if i<4 else '22A',samples=len(t),
            end_h=float(t[-1]),Q_peak_W_m3=float(q[peak]),peak_h=float(t[peak]),Q_end_W_m3=float(q[-1]),
            energy_observed_MJ_m3=float(energy[-1]/1e6),energy_common_MJ_m3=common_energy/1e6,
            equivalent_adiabatic_rise_observed_C=float(energy[-1]/(2476*1023)),
            missing_to_age_336_h=float(336-t[-1])))
    for ax in axes:
        ax.axvline(common_end,color='gray',lw=1,ls=':',label=f'Fin común: {common_end:.2f} h')
        ax.grid(alpha=.2)
    axes[0].legend(ncol=3,fontsize=9)
    axes[0].set(ylabel='Fuente Q [W/m³]',title='Ocho curvas entregadas · continua: SS / discontinua: 22A')
    axes[1].set(ylabel='Energía acumulada observada [MJ/m³]',xlabel='Tiempo desde inicio de ventana retenida [h]')
    fig.savefig(out/'ocho_curvas.png',dpi=160);plt.close(fig)
    with (out/'resumen.csv').open('w',encoding='utf-8',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=rows[0]);writer.writeheader();writer.writerows(rows)
    audit=dict(source='data/hydration/source_terms.txt',raw_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
        units=dict(time='h',source='W/m3',integrated_energy='MJ/m3'),common_end_h=float(common_end),
        time_origin='Inicio de ventana retenida: inicio del registro +2 h. Edad desde mezcla no establecida.',
        status='DATA_AUDIT_ONLY_NO_PROBABILITY_ASSIGNED',curves=rows,
        unknowns=['El encabezado declara 350.77 kg/m³ de cemento y rho/cp; faltan composición detallada y temperaturas de ensayo por muestra.',
                  'No se establece que M1-M4 y las campañas sean réplicas de una misma población.',
                  'Fuente vigente recuperada por FV/Tikhonov; el encabezado declara menor confianza de 22A. Falta validación independiente de la fundación.'],
        policy='Sin suavizado, derivación, relleno de NaN ni extrapolación. Se integra Q original lineal por tramos.',
        adiabatic_note='Elevación equivalente = integral Q/(2476*1023), no temperatura medida ni resultado de fundación.')
    (out/'auditoria.json').write_text(json.dumps(audit,ensure_ascii=False,indent=2),encoding='utf-8')
    text='''# E13 — Paso 1: entender los datos de hidratación

Se inspeccionaron las ocho columnas de `data/hydration/source_terms.txt`.
Se usa la fuente FV/Tikhonov confirmada por el usuario el 16-11-2026.
El archivo PINN previo fue retirado por datos incorrectos. No se asignaron probabilidades.

El archivo declara Q en W/m³, recuperada mediante FV/Tikhonov para probetas cilíndricas
de radio 0.0375 m y altura 0.15 m. No son temperaturas medidas ni curvas de
incremento adiabático. No multiplicar Q por densidad y calor específico.
El tiempo está en horas y comienza en una ventana retenida, registro +2 h.
El beta declarado corresponde al ensayo; no es automáticamente el h de la fundación.

![Fuentes e integrales](ocho_curvas.png)

Cada color identifica M1-M4. Línea continua: campaña SS (13–20 abril 2025);
discontinua: campaña 22A (22 abril 2025). Los puntos marcan el último dato:
las líneas terminan allí porque no conocemos su continuación.

Arriba se muestra potencia por volumen: una curva más alta libera energía más
rápido en ese instante. Abajo se muestra su integral: energía acumulada por
volumen. El pico más alto no identifica necesariamente la mayor energía total.
Para integrar se convierten horas a segundos; W·s/m³ = J/m³.

SS cubre hasta 240.333 h; 22A tiene datos finitos hasta 163.0 h.
Para comparar integral en igualdad de condiciones se usa el final común, 163.0 h: columna energy_common_MJ_m3
del CSV. No comparar integral total SS y 22A como si cubrieran igual duración.
Los NaN al final de 22A son ausencia de información, no Q=0.

Ninguna curva cubre edad 336 h. Antes de simular hay que declarar y estudiar
el efecto de una política de cola. Este paso no extiende las curvas.
La cola constante empleada en E12 fue una hipótesis; no se convierte aquí
en evidencia experimental ni se copia automáticamente a ocho escenarios.

El CSV incluye la elevación adiabática equivalente de la energía observada
usando rho=2476 kg/m³ y cp=1023 J/(kg K), declarados en el encabezado vigente. Es sólo una conversión con esas propiedades, no una temperatura observada ni una predicción térmica de la fundación.

## Lo que falta saber antes de asignar pesos

¿M1-M4 tienen la misma receta o son mezclas distintas? ¿Qué temperatura inicial,
condiciones de ensayo corresponden a cada muestra? El contenido de cemento
de referencia declarado es 350.77 kg/m³.
¿Qué evidencia respalda la identificación de Q? El encabezado no resuelve todas esas preguntas. No se puede afirmar todavía que las ocho curvas sean réplicas
equiprobables. Si siguen faltando antecedentes, se pueden declarar escenarios
de incertidumbre de modelo y estudiar sensibilidad de los pesos, explicando el supuesto.

Este paso no selecciona una mezcla ni calcula probabilidad de falla. El siguiente
paso es fijar la interpretación material, el origen temporal y la cola para
utilizar cada historia completa sin mezclar sus puntos.

Repetir desde la raíz: `.\\.venv\\Scripts\\python.exe analizar_curvas_e13.py`.
Fuente y SHA-256 están en `auditoria.json`; estadísticas en `resumen.csv`.
'''
    (out/'PASO_01.md').write_text(text,encoding='utf-8')
    print('Fin común [h]:',common_end)
    for r in rows:
        print(f"{r['curve']:7s} pico={r['Q_peak_W_m3']:8.2f} W/m³ a {r['peak_h']:6.2f} h; energía común={r['energy_common_MJ_m3']:7.2f} MJ/m³; fin={r['end_h']:.2f} h")


if __name__=='__main__':main()
