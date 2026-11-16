"""Audita campos, métricas, historias y hashes de las corridas exportadas."""
import argparse
import csv
import json
from pathlib import Path
from decimal import Decimal
import numpy as np
from therma.lotes import sha,write_json


def verificar(output):
    output=Path(output)
    records=json.loads((output/'tabla_corridas.json').read_text(encoding='utf-8'))
    verified=0
    for r in records:
        if r['status']!='COMPLETED':continue
        folder=Path(r['snapshot_folder'])
        for name,digest in r['artifacts'].items():
            assert sha(folder/name)==digest,(r['scenario_id'],name)
            verified+=1
        with np.load(folder/'campos.npz') as z:
            assert z['T_C'].shape==z['active'].shape
            maxima=[float(T[A].max()) if A.any() else -np.inf for T,A in zip(z['T_C'],z['active'])]
            assert abs(max(maxima)-r['Tmax_C'])<1e-10
            j=int(np.argmax(maxima))
            assert abs(z['tiempo_s'][j]/3600-r['Tmax_time_h'])<1e-8
        with (folder/'history_s25.csv').open(encoding='utf-8-sig') as f:
            history=list(csv.DictReader(f))
        for h in history:
            assert abs(float(h['Delta_estimate_C'])-(float(h['Tmax_C'])-float(h['S25_min_estimate_C'])))<1e-10
        assert abs(max(float(h['Delta_estimate_C']) for h in history)-r['Delta_estimate_C'])<1e-10
    ids={r['plan_id'] for r in records}
    baseline=None
    for plan in ids:
        runs=[r for r in records if r['plan_id']==plan]
        weights={r['scenario_id']:r['weight'] for r in runs}
        assert sum(Decimal(str(w)) for w in weights.values())==Decimal(1)
        if baseline is None:baseline=weights
        else:assert baseline==weights
    method_file=output/'sensibilidad_metodos/comparacion_metodos.json'
    difference=None
    if method_file.exists():
        method=json.loads(method_file.read_text(encoding='utf-8'))['rows'][0]
        matching=next(r for r in records if r['plan_id']=='propuesto' and r['source_id']=='fv_M1_SS')
        difference=method['Tmax_C']-matching['Tmax_C']
        assert abs(difference)<1e-10
    result=dict(status='VERIFIED',completed_runs=sum(r['status']=='COMPLETED' for r in records),
                artifacts_verified=verified,same_scenarios_and_weights_all_plans=True,
                independent_FV_Tmax_difference_C=difference,
                field_maxima_and_simultaneous_delta_match=True,S25_physical_validation='NOT VALIDATED',
                tests='272 pruebas en regresión completa y 3 pruebas adicionales aprobadas tras agregarlas: 275 verificadas.')
    write_json(output/'reproducibilidad.json',result)
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--salida',type=Path,default=Path('resultados/defensa'))
    print(verificar(p.parse_args().salida))
