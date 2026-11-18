"""Observador experimental IFC+MLS. Validez oficial separada de la estimación."""
import csv
import json
from pathlib import Path
import hashlib
import numpy as np
from collections import OrderedDict
from threading import Lock
from .superficies_ifc import cargar_superficies
from .reconstruccion_s25 import Reconstruccion
from .auditoria_geometrica import detalle_distancia,distancia_aristas
from .criterio_s25 import evaluar_testigos

# Sólo geometría/pesos: nunca temperaturas ni parámetros térmicos de otra corrida.
_STENCILS=OrderedDict()
_STENCIL_LOCK=Lock()

def stencil_compartido(sample,m,p):
    key=hashlib.sha256(m.activo.tobytes()+m.ids.tobytes()+np.asarray(p['origin'],float).tobytes()+
        np.asarray(m.dx,float).tobytes()+sample['points'].tobytes()+sample['point_owner'].tobytes()).hexdigest()
    with _STENCIL_LOCK:
        cached=_STENCILS.get(key)
        if cached is not None:
            _STENCILS.move_to_end(key);return cached
    value=Reconstruccion(sample['points'],m.activo,p['origin'],m.dx,cell_ids=m.ids,point_ids=sample['point_owner'],allow_partial=True)
    with _STENCIL_LOCK:
        _STENCILS[key]=value
        while len(_STENCILS)>6:_STENCILS.popitem(last=False)
    return value


def validar_s25(p):
    spec=p.get('s25')
    if spec is None:return
    if not p.get('construction') or p['geometry']!='foundation':raise ValueError('S25 IFC requiere construcción de fundación Python.')
    if not isinstance(spec,dict) or set(spec)!={'method','depth_m','surface_spacing_m'} or spec['method']!='ifc_mls':
        raise ValueError('Configuración S25 IFC desconocida.')
    if spec['depth_m']!=.025 or isinstance(spec['surface_spacing_m'],bool) or not isinstance(spec['surface_spacing_m'],(int,float)) or not np.isfinite(spec['surface_spacing_m']) or not .2<=spec['surface_spacing_m']<=5:
        raise ValueError('Profundidad S25=0,025 m y separación de muestras 0,2–5 m.')


class ObservadorIFC:
    def __init__(self,config,path,*,geometry=None):
        self.config=config;self.path=Path(path);self.stages={};self.rows=[];self.peak=None;self.peak_snapshot=None
        self.geometry=geometry if geometry is not None else cargar_superficies(str(self.path),self.path.stat().st_mtime_ns,config['s25']['surface_spacing_m'])

    def __call__(self,m,p,history):
        if not m.activo.any():return
        key=tuple(map(int,np.unique(m.ids[m.activo])))
        if key not in self.stages:
            sample=dict(self.geometry.at(key))
            if not p.get('environment'):
                sample['region']=np.where(sample['region']=='soil','base_boundary',sample['region'])
            reconstruct=stencil_compartido(sample,m,p)
            self.stages[key]=(sample,reconstruct)
        sample,reconstruct=self.stages[key]
        values=reconstruct.evaluate(m.T)
        finite=np.isfinite(values)
        if not finite.any():raise ValueError('Ningún punto IFC admite reconstrucción en esta malla.')
        cold=int(np.nanargmin(values));maximum=float(np.max(m.T[m.activo]))
        row=dict(time_s=float(m.t),Tmax_C=maximum,Tmin_S25_estimate_C=float(values[cold]),
                 DeltaT_estimate_C=maximum-float(values[cold]),sample_count=len(values),
                 valid_sample_count=int(finite.sum()),unsupported_points=int((~finite).sum()),
                 complete_sampling=bool(finite.all()),cold_sample_index=cold,active_pours=list(key))
        self.rows.append(row)
        if self.peak is None or row['DeltaT_estimate_C']>self.peak['DeltaT_estimate_C']:
            hot=np.unravel_index(np.argmax(np.where(m.activo,m.T,-np.inf)),m.forma)
            self.peak=dict(**row,sample_index=cold,surface_xyz_m=sample['surface'][cold].tolist(),
                           S25_xyz_m=sample['points'][cold].tolist(),outward_normal=sample['outward'][cold].tolist(),
                           triangle_id=int(sample['triangle_id'][cold]),
                           hot_index=list(map(int,hot)),hot_xyz_m=(np.asarray(p['origin'])+(np.array(hot)+.5)*m.dx).tolist(),
                           hot_pour_id=int(m.ids[hot]),air_temperature_C=history.get('air_temperature_C'),
                           region=str(sample['region'][cold]),surface_pour_id=int(sample['owner'][cold]),point_pour_id=int(sample['point_owner'][cold]))
            self.peak_snapshot=(float(m.t),m.T.copy(),m.activo.copy(),history.get('construction_state'))
            self.peak_ids=m.ids.copy()

    def extra_snapshots(self):
        return [self.peak_snapshot] if self.peak_snapshot and self.peak_snapshot[3] is not None else []

    def critical_detail(self):
        peak=self.peak;key=tuple(peak['active_pours']);sample,reconstruct=self.stages[key]
        t,T,active,state=self.peak_snapshot;i=peak['sample_index'];p=self.config
        surface_solid=next(s for s in self.geometry.solids if int(s['VertidaID'])==peak['surface_pour_id'])
        geometry=detalle_distancia(sample['points'][i],sample['surface'][i],sample['outward'][i],self.geometry,key)
        geometry['feature_edge']=distancia_aristas(sample['surface'][i],surface_solid)
        orientations=[]
        from .moldaje import resistencia_extra
        for axis,n in enumerate(sample['outward'][i]):
            if abs(n)<1e-7:continue
            face=2*axis+int(n>0);b=p['faces'][face]
            orientations.append(dict(face='xyz'[axis]+('+' if n>0 else '-'),type=b['type'],h_W_m2K=b['h'],
                                      R_additional_m2K_W=b['R'],R_formwork_m2K_W=resistencia_extra(p,face,t)))
        np.savez_compressed(self.folder/'s25_ifc_critical.npz',T_C=T,active=active,pour_ids=self.peak_ids,time_s=t,
                            origin_m=p['origin'],spacing_m=reconstruct.dx)
        detail=dict(time_s=t,hot=dict(xyz_m=peak['hot_xyz_m'],ijk=peak['hot_index'],temperature_C=peak['Tmax_C'],pour_id=peak['hot_pour_id']),
                    cold=dict(xyz_m=peak['S25_xyz_m'],surface_xyz_m=peak['surface_xyz_m'],temperature_C=peak['Tmin_S25_estimate_C'],
                              surface_pour_id=peak['surface_pour_id'],point_pour_id=peak['point_pour_id'],guid=surface_solid['guid'],
                              triangle_id=peak['triangle_id'],triangle_xyz_m=surface_solid['triangulos'][peak['triangle_id']].tolist(),normal=peak['outward_normal']),
                    geometry=geometry,reconstruction=reconstruct.audit(i,T),
                    boundary=dict(region=peak['region'],air_temperature_C=peak['air_temperature_C'],orientations=orientations,
                                  staircase_area_factor=float(np.sum(np.abs(sample['outward'][i]))),
                                  note='Parámetros por caras cartesianas, no una frontera conforme IFC.'),
                    numerical_error_bound_C=None,field_file='s25_ifc_critical.npz',
                    temporal_audit=dict(activation_distance_h=min(abs(t/3600-v['start_h']) for v in p['construction']['pours']),
                        time_interpolation_used=False,near_peak=[r for r in self.rows if abs(r['time_s']-t)<=3600]),
                    assessment=evaluar_testigos([dict(id='critical',delta_C=peak['DeltaT_estimate_C'],validated=False,error_bound_C=None)]))
        return detail

    def export(self,folder,metadata):
        folder=Path(folder)
        self.folder=folder
        def csvfile(name,rows):
            if not rows:return
            with (folder/name).open('w',encoding='utf-8-sig',newline='') as f:
                writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
        csvfile('s25_ifc_history.csv',self.rows)
        stages=[]
        for number,(key,(sample,reconstruct)) in enumerate(self.stages.items()):
            name=f's25_ifc_points_{number}.csv'
            csvfile(name,[dict(surface_pour_id=int(owner),point_pour_id=int(point_owner),triangle_id=int(face),surface_x=float(s[0]),surface_y=float(s[1]),surface_z=float(s[2]),
                              x=float(x[0]),y=float(x[1]),z=float(x[2]),nx=float(n[0]),ny=float(n[1]),nz=float(n[2]),region=str(region),area_m2=float(area),reconstruction_available=bool(available))
                          for owner,point_owner,face,s,x,n,region,area,available in zip(sample['owner'],sample['point_owner'],sample['triangle_id'],sample['surface'],sample['points'],sample['outward'],sample['region'],sample['area'],reconstruct.supported)])
            unknown=[]
            for i in np.flatnonzero(~reconstruct.supported):
                unknown.append(dict(sample_id=int(sample['indices'][i]),surface_pour_id=int(sample['owner'][i]),
                    point_pour_id=int(sample['point_owner'][i]),triangle_id=int(sample['triangle_id'][i]),
                    xyz_m=sample['points'][i].tolist(),normal=sample['outward'][i].tolist(),area_m2=float(sample['area'][i]),
                    **reconstruct.details[i]))
            csvfile(f's25_unknown_{number}.csv',unknown)
            coverage=[]
            normals=sample['outward']
            types=np.where(np.abs(normals[:,2])>.99999,'horizontal',np.where(np.abs(normals[:,2])<1e-7,'lateral','inclined'))
            for region in np.unique(sample['region']):
                for kind in np.unique(types):
                    mask=(sample['region']==region)&(types==kind)
                    if not mask.any():continue
                    area=float(sample['area'][mask].sum());computed=float(sample['area'][mask&reconstruct.supported].sum())
                    coverage.append(dict(region=str(region),surface_type=str(kind),points=int(mask.sum()),
                        computed_points=int(np.sum(mask&reconstruct.supported)),area_m2=area,computed_area_m2=computed,computed_area_fraction=computed/area))
            stages.append(dict(active_pours=list(key),points_file=name,coverage_by_area=coverage,excluded_internal=sample['excluded_internal'],
                               rejected_not_in_active_concrete=sample['rejected_not_in_active_concrete'],**reconstruct.diagnostics))
        result=dict(method='IFC_TRIANGLES_QUADRATIC_MLS',depth_m=.025,validation='NOT VALIDATED',
                    probability_status='NOT FULLY EVALUATED',compliance='INDETERMINATE',
                    ifc_sha256=hashlib.sha256(self.path.read_bytes()).hexdigest(),peak_estimate=self.peak,
                    sampling_spacing_m=self.config['s25']['surface_spacing_m'],stages=stages,history=self.rows,
                    complete_sampling=all(r['complete_sampling'] for r in self.rows),
                    limitations=['Reconstrucción de campo FV con borde escalonado; no cut-cell ni refinamiento local.',
                                 'Stencils unilaterales por vertida del punto; puntos singulares permanecen desconocidos y la métrica es parcial.',
                                 'Cuadratura superficial finita; aristas por límites de caras, sin normal única en la arista.',
                                 'Superficie curva representada por triangulación IFC; error de faceteado separado.',
                                 'MLS no corrige errores del solver ni demuestra convergencia del mínimo continuo S25.'])
        result['critical_pair']=self.critical_detail()
        metadata['s25_ifc']=result
        metadata['validity']['project_deltaT_25mm']='NOT EVALUATED'
        (folder/'s25_ifc.json').write_text(json.dumps(result,ensure_ascii=False,allow_nan=False),encoding='utf-8')
        (folder/'metadata.json').write_text(json.dumps(metadata,ensure_ascii=False,allow_nan=False),encoding='utf-8')
        return result
