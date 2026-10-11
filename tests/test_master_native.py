import numpy as np
import pytest
from seed_search.backend import Backend, raw_layout, sweep_raw, RAW_MT_TYPES, native_runtime, configure_native_threads


@pytest.mark.parametrize('start,count',[(0,4),(2**32-4,4),(2**32,0),(12345,64)])
def test_raw_sweep_matches_reference_layouts_and_order(start,count):
    families=[(name,(-577,-401,399,800)) for name in sorted(RAW_MT_TYPES)]
    reference=sweep_raw(start,count,families,1)
    for i in range(count):
        assert reference[i].tolist()==[len(raw_layout(start+i,name,bounds)) for name,bounds in families]
    if native_runtime()['openmp']:
        assert np.array_equal(reference,sweep_raw(start,count,families,4))


@pytest.mark.parametrize('start,count',[(2**32-1,2),(-1,1),(True,1),(0,65537)])
def test_raw_overflow_and_unbounded_batches_fail(start,count):
    with pytest.raises(ValueError):sweep_raw(start,count,[('fortress',(-10,-10,10,10))])


def test_raw_sweep_forbidden_full64_families_and_work_budget():
    with pytest.raises(ValueError):sweep_raw(0,1,[('stronghold',(0,0,1,1))])
    with pytest.raises(ValueError):sweep_raw(0,1,[('village',(-1000000,-1000000,1000000,1000000))])


def test_parallel_columns_preserve_cold_seed_history_and_negative_quart_edges():
    points=np.array([[x,z] for x in range(-9,9) for z in range(-9,9)],np.int32)
    threads=(1,3,2,1) if native_runtime()['openmp'] else (1,1)
    previous=None
    try:
        for n in threads:
            configure_native_threads(n)
            with Backend(-1) as backend:
                result=[backend.land(points),*backend.heights(points,1),*backend.grid(-17,-9,19,17,3).values()]
                assert backend.land(np.empty((0,2),np.int32)).size==0
            if previous is not None:
                assert all(np.array_equal(a.view(np.uint8),b.view(np.uint8)) for a,b in zip(result,previous))
            previous=result
    finally:configure_native_threads(1)
