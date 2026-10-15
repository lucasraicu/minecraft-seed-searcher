"""Indexed baseline ranking derived from evidence, without rewriting durable records."""

# Keep these expressions identical in the index and view so SQLite can satisfy
# ORDER BY with the index. JSON remains the authoritative, retry-digested record.
DOCUMENT = "CASE WHEN json_valid(result) THEN result ELSE '{}' END"


def field(path):
    return f"json_extract(({DOCUMENT}),'$.{path}')"


CLASS = field('retention.classification')
DYNAMIC_V1 = f"{field('screening_revision')}='dynamic-envelope-1664-v1'"
DYNAMIC_V2 = f"{field('screening_revision')}='dynamic-envelope-1664-v2'"
DEFICITS = f"COALESCE(json_array_length({field('deficit_categories')}),0)"
HAS_DEFICITS = f"json_type({field('deficit_categories')})='array'"
TIER = (
    f"CASE WHEN {DYNAMIC_V2} THEN CASE WHEN qualification IN ('VERIFIED','PREDICTED') THEN 0 "
    f"WHEN qualification='PENDING' THEN 1 ELSE 2 END "
    f"WHEN {DYNAMIC_V1} THEN CASE WHEN qualification IN ('VERIFIED','PREDICTED') THEN {DEFICITS} "
    f"WHEN qualification='PENDING' THEN 3 ELSE 4 END "
    f"ELSE CASE qualification WHEN 'VERIFIED' THEN 0 WHEN 'PREDICTED' THEN 1 WHEN 'FAILED' THEN 4 "
    f"ELSE CASE WHEN {CLASS}='NEAR_MISS' THEN 2 ELSE 3 END END END"
)
MISSES = (
    f"CASE WHEN {HAS_DEFICITS} THEN {DEFICITS} "
    f"WHEN {CLASS}='NEAR_MISS' THEN CAST({field('retention.unmet_requirements')} AS INTEGER) ELSE 0 END"
)
MIDPOINT = f"(CAST({field('baseline_score_uncertainty.prediction_score_interval[0]')} AS REAL)+CAST({field('baseline_score_uncertainty.prediction_score_interval[1]')} AS REAL))/2"
SCORE = f"CASE WHEN {CLASS}='NEAR_MISS' THEN CAST({field('baseline_score_observed')} AS REAL) ELSE COALESCE(CAST({field('combined_score')} AS REAL),CAST({field('baseline_score')} AS REAL),{MIDPOINT},CAST({field('baseline_score_observed')} AS REAL)) END"
RADIAL = f"CASE WHEN {DYNAMIC_V1} THEN COALESCE(CAST({field('weighted_radial_dist')} AS REAL),1e30) ELSE 0 END"
ORIGIN = f"CASE WHEN {DYNAMIC_V1} THEN COALESCE(CAST({field('origin_distance')} AS REAL),1e30) ELSE 0 END"
IS_NOT_V2 = f"CASE WHEN {DYNAMIC_V2} THEN 0 ELSE 1 END"
RADIAL_KEY = f"CASE WHEN {DYNAMIC_V2} THEN COALESCE(CAST({field('radial_key')} AS INTEGER),CAST({field('ranking.radial_key')} AS INTEGER),0) ELSE 0 END"
ORIGIN_SQ = f"CASE WHEN {DYNAMIC_V2} THEN COALESCE(CAST({field('origin_distance_squared')} AS INTEGER),CAST({field('ranking.origin_distance_squared')} AS INTEGER),0) ELSE 0 END"
EVAL_CX = f"CASE WHEN {DYNAMIC_V2} THEN COALESCE(CAST({field('evaluation_center[0]')} AS INTEGER),0) ELSE 0 END"
EVAL_CZ = f"CASE WHEN {DYNAMIC_V2} THEN COALESCE(CAST({field('evaluation_center[1]')} AS INTEGER),0) ELSE 0 END"

ORDER = "ranking_tier,unmet_requirements,smart_score DESC,weighted_radial_dist,origin_distance,id"
ORDER_V1 = ORDER
ORDER_V2 = "ranking_tier,smart_score DESC,unmet_requirements,radial_key,origin_distance_squared,eval_cx,eval_cz,id"


def order_for(db):
    """Read old run views without mutating checkpoints merely to display them."""
    row = db.execute(f"SELECT 1 FROM candidates WHERE {DYNAMIC_V2} LIMIT 1").fetchone()
    if row:
        return ORDER_V2
    meta_id = db.execute("SELECT value FROM meta WHERE key='identity'").fetchone()
    if meta_id and 'dynamic-envelope-1664-v2' in meta_id[0]:
        return ORDER_V2
    columns={row[1] for row in db.execute('PRAGMA table_info(candidate_leaderboard_view)')}
    return ORDER if {'weighted_radial_dist','origin_distance'}<=columns else "ranking_tier,unmet_requirements,smart_score DESC,id"



def install(db):
    """An additive, transactionally installed view/index; valid for legacy runs too."""
    view=f"""CREATE VIEW candidate_leaderboard_view AS
            SELECT id,idx,seed,qualification,result,{CLASS} AS retention_classification,
                   {TIER} AS ranking_tier,{MISSES} AS unmet_requirements,{SCORE} AS smart_score,
                   {RADIAL} AS weighted_radial_dist,{ORIGIN} AS origin_distance,
                   {IS_NOT_V2} AS is_not_v2,{RADIAL_KEY} AS radial_key,
                   {ORIGIN_SQ} AS origin_distance_squared,{EVAL_CX} AS eval_cx,{EVAL_CZ} AS eval_cz
            FROM candidates WHERE NOT EXISTS (SELECT 1 FROM meta
              WHERE key='rescore_revision' AND json_type(value)!='null'
                AND COALESCE(json_extract(value,'$.status'),'')!='complete')"""
    index=f"CREATE INDEX candidate_leaderboard ON candidates(({TIER}),({MISSES}),({SCORE}) DESC,({RADIAL}),({ORIGIN}),id)"
    index_v2=f"CREATE INDEX candidate_leaderboard_v2 ON candidates(({TIER}),({SCORE}) DESC,({MISSES}),({RADIAL_KEY}),({ORIGIN_SQ}),({EVAL_CX}),({EVAL_CZ}),id)"
    if db.in_transaction:raise ValueError('Finish caller transaction before installing leaderboard')
    installed_index=db.execute("SELECT sql FROM sqlite_master WHERE type='index' AND name='candidate_leaderboard'").fetchone()
    installed_index_v2=db.execute("SELECT sql FROM sqlite_master WHERE type='index' AND name='candidate_leaderboard_v2'").fetchone()
    installed_view=db.execute("SELECT sql FROM sqlite_master WHERE type='view' AND name='candidate_leaderboard_view'").fetchone()
    if installed_index==(index,) and installed_index_v2==(index_v2,) and installed_view==(view,):return
    with db:
        db.execute('BEGIN IMMEDIATE')
        previous_index=db.execute("SELECT sql FROM sqlite_master WHERE type='index' AND name='candidate_leaderboard'").fetchone()
        if previous_index is None:db.execute(index)
        elif previous_index[0]!=index:
            db.execute('DROP INDEX candidate_leaderboard');db.execute(index)
        previous_index_v2=db.execute("SELECT sql FROM sqlite_master WHERE type='index' AND name='candidate_leaderboard_v2'").fetchone()
        if previous_index_v2 is None:db.execute(index_v2)
        elif previous_index_v2[0]!=index_v2:
            db.execute('DROP INDEX candidate_leaderboard_v2');db.execute(index_v2)
        previous=db.execute("SELECT sql FROM sqlite_master WHERE type='view' AND name='candidate_leaderboard_view'").fetchone()
        if previous is None:db.execute(view)
        elif previous[0]!=view:
            db.execute('DROP VIEW candidate_leaderboard_view');db.execute(view)


def rows(db, limit):
    if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 10000:
        raise ValueError('Leaderboard limit must be 1–10,000')
    return db.execute(f"SELECT result,smart_score,ranking_tier,unmet_requirements FROM candidate_leaderboard_view ORDER BY {order_for(db)} LIMIT ?", (limit,))
