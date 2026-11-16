"""Prototipo de cierre unilateral Robin para stencils coplanares.
NO se aplica al IFC: necesita frontera físicamente consistente, hoy staircase.
"""
import argparse,math
from pathlib import Path
import numpy as np
from therma.lotes import write_csv,write_json


def reconstruir_robin(point,centers,values,outward,k,h,air,external_R=0.,depth=.025):
    p=np.asarray(point,float);x=np.asarray(centers,float);n=np.asarray(outward,float);n=n/np.linalg.norm(n)
    if k<=0 or h<=0 or external_R<0:raise ValueError('Propiedades positivas y resistencia no negativa.')
    H=1/(external_R+1/h)
    # T=a+b.(x-p), Ts=a+depth*b.n, -k*b.n=H*(Ts-air).
    C=np.r_[H,(k+H*depth)*n][None,:];rhs=H*air
    particular=C[0]*rhs/(C@C.T).item()
    Z=np.linalg.svd(C,full_matrices=True)[2][1:].T
    A=np.c_[np.ones(len(x)),x-p];w=1/np.sqrt(1+np.sum((x-p)**2,axis=1))
    B=(A@Z)*w[:,None]
    if np.linalg.matrix_rank(B)!=3:raise ValueError('Ni el cierre Robin determina un ajuste afín único.')
    coeff=particular+Z@np.linalg.lstsq(B,(np.asarray(values)-A@particular)*w,rcond=None)[0]
    return dict(S25_C=float(coeff[0]),fit_RMSE_C=float(np.sqrt(np.mean((A@coeff-values)**2))),boundary_constraint_residual_W_m2=float((C@coeff)[0]-rhs),condition=float(np.linalg.cond(B)))


def referencias():
    rows=[]
    for slope in (0.,.2):
        n=np.array([slope,0,-1.]);n/=np.linalg.norm(n);point=-.025*n
        for layer in (.25,.125,.0625):
            xy=np.stack(np.meshgrid(np.linspace(-.3,.3,4),np.linspace(-.3,.3,4),indexing='ij'),axis=-1).reshape(-1,2)
            centers=np.c_[xy,np.full(len(xy),layer/2)]
            distance=-centers@n;k=2.;h=10.;q=10.;air=20.;R=.133333333333
            truth=air+q*(R+1/h)+q*.025/k
            values=air+q*(R+1/h)+q*distance/k
            r=reconstruir_robin(point,centers,values,n,k,h,air,R)
            rows.append(dict(case='inclined_linear' if slope else 'flat_linear',cell_size_m=layer,reference_C=truth,**r,error_C=abs(r['S25_C']-truth),scope='Known linear field, coplanar centers; boundary closure exact. Not foundation validation.'))
    lo,hi=0.,math.pi
    for _ in range(70):
        mu=(lo+hi)/2
        if mu*math.tan(mu/2)>1:hi=mu
        else:lo=mu
    mu=(lo+hi)/2;t=.01
    exact=lambda x:20+5*np.cos(mu*(x-.5))*np.exp(-mu*mu*t)
    truth=float(exact(.025))
    for step in (.5,.25,.125,.0625):
        yz=np.stack(np.meshgrid(np.linspace(.2,.8,4),np.linspace(.2,.8,4),indexing='ij'),axis=-1).reshape(-1,2)
        centers=np.c_[np.full(len(yz),step/2),yz]
        r=reconstruir_robin([.025,.5,.5],centers,exact(centers[:,0]),[-1,0,0],1.,1.,20.)
        rows.append(dict(case='transient_Robin_exact',cell_size_m=step,reference_C=truth,**r,error_C=abs(r['S25_C']-truth),scope='Single plane + exact Robin constraint; linear truncation quantified, no FV field error.'))
    return rows

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--salida',type=Path,default=Path('resultados/exploracion_constructiva/validacion_en_curso'));a=p.parse_args();r=referencias();write_csv(a.salida/'cierre_robin_coplanar.csv',r);write_json(a.salida/'estado.json',dict(status='PROTOTYPE_NOT_IN_IFC_SOLVER',rows=r,limitations='Boundary closure must match actual geometry/fluxes before using on unknown IFC points. No temperature filling performed.'))
    print(r)

