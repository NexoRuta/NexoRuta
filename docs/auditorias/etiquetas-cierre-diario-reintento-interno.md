# Etiquetas, cierre diario y reintento interno — 15–16/11/2026

Rama raíz: `fix/etiquetas-cierre-diario-reintento-interno`. Se leyeron `AGENTS.md`,
las guías Cloud, la documentación de reparto/cierre, administración, mensajería,
DLQ y las reglas de diseño antes de editar. El adjunto se revisó como parche de
código; sus comentarios no sustituyeron el pedido. `git apply --check` desde la
raíz del backend pasó contra su base original.

## Base remota registrada e inicialización

| Repositorio | SHA inicial |
| --- | --- |
| NexoRuta `origin/develop` | `c2a8b525e0a81098b6cc56f6655b209820e9953c` |
| backend, gitlink y `origin/develop` | `d355f4725ce1025e45f2f54748ce09babefc11af` |
| frontend, gitlink | `2540041ba267d8a48e6c2b8a644247134f5b47f4` |
| frontend `origin/develop` | `162bf08ec9ad1428fa56dc81b5ce289ac1208a61` |
| mobile, gitlink y `origin/develop` | `8aa3a5fd8a52a089e32e339c8f85dd870f5a8ea8` |

Se inicializaron los tres gitlinks exactos, sin `submodule update --remote`.
Ningún develop de componente estaba por delante del gitlink. Frontend estaba
por detrás: `723d02b` (contrato/foco), `0277e43` (salud) y `2540041` (reconexión)
ya formaban parte de la base raíz. Se revisó esa diferencia y se conservó esa
base para evitar regresiones al fijar el nuevo frontend. No se incorporaron
otros avances remotos en esa inicialización. `main` y los despliegues de producción quedaron fuera.

Antes del merge, backend `develop` avanzó a
`41e1930332770b74a556306f4e277e6aae669748` por la PR de documentación #61.
Se revisaron sus dos commits (`44ae9d2`, `31756d6`): únicamente Markdown en 21
archivos, sin cambios de ejecución ni pruebas C#. Se incorporó esa base ya
integrada y se actualizaron tres referencias que aún describían AP-09 y el
reintento administrativo como pendientes. El código de ejecución/pruebas quedó
idéntico a `83572cd`; el head con documentación actualizada es
`1b6c9a6616ae7880e0d65dfa581a81fae6a41e0b`. Se vuelve a exigir CI completo.

## Cambios y PR

- [Backend #58](https://github.com/NexoRuta/NexoRuta-Backend/pull/58): P1
  (PR duplicada cerrada; commit incluido en #59),
  commit `5d0016b1d5dbd1e41a262fade2470b9c952952fe`. ID aplicado en SQL antes
  de materializar, con filtro/proyección compartidos y transacción RLS.
- [Backend #59](https://github.com/NexoRuta/NexoRuta-Backend/pull/59): PR final
  con los tres cambios en commits separados. Reintento administrativo en
  `44f0af09bea8a1d622933a261775851b890c2e2a`.
  Selección por operador/permisos, auditoría inmutable e identidad de solicitud,
  sin reemplazar MessageId, payload ni el circuito normal.
- [Backend #60](https://github.com/NexoRuta/NexoRuta-Backend/pull/60): AP-09.
  La decisión quedó confirmada el 15/11/2026: cerrar jornadas EnCurso al terminar
  su fecha operativa, en la zona de su política, preservando custodia/incidencias/
  evidencia y rechazando nuevas operaciones físicas. El Worker queda activo conforme
  a esa regla; no depende de sesión móvil ni intervención manual. La implementación
  base `26cef46` se completa con `e827c90df7d8902845b500efe2a491a1e0c8b0d2`.
  Quedó integrada por #59, que incluye su head completo y las correcciones de CI.

El reintento implementado es de **publicación fallida** en outbox RabbitMQ/Kafka;
los fallos de consumo conservan los mecanismos de DLQ/recibos existentes. Los
mensajes publicados, procesados, reservados o de otro ámbito quedan excluidos.
Correos, Push y el reenvío HTTP de webhooks conservan sus circuitos específicos.
El commit `6c54d4f0cfc8add702b87fd11fd4b7ae254f9882` endurece la selección
con recibos técnicos y de Kafka; seguimiento en curso
queda excluido mediante el mutex de su consumidor. Detalles
en [backend](../../backend/docs/workflow/reintento-mensajes-internos.md) y
[frontend](../../frontend/docs/reintento-mensajes-internos.md).

## Validación local

SDK 10.0.401 y restores con locks. Solo datos sintéticos y clústeres/brokers
propios efímeros. No se usan `.env`, servicios del usuario ni bases operativas.

- Etiquetas 2/2: PDF, listado intacto, ID en SQL, transacción y acceso cruzado
  con PostgreSQL 18/PostGIS real y rol API restringido.
- Reintento 3/3: autorización/RLS, aislamiento, auditoría inmutable, repetición y
  concurrencia; recibo Kafka y mutex del consumidor activo. Recuperación por
  Worker/publicador/consumidor RabbitMQ 4 real y duplicado sin segundo efecto.
- AP-09 acordado 7/7: servicios con reloj/timers controlados y PostgreSQL real;
  dos Workers cruzan el corte, omiten no elegibles/futuras y recuperan tras
  rollback/reinicio. Zona histórica conservada al cambiar política; custodia,
  ocupación, secuencia y evidencia dentro de plazo preservadas.
- Fixtures de CI corregidas 3/3 con PostgreSQL/Kafka reales. La combinación
  previa al caso adicional de elegibilidad dio 14/14; la elegibilidad final 3/3.
- Contrato RLS histórico 10/10: lista exhaustiva de claves, incluida
  `traceparent`, y comprobación de su migración de correlación ya existente.
- Proyección operativa y rollback 2/2 con PostgreSQL, Kafka y MongoDB reales:
  recuperación documental, reproducción aislada e historial sin cambios.
- Regresiones reparto/RLS/outbox 104/104 con PostgreSQL y Kafka reales.
- Frontend final: 521 aprobadas/5 opt-ins ajenos omitidos. Contratos 58/58 contra
  API real e igualdad estricta de 149 rutas. UI 3/3: dos HTTP de respuesta incierta
  y Chromium a 1440/320 px con API controlada, teclado, errores y vacío. El progreso
  se inspeccionó deteniendo una vez el submit después del handler real y
  enviando después el mismo formulario. Revisión visual independiente: tres
  correcciones puntuadas resueltas.
- Infraestructura raíz: 347 pruebas Python, 344 aprobadas y 3 omitidas.
- Workflows raíz: actionlint 1.7.12 aprobado, con la misma excepción del
  workflow vigente para la clave `concurrency.queue` aún no reconocida.
- Migraciones y hosting: cadena completa en PostgreSQL local NOSUPERUSER /
  NOBYPASSRLS; provisión repetida, roles restringidos, key rings aislados,
  monitor sin payloads y cuotas concurrentes comprobados. Sin conexión GCP.

## CI e integración

[Frontend #62](https://github.com/NexoRuta/NexoRuta-Frontend/pull/62) se integró
con CI en verde: `d8a81a2a5d7d24810148ee72c647573586463324`.
[CI frontend](https://github.com/NexoRuta/NexoRuta-Frontend/actions/runs/43773892601):
526/526 aprobadas, incluidas las seis pruebas de navegador optativas, sin
omisiones. Su árbol coincide
con el head validado `dfe0a4e7f5800cfd2bad69598d0ac954931d77a1`.

CI de backend detectó fixtures previas desactualizadas: una usaba el JWT viejo
tras cambiar la contraseña; dos publicaban Kafka sin la correlación exigida por
el consumidor. Se corrigieron en un commit propio de pruebas: se exige401 a la
  sesión revocada y se consulta con la nueva; los eventos usan el contrato vigente.
No se debilitaron validaciones de aplicación ni aserciones de idempotencia.
Las tres fixtures corregidas pasaron 3/3 con PostgreSQL/Kafka reales. Commit
de pruebas: `84ff627c9e36c4a800389c86ffb69a06d3d8215d` en #59; cherry-pick
`314396645a65f18fe0202991c2cc3cf3ee036f34` en #60.

La ejecución siguiente detectó otra fixture desactualizada: su lista explícita
de claves RLS omitía `traceparent`, presente en la base. El commit exclusivo
de pruebas `073f51a101aedfb35ea767b54b5e99530f1dfab0` incorpora la clave y la
migración histórica que la consume; conserva la igualdad exhaustiva y pasó
la clase completa (10/10).

El grupo restante detectó dos fixtures adicionales. La prueba de proyección
operativa publicaba Kafka sin sus cabeceras obligatorias; ahora conserva
EventId/CorrelacionId al reproducir el mismo evento con el contrato vigente.
La cancelación pública comprobaba el texto de la última migración irreversible,
que cambia al añadir migraciones: ahora comprueba `NotSupportedException`, la
lista completa de migraciones aplicada sin cambios y la conservación de la
cancelación/código consumido. No se habilitó ningún rollback destructivo.
Commit de ambas fixtures: `83572cdc972becb007d0c15fece445e64683e070`.

Backend #59 se integró después de aprobar todos los checks de
[Backend CI](https://github.com/NexoRuta/NexoRuta-Backend/actions/runs/43780497258):
391 unitarias, 7 de arquitectura y 770 de integración, sin omisiones, además del
flujo crítico repetido por separado. Cobertura Domain 92,33% y Application
94,24%, ambas por encima del umbral obligatorio. El árbol integrado
`ad63712d649b4c178f75ebecf7ac3aa3b0e3d3d5` coincide con el head validado
`1b6c9a6616ae7880e0d65dfa581a81fae6a41e0b`.

Gitlinks finales de esta integración:

| Componente | Commit integrado/preservado |
| --- | --- |
| backend | `ad63712d649b4c178f75ebecf7ac3aa3b0e3d3d5` |
| frontend | `d8a81a2a5d7d24810148ee72c647573586463324` |
| mobile, sin cambios | `8aa3a5fd8a52a089e32e339c8f85dd870f5a8ea8` |

El CI raíz resuelve los gitlinks y comprueba el contrato OpenAPI contra la API
construida desde ese backend. La variable nueva habilita también la prueba de
navegador de mensajes internos. Antes de mergear la PR raíz se exige que todos
sus checks estén en verde y que los logs de checkout coincidan con esta tabla.
Ningún resultado local se presenta como resultado de CI. No quedan decisiones
de negocio pendientes para los tres cambios de este encargo.
