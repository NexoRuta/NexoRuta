# CU06 · acceso a vehículos e integración local

Fecha: 2026-11-01. **Acceso a Vehículos corregido en la instancia local:** [http://localhost:5101/vehiculos](http://localhost:5101/vehiculos), menú **Operador y equipo → Vehículos**, junto a Repartidores.

**La integración operativa de las tres consultas continúa bloqueada.** Se comprobó un backend ejecutado sin esos endpoints y una base sin las migraciones B2–B4. No se sustituyó ese binario por uno incompatible ni se migró la base. La combinación actual del checkout funciona en aislamiento, incluida la navegación y escrituras mediante Backoffice real. No se declara resuelto un404 operativo que todavía existe ni cerrado CU06.

## 1. Gestión encontrada y corrección implementada

Antes del cambio, la gestión estaba efectivamente en `/configuracion-reparto`: `ConfiguracionRepartoModel.OnPostVehiculoAsync`, listado y formularios en `Pages/ConfiguracionReparto.cshtml`. Se leyó y rastreó antes de moverla; no se dedujo por su nombre ni se confundió con compatibilidad vial.

| Recorrido comprobado | Ubicación vigente |
|---|---|
| Menú único | `frontend/src/NexoRuta.Backoffice/Core/Navigation/BackofficeNavigation.cs`, grupo Operador y equipo, inmediatamente después de Repartidores |
| Página | `frontend/src/NexoRuta.Backoffice/Pages/Vehiculos.cshtml`, `@page "/vehiculos"` |
| Handler y validación | `Features/Reparto/Pages/VehiculosModel.cs`: `OnGetAsync`, `OnGetReintentarAsync`, `OnPostVehiculoAsync`, `ValidarCapacidad` |
| Cliente HTTP existente | `frontend/src/NexoRuta.ApiClient/Features/Reparto/Clients/ConfiguracionRepartoApiClient.cs`: `VehiculosAsync` y `GuardarVehiculoAsync` |
| API existente | `backend/src/NexoRuta.Api/Features/Reparto/Controllers/ConfiguracionRepartoController.cs`: GET y PUT `/api/reparto/vehiculos` |
| Aplicación / persistencia existentes | `ConfigurarRepartoUseCase` → `EfConfiguracionRepartoRepository` → `Vehiculo`, tabla `Vehiculos`, versión y ámbito por operador |
| Permiso | `configuracion.gestionar`, mismo en catálogo de menú, convención Razor `/Vehiculos` y API. La convención general exige contexto Operador. No se cambió a `usuarios.gestionar` solo por estar junto a Repartidores |

Se **trasladaron**, no duplicaron, la presentación y handler del CRUD. Permanecen alta, listado/consulta, edición inline, capacidades en gramos/cm³, estado Activo y tokens de versión. Sin nuevo modelo, repositorio, endpoint ni borrado físico. Validación B1 invariante con dos decimales efectivos, min/max/step y valores conservados ante error/conflicto. No se usa automáticamente una versión nueva. Timeout de guardado deja explícito resultado desconocido y conserva datos/versión.

Compatibilidad vial sigue siendo una sección adicional en `/configuracion-reparto#perfiles-heading`, enlazada desde Vehículos; no sustituye el listado ni los formularios. Configuración de reparto conserva política, base y compatibilidad, con enlace de vuelta al CRUD. Conserva también la comprobación de disponibilidad API anterior a guardar política: un404 de configuración no debe habilitar escrituras cuando sus endpoints de lectura faltan.

La página Vehículos **no depende** de consultar política, base, ocupación ni perfil para mostrar/gestionar su catálogo. Los errores de esos módulos no ocultan el acceso al CRUD disponible. Formularios con etiquetas/contexto accesibles, errores por campo con `aria-describedby`/`aria-invalid`, antiforgery y `data-single-submit`. Sin framework nuevo, skeleton SSR artificial ni rediseño general.

## 2. Diagnóstico conjunto de las tres consultas

[Probes autenticados de la instancia](evidencias/vehiculos-integracion/final-local.json), [contratos publicados](evidencias/vehiculos-integracion/rutas-publicadas.json) y [procesos/binarios](evidencias/vehiculos-integracion/runtime-final.json). No se incluyen credenciales, tokens ni cookies.

El Backoffice5101 usa **`Api__BaseAddress=http://api:8080/`** dentro de Compose. El mismo contenedor API se publica al host en **`http://localhost:5000/`**. Los ApiClient agregan el prefijo `api/` una sola vez. No se encontró una dirección base o prefijo incorrectos.

| Método | Ruta relativa a la API | Instancia operativa antes / después | Checkout + esquema efímero |
|---|---|---|---|
| GET | `/api/reparto/flota` | **404 / 404** | **200**, desde SSR Backoffice real |
| GET | `/api/rutas/{id}/estimaciones` | **404 / 404**, con ruta propia existente | **200**, desde SSR Backoffice real |
| GET | `/api/reparto/perfiles-viales` | **404 / 404** | **200**, desde SSR Backoffice real |
| GET | `/api/reparto/vehiculos` | **200 / 200** autenticado | **200**, listado real |
| PUT | `/api/reparto/vehiculos` | **No ejecutado** sobre operación | Alta/edición/habilitación200, precisión inválida400 y versión atrasada409 |

El ID concreto de la consulta de histórico está en el JSON citado. Los probes sin token también devolvían404 en los tres endpoints faltantes, frente a401 en vehículos publicado. Con identidad válida, vehículos y consulta de rutas respondieron200 y los tres endpoints404: **no se atribuyó a falta de permiso ni a un tenant ajeno**. OpenAPI público de la API ejecutada no contiene esas tres rutas; el contrato actual del checkout sí.

### Causa comprobada: no se está ejecutando el mismo backend

- `nexoruta-api`: `dotnet NexoRuta.Api.dll`, directorio `/app`, imagen `nexoruta-api`, sin bind mount de backend; creado2026-10-31, iniciado2026-11-01T16:05:24Z. SHA256 del DLL ejecutado **`002b78bc…cb72eac`**, distinto del Debug actual **`2cec0e6e…3dac79`**.
- La diferencia de hash sola no se toma como prueba de antigüedad. Se contrastó además el inventario OpenAPI y la presencia de nombres de tipos en el binario: el ejecutado incluye `ConfiguracionRepartoController`, pero no `FlotaController`, `EstimacionesController` ni `BaseOperativaController`; el build actual los incluye. Evidencia combinada de **artefactos/contratos distintos**, no una versión vieja supuesta. No se conoce/acredita el commit exacto del artefacto ejecutado.
- `nexoruta-backoffice`: SDK10, `dotnet watch --non-interactive --artifacts-path /tmp/nexoruta-artifacts ... run --no-launch-profile`, bind del frontend de este checkout a `/workspace`. Se comprobó coincidencia SHA del fuente montado y el checkout. El watcher recompiló la página nueva y sus mensajes; navegación real5101 los muestra. No se inició un segundo Backoffice operativo ni se modificó su dirección API.

### Segundo impedimento comprobado: esquema incompatible con el backend actual

[Lectura de esquema inicial](evidencias/vehiculos-integracion/schema-initial.txt) y [final](evidencias/vehiculos-integracion/schema-final.txt): **64 migraciones**, última `20261030120000_ListImportedShipmentReferences`; no existen `OcupacionesRuta`, `EstimacionesRuta` ni `PerfilesVialesVehiculo`. Faltan las etapas B2 y los esquemas B3/B4 ya documentados.

Recompilar y arrancar la API completa sin esa transición no sería una solución suficiente: sus consultas requieren tablas/columnas ausentes y no es seguro sustituir el binario. Ese arranque incompatible no se probó sobre operación. **No se hizo.** No se añadieron tablas vacías, aliases, respuestas simuladas200, fallbacks de disponibilidad ni compatibilidad con el esquema anterior. Las tres consultas se verificaron desde5101 y se conservan como fallidas; no se maquilló el resultado.

## 3. Tratamiento visible y bloqueo operativo

Los errores ahora identifican **GET, ruta y estado HTTP** en los tres puntos:

- `RutasModel.Cargar`: flota fallida ⇒ disponibilidad desconocida, no flota vacía/disponible.
- `RutasModel.CargarEstimaciones`: histórico fallido ⇒ error explícito, no «Sin cálculos registrados» ni estimación vigente.
- `ConfiguracionRepartoModel.CargarPerfilesAsync`: perfil fallido ⇒ error explícito, no estado de compatibilidad confirmado/no confirmado devuelto por la API. Si también hubo error de comando, se conserva junto al error de consulta.

No se exponen cuerpos internos de persistencia ni credenciales. Un nuevo vehículo que recibe respuesta200 de flota puede mostrar legítimamente **«Disponibilidad desconocida: verificación inicial pendiente»**; eso es distinto de un error de consulta HTTP. Asimismo `SinDeterminar` solo puede presentarse como dato de perfil si hubo respuesta válida, no como sustituto de404/500.

### Qué hace falta para corregir las tres consultas en la instancia operativa

Responsable de la transición debe aplicar el procedimiento07–12: detener/verificar escritores y jobs anteriores; disponer de **artefacto B2 compatible con Stage, con procedencia acreditada**; Stage → conciliación auditable → Enforce → B3 → B4, y recién después ejecutar una API construida del checkout compatible con ese esquema. Ese artefacto sigue sin estar acreditado; no se reconstruyó eliminando cambios.

**No ejecutar `levantar-entorno-dev.bat` para este arreglo:** su paso3 ejecuta `rls-migrator`, seguido de importación/provisión/bootstrap. `DatabaseInitialization__ApplyMigrations=false`/`SeedData=false` de la API actual no detienen ese comando externo. Tampoco ejecutar `database-migrate` durante la pausa entre Stage y conciliación, porque aplica todas las pendientes sin ese límite. No se ejecutó ningún comando de migración ni conciliación operativa.

Tras una transición expresamente autorizada: usar la construcción/reinicio por servicio del Compose existente, verificar hash/contrato publicado y repetir los tres GET desde Backoffice. Aquí no se cambió tag/imagen ni se reinició la API incompatible. **Ese es el bloqueo concreto pendiente, no una corrección que se haya dado por terminada.** No habilitar operación B2–B5 ni inferir seguridad física del backend actualmente ejecutado a partir de las pruebas del checkout.

## 4. Verificación ejecutada

| Capa | Resultado observado |
|---|---|
| RED acceso | `/vehiculos` devolvió404 antes de implementar; `cu06-vehiculos-red.log` |
| RED errores | Pruebas404/500 fallaron porque no se mostraban método/ruta/estado; `cu06-vehiculos-queries-red.log` |
| RED accesibilidad | Error de precisión no tenía `aria-invalid=true`; `cu06-vehiculos-aria-red.log`, corregido sin tocar precisión B1 |
| Frontend focalizado | **14 aprobadas**, `cu06-vehiculos-final.log`: permisos/menú, pantalla independiente, separación de compatibilidad, precisión/conflictos, lectura fallida y guardado desconocido sin perder valores, errores de las tres consultas, disponibilidad desconocida y regresión de configuración/base/navegación |
| Regresión visual B4 afectada | **1 aprobada** dentro del lote15 de `cu06-vehiculos-verified.log`: perfil/estimación inicial siguen operando después de separar la presentación. No se reabrieron aceptaciones ni suites ajenas |
| API real en aislamiento | **1 aprobada**, `VehiculosIntegracionBackofficeHttpTests.CurrentCheckoutPublishesFleetHistoryProfilesAndVehicleCrudWithIsolatedSchema`: tres consultas200, listado/alta/edición, deactivación/reactivación, rechazo1.005,409 sin sobrescritura; sin ocupación física creada |
| E2E real aislado | **1 aprobada**, `VehiculosBackofficeBrowserTests.ChromiumTraversesCheckoutBackofficeRealApiAndEphemeralPostgres`, `cu06-vehiculos-e2e-verified.log`. Chromium → Razor/Kestrel del checkout → HTTP API real → PostgreSQL efímero. No es FakeApi ni HTML estático. [GET/PUT observados](evidencias/vehiculos-integracion/aislado-api-queries.json) |
| Instancia5101 | Login de cuenta local configurada, solo consultas/navegación: menú y vehículos200, tres GET404 con mensajes visibles. Sin altas/ediciones/confirmaciones de negocio. [Estado local](evidencias/vehiculos-integracion/final-local.json) |
| Compilación | Backoffice/ApiClient y API/Infrastructure compilan en los lotes. Warnings NU1510 y CS8629 ajeno se conservan. Sin dependencias ni migración nueva |

Fixtures PostgreSQL existentes verifican propiedad/aislamiento; las únicas escrituras de catálogo fueron sobre bases efímeras. API/Backoffice de pruebas usaron loopback y se detuvieron al terminar. El contenedor y la base operativa no se recrearon ni migraron.

Las primeras ejecuciones de la nueva fixture de navegador fallaron por inicialización Kestrel de una factory delegada; se habilitó una inyección opcional de servicios de prueba sobre la **factory existente** y se utilizó su raíz. No se alteró el servidor operativo. Se corrigieron supuestos de la prueba: el botón después de un error se llama «Reintentar guardado» y un vehículo nuevo correctamente consultado sigue pendiente de verificación física. No se relajaron las garantías B2 para hacerlo disponible. La regresión detectó que al separar la pantalla se había eliminado la comprobación de lectura que impedía escribir política con API ausente; se restituyó esa guarda, no se debilitó el test.

### Navegador y capturas nuevas

Chromium **151.0.7922.34**, escritorio1440 y **320 CSSpx**, sin desborde general. Capturas reales generadas e inspeccionadas, no mockups:

- Instancia operativa: [vehículos320](evidencias/vehiculos-integracion/local-final-vehiculos-320.png), [menú1440](evidencias/vehiculos-integracion/local-final-menu-1440.png), [error de perfil](evidencias/vehiculos-integracion/local-final-perfil-1440.png), [error de histórico](evidencias/vehiculos-integracion/local-final-historial-1440.png).
- Aislado, API real y datos temporales: [menú320](evidencias/vehiculos-integracion/aislado-menu-320.png), [vehículos1440](evidencias/vehiculos-integracion/aislado-vehiculos-1440.png), [validación320](evidencias/vehiculos-integracion/aislado-validacion-320.png), [perfil200](evidencias/vehiculos-integracion/aislado-perfiles-320.png), [flota200](evidencias/vehiculos-integracion/aislado-flota-320.png), [histórico200](evidencias/vehiculos-integracion/aislado-historial-320.png), [resultado](evidencias/vehiculos-integracion/aislado-browser.json).

Se recorrió menú → Vehículos, alta con validación de campo y conservación, alta válida con doble click/un solo envío, edición de capacidades, deshabilitación y habilitación con incremento de versión. En320 se navegó desde Repartidores mediante Tab a Vehículos y Enter; `aria-current=page`, etiquetas, antiforgery y respuesta `role=status`. Las consultas del E2E tienen estados capturados en el servidor API, no se deducen de la ausencia de texto de error. La consulta local se mantiene separada de esa evidencia aislada y **no se afirma que los tres errores404 hayan desaparecido de5101**.

## 5. Preservación, archivos y pendientes

[16 archivos de código/pruebas modificados o agregados](evidencias/vehiculos-integracion/archivos-incremento.json); no se cambió contrato API/ApiClient/OpenAPI ni esquema. [Preservación](evidencias/vehiculos-integracion/preservacion.json):258 archivos locales previos conservados, ninguno eliminado;8 previos adaptados y13 superficies críticas B1–B5/mobile/clientes/model snapshot idénticas byte a byte. Docs01–12 intactos. Ramas y HEAD raíz/backend/frontend/mobile sin cambios; gitlinks divergentes preservados. Sin reset, checkout, actualización de submódulos, commits, push, despliegue ni subagentes.

- **Revisión nativa:** frontend OFF clone-local/backend ON global, leído sin cambiar preferencias. No se fabrica aprobación. La revisión anterior B1–B5 sigue pendiente por la capacidad de selección no expuesta documentada en11–12; no se reintenta indefinidamente.
- **Habilitación operativa pendiente:** transición/esquema y artefacto Stage ya indicados, además del piloto y perfiles constatados de B4/B5. Las llamadas reales siguen deshabilitadas, no se usaron claves viales ni se comprobaron tiempos reales en Uruguay.
- **Fallo de arquitectura previo** `ShipmentEndpoints_DeclareApiOwnedResponses`, esperado2/actual7, sigue abierto según baseline11; no se alteró ni se repitió esa suite ajena.
- Engram sin identidad runtime registrada: recuperación local en `odd/tasks/cu06-vehiculos-acceso.md`, mirror pendiente. No se afirma memoria atribuida guardada.

**Resultado:** acceso y presentación del catálogo corregidos, estados de error trazables y combinación del checkout verificada en aislamiento; tres consultas operativas bloqueadas por artefacto/esquema, sin ocultarlo. **CU06 no se declara cerrado.**

Risk: items2,3 (política de acceso a nueva página y traslado de handlers/consumidores SSR); implementación inline por prohibición de subagentes, sin aprobación nativa fabricada.
