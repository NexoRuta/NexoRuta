# DEC-07 — Alineación de escritores y reasignaciones con la máquina de estados

**Corte:** 28/10/2026  
**Resultado al cierre inicial de DEC-07:** implementación y verificaciones de esa etapa para un bulto por envío; la conclusión vigente del grafo se actualiza en §9 y en el informe 19. CU-08 y la revisión nativa siguen pendientes.

## 1. Alcance y fuentes

DEC-07 opción A es una decisión del equipo: corregir los escritores para que respeten el diagrama y las decisiones ya aprobadas, sin añadir flechas para justificar el comportamiento anterior. No convierte cada arista del diagrama en texto literal del taller.

Fuentes contrastadas:

- `docs/alcance/Laboratorio__NET_2026.pdf`, §5.2, requisitos 11–12 (página PDF 5, página impresa 4): máquina de estados explícita y eventos de envío inmutables; §§5.3–5.4 para planificación, despacho, carga, entrega, devolución y offline.
- `docs/alcance/Calcs/Casos de Uso - Responsables.xlsm`, hoja `CU obligatorios`, `A10:I11` (CU-07 y CU-08), y hoja `Dependencias`, `A19:I21` (reglas de elegibilidad/capacidad ligadas a datos de bulto y planificación). El libro se revisó sin ejecutar macros ni modificarlo.
- `docs/alcance/Diagramas/maquina-estados-envio-corregida.png`, flechas corregidas incluida la cancelación.
- `docs/auditorias/envios/11-matriz-transiciones-y-brechas.md`, §§3, 5–8 y actualización vigente §14; informes 12–17 para historia, DEC-01 B, DEC-04 A, DEC-05 A, DEC-06 B, permisos, cancelación y hechos tardíos.
- `backend/docs/cu/cierre-jornada.md` (D18); su regla de FinJornada incompatible con la prueba pendiente ya había sido reemplazada por DEC-01 B. El resto de cierre, incidencias y custodia se conserva.

No se identificó una cláusula obligatoria del PDF que exija las aristas extra encontradas en el código. La contradicción concreta de D18 sobre la prueba ya tiene resolución explícita en DEC-01; no se añadió otra interpretación funcional.

## 2. Escritores inspeccionados y controles

- Dominio: `backend/src/NexoRuta.Domain/Envios/Envio.cs` (`CambiarEstado`, `RegistrarReasignacionSinCambioDeEstado`, conciliación física y `Permite`). La matriz queda enumerada en un único predicado y rechaza las salidas no acordadas.
- Persistencia: migración nueva `backend/src/NexoRuta.Infrastructure/Persistence/Migrations/20261028010000_EnforceShipmentTransitionMatrix.cs`, trigger `BEFORE UPDATE OF "Estado"`. La guarda SQL aplica la misma matriz incluso ante un escritor que no llame al método de dominio. No reescribe filas/historia existentes; no se editó una migración histórica.
- Rutas: `EfRutasRepository.cs` (`PlanificarAsync`, `DespacharAsync`, `RecibirAsync`) y `EfRutasRepository.Reasignaciones.cs` (`ReprogramarAsync`, `ReasignarAsync`, `IniciarDevolucionAsync`). Se conservan actor/permiso, operador autenticado, reglas versionadas, destino, carga, capacidad, locks y versión.
- Operaciones de reparto: `EfOperacionesRepartoRepository.Ejecucion.cs` (`FinJornada`, `ConfirmarCarga`, `Rendicion`, `IntentoFallido`, `EntregaFisica` y evidencia). Sus hechos, custodia y estado comercial se distinguen; no se crean movimientos físicos ficticios.
- Flujos conservados: worker DEC-01 para vencimiento; función/endpoint de cancelación y matriz ya cubierta; confirmación DEC-06 desde `EfRutasRepository.Extravio.cs`; decisión manual de devolución DEC-05. No se cambió la política de hechos físicos posteriores a `Extraviado`.

Las escrituras continúan bajo la transacción por solicitud de `RlsTransactionMiddleware` y el patrón `BeginOrJoinAsync`; cambios de envío, parada/ruta, historia y outbox que la operación ya produzca se revierten juntos. La prueba PostgreSQL que intenta una actualización de estado fuera de la matriz como `nexoruta_api` recibe SQLSTATE `23514` con `CK_Envios_TransicionEstado`. No se amplió el permiso general de escritura del rol.

## 3. Matriz de recorrido y brechas

| Transición / operación anterior | Comportamiento acordado | Corrección aplicada | Evidencia | Decisiones o limitaciones pendientes |
|---|---|---|---|---|
| `Admitido → EnDeposito`; recepción registraba además cambios comerciales improcedentes | La recepción confirma admisión física; solo el envío admitido entra a depósito. La custodia representa el movimiento físico. | `RecibirAsync` conserva `Admitido → EnDeposito`; para otros estados registra recepción/custodia solo cuando el flujo lo autoriza y no inventa `Reprogramado`. | `EfRutasRepository.RecibirAsync`; suite de Reparto y matriz SQL. | CU-08 debe definir recepción parcial y agregación multi-bulto. |
| `EnDeposito → AsignadoRuta`; planificación podía tomar envíos sin custodia física en depósito | Planificar una ruta nueva válida exige destino confirmado y elegibilidad, capacidad y custodia de depósito conforme a las reglas existentes. | La planificación exige que todos los bultos del envío estén en depósito; no relaja destino, carga ni capacidad. | `EfRutasRepository.PlanificarAsync`; pruebas de planificación/DEC-04 y test de custodia de reasignación. | Sin varios bultos no se certifica política de agregación. |
| `AsignadoRuta → EnTransito`; despacho | El despacho registra salida/carga real y cambia el estado por la operación de despacho, no por seleccionar un estado. | Se conserva el recorrido de despacho y validación de carga/custodia. Una discrepancia permitida suspende la parada sin retroceder el estado comercial. | `EfRutasRepository.DespacharAsync`; `ConfirmarCargaConDiscrepanciaPermitidaSuspendeSinRetrocederEstado` (PostgreSQL). | CU-08 debe definir faltantes y cargas mixtas por bulto. |
| `EnTransito → Entregado` o `EntregaPendienteValidacion`; entrega física | La operación debe pertenecer a la parada/ruta vigente y respetar la prueba exigida por la versión del envío. El hecho físico y la custodia no son equivalentes a la validación comercial. | `EntregaFisica` conserva `EnTransito` como precondición; registra hecho/recepción UTC y custodia. Solo cambia a entregado con prueba válida; de lo contrario deja pendiente con plazo DEC-01. | `Envio.DeclararEntregaFisica`; `EntregaFisica` en `EfOperacionesRepartoRepository.Ejecucion.cs`; regresiones Reparto. | Operación móvil offline completa sigue pendiente. |
| `EntregaPendienteValidacion → Entregado`; evidencia válida | La prueba requerida, asociada a operación, ruta, custodia y versión, debe recibirse antes del deadline del envío. | Se conserva la validación del servidor y su límite estricto; FinJornada no impide completar una prueba dentro del plazo, pero no reabre la jornada. | DEC-01, `FinJornadaNoBloqueaPruebaCompletaRecibidaAntesDelVencimiento` y prueba de límite/worker. | No se creó una revisión humana no exigida por las fuentes. |
| `EntregaPendienteValidacion → EntregaSinValidacion`; antes FinJornada podía dispararla | Solo el Worker durable vence el deadline fijado desde la primera recepción de servidor y la regla versionada; `now >= vencimiento`. | El cierre conserva pendiente; el Worker solo cambia el estado aún pendiente bajo control concurrente. | DEC-01; worker restringido, reinicio y rollback probados en `OperacionesRepartoHttpTests.PlazoPrueba.cs`. | Versiones históricas sin duración no se vencen automáticamente; política histórica pendiente. No hay salidas añadidas desde `EntregaSinValidacion`. |
| `EnTransito → NoEntregado`; intento fallido | Solo un intento real y válido, con motivos, intervalo y máximo de `Envio.VersionReglasId`, produce el estado fallido. | Se eliminan saltos transitorios desde `NoEntregado`; la operación nueva exige estado vigente `EnTransito`, parada y custodia válidas. | `IntentoFallido`; pruebas DEC-04, retry/replay e intervalo. | La sincronización móvil offline no está completa. |
| `NoEntregado → Reprogramado`; se reintentaba la misma parada o se usaba un cambio técnico de estado | Con DEC-04 A, reprogramar explícitamente exige actor autorizado, intentos disponibles e intervalo; suspende la parada fallida, no suma intento, no reinicia intervalo/reglas ni mueve custodia. | Se conserva el comando de reprogramación específico. No se fabrica intento fallido ni se acepta nueva UUID como autorización para saltar estados. | `ReprogramacionExplicitaEsAtomicamenteVersionadaYNoMueveLaCustodia`; DEC-04. | DEC-05 define la salida manual al agotarse con `DecisionOperativa`; no se habilitan intentos extraordinarios. |
| `NoEntregado → EnDevolucion`; agotamiento automático/manual | Con `IniciarAutomaticamente`, el intento agotado persiste `EnTransito → NoEntregado → EnDevolucion` dentro de la misma transacción. Con `DecisionOperativa`, se queda NoEntregado hasta decisión autorizada; la decisión no mueve custodia. | Se separa el hecho de intento del paso de política; no se usa rendición/recepción para adelantar la decisión. DEC-05 conserva motivo, autorización e idempotencia. | `DecisionOperativaAgotadaIniciaDevolucionUnaSolaVezSinCambiarCustodia`; DEC-05/DEC-04. | La decisión operativa no es recepción física. |
| `Reprogramado → AsignadoRuta`; se intentaba regresar a la ruta anterior | Solo planificación de ruta nueva elegible puede asignar un envío reprogramado. | La asignación requiere nuevo destino/ruta y las condiciones vigentes de depósito/capacidad; el despacho posterior vuelve a validar la tentativa y su intervalo. | `EfRutasRepository.PlanificarAsync`; `FinJornadaLeavesAnUnstartedAssignmentAndItCanBeReassignedWithoutCustodyTransfer`; DEC-04. | Reasignación automática a la ruta anterior no está permitida por este recorrido. |
| `EnDevolucion → Devuelto`; rendición podía confundir decisión con recepción | Devuelto solo al registrar recepción física de la devolución; la decisión de iniciar retorno no traslada custodia. | `RecibirAsync` conserva esta flecha y actualiza la custodia únicamente con la recepción real; Rendicion no fuerza `Reprogramado` ni `Devuelto`. | `RendicionYRecepcionNoEludenElAgotamientoDeDecisionOperativa`; `EfRutasRepository.RecibirAsync`. | CU-08 debe definir agregación si el envío tiene bultos separados. |
| `EnDeposito/AsignadoRuta/EnTransito/EnDevolucion → Extraviado` | DEC-06 B: administrador protegido o `despachador_operador`, permiso vigente, pertenencia, motivo; confirma pérdida sin transferencia física. | Se conserva acción específica, custodia antecedente, suspensión de parada y terminalidad. | DEC-06 `ConfirmationWorksFromEachAllowedOriginAndSuspendsOnlyAnActiveStop` (4 casos); informe 17. | Hechos físicos offline recibidos después de Extraviado siguen pendientes; no se aplicó la excepción de Cancelado. |
| Cancelación desde siete estados habilitados; desde cinco prohibidos; Cancelado terminal | Se conserva la matriz confirmada, control de autorización/código y replay sin efectos duplicados. | La matriz dominio/SQL la protege; DEC-07 no amplía autorización de cancelación ni permite reactivar terminales. | `CancelacionAutenticadaRespetaLaMatrizDeEstados` (12 casos), unidad y pruebas de endpoint. | No hay cambio de regla. |
| Reasignación activa podía `EnTransito → EnTransito` con ruta/repartidor distinto, o cambiar estado para conseguir una ruta | Solo se permite reasignar sin transición si sigue `AsignadoRuta`, la versión es actual, no hay hecho físico, todos los bultos están realmente en depósito y el destino/ruta/capacidad/carga/autorización son válidos. | `RegistrarReasignacionSinCambioDeEstado` avanza la versión, no el estado; suspende la parada fuente y actualiza asociaciones en el mismo comando. No cambia custodia. `EnTransito` y `NoEntregado` no se reasignan. | Test restringido `ReasignacionAntesDeLaSalidaMantieneEstadoYCustodiaYNotificaAlRepartidorActual` (1); página Rutas (12) y navegador (1). | La elegibilidad UI usa `bultos[].custodia`; consulta multi-fecha/multi-bulto completa depende de CU-08 y del contexto de ruta. |
| Atajos históricos: `AsignadoRuta → EnDeposito/Reprogramado`, `EnTransito → Reprogramado`, `NoEntregado → EnTransito`, `Reprogramado → EnDevolucion`, salida a devolución desde entrega o `EntregaSinValidacion`, `EnDeposito → EnDevolucion` | Ninguna flecha adicional se infiere de rendición, recepción, cierre, reassign, un UUID nuevo o una actualización directa. | Se retiraron cambios de estado no autorizados en los escritores identificados y el trigger SQL rechaza también actualizaciones residuales directas. | Matriz unitaria exhaustiva (44); integración restringida `RestrictedApiRoleCannotPersistAnUndocumentedShipmentTransition` (SQLSTATE 23514); cuatro regresiones DEC-07. | No se inventaron salidas para estados sin flecha. |
| Entrega física tardía sobre Cancelado | Conservar el hecho y evidencia, sin reactivar ni producir `Cancelado → Cancelado`. | Se mantuvo la conciliación especial ya implementada; no se borran hechos. DEC-07 no la amplía a Extraviado. | Regresiones de conciliación/cancelación previas; no se modificó este camino. | El comportamiento posterior a Extraviado requiere decisión separada. |

## 4. Cambios API y Backoffice

No se agregó endpoint ni se hizo público un setter de estado. Para que Rutas pueda juzgar custodia cuando la parada fuente no aparece en el filtro de la fecha activa, `GET /api/envios` incorpora el campo aditivo `bultos[].custodia`. Se mapea desde `Bulto.Custodia` en el repositorio y DTOs API; ApiClient lo consume en `BultoResponse`; el snapshot `frontend/contracts/nexoruta.openapi.json` fue regenerado desde el OpenAPI que sirve la aplicación de integración.

La acción de reasignación se presenta en `Rutas.cshtml` solo para `AsignadoRuta` con custodia de todos los bultos en `Deposito`; no se muestra para `EnTransito` ni para un envío reprogramado que necesita una ruta nueva. La página explica que reasignar no hace una transferencia física. Se mantuvieron autorización y endpoint existentes; API y persistencia vuelven a validar todas las precondiciones. El alta individual conserva su respuesta, además de la propiedad de custodia ya aplicada a los DTOs de detalle.

## 5. Verificación observada

Esta tabla conserva el resultado en el corte inicial de DEC-07; los checks repetidos y el navegador positivo posteriores se registran en §8 y prevalecen como evidencia más reciente, sin borrar el historial de 73/86.

Destino Docker confirmado antes de los fixtures: contexto `desktop-linux`, endpoint `npipe:////./pipe/dockerDesktopLinuxEngine`. Las pruebas de integración usaron el fixture PostgreSQL/PostGIS efímero; no se modificaron las instancias de servicios compartidos que aparecían en `docker ps`.

| Evidencia | Resultado | Qué demuestra y qué no |
|---|---:|---|
| Dominio `EnvioStateMachineTests`, `EnvioCancellationRulesTests`, `EnvioLossRulesTests` | 44/44 | Matriz dominio y regresiones; no prueba persistencia por sí sola. |
| Integración focal DEC-07: cuatro métodos de `OperacionesRepartoHttpTests.Dec07.cs` | 4/4 | HTTP de integración, PostgreSQL efímero y rol API restringido; incluye trigger SQL, intento offline anterior, FinJornada/reasignación y discrepancia de carga. |
| Matriz autenticada de cancelación | 12/12 | Casos permitidos y prohibidos llegan a sus verificaciones HTTP con fixture válido. |
| Regresiones DEC-01/04/05/06 focales: vencimiento/Worker, reprogramación, decisión de devolución y cuatro orígenes de extravío | 7/7 | Persistencia, versión/reglas y política de esas dependencias. |
| Reasignación y respuesta de custodia con API restringida | 1/1 | `GET /api/envios` expone custodia real sin elevar el rol; mantiene el efecto de notificación ya existente. No se ejecutó broker externo. |
| Exportación de OpenAPI con `OpenApiContainsTypedRulesRoutesAndExportsTheGeneratedDocument` | 1/1 | El snapshot contiene `BultoDetalle.custodia`; es el documento generado por la aplicación de prueba, no revisión manual de todos los contratos. |
| ApiClient/OpenAPI + páginas Rutas TestServer | 64/64 | Contrato versionado, DTO y gating UI positivo/negativo; no equivale a navegador. |
| Kestrel + Chromium `BackofficeBrowserReprogramsFailedDeliveryAndShowsRuleBoundEligibility` | 1/1 | Navegador, foco/teclado y vista 320 CSS px; comprueba que no se ofrece reasignar un envío que requiere reprogramación. No automatiza el caso visual positivo de reasignación elegible. |
| Reparto/cancelación/reasignación, filtro amplio posterior al cambio de respuesta | 73/86; 13 fallos | No se considera suite limpia. Los rastros observados para las fallas empiezan en `PostgresFixture.CreateDatabaseAsync`: una conexión cerrada durante migración y conexiones posteriores con `57P03` (“database system is not yet accepting connections”). Esas ejecuciones no alcanzaron el endpoint según esos rastros; la causa raíz del reinicio/disponibilidad del fixture no quedó determinada. Las pruebas focales listadas después sí pasaron. |

La evidencia de un filtro amplio anterior de 86/86 se conserva como corte previo, pero no sustituye el resultado posterior de 73/86 tras añadir el campo de custodia. No se verificó publicación/consumo de RabbitMQ/Kafka en este bloque; no se cambió contrato de broker ni se añadieron eventos.

## 6. Límites y pendientes

- **CU-08:** sigue definiendo recepción, carga, capacidad, entrega, devolución, extravío y estado comercial cuando hay más de un bulto. El cambio es para un bulto; la interfaz falla cerrada si no puede demostrar que todos están en depósito.
- **DEC-08/rutas:** las vistas consultan rutas por fecha. La custodia aditiva evita habilitar acción basándose solo en una parada visible, pero una UX de recuperación multi-fecha/multi-bulto requiere diseño propio.
- **Offline:** el cliente móvil y la sincronización completa de operaciones siguen pendientes. Se conserva el tratamiento de la misma operación ya aplicada y la prohibición de ejecutar una operación nueva de una ruta anterior sobre estado/versión ya cambiados.
- **Extraviado:** no se definió qué hacer con un hecho físico recibido después. Esta implementación no lo concilia ni reactiva el estado.
- **Historia y brokers:** estado/historia/outbox continúan en transacciones existentes; no se volvió a probar publicación/consumo externo ni se declara entrega exactamente una vez.
- **Datos históricos:** no se reparan estados ni historia antiguos. Si una fila histórica infringe la matriz, las escrituras futuras que cambien su estado serán rechazadas hasta resolver el dato con una decisión de mantenimiento separada; no se alteraron registros para ocultarlo.
- **Revisión nativa:** sigue pendiente. La verificación manual y las pruebas no son aprobación nativa.

## 7. Archivos y límites del cambio

- Backend: `Envio.cs`; `EfOperacionesRepartoRepository.Ejecucion.cs`; `EfRutasRepository.cs`; `EfRutasRepository.Reasignaciones.cs`; mapeos de detalle de bulto; migración `20261028010000_EnforceShipmentTransitionMatrix.cs`; pruebas de matriz, reparto, cancelación y reasignación.
- Frontend: `BultoResponse.cs`; `RutasModel.cs`; `Rutas.cshtml`; `RutasPagesTests.cs`; snapshot OpenAPI.
- Documentación funcional/auditoría: `backend/docs/cu/cierre-jornada.md`, informes 11, 12 y este informe.
- El cambio preexistente de `mobile` se preservó y no forma parte del alcance.

**Conclusión:** DEC-07 opción A quedó alineada para un bulto con guarda en dominio y base, escritores de ruta/reparto corregidos, custodia explícita en el contrato de lectura y acción Backoffice condicionada. La suite amplia de integración tuvo fallos de disponibilidad del PostgreSQL de pruebas, así que su cierre se apoya en los grupos focales aprobados y mantiene la limitación registrada; no se declara completa la máquina de estados.

**Actualización al corte de §8:** la repetición posterior del filtro produjo 86/86 y el flujo elegible ya cuenta con navegador positivo; esto no identifica la causa del fallo previo ni cierra la máquina completa.

## 8. Seguimiento: estabilidad del fixture y navegador positivo (28/10/2026)

### Diagnóstico del PostgreSQL efímero

Se inspeccionó `backend/tests/NexoRuta.IntegrationTests/Fixtures/PostgresFixture.cs` y se repitió la corrida amplia. Cada fixture de clase inicia su propio contenedor `postgis/postgis:18-3.6-alpine` mediante Testcontainers (estrategia de espera de disponibilidad del paquete); antes de crear la base verifica que el contenedor esté `Running`, abre una conexión no agrupada, consulta identidad/versión del servidor, crea una base única, verifica esa base y luego aplica migraciones. El código usa conexiones/recursos propios por fixture y bases de prueba separadas; no se encontró una carrera de dos migraciones sobre la misma base ni una limpieza SQL destructiva concurrente. La eliminación ocurre al disponer el contenedor.

En la repetición monitoreada se observaron siete IDs de contenedor y 416 muestras de estado: cero muestras `OOMKilled` y cero `Restarting`; los estados finales `removing` correspondieron al teardown normal. Después de la corrida no quedaron contenedores Testcontainers. Los logs PostgreSQL de esta ejecución no contienen `FATAL`, `PANIC`, apagado ni OOM; sí contienen mensajes de `__EFMigrationsHistory` inexistente durante inicializaciones y errores esperados de pruebas que verifican permisos/matriz/historia. Estos últimos no demuestran por sí mismos una readiness defectuosa.

**La causa de la corrida previa 73/86 sigue sin demostrarse.** Sus logs completos, estado de contenedor y eventos Docker no se conservaron en ese momento, por lo que no se puede atribuir el cierre de conexión/`57P03` a reinicio, recursos, readiness o concurrencia. La corrida actual exitosa no explica retrospectivamente aquel incidente. Los 39 fallos de preparación citados por el informe 17 tampoco se equiparan a este incidente sin evidencia común. No se cambió el fixture, no se agregaron reintentos ni se aumentaron timeouts: no se identificó una causa que justificara modificar el ámbito de inicialización y no se modificó producción.

### Corrida amplia exacta

Comando ejecutado desde `backend` (Testcontainers efímeros; Ryuk deshabilitado para el ciclo controlado):

```powershell
$env:TESTCONTAINERS_RYUK_DISABLED='true'
dotnet test tests/NexoRuta.IntegrationTests/NexoRuta.IntegrationTests.csproj --no-restore --filter 'FullyQualifiedName~NexoRuta.IntegrationTests.Reparto|FullyQualifiedName~CancelacionAutenticadaRespetaLaMatrizDeEstados|FullyQualifiedName~CancelacionPublicaAdmiteEnDevolucion|FullyQualifiedName~NexoRuta.IntegrationTests.Notificaciones.ReasignacionPushTests' --logger "trx;LogFileName=dec07-regression.trx" --results-directory C:\Users\Josec\AppData\Local\Temp\nexoruta-dec07-regression-20261028-133714 --logger 'console;verbosity=minimal'
```

Resultado: **86/86 pasaron**, 0 fallidas, duración 5m53s. TRX completo: `C:\Users\Josec\AppData\Local\Temp\nexoruta-dec07-regression-20261028-133714\dec07-regression.trx`; el directorio conserva además `dotnet-test.log`, muestras `postgres-container-state.log` y siete logs `*-postgres.log`. Nota de cobertura: el último término del filtro no encontró casos porque `ReasignacionPushTests` no es el nombre de la clase actual (la clase es `PushOutboxTests`); por tanto, esos tests no están incluidos en el total 86. Se mantuvo la cadena exacta, sin excluir casos del filtro que sí coincidían; el positivo/negativo de reasignación se ejecutó aparte según abajo.

### Reasignación elegible en Kestrel + Chromium

Se agregó `BackofficeBrowserReassignsEligibleShipmentAndPersistsOneEffect` en `backend/tests/NexoRuta.IntegrationTests/Envios/CommerceCsvImportKestrelTests.cs`. El recorrido crea envío, confirma destino, recibe el bulto físicamente en depósito mediante la operación real, y configura rutas fuente/destino válidas; el API Kestrel usa la conexión del rol API restringido del fixture efímero. Backoffice Kestrel y Chromium completan la acción como actor autorizado; no se preparó custodia con escrituras directas.

Comando final sobre los bytes actuales:

```powershell
$env:TESTCONTAINERS_RYUK_DISABLED='true'
dotnet test tests/NexoRuta.IntegrationTests/NexoRuta.IntegrationTests.csproj --no-restore --filter 'FullyQualifiedName~BackofficeBrowserReassignsEligibleShipmentAndPersistsOneEffect' --logger "trx;LogFileName=dec07-browser-final2.trx" --results-directory C:\Users\Josec\AppData\Local\Temp\nexoruta-dec07-browser-final2-20261028-1406 --logger 'console;verbosity=minimal'
```

Resultado **1/1** (26s); TRX: `C:\Users\Josec\AppData\Local\Temp\nexoruta-dec07-browser-final2-20261028-1406\dec07-browser-final2.trx`. El test comprueba en navegador un conflicto por versión obsoleta sin efectos, corrección a la versión vigente, protección contra doble submit, y un reintento de la misma reasignación con versión vieja que vuelve a conflicto. Tras el éxito verifica PostgreSQL: el estado sigue `AsignadoRuta`, la versión avanza exactamente una vez, custodia sigue `Deposito`, la parada fuente queda inactiva y la destino activa, se conserva un hecho de reasignación y no se duplica aviso ni mensaje `PushFcm`. Se revisaron teclado/foco y viewport móvil de 320 CSS px y desktop de 1280 px mediante Chromium.

La regresión negativa de navegación/EnTransito se ejecutó por separado con:

```powershell
dotnet test tests/NexoRuta.IntegrationTests/NexoRuta.IntegrationTests.csproj --no-restore --filter 'FullyQualifiedName~BackofficeBrowserReprogramsFailedDeliveryAndShowsRuleBoundEligibility|FullyQualifiedName~EnTransitoNoSeReasignaYLaRutaOriginalConservaLaEntrega' --logger "trx;LogFileName=dec07-negative.trx" --results-directory C:\Users\Josec\AppData\Local\Temp\nexoruta-dec07-negative-20261028-135401
```

Resultado **2/2**; TRX: `C:\Users\Josec\AppData\Local\Temp\nexoruta-dec07-negative-20261028-135401\dec07-negative.trx`. Cubre que la interfaz no ofrece reasignar un envío que requiere reprogramación y que el endpoint rechaza `EnTransito` conservando la ruta/entrega anterior.

### Estado de cierre de este seguimiento

DEC-07 conserva su implementación; esta ronda completa una corrida amplia exitosa y el caso visual positivo de reasignación elegible. La explicación causal del 73/86 histórico sigue abierta por falta de sus artefactos originales, y el filtro amplio no sustituye el test de reasignación push que no coincidía. No se declara cierre global: continúan pendientes CU-08, cliente offline, política de hechos físicos posteriores a `Extraviado`, verificación externa de brokers, otros recorridos/decisiones de la máquina y revisión nativa.

## 9. Cierre posterior del grafo y PushOutboxTests (2026-10-28)

El informe 19, docs/auditorias/envios/19-cierre-maquina-estados.md, actualiza la conclusión funcional: las flechas acordadas y sus guardas quedan cerradas para servidor/API y Backoffice, DEC-01 B/DEC-04 A/DEC-05 A/DEC-06 B/DEC-07 A, cardinalidad actual de un bulto. Esta sección sustituye la conclusión provisional de §8 que mantenía abiertos otros recorridos; no reemplaza ni altera la evidencia de estabilidad del fixture o del navegador allí registrada.

Se corrigió el filtro incompleto de Push ejecutando directamente FullyQualifiedName~PushOutboxTests: 50/50, PostgreSQL efímero, TRX y diagnóstico en el informe 19 §4. La ejecución cubre entrega/reintento de los efectos de outbox bajo transportes controlados, no aceptación externa real de Firebase/RabbitMQ/Kafka. Las adaptaciones de los tests corrigieron expectativas/preparación frente a la guarda de matriz, la regla de no reasignar EnTransito, el límite de login y la comparación del reloj SQL; no se modificó producción.

La causa de 73/86 sigue explícitamente sin demostrar. Ni la corrida 86/86 ni el nuevo 50/50 la explican. CU-08, cliente móvil offline, política de hechos tardíos tras Extraviado, publicación/consumo externo y revisión nativa continúan pendientes e independientes del cierre del grafo en el alcance indicado.