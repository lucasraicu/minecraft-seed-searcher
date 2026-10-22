# Actual publication transaction

        # Single atomic metadata transaction
        with self._lock:
            cursor = self.conn.cursor()
            cursor.execute("BEGIN IMMEDIATE;")
            try:
                # Insert artifact refs
                for m in new_artifacts.values():
                    cursor.execute(
                        """
                        INSERT OR IGNORE INTO artifact_ref
                        (sha256, relative_key, byte_length, uncompressed_length, codec, published_at)
                        VALUES (?, ?, ?, ?, ?, ?);
                        """,
                        (m["sha256"], m["relative_key"], m["byte_length"], m["uncompressed_length"], m["codec"], now),
                    )

                # Insert leaf segments
                for seg_id, (m_sha, wid, l_cnt) in new_leaf_records.items():
                    cursor.execute(
                        """
                        INSERT OR IGNORE INTO leaf_segment
                        (segment_id, manifest_sha256, world_id, layout_count, created_at)
                        VALUES (?, ?, ?, ?, ?);
                        """,
                        (seg_id, m_sha, wid, l_cnt, now),
                    )

                # Insert snapshot root
                header_json_str = json.dumps(current_header, sort_keys=True, separators=(",", ":"))
                cursor.execute(
                    """
                    INSERT INTO snapshot_root
                    (snapshot_id, parent_id, manifest_sha256, tree_root_sha256, header_json, world_count, layout_count, published_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?);
                    """,
                    (
                        snapshot_id,
                        parent,
                        snap_manifest["sha256"],
                        tree_root_manifest["sha256"],
                        header_json_str,
                        len(all_worlds),
                        total_layouts,
                        now,
                    ),
                )

                # Insert observation refs
                cursor.executemany(
                    """
                    INSERT INTO observation_ref
                    (snapshot_id, world_id, observation_id, seed, manifest_sha256)
                    VALUES (?, ?, ?, ?, ?);
                    """,
                    generation_obs_refs,
                )

                # Insert snapshot membership
                membership_rows = [
                    (snapshot_id, item["segment_id"], ordinal)
                    for ordinal, item in enumerate(all_leaf_items)
                ]
                cursor.executemany(
                    """
                    INSERT INTO snapshot_membership
                    (snapshot_id, segment_id, ordinal)
                    VALUES (?, ?, ?);
                    """,
                    membership_rows,
                )

                if prepare_publication is not None:
                    prepare_publication(self, snapshot_id)
                cursor.execute("COMMIT;")
            except Exception:
                cursor.execute("ROLLBACK;")
                raise

        return snapshot_id


Callbacks run before commit. Artifact/root ID derivation and checks occur earlier. Existing snapshot IDs return idempotently before this transaction; refresh calls prepare separately for their readiness readback. SQL errors/callback failures roll back metadata. Independent connection and os._exit child tests passed.
