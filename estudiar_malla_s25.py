"""Estudio de resolución IFC/S25 desde CLI, también disponible en THERMA."""
import argparse
import json
from pathlib import Path
from ejecutar_lotes_defensa import build_catalog
from therma.lotes import preparar_config
from therma.convergencia import ejecutar_estudio


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--config',type=Path)
    p.add_argument('--resoluciones',nargs='+',type=float,default=[.5,.375,.25,.125,.05,.025])
    p.add_argument('--salida',type=Path,default=Path('resultados/convergencia_s25_ifc'))
    p.add_argument('--separacion-superficie',type=float,default=1.5)
    p.add_argument('--dias',type=float)
    args=p.parse_args()
    if args.config:config=json.loads(args.config.read_text(encoding='utf-8'))
    else:
        cat=build_catalog();config=preparar_config(cat,cat['plans'][1],cat['scenarios'][-1])
    if args.dias:config['days']=args.dias
    config['s25']=dict(method='ifc_mls',depth_m=.025,surface_spacing_m=args.separacion_superficie)
    report=ejecutar_estudio(config,args.resoluciones,args.salida,progress=lambda v:print(f'{v:.0%}',flush=True))
    print(json.dumps(report,ensure_ascii=False,indent=2))


if __name__=='__main__':main()
