"""Repite el plan Meteored de diez vertidas variando sus protecciones exteriores."""
import argparse
import json
from pathlib import Path
from shutil import copy2
from uuid import uuid4

from therma.construccion import ejecutar_construccion, validar_construccion
from therma.lotes import write_json
from therma.s25_ifc import ObservadorIFC
from therma.superficies_ifc import SuperficiesIFC
from voxelizar import cargar_geometria


def run(reference, formwork):
    saved = json.loads((reference / 'metadata.json').read_bytes())
    receipt = json.loads((reference / 'ensayo_pronostico.json').read_bytes())
    config = saved['config']
    if config['n'] != [96, 96, 54] or receipt['plan_pours'] != 10:
        raise ValueError('Se requiere el plan guardado de diez vertidas en la malla común.')
    validar_construccion(config)
    for face in config['faces']:
        face['R'] = 0.
    if not formwork:
        config.pop('formwork', None)
    simulation_id = uuid4().hex
    folder = reference.parent / simulation_id
    folder.mkdir()
    ifc = saved['provenance']['ifc']
    path = folder / Path(ifc['archivo']).name
    copy2(reference / path.name, path)
    case = 'moldaje' if formwork else 'sin_protecciones'
    print(case, simulation_id, flush=True)
    spacing = config['s25']['surface_spacing_m']
    surfaces = SuperficiesIFC(cargar_geometria(path), spacing, max_points=160000)
    inspector = ObservadorIFC(config, path, geometry=surfaces)
    milestone = -1

    def progress(value):
        nonlocal milestone
        step = int(10 * value)
        if step > milestone:
            print(case, step * 10, '%', flush=True)
            milestone = step

    meta = ejecutar_construccion(config, simulation_id, folder, ifc['geometry'], progress, inspector)
    meta['provenance']['ifc'] = ifc
    inspector.export(folder, meta)
    peak = meta['s25_ifc']['peak_estimate']
    write_json(folder / 'ensayo_pronostico.json', dict(
        receipt, simulation_id=simulation_id, eps_mm=0, additional_basal_R_m2K_W=0,
        protection_control=case, control_reference=saved['simulation_id'],
        Tmax_C=meta['metrics']['maxField'], DeltaT_S25_estimate_C=peak['DeltaT_estimate_C'],
        S25_validation=meta['s25_ifc']['validation']))
    print(case, 'COMPLETED', simulation_id, meta['metrics']['maxField'], peak['DeltaT_estimate_C'], flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('reference', type=Path)
    parser.add_argument('--formwork', action='store_true')
    args = parser.parse_args()
    run(args.reference, args.formwork)
