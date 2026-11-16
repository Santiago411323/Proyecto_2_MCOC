"""Búsqueda exploratoria acotada con el gestor de lotes oficial y S25 IFC."""
import argparse,json
from pathlib import Path
from therma.exploracion import catalogo,execute,plots
from therma.lotes import write_json

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--salida',type=Path,default=Path('resultados/exploracion_constructiva'));p.add_argument('--opciones',type=Path);p.add_argument('--catalogo',type=Path);p.add_argument('--paso',type=float,default=.5);p.add_argument('--planes',nargs='+');p.add_argument('--piloto',action='store_true');p.add_argument('--preparar',action='store_true');a=p.parse_args()
    cat=json.loads(a.catalogo.read_text(encoding='utf-8')) if a.catalogo else catalogo(json.loads(a.opciones.read_text(encoding='utf-8')) if a.opciones else None)
    for key in ('engine_fingerprint','grid','planned_runs'):cat.pop(key,None)
    if a.preparar:write_json(a.salida/'catalogo_preparado.json',cat);print('Preparados',len(cat['plans']),'planes x',len(cat['scenarios']),'escenarios');return
    execute(cat,a.salida,a.paso,a.planes,a.piloto);plots(a.salida)
if __name__=='__main__':main()
