# Registro de validación

La implementación se integró en `develop` mediante las PR [Backend #49](https://github.com/NexoRuta/NexoRuta-Backend/pull/49) y [Frontend #51](https://github.com/NexoRuta/NexoRuta-Frontend/pull/51), después de sus checks finales verdes y sin omitir protecciones.

Candidato Backend: `655edd3a2f2e2326e7a9d99bb2a405b81ee7b6e8`. Frontend: `7ce3e969924e1157d2eaa80b5c933bea9560f5b0`. Mobile conserva `f2b3db412ce23b0b36215fd301f6d3d3d6959252`.

El [CI final de Frontend](https://github.com/NexoRuta/NexoRuta-Frontend/actions/runs/42306859258) aprobó 518 pruebas. El [CI final de Backend](https://github.com/NexoRuta/NexoRuta-Backend/actions/runs/42306868322) aprobó 346 unitarias, 4 de arquitectura y 720 casos únicos de integración (241/219/260 por shard). El preflight repite además un caso crítico de decisión operativa; no se suma como un caso distinto. No hubo fallos ni omitidas en esos reportes finales.

Gitlinks publicados del conjunto:

| Repositorio | Merge en develop / gitlink |
|---|---|
| Backend | `a7c1de8fae4859385082a2e7065704d3dc7d4fe6` |
| Frontend | `06b1ca380aea0ec68dbbaafff5de9a63a24d8f6b` |
| Mobile, sin cambios | `f2b3db412ce23b0b36215fd301f6d3d3d6959252` |

Los árboles de ambos merges coinciden exactamente con los candidatos validados. No hubo avances concurrentes de sus bases durante el cierre. [ci-final.json](evidencias/ci-final.json) conserva SHAs, corridas, contadores TRX, identidades y hashes SHA-256 de los artefactos descargados. Los artefactos crudos del CI tienen retención de 14 días; los resúmenes y hechos seleccionados permanecen versionados aquí.

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

La [PR principal #74](https://github.com/NexoRuta/NexoRuta/pull/74) apunta a `develop` y conserva los gitlinks publicados de ambos hijos ya integrados y Mobile sin cambios. La consulta remota confirmó la base en `25ffb1d8a7f34bb17623a99357d0b7b743ba8404`, antecesor del candidato, sin avances concurrentes.

El [CI integrado completo 42333366312](https://github.com/NexoRuta/NexoRuta/actions/runs/42333366312) terminó con **success** sobre el head `15aef02f9393f128f6f67c5edbd53061b95b1cb6`. GitHub ejecutó el checkout de merge sintético `ef9f184c461a6d210802e2ce5924837cf7992744`, con los tres gitlinks de la tabla anterior. El plan activó todas las validaciones y los doce jobs terminaron aprobados, sin jobs omitidos.

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

El commit que guarda este informe solo agrega documentación y evidencia; no cambia fuentes, workflow ni gitlinks respecto de la ejecución citada. Los [checks de la PR sobre el candidato final](https://github.com/NexoRuta/NexoRuta/pull/74/checks) son la condición adicional para integrar: se espera su cierre completo en verde y el cumplimiento de las protecciones de GitHub, sin bypass. La cobertura por capa continúa referenciada al gate independiente de los hijos, cuyos árboles permanecen idénticos.

El guion está en [DEMOSTRACION.md](DEMOSTRACION.md). CU-28 y los demás puntos expresamente fuera de alcance conservan su implementación actual; Kafka interno y correos no se acreditan como webhooks HTTP salientes.
