# NFR-12 / §6.12 — Implementación y evidencia de observabilidad

Fecha: 14/11/2026. Estado: **implementado y validado localmente; el GCP actual está sano, pero el release desplegado no incluye estos cambios NFR-12. Falta integrar/publicar el cambio y aceptación en dispositivo**.

El alcance corresponde al requisito facilitado por el usuario: Serilog estructurado, OpenTelemetry para métricas/trazas, correlación Mobile→API→worker y un tablero con media/p95/p99 HTTP, errores, cola, pendientes Mobile, avisos comerciales fallidos y aciertos del caché.

## 1. Resultado

La implementación completa las brechas de contexto SQL/Kafka/HTTP, añade el snapshot persistente de sincronización Mobile, conecta `worker-webhooks` a OTLP en Compose local y GCP, y amplía el dashboard y las alertas compartidas. Se conservaron el UID del dashboard (`nexoruta-demo`), los datasources, las políticas RLS y las migraciones históricas.

“Validado localmente” aquí significa compilación, pruebas con PostgreSQL desechable, Compose validado sin arrancar los servicios del usuario y revisión del dashboard en un stack de observabilidad aislado con métricas sintéticas. La comprobación GCP del 14/11 confirma salud del release remoto actual, no de este cambio local.

## 2. Cambios implementados

### Mobile y correlación

- Mobile usa Serilog JSON con rotación diaria y límite de tamaño; incluye `trace_id` y `span_id` en los eventos.
- `ActivitySource` instrumenta la operación móvil, los intentos HTTP y las respuestas. La proporción de muestreo se configura con `NEXORUTA_OTEL_SAMPLING_RATIO` (por defecto 100% Debug y 10% Release).
- SQLite cifrado v2 persiste el `traceparent` por operación y crea una identidad/secuencia de instalación en metadatos cifrados. Reintentos y reaperturas conservan la traza original.
- La sincronización envía el contexto W3C en los requests y reporta pendientes antes/después del intento de forma best-effort; un fallo del reporte no bloquea el trabajo de negocio.
- El endpoint autenticado `POST /api/mobile/sync-status` sólo acepta el actor operador validado. La secuencia es monotónica, los reportes atrasados devuelven 409 y cada acceso sólo modifica su propio snapshot mediante RLS.

### API, PostgreSQL y workers

- `RlsTransaction` establece el `traceparent` validado en contexto transaccional. Una migración nueva conserva el contexto en el outbox operativo creado por trigger SQL y en `WebhookDeliveries`, fuera del payload comercial firmado.
- Publicadores y consumidores Kafka propagan/restauran W3C y abren spans/scope estructurados con el ID de correlación de negocio.
- Cada entrega HTTP crea un span consumidor, propaga W3C al receptor y registra el resultado sin URL, body, firma ni secreto. El contador de intentos fallidos quedó separado de los estados terminales.
- `worker-webhooks` exporta OTLP en local y GCP. En local tiene healthcheck; en GCP se incluye en arranque, monitorización y comprobaciones de release.
- El worker HTTP consulta cada 30 s una función SQL `SECURITY DEFINER` que devuelve sólo agregados. El rol restringido recibe `EXECUTE`; la función lee los snapshots con políticas RLS y no expone filas o identidades individuales.
- Los snapshots Mobile cuentan pendientes de los reportes de los últimos cinco minutos y muestran instalaciones vencidas. Un reporte nuevo limpia filas del mismo acceso con más de 30 días; una instalación sin actividad sigue visible como vencida hasta que llegue otro reporte. Ausencia de reporte no se trata como cero.

### Dashboard y alertas

La fuente canónica sigue siendo [nexoruta.json](../../deploy/observability/grafana/nexoruta.json), sincronizada con la copia de GCP. Conserva media, p95/p99 y 5xx, y ahora diferencia:

- Profundidad de RabbitMQ y estados de entrega HTTP.
- Intentos HTTP fallidos frente a entregas `Fallido` terminales.
- Pendientes Mobile recientes, instalaciones frescas/vencidas, antigüedad y disponibilidad del snapshot.
- Ratio de caché y las señales previas de logs, trazas, workers e infraestructura.

Las nuevas alertas cubren entregas terminales fallidas y falta del snapshot Mobile; sus reglas de disparo/recuperación están en [alerts-test.yaml](../../deploy/observability/prometheus/alerts-test.yaml). Las reglas y el dashboard canónico se copian a GCP.

## 3. Límites de configuración

- GCP ya declara el worker y el pipeline de observabilidad. La variable opcional `WEBHOOK_ALLOWED_ORIGINS` del entorno GitHub `nexoruta-demo` se sincroniza a API y worker como orígenes HTTPS exactos separados por `;`. Sigue vacía hasta que se definan destinos reales; la política deniega por defecto y no se habilitó egress genérico.
- No se abrió OTLP a Internet ni se agregó una cola de exportación Mobile. El teléfono conserva el contexto/log local; los spans de servidor se exportan al Collector al reconectar. La demostración con un dispositivo Android físico sigue pendiente.
- Los percentiles del ensayo visual proceden de métricas sintéticas y sólo validan consulta/unidad/presentación. No son un benchmark ni prueban una carga de producción.

## 4. Verificación local realizada

| Capa | Evidencia |
|---|---|
| Backend | `dotnet build backend/NexoRuta.sln --no-restore`: compilación correcta, 0 errores. `NexoRuta.UnitTests`: **381 aprobadas**. Permanece NU1510 y avisos de análisis preexistentes en pruebas. |
| Integración PostgreSQL | `WebhooksHttpTests`: **5 aprobadas**; la migración nueva se aplicó en PostgreSQL desechable. La prueba añadida verifica el endpoint Mobile (actualización, cero final y 409 atrasado), continuidad del trace ID hasta `WebhookDeliveries`, lectura del snapshot con el rol worker restringido y recuperación de trace/correlación al reclamar la entrega. |
| Mobile | `dotnet test mobile/NexoRuta.sln --no-restore --filter FullyQualifiedName~NexoRuta.Mobile`: **239 aprobadas**; también compiló el target Android. Persistencia cifrada, reinstalación lógica de jornada y reintentos cubiertos. |
| Reglas Prometheus | `promtool check rules` encontró 14 reglas; `promtool test rules` pasó los casos, incluidos disparo y recuperación de alertas nuevas. |
| Regresión de despliegue | `test_delivery` y `test_vm_deploy`: **65 pruebas Python aprobadas**, incluidas configuración de orígenes exactos, dashboard compartido, límites del collector GCP e inclusión de `worker-webhooks` en ambos ambientes/inventarios. |
| Compose | `docker compose -f compose.yaml -f compose.override.yaml config --quiet` pasó. GCP Compose pasó con un archivo temporal de valores sintéticos; no se leyeron credenciales GCP. No se ejecutó `up` sobre la pila existente. |
| HTTP y Prometheus | El stack efímero respondió Grafana `/api/health` 200 en versión 13.2.3, Prometheus `/-/ready` listo y target sintético `up`. Consultas directas devolvieron media/p95 y métricas de backlog/estados. |
| BrowserAct | Revisé el dashboard compartido en Chrome con métricas sintéticas: filtros, carga de paneles, media/p95/p99, tasa 5xx, backlog Mobile, caché, cola y estados de webhook. Las consultas se vieron en la interfaz; no se usó el Grafana de los contenedores activos del usuario. |
| GCP existente | El workflow [43616743052](https://github.com/NexoRuta/NexoRuta/actions/runs/43616743052) terminó `success` para el commit `4b478f0`; publicó `release-2c9f1ca79ad547548b2f79662c922f1a`. A/B estaban `RUNNING`, los siete backends del balanceador `HEALTHY`, `/api/health` de Grafana respondió 200 y Cloud Monitoring reportó probes recientes `1`, además de Prometheus, Grafana y Collector activos. La ruta del dashboard sin sesión redirige a `/login`; no inspeccioné paneles autenticados en el GCP real. |

El release GCP no contiene este cambio NFR-12: el commit `4b478f0` sólo cambia permisos de la fixture de carga; sus gitlinks apuntan a Backend `425634e` y Mobile `840a557`. Esos árboles no tienen el controller/snapshot Mobile ni `TelemetryMovil`; el Compose desplegado no declara `worker-webhooks`, y las series recientes de contenedores tampoco lo incluyen. El dashboard remoto conserva HTTP media/p95/p99, 5xx, histogramas de pendientes Mobile, Rabbit/Kafka y caché. Tiene un panel genérico de fallos de notificaciones basado en `nexoruta_commerce_notifications_failed_total`, pero no las series nuevas de intentos HTTP fallidos (`nexoruta_commerce_notification_attempts_failed_total`) y entregas terminales por estado (`nexoruta_commerce_webhooks_deliveries`). No se actualizó GCP desde el checkout local durante esta comprobación.

El stack efímero usó Grafana `127.0.0.1:33000`, Prometheus `127.0.0.1:39090` y un exporter sintético `127.0.0.1:39100`; sus servicios y proceso se detienen al terminar la validación. Los puertos habituales 3000/9090 estaban ocupados sin listener en esta sesión; no se reiniciaron ni se modificaron contenedores, bases o volúmenes preexistentes.

## 5. Pendiente antes de cerrar NFR-12

- [ ] Ejecutar recorrido offline/reintento/cierre-reapertura desde Android/MAUI y confirmar el mismo trace ID en el registro Mobile y los spans de API/worker.
- [ ] Revisar tablero con tráfico real de la aplicación local, logs/trazas reales y receptor controlado; el ensayo BrowserAct de esta sesión usa exclusivamente series sintéticas.
- [ ] Verificar accesibilidad/reflow del dashboard a 320 px y zoom 200%; el navegador disponible se revisó a su viewport de escritorio.
- [ ] Definir y configurar los orígenes HTTPS permitidos por el equipo en `WEBHOOK_ALLOWED_ORIGINS` para el smoke de webhooks GCP, manteniendo la política de egress restringida.
- [ ] Integrar/publicar estos cambios sobre el `develop` actual antes de un `update` GCP. Este checkout local está 30 commits detrás de `origin/develop` y el cambio NFR-12 permanece sin commit; no desplegarlo desde esta punta vieja.
- [ ] Después del release NFR-12, comprobar ambos workers (incluido `worker-webhooks`), Collector/scrape, HTTPS/login y series Mobile/webhook recientes en ambos nodos.

No se actualizó ningún gitlink para la implementación local. La comprobación del release existente no sustituye la verificación del futuro release NFR-12. La aceptación en navegador tampoco sustituye la prueba nativa.
