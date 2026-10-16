const {load,root}=require('../../tests/web_test_loader.cjs');
const {compareCandidateRank}=load(root+'/web-ui/src/utils/ranking.ts');
const a={id:'a',screeningRevision:'dynamic-envelope-2048-v3',rankingTier:0,score:100,unmetRequirements:0,radialKey:900,originDistanceSquared:0,evaluationCenter:[0,0]};
const b={...a,id:'b',radialKey:100};
console.log(JSON.stringify({v3_comparison:compareCandidateRank(a,b),expected:'positive: b wins smaller radialKey',v2_comparison:compareCandidateRank({...a,screeningRevision:'dynamic-envelope-1664-v2'},{...b,screeningRevision:'dynamic-envelope-1664-v2'})},null,2));
