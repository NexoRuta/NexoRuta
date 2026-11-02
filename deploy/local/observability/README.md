# Observabilidad local

El Compose habitual incluye observabilidad automáticamente mediante `compose.override.yaml`. Desde la raíz del repositorio, con Docker Compose v2 y los secretos de desarrollo configurados en `.env`:

```powershell
docker compose config --quiet
docker compose up -d --build
```

El arranque ejecuta `rls-migrator` y luego `rls-role-provisioner`; API y workers esperan a que ambos terminen correctamente. El migrador está fijado al PostgreSQL local `postgres/nexoruta`. En Windows, `levantar-entorno-dev.bat` también valida el destino y ejecuta importación de catálogo y bootstrap de desarrollo.

Ese comando levanta la aplicación y Prometheus, Loki, Tempo, Grafana Alloy, OpenTelemetry Collector y Grafana. También conserva Aspire Dashboard. Grafana queda en <http://localhost:3000>, Prometheus en <http://localhost:9090> y Aspire Dashboard en <http://localhost:18888>. El dashboard es el mismo que se aprovisiona en GCP, con UID `nexoruta-observabilidad` y definición en [nexoruta.json](../../observability/grafana/nexoruta.json).

Grafana usa Prometheus para todas las métricas, Loki para logs y Tempo para trazas. El tablero incluye latencia media, p95 y p99, errores del API, sincronizaciones móviles pendientes, aciertos del caché, avisos a comercios fallidos, servicios y contenedores disponibles, métricas de cola y logs filtrables por servicio o `correlation_id`. La fila plegable de infraestructura GCP muestra VMs, balanceador y Cloud SQL cuando se abre en GCP.

Alloy recoge stdout/stderr de todos los contenedores de NexoRuta y envía los logs a Loki. El estado exporter consulta Docker para publicar el estado y la salud de cada contenedor; Alloy usa blackbox para comprobar API, portales, base de datos, Redis, RabbitMQ y servicios de observabilidad. Las métricas y trazas de la aplicación pasan por OpenTelemetry Collector; las métricas de cola RabbitMQ llegan a Prometheus desde su exporter.

Para levantar el worker Kafka y los servicios de su perfil:

```powershell
docker compose --profile kafka up -d --build
```

Mailpit usa los puertos locales `11025` y `18025`. Grafana, Prometheus y Loki solo publican puertos en loopback; Tempo, Alloy y los collectors quedan dentro de la red Compose. Los datos de Prometheus, Loki, Tempo y Grafana se guardan en volúmenes nombrados. Para detener la pila y conservar esos volúmenes:

```powershell
docker compose down
```

Alloy y el estado exporter necesitan acceso al socket local de Docker para leer los logs y el estado de los contenedores. Ese socket no se publica como puerto de red. En GCP se usa el mismo dashboard; un collector consulta la API de Cloud Monitoring y expone esas métricas a Prometheus. El receiver de Google está en estado alpha y recoge métricas administradas cada 60 segundos. Más detalles en [monitoring GCP](../../gcp/monitoring/README.md) y [Grafana en GCP](../../gcp/grafana/README.md).
