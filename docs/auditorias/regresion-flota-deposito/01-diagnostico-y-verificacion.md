# Regresiones de pruebas de Flota/Depósito

Corte del 03/11/2026, desde el principal publicado `317c706adb095e8c88c305114aca902711b57678`. Gitlinks comprobados: Backend `9a35b8b292e74a98a55f3e22eab8097bd0d7eb9a`, Frontend `d470cfd999faccc90fcfcc99672e50531716c29e`, Mobile `74a25f1b5b18c7dfc006cf7df747d73b0ec4910a`. Las puntas remotas del corte de sesión coincidían con el checkout limpio antes de crear `fix/regresion-flota-deposito` en principal y Frontend. No hicieron falta ramas nuevas de Backend/Mobile.

## Requisitos y comportamiento contrastados

Fuentes: enunciado `docs/alcance/Laboratorio__NET_2026.pdf`, apartado 5.2, requisitos 6 (gestión de vehículos/capacidad) y 10 (recepción mediante escaneo, verificación y discrepancias); planilla `Casos de Uso - Responsables.xlsm`, hoja **CU obligatorios**, filas 9 (CU-06) y 13 (CU-10). No se ejecutaron macros ni se interpretaron colores como evidencia. El enunciado no exige mezclar disponibilidad global, lista diaria e historial en una página ni recibir todos los bultos de un envío admitido mediante una sola confirmación.

Se contrastaron además `frontend/DESIGN.md`, [diseño compartido](../rediseno/01-diseno-compartido.md), [recepción CU-10](../cu10/01-aceptacion.md), los consumidores reales y las pruebas de separación por tarea existentes en la misma base. Este corte no cambia ni acepta otros CU ni la base pendiente de revisión humana.

| Fallo reproducido | Causa comprobada | Corrección que preserva su intención |
| --- | --- | --- |
| `FailedFleetHistoryAndRoadQueriesStayExplicitInsteadOfPretendingEmptyData(NotFound)` | La prueba pedía que `/rutas` mostrara fallos de consultas que deliberadamente no ejecuta. `RutasModel.Cargar` consulta Flota solo en Flota/detalle e historial solo en detalle. La lista diaria tiene su propia regresión que prohíbe esas consultas globales. | Verifica la lista sin consultas globales, luego `/flota`, `/rutas/{id}` y configuración. Cada consulta debe haberse realizado y su pantalla debe mostrar HTTP 404; la flota queda desconocida, sin conteos inventados ni falsa lista vacía; el historial no puede mostrarse vacío ni vigente; el perfil vial no puede darse por confirmado. |
| `FailedFleetHistoryAndRoadQueriesStayExplicitInsteadOfPretendingEmptyData(InternalServerError)` | La misma expectativa anterior fallaba también con HTTP 500, antes de llegar a comprobar el historial y el perfil. No era un fallo de recuperación de API del producto. | Conserva el caso separado de HTTP 500 y las mismas garantías. Se comprueban los códigos en cada superficie pertinente, no solo un error genérico en otra parte de la página. |
| `DepotDefersPhysicalReceiptToExplicitShipmentContext` | Exigía `handler=Recibir` al seleccionar un envío `Admitido`, aunque CU-10 reemplazó la primera recepción masiva por cotejo individual. El handler masivo conserva su función para retornos. `_Deposito` ya enlaza al cotejo por código; `RecepcionModel` carga el bulto, declara versiones/comando y no escribe en GET. | La prueba exige ausencia de recepción masiva antes y después de seleccionar; sigue el enlace real al cotejo de `TEST`, comprueba GET autenticado al endpoint vigente, envío/bulto correctos, formulario explícito, requisito de presencia física, discrepancias, dos bultos pendientes, versiones 8/2 y comando no vacío. Navegar no puede emitir POST de recepción ni otro payload operativo. |

**Los tres casos eran pruebas desactualizadas; no se encontró una regresión funcional en esas tres rutas de ejecución.** No se cambió producto, interfaz, contratos, permisos, reglas, autenticación ni fixtures de backend. Se actualizaron solo tres archivos de pruebas frontend. No se borraron casos, no se agregaron Skip ni exclusiones, y el total de casos se conserva.

En `FakeApi` se agregó únicamente una respuesta de consulta de recepción opcional, usando el DTO vigente `ConsultaRecepcionResponse`, para poder seguir el enlace real hasta el formulario. No se implementó ni se simuló una nueva operación de recepción en esa fixture. El resto de pruebas conserva el comportamiento previo cuando no configura ese dato.

La prueba vecina `DepotReceiptPreservesTaskSearchAndExactVersionInPrg` estaba pasando con un estado `Admitido` que ya no corresponde a recepción masiva. Se cambió solo su dato inicial a `EnDevolucion`: mantiene intactas sus aserciones de búsqueda, filtro, página, PRG y versión exacta del POST, y ahora representa el retorno que conserva legítimamente ese circuito. No se reintrodujo compatibilidad con recepción masiva inicial.

## Evidencia ejecutada

Suite completa del proyecto `frontend/tests/NexoRuta.ApiClient.Tests`, **sin `--filter` ni exclusiones**:

| Ejecución | Aprobadas | Fallidas | Optativas omitidas | Total |
| --- | ---: | ---: | ---: | ---: |
| Base sin cambios | 473 | 3 | 5 | 481 |
| Corrección | 476 | 0 | 5 | 481 |

Los dos HTTP y el caso de Depósito son exactamente los tres fallos de la base. Todos pasan tras corregir sus expectativas. La suite también incluye permisos, antiforgery, versiones, cancelación, recuperación de sesión, expiración, rechazo demorado y aislamiento del contexto de páginas. No se retiraron aserciones para aceptar una flota/historial vacío ante error: se reforzaron los controles de consulta efectiva y de ausencia de datos inventados.

Adicionalmente, `node --test frontend/tests/*.test.cjs`: **21 aprobadas, 0 fallidas, 0 omitidas**.

Datos exclusivamente sintéticos de las fixtures en memoria. Los tests ejecutan los portales Razor reales con API controlada; **no se presentan como una nueva integración PostgreSQL ni como prueba de navegador real**. No hubo cambios de producto que requirieran otra validación visual, de migraciones o de persistencia. No se operó sobre la prueba manual Mobile, ni sobre datos de servicios habituales. Backend/Mobile y la corrección de sesión quedan intactos. El origen del 401 histórico de arranque sigue sin determinar.

Los resultados TRX completos quedaron fuera de Git en `/workspace/.regresion-flota-deposito/{baseline,complete}`. No se publican logs, bases, certificados ni artefactos temporales.

## Optativas omitidas, informadas por separado

Estas cinco pruebas ya son optativas en la base y se omitieron por no activar sus variables de navegador; no se modificaron sus condiciones:

| Prueba | Activación existente |
| --- | --- |
| `BaseBrowserUsesRealRazorAndIsolatedApi` | `NEXORUTA_B3_BROWSER_DIR` |
| `DestinationSearchSelectSaveEditAndManualFallbackInChromium` | `NEXORUTA_DESTINATION_BROWSER_DIR` |
| `RoadEstimatesUseRealRazorWithIsolatedControlledData` | `NEXORUTA_B4_BROWSER_DIR` |
| `FleetBrowserUsesRealRazorAndIsolatedApiFixture` | `NEXORUTA_B2_BROWSER_DIR` |
| `RoadUpdatesShowGpsManualInitialAndConflictInRealChromium` | `NEXORUTA_B5_BROWSER_DIR` |

No se contabilizan como aprobadas. Tampoco se repitió la prueba manual Mobile ni se cerró CU-06. Gentle-AI/Engram y revisión nativa siguen sin herramientas disponibles; no se afirma haber ejecutado esa revisión opcional. Se revisaron requisitos, código, diff y resultados completos.

## Reproducción

Desde el checkout integrado, con SDK 10.0.401 y dependencias ya restauradas según la continuidad Cloud:

```bash
source scripts/cloud/env-agent.sh
export DOTNET_CLI_HOME=/workspace
export NUGET_PACKAGES=/workspace/.cache/nuget-packages
export NUGET_HTTP_CACHE_PATH=/workspace/.cache/nuget-http
dotnet test frontend/tests/NexoRuta.ApiClient.Tests --no-restore
node --test frontend/tests/*.test.cjs
```

Para comparar la prueba roja, usar en otra carpeta el principal base `317c706` con sus gitlinks exactos y ejecutar los mismos comandos. No cambiar el checkout de trabajo ni sustituirlo por checkpoints antiguos. Conservar las optativas sin activar permite comparar los mismos 481 casos; activarlas requiere los prerrequisitos Chromium/Playwright documentados por sus fixtures.

## Revisión e integración posterior

Revisar primero la base pendiente, luego las pruebas del Frontend y finalmente el gitlink/documentación del principal. Solo se publican ramas propias `fix/regresion-flota-deposito`, primero Frontend y después principal. No se ejecutan merges ni force-push. Backend y Mobile conservan sus gitlinks.

## Publicación

Frontend publicado en `fix/regresion-flota-deposito`: `bf36df3d02f6e4c9b098d5545a3483f4c6dea15e`, un commit que modifica solo los tres archivos de pruebas descritos. El principal publica esta documentación y apunta a ese commit; Backend permanece en `9a35b8b292e74a98a55f3e22eab8097bd0d7eb9a` y Mobile en `74a25f1b5b18c7dfc006cf7df747d73b0ec4910a`.

Para revisar en otra carpeta:

```bash
git clone --branch fix/regresion-flota-deposito --recurse-submodules https://github.com/NexoRuta/NexoRuta.git NexoRuta-regresion
cd NexoRuta-regresion
git submodule status
```

Después ejecutar la suite completa y los tests Node con los comandos anteriores. La revisión no requiere servicios ni datos del Windows del usuario.
