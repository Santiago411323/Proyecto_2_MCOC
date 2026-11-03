"""4C: secuencia constructiva sobre la misma voxelización IFC y motor oficial."""
from pathlib import Path
import hashlib
import json
import math
import time
import numpy as np
from .activacion import ConstruccionTermica
from .hidratacion import AdiabaticaExponencial
from .resultados import guardar,a_xfast


def validar_construccion(p):
    c=p['construction']
    if p['geometry']!='foundation' or p['dim']!=3:raise ValueError('La construcción usa exclusivamente la fundación IFC 3D.')
    if p['calibrate'] or p['source']!='none':raise ValueError('Construcción: sin calibración a 70 °C ni pulso adicional; usar hidratación por edad.')
    if not isinstance(c,dict) or set(c)!={'model','parameter_source','pours'} or c['model']!='exponential_adiabatic':raise ValueError('Configuración constructiva desconocida.')
    if not isinstance(c['parameter_source'],str) or not 5<=len(c['parameter_source'])<=500:raise ValueError('Declara la procedencia de los parámetros de hidratación.')
    if not isinstance(c['pours'],list):raise ValueError('Se requiere una lista de vertidas.')
    actual=set(v for v in p['mask'] if v)
    if len(c['pours'])!=len(actual):raise ValueError('Una configuración por vertida del IFC.')
    ids=[]
    for v in c['pours']:
        if not isinstance(v,dict) or set(v)!={'id','start_h','placement_C','theta_inf_C','tau_h'}:raise ValueError('Parámetros de vertida desconocidos.')
        if any(isinstance(x,bool) or not isinstance(x,(int,float)) or not math.isfinite(x) for x in v.values()):raise ValueError('Parámetros de vertida finitos.')
        if int(v['id'])!=v['id'] or v['id'] not in actual or v['start_h']<0 or v['theta_inf_C']<0 or v['tau_h']<=0:raise ValueError('ID/horario/elevación/tau de vertida inválidos.')
        if v['start_h']>365*24 or v['tau_h']<.01:raise ValueError('Horario máximo 365 días y tau mínimo 0.01 h para este prototipo.')
        ids.append(v['id'])
    if set(ids)!=actual or len(set(ids))!=len(ids):raise ValueError('IDs duplicados o ausentes.')
    if min(v['start_h'] for v in c['pours'])>=p['days']*24:raise ValueError('El horizonte debe incluir hormigón colocado.')


def ejecutar_construccion(p,identificador,carpeta,ifc,progress=lambda v:None):
    start=time.perf_counter();n=tuple(map(int,p['n']));ids=np.asarray(p['mask']).reshape(n[::-1]).transpose(2,1,0)
    config=p['construction'];by_id={int(v['id']):v for v in config['pours']}
    pours=[dict(id=layer['id'],guid=layer['guid'],name=layer['nombre'],material_id=1,
                inicio_s=by_id[layer['id']]['start_h']*3600,temperatura_C=by_id[layer['id']]['placement_C']) for layer in ifc['capas']]
    borders={f"{'xyz'[a]}{sign}":dict(tipo={'D':'dirichlet','N':'neumann','R':'robin'}[b['type']],
        temperatura_C=b['temp'],flujo_saliente_W_m2=b['flux'],h_W_m2K=b['h'],R_m2K_W=b['R'])
        for a in range(3) for s,sign in enumerate(('-','+')) for b in [p['faces'][2*a+s]]}
    ground=None
    if p.get('environment'):
        from .suelo import validar_entorno
        ground=validar_entorno(p)
    m=ConstruccionTermica(ids,p['L'],pours,p['k'],p['rho'],p['cp'],borders,suelo=ground)
    models={ident:AdiabaticaExponencial(v['theta_inf_C'],v['tau_h']*3600) for ident,v in by_id.items()}
    duration=p['days']*86400;targets=set(map(float,np.linspace(0,duration,p['frames'])))
    starts=sorted(set(v['inicio_s'] for v in pours))
    for t in starts:
        if 0<t<=duration:
            targets.add(t);previous=max([s for s in starts if s<t]+[0.]);targets.add(max(0.,t-min(1.,(t-previous)/2)))
    targets=sorted(targets);hist=[];fields=[];active=[];times=[];states=[];steps=0;dt_used=[];dt_critical=[]
    critical=None;critical_value=-math.inf
    center=tuple(int(v//2) for v in n)

    def pour_states():
        out=[]
        for v in pours:
            ident=v['id'];is_active=bool(np.any((ids==ident)&m.activo));age=m.edad_s(ident) if is_active else None
            out.append(dict(id=ident,active=is_active,age_s=age,
                source_W_m3=p['rho']*p['cp']*models[ident].tasa_C_s(age) if is_active else 0.,
                adiabatic_rise_C=models[ident].elevacion(age) if is_active else None))
        return dict(time_s=m.t,pours=out,active_pour_ids=[v['id'] for v in out if v['active']])

    def measure():
        nonlocal critical,critical_value
        state=pour_states();vals=m.T[m.activo];count=len(vals)
        location=None if not count else list(map(int,np.unravel_index(np.argmax(np.where(m.activo,m.T,-np.inf)),n)))
        q=sum(s['source_W_m3']*np.count_nonzero(ids==s['id']) for s in state['pours'] if s['active'])/count if count else 0.
        E=m.energia();net=m.energia_colocacion_J+m.energia_fuente_J+m.energia_borde_J
        h=dict(t=m.t,center=float(m.T[center]) if m.activo[center] else None,min=float(vals.min()) if count else None,
            max=float(vals.max()) if count else None,hottest_xyz=location,active_cells=count,active_volume_m3=count*m.volumen,
            energy=E,net=net,residual=m.residual(),placed_J=m.energia_colocacion_J,source_J=m.energia_fuente_J,
            boundary_J=m.energia_borde_J,q=q,layers=[float(m.T[(ids==v['id'])&m.activo].mean()) if np.any((ids==v['id'])&m.activo) else None for v in pours])
        if ground:
            soil_power=float(np.sum((m.P_suelo-m.G_suelo*m.T)*m.activo))
            total_power=float(np.sum((m.modelo.P_borde_constante-m.modelo.G_borde*m.T)*m.activo)) if m.modelo else 0.
            h.update(soil_J=m.energia_suelo_J,air_J=m.energia_aire_J,soil_into_concrete_W=soil_power,
                     air_into_concrete_W=total_power-soil_power)
        hist.append(h)
        if count and h['max']>critical_value:
            critical_value=h['max'];critical=(m.t,m.T.copy(),m.activo.copy(),state)
        return state

    def snapshot(state):
        times.append(m.t);fields.append(m.T.copy());active.append(m.activo.copy());states.append(state)

    snapshot(measure());target_index=1
    while m.t<duration-1e-9:
        limit=m.dt_max
        if p['dtMode']=='manual':
            dt=p['dt']
            if not math.isfinite(dt) or dt<=0 or dt>limit*(1+1e-12):raise ValueError(f'Paso manual inestable para la etapa en t={m.t:g} s; dt crítico={limit:g} s.')
        else:
            active_tau=[model.tau_s for ident,model in models.items() if model.theta_inf_C>0 and np.any((ids==ident)&m.activo)]
            dt=min(p['factor']*limit,min(active_tau,default=144000.)/40,3600.)
        end=min(m.t+dt,targets[target_index],m.siguiente_evento_s,duration);h=end-m.t
        if h<=0:raise ValueError('El integrador no puede avanzar; revisar cronograma.')
        q=np.zeros(n)
        for ident,model in models.items():
            cells=(ids==ident)&m.activo
            if cells.any():q[cells]=model.fuente_media(m.edad_s(ident),m.edad_s(ident)+h,p['rho'],p['cp'])
        dt_used.append(h)
        if math.isfinite(limit):dt_critical.append(limit)
        m.paso(h,q);m.t=end;state=measure();steps+=1
        if abs(m.t-targets[target_index])<1e-8:
            snapshot(state);target_index+=1
        if steps>200000 or steps*np.prod(n)>3e8:raise ValueError('Construcción demasiado costosa; reducir malla, horizonte o resolución temporal.')
        if steps%50==0:progress(m.t/duration)
    t,T,mask,state=critical
    hit=next((j for j,v in enumerate(times) if abs(v-t)<1e-7),None)
    if hit is None:
        j=int(np.searchsorted(times,t));times.insert(j,t);fields.insert(j,T);active.insert(j,mask);states.insert(j,state)
    else:times[hit]=t;fields[hit]=T;active[hit]=mask;states[hit]=state
    centers=[h for h in hist if h['center'] is not None];central_peak=max(centers,key=lambda h:h['center']) if centers else None
    residual=max(abs(h['residual']) for h in hist);scale=max(1.,max(abs(h['energy']) for h in hist))
    metrics=dict(maxCenter=central_peak['center'] if central_peak else None,peakTime=central_peak['t'] if central_peak else t,
        maxField=critical_value,hottest_xyz=next(h['hottest_xyz'] for h in hist if h['t']==t),global_peak_time_s=t,
        global_peak_field_exported=True,residual=residual,energy_residual_relative=residual/scale,exactError=None,qmax=0.,
        dt=max(dt_used),dtMax=min(dt_critical) if dt_critical else None,alpha=p['k']/(p['rho']*p['cp']),steps=steps,
        N=int(m.activo.sum()),gridN=int(np.prod(n)),volume=float(m.activo.sum()*m.volumen),geometric_volume_m3=float(np.count_nonzero(ids)*m.volumen),
        runtime_s=time.perf_counter()-start,connectivity_rebuilds=m.reconstrucciones)
    provenance=dict(mode='Construcción por vertidas · hidratación didáctica no calibrada',solver='termico_cartesiano.TermicoCartesiano.paso',
        ifc={k:ifc[k] for k in ('archivo','sha256')},pours=[dict(id=v['id'],guid=v['guid'],name=v['name'],material_id=1,
             active_from_s=v['inicio_s'],placement_C=v['temperatura_C']) for v in pours],hydration_parameter_source=config['parameter_source'])
    folder=Path(carpeta);meta=guardar(folder,identificador,p,fields,times,hist,metrics,provenance)
    active_array=np.stack(active);flat=np.stack([a_xfast(a).astype('uint8') for a in active_array]);flat.tofile(folder/'active.bin')
    placement=np.full(n,-1.);temperatures=np.zeros(n)
    for v in pours:placement[ids==v['id']]=v['inicio_s'];temperatures[ids==v['id']]=v['temperatura_C']
    np.savez_compressed(folder/'campos.npz',T_C=np.stack(fields),tiempo_s=times,active=active_array,geometric_mask=ids>0,
        pour_ids=ids,material_ids=(ids>0).astype('int32'),placement_time_s=placement,placement_temperature_C=temperatures,
        age_s_by_pour=[[s['age_s'] if s['active'] else 0. for s in st['pours']] for st in states],
        active_by_pour=[[s['active'] for s in st['pours']] for st in states],
        source_W_m3_by_pour=[[s['source_W_m3'] for s in st['pours']] for st in states])
    if ground:
        with np.load(folder/'campos.npz') as data:arrays={key:data[key] for key in data.files}
        basal=np.zeros(n,dtype=bool);basal[:,:,0]=ids[:,:,0]>0
        histories={h['t']:h for h in hist}
        arrays.update(soil_contact_geometry=basal,soil_into_concrete_J=[histories[t]['soil_J'] for t in times],
                      air_into_concrete_J=[histories[t]['air_J'] for t in times])
        np.savez_compressed(folder/'campos.npz',**arrays)
        from dataclasses import asdict
        region_cache={}
        for state in states:
            key=tuple(state['active_pour_ids'])
            if key not in region_cache:
                from .suelo import resumen_caras
                region_cache[key]=resumen_caras(np.isin(ids,key),m.dx)
        meta['environment']=dict(stage='5A',soil=dict(**asdict(ground),effective_resistance_m2K_W=ground.resistance_m2K_W,
            representation='Reservorio a temperatura fija, sin voxeles ni capacidad térmica de suelo.',
            basal_plane_z_m=p['origin'][2],layer_conductance_W_m2K=ground.conductivity_W_mK/ground.depth_m,external_conductance_W_m2K=1/ground.resistance_m2K_W),
            sign_convention='Potencias/energías positivas entran al hormigón; el reservorio recibe la cantidad opuesta.',
            soil_contact_cells_xfast=np.flatnonzero(a_xfast(basal)).astype(int).tolist(),
            snapshots=[dict(time_s=t,soil_into_concrete_J=histories[t]['soil_J'],air_into_concrete_J=histories[t]['air_J'],
                soil_into_concrete_W=histories[t]['soil_into_concrete_W'],air_into_concrete_W=histories[t]['air_into_concrete_W'],
                face_regions=region_cache[tuple(state['active_pour_ids'])]) for t,state in zip(times,states)])
        metrics['final_soil_into_concrete_J']=m.energia_suelo_J
        metrics['final_air_into_concrete_J']=m.energia_aire_J
        # guardar() ya serializó las métricas comunes; reflejar los diagnósticos nuevos.
        meta['metrics']=metrics
    meta['schema_version']='1.1';meta['geometry']['active_static']=False
    meta['activation']=dict(file='active.bin',dtype='uint8',shape=list(flat.shape),sha256=hashlib.sha256((folder/'active.bin').read_bytes()).hexdigest(),
        semantics='1=concrete active at snapshot time; 0=not placed or outside geometry',index_order=meta['geometry']['index_order'])
    meta['construction']=dict(model='exponential_adiabatic',snapshots=states,events=m.eventos,
        timeline_semantics='Estados posteriores a activación en t_inicio. Salida adicional hasta 1 s antes de cada evento.',
        energy_reference='0 °C; E_activa = E_colocacion + E_hidratacion + E_borde; no se resta la energía del hormigón nuevo como error.',
        parameter_source=config['parameter_source'],exposed_boundary_policy='Mismos bordes por orientación en toda cara expuesta de la máscara activa; contacto interno perfecto al activar.')
    meta['fields']['snapshot_method']='Snapshots de pasos Python exactos; sin interpolar a través de activaciones.'
    meta['validity']['construction_schedule']='SIMULATED';meta['validity']['hydration']='DIDACTIC_NOT_CALIBRATED'
    meta['warnings']=['Geometría IFC provisional; requiere validación docente.','Hidratación exponencial por edad, sin calibración experimental ni dependencia de temperatura.',
        'Ambiente constante y bordes simplificados; sin suelo explícito, clima real ni mecánica de fisuración.','Activación completa instantánea de cada vertida; no se modela hormigonado continuo.',
        'Diferencial docente a 25 mm: NOT EVALUATED.']
    if ground:
        meta['warnings'][2]='Suelo como reservorio efectivo sin almacenamiento: parámetros didácticos declarados; no suelo explícito ni validación geotécnica. Aire constante; sin clima real ni mecánica de fisuración.'
        meta['validity']['ground']='EFFECTIVE_DIDACTIC_RESERVOIR'
        meta['provenance']['soil_parameter_source']=ground.parameter_source
        meta['construction']['exposed_boundary_policy']='Contacto basal exclusivo con suelo efectivo; demás caras expuestas con borde por orientación; contacto interno perfecto al activar.'
    (folder/'metadata.json').write_text(json.dumps(meta,ensure_ascii=False,allow_nan=False),encoding='utf-8')
    return meta
