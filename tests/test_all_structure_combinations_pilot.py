"""Pilot contracts: exact dimension, safe rejection, and measured filter order."""
from scripts.pilot_all_structure_combinations import (MT, PROFILES, direct, expanded_raw,
                                                     greedy_order, query_bounds)
from scripts.pilot_locked_stronghold import exact_bounds


def test_all_family_profile_routes_correct_dimensions_and_uses_selected_anchor():
    row = {'bounds': exact_bounds((-4, 4))}
    names = PROFILES['all_21_overworld_nether']
    assert len(names) == 20  # Plus the already selected Stronghold = 21.
    assert 'stronghold' not in names and 'end_city' not in names
    for name in names:
        dimension = 'nether' if name in ('fortress', 'bastion', 'ruined_portal_nether') else 'overworld'
        assert query_bounds(row, name) == row['bounds'][dimension]
    assert query_bounds(row, 'end_city') == row['bounds']['overworld']


def test_direct_exits_on_first_missing_viable_witness():
    class Backend:
        def structure_first(self, name, bounds):
            assert name == 'swamp_hut'
            return None
    assert not direct(Backend(), {'bounds':exact_bounds((4, 4))}, ('swamp_hut', 'village'))


def test_raw_positive_does_not_establish_viable_combination():
    class Backend:
        def structures(self, name, bounds, viable):
            assert not viable
            return [(0, 0)]
        def structure_first(self, name, bounds):
            return None
    backend = Backend()
    row = {'bounds':exact_bounds((4, 4))}
    assert expanded_raw(backend, row, ('swamp_hut',))
    assert not direct(backend, row, ('swamp_hut',))


def test_greedy_order_accounts_for_cost_and_conditional_survivors():
    observations = [
        {'a':{'viable':False,'seconds':10}, 'b':{'viable':True,'seconds':1}, 'c':{'viable':False,'seconds':1}},
        {'a':{'viable':True,'seconds':10}, 'b':{'viable':False,'seconds':1}, 'c':{'viable':True,'seconds':1}},
    ]
    assert greedy_order([{},{}], observations, ('a','b','c')) == ['b','c','a']


def test_expanded_placement_gate_excludes_upper_bit_dependent_families():
    assert len(MT) == 16
    assert not set(MT) & {'stronghold','trial_chamber','trail_ruins','abandoned_camp','mineshaft','end_city'}


def test_sparse_raw_gate_stops_at_first_in_bounds_candidate():
    from scripts.pilot_minimal_raw_gate import sparse_raw_first
    class Backend:
        def attempt(self, name, rx, rz):
            assert (rx,rz) == (0,0)
            return (8,8)
    row = {'bounds': {'overworld': (0,0,15,15)}}
    assert sparse_raw_first(Backend(), row, 'mansion')
    row['bounds']['overworld'] = (0,0,7,7)
    assert not sparse_raw_first(Backend(), row, 'mansion')


def test_sparse_raw_gate_recognizes_full_offset_rectangle_without_queries():
    from scripts.pilot_minimal_raw_gate import sparse_raw_first
    class Backend:
        def attempt(self, *args):
            raise AssertionError('A complete placement-offset rectangle guarantees presence')
    for name, offset in (('mansion',8),('outpost',0)):
        for origin in (-1280,0,1280):
            row = {'bounds': {'overworld': (origin+offset,origin+offset,origin+944+offset,origin+944+offset)}}
            assert sparse_raw_first(Backend(), row, name)


def test_outpost_zero_offset_must_not_be_treated_as_eight_offset_guarantee():
    from scripts.pilot_minimal_raw_gate import sparse_raw_first
    class Backend:
        def attempt(self, name, rx, rz):
            assert name == 'outpost'
            return (0,0)
    row = {'bounds': {'overworld': (8,8,952,952)}}
    assert not sparse_raw_first(Backend(), row, 'outpost')
    row['bounds']['overworld'] = (0,0,7,7)
    assert sparse_raw_first(Backend(), row, 'outpost')
