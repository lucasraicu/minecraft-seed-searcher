#!/usr/bin/env python3
"""Private segmented Catalog tools. Import/query commands never extract new seeds."""
import argparse
import json
import os
from pathlib import Path
import resource
import sys
import time

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))


def migrate(source,destination,snapshot_id=None,*,batch_worlds=10):
    from seed_search.catalog.store import CatalogStore
    from seed_search.catalog.segments import SegmentedCatalog
    from seed_search.catalog.models import world_id
    from seed_search.catalog.ingestion import atomic_json,verify_no_symlinks
    source=verify_no_symlinks(source);destination=verify_no_symlinks(destination)
    if source==destination or source in destination.parents or destination in source.parents:
        raise ValueError('Import requires separate, nonnested source/destination roots')
    if not 1<=batch_worlds<=25:raise ValueError('Batch size must be1..25')
    start=time.monotonic()
    with CatalogStore(source) as old:
        if snapshot_id is None:
            row=old.conn.execute('SELECT snapshot_id FROM catalog_snapshot ORDER BY published_at DESC,snapshot_id DESC LIMIT 1').fetchone()
            if row is None:raise ValueError('Source has no published snapshots')
            snapshot_id=row[0]
        data=old.snapshot(snapshot_id)
    # Existing v1 manifests load as a unit; the new publisher uses bounded batches.
    # Keep this bridge bounded to the approved small reference corpus.
    if len(data['observations'])>200:raise ValueError('Legacy import bridge capped at200 worlds')
    by_world={}
    for layout in data['layouts']:by_world.setdefault(layout['world_id'],[]).append(layout)
    with SegmentedCatalog(destination) as new:
        roots=new.snapshots();parent=roots[-1]['snapshot_id'] if roots else None
        for offset in range(0,len(data['observations']),batch_worlds):
            if time.monotonic()-start>900:raise TimeoutError('Import wall allowance exhausted')
            observations=data['observations'][offset:offset+batch_worlds]
            layouts=[row for obs in observations for row in by_world.get(world_id(obs['identity']),[])]
            parent=new.publish(observations,layouts,parent=parent)
            atomic_json(destination/'import-progress.json',dict(source_snapshot_id=snapshot_id,
                imported_worlds=offset+len(observations),snapshot_id=parent))
        audit=new.audit(parent);info=new.info(parent)
    report=dict(schema='catalog-pilot-import-v1',source_snapshot_id=snapshot_id,**info,audit=audit,
        wall_seconds=time.monotonic()-start,process_peak_rss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        note='Verified existing observations; no native extraction, no source migration in place')
    atomic_json(destination/'import-report.json',report);return report


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__);sub=parser.add_subparsers(dest='command',required=True)
    imp=sub.add_parser('import-v1');imp.add_argument('--source',required=True,type=Path);imp.add_argument('--root',required=True,type=Path)
    imp.add_argument('--snapshot');imp.add_argument('--batch-worlds',type=int,default=10)
    feedback=sub.add_parser('import-requests',help='Validate explicit participant requests and prepare a grouped holdout')
    feedback.add_argument('--input',required=True,type=Path)
    feedback.add_argument('--source',choices=('player','developer','synthetic'),required=True)
    for name in ('audit','snapshots','backup','query'):
        p=sub.add_parser(name);p.add_argument('--root',required=True,type=Path)
        if name=='audit':p.add_argument('--snapshot')
        if name=='backup':p.add_argument('--destination',required=True,type=Path)
        if name=='query':p.add_argument('--request',required=True,type=Path);p.add_argument('--page-size',type=int,default=20)
    args=parser.parse_args(argv)
    if args.command=='import-requests':
        from seed_search.catalog.usefulness import import_requests,split_groups
        if args.input.stat().st_size>1<<20:raise ValueError('Request import capped at1MiB')
        corpus=import_requests(args.input.read_text(),source=args.source)
        result=dict(corpus=corpus,holdout=split_groups(corpus))
    elif args.command=='import-v1':result=migrate(args.source,args.root,args.snapshot,batch_worlds=args.batch_worlds)
    elif args.command=='query':
        from seed_search.catalog.service import CatalogService
        from seed_search.catalog.request import load_request
        result=CatalogService(args.root).query(dict(request=load_request(args.request.read_text()),page_size=args.page_size))
    else:
        from seed_search.catalog.segments import SegmentedCatalog
        with SegmentedCatalog(args.root) as store:
            if args.command=='audit':result=store.audit(args.snapshot)
            elif args.command=='snapshots':result=store.snapshots()
            else:store.backup(args.destination);result=dict(backup=str(args.destination),verified=True)
    print(json.dumps(result,indent=2,allow_nan=False));return 0


if __name__=='__main__':raise SystemExit(main())
