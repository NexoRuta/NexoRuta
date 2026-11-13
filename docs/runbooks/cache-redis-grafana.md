# Operación de cachés Redis y métricas

Dashboard: `nexoruta-demo` en el Grafana existente. La fila **Caché distribuida** muestra actividad de la aplicación; la fila **Infraestructura GCP · Prometheus** muestra la salud y los recursos del Redis único en VM B.

## Paneles y filtros

- `cache`: `operator_branding` corresponde al snapshot de identidad visual; `published_tariff` corresponde a una versión de tarifas publicada.
- `node`: filtra las API A/B que leen/escriben el mismo Redis de B. `redis` no se espera como contenedor en A.
- `otel_service`: para esta funcionalidad usar `NexoRuta.Api`. La caché local de Geoapify tiene paneles separados.
- **Aciertos por segundo** y **Misses por segundo** usan tasas de contadores. Un miss es normal cuando se lee una versión nueva, después de una expulsión LRU o al arrancar B vacío.
- **Porcentaje de aciertos** separa los casos. **Porcentaje total ponderado** calcula `hits / (hits + misses)` con los contadores agregados; no promedia porcentajes por nodo o caso. Error, bypass y cancelación no entran en el denominador.
- **Hits y misses en el rango** usa `increase()` de Prometheus y es una estimación del intervalo, no un registro contable exacto.
- **Series de telemetría de caché** distingue falta de series de un nodo con series y cero lecturas. Sin series significa telemetría ausente o todavía no exportada; no significa 0 % de hits ni Redis caído.
- **Latencia p95 de Redis** mide operaciones GET/SET observadas por la API. Los paneles de infraestructura separan el probe TLS/AUTH, RSS Redis, memoria cgroup, clientes y desalojos LRU.

## Diagnóstico

1. Si falta un nodo en **Series de telemetría de caché**, revisar que `OpenTelemetry:Enabled` esté activo, que `NODE_NAME` sea `a`/`b`, que la API exporte a su Collector y que el Collector de ese nodo complete remote write. Consultar primero las series `nexoruta_cache_distributed_requests_total` y `nexoruta_api_requests_total` en Prometheus.
2. Si las series existen pero hit/miss siguen en cero, comprobar volumen de GET elegibles dentro del rango. El panel inicializa series en cero al arrancar; no generar tráfico sintético desde Grafana.
3. `nexoruta_gcp_service_up{service="redis"}` ahora ejecuta TLS con CA y hostname, AUTH y PING desde cada VM. El TCP abierto por sí solo no acredita disponibilidad.
4. Redis solo debe estar en B: comprobar `nexoruta_gcp_container_up{service="redis",node="b"}`, reinicios, OOM, RSS de Redis y memoria cgroup. Las métricas de servidor no reemplazan los hits/misses de negocio.
5. Comparar contra la auditoría más reciente: al menos 2 GiB `MemAvailable`, CPU p95 del host menor a 70 %, sin CPU mayor o igual a 85 % sostenida cinco minutos, sin OOM ni presión de memoria sostenida y RSS Redis menor a 80 % del límite de 512 MiB. Investigar una regresión de endpoint mayor a 10 % y 20 ms simultáneamente, repetida y sostenida.

## Recuperación

- La aplicación degrada a PostgreSQL si Redis falla; la caída de Redis no debe convertir `/ready` en una dependencia del balanceador. Confirmar lecturas del origen y errores de caché sin modificar PostgreSQL ni invalidar claves globalmente.
- Una vez completada la migración a B, para bypass deliberado durante una falla persistente, establecer `NEXORUTA_CACHE_ENABLED=false` en el entorno GitHub `nexoruta-demo` y ejecutar el workflow manual `vm-controls` con `update`. Los dos nodos deben confirmar el modo bypass; el deployer omite reconciliar Redis y las sondas Redis, actualiza las API para leer el origen PostgreSQL y conserva el límite de sesión existente. La monitorización sigue mostrando Redis no saludable. Volver a `true` y ejecutar otro `update` al resolver la causa; esa actualización exige nuevamente smoke TLS/AUTH desde A y B.
- `stop` detiene ambas VM y el contenedor Redis de B. `start` levanta las VMs dentro del límite de cuatro horas; Redis vuelve vacío y se rellena desde PostgreSQL. Los datos de negocio no dependen de Redis.
- No usar `FLUSHALL`, `FLUSHDB`, `KEYS`, `CONFIG` ni `SHUTDOWN` con credenciales runtime. El ACL limita el usuario a comandos de caché y claves bajo el namespace de NexoRuta.
- Una identidad TLS inválida o a menos de 30 días de vencer hace fallar el preflight; no se regenera sola. La rotación requiere una operación coordinada explícita con las VMs detenidas y una nueva versión de Secret Manager antes del próximo `start`.

La ausencia de Redis en A es intencional. No instalar una segunda instancia, Sentinel o fallback automático a Memorystore.
