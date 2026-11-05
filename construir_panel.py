"""Genera THERMA; el visor WebGL carga dependencias locales desde el servidor."""
from pathlib import Path
import json
from panel.exportar_ifc import datos_ifc

BASE = Path(__file__).resolve().parent


def main():
    origen = BASE/'panel'
    html = (origen/'plantilla.html').read_text(encoding='utf-8')
    for marcador, archivo in [('STYLE', 'estilos.css'), ('SOLVER', 'solver.js'), ('API', 'api.js'), ('APP', 'app.js'), ('FOUNDATION', 'fundacion.js'), ('VIEWDATA', 'visordatos.js'), ('VIEWUI', 'visor.html'), ('VIEWSTYLE', 'visor.css'), ('INTELLIGENCE', 'inteligencia.js'), ('RESEARCHUI', 'investigacion.html'), ('RESEARCHSTYLE', 'investigacion.css'), ('CONSTRUCTIONUI', 'construccion.html'), ('CONSTRUCTIONSCRIPT', 'construccion.js'), ('ENVIRONMENTUI', 'entorno.html'), ('ENVIRONMENTSCRIPT', 'entorno.js'), ('EQUATIONUI', 'ecuaciones.html'), ('EQUATIONSTYLE', 'ecuaciones.css'), ('EQUATIONMODEL', 'ecuaciones_modelo.js'), ('EQUATIONSCRIPT', 'ecuaciones.js'), ('FORMWORKUI', 'moldaje.html'), ('FORMWORKMATH', 'moldaje_modelo.js'), ('FORMWORKSCRIPT', 'moldaje_ui.js'), ('COREEXTERIOR', 'nucleo_exterior.js')]:
        html = html.replace(f'/*__{marcador}__*/', (origen/archivo).read_text(encoding='utf-8'))
    html = html.replace('/*__IFC_DATA__*/', json.dumps(datos_ifc(BASE/'modelo_e02.ifc'), ensure_ascii=False).replace('</', '<\\/'))
    destino = BASE/'panel_termico.html'
    destino.write_text(html, encoding='utf-8')
    print(destino)


if __name__ == '__main__':
    main()
