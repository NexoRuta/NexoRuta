# Navegadores optativos — ejecución posterior a CU-11

Base comprobada del 03/11/2026: principal `337ca0bf155b6f3da875b6c7d215df128e97717a`, Backend `43cdaa82d9e2282f3aea309eb6aa5596c88a0b5e`, Frontend `bf36df3d02f6e4c9b098d5545a3483f4c6dea15e`, Mobile `74a25f1b5b18c7dfc006cf7df747d73b0ec4910a`. Ramas propias `test/navegador-optativos`; no se mezclan ramas ni se alteran datos de la prueba manual del 02/11.

## Aislamiento y prerrequisitos

Se reutilizan SDK .NET 10, Node 24.22.2, Chromium/Playwright, axe, pdftoppm y Docker existentes. Los hosts Razor de prueba escuchan exclusivamente en loopback. Las cuatro integraciones crean bases efímeras; las cinco pruebas frontend usan API en memoria y no acreditan persistencia real por sí solas. Los proveedores de geocodificación, mapas, estilos, tiles, sesiones y telemetría están controlados por los harness. Se descarga únicamente SDK/CSS público estático Mapbox 3.33.0, sin credenciales reales ni llamadas facturables. TLS conserva su validación.

La primera descarga SDK/CSS falló con `fetch failed/ECONNREFUSED`: el fetch de Node no usaba el proxy heredado. Se comprobó HTTP 200 al activar `NODE_USE_ENV_PROXY=1` en Node 24. Es preparación del entorno, sin cambio del producto ni bypass del proxy. No se imprimieron credenciales ni se versionaron perfiles, claves, logs o bases.

Gentle-AI/Engram y revisión nativa no están expuestos: no se afirma su ejecución. No se valida Android, cámara física/lector real ni CU-06. La base y los CU siguen pendientes de aceptación humana.

## Intención conservada de cada caso

| Caso optativo | Comportamiento comprobado por sus aserciones |
| --- | --- |
| `CommerceAuthenticatedApiAndRestrictedPostgresUseControlledProviderOnly` | Commerce autenticado, SDK/Marker/CSS Mapbox reales con estilo vacío; sugerencia, clic/arrastre, confirmación, reapertura, teclado, cuota/error y alternativa manual; handshake con otra actualización API para comprobar versión obsoleta, sin guardar sobre ella silenciosamente; persistencia, RLS y contador de consumo. |
| `AdmissionSelectsAdjustsQuotesSavesAndReopensBeforeShipping` | Alta Commerce con mapa simulado: buscar/seleccionar/ajustar destino antes de crear, conservar dos bultos y destino ante validación, cotizar y confirmar tarifa, detalle y reapertura/edición de ubicación; API autenticada y persistencia real. No acredita SDK real por este caso. |
| `ChromiumTraversesCheckoutBackofficeRealApiAndEphemeralPostgres` | Vehículos con menú/teclado, precisión decimal y error conservando campos, alta/edición/activación, versiones y doble submit; consultas reales de perfiles, Flota y estimaciones, sin inventar disponibilidad. |
| `RealLabelDecodingAndBackofficeReceiptUseRestrictedApiAndIsolatedPostgres` | PDF de etiqueta real → PNG → decodificador QR real, UUID persistido; teclado y cámara por MediaStream sintético con denegación/ausencia/cancelación; identificación GET sin recepción, discrepancia/incompleta/recotejo/completa, carga/doble envío, respuesta perdida tras commit y retry exacto, errores/foco, axe, 320px y texto 200%. |
| `BaseBrowserUsesRealRazorAndIsolatedApi` | Dirección y minutos de base, propuesta sin confirmación implícita, confirmación explícita, edición invalida punto, versión obsoleta conserva valores; planificación manual cruzando medianoche, teclado y 1440/390/320px. |
| `DestinationSearchSelectSaveEditAndManualFallbackInChromium` | Razor Commerce con API en memoria, SDK/Marker/CSS reales y estilo controlado; búsqueda/debounce/teclado, clic y arrastre físicos del puntero, guardar/reabrir, cuota y fallback manual; 1440/320px, cero peticiones externas inesperadas. No acredita DB real por sí sola. |
| `RoadEstimatesUseRealRazorWithIsolatedControlledData` | Perfil vial con compatibilidad explícita, razón y token ante conflicto; estimación separada de llegada manual, histórico/invalidez/validez desconocida; recálculo explícito, accesibilidad, doble clic y conflicto sin renovar comando automáticamente, 1440/390/320px. |
| `FleetBrowserUsesRealRazorAndIsolatedApiFixture` | Tarjetas, conteos globales, filtros/popstate, ocupaciones de todas las fechas; panel con focus trap/restauración/Escape, selección rápida/reduced-motion y 1440/768/390/320px; retorno conserva comando/ocupación/versión ante respuesta no confirmada, retry explícito y un solo submit. |
| `RoadUpdatesShowGpsManualInitialAndConflictInRealChromium` | Inicial/manual/actualización diferenciadas, GPS antiguo y precisión/horario recibidos, último éxito y validez desconocida; foco visible/Tab, doble clic, conflicto conserva comando/ocupación/versión y reenvío explícito accesible, 1440/390/320px. |

## Diagnóstico de las primeras ejecuciones

Frontend completo inicial: 478 aprobadas, 3 fallidas, 0 omitidas (481). Base y Flota optativas pasaron; destino falló al descargar SDK/CSS por la preparación del proxy; B4/B5 buscaban estimaciones en `/rutas` aunque el diseño aceptado las ubica en `/rutas/{id}`. Se conserva el circuito de conflicto, teclado, historial, responsive y doble envío en el detalle actual. B4 también leía el cuerpo oculto de `details`: se abre expresamente la versión vigente antes de comprobar llegada manual/calculada, manteniendo la comprobación de historia anterior.

Integración inicial: 1 aprobada (recepción), 3 fallidas, 0 omitidas. Vehículos buscaba Flota e historia en la antigua página combinada `/rutas`; se verifica Flota en `/flota` y estimaciones en el detalle de la hoja realmente creada, con su ID transmitido por la fixture. Se mantiene verificación pendiente del vehículo nuevo y consultas reales exitosas. El alta simulaba Mapbox pero no respondía a la carga de CSS ni a las operaciones de cobertura añadidas al mapa existente; se completa el doble de pruebas y se sirve CSS controlado, sin cambiar el producto ni llamar al proveedor. Los valores ocultos se excluyen del diagnóstico de campos para no registrar antiforgery. La fixture de destino ahora conserva el error del navegador si este sale antes del handshake, en lugar de ocultarlo bajo un mensaje genérico.

### Defecto demostrado: inicialización reentrante del mapa

La integración de destino llegó a encontrar **dos `.mapboxgl-canvas` en el mismo selector**, antes de poder iniciar el recorrido. `OnAfterRenderAsync` esperaba a importación/creación JS con `mapa == null`; una actualización de cobertura o callback JS podía provocar otro render durante esa espera y crear otra instancia. No se ocultó el problema con `.first()`.

Se añadió `RenderWhileMapCreationIsPendingDoesNotCreateAnotherMapOrKeyboardBinding`: detiene explícitamente `crear`, invoca un segundo render y exige una sola creación y un solo binding, libera la espera y verifica que un render posterior no recrea recursos. Contra el producto de la base falla `Expected: 1, Actual: 2`; con la protección de reentrada pasa. El render que inicializa aplica después los parámetros actuales. Se conserva el manejo de error existente y no se alteran la API, estados comerciales ni permisos.

Otros ajustes del harness: abrir el `summary` de cada versión por su texto propio (el cuerpo contiene referencias a otras versiones); comprobar el aviso vigente «Horarios orientativos: no confirman retorno, recepción ni disponibilidad» junto con llegadas manual/calculada, en lugar del texto anterior. En el alta, seleccionar exactamente el punto ya confirmado no genera una edición: el mapa simulado ahora ajusta realmente a otro punto al reabrir, preservando la intención de probar modificación y su aserción final de persistencia. El recorrido SDK real espera a que estilo/fuentes estén cargados y cámara inmóvil antes del clic; presencia del canvas no acredita que haya terminado el ajuste automático de cobertura.

### Intermitencia del harness de Flota

En repeticiones de B2 apareció `innerText == ''` al reabrir rápidamente el panel tras Escape/reduced-motion. Se agregó diagnóstico acotado (clases, visibilidad y título, sin formularios/tokens). En la falla: panel `show`, visibilidad del panel `visible`, `textContent` del título **B2-EN-CURSO**, pero visibilidad heredada del título **hidden**. La selección ya se había aplicado; esperar solo la clase del panel era insuficiente. Se espera ahora que el título sea realmente visible antes de exigir su texto exacto; no se reemplaza por `textContent`, no se elimina la comprobación de última selección y un título que permanezca oculto sigue fallando por timeout. No se cambia el producto Flota por esta observación.

En el clic SDK real se registró centro `(-34.905, -56.205)` correcto, pero el evento físico redondeado a píxel aportaba latitud `-34.904983502361176`: la prueba exigía 1e-5 grados a zoom 15 con un canvas de posición fraccionaria. Se aumenta zoom a 17 antes del clic, conservando exactamente esa tolerancia y comprobación de persistencia; no se amplía el margen para obtener verde.

## Preparación y reproducción

Desde el principal con submódulos, compilar los hosts actuales antes de ejecutar integración (no compilar mientras los harness usan sus DLL). Activar explícitamente los nueve optativos:

```bash
source scripts/cloud/env-agent.sh
export DOTNET_CLI_HOME=/workspace
export NUGET_PACKAGES=/workspace/.cache/nuget-packages
export NUGET_HTTP_CACHE_PATH=/workspace/.cache/nuget-http
export PLAYWRIGHT_BROWSERS_PATH=/workspace/.cache/ms-playwright
export NEXORUTA_PLAYWRIGHT_MODULE="$PWD/scripts/cloud/node_modules/playwright"
export NODE_USE_ENV_PROXY=1 # Node 24: mantener proxy/CA heredados
export NEXORUTA_B2_BROWSER_DIR=/tmp/nexoruta-optativos/b2
export NEXORUTA_B3_BROWSER_DIR=/tmp/nexoruta-optativos/b3
export NEXORUTA_B4_BROWSER_DIR=/tmp/nexoruta-optativos/b4
export NEXORUTA_B5_BROWSER_DIR=/tmp/nexoruta-optativos/b5
export NEXORUTA_DESTINATION_BROWSER_DIR=/tmp/nexoruta-optativos/destination
export NEXORUTA_GEOCODING_FULLSTACK_DIR=/tmp/nexoruta-optativos/geocoding
export NEXORUTA_VEHICLES_E2E_DIR=/tmp/nexoruta-optativos/vehicles
export NEXORUTA_RECEIPT_E2E_DIR=/tmp/nexoruta-optativos/receipt
dotnet test frontend/tests/NexoRuta.ApiClient.Tests --no-restore
dotnet test backend/tests/NexoRuta.IntegrationTests --no-restore --filter 'FullyQualifiedName~GeocodificacionFullStackBrowserTests|FullyQualifiedName~VehiculosBackofficeBrowserTests|FullyQualifiedName~RecepcionDepositoBrowserTests'
node --test frontend/tests/*.test.cjs
```

En otro entorno ajustar rutas de SDK/caché/Playwright; restaurar los locks y preparar dependencias según `docs/continuidad/cloud-agent.md`. Se requiere Docker local accesible, PostgreSQL/PostGIS de fixture, Chromium con bibliotecas del sistema, Node compatible, paquete `@axe-core/playwright` y `pdftoppm`. El SDK/CSS público requiere salida HTTPS por el proxy configurado. No se necesitan API keys reales, Android, emulador ni servicios habituales.

Los artefactos se guardan fuera del repositorio en `/workspace/.optativos-evidence`: TRX por ejecución, capturas, informes JSON, etiqueta sintética y logs privados. Se inspeccionaron visualmente destino con cobertura/marcador guardado y recepción completa a 320px; esto complementa las aserciones, no acredita todos los dispositivos. El PDF/frames de cámara son sintéticos y el test no usa un lector físico. No publicar la carpeta: los hosts de fixture pueden generar claves temporales y antiforgery de prueba.

## Resultados finales individuales

Todos los optativos solicitados se ejecutaron y aprobaron contra el checkout actual, sin casos bloqueados ni omisiones. Las ejecuciones rojas anteriores se conservaron como diagnóstico; no se contabilizan como aprobaciones.

| Prueba | Resultado | Duración del caso |
| --- | --- | --- |
| `CommerceAuthenticatedApiAndRestrictedPostgresUseControlledProviderOnly` | Aprobada | 00:00:25.8196976 |
| `AdmissionSelectsAdjustsQuotesSavesAndReopensBeforeShipping` | Aprobada | 00:00:11.0943059 |
| `ChromiumTraversesCheckoutBackofficeRealApiAndEphemeralPostgres` | Aprobada | 00:00:21.6618831 |
| `RealLabelDecodingAndBackofficeReceiptUseRestrictedApiAndIsolatedPostgres` | Aprobada | 00:00:24.8103836 |
| `BaseBrowserUsesRealRazorAndIsolatedApi` | Aprobada | 00:00:04.9729618 |
| `DestinationSearchSelectSaveEditAndManualFallbackInChromium` | Aprobada | 00:00:09.4776775 |
| `RoadEstimatesUseRealRazorWithIsolatedControlledData` | Aprobada | 00:00:04.2580535 |
| `FleetBrowserUsesRealRazorAndIsolatedApiFixture` | Aprobada | 00:00:03.0846254 |
| `RoadUpdatesShowGpsManualInitialAndConflictInRealChromium` | Aprobada | 00:00:03.7754492 |

| Ejecución final | Aprobadas | Fallidas | Omitidas |
| --- | ---: | ---: | ---: |
| Cuatro integraciones optativas juntas (`integration-final.trx`) | 4 | 0 | 0 |
| Frontend completo, cinco optativos activados + nueva regresión (`frontend-verified.trx`) | 482 | 0 | 0 |
| Pruebas Node completas | 21 | 0 | 0 |
| Flota después de esperar visibilidad, cinco repeticiones consecutivas independientes | 5 | 0 | 0 |

La integración conjunta duró 37s; frontend completo 55s. La prueba determinista nueva está incluida entre las 482; antes de corregir el producto falló 1/1 (`map-race-before.trx`), luego pasó. Las cinco repeticiones de Flota complementan su caso dentro de la suite, no se suman como cinco requisitos diferentes. No se agregaron `Skip`, filtros para retirar fallos ni ampliaciones de tolerancia. La suite frontend conserva regresiones de sesión y las correcciones anteriores de Flota/Depósito.

## Publicación y revisión

Se publicaron primero los submódulos en ramas propias `test/navegador-optativos`, con remoto, destino y contenido revisados antes de cada push. Principal conserva los gitlinks exactos y documentación; Mobile permanece sin cambios.

| Repositorio | Rama | Commit |
| --- | --- | --- |
| NexoRuta-Backend | `test/navegador-optativos` | `bf4da61134e2c04db66f0e21bb99167dfb49306e` |
| NexoRuta-Frontend | `test/navegador-optativos` | `1ca0172bec203af3fa860b34925e4562ec11ee44` |
| NexoRuta principal | `test/navegador-optativos` | Punta publicada de la rama que contiene este informe y los gitlinks anteriores |
| Mobile, sin cambios | gitlink conservado | `74a25f1b5b18c7dfc006cf7df747d73b0ec4910a` |

Para revisar sin integrar: `git clone --branch test/navegador-optativos --recurse-submodules https://github.com/NexoRuta/NexoRuta.git`, verificar `git submodule status` y ejecutar los comandos anteriores con los prerrequisitos. Comparar Backend contra `43cdaa8`, Frontend contra `bf36df3` y principal contra `337ca0b`. No se ejecutan merges. Revisar la base pendiente, después los cambios de submódulos y finalmente el principal con sus gitlinks.

La prueba manual Mobile del 02/11, Android/hardware, CU-06, origen del 401 histórico y la aceptación humana de otros CU no quedan resueltos por estos resultados. No hubo migraciones ni cambios de precios, declaraciones, etiquetas, permisos, RLS, autenticación, TLS, offline o `permanent=false`.
