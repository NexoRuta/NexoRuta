# NFR-07: guía de cierre para el agente ejecutor

Auditoría inicial: 05/11/2026, 23:55 UYT. **Ampliación: 06/11/2026, con capacidad de VM B medida entre 00:06 y 00:09 UYT.** Tipo de entrega: auditoría y especificación; no implementa los cambios pendientes ni modifica la card.

## Estado de implementación — 06/11/2026

Esta ejecución implementó localmente la ruta de Redis en VM B y la ampliación de observabilidad, pero **no desplegó ni modificó GCP**. La auditoría inicial y el inventario de GCP de abajo describen el estado observado antes de estos cambios; el checkout actual todavía no está publicado en una release. Memorystore sigue declarado en IaC deliberadamente hasta aceptar la migración.

| Frente | Implementado en el checkout | Aceptación que sigue pendiente |
| --- | --- | --- |
| R0 capacidad | Se conserva la medición de B: 6 vCPU, 16 GiB, `MemAvailable` mínimo 12,74 GiB y CPU p95 histórico 12,617%. | Repetir medición bajo carga representativa con Redis y comprobar los gates de memoria, CPU, PSI, OOM y latencia. |
| R1 identidad/red/IaC | Secreto separado, identidad TLS validada sin regeneración implícita, DNS de B, subnet runtime, firewall privado y tag exclusivo de destino B. | Aplicar bootstrap y plan demo revisado; confirmar valores/recursos efectivos sin deletes ni replaces. |
| R2 servicio Redis | Compose contiene una sola instancia Redis fijada por digest, perfil `cache-b`, TLS, ACL por namespace, límites 512 MiB/1 CPU y filesystem no escribible salvo tmpfs de caché. | Validar Compose con Docker y ejercitar imagen, permisos, TLS, ACL y consumo bajo carga en fixture. |
| R3 despliegue | El deployer prepara Redis solo en B, preserva el servicio durante updates y ejecuta smoke TLS/AUTH/SET/GET/DEL desde A y B antes de admitir APIs. El modo bypass permite actualizar ambos nodos sin depender del secreto, DNS o contenedor Redis y omite las sondas Redis. | Publicar una release y probar start/update/stop reales, incluidos bypass y retorno a caché activa, sin ampliar el lease de cuatro horas. |
| R4 telemetría | El monitor valida TLS/hostname/AUTH/PING desde ambas VMs y expone salud, memoria, RSS, clientes, evicciones y recursos Docker de Redis en B. Dashboard canónico/copia y runbook incluyen métricas de caché y Redis. | Confirmar las series en Prometheus/Grafana GCP, revisar el dashboard en navegador y aceptar capacidad bajo carga. |
| A1 series iniciales | Las series conocidas en cero se emiten desde `IHostedLifecycleService.StartedAsync`, después del arranque del proveedor OTLP; hay prueba unitaria. | Verificar en el exportador real que aparecen tras arrancar dos procesos. |
| A2 procesos/OTLP | La instrumentación y el exportador existente se conservan. | No se agregó aún el ensayo de dos procesos independientes atravesando Collector y Prometheus; comprobar nombres, labels, acumulación y reset. |
| A3 Grafana | Se añadieron ratio total ponderado, cantidades de hit/miss por rango, estado sin telemetría y paneles de salud/recursos Redis. | Generar lecturas reales de ambos nodos y casos; adjuntar consultas/capturas y hacer revisión visual del Grafana servido. |
| A4 beneficio/degradación | Se conserva el fallback a PostgreSQL y se añade ACL de runtime probada por integración al compilar. | Medir beneficio con payloads representativos, presupuesto de latencia con Redis caído/sin respuesta y recuperación; ejecutar las pruebas Redis con Docker. |
| R5 primera entrega | El código local ya apunta únicamente a B y el recurso anterior sigue presente en IaC durante la migración. | Pendiente publicar, aplicar cambios no destructivos y aceptar smoke cruzado y capacidad antes de retirar Memorystore. |
| R6 stop/4 h | No se alteró el control existente: el workflow `stop` detiene ambas VMs y Compute Engine conserva `STOP` a los 14400 segundos; Redis comparte el ciclo de B. | Observar stop manual, vencimiento real, start con caché vacía, miss→hit y degradación/recuperación de A. |
| R7 retiro | **Pendiente intencional.** No se quitó `google_redis_instance.cache` ni se debilitó el guard contra deletes. | Retirar Memorystore mediante el plan específico descrito abajo, solo después de aceptar R5/R6. |
| R8 entrega | Este plan y `docs/runbooks/cache-redis-grafana.md` reflejan configuración y operación propuestas. | Publicar SHAs, resultados efectivos, evidencias de Grafana y estado final en la card después de realizar esas operaciones. |

### Validación del checkout de esta ejecución

| Tipo | Resultado |
| --- | --- |
| Automatización Python | `python -m unittest discover -s scripts/gcp -p 'test_*.py'`: **234 tests, OK, 8 skipped**. |
| .NET integración | `dotnet restore ... --locked-mode` y `dotnet build tests/NexoRuta.IntegrationTests/NexoRuta.IntegrationTests.csproj --no-restore`: compiló con 0 errores y 3 warnings preexistentes en otros archivos. La prueba que inicia Redis no se ejecutó. |
| .NET unitarias | `dotnet restore tests/NexoRuta.UnitTests/NexoRuta.UnitTests.csproj --locked-mode` y `dotnet test ... --no-restore`: **337 aprobadas, 0 fallidas, 0 omitidas**. |
| OpenTofu | `tofu fmt -check -recursive`, `tofu init -backend=false -lockfile=readonly` y `tofu validate`: correctos. Init/validate fueron locales, sin backend ni estado remoto. |
| Python/JSON/diff | `py_compile` de archivos Python cambiados, parseo JSON de dashboard, igualdad de las dos copias y `git diff --check`: correctos. |
| Compose/Redis TLS | No ejecutados: `docker` y `openssl` no están instalados/en PATH en este entorno Windows. |
| Grafana visual | No ejecutada: se editaron JSON estáticos, pero no se abrió un Grafana servido en navegador. |
| GCP | Sin apply, despliegue, reinicio, tráfico funcional ni retiro de recursos. |

Los cambios están sin commit. Por ello, el workflow de VM no puede consumirlos como release hasta que el checkout y sus gitlinks se publiquen conforme al proceso existente. Ninguna casilla de aceptación R5–R8 debe marcarse como completada usando solo las pruebas con mocks de esta suite.

## 1. Conclusión y autoridad

La feature **ya tiene implementación y despliegue**. El trabajo restante es completar la observabilidad de arranque, demostrar lecturas compartidas entre procesos, verificar métricas emitidas por las APIs en el Grafana existente y documentar beneficio y degradación.

**Decisión posterior del usuario: migrar el único Redis a la VM B para que su cómputo se detenga con stop y al cumplirse cuatro horas.** Conservar ambas cachés y ambos consumidores. No mover a B otros servicios compartidos por interpretar «todo» fuera del contexto de Redis. La [sección 9](#9-migración-de-redis-a-vm-b-y-ciclo-de-cuatro-horas) es la especificación vigente de infraestructura y reemplaza la elección original de Memorystore permanente; la [auditoría de capacidad](../auditorias/nfr-07/2026-11-06-capacidad-vm-b.md) confirma margen para preparar esa migración, con aceptación bajo carga pendiente. No reimplementar las cachés de negocio.

Fuentes:

- [Card NFR-07](https://app.notion.com/p/40a032f1caff8153a177dc1212d1d903), leída mediante MCP de Notion. Estado consultado: **Do tests**. La descripción del 31/10 quedó superada; sus notas posteriores reconocen código y dashboards, pero todavía incluyen el pendiente ya superado de desplegar Redis.
- [Plan original](nfr-07-cache-distribuida.md): define las lecturas, invariantes, políticas y evidencia histórica. Sus tareas T1–T6 ya no son un backlog desde cero.
- [Card NFR-12](https://app.notion.com/p/40a032f1caff816b8875f31ab987e239): figura Done por una validación anterior de observabilidad general y caché local Geoapify. Ese cierre no acredita los nuevos casos Redis.
- Checkout exacto y consultas actuales de GCP/Prometheus, descritos abajo. La existencia del código, el estado READY y las pruebas históricas acreditan cosas diferentes.

Mantener **Do tests** mientras se ejecuta la aceptación. Si se comienza la corrección pendiente, In progress puede reflejar ese trabajo; Done requiere la matriz de cierre completa. Este documento no cambia propiedades ni contenido de Notion.

## 2. Evidencia nueva y límites

### Fuentes inspeccionadas y release efectiva

| Fuente | SHA |
| --- | --- |
| Raíz | `9d805b6536d46a4febf2ae0c1018d2e13c3be4ed` |
| Backend | `aeeab68403c8de9c90d65069c710403f781981d9` |
| Frontend | `33735dea78615b9f244403cc713c2b76927864db` |
| Mobile | `683766d6d8cd6c1bd9ce45bb12f6581ddb19b98c` |

Se inicializaron los gitlinks exactos, sin avanzar ramas. El manifiesto de `release-e13f492d80c346db82e5b9f6aa12758c`, canal develop, contiene exactamente esos cuatro SHAs. Se leyó desde el bucket de entrega indicado por la variable GitHub `GCP_DELIVERY_BUCKET`, sin publicar secretos ni descargar estado OpenTofu.

### Estado operativo observado mediante lecturas

| Comprobación | Resultado y alcance |
| --- | --- |
| Proyecto/región | `nexoruta-demo-20261022`, `southamerica-west1`. |
| Memorystore | `nexoruta-demo-cache`, creado el 04/11/2026 a las 19:22 UTC; READY, BASIC, 1 GiB, Redis 7.2, PRIVATE_SERVICE_ACCESS, AUTH true, SERVER_AUTHENTICATION, puerto 6378. No se verificó una operación Redis autenticada desde la aplicación. |
| VMs | `nexoruta-demo` en zona a y `nexoruta-demo-b` en zona b: RUNNING. |
| Release | El marcador de ambas VMs y `nexoruta_gcp_applied_release` coinciden con la release indicada arriba. |
| API A/B | Contenedores running y misma imagen `api@sha256:db17793f476c8837c30b8376cf1ce013299646dbc963a0f98ac71aa5d3a58837`. Caché, TLS y OpenTelemetry habilitados; namespace `nexoruta-gcp-demo`; `NODE_NAME=a/b`; exportación a `http://otel-collector:4317`. Se comprobó presencia de endpoint, AUTH y CA sin imprimir sus valores. |
| Redis desde nodos | `nexoruta_gcp_service_up{service="redis"}=1` en a y b. El agente usa `socket.create_connection`: acredita TCP, **no valida TLS, AUTH ni GET/SET**. |
| Prometheus | API HTTP de consulta accesible por IAP/SSH y red privada. Hay series `nexoruta_api_requests_total` y duración HTTP de `NexoRuta.Api`. La ruta general de métricas funciona. |
| Caché en Prometheus | `sum by (node,cache,result)(nexoruta_cache_distributed_requests_total{service_name="NexoRuta.Api"})` devolvió vector vacío. También `count by (__name__)({__name__=~"nexoruta_cache.*"})` devolvió vacío. No se generaron lecturas de negocio en esta revisión; **causa no determinada**. |
| Dashboard | UID `nexoruta-demo`; fuente canónica y copia GCP semánticamente iguales. El archivo montado en Grafana B coincide con ambas al normalizar CRLF a LF: SHA-256 `a6fd2f4db93a5658c5eeecf699911371c3ea80b5da6ff56f11346b16907e0cba`. Incluye fila Caché distribuida y cinco paneles. No se abrió en navegador ni se inspeccionó la representación servida por Grafana. |

Comandos de inventario reproducibles, siempre con proyecto explícito:

```powershell
git rev-parse HEAD
git submodule status
gcloud redis instances describe nexoruta-demo-cache --project=nexoruta-demo-20261022 --region=southamerica-west1 --format="json(name,state,tier,memorySizeGb,redisVersion,createTime,connectMode,transitEncryptionMode,authEnabled)"
gcloud compute instances list --project=nexoruta-demo-20261022 --filter="name~nexoruta-demo" --format="table(name,zone.basename(),status)"
```

Las consultas de Prometheus se hicieron desde las VMs, contra `http://nexoruta-demo.southamerica-west1-a.c.nexoruta-demo-20261022.internal:9090/api/v1/query`. Los puertos privados no deben publicarse para facilitar las pruebas. No asumir que este estado sigue vigente cuando otro agente retome.

### Verificación de esta revisión, separada por categoría

| Categoría | Evidencia de esta ejecución |
| --- | --- |
| Compilación | No ejecutada: cambio documental. SDK disponible 10.0.401. Los resultados .NET del plan original son históricos. |
| HTTP | GET de consultas de Prometheus reales con status success; sin llamadas funcionales autenticadas a las APIs. |
| Automatización | `python -m unittest discover -s scripts/gcp -p 'test_*.py'`: **221 tests, OK, 7 skipped**. Los escenarios de despliegue de esa suite usan mocks; no son despliegues realizados. Comparación de dashboard local/copia y hash del archivo montado en B comprobados. |
| Compose | `python scripts/gcp/validate_compose.py` no pudo ejecutarse: Docker no está en PATH. No acredita manifiesto inválido. |
| Revisión visual | No ejecutada. La revisión sintética del 03/11 sigue siendo evidencia histórica limitada. |
| GCP | Inventario, configuración seleccionada, release y métricas consultados. Sin apply, despliegue, reinicio, cambio de TTL, tráfico funcional o pruebas de caída. |

## 3. Qué existe y debe conservarse

| Parte | Código y comportamiento actual |
| --- | --- |
| Acceso Redis | `backend/src/NexoRuta.Infrastructure/Caching/DistributedCacheAccess.cs`: IDistributedCache, envelope v1, System.Text.Json, validación, límite 2 MiB, TTL absoluto con jitter hacia abajo de hasta 10%, resultados y operaciones separados. |
| Configuración y DI | `DistributedCacheSettings.cs` y `Persistence/DependencyInjection.cs`: proveedor Microsoft.Extensions.Caching.StackExchangeRedis 10.0.12, cliente compartido, tiempos configurados 500 ms, CA propia y comprobación de nombre TLS. TTL permitido 60–604800 s; no usar TTL=1 a través de configuración de arranque. |
| Identidad | `Infrastructure/Administracion/EfConsultaIdentidadVisualOperador.cs`: selecciona versión en PostgreSQL/RLS, busca snapshot exacto y consulta origen ante miss/error/bypass. Consumida por GET administrativo y GET de Commerce. TTL nominal 900 s. |
| Tarifarios | `Infrastructure/Tarifas/EfTarifariosRepository.cs`: cabecera autorizada viva, snapshot Publicada reutilizado entre detalle y simulación; borradores bypass; zona activa consultada en cada simulación. TTL nominal 21600 s. |
| Invalidación | Claves por operador y versión inmutable. Las escrituras no publican caché ni cachean el puntero vigente. Después del commit se selecciona una clave nueva; el histórico publicado sigue disponible por ID. No necesita outbox de invalidación. |
| Métricas | `Infrastructure/Hosting/ApiTelemetry.cs`, clase `DistributedCacheTelemetry`, meter `NexoRuta.Hosting`; `HostingTelemetry.cs` suscribe ese meter y exporta OTLP. |
| Observabilidad | `deploy/observability/grafana/nexoruta.json` es la fuente canónica; copia en `deploy/gcp/grafana/provisioning/dashboards/nexoruta.json`. Alertas canónicas y tests en `deploy/observability/prometheus/`; copia GCP de reglas. |
| Transporte | Local: API → Collector → exporter Prometheus → scrape. GCP: API A/B → Collector por nodo → remote write a Prometheus A → Grafana. |
| Pruebas actuales | `IdentidadVisualOperadorHttpTests`, `TarifarioHttpTests`, `Caching/DistributedCacheRedisTests`, unitarias `Caching/DistributedCacheAccessTests`. PostgreSQL/RLS y Redis propios. Incluyen consultas pesadas evitadas, carreras, rollback, aislamiento, caída/recuperación, expiración y desalojo. |

**Límite de las pruebas existentes:** `Fixtures/IntegrationApiFactory.cs` deriva de WebApplicationFactory y fija `OpenTelemetry:Enabled=false`. A y B tienen DI/clientes independientes, pero viven en el mismo proceso de tests y comparten estáticos del meter. MeterListener verifica instrumentación dentro del proceso; no prueba OTLP, nombres exportados ni aislamiento entre procesos. No sustituir estas pruebas: complementarlas.

Claves reales; los nombres de caso llevan **underscore**, a diferencia de los ejemplos propuestos en el plan original:

```text
nexoruta:<namespace>:cache:v1:operator_branding:<operadorUuid>:<versionEntera>
nexoruta:<namespace>:cache:v1:published_tariff:<operadorUuid>:<versionUuid>
```

## 4. Brechas concretas que resolver

1. **Inicialización de telemetría perezosa.** Los Add(0) están en el constructor estático de DistributedCacheTelemetry; no hay inicialización explícita al iniciar la API. Antes de su primer uso los filtros de Grafana pueden no tener casos disponibles. Es compatible con lo observado, pero no demuestra que sea la única causa de ausencia actual. Garantizar exportación inicial con cero después de que el MeterProvider esté escuchando, sin inventar lecturas.
2. **Falta prueba de procesos y pipeline completo.** Los tests de dos hosts no cubren dos procesos ni Collector/Prometheus. Falta demostrar también el transporte real local y remote write.
3. **Dashboard incompleto respecto del plan.** Los cinco paneles 101–105 muestran tasas, porcentaje por caso agregado entre nodos, errores/bypass y p95. No hay un total ponderado entre ambos casos ni cantidades hit/miss de la ventana seleccionada. Agregarlos en la misma fila; conservar UID y filtros.
4. **Vacío ambiguo.** “Sin tráfico” solo es correcto con telemetría presente y contadores sin incremento. Ausencia de series debe identificarse como “Sin telemetría de caché”; no presentarla como 0% ni como Redis caído.
5. **Presupuesto de fallo no medido.** Hay timeout de operación y AsyncTimeout configurados, pero no aserciones de latencia ni política BacklogPolicy explícita. Validar tiempos con el proveedor real bajo conexión rechazada y conexión aceptada que no responde. No asegurar que CancelAfter limita toda espera del cliente solo por leer el código.
6. **Beneficio no cuantificado.** Los interceptores comprueban reducción de cargas grandes, pero falta comparación reproducible de latencia/volumen con caché habilitada/deshabilitada.
7. **Runbooks y card atrasados.** Las guías de Grafana describen caché genérica; falta explicar los dos casos, filtros, diagnóstico, rollback y evidencia operativa actual. La card debe reemplazar pendientes superados por resultados comprobados al concluir.
8. **Ciclo de recursos cambiado por decisión del usuario.** Sustituir Memorystore por Redis en B, con límites, TLS/AUTH, despliegue por nodo, probes y apagado ligados a B. Retirar el servicio administrado solo después de aceptar el nuevo destino. El stop habitual seguirá sin destruir infraestructura persistente.

## 5. Secuencia de trabajo y entregas

Orden actualizado: A0 → preparación/validación de R0–R4 de la sección 9 → A1–A4 → R5/despliegue y A5 → R6/aceptación de ciclo y R7/retiro → A6. Se puede preparar código local de tareas independientes a la vez, sin requerir agentes adicionales. Cada paso termina con resultado verificable y pendientes explícitos.

### A0 — Preflight y línea base

- Leer AGENTS.md, `frontend/DESIGN.md` antes de tocar Grafana, continuidad Cloud y este documento. Registrar HEAD, gitlinks y cambios locales; no cambiar fuentes para reproducir SHAs históricos.
- Repetir inventario GCP, release A/B y consultas de series. Si la sesión terminó, preparar todo lo local y dejar la operación GCP para una sesión explícitamente autorizada; no arrancar VMs para elaborar un plan.
- Ejecutar primero los tests focalizados existentes con fixtures propias. Con Docker usar los contenedores fijados; sin Docker en Linux usar el procedimiento versionado de `scripts/cloud/check-nfr-07.sh`, leyendo antes sus dependencias. El helper **no instala Redis**: requiere `/opt/nexoruta-redis-7.2.16/bin/redis-server` preparado por `install.sh`. No reemplazar gitlinks ni usar bases del usuario.
- Conservar resultados previos como históricos y guardar nuevos comandos, filtros, cantidades y TRX en artefactos privados/sanitizados. No atribuir al agente una ejecución anterior.

**Salida:** inventario fechado y línea base actual; si algo falla, clasificación concreta antes de editar.

### A1 — Telemetría de arranque y paneles

**Backend:** editar `ApiTelemetry.cs`, composición en `HostingTelemetry.cs`/arranque API y tests correspondientes.

- Agregar una inicialización idempotente de las combinaciones conocidas de request y operación, integrada al arranque de API. Ejecutarla después de crear/suscribir el MeterProvider, también cuando aún no hubo lecturas. Evitar que un constructor estático que ya corrió antes del listener impida registrar ceros. No abrir Redis ni hacer SELECT solo para inicializar métricas.
- Conservar exactamente una decisión por lectura elegible: hit, miss, error, bypass o cancelled. Un set fallido después del miss solo aumenta error de operación. No sumar error como miss ni cachear errores de negocio.
- Prueba necesaria: iniciar **proceso nuevo**, OTLP habilitado, sin lecturas funcionales; esperar exportación y comprobar ceros para ambos casos. Repetir con caché deshabilitada y luego una lectura, que debe incrementar bypass.

**Raíz:** editar dashboard canónico, sincronizar copia, ajustar `scripts/gcp/test_delivery.py` y documentación de observabilidad.

- Conservar paneles existentes y agregar cantidades hit/miss para `$__range` usando increase por caso, y porcentaje total ponderado de los casos/nodos seleccionados. Las tasas usan `$__rate_interval`; las cantidades de ventana son estimaciones Prometheus, no un registro contable exacto.
- Total = `100 * sum(rate(hit)) / sum(rate(hit|miss))`, con los mismos filtros y ventana, únicamente si denominador > 0. No usar avg de ratios; excluir error/bypass/cancelled. Usar unidad percent 0–100. Cero misses/hits no debe producir porcentaje.
- Conservar filtro `cache` dinámico para `operator_branding` y `published_tariff`, `node` y `otel_service`; el tráfico de aceptación usa NexoRuta.Api. Identificar Geoapify como caché local separada.
- Añadir indicación de presencia/actualidad de telemetría por nodo, evaluada sobre las series de requests y señales de API/Collector disponibles. Diferenciar estado sin incremento y ausencia de series; no reemplazar métricas ausentes con ceros indiscriminadamente. Antes del primer GET/SET puede no existir histograma: mostrar ausencia de operaciones, no inventar p95=0.
- Verificar en navegador carga, vacío, error de datasource, filtros, unidades, leyendas y teclado usando los controles de Grafana. Aplicar DESIGN.md sin añadir framework ni skeleton artificial al dashboard.

**Aceptación:** después de arrancar sin tráfico se pueden seleccionar ambos casos; ceros y ausencia de muestras se distinguen. Con tráfico, tasas, cantidades y ratios son consistentes. Archivo canónico/copia iguales y UID estable.

### A2 — Harness de dos procesos y telemetría real

Crear un harness optativo, por ejemplo `scripts/verification/nfr07/`, con README, arranque/parada y salida JSON. Reutilizar las fixtures y seeding existentes; no agregar endpoints de diagnóstico al producto ni aceptar privilegios extra en el API runtime.

- Dos procesos Kestrel independientes con IDs/PIDs y puertos distintos, misma base sintética PostgreSQL/PostGIS con rol API restringido y un Redis efímero propio. Namespace único por ejecución. Sin WebApplicationFactory como sustituto de esta evidencia.
- Autenticación normal del producto. Se pueden preparar actores mediante los helpers de test, sin saltar auth en las solicitudes ni imprimir tokens. Registrar solo IDs sintéticos y huellas necesarias, nunca credenciales o logos completos.
- Collector/Prometheus de versiones fijadas. Probar **(a)** transporte local con una API y **(b)** dos procesos con los dos Collectors del diseño GCP, `NODE_NAME=a/b`, `SERVICES_HOST` apuntando al Prometheus de la fixture y remote write real. Así se conserva separación de series. El Collector local fija `node=local` y no exporta service.instance.id: no enviar dos APIs al mismo exporter local y asumir que eso distingue nodos.
- No fabricar contadores con un exporter sintético. Las únicas operaciones que producen hit/miss son los endpoints de las APIs.
- Antes de cada secuencia nueva, esperar al menos dos exportaciones/muestras para establecer una línea base cero. Después esperar con polling acotado hasta 180 s por fase para observar deltas. El periodo debe cubrir exportación SDK, batch y scrape/remote write. En caso de timeout fallar con diagnóstico por tramo, no continuar declarando éxito.
- Emitir por paso nodo, endpoint plantilla, resultado HTTP, recurso sintético/versionado, deltas de métricas y duración; no URL privada con tokens ni cuerpos completos. Contar consultas pesadas mediante interceptores de prueba o diagnóstico de base aislada, sin habilitar logging de SQL sensible en el despliegue compartido.
- Limpiar solo procesos/recursos propios con identificador de propiedad y conservar reporte. No ejecutar down -v, FLUSHALL, KEYS ni barrido del namespace compartido de GCP.

**Salida:** una invocación documentada reproduce la matriz A3 y deja `summary.json` y consultas Prometheus de respaldo. Incluirla en el gate de integración apropiado si el coste es aceptable; de lo contrario gate optativo explícito previo al cierre. Actualizar inventario/shards si se agregan clases de integración.

### A3 — Matriz funcional y de métricas

Usar recursos nuevos o versiones nuevas para obtener misses; no vaciar el Redis de la demo.

| Secuencia | Aserciones |
| --- | --- |
| Identidad A → B | Guardar versión N por PUT administrativo, esperar respuesta confirmada. GET administrativo A: miss=1, carga grande=1. GET Commerce B del mismo operador: hit=1, carga grande=0. Datos de marca iguales según contratos de cada endpoint. |
| Identidad B → A | Guardar N+1; GET B primero: miss. GET A después: hit. Visible sin esperar TTL. Versión N no contamina N+1 si había lector lento. |
| Tarifario A → B | Crear/configurar/publicar P; publicación responde tras commit. Detalle A: miss. Simulación publicada B de P: hit y sin cargar grafo completo. Variar bultos y comprobar cálculo diferente y correcto. |
| Tarifario B → A | Publicar P+1 nueva. Detalle B: miss. Simulación A: hit. P sigue consultable por ID; el endpoint de estado selecciona P+1. |
| Borrador | Simular, editar, simular otra vez: datos actuales, bypass, ningún get/set de ese snapshot editable. Publicarlo y verificar elegibilidad solo después del commit. |
| Estado y seguridad | Hit de publicación seguido de zona inactiva rechaza simulación; reactivación recupera. Operador/versión ajenos, permisos revocados o acceso suspendido no atraviesan auth/RLS por estar cacheados. Redis no almacena decisiones de permiso. |
| Expiración | Fixture con TTL 60 s y 70 s y jitter: PTTL positivo, finito y dentro de rango esperado; después de expiración real vuelve miss. Sondeo acotado; no esperar seis horas ni cambiar TTL de GCP para esta prueba. |
| Corrupción/tamaño | Solo fixture: JSON inválido, payload de otro operador/versión, y mayor al máximo producen error de lookup y origen; snapshot de origen demasiado grande se sirve y no se cachea. |
| Cancelación y fallo | Cancelled conserva cancelación; error GET no es miss; error SET no falla respuesta de origen. Verificar error/bypass y recuperación según A4. |
| Reinicio API | Reiniciar solo un proceso de fixture conserva entradas Redis compartidas; demostrar nuevo hit y ratio correcto con reset de contadores. |

Endpoints actuales para el harness:

```text
GET/PUT /api/configuracion/identidad-visual
GET     /api/operadores/{operadorId}/identidad-visual      (sesión Commerce)
GET     /api/configuracion/tarifas
POST    /api/configuracion/tarifas/borrador
PUT     /api/configuracion/tarifas/borrador/tarifas
POST    /api/configuracion/tarifas/borrador/publicar
GET     /api/configuracion/tarifas/publicaciones/{versionId}
POST    /api/configuracion/tarifas/simulaciones
```

Usar contratos vigentes en `TarifarioContracts.cs`. Ejemplo de simulación para una zona/versión sintética válida:

```json
{
  "versionTarifarioId": "<UUID publicación>",
  "zonaId": "<UUID zona activa>",
  "modalidad": "Estandar",
  "bultos": [{"pesoGramos": 1000, "largoCentimetros": 10, "anchoCentimetros": 10, "altoCentimetros": 10}]
}
```

No usar el GET de estado como prueba de hit del tarifario: ese endpoint no consume el lector cacheado. Una identidad nunca configurada retorna respaldo sin lookup, por lo que tampoco genera miss.

### A4 — Fallos y medición del beneficio

**Fallos, solamente sobre fixture propia:** arranque con Redis rechazando conexiones, caída tras calentar, servidor que acepta TCP pero no responde, GET/SET y recuperación sin reiniciar API. Incluir CA y AUTH incorrectos en fixture TLS; no degradar TLS real ni editar la CA del recurso compartido para probar.

- Medir separadamente primera conexión, GET y SET. Con timeout configurado 500 ms, objetivo de aceptación: cada acceso Redis termina en **≤1500 ms** y una lectura fría completa no acumula **>3000 ms adicionales** respecto del origen sano, bajo carga sintética acotada. Es tolerancia de validación, no SLO público de la aplicación.
- Si el proveedor incumple, corregir DI/espera/política de cola. Evaluar `BacklogPolicy.FailFast` y espera explícitamente acotada según la versión fijada; no añadir reintentos por petición. Probar recuperación y que no queden tareas/colas creciendo. Si se abandona una espera, observar la tarea pendiente y evitar callbacks que capturen DbContext scoped.
- El error de PostgreSQL conserva su semántica aunque falle Redis; readiness de negocio no depende de Redis. Un circuito local solo si la medición lo justifica, con estados, TTL y pruebas de recuperación; no introducir L1 para ocultar caída.

**Beneficio, fixture:** usar marca con logo válido cercano al máximo permitido, tarifario con tarifas/ajustes representativos dentro de los límites HTTP y la misma red/base para ambos modos. Separar arranque, miss y hit. Hacer 10 lecturas de calentamiento y al menos 100 lecturas medidas por caso/modo, concurrencia inicial 1; repetir con concurrencia 5. Para comparar, mismo dataset y procesos aislados con Caching.Enabled true/false.

Registrar p50/p95 de endpoint, tiempo de GET/SET, consultas de snapshot/grafo, filas/bytes si el diagnóstico lo permite y errores. **Gate funcional:** en hit desaparece la carga grande, pero siguen las comprobaciones pequeñas vivas. **Gate de beneficio:** mejora medible de consultas/transferencia y reporte honesto de latencia; no exigir un porcentaje arbitrario de mejora ni prometer que todo hit Redis siempre es más rápido. Si hay regresión repetible, investigar serialización/tamaño/red antes de cerrar. No migrar otros casos para inflar ratio.

### A5 — Despliegue y smoke GCP

Preparar y revisar todos los cambios antes de cualquier operación remota. Esta solicitud es de planificación: no autoriza iniciar sesión, desplegar ni realizar pruebas destructivas. La siguiente ejecución debe tener autorización de operación GCP vigente.

- Publicar backend y actualizar su gitlink en raíz solo después de tests. Entregar dashboard/configuración en el mismo conjunto; frontend/mobile no necesitan cambios por este cierre.
- Repetir inventario y seguir R5–R7: la migración sí modifica IaC/secretos/firewall. Primero aprovisionar el destino B y validar ambas APIs; después retirar Memorystore con un plan deliberado separado. No reemplazar SQL/peering ni borrar sus recursos.
- Usar el canal correcto y release inmutable. `vm-controls.yml` develop publica el conjunto exacto de gitlinks; no ejecuta Integrated CI: pasar los gates de integración por separado. En sesión activa, update actualiza aplicaciones pero `demo_session.py` no aplica el plan de infraestructura. No usar update esperando que aprovisione cambios IaC.
- Confirmar misma release/namespace y endpoint Redis **de B** en A/B, CA y AUTH configurados, TLS con verificación del DNS privado de B. Una sonda TCP verde no reemplaza GET/SET real autenticado.
- Ejecutar ambas direcciones de A3 en los dos casos con operador/versiones **sintéticos identificados**, usando los endpoints normales. Llegar directamente a API A/B mediante IAP/canal privado existente, respetando AllowedHosts; no depender del balanceador para alternar ni abrir puertos públicos. Acordar autenticación y fixtures sin modificar datos operativos existentes.
- Registrar deltas por nodo y caché antes/después. No exigir deltas exactamente 1 si otros usuarios generan tráfico en las mismas series agregadas: correlacionar ventana controlada, recursos sintéticos y observación por nodo; la prueba aislada sí exige deltas exactos.
- Abrir el Grafana existente bajo `monitor`, ruta `/d/nexoruta-demo`, filtros servicio API, caso y nodo. Verificar datos reales, ambos casos, combinaciones a/b/All, total ponderado, unidades, p95 y ausencia de tráfico. Guardar capturas sanitizadas y respuestas de consultas.
- Las pruebas de caída/TLS inválido quedan en fixture. Los ensayos de stop/arranque de R6 usan una ventana de demo identificada; no provocar indisponibilidad fuera de ella.
- Durante la transición Memorystore sigue facturando. Su retiro es R7, nunca una limpieza implícita del smoke. Una vez retirado, stop/guard de B detiene Redis; discos, secretos y otros recursos conservados pueden seguir generando costo.

**Salida:** reporte GCP fechado con release/SHAs, solicitudes por instancia, resultados y telemetría real. Si falta acceso navegador o una operación falla, conservar el pendiente específico y no cerrar la card.

### A6 — Documentación y cierre de la card

- Actualizar `deploy/local/observability/README.md`, `deploy/gcp/grafana/README.md` y, si corresponde, `deploy/gcp/monitoring/README.md`: ubicación de fila/filtros, significado de hit/miss/bypass/error, intervalo de exportación y diagnóstico por tramo.
- Dejar evidencia sanitizada en `docs/auditorias/nfr-07/` o artefacto privado enlazado: fecha/zona, versión, comandos, matriz de resultados, consultas, medición y capturas. Binarios/logs crudos y secretos no van a Git.
- Actualizar esta guía y la card con hechos nuevos; reemplazar “desplegar Redis” por resultado fechado y conservar historial de limitaciones. Cambiar Done únicamente tras satisfacer la matriz final, dentro del alcance de escritura autorizado en esa ejecución.
- Entregar un informe separado de compilación, HTTP, automatización, revisión visual y GCP; enlazar commits y evidencia. No presentar un dashboard sintético como prueba de métricas de producto.

## 6. Consultas y diagnóstico que debe entregar el agente

Nombres **esperados**, que deben verificarse en la salida de las versiones fijadas de ambos exporters; si difieren, corregir instrumentos/consultas juntos, sin aliases para el nombre anterior:

```text
nexoruta_cache_distributed_requests_total{cache,result,node,service_name}
nexoruta_cache_distributed_operations_total{cache,operation,result,node,service_name}
nexoruta_cache_distributed_operation_duration_seconds_bucket{cache,operation,le,node,service_name}
```

Cada lectura elegible emite una decisión. Un get saludable con payload corrupto es error de lookup, aunque la operación de transporte get figure success. Los errores de lookup y operación se muestran separados: no sumarlos como si fueran fallos únicos.

Diagnóstico inicial y tasas por nodo/caso:

```promql
# Presencia actual y nombres reales; no presupone que existan muestras.
count by (__name__, node, service_name) ({__name__=~"nexoruta_cache_distributed_.*"})

# Resultados y operaciones: inspeccionar ambas familias.
sum by (node, cache, result) (
  increase(nexoruta_cache_distributed_requests_total{service_name="NexoRuta.Api"}[5m])
)
sum by (node, cache, operation, result) (
  increase(nexoruta_cache_distributed_operations_total{service_name="NexoRuta.Api"}[5m])
)

# Tasas en el dashboard; los filtros conservan selección múltiple/All.
sum by (cache, result) (
  rate(nexoruta_cache_distributed_requests_total{
    service_name=~"$otel_service",node=~"$node",cache=~"$cache",result=~"hit|miss"
  }[$__rate_interval])
)
```

Usar contadores sin rate para una primera muestra; rate/increase requieren al menos dos muestras. Comparar deltas en fixture y comprobar resets. Para p95 usar histogram_quantile sobre suma de buckets por `le,cache,operation`; esa latencia mide la operación instrumentada de caché, **no** el endpoint completo ni solo CPU del servidor Redis.

Orden de diagnóstico cuando faltan series: lectura elegible/autorizada → instrumentación e inicialización → suscripción del meter/exportación API → recepción Collector → nombres/etiquetas exportadas → scrape/remote write → consulta datasource/filtros → dashboard. Guardar el primer tramo fallido; no cambiar varias capas sin localizarlo.

Mantener alertas existentes `NexoRutaDistributedCacheHitRatioLow` y `NexoRutaDistributedCacheErrorsHigh`. Verificar con promtool ausencia/poco tráfico, volumen suficiente, agregación ponderada, reset y recuperación. Ratio bajo no es por sí solo una falla funcional ni debe dispararse sin tráfico.

## 7. Gates y criterio de terminado

Comandos base, ajustando filtros solo si los nombres cambian y comprobando tests descubiertos:

```powershell
dotnet restore backend/NexoRuta.sln --locked-mode
dotnet build backend/NexoRuta.sln -c Release --no-restore
dotnet test backend/tests/NexoRuta.UnitTests/NexoRuta.UnitTests.csproj -c Release --no-build --no-restore --filter "FullyQualifiedName~Caching|FullyQualifiedName~Tarifas|FullyQualifiedName~IdentidadVisual"
dotnet test backend/tests/NexoRuta.ArchitectureTests/NexoRuta.ArchitectureTests.csproj -c Release --no-build --no-restore
dotnet test backend/tests/NexoRuta.IntegrationTests/NexoRuta.IntegrationTests.csproj -c Release --no-build --no-restore --filter "FullyQualifiedName~Caching|FullyQualifiedName~IdentidadVisualOperador|FullyQualifiedName~Tarifario|FullyQualifiedName~TarifaAdmision"
python -m unittest discover -s scripts/gcp -p 'test_*.py'
python scripts/gcp/validate_compose.py
promtool check rules deploy/observability/prometheus/alerts.yaml
promtool test rules deploy/observability/prometheus/alerts-test.yaml
```

Agregar pruebas nuevas del arranque/pipeline de A1/A2 a las invocaciones apropiadas. La CI completa sigue siendo el gate de integración; registrar cualquier fallo arquitectónico existente sin debilitarlo. `tofu fmt/init -backend=false/validate` solo si se modifica IaC, en validación aislada y sin estado/variables reales. No instalar Docker ni levantar el stack del usuario para validar un cambio exclusivamente documental.

| Gate | Evidencia exigida para Done |
| --- | --- |
| Dos casos y perfiles | Ambos endpoints consumen Redis; TTL distintos y expiración real. |
| Distribución | Dos procesos independientes y smoke GCP A→B/B→A, ambos casos. |
| Corrección | Invalidación por versión confirmada, rollback/carreras, histórico, borrador, zona viva, seguridad y cálculo preservados. |
| Degradación | Fallback, presupuesto medido, TLS/AUTH y recuperación probados sin afectar datos compartidos. |
| Métricas | Una decisión por lectura; nombres/labels reales; inicialización y reseteo correctos; errores y bypass separados. |
| Grafana | Dashboard existente con métricas reales, tasas/cantidades/ratio por caso y total ponderado; estados sin tráfico/sin telemetría claros; navegador y consultas adjuntos. |
| Beneficio | Comparación reproducible de lecturas grandes y latencia con/sin caché; sin afirmaciones no medidas. |
| Redis en B y ciclo | R0–R7 aceptados: capacidad bajo carga, único contenedor en B, TLS/AUTH desde A/B, stop/14400 s, reinicio vacío, Memorystore retirado y sin referencias activas. |
| Entrega | Tests/CI de los SHAs entregados, runbook y card con resultados actuales; pendientes no ocultos. |

## 8. Restricciones y recuperación

- Conservar permisos/RLS, cuotas PostgreSQL, concurrencia optimista, B1–B5 y selector selección → ajuste → guardado → reapertura. No iniciar CU08/CU09/rediseño por este cierre.
- Mapbox mantiene permanent=false, sin almacenar resultados temporales; Geoapify geocodificación/routing sin consumo real en tests. No transformar la caché local geográfica ni los cálculos de admisión en los dos casos Redis.
- Sin compatibilidad con releases/contratos anteriores ni aliases nuevos. No borrar migraciones, datos, SQL peering, discos o volúmenes para recuperar servicios.
- Recuperación coordinada: deshabilitar Caching.Enabled en A/B mediante la configuración de despliegue autorizada, comprobar bypass y lecturas PostgreSQL; conservar datos/reglas y diagnóstico. No desactivar TLS para hacer funcionar Redis.
- El Redis de B no tendrá réplica; si B cae, la API de A debe degradar a PostgreSQL. Prometheus/Loki/Tempo siguen dependiendo de A. No instalar otro Redis en A ni Sentinel/Cluster para ocultar esa dependencia. La sección 9 exige señales de recursos/evicciones para operar el nuevo servicio; un exporter adicional solo si esas señales no se pueden obtener con el agente existente.

Referencias técnicas primarias consultadas para este cierre: [IDistributedCache y proveedor Redis](https://learn.microsoft.com/en-us/aspnet/core/performance/caching/distributed?view=aspnetcore-10.0), [configuración de StackExchange.Redis](https://seredis.dev/Configuration.html), [TLS y CA de Memorystore](https://docs.cloud.google.com/memorystore/docs/redis/about-in-transit-encryption), [capacidad y facturación de Memorystore](https://cloud.google.com/memorystore/docs/redis/pricing). Las versiones del checkout y los resultados medidos prevalecen sobre ejemplos de documentación de versiones más nuevas.

## 9. Migración de Redis a VM B y ciclo de cuatro horas

### Decisión, alcance y capacidad comprobada

La decisión del usuario es **mover todo el servicio Redis a B**, con las dos cachés de negocio y ambas APIs como clientes. No significa trasladar brokers, MongoDB, SQL, Prometheus, Loki o Tempo a B. No crear una VM nueva, un segundo Redis en A ni un selector permanente de proveedores. Se admite un corte coordinado y empezar con caché vacía.

La [auditoría del 06/11](../auditorias/nfr-07/2026-11-06-capacidad-vm-b.md) registra:

- B: 6 vCPU y 16 GiB provisionados, 16000,8 MiB utilizables; 12 contenedores activos.
- MemAvailable mínimo durante el muestreo: **13048,4 MiB ≈12,74 GiB**; sin presión PSI sostenida ni OOMKilled en el estado actual de los contenedores.
- Ventana retrospectiva de 24 h, con muestras disponibles: CPU p95 **12,617%**, mayor promedio de un minuto **42,820%**; memoria usada máxima **20,473%**. Cobertura 826 muestras CPU/829 RAM; no asumir 24 horas continuas ni pico instantáneo.
- Límites Docker actuales suman **8320 MiB**. Con Redis de 512 MiB y reserva presupuestaria SO/agentes de 2048 MiB quedarían **5120,8 MiB** de margen frente a RAM utilizable. No son reservas garantizadas.
- Grafana B ya registra **444,6/512 MiB** (86,84% de su límite). Es un límite por contenedor que debe observarse, sin ampliar este trabajo a cambiar Grafana por rutina.

**Conclusión de capacidad:** alcanza para preparar y probar Redis en B con los límites siguientes, sin ampliar la VM. No afirmar ausencia de problemas bajo toda carga: R4/R6 deben validar la carga representativa y conservar el margen del host.

### Contrato final de infraestructura

| Elemento | Destino requerido |
| --- | --- |
| Ubicación | Un contenedor `redis` solamente en `nexoruta-demo-b`. |
| Clientes | API A y API B; ambas usan el mismo DNS privado de B y namespace actual. |
| Endpoint | `nexoruta-demo-b.<secondary_zone>.c.<project_id>.internal:6378`. En el inventario actual, secondary_zone=southamerica-west1-b. Resolver dinámicamente; no copiar la IP de Memorystore. |
| TLS/AUTH | TLS servidor y contraseña/ACL; SAN del certificado incluye el DNS privado exacto. Puerto plaintext deshabilitado. Mantener verificación de CA y nombre. |
| Capacidad inicial | Redis maxmemory=256 MiB, allkeys-lru; límite Docker 512 MiB; cuota cpus=1.0; límite de PIDs 64; maxclients=128. |
| Margen del proceso | maxmemory no cubre por sí solo RSS, TLS, buffers y fragmentación. Configurar `maxmemory-clients 64mb`, disponible en Redis 7.2.16, y validar bajo payload máximo. |
| Persistencia | `save ""`, `appendonly no`; `/data` temporal, sin RDB/AOF, sin nuevo volumen durable. El origen es PostgreSQL. |
| Inicio | El workflow prepara B y reconcilia Redis antes de habilitar las APIs nuevas; arranque normal de Docker conserva restart policy unless-stopped. |
| Stop | El stop de la demo detiene ambas VMs y con B su Redis. No depende de un job GitHub que espere cuatro horas. |
| Límite temporal | Conservar STOP/14400 s, automaticRestart=false y lease/guard común existentes. Update no reinicia VMs ni renueva el plazo. |
| Reinicio de sesión | Redis vuelve vacío, clientes reconectan y rellenan desde PostgreSQL. Los TTL son máximos de vida de entradas, no promesa de conservarlas entre sesiones. |
| Servicio administrado | Retirar Memorystore después de aceptar Redis B. No conservarlo aprovisionado como respaldo permanente. |

Los límites son valores de partida explícitos, no mediciones de Redis. Una CPU de cuota representa hasta 16,67% del host de seis vCPU; no equivale a reservarle una CPU exclusiva. Los secretos y discos conservados continúan su ciclo y eventual facturación propios; detener B elimina el cómputo Redis, no todos los costos del proyecto.

### R0 — Revalidar capacidad y fijar la evidencia

1. Repetir inventario, muestreo de host y consulta histórica como en la auditoría si cambia la release/carga o pasó otra sesión. No iniciar una VM apagada solo para redactar el plan.
2. Registrar los 12 servicios actuales y sus límites, procesos de host, MemAvailable/PSI, CPU por intervalo y cobertura de Monitoring. Comparar límites previstos con RAM, incluyendo SO y agentes.
3. Gates previos: al menos 2 GiB de MemAvailable de margen después del presupuesto Redis, CPU p95 histórica <70% y sin saturación sostenida conocida; si falta histórico suficiente, dejarlo explícito y ampliar el ensayo posterior. No usar medias de VM apagada como ceros.
4. Entregar `capacity-before` fechado con SHAs, cargas observadas y límites elegidos; no reutilizar esta auditoría como si se hubiera repetido.

### R1 — Credenciales, DNS, red e IaC sin romper SQL

Archivos: `infra/gcp/bootstrap/delivery.tf`, `infra/gcp/demo/database.tf`, `main.tf`/`load-balancer.tf`, `scripts/gcp/github_environment.py`; agregar `scripts/gcp/redis_identity.py` y sus pruebas siguiendo el patrón de `hosting_identity.py`.

1. Crear un secreto dedicado `nexoruta-demo-redis` en Secret Manager. Generación serializada por el mismo bloqueo/concurrency de despliegue: contraseña aleatoria fuerte, CA privada dedicada y certificado de servidor con SAN DNS de B. No reutilizar el certificado de DataProtection ni la clave de Grafana. Guardar en el secreto contraseña, CA pública, certificado/cadena del servidor, clave privada del servidor, nombre DNS y vencimiento; no es necesario conservar la clave privada de CA si no se reutiliza para emitir certificados.
2. Patrón ensure: crear solo si no existe; validar formato, par clave/certificado, cadena, SAN y vencimiento del existente. Una versión inválida o próxima a vencer requiere renovación deliberada y coordinada; no regenerar en cada start/update. La CA y las credenciales deben sobrevivir a stop/start. No imprimir PEM, contraseñas ni respuestas completas de Secret Manager.
3. El deployer materializa en A solo configuración cliente (AUTH/CA); en B además certificado/clave del servidor y ACL/configuración privadas. Directorios 0700 y archivos privados con dueño/grupo apropiados al UID no root de la imagen. Las dos VMs comparten hoy la misma service account: **no afirmar que IAM aísla la clave por nodo**. Limitar el material escrito/montado y conservar permisos existentes; separar identidades IAM sería otro cambio deliberado.
4. El runtime pasa a publicar `redis.host` = DNS privado de B y `redis.port`=6378; el helper de identidad provee AUTH/CA. Actualizar productores, validadores y consumidores juntos; eliminar la dependencia de `google_redis_instance.cache.host/auth_string/server_ca_certs` del contrato final. No agregar `RedisProvider=memorystore/vm` ni fallback a la dirección vieja.
5. Evitar ciclo Terraform: el secreto runtime ya es dependencia de ambas VMs; construir el DNS desde nombres/zona/proyecto, sin referenciar el recurso VM B desde ese mismo secreto.
6. Agregar una regla de firewall específica TCP/6378, origen las VMs de aplicación mediante su tag existente y destino un tag exclusivo de B para Redis. Mantener salida/resolución privada. No agregar 6378 al acceso público ni al balanceador. No ampliar indiscriminadamente la regla de todos los servicios compartidos.
7. Actualizar validadores hoy limitados a IP privada Memorystore: aceptar **solo el DNS de B derivado del inventario**, resolverlo y comprobar direcciones dentro de la subred privada esperada. No aceptar un hostname arbitrario por pasar un regex. Usar ese DNS como sslHost/SNI para ambos clientes.
8. Conservar Service Networking, rango PSA y peering usados por Cloud SQL. Eliminar Memorystore del estado/recursos solo en R7. Durante la primera entrega su declaración puede permanecer para evitar borrarlo antes de aceptar B, pero ninguna API nueva lo usa. Es una transición operativa acotada, sin contratos paralelos de aplicación.

**Pruebas:** secreto ausente/existente/inválido, SAN incorrecto, caducidad, estabilidad entre ejecuciones, permisos sin fugas; DNS inesperado/resolución pública rechazada; plan sin reemplazo de VM/SQL/peering; regla Redis solo hacia B.

### R2 — Contenedor Redis y presupuesto real

Archivos: agregar `deploy/gcp/redis/redis.conf` y plantilla/entrada de arranque privada; editar `deploy/gcp/compose.yaml`, bundle de `scripts/gcp/delivery.py` y validador Compose. Reutilizar Redis 7.2.16 ya fijado por el proyecto; fijar imagen por digest verificado y probar TLS en esa imagen. No introducir actualización de versión ajena a la migración.

1. Servicio con perfil propio, por ejemplo `cache-b`; no incorporarlo al perfil shared de A ni a APPS, que se recrea en ambos nodos. Publicar exclusivamente `${NODE_PRIVATE_IP}:6378:6378` cuando se despliega en B. Ningún contenedor Redis en A.
2. Configurar `port 0`, `tls-port 6378`, `tls-auth-clients no` para TLS servidor + AUTH, archivos de certificado/clave/CA de solo lectura y protected-mode. Mantener el usuario default únicamente autenticado, con ACL/contraseña protegida y patrón del namespace requerido, compatible con el contrato cliente actual sin username nuevo. Conceder comandos usados por el proveedor fijado, conexión y probes. Verificarlos contra lecturas/escrituras reales del paquete, sin adivinar una lista incompatible con sus operaciones hash/scripts. No permitir FLUSHALL/FLUSHDB/CONFIG/SHUTDOWN a la credencial runtime. El stop lo administra Docker.
3. Redis maxmemory `256mb`, allkeys-lru, clientes y buffers acotados; límite Docker `512m`, `memswap_limit=512m`, cpus=1.0, pids_limit=64, sin privilegios/capabilities adicionales y usuario no root. El host no tiene swap actualmente; el límite no debe asumir que existe.
4. `save ""`, `appendonly no`, dir `/data` temporal. Montar tmpfs acotado en `/data` para evitar que el VOLUME de la imagen cree almacenamiento anónimo durable, y tmpfs pequeño en `/tmp` si hace falta. Conservar solo configuración/identidad privadas fuera del contenedor; no crear volumen de datos nuevo ni borrar volúmenes existentes.
5. Healthcheck local hace PING con TLS, CA/SNI y AUTH; no una conexión TCP sin autenticar. Leer contraseña de archivo protegido o entorno efímero del probe, sin literal en argumentos/healthcheck inspeccionable y sin devolverla en logs. No asumir que --sni reemplaza la validación de nombre: comprobar negativos con certificado de otro nombre y validar con cliente que lo compruebe.
6. restart unless-stopped, stop_grace_period finito y prueba de SIGTERM. Los permisos de mounts deben permitir leer la clave al UID/GID real de la imagen, sin chmod 777 ni ejecutar Redis como root para evitar resolver permisos.
7. El volumen de caché es reemplazable; no tocar el `redis_data` local ni aplicar esta migración a Compose de desarrollo sin necesidad. El contrato de las dos cachés, TTL y límite de payload de aplicación permanecen iguales.

**Pruebas:** Compose/bundle completos, recursos aplicados en docker inspect seleccionado, TLS/AUTH válidos e inválidos, hostname correcto/incorrecto, acceso plaintext rechazado, ACL/proveedor compatibles, payload próximo a 2 MiB, evicción bajo límite, RSS/buffers y apagado. No publicar salidas completas de inspect/config que contengan secretos.

### R3 — Deployer por nodo y orden de operaciones

Archivos: `scripts/gcp/vm_deploy.py`, `delivery.py`, `github_environment.py`, `.github/workflows/vm-controls.yml` si requiere integración; tests de estos módulos.

1. Expresar servicios por nodo de forma explícita: shared actual permanece en A; Redis pertenece a B. Actualizar pull, validación de perfiles, prepare, reconcile y pruebas. Hoy `SHARED if node == a` y `APPS` no permiten ubicar Redis solo en B por agregarlo a una lista existente.
2. `prepare B` escribe configuración privada y reconcilia Redis desde la release seleccionada con su perfil. No hacer solamente docker start de un contenedor antiguo: cambios de configuración, imagen, mounts, límites y TLS deben aplicarse con Compose. Recrear solo cuando cambia la configuración/imagen; no vaciar la caché por cada verificación o por preparar A.
3. Añadir una comprobación explícita después de preparar B: TLS/AUTH y una operación efímera en namespace reservado de smoke, con TTL y eliminación de **esa clave exacta**. Verificar acceso desde A y desde B; no dejar datos de smoke ni usar FLUSH/KEYS. El gate de despliegue puede fallar por configuración Redis inválida, sin convertir Redis en dependencia de readiness de negocio.
4. Revisar el orden en `delivery.deploy`: actualmente prepara A y después B, detiene APPS en ambos, migra en A y aplica B→A. Mantener esa secuencia si `prepare A` no exige aún que Redis B esté listo; ejecutar el gate Redis cuando ambos prepares terminaron y antes de admitir APIs nuevas. Alternativamente preparar Redis B en una etapa explícita previa; documentar una sola secuencia y probarla.
5. El stage stop de aplicaciones durante un update no debe detener Redis por estar en APPS. Un update no reinicia la VM ni extiende lease/deadline. El stop de sesión sí detiene ambas VMs mediante el flujo existente y con ello Redis B.
6. Añadir al resumen de despliegue nodo Redis=b, endpoint lógico validado, release y resultado de probes, sin credenciales. Ambas APIs deben usar exactamente el mismo servidor/namespace; no dejar A en Memorystore por error.
7. En reinicio de B, Docker inicia Redis con identidad persistida pero datos vacíos. Durante indisponibilidad, API A conserva fallback a PostgreSQL y recupera Redis sin reinicio. No hacer depender el arranque de Redis de un proceso de GitHub que deba seguir vivo.

**Pruebas:** presencia solo en B, prepare idempotente, configuración nueva reconciliada, B no listo, ambos clientes, update sin reiniciar ni ampliar plazo, APPS-stop conserva Redis y session-stop apaga B. Mantener CI y publicación por gitlinks exactos.

### R4 — Monitoreo y aceptación de recursos en fixture

Archivos: `scripts/gcp/monitor_agent.py`, sus tests, dashboard canónico/copia y runbooks. No mover Prometheus de A.

1. El inventario esperado de contenedores debe incluir redis **solo en B**; hoy INFRASTRUCTURE solo se añade en A. Reportar container_up/restarts/OOM de B y no alertar por «Redis ausente» en A.
2. Sustituir la semántica actual de `service=redis` basada solo en TCP por una comprobación TLS/CA/nombre/AUTH/PING desde cada nodo, con timeout finito. Si se conserva señal TCP adicional, nombrarla redis_tcp y actualizar consultas/tests; no presentarla como salud autenticada. No etiquetar con host/clave/operador/exception message.
3. Usar señales de host y cgroup para memoria/RSS, CPU/throttling, reinicios/OOM. Obtener INFO memory/stats/clients con cliente autenticado desde B para used_memory, used_memory_rss, maxmemory, evicted_keys y connected_clients; preferir el agente existente, con timeouts y muestras acotadas. Exporter adicional solo si se justifica, con límite propio y presupuesto actualizado.
4. Hits/misses de negocio siguen siendo los instrumentos de las APIs. No sustituirlos por keyspace_hits/misses del servidor. TTL/expulsión y reinicio pueden producir misses legítimos.
5. Probar en fixture el Redis de la imagen/configuración final con los límites exactos, TLS y logos/tarifarios representativos de A4. Registrar cliente, servidor y host. No usar redis-benchmark contra la demo compartida.
6. Gates para carga representativa: MemAvailable ≥2 GiB; CPU p95 host <70% y sin ≥85% sostenido cinco minutos; sin OOM ni PSI de memoria sostenida; Redis RSS <80% de 512 MiB en la fase estable y sin desconexiones/errores inducidos por buffers o cuota. Comparar p95 de endpoints con la línea base: investigar regresión >10% y >20 ms simultáneamente, sostenida en repeticiones; distinguir ruido y red de falta de recursos.
7. Throttling aislado no es fallo por sí solo; si coincide con incumplimiento de latencia, medir y ajustar cuota dentro del presupuesto del host y repetir gates. Evicciones bajo presión controlada deben generar miss/origen, sin pérdida de datos ni OOM. Si no se cumplen gates, reducir dataset/cache, resolver carga o revisar recursos antes de retirar Memorystore; no ampliar VM/cuota silenciosamente.

### R5 — Primera entrega: Redis B activo, Memorystore aún sin retirar

1. Entregar código/configuración/tests de R1–R4 y A1–A4. Mantener temporalmente la declaración del recurso Memorystore para no destruirlo antes de validar B; el contrato de aplicación de esta entrega ya tiene como único destino B.
2. Aplicar bootstrap para el secreto/permisos y luego inicializar identidad. Aplicar un plan demo revisado **sin deletes/replaces** para firewall/tag y contrato runtime. No ejecutar start sobre una sesión activa para aplicar infraestructura: start rechaza VMs ya encendidas. Update aplica bootstrap, pero no el plan demo; preparar la aplicación de ese plan de mantenimiento con el backend/lock/variables y deadline de la sesión, o hacerla en el siguiente start permitido.
3. El plan no debe reemplazar VMs/SQL/discos, modificar scheduling/lease para alargar el plazo ni rotar credenciales de otras funciones. No guardar tfplan/tfstate en Git/artifacts públicos: contienen secretos.
4. Desplegar una release inmutable con ambos clientes a B, gate autenticado, luego A3/A5. Verificar no hay contenedor Redis en A, que B tiene los límites previstos y que no hay conexiones de las APIs al endpoint administrado. Las conexiones o una sonda del agente antiguo no deben confundirse con consumo de caché; comprobar configuración efectiva de cada proceso.
5. Ejecutar al menos diez minutos de carga sintética controlada, cinco usuarios concurrentes repartidos entre APIs y ambos casos; comparar capacity-before/after y los gates R4. Mapbox/Geoapify controlados, sin consumo real ni cambios a datos ajenos.
6. Recoger métricas reales y capturas de Grafana. No retirar Memorystore si falta smoke cruzado, capacidad bajo carga o recuperación del cliente.

Esta coexistencia es únicamente el orden de migración del recurso, no compatibilidad de releases ni un modo de dos proveedores. Conservar una tarea de retiro obligatoria para evitar seguir pagando el recurso abandonado.

### R6 — Stop, cuatro horas y recuperación

Hacer los ensayos en una ventana de demo identificada. No detener VMs de una sesión ajena para verificar este plan.

| Ensayo | Procedimiento y resultado exigido |
| --- | --- |
| Stop manual | Usar el workflow existente, operation=stop. Confirmar ambas VMs TERMINATED; Redis B deja de atender. Registrar estado Compute y hora, sin presentar timeout de red como prueba suficiente de apagado. |
| Arranque posterior | Usar start con las VMs detenidas. Redis B arranca con identidad válida y datos vacíos; confirmar miss y después hit entre A/B, sin migrar datos de caché. PostgreSQL conserva los datos de negocio. |
| Update | Comparar lastStartTimestamp, deadline y lease antes/después: sin reinicio de VM ni extensión. Redis conserva proceso/datos si su configuración no cambió; si cambia, una recreación explícita puede vaciarlo y debe observarse como miss legítimo. |
| Límite de cuatro horas | Tests de infraestructura/guard comprueban max_run_duration=14400 y STOP de B; tests de vencimiento ejercitan el guard sin esperas largas. Completar una observación real del vencimiento en sesión de aceptación y registrar hora límite/TERMINATED; no afirmar cuatro horas verificadas solo por leer HCL. La observación puede continuar después de terminar el job de despliegue. |
| B ausente | Ensayo de fallo en fixture demuestra que API A sirve desde PostgreSQL dentro del presupuesto, aumenta error/bypass según su decisión y reconecta cuando B vuelve. La API B estará indisponible si su VM está apagada; no prometer alta disponibilidad total. |

No crear un scheduler nuevo que apague solo Redis ni un job GitHub durmiendo cuatro horas. El límite de Compute y guard existentes gobiernan B y todos sus contenedores. Si se desconecta Docker o el host se apaga abruptamente, la falta de persistencia de caché no puede afectar datos de negocio.

### R7 — Retiro deliberado de Memorystore y finalización

1. Solo tras R5/R6 aceptados, preparar la segunda entrega que elimina `google_redis_instance.cache` de `infra/gcp/demo/database.tf` y cualquier referencia activa a sus atributos. Mantener contrato B y secreto de identidad. Actualizar docs y pruebas para que no sugieran que el próximo start recreará Memorystore.
2. **Resolver el guard existente:** `demo_session.check_plan()` rechaza cualquier delete de recursos. No desactivarlo ni agregar un allow-delete global a start/stop/update. Retirar el recurso con una operación manual de mantenimiento que revise y aplique un plan guardado; si se automatiza, un validador específico solo acepta delete del recurso `google_redis_instance.cache` con identidad/proyecto/región esperados, además de los cambios no destructivos revisados y versiones de secreto con ABANDON ya permitidas.
3. El resumen sanitizado debe enumerar direcciones/tipos/acciones y rechazar cualquier otro delete/replace, especialmente SQL, discos, Service Networking, secretos o buckets. No imprimir valores before/after de secretos para revisar ese resumen. Usar bloqueo del estado y la misma serialización de operaciones de demo; no ejecutar tofu destroy global, state rm ni gcloud delete por fuera de IaC como sustituto de un plan coherente.
4. Verificar que ninguna API/probe usa el endpoint anterior antes de aplicar. El borrado pierde las entradas de ese Redis, deliberadamente reemplazables por PostgreSQL; no autoriza borrar ninguna otra base ni volumen. No exportar ni importar snapshots de caché.
5. Aplicar el plan de retiro revisado. Confirmar por inventario que Memorystore ya no existe y con un plan posterior que no se vuelve a crear. Asegurar que no quedan jobs, secrets runtime o alertas que sigan apuntando al endpoint administrado; versiones históricas de secretos se conservan según su política, sin montarlas ni usarlas como fallback.
6. Mantener las APIs/Service Networking que SQL u otros recursos usan. Si se retira la habilitación redis.googleapis.com del catálogo IaC, comprobar antes que no hay otros consumidores y no deshabilitar servicios compartidos como limpieza incidental.
7. Repetir smoke A→B/B→A y un stop/start con la infraestructura final, sin Memorystore. Comprobar que la caché sigue sirviendo y las métricas llegan. Verificar facturación posterior con su demora de ingestión: no confundir cargos históricos con un recurso todavía aprovisionado.
8. Recuperación de la migración: antes del retiro, ante fallo servir temporalmente con Caching.Enabled=false en A/B y corregir B, sin selector automático de proveedor. Después del retiro hacer lo mismo; no recrear Memorystore ni reintroducir aliases para recuperar disponibilidad de negocio.

### R8 — Entrega del agente y checklist adicional

Entregar commits/SHAs, archivos, esquema final de red/credenciales, capacity-before/after, gates bajo carga, probes y matrices A3/R6; consultas y capturas reales; plan sanitizado de retiro y comprobación de ausencia posterior. Actualizar la card y los runbooks solo con operaciones efectivamente realizadas. Este documento planifica esas acciones: **en esta revisión solo se midió capacidad y se editaron documentos**.

- [ ] Un Redis únicamente en B; ambas APIs usan el mismo endpoint/namespace y conservan sus dos casos.
- [ ] Host y contenedor dentro de presupuesto con cinco usuarios, TLS y payloads representativos; Grafana B observado por separado.
- [ ] Firewall privado, TLS/hostname/AUTH/ACL y secretos persistentes correctos; sin claves privadas materializadas en A.
- [ ] Despliegue/start/update/stop y guard funcionan con la ubicación B; update no renueva la sesión.
- [ ] Stop manual y vencimiento real dejan B apagada; start recupera Redis vacío y miss→hit compartido.
- [ ] API A degrada y recupera Redis sin perder corrección/RLS cuando B falla.
- [ ] Métricas de negocio y recursos aparecen en el Grafana existente con nodos/casos bien identificados.
- [ ] Memorystore retirado mediante plan deliberado y no reaparece en el siguiente start; sin referencias activas al proveedor anterior.

Referencias primarias para la implementación: [configuración exacta Redis 7.2.16](https://raw.githubusercontent.com/redis/redis/7.2.16/redis.conf), [configuración de Redis](https://redis.io/docs/latest/operate/oss_and_stack/management/config/), [TLS Redis](https://redis.io/docs/latest/operate/oss_and_stack/management/security/encryption/), [evicción y maxmemory](https://redis.io/docs/latest/develop/reference/eviction/), [límites de recursos Docker](https://docs.docker.com/engine/containers/resource_constraints/), [eliminación/recreación de Memorystore y cambio de IP](https://docs.cloud.google.com/memorystore/docs/redis/create-manage-instances). Verificar cada opción contra Redis 7.2.16, no copiar opciones exclusivas de versiones nuevas.
