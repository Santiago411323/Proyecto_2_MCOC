"""Vista de defensa a partir de planes y corridas ya guardados."""
import base64
from collections import defaultdict
from html import escape
from io import BytesIO
import math
from pathlib import Path

from matplotlib.figure import Figure

from therma.comparacion_f02 import ROOT, load, read

MESH = [96, 96, 54]
PLAN_NAMES = {
    'continua': 'Vertida única', 'propuesto': 'Propuesto', 'rapido': 'Más rápido',
    'lento': 'Más lento', 't8_eps100_base1': 'Hielo a 8 °C',
    't12_eps100_base1.0': 'Hielo a 12 °C',
}
TEN = '5950c8275e6d4991826e5dda60412284'
TWELVE = '1dfa0d1c493d439b88651a9815e33cec'
NITROGEN = '78f89b0fd7aa498db53c4a2600b801a6'
BASAL = 'fb6215d3ad7d4a5fb6377f46304cfdd7'


def number(value, digits=2):
    return ('—' if value is None else f'{value:.{digits}f}'.replace('.', ','))


def table(headers, rows):
    head = ''.join(f'<th scope="col">{h}</th>' for h in headers)
    body = ''.join('<tr>' + ''.join(f'<td>{x}</td>' for x in row) + '</tr>' for row in rows)
    return f'<div class="table-scroll"><table class="plan-table"><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table></div>'


def link(ident, name='Abrir corrida'):
    if not isinstance(ident,str) or len(ident)!=32 or any(c not in '0123456789abcdef' for c in ident):
        return '—'
    return f'<a href="?result={ident}#simulationDesk">{escape(name)}</a>'


def schedule(entries):
    if not entries:
        return ''
    step = 20 if max(end for _, _, end in entries)>40 else 5
    scale = step*math.ceil(max(end for _,_,end in entries)/step)
    ticks=''.join(f'<span style="left:{100*t/scale:g}%">{t}</span>' for t in range(0,scale+1,step))
    body = ''
    for name, operations, end in entries:
        segments = ''
        for n, o in enumerate(operations, 1):
            start, stop = o['start_h'], o['end_h']
            info = f'Vertida {n}: {number(start)}–{number(stop)} h'
            segments += (f'<span class="defense-pour" style="left:{100*start/scale:.6f}%;width:{100*(stop-start)/scale:.6f}%"'
                         f' title="{info}"></span>')
        schedule_text='; '.join(f'{number(o["start_h"])} a {number(o["end_h"])} h' for o in operations)
        body += (f'<div class="defense-schedule-row"><span>{escape(name)}</span><div class="defense-track"'
                 f' role="img" aria-label="{schedule_text}">{segments}</div><strong>{number(end)} h</strong></div>')
    return ('<div class="table-scroll"><div class="defense-schedule"><div class="defense-schedule-row">'
            f'<span>Horas desde el inicio</span><div class="defense-ticks">{ticks}</div><span>Total</span></div>'
            +body+'</div></div>')


def risk_plot(points):
    if not points:
        return '<p class="hint">El catálogo no contiene valores comparables de P_f.</p>'
    grouped = defaultdict(list)
    for name, duration, risk in points:
        grouped[(round(duration,2), risk)].append(name)
    fig = Figure(figsize=(9,3.9), layout='constrained', facecolor='#111d2a')
    ax = fig.subplots()
    ax.set_facecolor('#111d2a')
    ax.axhline(5, linestyle='--', color='#f4b17d', label='Límite 5 %')
    for (x,y), names in sorted(grouped.items()):
        ax.scatter(x,y,s=48,c='#79dfc7' if y<=5 else '#ecaa8a',zorder=3)
        alignment = 'right' if x>85 else 'left'
        label = 'Hielo 8 °C y 12 °C' if len(names)==2 and all(n.startswith('Hielo') for n in names) else ' / '.join(names)
        # Las etiquetas de 100 % alternan niveles para separar los planes más próximos.
        high_offsets = {'Vertida única':(0,19), 'Más rápido':(8,-25),
                        'Propuesto':(8,19), 'Más lento':(-8,-25)}
        offset = high_offsets.get(label,(-8 if x>85 else 8,9)) if y==100 else (8,8)
        ax.annotate(label,(x,y),xytext=offset,textcoords='offset points',ha=alignment,color='#dce9f4',fontsize=9)
    ax.set(xlim=(0,max(110,max(x for _,x,_ in points)+12)),ylim=(-8,120),
           xlabel='Duración física D [h]',ylabel='P_f conjunta estimada [%]',yticks=[0,5,25,50,75,100])
    ax.grid(axis='y',alpha=.2)
    ax.tick_params(colors='#c7dae8')
    ax.xaxis.label.set_color('#dce9f4')
    ax.yaxis.label.set_color('#dce9f4')
    for edge in ax.spines.values():
        edge.set_color('#466278')
    ax.legend(loc='center right',facecolor='#162636',labelcolor='#fff')
    buffer=BytesIO()
    fig.savefig(buffer,format='png',dpi=140,facecolor=fig.get_facecolor())
    encoded=base64.b64encode(buffer.getvalue()).decode('ascii')
    return ('<img class="defense-risk" width="1260" height="546" alt="Duración física frente a excedencia conjunta estimada, con línea límite del 5 %."'
            f' src="data:image/png;base64,{encoded}">')


def primary_lot():
    cohorts=load().public()['cohorts']
    candidates=[c for c in cohorts if c['id'].startswith('malla-comun-')]
    if not candidates:
        return '<p>El lote F02 de la malla común todavía no está disponible.</p>'
    cohort=max(candidates,key=lambda c:sum(len(p['runs']) for p in c['plans']))
    plans={p['id']:p for p in cohort['plans']}
    rows, schedules, points = [], [], []
    for key, name in PLAN_NAMES.items():
        if key not in plans:
            continue
        p=plans[key]
        risk=p['estimated_risk']
        pf=risk['P_f']
        d=p['D_h']
        if pf is not None and d is not None:
            points.append((name,d,100*pf))
        if d is not None and p['operations']:
            schedules.append((name,p['operations'],d))
        m4=next((r for r in p['runs'] if r['source_id']=='fv_M4_SS' and r['can_open']),None)
        display_name = f'<strong>{name}</strong>' if pf is not None and pf<=.05 else name
        rows.append([display_name,number(d),number(p['Tmax_C']),number(p['Delta_estimate_C']),
                     str(sum(r['I_F_estimated'] is True for r in p['runs']))+' / '+str(p['evaluated']),
                     (number(100*pf,0)+' %') if pf is not None else '—',
                     link(m4['simulation_id'],'Ver M4_SS') if m4 else '—'])
    ice_pair=[p for p in points if p[0].startswith('Hielo') and p[2]<=5]
    conclusion=('Los dos candidatos con hielo comparten la duración mínima del lote y el mismo punto en el gráfico. '
                'El de 8 °C tiene mayor margen frente a 20 °C. ' if len(ice_pair)==2 and ice_pair[0][1:]==ice_pair[1][1:] else '')
    return ('<section class="panel defense-section"><h2>Comparación de planes F02</h2>'
            '<p>Vertida única, propuesta y variantes en la misma malla. Cada plan se probó con cuatro fuentes SS y una historia común de Open‑Meteo. '
            'Se cuenta una sola excedencia por corrida cuando se supera cualquiera de los dos límites. Cada fuente pesa 25 %.</p>'
            +table(['Plan','D [h]','Tmax [°C]','ΔT S25 est. [°C]','Exceden / corridas','P_f estimada','Campo'],rows)
            +'<h3>Cronogramas con el mismo reloj</h3><p>Las barras representan colocación de hormigón y los espacios representan esperas.</p>'
            +schedule(schedules)
            +'<h3>Duración frente a riesgo conjunto</h3>'+risk_plot(points)
            +f'<p>{conclusion}P_f se estima dentro de este catálogo. S25 sigue pendiente de validación física.</p></section>')


def trial_sequence(folder):
    evidence=read(ROOT/'docs/decision_f02/ensayos_meteored.json',{})
    runs={r['simulation_id']:r for r in evidence.get('runs',[])}
    controls={r['protection_control']:r['simulation_id'] for r in runs.values() if r.get('control_reference')==TEN}
    definitions=[
        (controls.get('sin_protecciones'),'10 vertidas · sin moldaje ni EPS','14,00'),
        (controls.get('moldaje'),'10 vertidas · solo moldaje','14,00'),
        (TEN,'10 vertidas · moldaje + EPS','14,00'),
        (TWELVE,'12 vertidas · moldaje + EPS','14,00'),
        (NITROGEN,'Vertida única · nitrógeno + moldaje + EPS','8,00'),
        (BASAL,'Vertida única · nitrógeno + moldaje + EPS + protección basal','8,00'),
    ]
    rows, schedules = [], []
    for ident,label,placement in definitions:
        r=runs.get(ident)
        if not r or r['shape']!=MESH or r['status']!='COMPLETED':
            rows.append([label,placement,'—','—','—','Sin resultado cargado','—'])
            continue
        ops=r['placement_schedule']
        duration=ops[-1]['end_h']
        tmax=r['Tmax_C']
        delta=r['DeltaT_S25_estimate_C']
        if tmax>70 or delta>20:
            verdict='Supera un límite'
        elif r['complete_sampling']:
            verdict='Bajo 70 / 20 · estimado'
        else:
            verdict='Cobertura S25 parcial'
        local=folder/ident
        can_open=all((local/name).is_file() for name in ('metadata.json','fields.bin','active.bin'))
        rows.append([label,placement,number(duration),number(tmax),number(delta),verdict,
                     link(ident) if can_open else 'Resumen publicado'])
        if ident in (TEN,TWELVE,BASAL):
            schedules.append((label.split(' · ')[0],ops,duration))
    return ('<section class="panel defense-section"><h2>Qué probamos con Meteored</h2>'
            '<p>Leemos de arriba hacia abajo: efecto del moldaje y el EPS en diez vertidas, cambio de número de vertidas, '
            'y protección basal en una vertida preenfriada. Todos usan 96 × 96 × 54, M4_SS y el mismo clima Meteored. '
            'Una fuente permite comparar valores térmicos en ese escenario. El gráfico de P_f corresponde al lote F02 de cuatro fuentes.</p>'
            +table(['Ensayo','Tcol [°C]','D [h]','Tmax [°C]','ΔT S25 est. [°C]','Umbrales','Resultado'],rows)
            +'<details class="workflow-details"><summary>Cronogramas de 10, 12 y una vertida</summary>'
            +schedule(schedules)+'<p>A 20 m³/h y sin esperas, dividir la fundación en más etapas conserva el tiempo físico total de colocación.</p></details>'
            '<p class="hint">Meteored Punta Arenas se usa como aproximación a Faro del Sur. Para completar 42 días, se repite el último ciclo de 24 h disponible.</p></section>')


def render():
    return ('<section id="defensePresentation"><p class="defense-intro">'
            '<strong>Malla 96 × 96 × 54</strong> · horizonte térmico de 42 días · límites de 70 °C y 20 °C.</p>'
            +trial_sequence(Path(ROOT/'resultados/servidor_therma'))+primary_lot()+'</section>')
