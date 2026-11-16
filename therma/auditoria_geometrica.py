"""Distancias euclídeas a triángulos; no confundir offset normal con distancia mínima."""
import numpy as np


def mas_cercano(point,triangles):
    triangles=np.asarray(triangles,float);p=np.asarray(point,float)
    a,b,c=triangles[:,0],triangles[:,1],triangles[:,2]
    u=b-a;v=c-a;normal=np.cross(u,v);norm=np.linalg.norm(normal,axis=1)
    if np.any(norm<=1e-12):raise ValueError('Triángulo degenerado.')
    normal/=norm[:,None]
    projection=p-np.einsum('ij,ij->i',p-a,normal)[:,None]*normal
    w=projection-a
    uu=np.einsum('ij,ij->i',u,u);uv=np.einsum('ij,ij->i',u,v);vv=np.einsum('ij,ij->i',v,v)
    wu=np.einsum('ij,ij->i',w,u);wv=np.einsum('ij,ij->i',w,v);den=uu*vv-uv*uv
    s=(vv*wu-uv*wv)/den;t=(uu*wv-uv*wu)/den
    inside=(s>=-1e-12)&(t>=-1e-12)&(s+t<=1+1e-12)
    candidates=[np.where(inside[:,None],projection,np.inf)]
    for start,end in ((a,b),(b,c),(c,a)):
        edge=end-start;alpha=np.clip(np.einsum('ij,ij->i',p-start,edge)/np.einsum('ij,ij->i',edge,edge),0,1)
        candidates.append(start+alpha[:,None]*edge)
    candidates=np.stack(candidates,axis=1)
    distances=np.sum((candidates-p)**2,axis=2)
    choice=np.argmin(distances,axis=1);q=candidates[np.arange(len(triangles)),choice]
    return np.linalg.norm(q-p,axis=1),q


def detalle_distancia(point,surface,normal,geometry,active_ids):
    # Filtrar puntos proyectados sobre interfaces internas antes del mínimo.
    best=None
    for solid in geometry.solids:
        ident=int(solid['VertidaID'])
        if ident not in active_ids:continue
        distances,closest=mas_cercano(point,solid['triangulos'])
        for face in np.argsort(distances):
            if best and distances[face]>best['nearest_exterior_distance_m']+1e-12:break
            tri=solid['triangulos'][face];n=np.cross(tri[1]-tri[0],tri[2]-tri[0]);n/=np.linalg.norm(n)
            if geometry.inside([closest[face]+n*1e-5],(ident,))[0]:n=-n
            if geometry.inside([closest[face]+n*1e-5],active_ids)[0]:continue
            best=dict(nearest_exterior_distance_m=float(distances[face]),nearest_surface_xyz_m=closest[face].tolist(),
                      nearest_triangle_id=int(face),nearest_surface_pour_id=ident)
            break
    if best is None:raise ValueError('No se encontró superficie exterior cercana.')
    best.update(normal_offset_m=float(np.linalg.norm(np.asarray(point)-surface)),
                signed_normal_offset_m=float(np.dot(np.asarray(surface)-point,normal)))
    return best


def distancia_aristas(point,solid,angle_deg=1.):
    """Aristas entre planos distintos; descarta diagonales coplanares de triangulación."""
    edges={}
    for tri in solid['triangulos']:
        n=np.cross(tri[1]-tri[0],tri[2]-tri[0]);n/=np.linalg.norm(n)
        for i,j in ((0,1),(1,2),(2,0)):
            key=tuple(sorted((tuple(np.round(tri[i],8)),tuple(np.round(tri[j],8)))))
            edges.setdefault(key,[]).append(n)
    features=[]
    for key,normals in edges.items():
        if len(normals)!=2 or abs(float(np.dot(normals[0],normals[1])))<np.cos(np.deg2rad(angle_deg)):
            features.append(key)
    if not features:return None
    lines=np.asarray(features);a,b=lines[:,0],lines[:,1];v=b-a
    t=np.clip(np.einsum('ij,ij->i',np.asarray(point)-a,v)/np.einsum('ij,ij->i',v,v),0,1)
    distances=np.linalg.norm(a+t[:,None]*v-point,axis=1);j=int(np.argmin(distances))
    return dict(distance_to_feature_edge_m=float(distances[j]),edge_xyz_m=lines[j].tolist(),angle_threshold_deg=angle_deg)
