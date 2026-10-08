# Monitoreo NexoRuta 08/10/2026

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
- CI: workflows propios en `backend/.github/workflows/ci.yml` y `frontend/.github/workflows/ci.yml`, activados únicamente al cerrar un PR hacia `main`; el job exige que esté fusionado, que venga de `develop` en el mismo repositorio y hace checkout de `main`. La raíz y mobile no tienen pipeline. `actionlint`, builds y pruebas locales pasaron; la CI remota todavía no se ejecutó.
- Limitaciones: el alta usa identidad demo fija en ambiente Development; sin autenticación ni autorización real. Worker, RabbitMQ y Redis están presentes en Compose pero no integrados al flujo; no se implementaron RLS ni multitenencia; no se validó MAUI.
- Estado: implementación y verificaciones locales completadas; la primera ejecución remota queda pendiente de publicar las ramas y seguir el flujo de promoción indicado abajo.

## Publicación y primera ejecución de CI

1. En cada repositorio de código (`backend` y `frontend`), publicar `feature/monitoreo-2026-10-08` y abrir su PR hacia `develop`. Ese PR no ejecuta CI.
2. Fusionar cada PR de feature en `develop`; los pushes a `develop` tampoco ejecutan CI.
3. Abrir un PR de `develop` hacia `main` en cada repositorio. Mientras siga abierto, CI no se ejecuta.
4. Al fusionar cada PR hacia `main`, GitHub emite `pull_request: closed`; el job continúa solo si `merged == true`, la rama de origen es `develop` y el repositorio de origen es el mismo. Hace checkout explícito de `main`, restaura y compila; backend además ejecuta sus pruebas contra un PostgreSQL limpio.
5. Observar el resultado en la pestaña **Actions** de los repositorios backend y frontend. La raíz (`NexoRuta`) no tiene workflow; Compose se valida localmente. Mobile no tiene CI porque no se modificó.


## Resultado por requisito

| Requisito | Implementación y demostración | Estado y pendiente |
|---|---|---|
| **CU-01 — Datos de demostración** | La API obtiene del servidor el usuario de demo y su vínculo con `Operador Demo` y `Comercio Demo`; no acepta que el portal elija esos propietarios. Se inicializan al aplicar la migración. | Implementado solo para demo local; **no hay autenticación ni autorización real**. |
| **CU-07 — Alta individual** | Formulario interactivo en Comercio; `POST /api/envios` crea el registro y lo persiste en PostgreSQL. Chrome headless envió el formulario real; el ID `01a11945-6737-71a1-ba1a-bfe44dc844ba` quedó en la API y apareció en Backoffice. | Recorrido portal → API → PostgreSQL → Backoffice comprobado. No incluye importación ni API masiva. |
| **CU-08 — Bulto** | El formulario exige código, peso positivo y largo, ancho y alto positivos. El bulto queda asociado al envío en PostgreSQL. | Implementado para uno o más bultos; la demo solicita uno. |
| **T-01 — Compose** | Agregué healthcheck de readiness para API y Aspire Dashboard con exportación OTLP. `docker compose config --quiet`, `docker compose build` y `docker compose up -d` finalizaron bien. Los nueve servicios quedaron levantados; API, PostgreSQL, Redis y RabbitMQ reportaron saludables, y Dashboard respondió HTTP 200. | URLs: Comercio `http://localhost:5102`, Backoffice `:5101`, API `:5000`, Dashboard `:18888`, RabbitMQ Management `:15672`, PostgreSQL `:5432`, RabbitMQ `:5672`, Tracking `:5103`. Redis solo es interno en `6379`. Dashboard está **sin autenticación**, solo para uso local. |
| **T-02 — Backoffice** | Backoffice consulta la API y muestra el mismo ID, operador, comercio, usuario, destinatario, dirección, estado y bulto. Verifiqué el ID creado desde el portal en su HTML. | Comprobado en Compose. |
| **T-03 — CI** | Workflows separados en backend y frontend, solo para PR cerrado contra `main`; los jobs exigen PR fusionado desde `develop` del mismo repositorio y hacen checkout explícito de `main`. Backend ejecuta restauración, build, pruebas unitarias e integración con PostgreSQL limpio; frontend restaura y compila. Compose se valida localmente, fuera de CI. | `actionlint`, builds y pruebas locales pasaron. **La CI remota todavía no se ejecutó**: falta publicar los workflows/código, completar la promoción feature → develop → main y observar la ejecución posterior al merge. |

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

Para repetir también las pruebas en Windows con una base limpia, iniciar PostgreSQL efímero en el puerto `55432`, establecer `NEXORUTA_TEST_POSTGRES` a `Host=127.0.0.1;Port=55432;Database=nexoruta;Username=nexoruta;Password=nexoruta_dev`, correr `dotnet test backend/NexoRuta.sln --configuration Release` y detener el contenedor efímero. La CI remota no se ejecuta hasta fusionar los PR de `develop` hacia `main` en cada repositorio de código.

## Key Learnings:

1. El formulario interactivo conserva el mismo identificador desde Comercio hasta Backoffice.
2. La prueba de integración usa una base efímera para aislar credenciales y datos persistentes.
3. Redis y RabbitMQ están presentes, pero todavía no participan en el caso de uso.
4. El dashboard OTLP local queda accesible sin autenticación y no debe exponerse externamente
