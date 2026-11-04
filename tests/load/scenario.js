import http from 'k6/http';
import { check, sleep } from 'k6';
import { Counter, Trend } from 'k6/metrics';

const fixture = JSON.parse(__ENV.NEXORUTA_LOAD_FIXTURE || '{}');
const profile = JSON.parse(__ENV.NEXORUTA_LOAD_PROFILE || '{}');
const operationsByJourney = profile.sync
  ? JSON.parse(open(__ENV.NEXORUTA_LOAD_OPERATIONS_FILE || ''))
  : {};
const unexpected = new Counter('nexoruta_load_unexpected_results');
const syncApplied = new Counter('nexoruta_load_sync_operations_applied');
const syncBatches = new Counter('nexoruta_load_sync_batches_completed');
const syncDrainDuration = new Trend('nexoruta_load_sync_drain_duration');

if (!fixture.accounts || !Array.isArray(fixture.accounts) || !fixture.accounts.length) {
  throw new Error('A private per-run NEXORUTA_LOAD_FIXTURE with synthetic accounts is required.');
}
if (!fixture.accounts.every((account) => typeof account.email === 'string'
    && account.email.endsWith('@nexoruta.test') && account.password && account.jornadaId)) {
  throw new Error('Each synthetic account needs credentials and an isolated jornadaId.');
}
if (fixture.readPath !== '/api/mobile/perfil') {
  throw new Error('The load suite only permits the fixed mobile profile read route.');
}
if (fixture.accounts.length < profile.vus
    || new Set(fixture.accounts.map((account) => account.email)).size !== fixture.accounts.length
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

export const options = {
  // Avoid per-journey URLs and detailed transport errors as Prometheus labels.
  systemTags: ['proto', 'status', 'method', 'name', 'group', 'check', 'error_code', 'tls_version', 'scenario', 'expected_response'],
  scenarios: {
    application: profile.rate
      ? { executor: 'ramping-arrival-rate', startRate: 1, timeUnit: '1s', preAllocatedVUs: 10,
          maxVUs: profile.vus, stages: [
            { target: 1, duration: '4m' }, { target: 3, duration: '6m' },
            { target: 5, duration: '6m' }, { target: 10, duration: '9m' },
          ] }
      : { executor: 'ramping-vus', startVUs: 1, stages: [
          { target: profile.vus, duration: profile.ramp }, { target: profile.vus, duration: profile.duration },
        ] },
  },
  thresholds: JSON.parse(__ENV.NEXORUTA_LOAD_THRESHOLDS || '{}'),
  tags: { run_id: __ENV.NEXORUTA_RUN_ID || 'local', profile: __ENV.NEXORUTA_LOAD_PROFILE_NAME || 'smoke' },
};

export function setup() {
  // Existing login policy is five requests/minute per source IP. Pace logins
  // sequentially instead of creating a burst that only measures rate limiting.
  const sessions = fixture.accounts.slice(0, profile.vus).map((account) => {
    const response = http.post(`${base}/api/auth/mobile/login`, JSON.stringify({
      email: account.email, password: account.password,
    }), { headers: { 'Content-Type': 'application/json' }, tags: { kind: 'setup' } });
    if (response.status !== 200) throw new Error(`Synthetic account login failed with HTTP ${response.status}.`);
    const body = response.json();
    if (!body.accessToken) throw new Error('Login response did not contain an access token.');
    sleep(12.1);
    return { token: body.accessToken, jornadaId: account.jornadaId };
  });
  return { sessions };
}

export default function (data) {
  const identity = data.sessions[(__VU - 1) % data.sessions.length];
  const headers = { Authorization: `Bearer ${identity.token}` };
  const read = http.get(`${base}${fixture.readPath}`, { headers, tags: { kind: 'read', name: 'mobile_profile' } });
  if (!check(read, { 'profile response is 200': (r) => r.status === 200 })) unexpected.add(1, { kind: 'read' });

  if (profile.sync && __ITER === 0) {
    const drainStarted = Date.now();
    let applied = 0;
    const operations = operationsByJourney[identity.jornadaId];
    for (let index = 0; index < operations.length; index += 1) {
      const response = http.post(`${base}/api/mobile/jornadas/${identity.jornadaId}/operaciones`,
        JSON.stringify(operations[index]), { headers: { ...headers, 'Content-Type': 'application/json',
          'X-NexoRuta-Pending-Sync': String(operations.length - index) },
        tags: { kind: 'sync', name: 'mobile_sync_operation' } });
      let result = '';
      try { result = response.json().resultado || ''; } catch (_) { /* counted as unexpected below */ }
      const valid = response.status === 200 && result === 'Aplicada';
      if (!valid) {
        unexpected.add(1, { kind: 'sync', result: result || 'invalid_response' });
        check(response, { 'operation replay accepted and applied': () => valid });
        break;
      }
      applied += 1;
      syncApplied.add(1);
      check(response, { 'operation replay accepted and applied': () => valid });
    }
    syncDrainDuration.add(Date.now() - drainStarted);
    if (applied === operations.length) syncBatches.add(1);
  }
  sleep(1);
}
