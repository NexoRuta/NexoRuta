# Sesión web: respuesta 401 demorada y recuperación

Corte del 03/11/2026. Base publicada y gitlinks comprobados nuevamente tras recuperar el workspace:

| Repositorio | SHA de base |
| --- | --- |
| Principal | `c97f6c21a4610f5eea835847db883dcb410b598f` |
| Backend | `adcba4189c70b32ec78d3a9d8dce132387c02eb0` |
| Frontend | `c0f40c1bc032e6da1988098ab4c36e4869228a61` |
| Mobile | `74a25f1b5b18c7dfc006cf7df747d73b0ec4910a` |

La base CU-10/CU-12/14/15/16 sigue pendiente de revisión humana. Este corte no acepta esos CU, no cierra CU-06 ni valida la prueba manual Mobile del 02/11. Solo se usan bases nuevas de fixtures, usuarios y organizaciones sintéticos. No se consultó ni modificó el envío excluido ni su ruta manual.

## Causa demostrada y límite del diagnóstico

**Un rechazo antiguo podía invalidar un ingreso posterior válido.** Un request A usa la cookie anterior; su JWT recibe 401 legítimo después de revocar la versión del acceso. El portal respondía borrando la cookie (`Set-Cookie` con valor vacío) y redirigiendo al ingreso. Si B completa un nuevo ingreso antes de que llegue A, la respuesta A borra la cookie nueva del mismo nombre. Además, el GET de ingreso con `expirada=true` volvía a ejecutar SignOut. El navegador no distingue la generación de cookie que motivó cada respuesta.

La prueba reproduce ese orden con Chromium, dos pestañas, portales reales, API Kestrel y PostgreSQL/PostGIS real con rol restringido. El proxy local de prueba retiene la respuesta de A **después de recibir el rechazo real**; no inventa un 401 ni sustituye autenticación por mocks. B obtiene otro JWT mediante login real y recién entonces se libera A.

Esto demuestra un defecto de invalidación/recuperación, **no la causa del 401 histórico al arrancar**. No se consiguió atribuir ese incidente histórico a reloj, TLS, infraestructura, claves, permisos o renovación. Sigue sin determinar. No se modifican vencimientos, permisos ni validaciones para ocultarlo.

## Circuito auditado

- Backoffice y Commerce: POST con antiforgery al portal → `/api/auth/login` → `/api/usuarios/actual` → cookie cifrada HttpOnly que contiene el JWT. La fecha de la cookie es exactamente `expiresAtUtc`; `AllowRefresh=false`, `SlidingExpiration=false`. No existe renovación automática web. El JWT central dura 15 minutos; validación de emisor/audiencia/firma/vida y tolerancia de 30 segundos se conservan.
- Cada operación envía el JWT desde el servidor; permisos vigentes y RLS siguen verificándose en API/transacción. No se agregan permisos a la cookie ni se usa su marcador como autorización.
- Las claves Data Protection deben persistirse y compartirse según el despliegue. La prueba usa los keyrings PostgreSQL existentes y un certificado efímero propio; comprueba reinicio de cada portal y de API con la misma sesión.
- Mobile usa el contrato separado de [sesiones renovables](../../../backend/docs/workflow/sesiones-moviles.md): rotación y detección de reutilización, vencimiento absoluto de 30 días. No se cambia ese protocolo ni el cliente móvil.

## Corrección

1. Ninguna reacción a un 401 de API borra automáticamente la cookie web. Un token revocado continúa siendo rechazado por el servidor y muestra el ingreso. El cierre explícito sigue siendo POST con antiforgery; se conserva el cierre intencional posterior a crear organización.
2. Cada ingreso web crea un GUID aleatorio de correlación en la cookie cifrada (`nexoruta:web_signin_id`). El rechazo lleva solamente ese marcador no autorizante (`rechazo`) y un destino local. No es JWT, cookie, refresh token, ID de usuario ni una credencial. No permite ingresar ni elegir operador/comercio.
3. Si el GET de recuperación encuentra un marcador **diferente** en la cookie actual, consulta una sola vez el usuario actual de esa cookie. Si sigue válido, vuelve al destino y sus políticas normales. Si coincide, falta, fue cerrado, está vencido o es inválido, presenta el formulario sin redirección automática. Esto limita el recorrido aunque whoami y permisos discrepen. Un fallo temporal de API conserva la cookie y ofrece reintento explícito.
4. `ReturnUrl` conserva únicamente la ruta local: se descartan query y fragmento, rutas externas, rutas de autenticación y dot segments. No se guardan formularios, credenciales ni filtros sensibles en URLs ni en almacenamiento local. El destino atraviesa de nuevo autorización al volver.
5. 403 conserva su acceso denegado. 503, errores de transporte y timeout se comunican como indisponibilidad, sin cerrar sesión. Login 200 seguido de whoami 401 informa fallo de validación de la sesión recién iniciada; no acusa contraseña incorrecta.
6. No se reenvían POST/PUT/DELETE, recepciones, despachos, entregas ni eventos. La recuperación automática hace solo un GET y navegación; el usuario debe decidir sobre cualquier operación anterior de resultado incierto.

## Observabilidad mínima

`AuthDiagnostics` emite eventos `AuthenticationDecision` (40101/40301) con estado, motivo estable, hora UTC del servidor, método, plantilla de endpoint y GUID `AuthTrace`. El header `X-NexoRuta-Auth-Trace` permite unirlo con el fallo de ingreso/recuperación del portal. ApiClient solo acepta un GUID de 32 hexadecimales, no texto arbitrario del header.

Motivos comprobables: `missing_bearer`, `invalid_token`, `token_expired`, `token_not_yet_valid`, `invalid_issuer`, `invalid_audience`, firma inválida/clave no encontrada, `access_context_changed`, `login_rejected` y `permission_denied`. Se preservan los mensajes y validaciones HTTP existentes. No se registran token, cookie, refresh, contraseña, email, claims, query, body, excepciones con credenciales ni identificadores de organización. La prueba captura los campos estructurados permitidos, no mensajes completos de terceros.

Para investigar otro incidente: anotar hora UTC, portal, ruta sin query, estado y AuthTrace; correlacionar con los motivos anteriores y readiness/reinicio de servicios. Un 401 sin sesión o con token vencido no acredita por sí solo una falla del sistema.

## Recuperación del workspace

Se rescató el checkout original y se conservaron las ramas locales. Antes de editar se guardaron patches binarios contra HEAD y copias de los 29 archivos fuente modificados/nuevos, con manifest de ramas/SHA/hashes. Se verificó que los patches aplican a las bases registradas mediante índices alternativos. Respaldo local privado: `/workspace/nexoruta-rescue-session401-20261103T123127Z`. No se respaldaron secretos, certificados, logs, bases, bin/obj ni node_modules. La edición pendiente que agregaba el límite por generación de ingreso no había llegado a ejecutarse; se implementó sobre los archivos efectivamente recuperados. No se sustituyó el checkout.

## Verificación y reproducción

Los resultados y comandos se registran a continuación. Los informes completos, capturas y certificados del harness son locales privados, no contenido a publicar. Gentle-AI/Engram y revisión nativa no están expuestos entre las herramientas disponibles; se continuó con inspección y verificaciones ejecutables. No se afirma haber realizado esa revisión opcional.

### Evidencia comprobada

- Backend: 24/24 pruebas existentes de sesiones Mobile y RLS pasaron; la nueva prueba `AuthDiagnosticsHttpTests` pasó después de ajustar la captura de log del harness al logger usado por la aplicación (Serilog no reenvía a los providers de Microsoft por defecto). Solo se sustituye el destino de log en la fixture; autenticación y API son reales.
- Frontend: 244 pasadas, 0 fallidas, 5 omitidas optativas de navegador de otros circuitos. Incluye cookies por portal, login/logout/antiforgery, permisos, respuestas 401/403/404/transporte/timeout, vencimiento nativo de cookie con reloj controlado, rutas seguras y finalización de recuperación incluso si whoami y permisos discrepan o se manipula el marcador de correlación. Las fixtures de páginas usan API controlada y complementan la integración real; no la sustituyen.
- Tres fallos ajenos fueron reproducidos **sin modificar el frontend de base** (`git archive c0f40c1`): dos casos de `FailedFleetHistoryAndRoadQueriesStayExplicitInsteadOfPretendingEmptyData` buscan el texto anterior `GET /api/reparto/flota`; `DepotDefersPhysicalReceiptToExplicitShipmentContext` espera `handler=Recibir` del circuito previo. Se conservan, no se modifican ni omiten silenciosamente. La selección de 244 pruebas excluye explícitamente esos tres casos. No se afirma que toda la suite de frontend esté verde.
- Prueba roja real de ambos portales sobre las DLL construidas del archivo de la base: **1 fallo esperado por portal**, tras demostrar que el nuevo login había terminado antes de liberar el rechazo antiguo. Backoffice: rechazo retenido a las `12:37:55.491Z`, nuevo ingreso `12:37:55.829Z`, resultado `/ingresar` `12:37:55.899Z`. Commerce: `12:38:18.561Z` → `12:38:18.945Z` → `/ingresar` `12:38:19.012Z`. En ambos, la respuesta vieja incluía borrado de cookie.
- Primera integración verde completa: ambos portales conservaron el nuevo ingreso y el destino. Backoffice: `12:40:17.663Z` → `12:40:17.995Z` → `/deposito/recepcion` `12:40:18.190Z`; Commerce: `12:40:24.366Z` → `12:40:24.698Z` → `/usuarios` `12:40:24.932Z`. Ninguna respuesta vieja borró cookies. Pasaron además 12 GET simultáneos por portal, cambios reales de permisos, 503 controlado, conexión rechazada al detener API, reinicio API/portal y keyring persistido, sesión revocada sin bucle, fallo de validación después de login, logout con antiforgery y formulario a 320px/escritorio con teclado. Sin errores JavaScript en esta ejecución.

Las fechas anteriores son UTC del 03/11/2026. El proxy demora una respuesta real; no se usa un `401` simulado como acreditación del defecto. No se esperaron 15 minutos en navegador: la expiración se acredita con JWT realmente vencido contra API y reloj controlado del handler nativo de cookie en las pruebas de páginas. Producción HTTPS/TLS y dispositivos Mobile no se ensayaron; no se alteraron sus configuraciones.

### Ejecución final HTTP

`JwtRbacHttpTests`, `AuthDiagnosticsHttpTests`, `SesionesMovilesHttpTests` y `RlsRestrictedHttpFlowTests`: **63 pasadas, 0 fallidas, 0 omitidas**, duración 1m38s. Incluye firmas/emisor/audiencia/identidad/vida inválidos, revocación de acceso/credencial, políticas con grants vigentes, rechazo de headers antiguos, listado/alta aislado por comercio/operador, tracking público sin cambios, rotación móvil con JWT vencido, renovación simultánea sin dos sucesores, reutilización que revoca la familia, logout idempotente/aislado y migración/rollback existentes. RLS se ejecuta con rol sin superuser/BYPASSRLS y comprueba dos operadores y dos comercios reales.

### Repetir desde un checkout integrado

Usar las ramas de este corte y sus gitlinks, SDK 10.0.401, Docker/PostGIS y Playwright/Chromium versionados en `scripts/cloud/package-lock.json`. Primero leer `AGENTS.md` y la continuidad Cloud. No ejecutar el instalador para restaurar los SHA antiguos de su manifiesto. No hace falta arrancar el runtime habitual: las fixtures crean sus propios servicios y datos. No ejecutar HTTP y navegador en paralelo ni recompilar los portales durante el navegador.

```bash
source scripts/cloud/env-agent.sh
export DOTNET_CLI_HOME=/workspace
export NUGET_PACKAGES=/workspace/.cache/nuget-packages
export NUGET_HTTP_CACHE_PATH=/workspace/.cache/nuget-http
export PLAYWRIGHT_BROWSERS_PATH=/workspace/.cache/ms-playwright
export NEXORUTA_PLAYWRIGHT_MODULE="$PWD/scripts/cloud/node_modules/playwright"
# En un entorno nuevo: restore --locked-mode de los proyectos y npm ci --prefix scripts/cloud.
dotnet test frontend/tests/NexoRuta.ApiClient.Tests --filter '(FullyQualifiedName~RutaSesionTests|FullyQualifiedName~SesionUsuarioTests|FullyQualifiedName~BackofficeSessionAndPagesTests|FullyQualifiedName~AdminSessionAndPagesTests)&FullyQualifiedName!~FailedFleetHistoryAndRoadQueriesStayExplicitInsteadOfPretendingEmptyData&FullyQualifiedName!~DepotDefersPhysicalReceiptToExplicitShipmentContext'
dotnet test frontend/tests/NexoRuta.ApiClient.Tests --no-build --filter 'FullyQualifiedName~SeguimientoPagesTests|FullyQualifiedName~ImportacionEnviosComponentTests|FullyQualifiedName~RutaSesionTests|FullyQualifiedName~RejectedSameSignIn|FullyQualifiedName~CookieExpiry|FullyQualifiedName~RecoveryNever|FullyQualifiedName~LoginUsesIsolatedProtectedCookies'
dotnet test backend/tests/NexoRuta.IntegrationTests --filter 'FullyQualifiedName~JwtRbacHttpTests|FullyQualifiedName~AuthDiagnosticsHttpTests|FullyQualifiedName~SesionesMovilesHttpTests|FullyQualifiedName~RlsRestrictedHttpFlowTests'
umask 077
export NEXORUTA_SESSION_E2E_DIR="$(mktemp -d /tmp/nexoruta-session401-XXXXXX)"
dotnet test backend/tests/NexoRuta.IntegrationTests --no-build --filter FullyQualifiedName~SesionWebBrowserTests
```

El test frontend construye ambos portales. El harness de navegador requiere esas DLL Debug, carga la API real desde el proyecto backend y ejecuta `frontend/tests/browser/sesion-401.cjs`. El limitador de login permanece en 5/minuto: se reinicia únicamente la API **sintética en memoria de la fixture** entre grupos para no confundir 429 esperados con 401. No se modifica ningún límite de producto.

Para obtener la prueba roja sin tocar el checkout de trabajo:

```bash
# Dentro del checkout raíz; carpeta nueva fuera del repo.
baseline_dir="$(mktemp -d /tmp/nexoruta-baseline401-XXXXXX)"
mkdir "$baseline_dir/frontend"
git -C frontend fetch --no-tags origin c0f40c1bc032e6da1988098ab4c36e4869228a61
git -C frontend archive c0f40c1bc032e6da1988098ab4c36e4869228a61 | tar -x -C "$baseline_dir/frontend"
dotnet build "$baseline_dir/frontend/src/NexoRuta.Backoffice" -p:RestoreLockedMode=true -p:OfficialDepartmentSource="$PWD/backend/src/ZonasCobertura/Data/departamentos-uruguay.geojson"
dotnet build "$baseline_dir/frontend/src/NexoRuta.Commerce" -p:RestoreLockedMode=true
export NEXORUTA_SESSION_PORTAL_ROOT="$baseline_dir/frontend"
export NEXORUTA_SESSION_RACE_ONLY=1
for portal in backoffice commerce; do
  export NEXORUTA_SESSION_ONLY="$portal"
  export NEXORUTA_SESSION_E2E_DIR="$(mktemp -d /tmp/nexoruta-session401-red-XXXXXX)"
  dotnet test backend/tests/NexoRuta.IntegrationTests --no-build --filter FullyQualifiedName~SesionWebBrowserTests
  # Esperado: fallo "A delayed 401 erased the newer sign-in cookie" en cada portal.
done
unset NEXORUTA_SESSION_PORTAL_ROOT NEXORUTA_SESSION_RACE_ONLY NEXORUTA_SESSION_ONLY
```

Los errores de build de una carpeta aislada sin el GeoJSON canónico no son fallos de autenticación: pasar `OfficialDepartmentSource` como arriba. No copiar claves/certificados/credenciales del entorno habitual.

### Recorrido manual breve

1. Ingresar en Backoffice/Commerce con una cuenta sintética autorizada. Abrir una pantalla permitida mediante su URL directa; después de un ingreso explícito debe volver a esa ruta, sin transportar queries ni formularios.
2. Con el harness, retener la respuesta antigua tras revocar solo su acceso, ingresar de nuevo desde la otra pestaña y liberar la respuesta. Las dos pestañas deben conservar la nueva sesión y su destino. El harness realiza la sincronización; no es reproducible de forma fiable solo haciendo clic rápido.
3. Revocar la sesión actual sin nuevo ingreso: aparece el formulario con mensaje de sesión inválida y no hay bucle. Un error temporal de API debe ofrecer reintento, conservar cookie y recuperar al volver el servicio. Una denegación de permiso debe seguir siendo acceso denegado.
4. Verificar salida explícita, ausencia de autorización posterior, y formulario/mensajes con teclado a 320px y escritorio. No usar los datos ni la ruta manual Mobile del 02/11.

La inspección del formulario detectó además `label-content-name-mismatch` en los enlaces de marca de ingreso de ambos portales: el nombre accesible redundante no coincidía con el texto visible que obtiene el navegador. Se quitó únicamente el aria-label redundante de los layouts de ingreso: el nombre ahora proviene del texto visible; no cambió su aspecto. El hallazgo se aisló con el marcado original y axe, y se comprobó en el navegador real.

Mobile Core: **36 pasadas, 0 fallidas**. Es regresión de lógica portátil; no acredita Android, hardware, prueba manual ni diagnóstico del 401 histórico.

Los enlaces de expiración ya existentes en componentes Commerce también conservan ahora solo la ruta actual mediante `RutaSesion`. Cuando un componente no adjunta generación de ingreso, el formulario requiere ingreso explícito; nunca elimina una cookie posterior ni reproduce el formulario/operación que falló. La cancelación con 401 se verifica con un único POST y el destino seguro `/envios`.

### Verificación final de componentes y navegador

Tras conservar el destino en los enlaces Blazor: **65/65 pruebas dirigidas** de `SeguimientoPagesTests`, `ImportacionEnviosComponentTests`, rutas seguras y recuperación web. Se mantuvo la expectativa concreta de un solo POST de cancelación ante 401, ahora con retorno a `/envios`. Se ajustaron únicamente las expectativas de navegación que antes descartaban esa ruta.

Después de quitar los nombres accesibles redundantes de los enlaces de marca: **integración real 1/1**, ambos portales, 23 comprobaciones de recorrido, **0 errores JavaScript**, **0 violaciones axe en el ingreso a 320px**. Incluye un 401 retenido que llega después de logout sin restaurar ninguna sesión, destino de una ruta Blazor protegida, mensajes de expiración, foco de teclado y ausencia de desborde. Se inspeccionaron visualmente capturas de mensajes de ambos portales a 320px y el ingreso en escritorio (1280×900), conservando el diseño existente. El escáner no equivale a certificar WCAG ni reemplaza la revisión manual.

No se agregaron migraciones ni se modificaron tokens, vida de sesión, TLS, antiforgery, RLS, tarifas, etiquetas, datos declarados, idempotencia, versiones, offline ni configuración Mapbox `permanent=false`. El reinicio de la prueba ejercita persistencia de keyrings y conectividad; no acredita un despliegue productivo ni resuelve el incidente histórico.


Última ejecución sobre los archivos a publicar: **1/1 integración, 23 comprobaciones en ambos portales, 0 errores JavaScript y axe sin violaciones**. Incluye también ampliación CSS al 200%, sin desborde y con foco usable. No se presenta esa emulación CSS como zoom nativo de todos los navegadores.

## Ramas de este corte y orden de revisión

Todos los commits propios se publican únicamente en `fix/sesion-401-intermitente`:

| Repositorio | SHA del corte |
| --- | --- |
| [Backend](https://github.com/NexoRuta/NexoRuta-Backend/tree/fix/sesion-401-intermitente) | `9a35b8b292e74a98a55f3e22eab8097bd0d7eb9a` |
| [Frontend](https://github.com/NexoRuta/NexoRuta-Frontend/tree/fix/sesion-401-intermitente) | `d470cfd999faccc90fcfcc99672e50531716c29e` |
| Mobile (gitlink conservado, sin rama nueva ni cambios) | `74a25f1b5b18c7dfc006cf7df747d73b0ec4910a` |

El principal actualiza solo estos gitlinks y documentación. Revisar primero la base pendiente CU-10 y sus anteriores; después Backend (diagnóstico/harness), Frontend (corrección/recuperación), y finalmente los gitlinks/documentación del principal. No se ejecutaron merges ni se crearon PR. No se modifica ninguna rama ajena.


## Comprobación de publicación desde cero

El 03/11/2026 se clonó **desde GitHub**, sin referencias ni alternates al workspace original:

```bash
git clone --depth 1 --branch fix/sesion-401-intermitente --recurse-submodules --shallow-submodules https://github.com/NexoRuta/NexoRuta.git /workspace/nexoruta-session401-clean-20261103T1300
```

El principal publicado `3a801c3cb88de91115a5970f8c196a2e009c1650` obtuvo Backend `9a35b8b292e74a98a55f3e22eab8097bd0d7eb9a`, Frontend `d470cfd999faccc90fcfcc99672e50531716c29e` y Mobile `74a25f1b5b18c7dfc006cf7df747d73b0ec4910a` por fetch de sus respectivos remotos. Se compararon SHA y estados limpios de los cuatro repositorios. No se copió ningún submódulo local. El commit posterior de esta constancia cambia solo este documento y mantiene los mismos tres gitlinks.

Para revisión local basta clonar la rama con submódulos como arriba (usar otra carpeta destino), leer este informe y ejecutar los comandos dirigidos. El entorno original y el respaldo recuperable permanecen conservados. Los tres repositorios modificados tienen upstream en la rama propia; Mobile sigue intacto.

Actualización posterior, 03/11/2026: los tres fallos preexistentes de Flota/Depósito fueron auditados y corregidos como expectativas desactualizadas, sin modificar producto. La suite completa pasó con 476 aprobadas, 0 fallidas y las mismas 5 optativas omitidas. Ver [diagnóstico individual y evidencia](../regresion-flota-deposito/01-diagnostico-y-verificacion.md). Esta actualización no cambia el diagnóstico pendiente del 401 histórico ni cierra otros CU.
