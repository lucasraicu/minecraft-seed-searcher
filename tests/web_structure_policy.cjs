// Exercise actual sidebar handlers and App launch validation without a backend.
const assert = require('node:assert/strict');
const test = require('node:test');
const { load, root, hooks } = require('./web_test_loader.cjs');
const { SEARCH_PROFILES } = load(root + '/web-ui/src/constants/baselinePolicy.ts');
const { INITIAL_CONFIG } = load(root + '/web-ui/src/mockData.ts');
const { FilterSidebar } = load(root + '/web-ui/src/components/FilterSidebar.tsx');
const { buildSweepRequest } = load(root + '/web-ui/src/utils/sweep.ts');
const validate = config => buildSweepRequest(config).counts;

function nodes(node) {
  if (node == null) return [];
  if (Array.isArray(node)) return node.flatMap(nodes);
  if (typeof node !== 'object') return [];
  return [node, ...nodes(node.props?.children)];
}
function sidebar(config, tab = 'targets', running = false) {
  hooks.state = value => value === 'targets' ? tab : value;
  let changed;
  const tree = FilterSidebar({ config, onChangeConfig: value => changed = value,
    logs: [], onResumeSweep: () => {}, sweepRunning: running });
  hooks.state = value => value;
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
    assert.equal(JSON.stringify(validate(config)), JSON.stringify(policy.counts));
    const increase = nodes(row).find(node => node.type === 'button' && node.props.title === 'Increase target count');
    assert.equal(increase.props.disabled, !policy.editableCounts.includes('desert_pyramid'));
    increase.props.onClick();
    if (policy.editableCounts.includes('desert_pyramid')) assert.equal(validate(view.changed()).desert_pyramid, policy.counts.desert_pyramid + 1);
    else assert.equal(view.changed(), undefined);
    view.all.find(node => node.type === 'button' && node.props.children === 'Reset').props.onClick();
    assert.ok(!('pyramid' in view.changed().structureFloorCounts));
    assert.equal(JSON.stringify(validate(view.changed())), JSON.stringify(SEARCH_PROFILES[view.changed().profile].counts));
    view.all.find(node => node.type === 'select' && node.props.value === profile)
      .props.onChange({ target: { value: 'dynamic1664' } });
    assert.ok(!view.changed().requiredStructures.includes('pyramid'));
    assert.equal(JSON.stringify(validate(view.changed())), JSON.stringify(SEARCH_PROFILES[view.changed().profile].counts));
  }
});


const { CandidateFeed } = load(root + '/web-ui/src/components/CandidateFeed.tsx');
const { SeedDetailModal } = load(root + '/web-ui/src/components/SeedDetailModal.tsx');
const noop = () => {};
function text(node) {
  if (node == null || typeof node === 'boolean') return '';
  if (Array.isArray(node)) return node.map(text).join(' ');
  if (typeof node === 'object') return text(node.props?.children);
  return String(node);
}

test('candidate page controls can reach results beyond the former pool cap', () => {
  let next;
  const tree = CandidateFeed({ candidates: [], selectedCandidate: null,
    onSelectCandidate: noop, onInspectCandidate: noop, onCopyNotice: noop,
    pagination: { offset: 5000, total: 5101, limit: 100, onChangeOffset: value => { next = value; } } });
  assert.match(text(tree), /5001–5100 of 5,101/);
  const button = nodes(tree).find(node => node.props?.['aria-label'] === 'Next candidate page');
  assert.equal(button.props.disabled, false);
  button.props.onClick();
  assert.equal(next, 5100);
});

test('negative eligible scores are visible before the user applies a score filter', () => {
  const tree = CandidateFeed({ candidates: [{ id: 'a', seed: '1', score: -10, structures: [] }],
    selectedCandidate: null, onSelectCandidate: noop, onInspectCandidate: noop, onCopyNotice: noop });
  assert.ok(nodes(tree).some(node => node.key === 'a'));
});

test('player detail shows predictive suggestion separately from unverified inspections', () => {
  const candidate = { id: 'a', seed: '1', score: 100, structures: [], evaluationCenter: [0, 0],
    suggestedSpawn: { status: 'PREDICTED_SCENIC_SUGGESTION', coordinates: [64, 63, 0], biome: 'plains', distance: 64 },
    playerInspections: { end_access: { status: 'UNVERIFIED', reason: 'Portal room not inspected', source: null } } };
  const tree = SeedDetailModal({ candidate, onClose: noop, onCopyNotice: noop });
  assert.match(text(tree), /Suggested community spawn/);
  assert.match(text(tree), /Actual ground height and safety remain unverified/);
  assert.match(text(tree), /Portal room not inspected/);
});


test('every editable run setting is included in the shared preview/launch request', () => {
  const changes = { 'Seed count': ['sweepSeedCount', '1234', 'count', 1234],
    'Starting seed index': ['startIndex', '18446744073709550000', 'startIndex', '18446744073709550000'],
    'Deficit budget': ['maxMisses', '2', 'maxMisses', 2],
    'Native threads': ['openmpThreads', '7', 'threads', 7],
    'Native batch size': ['batchSize', '128', 'batchSize', 128] };
  for (const [label, [state, value, requestKey, expected]] of Object.entries(changes)) {
    const view = sidebar({ ...INITIAL_CONFIG, sweepSeedCount: 10 }, 'engine');
    const control = view.all.find(node => node.props?.['aria-label'] === label);
    control.props.onChange({ target: { value } });
    assert.equal(view.changed()[state], expected);
    assert.equal(buildSweepRequest(view.changed())[requestKey], expected);
  }
});

test('fixed policy controls cannot drift and running settings are locked', () => {
  const view = sidebar(INITIAL_CONFIG);
  assert.ok(!view.all.some(node => node.props?.type === 'checkbox'));
  const stronghold = view.all.find(node => node.key === 'stronghold');
  for (const button of nodes(stronghold).filter(node => node.type === 'button')) assert.equal(button.props.disabled, true);
  const floor = { ...INITIAL_CONFIG, structureFloorCounts: { ...INITIAL_CONFIG.structureFloorCounts, village: 8 } };
  const village = sidebar(floor).all.find(node => node.key === 'village');
  assert.equal(nodes(village).find(node => node.props?.title === 'Decrease target count').props.disabled, true);
  assert.ok(sidebar(INITIAL_CONFIG, 'engine', true).all.some(node => node.type === 'fieldset' && node.props.disabled));
});


test('command card includes the resolved target policy and last executed command', () => {
  const receipt = { kind: 'preview', shellCommand: 'cd /repo && python scan --config policy.yaml',
    cwd: '/repo', policyYaml: 'minimum_counts: village: 10',
    controls: { count: 123, start_index: '9007199254741001', threads: 7, batch_size: 128, max_misses: 2 } };
  const tree = FilterSidebar({ config: INITIAL_CONFIG, onChangeConfig: noop, logs: [],
    onResumeSweep: noop, sweepRunning: false, preview: receipt, lastLaunch: { ...receipt, kind: 'scan' } });
  assert.match(text(tree), /minimum_counts: village: 10/);
  assert.match(text(tree), /Last executed command/);
  assert.match(text(tree), /9007199254741001/);
  assert.match(text(tree), /Copy runnable command/);
});

test('live biome toggles reach the request without changing run controls', () => {
  const config = { ...INITIAL_CONFIG, selectedBiomes: [...SEARCH_PROFILES.dynamic1664.requiredBiomes] };
  const view = sidebar(config);
  view.all.find(n => n.type === 'button' && n.props['aria-label'] === 'Require Deep Dark').props.onClick();
  const changed = view.changed();
  assert.ok(!changed.selectedBiomes.includes('deep_dark'));
  assert.deepEqual([...buildSweepRequest(changed).biomes], [...changed.selectedBiomes]);
  assert.equal(changed.openmpThreads, config.openmpThreads);
  assert.equal(changed.batchSize, config.batchSize);
  assert.ok(sidebar(config, 'targets', true).all.find(n => n.props?.['aria-label'] === 'Require Deep Dark').props.disabled);
  assert.deepEqual([...buildSweepRequest({ ...config, selectedBiomes: [] }).biomes], []);
  assert.throws(() => buildSweepRequest({ ...config, selectedBiomes: ['unsupported'] }), /supported biome/);
});

test('dynamic2048 profile supports live biome toggling and valid sweep requests', () => {
  assert.ok(SEARCH_PROFILES.dynamic2048);
  assert.equal(SEARCH_PROFILES.dynamic2048.revision, 'dynamic-envelope-2048-v3');
  const config = { ...INITIAL_CONFIG, profile: 'dynamic2048',
    structureFloorCounts: { ...SEARCH_PROFILES.dynamic2048.counts },
    requiredStructures: Object.keys(SEARCH_PROFILES.dynamic2048.counts),
    selectedBiomes: [...SEARCH_PROFILES.dynamic2048.requiredBiomes] };
  const view = sidebar(config);
  const deepDarkBtn = view.all.find(n => n.type === 'button' && n.props['aria-label'] === 'Require Deep Dark');
  assert.equal(deepDarkBtn.props.disabled, false);
  deepDarkBtn.props.onClick();
  const changed = view.changed();
  assert.ok(!changed.selectedBiomes.includes('deep_dark'));
  assert.deepEqual([...buildSweepRequest(changed).biomes], [...changed.selectedBiomes]);
});

test('compareCandidateRank prioritizes score for dynamic-envelope-2048-v3', () => {
  const { compareCandidateRank } = load(root + '/web-ui/src/utils/ranking.ts');
  const a = { id: 'a', seed: '1', score: 850, screeningRevision: 'dynamic-envelope-2048-v3', rankingTier: 1, unmetRequirements: 0 };
  const b = { id: 'b', seed: '2', score: 920, screeningRevision: 'dynamic-envelope-2048-v3', rankingTier: 1, unmetRequirements: 0 };
  assert.ok(compareCandidateRank(a, b) > 0); // b ranks higher than a
  assert.ok(compareCandidateRank(b, a) < 0);
});

test('SeedDetailModal renders dynamic-v3 1,250 Pts Max breakdown, nether core badge, and hides deficits when zero', () => {
  const candZeroDeficit = {
    id: 'cand1',
    seed: '12345',
    score: 950,
    bonusTotal: 950,
    deficitPenalty: 0,
    unmetRequirements: 0,
    evaluationCenter: [64, 64],
    structures: [
      { type: 'fortress', x: 8, z: 8 },
      { type: 'bastion', x: 10, z: 10 },
    ],
    scoreComponents: {
      core_surplus: 340,
      optional_bonus: 80,
      luxury_biomes: 120,
      hub_bonus: 45,
      nether_core_bonus: 20,
      scenic_bonus: 25,
      village_spread_bonus: 25,
      treasure_bastion_bonus: 20,
    },
    treasureBastion: 1,
  };
  const modalText = text(SeedDetailModal({ candidate: candZeroDeficit, onClose: noop, onCopyNotice: noop }));
  assert.match(modalText, /Player Quality Score Breakdown \(dynamic-v3: 1,250 Pts Max\)/);
  assert.match(modalText, /Core Surplus/);
  assert.match(modalText, /\+650 max/);
  assert.match(modalText, /Optional Structures/);
  assert.match(modalText, /\+200 max/);
  assert.match(modalText, /Luxury Biomes/);
  assert.match(modalText, /\+265 max/);
  assert.match(modalText, /Spatial & Nether/);
  assert.match(modalText, /\+135 max/);
  assert.match(modalText, /Nether Portal Core/);
  assert.match(modalText, /Fortress ≤256m/);
  assert.match(modalText, /Bastion ≤256m/);
  assert.match(modalText, /Treasure Bastion/);
  assert.match(modalText, /\+20 max \(v3\)/);
  // Zero deficits should hide the deficit penalty card
  assert.doesNotMatch(modalText, /Deficits Penalty/);

  // Candidate with deficit penalty displays the deficit card
  const candWithDeficit = {
    ...candZeroDeficit,
    deficitPenalty: 10,
    unmetRequirements: 1,
    scoreComponents: { ...candZeroDeficit.scoreComponents, deficit_penalty: 10 },
  };
  const modalWithDeficitText = text(SeedDetailModal({ candidate: candWithDeficit, onClose: noop, onCopyNotice: noop }));
  assert.match(modalWithDeficitText, /Deficits Penalty/);
  assert.match(modalWithDeficitText, /missing requirement/);
});

