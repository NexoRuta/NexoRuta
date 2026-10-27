# CU-07 — revisión técnica manual del cambio acumulado

**Fecha:** 25/10/2026. **Resultado:** revisión manual completada con una corrección puntual de presentación. No es aprobación nativa, cierre global de CU-07 ni cierre de CU-08, máquina de estados o mensajería transversal.

## Alcance y estado revisado

Se leyeron las instrucciones entregadas para el workspace, `docs/auditorias/cu07/09-commerce-importacion-y-verificacion.md` y los componentes necesarios para contrastar implementación, pruebas y afirmaciones previas: endpoint/importación, parser, caso de uso, identidad persistida, funciones RLS, bloqueo de referencias, transacción, outbox, ApiClient, Commerce, OpenAPI, cancelación terminal y pruebas asociadas. No se repitió la auditoría funcional de las fuentes originales ni se amplió la revisión a CU-08, al resto de transiciones o al funcionamiento integral de brokers.

| Repositorio | Rama | HEAD al inicio de la revisión | Estado relevante |
|---|---|---|---|
| Raíz | `feature/cu07` | `23ae885f80a63c13579c3633b052f29f8b2fa191` | `architecture.md` modificado; gitlinks `backend` y `frontend` apuntan a checkouts con cambios locales; `mobile` diverge del gitlink registrado; documentación de auditoría y diagrama corregido sin seguimiento. |
| Backend | `feature/cu07` | `cb628c2b6c1608c2da185ad2f969ed5b48f08bdd` | Cambios acumulados versionados y archivos CU-07/cancelación nuevos sin seguimiento, detallados abajo. |
| Frontend | `feature/cu07` | `10a1768e375708af9263cb422be04ff3d347ffa3` | Cambios acumulados versionados y archivos de Commerce/API Client nuevos sin seguimiento, detallados abajo. |

El checkout de `mobile` está en `da537ecf60c188e7b2adbf67d4b70097cad9e8d9`, mientras la raíz registra `e687541b79e4db490f76ba77ea671a94025ac83f`; el submódulo móvil no tenía cambios locales propios. Es una diferencia preexistente ajena a CU-07. No se revirtió, editó ni atribuyó a esta revisión. Tampoco se atribuyen a esta revisión los cambios previos de `architecture.md`, los docs 01–09, el diagrama corregido ni los cambios acumulados de los submódulos.

### Inventario del cambio acumulado

El inventario se obtuvo con `git status --short --untracked-files=all` en la raíz, backend y frontend. La etiqueta `M`/`m` refleja cambios versionados o gitlinks modificados; `??` refleja archivos nuevos sin seguimiento. No se usó únicamente `git diff` para contar los nuevos archivos.

**Raíz:** `architecture.md`; gitlinks `backend`, `frontend`, `mobile`; `docs/alcance/Diagramas/maquina-estados-envio-corregida.png`; auditorías `docs/auditorias/cu07/01-requisitos-y-trazabilidad.md` a `09-commerce-importacion-y-verificacion.md` (anteriores a esta tarea). Este informe 10 y las actualizaciones de resumen indicadas abajo son documentación de esta revisión.

**Backend — versionados con modificaciones acumuladas:**

- Documentación: `README.md`, `docs/cu/CU-07-alta-envios.md`, `docs/cu/CU-08-bultos.md`, `docs/cu/cancelacion-envios.md`.
- API/aplicación/dominio/persistencia: `src/NexoRuta.Api/Features/Comercios/Controllers/OperadoresDisponiblesController.cs`, `src/NexoRuta.Api/Features/Envios/Controllers/EnviosController.cs`, `src/NexoRuta.Application/Administracion/Dtos/OperadorDisponible.cs`, `src/NexoRuta.Application/Administracion/Repositories/IOperadoresRepository.cs`, `src/NexoRuta.Application/Envios/Repositories/IEnviosRepository.cs`, `src/NexoRuta.Application/Envios/UseCases/CrearEnvioUseCase.cs`, `src/NexoRuta.Domain/Envios/Envio.cs`, `src/NexoRuta.Infrastructure/Administracion/Repositories/EfOperadoresRepository.cs`, `src/NexoRuta.Infrastructure/Envios/Repositories/EfEnviosRepository.cs`, `src/NexoRuta.Infrastructure/Persistence/DependencyInjection.cs`, `src/NexoRuta.Infrastructure/Persistence/Migrations/NexoRutaDbContextModelSnapshot.cs`, `src/NexoRuta.Infrastructure/Persistence/NexoRutaDbContext.cs`, `src/NexoRuta.Infrastructure/Persistence/RlsSqlFunctionContract.cs`, `src/NexoRuta.Infrastructure/Persistence/RlsTransaction.cs`, `src/NexoRuta.Infrastructure/Reparto/EfOperacionesRepartoRepository.Ejecucion.cs`.
- Pruebas modificadas: `tests/NexoRuta.IntegrationTests/Envios/OperadoresDisponiblesHttpTests.cs`, `tests/NexoRuta.IntegrationTests/Notificaciones/CancelacionPublicaPushTests.cs`, `tests/NexoRuta.IntegrationTests/Notificaciones/CancelacionPushTests.cs`, `tests/NexoRuta.IntegrationTests/Reparto/ConciliacionEntregaHttpTests.cs`, `tests/NexoRuta.IntegrationTests/Seguimiento/PublicCancellationTests.cs`, `tests/NexoRuta.IntegrationTests/Seguridad/RlsRestrictedHttpFlowTests.cs`, `tests/NexoRuta.IntegrationTests/Seguridad/RlsSqlFunctionContractTests.cs`, `tests/NexoRuta.UnitTests/Envios/CrearEnvioUseCaseTests.cs`.

**Backend — archivos nuevos de CU-07/cancelación:**

- Contratos: `src/NexoRuta.Api/Features/Envios/Contracts/Requests/ImportarEnviosRequest.cs`, `src/NexoRuta.Api/Features/Envios/Contracts/Responses/ImportacionEnviosResponse.cs`.
- Importación: `src/NexoRuta.Application/Envios/Importacion/CsvEnviosParser.cs`, `HuellaSolicitudEnvio.cs`, `ImportacionEnviosContracts.cs`, `ImportarEnviosUseCase.cs`.
- Persistencia: `src/NexoRuta.Infrastructure/Envios/IdentidadEnvioImportado.cs`.
- Migraciones nuevas: `20261024120000_EnforceCancellationTerminalState.cs`; `20261024130000_AddShipmentImportIdentity.cs` y `.Designer.cs`; `20261025005447_OrderImportLocksByEffectiveKey.cs` y `.Designer.cs`; `20261025010937_HistoricalImportOperatorCatalog.cs` y `.Designer.cs`.
- Pruebas nuevas: `tests/NexoRuta.IntegrationTests/Envios/CommerceCsvImportKestrelTests.cs`, `ShipmentCsvImportHttpTests.cs`, `tests/NexoRuta.UnitTests/Envios/CsvEnviosParserTests.cs`, `EnvioCancellationRulesTests.cs`.

**Frontend — versionados con modificaciones acumuladas:** `contracts/nexoruta.openapi.json`; `src/NexoRuta.ApiClient/Core/Http/ApiHttp.cs`; `src/NexoRuta.ApiClient/Features/Envios/Clients/EnviosApiClient.cs`; `src/NexoRuta.ApiClient/Features/Envios/Contracts/Responses/EnvioResponse.cs`; `src/NexoRuta.ApiClient/Features/Operadores/Clients/OperadoresApiClient.cs`; Commerce `Components/Features/Envios/Pages/CrearEnvio.razor` y `Components/Layout/CommerceNavigationCatalog.cs`; Tracking `Components/Pages/Seguimiento.razor`; pruebas `CancelacionCommerceTests.cs`, `OpenApiContractTests.cs`, `SeguimientoCancelacionPagesTests.cs`.

**Frontend — archivos nuevos de importación:** `src/NexoRuta.ApiClient/Features/Envios/Contracts/Responses/ImportacionEnviosResponse.cs`, `src/NexoRuta.ApiClient/Features/Operadores/Contracts/Responses/OperadorImportacionResponse.cs`; Commerce `Components/Features/Envios/Pages/ImportarEnvios.razor(.css)`, `Components/Features/Envios/Shared/ResultadoImportacionEnvios.razor(.css)`, `wwwroot/plantillas/alta-envios.csv`; pruebas `tests/NexoRuta.ApiClient.Tests/ImportacionEnviosApiClientTests.cs` y `ImportacionEnviosComponentTests.cs`.

**Superficies editadas específicamente durante esta revisión:** `frontend/src/NexoRuta.Commerce/Components/Features/Envios/Shared/ResultadoImportacionEnvios.razor`, `frontend/src/NexoRuta.ApiClient/Features/Envios/Clients/EnviosApiClient.cs`, `frontend/tests/NexoRuta.ApiClient.Tests/ImportacionEnviosComponentTests.cs`, `frontend/tests/NexoRuta.ApiClient.Tests/ImportacionEnviosApiClientTests.cs` y una aserción del caso de rechazo en navegador en `backend/tests/NexoRuta.IntegrationTests/Envios/CommerceCsvImportKestrelTests.cs`. Además se creó este documento y se actualizaron los resúmenes vigentes 01 y 03. No se modificó código de producción backend ni se editaron contratos o migraciones durante esta revisión.

## Hallazgo confirmado y corrección

### CU07-MR-01 — Mensaje de duplicado afirmaba una operación en un archivo rechazado

- **Severidad:** moderada (P2). No provocaba escrituras extra ni alteraba el resultado almacenado, pero informaba a Comercio que se había procesado una operación cuando la atomicidad impedía crear todos los registros nuevos.
- **Requisito afectado:** resultado comprensible y veraz por fila; un rechazo atómico crea cero nuevos y debe mostrar los válidos nuevos como no procesados.
- **Comportamiento esperado:** `DuplicadoDe` identifica la fila canónica, pero no implica que el archivo haya sido aceptado ni que se haya creado una operación.
- **Comportamiento observado antes de corregir:** `ResultadoImportacionEnvios.razor:42-45` siempre mostraba “se realizó una sola operación”. Backend puede devolver un grupo equivalente cuyo canónico sea `NoProcesado` y cuyo duplicado sea `DuplicadoDe` cuando otra fila rechaza atómicamente el archivo.
- **Reproducción:** en un archivo con dos filas equivalentes de una referencia nueva y una fila conflictiva (o filas nuevas para un operador histórico inactivo), el servidor rechaza todo; la respuesta contiene `NoProcesado` para la fila canónica y `DuplicadoDe` para la fila repetida. La interfaz afirmaba una operación pese a que no había creación.
- **Corrección mínima:** la vista busca el estado de la fila canónica. Solo dice que se procesó una vez si su estado es `Creado` o `YaExistente`; en los demás estados explica que el duplicado tampoco se procesó porque se rechazó el archivo.
- **Regresión:** prueba de componente con respuesta atómica realista, más afirmación en Chromium/Kestrel para duplicados y rechazo por operador inactivo. La base aislada conserva sus conteos.
- **Estado:** corregido y probado; el contrato HTTP no cambió.

### CU07-MR-02 — El ApiClient aceptaba JSON incompleto como resultado estructurado

- **Severidad:** moderada (P2). Un cuerpo JSON sintácticamente válido pero incompleto podía devolver un resultado con `Resumen`/`Filas` nulos; Commerce los consume al renderizar y la página podía terminar en excepción en vez de presentar un error de respuesta.
- **Comportamiento esperado:** respuestas 200/409/422 solo se devuelven a Commerce si su estado coincide con el HTTP y los datos necesarios para renderizar cada fila están presentes; un cuerpo inesperado se traduce en error comprensible.
- **Comportamiento observado antes de corregir:** `ReadFromJsonAsync<ImportacionEnviosResponse>` devolvía un objeto no nulo para `{"estado":"Completada"}`. `EnviosApiClient.ImportarAsync` lo aceptaba por no nulo, aunque faltaban `resumen` y `filas`.
- **Reproducción/evidencia:** prueba del `HttpMessageHandler` con status 200 y cuerpo `{"estado":"Completada"}`. Antes de la corrección, la aserción `ThrowsAsync<NexoRutaApiException>` falló con “No exception was thrown”.
- **Corrección mínima:** validar estado compatible con HTTP, resumen/filas, número de fila, estados conocidos y colecciones requeridas; si no es válido, el cliente usa el error existente de “formato inesperado”. No se cambia la respuesta del backend ni el contrato OpenAPI.
- **Regresión:** prueba del cliente cubre el JSON incompleto; las pruebas válidas 200/409/422 comprueban que se conservan resultados por fila.
- **Estado:** corregido y probado con handler HTTP simulado. El flujo Kestrel usa respuestas válidas; la anomalía JSON solo está probada en ApiClient.

## Revisión técnica por superficie

### Autorización, contexto y RLS

- `EnviosController` limita `POST /api/envios/importaciones` a autenticación, actor Comercio y `envios.crear`; `operadorId` es una selección, no una fuente de identidad del comercio. El contexto de comercio procede de la autenticación y el acceso persistido.
- El catálogo específico para importación mantiene la misma restricción de actor/permisos y devuelve datos mínimos de operadores activos e históricos utilizados por importaciones de ese comercio. No otorga `envios.consultar` ni expone configuración del operador. La decisión backend rechaza atómicamente cualquier fila nueva dirigida a un operador inactivo, a la vez que permite reconocer una referencia original equivalente.
- `IdentidadesEnvioImportado` tiene RLS habilitado y forzado, clave única por comercio y referencia, y no concede lectura/escritura directa al rol `nexoruta_api`. Las funciones `SECURITY DEFINER` tienen propietario de función acotado, `search_path` explícito, EXECUTE revocado a `PUBLIC`, concesión explícita al rol API y validación del contexto/actor/comercio.
- La evidencia de aislamiento no depende únicamente de superusuario o mocks: `CommerceCsvImportKestrelTests` crea una identidad de login `NOSUPERUSER NOCREATEDB NOCREATEROLE NOBYPASSRLS`, miembro de `nexoruta_api`, y usa ese login en HTTP real contra Postgres efímero. Las conexiones privilegiadas de la fixture se usan para crear/migrar y consultar conteos de verificación, no como principal HTTP.
- La función vigente `lock_import_references` en la migración `20261025005447_OrderImportLocksByEffectiveKey` calcula, deduplica y ordena por el `bigint` efectivo producido por `hashtextextended`, no por el texto de referencia antes del hash. El orden global evita que dos lotes con el mismo conjunto en órdenes opuestos adquieran las claves de advisory en órdenes distintos. La garantía final sigue siendo la restricción única `(ComercioId, ReferenciaExterna)`. La migración histórica con el primer orden se conserva; la migración aditiva reemplaza la función.
- Las referencias internas de operador/reglas usan bloqueos de filas y el flujo de creación conserva sus validaciones. No se observó una incompatibilidad de orden en los caminos inspeccionados: importación serializa claves externas antes de entrar a creación; los bloqueos de operador/reglas y creación individual no esperan las advisory de importación.

### Transacción, resultado, reimportación y outbox

- `RlsTransactionMiddleware` abre la transacción de la solicitud autenticada, captura el cuerpo de respuesta en memoria y solo lo copia al cuerpo HTTP después del commit. Devuelve rollback para respuestas 4xx y ante excepciones. `BeginOrJoinAsync` permite que el caso de uso/repositorio participe de esa transacción sin crear una transacción paralela.
- La importación usa `READ COMMITTED`: adquiere advisory locks de referencias y ejecuta la lectura de identidades en una operación posterior. Un archivo nuevo, sus hijos, la identidad y los mensajes outbox quedan dentro del mismo límite transaccional. Los nuevos se informan como `Creado` únicamente para una respuesta que middleware libera después de commit confirmado. Un fallo de comunicación durante commit puede dejar resultado desconocido al cliente; el reintento con las mismas referencias reconcilia mediante la identidad única, no se etiqueta como rollback confirmado.
- El repositorio aplica el contexto RLS por envío y guarda cada envío, vínculo de identidad y sus dos mensajes outbox antes de establecer el contexto del siguiente envío. Esto es necesario porque la política de inserción outbox verifica el `ShipmentId` actual; diferir todos los mensajes al final habría dejado el contexto apuntando al último envío. La operación sigue en una transacción única.
- Los envíos nuevos generan los eventos existentes `GenerarSeguimiento` (RabbitMQ) y `EnvioCreado` (Kafka), una vez por envío nuevo en la transacción; `YaExistente`/duplicados no agregan filas outbox. La idempotencia aplica por identidad de referencia, no por hash del contenido.
- La huella original versionada se deriva de datos originales normalizados, comercio y operador seleccionados; no depende del estado mutable, reglas publicadas actuales, seguimiento ni prueba física posterior. La migración de identidad es aditiva; no adopta retrospectivamente altas individuales/API sin referencia. La revisión no repitió pruebas de publicación/consumo de brokers: entrega exactly-once no queda afirmada. Retries crecientes y operación de mensajes fallidos permanecen pendientes transversales.

### CSV, HTTP y Commerce

- El parser exige UTF-8 estricto, acepta BOM, usa el lector CSV de la dependencia ya instalada para comillas/campos multilínea, valida encabezado y datos, y acota el archivo a 5 MiB y los registros de datos a 500. El endpoint da margen de 32 KiB al multipart; controla por separado el tamaño del archivo. La prueba Kestrel acepta archivo exacto de 5 MiB y devuelve 413 con 5 MiB + 1 byte.
- El `ApiClient` envía multipart `archivo`/`operadorId`, usa Bearer, streaming, `ResponseHeadersRead`, dispone request/content/response, construye un stream nuevo por invocación y lee resultados estructurados para 200/409/422. Los errores globales y cuerpos inesperados se distinguen de resultados por fila. Commerce evita doble envío, no reintenta automáticamente errores funcionales y ofrece reintento manual con archivo y operador conservados; ante pérdida de comunicación declara que el resultado puede no haberse recibido.
- La revisión adicional endureció solo la lectura de resultados de importación: la validación de forma rechaza respuestas JSON parciales antes de exponerlas al componente. No se tocó el tratamiento general de errores HTTP del resto de ApiClient.
- La ruta Commerce presenta plantilla con el mismo encabezado del parser, límites y semántica; estados de carga y resultado accesibles. La revisión manual y navegador no equivalen a certificación WCAG 2.2 AA. El OpenAPI versionado y las pruebas previas de contrato están en 09; no se cambió el contrato en esta revisión.

### Cancelación

- El dominio no permite transición saliente desde `Cancelado`. `ConciliarEntregaFisica` todavía acepta ese estado para registrar un hecho físico tardío, pero `RegistrarEntregaFisica` conserva `Cancelado` y no cambia el estado a Entregado/Pendiente: no es una salida ni borra evidencia histórica.
- La función SQL vigente permite cancelar solo desde `Admitido`, `EnDeposito`, `AsignadoRuta`, `EnTransito`, `NoEntregado`, `Reprogramado` y `EnDevolucion`; bloquea el envío y exige versión actual. La autorización se valida antes de reconocer una cancelación repetida. El camino público conserva comprobación del código. Repetir una cancelación autorizada equivalente devuelve la auditoría existente sin agregar historial/outbox.
- En esta revisión se ejecutaron 27 pruebas unitarias `EnvioCancellationRulesTests` y 18 integraciones filtradas de cancelación autenticada/pública y conciliación; todas pasaron. No se modificó esta lógica.

## Verificaciones ejecutadas en esta revisión

| Tipo | Comando / verificación | Resultado y límite |
|---|---|---|
| Destino Docker | `docker context show`; `docker context inspect desktop-linux --format '{{json .Endpoints.docker.Host}}'` | `desktop-linux`; `npipe:////./pipe/dockerDesktopLinuxEngine`. |
| RED de regresión de componente | `dotnet test frontend/tests/NexoRuta.ApiClient.Tests/NexoRuta.ApiClient.Tests.csproj --filter FullyQualifiedName~ImportacionEnviosComponentTests --no-restore --verbosity quiet` sobre la aserción nueva antes de corregir la vista | Falló únicamente `AtomicRejectionShowsNoGlobalSuccessAndCorrelatesRowsForCorrection`; demostró el texto falso. |
| RED de contrato defensivo | `dotnet test frontend/tests/NexoRuta.ApiClient.Tests/NexoRuta.ApiClient.Tests.csproj --filter FullyQualifiedName~ImportarAsync_RejectsIncompleteStructuredResponse --no-restore --verbosity minimal` antes de corregir ApiClient | Falló con `Assert.Throws() Failure: No exception was thrown` para `{"estado":"Completada"}`. |
| Componente + build frontend | Mismo proyecto/filtro con `--verbosity minimal`, luego de la corrección | 3/3 pasaron; construyó ApiClient, Commerce y proyectos frontend referenciados, sin errores. Evidencia de renderer de componente, no por sí sola de navegador. |
| ApiClient + componente | `dotnet test frontend/tests/NexoRuta.ApiClient.Tests/NexoRuta.ApiClient.Tests.csproj --filter 'FullyQualifiedName~ImportacionEnviosApiClientTests|FullyQualifiedName~ImportacionEnviosComponentTests' --no-restore --verbosity minimal` | 11/11 pasaron tras ambas correcciones. Incluye rechazo del JSON incompleto y los estados esperados. Un primer ciclo mostró la falla RED; el primer build detectó además un warning nullable introducido, corregido antes de la ejecución final (el último build no mostró ese warning). |
| Kestrel + Postgres + Chromium | `dotnet test backend/tests/NexoRuta.IntegrationTests/NexoRuta.IntegrationTests.csproj --filter FullyQualifiedName~CommerceCsvImportKestrelTests --no-restore --verbosity minimal` | 1/1 pasó (24 s, ejecución final tras endurecer ApiClient). Testcontainers efímero, principal HTTP restringido, procesos API/Commerce y Chromium. Incluye doble fila nueva con operador inactivo, mensaje correcto de `DuplicadoDe` no procesado, y conteos sin cambios. El mismo test cubre regresiones CU-07, límites, aislamiento, autenticación y carga visual descritas en 09; no prueba brokers. |
| Cancelación dominio | `dotnet test backend/tests/NexoRuta.UnitTests/NexoRuta.UnitTests.csproj --filter FullyQualifiedName~EnvioCancellationRulesTests --no-restore --verbosity minimal` | 27/27 pasaron. |
| Cancelación HTTP/Postgres | `dotnet test backend/tests/NexoRuta.IntegrationTests/NexoRuta.IntegrationTests.csproj --filter 'FullyQualifiedName~CancelacionPublicaPushTests|FullyQualifiedName~CancelacionPushTests|FullyQualifiedName~PublicCancellationTests|FullyQualifiedName~ConciliacionEntregaHttpTests' --no-restore --verbosity minimal` | 18/18 pasaron (62 s) en el fixture efímero existente. |

La vista de importación ya se había inspeccionado en Chromium escritorio y a 320 CSS px, con teclado/foco, en el corte 09. El test Kestrel/browser se volvió a ejecutar con la regresión nueva. No se realizó una nueva auditoría visual completa ni contraste instrumental. La prueba de publicación/consumo de brokers no se repitió ni se declara realizada.

## Estado actual y riesgos residuales

- **Implementado:** alta individual/API existente, CSV idempotente de CU-07, identidad externa por comercio, atomicidad, Commerce/ApiClient, catálogo mínimo de operadores históricos y el bloque de cancelación terminal documentado en 07.
- **Verificado:** pruebas unitarias/componentes, PostgreSQL aislado con principal API restringido, Kestrel/browser para escenarios cubiertos, tamaños de archivo, aislamiento/outbox transaccional y regresión de cancelación, según 08, 09 y las ejecuciones de esta revisión. Cada modo tiene límites descritos arriba y en 09.
- **Revisión manual:** completada para las superficies indicadas; un defecto de mensaje fue corregido. No equivale a revisión independiente automática ni aprueba la candidata.
- **Revisión nativa:** pendiente. La revisión no pudo avanzar porque la transición requería `external.select_intended_untracked` y esa captura no está disponible en las herramientas del runtime. No se inventó evidencia ni se generó aprobación.
- **Pendientes transversales/documentales:** clarificación D01; matriz completa de configuración de dos operadores y evidencia de principal de despliegue real; retries crecientes/administración de fallidos; publicación y consumo de brokers; cobertura visual/accesibilidad más amplia. CU-08 sigue siendo caso obligatorio separado. La máquina de estados completa tampoco se cierra por esta revisión.

No se hicieron commits, push, cambios de rama, reset, clean, stash, despliegues, cambios de código backend de producción, migraciones, contratos ni dependencias.

Risk: none (las correcciones quedan limitadas a la representación y validación del resultado de importación; no cambian comportamiento compartido, datos persistidos, permisos ni contrato público, y tienen pruebas de componente, cliente y Kestrel).
