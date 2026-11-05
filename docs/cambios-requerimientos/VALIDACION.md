> El cuerpo original de este documento describe la **primera implementación**. Sus números son históricos. La ejecución de continuidad H1–H6 se registra en el apartado final y no acredita Android nativo.

# Verificación ejecutada — 5/11/2026

La evidencia corresponde a Linux Cloud con datos sintéticos propios, .NET SDK 10.0.401, PostgreSQL 18/PostGIS y conexiones runtime sin superusuario ni BYPASSRLS. No se accedió a Windows ni a sus bases/emulador. Se distingue el alcance de cada comprobación; no constituye aceptación integral de todos los CU.

## Compilación y pruebas automatizadas

| Comprobación | Resultado |
|---|---|
| API y Worker .NET | Compilan; advertencia NU1510 existente |
| Solución frontend: Backoffice, Commerce, Tracking, ApiClient | Compila; advertencias de analizadores existentes |
| Unitarias backend focalizadas: creación, agregación/transiciones y capacidad | 24 pasan |
| Frontend: tarifas, reglas, envíos del operador y rutas | 37 pasan |
| Mobile Application portátil, incluyendo ViewModels enlazados | 88 pasan en la ejecución final, incluidos ViewModels y distinción de visita completada |
| Integración nueva parcial permitida/rechazada/devolución y retiro exitoso/fallido | 5 pasan en tanda serial; parcial extendida y devolución operativa: 4 pasan |
| Regresión focalizada de intentos/devolución | Dos tandas de 6 pasan |
| Retiro y rechazo de imágenes corruptas con cifrado preservado | 6 pasan |
| Matrices SQL/dominio exhaustivas de envío y resultado de bulto | 2 pasan, incluyen todas las parejas de ambos enums |
| Firmas/contratos de funciones RLS | 1 pasa |
| Recorrido completo con conexión restringida | 1 pasa |

La tanda extendida de parcial verifica además carga incompleta permitida, asociación de prueba al bulto, reenvío idéntico, conflicto por versión, nueva ruta con solo pendientes, conservación de membresía histórica, segundo intento y conteo por bulto, devolución física y aislamiento de inbox por comercio/operador. La de retiro comprueba idempotencia de solicitud, franja/tarifa, foto y firma, visita fallida sin custodia inventada y entrega final al comercio.

Una regresión amplia inicial dio 82/83: una aserción contaba todo el outbox y asumía un solo evento. Se ajustó para contar el evento v1 cuyo significado debe conservarse; las nuevas notificaciones v2 son adicionales. La prueba específica pasa y conserva la aserción de un único aviso de ruta. Una ejecución amplia posterior dio 39/84 y 45 fallos por `ENOSPC` al acumular bases temporales. **No se declara verde esa suite completa.** Se continuó con tandas pequeñas y los recorridos relevantes, sin borrar volúmenes persistentes ni cambiar fixtures para ocultar el problema.

Comandos principales, con el entorno de [DEMOSTRACION.md](DEMOSTRACION.md) cargado:

```bash
dotnet build backend/src/NexoRuta.Api
dotnet build backend/src/NexoRuta.Worker
dotnet build frontend/NexoRuta.sln
dotnet test backend/tests/NexoRuta.UnitTests --filter 'FullyQualifiedName~CrearEnvio|FullyQualifiedName~Capacidad|FullyQualifiedName~CambiosRequerimientos'
dotnet test backend/tests/NexoRuta.IntegrationTests --filter 'FullyQualifiedName~C31_'
dotnet test backend/tests/NexoRuta.IntegrationTests --filter 'FullyQualifiedName~C37_'
dotnet test mobile/tests/NexoRuta.Mobile.Application.Tests -p:NuGetLockFilePath=obj/cloud.packages.lock.json
```

Usar `DOTNET_PROCESSOR_COUNT=1` para contener las bases concurrentes. Ejecutar filtros de integración en procesos separados en máquinas con poco disco.

## Demostración integrada y sin conexión

Ejecutada la secuencia setup → cliente portátil offline → terminación del proceso → cliente nuevo sync → finish → revisit. SQLite y tres archivos cifrados sobreviven al proceso; durante el tramo offline toda petición del cliente falla. La sincronización posterior entrega a API real, con confirmaciones persistidas. No es un mock del servidor ni una cola solo en memoria.

Se comprobaron parcial 2/3, retiro con foto/firma, rendición/cierre, recepción, entrega al comercio, retorno físico y liberación separados. `revisit` confirmó exclusivamente el pendiente y el recargo único de 25 UYU sobre snapshot histórico. Kafka local procesó contratos v2 hasta la bandeja Commerce; RabbitMQ generó enlaces públicos reales; se comprobó el conteo público y la ausencia de IDs internos. No se envió correo externo ni se consumieron servicios pagos.

`dev.py verify` comprueba la base migrada (78 migraciones), autenticación y rol API restringido. Las nuevas funciones y bandeja conservan RLS; tests usan actores ajenos para validar rechazo/filtrado.

## Navegador y límites nativos

Verificación con Chromium/Playwright, automatización, capturas y revisión visual en escritorio y 320 CSS px. La guía incluye el script reproducible y los artefactos locales. Se completó una solicitud real de retiro desde Commerce, con cotización y error recuperable por motivo vacío; se guardaron y reabrieron las tres reglas nuevas. Se revisaron envíos, ruta, reporte, reglas, retiro, avisos y seguimiento: sin desborde general a 320 px ni con texto al 200 %, foco alcanzable por teclado y cero hallazgos axe en esas siete pantallas tras corregir la lista de datos de carga y el título interactivo de Tracking. Las capturas de retiro a 320 px, ruta de escritorio y seguimiento a 320 px se inspeccionaron visualmente. Esto no certifica WCAG del producto completo.

La compilación Android fue intentada y se detuvo con NETSDK1147: falta el workload `maui-android`. Tampoco hay adb/emulador. No se declara build APK, cámara/escáner/firma nativos ni recorrido Android ejecutado. Los ViewModels se compilan en las pruebas portátiles; XAML y los componentes nativos requieren validación en una máquina Android habilitada.

## Publicación

Los commits se publican primero en los tres submódulos y después en el principal, todos en `feature/cambiosrequerimientos`, sin merge ni force push. Las bases efectivas están en el ADR. El manifiesto de esta entrega registra SHAs de componentes; el `checkpoint.json` anterior conserva su carácter histórico y no selecciona fuentes. Se clonó de GitHub la rama publicada en un directorio nuevo de `/tmp`, con `--depth 1 --recurse-submodules --shallow-submodules`. Git descargó los tres SHAs publicados y `verify-gitlinks.py` comprobó los tres sin cambiar fuentes. Desde ese clon se compilaron API, Worker, solución frontend completa y la herramienta portátil Mobile: cero errores. El ejemplo portátil Linux presenta dos advertencias CA1416 por permisos Unix; no afecta al cliente Android. El principal y cada submódulo permanecieron limpios tras las compilaciones. La corrección documental posterior conserva esos mismos gitlinks.

## Continuidad H1–H6 — 5/11/2026, nueva ejecución

Esta sección es evidencia nueva; los resultados anteriores permanecen como históricos. Se consultaron los remotos y se partió exactamente del snapshot solicitado. El checkout inicial `work` no era la feature: se seleccionó `feature/cambiosrequerimientos` y se materializaron sus gitlinks, sin ejecutar el checkpoint para elegir fuentes ni integrar develop.

| Hallazgo | Confirmación observada | Corrección y regresión |
|---|---|---|
|H1|Dos visitas por HTTP; PostgreSQL real rechaza la segunda con `55000`, «Accepted physical-delivery timestamps and proof deadline are immutable»|El agregado fija plazo solo en el primer hecho físico. H1H2 verifica segunda visita persistida, primeras fechas/plazo intactos y plazo propio de B2. Trigger histórico intacto.|
|H2|Tras vencer B1, completar B2 devuelve conflicto o su segundo vencimiento afecta cero envíos|Migración hacia adelante y admisión de evidencia por bulto dentro de `EntregaSinValidacion`. H1H2 cubre t0/t20/t60/t70/t80: B2 completa en plazo o también vence; B1 permanece vencido.|
|H3|Después de declarar entrega offline, `PuedeRegistrar` y la captura quedan deshabilitados|Proyección durable del diario local, prueba de visita propia y captura mediante comandos reales. H3 prueba reapertura SQLite/cifrado y no habilita evidencia de otra visita.|
|H4|Un acuse `Conflicto` por capacidad produce el mensaje «Retiro registrado»|Mensajes según acuse; pendientes/rechazos fuera de rendición; resolución explícita vinculada sin borrar diario. H4 prueba reinicio, nueva identidad de negocio y el mismo sobre al perder la respuesta de transporte.|
|H5|Al restaurar temporalmente solo el selector vial original, las tres regresiones de revisita reciben cero paradas cuando deben recibir una|Selector por visita activa/resultado/snapshot y estado operativo. Las pruebas corregidas incluyen ruta mixta, retiro pendiente, revisita y retorno sin pendientes, con HTTP vial controlado.|
|H6|Al restaurar temporalmente solo la validación original de operaciones, la admisión permite 501/1500 pero su operación devuelve HTTP 400; 1/500 sí avanzan|Sin máximo comercial inventado; transporte alineado y comando completo atómico. C37 recorre 1/500/501/1500 hasta depósito/comercio, incluyendo rechazo por capacidad y reintento sin duplicar efectos.|

Las restauraciones temporales de H5/H6 se hicieron exclusivamente para reproducir el defecto con las demás correcciones presentes, y se deshicieron antes de compilar y verificar el resultado final. No se publicó ninguna de ellas.

Comprobaciones nuevas ya completadas:

- Unitarias Backend: **336 aprobadas**.
- Frontend: **491 aprobadas, 5 omitidas** porque requieren habilitación opt-in de sus harnesses de navegador. La ejecución inicial falló por fixtures anteriores a estos requerimientos: navegación no inyectada, campos nuevos ausentes y expectativas de modalidades/textos antiguas. Se actualizaron los fixtures y se repitió la suite conservando sus aserciones funcionales.
- Mobile Core/Api/Storage: **36/63/35 aprobadas**.
- Mobile Application: **92 aprobadas**, con los ViewModels reales enlazados; capturas/ubicación nativas sustituidas por adaptadores portables identificados.
- H1H2: **3 aprobadas** sobre base que recibió las 78 migraciones anteriores y luego la nueva. Incluyen motivos inexistentes sin efectos parciales, reenvío idéntico, plazos persistidos y selección vial antes/después de la segunda visita.
- C31: **3 aprobadas**, parcial permitida/prohibida, devolución y replanificación; versiones, pruebas por bulto y outbox.
- C37: **5 aprobadas**, retiro fallido/replanificado y retiros de 1/500/501/1500, cada uno con ruta mixta, rechazo físico, resolución, reintento, rendición, recepción y entrega al comercio.
- `dev.py verify`: base sintética nueva con **79 migraciones**, PostgreSQL 18/PostGIS, autenticación y rol runtime sin superusuario ni BYPASSRLS; RLS forzado conservado.
- Demostración portable con API real: `setup` → `offline` mediante ViewModels → terminación del proceso → `sync` → `finish` → `revisit` → cliente `revisit`. Evidencias cifradas y tres operaciones offline conservadas. Parcial 2/3 y segunda entrega real 3/3; retiro hasta comercio; cierre, retorno y liberación separados. Recargo de visita de 25 UYU conforme a la configuración sintética, no un importe comercial nuevo.
- Kafka y RabbitMQ locales reales, Mongo y workers propios: avisos v2 llegan al inbox Commerce y se generan los enlaces públicos. Seguimiento HTTP verifica 2/3 y 3/3 sin IDs internos. No se envió correo externo ni se usaron mapas/geocodificación pagos.
- `verify-cambios-ui.cjs`: siete pantallas a 1440 y 320 px, reflujo/texto al 200 %, foco por teclado y cero hallazgos axe en ese alcance. Solicitud de retiro real con cotización y motivo obligatorio; reglas guardadas/reabiertas. Se inspeccionaron visualmente las capturas de retiro y seguimiento a 320 px y ruta en escritorio. No equivale a certificación WCAG general.

Una tanda amplia de integraciones encontró `53100 / No space left on device` mientras se incorporaban los brokers a la VM de 32 GB. Se interrumpió y **no se declara verde**. Solo se liberaron cachés HTTP NuGet y la descarga regenerable de Chromium completo de esta ejecución; se conservó el headless shell utilizado, los datos y todos los volúmenes. Las comprobaciones focalizadas se repitieron en procesos pequeños para liberar sus fixtures entre tandas. Los fallos de preparación de pruebas (hora de la franja, credenciales sintéticas, reservas de recursos) se resolvieron antes de atribuir resultados al producto.

Comandos de las suites y escenarios, con `scripts/cloud/env-agent.sh` cargado, cachés en `/workspace`, `DOTNET_PROCESSOR_COUNT=1` y `PLAYWRIGHT_BROWSERS_PATH=/workspace/.cache/ms-playwright`:

```bash
dotnet test backend/tests/NexoRuta.UnitTests --no-restore
dotnet test frontend/tests/NexoRuta.ApiClient.Tests --no-restore
dotnet test mobile/tests/NexoRuta.Mobile.Application.Tests -p:NuGetLockFilePath=obj/cloud.packages.lock.json
# Integraciones: cada línea en un proceso separado.
dotnet test backend/tests/NexoRuta.IntegrationTests --filter 'FullyQualifiedName~H1H2_'
dotnet test backend/tests/NexoRuta.IntegrationTests --filter 'FullyQualifiedName~C31_'
dotnet test backend/tests/NexoRuta.IntegrationTests --filter 'FullyQualifiedName~C37_'
python3 scripts/cloud/dev.py verify
node scripts/cloud/verify-cambios-ui.cjs
```

Migración: `20261105180000_IndependentParcelProofDeadlines`. No modifica migraciones históricas ni elimina datos. Se verifican base nueva y actualización desde `20261105063923_SnapshotParcelsPerVisit`. El rollback deliberadamente no vuelve a un proceso que puede dejar pruebas de bultos sin resolución; cualquier reversión requiere una migración correctiva revisada.

Android: `dotnet build mobile/src/NexoRuta.Mobile -f net10.0-android --no-restore` falla con **NETSDK1147**, falta `maui-android`. `dotnet workload list` no muestra workloads instalados y no hay ADB/emulador. No se acreditan APK, cámara, firma, escáner ni XAML ejecutado. Los pasos manuales están en DEMOSTRACION; la revisión nativa sigue pendiente. No se accedió al Windows del usuario ni se tocaron sus operaciones/planillas reservadas.

Las regresiones adicionales completaron **3 pruebas de firmas/aislamiento RLS**, **2 matrices SQL**, **5 de GPS/retorno/visitas resueltas** y **3 del circuito de prueba previo**. La prueba de evidencia exactamente en el límite detectó una carrera en la primera corrección local de H2: dos candidatos leídos antes del bloqueo podían incrementar dos veces la versión del envío. Se corrigió antes de publicar: después del bloqueo solo se actualiza el agregado si se resolvieron bultos o sigue aplicando el caso histórico sin resultados. Se repitió esa prueba junto con H1H2: **4 aprobadas**, incluyendo dos barridos simultáneos y conservación de evidencia al competir con ellos. La versión defectuosa intermedia no se publicó.

El runtime y los workers propios se detuvieron después de verificar la demostración. Se conservaron bases, volúmenes, claves locales y capturas. Se retiraron únicamente sus salidas de compilación regenerables para disponer de espacio para el checkout limpio.

## Publicación y checkout limpio de esta corrección

Los submódulos se publicaron primero en `feature/cambiosrequerimientos`; después se publicaron los gitlinks del principal. No hubo merge a develop/main ni force push.

| Repositorio | SHA publicado de las fuentes verificadas |
|---|---|
|Principal integrado|`380236678794e4fb275c82a3c86b610832741f04`|
|Backend|`f71b114ec0d4c0f832625e5e220befe654ad1850`|
|Frontend|`5190efff4d21e9a1a203915a9a57369dacfe2dae`|
|Mobile|`683766d6d8cd6c1bd9ce45bb12f6581ddb19b98c`|

Se clonó nuevamente desde GitHub con `--depth 1 --branch feature/cambiosrequerimientos --recurse-submodules --shallow-submodules`. Git descargó los tres commits anteriores por sus SHA; `verify-gitlinks.py` confirmó los tres. No se copiaron `.env`, bases, binarios, obj ni estado privado desde el checkout de trabajo. Se reutilizaron exclusivamente SDK, herramientas y caché NuGet del entorno.

Desde ese clon: API, Worker, solución Frontend completa y `Cambios.DemoMobile` compilan con **cero errores**, manteniendo advertencias de analizadores/NU1510/CA1416. Se ejecutaron **4 pruebas de plazos/concurrencia**, **5 de retiro** y **92 de Mobile Application**, todas aprobadas. Al terminar, el principal y los tres submódulos estaban limpios y sus gitlinks seguían coincidiendo. Comandos adicionales:

```bash
python3 scripts/cloud/verify-gitlinks.py
dotnet build backend/src/NexoRuta.Api
dotnet build backend/src/NexoRuta.Worker
dotnet build frontend/NexoRuta.sln
dotnet build tests/Cambios.DemoMobile
dotnet test backend/tests/NexoRuta.IntegrationTests --filter 'FullyQualifiedName~H1H2_|FullyQualifiedName~EvidenciaEnElLimite'
dotnet test backend/tests/NexoRuta.IntegrationTests --no-build --no-restore --filter 'FullyQualifiedName~C37_'
dotnet test mobile/tests/NexoRuta.Mobile.Application.Tests -p:NuGetLockFilePath=obj/cloud.packages.lock.json
```

Este cierre documental posterior conserva exactamente esos tres gitlinks. El SHA final del principal es `HEAD` del commit que contiene este documento; se informa con su enlace canónico en la entrega, evitando una referencia circular dentro de su propio commit. `entrega.json` registra el principal integrado comprobado y los SHA completos de componentes.

La búsqueda de PR para `head:feature/cambiosrequerimientos` no encontró una PR existente en ninguno de los cuatro repositorios. La consulta de ejecuciones de PR asociadas a los SHA devolvió listas vacías; no se acredita CI remota verde. Se mantuvieron los workflows existentes sin introducir nueva infraestructura.

**Conclusión:** correcciones H1–H6 implementadas, publicadas y listas para revisión técnica dentro de requerimientos 31–41. La aceptación operativa/integración final mantiene pendiente el recorrido Android nativo y las verificaciones manuales indicadas en DEMOSTRACION/TRAZABILIDAD. No se declaran aceptados otros CU ni se certifican servicios externos de comercios o correo.
