# CU-10 — recepción en depósito

## Base, fuentes y alcance

Base remota verificada: principal `7bcca7a`, Backend `3ebf059`, Frontend `a65c131`, Mobile `74a25f1`, rama `feature/cu12-14-15-16`. Esa base sigue pendiente de revisión humana. Este informe no declara aceptados CU-06, CU-08, CU-12, CU-14, CU-15, CU-16 ni otros CU.

Fuentes: `docs/alcance/Laboratorio__NET_2026.pdf`, §4 (superficie Backoffice y operario de depósito), §5.2 numeral 10, página impresa 4: «Recepción del envío en depósito mediante escaneo, con verificación contra lo declarado por el comercio y registro de discrepancias». Planilla `Calcs/Casos de Uso - Responsables.xlsm`, hoja **CU obligatorios A13:I13**, CU-10, M02, Backoffice/API, actor operario de depósito. Se leyeron también Dependencias y Alcance aplicaciones: D06/D09 consumen datos de bultos; AP-01 (gestión general de incidencias) no fija una política de aceptación de discrepancias de recepción. No se ejecutaron macros ni se usaron colores como evidencia.

Se contrastaron las auditorías existentes de CU-08, la matriz de estados y el historial inmutable. Sus descripciones históricas de un solo bulto o de recepción masiva no sustituyen el checkout real.

Las fuentes no dicen que se deban corregir medidas declaradas, recalcular tarifas, aceptar una diferencia sin subsanación ni recibir todos los bultos al escanear uno. Interpretación aplicada:

- Escanear identifica; confirmar el cotejo acredita presencia física de **ese bulto**.
- Bulto presente, incluso con discrepancia: custodia `Deposito`. Bulto no presentado: no se mueve su custodia ni se inventa observación. El listado muestra qué falta cotejar.
- El envío conserva `Admitido` hasta que todos sus bultos estén físicamente recibidos y su último cotejo sea conforme. Así no resulta elegible para planificación cuando aún hay faltantes o diferencias pendientes.
- Una discrepancia exige observaciones. Las medidas observadas pueden omitirse cuando no es posible medir; se conservan como «Sin medir». No se sustituyen por supuestos.
- Para subsanar, se registra **otro cotejo** con las medidas verificadas iguales a las declaradas y confirmación de conformidad. No se edita ni borra el hecho anterior. Este circuito no permite aprobar un sobrepeso como si coincidiera ni corregir la declaración/tarifa del comercio.
- Los retornos/devoluciones mantienen su circuito previo y sus reglas de custodia, estados e incidencias de cierre. Una recepción no libera vehículo ni completa una entrega.

## Inventario y brechas encontradas

| Área | Existía en la base | Brecha y cambio de CU-10 |
| --- | --- | --- |
| Identificación | UUID persistido por bulto, código visible, etiquetas PDF con QR que contiene UUID en formato D | Consulta por UUID o código exacto dentro del operador. Código ambiguo: 409 y pedir UUID; código desconocido/ajeno: mismo 404. Sin búsquedas globales o creación automática de bultos. |
| Recepción | `RecibirAsync` cambiaba custodia de todos los bultos y estado del envío mediante una confirmación masiva | Primera recepción individual con cotejo. Se impide usar el endpoint masivo para un envío `Admitido`; sigue disponible para los retornos y confirmaciones previas. Consumidores y fixtures se actualizaron juntos, sin un alias del contrato anterior para primera recepción. |
| Cotejo | Medidas declaradas en `Bultos`; controles de capacidad y precisión existentes | Medidas observadas separadas, resultado conforme/discrepancia y observaciones; conformidad requiere igualdad con la declaración y medidas completas. Hasta dos decimales efectivos, valores positivos dentro del rango del dominio. |
| Parciales | Custodia separada del estado comercial, pero UI asumía todos los bultos juntos | Resumen por bulto con custodia, cotejo actual, pendientes e historial; transición del envío solo al completar todos. |
| Permisos | `envios.gestionar`, contexto de operador, RLS, antiforgery Backoffice | Se reutiliza ese permiso; no requiere rol administrador ni permiso de decisiones operativas. Comercio, anónimo y operador sin permiso quedan rechazados. |
| Historia | Eventos canónicos de estado y trazas de operaciones existentes | `RecepcionesBulto` registra cada cotejo con declaración, observado, responsable, comando y fecha; es append-only y con FORCE RLS. La transición final usa el historial canónico `RecepcionDeposito`, correlacionado por comando. |
| UI | Diseño aceptado de Depósito/Rutas/Flota/Envíos, acciones contextuales | Acción «Escanear y cotejar bultos» en cabecera de Depósito, aun si falla la consulta de reparto; acción contextual de primera recepción. Pantalla de tarea con el mismo shell/tokens; no rediseño de otras superficies. |

## Persistencia, versiones y reintentos

Migración aditiva `20261103000000_AddDepotParcelReceipts`. La tabla especializada conserva la declaración como snapshot y el cotejo observado por separado. Identidad de comando por operador, FKs a envío/bulto/usuario/acceso, secuencia generada por servidor para orden histórico determinista, fecha UTC del servidor. No reconstruye cotejos para recepciones anteriores a esta migración.

La recepción toma el bloqueo de operador ya utilizado por reparto, valida versiones de envío/bulto y persiste auditoría, custodia y transición final dentro de la misma transacción. Un recotejo en depósito avanza la versión del bulto. Una recepción parcial no inventa una transición del envío. Un reintento exacto exige mismo actor, bulto y payload y recupera el resultado sin repetir escrituras. Un escaneo posterior de un bulto ya conforme informa que ya estaba recibido; no emite otro hecho ni mueve su custodia. Una nueva operación incompatible o con versión vencida recibe conflicto controlado.

RLS de lectura por operador; INSERT requiere contexto de operador y usuario/acceso del actor, y bulto del mismo envío/operador. Rol API con SELECT/INSERT, sin UPDATE/DELETE/TRUNCATE. Triggers rechazan modificación/borrado/truncado incluso desde el propietario de la fixture. No se amplían permisos de `Envios`, `Bultos` ni historia canónica.

## Interfaz y cámara

Backoffice `/deposito/recepcion`: UUID del QR como identificador principal; código impreso exacto como alternativa. Enter busca y **no** confirma una recepción. El formulario muestra medidas declaradas, observadas, resultado y observaciones; mantiene valores/comando ante error (incluso si tampoco puede recuperar el estado), selecciona el código al enfocar para que la próxima lectura lo reemplace, evita doble envío e informa progreso. Tras confirmar, lista faltantes/discrepancias del envío y conserva todos los cotejos del bulto seleccionado.

Cámara opcional, solo tras pulsar «Leer QR con cámara», audio deshabilitado, contexto seguro (HTTPS o loopback admitido por navegador). Decodificación local `@zxing/browser` 0.1.5, bundle versionado y licencias MIT/Apache-2.0 incluidas, sin CDN ni subida de imágenes. Se detienen tracks al leer, cancelar, ocultar o abandonar la página, también si un permiso pendiente llega después de cancelar. Errores de permiso/dispositivo/apertura tienen mensajes y retorno al campo manual. No se altera `permanent=false` ni se usa geocodificación/routing.

Entrada por lector que actúa como teclado (USB/Bluetooth), teclado y pegado permanecen disponibles. No se presume una prueba con lector físico ni una cámara de teléfono real.

## Evidencia por requisito

| Requisito | Evidencia ejecutable |
| --- | --- |
| Varios bultos, incompletos y conservación de declaración/tarifa | `RecepcionDepositoHttpTests.MultiParcelReceiptIsIncompleteUntilAllAreComparedAndDoesNotRewriteDeclarationsOrTariff`: alta real con dos bultos; custodia parcial, bloqueo del bypass masivo, finalización y comparación de declaraciones/cargo antes/después. |
| Discrepancia, pendiente y recotejo | `DiscrepancyKeepsPhysicalCustodyAndPendingStateUntilANewConformingRecheckWithoutErasingHistory`: peso observado distinto, custodia en depósito, estado pendiente, recotejo y dos hechos preservados en orden. |
| Repetición e idempotencia | `RetriesAreScopedToActorPayloadAndParcelAndNewScansDoNotDuplicateFacts`: comando repetido, payload alterado, nuevo escaneo de bulto conforme y conteo de efectos. |
| Concurrencia real | `IndependentOperatorsCompeteInPostgresAndOnlyOneReceiptAndTransitionAreWritten`: dos operarios autenticados, transacciones independientes con rol API restringido; una tercera transacción retiene el bloqueo y observa dos sesiones esperando en `pg_stat_activity` antes de liberarlo. Una recepción nueva y una confirmación de ya recibido; un solo cotejo y transición. No usa mocks para la competencia. |
| Código desconocido/ajeno y acceso | `UnknownForeignAndUnauthorizedParcelsAreNotExposed`: operador extranjero con bulto real, 404 uniforme, comercio 403 y anónimo 401. |
| Estados/versiones/medidas inválidas | `StaleVersionsInvalidMeasuresAndIncompatibleStatesCannotReceive`: 409/400 sin recepción/custodia parcial. |
| Atomicidad | `FailureOfReceiptOrCanonicalHistoryRollsBackCustodyStateAndAllEventsAndCanRetry`: restricciones de base forzadas en auditoría y luego historia canónica, rollback de toda la operación, reintento posterior exitoso. |
| Inmutabilidad | Intentos UPDATE/DELETE/TRUNCATE sobre auditoría desde propietario de fixture, rechazados con SQLSTATE 55000. |
| Rol de depósito / contrato | `WarehouseRoleNeedsOnlyShipmentManagementAndOperatorWithoutItIsForbidden`, `AmbiguousPrintedCodeRequiresUuidAndOpenApiPublishesReceiptContracts`. |
| Etiqueta y navegador real | `RecepcionDepositoBrowserTests.RealLabelDecodingAndBackofficeReceiptUseRestrictedApiAndIsolatedPostgres`: PDF descargado del endpoint real, render por `pdftoppm`, decodificación QR real por ZXing, Backoffice compilado del checkout, API Kestrel y PostgreSQL/RLS propios. |
| Regresiones | Suite Reparto sin Browser, destinos, historia/RLS, etiquetas, tarifas y push de reasignación; se preservan retornos, cierre/custodia, capacidad y snapshots. Las fixtures hacen la primera recepción por la API nueva, conservando sus aserciones. |

Resultados ejecutados en Cloud, SDK 10.0.401 / PostgreSQL18-PostGIS / Chromium151:

| Invocación | Resultado |
| --- | --- |
| Build API y Backoffice del checkout | Aprobados; advertencias preexistentes NU1510/CS8629, sin errores |
| CU-10 HTTP + RLS + concurrencia + OpenAPI | **9/9 aprobadas**, sin omisiones |
| Regresión reparto, destinos, historia/RLS, etiquetas, tarifas y push | **201/201 aprobadas**, sin omisiones; incluye las primeras 7 pruebas de CU-10, no sumar como casos distintos |
| Unitarias Backend, suite completa | **308/308 aprobadas** |
| Cliente de etiquetas, filtro Etiquetas | **10/10 aprobadas** |
| Chromium fullstack CU-10 (opt-in) | **1/1 aprobada**; PDF real, discrepancia/parcial/recotejo, consulta y persistencia, pérdida controlada de respuesta después de confirmar y fallo de consulta, reintento con mismo comando sin nuevo hecho |
| Axe, acotado a pantalla de recepción | Sin hallazgos en formulario y recepción completa; no certifica WCAG global |
| Inspección visual | Capturas de 1440, 375 y 320 px, reflujo a 200% y estados de discrepancia/completo revisados |

Los resultados corresponden a ejecuciones finales; los intentos iniciales del harness con esperas de navegación/axe/contexto o comparación textual de decimales no se cuentan como aprobaciones. No se cambiaron reglas del producto para sortearlos. Las capturas, PDF sintético, logs y claves del proceso de prueba quedan fuera de Git.

La evidencia de cámara utiliza un `MediaStream` de canvas con fotogramas de la etiqueta PDF, consumido por el decodificador real. Los errores de permiso/dispositivo y la demora/cancelación de permiso se controlan en el harness. Esto acredita decodificación, flujo, limpieza y recuperación; **no acredita cámara física, calidad óptica, Bluetooth ni un lector USB real**. Teclado, Enter, foco, 1440/375/320 px, reflujo con texto al 200%, errores de servidor con valores preservados y escaneo axe acotado se verifican en Chromium. La espera de envío se controla en el harness para inspeccionar el estado ocupado; la persistencia y los reintentos se comprueban contra PostgreSQL. El fallo de transporte de la prueba se introduce únicamente en middleware del host de test, después de una escritura real confirmada; se comprueba que hubo exactamente una respuesta 503 forzada y un fallo de consulta, y que el reintento no agrega otro cotejo. No hay endpoint de control de fallos en la aplicación publicada.

## Reproducir y validar manualmente

Requisitos: SDK .NET 10.0.401, Docker PostgreSQL18/PostGIS, Node/Playwright de `scripts/cloud/package-lock.json`, Chromium y `pdftoppm`. En Cloud se reutilizó SDK/Docker y se instalaron las herramientas de navegador con cachés dentro de workspace; no se ejecutó el instalador con el manifiesto antiguo para mover gitlinks a un checkpoint.

```bash
source scripts/cloud/env-agent.sh
export DOTNET_CLI_HOME=/workspace
export NUGET_PACKAGES=/workspace/.cache/nuget-packages
export NUGET_HTTP_CACHE_PATH=/workspace/.cache/nuget-http
export PLAYWRIGHT_BROWSERS_PATH=/workspace/.cache/ms-playwright
export NEXORUTA_PLAYWRIGHT_MODULE=/workspace/NexoRuta/scripts/cloud/node_modules/playwright
export NEXORUTA_RECEIPT_E2E_DIR=/tmp/nexoruta-cu10-browser
export NPM_CONFIG_CACHE=/workspace/.cache/npm
npm ci --prefix scripts/cloud --ignore-scripts
scripts/cloud/node_modules/.bin/playwright install chromium
dotnet build frontend/src/NexoRuta.Backoffice
dotnet test backend/tests/NexoRuta.IntegrationTests --filter 'FullyQualifiedName~RecepcionDeposito'
```

En una PC adaptar/omitir variables de caché y ajustar la ruta absoluta del módulo Playwright. Las fixtures generan/migran bases exclusivas con datos sintéticos y eliminan sus contenedores al terminar. No necesitan ni leen `.env` del taller.

Recorrido manual posterior: crear un envío sintético con dos bultos e imprimir sus etiquetas; entrar como operario con `envios.gestionar`; Depósito → Escanear y cotejar bultos; leer el primer QR o ingresar UUID/código y Enter; comprobar declarado y registrar conforme. Verificar que el otro sigue pendiente. En el segundo registrar una discrepancia con valores/notas reales; verificar custodia y que `Admitido` permanece. Subsanar físicamente y registrar otro cotejo conforme; comprobar `En depósito`, historial previo conservado y declaración/tarifa sin cambios. Repetir el escaneo y comprobar que no duplica. Probar cámara denegada/ausente y completar por teclado. No usar los datos de la prueba manual existente.

## Límites y publicación

No se operó sobre el envío excluido ni sobre la ruta manual del 02/11/2026: solo bases nuevas de fixtures. No se cerraron entregas/liberaciones de esa prueba. Mobile, CU-06, 401 intermitente y revisión humana de la base siguen pendientes.

No hay herramienta Gentle-AI, memoria Engram o revisión nativa disponible en esta sesión; no se afirma haber ejecutado esas revisiones. Se siguieron AGENTS.md, DESIGN.md, la skill del entorno Cloud, inspección de código/diff y las verificaciones disponibles.

Publicación exclusiva en `feature/cu10-recepcion-deposito`:

| Repositorio | SHA publicado |
| --- | --- |
| Backend | `adcba4189c70b32ec78d3a9d8dce132387c02eb0` |
| Frontend | `c0f40c1bc032e6da1988098ab4c36e4869228a61` |
| Mobile (sin cambios) | `74a25f1b5b18c7dfc006cf7df747d73b0ec4910a` |

El principal referencia esos gitlinks. Backend y Frontend se publicaron primero. No se hicieron merges, force-push ni publicaciones sobre ramas ajenas. Verificación desde un clon **remoto** limpio del principal (commit `099cc7c`, antes de esta nota documental): `git submodule update --init --recursive --depth 1` obtuvo los tres SHA anteriores desde GitHub y dejó el árbol limpio. No se copiaron carpetas de trabajo, binarios, `.env`, claves ni bases del checkout de implementación. La última actualización del principal es documental y conserva esos mismos gitlinks; el SHA final se informa en la entrega.

Orden para revisar/integrar posteriormente: Backend y su migración, Frontend consumidor, principal con los gitlinks. No se ejecutó esa integración.
