# CU-06 — Implementación B2: ocupación, retorno y disponibilidad

Fecha: 01/11/2026. Fuente: checkout local, incluidos B1 y B2 sin commit. No es una afirmación sobre GitHub ni un despliegue. H02 y la extensión operativa de H05 se implementan aquí; no se reescribe su evidencia histórica en 01–04. B3–B5 no se implementan.

> **Actualización de aceptación:** ver [07-aceptacion-b2.md](07-aceptacion-b2.md). Se completó la revisión visual con Chromium local, se corrigió claridad de estados/requisitos y se aprobaron 24 pruebas focalizadas con navegador. Los resultados y limitaciones de la entrega inicial conservados debajo son históricos; la constatación física y la transición operativa siguen pendientes. No se inició B3.

> **Aceptación funcional aislada completada:** [08-aceptacion-funcional-aislada-b2.md](08-aceptacion-funcional-aislada-b2.md) registra esperado/observado/evidencia por paso y 19 verificaciones aprobadas. B2 queda técnicamente verificado; la revisión nativa y la habilitación operativa continúan pendientes. No hay firmas ni constataciones físicas atribuidas.

## Estado inicial y preservación

| Repositorio | Rama | HEAD inicial |
|---|---|---|
| Superproyecto | develop | `1ef21751106e727bb15f4f75d3976196857e2ca1` |
| backend | fix/zonacobertura | `a0aa204ffc3390606b9f04bc8a57424b598c205c` |
| frontend | fix/zonacobertura | `e05c0de27702cf9909656bed0a0d389152c25806` |
| mobile | fix/zonacobertura | `78f65e1ca534888270028d68e7abe86460989e12` |

Antes de editar se capturaron estados y archivos nuevos; raíz tenía gitlinks divergentes en backend/frontend/mobile y `docs/auditorias/cu06/` sin seguimiento. Backend/frontend conservaban todos los cambios B1 enumerados en 05; mobile no tenía cambios internos. Se preservó una copia completa de esos archivos locales en `%TEMP%/NexoRuta-CU06-B2-initial-d2bf97eaba344669a5eaf0a390e758a4`, con inventarios Git. No hubo cambio de rama, reset, checkout, limpieza, actualización de submódulos, commit, push ni despliegue. Se trabajó sin subagentes, por instrucción explícita.

## Cambios deliberados respecto del flujo anterior

- Planificar sigue reservando por fecha y permite futuro aunque exista ocupación hoy.
- **Despachar ahora solo se permite en la fecha operativa de la hoja**, según la zona horaria de su política. Antes se podía despachar anticipadamente. El rechazo 409 es anterior a cualquier mutación de ruta/ocupación.
- Despachar adquiere ocupación exclusiva de vehículo **y repartidor** en la misma transacción. Incluye preparación, carga y recorrido. No existe filtro por fecha ni por estado administrativo de la jornada.
- `FinJornada` conserva D18: cierra con incidencias, conserva custodia y libera la reserva diaria, **no** la ocupación física.
- Retorno y liberación son confirmaciones distintas desde Backoffice. El retorno no recibe bultos ni reabre jornada. Liberar requiere cierre aplicado, retorno y custodia pendiente resuelta. Rendición declarada, suspensión, desactivación, GPS o medianoche no acreditan descarga ni retorno.
- Se conserva la autorización offline de una hoja despachada: la ocupación no vence a medianoche. Inicio/carga/salida exigen su ocupación exacta vigente y sin retorno. El inicio no se rechaza solo porque su sincronización llega un día después; sigue rechazándose un inicio anterior a la fecha operativa. El diario móvil conserva su idempotencia/secuencia y conflicto sin aplicación parcial.
- Anular una autorización nunca iniciada exige ausencia de inicio/salida/carga y de operaciones de carga aplicadas. Suspende paradas y deja hoja `Cancelada`, sin cancelar envíos ni inventar retorno. La hoja no se recicla: el trabajo se reasigna explícitamente a una identidad nueva. Así un comando offline antiguo no puede iniciar otra autorización sobre la misma hoja.

## Modelo e invariantes

| Concepto | Fuente de verdad |
|---|---|
| Habilitación administrativa | `Vehiculo.Activo` |
| Reserva diaria | `HojaRuta.ReservaRecursosActiva` e índices existentes |
| Ocupación | `OcupacionRuta`, identidad propia, una por ruta |
| Activa | Derivada: `LiberadaEnUtc == null && AnuladaEnUtc == null` |
| Retorno | Instante/actor confirmados de la ocupación exacta |
| Liberación | Instante/actor confirmados, previo cierre/retorno/custodia resuelta |
| Disponibilidad inicial desconocida | `Vehiculo.VerificacionInicialEnUtc == null` |
| Auditoría/idempotencia | `HechosFlota`, comando UUID + hash + actor + recurso + versiones + respuesta inmutable |

No se agrega un enum que mezcle habilitación, reserva y ocupación ni booleanos de disponibilidad mantenidos por comandos distintos. La versión de ocupación es independiente de la hoja: no altera la secuencia móvil. Capacidades actuales y snapshots B1 permanecen sin cambios.

Se reutilizan `BeginOrJoinAsync`, el bloqueo de la fila del operador y los repositorios/casos de uso existentes. PostgreSQL agrega índices únicos parciales `(OperadorId,VehiculoId)` y `(OperadorId,RepartidorAccesoId)` sobre ocupaciones activas, sin fecha ni estado de hoja. Una jornada `Finalizada` sigue ocupando mientras no se confirme liberación. Claves compuestas y guard SQL vinculan ruta, operador, vehículo y repartidor. Las tablas nuevas tienen FORCE RLS, sin privilegios públicos/worker; API solo ve su tenant y su diario verifica identidad del actor. El diario es append-only, también para la identidad propietaria.

La misma confirmación (mismo UUID, actor, acción y payload) devuelve su respuesta guardada, sin duplicar hecho ni aviso. Otro contenido con el mismo UUID da 409. Un comando atrasado de A no modifica B: la consulta se vincula al ID de ocupación, vehículo, tenant y versión; incluso el replay exacto de una liberación pasada solo devuelve el recibo pasado.

### Carga pendiente

Se consulta custodia de **todos** los bultos con ruta custodiante, no solo paradas activas. `Repartidor` y `PendienteDeposito` bloquean liberación. Se reutiliza la recepción real en depósito y la conciliación vigente explícita de extravío; la mera cancelación no excluye carga. Las incidencias históricas no se borran y no bloquean cuando la custodia ya se resolvió. Una liberación rechazada no guarda cambios parciales.

## API y consumidores

- `GET /api/reparto/flota`: vehículos activos/inactivos, verificación inicial, ocupaciones activas de cualquier fecha, ruta responsable/fecha original, retorno, cantidad de bultos pendientes y última liberación.
- `POST /api/reparto/flota/{vehiculoId}/{accion}`: `verificar-inicial`, `conciliar`, `retorno`, `liberar`, `anular`, `recibir-carga-inicial`.
- Request: `comandoId`, `ocupacionId` (null solo para verificación/recepción inicial), `version`, `motivo` obligatorio hasta 500 caracteres. Recepción inicial agrega `envioId` y `versionEnvio`. Respuesta registra comando/recurso/ocupación/ruta/versión/instante del servidor; recepción inicial conserva IDs y versiones anteriores de bultos afectados.
- Permisos reutilizados: **ambos** `envios.gestionar` y `envios.consultar`, con comprobación de acceso operador y la autoridad operativa existente en aplicación (`ActorConGestionOperativaAsync`: rol protegido administrador/dueño/despachador). Un rol personalizado con ambos permisos no elude esa restricción existente. No hay confirmaciones móviles nuevas.
- Backoffice `/rutas` incorpora un panel de flota independiente del filtro diario. Muestra pendientes anteriores, enlace a ruta/fecha exactas y acciones por estado. Errores no se interpretan como disponibilidad. Antiforgery y `data-single-submit` existentes; se conserva el comando, versión y motivo ante error, sin reintentar con una versión nueva. Confirmación exitosa usa la región `role="status"` existente y recarga el listado.
- Mobile solo aclara al cerrar que retorno/disponibilidad se confirman en Backoffice. No cambia transporte ni genera hechos de flota: la ruta anulada no reutilizable evita confundir autorizaciones offline.
- API, ApiClient y snapshot OpenAPI se actualizan conjuntamente. Se conserva precisión B1; no se modifican tarifas, huellas de importación ni alta multibulto.

## Migración y conciliación inicial — procedimiento previo a habilitar B2

**No se aplicó ninguna migración a la base operativa.** La entrega separa estructura y activación para no elegir silenciosamente un recurso ni inventar historia.

1. Respaldar/verificar recuperación con el procedimiento habitual. Detener escritores anteriores (API/worker/mobile sync) y mantener ventana de mantenimiento. No habilitar B2 general ni ejecutar migración automática hasta conciliar.
2. Con una identidad de migración autorizada con SUPERUSER/BYPASSRLS (nunca el rol API), aplicar **solo** `20261101184716_StageFleetOccupations`, usando el mecanismo de despliegue existente. Equivalente EF: `dotnet ef database update 20261101184716_StageFleetOccupations --context NexoRutaDbContext --project src/NexoRuta.Infrastructure --startup-project src/NexoRuta.Api`, desde backend, con configuración deliberada de la base destino. Este comando se documenta; no se ejecutó sobre operación.

   **Corrección del cierre de aceptación:** la factory de diseño actual no configura conexión; el comando EF anterior es orientativo/incompleto sin conexión explícita, y el migrador habitual aplica todas las pendientes. Usar el procedimiento SQL offline por etapas y el bloqueo del job externo detallados en [07-aceptacion-b2.md](07-aceptacion-b2.md), no ejecutar el pipeline habitual suponiendo que pausará entre ambas etapas. Se conserva el texto original para trazabilidad; no se aplicó sobre operación.
3. Esta etapa agrega columnas/tablas/RLS y registra únicamente asignaciones `Despachada`/`EnCurso` legadas. `Legada=true`, pero adquisición/actor/retorno quedan **null**: no son eventos históricos reconstruidos. Identidades UUID técnicas no acreditan hechos físicos. Rutas históricas finalizadas no generan ocupaciones eternas. Todos los vehículos existentes quedan con disponibilidad inicial desconocida.
4. Ejecutar la versión B2 con migraciones automáticas **deshabilitadas** y acceso administrativo controlado. Abrir `/rutas`: los conflictos aparecen como varias ocupaciones, con IDs/fechas, sin importar el filtro diario. Inspeccionar físicamente vehículo/carga y confrontar asignaciones. Para una autorización realmente no iniciada, anular explícitamente. Para jornadas iniciadas, conservar/sincronizar operaciones, cerrar con D18 cuando corresponda, confirmar retorno real y resolver carga, luego liberar. **No** cancelar rutas ni seleccionar un ganador por fecha mediante SQL.
5. La acción `conciliar` acredita la vigencia **actual** de una ocupación legada después de inspección. Rechaza si comparte vehículo o repartidor con otra activa; no inventa el instante original del despacho. El actor y hora actuales quedan auditados. No ejecuta retornos ni descargas.
6. Para vehículos sin ocupación activa, confirmar `verificar-inicial` solo después de verificar retorno y ausencia de carga. Si hay custodia histórica de una ruta finalizada anterior a B2, usar primero los mecanismos vigentes de recepción/conciliación. Cuando falta la antigua incidencia necesaria para recepción normal, el panel ofrece **recepción física inicial** acotada: vehículo aún sin verificar, ruta finalizada sin registro B2, envío/versión vigentes y custodia de una sola ruta. Registra motivo, actor, ruta, envío y versiones previas de todos los bultos; no crea una incidencia o retorno retrospectivo ni altera el estado comercial. Si no hay constatación física ni conciliación válida, no confirmar disponibilidad: permanece desconocida.
7. Aplicar `20261101185119_EnforceFleetOccupationExclusivity`. Su precheck inspecciona **todos los tenants**; rechaza conflictos activos por vehículo/repartidor o asignaciones legadas activas sin conciliar. La excepción detiene la activación, preserva datos y no cancela nada. Volver al paso 4 y resolver explícitamente; no saltar el precheck ni debilitar los índices.
8. Verificar índices, RLS y panel por operador, ejecutar aceptación operativa en datos controlados y reción después habilitar el tráfico general. Vehículos aún desconocidos continúan bloqueados para despacho hasta inspección inicial individual.

La transición se prueba realmente bajando solo las nuevas tablas vacías en bases efímeras, creando asignaciones con el modelo anterior y migrando en las dos etapas. No hay limpieza de datos operativos. `Down` de la primera etapa rechaza borrar historia de flota existente; rollback con hechos requiere un procedimiento explícito que la conserve, no un `database update` destructivo.

## Verificación

Los tests encontrados en código no se presentan como ejecutados. Todos los HTTP de backend usan TestServer y las fixtures PostgreSQL/PostGIS temporales existentes; no se levantó otra API operativa ni se tocó la base de desarrollo. Reloj controlado por `TimeProvider`, nunca el reloj del equipo.

| Comprobación ejecutada | Resultado observado |
|---|---|
| RED previo al cambio: futuro despachado + vehículo/repartidor usado en otra fecha | 2 fallos esperados (devolvía 200 donde debía 409); `%TEMP%/cu06-b2-red.log` |
| API build | Correcto, 0 errores; advertencia NU1510 preexistente |
| Backoffice build / Razor | Correcto, 0 errores; NU1510 y CS8629 en DetalleModel ajeno a B2 |
| Backend B2 final, incluidas migraciones reales y RLS | **15/15**, `%TEMP%/cu06-b2-final15.log` |
| Diario de operaciones / DEC-04 / carga / cierre (`OperacionesRepartoHttpTests*`), serializado | **55/55**, `%TEMP%/cu06-b2-operations.log` |
| Backend unitarias, incluidas regresiones B1 | **227/227**, `%TEMP%/cu06-b2-unit.log` |
| Backend B1 capacidad vigente + RutasHttpTests + RepartoRestrictedHttpTests, serializados | **29/29**, `%TEMP%/cu06-b2-b1routes.log` |
| Frontend suite completa en un pase intermedio | **383/383**, `%TEMP%/cu06-b2-front-green.log` |
| Frontend final afectado (Fleet/Capacidad/Rutas/Configuration), serializado | **22/22**, incluye formularios de ocupación vieja, antiforgery y conservación exacta tras conflicto; `%TEMP%/cu06-b2-front-final-serialized.log` |
| JavaScript B1 `node --test frontend/tests/rutas-planificacion.test.cjs` | **1/1**, unidades/conversión se conservan |
| Mobile Core | **35/35** |
| Mobile Application / sincronización | **76/76** |
| Android ARM64 `dotnet build mobile/src/NexoRuta.Mobile -f net10.0-android --no-restore -p:RuntimeIdentifier=android-arm64` | Correcto, 0 errores; advertencias XA0141 en bibliotecas MapBox existentes |
| Revisión visual / teclado / 320 CSS px | **Pendiente**, host de navegador no disponible |

Un primer lote amplio de backend fue **anulado por `Internal CLR error (0x80131506)`** tras 72 pruebas aprobadas; no cuenta como suite aprobada. Un intento final completo de frontend sufrió el mismo aborto tras 231 aprobadas. Se dividieron los lotes y se usó un archivo `.runsettings` temporal con `MaxParallelThreads=1`/`ParallelizeTestCollections=false`; no se alteraron tests para ocultar el fallo del host. El pase completo previo y las verificaciones finales focalizadas se distinguen arriba. Un primer build Android sin RID intentó `android-x64`, ausente en los assets locales (NETSDK1047); se corrigió la invocación al RID **android-arm64 ya restaurado**, sin cambiar SDK/proyecto ni instalar dependencias.

Durante la ampliación de fixtures se corrigieron errores de preparación, no reglas de B1: el escenario de reutilización debía reactivar antes de planificar; un segundo tenant necesitaba el rol protegido que exige la autoridad operativa existente; el reloj falso debía devolver UTC para Npgsql. El control real de capacidad, custodia y exclusión no se relajó. Los dos escenarios DEC-04 que reutilizan el mismo recurso incorporan retorno/liberación explícitos después de recepción, sin eliminar sus aserciones previas.

Arquitectura ejecutada: **2 aprobadas / 1 fallo preexistente**, `ShipmentBoundaryTests.ShipmentEndpoints_DeclareApiOwnedResponses`, línea 30, esperado 2 / real 7. Es el mismo baseline documentado y reproducido antes de B1 en 05; no se modificó ni debilitó el test, ni se mezcla con B2. Log: `%TEMP%/cu06-b2-architecture.log`.

`dotnet ef migrations has-pending-model-changes --context NexoRutaDbContext --project backend/src/NexoRuta.Infrastructure --startup-project backend/src/NexoRuta.Api --no-build`: **sin cambios de modelo pendientes**, sin conectarse/aplicar migraciones operativas. `git diff --check` de los tres submódulos no reporta problemas.

### Evidencia funcional B2 persistente

Todas las funciones siguientes están en `backend/tests/NexoRuta.IntegrationTests/Reparto/OcupacionFlotaHttpTests*.cs`; sus 15 casos finalizaron aprobados:

| Escenario | Prueba / evidencia |
|---|---|
| Planificar futuro y rechazar despacho futuro sin mutaciones | `FuturePlanningIsAllowedButDispatchCannotAcquireBeforeItsOperationalDate` |
| Ocupación sin fecha / medianoche / ruta responsable | `OccupiedVehicleAndCourierBlockDispatchAcrossMidnightWithoutBlockingFuturePlanning` |
| Inicio y cierre offline autorizados sincronizados tarde no liberan globalmente | `AuthorizedOfflineStartAndCloseSurviveMidnightButDoNotReleaseGlobally` |
| D18, retorno sin descarga, rechazo atómico, recepción real, incidencia histórica, idempotencia, inactivo, reutilización el mismo día y comando viejo A/B | `CloseReturnReceiveReleaseReuseAreSeparateAuditableAndIdempotent`, propietario y rol PostgreSQL restringido |
| Anulación sin retorno/envíos cancelados; rechazo con inicio, carga o salida | `AnnulmentOnlyBeforeStartPreservesShipmentAndDoesNotInventReturn`, etapas 0/1/2/3 |
| Despachos concurrentes y segunda barrera PostgreSQL cruzando fechas | `ConcurrentDispatchAcquiresAtMostOneAndSqlExcludesVehicleAndCourierAcrossDates` |
| Mismo repartidor con otro vehículo | `DifferentVehicleCannotBypassOccupiedCourier` |
| Conflictos legados detectados, adquisición/actores desconocidos, conciliación y activación explícitas | `LegacyTransitionPreservesUnknownFactsDetectsConflictsAndRequiresExplicitReconciliation` |
| Históricos cerrados sin ocupaciones eternas, carga inicial bloqueante y recepción auditada sin retorno ficticio | `HistoricalClosedRouteDoesNotInventReturnAndInitialReceiptIsExplicitAndAudited` |
| Otro tenant, rol personalizado sin autoridad y RLS, inmutabilidad del diario | `FleetTenantIsolationIsEnforcedByHttpAndRlsAndFactsCannotBeMutated` |
| Contrato generado y comercio sin permiso | `FleetContractAndCommerceAuthorizationAreExplicit` |

Frontend persistente: `FlotaPagesTests.cs` comprueba HTML SSR con ocupación de una fecha anterior, ruta/fecha enlazadas, comandos/versiones exactos, antiforgery y conservación del motivo tras 409 sin reintento automático. No equivale a revisión visual. El panel abre las ocupaciones/cargas pendientes para que sus enlaces no queden ocultos al intentar despachar otro trabajo.

## Archivos de B2

Backend (prefijo `backend/`):
- `src/NexoRuta.Domain/Reparto/{OcupacionRuta,HojaRuta,Vehiculo}.cs`.
- `src/NexoRuta.Application/Reparto/Dtos/FlotaDatos.cs`, `Repositories/IRutasRepository.cs`, `UseCases/GestionarRutasUseCase.cs`.
- `src/NexoRuta.Infrastructure/Reparto/{EfRutasRepository,EfRutasRepository.Flota,EfOperacionesRepartoRepository.Ejecucion,HechoFlota,OcupacionRutaConfiguration}.cs`.
- `src/NexoRuta.Infrastructure/Persistence/{NexoRutaDbContext,DatosDemoSeeder}.cs`, dos migraciones anteriores, sus `.Designer.cs` y `Migrations/NexoRutaDbContextModelSnapshot.cs`.
- `src/NexoRuta.Api/Features/Reparto/{Contracts/FlotaContracts,Controllers/FlotaController}.cs`.
- `tests/NexoRuta.IntegrationTests/Fixtures/RepartoHttpData.cs` y `Reparto/OcupacionFlotaHttpTests*.cs`; `Reparto/OperacionesRepartoHttpTests.Dec04.cs` adapta los dos escenarios de reutilización al retorno/liberación explícitos sin eliminar aserciones anteriores.
- `docs/cu/cierre-jornada.md`: conserva D18 y explicita la nueva separación.

Frontend (prefijo `frontend/`):
- `src/NexoRuta.ApiClient/Features/Reparto/{Contracts/FlotaContracts,Clients/RutasApiClient}.cs`.
- `src/NexoRuta.Backoffice/Features/Reparto/Pages/RutasModel.cs`, `Pages/Rutas.cshtml`, `Pages/Rutas/{_Flota,_ConfirmacionFlota}.cshtml`, `wwwroot/css/rutas-deposito.css`.
- `tests/NexoRuta.ApiClient.Tests/{RutasPagesTests,FlotaPagesTests}.cs`, `contracts/nexoruta.openapi.json`.

Mobile: `mobile/src/NexoRuta.Mobile/Presentacion/HojaRutaViewModel.cs` (mensaje, sin funcionalidades nuevas). Superproyecto: este documento y log de trabajo local `odd/tasks/cu06-b2.md`. Comparación contra la copia inicial: 23 archivos B1 idénticos byte a byte, ninguno faltante y cinco compartidos con agregados B2 (Vehiculo, EfOperacionesRepartoRepository.Ejecucion, EfRutasRepository, OpenAPI y RutasPagesTests). Los archivos B1 no enumerados como B2 se conservan sin editar; los compartidos agregan comportamiento B2 sin sustituir las reglas de 05.

## Limitaciones y siguientes bloques

- B3–B5 siguen pendientes: base geográfica, horarios/ETA viales, proveedor y GPS. No se deduce retorno de ninguna estimación.
- Aceptación física con operador, datos reales conciliados y dispositivo sigue siendo posterior a las pruebas aisladas. No se declara CU-06 completo ni B2 desplegado.
- Navegador: `cua.getState()` devuelve `apps=[]`, `browsers=[]`, `Native pipe unavailable` y `browser access host unavailable`. No hubo revisión visual, prueba real de teclado ni viewport de 320 CSS px. HTML/HTTP y CSS adaptable no equivalen a esa prueba.
- Engram: el hook no registró identidad autoritativa y prohíbe nuevas escrituras atribuidas. Se conserva trazabilidad local; no se afirma memoria guardada ni se inventa sesión.
- Gentle-AI: sin cambiar preferencias, el límite conocido de backend es `external.select_intended_untracked`, operación requerida no expuesta; frontend confirmó modo OFF por preferencia clone-local (`rdd_disabled`). Backend volvió a confirmar `external.select_intended_untracked` en STATUS sin flags tras rechazar los flags de lentes antes de seleccionar untracked (`invalid_request`, `mutation_outcome=not_started`). No se fabricó revisión/aprobación ni se repitió indefinidamente una operación ausente. La verificación funcional propia es independiente.

## Ejemplo concreto de operación

1. Planificar para hoy y **despachar A**: adquiere ocupación de vehículo y repartidor, tras verificación inicial y capacidad B1 vigente.
2. **Iniciar**, cargar todos los bultos y **confirmar salida**: se exige la ocupación de A; carga/estados conservan su transacción y diario offline.
3. **Cerrar con pendientes**: D18 registra incidencias y conserva custodia. A queda finalizada, pero el vehículo sigue ocupado incluso mañana.
4. **Confirmar retorno** de A desde Backoffice: acredita regreso, no descarga. Liberar todavía se rechaza si conserva bultos `Repartidor`/`PendienteDeposito`.
5. **Resolver carga** mediante recepción física en depósito (o conciliación existente válida). La incidencia histórica permanece.
6. **Liberar** A con su ID/versión: registra disponibilidad y termina ocupación; repetir el comando recupera el mismo recibo.
7. **Reutilizar** con otra ruta B de la fecha operativa actual, incluso el mismo día. Un comando viejo de A no libera B. Si B nunca se inicia ni carga, se puede anular expresamente sin fabricar retorno.
