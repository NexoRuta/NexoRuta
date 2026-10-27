# DEC-01 — plazo de validación de prueba

**Estado:** opción B implementada para publicaciones con plazo configurado. La máquina de estados completa sigue abierta; este informe no cierra CU-08, las demás transiciones ni la mensajería transversal. La revisión nativa continúa pendiente.

## 1. Decisión efectiva

`FinJornada` finaliza la hoja y conserva `EntregaPendienteValidacion`; ya no causa `EntregaPendienteValidacion → EntregaSinValidacion`. Se mantiene el resto de D18: cierre con incidencias, conservación de custodia y ausencia de recepciones físicas inventadas.

Cada versión nueva de reglas operativas debe llevar un `PlazoValidacionPruebaMinutos` positivo, separado de `PlazoEstandarMinutos` y `PlazoUrgenteMinutos`. No se fijó duración por defecto. Una versión publicada es inmutable. Una publicación histórica sin el campo se conserva con `NULL`; su vencimiento no se inventa ni se calcula retrospectivamente.

El inicio se fija cuando el servidor acepta por primera vez una declaración válida de entrega física. El plazo vence al alcanzar su instante límite. En consecuencia:

- Evidencia completa recibida por el servidor con `recibidaEnUtc < venceEnUtc` puede producir `EntregaPendienteValidacion → Entregado`, incluso después del cierre de jornada.
- En `recibidaEnUtc >= venceEnUtc`, la evidencia se conserva como hecho verificable, pero no valida automáticamente el envío. El Worker produce la transición a `EntregaSinValidacion`.
- Evidencia tardía no reabre `EntregaSinValidacion`, `Cancelado` u otro estado final; tampoco se crea `Cancelado → Cancelado`.
- Una conciliación física tardía sobre `Cancelado` conserva la conducta existente: hecho, prueba y custodia bajo sus controles; sin vencimiento ni transición de validación.

## 2. Datos y versión

`Envio` conserva por separado:

| Dato | Significado |
|---|---|
| `EntregaFisicaEnUtc` | Instante físico declarado por el dispositivo, normalizado a UTC según las validaciones vigentes. |
| `EntregaFisicaRecibidaEnUtc` | Primera recepción válida aceptada por el servidor. Es el origen del plazo. |
| `PlazoPruebaVenceEnUtc` | Vencimiento persistido: primera recepción del servidor más `PlazoValidacionPruebaMinutos` de la versión asociada al envío. |

El flujo móvil carga `VersionReglasOperativas` por `Envio.VersionReglasId`, no por la publicación vigente del operador. La recepción de evidencia bloquea y vuelve a leer el envío antes de decidir. Los tres instantes no se reinician por replay, evidencia parcial, reenvíos, cierre de jornada, una publicación posterior o reinicios.

Los campos nuevos de `Envio` quedan protegidos por trigger SQL contra reemplazo después del primer hecho físico. La regla de duración tiene restricción `1..525600` minutos —el máximo de duración ya establecido por el modelo— y una publicación nueva sin valor no se acepta. Borradores pueden seguir incompletos. No se cambia una publicación histórica para rellenar el campo.

### Política histórica explícita

- La migración agrega la duración como columna nullable, sin default; las publicaciones existentes permanecen en `NULL`.
- El Worker excluye envíos con `PlazoPruebaVenceEnUtc IS NULL`; no asigna la duración de otra versión ni backfillea una fecha de recepción que no puede demostrarse.
- Para versiones antiguas sin campo, el plazo histórico queda pendiente de política/configuración: no hay expiración automática. En la publicación se muestra el dato como “Sin completar”; en datos, la combinación de duración/versionado y vencimiento nulos permite identificarlo.
- Una copia de borrador conserva el `NULL` hasta que el operador establezca explícitamente la duración. La publicación nueva requiere valor.
- El código actual permite que evidencia completa asociada a una versión histórica sin duración complete la prueba sin corte temporal; queda identificada por la versión `NULL`. No se le asigna una duración ficticia.

## 3. Escritura y concurrencia

El `ProofValidationDeadlineWorker` es un `BackgroundService` registrado para todos los modos de transporte del Worker. Cada ciclo abre scope/DbContext, toma la hora UTC de `TimeProvider` y llama `nexoruta_app.expire_pending_proof_deadlines(now, 100)`. Consulta los vencidos por deadline y procesa por lotes; un lote lleno se continúa enseguida, de otro modo espera 30 segundos. No existe temporizador en memoria por envío ni dependencia de `FinJornada`.

La función opera solo sobre `EntregaPendienteValidacion` con deadline no nulo y `deadline <= now`. Cada `UPDATE` vuelve a comprobar el estado/plazo vigentes y suma la versión. Evidencia usa `SELECT … FOR UPDATE` y recarga el envío; el Worker usa actualización condicional bajo bloqueo PostgreSQL. En el límite, la evidencia no gana por llegar con igualdad: si Worker y evidencia compiten, la operación que toma el bloqueo primero deja una fila coherente, y la posterior evalúa el estado actual. Ninguna puede confirmar una salida incompatible basada en lectura antigua.

El trigger de historia canónica agrega `TransicionEstado` con origen `PlazoValidacionPrueba`, actor `Proceso` / `worker:proof-validation-deadline`, versión y estados. El cambio de envío, versión e historia se escribe dentro de la transacción de la misma sentencia SQL; si falla la historia, la actualización se revierte. No se agrega mensaje outbox, consumidor, webhook ni aviso: no se identificó contrato de evento de negocio existente aplicable a este vencimiento.

### Contexto y privilegios

La función es `SECURITY DEFINER` y pertenece al rol acotado `nexoruta_proof_deadline_fn` (`NOLOGIN`, `NOINHERIT`, `NOSUPERUSER`, `NOBYPASSRLS`); tiene `search_path` fijado. Solo posee `SELECT` y `UPDATE` de las dos columnas de estado/versión en `Envios`, más los privilegios de esquema/funciones necesarios. RLS habilitado y forzado delimita el escaneo de pendientes y la fila/operador de cada actualización. El usuario de Worker tiene `EXECUTE` en esa función, no lectura directa de envíos por este camino ni escritura general de negocio. La identidad/proceso y los GUC de contexto se establecen dentro de la función; la API no envía actor libre.

La integración usa una conexión con login de prueba `NOSUPERUSER NOBYPASSRLS`, miembro de `nexoruta_worker`: la lectura directa de `Envios` devuelve cero filas, mientras que la ejecución de la función puede vencer una fila autorizada. La función no depende de una conexión de superusuario para el comportamiento bajo prueba.

## 4. Cambios concretos

### Backend

- `VersionReglasOperativas`, configuración/validación de dominio y contratos API aceptan y exponen `PlazoValidacionPruebaMinutos`; publicación nueva requiere un valor positivo y publicación existente no se edita.
- `Envio` fija primera recepción/vencimiento y aplica la comparación estricta de evidencia. `EfOperacionesRepartoRepository.Ejecucion` toma la regla asociada al envío, conserva evidencia tras cerrar jornada, bloquea/recarga al recibir prueba y trata la evidencia tardía como hecho sin transición.
- `ProofValidationDeadlineWorker` procesa vencimientos persistidos con `TimeProvider` y acceso de base restringido. El registro es independiente de RabbitMQ, Kafka y Push; no agrega broker ni evento.
- Se agregó el contrato de función a `RlsSqlFunctionContract`.

### Migraciones aditivas

- `20261025233714_AddProofValidationDeadline`: columna nullable de regla, check de duración positiva/techo existente y guard de publicación para impedir publicar un borrador nuevo sin plazo.
- `20261025234203_PersistShipmentProofDeadline`: timestamps del envío, restricciones/índice de vencimiento, guardas de inmutabilidad, rol de función, políticas RLS y función de expiración.
- Snapshot de EF actualizado. No se ejecutaron migraciones en bases compartidas ni de producción.

### Backoffice y contrato

El formulario del borrador incluye el campo como duración editable; la vista previa de publicación y el detalle histórico lo muestran. No se agregó valor inicial. `PlazoValidacionPruebaMinutos` se incorporó al DTO ApiClient, al esquema OpenAPI y a `frontend/contracts/nexoruta.openapi.json`; el borrador puede expresar `null`, pero una publicación nueva no. La lectura de publicaciones antiguas muestra el dato faltante sin cambiarlo.

## 5. Verificación ejecutada

Destino de Docker confirmado en solo lectura:

```text
docker context inspect desktop-linux --format '{{.Endpoints.docker.Host}}'
npipe:////./pipe/dockerDesktopLinuxEngine
```

Los tests de integración usan `PostgresFixture`/Testcontainers con PostgreSQL efímero y bases separadas por test. Las pruebas del Worker crean un login restringido sin `BYPASSRLS`.

| Verificación | Comando / filtro | Resultado y evidencia |
|---|---|---|
| Lógica de reglas y regresión de Cancelado | `dotnet test backend/tests/NexoRuta.UnitTests/NexoRuta.UnitTests.csproj --no-restore --filter "FullyQualifiedName~EnvioCancellationRulesTests|FullyQualifiedName~VersionReglasOperativasTests"` | 34/34. Incluye límites/validación de duración y reglas de cancelación existentes. |
| Pruebas de plazo / Worker | `dotnet test backend/tests/NexoRuta.IntegrationTests/NexoRuta.IntegrationTests.csproj --no-restore --filter "FullyQualifiedName~FinJornadaNoBloquea|FullyQualifiedName~EvidenciaEnElLimite|FullyQualifiedName~FalloAlEscribirHistoria|FullyQualifiedName~VersionHistoricaSinPlazo|FullyQualifiedName~HostedWorkerProcesaVencimiento"` | 5/5. Reloj manual, primera recepción y vencimiento estables, evidencia tras cierre y antes del límite, carrera de evidencia con dos barridos restringidos, límite y evidencia posterior, replay sin duplicar, versión histórica nula, actor de proceso y rollback si falla historia. Worker hosted con conexión restringida cambia el estado. |
| Reglas HTTP | `dotnet test backend/tests/NexoRuta.IntegrationTests/NexoRuta.IntegrationTests.csproj --no-restore --filter "FullyQualifiedName~ReglasOperativasHttpTests"` | 3/3. Borrador incompleto, rechazo de plazo cero, publicación con 60 minutos explícitos, copia de borrador y publicación histórica conservada en 60 tras editar la copia a 90. Ejecuta API TestServer y persistencia real. |
| Reparto y cancelación en el recorrido HTTP | `dotnet test backend/tests/NexoRuta.IntegrationTests/NexoRuta.IntegrationTests.csproj --no-restore --filter "FullyQualifiedName~OperacionesRepartoHttpTests"` | 25/25. Incluye cerrar la jornada, prueba tardía sobre cancelación, conciliación y carreras existentes. |
| Reimportación de CU-07 | `dotnet test backend/tests/NexoRuta.IntegrationTests/NexoRuta.IntegrationTests.csproj --no-restore --filter "FullyQualifiedName~ShipmentCsvImportHttpTests"` | 14/14. No regresión para altas/reimportaciones, incluidos identidad cancelada y conciliación tardía. |
| Cancelación pública | `dotnet test backend/tests/NexoRuta.IntegrationTests/NexoRuta.IntegrationTests.csproj --no-restore --filter "FullyQualifiedName~PublicCancellationTests"` | 18/18. El cambio de plazo no modificó el contrato público de cancelación. |
| Migración de historia sobre esquema histórico de prueba | `dotnet test backend/tests/NexoRuta.IntegrationTests/NexoRuta.IntegrationTests.csproj --no-restore --filter "FullyQualifiedName~MigrationMarksTheCutoverAndBackfillsOnlyAuditedCancellations"` | 1/1 después de ajustar el fixture para que la versión actual del modelo pueda sembrar su columna nullable sobre el esquema anterior aislado. La migración de historia sigue siendo la operación bajo prueba; las migraciones de plazo se aplican y ejercitan en los fixtures normales. |
| Edición/lectura Backoffice y contratos del cliente | `dotnet test frontend/tests/NexoRuta.ApiClient.Tests/NexoRuta.ApiClient.Tests.csproj --no-restore --filter "FullyQualifiedName~ReglasOperativasApiClientTests|FullyQualifiedName~OperationalRulesDraftKeepsIncompleteValues|FullyQualifiedName~OperationalRulesBlankDraftKeepsNullDurations|FullyQualifiedName~OperationalRulesPublishRequiresConfirmation|FullyQualifiedName~OperationalRulesPublishExplainsIncompleteSections|FullyQualifiedName~OperationalRulesHistoryIsPagedAndPublicationDetailIsReadonly"` | 7/7. Incluye campos y unidades del formulario, borrador vacío, publicación/detalle histórico. |
| Exportación real de OpenAPI desde API | `$env:NEXORUTA_OPENAPI_EXPORT_PATH=(Resolve-Path -LiteralPath 'frontend/contracts/nexoruta.openapi.json').Path; dotnet test backend/tests/NexoRuta.IntegrationTests/NexoRuta.IntegrationTests.csproj --no-restore --filter "FullyQualifiedName~OpenApiContainsTypedRulesRoutesAndExportsTheGeneratedDocument"` | 1/1. La prueba obtuvo `/openapi/v1.json` desde TestServer y exportó el documento generado al contrato versionado. |
| Validación del contrato OpenAPI de frontend | `dotnet test frontend/tests/NexoRuta.ApiClient.Tests/NexoRuta.ApiClient.Tests.csproj --no-restore --filter "FullyQualifiedName~OperationalRulesContractContainsVersionedDraftPublicationAndValidationSchemas"` | 1/1. Confirma el campo requerido y nullable del borrador y el rango 1..525600 en el contrato versionado. |
| Build Backoffice | `dotnet build frontend/src/NexoRuta.Backoffice/NexoRuta.Backoffice.csproj --no-restore --verbosity minimal` | Compilación correcta, 0 advertencias / 0 errores en la ejecución repetida. |

Una primera ejecución combinada de filtros de varias clases falló en 25 casos antes de ejecutar sus aserciones de negocio: Testcontainers no pudo iniciar PostgreSQL efímero (`pg_ctl: server did not start in time`, `ContainerNotRunningException`). La prueba de migración falló inicialmente por el modelo actual escribiendo campos nuevos sobre un esquema histórico anterior. El fixture aislado se adaptó y la migración pasó sola; después cada suite pertinente se ejecutó por separado y pasó con PostgreSQL efímero. No se atribuye esa primera falla a producción.

## 6. Límites y pendientes

- No se hizo revisión visual en navegador: no hay Playwright/browser instalado en el checkout o en `PATH`, y no se instalaron dependencias. Build y tests de Razor/ApiClient no sustituyen esa revisión visual.
- La prueba ejecuta el `ProofValidationDeadlineWorker` real como `BackgroundService` contra PostgreSQL y el mismo rol restringido; no se desplegó ni arrancó un proceso de Worker independiente. La repetición con una nueva conexión prueba replay/reinicio durable del barrido, pero no una prueba de caída de proceso/host real.
- No se probó un broker ni se generó evento outbox al vencer: el vencimiento no tiene contrato de mensajería existente aplicable, así que no se inventó uno. Webhooks/avisos permanecen fuera de este bloque.
- Para publicaciones históricas `NULL` no hay duración demostrable: esos envíos no vencen automáticamente hasta que exista una política explícita. No se cambió `EntregaSinValidacion` ni se implementó una salida posterior.
- Las transiciones restantes, extravío, política de intentos/reprogramación y agregación multi-bulto siguen pendientes conforme a los informes 11/12. CU-08 es obligatorio y separado. El estado de revisión nativa sigue pendiente; este trabajo no es aprobación.
