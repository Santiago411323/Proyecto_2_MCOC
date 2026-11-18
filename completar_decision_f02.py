"""Completa los seis planes de decisión en la malla común (24 escenarios)."""
from concurrent.futures import ProcessPoolExecutor
from itertools import product
from estudiar_mallas_hielo import thermal
from estudiar_malla_comun import task


def run(case):
    plan, source = case
    if isinstance(plan,int):
        result=thermal([[96, 96, 54]], plan, 1200, [source])[0]
    else:
        result=task((plan,[96,96,54],1200,source))
    if result['status']!='COMPLETED':
        raise RuntimeError(f"{plan} / {source}: {result.get('error')}")
    return result['simulation_id']


if __name__ == '__main__':
    cases = product((8,12,'continua','propuesto','rapido','lento'), [f'fv_M{i}_SS' for i in range(1, 5)])
    with ProcessPoolExecutor(max_workers=4) as pool:
        for ident in pool.map(run, cases):
            print(ident, flush=True)
