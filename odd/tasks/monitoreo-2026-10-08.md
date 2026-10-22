# Monitoreo NexoRuta 08/10/2026

## Catálogo global y coherencia del código — 08/10/2026

Se publica `GET /api/operadores` para el catálogo compartido por todos los comercios; la ruta anterior devuelve 404. Cliente HTTP, contrato OpenAPI, pruebas y documentación usan la ruta nueva. La autorización sigue admitiendo las cuentas del comercio.

La revisión de los flujos implementados corrigió el mensaje que exigía pertenecer a operador y comercio a la vez, la excepción de operador inexistente, textos y nombres que confundían empresas con cuentas, el ejemplo HTTP de plantilla que devolvía 404 y el desacople entre Development de las webs (antes API 5000) y el perfil local del backend (5041). Las webs en Development usan 5041; Compose inyecta `http://api:8080/` y mantiene sus URLs y PostgreSQL 5432. Arquitectura distingue ahora estado vigente y evidencia histórica, y sus módulos coinciden con el Excel rector.

Pasaron 60 pruebas: 8 unitarias, 22 de integración y 30 del frontend contra copia y API actual. Las soluciones compilan; las tres advertencias EF Core de Worker son preexistentes. Una API y una base temporales comprobaron que dos comercios sin envíos ven el mismo catálogo, crean con un operador nuevo y consultan solo sus envíos; un empleado no propietario pudo crear y el servidor resolvió comercio/usuario desde su cuenta incluso con otros IDs en el JSON. Chrome confirmó login, selector, alta y el mismo ID/bulto/comercio en Backoffice con Development apuntando a la API 5041.

La API y las webs de Compose se reconstruyeron, responden HTTP 200 y OpenAPI coincide con el contrato del frontend. Los nueve servicios continúan activos. No se agregaron funcionalidades ni se migró/borró la base persistente. Los datos de interfaz se guardaron en una base temporal de revisión. MAUI en dispositivos, CI y despliegue remoto no se ejecutaron.

## Separación de repositorios de cuentas y empresas — 08/10/2026

`IAccesosUsuarioRepository` conserva la consulta de cuentas y pertenencias. Las consultas generales de operadores pasan a `IOperadoresRepository`/`EfOperadoresRepository`; el controlador de operadores disponibles y el alta de envíos consumen ese contrato. Se agrega `IComerciosRepository`/`EfComerciosRepository` con consultas de lista ordenada y por ID, registrado por scope y probado con PostgreSQL. Las empresas se consultan independientemente de sus usuarios y envíos. El login sigue mostrando cuentas con su organización en una sola consulta.

Antes del cambio pasaron 57 pruebas. Después pasaron 59: 8 unitarias, 22 de integración y 29 del frontend contra OpenAPI actual. Los nuevos escenarios comprueban empresas sin usuarios ni envíos, DI, orden, consulta por ID, inexistencia y cancelación. La compilación del backend pasó con las tres advertencias EF Core preexistentes de Worker. Se reconstruyó la API local y se verificaron cuentas, selector, filtros y estados HTTP 200/401/403/400, sin duplicar la consulta del acceso.

OpenAPI coincide con el contrato del frontend; los nueve servicios están activos y PostgreSQL sigue en 5432. Este cambio agrega los repositorios internos y actualiza sus consumidores, sin nuevas pantallas, endpoints, migraciones ni consulta de comercios atendidos por operador. La CI remota no se ejecutó.

## Consulta única por petición y cancelación de Blazor — 08/10/2026

Se reutiliza en `HttpContext.Items` el `ContextoUsuario` validado por `AccesoSeleccionadoHandler`; `UsuarioActualHttp` comprueba que corresponda al principal y lo devuelve sin otra consulta. Cada petición nueva vuelve a consultar y validar su cuenta. La prueba previa reprodujo tres consultas al autenticar y leer dos veces el contexto; con el cambio se hace una. La API desplegada también confirmó una sola consulta para `GET /api/usuarios/actual`.

El componente `Home` de Commerce pasa su token a la obtención del usuario, la lista de operadores y el alta. `Dispose` cancela y libera el token source; la cancelación al salir del componente no muestra un error. No se agregan endpoints ni cambian los contratos HTTP.

Pasaron 57 pruebas: 8 unitarias y 20 de integración del backend, y 29 del frontend. Las regresiones comprueban una consulta por petición, separación de usuarios y peticiones, rechazo de acceso inválido y contexto incompatible con el principal, y cancelación del acceso actual y de las llamadas HTTP del cliente. Chrome navegó fuera del formulario durante una consulta y un alta pendientes; un proxy temporal registró la cancelación de ambos HTTP y la navegación continuó sin error del circuito. El proxy retuvo el POST antes de enviarlo a la API, por lo que no se creó un envío de prueba.

API y Commerce locales se reconstruyeron; las cuentas y respuestas 200/401/403 siguen correctas, las aplicaciones responden HTTP 200 y los nueve servicios continúan activos. PostgreSQL mantiene 5432. Cancelar una petición no revierte un envío ya confirmado. La CI remota no se ejecutó.

## Arranque Compose con el puerto original — 08/10/2026

Se reprodujo el conflicto de `5432`, ocupado por PostgreSQL 16 instalado mediante Snap. Por instrucción del usuario se detuvo esa instancia con cierre ordenado y se mantuvo `5432:5432` en Compose. La configuración de Development, las pruebas y la documentación conservan el puerto original; se revirtió el cambio provisional a 5433.

La reconstrucción también mostró que `frontend/Dockerfile` rechazaba `NexoRuta.Tracking`; se agregó a la lista de los tres proyectos permitidos. `docker compose up -d --build` completó correctamente. Los nueve servicios están activos, con API/PostgreSQL/Redis/RabbitMQ saludables. API, OpenAPI, Backoffice, Commerce, Tracking, Dashboard y RabbitMQ Management respondieron HTTP 200. Las 13 pruebas de integración del backend pasaron usando la conexión por defecto en 5432, con una base temporal por escenario. La migración `ShipmentCommerce` está aplicada en la base de Compose. No se borraron volúmenes ni datos.

## Eliminación del vínculo operador–comercio — 08/10/2026

Por solicitud del equipo se elimina `OperadorComercio` del modelo vigente. Cada envío conserva `OperadorId` y `ComercioId` directamente; el comercio elige cualquier operador registrado sin un vínculo previo. Se mantienen el ingreso por tipo de cuenta, el alta individual con bulto y la consulta de envíos filtrada por comercio/operador. El listado de comercios atendidos por un operador queda fuera de este cambio.

`ShipmentCommerce` obtiene el comercio de los vínculos anteriores antes de eliminar la tabla. Su reversión reconstruye los pares que tienen envíos, con nuevos IDs de vínculo; no restaura vínculos sin envíos. Se actualizaron DTOs, OpenAPI, selector y Backoffice. Las migraciones históricas se conservan para actualizar bases existentes.

Verificación local con SDK .NET 10.0.401 y PostgreSQL 18 temporal: 8 pruebas unitarias y 13 de integración del backend, y 26 del frontend contra OpenAPI actual y su copia. La integración comprueba migración, reversión, reaplicación y conservación de cuentas, envíos y bultos, incluidos varios envíos del mismo par operador/comercio. EF Core no detecta cambios de modelo pendientes. Ambas soluciones compilan; frontend sin advertencias y backend con tres advertencias MSB3277 de versiones EF Core en Worker, reproducidas también al compilar el commit anterior sin los cambios.

La API confirmó 401/403 según cuenta, 400 para operador ausente/vacío/inexistente y 201 para un alta válida; comercio y usuario creador se resuelven desde la cuenta aunque el cliente envíe otros IDs. Chrome creó el envío `01a11dce-3e41-7e41-bd97-0c6bdb8b2f60` desde el portal eligiendo un operador nuevo sin vínculo previo; Backoffice mostró el mismo ID, comercio y bulto, y mantuvo el filtro por operador.

Solo se migraron bases temporales de validación; no se modificó la base persistente de Compose. Backend y frontend deben actualizarse juntos por el reemplazo de `operadorComercioId` por `comercioId`. La CI remota no se ejecutó. Los apartados siguientes conservan evidencia histórica; el comportamiento vigente está en [CU-01](../../backend/docs/cu/CU-01-comercios-usuarios.md) y [CU-07](../../backend/docs/cu/CU-07-alta-envios.md).

## Cuentas propias y operador por envío — 08/10/2026

Se revisó `docs/alcance/Laboratorio__NET_2026.pdf`: §3.3, página 2, permite que un comercio trabaje con más de un operador; §5.1 define comercios clientes y sus usuarios. Se conserva `OperadorComercio` como relación comercial, y se separa de la pertenencia de las cuentas. La cuenta del dueño pertenece al comercio; la cuenta del operador pertenece al operador. El ingreso selecciona una cuenta y el formulario del envío elige el operador disponible; la API valida la relación antes de guardar. No se implementaron CRUD ni perfiles laborales nuevos.

La migración conservó los IDs de usuarios/cuentas y los envíos anteriores. Pasaron 8 pruebas unitarias y 7 de integración PostgreSQL del backend y 26 del frontend, contra OpenAPI actual y su copia. Chrome confirmó cuentas separadas, rechazos cruzados, elección obligatoria del operador, sesiones independientes y el envío `01a11cc7-b482-7700-9b9b-e25615daab04` con su bulto en Backoffice. La integración también comprobó dos operadores elegibles para la misma cuenta del comercio y la migración/reversión conservando datos.

La implementación vigente se describe en [CU-01](../../backend/docs/cu/CU-01-comercios-usuarios.md) y [CU-07](../../backend/docs/cu/CU-07-alta-envios.md). La selección sigue sin credenciales para el primer monitoreo; la CI remota no se ejecutó. Los apartados inferiores conservan evidencia histórica.

## Selección de usuario y revisión de actores — 08/10/2026

El alcance sigue limitado a CU-01, CU-07 y CU-08 del Excel. Commerce y Backoffice presentan un dropdown leído desde PostgreSQL, con accesos de comercio e internos del operador respectivamente. La selección usa el ID del vínculo, cookies independientes y la declaración de ámbito `nexoruta:tipo_acceso`; no representa un perfil laboral. Se agregaron el usuario interno inicial y una migración que admite acceso al operador sin comercio, conservando los datos anteriores.

La revisión de la letra distingue tenant, comercio, usuario y datos del destinatario. `OperadorComercio` y los accesos permiten que un mismo comercio y usuario trabajen con dos operadores sin duplicar su identidad. No se implementaron perfiles de administrador/despachador/repartidor/depósito, CRUD, RLS ni otros CU. El detalle vigente está en [CU-01](../../backend/docs/cu/CU-01-comercios-usuarios.md).

Pasaron 6 pruebas unitarias, 8 de integración PostgreSQL y 23 de frontend, incluidos contratos contra OpenAPI actual. Chrome comprobó entrada por ámbito, selección manual incompatible rechazada, sesiones independientes, antiforgery y cambio de usuario. El envío `01a11c7a-7cbc-7d1c-ba7f-99699a89c07e` se creó con el usuario del comercio y apareció con su bulto en Backoffice con el usuario del operador. La selección no verifica identidad por credenciales y se limita al monitoreo. La CI remota de estos cambios no se ejecutó; las revisiones inferiores son históricas.

## Revisión del acceso inicial — 08/10/2026

El recorte del Excel se implementa como los primeros casos de uso del proyecto. `IUsuarioActual` resuelve la identidad y sus vínculos persistidos mediante el adaptador de acceso directo; el repositorio de envíos ya no conoce el seeder ni selecciona un usuario por un correo hardcodeado. Los nombres configurados se usan solo para inicializar datos. `DatosInicialesSeeder` reutiliza los IDs anteriores, completa vínculos faltantes y evita duplicados; el portal y Backoffice consultan `GET /api/usuarios/actual`.

Se documentaron [CU-01](../../backend/docs/cu/CU-01-comercios-usuarios.md), [CU-07](../../backend/docs/cu/CU-07-alta-envios.md) y [CU-08](../../backend/docs/cu/CU-08-bultos.md). Pasaron 4 pruebas unitarias, 5 de integración PostgreSQL y 17 de frontend. Se comprobó con Chrome el envío `01a11c48-1859-79d1-96dd-3b77741d6421`, creado desde el formulario real y consultado en Backoffice con su bulto y propietarios. Los IDs iniciales se conservaron al actualizar el entorno. También se probó la API en modo Production con otra configuración de acceso y las respuestas 503 al retirar el vínculo en una base temporal.

El acceso sigue siendo directo y con un único vínculo por usuario; no se agregaron login, CRUD, perfiles ni RLS. La CI remota de estos cambios no se ejecutó. Los apartados siguientes conservan la evidencia e instrucciones de la implementación anterior.

## Objetivo

Demostrar en el entorno local Compose el alta individual de un envío en el portal, su persistencia en PostgreSQL con operador/comercio/usuario de prueba y bulto, su consulta en Backoffice y una ejecución local de CI.

## Alcance y restricciones

- Fuentes rectoras: `docs/alcance/Monitoreo_2026-10-08_CU.xlsx`, `docs/alcance/Laboratorio__NET_2026.pdf`, `docs/alcance/Entregas/Entrega-10-4-2026-Grupo-4.pdf`, `architecture.md` y `backend/docs/workflow/arquitectura-backend.md`.
- Implementar CU-01 solo como relaciones/datos de demo; CU-07 solo alta individual; CU-08 un bulto o más; T-01 entorno Compose con base, caché, cola y observabilidad; T-02 lectura en Backoffice del mismo envío; T-03 pipeline CI localmente verificable.
- No adelantar autenticación, perfiles completos, RLS/dos operadores, tarifas CU-09, máquina de estados completa, cache funcional, cola funcional, móvil, despliegue remoto ni otros hitos.
- Mantener README, `architecture.md` y `docs/` existentes. No commit ni push; todo cambio de código queda en ramas `feature/monitoreo-2026-10-08` de los repositorios editados.

## Tareas

- [x] M01 — Persistir entidades mínimas de operador/comercio/usuario y crear envíos/bultos por API usando EF Core, PostgreSQL y migración; pruebas de dominio e integración.
- [x] M02 — Completar el portal de comercio para el alta individual y Backoffice para consultar el registro persistido, demostrando el mismo ID de extremo a extremo.
- [x] M03 — Completar Compose con health/observabilidad requeridos por el hito y agregar workflow CI de compilación/pruebas; validar comandos localmente y demo Compose.

## Verificación y estado

- Resultado esperado: los casos CU-01, CU-07, CU-08 y condiciones T-01/T-02/T-03 quedan reproducibles con evidencia local; la CI remota no se considera ejecutada ni publicada.
- Ruta de implementación: directa en línea, por instrucción explícita del usuario de no delegar.
- Evidencia: `dotnet test NexoRuta.sln --configuration Release` pasó con 2 unitarias y 1 integración contra PostgreSQL efímero limpio; las compilaciones Release de backend/frontend pasaron; `docker compose config --quiet`, `docker compose build`, `docker compose up -d` y `actionlint` sobre el workflow CI pasaron. Chrome headless envió el formulario real del portal; el mismo ID se confirmó por `GET /api/envios` y en el HTML de Backoffice; portal y dashboard respondieron HTTP 200.
- CI: workflows propios en `backend/.github/workflows/ci.yml` y `frontend/.github/workflows/ci.yml`, activados al abrir, reabrir o actualizar un PR hacia `main`. Un paso falla si el origen no es `develop` del mismo repositorio. El checkout prueba el merge propuesto por el PR. La raíz y mobile no tienen pipeline. `actionlint`, builds y pruebas locales pasaron; la CI remota todavía no se ejecutó.
- Limitaciones: el alta usa identidad demo fija en ambiente Development; sin autenticación ni autorización real. Worker, RabbitMQ y Redis están presentes en Compose pero no integrados al flujo; no se implementaron RLS ni multitenencia; no se validó MAUI.
- Estado: implementación y verificaciones locales completadas; la primera ejecución remota queda pendiente de publicar las ramas y seguir el flujo de promoción indicado abajo.

## Publicación y primera ejecución de CI

1. En cada repositorio de código (`backend` y `frontend`), publicar `feature/monitoreo-2026-10-08` y abrir su PR hacia `develop`. Ese PR no ejecuta CI.
2. Fusionar cada PR de feature en `develop`; los pushes a `develop` tampoco ejecutan CI.
3. Abrir un PR de `develop` hacia `main` en cada repositorio. Al abrirlo y en cada actualización/reapertura, CI ejecuta restore y build; backend además ejecuta las pruebas contra un PostgreSQL limpio. El checkout usa el merge propuesto por el PR.
4. Configurar como checks obligatorios en las reglas de `main` el job `build-and-test` del workflow **Backend CI** y el job `build` del workflow **Frontend CI**, respectivamente. No fusionar el PR hasta que el check correspondiente pase. El paso `Validate PR source` falla si el origen no es `develop` del mismo repositorio.
5. Observar los checks en el PR y la ejecución en la pestaña **Actions** de backend y frontend. La raíz (`NexoRuta`) no tiene workflow; Compose se valida localmente. Mobile no tiene CI porque no se modificó. La CI remota sigue pendiente de publicar los workflows y observar la primera ejecución.


## Resultado por requisito

| Requisito | Implementación y demostración | Estado y pendiente |
|---|---|---|
| **CU-01 — Datos de demostración** | La API obtiene del servidor el usuario de demo y su vínculo con `Operador Demo` y `Comercio Demo`; no acepta que el portal elija esos propietarios. Se inicializan al aplicar la migración. | Implementado solo para demo local; **no hay autenticación ni autorización real**. |
| **CU-07 — Alta individual** | Formulario interactivo en Comercio; `POST /api/envios` crea el registro y lo persiste en PostgreSQL. Chrome headless envió el formulario real; el ID `01a11945-6737-71a1-ba1a-bfe44dc844ba` quedó en la API y apareció en Backoffice. | Recorrido portal → API → PostgreSQL → Backoffice comprobado. No incluye importación ni API masiva. |
| **CU-08 — Bulto** | El formulario exige código, peso positivo y largo, ancho y alto positivos. El bulto queda asociado al envío en PostgreSQL. | Implementado para uno o más bultos; la demo solicita uno. |
| **T-01 — Compose** | Agregué healthcheck de readiness para API y Aspire Dashboard con exportación OTLP. `docker compose config --quiet`, `docker compose build` y `docker compose up -d` finalizaron bien. Los nueve servicios quedaron levantados; API, PostgreSQL, Redis y RabbitMQ reportaron saludables, y Dashboard respondió HTTP 200. | URLs: Comercio `http://localhost:5102`, Backoffice `:5101`, API `:5000`, Dashboard `:18888`, RabbitMQ Management `:15672`, PostgreSQL `:5432`, RabbitMQ `:5672`, Tracking `:5103`. Redis solo es interno en `6379`. Dashboard está **sin autenticación**, solo para uso local. |
| **T-02 — Backoffice** | Backoffice consulta la API y muestra el mismo ID, operador, comercio, usuario, destinatario, dirección, estado y bulto. Verifiqué el ID creado desde el portal en su HTML. | Comprobado en Compose. |
| **T-03 — CI** | Workflows separados en backend y frontend para PR abierto/reabierto/actualizado hacia `main`; un paso falla si el origen no es `develop` del mismo repositorio. El checkout prueba el merge propuesto. Backend restaura, compila y ejecuta pruebas unitarias e integración con PostgreSQL limpio; frontend restaura y compila. Compose se valida localmente, fuera de CI. | `actionlint`, builds y pruebas locales pasaron. **La CI remota todavía no se ejecutó**: falta publicar los workflows/código, completar la promoción feature → develop y abrir el PR develop → main; los checks obligatorios deben pasar antes de fusionarlo. |

## Pruebas y limitaciones

- `dotnet test NexoRuta.sln --configuration Release`: **2 pruebas unitarias y 1 de integración pasaron**. La integración aplicó la migración y comprobó persistencia de envío y bulto contra PostgreSQL 18 efímero. El proyecto ArchitectureTests no tiene pruebas registradas.
- `dotnet build NexoRuta.sln --configuration Release` quedó cubierto por la compilación de la suite; frontend Release compiló sin advertencias ni errores.
- La prueba de integración apuntando desde Windows al PostgreSQL persistente de Compose falló por autenticación del host. La repetí con una instancia PostgreSQL efímera en `55432`, que pasó; no borré ni reinicié volúmenes existentes.
- La primera aserción del script de Chrome no reconoció el texto acentuado, aunque el portal mostró la confirmación. Verifiqué después el mismo ID directamente en API y Backoffice.
- Redis, RabbitMQ y Worker están incluidos en Compose, pero **no participan del flujo**. No implementé ni afirmo RLS, multitenencia, autenticación, máquina de estados completa, mensajería, cache funcional ni MAUI en dispositivos.

## Archivos modificados

- **Raíz:** `compose.yaml`, eliminación del workflow raíz `.github/workflows/ci.yml`, `odd/tasks/monitoreo-2026-10-08.md`.
- **Backend:** `Dockerfile`; configuración y arranque de API; controlador de envíos y healthcheck; entidades y casos de uso; persistencia EF Core, datos demo y migración; pruebas unitarias/de integración y referencias de pruebas; workflow `backend/.github/workflows/ci.yml`.
- **Frontend:** formulario de Comercio y configuración HTTP; página y modelo de Backoffice para consultar envíos; workflow `frontend/.github/workflows/ci.yml`.
- **Mobile:** sin cambios. `README.md`, `architecture.md` y `docs/` quedaron intactos.

Raíz, backend y frontend están en `feature/monitoreo-2026-10-08`. Mobile quedó en `develop` porque no se modificó. No hice commit ni push. Ejecuté `git diff --check` en raíz y en los tres submódulos: **los cuatro terminaron con exit 0**.

## Pasos para repetir la demo mañana

1. Desde la raíz, ejecutar `git submodule update --init --recursive`.
2. Ejecutar `docker compose up --build -d` y comprobar `docker compose ps`.
3. Abrir `http://localhost:5102`. Completar destinatario, dirección, código de bulto, peso en gramos y dimensiones en centímetros; presionar **Crear envío** y copiar el ID confirmado.
4. Abrir `http://localhost:5101` y actualizar. Confirmar que aparece ese ID y los datos del envío y bulto.
5. Evidencia complementaria: consultar `http://localhost:5000/api/envios`, readiness en `http://localhost:5000/health/ready` y observabilidad en `http://localhost:18888`.

Para repetir también las pruebas en Windows con una base limpia, iniciar PostgreSQL efímero en el puerto `55432`, establecer `NEXORUTA_TEST_POSTGRES` a `Host=127.0.0.1;Port=55432;Database=nexoruta;Username=nexoruta;Password=nexoruta_dev`, correr `dotnet test backend/NexoRuta.sln --configuration Release` y detener el contenedor efímero. La CI remota está pendiente de publicación: se ejecutará al abrir, reabrir o actualizar el PR `develop` → `main`, y sus checks deben pasar antes del merge.

## Key Learnings:

1. El formulario interactivo conserva el mismo identificador desde Comercio hasta Backoffice.
2. La prueba de integración usa una base efímera para aislar credenciales y datos persistentes.
3. Redis y RabbitMQ están presentes, pero todavía no participan en el caso de uso.
4. El dashboard OTLP local queda accesible sin autenticación y no debe exponerse externamente
