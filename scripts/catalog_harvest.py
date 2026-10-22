#!/usr/bin/env python3
"""Register, inspect or explicitly drain independent CPU catalog work.

Personal search interruption does not cancel a registered public campaign.
This command never changes personal checkpoints or launches personal searches.
"""
import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))


def main(argv=None):
    from seed_search.catalog.harvest import HarvestQueue
    from seed_search.catalog.ingestion import strict_json_loads,verify_no_symlinks
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',required=True,type=Path)
    sub=parser.add_subparsers(dest='command',required=True)
    sub.add_parser('status')
    setup=sub.add_parser('automation-configure');setup.add_argument('--spawn-estimator',type=Path,required=True);setup.add_argument('--native-build',type=Path)
    for command in ('automation-status','automation-run','automation-start','automation-pause','automation-resume','automation-allocate'):
        sub.add_parser(command)
    cleanup=sub.add_parser('cleanup');cleanup.add_argument('--mode',choices=('dry_run','quarantine','delete'),default='dry_run')
    register=sub.add_parser('register');register.add_argument('--descriptor',required=True,type=Path)
    work=sub.add_parser('drain');work.add_argument('--max-worlds',type=int,default=100)
    work.add_argument('--spawn-estimator',type=Path);work.add_argument('--spawn-estimator-sha256');work.add_argument('--spawn-source-sha256')
    for state in ('pause','resume','cancel'):
        p=sub.add_parser(state);p.add_argument('--campaign',required=True)
    args=parser.parse_args(argv)
    if args.command.startswith('automation-') or args.command=='cleanup':
        from seed_search.catalog import automation
        if args.command=='automation-configure':
            import hashlib
            from seed_search import _native
            from seed_search.backend import native_runtime,model_metadata
            from seed_search.realm.native_identity import native_source_fingerprint
            from seed_search.catalog.models import identity
            native_runtime()
            pinfile=verify_no_symlinks(Path(str(args.spawn_estimator)+'.build.json'))
            if pinfile.stat().st_size>65536:raise ValueError('Build manifest cap')
            pin=strict_json_loads(pinfile.read_bytes())
            ident=identity('0',model_id=model_metadata()['model'],source_sha256=native_source_fingerprint(),native_sha256=hashlib.sha256(Path(_native.__file__).read_bytes()).hexdigest())
            options=dict(spawn=dict(executable=str(args.spawn_estimator.absolute()),binary_sha256=pin['binary_sha256'],source_sha256=pin['source_sha256']))
            if args.native_build:options['native_build']=str(args.native_build.absolute())
            result=automation.configure(args.root,ident,options)
        elif args.command=='automation-status':result=automation.status(args.root)
        elif args.command=='automation-run':result=automation.run(args.root)
        elif args.command=='automation-start':result=automation.ensure_supervisor(args.root)
        elif args.command=='cleanup':
            from seed_search.catalog.store import AutomationStore
            from seed_search.catalog.harvest import AutomationLedger
            from seed_search.catalog.retention import automation_objectives
            config=automation.configuration(args.root)
            if config is None:raise ValueError('Configure automation before cleanup')
            with HarvestQueue(args.root) as queue,queue.ownership():
                ledger=AutomationLedger(queue,policy_revision=config['policy_revision'],objectives=automation_objectives())
                result=AutomationStore(args.root).cleanup(ledger,mode=args.mode)
        else:result=automation.control(args.root,args.command.removeprefix('automation-'))
        print(json.dumps(result,indent=2));return 0
    with HarvestQueue(args.root) as queue:
        if args.command=='register':
            path=verify_no_symlinks(args.descriptor)
            if path.stat().st_size>1<<20:raise ValueError('Descriptor exceeds1MiB')
            queue.register(strict_json_loads(path.read_bytes()));result=queue.status()
        elif args.command=='drain':
            from seed_search.catalog.harvest_worker import drain
            from seed_search.catalog.harvest_native import extract_native,publish_observation
            extract=lambda job,seconds:extract_native(job,seconds,heartbeat=queue.heartbeat)
            publish=lambda job,obs:publish_observation(args.root,job,obs)
            spawn_options=(args.spawn_estimator,args.spawn_estimator_sha256,args.spawn_source_sha256)
            if any(spawn_options):
                if not all(spawn_options):raise ValueError('All three pinned spawn estimator options are required')
                from seed_search.catalog.spawn_estimator import SpawnEstimator
                from seed_search.catalog.accuracy_harvest import extract_with_spawn,publish_with_spawn
                estimator=SpawnEstimator(args.spawn_estimator,binary_sha256=args.spawn_estimator_sha256,source_sha256=args.spawn_source_sha256)
                base_extract=extract
                extract=lambda job,seconds:extract_with_spawn(job,seconds,estimator=estimator,extract=base_extract)
                publish=lambda job,obs:publish_with_spawn(args.root,job,obs,publish=publish_observation)
            result=drain(queue,extract,publish,max_worlds=args.max_worlds)
        elif args.command in ('pause','resume','cancel'):
            queue.set_campaign_state(args.campaign,{'pause':'paused','resume':'active','cancel':'cancelled'}[args.command]);result=queue.status()
        else:result=queue.status()
    print(json.dumps(result,indent=2));return 0


if __name__=='__main__':raise SystemExit(main())
