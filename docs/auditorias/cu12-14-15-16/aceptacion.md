# CU-12, CU-14, CU-15 y CU-16 — auditoría y aceptación

Base remota comprobada el 03/11/2026: `fix/cu0708`, principal `486633d`, Backend `9ad5c86`, Frontend `a65c131`, Mobile `74a25f1`. Trabajo en `feature/cu12-14-15-16`. No se aplica el manifiesto antiguo de `scripts/cloud/checkpoint.json` como base de aplicación.

## Fuentes e interpretación

Enunciado `docs/alcance/Laboratorio__NET_2026.pdf`, §5.2 requisito 12 y §5.3 requisitos 14–16. Planilla `Calcs/Casos de Uso - Responsables.xlsm`, hojas CU obligatorios filas 15, 17–19; Dependencias D04–D07 y D13–D24; Alcance aplicaciones AP-03, AP-07, AP-08. Se leyó el contenido, no los colores. Se contrastó además la auditoría existente de historia `envios/13-implementacion-historial-inmutable.md` y la matriz de transiciones `envios/11-matriz-transiciones-y-brechas.md`.

La planilla exige zona y ventana comprometida. La admisión existente registra zona/modalidad y referencia exacta a la revisión de cobertura, pero no selecciona una única franja ni una fecha de promesa. Se interpreta la compatibilidad como pertenencia de la llegada manual **y todo su servicio** a alguna franja activa de esa revisión histórica, en su zona horaria. No se inventa una promesa de fecha, no se usa la configuración actual y no se altera el precio. Una futura selección de una ventana individual requerirá ampliar el contrato de admisión; esta implementación no acredita ese contrato inexistente.

El enunciado excluye optimización obligatoria. CU-16 conserva el criterio actual: orden explícito del despachador, validado cronológicamente por llegada manual y fin del servicio anterior. Backoffice ordena por el entero `Orden` antes de enviar; el dominio asigna posiciones consecutivas y rechaza solapamientos. Empates de llegada solo son admisibles si el servicio previo es cero; desempata el orden explícito recibido. No se reordenan horarios ni snapshots, no hay proveedor externo. Las reasignaciones agregan al final y deben respetar esa cronología; las rutas despachadas no admiten agregar paradas.

## Diagnóstico y cambios

| CU | Existía / evidencia disponible al comenzar | Brecha y cambio |
| --- | --- | --- |
| 12 | Historia canónica PostgreSQL mediante triggers, transacciones, identidad de actor, correlación, RLS y prohibición de UPDATE/DELETE/TRUNCATE; operaciones móviles idempotentes con fecha física/GPS y persistencia propia. Tests de rollback de historia/outbox y migración con corte explícito. | `RecibirAsync` comprobaba el estado anterior después de mutarlo y perdía `RecepcionDeposito` como origen. Se captura la condición antes del cambio y se prueba origen/responsable persistidos. Se reutiliza el escritor canónico; no se crea una historia paralela. |
| 14 | Máximo en planificación/incorporación por reasignación; capacidad acumulada de todos los bultos mediante `CapacidadCarga`, controles vigentes en despacho y carga física de salida; cronología con servicio. | Faltaba comprobar franjas. Se reutiliza la revisión de cobertura del cargo de admisión y se valida antes de cambios en planificación, reasignación, despacho y confirmación de carga/salida. Se revalida máximo en despacho/salida. Sin revisión verificable se rechaza con conflicto. Reasignación valida también paradas destino. |
| 15 | Bloqueo transaccional de operador, índice único de parada activa, estado/versiones y transacción conjunta. | El test anterior competía también por los mismos recursos. Ahora usa vehículos/repartidores distintos, mantiene un bloqueo desde una tercera transacción y observa dos sesiones PostgreSQL esperando antes de liberarlo. Exige un éxito, un 409, una sola ruta/parada, un único evento y reintento sin nuevas escrituras. |
| 16 | Orden manual explícito, posiciones persistidas únicas, cronología incluyendo servicio, snapshot inicial inmutable y prohibición tras despacho. `PlanTemporalTests` comprueba servicio/medianoche/snapshot. | Se documenta el criterio existente y se conserva. No se agrega una heurística que sobrescriba decisiones manuales. |

Las fixtures publican una cobertura sintética de siete días y su revisión, para que las pruebas de reparto no dependan del día de ejecución. La producción no recibe cambios de cobertura ni tarifas.

## Verificación reproducible

Usar .NET SDK 10.0.401 y Docker PostgreSQL18/PostGIS. No hace falta levantar los portales para estas pruebas HTTP de API real con PostgreSQL. Las fixtures crean y migran sus bases exclusivas; no toman datos del runtime ni del taller.

```bash
source scripts/cloud/env-agent.sh
export NUGET_HTTP_CACHE_PATH=/workspace/.cache/nuget-http
export NUGET_PACKAGES=/workspace/.cache/nuget-packages
export DOTNET_CLI_HOME=/workspace
dotnet test backend/tests/NexoRuta.UnitTests --filter 'FullyQualifiedName~Reparto'
dotnet test backend/tests/NexoRuta.IntegrationTests --filter 'FullyQualifiedName~Reparto&FullyQualifiedName!~Browser'
dotnet test backend/tests/NexoRuta.IntegrationTests --filter 'FullyQualifiedName~EnvioEventsHttpTests|FullyQualifiedName~EnvioHistoryMigrationTests|FullyQualifiedName~RlsRestrictedHttpFlowTests'
```

En una PC se pueden omitir las tres variables de caché o apuntarlas a directorios propios. No ejecutar el instalador con su aserción de SHAs del manifiesto antiguo para mover la aplicación a ese checkpoint.

Resultados de esta ejecución:

- Unitarias de reparto: **66/66**, incluidos 10 casos nuevos de franjas y los tests existentes de cronología/snapshots.
- Mobile Core: **36/36**, suite completa portátil.
- Primera regresión amplia: 162/169; siete fallos demostraron que un helper de flota creaba envíos secundarios sin cargo/cobertura. Se completó ese dato sintético, conservando las aserciones.
- Segunda regresión amplia: **174/175**; pasan flota, roles restringidos, historia, migraciones, capacidad, límites y snapshots. El único fallo fue el inicio de sesión del segundo actor nuevo de la prueba concurrente: faltaba su hash de contraseña sintética. Se corrigió el helper y se repitió toda la clase `RutasHttpTests`: **18/18 aprobadas**, incluyendo la competencia con dos identidades reales y espera PostgreSQL sincronizada.
- Ninguna prueba omitida. No se cuentan los fallos de preparación como aprobaciones. Los resultados de la segunda regresión y de la repetición final se informan por separado; no se afirma que una única invocación amplia terminó verde.

Los dos fallos de preparación del nuevo harness (conexión sin contraseña desde una connection string ya saneada por Npgsql, y actor sintético sin credencial) se corrigieron usando `IntegrationDatabase.ConnectionString` original de la fixture y el hasher de autenticación sintética existente. No se cambió autenticación del producto ni se diagnostica con ello el 401 intermitente pendiente.

| Evidencia ejecutable | Requisito / aserción relevante |
| --- | --- |
| `EnvioEventsHttpTests.HistoryAndLaterOutboxFailuresRollbackTheWholeShipmentCreation` | CU-12: fallo forzado en historia y luego outbox revierte alta completa; fallo en historia de cancelación revierte estado y efectos. |
| `EnvioHistoryMigrationTests.MigrationMarksTheCutoverAndBackfillsOnlyAuditedCancellations` | CU-12: migraciones en PostgreSQL, sin reconstruir hechos anteriores sin respaldo. |
| `RlsRestrictedHttpFlowTests.ShipmentHistoryRlsSeparatesCommerceAndOperatorRows` y primer test de esa clase | CU-12: lectura por operador/comercio, permisos reales e inmutabilidad incluso frente a intentos directos de modificación. |
| `RutasHttpTests.RecibirPlanificarDespacharYDescargarConservaVersionPoliticaYDestino` | CU-12: origen `RecepcionDeposito`, responsable autenticado y correlación persistidos; flujo planificación/despacho/descarga. |
| `VentanaRutaTests` (10 casos) | CU-14: inicio incluido, fin excluido, fin de servicio en límite incluido, exceso rechazado, día local y franja nocturna. |
| `HistoricalCoverageRequiresArrivalAndWholeServiceInsideWindow` (3 casos) | CU-14: aplicación real en PostgreSQL, límites de franja/servicio y rechazo sin ruta/paradas/eventos parciales. |
| `PlanningUsesAdmittedCoverageRevisionAfterLiveWindowsChange` | CU-14: cambiar las ventanas actuales no cambia el compromiso histórico admitido. |
| `ExactStopLimitUsesShipmentsAndPreservesExplicitOrder` (2 casos) | CU-14/16: máximo exacto aceptado, exceso rechazado sin asignaciones, empate cronológico conserva orden explícito y snapshot. |
| `CapacidadVigenteHttpTests` | CU-14: múltiples bultos, límites de peso/volumen exactos, acumulación, capacidad vigente en despacho/reasignación/salida física parcial, preservación de snapshots y aislamiento de operador. |
| `DosPlanificacionesConcurrentesSoloAsignanUnaVez` | CU-15: dos actores y transacciones independientes con recursos distintos, espera PostgreSQL observada; un éxito/un 409, un evento, una parada y reintento sin duplicación. |
| `PlanTemporalTests`, `RepartoRestrictedHttpTests`, `OperacionesRepartoHttpTests`, `OcupacionFlotaHttpTests` | CU-12/14/16 y regresiones: cronología/servicio/snapshot, rol API real, reintentos offline, custodia y ocupación separadas de estado comercial. |

## Límites preservados

Sin cambios visuales, contratos HTTP, esquema/migraciones, precios, RLS ni clientes Mobile/Frontend. No se verifica navegador responsive porque no hay cambio de interfaz. Mobile Core: 36/36 aprobadas con lock portátil en `obj/cloud.packages.lock.json`, sin modificar el lock Android versionado. Los envíos legados sin una referencia de cobertura verificable requieren revisión explícita antes de planificar; no se inventan ventanas retrospectivas. La confirmación de salida valida el plan manual; no convierte una sincronización offline tardía en una nueva llegada estimada ni modifica el instante físico informado.

Prueba manual Mobile del 02/11/2026 y 401 intermitente siguen pendientes; CU-06 permanece abierto. No se usan sus datos. Gentle-AI, memoria Engram y revisión nativa no aparecen entre herramientas/skills disponibles; no se afirma haberlas ejecutado. Se usa inspección de fuentes, diff y pruebas disponibles. La preparación Docker y restore se ejecutaron con acceso de red habilitado y cachés en workspace; el primer restore con caché predeterminada falló por filesystem de solo lectura.

## Revisión e integración posterior

Revisar primero el diff Backend y ejecutar las suites anteriores. Obtener luego el principal con sus gitlinks mediante `git submodule update --init --recursive`. Integrar Backend antes del principal que referencia su commit publicado; Frontend/Mobile conservan los SHA de la base. No se ejecuta integración a otras ramas ni se crea PR.

## Publicación

Backend publicado: `feature/cu12-14-15-16`, commit `3ebf059`. Principal: misma rama, gitlink Backend actualizado a ese commit; los gitlinks Frontend `a65c131` y Mobile `74a25f1` se conservan. Los SHA completos del principal y la comprobación final de clon remoto limpio se entregan en el cierre de la tarea. No se modificaron ramas ajenas, no hubo merge ni force-push.
