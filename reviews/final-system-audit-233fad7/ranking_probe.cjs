// Run from web-ui: node ../reviews/final-system-audit-233fad7/ranking_probe.cjs
const fs = require('fs');
const path = require('path');
const vm = require('vm');
const ts = require(path.resolve('node_modules/typescript'));
const source = fs.readFileSync('src/utils/ranking.ts', 'utf8');
const output = ts.transpileModule(source, {
  compilerOptions: { module: ts.ModuleKind.CommonJS },
}).outputText;
const context = { exports: {} };
vm.runInNewContext(output, context);
const base = {
  screeningRevision: 'dynamic-envelope-1664-v2', rankingTier: 0,
  score: 100, unmetRequirements: 0, radialKey: 10,
  originDistanceSquared: 0, evaluationCenter: [0, 0],
};
const a = { ...base, id: '-1:0:0' }, b = { ...base, id: '-10:0:0' };
const result = {
  a: a.id, b: b.id,
  uiComparator: Math.sign(context.exports.compareCandidateRank(a, b)),
  binaryComparator: a.id < b.id ? -1 : a.id > b.id ? 1 : 0,
  scope: 'Synthetic equal score and equal tie keys; actual production comparator.',
};
fs.writeFileSync(path.join(__dirname, 'ranking-probe.json'), JSON.stringify(result, null, 2) + '\n');
console.log(result);
