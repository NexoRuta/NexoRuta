# Selector de destino: Mapbox temporal restaurado

> **Actualización posterior:** el modo vista previa y sus bloqueos quedaron sustituidos por la decisión explícita de guardar dirección/coordenadas. La evidencia original se conserva abajo. Véase [03-selector-guardar-reabrir.md](03-selector-guardar-reabrir.md).

## Qué quedó implementado

Mapbox conserva el mapa y vuelve a proveer la búsqueda del selector. **No se activó permanente, un plan pago, facturación ni tokens nuevos.** Se reutilizó el token público ya configurado en Commerce, sin modificar su valor. Las pruebas no hicieron llamadas reales al proveedor.

La implementación anterior en frontend (`a4b6dc4`, destino-mapbox.js) ya utilizaba Mapbox v6 forward. Se reutilizaron endpoint/parámetros y mapeo de features, eliminando su modo permanente. El transporte ahora está en backend para **reutilizar el corte PostgreSQL global del proyecto**, no en un contador por pestaña evadible. No es otra migración de proveedor o datos.

Flujo: SelectorDestino → DestinosEnvioApiClient → POST destino/busqueda → mismo caso de uso/permisos/repositorio → adaptador **Mapbox temporal**. `/propuestas` del destino también usa ese adaptador. Una dependencia keyed acota el cambio al controlador de destinos: el geocodificador de base operativa conserva su implementación independiente y Geoapify vial B4/B5 no fue modificado.

La atribución del selector es Mapbox. `destino-mapbox.js` conserva mapa/marcador/teclado, sin fetch geocodificador directo ni fallback. El transporte backend devuelve `Cache-Control:no-store`, no cachea resultados, sigue usando autenticación/tenant y no registra URL/key/payload del proveedor. El cliente HTTP no tiene retries, redirecciones ni loggers; la configuración existente no exporta spans HTTP salientes.

## Solicitudes exclusivamente temporales

Único transporte de búsqueda Mapbox en fuentes de producción:

```text
GET https://api.mapbox.com/search/geocode/v6/forward
q=<consulta escapada>&permanent=false&autocomplete=<true|false>
&limit=5&language=es&types=address,street,place,locality,neighborhood
```

El token se agrega únicamente a la solicitud y nunca a esta documentación. No hay `permanent=true`, places-permanent, batch ni fallback permanente. La regresión del transporte comprueba método/host/ruta/query en cada respuesta controlada; el test JS prohíbe reintroducir geocodificación en el módulo y verifica la política permanente del transporte. La inspección de backend/frontend/mobile encontró solo ese forward temporal.

Se conservaron mínimo3 caracteres, debounce300ms, cancelación y descarte por secuencia. No hay búsquedas al renderizar/reabrir, mover mapa/marcador, seleccionar o confirmar. Solo escribir explícitamente en Buscar dirección genera la búsqueda. Sin reintentos automáticos. Teclado Arrow/Enter/Escape conserva orden mediante interop serializado; la selección por teclado solicita render explícito porque no es un evento Blazor y las coordenadas persistibles del padre no cambian.

## Corte conservador del proyecto

Se reutilizan **la migración ya aplicada** `20261102000000_LimitGeocodingConsumption`, tabla UsoGeocodificacion y función reserve_geocoding_request. No se creó ni aplicó otra migración. Ambos geocodificadores comparten el mismo contador; no hay una cuota nueva que permita eludirlo.

Configuración compartida actual (productores/tests actualizados sin aliases de configuración vieja):

```json
"Geocoding": {
  "Consumo": {
    "MaxSolicitudes24Horas": 500,
    "SolicitudesPorSegundo": 3,
    "SolicitudesPorMinutoUsuario": 10,
    "TimeoutSegundos": 8
  },
  "Geoapify": { "PermitirLlamadasReales": false },
  "MapboxTemporal": { "Habilitado": false }
}
```

Appsettings queda fail-closed por defecto. **compose.dev.yaml habilita únicamente la búsqueda temporal solicitada** y referencia `${Mapbox__PublicAccessToken:-}`, la misma variable pública ya usada por Commerce. Geoapify de geocodificación permanece apagado; RoutingGeoapify sigue apagado e independiente. No se modificó `.env` ni se cambió un token/plan/cuenta.

Reserva atómica bajo lock PostgreSQL antes del envío, en transacción independiente comprometida: llamadas concurrentes respetan el mismo corte, recrear el servicio no lo reinicia, cancelar/fallar después de reservar **no devuelve el cupo**. Puede sobrecontar solicitudes reservadas que no llegaron a enviarse; es deliberadamente conservador. HTTP429 limita y la alternativa manual sigue operativa. Timeout no convierte ausencia de datos en coordenadas cero.

**No es garantía de costo cero ni un corte de facturación de la cuenta Mapbox.** No cubre otros proyectos/credenciales/aplicaciones que compartan cuenta, ni las cargas/tiles del mapa. No se inspeccionaron ni modificaron condiciones comerciales de la cuenta.

## Almacenamiento: incompatibilidad explícita y protección de la UI

Mapbox especifica que los resultados temporales no pueden cachearse/persistirse; cambiar a permanente es una modalidad distinta y **no está autorizada**. Fuentes oficiales consultadas sin invocar geocodificación: [Geocoding API](https://docs.mapbox.com/api/search/geocoding/), [Temporary versus Permanent](https://docs.mapbox.com/help/dive-deeper/understand-temporary-vs-permanent-geocoding/).

El guardado vigente persiste **latitud, longitud, versión y confirmación** en Direcciones; la descripción de la sugerencia no se guarda y la dirección registrada se conserva. Eso **no** convierte las coordenadas derivadas de Mapbox temporal en almacenables. Confirmar o mover un marcador tampoco lo hace.

Se implementó la corrección mínima sin borrar datos ni bloquear silenciosamente el guardado:

- Elegir una sugerencia la muestra como **vista previa temporal**, sin emitir sus coordenadas al formulario persistible.
- Aviso visible explica por qué no se puede guardar; confirmación deshabilitada. Mover el marcador temporal no levanta la restricción.
- Descartar vista previa limpia el estado temporal y restaura el punto previo o vista general; no borra el destino almacenado. No autoriza copiar sus coordenadas.
- La alternativa manual permite confirmar un punto obtenido de **una fuente independiente autorizada**. Se mantiene el contrato PUT, permisos, versión y control de concurrencia.

**Pendiente real de almacenamiento:** no se puede ofrecer búsqueda temporal → guardar ese resultado como destino con las autorizaciones actuales. La API PUT existente no tiene procedencia geográfica y no puede certificar que coordenadas enviadas por otro consumidor sean independientes; esta protección cubre el flujo normal de la UI, no demuestra cumplimiento global ni de datos históricos. No se borraron destinos existentes ni se inventó su origen. Resolver persistencia de resultados del proveedor exige una decisión contractual/producto posterior; esta tarea no la sustituye por permanente, otro proveedor o el supuesto de que mover el punto cambia la licencia.

## Pruebas y evidencia

Todo transporte de proveedor en las pruebas fue controlado, con claves sintéticas; SDK/tiles/telemetría del mapa sustituidos y red externa prohibida en Chromium. No se instalaron mocks en la instancia habitual.

| Tipo | Resultado |
|---|---|
| RED previo a implementación | Seleccionar resultado emitía coordenadas persistibles: fallo esperado documentado |
| Unitarias Mapbox/Geoapify |21/21; temporal fijo, sin caché/retry, mínimos, error/malformed, cancelación sin devolución; consumidor independiente preservado|
| Selector/cliente + navegador |9/9; selección temporal no emitida, cancelación/debounce/respuestas obsoletas y Chromium1440/320|
| JavaScript |3/3; sin geocodificación directa/permanente y orden de teclado|
| MVC/PostgreSQL/full stack |15/15; [log final](evidencias/mapbox-temporal/nexoruta-mapbox-integration-verified.log) de los casos afectados|
| Full stack controlado |Commerce/API/JWT/RLS/PostgreSQL reales en fixture, solo transporte proveedor/SDK controlados. Tres reservas y tres solicitudes controladas; cuarta rechazada; tres guardados manuales independientes, no resultados temporales|

Durante el desarrollo se corrigieron: aserciones específicas del proveedor anterior, render omitido de vista temporal tras JS interop y una dependencia de instrumentación innecesaria que fallaba en unitarias (se retiró, no se agregó paquete). El lote intermedio tuvo14 casos correctos y un fallo de navegador; este fue corregido y se reejecutó el caso y el lote final. No se presentan fallos intermedios como aprobación.

Capturas reales generadas e inspeccionadas: [vista temporal320](evidencias/mapbox-temporal/temporary-preview-320.png), [manual/error controlado320](evidencias/mapbox-temporal/destination-320.png), [1440](evidencias/mapbox-temporal/destination-1440.png). Foco visible, teclado, mensajes y ausencia de desborde comprobados; no certificación WCAG ni mapa/proveedor geográfico real.

Reproducción sin proveedor real:

```powershell
node --test frontend/tests/destino-mapbox.test.cjs
dotnet test backend/tests/NexoRuta.UnitTests --no-restore --filter 'FullyQualifiedName~GeocodificadorMapboxTemporalTests|FullyQualifiedName~GeocodificadorGeoapifyTests'
$env:NEXORUTA_PLAYWRIGHT_MODULE = '<playwright-core local existente>'
$env:NEXORUTA_DESTINATION_BROWSER_DIR = Join-Path $env:TEMP 'nexoruta-mapbox-temporal-browser'
dotnet test frontend/tests/NexoRuta.ApiClient.Tests --no-restore --filter 'FullyQualifiedName~DestinosEnvioPagesTests|FullyQualifiedName~DestinationSearchSelectSaveEditAndManualFallbackInChromium'
$env:NEXORUTA_GEOCODING_FULLSTACK_DIR = Join-Path $env:TEMP 'nexoruta-mapbox-temporal-fullstack'
dotnet test backend/tests/NexoRuta.IntegrationTests --no-restore --filter 'FullyQualifiedName~GeocodificacionFullStackBrowserTests|FullyQualifiedName~BusquedaDestinoSimuladaHttpTests|FullyQualifiedName~ConsumoGeocodificacionPostgresTests|FullyQualifiedName~DestinosEnvioHttpTests'
```

El runner histórico `scripts/geocodificacion/verify-local.cjs` ejercitaba búsqueda deshabilitada. Ahora aborta **antes de login/escrituras/consultas** si Mapbox temporal está habilitado; no debe repetirse ciegamente contra la instancia real como prueba de consumo cero. Se comprobó su rechazo preventivo.

## Entorno local y límites de la verificación

API reconstruida desde el checkout dirty y recreada con el Dockerfile/composición existentes, sin migraciones ni seed. Commerce reiniciado con su dotnet watch/bind existente. [Artefacto/flags/módulo servido](evidencias/mapbox-temporal/local-served.json): GET `/js/destino-mapbox.js` en Commerce5102 coincide **byte a byte** con el checkout. Historial sigue LimitGeocodingConsumption; contador habitual antes/después **0**. No se hicieron consultas reales a Mapbox ni se alteró token/plan/facturación.

La búsqueda queda habilitada en desarrollo **para futuras acciones explícitas del usuario**, con el token público existente. No se validaron su respuesta real, restricciones URL de ese token o calidad de resultados mediante consumo externo; los errores reales siguen visibles, sin fallback permanente. Una prueba controlada no demuestra precisión geográfica ni condiciones comerciales de la cuenta.

[Corrección de la misma cuenta de Backoffice](../cu06/16-acceso-cuenta-efectiva.md): flota403→200 con mismo JWT antes de cambiar datos; sigue200 después del reinicio; negativo403. La sesión abierta del navegador del usuario debe renovarse y queda pendiente de su comprobación, no sustituida por fixtures.

Cambios: adaptador Mapbox temporal, binding keyed en DestinosEnvioController/DI, configuración compartida de consumo/Program/compose.dev; selector/página/JS, tests y documentación. APIClient/OpenAPI no cambian porque rutas y DTO permanecen iguales. No se editaron GeoapifyRouting/B4/B5, mobile, migraciones, planes ni tokens.

Revisión nativa pendiente, fallo arquitectónico previo y precisión vial B4/B5 no validada se conservan explícitos; no se fabricaron aprobaciones. Sin subagentes, commits, push o remoto. Engram sin identidad runtime: trazabilidad local, no memoria atribuida.

Risk: items2/3/4/5 (asignación local autorizada, binding/configuración, orden asíncrono y actualización local). No se declara CU06 completo ni persistencia de resultados temporales autorizada.
