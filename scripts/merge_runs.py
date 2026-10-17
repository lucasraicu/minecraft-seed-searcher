"""Build a read-only aggregate leaderboard; original Realm runs remain authoritative."""
from __future__ import annotations

import argparse
from contextlib import ExitStack, closing
import hashlib
import json
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from seed_search.realm.leaderboard import install, order_for
from seed_search.realm.store import LIMIT, canonical, semantic_identity

CONTRACT = 'aggregate-leaderboard-v1'
SCHEMA_SCRIPT = '''
CREATE TABLE IF NOT EXISTS meta(key TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS candidates(id TEXT PRIMARY KEY, idx TEXT NOT NULL,
    seed TEXT NOT NULL, qualification TEXT NOT NULL, result TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS variants(candidate_id TEXT NOT NULL, variant TEXT NOT NULL,
    center TEXT NOT NULL, result TEXT NOT NULL, PRIMARY KEY(candidate_id,variant,center));
CREATE TABLE IF NOT EXISTS observations(id TEXT PRIMARY KEY, candidate_id TEXT, result TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS merged_source_runs(source_id TEXT PRIMARY KEY, identity TEXT NOT NULL, source_path TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS ranges(source_id TEXT NOT NULL, start TEXT NOT NULL, end TEXT NOT NULL,
    PRIMARY KEY(source_id,start));
CREATE TABLE IF NOT EXISTS provenance(table_name TEXT NOT NULL, record_key TEXT NOT NULL,
    source_id TEXT NOT NULL, PRIMARY KEY(table_name,record_key,source_id));
'''


def union_intervals(intervals):
    merged = []
    for start, end in sorted(intervals):
        if type(start) is not int or type(end) is not int or not 0 <= start < end <= LIMIT:
            raise ValueError('Invalid completed interval')
        if merged and start <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(end, merged[-1][1]))
        else:
            merged.append((start, end))
    return merged


def compute_interval_coverage(intervals):
    return sum(end - start for start, end in union_intervals(intervals))


def compatibility(identity):
    cfg = identity.get('config', identity.get('cfg'))
    policy = semantic_identity({'config': cfg})['config_sha256'] if cfg is not None else identity.get('config_sha256')
    if not policy:
        raise ValueError('Source policy identity is required')
    native = identity.get('native', identity.get('prototype'))
    if isinstance(native, dict):
        # Architecture-specific binaries/paths remain provenance, not a cross-host equality requirement.
        source = native.get('record_computation_identity', {}).get('sha256', {})
        code = {k: v for k, v in source.items() if Path(k).suffix in ('.py', '.c', '.h', '.inc', '.json')}
        native_id = {'sources': code, 'adapter': native.get('record_adapter_sha256'),
                     'record_sources': native.get('record_sources_sha256'),
                     'policy': native.get('policy_sha256'), 'stronghold_after': native.get('stronghold_after')}
        if not code or not native_id['policy']:
            raise ValueError('Native source/policy identity is required')
    else:
        native_id = identity.get('native_build', identity.get('backend'))
    return {'policy': policy, 'native': native_id,
            'sequence': (cfg or {}).get('search', {}).get('sequence', 'permutation'),
            'run_key': str((cfg or {}).get('search', {}).get('run_key', '0')),
            'low32': (cfg or {}).get('search', {}).get('low32', 0)}


def _equal_rows(existing, incoming):
    if len(existing) != len(incoming):
        return False
    for a, b in zip(existing, incoming):
        if a == b:
            continue
        try:
            if canonical(json.loads(a)) == canonical(json.loads(b)):
                continue
        except (ValueError, TypeError):
            pass
        return False
    return True


def merge_runs(sources, destination, *, strict=True):
    destination = Path(destination).resolve()
    target = destination if destination.suffix == '.sqlite' else destination / 'realm.sqlite'
    target.parent.mkdir(parents=True, exist_ok=True)
    conflicts = []
    with ExitStack() as stack:
        snapshots = []
        expected = None
        for src in sources:
            src = Path(src).resolve()
            db = src / 'realm.sqlite' if src.is_dir() else src
            if not db.is_file() or db.resolve() == target.resolve():
                raise ValueError(f'Missing source or source equals destination: {db}')
            conn = stack.enter_context(closing(sqlite3.connect(db.as_uri() + '?mode=ro', uri=True)))
            conn.execute('BEGIN')  # One consistent read snapshot, including WAL records.
            meta = dict(conn.execute('SELECT key,value FROM meta'))
            identity = json.loads(meta.get('identity', 'null'))
            if not isinstance(identity, dict) or meta.get('aggregate_contract'):
                raise ValueError(f'Original Realm source identity is required: {db}')
            signature = compatibility(identity)
            if expected is None:
                expected = signature
            if (signature['policy'] != expected['policy'] or signature['run_key'] != expected['run_key'] or
                signature['sequence'] != expected['sequence'] or signature.get('low32') != expected.get('low32')):
                raise ValueError(f'Policy hash mismatch or seed-domain mismatch: {db}')
            if signature['native'] != expected['native']:
                raise ValueError(f'Native build identity mismatch: {db}')
            if signature['sequence'] not in ('permutation', 'strided'):
                raise ValueError(f"Aggregate coverage requires permutation or strided index domain, got '{signature['sequence']}'")
            intervals = [(int(a), int(b)) for a, b in conn.execute("SELECT start,end FROM ranges WHERE status='complete'")]
            union_intervals(intervals)
            from seed_search.seeds import validate_sequence_range
            for first, end in intervals:
                validate_sequence_range(first, end-first, signature['sequence'])
            # Durable identity + configured interval distinguishes shards, even if their directory names match.
            shard = json.loads(meta.get('range', 'null'))
            source_id = hashlib.sha256(canonical({'identity': semantic_identity(identity), 'range': shard}).encode()).hexdigest()
            snapshots.append((conn, db, source_id, identity, intervals))
        if not snapshots:
            raise ValueError('At least one original source is required')
        dest = stack.enter_context(closing(sqlite3.connect(target)))
        if dest.execute("SELECT 1 FROM sqlite_master WHERE name='meta'").fetchone():
            saved = dict(dest.execute('SELECT key,value FROM meta'))
            if saved.get('aggregate_contract') != canonical(CONTRACT):
                raise ValueError('Destination is not a read-only aggregate; original runs must never be modified')
            if json.loads(saved['compatibility']) != expected:
                raise ValueError('Policy hash mismatch or native identity mismatch with existing aggregate')
        dest.executescript(SCHEMA_SCRIPT)
        with dest:
            dest.execute("INSERT OR IGNORE INTO meta VALUES ('aggregate_contract',?)", (canonical(CONTRACT),))
            dest.execute("INSERT OR IGNORE INTO meta VALUES ('compatibility',?)", (canonical(expected),))
        # This contract must survive a conflicting merge transaction so a
        # corrected source can be retried safely against the same destination.
        with dest:
            for conn, db, source_id, identity, intervals in snapshots:
                dest.execute('INSERT OR REPLACE INTO merged_source_runs VALUES (?,?,?)', (source_id, canonical(identity), str(db)))
                for table, columns, keys in (
                    ('candidates', ('id','idx','seed','qualification','result'), ('id',)),
                    ('variants', ('candidate_id','variant','center','result'), ('candidate_id','variant','center')),
                    ('observations', ('id','candidate_id','result'), ('id',)),
                ):
                    if not conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)).fetchone():
                        raise ValueError(f'Missing evidence table {table}: {db}')
                    sql = f"SELECT {','.join(columns)} FROM {table}"
                    for row in conn.execute(sql):
                        key = tuple(row[columns.index(k)] for k in keys)
                        terms = ' AND '.join(f'{k}=?' for k in keys)
                        previous = dest.execute(f'{sql} WHERE {terms}', key).fetchone()
                        if previous is not None and not _equal_rows(previous, row):
                            conflicts.append({'table': table, 'id': ':'.join(map(str,key)), 'source': str(db), 'reason': 'Record payload/identity conflict'})
                            if strict:
                                raise ValueError(f'Found incompatible records: {conflicts[-1]}')
                            continue
                        dest.execute(f"INSERT OR IGNORE INTO {table} VALUES ({','.join('?' for _ in columns)})", row)
                        dest.execute('INSERT OR IGNORE INTO provenance VALUES (?,?,?)', (table, canonical(key), source_id))
                for start, end in intervals:
                    dest.execute('INSERT OR IGNORE INTO ranges VALUES (?,?,?)', (source_id, str(start), str(end)))
            all_intervals = [(int(a),int(b)) for a,b in dest.execute('SELECT start,end FROM ranges')]
            coverage = compute_interval_coverage(all_intervals)
            dest.execute("INSERT OR REPLACE INTO meta VALUES ('completed_seeds',?)", (str(coverage),))
        install(dest)
        top = dest.execute(f'SELECT seed,smart_score,ranking_tier,unmet_requirements FROM candidate_leaderboard_view ORDER BY {order_for(dest)} LIMIT 5').fetchall()
        return {'destination': str(target), 'contract': CONTRACT, 'resumable': False,
                'merged_sources': len({r[2] for r in snapshots}), 'total_seeds_scanned': coverage,
                'total_candidates': dest.execute('SELECT count(*) FROM candidates').fetchone()[0],
                'incompatible_records': conflicts,
                'top_candidates': [{'seed':r[0],'smart_score':r[1],'tier':r[2],'unmet':r[3]} for r in top]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--inputs','-i', nargs='+', required=True, type=Path)
    parser.add_argument('--output','-o', required=True, type=Path)
    parser.add_argument('--strict', action='store_true', help='Compatibility option; conflict rejection is already the default')
    args = parser.parse_args()
    print(json.dumps(merge_runs(args.inputs,args.output),indent=2))


if __name__ == '__main__':
    main()
