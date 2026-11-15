# Auditoría y plan de corrección de push Android con Firebase

Fecha: 14/11/2026. Alcance original: push en Android y dependencias de API, Worker, Firebase y distribucion. iOS queda fuera por indicacion del usuario. La implementacion Android se publico en `develop` el 15/11/2026 y la recepcion Firebase quedo comprobada en el telefono. Dos intentos de despliegue GCP fallaron durante el bootstrap de datos, antes de aplicar las imagenes. La consulta de solo lectura identifico una identidad administrativa huérfana que el bootstrap rehusa elevar; el Worker desplegado y el flujo de apertura/confirmacion siguen pendientes.

## 1. Dictamen y fuentes examinadas

**Android dispone de las piezas principales para enviar y recibir push. No corresponde afirmar que su circuito esté completamente verificado o correctamente configurado para cualquier entorno.** Hay defectos de recuperación y de estado de activación, y comprobaciones de configuración y diagnóstico que faltan. En este alcance se identifican tres problemas de código y un riesgo de configuración.

Inventario de fuentes de esta auditoría:

| Repositorio | Commit examinado |
| --- | --- |
| Raíz | `f65a98e068ea4824f91ed51249f1d1ab2caeaf72` |
| Backend | `7562ca95b91028b682fb0aa72883be79cd038441` |
| Mobile | `90976706c7db6a54c06ac552811f20f04d90375e` |
| Frontend | `2540041ba267d8a48e6c2b8a644247134f5b47f4` |

Se inicializaron los submódulos en esos gitlinks exactos. Las referencias de líneas siguientes corresponden a esas versiones. No se consultaron secretos, estado remoto de Firebase/IAM, variables privadas de Actions ni la configuración de una instalación existente.

### Piezas presentes

| Tramo | Implementación disponible |
| --- | --- |
| Android: configuración y consentimiento | `NexoRuta.Mobile.csproj`, `AndroidManifest.xml`, `RegistroPushPlataforma`, permiso Android 13+, canal de importancia alta e icono propio. JSON Firebase externo al repositorio. |
| Android: registro y recepción | `FirebaseMessaging.Register()`, `ServicioMensajeria.OnRegistered`, recepción en primer plano y notificación local; notificación de sistema en segundo plano; apertura en `MainActivity`. |
| Mobile: persistencia y consulta | FID en SecureStorage; identidad de instalación y referencias de avisos cifradas; validación de cuenta y payload; consulta autenticada del aviso y de su vigencia; confirmaciones separadas. |
| API | `PUT /api/mobile/instalaciones`, `DELETE /api/mobile/instalaciones/{id}`, listado/detalle de notificaciones y confirmaciones. Autorización por sesión mobile y permiso de reparto. |
| Backend | Productores de avisos por cambios de reparto, outbox, worker Push, Firebase Admin 3.7.0 y ADC, cifrado AES-GCM, funciones SQL restringidas y registro por destino. |
| Protección del destinatario | Filtros por operador, acceso, sesión vigente, credencial, permiso y repartidor activo; deduplicación por aviso/FID; resultados parciales persistidos; baja de instalación y revocación al salir. |
| Distribución | Script de APK y workflow mobile de desarrollo que incorporan Firebase; IaC Android/Firebase e IAM del proyecto de demo. El CI de verificación Android permite compilar sin Firebase deliberadamente. |

**FID en Android y en el servidor es correcto.** `MensajePushReparto.cs:9` usa `MulticastMessage.Fids`, no `Tokens`; el manifiesto Android activa `firebase_messaging_installation_id_enabled` y el adaptador usa `Register()`/`OnRegistered`. La documentación actual admite ese flujo. No reemplazarlo por tokens antiguos a partir de guías históricas: [registro Android](https://firebase.google.com/docs/reference/android/com/google/firebase/messaging/FirebaseMessaging), [MulticastMessage.Fids](https://firebase.google.com/docs/reference/admin/dotnet/class/firebase-admin/messaging/multicast-message).

Existe evidencia histórica de push real en S21 en `mobile/docs/validacion-local-s21.md`; no es una ejecución del checkout actual ni valida la configuración de GCP de hoy.

## 2. Hallazgos

### H01 — P1: fallos operativos impiden recuperar el registro push

**Reproducido con las clases originales y dependencias controladas.**

`mobile/src/NexoRuta.Mobile/SincronizacionConectividad.cs:30` sincroniza operaciones, acusa recepciones y refresca rutas antes de ejecutar `ActualizarRegistroAsync` en la línea 34. Toda la secuencia comparte un único `try/catch` y un plazo de 45 segundos.

Si falla cualquiera de esos pasos, no se actualiza el registro push. Esto afecta la recuperación tras un alta fallida, la renovación del destino y el reporte de permisos cambiado. Los callbacks y el ingreso ofrecen caminos alternativos, pero no garantizan recuperar un alta pendiente si el mismo fallo operativo se repite.

El probe local reprodujo por separado un fallo de sincronización y otro de ACK: en ambos casos hubo **cero intentos de registro**. No significa que Android nunca envíe registros: significa que este disparador queda bloqueado por trabajo independiente.

### H02 — P2: el estado visible no sigue el resultado asíncrono del alta

**Reproducida la activación que queda pendiente después de éxito.**

`Notificaciones/ControlNotificaciones.cs:23` elige el texto según exista un FID local. `RegistroRecibidoAsync`, en la línea 27, guarda el FID y llama a la API, pero no actualiza `Estado` ni emite un cambio observable. `Presentacion/PrincipalViewModel.cs:96` notifica `EstadoAvisos` solamente al terminar el comando de activación.

Con un callback posterior a ese comando, el registro puede completarse con éxito y la pantalla seguir en «Activando las notificaciones…». Un FID persistido tampoco demuestra un alta vigente para la cuenta, sesión y permiso actuales.

Además, `Platforms/Android/ServicioMensajeria.cs:23` silencia excepciones del callback. Conservar el trabajo para reintentar es adecuado; faltan un estado de alta pendiente/error y diagnóstico sanitizado que permitan saber qué ocurrió.

### H03 — P2: se pierden los motivos de rechazo FCM y se reintentan errores permanentes

**Confirmado por inspección del adaptador y del outbox.**

`backend/src/NexoRuta.Worker/Messaging/TransporteFcm.cs:21` distingue únicamente `Unregistered`; cualquier otro rechazo individual se convierte en `Reintentar`, sin conservar el código. `PushOutboxWorker.cs:90` transforma la falla parcial en una `HttpRequestException` genérica. El log y `MarcarErrorAsync` conservan principalmente el tipo de excepción.

Un proyecto incorrecto (`SenderIdMismatch`), un argumento inválido, cuota y una falla transitoria terminan sin diagnóstico específico. El outbox aplica backoff, pero no clasifica la permanencia del error. Puede reintentar reiteradamente un problema que exige corregir configuración, mientras el aviso siga vigente.

No desactivar instalaciones por cualquier `InvalidArgument`: también puede indicar un payload inválido. Tampoco desactivar por IAM/proyecto. Fuentes: [códigos del Admin SDK](https://firebase.google.com/docs/reference/admin/dotnet/namespace/firebase-admin/messaging), [tratamiento de registros inválidos](https://firebase.google.com/docs/cloud-messaging/manage-tokens).

### H04 — P1 si hay discrepancia: no se verifica la identidad Firebase entre APK y worker

**Riesgo de configuración confirmado; discrepancia efectiva NO comprobada.**

- `deploy/gcp/compose.yaml:475` asigna al worker el proyecto GCP de ejecución como `Push:ProjectId`.
- `infra/gcp/bootstrap/delivery.tf:152` concede envío al runtime en ese proyecto y crea su app Android.
- `mobile/.github/workflows/release-dev.yml:76` toma otro origen de configuración: el secreto independiente `MOBILE_FIREBASE_ANDROID_CONFIG_BASE64`. Su comprobación, en la línea 96, valida el package, pero no lo contrasta con el proyecto Firebase esperado para el backend elegido.
- El entorno local mobile fija `Push:ProjectId=nexoruta-mobile`; la documentación histórica menciona proyectos distintos. Esto puede ser intencional por entorno y no demuestra una falla remota.
- Los targets de validación del `.csproj` verifican existencia del archivo indicado, sin comparar el proyecto Firebase esperado. La clave de cifrado push se valida al usarla, no al arrancar el servicio.

Dos JSON pueden tener el mismo package y pertenecer a proyectos Firebase distintos. Compilar e instalar no verifica la correspondencia. El proyecto de destino del envío debe ser el de la app cliente; **la identidad ADC puede residir en otro proyecto** si tiene IAM de envío en el proyecto destinatario. No imponer igualdad entre el proyecto de origen de la credencial y el proyecto destinatario. Fuente: [autorización FCM entre proyectos](https://firebase.google.com/docs/cloud-messaging/auth-server).

### Configuraciones esperadas que no son errores

- `compose.override.yaml:46` activa `Push:NoSend=true` en Development. Ese transporte deja destinos reintentables y evita contactar Firebase; no acredita entrega. `Program.cs` impide usarlo fuera de Development.
- El CI Android de la raíz produce un APK de verificación sin exigir Firebase. No debe confundirse con el APK de distribución ni cerrarse esta auditoría con ese resultado.
- No versionar `google-services.json`, ADC, keystores o claves no es código faltante. Son entradas externas necesarias.
- Una aceptación FCM, una publicación del outbox, una recepción, una apertura y una confirmación del repartidor son hechos diferentes. El modelo existente los distingue y debe conservarse.

## 3. Plan de implementación para un agente de IA

Orden sugerido: T0 → T1 → T2 → T3 → T4 → aceptación Android. Implementar en los repositorios propietarios y actualizar los gitlinks juntos al integrar. Los cambios compartidos deben limitarse a lo necesario para Android. No iniciar CU08, CU09 ni un rediseño general.

### T0. Preparar el trabajo y pruebas de regresión

1. Leer `AGENTS.md`, los documentos de continuidad y los gitlinks actuales. Conservar cambios locales y no cambiar submódulos a otras puntas para resolver builds.
2. Leer `frontend/DESIGN.md` antes de modificar el estado visible. Reutilizar MAUI y sus componentes/tokens; estado pendiente, éxito, permiso denegado y error deben ser accesibles.
3. Convertir los escenarios H01/H02 en pruebas portables de la coordinación real. Extraer únicamente las dependencias necesarias de SecureStorage/plataforma y publicar cambios de estado de forma comprobable. No sustituir el adaptador nativo por un fake y declarar Firebase probado.
4. Mantener las suites actuales de avisos, sesión y outbox como regresión. Definir dónde se guardarán TRX, logs sanitizados y evidencia de dispositivo fuera de Git cuando contengan datos privados.

### T1. Recuperar el registro independientemente del trabajo operativo — H01

Archivos: `SincronizacionConectividad`, `ControlNotificaciones`, `IRegistroPush` y adaptador Android.

1. Dar al registro push un intento y plazo propios aunque falle sync, ACK o actualización de rutas. No usar un token ya agotado por las otras operaciones.
2. Persistir el alta pendiente de la identidad actual antes de enviarla; reintentar con backoff acotado al activar/reanudar/conectar. Evitar bucles continuos y uploads concurrentes del mismo registro.
3. Recuperar desde el SDK el registro vigente cuando corresponda, conservando `Register`/`OnRegistered` en Android. Reintentar no debe limitarse a reenviar indefinidamente un FID local que ya cambió.
4. Asociar cada intento a cuenta, sesión, FID y permiso capturados. Una respuesta antigua no debe marcar activa otra sesión ni reactivar una instalación después del logout. Respetar la exclusión existente en `ClienteSesionMovil`.

Aceptación: fallas controladas de cada paso operativo permiten intentar el alta; el permiso revocado se informa; al recuperar red se completa un alta pendiente sin pulsar repetidamente; logout y cambio de cuenta conservan su aislamiento.

### T2. Hacer que el estado de activación refleje el alta — H02

Archivos: `ControlNotificaciones`, `PrincipalViewModel`, presentación de cuenta y callbacks.

1. Distinguir disponibilidad del proveedor, permiso, registro FCM completado, alta pendiente en API y alta confirmada. «Activada» requiere ACK de la API para el registro actual; tampoco promete que el próximo mensaje se mostrará.
2. Actualizar y publicar el estado cuando finalice un callback, upload, reintento, denegación o logout. Llevar la actualización visual al dispatcher de MAUI.
3. Reemplazar los `catch` silenciosos por persistencia del pendiente y diagnóstico limitado a etapa/tipo/código seguro. No registrar FID, tokens, payloads privados ni credenciales.
4. Usar una generación o identidad de intento para rechazar resultados atrasados. Mantener reintento simple, sin bloquear la jornada por una falla exclusiva de push.

Aceptación: callback retrasado + HTTP 204 cambia automáticamente de pendiente a activa; fallo HTTP no anuncia éxito; cambiar cuenta/permiso antes de una respuesta impide aplicar el éxito anterior. No agregar skeletons artificiales a un botón de activación; usar progreso y estados claros según `DESIGN.md`.

### T3. Validar configuración de cada artefacto/entorno — H04

Archivos: workflow mobile, script de distribución, targets de build, configuración de despliegue y documentación operativa.

1. Definir un proyecto Firebase de destino explícito por entorno. No asumir que coincide con el proyecto que hospeda las VMs.
2. Comprobar el `project_info.project_id`, sender/project number y package de `google-services.json` contra ese contrato antes de distribuir. Comparar además el destino del worker. Reutilizar el contrato en ambos caminos de distribución; rechazar un archivo de otro proyecto aunque tenga el mismo package.
3. Verificar la identidad ADC efectiva y `cloudmessaging.messages.create` en el proyecto destinatario; no basta con descargar el JSON cliente. Soportar la identidad runtime con ADC existente sin introducir claves administrativas dentro de la app.
4. Validar al inicio del modo de envío real: proyecto, credencial disponible y formato de clave AES de 32 bytes. Comprobar privadamente que API y worker usan la misma versión de clave mediante su referencia de Secret Manager, sin imprimir claves ni huellas de secretos.
5. Hacer que un modo explícito de artefacto distribuible con push requiera configuración; conservar el build de verificación sin secretos y etiquetarlo correctamente. No romper por accidente el CI portable.
6. Añadir pruebas con configuraciones sintéticas correctas, proyecto incorrecto con package correcto, archivo ausente y clave inválida. No contactar Firebase en estas pruebas.

Aceptación: proyecto equivocado falla antes de distribución; proyecto/identidad/claves quedan verificables sin filtrar secretos. La configuración real se inspecciona solo cuando el entorno de aceptación esté disponible, sin modificar IAM automáticamente para aprobar la prueba.

### T4. Clasificar y observar fallas del proveedor — H03

Archivos: `ITransporteFcm`, `TransporteFcm`, `PushOutboxWorker`, persistencia de resultados y telemetría que requiera el nuevo contrato.

1. Conservar un código seguro de proveedor y categoría de resultado: aceptado, registro inválido, transitorio, configuración/autorización y mensaje inválido. Actualizar productores/consumidores juntos; no mantener aliases de contratos anteriores.
2. `Unregistered` sigue dando de baja solo al hash enviado. `InvalidArgument` exige distinguir destinatario inválido de payload inválido antes de dar de baja una instalación. IAM y sender mismatch no deben borrar registros válidos.
3. Aplicar reintentos con backoff/jitter a transitorios y cuotas, respetando la información de reintento que exponga el SDK. Definir tratamiento durable y recuperación explícita de errores permanentes/configuración, sin descartar avisos ni reintentarlos indefinidamente sin señal operativa.
4. Registrar códigos agregables y métricas por categoría; conservar correlación con el outbox sin copiar identificadores de dispositivo al log. Mantener los recibos de aceptación ya persistidos para no reenviar los destinos exitosos.
5. Si cambia persistencia, agregar migración hacia adelante; no editar/borrar migraciones antiguas ni perder registros cifrados. Mantener RLS, roles restringidos y protección de reservas.

Aceptación: pruebas cubren `Unregistered`, `InvalidArgument` de payload/destino, sender mismatch, autorización, cuota, indisponibilidad, respuesta parcial y FID rotado durante envío; los logs permiten distinguir la causa sin datos sensibles.

## 4. Guía de verificación paso a paso para el agente

### Paso 1. Registrar fuentes y aislar los efectos

Guardar SHAs de raíz/submódulos, SDK/workloads, plataforma, versión y hash del artefacto. Usar cuentas y envíos sintéticos, base y servicios propios. Leer los procedimientos de continuidad antes de instalar/arrancar. No usar la base del Windows del usuario como fixture Cloud ni borrar datos de una app para reiniciarla.

Durante automatización usar `ITransporteFcm` controlado; Mapbox `permanent=false` y Geoapify/SMTP controlados. Esta auditoría/plan no autoriza envíos productivos ni cambios IAM. Para aceptación real, identificar un dispositivo y destinatarios de prueba habilitados expresamente; si faltan, dejar ese resultado pendiente y completar las verificaciones independientes.

### Paso 2. Ejecutar regresiones portables

Desde `mobile/`, con el SDK del `global.json` y locks del checkout de implementación:

```powershell
dotnet test tests/NexoRuta.Mobile.Application.Tests/NexoRuta.Mobile.Application.Tests.csproj --filter "FullyQualifiedName~AvisosRepartoTests|FullyQualifiedName~SesionTrabajoTests" --logger "trx;LogFileName=push-application.trx"
dotnet test tests/NexoRuta.Mobile.Api.Tests/NexoRuta.Mobile.Api.Tests.csproj --filter "FullyQualifiedName~Salida|FullyQualifiedName~RegistroPush|FullyQualifiedName~Instalacion" --logger "trx;LogFileName=push-session.trx"
dotnet test tests/NexoRuta.Mobile.Application.Tests/NexoRuta.Mobile.Application.Tests.csproj --filter "FullyQualifiedName~ServicioRegistroPushTests" --logger "trx;LogFileName=push-registration.trx"
python -m unittest discover -s tools/tests -p "test_*.py" -v
```

Comprobar el número de pruebas: una ejecución sin coincidencias no aprueba nada. En el checkout auditado, `ClienteSesionMovilSalidaTests.cs` contiene parte de la clase `ClienteSesionMovilTests`, no una clase con el nombre del archivo.

Ejecutar después las pruebas nuevas de T1/T2/T3/T4. Sus escenarios mínimos deben incluir:

| Caso | Resultado exigido |
| --- | --- |
| Callback FCM llega después de terminar Activar | Pendiente → activa después de HTTP 204, con cambio observable. |
| API rechaza o pierde la respuesta del alta | Pendiente/error recuperable, sin éxito aparente, identidad local estable. |
| Falla sync, ACK o refresco de ruta | Se intenta el registro push con su propio plazo. |
| FID cambia con upload anterior pendiente | Se conserva el vigente; la respuesta anterior no modifica su estado. |
| Logout coincide con callback/upload | No reaparece un destino activo tras la revocación. |
| Cambia cuenta/tenant | Ningún callback o referencia se aplica a la cuenta siguiente. |
| Proveedor rechaza parcialmente | Solo se reintentan los destinos pendientes; quedan recibos de éxitos. |
| Configuración de otro proyecto | Falla el preflight aunque el package sea correcto. |

### Paso 3. Probar API, SQL y worker con transporte controlado

Con Docker disponible, ejecutar desde `backend/` la fixture propia; en Linux sin Docker usar únicamente la fixture nativa documentada con PostgreSQL18/PostGIS, `NEXORUTA_TEST_POSTGRES_MODE=native`. No sustituirla por una conexión operativa.

```powershell
dotnet build src/NexoRuta.Worker/NexoRuta.Worker.csproj
dotnet test tests/NexoRuta.IntegrationTests/NexoRuta.IntegrationTests.csproj --filter "FullyQualifiedName~PushOutboxTests|FullyQualifiedName~ReasignacionPushTests|FullyQualifiedName~CancelacionPushTests|FullyQualifiedName~CancelacionPublicaPushTests|FullyQualifiedName~SalidaPushTests" --logger "trx;LogFileName=push-integration.trx"
```

Desde el proyecto de pruebas unitarias, ejecutar tambien `dotnet test tests/NexoRuta.UnitTests/NexoRuta.UnitTests.csproj --filter "FullyQualifiedName~PushErrorClassificationTests"`. El test `FalloParcialReintentaSoloElDestinoQueNoFueAceptado` verifica la cuota, el backoff persistido y la conservacion del destino aceptado.

Añadir el filtro de las pruebas nuevas según su ubicación real. Revisar HTTP 204 de alta, cifrado del FID, autorización 403/404, sesión vencida/revocada, permiso denegado, roles worker restringidos, reserva vencida, duplicados, rotación concurrente y fallas parciales. Una aceptación controlada no acredita aceptación Firebase ni recepción en dispositivo.

### Paso 4. Comprobar configuración efectiva antes de contactar Firebase

1. Definir `NEXORUTA_FIREBASE_ANDROID_PROJECT_ID` con el mismo ID que `Push:ProjectId` del Worker y ejecutar `tools/validar-firebase-android.py --config <google-services.json> --project-id "$NEXORUTA_FIREBASE_ANDROID_PROJECT_ID"`. El preflight exige el package `uy.nexoruta.repartidor` y que el app ID use el numero de proyecto esperado. No deducirlos de un APK previo o una guia historica.
2. Comprobar API FCM habilitada, IAM de envío para la identidad ADC efectiva y correspondencia del package Android registrado en Firebase con el del APK.
3. Verificar HTTPS accesible desde el teléfono y clave de cifrado consistente API/worker. No desactivar validación TLS.
4. Verificar que el servicio de aceptación usa `Messaging:Transport=Push` y transporte real. `Push:NoSend=true` invalida una conclusión de entrega real.
5. Si hay dos réplicas, verificar que ambas usan el mismo contrato de destino y secreto persistente. No regenerar la clave para resolver un error de descifrado.

### Paso 5. Construir e inspeccionar el artefacto nativo

Usar `mobile/tools/apk-distribucion.sh` o el camino de distribución corregido con sus entradas externas. Registrar SHA256, package, firma, endpoint HTTPS y metadatos públicos del proyecto Firebase; no publicar el JSON entero. No confundirlo con el APK de CI sin Firebase.

Instalar únicamente en el dispositivo de pruebas previsto. Si se actualiza una instalación con datos, verificar primero package y firma y usar actualización conservadora; no desinstalar ni limpiar datos para solucionar incompatibilidades. Una variante necesita su propia app Firebase registrada; la variante `uy.nexoruta.repartidor.validacion` sin Firebase no sirve para esta aceptación.

### Paso 6. Verificar inscripción y permisos

Ingresar con un repartidor sintético activo y activar avisos. Verificar por separado permiso del sistema/canal, callback de registro FCM y HTTP 204 del alta. Consultar con una herramienta autorizada el registro protegido: cuenta, sesión, plataforma, activa/permitida y fecha; no imprimir FID descifrado.

Comprobar que el estado de la app cambia al recibir el ACK. Repetir con permiso denegado, canal bloqueado, permiso reactivado, primer arranque sin red y API temporalmente no disponible. Comprobar recuperación automática y ausencia de éxito aparente. Incluir el permiso de notificaciones en Android 13+ y el bloqueo individual del canal `nexoruta.avisos`.

### Paso 7. Probar un evento real de NexoRuta con app abierta

Preparar el caso válido de reasignación antes de salida, con ruta original, planificación futura y destinatario actual conocidos; seguir `mobile/docs/push-reasignacion.md` y los contratos vigentes para no producir un aviso obsoleto. Realizar la reasignación por API o interfaz real.

Correlacionar aviso → mensaje outbox → resultado por instalación → recepción observada → notificación visible. Verificar un solo aviso visual por ID, payload mínimo, ausencia de datos de destinatario y ausencia de aviso urgente al repartidor futuro. Repetir el flujo de cancelación válido sin duplicar efectos.

### Paso 8. Probar segundo plano y proceso ausente

Repetir con app en segundo plano, pantalla bloqueada y proceso ausente. En Android, retirar de recientes no garantiza que el proceso termine: comprobar su ausencia antes de generar un aviso nuevo. **No usar Forzar detención/`am force-stop` como equivalente de app cerrada**. El control de fuerza de detención, si se ensaya, debe registrarse como condición distinta; [condiciones de recepción FCM](https://firebase.google.com/docs/cloud-messaging/flutter/receive).

Comprobar notificación visible y tocarla. La app debe abrir el aviso correcto, exigir desbloqueo según su política, consultar vigencia y separar `Recibido`, `Abierto` y `Confirmado`. En segundo plano el sistema puede mostrar la notificación sin ejecutar el callback de datos antes del toque: no inventar un ACK de recepción que el cliente no observó. Probar apertura con proceso Android vivo y arranque en frío mediante `MainActivity`.

### Paso 9. Probar rotación, reconexión y salida

1. Usar una instalación de pruebas prescindible para provocar renovación mediante las APIs oficiales del modo FID y completar su reinscripción; no borrar el estado operativo de la app habitual.
2. Verificar que el alta actualiza el destino, que el viejo deja de ser elegible y que un rechazo tardío no desactiva el nuevo. En pruebas controladas simular además la carrera exacta durante envío.
3. Cambiar conectividad y provocar una falla de sync/ACK de forma controlada. Confirmar que sigue intentándose el registro push.
4. Completar logout y verificar baja + revocación. Generar un evento nuevo después del logout: el worker no debe seleccionar esa sesión. Un mensaje que Firebase ya hubiera aceptado antes de salir puede estar en tránsito; distinguirlo con su correlación.
5. Ingresar con otra cuenta autorizada y comprobar aislamiento de avisos, referencias persistidas y callbacks anteriores.

### Paso 10. Probar fallas sin depender de errores reales del proveedor

Inyectar en el transporte las respuestas de T4. Comprobar tratamiento durable, backoff y alertas, sin provocar fallas deliberadas en un Firebase compartido. El proveedor real puede usarse para un envío positivo acotado; un mock nunca cierra la prueba de recepción real.

Repetir aviso duplicado/obsoleto, confirmación perdida y entrega offline concurrente para comprobar que una notificación no ejecuta decisiones de negocio ni pierde hechos/evidencia locales. Conservar la semántica de custodia y de conciliación existente.

### Paso 11. Revisar interfaz y entregar evidencia separada

Probar visualmente en dispositivos las transiciones pendiente/activa/error/denegada, accesibilidad, bloqueo y apertura; guardar capturas sanitizadas. Si la implementación toca portales web, verificarlos en navegador según `frontend/DESIGN.md`; una prueba del teléfono no reemplaza esa revisión web.

Entregar una matriz con commit, comando/acción, resultado, evidencia y límites, separando: **compilación**, **HTTP**, **automatización**, **revisión visual** y **proveedor/dispositivo real**. Enumerar aparte aceptación FCM, recepción, apertura y confirmación. Android queda aceptado únicamente cuando se comprueba su recorrido nativo; dejar explícito cualquier paso bloqueado.

## 5. Verificación ejecutada durante esta auditoría

| Tipo | Resultado de esta sesión | Límite |
| --- | --- | --- |
| Compilación | Worker backend compilado con .NET 10.0.401, 0 errores. Dos warnings: NU1510 y EF1003 en código ajeno a push. Proyectos portables de las pruebas también compilados. | No se construyó APK en esta auditoría. |
| Automatización | `AvisosRepartoTests`: 11/11; `SesionTrabajoTests`: 7/7; filtro API de salida/registro/instalación: 10/10. Total: 28 pruebas existentes aprobadas. | Suites enfocadas; no adaptadores Firebase nativos. Un primer filtro por nombre de archivo no encontró pruebas y se reemplazó por el filtro real; no se cuenta como aprobado. |
| Reproducción de hallazgos | Probe local enlazó sin modificar `ControlNotificaciones.cs` y `SincronizacionConectividad.cs`, rama `ANDROID`, con stubs de almacenamiento, conectividad y servicios. Reprodujo estado pendiente después del ACK y ausencia de upload ante fallos de sync y de ACK. | Tres escenarios controlados de coordinación; sin SDK Firebase, HTTP ni SQLite reales. Harness temporal en `.local/push-audit-harness`, ignorado por Git; T0 prescribe trasladar los casos a regresiones portables mantenidas. |
| HTTP | 10 pruebas del cliente API con transporte HTTP controlado. | No se arrancó una API real ni se hicieron peticiones a un despliegue. |
| Backend integrado | No ejecutado. Docker no está disponible como comando en este entorno Windows y la fixture PostgreSQL nativa exige Linux. | Inspección del SQL y las pruebas existentes; ningún resultado histórico se atribuye a esta sesión. |
| Revision visual | No ejecutada durante la auditoria original: fue una entrega documental sin cambios de interfaz. | No acreditaba interaccion ni apariencia mobile/web. |
| Firebase/dispositivo | No se enviaron push reales. `adb devices -l` no mostró dispositivos. | IAM/secretos y entrega real del entorno elegido siguen sin verificar. |

La modificación versionada de esta auditoría es este documento. El objetivo de una ejecución posterior es corregir H01–H03, cerrar o descartar con evidencia el riesgo H04, y completar la guía de Android sin convertir pruebas controladas en una afirmación de entrega real.


## 6. Resultado de implementacion Android (2026-11-15)

Se implementaron T0-T4 para Android. iOS queda fuera de esta entrega.

- **H01:** el trabajo de conectividad ahora ejecuta el registro push en un flujo independiente, con un plazo propio de 12 segundos. Las fallas o el timeout de sincronizacion/recepciones/rutas no impiden intentar subir el FID durable.
- **H02:** el registro se movio a `Mobile.Application` con contratos para el FID, permisos y cliente de instalaciones. El estado solo pasa a activo despues del ACK HTTP. La pantalla recibe cambios de estado del callback asincrono; una respuesta de cuenta/FID/permiso obsoleta provoca un nuevo registro del estado actual.
- **H03:** el Worker conserva el codigo FCM y la categoria (`mensaje`, `configuracion`, `cuota`, `transitorio`, `desconocido`). Persistencia, log y metrica contienen categorias/codigos controlados, sin FID. `Unregistered` es el unico resultado que invalida una instalacion. La alerta existente de fallas push sigue detectando cada reintento.
- **Reintentos FCM:** una migracion hacia adelante conserva el backoff exponencial/jitter existente y da a `QuotaExceeded` un minimo de 60 segundos, con crecimiento hasta una hora. El caso de respuesta parcial valida el plazo persistido; los destinos aceptados siguen confirmados.
- **H04:** CI y el script de distribucion comparan paquete Android, Firebase project ID y numero de proyecto/app ID. Se requiere `NEXORUTA_FIREBASE_ANDROID_PROJECT_ID`, igual a `Push:ProjectId` del Worker. El Worker valida la clave de cifrado push al iniciar y exige el project ID al enviar.
- Se actualizaron los lockfiles Android de Api/Application: el restore bloqueado detecto referencias `Microsoft.Extensions.Logging.Abstractions` que ya estaban declaradas en los proyectos pero faltaban en los lockfiles.
- Se marco `NexoRuta.UnitTests` como proyecto de pruebas. Antes, `dotnet test` finalizaba correctamente sin ejecutar casos por faltar `IsTestProject`.

La guia operativa Android de la seccion 4 sigue siendo el procedimiento de aceptacion real, desde provision del proyecto y registro hasta primer plano, segundo plano, rotacion, reconexion, cierre y evidencia. La implementacion no sustituye esa aceptacion en Firebase y dispositivo.

### Verificación actual de esta implementación (2026-11-15)

| Capa | Resultado | Limite |
| --- | --- | --- |
| Compilación Android | Build Debug ARM64 con el archivo real de Firebase, target GcpDemo y EmbedAssembliesIntoApk=true: 0 errores. Se instalo y abrio en Galaxy S21, Android 14; la pantalla de acceso y la sección Cuenta cargaron. | 4 advertencias: XA0033 por la salida de Java 21 y tres XA0141 de bibliotecas Mapbox sin páginas de 16 KB. No es un APK de distribución Release. |
| Worker y pruebas | Build del Worker sin errores; pruebas focales repetidas: Mobile 33/33, clasificación del Worker 9/9, preflight Firebase Python 6/6. También se registraron las suites más amplias de la ejecución anterior: Mobile.Application 107/107, Worker 9/9 y GitHub/GCP 46 aprobadas + 1 omitida. | Advertencias NU1510 y EF1003 ajenas a push. No se ejecutó la prueba integrada PostgreSQL de migración/outbox. |
| CI Android | El workflow [Mobile CI 43731747303](https://github.com/NexoRuta/NexoRuta-Mobile/actions/runs/43731747303) compiló el APK Release de verificación. | El job falló después, al validar restore para `android-x64`: `NU1004` indica que `packages.lock.json` no refleja las referencias actuales de Mobile, Mobile.Api y Mobile.Application. Por el fallo se omitieron checksum y publicación del artefacto; no hay APK descargable de esa ejecución. |
| HTTP GCP | `/ready` dio HTTP 200 durante los intentos 43682929092 y 43729545386, antes de drenar el balanceador. | Ambos intentos fallaron luego en bootstrap; HTTP 200 no identifica el release ni demuestra que Worker se aplicara. |
| Registro Android | La cuenta administrativa indicada rechazó el acceso. Con autorización del usuario se inició sesión con la cuenta sintética `repartidor_demo`; la app mostró "Notificaciones activadas." y el API confirmó el registro. El FID no se incluyó en logs ni en este documento. | La cuenta de repartidor de prueba no tiene una hoja de ruta activa. |
| Firebase y entrega Android | Se enviaron dos mensajes de datos sintéticos desde FCM HTTP v1 al proyecto `nexoruta-mobile`: uno con la app en primer plano y otro con la app minimizada. FCM aceptó ambos y NotificationManager registró dos notificaciones en `nexoruta.avisos` con el título y cuerpo esperados; el usuario confirmó que aparecen en la barra de notificaciones de Android. | Los payloads usaron identificadores sintéticos; no se creó aviso de negocio. No se probó el toque, apertura y confirmación de un aviso real. La prueba directa no acredita que el Worker GCP desplegado use todavía el proyecto nuevo. |
| Revisión visual | No se cambió el layout. El usuario confirmó la visualización de las notificaciones en la barra de Android. | No se guardó una captura del sistema. |

### Configuración Firebase y GCP realizada

- Se obtuvo mediante Firebase CLI la configuracion Android de la app principal `uy.nexoruta.repartidor` del proyecto `nexoruta-mobile` y se guardó en `mobile/google-services.json`, ignorado por Git. La configuracion del APK y el package se validaron antes del build.
- Se actualizaron el secreto de configuracion Android y la variable de proyecto Firebase del repositorio Mobile y el environment `nexoruta-demo` del repositorio raiz para usar `nexoruta-mobile`.
- Se habilitó FCM en `nexoruta-mobile` y se concedió `roles/firebasecloudmessaging.admin` a la identidad runtime de `nexoruta-demo` en ese proyecto. El secreto `nexoruta-demo-integrations` recibió una nueva version con `firebase_project_id=nexoruta-mobile`; tambien se agregó una versión nueva del secreto de configuracion Firebase.
- Se retiró la app temporal `uy.nexoruta.repartidor.pushcheck` creada durante la preparacion. La app Android principal sigue registrada en `nexoruta-mobile`.
- Por decisión del usuario, se conserva íntegro el proyecto GCP `nexoruta-demo-20261022`, incluidas sus VMs y demas recursos. Solo se cambio el destino Firebase de Mobile.

### Estado del despliegue GCP y pendientes (2026-11-15)

- Los cambios de raiz, Backend y Mobile están publicados en `develop`: raiz `152f368`, Backend `f7d05e7`, Mobile `4dc2904`; el estado actualizado de este plan también está publicado en `develop`. Las acciones [43682929092](https://github.com/NexoRuta/NexoRuta/actions/runs/43682929092) y [43729545386](https://github.com/NexoRuta/NexoRuta/actions/runs/43729545386) publicaron correctamente los releases `release-a03dfa49040749b1b5b271742cd73594` y `release-b75f6e4f50ba4d70bbb142d9f3125ebe`, y sincronizaron `firebase_project_id=nexoruta-mobile`.
- Ambos intentos `operation=start` fallaron en el nodo A durante `vm_migrate_bootstrap_data`. Pasaron SQL preflight, migraciones de esquema, provisión de roles y catálogo departamental; no se llegó a la etapa `apply` de las imágenes. El error del proceso remoto quedó sanitizado como `CalledProcessError`.
- La causa de bootstrap quedó identificada con una consulta SQL de solo lectura: existe `admin@nexoruta.test` en `Usuarios`, pero no tiene fila en `AccesosPlataforma`. `EfPlataformaRepository.AsegurarConfiguradaAsync` detecta el correo ya ocupado y se niega a elevar esa identidad; `DatosInicialesSeeder` convierte el conflicto en fallo de inicialización. No se modificó la cuenta, su acceso ni sus credenciales. Para reintentar hay que decidir si se conserva esa identidad y se crea un administrador sintético distinto, o si se autoriza explícitamente cambiar el acceso de la existente.
- El workflow ejecutó la limpieza de fallo: cerró el lease y detuvo A y B. La consulta posterior a Compute reportó ambas instancias `TERMINATED`. El proyecto y la base GCP se conservaron.
- `/ready` respondió HTTP 200 durante el arranque, antes del drenaje del balanceador; no acredita que el release nuevo quedara aplicado. La etapa de aplicación de imágenes y health del Worker no se alcanzó, por lo que no se comprobó el `FIREBASE_PROJECT_ID` dentro de un Worker corriendo.
- Verificación portable repetida: Mobile 33/33 pruebas focales, validador Firebase 6/6, clasificación push del Worker 9/9 y build del Worker sin errores. Persisten advertencias NU1510 y EF1003 ajenas a push. La integración PostgreSQL/outbox no se ejecutó en este Windows sin Docker; no se usaron servicios del host como fixture.
- El repartidor sintético `repartidor_demo` no tiene una hoja de ruta activa. Por eso no se generó un aviso de negocio y siguen pendientes la apertura del aviso y su confirmación/ACK. Los dos mensajes FCM directos sí aparecieron en la barra de Android, según verificó el usuario.
- El APK instalado es Debug, firmado localmente; antes de uso real se necesita una compilación Release y que el usuario inicie sesión con su cuenta.

### Estado de los pasos de verificación del plan

| Paso | Estado | Evidencia / límite |
| --- | --- | --- |
| 1. Fuentes y efectos | Completo | SHAs de raíz/submódulos registrados; cambios publicados en `develop`; se conservaron proyecto, base y volúmenes GCP. No se usaron proveedores de mapas reales. |
| 2. Regresiones portables | Parcial | Pasaron los filtros Mobile 33/33, Python 6/6 y Worker 9/9. No se ejecutó cada combinación de carreras enumerada en la guía. |
| 3. API, SQL y Worker controlados | Parcial | Build Worker y clasificación unitaria pasaron. Fixture de integración PostgreSQL/outbox no se ejecutó en Windows sin Docker. |
| 4. Configuración Firebase efectiva | Parcial | JSON real validado; `nexoruta-mobile`, FCM API e IAM runtime verificados; secreto GCP apunta al proyecto correcto. Worker no llegó a correr el release nuevo y no se leyó su entorno efectivo. |
| 5. Artefacto nativo | Parcial | APK Debug ARM64 con configuración real instalada y abierta en Galaxy S21 Android 14; el CI también compiló el APK Release de verificación. No se produjo APK Release firmado ni SHA256: el job falló en la comprobación posterior de lockfiles y omitió la publicación del artefacto. |
| 6. Inscripción y permisos | Parcial | Sesión `repartidor_demo`, notificaciones activadas y alta confirmada por API. No se probaron permiso/canal denegado, primer arranque sin red o recuperación tras API caída. |
| 7. Evento real con app abierta | Pendiente | La cuenta sintética no tiene ruta activa; no se creó un aviso de negocio ni se correlacionó su outbox. |
| 8. Segundo plano y proceso ausente | Parcial | Llegó el push directo con la app minimizada y el usuario vio la notificación. No se probó proceso ausente, toque, apertura ni ACK de negocio. |
| 9. Rotación, reconexión y salida | Pendiente | No se rotó FID ni se probaron logout/revocación/cambio de cuenta en esta aceptación. |
| 10. Fallas controladas del proveedor | Parcial | Clasificación unitaria 9/9. Falta la matriz integrada de cuotas, respuesta parcial, carreras y persistencia con PostgreSQL. |
| 11. Revisión visual y evidencia | Parcial | El usuario confirmó las notificaciones en la barra; no se guardó captura y no se revisaron visualmente estados de error/denegación ni accesibilidad. |

El ADB del teléfono está actualmente `offline`; el último puerto/código de emparejamiento proporcionado ya no conectó. Se conserva la evidencia de las dos entregas anteriores, pero hacen falta datos ADB vigentes para repetir las pruebas de los pasos 6–9.
