# NFR-13 — Estado de implementación y aceptación

**Estado vigente al 14/11/2026: implementación aplicada y verificada localmente y en GCP; aceptación NFR-13 pendiente.** Este informe no declara `Done`: quedan gates operativos y de cobertura descritos en la actualización más reciente.

## Fuentes inspeccionadas

| Componente | Fuente |
| --- | --- |
| Raíz | `eefe3886c3ebc34147283f8842b1c321c36b39e4` |
| Backend de partida | `db38a2ac31d69e2a70411c283238e28400636d77`; candidato local `e8e4ec6` |
| Frontend fijado por la raíz | `723d02ba6cb5d0196a5181e4f4f076c115d7fe6d` |
| Frontend en el checkout local compilado | `162bf08ec9ad1428fa56dc81b5ce289ac1208a61` |
| Mobile de partida | `329dd3454704c0f45b615d609f469b7fd4b2dd5f`; candidato local `840a557` |

El checkout frontend difiere del gitlink raíz. Los cambios de salud también se aplicaron en un checkout aislado basado en `723d02b`; allí compilaron los cuatro portales y pasaron 57 pruebas del contrato OpenAPI, utilizando el GeoJSON canónico del backend fijado. Se fijaron en el commit `0277e43`, publicado en `nfr13-candidate`, pero aún no está incorporado como gitlink. La rama remota `develop` apunta a `162bf08`, por lo que un CI de pull request contra ella evaluaría una combinación distinta del gitlink original; debe resolverse sin incorporar implícitamente esos cambios ajenos.

Los candidatos de backend y mobile se publicaron en ramas `nfr13-candidate` y sus PR de CI están en borrador: [backend #57](https://github.com/NexoRuta/NexoRuta-Backend/pull/57) y [mobile #24](https://github.com/NexoRuta/NexoRuta-Mobile/pull/24). Ninguno está integrado ni desplegado.

## Cambios preparados

| Área | Implementación |
| --- | --- |
| Salud API | `/live` no consulta dependencias. `/ready` y `/health` comprueban ciclo de vida, PostgreSQL y, cuando se configuran, los almacenes compartidos de Data Protection y cuotas; cada consulta tiene límite de 2 s. La API de producción exige ambos almacenes compartidos. Las respuestas contienen solo estados y no incluyen excepciones ni configuración. Se retiraron las rutas antiguas del código activo y se actualizaron los consumidores locales. |
| Salud portales | Se agregó el mismo contrato anónimo y resumido al checkout frontend actual. Readiness comprueba arranque/drenaje y lectura del almacén compartido de Data Protection cuando está configurado; no hace llamadas externas. Los portales de producción ya requieren almacenamiento compartido. |
| Coordinación del vencimiento | Nueva migración `20261112100000_CoordinateProofDeadlineSweeps`: lock advisory transaccional fijo, una fila técnica con cooldown de PostgreSQL y `MoreWork`, permisos/RLS limitados al definer. La función devuelve `Completed`, `Contended` o `NotDue`. |
| Carrera por envío | El barrido toma el lock del envío y vuelve a comprobar el estado de bultos antes de escribir. Un competidor sin cambio real no incrementa la versión ni genera una transición vacía. SQL falla con error y revierte el avance junto a los efectos. |
| Worker y métricas | El worker consume el resultado tipado, continúa de inmediato si hay más lotes y separa contención, espera, fallo y apagado. Métricas acotadas incluyen resultados, duración, envíos afectados, continuación y edad desde la última ejecución completada; el recurso OTEL ya identifica nodo/release. |
| Apagado | API, portales y worker tienen `HostOptions.ShutdownTimeout = 20 s`. Compose conserva 30 s para salida de procesos; entrega existente espera al menos 35 s y el balanceador conserva 30 s de drenaje. El balanceador da afinidad cookie a Backoffice, que usa circuitos interactivos; esto no preserva circuitos si se pierde el nodo. |
| IaC y operación | Los probes del LB, Compose, verificadores, fixtures y scripts apuntan a `/ready`. No se cambió topología ni se aplicó IaC. |
| Cobertura | Se añadieron pruebas compilables para health anónimo/sin aliases, lock/cooldown, privacidad de la fila y firma exacta SQL. Se registró la clase nueva en el planificador de shards. |

## Resultados ejecutados

| Tipo | Resultado |
| --- | --- |
| Compilación | Build correcto de API, Worker, IntegrationTests y Admin, Backoffice, Commerce y Tracking del checkout frontend `162bf08`. Quedan warnings preexistentes NU1510/EF1003/BL0005/xUnit2031/CS8629; no hubo errores. |
| Automatización | Suite `scripts/gcp` en WSL: 241 tests, 0 fallidos y 3 omitidos por ausencia de PowerShell nativo; esos tres pasaron por separado en Windows. Una primera ejecución en WSL encontró incorrectamente `powershell.exe` y falló por las rutas Linux; se corrigió la selección del ejecutable. Planificador de shards: 3/3. Cliente OpenAPI frontend: 56/56. Cliente mobile: 63/63. |
| IaC | `tofu fmt -check -recursive infra/gcp` correcto; `init -backend=false -input=false -lockfile=readonly` y `validate` correctos para módulos `demo` y `bootstrap`. No se generó plan remoto ni se aplicó. |
| Compose | `scripts/gcp/validate_compose.py` validó la configuración de producción con Docker en WSL. |
| PostgreSQL/HTTP | Con PostgreSQL/PostGIS en Docker sobre WSL pasaron pruebas de salud, RLS, contención, rollback y carrera, incluidos bloqueos observados con prueba válida y con entrega parcial, plazos independientes con historia y un backlog de 251 envíos en tres lotes. La clase completa de reparto terminó con 79/79 pruebas aprobadas. Pasaron pruebas de dos APIs Kestrel para login, aislamiento de tenant y revocación, y un ensayo concurrente de cuota con contador SQL controlado. La función de cuota real se validó aparte. También pasaron antiforgery y cookie entre dos procesos Backoffice, reinicio del portal y rechazo en Admin. |
| Compatibilidad Cloud SQL | `scripts/gcp/cloudsql_compat.py` pasó en PostgreSQL/PostGIS local con `NOSUPERUSER`, migraciones completas, aprovisionamiento repetido, aislamiento de anillos y roles y función real de cuota: cinco admisiones y siete rechazos en doce conexiones concurrentes. Una primera ejecución detectó que el nuevo propietario de la función no tenía permiso temporal `CREATE` en el esquema; se corrigió la migración y se verificó que ese permiso queda revocado. |
| Candidato recompilado | Pasaron 4/4 pruebas focalizadas de coordinación y SIGTERM de API y worker, y 11/11 de salud, cuotas, portales y SignalR entre nodos. Las pruebas de portal usaron el checkout aislado basado en el gitlink raíz; el cliente SignalR sigue el transporte WebSocket del producto. Esto no sustituye el recorrido en navegador ni la aceptación GCP. |
| Pérdida del propietario del job | Una prueba con PostgreSQL real terminó la conexión del worker después de ejecutar el barrido sobre un envío dentro de una transacción sin confirmar. Otro worker observó primero contención y después completó el barrido. Se comprobó el rollback de estado, versión e historia, y luego un único vencimiento e incremento de versión. Tras terminar también la conexión del segundo worker, un sucesor ejecutó otro barrido después del cooldown real sin repetir el efecto. |
| Seis competidores | Seis conexiones de worker restringidas iniciaron el barrido simultáneamente sobre PostgreSQL real: una fue admitida y las demás devolvieron contención o espera. El caso verifica admisión sin envíos; las pruebas de carrera y backlog verifican efectos por separado. |
| Contrato RLS | La clase `RlsSqlFunctionContractTests` pasó 3/3 pruebas sobre la compilación actual y PostgreSQL real. |
| Apagado local | Una API en proceso separado recibió SIGTERM con una solicitud bloqueada en PostgreSQL; respondió, confirmó el par completo de outbox y terminó dentro del presupuesto. Un worker en proceso separado recibió SIGTERM con una reserva durante la publicación a RabbitMQ real pausado; terminó dentro de 30 s y un segundo worker recuperó la reserva y procesó el mensaje una vez. La prueba adelantó artificialmente el vencimiento de la reserva para acotar su duración. |
| RabbitMQ | La prueba existente `RepublicacionSinDestinoConfirmado_NoHaceAckDelOriginal` pasó con broker real: el consumidor no confirma el mensaje original si la republicación al destino no se confirma. |
| GCP | Las dos VM estaban `TERMINATED`; Cloud SQL estaba `RUNNABLE` y zonal, con backups automáticos deshabilitados. Se creó el backup bajo demanda `1794544830182`, terminado `SUCCESSFUL` el 13/11/2026 a las 04:42 UTC. La restauración a la instancia privada independiente `nexoruta-nfr13-restore-check` terminó y contiene las bases `nexoruta` y `grafana`. Dos consultas agregadas ejecutadas en la copia devolvieron 97 tablas públicas y 8500 filas de `spatial_ref_sys`; queda pendiente contrastar datos de negocio. Se ordenó detener la copia y se eliminó el bucket temporal de consulta. No hubo despliegue, carga ni inyección de fallos. |
| Navegador | Sin revisión visual o recorrido real. No hubo cambios de interfaz. |

## Matriz de aceptación

| Grupo | Estado | Evidencia o gate |
| --- | --- | --- |
| H01/H05 — rutas y consumidores | Código actualizado; health API probado por HTTP | El frontend preparado desde `723d02b` compiló; falta publicarlo y completar la matriz HTTP. |
| H02/H03/H04 — SQL caído, dependencias opcionales, arranque/drenaje | Parcial | Se comprobaron liveness con SQL y cuotas inaccesibles, readiness degradado y drenaje mediante Kestrel real. Falta completar los escenarios restantes de dependencias y arranque. |
| S01–S06 — sesión, tenant, cuotas, antiforgery, anillos y reinicio | Parcial | Login, aislamiento, revocación, antiforgery, cookies y reinicio probados con hosts reales y SQL restringido. La cuota HTTP usó un contador controlado; el contrato SQL real pasó por separado con conexiones concurrentes restringidas. Falta completar la matriz. |
| C01–C07 — reparto, caída de API/VM, comandos y reconexión | Pendiente | Requiere cliente real, fuente publicada y observación externa. |
| D01–D05 — SIGTERM, crash, reservas y presupuesto | Parcial | SIGTERM de API con petición en vuelo y recuperación de reserva tras SIGTERM del worker con RabbitMQ real probados localmente; faltan crash y ensayo GCP. |
| J01/J02/J08/J09 — lock, cooldown, resultados y RLS | Implementado y probado parcialmente | Se probaron health, contrato RLS y contención; falta completar toda la matriz de coordinación. |
| J03–J07/J10 — carreras, rollback, lotes y regresiones | Parcial | Carreras con bloqueos observados, rollback y 251 envíos en tres lotes probados; falta completar regresión y restantes escenarios de fallo. |
| O01–O04 — telemetría, observador y estabilidad | Métricas añadidas; aceptación pendiente | Falta scraping visible, prueba de frescura y ensayo sostenido. |
| P7 — aceptación GCP | No ejecutada | Requiere release candidata, inventario, respaldo recuperable, sesión suficiente y autorización operativa específica. |

### Gates pendientes para poder cerrar

1. Seleccionar fuentes exactas y publicar el cambio frontend sin arrastrar diferencias ajenas; no mover gitlinks implícitamente.
2. Completar la matriz local de dos APIs, job concurrente, reinicio, SignalR y navegador con PostgreSQL 18/PostGIS.
3. Ejecutar el CI de las fuentes publicadas exactas.
4. Preparar una ventana GCP con respaldo recuperable y recuperación ensayada. El usuario autorizó el despliegue y las pruebas de GCP; aún no se han ejecutado.
5. Adjuntar observaciones HTTP/GCP y evidencia de salida/reconexión; actualizar la tarjeta Notion solo después de resultados observados.

La aceptación debe permanecer pendiente hasta superar esos gates. La topología actual sigue teniendo SQL zonal y servicios únicos en VM A; el trabajo no establece HA regional ni continuidad integral de esos servicios.

## Actualización de ejecución — 13/11/2026

Esta sección reemplaza como estado vigente las cifras y gates del corte inicial anterior. Las limitaciones de disponibilidad GCP siguen pendientes.

| Componente | Fuente candidata exacta |
| --- | --- |
| Raíz | `eefe3886c3ebc34147283f8842b1c321c36b39e4` |
| Backend | `425634e743fed4e3217c77c8ef3cf56ec0e150c7` |
| Frontend | `2540041ba267d8a48e6c2b8a644247134f5b47f4` (basado en el gitlink original `723d02b`; suma la prueba de reconexión automática) |
| Mobile | `840a5570cece18eb4de558b3b5004ae935dff771` |

Los componentes siguen publicados en sus ramas candidatas; la raíz debe fijar estos commits explícitamente. No se usa el checkout frontend local `162bf08` ni las evidencias AP-04 sin seguimiento.

### Verificaciones posteriores

| Categoría | Resultado observado |
| --- | --- |
| Scripts GCP | `python -m unittest discover -s scripts/gcp -p 'test_*.py'`: 255 tests, 0 fallidos, 8 omitidos por capacidades/plataforma opcionales. |
| Compose | `python scripts/gcp/validate_compose.py` pasó en WSL con Docker disponible. |
| OpenTofu | `fmt -check`, `init -backend=false -input=false -lockfile=readonly` y `validate` pasaron para `bootstrap` y `demo`; no hubo plan remoto ni apply. |
| HTTP local | Las pruebas de salud y el caso de login `Production` que reproducía el 503 pasaron juntas: 7/7. El fixture instala la dependencia compartida que producción instala aparte con `hosting.sql`. |
| Navegador | `OperationalBrowserTests.RealTrackingRequestsAndBackofficeUseRestrictedApiAndPreservePhysicalCustody` pasó 1/1 con Chromium, PostgreSQL/PostGIS y Kafka propios. El browser abrió el tablero, cerró un WebSocket establecido, observó que el cliente SignalR reconectó automáticamente y recuperó la fotografía confirmada; además conservó la recuperación manual de un inicio fallido. Axe informó 0 violaciones. La captura sintética está en `evidencia/local-browser-auto-reconnect.png`; el resumen sanitizado en `evidencia/local-browser-reconnect-summary.json`. |
| Backend CI | Run `43452791131`, commit `425634e`: build, política de fuentes, cobertura y los tres integration shards terminaron verdes. |
| Mobile CI | Run `43445604753`, commit `840a557`: API, Application, Core, Storage, Android, lint y política de fuentes terminaron verdes. |
| Frontend CI | El run `43458995384` evalúa el commit `2540041` y terminó correctamente: build, syntax, portales, API client y pruebas de contrato OpenAPI. |
| Inventario GCP | `evidencia/gcp-inventario-2026-11-13.json`, lectura observada a las 15:29 UTC: ambas VM `TERMINATED`, Cloud SQL `RUNNABLE` y `ZONAL`, sin lease activa y sin backends API sanos mientras las VM están apagadas. Backups automáticos siguen deshabilitados. |
| Recuperación SQL | El backup bajo demanda `1794544830182` sigue `SUCCESSFUL`; su restauración aislada `nexoruta-nfr13-restore-check` permanece `STOPPED` después de comprobar que contiene las bases `nexoruta` y `grafana`. |

La sesión GCP, el despliegue del conjunto exacto, la carga base, los cuatro ensayos de falla, la ventana posterior de estabilidad y la reconciliación operativa aún no se ejecutaron. No se reporta un resultado GCP verde a partir del inventario estático. El usuario autorizó iniciar y probar las VM; esta etapa se realizará después del CI de la raíz y con el backup/restauración aislada ya disponibles.

## Actualización de ejecución — 14/11/2026

Esta actualización reemplaza como estado vigente las cifras y gates operativos del corte del 13/11. No elimina el historial ni cambia la definición de terminado de la card. La aceptación permanece pendiente.

### Validación local

| Categoría | Resultado observado |
| --- | --- |
| Automatización de scripts GCP | `wsl.exe --cd /mnt/c/Users/ignac/code/utec/NexoRuta python3 -m unittest discover -s scripts/gcp -p 'test_*.py'`: 265 tests, 0 fallidos, 3 omitidos por capacidades/plataforma opcionales; código de salida 0. Se repitió tras integrar los commits recientes de `develop`. |
| Alcance | Incluye los nuevos casos para deadline absoluto de la sesión tras recuperar una VM y omisión del backend apagado en `get-health`. El fixture temporal expirado se reemplazó por una fecha futura dinámica y se volvió a ejecutar toda la suite. |

### Validación GCP

| Categoría | Resultado observado |
| --- | --- |
| Línea base | Workflow `43618895927`, release `release-2c9f1ca79ad547548b2f79662c922f1a`: 4.492 solicitudes, 0 errores, 0 resultados inesperados y 0 iteraciones descartadas. La etapa nominal duró 960 s; p95 55,392 ms y p99 67,864 ms. `docs/auditorias/nfr-13/evidencia/gcp-load-baseline-2026-11-14-43618895927.json`. |
| Salud durante la carga | 16 endpoints revisados, todos HTTP 200. Los probes finales `/live`, `/ready` y `/health` también dieron HTTP 200 y readiness informó PostgreSQL, Data Protection y rate limits saludables. |
| Pérdida API A/B | Los dos escenarios pasaron y restauraron ambos backends: API A 29,964 s y API B 32,183 s. Evidencias `gcp-api-a-2026-11-14-final.json` y `gcp-api-b-2026-11-14-final.json`. |
| Pérdida VM A/B | Los dos escenarios pasaron y restauraron el par: VM A 8,266 s y VM B 7,612 s. Cuando Compute omitió el backend detenido de `get-health`, el verificador lo aceptó solo con ambos backends sanos en preflight y el superviviente sano. Evidencias `gcp-vm-a-2026-11-14-final.json` y `gcp-vm-b-2026-11-14-final.json`. |
| Estabilidad | El observador se inició a las 18:47:08 UTC y se cerró por instrucción del usuario a las 19:04:12 UTC: 1.023,2 s, 18/31 lotes y 54/54 probes HTTP 200. **No completa el intervalo de 30 minutos requerido**; no usar como aprobación de operación sostenida. El resumen está en `evidencia/gcp-stability-2026-11-14.json`; no conserva latencia individual por muestra. |
| Inventario al cierre de medición | Observado a las 19:08:15 UTC y confirmado tras el push a las 19:11:48 UTC: VM A/B `RUNNING`, ambos backends `HEALTHY`, sesión activa, Cloud SQL `RUNNABLE`/`ZONAL`. Se conserva el plazo original 20:19:23 UTC. Evidencias `evidencia/gcp-inventario-final-2026-11-14.json` y `evidencia/gcp-inventario-postpush-2026-11-14.json`. Por instrucción expresa del usuario, las VMs permanecen encendidas. |
| Respaldo | Cloud SQL continúa con backups automáticos deshabilitados. El backup bajo demanda y la restauración aislada probados en el corte anterior no sustituyen una política automática ni la comparación de datos de negocio. |

### Límites y gates pendientes

- Redis se observó degradado: `service_up=0` en ambos nodos y el contenedor de B `unhealthy`, con 61 PIDs de un límite 64 y fallos de ejecución del healthcheck. La API conservó readiness saludable, pero esto no acredita la salud del servicio compartido. No se hizo una modificación de runtime o Compose para ocultar el problema.
- Los agentes de telemetría de las dos VMs estaban inactivos y se reiniciaron antes de la ventana. Los puntos de inicio fueron frescos (A 49,35 s; B 6,41 s); OOM y reinicios de contenedores API estaban en cero. Hace falta validar continuidad/frescura durante una observación completa.
- BrowserAct llegó al login OAuth de Google de Grafana. No se ingresaron credenciales y no se pudo verificar visualmente el dashboard autenticado. La consulta directa de Prometheus sí funcionó; no equivale a una revisión del dashboard.
- La prueba sostenida de 30 minutos se omitió por instrucción del usuario. Una ejecución posterior debe completarla si se requiere acreditar ese criterio.
- Faltan los casos de la matriz local que continúan parciales, en particular las combinaciones restantes de salud/arranque, sesión y comandos, crash y regresiones del job. Los resultados previos de SIGTERM local y PostgreSQL real se conservan, pero no reemplazan esos casos.
- En GCP se ejecutaron baseline y cuatro pérdidas controladas de API/VM; no se probó allí un comando de negocio persistente con cliente real durante el failover ni un SIGTERM de API/worker con trabajo en vuelo. La aceptación integral de P7 sigue pendiente.
- El CI del conjunto final no se ejecutó; el usuario instruyó probar localmente y publicar directo en `develop`, sin CI de PR. Esto no cambia el resultado de la suite local ni debe describirse como CI verde.
- La topología sigue siendo Cloud SQL zonal, con servicios singleton en A y backups automáticos deshabilitados. No se acredita HA regional ni continuidad integral de servicios singleton.

**Criterio de cierre:** mantener NFR-13 como no aceptado hasta resolver Redis/telemetría, acreditar los casos locales y operativos pendientes y completar la estabilidad si se exige ese gate. Esta ejecución acredita la suite local, la línea base GCP y los cuatro escenarios API/VM enumerados; no cambia los criterios de la card.
