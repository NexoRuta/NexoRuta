# CU-07 — hallazgos

## Estado del bloque backend CSV (24/10/2026)

Los hallazgos H-01 y H-02 describían correctamente las brechas de la auditoría inicial. El backend quedó implementado/verificado en `08-backend-importacion.md`, y la entrada Commerce quedó implementada/verificada en `09-commerce-importacion-y-verificacion.md`; por tanto, sus afirmaciones históricas de ausencia de importación e interfaz pendiente quedan reemplazadas para el checkout actual. La trazabilidad directa R01–R04 está cubierta; los límites transversales X02/X04/X05/X06 siguen vigentes y no se declara cerrado todo CU-07.
## Estado tras la verificación del flujo existente — 23/10/2026

- **Cerrados documentalmente:** H-03 (los documentos CU-07/CU-08 ya distinguen el recorte inicial del alcance obligatorio completo) y H-04 (README/arquitectura separan estado implementado, cubierto y ejecutado).
- **Actualizado con evidencia:** R-01. API y PostgreSQL/RLS/outbox ya se probaron con fixtures aislados y TestServer. Commerce no se revisó en navegador; esto limita la evidencia de UI, no demuestra que el alta individual falle.
- **Pendientes funcionales:** H-01/H-02 permanecen incumplimientos probados: no hay importación de archivos ni deduplicación de reimportaciones. Las propuestas de `04-diseno-de-implementacion.md` no están confirmadas.
- **Pendientes de aclaración/evidencia:** H-05 mantiene únicamente una aclaración documental de D01; no se exige ni debe agregarse una membresía permanente Comercio–Operador. La discrepancia entre el `LOGIN` documentado para `nexoruta_api` y `NOLOGIN` de la migración queda registrada en `05-verificacion-flujo-existente.md`; no se verificó la credencial runtime de producción.

Hallazgos ordenados por impacto. “No implementado” se reserva para capacidades ausentes en el recorrido/contrato inspeccionado; las limitaciones de ejecución se informan por separado y no se usan para inferir ausencia de implementación.

## Incumplimientos demostrados

### H-01 — Falta el alta de envíos por archivo

- **Severidad: Alta.** Es uno de los tres canales obligatorios expresos y actualmente no existe evidencia de ese flujo.
- **Requisito:** CU07-R03.
- **Esperado:** el comercio debe poder registrar envíos mediante importación de archivo, además de alta individual y API.
- **Observado:** la pantalla frontend/src/NexoRuta.Commerce/Components/Features/Envios/Pages/CrearEnvio.razor contiene un formulario individual; EnviosApiClient.CrearEnvioAsync manda un solo request a api/envios; backend/src/NexoRuta.Api/Features/Envios/Controllers/EnviosController.cs:23-51 recibe un CrearEnvioRequest individual. El OpenAPI frontend/contracts/nexoruta.openapi.json:9073-9082 documenta POST /api/envios con un único esquema CrearEnvioRequest. No se halló en la feature inspeccionada una carga de archivo, contrato multipart ni caso de uso de ingesta. Búsqueda acotada de importación en backend/src, frontend/src y frontend/contracts encontró el importador del catálogo de departamentos y el multipart de identidad visual, pero no importación de envíos. La documentación histórica backend/docs/cu/CU-07-alta-envios.md:30 dice que la importación masiva queda fuera de otros casos/hitos, contradiciendo el alcance obligatorio vigente.
- **Reproducción por inspección:** ingresar a /envios/crear presenta el alta de un envío; inspeccionar la solicitud cliente muestra un único POST JSON. No hay ejecución visual real en esta auditoría.
- **Impacto:** comercios que preparan lotes no pueden usar el canal requerido; una solución manual registro-por-registro no satisface “por archivo”.
- **Corrección mínima propuesta:** agregar una ingesta de archivo en Commerce y un contrato/API de lote que reutilice validaciones y el camino de creación existente. Definir formato y errores antes de implementar.
- **Aceptación necesaria:** con un archivo válido se crean los registros esperados; los datos inválidos se informan según política acordada; se preserva el actor Comercio y el operador seleccionado/permitido; el flujo no envía filas por un canal que omita permisos o validación.

### H-02 — No existe importación masiva idempotente para lotes completos ni parciales

- **Severidad: Alta.** Repetir una importación sin deduplicación puede crear envíos duplicados, contradiciendo un criterio expreso.
- **Requisito:** CU07-R04.
- **Esperado:** una reimportación del lote completo o de una parte ya ingresada no debe generar duplicados. La letra no especifica cómo identificar una fila repetida ni qué hacer ante cambios en sus datos.
- **Observado:** el request actual contiene OperadorId y campos de un envío/bulto, sin identidad de lote, fila o clave idempotente (CrearEnvioRequest.cs:5-33). El endpoint y el esquema OpenAPI aceptan una creación individual; no se encontró ruta batch ni contrato de importación. CrearEnvioUseCase genera un nuevo agregado y los IDs de dominio son UUIDv7, lo cual no define por sí mismo la identidad estable de una reimportación. Las pruebas disponibles comprueban el flujo individual y no la repetición de importaciones.
- **Impacto:** un reintento por archivo completo o parcial podría dejar duplicados y publicar eventos repetidos.
- **Corrección mínima propuesta:** decidir primero la identidad de repetición y su ámbito; después persistirla con protección contra concurrencia y ejecutar la creación/outbox en la frontera transaccional acordada. No asumir que el código de bulto es una clave idempotente.
- **Aceptación necesaria:** importar lote L una vez y luego L completo no aumenta el número de envíos; reimportar un subconjunto previamente procesado tampoco; los registros no repetidos sí se crean; dos solicitudes simultáneas de la misma fila no duplican envío ni efecto de outbox. El resultado para filas corregidas o parcialmente fallidas debe seguir la decisión funcional documentada.

## Riesgos documentales y decisiones abiertas

### H-03 — Documento de CU-07 del backend conserva un recorte histórico contrario a la letra vigente

**Estado: resuelto documentalmente en esta revisión.**

- **Severidad: Media.** Puede hacer que la ausencia de un requisito obligatorio se tome erróneamente por una decisión aceptada.
- **Requisito afectado:** CU07-R03 y CU07-R04.
- **Esperado:** la documentación de implementación debe distinguir el recorte demostrado en el monitoreo de la definición completa del laboratorio.
- **Observado:** backend/docs/cu/CU-07-alta-envios.md:3,16,30 declara implementado el alta individual y afirma que importación masiva queda en otros casos/hitos. PDF 5.2 n.° 7 (p. impresa 4, PDF físico 6) y XLSM CU obligatorios!D10 exigen archivo e idempotencia, incluso parcial. El documento backend/docs/cu/CU-08-bultos.md:19 también describe explícitamente un recorte de monitoreo, no la totalidad de CU-08.
- **Impacto:** aceptación basada en un hito parcial confunde estado histórico con cierre del CU.
- **Corrección realizada:** `backend/docs/cu/CU-07-alta-envios.md` ahora identifica su contenido como el primer monitoreo del canal individual y enumera archivo/idempotencia como parte obligatoria aún pendiente. No afirma que CU-07 completo esté cerrado.
- **Aceptación verificada:** se contrastó la corrección con PDF §5.2 n.° 7 y XLSM `CU obligatorios!A10:I10`/`D10`.

### H-04 — La documentación sobre el estado de RLS estaba desactualizada frente a ADR y código

**Estado: resuelto para las afirmaciones de estado del README y arquitectura; el runtime productivo sigue sin verificarse.**

- **Severidad: Media.** Complica determinar si el aislamiento transversal está pendiente o implementado; no demuestra un fallo de seguridad.
- **Requisito afectado:** CU07-X02.
- **Esperado:** resúmenes arquitectónicos reflejan el estado implementado y separan implementación estática de verificación ejecutada.
- **Observado inicialmente:** `architecture.md` y `backend/README.md` tenían estados antiguos. Esta revisión ejecutó `RlsPolicyTests` (17), `RlsRestrictedHttpFlowTests` (3), `RlsSqlFunctionContractTests` (1) y otras integraciones con PostgreSQL efímero; las 21 pruebas RLS/HTTP/función pasaron.
- **Impacto:** documentación contradictoria puede inducir a repetir un trabajo ya realizado o a considerar comprobada una propiedad que aquí no se ejecutó.
- **Corrección realizada:** `backend/README.md` y `architecture.md` distinguen diseño/implementación, tests ejecutados en DB local aislada y despliegue no inspeccionado. `05-verificacion-flujo-existente.md` conserva comandos y límites.
- **Limitación/documentación pendiente:** la ADR `docs/alcance/ADR-MT-001-PostgreSQL-RLS.md:21` etiqueta `nexoruta_api` como `LOGIN`, pero la migración lo fuerza a `NOLOGIN`; en pruebas la API usa un login separado con ese rol concedido. No se alteró la ADR ni se infirió el login productivo.

### H-05 — Queda ambigua la semántica del vínculo comercio-operador

- **Severidad: Media, decisión pendiente; no se clasifica como incumplimiento demostrado de CU-07.**
- **Requisito/contexto:** PDF 3.3 permite que un mismo comercio trabaje con más de un operador; workbook Dependencias!A4:I4 (D01) propone “contexto de operador + vínculo comercio-operador”; ADR-MT-001-PostgreSQL-RLS.md:11 dice que no se requiere una relación permanente y que el operador es seleccionado para cada envío.
- **Esperado:** dejar claro si “vínculo” significa pertenencia permanente, autorización de uso por comercio o simplemente el par comercio-operador de cada envío.
- **Observado:** la UI y pruebas existentes permiten elegir distintos operadores por envío. La función de base valida actor, comercio y operador activo; la ADR descarta la membresía permanente. La fila D01 no define su cardinalidad/vida útil y la letra principal no prescribe ese modelo.
- **Impacto:** una interpretación distinta puede causar consultas fallidas, decisiones de acceso incompatibles o una membresía no solicitada.
- **Corrección mínima propuesta:** aclarar D01 y mantener la ADR/validación de código alineadas con esa decisión. No agregar una tabla ni una regla de membresía por inferencia.
- **Tratamiento en esta revisión:** la selección por envío conforme a la ADR actual se toma como el comportamiento de acceso; la membresía permanente no es requisito. D01 sólo requiere aclaración documental. No se agregó tabla, permiso ni regla de acceso.
- **Aceptación de aislamiento observada:** dos envíos del mismo comercio usan distintos operadores y las lecturas quedan limitadas a comercio/operador asignado, incluidos los hijos; ver pruebas ejecutadas en 05.

### H-06 — Los reintentos de mensajería no usan espera creciente ni tienen panel de reintento encontrado

- **Severidad: Media.** Es una brecha de resiliencia/operación del requisito transversal §6.8; no invalida la atomicidad local del alta.
- **Requisito afectado:** PDF §6.8, p. impresa 6 (PDF físico 8); XLSM `No funcionales!A11:F11` (NFR-08).
- **Esperado:** reintentos con espera creciente, cola de mensajes fallidos y visibilidad para que administración consulte/reintente mensajes fallidos.
- **Observado:** el outbox reprograma errores a 30 segundos; la cola Rabbit de tracking conserva mensajes 30 segundos y redirige a la cola principal. El retry no aumenta el intervalo. `GenerarSeguimientoConsumer` limita a tres intentos de procesamiento no transitorio y envía esos mensajes a fallidos; los errores clasificados transitorios no tienen tope observado. No se encontró endpoint/UI de consulta/reintento administrativo en API/Commerce/Backoffice revisados.
- **Evidencia:** `RabbitMqSeguimientoTopology.cs:11-51`; `GenerarSeguimientoConsumer.cs:272-309`; funciones de claim/finish en `20261017201732_EnablePostgreSqlRls.cs:378-438`; pruebas de consumidor/topología pasaron (25 pruebas de mensajería detalladas en 05).
- **Impacto:** intervalos fijos pueden martillar servicios caídos y no se demuestra una operación administrativa de recuperación; el comportamiento no coincide con la espera creciente de la letra.
- **Corrección mínima propuesta:** pendiente de priorización/cierre en el alcance transversal de mensajería; no se implementó aquí.
- **Prueba de aceptación necesaria:** comprobar intervalos crecientes y persistencia/consulta/reintento de fallidos por el actor administrativo autorizado, además del comportamiento de retry existente.

### R-02 — La publicación outbox admite redelivery tras confirmar el broker

- **Severidad: Riesgo técnico controlado por idempotencia del consumidor; no es una afirmación de entrega exactamente una vez.**
- **Comportamiento observado:** el broker puede confirmar la publicación y fallar el marcado `Published` en DB; el worker reintenta y publica otra vez con el mismo EventId.
- **Evidencia:** `KafkaOutboxTests.ConfirmacionSinActualizacionSql_ReinicioRepublicaConEventIdEstable` pasó; `KafkaEnvioCreadoPublisher.cs` fija clave/event-id. La ventana equivalente existe entre efecto del consumidor y ACK.
- **Impacto:** consumidores externos deben usar EventId estable y deduplicar; el consumidor de seguimiento lo hace con persistencia transaccional. No se halló consumidor de producción local para `EnvioCreado`.
- **Corrección mínima propuesta:** conservar entrega at-least-once e idempotencia donde se consuma; no prometer exactamente una vez ni eliminar la ventana mediante una garantía inexistente.
- **Prueba de aceptación necesaria:** consumidor duplicado no produce efectos repetidos; confirmar EventId idéntico para redelivery.

## Riesgos técnicos y límites de verificación

### R-01 — No se verificó Commerce en navegador ni el rol configurado en producción

- **Severidad: Riesgo de evidencia, no defecto demostrado.**
- **Observado:** se ejecutaron pruebas HTTP de `TestServer` contra PostgreSQL real efímero, políticas RLS con login restringido, outbox, RabbitMQ/Kafka; Commerce tiene un test de componente con handler simulado. No se abrió una página Commerce en navegador y no se inspeccionó el connection string/rol de producción.
- **Impacto:** no se puede afirmar validación visual/teclado real ni la configuración del rol productivo. No invalida las garantías ejercitadas en el fixture.
- **Siguiente verificación segura:** preparar un stack de browser aislado para recorrido visual; comprobar el principal de DB del despliegue por procedimiento autorizado sin divulgar secretos.
- **Criterio:** browser evidencia éxito/validación/error/reintento/doble envío y confirmar el rol efectivo sin `SUPERUSER`/`BYPASSRLS`.

## Alcance separado — no mezclar con CU-07, aunque también es obligatorio

- CU-08 es un caso de uso **obligatorio y separado**, no una mejora opcional: exige uno o más bultos con identificación, peso y dimensiones (PDF §5.2 n.° 8; XLSM `CU obligatorios!A11:I11`). El alta actual sólo crea uno; el cierre de múltiples bultos corresponde al plan de CU-08, no se atribuye a CU-07.
- CU-09: no se evaluó cálculo de tarifa como condición de CU-07.
- API pública versionada, sandbox y claves por comercio están en la sección opcional 7.4; no se reportan como brecha del API obligatorio de CU-07.
- La letra no prescribe etiqueta, tarifa, tracking ni notificación como parte de CU-07; no se proponen.

## Resumen de pruebas observadas

- Backend: CrearEnvioUseCaseTests — 13 aprobadas; CrearEnvioRequestTests — 8 aprobadas.
- Frontend/contrato: OpenApiContractTests — 49 aprobadas; prueba de doble submit y reintento de alta — 1 aprobada con HTTP simulado.
- Todos los comandos incluyeron --no-restore; los tests compilaron sus proyectos referenciados. Advertencia observada una vez y ajena al caso: CS8629 en Backoffice/Features/ZonasCobertura/Pages/DetalleModel.cs:75.
- PostgreSQL/RLS/outbox y mensajería sí se ejecutaron con contenedores efímeros confirmados localmente; detalles por comando en `05-verificacion-flujo-existente.md`. Sin navegador/revisión visual. El HTTP fue `TestServer`, no Kestrel externo. Un primer filtro frontend sin coincidencias se corrigió en la primera auditoría; no se contabiliza como test aprobado.

## Seguimiento acotado de cancelación (24/10/2026)

Esta actualización posterior al corte de auditoría CU-07 no reclasifica la importación, no cierra CU-07 y cubre solo el bloque autorizado de cancelación terminal. La ejecución confirmó que la matriz SQL y las funciones públicas/authenticated excluían `EnDevolucion`; también se identificaron un control de versión que impedía reconocer una repetición tras registrar una entrega física tardía y una restricción de tabla que impedía conservar ese hecho junto a `Cancelado`. La repetición SQL existente ya verificaba autorización antes de devolver el resultado y no duplicaba efectos, por lo que se conservó.

Cambios y evidencia de este bloque: [`07-bloque-cancelacion-terminal.md`](07-bloque-cancelacion-terminal.md). El alcance completo de la máquina de estados, la importación/idempotencia de archivos y CU-08 permanecen pendientes en sus respectivos casos; no se incorporan como hallazgos resueltos de CU-07 por este cambio.
