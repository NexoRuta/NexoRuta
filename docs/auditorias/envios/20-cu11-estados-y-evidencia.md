# CU-11 — estado comercial, política y verificación actual

Corte 03/11/2026. Base remota comprobada: rama `fix/regresion-flota-deposito`, principal `6d179b83f47daaf5331bdddd6f92baac1e2d84b4`, Backend `9a35b8b292e74a98a55f3e22eab8097bd0d7eb9a`, Frontend `bf36df3d02f6e4c9b098d5545a3483f4c6dea15e`, Mobile `74a25f1b5b18c7dfc006cf7df747d73b0ec4910a`. Checkout limpio antes de crear las ramas propias `feature/cu11-estados-envio` en principal y Backend. La base y otros CU siguen pendientes de revisión humana.

## Fuentes e interpretación

- Enunciado `docs/alcance/Laboratorio__NET_2026.pdf`, §5.2, 11: máquina explícita, transiciones declarativas verificables, sin modificar estado desde cualquier punto; enumera diez estados mínimos. Requisitos 8/10/12 y §§5.3–5.4 añaden varios bultos, cotejo, historia, planificación y sincronización.
- Planilla `Calcs/Casos de Uso - Responsables.xlsm`: **CU obligatorios A14:I14**, CU-11/M02/API-dominio/Sistema. Dependencias **D03** (reglas del operador/versionadas), **D05** (elegibilidad de asignación), **D12** (sincronización/versiones/conflicto), **D20** (lectura de estado para riesgo). Se leyeron también alcance de aplicaciones/incidencias. No se ejecutaron macros ni se usaron colores como aceptación.
- Diagrama `Diagramas/maquina-estados-envio-corregida.png`, decisiones DEC-01/04/05/06/07 registradas en informes 11–19 y [CU-10](../cu10/01-aceptacion.md). El PDF fija mínimos, no todas las flechas ni todos los permisos; se preservan las decisiones documentadas y contratos existentes.

El informe 19 describe el corte de un bulto anterior a CU-10. Sus menciones a recepción inicial masiva y a despacho/carga no sustituyen la implementación actual. **Despacho autoriza la hoja; ConfirmarCarga acredita salida y cambia el envío.** Para varios bultos, solo el cotejo final conforme completa la primera recepción. No se agregan estados ni un motor de workflows.

## Inventario y brechas

Estados comerciales persistidos: `Admitido`, `EnDeposito`, `AsignadoRuta`, `EnTransito`, `Entregado`, `NoEntregado`, `Reprogramado`, `EnDevolucion`, `Devuelto`, `Extraviado`, `EntregaPendienteValidacion`, `EntregaSinValidacion`, `Cancelado`. Los últimos tres amplían legítimamente el mínimo del PDF según las decisiones existentes. `Entregado`, `Devuelto`, `Extraviado`, `EntregaSinValidacion` y `Cancelado` no tienen flechas salientes.

| Componente / entrada | Escritor real y control existente | Hallazgo / tratamiento |
| --- | --- | --- |
| Alta individual, API de comercio e importación CSV | Casos de uso de creación/importación → constructor `Envio` → `EfEnviosRepository`; constructor fija Admitido y el trigger exige nacimiento Admitido/version 0. Identidad de importación y creación/historia/outbox comparten transacción. | No hay parámetro público para elegir el estado inicial. Se conserva idempotencia de importación, tarifas y declaración de bultos. |
| Primera recepción CU-10 | `CotejarBultoAsync` en `EfRutasRepository.Recepcion.cs`, `POST /api/deposito/bultos/{id}/recepcion` | Ya agrega conformidad/custodia de todos los bultos antes de Admitido→EnDeposito. Escaneo/GET solo identifica. Se verifica con las suites existentes y nuevos casos de competencia/rollback. |
| Retorno/recepción de custodia | `EfRutasRepository.RecibirAsync`, POST de recepción por envío | Rechaza Admitido al entrar, pero conservaba código posterior inalcanzable Admitido→EnDeposito. Se elimina esa rama muerta; solo EnDevolucion→Devuelto cambia estado comercial aquí. No se retira el circuito de retorno. |
| Planificación / reasignación / reprogramación | `EfRutasRepository.cs` y `.Reasignaciones.cs`; endpoints `api/rutas`, `api/envios/{id}/reasignacion`, `reprogramacion` | Usan el agregado, versiones, operador, ocupación, destino, capacidad, horarios y custodia. Reasignación de AsignadoRuta incrementa versión/hecho sin cambiar estado. |
| Despacho / carga / salida / entrega / intentos / rendición / cierre | `RutasController`, `EjecutarRepartoUseCase` y `EfOperacionesRepartoRepository(.Ejecucion)`; `POST /api/mobile/jornadas/{id}/operaciones` | Secuencia/UUID/hash/actor, jornada y versiones preceden a los cambios. Los métodos especializados de entrega física y evidencia asignaban Estado dentro del agregado sin consultar el predicado común. Se los canaliza por la misma política, sin cambiar sus precondiciones. |
| Cancelación autenticada | `CancelarEnvioUseCase` → `EfCancelacionesEnvioRepository` → función `nexoruta_app.cancel_shipment` | Dominio valida elegibilidad; SQL revalida permisos/versión/hecho físico dentro del lock y registra auditoría/evento/efectos. No se amplían permisos de comercio sobre otras columnas. |
| Cancelación pública | `CancelacionPublicaController` → servicio/funciones SQL de confirmación por token y código | Escritura acotada por token/código, enlace vigente, versión y contexto público. Pasa por la guarda de matriz e historia; no se inventa usuario autenticado para ese actor. |
| Devolución y extravío operativos | `.Reasignaciones.cs` / `.Extravio.cs`; endpoints iniciar-devolucion y confirmar-extravio | Estado/versión, decisión operativa, motivo y permisos efectivos; replay por comando; atomicidad de decisión, ruta e historia existente. |
| Vencimiento de prueba | `ProofValidationDeadlineWorker` → `nexoruta_app.expire_pending_proof_deadlines` | SQL limitado a pendientes con deadline vencido y rol privado; guarda matriz PostgreSQL e historia canónica. Conserva versiones históricas sin deadline. |
| Mobile offline y proyección | `JornadaLocal`, `SincronizadorJornada`, `VistaParada` | El teléfono conserva operaciones/UUID/secuencia y aplica a su vista versiones/estados confirmados por el servidor; no escribe directamente Envios. Un conflicto no aporta cambios aplicados. No se cambia el contrato ni se cierra el cliente Mobile. |
| Backoffice/Commerce, tracking, etiquetas, notificaciones | Comandos de negocio anteriores o proyecciones de lectura | No se encontró endpoint genérico de “set estado”. Etiquetas/escaneo/descarga no son escritores comerciales. Notificaciones consumen persistencia/outbox, no deciden transiciones por sí solas. |

### Corrección acotada

Se reutiliza exactamente el predicado previo en `TransicionesEstadoEnvio.Permite`, política pura y declarativa. `Envio.AplicarEstado` es ahora la única asignación comercial posterior al nacimiento y aplica esa política tanto al cambio general como a entrega física y evidencia. El constructor y la materialización histórica no son transiciones. Las precondiciones físicas, versiones, permisos y reglas permanecen en sus operaciones existentes; una arista permitida no autoriza por sí sola a un actor ni reemplaza esas guardas.

La guarda SQL instalada por `20261028010000_EnforceShipmentTransitionMatrix` permanece como defensa de escritores SQL/worker. Se prueba su **función instalada real** para los 169 pares del enum y su acuerdo con dominio. La prueba unitaria existente conserva la lista independiente de flechas esperadas; no se usa la propia matriz como único oráculo. SQL admite UPDATE con el mismo valor; no es una transición ni una nueva flecha del dominio.

No se cambiaron flechas de negocio ni se demostró una transición ilícita ya aceptada por los endpoints. La brecha corregida es la dispersión de escrituras internas y su cobertura verificable. No se agregan migraciones, permisos ni aliases; no cambia ningún contrato HTTP ni dato histórico.

## Matriz comercial vigente

Toda transición produce `EnvioEventos.Tipo=TransicionEstado` con origen/final, versiones, marca temporal y actor/origen del comando en la **misma transacción**. La creación produce `Creacion` en Admitido/version 0. No se emite transición por un no-op o replay. Las columnas de origen indicadas abajo son `OrigenTipo`; custodia/ruta solo cambian cuando lo dispone expresamente la operación.

Abreviaturas de rechazo/repetición (no implican auto-reintentar operaciones):

- **V:** versión esperada vigente; nueva solicitud obsoleta/incompatible: HTTP 409, sin escritura comercial parcial. Motivo validado por la operación.
- **R:** comando de recepción ligado a actor, bulto y payload; replay exacto recupera resultado, no escribe otro cotejo. Comando reutilizado con otros datos: 409.
- **M:** sincronización Mobile por UUID/hash/actor/jornada y secuencia. Replay exacto devuelve respuesta persistida; UUID con otro payload/contexto o salto de secuencia: 409. Una operación de negocio incompatible puede quedar como `Resultado=Conflicto` HTTP 200, conservando su hecho de sincronización pero **sin** cambio comercial/custodia/prueba parcial; no se confunde con aplicación exitosa.
- **D:** decisión operativa por UUID/payload/actor/versiones: replay exacto; UUID cambiado o estado/versiones incompatibles: 409.
- **C:** cancelación autenticada reitera solo misma auditoría/actor/versión original/motivo y versión resultante; una variante incompatible: 409. La pública mantiene su resultado de negocio/código y HTTP existentes, sin convertir sus rechazos en el contrato autenticado.

| # | Inicial → final | Operación / actor o permiso | Precondiciones particulares | Efectos / origen de evento | Repetición / conflicto |
| --- | --- | --- | --- | --- | --- |
| 1 | Admitido → EnDeposito | Cotejo que completa recepción; operador `envios.gestionar` | Versiones envío/bulto; todos presentes en Deposito y último cotejo conforme, sin faltantes/discrepancias | Cotejo inmutable, custodia del bulto presente, versión envío +1; `RecepcionDeposito` | R, V |
| 2 | EnDeposito → AsignadoRuta | Planificar; operador `envios.gestionar` | Todos los bultos en depósito, destino confirmado, ruta/recursos, capacidad, paradas y horarios válidos; sin otra parada activa | Crea parada y reserva; no mueve custodia; `PlanificacionRuta` | V; nueva planificación repetida no duplica asignación |
| 3 | AsignadoRuta → EnTransito | ConfirmarCarga/salida; repartidor `reparto.ejecutar` de esa jornada | Hoja en curso, ocupación activa sin retorno, sin salida previa; carga completa de paradas activas, capacidad/horarios/versiones vigentes | Confirma salida; la custodia ya proviene de CargarBulto, no de despacho; `OperacionJornada` | M |
| 4 | EnTransito → Entregado | EntregaFisica con prueba completa; mismo repartidor | Salida, parada activa, todos los bultos bajo custodia propia, versión y requisitos fijados al envío | Guarda hecho físico/prueba; custodia Destinatario; `OperacionJornada` | M |
| 5 | EnTransito → EntregaPendienteValidacion | EntregaFisica sin prueba completa; mismo repartidor | Mismas guardas de entrega; falta prueba exigida | Conserva entrega física, primera recepción UTC y deadline versionado; custodia Destinatario; `OperacionJornada` | M |
| 6 | EntregaPendienteValidacion → Entregado | EvidenciaEntrega; repartidor original | Entrega física original y custodia de destino de esa ruta, prueba completa recibida antes del deadline (o versión histórica sin plazo) | Prueba vinculada; no inventa otra entrega/custodia; `OperacionJornada` | M; versión posterior por vencimiento tiene conciliación restringida, no reabre estado |
| 7 | EntregaPendienteValidacion → EntregaSinValidacion | Worker / rol privado de vencimiento | Deadline no nulo <= reloj servidor; sigue pendiente al UPDATE | Versión +1, sin movimiento físico; `PlazoValidacionPrueba`, actor proceso | Repetir barrido no vuelve a afectar la fila; concurrencia vuelve a comprobar estado/plazo |
| 8 | EnTransito → NoEntregado | IntentoFallido; repartidor de jornada | Salida/custodia propias, motivo disponible, prueba exigida, intervalo y máximo versionados | Registra intento; conserva custodia; `OperacionJornada` | M |
| 9 | NoEntregado → Reprogramado | Reprogramar; operador `envios.gestionar` | Sin entrega física, intento aplicado e intentos restantes; versión y reglas fijadas al envío. La custodia y el horario de la próxima visita se validan al volver a asignar | Suspende asociación previa y habilita nueva planificación; no mueve custodia; `ReprogramacionEnvio` | V |
| 10 | Reprogramado → AsignadoRuta | Planificar o reasignar a nueva ruta; operador `envios.gestionar` | Custodia de depósito, nueva ruta elegible, destino, capacidad, horarios y versiones | Nueva parada/asociación; `PlanificacionRuta` o `ReasignacionRuta` | V; no permite dos asignaciones activas |
| 11 | NoEntregado → EnDevolucion | Agotamiento automático en IntentoFallido o decisión manual; repartidor / operador con capacidad de decisión operativa | Máximo agotado; política versionada automática o DecisionOperativa; para manual motivo y actor habilitado | Suspende parada, conserva custodia; `OperacionJornada` o `DecisionDevolucionEnvio`. Automático persiste ambas aristas 8/11 en una transacción | M o D; fallo revierte ambos pasos |
| 12 | EnDevolucion → Devuelto | Recepción de retorno; operador `envios.gestionar` | Versión vigente; bultos recibibles/rendidos o incidencia de cierre acreditada | Custodia Deposito, no libera vehículo; `RecepcionDeposito` | V; repetir estado final no vuelve a transicionar |
| 13 | EnDeposito → Extraviado | ConfirmarExtravio; operador con `envios.gestionar` y `PuedeGestionarDecisionesOperativasEnvio` | Motivo, versión, pertenencia y custodia compatibles; sin entrega física | Auditoría de confirmación y suspensión/conciliación aplicable; `ConfirmacionExtravioEnvio` | D |
| 14 | AsignadoRuta → Extraviado | Misma operación/actor | Mismas guardas más asociación/ruta vigente | Misma auditoría; no entrega ni recepción ficticias; `ConfirmacionExtravioEnvio` | D |
| 15 | EnTransito → Extraviado | Misma operación/actor | Mismas guardas y custodia de recorrido compatible | Misma auditoría/historia; no libera vehículo por sí sola; `ConfirmacionExtravioEnvio` | D |
| 16 | EnDevolucion → Extraviado | Misma operación/actor | Mismas guardas, sin recepción/entrega posterior | Misma auditoría/historia; `ConfirmacionExtravioEnvio` | D |
| 17 | Admitido → Cancelado | Cancelación autenticada o pública vigente | V, sin entrega física; comercio propio `envios.crear`, administrador operador `envios.gestionar`, o token/código público autorizado | Auditoría, evento y avisos/outbox aplicables; `CancelacionEnvio` o contexto público registrado | C |
| 18 | EnDeposito → Cancelado | Misma operación/actores | Mismas guardas efectivas | No inventa movimientos de custodia; `CancelacionEnvio`/público | C |
| 19 | AsignadoRuta → Cancelado | Misma operación/actores | Mismas guardas y versión | Suspende parada; cancelar envío no libera reserva de ruta; `CancelacionEnvio`/público | C |
| 20 | EnTransito → Cancelado | Misma operación/actores | Mismas guardas; si ya hay hecho físico, no procede | Conserva custodia real y concilia evidencia tardía sin reactivar; `CancelacionEnvio`/público | C |
| 21 | NoEntregado → Cancelado | Misma operación/actores | Mismas guardas y versión | Suspende asociación aplicable, auditoría/historia; `CancelacionEnvio`/público | C |
| 22 | Reprogramado → Cancelado | Misma operación/actores | Mismas guardas y versión | Auditoría/historia y efectos existentes; `CancelacionEnvio`/público | C |
| 23 | EnDevolucion → Cancelado | Misma operación/actores | Mismas guardas y versión; no completó devolución | Auditoría/historia, sin fingir recepción; `CancelacionEnvio`/público | C |

No hay otra arista autorizada. Los motivos/actores/identificadores y horas se conservan por los mecanismos de historia ya existentes; este corte no reconstruye ni corrige eventos históricos.

## Operaciones sin transición comercial

- Escanear, consultar, descargar hoja o imprimir etiqueta: lectura/identificación; no acredita recepción ni estado.
- Cotejo parcial/discrepante: registra presencia y observación del bulto; envío sigue Admitido. El último cotejo conforme de todos permite únicamente la fila 1. El recotejo conserva el anterior y no modifica la declaración/tarifa.
- Despachar: hoja Planificada→Despachada/ocupación autorizada; envío sigue AsignadoRuta, sin transferencia de custodia.
- InicioJornada/CargarBulto: inicio de hoja y custodia física respectivamente; envío sigue AsignadoRuta hasta ConfirmarCarga. Si se permiten diferencias, las paradas incompletas se suspenden conservando AsignadoRuta; no se inventa EnDeposito ni un retroceso.
- Reasignar AsignadoRuta: conserva estado con versión/hecho; exige custodia de depósito y nueva asociación válida. EnTransito no se reasigna directamente; NoEntregado exige reprogramación.
- Rendicion, FinJornada, retorno/liberación de vehículo e incidencias de cierre: hechos de custodia/ruta/ocupación, sin una entrega comercial implícita. FinJornada no vence por sí solo una prueba pendiente.
- Evidencia incompleta o tardía: puede avanzar versión y registrar Hecho; no valida después del plazo ni reabre EntregaSinValidacion. Entrega física tardía conciliable tras Cancelado conserva Cancelado y su evidencia; no es una flecha de salida del terminal.

## Evidencia y límites

Las verificaciones por punto de entrada y los resultados de este corte se registran a continuación. La tabla de pares no sustituye HTTP real, transacciones ni RLS. No se interviene en el envío/ruta de la prueba manual del 02/11 ni se cierran Mobile, CU-06, el 401 histórico de arranque o CU pendientes de aceptación. Sin cambios de UI, etiquetas, precios, contratos de bultos, permisos, TLS, sesión, offline ni `permanent=false`.

### Evidencia por requisito y punto de entrada

| Requisito | Pruebas ejecutables que lo acreditan |
| --- | --- |
| Matriz permitida/prohibida y versiones del agregado | `EnvioStateMachineTests.CambiarEstadoAceptaSoloLasFlechasConfirmadas`: todos los pares, lista esperada independiente; `EnvioCancellationRulesTests` y `EnvioLossRulesTests`: terminalidad, hechos físicos y restricciones de cancelación/extravío. |
| Defensa de persistencia y paridad de política | Nueva `ShipmentStatePolicySqlTests.ActualPostgresGuardAgreesWithDomainForEveryPairIncludingNonTransitionUpdates`: 169 pares contra la función instalada en una tabla temporal de prueba, transacción por par. Complementa, no reemplaza, `RestrictedApiRoleCannotPersistAnUndocumentedShipmentTransition`, que modifica Envios real bajo rol API/RLS y comprueba rechazo 23514. |
| CU-10 multi-bulto, discrepancia y recotejo | `RecepcionDepositoHttpTests`: recepción parcial hasta completar todos, discrepancia con custodia física y estado pendiente, recotejo conforme con historia, replay y código ambiguo/ajeno; conserva declaraciones y tarifa. |
| Dos operaciones incompatibles | Nueva `CompleteReceiptAndCommerceCancellationCompeteWithoutPartialStateCustodyOrEvents`: operador y comercio en dos solicitudes/transacciones independientes; una tercera conexión mantiene el lock hasta observar **ambas esperando en pg_stat_activity**. Solo una transición, el otro comando 409, custodia/auditoría/cotejo coherentes con el ganador; replay del ganador y del perdedor no duplica efectos. |
| Fallo al persistir estado o evento | Nueva `FailurePersistingCommercialStateRollsBackReceiptCustodyAndHistoryThenExactRetrySucceeds`: constraint artificial de Envios rechaza EnDeposito; ninguna recepción/custodia/versión/evento parcial y retry exacto tras retirar la falla. La existente `FailureOfReceiptOrCanonicalHistoryRollsBackCustodyStateAndAllEventsAndCanRetry` falla RecepcionesBulto e historia canónica. |
| Planificación, despacho y carga separados | `RutasHttpTests`, `OperacionesRepartoHttpTests` y `.Dec07`: recepción/planificación/despacho/descarga reales, destino/capacidad/versiones, doble asignación, carga ajena, ConfirmarCarga incompleta sin retroceso, cierre antes de salir sin transición inventada. |
| Reprogramación y devolución | `.Dec04` / `.Dec05`: intentos/intervalos/versiones fijadas, nueva ruta, concurrencia cancelación/asignación/devolución, decisión manual y replay, fallo de historia que revierte estado/parada/avisos/outbox. |
| Entrega, evidencia y vencimiento | `OperacionesRepartoHttpTests`, `.PlazoPrueba`: prueba cifrada e inmutable, entrega pendiente tras cerrar jornada, límite exacto de plazo, evidencia tardía, worker restringido/reinicio, versión histórica sin plazo y rollback del vencimiento al fallar historia. |
| Cancelación por todas las entradas | `PushOutboxTests` (parciales CancelacionPush/CancelacionPublicaPush): matriz autenticada, efectos atómicos/auditoría/outbox, terminalidad y cancelación pública por código. `PublicCancellationTests`: tokens/códigos, reintento, revocación y límites. |
| Aislamiento y permisos | Recepción ajena/no autorizada/operario sin permiso, `.Dec05` envío ajeno y `RlsRestrictedHttpFlowTests`: dos comercios y dos operadores, rol API sin superuser/BYPASSRLS, cada actor solo ve su historia. |
| Sincronización | `OperacionesRepartoHttpTests`: UUID/hash, secuencia, versión obsoleta, conflicto sin inventar entrega/custodia, operación tardía tras reprogramación/cancelación. Mobile Core/Application/Api: cola, confirmaciones/proyección y contratos, con límites de prueba portátil indicados abajo. |

La prueba de paridad SQL usa permisos de preparación de fixture para crear la tabla temporal; **no se la presenta como una prueba de permisos de API**. Las pruebas HTTP citadas ejecutan API real y PostgreSQL/PostGIS aislado con roles restringidos donde se señala. Los fallos de escritura se inyectan solo en bases efímeras propias; no se debilitan constraints de producto ni se agrega un modo de bypass.

## Pendientes y decisiones que este corte no inventa

- Fuente y decisiones existentes no autorizan reabrir Entregado, Devuelto, Extraviado, EntregaSinValidacion o Cancelado. Recuperar físicamente algo tras Extraviado requiere una decisión de negocio específica, no una nueva flecha por analogía con conciliación de Cancelado.
- Una versión histórica sin deadline no se vence por un valor inventado. Evidencia tardía no equivale a validación fuera de plazo. La gestión general de incidencias/AP-01 y devoluciones comerciales/AP-04 no se implementa completa para rellenar la matriz.
- CU-10 conserva faltantes/discrepancias como pendientes hasta recotejo conforme; aprobar diferencias como excepción o reescribir pesos/tarifas no está definido por las fuentes ni se habilita aquí.
- Reprogramar y volver a asignar son pasos distintos: reprogramar no acredita recepción física; la nueva asignación verifica la custodia y el horario elegible. No se cambia el estado para eludir un intento/intervalo agotado.
- Las regresiones portátiles y HTTP de sincronización no acreditan Android, cámara/hardware, almacenamiento del dispositivo ni la prueba manual Mobile del 02/11. No se declara cerrado Mobile ni CU-06. El origen del 401 histórico sigue sin determinar.
- Revisión humana de la base, Gentle-AI/Engram y revisión nativa permanecen fuera de la evidencia ejecutada: esas herramientas opcionales no están expuestas en este entorno. Se continúa con inspección, pruebas y diff; no se afirma haberlas usado.

## Recorrido manual posterior, con datos nuevos

1. Crear un envío sintético con dos bultos y sus etiquetas. Consultar/descargar/imprimir/escaneo de identificación debe mantener Admitido.
2. Cotejar uno, registrar discrepancia y luego recotejo conforme: observar custodia, faltante del otro bulto e historia acumulada, sin EnDeposito prematuro. Completar el segundo: un único cambio a EnDeposito, manteniendo declaración/tarifa.
3. Confirmar destino y planificar una ruta válida. Estado AsignadoRuta; despacho no lo cambia ni carga bultos. Confirmar carga física y salida mediante una jornada sintética autorizada: solo entonces EnTransito.
4. Probar una operación incompatible o con versión antigua: mensaje de conflicto, sin efectos parciales. Usar las pruebas automatizadas para la competencia sincronizada y rollback; hacer clic rápido no demuestra concurrencia.
5. En otra jornada sintética, intento fallido y su reprogramación/devolución según las reglas publicadas; cotejar historia y custodia por separado. Probar entrega con/sin prueba y deadline en fixtures con reloj controlado, sin cambiar la política del entorno habitual.
6. Verificar que un actor ajeno no puede operar ni leer el envío y que repetir el comando aplicado no agrega otro evento. No utilizar nunca el envío/ruta de la prueba manual del 02/11 para este recorrido.

## Verificación ejecutada y preparación reproducible

Resultados finales (sin sumar dos veces los tres casos focales incluidos en la integración amplia):

| Suite | Resultado |
| --- | --- |
| Backend UnitTests completo, antes y después | 308 aprobadas, 0 fallidas/omitidas en cada ejecución; incluye el recorrido de los 169 pares del enum contra la lista independiente de aristas |
| Integración amplia Reparto/Envios/Seguimiento, RLS y paridad SQL | 340 aprobadas, 0 fallidas, 4 optativas omitidas; 344 totales, 9m01s. Incluye los cuatro recorridos obligatorios de navegador y los tres casos nuevos |
| Nuevas integraciones PostgreSQL focales | 3 aprobadas: paridad de la función instalada, competencia recepción/cancelación y rollback al fallar el estado |
| PushOutboxTests completo (incluye CancelacionPush/CancelacionPublicaPush) | 50 aprobadas, 0 fallidas/omitidas; 2m43s |
| Frontend ApiClient.Tests completo, sin exclusiones | 476 aprobadas, 0 fallidas, 5 optativas omitidas; 481 casos totales |
| Mobile Core.Tests completo | 36 aprobadas, 0 fallidas/omitidas |
| Mobile Application.Tests completo | 85 aprobadas, 0 fallidas/omitidas; sincronización, cola y proyección portátiles |
| Mobile Api.Tests completo | 63 aprobadas, 0 fallidas/omitidas; contratos/transporte controlado, no dispositivo Android |

Los tres casos de Flota/Depósito corregidos en la base anterior se incluyen en la ejecución completa de frontend y siguen pasando. No se agregaron exclusiones para obtener estos resultados.

### Ajustes necesarios del harness de navegador, sin cambiar producto

La primera selección amplia ejecutó 344 casos: 336 pasaron, 4 fallaron por no tener configurada la ruta a Chromium y 4 optativos se omitieron. Se ajustó la variable de ejecución a la caché existente (`PLAYWRIGHT_BROWSERS_PATH`), sin instalar otro navegador ni deshabilitar TLS/seguridad de autenticación. Al ejecutar los cuatro navegadores con ese prerrequisito aparecieron expectativas anteriores al diseño aceptado:

- Reprogramación/decisión operativa buscaban formularios en la lista `/rutas`; ahora navegan al detalle explícito de la ruta. Después de una devolución la parada está suspendida y el extravío se confirma en el contexto del envío en Depósito, no se inventa una parada activa.
- Reasignación conserva las pruebas de lista/filtros/fecha, navegación al detalle y vuelta, shell único, teclado, 320px, versión obsoleta, doble envío, persistencia e historia/outbox. Se verifican en sus páginas actuales. El selector de teclado abría el nuevo disclosure de identificadores técnicos; ahora se acota a las acciones de la parada. Se comprobó con captura/validez de campos, sin relajar el requisito de formulario válido y sin desborde.
- La identidad visible del envío se verifica en el disclosure vigente, comprobando su UUID exacto en lugar de exigir el antiguo rótulo con distinta capitalización.
- La recepción inicial sigue el enlace real al cotejo individual de CU-10 y confirma el bulto presente; no se restaura el POST masivo para Admitido.
- Alta Commerce ahora verifica la redirección al detalle del envío creado, query `creado=true`, identidad del bulto y contenido del detalle; la confirmación ya no es el antiguo bloque inline `.nr-admission-success`.

Se conservan los casos y las comprobaciones funcionales, de permisos, conflicto y efectos persistidos. Los resultados parciales con errores de preparación/expectativas no se presentan como aprobados. Tras corregirlos se repitió la selección amplia: 340 aprobadas, 0 fallidas y 4 optativas omitidas (344 totales, 9m01s). Los cuatro navegadores obligatorios pasaron, incluidos Commerce/importación, reprogramación, decisión operativa y reasignación. Se verificó visualmente la captura del formulario de reasignación a 320px, además de sus aserciones de teclado, foco y ausencia de desborde; no se presenta esa inspección como prueba de todo dispositivo móvil. Las capturas de escritorio/móvil y TRX son locales, fuera de Git, bajo `/workspace/.cu11-evidence`; no se publican logs, certificados, perfiles ni bases.

### Optativos informados separadamente

La selección de integración mantiene sin activar cuatro optativos: dos recorridos de `GeocodificacionFullStackBrowserTests`, `VehiculosBackofficeBrowserTests.ChromiumTraversesCheckoutBackofficeRealApiAndEphemeralPostgres` y `RecepcionDepositoBrowserTests.RealLabelDecodingAndBackofficeReceiptUseRestrictedApiAndIsolatedPostgres`. Su omisión no equivale a aprobación ni elimina los cuatro navegadores **obligatorios** de `CommerceCsvImportKestrelTests`.

Frontend mantiene los cinco optativos de BaseOperativa, destino/geocodificación, estimación vial, Flota y actualización GPS documentados en [la regresión de Flota/Depósito](../regresion-flota-deposito/01-diagnostico-y-verificacion.md). No se agregaron Skip ni se cambiaron sus condiciones.

### Comandos

Se reutilizaron SDK 10.0.401, Docker PostgreSQL18/PostGIS, Node y Chromium existentes, según las instrucciones de continuidad Cloud. No se ejecutó el instalador para volver a un checkpoint antiguo. No compilar DLLs mientras el harness las esté usando ni ejecutar HTTP y navegador en procesos simultáneos.

```bash
source scripts/cloud/env-agent.sh
export DOTNET_CLI_HOME=/workspace
export NUGET_PACKAGES=/workspace/.cache/nuget-packages
export NUGET_HTTP_CACHE_PATH=/workspace/.cache/nuget-http
export PLAYWRIGHT_BROWSERS_PATH=/workspace/.cache/ms-playwright
export NEXORUTA_PLAYWRIGHT_MODULE="$PWD/scripts/cloud/node_modules/playwright"
dotnet test backend/tests/NexoRuta.UnitTests --no-restore
dotnet test frontend/tests/NexoRuta.ApiClient.Tests --no-restore
dotnet test backend/tests/NexoRuta.IntegrationTests --no-restore --filter 'FullyQualifiedName~NexoRuta.IntegrationTests.Reparto|FullyQualifiedName~NexoRuta.IntegrationTests.Envios|FullyQualifiedName~NexoRuta.IntegrationTests.Seguimiento|FullyQualifiedName~RlsRestrictedHttpFlowTests|FullyQualifiedName~ShipmentStatePolicySqlTests'
dotnet test backend/tests/NexoRuta.IntegrationTests --no-build --no-restore --filter FullyQualifiedName~PushOutboxTests
dotnet test mobile/tests/NexoRuta.Mobile.Core.Tests --no-restore -p:NuGetLockFilePath=obj/cloud.packages.lock.json
dotnet test mobile/tests/NexoRuta.Mobile.Application.Tests -p:NuGetLockFilePath=obj/cloud.packages.lock.json -p:RestoreLockedMode=false
dotnet test mobile/tests/NexoRuta.Mobile.Api.Tests -p:NuGetLockFilePath=obj/cloud.packages.lock.json -p:RestoreLockedMode=false
```

En Mobile Application/Api faltaban assets de restore: se generaron locks portátiles solo en `obj` con las referencias fijadas existentes, sin editar locks, dependencias ni código versionados de Mobile. En un checkout nuevo restaurar primero los demás proyectos con los locks existentes y preparar Chromium como indica la continuidad. Estos comandos usan exclusivamente fixtures propias; no requieren levantar servicios habituales ni conectarse al Windows del usuario.

## Publicación y revisión

Ramas propias `feature/cu11-estados-envio`, sin merges ni modificaciones de ramas ajenas. Backend se publicó antes de actualizar el gitlink del principal; remoto y contenido revisados antes de cada push.

| Repositorio | Rama / commit |
| --- | --- |
| NexoRuta-Backend | `feature/cu11-estados-envio` → `43cdaa82d9e2282f3aea309eb6aa5596c88a0b5e` (incluye política y pruebas) |
| NexoRuta principal | `feature/cu11-estados-envio`; su commit de documentación y gitlink se identifica por la punta publicada de esa rama |
| Frontend (sin cambios) | gitlink `bf36df3d02f6e4c9b098d5545a3483f4c6dea15e` |
| Mobile (sin cambios) | gitlink `74a25f1b5b18c7dfc006cf7df747d73b0ec4910a` |

Para revisar sin integrar: clonar el principal con `--branch feature/cu11-estados-envio --recurse-submodules`, comprobar los gitlinks y ejecutar los comandos anteriores. Comparar Backend contra `9a35b8b292e74a98a55f3e22eab8097bd0d7eb9a` y principal contra `6d179b83f47daaf5331bdddd6f92baac1e2d84b4`. El orden recomendado de integración humana posterior es revisar/aceptar primero la base pendiente, luego Backend CU-11 y finalmente principal con su gitlink y documentación; aquí no se realiza esa integración.
