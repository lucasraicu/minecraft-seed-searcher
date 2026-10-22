#!/usr/bin/env python3
"""Offline accuracy bundle construction over an existing cohort; never searches seeds."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import time
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from seed_search.catalog.accuracy_store import REVISION,write_bundle,read_bundle
from seed_search.catalog.anchors import derive_anchor_layouts
from seed_search.catalog.spawn_estimator import SpawnEstimator
from seed_search.catalog.segments import SegmentedCatalog


def build_spawn_bundle(root,snapshot_id,estimator,*,seconds=300):
    start=time.monotonic()
    try:_,prior=read_bundle(root,snapshot_id)
    except FileNotFoundError:prior=None
    entries=[] if prior is None else list(prior['anchors'])
    seen={(e['world_id'],e['anchor']['mode']) for e in entries}
    with SegmentedCatalog(root) as store:
        info=store.info(snapshot_id)
        if info['worlds']>2000:raise ValueError('Accuracy cohort cap2000')
        members=store.conn.execute('SELECT world_id FROM observation_ref WHERE snapshot_id=? ORDER BY world_id',(snapshot_id,)).fetchall()
        for (wid,) in members:
            if time.monotonic()-start>seconds:raise TimeoutError('Accuracy derivation budget')
            if (wid,'world_spawn_estimated') in seen:continue
            obs=store.observation(snapshot_id,wid)
            anchor=estimator.estimate(obs['identity'])
            entries.append(derive_anchor_layouts(obs,anchor))
        bundle=dict(revision=REVISION,snapshot_id=snapshot_id,anchors=entries,
            tiles=[] if prior is None else prior['tiles'],metadata=dict(estimator_binary_sha256=estimator.binary_sha256,
                estimator_source_sha256=estimator.source_sha256,scope='world_spawn_xz_not_player_landing',worlds=info['worlds']))
    return bundle


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,required=True);parser.add_argument('--snapshot',required=True)
    parser.add_argument('--estimator',type=Path,required=True);parser.add_argument('--estimator-sha256',required=True)
    parser.add_argument('--source-sha256',required=True);parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--publish',action='store_true')
    args=parser.parse_args();estimator=SpawnEstimator(args.estimator,binary_sha256=args.estimator_sha256,source_sha256=args.source_sha256)
    bundle=build_spawn_bundle(args.root,args.snapshot,estimator)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    with args.output.open('x') as handle:json.dump(bundle,handle,separators=(',',':'));handle.write('\n')
    if args.publish:print(json.dumps(dict(accuracy_generation=write_bundle(args.root,bundle),anchors=len(bundle['anchors']))))
    else:print(json.dumps(dict(prepared=str(args.output),anchors=len(bundle['anchors']),published=False)))
if __name__=='__main__':main()
