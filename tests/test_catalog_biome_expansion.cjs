/**
 * Test suite for Catalog Biome Expansion V3:
 * - Conforms to docs/catalog/v3/INTERFACES.md and PUBLIC_CATALOG_BIOME_EXPANSION_PLAN.md
 * - V3 Feature Registry: 56 OW exact choices (46 enabled, 10 gated), 4 groups, 2 contextual structures, 5 Nether biomes
 * - Snapshot negotiation: catalog-query-v3 / predicted_observations_v3, catalog-query-v2, catalog-query-v1
 * - Serialization constraints: max 12 rows, max 16 alternatives per any_of row
 * - FilterBuilder pure helpers: dimension detection, radius normalization, max 16 alternative capping, gated option prevention, search filtering
 * - React SSR rendering: FilterBuilder (V3, V2, V1), DetailModal (XYZ witness heights and evidence states), LaunchProductList (witnesses, primary/reserve counts)
 */

const path = require('node:path');
const fs = require('node:fs');
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

// Import catalog modules
const constants = require(path.resolve(webUiDir, 'src/catalog/constants.ts'));
const validation = require(path.resolve(webUiDir, 'src/catalog/validation.ts'));
const filterBuilder = require(path.resolve(webUiDir, 'src/catalog/FilterBuilder.tsx'));
const detailModal = require(path.resolve(webUiDir, 'src/catalog/DetailModal.tsx'));
const productList = require(path.resolve(webUiDir, 'src/catalog/LaunchProductList.tsx'));

let totalTests = 0;
let passedTests = 0;

function test(name, fn) {
  totalTests++;
  try {
    fn();
    passedTests++;
    console.log(`  ✓ ${name}`);
  } catch (err) {
    console.error(`  ✗ ${name}`);
    console.error(err);
    process.exit(1);
  }
}

console.log('=== Suite 1: V3 Feature Registry Vocabulary & Metadata ===');

test('V3 Exact Biomes: Exactly 56 Overworld choices', () => {
  assert.strictEqual(constants.V3_EXACT_BIOMES.length, 56);
  assert(constants.V3_EXACT_BIOMES.every(b => b.id.startsWith('biome.exact.')));
  assert(constants.V3_EXACT_BIOMES.every(b => b.dimension === 'overworld'));
});

test('Core 46 Overworld choices enabled, 10 mountain and cave choices gated', () => {
  const enabledBiomes = constants.V3_EXACT_BIOMES.filter(b => b.available === true);
  const gatedBiomes = constants.V3_EXACT_BIOMES.filter(b => b.available === false);

  assert.strictEqual(enabledBiomes.length, 46);
  assert.strictEqual(gatedBiomes.length, 10);

  // Six mountain biomes gated with mountain height profile reason
  const mountainIds = [
    'biome.exact.windswept_hills',
    'biome.exact.windswept_gravelly_hills',
    'biome.exact.jagged_peaks',
    'biome.exact.frozen_peaks',
    'biome.exact.stony_peaks',
    'biome.exact.grove',
  ];
  for (const mid of mountainIds) {
    const feat = gatedBiomes.find(b => b.id === mid);
    assert(feat, `Missing gated mountain: ${mid}`);
    assert.strictEqual(feat.available, false);
    assert(feat.unavailable_reason.includes('mountain'));
    assert.deepStrictEqual(feat.eligible_y, [96, 160, 224]);
  }

  // Four cave biomes gated with subterranean profile reason
  const caveIds = [
    'biome.exact.lush_caves',
    'biome.exact.dripstone_caves',
    'biome.exact.deep_dark',
    'biome.exact.sulfur_caves',
  ];
  for (const cid of caveIds) {
    const feat = gatedBiomes.find(b => b.id === cid);
    assert(feat, `Missing gated cave: ${cid}`);
    assert.strictEqual(feat.available, false);
    assert(feat.unavailable_reason.includes('cave'));
    assert.deepStrictEqual(feat.eligible_y, [-48, 0]);
  }
});

test('Four declared biome groups with exact atomic members', () => {
  assert.strictEqual(constants.V3_BIOME_GROUPS.length, 4);

  const badlandsGroup = constants.V3_BIOME_GROUPS.find(g => g.id === 'biome.group.badlands');
  assert(badlandsGroup);
  assert.strictEqual(badlandsGroup.available, true);
  assert.deepStrictEqual(badlandsGroup.canonical_members, [
    'biome.exact.badlands',
    'biome.exact.eroded_badlands',
    'biome.exact.wooded_badlands',
  ]);

  const snowyGroup = constants.V3_BIOME_GROUPS.find(g => g.id === 'biome.group.snowy');
  assert(snowyGroup);
  assert.strictEqual(snowyGroup.available, true);
  assert.deepStrictEqual(snowyGroup.canonical_members, [
    'biome.exact.snowy_plains',
    'biome.exact.snowy_slopes',
    'biome.exact.snowy_taiga',
    'biome.exact.ice_spikes',
  ]);

  const forestGroup = constants.V3_BIOME_GROUPS.find(g => g.id === 'biome.group.forest');
  assert(forestGroup);
  assert.strictEqual(forestGroup.available, true);
  assert.deepStrictEqual(forestGroup.canonical_members, [
    'biome.exact.forest',
    'biome.exact.birch_forest',
    'biome.exact.flower_forest',
    'biome.exact.old_growth_birch_forest',
  ]);

  const plainsGroup = constants.V3_BIOME_GROUPS.find(g => g.id === 'biome.group.plains');
  assert(plainsGroup);
  assert.strictEqual(plainsGroup.available, true);
  assert.deepStrictEqual(plainsGroup.canonical_members, [
    'biome.exact.plains',
    'biome.exact.sunflower_plains',
    'biome.exact.meadow',
  ]);
});

test('Contextual structures: basement igloo and treasure bastion initially gated', () => {
  assert.strictEqual(constants.V3_NEW_STRUCTURES.length, 2);

  const igloo = constants.V3_NEW_STRUCTURES.find(s => s.id === 'structure.igloo_with_basement');
  assert(igloo);
  assert.strictEqual(igloo.dimension, 'overworld');
  assert.strictEqual(igloo.available, false);
  assert(igloo.unavailable_reason.includes('auxiliary controls'));

  const bastion = constants.V3_NEW_STRUCTURES.find(s => s.id === 'structure.bastion_treasure');
  assert(bastion);
  assert.strictEqual(bastion.dimension, 'nether');
  assert.strictEqual(bastion.available, false);
  assert(bastion.unavailable_reason.includes('auxiliary controls'));
});

test('Feature dimension and Nether feature predicates', () => {
  assert.strictEqual(constants.getFeatureDimension('biome.exact.ocean'), 'overworld');
  assert.strictEqual(constants.getFeatureDimension('biome.group.forest'), 'overworld');
  assert.strictEqual(constants.getFeatureDimension('structure.igloo_with_basement'), 'overworld');
  assert.strictEqual(constants.getFeatureDimension('structure.bastion_treasure'), 'nether');
  assert.strictEqual(constants.getFeatureDimension('biome.nether_wastes'), 'nether');

  assert.strictEqual(constants.isNetherFeature('structure.bastion_treasure'), true);
  assert.strictEqual(constants.isNetherFeature('biome.nether_wastes'), true);
  assert.strictEqual(constants.isNetherFeature('biome.exact.ocean'), false);
  assert.strictEqual(constants.isNetherFeature('structure.igloo_with_basement'), false);
});

test('isV3Feature accurately identifies V3 additions vs V1/V2 legacy', () => {
  assert.strictEqual(constants.isV3Feature('biome.exact.cherry_grove'), true);
  assert.strictEqual(constants.isV3Feature('biome.exact.deep_dark'), true);
  assert.strictEqual(constants.isV3Feature('biome.group.plains'), true);
  assert.strictEqual(constants.isV3Feature('structure.igloo_with_basement'), true);
  assert.strictEqual(constants.isV3Feature('structure.bastion_treasure'), true);

  // Legacy and V2 features are not V3 exclusive
  assert.strictEqual(constants.isV3Feature('biome.cherry_grove'), false);
  assert.strictEqual(constants.isV3Feature('structure.village'), false);
  assert.strictEqual(constants.isV3Feature('structure.stronghold'), false);
  assert.strictEqual(constants.isV3Feature('structure.fortress'), false);
  assert.strictEqual(constants.isV3Feature('biome.nether_wastes'), false);
});

test('featureLabel resolves all V3 and legacy labels cleanly', () => {
  assert.strictEqual(constants.featureLabel('biome.exact.cherry_grove'), 'Cherry grove');
  assert.strictEqual(constants.featureLabel('biome.exact.deep_dark'), 'Deep dark');
  assert.strictEqual(constants.featureLabel('biome.group.badlands'), 'Badlands group');
  assert.strictEqual(constants.featureLabel('structure.igloo_with_basement'), 'Igloo with basement');
  assert.strictEqual(constants.featureLabel('structure.bastion_treasure'), 'Bastion treasure room');
  assert.strictEqual(constants.featureLabel('structure.village'), 'Village');
});

console.log('=== Suite 2: Serialization, Capping & Negotiation ===');

test('serializeRows limits any_of to max 16 unique alternatives', () => {
  const seventeenBiomes = [
    'biome.exact.ocean', 'biome.exact.deep_ocean', 'biome.exact.warm_ocean',
    'biome.exact.lukewarm_ocean', 'biome.exact.deep_lukewarm_ocean', 'biome.exact.cold_ocean',
    'biome.exact.deep_cold_ocean', 'biome.exact.frozen_ocean', 'biome.exact.deep_frozen_ocean',
    'biome.exact.river', 'biome.exact.beach', 'biome.exact.forest',
    'biome.exact.taiga', 'biome.exact.plains', 'biome.exact.meadow',
    'biome.exact.sunflower_plains', 'biome.exact.dark_forest',
  ];
  assert.strictEqual(seventeenBiomes.length, 17);

  const row = {
    id: 'row-1',
    rule: 'preferred',
    kind: 'biome_witness',
    any_of: seventeenBiomes,
    importance: 4,
    scope: { kind: 'near_base', radius: 512 },
  };

  assert.throws(()=>validation.serializeRows([row]),/16 alternatives/);
});

test('serializeRows bounds total rows to maximum 12', () => {
  const rows = Array.from({ length: 15 }, (_, i) => ({
    id: `row-${i}`,
    rule: 'preferred',
    kind: 'structure_count',
    feature: 'structure.village',
    at_least: 1,
    importance: 3,
    scope: { kind: 'near_base', radius: 512 },
  }));

  assert.throws(()=>validation.serializeRows(rows),/12 filter rows/);
});

test('serializeRows deduplicates repeated alternatives before capping', () => {
  const duplicates = [
    'biome.exact.plains', 'biome.exact.plains', 'biome.exact.plains',
    'biome.exact.forest', 'biome.exact.forest',
  ];
  const row = {
    id: 'row-1',
    rule: 'preferred',
    kind: 'biome_witness',
    any_of: duplicates,
    scope: { kind: 'inside_border' },
  };
  const serialized = validation.serializeRows([row]);
  assert.deepStrictEqual(serialized[0].any_of, ['biome.exact.plains', 'biome.exact.forest']);
});

console.log('=== Suite 3: FilterBuilder Pure Helpers ===');

test('getRowDimension identifies dimension from feature or any_of biomes', () => {
  const structureRowOW = {
    id: 'r1', rule: 'preferred', kind: 'structure_count',
    feature: 'structure.village', at_least: 1, scope: { kind: 'near_base', radius: 512 },
  };
  assert.strictEqual(filterBuilder.getRowDimension(structureRowOW), 'overworld');

  const structureRowNether = {
    id: 'r2', rule: 'preferred', kind: 'structure_count',
    feature: 'structure.bastion_treasure', at_least: 1, scope: { kind: 'near_base', radius: 128 },
  };
  assert.strictEqual(filterBuilder.getRowDimension(structureRowNether), 'nether');

  const biomeRowOW = {
    id: 'r3', rule: 'preferred', kind: 'biome_witness',
    any_of: ['biome.exact.cherry_grove', 'biome.group.plains'], scope: { kind: 'inside_border' },
  };
  assert.strictEqual(filterBuilder.getRowDimension(biomeRowOW), 'overworld');

  const biomeRowNether = {
    id: 'r4', rule: 'preferred', kind: 'biome_witness',
    any_of: ['biome.nether_wastes', 'biome.crimson_forest'], scope: { kind: 'inside_border' },
  };
  assert.strictEqual(filterBuilder.getRowDimension(biomeRowNether), 'nether');
});

test('switchRowFeature normalizes radius when switching dimension in V3', () => {
  const owRow = {
    id: 'r1', rule: 'preferred', kind: 'structure_count',
    feature: 'structure.village', at_least: 1, scope: { kind: 'near_base', radius: 512 },
  };
  // Switching from OW 512 to Nether structure normalizes radius to 128 (default Nether)
  const netherRow = filterBuilder.switchRowFeature(owRow, 'structure.bastion_treasure', true, true);
  assert.strictEqual(netherRow.feature, 'structure.bastion_treasure');
  assert.strictEqual(netherRow.scope.radius, 128);

  // Compatible radius (256m) is preserved across dimension switch
  const row256 = {
    id: 'r2', rule: 'preferred', kind: 'structure_count',
    feature: 'structure.village', at_least: 1, scope: { kind: 'near_base', radius: 256 },
  };
  const switched256 = filterBuilder.switchRowFeature(row256, 'structure.fortress', true, true);
  assert.strictEqual(switched256.scope.radius, 256);
});

test('switchBiomeDimension enforces default in new dimension and normalizes radius', () => {
  const owBiomeRow = {
    id: 'r1', rule: 'preferred', kind: 'biome_witness',
    any_of: ['biome.exact.forest'], scope: { kind: 'near_base', radius: 1024 },
  };
  const toNether = filterBuilder.switchBiomeDimension(owBiomeRow, 'nether', true);
  assert.strictEqual(toNether.any_of[0], 'biome.nether_wastes');
  assert.strictEqual(toNether.scope.radius, 128);

  const toOW = filterBuilder.switchBiomeDimension(toNether, 'overworld', true);
  assert.strictEqual(toOW.any_of[0], 'biome.exact.cherry_grove');
  assert.strictEqual(toOW.scope.radius, 512);
});

test('toggleBiomeSelectionInRow prevents selecting gated biomes in V3', () => {
  const row = {
    id: 'r1', rule: 'preferred', kind: 'biome_witness',
    any_of: ['biome.exact.plains'], scope: { kind: 'inside_border' },
  };
  // Jagged peaks is gated
  const result = filterBuilder.toggleBiomeSelectionInRow(row, 'biome.exact.jagged_peaks', true, true);
  assert.deepStrictEqual(result.any_of, ['biome.exact.plains']); // Unchanged

  // Deep dark is gated
  const resultCave = filterBuilder.toggleBiomeSelectionInRow(row, 'biome.exact.deep_dark', true, true);
  assert.deepStrictEqual(resultCave.any_of, ['biome.exact.plains']); // Unchanged
});

test('toggleBiomeSelectionInRow enforces 16-alternative ceiling in V3', () => {
  const sixteenBiomes = [
    'biome.exact.ocean', 'biome.exact.deep_ocean', 'biome.exact.warm_ocean',
    'biome.exact.lukewarm_ocean', 'biome.exact.deep_lukewarm_ocean', 'biome.exact.cold_ocean',
    'biome.exact.deep_cold_ocean', 'biome.exact.frozen_ocean', 'biome.exact.deep_frozen_ocean',
    'biome.exact.river', 'biome.exact.beach', 'biome.exact.forest',
    'biome.exact.taiga', 'biome.exact.plains', 'biome.exact.meadow',
    'biome.exact.sunflower_plains',
  ];
  assert.strictEqual(sixteenBiomes.length, 16);

  const row = {
    id: 'r1', rule: 'preferred', kind: 'biome_witness',
    any_of: sixteenBiomes, scope: { kind: 'inside_border' },
  };

  // Attempting to add 17th biome is blocked
  const result = filterBuilder.toggleBiomeSelectionInRow(row, 'biome.exact.cherry_grove', true, true);
  assert.strictEqual(result.any_of.length, 16);
  assert(!result.any_of.includes('biome.exact.cherry_grove'));

  // Deselecting an existing one works
  const deselected = filterBuilder.toggleBiomeSelectionInRow(row, 'biome.exact.ocean', true, true);
  assert.strictEqual(deselected.any_of.length, 15);
  assert(!deselected.any_of.includes('biome.exact.ocean'));
});

test('selectBiomeGroupInRow adds group choice towards the 16 limit', () => {
  const row = {
    id: 'r1', rule: 'preferred', kind: 'biome_witness',
    any_of: ['biome.exact.cherry_grove'], scope: { kind: 'inside_border' },
  };
  const withGroup = filterBuilder.selectBiomeGroupInRow(row, 'biome.group.forest', true);
  assert.deepStrictEqual(withGroup.any_of, ['biome.exact.cherry_grove', 'biome.group.forest']);
});

test('filterBiomesBySearch filters biomes by keyword across label, id and category', () => {
  const biomes = constants.V3_EXACT_BIOMES;

  const cherryMatch = filterBuilder.filterBiomesBySearch(biomes, 'cherry');
  assert.strictEqual(cherryMatch.length, 1);
  assert.strictEqual(cherryMatch[0].id, 'biome.exact.cherry_grove');

  const oceanMatches = filterBuilder.filterBiomesBySearch(biomes, 'ocean');
  assert(oceanMatches.length >= 9);

  const forestMatches = filterBuilder.filterBiomesBySearch(biomes, 'forest');
  assert(forestMatches.length >= 6);

  const emptyQuery = filterBuilder.filterBiomesBySearch(biomes, '');
  assert.strictEqual(emptyQuery.length, biomes.length);
});

console.log('=== Suite 4: React SSR Rendering Verification ===');

test('FilterBuilder renders in V3 mode with expandable groups, search bar and gated notices', () => {
  const rows = [
    {
      id: 'r1',
      rule: 'preferred',
      kind: 'biome_witness',
      any_of: ['biome.exact.cherry_grove'],
      importance: 5,
      scope: { kind: 'inside_border' },
    },
    {
      id: 'r2',
      rule: 'required',
      kind: 'structure_count',
      feature: 'structure.village',
      at_least: 1,
      scope: { kind: 'near_base', radius: 512 },
    },
  ];

  const html = ReactDOMServer.renderToString(
    React.createElement(filterBuilder.FilterBuilder, {
      rows,
      onChangeRows: () => {},
      onResetRows: () => {},
      enableV2: true,
      enableV3: true,
    })
  );

  // Search input rendered
  assert(html.includes('Search biomes &amp; groups') || html.includes('Search biomes & groups'));

  // Groups rendered with Any + Atomic buttons
  assert(html.includes('Any Badlands group') || html.includes('Badlands group'));
  assert(html.includes('Any Snowy group') || html.includes('Snowy group'));
  assert(html.includes('Any Forest / birch group') || html.includes('Forest / birch group'));
  assert(html.includes('Any Plains / meadow group') || html.includes('Plains / meadow group'));

  // Gated mountain and cave options rendered with Gated indicators and disabled
  assert(html.includes('Windswept hills') && html.includes('Gated'));
  assert(html.includes('Jagged peaks') && html.includes('Gated'));
  assert(html.includes('Deep dark') && html.includes('Gated'));
  assert(html.includes('Lush caves') && html.includes('Gated'));

  // Notice about coordinate scaling and no portal claim
  assert(html.includes('Nether Coordinate Scaling'));
  assert(html.includes('No actual portal claim'));
});

test('FilterBuilder renders in V2 and V1 legacy modes for full backwards compatibility', () => {
  const rows = [
    {
      id: 'r1',
      rule: 'preferred',
      kind: 'biome_witness',
      any_of: ['biome.cherry_grove'],
      importance: 3,
      scope: { kind: 'inside_border' },
    },
  ];

  // V2 render
  const htmlV2 = ReactDOMServer.renderToString(
    React.createElement(filterBuilder.FilterBuilder, {
      rows,
      onChangeRows: () => {},
      onResetRows: () => {},
      enableV2: true,
      enableV3: false,
    })
  );
  assert(htmlV2.includes('Overworld Biomes (9)'));
  assert(htmlV2.includes('Nether Biomes (5)'));

  // V1 render
  const htmlV1 = ReactDOMServer.renderToString(
    React.createElement(filterBuilder.FilterBuilder, {
      rows,
      onChangeRows: () => {},
      onResetRows: () => {},
      enableV2: false,
      enableV3: false,
    })
  );
  assert(!htmlV1.includes('v2-anchor-projection-notice'));
  assert(!htmlV1.includes('Nether Biomes (5)'));
});

test('DetailModal renders witness XYZ coordinates and height evidence states', () => {
  const detail = {
    ok: true,
    snapshot_id: 'test-snapshot',
    world_id: 'w1',
    identity: { seed: '123456789012345' },
    layout: { border_side: 2048, anchor: [0, 0], anchor_mode: 'recommended' },
    structures: {
      'structure.village': [[100, 200]],
    },
    biome_witnesses: [
      { feature: 'biome.exact.ocean', x: 64, y: 63, z: -128, distance_squared: 20480 },
      { feature: 'biome.exact.jagged_peaks', x: 256, y: 160, z: 512, distance_squared: 327680 },
      { feature: 'biome.exact.deep_dark', x: 0, y: -48, z: 64, distance_squared: 4096 },
    ],
    coverage: {},
    evidence_label: 'V3 Research predictions with sampled height planes',
  };

  const originalUseState=React.useState;
  React.useState=(initial)=>originalUseState(initial==='map'?'biomes':initial);
  const html = ReactDOMServer.renderToString(
    React.createElement(detailModal.DetailModal, {
      detail,
      seedString: '123456789012345',
      snapshotId: 'test-snapshot',
      worldId: 'w1',
      layoutId: 'l1',
      isOpen: true,
      onClose: () => {},
    })
  );

  React.useState=originalUseState;
  // Check witness XYZ rendered in table
  assert(html.includes('Y (Height)'));
  assert(html.includes('Evidence State'));
  assert(html.includes('63'));
  assert(html.includes('160'));
  assert(html.includes('-48'));
  assert(html.includes('Predicted sample at Y=63'));
  assert(html.includes('Predicted sample at Y=160'));
  assert(html.includes('Predicted sample at Y=-48'));
});

test('validateProductResultsV2 accepts V3 responses with primary and reserve counts', () => {
  const v3Response = {
    ok: true,
    revision: 'catalog-product-results-v3',
    snapshot_id: 'a'.repeat(64),
    product_id: 'realm_2048',
    matched_worlds: 10,
    population_worlds: 222,
    results: [],
    next_cursor: null,
    evaluation_counts: { match: 10, no_match: 200, pending: 12 },
    scope: { dimension: 'overworld', radius: 1024 },
    policy_revision: 'b'.repeat(64),
    evidence_label: 'V3 public retention with 2x reserve',
    view: 'primary',
    primary_count: 10,
    reserve_count: 10,
  };

  const validationRes = productList.validateProductResultsV2(v3Response);
  assert(validationRes.ok, `Validation failed: ${validationRes.error}`);
  assert.strictEqual(validationRes.value.primary_count, 10);
  assert.strictEqual(validationRes.value.reserve_count, 10);
  assert.strictEqual(validationRes.value.view, 'primary');
});

test('LaunchProductList renders witnesses with XYZ coordinates and height state column', () => {
  const product = {
    id: 'realm_2048',
    pillar_id: 'realm',
    kind: 'record',
    label: 'Realm 2048 Board',
    category: 'Realm',
    criteria_summary: 'Comprehensive score across Overworld and Nether',
    availability_status: 'available',
    missing_dependencies: [],
    evidence_needed: [],
  };

  const initialData = {
    ok: true,
    revision: 'catalog-product-results-v2',
    snapshot_id: 'a'.repeat(64),
    product_id: 'realm_2048',
    matched_worlds: 1,
    population_worlds: 222,
    results: [
      {
        product_id: 'realm_2048',
        world_id: 'c'.repeat(64),
        seed: '9876543210987654321',
        observation_id: 'd'.repeat(64),
        status: 'match',
        rank: [1200],
        anchor: {
          mode: 'recommended',
          coordinate: [128, 256],
          overworld: [128, 256],
          nether: [16, 32],
        },
        witnesses: [
          {
            feature: 'biome.cherry_grove',
            dimension: 'overworld',
            coordinate: [128, 63, 256],
            distance_squared: 0,
            witness_id: 'e'.repeat(64),
            provider: 'test-provider',
            observation_id: 'd'.repeat(64),
          },
        ],
        scope: { dimension: 'overworld', radius: 1024 },
      },
    ],
    next_cursor: null,
    evaluation_counts: { match: 1, no_match: 220, pending: 1 },
    scope: { dimension: 'overworld', radius: 1024 },
    policy_revision: 'f'.repeat(64),
    evidence_label: 'Product evidence',
    primary_count: 1,
    reserve_count: 1,
  };

  const originalUseState=React.useState;
  let stateIndex=0;
  React.useState=(initial)=>{const n=stateIndex++;return originalUseState(n===4?'c'.repeat(64):initial);};
  const html = ReactDOMServer.renderToString(
    React.createElement(productList.LaunchProductList, {
      product,
      snapshotId: 'a'.repeat(64),
      initialData,
    })
  );

  React.useState=originalUseState;
  const text=html.replace(/<!--.*?-->/g,'');
  // Primary and reserve view switches rendered
  assert(text.includes('Primary (1)'));
  assert(text.includes('Reserve (1)'));

  // Witness coordinates and height state rendered
  assert(text.includes('Coordinates'));
  assert(text.includes('Height State'));
  assert(text.includes('X 128, Y 63, Z 256'));
  assert(text.includes('Predicted sample at Y=63'));
});

test('Snapshot metadata enables validated mountain choices and can gate a named group',()=>{
  const row={id:'activation',kind:'biome_witness',rule:'required',any_of:['biome.exact.forest'],scope:{kind:'inside_border'}};
  const enabled=[{id:'biome.exact.jagged_peaks',available:true}];
  assert(filterBuilder.toggleBiomeSelectionInRow(row,'biome.exact.jagged_peaks',true,true,enabled).any_of.includes('biome.exact.jagged_peaks'));
  assert.deepStrictEqual(filterBuilder.selectBiomeGroupInRow(row,'biome.group.forest',true,[{id:'biome.group.forest',available:false}]),row);
  assert(filterBuilder.filterBiomesBySearch(constants.V3_BIOME_GROUPS,'birch').some(f=>f.id==='biome.group.forest'));
});
test('Personal reserve selector is explicit and hidden for historical runs',()=>{
  const Feed=require(path.resolve(webUiDir,'src/components/CandidateFeed.tsx')).CandidateFeed;
  const props={candidates:[],selectedCandidate:null,onSelectCandidate:()=>{},onInspectCandidate:()=>{},onCopyNotice:()=>{}};
  const legacy=ReactDOMServer.renderToString(React.createElement(Feed,props));
  assert(!legacy.includes('Candidate retention view'));
  const html=ReactDOMServer.renderToString(React.createElement(Feed,{...props,reserveSelection:{primary:50,reserve:50,view:'primary',onChange:()=>{}}})).replace(/<!--.*?-->/g,'');
  assert(html.includes('Primary (50)')&&html.includes('Reserve (50)')&&html.includes('Predicted candidates'));
});
test('Candidate page rejects malformed reserve metadata',()=>{
  const network=require(path.resolve(webUiDir,'src/utils/network.ts'));
  const page={total:50,candidates:[],primary_count:50,reserve_count:50,view:'primary'};
  assert(network.validCandidatePage(page));
  assert(!network.validCandidatePage({...page,reserve_count:-1}));
  assert(!network.validCandidatePage({...page,view:'all'}));
});

console.log(`\n========================================`);
console.log(`All ${passedTests}/${totalTests} tests passed successfully!`);
console.log(`========================================\n`);
