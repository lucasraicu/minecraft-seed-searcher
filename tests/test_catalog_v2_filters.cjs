/**
 * Unit & Integration Tests for Catalog V2 Filter Builder and Constants
 * Conforms to task contract:
 * - Tests legacy vs V2 options (14 vs 31 features)
 * - Tests dimension radius rules (OW 256/512/1024 vs Nether 64/128/256)
 * - Tests mixed-dimension OR safeguards (single-dimension biome OR)
 * - Tests pure helpers exported from FilterBuilder.tsx and constants.ts
 * - Tests actual transpile and real ReactDOM renderToString
 * - Asserts floor(OW/8) projection reference and visible cleartext "no actual portal claim"
 */
const fs = require('fs');
const path = require('path');
const { createRequire } = require('module');
const assert = require('assert');

const webUiRequire = createRequire(path.resolve('web-ui/package.json'));
const React = webUiRequire('react');
const ReactDOMServer = webUiRequire('react-dom/server');
const ts = webUiRequire('typescript');

function loadTsModule(filePath, customExports = {}) {
  const code = fs.readFileSync(filePath, 'utf8');
  const transpiled = ts.transpileModule(code, {
    compilerOptions: {
      module: ts.ModuleKind.CommonJS,
      target: ts.ScriptTarget.ES2022,
      jsx: ts.JsxEmit.ReactJSX,
    },
  });

  const moduleObj = { exports: {} };
  const contextRequire = (mod) => {
    if (mod === 'react') return React;
    if (mod === 'react/jsx-runtime') {
      return webUiRequire('react/jsx-runtime');
    }
    if (mod === 'react/jsx-dev-runtime') {
      return webUiRequire('react/jsx-dev-runtime');
    }
    if (mod === './types') return {};
    if (mod === './constants') return customExports.constants || {};
    return webUiRequire(mod);
  };

  const fn = new Function('require', 'module', 'exports', transpiled.outputText);
  fn(contextRequire, moduleObj, moduleObj.exports);
  return moduleObj.exports;
}

const constants = loadTsModule(path.resolve('web-ui/src/catalog/constants.ts'));
const filterBuilder = loadTsModule(path.resolve('web-ui/src/catalog/FilterBuilder.tsx'), { constants });

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

console.log('=== Suite 1: Constants & Vocabulary Verification ===');

test('Legacy vocabulary: 14 OW structures, 9 OW biomes, radii 256/512/1024', () => {
  assert.strictEqual(constants.KNOWN_STRUCTURES.length, 14);
  assert(constants.KNOWN_STRUCTURES.every(s => s.dimension === 'overworld' || s.category === 'Overworld'));
  assert.strictEqual(constants.KNOWN_BIOMES.length, 9);
  assert(constants.KNOWN_BIOMES.every(b => b.dimension === 'overworld' || b.category === 'Overworld'));
  assert.deepStrictEqual(constants.NEAR_RADII, [256, 512, 1024]);
});

test('V2 vocabulary: 8 new typed features (1 OW stronghold, 2 Nether structures, 5 Nether biomes)', () => {
  assert.strictEqual(constants.V2_NEW_STRUCTURES.length, 3);
  assert.strictEqual(constants.V2_NEW_STRUCTURES.find(s => s.id === 'structure.stronghold')?.dimension, 'overworld');
  assert.strictEqual(constants.V2_NEW_STRUCTURES.find(s => s.id === 'structure.fortress')?.dimension, 'nether');
  assert.strictEqual(constants.V2_NEW_STRUCTURES.find(s => s.id === 'structure.bastion')?.dimension, 'nether');

  assert.strictEqual(constants.V2_NEW_BIOMES.length, 5);
  const netherBiomeIds = [
    'biome.nether_wastes',
    'biome.crimson_forest',
    'biome.warped_forest',
    'biome.soul_sand_valley',
    'biome.basalt_deltas',
  ];
  for (const id of netherBiomeIds) {
    const biome = constants.V2_NEW_BIOMES.find(b => b.id === id);
    assert(biome, `Missing nether biome: ${id}`);
    assert.strictEqual(biome.dimension, 'nether');
  }
});

test('V2 feature totals: 17 structures, 14 biomes, 31 total features exposed', () => {
  assert.strictEqual(constants.V2_STRUCTURES.length, 17);
  assert.strictEqual(constants.V2_BIOMES.length, 14);
  assert.strictEqual(constants.ALL_FEATURES_V2.length, 31);
});

test('Nether radii & fixed side constants', () => {
  assert.deepStrictEqual(constants.OVERWORLD_NEAR_RADII, [256, 512, 1024]);
  assert.deepStrictEqual(constants.NETHER_NEAR_RADII, [64, 128, 256]);
  assert.deepStrictEqual(constants.ALL_NEAR_RADII, [64, 128, 256, 512, 1024]);
  assert.strictEqual(constants.NETHER_FIXED_SIDE, 1024);
  assert.strictEqual(constants.DEFAULT_OVERWORLD_NEAR_RADIUS, 512);
  assert.strictEqual(constants.DEFAULT_NETHER_NEAR_RADIUS, 128);
});

test('featureLabel resolves legacy, V2, and unknown features', () => {
  assert.strictEqual(constants.featureLabel('structure.village'), 'Village');
  assert.strictEqual(constants.featureLabel('structure.stronghold'), 'Stronghold');
  assert.strictEqual(constants.featureLabel('structure.fortress'), 'Nether fortress');
  assert.strictEqual(constants.featureLabel('structure.bastion'), 'Bastion remnant');
  assert.strictEqual(constants.featureLabel('biome.cherry_grove'), 'Cherry grove');
  assert.strictEqual(constants.featureLabel('biome.nether_wastes'), 'Nether Wastes');
  assert.strictEqual(constants.featureLabel('biome.warped_forest'), 'Warped Forest');
});

test('getFeatureDimension accurately identifies Nether vs Overworld', () => {
  assert.strictEqual(constants.getFeatureDimension('structure.village'), 'overworld');
  assert.strictEqual(constants.getFeatureDimension('structure.stronghold'), 'overworld');
  assert.strictEqual(constants.getFeatureDimension('biome.plains'), 'overworld');
  assert.strictEqual(constants.getFeatureDimension('structure.fortress'), 'nether');
  assert.strictEqual(constants.getFeatureDimension('structure.bastion'), 'nether');
  assert.strictEqual(constants.getFeatureDimension('biome.nether_wastes'), 'nether');
  assert.strictEqual(constants.getFeatureDimension('biome.basalt_deltas'), 'nether');
  assert.strictEqual(constants.isNetherFeature('structure.fortress'), true);
  assert.strictEqual(constants.isNetherFeature('structure.village'), false);
});

console.log('=== Suite 2: Pure Helper Functions & Radius Normalization ===');

test('normalizeRadiusForDimension handles Overworld and Nether constraints', () => {
  // Overworld valid: 256, 512, 1024
  assert.strictEqual(constants.normalizeRadiusForDimension('overworld', 256), 256);
  assert.strictEqual(constants.normalizeRadiusForDimension('overworld', 512), 512);
  assert.strictEqual(constants.normalizeRadiusForDimension('overworld', 1024), 1024);
  assert.strictEqual(constants.normalizeRadiusForDimension('overworld', 64), 512);
  assert.strictEqual(constants.normalizeRadiusForDimension('overworld', 128), 512);
  assert.strictEqual(constants.normalizeRadiusForDimension('overworld', undefined), 512);

  // Nether valid: 64, 128, 256
  assert.strictEqual(constants.normalizeRadiusForDimension('nether', 64), 64);
  assert.strictEqual(constants.normalizeRadiusForDimension('nether', 128), 128);
  assert.strictEqual(constants.normalizeRadiusForDimension('nether', 256), 256);
  assert.strictEqual(constants.normalizeRadiusForDimension('nether', 512), 128);
  assert.strictEqual(constants.normalizeRadiusForDimension('nether', 1024), 128);
  assert.strictEqual(constants.normalizeRadiusForDimension('nether', undefined), 128);

  // 256 is compatible with BOTH dimensions and must be preserved across switches
  assert.strictEqual(constants.normalizeRadiusForDimension('overworld', 256), 256);
  assert.strictEqual(constants.normalizeRadiusForDimension('nether', 256), 256);
});

test('getRowDimension inspects structure and biome rows', () => {
  const owStructRow = { id: '1', rule: 'preferred', kind: 'structure_count', feature: 'structure.village', at_least: 1, scope: { kind: 'near_base', radius: 512 } };
  const netherStructRow = { id: '2', rule: 'preferred', kind: 'structure_count', feature: 'structure.fortress', at_least: 1, scope: { kind: 'near_base', radius: 128 } };
  const owBiomeRow = { id: '3', rule: 'preferred', kind: 'biome_witness', any_of: ['biome.cherry_grove', 'biome.plains'], scope: { kind: 'inside_border' } };
  const netherBiomeRow = { id: '4', rule: 'preferred', kind: 'biome_witness', any_of: ['biome.crimson_forest'], scope: { kind: 'near_base', radius: 64 } };

  assert.strictEqual(filterBuilder.getRowDimension(owStructRow), 'overworld');
  assert.strictEqual(filterBuilder.getRowDimension(netherStructRow), 'nether');
  assert.strictEqual(filterBuilder.getRowDimension(owBiomeRow), 'overworld');
  assert.strictEqual(filterBuilder.getRowDimension(netherBiomeRow), 'nether');
});

test('switchRowFeature resets incompatible radius to 512 OW / 128 Nether, retains compatible radius & choices', () => {
  // Case 1: Overworld -> Nether with incompatible radius 1024 -> resets to 128
  const rowOW1024 = {
    id: 's1',
    rule: 'preferred',
    kind: 'structure_count',
    feature: 'structure.village',
    at_least: 2,
    importance: 5,
    scope: { kind: 'near_base', radius: 1024 },
  };
  const switchedToNether = filterBuilder.switchRowFeature(rowOW1024, 'structure.fortress', true);
  assert.strictEqual(switchedToNether.feature, 'structure.fortress');
  assert.strictEqual(switchedToNether.scope.kind, 'near_base');
  assert.strictEqual(switchedToNether.scope.radius, 128); // incompatible 1024 reset to 128
  assert.strictEqual(switchedToNether.at_least, 2); // retained
  assert.strictEqual(switchedToNether.importance, 5); // retained
  assert.strictEqual(switchedToNether.rule, 'preferred'); // retained

  // Case 2: Overworld -> Nether with compatible radius 256 -> retains 256
  const rowOW256 = {
    ...rowOW1024,
    scope: { kind: 'near_base', radius: 256 },
  };
  const switchedToNether256 = filterBuilder.switchRowFeature(rowOW256, 'structure.bastion', true);
  assert.strictEqual(switchedToNether256.scope.radius, 256); // 256 retained!

  // Case 3: Nether -> Overworld with incompatible radius 64 -> resets to 512
  const rowNether64 = {
    id: 's2',
    rule: 'required',
    kind: 'structure_count',
    feature: 'structure.fortress',
    at_least: 1,
    scope: { kind: 'near_base', radius: 64 },
  };
  const switchedToOW = filterBuilder.switchRowFeature(rowNether64, 'structure.stronghold', true);
  assert.strictEqual(switchedToOW.feature, 'structure.stronghold');
  assert.strictEqual(switchedToOW.scope.radius, 512); // incompatible 64 reset to 512
  assert.strictEqual(switchedToOW.rule, 'required'); // retained

  // Case 4: Nether -> Overworld with compatible radius 256 -> retains 256
  const rowNether256 = {
    ...rowNether64,
    scope: { kind: 'near_base', radius: 256 },
  };
  const switchedToOW256 = filterBuilder.switchRowFeature(rowNether256, 'structure.trial_chamber', true);
  assert.strictEqual(switchedToOW256.scope.radius, 256); // 256 retained!

  // Case 5: inside_border scope retains inside_border
  const rowInsideBorder = {
    id: 's3',
    rule: 'preferred',
    kind: 'structure_count',
    feature: 'structure.village',
    at_least: 1,
    scope: { kind: 'inside_border' },
  };
  const switchedInsideBorder = filterBuilder.switchRowFeature(rowInsideBorder, 'structure.fortress', true);
  assert.deepStrictEqual(switchedInsideBorder.scope, { kind: 'inside_border' });
});

test('switchBiomeDimension enforces single-dimension and normalizes radius', () => {
  const owBiomeRow = {
    id: 'b1',
    rule: 'preferred',
    kind: 'biome_witness',
    any_of: ['biome.cherry_grove', 'biome.desert'],
    importance: 3,
    scope: { kind: 'near_base', radius: 1024 },
  };

  // Switch to Nether
  const netherBiomeRow = filterBuilder.switchBiomeDimension(owBiomeRow, 'nether');
  assert.deepStrictEqual(netherBiomeRow.any_of, ['biome.nether_wastes']);
  assert.strictEqual(netherBiomeRow.scope.radius, 128); // 1024 normalized to 128

  // Switch back to Overworld
  const owBiomeRowBack = filterBuilder.switchBiomeDimension(netherBiomeRow, 'overworld');
  assert.deepStrictEqual(owBiomeRowBack.any_of, ['biome.cherry_grove']);
  assert.strictEqual(owBiomeRowBack.scope.radius, 512); // 128 normalized to 512

  // Compatible radius 256 is retained across dimension switches
  const rowWith256 = { ...owBiomeRow, scope: { kind: 'near_base', radius: 256 } };
  const netherWith256 = filterBuilder.switchBiomeDimension(rowWith256, 'nether');
  assert.strictEqual(netherWith256.scope.radius, 256);
});

test('toggleBiomeSelectionInRow prevents mixed-dimension biome OR and switches dimension cleanly', () => {
  // Legacy mode: multi-select within Overworld
  let row = {
    id: 'b_leg',
    rule: 'preferred',
    kind: 'biome_witness',
    any_of: ['biome.cherry_grove'],
    scope: { kind: 'inside_border' },
  };
  row = filterBuilder.toggleBiomeSelectionInRow(row, 'biome.plains', false);
  assert.deepStrictEqual(row.any_of, ['biome.cherry_grove', 'biome.plains']);
  row = filterBuilder.toggleBiomeSelectionInRow(row, 'biome.cherry_grove', false);
  assert.deepStrictEqual(row.any_of, ['biome.plains']);
  // Cannot uncheck the last remaining biome
  row = filterBuilder.toggleBiomeSelectionInRow(row, 'biome.plains', false);
  assert.deepStrictEqual(row.any_of, ['biome.plains']);

  // V2 mode: Same dimension toggle works
  let v2Row = {
    id: 'b_v2',
    rule: 'preferred',
    kind: 'biome_witness',
    any_of: ['biome.cherry_grove'],
    importance: 3,
    scope: { kind: 'near_base', radius: 1024 },
  };
  v2Row = filterBuilder.toggleBiomeSelectionInRow(v2Row, 'biome.badlands', true);
  assert.deepStrictEqual(v2Row.any_of, ['biome.cherry_grove', 'biome.badlands']);

  // V2 mode: Clicking a Nether biome switches dimension!
  // Mixed-dimension OR is IMPOSSIBLE: Overworld biomes are replaced by the clicked Nether biome.
  v2Row = filterBuilder.toggleBiomeSelectionInRow(v2Row, 'biome.crimson_forest', true);
  assert.deepStrictEqual(v2Row.any_of, ['biome.crimson_forest']);
  assert.strictEqual(v2Row.scope.radius, 128); // incompatible 1024 reset to 128

  // V2 mode: Within Nether, toggle works
  v2Row = filterBuilder.toggleBiomeSelectionInRow(v2Row, 'biome.warped_forest', true);
  assert.deepStrictEqual(v2Row.any_of, ['biome.crimson_forest', 'biome.warped_forest']);

  // V2 mode: Clicking Overworld biome switches dimension back!
  v2Row = filterBuilder.toggleBiomeSelectionInRow(v2Row, 'biome.snowy', true);
  assert.deepStrictEqual(v2Row.any_of, ['biome.snowy']);
  assert.strictEqual(v2Row.scope.radius, 512); // incompatible 128 reset to 512
});

console.log('=== Suite 3: React DOM Server Render Tests ===');

test('Legacy FilterBuilder (enableV2=false): never offers new features or Nether radii', () => {
  const legacyRows = [
    {
      id: 'row-ow-struct',
      rule: 'preferred',
      kind: 'structure_count',
      feature: 'structure.village',
      at_least: 1,
      importance: 3,
      scope: { kind: 'near_base', radius: 512 },
    },
    {
      id: 'row-ow-biome',
      rule: 'preferred',
      kind: 'biome_witness',
      any_of: ['biome.cherry_grove'],
      importance: 3,
      scope: { kind: 'inside_border' },
    },
  ];

  const html = ReactDOMServer.renderToString(
    React.createElement(filterBuilder.FilterBuilder, {
      rows: legacyRows,
      onChangeRows: () => {},
      onResetRows: () => {},
      enableV2: false,
    })
  );

  // Must include legacy structures & biomes
  assert(html.includes('Village'), 'Should render Village');
  assert(html.includes('Cherry grove'), 'Should render Cherry grove');
  assert(html.includes('Near Base'), 'Should render Near Base');
  assert(html.includes('Inside Border'), 'Should render Inside Border');
  assert(html.includes('value="512"'), 'Should render 512m radius option');
  assert(html.includes('value="256"'), 'Should render 256m radius option');
  assert(html.includes('value="1024"'), 'Should render 1024m radius option');

  // Must NOT include V2 structures
  assert(!html.includes('Stronghold'), 'Legacy must NOT include Stronghold');
  assert(!html.includes('Nether fortress'), 'Legacy must NOT include Nether fortress');
  assert(!html.includes('Bastion remnant'), 'Legacy must NOT include Bastion remnant');

  // Must NOT include V2 Nether biomes
  assert(!html.includes('Nether Wastes'), 'Legacy must NOT include Nether Wastes');
  assert(!html.includes('Crimson Forest'), 'Legacy must NOT include Crimson Forest');
  assert(!html.includes('Warped Forest'), 'Legacy must NOT include Warped Forest');
  assert(!html.includes('Soul Sand Valley'), 'Legacy must NOT include Soul Sand Valley');
  assert(!html.includes('Basalt Deltas'), 'Legacy must NOT include Basalt Deltas');

  // Must NOT include Nether radii
  assert(!html.includes('value="64"'), 'Legacy must NOT include 64m');
  assert(!html.includes('value="128"'), 'Legacy must NOT include 128m');

  // Must NOT include Nether text, floor8 projection, or portal notice
  assert(!html.includes('floor(OW/8)'), 'Legacy must NOT include floor8');
  assert(!html.includes('no actual portal claim') && !html.includes('No actual portal claim'), 'Legacy must NOT include portal claim notice');
  assert(!html.includes('Fixed 1024m Square'), 'Legacy must NOT include Fixed 1024m Square');
});

test('V2 FilterBuilder (enableV2=true): exposes 31 features, groups OW/Nether, renders distinct radii and portal cleartext', () => {
  const v2Rows = [
    {
      id: 'row-nether-struct',
      rule: 'preferred',
      kind: 'structure_count',
      feature: 'structure.fortress',
      at_least: 1,
      importance: 3,
      scope: { kind: 'near_base', radius: 128 },
    },
    {
      id: 'row-nether-biome',
      rule: 'preferred',
      kind: 'biome_witness',
      any_of: ['biome.crimson_forest'],
      importance: 3,
      scope: { kind: 'inside_border' },
    },
    {
      id: 'row-ow-struct',
      rule: 'required',
      kind: 'structure_count',
      feature: 'structure.stronghold',
      at_least: 1,
      scope: { kind: 'near_base', radius: 512 },
    },
  ];

  const html = ReactDOMServer.renderToString(
    React.createElement(filterBuilder.FilterBuilder, {
      rows: v2Rows,
      onChangeRows: () => {},
      onResetRows: () => {},
      enableV2: true,
    })
  );

  // Exposes V2 additions
  assert(html.includes('Stronghold'), 'V2 must include Stronghold');
  assert(html.includes('Nether fortress'), 'V2 must include Nether fortress');
  assert(html.includes('Bastion remnant'), 'V2 must include Bastion remnant');
  assert(html.includes('Nether Wastes'), 'V2 must include Nether Wastes');
  assert(html.includes('Crimson Forest'), 'V2 must include Crimson Forest');
  assert(html.includes('Warped Forest'), 'V2 must include Warped Forest');
  assert(html.includes('Soul Sand Valley'), 'V2 must include Soul Sand Valley');
  assert(html.includes('Basalt Deltas'), 'V2 must include Basalt Deltas');

  // Clearly groups OW and Nether in structures
  assert(html.includes('<optgroup label="Overworld">'), 'Must have Overworld optgroup');
  assert(html.includes('<optgroup label="Nether">'), 'Must have Nether optgroup');

  // Clearly groups OW and Nether in biomes
  assert(html.includes('Overworld Biomes (9)'), 'Must have Overworld biomes heading');
  assert(html.includes('Nether Biomes (5)'), 'Must have Nether biomes heading');

  // Enforces single-dimension notice in biome row
  assert(html.includes('single dimension only'), 'Must state single dimension only for biomes');

  // Nether scope & distinct radii
  assert(html.includes('Fixed 1024m Square'), 'Nether row inside_border must show Fixed 1024m Square');
  assert(html.includes('value="64"'), 'Must render 64m Nether radius option');
  assert(html.includes('value="128"'), 'Must render 128m Nether radius option');
  assert(html.includes('value="256"'), 'Must render 256m Nether radius option');

  // Visible cleartext requirements:
  // 1. All requirements share chosen OW anchor and its floor8 projection
  assert(html.includes('floor(OW/8)'), 'Must reference floor(OW/8) projection');
  // 2. Visible cleartext: no actual portal claim
  assert(
    html.includes('No actual portal claim') || html.includes('no actual portal claim'),
    'Must render visible cleartext: no actual portal claim'
  );
  // 3. Fixed 1024m square reference in cleartext notice
  assert(html.includes('fixed 1024m square'), 'Must state fixed 1024m square');
});

test('Default enableV2 prop evaluates to false', () => {
  const htmlWithoutProp = ReactDOMServer.renderToString(
    React.createElement(filterBuilder.FilterBuilder, {
      rows: [],
      onChangeRows: () => {},
      onResetRows: () => {},
    })
  );
  assert(!htmlWithoutProp.includes('Nether fortress'), 'Default prop must not enable V2');
  assert(!htmlWithoutProp.includes('floor(OW/8)'), 'Default prop must not show floor(OW/8)');
  assert(!htmlWithoutProp.includes('No actual portal claim'), 'Default prop must not show portal claim');
});

console.log(`\n========================================`);
console.log(`Summary: All ${passedTests} / ${totalTests} tests passed successfully!`);
console.log(`========================================\n`);
