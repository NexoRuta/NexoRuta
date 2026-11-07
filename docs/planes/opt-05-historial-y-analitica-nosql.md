# OPT-05 — Plan de implementación, consolidación y verificación

Fecha de análisis: 07/11/2026. Documento para un agente de IA que trabaje en el checkout combinado de NexoRuta. **Este plan no ejecuta la implementación ni habilita servicios o despliegues.**

## 1. Punto de partida y criterio de alcance

La [card OPT-05 de Notion](https://app.notion.com/p/40a032f1caff814c8c02c621bd7835ee), consultada mediante MCP, figura como `Not started`, prioridad Media, módulos M02/M06. Su observación del 31/10 dice que MongoDB solo participa en recuperación de contraseña. **Esa observación quedó desactualizada:** el `develop` inspeccionado ya contiene historial documental, analítica básica, índices, TTL, API y pruebas de integración. No crear otro módulo desde cero ni repetir la infraestructura existente.

El trabajo comienza verificando ese recorrido y cerrando sus brechas concretas. La presencia del código y los informes históricos no acredita una ejecución actual ni el funcionamiento de una instalación desplegada. Tampoco hace falta ampliar OPT-05 a todos los reportes de CU-30.

Los cuatro repositorios estaban limpios, en `develop`, y respondieron `Already up to date` a `git pull --ff-only origin develop`:

| Repositorio | Commit inspeccionado |
| --- | --- |
| Raíz | `d9e56ac4fc09514766a28744d8c9318f055e20d2` |
| Backend | `8c8cffdd2a7c841857023af06dcf8d7243c9d10c` |
| Frontend | `06b1ca380aea0ec68dbbaafff5de9a63a24d8f6b` |
| Mobile | `53f6be2cdec48f48e30e390060feeaefb5be0ead` |

Los gitlinks de la raíz coinciden con esas puntas. Estos SHAs describen la inspección; no son instrucciones de retroceder futuros checkouts. El ejecutor debe registrar sus propios SHAs y adaptar el plan si cambió el código.

### Fuentes de alcance y precedencia

Leer los originales, sin ejecutar macros de las planillas:

| Fuente | Regla aplicable |
| --- | --- |
| `docs/alcance/Laboratorio__NET_2026.pdf`, §7.2, página PDF 9 | Base documental para eventos históricos y consultas analíticas, índices adecuados, retención y API de lectura paginada/filtrable, sin trasladar esa carga a la base transaccional. |
| `docs/alcance/Calcs/Casos de Uso - Responsables.xlsm`, hoja `Opcionales`, fila 8 | OPT-05 está **Seleccionado**, vale 2 puntos y corresponde a M02/M06. El encabezado que dice que ninguno está seleccionado contradice las filas: usar la decisión específica. |
| Misma planilla, hoja `Dependencias`, D23; hoja `CU obligatorios`, CU-12 y CU-30 | Los indicadores parten de hechos inmutables; reportes/liquidaciones tienen alcance funcional propio. |
| `docs/alcance/Laboratorio__NET_2026.pdf`, §6.1, §6.3–6.5, §6.8 y §6.15 | .NET 10, monolito modular, dependencias hacia las capas internas, seguridad por organización, persistencia controlada, mensajería y pruebas. |
| `docs/alcance/Entregas/Entrega-10-4-2026-Grupo-4.pdf`, ADR y arquitectura | NoSQL y Kafka seleccionados; preservar la cola de trabajo y justificar su costo. |
| `docs/alcance/ADR-MT-001-PostgreSQL-RLS.md` | Operador como tenant; comercio limitado a sus envíos; identidad y permisos persistidos; roles restringidos y contexto transaccional. |
| `AGENTS.md`, `backend/docs/workflow/arquitectura-backend.md` | Estructura del código, contratos explícitos, controladores delgados y un tipo público principal por archivo. |
| `docs/seguimiento-tablero/TRAZABILIDAD.md`, `VALIDACION.md`, `DEMOSTRACION.md` | Implementación y evidencias posteriores a la card. Los resultados citados allí son históricos y conservan sus propios SHAs. |

Los PDF históricos de ADR que indican opcionales todavía no elegidos y los README que describen funciones pendientes no invalidan la selección de la planilla ni lo que efectivamente existe en el código actual. Si una contradicción afecta una regla de negocio, registrarla; no resolverla inventando comportamiento.

## 2. Inventario comprobado en el código

Todas las rutas de esta sección son relativas a la raíz del superproyecto.

| Pieza existente | Ubicación y comportamiento |
| --- | --- |
| Contrato de evento | `backend/src/NexoRuta.Application/Operacion/EventoOperativo.cs`: v1, identidad, operador/comercio, entidad/envío/ruta, versión, correlación, fecha física y de registro, datos por tipo. Tipos: `Envio`, `Bulto`, `Posicion`, `Ruta`, `Parada`, `Estimacion`, `Flota`. |
| Captura transaccional | Migración `20261106190000_OperationalEventStream.cs`: triggers sobre hechos canónicos, allowlist de campos y escritura en la tabla compartida `OutboxMessages`. No depende de MongoDB o Kafka para aceptar el hecho. |
| Publicación | `backend/src/NexoRuta.Worker/Messaging/OperationalConsumers.cs`, `OperationalOutboxHandler`; `KafkaEnvioCreadoPublisher.PublicarOperativoAsync`. Topic `nexoruta.operacion.v1`; clave `operadorId:entidadId`. |
| Consumidor documental | `OperationalHistoryConsumer`, grupo `nexoruta-operational-history-v1`, en el proceso `worker-kafka` existente. Inserta en MongoDB, acusa en PostgreSQL y después confirma Kafka. |
| Proyección MongoDB | `backend/src/NexoRuta.Infrastructure/Operacion/OperationalMongoStore.cs`: colección `operational_history_v1`, `_id=eventId`, inserción inmutable, rechazo de duplicados divergentes, consultas y agregación. |
| Retención | 90 días desde `RegistradaEnUtc`, índice TTL sobre `expiresAt`, y filtro de expiración en consultas. El replay conserva la fecha original. |
| API | `backend/src/NexoRuta.Api/Features/Operacion/OperationalController.cs`: `GET /api/operacion/historial` y `GET /api/operacion/analitica/volumen`; permiso `envios.consultar`; ámbito de operador/comercio. |
| Consulta actual | Rango `[desde,hasta)` de hasta 31 días; límite 1–100; offset 0–10000; filtros de envío y tipo; orden descendente por registro e identidad; tiempo máximo MongoDB de 3 s. |
| Estado de proyección | `OperationalReadStore.ReadHealthAsync`; migraciones `OperationalProjectionHealth` y `OperationalSourceFrontier`: latidos, lag, capturados/documentados y recibos idempotentes. Ventana de frescura de 15 s. |
| Reconstrucción inicial | Migración `20261106190600_BootstrapOperationalLog.cs` y `OperationalBootstrapTests`. No sustituirla por un script que vuelva a emitir efectos de negocio. |
| Pruebas | `OperationalMongoIsolationTests`, `OperationalProjectionTests`, `OperationalConsumerHealthTests`, `OperationalBootstrapTests`, bajo `backend/tests/NexoRuta.IntegrationTests/Operacion/`. |
| Stack | SDK `10.0.401`; ASP.NET Core/EF Core 10; `MongoDB.Driver` 3.12.0 en Infrastructure y Worker; Confluent.Kafka 2.15.1. MongoDB 8.0 en Compose/tests. Conservar las versiones y locks del checkout; no actualizar paquetes por rutina. |
| Composición local | `compose.yaml` configura MongoDB y `worker-kafka`; `backend/compose.operacion.yaml` agrega conexión a la API y creación del topic con 3 particiones y retención Kafka ilimitada. |

### Brechas y límites que debe resolver el plan

1. **La API concentra coordinación y persistencia:** usa `IServiceProvider`, MongoDB.Driver, stores concretos, selección de contexto SQL y respuestas anónimas en el controlador. Consolidar siguiendo los UseCases/Repositories y contratos HTTP del proyecto, sin reescribir el resto de Operación.
2. **La evidencia de cierre es parcial para los bordes:** el test Mongo existente comprueba dos páginas, un tipo de evento, aislamiento, duplicados, expiración lógica y 503. No demuestra por sí solo todos los límites HTTP, tipos, índices efectivos, TTL físico ni costo de consultas. Ampliar escenarios con resultados específicos.
3. **El volumen actual cuenta eventos por tipo**, no envíos únicos, bultos entregados ni dinero. Explicitar esa semántica para no presentar snapshots y transiciones como envíos nuevos. No declarar CU-30 implementado por este endpoint.
4. **GCP tiene una diferencia estática verificable:** `deploy/gcp/compose.yaml` configura MongoDB en `worker-kafka`, pero no en el entorno compartido de API. `scripts/gcp/vm_deploy.py` crea solo los topics de alta y recuperación; no crea el topic operativo. Sin corregir/configurar esas piezas no se acredita la API documental remota.
5. **Monitoreo remoto incompleto para este flujo:** `scripts/gcp/monitor_agent.py` tiene un único `KAFKA_GROUP` de recuperación. No permite inferir el atraso de history/board.
6. **Retención y reconstrucción tienen costos distintos:** MongoDB vence documentos, Kafka retiene el log sin límite y PostgreSQL conserva recibos/fronteras. No asumir que TTL limita todo el almacenamiento ni que un MongoDB vacío queda detectado por los contadores históricos.

Los puntos 1–3 son la consolidación propuesta de calidad y verificabilidad. El criterio académico ya tiene implementación en el árbol: no atribuirle requisitos nuevos como cursores, dashboards o reportes financieros. Los puntos 4–5 son preparación operativa versionable; aplicar cambios a una instalación real es una etapa separada.

## 3. Resultado que debe producir la implementación

Conservar este recorrido:

```text
Hecho aceptado + outbox, en una transacción PostgreSQL
  -> publicador Kafka del worker existente
  -> nexoruta.operacion.v1
     -> grupo board existente -> lectura operativa PostgreSQL
     -> grupo history existente -> MongoDB -> acuse PostgreSQL -> commit Kafka

Petición autenticada -> caso de uso -> ámbito validado
  -> estado de proyección PostgreSQL + consulta documental MongoDB
  -> contrato HTTP explícito, paginado/filtrable o agregado
```

Invariantes obligatorios:

- PostgreSQL sigue siendo autoridad de negocio e historial canónico. MongoDB es una proyección derivada de lectura. Su caída no revierte hechos ya aceptados ni habilita cálculos masivos contra tablas transaccionales como fallback.
- Los triggers/outbox existentes cubren las fuentes actuales. No agregar una segunda emisión C# del mismo hecho, otra tabla outbox, otro broker, proyecto ejecutable o contenedor de worker.
- Las lecturas MongoDB exigen operador validado y, para comercio, su `ComercioId` derivado de sesión. MongoDB no hereda el RLS de PostgreSQL: imponer el filtro también dentro del repositorio documental.
- Un usuario operador solo consulta su operador; un comercio consulta sus hechos dentro del operador solicitado. Los hechos de flota sin comercio no se exponen al comercio. No exigir una afiliación comercio–operador que el sistema no contempla.
- No incluir credenciales, enlaces/token de seguimiento, destinatarios, direcciones, fotos, firmas, evidencias ni datos de correo de recuperación. Preservar la allowlist operativa; GPS y datos del repartidor requieren el permiso y ámbito operativo correspondientes.
- El replay conserva identidad, registro y expiración, y no reenvía avisos, altera estados, custodia, versiones, tarifas o B1–B5.
- Las pruebas mantienen Mapbox con `permanent=false` y Geoapify sin consumo real, con respuestas controladas. No usar este módulo para persistir resultados temporales de geocodificación.
- No mantener aliases, adaptadores o versiones paralelas por compatibilidad histórica. Si un contrato cambia, actualizar todos sus productores/consumidores/tests juntos. Conservar migraciones y estado persistente.

## 4. Secuencia ejecutable para el agente

### Paso 0 — Confirmar fuentes y obtener una línea base

1. Leer `AGENTS.md`, este plan, las fuentes de alcance anteriores y `backend/docs/workflow/arquitectura-backend.md`. Antes de instalar o arrancar, leer los tres archivos de continuidad indicados por AGENTS.
2. Registrar branch, SHA, estado y gitlinks de los cuatro repos. Si hay trabajo ajeno, preservarlo; no hacer stash/reset/checkout forzoso. La actualización a `develop` de este análisis ya está hecha. En Cloud, usar los gitlinks del checkout, no `--remote` ni SHAs del manifiesto histórico.
3. Confirmar SDK exacto y dependencias mediante restore bloqueado. Compilar y ejecutar primero las pruebas existentes de historial, replay y salud de consumidores. Guardar resultados, tiempos, comandos y SHAs fuera del código fuente.
4. Para integración, usar servicios efímeros propiedad de las fixtures. Comprobar que Docker está disponible y que MongoDB 8 puede arrancar en el kernel del ejecutor. El CI actual usa `ubuntu-22.04` por la incompatibilidad documentada; no desactivar la protección del servidor ni reemplazar MongoDB real por mocks.
5. Si no hay Docker, continuar código/documentación y pruebas puras; registrar integración como pendiente. El camino Cloud mínimo no levanta MongoDB/Kafka ni acredita OPT-05. No usar servicios del Windows del usuario, `.env` o una base operativa como sustituto Cloud.

**Salida:** informe breve de línea base que distingue implementación existente, pruebas realmente ejecutadas y bloqueos. Si cambió la implementación, corregir el inventario antes de avanzar.

### Paso 1 — Formalizar los casos de lectura y los contratos

Agregar únicamente tipos que se utilicen. Los nombres siguientes son **propuestos**, no archivos ya existentes:

| Ruta propuesta dentro de Backend | Responsabilidad |
| --- | --- |
| `src/NexoRuta.Application/Operacion/Commands/ConsultarHistorialOperativoQuery.cs` | Entradas normalizadas de historial. Mantener `Commands` como convención existente para entradas, sin introducir un framework CQRS. |
| `src/NexoRuta.Application/Operacion/Commands/ConsultarVolumenOperativoQuery.cs` | Período y operador solicitado para la agregación. |
| `src/NexoRuta.Application/Operacion/Dtos/AmbitoLecturaOperativa.cs` | Operador y comercio resueltos por el servidor; no DTO vinculable desde HTTP. |
| `src/NexoRuta.Application/Operacion/Repositories/IHistorialOperativoRepository.cs` | Consulta paginada y agregación, con ámbito obligatorio y tipos ajenos a BSON/HTTP. |
| `src/NexoRuta.Application/Operacion/Repositories/IEstadoProyeccionOperativaRepository.cs` | Lectura de frontera/salud necesaria para el historial. |
| `src/NexoRuta.Application/Operacion/UseCases/ConsultarHistorialOperativoUseCase.cs` | Resolver actor, validar entrada, consultar salud–datos–salud y construir resultado. |
| `src/NexoRuta.Application/Operacion/UseCases/ConsultarVolumenOperativoUseCase.cs` | Misma autorización/frescura, con agregación de eventos. |
| `src/NexoRuta.Application/Operacion/Results/` | Un archivo por resultado de historial, volumen y estado compartido que realmente se necesite. |
| `src/NexoRuta.Api/Features/Operacion/Contracts/Requests/` y `Responses/` | Modelos HTTP explícitos, separados de contratos internos, con mapeo y OpenAPI. |

Implementar autorización siguiendo `IUsuarioActual` y `ListarEnviosUseCase`: obtener el actor persistido por request; operador distinto implica denegación; para comercio derivar su ID y nunca permitir que la request lo reemplace. Mantener `[Authorize(Policy = "envios.consultar")]`.

Mover la selección SQL del operador del comercio al adaptador de salud en Infrastructure. Reutilizar el mismo `NexoRutaDbContext` y transacción del middleware, usando `RlsTransaction.SelectOperatorAsync` antes de las consultas SQL que lo requieren. No crear otro contexto ni modificar el ciclo de commit del request. `OperationalReadStore` puede seguir atendiendo el tablero; extraer o delegar solo la parte de salud que usa este módulo.

`OperationalMongoStore` implementará el puerto documental. Si comparte lectura con inserción del worker, conservar esa clase y su ciclo singleton; no introducir un repositorio genérico ni duplicar colección/índices. La API recibe los casos de uso por constructor y elimina su dependencia directa de MongoDB y la resolución de servicios para estos dos endpoints. El adaptador traduce fallos documentales a una excepción de Application acotada; el límite HTTP la transforma en 503 sin revelar detalles de conexión. Cancelación del request no se transforma en indisponibilidad.

Mantener `/fotografia` y SignalR fuera del refactor salvo el ajuste mínimo de inyección que exija separar historial. Un tipo público principal por archivo; no copiar las clases múltiples de `OperationalConsumers.cs` como convención para código nuevo. No introducir MediatR, AutoMapper o un nuevo proyecto.

**Salida:** dependencias internas limpias y contratos HTTP documentados; mismo aislamiento y rutas de lectura. Pruebas de autorización y caso de uso sin infraestructura, y prueba de arquitectura que impida referencias MongoDB/EF/ASP.NET Core en Application.

### Paso 2 — Consolidar el documento, idempotencia y retención

1. Conservar `operational_history_v1`. La identidad global es el `EventId` original y corresponde al `_id` de MongoDB. Conservar en BSON los campos actuales: operador/comercio/envío, tipo, versión, correlación, registro, ocurrencia, expiración y payload; entidad y ruta ya viajan en el envelope del payload. Promover otro campo a raíz solo si una consulta autorizada lo necesita.
2. Mantener el contrato de `EventoOperativo.Validar` y el JSON `JsonSerializerDefaults.Web`. Asegurar que el envelope validado y el payload que se persiste representan el mismo evento. Actualmente `InsertAsync` recibe ambos por separado: evitar que una divergencia interna produzca filtros de un tenant y contenido de otro. Elegir una sola representación validada para construir documento y respuesta; conservar rechazo de JSON/schema inválido.
3. Una reentrega idéntica es éxito idempotente, incluida una entrega concurrente. Comparar semánticamente el contenido, no bytes o orden de propiedades; mismo ID con distinto ámbito, versión, fechas o datos se rechaza. El duplicado no actualiza `expiresAt`. No usar un upsert que sobrescriba un hecho ya guardado.
4. Mantener `expiresAt = registradaEnUtc + 90 días`, como fecha BSON UTC y TTL de un solo campo con `expireAfterSeconds=0`. No convertir expiración a texto, usar hora de consumo ni tomarla de `ocurridaEnUtc`: un GPS recibido tarde conserva ambos tiempos.
5. Inyectar `TimeProvider` donde se evalúe expiración lógica. Tomar un solo `ahora` por consulta, para que los bordes sean reproducibles. Los tests de fecha usan reloj controlado; el TTL físico se verifica aparte contra el servidor real.
6. Conservar la política actual para eventos ya expirados que llegan por replay: insertar/reconocer idempotentemente con la expiración original, excluirlos inmediatamente de la consulta y dejar su eliminación al TTL. Luego continuar el acuse. No renovarlos ni bloquear el replay por antigüedad. Optimizar ese replay para omitir escrituras vencidas queda fuera de este corte.
7. Conservar la política fija de 90 días para este corte. Hacerla configurable no es requisito. Un cambio posterior de retención debe especificar qué sucede con documentos existentes; cambiar una constante no actualiza sus fechas.

El TTL borra la proyección, no el historial canónico, outbox, log de Kafka o recibos PostgreSQL. El barrido no es inmediato: la API siempre filtra `expiresAt > ahora`, incluso antes del borrado físico.

**Salida:** reentregas idempotentes, colisiones divergentes rechazadas, fechas UTC y retención comprobadas sin pérdida del estado fuente.

### Paso 3 — Completar y probar el contrato de consulta

Conservar la paginación acotada por offset, suficiente para la card. No añadir simultáneamente cursores y offset ni prometer una fotografía estable entre requests concurrentes.

| Elemento | Contrato objetivo |
| --- | --- |
| Ruta historial | `GET /api/operacion/historial` |
| Entradas | `operadorId`, `desde`, `hasta`; opcionales `envioId`, `tipo`, `offset=0`, `limite=50`. Fechas ISO 8601 con zona/UTC, normalizadas a UTC. |
| Validación | IDs válidos y no vacíos; fechas obligatorias; `desde < hasta`; diferencia máxima 31 días; límite 1–100; offset 0–10000; tipo opcional limitado al catálogo del contrato. Tipo desconocido o vacío explícito produce 400. |
| Filtro | Operador obligatorio, comercio de sesión cuando corresponde, envío y tipo cuando se soliciten, rango por registro `[desde,hasta)`, exclusión lógica de expirados. Nunca aceptar JSON de filtros Mongo del cliente. |
| Orden | `registradaEnUtc DESC, _id DESC`, con desempate único; probar varios eventos con la misma fecha. |
| Respuesta | DTO explícito con `estadoProyeccion`, `verificadaEnUtc`, `retencionDias`, `offset`, `limite`, `datos`. Los datos contienen el envelope operativo permitido, sin BSON técnico ni `expiresAt` interno. |
| Ruta analítica | `GET /api/operacion/analitica/volumen`, mismo operador, fechas, validación temporal y aislamiento. |
| Agregación | `$match` por ámbito/registro/expiración **antes** de `$group`; sumar eventos por `tipo` en MongoDB. No cargar todos los documentos a .NET ni agrupar en PostgreSQL. |
| Respuesta analítica | DTO explícito con estado, verificación, retención, desde/hasta y `volumenPorTipo`. Documentar que son cantidades de eventos por tipo, no envíos únicos. Conjunto vacío devuelve diccionario vacío. |
| Errores | 400 entrada inválida; 401 sin sesión válida; 403 sin permiso/ámbito; 503 MongoDB sin configuración, caído o excediendo el presupuesto de consulta. Conjunto vacío autorizado: 200. Mantener ProblemDetails y el comportamiento de autenticación del proyecto. |

No necesita `total` exacto, exportación ni un endpoint de escritura. Si se agrega `hayMas`, obtener `limite+1` y devolver solo `limite`, con prueba de borde; no ejecutar un conteo total por página. No ampliar campos por conveniencia del frontend.

Conservar las lecturas de salud antes/después de MongoDB. `Actualizada` exige que ambas sean actuales y que no cambien capturados/documentados; si cambian, devolver estado conservador. `verificadaEnUtc` es la fecha de comprobación, no una garantía de snapshot distribuido entre PostgreSQL/MongoDB. Una proyección atrasada o sin latidos puede devolver datos retenidos con advertencia en el contrato; MongoDB inaccesible devuelve 503 y nunca una lista vacía que parezca válida.

Las consultas están vivas: con offset, nuevas inserciones o expiraciones entre páginas pueden desplazar resultados. Documentarlo en OpenAPI. Si posteriormente se requiere recorrer un conjunto estable bajo escrituras, tratarlo como cambio deliberado a cursor y frontera de consulta, actualizando todos los consumidores; no es condición nueva de OPT-05.

**Salida:** API tipada, casos de uso probados y contratos OpenAPI verificables. Buscar consumidores reales antes de alterar la forma JSON. En este análisis no se encontraron llamadas de Frontend/Mobile a estas dos rutas.

### Paso 4 — Verificar índices con las consultas reales

Mantener inicialmente los índices actuales, además del `_id_` único creado por MongoDB:

| Nombre | Claves |
| --- | --- |
| `operator_history` | operador ascendente, registro descendente, `_id` descendente |
| `operator_shipment_history` | operador, envío, registro descendente, `_id` descendente |
| `tenant_history` | operador, comercio, registro descendente, `_id` descendente |
| `shipment_history` | operador, comercio, envío, registro descendente, `_id` descendente |
| `history_retention` | `expiresAt` ascendente; TTL absoluto, 0 segundos |

1. Verificar por `listIndexes` nombre, orden de claves, unicidad de `_id` y opciones TTL. La inicialización debe ser idempotente ante dos instancias; un índice incompatible se informa, no dispara borrado de colección/índices a ciegas.
2. Preparar datos sintéticos representativos de más de un operador/comercio, varias fechas, tipos y envíos. Ejecutar `explain("executionStats")` para operador, operador+envío, comercio, comercio+envío y variantes con tipo; incluir el pipeline de volumen.
3. Guardar plan ganador, documentos retornados/examinados, claves examinadas y tiempo. Evaluar con suficiente selectividad: un dataset de tres filas no demuestra un índice adecuado. No fijar artificialmente el planificador con un `hint` en producción para hacer pasar el test.
4. Si el filtro por tipo examina demasiadas filas dentro del rango, agregar solo el índice que respalde el perfil medido, por ejemplo `(operadorId,tipo,registradaEnUtc DESC,_id DESC)` y su variante con comercio cuando sea necesaria. Justificar espacio y costo de inserción antes de multiplicar combinaciones.
5. Conservar `MaxTime` de consulta y agregación (3 s como valor inicial actual), límite de página y cancelación. Medir también offset alto dentro del límite. Registrar capacidad del entorno sintético; no afirmar rendimiento remoto o productivo sin medirlo allí.

Provisionar índices con el worker/provisioner, no conceder DDL al usuario lector de la API. Puede usarse el `InitializeAsync` existente con credencial acotada; separar creación de índices de la lectura. No hacer que cada GET intente crear índices.

**Salida:** inventario real de índices y evidencia de planes para los perfiles publicados; cualquier índice nuevo tiene una consulta y medición que lo justifican.

### Paso 5 — Probar el orden durable y la recuperación

Preservar el orden de `OperationalHistoryConsumer.ProjectAsync`:

1. Validar envelope y clave Kafka.
2. Persistir/reconocer la reentrega en MongoDB, o aplicar la política documentada de expirados.
3. Ejecutar `ack_operational_document` con el rol worker y contexto limitado existentes.
4. Confirmar el offset únicamente después de ambos efectos durables.

No hay transacción distribuida entre MongoDB, PostgreSQL y Kafka. Probar las tres ventanas de fallo: antes de insertar, después de insertar/antes del acuse, y después del acuse/antes del commit Kafka. La reentrega debe dejar un solo documento y un solo incremento de frontera. Una falla temporal no puede confirmarse indirectamente al avanzar al siguiente mensaje de la misma partición.

Mantener grupos independientes de board/history. Una caída documental no debe detener la reconstrucción del tablero ni el publicador. Conservar el tratamiento actual de eventos inválidos: bloquear/reintentar la partición, registrar identidad/offset/tipo de error sin payload privado y alertar; no saltar el hecho ni inventar un DLQ que lo descarte. Si se cambia la política de retry, usar espera acotada con cancelación y no cambiarla para todos los consumidores sin necesidad.

Los consumidores hospedados son singleton; los DbContext se obtienen mediante scope por operación como hace el código actual. No capturar un contexto scoped en el constructor ni mantener una transacción SQL mientras se espera la recuperación de MongoDB.

**Reconstrucción:** reutilizar el escenario de destinos aislados de `OperationalProjectionTests`: topic/grupo nuevos, MongoDB nuevo y PostgreSQL de prueba independiente para sus fronteras. Nunca reiniciar offsets de grupos activos. Comparar identidades/contenido del período retenido, no solo cantidades; comparar el tablero sin IDs de revisión locales.

No conectar un MongoDB recién vaciado a las fronteras/offsets activos y declarar `Actualizada`: los recibos SQL no prueban que los documentos sobrevivan a una pérdida/restauración. Este corte no incorpora reconstrucción online sobre el destino activo. El runbook debe exigir destino aislado, replay verificado y procedimiento explícito de promoción que reinicialice/coincida con su frontera; si se necesita promoción online, diseñar primero generación de proyección y fronteras por generación. No resolverlo borrando recibos o cambiando offsets en una instalación real.

**Salida:** evidencia de recuperación independiente e idempotente; runbook de replay con límites y sin comandos destructivos sobre destinos operativos.

### Paso 6 — Alinear configuración y preparar operación

1. Registrar opciones y adaptadores en `backend/src/NexoRuta.Infrastructure/Persistence/DependencyInjection.cs` o una extensión específica de Operación llamada por API/Worker. Reutilizar un `IMongoClient` singleton por configuración; no crear clientes por request. Mantener scopes correctos para EF.
2. Validar configuración por Options: URI/database requeridas cuando se habilita lectura documental; tiempos positivos y acotados. Con ambas ausentes, conservar el modo sin MongoDB del entorno Cloud mínimo: registrar siempre el puerto de lectura, con una implementación indisponible que arroje la excepción de Application traducida a 503. Con ambas presentes, registrar el cliente/store real; con una sola o valores inválidos, fallar explícitamente al validar configuración. Así los casos de uso se resuelven sin Service Locator incluso sin MongoDB. No crear una base con nombre de respaldo silencioso. Distinguir configuración inválida de servicio temporalmente caído.
3. API y worker deben apuntar al mismo destino operativo; mantener independiente la colección de recuperación y su comportamiento. `MongoDB`/`MongoDb` son claves equivalentes en la configuración .NET: normalizar el código si se toca, sin agregar aliases de compatibilidad.
4. Revisar el overlay local `backend/compose.operacion.yaml` con `compose.yaml` en un proyecto sintético explícito. Configurar el perfil Kafka, topic y particiones; no ejecutar el Compose habitual del usuario por accidente ni imprimir un `config` con secretos interpolados.
5. Preparar en `deploy/gcp/compose.yaml` conexión/database documental para ambas API mediante el entorno compartido, y `Operational__Partitions=3` coherente con el topic/worker. Reutilizar host privado y mecanismos de secretos existentes. MongoDB queda en la red privada.
6. Extender `scripts/gcp/vm_deploy.py`: crear idempotentemente `nexoruta.operacion.v1` con 3 particiones, factor 1 para el broker actual y retención explícita `-1/-1`, como el overlay local. No alterar automáticamente topics existentes, reducir particiones, borrar log o cambiar offsets; detectar una configuración incompatible y detener la activación con diagnóstico. La retención ilimitada es una decisión existente para replay, no una recomendación de capacidad sin límite.
7. Definir credenciales Mongo de mínimo privilegio: API solo lectura de colección operativa; worker inserción/lectura para deduplicar; aprovisionamiento de índices con permiso separado cuando corresponda. No usar la cuenta administradora como diseño final ni dar a la API acceso a la colección de seguridad. Provisionar y probar usuarios sobre un destino propio antes de documentar el cambio operativo; no rotar secretos reales durante esta implementación.
8. Extender el monitoreo existente para los grupos history y board además del de recuperación, preservando sus métricas previas. Observar lag, latido, estado de la proyección, fallos/tiempos de consulta y tamaño de Mongo/Kafka/recibos. Labels de cardinalidad acotada: proyección/tipo/resultado; IDs de evento/correlación pueden ir en logs, no como labels por evento/tenant.
9. Agregar tests a `scripts/gcp/test_vm_deploy.py` y `test_delivery.py` para topología/configuración, destino compartido y protección de topics. Si se modifica `monitor_agent.py`, probar recolección de los tres grupos con transporte simulado y ausencia de secretos en errores. No operar GCP para verificar estos tests.

**Salida:** configuración versionada revisable, permisos definidos, servicios sintéticos reproducibles y pruebas de infraestructura. Preparar instrucciones de habilitación; ejecutar un despliegue, migración persistente o cambio de credenciales requiere una tarea operativa concreta sobre un destino identificado.

### Paso 7 — Ejecutar aceptación y dejar la entrega trazable

Ampliar los archivos existentes y dividir escenarios largos por comportamiento cuando mejore diagnóstico. Usar fixtures y `OperationalInfrastructureCollection` para evitar levantar en paralelo conjuntos completos de servicios.

| Grupo de pruebas | Casos mínimos y comprobación |
| --- | --- |
| Application, puras | Operador propio/ajeno; comercio derivado de sesión; todos los límites de consulta; tipo inválido; sin datos; estado antes/después conservador; cancelación. El repositorio no se invoca con entrada/ámbito inválidos. |
| HTTP con login/RLS restringidos | Sin token 401; sin permiso y operador ajeno 403; comercio A no ve B; mismo comercio en dos operadores no mezcla resultados; IDs vacíos/malformados, fechas ausentes/invertidas/32 días, límites 0/101 y offsets -1/10001 dan 400; 31 días/1/100/10000 aceptados. Probar también analítica. |
| Documento/idempotencia | Cada tipo soportado; datos y scope coinciden con payload; duplicado concurrente idéntico cuenta una vez; orden de propiedades no altera igualdad; divergencia de ámbito/fecha/versión/datos se rechaza. |
| Paginación/filtros | Varias filas con igual fecha; páginas sucesivas sobre dataset estable sin duplicados/huecos; aislamiento se aplica antes del límite; filtro combinado operador/comercio/envío/tipo; inclusión de `desde` y exclusión de `hasta`; última página/vacío; límites máximos. |
| Retención | `expiresAt` original; replay no lo renueva; vencido excluido antes del barrido; justo en expiración excluido con reloj controlado; TTL físico con sondeo y deadline razonable, sin depender de un sleep exacto. |
| Analítica | Conteos de eventos por tipo coinciden con documentos válidos; excluir otros tenants/comercios, expirados y duplicados; varias transiciones del mismo envío cuentan como varios eventos, sin presentarlo como volumen de envíos. |
| Resiliencia | Mongo detenido da 503; historial atrasado muestra estado explícito; las tres ventanas de fallo del consumidor no pierden ni duplican efecto; board sigue avanzando con history detenido. |
| Frescura | Todas las particiones vacías, primer evento, reinicio con offset confirmado; outbox pendiente implica atraso; falta de latido implica indisponibilidad; cambios de frontera durante lectura impiden `Actualizada`. |
| Índices/costo | Inspección real y `explain` de perfiles de consulta, incluyendo por tipo; retención del log y tamaño de índices documentados. |
| Captura canónica | Rollback de un hecho no deja su outbox; un hecho aceptado con Mongo apagado sí conserva outbox; bootstrap no muta dominio ni emite avisos históricos. Reutilizar/ampliar `OperationalBootstrapTests`. |
| Arquitectura/OpenAPI | Application sin drivers/frameworks externos; respuestas HTTP propias de API, schemas y estados documentados. Reutilizar el patrón de `ShipmentBoundaryTests`, sin debilitar reglas previas. |
| Regresión dirigida | `OperationalProjectionTests`, `OperationalMongoIsolationTests`, `OperationalConsumerHealthTests`, `OperationalBootstrapTests`; recuperación Mongo y publicación outbox si se tocan sus servicios compartidos. |

No usar mocks como evidencia de aislamiento Mongo, índices, TTL, commit Kafka o transacciones SQL. Las pruebas puras sí aíslan reglas de aplicación. No modificar aserciones existentes para ocultar fallos ni adjudicar a este cambio los fallos históricos sin reproducirlos en su SHA.

Comandos desde la raíz, en un entorno preparado con Docker para integración:

```powershell
dotnet restore backend/NexoRuta.sln --locked-mode --nologo
dotnet build backend/NexoRuta.sln -c Release --no-restore --nologo
dotnet test backend/tests/NexoRuta.UnitTests/NexoRuta.UnitTests.csproj -c Release --no-build --no-restore
dotnet test backend/tests/NexoRuta.ArchitectureTests/NexoRuta.ArchitectureTests.csproj -c Release --no-build --no-restore
dotnet test backend/tests/NexoRuta.IntegrationTests/NexoRuta.IntegrationTests.csproj -c Release --no-build --no-restore --filter "FullyQualifiedName~OperationalMongoIsolationTests|FullyQualifiedName~OperationalProjectionTests|FullyQualifiedName~OperationalConsumerHealthTests|FullyQualifiedName~OperationalBootstrapTests"
python -m unittest discover -s scripts/gcp -p test_vm_deploy.py
python -m unittest discover -s scripts/gcp -p test_delivery.py
git diff --check
git -C backend diff --check
```

Ampliar el filtro con las clases nuevas de este módulo. No ejecutar suites repetidamente sin un cambio/fallo que lo justifique. Si se alteran contratos compartidos o composición global, ejecutar las regresiones afectadas y los gates requeridos del CI integrado. Las rutas de resultados/TRX deben quedar en artefactos locales/CI; nunca incluir credenciales ni bases.

Actualizar `docs/seguimiento-tablero/TRAZABILIDAD.md` y crear `docs/auditorias/opt-05/aceptacion.md` con fuentes, SHAs, decisiones, pruebas, límites y guion reproducible de API. Actualizar OpenAPI y la documentación backend del módulo que quede implementado. Para una PR, seguir `backend/docs/workflow/implementar-cu.md` y la bitácora individual vigente: no inventar una identidad de autor o crear una bitácora nueva por tarea.

**Salida:** implementación revisable con evidencia actual, checklist de la sección siguiente y pendientes operativos identificados. No marcar la card Done por haber escrito este plan o por reutilizar un informe anterior. Actualizar Notion solo dentro de una tarea que autorice ese cambio y con enlace a la aceptación final.

## 5. Criterios de cierre y límites deliberados

- [ ] La proyección usa eventos persistidos del sistema actual y no crea un segundo historial canónico.
- [ ] El almacenamiento, filtros y agregaciones documentales funcionan en MongoDB real con autorización por operador/comercio.
- [ ] La API tipada pagina, filtra, valida límites y comunica retraso/indisponibilidad; OpenAPI documenta semántica y errores.
- [ ] Índices efectivos y retención de 90 días verificados; no se devuelven documentos vencidos antes del barrido TTL.
- [ ] Replay/reentregas no duplican, renuevan TTL ni alteran negocio; fallos entre almacenes son recuperables.
- [ ] No se ejecutan agregaciones analíticas sobre la base transaccional como fallback; solo consultas acotadas de autorización/salud. Se documenta el costo adicional de captura/fronteras.
- [ ] Evidencia nueva distingue tests puros, HTTP con fixtures, infraestructura, rendimiento medido y pruebas remotas pendientes.
- [ ] Configuración local y preparación GCP coherentes; cualquier instalación remota que se declare operativa tiene su propia verificación sobre ambas API.
- [ ] Migraciones, datos, volúmenes, RLS, B1–B5, selector de dirección y recuperación de contraseña preservados.

OPT-05 no requiere agregar pantallas, modificar Mobile, rediseñar el tablero, implementar CU-30 completo, webhooks, autoescalado, exportaciones, Atlas o un servicio independiente. Si luego se solicita UI, leer `frontend/AGENTS.md` y `frontend/DESIGN.md`, reutilizar Razor Pages/Blazor/Bootstrap y componentes existentes, aplicar skeletons cuando correspondan, jerarquía simple, tokens semánticos y accesibilidad. Verificar en navegador escritorio/móvil/teclado y separar esa revisión de compilación, HTTP y automatización.

## 6. Referencias oficiales para las decisiones técnicas

Consultadas durante el análisis; aplicar las APIs disponibles en las versiones fijadas del repositorio, sin copiar ejemplos de otra versión ni actualizar el stack para acomodarlos:

- [MongoDB .NET/C# Driver — MongoClient](https://www.mongodb.com/docs/drivers/csharp/current/connect/mongoclient/): reutilización del cliente y gestión de conexiones. Fundamenta su ciclo singleton.
- [MongoDB — TTL indexes](https://www.mongodb.com/docs/manual/core/index-ttl/): índice de un campo, fecha BSON y borrado asíncrono. Fundamenta mantener además el filtro de expiración.
- [MongoDB — índices y ESR](https://www.mongodb.com/docs/manual/tutorial/equality-sort-range-guideline/): diseñar índices a partir de igualdad, orden y rango; validarlos con explain.
- [MongoDB — skip y orden estable](https://www.mongodb.com/docs/manual/reference/method/cursor.skip/): desempate único y costo de offsets profundos. Fundamenta el orden actual y sus límites, sin prometer snapshot entre páginas.
- [ASP.NET Core — buenas prácticas](https://learn.microsoft.com/en-us/aspnet/core/fundamentals/best-practices?view=aspnetcore-10.0): consultas acotadas, operaciones asíncronas y cuidado de recursos en requests.
- [ASP.NET Core — Options](https://learn.microsoft.com/en-us/aspnet/core/fundamentals/configuration/options?view=aspnetcore-10.0): configuración tipada y validación explícita.
- [.NET — servicios scoped dentro de BackgroundService](https://learn.microsoft.com/en-us/dotnet/core/extensions/scoped-service): scope por trabajo para persistencia SQL del consumidor.

## 7. Evidencia de esta preparación documental

Esta sección describe únicamente lo ejecutado al preparar el plan; no acredita la aceptación futura:

- **Fuentes/Git:** card obtenida por MCP de Notion; PDFs de alcance extraídos y planillas leídas sin macros; código y documentación inspeccionados en los SHAs de la sección 1. Pull fast-forward de los cuatro repos completado, sin necesidad de cambiar ramas ni gitlinks.
- **Compilación:** `dotnet restore backend/NexoRuta.sln --locked-mode --nologo -v minimal` y `dotnet build backend/NexoRuta.sln --no-restore --nologo -v minimal` correctos con SDK 10.0.401, configuración Debug; 0 errores y 3 advertencias (`NU1510`, `xUnit2031`, `EF1003`). El primer intento sin restore encontró assets ausentes/desactualizados; el intento posterior al restore resolvió esos errores sin cambiar código ni locks.
- **HTTP:** no se arrancó ni consultó una API en esta preparación.
- **Automatización:** `dotnet test` sobre UnitTests y ArchitectureTests, con `--no-build --no-restore --nologo`, aprobó respectivamente 347/347 y 4/4, sin omitidas, en Debug. Integración MongoDB/Kafka/PostgreSQL no ejecutada; Docker CLI no está disponible en este entorno. Las suites e informes citados como antecedentes no son resultados nuevos. Las comprobaciones Git muestran `HEAD...origin/develop = 0/0` en los cuatro repositorios; los tres submódulos permanecen sin cambios locales.
- **Revisión visual:** no aplica; el entregable es documental y no modifica interfaces.

El único cambio versionable de esta preparación es este plan. El código del módulo, los servicios persistentes, el despliegue GCP y el estado de la card en Notion permanecen como estaban.

## 8. Resultado de la implementación (2026-11-07)

La sección 7 conserva la evidencia histórica de la preparación documental. La implementación posterior está descrita en [`docs/auditorias/opt-05/aceptacion.md`](../auditorias/opt-05/aceptacion.md); la guía de contratos y operación está en [`backend/docs/operacion/historial-y-analitica.md`](../../backend/docs/operacion/historial-y-analitica.md).

Quedaron implementados los casos de uso/repositorios de Application, los contratos HTTP y controladores tipados, la separación de consultas en Infrastructure, los límites de tiempo Mongo, la validación de idempotencia semántica, la provisión de usuarios/roles sobre volúmenes GCP existentes y la observabilidad del grupo history. El worker conserva su ciclo de inserción, acuse PostgreSQL y commit Kafka. No se agregaron UI, cambios Mobile, migraciones, borrado de datos, cambio de offsets ni cambios de reglas de negocio.

Compilación, pruebas unitarias, arquitectura y scripts de despliegue pasaron según el informe de aceptación. La prueba de integración extendida compila, pero la aceptación HTTP/Mongo/Kafka/PostgreSQL, índices/TTL físicos, `explain` y rendimiento no se ejecutaron porque `docker` no está disponible. `terraform fmt` tampoco pudo ejecutarse porque Terraform no está instalado. No hubo despliegue ni acceso a GCP; el provisionador está preparado, no ejecutado contra un volumen real. La checklist de la sección 5 queda abierta donde exige evidencia integrada u operativa.
