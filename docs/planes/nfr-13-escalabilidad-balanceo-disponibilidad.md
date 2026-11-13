# NFR-13 — Plan de implementación y aceptación para un agente de IA

Fecha de análisis: 12/11/2026. Estado: **plan, sin implementación ni aceptación de NFR-13**. El trabajo de esta revisión es documental. Las consultas de GCP fueron de solo lectura; no se provocaron fallos ni se desplegó una release para elaborar este plan.

## 1. Objetivo, autoridad y alcance

Cerrar [NFR-13 — Escalabilidad, balanceo y disponibilidad](https://app.notion.com/p/40a032f1caff81718c15f6b38911247f), que en Notion tiene prioridad Alta y estado `In progress`. La card, consultada por MCP, indica dos APIs y failover/reconexión controlados, con operación sostenida, jobs únicos y aceptación de GCP pendientes. Su última edición visible fue el 12/11/2026; la descripción de estado corresponde al 09/11/2026. No convertir esa descripción en evidencia actual de todas las condiciones.

Fuentes normativas leídas:

- [Laboratorio .NET 2026](../alcance/Laboratorio__NET_2026.pdf), página PDF 8, página impresa 7, sección 6.13: al menos dos instancias simultáneas de API, balanceador, continuidad ante caída de una, API sin estado en memoria, `/health`, `/ready`, `/live`, apagado controlado, Data Protection compartida cuando corresponda y tareas programadas sin duplicación.
- [Casos de Uso — Responsables](../alcance/Calcs/Casos%20de%20Uso%20-%20Responsables.xlsm), hoja `No funcionales`, fila identificada por `NFR-13`, sección `6.13`, M01 con dependencias M01/M05/M06. Se leyó el archivo sin ejecutar macros.
- Secciones 6.8 y 6.14 del laboratorio/card: outbox, consumidores idempotentes y despliegue remoto real con HTTPS/IaC/CI. Son dependencias de la aceptación, no autorización para rehacer esos módulos.
- [Reglas del repositorio](../../AGENTS.md), [ADR de aislamiento RLS](../alcance/ADR-MT-001-PostgreSQL-RLS.md), [plan de dos VMs](../../infra/gcp/plan-doble-vm-monitorizacion.md) y [validación previa](../seguimiento-tablero/VALIDACION.md). Los dos últimos mezclan resultados históricos y pendientes: contrastarlos con código y ejecución, no copiarlos como estado vigente.

La nota del laboratorio sobre exoneración para equipos de tres integrantes no se usa para omitir NFR-13: existe una card explícita y el usuario pidió planificarla. No se presupone un tamaño de equipo para reducir alcance.

**Resultado exigido:** una release identificada sirve peticiones autenticadas y operaciones persistentes mediante dos APIs reales; al perder una API, la otra acepta peticiones nuevas dentro de un límite medido; la identidad, las cuotas y los datos no dependen de memoria del nodo perdido; el apagado ordenado tiene presupuesto verificable; la tarea periódica real tiene coordinación distribuida y efectos únicos demostrados.

**Fuera de alcance:** Kubernetes, autoscaling, tercera VM, migración de proveedor, SQL regional HA, clústeres de brokers/Mongo, SLA 24x7, continuidad entre regiones, despliegue sin corte, rediseño de portales y creación de un cierre contable diario nuevo. No se necesita nada de eso para demostrar las condiciones de 6.13. Si una brecha exige ampliar alcance, documentar el motivo y la alternativa mínima antes de implementarla.

## 2. Base reproducible y límites del diagnóstico

| Fuente | Identidad observada |
| --- | --- |
| Raíz local `develop` | `eefe3886c3ebc34147283f8842b1c321c36b39e4` |
| Backend, gitlink y checkout | `db38a2ac31d69e2a70411c283238e28400636d77` |
| Frontend, gitlink de raíz | `723d02ba6cb5d0196a5181e4f4f076c115d7fe6d` |
| Frontend, checkout efectivamente inspeccionado | `162bf08ec9ad1428fa56dc81b5ce289ac1208a61` |
| Mobile, gitlink y checkout | `329dd3454704c0f45b615d609f469b7fd4b2dd5f` |
| Release aplicada a ambas VMs | `release-cbb8e8797547441abb3930bb00933182` |
| Imagen API de ambas VMs | `api@sha256:24fc078a69f5eb1a9cc171e6706f4871a3123834b6051ec1a442c33d91e0cc7f` |

La diferencia del frontend existía antes del análisis. Hay además evidencias locales AP-04 sin seguimiento. **No incorporarlas, descartarlas ni actualizar el gitlink implícitamente.** El agente debe elegir deliberadamente el conjunto de fuentes para implementar y repetir la inspección de frontend sobre ese conjunto; no hacer `submodule update --remote` ni sustituir commits para obtener un build verde. El manifiesto histórico `scripts/cloud/checkpoint.json` tampoco elige las fuentes de esta tarea.

No se inspeccionaron secretos ni datos de negocio de Cloud SQL. No se ejecutaron pruebas de concurrencia, suites .NET, carga, failover ni revisión visual nueva para este análisis. Una lectura de fuentes de tests demuestra cobertura prevista, no que hoy pasen. Las pruebas de la corrección de Grafana de la sesión anterior no cierran NFR-13.

## 3. Estado actual y brechas concretas

| Área | Evidencia revisada | Conclusión y acción |
| --- | --- | --- |
| Dos APIs reales | GCP: `nexoruta-demo`, zona `southamerica-west1-a`, y `nexoruta-demo-b`, zona `southamerica-west1-b`; ambas RUNNING, `n4-custom-6-16384`; mismo digest API; health Docker sano y cero reinicios en la consulta | Ya existe. Conservar; falta demostrar reparto y continuidad de negocio bajo la release candidata |
| Balanceador | `infra/gcp/demo/load-balancer.tf`: HTTPS global `EXTERNAL_MANAGED`, grupos no administrados A/B; `get-health nexoruta-demo-api` devolvió ambos `HEALTHY` en puerto 18080 | Ya existe. No crear otro LB ni MIG por rutina |
| Health checks | API publica `/health/ready` y `/health/live`; ready usa `PostgreSqlHealthCheck`; ambos dieron 200 en A, ready dio 200 en B | Hay discrepancia con las tres rutas literales del laboratorio; falta readiness durante drenaje y timeout explícito verificado |
| Afinidad | API sin afinidad; Commerce/Tracking con cookie del LB; Backoffice sin afinidad en el manifiesto aunque tiene SignalR | Verificar qué conexiones/circuitos se usan realmente. Data Protection no migra circuitos Blazor ni IDs de negociación SignalR |
| Estado compartido | PostgreSQL, claves/certificados compartidos, JWT configurado por release; `PostgresRateLimiter` usa una función SQL | Conservar. Añadir aceptación HTTP cruzada y auditoría de estado mutable por nodo; no eliminar cachés puramente reconstructibles |
| Data Protection | Backend y frontend tienen proveedores PostgreSQL por anillo; claves cifradas con certificado; tests `HostingStateTests` | Probar cookies y antiforgery reales entre dos procesos, aislamiento de anillos y reinicio; un `Protect/Unprotect` aislado no cubre todo |
| Apagado | Compose usa `stop_grace_period: 30s` para apps/workers; entrega retira ambos nodos, espera 35 s y migra una vez | Hay mecanismos. Falta demostrar SIGTERM, trabajo en vuelo y márgenes entre host, Docker y LB; no declarar cero corte en un update |
| Failover controlado previo | `OperationalSignalRTests.TwoRealKestrelApisShareTenantScopedPhotographsAndReconnectWithoutRewinding` levanta dos Kestrel y proxy WebSocket; usa `SkipNegotiation=true` y reinicia explícitamente la conexión | Reutilizar. No acredita automáticamente el cliente real, negociación estándar, autoreconexión del navegador ni GCP |
| Outbox y consumidores | Reservas SQL, confirmación condicionada al propietario, consumidores y proyecciones con deduplicación; pruebas Rabbit/Kafka/Push existentes | Es base para mensajes al menos una vez. No equivale a exclusión de un job periódico |
| Job periódico real | `ProofValidationDeadlineWorker` cada 30 s, lotes de 100; `Program.cs` lo registra en RabbitMq, Kafka y Push, en ambos nodos | Hay hasta seis competidores para el mismo barrido; la garantía debe residir en PostgreSQL, no en que usualmente gane uno |
| Riesgo de doble efecto | Última redefinición observada en `ParcelResultsAndHomePickups.Sql.cs`: selecciona candidatos antes de bloquear; luego incrementa versión del envío parcial aunque otro competidor ya haya vencido sus bultos | Hipótesis concreta de carrera, **a reproducir**. No afirmar fallo observado en producción. Probar versión, historia y outbox, no solamente estado final |
| Jobs diarios | No se identificó en la inspección un scheduler diario de cierre contable; reportes/liquidaciones actuales no son prueba de ese scheduler | No inventar AP-09 ni una regla económica diaria para cerrar NFR-13. Demostrar la garantía con el barrido real e inventariar cualquier tarea adicional encontrada |
| Dependencias centrales | Brokers, Mongo, SMTP de demo y Prometheus/Loki/Tempo en A; Redis de caché configurado en B; SQL separado pero ZONAL | Caída de una API, de una VM y de una zona son fallos distintos. La pérdida de A degrada funciones asíncronas y observabilidad; no prometer HA integral |
| SQL real | `POSTGRES_18`, RUNNABLE, `availabilityType=ZONAL`; backups automáticos y PITR deshabilitados en la consulta | NFR-13 no exige convertirlo a regional; el ensayo con datos persistentes exige un respaldo deliberado y recuperable antes de intervenir |
| Redis/IaC | Existe Memorystore BASIC READY y recurso en `database.tf`, mientras Compose integra Redis B y hay plan NFR-07 de retiro | Documentar coexistencia y comprobar endpoint efectivo sin imprimir credenciales. No borrar Memorystore ni terminar NFR-07 como efecto lateral |
| Observabilidad | Incidente reciente: Prometheus OOM con límite 2 GiB; corrección raíz a 4 GiB y colas OTLP antiguas conservadas en respaldo | Exigir telemetría fresca A/B antes de medir continuidad. Dashboard accesible y datos históricos no bastan |

## 4. Decisiones técnicas del plan

### 4.1. Contrato de salud único

Adoptar las rutas literales `/health`, `/ready`, `/live` para API y un contrato coherente para portales. Actualizar a la vez productores y consumidores propios. Eliminar las rutas antiguas activas `/health/ready` y `/health/live`, sin redirects ni aliases de compatibilidad. No reescribir evidencia histórica para simular que esas rutas siempre existieron.

| Ruta | Propósito | Dependencias y respuesta |
| --- | --- | --- |
| `/live` | El proceso atiende y el pipeline mínimo funciona | 200 sin consultar SQL, Redis, brokers, Geoapify ni Mapbox |
| `/ready` | Admitir peticiones de negocio nuevas | 200 cuando inicialización completa, no drenando y PostgreSQL crítico disponible; 503 durante arranque, drenaje o fallo SQL; prueba SQL con cancelación y timeout acotado |
| `/health` | Resumen operativo público mínimo | Estado esencial y release/nodo si están habilitados para diagnóstico; 200 apto, 503 no apto; no revelar cadenas, consultas, excepciones, certificados, inventario interno ni datos de usuarios |

Los portales no deben hacer una llamada externa sin límite por cada probe. Decidir por host qué dependencia es crítica: al menos configuración/claves inicializadas y ciclo de vida. Documentar la semántica sin dar por sano un portal solo porque no registró checks. Las señales de dependencias opcionales se publican separadas; caída de caché no retira una API capaz de servir desde SQL. Los probes no consumen cuotas de login ni abren transacciones de negocio innecesarias.

Usar `IHostApplicationLifetime`, un estado local de ciclo de vida y `HealthCheckOptions`/checks existentes. Este estado local de salud es legítimo: no es una sesión ni información de negocio. Añadir timeout inicial SQL de 2 s, inferior al timeout 5 s del LB; medir y ajustar sin retries acumulativos. Readiness debe respetar cancelación y evitar trabajo costoso.

Para identificar el backend en ensayos, preferir correlación + logs actuales con `node` y `RELEASE_ID`. Si no permiten atribuir cada respuesta, añadir cabecera diagnóstica acotada y configurable con nodo/release, sin IPs ni secretos; no crear un endpoint de administración público para forzar tráfico. No activar request logs completos del LB: actualmente están apagados para proteger tokens de seguimiento en URL.

### 4.2. Estado, autenticación y conexiones

Conservar PostgreSQL como autoridad para identidad, sesiones revocables, RLS, cuotas e idempotencia. JWT, certificados y anillos deben corresponder a la misma release/configuración en ambos nodos; no regenerarlos al reiniciar. Conservar separación de anillos API/Admin/Backoffice/Commerce/Tracking. La recuperación mediante certificados anteriores es protección de datos, no un alias de versiones que deba borrarse.

Auditar `static`, singletons, memoria caché, archivos locales, cuotas, almacenamiento de tokens y uploads. Clasificar cada hallazgo como dato durable, estado por conexión o caché reconstructible. Corregir solamente los que impidan que una petición equivalente llegue al otro nodo con el mismo resultado o seguridad. No convertir un caché local reconstructible en motivo para rehacer arquitectura.

Revisar separadamente: cookie compartida, antiforgery, conexión SignalR, negociación y circuito Blazor. Una cookie válida no conserva un circuito de servidor muerto. El cliente debe reconectar o recargar de forma comprensible y recuperar su estado confirmado; no prometer continuidad de un formulario aún no guardado. Un cliente que negocia y luego conecta a otro backend puede necesitar afinidad; el test con WebSocket directo no cubre ese escenario. Conservar API sin afinidad salvo necesidad demostrada del transporte; preferir WebSockets y el comportamiento del cliente existente antes de añadir backplane o servicio nuevo. Evaluar afinidad de Backoffice solamente si utiliza circuitos/negociación que la requieren y verificar el camino real.

### 4.3. Apagado controlado frente a caída abrupta

Hay dos contratos diferentes que deben probarse:

1. **Mantenimiento/SIGTERM:** retirar admisión, permitir terminar trabajo acotado, cerrar consumidores y salir antes del kill de Docker.
2. **Crash/SIGKILL:** la petición en vuelo puede perder respuesta; al reconectar no se duplican efectos confirmados y una reserva no completada es recuperable.

Presupuesto inicial propuesto: `HostOptions.ShutdownTimeout` 20 s, Docker 30 s, drenaje LB 30 s y espera del orquestador de al menos 35 s, ya existente. No son valores aceptados sin ensayo. Si una operación legítima excede 20 s, ajustar todos los presupuestos relacionados y la prueba; nunca subir un timeout aislado y suponer resuelto el problema.

El drenaje por retiro del grupo ocurre antes del SIGTERM; el callback de parada cambia `/ready` pero no sustituye la propagación del LB. El LB tiene además requests largos y conexiones persistentes: documentar la reconexión, no esperar cuatro horas a que termine un circuito. Workers dejan de reservar mensajes nuevos, preservan reservas inciertas, solo confirman efectos realmente persistidos y cierran conexiones dentro del presupuesto. Prohibido marcar publicado en un `finally` o confirmar Kafka/Rabbit antes del efecto durable.

Conservar el corte coordinado de `delivery.py`: ambos nodos fuera, detener aplicaciones, migrar una vez, aplicar nueva release B/A y readmitir sanos. No ejecutar la release vieja contra un esquema nuevo, ni introducir blue/green o rollback binario para lograr despliegue sin interrupción.

### 4.4. Exclusión y efectos únicos de tareas periódicas

No añadir Hangfire/Quartz/Redis-locks para un barrido SQL de 100 elementos. Reutilizar worker, PostgreSQL y las transacciones/roles del sistema. Inventariar primero barridos de vencimientos, reconciliación de gestión, heartbeats y limpiezas. No confundir consumo por partición o reconciliación idempotente con una tarea que necesita ejecutar un único período global.

Para `ProofValidationDeadlineWorker`, la unidad de aceptación es **un solo barrido admitido simultáneamente y un solo efecto durable por vencimiento**, con recuperación del competidor si el propietario falla. La propuesta mínima es:

1. Adquirir `pg_try_advisory_xact_lock` con una clave estable y exclusiva para este barrido **dentro de la misma transacción SQL que aplica sus efectos**. Nunca `string.GetHashCode()`, mutex de proceso, archivo local, lock de sesión devuelto al pool ni un candado de Redis con TTL sin fencing.
2. Si no se obtiene, devolver resultado explícito `Contended` sin recorrer envíos. Distinguirlo de `Completed` con cero cambios. Puede cambiarse el contrato interno de la función y su único consumidor juntos; no conservar firmas antiguas para compatibilidad.
3. Para evitar que cada réplica ejecute sucesivamente el mismo tick, mantener una fila técnica de última ejecución exitosa de este job, actualizada en la misma transacción. Usar el reloj de PostgreSQL y un intervalo mínimo de 30 s para los barridos ordinarios; los competidores devuelven `NotDue`. La fila no es un historial ilimitado ni una plataforma de scheduling.
4. Preservar el drenaje inmediato de lotes completos: la fila registra `MoreWork` y permite el siguiente lote sin esperar 30 s, con un solo propietario simultáneo. Si el propietario muere, otro continúa desde los datos pendientes. No limitar el sistema accidentalmente a 100 vencimientos cada 30 s cuando hoy drena lotes completos.
5. Si el tick falla o la conexión cae antes del commit, los efectos y el avance de la fila se revierten juntos. No dejar un `Running` perpetuo. El lock transaccional se libera automáticamente al terminar; no implementar limpieza manual del candado ni prolongar una transacción mientras duerme el worker.
6. Después de bloquear cada envío, volver a evaluar cuáles bultos siguen realmente pendientes y vencidos. Incrementar la versión del envío y generar historia/outbox solo cuando cambie un hecho. Un competidor retrasado que ya no tiene cambios devuelve cero efectos, sin alterar la versión ni crear eventos vacíos.
7. Distinguir el reloj del corte funcional (`p_now`, hoy testeable con `TimeProvider`) del reloj técnico de admisión PostgreSQL. Pruebas con reloj funcional adelantado no deben permitir que un runtime falsifique el reloj del coordinador. Mantener contratos y límites explícitos.
8. Conservar las validaciones de `p_batch_size`, RLS forzado, `search_path=pg_catalog`, propietario definer restringido y `EXECUTE` solo para worker. La tabla técnica puede vivir en un esquema interno de jobs con propietario limitado; API y portales no leen ni escriben esa coordinación. Agregar únicamente permisos mínimos y pruebas de aislamiento.

No es necesario quitar competidores de Kafka/Push para obtener la garantía: varios procesos pueden intentar adquirir, solo uno entra. Si luego se decide reducir invocaciones para ahorrar consultas, eso no sustituye el lock ni la aceptación con dos réplicas. No introducir un scheduler de un solo nodo como solución a disponibilidad.

Para procesos con efectos externos, mantener outbox y deduplicación por identidad de evento. Un commit SQL no asegura entrega exactamente una vez en SMTP/FCM/webhooks. No extender la promesa de NFR-13 a esos proveedores. Si se descubre un job real por día/tenant, definir su clave de período, zona horaria y recibo durable único junto a su efecto; no usar esta fila de último tick como única defensa de un cierre económico. La existencia de ese caso debe demostrarse antes de implementarlo.

Contrato propuesto de coordinación, a concretar en P3 sin convertirlo en un framework:

| Elemento | Propuesta y restricción |
| --- | --- |
| Fila técnica | Clave de job fija, `LastCompletedAtUtc timestamptz`, `NextEligibleAtUtc timestamptz`, `MoreWork boolean`; una fila para el barrido existente, sin payloads de negocio |
| Clave de exclusión | Namespace estable del producto + nombre de job, convertido de forma determinista en PostgreSQL; documentar su valor/derivación y evitar reutilizar el lock de despliegue o migración |
| Resultado del lote | Estado `Completed`, `Contended` o `NotDue`, cantidad afectada y `MoreWork`; errores SQL se propagan, no se convierten en estos estados |
| Cálculo de MoreWork | Un lote completo permite volver a comprobar inmediatamente; una pasada adicional vacía es aceptable y no crea versiones/eventos |
| Transacción | Admisión, fila técnica, cambios funcionales y captura de eventos confirmados juntos; no hacer HTTP, esperar brokers ni dormir con ese lock |
| Recuperación | Antes del commit no queda avance; después del commit queda la admisión registrada y los hechos no se repiten; un lote completo mantiene continuidad para otro competidor |
| Esquema/permisos | Tabla sin acceso de API/portales; función con `EXECUTE` restringido al worker y propietario mínimo; prueba negativa por cada rol relevante |

La coordinación técnica usa un intervalo global porque el barrido actual cruza tenants mediante una función restringida. No reemplazarlo por una conexión superusuario o un contexto de tenant tomado del request. Las modificaciones funcionales siguen acotadas al envío/bulto y a los contextos RLS existentes.

## 5. Paquetes de trabajo y orden de ejecución

Cada paquete debe terminar con cambios revisables, verificaciones y evidencia. Avanzar secuencialmente por dependencias; este documento no exige ni autoriza delegar a subagentes. Los nombres de archivos nuevos siguientes son propuestas, no componentes ya existentes.

### P0 — Fijar fuentes y reproducir el estado (sin mutaciones remotas)

**Entrada:** lectura de este plan, card, AGENTS y continuidad Cloud.

1. Registrar rama, HEAD, gitlinks y estado de trabajo de los cuatro repositorios. Aislar el trabajo si fuera necesario, sin reset ni stash global automático.
2. Elegir el frontend a partir del conjunto solicitado y explicar la divergencia indicada en sección 2. Leer sus instrucciones de diseño antes de revisar UI.
3. Releer las funciones SQL efectivas buscando todas sus redefiniciones y su orden de migración. No corregir solo una migración vieja ignorando la última definición efectiva.
4. Crear `docs/auditorias/nfr-13/diagnostico.md` con inventario de estado de negocio/local, servicios, health, jobs y pruebas existentes; separar observado, inferido y pendiente.
5. Reproducir las pruebas focalizadas existentes como línea base en base/infra propias. Registrar fallos previos sin relajar pruebas ni tratarlos como autorización para otras etapas.
6. Inventariar los consumidores de rutas de salud en raíz, backend y frontend: Compose local/GCP, Dockerfiles, Caddy, OTel/monitor, scripts de fixtures, `vm_deploy.py`, `monitor_agent.py`, `verify_load_runtime.py`, tests y workflows. El plan inicial encontró decenas de referencias; una sustitución en `Program.cs` es insuficiente.

**Salida:** manifiesto de fuentes exactas y matriz actualizada. Si no hay runtime Cloud utilizable, se puede continuar código/estático y declarar pendientes de ejecución; no usar SQL del usuario como reemplazo.

### P1 — Pruebas que revelan las brechas

**Depende de:** P0. **Propósito:** que los tests relevantes fallen contra el comportamiento incompleto, antes de modificarlo.

- Salud: rutas literales, SQL ausente con liveness vivo, timeout y estado drenando; pruebas con Kestrel para ciclo de vida real, además de TestServer para contrato.
- Jobs: extender `OperacionesRepartoHttpTests.PlazoPrueba.cs` o crear `PeriodicJobConcurrencyTests.cs`. Usar barreras/locks SQL para que dos conexiones hayan seleccionado el mismo envío antes de aplicar cambios. Evitar un `Task.WhenAll` sin control que casualmente serialice y nunca reproduzca la carrera.
- Caso obligatorio de carrera: envío `EntregadoParcialmente`, un bulto pendiente vencido y otro con resultado independiente. A/B compiten y se comprueban versiones de envío y bultos, cantidad de hechos de vencimiento y eventos outbox. El estado final igual no basta.
- Apagado: proceso real con una petición acotada en vuelo y un mensaje reservado. Validar persistencia y respuesta; el cierre de un WebApplicationFactory por sí solo no prueba SIGTERM de Docker.

**Salida:** reproducción documentada, identificadores de tests y motivo de fallo. Si el riesgo de carrera no se reproduce, registrar por qué y ajustar el diagnóstico; no fabricar un defecto para justificar una abstracción nueva.

### P2 — Salud y estado compartido

**Depende de:** P1 para salud; P0 para auditoría de estado.

Archivos principales: `backend/src/NexoRuta.Api/Program.cs`, `Core/Health/PostgreSqlHealthCheck.cs`, configuración de hosting; `frontend/src/NexoRuta.Hosting/` y Program de los cuatro portales; consumidores identificados en P0.

1. Implementar contrato de sección 4.1 con estado de arranque/parada y timeouts; `AllowAnonymous` explícito donde exista fallback de autorización.
2. Migrar consumidores a `/ready` y `/live`; usar `/ready` en LB, Compose y salud directa. No modificar `/api/health` propio de Grafana ni `/healthz` de proxy/Mailpit por una sustitución general.
3. Revisar exclusión de probes en logging/telemetría para que no oculten errores ni inflen métricas de negocio. No registrar secretos ni cuerpos.
4. Mantener validación de proxies confiables, scheme HTTPS e IP de cliente para cuotas. No aceptar `X-Forwarded-For` arbitrario de Internet.
5. Corregir únicamente el estado por nodo que la auditoría demuestre incompatible con failover. Verificar cuotas y revocación con clientes alternando A/B.
6. Compilar y actualizar contrato OpenAPI solo si afecta contratos de clientes; probes no deben provocar regeneración de toda la API funcional.

**Salida:** matriz de salud verde local, ambos hosts comparten identidad/cuotas, consumidores sincronizados y ausencia de aliases activos antiguos.

### P3 — Coordinación del barrido y carrera de vencimientos

**Depende de:** P1. Puede desarrollarse antes de P2, pero debe integrarse con el mismo conjunto final.

1. Añadir una **migración nueva**, posterior a las existentes, que cree la coordinación mínima y reemplace la función efectiva. No editar/eliminar migraciones históricas para borrar el fallo.
2. Implementar lock/admisión/MoreWork/efectos atómicos de sección 4.4. Mantener lote 100 e intervalo 30 s como punto inicial, sin introducir un cron configurable por tenant.
3. Cambiar consumidor y contrato SQL juntos si el resultado deja de ser entero; centralizar nombres de función y actualizar `RlsSqlFunctionContract`, tests de roles y fixtures donde corresponda. Quitar la firma anterior del esquema resultante si cambió, preservando la cadena de migraciones.
4. Resolver no-op de envío parcial después de la espera de locks. Validar asimismo competencia entre el barrido y la recepción de prueba válida, entrega parcial y otra transición operativa.
5. Añadir métricas acotadas: intentos por resultado (`completed`, `contended`, `not_due`, `failed`), duración, elementos afectados y última ejecución exitosa. Etiquetas job/nodo/transporte; nunca IDs de envío, tenant, corrida o lease de cardinalidad ilimitada.
6. No esconder indisponibilidad SQL como cero vencimientos. Cancelación por apagado no es éxito ni error de negocio.

**Salida:** un propietario por barrido, sin doble efecto; rollback recuperable; lotes completos no quedan artificialmente retrasados; API no adquiere permisos técnicos de job.

### P4 — Apagado y reconexión reales

**Depende de:** P2 y P3.

1. Configurar presupuesto explícito del host y revisar Dispose/StopAsync de publishers/consumers. Asegurar que los comandos de parada existentes esperan salida y registran timeout/fallo.
2. Mantener `stop_grace_period` coherente en Compose local/GCP; verificar que la imagen ejecuta .NET como PID que recibe SIGTERM y no un shell que lo absorbe.
3. Crear un harness reutilizable con dos API Kestrel/procesos, PostgreSQL restringido y proxy de salud. Extender el fixture existente en lugar de duplicar su lógica de autenticación/RLS.
4. Probar cookie/antiforgery cruzados en dos hosts del mismo portal. Cookies de Admin no deben funcionar en Commerce ni viceversa.
5. Probar cliente real de SignalR y navegador de portales: negociación si aplica, conexión, pérdida, reconexión/recarga y relectura de estado confirmado. No cambiarlo a WebSocket directo únicamente para que el test pase si el cliente de producto utiliza negociación.
6. Si cambia UI de reconexión, aplicar DESIGN.md: conservar contenido cuando siga válido, estado de error/reintento accesible, foco y teclado, sin spinner indefinido. Limitarse al flujo afectado.
7. Ensayar SIGTERM y crash por separado. Reenviar comandos solamente con la identidad idempotente original, si el caso de uso la posee; un timeout no autoriza crear una identidad nueva ni reintentar una mutación arbitraria.

**Salida:** respuesta o resultado durable verificable para trabajo en vuelo, reservas recuperables y experiencia de reconexión documentada. Ninguna promesa de persistir memoria de circuitos muertos.

### P5 — Entrega, IaC, sesiones y evidencia automatizada

**Depende de:** P2/P3/P4.

Archivos: `infra/gcp/demo/load-balancer.tf`, `scripts/gcp/vm_deploy.py`, `delivery.py`, `demo_session.py`, `monitor_agent.py`, `control_lock.py`, tests correspondientes, configuración guard y `.github/workflows/ci.yml`.

1. Actualizar probes del LB y todos los verificadores; mantener puertos privados, grupos A/B, TLS y restricciones de red actuales.
2. Preservar migración única y control lock de operación; un update no amplía la sesión ni arranca por su cuenta un nodo apagado. Un nodo fallido queda fuera del grupo hasta recuperarse sano.
3. Verificar por tests de scripts la secuencia retirar → drenaje → parar → migrar una vez → aplicar → salud local → admitir → salud LB. Si falla migración, ambos siguen fuera; si falla admisión, retirar ese nodo.
4. Revisar guard con A caída, B caída, sesión vencida y cancelación del runner. No apagar SQL/nodo sano antes del vencimiento por una caída parcial; no ampliar las cuatro horas al recuperar un nodo.
5. Agregar una herramienta de ensayo `scripts/gcp/verify_nfr13.py` **propuesta**, con modo solo lectura predeterminado y subcomando explícito para fallos; no ejecutar operaciones de parada desde `--help`, importación, `check` ni tests unitarios. Reusar clientes/lease existentes. No crear otra CLI para start/stop de la demo.
6. El modo de fallo requiere proyecto, release esperada, inventario exacto, sesión activa y reserva operativa; registrar qué nodo se altera y rechazar prod/proyectos no esperados. Asegurar restauración en `finally`, más instrucciones y comando manual de recuperación si desaparece el proceso. No confundir `finally` con protección ante pérdida completa del runner.
7. Si un lock de ensayo debe convivir con el guard, diseñar protocolo explícito: nunca bloquear el apagado por vencimiento, mantener lease, admitir cancelación y no adquirir el mismo mutex dos veces anidadas. Preferir el mecanismo común actual y no editar grupos/VMs por dos actores a la vez.
8. Integrar suites nuevas al inventario de shards .NET y al CI raíz/companion; ninguna prueba crítica de NFR-13 debe quedar silenciosamente fuera por filtro, categoría o flag opt-in. Publicar TRX y resumen sanitizado por escenario, con expiración de artefactos declarada.

**Salida:** estático y CI verdes para el candidato exacto; plan IaC revisable sin reemplazar discos/SQL ni cambiar cuota/topología. No ejecutar apply para regenerar un plan cuando solo se necesita validate.

### P6 — Aceptación local integral

**Depende de:** P5. Ejecutar la matriz de sección 6 en infraestructura efímera propia.

1. Dos procesos de API, dos del portal que se valida y al menos dos competidores del job; usar roles runtime restringidos y las migraciones reales. Para escenarios Rabbit/Kafka, usar brokers propios y test doubles de SMTP/FCM/webhooks externos.
2. Establecer identidad sintética, dos tenants y un caso de uso persistente cuyo `ComandoId` ya exista. Verificar la misma fila/versiones desde ambos nodos, incluida respuesta a duplicados.
3. Generar tráfico pequeño y controlado, forzar pérdida API A, recuperar, luego API B. Verificar avance de negocio en el superviviente, no solamente GET de salud.
4. Ejecutar fallos de SQL/broker/caché por separado y confirmar la semántica prevista. Las llamadas Geoapify/Mapbox se bloquean o se responden de manera controlada; `permanent=false` permanece.
5. Repetir los casos de carrera deterministas varias veces solo para demostrar ausencia del fallo bajo los puntos de sincronización; no compensar flaky tests con reintentos automáticos que oculten errores.

**Salida:** pruebas sin fallidas/omitidas en el conjunto requerido; evidencia de integridad antes/después y recuperación, con causas de cualquier limitación.

### P7 — Aceptación en GCP y operación sostenida

**Depende de:** CI y aceptación local, release publicada y autorización para la ventana de intervención. El pedido actual de plan no ejecuta esta etapa.

Preparación:

1. Seleccionar una release publicada con SHAs y digests exactos; registrar configuración efectiva y estado de A/B, SQL, guard, vencimiento, backends y telemetría. Si otra sesión actualizó el entorno, no reutilizar los valores históricos de sección 2.
2. Obtener respaldo SQL y evidencia de recuperación ensayada en entorno separado, preservar certificados/anillos y discos. Nunca descargar secretos a un artefacto público ni usar `down -v`, `FLUSHALL`, reset de offsets o reinstalación Mobile como recuperación.
3. Verificar tiempo restante de sesión mayor que ensayo + recuperación + margen. Propuesta: reservar 90 min dentro de las cuatro horas. Si no alcanza, no iniciar el fallo; no extender el vencimiento por fuera de la operación autorizada.
4. Confirmar `/ready`/`/live`/`/health` públicos, backends A/B sanos, misma release y muestras recientes A/B. Si Prometheus está recuperando, el collector está atrasado o faltan series, corregir/posponer la medición; no llenar huecos con cero.
5. Crear datos sintéticos identificados y un plan de recuperación que no dependa de A. Usar consultas agregadas y actores sintéticos; no probar comandos de negocio sobre envíos reales.

Ejecución propuesta dentro de una sesión:

- **15 min de base**, cinco usuarios sintéticos como máximo, lecturas autenticadas + operaciones idempotentes conocidas. Usar infraestructura de carga existente si encaja; mantener tasas pequeñas y sin servicios externos reales. Verificar al menos una petición atribuida a cada backend, sin exigir reparto 50/50.
- **Pérdida del contenedor API A**, sin retirar previamente del grupo: medir desde que deja de atender hasta recuperación de peticiones nuevas; restaurar y esperar ambos sanos. Repetir con API B. Este es el núcleo del requisito.
- **Apagado ordenado** de una API durante una operación lenta acotada y del worker con reserva en vuelo; medir salida y contrastar datos. No usar un endpoint lento público de producción; preparar el caso en fixture o mediante una operación sintética legítima controlada.
- **Caída de VM B**, una vez recuperada la base: A conserva SQL y brokers, caché puede degradar; restaurar dentro del plazo existente. Confirmar fallback de caché y posterior recuperación.
- **Caída de VM A**, en la ventana autorizada y después de restaurar B: B debe continuar las operaciones canónicas que dependan de SQL y no de servicios únicos en A; registrar qué funciones asíncronas/logs quedan atrasadas. No declarar caído todo NFR-13 por una función documental dependiente de Mongo, ni declarar disponible lo que no se comprobó.
- **30 min de estabilidad posteriores**, ambos nodos sanos, sin reinicios/OOM ni duplicados; reconciliar outbox y job. Los 15+30 min son un mínimo propuesto para esta aceptación, no prueba de estabilidad diaria/mensual. Ajustar duración antes de empezar para respetar la sesión.

Umbrales propuestos para el ensayo, que deben quedar en su manifiesto antes de ejecutarlo:

| Señal | Condición |
| --- | --- |
| Recuperación tras caída de una API | Nuevas peticiones correctas mediante LB en ≤60 s; al menos 10 respuestas consecutivas correctas y observación estable posterior |
| Integridad | Cero efectos de negocio duplicados, cero lecturas cruzadas entre tenants, cero pérdida de filas ya confirmadas |
| Exposición | Cero secretos/tokens/cuerpos sensibles en reportes, logs ni capturas |
| Apagado ordenado | Finaliza antes de 30 s de Docker, con presupuesto del host y resultado de trabajo en vuelo verificado |
| Estado final | A/B en release objetivo, HEALTHY, sesión y guard conservados, reservas recuperables y job activo |
| Parada del ensayo | Nuevo OOM/reinicio inesperado, error de aislamiento/integridad, pérdida de lease, poco tiempo de recuperación o >5% de fallos sostenidos 60 s fuera del intervalo de fallo previsto |

La ventana intencional de failover no se elimina de los resultados: se reportan todos sus fallos, tiempo y peticiones en vuelo por separado. No computarla como tráfico base saludable ni usar el umbral de aborto para cancelar automáticamente el propio escenario esperado. Si excede 60 s, el escenario falla aunque el servicio luego vuelva. Medir p95/p99, pero no inventar un objetivo del laboratorio que no existe ni confundir rendimiento de cinco usuarios con capacidad máxima.

Durante caída de A, usar un observador externo al nodo: timestamps monotónicos del harness, respuestas del LB, `get-health` y Cloud Monitoring cuando esté disponible. Grafana depende de A y no puede ser el único observador de su caída. No abrir públicamente Prometheus, Docker, SQL o brokers para facilitar el ensayo.

**Salida:** reporte GCP reproducible con línea temporal, requests completos contabilizados, evidencias por nodo y recuperación. Un fallo sin restaurar el entorno deja el paquete incompleto aunque el diagnóstico sea correcto.

### P8 — Cierre y entrega

**Depende de:** P6/P7 aprobados o limitaciones explícitas que impidan cierre.

1. Completar matriz requisito → implementación → test → evidencia → estado. No marcar Done con observaciones estáticas solamente.
2. Redactar `docs/auditorias/nfr-13/aceptacion.md` y runbook de operación/recuperación, enlazando resultados y límites de topología. Corregir referencias vigentes del plan histórico sin borrar su contexto fechado.
3. Identificar companions publicados y actualizar gitlinks deliberadamente. No incorporar el frontend previo ajeno ni evidencias AP-04 al commit de esta tarea.
4. Publicar fuentes, CI y artefactos según autorización de esa ejecución. Este documento no incluye permiso tácito para cambiar audiencias, secretos, presupuesto o la topología.
5. En Notion, conservar la descripción histórica y agregar el enlace de aceptación + resultado observado si se pide actualizar la card. `Done` solo con todos los criterios obligatorios acreditados; si falta GCP, mantener estado pendiente y nombrar el gate exacto.

## 6. Matriz de pruebas obligatorias

| ID | Escenario | Aserción principal | Nivel |
| --- | --- | --- | --- |
| H01 | Tres rutas nuevas sin credenciales | Contrato y estados correctos, sin detalles privados | HTTP |
| H02 | SQL desconectado | live 200; ready/health 503 en tiempo acotado | Integración |
| H03 | Redis/broker/Grafana caído | API canónica no se retira por dependencia opcional; señal degradada veraz | Integración |
| H04 | Arranque y parada | Ready no admite antes de inicializar ni después de comenzar drenaje | Proceso real |
| H05 | Consumidores de health | LB/Compose/monitor/verificador/fixtures usan contrato nuevo; no aliases activos | Estático + HTTP |
| S01 | Login A, petición B | Identidad, permisos y tenant iguales | HTTP real |
| S02 | Revocación/tenant | Revocado se rechaza en B; tenant ajeno nunca visible | HTTP + RLS |
| S03 | Cuotas alternadas | Alternar A/B no duplica el límite; SQL caído no abre cuota | HTTP concurrente |
| S04 | Cookie y antiforgery cruzados | Formulario de A se valida en B con mismo anillo y propósito | Portal real |
| S05 | Aislamiento de anillos | Cookie/ciphertext de otro portal no se acepta; roles no leen otras tablas | Integración |
| S06 | Reinicio con claves persistidas | Sesión/payload confirmado siguen utilizables; no se generan claves de reemplazo destructivas | Proceso real |
| C01 | Lecturas a través del LB | Se observa A y B con el mismo digest/release | GCP + correlación |
| C02 | API A cae abruptamente | B procesa nuevas peticiones y comando sintético; recuperación ≤60 s | Local + GCP |
| C03 | API B cae abruptamente | Simétrico a C02 | Local + GCP |
| C04 | Pérdida de respuesta a comando | Replay con mismo ID no duplica efecto; se detecta conflicto de payload distinto | HTTP + SQL |
| C05 | Reconexión SignalR real | Snapshot recuperado sin retroceso ni tenant cruzado; camino de transporte de producto | Navegador + HTTP |
| C06 | Caída de circuito Blazor | Reconecta o recarga con mensaje/reintento usable; conserva datos confirmados | Navegador |
| C07 | Caída VM A y VM B por separado | Alcance de continuidad y degradaciones medidos; guard no apaga sano/SQL antes de tiempo | GCP |
| D01 | SIGTERM con petición en vuelo | Finaliza o revierte coherentemente, no deja cambio parcial | Proceso real |
| D02 | SIGTERM con outbox reservado | Confirmación solo si efecto persistido; reserva no confirmada recuperable | Worker/broker reales |
| D03 | Crash antes/después de ACK/commit | Replay seguro según contrato; sin promesa falsa de exactly-once externo | Integración |
| D04 | Update con migración | Migración una vez, ambos detenidos, nuevo esquema con nueva release; fallo queda fuera | Scripts + fixture |
| D05 | Plazo de apagado | Host sale antes de kill de Docker; tiempo/exit code registrados | Proceso real |
| J01 | Dos/seis competidores simultáneos | Solo un barrido admitido; contendientes no recorren candidatos | SQL concurrente |
| J02 | Misma ventana de 30 s | Una ejecución ordinaria; resto NotDue/Contended | SQL concurrente |
| J03 | Envío parcial y doble selección | Un solo efecto por bulto; versión/historia/outbox sin incremento espurio | SQL con barreras |
| J04 | Prueba válida llega al vencer | Resultado permitido por regla vigente; ningún vencimiento pisa un hecho confirmado | SQL concurrente |
| J05 | Propietario muere antes del commit | Rollback integral; otro competidor procesa y avanza coordinación | Conexión/proceso real |
| J06 | Propietario muere después del commit | Siguiente intento no repite versiones/eventos | Proceso real |
| J07 | 250+ elementos y lotes 100 | Drenaje inmediato sin esperar 30 s por lote; ningún elemento truncado | Integración |
| J08 | Cero vencimientos/cancelación | Resultado y métricas distinguen completed, not due, contended, failed y shutdown | Integración |
| J09 | SQL y RLS | API no altera coordinación; worker no accede a datos fuera del contrato; search_path seguro | PostgreSQL restringido |
| J10 | Reconciliación/consumidores existentes | No pierden progreso ni duplican proyecciones al escalar workers | Regresión focalizada |
| O01 | Frescura de telemetría | Nodo/release/última muestra visibles; huecos no aparecen como cero | HTTP + visual |
| O02 | Caída de observabilidad A | Observador externo mide failover y puede recuperar A | GCP |
| O03 | Estabilidad propuesta | 15 min base + 30 min posterior, recursos y errores registrados | GCP |
| O04 | Final/cancelación del ensayo | Recursos restaurados o pendientes explícitos con comandos; lease no extendida | Scripts + GCP |

## 7. Comandos de orientación y ejecución segura

Los siguientes comandos de lectura y tests son ejemplos desde la raíz; ajustar rutas de salida y flags al conjunto seleccionado. Ningún comando aquí debe imprimir `.env` ni conexiones. No se propone ejecutar ahora una mutación de GCP.

```powershell
git status --short
git rev-parse HEAD
git ls-tree HEAD backend frontend mobile
git submodule status
rg -n 'health/ready|health/live|expire_pending_proof_deadlines' backend frontend deploy scripts infra .github
python -m unittest discover -s scripts/gcp -p test_delivery.py
python -m unittest discover -s scripts/gcp -p test_vm_deploy.py
python -m unittest discover -s scripts/gcp -p test_demo_session.py
python -m unittest discover -s scripts/gcp -p test_control_lock.py
python scripts/gcp/validate_compose.py
dotnet test backend/tests/NexoRuta.IntegrationTests/NexoRuta.IntegrationTests.csproj --filter 'FullyQualifiedName~HostingStateTests|FullyQualifiedName~PostgresRateLimiterTests|FullyQualifiedName~OperationalSignalRTests|FullyQualifiedName~OperacionesRepartoHttpTests'
```

Añadir los tests nuevos al filtro y a shards, no depender solo de estos nombres de línea base. Docker es necesario para el validador Compose y para fixtures que lo usen; su ausencia no es un test aprobado. En esta revisión el sistema Windows no tenía `docker` en PATH. En Cloud seguir [cloud-agent.md](../continuidad/cloud-agent.md), [codex-cloud.md](../continuidad/codex-cloud.md) y los helpers existentes; no instalar otro stack ni usar los servicios Windows como atajo. `dev.py` mínimo no levanta todos los brokers.

Para IaC: `tofu fmt -check -recursive infra/gcp`, y en cada módulo init con `-backend=false -input=false -lockfile=readonly` seguido de validate. Usar la versión fijada del repositorio. Plan remoto y apply son pasos posteriores de despliegue, no dependencias para revisar el Markdown o los tests locales. Una modificación de health path del LB necesita aplicación coordinada con la release; programar un corte explícito para evitar que el LB nuevo sondee el contrato viejo, sin mantener aliases.

Consultas GCP de inventario usadas en el análisis, todas de lectura:

```powershell
gcloud.cmd compute instances list --project nexoruta-demo-20261022 --format='table(name,zone.basename(),status,machineType.basename())'
gcloud.cmd compute backend-services get-health nexoruta-demo-api --global --project nexoruta-demo-20261022 --format=json
gcloud.cmd sql instances describe nexoruta-demo-db --project nexoruta-demo-20261022 --format='json(state,databaseVersion,settings.availabilityType,settings.backupConfiguration.enabled,settings.backupConfiguration.pointInTimeRecoveryEnabled)'
gcloud.cmd redis instances list --region southamerica-west1 --project nexoruta-demo-20261022 --format='table(name,state,tier)'
```

En Linux utilizar `gcloud` en lugar de `gcloud.cmd`. No agregar dumps de estado IaC completo: pueden contener secretos. IAP SSH sirve para administración; la aplicación debe seguir publicada por el LB remoto HTTPS, nunca mediante túnel al equipo de un integrante.

## 8. Artefactos y definición de terminado

Artefactos propuestos en `docs/auditorias/nfr-13/`:

- `diagnostico.md`: línea base, diferencias de fuentes, jobs inventariados y brechas reproducidas.
- `aceptacion.md`: requisito por requisito, resultados por nivel, límites de topología y pendientes.
- `evidencia/manifest.json`: SHAs/gitlinks/digests, release, proyecto, ventana, comandos/versions y hashes de artefactos; sin credenciales ni filas privadas.
- `evidencia/failover.json`: escenario, nodo afectado, reloj UTC y monotónico, primer fallo, primera recuperación, diez éxitos posteriores, respuestas/latencias/errores y nodo de cada muestra. Conservar todos los intentos.
- `evidencia/jobs.json`: competidores, lotes, admisiones, versiones y cantidades antes/después, commits/rollbacks y recuperación; usar IDs sintéticos o huellas adecuadas, sin información real de clientes.
- `evidencia/shutdown.json`: señal, trabajo en vuelo, tiempos, resultado durable, exit code, forced kill y estado posterior.
- Capturas sanitizadas de disponibilidad/reconexión y referencias a TRX/CI. Mantener artefactos pesados en el mecanismo CI existente y no commitear logs crudos por defecto.
- Runbook con lectura de salud, diagnóstico, retiro/readmisión por herramientas existentes, recuperación de nodo/worker y prohibiciones de pérdida de datos.

El informe final del agente debe separar explícitamente:

| Categoría | Qué acredita |
| --- | --- |
| Compilación/estático | Build, formato, contrato, Compose y IaC válidos para las fuentes exactas |
| Automatización | Tests realmente ejecutados, conteos de aprobadas/fallidas/omitidas, nivel y fixtures |
| HTTP/GCP | Dos backends, reparto, efectos persistentes, failover medido y recuperación real |
| Revisión visual | Capturas vistas y comportamiento real de login/reconexión/error; escritorio y tamaños pertinentes si cambió UI |

**Checklist de cierre:**

- [ ] Card/laboratorio trazados sin cambiar sus exigencias.
- [ ] Dos APIs simultáneas en GCP y mismo candidato verificado; reparto atribuido a ambos nodos.
- [ ] `/health`, `/ready`, `/live` implementados y todos los consumidores propios actualizados.
- [ ] Pérdida de cada API por separado satisface el objetivo medido; errores en vuelo contabilizados.
- [ ] Autenticación, antiforgery, RLS, cuotas y comandos confirmados funcionan al cambiar de nodo.
- [ ] Apagado y crash tienen contratos separados y evidencia de integridad/recuperación.
- [ ] Job real coordinado por SQL, carrera parcial cubierta y sin duplicación de efectos/versiones/eventos.
- [ ] Roles mínimos y datos/claves/migraciones/volúmenes preservados.
- [ ] Cliente real SignalR/Blazor probado; cualquier afinidad necesaria documentada y configurada.
- [ ] Telemetría fresca y observador independiente para la caída de A.
- [ ] Operación sostenida dentro de la ventana acordada y entorno restaurado.
- [ ] CI del conjunto final verde; gitlinks y evidencia corresponden a ese conjunto.
- [ ] Topología ZONAL/servicios únicos/cortes de despliegue descritos sin promesa de HA integral.

## 9. Prompt listo para el agente ejecutor

> Implementa y valida NFR-13 siguiendo `docs/planes/nfr-13-escalabilidad-balanceo-disponibilidad.md`. Empieza por P0 y conserva cambios ajenos. Lee la card por MCP y las fuentes normativas; no interpretes una auditoría histórica como aprobación operativa. No actualices submódulos a otras puntas ni agregues compatibilidad con contratos anteriores. Reutiliza .NET 10, PostgreSQL/RLS, workers, Compose, OpenTofu, scripts y pruebas existentes. Primero reproduce las brechas de salud, apagado y concurrencia del barrido real. Aplica contratos de salud y coordinación SQL según el plan, con migración nueva y productores/consumidores sincronizados. Demuestra cookies/cuotas/RLS y reconexión real entre dos procesos. No inventes un cierre diario, no prometas entrega externa exactamente una vez y no conviertas este trabajo en HA de SQL/brokers. Prepara el candidato y las evidencias locales antes de iniciar una ventana GCP. Usa únicamente la autorización operativa vigente; un pedido de planificación no autoriza fallos, carga, apply ni despliegue. Preserva las cuatro horas, respaldos, secretos y datos; recupera el entorno tras cada escenario. No declares Done con tests simulados, rutas sanas solamente o evidencia sin frescura. Entrega el commit/conjunto exacto, resultados por compilación, automatización, HTTP y revisión visual, y los gates que sigan pendientes.

## 10. Referencias técnicas primarias

Consultadas para contrastar decisiones, no para reemplazar el laboratorio ni el código del proyecto:

- [ASP.NET Core 10: health checks y readiness/liveness](https://learn.microsoft.com/en-us/aspnet/core/host-and-deploy/health-checks?view=aspnetcore-10.0).
- [Google Cloud: distribución de peticiones y afinidad](https://docs.cloud.google.com/load-balancing/docs/https/request-distribution): la afinidad es best effort; no garantiza conservación de estado de un backend muerto.
- [Google Cloud: connection draining](https://docs.cloud.google.com/load-balancing/docs/enabling-connection-draining): retirar una instancia de su grupo es distinto de eliminar todo el grupo del backend; el drenaje permite terminar peticiones en curso durante su presupuesto.
- [PostgreSQL 18: advisory locks](https://www.postgresql.org/docs/18/explicit-locking.html#ADVISORY-LOCKS): usar el ciclo de vida transaccional para que el candado no sobreviva al trabajo ni se devuelva retenido al pool.
- [PostgreSQL: SELECT y SKIP LOCKED](https://www.postgresql.org/docs/current/sql-select.html): apropiado para trabajo tipo cola; no reemplaza las condiciones de actualización ni una garantía de efecto único.

## 11. Validación de este documento

Se comprobó el contenido de la card por MCP, se extrajeron las secciones relevantes del PDF y la fila NFR-13 del XLSM, se inspeccionaron fuentes/pruebas y se realizaron las consultas remotas de lectura descritas. Se revisaron las referencias locales y el formato del documento. No se ejecutaron builds, tests funcionales, automatización de fallos ni revisión de navegador en esta tarea documental; sus resultados quedan como trabajo del agente implementador. No hay modificación de contratos, infraestructura, datos, estado de Notion ni gitlinks por la elaboración del plan.
