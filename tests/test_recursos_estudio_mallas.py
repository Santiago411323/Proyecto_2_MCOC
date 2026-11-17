from therma.resolucion import estimar


def test_malla_del_estudio_es_acotada_y_aumentar_frames_activa_guardia():
    inputs=dict(longitudes=[18,18,3.3],pasos=[18/84,18/84,3.3/48],volumen_ifc=487.0695,
                k=2,rho=2476,cp=1023,days=42,dt=900)
    study=estimar(**inputs,frames=40)
    assert study['shape']==[84,84,48]
    assert study['allowed']
    assert study['memory_bytes_estimate']<1024**3
    larger=estimar([18,18,3.3],[.18,.18,.055],487.0695,
                   k=2,rho=2476,cp=1023,days=42,dt=900,frames=100)
    assert not larger['allowed']
    assert any('memoria' in r.lower() for r in larger['reasons'])


def test_refinamiento_xyz_cabe_con_salida_acotada_pero_no_sin_limite():
    study=estimar([18,18,3.3],[.18,.18,.055],487.0695,
                  k=2,rho=2476,cp=1023,days=42,dt=1200,frames=40)
    assert study['shape']==[100,100,60]
    assert study['allowed']
    assert study['memory_bytes_estimate']<1536*1024**2
    bigger=estimar([18,18,3.3],[.15,.15,.05],487.0695,days=42,dt=1200,frames=40)
    assert not bigger['allowed']


def test_malla_completa_25_mm_sigue_bloqueada():
    result=estimar([18,18,3.3],[.025]*3,487.0695,days=42,dt=900)
    assert not result['allowed']
    assert result['total_cells']>60_000_000
