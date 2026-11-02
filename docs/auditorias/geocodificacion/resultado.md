# Geocodificación de destinos sin Mapbox Permanent

> Antecedente histórico: el usuario decidió después restaurar Mapbox **temporal**, sin permanente ni planes pagos. La implementación y verificación vigente están en [02-mapbox-temporal.md](02-mapbox-temporal.md). Se conservan aquí las pruebas/limitaciones de la solución Geoapify anterior; no son el estado actual del selector.

Se eliminó la búsqueda directa/permanente de Mapbox y se reutilizó el geocodificador Geoapify del backend. **Verificación local completada con Docker disponible:** siete casos PostgreSQL aprobados, migración aplicada y servicios habituales funcionando con el checkout actual. Las llamadas reales continúan **apagadas**. No se realizaron solicitudes a APIs de proveedores, cambios de cuenta, commits, push ni despliegues remotos.

**Prueba local:** [Commerce](http://localhost:5102/envios) · [destino sintético guardado y reabierto](http://localhost:5102/envios/01a19a02-7867-71aa-a1d7-85ba95b7f5c9/destino) · [API readiness](http://localhost:5000/health/ready). Usar la sesión de comercio local existente. La búsqueda externa muestra el estado deshabilitado; la selección manual permanece operativa. No se instaló un proveedor simulado en el servicio habitual.

## Flujo y alcance verificados

- Superproyecto: `develop`. Backend/frontend: `fix/zonacobertura`, conservadas. `a4b6dc4` existe en frontend y está contenido en `develop`, `feature/cu07` y la rama actual. No se revirtió ese commit completo ni se tocaron cambios ajenos de CU06/mobile.
- `DestinoEnvio.razor` carga `SelectorDestino.razor`, que importa `destino-mapbox.js`. Antes el JS enviaba consultas Mapbox v6 con `permanent=true` y `autocomplete=true`. Ahora el módulo solo maneja mapa/marcador/teclado y el componente llama al backend con el token de sesión (no con una clave de proveedor).
- Nuevo POST autenticado `api/envios/{id}/destino/busqueda` reutiliza el caso de uso, las comprobaciones de comercio/estado y el adaptador Geoapify; no duplica repositorios ni persistencia. `/propuestas` y base operativa conservan la búsqueda completa; ambas modalidades comparten presupuesto.
- PUT de destino conserva versión, coordenadas y confirmación explícita. La dirección registrada permanece igual; la descripción elegida sigue siendo provisional. Seleccionar/confirmar/recargar no vuelve a geocodificar.
- Búsqueda de variantes permanentes, endpoints Mapbox search/geocoding, SDK de geocodificación y llamadas forward/reverse en fuentes backend/frontend/mobile: no se encontraron otras llamadas de geocodificación Mapbox después del cambio. Mapbox GL y mapas offline móviles permanecen; no se promete eliminar la facturación de mapas.

## Condiciones y protección de consumo

[Geoapify autocomplete](https://www.geoapify.com/address-autocomplete/) permite almacenar y cachear sugerencias. [Pricing](https://www.geoapify.com/pricing/) publica 3.000 créditos/día, 5 solicitudes/s y límites **soft**. La [documentación](https://apidocs.geoapify.com/docs/geocoding/address-autocomplete/) cuenta un crédito por autocomplete. Los [términos](https://www.geoapify.com/terms-and-conditions/) exigen atribuciones y contemplan sobrecargos. Consultados el 01/11/2026 como documentación pública, sin probar sus APIs.

El código no certifica costo cero: faltaría revisar la cuenta, sus demás consumidores y cualquier bloqueo de sobrecargos efectivo. Hasta entonces debe permanecer `Geocoding:Geoapify:PermitirLlamadasReales=false`. El contador local reserva antes de enviar, con 500 solicitudes/24h móviles y 3/s por defecto, persistencia en PostgreSQL y sin devolución por fallo/cancelación. No cubre otros servicios/proyectos de esa cuenta. La migración **ya está aplicada en la base local habitual**, sin borrar base ni volúmenes.

Configuración, límites ajustables, contrato, atribución, almacenamiento y activación segura: [documentación backend](../../../backend/docs/cu/destinos-envios.md#corrección-de-consumo-permanente-01112026).

## Evidencia de verificación

| Tipo | Comprobación | Resultado observado |
|---|---|---|
| RED → GREEN | `ClaveSolaNoAutorizaConsumoExterno` | Falló antes del cambio (una clave permitía HTTP); pasó después |
| Compilación | `dotnet build backend/NexoRuta.sln --no-restore --verbosity quiet` | Correcta; warning NU1510 existente |
| Compilación | `dotnet build frontend/NexoRuta.sln --no-restore --verbosity quiet` | Correcta; warning NU1510 existente |
| Unitarias backend | `dotnet test backend/tests/NexoRuta.UnitTests --no-restore --verbosity quiet` | 289 aprobadas; 15 del adaptador |
| HTTP simulado | `dotnet test backend/tests/NexoRuta.IntegrationTests --no-restore --filter FullyQualifiedName~BusquedaDestinoSimuladaHttpTests` | 7 aprobadas: MVC/caso de uso/adaptador reales, repositorio y transporte externos simulados |
| Unitarias/contratos frontend | `dotnet test frontend/tests/NexoRuta.ApiClient.Tests --no-build --no-restore --filter 'FullyQualifiedName~OpenApiContractTests\|FullyQualifiedName~DestinosEnvioPagesTests'` | 63 aprobadas; incluye 8 del selector/cliente y contrato |
| Suite frontend | `dotnet test frontend/tests/NexoRuta.ApiClient.Tests --no-build --no-restore --verbosity quiet` | 399 aprobadas y 5 omitidas (tests de navegador opt-in); ejecución fuera del sandbox |
| JS mapa | `node --test frontend/tests/destino-mapbox.test.cjs` | 1 aprobada: sin geocodificador, selecciona/edita marcador y respeta solo lectura; fetch prohibido |
| Navegador | `DestinationSearchSelectSaveEditAndManualFallbackInChromium` | 1 aprobada aparte: entrada corta, selección por teclado, guardado, reapertura/edición, cuota, 503 y mapa manual. API/SDK del mapa simulados y **cero solicitudes externas** |
| Revisión visual | Capturas reales Chromium a 1440 y 320 CSS px | Texto/atribuciones legibles, foco visible, mensajes claros y sin desbordamiento horizontal. No certifica WCAG ni el renderizado geográfico real |
| PostgreSQL — resultado definitivo | `ConsumoGeocodificacionPostgresTests` y `DestinosEnvioHttpTests` | **7 aprobados, 0 fallidos, 0 omitidos**, 31,9 s. Docker disponible; pruebas sin modificaciones ni debilitamiento. [Resultados por caso](evidencias/postgres-seven-results.txt) |
| Full stack nuevo | `GeocodificacionFullStackBrowserTests.CommerceAuthenticatedApiAndRestrictedPostgresUseControlledProviderOnly` | **1 aprobado**. Commerce y API reales en Kestrel, JWT/permisos y PostgreSQL con rol SQL restringido; solo transporte del proveedor controlado. [HTTP observado](evidencias/fullstack/api-queries.json) |
| Instancia local habitual | `node scripts/geocodificacion/verify-local.cjs` | **Aprobada** en Commerce5102/API5000/base habitual: 401 anónimo, 400 consulta corta, 503 deshabilitado, dos guardados/reaperturas por UI y 429 al límite HTTP. [Resultado](evidencias/local/result.json), [persistencia SQL](evidencias/local/postgres-verification.json) |
| Estructural | `git diff --check` en raíz/backend/frontend | Sin errores |

La primera suite frontend dentro del sandbox se interrumpió por una falla ambiental de permisos de Windows EventLog (`Cannot open log for source '.NET Runtime'`, acceso denegado). La repetición autorizada fuera del sandbox aprobó completa. El navegador también requirió ejecución fuera del sandbox para acceder al servidor Kestrel local.

Los builds/suites generales anteriores se conservan como evidencia de la primera entrega: **no se repitieron** en esta continuación. Se ejecutaron únicamente los siete casos pendientes, el nuevo full stack, el runner de la instancia habitual y una regresión del navegador anterior porque se parametrizó ese mismo script para reutilizarlo. No fue necesaria ninguna corrección del código de producto.

## Continuación definitiva: migración y servicios locales

### Siete casos PostgreSQL

| Caso | Resultado |
|---|---|
| Cuota compartida entre instancias concurrentes y recreación de servicio | Aprobado |
| Límite por segundo, reservas conservadas y ventana de 24 horas | Aprobado |
| Proveedor ausente y rechazo de JSON incompleto | Aprobado |
| Dos confirmaciones concurrentes con la misma versión | Aprobado |
| Completar destino pendiente tras recepción, sin editar uno confirmado | Aprobado |
| Cuenta ajena y operador no acceden al destino del comercio | Aprobado |
| Propuestas sin escritura y confirmación con rol SQL restringido | Aprobado |

Comando ejecutado:

```powershell
dotnet test backend/tests/NexoRuta.IntegrationTests --no-restore --filter 'FullyQualifiedName~ConsumoGeocodificacionPostgresTests|FullyQualifiedName~DestinosEnvioHttpTests'
```

### Migración local aplicada

1. Se cotejó el historial real: **68 migraciones**, terminando en `20261101213104_AddRoadEstimationHistory`. Stage, Enforce, B3 y B4 ya estaban aplicadas, según la [transición local documentada](../cu06/15-activacion-local-b1-b5.md); **no se repitieron** regularizaciones ni fases CU06.
2. Se detuvieron API y workers. Se reutilizó `transition.py backup --expected-migration ...AddRoadEstimationHistory`: respaldo consistente cifrado DPAPI CurrentUser/ACL, hash e ida/vuelta de cifrado comprobados, bajo `%LOCALAPPDATA%/NexoRuta/cu06-transition/517e7fdd146d`. No se restauró ni sustituyó la base habitual y no se exportaron secretos al repositorio.
3. Se generó con EF el [SQL exacto B4 → LimitGeocodingConsumption](evidencias/limit-geocoding.sql) y se aplicó con `ON_ERROR_STOP=1` en una transacción. SHA256: `4ededd9238369cd152cf6e33a136c7cd78c897650ef61841b0e85a41c5c30ab6`.
4. Historial final: **69 migraciones**, con **`20261102000000_LimitGeocodingConsumption`** como única adición. Conteos de envíos/direcciones iguales antes y después de migrar. El rol `nexoruta_api` puede reservar por la función, pero no leer la tabla contable directamente. [Manifiesto](evidencias/migration.json), [aplicación](evidencias/migration-apply.log).

No se ejecutó `database-migrate` general, seed, bootstrap, Down, borrado de datos/base/volúmenes ni desactivación de restricciones.

### Binarios y servicios actuales

- API reconstruida desde el checkout dirty actual con el Dockerfile existente y `RUNTIME_TOOLS=true`; tag local conservado `nexoruta-api:cu06-local-b1-b5`, imagen `sha256:4c9f271b9ddfce6b4426783f17038be9b2a148ff82dde8efacdf9f946d99c1ed`. Se recreó la API con los mismos archivos Compose/override documentados, `--no-deps --no-build`.
- Workers reanudados con su imagen previa: no necesitan recompilar para esta migración SQL aditiva ni intervienen en búsqueda. Commerce, Backoffice, Admin y Tracking se reiniciaron con su `dotnet watch` y bind existentes; compilaron y retomaron sus puertos. No se editaron `.env`, Compose ni el override privado.
- API/workers saludables; readiness **200** en API5000, Backoffice5101, Commerce5102, Tracking5103 y Admin5104. [Runtime](evidencias/runtime-current.json), [HTTP y módulo servido](evidencias/served-current.json).
- El módulo JS servido por Commerce es **idéntico byte a byte al checkout**, SHA256 `ef337b378344522f4116f3efc7468955e7a2e5fe482cc89d6eae6dd961015623`, sin exports/endpoints de geocodificación Mapbox.

### Dos niveles de prueba, sin confundir simulación con persistencia real

**Full stack aislado:** se añadió `backend/tests/NexoRuta.IntegrationTests/Envios/GeocodificacionFullStackBrowserTests.cs`, reutilizando los patrones existentes de Testcontainers, Kestrel, autenticación y rol SQL restringido. Commerce habla por HTTP con la API real y esta persiste en PostgreSQL real; no se sustituye el caso de uso, el repositorio ni el contador. Únicamente `HttpMessageHandler` del proveedor y el SDK cartográfico están controlados y no tienen salida externa. El flag del adaptador se activa **solo dentro de ese fixture con clave sintética**, nunca en la configuración habitual. Así se atraviesa el adaptador sin usar una credencial ni conectar con Geoapify.

Chromium escribió, eligió con teclado, guardó, recargó y volvió a editar; un error controlado 503 consumió su reserva y la cuarta consulta fue rechazada con cuota local429 antes del transporte. El test comprobó **tres reservas persistidas**, solo tres consultas al transporte controlado (`Primera`, `Cambio`, `Fallo`), tres PUT204 autenticados, versión final3, coordenadas manuales y dirección original conservada. También comprobó 401 sin autenticación. No hubo solicitudes externas. [Captura full stack320](evidencias/fullstack/destination-320.png).

**Instancia habitual:** se usó exclusivamente el login de aplicación local existente (nunca una clave del proveedor), se creó un envío sintético nuevo y se probó la UI real de Commerce5102. Búsqueda deshabilitada503, selección manual, dos confirmaciones y reapertura con versión2; consulta directa de PostgreSQL confirmó coordenadas y dirección original. El límite HTTP devolvió429 sin afectar la confirmación. El contador **permanece en cero** en esa base: no se reservó ninguna llamada al proveedor. En el contenedor efectivo `PermitirLlamadasReales=false`, sin clave Geoapify configurada y routing realfalse. El mapa se sustituyó en el navegador de prueba para no cargar SDK/tiles ni usar el token cartográfico; fuera de la prueba permanece el mapa normal, sin modificar configuración. [Captura deshabilitado1440](evidencias/local/disabled-1440.png), [guardado habitual320](evidencias/local/saved-320.png).

Revisión visual de estas capturas nuevas: mensajes/atribuciones legibles, sin desbordamiento a320px y confirmación persistida visible. No acredita una visita a un mapa/tiles reales ni certificación WCAG.

Repetición del full stack aislado (requiere Commerce Debug compilado y el módulo Playwright ya instalado):

```powershell
$env:NEXORUTA_PLAYWRIGHT_MODULE = '<ruta local a playwright-core>'
$env:NEXORUTA_GEOCODING_FULLSTACK_DIR = Join-Path $env:TEMP 'nexoruta-geocoding-fullstack'
dotnet test backend/tests/NexoRuta.IntegrationTests --no-restore --filter FullyQualifiedName~GeocodificacionFullStackBrowserTests
```

`node scripts/geocodificacion/verify-local.cjs` repite la comprobación habitual usando las dos variables locales de login Commerce, sin imprimirlas; crea **otro envío sintético**. El script bloquea todo host externo antes de navegar y nunca habilita Geoapify. No debe interpretarse como una prueba del proveedor real.

### Repetir navegador sin APIs reales

Usar el módulo `playwright-core` y Chromium ya instalados; no se agrega dependencia:

```powershell
$env:NEXORUTA_PLAYWRIGHT_MODULE = '<ruta local a playwright-core>'
$env:NEXORUTA_DESTINATION_BROWSER_DIR = Join-Path $env:TEMP 'nexoruta-destination-geocoding'
dotnet test frontend/tests/NexoRuta.ApiClient.Tests --no-restore --filter FullyQualifiedName~DestinationSearchSelectSaveEditAndManualFallbackInChromium
```

El test inicia Commerce real en Kestrel con API sintética en memoria; el SDK cartográfico se sustituye antes de cargar la página. Bloquea todos los hosts externos y verifica que no se intentaron solicitudes externas. No verifica mapas/tiles reales ni servicios reales de Geoapify.

Capturas revisadas: [320 px](evidencias/destination-320.png), [1440 px](evidencias/destination-1440.png). El mapa blanco con botón está **simulado intencionalmente**, no es una falla del mapa real.

## Archivos modificados por este encargo

Backend (rutas relativas a `backend/`):
- `src/NexoRuta.Application/Envios/Interfaces/IGeocodificador.cs`, `UseCases/GestionarDestinoEnvioUseCase.cs`, `Exceptions/GeocodificacionLimiteException.cs`.
- `src/NexoRuta.Infrastructure/Envios/Geocodificacion/GeocodificadorGeoapify.cs`, `ConsumoGeocodificacion.cs`; `Persistence/DependencyInjection.cs`; migración `20261102000000_LimitGeocodingConsumption.cs`.
- `src/NexoRuta.Api/Features/Envios/Controllers/DestinosEnvioController.cs`, `Contracts/Requests/BuscarDestinoRequest.cs`; `Features/Reparto/Controllers/BaseOperativaController.cs`; `Program.cs` y `appsettings.json` (solo límites de geocodificación, preservando cambios locales anteriores).
- `tests/NexoRuta.UnitTests/Envios/GeocodificadorGeoapifyTests.cs`; `tests/NexoRuta.IntegrationTests/Envios/BusquedaDestinoSimuladaHttpTests.cs`, `ConsumoGeocodificacionPostgresTests.cs`, `DestinosEnvioHttpTests.cs`; `tests/NexoRuta.IntegrationTests/Reparto/BasePlanificacionHttpTests.cs` (solo firma del doble existente).
- `docs/cu/destinos-envios.md`.

Frontend (rutas relativas a `frontend/`):
- `src/NexoRuta.ApiClient/Features/Envios/Clients/DestinosEnvioApiClient.cs`.
- `src/NexoRuta.Commerce/Components/Features/Envios/Pages/DestinoEnvio.razor`, `Shared/SelectorDestino.razor`; `wwwroot/js/destino-mapbox.js`.
- `contracts/nexoruta.openapi.json` (solo nuevo endpoint, preservando el contrato local anterior).
- `tests/NexoRuta.ApiClient.Tests/DestinosEnvioPagesTests.cs`, `DestinoGeocodificacionBrowserTests.cs`; `tests/browser/destination-geocoding.cjs`; `tests/destino-mapbox.test.cjs`.

Continuación: nuevo test `backend/tests/NexoRuta.IntegrationTests/Envios/GeocodificacionFullStackBrowserTests.cs`; runner `frontend/tests/browser/destination-geocoding.cjs` parametrizado para reutilizarlo; `scripts/geocodificacion/verify-local.cjs`; SQL, manifiestos y capturas bajo este informe. No hubo nuevas modificaciones del código de producto.

Raíz: este informe/capturas y el seguimiento local `odd/tasks/destination-geocoding.md` (ignorado por Git según configuración existente). No se modificó mobile.

## Pendiente y alcance de las garantías

1. **No queda pendiente la verificación PostgreSQL ni la migración local:** siete casos aprobados, migración aplicada y circuito completo comprobado. Servicios habituales funcionando.
2. Revisar cuenta Geoapify antes de habilitar llamadas; no se inspeccionaron credenciales, plan ni facturación. No hay garantía de costo cero de la cuenta ni de otros consumidores.
3. No se usaron APIs/tiles reales ni se revocaron tokens Mapbox. Clientes antiguos/otras aplicaciones pueden seguir consumiéndolos.
4. Engram rechazó guardado/resumen porque la sesión host no está registrada. Se conserva seguimiento local; no se inventó identidad ni se registró una sesión.
5. La limpieza de los directorios temporales propios del fixture fue rechazada por la política runtime. Se conservaron sus logs/claves sintéticos y capturas en TEMP, fuera del repositorio; no se intentó eludir la restricción. No afecta a los servicios ni a las comprobaciones aprobadas.

Risk: items 2 (nuevo endpoint con políticas existentes), 4 (presupuesto concurrente y respuestas asíncronas), 5 (configuración y migración). Trabajo y verificaciones inline, sin subagentes por instrucción expresa.
