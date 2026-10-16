// Load the actual TypeScript modules for UI handler and cross-language contract tests.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const root = path.resolve(__dirname, '..');
const ts = require(root + '/web-ui/node_modules/typescript');
const React = require(root + '/web-ui/node_modules/react');
const cache = new Map();
const hooks = { state: value => value };
function load(file) {
  if (cache.has(file)) return cache.get(file).exports;
  if (file.endsWith('.json')) return JSON.parse(fs.readFileSync(file, 'utf8'));
  const module = { exports: {} };
  cache.set(file, module);
  function requireLocal(name) {
    if (name === 'react') return { ...React,
      useState: value => [hooks.state(typeof value === 'function' ? value() : value), () => {}],
      useMemo: compute => compute(), useRef: value => ({ current: value }), useEffect: () => {} };
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
module.exports = { load, root, hooks };
