"""Tuberías paralelas en x: agua cuasiestacionaria, intercambio subvoxel conservativo.

U lineal efectivo relaciona temperatura MEDIA de celda y agua. No resuelve
pared, gradiente radial ni capacidad del agua/tubo. No es un diseño hidráulico.
"""
import math
import numpy as np


def validar_enfriamiento(p):
    c=p.get('cooling')
    if c is None:return
    keys={'model','inlet_C','flow_kg_s','water_cp_J_kgK','conductance_W_mK','spacing_m','levels_m','start_h','stop_h','parameter_source'}
    if not isinstance(c,dict) or set(c)!=keys or c['model']!='parallel_x_pipes':raise ValueError('Configuración de tuberías desconocida.')
    if p.get('geometry')!='foundation' or not p.get('construction'):raise ValueError('Tuberías requieren fundación y vertidas Python.')
    for key in keys-{'model','levels_m','parameter_source'}:
        if isinstance(c[key],bool) or not isinstance(c[key],(int,float)) or not math.isfinite(c[key]):raise ValueError('Parámetros de tuberías finitos.')
    if min(c[k] for k in ['flow_kg_s','water_cp_J_kgK','conductance_W_mK','spacing_m'])<=0:raise ValueError('Caudal, capacidad, conductancia y separación positivos.')
    if not math.isfinite(c['flow_kg_s']*c['water_cp_J_kgK']):raise ValueError('Capacidad de transporte del agua fuera de rango.')
    if not 0<=c['start_h']<c['stop_h']<=8760:raise ValueError('Horario de tuberías: 0 ≤ inicio < fin ≤ 8760 h.')
    if not isinstance(c['levels_m'],list) or not 1<=len(c['levels_m'])<=12 or any(isinstance(z,bool) or not isinstance(z,(int,float)) or not math.isfinite(z) or not 0<z<p['L'][2] for z in c['levels_m']):raise ValueError('Cotas de tubería relativas a la base, dentro del hormigón.')
    if len(set(c['levels_m']))!=len(c['levels_m']):raise ValueError('Cotas de tubería repetidas.')
    if not isinstance(c['parameter_source'],str) or not 5<=len(c['parameter_source'])<=500:raise ValueError('Declarar procedencia de tuberías.')


class CircuitoTuberias:
    def __init__(self,ids,lengths,origin,config):
        self.config=dict(config);self.shape=ids.shape;self.dx=np.asarray(lengths)/ids.shape
        if config['spacing_m']<self.dx[1]:raise ValueError('Malla demasiado gruesa para separar las tuberías; refinar o aumentar separación.')
        self.origin=np.asarray(origin);self.paths=[];self.geometry=[];self.G=np.zeros(ids.shape)
        self.cdot=config['flow_kg_s']*config['water_cp_J_kgK']
        self.g=self.cdot*(-np.expm1(-config['conductance_W_mK']*self.dx[0]/self.cdot))
        ys=np.arange(config['spacing_m']/2,lengths[1],config['spacing_m'])
        rows=[int(y/self.dx[1]) for y in ys];zs=[int(z/self.dx[2]) for z in config['levels_m']]
        if len(set(rows))!=len(rows) or len(set(zs))!=len(zs):raise ValueError('Malla demasiado gruesa para separar las tuberías; refinar o aumentar separación.')
        for y,j in zip(ys,rows):
            for z,k in zip(config['levels_m'],zs):
                start=0
                while start<ids.shape[0]:
                    owner=ids[start,j,k];end=start+1
                    while end<ids.shape[0] and ids[end,j,k]==owner:end+=1
                    if owner>0:
                        indices=np.ravel_multi_index((np.arange(start,end),np.full(end-start,j),np.full(end-start,k)),ids.shape)
                        self.paths.append(indices);self.G.ravel()[indices]+=self.g
                        self.geometry.append(dict(pour_id=int(owner),length_m=float((end-start)*self.dx[0]),
                            start_xyz_m=(self.origin+[start*self.dx[0],y,z]).tolist(),end_xyz_m=(self.origin+[end*self.dx[0],y,z]).tolist()))
                    start=end
        if not self.paths:raise ValueError('Ninguna tubería intersecta la geometría voxelizada.')

    def enabled(self,t):return self.config['start_h']*3600<=t<self.config['stop_h']*3600

    def next_event(self,t):return min((h*3600 for h in (self.config['start_h'],self.config['stop_h']) if h*3600>t+1e-8),default=math.inf)

    def exchange(self,T,active,t):
        power=np.zeros(self.shape);outlets=[];inlet=self.config['inlet_C']
        if self.enabled(t):
            flat=T.ravel();mask=active.ravel();out=power.ravel()
            for path in self.paths:
                if not mask[path].all():continue
                water=inlet
                for i in path:
                    watts=self.g*(flat[i]-water)
                    out[i]+=watts;water+=watts/self.cdot
                outlets.append(water)
        water_power=self.cdot*sum(v-inlet for v in outlets)
        return power,dict(power_out_W=float(power.sum()),water_power_W=float(water_power),
            inlet_C=inlet,outlet_mean_C=float(np.mean(outlets)) if outlets else None,
            outlet_max_C=max(outlets,default=None),active_circuits=len(outlets),
            total_flow_kg_s=len(outlets)*self.config['flow_kg_s'])

    def metadata(self):
        return dict(config=self.config,circuits=self.geometry,total_length_m=sum(p['length_m'] for p in self.geometry),
            total_circuits=len(self.paths),model='Agua cuasiestacionaria por segmentos en serie; circuitos paralelos independientes, entrada prescrita.',
            equations='Tout=Tcell+(Tin-Tcell)*exp(-Ul*L/(mdot*cpw)); P=mdot*cpw*(Tout-Tin); hormigón recibe -P.',
            limitations='Conductancia efectiva subvoxel no calibrada; no resuelve gradiente radial, pared ni almacenamiento del agua. Volumen desplazado por tubos despreciado; extremos ajustados a la máscara voxelizada. Sin bomba/chiller modelados; entrada constante supone suministro acondicionado. Intercambio firmado: agua más caliente puede calentar hormigón.')
