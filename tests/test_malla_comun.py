from estudiar_malla_comun import assess


def cases():
    return [dict(shape=n,status='COMPLETED',missing_points_max=0,numerical_checks=True,
        horizon_captured=True,engine_fingerprint='same',Tmax_C=t,Delta_estimate_C=d)
        for n,t,d in [([72,72,42],55.1,40.2),([84,84,48],55.05,40.15),([90,90,48],55.04,40.12)]]


def test_small_changes_with_complete_coverage():
    assert assess(cases())['within_tolerance']


def test_complete_coverage_is_not_convergence():
    c=cases();c[-1]['Delta_estimate_C']=41
    assert not assess(c)['within_tolerance']


def test_unknown_points_or_incompatible_versions_do_not_pass():
    c=cases();c[0]['missing_points_max']=1
    assert not assess(c)['within_tolerance']
    c=cases();c[0]['engine_fingerprint']='different'
    assert not assess(c)['within_tolerance']


def test_failed_or_short_horizon_does_not_pass():
    c=cases();c[-1]['status']='FAILED'
    assert not assess(c)['within_tolerance']
    c=cases();c[-1]['horizon_captured']=False
    assert not assess(c)['within_tolerance']
