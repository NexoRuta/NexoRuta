# Selector de destino: selección, guardado y reapertura

Fecha: 02/11/2026. Implementado y actualizado en la instancia local de prueba. Sustituye únicamente el modo vista previa de [02-mapbox-temporal.md](02-mapbox-temporal.md), por decisión expresa del usuario. No modifica B1–B5 ni el adaptador vial.

## Resultado y causa corregida

La selección volvía `(null,null,null)` al padre y activaba un estado de vista previa que bloqueaba confirmación. Se retiraron ese estado, callback, descarte y textos sobre fuentes independientes. Elegir una sugerencia ahora entrega texto y coordenadas válidas; ajustar el marcador conserva el texto elegido y cambia las coordenadas provisionales. Confirmar persiste ambos y reabrir carga el destino confirmado. No hay otro formulario ni paso nuevo; permanece la revisión expresa existente y la protección contra doble envío.

Además, el PUT existente solo guardaba coordenadas. Se extendió mínimamente para guardar también `direccion` (opcional para selección manual; null conserva el texto). No se guarda la respuesta completa de Mapbox. Dominio, API, caso de uso, repositorio, ApiClient y OpenAPI se actualizaron juntos. Texto no vacío, Trim, máximo240; coordenadas finitas/en rango; autorización, pertenencia, estado y versión se conservan. Una confirmación incrementa la versión una sola vez. Un409 conserva la selección, obliga a revisarla y nunca reenvía automáticamente con otra versión. La comprobación de resultado incierto compara también el texto.

El transporte existente sigue usando exclusivamente Mapbox v6 forward, `permanent=false`. Sin permanente, batch, fallback pago, búsquedas al renderizar/reabrir/mover el mapa ni reintentos automáticos. Se mantienen debounce300ms, mínimo3 caracteres, cancelación, descarte obsoleto y cuota compartida PostgreSQL (500/24h del proyecto,3/s,10/min por usuario, timeout8s; lo ya enviado consume aunque se cancele). No se cambiaron planes, tokens ni facturación; no se afirma gratuidad ilimitada.

## Persistencia y actualización local

Migración nueva **20261102010000_ConfirmSelectedDestinationAddress**, posterior a LimitGeocodingConsumption. No agrega tablas/columnas ni reescribe filas existentes: reemplaza la función de confirmación de4 argumentos por5 y concede UPDATE(Descripcion) exclusivamente al propietario NOLOGIN/NOBYPASSRLS `nexoruta_destino_fn`, no al rol API. Conserva RLS, comprobación de permiso vigente, pertenencia y bloqueo del operador/dirección; el UPDATE de texto/coordenadas/actor/fecha/versión es atómico. Down restaura la firma/grant anteriores, no revierte datos guardados después.

Se probó primero en PostgreSQL efímero (suite HTTP y flujo completo con rol SQL restringido) y sobre copia restaurada del esquema habitual69→70: hashes de todas las tablas idénticos salvo historial de migraciones. Respaldo cifrado DPAPI/ACL previo restaurado dos veces con hashes iguales, en `%LOCALAPPDATA%/NexoRuta/cu06-transition/cda030ef7775`. Tras detener API/Commerce se generó respaldo final `%LOCALAPPDATA%/NexoRuta/cu06-transition/cd9dfdcdae39`; sus herramientas de recuperación son las mismas ya verificadas en las dos restauraciones. No se borraron datos/volúmenes.

Se aplicó **solo** SQL EF69→70 con psql ON_ERROR_STOP, no database-migrate ni batch general. Hash de Direcciones antes/después idéntico. API reconstruida con backend/Dockerfile y composición local existente; Commerce reiniciado con su watch/bind. Migraciones y seeds automáticos siguen false; Geoapify geocoding y Routing reales false. [Digest de imagen, flags seguros, SHA del JS servido y comprobación PostgreSQL](evidencias/selector-guardar/local-result.json). El JS de Commerce5102 coincide byte a byte con el checkout y no contiene el antiguo método de descarte.

Recuperación: detener escritores, restaurar el dump final/roles mediante las herramientas DPAPI del procedimiento CU06 y ejecutar artefactos correspondientes al esquema69; alternativamente Down acotado requiere también el binario anterior con función4argumentos. Una restauración completa perdería escrituras posteriores: no aplicarla sin evaluar/exportar esas escrituras. No se ejecutó rollback sobre la instancia habitual.

## Verificación observada

| Ámbito | Resultado esperado/observado | Evidencia |
|---|---|---|
| RED previo | Elegir sugerencia produce texto/coordenadas; fallaba porque devolvía null | log privado nexoruta-selector-red.log |
| Componentes/ApiClient/contrato |8 pruebas correctas; selección, debounce/obsolescencia, lectura y PUT texto/versionado | DestinosEnvioPagesTests |
| Chromium fixture |1 correcta; teclado, selección, confirmar/reabrir, ajuste/edición, errores/cuota y manual,1440/320 sin overflow ni solicitudes externas | DestinoGeocodificacionBrowserTests |
| HTTP/PostgreSQL |12 correctas; autorización/otro comercio, versión/concurrencia, estado/recepción, búsqueda controlada. Las5 de Destinos se repitieron tras agregar casos de texto inválido/Trim/conflicto atómico y pasaron | DestinosEnvioHttpTests + BusquedaDestinoSimuladaHttpTests |
| Flujo completo aislado |1 correcta; Commerce autenticado→API real→función SQL con RLS→PostgreSQL; Mapbox HTTP controlado. Texto y coords conservados, versión5, cinco PUT204 y uno409; manuales y edición | GeocodificacionFullStackBrowserTests; [solicitudes](evidencias/selector-guardar/api-queries.json) |
| Política Mapbox |6 unitarias del adaptador y3 Node correctas: permanent=false, sin permanente/fallback y orden de teclado | GeocodificadorMapboxTemporalTests; destino-mapbox.test.cjs |
| OpenAPI |1 exportación generada correcta; se incorporó solo nueva propiedad direccion, preservando las modificaciones previas B1–B5 del snapshot | GeneratedOpenApiIncludesTarifarioRoutesAndExportsVersionedContractOnRequest |
| Compilación |API Debug/Release Docker y Commerce/tests correctos; advertencias NU1510/BL0005 existentes | logs privados selector-* |

Durante ajuste de las pruebas finales se corrigieron dos aserciones de prueba: OpenAPI generado no emite maxLength para el parámetro del record (la validación HTTP sí rechaza >240); y se espera el render asíncrono de Blazor antes de comprobar el botón habilitado. La ejecución final frontend9/9 pasó. No se ocultaron fallos funcionales ni se debilitó autorización.

### Instancia habitual, comprobación separada

URL **http://localhost:5102/envios**; selector `/envios/{id}/destino`. Envío sintético retenido identificado en local-result.json. API local PUT204 con dirección sintética; Chromium habitual con SDK de mapa simulado, sin escribir búsqueda: ajuste del punto, confirmación, GET/reapertura y SELECT directo PostgreSQL coinciden en texto, latitud-34.91, longitud-56.21 y versión2. Capturas reales inspeccionadas [1440](evidencias/selector-guardar/local-saved-1440.png) y [320](evidencias/selector-guardar/local-saved-320.png), mapa simulado ya cargado. Sin overflow. Cuenta Commerce local existente; ningún secreto aparece en evidencia.

La selección de sugerencias se acredita en el flujo completo **aislado**, no mediante consumo real desde la instancia habitual. El contador habitual UsoGeocodificacion era5 en el respaldo restaurado y sigue5 tras comprobar la instancia. Ninguna prueba hizo llamadas externas. Las capturas muestran SDK/tiles simulados, no cartografía real. [Selección320](evidencias/selector-guardar/selected-320.png), [conflicto320](evidencias/selector-guardar/conflict-320.png) y [escritorio aislado](evidencias/selector-guardar/destination-1440.png) fueron inspeccionadas; etiquetas, foco, teclado y mensajes sin bloqueo temporal.

## Archivos y preservación

Backend: ConfirmarDestinoRequest, DestinosEnvioController, GestionarDestinoEnvioUseCase, IDestinosEnvioRepository, EfDestinosEnvioRepository, Direccion, nueva migración70; pruebas HTTP/fullstack y fake de búsqueda. Frontend: SelectorDestino, DestinoEnvio, destino-mapbox.js, DestinosEnvioApiClient, snapshot OpenAPI y pruebas de componente/browser. Documentación de destinos y auditoría actualizada; evidencia nueva en selector-guardar/.

Ramas/HEAD intactos: raíz develop1ef2175; backend fix/zonacobertura a0aa204; frontend fix/zonacobertura e05c0de; mobile fix/zonacobertura78f65e1. Captura inicial y copias de cambios anteriores en `%LOCALAPPDATA%/NexoRuta/selector-guardar/20261101-234956`. Gitlinks y cambios previos preservados. Sin subagentes, commits, push ni remoto.

Revisión nativa pendiente (capacidad requerida previamente indisponible; no se inventa aprobación), fallo de arquitectura previo esperado2/actual7 y precisión vial Uruguay no validada se conservan. No se repitieron suites ajenas ni aceptación B2. No se declara CU06 completo. Engram sin identidad registrada: trazabilidad local, sin afirmar guardado atribuido.

Risk: items2/3/4/5 (función con permisos limitados/contrato, conflicto asíncrono y actualización local). La migración no cambia datos existentes.
