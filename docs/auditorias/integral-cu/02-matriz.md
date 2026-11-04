# Matriz integral de requisitos

Base exacta auditada: principal `13aefdb`, Backend `bf4da61`, Frontend `1ca0172`, Mobile `74a25f1`. Ningún estado equivale a aceptación. Los IDs CU/AP/NFR/OPT se toman de la planilla, no se crean numeraciones de negocio.

## CU obligatorios: 30/30

| CU / requisito | Fuente exacta | Implementación y persistencia encontradas | Interfaz / entrada | Evidencia disponible y límite | Estado / recorrido |
|---|---|---|---|---|---|
| CU-01 — Comercios y usuarios | PDF §5.1 nº1; XLSM «CU obligatorios» A4:I4 | UsuariosController, RolesController, OrganizacionPropiaController; Usuarios, AccesosUsuario, Roles y políticas RLS | /usuarios; /roles; Admin /operadores, /comercios; autogestión /mi-comercio | UsuariosHttpTests, RolesHttpTests, OrganizacionPropiaHttpTests. Pruebas disponibles no implican aceptación; ejecución nueva en 05. | **Pendiente de validación humana**; [caso manual](03-guia-manual.md#cu-01) |
| CU-02 — Zonas y franjas | PDF §5.1 nº2; XLSM «CU obligatorios» A5:I5 | ZonasCoberturaController, ZonaCobertura; ZonasCobertura, FranjasEntrega, ZonasCoberturaRevisiones | /zonas; /api/configuracion/zonas y /{id}/franjas | ZonasCoberturaHttpTests, ZonaCoberturaPostgisTests, UruguayCatalogAndTerritoryTests. Pruebas disponibles no implican aceptación; ejecución nueva en 05. | **Pendiente de validación humana**; [caso manual](03-guia-manual.md#cu-02) |
| CU-03 — Tarifas configurables | PDF §5.1 nº3; XLSM «CU obligatorios» A6:I6 | TarifarioController, CalculadoraTarifas; TarifariosOperador, VersionesTarifario, tarifas y ajustes versionados | /tarifas, /tarifas/borrador, /tarifas/simular; /api/configuracion/tarifas | TarifarioHttpTests, TarifarioPersistenceTests, CalculadoraTarifasTests. Pruebas disponibles no implican aceptación; ejecución nueva en 05. | **Pendiente de validación humana**; [caso manual](03-guia-manual.md#cu-03) |
| CU-04 — Reglas operativas | PDF §5.1 nº4; XLSM «CU obligatorios» A7:I7 | ReglasOperativasController, VersionReglasOperativas; ReglasOperativasOperador, versiones, requisitos y motivos | /reglas-operativas; /api/configuracion/reglas-operativas | ReglasOperativasHttpTests, ReglasEnvioAdmisionHttpTests. Pruebas disponibles no implican aceptación; ejecución nueva en 05. | **Pendiente de validación humana**; [caso manual](03-guia-manual.md#cu-04) |
| CU-05 — Identidad visual | PDF §5.1 nº5; XLSM «CU obligatorios» A8:I8 | IdentidadVisualOperadorController, IdentidadVisualPublicaResponse; VersionesIdentidadVisualOperador y consumidores por tenant | /identidad-visual; Commerce; Tracking; comunicaciones | IdentidadVisualOperadorHttpTests, IdentidadVisualPagesTests. Pruebas disponibles no implican aceptación; ejecución nueva en 05. | **Brecha encontrada**; [caso manual](03-guia-manual.md#cu-05) |
| CU-06 — Repartidores y vehículos | PDF §5.1 nº6; XLSM «CU obligatorios» A9:I9 | FlotaController, RepartidoresController, EfRutasRepository.Flota; Vehiculos, accesos de repartidor, OcupacionesRuta e historial | /repartidores; /vehiculos; /flota; /api/repartidores, /api/reparto/vehiculos, /api/reparto/flota | CapacidadVigenteHttpTests, OcupacionFlotaHttpTests; navegadores Vehiculos/Flota. Pruebas disponibles no implican aceptación; ejecución nueva en 05. | **Pendiente de validación humana**; [caso manual](03-guia-manual.md#cu-06) |
| CU-07 — Alta de envíos | PDF §5.2 nº7; XLSM «CU obligatorios» A10:I10 | CrearEnvioUseCase, ImportarEnviosUseCase, CsvEnviosParser; Envios, identidades de importación v2 y outbox en transacción | /envios/crear; /envios/importar; POST /api/envios y /api/envios/importaciones | ShipmentCsvImportHttpTests, CommerceCsvImportKestrelTests, AdmissionSelectsAdjustsQuotesSavesAndReopensBeforeShipping. Pruebas disponibles no implican aceptación; ejecución nueva en 05. | **Pendiente de validación humana**; [caso manual](03-guia-manual.md#cu-07) |
| CU-08 — Bultos | PDF §5.2 nº8; XLSM «CU obligatorios» A11:I11 | CrearEnvioRequest, Bulto, EtiquetasEnvioPdf; Bultos con UUID, código, peso y dimensiones | Alta multibulto; etiquetas; recepción y ruta | CrearEnvioUseCaseTests, EtiquetasEnvioHttpTests, RecepcionDepositoHttpTests. Pruebas disponibles no implican aceptación; ejecución nueva en 05. | **Pendiente de validación humana**; [caso manual](03-guia-manual.md#cu-08) |
| CU-09 — Cálculo de tarifa | PDF §5.2 nº9; XLSM «CU obligatorios» A12:I12 | TarifasAdmision, CalculadoraTarifas; TarifasEnvio append-only; procedencia tarifaria/geográfica | Cotización en alta; POST /api/envios/cotizacion; GET /api/envios/{id}/tarifa e historial | TarifaAdmisionHttpTests, AdmissionSelectsAdjustsQuotesSavesAndReopensBeforeShipping. Pruebas disponibles no implican aceptación; ejecución nueva en 05. | **Pendiente de validación humana**; [caso manual](03-guia-manual.md#cu-09) |
| CU-10 — Recepción en depósito | PDF §5.2 nº10; XLSM «CU obligatorios» A13:I13 | EfRutasRepository.Recepcion, RecepcionModel; RecepcionesBulto inmutable, custodia/versiones e historia canónica al completar | /deposito/recepcion; GET /api/deposito/consulta; POST /api/deposito/bultos/{id}/recepcion | RecepcionDepositoHttpTests y RecepcionDepositoBrowserTests. Pruebas disponibles no implican aceptación; ejecución nueva en 05. | **Pendiente de validación humana**; [caso manual](03-guia-manual.md#cu-10) |
| CU-11 — Estado del envío | PDF §5.2 nº11; XLSM «CU obligatorios» A14:I14 | TransicionesEstadoEnvio, Envio, guard_shipment_state_transition; Envios, versiones, hechos físicos y trigger de historia | Comandos de recepción, ruta, móvil, cancelación y decisiones; sin setter de estado | EnvioStateMachineTests, ShipmentStatePolicySqlTests, RecepcionDepositoHttpTests.Estados. Pruebas disponibles no implican aceptación; ejecución nueva en 05. | **Pendiente de validación humana**; [caso manual](03-guia-manual.md#cu-11) |
| CU-12 — Eventos del envío | PDF §5.2 nº12; XLSM «CU obligatorios» A15:I15 | EnvioEvento, triggers, SetShipmentHistoryContextAsync; EnvioEventos append-only, origen/responsable/fecha/GPS según operación | Sin endpoint general de eventos encontrado; consulta de recepción y verificación PostgreSQL en fixture | EnvioEventsHttpTests, EnvioHistoryMigrationTests, RlsRestrictedHttpFlowTests. Pruebas disponibles no implican aceptación; ejecución nueva en 05. | **Pendiente de validación humana**; [caso manual](03-guia-manual.md#cu-12) |
| CU-13 — Armar rutas | PDF §5.3 nº13; XLSM «CU obligatorios» A16:I16 | GestionarRutasUseCase, EfRutasRepository.PlanificarAsync; HojasRuta, ParadasRuta, recursos y snapshot temporal | /rutas/planificar; POST /api/rutas | RutasHttpTests, BasePlanificacionHttpTests. Pruebas disponibles no implican aceptación; ejecución nueva en 05. | **Pendiente de validación humana**; [caso manual](03-guia-manual.md#cu-13) |
| CU-14 — Validar restricciones | PDF §5.3 nº14; XLSM «CU obligatorios» A17:I17 | CapacidadCarga, RestriccionesTemporales, VentanaRuta; Revisión histórica de zona/cargo, versión de configuración y snapshot de ruta | Planificación, reasignación, despacho y confirmación de carga | VentanaRutaTests, HistoricalCoverageRequiresArrivalAndWholeServiceInsideWindow, CapacidadVigenteHttpTests. Pruebas disponibles no implican aceptación; ejecución nueva en 05. | **Brecha encontrada**; [caso manual](03-guia-manual.md#cu-14) |
| CU-15 — Evitar doble asignación | PDF §5.3 nº15; XLSM «CU obligatorios» A18:I18 | Bloqueo PostgreSQL de operador e índice único de parada activa; ParadasRuta activas + Envios en transacción | POST /api/rutas concurrente; reasignación | DosPlanificacionesConcurrentesSoloAsignanUnaVez. Pruebas disponibles no implican aceptación; ejecución nueva en 05. | **Pendiente de validación humana**; [caso manual](03-guia-manual.md#cu-15) |
| CU-16 — Ordenar paradas | PDF §5.3 nº16; XLSM «CU obligatorios» A19:I19 | HojaRuta.AgregarParada y PlanTemporal; Orden persistido y snapshot temporal inicial | /rutas/planificar; orden y llegada manual en detalle | ExactStopLimitUsesShipmentsAndPreservesExplicitOrder, PlanTemporalTests. Pruebas disponibles no implican aceptación; ejecución nueva en 05. | **Pendiente de validación humana**; [caso manual](03-guia-manual.md#cu-16) |
| CU-17 — Despachar ruta | PDF §5.3 nº17; XLSM «CU obligatorios» A20:I20 | EfRutasRepository.DespacharAsync; HojasRuta Despachada + OcupacionRuta e historial | Detalle /rutas/{id}; POST /api/rutas/{id}/despacho; /api/mobile/rutas | RutasHttpTests, OcupacionFlotaHttpTests. Pruebas disponibles no implican aceptación; ejecución nueva en 05. | **Pendiente de validación humana**; [caso manual](03-guia-manual.md#cu-17) |
| CU-18 — Descargar ruta | PDF §5.4 nº18; XLSM «CU obligatorios» A21:I21 | HojaRutaViewModel, repositorio local y ApiReparto; SQLite y snapshot de hoja/reglas | MAUI hoja del día; GET /api/mobile/rutas y /{id} | Mobile Api/Application Tests; RutasHttpTests. Pruebas disponibles no implican aceptación; ejecución nueva en 05. | **Pendiente de validación humana**; [caso manual](03-guia-manual.md#cu-18) |
| CU-19 — Escanear carga | PDF §5.4 nº19; XLSM «CU obligatorios» A22:I22 | HojaRutaViewModel, EfOperacionesRepartoRepository; Custodia Bultos y operación idempotente por jornada/secuencia | MAUI escaneo de carga; operaciones CargarBulto/ConfirmarCarga | OperacionesRepartoHttpTests; Mobile Application/Core Tests. Pruebas disponibles no implican aceptación; ejecución nueva en 05. | **Pendiente de validación humana**; [caso manual](03-guia-manual.md#cu-19) |
| CU-20 — Registrar entrega | PDF §5.4 nº20; XLSM «CU obligatorios» A23:I23 | Envio.DeclararEntregaFisica, AplicarPrueba, GuardarEvidenciaAsync; PruebasEntrega, EvidenciasReparto cifradas, estado y custodia | MAUI entrega; operaciones EntregaFisica/EvidenciaEntrega; PUT evidencias | OperacionesRepartoHttpTests; AuditoriaIntegral_InvalidPngMustNotValidateDelivery. Pruebas disponibles no implican aceptación; ejecución nueva en 05. | **Brecha encontrada**; [caso manual](03-guia-manual.md#cu-20) |
| CU-21 — Registrar intento fallido | PDF §5.4 nº21; XLSM «CU obligatorios» A24:I24 | ResumenIntentosEntrega y catálogo de reglas del envío; OperacionesJornada, estado NoEntregado y devolución si corresponde | MAUI intento fallido; operación IntentoFallido | OperacionesRepartoHttpTests, ReasignacionPushTests. Pruebas disponibles no implican aceptación; ejecución nueva en 05. | **Pendiente de validación humana**; [caso manual](03-guia-manual.md#cu-21) |
| CU-22 — Devolución y rendición | PDF §5.4 nº22; XLSM «CU obligatorios» A25:I25 | EfOperacionesRepartoRepository, EfRutasRepository.RecibirAsync, flota; Custodia Repartidor→PendienteDeposito→Deposito y ocupación separada | MAUI Rendicion/FinJornada; /deposito; /flota | OperacionesRepartoHttpTests, OcupacionFlotaHttpTests, ConciliacionEntregaHttpTests. Pruebas disponibles no implican aceptación; ejecución nueva en 05. | **Pendiente de validación humana**; [caso manual](03-guia-manual.md#cu-22) |
| CU-23 — Posición del vehículo | PDF §5.4 nº23; XLSM «CU obligatorios» A26:I26 | TrackingJornada, ServicioUbicacion, EfOperacionesRepartoRepository; OperacionesJornada con posición/precisión/instantes | MAUI tracking; operación Posicion; estimaciones B5 | Mobile Application/Core; EstimacionesVialesHttpTests. Pruebas disponibles no implican aceptación; ejecución nueva en 05. | **Pendiente de validación humana**; [caso manual](03-guia-manual.md#cu-23) |
| CU-24 — Sincronización diferida | PDF §5.4 nº24; XLSM «CU obligatorios» A27:I27 | SincronizadorJornada y RepositorioJornadasSqlite.Sincronizacion; SQLite/archivos cifrados; secuencias, hash, conflicto explícito | MAUI cola offline; API operaciones/evidencias | Mobile Core 36, Application 85, Api 63; OperacionesRepartoHttpTests. Pruebas disponibles no implican aceptación; ejecución nueva en 05. | **Pendiente de validación humana**; [caso manual](03-guia-manual.md#cu-24) |
| CU-25 — Seguimiento público | PDF §5.5 nº25; XLSM «CU obligatorios» A28:I28 | SeguimientoPublicoController, SeguimientoEstadoResponse; Enlaces opacos y estado actual RLS mediante función pública | Tracking /seguimiento/{token}; GET /api/public/seguimiento/{token} | PublicCancellationTests, EnlaceSeguimientoPostgresTests, ConsultarSeguimientoPublicoUseCaseTests. Pruebas disponibles no implican aceptación; ejecución nueva en 05. | **Brecha encontrada**; [caso manual](03-guia-manual.md#cu-25) |
| CU-26 — Reprogramación | PDF §5.5 nº26; XLSM «CU obligatorios» A29:I29 | RutasController.Reprogramar exige envios.gestionar; Tracking carece del formulario; No se encontró solicitud pública persistida | No se encontró solicitud pública de reprogramación; solo POST operador /api/envios/{id}/reprogramacion | Pruebas de reprogramación OPERATIVA no prueban al destinatario. Pruebas disponibles no implican aceptación; ejecución nueva en 05. | **No implementado**; [caso manual](03-guia-manual.md#cu-26) |
| CU-27 — Avisos al destinatario | PDF §5.5 nº27; XLSM «CU obligatorios» A30:I30 | Program Worker, OutboxMessageTypes/OutboxHandlerRegistry; No se encontró entrega de avisos por transiciones a destinatarios | Worker: seguimiento, recuperación, código cancelación y push repartidor; no avisos de estado al destinatario | CreacionAutomaticaSeguimientoTests prueba crear enlace, no avisos CU-27. Pruebas disponibles no implican aceptación; ejecución nueva en 05. | **No implementado**; [caso manual](03-guia-manual.md#cu-27) |
| CU-28 — Avisos a comercios | PDF §5.5 nº28; XLSM «CU obligatorios» A31:I31 | OutboxMessageTypes y Worker sin contrato webhook de cambio de estado; Sin modelo de suscripción/entrega HTTP por comercio localizado | No se encontró configuración de suscripción, historial/reenvío webhook ni receptor de prueba | No hay prueba de firma/reintento/reenvío de webhook de comercio. Pruebas disponibles no implican aceptación; ejecución nueva en 05. | **No implementado**; [caso manual](03-guia-manual.md#cu-28) |
| CU-29 — Tablero en vivo | PDF §5.5 nº29; XLSM «CU obligatorios» A32:I32 | Catálogo Backoffice sin tablero; API sin Hub/MapHub; Posiciones/estimaciones puntuales no constituyen proyección en vivo | /flota muestra disponibilidad; no tablero de posición/riesgo SignalR localizado | B5/Flota prueban consultas y snapshots; no SignalR multinstancia. Pruebas disponibles no implican aceptación; ejecución nueva en 05. | **No implementado**; [caso manual](03-guia-manual.md#cu-29) |
| CU-30 — Reportes y liquidación | PDF §5.5 nº30; XLSM «CU obligatorios» A33:I33 | Navegaciones y API sin reportes/liquidaciones; TarifaAplicada muestra cargo individual; Cargos/historia son insumos, sin agregados/ledger localizado | No reportes de cumplimiento/motivos/volumen/liquidación ni cuenta corriente localizados | TarifaAdmisionHttpTests conserva cargos; no prueba liquidación. Pruebas disponibles no implican aceptación; ejecución nueva en 05. | **No implementado**; [caso manual](03-guia-manual.md#cu-30) |

## Alcance aplicaciones

### AP-01 — Gestión de incidencias

Fuente: XLSM «Alcance aplicaciones» fila 4; PDF §4. Capacidad: Gestión de incidencias; Descripción: Registrar y resolver incidencias desde el backoffice.; Módulo: M06; Aplicación: Backoffice; Sección: 4; Estado de definición: Detalle funcional a diseñar.

**Implementación/evidencia encontrada:** Parcial: decisiones de devolución/extravío e incidencias de cierre en Rutas/Depósito; no sistema general de incidencias encontrado.

**Estado:** Pendiente de validación humana. **Validación ejecutable/precondiciones y límites:** CU-11/21/22; crear intento fallido, decidir devolución, rendir/recibir y revisar trazabilidad; evaluar catálogo y resolución general con negocio.

### AP-02 — Etiquetas

Fuente: XLSM «Alcance aplicaciones» fila 5; PDF §4. Capacidad: Etiquetas; Descripción: Imprimir etiquetas de envíos desde el portal del comercio.; Módulo: M02; Aplicación: Portal Blazor; Sección: 4; Estado de definición: Detalle funcional a diseñar.

**Implementación/evidencia encontrada:** EtiquetasEnvioPdf y GET /api/envios/{id}/etiquetas; botones Commerce/Backoffice.

**Estado:** Pendiente de validación humana. **Validación ejecutable/precondiciones y límites:** CU-08: imprimir PDF, cotejar UUID/código/peso y leer QR con lector REAL; prueba automatizada decodifica PDF real sin hardware.

### AP-03 — Consulta del comercio

Fuente: XLSM «Alcance aplicaciones» fila 6; PDF §4. Capacidad: Consulta del comercio; Descripción: El comercio consulta y sigue exclusivamente sus propios envíos.; Módulo: M02; Aplicación: Portal Blazor; Sección: 4; Estado de definición: Detalle funcional a diseñar.

**Implementación/evidencia encontrada:** MisEnvios, lectura Envios/RLS, cargos e historia tarifaria; no pantalla/endpoint general de eventos encontrado.

**Estado:** Brecha encontrada. **Validación ejecutable/precondiciones y límites:** CU-07/12/25: C1 y C2 no ven envíos ajenos; contrastar seguimiento completo sin confundir cargo con historial de eventos.

### AP-04 — Devoluciones del comercio

Fuente: XLSM «Alcance aplicaciones» fila 7; PDF §4. Capacidad: Devoluciones del comercio; Descripción: El comercio consulta y gestiona devoluciones de sus envíos.; Módulo: M02; Aplicación: Portal Blazor; Sección: 4; Estado de definición: Detalle funcional a diseñar.

**Implementación/evidencia encontrada:** Comercio consulta estado; iniciar devolución es operación del operador, no se encontró gestión propia por comercio.

**Estado:** Brecha encontrada. **Validación ejecutable/precondiciones y límites:** CU-22: buscar solicitud/gestión en Commerce; registrar ausencia antes de acreditar devolución autogestionada.

### AP-05 — Suscripción de avisos

Fuente: XLSM «Alcance aplicaciones» fila 8; PDF §4. Capacidad: Suscripción de avisos; Descripción: El comercio configura los avisos automáticos a sus sistemas.; Módulo: M05; Aplicación: Portal Blazor; Sección: 4; Estado de definición: Detalle funcional a diseñar.

**Implementación/evidencia encontrada:** No se encontraron suscripción/eventos, firma, historial o reenvío de webhook por comercio.

**Estado:** No implementado. **Validación ejecutable/precondiciones y límites:** CU-28, H04; validar contra receptor local tras implementación, no enviar HTTP a servicios ajenos.

### AP-06 — Cuenta corriente

Fuente: XLSM «Alcance aplicaciones» fila 9; PDF §4. Capacidad: Cuenta corriente; Descripción: El comercio consulta cuenta corriente y liquidaciones.; Módulo: M06; Aplicación: Portal Blazor; Sección: 4; Estado de definición: Detalle funcional a diseñar.

**Implementación/evidencia encontrada:** TarifaAplicada muestra cargos individuales; no cuenta corriente/liquidaciones.

**Estado:** No implementado. **Validación ejecutable/precondiciones y límites:** CU-30, H05: verificar saldos y liquidación contra sumas independientes cuando exista ledger.

### AP-07 — Ventana estimada

Fuente: XLSM «Alcance aplicaciones» fila 10; PDF §4. Capacidad: Ventana estimada; Descripción: El destinatario ve la ventana horaria estimada en el seguimiento público.; Módulo: M05; Aplicación: Blazor público; Sección: 4; Estado de definición: Detalle funcional a diseñar.

**Implementación/evidencia encontrada:** SeguimientoEstadoResponse contiene Estado e Identidad únicamente.

**Estado:** No implementado. **Validación ejecutable/precondiciones y límites:** CU-25, H03: verificar que se publique una ventana verificable y no ETA inventada desde disponibilidad.

### AP-08 — Navegación de ruta

Fuente: XLSM «Alcance aplicaciones» fila 11; PDF §4. Capacidad: Navegación de ruta; Descripción: El repartidor navega entre las paradas de la hoja de ruta.; Módulo: M04; Aplicación: .NET MAUI; Sección: 4; Estado de definición: Detalle funcional a diseñar.

**Implementación/evidencia encontrada:** HojaRutaViewModel y navegación MAUI; no ejecutada en Android.

**Estado:** Pendiente de validación humana. **Validación ejecutable/precondiciones y límites:** CU-18/23/24: desplazarse entre paradas offline y recuperar; proveedor externo real/hardware separados.

### AP-09 — Cierre diario

Fuente: XLSM «Alcance aplicaciones» fila 12; PDF §4. Capacidad: Cierre diario; Descripción: El worker ejecuta el cierre diario de la operación.; Módulo: M06; Aplicación: Worker; Sección: 4; Estado de definición: Detalle funcional a diseñar.

**Implementación/evidencia encontrada:** ProofValidationDeadlineWorker vence pruebas; no cierre diario agregado de operación localizado.

**Estado:** No implementado. **Validación ejecutable/precondiciones y límites:** CU-30; no confundir vencimiento individual de prueba con cierre diario único.


## No funcionales

### NFR-01 — Plataforma y arquitectura

Fuente: XLSM «No funcionales» fila 4; PDF §6.1. Sección: 6.1; Bloque: Plataforma y arquitectura; Módulo de referencia: M01; Módulos afectados: Todos; Exigencia resumida: NET 10; monolito modular API/web; worker separado por cola; dominio independiente; prueba de arquitectura; ADR; Docker Compose..

**Implementación/evidencia encontrada:** NET10, capas y worker separado presentes; Compose e infraestructura en deploy/. Dos pruebas de dependencia pasan, suite/restore de arquitectura fallan H07/H08.

**Estado:** Brecha encontrada. **Validación ejecutable/precondiciones y límites:** Técnico: restaurar con --locked-mode y ejecutar ArchitectureTests; verificar Docker Compose completo posteriormente sin secretos ni volúmenes operativos.

### NFR-02 — Presentación web

Fuente: XLSM «No funcionales» fila 5; PDF §6.2. Sección: 6.2; Bloque: Presentación web; Módulo de referencia: M01; Módulos afectados: M01, M02, M05, M06; Exigencia resumida: Backoffice Razor Pages; portal y público Blazor; ADR del modo de renderizado y su efecto operativo..

**Implementación/evidencia encontrada:** Razor Pages Backoffice; Blazor Commerce/Tracking; DESIGN y decisiones de arquitectura existentes.

**Estado:** Pendiente de validación humana. **Validación ejecutable/precondiciones y límites:** Navegar dos sesiones y revisar persistencia/escalado del renderizado; los nueve optativos no prueban varias instancias ni consumo medido.

### NFR-03 — Seguridad

Fuente: XLSM «No funcionales» fila 6; PDF §6.3. Sección: 6.3; Bloque: Seguridad; Módulo de referencia: M01; Módulos afectados: Todos; Exigencia resumida: OIDC/OAuth 2.1 con PKCE o Identity; autorización API por rol/tenant/comercio; secretos, TLS, CORS, rate limit, cabeceras y cifrado móvil..

**Implementación/evidencia encontrada:** Identity/JWT, políticas API, RLS, limitadores PostgreSQL y cifrado de archivos móvil/evidencias; sesión por generación.

**Estado:** Pendiente de validación humana. **Validación ejecutable/precondiciones y límites:** CU-01/24/25 y circuito sesión: credenciales/permisos/tenant, CSRF, open redirect, HTTPS/CORS/cabeceras; cifrado móvil en dispositivo no validado aquí.

### NFR-04 — Persistencia

Fuente: XLSM «No funcionales» fila 7; PDF §6.4. Sección: 6.4; Bloque: Persistencia; Módulo de referencia: M02; Módulos afectados: M02, M03, M04; Exigencia resumida: Base principal con EF Core y migraciones; SQLite móvil; concurrencia optimista demostrada..

**Implementación/evidencia encontrada:** EF/migraciones y versiones; PostgresFixture crea bases propias; SQLite Mobile con sincronización.

**Estado:** Pendiente de validación humana. **Validación ejecutable/precondiciones y límites:** Competencia con barrera PostgreSQL en CU-10/15; revisar migración desde corte anterior y SQLite real. No migrar bases ajenas ni borrar legados.

### NFR-05 — Multitenancy

Fuente: XLSM «No funcionales» fila 8; PDF §6.5. Sección: 6.5; Bloque: Multitenancy; Módulo de referencia: M01; Módulos afectados: Todos; Exigencia resumida: Estrategia y resolución de tenant; aislamiento lectura/escritura y de comercios; tests, branding, migraciones y dos operadores..

**Implementación/evidencia encontrada:** ADR-MT-001: RLS por fila Envios (operador+comercio), roles restringidos, funciones acotadas.

**Estado:** Pendiente de validación humana. **Validación ejecutable/precondiciones y límites:** Dos operadores/configuraciones y C1/C2; lectura/escritura por ID ajeno denegadas. 73 focales incluyen rol restringido, no auditoría de todas las tablas/roles.

### NFR-06 — Configurabilidad

Fuente: XLSM «No funcionales» fila 9; PDF §6.6. Sección: 6.6; Bloque: Configurabilidad; Módulo de referencia: M01; Módulos afectados: M01, M02, M04, M05; Exigencia resumida: Tarifas y reglas editables en caliente y versionadas; envíos previos conservan tratamiento..

**Implementación/evidencia encontrada:** Versiones de tarifas, reglas y revisión geográfica; cargos/historia append-only.

**Estado:** Pendiente de validación humana. **Validación ejecutable/precondiciones y límites:** CU-03/04/09/14: publicar nuevas versiones y comprobar originales, sin backfill inventado. Resolver semántica de compromiso D-P01.

### NFR-07 — Caché distribuido

Fuente: XLSM «No funcionales» fila 10; PDF §6.7. Sección: 6.7; Bloque: Caché distribuido; Módulo de referencia: M05; Módulos afectados: M01, M05; Exigencia resumida: Dos casos de uso con perfiles distintos, expiración e invalidación y métricas hit/miss..

**Implementación/evidencia encontrada:** Solo se localizó IMemoryCache para geocodificación Geoapify; no caché distribuido de dos CU ni perfiles/invalidación/hit-miss exigidos.

**Estado:** No implementado. **Validación ejecutable/precondiciones y límites:** H06: revisar registro DI y dependencias; tras implementar calentar dos API y comparar hit/miss e invalidación bajo cambios, no atribuir éxito al caché local.

### NFR-08 — Mensajería y worker

Fuente: XLSM «No funcionales» fila 11; PDF §6.8. Sección: 6.8; Bloque: Mensajería y worker; Módulo de referencia: M05; Módulos afectados: M02, M04, M05, M06; Exigencia resumida: Outbox; consumidor idempotente; reintentos crecientes, cola de fallidos y panel de reintento..

**Implementación/evidencia encontrada:** Outbox, leases/handlers, Rabbit/Kafka/Push y dead-letter de recuperación de contraseña presentes; cobertura por tipo desigual.

**Estado:** Brecha encontrada. **Validación ejecutable/precondiciones y límites:** Receptor local: persistir negocio, observar outbox y entrega, detener worker/repetir; CU-27/28 faltan y no se ejercitaron brokers reales en esta revisión.

### NFR-09 — Avisos a comercios

Fuente: XLSM «No funcionales» fila 12; PDF §6.9. Sección: 6.9; Bloque: Avisos a comercios; Módulo de referencia: M05; Módulos afectados: M02, M05; Exigencia resumida: Suscripción por comercio y evento; firma, reintentos, fallidos, historial/reenvío y receptor de prueba..

**Implementación/evidencia encontrada:** No contratos/handlers/modelos de suscripción y entrega webhook por comercio localizados.

**Estado:** No implementado. **Validación ejecutable/precondiciones y límites:** CU-28/H04: firma, tipos, backoff, fallidos, reenvío e historial, con receptor local e aislamiento.

### NFR-10 — Tiempo real

Fuente: XLSM «No funcionales» fila 13; PDF §6.10. Sección: 6.10; Bloque: Tiempo real; Módulo de referencia: M06; Módulos afectados: M04, M06; Exigencia resumida: SignalR con autenticación, autorización, aislamiento tenant y varias instancias API..

**Implementación/evidencia encontrada:** No Hub/MapHub/IHubContext SignalR ni tablero de posición/riesgo localizados.

**Estado:** No implementado. **Validación ejecutable/precondiciones y límites:** CU-29/H05: dos API y clientes A/B, actualización sin refresco y corte de una instancia; no se ejecuta despliegue.

### NFR-11 — MAUI

Fuente: XLSM «No funcionales» fila 14; PDF §6.11. Sección: 6.11; Bloque: MAUI; Módulo de referencia: M04; Módulos afectados: M04; Exigencia resumida: MVVM, ubicación segundo plano, escaneo, evidencia, offline cifrado, biometría y avisos con app cerrada..

**Implementación/evidencia encontrada:** MAUI MVVM, SQLite/archivos cifrados, tracking/background, cámara/evidencia y FCM en código.

**Estado:** Pendiente de validación humana. **Validación ejecutable/precondiciones y límites:** CU-18 a 24; Android, biometría, cámara/lector, GPS con pantalla apagada y push con app cerrada requieren dispositivo y persona.

### NFR-12 — Observabilidad

Fuente: XLSM «No funcionales» fila 15; PDF §6.12. Sección: 6.12; Bloque: Observabilidad; Módulo de referencia: M06; Módulos afectados: Todos; Exigencia resumida: Serilog, OpenTelemetry, correlación extremo a extremo y tablero con latencia, errores, cola, sync, fallidos y caché..

**Implementación/evidencia encontrada:** Serilog, HostingTelemetry/ApiTelemetry, WorkerTelemetry; dashboards deploy/observability y deploy/gcp.

**Estado:** Pendiente de validación humana. **Validación ejecutable/precondiciones y límites:** Traza desde móvil a worker con correlación; verificar p95/p99/errores/cola/sync/fallidos/hit-miss con tráfico local. No se arrancó stack observabilidad y faltan métricas de funciones ausentes.

### NFR-13 — Escalabilidad

Fuente: XLSM «No funcionales» fila 16; PDF §6.13. Sección: 6.13; Bloque: Escalabilidad; Módulo de referencia: M01; Módulos afectados: M01, M05, M06; Exigencia resumida: Dos API balanceadas, continuidad, API sin estado, health/ready/live, cierre controlado, claves compartidas y jobs únicos..

**Implementación/evidencia encontrada:** IaC balanceador, claves compartidas y endpoints de salud; prueba sesión reinicia API sintética y conserva keyring.

**Estado:** Pendiente de validación humana. **Validación ejecutable/precondiciones y límites:** Dos API balanceadas, corte y apagado controlado/jobs únicos en entorno descartable autorizado. No se acredita multinstancia por reiniciar una API.

### NFR-14 — Nube e IaC

Fuente: XLSM «No funcionales» fila 17; PDF §6.14. Sección: 6.14; Bloque: Nube e IaC; Módulo de referencia: M01; Módulos afectados: Todos; Exigencia resumida: Nube remota HTTPS; IaC reproducible, variables, secretos, CI/CD y evidencia de costo..

**Implementación/evidencia encontrada:** infra/gcp y workflows de publicación existentes.

**Estado:** Pendiente de validación humana. **Validación ejecutable/precondiciones y límites:** Revisión de plan IaC/costos/HTTPS por personas con acceso; no aplicar/destroy/deploy en esta tarea. Evidencia remota real no sustituible por localhost.

### NFR-15 — Calidad

Fuente: XLSM «No funcionales» fila 18; PDF §6.15. Sección: 6.15; Bloque: Calidad; Módulo de referencia: M02; Módulos afectados: Todos; Exigencia resumida: Pruebas unitarias de dominio, integración crítica, arquitectura y aislamiento, todas en pipeline..

**Implementación/evidencia encontrada:** Unitarias/integraciones/RLS/browsers y arquitectura; pipeline ejecuta restore bloqueado y ArchitectureTests.

**Estado:** Brecha encontrada. **Validación ejecutable/precondiciones y límites:** H07/H08: corregir primero reproducibilidad y oráculo binario, conservar dos reproducciones rojas H01/H02; no retirar fallos ni exclusiones para CI verde.


## Opcionales

### OPT-01 — Seguimiento público como servicio independiente

Fuente: XLSM «Opcionales» fila 4; PDF §7.1. Sección: 7.1; Requisito opcional: Seguimiento público como servicio independiente; Puntos: 4; Módulo relacionado: M05; Decisión del equipo: Descartado; Condición de cumplimiento resumida: Base propia de solo lectura alimentada solo por cola; consistencia eventual medida y escalado independiente..

**Implementación/evidencia encontrada:** Descartado en columna F; Tracking consulta API transaccional, sin base propia de solo lectura.

**Estado:** No implementado. **Validación ejecutable/precondiciones y límites:** No seleccionado; no atribuir 4 puntos. Si se adopta, aislar base/consumidor y medir atraso/replay y caída.

### OPT-02 — gRPC para sincronización y telemetría móvil

Fuente: XLSM «Opcionales» fila 5; PDF §7.1. Sección: 7.1; Requisito opcional: gRPC para sincronización y telemetría móvil; Puntos: 4; Módulo relacionado: M04; Decisión del equipo: Descartado; Condición de cumplimiento resumida: Client streaming, protobuf y comparación medida con REST en red degradada..

**Implementación/evidencia encontrada:** Descartado; canal actual REST/JSON, sin client streaming protobuf localizado.

**Estado:** No implementado. **Validación ejecutable/precondiciones y límites:** No seleccionado. Si se adopta, mismo corpus/bytes/tiempo/conexiones y red degradada, sin reemplazar SignalR web.

### OPT-03 — Kafka para eventos de flota

Fuente: XLSM «Opcionales» fila 6; PDF §7.1. Sección: 7.1; Requisito opcional: Kafka para eventos de flota; Puntos: 3; Módulo relacionado: M04 / M06; Decisión del equipo: Seleccionado; Condición de cumplimiento resumida: Más de un consumidor y reconstrucción por replay; justificar coexistencia con cola obligatoria..

**Implementación/evidencia encontrada:** Seleccionado (3 puntos); KafkaEnvioCreadoPublisher y PasswordRecoveryMongoConsumer, sin flujo completo de telemetría flota y replay demostrado.

**Estado:** Brecha encontrada. **Validación ejecutable/precondiciones y límites:** Producir posiciones/eventos de envío, dos consumidores independientes, reconstruir estado desde log y comparar hash; no ejecutado Kafka real.

### OPT-04 — Autoescalado horizontal

Fuente: XLSM «Opcionales» fila 7; PDF §7.1. Sección: 7.1; Requisito opcional: Autoescalado horizontal; Puntos: 3; Módulo relacionado: M01; Decisión del equipo: Descartado; Condición de cumplimiento resumida: Escalado automático por métricas con prueba de carga..

**Implementación/evidencia encontrada:** Descartado; balanceador estático/IaC no demuestra autoescalado por métricas.

**Estado:** No implementado. **Validación ejecutable/precondiciones y límites:** No seleccionado; no generar gastos de carga/nube en esta revisión.

### OPT-05 — NoSQL para historial y analítica

Fuente: XLSM «Opcionales» fila 8; PDF §7.2. Sección: 7.2; Requisito opcional: NoSQL para historial y analítica; Puntos: 2; Módulo relacionado: M02 / M06; Decisión del equipo: Seleccionado; Condición de cumplimiento resumida: Base documental, índices, retención y API paginada y filtrable..

**Implementación/evidencia encontrada:** Seleccionado (2 puntos); Mongo guarda recuperación de contraseña, no historial/analítica de envíos con API paginada.

**Estado:** Brecha encontrada. **Validación ejecutable/precondiciones y límites:** Tras implementar, índices/retención/consulta con filtros y aislamiento y replay; no contar historial de credenciales como CU-12.

### OPT-06 — Pruebas de carga automatizadas

Fuente: XLSM «Opcionales» fila 9; PDF §7.2. Sección: 7.2; Requisito opcional: Pruebas de carga automatizadas; Puntos: 2; Módulo relacionado: M06; Decisión del equipo: Seleccionado; Condición de cumplimiento resumida: Escenarios, objetivos previos y sincronización simultánea en ambiente remoto..

**Implementación/evidencia encontrada:** Seleccionado (2 puntos); no plan/ejecución remota de carga con SLO previo y retorno simultáneo localizado.

**Estado:** No implementado. **Validación ejecutable/precondiciones y límites:** Definir objetivos antes; preparar datos nuevos y ejecutar solo en remoto autorizado con presupuesto. No se corrió prueba de carga ni servicios pagos.

### OPT-07 — Cobertura de pruebas

Fuente: XLSM «Opcionales» fila 10; PDF §7.2. Sección: 7.2; Requisito opcional: Cobertura de pruebas; Puntos: 2; Módulo relacionado: Transversal; Decisión del equipo: Seleccionado; Condición de cumplimiento resumida: Más de 70 % de cobertura en dominio y aplicación, publicada por pipeline..

**Implementación/evidencia encontrada:** Seleccionado (2 puntos); tests abundantes no demuestran >70% de dominio/aplicación ni publicación de reporte.

**Estado:** Pendiente de validación humana. **Validación ejecutable/precondiciones y límites:** Medir cobertura real por capa, revisar exclusiones/denominador y publicar por pipeline tras resolver sus fallos. No se calculó cobertura en esta auditoría.

### OPT-08 — Pruebas extremo a extremo

Fuente: XLSM «Opcionales» fila 11; PDF §7.2. Sección: 7.2; Requisito opcional: Pruebas extremo a extremo; Puntos: 2; Módulo relacionado: Transversal; Decisión del equipo: Seleccionado; Condición de cumplimiento resumida: Playwright o equivalente para flujos críticos, integrado al pipeline..

**Implementación/evidencia encontrada:** Seleccionado (2 puntos); nueve optativos activados y aprobados aquí; pipeline tiene otros browsers críticos, no activa todos estos optativos.

**Estado:** Pendiente de validación humana. **Validación ejecutable/precondiciones y límites:** Revisar qué flujos y SHA ejecuta CI. Mantener rojo mapa-dispose y validar persistencia/consumo externo; no confundir tests omitidos por flags con aprobados.

### OPT-09 — Notificaciones remotas en producción

Fuente: XLSM «Opcionales» fila 12; PDF §7.3. Sección: 7.3; Requisito opcional: Notificaciones remotas en producción; Puntos: 3; Módulo relacionado: M04; Decisión del equipo: Seleccionado; Condición de cumplimiento resumida: Push real con app cerrada ante reasignación urgente y ciclo de vida de IDs de dispositivo..

**Implementación/evidencia encontrada:** Seleccionado (3 puntos); instalaciones/avisos FCM y worker presentes; pruebas usan transporte controlado.

**Estado:** Pendiente de validación humana. **Validación ejecutable/precondiciones y límites:** Android REAL, app cerrada, reasignación urgente y rotación/revocación de token; no probado y no usar proveedor pago ni secretos en Git.

### OPT-10 — Geocercas

Fuente: XLSM «Opcionales» fila 13; PDF §7.3. Sección: 7.3; Requisito opcional: Geocercas; Puntos: 3; Módulo relacionado: M04; Decisión del equipo: Descartado; Condición de cumplimiento resumida: Llegada y salida automáticas de parada y análisis de batería..

**Implementación/evidencia encontrada:** Descartado; GPS/proyección no equivale a eventos automáticos de geocerca.

**Estado:** No implementado. **Validación ejecutable/precondiciones y límites:** No seleccionado. Si se adopta, trayecto físico y consumo batería medidos con consentimiento.

### OPT-11 — Impresión Bluetooth

Fuente: XLSM «Opcionales» fila 14; PDF §7.3. Sección: 7.3; Requisito opcional: Impresión Bluetooth; Puntos: 2; Módulo relacionado: M04; Decisión del equipo: Descartado; Condición de cumplimiento resumida: Etiqueta o comprobante desde móvil a impresora térmica..

**Implementación/evidencia encontrada:** Descartado; etiqueta PDF no es impresión Bluetooth desde móvil.

**Estado:** No implementado. **Validación ejecutable/precondiciones y límites:** No seleccionado; prueba requiere impresora térmica física, no PDF/ZXing simulado.

### OPT-12 — Optimización del orden de paradas

Fuente: XLSM «Opcionales» fila 15; PDF §7.3. Sección: 7.3; Requisito opcional: Optimización del orden de paradas; Puntos: 2; Módulo relacionado: M03; Decisión del equipo: Descartado; Condición de cumplimiento resumida: Algoritmo o servicio, comparado con el criterio obligatorio del CU-16..

**Implementación/evidencia encontrada:** Descartado; CU-16 usa orden manual explícito/cronología.

**Estado:** No implementado. **Validación ejecutable/precondiciones y límites:** No seleccionado; algoritmo/servicio solo si se decide, comparación medida sin proveedor pago.

### OPT-13 — API pública para comercios

Fuente: XLSM «Opcionales» fila 16; PDF §7.4. Sección: 7.4; Requisito opcional: API pública para comercios; Puntos: 3; Módulo relacionado: M02; Decisión del equipo: Descartado; Condición de cumplimiento resumida: API documentada/versionada con claves por comercio, sandbox y rate limit diferenciado..

**Implementación/evidencia encontrada:** Descartado; alta API autenticada existe, no contrato completo de claves por comercio/sandbox/rate diferenciado.

**Estado:** No implementado. **Validación ejecutable/precondiciones y límites:** No seleccionado; no confundir CU-07 obligatorio con opcional de integración pública completo.

### OPT-14 — Banderas de funcionalidad

Fuente: XLSM «Opcionales» fila 17; PDF §7.4. Sección: 7.4; Requisito opcional: Banderas de funcionalidad; Puntos: 2; Módulo relacionado: M01; Decisión del equipo: Descartado; Condición de cumplimiento resumida: Activación por tenant en caliente, sin despliegue..

**Implementación/evidencia encontrada:** Descartado; configuración por operador no prueba feature flags en caliente.

**Estado:** No implementado. **Validación ejecutable/precondiciones y límites:** No seleccionado; si se adopta, toggles por tenant y fallos sin filtrar reglas entre organizaciones.

### OPT-15 — Pruebas de resiliencia

Fuente: XLSM «Opcionales» fila 18; PDF §7.4. Sección: 7.4; Requisito opcional: Pruebas de resiliencia; Puntos: 2; Módulo relacionado: Transversal; Decisión del equipo: Descartado; Condición de cumplimiento resumida: Cortes deliberados de caché, cola, BD y servicio externo con comparación esperado/observado..

**Implementación/evidencia encontrada:** Descartado; faults de tests locales no acreditan plan completo de resiliencia de todas las dependencias.

**Estado:** No implementado. **Validación ejecutable/precondiciones y límites:** No seleccionado; cortes solo sobre contenedores propios y comparación de degradación/caché/cola/DB/proveedor; nunca servicios de la prueba reservada.


## Condiciones del hito inicial — no son CU adicionales

Fuente secundaria contrastada: `docs/alcance/Monitoreo_2026-10-08_CU.xlsx`, hoja «CU 08-10». Las filas7–9 recortan CU-01/07/08 para aquel hito y la fila18 aclara que no los cierra. No reemplazan el alcance final de30CU. La hoja comparativa `Calcs/Estrategia Multitenancy.xlsx` es análisis de alternativas; el ADR-MT-001 concreta RLS y autorización por fila de envío, sin vínculo comercio-operador permanente obligatorio.

| ID existente / fuente | Requisito | Implementación/evidencia y estado | Validación humana |
|---|---|---|---|
| T-01, A13:D13 | Compose arranca web/API/worker/PostgreSQL/caché/cola/observabilidad | Hay Compose/IaC; runtime mínimo nuevo no incluye todos esos soportes, caché faltante H06. **Brecha encontrada** | Sobre stack aislado completo ejecutar Compose sin copiar secretos, comprobar salud de cada servicio; el start mínimo no satisface este hito |
| T-02, A14:D14 | El envío del portal aparece en Backoffice con mismo ID | Integraciones de admisión y consultas separadas; falta demostración humana conjunta. **Pendiente de validación humana** | Crear referencia nueva desde C1, anotar ID nuevo, abrir operador A/recargar y comparar; B/C2 no acceden |
| T-03, A15:D15 | Pipeline del código demostrado compila/prueba correctamente | H07/H08 fallan en esta revisión; no se consultó ni afirmó éxito de un pipeline remoto. **Brecha encontrada** | Tras corrección ejecutar CI del SHA a demostrar, comprobar restore bloqueado/pruebas y artefactos sin ocultar fallos |

## Dependencias individuales de la planilla

No son decisiones nuevas del revisor. La validación concreta y el estado están en las filas CU consumidor/proveedor y sus casos manuales.

| Dependencia / fila fuente | Consumidor ← proveedor | Contrato exigido y riesgo |
|---|---|---|
| D01 / Dependencias A4:I4 | CU-07 ← CU-01 | Contexto de operador + vínculo comercio-operador. Riesgo: Alta o consulta en tenant equivocado. |
| D02 / Dependencias A5:I5 | CU-09 ← CU-03 | Servicio de cálculo + ID de versión de tarifa. Riesgo: Cambios retroactivos de precio. |
| D03 / Dependencias A6:I6 | CU-11 ← CU-04 | Versión de reglas asociada al envío. Riesgo: Transiciones distintas entre operadores. |
| D04 / Dependencias A7:I7 | CU-13 ← CU-02 | Zona y franja del envío. Riesgo: Ruta incompatible con promesa al destinatario. |
| D05 / Dependencias A8:I8 | CU-13 ← CU-11 | Consulta de candidatos + comando de asignación. Riesgo: Doble asignación o estado inválido. |
| D06 / Dependencias A9:I9 | CU-14 ← CU-08 | Datos de bultos y envío. Riesgo: Ruta que supera capacidad. |
| D07 / Dependencias A10:I10 | CU-14 ← CU-02 | Calendario y ventanas configuradas. Riesgo: Compromisos incumplibles. |
| D08 / Dependencias A11:I11 | CU-18 ← CU-17 | Contrato versionado de hoja de ruta. Riesgo: App sin datos o con versión incompatible. |
| D09 / Dependencias A12:I12 | CU-19 ← CU-13 | Lista de bultos por ruta. Riesgo: Carga incompleta sin alerta. |
| D10 / Dependencias A13:I13 | CU-20 ← CU-04 | Política de evidencia versionada. Riesgo: Pruebas insuficientes o innecesarias. |
| D11 / Dependencias A14:I14 | CU-21 ← CU-04 | Catálogo de motivos versionado. Riesgo: Motivos inválidos sin conexión. |
| D12 / Dependencias A15:I15 | CU-24 ← CU-11 | API de eventos idempotente + versión de estado. Riesgo: Pérdida o duplicación de eventos. |
| D13 / Dependencias A16:I16 | CU-22 ← CU-12 | Comandos y eventos de devolución. Riesgo: Devoluciones sin trazabilidad. |
| D14 / Dependencias A17:I17 | CU-25 ← CU-12 | Proyección pública por token opaco. Riesgo: Datos desactualizados o expuestos. |
| D15 / Dependencias A18:I18 | CU-25 ← CU-05 | Identidad visual por tenant. Riesgo: Marca incorrecta o filtración entre tenants. |
| D16 / Dependencias A19:I19 | CU-26 ← CU-04 | Validador de reprogramación. Riesgo: Reprogramaciones fuera de política. |
| D17 / Dependencias A20:I20 | CU-27 ← CU-12 | Evento de dominio mediante outbox. Riesgo: Aviso sin estado persistido o aviso perdido. |
| D18 / Dependencias A21:I21 | CU-28 ← CU-12 | Evento de dominio mediante outbox. Riesgo: Avisos duplicados o ausentes. |
| D19 / Dependencias A22:I22 | CU-29 ← CU-23 | Evento de ubicación y canal SignalR. Riesgo: Mapa sin posición actual. |
| D20 / Dependencias A23:I23 | CU-29 ← CU-11 | Lectura de envíos y ventanas. Riesgo: Alertas de riesgo incorrectas. |
| D21 / Dependencias A24:I24 | CU-29 ← CU-13 | Proyección de ruta y asignación. Riesgo: Visión operativa incompleta. |
| D22 / Dependencias A25:I25 | CU-30 ← CU-09 | Tarifa aplicada e historial. Riesgo: Liquidación recalculada con reglas nuevas. |
| D23 / Dependencias A26:I26 | CU-30 ← CU-12 | Eventos inmutables / proyección analítica. Riesgo: Reportes inconsistentes. |
| D24 / Dependencias A27:I27 | CU-27 ← CU-24 | Evento confirmado por servidor. Riesgo: Aviso prematuro de entrega. |
