"""Explicit offline one-tile worker. HTTP never imports or invokes this entry point."""
import argparse
import hashlib
import json
from pathlib import Path
import time
from .refinement_queue import RefinementQueue
from .refinement import sample_tile,decode_tile,make_tile


def execute_one(queue,provider_factory,*,seconds=60):
    if type(seconds)is not int or not 1<=seconds<=60:raise ValueError('Tile worker budget1..60s')
    claim=queue.claim(lease_seconds=seconds+30)
    if claim is None:return dict(status='no_ready_work')
    start=time.monotonic();spec=claim['spec']
    # A crash/exception leaves a fenced, expiring claim. No guessed completion.
    with provider_factory(spec['context'])as provider:
        def sample(x,y,z):
            if time.monotonic()-start>seconds:raise TimeoutError('Tile sampling wall budget')
            return provider.sample(x,y,z)
        tile=sample_tile(spec['context'],spec['bounds'],spec['y'],sample)
        values=decode_tile(tile)
        names={str(raw):provider.name(raw)for raw in set(values)if raw is not None}
        tile=make_tile(spec['context'],spec['bounds'],spec['y'],list(values),biome_names=names)
    if time.monotonic()-start>seconds:raise TimeoutError('Tile worker wall budget')
    queue.complete(claim,tile)
    return dict(status='complete',task_id=claim['task_id'],tile_id=tile['tile_id'],seconds=time.monotonic()-start)


class NativeProvider:
    def __init__(self,context):self.context=context
    def __enter__(self):
        if self.context['provider']!='procedural_model_v1':raise ValueError('This CLI only runs native model tiles; game-backed providers need an explicit offline oracle')
        from ..backend import Backend,native_runtime,biome_name,model_metadata
        from ..realm.native_identity import native_source_fingerprint
        from .. import _native
        native_runtime()
        ident=self.context['identity']
        if ident['world_settings_id']!='default' or ident['model_id']!=model_metadata()['model']:
            raise ValueError('Native refinement does not implement these world settings/model')
        if (native_source_fingerprint()!=ident['source_sha256'] or
            hashlib.sha256(Path(_native.__file__).read_bytes()).hexdigest()!=ident['native_sha256']):
            raise ValueError('Refinement runtime differs from requested observation')
        self.backend=Backend(ident['seed']);self._name=biome_name
        return self
    def __exit__(self,*args):self.backend.close()
    def sample(self,x,y,z):return self.backend.biome(x,y,z,dimension=0 if self.context['dimension']=='overworld' else -1)
    def name(self,raw):return self._name(raw)


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--spool',type=Path,required=True)
    parser.add_argument('--descriptor',type=Path);parser.add_argument('--execute-one',action='store_true')
    args=parser.parse_args();queue=RefinementQueue(args.spool)
    if args.descriptor:
        if args.descriptor.stat().st_size>16384:raise ValueError('Descriptor16KiB cap')
        from .ingestion import strict_json_loads
        d=strict_json_loads(args.descriptor.read_bytes())
        if set(d)!={'context','bounds','y'}:raise ValueError('Invalid tile descriptor')
        print(json.dumps(dict(queued=queue.submit(d['context'],d['bounds'],d['y']))))
    if args.execute_one:print(json.dumps(execute_one(queue,NativeProvider)))
    if not args.descriptor and not args.execute_one:parser.error('Use --descriptor and/or --execute-one explicitly')
if __name__=='__main__':main()
