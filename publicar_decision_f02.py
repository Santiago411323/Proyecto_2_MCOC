"""Exporta evidencia determinista del lote congelado al panel y a un HTML portátil."""
import base64
import hashlib
import io
import json
from html import escape
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

from therma.comparacion_f02 import aggregate_estimated, op_config
from therma.lotes import canonical, fingerprint

ROOT = Path(__file__).resolve().parent
OUT = ROOT / 'docs/decision_f02'
CAT = ROOT / 'docs/cierre_f02/evidencia'
ICE = ROOT / 'docs/hielo_f02'


def read(path):
    return json.loads(path.read_bytes())


def num(x, places=2):
    return f'{float(x):.{places}f}'.replace('.', ',')


def table(labels, rows):
    content = ''.join('<tr>' + ''.join(f'<td>{item}</td>' for item in row) + '</tr>' for row in rows)
    return '<div class="table-scroll"><table class="plan-table"><thead><tr>' + ''.join(
        f'<th scope="col">{x}</th>' for x in labels) + '</tr></thead><tbody>' + content + '</tbody></table></div>'


def figure(r, history, folder, plan, schedule_end_h):
    peak = r['peak_S25']
    t = [h['time_s']/86400 for h in history]
    fig, axes = plt.subplots(2, 2, figsize=(10, 6), layout='constrained')
    schedule, curves, delta, cut = axes.ravel()
    for op in plan['operations']:
        start, end = op['start_h'], op['end_h']
        schedule.barh(op['id'], end-start, left=start, color='#298684')
        schedule.plot(op['start_h'], op['id'], marker='|', color='black')
    schedule.set(yticks=[op['id'] for op in plan['operations']], xlim=(0,schedule_end_h), xlabel='Horas desde el inicio', ylabel='Operación', title='Colocación física')
    for key, label in [('Tmax_C','Máxima activa'), ('Tmin_S25_estimate_C','Mínima S25')]:
        curves.plot(t,[h[key] for h in history], label=label)
    curves.axhline(70, color='firebrick', linestyle='--')
    curves.set(xlabel='Días', ylabel='°C', ylim=(0,75), title='Envolventes de temperatura')
    curves.legend()
    delta.plot(t,[h['DeltaT_estimate_C'] for h in history])
    delta.axhline(20,color='firebrick',linestyle='--')
    delta.scatter(peak['time_s']/86400,peak['DeltaT_estimate_C'],color='black')
    delta.set(xlabel='Días', ylabel='ΔT estimado [°C]', ylim=(0,50), title='Diferencial simultáneo')
    with np.load(folder/'s25_ifc_critical.npz') as field:
        assert np.isclose(field['time_s'],peak['time_s'])
        j = peak['hot_index'][1]
        x,_,z = field['origin_m']
        dx,_,dz = field['spacing_m']
        raw=field['T_C'][:,j,:]
        data=np.ma.masked_where(~field['active'][:,j,:].astype(bool),raw)
        im=cut.imshow(data.T, origin='lower',extent=[x,x+raw.shape[0]*dx,z,z+raw.shape[1]*dz],aspect='equal',vmin=0,vmax=70,cmap='inferno')
        cut.plot(peak['hot_xyz_m'][0],peak['hot_xyz_m'][2],'c+',ms=9)
        fig.colorbar(im,ax=cut,label='°C',shrink=.8)
    cut.set(xlabel='X [m]',ylabel='Z [m]',title=f"Corte por punto caliente · {num(peak['time_s']/3600,1)} h")
    stream=io.BytesIO()
    fig.savefig(stream,format='png',dpi=105)
    plt.close(fig)
    return '<img style="width:100%;height:auto" alt="Cronograma, temperaturas, diferencial y corte al instante crítico" src="data:image/png;base64,'+base64.b64encode(stream.getvalue()).decode()+'">'


def load_run(path, scenario, plan, catalog, engine):
    if not path.exists():
        return []
    r=read(path)
    config=op_config(catalog,plan,scenario['source_id'],[96,96,54],days=42,dt=1200)
    if (r.get('configuration_hash')!=hashlib.sha256(canonical(config)).hexdigest()
            or r.get('status')!='COMPLETED' or r.get('shape')!=[96,96,54]
            or r.get('source_id')!=scenario['source_id'] or r.get('engine_fingerprint')!=engine
            or r.get('horizon_audit',{}).get('end_h')!=1008 or r.get('dt_requested_s')!=1200):
        return []
    return [dict(r,scenario_id=scenario['id'],weight=scenario['weight'])]


def main():
    catalog=read(CAT/'catalogo_congelado.json')
    scenarios=catalog['scenarios']
    plans={p['id']:p for p in catalog['plans']}
    engine=fingerprint()
    entries=[]
    for temp in (8,12):
        report=read(ICE/f'plan_{temp}_estudiada.json')
        records=[]
        for s in scenarios:
            path=ICE/'convergencia'/f"T{temp}_96x96x54_dt1200_{s['source_id']}.json"
            plan_id={8:'t8_eps100_base1',12:'t12_eps100_base1.0'}[temp]
            records.extend(load_run(path,s,plans[plan_id],catalog,engine))
        entries.append((report['plan'],records,report['mix']['total_t'],'96×96×54','hielo_f02'))
    for pid in ('continua','propuesto','rapido','lento'):
        records=[]
        for s in scenarios:
            path=ROOT/'docs/malla_comun/corridas'/f"{pid}_96x96x54_dt1200_{s['source_id']}.json"
            records.extend(load_run(path,s,plans[pid],catalog,engine))
        entries.append((plans[pid],records,0,'96×96×54','malla_comun'))

    summary=[]; details=[]; candidates=[]
    registry_path=ROOT/'resultados/planes_publicados.json'
    registry=read(registry_path) if registry_path.exists() else {}
    schedule_end_h=max(plan['D_h'] for plan,*_ in entries)
    for plan,records,ice,mesh,cache in entries:
        if not records:
            summary.append([escape(plan['name']),num(plan['D_h']),num(ice),mesh,'—','—','0 de 4 disponibles',
                            'Pendiente','Pendiente','Pendiente','Pendiente de simulación'])
            continue
        same_engine=len({r['engine_fingerprint'] for r in records})==1
        risk=aggregate_estimated([dict(r,coverage=float(r['coverage_air_min_fraction'])) for r in records],scenarios)
        rates=[risk[k] for k in ('P_T','P_Delta','P_f')]
        if not same_engine:
            rates=[None]*3
        if ice and rates[2] is not None and rates[2]<=.05:
            candidates.append((plan['placement_C'],ice))
        name=escape(plan['name'])
        if ice:
            name=f"Hielo a {plan['placement_C']:g} °C"
        failed=sum(float(r['Delta_estimate_C'])>20 or float(r['Tmax_C'])>70 for r in records)
        summary.append([name,num(plan['D_h']),num(ice),mesh,num(max(float(r['Tmax_C']) for r in records)),
            num(max(float(r['Delta_estimate_C']) for r in records)),f'{failed} de {len(records)} disponibles',*[num(100*p,0)+' %' if p is not None else 'Pendiente' for p in rates],
            'Indeterminado' if rates[2] is None else 'Sí · estimado' if rates[2]<=.05 else 'No · estimado'])
        rows=[]
        critical=max(records,key=lambda r:float(r['Delta_estimate_C']))
        plot=''
        for r in records:
            folder=ROOT/'resultados'/cache/'cache'/r['cache_key']
            hist=read(folder/'s25_ifc.json')['history'] if (folder/'s25_ifc.json').exists() else []
            ident=escape(r['simulation_id'])
            if hist and (folder/'fields.bin').is_file():
                artifacts=r['artifacts']
                registry[ident]=dict(folder=folder.relative_to(ROOT).as_posix(),
                                     artifacts=json.loads(artifacts) if isinstance(artifacts,str) else artifacts)
                ident=f'<span data-decision-run="{ident}">{ident}</span>'
            first=[h for h in hist if h['time_s']<=336*3600]
            exceeded=[]
            if float(r['Tmax_C'])>70:
                exceeded.append('Tmax')
            if float(r['Delta_estimate_C'])>20:
                exceeded.append('ΔT')
            rows.append([escape(r['source_id']),num(r['weight']),num(max(h['Tmax_C'] for h in first)) if first else 'Sin serie',
                num(max(h['DeltaT_estimate_C'] for h in first)) if first else 'Sin serie',num(r['Tmax_C']),num(r['Delta_estimate_C']),
                num(r['Tmax_time_h'],1),num(r['Delta_time_h'],1),' y '.join(exceeded) or 'Ninguno',ident])
            if r is critical and hist and (folder/'s25_ifc_critical.npz').exists():
                peak=r['peak_S25']
                hot=', '.join(num(v,3) for v in peak['hot_xyz_m'])
                cold=', '.join(num(v,3) for v in peak['S25_xyz_m'])
                surface={'air':'cara hacia el aire','soil':'contacto con el suelo'}.get(peak.get('region'),'frontera IFC')
                plot=(f"<p>Mayor diferencial estimado · {escape(r['source_id'])} · {num(peak['time_s']/3600)} h. "
                      f"En ese instante, {num(peak['Tmax_C'])} °C en el punto caliente menos {num(peak['Tmin_S25_estimate_C'])} °C a 25 mm "
                      f"da {num(peak['DeltaT_estimate_C'])} °C. Punto caliente XYZ [m] ({hot}). Punto S25 XYZ [m] ({cold}), {surface}.</p>"
                      +figure(r,hist,folder,plan,schedule_end_h))
        details.append('<details><summary>'+name+f' · {len(records)}/4 corridas · ver evidencia</summary>'+table(
            ['Fuente','Peso','Tmax 14 d [°C]','ΔT 14 d [°C]','Tmax 42 d [°C]','ΔT 42 d [°C]','Hora Tmax','Hora ΔT','Supera (aprox.)','Corrida'],rows)+plot+'</details>')
    title=('Planes con hielo · empate en duración a 24,35 h' if len(candidates)==2 else 'Planes con hielo · comparación a 24,35 h')
    text=' y '.join(f'{t:g} °C ({num(i)} t de hielo)' for t,i in candidates)
    decision=(f'Bajo el criterio aproximado del lote quedan {text}.' if candidates else 'La decisión depende del resultado de las cuatro fuentes de cada candidato.')
    block='<section class="panel" id="decisionDefensa"><h2>'+title+'</h2><p>'+decision+' Ambos candidatos usan EPS de 100 mm y resistencia basal adicional de 1,0 m²·K/W. El tiempo mínimo de colocación se obtiene dividiendo 487,07 m³ por 20 m³/h. Supone hielo disponible al inicio y capacidad de colocación sostenida.</p>'+table(
        ['Plan','D [h]','Hielo [t]','Malla','Tmax [°C]','ΔT aprox. [°C]','Fallan','P_T','P_Δ aprox.','P_f aprox.','≤5 %'],summary)
    block+='<p>«Fallan» cuenta las corridas que superan 70 °C de temperatura máxima o 20 °C de diferencial estimado. Cada una de las cuatro fuentes SS pesa 25 %. Comparten el clima desde el 19 de noviembre a las 10:00, extendido repitiendo las últimas 48 h. Las probabilidades corresponden a 42 días. Los seis planes se evalúan con la misma malla de 96 × 96 × 54. S25 estima la temperatura a 25 mm de la superficie IFC. Su validación física sigue pendiente.</p>'+''.join(details)+'</section>'
    mesh=next(m for m in read(ICE/'convergencia/cobertura.json') if m['shape']==[96,96,54])
    mesh_note=(f"<details><summary>¿Qué malla se utilizó para los seis planes?</summary><p>"
               f"{mesh['total_cells']} celdas en la grilla, {mesh['active_cells']} de hormigón al terminar la colocación. "
               f"El volumen voxelizado difiere en {num(mesh['volume_error_pct'])} % respecto del IFC. "
               "Este porcentaje mide la diferencia de volumen. Usar la misma resolución permite comparar los seis planes. "
               "Demostrar convergencia del diferencial de cada plan requiere repetirlo en varias resoluciones.</p></details>")
    block=block.removesuffix('</section>')+mesh_note+'</section>'
    OUT.mkdir(exist_ok=True)
    registry_path.write_text(json.dumps(registry,ensure_ascii=False),encoding='utf8')
    (OUT/'fragmento.html').write_text(block,encoding='utf8')
    (OUT/'decision.html').write_text('<!doctype html><html lang="es"><meta charset="utf-8"><title>THERMA · Decisión F02</title><style>body{font:16px system-ui;max-width:1200px;margin:3vw auto;padding:16px}table{border-collapse:collapse}th,td{padding:8px;border-bottom:1px solid #bbb;text-align:left}.table-scroll{overflow:auto}summary{padding:12px;cursor:pointer}</style>'+block+'</html>',encoding='utf8')


if __name__=='__main__':
    main()
