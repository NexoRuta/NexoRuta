import http from 'k6/http';
import { check, sleep } from 'k6';
import execution from 'k6/execution';
import { Counter, Gauge, Trend } from 'k6/metrics';

const fixture = JSON.parse(__ENV.NEXORUTA_LOAD_FIXTURE || '{}');
const profile = JSON.parse(__ENV.NEXORUTA_LOAD_PROFILE || '{}');
const setupTimeoutSeconds = Math.ceil(profile.vus * 22.1 + 40);
const scenarioDurationSeconds = profile.rate
  ? profile.stages.reduce((total, stage) => total + durationSeconds(stage.duration), 0)
  : durationSeconds(profile.ramp) + durationSeconds(profile.duration);
const operationsByJourney = profile.sync
  ? JSON.parse(open(__ENV.NEXORUTA_LOAD_OPERATIONS_FILE || ''))
  : {};
const unexpected = new Counter('nexoruta_load_unexpected_results');
const syncApplied = new Counter('nexoruta_load_sync_operations_applied');
const syncBatches = new Counter('nexoruta_load_sync_batches_completed');
const syncStarted = new Counter('nexoruta_load_sync_batches_started');
const windowStarted = new Gauge('nexoruta_load_window_started');
const windowFinished = new Gauge('nexoruta_load_window_finished');
const syncDrainDuration = new Trend('nexoruta_load_sync_drain_duration');
const generatorCpuUtilization = new Gauge('nexoruta_load_generator_cpu_utilization');
const generatorMemoryUtilization = new Gauge('nexoruta_load_generator_memory_utilization');

if (!fixture.accounts || !Array.isArray(fixture.accounts) || !fixture.accounts.length) {
  throw new Error('A private per-run NEXORUTA_LOAD_FIXTURE with synthetic accounts is required.');
}
if (!fixture.accounts.every((account) => typeof account.jornadaId === 'string'
    && /^[0-9a-f-]{36}$/i.test(account.jornadaId))) {
  throw new Error('Each synthetic account needs an isolated jornadaId.');
}
if (fixture.readPath !== '/api/mobile/perfil') {
  throw new Error('The load suite only permits the fixed mobile profile read route.');
}
if (fixture.accounts.length < profile.vus
    || new Set(fixture.accounts.map((account) => account.jornadaId)).size !== fixture.accounts.length) {
  throw new Error('Each active VU needs a distinct account and journey fixture.');
}
if (profile.sync && Object.keys(operationsByJourney).length !== fixture.accounts.length) {
  throw new Error('The pinned replay dataset must contain exactly one journey for each account.');
}
if (profile.sync && !fixture.accounts.every((account) => Array.isArray(operationsByJourney[account.jornadaId])
    && operationsByJourney[account.jornadaId].length === 50
    && operationsByJourney[account.jornadaId].every((operation, index) => operation?.tipo === 'Posicion'
      && /^[0-9a-f-]{36}$/.test(operation.id) && operation.ocurridaEn
      && operation.secuencia === index + 1 && operation.envioId === null
      && operation.versionEnvio === null))) {
  throw new Error('Each sync account needs 50 pre-seeded, ordered Posicion events for safe idempotent replay.');
}
if (profile.sync) {
  const ids = fixture.accounts.flatMap((account) => operationsByJourney[account.jornadaId].map((operation) => operation.id));
  if (new Set(ids).size !== ids.length) throw new Error('Operation IDs must be unique across synthetic journeys.');
}

const base = (__ENV.NEXORUTA_API_ORIGIN || '').replace(/\/$/, '');
if (!/^https:\/\/[a-z0-9.-]+$/.test(base)) throw new Error('A validated HTTPS API origin is required.');
const broker = __ENV.NEXORUTA_AUTH_BROKER_URL || '';
const brokerKey = __ENV.NEXORUTA_AUTH_BROKER_KEY || '';
if (!/^http:\/\/127\.0\.0\.1:[0-9]{1,5}$/.test(broker)
    || Number(broker.split(':').pop()) > 65535 || Number(broker.split(':').pop()) < 1
    || !/^[A-Za-z0-9_-]{32,64}$/.test(brokerKey)) {
  throw new Error('The private loopback session broker is required.');
}
let vuSession = null;

export const options = {
  maxRedirects: 0,
  // Login pacing and warm-up run before scenarios. Budget every identity at
  // the existing IP quota plus the bounded HTTP timeout.
  setupTimeout: `${setupTimeoutSeconds}s`,
  // Avoid per-journey URLs and detailed transport errors as Prometheus labels.
  systemTags: ['proto', 'status', 'method', 'name', 'group', 'check', 'error_code', 'tls_version', 'scenario', 'expected_response'],
  scenarios: {
    application: profile.rate
      ? { executor: 'ramping-arrival-rate', startRate: 1, timeUnit: '1s', preAllocatedVUs: 10,
          maxVUs: profile.vus, stages: profile.stages }
      : { executor: 'ramping-vus', startVUs: 1, stages: [
          { target: profile.vus, duration: profile.ramp }, { target: profile.vus, duration: profile.duration },
        ] },
    generator_monitor: { executor: 'constant-vus', vus: 1,
      duration: `${scenarioDurationSeconds}s`, exec: 'generatorTelemetry' },
  },
  thresholds: JSON.parse(__ENV.NEXORUTA_LOAD_THRESHOLDS || '{}'),
  tags: { run_id: __ENV.NEXORUTA_RUN_ID || 'local', profile: __ENV.NEXORUTA_LOAD_PROFILE_NAME || 'smoke' },
};

export function setup() {
  // The wrapper serializes login and renewal for all identities, including VUs
  // not yet active. No password or refresh token enters the k6 process.
  const preparationDeadline = Date.now() + (setupTimeoutSeconds - 40) * 1000;
  while (true) {
    const response = localGet('/ready', 'load_auth_ready', '15s');
    if (Date.now() >= preparationDeadline) execution.test.abort('Synthetic session preparation exceeded its budget.');
    if (response.status === 200) break;
    if (response.status !== 202) {
      execution.test.abort('Synthetic session preparation failed.');
    }
    sleep(1);
  }
  const sessions = fixture.accounts.slice(0, profile.vus).map((account, index) => ({
    jornadaId: account.jornadaId, index,
  }));
  // Warm only the permitted read route. Replay belongs exclusively to the
  // measured phase, where each VU must still send its first batch exactly once.
  const warmupDeadline = Date.now() + 30000;
  let accountIndex = 0;
  while (Date.now() < warmupDeadline) {
    const identity = sessions[accountIndex % sessions.length];
    const session = fetchSession(identity.index);
    const response = http.get(`${base}${fixture.readPath}`, {
      timeout: '10s', headers: { Authorization: `Bearer ${session.accessToken}` },
      tags: { phase: 'warmup', kind: 'read', name: 'mobile_profile' },
    });
    if (response.status !== 200) throw new Error(`Warm-up failed with HTTP ${response.status}.`);
    accountIndex += 1;
    sleep(1);
  }
  return { sessions };
}

export function generatorTelemetry() {
  const response = localGet('/generator', 'generator_metrics', '10s');
  if (response.status === 202) {
    sleep(1);
    return;
  }
  if (response.status !== 200) execution.test.abort('Generator resource telemetry is unavailable.');
  let sample;
  try { sample = response.json(); } catch (_) { execution.test.abort('Invalid generator resource telemetry.'); }
  if (!sample || !Number.isFinite(sample.cpu_utilization) || sample.cpu_utilization < 0
      || sample.cpu_utilization > 1.05 || !Number.isFinite(sample.memory_utilization)
      || sample.memory_utilization < 0 || sample.memory_utilization > 1) {
    execution.test.abort('Invalid generator resource telemetry.');
  }
  const tags = { phase: 'control', kind: 'generator', name: 'resource_usage' };
  generatorCpuUtilization.add(sample.cpu_utilization, tags);
  generatorMemoryUtilization.add(sample.memory_utilization, tags);
  sleep(5);
}

export function teardown() {
  windowFinished.add(Date.now(), { phase: 'control' });
}

export default function (data) {
  if (__ITER === 0) windowStarted.add(execution.scenario.startTime, { phase: 'control' });
  const identity = data.sessions[(__VU - 1) % data.sessions.length];
  const readTags = measurementTags();
  const read = http.get(`${base}${fixture.readPath}`, { timeout: '10s', headers: authorization(identity),
    tags: { ...readTags, kind: 'read', name: 'mobile_profile' } });
  unexpected.add(check(read, { 'profile response is 200': (r) => r.status === 200 }) ? 0 : 1,
    { ...readTags, kind: 'read' });

  if (profile.sync && __ITER === 0) {
    const batchTags = measurementTags();
    syncStarted.add(1, batchTags);
    const drainStarted = Date.now();
    let applied = 0;
    const operations = operationsByJourney[identity.jornadaId];
    for (let index = 0; index < operations.length; index += 1) {
      const operationTags = measurementTags();
      const response = http.post(`${base}/api/mobile/jornadas/${identity.jornadaId}/operaciones`,
        JSON.stringify(operations[index]), { timeout: '10s', headers: { ...authorization(identity), 'Content-Type': 'application/json',
          'X-NexoRuta-Pending-Sync': String(operations.length - index) },
        tags: { ...operationTags, kind: 'sync', name: 'mobile_sync_operation' } });
      let result = '';
      try { result = response.json().resultado || ''; } catch (_) { /* counted as unexpected below */ }
      const valid = response.status === 200 && result === 'Aplicada';
      if (!valid) {
        unexpected.add(1, { ...operationTags, kind: 'sync' });
        check(response, { 'operation replay accepted and applied': () => valid });
        break;
      }
      applied += 1;
      syncApplied.add(1, measurementTags());
      check(response, { 'operation replay accepted and applied': () => valid });
    }
    syncDrainDuration.add(Date.now() - drainStarted, batchTags);
    if (applied === operations.length) syncBatches.add(1, batchTags);
  }
  if (!profile.rate) sleep(1);
}

function localGet(path, name, timeout = '5s') {
  return http.get(broker + path, { timeout, redirects: 0,
    headers: { Authorization: `Bearer ${brokerKey}` },
    tags: { phase: 'control', kind: 'authentication', name } });
}

function fetchSession(index) {
  const response = localGet(`/sessions/${index}`, 'load_session');
  if (response.status !== 200) execution.test.abort('Synthetic session is unavailable.');
  let session;
  try { session = response.json(); } catch (_) { execution.test.abort('Invalid synthetic session response.'); }
  if (!session || typeof session !== 'object' || typeof session.accessToken !== 'string') {
    execution.test.abort('Invalid synthetic session response.');
  }
  const expiresAt = Date.parse(session.expiresAtUtc);
  if (!session.accessToken || !Number.isFinite(expiresAt) || expiresAt <= Date.now() + 30000) {
    execution.test.abort('Synthetic session has no usable access token.');
  }
  return { ...session, expiresAt, index };
}

function authorization(identity) {
  if (!vuSession || vuSession.index !== identity.index || vuSession.expiresAt <= Date.now() + 60000) {
    vuSession = fetchSession(identity.index);
  }
  return { Authorization: `Bearer ${vuSession.accessToken}` };
}

function measurementTags() {
  if (!profile.rate) return { phase: 'measured', stage: 'nominal' };
  const elapsed = Date.now() - execution.scenario.startTime;
  let boundary = 0;
  for (let index = 0; index < profile.stages.length; index += 1) {
    const duration = profile.stages[index].duration;
    boundary += Number.parseInt(duration, 10) * (duration.endsWith('m') ? 60000 : 1000);
    if (elapsed < boundary) return { phase: 'measured', stage: String(index + 1) };
  }
  return { phase: 'measured', stage: String(profile.stages.length) };
}

function durationSeconds(value) {
  const match = /^([1-9][0-9]*)([sm])$/.exec(value);
  if (!match) throw new Error('A bounded load duration is required.');
  return Number(match[1]) * (match[2] === 'm' ? 60 : 1);
}
