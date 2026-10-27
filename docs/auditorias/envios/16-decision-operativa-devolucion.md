# DEC-05 — Decisión operativa de devolución

**Estado:** opción A implementada y verificada para la operación API/Backoffice con la cardinalidad actual de un bulto por envío.
**Corte:** 26/10/2026.
**Alcance:** iniciar manualmente la devolución después de agotar intentos bajo `DecisionOperativa`; no implementar extravío (DEC-06), reasignaciones activas (DEC-07), múltiples bultos (CU-08) ni cliente offline.
**Control nativo:** continúa pendiente. Esta implementación y su revisión manual no son aprobación nativa.

## Decisión funcional

La opción A quedó confirmada para esta etapa del proyecto: con `DecisionOperativa`, agotados los intentos el envío permanece `NoEntregado`; no puede reprogramarse ni recibir otro intento. Un administrador del operador o despachador autorizado puede iniciar la devolución desde Backoffice e indicar un motivo. La acción produce `NoEntregado → EnDevolucion`. No cambia custodia ni simula rendición o recepción; `Devuelto` sigue requiriendo la recepción física existente.

Esta precisión complementa las reglas versionadas y la máquina propuesta; no es una frase literal del PDF del taller. `IniciarAutomaticamente` conserva su recorrido anterior. La acción no reinicia intentos, no aumenta el máximo ni cambia `Envio.VersionReglasId`.

## Implementación

### Autorización y contrato

- Se agregó `POST /api/envios/{id}/iniciar-devolucion` en `RutasController`, sujeto a la política vigente `envios.gestionar`.
- La política se evalúa contra el acceso autenticado/persistido. La organización y el operador provienen del contexto de acceso; el request no acepta identidad, rol ni operador. La correspondencia ahora está limitada al administrador protegido del operador (`administrador_operador`, `administrador` o `dueno`, según el aprovisionamiento existente) o al rol protegido de código estable `despachador_operador`, y en ambos casos requiere `envios.gestionar` vigente. `usuario_operador` y roles personalizados quedan rechazados aunque reciban ese permiso. Comercio, courier y operador ajeno son rechazados. No se compara un nombre visible de rol ni se amplía la autorización de cancelación.
- Request: `versionEnvio`, `comandoId` no vacío y `motivo` obligatorio, recortado y limitado a 500 caracteres. La respuesta diferencia la decisión original/replay del estado actual del envío. Los rechazos funcionales por estado/versión/regla se responden como conflicto; la API conserva sus respuestas de validación y autorización para requests inválidos o actores no autorizados.
- La ruta está reflejada en la exportación OpenAPI versionada; el contrato de alta individual y las rutas de reprogramación existentes no cambian.

### Componentes concretos

- Dominio: `backend/src/NexoRuta.Domain/Envios/Envio.cs` y `Domain/Reparto/DecisionDevolucionEnvio.cs`.
- Aplicación: `Application/Reparto/UseCases/GestionarRutasUseCase.cs`, `Repositories/IRutasRepository.cs` y `Dtos/IniciarDevolucionEnvioDatos.cs`.
- Persistencia: `Infrastructure/Reparto/EfRutasRepository.Reasignaciones.cs`, `DecisionDevolucionEnvioConfiguration.cs`, la nueva migración y `NexoRutaDbContextModelSnapshot.cs`.
- HTTP/OpenAPI: `Api/Features/Reparto/Controllers/RutasController.cs` y contratos request/response de DEC-05; exportación versionada en `frontend/contracts/nexoruta.openapi.json`.
- Backoffice: `frontend/src/NexoRuta.ApiClient/Features/Reparto/Clients/RutasApiClient.cs`, contratos de DEC-05, `frontend/src/NexoRuta.Backoffice/Features/Reparto/Pages/RutasModel.cs` y `Pages/Rutas.cshtml`.
- Regresión: `backend/tests/NexoRuta.IntegrationTests/Reparto/OperacionesRepartoHttpTests.Dec05.cs`, `backend/tests/NexoRuta.IntegrationTests/Envios/CommerceCsvImportKestrelTests.cs` y pruebas ApiClient/Backoffice de `frontend/tests/NexoRuta.ApiClient.Tests`.

### Reglas y transacción

`GestionarRutasUseCase` delega en la operación específica del repositorio. `EfRutasRepository.IniciarDevolucionAsync` aplica, bajo la transacción de solicitud existente y los bloqueos usados por las operaciones de ruta, las siguientes condiciones vigentes:

1. El envío pertenece al operador autenticado, tiene la versión esperada y sigue `NoEntregado`.
2. Se consulta `Envio.VersionReglasId`, no la publicación más reciente. La política debe ser `DecisionOperativa` y el resumen de operaciones `IntentoFallido` aplicadas debe alcanzar el máximo configurado.
3. No debe existir hecho/recepción física de entrega ni una custodia incompatible. El envío no se devuelve manualmente si aún quedan intentos.
4. La transición de dominio incrementa versión y cambia a `EnDevolucion`; la parada activa se suspende. La custodia del bulto no se altera.
5. La decisión, la transición, la historia canónica existente y los efectos outbox que correspondan se confirman juntos. Si la ruta está en curso, se reutiliza el aviso/outbox existente para el repartidor actual; no se crea un aviso para un repartidor futuro, un evento nuevo de broker ni un webhook.

La publicación automática de agotamiento permanece intacta. La operación manual no sustituye rendición ni recepción de depósito.

### Decisión, historia e idempotencia

La migración aditiva `20261026123301_DecisionOperativaDevolucion` agrega `DecisionesDevolucionEnvio`, relacionada por claves foráneas con envío, operador y versión de reglas. Guarda comando, motivo, actor/acceso, organización, versión anterior/nueva y fecha UTC; la restricción única `(OperadorId, ComandoId)` es el límite durable para identidad de comando. La fila de decisión conserva el motivo sin sobrescribir motivos previos.

La tabla usa `ENABLE ROW LEVEL SECURITY` y `FORCE ROW LEVEL SECURITY`, pertenece al rol de esquema, concede al rol API solo `SELECT, INSERT` y no concede escritura al Worker. Las políticas limitan lectura e inserción al operador/contexto confiable. Un trigger append-only impide `UPDATE`/`DELETE`; el API no recibe permiso general de escritura. La historia de transición sigue en `EnvioEventos` y su trigger transaccional existente; no se usa outbox como historial.

La autorización se comprueba antes de la búsqueda de replay. El mismo comando autorizado y equivalente devuelve la decisión original sin nueva transición, decisión, historia o outbox. Reutilizar su identidad con otro payload entra en conflicto. Un UUID distinto con la versión vigente tampoco permite repetir una decisión cuando el envío ya está `EnDevolucion`; recibe conflicto sin efectos nuevos. La respuesta conserva ambos hechos: decisión original `EnDevolucion` y estado/versión actuales, por ejemplo `Cancelado` si una cancelación autorizada ocurrió después.

Bloqueos y concurrencia:

- Comandos distintos simultáneos sobre el mismo envío: como máximo una transición se confirma; el siguiente relee el estado y recibe conflicto.
- Mismo comando simultáneo: la clave única y el camino de recuperación entregan un resultado aplicado y un replay.
- Cancelación/reprogramación/recepción y decisiones obsoletas compiten con el estado/versionado vigentes; una decisión de devolución no reactiva ni sobrescribe un ganador posterior.
- Fallo al insertar historia revierte decisión, estado, parada, aviso y outbox de la misma operación.

## Evidencia ejecutada

Docker se confirmó en solo lectura: `docker context inspect desktop-linux --format '{{.Endpoints.docker.Host}}'` devolvió `npipe:////./pipe/dockerDesktopLinuxEngine`. Las pruebas de integración usaron `PostgresFixture` efímero y las peticiones HTTP probaron el rol API restringido; no se usaron bases compartidas ni producción.

| Evidencia | Comando / prueba | Resultado |
|---|---|---:|
| Operación, administrador/despachador, actor sin permiso, operador ajeno, replay, política, concurrencia, tabla append-only y rollback | `dotnet test ... --filter` con el filtro OR DEC-05 completo listado abajo; nueve casos de `OperacionesRepartoHttpTests` | **9/9** |
| Regresiones de disponibilidad de intentos, DEC-04 contra cancelación, matriz autenticada y regla versionada de agotamiento automático | mismo proyecto, filtro OR para `IntentosDisponiblesYPoliticaAutomaticaNoPermitenDecisionManual`, `ReprogramacionConcurrenteConCancelacionNoSobrescribeElEstadoGanador`, `CancelacionAutenticadaRespetaLaMatrizDeEstados` y `EnviosNuevosUsanLaPublicacionParaValidarPruebaOIniciarDevolucion` | **16/16** |
| Backoffice y API HTTP real | `BackofficeBrowserIniciaDecisionOperativaConConflictoYReintentoSeguro` | **1/1**, Kestrel + Chromium + PostgreSQL aislado. Comprueba el agotamiento mostrado, motivo y confirmación, conflicto por versión obsoleta, recarga conservando motivo/comando y reintento exitoso. Estado, historia, decisión y custodia persistidos; el bulto sigue bajo custodia del repartidor. |
| Exportación OpenAPI versionada | `GeneratedOpenApiIncludesTarifarioRoutesAndExportsVersionedContractOnRequest` con `NEXORUTA_OPENAPI_EXPORT_PATH` dirigido a `frontend/contracts/nexoruta.openapi.json` | **1/1**; ruta presente |
| Contrato OpenAPI de importación y DEC-05 | `OpenApi_DescribesImportAsMultipartFormData` | **1/1** |
| ApiClient/Backoffice | `dotnet test tests/NexoRuta.ApiClient.Tests/NexoRuta.ApiClient.Tests.csproj --no-restore --filter FullyQualifiedName~RutasIniciaDecisionOperativaConMotivoConfirmadoYPermiteReintentoSeguro` | **1/1** |

Comandos ejecutados (los filtros usan `|` como OR de `FullyQualifiedName`):

```powershell
$filter = 'FullyQualifiedName~DecisionOperativaAgotada|FullyQualifiedName~UsuarioOperadorConPermisoGestionarPuedeDecidir|FullyQualifiedName~OperadorConPermisoNoPuedeIniciarDevolucionDeEnvioAjeno|FullyQualifiedName~IntentosDisponiblesYPoliticaAutomaticaNoPermitenDecisionManual|FullyQualifiedName~ReplayAutorizadoDevuelveDecisionOriginalAunqueElEnvioYaEsteCancelado|FullyQualifiedName~DecisionesConcurrentesDeDevolucion|FullyQualifiedName~MismoComandoConcurrenteDevuelveUnResultadoAplicadoYUnReplay|FullyQualifiedName~FalloAlInsertarHistoriaRevierteDecisionEstadoParadaAvisoYOutbox|FullyQualifiedName~RendicionYRecepcionNoEludenElAgotamientoDeDecisionOperativa'
dotnet test tests/NexoRuta.IntegrationTests/NexoRuta.IntegrationTests.csproj --no-restore --filter $filter --logger 'console;verbosity=minimal'

$filter = 'FullyQualifiedName~IntentosDisponiblesYPoliticaAutomaticaNoPermitenDecisionManual|FullyQualifiedName~ReprogramacionConcurrenteConCancelacionNoSobrescribeElEstadoGanador|FullyQualifiedName~CancelacionAutenticadaRespetaLaMatrizDeEstados|FullyQualifiedName~EnviosNuevosUsanLaPublicacionParaValidarPruebaOIniciarDevolucion'
dotnet test tests/NexoRuta.IntegrationTests/NexoRuta.IntegrationTests.csproj --no-restore --filter $filter --logger 'console;verbosity=minimal'

dotnet test tests/NexoRuta.IntegrationTests/NexoRuta.IntegrationTests.csproj --no-restore --filter 'FullyQualifiedName~BackofficeBrowserIniciaDecisionOperativaConConflictoYReintentoSeguro' --logger 'console;verbosity=minimal'

$env:NEXORUTA_OPENAPI_EXPORT_PATH = (Resolve-Path '../frontend/contracts/nexoruta.openapi.json').Path
dotnet test tests/NexoRuta.IntegrationTests/NexoRuta.IntegrationTests.csproj --no-restore --filter 'FullyQualifiedName~GeneratedOpenApiIncludesTarifarioRoutesAndExportsVersionedContractOnRequest' --logger 'console;verbosity=minimal'
dotnet test tests/NexoRuta.IntegrationTests/NexoRuta.IntegrationTests.csproj --no-restore --filter 'FullyQualifiedName~OpenApi_DescribesImportAsMultipartFormData' --logger 'console;verbosity=minimal'

dotnet test tests/NexoRuta.ApiClient.Tests/NexoRuta.ApiClient.Tests.csproj --no-restore --filter FullyQualifiedName~RutasIniciaDecisionOperativaConMotivoConfirmadoYPermiteReintentoSeguro --logger 'console;verbosity=minimal'
```

La prueba de autorización añadida para operador ajeno devuelve 404 sin decisión, transición ni historia de devolución. Al preparar ese fixture, una primera inserción simultánea de operador/rol/acceso chocó con la FK compuesta antes del HTTP; al separar la persistencia en el orden de dependencias, el test aislado pasó 1/1 y la suite DEC-05 final pasó 9/9. Un intento de incluir ese actor extra en el test que ya hacía varios login alcanzó el rate limit de autenticación (429); se aisló en una prueba propia. Ninguno fue un fallo de producción.

La prueba de navegador verificó escritorio (1280 px), móvil estrecho (320 px), navegación/foco por teclado y la interacción de conflicto/reintento. Esto no representa una revisión visual completa en todos los navegadores/dispositivos. El build frontend produjo una advertencia preexistente `CS8629` en `ZonasCobertura/Pages/DetalleModel.cs:75`, ajena a DEC-05. No se probaron publicación/consumo reales de RabbitMQ/Kafka ni se amplió la auditoría de brokers.

## Límites y trabajo siguiente

- La acción queda verificada para el modelo actual de un bulto. CU-08 es obligatorio y separado; recepción, rendición y devolución con varios bultos/discrepancias no están cubiertas ni se infieren de esta acción.
- **Al cierre del bloque 16:** DEC-06 (actor/evidencia/custodia de extravío) y DEC-07 (reasignaciones activas/salidas adicionales) seguían pendientes. DEC-06 opción B quedó implementada después en el bloque 17; los detalles y límites actuales están en `17-confirmacion-operativa-extravio.md`. DEC-07 sigue pendiente.
- CU-24 / cliente móvil offline sigue pendiente; este bloque protege comandos del servidor y sus replays, pero no implementa sincronización offline en MAUI.
- CU-08 y los demás CU no se declaran completos. La política automática se mantuvo, no se rediseñó.
- La revisión nativa continúa pendiente; no hay aprobación nativa ni cierre global de la máquina de estados.

**Risk:** item 1 (estado, historial y nueva decisión persistida), item 2 (autorización/RLS), item 4 (replay, locks y carreras concurrentes).

## Actualización de autorización DEC-05 — rol dedicado

El equipo confirmó que “despachador” significa exclusivamente el rol protegido `despachador_operador`; tener `envios.gestionar` en cualquier rol no basta. La misma regla de actor se aplica a DEC-05 y DEC-06. El acceso autorizado exige además organización operativa, operador activo, acceso vigente, permiso actual y pertenencia del envío. La autorización se revalida antes de leer el replay. El administrador protegido se reconoce por los códigos de rol que genera el aprovisionamiento vigente (`administrador_operador`, `administrador` y `dueno`), siempre con `EsProtegidoSistema`; no por el nombre visible ni por `EsPropietario` aislado.

El rol `despachador_operador` queda disponible para asignación mediante `GET /api/roles/asignables` y el flujo administrativo existente de usuarios. No se asigna a ningún usuario al aprovisionarlo. La migración `20261027020542_ConfirmOperationalShipmentLoss` lo crea en operadores existentes y otorga únicamente `envios.gestionar`/`envios.consultar`; `EfPlataformaRepository` y `DatosInicialesSeeder` lo crean para operadores nuevos y de bootstrap. Las pruebas de plataforma verifican que roles personalizados y `usuario_operador` no reciben autorización por tener el permiso.

**Corrección confirmada:** el flujo de creación de una organización nueva produce roles administrativos protegidos `administrador` (identidad nueva) y `dueno` (identidad existente); una revisión focalizada detectó que la comprobación anterior aceptaba únicamente `administrador_operador`, por lo que el administrador recién aprovisionado recibía `puedeGestionarDecisionesOperativasEnvio = false`. Se amplió la lista únicamente a esos códigos protegidos realmente creados por el proyecto. Un test TestServer primero reprodujo el valor falso y luego pasó tras la corrección; los accesos de usuario-operador y personalizados continúan denegados.

### Evidencia posterior a la corrección

| Check | Resultado | Evidencia |
|---|---:|---|
| DEC-05 y DEC-06 con rol API restringido, incluidos administrador, dispatcher, custom role, `usuario_operador`, operador ajeno, revocación y permiso removido antes de replay; migración de operadores existentes | **4/4** | `DespachadorDedicadoPuedeDecidirYRolesSinCorrespondenciaNoPuedenRepetirla`, `DispatcherConfirmsLossButCannotCancelAndReplaysRecheckCurrentAccess`, `AdministradorConfirmaExtravioDesdeDepositoSinMoverCustodia`, `LossConfirmationMigrationProvisionsDispatcherForExistingOperatorsWithoutAssigningUsers`. |
| Aprobación del perfil para administradores creados por plataforma (`administrador`) y alta propia (`dueno`), con rol dispatcher protegido no autoasignado en el recorrido de operador nuevo | **3/3** | `RestrictedApiCreatesOperatorOnlyForAuthorizedPlatformAndRejectsUnauthorizedUsersAtomically` más los dos casos de `IdentityOnlySessionCreatesOwnProtectedOrganizationAndRequiresNewLogin`. |
| Backoffice operativo | **1/1** | `BackofficeBrowserIniciaDecisionOperativaConConflictoYReintentoSeguro`: Kestrel local, Chromium y PostgreSQL efímero/restringido; el administrador protegido ve la acción, y el dispatcher ejecuta DEC-05 y DEC-06 con formulario, conflicto, reintento y terminalidad. |

No se agregó ni cambió una regla de cancelación: el mismo test confirma que el dispatcher no puede cancelar, y la regresión completa de Reparto continúa verificándose por separado. La revisión nativa sigue pendiente.
