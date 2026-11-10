"""Descarga/inspecciona snapshots sin sobrescribirlos. Sin dependencias nuevas."""
import argparse
from pathlib import Path
import json
from therma.meteorologia import descargar,cargar_snapshot,configuracion_snapshot,ForzanteAire,instante

ROOT=Path(__file__).resolve().parent


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    sub=parser.add_subparsers(dest='action',required=True)
    d=sub.add_parser('descargar');d.add_argument('--sitio',type=Path,default=ROOT/'sitio.json')
    d.add_argument('--salida',type=Path,default=ROOT/'data'/'weather');d.add_argument('--dias',type=int,default=16)
    i=sub.add_parser('inspeccionar');i.add_argument('snapshot',type=Path)
    i.add_argument('--inicio',help='ISO 8601 con zona horaria');i.add_argument('--dias',type=float,default=14.)
    args=parser.parse_args()
    try:
        if args.action=='descargar':
            site=json.loads(args.sitio.read_text(encoding='utf-8'))
            folder=descargar(args.salida,site['latitud'],site['longitud'],args.dias)
        else:folder=args.snapshot
        _,_,meta=cargar_snapshot(folder)
        print(json.dumps(dict(snapshot=str(folder),metadata=meta),indent=2,ensure_ascii=False))
        if args.action=='inspeccionar' and args.inicio:
            config=configuracion_snapshot(folder,args.inicio)
            ForzanteAire(config,args.dias*86400)
            print('COBERTURA COMPLETA: puede usarse sin extrapolar.')
    except (OSError,ValueError,KeyError) as error:parser.error(str(error))


if __name__=='__main__':main()
