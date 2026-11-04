# CU06 · B5 — actualización explícita desde GPS sincronizado

2026-11-01. Implementación local de B5, continuación del plan03 y B4 documentado en11. **Llamadas reales deshabilitadas, sin piloto ni migraciones operativas.** No constituye cierre total de CU06 ni certificación de precisión vial en Uruguay.

## 1. Flujo implementado

Backoffice `/rutas` permite **Actualizar estimación desde GPS** para una ruta con salida y ocupación vigente, hasta confirmar retorno. No hay polling, cálculo por cada posición, jobs, notificaciones al destinatario, optimización ni cambios de orden. El cálculo inicial y los horarios manuales permanecen identificados y conservados.

Se reutilizan el estimador secuencial, Geoapify `drive/free_flow`, compatibilidad expresa de vehículo, presupuestos global/operador, límites de tramos, timeout, cancelación y restricciones de transporte B4. Cada intento conserva tipo, actor/comando, versiones, posición fuente, ocupación/jornada/repartidor/vehículo, entradas y resultado en el histórico append-only existente. No hay repositorio, fuente GPS ni cupo paralelo.

**Separación física:** calcular no llama a recepción, rendición, cierre, retorno, liberación ni modifica estados comerciales/custodia. B1 sigue validando capacidades en sus operaciones; B2 sigue siendo la autoridad de ocupación. Finalizar administrativamente sin retornar todavía permite estimar el regreso, pero nunca revierte el cierre.

## 2. Fuente y admisión de GPS

Fuente de verdad: `OperacionJornada` recibida por el servidor, `Tipo=Posicion`, `Resultado=Aplicada`, payload sincronizado del flujo mobile existente. `Datos.PosicionEnUtc` es medición; `RecibidaEnUtc` es recepción. Un dato exclusivamente pendiente en teléfono no se consulta.

- Filtro explícito por operador, ruta y repartidor exactos, con ocupación activa del mismo vehículo/repartidor, adquisición acreditada y sin retorno. Requiere inicio y salida de esa hoja.
- Medición posterior o igual al máximo de adquisición/inicio/salida. Coordenadas finitas y dentro de rango, precisión finita positiva, fechas presentes.
- Se elige entre las admisibles la **medición más reciente**; empate: menor error declarado, luego UUID ascendente. Recepción/secuencia no permiten retroceder la posición. La última medición usada con éxito en esta ocupación fija un piso: ni un umbral de precisión más exigente habilita volver a un punto anterior. Se mantiene íntegro el diario fuera de orden.
- Hasta120s de antigüedad y hasta100m de precisión, límites inclusivos. La tolerancia de futuro es **cero**: no se encontró un contrato de jornada que autorice adelanto del reloj del dispositivo. Es una admisión conservadora, no corrección ni calibración del reloj/GPS.
- Causas explícitas: `SinPosicion`, `GpsAntiguo`, `GpsImpreciso`, `GpsFuturo`, `GpsInvalido`, `GpsOtraEjecucion`, `GpsAnteriorProyeccion`, `EjecucionNoDisponible`. Nunca se fabrican coordenadas ni se usa la base como sustituto.

Configuración única en `RoutingGeoapify:Gps`:

```json
"Gps": { "AntiguedadMaximaSegundos": 120, "PrecisionMaximaMetros": 100 }
```

Antigüedad configurable positiva; precisión positiva hasta el máximo100000m del contrato de captura existente. Defaults definidos en `AdmisionGpsOptions`, configuración validada al arrancar. Cada intento guarda los criterios utilizados y los presenta; no son certificación de exactitud. La lectura del diario es O(n) por ejecución, memoria constante; si escala requiere índices de hechos medidos sobre esa fuente, no otro tracking. No se escanea otro operador. La jornada cerrada no admite nuevas operaciones GPS en el flujo actual: B5 no agrega tracking posterior al cierre; solo aprovecha una medición admisible ya recibida y explica cuándo quedó antigua.

## 3. Pendientes y supuestos temporales

No basta `Activa`: se consideran solo visitas activas de envíos **EnTransito**, sin entrega física. El dominio marca completadas/suspendidas inactivas, pero un intento fallido puede dejar `Activa=true` y estado `NoEntregado`: no se reincorpora como reintento implícito. Se excluyen entregas pendientes de evidencia, devoluciones, cancelados y rendidos/suspendidos. Se mantiene orden y servicio del plan B3.

Origen temporal: instante de captura del cálculo en el servidor; origen espacial: punto medido admisible. No se extrapola velocidad desde GPS. Se cuenta el servicio completo de cada visita pendiente porque el modelo no registra inicio de atención; no se inventa atención ya transcurrida. No se espera hasta la llegada manual.

Sin visitas pendientes se calcula **posición → base del snapshot**, sin servicio adicional; margen B3 una sola vez después del regreso. Hay fechas completas/zona del plan y cruce de medianoche. Regreso estimado y listo previsto nunca significan retorno/liberación confirmados. No se actualiza el catálogo de base ni snapshots anteriores.

## 4. Historia, concurrencia y vigencia

1. Captura bajo transacción corta/bloqueo de operador y revalidación persistida de acceso/permiso `envios.gestionar`.
2. I/O con la conexión independiente ya utilizada por B4, fuera del bloqueo del operador.
3. Nueva transacción/contexto RLS, permisos y entradas releídas; respuesta obsoleta409 sin registro ni horarios/hechos parciales.

La huella B5 incluye ejecución/ocupación/salida/adquisición, posición elegida, perfil confirmado/versión, base/servicios/margen/zona y composición/orden pendientes. **No incluye** hora actual de la relectura ni versión/secuencia general de la hoja: estas también cambian por GPS anterior, evidencia o conflicto sin alterar recorrido. El comando sí exige versión actual al ingresar y conserva esa versión para idempotencia. No se reintenta con versión nueva.

Retorno, liberación/anulación, cambio de pendientes/posición/perfil o de criterios de admisión invalidan. Cambiar peso de ficha sin cambiar perfil no altera el tiempo vial; las guardas de capacidad B1 siguen independientes. Una respuesta cuyo cálculo fue superado por otro intento persistido durante el I/O se rechaza; un éxito posterior invalida la actualización anterior. Repetir exactamente un comando devuelve su registro histórico, nunca lo reaplica ni rejuvenece.

Se conserva el último éxito inicial y durante recorrido incluso si hay más de20 fallos posteriores: primera página devuelve20 registros y hasta2 referencias `EsReferencia=true`, sin romper el cursor de paginación. No se actualizan filas históricas. Un intento fallido no publica tramos ni horarios parciales. Se muestra fecha/antigüedad del último éxito y el fallo posterior. La vigencia de uso se deriva al consultar, con causa de invalidación. **Antigüedad GPS/cálculo no equivale a TTL del proveedor**: Geoapify sigue sin informar caducidad y se presenta desconocida.

## 5. Contratos, UI y persistencia

- Nuevo `POST /api/rutas/{id}/estimaciones/recorrido`: `{comandoId,versionRuta,ocupacionId}`; permiso `envios.gestionar`, operador derivado de identidad.200 es intento registrado, no necesariamente éxito;400 entrada,403 permiso,404 ámbito ajeno,409 versión/ocupación/respuesta obsoleta.
- GET histórico B4 incorpora `tipoCalculo` (`Inicial` / `DuranteRecorrido`), `ocupacionId`, `posicionFuente` (ID/medición/recepción/precisión), `criteriosGps`, `motivoInvalidacion`, `esReferencia`. Manual/calculada y fechas se conservan. Coordenadas se conservan en la entrada privada autorizada, no en el DTO público ni logs/errores.
- API, ApiClient y OpenAPI actualizados conjuntamente. SSR conserva comando/versión/ocupación ante conflicto; botón explícito con prevención de doble envío, teclado/foco y resultado accesible. Los errores de flota no se interpretan como ocupación vigente. No hay skeleton artificial.
- **Sin migración nueva:** tipo/posición/criterios y procedencia de ejecución se agregan a `Entrada` JSONB append-only de B4. No se reescriben registros anteriores; lectura de iniciales históricos y su huella original conservadas. RLS/FK/guardas de inmutabilidad de B4 y diario/ocupación de B2 reutilizados. Mobile no cambia: ya transmite medición y precisión.

## 6. Verificación

Evidencia durable en [evidencias/b5/](evidencias/b5/). Resultados observados, no pruebas meramente encontradas:

| Capa / comando focalizado | Resultado y alcance |
|---|---|
| RED `dotnet test backend/tests/NexoRuta.UnitTests --filter FullyQualifiedName~PosicionProyeccionTests` | Falló compilación porque el contrato B5 no existía; `cu06-b5-red.log`. No se presenta como reproducción de un defecto previo de B1–B4 |
| Unitarias `EstimadorRutaInicialTests / PosicionProyeccionTests / GeoapifyRoutingTests` | **54 aprobadas**, `cu06-b5-unit-delivery.log`:34 núcleo compartido,8 selector/admisión y12 adaptador. Incluyen límites exactos, precisión configurable, NaN, empates, piso temporal tras endurecer precisión, solo regreso, servicio/margen, campos numéricos ausentes, timeout/cancelación y flag apagado |
| B5 HTTP/PostgreSQL | **25 casos B5 comprobados entre lotes**, sin sumarlos otra vez por reejecución: lote `cu06-b5-http-delivery.log` aprobó24/25 (23 B5 + contrato); el caso restante tenía un error en la fixture, corregido y aprobado en `cu06-b5-scope-final.log`. Caso adicional de monotonía y recheck dueño/restringido/concurrencia:4 aprobados en `cu06-b5-monotonic.log`; recheck final de monotonía:1 aprobado en `cu06-b5-final-check.log` |
| Regresión B4 compartida | Lote `cu06-b5-regression.log`:22 aprobadas,14 B5 iniciales +8 B4. Cálculo inicial/historia/manuales/cuotas/HTTP/aislamiento y contrato conservados |
| Regresión afectada B1–B3 | **6 aprobadas** en `cu06-b5-final-http.log`: capacidad vigente/snapshot al despachar2; ciclo B2 cierre/retorno/recepción/liberación/reutilización2; base/plan/medianoche B3 dueño/restringido2. En ese mismo lote31 hubo un error de expectativa B5 para404/cuerpo inválido, corregido y aprobado en el lote siguiente; no se declara que el lote31 completo pasó |
| Contratos frontend | **55 aprobados**, `cu06-b5-contract.log`, contra OpenAPI capturado de TestServer real. Endpoint B5, metadatos GPS/tipo/ocupación y tiempos separados; sin claves/coordenadas en DTO público |
| Navegador/SSR | **2 escenarios aprobados** (B4 y B5) en `cu06-b5-ui-delivery.log`; B5 recompilado/revisado después del último mensaje y ampliada prueba Tab/foco en `cu06-b5-ui-keyboard-final.log`:1 aprobado, no otro escenario nuevo |
| Compilación/modelo | API/Infrastructure/Application y Backoffice/ApiClient compilan al ejecutar pruebas. Modelo sin diferencias: `dotnet ef migrations has-pending-model-changes --project backend/src/NexoRuta.Infrastructure --startup-project backend/src/NexoRuta.Api --context NexoRutaDbContext --no-build`, `cu06-b5-model-final.log`, con conexión dummy no operativa. No se generó ni aplicó migración B5 |

### Escenarios funcionales cubiertos

- `RecorridoUsesReceivedGps…` dueño/SQL restringido: GPS reciente/preciso, todos los horarios completos al cruzar medianoche, servicio/margen una vez, manual/inicial conservados, idempotencia sin nuevo HTTP, recepción fuera de orden sin retroceso, último éxito retenido tras429, sin mutación física.
- `RecorridoRejects…`: ausente, medición antigua recién recibida, imprecisa y futura; cero HTTP y estado/causa explícitos. Selector cubre coordenadas inválidas y umbrales efectivos. `RecorridoDoesNotAdmit…` usa filas históricas sintéticas para separar ruta/repartidor y payload inválido; no presenta esas filas como comandos móviles autorizados.
- `RecorridoExcludesResolvedAndFailed…`: entrega física resuelta y fallo con parada todavía activa se excluyen. `RecorridoOnlyReturns…`: rendición/suspensión excluida y solo regreso, sin recepción ficticia ni servicio duplicado.
- `RecorridoConcurrentNewerResponse…`: el cálculo nuevo persiste; el viejo409, mismo comando simultáneo un registro. `RecorridoRevalidates…`: retorno, liberación, permiso efectivamente retirado, perfil, nuevo GPS y composición cambiada durante I/O invalidan sin guardar resultados obsoletos. Un histórico previo queda invalidado después del retorno.
- `RecorridoProviderFailure… / TimeoutOrCancellation…`:500,404 con cuerpo inválido, timeout y cancelación; sin horarios parciales ni cambios de custodia/hoja/ocupación. Cuota429, contador global concurrente, cupo por operador y llamadas apagadas reutilizan además las pruebas B4 del mismo adaptador/presupuesto.
- `RecorridoRlsHidesActual…`: otra organización no ve posiciones reales de la fixture, ocupación ni histórico. Prueba B4 de tenant/comercio ampliada para POST B5;404/403 y ocupación exacta ajena409.
- `RecorridoRetainsLastSuccess…`:21 fallos posteriores, referencias al éxito inicial/durante recorrido y cursor sin saltar registros. `RecorridoDoesNotRewindAfterAdmissionPrecisionIsTightened`: perfil GPS80m inicialmente admitido; nuevo umbral50m no reutiliza una medición anterior10m. Sin HTTP nuevo, causa y vigencia derivadas.

Los fallos de preparación se conservaron: login con reloj de prueba futuro emitía JWT fuera de la ventana del validador; se hizo login con hora real y luego se movió solo `TimeProvider` del dominio. Las filas históricas directas de una fixture debían estar en UTC y su helper debía seleccionar la ruta exacta al haber dos hojas.404 con texto no JSON corresponde a `RespuestaInvalida`, no a indisponibilidad: se corrigió la expectativa, no el adaptador B4. Un build paralelo produjo error interno CLR; build serial `-m:1 /nodeReuse:false` y pruebas posteriores pasaron. El test Tab inicial suponía un punto de inicio de foco incorrecto; se corrigió para recorrer controles reales, sin modificar el DOM ni eliminar comprobaciones de foco.

Warnings NU1510 y CS8629 ajeno siguen presentes. No se cambiaron reloj del equipo, bases operativas ni reglas para hacer pasar tests.

### Revisión visual real

Chromium **151.0.7922.34**, Razor/Kestrel loopback y API en memoria, tráfico externo bloqueado. Escritorio1440, móvil390 y **320 CSSpx**, sin desbordamiento de página/sección. Capturas generadas e inspeccionadas: [escritorio](evidencias/b5/recorrido-1440.png), [móvil320](evidencias/b5/recorrido-320.png), [conflicto](evidencias/b5/conflicto-mensaje-320.png); [resultado automatizado](evidencias/b5/resultado.json).

Se verificaron separación manual/inicial/actualización, GPS medido/recibido/precisión, fallo reciente y éxito anterior con antigüedad, atribución, caducidad desconocida, regreso/listo no físicos, botón alcanzable por **Tab**, outline de foco visible y activación por Enter. Doble click produce un POST, botón deshabilitado/`aria-busy`;409 conserva UUID, versión y ocupación, sin reintento con token nuevo. Éxito explícito anuncia versión4 mediante `role=status`.

HTTP controlado y PostgreSQL efímero **no demuestran precisión vial real**. El navegador no se presenta como conectado a PostgreSQL ni como aprobación nativa o certificación WCAG de todo el producto.

## 7. Habilitación y pendientes no resueltos

- `RoutingGeoapify:PermitirLlamadasReales=false` sigue en configuración. No se leyeron/reutilizaron claves existentes, contrataron planes ni hicieron llamadas reales; tests usan cadenas sintéticas y handler controlado. Habilitar requiere autorización futura de piloto/credencial dedicada (`RoutingGeoapify__ApiKey`, nunca clave del geocodificador), presupuesto y perfiles constatados. Los umbrales se configuran con `RoutingGeoapify__Gps__AntiguedadMaximaSegundos` y `RoutingGeoapify__Gps__PrecisionMaximaMetros`, sin activar el flag de llamadas como parte de este bloque. Mantener exclusión de logs/spans HTTP salientes y no registrar URLs/coordenadas.
- **Revisión nativa pendiente:** backend ON global/frontend OFF clone-local, preferencias sin cambios. El requisito previo `external.select_intended_untracked` sigue sin capacidad expuesta; no se inventa selección, consentimiento ni aprobación. Sin subagentes por instrucción expresa. Engram sin identidad runtime registrada: trazabilidad local, mirror pendiente.
- **Habilitación operativa pendiente**, incluidos conciliación y artefacto B2 compatible con Stage de procedencia acreditada. No se identificó ni se reconstruyó uno borrando cambios. El binario actual B3–B5 no es evidencia de compatibilidad con Stage.
- Procedimiento07–11 sigue obligatorio: verificar escritores anteriores/jobs/sesiones detenidos y pipeline/migrador deshabilitado; no activar profiles `rls-admin`/`rls-migrator`. `ApplyMigrations=false` del web **no impide** que el comando `database-migrate` aplique anticipadamente todas las pendientes. No ejecutarlo durante la pausa Stage. Conciliación deliberada con artefacto acreditado antes de Enforce; luego esquemas B3/B4. B5 no agrega etapa de esquema.
- Fallo de arquitectura preexistente `ShipmentEndpoints_DeclareApiOwnedResponses` esperado2/actual7 sigue documentado en11. No se debilitó ni se presenta resuelto; no se repite esa suite ajena por rutina.
- Aceptación operativa, revisión nativa y precisión vial en Uruguay requieren constatación/prueba autorizada posterior. No se atribuyen firmas ni hechos físicos a personas.

## 8. Archivos, preservación y objetivo global

[Inventario exacto de23 archivos fuente/contratos/pruebas/configuración](evidencias/b5/archivos-incremento.json). Superficies principales:

- Application: selector `PosicionProyeccion.cs`, contrato/estimador compartido y DTO de histórico.
- Infrastructure: parcial `EfRutasRepository.Recorrido.cs`, extensión de las mismas transacciones/historia B4 y opciones GPS en `GeoapifyRouting.cs`. No se cambian tablas ni capturas de posición.
- API: controller/contratos de estimaciones existentes y appsettings seguro. ApiClient/OpenAPI actualizados.
- Backoffice: parcial de estimaciones y su sección SSR; fixtures/browser/contratos y pruebas backend persistentes. Sin cambios mobile ni dependencias nuevas.

[Preservación](evidencias/b5/preservacion.json):218 archivos locales iniciales conservados, ninguno eliminado;18 de ellos adaptados a B5.10 archivos críticos B1/B2/B3/mobile idénticos byte a byte, incluyendo operaciones de ejecución/capacidad/ocupación/model snapshot. Docs01–11 intactos. Backup TEMP `NexoRuta-B5-initial-af62__4o`. Raíz develop1ef2175; backend fix/zonacobertura a0aa204; frontend fix/zonacobertura e05c0de; mobile fix/zonacobertura78f65e1: ramas/HEAD/gitlinks divergentes preservados. Sin commits, resets, actualizaciones de submódulos, push ni despliegues.

**Objetivo cubierto localmente:** gestión existente de repartidores/vehículos reutilizada; B1 capacidad confiable, B2 ocupación/retorno/liberación, B3 base/plan temporal, B4 inicial vial y B5 actualización explícita desde GPS recibido están implementados. Se mantienen sus niveles de evidencia previos, sin reabrir aceptaciones. Para uso real faltan revisión nativa, habilitación/conciliación y artefacto Stage acreditado, configuración/perfiles constatados y piloto vial expresamente autorizado. **No se declara CU06 completo.**

Risk: items1,2,3,4,5 (formato JSON persistido, alcance/RLS/privacidad, contratos, concurrencia y configuración). B1–B4 y sus aceptaciones se preservan; CU06 no se declara completo.
