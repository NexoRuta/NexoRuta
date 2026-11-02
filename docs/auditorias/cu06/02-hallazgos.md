# CU-06 — hallazgos y evidencia de verificación

> **Resolución posterior B1 (01/11/2026):** H01/H03/H04/H08 y la autorización puntual de H07 recibieron implementación y regresiones persistentes. Se conserva intacta debajo la evidencia del defecto original. Ver [cambios, pruebas y límites](05-implementacion-b1.md). H02/H05/H09 no se resolvieron; H07 conserva pendiente la aceptación visual.

Corte local: **01/11/2026**, commits del [documento 01](01-estado-y-trazabilidad.md). No se modificó implementación ni se corrigieron pruebas para obtener resultados favorables.

**Prioridad recomendada:** primero capacidad vigente y precisión; después disponibilidad física entre fechas y retorno confirmado. La flota no necesita reescribirse.

## 1. Clasificación

- **Defecto confirmado:** contradicción técnica reproducida o demostrable directamente en el flujo indicado.
- **Brecha confirmada:** comportamiento comprobado que no cubre la nueva necesidad; no equivale automáticamente a incumplimiento del enunciado.
- **Riesgo inferido:** consecuencia razonable del código, sin reproducción integral del escenario.
- **Decisión pendiente / mejora:** exige política de negocio o mejora de experiencia, no se presenta como bug.
- P1: corregir antes de confiar operativamente en esa garantía. P2: coherencia/experiencia y contrato. P3: robustez extrema o mejora no bloqueante.

## 2. Hallazgos priorizados

### H01 — P1 · Capacidad reducida tras planificar no impide despachar

**Tipo:** defecto confirmado de integración de capacidad vigente; grupo A/B. No implica que falte el cálculo inicial.

**Archivo/función/líneas:**

- `backend/src/NexoRuta.Infrastructure/Reparto/EfRutasRepository.cs:77-84`, `PlanificarAsync`: suma y compara con vehículo actual.
- Mismo archivo `:99-114`, `DespacharAsync`: comprueba Activo, repartidor, estado y custodia, **no capacidad**.
- `backend/src/NexoRuta.Domain/Reparto/HojaRuta.cs:26-34`, constructor: snapshot al **planificar**, no al despachar.
- `backend/src/NexoRuta.Infrastructure/Reparto/EfRutasRepository.Reasignaciones.cs:195-215`, `ReasignarAsync`: compara contra snapshot.
- `backend/src/NexoRuta.Infrastructure/Reparto/EfConfiguracionRepartoRepository.cs:47-71`, `GuardarVehiculoAsync`: permite reducir capacidad sin revisar hojas.

**Reproducción aislada P04:** dos bultos de 1.000 y 2.000 g, ambos 10×10×10 cm; vehículo 3.000 g / 2.000 cm³; plan HTTP 200. PUT reduce a 1.500 g / 1.000 cm³, HTTP 200. Despacho de la hoja con versión vigente: **HTTP 200**.

**Actual:** el snapshot conserva 3.000/2.000, el vehículo real declara 1.500/1.000 y el despacho no lo consulta para carga. **Esperado recomendado:** conservar el snapshot histórico y rechazar el despacho si excede la capacidad vigente, sin modificar la ruta/envíos; comunicar ambas capacidades. La regla exacta sobre editar flota ocupada debe formalizarse, no invalidar historia.

**Impacto:** sobrecarga admitida; una reasignación también puede admitir más que la capacidad reducida (este último efecto se infiere del código, no se ejecutó sonda específica). `ConfirmarCarga` tampoco revalida capacidad, por lo que un cambio posterior al despacho queda igualmente sin garantía actual.

### H02 — P1 · La reserva por fecha no garantiza disponibilidad física

**Tipo:** brecha confirmada frente a C; no se redefine retroactivamente la semántica actual de reserva.

**Archivo/función/líneas:**

- `backend/src/NexoRuta.Infrastructure/Reparto/EfRutasRepository.cs:41-65`, `PlanificarAsync`: consulta solo `Fecha == datos.Fecha`.
- `backend/src/NexoRuta.Infrastructure/Reparto/HojaRutaConfiguration.cs:23-30`, `Configure`: índices únicos por operador/recurso/**fecha**, no ocupación global.
- `backend/src/NexoRuta.Infrastructure/Reparto/EfRutasRepository.cs:99-114`, `DespacharAsync`: no busca otra hoja en curso del mismo vehículo/repartidor.
- `backend/src/NexoRuta.Infrastructure/Reparto/EfOperacionesRepartoRepository.Ejecucion.cs:15-20`, `Ejecutar`: InicioJornada valida la fecha de **esa** hoja, no otra ocupación.

**Reproducción P07:** plan/despacho del día D, InicioJornada aplicado y hoja A `EnCurso`. Se crea otro envío de prueba en depósito. Para D+1, mismo repartidor y vehículo: **plan 200 y despacho 200** sin terminar A. La sonda no adelantó el reloj ni inició B; la ausencia de guardia al inicio se comprobó estáticamente.

**Actual:** dos compromisos en fechas distintas pueden coexistir aun con A en ejecución. **Esperado de C:** reservar trabajos futuros es válido, pero un segundo despacho/salida no debe otorgar ocupación física mientras falte retorno confirmado de A. No se recomienda bloquear toda planificación futura.

**Impacto:** riesgo de doble uso, especialmente después de medianoche y con cierres offline pendientes. Locks e índices evitan duplicados del mismo día; no arreglan una regla que omite el intervalo/ocupación real.

### H03 — P2 · Unidad de volumen incorrecta en HTML inicial; resumen incompleto

**Tipo:** defecto estático confirmado de conversión + mejora de feedback; A/B. Efecto visual real pendiente.

**Archivo/función/líneas:**

- `frontend/src/NexoRuta.Backoffice/Pages/Rutas/Planificar.cshtml:68`: imprime `VolumenMaximoCm3` sin dividir y etiqueta `m³` cuando hay vehículo seleccionado.
- `frontend/src/NexoRuta.Backoffice/wwwroot/js/rutas-planificacion.js:55-61`, `refreshSummary`: sí divide por `1_000_000` y reemplaza el texto al inicializar.
- `Planificar.cshtml:8-9,93-98,121` y JS `:38-41,80-85`: suman peso/cantidad; no muestran volumen total ni alertan exceso de volumen.

**Escenario:** capacidad 4.000.000 cm³ → Razor puede emitir «4000000 m³», aunque corresponde **4 m³**. JS normal lo corrige; sin JS, ante fallo o durante render inicial, persiste/parpadea información incorrecta. No se afirmó haber visto ese parpadeo.

**Esperado:** misma conversión en HTML y JS; volumen agregado visible con unidad consistente y avisos de excesos independientes. Servidor sigue siendo autoridad. **Impacto:** decisión de carga mal informada; no significa que el servidor deje pasar un exceso inicial.

### H04 — P2 · La API admite más decimales que la persistencia y devuelve otro valor

**Tipo:** defecto confirmado; A y coherencia con B.

**Archivo/función/líneas:**

- `backend/src/NexoRuta.Api/Features/Reparto/Contracts/VehiculoContract.cs:9-13`: rangos, sin escala máxima.
- `backend/src/NexoRuta.Domain/Reparto/Vehiculo.cs:27-33`, `Definir`: asignación sin redondeo ni rechazo de escala.
- `backend/src/NexoRuta.Infrastructure/Reparto/VehiculoConfiguration.cs:18-20`: dos decimales.
- `backend/src/NexoRuta.Infrastructure/Reparto/EfConfiguracionRepartoRepository.cs:69-71`: respuesta desde entidad en memoria, no relectura persistida.
- `frontend/src/NexoRuta.Backoffice/Pages/ConfiguracionReparto.cshtml:38-39,51-52`: step 0,01 sin máximos explícitos; `VehiculoResponse.cs:3-10` no agrega validaciones de rango al PageModel.

**Reproducción P06:** PUT con peso y volumen `1.005`: **200 y cuerpo 1.005**; GET posterior: **1.01** para ambos. El formulario nativo sugiere centésimas, pero no protege la API de clientes directos.

**Esperado recomendado:** rechazar más de dos decimales en las fronteras, o acordar una normalización explícita y devolver el valor normalizado; misma regla para bultos. **Impacto:** diferencias entre valores confirmados, persistidos y usados para límites exactos. API usa mínimo 0,01; dominio solo >0: debe explicitarse el contrato único. Los máximos del vehículo caben en las columnas actuales; no se detectó overflow en esos máximos por sí solos.

### H05 — P1 para la nueva necesidad · FinJornada no confirma retorno físico

**Tipo:** decisión vigente + brecha confirmada frente a C, **no bug automático de D18**.

**Archivo/función/líneas:**

- `backend/docs/cu/cierre-jornada.md`: D18, DEC-01 y DEC-07.
- `backend/src/NexoRuta.Domain/Reparto/HojaRuta.cs:77-80`, `RegistrarFin`: finaliza y desactiva reserva.
- `backend/src/NexoRuta.Infrastructure/Reparto/EfOperacionesRepartoRepository.Ejecucion.cs:69-85`, `Ejecutar(FinJornada)`: permite pendientes y conserva su custodia.
- `backend/src/NexoRuta.Infrastructure/Reparto/EfOperacionesRepartoRepository.cs:72-86`, `AplicarAsync`: incidencias + cierre en la misma transacción.

**Escenario:** repartidor termina jornada con bulto no entregado ni rendido. **Actual:** hoja finalizada y reserva libre, bulto sigue en custodia del repartidor y la incidencia queda registrada. Pruebas ejecutadas confirman conservación e idempotencia, no retorno.

**Esperado para C:** cierre administrativo y retorno/disponibilidad deben poder diferir. Conservar D18 para la jornada y requerir confirmación explícita de retorno y aptitud antes del uso físico siguiente. La ETA no reemplaza esa confirmación. **Impacto:** el estado finalizado hoy no prueba regreso, descarga ni capacidad residual libre. Cambiar el momento de liberación requiere una decisión explícita documentada y migración deliberada; no reinterpretar cierres antiguos como retornos.

### H06 — P2 · Edición administrativa de vehículo no considera su uso actual

**Tipo:** comportamiento estático confirmado; consecuencias posteriores parcialmente inferidas y decisión pendiente.

**Ubicación:** `EfConfiguracionRepartoRepository.cs:47-71`, `GuardarVehiculoAsync`; `EfRutasRepository.cs:106-108`, `DespacharAsync`; `EfOperacionesRepartoRepository.Ejecucion.cs:15-50`, `Ejecutar`; rutas completas bajo `backend/src/NexoRuta.Infrastructure/Reparto/`.

**Escenario:** editar matrícula/capacidad o desactivar después de reservar, despachar o iniciar.

| Momento | Comportamiento actual |
|---|---|
| Planificada | Editar/desactivar permitido; snapshot no cambia. Si inactivo, despacho 409. P05 lo reprodujo y reactivar permite despacho 200. |
| Despachada | La edición sigue permitida. Inicio de jornada no comprueba Activo del vehículo; efecto inferido de la implementación. |
| EnCurso | No hay consulta de vehículo en carga/fin. Desactivar no libera la reserva ni reescribe la historia. |
| Finalizada | Datos de matrícula/capacidad de hoja siguen siendo los del snapshot; no hay historial completo de cada edición de la ficha del vehículo. |

**Recomendación:** desactivar impide nuevos compromisos y nueva ocupación; no debe impedir rendir/cerrar/retornar una ruta existente. Reducir capacidad obliga a revalidar antes de salir; las modificaciones que afectan un vehículo en uso necesitan aviso/limitación explícita. No cambiar silenciosamente custodia ni liberar por desactivación.

### H07 — P2/P3 · Acceso de pantalla y evidencia UX incompleta

**Tipo:** desalineación estática de defensa en profundidad + mejora/pendiente de verificación, no bypass de API demostrado.

**Ubicación:** `frontend/src/NexoRuta.Backoffice/Program.cs:31-54` (no convención específica para `/ConfiguracionReparto`); `Core/Navigation/BackofficeNavigation.cs:55-58` (menú por `configuracion.gestionar`); `backend/src/NexoRuta.Api/Features/Reparto/Controllers/ConfiguracionRepartoController.cs:9` (API protegida).

Un operador sin permiso de configuración puede llegar directamente al PageModel bajo la política general, aunque el menú lo oculte y el API rechace la lectura/escritura. Recomendar alinear política de página; **no se encontró ni afirmó escritura sin autorización**. No se abrió una auditoría general de seguridad.

La pantalla sí tiene labels, unidades y alertas/status; conserva el vehículo enviado ante error (`ConfiguracionRepartoModel.cs:47-81`) y usa formularios SSR, por lo que no requiere skeleton artificial. No hay resumen por campo ni máximos HTML explícitos en capacidades; no se ensayaron todos los conflictos del formulario de vehículo ni WCAG real. El nombre del menú oculta semánticamente la flota dentro de «Configuración de reparto»: mejorar rótulo/ayuda es recomendación, no ausencia funcional demostrada.

### H08 — P3 · Overflow en sumatoria extrema de volumen

**Tipo:** excepción técnica reproducida con datos sintéticos fuera del alta actual; robustez, no bloqueo principal de CU-06.

**Ubicación:** `backend/src/NexoRuta.Infrastructure/Reparto/EfRutasRepository.cs:81-83`, `PlanificarAsync`; misma fórmula en `EfRutasRepository.Reasignaciones.cs:210-212`.

P08 añadió **80 bultos adicionales** al envío de prueba, cada uno de 1 g y dimensiones `999999999` cm por eje, dentro del máximo numérico declarado por el contrato de bulto; fixture propietaria, no alta pública multibulto. `Sum(decimal)` desbordó y TestServer propagó `OverflowException`, en vez de un conflicto de capacidad. La sonda terminó **exit 1**. No se obtuvo respuesta HTTP 500: no se inventa ese resultado. No se ejecutó un assert posterior de integridad en ese escenario; rollback se infiere de la transacción.

El producto de un bulto máximo (~10²⁷ cm³) cabe en decimal .NET (~7,9×10²⁸); muchas sumas no. Con múltiples envíos también es un riesgo aritmético, pero no se reprodujo por alta pública y su plausibilidad física es ínfima. Recomendación mínima: acumulación limitada que corte en exceso, validación de límites de negocio y error controlado; no empaquetador ni nueva dependencia. El volumen de cada bulto muy pequeño conserva hasta seis decimales al multiplicar medidas con dos decimales: no redondear cada bulto antes de sumar.

### H09 — C · Base, estimaciones y aviso no están construidos

**Tipo:** funcionalidad adicional ausente en las superficies inspeccionadas; no incumplimiento literal de A.

**Ubicación:**

- `backend/src/NexoRuta.Domain/Administracion/Operador.cs:3-8`, `VersionIdentidadVisualOperador.cs:25-37`: identidad/contacto, no base geográfica.
- `backend/src/NexoRuta.Domain/Reparto/ConfiguracionReparto.cs:3-11`: zona horaria/política, no dirección/base ni tiempos.
- `frontend/src/NexoRuta.Backoffice/Features/Reparto/Pages/RutasModel.cs:89-97,294-299`: convierte horas manuales a UTC, no calcula tiempos viales.
- `backend/src/NexoRuta.Domain/Reparto/HojaRuta.cs:18-21,70-80`: inicio/salida/fin reales, sin salida planificada/regreso previsto/retorno confirmado.
- `backend/src/NexoRuta.Infrastructure/Envios/Geocodificacion/GeocodificadorGeoapify.cs:20-34`: búsqueda geográfica, no enrutamiento.
- `backend/src/NexoRuta.Infrastructure/Reparto/EfOperacionesRepartoRepository.Ejecucion.cs:25-29`: registra posición; no recalcula llegadas.
- `mobile/src/NexoRuta.Mobile/Mapas/ProveedorMapbox.cs:14-20,31-58`: mapas/recursos offline, no proveedor vial del backend.

No se encontró contrato de tiempos por carretera ni cálculo de retorno al último destino/base. Reutilizar proveedores actuales de coordenadas/mapas no demuestra que exista autorización, contrato o implementación de routing. Diseño mínimo y decisiones en el documento 04.

## 3. Carga: fuente de verdad y garantías existentes

Fuente operativa: filas de `Bultos` pertenecientes al operador y envío; no el texto del formulario ni el resumen de la pantalla. `CrearEnvioUseCase.cs:73-82` construye un único bulto; `NexoRutaDbContext.cs:393-413` persiste cuatro medidas `numeric(12,2)` y pertenencia compuesta. Rutas expone Id/código/peso/volumen/custodia/versión (`EfRutasRepository.cs:201-210`). La cantidad se deriva de la colección, no de una capacidad declarada por envío.

| Lugar | Operación y observación |
|---|---|
| `EfRutasRepository.PlanificarAsync:31,66-83` | Rechaza envíos repetidos; trae todos los bultos una vez por consulta; suma pesos y productos de dimensiones. Acepta igualdad, rechaza `>` en cualquiera de los ejes de capacidad agregada. |
| `EfRutasRepository.ReasignarAsync:195-215` | Rechaza duplicación en destino; agrega nuevo envío al conjunto de paradas **activas**, no incluye suspendidas en carga de destino; compara snapshot. |
| `EfRutasRepository.Datos:208-209` | Calcula volumen por bulto para la hoja; puede incluir datos históricos de paradas suspendidas. Eso no es una sumatoria operativa de carga. |
| `Planificar.cshtml:8-9,93-98` / JS `refreshSummary` | Peso y cantidad de todos los bultos seleccionados, no solo el primero; JS usa Number, orientativo y no autoridad de validación. |
| `frontend/src/NexoRuta.Backoffice/Features/Envios/Pages/IndexModel.cs:143-146` | Resumen de peso de envíos en kg, no validador de vehículo. |
| `backend/src/NexoRuta.Domain/Tarifas/CalculadoraTarifas.cs:84-100` | También suma peso/volumen para **tarifa**, no disponibilidad/carga del vehículo. Identificado, no auditado como CU-09 ni modificado. |

Fórmulas comprobadas: `Σ pesoGramos`; `Σ (largoCm × anchoCm × altoCm)`; kg = g / **1.000**; m³ = cm³ / **1.000.000**. El agregado no garantiza que un objeto largo pase por una puerta ni que los sólidos puedan acomodarse. No hay evidencia de validación dimensional del interior del vehículo; no se considera exigida por el texto original.

La planificación nueva no tiene paradas suspendidas; en reasignaciones sí se filtran las activas. La ejecución puede conservar carga física de paradas suspendidas por discrepancia/rendición: no debe confundirse esa custodia con la carga asignable a otra ruta. No se probaron todas las combinaciones multibulto, porque el alta pública sigue limitada a uno.

## 4. Verificaciones ejecutadas

### 4.1 Seguridad del entorno

SDK observado: `10.0.401`; Docker Server: `28.0.4`. Se leyeron `PostgresFixture.cs` e `IntegrationApiFactory.cs` antes de ejecutar integración. La fixture crea contenedor propio `postgis/postgis:18-3.6-alpine`, base/usuario aleatorios y bases por escenario; verifica identidad y versión antes de migrar. TestServer sustituye DbContext por ese destino; no hay fallback al desarrollo. El contenedor se elimina mediante Dispose, no se ejecuta limpieza SQL en una base externa.

No se ejecutó `compose up`, otra API/base operativa, migraciones sobre desarrollo, reset, cambio de rama, update de submódulos, commit, push o despliegue. No se leyeron secretos de `.env` ni se usaron credenciales operativas para las sondas.

### 4.2 Automatización existente: **261 aprobadas**, 0 fallos, 0 omitidas

Ejecutadas desde raíz, con `--nologo --logger 'console;verbosity=minimal'`:

```powershell
dotnet test backend/tests/NexoRuta.IntegrationTests/NexoRuta.IntegrationTests.csproj --no-restore --filter 'FullyQualifiedName~ConfiguracionRepartoHttpTests|FullyQualifiedName~RutasHttpTests|FullyQualifiedName~RepartoRestrictedHttpTests' --nologo --logger 'console;verbosity=minimal'
# 19/19, exit 0; duración de pruebas 1 m 5 s.

dotnet test backend/tests/NexoRuta.IntegrationTests/NexoRuta.IntegrationTests.csproj --no-build --no-restore --filter 'FullyQualifiedName~CierreConIncidenciaEsIdempotente|FullyQualifiedName~RendicionDeclaradaAntesDelCierre|FullyQualifiedName~CierreDuranteLaCarga|FullyQualifiedName~FinJornadaLeavesAnUnstartedAssignment|FullyQualifiedName~ConfirmarCargaConDiscrepanciaPermitida|FullyQualifiedName~ReintentoDevuelveLaMismaConfirmacion|FullyQualifiedName~CargaNoAdmiteBultosAjenos' --nologo --logger 'console;verbosity=minimal'
# 8/8, exit 0; 52 s.

dotnet test frontend/tests/NexoRuta.ApiClient.Tests/NexoRuta.ApiClient.Tests.csproj --no-restore --filter 'FullyQualifiedName~RutasPagesTests|FullyQualifiedName~BackofficeSessionAndPagesTests|FullyQualifiedName~SpecializedApiClientTests|FullyQualifiedName~OpenApiContractTests' --nologo --logger 'console;verbosity=minimal'
# 192/192, exit 0; 36 s.

dotnet test mobile/tests/NexoRuta.Mobile.Core.Tests/NexoRuta.Mobile.Core.Tests.csproj --no-restore --filter 'FullyQualifiedName~JornadaLocalTests|FullyQualifiedName~IncidenciasCierreTests' --nologo --logger 'console;verbosity=minimal'
# 28/28, exit 0; 513 ms.

dotnet test mobile/tests/NexoRuta.Mobile.Application.Tests/NexoRuta.Mobile.Application.Tests.csproj --no-restore --filter 'FullyQualifiedName~EstadoJornadaIndicadorTests|FullyQualifiedName~SincronizadorJornada' --nologo --logger 'console;verbosity=minimal'
# 14/14, exit 0; 31 s.
```

`RutasPagesTests.cs` pertenece a la clase parcial `BackofficeSessionAndPagesTests`, no a una clase llamada RutasPagesTests. El filtro ejecutó toda esa clase y pruebas auxiliares de cliente/contrato: parte de las 192 es soporte incidental ajeno a CU-06, no una auditoría general ni 192 garantías específicas de flota.

Qué prueban los casos pertinentes:

- Normalización, matrícula duplicada, edición y versión obsoleta; comercio no configura flota.
- Ruta vacía reserva, no se despacha ni descarga; cancelación explícita libera sin borrar historial; carreras cancelar/planificar no duplican reserva.
- Dos planificaciones concurrentes asignan una sola vez; rechazo por capacidad no asigna envíos.
- Preparación/despacho/ejecución bajo rol PostgreSQL restringido, no solo usuario propietario.
- Cierre idempotente con incidencias, conservación de custodia, recepción posterior y cierre durante carga.
- Persistencia offline, orden causal, reintento de mismos bytes y acuse de cierre separado del hecho local.

Lo que **no** prueban por sí solos: CRUD visual con navegador, matriz completa de tenant/Id ajeno para vehículos, todos los límites de escala, capacidad vigente tras edición, bloqueo físico entre días, proveedor vial, retorno real o uso del hardware MAUI. Los defectos sobreviven con la suite verde.

### 4.3 Sondas temporales propias: resultados observados, no suite verde

Se usó un proyecto consola **fuera del checkout**, referenciando el proyecto de integración existente, `PostgresFixture` y su helper `RepartoHttpData.Preparar` por reflexión. Reutilizó API en memoria y creó una base efímera independiente por escenario. No se modificaron tests ni código de negocio. Se corrigió solo el content-root del runner temporal para que WebApplicationFactory encontrara la API local.

Datos comunes P01–P07: fixture crea envío recibido con bulto 1.000 g, 10×10×10 cm; se añade otro bulto por seed aislado de 2.000 g y mismas medidas. PUT fija vehículo 3.000 g y 2.000 cm³, salvo variación indicada. Por tanto las pruebas multibulto demuestran el consumidor de carga, **no** un alta multibulto pública.

| Sonda | Variación / acción pública | Resultado observado |
|---|---|---|
| P01 exact | Plan con ambos límites exactos | 200; hoja devuelve ambos bultos |
| P02 weight | Capacidad 2.999,99 g; volumen 2.000 cm³ | Plan 409; sin hoja persistida |
| P03 volume | Capacidad 3.000 g; volumen 1.999,99 cm³ | Plan 409; sin hoja persistida |
| P04 reduce | Plan válido; PUT capacidad 1.500 g / 1.000 cm³; despachar | PUT 200, despacho 200: H01 |
| P05 inactive | Plan válido; PUT Activo=false; despachar; reactivar; despachar | 409 inactivo, 200 tras reactivar |
| P06 precision | PUT peso/volumen 1.005; GET posterior | PUT devuelve 1.005; GET 1.01: H04 |
| P07 crossdate | Hoja D iniciada por API, otro envío en depósito; plan/despacho D+1 mismo recurso | Ambas peticiones 200 mientras D seguía EnCurso: H02 |
| P08 overflow | 80 bultos adicionales de 1 g y 999999999³ cm³; plan | `OverflowException` en Sum, TestServer propaga; runner exit 1: H08 |
| P09 tenant | Seed de otro operador y vehículo con igual matrícula; GET/PUT desde operador original | GET no lo lista; PUT a Id ajeno 404; fila ajena sin cambios. La igualdad de matrícula entre operadores persistió. |
| P10 limits | PUT: 0, -1, 0.001 g; peso 10000000000000000; volumen 10000000000000000000000 | Cinco 400; mínimo 0.01/0.01 y máximos 9999999999999999/9999999999999999999999 dan 200 y GET exacto. |
| P11 concurrent | Dos PUT a mismo vehículo/versión con capacidades distintas | Uno 200 y otro 409. |
| P12 reuse | Plan/despacho/inicio y fin aplicado antes de salida; nueva ruta vacía mismo día/recursos | Fin deja Finalizada/Reserva=false; nueva reserva 200. No prueba retorno físico. |

Salida resumida del runner:

```text
CU06_PROBE exact plan HTTP=200
CU06_PROBE weight plan HTTP=409
CU06_PROBE volume plan HTTP=409
CU06_PROBE reduce plan HTTP=200
CU06_PROBE reduce dispatch HTTP=200
CU06_PROBE inactive plan HTTP=200
CU06_PROBE inactive dispatch HTTP=409
CU06_PROBE reactivation dispatch HTTP=200
CU06_PROBE precision PUT=1.005 GET=1.01 g/cm3
CU06_PROBE crossdate plan HTTP=200
CU06_PROBE crossdate dispatch HTTP=200
CU06_PROBE crossdate first=EnCurso next-date plan=200 dispatch=200 same vehicle/repartidor
System.OverflowException ... Enumerable.Sum ... EfRutasRepository.PlanificarAsync ... line 81
CU06_PROBE tenant GET excludes foreign, foreign PUT=404 unchanged, same plate different operator persisted
CU06_PROBE limits 5 invalid=400, min/max=200 and GET exact
CU06_PROBE concurrent vehicle edits=200+409
CU06_PROBE reuse plan HTTP=200
CU06_PROBE reuse dispatch HTTP=200
CU06_PROBE reuse Fin applied Reserva=false, same-day new reservation=200
```

Incidentes del runner, no defectos de aplicación: primer intento sin elevación no accedió a Docker; segundo no localizó la raíz de solución desde TEMP; tercer intento ejecutó P01–P07 y terminó por P08. Una ejecución adicional con argumentos `tenant limits concurrent reuse` completó P09–P12 con **exit 0**. No se falsea éxito global del primer lote. La liberación del contenedor estaba en `finally` y se comprobó terminación de procesos; la limpieza de archivos propios se registra al cierre de la auditoría.

### 4.4 Compilación

Las ejecuciones sin `--no-build` compilaron backend Domain/Application/Infrastructure/API/Worker e IntegrationTests; frontend Hosting/ApiClient/Admin/Commerce/Tracking/Backoffice y sus tests; mobile Core/Api/Storage/Application y tests seleccionados. Resultado de esos builds implícitos: exitoso. **No** se ejecutó build completo de las tres soluciones ni MAUI Android/iOS.

Warnings observados: NU1510 en Infrastructure y Hosting (`System.Security.Cryptography.Xml` redundante) y CS8629 en `frontend/.../ZonasCobertura/Pages/DetalleModel.cs:75`. No se atribuyen a CU-06 ni se tocaron.

### 4.5 HTTP de instancia existente

```text
curl.exe -I --max-time 5 http://localhost:5101/configuracion-reparto
HTTP/1.1 302 Found
Location: http://localhost:5101/ingresar?ReturnUrl=%2Fconfiguracion-reparto

curl.exe -I --max-time 5 http://localhost:5046/configuracion-reparto
curl exit 7: no se pudo conectar
```

Esto confirma un Kestrel local y protección de acceso anónimo en 5101, **no** qué commit sirve ni CRUD autenticado ni persistencia de esa instancia. No se iniciaron servicios para suplir el puerto 5046 ni se modificó la base existente.

### 4.6 Navegador y revisión visual: pendiente

Se invocó Computer Use `cua.getState()`. Resultado: inventario sin apps/navegadores; errores **“Computer Use native pipe is unavailable”** y **“The browser access host is unavailable”**. No fue posible observar la pantalla, probar teclado/foco, 320 CSS px, zoom ni contraste. No se usaron capturas históricas como evidencia actual. La revisión estática de Razor/JS y el HTTP anterior no se presentan como revisión visual.

### 4.7 Gentle-AI y memoria

`gentle-ai review mode status` inicialmente falló por acceso; repetido con aprobación devolvió `on (decided by global)`, global on y clone-local unset. No se alteró configuración ni se abrió ciclo de implementación/revisión. Sin subagentes por instrucción explícita.

Engram resolvió `nexoruta` en el cwd correcto, pero `mem_review` y el guardado de descubrimientos fueron rechazados por el hook: **“Codex host session is not registered; start a new Codex session to register it.”** No se inventó identidad ni se registró manualmente una sesión. Los documentos locales son la entrega durable; memoria no confirmada.

### 4.8 Preservación y cierre de archivos

Readback final: las ramas y HEAD de los cuatro repositorios coinciden con el corte inicial; backend, frontend y mobile siguen limpios internamente. La raíz conserva los tres `M` originales y agrega únicamente `?? docs/auditorias/cu06/` con los cuatro Markdown solicitados. `git diff --check` pasó en los cuatro repositorios. Se comprobaron UTF-8, cercas de código balanceadas, enlaces Markdown locales existentes y 36 referencias completas a archivo/línea; se corrigieron referencias antes de entregar.

Todos los runners terminaron y no se encontró un proceso de sonda activo. Se intentó retirar únicamente el directorio propio de sondas en TEMP, con verificación de ruta y proceso; la ejecución fue **rechazada por política antes de iniciarse**. No se buscó un método alternativo para eludirla. Quedan el runner y sus logs en `%LOCALAPPDATA%/Temp/NexoRuta-CU06-audit-47474606f2ab4abfb11d1fdf57cc17e4/`; no son archivos del checkout ni cambios funcionales. Contienen `Probe.csproj`, `Program.cs`, `run.log` y `additional.log`, además de resultados de compilación; permiten reconstruir las sondas descritas en §4.3. No se limpió el checkout.

El inventario Docker con etiqueta Testcontainers solo mostró un contenedor detenido desde antes de esta auditoría; no se eliminó ni modificó. No quedaron contenedores de las sondas actuales en ese inventario. No se tocaron bases ni volúmenes operativos.

## 5. Pendientes concretos de prueba

1. Revisión real de `/configuracion-reparto` con alta/edición/desactivación/reactivación sobre una instalación de pruebas aislada identificada, sin usar datos operativos para escrituras de auditoría.
2. Convertir P09/P11 en regresiones permanentes y ampliar aislamiento bajo cada rol pertinente. Ya se probó GET/PUT con Id ajeno, igualdad de matrícula entre operadores y edición concurrente; no se certifica una matriz exhaustiva por ese escenario.
3. Convertir P06/P10 en regresiones permanentes. Cero/negativos/mínimo/máximos/sobre máximo fueron ejecutados; queda formalizar escala y verificar coherencia también en formulario y bultos, no solo capacidades API.
4. Reasignación con reducción de capacidad, suspendidas y bultos múltiples; revalidación al despacho y confirmación de carga; asegurar que el rechazo no altera envíos, hoja ni reserva.
5. Regresión del volumen HTML sin JS y total visual; prueba de navegación/errores con todos los valores conservados. No se agregaron tests de implementación todavía.
6. Antes de construir C: reglas de despacho futuro, ocupación entre fechas, cierre/retorno offline, liberación con carga residual y quién puede confirmar disponibilidad. No hay prueba de ETA/proveedor porque esa integración no existe.
