import copy

import pytest

from therma.hielo import balance, preview, reference


BASE = dict(mode='target', value=8., reference_C=18., water_C=20., ice_C=0., water_kg_m3=160.)


def test_balance_energia_y_masa_en_ambos_modos():
    target = preview(BASE)
    assert target['dose_kg_m3'] * (334000 + 4180*20) == pytest.approx(2476*1023*10)
    assert target['dose_kg_m3'] + target['liquid_kg_m3'] == pytest.approx(160)
    direct = preview(dict(BASE, mode='dose', value=target['dose_kg_m3']))
    assert direct == pytest.approx(target)
    assert target['total_t'] == pytest.approx(target['dose_kg_m3']*target['volume_m3']/1000)
    assert preview(dict(BASE, ice_C=-10))['dose_kg_m3'] < target['dose_kg_m3']
    assert preview(dict(BASE, mode='dose', value=0))['placement_C'] == 18


@pytest.mark.parametrize('changes', [dict(water_kg_m3=10), dict(value=-2), dict(value=19),
                                     dict(ice_C=1), dict(value=None), dict(value=float('nan'))])
def test_rechaza_objetivos_inviables(changes):
    with pytest.raises(ValueError):
        balance(dict(BASE, **changes), 2476, 1023, 487)


def test_par_controlado_mismos_parametros_y_cronograma(tmp_path, monkeypatch):
    import therma.hielo as hielo
    import json
    calls=[]
    def capture(config, ident, dest, progress, observer):
        calls.append(copy.deepcopy(config))
        return dict(config_sha256='prueba',metrics=dict(maxField=45,global_peak_time_s=3600),
                    s25_ifc=dict(peak_estimate=dict(DeltaT_estimate_C=22,time_s=7200),
                                 history=[dict(time_s=7200,Tmax_C=44,DeltaT_estimate_C=22)],complete_sampling=True))
    monkeypatch.setattr(hielo,'ejecutar',capture)
    folder=tmp_path/'estudio'
    hielo.run_pair(BASE, folder, lambda v:None, None)
    record=json.loads((folder/'ice_study.json').read_text(encoding='utf-8'))
    assert record['duration_h'] == pytest.approx(reference()[1]/20)
    assert record['cases'][0]['simulation_id'] != record['cases'][1]['simulation_id']
    for a,b in zip(calls[0]['construction']['pours'],calls[1]['construction']['pours']):
        assert a.pop('placement_C') == 18
        assert b.pop('placement_C') == 8
    assert calls[0] == calls[1]
