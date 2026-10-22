/**
 * SSR Render Tests for EvidenceSummary React Component.
 *
 * Verifies SSR rendering using createRequire from web-ui/package.json,
 * typescript.transpileModule and React renderToStaticMarkup,
 * with zero local dependencies.
 */

const path = require('path');
const fs = require('fs');
const assert = require('assert');
const { createRequire } = require('module');

// Generic repo root computed dynamically from __dirname
const root = path.resolve(__dirname, '..');
const webUiPackageJson = path.join(root, 'web-ui', 'package.json');

function runTests() {
  const webUiRequire = createRequire(webUiPackageJson);

  const ts = webUiRequire('typescript'), React = webUiRequire('react'), ReactDOMServer = webUiRequire('react-dom/server');

  const componentPath = path.join(root, 'web-ui', 'src', 'catalog', 'EvidenceSummary.tsx');
  const sourceCode = fs.readFileSync(componentPath, 'utf8');

  // Transpile EvidenceSummary.tsx in CommonJS mode
  const transpileResult = ts.transpileModule(sourceCode, {
    compilerOptions: {
      module: ts.ModuleKind.CommonJS,
      target: ts.ScriptTarget.ES2020,
      jsx: ts.JsxEmit.React,
    },
  });

  const moduleExports = {};
  const moduleObj = { exports: moduleExports };

  // Custom require enforcing zero local dependencies
  function customRequire(id) {
    if (id === 'react') {
      if (!React.default) {
        React.default = React;
      }
      return React;
    }
    if (id === 'react/jsx-runtime') {
      return webUiRequire('react/jsx-runtime');
    }
    if (id.startsWith('.') || id.startsWith('/') || id.includes('types') || id.includes('constants')) {
      throw new Error(`Forbidden local dependency: ${id}. Component must have zero local dependencies.`);
    }
    return webUiRequire(id);
  }

  const runModule = new Function('require', 'module', 'exports', 'React', transpileResult.outputText);
  runModule(customRequire, moduleObj, moduleExports, React);

  const EvidenceSummary = moduleObj.exports.EvidenceSummary || moduleObj.exports.default;
  assert.strictEqual(typeof EvidenceSummary, 'function', 'EvidenceSummary must be an exported component function');

  // 1. Complete test case: 28 predicted, 28 tested (27 exact matches + 1 unresolved coordinate difference)
  {
    const summary = {
      revision: 'catalog-structure-evidence-summary-v1',
      feature_id: 'structure.village',
      predicted_count: 28,
      tested_count: 28,
      located_exact: 27,
      coordinate_difference: 1,
      no_location: 0,
      errors: 0,
      untested_count: 0,
      grouped_command: false,
      verifier_game_build_id: '1.26.52.3',
      generated_count: null,
      exhaustive_count: null,
    };

    const html = ReactDOMServer.renderToStaticMarkup(
      React.createElement(EvidenceSummary, { summary })
    );

    assert.ok(html.includes('27 BDS exact-location matches'), 'Must show 27 exact matches');
    assert.ok(html.includes('1 unresolved'), 'Must show 1 unresolved tested count');
    assert.ok(html.includes('28 predicted'), 'Must show 28 predicted');
    assert.ok(html.includes('0 untested'), 'Must show 0 untested');
    assert.ok(html.includes('1.26.52.3'), 'Must show verifier build 1.26.52.3');
    assert.ok(
      /not an exhaustive generated-building census/i.test(html),
      'Must explicitly state counts are not an exhaustive generated-building census'
    );
    assert.ok(
      /coordinate difference: 1/i.test(html),
      'Must show coordinate difference breakdown'
    );
    assert.ok(
      !/physical absence/i.test(html) || /not.*physical absence|do not indicate physical absence/i.test(html),
      'Must not conflate coordinate difference with physical absence'
    );
    assert.ok(
      !/fully verified|global verified|100% verified|all verified/i.test(html),
      'Must have no global verified badge or claim'
    );
  }

  // 2. Partial test case: 28 predicted, 3 tested (3 exact matches, 25 untested)
  {
    const summary = {
      revision: 'catalog-structure-evidence-summary-v1',
      feature_id: 'structure.village',
      predicted_count: 28,
      tested_count: 3,
      located_exact: 3,
      coordinate_difference: 0,
      no_location: 0,
      errors: 0,
      untested_count: 25,
      grouped_command: false,
      verifier_game_build_id: '1.26.52.3',
      generated_count: null,
      exhaustive_count: null,
    };

    const html = ReactDOMServer.renderToStaticMarkup(
      React.createElement(EvidenceSummary, { summary })
    );

    assert.ok(html.includes('3 BDS exact-location matches'), 'Must show 3 exact matches');
    assert.ok(html.includes('25 untested'), 'Must show 25 untested');
    assert.ok(html.includes('28 predicted'), 'Must show 28 predicted');
    assert.ok(html.includes('1.26.52.3'), 'Must show verifier build 1.26.52.3');
    assert.ok(
      /not an exhaustive generated-building census/i.test(html),
      'Must explicitly state counts are not an exhaustive generated-building census'
    );
    assert.ok(
      !/fully verified|global verified|100% verified|all verified/i.test(html),
      'Must have no global verified badge or claim'
    );
  }

  // 3. Missing evidence test cases: null, undefined, and tested_count === 0
  {
    for (const missingSummary of [null, undefined]) {
      const html = ReactDOMServer.renderToStaticMarkup(
        React.createElement(EvidenceSummary, { summary: missingSummary })
      );
      assert.ok(/not checked/i.test(html), 'Missing evidence must state not checked');
      assert.ok(
        /does not imply 0|don&#x27;t imply 0|not imply 0/i.test(html),
        'Missing evidence must state it does not imply 0 structures'
      );
      assert.ok(
        !/fully verified|global verified|100% verified|all verified/i.test(html),
        'Missing evidence must not claim full verification'
      );
    }

    // summary provided but tested_count === 0
    const untestedSummary = {
      revision: 'catalog-structure-evidence-summary-v1',
      feature_id: 'structure.village',
      predicted_count: 10,
      tested_count: 0,
      located_exact: 0,
      coordinate_difference: 0,
      no_location: 0,
      errors: 0,
      untested_count: 10,
      grouped_command: false,
      verifier_game_build_id: null,
      generated_count: null,
      exhaustive_count: null,
    };
    const htmlUntested = ReactDOMServer.renderToStaticMarkup(
      React.createElement(EvidenceSummary, { summary: untestedSummary })
    );
    assert.ok(/not checked/i.test(htmlUntested), 'Untested summary must say not checked');
    assert.ok(
      /does not imply 0|don&#x27;t imply 0|not imply 0/i.test(htmlUntested),
      'Untested summary must state it does not imply 0 structures'
    );
    assert.ok(htmlUntested.includes('10 untested'), 'Must show 10 untested');
    assert.ok(
      !/fully verified|global verified|100% verified|all verified/i.test(htmlUntested),
      'Must not claim full verification'
    );
  }

  // 4. Grouped temple commands: generic temple locations, not subtypes
  {
    const summary = {
      revision: 'catalog-structure-evidence-summary-v1',
      feature_id: 'structure.desert_pyramid',
      predicted_count: 4,
      tested_count: 4,
      located_exact: 4,
      coordinate_difference: 0,
      no_location: 0,
      errors: 0,
      untested_count: 0,
      grouped_command: true,
      verifier_game_build_id: '1.26.52.3',
      generated_count: null,
      exhaustive_count: null,
    };

    const html = ReactDOMServer.renderToStaticMarkup(
      React.createElement(EvidenceSummary, { summary })
    );

    assert.ok(
      /generic temple/i.test(html),
      'Grouped temple commands must indicate generic temple locations'
    );
    assert.ok(
      /not.*subtype/i.test(html),
      'Grouped temple commands must indicate not specific subtypes'
    );
    assert.ok(
      !/fully verified|global verified|100% verified|all verified/i.test(html),
      'Must have no global verified badge'
    );
  }

  // 5. No full verified claims across multiple features
  {
    const sampleFeatures = [
      'structure.ancient_city',
      'structure.mansion',
      'structure.monument',
      'structure.trial_chamber',
    ];
    for (const feature of sampleFeatures) {
      const summary = {
        revision: 'catalog-structure-evidence-summary-v1',
        feature_id: feature,
        predicted_count: 5,
        tested_count: 5,
        located_exact: 5,
        coordinate_difference: 0,
        no_location: 0,
        errors: 0,
        untested_count: 0,
        grouped_command: false,
        verifier_game_build_id: '1.26.52.3',
        generated_count: null,
        exhaustive_count: null,
      };
      const html = ReactDOMServer.renderToStaticMarkup(
        React.createElement(EvidenceSummary, { summary })
      );
      assert.ok(
        !/fully verified|global verified|100% verified|all verified/i.test(html),
        `Must have no global verified claims for ${feature}`
      );
      assert.ok(
        /not an exhaustive generated-building census/i.test(html),
        `Must include exhaustive census disclaimer for ${feature}`
      );
    }
  }

  console.log('All SSR render tests passed successfully.');
}

if (require.main === module) {
  runTests();
}

module.exports = { runTests };
