# Registro de validación

La implementación inicial se integró en `develop` mediante las PR [Backend #49](https://github.com/NexoRuta/NexoRuta-Backend/pull/49) y [Frontend #51](https://github.com/NexoRuta/NexoRuta-Frontend/pull/51), después de sus checks finales verdes y sin omitir protecciones.

Candidatos del cierre inicial: Backend `655edd3a2f2e2326e7a9d99bb2a405b81ee7b6e8`, Frontend `7ce3e969924e1157d2eaa80b5c933bea9560f5b0`. Mobile conserva `f2b3db412ce23b0b36215fd301f6d3d3d6959252`. La corrección posterior de salud Kafka se identifica al final de este registro.

El [CI final de Frontend](https://github.com/NexoRuta/NexoRuta-Frontend/actions/runs/42306859258) aprobó 518 pruebas. El [CI final de Backend](https://github.com/NexoRuta/NexoRuta-Backend/actions/runs/42306868322) aprobó 346 unitarias, 4 de arquitectura y 720 casos únicos de integración (241/219/260 por shard). El preflight repite además un caso crítico de decisión operativa; no se suma como un caso distinto. No hubo fallos ni omitidas en esos reportes finales.

Gitlinks publicados del conjunto:

| Repositorio | Commit publicado / gitlink |
|---|---|
| Backend, candidato #52 pendiente de merge | `06a495a35625ba771926e6eca571e148cd016ef2` |
| Frontend | `06b1ca380aea0ec68dbbaafff5de9a63a24d8f6b` |
| Mobile, sin cambios | `f2b3db412ce23b0b36215fd301f6d3d3d6959252` |

Los merges iniciales Backend `a7c1de8fae4859385082a2e7065704d3dc7d4fe6` y Frontend `06b1ca380aea0ec68dbbaafff5de9a63a24d8f6b` coinciden exactamente con sus candidatos validados. No hubo avances concurrentes de sus bases durante aquel cierre. [ci-final.json](evidencias/ci-final.json) conserva SHAs, corridas, contadores TRX, identidades y hashes SHA-256 de los artefactos descargados de ese cierre inicial. Los artefactos crudos del CI tienen retención de 14 días; los resúmenes y hechos seleccionados permanecen versionados aquí.

## Cobertura

Métrica: líneas de fuente ejecutables, unión por archivo/línea de unitarias e integración, por capa. El control es estrictamente **>70% en cada capa**, sin exclusiones personalizadas. No hay atributos de exclusión añadidos en Domain/Application. Los valores y fallos/omitidas iniciales están publicados en `backend/docs/seguimiento-tablero/evidencias/`.

| Capa | Inicial | Final CI sobre 655edd3 | >70% |
|---|---:|---:|---|
| Domain | 1880/2038 — 92,25% | 1880/2038 — 92,25% | Aprobado |
| Application | 1543/1638 — 94,20% | 1576/1673 — 94,20% | Aprobado |

La medición inicial cubrió 336 unitarias aprobadas y 712 integraciones: 700 aprobadas, 7 fallidas y 5 omitidas; esa ejecución inicial no fue verde. Sus métricas se publicaron antes de cambiar el producto. El informe final es la unión por archivo/línea de ocho reportes Cobertura del CI, sin contar dos veces una línea por ejecutarse en varias suites: [JSON](evidencias/cobertura-final/summary.json) y [resumen](evidencias/cobertura-final/summary.md). El gate falla con 70% exacto, con una capa ausente o con reportes insuficientes. La cobertura de Mobile no se mezcla con Backend; no se midió cobertura adicional de Mobile.

## Evidencias locales

- 346 unitarias y 4 de arquitectura de Backend aprobadas.
- 96 verificaciones focalizadas de regresión, aislamiento, importación, segunda visita y retiros aprobadas.
- 8 escenarios operativos completos aprobados; 2 adicionales de MongoDB/replay verifican igualdad JSON sin depender del orden de propiedades.
- 7 casos de seguimiento/contrato/retiro público aprobados, incluidos retiros con 1/500/501/1500 bultos, y 6 casos de reserva de outbox aprobados.
- Frontend: 518 pruebas aprobadas sin omitidas, incluidos los navegadores opt-in; 21 pruebas Node aprobadas.
- Principal: 221 controles Python aprobados sin omitidas, prueba de gitlinks y actionlint aprobados. PowerShell ejecuta únicamente un receptor Python de argumentos; no se ejecuta el cuerpo de setup ni un motor IaC.
- Migración completa y controles de roles, RLS, hosting y cuotas en PostgreSQL **efímero** con migrador sin superusuario/BYPASSRLS aprobados. No se conectó a Cloud SQL ni a una VM real.

[operacion.json](evidencias/operacion.json) recoge los TRX del CI final: identidades de topic y cuatro grupos aislados, 12 eventos únicos y 9 filas reconstruidas idénticas; recuperación independiente de MongoDB; Mailpit con un correo recibido, dos intentos SMTP y ausencia de reenvío por mensaje duplicado; dos API reales detrás de un proxy WebSocket, un failover, reconexión a la superviviente, aislamiento y detección de outbox atrasado. Incluye los ocho resultados operativos completos. Las capturas y resúmenes de Chromium quedan en los artefactos de CI. Se revisaron visualmente escritorio y web a 320 px, teclado y foco; axe del tablero no encontró violaciones. No se realizó una validación visual nativa Android.

La corrida local completa anterior se interrumpió tras fallos de aserciones ya actualizadas y falta de disco temporal de Docker VFS; **no cuenta como aprobada**. Los pipelines posteriores ejecutan el inventario exhaustivo en tres shards y publican TRX/Cobertura. Las ejecuciones canceladas o fallidas no se cuentan como verdes.

## Integración del principal

El usuario aclaró el alcance y autorizó las validaciones del CI existente: `tofu fmt -check`, `tofu init -backend=false -input=false -lockfile=readonly`, `tofu validate` y pruebas con infraestructura sintética y efímera. El bloqueo anterior de autorización queda resuelto. Siguen prohibidos `apply`, `destroy`, `import`, acceso o modificaciones del estado remoto, despliegues y operaciones sobre la VM/base real.

El workflow [Integrated CI](../../.github/workflows/ci.yml) usa permisos `contents: read` y el entorno `nexoruta-ci` para las PR, sin autenticación de despliegue ni permiso OIDC. El job `infrastructure` inicializa los módulos con backend deshabilitado y valida su configuración; `cloudsql` verifica PostgreSQL efímero, no una instancia real. Los workflows de publicación y operación no se disparan al abrir esta PR ni al integrar con `develop`.

La [PR principal #74](https://github.com/NexoRuta/NexoRuta/pull/74) apunta a `develop`, mantiene Frontend y Mobile exactos y valida la corrección posterior de Backend #52. La consulta remota confirmó la base en `25ffb1d8a7f34bb17623a99357d0b7b743ba8404`, antecesor del candidato, sin avances concurrentes.

El [CI integrado completo 42333366312](https://github.com/NexoRuta/NexoRuta/actions/runs/42333366312) terminó con **success** sobre el head `15aef02f9393f128f6f67c5edbd53061b95b1cb6`. GitHub ejecutó el checkout de merge sintético `ef9f184c461a6d210802e2ce5924837cf7992744`, con Backend `a7c1de8fae4859385082a2e7065704d3dc7d4fe6`, Frontend `06b1ca380aea0ec68dbbaafff5de9a63a24d8f6b` y Mobile `f2b3db412ce23b0b36215fd301f6d3d3d6959252`. El plan activó todas las validaciones y los doce jobs terminaron aprobados, sin jobs omitidos.

| Validación integrada | Resultado real |
|---|---|
| Backend unitarias / arquitectura | 346 / 4 aprobadas |
| Backend integración | 720 casos únicos aprobados: 241/219/260; preflight crítico repetido aparte |
| Frontend, API del conjunto y contrato OpenAPI en vivo | 518 aprobadas |
| Mobile portable | 235 aprobadas: Core 36, Api 63, Storage 35, Application 101 |
| Android, Mobile sin modificaciones | APK Release arm64, restore x64 y portable antes/después; lockfiles sin diferencias |
| Infraestructura | 221 pruebas Python, fmt/init/validate de ambos módulos, compose, shell y actionlint aprobados |
| Runner k6 real | Aprobado contra servicios controlados; contexto `controlled-no-cloud`, sin carga sobre una instalación real |
| PostgreSQL efímero | Cadena de migraciones con NOSUPERUSER/CREATEROLE/CREATEDB, atributos de roles y aislamiento de hosting aprobados |

Los TRX anteriores no contienen pruebas fallidas ni omitidas. [ci-integrado.json](evidencias/ci-integrado.json) conserva el plan completo, head y merge sintético, jobs, contadores TRX y hashes de artefactos verificados. Incluye los hechos del replay Kafka/MongoDB, SignalR sobre dos API y Mailpit de esta misma ejecución integrada. [k6-controlado.json](evidencias/k6-controlado.json) conserva el resultado del runner; sus métricas describen el entorno controlado, no capacidad productiva. Los artefactos de pruebas/APK tienen retención de 14 días; el artefacto k6, 7 días. El binario Android no se descargó localmente y no se realizó revisión visual nativa.

Los comandos OpenTofu reales se limitaron a los autorizados. Las trazas de acciones administrativas de las pruebas Python son simulaciones con comandos reemplazados por mocks; no ejecutaron apply ni operaron recursos. No se accedió al estado remoto ni se utilizaron credenciales de despliegue.

El commit `99aa4af9bfd03068805ca364194a2112e1de3da3` agregó únicamente este informe y evidencia, sin cambiar fuentes, workflow ni gitlinks respecto de esa ejecución verde. Sin embargo, su [CI 42334710778](https://github.com/NexoRuta/NexoRuta/actions/runs/42334710778) falló: 719 de 720 integraciones aprobaron y el E2E de seguimiento/reprogramación/tablero no alcanzó una proyección vigente en 45 segundos. Esa corrida no se cuenta como verde y la PR no se integró.

Se reprodujo la causa con Kafka real: antes de consumir el primer registro, `Position` permanece sin inicializar; el consumidor omitía el latido de las particiones vacías y la proyección podía quedar atrasada indefinidamente. La [corrección Backend #52](https://github.com/NexoRuta/NexoRuta-Backend/pull/52) usa los watermarks del broker para demostrar que una partición está vacía; si tiene registros y posición desconocida conserva un atraso positivo. No se relajaron los contadores de frontera ni la frescura de 15 segundos.

El usuario autorizó expresamente la excepción necesaria: integrar esa corrección y actualizar únicamente el gitlink Backend, preservando Frontend y Mobile exactos. La prueba nueva falla contra el código anterior y la validación local corregida aprobó cuatro escenarios sin omitidas: particiones vacías/primer evento, E2E completo, paginación pública y replay independiente. Una corrida local intermedia falló por datos de fixture y disposición del worktree; no se cuenta como aprobada. El [CI completo de Backend #52](https://github.com/NexoRuta/NexoRuta-Backend/actions/runs/42336762688) está en curso. El principal valida en paralelo el commit publicado `06a495a35625ba771926e6eca571e148cd016ef2`; antes de integrar se fijará el merge de Backend, con árbol idéntico al candidato aprobado, y se repetirá el CI del conjunto final.

Los [checks de la PR sobre el candidato final](https://github.com/NexoRuta/NexoRuta/pull/74/checks) siguen siendo condición para integrar: se espera su cierre completo en verde y el cumplimiento de las protecciones de GitHub, sin bypass. Los resultados históricos anteriores identifican sus commits y no sustituyen la validación del conjunto corregido.

El guion está en [DEMOSTRACION.md](DEMOSTRACION.md). CU-28 y los demás puntos expresamente fuera de alcance conservan su implementación actual; Kafka interno y correos no se acreditan como webhooks HTTP salientes.
