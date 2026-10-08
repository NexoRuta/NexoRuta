# Monitoreo NexoRuta 08/10/2026

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
