"""Caso didáctico reproducible: IFC + tres vertidas + hidratación no calibrada."""
import argparse
import json
from pathlib import Path
import uuid
from therma.ejecutar import ejecutar


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--intervalo-h',type=float,default=24.)
    parser.add_argument('--dias',type=float,default=14.)
    parser.add_argument('--malla',type=int,choices=[0,1],default=0)
    parser.add_argument('--theta-inf',type=float,default=40.)
    parser.add_argument('--tau-h',type=float,default=24.)
    args=parser.parse_args();ident=uuid.uuid4().hex
    output=Path(__file__).resolve().parent/'resultados'/'servidor_therma'/ident
    p=dict(geometry='foundation',meshIndex=args.malla,source='none',calibrate=False,days=args.dias,
        faces=[dict(type='R',temp=20.,h=10.,R=0.,flux=0.) for _ in range(6)],
        construction=dict(model='exponential_adiabatic',parameter_source='Hipótesis didáctica declarada en CLI; sin ensayo de mezcla real.',
            pours=[dict(id=i+1,start_h=i*args.intervalo_h,placement_C=18.,theta_inf_C=args.theta_inf,tau_h=args.tau_h) for i in range(3)]))
    meta=ejecutar(p,ident,output)
    print(json.dumps(dict(run_id=ident,output=str(output),Tmax_C=meta['metrics']['maxField'],
        peak_h=meta['metrics']['global_peak_time_s']/3600,residual_relative=meta['metrics']['energy_residual_relative'],
        runtime_s=meta['metrics']['runtime_s'],events=meta['construction']['events']),indent=2,ensure_ascii=False))


if __name__=='__main__':main()
