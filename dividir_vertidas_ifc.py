"""Subdivide el IFC base en etapas horizontales conservando su envolvente."""
import json
from pathlib import Path

import ifcopenshell
import ifcopenshell.api
import numpy as np

from completar_modelo import completar
from panel.exportar_ifc import datos_ifc
from therma.construccion import ejecutar_construccion, validar_construccion
from therma.ejecutar import ROOT, validar
from therma.s25_ifc import ObservadorIFC
from therma.superficies_ifc import SuperficiesIFC
from voxelizar import cargar_geometria


def split_triangles(triangles, level):
    """Recorta los triángulos en ambos semiespacios y cierra la sección."""
    sections = [[], []]
    rim = []
    for triangle in triangles:
        for side, output in zip((1, -1), sections):
            polygon = []
            for a, b in zip(triangle, np.roll(triangle, -1, axis=0)):
                a_inside = side * (level - a[2]) > 0
                b_inside = side * (level - b[2]) > 0
                if a_inside:
                    polygon.append(a)
                if a_inside != b_inside:
                    crossing = a + (b - a) * ((level - a[2]) / (b[2] - a[2]))
                    crossing[2] = level
                    polygon.append(crossing)
                    if side == 1:
                        rim.append(crossing)
            output.extend([polygon[0], polygon[i], polygon[i+1]]
                          for i in range(1, len(polygon)-1))
    edge = np.unique(np.round(rim, 10), axis=0)
    center = edge.mean(axis=0)
    offsets = edge - center
    edge = edge[np.argsort(np.arctan2(offsets[:, 1], offsets[:, 0]))]
    for a, b in zip(edge, np.roll(edge, -1, axis=0)):
        sections[0].append([center, a, b])
        sections[1].append([center, b, a])
    return sections


def write_ifc(path, parts_per_solid, spacing_z, origin_z):
    base = ROOT / 'modelo_e02.ifc'
    model = ifcopenshell.open(str(ROOT / 'modelo_inicial.ifc'))
    body = next(c for c in model.by_type('IfcGeometricRepresentationSubContext')
                if c.ContextIdentifier == 'Body' and c.ContextType == 'Model')
    storey = model.by_type('IfcBuildingStorey')[0]
    ident = 0
    for solid, parts in zip(sorted(cargar_geometria(base), key=lambda s: s['VertidaID']), parts_per_solid, strict=True):
        triangles = solid['triangulos']
        z = triangles[:, :, 2]
        levels = np.linspace(z.min(), z.max(), parts + 1)[1:-1]
        cuts = np.round((levels - origin_z)/spacing_z) * spacing_z + origin_z
        sections = []
        for level in cuts:
            if np.any(np.isclose(triangles[:, :, 2], level, rtol=0, atol=1e-8)):
                raise ValueError('El plano de corte atraviesa vértices existentes.')
            low, high = split_triangles(triangles, level)
            sections.append(low)
            triangles = np.asarray(high)
        sections.append(triangles)
        for section in sections:
            ident += 1
            footing = ifcopenshell.api.run('root.create_entity', model, ifc_class='IfcFooting',
                                           name=f'Vertida_{ident:02}')
            footing.Description = f'Subdivisión geométrica del elemento IFC {solid["guid"]}'
            vertices, indices = np.unique(np.round(np.asarray(section).reshape(-1, 3), 10),
                                          axis=0, return_inverse=True)
            faces = indices.reshape(-1, 3).tolist()
            if any(len(set(face)) != 3 for face in faces):
                raise ValueError('La subdivisión produjo una cara degenerada.')
            ifcopenshell.api.run('spatial.assign_container', model, products=[footing], relating_structure=storey)
            rep = ifcopenshell.api.run('geometry.add_mesh_representation', model, context=body,
                                      vertices=[vertices.tolist()], faces=[faces])
            ifcopenshell.api.run('geometry.assign_representation', model, product=footing, representation=rep)
            ifcopenshell.api.run('geometry.edit_object_placement', model, product=footing, matrix=np.eye(4))
    completar(model).write(str(path))


def ejecutar_subdividido(config, ident, folder, reference, wait_h, rate, progress, count):
    if not np.isfinite(wait_h) or wait_h < 0:
        raise ValueError('La espera entre etapas debe ser finita y no negativa.')
    p = validar(config)
    parts = {6:(2,2,2),10:(4,3,3),12:(4,4,4)}[count]
    path = folder / f'vertidas_{count}.ifc'
    write_ifc(path, parts, p['L'][2]/p['n'][2], p['origin'][2])
    geometry = datos_ifc(path, formas=[p['n']])
    old = np.asarray(p['mask'])
    new = np.asarray(geometry['mallas'][0]['ids'])
    parents = np.repeat(np.arange(1,4), parts)
    if not np.array_equal(old, np.r_[0,parents][new]):
        raise ValueError('El IFC derivado modifica la ocupación de la geometría de referencia.')
    if len(geometry['capas']) != count or not np.array_equal(np.unique(new[new>0]), np.arange(1,count+1)):
        raise ValueError('La geometría no contiene todas las etapas de colocación.')
    print(f'{count} vertidas: ocupación de la malla verificada.', flush=True)
    p['mask'] = new.tolist()
    schedule = []
    start = 0.
    for layer in geometry['capas']:
        volume = layer['volumen_m3']
        end = start + volume / rate
        schedule.append(dict(id=layer['id'], start_h=start, end_h=end, volume_m3=volume))
        start = end + wait_h
    p['construction']['pours'] = [dict(id=o['id'], start_h=o['start_h'], placement_C=reference) for o in schedule]
    validar_construccion(p)
    # Los planos intermedios agregan caras al IFC. Conservar la separación
    # de muestreo del caso de una vertida dentro de este ejecutor local.
    surfaces = SuperficiesIFC(cargar_geometria(path), p['s25']['surface_spacing_m'], max_points=160000)
    inspector = ObservadorIFC(p, path, geometry=surfaces)
    meta = ejecutar_construccion(p, ident, folder, geometry, progress, inspector)
    meta['provenance']['ifc'] = dict(archivo=path.name, sha256=geometry['sha256'], geometry=geometry)
    (folder/'metadata.json').write_text(json.dumps(meta, ensure_ascii=False, allow_nan=False), encoding='utf-8')
    inspector.export(folder, meta)
    return meta, schedule
