const fs = require('fs');
const path = require('path');
const vm = require('vm');
const assert = require('assert');

// 1. Resolve TypeScript and transpile actual network.ts (no mocking the implementation)
const tsPath = process.env.SEED_SEARCH_TYPESCRIPT_PATH || path.resolve(__dirname, '../web-ui/node_modules/typescript');
const ts = require(tsPath);

const sourceFilePath = path.resolve(__dirname, '../web-ui/src/utils/network.ts');
const sourceText = fs.readFileSync(sourceFilePath, 'utf-8');

const transpileResult = ts.transpileModule(sourceText, {
  compilerOptions: {
    module: ts.ModuleKind.CommonJS,
    target: ts.ScriptTarget.ES2022,
    esModuleInterop: true,
  },
});

const moduleExports = {};
const moduleObj = { exports: moduleExports };
const sandbox = {
  module: moduleObj,
  exports: moduleExports,
  require,
  console,
  setTimeout,
  clearTimeout,
  setInterval,
  clearInterval,
  AbortController: globalThis.AbortController,
  AbortSignal: globalThis.AbortSignal,
  Date,
  Math,
  Error,
  Promise,
  URL: globalThis.URL,
  URLSearchParams: globalThis.URLSearchParams,
  fetch: globalThis.fetch,
  Headers: globalThis.Headers,
  Request: globalThis.Request,
  Response: globalThis.Response,
};
sandbox.globalThis = sandbox;
vm.createContext(sandbox);
const script = new vm.Script(transpileResult.outputText);
script.runInContext(sandbox);

const network = moduleObj.exports;

// Helper to compare objects across VM realms
function assertDeepEqual(actual, expected, message) {
  assert.deepStrictEqual(JSON.parse(JSON.stringify(actual)), JSON.parse(JSON.stringify(expected)), message);
}

// Helper to create mock Response
function createMockResponse({ status = 200, statusText = 'OK', body = '', ok = status >= 200 && status < 300 }) {
  const textBody = typeof body === 'string' ? body : JSON.stringify(body);
  return {
    status,
    statusText,
    ok,
    text: async () => textBody,
    json: async () => JSON.parse(textBody),
  };
}

async function runTests() {
  console.log('Running test suite for network contracts...');

  // Test 1: Successful GET request
  {
    const fakeFetch = async (url, opts) => {
      assert.strictEqual(opts.method, 'GET');
      assert.strictEqual(opts.headers.Accept, 'application/json');
      return createMockResponse({
        status: 200,
        body: { status: 'idle', targetCount: 100000 },
      });
    };

    const result = await network.requestJson('/api/sweep/status', {
      fetchFn: fakeFetch,
      timeoutMs: 1000,
    });
    assert.strictEqual(result.ok, true);
    assert.strictEqual(result.status, 200);
    assertDeepEqual(result.data, { status: 'idle', targetCount: 100000 });
    assert(result.elapsedMs >= 0, 'elapsedMs should be non-negative');
    assert(result.timestamp > 0, 'timestamp should be positive');
    console.log('✓ Test 1: Successful GET request passed');
  }

  // Test 2: Successful POST request with body and headers
  {
    let receivedBody = null;
    let receivedHeaders = null;
    const fakeFetch = async (url, opts) => {
      assert.strictEqual(opts.method, 'POST');
      receivedHeaders = opts.headers;
      receivedBody = JSON.parse(opts.body);
      return createMockResponse({
        status: 200,
        body: { ok: true, runId: 'run-123' },
      });
    };

    const result = await network.requestJson('/api/sweep/start', {
      method: 'POST',
      body: { count: 50000 },
      fetchFn: fakeFetch,
      timeoutMs: 1000,
    });
    assert.strictEqual(result.ok, true);
    assert.strictEqual(result.data.runId, 'run-123');
    assert.strictEqual(receivedHeaders['Content-Type'], 'application/json');
    assertDeepEqual(receivedBody, { count: 50000 });
    console.log('✓ Test 2: Successful POST request passed');
  }

  // Test 3: Hung fetch times out with TimeoutError
  {
    const fakeFetch = (url, opts) => {
      return new Promise((resolve, reject) => {
        // Simulates a hung server connection; only rejects if aborted
        opts.signal.addEventListener('abort', () => {
          const err = new Error('The operation was aborted');
          err.name = 'AbortError';
          reject(err);
        });
      });
    };

    let caughtError = null;
    try {
      await network.requestJson('/api/sweep/status', {
        fetchFn: fakeFetch,
        timeoutMs: 50,
      });
    } catch (err) {
      caughtError = err;
    }

    assert(caughtError !== null, 'Should have thrown an error on hung fetch');
    assert(caughtError instanceof network.TimeoutError, `Expected TimeoutError but got ${caughtError?.name}`);
    assert.strictEqual(caughtError.timeoutMs, 50);
    console.log('✓ Test 3: Hung fetch timeout passed');
  }

  // Test 4: External AbortController cancellation
  {
    const parentController = new AbortController();
    const fakeFetch = (url, opts) => {
      return new Promise((resolve, reject) => {
        opts.signal.addEventListener('abort', () => {
          const err = new Error('The operation was aborted');
          err.name = 'AbortError';
          reject(err);
        });
      });
    };

    const promise = network.requestJson('/api/sweep/status', {
      fetchFn: fakeFetch,
      signal: parentController.signal,
      timeoutMs: 5000,
    });

    // Abort externally before timeout
    parentController.abort();

    let caughtError = null;
    try {
      await promise;
    } catch (err) {
      caughtError = err;
    }

    assert(caughtError !== null, 'Should have thrown on external abort');
    assert(caughtError instanceof network.AbortError, `Expected AbortError but got ${caughtError?.name}`);
    console.log('✓ Test 4: External signal abort passed');
  }

  // Test 5: Explicit HTTP error with status and payload
  {
    const fakeFetch = async (url, opts) => {
      return createMockResponse({
        status: 503,
        statusText: 'Service Unavailable',
        body: { error: 'Daemon sweep engine busy' },
        ok: false,
      });
    };

    let caughtError = null;
    try {
      await network.requestJson('/api/sweep/status', {
        fetchFn: fakeFetch,
        timeoutMs: 1000,
      });
    } catch (err) {
      caughtError = err;
    }

    assert(caughtError !== null, 'Should throw on HTTP 503');
    assert(caughtError instanceof network.HttpError, `Expected HttpError, got ${caughtError?.name}`);
    assert.strictEqual(caughtError.status, 503);
    assert.strictEqual(caughtError.statusText, 'Service Unavailable');
    assertDeepEqual(caughtError.responseBody, { error: 'Daemon sweep engine busy' });
    console.log('✓ Test 5: Explicit HTTP 503 error handling passed');
  }

  // Test 6: Malformed response (non-JSON on 200 OK)
  {
    const fakeFetch = async (url, opts) => {
      return createMockResponse({
        status: 200,
        statusText: 'OK',
        body: '<!DOCTYPE html><html><body>502 Bad Gateway</body></html>',
        ok: true,
      });
    };

    let caughtError = null;
    try {
      await network.requestJson('/api/sweep/status', {
        fetchFn: fakeFetch,
        timeoutMs: 1000,
      });
    } catch (err) {
      caughtError = err;
    }

    assert(caughtError !== null, 'Should throw on malformed JSON');
    assert(caughtError instanceof network.MalformedResponseError, `Expected MalformedResponseError, got ${caughtError?.name}`);
    assert(caughtError.rawText.includes('Bad Gateway'));
    console.log('✓ Test 6: Malformed response error handling passed');
  }

  // Test 7: Bounded polling backoff
  {
    const base = 1000;
    const max = 8000;
    assert.strictEqual(network.calculateBackoff(0, base, max), 1000);
    assert.strictEqual(network.calculateBackoff(1, base, max), 1500);
    assert.strictEqual(network.calculateBackoff(2, base, max), 2250);
    assert.strictEqual(network.calculateBackoff(3, base, max), 3375);
    // Large failure counts must be capped at max
    assert.strictEqual(network.calculateBackoff(10, base, max), 8000);
    assert.strictEqual(network.calculateBackoff(100, base, max), 8000);
    console.log('✓ Test 7: Bounded polling backoff passed');
  }

  // Test 8: Connection status determination & recovery
  {
    const now = 100000;
    // Initial connecting state
    assert.strictEqual(
      network.determineConnectionStatus({
        hasEverConnected: false,
        consecutiveFailures: 0,
        lastContactTimestamp: null,
        now,
      }),
      'connecting'
    );

    // Live state after recent successful contact
    assert.strictEqual(
      network.determineConnectionStatus({
        hasEverConnected: true,
        consecutiveFailures: 0,
        lastContactTimestamp: now - 1000,
        now,
      }),
      'live'
    );

    // Stale state: 1 intermittent failure
    assert.strictEqual(
      network.determineConnectionStatus({
        hasEverConnected: true,
        consecutiveFailures: 1,
        lastContactTimestamp: now - 2000,
        now,
      }),
      'stale'
    );

    // Stale state: elapsed exceeds stale threshold (5000ms)
    assert.strictEqual(
      network.determineConnectionStatus({
        hasEverConnected: true,
        consecutiveFailures: 0,
        lastContactTimestamp: now - 6000,
        now,
      }),
      'stale'
    );

    // Disconnected state: 3 consecutive failures
    assert.strictEqual(
      network.determineConnectionStatus({
        hasEverConnected: true,
        consecutiveFailures: 3,
        lastContactTimestamp: now - 3000,
        now,
      }),
      'disconnected'
    );

    // Disconnected state: elapsed exceeds disconnect threshold (12000ms)
    assert.strictEqual(
      network.determineConnectionStatus({
        hasEverConnected: true,
        consecutiveFailures: 0,
        lastContactTimestamp: now - 13000,
        now,
      }),
      'disconnected'
    );

    // Recovery on success
    assert.strictEqual(
      network.determineConnectionStatus({
        hasEverConnected: true,
        consecutiveFailures: 0,
        lastContactTimestamp: now,
        now,
      }),
      'live'
    );
    console.log('✓ Test 8: Connection status determination & recovery passed');
  }

  // Test 9: Generation & runId guard (stale response rejection)
  {
    // Stale generation
    assert.strictEqual(network.isResponseStale(1, 2, 'run-1', 'run-1'), true);
    // Current generation and matching run
    assert.strictEqual(network.isResponseStale(2, 2, 'run-1', 'run-1'), false);
    // Current generation but superseded runId
    assert.strictEqual(network.isResponseStale(2, 2, 'old-run', 'new-run'), true);
    console.log('✓ Test 9: Generation and runId stale response guards passed');
  }

  // Test 10: formatLastContact formatting helper
  {
    const now = 200000;
    assert.strictEqual(network.formatLastContact(null, now), 'No contact yet');
    assert.strictEqual(network.formatLastContact(now - 2000, now), 'just now');
    assert.strictEqual(network.formatLastContact(now - 15000, now), '15s ago');
    assert.strictEqual(network.formatLastContact(now - 90000, now), '1m 30s ago');
    console.log('✓ Test 10: Last contact timestamp formatting passed');
  }

  // Test 11: End-to-end simulated client failure and recovery cycle
  {
    let attempts = 0;
    const flakeyFetch = async (url, opts) => {
      attempts++;
      if (attempts === 1) {
        // Hang first attempt to test timeout
        return new Promise((resolve, reject) => {
          opts.signal.addEventListener('abort', () => {
            const err = new Error('Aborted');
            err.name = 'AbortError';
            reject(err);
          });
        });
      }
      if (attempts === 2) {
        // Return 500 on second attempt
        return createMockResponse({
          status: 500,
          statusText: 'Internal Server Error',
          body: { error: 'Kernel crash' },
          ok: false,
        });
      }
      // Recover on third attempt
      return createMockResponse({
        status: 200,
        body: { status: 'running', totalScanned: 12000 },
      });
    };

    let failures = 0;
    let lastContact = null;
    let dataMode = 'connecting';

    // Attempt 1: timeout
    try {
      await network.requestJson('/api/sweep/status', { fetchFn: flakeyFetch, timeoutMs: 40 });
    } catch (err) {
      assert(err instanceof network.TimeoutError);
      failures++;
      dataMode = network.determineConnectionStatus({
        hasEverConnected: false,
        consecutiveFailures: failures,
        lastContactTimestamp: lastContact,
      });
    }
    assert.strictEqual(dataMode, 'disconnected'); // 1 failure without ever connecting

    // Attempt 2: 500 HTTP error
    try {
      await network.requestJson('/api/sweep/status', { fetchFn: flakeyFetch, timeoutMs: 1000 });
    } catch (err) {
      assert(err instanceof network.HttpError);
      failures++;
      dataMode = network.determineConnectionStatus({
        hasEverConnected: false,
        consecutiveFailures: failures,
        lastContactTimestamp: lastContact,
      });
    }
    assert.strictEqual(failures, 2);

    // Attempt 3: Success and recovery
    const recoveryResult = await network.requestJson('/api/sweep/status', { fetchFn: flakeyFetch, timeoutMs: 1000 });
    assert.strictEqual(recoveryResult.ok, true);
    assert.strictEqual(recoveryResult.data.status, 'running');
    failures = 0;
    lastContact = Date.now();
    dataMode = network.determineConnectionStatus({
      hasEverConnected: true,
      consecutiveFailures: failures,
      lastContactTimestamp: lastContact,
    });
    assert.strictEqual(dataMode, 'live');
    console.log('✓ Test 11: End-to-end failure and recovery cycle passed');
  }

  // Test 12: Scoped syntax and semantic transpile check of all owned UI files
  {
    const filesToVerify = [
      '../web-ui/src/types.ts',
      '../web-ui/src/utils/network.ts',
      '../web-ui/src/components/TelemetryBar.tsx',
      '../web-ui/src/components/MapCanvas.tsx',
      '../web-ui/src/App.tsx',
    ];

    for (const rel of filesToVerify) {
      const fullPath = path.resolve(__dirname, rel);
      assert(fs.existsSync(fullPath), `File must exist: ${rel}`);
      const content = fs.readFileSync(fullPath, 'utf-8');
      const result = ts.transpileModule(content, {
        fileName: path.basename(fullPath),
        compilerOptions: {
          module: ts.ModuleKind.ESNext,
          target: ts.ScriptTarget.ES2022,
          jsx: ts.JsxEmit.ReactJSX,
        },
        reportDiagnostics: true,
      });

      assert(result.outputText && result.outputText.length > 0, `Output empty for ${rel}`);
      if (result.diagnostics && result.diagnostics.length > 0) {
        const errors = result.diagnostics.filter((d) => d.category === ts.DiagnosticCategory.Error);
        const msg = errors.map((d) => {
          const text = typeof d.messageText === 'string' ? d.messageText : d.messageText?.messageText;
          const pos = d.file && d.start ? d.file.getLineAndCharacterOfPosition(d.start) : null;
          return `${pos ? `Line ${pos.line + 1}:${pos.character + 1} ` : ''}${text}`;
        }).join('; ');
        assert.strictEqual(errors.length, 0, `Syntax/transpile errors in ${rel}: ${msg}`);
      }
    }
    console.log('✓ Test 12: Scoped syntax/transpile verification of all owned files passed');
  }

  // Deadline must cover transports and body readers that ignore AbortSignal.
  await assert.rejects(network.requestJson('/hung', {
    timeoutMs: 20, fetchFn: () => new Promise(() => {})
  }), error => error.name === 'TimeoutError');
  console.log('✓ Test 13: Uncooperative transport cannot defeat deadline');
  await assert.rejects(network.requestJson('/hung-body', {
    timeoutMs: 20, fetchFn: async () => ({ ok: true, status: 200, text: () => new Promise(() => {}) })
  }), error => error.name === 'TimeoutError');
  console.log('✓ Test 14: Deadline includes response body');
  await assert.rejects(network.requestJson('/empty', {
    fetchFn: async () => createMockResponse({ body: '' })
  }), error => error.name === 'MalformedResponseError');
  console.log('✓ Test 15: Empty JSON cannot become successful telemetry');
  assert.equal(network.validStatusPayload({}), false);
  assert.equal(network.validStatusPayload({ status: 'running' }), false);
  assert.equal(network.validStatusPayload({ status: 'running', totalScanned: NaN }), false);
  assert.equal(network.validStatusPayload({ status: 'idle', totalScanned: 0, seedsPerSec: 0,
    elapsedSeconds: 0, targetCount: 100, runId: null }), true);
  assert.equal(network.validCandidatePage({ candidates: [], total: -1 }), false);
  assert.equal(network.validCandidatePage({ candidates: [], total: 0, runId: null }), true);
  console.log('✓ Test 16: Semantic snapshot/page validation');
  assert.equal(network.snapshotMismatch({ runId: 'old', generation: 1 }, { runId: 'new', generation: 2 }), true);
  assert.equal(network.snapshotMismatch({ runId: 'a', generation: 1 }, { runId: 'a', generation: 2 }), true);
  assert.equal(network.snapshotMismatch({ runId: null }, { runId: 'a' }), true);
  assert.equal(network.snapshotMismatch({ runId: 'a' }, { runId: 'a' }), false);
  console.log('✓ Test 17: Server run/generation snapshot guards');
  await assert.rejects(network.requestJson('/unbounded', { timeoutMs: Infinity }), error => error.name === 'RangeError');
  console.log('✓ Test 18: Unbounded request controls rejected');
  const noFetch = async () => { throw new Error('Unexpected catalog lookup'); };
  const personalOnly = { count: 100, catalogEnabled: false };
  assert.equal(await network.resolvePublicCatalogRoot(personalOnly, { fetchFn: noFetch }), personalOnly);
  const explicit = { catalogEnabled: true, catalogRoot: '/chosen/catalog' };
  assert.equal(await network.resolvePublicCatalogRoot(explicit, { fetchFn: noFetch }), explicit);
  const before = { catalogEnabled: true, count: 100 };
  const current = await network.resolvePublicCatalogRoot(before, {fetchFn: async (url, options) => {
    assert.equal(url, '/api/catalog/automation-status'); assert.equal(options.method, 'GET');
    return createMockResponse({ body: { ok: true, configured: true, catalog_root: '/new/policy/catalog' } });
  }});
  assertDeepEqual(current, { ...before, catalogRoot: '/new/policy/catalog' });
  assert.equal(before.catalogRoot, undefined, 'Do not mutate saved personal controls');
  for (const body of [{ok:true,configured:false}, {ok:true,configured:true,catalog_root:'relative'}, {ok:false}]) {
    await assert.rejects(network.resolvePublicCatalogRoot(before,
      {fetchFn: async () => createMockResponse({body})}), /configured public catalog folder/);
  }
  const aborted=new AbortController();aborted.abort();
  await assert.rejects(network.resolvePublicCatalogRoot(before, {signal:aborted.signal,fetchFn:noFetch}));
  console.log('✓ Test 19: Active catalog destination, explicit overrides, personal isolation and abort');
  const appSource=fs.readFileSync(path.resolve(__dirname,'../web-ui/src/App.tsx'),'utf8');
  const appTree=ts.createSourceFile('App.tsx',appSource,ts.ScriptTarget.Latest,true,ts.ScriptKind.TSX);
  let commandArrow;
  const findCommand=node=>{
    if(ts.isVariableDeclaration(node)&&node.name.getText(appTree)==='postCommand')commandArrow=node.initializer.arguments[0];
    ts.forEachChild(node,findCommand);
  };
  findCommand(appTree);assert.ok(commandArrow,'Actual App command handler must exist');
  const commandCode=ts.transpileModule('exports.command='+commandArrow.getText(appTree),
    {compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022}}).outputText;
  const commandInFlight={current:false},apiGeneration={current:0};let posts=0,refreshes=0,posted;
  const commandContext={exports:{},commandInFlight,apiGeneration,TimeoutError:network.TimeoutError,
    requestJson:async(url,options)=>{posts++;posted=options.body;return{data:{ok:true}};},
    pollStatus:()=>{refreshes++;},setDataMode:()=>{},setTelemetry:()=>{}};
  vm.runInNewContext(commandCode,commandContext);const command=commandContext.exports.command;
  let release;const waiting=new Promise(resolve=>{release=resolve;});
  const first=command('/api/sweep/start',()=>waiting);
  assert.equal(commandInFlight.current,true);assert.equal(posts,0);
  await assert.rejects(command('/api/sweep/start',{}),/Another command is still pending/);
  release({catalogRoot:'/new/policy/catalog'});await first;
  assert.equal(posts,1);assertDeepEqual(posted,{catalogRoot:'/new/policy/catalog'});
  assert.equal(commandInFlight.current,false);
  const resolutionFailure=new network.TimeoutError(8000);
  await assert.rejects(command('/api/sweep/start',async()=>{throw resolutionFailure;}),e=>e===resolutionFailure);
  assert.equal(posts,1);assert.equal(refreshes,0);assert.equal(commandInFlight.current,false);
  console.log('✓ Test 20: Actual App handler serializes root resolution and sends no POST after lookup failure');
  console.log('\nAll 20 network contract and frontend contract tests passed successfully!');
}

runTests().catch((err) => {
  console.error('Test suite failed:', err);
  process.exit(1);
});
