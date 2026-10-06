# NexoRuta — Arquitectura

## Estado

Arquitectura base definida para el inicio del desarrollo.

## Decisiones principales

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

## Arquitectura lógica

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

## Persistencia

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

## Estructura de repositorios

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

## Flujo de comunicación

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

## Comando de inicio previsto

Desde la raíz del repositorio:

```bash
docker compose up -d --build
```

## Principios

- Modularidad antes que distribución física.
- Seguridad aplicada en API y base de datos.
- Procesos lentos fuera del ciclo HTTP.
- Infraestructura reproducible.
- Separación clara entre dominio, aplicación e infraestructura.
- Evolución gradual hacia componentes distribuidos únicamente si existe una necesidad real.