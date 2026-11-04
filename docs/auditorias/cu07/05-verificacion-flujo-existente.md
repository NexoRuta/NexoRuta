# CU-07 — verificación del flujo existente

**Conclusión:** el alta individual tiene una base reutilizable verificada con HTTP de integración y PostgreSQL efímero; las pruebas también ejercitan RLS, autorización por actor, reglas versionadas y outbox. Esto no cierra CU-07: el alta por archivo y la idempotencia de reimportaciones siguen sin implementar. La UI no se recorrió en navegador. La mensajería admite redelivery y tiene brechas documentadas abajo; no ofrece entrega exactamente una vez.

**Nota de vigencia:** esta conclusión y el párrafo siguiente describen el corte pre-importación del 23/10/2026. Las afirmaciones “sin implementar” para importación/idempotencia y “UI no recorrida” quedan sustituidas por los resultados posteriores en `08-backend-importacion.md` y `09-commerce-importacion-y-verificacion.md`. La caracterización de mensajería y sus brechas transversales se conserva en los límites descritos por esos informes.

Esta revisión es de evidencia del checkout al **23/10/2026**. No se inició la implementación de importación y las alternativas de `04-diseno-de-implementacion.md` siguen siendo propuestas, no decisiones funcionales.

## Alcance y fuentes

- `docs/alcance/Laboratorio__NET_2026.pdf`: requisito 7 de §5.2 (página impresa 4, PDF físico 6); requisitos transversales §3.3 (p. impresa 2 / física 4), §6.3 (5 / 7), §6.5, §6.6 y §6.8 (6 / 8). §6.8 exige outbox, consumidor idempotente, reintentos con espera creciente, cola de fallidos y consulta/reintento administrativo.
- `docs/alcance/Calcs/Casos de Uso - Responsables.xlsm`, leído como ZIP/XML con biblioteca estándar, sin ejecutar macros ni modificarlo: hojas `Módulos`, `CU obligatorios`, `Alcance aplicaciones`, `Dependencias`, `No funcionales`, `Opcionales`; `CU obligatorios!A10:I10` define CU-07 como obligatorio; `CU obligatorios!A11:I11` define CU-08 como obligatorio y separado; `Dependencias!A4:I4` es D01; `No funcionales!A8:F8` (NFR-05) y `A11:F11` (NFR-08) aplican aislamiento y mensajería. Las celdas revisadas no contienen fórmulas.
- `docs/auditorias/cu07/01-requisitos-y-trazabilidad.md` a `04-diseno-de-implementacion.md`; se contrastaron con el código y las fuentes originales, no se aceptó el diseño propuesto de importación como requisito.
- Código/test fixtures: `backend/src/NexoRuta.Api`, `Application`, `Domain`, `Infrastructure`, `Worker`; `backend/tests/NexoRuta.IntegrationTests`; pantalla y pruebas en `frontend/src` y `frontend/tests`.
- Referencias de líneas abajo corresponden a los archivos del checkout auditado. No se inspeccionaron valores de `.env`, secretos ni credenciales de despliegue.

## Estado del checkout y aislamiento de pruebas

| Checkout | Rama / HEAD | Estado observado |
|---|---|---|
| Raíz | `feature/cu07` / `23ae885f80a63c13579c3633b052f29f8b2fa191` | `architecture.md` actualizado; `backend` con cambios locales; `mobile` modificado; `docs/auditorias/` sin seguimiento. Los cambios preexistentes se conservaron. |
| Backend | `feature/cu07` / `cb628c2b6c1608c2da185ad2f969ed5b48f08bdd` | Cambios documentales en `README.md`, `docs/cu/CU-07-alta-envios.md` y `docs/cu/CU-08-bultos.md`; `tests/NexoRuta.IntegrationTests/Seguridad/RlsRestrictedHttpFlowTests.cs` agrega prueba de denegación POST para actor Operador. Sin cambios de código de producción. |
| Frontend | `feature/cu07` / `10a1768e375708af9263cb422be04ff3d347ffa3` | Limpio. |
| Mobile | checkout `da537ecf60c188e7b2adbf67d4b70097cad9e8d9`; gitlink raíz `e687541b79e4db490f76ba77ea671a94025ac83f` | La diferencia local preexistente se dejó intacta. |

No se cambiaron ramas ni se usaron reset, clean, stash, commits, push o despliegues. Los tests de integración usan `PostgresFixture`/Testcontainers y recursos efímeros propios; no se apuntó a una base compartida.

Se corrigió la inspección del contexto Docker y se verificó, antes de correr contenedores:

| Comando de solo lectura | Resultado |
|---|---|
| `docker context inspect desktop-linux --format '{{.Endpoints.docker.Host}}'` | `npipe:////./pipe/dockerDesktopLinuxEngine` |
| `docker info --format 'name={{.Name}} os={{.OSType}} server={{.ServerVersion}}'` | `name=docker-desktop os=linux server=28.0.4` |

Docker Desktop local se inició para estas pruebas aisladas. No se instalaron/actualizaron dependencias ni se ejecutaron migraciones o seeds sobre una instancia compartida.

## Recorrido real del alta individual

| Paso | Evidencia actual | Resultado comprobado |
|---|---|---|
| Commerce | `frontend/src/NexoRuta.Commerce/Components/Features/Envios/Pages/CrearEnvio.razor` y su PageModel. Permite capturar un envío, elegir operador y enviar un bulto; la página tiene estados de carga/envío/éxito/error y previene doble submit. | Revisión estática. El test `CrearEnvioIgnoresConcurrentSubmitAndRetriesWithTheSameEnteredValues` pasa con `HttpMessageHandler` simulado. No hubo navegador conectado al API. |
| Cliente HTTP | `frontend/src/NexoRuta.ApiClient/Features/Envios/Clients/EnviosApiClient.cs:59-69`, serializa el DTO individual y envía `POST api/envios` con Bearer/token de cancelación. | OpenAPI y pruebas de componente; el test de componente no prueba un servidor real. |
| Endpoint y actor | `backend/src/NexoRuta.Api/Features/Envios/Controllers/EnviosController.cs:16-78`: `[Authorize]`, permiso `envios.crear`, actor Comercio; respuesta 201 y mapeo de errores. | `WebApplicationFactory`/`TestServer` envió HTTP por el pipeline ASP.NET real y obtuvo respuesta contra DB efímera. No es un proceso Kestrel escuchando por TCP. |
| Contexto | `JwtValidacionEventos.cs:15-27,41-46,105-150`; `UsuarioActualHttp.cs:13-34`; `PermisoAuthorizationHandler.cs:20-55`. Se valida JWT, acceso persistido, versión/estado, rol y permiso; `CrearEnvioUseCase.cs:19-46` deriva el comercio del contexto, no del request. | La prueba HTTP usa acceso Comercio. La nueva prueba `RestrictedOperatorHttpCannotCreateShipmentOrOutboxRows` postea como Operador y espera 403, sin Envio ni outbox. El header `X-NexoRuta-Acceso` no sustituye el acceso del JWT. |
| Caso de uso y modelo | `CrearEnvioUseCase.cs:19-46` valida actor, operador activo, reglas publicadas y construye envío con destinatario, dirección y un Bulto. El `OperadorId` recibido es selección de asignación, no identidad del actor. | Pruebas de unidad, round-trip y HTTP; la selección por envío concuerda con la ADR actual. No se exige membresía permanente Comercio–Operador. |
| Persistencia/response | `EfEnviosRepository.cs:24-99` usa `create_shipment`, añade outbox y persiste; `EnviosController` mapea `EnvioCreado`. `EnvioPostgresRoundTripTests` verifica lecturas de vuelta. | Alta, respuesta y relaciones se ejercitaron por HTTP de integración y PostgreSQL efímero. El formulario Commerce no fue verificado visualmente. |

La API y la pantalla existentes sirven de base para una futura extensión. La API actual es de una creación JSON por llamada: no existe en el contrato revisado endpoint/DTO de archivo o lote. La UI individual no satisface por sí sola los canales de archivo ni la idempotencia que hacen obligatorio CU-07 completo.

## RLS y actor de base de datos

### Cómo se construye el contexto confiable

1. El JWT aporta sujeto, ID de acceso y versión de credenciales. `JwtValidacionEventos` valida y consulta el acceso persistido; el middleware agrega el `ContextoUsuario` validado a `HttpContext.Items` (`JwtValidacionEventos.cs:15-27,105-150`).
2. El pipeline registra autenticación/autorización antes de `RlsTransactionMiddleware` (`backend/src/NexoRuta.Api/Program.cs:272-277`). El middleware abre transacción, revalida acceso/organización/sesión, configura los GUC de RLS, y mantiene la respuesta en buffer hasta elegir commit o rollback (`RlsTransactionMiddleware.cs:18-64,70-123`).
3. `IUsuarioActual` exige ese contexto y `RequerirComercio()` falla si no es actor Comercio (`UsuarioActualHttp.cs:13-34`, `ContextoUsuario.cs:7-40`). El endpoint además exige el permiso y el tipo de actor.
4. El formulario envía `OperadorId` para escoger la asignación. El caso de uso lo resuelve como operador activo; no acepta `ComercioId` ni `UsuarioId` como autoridad del cliente. No se observó una regla de membresía Comercio–Operador y no se añadió ninguna; la selección es por envío, conforme a la ADR y la instrucción vigente.

### Rol, privilegios y funciones

- La API obtiene `ConnectionStrings:Postgres` y configura Npgsql (`backend/src/NexoRuta.Infrastructure/Persistence/DependencyInjection.cs:39-44`); el código de la API no fija `SET ROLE`. Por eso el usuario de conexión de una instalación real depende de su configuración runtime, que no se leyó por la restricción de secretos.
- La migración `20261017201732_EnablePostgreSqlRls.cs:17-47` configura `nexoruta_api` como `NOLOGIN`, `NOINHERIT`, `NOSUPERUSER`, `NOBYPASSRLS` y revoca membresías del rol. Es un rol de permisos, no demuestra por sí solo cuál login externo se usa al desplegar. En el test HTTP real se crea un login aleatorio `rls_http_*` sin superusuario ni `BYPASSRLS`, se le concede `nexoruta_api` y ese connection string se configura en el host de pruebas (`RlsRestrictedHttpFlowTests.cs:184-202`). Es la identidad de la API efectivamente probada en este entorno.
- Existe contradicción documental pendiente: `docs/alcance/ADR-MT-001-PostgreSQL-RLS.md:21` describe `nexoruta_api` como `LOGIN`; la migración actual lo fuerza a `NOLOGIN`, y las pruebas usan login aparte. No se puede inferir del repositorio qué principal concreto usa producción. No se afirma que la configuración de producción haya sido comprobada.
- La migración aplica RLS y `FORCE ROW LEVEL SECURITY` a las tablas de negocio y limita privilegios directos. Para el API, las tablas del grafo de envíos se leen por privilegios/RLS; se revocan escrituras de negocio y la creación se permite por función acotada; outbox permite sólo el insert que cumple política (`20261017201732_EnablePostgreSqlRls.cs:93-110,919-986,1040-1053,1108-1144`).
- `Envios` se filtra por ComercioId para Comercio y OperadorId asignado para Operador. Destinatario, Dirección y Bulto heredan visibilidad/escritura desde el envío relacionado (misma migración, políticas inmediatamente posteriores; integración `RlsPolicyTests.cs:182-235`). Así un comercio consulta sus propios envíos entre operadores elegidos; un operador sólo ve sus asignaciones.
- `create_shipment` y `shipment_rules_for_admission` son `SECURITY DEFINER`, con propietario de función separado, `search_path` fijo (`pg_catalog,nexoruta_app`), `EXECUTE` concedido a `nexoruta_api` y acceso público revocado (`20261020232808_BindShipmentToPublishedOperationalRules.Sql.cs:17-39,53-116`). La función valida actor Comercio, contexto org/usuario, acceso activo del mismo comercio, operador activo y versión publicada; inserta recipient/address/shipment/parcel. `claim_outbox`/finish son funciones de cola de propietario acotado, con ruta de ejecución concedida al worker, no al cliente API (`20261017201732_EnablePostgreSqlRls.cs:378-438,598-636`). Las pruebas de catálogo comprueban propietarios, grants, RLS forzado, no-BYPASSRLS y `search_path` (`RlsPolicyTests`, `RlsSqlFunctionContractTests`).
- El contexto se configura con `set_config(..., true)` dentro de la transacción; settings de actor no usados se vacían (`RlsTransaction.cs:139-209`). Commit/rollback cierra su alcance local aun si Npgsql reutiliza una conexión. `TenantRowsAndShipmentChildrenAreScopedByBothShipmentPartiesAndLocalContextExpires` verifica el mismo backend PID tras terminar el contexto; `ConcurrentTenantTransactionsDoNotShareActorContext` cubre aislamiento concurrente (`RlsPolicyTests.cs:182-261`). Ambos pasaron en PostgreSQL real.
- Se ejercitó manipulación del header de selección de acceso frente a JWT y creación denegada para Operador (`RlsPolicyTests.cs:292-350`; `RlsRestrictedHttpFlowTests.cs:67-99`). Los campos de petición no permiten fijar el comercio; `OperadorId` sigue siendo una selección que se valida contra operadores activos.

**Resultado RLS:** garantías de fila, hijos, roles restringidos, función de creación y expiración transaccional están implementadas, cubiertas y ejecutadas satisfactoriamente en los fixtures aislados de esta revisión. No se comprobó el login/rol efectivo de un despliegue ni cualquier configuración manual externa. Las pruebas abarcan dos comercios y dos operadores; no se verificó una comparación de dos configuraciones de operador distintas que satisfaga ese punto más amplio de §6.5. La contradicción ADR/migración se conserva como aclaración documental, no como evidencia de bypass ni motivo para introducir otra regla de acceso.

## Transacción de creación y outbox

La frontera habitual del API es `RlsTransactionMiddleware`: abre una transacción antes del endpoint, vuelve a validar el actor, instala el contexto RLS, captura la respuesta y confirma sólo respuestas exitosas; respuestas de error, excepciones y cancelación llevan a rollback. `EfEnviosRepository.BeginOrJoinAsync` se une a la transacción request-scoped (o toma propiedad si no hay una) (`RlsTransactionMiddleware.cs:35-64`; `RlsTransaction.cs:59-99`).

Dentro de esa frontera:

1. El caso de uso resuelve reglas operativas publicadas y crea el modelo de envío en estado inicial actual.
2. `create_shipment` valida contexto y regla, bloquea/verifica el operador activo y escribe destinatario, dirección, envío y un bulto en la misma transacción (`20261020232808_BindShipmentToPublishedOperationalRules.Sql.cs:53-111`).
3. `EfEnviosRepository.cs:48-99` agrega dos filas outbox: `GenerarSeguimiento` para RabbitMQ con payload `{ envioId, operadorId }` y `EnvioCreado` para Kafka con `{ envioId, operadorId, comercioId, estado }`. Cada fila tiene su propio Id UUIDv7; ambas conservan versión de contrato, destino, prioridad, alcance/clave del envío y estado de entrega.
4. `SaveChangesAsync` persiste los mensajes y el commit de la misma transacción confirma el agregado y ambos mensajes juntos. Los tests fuerzan un error al insertar outbox y comprueban que no queda Envio/Destinatario/Dirección/Bulto parcial (`CreacionAutomaticaSeguimientoTests.cs:128-198`); el caso exitoso comprueba dos mensajes pendientes (`:16-124`).

Por lo tanto, el camino cubierto no puede confirmar los datos de negocio sin las dos filas outbox, ni confirmar esas filas si se revierte la creación. La publicación en el broker es posterior y asíncrona: el outbox asegura persistencia atómica de intención de publicación, no publicación en el mismo commit distribuido con RabbitMQ/Kafka. La cancelación propaga `CancellationToken` por queries, guardado y commit; el middleware intenta rollback con token independiente al atrapar una excepción. Se ejecutó rollback por error de persistencia, no una prueba específica de cancelación ni un corte entre todos los pasos de commit.

## Publicación, consumo y límites de entrega

| Componente | Qué existe | Qué se verificó / límite |
|---|---|---|
| Dispatcher outbox | `Worker/Worker.cs` despacha RabbitMQ; `KafkaOutboxWorker.cs` despacha Kafka. Claim de DB usa lease y `FOR UPDATE SKIP LOCKED`; completa como publicado o error, con nuevo intento programado a 30 s (`EnablePostgreSqlRls.cs:378-438`). Worker selecciona transportes por configuración (`Worker/Program.cs:22-87`). | Pruebas reales con PostgreSQL y brokers efímeros. No se inspeccionó configuración runtime de producción. |
| Rabbit publisher | `RabbitMqOutboxPublisher.cs:35-80` usa durable queue, `mandatory`, mensaje persistente y publisher confirms; MessageId es el Id outbox. Credenciales se requieren de configuración; host/puerto tienen defaults de código (`RabbitMqWorkerConnection.cs:9-23`), no se imprimieron valores secretos. | Broker efímero en pruebas. Si Rabbit confirma pero la actualización SQL falla, el outbox se republica tras lease/retry; posible duplicado, identidad de evento se conserva. |
| Kafka publisher | `KafkaEnvioCreadoPublisher.cs:28-69,114-132` configura productor idempotente, `Acks.All`, key por envío, cabeceras EventId/tipo/versión/fecha/operador y comprueba persistencia. | `KafkaOutboxTests`: 5 pasaron; `ConfirmacionSinActualizacionSql_ReinicioRepublicaConEventIdEstable` demuestra publicación repetida con el mismo EventId cuando el broker confirma y falla el marcado SQL. La idempotencia del productor no elimina la ventana entre broker y DB. |
| Consumidor de tracking | `GenerarSeguimientoConsumer.cs:82-145,201-221` consume Rabbit con ACK manual/prefetch 1; ejecuta persistencia y ACK tras commit. Reintentos conservan Id/contenido; espera confirmación de republicación antes de ACK. `ProcesarGeneracionSeguimiento` guarda identidad procesada de forma idempotente. | `GenerarSeguimientoConsumerTests`: 14; `RabbitMqSeguimientoTopologyTests`: 2; `ProcesarGeneracionSeguimientoTests`: 4, todos pasaron con broker/DB de prueba. |
| Retry/fallidos de tracking | Cola retry durable TTL de 30 s retorna a principal; cola durable de fallidos existe (`RabbitMqSeguimientoTopology.cs:11-51`). Errores de contrato o permanentes van a fallidos; errores de proceso tienen máximo tres intentos. Los clasificados transitorios pueden reintentarse indefinidamente (`GenerarSeguimientoConsumer.cs:272-309`). | Implementado y testeado, pero el intervalo es fijo de 30 s, no creciente. No se encontró endpoint/UI administrativa para consultar/reintentar la cola de tracking fallida. |
| Consumo Kafka de `EnvioCreado` | El handler `KafkaShipmentCreatedOutboxHandler` conecta el outbox al publisher (`OutboxHandlerRegistry.cs:53-58`). | En el código revisado no se encontró consumidor de `nexoruta.envios.creados.v1`; la prueba Kafka lee el mensaje como consumidor de prueba. No demuestra consumo downstream de producción ni su deduplicación. |
| Error de dispatcher outbox | `EfOutboxRepository` completa/error; los workers vuelven a reclamar mensajes con error/lease vencido. | La reprogramación SQL es fija (+30 s); no equivale a espera creciente ni a una cola de fallidos consultable/reintentable por administrador. |

La evidencia soporta **entrega al menos una vez con deduplicación en el consumidor de seguimiento**, no exactamente una vez. Las dos ventanas principales son: broker confirma y el worker cae antes del marcado SQL; o un consumidor completa efecto persistido y cae antes del ACK. Los EventId estables y la tabla de mensajes procesados permiten deduplicar donde ese consumidor participa; cualquier consumidor externo del evento Kafka debe implementar/validar su propia idempotencia. La obligación PDF de esperas crecientes y panel operativo de mensajes fallidos no queda satisfecha por el retry fijo y la cola durable sola.

“Offline” no está resuelto por la frase funcional: el outbox actual cubre trabajo asíncrono **del servidor después del commit HTTP**; no ofrece cola local del navegador/móvil, captura sin conexión ni sincronización posterior del cliente. Esta auditoría no agrega ninguna de esas modalidades.

## Comandos y resultados de verificación

Todos los `dotnet test` usaron `--no-restore`; no se instalaron dependencias. Los tests HTTP usan `WebApplicationFactory`/`TestServer` y PostgreSQL real efímero. No son mocks de persistencia, aunque tampoco son una API Kestrel externa.

| Comando / filtro | Resultado | Alcance y límite |
|---|---:|---|
| `dotnet test backend/tests/NexoRuta.UnitTests/NexoRuta.UnitTests.csproj --no-restore --filter FullyQualifiedName~CrearEnvioUseCaseTests --logger "console;verbosity=minimal"` | 13/13 | Compila capas referenciadas; actor, operador y reglas del caso de uso, sin DB/HTTP. |
| `dotnet test backend/tests/NexoRuta.IntegrationTests/NexoRuta.IntegrationTests.csproj --no-restore --filter FullyQualifiedName~CrearEnvioRequestTests --logger "console;verbosity=minimal"` | 8/8 | Validación de request/unidades/cultura; no cubre DB. |
| `dotnet test frontend/tests/NexoRuta.ApiClient.Tests/NexoRuta.ApiClient.Tests.csproj --no-restore --filter FullyQualifiedName~OpenApiContractTests --logger "console;verbosity=minimal"` | 49/49 | Contratos OpenAPI, no servidor vivo. También compiló Commerce y referencias. |
| `dotnet test backend/tests/NexoRuta.IntegrationTests/NexoRuta.IntegrationTests.csproj --no-restore --no-build --filter FullyQualifiedName~EnvioPostgresRoundTripTests --logger "console;verbosity=minimal"` | 13/13 | Alta y recuperación real de datos en PostgreSQL aislado. |
| Mismo comando, filtros `OperadoresDisponiblesHttpTests`, `ReglasEnvioAdmisionHttpTests`, `RlsPolicyTests`, `RlsRestrictedHttpFlowTests`, `RlsSqlFunctionContractTests`, `CreacionAutomaticaSeguimientoTests` | 2/2, 1/1, 17/17, 3/3, 1/1, 2/2 | HTTP/persistencia; selección de operador, versión reglas, aislamiento, rol restringido, función SQL y atomicidad. Total de este grupo: 39 aprobadas. `RlsRestrictedHttpFlowTests` incluye la nueva denegación al actor Operador. |
| Mismo comando, filtro `KafkaOutboxTests` | 5/5 | Publicación/confirmación/reintento con Kafka/Postgres aislados; incluye duplicado tras ventana broker–DB. |
| Mismo comando, filtros `GenerarSeguimientoConsumerTests`, `RabbitMqSeguimientoTopologyTests`, `ProcesarGeneracionSeguimientoTests` | 14/14, 2/2, 4/4 | Rabbit real, retry/cola fallidos, topología y procesamiento/deduplicación con Postgres. Total de mensajería: 25 aprobadas. |
| Mismo comando, filtro `RecipientEmailHttpTests` | 6/6 | Casos HTTP de validación del destinatario contra fixture PostgreSQL. |
| `dotnet test frontend/tests/NexoRuta.ApiClient.Tests/NexoRuta.ApiClient.Tests.csproj --no-restore --no-build --filter FullyQualifiedName~CrearEnvioIgnoresConcurrentSubmitAndRetriesWithTheSameEnteredValues --logger "console;verbosity=minimal"` | 1/1 | Previene doble submit/reintenta valores con handler HTTP simulado. No prueba navegador ni servidor real. |

No se ejecutó una build completa separada: las invocaciones unitarias/contrato compilaron sus proyectos referenciados. Las pruebas de integración se ejecutaron en el daemon local confirmado y sus fixtures efímeros.

## Verificaciones no realizadas y decisiones previas a importación

- No hubo revisión de Commerce en navegador: Chrome/Edge existen como aplicaciones, pero no hay Playwright/Chromium/Chrome/Edge en PATH ni un entorno frontend+API aislado arrancado para exploración visual. No se instalaron herramientas. Quedan sin comprobar visualmente éxito, errores, reintento y doble envío.
- No se recorrió Kestrel por socket externo; el HTTP de `TestServer` sí pasa por middleware, auth, endpoint y PostgreSQL real. No se comprobó despliegue, variables/roles runtime, broker compartido ni CI remoto.
- La auditoría no decide formato/columnas, identidad externa y ámbito de unicidad, archivo atómico frente a procesar filas válidas, qué hacer con referencia existente y payload diferente, ni si deduplicar contra altas de otros canales. Las alternativas de `04-diseno-de-implementacion.md` no están aprobadas.
- Antes de implementar importación, preservar el mismo contexto de comercio y operador por envío, validación/reglas versionadas, función de creación, transacción y outbox; no repetir eventos al reconocer una identidad existente. Primero acordar las semánticas anteriores y aclarar en D01 el lenguaje “vínculo”, manteniendo la ADR: selección por envío, sin membresía permanente como nuevo requisito.
- CU-08 es obligatorio y separado; el alta actual crea exactamente un bulto, por lo que no debe declararse CU-08 completo ni mezclarse su cierre con las decisiones de identidad de importación CU-07.

**Conclusión de cierre:** el alta individual existente sí es una base técnica probada para reutilizar, incluyendo aislamiento RLS y atomicidad local negocio+outbox en PostgreSQL de prueba. CU-07 completo permanece abierto hasta implementar archivo e idempotencia contra semántica confirmada; además, mensajería conserva brechas de espera creciente/operación de fallidos y la experiencia real de Commerce sigue sin evidencia de navegador.

## Seguimiento posterior (24/10/2026)

El informe anterior verifica el flujo de alta individual con corte al 23/10; no cubre la nueva matriz de cancelación ni extiende la conclusión a todo CU-07. El bloque posterior verificó de forma acotada estados permitidos/prohibidos, terminalidad, repetición, RLS/autorización y atomicidad de cancelación en PostgreSQL efímero. Sus resultados están en [`07-bloque-cancelacion-terminal.md`](07-bloque-cancelacion-terminal.md). Importación e idempotencia de archivo siguen pendientes; este trabajo tampoco completa el resto de la máquina ni CU-08.
