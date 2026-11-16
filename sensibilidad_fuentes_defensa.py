"""PINN versus FV manteniendo el mismo plan y físicos; NO mezcla sus pesos."""
import argparse
from pathlib import Path
from ejecutar_lotes_defensa import build_catalog
from therma.lotes import ejecutar_catalogo, write_csv, write_json


def main(output):
    rows=[]
    for method in ('fv','pinn'):
        cat=build_catalog(method)
        cat['plans']=[next(p for p in cat['plans'] if p['id']=='propuesto')]
        cat['sources']=cat['sources'][:1]
        cat['scenarios']=[dict(cat['scenarios'][0],weight='1')]
        _,records=ejecutar_catalogo(cat,output/method)
        rows.append(dict(method=method,**records[0]))
    write_csv(output/'comparacion_metodos.csv',rows)
    write_json(output/'comparacion_metodos.json',dict(rows=rows,
        scope='M1_SS, Propuesto, mismos clima, malla, rho/cp y k. Métodos distintos, no réplicas aleatorias. No se agregan probabilidades entre archivos.'))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--salida',type=Path,default=Path('resultados/defensa/sensibilidad_metodos'))
    main(p.parse_args().salida)
