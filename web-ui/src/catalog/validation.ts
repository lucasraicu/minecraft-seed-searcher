import type {CatalogFavorite,FilterRow} from './types';

export function filterLimitsError(rows:FilterRow[]):string|null {
  if(rows.length>12)return 'At most 12 filter rows are supported. Remove a row before querying.';
  if(rows.some(row=>row.kind==='biome_witness'&&new Set(row.any_of).size>16))return 'At most 16 alternatives are supported per biome row. Remove an alternative before querying.';
  return null;
}

export function serializeRows(rows:FilterRow[]):Array<Record<string,unknown>> {
  const error=filterLimitsError(rows);if(error)throw Error(error);
  return rows.map(row=>({rule:row.rule,kind:row.kind,
    scope:row.scope.kind==='inside_border'?{kind:'inside_border'}:{kind:'near_base',radius:row.scope.radius},
    ...(row.rule==='preferred'?{importance:row.importance||3}:{}),
    ...(row.kind==='structure_count'
      ? {feature:row.feature,at_least:row.at_least}
      : {any_of:[...new Set(row.any_of)]})}));
}

export function validFavorites(value:unknown):CatalogFavorite[] {
  if(!Array.isArray(value)||value.length>1000)throw Error('Favorites must contain at most 1000 entries');
  const seen=new Set<string>();const result:CatalogFavorite[]=[];
  for(const f of value){
    if(!f||typeof f!=='object'||typeof f.seed!=='string'||! /^-?(0|[1-9][0-9]*)$/.test(f.seed)||f.seed==='-0')throw Error('Invalid seed string');
    const seed=BigInt(f.seed);if(seed<-(1n<<63n)||seed>=(1n<<63n))throw Error('Seed exceeds signed64 range');
    for(const key of ['world_id','layout_id','snapshot_id'])if(typeof f[key]!=='string'||! /^[a-f0-9]{64}$/.test(f[key]))throw Error('Invalid favorite identity');
    const id=`${f.snapshot_id}:${f.world_id}:${f.layout_id}`;
    if(f.id!==id||![2048,4096,8192].includes(f.border_side)||!['origin','recommended','world_spawn_estimated','world_spawn_observed'].includes(f.anchor_mode)||!Number.isFinite(f.score)||!Number.isFinite(f.saved_at))throw Error('Invalid favorite metadata');
    if(f.bounds&&(!Array.isArray(f.bounds)||f.bounds.length!==4||!f.bounds.every(Number.isSafeInteger)))throw Error('Invalid favorite bounds');
    if(!seen.has(id)){seen.add(id);result.push({id,seed:f.seed,world_id:f.world_id,layout_id:f.layout_id,snapshot_id:f.snapshot_id,border_side:f.border_side,
      anchor_mode:f.anchor_mode,score:f.score,saved_at:f.saved_at,...(f.bounds?{bounds:f.bounds}: {})});}
  }
  return result;
}
