# AP-04 — Informe de validación

Fecha: 10/11/2026 (America/Montevideo). Fuentes de código seleccionadas: checkout materializado `develop`; backend `3a7cffefb03967e6a9135a5575676403b7c12d8f`, frontend `84444f6a8b42c0f9f164229f520ef6f005bed205`, mobile `329dd3454704c0f45b615d609f469b7fd4b2dd5f`. Los gitlinks de raíz siguen preexistentes y distintos; no se actualizaron ni se hizo checkout/reset. Las pruebas usaron únicamente datos y credenciales sintéticas.

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
- Quedan pendientes el circuito Compose con reinicio y persistencia de acuses, brokers/efectos asíncronos, CI integrado, revisión browser responsive/interactiva, ejecución multiinstancia y aceptación en GCP/Cloud SQL. No se ejecutaron migraciones, workflows, cambios ni despliegues remotos.
- La card de Notion permanecía en `In progress` al consultarla el 10/11/2026; no debe pasar a `Do tests`/`Done` hasta resolver los criterios pendientes y obtener la aceptación requerida.

## Siguiente evidencia requerida

1. Habilitar un transporte BrowserAct/Chrome que mantenga el WebSocket de Blazor al runtime WSL; con fixtures propias, repetir filtros, detalle, selección, acuse, refresh y reapertura.
2. Repetir el circuito en Compose local sin limpiar volúmenes; inspeccionar reinicio conservando datos.
3. Ejecutar el harness de navegador y la suite/CI integrada, registrando cantidades y pruebas omitidas.
4. Preparar evidencia de viewport 1440/320, ampliación 200 %, teclado y estados de carga/error.
5. Con autorización específica, validar imágenes/digests, migración, permisos, HTTPS y replay explícito entre A/B en GCP; conservar el gate hasta entonces.
