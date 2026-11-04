# Grafana y observabilidad

Grafana se ejecuta en las dos VMs, comparte su base PostgreSQL de Cloud SQL y se publica bajo el subdominio `monitor`. El proxy de cada VM envía ese host a Grafana por el puerto privado 13000. La imagen está fijada por digest. Prometheus, Loki y Tempo se ejecutan como servicios Compose solo en la VM A; los datos persisten en volúmenes bajo `/srv/nexoruta/docker`.

Grafana usa Prometheus como única fuente de métricas, Loki para logs y Tempo para trazas. OpenTelemetry Collector y Alloy se ejecutan en ambas VMs. El Collector reenvía métricas OTLP a Prometheus y trazas a Tempo en A. Alloy descubre los contenedores del proyecto Compose, recoge stdout/stderr y envía los logs a Loki con etiquetas de nodo, servicio y contenedor. El procesamiento descarta líneas sensibles y conserva `trace_id`, `span_id` y `correlation_id` como metadatos estructurados.

En A, `gcp-metrics-collector` consulta la API de Cloud Monitoring cada 60 segundos y expone sus series a Prometheus. Así el dashboard muestra las métricas de Compute Engine, Cloud SQL, balanceador y sesión en la misma fuente que la aplicación. La identidad runtime de las VMs tiene `roles/monitoring.viewer`. El receiver `googlecloudmonitoring` de OpenTelemetry está en estado alpha.

Las dos instalaciones aprovisionan el mismo [dashboard NexoRuta](../../observability/grafana/nexoruta.json), con el mismo UID y paneles. La fila de infraestructura de GCP incluye estado de servicios y contenedores, CPU, RAM, disco, balanceador, Cloud SQL, colas y release aplicada. Los paneles compartidos cubren además latencia media, p95/p99, errores, sincronizaciones, caché, notificaciones, logs y trazas.

Los puertos de Prometheus, Loki y Tempo están ligados a la IP privada de A. El firewall permite conexiones desde la subred de las VMs; no hay reglas públicas para esos puertos. Alloy y el agente de estado consultan el Docker Engine de cada VM para recoger logs y estados. El perfil local está documentado en [observabilidad local](../../local/observability/README.md).
