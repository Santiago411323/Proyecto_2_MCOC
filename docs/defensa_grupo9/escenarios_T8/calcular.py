"""Lote T8. Ejecutar desde la raíz con numpy, numba y dependencias del proyecto."""
import csv
import json
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import numpy as np
from numba import njit

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from comparar_vertidas_pronostico import weather_for_run
from therma.ejecutar import validar
from therma.fuente_tabulada import FuenteTabulada
from therma.meteorologia import ForzanteAire
from therma.moldaje import resistencia_extra
from therma.suelo import validar_entorno
from therma.superficies_ifc import cargar_superficies
from therma.reconstruccion_s25 import Reconstruccion
from therma.cierre_f02 import evaluar_horizonte
from termico_cartesiano import TermicoCartesiano

OUT = Path(__file__).parent
DURATION = 42*86400
NAMES = [f'M{i}_{c}' for c in ('SS','22A') for i in range(1,5)]
CLIMATES = ['OM16','OM18','Meteored18']
def read(path):
    return json.loads(Path(path).read_bytes())

@njit(nogil=True)
def march(old,new,idx,neighbors,labels,axis_g,ga,gs,air,ground,h,source):
    hot=-1e20
    hotidx=-1
    for j in range(idx.size):
        i=idx[j]
        v=old[i]
        power=ga[j]*(air-v)+gs[j]*(ground-v)+source[labels[j]]
        for a in range(3):
            power+=axis_g[a]*((old[neighbors[j,a*2]]-v)+(old[neighbors[j,a*2+1]]-v))
        x=v+h*power
        new[i]=x
        if x>hot:
            hot=x
            hotidx=i
    return hot,hotidx

@njit(nogil=True)
def lowest(T,indices,weights,offset):
    cold=1e30
    pt=-1
    for j in range(len(offset)-1):
        v=0.
        for k in range(offset[j],offset[j+1]):
            v+=T[indices[k]]*weights[k]
        if v<cold:
            cold=v
            pt=j
    return cold,pt

cfg=read(ROOT/'docs/hielo_f02/refinamiento_xyz/config_T8_96x96x54.json')
p=validar(cfg)
shape=tuple(p['n'])
dx=np.array(p['L'])/shape
ids=np.ascontiguousarray(np.array(p['mask']).reshape(shape[::-1]).T)
pours=p['construction']['pours']
starts=np.array([o['start_h']*3600 for o in pours])
soil=validar_entorno(p)
geompath=ROOT/'modelo_e02.ifc'
surf=cargar_superficies(str(geompath),geompath.stat().st_mtime_ns,p['s25']['surface_spacing_m'])
stages=[]
for stage in range(1,4):
    active=(ids>0)&(ids<=stage)
    exterior={}
    for n,b in enumerate(p['faces']):
        exterior['xyz'[n//2]+'-+'[n%2]]=dict(tipo='robin',h_W_m2K=b['h'],R_m2K_W=b['R']+resistencia_extra(p,n,0),temperatura_C=0.)
    model=TermicoCartesiano(shape,p['L'],p['k'],p['rho'],p['cp'],soil.bordes(active,exterior),active)
    assert p['dt']<=model.dt_max
    gs,_=soil.terminos_diagnosticos(model)
    ga=model.G_borde-gs
    cap=p['rho']*p['cp']*model.volumen
    axis_g=np.array([model.volumen/d**2*p['k']/cap for d in dx])
    ix=np.flatnonzero(active.ravel()).astype(np.int32)
    nb=np.repeat(ix[:,None],6,axis=1)
    for a,(lo,hi,G) in enumerate(model.pares):
        pair=np.argwhere(G>0)
        left=np.ravel_multi_index(pair.T,shape)
        pair[:,a]+=1
        right=np.ravel_multi_index(pair.T,shape)
        nb[np.searchsorted(ix,left),2*a+1]=right
        nb[np.searchsorted(ix,right),2*a]=left
    sample=surf.at(tuple(range(1,stage+1)))
    rec=Reconstruccion(sample['points'],active,p['origin'],dx,cell_ids=ids,point_ids=sample['point_owner'],allow_partial=True)
    assert rec.supported.all()
    stages.append((ix,nb,ids.ravel()[ix],axis_g,ga.ravel()[ix]/cap,gs.ravel()[ix]/cap,rec.indices.astype(np.int32),rec.weights,np.r_[rec.starts,len(rec.weights)],sample['points']))
    print('Geometría IFC comprobada, etapa',stage,flush=True)

start=cfg['weather']['start_utc']
weather=[cfg['weather']]+[weather_for_run(ROOT/'data/weather'/folder,start) for folder in ('20261118T143552195128Z_ee51ca19','meteored_20261118_punta_arenas')]
forces=[ForzanteAire(w,DURATION) for w in weather]
targets=set(np.linspace(0,DURATION,p['frames']))|set(starts)|{float(t-1) for t in starts[1:]}
times=[0.]
for target in sorted(targets)[1:]:
    while times[-1]<target-1e-9:
        t=times[-1]
        times.append(min(t+p['dt'],target,forces[0].siguiente(t)))
times=np.array(times)
airs=np.array([[w.temperatura(t) for t in times[:-1]] for w in forces])
tbl=np.loadtxt(ROOT/'data/hydration/source_terms_fv_tikhonov.txt')
rates=[]
for i,name in enumerate(NAMES):
    keep=np.isfinite(tbl[:,i+1])
    curve=dict(cfg['construction']['curve'],time_h=tbl[keep,0].tolist(),Q_W_m3=tbl[keep,i+1].tolist(),column=name+'_W_m3')
    source=FuenteTabulada(curve,p['rho'],p['cp'])
    mat=np.zeros((len(times)-1,4))
    for layer,activation in enumerate(starts,1):
        energies=np.array([source.energia_volumetrica(max(0,t-activation)) for t in times])
        mat[:,layer]=np.diff(energies)/np.diff(times)/(p['rho']*p['cp'])
    rates.append(mat)
def simulate(case, *, output_dir=OUT):
    wi,si=case
    T=np.zeros(ids.size);tmp=T.copy();T[stages[0][0]]=8
    stage=0
    tmax=[8.];delta=[0.];peaks=[-1e9,-1e9]
    locations={}
    for j,h in enumerate(np.diff(times)):
        ix,nb,labels,g,ga,gs,indices,weights,offset,xyz=stages[stage]
        hot,hidx=march(T,tmp,ix,nb,labels,g,ga,gs,airs[wi,j],soil.temperature_C,h,rates[si][j])
        T,tmp=tmp,T
        if stage<2 and times[j+1]>=starts[stage+1]-1e-9:
            stage+=1
            fresh=ids.ravel()==stage+1
            T[fresh]=8
            if hot<8:
                hot=8.
                hidx=int(np.flatnonzero(fresh)[0])
            indices,weights,offset,xyz=stages[stage][6:]
        cold,cidx=lowest(T,indices,weights,offset)
        pair=hot-cold
        for index,value,prefix in [(0,hot,'T'),(1,pair,'D')]:
            if value>peaks[index]:
                peaks[index]=value
                locations[prefix+'_time_h']=times[j+1]/3600
                locations[prefix+'_hot_xyz_m']=(p['origin']+(np.array(np.unravel_index(hidx,shape))+.5)*dx).tolist()
                if index:locations['D_S25_xyz_m']=xyz[cidx].tolist()
        tmax.append(hot);delta.append(pair)
    audit=evaluar_horizonte([dict(time_s=t,Tmax_C=v,DeltaT_estimate_C=d) for t,v,d in zip(times,tmax,delta)],starts[-1]/3600)
    fourteen=times<=14*86400
    record=dict(climate=CLIMATES[wi],source=NAMES[si],Tmax_C=max(tmax),Delta_C=max(delta),T14_C=max(np.array(tmax)[fourteen]),D14_C=max(np.array(delta)[fourteen]),exceeds_T=max(tmax)>70,exceeds_delta=max(delta)>20,horizon_captured=audit['captured'],**locations)
    if wi==0 and si<4:
        ref=read(ROOT/f'docs/hielo_f02/convergencia/T8_96x96x54_dt1200_fv_{NAMES[si]}.json')
        err=max(abs(record['Tmax_C']-ref['Tmax_C']),abs(record['Delta_C']-ref['Delta_estimate_C']))
        assert err<1e-6,(record,err)
        record['reference_max_error_C']=err
    if output_dir is not None:
        (output_dir/(CLIMATES[wi]+'_'+NAMES[si]+'.json')).write_text(json.dumps(record,indent=2),encoding='utf8')
    print(CLIMATES[wi],NAMES[si],round(max(tmax),3),round(max(delta),3),flush=True)
    return record
if __name__=='__main__':
    cases=[(w,s) for w in range(3) for s in range(8)]
    with ThreadPoolExecutor(max_workers=4) as pool:
        results=list(pool.map(simulate,cases))
    with (OUT/'resultados.csv').open('w',newline='',encoding='utf-8-sig') as f:
        writer=csv.DictWriter(f,fieldnames=list(results[0]))
        writer.writeheader();writer.writerows(results)
