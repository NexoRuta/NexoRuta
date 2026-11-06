# Observabilidad local

El Compose habitual incluye observabilidad automáticamente mediante `compose.override.yaml`. Desde la raíz del repositorio, con Docker Compose v2 y los secretos de desarrollo configurados en `.env`:

```powershell
docker compose config --quiet
docker compose up -d --build
```

El arranque ejecuta `rls-migrator` y luego `rls-role-provisioner`; API y workers esperan a que ambos terminen correctamente. El migrador está fijado al PostgreSQL local `postgres/nexoruta`. En Windows, `levantar-entorno-dev.bat` también valida el destino y ejecuta importación de catálogo y bootstrap de desarrollo.

Ese comando levanta la aplicación y Prometheus, Loki, Tempo, Grafana Alloy, OpenTelemetry Collector y Grafana. También conserva Aspire Dashboard. Grafana queda en <http://localhost:3000>, Prometheus en <http://localhost:9090> y Aspire Dashboard en <http://localhost:18888>. El dashboard es el mismo que se aprovisiona en GCP, con UID `nexoruta-demo` y definición en [nexoruta.json](../../observability/grafana/nexoruta.json).

Grafana usa Prometheus para todas las métricas, Loki para logs y Tempo para trazas. El tablero filtra métricas HTTP, workers, sincronizaciones y alertas por `service_name`; conserva el filtro de contenedores y logs por servicio y `correlation_id`. Incluye una gráfica de peticiones HTTP por servicio en ventanas móviles de cinco minutos (suma de los nodos seleccionados), latencia media/p95/p99, tasa 5xx, cola, resultados y pendientes de sync, errores de worker, fallos Push/notificaciones, caché, disponibilidad y alertas activas. La fila plegable de infraestructura GCP muestra VMs, balanceador y Cloud SQL cuando se abre en GCP.

Prometheus scrapea y evalúa las reglas cada 30 segundos; Alloy también comprueba los servicios locales con esa frecuencia.

Alloy recoge stdout/stderr de todos los contenedores de NexoRuta y envía los logs a Loki. Cada request web deja un evento estructurado con método, plantilla de ruta, estado y duración, sin URL completa ni cuerpo; los logs de API, portales y workers comparten `trace_id`, `span_id` y `correlation_id`. Las llamadas HTTP salientes conservan la propagación W3C y se limpian de URL y datos de excepción antes de exportarse. El estado exporter consulta Docker para publicar el estado y la salud de cada contenedor; Alloy usa blackbox para comprobar API, portales, base de datos, Redis, RabbitMQ y servicios de observabilidad. Las métricas y trazas de la aplicación pasan por OpenTelemetry Collector; las métricas de cola RabbitMQ llegan a Prometheus desde su exporter. La etiqueta `node=local` se añade en el Collector para que coincida con el filtro del dashboard.

Prometheus carga las reglas compartidas en [alerts.yaml](../../observability/prometheus/alerts.yaml): disponibilidad por servicio durante 2 minutos, tasa HTTP 5xx superior al 5% con al menos 20 solicitudes, p95 superior a 2 segundos con al menos 20 solicitudes, errores de workers/sync/Push, backlog RabbitMQ superior a 100 mensajes y caché bajo 25% con más de 20 consultas. El panel de alertas muestra las que estén en `firing`; sin filas significa que no hay incidentes activos.

El worker Push se levanta junto con RabbitMQ y usa `Push:NoSend` en Development para no contactar Firebase sin credenciales locales; si procesa destinos, los deja reintentables. Para levantar Kafka y sus servicios de perfil:

```powershell
docker compose --profile kafka up -d --build
```

Mailpit usa los puertos locales `11025` y `18025`. Grafana, Prometheus y Loki solo publican puertos en loopback; Tempo, Alloy y los collectors quedan dentro de la red Compose. Los datos de Prometheus, Loki, Tempo y Grafana se guardan en volúmenes nombrados. Para detener la pila y conservar esos volúmenes:

```powershell
docker compose down
```

Alloy y el estado exporter necesitan acceso al socket local de Docker para leer los logs y el estado de los contenedores. Ese socket no se publica como puerto de red. En GCP se usa el mismo dashboard; un collector consulta la API de Cloud Monitoring y expone esas métricas a Prometheus. El receiver de Google está en estado alpha y recoge métricas administradas cada 60 segundos. Más detalles en [monitoring GCP](../../gcp/monitoring/README.md) y [Grafana en GCP](../../gcp/grafana/README.md).
