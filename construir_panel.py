"""Construye un HTML autónomo sin dependencias de red para el laboratorio."""
from pathlib import Path

BASE = Path(__file__).resolve().parent


def main():
    origen = BASE/'panel'
    html = (origen/'plantilla.html').read_text(encoding='utf-8')
    for marcador, archivo in [('STYLE', 'estilos.css'), ('SOLVER', 'solver.js'), ('APP', 'app.js')]:
        html = html.replace(f'/*__{marcador}__*/', (origen/archivo).read_text(encoding='utf-8'))
    destino = BASE/'panel_termico.html'
    destino.write_text(html, encoding='utf-8')
    print(destino)


if __name__ == '__main__':
    main()
