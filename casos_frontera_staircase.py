"""Referencia independiente: plano Robin exacto vs frontera FV escalonada.

Sólo benchmark: usa paso() oficial y datos Dirichlet analíticos en caras lejanas.
La variante de área corregida NO modifica la fundación ni sus parámetros.
"""
import argparse
from pathlib import Path
import math
import numpy as np
from termico_cartesiano import TermicoCartesiano
from therma.reconstruccion_s25 import Reconstruccion
from therma.lotes import write_json,write_csv


def referencia_plano(n,inclined=True,area_corrected=False):
    L=2.;h=L/n;k=1.;conv=4.;q=10.;ambient=20.;surface=ambient+q/conv
    normal=np.array([1.,1.])/np.sqrt(2) if inclined else np.array([1.,0.])
    c=1.037/np.sqrt(2) if inclined else .5
    x,y=np.meshgrid((np.arange(n)+.5)*h,(np.arange(n)+.5)*h,indexing='ij')
    distance=normal[0]*x+normal[1]*y-c;active=distance>0
    m=TermicoCartesiano((n,n),(L,L),k=k,rho=1.,cp=1.,activo=active)
    exact=surface+q*distance/k
    regions=[];air_faces=0
    for axis in range(2):
        for side in (-1,1):
            neighbor=np.zeros_like(active);lo=[slice(None)]*2;hi=lo.copy();lo[axis]=slice(None,-1);hi[axis]=slice(1,None);lo,hi=tuple(lo),tuple(hi)
            if side>0:neighbor[lo]=active[hi]
            else:neighbor[hi]=active[lo]
            exposed=active&~neighbor;far=np.zeros_like(active);edge=[slice(None)]*2;edge[axis]=-1 if side>0 else 0;far[tuple(edge)]=True
            air=exposed&~far;far=exposed&far;air_faces+=int(air.sum())
            face_distance=distance+normal[axis]*side*h/2
            regions.append((far,air,surface+q*face_distance/k))
    true_area=1.037*np.sqrt(2) if inclined else L
    staircase_area=air_faces*h;correction=true_area/staircase_area if area_corrected else 1.
    Gair=np.zeros_like(exact);Pair=np.zeros_like(exact)
    for far,air,Tfar in regions:
        G=2*k*h/h*far+h/(h/(2*k)+1/conv)*correction*air
        P=2*k*h/h*Tfar*far+h/(h/(2*k)+1/conv)*correction*ambient*air
        m.G_borde+=G;m.P_borde_constante+=P;m.suma_G+=G
        Gair+=h/(h/(2*k)+1/conv)*correction*air;Pair+=h/(h/(2*k)+1/conv)*correction*ambient*air
    m.dt_max=float(np.min(m.capacidad[active]/m.suma_G[active]));dt=.7*m.dt_max
    T=np.where(active,exact,0.);E0=m.energia(T);net=0.;t=0.;steps=0;rate=float('inf')
    while t<8.:
        step=min(dt,8.-t)
        P=float(np.sum((m.P_borde_constante-m.G_borde*T)*active))
        T=m.paso(T,step);net+=step*P;t+=step;steps+=1
        if steps%100==0:
            rate=float(np.max(np.abs(m.potencias(T)[active]/m.capacidad[active])))
            if rate<1e-5:break
    point2=np.array([1.037/2,1.037/2])+normal*.025 if inclined else np.array([.525,1.])
    points=np.r_[point2,1.][None,:]
    T3=np.repeat(T[:,:,None],4,axis=2);mask=np.repeat(active[:,:,None],4,axis=2)
    R=Reconstruccion(points,mask,[0,0,0],[h,h,.5]);value=float(R.evaluate(T3)[0])
    ideal=np.repeat(exact[:,:,None],4,axis=2)
    recon_only=float(R.evaluate(ideal)[0])-(surface+q*.025/k)
    return dict(n=n,spacing_m=h,inclined=inclined,area_corrected=area_corrected,
                physical_h_W_m2K=conv,true_area_m2=true_area,staircase_area_m2=staircase_area,
                staircase_area_ratio=staircase_area/true_area,S25_exact_C=surface+q*.025/k,S25_numerical_C=value,
                total_error_C=abs(value-(surface+q*.025/k)),reconstruction_only_error_C=abs(recon_only),
                air_heat_out_W=float(np.sum((Gair*T-Pair)*active)),true_heat_out_W=q*true_area,
                steady_residual_K_s=rate,time_s=t,steps=steps,energy_residual_J=float(m.energia(T)-E0-net))


def gradiente_pronunciado():
    rows=[];width=.05
    for n in (4,8,16,32):
        x=(np.arange(n)+.5)/n
        line=20+50*np.array([math.erf(v/width) for v in x])
        T=np.broadcast_to(line[:,None,None],(n,n,n)).copy()
        R=Reconstruccion([[.025,.5,.5]],np.ones(T.shape,bool),[0,0,0],[1/n]*3)
        value=float(R.evaluate(T)[0]);truth=20+50*math.erf(.025/width)
        rows.append(dict(n=n,spacing_m=1/n,S25_exact_C=truth,S25_reconstructed_C=value,absolute_error_C=abs(value-truth),
                         true_delta_C=70-truth,estimated_delta_C=70-value,
                         scope='Perfil erf exacto de difusión en semiespacio, profundidad 25 mm y ancho térmico 50 mm; NO campo de fundación.'))
    return rows


def main(output):
    rows=[]
    for n in (12,24,48):
        for inclined,correction in ((False,False),(True,False),(True,True)):
            rows.append(referencia_plano(n,inclined,correction))
    write_csv(output/'frontera_staircase.csv',rows)
    sharp=gradiente_pronunciado();write_csv(output/'gradiente_pronunciado.csv',sharp)
    write_json(output/'referencias.json',dict(staircase=rows,sharp_gradient=sharp,
        note='Errores de referencia, no cotas transferibles automáticamente al IFC. Variante corregida sólo en benchmark, no en la fundación.'))
    print(rows)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--salida',type=Path,default=Path('resultados/validacion_s25_final/referencias'))
    main(p.parse_args().salida)
