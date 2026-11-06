# Estado observado al preparar la guía

Fecha5/11/2026. Este documento registra comprobaciones de preparación, no una ejecución del recorrido de demo ni aceptación de los CU.

## Revisiones fijadas por el último despliegue develop

Actions run [42104311807](https://github.com/NexoRuta/NexoRuta/actions/runs/42104311807) terminó correctamente el 2026-11-05 a las 20:41:41 UTC. Desplegó `release-c5904be94e0e41f6b5ff20fc21dd1bb4` con el root y los gitlinks siguientes:

| Repo | SHA desplegado |
|---|---|
| Root | `5f79e1fbd16fb90b177dae1ac23188741ff0787` |
| Backend | `09538d989399b511473ad5af063754ea76d554a6` |
| Frontend | `d328e98c27db7c5cef018ab3492c54fc563eed49` |
| Mobile | `683766d6d8cd6c1bd9ce45bb12f6581ddb19b98c` |

El checkout principal del usuario sigue en `develop` en `871626c` y contiene cambios locales, incluida la edición protegida de `infra/gcp/plan-opt-06-carga-remota.md`. Esta actualización documental se preparó en un worktree limpio basado en el develop integrado; no se alteraron esos cambios ni se actualizaron los gitlinks.

La guía prioriza el código actual ante README históricos: hoy `HojaRutaViewModel` permite salida sin mapa offline preparado.

## Remoto y evidencia de Actions

Consultas de solo lectura con GitHub CLI:

- [Integrated CI del HEAD raíz871626c](https://github.com/NexoRuta/NexoRuta/actions/runs/42062120283): completed/success. Es estado del workflow consultado; no se descargaron ni revisaron todos sus artefactos/cobertura.
- [Último arranque remoto encontrado](https://github.com/NexoRuta/NexoRuta/actions/runs/41975206069): start/develop,5/11/2026,05:37–05:46UTC; source root f58290fd5dd1d50800343240758cc2bfd6e01b26. Es anterior al HEAD actual; consultar manifiesto efectivo de imágenes antes del ensayo.
- [Carga remota posterior](https://github.com/NexoRuta/NexoRuta/actions/runs/41986950047): completed/success,5/11/2026,07:23–07:31UTC; root8ad1a5d6b0bdb2b8661a6b5ebcc29aff01449d5a. Ese estado por sí solo no acredita SLO, concurrencia ni una nueva carga ejecutada por esta tarea. No describir OPT-06 como ausente basándose en la auditoría antigua.

Los logs del arranque contienen hosts `https://{servicio}.34-49-146-66.sslip.io` para api,backoffice,commerce,tracking,admin,mail,monitor. **No son valores permanentes**: tomar los vigentes del resumen de sesión.

Sondeo HTTPS con validación TLS normal,5/11 a las16:52:10UTC(13:52 Uruguay):

| Servicio/ruta | HTTP observado |
|---|---:|
| api `/health/live` |503|
| api `/health/ready` |503|
| backoffice `/` |503|
| commerce `/` |503|
| tracking `/` |503|
| admin `/` |503|
| mail `/` |503|
| monitor `/` |503|

No se diagnosticó infraestructura interna ni se inició una sesión. El apagado automático tras cuatro horas es una explicación posible consistente con el arranque temprano, no causalidad confirmada. Antes del ensayo el responsable debe comprobar estado/iniciar una sesión que cubra la reunión y volver a verificar HTTP.

## Bloqueos y alcance que no debe prometerse

1. **Recuperar enlace en GCP:** `deploy/gcp/compose.yaml` fija API Production; `backend/src/NexoRuta.Api/Program.cs` define `seguimiento-demo` únicamente para Development y `EnlaceSeguimientoController` la exige. Por inspección de contrato, la recuperación desde Commerce queda denegada en esa configuración. No se probó autenticado contra el remoto503. El endpoint público puede consultar un token legítimo existente, pero esta guía no fabrica/extrae tokens de la BD ni cambia Production para obtenerlos.
2. **Seguimiento incompleto:** `SeguimientoEstadoResponse` y Tracking ofrecen estado/identidad, sin historia ni ventana estimada. CU-25 parcial y AP-07 pendiente.
3. **CU-26–30 y capacidades relacionadas:** no se localizaron solicitud pública de reprogramación, avisos automáticos de estado a destinatarios, webhooks/suscripciones de comercios, hub/tablero de riesgo SignalR ni reportes/liquidación/cuenta corriente/cierre diario. La reprogramación operativa protegida, correos de códigos, `/flota`, Grafana y cierre móvil no sustituyen esos contratos.
4. **D-P01/D-P02 y CU-06:** compromiso temporal individual y resolución de discrepancias siguen pendientes de definición/aceptación; no inventar franjas prometidas, igualdad de medidas, retornos o habilitación operativa.
5. **Hardware/proveedores:** `adb devices -l` no mostró dispositivos conectados. No se ejecutó MAUI, cámara, GPS, biometría ni FCM en esta preparación. No se habilitó consumo real Mapbox/Geoapify. OPT-03/05 siguen parciales respecto a flota/replay e historial analítico, aunque existan Kafka/Mongo.

## Qué se comprobó y qué falta

- **Compilación:** no se recompilaron aplicaciones en esta tarea documental. Se consultó estado de Integrated CI del HEAD; no es una compilación local nueva.
- **HTTP:** ocho sondeos remotos negativos503 con TLS validado; sin autenticación ni consultas de datos de negocio.
- **Automatización:** validador offline aprobado:41 escenas sin dependencias circulares/ausentes y69 requisitos inventariados, incluidos los6 opcionales seleccionados. Generador ejecutado con UUID sintéticos: CSV de2/1/2/1/7 filas, todos de13 columnas; JSON/ficha de dos bultos y plantilla de41 resultados pendientes válidos. Repetir sobre la misma carpeta fue rechazado sin modificar archivos. Se comprobaron sintaxis Python y enlaces locales. Son comprobaciones del material de demo, no pruebas ejecutadas del parser C# ni del circuito web/Android.
- **Revisión visual:** no se hizo una revisión nueva de interfaces en navegador ni Android; no hubo cambios de producto/UI. El guion y los selectores se contrastaron con fuentes. Falta ensayar la versión remota y registrar evidencias por escena.

## Revisión e intento E2E adicional — 2026-11-05

Corte HTTPS del **18:07 UTC**: api /health/live, api /health/ready, backoffice, commerce, tracking, admin, mail y monitor respondieron **503**, con validación TLS. BrowserAct abrió el host remoto en la pestaña Chrome nexoruta-demo-tab; la pestaña mostró “unconditional drop overload”, no la interfaz de Backoffice. No hubo solicitudes autenticadas, escritura ni recorrido de negocio.

El SDK Android tiene emulator.exe, pero no tiene AVD ni imagen de sistema instalada; adb devices -l no mostró dispositivos. No se ejecutó MAUI en Android. Para completar el E2E hay que restablecer el ambiente remoto y disponer de un dispositivo/AVD. No se ejecutó start/develop: esa operación construye y despliega la revisión seleccionada sobre VMs/Cloud SQL compartidas; la habilitación operativa sigue pendiente y no se toma como autorización implícita.

### Verificación local adicional

- python scripts/demo/workflow.py validar: aprobado; 41 escenas y 69 referencias de alcance.
- Backend UnitTests: 328 aprobadas.
- API Release: compiló con 0 errores y una advertencia NU1510.
- Frontend ApiClient.Tests: 491 aprobadas y 5 omitidas; son pruebas opt-in que requieren fixtures/carpetas de Chromium aisladas (B2/B3/B4/B5 y Mapbox controlado).
- Mobile Core/Application/Storage/Api.Tests: 217 aprobadas en total.
- Tests JavaScript de frontend: 21 aprobadas.
- Total: 1.057 pruebas portátiles aprobadas y 5 omitidas. No acredita el circuito E2E.
- La revisión de Chrome solo pudo ver la respuesta de error del host; no se revisó visualmente la UI cargada. Sin dispositivo no se revisó Android.

Ver issues y bloqueos E2E en issues-e2e-20261105.md para causas, impacto y criterios de cierre.

## Start/develop autorizado y fallido — 2026-11-05

**Actualización posterior:** el intento 2 del mismo run terminó correctamente el 5/11 a las 19:38 UTC, tras aplicar el bootstrap pendiente (9 altas, sin cambios ni eliminaciones) y configurar GCP_LOAD_PREPARER_SERVICE_ACCOUNT en GitHub. A las 19:39 UTC los health checks y los portales devolvieron 200; Mail devolvió el 401 esperado por autenticación. Release: release-dfc484da5b8541e6aa226bab8a3a21dc. Las VMs están RUNNING y tienen límite de cuatro horas desde aproximadamente las 19:32 UTC, hasta las 23:32 UTC (20:32 Uruguay). E2E-DMO-05 está resuelto; el relato de fallo que sigue conserva la evidencia del intento 1.

El usuario autorizó ejecutar start en develop. [Actions run 42091707151](https://github.com/NexoRuta/NexoRuta/actions/runs/42091707151) publicó las imágenes correctamente, pero falló en OpenTofu apply. GCP rechazó permisos IAM porque no existe la cuenta nexoruta-load-preparer y devolvió 404 para el secreto nexoruta-load-preparer-credentials. El cleanup cerró la lease y detuvo las dos VMs. El código de sesión deja Cloud SQL encendido; no se modificó esa política.

El run intentó root 4e5c233dc751736ed59cc234582f157f5c9c278a; sus gitlinks fueron backend 09538d989399b511473ad5af063754ea76d554a6, frontend d328e98c27db7c5cef018ab3492c54fc563eed49 y mobile 683766d6d8cd6c1bd9ce45bb12f6581ddb19b98c. Son revisiones posteriores a las del workflow local; las pruebas locales no verifican estos cambios.

Sondeo HTTPS posterior, 2026-11-05 a las 19:24 UTC: los ocho endpoints listados arriba continuaban en 503. No se pudo navegar ni ejecutar el flujo. Ver E2E-DMO-05 y E2E-DMO-06 en issues-e2e-20261105.md.

## Revision tras recuperar el remoto -- 2026-11-05 20:00 UTC

Sondeo HTTPS repetido con validacion TLS: `/health/live`, `/health/ready`, Backoffice, Commerce, Tracking, Admin y Monitor devolvieron 200. Mail devolvio 401, respuesta esperada por su autenticacion. No se usaron credenciales ni se hicieron escrituras.

BrowserAct conserva el navegador Chrome `nexoruta-demo-chrome` y la sesion `nexoruta-demo-tab`, pero sus comandos `state`/`get title` y la apertura de una sesion nueva devolvieron `Connection health check failed` (codigo 210101). No se pudo revisar el DOM, capturar la UI ni confirmar login; no se considero evidencia de una falla de la aplicacion. Las VMs siguen dentro de la ventana iniciada aproximadamente a las 19:32 UTC, con apagado limite a las 23:32 UTC (20:32 Uruguay). A este corte no se completo ninguna escena de negocio ni se confirmo dispositivo Android.

El workflow de demo pasó el validador local: 41 escenas, 30 CU, 9 AP, 15 NFR y 15 opcionales inventariados. En Integrated CI del PR #68 fallaron los tres shards backend. El run 42098298395 terminó con 25 fallos, 679 aprobadas y 5 omitidas. Los tres shards fallaron; el test de seguimiento devolvió campos adicionales al contrato esperado y el test de flota encontró `EntregadoEnUtc` ausente en su esquema. Ver E2E-DMO-07/09 y E2E-DMO-08. El PR #68 se integró a develop a las 20:19 UTC (merge `5ddb9da`). El primer `update/develop`, run 42102394156, se detuvo en `tofu init` por la sintaxis del archivo generado, antes de leer/aplicar estado remoto o desplegar. No se cambió GCP y el health/portal smoke de las 20:20 UTC siguió en 200; E2E-DMO-10 registra la corrección en curso.

## Bootstrap automático y primer deploy corregido -- 2026-11-05

PR #68 integró el bootstrap previo a start/update en develop. El primer `update/develop`, run 42102394156, reveló HCL inválido antes de leer el estado remoto; PR #69 corrigió el formato multilínea y añadió una prueba de regresión. Las 213 pruebas de scripts/gcp aprobaron con 7 omitidas; `tofu fmt -check` y el validador del workflow también pasaron.

El run [42104311807](https://github.com/NexoRuta/NexoRuta/actions/runs/42104311807) ejecutó el paso automático de bootstrap y aplicó un plan de 0 altas, 1 cambio y 0 eliminaciones. El despliegue y los smoke checks terminaron correctamente. Los siguientes start/update en develop repetirán el bootstrap desde el workflow.

## Recorrido web con BrowserAct -- 2026-11-05 21:18 UTC

Se reinició Chrome por la ruta integrada `chrome://restart` después del error de conexión 210101; BrowserAct volvió a controlar el Chrome del usuario en pestañas de Commerce, Backoffice, Admin y Tracking. Se autenticaron cuentas sintéticas `@nexoruta.test` usando referencias privadas de Secret Manager. No se escribieron credenciales en este documento.

El sondeo HTTPS, con validación TLS normal, devolvió 200 en API live/ready y en Backoffice, Commerce, Tracking, Admin y Monitor. Mail devolvió 401, esperado por autenticación.

Commerce abre Mis envíos con un registro sintético. Al intentar “Ver seguimiento”, mostró “No pudimos abrir el seguimiento. Intentá nuevamente más tarde.” El portal anónimo de Tracking muestra que la consulta debe abrirse desde un enlace compartido. En Crear envío, el selector permite elegir Operador Demo Uruguay, pero para el punto sintético (-34.9, -56.2) la búsqueda de servicio informó que no hay cobertura ni tarifa; aparecen alternativas del juego compartido. No se confirmó el precio ni se envió el formulario. La pantalla advierte que Mapbox no está configurado y mantiene dirección/coordenadas manuales.

En Backoffice, Depósito no tiene recepciones pendientes; Rutas para 2026-11-05 muestra cero rutas y el planificador cero candidatos; no se creó una ruta vacía. Flota muestra “Disponibilidad desconocida” y HTTP 403 al llamar GET `/api/reparto/flota` para la cuenta `Propietario Operador`. Usuarios y accesos confirma que esa cuenta es propietaria y no hay Dispatcher activo.

Zonas muestra cero activas e inactivas; Tarifas indica “Sin publicación”. En `/zonas/crear` el mensaje “Cargando límites departamentales oficiales…” persiste después de recargar. El GeoJSON devuelve HTTP 200 y 16.944.285 bytes, pero el selector oficial sigue deshabilitado; el dibujo también requiere un token público de Mapbox. No se escribió una zona por fuera de la interfaz.

El registro precargado `GCP-S21-2026-10-28` aparece “Entregado” en ambas listas, pero Backoffice indica 0/1 bultos entregados, Resultado “Pendiente” y Custodia “Destinatario”. Su endpoint de etiquetas respondió HTTP 200 con MIME application/pdf. No se modificó ese registro.

La cuenta Comercio tuvo que volver a iniciar sesión tras un intervalo sin actividad. Esto se anotó como observación de sesión, no como defecto confirmado. El recorrido manual llegó a consulta y preparación de formulario; no se creó un tenant/run exclusivo ni se generaron nuevos envíos por los bloqueos documentados en E2E-DMO-11/12. La revisión visual de escritorio confirmó jerarquía, etiquetas y estados visibles de los formularios consultados; no se completaron teclado, zoom 200 %, reflujo a 320 px ni escaneo WCAG. Ver [issues E2E](issues-e2e-20261105.md).

## Instalación Android y revisión de acceso — 2026-11-05 21:48 UTC

Se emparejó por depuración Wi‑Fi el Samsung Galaxy S21 (SM_G991U, Android 14/API 34, `arm64-v8a`). A petición del usuario, se desinstaló el paquete anterior `uy.nexoruta.repartidor` y se instaló en limpio el APK recién compilado desde el gitlink mobile `683766d6d8cd6c1bd9ce45bb12f6581ddb19b98c`. La compilación seleccionó `NexoRutaBackendTarget=GcpDemo` y el origen HTTPS de la sesión. El APK instalado tiene `versionName=1.0`, `versionCode=1`, ABI `arm64-v8a` y SHA-256 `3786DA98EAE7EF2B8B482751353DDE898DF5CC9AFF50F1DDAC9285EF412E8E1C`. ADB informó `Success`; el paquete arrancó y se revisó visualmente la pantalla de inicio de sesión. El endpoint remoto `/health/ready` devolvió HTTP 200 a las 21:48 UTC.

No se ingresó una cuenta ni se envió un login: las claves disponibles en `nexoruta-demo-runtime` no incluyen un actor repartidor, y el juego compartido no se debe usar para crear cuentas o jornadas de prueba. Tampoco hay tenant exclusivo listo. Por eso no se pudo validar descarga de ruta, operación offline, sincronización, prueba de entrega ni retorno desde Android. Ver E2E-DMO-15. La compilación emitió advertencias XA0141 sobre bibliotecas nativas de Mapbox que no están alineadas a páginas de 16 KB; la app sí instaló y abrió en Android 14, por lo que no se registró como fallo reproducido de ejecución.
