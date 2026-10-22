# NexoRuta — Arquitectura

## Estado actual — 8 de octubre de 2026

Están implementados los recortes del primer monitoreo: cuentas pertenecientes a un operador o a un comercio, catálogo global de operadores para el alta, envíos con `OperadorId` y `ComercioId`, un bulto por alta y lectura por la organización de la cuenta. Las empresas y sus usuarios tienen identidades separadas; el comercio puede enviar con cualquier operador registrado.

| Área | Implementado y verificado localmente | Previsto o pendiente | Evidencia |
| --- | --- | --- | --- |
| Backend y persistencia | Capas .NET 10, EF Core/Npgsql, migraciones, inicialización repetible, envíos y bultos persistidos. Repositorios separados de accesos, operadores y comercios. | Límites completos de módulos, concurrencia y capacidades posteriores del laboratorio. | `backend/src/`, `backend/docs/cu/` |
| Entrada y acceso | `/api/accesos`, `/api/usuarios/actual`, `/api/operadores` y `/api/envios`. Selección de cuenta, ámbito de empresa, filtros por organización y contexto reutilizado en una sola consulta por petición. | Autenticación por credenciales, perfiles laborales y RLS. La selección actual no prueba identidad. | `backend/src/NexoRuta.Api/Controllers/`, `backend/src/NexoRuta.Api/Seguridad/` |
| Clientes | Commerce crea envíos y elige cualquier operador registrado; Backoffice consulta los de su operador. Cliente HTTP compartido, cookies independientes y cancelación de llamadas al destruir el formulario Blazor. | Tracking y Mobile mantienen plantillas; seguimiento público y operación móvil siguen pendientes. | `frontend/src/`, `mobile/src/` |
| Pruebas | 30 pruebas del backend: 8 unitarias y 22 de integración. 30 del frontend: cliente, formulario y OpenAPI. Integración con PostgreSQL mediante bases temporales por escenario. | ArchitectureTests sigue sin pruebas. No se ejecutó MAUI en dispositivos. | `backend/tests/`, `frontend/tests/` |
| Servicios y observabilidad | Nueve servicios Compose; API/PostgreSQL/Redis/RabbitMQ saludables. Salud de API y webs, OpenAPI y exportación OpenTelemetry al Dashboard local. Worker registra actividad. | Redis, RabbitMQ y Worker todavía no participan en envíos; RLS y observabilidad de mensajes quedan pendientes. | `compose.yaml`, `backend/src/NexoRuta.Api/Program.cs` |
| Construcción y publicación | Soluciones backend/frontend y Docker comprobados localmente. Workflows de CI presentes. Backend mantiene tres advertencias preexistentes de versiones EF Core en Worker. | No se verificaron CI ni despliegue remoto en esta revisión. Kafka y NoSQL siguen previstos. | `backend/.github/`, `frontend/.github/` |

La API usa `http://localhost:5000` en Compose y `http://localhost:5041` con su perfil `http` de `dotnet run`. Las webs usan 5041 en Development y reciben `http://api:8080/` desde Compose. PostgreSQL conserva el puerto local 5432. El detalle de ejecución vigente está en `odd/tasks/monitoreo-2026-10-08.md`.

## Evidencia histórica de validación local — 7 de octubre de 2026

La sección siguiente conserva la comprobación del esqueleto inicial anterior al primer monitoreo. Sus cifras, endpoints y pendientes corresponden exclusivamente al 7 de octubre; el estado vigente figura arriba.

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

### Límites de la validación histórica

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

Módulos funcionales acordados en la hoja `Módulos` de `docs/alcance/Calcs/Casos de Uso - Responsables.xlsm` y en la guía de arquitectura del backend:

- M01 — Administración y configuración.
- M02 — Envíos y depósito.
- M03 — Planificación, flota y despacho.
- M04 — Ejecución y sincronización móvil.
- M05 — Seguimiento y comunicaciones.
- M06 — Monitoreo y liquidaciones.

El Worker procesará tareas en segundo plano, mensajes de RabbitMQ, notificaciones, actualizaciones de seguimiento y procesos de liquidación.

## Persistencia y mensajería previstas

### PostgreSQL

Será la base de datos transaccional principal.

Se utilizará una única base de datos compartida con aislamiento lógico mediante RLS.

El operador es el tenant y el comercio tiene una identidad independiente. Cada envío conserva `OperadorId` y `ComercioId`; cualquier comercio puede enviar con cualquier operador registrado, sin una relación comercial previa. Las cuentas de comercio consultan sus propios envíos y las cuentas del operador los de su organización. La consulta de los comercios atendidos por un operador se derivará de los envíos cuando se implemente esa funcionalidad.

La API establecerá el contexto validado en la conexión o transacción, y PostgreSQL aplicará las políticas RLS correspondientes cuando se implemente esa segunda barrera.

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

## Flujo implementado y comunicación prevista

El flujo implementado del monitoreo es `Commerce / Backoffice → NexoRuta.Api → PostgreSQL`. Cloudflare, móvil, caché funcional y mensajería del diagrama siguiente corresponden a la arquitectura prevista.

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
