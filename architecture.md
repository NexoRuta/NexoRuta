# NexoRuta — Arquitectura

## Estado

La base técnica está implementada como una estructura inicial por capas en .NET 10 y su compilación y arranque local fueron verificados. El monolito modular y sus integraciones siguen siendo la arquitectura objetivo, no funcionalidades ya implementadas.

Esta fotografía corresponde al diagnóstico de código y a la segunda pasada de ejecución del **7 de octubre de 2026**, en el entorno local de Uruguay. Los resultados siguientes describen esa ejecución; no garantizan el estado actual ni la operación en producción.

| Área | Implementado y verificado | Previsto o pendiente | Evidencia en el repositorio |
| --- | --- | --- | --- |
| Backend .NET 10 y capas | Proyectos Domain, Application, Infrastructure, API y Worker; compilación satisfactoria. Domain no referencia otras capas; Application referencia Domain; Infrastructure referencia Application/Domain; API y Worker referencian Application/Infrastructure. | Módulos y comprobaciones de sus límites. La separación por proyectos no demuestra un monolito modular integrado. | `backend/NexoRuta.sln`, `backend/src/*/*.csproj` |
| API y Worker separados | Ambos arrancaron; la API sirve OpenAPI sin rutas y el Worker escribe un mensaje periódico. | Endpoints e implementación del procesamiento en segundo plano. | `backend/src/NexoRuta.Api/Program.cs`, `backend/src/NexoRuta.Worker/Program.cs`, `backend/src/NexoRuta.Worker/Worker.cs` |
| PostgreSQL, EF Core y RLS | Contenedor PostgreSQL iniciado y saludable. | EF Core/Npgsql, DbContext, migraciones, políticas RLS, autenticación y contexto de tenant no implementados; aislamiento sin validar. | `compose.yaml`, `backend/src/NexoRuta.Infrastructure/NexoRuta.Infrastructure.csproj`, `backend/src/NexoRuta.Api/Program.cs` |
| Redis y RabbitMQ | Contenedores iniciados y saludables; RabbitMQ Management respondió por HTTP. Compose suministra configuración a API y Worker. | Adaptadores de caché/sesiones y publicación/consumo de mensajes no implementados. Configurar conexiones no demuestra utilizarlas. | `compose.yaml`, `backend/src/NexoRuta.Api/Program.cs`, `backend/src/NexoRuta.Worker/Program.cs` |
| Clientes web y móvil | Plantillas Razor Pages, Blazor interactivo de servidor y MAUI; compilación satisfactoria y HTTP de las tres aplicaciones web. | Clientes HTTP hacia la API no implementados; ejecución móvil en dispositivos y despliegue Apple sin validar. | `frontend/src/NexoRuta.{Backoffice,Commerce,Tracking}/Program.cs`, `mobile/src/NexoRuta.Mobile/MauiProgram.cs`, `mobile/src/NexoRuta.Mobile/MainPage.xaml.cs` |
| Pruebas | El comando de test terminó sin error en las tres soluciones. | **Cero pruebas ejecutadas**: no hay cobertura demostrada ni comprobaciones funcionales o de aislamiento. | `backend/tests/NexoRuta.{ArchitectureTests,IntegrationTests,UnitTests}/`, `frontend/NexoRuta.sln`, `mobile/NexoRuta.sln` |
| Observabilidad y disponibilidad | Logging básico y healthchecks de los tres servicios de infraestructura. | Telemetría operativa, correlación API–mensajes, liveness/readiness y checks de dependencias de las aplicaciones no implementados. | `compose.yaml`, `backend/src/NexoRuta.Api/Program.cs`, `backend/src/NexoRuta.Worker/Worker.cs` |
| Docker Compose y despliegue | Construcción de cinco imágenes de aplicación y arranque de ocho servicios locales. | VPS, HTTPS/Cloudflare y automatización GitHub Actions sin validar en esta revisión; Kafka y NoSQL siguen previstos, no presentes en el Compose actual. | `compose.yaml`, `backend/Dockerfile`, `frontend/Dockerfile` |

Las rutas con `*` o `{...}` agrupan archivos equivalentes. La evidencia de ejecución y sus límites se detallan a continuación; las decisiones posteriores conservan su carácter de arquitectura objetivo.

## Evidencia de validación local

En la segunda pasada se ejecutaron estos comandos para cada solución: `backend/NexoRuta.sln`, `frontend/NexoRuta.sln` y `mobile/NexoRuta.sln`.

```powershell
dotnet restore <solución> --nologo
dotnet build <solución> --no-restore --nologo
dotnet test <solución> --no-build --no-restore --nologo
```

| Solución | Restore | Build | Test | Pruebas ejecutadas realmente |
| --- | --- | --- | --- | ---: |
| Backend | Exit 0 | Exit 0; 0 warnings y 0 errores | Exit 0 | 0 |
| Frontend | Exit 0 | Exit 0; 0 warnings y 0 errores | Exit 0 | 0 |
| Mobile | Exit 0 | Exit 0; 0 warnings y 0 errores | Exit 0 | 0 |

Los tres proyectos de pruebas del backend informaron que no había pruebas disponibles; frontend y mobile no contienen proyectos de pruebas. **El exit 0 de `dotnet test` no acredita cobertura.** La compilación MAUI de los destinos configurados con los workloads existentes no acredita ejecución en dispositivos ni despliegue Apple.

También finalizaron con exit 0 `docker compose config --quiet`, `docker compose build` y `docker compose up -d`, usando Docker Desktop local. Se revisaron el estado y los logs de los ocho servicios: todos estaban `Up`; PostgreSQL, Redis y RabbitMQ estaban `healthy`, y el Worker mantenía su mensaje periódico. No se encontraron errores bloqueantes ni fue necesario corregir código o configuración.

| Petición HTTP local | Resultado observado |
| --- | --- |
| `http://localhost:5000/` | 404, coherente con la ausencia de endpoints |
| `http://localhost:5000/openapi/v1.json` | 200; documento con cero rutas |
| `http://localhost:5101/` — Backoffice | 200 |
| `http://localhost:5102/` — Commerce | 200 |
| `http://localhost:5103/` — Tracking | 200 |
| `http://localhost:15672/` — RabbitMQ Management | 200 |

El Worker no expone una aplicación HTTP. Estas respuestas prueban disponibilidad básica de las plantillas, no integración entre clientes, API, persistencia y transporte.

### Límites y validaciones pendientes

- `global.json` selecciona SDK `10.0.401` con `latestPatch`; `backend/Dockerfile` y `frontend/Dockerfile` usan `sdk:10.0`. Los contextos de construcción de `compose.yaml` no incluyen el `global.json` raíz, por lo que no se ha demostrado equivalencia ni reproducibilidad exacta entre SDK local y Docker.
- El Compose actual es de desarrollo: usa `Development`, credenciales escritas en el archivo y puertos publicados de PostgreSQL y RabbitMQ sin restringir interfaz. El arranque local no valida un despliegue seguro en la VPS.
- Los logs mostraron advertencias no bloqueantes de claves DataProtection efímeras/sin cifrar, configuración redundante de puertos y métricas obsoletas de RabbitMQ. Redis funciona sin autenticación dentro de la red Compose. Son pendientes de preparación operativa, no errores de arranque corregidos.
- Persistencia de datos de aplicación, enforcement RLS, seguridad entre tenants, consumo/confirmación de mensajes, caché, recuperación ante fallos y observabilidad integral no se validaron: sus implementaciones todavía faltan.
- No se inspeccionó ni desplegó infraestructura remota. Cloudflare, GitHub Actions y las extensiones Kafka/NoSQL conservan su condición de decisiones previstas; su operación queda sin validar.

## Decisiones principales (arquitectura objetivo)

- La solución utilizará un monolito modular.
- No se utilizarán microservicios inicialmente.
- Backend basado en .NET 10.
- Se separan la API HTTP y el Worker de procesamiento.
- PostgreSQL será la base de datos principal.
- La estrategia multitenancy será Row-Level Security (RLS).
- Redis se utilizará para caché, sesiones y datos temporales.
- RabbitMQ se utilizará para comunicación asíncrona entre módulos.
- Kafka y una base NoSQL quedan contemplados como extensiones para eventos, auditoría técnica y analítica.
- El backoffice utilizará ASP.NET Core Razor Pages.
- Las interfaces de comercio y seguimiento utilizarán Blazor.
- La aplicación móvil se desarrollará con .NET MAUI.
- El despliegue inicial se realizará en una única VPS de Hetzner.
- Cloudflare se utilizará como proxy, DNS y capa perimetral.
- La automatización se realizará mediante GitHub Actions.

## Arquitectura lógica prevista

### Clientes

- Backoffice administrativo: ASP.NET Core Razor Pages.
- Portal de comercios: Blazor.
- Portal público de seguimiento: Blazor.
- Aplicación móvil: .NET MAUI.

### Backend

La API estará organizada como un monolito modular. Los módulos compartirán el mismo proceso y solución, pero mantendrán límites claros de responsabilidad.

Módulos funcionales iniciales:

- M01 — Gestión de usuarios y operadores.
- M02 — Gestión de comercios y configuraciones.
- M03 — Gestión de pedidos y envíos.
- M04 — Gestión de repartidores y asignaciones.
- M05 — Seguimiento y comunicaciones.
- M06 — Monitoreo y liquidaciones.

El Worker procesará tareas en segundo plano, mensajes de RabbitMQ, notificaciones, actualizaciones de seguimiento y procesos de liquidación.

## Persistencia y mensajería previstas

### PostgreSQL

Será la base de datos transaccional principal.

Se utilizará una única base de datos compartida con aislamiento lógico mediante RLS.

Cada comercio tendrá su propio identificador:

```text
operator_id UUID
```

Las tablas pertenecientes a un comercio incluirán `operator_id`. La API establecerá el operador actual en la conexión o transacción, y PostgreSQL aplicará las políticas RLS correspondientes.

La seguridad se validará en dos capas:

1. Autorización y validación en la API.
2. Políticas RLS directamente en PostgreSQL.

### Redis

Se utilizará para:

- Caché.
- Sesiones y datos temporales.
- Rate limiting.
- Estados efímeros de seguimiento.
- Bloqueos distribuidos cuando sea necesario.

### RabbitMQ

Será el mecanismo principal para:

- Eventos de dominio.
- Procesamiento asíncrono.
- Notificaciones.
- Actualización de estados.
- Comunicación entre la API y el Worker.

### Kafka y NoSQL

Kafka y una base NoSQL se consideran componentes de extensión para:

- Historial de eventos.
- Analítica.
- Telemetría.
- Auditoría técnica.
- Consultas de lectura optimizadas.

No serán dependencias obligatorias del primer arranque local si el costo de infraestructura o memoria resulta elevado.

## Despliegue previsto

Todos los componentes iniciales se ejecutarán mediante Docker Compose en una única VPS de Hetzner.

Componentes previstos:

- API .NET.
- Worker .NET.
- Backoffice Razor Pages.
- Portal Blazor de comercios.
- Portal Blazor de seguimiento.
- PostgreSQL.
- Redis.
- RabbitMQ.
- Kafka y NoSQL mediante perfiles de infraestructura extendida.
- Proxy perimetral administrado mediante Cloudflare.

La aplicación móvil no se ejecutará dentro de Docker Compose. Se compilará para Android, Windows u otras plataformas compatibles.

## Estructura de repositorios implementada

```text
NexoRuta/
├── backend/
├── frontend/
├── mobile/
├── architecture.md
├── compose.yaml
├── global.json
└── .gitmodules
```

### Backend

```text
backend/
├── src/
│   ├── NexoRuta.Api
│   ├── NexoRuta.Worker
│   ├── NexoRuta.Domain
│   ├── NexoRuta.Application
│   └── NexoRuta.Infrastructure
└── tests/
```

### Frontend

```text
frontend/
└── src/
    ├── NexoRuta.Backoffice
    ├── NexoRuta.Commerce
    └── NexoRuta.Tracking
```

### Mobile

```text
mobile/
└── src/
    └── NexoRuta.Mobile
```

## Flujo de comunicación previsto (no integrado todavía)

```text
Cliente
  -> Cloudflare
  -> Aplicación web o móvil
  -> NexoRuta.Api
  -> Módulo correspondiente
  -> PostgreSQL / Redis

NexoRuta.Api
  -> RabbitMQ
  -> NexoRuta.Worker
  -> Notificaciones, seguimiento y procesos de liquidación
```

## Comando de inicio local

Desde la raíz del repositorio:

```bash
docker compose up -d --build
```

La segunda pasada verificó construcción y arranque en comandos separados (`docker compose build` y `docker compose up -d`). Este comando combinado es la forma de inicio local; no implica que el despliegue previsto en VPS esté validado.

## Principios

- Modularidad antes que distribución física.
- Seguridad aplicada en API y base de datos.
- Procesos lentos fuera del ciclo HTTP.
- Infraestructura reproducible.
- Separación clara entre dominio, aplicación e infraestructura.
- Evolución gradual hacia componentes distribuidos únicamente si existe una necesidad real.
