"""MLS cuadrático de centros activos a puntos IFC. No modifica el solver.

Exacto para polinomios de grado <=2 si el stencil tiene rango completo.
Reconstrucción puntual NO equivale a AMR ni corrige el borde escalonado del FV.
"""
import numpy as np


def basis(x,degree):
    columns=[np.ones(len(x)),x[:,0],x[:,1],x[:,2]]
    if degree==2:columns += [x[:,0]**2,x[:,1]**2,x[:,2]**2,x[:,0]*x[:,1],x[:,0]*x[:,2],x[:,1]*x[:,2]]
    return np.array(columns).T


class Reconstruccion:
    def __init__(self,points,active,origin,spacing,cell_ids=None,point_ids=None,allow_partial=False):
        self.points=np.asarray(points,float);self.shape=active.shape;dx=np.asarray(spacing,float);origin=np.asarray(origin,float)
        self.origin=origin;self.dx=dx;self.details=[]
        stencils=[];weights=[];conditions=[];degrees=[];distances=[];radii=[];supported=[]
        offset_sets={radius:np.stack(np.meshgrid(*[np.arange(-radius,radius+1)]*3,indexing='ij'),axis=-1).reshape(-1,3) for radius in (2,4,6)}
        for point_number,point in enumerate(self.points):
            base=np.floor((point-origin)/dx).astype(int)
            solved=False
            for radius,offsets in offset_sets.items():
                indices=base+offsets
                valid=np.all((indices>=0)&(indices<np.array(active.shape)),axis=1)
                indices=indices[valid]
                indices=indices[active[tuple(indices.T)]]
                if cell_ids is not None:
                    if point_ids is None:raise ValueError('Identificar la vertida real de cada punto S25.')
                    indices=indices[np.asarray(cell_ids)[tuple(indices.T)]==point_ids[point_number]]
                if len(indices)<4:continue
                centers=origin+(indices+.5)*dx
                local=(centers-point)/dx
                distance=np.linalg.norm(local,axis=1)
                root_weight=1/np.sqrt(1+distance**2)
                for degree in (2,1):
                    A=basis(local,degree);B=A*root_weight[:,None]
                    if np.linalg.matrix_rank(B)<B.shape[1]:continue
                    cond=float(np.linalg.cond(B))
                    if cond>1e5:continue
                    # w^T A = e0^T. Pesos de evaluación, no un segundo solver.
                    target=np.zeros(B.shape[1]);target[0]=1
                    w=np.linalg.lstsq(B.T,target,rcond=1e-12)[0]*root_weight
                    solved=True;break
                if solved:break
            if not solved:
                if not allow_partial:raise ValueError('Stencil S25 singular: no se inventa una temperatura.')
                stencils.append(np.array([0]));weights.append(np.array([0.]));supported.append(False)
                centers=origin+(indices+.5)*dx
                rank=int(np.linalg.matrix_rank(basis((centers-point)/dx,1))) if len(indices) else 0
                span=np.ptp(centers,axis=0) if len(indices) else np.zeros(3)
                self.details.append(dict(supported=False,neighbors=len(indices),radius_cells=radius,
                    affine_rank=rank,coordinate_span_m=span.tolist(),
                    failure_reason='TOO_FEW_NEIGHBORS' if len(indices)<4 else 'COPLANAR_OR_COLLINEAR_CENTERS' if rank<4 else 'ILL_CONDITIONED'))
                continue
            stencils.append(np.ravel_multi_index(tuple(indices.T),active.shape));weights.append(w)
            supported.append(True)
            conditions.append(cond);degrees.append(degree);distances.append(float(np.min(np.linalg.norm(centers-point,axis=1))))
            radii.append(radius)
            self.details.append(dict(supported=True,neighbors=len(indices),radius_cells=radius,degree=degree,condition=cond,
                coordinate_span_m=np.ptp(centers,axis=0).tolist(),nearest_cell_m=distances[-1],
                weights_l1=float(np.sum(np.abs(w))),polynomial_reproduction_error=float(np.max(np.abs(w@A-target)))))
        # CSR sin padding: unos pocos stencils amplios no inflan todos los demás.
        self.indices=np.concatenate(stencils);self.weights=np.concatenate(weights)
        self.starts=np.r_[0,np.cumsum([len(s) for s in stencils])[:-1]]
        self.supported=np.asarray(supported,bool)
        self.diagnostics=dict(points=len(points),max_condition=max(conditions,default=None),linear_fallbacks=degrees.count(1),
                              unsupported_points=int((~self.supported).sum()),
                              nearest_cell_distance_max_m=max(distances,default=None),max_abs_weight=float(np.max(np.abs(self.weights))),
                              one_sided_by_point_pour=cell_ids is not None,
                              expanded_stencils=sum(r>2 for r in radii),max_stencil_radius_cells=max(radii,default=0),
                              method='weighted_quadratic_MLS_active_centers',boundary_constraints='NONE: condiciones de borde ya actúan en FV; no se inventa BC sobre una normal inclinada.')

    def evaluate(self,temperature):
        values=np.add.reduceat(np.asarray(temperature).ravel()[self.indices]*self.weights,self.starts)
        values[~self.supported]=np.nan
        return values

    def audit(self,index,temperature=None):
        detail=dict(self.details[index]);detail['point_xyz_m']=self.points[index].tolist()
        if not detail['supported']:return detail
        start=self.starts[index];end=self.starts[index+1] if index+1<len(self.starts) else len(self.indices)
        cells=self.indices[start:end];weights=self.weights[start:end]
        ijk=np.array(np.unravel_index(cells,self.shape)).T;centers=self.origin+(ijk+.5)*self.dx
        detail['neighbors_ijk']=ijk.tolist();detail['neighbors_xyz_m']=centers.tolist();detail['weights']=weights.tolist()
        if temperature is not None:
            T=np.asarray(temperature).ravel()[cells];local=(centers-self.points[index])/self.dx
            A=basis(local,detail['degree']);root=1/np.sqrt(1+np.sum(local**2,axis=1))
            coefficients=np.linalg.lstsq(A*root[:,None],T*root,rcond=1e-12)[0]
            residual=A@coefficients-T
            detail.update(neighbors_temperature_C=T.tolist(),fit_rmse_C=float(np.sqrt(np.mean(residual**2))),
                          fit_max_residual_C=float(np.max(np.abs(residual))),predicted_C=float(weights@T))
        return detail
