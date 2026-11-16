from pathlib import Path
import json
import shutil
import subprocess
import numpy as np
import pytest
from therma.superficies_ifc import SuperficiesIFC
from therma.reconstruccion_s25 import Reconstruccion
from therma.resolucion import estimar
from termico_cartesiano import TermicoCartesiano


def cube(ident=1,offset=(0,0,0),transform=None):
    v=np.array([[0,0,0],[1,0,0],[1,1,0],[0,1,0],[0,0,1],[1,0,1],[1,1,1],[0,1,1]],float)
    if transform is not None:v=v@np.array(transform).T
    v+=offset
    faces=np.array([[0,2,1],[0,3,2],[4,5,6],[4,6,7],[0,1,5],[0,5,4],[1,2,6],[1,6,5],[2,3,7],[2,7,6],[3,0,4],[3,4,7]])
    return dict(VertidaID=ident,vertices=v,triangulos=v[faces],guid='g'+str(ident))


@pytest.mark.parametrize('step,allowed',[(.5,True),(.25,True),(.125,False),(.05,False),(.025,False)])
def test_preflight_blocks_before_allocation(step,allowed):
    r=estimar([18,18,3.3],[step]*3,487.)
    assert r['allowed']==allowed
    assert r['volume_error'] is None
    assert r['occupied_cells_estimate']<=r['total_cells']
    if step==.025:assert r['total_cells']==68428800 and r['memory_bytes_estimate']>50*1024**3
    assert r['dt_sufficient_s']>0


def test_resource_estimates_javascript_python_parity():
    node=shutil.which('node')
    if not node:pytest.skip('Node ausente')
    for step in (.5,.25,.025):
        py=estimar([18,18,3.3],[step]*3,487.)
        script=f"const M=require('./panel/resolucion_modelo.js');console.log(JSON.stringify(M.estimate([18,18,3.3],[{step},{step},{step}],487)))"
        js=json.loads(subprocess.check_output([node,'-e',script],text=True))
        for key in ('shape','total_cells','memory_bytes_estimate','allowed'):assert js[key]==py[key]
        assert js['dt_sufficient_s']==pytest.approx(py['dt_sufficient_s'])


@pytest.mark.parametrize('transform',[None,[[1,0,0],[0,1,0],[.35,.2,1]]])
def test_surface_normal_offset_planar_and_inclined(transform):
    solid=cube(transform=transform);surface=SuperficiesIFC([solid],spacing=2.)
    samples=surface.at((1,))
    delta=samples['surface']-samples['points']
    np.testing.assert_allclose(np.linalg.norm(delta,axis=1),.025,atol=1e-13)
    np.testing.assert_allclose(delta,.025*samples['outward'],atol=1e-13)
    assert surface.inside(samples['points'],(1,)).all()
    assert set(samples['region'])==({'air','soil'} if transform is None else {'air'})
    assert np.any(samples['outward'][:,2]<-.9)


def test_interfaces_disappear_with_pour_activation():
    surface=SuperficiesIFC([cube(),cube(2,(0,0,1))],spacing=2.)
    first=surface.at((1,));both=surface.at((1,2))
    assert len(first['points'])==12 and len(both['points'])==20
    assert both['excluded_internal']==4
    assert not np.any((np.abs(both['surface'][:,2]-1)<1e-10)&(np.abs(both['outward'][:,2])>.99))
    assert set(first['owner'])=={1}


def cylinder(n=32):
    angles=np.arange(n)*2*np.pi/n
    ring=np.c_[np.cos(angles),np.sin(angles)]
    v=np.vstack([np.c_[ring,np.zeros(n)],np.c_[ring,np.ones(n)],[0,0,0],[0,0,1]])
    faces=[]
    for i in range(n):
        j=(i+1)%n
        faces += [[i,j,j+n],[i,j+n,i+n],[2*n,j,i],[2*n+1,i+n,j+n]]
    return dict(VertidaID=1,vertices=v,triangulos=v[np.array(faces)],guid='cylinder')


def test_curved_surface_faceting_error_separate_from_depth():
    surf=SuperficiesIFC([cylinder()],spacing=2.)
    a=surf.at((1,));side=np.abs(a['outward'][:,2])<.1
    depth_in_true_cylinder=1-np.linalg.norm(a['points'][side,:2],axis=1)
    sagitta=1-np.cos(np.pi/32)
    assert np.max(np.abs(depth_in_true_cylinder-.025))<sagitta
    assert np.max(np.abs(depth_in_true_cylinder-.025))>0  # faceta no es círculo exacto


@pytest.mark.parametrize('point',[[.025,.3,.6],[.025,.025,.025],[.7,.7,.975]])
def test_quadratic_and_linear_reconstruction_at_edges_corners(point):
    n=np.array([8,9,10]);dx=1/n
    xyz=np.stack(np.meshgrid(*[(np.arange(k)+.5)/k for k in n],indexing='ij'),axis=-1)
    reconstruction=Reconstruccion([point],np.ones(n,bool),[0,0,0],dx)
    def f(v):return 20+v[...,0]+2*v[...,1]-v[...,2]+v[...,0]**2-.5*v[...,2]**2+v[...,0]*v[...,1]
    assert reconstruction.evaluate(f(xyz))[0]==pytest.approx(f(np.array(point)),abs=1e-10)
    assert reconstruction.diagnostics['linear_fallbacks']==0


def test_inactive_centers_never_contribute():
    active=np.ones((8,8,8),bool);active[:,:,4:]=False
    a=Reconstruccion([[.2,.2,.475]],active,[0,0,0],[.125]*3)
    T=np.full(active.shape,20.);T[~active]=1e9
    assert a.evaluate(T)[0]==pytest.approx(20,abs=1e-10)


def test_steady_neumann_and_dirichlet_field_known_solution():
    for types in ('N','D'):
        borders={}
        if types=='N':borders={'x-':dict(tipo='neumann',flujo_saliente_W_m2=-10.),'x+':dict(tipo='neumann',flujo_saliente_W_m2=10.)}
        else:borders={'x-':dict(tipo='dirichlet',temperatura_C=30.),'x+':dict(tipo='dirichlet',temperatura_C=20.)}
        m=TermicoCartesiano((8,8,8),(1,1,1),k=1,rho=1,cp=1,bordes=borders)
        T=30-10*m.coordenadas[0]
        out=m.resolver(T,.01,.5*m.dt_max)['T']
        np.testing.assert_allclose(out,T,atol=1e-10)
        r=Reconstruccion([[.025,.3,.4]],m.activo,[0,0,0],m.dx)
        assert r.evaluate(out)[0]==pytest.approx(29.75,abs=1e-10)


def eigenvalue(beta):
    lo=0.;hi=np.pi-1e-10
    for _ in range(80):
        mid=(lo+hi)/2
        if mid*np.tan(mid/2)>beta:hi=mid
        else:lo=mid
    return (lo+hi)/2


def transient_errors(kind,details=False):
    points=SuperficiesIFC([cube()],spacing=2.).at((1,))['points']
    errors=[];rows=[];t=.01
    for n in (6,10,16):
        if kind=='D':
            borders={a+s:dict(tipo='dirichlet',temperatura_C=20.) for a in 'xyz' for s in '-+'}
            mu=np.pi;basis=lambda x:np.sin(mu*x)
        else:
            h=10.;R=.2;mu=eigenvalue(1/(R+1/h));basis=lambda x:np.cos(mu*(x-.5))
            borders={a+s:dict(tipo='robin',temperatura_C=20.,h_W_m2K=h,R_m2K_W=R) for a in 'xyz' for s in '-+'}
        m=TermicoCartesiano((n,)*3,(1,)*3,k=1,rho=1,cp=1,bordes=borders)
        initial=20+5*np.prod([basis(x) for x in m.coordenadas],axis=0)
        T=m.resolver(initial,t,.2*m.dt_max)['T']
        exact=20+5*np.prod(basis(points),axis=1)*np.exp(-3*mu*mu*t)
        r=Reconstruccion(points,m.activo,[0,0,0],m.dx)
        errors.append(float(np.max(np.abs(r.evaluate(T)-exact))))
        exact_centers=20+5*np.prod([basis(x) for x in m.coordenadas],axis=0)*np.exp(-3*mu*mu*t)
        rows.append(dict(boundary=kind,n=n,dx_m=1/n,total_error_C=errors[-1],
                         reconstruction_only_error_C=float(np.max(np.abs(r.evaluate(exact_centers)-exact))),
                         propagated_solver_error_C=float(np.max(np.abs(r.evaluate(T-exact_centers))))))
    return rows if details else errors


@pytest.mark.parametrize('kind',['D','R'])
def test_3d_transient_reconstruction_three_meshes(kind):
    errors=transient_errors(kind)
    assert errors[2]<errors[1]<errors[0]


def test_singular_stencil_rejected():
    active=np.zeros((6,6,6),bool);active[:,0,0]=True
    with pytest.raises(ValueError):Reconstruccion([[.1,.01,.01]],active,[0,0,0],[1/6]*3)


def test_soil_contact_reconstruction_exact_linear_steady_solution():
    k=2.;R=.05+1/1.5;slope=(20-8)/(1+k*R)
    m=TermicoCartesiano((8,8,8),(1,1,1),k=k,rho=1,cp=1,bordes={
        'z-':dict(tipo='robin',temperatura_C=8.,h_W_m2K=1.5,R_m2K_W=.05),
        'z+':dict(tipo='dirichlet',temperatura_C=20.)})
    initial=8+k*slope*R+slope*m.coordenadas[2]
    T=m.resolver(initial,.01,.2*m.dt_max)['T']
    np.testing.assert_allclose(T,initial,atol=1e-10)
    r=Reconstruccion([[.4,.4,.025]],m.activo,[0,0,0],m.dx)
    assert r.evaluate(T)[0]==pytest.approx(8+k*slope*R+slope*.025,abs=1e-10)


@pytest.mark.parametrize('solid',[cube(transform=[[1,0,0],[0,1,0],[.35,.2,1]]),cylinder()])
def test_polynomial_temperature_on_inclined_and_curved_ifc(solid):
    g=SuperficiesIFC([solid],spacing=2.)
    lo=solid['vertices'].min(0);L=solid['vertices'].max(0)-lo;n=np.array([12]*3);dx=L/n
    xyz=np.stack(np.meshgrid(*[lo[a]+(np.arange(n[a])+.5)*dx[a] for a in range(3)],indexing='ij'),axis=-1)
    active=g.inside(xyz.reshape(-1,3),(1,)).reshape(tuple(n))
    points=g.at((1,))['points'];r=Reconstruccion(points,active,lo,dx)
    f=lambda x:20+x[...,0]+x[...,1]**2-.3*x[...,2]
    np.testing.assert_allclose(r.evaluate(f(xyz)),f(points),atol=1e-10)


def test_cancel_stops_backend_instead_of_only_stopping_browser(tmp_path,monkeypatch):
    import time
    from threading import Event
    import servidor_therma as module
    started=Event()
    def fake(config,ident,folder,progress,observer):
        started.set()
        while True:
            observer(None,None,None);time.sleep(.005)
    monkeypatch.setattr(module,'ejecutar',fake)
    server=module.Servidor(('127.0.0.1',0),tmp_path)
    try:
        ident=server.enviar({})
        assert started.wait(2)
        assert server.cancelar(ident)['cancel_requested']
        deadline=time.monotonic()+2
        while server.jobs[ident]['status']=='RUNNING' and time.monotonic()<deadline:time.sleep(.01)
        assert server.jobs[ident]['status']=='CANCELLED'
        assert 'metadata_url' not in server.jobs[ident]
    finally:server.server_close()


def test_mesh_study_skips_excessive_resolutions_without_solver(tmp_path,monkeypatch):
    import therma.convergencia as module
    from test_construccion import config
    from therma.ejecutar import validar
    def forbidden(*args,**kwargs):raise AssertionError('No generar grilla grande')
    monkeypatch.setattr(module,'ejecutar',forbidden)
    result=module.ejecutar_estudio(validar(config()),[.125,.05,.025],tmp_path)
    assert all(row['status']=='SKIPPED_RESOURCE' for row in result['rows'])
    assert all('Tmax_C' not in row for row in result['rows'])
    assert (tmp_path/'mesh_study.png').is_file()


def test_backend_rejects_expensive_step_before_ifc_allocation(monkeypatch):
    import therma.ejecutar as module
    from test_construccion import config
    def forbidden(*args):raise AssertionError('No debe voxelizar un cálculo ya excesivo')
    monkeypatch.setattr(module,'ifc_actual',forbidden)
    p=config();p.update(meshIndex=2,n=[72,72,14],dtMode='manual',dt=1.,days=14.)
    with pytest.raises(ValueError,match='Costo excesivo'):module.validar(p)


def test_ifc_s25_observer_preserves_fields_energy_and_not_validated(tmp_path):
    from test_construccion import config
    from therma.ejecutar import ejecutar
    p=config();p['days']=2.2
    baseline=ejecutar(p,'baseline',tmp_path/'baseline')
    p['s25']=dict(method='ifc_mls',depth_m=.025,surface_spacing_m=1.5)
    inspected=ejecutar(p,'inspected',tmp_path/'inspected')
    with np.load(tmp_path/'baseline/campos.npz') as a,np.load(tmp_path/'inspected/campos.npz') as b:
        for i,t in enumerate(a['tiempo_s']):
            j=list(b['tiempo_s']).index(t)
            np.testing.assert_array_equal(a['T_C'][i],b['T_C'][j])
            np.testing.assert_array_equal(a['active'][i],b['active'][j])
        assert inspected['s25_ifc']['critical_pair']['time_s'] in b['tiempo_s']
    assert baseline['metrics']['energy_residual_relative']==inspected['metrics']['energy_residual_relative']
    assert inspected['s25_ifc']['validation']=='NOT VALIDATED'
    assert inspected['validity']['project_deltaT_25mm']=='NOT EVALUATED'
    assert len(inspected['s25_ifc']['stages'])==3
    h=inspected['s25_ifc']['history']
    assert all(abs(r['DeltaT_estimate_C']-(r['Tmax_C']-r['Tmin_S25_estimate_C']))<1e-12 for r in h)


def test_new_pour_one_sided_reconstruction_does_not_mix_hot_neighbors():
    ids=np.ones((8,8,8),int);ids[:,:,4:]=2
    T=np.full(ids.shape,50.);T[ids==2]=18.
    r=Reconstruccion([[.4,.4,.525]],np.ones(ids.shape,bool),[0,0,0],[.125]*3,cell_ids=ids,point_ids=[2])
    assert r.evaluate(T)[0]==pytest.approx(18,abs=1e-10)
    assert r.diagnostics['one_sided_by_point_pour']


def test_unsupported_surface_points_remain_unknown_not_invented():
    active=np.zeros((6,6,6),bool);active[:,0,0]=True
    r=Reconstruccion([[.1,.01,.01]],active,[0,0,0],[1/6]*3,allow_partial=True)
    assert np.isnan(r.evaluate(np.full(active.shape,20.))[0])
    assert r.diagnostics['unsupported_points']==1
