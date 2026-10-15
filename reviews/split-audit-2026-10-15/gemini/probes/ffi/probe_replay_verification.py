"""Probe to audit whether ReplayProvider independently verifies dynamic center selection or blindly accepts supplied C decision."""
import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[5]))
sys.path.insert(0, str(Path(__file__).resolve().parents[5] / "tests"))

from scripts.build_blueprint_batch import build
from seed_search.realm.config import dynamic_blueprint_config
from seed_search.realm.blueprint import evaluate_dynamic_seed
from seed_search.realm.native_batch import Prototype, ReplayProvider
from seed_search.realm.dynamic import candidate_centers

def main():
    build_dir = Path("/tmp/dynamic-ffi-audit-build")
    cfg = dynamic_blueprint_config()
    proto = Prototype(build_dir, cfg)

    # Sweep seed 42 with synthetic fixture
    with proto.sweep([42], fixtures=[(0, 0, -1)], retention='survivors', max_misses=2) as batch:
        native = batch.pointer.results[0]
        chosen_x = native.anchors[0].x
        chosen_z = native.anchors[0].z
        print(f"C native selected center: ({chosen_x}, {chosen_z})")

        # Now create ReplayProvider
        provider = ReplayProvider(native, proto)
        print(f"Provider dynamic_center: {provider.dynamic_center}")

        # Now test: what happens if we mutate provider.dynamic_center to a DIFFERENT center?
        # Say, (chosen_x + 16, chosen_z)
        # Note: (chosen_x + 16) won't have queries in provider.queries because C only subsetted for chosen_x!
        print(f"Queries in provider: {list(provider.queries.keys())[:3]}")

        # Test evaluating with normal ReplayProvider
        rec = evaluate_dynamic_seed(0, 42, cfg, backend_factory=lambda _: provider)
        print(f"evaluate_dynamic_seed returned center: {rec['anchors'][0]['evaluation_center']}")

        # What if native had 0 anchors (reject)?
        # Create a mock reject result
        mock_reject = SimpleNamespace(
            discovery=native.discovery,
            nanchors=0,
            anchors=[],
            seconds=0.1,
            stage_seconds=[0.0]*15
        )
        reject_provider = ReplayProvider(mock_reject, proto)
        print(f"Reject provider dynamic_center: {reject_provider.dynamic_center}")
        print(f"Reject provider dynamic_no_anchor: {reject_provider.dynamic_no_anchor}")
        rec_reject = evaluate_dynamic_seed(0, 42, cfg, backend_factory=lambda _: reject_provider)
        print(f"evaluate_dynamic_seed on reject returned anchors: {rec_reject['anchors']}")

if __name__ == '__main__':
    main()
