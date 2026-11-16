import numpy as np
import pytest
from therma.auditoria_geometrica import mas_cercano,detalle_distancia,distancia_aristas
from therma.criterio_s25 import evaluar_testigos
from therma.superficies_ifc import SuperficiesIFC
from therma.reconstruccion_s25 import Reconstruccion
from test_s25_ifc_resolucion import cube
from casos_frontera_staircase import referencia_plano,gradiente_pronunciado


def test_distance_to_triangle_plane_edge_vertex():
    tri=np.array([[[0,0,0],[1,0,0],[0,1,0]]],float)
    for p,expected in [([.2,.2,.025],.025),([2,0,0],1.),([1,1,0],np.sqrt(.5))]:
        d,_=mas_cercano(p,tri)
        assert d[0]==pytest.approx(expected)


def test_normal_offset_is_not_always_nearest_surface_distance():
    g=SuperficiesIFC([cube()],spacing=2.)
    point=np.array([.025,.01,.5]);surface=np.array([0,.01,.5]);normal=np.array([-1,0,0])
    detail=detalle_distancia(point,surface,normal,g,(1,))
    assert detail['normal_offset_m']==pytest.approx(.025)
    assert detail['nearest_exterior_distance_m']==pytest.approx(.01)


def test_internal_interface_excluded_from_closest_surface():
    g=SuperficiesIFC([cube(),cube(2,(0,0,1))],spacing=2.)
    p=np.array([.5,.5,1.01])
    d=detalle_distancia(p,[0,.5,1.01],[-1,0,0],g,(1,2))
    assert d['nearest_exterior_distance_m']==pytest.approx(.5)


def test_feature_edges_ignore_coplanar_triangulation_diagonal():
    e=distancia_aristas(np.array([.5,.5,0]),cube())
    assert e['distance_to_feature_edge_m']==pytest.approx(.5)


def test_rank_three_cannot_identify_normal_gradient_from_cell_data():
    mask=np.zeros((8,8,8),bool);mask[:,:,3]=True
    point=[.4,.4,.45]
    r=Reconstruccion([point],mask,[0,0,0],[.125]*3,allow_partial=True)
    assert r.details[0]['failure_reason']=='COPLANAR_OR_COLLINEAR_CENTERS'
    assert r.details[0]['neighbors']>4 and r.details[0]['affine_rank']==3
    zcenter=(3+.5)*.125
    # Dos campos afines dan los mismos valores en todos los vecinos coplanares.
    assert 20+100*(zcenter-zcenter)==20
    assert abs((20+100*(point[2]-zcenter))-20)>1


def test_fit_residual_is_not_an_error_bound():
    n=8;xyz=np.stack(np.meshgrid(*[(np.arange(n)+.5)/n]*3,indexing='ij'),axis=-1)
    r=Reconstruccion([[.025,.4,.5]],np.ones((n,)*3,bool),[0,0,0],[1/n]*3)
    field=20+xyz[...,0]+xyz[...,1]**2
    audit=r.audit(0,field)
    assert audit['fit_rmse_C']<1e-10 and audit['polynomial_reproduction_error']<1e-10
    assert audit['weights_l1']>=1-1e-10
    assert evaluar_testigos([dict(delta_C=40.,validated=False,error_bound_C=None)])['I_Delta'] is None


@pytest.mark.parametrize('delta,error,expected',[(21,0.5,True),(20.1,.1,None),(20,.2,None),(19,.1,None)])
def test_one_validated_witness_can_reject_without_full_coverage(delta,error,expected):
    result=evaluar_testigos([dict(id='known',delta_C=delta,error_bound_C=error,validated=True)],full_surface_coverage=False)
    assert result['I_Delta'] is expected


def test_pass_requires_global_validated_bound():
    assert evaluar_testigos([],True,19.9,False)['I_Delta'] is None
    assert evaluar_testigos([],False,19.9,True)['I_Delta'] is None
    assert evaluar_testigos([],True,20.,True)['I_Delta'] is False


def test_robin_staircase_error_exists_despite_exact_reconstruction():
    aligned=referencia_plano(24,False)
    stair=referencia_plano(24,True)
    corrected=referencia_plano(24,True,True)
    assert aligned['total_error_C']<1e-10
    assert stair['reconstruction_only_error_C']<1e-10
    assert stair['total_error_C']>.1 and stair['staircase_area_ratio']>1.3
    assert corrected['total_error_C']<stair['total_error_C']
    assert abs(stair['energy_residual_J'])<1e-8


def test_underresolved_sharp_gradient_can_hide_exceedance():
    rows=gradiente_pronunciado()
    assert rows[0]['true_delta_C']>20 and rows[0]['estimated_delta_C']<20
    assert rows[-1]['absolute_error_C']<rows[0]['absolute_error_C']/50

def test_viewer_critical_pair_requires_exact_frame_and_matching_hot_temperature():
    import subprocess,shutil,json
    code="""const D=require('./panel/visordatos.js');const r={n:[2,2,2],dx:[1,1,1],config:{origin:[0,0,0]},frameTimes:[0,5],fields:[Array(8).fill(20),Array(8).fill(30)],metadata:{s25_ifc:{critical_pair:{time_s:5,hot:{ijk:[1,0,1],temperature_C:30}}}}};
const c=D.criticalPair(r);if(c.frame!==1||c.hot!==5)throw Error('order/time');
r.metadata.s25_ifc.critical_pair.time_s=4.9;if(D.criticalPair(r)!==null)throw Error('nearest forbidden');
r.metadata.s25_ifc.critical_pair.time_s=5;r.metadata.s25_ifc.critical_pair.hot.temperature_C=40;
let caught=false;try{D.criticalPair(r)}catch(e){caught=true}if(!caught)throw Error('incompatible accepted');console.log('ok');"""
    assert subprocess.run([shutil.which('node'),'-e',code],capture_output=True,text=True,check=True).stdout.strip()=='ok'
