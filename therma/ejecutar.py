"""Validación y orquestación: usa exclusivamente la API del motor Python."""
from functools import lru_cache
import copy
import math
from pathlib import Path
import numpy as np
from termico_cartesiano import TermicoCartesiano
from calibrar_qmax import integral_pulso, temperatura_centro
from panel.exportar_ifc import datos_ifc
from .resultados import guardar
from .moldaje import validar_moldaje,resistencia_extra

ROOT=Path(__file__).resolve().parents[1]


@lru_cache(maxsize=6)
def ifc_actual(mtime,forma=None):
    return datos_ifc(ROOT/'modelo_e02.ifc',formas=[forma] if forma else None)


def validar(config):
    if not isinstance(config,dict):raise ValueError('La configuración debe ser un objeto JSON.')
    p=copy.deepcopy(config)
    defaults=dict(geometry='block',meshIndex=0,dim=1,L=[1.,1.,1.],n=[20,16,8],k=2.,rho=2400.,cp=900.,
        initial=20.,initialType='uniform',amplitude=30.,source='none',period=172800.,qmax=0.,calibrate=False,
        target=70.,days=1.,dtMode='auto',dt=300.,factor=.7,frames=65,origin=[0.,0.,0.])
    allowed=set(defaults)|{'faces','mask','construction','environment','formwork'}
    if set(p)-allowed:raise ValueError('Parámetros desconocidos: '+', '.join(sorted(set(p)-allowed)))
    p={**defaults,**p}
    if p['geometry'] not in ('block','foundation') or isinstance(p['dim'],bool) or p['dim'] not in (1,2,3):raise ValueError('Geometría o dimensión inválida.')
    for key,values in [('initialType',('uniform','sine')),('source',('none','constant','pulse')),('dtMode',('auto','manual'))]:
        if p[key] not in values:raise ValueError('Opción inválida: '+key)
    if not isinstance(p['calibrate'],bool):raise ValueError('calibrate debe ser booleano.')
    for key in ('k','rho','cp','initial','amplitude','period','qmax','target','days','dt','factor'):
        if isinstance(p[key],bool) or not isinstance(p[key],(int,float)) or not math.isfinite(p[key]):raise ValueError('Número finito requerido: '+key)
    if min(p['k'],p['rho'],p['cp'],p['days'],p['period'])<=0 or p['days']>365 or not 0<p['factor']<=1:raise ValueError('Material y duración positivos; duración ≤365 días, factor en (0,1].')
    if p['source']=='pulse' and p['days']*86400<p['period']:raise ValueError('La simulación debe cubrir todo el pulso.')
    if not isinstance(p['frames'],int) or not 20<=p['frames']<=100:raise ValueError('Usar entre 20 y 100 fotogramas.')
    if p['geometry']=='foundation':
        if isinstance(p['meshIndex'],bool) or p['meshIndex'] not in (0,1,2):raise ValueError('Malla IFC desconocida.')
        shape=None
        if p['meshIndex']==2:
            raw=p['n']
            if not isinstance(raw,list) or len(raw)!=3 or any(isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v) or v!=int(v) or not 2<=v<=160 for v in raw):raise ValueError('Malla personalizada: tres cantidades de celdas enteras entre 2 y 160.')
            shape=tuple(map(int,raw))
            if math.prod(shape)>50000:raise ValueError('Máximo 50.000 celdas; aumenta el tamaño del voxel.')
        d=ifc_actual((ROOT/'modelo_e02.ifc').stat().st_mtime_ns,shape);m=d['mallas'][0 if shape else p['meshIndex']]
        p.update(dim=3,L=np.subtract(d['max'],d['min']).tolist(),n=list(m['n']),mask=m['ids'],origin=d['min'])
    else:
        # Nunca aceptar máscaras arbitrarias del navegador en Fase 1.
        p['mask']=None
    for key in ('L','n','origin'):
        if not isinstance(p[key],list) or len(p[key])!=3 or any(isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v) for v in p[key]):raise ValueError('Se requieren tres números en '+key)
    if any(v<=0 for v in p['L']) or any(int(n)!=n or not 2<=n<=160 for n in p['n']):raise ValueError('Longitudes positivas y celdas enteras entre 2 y 160.')
    if np.prod(p['n'][:p['dim']])>50000:raise ValueError('Máximo 50.000 celdas en esta fase.')
    p.setdefault('faces',[dict(type='D',temp=20.,flux=0.,h=10.,R=0.) for _ in range(6)])
    if not isinstance(p['faces'],list) or len(p['faces'])!=6:raise ValueError('Se requieren seis condiciones de cara.')
    for b in p['faces']:
        if not isinstance(b,dict) or b.get('type') not in ('D','N','R'):raise ValueError('Borde desconocido.')
        for k in ('temp','flux','h','R'):
            if isinstance(b.get(k),bool) or not isinstance(b.get(k),(float,int)) or not math.isfinite(b[k]):raise ValueError('Valor de borde inválido: '+k)
        if min(b['h'],b['R'])<0:raise ValueError('h y R no pueden ser negativos.')
    validar_moldaje(p)
    if p.get("construction") is not None:
        from .construccion import validar_construccion
        validar_construccion(p)
    if p.get("environment") is not None:
        from .suelo import validar_entorno
        validar_entorno(p)
    return p


def preparar(p,homogeneo=False):
    shape=tuple(map(int,p['n'][:p['dim']]));mask=None
    if p['mask'] is not None:
        mask=np.asarray(p['mask']).reshape(tuple(reversed(shape))).transpose(tuple(reversed(range(p['dim']))))
    borders={}
    for a in range(p['dim']):
        for s in range(2):
            b=p['faces'][2*a+s]
            borders[f"{'xyz'[a]}{'+' if s else '-'}"]={'tipo':{'D':'dirichlet','N':'neumann','R':'robin'}[b['type']],
                'temperatura_C':0. if homogeneo else b['temp'],'flujo_saliente_W_m2':0. if homogeneo else b['flux'],
                'h_W_m2K':b['h'],'R_m2K_W':b['R']+resistencia_extra(p,2*a+s)}
    m=TermicoCartesiano(shape,p['L'][:p['dim']],k=p['k'],rho=p['rho'],cp=p['cp'],bordes=borders,activo=None if mask is None else mask>0)
    dt=p['dt'] if p['dtMode']=='manual' else p['factor']*m.dt_max
    if p['dtMode']=='auto' and p['source']=='pulse':dt=min(dt,p['period']/200)
    if not math.isfinite(dt) or dt<=0 or dt>m.dt_max*(1+1e-12):raise ValueError(f'Δt inestable: usar Δt ≤ {m.dt_max:g} s.')
    steps=math.ceil(p['days']*86400/dt)+2
    if steps>200000 or steps*np.prod(shape)*(3 if p['calibrate'] else 1)>3e8:raise ValueError('Cálculo demasiado grande; reducir malla o duración.')
    return m,dt,mask


def fuente_media(a,b,p):
    return 0. if p['source']=='none' else 1. if p['source']=='constant' else float(integral_pulso(b,p['period'])-integral_pulso(a,p['period']))/(b-a)


def integrar(m,p,dt,inicial,qmax,mask=None,guardar_campos=True,progress=lambda v:None):
    T=m.campo(inicial);duration=p['days']*86400;t=0.;E0=m.energia(T);net=0.;hist=[];campos=[];times=[]
    targets=np.linspace(0,duration,p['frames']);next_frame=0
    critical_value=-np.inf;critical_time=0.;critical_field=None
    def medir():
        nonlocal critical_value,critical_time,critical_field
        values=T[m.activo];index=int(np.argmax(np.where(m.activo,T,-np.inf)));xyz=np.unravel_index(index,m.forma)
        q=qmax*(0. if p['source']=='none' else 1. if p['source']=='constant' else
                  .5*(1-math.cos(2*math.pi*t/p['period'])) if t<=p['period'] else 0.)
        hist.append(dict(t=t,center=temperatura_centro(T),min=float(values.min()),max=float(values.max()),
            hottest_xyz=list(map(int,xyz)),energy=m.energia(T)-E0,net=net,residual=m.energia(T)-E0-net,q=q,
            layers=None if mask is None else [float(T[mask==i].mean()) for i in (1,2,3)]))
        if guardar_campos and hist[-1]['max']>critical_value:
            critical_value=hist[-1]['max'];critical_time=t;critical_field=np.where(m.activo,T,0).copy()
    medir()
    if guardar_campos:campos.append(np.where(m.activo,T,0).copy());times.append(0.);next_frame=1
    step=0
    while t<duration:
        end=min(t+dt,duration)
        if p['source']=='pulse' and t<p['period']<end:end=p['period']
        h=end-t;q=qmax*fuente_media(t,end,p)
        P=float(np.sum((m.P_borde_constante-m.G_borde*T)*m.activo))+q*m.volumen*np.sum(m.activo)
        nueva=m.paso(T,h,fuente_W_m3=q);net+=h*P
        while guardar_campos and next_frame<len(targets) and targets[next_frame]<=end+1e-8:
            w=min(1.,(targets[next_frame]-t)/h);campos.append(np.where(m.activo,(1-w)*T+w*nueva,0));times.append(float(targets[next_frame]));next_frame+=1
        T=nueva;t=end;medir();step+=1
        if step%100==0:progress(t/duration)
    if guardar_campos:
        # Conservar el campo del paso crítico real; no altera integración ni energía.
        match=next((i for i,v in enumerate(times) if abs(v-critical_time)<1e-7),None)
        if match is not None:campos[match]=critical_field;times[match]=critical_time
        else:
            pos=int(np.searchsorted(times,critical_time));times.insert(pos,critical_time);campos.insert(pos,critical_field)
    return hist,np.array(campos),times,T


def ejecutar(config,identificador,carpeta,progress=lambda v:None):
    p=validar(config)
    validar_moldaje(p)
    if p.get("construction") is not None:
        from .construccion import ejecutar_construccion
        return ejecutar_construccion(p,identificador,carpeta,ifc_actual((ROOT/"modelo_e02.ifc").stat().st_mtime_ns),progress)
    m,dt,mask=preparar(p)
    perfil=np.prod([np.sin(np.pi*x/L) for x,L in zip(m.coordenadas,m.longitudes)],axis=0)
    inicial=p['initial']+(p['amplitude']*perfil if p['initialType']=='sine' else 0.)
    qmax=0. if p['source']=='none' else p['qmax']
    if p['calibrate']:
        if p['source']=='none':raise ValueError('La calibración requiere una fuente.')
        if temperatura_centro(m.campo(inicial))>=p['target']:raise ValueError('El estado inicial ya alcanza el objetivo central.')
        base,_,_,_=integrar(m,p,dt,inicial,0.,mask,False,lambda v:progress(.25*v))
        unit,_,_,_=integrar(preparar(p,True)[0],p,dt,0.,1.,mask,False,lambda v:progress(.25+.25*v))
        candidatos=[(p['target']-b['center'])/u['center'] for b,u in zip(base,unit) if u['center']>1e-15]
        if any(b['center']>=p['target'] for b in base) or not candidatos or min(candidatos)<=0:raise ValueError('No hay calibración positiva para estos bordes y objetivo.')
        qmax=min(candidatos)
    hist,fields,times,final=integrar(m,p,dt,inicial,qmax,mask,True,lambda v:progress((.5 if p['calibrate'] else 0)+(.5 if p['calibrate'] else 1)*v))
    centermax=max(h['center'] for h in hist);peak=next(h['t'] for h in hist if h['center']>=centermax-1e-8)
    exact_error=None
    if mask is None and p['source']=='none' and p['initialType']=='sine' and all(b['type']=='D' and abs(b['temp']-p['initial'])<1e-12 for b in p['faces'][:2*p['dim']]):
        exact=p['initial']+p['amplitude']*perfil*np.exp(-p['k']/(p['rho']*p['cp'])*sum((np.pi/m.longitudes)**2)*p['days']*86400)
        exact_error=float(np.abs(final-exact).max())
    critical=max(hist,key=lambda h:h['max'])
    metrics=dict(maxCenter=centermax,peakTime=peak,maxField=critical['max'],hottest_xyz=critical['hottest_xyz'],
        global_peak_time_s=critical['t'],global_peak_field_exported=True,residual=max(abs(h['residual']) for h in hist),exactError=exact_error,
        qmax=qmax,dt=dt,dtMax=m.dt_max,alpha=p['k']/(p['rho']*p['cp']),steps=len(hist)-1,
        N=int(m.activo.sum()),gridN=int(np.prod(m.forma)),volume=float(m.activo.sum()*m.volumen))
    provenance=dict(solver='termico_cartesiano.TermicoCartesiano.paso',mode='ensayo de fundación' if mask is not None else 'verificación',
        ifc=None if mask is None else {k:ifc_actual((ROOT/'modelo_e02.ifc').stat().st_mtime_ns)[k] for k in ('archivo','sha256')})
    if mask is not None:
        d=ifc_actual((ROOT/'modelo_e02.ifc').stat().st_mtime_ns)
        provenance['pours']=[dict(id=c['id'],guid=c['guid'],name=c['nombre'],material_id=1,
            active_from_s=0.,ifc_start_h_not_applied=c['inicio_h'],ifc_placement_C_not_applied=c['temperatura_colocacion_C']) for c in d['capas']]
    return guardar(carpeta,identificador,p,fields,times,hist,metrics,provenance)
