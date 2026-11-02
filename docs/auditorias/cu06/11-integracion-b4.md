# CU06 · B4 integrado y verificado con HTTP controlado

Fecha: 2026-11-01. **Integración implementada; llamadas reales deshabilitadas.** Este documento continúa10 después de la aprobación explícita de Geoapify `drive/free_flow` y horarios paralelos. No declara CU06 completo, piloto habilitado ni precisión vial comprobada en Uruguay.

## 1. Alcance implementado

| Requisito | Implementación / evidencia |
|---|---|
| Perfil explícito por vehículo | Estado inicial `SinDeterminar`; opciones `DriveConfirmado` / `NoCompatible`. Confirmar drive exige casilla expresa y motivo. Se registra recurso exacto, actor, instante UTC del servidor y versión. Nunca se deduce del peso, volumen, matrícula o condición de «liviano» |
| Solo perfil autorizado | Sin confirmación específica no se llama al proveedor; resultado `PerfilPendiente`. Un recurso `NoCompatible` tampoco usa drive ni cae silenciosamente en otro perfil. La interfaz pide configurar/confirmar y explica el perfil de automóvil |
| Adaptador Geoapify | Host fijo `https://api.geoapify.com/v1/routing`, `mode=drive`, `traffic=free_flow`, unidades métricas, formato JSON, dos puntos por tramo. No optimiza ni utiliza GPS. Valida una ruta/un tramo y tiempo/distancia presentes, finitos y no negativos |
| Manuales / calculadas | Conserva `LlegadaEstimadaUtc` manual de B3. Respuesta e interfaz separan manual, llegada calculada y salida calculada. Cálculo sin esperas por manuales; una diferencia no se presenta como retraso real |
| Historia | Registro append-only con comando, actor, ruta/versión, número de cálculo por ruta, entrada/snapshot/huella y resultado/procedencia. GET ordenado por versión descendente, páginas de20 mediante `antesDeVersion`; ningún cálculo nuevo borra anteriores |
| Respuesta obsoleta | Captura entradas en una transacción corta y vuelve a leerlas bajo el bloqueo del operador antes de guardar. Cambiar ruta/versión/vehículo/perfil durante I/O produce409, descarta la respuesta y no agrega un cálculo ni altera horarios |
| Idempotencia | Repetir mismo comando/actor/ruta/versión devuelve el registro existente sin duplicarlo. Reusar comando con otros datos/actor se rechaza. Dos intentos simultáneos pueden haber iniciado I/O antes de encontrarse; la garantía es un registro por comando, no exactamente una consulta externa |
| Procedencia / vigencia | Geoapify, modelo `drive/free_flow`, sin tráfico, atribución e instante del cálculo en NexoRuta. La API no informa caducidad: queda **desconocida**, no se inventa TTL. La fecha representa elaboración/recepción en NexoRuta, no una certificación del instante de generación de datos del vendedor |
| Histórico invalidado | Cambios de entradas invalidan su uso como cálculo vigente, sin actualizar el JSON histórico. El plan conserva base/punto/salida/servicios del snapshot B3; editar el catálogo de base no lo reemplaza silenciosamente |
| Hechos físicos separados | Regreso estimado y listo previsto con margen no confirman retorno, recepción, descarga, custodia ni liberación. No se invocan comandos físicos ni el diario de ejecución desde B4 |

El [contrato oficial Routing](https://apidocs.geoapify.com/docs/routing/) distingue `free_flow` de tráfico aproximado y devuelve tiempos/distancias por tramo. No se añadió una aproximación geométrica ni una promesa de restricciones de camión. La persona responsable debe confirmar compatibilidad real del vehículo con el perfil; los registros sintéticos de tests no acreditan esa constatación.

## 2. Flujo, autorización y transacciones

1. **Configuración de reparto → Compatibilidad con perfil vial**, permiso existente `configuracion.gestionar`: seleccionar compatibilidad, confirmar expresamente drive cuando corresponda, indicar motivo y guardar con versión.
2. **Rutas → Estimaciones viales sin tráfico**, permiso `envios.gestionar`: Calcular/Recalcular explícito, solo sobre ruta Planificada o Despachada. EnCurso/Finalizada conservan consulta histórica, no un cálculo inicial que se confunda con B5.
3. Actor y operador provienen de identidad validada, nunca del body. Se capturan base B3, salida prevista, paradas activas/destinos confirmados/servicios, margen, perfil y versiones.
4. I/O fuera del bloqueo. El middleware RLS existente conserva su transacción de autorización durante la petición: B4 usa **otra conexión del mismo DbContext/repository**, no un repositorio paralelo, para confirmar/liberar sus dos transacciones cortas. No cambia ese middleware compartido.
5. Cada fase aplica contexto RLS y revalida acceso/versión de sesión/organización activa y permiso vigente con los repositorios existentes. Tras I/O toma nuevamente el bloqueo del operador y compara huella completa; solo entonces agrega historia.

La reserva diaria, capacidad vigente, ocupación física exclusiva, inicio/carga/salida, custodia, D18, retorno/liberación y sincronización mobile no se cambian. Se ejecutaron regresiones compartidas por los nuevos campos/lecturas de hoja, no una reapertura de aceptación B2.

### API / consumidores

- `GET /api/reparto/perfiles-viales` y `PUT /api/reparto/perfiles-viales/{id}`: recurso propio; compatibilidad, confirmación expresa, motivo y versión.400 por entrada inválida;404 para recurso ajeno/no encontrado;409 por versión.
- `POST /api/rutas/{id}/estimaciones`: `{comandoId, versionRuta}`.200 significa **intento registrado**, que puede contener Calculada o un estado de fallo tipado; no equivale a una estimación utilizable.409 por solicitud/respuesta obsoleta o comando conflictivo; sin registro nuevo en ese caso.
- `GET /api/rutas/{id}/estimaciones?antesDeVersion=...`: histórico propio con vigencia derivada, sin modificarlo.404 oculta ruta ajena; permisos y comercio no autorizado reciben403.
- DTO API propios, ApiClient y snapshot OpenAPI actualizados conjuntamente. `HorarioVialResponse` separa fechas manual/calculada; `TramoVialResponse` expone procedencia/modelo/atribución, no URI, clave ni cuerpo externo.
- La hoja B3 conserva sus campos; ahora su estado de estimación consulta el último registro y detecta versiones de ruta/vehículo/perfil cambiadas. No continúa diciendo «sin proveedor B4» después de un cálculo.
- Sin cambio de comandos ni UI mobile. No se inicia B5 ni se utiliza la última posición.

## 3. Configuración segura, consumo y errores

Configuración agregada a `backend/src/NexoRuta.Api/appsettings.json` y validada al arrancar:

```json
"RoutingGeoapify": {
  "PermitirLlamadasReales": false,
  "MaxSolicitudesDiaGlobal": 1000,
  "MaxSolicitudesDiaOperador": 100,
  "MaxTramosCalculo": 51,
  "SolicitudesPorSegundo": 4,
  "TimeoutSegundos": 8
}
```

- **No se activó ni se debe activar como parte de esta entrega.** Una habilitación posterior requiere autorización de destino/credencial/piloto y presupuesto. La clave dedicada sería `RoutingGeoapify:ApiKey` —por Secret Manager o variable autorizada `RoutingGeoapify__ApiKey`—; no está en el archivo ni se toma de `Geocoding:Geoapify:ApiKey` o Mapbox. Sin flag verdadero **y** clave dedicada, cero reservas/llamadas HTTP.
- Límites configurables de **solicitudes**, no un presupuesto monetario ni equivalencia garantizada con créditos Geoapify. Tramos/opciones/distancia pueden afectar créditos; geocodificación tiene consumo aparte. No se contrata ni se aumenta un plan automáticamente.
- Contadores persistentes diarios UTC, global y por operador, se reservan atómicamente mediante función SQL con bloqueo global corto. Incluye turnos separados por la tasa configurada. La espera es **relativa calculada por PostgreSQL**, sin asumir relojes host/DB idénticos. Se observó un timeout durante el desarrollo con resta entre relojes; se eliminó esa dependencia, sin afirmar que se midió un desfase concreto.
- Los cupos se conservan aunque falle/cancele la consulta o la respuesta resulte obsoleta; no se reembolsan automáticamente. Son reservas de intentos, no medición del instante exacto del egress ni de facturación del vendedor. La tasa reserva turnos; no constituye SLA de red.
- Máximo configurable por cálculo1–501 tramos, sin reducir límites de planificación/carga. Por defecto51. Ventana de cálculo/I/O de30s (no incluye las fases DB, sujetas a cancelación del request y timeout de comandos); timeout por petición8s configurable1–30s, incluye espera/cuerpo (el HttpClient no impone otro timeout fijo que contradiga esa configuración); cancelación del llamador se propaga. Respuesta máxima64KiB por tramo. **Sin reintentos automáticos.**
-429/cuota o presupuesto agotado: `CuotaExcedida`; sin ruta: `RutaNoEncontrada`; timeout: `TiempoAgotado`; red/5xx/autenticación externa: `ProveedorNoDisponible`; respuesta incompleta/inválida: `RespuestaInvalida`; deshabilitado/sin clave: `ProveedorNoConfigurado`. Error en un tramo no publica una secuencia parcial ni ceros ficticios.
- Cliente HTTP nombrado sin redirecciones automáticas, con máximo2 conexiones al servidor y sin loggers, reutilizando el patrón del proyecto; el hosting no registra spans HTTP salientes. No se loguean URI/cuerpos de routing, claves, coordenadas o errores externos. Si se cambia la observabilidad, mantener esa exclusión/redacción: las URLs del proveedor contienen datos sensibles.
- Presentación con enlaces de atribución **Powered by Geoapify** y **© OpenStreetMap contributors**. No se muestran segundos como precisión prometida de llegada.

## 4. Migración aditiva y transición futura

**`20261101213104_AddRoadEstimationHistory`**, con Designer/model snapshot:

- `PerfilesVialesVehiculo`: clave compuesta operador/recurso, FK al vehículo del mismo operador, versión concurrente y validación de estados; no backfill de compatibilidad.
- `EstimacionesRuta`: FK compuesta a hoja del operador, PK operador/ruta/número, comando único por operador, entrada/resultado JSON. API solo SELECT/INSERT; trigger impide UPDATE/DELETE incluso accidental desde owner.
- `UsoRoutingDiario` y función `nexoruta_app.reserve_routing_request`: tabla privada, RLS forzado, contador global interno y por operador; acceso API solo mediante función que verifica contexto de operador. Sin permisos worker/PUBLIC. El contador global no es un vehículo ni se presenta como tenant.
- RLS forzado sobre perfiles e historia; lecturas por operador, inserción ligada al actor del contexto. Guard de identidad/versión de perfil. Down rechaza eliminar datos B4 existentes, incluidos contadores: necesita un procedimiento deliberado de preservación.

Generada/aplicada **solo en bases efímeras Testcontainers PostgreSQL18**, con consultas de API además bajo rol SQL restringido. [SQL offline generado](evidencias/b4-integracion/migracion-b4.sql), **no ejecutado sobre operación**. Modelo EF sin diferencias pendientes. No se ejecutó `database-migrate`, migración operativa, despliegue ni conciliación real.

### Dependencia Stage B2 que continúa vigente

Un binario de este checkout con B3/B4 **no sirve para administrar una base detenida en Stage B2**. Sigue siendo necesario un artefacto B2 compatible con Stage y con procedencia acreditada. No se identificó/acreditó aquí dicho artefacto, ni se reconstruyó una versión supuesta eliminando cambios. Un backup de fuentes y un build Debug actual no constituyen esa evidencia.

Responsable operativo/DBA debe mantener el procedimiento07–09: escritores anteriores detenidos/verificados, job/pipeline externo deshabilitado y profile `rls-admin`/`rls-migrator` no activado. `DatabaseInitialization__ApplyMigrations=false`/`SeedData=false` controlan el arranque web; **no detienen el comando `database-migrate`**, que aplica todas las pendientes sin destino y no puede usarse para saltar la pausa entre etapas.

Secuencia deliberada futura: Stage → conciliación con artefacto B2 acreditado → Enforce B2 → esquema B3 → esquema B4. Verificar `__EFMigrationsHistory` antes/después de cada etapa y privilegios reales del migrador. El SQL B4 se genera acotado de B3 a B4; no habilita ese procedimiento ni acredita hechos físicos. Configurar perfiles reales y autorizar un piloto/clave nueva es trabajo operativo pendiente.

## 5. Pruebas observadas y revisión visual

Evidencia en [evidencias/b4-integracion/](evidencias/b4-integracion/). Encontrar tests no se cuenta como ejecutarlos.

| Capa | Resultado observado |
|---|---|
| RED previo | Caso HTTP persistente falló404 por endpoint de perfiles ausente antes de integrar. Se conserva log `cu06-b4i-red.log` |
| Núcleo/adaptador | **45 aprobadas**:33 del núcleo y12 casos del adaptador, incluidos flag deshabilitado con clave nueva, no reutilización de clave de geocodificación, JSON/numéricos incompletos, estático/atribución/caducidad, cuota, timeout1s, cancelación y cero reintentos |
| Integración B4 |7 casos iniciales en lote compartido;4 reejecutados después de ampliar sus aserciones: dueño/rol SQL restringido, perfil pendiente y confirmación expresa, persistencia/manuales/medianoche, idempotencia, retención de éxitos al registrar429 posterior, historia inmutable, respuesta obsoleta por cambio concurrente de perfil, presupuesto agotado, operador ajeno/RLS y comercio403, contrato público |
| Recheck de transporte final |2 casos dueño/rol restringido aprobados después de deshabilitar redirecciones y quitar el timeout fijo duplicado del HttpClient; la cancelación temporizada pertenece al adaptador |
| Concurrencia de presupuesto |1 caso adicional aprobado: dos conexiones simultáneas con cupo global1 adquieren como máximo una reserva; no se puede reservar para otro tenant |
| Regresión compartida | **20 aprobadas**: B4, B3, capacidad vigente al despacho y ciclo B2 de cierre/retorno/recepción/liberación/reutilización. Sin reapertura de aceptación B2 ni repetición de suites ajenas |
| Frontend | **8 aprobadas** en lote focalizado, incluido Chromium real y regresiones de formularios B1/B3; **55 contratos OpenAPI aprobados** contra snapshot actualizado copiado por build |
| Build/modelo | API/Infrastructure/Application y Backoffice/ApiClient compilan al ejecutar los lotes;0 errores. `has-pending-model-changes --no-build`: sin diferencias. NU1510/CS8629 anteriores no se corrigen en este bloque |
| Arquitectura | **Preexistente, no resuelto:** `ShipmentEndpoints_DeclareApiOwnedResponses`, esperado2/actual7; suite2 aprobadas/1 fallida, mismo baseline |

Los lotes se identifican por comando en sus logs. No se suman ejecuciones repetidas como escenarios nuevos ni se afirma un único E2E de navegador conectado a PostgreSQL. Las respuestas HTTP del proveedor son controladas; **no se validó precisión, cobertura práctica, tráfico ni tiempos viales reales en Uruguay**.

### Navegador real

`frontend/tests/browser/cu06-b4.cjs`, Chromium151.0.7922.34; Razor en Kestrel loopback, API en memoria, tráfico externo bloqueado. Escritorio1440, móvil390 y **320 CSSpx**:

- Perfil exige confirmación expresa, conserva motivo/selección/versión ante409 y no reintenta con token nuevo.
- Manual/calculada separadas con fecha completa, histórico invalidado, caducidad desconocida y regreso distinto de disponibilidad.
- Acciones explícitas, teclado/foco en selector y botón, doble click produce un solo POST, `disabled` y `aria-busy=true`, conflicto conserva comando/versión; éxito anuncia versión nueva mediante `role="status"`.
- Se corrigió el formulario que quedaba cerrado tras error y se acortó la opción del select que se recortaba en móvil. Sin desborde de página/sección. Capturas finales realmente inspeccionadas: [perfil320](evidencias/b4-integracion/perfil-conflicto-320.png), [estimaciones320](evidencias/b4-integracion/estimaciones-320.png), [escritorio](evidencias/b4-integracion/estimaciones-1440.png), [conflicto320](evidencias/b4-integracion/estimacion-conflicto-320.png), [resultado](evidencias/b4-integracion/resultado.json).

Es revisión visual propia de fixtures, no revisión nativa ni aceptación de un vehículo/ubicación/retorno reales.

## 6. Archivos y preservación

Inventario exacto de **37 archivos de código/contrato/pruebas/configuración** del incremento, incluidos generados: [archivos-incremento.json](evidencias/b4-integracion/archivos-incremento.json). Principales superficies:

- Application: contrato/núcleo de10, DTO B4, IRutasRepository y parcial de GestionarRutasUseCase.
- Infrastructure: GeoapifyRouting/opciones/consumo, parcial del mismo EfRutasRepository, registros/configuraciones de perfil e historia, DI, DbContext/model snapshot y nueva migración. No repositorio paralelo.
- API: contratos/controller propios de B4 y configuración segura. ApiClient: contratos y métodos nuevos; OpenAPI actualizado.
- Backoffice: parciales de ConfiguracionRepartoModel y RutasModel, perfiles/estimaciones SSR y ajuste CSS localizado; FakeApi/tests/browser. No rediseño general ni skeletons SSR artificiales.
- Tests persistentes de backend HTTP/RLS/presupuesto/adaptador y de cliente/navegador.

Se preservaron los171 archivos locales inventariados al inicio: ninguno eliminado;17 superficies previas adaptadas para B4, sin reemplazarlas por HEAD. Comparación de bytes críticos B1/B2/B3 y mobile, ramas/HEAD/estado inicial/final en [preservacion.json](evidencias/b4-integracion/preservacion.json); copia inicial TEMP `NexoRuta-B4-integration-initial-te5m0n26`. Gitlinks divergentes previos, ramas y HEAD sin cambios; no commits/push/merge.

## 7. Pendientes que no se acreditan con esta entrega

- **Revisión nativa pendiente:** backend ON global, frontend OFF local, preferencias intactas. Assess no pudo seleccionar archivos no seguidos; STATUS pide `external.select_intended_untracked`, capacidad no expuesta. No se inventó selección, revisión independiente ni aprobación; no se reintentó indefinidamente.
- **Habilitación operativa pendiente:** artefacto Stage B2, conciliación/migraciones deliberadas, verificación de permisos/privilegios/despliegue, perfiles reales y autorización expresa del piloto, presupuesto y credencial dedicada. No se usaron credenciales existentes ni se hicieron peticiones reales a `/v1/routing`.
- **Precisión vial en Uruguay pendiente de piloto autorizado.** HTTP controlado comprueba integración, no la realidad de carreteras/duraciones.
- Fallo de arquitectura anterior sigue abierto. Engram sin identidad runtime registrada: trazabilidad local, sin afirmar memoria atribuida guardada.
- B5 no iniciado. **B4 integrado no equivale a CU06 completo.**

Risk: items1,2,3,4,5 (migración/persistencia, autorización/RLS/privacidad, contratos públicos, concurrencia de guardado/presupuesto y configuración). Trabajo inline por restricción de no subagentes; sin aprobación nativa fabricada.
