# Revisión independiente integral de NexoRuta

Corte de revisión: **03/11/2026, America/Montevideo**. No es aceptación de ningún CU. Se contrastaron directamente PDF, celdas OOXML sin macros/colores, diagramas, ADR, código, diffs y nuevas ejecuciones. Los informes anteriores se usaron solo como índice para localizar afirmaciones y pruebas.

## Base y método

Remotos comprobados por `git ls-remote`: principal `13aefdb15d0f4d00cd870220e961717dcb48a1fd`, Backend `bf4da61134e2c04db66f0e21bb99167dfb49306e`, Frontend `1ca0172bec203af3fa860b34925e4562ec11ee44`, rama `test/navegador-optativos`. El árbol remoto del principal contiene exactamente esos gitlinks y Mobile `74a25f1b5b18c7dfc006cf7df747d73b0ec4910a`. Mobile no publica `test/navegador-optativos`; ese objeto está publicado en `fix/cu0708`. Se conservó su SHA exacto, sin sustituir por develop. El checkout precargado era `a697d45`; se preservó su rama y se creó `review/auditoria-integral-cu` desde la base pedida.

La cadena revisada fue requisito → entrada/autorización → regla → escritura/transacción → consumidor → aserción. [Inventario](inventario-fuentes.json): SHA-256 de todas las fuentes de `docs/alcance`, texto/celdas de todas las hojas del XLSM e índice de atributos de controladores. Ese índice no demuestra por sí mismo accesibilidad de una ruta. [Matriz](02-matriz.md): 30 CU, 9 AP, 15 NFR y 15 OPT, con estados individuales. [Guía](03-guia-manual.md): actores, precondiciones, pasos y negativos por CU. [Comandos/datos](04-reproduccion-y-datos.md), [ejecuciones](05-ejecuciones.md) y [orden propuesto](06-orden-propuesto.md).

No se consultaron ni modificaron el envío `01a19e23-d3a5-7a48-92f4-97fe178c87ad` ni la ruta `01a19e71-822f-7434-9acc-2a02b89b2487`. Las pruebas usan bases efímeras propias y la preparación humana usa un contenedor/base nuevos. No se cambiaron producto, contratos, migraciones, reglas, diseño ni `permanent=false`.

## Hallazgos confirmados priorizados

P1: afecta cumplimiento obligatorio, integridad de evidencia o reproducibilidad de CI. P2: defecto funcional acotado o del oráculo/herramienta. La severidad no equivale a una aceptación ni a una explotación demostrada.

### H01 — P1 — una cabecera PNG inválida puede validar una entrega

- **Ubicación:** `backend/src/NexoRuta.Infrastructure/Reparto/EfOperacionesRepartoRepository.Evidencias.cs:13` (solo firma/longitud del archivo); `EfOperacionesRepartoRepository.Ejecucion.cs:251` (existencia del archivo), `:254` (requisito de fotografía por ID).
- **Requisito:** PDF §5.4 nº20 y §6.11; XLSM CU obligatorios fila23, D10; diagrama corregido: prueba exigida **válida** para Entregado.
- **Reproducción:** `OperacionesRepartoHttpTests.AuditoriaIntegral_InvalidPngMustNotValidateDelivery`, añadido solo como prueba. Nueva base PostgreSQL/PostGIS, rol API restringido; reglas exigen Fotografia. Ruta recibida/cargada en fixture, entrega pendiente; subir 16 bytes (firma PNG + ocho ceros, sin IHDR/IDAT/IEND); completar nombre/GPS y enviar EvidenciaEntrega.
- **Esperado:** rechazar el contenido corrupto con 400 o impedir que cumpla Fotografia; conservar pendiente, sin inventar una foto válida.
- **Actual observado:** PUT 204, operación aplicada, estado persistido **Entregado**. La aserción independiente `NotEqual(Entregado)` falla. No se usó cámara física ni se acredita entrega física humana; es evidencia de validación HTTP/DB insuficiente.
- **Impacto:** prueba fotográfica requerida sorteable por HTTP; intentos que solo comprueban existencia del archivo comparten el riesgo. No se afirma falsificación semántica de una fotografía decodificable.
- **Corrección propuesta:** decodificación segura y limitada de PNG/JPEG antes de cifrar/persistir, validación de estructura/dimensiones y límites de recursos, política explícita de imágenes inválidas; pruebas negativas PNG/JPEG truncados y control positivo real. Preservar hash, cifrado, inmutabilidad, idempotencia y contexto.

### H02 — P2 — mapa creado después de Dispose queda sin liberar

- **Ubicación:** `frontend/src/NexoRuta.Commerce/Components/Features/Envios/Shared/SelectorDestino.razor:169` y `DisposeAsync:370`.
- **Requisito:** selección/ajuste y recuperación de UI; DESIGN §accesibilidad/navegación, calidad §6.15. Interacción directa con el cambio optativo `1ca0172`.
- **Reproducción:** `AuditoriaIntegralSelectorDisposeTests.AuditoriaIntegral_MapReturnedAfterDisposeMustBeReleased`: bloquear la promesa `crear`, ejecutar Dispose como al navegar fuera, devolver después la referencia del mapa y terminar el render.
- **Esperado:** cancelar la inicialización o liberar inmediatamente el mapa tardío y no reactivar bindings/callbacks.
- **Actual observado:** `dispose` del mapa se invoca **0 veces**, esperado1; reproducción determinista roja. No acredita un crash real del SDK ni medición de memoria en navegador: confirma falta de cleanup del recurso retornado con un doble de interoperabilidad.
- **Impacto:** referencia/recursos JS y callbacks que sobreviven al abandono rápido; la guarda de reentrada no resuelve la disposición durante una espera.
- **Corrección propuesta:** bandera/generación de disposición y cancelación; usar referencias temporales y liberar resultados tardíos de importación/teclado/mapa. Probar además navegación durante importación y creación, con SDK real y transporte controlado.

### H03 — P1 — seguimiento público incompleto

- **Ubicación:** `backend/src/NexoRuta.Api/Features/Seguimiento/Contracts/SeguimientoEstadoResponse.cs:5`; `SeguimientoPublicoController.cs:35`; `backend/src/NexoRuta.Application/Seguimiento/Dtos/SeguimientoPublico.cs`; `frontend/src/NexoRuta.Tracking/Components/Pages/Seguimiento.razor`.
- **Requisito:** PDF §4 seguimiento: estado, **ventana estimada e historial**; §5.5 nº25; AP-07 y D14 de la planilla.
- **Escenario verificable:** destinatario abre token válido nuevo tras varias transiciones. El contrato público solo tiene Estado/Identidad; la UI no obtiene historial ni ventana. Un campo inexistente no puede aparecer por activar un worker.
- **Esperado/actual:** proyección pública minimizada con historia y ventana verificable / solo estado y marca. Es comprobación estática completa del contrato/consumidor, no una nueva aceptación visual del sitio público.
- **Impacto:** el destinatario no dispone de la información expresamente exigida. La historia canónica existente en PostgreSQL no compensa su ausencia en el recorrido público.
- **Propuesta:** proyección pública autorizada por token opaco, eventos sanitizados y ventana con procedencia; evitar IDs internos/PII, invalidar caché y probar token ajeno y rate limit. Resolver D-P01 sin inventar promesa.

### H04 — P1 — faltan recorridos obligatorios de destinatario y webhooks de comercios

- **Ubicación:** `backend/src/NexoRuta.Api/Features/Seguimiento/Controllers/SeguimientoPublicoController.cs:12` y `CancelacionPublicaController.cs`; `backend/src/NexoRuta.Api/Features/Reparto/Controllers/RutasController.cs:77`; `backend/src/NexoRuta.Infrastructure/Outbox/OutboxMessage.cs:5`; `backend/src/NexoRuta.Worker/Program.cs:39` y `Messaging/OutboxHandlerRegistry.cs`; catálogo Commerce `Components/Layout/CommerceNavigationCatalog.cs`.
- **Requisito:** CU-26 (solicitud de reprogramación **por destinatario**), CU-27 (avisos por cambios relevantes), CU-28/AP-05/NFR-09 (suscripciones, firma, reintentos, fallidos, historial/reenvío y receptor de prueba); PDF §4, §5.5 nº26–28 y §6.9.
- **Escenarios:** abrir seguimiento anónimo y solicitar reprogramación; cambiar estado y buscar aviso al destinatario; C1 intenta configurar y reenviar webhook. Inventario de entradas/modelos/handlers no contiene esos recorridos. Reprogramar existe solo para operador con `envios.gestionar`. Hay correos de contraseña/código de cancelación, generación de enlace y push al repartidor; no sustituyen avisos de estado al destinatario ni webhook al comercio.
- **Esperado/actual:** recorridos completos por el actor correcto / no implementados para esos actores y garantías. Son brechas de implementación comprobadas en el árbol inspeccionado, no un fallo de servicio externo probado.
- **Propuesta:** separar comandos públicos por token/reglas de la reprogramación interna; contratos outbox de estado, suscripción/entrega por comercio, firma, receptor local, backoff/DLQ y UI por tenant. No resolver enviando HTTP sin autorización a receptores reales.

### H05 — P1 — no están implementados el tablero en vivo y los reportes/liquidaciones

- **Ubicación:** `frontend/src/NexoRuta.Backoffice/Core/Navigation/BackofficeNavigation.cs:28`; `backend/src/NexoRuta.Api/Program.cs` y controladores indexados; `backend/src/NexoRuta.Infrastructure/Persistence/NexoRutaDbContext.cs:25` (modelos disponibles); `backend/src/NexoRuta.Worker/Program.cs`.
- **Requisito:** CU-29/30, AP-06/AP-09 y NFR-10; PDF §4, §5.5 nº29/30, §6.10; D19–D23.
- **Escenarios:** despachador necesita posición y riesgo actualizados sin refrescar; operador pide cumplimiento por zona/repartidor/comercio, motivos y volumen; comercio pide liquidación/cuenta corriente. No se localizaron Hub/MapHub/IHubContext ni pantallas/endpoints de esos productos ni cierre diario agregado. `/flota` es disponibilidad/custodia, B5 es estimación explícita, TarifaAplicada es cargo individual.
- **Esperado/actual:** tablero SignalR aislado y reportes/ledger sobre hechos / insumos persistidos y consultas operativas puntuales. Ausencia constatada por inventario de código/modelos/consumidores; no se ejecutó un stack SignalR inexistente.
- **Propuesta:** proyecciones de posición/riesgo y agregados desde eventos, aislados por tenant y con referencias a cargos históricos D22; validación multinstancia y totales independientes.

### H06 — P1 — caché distribuido obligatorio no localizado

- **Ubicación:** `backend/src/NexoRuta.Infrastructure/Envios/Geocodificacion/GeocodificadorGeoapify.cs:13` usa IMemoryCache; registros de servicios en API/Worker e inventario completo de `backend/src`.
- **Requisito:** NFR-07, PDF §6.7: dos CU con perfiles distintos, expiración/invalidación y hit/miss observables.
- **Escenario esperado/actual:** calentar lectura en API1 y reutilizar/invalidar coherentemente en API2 / no implementación distribuida de esos dos perfiles encontrada. Caché local del geocodificador no cumple ese contrato.
- **Límite:** comprobación estática de registro/consumidores, no benchmark remoto ni medición de hit/miss. No se instalaron dependencias para fingir cumplimiento.
- **Propuesta:** elegir dos lecturas de negocio y políticas documentadas, infraestructura y claves por tenant, invalidación por eventos/versiones y métricas; pruebas con dos instancias y dependencia caída.

### H07 — P1 — restore bloqueado falla con NU1004

- **Ubicación:** `backend/tests/NexoRuta.ArchitectureTests/packages.lock.json`, dependencia de proyecto nexoruta.api; `.github/workflows/ci.yml:105`, `backend/.github/workflows/ci.yml:56`.
- **Requisito:** NFR-01/NFR-15: compilación/pruebas reproducibles en pipeline.
- **Reproducción:** con el lock original exacto, `dotnet restore backend/tests/NexoRuta.ArchitectureTests --locked-mode`.
- **Esperado/actual observado:** restore sin modificar lock / NU1004: referencias de nexoruta.api cambiadas; faltan transitivas PdfPig/ZXing en ese lock. Un restore no bloqueado previo actualizó solo ese archivo; se preservó el original y se repitió el modo bloqueado para demostrar el defecto. **No se publica ninguna actualización de lock**.
- **Propuesta:** regeneración deliberada de locks de todos los consumidores afectados y validación del mismo restore de CI en clon limpio. No deshabilitar locked-mode en CI.

### H08 — P2 — oráculo de arquitectura incompatible con respuesta PDF

- **Ubicación:** `backend/tests/NexoRuta.ArchitectureTests/ShipmentBoundaryTests.cs:35`; `EnviosController.cs:219–232` (Etiquetas).
- **Requisito:** NFR-15, calidad de las pruebas y pipeline obligatorio.
- **Reproducción:** ejecutada la suite tras restore ordinario para poder observarla: 2 pasan, 1 falla `Assert.NotEmpty`, al exigir un tipo DTO en todos los endpoints. Etiquetas declara `application/pdf` y códigos HTTP sin DTO y devuelve File.
- **Esperado/actual:** política que preserve contratos API propios para JSON y contemple explícitamente el binario / regla universal de DTO JSON hace fallar el caso PDF legítimo. No se demuestra con ello un defecto funcional de impresión.
- **Propuesta:** caso binario con media type, status y contenido PDF verificables, conservando reglas de propiedad de DTO JSON y dependencia de capas. No borrar el test ni aceptar cualquier IActionResult.

### H09 — P2 — manifiesto Cloud no corresponde a esta base

- **Ubicación:** `scripts/cloud/checkpoint.json:3` y `environment-install.sh:5–9`.
- **Requisito:** preparación reproducible y base exacta del pedido.
- **Escenario:** instalar esta rama con environment-install. El manifiesto aún dice develop y SHA anteriores; su aserción no puede coincidir con los gitlinks auditados. **No se ejecutó ese script** ni se cambiaron sus referencias. Se ejecutó solo install-agent, que restaura dependencias y no hace checkout.
- **Impacto/propuesta:** onboarding se detiene o induce al operador a usar referencias antiguas. Corregir manifiesto/procedimiento en una corrección separada, con gitlinks como autoridad y prueba de clon limpio. La documentación de esta auditoría proporciona un camino que no sustituye fuentes.

## Decisiones y riesgos pendientes, separados de defectos demostrados

**D-P01 (rótulo de esta revisión, no decisión de negocio): compromiso temporal individual.** `CrearEnvioRequest.cs:49` y `CrearEnvioCommand.cs:9` capturan zona/modalidad/punto/publicación, pero ninguna franja/fecha prometida. `RestriccionesTemporales.cs:26–32` admite cualquier franja activa de la revisión histórica. D04/D07 piden zona y ventana comprometida y CU-14 compatibilidad con ella. Se comprobó qué hace el código; falta decidir con responsables si la promesa es una ventana individual, calendario elegible o plazo por modalidad, cómo se comunica y cómo se conserva al reprogramar. No se considera correcta la interpretación previa solo porque su test la codifica, ni se inventa una fecha alternativa.

**D-P02: discrepancias de CU-10.** `EfRutasRepository.Recepcion.cs:52–85` exige medidas iguales para Conforme y retiene Admitido hasta todos los cotejos conformes, aunque custodia ya sea Depósito. Preserva hechos/medidas/tarifas y es consistente internamente. El enunciado exige cotejar/registrar discrepancias, no determina bloqueo de ruta, aceptación con diferencia, corrección de declaración/tarifa ni devolución. Una diferencia físicamente real no se arregla marcando igualdad ficticia. Negocio debe decidir su resolución y actor; mientras tanto ese circuito queda pendiente, no defectuoso por una política inventada por el revisor.

**CU-11:** diagrama corregido y 13 estados del código son coherentes en las aristas examinadas. Se inspeccionaron asignaciones directas, gateway AplicarEstado, guard SQL y contexto de historia; paridad SQL cubre169 pares contra dominio, mientras unitarias enumeran aristas esperadas. Paridad no prueba que negocio haya autorizado cada arista. Entrega física conciliada puede conservar Cancelado sin perder evidencia/custodia; cierre no equivale a retorno/recepción/liberación. No se encontró en los 73 casos focales un bypass adicional de estado o una doble asignación, sin generalizarlo a todos los recorridos.

## Cambios acumulados y calidad de evidencia

Se compararon padres reales: Backend `3ebf059^..3ebf059` (restricciones/recepción/oráculo de competencia), `adcba41^..adcba41` (CU-10 y migración), `2340f66^..2340f66` (gateway CU-11 y paridad), `9a35b8b^..9a35b8b` (diagnóstico/sesión), `43cdaa8..bf4da61` (browsers); Frontend `c0f40c1^..c0f40c1` (recepción), `8c6545c^..8c6545c` y `d470cfd` (sesión), `bf36df3^..bf36df3` (tres regresiones Flota/Depósito) y `bf36df3..1ca0172` (mapa/browsers). Los diffs se leyeron junto al consumidor actual, no contra develop ni un checkpoint aproximado.

- CU-12/14/15/16: historia/rollback y competencia con dos sesiones SQL reales en los casos ejecutados. La prueba de exclusión usa recursos diferentes y observa esperas antes de soltar barrera; un solo éxito/409 y estado final son un oráculo más fuerte que Task.WhenAll o clics rápidos. La compatibilidad temporal sigue sujeta a D-P01.
- CU-10: migración aditiva con FORCE RLS y triggers contra UPDATE/DELETE/TRUNCATE; identificación GET sin escritura; idempotencia compara actor/bulto/payload; transacción combina cotejo/custodia/transición. Los nueve HTTP y browser incluidos en el filtro pasaron. Un MediaStream sintético no es cámara física.
- Flota/Depósito: se comprobó que los tres cambios de tests conservan la intención de errores reales/consulta efectiva/ausencia de falsa recepción y siguen el diseño de tareas existente. El cambio de Admitido a EnDevolucion en la prueba de recepción masiva corresponde al retorno, no al nuevo primer cotejo. 482 casos originales frontend pasaron con las cinco flags optativas, sin Skip.
- Sesión: lectura del cliente/handlers de generación y destinos seguros, diagnóstico sin tokens, y prueba real de dos portales/API/Postgres: pasa. Retiene 401 antiguo después de ingreso nuevo y contrasta rechazo actual, 403 y transitorio. No reproduce ni explica el **origen** del 401 histórico de arranque. No se declara resuelto ese incidente.
- Navegadores: cuatro integraciones usan API real/RLS/DB aislada; cinco frontend usan API controlada. Los proveedores/estilos/tiles están controlados; descarga estática del SDK/CSS Mapbox por proxy, sin token real ni consumo pago. Se inspeccionaron handshakes, esperas de visibilidad, fault después del commit y estados finales, no solo un contador de casos. Pasa la guarda de reentrada, pero faltaba abandono durante inicialización (H02).

## Límites explícitos

No es una auditoría exhaustiva de cada línea, cada política RLS, cada migración histórica ni un pentest. No se corrieron servicios SMTP/Rabbit/Kafka/Mongo/SignalR/observabilidad reales, carga remota, IaC apply/destroy ni despliegues. No se revisaron secretos por valor ni se publicaron bases/TRX/logs privados. No se ejecutaron Android/MAUI, cámara/lector físico, biometría, Bluetooth, precisión vial real o push con app cerrada. Las suites portátiles Mobile no los sustituyen. CU-06 y aceptación humana siguen abiertos.

No hay herramientas Gentle-AI/Engram/revisión nativa disponibles en el catálogo de esta sesión; se continuó con inspección, Git, Python OOXML/PDF, .NET, PostgreSQL/PostGIS y Playwright. No se atribuye revisión a herramientas ausentes.

La planilla conserva encabezado «Ninguno está seleccionado», pero F6/F8–F12 selecciona OPT-03/05/06/07/08/09 (14 puntos planificados). Se reporta el contenido individual, sin otorgar puntos ni aceptación. No hay evidencia específica aquí que permita declarar cumplidos Kafka de flota/replay, NoSQL de envíos, carga remota, cobertura >70% o push real.
