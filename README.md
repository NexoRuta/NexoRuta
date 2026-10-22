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

## VM de pruebas en Google Cloud

La [guía de infraestructura y CI/CD](infra/gcp/README.md) documenta OpenTofu,
Cloud SQL/PostGIS, las seis imágenes .NET, HTTPS, los workers y el APK. La demo usa
una VM de 16 GiB en Santiago, cercana a Uruguay, con inicio manual por cuatro horas
y apagado coordinado de VM y base de datos. Los pushes a `main` solo prueban y publican
imágenes. Iniciar, actualizar contenedores y apagar son operaciones manuales desde
GitHub Actions; `start` usa lo último de `main` de los tres repos. La preparación
y operación también se hacen por terminal.

La configuración pública de aplicaciones (SMTP y Mapbox) está en el bloque
`x-app-settings` de [compose.yaml](compose.yaml), junto con la configuración local.
Las variables GCP y las credenciales se configuran en el environment de GitHub,
según la [lista de variables y secrets](infra/gcp/github-environment.md).

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

El Compose inicia nueve servicios. Para el primer monitoreo del 8 de octubre de 2026 se verificó el alta de un envío desde el portal, su persistencia con bulto en PostgreSQL y la consulta del mismo ID en Backoffice. Se inicializan un operador, un comercio, una cuenta del dueño y una cuenta del operador. El comercio puede elegir cualquier operador registrado, sin un vínculo previo; cada envío conserva `OperadorId` y `ComercioId`. El ingreso al portal selecciona la cuenta del comercio, y el operador se elige al crear cada envío. Backoffice solo admite cuentas del operador. El selector es sin credenciales; no se implementaron CRUD ni perfiles laborales.

Para detener los servicios sin borrar los volúmenes de datos:

```bash
docker compose down
```

### URLs y puertos publicados

| Servicio | Dirección local | Uso y límites |
| --- | --- | --- |
| API | `http://localhost:5000` | Cuentas en `GET /api/accesos?tipo=Comercio|Operador`; operadores disponibles en `GET /api/operadores`. Usuario actual, operadores y envíos requieren `X-NexoRuta-Acceso`. Salud en `/health/live` y `/health/ready`; OpenAPI en [`/openapi/v1.json`](http://localhost:5000/openapi/v1.json). |
| Backoffice | `http://localhost:5101` | Consulta de envíos persistidos y sus bultos en Razor Pages. |
| Commerce | `http://localhost:5102` | Alta individual de envío y bulto en Blazor Server. |
| Tracking | `http://localhost:5103` | Plantilla Blazor Server. |
| Aspire Dashboard | `http://localhost:18888` | Observabilidad local; recibe telemetría de la API. |
| RabbitMQ Management | `http://localhost:15672` | Interfaz de administración; credenciales locales de desarrollo: `nexoruta` / `nexoruta_dev`. |
| PostgreSQL | `localhost:5432` | Puerto TCP; base `nexoruta`, usuario `nexoruta`, contraseña `nexoruta_dev` (solo desarrollo local). |
| RabbitMQ | `localhost:5672` | Puerto AMQP; las mismas credenciales locales de desarrollo. |
| Redis | Sin puerto publicado en el host | Disponible para otros contenedores en `redis:6379` dentro de la red Compose. |
| Worker | Sin puerto HTTP publicado | Proceso de plantilla que registra actividad periódica. |

Las credenciales del archivo Compose son públicas y no deben reutilizarse fuera del entorno local. EF Core/PostgreSQL persiste los envíos; Redis, RabbitMQ y Worker todavía no participan del flujo. La configuración de `AccesoInicial` y su alcance se describen en [CU-01](backend/docs/cu/CU-01-comercios-usuarios.md).

## Estructura del repositorio

```text
NexoRuta/
  backend/       # API, Worker y proyectos de capas .NET
  frontend/      # Backoffice, Commerce y Tracking
  mobile/        # aplicación .NET MAUI
  architecture.md
  compose.yaml
  global.json
  .gitmodules
```

`architecture.md` distingue la base técnica verificada de la arquitectura y capacidades previstas.

## Estado actual

- Backend y frontend compilan con .NET 10. La compilación de Worker presenta advertencias por versiones distintas de EF Core; no se modificaron sus dependencias en esta revisión. La última compilación de mobile corresponde al 7 de octubre de 2026.
- Pasaron **30 pruebas de backend** (8 unitarias y 22 de integración PostgreSQL) y **30 de frontend** (cliente HTTP, selección y contratos). ArchitectureTests todavía no contiene pruebas; no se validó MAUI en dispositivos.
- Los nueve servicios de Compose arrancan. Se comprobó el formulario real del portal, el bulto persistido y el mismo envío en Backoffice.
- Están implementados los recortes de [CU-01](backend/docs/cu/CU-01-comercios-usuarios.md), [CU-07](backend/docs/cu/CU-07-alta-envios.md) y [CU-08](backend/docs/cu/CU-08-bultos.md) del primer monitoreo. Autenticación por credenciales, RLS, CRUD de administración y mensajería funcional quedan pendientes.
- Backend y frontend tienen workflows de CI. Compilación y pruebas se verificaron localmente; no se ejecutó CI remota para estos cambios ni se verificó despliegue remoto.

Para conocer el estado y los comandos de cada componente, consultá [Backend](backend/README.md), [Frontend](frontend/README.md) y [Mobile](mobile/README.md).
