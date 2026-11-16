"""Refina una selección ya explorada, conservando versión física y clima."""
import argparse,copy,json
from pathlib import Path
from therma.exploracion import execute,plots
from therma.lotes import write_json

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--base',type=Path,default=Path('resultados/exploracion_constructiva'));p.add_argument('--salida',type=Path,default=Path('resultados/exploracion_refinada'));p.add_argument('--paso',type=float,default=.25);p.add_argument('--planes',nargs='+');a=p.parse_args()
    cat=json.loads((a.base/'catalogo_congelado.json').read_text(encoding='utf-8'))
    # Comparación prevista: referencia, menor Tcol, y dos alternativas rápidas.
    select=a.planes or ['propuesto','colocacion12','continua','combinado','eps50']
    plans=[copy.deepcopy(v) for v in cat['plans'] if v['id'] in select]
    fastcold=copy.deepcopy(next(v for v in cat['plans'] if v['id']=='espera0'))
    fastcold.update(id='rapido_frio',name='Sin espera, Tcol12, sin EPS',placement_C=12.,family='adaptive_refinement')
    if not a.planes:plans.append(fastcold)
    cat['plans']=plans
    for key in ('engine_fingerprint','grid','planned_runs'):cat.pop(key,None)
    cat['adaptive_rationale']='Compare identical candidates at 250 mm and fastest cold case without EPS; no climate or curve changes. No official winner.'
    execute(cat,a.salida,a.paso);plots(a.salida)
