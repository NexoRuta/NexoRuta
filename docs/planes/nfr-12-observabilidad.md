# NFR-12 / §6.12 — Implementación y evidencia de observabilidad

Fecha: 14/11/2026. Estado: **implementado, validado localmente y publicado en `develop` (`b21f5b3`); el rollout GCP queda pendiente porque los nodos A/B están `TERMINATED`**. El release `release-bd39c48fde2b49fa80b18a01f173ebd6` sigue siendo el último aplicado. La inspección autenticada detectó que Prometheus rechaza registros persistidos con `400 too old sample`, y no hay series recientes para los paneles de aplicación. La actualización del Collector a `0.165.0` está lista; falta iniciar una nueva sesión GCP, aplicar el release y confirmar que la WAL vuelve a avanzar. También falta recorrido nativo Mobile y smoke real de webhooks con destinos permitidos.

El alcance corresponde al requisito facilitado por el usuario: Serilog estructurado, OpenTelemetry para métricas/trazas, correlación Mobile→API→worker y un tablero con media/p95/p99 HTTP, errores, cola, pendientes Mobile, avisos comerciales fallidos y aciertos del caché.

## 1. Resultado

La implementación completa las brechas de contexto SQL/Kafka/HTTP, añade el snapshot persistente de sincronización Mobile, conecta `worker-webhooks` a OTLP en Compose local y GCP, y amplía el dashboard y las alertas compartidas. Se conservaron el UID del dashboard (`nexoruta-demo`), los datasources, las políticas RLS y las migraciones históricas.

“Validado localmente” aquí significa compilación, pruebas con PostgreSQL desechable, Compose validado sin arrancar los servicios del usuario y revisión del dashboard en un stack de observabilidad aislado con métricas sintéticas. La validación GCP posterior al despliegue está documentada en la sección 4; confirmó el release, los dos nodos, health HTTPS y el arranque de los servicios de observabilidad. No equivale a verificar las consultas del tablero autenticado ni a producir datos reales Mobile/webhook.

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
| Collector 0.165.0 | Se validó la configuración local y GCP con `otelcol-contrib validate`. En un stack Docker efímero, OTLP→Collector→exporter Prometheus local produjo `nfr12_observability_smoke_total` con valor `7`. `test_delivery`: **39 aprobadas**. |
| Remote-write y WAL local | El config GCP real, con puertos y destino sustituidos por un receptor efímero y un exporter debug adicional, aceptó OTLP `200`, observó el punto `Value: 7` y, tras la ventana predeterminada del WAL (70 s), envió `POST /api/v1/write` (`application/x-protobuf`, Remote-Write `0.1.0`). El receptor contestó `200`; el WAL efímero se limpió al cerrar el stack. |
| HTTP y Prometheus | El stack efímero respondió Grafana `/api/health` 200 en versión 13.2.3, Prometheus `/-/ready` listo y target sintético `up`. Consultas directas devolvieron media/p95 y métricas de backlog/estados. |
| BrowserAct | Revisé el dashboard compartido en Chrome con métricas sintéticas: filtros, carga de paneles, media/p95/p99, tasa 5xx, backlog Mobile, caché, cola y estados de webhook. Las consultas se vieron en la interfaz; no se usó el Grafana de los contenedores activos del usuario. |
| GCP antes del update (histórico) | El workflow [43616743052](https://github.com/NexoRuta/NexoRuta/actions/runs/43616743052) terminó `success` para el commit `4b478f0`; publicó `release-2c9f1ca79ad547548b2f79662c922f1a`. A/B estaban `RUNNING`, los siete backends del balanceador `HEALTHY` y `/api/health` de Grafana respondió 200. Ese release todavía no contenía NFR-12. |
| GCP post-update | El workflow [43631884438](https://github.com/NexoRuta/NexoRuta/actions/runs/43631884438) terminó `success` desde `develop` (`86e234e`) y publicó `release-bd39c48fde2b49fa80b18a01f173ebd6` (6 imágenes). `update` terminó en ambos nodos sin reiniciarlos ni extender la sesión; expiración original conservada. `worker-webhooks`, `otel-collector`, Grafana y los demás servicios `APPS` quedaron levantados en ambos nodos mediante `compose up --wait`; en A se reconciliaron y esperaron Prometheus, Prometheus Write Gateway, GCP Metrics Collector, Loki y Tempo. Las comprobaciones directas de API/admin/backoffice/commerce/tracking/monitor pasaron. Redis TLS/AUTH pasó desde A y B. Los backends del balanceador pasaron el gate en A y B; después del margen de propagación, admin/API/backoffice/commerce/tracking/monitor/mail quedaron saludables. El smoke HTTPS/login del nodo A pasó, incluidos los logins de base de datos de las cuentas bootstrap admin/operador/comercio. Probes externos: API `/ready` 200, tracking `/ready` 200, admin/backoffice/commerce `/ingresar` 200 y Grafana `/api/health` 200 (v13.2.3, database `ok`). |
| GCP antes del rollout correctivo (14/11) | `gcloud compute instances list`, filtrado por las etiquetas de NexoRuta/OpenTofu, devuelve `nexoruta-demo` y `nexoruta-demo-b` en `TERMINATED`. El workflow `update` requiere ambos nodos `RUNNING` y no abre ni extiende la sesión; no se despachó para evitar un build sin aplicación del release. Hace falta autorizar una nueva sesión para poder aplicar `b21f5b3`. |
| GCP Grafana autenticado (14/11) | BrowserAct en Chrome directo abrió `nexoruta-demo`, rango de 4 h. El panel de servicios y el de contenedores muestran A/B disponibles; Prometheus tiene `prometheus` y `gcp-cloud-metrics` `up`, y el marcador de release coincide con `release-bd39c48fde2b49fa80b18a01f173ebd6` en ambos nodos. Los paneles HTTP/media/p95/p99/5xx, Mobile, caché, workers, RabbitMQ scrapes y webhooks no tienen series recientes; también `increase(nexoruta_api_requests_total[5m])` quedó vacío. Loki muestra en el Collector del nodo A rechazos `400 Bad Request` con `error: too old sample` al enviar `/api/v1/write`. |

La observación del release `4b478f0` y sus gitlinks antiguos describe sólo el estado previo al update; fue sustituida por `release-bd39c48fde2b49fa80b18a01f173ebd6`. BrowserAct autenticó el Grafana GCP con la sesión autorizada del usuario y verificó los paneles. Aunque la disponibilidad de servicio/contenedor y las métricas GCP están vivas, Prometheus no recibe métricas recientes de aplicación. El Collector GCP está fijado en `0.164.0`; el fallo coincide con [el defecto upstream #51710](https://github.com/open-telemetry/opentelemetry-collector-contrib/issues/51710), donde un registro que el endpoint rechaza bloquea el avance de la WAL. La corrección upstream se integró en [51411b7](https://github.com/open-telemetry/opentelemetry-collector-contrib/commit/51411b7), incluida en `0.165.0`. La configuración se actualizó en local y GCP a esa versión, conservando el volumen `otelcol` y la WAL; rollout y reconsulta GCP siguen pendientes.

`WEBHOOK_ALLOWED_ORIGINS` no figura entre las variables del entorno `nexoruta-demo`, así que el egress sigue denegado por defecto y no se ejecutó una entrega real a un comercio.

El stack efímero usó Grafana `127.0.0.1:33000`, Prometheus `127.0.0.1:39090` y un exporter sintético `127.0.0.1:39100`; sus servicios y proceso se detienen al terminar la validación. Los puertos habituales 3000/9090 estaban ocupados sin listener en esta sesión; no se reiniciaron ni se modificaron contenedores, bases o volúmenes preexistentes.

## 5. Pendiente antes de cerrar NFR-12

- [ ] Ejecutar recorrido offline/reintento/cierre-reapertura desde Android/MAUI y confirmar el mismo trace ID en el registro Mobile y los spans de API/worker.
- [ ] Revisar tablero con tráfico real de la aplicación local, logs/trazas reales y receptor controlado; el ensayo BrowserAct de esta sesión usa exclusivamente series sintéticas.
- [ ] Verificar accesibilidad/reflow del dashboard a 320 px y zoom 200%; el navegador disponible se revisó a su viewport de escritorio.
- [ ] Definir y configurar los orígenes HTTPS permitidos por el equipo en `WEBHOOK_ALLOWED_ORIGINS` para el smoke de webhooks GCP, manteniendo la política de egress restringida.
- [x] Ejecutar `vm-controls.yml` con `operation=update` sobre `develop`; verificar release, ambos nodos, workers, Redis TLS/AUTH, health del balanceador y smoke HTTPS/login. Evidencia: workflow [43631884438](https://github.com/NexoRuta/NexoRuta/actions/runs/43631884438).
- [x] Revisar targets y paneles autenticados de GCP: Prometheus y GCP Metrics Collector están `up`; servicios/contenedores A/B están disponibles; las series de aplicación no aparecen y el Collector reporta `too old sample`.
- [ ] Con los dos nodos activos en una sesión autorizada, ejecutar `vm-controls.yml` `operation=update` con Collector `0.165.0`; verificar que la WAL avanza y que aparecen series HTTP frescas sin retirar ni borrar el volumen. Commit publicado: `b21f5b3`.
- [ ] Confirmar después del update series recientes HTTP/media/p95/p99/5xx, Mobile y webhooks tras generar tráfico real; ejecutar los flujos Mobile y webhook con receptor controlado.

El root `develop` desplegado fija los gitlinks Backend `5b6f0f9` y Mobile `9097670`; el gitlink de Frontend no cambió. El update no extendió el lease GCP existente. Los percentiles y estados de Mobile/webhooks sólo se darán por aceptados tras observar series reales posteriores al update y generar eventos controlados.
