# CU-06 B2 — aceptación funcional aislada

Fecha: 01/11/2026. Punto de partida: checklist de [07](07-aceptacion-b2.md), contrastado con el checkout local y ejecutado por capas sobre datos controlados.

**Resultado: aceptación funcional aislada aprobada; B2 técnicamente verificado.** Revisión nativa y habilitación operativa **pendientes**, por motivos distintos. No se declara CU-06 completo ni se inicia B3. No se atribuyen firmas, inspecciones físicas o aceptación humana a ninguna persona.

## Alcance de esta ejecución

- Backend: API/casos de uso/dominio/repositorios reales mediante TestServer y PostgreSQL/PostGIS efímero de `PostgresFixture`. Contenedor propio, bases aleatorias e identidad verificada; la fixture ignora conexiones externas. Se aplicaron migraciones **solo en esas bases de prueba**.
- Interfaz: runner de navegador existente con Kestrel loopback, Razor/CSS/JS reales y API simulada en memoria. Se ejecutó únicamente ese Fact, no otra suite amplia.
- Aviso de éxito: había evidencia del conflicto 409 en navegador, pero no una ejecución de la rama SSR de liberación exitosa. Se agregó **solo un probe temporal fuera del checkout**, reutilizando `BackofficeFactory`, sesión, antiforgery, PageModel y FakeApi. El probe devuelve 200 en memoria y verifica redirección, listado actualizado y `role="status"`. No pretende probar persistencia: esta la prueban los casos de backend.
- No es un único recorrido de navegador conectado a una API/base reales. Es aceptación aislada por capas con límites de evidencia explícitos. Los actores, rutas, vehículos y confirmaciones de las fixtures son sintéticos; un POST llamado «retorno» o «recepción» no acredita un movimiento físico real.
- No se modificaron aplicación, contratos, migraciones ni pruebas del checkout. Solo documentación y evidencia. B1/B2 y los gitlinks divergentes se conservaron; ramas/HEAD siguen siendo los de 06. Sin commits, despliegues ni modificaciones de datos operativos.

## Resultado esperado, observado y evidencia por paso

Los resultados de backend indicados abajo fueron comprobados por las aserciones ejecutadas de las pruebas, no inferidos por la existencia de código. Los IDs B/E/V/S se resuelven a nombre completo, resultado y duración en [resultados.json](evidencias/aceptacion-aislada/resultados.json).

| Paso de 07 | Resultado esperado | Resultado observado en aislamiento | Evidencia |
|---|---|---|---|
| 1. Despachar A, iniciar, cargar y salir | Adquirir ocupación propia y aplicar operaciones autorizadas | Despacho 200; `InicioJornada`, `CargarBulto` y `ConfirmarCarga` devuelven `Aplicada`. Se utiliza la ocupación adquirida por A. No se acredita una salida física. Las regresiones de capacidad B1 ya aprobadas en 06 se conservan, sin repetir toda esa suite. | B06, B07; `OcupacionFlotaHttpTests.Ciclo.cs` |
| 2. Cerrar con pendientes | Jornada cerrada con incidencia; custodia y ocupación conservadas | `FinJornada` aplicada; hoja `Finalizada`, un bulto pendiente y retorno null. La incidencia conserva bulto/envío/versión y el bulto sigue `Repartidor`, vinculado a su ruta/custodio. | B06, B07, E01, E02 |
| 3. Consultar otra fecha | Pendientes de A visibles con fecha original y enlace | Navegador real mantiene visible la ocupación antigua del fixture al cambiar de `20/10/2026` a `03/02/2027`; enlace con `fecha=2020-01-02`. La fixture UI es independiente de los UUID de A del backend, no una consulta a la base efímera de ese caso. | V01; runner existente `FlotaBrowserTests.cs` / `tests/browser/cu06-b2.cjs` |
| 4. Retorno sin descarga | Registrar retorno sin resolver custodia u ocupación | Confirmación 200 y repetición idéntica con la misma respuesta. La liberación posterior con carga pendiente sigue rechazándose; custodia `Repartidor` y `LiberadaEnUtc=null`. Se admite resolver la ocupación aun con vehículo administrativamente inactivo. | B06, B07 |
| 5. Liberación incompatible | 409 sin mutación parcial | API devuelve 409. SQL confirma que no hay liberación y que la custodia se conserva. El mismo comando/versión de liberación puede aplicarse después de la recepción: el rechazo no consumió un hecho de liberación ni alteró su versión. La UI no ofrece liberar con carga pendiente. | B06, B07; V01 distingue «retornado con carga» de «listo para liberar» |
| 6. Recibir carga | Resolver custodia sin borrar la incidencia ni inventar estado comercial | Endpoint real de depósito devuelve 204 en la base efímera. La lectura posterior muestra `Deposito`, conserva la incidencia y mantiene el envío `EnTransito`; no lo transforma automáticamente en `Reprogramado`. Es simulación del comando, no recepción física constatada. | E01, E02; `CierreConIncidenciaEsIdempotenteConservaCustodiaYPermiteRecepcionFisicaPosterior` |
| 7. Liberar y actualizar listado/aviso | Liberación confirmada con versión exacta; disponibilidad y aviso accesible | API 200, replay idéntico, listado sin ocupaciones y última liberación no null; incidencia histórica conservada. En SSR, el POST exitoso redirige y el GET actualizado elimina el ID de ocupación, muestra `Disponibilidad confirmada` y «Confirmación de flota registrada» en `role="status"`, con un solo POST. | B06, B07 para persistencia; S01 para PageModel/Razor con respuesta API simulada |
| 8. Usar B y reenviar A | B sigue ocupando; A no puede liberar B | Tras reactivar administrativamente el vehículo, se planifica y despacha B el mismo día: 200. Replay exacto de liberación de A: 200 sin tocar B. Nuevo UUID con ocupación/versión antigua de A: 409. SQL identifica B como la ocupación activa y solo un hecho de retorno/liberación de A. | B06, B07 |
| 9. Anular autorización nunca iniciada | Liberar sin retorno ficticio ni cancelación de envíos | Anulación 200 y replay 200; ocupación inactiva por anulación, `RetornoEnUtc` y `LiberadaEnUtc` null, ruta `Cancelada`, envío `AsignadoRuta` y custodia `Deposito`. Se conserva historial; no se cancela el envío. | B01, etapa 0 |
| 10. Anular con inicio o carga | Rechazar sin borrar ocupación/custodia | 409 en etapas 1/2/3: inicio, carga y salida. Ocupación activa y hoja `EnCurso`; custodia `Deposito` antes de cargar y `Repartidor` después. No se fabrican retorno ni liberación. | B02, B03, B04 |

### Garantías complementarias reutilizadas

Se ejecutaron las verificaciones existentes, sin duplicar su implementación:

- **B08:** dos despachos concurrentes producen exactamente un 200 y un 409; una segunda ocupación por SQL en otra fecha viola unicidad (`23505`).
- **B05/B15:** medianoche y sincronización tardía no liberan; la planificación futura se conserva y otra ocupación bloquea el despacho.
- **B09:** otro vehículo no permite eludir la ocupación del repartidor.
- **B10/B11 y variante B07:** autorización, tenant, RLS y diario inmutable; el comercio y un rol sin autoridad no confirman hechos ajenos. No se reabrió una auditoría general de permisos.
- **B12:** planificación futura permitida y despacho futuro rechazado sin mutaciones.
- **B13/B14:** históricos desconocidos sin retorno/actor inventados; conflictos legados detienen la segunda etapa. Anulación/conciliación explícitas permiten activarla en la fixture, sin seleccionar silenciosamente un ganador ni convertir todas las jornadas cerradas en ocupaciones eternas.

## Ejecuciones y reproducibilidad

| Lote ejecutado | Resultado final | Límite de lo que prueba |
|---|---|---|
| `OcupacionFlotaHttpTests*` existentes | **15/15** | Flujo funcional, persistencia, idempotencia, exclusión, RLS y transición en PostgreSQL efímero |
| Recepción tras cierre con incidencia, propietario y restringido | **2/2** | Custodia real del modelo/persistencia y conservación del historial en fixtures |
| `FleetBrowserUsesRealRazorAndIsolatedApiFixture` existente | **1/1** | Renderizado/interacción, fecha independiente, conflicto y doble envío; API simulada |
| `IsolatedAcceptanceReleaseRefreshesFleetAndAnnouncesSuccess`, probe temporal | **1/1** | Rama de éxito del PageModel y HTML actualizado/aviso, API simulada |
| **Total** | **19 aprobadas, 0 fallos, 0 omitidas** | Aceptación funcional aislada, no firmas físicas ni aprobación nativa |

Se usó el runner existente, serializado para backend mediante `.runsettings` temporal (`MaxParallelThreads=1`, `ParallelizeTestCollections=false`). Los TRX y logs crudos están en `%TEMP%/NexoRuta-B2-functional-ebe82c9379c840a4b2e9db6901cb2fd8/`. El [resumen JSON](evidencias/aceptacion-aislada/resultados.json) conserva casos/resultados y hashes de TRX y fuentes; no exporta secretos, conexiones ni tokens. Las capturas nuevas de V01 permanecen en el subdirectorio temporal `browser/`; las capturas revisadas de 07 se conservan sin sobrescribir.

Comandos de los lotes existentes:

```powershell
dotnet test backend/tests/NexoRuta.IntegrationTests --no-restore --settings <runsettings-temporal> --filter FullyQualifiedName~OcupacionFlotaHttpTests --logger 'trx;LogFileName=backend.trx' --results-directory <evidencia-temporal>
dotnet test backend/tests/NexoRuta.IntegrationTests --no-build --settings <runsettings-temporal> --filter FullyQualifiedName~CierreConIncidenciaEsIdempotenteConservaCustodiaYPermiteRecepcionFisicaPosterior --logger 'trx;LogFileName=deposito.trx' --results-directory <evidencia-temporal>
# Mismas variables de navegador documentadas en 07, con salida en TEMP:
dotnet test frontend/tests/NexoRuta.ApiClient.Tests --no-build --filter FullyQualifiedName~FleetBrowserUsesRealRazorAndIsolatedApiFixture --logger 'trx;LogFileName=frontend-browser.trx' --results-directory <evidencia-temporal>
```

El [probe de éxito conservado como evidencia textual](evidencias/aceptacion-aislada/frontend-success-probe.cs.txt) se compiló exclusivamente en un proyecto temporal que referencia los mismos hosts y reutiliza las fuentes/fixtures de pruebas actuales. El handler temporal sustituye únicamente la respuesta de flota por un 200 y un listado sin ocupación. La primera preparación de ese proyecto falló por una ruta relativa al snapshot OpenAPI; se corrigió **solo en TEMP** y luego pasó. No fue un defecto del producto ni motivó cambios en el checkout.

No se repitieron las suites amplias de 06/07. El fallo de arquitectura preexistente `ShipmentEndpoints_DeclareApiOwnedResponses` —esperado 2 / real 7— sigue explícito y separado; no se modificó ni se presenta resuelto por esta aceptación.

## Comprobación del procedimiento de despliegue

**El procedimiento sí identifica expresamente cómo impedir una segunda etapa anticipada.** Se volvió a contrastar 07 con el código/configuración local; esto no inspecciona ni acredita la configuración efectiva de un ambiente operativo:

1. `Program.cs`, rama `database-migrate`, llama `MigrateAsync()` **sin destino**. Deshabilitar `DatabaseInitialization__ApplyMigrations` solo controla el arranque web; **no frena ese comando**.
2. Por eso 07 exige **deshabilitar el job/pipeline externo y no activar `rls-admin`/`rls-migrator`**, cuyo comando es `database-migrate`. Tampoco ejecutar el pipeline completo de entrega, que no pausa entre etapas. No se cambió ni se ejecutó ninguno aquí.
3. Generar/aplicar **solo el SQL Stage** con límites exactos, sin concatenarlo con Enforce. La factory de diseño no configura conexión; no confiar en que un `database update` sin conexión explícita tome el destino de appsettings.
4. Mantener el arranque administrativo B2 con `ApplyMigrations=false` y `SeedData=false`, escritores viejos detenidos, y comprobar en `__EFMigrationsHistory` que existe Stage y **no Enforce**. Es el control verificable entre etapas, no una suposición basada en un flag.
5. Solo después de conciliar y autorizarlo, aplicar **Enforce** explícitamente. B14 ejercitó su rechazo por conflicto y su éxito posterior en una base efímera; no se aplicó a operación ni se debilitó el precheck.

Se conserva el procedimiento de 07 para inventariar/detener escritores de todos los nodos y comprobar sesiones, sin asumir que un balanceador drenado o un `pg_stat_activity` momentáneamente vacío basten. Ese inventario y sus resultados efectivos **siguen pendientes de habilitación operativa**, no forman parte del resultado automático aprobado.

## Tres estados separados al cierre

1. **Aceptación funcional aislada: aprobada. B2 técnicamente verificado.** Se ejecutaron los pasos automatizables del checklist y se documentaron sus límites. No se encontraron defectos reproducibles que requirieran modificar la aplicación.
2. **Revisión nativa: pendiente.** Se conserva la limitación `external.select_intended_untracked` de 07 y las preferencias existentes. Ni los tests ni esta revisión propia equivalen a aprobación nativa.
3. **Habilitación operativa: pendiente.** Requiere autorización de mantenimiento, respaldo, pausa efectiva de migrador/escritores, configuración/historial por etapas y conciliación física/auditable por los responsables autorizados. No se atribuye a QA, operador o depósito una firma o constatación no realizada.

CU-06 no se declara completo. B3 permanece fuera del alcance.
