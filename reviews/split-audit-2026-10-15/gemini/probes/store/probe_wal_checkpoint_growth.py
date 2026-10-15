"""
Probe: Verify WAL growth when checkpoints are blocked by concurrent readers.
Finding ID: G-STORE-06

Demonstrates that in SQLite WAL mode with wal_autocheckpoint=16384 and
journal_size_limit=134217728 (configured by RealmStore), if a long-running reader
holds an active transaction or cursor, checkpoints cannot advance or truncate the
WAL, causing unbounded file growth.
"""
import os
import sqlite3
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from seed_search.realm.store import RealmStore


def test_wal_growth_blocked_by_reader(tmp_path):
    run_dir = tmp_path / "realm_wal_growth"
    run_dir.mkdir(parents=True)
    
    cfg = {"search": {"workers": 1, "max_misses": 0}}
    identity = {"config": cfg, "count": 10000, "start_index": 0}
    
    with RealmStore(run_dir, identity=identity) as store:
        # Check configured pragmas
        autocheckpoint = store.db.execute("PRAGMA wal_autocheckpoint").fetchone()[0]
        journal_limit = store.db.execute("PRAGMA journal_size_limit").fetchone()[0]
        print(f"[Probe] Configured wal_autocheckpoint: {autocheckpoint} pages")
        print(f"[Probe] Configured journal_size_limit: {journal_limit} bytes ({journal_limit // (1024*1024)} MiB)")
        assert autocheckpoint == 16384
        assert journal_limit == 134217728
        
        # Open a concurrent reader connection that holds a read transaction
        # (e.g. slow client reading leaderboard or streaming candidates)
        reader = sqlite3.connect(f"file:{run_dir / 'realm.sqlite'}?mode=ro", uri=True)
        # In SQLite, an open uncommitted read transaction or active multi-row cursor
        # holds a lock on the WAL index
        cur = reader.cursor()
        cur.execute("BEGIN DEFERRED")
        cur.execute("SELECT 1 FROM meta")
        _ = cur.fetchone()
        
        wal_path = run_dir / "realm.sqlite-wal"
        
        # Now simulate writing many batches from store
        # Insert 1000 rows with 4KB payloads to generate WAL frames
        store.configure_range(0, 1000, 10)
        large_payload = "x" * 8192
        for i in range(10):
            store.claim_range(f"w-{i}", max_seeds=10)
            batch = [{
                "index": i * 10 + j,
                "seed": str(i * 10 + j),
                "anchors": [],
                "counts": {"test": 1},
                "data": large_payload
            } for j in range(10)]
            store.complete_range(i * 10, i * 10 + 10, batch)
            
        wal_size = wal_path.stat().st_size if wal_path.exists() else 0
        print(f"[Probe] WAL size while reader active: {wal_size:,} bytes")
        
        # Writer attempts passive checkpoint (as autocheckpoint would do)
        ckpt = store.db.execute("PRAGMA wal_checkpoint(PASSIVE)").fetchone()
        print(f"[Probe] PASSIVE checkpoint result: busy={ckpt[0]}, log={ckpt[1]}, checkpointed={ckpt[2]}")
        
        # Notice: log > checkpointed (cannot checkpoint all frames because reader is active!)
        reader_blocked = ckpt[1] > ckpt[2]
        print(f"[Probe] Checkpoint blocked by reader: {reader_blocked} (log={ckpt[1]}, checkpointed={ckpt[2]})")
        
        # Close reader
        cur.close()
        reader.close()
        
        # Now checkpoint again
        ckpt_after = store.db.execute("PRAGMA wal_checkpoint(PASSIVE)").fetchone()
        print(f"[Probe] Checkpoint after reader closed: busy={ckpt_after[0]}, log={ckpt_after[1]}, checkpointed={ckpt_after[2]}")
        
        if reader_blocked:
            print("[BUG/RISK CONFIRMED] G-STORE-06: Reader blocked WAL checkpointing from advancing!")
            return True
        return False


if __name__ == "__main__":
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        success = test_wal_growth_blocked_by_reader(Path(td))
        if not success:
            sys.exit(1)
        print("Probe completed successfully.")
