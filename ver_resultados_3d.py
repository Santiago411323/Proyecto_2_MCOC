"""Visor PyVista con corte móvil o clipping; admite captura sin ventana."""
import argparse
import json
from pathlib import Path

import numpy as np
import pyvista as pv


def visualizar(carpeta, campo=None, captura=None, clip=False):
    folder = Path(carpeta)
    if (folder / 'ultima_corrida.json').exists():
        latest = json.loads((folder / 'ultima_corrida.json').read_text(encoding='utf-8'))
        folder = folder / latest['folder'] / 'vtk'
    meta = json.loads((folder / 'manifest.json').read_text(encoding='utf-8'))
    frame = meta['peak_frame'] if campo is None else campo
    if not 0 <= frame < len(meta['frames']):
        raise ValueError('Índice de campo fuera de rango.')
    info = meta['frames'][frame]
    mesh = pv.read(folder / info['file'])
    if not mesh.n_cells:
        raise ValueError('Este campo todavía no tiene hormigón colocado.')
    plotter = pv.Plotter(off_screen=captura is not None, window_size=(1400, 950))
    plotter.set_background('#f6f8fc')
    limits = (float(mesh['T_C'].min()), float(mesh['T_C'].max()))
    if limits[0] == limits[1]:
        limits = (limits[0] - .5, limits[1] + .5)
    style = dict(scalars='T_C', cmap='turbo', clim=limits,
                 scalar_bar_args=dict(title='Temperatura [C]', vertical=True, position_x=.87))
    plotter.add_mesh(mesh, style='wireframe', color='#7b8798', opacity=.12)
    if clip:
        if captura:
            plotter.add_mesh(mesh.clip(normal='y', origin=mesh.center), **style)
        else:
            plotter.add_mesh_clip_plane(mesh, normal='y', origin=mesh.center, **style)
    else:
        plotter.add_mesh(mesh, opacity=.1, show_scalar_bar=False, **style)
        if captura:
            plotter.add_mesh(mesh.slice(normal='y', origin=mesh.center), show_edges=True, **style)
        else:
            plotter.add_mesh_slice(mesh, normal='y', origin=mesh.center, show_edges=True, **style)
    for name, color in [('nucleo', '#111111'), ('exterior', '#0d823e')]:
        point = meta['points'][name]
        match = np.flatnonzero(mesh['celda_original'] == point['celda_original'])
        if not len(match):
            continue
        temperature = float(mesh['T_C'][match[0]])
        plotter.add_point_labels([point['xyz_m']], [f'{name}: {temperature:.2f} C'],
            point_color=color, text_color=color, point_size=15, font_size=17,
            always_visible=True, shape_color='white')
    plotter.add_text(f"E11 | t = {info['time_s']/3600:.2f} h | {mesh.n_cells} voxeles activos\n"
                     + ('Clipping' if clip else 'Corte: plano Y')
                     + '\nPuntos: centros de voxel; exterior no equivale a S25',
                     position='upper_left', font_size=13, color='#182a3a')
    plotter.show_axes()
    plotter.show_grid(xtitle='X [m]', ytitle='Y [m]', ztitle='Z [m]', color='#334155', n_zlabels=3)
    plotter.view_isometric()
    plotter.camera.zoom(1.15)
    if captura:
        Path(captura).parent.mkdir(parents=True, exist_ok=True)
        plotter.screenshot(str(captura))
        plotter.close()
    else:
        plotter.show(title='THERMA E11 - corte y temperatura 3D')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('carpeta', type=Path, help='Carpeta vtk con manifest.json')
    parser.add_argument('--campo', type=int, help='Índice; por defecto campo del máximo global')
    parser.add_argument('--captura', type=Path, help='Guarda PNG sin ventana interactiva')
    parser.add_argument('--clip', action='store_true', help='Recortar el volumen en vez de cortarlo')
    args = parser.parse_args()
    visualizar(args.carpeta, args.campo, args.captura, args.clip)


if __name__ == '__main__':
    main()
