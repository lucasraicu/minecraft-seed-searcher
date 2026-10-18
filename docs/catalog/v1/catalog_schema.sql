-- Proposed pilot schema only. Never applied to the personal database.
PRAGMA foreign_keys = ON;
CREATE TABLE schema_meta (revision TEXT PRIMARY KEY, status TEXT NOT NULL);
INSERT INTO schema_meta VALUES ('catalog-proposed-v1','not_implemented');
CREATE TABLE world (
    world_id TEXT PRIMARY KEY,
    edition TEXT NOT NULL CHECK (edition='bedrock'),
    game_build_id TEXT NOT NULL,
    world_settings_id TEXT NOT NULL,
    seed_i64 INTEGER NOT NULL CHECK (typeof(seed_i64)='integer'),
    seed_order_u64_be BLOB NOT NULL CHECK (length(seed_order_u64_be)=8),
    created_at TEXT NOT NULL,
    UNIQUE (edition,game_build_id,world_settings_id,seed_i64)
);
CREATE TABLE artifact (
    sha256 TEXT PRIMARY KEY CHECK (length(sha256)=64),
    relative_key TEXT NOT NULL UNIQUE,
    format_revision TEXT NOT NULL,
    byte_length INTEGER NOT NULL CHECK (byte_length>=0),
    published_at TEXT NOT NULL
);
CREATE TABLE observation_set (
    observation_id TEXT PRIMARY KEY,
    world_id TEXT NOT NULL REFERENCES world(world_id),
    model_id TEXT NOT NULL, extractor_revision TEXT NOT NULL,
    registry_revision TEXT NOT NULL, settings_hash TEXT NOT NULL,
    manifest_sha256 TEXT REFERENCES artifact(sha256),
    status TEXT NOT NULL CHECK (status IN ('pending','partial','complete','failed')),
    UNIQUE (world_id,model_id,extractor_revision,registry_revision,settings_hash)
);
CREATE TABLE coverage_map (
    observation_id TEXT NOT NULL REFERENCES observation_set(observation_id),
    feature_id TEXT NOT NULL, dimension TEXT NOT NULL,
    method_id TEXT NOT NULL, sample_y INTEGER NOT NULL,
    tile_origin_x INTEGER NOT NULL, tile_origin_z INTEGER NOT NULL,
    tiles_x INTEGER NOT NULL CHECK (tiles_x>0), tiles_z INTEGER NOT NULL CHECK (tiles_z>0),
    status_bits BLOB NOT NULL,
    artifact_manifest_sha256 TEXT REFERENCES artifact(sha256),
    CHECK (length(status_bits)=(tiles_x*tiles_z+3)/4),
    -- Two bits/tile: unknown=0, partial=1, complete=2, failed=3.
    -- sample_y=-32768 is the non-Y-specific structure inventory method sentinel.
    PRIMARY KEY (observation_id,feature_id,dimension,method_id,sample_y)
);
CREATE TABLE anchor (
    anchor_id TEXT PRIMARY KEY, world_id TEXT NOT NULL REFERENCES world(world_id),
    dimension TEXT NOT NULL, x INTEGER NOT NULL, z INTEGER NOT NULL,
    CHECK (x BETWEEN -2147483648 AND 2147483647),
    CHECK (z BETWEEN -2147483648 AND 2147483647),
    UNIQUE (world_id,dimension,x,z)
);
CREATE TABLE anchor_role (
    anchor_id TEXT NOT NULL REFERENCES anchor(anchor_id),
    role TEXT NOT NULL CHECK (role IN ('origin','settlement','spawn_estimated','spawn_observed')),
    evidence_revision TEXT NOT NULL, evidence_sha256 TEXT REFERENCES artifact(sha256),
    PRIMARY KEY (anchor_id,role,evidence_revision)
);
CREATE TABLE spawn_observation (
    spawn_id TEXT PRIMARY KEY, world_id TEXT NOT NULL REFERENCES world(world_id),
    status TEXT NOT NULL CHECK (status IN ('unknown','estimated','observed')),
    reference_kind TEXT NOT NULL, source_revision TEXT NOT NULL,
    anchor_id TEXT REFERENCES anchor(anchor_id), y INTEGER,
    evidence_sha256 TEXT REFERENCES artifact(sha256),
    CHECK ((status='unknown' AND anchor_id IS NULL) OR (status<>'unknown' AND anchor_id IS NOT NULL))
);
CREATE TABLE border_profile (
    side INTEGER PRIMARY KEY CHECK (side>0 AND side%2=0),
    rollout_phase TEXT NOT NULL, runtime_enabled INTEGER NOT NULL DEFAULT 0 CHECK (runtime_enabled IN (0,1))
);
INSERT INTO border_profile(side,rollout_phase) VALUES (2048,'initial'),(4096,'initial'),(8192,'initial');
CREATE TABLE layout (
    layout_id TEXT PRIMARY KEY, anchor_id TEXT NOT NULL REFERENCES anchor(anchor_id),
    observation_id TEXT NOT NULL REFERENCES observation_set(observation_id),
    border_side INTEGER NOT NULL REFERENCES border_profile(side),
    geometry_revision TEXT NOT NULL,
    UNIQUE (anchor_id,observation_id,border_side,geometry_revision)
);
CREATE VIEW layout_bounds AS
SELECT l.layout_id,a.world_id,a.dimension,a.x,a.z,l.border_side,
       a.x-l.border_side/2 AS min_x,a.x+l.border_side/2 AS max_x_exclusive,
       a.z-l.border_side/2 AS min_z,a.z+l.border_side/2 AS max_z_exclusive
FROM layout l JOIN anchor a USING(anchor_id);
CREATE TABLE layout_summary (
    layout_id TEXT NOT NULL REFERENCES layout(layout_id),
    summary_revision TEXT NOT NULL,
    counts_u32le BLOB NOT NULL CHECK (length(counts_u32le)=224),
    structure_nearest_d2_u32le BLOB NOT NULL CHECK (length(structure_nearest_d2_u32le)=56),
    biome_nearest_d2_u32le BLOB NOT NULL CHECK (length(biome_nearest_d2_u32le)=36),
    biome_witness_refs_u32le BLOB NOT NULL CHECK (length(biome_witness_refs_u32le)=36),
    scope_complete_bits BLOB NOT NULL CHECK (length(scope_complete_bits)=12),
    PRIMARY KEY (layout_id,summary_revision)
);
CREATE TABLE objective (
    objective_id TEXT PRIMARY KEY, policy_revision TEXT NOT NULL,
    definition_json TEXT NOT NULL, capacity INTEGER NOT NULL CHECK (capacity>0)
);
CREATE TABLE membership (
    objective_id TEXT NOT NULL REFERENCES objective(objective_id),
    world_id TEXT NOT NULL REFERENCES world(world_id),
    layout_id TEXT NOT NULL REFERENCES layout(layout_id),
    rank_tuple_json TEXT NOT NULL,
    PRIMARY KEY (objective_id,world_id)
);
CREATE TABLE catalog_snapshot (
    snapshot_id TEXT PRIMARY KEY, manifest_sha256 TEXT NOT NULL REFERENCES artifact(sha256),
    policy_revision TEXT NOT NULL, registry_revision TEXT NOT NULL,
    published_at TEXT NOT NULL
);
CREATE TABLE index_segment (
    snapshot_id TEXT NOT NULL REFERENCES catalog_snapshot(snapshot_id),
    segment_id INTEGER NOT NULL, manifest_sha256 TEXT NOT NULL REFERENCES artifact(sha256),
    layout_rows INTEGER NOT NULL CHECK (layout_rows BETWEEN 0 AND 1048576),
    PRIMARY KEY (snapshot_id,segment_id)
);
CREATE TABLE scan_shard (
    shard_id TEXT PRIMARY KEY, sequence_id TEXT NOT NULL,
    start_index_decimal TEXT NOT NULL CHECK (length(start_index_decimal)=20),
    end_index_decimal TEXT NOT NULL CHECK (length(end_index_decimal)=20),
    policy_revision TEXT NOT NULL,
    state TEXT NOT NULL CHECK (state IN ('pending','leased','complete','failed')),
    worker_id TEXT, lease_generation INTEGER NOT NULL DEFAULT 0, lease_expires_at TEXT,
    receipt_sha256 TEXT REFERENCES artifact(sha256),
    UNIQUE (sequence_id,start_index_decimal,end_index_decimal,policy_revision)
);
CREATE TABLE user_account (user_id TEXT PRIMARY KEY, created_at TEXT NOT NULL);
CREATE TABLE billing_event (
    provider TEXT NOT NULL, event_id TEXT NOT NULL, payload_sha256 TEXT NOT NULL,
    received_at TEXT NOT NULL, processed_at TEXT,
    state TEXT NOT NULL CHECK (state IN ('received','applied','failed')),
    PRIMARY KEY (provider,event_id)
);
CREATE TABLE entitlement (
    entitlement_id TEXT PRIMARY KEY, user_id TEXT NOT NULL REFERENCES user_account(user_id),
    tier TEXT NOT NULL CHECK (tier IN ('free','plus')), source_kind TEXT NOT NULL,
    effective_from TEXT NOT NULL, effective_until TEXT,
    provider_object_id TEXT, revision INTEGER NOT NULL
);
CREATE TABLE usage_bucket (
    user_id TEXT NOT NULL REFERENCES user_account(user_id), utc_day TEXT NOT NULL,
    counter_kind TEXT NOT NULL, used INTEGER NOT NULL CHECK (used>=0),
    PRIMARY KEY (user_id,utc_day,counter_kind)
);
CREATE TABLE saved_search (
    saved_search_id TEXT PRIMARY KEY, user_id TEXT NOT NULL REFERENCES user_account(user_id),
    canonical_request_json TEXT NOT NULL, request_hash TEXT NOT NULL,
    alerts_opt_in INTEGER NOT NULL DEFAULT 0 CHECK (alerts_opt_in IN (0,1)), consent_at TEXT,
    last_snapshot_id TEXT REFERENCES catalog_snapshot(snapshot_id),
    UNIQUE (user_id,request_hash)
);
CREATE TABLE saved_result (
    saved_result_id TEXT PRIMARY KEY, user_id TEXT NOT NULL REFERENCES user_account(user_id),
    world_id TEXT NOT NULL REFERENCES world(world_id),
    snapshot_id TEXT NOT NULL REFERENCES catalog_snapshot(snapshot_id),
    layout_id TEXT NOT NULL REFERENCES layout(layout_id), explanation_json TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE TABLE export_job (
    export_id TEXT PRIMARY KEY, user_id TEXT NOT NULL REFERENCES user_account(user_id),
    saved_result_id TEXT NOT NULL REFERENCES saved_result(saved_result_id),
    state TEXT NOT NULL CHECK (state IN ('queued','running','complete','failed')),
    idempotency_key TEXT NOT NULL, artifact_sha256 TEXT REFERENCES artifact(sha256),
    UNIQUE (user_id,idempotency_key)
);
CREATE INDEX observation_world ON observation_set(world_id);
CREATE INDEX anchors_world ON anchor(world_id);
CREATE INDEX layout_anchor ON layout(anchor_id,border_side);
CREATE INDEX membership_world ON membership(world_id);
CREATE INDEX entitlement_user ON entitlement(user_id,effective_from,effective_until);
CREATE INDEX shard_claim ON scan_shard(state,lease_expires_at);
CREATE INDEX saved_result_owner ON saved_result(user_id,created_at);
-- Application validation additionally enforces same-world foreign-reference
-- consistency, unsigned index bounds, artifact paths, JSON schemas, and leases.
-- This schema is a reference/control layout, not a billion-row serving benchmark.
