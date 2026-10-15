// Exercise actual sidebar handlers and App launch validation without a backend.
const assert = require('node:assert/strict');
const test = require('node:test');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const root = path.resolve(__dirname, '..');
const ts = require(root + '/web-ui/node_modules/typescript');
const React = require(root + '/web-ui/node_modules/react');
const cache = new Map();

function load(file) {
  if (cache.has(file)) return cache.get(file).exports;
  if (file.endsWith('.json')) return JSON.parse(fs.readFileSync(file, 'utf8'));
  const module = { exports: {} };
  cache.set(file, module);
  function requireLocal(name) {
    if (name === 'react') return { ...React,
      useState: value => [typeof value === 'function' ? value() : value, () => {}],
      useMemo: compute => compute() };
    if (!name.startsWith('.')) return require(name);
    const target = path.resolve(path.dirname(file), name);
    const resolved = ['', '.ts', '.tsx', '.json'].map(ext => target + ext)
      .find(candidate => fs.existsSync(candidate) && fs.statSync(candidate).isFile());
    assert.ok(resolved, `Unresolved import ${name}`);
    return load(resolved);
  }
  const js = ts.transpileModule(fs.readFileSync(file, 'utf8'), { compilerOptions: {
    module: ts.ModuleKind.CommonJS, jsx: ts.JsxEmit.React, esModuleInterop: true } }).outputText;
  vm.runInNewContext(js, { module, exports: module.exports, require: requireLocal });
  return module.exports;
}

const { SEARCH_PROFILES, normalizeStructureCounts } = load(root + '/web-ui/src/constants/baselinePolicy.ts');
const { INITIAL_CONFIG } = load(root + '/web-ui/src/mockData.ts');
const { FilterSidebar } = load(root + '/web-ui/src/components/FilterSidebar.tsx');
const appSource = fs.readFileSync(root + '/web-ui/src/App.tsx', 'utf8');
const ast = ts.createSourceFile('App.tsx', appSource, ts.ScriptTarget.Latest, true, ts.ScriptKind.TSX);
let validationLoop;
function visit(node) {
  if (ts.isForOfStatement(node) && node.expression.getText(ast) === 'Object.entries(policy.counts)')
    validationLoop = node.getText(ast);
  ts.forEachChild(node, visit);
}
visit(ast);
assert.ok(validationLoop, 'App launch validation loop missing');
const launch = new Function('config', 'policy', 'normalizeStructureCounts',
  'const floorCounts=normalizeStructureCounts(config.structureFloorCounts);const counts={};' + validationLoop + ';return counts;');
const validate = config => launch(config, SEARCH_PROFILES[config.profile], normalizeStructureCounts);

function nodes(node) {
  if (node == null) return [];
  if (Array.isArray(node)) return node.flatMap(nodes);
  if (typeof node !== 'object') return [];
  return [node, ...nodes(node.props?.children)];
}
function sidebar(config) {
  let changed;
  const tree = FilterSidebar({ config, onChangeConfig: value => changed = value,
    logs: [], onResumeSweep: () => {}, sweepRunning: false });
  return { all: nodes(tree), changed: () => changed };
}
function pyramidRow(view) { return view.all.find(node => node.key === 'desert_pyramid'); }
function displayedCount(row) {
  return nodes(row).find(node => node.type === 'span' && typeof node.props.children === 'number').props.children;
}

test('legacy alias displays, estimates and edits the same count that App launches', () => {
  const config = { ...INITIAL_CONFIG,
    requiredStructures: INITIAL_CONFIG.requiredStructures.map(key => key === 'desert_pyramid' ? 'pyramid' : key),
    structureFloorCounts: { ...INITIAL_CONFIG.structureFloorCounts, pyramid: 4 } };
  delete config.structureFloorCounts.desert_pyramid;
  const view = sidebar(config), row = pyramidRow(view);
  assert.equal(displayedCount(row), 4);
  assert.equal(validate(config).desert_pyramid, 4);
  assert.ok(nodes(row).some(node => node.props?.title?.startsWith('Uncalibrated modeled marginal:')));
  nodes(row).find(node => node.type === 'button' && node.props.title === 'Increase target count').props.onClick();
  const changed = view.changed();
  assert.equal(changed.structureFloorCounts.desert_pyramid, 5);
  assert.equal(validate(changed).desert_pyramid, 5);
  assert.ok(!('pyramid' in changed.structureFloorCounts));
  assert.ok(!changed.requiredStructures.includes('pyramid'));
  assert.equal(changed.requiredStructures.filter(key => key === 'desert_pyramid').length, 1);
  assert.equal(config.structureFloorCounts.pyramid, 4); // Reading never mutates historical input.
});

test('canonical value takes precedence over a stale alias, including zero', () => {
  for (const count of [0, 3, 5]) {
    const config = { ...INITIAL_CONFIG, structureFloorCounts: {
      ...INITIAL_CONFIG.structureFloorCounts, desert_pyramid: count, pyramid: 9 } };
    assert.equal(displayedCount(pyramidRow(sidebar(config))), count);
    if (count === 0) assert.throws(() => validate(config), /requires at least 2/);
    else assert.equal(validate(config).desert_pyramid ?? 3, count);
  }
});

test('all profile defaults, steppers, reset and profile changes stay canonical', () => {
  assert.ok(!('pyramid' in INITIAL_CONFIG.structureFloorCounts));
  for (const [profile, policy] of Object.entries(SEARCH_PROFILES)) {
    const config = { ...INITIAL_CONFIG, profile, structureFloorCounts: { ...policy.counts },
      requiredStructures: Object.keys(policy.counts) };
    const view = sidebar(config), row = pyramidRow(view);
    assert.equal(displayedCount(row), policy.counts.desert_pyramid);
    assert.equal(Object.keys(validate(config)).length, 0);
    nodes(row).find(node => node.type === 'button' && node.props.title === 'Increase target count').props.onClick();
    if (profile === 'dynamic1664') assert.equal(validate(view.changed()).desert_pyramid, 4);
    else assert.throws(() => validate(view.changed()), /fixes this target/);
    view.all.find(node => node.type === 'button' && node.props.children === 'Reset').props.onClick();
    assert.ok(!('pyramid' in view.changed().structureFloorCounts));
    assert.equal(Object.keys(validate(view.changed())).length, 0);
    view.all.find(node => node.type === 'select' && node.props.value === profile)
      .props.onChange({ target: { value: 'dynamic1664' } });
    assert.ok(!view.changed().requiredStructures.includes('pyramid'));
    assert.equal(Object.keys(validate(view.changed())).length, 0);
  }
});
