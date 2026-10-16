"""In-memory Top-50 candidate tracker with pure arithmetic ordering and persistence.

Maintains the top 50 discovered realm candidate seeds in memory with zero
per-batch disk bottleneck, matching the exact candidate_leaderboard_v2 ordering.
Provides O(1) cutoff score inspection and periodic serialization to JSON/SQLite.
"""
import copy
import heapq
import json
import sqlite3
from typing import Any, Dict, List, Optional, Tuple


class RevStr:
    """Reversed string wrapper for binary lexical comparison in min-heaps.

    In a min-heap storing (key, ...), smaller keys represent worse candidates.
    ORDER_V2 orders candidates by `id ASC` (smaller lexical ID is better).
    Therefore, a better candidate (smaller id) must have a larger RevStr key,
    and a worse candidate (larger id) must have a smaller RevStr key.
    """
    __slots__ = ('s',)

    def __init__(self, s: str):
        self.s = str(s)

    def __lt__(self, other: Any) -> bool:
        if isinstance(other, RevStr):
            return self.s > other.s
        return self.s > str(other)

    def __le__(self, other: Any) -> bool:
        if isinstance(other, RevStr):
            return self.s >= other.s
        return self.s >= str(other)

    def __gt__(self, other: Any) -> bool:
        if isinstance(other, RevStr):
            return self.s < other.s
        return self.s < str(other)

    def __ge__(self, other: Any) -> bool:
        if isinstance(other, RevStr):
            return self.s <= other.s
        return self.s <= str(other)

    def __eq__(self, other: Any) -> bool:
        if isinstance(other, RevStr):
            return self.s == other.s
        return self.s == str(other)

    def __ne__(self, other: Any) -> bool:
        if isinstance(other, RevStr):
            return self.s != other.s
        return self.s != str(other)

    def __repr__(self) -> str:
        return f"RevStr({self.s!r})"


class Top50Tracker:
    """Bounded in-memory priority queue maintaining the top N candidates."""

    def __init__(self, capacity: int = 50):
        if capacity < 1:
            raise ValueError("Capacity must be at least 1")
        self.capacity = capacity
        # Min-heap storing tuples: (sort_key, insertion_index, record)
        # sort_key is constructed so that WORSE candidates have SMALLER keys,
        # placing the worst candidate among the top N at root (index 0).
        self._heap: List[Tuple[Tuple[Any, ...], int, Dict[str, Any]]] = []
        self._seed_map: Dict[str, Tuple[Tuple[Any, ...], int, Dict[str, Any]]] = {}
        self._counter: int = 0

    def _extract_seed(self, record: Dict[str, Any]) -> str:
        anchor = record['anchors'][0] if (isinstance(record.get('anchors'), list) and record['anchors']) else record
        return str(record.get('seed') or anchor.get('seed') or '')

    def _extract_key(self, record: Dict[str, Any]) -> Tuple[int, int, int, int, int, int, int, RevStr]:
        """Extract arithmetic ranking tuple matching ORDER_V2.

        ORDER_V2: ranking_tier ASC, smart_score DESC, unmet_requirements ASC,
                  radial_key ASC, origin_distance_squared ASC, eval_cx ASC, eval_cz ASC, id ASC.

        For min-heap (worst at root), worse candidate must have smaller key:
        - tier: higher is worse -> -tier
        - score: lower is worse -> +score
        - misses: higher is worse -> -misses
        - radial_key: higher is worse -> -radial_key
        - orig_dist_sq: higher is worse -> -orig_dist_sq
        - eval_cx: higher is worse -> -eval_cx
        - eval_cz: higher is worse -> -eval_cz
        - id: higher is worse -> RevStr(raw_id)
        """
        anchor = record['anchors'][0] if (isinstance(record.get('anchors'), list) and record['anchors']) else record

        # Tier: 0 for PREDICTED/VERIFIED, 1 for PENDING, 2 for FAILED/NEAR_MISS
        if 'ranking_tier' in record:
            tier = int(record['ranking_tier'])
        elif 'ranking_tier' in anchor:
            tier = int(anchor['ranking_tier'])
        else:
            qual = record.get('qualification') or anchor.get('qualification')
            if qual in ('VERIFIED', 'PREDICTED'):
                tier = 0
            elif qual == 'PENDING':
                tier = 1
            else:
                tier = 2

        score = int(
            record.get('baseline_score_observed')
            or anchor.get('baseline_score_observed')
            or record.get('baseline_score')
            or anchor.get('baseline_score')
            or (record.get('ranking', {}).get('score') if isinstance(record.get('ranking'), dict) else None)
            or (anchor.get('ranking', {}).get('score') if isinstance(anchor.get('ranking'), dict) else None)
            or 0
        )

        deficits = record.get('deficit_categories') or anchor.get('deficit_categories')
        misses = len(deficits) if isinstance(deficits, list) else int(record.get('unmet_requirements', anchor.get('unmet_requirements', 0)))

        radial_key = int(
            record.get('radial_key')
            or anchor.get('radial_key')
            or (record.get('ranking', {}).get('radial_key') if isinstance(record.get('ranking'), dict) else None)
            or (anchor.get('ranking', {}).get('radial_key') if isinstance(anchor.get('ranking'), dict) else None)
            or 0
        )

        orig_dist_sq = int(
            record.get('origin_distance_squared')
            or anchor.get('origin_distance_squared')
            or (record.get('ranking', {}).get('origin_distance_squared') if isinstance(record.get('ranking'), dict) else None)
            or (anchor.get('ranking', {}).get('origin_distance_squared') if isinstance(anchor.get('ranking'), dict) else None)
            or 0
        )

        center = record.get('evaluation_center') or anchor.get('evaluation_center')
        if not center or len(center) < 2:
            cx, cz = 0, 0
        else:
            cx, cz = int(center[0]), int(center[1])

        raw_id = str(record.get('id') or anchor.get('id') or record.get('seed') or anchor.get('seed') or '')

        return (-tier, score, -misses, -radial_key, -orig_dist_sq, -cx, -cz, RevStr(raw_id))

    def observe(self, record: Dict[str, Any]) -> bool:
        """Observe a candidate record. Returns True if accepted into top N, False otherwise.

        Deduplicates by seed: if the exact same seed already exists in the heap,
        updates it only if the new record is better, avoiding duplicate slots.
        Deep copies record on insertion so external mutations don't invalidate heap keys.
        """
        record_copy = copy.deepcopy(record)
        key = self._extract_key(record_copy)
        seed = self._extract_seed(record_copy)

        if seed and seed in self._seed_map:
            existing_entry = self._seed_map[seed]
            existing_key = existing_entry[0]
            if key <= existing_key:
                return False
            # Better observation for the same seed: replace it in-place
            self._counter += 1
            new_entry = (key, self._counter, record_copy)
            self._seed_map[seed] = new_entry
            old_counter = existing_entry[1]
            for i, item in enumerate(self._heap):
                if item[1] == old_counter:
                    self._heap[i] = new_entry
                    heapq.heapify(self._heap)
                    break
            return True

        self._counter += 1
        entry = (key, self._counter, record_copy)

        if len(self._heap) < self.capacity:
            heapq.heappush(self._heap, entry)
            if seed:
                self._seed_map[seed] = entry
            return True

        # When at capacity, compare with current 50th-best (the heap root)
        if key > self._heap[0][0]:
            popped = heapq.heappushpop(self._heap, entry)
            popped_seed = self._extract_seed(popped[2])
            if popped_seed and popped_seed in self._seed_map:
                del self._seed_map[popped_seed]
            if seed:
                self._seed_map[seed] = entry
            return True

        return False

    def cutoff_score(self) -> Optional[int]:
        """Return the minimum score required to displace the current Nth-best candidate.

        Returns None if fewer than capacity candidates have been observed.
        """
        if len(self._heap) < self.capacity:
            return None
        return self._heap[0][0][1]

    def cutoff_key(self) -> Optional[Tuple[Any, ...]]:
        """Return the raw sorting key of the Nth-best candidate."""
        if len(self._heap) < self.capacity:
            return None
        return self._heap[0][0]

    def __len__(self) -> int:
        return len(self._heap)

    def top_records(self) -> List[Dict[str, Any]]:
        """Return records sorted from Rank 1 (best) to Rank N (worst)."""
        # In our heap, larger key is better. So descending order gives Rank 1 first.
        sorted_entries = sorted(self._heap, key=lambda item: item[0], reverse=True)
        return [copy.deepcopy(item[2]) for item in sorted_entries]

    def save_to_json(self, path: str) -> None:
        """Atomically dump current top records to a JSON file."""
        records = self.top_records()
        tmp_path = f"{path}.tmp"
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(records, f, indent=2)
        import os
        os.replace(tmp_path, path)

    def load_from_json(self, path: str) -> int:
        """Load candidate records from JSON file. Returns count loaded."""
        with open(path, "r", encoding="utf-8") as f:
            records = json.load(f)
        count = 0
        for r in records:
            if isinstance(r, dict):
                self.observe(r)
                count += 1
        return count

    def save_to_sqlite(self, db_or_conn: Any, table_name: str = "top_candidates", *, transactional: bool = True) -> None:
        """Save current top records into SQLite table."""
        records = self.top_records()
        is_path = isinstance(db_or_conn, (str, bytes)) or hasattr(db_or_conn, '__fspath__')
        conn = sqlite3.connect(db_or_conn) if is_path else getattr(db_or_conn, 'db', db_or_conn)
        try:
            with conn:
                conn.execute(f"""
                    CREATE TABLE IF NOT EXISTS {table_name} (
                        rank INTEGER PRIMARY KEY,
                        seed TEXT NOT NULL,
                        score INTEGER NOT NULL,
                        result TEXT NOT NULL
                    )
                """)
                conn.execute(f"DELETE FROM {table_name}")
                rows = []
                for rank, rec in enumerate(records, start=1):
                    anchor = rec['anchors'][0] if (isinstance(rec.get('anchors'), list) and rec['anchors']) else rec
                    raw_seed = str(rec.get('seed') or anchor.get('seed') or '')
                    score = int(
                        anchor.get('baseline_score_observed')
                        or anchor.get('baseline_score')
                        or rec.get('baseline_score_observed')
                        or rec.get('baseline_score')
                        or (anchor.get('ranking', {}).get('score') if isinstance(anchor.get('ranking'), dict) else None)
                        or (rec.get('ranking', {}).get('score') if isinstance(rec.get('ranking'), dict) else None)
                        or 0
                    )
                    rows.append((rank, raw_seed, score, json.dumps(rec)))
                if rows:
                    conn.executemany(
                        f"INSERT INTO {table_name} (rank, seed, score, result) VALUES (?, ?, ?, ?)",
                        rows
                    )
        finally:
            if is_path:
                conn.close()

    def flush(self, db_or_conn: Any, table_name: str = "top_candidates") -> None:
        """Periodic flush of current top records to SQLite."""
        self.save_to_sqlite(db_or_conn, table_name=table_name, transactional=True)

    def flush_transactional(self, db_or_conn: Any, table_name: str = "top_candidates") -> None:
        """Atomic transactional save of current top records to SQLite."""
        self.save_to_sqlite(db_or_conn, table_name=table_name, transactional=True)
