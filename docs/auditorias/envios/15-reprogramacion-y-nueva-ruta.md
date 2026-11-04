# DEC-04 — Reprogramación y nueva ruta

**Estado:** opción A implementada y verificada para el flujo servidor/Backoffice con el modelo actual de un bulto por envío.  
**Corte:** 25/10/2026.  
**Alcance:** exigir `NoEntregado → Reprogramado → AsignadoRuta → EnTransito` antes de otro intento; no completar DEC-05–08, CU-08 ni el cliente móvil offline.  
**Revisión nativa:** sigue pendiente; esta implementación y sus pruebas no son aprobación nativa.

> **Actualización posterior:** DEC-05, que al corte de este informe seguía pendiente, quedó resuelta e implementada en opción A por el bloque 16. Este informe conserva su corte histórico; ver [`16-decision-operativa-devolucion.md`](16-decision-operativa-devolucion.md). DEC-06/07, CU-08 y cliente offline siguen pendientes.

## Resultado

Un intento fallido deja el envío en `NoEntregado`. El mismo envío no puede volver a `EnTransito` ni recibir otra tentativa sobre la parada fallida. Un operador autorizado debe ejecutar la acción explícita de reprogramación; luego Backoffice debe asignar el envío a una ruta nueva elegible. Solo después de despacho, carga y confirmación de salida puede ejecutarse otra tentativa.

La reprogramación no cuenta como intento, no modifica el máximo ni la próxima elegibilidad, no cambia `VersionReglasId` y no mueve la custodia. La custodia vuelve a depósito únicamente cuando se registra la recepción física existente. `IniciarAutomaticamente` sigue iniciando devolución al agotarse los intentos; con `DecisionOperativa`, el bloque 16 agrega el inicio manual autorizado de devolución solo después del agotamiento, sin reprogramar ni mover custodia.

## Comportamiento y límites

| Regla | Comportamiento implementado |
|---|---|
| Reintento normal | `IntentoFallido` y `EntregaFisica` de una nueva operación requieren estado vigente `EnTransito`, parada activa y custodia de la ruta. El dominio rechaza `NoEntregado → EnTransito`. |
| Reprogramar | `POST /api/envios/{id}/reprogramacion` requiere actor operador con `envios.gestionar`, versión actual, `NoEntregado`, al menos un intento aplicado y un intento todavía disponible según la versión fijada al envío. |
| Ruta nueva | `POST /api/rutas` reutiliza la planificación existente, que admite `Reprogramado` y conserva confirmación de destino, elegibilidad, disponibilidad y capacidad. Despacho continúa exigiendo custodia física en depósito y carga normal. No se relajaron las precondiciones. |
| Máximo e intervalo | El total se deriva de las operaciones `IntentoFallido` aplicadas; el último instante es el `OcurridaEn` UTC guardado en la operación, conforme a CU-04. La frontera permite ejecutar exactamente en `último intento + intervalo`; antes se rechaza. Se consultan máximo e intervalo de `Envio.VersionReglasId`, no una publicación posterior. |
| Reprogramación sin efectos físicos | Suspende la parada anterior y persiste `NoEntregado → Reprogramado`; no cambia `Bulto.Custodia`, no simula rendición ni recepción y no crea intento. |
| Replay / comando nuevo | Reenviar el mismo UUID devuelve el resultado almacenado sin nueva operación, historia ni outbox. Un UUID distinto de la ruta anterior no evita la comprobación del estado y se rechaza. Una entrega física tardía verificable conserva el camino especializado de conciliación y su evidencia; no se transforma en una tentativa nueva. |
| Agotamiento | Con `IniciarAutomaticamente`, la última falla sigue cambiando a `EnDevolucion` y suspendiendo la parada. Con `DecisionOperativa`, no se ofrece reprogramación al agotarse el máximo; DEC-05 opción A permite al actor autorizado iniciar devolución con motivo, manteniendo custodia. Ver bloque 16. |
| Rutas activas (DEC-07) | Se excluyó `NoEntregado` de la reasignación directa. Se conservaron las reasignaciones desde `AsignadoRuta`/`EnTransito`; su revisión no forma parte de este bloque. |

### Historial, concurrencia y mensajería

La operación reutiliza `RlsTransactionMiddleware`, `BeginOrJoinAsync`, el bloqueo existente por operador, la concurrencia por versión del envío/ruta y el trigger de historia inmutable. La transición se registra con origen `ReprogramacionEnvio` y correlación propia. El cambio del envío, la suspensión de la parada, el aviso de reasignación cuando la ruta sigue activa, el outbox existente y la fila de historia participan de la misma transacción. No se creó migración, broker, evento de dominio/outbox nuevo ni movimiento de custodia.

La reprogramación concurrente con cancelación queda serializada por el bloqueo de estado/versión: solo la operación con versión vigente puede ganar; si gana cancelación, `Cancelado` permanece terminal. La planificación concurrente puede fallar con conflicto o continuar tras la reprogramación; en ningún caso se confirma una parada activa duplicada. Los errores de persistencia durante la captura de historia revierten también el estado, la parada y el outbox.

## Componentes modificados

### Backend

- `backend/src/NexoRuta.Domain/Envios/Envio.cs`: elimina el atajo `NoEntregado → EnTransito`; conserva las transiciones aprobadas de cancelación y los demás estados ajenos a DEC-04.
- `backend/src/NexoRuta.Infrastructure/Reparto/ResumenIntentosEntrega.cs`: resume intentos aplicados y calcula la elegibilidad usando `OcurridaEn` y el intervalo de la versión del envío.
- `backend/src/NexoRuta.Infrastructure/Reparto/EfOperacionesRepartoRepository.Ejecucion.cs`: exige `EnTransito` para nueva entrega/intento; no vuelve a transicionar desde `NoEntregado`; mantiene la custodia de NoEntregado al rendirlo y preserva hechos físicos tardíos.
- `backend/src/NexoRuta.Infrastructure/Reparto/EfRutasRepository.Reasignaciones.cs`: agrega `ReprogramarAsync`, suspende la parada anterior y reutiliza historia/outbox/transacción existentes; impide reasignación directa desde NoEntregado.
- `backend/src/NexoRuta.Infrastructure/Reparto/EfRutasRepository.cs`: publica cantidad de intentos y próxima elegibilidad en paradas; planificación continúa usando sus guardas actuales.
- `backend/src/NexoRuta.Application/Reparto/Dtos/`, `Repositories/IRutasRepository.cs` y `UseCases/GestionarRutasUseCase.cs`: añade contratos de aplicación específicos de reprogramación, no un setter genérico de estado.
- `backend/src/NexoRuta.Api/Features/Reparto/Controllers/RutasController.cs` y `Contracts/ReprogramarEnvioRequest.cs`, `ReprogramacionEnvioResponse.cs`: endpoint con actor/política existente, versión y resultado tipado.
- Sin migración: los intentos, eventos, outbox, estados y versiones de ruta existentes bastan para implementar esta acción.

### Frontend y contrato

- `frontend/src/NexoRuta.ApiClient/Features/Reparto/`: agrega request, response y cliente autenticado para la acción; DTO de parada expone intentos y elegibilidad.
- `frontend/src/NexoRuta.Backoffice/Features/Reparto/Pages/RutasModel.cs` y `Pages/Rutas.cshtml`: muestra el resumen de intentos, hora de elegibilidad en la zona de ruta, acción disponible con intentos restantes y explicación al agotarse. El formulario impide doble envío con el patrón `data-single-submit` existente.
- `frontend/contracts/nexoruta.openapi.json`: regenerado desde el documento OpenAPI servido por la API; registra ruta, DTOs y respuestas. `OpenApiContractTests` fija el contrato de versión y resultado.
- No se modificó Mobile ni se implementó almacenamiento/sync offline.

## Evidencia de verificación

Docker se confirmó en solo lectura antes de los fixtures: `docker context inspect desktop-linux --format '{{.Endpoints.docker.Host}}'` devolvió `npipe:////./pipe/dockerDesktopLinuxEngine`; `docker info --format '{{.ServerVersion}} {{.OperatingSystem}}'` informó Docker Desktop 28.0.4. Los tests de integración usan `PostgresFixture` con bases/roles efímeros; el API de los escenarios DEC-04 se conecta con el rol restringido del fixture (`NOBYPASSRLS`), no con superusuario.

| Check | Comando / escenario | Resultado | Qué demuestra y límite |
|---|---|---:|---|
| Integración Reparto | Desde `backend`: `dotnet test tests/NexoRuta.IntegrationTests/NexoRuta.IntegrationTests.csproj --no-restore --filter FullyQualifiedName~NexoRuta.IntegrationTests.Reparto.OperacionesRepartoHttpTests --logger "console;verbosity=minimal"` | **33/33** | PostgreSQL real efímero; incluye mismo UUID replay, nuevo UUID sobre parada fallida, recorrido de reprogramación y ruta nueva, contador/intervalo, agotamiento, carreras reprogramar-cancelar, reprogramar-planificar y agotamiento automático contra una reprogramación obsoleta, y fallo forzado del insert de historia con rollback. El rol HTTP está restringido; no sustituye pruebas multi-bulto ni cliente offline. |
| Rollback de historia | `FalloAlRegistrarHistoriaRevierteEstadoParadaYOutboxDeReprogramacion` dentro del filtro anterior | **1/1** | Trigger de prueba provoca error al insertar `EnvioEventos`; se verifica que envío, parada activa, aviso e outbox no queden parcialmente confirmados. TestServer propaga la excepción de persistencia; no se presenta como un código HTTP de negocio. |
| Navegador real | Desde `backend`: `dotnet test tests/NexoRuta.IntegrationTests/NexoRuta.IntegrationTests.csproj --no-restore --filter FullyQualifiedName~BackofficeBrowserReprogramsFailedDeliveryAndShowsRuleBoundEligibility --logger "console;verbosity=minimal"` | **1/1** | Kestrel real para API y Backoffice, Chromium cacheado vía CDP y PostgreSQL efímero con conexión API restringida. Verifica texto y elegibilidad, click de reprogramación, persistencia/historia, foco de teclado y ausencia de overflow a 320 px; capturas temporales se eliminan. No recorre la creación de otra ruta desde el navegador. |
| Regresiones cancelación/DEC-01 | Filtro de `CancelacionConcurrenteNoDeshaceEntregaFisicaNiExigeRendirla`, `CancelacionConcurrenteConRecepcionDeDevolucionNuncaReactivaCancelado`, `EnviosNuevosUsanLaPublicacionParaValidarPruebaOIniciarDevolucion` y `EvidenciaCifradaEsInmutableYCompletaLaPruebaAutomaticamente` | **8/8** | Mantiene terminalidad, conciliación física, política automática de agotamiento y plazo de prueba. PostgreSQL efímero/TestServer; no es el test parametrizado completo de todos los estados. |
| Dominio / terminalidad | Desde `backend`: `dotnet test tests/NexoRuta.UnitTests/NexoRuta.UnitTests.csproj --no-restore --filter FullyQualifiedName~EnvioCancellationRulesTests --logger "console;verbosity=minimal"` | **30/30** | Incluye la nueva aserción de que NoEntregado no puede volver a EnTransito y sí puede entrar a Reprogramado; conserva la matriz terminal de Cancelado. |
| ApiClient/OpenAPI/UI | Desde `frontend`: `dotnet test tests/NexoRuta.ApiClient.Tests/NexoRuta.ApiClient.Tests.csproj --no-restore --filter "FullyQualifiedName~ReprogrammingEndpointUsesVersionedBusinessActionContract|FullyQualifiedName~RutasSoloOfreceReprogramacionExplicitaConIntentosDisponibles|FullyQualifiedName~RutasNoOfreceReprogramacionCuandoLosIntentosEstanAgotados" --logger "console;verbosity=minimal"` | **3/3** | Snapshot y UI ocultan acción cuando se agota el máximo, y envían versión/identidad correctas. |
| Exportación OpenAPI | Desde `backend`, `NEXORUTA_OPENAPI_EXPORT_PATH` configurado al snapshot versionado y filtro `GeneratedOpenApiIncludesTarifarioRoutesAndExportsVersionedContractOnRequest` | **1/1** | Contrato generado por la API real de la prueba; no editado manualmente. |
| Build Backoffice | Desde `frontend`: `dotnet build src/NexoRuta.Backoffice/NexoRuta.Backoffice.csproj --no-restore` | **0 warnings / 0 errors** | Compila componentes afectados; no es prueba funcional por sí sola. |

### Check de regresión que no pudo completar su fixture

También se ejecutó un filtro que incluía `CancelacionAutenticadaRespetaLaMatrizDeEstados`. De 18 casos combinados, 7 pasaron y 11 fallaron **antes de invocar la cancelación**: el fixture modifica `Envios.Estado` directamente con `ExecuteUpdate` sin avanzar `Version`, y para `EntregaPendienteValidacion` tampoco configura `EntregaFisicaRecibidaEnUtc`; los guardas de base rechazan esos datos (`Shipment state or facts must advance the shipment version` / `A physical-delivery declaration requires its first server receipt time`). No se cambió la prueba para aceptar el comportamiento incorrecto ni se atribuye el fallo a DEC-04. La matriz autenticada completa queda como limitación pendiente de reparar en su fixture y reejecutar; los escenarios de cancelación y concurrencia listados arriba sí pasaron.

## Pendientes y límites

- **DEC-05 (reemplazado por bloque 16):** actor, permiso y acción ya quedaron definidos e implementados como opción A; esta línea describe únicamente el estado al cierre histórico del bloque 15.
- **DEC-06:** definir quién confirma extravío, evidencia y custodia; ninguna arista a `Extraviado` se agregó.
- **DEC-07:** revisar por separado las reasignaciones activas desde `AsignadoRuta`/`EnTransito` y otras salidas no dibujadas; este bloque solo quitó el atajo desde `NoEntregado`.
- **DEC-08 / CU-08:** el flujo sigue demostrado para un bulto por envío. La recepción, rendición, capacidad y cierre con varios bultos/discrepancias no se certifican.
- **CU-24 / cliente offline:** el servidor deduplica/rechaza operaciones por identidad, versión y ruta, pero el cliente MAUI offline no se implementó ni verificó.
- **Cancelación:** la matriz terminal ya quedó verificada en el seguimiento de este informe (12/12 y 36/36); se corrigió la preparación del fixture, no la implementación de cancelación.
- **Mensajería transversal:** se reutiliza el outbox de aviso existente cuando aplica. No se verificó publicación/consumo de brokers ni se declaran nuevos avisos/webhooks.
- **Revisión nativa:** pendiente; este informe no presenta aprobación.

**Risk:** item 1 (estado e historial persistidos), item 2 (autorización y controles del servidor) e item 4 (carreras y orden transaccional).

## Seguimiento — regresión completa de cancelación autenticada (25/10/2026)

### Diagnóstico reproducido y causa

Se reprodujo el filtro inicial:

    dotnet test tests/NexoRuta.IntegrationTests/NexoRuta.IntegrationTests.csproj --no-restore --filter FullyQualifiedName~CancelacionAutenticadaRespetaLaMatrizDeEstados --logger "console;verbosity=normal"

El caso parametrizado contiene los doce estados de la matriz. La preparación partía de una ruta ya cargada (envío EnTransito) y usaba ExecuteUpdateAsync para escribir el estado objetivo y, solo en los estados físicos, EntregaFisicaEnUtc. El endpoint todavía no se había llamado cuando fallaba la escritura en CancelacionPushTests.cs.

- **Ocho filas sin hecho físico** — Admitido, EnDeposito, AsignadoRuta, NoEntregado, Reprogramado, EnDevolucion, Devuelto y Extraviado — fallaban por no avanzar Envios.Version: PostgreSQL rechazaba la actualización con SQLSTATE 23514, “Shipment state or facts must advance the shipment version”.
- **Tres filas con declaración física** — Entregado, EntregaPendienteValidacion y EntregaSinValidacion — no establecían EntregaFisicaRecibidaEnUtc; PostgreSQL rechazaba la preparación con SQLSTATE 23514, “A physical-delivery declaration requires its first server receipt time”. El hecho tampoco fijaba el vencimiento de acuerdo con la publicación asociada.
- **EnTransito** ya era el estado preparado por el flujo de ruta; no requería una transición ficticia y era la única fila que alcanzaba el request HTTP en el primer run.

Esto era una incompatibilidad del fixture con las garantías actuales, no evidencia de un defecto del endpoint. No se cambió producción, la matriz, los triggers, RLS ni las restricciones.

### Corrección del fixture y assertions

PrepararEstadoMatrizCancelacionAsync prepara la fila antes del request y devuelve la versión vigente que se envía al endpoint:

- Avanza la versión al cambiar estado o hechos.
- Para los tres estados físicos establece por separado fecha física y primera recepción UTC. Lee PlazoValidacionPruebaMinutos de Envio.VersionReglasId; la prueba vencida se coloca después del límite derivado y las otras dentro de plazo. El fixture falla explícitamente si la publicación nueva de prueba no tiene duración configurada: no agrega un default.
- Mantiene una custodia coherente para el estado objetivo y el vínculo al repartidor/ruta cuando corresponde; actualiza la parada activa/suspendida y la versión de ruta en el fixture.
- La actualización controlada de estado queda marcada por OrigenTipo=TestFixtureCancelacionMatriz, OrigenId único y actor de proceso database-admin. El trigger de historia sigue activo y sus políticas RLS no se deshabilitan. Esta entrada significa preparación de fixture, **no** afirma que un usuario recorrió esa transición ni crea una operación de jornada ficticia.
- Congela IDs de historial y snapshots de estado, versión, hechos, custodia, parada, ruta, auditoría, aviso y outbox antes del HTTP. Casos permitidos comprueban una transición/auditoría/historia y los efectos de ruta/outbox que correspondan una vez; casos prohibidos comprueban respuesta 409 y ausencia de toda escritura posterior al snapshot.
- Las tres fechas se generan a precisión de milisegundo, menor que la precisión de PostgreSQL para timestamptz. Un run intermedio detectó una diferencia de sub-microsegundo solo en igualdad del snapshot; se corrigió la precisión del dato de prueba, no el comportamiento temporal de producción.

El test de rollback que invoca cancel_shipment directamente también omitía el contexto history_source_type/history_source_id que aporta el repositorio en producción. Por eso recibía SQLSTATE 42501 antes de alcanzar el trigger de fallo del outbox. El test ahora establece ese contexto real dentro de la transacción; vuelve a verificar el fallo SQLSTATE P0001 del outbox y el rollback conjunto.

### Verificación final

Docker se confirmó en solo lectura: docker context inspect desktop-linux --format "{{.Endpoints.docker.Host}}" devolvió npipe:////./pipe/dockerDesktopLinuxEngine; Docker Desktop informó versión 28.0.4. Cada escenario usa la base PostgreSQL efímera de PostgresFixture; las solicitudes HTTP pasan por TestServer con el rol API restringido, no por superusuario.

| Check | Resultado | Evidencia |
|---|---:|---|
| Matriz autenticada completa | **12/12** | Siete permitidos y cinco prohibidos llegaron al endpoint usando la versión preparada. Estado, hechos, custodia, historia, ruta, auditoría, aviso y outbox quedaron en el resultado esperado. |
| Regresiones de cancelación, acceso público, evidencia, terminalidad, DEC-01 e interacción DEC-04 | **36/36** | Incluye replays autenticados/públicos sin duplicados, restricciones tras hecho físico, prueba tardía, terminalidad, plazo DEC-01, carreras cancelación-entrega/reprogramación y rollback de outbox con historia. Efectos persistidos comprobados en PostgreSQL. |

Comandos ejecutados:

    dotnet test tests/NexoRuta.IntegrationTests/NexoRuta.IntegrationTests.csproj --no-restore --filter FullyQualifiedName~CancelacionAutenticadaRespetaLaMatrizDeEstados --logger "console;verbosity=minimal"

    dotnet test tests/NexoRuta.IntegrationTests/NexoRuta.IntegrationTests.csproj --no-restore --filter "FullyQualifiedName~CancelacionAutenticadaEsAtomicaYNoDeshaceUnaEntregaRecibida|FullyQualifiedName~CancelacionAutenticadaRespetaLaMatrizDeEstados|FullyQualifiedName~CancelacionAntesDePlanificarNoInventaAvisoNiMovimientoFisico|FullyQualifiedName~PersistenciaImpideReactivarUnEnvioCancelado|FullyQualifiedName~DosCancelacionesConcurrentesPersistenUnSoloHechoYAviso|FullyQualifiedName~EntregaYCancelacionConcurrentesRespetanElPrimerResultadoConfirmado|FullyQualifiedName~CancelacionPublicaAdmiteEnDevolucion|FullyQualifiedName~CodigoSinVencimientoCancelaUnaVezYAuditaSinInventarUsuario|FullyQualifiedName~DespuesDeEntregaFisicaNoCancelaAunqueLaPruebaEstePendiente|FullyQualifiedName~ConfirmacionesConcurrentesConservanUnaSolaCancelacion|FullyQualifiedName~CancelacionConcurrenteNoDeshaceEntregaFisicaNiExigeRendirla|FullyQualifiedName~CancelacionConcurrenteConRecepcionDeDevolucionNuncaReactivaCancelado|FullyQualifiedName~EnviosNuevosUsanLaPublicacionParaValidarPruebaOIniciarDevolucion|FullyQualifiedName~EvidenciaCifradaEsInmutableYCompletaLaPruebaAutomaticamente|FullyQualifiedName~ReprogramacionConcurrenteConCancelacionNoSobrescribeElEstadoGanador|FullyQualifiedName~FalloAlInsertarOutboxRevierteEstadoHistorialAvisoYParada" --logger "console;verbosity=minimal"

Los checks son PostgreSQL/TestServer; no constituyen una ejecución nueva de navegador ni de publicación/consumo de brokers. No se necesitó cambio de producción ni migración. La revisión nativa continúa pendiente.

**Risk del seguimiento:** none (solo se corrigieron fixtures/assertions y este informe; el endpoint y el esquema de producción no se modificaron).
