# Guía de validación humana — todos los CU

Todos los casos empiezan **pendientes de validación humana**; las brechas señaladas no se saltan ni se consideran aprobadas. Cada resultado debe registrar persona, fecha/hora local, commit, organización, referencia NUEVA del envío/ruta, pasos efectivamente realizados y evidencia sin secretos. No completar casillas de hechos físicos desde scripts.

## Preparación y actores

Seguir primero [prerrequisitos y comandos](04-reproduccion-y-datos.md). Usar exclusivamente el runtime `auditoria03nov` o uno NUEVO preparado de igual manera, nunca la base de la prueba manual del 02/11. No consultar ni modificar los dos UUID reservados del pedido.

- Administrador plataforma: alta de organizaciones nuevas; no acceso implícito a datos operativos.
- Operador A y B: administradores con configuración distinta. Despachadores A1/A2: `envios.gestionar` y `envios.consultar`. Operario depósito: solo los permisos requeridos por recepción, no administrador global.
- Comercios C1 y C2: accesos propios con `envios.crear`/`envios.consultar`; mismo comercio puede operar con A/B. No inventar vínculo permanente obligatorio: ADR-MT-001 autoriza por fila de envío.
- Repartidores R1/R2: `reparto.ejecutar`, vehículo V1/V2 y ocupación autorizada, sin permisos de despachador. Destinatario: sin cuenta, solo enlace NUEVO.

Configuración sintética propuesta (no política real): en A zona que contiene -34.9,-56.2 y excluye Rivera; franjas/fechas locales explícitas; B con valores distintos. Las tarifas y reglas se publican desde UI y se calculan por separado antes de operar. No habilitar cobertura para que un negativo pase.

## Orden de circuitos

1. Configuración y acceso: CU-01 a CU-06.
2. Comercio/admisión: CU-07/08/09 y etiquetas AP-02.
3. Depósito e historia: CU-10/11/12.
4. Planificación/despacho: CU-13/14/15/16/17.
5. Android/calle/offline: CU-18/19/20/21/22/23/24.
6. Destinatario/comunicación/gestión: CU-25/26/27/28/29/30.

Cambiar de circuito no acredita hechos físicos. Detener la aceptación donde haya una brecha, conservar evidencia y continuar otros casos independientes con nuevos envíos.

<a id="cu-01"></a>
## CU-01 — Comercios y usuarios

**Actor:** Administrador operador/comercio. **Fuente:** PDF §5.1 nº1; XLSM «CU obligatorios» A4:I4. **Estado:** Pendiente de validación humana.

**Entrada y código:** /usuarios; /roles; Admin /operadores, /comercios; autogestión /mi-comercio; UsuariosController, RolesController, OrganizacionPropiaController. **Persistencia:** Usuarios, AccesosUsuario, Roles y políticas RLS.

**Precondiciones/datos:** A: crear usuario y rol restringido; B/C2: aislamiento. Permisos según actor y guardas del endpoint; confirmar con CU-01, no asumirlos por visibilidad del menú.

**Evidencia automatizada disponible:** UsuariosHttpTests, RolesHttpTests, OrganizacionPropiaHttpTests. La cobertura ejecutada en esta auditoría y sus límites están en [05](05-ejecuciones.md); el nombre de un test no demuestra por sí solo todos los pasos siguientes.

1. Crear usuario en la organización A y asignarle un rol sin envios.gestionar.
2. Ingresar con ese usuario y comprobar menú y acceso directo a Depósito rechazado.
3. Editar, suspender/reactivar el acceso; comprobar efectos tras nueva consulta y auditoría.
4. Intentar gestionar usuarios de B y C2; no deben aparecer ni modificarse.

**Negativos, conflictos y recuperación:** Confirmar con negocio la administración de comercios clientes desde operador: autogestión/administración de plataforma no equivalen por sí solas al ABM solicitado. Repetir la operación ante fallo de transporte solo con su mismo comando/payload cuando el contrato sea idempotente; frente a versión obsoleta, releer y decidir explícitamente. Guardar valores y evidencia del error, no afirmar éxito por PRG/HTTP 200 sin verificar resultado.

**Registro humano:** pendiente. Resultado observado / evidencia / incidencias / persona / fecha: ____________________.

<a id="cu-02"></a>
## CU-02 — Zonas y franjas

**Actor:** Administrador operador. **Fuente:** PDF §5.1 nº2; XLSM «CU obligatorios» A5:I5. **Estado:** Pendiente de validación humana.

**Entrada y código:** /zonas; /api/configuracion/zonas y /{id}/franjas; ZonasCoberturaController, ZonaCobertura. **Persistencia:** ZonasCobertura, FranjasEntrega, ZonasCoberturaRevisiones.

**Precondiciones/datos:** A/B con zonas distintas y puntos dentro/borde/fuera. Permisos según actor y guardas del endpoint; confirmar con CU-01, no asumirlos por visibilidad del menú.

**Evidencia automatizada disponible:** ZonasCoberturaHttpTests, ZonaCoberturaPostgisTests, UruguayCatalogAndTerritoryTests. La cobertura ejecutada en esta auditoría y sus límites están en [05](05-ejecuciones.md); el nombre de un test no demuestra por sí solo todos los pasos siguientes.

1. Crear polígono sintético y franjas para A en America/Montevideo.
2. Guardar y reabrir para comparar geometría, zona horaria y horarios.
3. Probar punto interior, sobre borde y exterior; verificar cobertura coherente.
4. Editar desde dos pestañas con misma versión; el segundo guardado debe informar conflicto sin perder campos.

**Negativos, conflictos y recuperación:** No extender cobertura real ni inferir aceptación por ver mapa. Repetir la operación ante fallo de transporte solo con su mismo comando/payload cuando el contrato sea idempotente; frente a versión obsoleta, releer y decidir explícitamente. Guardar valores y evidencia del error, no afirmar éxito por PRG/HTTP 200 sin verificar resultado.

**Registro humano:** pendiente. Resultado observado / evidencia / incidencias / persona / fecha: ____________________.

<a id="cu-03"></a>
## CU-03 — Tarifas configurables

**Actor:** Administrador operador. **Fuente:** PDF §5.1 nº3; XLSM «CU obligatorios» A6:I6. **Estado:** Pendiente de validación humana.

**Entrada y código:** /tarifas, /tarifas/borrador, /tarifas/simular; /api/configuracion/tarifas; TarifarioController, CalculadoraTarifas. **Persistencia:** TarifariosOperador, VersionesTarifario, tarifas y ajustes versionados.

**Precondiciones/datos:** Zonas A publicadas; juego tarifario sintético explícito. Permisos según actor y guardas del endpoint; confirmar con CU-01, no asumirlos por visibilidad del menú.

**Evidencia automatizada disponible:** TarifarioHttpTests, TarifarioPersistenceTests, CalculadoraTarifasTests. La cobertura ejecutada en esta auditoría y sus límites están en [05](05-ejecuciones.md); el nombre de un test no demuestra por sí solo todos los pasos siguientes.

1. Crear borrador con zona/peso/volumen/Estandar/Urgente y ajustes.
2. Simular con calculadora independiente y guardar el cálculo esperado.
3. Publicar, reabrir y verificar número/versionado.
4. Publicar una segunda tarifa y comprobar que envíos anteriores conservan su cargo e historial.

**Negativos, conflictos y recuperación:** Comparar redondeo, límites, recargo y bonificación; rechazar edición concurrente. Repetir la operación ante fallo de transporte solo con su mismo comando/payload cuando el contrato sea idempotente; frente a versión obsoleta, releer y decidir explícitamente. Guardar valores y evidencia del error, no afirmar éxito por PRG/HTTP 200 sin verificar resultado.

**Registro humano:** pendiente. Resultado observado / evidencia / incidencias / persona / fecha: ____________________.

<a id="cu-04"></a>
## CU-04 — Reglas operativas

**Actor:** Administrador operador. **Fuente:** PDF §5.1 nº4; XLSM «CU obligatorios» A7:I7. **Estado:** Pendiente de validación humana.

**Entrada y código:** /reglas-operativas; /api/configuracion/reglas-operativas; ReglasOperativasController, VersionReglasOperativas. **Persistencia:** ReglasOperativasOperador, versiones, requisitos y motivos.

**Precondiciones/datos:** A con foto+nombre, intentos y catálogo sintéticos; B distinto. Permisos según actor y guardas del endpoint; confirmar con CU-01, no asumirlos por visibilidad del menú.

**Evidencia automatizada disponible:** ReglasOperativasHttpTests, ReglasEnvioAdmisionHttpTests. La cobertura ejecutada en esta auditoría y sus límites están en [05](05-ejecuciones.md); el nombre de un test no demuestra por sí solo todos los pasos siguientes.

1. Configurar intentos, intervalo, prueba, motivos, devolución y plazos.
2. Publicar y admitir un envío; anotar VersionReglasId.
3. Cambiar/publicar y admitir otro envío.
4. Intentar usar motivo/prueba de la versión nueva en el envío anterior; debe respetar la original.

**Negativos, conflictos y recuperación:** No reducir reglas operativas de datos ajenos para conseguir pruebas verdes. Repetir la operación ante fallo de transporte solo con su mismo comando/payload cuando el contrato sea idempotente; frente a versión obsoleta, releer y decidir explícitamente. Guardar valores y evidencia del error, no afirmar éxito por PRG/HTTP 200 sin verificar resultado.

**Registro humano:** pendiente. Resultado observado / evidencia / incidencias / persona / fecha: ____________________.

<a id="cu-05"></a>
## CU-05 — Identidad visual

**Actor:** Administrador operador; destinatario. **Fuente:** PDF §5.1 nº5; XLSM «CU obligatorios» A8:I8. **Estado:** Brecha encontrada.

**Entrada y código:** /identidad-visual; Commerce; Tracking; comunicaciones; IdentidadVisualOperadorController, IdentidadVisualPublicaResponse. **Persistencia:** VersionesIdentidadVisualOperador y consumidores por tenant.

**Precondiciones/datos:** Marca A y B diferentes; correo local capturado. Permisos según actor y guardas del endpoint; confirmar con CU-01, no asumirlos por visibilidad del menú.

**Evidencia automatizada disponible:** IdentidadVisualOperadorHttpTests, IdentidadVisualPagesTests. La cobertura ejecutada en esta auditoría y sus límites están en [05](05-ejecuciones.md); el nombre de un test no demuestra por sí solo todos los pasos siguientes.

1. Guardar marca/contacto/colores A y abrir Commerce y Tracking de un envío A.
2. Abrir B en otra sesión y verificar que no aparece marca A.
3. Probar colores sin contraste y versión obsoleta; conservar valores/advertencias.
4. Inspeccionar una comunicación real local al destinatario; registrar bloqueo si el aviso de estado no existe.

**Negativos, conflictos y recuperación:** H04: avisos al destinatario por estado no implementados; no dar por integrado ese consumidor. Repetir la operación ante fallo de transporte solo con su mismo comando/payload cuando el contrato sea idempotente; frente a versión obsoleta, releer y decidir explícitamente. Guardar valores y evidencia del error, no afirmar éxito por PRG/HTTP 200 sin verificar resultado.

**Registro humano:** pendiente. Resultado observado / evidencia / incidencias / persona / fecha: ____________________.

<a id="cu-06"></a>
## CU-06 — Repartidores y vehículos

**Actor:** Administrador y despachador. **Fuente:** PDF §5.1 nº6; XLSM «CU obligatorios» A9:I9. **Estado:** Pendiente de validación humana.

**Entrada y código:** /repartidores; /vehiculos; /flota; /api/repartidores, /api/reparto/vehiculos, /api/reparto/flota; FlotaController, RepartidoresController, EfRutasRepository.Flota. **Persistencia:** Vehiculos, accesos de repartidor, OcupacionesRuta e historial.

**Precondiciones/datos:** V1/V2 con capacidades distintas, R1/R2; confirmaciones físicas pendientes. Permisos según actor y guardas del endpoint; confirmar con CU-01, no asumirlos por visibilidad del menú.

**Evidencia automatizada disponible:** CapacidadVigenteHttpTests, OcupacionFlotaHttpTests; navegadores Vehiculos/Flota. La cobertura ejecutada en esta auditoría y sus límites están en [05](05-ejecuciones.md); el nombre de un test no demuestra por sí solo todos los pasos siguientes.

1. Crear/editar repartidor y vehículo con peso y volumen; reabrir.
2. Probar precisión decimal, límites y edición concurrente.
3. Comprobar disponibilidad inicial solo tras constatación humana explícita.
4. Despachar, cerrar jornada y verificar que cierre no libera recursos; retorno/liberación requieren sus constataciones.

**Negativos, conflictos y recuperación:** CU-06 permanece abierto: B1–B5 y pruebas de lógica no acreditan hardware, precisión vial ni habilitación operativa. Repetir la operación ante fallo de transporte solo con su mismo comando/payload cuando el contrato sea idempotente; frente a versión obsoleta, releer y decidir explícitamente. Guardar valores y evidencia del error, no afirmar éxito por PRG/HTTP 200 sin verificar resultado.

**Registro humano:** pendiente. Resultado observado / evidencia / incidencias / persona / fecha: ____________________.

<a id="cu-07"></a>
## CU-07 — Alta de envíos

**Actor:** Comercio C1. **Fuente:** PDF §5.2 nº7; XLSM «CU obligatorios» A10:I10. **Estado:** Pendiente de validación humana.

**Entrada y código:** /envios/crear; /envios/importar; POST /api/envios y /api/envios/importaciones; CrearEnvioUseCase, ImportarEnviosUseCase, CsvEnviosParser. **Persistencia:** Envios, identidades de importación v2 y outbox en transacción.

**Precondiciones/datos:** CSV nuevos del generador; operador/zona/tarifa propios. Permisos según actor y guardas del endpoint; confirmar con CU-01, no asumirlos por visibilidad del menú.

**Evidencia automatizada disponible:** ShipmentCsvImportHttpTests, CommerceCsvImportKestrelTests, AdmissionSelectsAdjustsQuotesSavesAndReopensBeforeShipping. La cobertura ejecutada en esta auditoría y sus límites están en [05](05-ejecuciones.md); el nombre de un test no demuestra por sí solo todos los pasos siguientes.

1. Crear envío individual y comparar con GET autenticado.
2. Importar 01-alta-v2.csv declarando VersionFormato=2.
3. Reimportar completo y parcial 02: mismas referencias, ningún duplicado.
4. Importar lote 03 con fila nueva válida e inválida: ningún alta parcial; corregir y reintentar.

**Negativos, conflictos y recuperación:** Referencia existente con distinto contenido da conflicto; identidad v1 no se reinterpreta silenciosamente; no reutilizar datos manuales previos. Repetir la operación ante fallo de transporte solo con su mismo comando/payload cuando el contrato sea idempotente; frente a versión obsoleta, releer y decidir explícitamente. Guardar valores y evidencia del error, no afirmar éxito por PRG/HTTP 200 sin verificar resultado.

**Registro humano:** pendiente. Resultado observado / evidencia / incidencias / persona / fecha: ____________________.

<a id="cu-08"></a>
## CU-08 — Bultos

**Actor:** Comercio y depósito. **Fuente:** PDF §5.2 nº8; XLSM «CU obligatorios» A11:I11. **Estado:** Pendiente de validación humana.

**Entrada y código:** Alta multibulto; etiquetas; recepción y ruta; CrearEnvioRequest, Bulto, EtiquetasEnvioPdf. **Persistencia:** Bultos con UUID, código, peso y dimensiones.

**Precondiciones/datos:** MULTI con dos bultos y medidas declaradas diferentes. Permisos según actor y guardas del endpoint; confirmar con CU-01, no asumirlos por visibilidad del menú.

**Evidencia automatizada disponible:** CrearEnvioUseCaseTests, EtiquetasEnvioHttpTests, RecepcionDepositoHttpTests. La cobertura ejecutada en esta auditoría y sus límites están en [05](05-ejecuciones.md); el nombre de un test no demuestra por sí solo todos los pasos siguientes.

1. Agregar dos bultos con identificación/peso/dimensiones y guardar.
2. Reabrir y descargar PDF de etiquetas; comprobar ambos UUID y códigos.
3. Escanear cada etiqueta y cotejar el bulto exacto.
4. Quitar/agregar antes de confirmar y probar cero/negativos/precisión; no perder los demás datos.

**Negativos, conflictos y recuperación:** Medidas declaradas no son mediciones físicas ni justifican custodia. Repetir la operación ante fallo de transporte solo con su mismo comando/payload cuando el contrato sea idempotente; frente a versión obsoleta, releer y decidir explícitamente. Guardar valores y evidencia del error, no afirmar éxito por PRG/HTTP 200 sin verificar resultado.

**Registro humano:** pendiente. Resultado observado / evidencia / incidencias / persona / fecha: ____________________.

<a id="cu-09"></a>
## CU-09 — Cálculo de tarifa

**Actor:** Comercio C1. **Fuente:** PDF §5.2 nº9; XLSM «CU obligatorios» A12:I12. **Estado:** Pendiente de validación humana.

**Entrada y código:** Cotización en alta; POST /api/envios/cotizacion; GET /api/envios/{id}/tarifa e historial; TarifasAdmision, CalculadoraTarifas. **Persistencia:** TarifasEnvio append-only; procedencia tarifaria/geográfica.

**Precondiciones/datos:** Publicación A, MULTI e HISTORIA; operador sin Rivera. Permisos según actor y guardas del endpoint; confirmar con CU-01, no asumirlos por visibilidad del menú.

**Evidencia automatizada disponible:** TarifaAdmisionHttpTests, AdmissionSelectsAdjustsQuotesSavesAndReopensBeforeShipping. La cobertura ejecutada en esta auditoría y sus límites están en [05](05-ejecuciones.md); el nombre de un test no demuestra por sí solo todos los pasos siguientes.

1. Elegir punto interior y servicio; calcular con todos los bultos y contrastar desglose independiente.
2. Confirmar y reabrir cargo/versiones.
3. Cambiar publicación entre cotizar y confirmar: conflicto sin alta ni valores perdidos.
4. Intentar Rivera, zona de B, modalidad ausente e importe HTTP manipulado: rechazos sin cargos/envíos parciales.

**Negativos, conflictos y recuperación:** D02/D22: nueva publicación no cambia cargos anteriores; franja individual aún no forma parte del contrato (D-P01). Repetir la operación ante fallo de transporte solo con su mismo comando/payload cuando el contrato sea idempotente; frente a versión obsoleta, releer y decidir explícitamente. Guardar valores y evidencia del error, no afirmar éxito por PRG/HTTP 200 sin verificar resultado.

**Registro humano:** pendiente. Resultado observado / evidencia / incidencias / persona / fecha: ____________________.

<a id="cu-10"></a>
## CU-10 — Recepción en depósito

**Actor:** Operario depósito. **Fuente:** PDF §5.2 nº10; XLSM «CU obligatorios» A13:I13. **Estado:** Pendiente de validación humana.

**Entrada y código:** /deposito/recepcion; GET /api/deposito/consulta; POST /api/deposito/bultos/{id}/recepcion; EfRutasRepository.Recepcion, RecepcionModel. **Persistencia:** RecepcionesBulto inmutable, custodia/versiones e historia canónica al completar.

**Precondiciones/datos:** MULTI físicamente disponible; lector/cámara propios opcionales. Permisos según actor y guardas del endpoint; confirmar con CU-01, no asumirlos por visibilidad del menú.

**Evidencia automatizada disponible:** RecepcionDepositoHttpTests y RecepcionDepositoBrowserTests. La cobertura ejecutada en esta auditoría y sus límites están en [05](05-ejecuciones.md); el nombre de un test no demuestra por sí solo todos los pasos siguientes.

1. Buscar UUID/código y comprobar que GET/Enter no recibe físicamente nada.
2. Una persona constata y coteja primer bulto conforme: custodia Depósito; el otro sigue pendiente.
3. Registrar discrepancia REAL en segundo bulto con observaciones; no inventar medidas.
4. Conservar discrepancia; resolver según decisión humana D-P02. Solo si físicamente se subsanó, registrar nuevo cotejo conforme.
5. Repetir comando exacto y escaneo; no duplicar historia; versión vencida debe conservar valores y pedir revisión.

**Negativos, conflictos y recuperación:** Admitido con custodia Depósito es posible y no implica pérdida física. No falsear conformidad para desbloquear planificación. Repetir la operación ante fallo de transporte solo con su mismo comando/payload cuando el contrato sea idempotente; frente a versión obsoleta, releer y decidir explícitamente. Guardar valores y evidencia del error, no afirmar éxito por PRG/HTTP 200 sin verificar resultado.

**Registro humano:** pendiente. Resultado observado / evidencia / incidencias / persona / fecha: ____________________.

<a id="cu-11"></a>
## CU-11 — Estado del envío

**Actor:** Sistema; operadores; repartidor. **Fuente:** PDF §5.2 nº11; XLSM «CU obligatorios» A14:I14. **Estado:** Pendiente de validación humana.

**Entrada y código:** Comandos de recepción, ruta, móvil, cancelación y decisiones; sin setter de estado; TransicionesEstadoEnvio, Envio, guard_shipment_state_transition. **Persistencia:** Envios, versiones, hechos físicos y trigger de historia.

**Precondiciones/datos:** Envíos separados para éxito/fallo/devolución/cancelación. Permisos según actor y guardas del endpoint; confirmar con CU-01, no asumirlos por visibilidad del menú.

**Evidencia automatizada disponible:** EnvioStateMachineTests, ShipmentStatePolicySqlTests, RecepcionDepositoHttpTests.Estados. La cobertura ejecutada en esta auditoría y sus límites están en [05](05-ejecuciones.md); el nombre de un test no demuestra por sí solo todos los pasos siguientes.

1. Seguir flujo admitido→depósito→asignado→tránsito usando acciones específicas.
2. En otro envío registrar intento fallido y reprogramación/devolución conforme a versión.
3. Probar cancelar tras entrega física; no debe deshacerla ni habilitar otra entrega.
4. Consultar estados terminales y probar comandos incompatibles/versiones viejas; no deben mutar estado ni custodia.

**Negativos, conflictos y recuperación:** Diagrama corregido agrega Cancelado/pendiente/sin validación. El PDF de propuesta es histórico; no resolver divergencias de negocio solo con paridad SQL. Repetir la operación ante fallo de transporte solo con su mismo comando/payload cuando el contrato sea idempotente; frente a versión obsoleta, releer y decidir explícitamente. Guardar valores y evidencia del error, no afirmar éxito por PRG/HTTP 200 sin verificar resultado.

**Registro humano:** pendiente. Resultado observado / evidencia / incidencias / persona / fecha: ____________________.

<a id="cu-12"></a>
## CU-12 — Eventos del envío

**Actor:** Sistema; comercio y operador consultan. **Fuente:** PDF §5.2 nº12; XLSM «CU obligatorios» A15:I15. **Estado:** Pendiente de validación humana.

**Entrada y código:** Sin endpoint general de eventos encontrado; consulta de recepción y verificación PostgreSQL en fixture; EnvioEvento, triggers, SetShipmentHistoryContextAsync. **Persistencia:** EnvioEventos append-only, origen/responsable/fecha/GPS según operación.

**Precondiciones/datos:** HISTORIA y ejecución nueva; dos actores. Permisos según actor y guardas del endpoint; confirmar con CU-01, no asumirlos por visibilidad del menú.

**Evidencia automatizada disponible:** EnvioEventsHttpTests, EnvioHistoryMigrationTests, RlsRestrictedHttpFlowTests. La cobertura ejecutada en esta auditoría y sus límites están en [05](05-ejecuciones.md); el nombre de un test no demuestra por sí solo todos los pasos siguientes.

1. Con técnico, inspeccionar historia en la fixture aislada tras cada acción; no inventar un endpoint de consulta general.
2. Comprobar origen/responsable, versiones, hora física vs recibida y geolocalización donde corresponde.
3. Repetir comando aplicado: no debe agregar hechos.
4. Intentar lectura de B/C2: denegada; rollback/concurrencia/inmutabilidad SQL se reproducen con fixtures, no en la base manual.

**Negativos, conflictos y recuperación:** No reconstruir hechos anteriores al corte de migración ni considerar completa una proyección pública que no muestra historial (H03). Repetir la operación ante fallo de transporte solo con su mismo comando/payload cuando el contrato sea idempotente; frente a versión obsoleta, releer y decidir explícitamente. Guardar valores y evidencia del error, no afirmar éxito por PRG/HTTP 200 sin verificar resultado.

**Registro humano:** pendiente. Resultado observado / evidencia / incidencias / persona / fecha: ____________________.

<a id="cu-13"></a>
## CU-13 — Armar rutas

**Actor:** Despachador. **Fuente:** PDF §5.3 nº13; XLSM «CU obligatorios» A16:I16. **Estado:** Pendiente de validación humana.

**Entrada y código:** /rutas/planificar; POST /api/rutas; GestionarRutasUseCase, EfRutasRepository.PlanificarAsync. **Persistencia:** HojasRuta, ParadasRuta, recursos y snapshot temporal.

**Precondiciones/datos:** Bultos físicamente recibidos; destinos confirmados; V/R activos. Permisos según actor y guardas del endpoint; confirmar con CU-01, no asumirlos por visibilidad del menú.

**Evidencia automatizada disponible:** RutasHttpTests, BasePlanificacionHttpTests. La cobertura ejecutada en esta auditoría y sus límites están en [05](05-ejecuciones.md); el nombre de un test no demuestra por sí solo todos los pasos siguientes.

1. Seleccionar dos envíos elegibles, repartidor, vehículo y fecha operativa.
2. Definir orden, llegada y servicio, revisar y planificar.
3. Reabrir detalle y comparar asignaciones y snapshot.
4. Intentar incluir envío de B, no recibido o ya asignado: rechazo sin ruta/paradas parciales.

**Negativos, conflictos y recuperación:** Ruta vacía reserva recursos si el producto lo permite, pero no se despacha; no confundir reserva con ocupación física. Repetir la operación ante fallo de transporte solo con su mismo comando/payload cuando el contrato sea idempotente; frente a versión obsoleta, releer y decidir explícitamente. Guardar valores y evidencia del error, no afirmar éxito por PRG/HTTP 200 sin verificar resultado.

**Registro humano:** pendiente. Resultado observado / evidencia / incidencias / persona / fecha: ____________________.

<a id="cu-14"></a>
## CU-14 — Validar restricciones

**Actor:** Despachador. **Fuente:** PDF §5.3 nº14; XLSM «CU obligatorios» A17:I17. **Estado:** Brecha encontrada.

**Entrada y código:** Planificación, reasignación, despacho y confirmación de carga; CapacidadCarga, RestriccionesTemporales, VentanaRuta. **Persistencia:** Revisión histórica de zona/cargo, versión de configuración y snapshot de ruta.

**Precondiciones/datos:** Rutas separadas para límites; franja local A y servicio en borde. Permisos según actor y guardas del endpoint; confirmar con CU-01, no asumirlos por visibilidad del menú.

**Evidencia automatizada disponible:** VentanaRutaTests, HistoricalCoverageRequiresArrivalAndWholeServiceInsideWindow, CapacidadVigenteHttpTests. La cobertura ejecutada en esta auditoría y sus límites están en [05](05-ejecuciones.md); el nombre de un test no demuestra por sí solo todos los pasos siguientes.

1. Probar máximo exacto de paradas, peso y volumen, después exceder cada uno aisladamente.
2. Probar inicio incluido, fin excluido y servicio que termina exactamente en fin.
3. Modificar capacidad o configuración actual antes de despacho/salida y observar la revalidación aplicable.
4. Intentar verificar una franja prometida individual: documentar que alta no la captura y resolver D-P01 antes de aceptación.

**Negativos, conflictos y recuperación:** La comprobación actual usa CUALQUIER franja activa histórica, no una ventana individual comprometida. No aceptar la interpretación por tener pruebas verdes. Repetir la operación ante fallo de transporte solo con su mismo comando/payload cuando el contrato sea idempotente; frente a versión obsoleta, releer y decidir explícitamente. Guardar valores y evidencia del error, no afirmar éxito por PRG/HTTP 200 sin verificar resultado.

**Registro humano:** pendiente. Resultado observado / evidencia / incidencias / persona / fecha: ____________________.

<a id="cu-15"></a>
## CU-15 — Evitar doble asignación

**Actor:** Dos despachadores. **Fuente:** PDF §5.3 nº15; XLSM «CU obligatorios» A18:I18. **Estado:** Pendiente de validación humana.

**Entrada y código:** POST /api/rutas concurrente; reasignación; Bloqueo PostgreSQL de operador e índice único de parada activa. **Persistencia:** ParadasRuta activas + Envios en transacción.

**Precondiciones/datos:** Mismo envío; R1/V1 y R2/V2 distintos; barrera del test. Permisos según actor y guardas del endpoint; confirmar con CU-01, no asumirlos por visibilidad del menú.

**Evidencia automatizada disponible:** DosPlanificacionesConcurrentesSoloAsignanUnaVez. La cobertura ejecutada en esta auditoría y sus límites están en [05](05-ejecuciones.md); el nombre de un test no demuestra por sí solo todos los pasos siguientes.

1. Abrir mismo candidato en dos sesiones con recursos diferentes.
2. Ejecutar la prueba de competencia con bloqueo/barrera de PostgreSQL.
3. Verificar un éxito y un 409, una sola asignación/evento y ningún recurso fantasma.
4. Recuperar la sesión perdedora y releer estado antes de otro comando.

**Negativos, conflictos y recuperación:** Clics rápidos humanos no demuestran solapamiento; la prueba de barrera sí acredita transacciones concurrentes, no aceptación funcional. Repetir la operación ante fallo de transporte solo con su mismo comando/payload cuando el contrato sea idempotente; frente a versión obsoleta, releer y decidir explícitamente. Guardar valores y evidencia del error, no afirmar éxito por PRG/HTTP 200 sin verificar resultado.

**Registro humano:** pendiente. Resultado observado / evidencia / incidencias / persona / fecha: ____________________.

<a id="cu-16"></a>
## CU-16 — Ordenar paradas

**Actor:** Despachador. **Fuente:** PDF §5.3 nº16; XLSM «CU obligatorios» A19:I19. **Estado:** Pendiente de validación humana.

**Entrada y código:** /rutas/planificar; orden y llegada manual en detalle; HojaRuta.AgregarParada y PlanTemporal. **Persistencia:** Orden persistido y snapshot temporal inicial.

**Precondiciones/datos:** Tres envíos con orden y servicios distintos. Permisos según actor y guardas del endpoint; confirmar con CU-01, no asumirlos por visibilidad del menú.

**Evidencia automatizada disponible:** ExactStopLimitUsesShipmentsAndPreservesExplicitOrder, PlanTemporalTests. La cobertura ejecutada en esta auditoría y sus límites están en [05](05-ejecuciones.md); el nombre de un test no demuestra por sí solo todos los pasos siguientes.

1. Establecer orden explícito y llegadas cronológicas que incluyan duración de servicio.
2. Planificar y reabrir; comprobar posiciones consecutivas y orden elegido.
3. Probar solapamiento y medianoche; no corregir silenciosamente horas ni orden.
4. Intentar agregar/reordenar tras despacho: debe rechazarse donde el circuito no lo admite.

**Negativos, conflictos y recuperación:** Criterio obligatorio manual documentado; no equivale a optimización opcional OPT-12. Repetir la operación ante fallo de transporte solo con su mismo comando/payload cuando el contrato sea idempotente; frente a versión obsoleta, releer y decidir explícitamente. Guardar valores y evidencia del error, no afirmar éxito por PRG/HTTP 200 sin verificar resultado.

**Registro humano:** pendiente. Resultado observado / evidencia / incidencias / persona / fecha: ____________________.

<a id="cu-17"></a>
## CU-17 — Despachar ruta

**Actor:** Despachador y repartidor. **Fuente:** PDF §5.3 nº17; XLSM «CU obligatorios» A20:I20. **Estado:** Pendiente de validación humana.

**Entrada y código:** Detalle /rutas/{id}; POST /api/rutas/{id}/despacho; /api/mobile/rutas; EfRutasRepository.DespacharAsync. **Persistencia:** HojasRuta Despachada + OcupacionRuta e historial.

**Precondiciones/datos:** Fecha de hoy del operador; V/R verificados humanamente. Permisos según actor y guardas del endpoint; confirmar con CU-01, no asumirlos por visibilidad del menú.

**Evidencia automatizada disponible:** RutasHttpTests, OcupacionFlotaHttpTests. La cobertura ejecutada en esta auditoría y sus límites están en [05](05-ejecuciones.md); el nombre de un test no demuestra por sí solo todos los pasos siguientes.

1. Despachar una ruta válida del día y descargar con el repartidor asignado.
2. Comprobar que envíos siguen AsignadoRuta y bultos siguen Depósito.
3. Repetir con versión vieja: no duplicar despacho ni ocupación.
4. Intentar despacho futuro, sin verificación inicial o con ocupación de otra fecha: rechazo explicativo.

**Negativos, conflictos y recuperación:** Despacho NO acredita carga ni salida. Se requiere escaneo y ConfirmarCarga. Repetir la operación ante fallo de transporte solo con su mismo comando/payload cuando el contrato sea idempotente; frente a versión obsoleta, releer y decidir explícitamente. Guardar valores y evidencia del error, no afirmar éxito por PRG/HTTP 200 sin verificar resultado.

**Registro humano:** pendiente. Resultado observado / evidencia / incidencias / persona / fecha: ____________________.

<a id="cu-18"></a>
## CU-18 — Descargar ruta

**Actor:** Repartidor Android. **Fuente:** PDF §5.4 nº18; XLSM «CU obligatorios» A21:I21. **Estado:** Pendiente de validación humana.

**Entrada y código:** MAUI hoja del día; GET /api/mobile/rutas y /{id}; HojaRutaViewModel, repositorio local y ApiReparto. **Persistencia:** SQLite y snapshot de hoja/reglas.

**Precondiciones/datos:** Android real/emulador autorizado con usuario R1. Permisos según actor y guardas del endpoint; confirmar con CU-01, no asumirlos por visibilidad del menú.

**Evidencia automatizada disponible:** Mobile Api/Application Tests; RutasHttpTests. La cobertura ejecutada en esta auditoría y sus límites están en [05](05-ejecuciones.md); el nombre de un test no demuestra por sí solo todos los pasos siguientes.

1. Ingresar, descargar ruta despachada y abrir cada parada.
2. Activar modo avión y reiniciar app; hoja y reglas deben seguir disponibles.
3. Intentar hoja planificada o de otro repartidor: no visible/denegada.
4. Restablecer conexión sin borrar trabajo local.

**Negativos, conflictos y recuperación:** Pruebas portátiles no acreditan Android, persistencia del sistema operativo ni GPS. Repetir la operación ante fallo de transporte solo con su mismo comando/payload cuando el contrato sea idempotente; frente a versión obsoleta, releer y decidir explícitamente. Guardar valores y evidencia del error, no afirmar éxito por PRG/HTTP 200 sin verificar resultado.

**Registro humano:** pendiente. Resultado observado / evidencia / incidencias / persona / fecha: ____________________.

<a id="cu-19"></a>
## CU-19 — Escanear carga

**Actor:** Repartidor y depósito. **Fuente:** PDF §5.4 nº19; XLSM «CU obligatorios» A22:I22. **Estado:** Pendiente de validación humana.

**Entrada y código:** MAUI escaneo de carga; operaciones CargarBulto/ConfirmarCarga; HojaRutaViewModel, EfOperacionesRepartoRepository. **Persistencia:** Custodia Bultos y operación idempotente por jornada/secuencia.

**Precondiciones/datos:** MULTI recibido físicamente; lector/cámara REAL. Permisos según actor y guardas del endpoint; confirmar con CU-01, no asumirlos por visibilidad del menú.

**Evidencia automatizada disponible:** OperacionesRepartoHttpTests; Mobile Application/Core Tests. La cobertura ejecutada en esta auditoría y sus límites están en [05](05-ejecuciones.md); el nombre de un test no demuestra por sí solo todos los pasos siguientes.

1. Escanear físicamente primer bulto y observar pendiente del segundo.
2. Escanear un código ajeno/sobrante: aviso, sin cargarlo.
3. Completar carga y confirmar salida tras constatación humana.
4. Con faltantes probar política configurada: bloquear o suspender sin fingir carga; volver a consultar custodia.

**Negativos, conflictos y recuperación:** No usar MediaStream sintético como aceptación de cámara/lector. No ejecutar carga intermedia después de salir. Repetir la operación ante fallo de transporte solo con su mismo comando/payload cuando el contrato sea idempotente; frente a versión obsoleta, releer y decidir explícitamente. Guardar valores y evidencia del error, no afirmar éxito por PRG/HTTP 200 sin verificar resultado.

**Registro humano:** pendiente. Resultado observado / evidencia / incidencias / persona / fecha: ____________________.

<a id="cu-20"></a>
## CU-20 — Registrar entrega

**Actor:** Repartidor y receptor. **Fuente:** PDF §5.4 nº20; XLSM «CU obligatorios» A23:I23. **Estado:** Brecha encontrada.

**Entrada y código:** MAUI entrega; operaciones EntregaFisica/EvidenciaEntrega; PUT evidencias; Envio.DeclararEntregaFisica, AplicarPrueba, GuardarEvidenciaAsync. **Persistencia:** PruebasEntrega, EvidenciasReparto cifradas, estado y custodia.

**Precondiciones/datos:** PRUEBA con reglas foto+nombre; receptor/GPS reales en Android. Permisos según actor y guardas del endpoint; confirmar con CU-01, no asumirlos por visibilidad del menú.

**Evidencia automatizada disponible:** OperacionesRepartoHttpTests; AuditoriaIntegral_InvalidPngMustNotValidateDelivery. La cobertura ejecutada en esta auditoría y sus límites están en [05](05-ejecuciones.md); el nombre de un test no demuestra por sí solo todos los pasos siguientes.

1. Capturar los requisitos exigidos, hora y posición del dispositivo durante entrega física real.
2. Sin foto válida registrar hecho solo cuando ocurrió; debe quedar pendiente según versión.
3. Enviar la reproducción de PNG inválido en fixture aislada: hoy valida indebidamente (H01).
4. Después de corregir, repetir prueba válida/imagen corrupta/plazo vencido/cancelación concurrente.

**Negativos, conflictos y recuperación:** No declarar aceptación mientras H01 permita Entregado sin foto decodificable. Una persona confirma entrega física; el script no la acredita. Repetir la operación ante fallo de transporte solo con su mismo comando/payload cuando el contrato sea idempotente; frente a versión obsoleta, releer y decidir explícitamente. Guardar valores y evidencia del error, no afirmar éxito por PRG/HTTP 200 sin verificar resultado.

**Registro humano:** pendiente. Resultado observado / evidencia / incidencias / persona / fecha: ____________________.

<a id="cu-21"></a>
## CU-21 — Registrar intento fallido

**Actor:** Repartidor. **Fuente:** PDF §5.4 nº21; XLSM «CU obligatorios» A24:I24. **Estado:** Pendiente de validación humana.

**Entrada y código:** MAUI intento fallido; operación IntentoFallido; ResumenIntentosEntrega y catálogo de reglas del envío. **Persistencia:** OperacionesJornada, estado NoEntregado y devolución si corresponde.

**Precondiciones/datos:** INTENTO con motivos y foto exigida configurados. Permisos según actor y guardas del endpoint; confirmar con CU-01, no asumirlos por visibilidad del menú.

**Evidencia automatizada disponible:** OperacionesRepartoHttpTests, ReasignacionPushTests. La cobertura ejecutada en esta auditoría y sus límites están en [05](05-ejecuciones.md); el nombre de un test no demuestra por sí solo todos los pasos siguientes.

1. Registrar intento real con motivo vigente y evidencia del dispositivo.
2. Probar motivo ajeno, falta de evidencia y plazo entre intentos incumplido.
3. Sincronizar repetido: un solo intento y contador estable.
4. Al agotar intentos observar decisión manual/automática configurada sin inventar recepción física.

**Negativos, conflictos y recuperación:** Foto corrupta también puede superar el control de archivo (H01); requiere regresión negativa después de corrección. Repetir la operación ante fallo de transporte solo con su mismo comando/payload cuando el contrato sea idempotente; frente a versión obsoleta, releer y decidir explícitamente. Guardar valores y evidencia del error, no afirmar éxito por PRG/HTTP 200 sin verificar resultado.

**Registro humano:** pendiente. Resultado observado / evidencia / incidencias / persona / fecha: ____________________.

<a id="cu-22"></a>
## CU-22 — Devolución y rendición

**Actor:** Repartidor, depósito y despachador. **Fuente:** PDF §5.4 nº22; XLSM «CU obligatorios» A25:I25. **Estado:** Pendiente de validación humana.

**Entrada y código:** MAUI Rendicion/FinJornada; /deposito; /flota; EfOperacionesRepartoRepository, EfRutasRepository.RecibirAsync, flota. **Persistencia:** Custodia Repartidor→PendienteDeposito→Deposito y ocupación separada.

**Precondiciones/datos:** RETORNO con presencia física de bultos/vehículo confirmable. Permisos según actor y guardas del endpoint; confirmar con CU-01, no asumirlos por visibilidad del menú.

**Evidencia automatizada disponible:** OperacionesRepartoHttpTests, OcupacionFlotaHttpTests, ConciliacionEntregaHttpTests. La cobertura ejecutada en esta auditoría y sus límites están en [05](05-ejecuciones.md); el nombre de un test no demuestra por sí solo todos los pasos siguientes.

1. Declarar rendición de bultos que una persona realmente trae.
2. Cerrar jornada; comprobar que no simula recepción ni libera vehículo.
3. Depósito constata y recibe físicamente; verificar estado comercial que corresponde.
4. Confirmar retorno y liberación por actores autorizados; repetir comando/versiones viejas y revisar historia.

**Negativos, conflictos y recuperación:** Cierre, rendición, retorno, recepción y liberación son hechos diferentes. No usar ni consultar la ruta/envío reservados. Repetir la operación ante fallo de transporte solo con su mismo comando/payload cuando el contrato sea idempotente; frente a versión obsoleta, releer y decidir explícitamente. Guardar valores y evidencia del error, no afirmar éxito por PRG/HTTP 200 sin verificar resultado.

**Registro humano:** pendiente. Resultado observado / evidencia / incidencias / persona / fecha: ____________________.

<a id="cu-23"></a>
## CU-23 — Posición del vehículo

**Actor:** Repartidor; despachador. **Fuente:** PDF §5.4 nº23; XLSM «CU obligatorios» A26:I26. **Estado:** Pendiente de validación humana.

**Entrada y código:** MAUI tracking; operación Posicion; estimaciones B5; TrackingJornada, ServicioUbicacion, EfOperacionesRepartoRepository. **Persistencia:** OperacionesJornada con posición/precisión/instantes.

**Precondiciones/datos:** Android con permisos foreground/background y ruta en curso. Permisos según actor y guardas del endpoint; confirmar con CU-01, no asumirlos por visibilidad del menú.

**Evidencia automatizada disponible:** Mobile Application/Core; EstimacionesVialesHttpTests. La cobertura ejecutada en esta auditoría y sus límites están en [05](05-ejecuciones.md); el nombre de un test no demuestra por sí solo todos los pasos siguientes.

1. Dar permisos, iniciar jornada y moverse con dispositivo real.
2. Apagar pantalla y dejar app en segundo plano; registrar duración/consumo y posiciones reales.
3. Recuperar red y comprobar conservación de hora física, recepción y precisión.
4. Denegar ubicación y revisar aviso/recuperación; no generar coordenadas ficticias.

**Negativos, conflictos y recuperación:** Recepción API/B5 no demuestra seguimiento continuo ni tablero SignalR (H05). Repetir la operación ante fallo de transporte solo con su mismo comando/payload cuando el contrato sea idempotente; frente a versión obsoleta, releer y decidir explícitamente. Guardar valores y evidencia del error, no afirmar éxito por PRG/HTTP 200 sin verificar resultado.

**Registro humano:** pendiente. Resultado observado / evidencia / incidencias / persona / fecha: ____________________.

<a id="cu-24"></a>
## CU-24 — Sincronización diferida

**Actor:** Repartidor y sistema. **Fuente:** PDF §5.4 nº24; XLSM «CU obligatorios» A27:I27. **Estado:** Pendiente de validación humana.

**Entrada y código:** MAUI cola offline; API operaciones/evidencias; SincronizadorJornada y RepositorioJornadasSqlite.Sincronizacion. **Persistencia:** SQLite/archivos cifrados; secuencias, hash, conflicto explícito.

**Precondiciones/datos:** Ruta descargada; red controlable y segunda sesión despachador. Permisos según actor y guardas del endpoint; confirmar con CU-01, no asumirlos por visibilidad del menú.

**Evidencia automatizada disponible:** Mobile Core 36, Application 85, Api 63; OperacionesRepartoHttpTests. La cobertura ejecutada en esta auditoría y sus límites están en [05](05-ejecuciones.md); el nombre de un test no demuestra por sí solo todos los pasos siguientes.

1. Sin red registrar carga/entrega/intento según circuito; cerrar/reabrir app.
2. En servidor cambiar el mismo envío de forma autorizada desde otra sesión.
3. Restablecer red; observar orden de archivos/operaciones y estado Conflicto si incompatible.
4. Reintentar/cortar respuesta: no duplicar y conservar trabajo/evidencia para resolución humana.

**Negativos, conflictos y recuperación:** No sustituir resolución por éxito forzado; Android/SQLite real/cifrado en reposo siguen pendientes de prueba en dispositivo. Repetir la operación ante fallo de transporte solo con su mismo comando/payload cuando el contrato sea idempotente; frente a versión obsoleta, releer y decidir explícitamente. Guardar valores y evidencia del error, no afirmar éxito por PRG/HTTP 200 sin verificar resultado.

**Registro humano:** pendiente. Resultado observado / evidencia / incidencias / persona / fecha: ____________________.

<a id="cu-25"></a>
## CU-25 — Seguimiento público

**Actor:** Destinatario sin cuenta. **Fuente:** PDF §5.5 nº25; XLSM «CU obligatorios» A28:I28. **Estado:** Brecha encontrada.

**Entrada y código:** Tracking /seguimiento/{token}; GET /api/public/seguimiento/{token}; SeguimientoPublicoController, SeguimientoEstadoResponse. **Persistencia:** Enlaces opacos y estado actual RLS mediante función pública.

**Precondiciones/datos:** Enlace NUEVO obtenido del envío sintético. Permisos según actor y guardas del endpoint; confirmar con CU-01, no asumirlos por visibilidad del menú.

**Evidencia automatizada disponible:** PublicCancellationTests, EnlaceSeguimientoPostgresTests, ConsultarSeguimientoPublicoUseCaseTests. La cobertura ejecutada en esta auditoría y sus límites están en [05](05-ejecuciones.md); el nombre de un test no demuestra por sí solo todos los pasos siguientes.

1. Abrir enlace en sesión anónima y comprobar estado/marca correctos.
2. Intentar token inválido y enumeración: no filtrar IDs/PII ni distinguir datos de terceros.
3. Consultar historial y ventana estimada: actualmente no existen en el contrato (H03).
4. Probar límites de tasa en entorno aislado, no sobre servicio operativo.

**Negativos, conflictos y recuperación:** No confundir un enlace público existente con cumplimiento del recorrido público completo. Repetir la operación ante fallo de transporte solo con su mismo comando/payload cuando el contrato sea idempotente; frente a versión obsoleta, releer y decidir explícitamente. Guardar valores y evidencia del error, no afirmar éxito por PRG/HTTP 200 sin verificar resultado.

**Registro humano:** pendiente. Resultado observado / evidencia / incidencias / persona / fecha: ____________________.

<a id="cu-26"></a>
## CU-26 — Reprogramación

**Actor:** Destinatario sin cuenta. **Fuente:** PDF §5.5 nº26; XLSM «CU obligatorios» A29:I29. **Estado:** No implementado.

**Entrada y código:** No se encontró solicitud pública de reprogramación; solo POST operador /api/envios/{id}/reprogramacion; RutasController.Reprogramar exige envios.gestionar; Tracking carece del formulario. **Persistencia:** No se encontró solicitud pública persistida.

**Precondiciones/datos:** Token público nuevo y reglas de reprogramación definidas. Permisos según actor y guardas del endpoint; confirmar con CU-01, no asumirlos por visibilidad del menú.

**Evidencia automatizada disponible:** Pruebas de reprogramación OPERATIVA no prueban al destinatario. La cobertura ejecutada en esta auditoría y sus límites están en [05](05-ejecuciones.md); el nombre de un test no demuestra por sí solo todos los pasos siguientes.

1. Abrir enlace como destinatario y buscar acción de reprogramar.
2. Registrar que falta acción/endpoint público y detener ejecución funcional con brecha H04.
3. Después de implementar: solicitar fecha/franja válida y probar política/versionado/doble envío.
4. Comprobar que otro token no puede reprogramar este envío.

**Negativos, conflictos y recuperación:** Una cancelación pública ni la reprogramación interna por despachador sustituyen CU-26. Repetir la operación ante fallo de transporte solo con su mismo comando/payload cuando el contrato sea idempotente; frente a versión obsoleta, releer y decidir explícitamente. Guardar valores y evidencia del error, no afirmar éxito por PRG/HTTP 200 sin verificar resultado.

**Registro humano:** pendiente. Resultado observado / evidencia / incidencias / persona / fecha: ____________________.

<a id="cu-27"></a>
## CU-27 — Avisos al destinatario

**Actor:** Sistema; destinatario. **Fuente:** PDF §5.5 nº27; XLSM «CU obligatorios» A30:I30. **Estado:** No implementado.

**Entrada y código:** Worker: seguimiento, recuperación, código cancelación y push repartidor; no avisos de estado al destinatario; Program Worker, OutboxMessageTypes/OutboxHandlerRegistry. **Persistencia:** No se encontró entrega de avisos por transiciones a destinatarios.

**Precondiciones/datos:** Buzón SMTP local/capturador nuevo; nunca proveedor pago. Permisos según actor y guardas del endpoint; confirmar con CU-01, no asumirlos por visibilidad del menú.

**Evidencia automatizada disponible:** CreacionAutomaticaSeguimientoTests prueba crear enlace, no avisos CU-27. La cobertura ejecutada en esta auditoría y sus límites están en [05](05-ejecuciones.md); el nombre de un test no demuestra por sí solo todos los pasos siguientes.

1. Cambiar estado de envío nuevo con circuito válido.
2. Observar que no hay mensaje CU-27 en contratos/handlers; registrar H04.
3. Tras implementar, inspeccionar buzón local y correlación estado→outbox→worker→correo.
4. Interrumpir receptor local y comprobar reintentos/idempotencia sin aviso prematuro por offline.

**Negativos, conflictos y recuperación:** No enviar a correos de personas; ejemplo.test no acredita entrega externa. Repetir la operación ante fallo de transporte solo con su mismo comando/payload cuando el contrato sea idempotente; frente a versión obsoleta, releer y decidir explícitamente. Guardar valores y evidencia del error, no afirmar éxito por PRG/HTTP 200 sin verificar resultado.

**Registro humano:** pendiente. Resultado observado / evidencia / incidencias / persona / fecha: ____________________.

<a id="cu-28"></a>
## CU-28 — Avisos a comercios

**Actor:** Comercio y worker. **Fuente:** PDF §5.5 nº28; XLSM «CU obligatorios» A31:I31. **Estado:** No implementado.

**Entrada y código:** No se encontró configuración de suscripción, historial/reenvío webhook ni receptor de prueba; OutboxMessageTypes y Worker sin contrato webhook de cambio de estado. **Persistencia:** Sin modelo de suscripción/entrega HTTP por comercio localizado.

**Precondiciones/datos:** C1/C2, receptor HTTP local con verificación de firma. Permisos según actor y guardas del endpoint; confirmar con CU-01, no asumirlos por visibilidad del menú.

**Evidencia automatizada disponible:** No hay prueba de firma/reintento/reenvío de webhook de comercio. La cobertura ejecutada en esta auditoría y sus límites están en [05](05-ejecuciones.md); el nombre de un test no demuestra por sí solo todos los pasos siguientes.

1. Buscar suscripción por evento en Commerce y registrar ausencia H04.
2. Tras implementar, configurar receptor local y evento para C1.
3. Generar estado, comprobar firma, tenant/evento e idempotencia del receptor.
4. Apagar/reabrir receptor, inspeccionar backoff/fallidos y reenvío aislado C1/C2.

**Negativos, conflictos y recuperación:** Push FCM al repartidor y Kafka EnvioCreado no equivalen al webhook exigido por §6.9. Repetir la operación ante fallo de transporte solo con su mismo comando/payload cuando el contrato sea idempotente; frente a versión obsoleta, releer y decidir explícitamente. Guardar valores y evidencia del error, no afirmar éxito por PRG/HTTP 200 sin verificar resultado.

**Registro humano:** pendiente. Resultado observado / evidencia / incidencias / persona / fecha: ____________________.

<a id="cu-29"></a>
## CU-29 — Tablero en vivo

**Actor:** Despachador. **Fuente:** PDF §5.5 nº29; XLSM «CU obligatorios» A32:I32. **Estado:** No implementado.

**Entrada y código:** /flota muestra disponibilidad; no tablero de posición/riesgo SignalR localizado; Catálogo Backoffice sin tablero; API sin Hub/MapHub. **Persistencia:** Posiciones/estimaciones puntuales no constituyen proyección en vivo.

**Precondiciones/datos:** R1/R2 en jornada; dos operadores; dos API para prueba completa. Permisos según actor y guardas del endpoint; confirmar con CU-01, no asumirlos por visibilidad del menú.

**Evidencia automatizada disponible:** B5/Flota prueban consultas y snapshots; no SignalR multinstancia. La cobertura ejecutada en esta auditoría y sus límites están en [05](05-ejecuciones.md); el nombre de un test no demuestra por sí solo todos los pasos siguientes.

1. Abrir operación y buscar mapa vivo de flota con riesgo de ventanas.
2. Registrar ausencia de hub/tablero H05; no presentar /flota como equivalente.
3. Tras implementar, mover dispositivo real y observar actualización sin refrescar.
4. Abrir B y cortar una API: aislamiento y continuidad del canal.

**Negativos, conflictos y recuperación:** Sin aceptación de precisión GPS/vial ni escalabilidad por ver un mapa estático. Repetir la operación ante fallo de transporte solo con su mismo comando/payload cuando el contrato sea idempotente; frente a versión obsoleta, releer y decidir explícitamente. Guardar valores y evidencia del error, no afirmar éxito por PRG/HTTP 200 sin verificar resultado.

**Registro humano:** pendiente. Resultado observado / evidencia / incidencias / persona / fecha: ____________________.

<a id="cu-30"></a>
## CU-30 — Reportes y liquidación

**Actor:** Operador y comercio. **Fuente:** PDF §5.5 nº30; XLSM «CU obligatorios» A33:I33. **Estado:** No implementado.

**Entrada y código:** No reportes de cumplimiento/motivos/volumen/liquidación ni cuenta corriente localizados; Navegaciones y API sin reportes/liquidaciones; TarifaAplicada muestra cargo individual. **Persistencia:** Cargos/historia son insumos, sin agregados/ledger localizado.

**Precondiciones/datos:** Varios envíos nuevos de zonas/comercios distintos; resultados conocidos. Permisos según actor y guardas del endpoint; confirmar con CU-01, no asumirlos por visibilidad del menú.

**Evidencia automatizada disponible:** TarifaAdmisionHttpTests conserva cargos; no prueba liquidación. La cobertura ejecutada en esta auditoría y sus límites están en [05](05-ejecuciones.md); el nombre de un test no demuestra por sí solo todos los pasos siguientes.

1. Buscar reportes por zona/repartidor/comercio y registrar ausencia H05.
2. Tras implementar, preparar totales independientes desde hechos sintéticos.
3. Comparar filtros, período, zona horaria, paginación y aislamiento.
4. Cambiar tarifa y recalcular reporte: cargo histórico no debe cambiar (D22/D23).

**Negativos, conflictos y recuperación:** No contar el desglose de una tarifa individual como cuenta corriente o liquidación. Repetir la operación ante fallo de transporte solo con su mismo comando/payload cuando el contrato sea idempotente; frente a versión obsoleta, releer y decidir explícitamente. Guardar valores y evidencia del error, no afirmar éxito por PRG/HTTP 200 sin verificar resultado.

**Registro humano:** pendiente. Resultado observado / evidencia / incidencias / persona / fecha: ____________________.


## Circuito transversal — sesión y recuperación (NFR-03/04/15)

Precondiciones: A/C1 nuevos, dos pestañas por portal y permisos reales. La carrera necesita el harness `SesionWebBrowserTests` del apartado04, no una operación sobre la prueba Mobile reservada.

1. Abrir directamente una pantalla permitida (Backoffice y Commerce) sin sesión; ingresar expresamente y comprobar retorno a la **ruta** segura, sin query/fragment/formulario ni reenvío de POST.
2. Probar ReturnUrl externo, protocol-relative, segmentos `..`, codificación y rutas de ingreso/salida/API. Debe descartarse el destino inseguro, sin open redirect ni bucle. No incluir tokens de seguimiento reales en capturas.
3. Ejecutar el harness que retiene un401 antiguo, realizar otro ingreso y liberar esa respuesta. Observar que la generación nueva conserva cookie y destino en ambos portales; no basta una respuesta200 aislada.
4. Revocar solo la sesión ACTUAL sin nuevo ingreso: debe solicitar ingreso explícito. Un403 de permisos conserva distinción de acceso denegado; fallo transitorio de API conserva sesión y permite reintento, no borra la cookie.
5. Probar cancelar/guardar con sesión vencida y verificar que no se repite automáticamente la operación después del login. Los datos deben poder revisarse antes de otro comando.
6. Salir explícitamente y liberar un401 retenido: no restaurar una sesión ya cerrada. Revisar foco y teclado a320px/texto200%, con mensajes legibles y valores no expuestos.
7. Registrar diagnóstico seguro (AuthTrace, razón/código, hora), nunca JWT/cookie/contraseña. Si aparece401 de arranque, conservar evidencia específica; esta carrera reproducida no prueba el origen de ese incidente histórico.

Estado: **pendiente de validación humana**. La prueba automatizada nueva pasó en ambos portales, pero no declara aceptado ningún CU ni resuelto el origen del401 histórico.

## Circuitos técnicos adicionales — AP, NFR y opcionales

Consultar las 39 filas individuales AP/NFR/OPT de [02](02-matriz.md): incluyen entrada/implementación, estado, precondición y recorrido. Para la ejecución técnica registrar cada ID por separado, incluso cuando comparte circuito con un CU.

1. **Mensajería/avisos (NFR-08/09, AP-05, CU-27/28):** primero constatar brechas; después de corregir, usar receptor y SMTP LOCALES, generar un evento nuevo, parar/reabrir consumidor/receptor, observar backoff/fallidos, reenvío y ausencia de duplicados con firma válida. No pedir a una persona que marque “aviso recibido” sin observarlo.
2. **Caché/tiempo real/escalado (NFR-07/10/13, CU-29):** dos API descartables, claves compartidas, dos operadores, lecturas independientes y métricas por perfil; cambiar versión e invalidar, cortar solo una instancia y comprobar continuidad. Actualmente caché/tablero tienen brecha; no simularlos para aceptar.
3. **Datos/arquitectura/observabilidad (NFR-01/04/05/12/15, CU-12):** restore bloqueado, pruebas de dependencia/contratos binarios y aislación; migración desde corte previo en fixtures, rollback forzado, trazas correlacionadas hasta worker. Ninguna consulta a registros reservados ni migración de la base del taller.
4. **Nube y carga (NFR-14, OPT-04/06):** preparar SLO, conjunto nuevo, rampa/concurrencia/duración y sincronización simultánea de repartidores ANTES de medir. La ejecución remota/costo/IaC apply/destroy queda pendiente de autorización y medios de los responsables; no forma parte de esta revisión.
5. **Opcionales seleccionados (OPT-03/05/06/07/08/09):** replay Kafka con dos consumidores, índices/retención/API NoSQL de envíos, carga remota con SLO, cobertura por capa >70% publicada, E2E en CI y push Android cerrado. Verificar cada condición completa antes de otorgar puntos; faltan evidencias/implementaciones según02. Password recovery en Mongo no es analítica de envíos.
6. **Opcionales descartados:** no se convierten en mínimos ni se ejecuta hardware/gasto para completarlos. Si se decide adoptarlos, usar las condiciones exactas de la fila OPT correspondiente y una tarea autorizada separada.

Registro técnico/humano por ID: ____________________. No convertir un requisito bloqueado o no implementado en “no aplica” por conveniencia.
