from __future__ import annotations
import os
for _key in ("OMP_NUM_THREADS","OPENBLAS_NUM_THREADS","MKL_NUM_THREADS","VECLIB_MAXIMUM_THREADS"):
    os.environ[_key]="1"

import argparse
import json
from pathlib import Path
from . import BACKEND_COMMIT
from .backend import Backend
from .config import load_config,discovery_grid
from .preflight import benchmark,probe,metadata,compare_observations,save_json
from .seeds import parse_seed

def main(argv=None):
    from .realm.cli import handles
    if handles(argv):
        from .realm.cli import main as realm_main
        return realm_main(argv)
    parser=argparse.ArgumentParser(description="Bedrock 26.52 finite search with measured evidence readiness gate")
    parser.add_argument("--config",help="Configuration path (default search.example.yaml; resume defaults to persisted configuration)")
    sub=parser.add_subparsers(dest="command",required=True)
    doctor=sub.add_parser("doctor",help="Check native backend and pending validation gates")
    doctor.add_argument("--output")
    bench=sub.add_parser("benchmark",help="Measure up to ten fixed diagnostic seeds")
    bench.add_argument("--count",type=int,default=3)
    bench.add_argument("--workers",type=int,nargs="*",default=[4,8,12])
    bench.add_argument("--output",default="runs/preflight")
    inspect=sub.add_parser("probe",help="Generate one predicted terrain/structure inspection packet")
    inspect.add_argument("--seed",type=parse_seed,default=12345)
    inspect.add_argument("--center",type=int,nargs=2)
    inspect.add_argument("--output",default="runs/phone-check")
    compare=sub.add_parser("compare",help="Compare supplied actual phone observations")
    compare.add_argument("--observations",required=True)
    compare.add_argument("--output",default="runs/phone-check/comparison.json")
    reg=sub.add_parser("regression",help="Repeat the frozen external comparison and detect exact local drift")
    reg.add_argument("--output",default="runs/sweep-readiness/regression")
    for name in ("search","rank"):
        q=sub.add_parser(name,help="Finite deterministic automatic search" if name=="search" else "Rank supplied full signed seeds")
        q.add_argument("--output",required=True)
        q.add_argument("--workers",type=int)
        q.add_argument("--readiness")
        q.add_argument("--dry-run",action="store_true")
        q.add_argument("--stop-after",type=int,help="Checkpoint after this many completions, for bounded resume verification")
        if name=="search":
            q.add_argument("--count",type=int,required=True)
            q.add_argument("--start-index",type=int,default=0)
        else:q.add_argument("--seeds",required=True,help="One signed decimal seed per line")
    res=sub.add_parser("resume",help="Resume the exact persisted finite workload")
    res.add_argument("--run",required=True)
    res.add_argument("--workers",type=int)
    res.add_argument("--dry-run",action="store_true")
    review=sub.add_parser("review",help="Import recorded actual Chunkbase UI review and refresh reports")
    review.add_argument("--run",required=True);review.add_argument("--evidence",required=True)
    args=parser.parse_args(argv)
    try:
        if args.command in ('resume','review') and args.config is None:
            from .storage import Store
            original=Store(args.run,resume=True)
            cfg,hash_=original.identity['config'],original.identity['config_sha256'];original.close()
        else:cfg,hash_=load_config(args.config or 'search.example.yaml')
        if cfg["game"]["backend_commit"]!=BACKEND_COMMIT:
            raise ValueError("Configured commit does not match compiled prototype")
        if args.command=="doctor":
            with Backend(12345) as b:
                b.grid(-16,-16,3,3,16)
            result=metadata(hash_)
            result.update({"native_backend":"built_and_callable","discovery_grid":list(discovery_grid(cfg)),
                           "available_commands":["doctor","benchmark","probe","compare","regression","rank","search","resume","review"],
                           "capabilities":__import__("seed_search.backend",fromlist=["capabilities"]).capabilities(),
                           "large_search_gate":"requires_matching_identity_and_verified_readiness_record"})
            if args.output: save_json(args.output,result)
        elif args.command=="benchmark":
            result=benchmark(cfg,hash_,args.output,args.count,tuple(args.workers))
            result={"output":str(Path(args.output).resolve()),"stage_seconds":result["stage_seconds"],
                    "full_search_seconds_per_seed":None}
        elif args.command=="probe":
            result=probe(cfg,hash_,args.seed,args.output,tuple(args.center) if args.center else None)
            result={"output":str(Path(args.output).resolve()),"seed":result["seed"],"center":result["center"],
                    "validation":"predicted_diagnostic_optional_phone_followup"}
        elif args.command=="regression":
            from .regression import regression
            r=regression(args.output);result={"passed":r['passed'],"summary":r['summary']}
        elif args.command in ("search","rank"):
            from .search import run_search
            seeds=Path(args.seeds).read_text().splitlines() if args.command=="rank" else None
            result=run_search(cfg,hash_,args.output,getattr(args,'count',len(seeds) if seeds else 10),getattr(args,'start_index',0),
                              args.workers,seeds,readiness=args.readiness,dry_run=args.dry_run,stop_after=args.stop_after)
        elif args.command=="resume":
            from .search import run_search
            from .storage import Store
            store=Store(args.run,resume=True);identity=store.identity;store.close()
            if cfg!=identity['config'] or hash_!=identity['config_sha256']:
                raise ValueError('Incompatible resume configuration; supply the original --config')
            result=run_search(cfg,hash_,args.run,identity['count'],identity['start_index'],args.workers,
                              identity['seeds'],resume=True,readiness=identity['readiness'],dry_run=args.dry_run)
        elif args.command=="review":
            from .review import import_review
            from .storage import Store,backend_identity
            from .reports import export_search
            store=Store(args.run,resume=True)
            try:
                if store.identity['config_sha256']!=hash_ or store.identity['backend']!=backend_identity():
                    raise ValueError('Review run identity differs from current config/backend')
                import_review(args.run,args.evidence,cfg)
                result=export_search(args.run,store.results(),cfg,hash_,store.identity)
            finally:store.close()
        else:
            result=compare_observations(args.observations,args.output,cfg,hash_)
        print(json.dumps(result,indent=2,allow_nan=False),flush=True)
    except (ValueError,KeyError,FileNotFoundError) as e:
        parser.error(str(e))

if __name__=="__main__":
    main()
