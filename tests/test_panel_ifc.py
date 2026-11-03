import json
import re
from pathlib import Path
import numpy as np
from panel.exportar_ifc import datos_ifc
from voxelizar import cargar_geometria

BASE = Path(__file__).resolve().parents[1]


def test_exportacion_preserva_mallas_y_tres_capas():
    datos = datos_ifc(BASE/'modelo_e02.ifc')
    originales = sorted(cargar_geometria(BASE/'modelo_e02.ifc'), key=lambda s: s['VertidaID'])
    assert len(datos['capas']) == 3
    assert [c['id'] for c in datos['capas']] == [1, 2, 3]
    for capa, original in zip(datos['capas'], originales):
        assert capa['guid'] == original['guid']
        np.testing.assert_allclose(capa['triangulos'], original['triangulos'], atol=5.1e-7)
    np.testing.assert_allclose(np.subtract(datos['max'], datos['min']), [18, 18, 3.3])


def test_html_incluye_ifc_actual_y_separa_resultados_termicos():
    html = (BASE/'panel_termico.html').read_text(encoding='utf-8')
    contenido = re.search(r'<script id="foundation-data" type="application/json">(.*?)</script>', html, re.S).group(1)
    datos = json.loads(contenido)
    assert datos['sha256'] == datos_ifc(BASE/'modelo_e02.ifc')['sha256']
    assert 'Fundación conectada al laboratorio térmico.' in html
    assert '/*__IFC_DATA__*/' not in html


def test_mallas_preservan_tres_capas_y_volumen_aproximado():
    datos = datos_ifc(BASE/'modelo_e02.ifc')
    v = sum(c['volumen_m3'] for c in datos['capas'])
    for m in datos['mallas']:
        assert len(m['ids']) == np.prod(m['n'])
        assert set(m['ids']) == {0, 1, 2, 3}
        assert abs(m['volumen_m3']/v-1) < .08
