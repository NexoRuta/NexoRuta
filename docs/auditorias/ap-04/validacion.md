# AP-04 — Informe de validación

Fecha: 11/11/2026 (America/Montevideo). Fuentes fijadas en el manifiesto desplegado a GCP: raíz `a2b56f22fd8240c0cb6ba73309d2efb2cdb14429`, backend `013e11eeeaf177a00e9fbf1ff96c054bd7226084`, frontend `49d44f347a75c473aa39fffda272b4e3a944b269` y mobile `53f6be2cdec48f48e30e390060feeaefb5be0ead`. El checkout local mantiene el cambio materializado preexistente `M mobile`; se preservó y no se publicó desde el workspace. Las pruebas funcionales utilizaron datos/credenciales sintéticos; el despliegue se hizo sobre el canal GCP develop compartido siguiendo el workflow completo.

## Compilación

- La compilación completa de las soluciones Backend y Frontend pasó antes de los últimos ajustes. Después, el proyecto de integración Backend se volvió a compilar con el código final en WSL y el arranque del runtime sintético reconstruyó API, Backoffice, Commerce y Tracking; la prueba frontend de contrato volvió a compilar sus proyectos referenciados.
- El test estático de contrato OpenAPI se compiló y ejecutó en Windows en modo serial: `dotnet test frontend/tests/NexoRuta.ApiClient.Tests/NexoRuta.ApiClient.Tests.csproj --no-restore -m:1 -p:BuildInParallel=false -p:UseSharedCompilation=false --filter FullyQualifiedName~CommerceReturnsContractPublishesCurrentRoutesAndVersionedCommands`. Resultado: 1 aprobado.
- Una ejecución inicial de ese test con paralelismo por defecto agotó memoria/recursos del host (MSBuild lanzó errores `OutOfMemoryException` y `Stack overflow`). Se detuvo esa ejecución y la repetición serial anterior terminó correctamente. No se eliminó caché, build output, base ni volumen para recuperar recursos.
- Persisten warnings de paquetes/analyzers preexistentes (NU1510, xUnit/BL); no se registraron errores de compilación en la ejecución exitosa.

## HTTP, PostgreSQL y contrato

- `scripts/cloud/dev.py start` levantó un runtime efímero propio en WSL, en filesystem Linux: API `127.0.0.1:5000`, Backoffice `:5101`, Commerce `:5102` y Tracking `:5103`. `scripts/cloud/dev.py verify` pasó.
- La verificación reportó PostgreSQL 18.6/PostGIS 3.7, 91 migraciones aplicadas y runtime `nexoruta_api_runtime` con `rolsuper=false` y `rolbypassrls=false`. Los roles y datos eran sintéticos; no se usó la base local persistente del usuario.
- `GET http://127.0.0.1:5102/health/ready` respondió 200. El endpoint API de readiness y las páginas de los servicios del runtime quedaron disponibles.
- `GET http://127.0.0.1:5000/openapi/v1.json` respondió 200. Se regeneró `frontend/contracts/nexoruta.openapi.json` directamente desde ese documento. El snapshot tiene los cinco endpoints AP-04 de lectura, historial, transferencia y acuse; no conserva `POST /api/deposito/envios/{id}/devolucion-comercio`.
- El listado Commerce produjo inicialmente HTTP 500 por acceso directo a la identidad importada protegida por RLS. Se cambió la lectura para usar la función existente `nexoruta_app.list_import_shipment_references(...)` bajo la identidad/operador del contexto. Tras reconstruir, la página quedó en estado vacío sin error.

## Automatización

- Se ejecutó `C31_EntregaParcialRespetaPoliticaCustodiaPruebaReintentosYConflictoPorBulto` con `NEXORUTA_TEST_POSTGRES_MODE=native` contra PostgreSQL/PostGIS sintético: 3/3 variantes aprobadas. La rama de devolución probó transferencia del bulto no entregado, listado/detalle para el comercio, lectura con capacidad recalculada, rechazo HTTP 403 al quitar permiso, acuse, replay del mismo `ComandoId`, conflicto con contenido distinto y ausencia de cambios en resultado/custodia/versión del bulto por el acuse.
- `CommerceReturnsContractPublishesCurrentRoutesAndVersionedCommands`: 1/1 aprobado; valida rutas nuevas, ausencia del alias retirado y campos clave de comando/versionado y capacidades del bulto.
- No se ejecutaron todos los proyectos de test, CI integrado, el harness de browser tests del repositorio ni pruebas concurrentes entre dos instancias API.

## BrowserAct y revisión visual

- BrowserAct 1.6.2 autenticó Commerce con una cuenta sintética en `http://127.0.0.1:5102/devoluciones`. La navegación muestra Devoluciones; la página renderiza título, filtros de fechas/operador/situación/referencia, botón de actualización y el estado vacío accesible. No había una devolución sintética visible para revisar el detalle y acuse en UI.
- La captura de escritorio está en `.local/ap04-evidence/commerce-devoluciones-desktop.png` (1366 px de ancho; viewport del navegador 1366 × 543). La revisión visual encontró jerarquía clara, controles etiquetados y buen uso del ancho disponible en esa captura.
- La automatización observó reintentos repetidos a `/_blazor/negotiate`; el circuito InteractiveServer no llegó a estabilizar una conexión. Al enviar el filtro, el navegador navegó al GET nativo `/devoluciones?` y volvió a los filtros por defecto. Por eso no se considera validada la interacción del filtro: el entorno no demostró que el evento Blazor del componente se ejecutara. No se diagnosticó la causa del fallo de transporte.
- No se verificaron 1440 px, 320 px, zoom de texto al 200 %, estados lentos/error forzados, teclado completo ni la acción de acuse en navegador. La evidencia visual acredita la pantalla vacía de escritorio únicamente.

## Docker/WSL y GCP

- No había Docker CLI disponible en Windows y el socket Docker de WSL no aceptó conexión ni como usuario ni como root. No se arrancaron contenedores ni se tocaron volúmenes. La validación local disponible fue `dev.py` sobre dependencias Linux sintéticas, no Compose.
- El usuario autorizó el despliegue de AP-04 en GCP. Workflow `42957078788` terminó `success` el 11/11/2026, sobre `develop` y el root SHA `a2b56f22fd8240c0cb6ba73309d2efb2cdb14429`. Publicó el release completo `release-cf26779e0d964923b3c1d869a3538712` con seis imágenes construidas y cero digests reutilizados. Se registró el mismo release en los nodos A y B; ambos aplicaron las imágenes inmutables del manifiesto y sus checks directos pasaron. No se guardan aquí nombres de host, direcciones IP, claves ni configuración secreta.
- Manifiesto publicado: raíz `a2b56f22fd8240c0cb6ba73309d2efb2cdb14429`, backend `013e11eeeaf177a00e9fbf1ff96c054bd7226084`, frontend `49d44f347a75c473aa39fffda272b4e3a944b269` y mobile `53f6be2cdec48f48e30e390060feeaefb5be0ead`. Digests de imagen del release: API `sha256:14d33b7ee59f3eedec190494f4ef4ef7bbd2663bc604adf2bcfbc4ce3286e000`; worker `sha256:9eabf9a983020f2b785e2073b8b1696bdfefb0765dadfabad55209f86ad83e23`; Admin `sha256:9facb82c1e72c1ebb7988e377acf186c6a9896d94e38b37d9f3e20bc62f3320d`; Backoffice `sha256:d24c7037ae06a4ccd31131e2ef7b7dfb0af45cb27ac16bbb10ab04f3448658db`; Commerce `sha256:de79682cedf0da5da72b4a689d6465fbc51fae070e0f49a81cb811b218b6d3ab`; Tracking `sha256:ee2044e7db8d68cdfbbb940a6eb710542bbebe3fe24ffa77e9485e3edde851b3`.
- Secuencia de despliegue: servicios compartidos reconciliados y saludables; balanceador drenado; `vm_migrate_schema_migrations`, preflight SQL, provisión de roles/hosting y bootstrap finalizaron en A; después se levantaron A y B con el mismo release. No hubo error de migración en este run. Las comprobaciones de migración y runtime reportaron roles API/bootstrap/worker sin superusuario ni `BYPASSRLS`. A y B pasaron health directo y el balanceador no reportó servicios Commerce no saludables. El workflow concluyó `public_https_and_login_smoke` exitosamente, incluyendo login inicial respaldado por la base.
- Comprobación HTTP independiente posterior: Commerce `/health/ready` respondió 200, API `/health/ready` 200 y `/devoluciones` respondió 302 sin sesión, consistente con redirección a autenticación. Estos checks son HTTP, no revisión interactiva de UI.
- BrowserAct 1.6.2 no consiguió adjuntarse a Chrome directo: `browser open` para Commerce expiró dos veces con `chrome-direct CDP permission retry window expired after 20.0s`; reiniciar solamente el daemon no cambió el estado `idle`. En una continuación se probó también `--headed` con `about:blank` y volvió a expirar. Chrome tenía siete procesos activos. No se utilizó `--allow-restart-chrome`, no se cerraron pestañas ni se ingresaron credenciales. Por ello no hay evidencia BrowserAct ni captura GCP y no se afirma que se hayan validado navegación autenticada, filtros, detalle o acuse remoto. La opción de reinicio queda pendiente de autorización del usuario.
- Finalizada la ventana de comprobación, `vm-controls.yml` operation `stop` (run `42959245823`) terminó `success`. Compute Engine confirmó ambas VMs `TERMINATED`; Cloud SQL quedó `RUNNABLE`. No se solicitaron cambios sobre la base después del despliegue.
- La card de Notion continúa `In progress` (última consulta registrada: 10/11/2026). No se cambia el estado: faltan aceptación funcional/visual autenticada con BrowserAct, replay explícito entre A/B, Compose local con reinicio/persistencia, CI integrado y pruebas responsive/interactivas.

## Siguiente evidencia requerida

1. Restablecer el permiso/conexión CDP de BrowserAct sin reiniciar el Chrome del usuario; autenticar con cuenta sintética, abrir `/devoluciones`, inspeccionar filtros/listado y guardar captura GCP. Si el entorno no provee fixtures sintéticas de devolución, limitarse a lectura/estado vacío y documentarlo; no ejecutar el seed general.
2. Cuando haya fixtures AP-04 sintéticas aisladas, repetir en navegador filtros, detalle por bulto, selección, acuse, refresh y reapertura. Revisar además viewports 1440/320 px, texto al 200 %, teclado y estados de carga/error.
3. Repetir el circuito en Compose local sin limpiar volúmenes; inspeccionar reinicio conservando datos.
4. Ejecutar el harness de navegador y la suite/CI integrada, registrando cantidades y pruebas omitidas.
5. Probar replay/conflicto de forma explícita entre A y B con telemetría que identifique cada nodo; el health y el mismo release/digest no demuestran por sí solos concurrencia o replay multiinstancia.
