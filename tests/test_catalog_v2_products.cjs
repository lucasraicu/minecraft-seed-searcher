/**
 * Test suite for Catalog V2 Product UI:
 * - ProductResultsV2 contract validation and epoch/snapshot/product guards
 * - Signed64 seed strings, horizontal geometry, witness Y handling, unknown metrics
 * - Realm 2048 qualification (1250: 845/265/140) and 4096/8192 separate scope notices
 * - Current 16 presets / 17 records and historical gated-product compatibility
 * - Actual ReactDOM Server rendering of all states (loading, error, empty, populated, pagination)
 */

const path = require('node:path');
const fs = require('node:fs');
const { spawnSync } = require('node:child_process');
const assert = require('node:assert/strict');

const webUiDir = path.resolve(__dirname, '../web-ui');
const nodeModulesDir = path.resolve(webUiDir, 'node_modules');
module.paths.unshift(nodeModulesDir);

const ts = require(path.resolve(nodeModulesDir, 'typescript'));
const React = require(path.resolve(nodeModulesDir, 'react'));
const ReactDOMServer = require(path.resolve(nodeModulesDir, 'react-dom/server'));

function tsHook(module, filename) {
  const code = fs.readFileSync(filename, 'utf8');
  const transpiled = ts.transpileModule(code, {
    compilerOptions: {
      module: ts.ModuleKind.CommonJS,
      target: ts.ScriptTarget.ES2022,
      jsx: ts.JsxEmit.React,
      esModuleInterop: true,
    },
    fileName: filename,
  });
  const wrapped = `const React = require(${JSON.stringify(path.resolve(nodeModulesDir, 'react'))});\n` + transpiled.outputText;
  module._compile(wrapped, filename);
}
require.extensions['.ts'] = tsHook;
require.extensions['.tsx'] = tsHook;

const {
  LaunchProductList,
  validateProductResultsV2,
  formatRankItem,
  renderMetricSummary,
} = require(path.resolve(webUiDir, 'src/catalog/LaunchProductList.tsx'));

const {
  ProductPillar,
  PillarNavigation,
} = require(path.resolve(webUiDir, 'src/catalog/pillars/index.tsx'));

const SNAPSHOT_A = 'a'.repeat(64);
const SNAPSHOT_B = 'b'.repeat(64);

function makeMockEvaluations(count = 20) {
  const results = [];
  for (let i = 0; i < count; i++) {
    const seed = i % 2 === 0
      ? `-${9000000000000000000n + BigInt(i * 12345)}`
      : `${8000000000000000000n + BigInt(i * 67890)}`;
    const hasY = i % 3 === 0;
    results.push({
      product_id: 'preset.hardcore_rush',
      world_id: i.toString(16).padStart(64,'0'),
      seed,
      observation_id: 'e'.repeat(64),
      status: 'match',
      rank: [i + 1, { numerator: i + 1, denominator: 20 }],
      anchor: {
        mode: 'origin',
        coordinate: [i * 100, -i * 100],
        overworld: [i * 100, -i * 100],
        nether: [Math.floor((i * 100) / 8), Math.floor((-i * 100) / 8)],
        nether_reference: 'projected_floor_div_8',
      },
      witnesses: [
        {
          feature: 'structure.village',
          dimension: 'overworld',
          coordinate: [i * 100 + 40, null, -i * 100 + 50],
          distance_squared: 4100,
          provider:'procedural_model_v1',observation_id:'e'.repeat(64),
          witness_id: (i*2).toString(16).padStart(64,'0'),
        },
        {
          feature: 'biome.cherry_grove',
          dimension: 'overworld',
          coordinate: [i * 100 + 60, 63, -i * 100 + 80],
          distance_squared: 10000,
          provider:'procedural_model_v1',observation_id:'e'.repeat(64),
          witness_id: (i*2+1).toString(16).padStart(64,'0'),
        },
      ],
      metric: i === 0 ? {
        score: 1150,
        qualifying_core: 2048,
        nether_core: 1024,
        group_scores: {overworld:820,luxury_biomes:250,nether:80},
        count: 24,
        count_complete: true,
        farthest_witness_d2: 45000,
      } : {
        count: 10 + i,
        farthest_witness_d2: 20000 + i * 1000,
      },
      reason: null,
      scope: {
        dimension: 'overworld',
        radius: 2048,
      },
    });
  }
  return results;
}

function makeMockV2Response(overrides = {}) {
  return {
    ok: true,
    revision: 'catalog-product-results-v2',
    snapshot_id: SNAPSHOT_A,
    product_id: 'preset.hardcore_rush',
    results: makeMockEvaluations(20),
    matched_worlds: 142,
    next_cursor: 'cursor_token_page_2',
    population_worlds: 200,
    scope: { dimension: 'overworld', radius: 2048 },
    policy_revision: 'c'.repeat(64),
    evidence_label: 'predicted_observations_v2',
    ...overrides,
  };
}

function makeMockRegistryV2() {
  const products = [];
  // 16 Presets
  for (let i = 1; i <= 16; i++) {
    products.push({
      id: `preset.preset_${i}`,
      pillar_id: 'presets',
      kind: 'preset',
      label: `Preset ${i} Launch`,
      category: i <= 8 ? 'Survival Challenges' : 'Exploration Presets',
      criteria_summary: `Predicted requirements for preset ${i} within 2048 blocks.`,
      availability_status: 'predicted',
      missing_dependencies: [],
      evidence_needed: [],
    });
  }
  // 17 Launch Records
  for (let i = 1; i <= 17; i++) {
    products.push({
      id: `record.launch_${i}`,
      pillar_id: 'rare',
      kind: 'record',
      label: `Launch Record ${i}`,
      category: i <= 9 ? 'Hall of Terrain Wonders' : 'Hall of Density Records',
      criteria_summary: `Predicted rare feature alignment for record ${i}.`,
      availability_status: 'predicted',
      missing_dependencies: [],
      evidence_needed: [],
    });
  }
  // 5 Deferred Gated Records
  for (let i = 1; i <= 5; i++) {
    products.push({
      id: `record.deferred_${i}`,
      pillar_id: 'rare',
      kind: 'record',
      label: `Deferred Record ${i}`,
      category: 'Deferred Exotic Records',
      criteria_summary: `Advanced terrain/structure confluence for deferred record ${i}.`,
      availability_status: 'gated',
      missing_dependencies: ['terrain_collision_verifier', 'portal_room_carving'],
      evidence_needed: ['bds_portal_generation_check', 'walkability_mesh_validation'],
    });
  }
  // Legacy Research Products
  products.push({
    id: 'research.origin.village.r2000',
    pillar_id: 'rare',
    kind: 'research',
    label: 'Origin Village Density (r2000)',
    category: 'Research Previews',
    criteria_summary: 'Village density in 2000m circle around origin.',
    availability_status: 'research',
    missing_dependencies: [],
    evidence_needed: [],
  });
  // Realm Product
  products.push({
    id: 'realm.standard_2048',
    pillar_id: 'realm',
    kind: 'realm',
    label: 'Realm 2048 Standard Play',
    category: 'Certified Realm Worlds',
    criteria_summary: 'Certified Realm world with 845 OW, 265 luxury, 140 Nether.',
    availability_status: 'predicted',
    missing_dependencies: [],
    evidence_needed: [],
  });
  // Personalized
  products.push({
    id: 'personalized.custom_selection',
    pillar_id: 'personalized',
    kind: 'personalized',
    label: 'Personalized Query Target',
    category: 'Custom Search',
    criteria_summary: 'Interactive user criteria search.',
    availability_status: 'predicted',
    missing_dependencies: [],
    evidence_needed: [],
  });

  return {
    ok: true,
    revision: 'catalog-products-v2',
    products,
    evidence_label: 'predicted_observations_v2',
  };
}

let passedTests = 0, failedTests=0;
function test(name, fn) {
  try {
    fn();
    passedTests++;
    console.log(`PASS: ${name}`);
  } catch (err) {
    console.error(`FAIL: ${name}`);
    console.error(err);
    failedTests++;process.exitCode = 1;
  }
}

// ==========================================
// Suite 1: Contract & Response Validators
// ==========================================

test('validateProductResultsV2 accepts valid 20-row v2 response', () => {
  const data = makeMockV2Response();
  const res = validateProductResultsV2(data, SNAPSHOT_A, 'preset.hardcore_rush');
  assert.equal(res.ok, true);
  assert.equal(res.value.results.length, 20);
  assert.equal(res.value.matched_worlds, 142);
  assert.equal(res.value.population_worlds, 200);
});

test('validateProductResultsV2 rejects mismatched snapshot_id', () => {
  const data = makeMockV2Response();
  const res = validateProductResultsV2(data, SNAPSHOT_B, 'preset.hardcore_rush');
  assert.equal(res.ok, false);
  assert.match(res.error, /Mismatched snapshot_id/);
});

test('validateProductResultsV2 rejects mismatched product_id', () => {
  const data = makeMockV2Response();
  const res = validateProductResultsV2(data, SNAPSHOT_A, 'preset.different_product');
  assert.equal(res.ok, false);
  assert.match(res.error, /Mismatched product_id/);
});

test('validateProductResultsV2 rejects numeric seed (must be signed64 string)', () => {
  const data = makeMockV2Response();
  data.results[0].seed = 1234567890123456; // Numeric value is invalid
  const res = validateProductResultsV2(data, SNAPSHOT_A, 'preset.hardcore_rush');
  assert.equal(res.ok, false);
  assert.match(res.error, /signed64 string/);
});

test('validateProductResultsV2 rejects invalid revision', () => {
  const data = makeMockV2Response({ revision: 'catalog-product-results-v1' });
  const res = validateProductResultsV2(data, SNAPSHOT_A, 'preset.hardcore_rush');
  assert.equal(res.ok, false);
  assert.match(res.error, /Invalid revision/);
});

test('validateProductResultsV2 rejects negative matched_worlds or non-array results', () => {
  assert.equal(validateProductResultsV2(makeMockV2Response({ matched_worlds: -1 })).ok, false);
  assert.equal(validateProductResultsV2(makeMockV2Response({ results: 'not an array' })).ok, false);
});

test('formatRankItem handles numbers, rational fractions and unknowns', () => {
  assert.equal(formatRankItem(1), '1');
  assert.equal(formatRankItem(2.5), '2.50');
  assert.equal(formatRankItem({ numerator: 3, denominator: 4 }), '3/4');
  assert.equal(formatRankItem({ numerator: 140, denominator: 200 }), '140/200');
  assert.equal(formatRankItem(null), 'unknown');
  assert.equal(formatRankItem(undefined), 'unknown');
});

// ==========================================
// Suite 2: PillarNavigation & ProductPillar Rendering
// ==========================================

test('PillarNavigation renders all 4 pillars with correct labels and accessibility', () => {
  const html = ReactDOMServer.renderToStaticMarkup(
    React.createElement(PillarNavigation, {
      value: 'presets',
      onChange: () => {},
    })
  );
  assert.ok(html.includes('Realm/Server Seeds'));
  assert.ok(html.includes('Presets'));
  assert.ok(html.includes('Personalized Selection'));
  assert.ok(html.includes('Rare Seeds'));
  assert.ok(html.includes('aria-current="page"'));
});

test('ProductPillar renders historical registry payloads including gated records', () => {
  const registry = makeMockRegistryV2();
  const presetsCount = registry.products.filter(p => p.pillar_id === 'presets').length;
  const launchRecordsCount = registry.products.filter(p => p.pillar_id === 'rare' && p.availability_status === 'predicted').length;
  const deferredCount = registry.products.filter(p => p.pillar_id === 'rare' && p.availability_status === 'gated').length;

  assert.equal(presetsCount, 16, 'Registry must contain 16 presets');
  assert.equal(launchRecordsCount, 17, 'Registry must contain 17 launch records');
  assert.equal(deferredCount, 5, 'Registry must contain 5 deferred records');

  // Render Presets pillar
  const htmlPresets = ReactDOMServer.renderToStaticMarkup(
    React.createElement(ProductPillar, {
      pillarId: 'presets',
      snapshotId: SNAPSHOT_A,
      initialRegistry: registry,
    })
  );
  assert.ok(htmlPresets.includes('Sixteen fixed play-style presets'));
  assert.ok(htmlPresets.includes('Preset 1 Launch'));
  assert.ok(htmlPresets.includes('Browse launch results'));
  assert.ok(htmlPresets.includes('Launch'));

  // Render Rare pillar
  const htmlRare = ReactDOMServer.renderToStaticMarkup(
    React.createElement(ProductPillar, {
      pillarId: 'rare',
      snapshotId: SNAPSHOT_A,
      initialRegistry: registry,
    })
  );
  assert.ok(htmlRare.includes('Launch Record 1'));
  assert.ok(htmlRare.includes('Deferred Record 1'));
  assert.ok(htmlRare.includes('Browse launch results'));
  assert.ok(htmlRare.includes('Evidence pending · View criteria'));
  assert.ok(htmlRare.includes('Gated'));
  assert.ok(htmlRare.includes('Research'));

  // Render Realm pillar
  const htmlRealm = ReactDOMServer.renderToStaticMarkup(
    React.createElement(ProductPillar, {
      pillarId: 'realm',
      snapshotId: SNAPSHOT_A,
      initialRegistry: registry,
    })
  );
  assert.ok(htmlRealm.includes('Realm/Server Seeds'));
  assert.ok(htmlRealm.includes('845 OW / 265 luxury / 140 Nether'));
  assert.ok(htmlRealm.includes('Separate 2048, 4096 and 8192 Overworld boards'));
});

test('Current backend registry renders seventeen records without terrain-heavy cards', () => {
  const root=path.resolve(__dirname,'..');
  const output=spawnSync(path.join(root,'.venv/bin/python'),['-c',
    'import json; from seed_search.catalog.products import product_registry_v2; print(json.dumps(product_registry_v2()))'],
    {cwd:root,env:{...process.env,PYTHONPATH:path.join(root,'src')},encoding:'utf8',timeout:10000});
  assert.equal(output.status,0,output.stderr || String(output.error || 'registry failed'));
  const registry=JSON.parse(output.stdout);
  const records=registry.products.filter(p=>p.pillar_id==='rare');
  assert.equal(records.length,17);
  const html=ReactDOMServer.renderToStaticMarkup(React.createElement(ProductPillar,
    {pillarId:'rare',snapshotId:SNAPSHOT_A,initialRegistry:registry}));
  for (const label of ['Direct-Drop','Badlands Continental Spine','Mega Cherry Grove',
                       'Intersecting Triple Mineshaft','Endless Deep Dark Void']) {
    assert.ok(!html.includes(label),`Removed product still visible: ${label}`);
  }
  for (const record of records) {
    const label=ReactDOMServer.renderToStaticMarkup(React.createElement(React.Fragment,null,record.label));
    assert.ok(html.includes(label),`Missing card: ${record.label}`);
  }
  assert.ok(html.includes('Seventeen record categories'));
  assert.ok(!html.includes('5 deferred records'));
});

test('Optional product evaluation counts are checked and displayed', () => {
  const response=makeMockV2Response({evaluation_counts:{match:142,no_match:30,pending:28}});
  const product={id:response.product_id,pillar_id:'presets',label:'Counts',criteria_summary:'Declared method'};
  assert.equal(validateProductResultsV2(response,SNAPSHOT_A,response.product_id).ok,true);
  const html=ReactDOMServer.renderToStaticMarkup(React.createElement(LaunchProductList,{product,snapshotId:SNAPSHOT_A,initialData:response}));
  assert.ok(html.includes('28 pending'));
  for(const counts of [{match:0,no_match:0,pending:0},{match:142,no_match:30,pending:-1},{match:142,no_match:30,pending:300}]) {
    assert.equal(validateProductResultsV2({...response,evaluation_counts:counts},SNAPSHOT_A,response.product_id).ok,false);
  }
});

test('Larger Realm boards show their own scope and fixed Nether budget', () => {
  for (const side of [4096, 8192]) {
    const product = {id: `realm.v2.qualified_${side}`, pillar_id: 'realm', label: `Realm ${side}`,
      criteria_summary: 'Frozen calibrated requirements', scope: {border_sides: [side]}};
    const html = ReactDOMServer.renderToStaticMarkup(React.createElement(LaunchProductList,
      {product, snapshotId: SNAPSHOT_A}));
    assert.ok(html.includes(`Realm ${side} Qualification`));
    assert.ok(html.includes(`Overworld scope: ${side} × ${side}`));
    assert.ok(html.includes('Nether scope remains 1024 × 1024'));
    assert.ok(html.includes('845 Overworld, 265 luxury biomes and 140 Nether'));
    assert.ok(!html.includes('remain gated'));
  }
});

test('ProductPillar renders chosen gated product criteria and dependencies', () => {
  const registry = makeMockRegistryV2();
  const html = ReactDOMServer.renderToStaticMarkup(
    React.createElement(ProductPillar, {
      pillarId: 'rare',
      snapshotId: SNAPSHOT_A,
      initialRegistry: registry,
      initialSelected: 'record.deferred_1',
    })
  );
  assert.ok(html.includes('Deferred Record 1 criteria'));
  assert.ok(html.includes('Matching results are unavailable until the required evidence is implemented'));
  assert.ok(html.includes('bds_portal_generation_check'));
  assert.ok(html.includes('Pending: terrain collision verifier, portal room carving'));
});

// ==========================================
// Suite 3: LaunchProductList State Rendering
// ==========================================

test('LaunchProductList renders loading and error states cleanly', () => {
  const product = {
    id: 'preset.hardcore_rush',
    pillar_id: 'presets',
    kind: 'preset',
    label: 'Hardcore Rush',
    category: 'Challenge',
    criteria_summary: 'Summary text',
    availability_status: 'predicted',
    missing_dependencies: [],
    evidence_needed: [],
  };

  const htmlLoading = ReactDOMServer.renderToStaticMarkup(
    React.createElement(LaunchProductList, {
      product,
      snapshotId: SNAPSHOT_A,
    })
  );
  assert.ok(htmlLoading.includes('Loading product results…'));

  const htmlError = ReactDOMServer.renderToStaticMarkup(
    React.createElement(LaunchProductList, {
      product,
      snapshotId: SNAPSHOT_A,
      initialError: 'Product results are unavailable.',
    })
  );
  assert.ok(htmlError.includes('role="alert"'));
  assert.ok(htmlError.includes('Product results are unavailable.'));

  const htmlGated409 = ReactDOMServer.renderToStaticMarkup(
    React.createElement(LaunchProductList, {
      product,
      snapshotId: SNAPSHOT_A,
      initialError: 'Product is gated for this snapshot: requires calibration update.',
    })
  );
  assert.ok(htmlGated409.includes('Product is gated for this snapshot: requires calibration update.'));
});

test('LaunchProductList renders empty results state', () => {
  const product = {
    id: 'preset.empty_test',
    pillar_id: 'presets',
    kind: 'preset',
    label: 'Empty Preset',
    category: 'Challenge',
    criteria_summary: 'Summary text',
    availability_status: 'predicted',
    missing_dependencies: [],
    evidence_needed: [],
  };
  const emptyData = makeMockV2Response({ results: [], matched_worlds: 0 });

  const html = ReactDOMServer.renderToStaticMarkup(
    React.createElement(LaunchProductList, {
      product,
      snapshotId: SNAPSHOT_A,
      initialData: emptyData,
    })
  );
  assert.ok(html.includes('No retained matches in this snapshot.'));
  assert.ok(html.includes('0 retained matches · 200 evaluated catalog worlds'));
});

test('LaunchProductList renders 20 rows with signed64 strings, witnesses, metrics, disclaimers, and pagination', () => {
  const product = {
    id: 'realm.standard_2048',
    pillar_id: 'realm',
    kind: 'realm',
    label: 'Realm 2048 Standard Play',
    category: 'Certified Realm Worlds',
    criteria_summary: 'Standard 2048 realm worlds.',
    availability_status: 'predicted',
    missing_dependencies: [],
    evidence_needed: [],
  };
  const mockData = makeMockV2Response({
    product_id: 'realm.standard_2048',
  });

  const html = ReactDOMServer.renderToStaticMarkup(
    React.createElement(LaunchProductList, {
      product,
      snapshotId: SNAPSHOT_A,
      initialData: mockData,
    })
  );

  // 1. Check Realm 2048 qualification notice
  assert.ok(html.includes('Realm 2048 Qualification'));
  assert.ok(html.includes('845 Overworld, 265 luxury biomes and 140 Nether'));
  assert.ok(html.includes('Larger Overworld boards have separate calibrated requirements'));

  // 2. Check Disclaimers (never claim physical census / verified portal / walkability)
  assert.ok(html.includes('predicted start coordinates, not a physical census'));
  assert.ok(html.includes('Nether positions use floor(OW/8) and do not identify a verified portal'));
  assert.ok(!html.includes('Certification capacity'));
  assert.ok(!html.includes('2048/845'));
  assert.ok(html.includes('2048 × 2048 Overworld blocks'));
  assert.ok(html.includes('OW 820/845'));

  // 3. Check 20 evaluation rows and signed64 seed string preservation
  assert.ok(html.includes('142 retained matches · 200 evaluated catalog worlds'));
  assert.ok(html.includes('#1'));
  assert.ok(html.includes('#20'));
  // Verify full signed64 strings appear in code tags
  assert.ok(html.includes(mockData.results[0].seed));
  assert.ok(html.includes(mockData.results[1].seed));
  assert.ok(html.includes(mockData.results[19].seed));

  // 4. Check anchor coordinates (OW horizontal + Nether projected floor(OW/8))
  assert.ok(html.includes('Anchor (origin):'));
  assert.ok(html.includes('Overworld [X 0, Z 0]'));
  assert.ok(html.includes('Nether [X 0, Z 0]'));
  assert.ok(html.includes('(projected floor(OW/8); not a verified portal)'));

  // 5. Check metrics rendering (density, max distance², realm breakdown, rational fractions)
  assert.ok(html.includes('Score: 1150'));
  assert.ok(html.includes('OW 820/845, luxury 250/265, Nether 80/140'));
  assert.ok(html.includes('24 predicted starts (complete)'));
  assert.ok(html.includes('Max distance²: 45000'));
  assert.ok(html.includes('Ranking measures:'));
  assert.ok(html.includes('1, 1/20'));

  // 6. Check pagination controls (20 per page, Previous 20, Next 20, Page 1)
  assert.ok(html.includes('Previous 20'));
  assert.ok(html.includes('Page 1'));
  assert.ok(html.includes('Next 20'));
  assert.ok(html.includes('aria-label="Product pagination"'));

  // 7. Check copy button and witness view button
  assert.ok(html.includes('Copy seed'));
  assert.ok(html.includes('View witnesses (2)'));
});

test('response guards reject unsafe source rows and preserve signed64 boundaries',()=>{
  for(const mutate of [r=>r.results[0].product_id='other',r=>r.results[0].seed='-0',r=>r.results[0].seed='9223372036854775808',r=>r.results[0].status='pending',r=>r.results[0].anchor.nether=[-1,0],r=>r.results[0].witnesses[0]=null,r=>r.results[0].witnesses[0].feature=4,r=>r.results[0].witnesses[0].observation_id='f'.repeat(64),r=>r.results[0].witnesses[0].distance_squared=0,r=>r.results[0].witnesses[0].provider='' ]){
    const data=makeMockV2Response();mutate(data);assert.equal(validateProductResultsV2(data,SNAPSHOT_A,data.product_id).ok,false);
  }
  for(const seed of ['-9223372036854775808','9223372036854775807','0']){
    const data=makeMockV2Response();data.results[0].seed=seed;assert.equal(validateProductResultsV2(data,SNAPSHOT_A,data.product_id).ok,true);
  }
});

// Summary
console.log(`\n========================================`);
console.log(`${passedTests} Catalog V2 UI tests passed; ${failedTests} failed.`);
console.log(`========================================\n`);
