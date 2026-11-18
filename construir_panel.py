"""Genera THERMA; el visor WebGL carga dependencias locales desde el servidor."""
from pathlib import Path
import json
import hashlib
import numpy as np
from panel.exportar_ifc import datos_ifc

BASE = Path(__file__).resolve().parent


def graficos_fuentes(path):
    """Un par de ejes comunes; respeta huecos y fin de cada registro."""
    datos = np.loadtxt(path)
    if datos.ndim != 2 or datos.shape[1] != 9:
        raise ValueError('Se esperaba tiempo y ocho columnas FV/Tikhonov.')
    horas = datos[:, 0]
    xmax = np.ceil(horas.max()/50)*50
    ymax = np.ceil(np.nanmax(datos[:, 1:])/100)*100
    figuras = []
    for grupo, primera in [('SS', 1), ('22A', 5)]:
        svg = [f'<svg viewBox="0 0 480 218" role="img" aria-label="Generación de calor de las cuatro probetas {grupo}"><title>Campaña {grupo} · Q en W/m³</title>']
        for valor in np.arange(0, ymax+1, 100):
            y = 177-147*valor/ymax
            svg.append(f'<path d="M45 {y} H461" stroke="#324457"/><text x="39" y="{y+4}" text-anchor="end">{valor:.0f}</text>')
        for t in np.arange(0, xmax+1, 50):
            svg.append(f'<text x="{45+416*t/xmax}" y="194" text-anchor="middle">{t:.0f}</text>')
        svg.append('<text x="7" y="15">Q [W/m³]</text><text x="164" y="213">Edad desde la ventana retenida [h]</text>')
        for i,color in enumerate(['#5bdcc8','#ffb473','#aab5ff','#f879a1']):
            commands = []
            move = True
            for t,q in zip(horas, datos[:, primera+i]):
                if not np.isfinite(q):
                    move = True
                    continue
                commands.append(f'{"M" if move else "L"}{45+416*t/xmax:.2f},{177-147*q/ymax:.2f}')
                move = False
            svg.append(f'<path fill="none" stroke="{color}" stroke-width="1.8" d="{" ".join(commands)}"><title>M{i+1}_{grupo}</title></path>')
            svg.append(f'<text x="{158+72*i}" y="15" style="fill:{color}">M{i+1}_{grupo}</text>')
        figuras.append(f'<figure><figcaption>Campaña {grupo}</figcaption>'+''.join(svg)+'</svg></figure>')
    return ''.join(figuras)


def main():
    origen = BASE/'panel'
    html = (origen/'plantilla.html').read_text(encoding='utf-8')
    for marcador, archivo in [('STYLE', 'estilos.css'), ('SOLVER', 'solver.js'), ('API', 'api.js'), ('APP', 'app.js'), ('FOUNDATION', 'fundacion.js'), ('VIEWDATA', 'visordatos.js'), ('VIEWUI', 'visor.html'), ('VIEWSTYLE', 'visor.css'), ('INTELLIGENCE', 'inteligencia.js'), ('RESEARCHUI', 'investigacion.html'), ('RESEARCHSTYLE', 'investigacion.css'), ('CONSTRUCTIONUI', 'construccion.html'), ('CONSTRUCTIONSCRIPT', 'construccion.js'), ('ENVIRONMENTUI', 'entorno.html'), ('ENVIRONMENTSCRIPT', 'entorno.js'), ('EQUATIONUI', 'ecuaciones.html'), ('EQUATIONSTYLE', 'ecuaciones.css'), ('EQUATIONMODEL', 'ecuaciones_modelo.js'), ('EQUATIONSCRIPT', 'ecuaciones.js'), ('FORMWORKUI', 'moldaje.html'), ('FORMWORKMATH', 'moldaje_modelo.js'), ('FORMWORKSCRIPT', 'moldaje_ui.js'), ('COREEXTERIOR', 'nucleo_exterior.js'), ('WEATHERSCRIPT', 'clima_ui.js'), ('RESOLUTIONMODEL', 'resolucion_modelo.js'), ('RESOLUTIONUI', 'resolucion_ui.js')]:
        html = html.replace(f'/*__{marcador}__*/', (origen/archivo).read_text(encoding='utf-8'))
    html = html.replace('/*__FOUNDATIONEDITOR__*/', (origen/'geometria_ui.js').read_text(encoding='utf-8'))
    html = html.replace('/*__SIMULATIONS__*/', (origen/'simulaciones.js').read_text(encoding='utf-8'))
    html = html.replace('/*__NAVSTYLE__*/', (origen/'navegacion.css').read_text(encoding='utf-8'))
    html = html.replace('/*__NAVUI__*/', (origen/'navegacion.html').read_text(encoding='utf-8'))
    from presentacion_f02 import render as render_defense
    html = html.replace('/*__DEFENSE_PRESENTATION__*/', render_defense())
    dashboard=(origen/'panel_corrida.html').read_text(encoding='utf-8')
    html=html.replace('/*__RUN_DASH__*/',dashboard)
    weather={}
    for path in (BASE/'data/weather').glob('*/forecast.json'):
        raw=path.read_bytes()
        data=json.loads(raw)
        hourly=data.get('hourly',{})
        if data.get('hourly_units',{}).get('time')=='unixtime':
            weather[hashlib.sha256(raw).hexdigest()]={k:hourly[k] for k in ('time','wind_speed_10m','shortwave_radiation') if k in hourly}
    study=BASE/'docs/hielo_f02/plan_8_estudiada.json'
    if not study.exists():study=BASE/'docs/hielo_f02/plan_8_250.json'
    if not study.exists():study=BASE/'docs/hielo_f02/plan_8.json'
    demo=next((r['simulation_id'] for r in json.loads(study.read_bytes())['runs'] if r['source_id']=='fv_M4_SS'),None) if study.exists() else None
    # Preferir un campo realmente disponible en este equipo al ejemplo remoto.
    local=BASE/'docs/hielo_f02/convergencia/T8_96x96x54_dt1200_fv_M4_SS.json'
    if local.exists():
        record=json.loads(local.read_bytes());folder=Path(record.get('snapshot_folder',''))
        if folder.is_dir() and folder.resolve().is_relative_to((BASE/'resultados').resolve()) and (folder/'fields.bin').is_file():
            metadata=json.loads((folder/'metadata.json').read_bytes());demo=metadata['simulation_id']
            registry=BASE/'resultados/planes_publicados.json'
            published=json.loads(registry.read_bytes()) if registry.exists() else {}
            published[demo]=dict(folder=str(folder.relative_to(BASE)),artifacts=record['artifacts'])
            registry.write_text(json.dumps(published,ensure_ascii=False),encoding='utf-8')
    html=html.replace('/*__RUN_DATA__*/',json.dumps(dict(demo=demo,weather=weather),allow_nan=False))
    html=html.replace('/*__RUN_SCRIPT__*/',(origen/'panel_corrida.js').read_text(encoding='utf-8'))
    html=html.replace('/*__COMPARE_CURVES__*/',(origen/'comparar_curvas.js').read_text(encoding='utf-8'))
    html = html.replace('/*__ICE_SCRIPT__*/', (origen/'hielo.js').read_text(encoding='utf-8'))
    html = html.replace('/*__ICE_FORM__*/', (origen/'hielo.html').read_text(encoding='utf-8'))
    html = html.replace('/*__NAVSCRIPT__*/', (origen/'navegacion.js').read_text(encoding='utf-8'))
    for marker,file in [('F02UI','comparacion_f02.html'),('F02STYLE','comparacion_f02.css'),('F02SCRIPT','comparacion_f02.js')]:
        html=html.replace('/*__'+marker+'__*/',(origen/file).read_text(encoding='utf-8'))
    decision = BASE/'docs/decision_f02/fragmento.html'
    html = html.replace('/*__DECISION_F02__*/', decision.read_text(encoding='utf-8') if decision.exists() else '<p>La comparación final de 96 × 96 × 54 está pendiente de publicación.</p>')
    html=html.replace('/*__F02_SUMMARY__*/',(origen/'resumen_planes.js').read_text(encoding='utf-8'))
    html=html.replace('/*__F02_SOURCES__*/',graficos_fuentes(BASE/'data/hydration/source_terms.txt'))
    html = html.replace('/*__IFC_DATA__*/', json.dumps(datos_ifc(BASE/'modelo_e02.ifc'), ensure_ascii=False).replace('</', '<\\/'))
    html=html.replace('/*__DESIGNSTYLE__*/',(origen/'diseno.css').read_text(encoding='utf-8'))
    html=html.replace('/*__DESIGNSCRIPT__*/',(origen/'diseno.js').read_text(encoding='utf-8'))
    destino = BASE/'panel_termico.html'
    destino.write_text(html, encoding='utf-8')
    print(destino)


if __name__ == '__main__':
    main()
