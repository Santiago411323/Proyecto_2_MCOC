"""Comprueba el contrato físico NPZ -> VTK, incluyendo orientación y activación."""
import json
import xml.etree.ElementTree as ET

import numpy as np
import pytest

pv = pytest.importorskip('pyvista')
from therma.exportacion_vtk import exportar, malla_vtk


def test_roundtrip_cells_geometry_and_values(tmp_path):
    shape = (2, 3, 4)
    indices = np.indices(shape)
    T = 100*indices[0] + 10*indices[1] + indices[2]
    mask = np.ones(shape, bool)
    mask[0, 1, 2] = False
    origin, spacing = np.array([-5.1, 2.2, 7.3]), np.array([.7, 1.3, .55])
    mesh = malla_vtk(T, mask, 1+indices[2], origin, spacing)
    mesh.save(tmp_path/'field.vtu')
    read = pv.read(tmp_path/'field.vtu')
    assert read.n_cells == mask.sum()
    assert read.points.dtype == np.dtype('float64')
    assert abs(read.volume - mask.sum()*np.prod(spacing)) < 1e-10
    for xyz, value, ident, original in zip(read.cell_centers().points, read['T_C'], read['vertida_id'], read['celda_original']):
        index = tuple(np.unravel_index(original, shape, order='F'))
        assert mask[index]
        np.testing.assert_allclose(xyz, origin+(np.array(index)+.5)*spacing)
        assert value == T[index]
        assert ident == 1+index[2]


def test_series_keeps_activation_times_and_peak(tmp_path):
    shape = (2, 3, 4)
    T = np.stack([np.full(shape, value) for value in (18., 41., 30.)])
    active = np.ones_like(T, dtype=bool)
    active[0, :, :, 2:] = False
    ids = np.ones(shape, dtype=int)
    np.savez_compressed(tmp_path/'campos.npz', T_C=T, active=active, tiempo_s=[0., 3600., 7200.], pour_ids=ids)
    (tmp_path/'metadata.json').write_text(json.dumps(dict(geometry=dict(shape_xyz=list(shape), origin_m=[-1, -2, 0], spacing_m=[1, 2, 3]))))
    manifest = exportar(tmp_path)
    assert manifest['peak_frame'] == 1
    collection = ET.parse(tmp_path/'vtk'/'serie.pvd').find('Collection')
    assert [float(item.attrib['timestep']) for item in collection] == [0., 3600., 7200.]
    assert [pv.read(tmp_path/'vtk'/item.attrib['file']).n_cells for item in collection] == [12, 24, 24]
    for point in manifest['points'].values():
        index = tuple(point['index_xyz'])
        assert active[-1][index]
    exterior = manifest['points']['exterior']['index_xyz']
    assert exterior[0] == shape[0]-1
    assert manifest['points']['nucleo']['index_xyz'][2] == exterior[2]


def test_rejects_nonfinite_active_temperature():
    T = np.ones((2, 3, 4)); T[0, 1, 2] = np.nan
    with pytest.raises(ValueError, match='finita'):
        malla_vtk(T, np.ones_like(T, bool), np.ones_like(T, int), [0, 0, 0], [1, 1, 1])
