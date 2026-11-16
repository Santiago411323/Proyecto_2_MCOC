"""Prueba analítica transitoria de la reconstrucción S25, SIN certificar el IFC."""
import argparse
from pathlib import Path
import numpy as np
from termico_cartesiano import TermicoCartesiano
from therma.s25 import reconstruir
from therma.lotes import write_csv, write_json


def verificar(output):
    rows=[]
    for n in (4,8,16):
        m=TermicoCartesiano((n,),(1.,),k=1.,rho=1.,cp=1.,bordes={s:dict(tipo='dirichlet',temperatura_C=20.) for s in ('x-','x+')})
        x=(np.arange(n)+.5)/n
        t=.03
        result=m.resolver(20+10*np.sin(np.pi*x),t,.2*m.dt_max)
        center=float(result['T'][0])
        estimate=float(reconstruir(center,20.,0.,1.,1/n))
        exact=20+10*np.sin(np.pi*.025)*np.exp(-np.pi**2*t)
        profile_only=float(reconstruir(20+10*np.sin(np.pi*x[0])*np.exp(-np.pi**2*t),20.,0.,1.,1/n))
        rows.append(dict(n=n,dx_m=1/n,time_s=t,S25_estimate_C=estimate,S25_exact_C=exact,
                         absolute_error_C=abs(estimate-exact),reconstruction_only_error_C=abs(profile_only-exact)))
    write_csv(output/'analitico_s25.csv',rows)
    write_json(output/'validacion_s25.json',dict(status='NOT VALIDATED FOR IFC',analytical_rows=rows,
        scope='Difusión 1D sinusoidal, Dirichlet, alpha=1. No valida esquinas, caras escalonadas ni cinética de fundación.',
        warning='Error de dos mallas no es cota garantizada; no se habilita cumplimiento conjunto.'))
    return rows


def verificar_robin(output):
    # Autovalor exacto para cos(mu*(x-.5)); mu*tan(mu/2)=h/k.
    h=4.;k=1.;lo=0.;hi=np.pi-1e-12
    for _ in range(80):
        mid=(lo+hi)/2
        if mid*np.tan(mid/2)>h/k:hi=mid
        else:lo=mid
    mu=(lo+hi)/2;t=.03
    exact=20+10*np.cos(mu*(.025-.5))*np.exp(-mu*mu*t)
    rows=[]
    for n in (4,8,16):
        m=TermicoCartesiano((n,),(1.,),k=k,rho=1.,cp=1.,bordes={s:dict(tipo='robin',temperatura_C=20.,h_W_m2K=h) for s in ('x-','x+')})
        x=(np.arange(n)+.5)/n
        result=m.resolver(20+10*np.cos(mu*(x-.5)),t,.2*m.dt_max)
        value=float(reconstruir(result['T'][0],20.,1/h,k,1/n))
        rows.append(dict(n=n,dx_m=1/n,S25_estimate_C=value,S25_exact_C=float(exact),absolute_error_C=abs(value-exact)))
    write_csv(output/'analitico_robin_s25.csv',rows)
    write_json(output/'validacion_robin_s25.json',dict(status='VERIFIED_ON_1D_ROBIN_MODE_ONLY',mu=float(mu),rows=rows,
        scope='Autofunción transitoria Robin exacta; no certifica S25 en geometría IFC 3D.'))
    return rows


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--salida',type=Path,default=Path('resultados/defensa/verificacion_s25'))
    args=p.parse_args();print(verificar(args.salida));print(verificar_robin(args.salida))
