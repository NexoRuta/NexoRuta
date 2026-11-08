// Owned Cloud smoke only. Reads generated synthetic credentials without printing them.
const fs=require('node:fs/promises'),path=require('node:path'),assert=require('node:assert/strict');
const {chromium}=require('./node_modules/playwright');
(async()=>{
 const root=path.resolve(__dirname,'../..'),s=JSON.parse(await fs.readFile(path.join(root,'.local/codex-cloud/private.json'),'utf8'));
 assert.equal(s.purpose,'nexoruta-disposable-cloud');const out=process.env.NEXORUTA_WEBHOOK_E2E_DIR||path.join(root,'.local/webhooks-evidence');await fs.mkdir(out,{recursive:true});
 const browser=await chromium.launch({headless:true}),context=await browser.newContext({viewport:{width:1440,height:1000}}),page=await context.newPage();
 try{
  await page.goto('http://localhost:5102/ingresar');await page.locator('#Email').fill(s.commerceEmail);await page.locator('#Password').fill(s.commercePassword);await Promise.all([page.waitForURL(u=>!u.pathname.includes('ingresar')),page.getByRole('button',{name:'Ingresar',exact:true}).click()]);
  await page.goto('http://localhost:5102/webhooks');await page.getByLabel('Operador',{exact:true}).selectOption(s.operatorId);
  const login=await fetch('http://127.0.0.1:5000/api/auth/login',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({email:s.commerceEmail,password:s.commercePassword})});assert.equal(login.status,200);const token=(await login.json()).accessToken;console.log('Synthetic Commerce login verified');
  const headers={Authorization:'Bearer '+token,'Content-Type':'application/json'};
  const subscriptions=await(await fetch('http://127.0.0.1:5000/api/webhooks/suscripciones',{headers})).json();
  if(!subscriptions.some(x=>x.habilitada&&x.contrato===2&&x.url==='http://127.0.0.1:5103/comercio/webhook')){
   await page.getByRole('button',{name:'Nueva suscripción',exact:true}).click();await page.getByLabel('URL receptora',{exact:true}).fill('http://127.0.0.1:5103/comercio/webhook');await page.getByLabel('Clave compartida de firma',{exact:true}).fill(s.webhookSigning);await page.locator('#wh-EnvioCreado').check();await page.getByRole('button',{name:'Guardar suscripción',exact:true}).click();await page.getByText('Suscripción guardada.',{exact:false}).waitFor();
  }
  const opened=context.waitForEvent('page');await page.getByRole('link',{name:'Abrir receptor de prueba en otra pestaña'}).click();const receiver=await opened;console.log('Receiver tab opened');await receiver.getByLabel('Clave de controles',{exact:true}).fill(s.webhookAdmin);await Promise.all([receiver.waitForURL('http://localhost:5103/comercio'),receiver.getByRole('button',{name:'Abrir receptor',exact:true}).click()]);
  console.log('Receiver controls login verified');
  const created=await fetch('http://127.0.0.1:5000/api/envios',{method:'POST',headers,body:JSON.stringify({operadorId:s.operatorId,servicio:{zonaId:s.operatorId,latitud:-34.901,longitud:-56.201,modalidad:'Estandar'},destinatarioNombre:'Ensayo Cloud sintético',destinatarioEmail:'cloud-webhooks@example.test',direccion:'Synthetic 123',bultos:[{codigo:'WH-CLOUD-'+Date.now(),pesoGramos:100,largoCentimetros:10,anchoCentimetros:10,altoCentimetros:10}]})});assert.equal(created.status,201);const id=(await created.json()).id;
  let delivery;for(let i=0;i<100;i++){const history=await(await fetch('http://127.0.0.1:5000/api/webhooks/entregas?operadorId='+s.operatorId,{headers})).json();delivery=history.entregas.find(x=>x.envioId===id&&x.estado==='Entregado');if(delivery)break;await new Promise(r=>setTimeout(r,100));}assert.ok(delivery);assert.equal(delivery.codigoHttp,200);
  await receiver.reload();assert.match(await receiver.locator('body').innerText(),new RegExp(id));assert.match(await receiver.locator('body').innerText(),/0 de 1 bultos/);await receiver.screenshot({path:path.join(out,'cloud-localhost-5103.png'),fullPage:true});
  await page.reload();await page.getByLabel('Operador',{exact:true}).selectOption(s.operatorId);await page.getByRole('heading',{name:'Envío creado · Entregado',exact:true}).first().waitFor();await page.screenshot({path:path.join(out,'cloud-commerce.png'),fullPage:true});
  await fs.writeFile(path.join(out,'cloud-smoke.json'),JSON.stringify({browserUrl:'http://localhost:5103/comercio',workerUrl:'http://127.0.0.1:5103/comercio/webhook',http:200,shipment:id,delivery:delivery.id},null,2));console.log('Cloud HTTP webhook roundtrip verified at localhost:5103/comercio; credentials remain private.');
 }finally{await browser.close();}
})().catch(e=>{console.error(e.message);process.exitCode=1;});
