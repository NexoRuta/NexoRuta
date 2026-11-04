// Local workshop only. Uses existing application login, never provider credentials.
const assert = require('node:assert/strict');
const fs = require('node:fs/promises');
const path = require('node:path');
const { chromium, request } = require(process.env.NEXORUTA_PLAYWRIGHT_MODULE);

(async () => {
    // This historical runner exercises disabled-search errors. Never let it consume a real temporary search.
    const env = JSON.parse(require('node:child_process').execFileSync('docker', ['inspect', '--format', '{{json .Config.Env}}', 'nexoruta-api'], { encoding: 'utf8' }));
    assert.ok(!env.some(v => /^Geocoding__MapboxTemporal__Habilitado=true$/i.test(v)),
        'Mapbox temporary search is enabled: use the controlled browser/full-stack tests, not this disabled-provider runner.');
    const base = 'http://127.0.0.1:5102/';
    const out = path.resolve('docs/auditorias/geocodificacion/evidencias/local');
    await fs.mkdir(out, { recursive: true });
    const settings = {};
    for (const line of (await fs.readFile('.env', 'utf8')).split(/\r?\n/)) {
        const match = line.match(/^(NEXORUTA_COMERCIO_(?:MAIL|PASSWORD))=(.*)$/);
        if (match) settings[match[1]] = match[2].trim().replace(/^(['"])(.*)\1$/, '$2');
    }
    assert.ok(settings.NEXORUTA_COMERCIO_MAIL && settings.NEXORUTA_COMERCIO_PASSWORD, 'Existing local Commerce login is required');
    const api = await request.newContext({ baseURL: 'http://127.0.0.1:5000/' });
    const login = await api.post('api/auth/login', { data: { email: settings.NEXORUTA_COMERCIO_MAIL, password: settings.NEXORUTA_COMERCIO_PASSWORD } });
    assert.equal(login.status(), 200, 'Local application login failed');
    const token = (await login.json()).accessToken;
    assert.ok(token, 'Local login did not return an application session');
    const headers = { Authorization: 'Bearer ' + token };
    const operators = await api.get('api/operadores', { headers });
    assert.equal(operators.status(), 200);
    const operator = (await operators.json())[0];
    const created = await api.post('api/envios', { headers, data: {
        operadorId: operator.operadorId, destinatarioNombre: 'Geocoding local synthetic check',
        destinatarioEmail: 'geocoding-local@example.test', direccion: 'Geocoding local synthetic 123',
        codigoBulto: 'GEO-LOCAL-' + Date.now(), pesoGramos: 100,
        largoCentimetros: 10, anchoCentimetros: 10, altoCentimetros: 10
    } });
    assert.equal(created.status(), 201, 'Local synthetic shipment creation failed');
    const id = (await created.json()).id;
    const route = `api/envios/${id}/destino`;
    assert.equal((await api.post(route + '/busqueda', { data: { consulta: 'Disabled' } })).status(), 401);
    assert.equal((await api.post(route + '/busqueda', { headers, data: { consulta: 'ab' } })).status(), 400);
    const browser = await chromium.launch({ headless: true });
    const page = await browser.newPage({ viewport: { width: 1440, height: 1000 } });
    const external = [], errors = [];
    page.on('pageerror', error => errors.push(error.message));
    await page.route('**/*', route => {
        if (new URL(route.request().url()).origin !== new URL(base).origin) {
            external.push(new URL(route.request().url()).hostname); return route.abort();
        }
        return route.continue();
    });
    await page.addInitScript(() => {
        globalThis.__geoPoint = { lat: -34.91, lng: -56.21 };
        class Map {
            constructor(options) {
                this.handlers = {};
                const button = document.createElement('button'); button.type = 'button';
                button.textContent = 'Mapa simulado: seleccionar punto';
                button.onclick = () => this.handlers.click?.({ lngLat: globalThis.__geoPoint });
                options.container.append(button);
            }
            on(name, callback) { this.handlers[name] = callback; }
            once(name, callback) { if (name === 'load') setTimeout(callback, 0); }
            addControl() {} resize() {} remove() {} jumpTo() {}
        }
        class Marker { setLngLat() { return this; } addTo() { return this; } on() {} setDraggable() {} remove() {} }
        globalThis.mapboxgl = { Map, Marker, NavigationControl: class {} };
    });
    try {
        await page.goto(base + 'ingresar');
        await page.locator('#Email').fill(settings.NEXORUTA_COMERCIO_MAIL);
        await page.locator('#Password').fill(settings.NEXORUTA_COMERCIO_PASSWORD);
        await Promise.all([page.waitForNavigation(), page.getByRole('button', { name: 'Ingresar', exact: true }).click()]);
        await page.goto(base + `envios/${id}/destino`);
        const manual = page.getByRole('button', { name: 'Mapa simulado: seleccionar punto' });
        await manual.waitFor();
        await page.getByRole('combobox', { name: 'Buscar dirección' }).fill('External disabled');
        await page.getByRole('alert').filter({ hasText: 'no está habilitada' }).waitFor();
        await page.screenshot({ path: path.join(out, 'disabled-1440.png'), fullPage: true });
        for (const version of [1, 2]) {
            await page.evaluate(version => { globalThis.__geoPoint = { lat: -34.90 - version * .01, lng: -56.20 - version * .01 }; }, version);
            await manual.click(); await page.locator('#destino-revisado').check();
            await page.getByRole('button', { name: version === 1 ? 'Confirmar ubicación' : 'Confirmar nueva ubicación', exact: true }).click();
            await page.getByText('Ubicación confirmada. El punto quedó listo para su planificación.', { exact: true }).waitFor();
            const persisted = await api.get(route, { headers }); assert.equal(persisted.status(), 200);
            const saved = await persisted.json(); assert.equal(saved.version, version);
            assert.ok(Math.abs(saved.latitud - (-34.90 - version * .01)) < 1e-8);
            assert.equal(saved.direccion, 'Geocoding local synthetic 123');
            await page.reload(); await manual.waitFor();
            await page.getByText('Punto registrado · pendiente de revisar.', { exact: true }).waitFor();
        }
        await page.setViewportSize({ width: 320, height: 1000 });
        assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth));
        await page.screenshot({ path: path.join(out, 'saved-320.png'), fullPage: true });
        const statuses = [];
        for (let i = 0; i < 11; i++) statuses.push((await api.post(route + '/busqueda', { headers, data: { consulta: 'Disabled ' + i } })).status());
        assert.ok(statuses.includes(429), 'Configured user HTTP rate limit must reject');
        assert.ok(statuses.every(status => status === 503 || status === 429));
        assert.deepEqual(external, []); assert.deepEqual(errors, []);
        const report = { commerceUrl: 'http://localhost:5102/', destinationUrl: `http://localhost:5102/envios/${id}/destino`,
            shipmentId: id, anonymousSearch: 401, shortSearch: 400, disabledSearch: 503,
            manualSaves: 2, reopenedVersion: 2, persistedLat: -34.92, persistedLon: -56.22,
            httpRateStatuses: statuses, externalAttempts: 0, realProviderCallsEnabled: false,
            mapSdk: 'Synthetic, no real SDK/tiles', providerCredentialsUsed: false };
        await fs.writeFile(path.join(out, 'result.json'), JSON.stringify(report, null, 2));
        console.log(JSON.stringify(report, null, 2));
    } finally { await browser.close(); await api.dispose(); }
})().catch(error => { console.error(error.message); process.exitCode = 1; });
