"""Conecta las corridas ya ejecutadas con el catálogo HTML, sin recalcular."""
import copy
import json
from therma.hielo import ROOT
from therma.lotes import write_json
from estudiar_mallas_hielo import OUT


def main():
    catalog=json.loads((ROOT/'docs/cierre_f02/evidencia/catalogo_congelado.json').read_bytes())
    study=json.loads((ROOT/'docs/hielo_f02/estudio_mallas.json').read_bytes())
    for temperature in (8,12):
        report=copy.deepcopy(json.loads((ROOT/f'docs/hielo_f02/plan_{temperature}.json').read_bytes()))
        report['runs']=[]
        for s in catalog['scenarios']:
            path=OUT/f"T{temperature}_90x90x48_dt1200_{s['source_id']}.json"
            r=json.loads(path.read_bytes())
            if r['status']!='COMPLETED' or not r['numerical_checks'] or not r['horizon_captured'] or r['missing_points_max']:
                raise ValueError(f'Corrida incompleta: {path.name}')
            r.pop('snapshot_folder',None)
            r.update(scenario_id=s['id'],climate_id=s['climate_id'],weight=s['weight'])
            report['runs'].append(r)
        report['mesh_study']=study
        report['selected_shape']=[90,90,48]
        report['selection_note']='Resolución final del estudio de sensibilidad, con cobertura de los puntos S25. No valida el modelo físico ni garantiza error absoluto.'
        write_json(ROOT/f'docs/hielo_f02/plan_{temperature}_estudiada.json',report)
        print('Publicado',temperature,flush=True)


if __name__=='__main__':
    main()
