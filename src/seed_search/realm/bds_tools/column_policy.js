// Pure interpretation of actual observed blocks. No material proves provenance.
export const COLUMN_POLICY = 'actual-column-v2';
const WATER = new Set(['minecraft:water', 'minecraft:flowing_water']);
const ICE = new Set(['minecraft:ice', 'minecraft:packed_ice', 'minecraft:blue_ice', 'minecraft:frosted_ice']);
export function observeBlock(block,y) {
  let waterlogged=null,waterloggingError=null;
  try {const value=block.isWaterlogged;if(typeof value==='boolean') waterlogged=value;}
  catch(e) {waterloggingError=String(e);}
  let states=null,statesError=null;
  try {states=block.permutation.getAllStates();}catch(error){statesError=String(error);}
  return {y,block:block.typeId,waterlogged,waterloggingError,states,statesError};
}
export function classifySurface(id) {
  if (WATER.has(id)) return 'water';
  if (ICE.has(id)) return 'frozen_cover';
  if (id === 'minecraft:snow_layer') return 'thin_snow_cover';
  if (id === 'minecraft:snow' || id === 'minecraft:snow_block' || id === 'minecraft:powder_snow') return 'snow_cover';
  if (id === 'minecraft:grass_block') return 'terrain_material_candidate';
  if (/(?:_leaves|_log|_wood|_sapling)$/.test(id) ||
      /^minecraft:(?:.*_tulip|azure_bluet|dandelion|poppy|allium|blue_orchid|lily_of_the_valley|wither_rose)$/.test(id) ||
      /^minecraft:(?:short_grass|tall_grass|grass|fern|large_fern|.*flower.*|.*vine.*|moss_carpet|lily_pad|.*kelp.*|.*seagrass.*|bamboo|sugar_cane|cactus|deadbush|.*azalea.*|.*petals.*|leaf_litter|.*dripleaf.*|hanging_roots|spore_blossom|pitcher_plant)$/.test(id)) return 'vegetation';
  if (/^minecraft:(?:stone|dirt|coarse_dirt|rooted_dirt|podzol|mycelium|sand|red_sand|gravel|clay|mud|moss_block|deepslate|granite|diorite|andesite|tuff|calcite|dripstone_block|bedrock|.*terracotta|.*_ore)$/.test(id)) return 'terrain_material_candidate';
  return 'obstruction_unclassified';
}
export function isSupport(kind) {
  return !['water', 'vegetation', 'thin_snow_cover', 'air'].includes(kind);
}
export function interpretColumn(cells) {
  let top=null, ground=null, waterTop=null, waterBottom=null, closed=false, waterKnown=true;
  const discarded=[], cover=[], waterloggedCells=[], waterloggingErrors=[];
  for (const cell of cells) {
    const {y,block}=cell;
    if (['minecraft:air','minecraft:cave_air','minecraft:void_air'].includes(block)) {
      if (waterTop!==null) closed=true;
      continue;
    }
    const kind=classifySurface(block);
    if (!top) top={y,block};
    // Getter failure/missing is an explicit unknown, never inferred from capacity.
    if (kind!=='water' && typeof cell.waterlogged!=='boolean') {
      waterKnown=false;waterloggingErrors.push({y,block,error:cell.waterloggingError || 'isWaterlogged unavailable'});
    }
    if (cell.waterlogged===true) waterloggedCells.push({y,block});
    const fluid = kind==='water' || (kind==='vegetation' && cell.waterlogged===true);
    if (fluid) {
      if (waterTop===null && !closed) waterTop=waterBottom=y;
      else if (!closed && y===waterBottom-1) waterBottom=y;
      else closed=true;
    } else if (waterTop!==null) closed=true;
    if (kind==='vegetation' || kind==='thin_snow_cover') {
      discarded.push({y,block});
      if(kind==='thin_snow_cover') cover.push({y,block,kind});
      continue;
    }
    if (kind==='water') continue;
    ground={y,block,classification:kind,provenance:'unverified'};
    if(kind==='snow_cover' || kind==='frozen_cover') cover.push({y,block,kind});
    break; // Do not discover buried/disconnected water through solid cover.
  }
  if(!ground) throw new Error('ground not found');
  const waterDepth=waterTop===null?0:waterTop-waterBottom+1;
  return {policy:COLUMN_POLICY,top,ground,groundStatus:'observed_support_structure_provenance_unverified',
    substrateStatus:cover.some(c=>c.kind!=='thin_snow_cover')?'hidden_by_cover':'observed_material_provenance_unverified',
    cover,discarded,waterloggedCells,waterloggingErrors,waterTop,waterBottom,waterDepth,waterKnown,
    waterStatus:waterKnown?'observed_open_water_cells':'unknown_overlay_water',
    waterDepthStatus:waterKnown?'contiguous_observed_block_cells':'incomplete_overlay_observation',
    waterSurface:{blockY:waterTop,permutationStates:cells.find(c=>c.y===waterTop)?.states||null,continuousHeight:null,status:waterTop===null?'no_observed_open_water':'block_cell_only_fractional_fluid_height_unverified'},
    waterPresenceStatus:waterKnown?'observed_to_support':'incomplete_overlay_observation',
    waterPresent:waterDepth>0 || waterloggedCells.length>0};
}

export const SURFACE_BIOME_POLICY='one_cell_above_observed_exposed_support_or_water_including_snow_cover';
export const SURFACE_CANOPY_RULE='ignore_filtered_vegetation';
export function surfaceBiomeQuery(result) {
  const levels=[result.ground?.y,result.waterTop,...(result.cover||[]).map(c=>c.y)].filter(Number.isInteger);
  const y=levels.length?Math.max(...levels)+1:null;
  return {y,policy:SURFACE_BIOME_POLICY,canopyRule:SURFACE_CANOPY_RULE,
    status:result.waterKnown!==true || y===null?'UNKNOWN_SURFACE':y>319 || y< -64?'OUT_OF_RANGE':'READY'};
}
export function observeSurfaceBiome(result,x,z,getBiome) {
  const query=surfaceBiomeQuery(result);
  const observation={x,z,y:query.y,name:null,status:query.status,source:'official BDS 1.26.52.3 Script API 2.10.0 Dimension.getBiome',
    queryPolicy:query.policy,canopyRule:query.canopyRule,error:null};
  if(query.status!=='READY') return observation;
  try {
    const name=getBiome({x,y:query.y,z}).id;
    if(typeof name!=='string' || !name.trim()) {observation.status='INVALID_NAME';return observation;}
    observation.name=name;observation.status='OBSERVED';
  } catch(error) {observation.status='QUERY_FAILED';observation.error=String(error);}
  return observation;
}

export function observeBiomeRegistry(server) {
  const result={status:'UNSUPPORTED',names:[],source:'official BDS 1.26.52.3 Script API 2.10.0 BiomeTypes.getAll',error:null};
  if(typeof server?.BiomeTypes?.getAll!=='function') return result;
  try {
    const types=server.BiomeTypes.getAll();
    if(!Array.isArray(types) || types.some(type=>typeof type.id!=='string' || !type.id.trim())) {
      result.status='INVALID_NAMES';return result;
    }
    result.names=[...new Set(types.map(type=>type.id))].sort();result.status='OBSERVED';
  } catch(error){result.status='QUERY_FAILED';result.error=String(error);}
  return result;
}
