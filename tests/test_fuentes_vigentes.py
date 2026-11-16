import hashlib
import json
from pathlib import Path
import pytest
from therma.fuentes_vigentes import VIGENTE_SHA256,RETIRADA_PINN_SHA256
from therma.fuente_tabulada import FuenteTabulada
from ejecutar_lotes_defensa import build_catalog,audit_sources
from servidor_therma import catalogo_simulaciones

ROOT=Path(__file__).resolve().parents[1]


def test_current_original_and_alias_have_identical_bytes():
    current=(ROOT/'data/hydration/source_terms.txt').read_bytes()
    assert hashlib.sha256(current).hexdigest()==VIGENTE_SHA256
    assert current==(ROOT/'data/hydration/source_terms_fv_tikhonov.txt').read_bytes()
    withdrawn=(ROOT/'data/hydration/retiradas/source_terms_pinn_obsoleto.txt').read_bytes()
    assert hashlib.sha256(withdrawn).hexdigest()==RETIRADA_PINN_SHA256


def test_retired_embedded_e12_curve_is_rejected_and_current_is_admitted():
    historical=json.loads((ROOT/'docs/e12/evidencia/config.json').read_text(encoding='utf-8'))
    with pytest.raises(ValueError,match='retirada'):
        FuenteTabulada(historical['construction']['curve'],2400,900)
    current=build_catalog()
    for source in current['sources']:
        assert source['curve']['raw_sha256']==VIGENTE_SHA256
        assert FuenteTabulada(source['curve'],2476,1023).energia_volumetrica(86400)>0
    with pytest.raises(ValueError,match='retirado'):build_catalog('pinn')


def test_audit_keeps_retired_history_separate_from_active_source():
    audit=audit_sources()
    assert audit[0]['status']=='RETIRED_INVALID_USER_DATA'
    assert audit[1]['status']=='CURRENT_USER_PROVIDED'
    assert audit[1]['curves'][0]['energy_MJ_m3']==pytest.approx(88.148347776)


def test_catalog_hides_runs_with_withdrawn_source(tmp_path):
    for i,digest in enumerate((RETIRADA_PINN_SHA256,VIGENTE_SHA256)):
        ident=str(i)*32;folder=tmp_path/ident;folder.mkdir()
        (folder/'fields.bin').write_bytes(b'field')
        metadata=dict(status='COMPLETED',simulation_id=ident,
            config=dict(geometry='foundation',dim=3,days=14,construction=dict(curve=dict(raw_sha256=digest))),
            geometry=dict(lengths_m=[18,18,3.3]))
        (folder/'metadata.json').write_text(json.dumps(metadata),encoding='utf-8')
    assert [r['simulation_id'] for r in catalogo_simulaciones(tmp_path)]==['1'*32]


def test_method_comparison_is_now_read_only_audit(tmp_path):
    from sensibilidad_fuentes_defensa import main
    main(tmp_path)
    report=json.loads((tmp_path/'estado_fuentes.json').read_text(encoding='utf-8'))
    assert report['status']=='PINN_RETIRED_NO_THERMAL_COMPARISON_RUN'
    assert not (tmp_path/'comparacion_metodos.csv').exists()
