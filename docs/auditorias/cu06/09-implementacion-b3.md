# CU-06 · B3: base operativa y planificación temporal

Fecha: 2026-11-01. Fuente: checkout local, incluidos B1/B2 sin commit. No publicación remota.

## Resultado y límites

Se implementa **B3 de la tabla1 de03**, contrastado con03§4 y04§5/6: una base por operador, confirmación explícita del punto, parámetros temporales, salida prevista, fechas completas y snapshot histórico. **No** incluye los tramos ni el cálculo de ETA/regreso de B4, ni GPS de B5. La sección conjunta B3/B4 de03 no autoriza adelantar el proveedor vial.

B2 conserva la aceptación técnica de08. Las comprobaciones compartidas son regresiones por cambios en HojaRuta, serialización, migración y formularios; no una nueva aceptación de B2. No se tocaron capacidad/precisión B1, tarifas, importación, custodia, diario, retorno/liberación ni comandos offline.

| Requisito B3 | Implementación y resultado |
|---|---|
| Una base propia, no dirección de contacto/marca | `BaseOperativa`, PK por operador; API sin selector de tenant, permiso existente `configuracion.gestionar`; RLS de operador en PostgreSQL |
| Dirección y punto confirmados | Dirección hasta500 caracteres; coordenadas finitas/rangos válidos, actor e instante UTC del servidor, versión. Cambiar dirección invalida punto, actor e instante; editar solo tiempos los conserva |
| Geocodificar no confirma | Reutiliza `IGeocodificador`, atribución y rate limit existentes. Propuesta con dirección/versión; confirmación separada; propuesta obsoleta recibe409. Fallo503 no bloquea coordenadas manuales |
| Servicio y margen | Minutos enteros no negativos, opcionales; vacío significa desconocido, cero solo explícito. Servicio por parada admite override; sin override captura el valor de base al planificar y del snapshot de destino al reasignar |
| Salida prevista distinta de real | `SalidaPlanificadaEnUtc` dentro de fecha operativa de la política IANA; `SalidaEnUtc` sigue siendo el hecho de ConfirmarCarga. La planificación no inicia ni ocupa recursos físicos |
| Llegadas completas | Se conserva el nombre contractual `LlegadaEstimadaUtc`, pero se presenta como **manual**. Fecha local por parada admite días posteriores; orden respeta llegada más servicio anterior, no precede salida prevista |
| Historia | Snapshot inicial: base/versión/punto/confirmación, zona, salida, servicio/margen, orden de envíos y versión inicial de hoja. No se sobrescribe al editar base, capacidad o composición; SQL rechaza su modificación. Las paradas actuales conservan su propio servicio |
| No inventar ETA | `EstadoEstimacion=SinEstimacion` y motivo: sin paradas, metadata ausente, base sin confirmar, salida ausente, tiempos desconocidos o proveedor B4 pendiente. No se agrega un regreso numérico ni se libera por una hora |

## Flujo y contrato

- Backoffice **Configuración de reparto → Base operativa de salida y retorno**: guardar dirección/minutos; consultar propuestas si el proveedor existente está habilitado; revisar y confirmar coordenadas explícitamente. Formularios SSR con antiforgery, etiquetas, estado/alertas y mecanismo existente `data-single-submit`.
- Versionado optimista:0 significa alta todavía inexistente; primera base guardada tiene versión1. Cada cambio/confirmación incrementa. Reintento obsoleto recibe409, preserva entradas y token; no se reintenta con la versión de una consulta posterior.
- `GET/PUT /api/reparto/base-operativa`; `POST .../propuestas`; `POST .../confirmacion`. Coordenadas no provienen de un body de planificación ni de un tenant elegido por el cliente.
- Recursos de planificación expone la base propia por el permiso existente de rutas; no requiere otorgar administración de configuración al planificador. Solo el permiso de configuración permite modificarla.
- Planificar acepta salida prevista y `ServicioMinutos?` por parada; reasignación acepta el override opcional. Hoja responde snapshot, servicio, motivo y salida real. ApiClient y `frontend/contracts/nexoruta.openapi.json` se actualizan conjuntamente; no aliases de compatibilidad.
- En `/rutas/planificar`, fecha operativa, salida prevista y llegada manual tienen campos separados. El resumen SSR/JS muestra fecha y hora completas, conserva unidades B1. En `/rutas` se identifica el plan histórico frente al hecho de salida, sin confundir retorno físico y base geográfica.
- Mobile no necesita un nuevo comando ni cambiar ejecución: su consumidor de hoja admite los campos informativos adicionales. Una prueba verifica el parseo con llegada al día siguiente y conservación de custodia/incidencia; no se añade UI móvil de estimación.

## Persistencia y habilitación futura (no ejecutada sobre operación)

Migración aditiva **`20261101203256_AddOperationalBaseAndTemporalPlan`**: tabla `BasesOperativas`, `HojasRuta.PlanTemporal` jsonb nullable y `ParadasRuta.ServicioMinutos` nullable, checks y políticas RLS. API puede leer/crear/actualizar su base; worker/PUBLIC no reciben permisos. Confirmación SQL exige actor del contexto; snapshot inicial inmutable. No se insertan bases, coordenadas, minutos, actores ni retornos históricos. Down rechaza borrar datos B3 existentes: no es un mecanismo de reversión operativo destructivo.

Se generó y aplicó únicamente mediante fixtures propietarias Testcontainers/PostgreSQL18; nunca `database-migrate`, `database update`, migración ni conciliación sobre base operativa. Modelo EF sin cambios pendientes respecto de la migración.

### Dependencia importante con la transición B2

**El binario B3 no es el binario administrativo para una base detenida en Stage B2**: su modelo consulta columnas/tablas B3 todavía inexistentes. No se introduce un fallback de compatibilidad parcial. Antes de habilitarlo:

1. Ejecutar el procedimiento07/08 bajo control del responsable de operación/DBA: escritores anteriores detenidos y comprobados, migrador automático/job/pipeline externo deshabilitado; no activar `rls-admin`/`rls-migrator`. `DatabaseInitialization__ApplyMigrations=false` y `SeedData=false` frenan el arranque web, **no** la rama `database-migrate`, que llama MigrateAsync sin destino.
2. Si B2 aún requiere conciliación entre sus dos etapas, usar un **artefacto B2 preservado y compatible con Stage**, con acceso administrativo restringido, antes de Enforce. Su disponibilidad y autorización deben constatarse; no se da por existente/aprobado un build ni se sustituye por el ejecutable B3. Sin ese artefacto o un mecanismo administrativo explícitamente aprobado, detener la habilitación, no saltar la conciliación.
3. Comprobar inventario de procesos/contenedores/jobs y sesiones DB conforme07, antes/después de la pausa; no basta `docker compose stop` para demostrar que no hay otros escritores. Verificar `__EFMigrationsHistory`: Stage presente y Enforce ausente durante conciliación. Ni medianoche ni ausencia de conexiones puntuales acreditan hechos físicos.
4. Tras resolución documentada de conflictos/verificación inicial de B2, aplicar Enforce de forma deliberada. Solo entonces aprobar/aplicar el SQL acotado **Enforce → AddOperationalBaseAndTemporalPlan**, inspeccionado por DBA. No usar el job que aplica todas las pendientes para la etapa anterior. No se ejecutó ninguno de estos pasos sobre operación.
5. Verificar historia de las tres migraciones y RLS; iniciar API/Backoffice B3 juntos, con migración/seed automáticos aún deshabilitados. Cada operador configura su dirección, confirma realmente su punto y elige minutos; lo desconocido permanece desconocido.

Las fixtures de transición B2 se adaptaron para ejecutar **sus rangos SQL explícitos**, conservando el esquema aditivo B3. Antes intentaban bajar toda migración posterior para recrear legado: el nuevo guard de Down rechazó correctamente descartar snapshots B3. Se conservan sus aserciones de conflictos, custodia, conciliación e historia; no se debilitó el guard ni la exclusión. Este ajuste de pruebas no es una instrucción de despliegue ni de downgrade operativo.

## Verificación observada

Evidencia en [evidencias/b3/](evidencias/b3/). Pruebas encontradas no se cuentan como ejecutadas.

| Capa | Ejecución / resultado |
|---|---|
| RED previo | 3 HTTP iniciales fallaron por endpoint/metadatos ausentes; SSR falló por sección ausente. Regresión adicional de creación concurrente falló **OK/OK** antes de corregir el token inicial |
| HTTP B3 | `BasePlanificacionHttpTests`:7 casos aprobados, incluidos rol SQL restringido, snapshot tras editar base, cruce de medianoche, desconocidos, invalidaciones, propuestas sin guardar, proveedor no disponible, conflicto concurrente, rechazo temporal atómico y aislamiento HTTP/RLS |
| Migración histórica B3 | Caso adicional aprobado: parte exactamente de Enforce B2, inserta hoja histórica sintética sin campos B3 y aplica la nueva migración; snapshot/salida siguen null, sin base ni ocupación inventadas. Ver `cu06-b3-migration-history.log` |
| Reasignación temporal B3 | Caso adicional aprobado: destino vacío con snapshot5min, base actual cambia a9min; llegada al día siguiente hereda5min, snapshot/orden inicial no se reescriben. Entrada negativa rechazada sin mutaciones. La fixture inicial sin asignación fue corregida para usar ruta origen planificada, sin relajar la regla de custodia/estado. Ver `cu06-b3-reassignment-final.log` |
| Dominio | Suite `NexoRuta.UnitTests`:229 aprobadas, incluidas2 nuevas de snapshot/servicio/cronología, punto inválido y ausencia de mutaciones |
| Mobile | `NexoRuta.Mobile.Core.Tests`:36 aprobadas, incluida lectura B3 multifecha con custodia/incidencias intactas |
| SSR/cliente | 3 casos B3 aprobados: estado desconocido, contrato de fechas locales/UTC/servicio y Chromium;14 regresiones focalizadas de configuración/rutas/DST aprobadas |
| Contrato publicado |54 pruebas `OpenApiContractTests` aprobadas contra snapshot actualizado copiado por build; incluye nueva regresión de endpoints/campos B3. Ver `cu06-b3-client-contract-current.log` |
| JS | `node --test frontend/tests/rutas-planificacion.test.cjs`:1 aprobada; unidades B1 conservadas. El resumen ahora escucha también cambios de fecha de parada |
| Regresión compartida | Lote capacidad/rutas/ocupación:41 aprobadas,2 fallos iniciales de fixture al intentar bajar B3 con datos. Corregido el rango de fixture, **esas2** aprobaron; no se volvió a ejecutar el lote completo ni se reabrió aceptación B2 |
| Compilación | API/Domain/Application/Infrastructure/Worker y proyectos frontend/ApiClient compilados al ejecutar pruebas;0 errores. Advertencias NU1510 y CS8629 preexistente de DetalleModel |
| Modelo | `dotnet ef migrations has-pending-model-changes ... --no-build`: sin diferencias de modelo; no aplica migraciones |
| Arquitectura | **Preexistente y no resuelto**: `ShipmentEndpoints_DeclareApiOwnedResponses`, esperado2/actual7; suite2 aprobadas/1 fallida, mismo baseline B1/B2 |

### Navegador real, no solo HTML/HTTP

Runner persistente `frontend/tests/browser/cu06-b3.cjs`, Chromium151.0.7922.34, Razor real en Kestrel loopback y API en memoria. Tráfico externo bloqueado, ninguna base operativa. Se comprobó guardar → proponer sin confirmar → confirmar explícitamente → conflicto que conserva datos/versión → editar dirección e invalidar punto; teclado/foco en campos etiquetados, fecha siguiente/servicio y actualización del resumen. Anchos1440/390/320 CSSpx, sin desborde de página ni campos de parada. Se corrigió un recorte real de los nuevos campos a320px; capturas finales inspeccionadas, no aprobación nativa.

Capturas: [base escritorio](evidencias/b3/base-1440.png), [base320](evidencias/b3/base-320.png), [conflicto320](evidencias/b3/conflicto-320.png), [plan escritorio](evidencias/b3/plan-1440.png), [plan320](evidencias/b3/plan-320.png), [resultados del navegador](evidencias/b3/resultado.json). Las capturas son fixtures sintéticas independientes de la base de las pruebas HTTP: no se afirma un E2E de navegador conectado a PostgreSQL ni una constatación de ubicación física.

## Archivos y preservación

- Backend: nuevos `BaseOperativa.cs`, `BaseOperativaDatos.cs`, contratos/controlador API de base, `BaseOperativaConfiguration.cs`, parcial `EfConfiguracionRepartoRepository.Base.cs`, migración/Designer, `BasePlanificacionHttpTests.cs` y `PlanTemporalTests.cs`.
- Integración: interfaces/caso de uso existentes de configuración; DTO/contratos/controller de rutas, HojaRuta/ParadaRuta, sus configuraciones, DbContext/model snapshot, repositorio de rutas/reasignaciones. Solo se añaden datos temporales y su validación; capacidad/ocupación siguen sus reglas anteriores.
- Frontend: nuevo contrato ApiClient de base y parcial PageModel/vista `_BaseOperativa`; cliente de configuración y contrato de hoja; ConfiguracionReparto, RutasModel, vistas Rutas/Planificar, CSS/JS de planificación, OpenAPI; nuevas pruebas B3 y ampliación acotada de FakeApi.
- Tests B2 de transición: solo acotación SQL descrita arriba. Mobile: solo regresión de lectura en `IncidenciasCierreTests.cs`; implementación móvil B2 sin cambio.
- Git inicial: raíz develop `1ef21751106e727bb15f4f75d3976196857e2ca1`; backend fix/zonacobertura `a0aa204ffc3390606b9f04bc8a57424b598c205c`; frontend fix/zonacobertura `e05c0de27702cf9909656bed0a0d389152c25806`; mobile fix/zonacobertura `78f65e1ca534888270028d68e7abe86460989e12`. Gitlinks ya divergentes, conservados. Inventario inicial/archivos nuevos y copias con hashes en TEMP `NexoRuta-B3-initial-9q390mng`; ningún archivo local previo eliminado. Las superficies compartidas cambian por B3, no se reemplazan por HEAD remoto.

## Pendientes reales

- **Revisión nativa pendiente**: backend global ON; assess declara high/unassessable por archivos no seguidos. STATUS exige `external.select_intended_untracked`; la capacidad correspondiente no está expuesta en este runtime. No se inventó selección/aprobación, ni se cambiaron preferencias ni se reiteró indefinidamente. Frontend mantiene su OFF local previo. Revisión propia, pruebas y capturas no son aprobación nativa.
- **Habilitación operativa pendiente**: responsable de operación/DBA debe verificar escritores detenidos, transición B2, artefacto administrativo compatible, migración B3 y permisos. Cada operador debe constatar dirección/punto y elegir tiempos; las fixtures no acreditan estos hechos.
- B4: decidir/autorizar proveedor y semántica de convivencia con manuales; luego tramos viales, estimación inicial y regreso con calidad/instante. B5: política GPS/recálculo. Nada de esto se implementó.
- Fallo de arquitectura anterior pendiente. Engram sin identidad de sesión registrada: trazabilidad local en documentos/logbook; no se afirma memoria guardada.

**CU06 no se declara completo.** B3 aporta la configuración y los datos temporales verificables; no disponibilidad por ETA, no retorno geográfico automático y no optimización de rutas.

Risk: items1,2,3,4 (migración aditiva/RLS, contrato y serialización, bloqueo compartido por operador). Sin delegación por instrucción vigente; revisión nativa no disponible, no aprobada.
