// Explicit controlled mutations in an air-only disposable-world volume.
// API operations are injected so the mutation/rollback path is testable without BDS.
export const FIXTURE_POLICY='disposable-column-fixtures-v1';
function snapshot(block) {
  return {block:block.typeId,states:block.permutation.getAllStates(),waterlogged:block.isWaterlogged};
}
function sameStates(a,b) {
  return a!==null && b!==null && JSON.stringify(Object.entries(a).sort())===JSON.stringify(Object.entries(b).sort());
}
function same(a,b) {
  return a.block===b.block && a.waterlogged===b.waterlogged && sameStates(a.states,b.states);
}
export function fixturePlan(q) {
  if(q.disposableWorld!==true || !Number.isInteger(q.x0) || !Number.isInteger(q.z0) || q.side!==32 || q.spacing!==1)
    throw new Error('Fixtures require explicit disposableWorld=true and bounded 32x32 spacing1 request');
  const labels=['primary_water','flowing_water','waterlogged_plant','waterlogged_solid','thin_snow','solid_snow','powder_snow','ice_over_water','elevated_lake'];
  const cases=[],mutations=[];
  labels.forEach((label,i)=>{
    const x=q.x0+3+(i%3)*8,z=q.z0+3+Math.floor(i/3)*8,base=label==='elevated_lake'?304:300;
    cases.push({label,x,z,base});
    // Closed lateral walls and floor; column center remains open to the sky.
    for(let y=base;y<=base+4;y++)for(let dx=-1;dx<=1;dx++)for(let dz=-1;dz<=1;dz++) {
      if(y===base || dx!==0 || dz!==0) mutations.push({x:x+dx,y,z:z+dz,block:y===base?'minecraft:stone':'minecraft:glass',states:{}});
    }
    const put=(dy,block,states={},waterlogged=false)=>mutations.push({x,y:base+dy,z,block:'minecraft:'+block,states,waterlogged});
    if(label==='primary_water' || label==='elevated_lake') {put(1,'water',{liquid_depth:0});put(2,'water',{liquid_depth:0});}
    if(label==='flowing_water') put(1,'flowing_water',{liquid_depth:3});
    if(label==='waterlogged_plant') {put(1,'seagrass',{},true);put(2,'water',{liquid_depth:0});}
    if(label==='waterlogged_solid') put(1,'oak_slab',{},true);
    if(label==='thin_snow') put(1,'snow_layer');
    if(label==='solid_snow') put(1,'snow');
    if(label==='powder_snow') put(1,'powder_snow');
    if(label==='ice_over_water') {put(1,'water',{liquid_depth:0});put(2,'ice');}
  });
  return {cases,mutations};
}
export function restoreFixtureJournal(q,journal,getBlock,resolve) {
  const plan=fixturePlan(q),allowed=new Set(plan.mutations.map(p=>`${p.x},${p.y},${p.z}`));
  if(journal.policy!==FIXTURE_POLICY || journal.x0!==q.x0 || journal.z0!==q.z0 || !Array.isArray(journal.mutations) || journal.mutations.length>plan.mutations.length)
    throw new Error('Invalid fixture restoration journal');
  const seen=new Set();
  // Validate every target before changing any cell, including supplied journals.
  for(const p of journal.mutations) {
    const key=`${p.x},${p.y},${p.z}`;
    if(!allowed.has(key) || seen.has(key) || p.original?.block!=='minecraft:air' || p.original.waterlogged!==false || Object.keys(p.original.states||{}).length!==0)
      throw new Error('Restoration journal must contain unique planned original air cells');
    seen.add(key);
  }
  const results=[],errors=[];
  for(const p of [...journal.mutations].reverse()) {
    let before=null,after=null,error=null;
    try {
      const block=getBlock(p);if(!block) throw new Error('Unloaded restoration cell');
      before=snapshot(block);
      // Pinned runtime leaves primary water when an overlay-bearing block is
      // replaced by air. Remove its overlay BEFORE restoring original air.
      if(before.waterlogged===true) block.setWaterlogged(false);
      block.setPermutation(resolve(p.original.block,p.original.states));
      if(block.isWaterlogged===true) block.setWaterlogged(false);
      after=snapshot(block);
      if(!same(after,p.original)) throw new Error('Original permutation/overlay restoration mismatch');
    } catch(e) {error=String(e);errors.push({x:p.x,y:p.y,z:p.z,error});}
    results.push({x:p.x,y:p.y,z:p.z,original:p.original,before,after,error,restored:!error});
  }
  return {policy:FIXTURE_POLICY,evidenceRole:'controlled_fixture',status:errors.length?'FAILED':'RESTORED_SUBSET',
    restoredCells:results.filter(p=>p.restored).length,expectedCells:journal.mutations.length,errors,results};
}
export function createFixtures(q,getBlock,resolve) {
  const plan=fixturePlan(q);
  const journal={policy:FIXTURE_POLICY,evidenceRole:'controlled_fixture',x0:q.x0,z0:q.z0,cases:plan.cases,expectedCells:plan.mutations.length,mutations:[]};
  const permutations=[];let phase='PREFLIGHT',requestedPermutation=null;
  try {
    // Resolve all IDs/states and verify all originals BEFORE any mutation.
    for(const p of plan.mutations) {
      requestedPermutation={block:p.block,states:p.states};
      const block=getBlock(p);if(!block) throw new Error('Unloaded fixture preflight cell');
      const original=snapshot(block);
      if(original.block!=='minecraft:air' || original.waterlogged!==false || Object.keys(original.states).length!==0)
        throw new Error('Fixture preflight requires known dry original air, refusing natural terrain mutation');
      journal.mutations.push({...p,original,observed:null,applied:false});
      const permutation=resolve(p.block,p.states);
      const resolvedBlock=permutation?.type?.id;
      if(typeof resolvedBlock!=='string' || !resolvedBlock)throw new Error('Resolved fixture permutation has no block identity');
      journal.mutations.at(-1).resolvedBlock=resolvedBlock;
      journal.mutations.at(-1).resolvedStates=permutation.getAllStates();
      permutations.push(permutation);
    }
    phase='MUTATION';
    for(let i=0;i<journal.mutations.length;i++) {
      const p=journal.mutations[i];
      requestedPermutation={block:p.block,resolvedBlock:p.resolvedBlock,states:p.states,index:i,x:p.x,y:p.y,z:p.z};
      const block=getBlock(p);
      // Journal is complete before the first write, so partial setter failures roll back.
      block.setPermutation(permutations[i]);
      if(p.waterlogged===true) block.setWaterlogged(true);
      p.observed=snapshot(block);p.applied=true;
      // Pinned runtime fixture d1d20a proved this one setter normalization.
      // Require exact requested/resolved/observed states; no generic ID aliasing.
      const normalizedFlow=p.block==='minecraft:flowing_water' && p.resolvedBlock==='minecraft:flowing_water' &&
        p.observed.block==='minecraft:water' && sameStates(p.states,p.resolvedStates) && sameStates(p.resolvedStates,p.observed.states);
      p.normalization=normalizedFlow?'bedrock_flowing_water_setter_to_water':null;
      if((p.observed.block!==p.resolvedBlock && !normalizedFlow) || (p.waterlogged===true && p.observed.waterlogged!==true) ||
          Object.entries(p.states).some(([key,value])=>p.observed.states[key]!==value))
        throw new Error('Requested fixture permutation/overlay was not observed');
    }
    return {policy:FIXTURE_POLICY,evidenceRole:'controlled_fixture',status:'CREATED',journal,cases:plan.cases,mutatedCells:journal.mutations.length};
  } catch(error) {
    let restoration={status:'NOT_NEEDED',restoredCells:0,expectedCells:0,errors:[],results:[]};
    if(phase==='MUTATION') {
      try {restoration=restoreFixtureJournal(q,journal,getBlock,resolve);}
      catch(restoreError) {restoration={status:'FAILED',restoredCells:0,expectedCells:journal.mutations.length,
        errors:[{error:String(restoreError)}],results:[]};}
    }
    error.fixtureReport={policy:FIXTURE_POLICY,evidenceRole:'controlled_fixture',status:'FAILED',error:String(error),phase,
      requestedPermutation,journal,restoration};
    throw error;
  }
}

export function observeResolvedPermutations(permutations,resolve) {
  if(!Array.isArray(permutations) || permutations.length<1 || permutations.length>8)
    throw new Error('Resolve probe requires 1..8 requested permutations');
  for(const entry of permutations) {
    if(typeof entry.block!=='string' || !/^[a-z0-9_:]+$/.test(entry.block) || entry.block.length>128 ||
        !entry.states || typeof entry.states!=='object' || Array.isArray(entry.states) || Object.keys(entry.states).length>32 ||
        Object.values(entry.states).some(value=>!['string','boolean','number'].includes(typeof value) || typeof value==='number' && !Number.isFinite(value)))
      throw new Error('Invalid resolve probe block/states');
  }
  return permutations.map(requested=>{
    const observation={requested,resolved:null,status:'FAILED',error:null};
    try {
      const permutation=resolve(requested.block,requested.states);
      const block=permutation.type.id,states=permutation.getAllStates();
      if(typeof block!=='string' || !block || !states || typeof states!=='object') throw new Error('Resolved identity/states unavailable');
      observation.resolved={block,states};observation.status='RESOLVED';
    }catch(error){observation.error=String(error);}
    return observation;
  });
}
