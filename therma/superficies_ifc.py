"""Puntos S25 de TRIÁNGULOS IFC, no de caras del voxel.

Cuadratura por centroides de subtriángulos; aristas usan límites por cara,
no una normal promedio inventada. No certifica cobertura continua de S25.
"""
from functools import lru_cache
from pathlib import Path
import numpy as np
from voxelizar import cargar_geometria, dentro_malla


def subdividir(triangle,spacing):
    pending=[np.asarray(triangle,float)]
    result=[]
    while pending:
        t=pending.pop()
        pairs=((0,1,2),(1,2,0),(2,0,1))
        a,b,c=max(pairs,key=lambda q:np.linalg.norm(t[q[0]]-t[q[1]]))
        if np.linalg.norm(t[a]-t[b])<=spacing*(1+1e-12):result.append(t)
        else:
            mid=(t[a]+t[b])/2
            pending += [np.array([t[a],mid,t[c]]),np.array([mid,t[b],t[c]])]
        if len(pending)+len(result)>30000:raise ValueError('Cuadratura superficial demasiado grande.')
    return result


class SuperficiesIFC:
    def __init__(self,solids,spacing=1.5,depth=.025,max_points=20000):
        if not .2<=spacing<=5 or depth!=.025:raise ValueError('S25 fijo 0,025 m y separación superficial 0,2–5 m.')
        self.solids=solids;self.depth=depth;self.spacing=spacing;self.cache={}
        self.minimum=np.concatenate([s['vertices'] for s in solids]).min(0)
        centers=[];normals=[];owners=[];triangle_ids=[];areas=[]
        for solid in solids:
            triangles=solid['triangulos']
            raw=np.cross(triangles[:,1]-triangles[:,0],triangles[:,2]-triangles[:,0])
            lengths=np.linalg.norm(raw,axis=1)
            good=lengths>1e-12
            if not good.all():raise ValueError('Triángulo degenerado en superficie IFC.')
            n=raw/lengths[:,None];c=triangles.mean(axis=1)
            plus=dentro_malla(c+n*1e-5,triangles);minus=dentro_malla(c-n*1e-5,triangles)
            if np.any(plus==minus):raise ValueError('No se pudo orientar inequívocamente una cara IFC.')
            n[plus]*=-1
            for face,t in enumerate(triangles):
                parts=subdividir(t,spacing)
                for part in parts:
                    centers.append(part.mean(0));normals.append(n[face]);owners.append(int(solid['VertidaID']));triangle_ids.append(face)
                    areas.append(np.linalg.norm(np.cross(part[1]-part[0],part[2]-part[0]))/2)
                if len(centers)>max_points:raise ValueError(f'Más de {max_points} puntos S25; aumenta separación superficial.')
        self.surface=np.array(centers);self.outward=np.array(normals);self.owner=np.array(owners)
        self.triangle_ids=np.array(triangle_ids);self.area=np.array(areas)
        self.points=self.surface-depth*self.outward

    def inside(self,points,ids):
        points=np.asarray(points,dtype=float)
        result=np.zeros(len(points),bool)
        for solid in self.solids:
            if int(solid['VertidaID']) in ids:result |= dentro_malla(points,solid['triangulos'])
        return result

    def at(self,active_ids):
        key=tuple(sorted(active_ids))
        if key in self.cache:return self.cache[key]
        owner_active=np.isin(self.owner,key)
        indices=np.flatnonzero(owner_active)
        outside_probe=self.surface[indices]+1e-5*self.outward[indices]
        exposed=~self.inside(outside_probe,key)
        indices=indices[exposed]
        valid=self.inside(self.points[indices],key)
        rejected=int((~valid).sum())
        indices=indices[valid]
        if not len(indices):raise ValueError('Sin puntos S25 geométricamente interiores en este estado.')
        point_owner=np.zeros(len(indices),int)
        for solid in self.solids:
            ident=int(solid['VertidaID'])
            if ident in key:point_owner[dentro_malla(self.points[indices],solid['triangulos'])]=ident
        if not np.all(point_owner>0):raise ValueError('No se pudo identificar el hormigón que contiene un punto S25.')
        basal=(np.abs(self.surface[indices,2]-self.minimum[2])<1e-7)&(self.outward[indices,2]<-.999999)
        result=dict(points=self.points[indices],surface=self.surface[indices],outward=self.outward[indices],
                    owner=self.owner[indices],point_owner=point_owner,triangle_id=self.triangle_ids[indices],area=self.area[indices],
                    region=np.where(basal,'soil','air'),indices=indices,rejected_not_in_active_concrete=rejected,
                    excluded_internal=int(owner_active.sum()-exposed.sum()),sampling_spacing_m=self.spacing,depth_m=self.depth)
        self.cache[key]=result
        return result


@lru_cache(maxsize=4)
def cargar_superficies(path,mtime,spacing=1.5):
    return SuperficiesIFC(cargar_geometria(Path(path)),spacing)
