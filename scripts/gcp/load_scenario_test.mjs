import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';
import { test } from 'node:test';

const source = fs.readFileSync(new URL('../../tests/load/scenario.js', import.meta.url), 'utf8');
const profiles = JSON.parse(fs.readFileSync(new URL('../../tests/load/profiles.json', import.meta.url)));

async function harness({ count = 1, sync = false, warmupStatus = 200 } = {}) {
  const accounts = Array.from({ length: count }, (_, index) => ({
    email: `load-${index}@nexoruta.test`, password: 'controlled-fixture',
    jornadaId: `00000000-0000-4000-8000-${String(index + 1).padStart(12, '0')}`,
  }));
  const operations = Object.fromEntries(accounts.map(account => [account.jornadaId,
    Array.from({ length: 50 }, (_, index) => ({
      id: `10000000-0000-4000-8000-${String(index + 1).padStart(12, '0')}`,
      tipo: 'Posicion', secuencia: index + 1, ocurridaEn: '2026-11-04T00:00:00Z',
      envioId: null, versionEnvio: null,
    })),
  ]));
  const requests = [];
  let clock = 0;
  const context = vm.createContext({
    Date: { now: () => clock }, __VU: 1, __ITER: 0,
    open: () => JSON.stringify(operations),
    __ENV: { NEXORUTA_API_ORIGIN: 'https://controlled.invalid',
      NEXORUTA_LOAD_FIXTURE: JSON.stringify({ accounts, readPath: '/api/mobile/perfil' }),
      NEXORUTA_LOAD_PROFILE: JSON.stringify({ vus: count, sync, duration: '2m', ramp: '10s' }),
      NEXORUTA_LOAD_THRESHOLDS: JSON.stringify(profiles.thresholds) },
  });
  const response = (status, body) => ({ status, json: () => body });
  const http = {
    post(url, body, options) {
      requests.push({ url, body, ...options });
      return response(200, options.tags.kind === 'setup' ? { accessToken: 'synthetic-token' } : { resultado: 'Aplicada' });
    },
    get(url, options) {
      requests.push({ url, ...options });
      return response(options.tags.phase === 'warmup' ? warmupStatus : 200, {});
    },
  };
  function module(exports) {
    return new vm.SyntheticModule(Object.keys(exports), function () {
      for (const [name, value] of Object.entries(exports)) this.setExport(name, value);
    }, { context });
  }
  class Metric { add() {} }
  const dependencies = {
    'k6/http': module({ default: http }),
    k6: module({ sleep: seconds => { clock += seconds * 1000; },
      check: (value, checks) => Object.values(checks).every(check => check(value)) }),
    'k6/metrics': module({ Counter: Metric, Trend: Metric }),
  };
  const scenario = new vm.SourceTextModule(source, { context });
  await scenario.link(name => dependencies[name]);
  await scenario.evaluate();
  return { scenario: scenario.namespace, requests, elapsed: () => clock };
}

test('login and warm-up precede measured traffic and never replay sync', async () => {
  const h = await harness({ sync: true });
  const data = h.scenario.setup();
  assert.equal(h.requests.filter(r => r.tags.phase === 'setup').length, 1);
  assert.equal(h.requests.filter(r => r.tags.phase === 'warmup').length, 30);
  assert(h.requests.every(r => r.tags.kind !== 'sync'));
  assert(h.elapsed() >= 42100);
  h.scenario.default(data);
  assert.equal(h.requests.filter(r => r.tags.phase === 'measured' && r.tags.kind === 'sync').length, 50);
  assert.equal(h.requests.filter(r => r.tags.phase === 'measured' && r.tags.kind === 'read').length, 1);
});

test('failed warm-up aborts setup before measured scenarios can start', async () => {
  const h = await harness({ warmupStatus: 503 });
  assert.throws(() => h.scenario.setup(), /Warm-up failed with HTTP 503/);
  assert(h.requests.every(r => r.tags.phase !== 'measured'));
});

test('fifty paced logins fit the explicit setup timeout', async () => {
  const h = await harness({ count: 50 });
  h.scenario.setup();
  assert.equal(h.requests.filter(r => r.tags.kind === 'setup').length, 50);
  assert(h.elapsed() >= 635000);
  assert(Number.parseInt(h.scenario.options.setupTimeout, 10) * 1000 > h.elapsed());
});

test('HTTP SLO thresholds select measured samples exclusively', async () => {
  const h = await harness();
  const keys = Object.keys(h.scenario.options.thresholds).filter(key => key.startsWith('http_req_'));
  assert(keys.length >= 3);
  assert(keys.every(key => key.includes('phase:measured')));
});
