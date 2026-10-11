"""Parent-owned atomic SQLite checkpoints, independent of worker completion order."""
import hashlib
import json
import sqlite3
from pathlib import Path
from .backend import model_metadata

SCHEMA=1
ROOT=Path(__file__).resolve().parents[2]

def backend_identity():
    # Prediction/checkpoint identity excludes rendering and readiness assembly.
    # Those files are verified separately as hashed readiness artifacts; editing
    # a plot title must not invalidate every completed seed prediction.
    modules=('__init__','backend','cache','landscapes','config','geometry','seeds','wood','terrain','structures','scoring','storage','search','review')
    paths=[ROOT/'native/bridge.c',ROOT/'native/bridge.h',ROOT/'vendor/backend.json',*[ROOT/f'src/seed_search/{name}.py' for name in modules]]
    from . import _native
    paths.append(Path(_native.__file__))
    return {'model':model_metadata(),'sha256':{str(p.relative_to(ROOT)) if p.is_relative_to(ROOT) else p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}}

def semantic_hash(cfg):
    # Worker count/output depth do not change prediction semantics, but persisted
    # config is compared in full on resume to reject surprise changes.
    return hashlib.sha256(json.dumps(cfg,sort_keys=True,separators=(',',':')).encode()).hexdigest()

class Store:
    def __init__(self,run,identity=None,resume=False):
        self.run=Path(run)
        db=self.run/'checkpoint.sqlite'
        if not resume and db.exists():raise ValueError('Run already exists; use resume or a new output directory')
        if resume and not db.exists():raise ValueError('No checkpoint exists to resume')
        self.run.mkdir(parents=True,exist_ok=True)
        self.db=sqlite3.connect(db)
        self.db.execute('PRAGMA journal_mode=WAL')
        self.db.execute('PRAGMA synchronous=FULL')
        self.db.execute('CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY,value TEXT NOT NULL)')
        self.db.execute('CREATE TABLE IF NOT EXISTS seeds (idx TEXT PRIMARY KEY,seed TEXT NOT NULL,result TEXT NOT NULL)')
        if not resume:
            with self.db:self.db.execute('INSERT INTO meta VALUES (?,?)',('identity',json.dumps(identity,sort_keys=True)))
        self.identity=json.loads(self.db.execute("SELECT value FROM meta WHERE key='identity'").fetchone()[0])
        if resume and identity is not None and self.identity!=identity:
            self.close();raise ValueError('Incompatible resume: configuration, backend, seed sequence or evidence differs')
    def completed(self):return {int(v[0]) for v in self.db.execute('SELECT idx FROM seeds')}
    def save(self,index,seed,result):
        if str(result['seed'])!=str(seed) or result['index']!=index:raise ValueError('Worker index/seed mismatch')
        with self.db:self.db.execute('INSERT INTO seeds VALUES (?,?,?)',(str(index),str(seed),json.dumps(result,allow_nan=False)))
    def results(self):
        rows=[json.loads(v[0]) for v in self.db.execute('SELECT result FROM seeds')]
        return sorted(rows,key=lambda r:r['index'])
    def close(self):self.db.close()
