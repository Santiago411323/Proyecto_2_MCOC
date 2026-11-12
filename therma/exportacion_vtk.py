"""Exportación celular VTK: conserva ejes, máscara activa, vertidas y tiempos."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET

import numpy as np


def malla_vtk(temperatura, activo, vertidas, origen, paso):
    import pyvista as pv

    T = np.asarray(temperatura)
    mask = np.asarray(activo, dtype=bool)
    ids = np.asarray(vertidas)
    origin = np.asarray(origen, dtype=float)
    spacing = np.asarray(paso, dtype=float)
    if T.ndim != 3 or mask.shape != T.shape or ids.shape != T.shape:
        raise ValueError('Temperatura, máscara y vertidas deben tener la misma forma 3D.')
    if origin.shape != (3,) or spacing.shape != (3,) or not np.isfinite(origin).all() or not np.isfinite(spacing).all() or np.any(spacing <= 0):
        raise ValueError('Origen finito y tres tamaños de celda positivos requeridos.')
    if not np.isfinite(T[mask]).all() or np.any(ids[mask] <= 0):
        raise ValueError('Cada celda activa requiere temperatura finita e ID de vertida positivo.')
    # VTK enumera celdas con x más rápido; numpy [x,y,z] exige orden Fortran.
    grid = pv.ImageData(dimensions=np.asarray(T.shape) + 1, spacing=spacing, origin=origin)
    grid.cell_data['T_C'] = T.ravel(order='F')
    grid.cell_data['vertida_id'] = ids.ravel(order='F')
    grid.cell_data['celda_original'] = np.arange(T.size, dtype=np.int64)
    mesh = grid.extract_cells(np.flatnonzero(mask.ravel(order='F')))
    # vtkExtractCells convierte puntos implícitos de ImageData a float32.
    # Recuperar las coordenadas originales evita redondear geometría/volumen.
    mesh.points = grid.points[mesh.point_data['vtkOriginalPointIds']]
    return mesh


def puntos_fijos(activo, origen, paso):
    """Núcleo cercano al centro geométrico y exterior lateral a igual cota/vertida."""
    indices = np.argwhere(activo)
    if not len(indices):
        raise ValueError('No hay celdas activas para identificar puntos.')
    origin, spacing = np.asarray(origen), np.asarray(paso)
    xyz = origin + (indices + .5) * spacing
    center = (xyz.min(axis=0) + xyz.max(axis=0)) / 2
    core = indices[np.argmin(np.sum((xyz - center)**2, axis=1))]
    # Sólo exterior lateral: celda con alguna cara x/y expuesta y misma cota.
    padded = np.pad(activo, 1)
    lateral = activo & ~(padded[:-2, 1:-1, 1:-1] & padded[2:, 1:-1, 1:-1]
                          & padded[1:-1, :-2, 1:-1] & padded[1:-1, 2:, 1:-1])
    candidates = np.argwhere(lateral & (np.indices(activo.shape)[2] == core[2]))
    target = origin + (core + .5) * spacing
    target[0] = xyz[:, 0].max()
    coords = origin + (candidates + .5) * spacing
    surface = candidates[np.argmin(np.sum((coords - target)**2, axis=1))]
    return {name: dict(index_xyz=index.tolist(), xyz_m=(origin + (index + .5) * spacing).tolist(),
                      celda_original=int(np.ravel_multi_index(tuple(index), activo.shape, order='F')))
            for name, index in [('nucleo', core), ('exterior', surface)]}


def exportar(carpeta, salida=None):
    folder = Path(carpeta)
    destination = Path(salida) if salida else folder / 'vtk'
    metadata = json.loads((folder / 'metadata.json').read_text(encoding='utf-8'))
    geometry = metadata['geometry']
    with np.load(folder / 'campos.npz', allow_pickle=False) as data:
        T, active, times, ids = (data[k] for k in ('T_C', 'active', 'tiempo_s', 'pour_ids'))
    if T.ndim != 4 or active.shape != T.shape or times.shape != (len(T),) or len(T) == 0:
        raise ValueError('Serie de campos/tiempos incompatible.')
    if not np.isfinite(times).all() or np.any(np.diff(times) <= 0):
        raise ValueError('Tiempos finitos y estrictamente crecientes requeridos.')
    if list(T.shape[1:]) != geometry['shape_xyz']:
        raise ValueError('La forma del campo no coincide con la metadata.')
    destination.mkdir(parents=True, exist_ok=True)
    collection = ET.Element('VTKFile', type='Collection', version='0.1', byte_order='LittleEndian')
    datasets = ET.SubElement(collection, 'Collection')
    frames = []
    for i, time_s in enumerate(times):
        mesh = malla_vtk(T[i], active[i], ids, geometry['origin_m'], geometry['spacing_m'])
        mesh.field_data['tiempo_s'] = np.array([time_s])
        filename = f'campo_{i:03d}.vtu'
        mesh.save(destination / filename)
        ET.SubElement(datasets, 'DataSet', timestep=format(float(time_s), '.17g'), group='', part='0', file=filename)
        frames.append(dict(file=filename, time_s=float(time_s), active_cells=int(active[i].sum()),
                           volume_m3=float(active[i].sum() * np.prod(geometry['spacing_m']))))
    ET.indent(collection)
    ET.ElementTree(collection).write(destination / 'serie.pvd', encoding='utf-8', xml_declaration=True)
    peak = int(np.argmax([np.max(field[mask]) if mask.any() else -np.inf for field, mask in zip(T, active)]))
    manifest = dict(schema_version=1, created_at_utc=datetime.now(timezone.utc).isoformat(),
        source_npz_sha256=hashlib.sha256((folder / 'campos.npz').read_bytes()).hexdigest(),
        source_metadata_sha256=hashlib.sha256((folder / 'metadata.json').read_bytes()).hexdigest(),
        weather_sha256=metadata.get('weather', {}).get('provenance', {}).get('raw_sha256'),
        temperature_units='degC', length_units='m', time_units='s', association='cell_data',
        cell_order='x fastest; numpy ravel(order=F)', exported_cells='active concrete only',
        geometry=geometry, peak_frame=peak, frames=frames,
        points=puntos_fijos(active[-1], geometry['origin_m'], geometry['spacing_m']),
        point_note='Centros de voxeles fijos; exterior lateral a igual cota. No es temperatura exacta de cara ni a 25 mm.')
    (destination / 'manifest.json').write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding='utf-8')
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('carpeta', type=Path, help='Carpeta con campos.npz y metadata.json')
    parser.add_argument('--salida', type=Path)
    args = parser.parse_args()
    manifest = exportar(args.carpeta, args.salida)
    print(f"Exportados {len(manifest['frames'])} campos y serie.pvd")


if __name__ == '__main__':
    main()
