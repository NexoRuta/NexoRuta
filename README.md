# NexoRuta

NexoRuta es la base académica de una plataforma multioperador de distribución de última milla. El repositorio principal reúne la arquitectura y el entorno de desarrollo; el backend, las aplicaciones web y el cliente móvil están en submódulos Git.

## Clonar

Cloná el repositorio con sus submódulos:

```bash
git clone --recurse-submodules <URL-del-repositorio>
cd NexoRuta
```

Si ya clonaste el repositorio sin ellos:

```bash
git submodule update --init --recursive
```

Los submódulos configurados en `.gitmodules` son [backend](backend/), [frontend](frontend/) y [mobile](mobile/). Cada uno tiene un README independiente con su estructura, requisitos y comandos locales.

## Ramas y versiones de integración

La rama local `develop` de la raíz se prepara como manifiesto de integración desde `origin/main` (`df5fa86817dbaf4a84a8fff16473cf408984a87a`). La rama `feature/sync-feature-first-submodules` fija estas versiones, integradas en los `develop` de los componentes y verificadas en ARQ-09:

| Submódulo | Commit fijado |
| --- | --- |
| backend | `8a8e0db2d56dd0accc2109ca073eff6d9ee41397` |
| frontend | `bb29d036231f3e51b4b398f4c78e89ec5f394e43` |
| mobile | `da537ecf60c188e7b2adbf67d4b70097cad9e8d9` (sin cambios) |

Esta preparación es local: no crea `develop` remoto ni modifica `main`. Los commits fijados de backend y frontend todavía no están integrados en sus respectivos `main`. Publicar la rama de integración raíz y abrir un PR contra ella requiere autorización separada. La promoción del manifiesto a `main` debe coordinarse con las releases de los componentes; sus pushes a `main` pueden disparar despliegues. No actualizar los submódulos con `--remote` para sustituir estas versiones verificadas por otros HEAD.

## Requisitos de desarrollo

- Docker Desktop con Compose (o Docker Engine/Compose) para ejecutar el entorno local.
- .NET SDK 10 para compilar las soluciones. En este checkout, `global.json` selecciona SDK `10.0.401` con `latestPatch`.
- Workloads y herramientas nativas de .NET MAUI solo para compilar o ejecutar el destino móvil elegido.

## Levantar el entorno local

Desde esta raíz:

```bash
docker compose config --quiet
docker compose build
docker compose up -d
docker compose ps
```

Para API y portales, la configuración local ignorada por Git (`.env`) debe mantener `NEXORUTA_POSTGRES_CONNECTION` apuntando al servicio Compose `postgres` (`nexoruta:5432`), `NEXORUTA_APPLY_MIGRATIONS=false` y `NEXORUTA_SEED_DATA=false`. Arranque habitual en PowerShell:

```powershell
docker compose config --quiet
docker compose up -d --build postgres api backoffice commerce
docker compose ps
```

Aplicar una migración local es una operación administrativa separada: revisar previamente el SQL y confirmar que el destino es el PostgreSQL de este Compose. Sin cambiar `NEXORUTA_SEED_DATA=false`, habilitar solo la migración para el primer arranque de API y después volver a la configuración protegida:

```powershell
$env:NEXORUTA_APPLY_MIGRATIONS = 'true'
docker compose up -d --no-deps --force-recreate api
docker compose ps api  # esperar a que la API quede healthy
Remove-Item Env:NEXORUTA_APPLY_MIGRATIONS
docker compose up -d --no-deps --force-recreate api
```

No dejar el override de proceso habilitado luego de la aplicación. No se versionan credenciales ni cadenas de conexión; `.env` permanece local e ignorado.

El Compose inicia diez servicios. Para el primer monitoreo del 8 de octubre de 2026 se verificó el alta de un envío desde el portal, su persistencia con bulto en PostgreSQL y la consulta del mismo ID en Backoffice. Se inicializan un operador, un comercio, una cuenta del dueño y una cuenta del operador. El comercio puede elegir cualquier operador registrado, sin un vínculo previo; cada envío conserva `OperadorId` y `ComercioId`. El ingreso al portal selecciona la cuenta del comercio, y el operador se elige al crear cada envío. Backoffice solo admite cuentas del operador. El selector es sin credenciales; no se implementaron CRUD ni perfiles laborales.

Para detener los servicios sin borrar los volúmenes de datos:

```bash
docker compose down
```

### URLs y puertos publicados

| Servicio | Dirección local | Uso y límites |
| --- | --- | --- |
| API | `http://localhost:5000` | Cuentas en `GET /api/accesos?tipo=Comercio\|Operador`; operadores disponibles en `GET /api/comercio/operadores`. Usuario actual, operadores y envíos requieren `X-NexoRuta-Acceso`. Salud en `/health/live` y `/health/ready`; OpenAPI en [`/openapi/v1.json`](http://localhost:5000/openapi/v1.json). |
| Backoffice | `http://localhost:5101` | Consulta de envíos persistidos y sus bultos en Razor Pages. |
| Admin | `http://localhost:5104` | Administración exclusiva de plataforma: listado, detalle y alta de operadores/comercios con su primer administrador. Ver [preparación local pendiente](frontend/docs/admin.md). |
| Commerce | `http://localhost:5102` | Alta individual de envío y bulto en Blazor Server. |
| Tracking | `http://localhost:5103` | Plantilla Blazor Server. |
| Aspire Dashboard | `http://localhost:18888` | Observabilidad local; recibe telemetría de la API. |
| RabbitMQ Management | `http://localhost:15672` | Interfaz de administración; credenciales locales de desarrollo: `nexoruta` / `nexoruta_dev`. |
| PostgreSQL | `localhost:5432` | Puerto TCP; base `nexoruta`, usuario `nexoruta`, contraseña `nexoruta_dev` (solo desarrollo local). |
| RabbitMQ | `localhost:5672` | Puerto AMQP; las mismas credenciales locales de desarrollo. |
| Redis | Sin puerto publicado en el host | Disponible para otros contenedores en `redis:6379` dentro de la red Compose. |
| Worker | Sin puerto HTTP publicado | Proceso de plantilla que registra actividad periódica. |

Las credenciales del archivo Compose son públicas y no deben reutilizarse fuera del entorno local. EF Core/PostgreSQL persiste los envíos; Redis, RabbitMQ y Worker todavía no participan del flujo. El bootstrap conserva `AccesoInicial` y `DatosInicialesSeeder`, con cuatro valores explícitos requeridos: `AccesoInicial:UsuarioEmail`, `AccesoInicial:OperadorNombre`, `AccesoInicial:ComercioNombre` y `AccesoInicial:OperadorUsuarioEmail`. `Demo:Enabled` y las transformaciones históricas por nombres Demo fueron eliminados; no se borraron registros existentes. La configuración y su alcance se describen en [CU-01](backend/docs/cu/CU-01-comercios-usuarios.md).

### Initial platform administrator (local Compose)

Admin is available at `http://localhost:5104`. The API maps the ignored `.env` keys `NEXORUTA_ADMIN_MAIL` and `NEXORUTA_ADMIN_PASSWORD` to `PlatformInitialization__Email/Password`. Only `NEXORUTA_PLATFORM_BOOTSTRAP=true` enables platform initialization; it defaults to false and is independent of demonstration data. Keep habitual `NEXORUTA_APPLY_MIGRATIONS=false` and `NEXORUTA_SEED_DATA=false`.

Review/apply pending additive migrations explicitly to the confirmed local Compose PostgreSQL **before** recreating the updated API. Do not delete volumes or reset data. API startup creates the account atomically, or validates an existing compatible account without replacing its password. No manual `platform-admin create` is required in this configured local flow. See the [backend procedure](backend/docs/workflow/platform-administration.md).

## Estructura del repositorio

```text
NexoRuta/
  backend/       # API, Worker y proyectos de capas .NET
  frontend/      # Admin, Backoffice, Commerce y Tracking
  mobile/        # aplicación .NET MAUI
  architecture.md
  compose.yaml
  global.json
  .gitmodules
```

`architecture.md` distingue la base técnica verificada de la arquitectura y capacidades previstas.

## Estado actual

- Application, API, Infrastructure, ApiClient y presentación web están organizados por funcionalidad y responsabilidad. Las vistas Razor Pages conservan sus ubicaciones para mantener routing; sus PageModels están agrupados por feature. Tracking sigue siendo una plantilla.
- Baseline histórico ARQ-06: backend con 19 unitarias, 3 de arquitectura y 42 de integración; frontend con 53 pruebas, incluidas 7 de contratos OpenAPI. Las 17 de configuración/DI están incluidas en las 42 de integración. Backend y frontend compilaron sin errores ni advertencias; frontend en Debug y Release. Las 46 comprobaciones HTTP de presentación usaron un backend simulado.
- ARQ-09 (9 de octubre de 2026) verificó los commits de la tabla anterior con Chrome, Commerce, API, PostgreSQL 18 temporal aislado y Backoffice reales, sin mocks: el mismo envío se creó, persistió y visualizó. También se verificaron rechazos por sesión, cuenta y datos inválidos. No se encontraron ejecuciones de CI para esos commits integrados.
- ARQ-10 solo sincroniza gitlinks y documentación: no reejecuta suites, E2E ni Compose. El arranque de nueve servicios Compose corresponde al monitoreo anterior; no acredita un nuevo despliegue de estas versiones. La última compilación de mobile corresponde al 7 de octubre; no se validó MAUI en dispositivos.
- Están implementados los recortes de [CU-01](backend/docs/cu/CU-01-comercios-usuarios.md), [CU-07](backend/docs/cu/CU-07-alta-envios.md) y [CU-08](backend/docs/cu/CU-08-bultos.md) del primer monitoreo. Autenticación por credenciales, RLS, CRUD de administración y mensajería funcional quedan pendientes.
- Backend y frontend tienen workflows de CI. Compilación y pruebas se verificaron localmente; no se ejecutó CI remota para estos cambios ni se verificó despliegue remoto.

Para conocer el estado y los comandos de cada componente, consultá [Backend](backend/README.md), [Frontend](frontend/README.md) y [Mobile](mobile/README.md).

Self-service registration and organization onboarding is the habitual entry point; see [the onboarding guide](docs/registro-alta-propia.md). Platform Admin remains available for support. CU-01 is not closed.
