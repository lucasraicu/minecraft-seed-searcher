"""Indexed baseline ranking derived from evidence, without rewriting durable records."""

# Keep these expressions identical in the index and view so SQLite can satisfy
# ORDER BY with the index. JSON remains the authoritative, retry-digested record.
DOCUMENT = "CASE WHEN json_valid(result) THEN result ELSE '{}' END"


def field(path):
    return f"json_extract(({DOCUMENT}),'$.{path}')"


CLASS = field('retention.classification')
DYNAMIC = f"{field('screening_revision')}='dynamic-envelope-1664-v1'"
DEFICITS = f"COALESCE(json_array_length({field('deficit_categories')}),0)"
TIER = f"CASE WHEN {DYNAMIC} THEN {DEFICITS} ELSE CASE qualification WHEN 'VERIFIED' THEN 0 WHEN 'PREDICTED' THEN 1 WHEN 'FAILED' THEN 4 ELSE CASE WHEN {CLASS}='NEAR_MISS' THEN 2 ELSE 3 END END END"
MISSES = f"CASE WHEN {CLASS}='NEAR_MISS' THEN CAST({field('retention.unmet_requirements')} AS INTEGER) ELSE 0 END"
MIDPOINT = f"(CAST({field('baseline_score_uncertainty.prediction_score_interval[0]')} AS REAL)+CAST({field('baseline_score_uncertainty.prediction_score_interval[1]')} AS REAL))/2"
SCORE = f"CASE WHEN {CLASS}='NEAR_MISS' THEN CAST({field('baseline_score_observed')} AS REAL) ELSE COALESCE(CAST({field('baseline_score')} AS REAL),{MIDPOINT},CAST({field('baseline_score_observed')} AS REAL)) END"
RADIAL = f"CASE WHEN {DYNAMIC} THEN COALESCE(CAST({field('weighted_radial_dist')} AS REAL),1e30) ELSE 0 END"
ORIGIN = f"CASE WHEN {DYNAMIC} THEN COALESCE(CAST({field('origin_distance')} AS REAL),1e30) ELSE 0 END"
ORDER = "ranking_tier,unmet_requirements,smart_score DESC,weighted_radial_dist,origin_distance,id"


def order_for(db):
    """Read old run views without mutating checkpoints merely to display them."""
    columns={row[1] for row in db.execute('PRAGMA table_info(candidate_leaderboard_view)')}
    return ORDER if {'weighted_radial_dist','origin_distance'}<=columns else "ranking_tier,unmet_requirements,smart_score DESC,id"



def install(db):
    """An additive, transactionally installed view/index; valid for legacy runs too."""
    view=f"""CREATE VIEW candidate_leaderboard_view AS
            SELECT id,idx,seed,qualification,result,{CLASS} AS retention_classification,
                   {TIER} AS ranking_tier,{MISSES} AS unmet_requirements,{SCORE} AS smart_score,
                   {RADIAL} AS weighted_radial_dist,{ORIGIN} AS origin_distance
            FROM candidates WHERE NOT EXISTS (SELECT 1 FROM meta
              WHERE key='rescore_revision' AND json_type(value)!='null'
                AND COALESCE(json_extract(value,'$.status'),'')!='complete')"""
    index=f"CREATE INDEX candidate_leaderboard ON candidates(({TIER}),({MISSES}),({SCORE}) DESC,({RADIAL}),({ORIGIN}),id)"
    if db.in_transaction:raise ValueError('Finish caller transaction before installing leaderboard')
    installed_index=db.execute("SELECT sql FROM sqlite_master WHERE type='index' AND name='candidate_leaderboard'").fetchone()
    installed_view=db.execute("SELECT sql FROM sqlite_master WHERE type='view' AND name='candidate_leaderboard_view'").fetchone()
    if installed_index==(index,) and installed_view==(view,):return
    with db:
        db.execute('BEGIN IMMEDIATE')
        previous_index=db.execute("SELECT sql FROM sqlite_master WHERE type='index' AND name='candidate_leaderboard'").fetchone()
        if previous_index is None:db.execute(index)
        elif previous_index[0]!=index:
            db.execute('DROP INDEX candidate_leaderboard');db.execute(index)
        previous=db.execute("SELECT sql FROM sqlite_master WHERE type='view' AND name='candidate_leaderboard_view'").fetchone()
        if previous is None:db.execute(view)
        elif previous[0]!=view:
            db.execute('DROP VIEW candidate_leaderboard_view');db.execute(view)


def rows(db, limit):
    if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 10000:
        raise ValueError('Leaderboard limit must be 1–10,000')
    return db.execute(f"SELECT result,smart_score,ranking_tier,unmet_requirements FROM candidate_leaderboard_view ORDER BY {order_for(db)} LIMIT ?", (limit,))
