import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';
import { test } from 'node:test';

const source = fs.readFileSync(new URL('../../tests/load/scenario.js', import.meta.url), 'utf8');
const profiles = JSON.parse(fs.readFileSync(new URL('../../tests/load/profiles.json', import.meta.url)));

async function harness({ count = 1, sync = false, warmupStatus = 200, rateProfile = false,
  readyPolls = 0, brokerStatus = 200, generatorReadyPolls = 0 } = {}) {
  const accounts = Array.from({ length: count }, (_, index) => ({
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
  const metrics = [];
  const execution = { scenario: { startTime: 0 }, test: { abort: message => { throw new Error(message); } } };
  let clock = 0;
  const context = vm.createContext({
    Date: { now: () => clock, parse: Date.parse }, __VU: 1, __ITER: 0,
    open: () => JSON.stringify(operations),
    __ENV: { NEXORUTA_API_ORIGIN: 'https://controlled.invalid',
      NEXORUTA_AUTH_BROKER_URL: 'http://127.0.0.1:12345', NEXORUTA_AUTH_BROKER_KEY: 'K'.repeat(43),
      NEXORUTA_LOAD_FIXTURE: JSON.stringify({ accounts, readPath: '/api/mobile/perfil' }),
      NEXORUTA_LOAD_PROFILE: JSON.stringify(rateProfile
        ? { ...profiles.profiles.stress, sync, vus: count }
        : { vus: count, sync, duration: '2m', ramp: '10s' }),
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
      if (url.endsWith('/generator')) return response(generatorReadyPolls-- > 0 ? 202 : 200,
        { cpu_utilization: 0.4, memory_utilization: 0.5 });
      if (url.endsWith('/ready')) return response(readyPolls-- > 0 ? 202 : brokerStatus, {});
      if (url.includes('/sessions/')) return response(brokerStatus,
        { accessToken: `synthetic-token-${clock}`, expiresAtUtc: new Date(clock + 900000).toISOString() });
      return response(options.tags.phase === 'warmup' ? warmupStatus : 200, {});
    },
  };
  function module(exports) {
    return new vm.SyntheticModule(Object.keys(exports), function () {
      for (const [name, value] of Object.entries(exports)) this.setExport(name, value);
    }, { context });
  }
  class Metric {
    constructor(name) { this.name = name; }
    add(value, tags) { metrics.push({ name: this.name, value, tags }); }
  }
  const dependencies = {
    'k6/http': module({ default: http }),
    k6: module({ sleep: seconds => { clock += seconds * 1000; },
      check: (value, checks) => Object.values(checks).every(check => check(value)) }),
    'k6/metrics': module({ Counter: Metric, Gauge: Metric, Trend: Metric }),
    'k6/execution': module({ default: execution }),
  };
  const scenario = new vm.SourceTextModule(source, { context });
  await scenario.link(name => dependencies[name]);
  await scenario.evaluate();
  return { scenario: scenario.namespace, requests, metrics, execution,
    elapsed: () => clock, advance: milliseconds => { clock += milliseconds; } };
}

test('private session readiness and warm-up precede measured traffic and never replay sync', async () => {
  const h = await harness({ sync: true });
  const data = h.scenario.setup();
  assert.equal(h.requests.filter(r => r.tags.name === 'load_auth_ready').length, 1);
  assert.equal(h.requests.filter(r => r.tags.phase === 'warmup').length, 30);
  assert(h.requests.every(r => r.tags.kind !== 'sync'));
  assert(h.elapsed() >= 30000);
  assert(h.requests.every(r => !r.url.includes('/api/auth/mobile/')));
  assert(data.sessions.every(s => !s.token && !s.accessToken && !s.refreshToken));
  h.execution.scenario.startTime = h.elapsed();
  h.scenario.default(data);
  assert.equal(h.requests.filter(r => r.tags.phase === 'measured' && r.tags.kind === 'sync').length, 50);
  assert.equal(h.requests.filter(r => r.tags.phase === 'measured' && r.tags.kind === 'read').length, 1);
});

test('stress labels stages from the actual scenario clock and does not add think-time', async () => {
  const h = await harness({ count: 50, rateProfile: true });
  const data = h.scenario.setup();
  h.execution.scenario.startTime = h.elapsed();
  h.advance(239999);
  h.scenario.default(data);
  h.advance(1);
  h.scenario.default(data);
  h.advance(360000);
  h.scenario.default(data);
  h.advance(360000);
  h.scenario.default(data);
  assert.deepEqual(h.requests.filter(r => r.tags.phase === 'measured').map(r => r.tags.stage), ['1', '2', '3', '4']);
  assert.equal(h.elapsed() - h.execution.scenario.startTime, 960000);
  assert(h.metrics.filter(m => m.name === 'nexoruta_load_window_started')
    .every(m => m.value === h.execution.scenario.startTime));
  h.scenario.teardown();
  assert.deepEqual(JSON.parse(JSON.stringify(h.metrics.filter(m => m.name === 'nexoruta_load_window_finished')
    .map(m => m.tags))), [{ phase: 'control' }]);
  assert.deepEqual(JSON.parse(JSON.stringify(h.scenario.options.scenarios.application.stages)), profiles.profiles.stress.stages);
});

test('failed warm-up aborts setup before measured scenarios can start', async () => {
  const h = await harness({ warmupStatus: 503 });
  assert.throws(() => h.scenario.setup(), /Warm-up failed with HTTP 503/);
  assert(h.requests.every(r => r.tags.phase !== 'measured'));
});

test('setup waits for the wrapper and retains a bounded authentication budget', async () => {
  const h = await harness({ count: 50, readyPolls: 2 });
  h.scenario.setup();
  assert.equal(h.requests.filter(r => r.tags.name === 'load_auth_ready').length, 3);
  assert(h.elapsed() >= 32000);
  assert(Number.parseInt(h.scenario.options.setupTimeout, 10) > 50 * 12.1 + 30);
});

test('setup deadline survives k6 canonicalizing a seconds timeout into minutes', async () => {
  const h = await harness();
  h.scenario.options.setupTimeout = '1m3s';
  h.scenario.setup();
  assert.equal(h.requests.filter(r => r.tags.phase === 'warmup').length, 30);
  assert(h.elapsed() >= 30000);
});

test('generator telemetry retries startup and exports bounded control gauges', async () => {
  const h = await harness({ generatorReadyPolls: 1 });
  h.scenario.generatorTelemetry();
  assert.equal(h.requests.filter(r => r.url.endsWith('/generator')).length, 1);
  assert.equal(h.metrics.length, 0);
  h.scenario.generatorTelemetry();
  assert.deepEqual(JSON.parse(JSON.stringify(h.metrics.map(metric => [metric.name, metric.value, metric.tags]))), [
    ['nexoruta_load_generator_cpu_utilization', 0.4,
      { phase: 'control', kind: 'generator', name: 'resource_usage' }],
    ['nexoruta_load_generator_memory_utilization', 0.5,
      { phase: 'control', kind: 'generator', name: 'resource_usage' }],
  ]);
  assert.equal(h.elapsed(), 6000);
});

test('generator monitor duration follows both nominal and staged stress traffic', async () => {
  const nominal = await harness();
  assert.equal(nominal.scenario.options.scenarios.generator_monitor.duration, '130s');
  const stress = await harness({ rateProfile: true });
  const expected = profiles.profiles.stress.stages
    .reduce((total, stage) => total + Number.parseInt(stage.duration, 10) * 60, 0);
  assert.equal(stress.scenario.options.scenarios.generator_monitor.duration, `${expected}s`);
});

test('a VU fetches renewed access tokens without using a refresh token', async () => {
  const h = await harness();
  const data = h.scenario.setup();
  h.scenario.default(data);
  const firstToken = h.requests.filter(r => r.tags.phase === 'measured').at(-1).headers.Authorization;
  h.advance(15 * 60 * 1000);
  h.scenario.default(data);
  const secondToken = h.requests.filter(r => r.tags.phase === 'measured').at(-1).headers.Authorization;
  assert.notEqual(firstToken, secondToken);
  assert(h.requests.every(r => !r.url.includes('/api/auth/mobile/refresh')));
});

test('an unavailable authentication broker stops the test before business traffic', async () => {
  const h = await harness({ brokerStatus: 503 });
  assert.throws(() => h.scenario.setup(), /Synthetic session preparation failed/);
  assert(h.requests.every(r => r.tags.phase !== 'measured'));
});

test('an indefinitely pending broker cannot consume the measured or export budget', async () => {
  const h = await harness({ readyPolls: 1000 });
  assert.throws(() => h.scenario.setup(), /preparation exceeded its budget/);
  assert(h.elapsed() < Number.parseInt(h.scenario.options.setupTimeout, 10) * 1000);
  assert(h.requests.every(r => r.tags.phase === 'control'));
});

test('HTTP SLO thresholds select measured samples exclusively', async () => {
  const h = await harness();
  const keys = Object.keys(h.scenario.options.thresholds).filter(key => key.startsWith('http_req_'));
  assert(keys.length >= 3);
  assert(keys.every(key => key.includes('phase:measured')));
});
