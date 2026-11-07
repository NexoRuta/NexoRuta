# NFR-07: capacidad observada en VM B para alojar Redis

Fecha: 06/11/2026, 00:06–00:09 UYT (03:06–03:09 UTC). Revisión de lectura, sin desplegar Redis, iniciar carga, reiniciar procesos ni modificar recursos.

## Resultado

**La VM B tiene margen de RAM y CPU para incorporar un Redis con límite de contenedor de 512 MiB y cuota máxima de 1 vCPU, para el uso de demo observado.** No hace falta ampliar la máquina con la evidencia disponible. La aceptación bajo carga de la configuración nueva sigue siendo un gate de implementación; esta auditoría no es un ensayo de saturación ni una garantía para cargas no observadas.

Proyecto `nexoruta-demo-20261022`; VM `nexoruta-demo-b`, zona `southamerica-west1-b`; máquina `n4-custom-6-16384`: **6 vCPU y 16 GiB provisionados**. Linux informa 16000,8 MiB utilizables. Estado RUNNING, sin swap, CPU Intel Emerald Rapids. Último arranque 05/11/2026 23:43:08 UTC; release `release-e13f492d80c346db82e5b9f6aa12758c`. Scheduling: STOP al cumplir 14400 segundos y automaticRestart=false.

## Método y cobertura

Se consultó el inventario con gcloud, y por IAP/SSH se leyeron `/proc/meminfo`, `/proc/stat`, `/proc/loadavg`, `/proc/pressure/memory`, estados/límites seleccionados de Docker y una muestra de `docker stats --no-stream`. Se tomaron 12 intervalos de aproximadamente 10 segundos, entre 03:06:42 y 03:08:42 UTC. CPU busy = diferencia de CPU total menos idle e iowait, dividida entre total; porcentaje sobre las seis vCPU del host.

Desde la identidad runtime de B se consultó Cloud Monitoring para su instance_id, ventana retrospectiva de 24 horas al 06/11/2026 03:06:42 UTC. Métricas `compute.googleapis.com/instance/cpu/utilization` y `agent.googleapis.com/memory/percent_used`, esta última con `metric.labels.state="used"`; ALIGN_MEAN, alineación 60 s. No quedó paginación pendiente. Se consultaron datos agregados, sin imprimir tokens, secretos, variables de entorno completas ni argumentos de procesos.

La ventana tiene **826 muestras CPU y 829 de RAM**, no 1440 minutos continuos. Los periodos sin VM/agent/muestra no se convirtieron en cero. p95 = percentil empírico de muestras disponibles. El máximo es el mayor promedio de un minuto; no representa el máximo instantáneo. `percent_used{state=used}` y MemAvailable tienen semánticas diferentes y no deben tratarse como complementos exactos.

## Mediciones

| Indicador | Resultado |
| --- | --- |
| MemAvailable al inicio | 13066,8 MiB ≈ 12,76 GiB |
| MemAvailable durante los 12 intervalos | mínimo 13048,4 MiB; máximo 13087,1 MiB |
| CPU busy durante los 12 intervalos | mínimo 1,954%; máximo 3,116% del host |
| Iowait durante los 12 intervalos | 0–0,033% |
| Load average 1 min durante los 12 intervalos | 0,25–0,57, sobre 6 CPU lógicas |
| Presión de RAM | PSI some/full avg10/60/300 = 0,00 en todas las muestras; sin aumento de los acumulados durante la ventana |
| CPU histórica, 826 muestras | media 5,110%; p95 12,617%; máximo 42,820% |
| RAM usada histórica, 829 muestras | media 16,401%; p95 18,313%; máximo 20,473% |
| Mayor muestra CPU | 05/11/2026 21:45:42 UTC |
| Mayor muestra RAM | 05/11/2026 21:40:42 UTC |
| Contenedores del proyecto | 12 running; ninguno con OOMKilled=true en su estado actual |

Muestras del host para reproducir la evaluación, horas UTC del 06/11/2026:

| Hora | CPU busy % | MemAvailable MiB |
| --- | --- | --- |
| 03:06:52 | 2,847 | 13072,4 |
| 03:07:02 | 2,233 | 13065,3 |
| 03:07:12 | 2,647 | 13058,4 |
| 03:07:22 | 3,116 | 13048,4 |
| 03:07:32 | 2,166 | 13061,9 |
| 03:07:42 | 2,173 | 13053,9 |
| 03:07:52 | 2,436 | 13061,6 |
| 03:08:02 | 1,954 | 13066,1 |
| 03:08:12 | 2,650 | 13077,2 |
| 03:08:22 | 3,085 | 13087,1 |
| 03:08:32 | 2,084 | 13055,4 |
| 03:08:42 | 2,585 | 13052,8 |

## Procesos desplegados y presupuesto

Docker stats informa CPU sobre una CPU lógica: su 100% no equivale al 100% del host de seis vCPU. Su memoria tampoco es idéntica a RSS o a la métrica del agente. No mezclar estas bases para calcular un total aparente.

| Servicio en B | Uso Docker MiB, muestra | Límite Docker MiB |
| --- | --- | --- |
| api | 189,70 | 1536 |
| admin | 124,60 | 768 |
| backoffice | 139,20 | 768 |
| commerce | 135,20 | 768 |
| tracking | 123,30 | 768 |
| worker-rabbit | 194,50 | 768 |
| worker-kafka | 202,00 | 768 |
| worker-push | 173,40 | 768 |
| grafana | 444,60 | 512 |
| otel-collector | 91,82 | 512 |
| alloy | 82,94 | 128 |
| sql-proxy | 17,11 | 256 |
| **Suma de límites configurados** | — | **8320** |
| Redis propuesto | pendiente de medir | **512** |
| **Suma después de incorporar Redis** | — | **8832** |

Sumando además una reserva presupuestaria de 2048 MiB para SO, Docker y agentes, quedan aproximadamente **5120,8 MiB** de holgura respecto de los 16000,8 MiB utilizables. Los límites no son reservas ni un límite global: el agente debe volver a inventariar procesos ajenos a Compose y medir bajo carga.

La cuota propuesta Redis de 1 vCPU equivale a hasta 16,67 puntos porcentuales del host. Como estimación de planificación, el pico histórico de CPU más esa cuota sería 59,49%; no es una predicción de concurrencia ni una medición de Redis. El ensayo de la implementación debe observar CPU, throttling y latencia con TLS y payloads representativos.

**Hallazgo independiente:** Grafana B usa 444,6/512 MiB, 86,84% de su límite, aunque el host tenga RAM disponible. No se observó OOMKilled en ese contenedor. Registrar su comportamiento durante el ensayo y no atribuir un eventual OOM de Grafana al agotamiento de RAM del host. Esta revisión no modifica su límite.

## Decisión y condiciones

1. Ubicar **un solo Redis en B**, compartido por las APIs A y B, sin mover a B los brokers, SQL, Prometheus, Loki o Tempo.
2. Redis: maxmemory=256 MiB; límite del contenedor=512 MiB; cpus=1.0; sin RDB/AOF; TLS/AUTH y acceso privado. El margen entre maxmemory y límite debe cubrir fragmentación, conexiones/TLS y buffers; maxmemory no limita por sí solo el RSS total.
3. Repetir la medición antes del despliegue si cambió la release/carga. Gate posterior: MemAvailable ≥2 GiB, CPU p95 del host <70%, sin periodos ≥85% sostenidos cinco minutos, sin OOM, sin presión de memoria sostenida y sin regresión de las APIs. Revisar throttling Redis junto con latencia; no aumentar cuota automáticamente ante cualquier throttling.
4. Hacer primero ensayo aislado de límites, TLS, payload máximo y expulsión; luego smoke y carga controlada de cinco usuarios concurrentes durante al menos diez minutos en una sesión autorizada. Sin llamadas geográficas reales ni modificaciones a datos ajenos.
5. Si los gates fallan, no retirar Memorystore ni declarar completada la migración; documentar la causa y corregir límites/carga. La holgura observada permite preparar la migración sin cambiar el tipo de VM.

## Repetición por otro agente

```powershell
gcloud compute instances describe nexoruta-demo-b --project=nexoruta-demo-20261022 --zone=southamerica-west1-b --format="json(name,status,machineType,cpuPlatform,lastStartTimestamp,scheduling)"
gcloud compute ssh nexoruta-demo-b --project=nexoruta-demo-20261022 --zone=southamerica-west1-b --tunnel-through-iap --command uptime
```

Para la serie histórica usar `projects.timeSeries.list`, filtro `resource.type="gce_instance"` e instance_id de B, rango ISO UTC explícito, agregación indicada arriba; consumir todas las páginas y conservar número/cobertura de muestras. Leer credenciales solo en memoria. Para el host usar lectura de `/proc` y Docker con campos seleccionados; nunca guardar `docker inspect` completo, `.env`, tokens o material TLS en evidencia.

La [guía de implementación](../../planes/nfr-07-cierre-y-validacion.md#9-migración-de-redis-a-vm-b-y-ciclo-de-cuatro-horas) convierte esta decisión en pasos y gates. Las consultas de capacidad son nuevas; la compilación, el smoke funcional y la revisión visual no se ejecutaron en esta auditoría documental.
