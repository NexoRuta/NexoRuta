const fs = require('node:fs/promises');
const path = require('node:path');
const assert = require('node:assert/strict');
const { chromium } = require('playwright');
const { AxeBuilder } = require('@axe-core/playwright');
const root = path.resolve(__dirname, '../..');
const output = path.join(root, 'docs/evidencias/rediseno');
const surfaces = [
    ['commerce',5102,'commerce','/envios/crear'], ['envios',5102,'commerce','/envios'],
    ['importacion',5102,'commerce','/envios/importar'], ['comercio',5102,'commerce','/mi-comercio'],
    ['backoffice',5101,'operator','/'], ['configuracion',5101,'operator','/tarifas'],
    ['reglas',5101,'operator','/reglas-operativas'], ['rutas',5101,'operator','/rutas/planificar'],
    ['vehiculos',5101,'operator','/vehiculos'], ['zonas',5101,'operator','/zonas'],
    ['admin',5103,'admin','/operadores'], ['admin-formulario',5103,'admin','/operadores/crear'],
    ['tracking',5104,null,'/'], ['tracking-error',5104,null,'/not-found']
];
(async () => {
    await fs.mkdir(output, { recursive: true });
    const credentials = JSON.parse(await fs.readFile(path.join(root,'.local/codex-cloud/private.json')));
    assert.equal(credentials.purpose,'nexoruta-disposable-cloud');
    const browser = await chromium.launch({headless:true});
    const report = { surfaces:[], failures:[], externalBlocked:[] };
    const sessions = new Map();
    try {
        for (const [name,port,role,url] of surfaces) {
            const context = await browser.newContext({viewport:{width:1440,height:1000},reducedMotion:'reduce',storageState:sessions.get(role)});
            const page = await context.newPage();
            await page.route('**/*', route => {
                const u = new URL(route.request().url());
                if (/^https?:$/.test(u.protocol) && !['127.0.0.1','localhost'].includes(u.hostname)) {
                    report.externalBlocked.push(u.hostname); return route.abort();
                }
                return route.continue();
            });
            const base = `http://127.0.0.1:${port}`;
            try {
                if (role && !sessions.has(role)) {
                    await page.goto(base+'/ingresar');
                    await page.locator('#Email').fill(credentials[role+'Email']); await page.locator('#Password').fill(credentials[role+'Password']);
                    await page.getByRole('button',{name:'Ingresar',exact:true}).click(); await page.waitForURL(u=>!u.pathname.includes('ingresar'));
                    sessions.set(role,await context.storageState());
                }
                await page.goto(base+url); await page.waitForLoadState('networkidle');
                assert.equal(await page.locator('h1').count(),1,'One main heading');
                for (const width of [1440,320]) {
                    await page.setViewportSize({width,height:1000});
                    assert.equal(new URL(page.url()).pathname,url,'Surface route remains stable');
                    const overflow = await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth);
                    const axe = await new AxeBuilder({page}).withTags(['wcag2a','wcag2aa','wcag21aa','wcag22aa']).analyze();
                    const entry = {name,url,width,title:await page.locator('h1').innerText(),overflow,violations:axe.violations.map(v=>({id:v.id,impact:v.impact,help:v.help,nodes:v.nodes.map(n=>({target:n.target,summary:n.failureSummary}))}))};
                    report.surfaces.push(entry);
                    await page.screenshot({path:path.join(output,`despues-${name}-${width}.png`),fullPage:true});
                    if (overflow || axe.violations.length) report.failures.push({name,width,overflow,axe:axe.violations.map(v=>v.id)});
                    // Reach the skip link through the keyboard, then activate it with Enter.
                    for(let n=0;n<60 && !(await page.locator('.nr-skip-link').evaluate(e=>e===document.activeElement));n++)await page.keyboard.press('Shift+Tab');
                    assert.equal(await page.locator('.nr-skip-link').evaluate(e=>e===document.activeElement),true,'Keyboard reaches skip link');
                    const skip = await page.locator('.nr-skip-link').boundingBox();assert.ok(skip && skip.y>=0 && skip.x>=0,'Skip link visible when focused');
                    if(name==='commerce'&&width===320)await page.screenshot({path:path.join(output,'foco-salto-320.png')});
                    await page.keyboard.press('Enter');assert.equal(await page.evaluate(()=>document.activeElement.id),'main-content','Skip link focuses main');
                    assert.equal(new URL(page.url()).pathname,url,'Skip link preserves route');
                    if(width===320){
                        const menu=page.getByRole('button',{name:'Mostrar u ocultar navegación principal',exact:true});
                        if(await menu.count() && await menu.isVisible()){
                            await menu.press('Enter');await page.waitForFunction(()=>document.querySelector('.nr-menu-toggle')?.getAttribute('aria-expanded')==='true');
                            await page.keyboard.press('Escape');await page.waitForFunction(()=>document.querySelector('.nr-menu-toggle')?.getAttribute('aria-expanded')==='false');
                            assert.equal(await menu.evaluate(e=>e===document.activeElement),true,'Escape returns focus to menu');
                        }
                        await page.evaluate(()=>document.documentElement.style.fontSize='200%');
                        const zoomOverflow=await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth);
                        entry.text200Overflow=zoomOverflow;if(zoomOverflow)report.failures.push({name,width,text200Overflow:true});
                        if(['commerce','configuracion','admin-formulario','tracking'].includes(name))await page.screenshot({path:path.join(output,`texto200-${name}-320.png`),fullPage:true});
                        await page.evaluate(()=>document.documentElement.style.fontSize='');
                    }
                }
                console.log(`${name}: Chromium1440/320, axe, teclado y texto200 comprobados`);
            } catch(error) { report.failures.push({name,error:error.message}); console.error(`${name}: ${error.message}`); }
            finally { await context.close(); }
        }
    } finally { await browser.close(); }
    report.externalBlocked=[...new Set(report.externalBlocked)];
    await fs.writeFile(path.join(output,'verificacion-portales.json'),JSON.stringify(report,null,2)+'\n');
    console.log(JSON.stringify({surfaces:report.surfaces.length,failures:report.failures,externalBlocked:report.externalBlocked}));
    if(report.failures.length)process.exitCode=1;
})().catch(error=>{console.error(error.message);process.exit(1)});
