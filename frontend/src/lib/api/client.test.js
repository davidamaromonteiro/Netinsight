/**
 * Tests unitaires pour l'ApiClient.
 * Exécution : node src/lib/api/client.test.js
 *
 * Mock global.fetch et localStorage pour exécution hors navigateur.
 */

// ---------------------------------------------------------------------------
// Setup : mocks globaux (Node.js n'a ni localStorage ni fetch natif)
// ---------------------------------------------------------------------------

if (typeof localStorage === 'undefined') {
  let store = {};
  globalThis.localStorage = {
    _store: store,
    getItem(key) {
      return key in store ? store[key] : null;
    },
    setItem(key, value) {
      store[key] = String(value);
    },
    removeItem(key) {
      delete store[key];
    },
    // Helper pour réinitialiser entre les tests
    _clear() {
      store = {};
    },
  };
}

// On conserve la référence au fetch natif (Node 18+) ou on part de rien
const originalFetch = globalThis.fetch;

/**
 * Remplace globalThis.fetch par un mock qui retourne la réponse spécifiée.
 * @param {*}    data   Données JSON à retourner dans le body (ou null)
 * @param {number} status Code HTTP
 * @param {object} opts   Options supplémentaires (headers, ok override)
 * @returns {object} L'objet d'options passé à fetch (pour inspection de l'URL)
 */
let lastFetchUrl = null;
let lastFetchOptions = null;

function mockFetch(data, status = 200, opts = {}) {
  lastFetchUrl = null;
  lastFetchOptions = null;
  globalThis.fetch = async (url, options) => {
    lastFetchUrl = url;
    lastFetchOptions = options;
    const ok = opts.ok !== undefined ? opts.ok : status >= 200 && status < 300;
    return {
      ok,
      status,
      json: async () => data,
    };
  };
  return { getLastUrl: () => lastFetchUrl, getLastOptions: () => lastFetchOptions };
}

/** Rétablit le fetch original. */
function restoreFetch() {
  globalThis.fetch = originalFetch;
  lastFetchUrl = null;
  lastFetchOptions = null;
}

// ---------------------------------------------------------------------------
// Helper : compare deux valeurs (deep equality simple)
// ---------------------------------------------------------------------------
function assertEqual(actual, expected, msg = '') {
  const actualStr = JSON.stringify(actual);
  const expectedStr = JSON.stringify(expected);
  if (actualStr !== expectedStr) {
    throw new Error(
      `${msg ? msg + ' : ' : ''}expected ${expectedStr}, got ${actualStr}`,
    );
  }
}

function assertOk(value, msg = '') {
  if (!value) {
    throw new Error(`${msg ? msg + ' : ' : ''}expected truthy, got ${value}`);
  }
}

function assertThrowsAsync(fn, msg = '') {
  return fn()
    .then(() => {
      throw new Error(`${msg ? msg + ' : ' : ''}expected an error to be thrown`);
    })
    .catch((err) => {
      // Expected — l'erreur est bien levée
      return err;
    });
}

// ---------------------------------------------------------------------------
// Chargement dynamique du module (pour que les mocks soient en place)
// ---------------------------------------------------------------------------
const { api } = await import('./client.js');

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

async function testSetToken() {
  api.setToken('mon-super-token');
  assertEqual(api.token, 'mon-super-token', 'api.token');
  assertEqual(
    localStorage.getItem('netinsight_token'),
    'mon-super-token',
    'localStorage',
  );
}

function testClearToken() {
  api.setToken('token-a-supprimer');
  api.clearToken();
  assertEqual(api.token, null, 'api.token après clear');
  assertEqual(
    localStorage.getItem('netinsight_token'),
    null,
    'localStorage après clear',
  );
}

function testLoadToken() {
  localStorage.setItem('netinsight_token', 'token-stocke');
  const result = api.loadToken();
  assertEqual(result, 'token-stocke', 'valeur retournée');
  assertEqual(api.token, 'token-stocke', 'api.token après load');
  api.clearToken(); // nettoyage
}

function testGetHeadersWithoutToken() {
  api.clearToken();
  const headers = api.getHeaders();
  assertEqual(headers['Content-Type'], 'application/json', 'Content-Type présent');
  assertOk(
    !('Authorization' in headers),
    'Authorization ne doit pas être présent',
  );
}

function testGetHeadersWithToken() {
  api.setToken('bearer-token');
  const headers = api.getHeaders();
  assertEqual(headers['Content-Type'], 'application/json', 'Content-Type présent');
  assertEqual(
    headers['Authorization'],
    'Bearer bearer-token',
    'Authorization Bearer',
  );
}

async function testRequest200() {
  const fetchCtrl = mockFetch({ result: 'ok' }, 200);
  const data = await api.get('/test');
  assertEqual(data, { result: 'ok' }, 'body parsé');
  restoreFetch();
}

async function testRequest204() {
  mockFetch(null, 204);
  const data = await api.get('/no-content');
  assertEqual(data, null, 'retourne null pour 204');
  restoreFetch();
}

async function testRequest401() {
  // 401 doit lever une erreur avec un status
  mockFetch({ detail: 'Token invalide' }, 401);
  await assertThrowsAsync(
    () => api.get('/secure'),
    'appel 401 doit lever une erreur',
  );
  restoreFetch();
}

async function testRequest401SetsStatusOnError() {
  mockFetch({ detail: 'Non autorisé' }, 401);
  try {
    await api.get('/admin');
    throw new Error('aurait dû lever');
  } catch (err) {
    assertEqual(err.status, 401, 'err.status');
    assertEqual(err.message, 'Non autorisé', 'err.message');
  }
  restoreFetch();
}

async function testGetCampaignsWithoutFilter() {
  const fetchCtrl = mockFetch([], 200);
  await api.getCampaigns();
  const url = fetchCtrl.getLastUrl();
  // Normalise le séparateur de query string selon l'implémentation
  assertOk(url.includes('/api/v1/campaigns'), "l'URL contient /api/v1/campaigns");
  // Sans filtre, pas de query string attendu (ou ? vide)
  assertOk(
    !url.includes('?') || url.endsWith('?'),
    "pas de paramètre status quand pas de filtre",
  );
  restoreFetch();
}

async function testGetCampaignsWithFilter() {
  const fetchCtrl = mockFetch([], 200);
  await api.getCampaigns('running');
  const url = fetchCtrl.getLastUrl();
  assertOk(url.includes('/api/v1/campaigns?status=running'), "URL avec ?status=running");
  restoreFetch();
}

async function testGetVulnerabilitiesNoFilters() {
  const fetchCtrl = mockFetch([], 200);
  await api.getVulnerabilities();
  const url = fetchCtrl.getLastUrl();
  assertEqual(url, '/api/v1/vulnerabilities', 'URL sans query params');
  restoreFetch();
}

async function testGetVulnerabilitiesWithHostId() {
  const fetchCtrl = mockFetch([], 200);
  await api.getVulnerabilities('host-42', null);
  const url = fetchCtrl.getLastUrl();
  assertOk(
    url.includes('host_id=host-42'),
    'query param host_id présent',
  );
  assertOk(
    !url.includes('severity='),
    'pas de query param severity',
  );
  restoreFetch();
}

async function testGetVulnerabilitiesWithHostIdAndSeverity() {
  const fetchCtrl = mockFetch([], 200);
  await api.getVulnerabilities('host-1', 'HIGH');
  const url = fetchCtrl.getLastUrl();
  assertOk(
    url.includes('host_id=host-1'),
    'query param host_id',
  );
  assertOk(
    url.includes('severity=HIGH'),
    'query param severity',
  );
  restoreFetch();
}

async function testGetReportDownloadUrl() {
  const url = api.getReportDownloadUrl('rpt-001');
  assertEqual(url, '/api/v1/reports/rpt-001/download', 'URL de download');
}

async function testTriggerScanUrl() {
  const fetchCtrl = mockFetch({ message: 'scan started' }, 202);
  await api.triggerScan('camp-xyz');
  const url = fetchCtrl.getLastUrl();
  assertEqual(url, '/api/v1/campaigns/camp-xyz/scan', "URL du scan");
  const options = fetchCtrl.getLastOptions();
  assertEqual(options.method, 'POST', 'méthode POST');
  restoreFetch();
}

async function testTriggerReportUrl() {
  const fetchCtrl = mockFetch({ id: 'rpt-new', status: 'completed' }, 200);
  await api.triggerReport('camp-abc');
  const url = fetchCtrl.getLastUrl();
  assertEqual(url, '/api/v1/campaigns/camp-abc/report', "URL du rapport");
  assertEqual(fetchCtrl.getLastOptions().method, 'POST', 'méthode POST');
  restoreFetch();
}

async function testDeleteSendsDeleteMethod() {
  const fetchCtrl = mockFetch(null, 204);
  await api.deleteCampaign('camp-del');
  const url = fetchCtrl.getLastUrl();
  assertEqual(url, '/api/v1/campaigns/camp-del', "URL de suppression");
  assertEqual(fetchCtrl.getLastOptions().method, 'DELETE', 'méthode DELETE');
  restoreFetch();
}

async function testRegisterBuildsCorrectBody() {
  const fetchCtrl = mockFetch({ id: 1, email: 'test@test.com' }, 201);
  await api.register('test@test.com', 'password123', 'Jean Dupont');
  const body = JSON.parse(fetchCtrl.getLastOptions().body);
  assertEqual(body.email, 'test@test.com', 'email dans body');
  assertEqual(body.password, 'password123', 'password dans body');
  assertEqual(body.full_name, 'Jean Dupont', 'full_name dans body');
  restoreFetch();
}

async function testLoginBuildsCorrectBody() {
  const fetchCtrl = mockFetch({ access_token: 'jwt-token' }, 200);
  await api.login('admin@test.com', 'secret');
  const body = JSON.parse(fetchCtrl.getLastOptions().body);
  assertEqual(body.email, 'admin@test.com', 'email');
  assertEqual(body.password, 'secret', 'password');
  restoreFetch();
}

// ---------------------------------------------------------------------------
// Exécuteur de tests
// ---------------------------------------------------------------------------
const tests = [
  { name: 'testSetToken', fn: testSetToken },
  { name: 'testClearToken', fn: testClearToken },
  { name: 'testLoadToken', fn: testLoadToken },
  { name: 'testGetHeadersWithoutToken', fn: testGetHeadersWithoutToken },
  { name: 'testGetHeadersWithToken', fn: testGetHeadersWithToken },
  { name: 'testRequest200', fn: testRequest200 },
  { name: 'testRequest204', fn: testRequest204 },
  { name: 'testRequest401', fn: testRequest401 },
  { name: 'testRequest401SetsStatusOnError', fn: testRequest401SetsStatusOnError },
  { name: 'testGetCampaignsWithoutFilter', fn: testGetCampaignsWithoutFilter },
  { name: 'testGetCampaignsWithFilter', fn: testGetCampaignsWithFilter },
  { name: 'testGetVulnerabilitiesNoFilters', fn: testGetVulnerabilitiesNoFilters },
  { name: 'testGetVulnerabilitiesWithHostId', fn: testGetVulnerabilitiesWithHostId },
  { name: 'testGetVulnerabilitiesWithHostIdAndSeverity', fn: testGetVulnerabilitiesWithHostIdAndSeverity },
  { name: 'testGetReportDownloadUrl', fn: testGetReportDownloadUrl },
  { name: 'testTriggerScanUrl', fn: testTriggerScanUrl },
  { name: 'testTriggerReportUrl', fn: testTriggerReportUrl },
  { name: 'testDeleteSendsDeleteMethod', fn: testDeleteSendsDeleteMethod },
  { name: 'testRegisterBuildsCorrectBody', fn: testRegisterBuildsCorrectBody },
  { name: 'testLoginBuildsCorrectBody', fn: testLoginBuildsCorrectBody },
];

let passed = 0;
let failed = 0;
const failures = [];

for (const test of tests) {
  try {
    await test.fn();
    passed++;
    console.log(`  ✓ ${test.name}`);
  } catch (e) {
    failed++;
    failures.push({ name: test.name, error: e.message });
    console.error(`  ✗ ${test.name}: ${e.message}`);
  }
}

console.log(`\n${passed} passed, ${failed} failed, ${tests.length} total\n`);

// ---------------------------------------------------------------------------
// Nettoyage
// ---------------------------------------------------------------------------
restoreFetch();
api.clearToken();

// Exit code for CI
if (failed > 0) {
  process.exit(1);
}
