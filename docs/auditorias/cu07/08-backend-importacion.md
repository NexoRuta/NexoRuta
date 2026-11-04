# CU-07 — evidencia del bloque backend de importación CSV

**Fecha:** 24/10/2026  
**Alcance:** parser, validación, identidad persistida, caso de uso, transacción del lote y endpoint HTTP. Commerce y revisión visual no forman parte de este bloque.  
**Estado del corte backend:** backend implementado. Las afirmaciones de que Commerce, Kestrel o navegador no se habían verificado se refieren a este bloque y quedan reemplazadas por `09-commerce-importacion-y-verificacion.md`; la matriz transversal global sigue parcialmente abierta.

Las decisiones de CSV, identidad por referencia, operador por archivo, archivo atómico, equivalencia y límites descritas aquí fueron decisiones de proyecto expresadas para la implementación. No se presentan como texto literal del PDF o del XLSM. La matriz de requisitos originales y el diseño de base están en `01-requisitos-y-trazabilidad.md` y `06-diseno-tecnico-y-plan.md`.

## Alcance y estado inicial conservado

Se trabajó sobre `feature/cu07`, sin cambiar rama ni HEAD y sin commits, push o despliegues. El HEAD observado fue raíz `23ae885f80a63c13579c3633b052f29f8b2fa191` y backend `cb628c2b6c1608c2da185ad2f969ed5b48f08bdd`. Había cambios locales previos, incluido el bloque de cancelación y modificaciones en frontend/mobile; se conservaron. Este bloque no cambió frontend ni mobile y preservó `07-bloque-cancelacion-terminal.md`.

Docker se confirmó mediante inspección de solo lectura: contexto `desktop-linux`, endpoint `npipe:////./pipe/dockerDesktopLinuxEngine`, motor Docker Desktop `28.0.4`. Las integraciones usaron `PostgresFixture`/Testcontainers, con bases efímeras propias sobre `postgis/postgis:18-3.6-alpine`. No se usó una base compartida ni productiva.

## Comportamiento implementado

### CSV y validación

- `backend/src/NexoRuta.Application/Envios/Importacion/CsvEnviosParser.cs` usa `TextFieldParser`, ya disponible, con delimitador coma, campos entrecomillados, comillas internas escapadas, saltos de línea dentro de campos y BOM UTF-8 opcional. Decodifica UTF-8 en modo estricto.
- Exige exactamente el encabezado del diseño 06: `referenciaExterna,nombreDestinatario,emailDestinatario,direccion,codigoBulto,pesoGramos,largoCentimetros,anchoCentimetros,altoCentimetros`.
- Rechaza más de 5 MiB o más de 500 registros de datos. Las unidades y rangos son los del contrato real `CrearEnvioRequest`: gramos, centímetros y decimal invariante con punto; cada fila crea un envío y un bulto.
- `ImportarEnviosUseCase` valida todos los registros antes de admitir nuevos. Normaliza textos aplicando trim y referencia en NFC; la referencia distingue mayúsculas, mide Unicode por rune, acepta 1–128 caracteres y rechaza controles. Nombres, dirección, código/email y medidas observan longitudes, formato y rangos del contrato/dominio actuales.

### Identidad y equivalencia original

La migración nueva `20261024130000_AddShipmentImportIdentity` agrega `IdentidadesEnvioImportado` con PK única `(ComercioId, ReferenciaExterna)`, FK compuesta al envío/comercio y al operador del envío, índice único por `(ComercioId, EnvioId)`, versión de huella y check de SHA-256 de 32 bytes. El índice preexistente `IX_Envios_ComercioId` se conserva; la clave única compuesta `(ComercioId, Id)` se agrega para la FK y no reescribe registros.

`HuellaSolicitudEnvio` calcula SHA-256 versionada (dominio `NexoRuta/EnvioImport/V1`) a partir de componentes UTF-8 con longitudes prefijadas: comercio, operador, nombre/email/dirección originales normalizados, código de bulto y cuatro medidas en formato decimal `G29` invariante. La identidad sigue siendo la referencia, no la huella. No se comparan estado, versión actual, reglas publicadas actuales, seguimiento ni hechos de entrega agregados después. Alta individual/API anterior sin referencia no se backfillea.

### Transacción, RLS y carreras

`RlsTransactionMiddleware` conserva la propiedad de la transacción de la solicitud y bufferiza la respuesta hasta commit. El caso de uso llama `BeginOrJoinAsync`; `EfEnviosRepository.IniciarImportacionAsync` exige `READ COMMITTED`. El repositorio ejecuta primero la función de bloqueo y luego una consulta separada de identidades, para que una solicitud que esperó vea bajo `READ COMMITTED` el commit previo.

La función inicial `lock_import_references(text[])` deriva claves mediante `hashtextextended(comercioId || ':' || char_length(referencia) || ':' || referencia, 0)`. La auditoría posterior encontró que ordenar referencias en `COLLATE "C"` no garantizaba el orden global de las claves `bigint` efectivamente bloqueadas. La migración aditiva `20261025005447_OrderImportLocksByEffectiveKey` corrigió la función para deduplicar y adquirir las claves efectivas ordenadas numéricamente; no se editó la migración histórica. La restricción única sigue siendo la garantía final. `find_import_references(text[])` devuelve únicamente identidades del comercio del contexto, y `bind_import_identity(...)` escribe bajo el mismo contexto de comercio, envío y operador. Ver prueba de orden efectivo y concurrencia en 09.

La tabla nueva tiene RLS habilitado y forzado; el rol API no recibe DML directo. Las tres funciones son `SECURITY DEFINER`, propiedad de `nexoruta_shipment_fn` (sin `SUPERUSER`/`BYPASSRLS`), con `search_path` fijo, `PUBLIC` sin `EXECUTE` y ejecución otorgada al rol API. Las funciones validan el actor Comercio y el acceso persistido vigente; no confían en un comercio enviado por el cliente.

Las nuevas filas se crean mediante la preparación compartida de `CrearEnvioUseCase` y la función existente `create_shipment`. Se insertan el envío, destinatario, dirección, bulto e identidad dentro de la transacción. `EfEnviosRepository` agrega los dos outbox existentes a la misma transacción: un `GenerarSeguimiento` para RabbitMQ y un `EnvioCreado` para Kafka por cada envío nuevo. La persistencia de existentes o duplicados internos no produce mensajes adicionales.

Los equivalentes existentes se reconocen antes de validar admisión para filas nuevas, incluso si el operador original dejó de estar activo. Si una solicitud incluye nuevas filas para operador inactivo, se rechaza el archivo completo. Conflictos externos/internos no actualizan el envío. Filas válidas nuevas de un archivo rechazado quedan `NoProcesado`. Una respuesta exitosa con `Creado` se escribe únicamente cuando el middleware confirma la transacción; si se pierde la respuesta tras el commit, reintentar las mismas referencias devuelve `YaExistente`.

### Contrato HTTP/OpenAPI

Se agrega `POST /api/envios/importaciones`, multipart `archivo` + `operadorId`, autenticado, con políticas `envios.crear` y actor Comercio. El comercio se deriva del JWT/acceso; campos desconocidos como `comercioId` no establecen contexto. El contrato individual `POST /api/envios` permanece sin referencia obligatoria y sin cambio de ruta/request/respuesta.

- `200`: importación completada; resumen y estado por registro (`Creado`, `YaExistente`, `DuplicadoDe`).
- `400`: archivo ausente, encabezado/CSV/UTF-8 inválido o request incompleto.
- `409`: identidad externa ya existente con payload u operador diferente, o referencias repetidas incompatibles dentro del archivo.
- `413`: archivo sobre 5 MiB o más de 500 registros.
- `422`: filas inválidas o nuevas admisiones rechazadas (operador/reglas), con filas nuevas como `NoProcesado`.
- Un fallo inesperado de DB/commit no se transforma en éxito parcial; la transacción revierte cuando hay rollback confirmado. La pérdida de confirmación de commit se trata como resultado incierto, recuperable por reintento.

## Evidencia de pruebas

Comandos ejecutados desde `backend/` (sin instalar ni actualizar dependencias):

| Check | Resultado | Alcance / limitación |
|---|---|---|
| `dotnet test tests/NexoRuta.UnitTests/NexoRuta.UnitTests.csproj --filter 'FullyQualifiedName~CsvEnviosParserTests|FullyQualifiedName~CrearEnvioUseCaseTests' --no-restore --verbosity minimal` | 17/17 aprobadas. | Pruebas unitarias del parser y regresión del caso de uso; no demuestran PostgreSQL/RLS. |
| `dotnet test tests/NexoRuta.IntegrationTests/NexoRuta.IntegrationTests.csproj --filter 'FullyQualifiedName~ShipmentCsvImportHttpTests|FullyQualifiedName~ImportIdentityTableAndDefinerFunctionsRemainScopedToCommerceContext|FullyQualifiedName~ConsumedFunctionsMatchExactPostgresSignaturesForRestrictedRuntimeRoles' --no-restore --logger 'console;verbosity=detailed' --verbosity minimal` | 15/15 aprobadas en PostgreSQL Testcontainers. | Incluye HTTP TestServer, OpenAPI, identidad/RLS/privilegios y funciones en DB real. No usa broker ni navegador. |
| `dotnet test tests/NexoRuta.IntegrationTests/NexoRuta.IntegrationTests.csproj --filter 'FullyQualifiedName~EnvioPostgresRoundTripTests|FullyQualifiedName~EnvioCancellationRulesTests|FullyQualifiedName~CancelacionPushTests|FullyQualifiedName~CancelacionPublicaPushTests|FullyQualifiedName~PublicCancellationTests|FullyQualifiedName~ConciliacionEntregaHttpTests|FullyQualifiedName~RlsRestrictedHttpFlowTests' --no-restore --verbosity minimal` | 34/34 aprobadas. | Regresión del alta individual, RLS y bloque previo de cancelación/conciliación; no implica cierre de toda la máquina. |
| `dotnet ef migrations has-pending-model-changes --project src/NexoRuta.Infrastructure/NexoRuta.Infrastructure.csproj --startup-project src/NexoRuta.Api/NexoRuta.Api.csproj --no-build` | `No changes have been made to the model since the last migration.` | Comparación del modelo y snapshot; no ejecuta producción ni cambia datos. |
| `git diff --check` (raíz y backend) | Aprobado. | Comprobación de whitespace únicamente. |

Casos de integración HTTP/PostgreSQL incluidos: alta, reimportación completa y subconjunto; existente+nuevo; mismo ID de referencia en dos comercios; conflicto por cambio de operador/datos; duplicado interno equivalente e incompatible; operador inactivo; reimportar tras cancelación, conciliación física tardía y cambio de dirección; solicitudes concurrentes de referencias en orden opuesto y payload conflictivo; respuesta perdida después de commit y recuperación por reintento; rollback inducido después de crear una fila, insertar identidad y persistir outbox; ausencia de outbox duplicado; versiones de reglas asociadas; actor Operador denegado; spoof de `comercioId`; CSV demasiado grande y 501 filas; contrato OpenAPI multipart. Pruebas unitarias cubren BOM, UTF-8 inválido, comillas/comas/saltos de línea, CSV malformado, encabezado exacto y límites byte/registro exactos y límite + 1.

La prueba `ImportIdentityTableAndDefinerFunctionsRemainScopedToCommerceContext` verificó directamente en PostgreSQL RLS habilitado/forzado, policy Commerce, falta de privilegios directos del API, propietario de funciones, `SECURITY DEFINER`, `search_path`, `PUBLIC` sin `EXECUTE` y rol propietario sin `SUPERUSER`/`BYPASSRLS`.

## Medición local

En la última ejecución instrumentada, el envío HTTP de 500 filas tardó **2,905 ms** desde el proceso de prueba hacia el API TestServer y PostgreSQL efímero Docker (`postgis/postgis:18-3.6-alpine`). Dos solicitudes superpuestas con 2 referencias comunes en orden inverso tardaron **102 ms**; el resultado combinado fue 2 envíos nuevos y 2 existentes, sin duplicados. Una carrera simultánea de distinto payload para la misma referencia dejó una sola creación y un conflicto.

Son mediciones puntuales de un host local, base efímera e instancia de API de prueba sin broker; no representan latencia/contención de producción, no separan tiempo de parseo/DB/locks y no son un benchmark estadístico. El lote de 500 queda dentro de los límites iniciales en este entorno; medir p95, contención sostenida y tiempos del despliegue sigue pendiente antes de ampliar o ajustar límites.

## Limitaciones y pendientes

- **Corte histórico sustituido por 09:** Commerce, ApiClient, plantilla, estados, errores por fila, reintento, doble envío y navegador no estaban dentro de este bloque; se implementaron/verificaron después según la evidencia de 09.
- `TestServer` no aplica `IHttpMaxRequestBodySizeFeature`/`IHttpRequestBodySizeFeature`; por ello sus pruebas no demostraban enforcement Kestrel. La prueba posterior con Kestrel aislado confirmó el archivo válido exacto de 5 MiB y 413 para 5 MiB + 1 byte; ver 09.
- En este bloque el flujo HTTP fue `TestServer` con PostgreSQL efímero y no ejecutó publishers/consumidores/brokers. La etapa 09 tampoco amplió la ejecución de mensajería: la transacción prueba persistencia outbox, no publicación. Ver la evidencia histórica del dispatcher/consumidor en 05 solo para el alcance que cubrió.
- No se verificó el runtime de un despliegue real. El bloque 09 sí probó Kestrel y navegador local con login API restringido, que no acredita configuración productiva.
- Pendientes transversales ya conocidos (backoff creciente y administración/visibilidad de fallidos) no fueron ampliados por este bloque.
- El alta individual no exige ni recibe referencia y no se deduplican retrospectivamente datos previos.
- CU-08 continúa como caso obligatorio separado. La máquina de estados completa tampoco queda cerrada por esta importación.

## Conclusión

El backend ofrece una base funcional verificada para importar CSV atómica e idempotentemente, reutilizando el alta, el contexto RLS y transactional outbox. `09-commerce-importacion-y-verificacion.md` completa después el ApiClient/Commerce y la evidencia Kestrel/browser. La evidencia actual de modalidades directas de CU-07 está en 01/09; los pendientes transversales X02/X04/X05/X06 impiden declarar cerrada toda la auditoría. CU-08 y la máquina de estados completa permanecen fuera de este cierre.
