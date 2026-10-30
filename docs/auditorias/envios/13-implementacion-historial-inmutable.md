# Implementación de historia inmutable de envíos

El backend ahora mantiene una historia canónica en PostgreSQL para creaciones, cambios de estado persistidos y hechos del envío sin transición. La captura vive en la base de datos, comparte la transacción del escritor y no altera las reglas actuales de estado. No completa la máquina de estados, CU-08 ni los pendientes transversales de mensajería.

**Corte:** 26/10/2026 · **Rama observada:** `feature/cu07` · **Revisión nativa:** pendiente, sin aprobación.

## Recorrido breve

1. Los escritores existentes persisten el agregado `Envios` dentro de su transacción actual.
2. El trigger `shipment_history_capture` registra el `OLD`/`NEW` realmente persistido y lee actor, origen, correlación y fecha desde GUC transaction-local establecidos por `RlsTransaction`.
3. Estado, versión, evento canónico, auditoría especializada y los mensajes outbox que ya produce esa operación confirman o revierten juntos.

## Modelo y semántica

| Tipo | Significado | Datos de estado/orden |
|---|---|---|
| `Creacion` | Alta nueva confirmada, inicial `Admitido`, versión 0. | Sin estado anterior. No se emite al reimportar una identidad existente. |
| `TransicionEstado` | Cambio de estado realmente escrito en `Envios`. | Estado anterior/nuevo distintos y par de versiones persistidas. |
| `Hecho` | Hecho del agregado confirmado con estado comercial sin cambio, por ejemplo la entrega física tardía conciliada sobre `Cancelado`. | Estado observado, versión previa/nueva y código del hecho; nunca `Cancelado → Cancelado`. |
| `EstadoObservadoInicio` | Fotografía del estado al habilitar la historia para un envío preexistente. | Estado actual, versión observada y `OcurridaEnUtc = NULL`; no finge creación, actor humano ni cronología anterior. |

`EnvioEvento` guarda operador, comercio, envío, tipo, estados, versiones, versión de reglas fijada al envío, actor tipado, origen, correlación, operación móvil cuando aplica, fecha del hecho y fecha de registro. No copia fotografías, códigos privados ni payloads completos. La evidencia autorizada permanece en `PruebaEntrega`, `EvidenciasReparto` y `OperacionJornada`; la fila del hecho se correlaciona con la operación que lo registró.

La referencia de reglas del envío es inmutable en el dominio (`Envio.VersionReglasId` tiene setter privado); por eso la historia usa la versión asociada al agregado y no la publicación vigente al consultar.

## Captura de escritores actuales

La captura en trigger de base de datos evita que un camino EF o una función SQL olvide llamar a un escritor de historia:

| Camino | Escritura existente | Metadatos de historia |
|---|---|---|
| Alta individual | `EfEnviosRepository.GuardarAsync` → `CrearEnBaseAsync` → `create_shipment`. | `AltaIndividual`, envío creado y contexto autenticado. |
| Alta CSV | `EfEnviosRepository.GuardarImportadosAsync` → el mismo `CrearEnBaseAsync`. | `Importacion`; solo se dispara para envíos realmente insertados. La ruta idempotente de `YaExistente`/duplicado no inserta otro envío, evento ni outbox. |
| Recepción, carga, jornada, entrega, intento y cambios existentes | `EfOperacionesRepartoRepository` / `.Ejecucion.cs` y repositorios EF de rutas; dominio `Envio.CambiarEstado` o `ConciliarEntregaFisica`, seguido de `SaveChanges`. | Trigger sobre el cambio de estado, versión o `EntregaFisicaEnUtc`; operaciones móviles incluyen `OperacionJornadaId`, `OrigenId` y `OcurridaEnUtc`. |
| Cancelación autenticada | `EfCancelacionesEnvioRepository` → `nexoruta_app.cancel_shipment` y `CancelacionesEnvio`. | La función existente actualiza `Envios`; el trigger agrega la transición vinculada por `CancelacionEnvioId` al registro especializado. Una repetición idempotente no vuelve a cambiar la fila ni duplica historia. |
| Cancelación pública | `CancelacionPublica.ConfirmarAsync` → función existente de confirmación → `cancel_shipment`. | Actor `Publico` y referencia a la autorización pública, nunca el código privado. La auditoría especializada sigue siendo la fuente del motivo/autorización. |
| Workers | No se encontró un worker actual que escriba estado de `Envios`. | `RlsWorkerContext` establece identidad de proceso y envío para futuras escrituras. Ese camino queda pendiente de una prueba específica cuando se incorpore un worker escritor; no se declara verificado por configuración sola. |

El trigger observa escrituras finales, no estados intermedios que el dominio cambia y revierte antes de `SaveChanges`. Los escritores incluidos no incrementan `Envio.Version` por otros datos internos no relacionados. La evidencia adicional de una entrega permanece en sus tablas especializadas; la historia no se convierte en una copia por cada archivo o campo de prueba.

## Persistencia, RLS y funciones

Implementación aditiva en `EnvioEventos`:

- FKs compuestas vinculan envío-comercio, envío-operador y versión de reglas; la referencia a `CancelacionesEnvio` usa FK diferida para conservar el orden de la función existente (actualiza envío antes de insertar la auditoría).
- Constraints validan la forma de cada tipo. Los índices parciales aseguran una creación y un marcador de corte por envío, una fila por auditoría de cancelación y correlación de transición por envío/par de versiones. Los hechos se deduplican por su origen/código, no solo por versión.
- RLS está `ENABLE` y `FORCE`. La política de lectura API filtra por comercio autenticado u operador autenticado. El test con conexión `NOSUPERUSER NOBYPASSRLS` verificó dos comercios y dos operadores distintos.
- `nexoruta_api` tiene lectura pero no INSERT/UPDATE/DELETE/TRUNCATE. `nexoruta_worker` tampoco recibe escritura directa. `nexoruta_history_fn` es `NOLOGIN`, `NOINHERIT`, sin superuser, creación de roles/bases, replicación ni `BYPASSRLS`, y sin miembros. Solo tiene los privilegios mínimos usados por los triggers; no puede actualizar, borrar ni truncar la historia.
- Las funciones `capture_shipment_history` y `capture_cancellation_history` son `SECURITY DEFINER`, propiedad del rol restringido y con `search_path = pg_catalog, nexoruta_app`. No tienen permiso `EXECUTE` público/API; se invocan únicamente mediante triggers.
- Un trigger append-only rechaza UPDATE, DELETE y TRUNCATE. No es una frontera contra el superusuario/administrador de PostgreSQL, que conserva capacidad técnica de alterar objetos; el control protege los caminos runtime y operaciones ordinarias.
- La API no recibe actor ni origen libre del cliente. El middleware establece contexto transaccional autenticado; escritores móviles agregan ID y hora offline validados. Solicitudes sin contexto confiable fallan en el trigger.

No se agregó una ruta HTTP ni una pantalla para consultar la historia: este bloque implementa almacenamiento y aislamiento RLS, no un contrato de lectura pública. Cualquier proyección futura debe aplicar los mismos filtros sin exponer payloads o datos personales.

## Atomicidad e idempotencia

`RlsTransactionMiddleware` abre la transacción de solicitud y los repositorios participan con `BeginOrJoinAsync`; el contexto de historia se configura con `set_config(..., true)`, por lo que no queda pegado a una conexión reutilizada. Los triggers insertan en la misma conexión y transacción que modifica `Envios`.

En altas, los dos mensajes outbox actuales (`GenerarSeguimiento` y `EnvioCreado`) se conservan en la transacción de creación. En cancelación siguen la función/auditoría y outbox que ya existían. La historia no crea un nuevo mensaje, broker, consumidor ni aviso.

Las restricciones únicas son defensa final. Idempotencia conservada por camino:

- Alta/importación: solo el insert real en `Envios` origina `Creacion`; `YaExistente` y reimportación no tocan historia ni outbox.
- Cancelación: la función existente reconoce el estado/auditoría ya aplicada antes de otra transición; el ID de auditoría es la referencia canónica única.
- Operación offline: `OperacionJornada.Id` y su respuesta almacenada reconocen replay antes de ejecutar escrituras; los hechos correlacionan esa misma operación. La historia no inventa una transición a partir de un reintento.

Una violación al insertar historia invalida la operación completa. Las pruebas forzaron error al insertar `Creacion` y una `TransicionEstado`, y error posterior al insertar outbox; verificaron que no quedan envío/estado, bulto, auditoría de cancelación, evento ni mensajes huérfanos.

## Migración y lectura honesta del corte

Migración nueva: `20261025222429_AddCanonicalShipmentHistory` y snapshot EF actualizado.

- Cada envío previo recibe `EstadoObservadoInicio` con su estado/versión en el corte, actor `Migracion`, sin usuario y sin `OcurridaEnUtc`.
- Solo las cancelaciones respaldadas por `CancelacionesEnvio` reciben una transición histórica `Backfill`, vinculada por ID de auditoría, con versiones, actor/procedencia y fecha de cancelación comprobables. No se reconstruyen estados intermedios ni se generan outbox/avisos.
- `ON CONFLICT` sobre claves parciales evita duplicar marcadores y cancelaciones si la inicialización autorizada se repite.
- Para leer el pasado sin inventar secuencia, presentar las cancelaciones `Procedencia = Backfill` como evidencia histórica proveniente de auditoría y el `EstadoObservadoInicio` como límite de observación actual. Si ambos muestran `Cancelado`, no ordenarlos como una cadena de transiciones y nunca convertirlos en `Cancelado → Cancelado`. El resto del pasado sin auditoría durable se desconoce.
- La FK diferida de cancelación creó eventos pendientes durante el backfill; PostgreSQL no permite el posterior `ALTER TABLE` con esos eventos pendientes. La migración ahora ejecuta `SET CONSTRAINTS ... IMMEDIATE` tras el backfill para validarlos antes de instalar RLS.
- `Down` toma bloqueo exclusivo y solo permite eliminar el esquema cuando no hay filas de historia; con eventos falla `55000` para evitar destruir evidencia. Revoca privilegios locales, pero no elimina el rol cluster-wide: PostgreSQL lo comparte entre bases y puede seguir referenciado por otros catálogos. El rol permanece `NOLOGIN` y sin permisos en la base revertida.

## Evidencia ejecutada

Docker fue confirmado de forma read-only: contexto `desktop-linux`, endpoint `npipe:////./pipe/dockerDesktopLinuxEngine`; Testcontainers reportó Docker Desktop y PostgreSQL 18/PostGIS. `PostgresFixture` crea un contenedor y bases aisladas por prueba, verifica nombre de DB/usuario/versión y las elimina al terminar el contenedor. No se utilizó Compose ni una base compartida.

| Comando o filtro | Resultado | Evidencia/alcance |
|---|---|---|
| `dotnet test tests/NexoRuta.IntegrationTests/NexoRuta.IntegrationTests.csproj --no-restore --filter "FullyQualifiedName~EnvioEventsHttpTests|FullyQualifiedName~EnvioHistoryMigrationTests|FullyQualifiedName~ShipmentCsvImportHttpTests|FullyQualifiedName~CancelacionPushTests|FullyQualifiedName~PublicCancellationTests|FullyQualifiedName~ConciliacionEntregaHttpTests|FullyQualifiedName~OperacionesRepartoHttpTests|FullyQualifiedName~RlsRestrictedHttpFlowTests"` | 58/58 pasó. | TestServer + PostgreSQL efímero; importación, cancelación autenticada/pública, Reparto tardío/replay, outbox y RLS. Este resultado incluye la nueva prueba de separación de historia por comercio/operador y rollback de cancelación al fallar historia. Build de Domain/Application/Infrastructure/Worker/API/tests ejecutado por el comando. |
| Filtro `HistoryAndLaterOutboxFailuresRollbackTheWholeShipmentCreation` | 1/1 pasó. | Fallo de historia al crear y cancelar; fallo posterior de outbox; rollback de envío, hijos, auditoría, historia y outbox. |
| Filtro `ShipmentHistoryRlsSeparatesCommerceAndOperatorRows` | 1/1 pasó. | Cuatro contextos con rol API restringido: dos comercios y dos operadores ven solo el envío propio. |
| Filtro `RestrictedCommerceHttpCanCreateShipmentAndSeeItAfterChosenOperatorSuspension` | 1/1 pasó. | Verificó owner `SECURITY DEFINER`, `search_path`, atributos/membresía del rol, RLS forzada y privilegios API/worker/history_fn; UPDATE/DELETE/TRUNCATE rechazados. |
| Filtro `MigrationMarksTheCutoverAndBackfillsOnlyAuditedCancellations` | 1/1 pasó. | 32 envíos, una cancelación auditada; corte/backfill, estado inicial no inventado y outbox sin cambios. Migración: **343 ms** dentro de un contenedor efímero PostgreSQL 18/PostGIS. |
| Filtro `MigracionPuedeRevertirseSinHechosPublicosYVolverAAplicarse` | 1/1 pasó. | Down/up sin filas, sin migración de modelo pendiente; otra prueba de cancelación confirma que Down no borra historia con datos. |

Las pruebas unitarias completas no se ejecutaron en este bloque porque el comportamiento nuevo está en SQL/RLS/transacciones y las verificaciones pertinentes fueron de integración real. No se levantaron brokers: no se agregó mensajería; se comprobaron las filas outbox en la misma base, no publicación/consumo real. No hay UI ni Kestrel visual que verificar para almacenamiento interno. El benchmark representa 32 filas, no garantiza duración/lock para producción o millones de envíos.

## Pendientes explícitos

- La revisión nativa permanece pendiente; esta revisión manual, compilación y pruebas no constituyen aprobación.
- No se implementaron nuevas transiciones, plazos, reprogramación adicional, extravío operativo ni multibulto. La máquina sigue parcial.
- No existe una lectura API/UI de la historia en este bloque.
- No hay actualmente worker escritor de estado; su contexto existe, pero requiere prueba de integración cuando se agregue uno.
- CU-08 sigue obligatorio y separado; outbox/brokers transversales no se declaran completos.
- El siguiente bloqueo funcional para continuar con los estados es DEC-01 del informe 12: resolver el conflicto entre vencimiento temporal de `EntregaPendienteValidacion` en el diagrama y cierre de jornada D18, incluyendo el instante de inicio y las operaciones offline tardías. No se eligió duración ni política por inferencia.
