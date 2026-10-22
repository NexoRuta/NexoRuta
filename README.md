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

Estos comandos de configuración, construcción y arranque se verificaron localmente el 7 de octubre de 2026. `docker compose up -d` inicia ocho servicios; esto valida el arranque de las plantillas y la infraestructura, no flujos de negocio ni la conexión efectiva de las aplicaciones a sus dependencias.

Para detener los servicios sin borrar los volúmenes de datos:

```bash
docker compose down
```

### URLs y puertos publicados

| Servicio | Dirección local | Uso y límites |
| --- | --- | --- |
| API | `http://localhost:5000` | La raíz devuelve 404; no hay rutas de negocio. En Development, OpenAPI está en [`http://localhost:5000/openapi/v1.json`](http://localhost:5000/openapi/v1.json) y documenta cero rutas. |
| Backoffice | `http://localhost:5101` | Plantilla web Razor Pages. |
| Commerce | `http://localhost:5102` | Plantilla Blazor Server. |
| Tracking | `http://localhost:5103` | Plantilla Blazor Server. |
| RabbitMQ Management | `http://localhost:15672` | Interfaz de administración; credenciales locales de desarrollo: `nexoruta` / `nexoruta_dev`. |
| PostgreSQL | `localhost:5432` | Puerto TCP; base `nexoruta`, usuario `nexoruta`, contraseña `nexoruta_dev` (solo desarrollo local). |
| RabbitMQ | `localhost:5672` | Puerto AMQP; las mismas credenciales locales de desarrollo. |
| Redis | Sin puerto publicado en el host | Disponible para otros contenedores en `redis:6379` dentro de la red Compose. |
| Worker | Sin puerto HTTP publicado | Proceso de plantilla que registra actividad periódica. |

Las credenciales del archivo Compose son públicas y no deben reutilizarse fuera del entorno local. Compose configura conexiones en API y Worker, pero eso no significa que EF Core, Redis o RabbitMQ estén integrados funcionalmente.

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

- Las tres soluciones (.NET 10) compilaron correctamente en la validación local del 7 de octubre de 2026.
- `dotnet test` terminó sin error, pero en backend, frontend y mobile se ejecutaron **cero pruebas**. No hay cobertura funcional demostrada.
- `docker compose build` y `docker compose up -d` finalizaron correctamente en esa validación; los ocho servicios arrancaron.
- Las aplicaciones siguen siendo mayormente plantillas. No se afirma que estén implementados EF Core, migraciones, RLS, autenticación, mensajería, flujos funcionales de web ni ejecución de MAUI en dispositivos.
- No se verificó CI, despliegue remoto ni operación en producción.

Para conocer el estado y los comandos de cada componente, consultá [Backend](backend/README.md), [Frontend](frontend/README.md) y [Mobile](mobile/README.md).
