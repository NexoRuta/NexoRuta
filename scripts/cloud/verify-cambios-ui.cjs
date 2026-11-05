/* Controlled browser verification against dev.py synthetic runtime. */
const { chromium } = require('playwright');
const AxeBuilder = require('@axe-core/playwright').default;
const fs = require('node:fs');
const path = require('node:path');
const assert = require('node:assert/strict');
const root = path.resolve(__dirname, '../..');
const state = path.join(root, '.local/codex-cloud');
const secrets = JSON.parse(fs.readFileSync(path.join(state, 'private.json')));
assert.equal(secrets.purpose, 'nexoruta-disposable-cloud');
const demo = JSON.parse(fs.readFileSync(path.join(state, 'demo-cambios.json')));
const shots = path.join(state, 'screenshots');
fs.mkdirSync(shots, {recursive:true});
(async () => {
 const browser = await chromium.launch({headless:true});
 try {
  const checks = [];
  async function pageFor(port, actor) {
   const context = await browser.newContext({viewport:{width:1440,height:1000}});
   const page = await context.newPage();
   await page.route('**/*', route => ['127.0.0.1','localhost'].includes(new URL(route.request().url()).hostname) ? route.continue() : route.abort());
   if (actor) {
    await page.goto(`http://127.0.0.1:${port}/Ingresar`);
    await page.locator('#Email').fill(secrets[actor+'Email']);
    await page.locator('#Password').fill(secrets[actor+'Password']);
    await page.getByRole('button',{name:'Ingresar',exact:true}).click();
    await page.waitForURL(u => !u.pathname.includes('Ingresar'));
   }
   return page;
  }
  async function inspect(page, name) {
   await page.locator('h1').first().waitFor();
   await page.screenshot({path:path.join(shots,name+'.png'),fullPage:true});
   const axe = await new AxeBuilder({page}).withTags(['wcag2a','wcag2aa','wcag21aa','wcag22aa']).analyze();
   checks.push({screen:name,violations:axe.violations.map(v=>({id:v.id,impact:v.impact,nodes:v.nodes.map(n=>n.target)}))});
   await page.keyboard.press('Tab');
   assert(await page.evaluate(() => document.activeElement !== document.body), 'Keyboard focus unavailable: '+name);
   await page.setViewportSize({width:320,height:900});
   assert(!await page.evaluate(() => document.documentElement.scrollWidth > innerWidth), 'Page overflow at 320px: '+name);
   await page.screenshot({path:path.join(shots,name+'-320.png'),fullPage:true});
   await page.setViewportSize({width:1440,height:1000});
   await page.evaluate(()=>document.documentElement.style.fontSize='200%');
   assert(!await page.evaluate(() => document.documentElement.scrollWidth > innerWidth), 'Text overflow at 200%: '+name);
   await page.evaluate(()=>document.documentElement.style.fontSize='');
  }
  const back = await pageFor(5101,'operator');
  await back.goto('http://127.0.0.1:5101/');
  assert((await back.locator('body').innerText()).includes('Entregado parcialmente'));
  await inspect(back,'envios');
  await back.goto('http://127.0.0.1:5101/rutas/'+demo.rutaId);
  assert(!(await back.locator('body').innerText()).includes('Suspendida:'));
  await inspect(back,'ruta');
  await back.goto('http://127.0.0.1:5101/ReporteOperaciones');
  await back.getByRole('heading',{name:'Reporte de entregas y retiros'}).waitFor();
  await inspect(back,'reporte');
  await back.goto('http://127.0.0.1:5101/reglas-operativas');
  if (await back.getByRole('button',{name:'Crear copia para editar'}).count()) await back.getByRole('button',{name:'Crear copia para editar'}).click();
  await back.goto('http://127.0.0.1:5101/reglas-operativas/borrador');
  await back.locator('#PermiteEntregaParcial').check();
  await back.locator('#PoliticaPendientesParcial').selectOption('NuevaVisitaConRecargo');
  await back.locator('#RecargoNuevaVisitaUyu').fill('25');
  await back.getByRole('button',{name:'Guardar borrador',exact:true}).click();
  await back.goto('http://127.0.0.1:5101/reglas-operativas/borrador');
  assert(await back.locator('#PermiteEntregaParcial').isChecked());
  assert.equal(await back.locator('#PoliticaPendientesParcial').inputValue(),'NuevaVisitaConRecargo');
  assert.equal(Number(await back.locator('#RecargoNuevaVisitaUyu').inputValue()),25);
  await inspect(back,'reglas');
  const commerce = await pageFor(5102,'commerce');
  await commerce.goto('http://127.0.0.1:5102/retiros/crear');
  await commerce.getByRole('heading',{name:'Solicitar retiro en domicilio'}).waitFor();
  await commerce.locator('#envio-operador').selectOption(secrets.operatorId);
  await commerce.getByLabel('Nombre',{exact:true}).fill('Comprador sintético navegador');
  await commerce.getByLabel('Correo del comprador',{exact:true}).fill('browser@example.test');
  await commerce.getByLabel('Dirección',{exact:true}).fill('Domicilio sintético 456');
  await commerce.getByText('Ajustar coordenadas manualmente',{exact:true}).click();
  await commerce.getByLabel('Latitud',{exact:true}).fill('-34.9');
  await commerce.getByLabel('Longitud',{exact:true}).fill('-56.2');
  await commerce.getByLabel('Código',{exact:true}).fill('UI-'+Date.now());
  await commerce.getByLabel('Peso (g)',{exact:true}).fill('1000');
  for(const field of ['Largo (cm)','Ancho (cm)','Alto (cm)']) await commerce.getByLabel(field,{exact:true}).fill('10');
  await commerce.getByRole('button',{name:'Volver a comprobar cobertura'}).click();
  await commerce.locator('#alta-servicio option').nth(1).waitFor({state:'attached'});
  const offer = await commerce.locator('#alta-servicio option').nth(1).getAttribute('value');
  await commerce.locator('#alta-servicio').selectOption(offer);
  // Business validation preserves the form and reports the missing motive.
  await commerce.getByRole('button',{name:'Calcular tarifa',exact:true}).click();
  await commerce.getByRole('alert').filter({hasText:'Indicá motivo'}).waitFor();
  await commerce.locator('#retiro-motivo').fill('Cambio solicitado desde el portal');
  await inspect(commerce,'retiro');
  await commerce.getByRole('button',{name:'Calcular tarifa',exact:true}).click();
  await commerce.getByRole('button',{name:'Solicitar retiro',exact:true}).waitFor();
  await commerce.getByRole('button',{name:'Solicitar retiro',exact:true}).click();
  await commerce.waitForURL(u => /^\/envios\/[\da-f-]+$/.test(u.pathname));
  await commerce.getByText('RetiroSolicitado',{exact:false}).first().waitFor();
  checks.push({scenario:'Retiro por portal con cotización y validación de motivo',result:'passed'});
  await commerce.goto('http://127.0.0.1:5102/avisos');
  await commerce.getByRole('heading',{name:'Avisos de entregas y retiros'}).waitFor();
  await inspect(commerce,'avisos');
  const tracking = await pageFor(5103);
  const token = demo.links.entregaId.url.split('/').at(-1);
  await tracking.goto('http://127.0.0.1:5103/seguimiento/'+token);
  await tracking.getByText('2 de 3 bultos entregados',{exact:false}).waitFor();
  await inspect(tracking,'seguimiento');
  fs.writeFileSync(path.join(state,'ui-cambios-result.json'),JSON.stringify(checks,null,2));
  console.log(JSON.stringify(checks));
 } finally { await browser.close(); }
})().catch(error=>{console.error(error);process.exitCode=1;});
