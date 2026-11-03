# NFR-07: plan de implementación de caché distribuida

Fecha: 03/11/2026. Estado: **implementada en el checkout; no desplegada**. Ver la evidencia y límites al final.

## 1. Requisito y alcance

La [card NFR-07 de Notion](https://app.notion.com/p/40a032f1caff8153a177dc1212d1d903), consultada mediante MCP, exige dos lecturas de negocio con expiración, invalidación y métricas hit/miss. La fuente local `docs/alcance/Calcs/Casos de Uso - Responsables.xlsm`, hoja **No funcionales**, fila 10, agrega que deben tener **perfiles distintos**. `Monitoreo_2026-10-08_CU.xlsx`, hoja CU 08-10, fila 13, pide que Compose incluya caché y observabilidad.

La implementación comprende:

1. Agregar caché Redis de **identidad visual del operador**, compartida por su lectura administrativa y la lectura desde Commerce.
2. Agregar caché Redis del **detalle de tarifarios publicados**, reutilizable en consulta y simulación de una misma versión.
3. Publicar métricas por caso en el **Grafana existente**, tanto local como GCP.
4. Incorporar Redis compartido al despliegue GCP y verificar uso entre las dos instancias de API.

Ambas lecturas tienen datos y consumidores propios del sistema. Las integraciones geográficas quedan fuera de la implementación: no migrar la caché local Geoapify ni cambiar su habilitación. Mapbox conserva `permanent=false` y sus resultados temporales no entran en Redis ni en otra caché. Se mantienen cuotas PostgreSQL, RLS, permisos, concurrencia optimista, B1–B5 y selección → ajuste → guardado → reapertura. No se amplía a sesiones, permisos, rate limiting, estados de envíos, cotización/admisión de envíos o tracking por token. El cálculo de una simulación se ejecuta de nuevo con sus bultos y reglas de dominio; lo reutilizado es la configuración publicada.

## 2. Diagnóstico del checkout revisado

Base de análisis: raíz `53c5d6735ec5582b7b8ec2c7a5145bbb1378876e`; backend `bb1f91b229ee97b24dc43a7567a5f1d6f48dbb24`; frontend `e584c8033faa9d93debbc2248231b8a07c4077eb`; mobile `d570ddb7c482c56070140e25fafb5a18e51cdbfa`. Árboles Git limpios al iniciar el análisis original; esta revisión modifica únicamente el plan. Estos son los SHAs realmente inspeccionados. El manifiesto Cloud contiene otros SHAs para backend/frontend: el ejecutor debe registrar los gitlinks de su checkout, sin cambiarlos para reproducir este documento.

| Área | Hallazgo y consecuencia |
| --- | --- |
| Backend | Monolito modular .NET 10; `Application` define contratos y casos, `Infrastructure` implementa persistencia/integraciones; API y Worker componen servicios. Redis debe quedar en Infrastructure. |
| Caché actual | Hay caché local Geoapify, pero no se encontró `IDistributedCache`, HybridCache ni cliente Redis en el backend. La caché local existente no forma parte de los dos casos elegidos. |
| Identidad visual | `IdentidadVisualOperadorController.cs` contiene las lecturas administrativa/pública y la escritura. Lee snapshots `VersionIdentidadVisualOperador`, inmutables y numerados por operador. Logo admitido: hasta 1 MiB. Commerce consume la lectura en `CrearEnvio.razor` y `MisEnvios.razor`, además de la gestión en Backoffice. |
| Tarifarios | `EfTarifariosRepository.VersionsQuery` carga versión → tarifas → ajustes con `Include`/`ThenInclude`. `ConsultarTarifarioUseCase.ObtenerPublicacionAsync` y `SimularTarifaUseCase` necesitan esos datos. Una publicación es inmutable; los borradores siguen siendo editables. |
| Consumidores de tarifas | `TarifarioController` expone el detalle de publicación y simulaciones. Backoffice los usa desde `PublicacionModel` y `SimularModel`. La cotización/admisión Commerce usa otro camino SQL en `TarifasAdmision`; no debe cambiarse para implementar esta caché. |
| Cobertura y territorio | `EfZonasCoberturaRepository` ya conserva el catálogo incluido y el territorio mediante `Lazy`. La consulta por coordenadas usa `Geometria.Covers` y estado/franjas activos. Su perfil de reutilización depende de repetir puntos exactos y su invalidación afecta geometría, estado y franjas. |
| Transacciones | `RlsTransactionMiddleware` confirma después del controlador y antes de entregar el cuerpo. `SaveChangesAsync` dentro del controlador **no implica commit**. |
| Telemetría | `CacheTelemetry` en `Infrastructure/Hosting/ApiTelemetry.cs` ya publica hits, misses y un gauge acumulado de ratio, solo de la caché local Geoapify. `HostingTelemetry` registra el meter `NexoRuta.Hosting`. |
| Grafana | Ya existe un panel de ratio Geoapify. El dashboard canónico es `deploy/observability/grafana/nexoruta.json`; la copia GCP debe ser idéntica. `scripts/gcp/test_delivery.py` protege esa igualdad. |
| Transporte local | API → OTLP Collector → endpoint Prometheus del Collector → scrape Prometheus → Grafana. |
| Transporte GCP | API A/B → Collector local → remote write a Prometheus en A → Grafana. Se conservan `service_name` y `node`. No hace falta introducir otra plataforma de métricas. |
| Infraestructura | Compose local contiene Redis y `ConnectionStrings__Redis`. GCP tiene dos VMs en Santiago, aplicaciones en ambas y servicios compartidos en A, pero no contiene Redis ni su conexión. |
| Operación | Demo de hasta cinco usuarios, sesiones de cuatro horas. Las dos VMs actuales consumen las 12 vCPU de cuota documentadas. Prometheus/Loki/Tempo dependen actualmente de A. |

Se leyeron `AGENTS.md`, los documentos de continuidad Cloud y `frontend/DESIGN.md`. Los documentos históricos de arquitectura no sustituyen estos hallazgos del código actual.

### Por qué estas dos lecturas

| Candidata | Valor esperado y decisión |
| --- | --- |
| **Identidad visual** | Se reutiliza entre usuarios/páginas de Commerce y Backoffice. Evita transferir y materializar repetidamente el snapshot con logo desde PostgreSQL; la versión permite invalidación precisa. **Priorizar.** |
| **Tarifario publicado** | El mismo conjunto de tarifas/ajustes sirve para múltiples consultas y simulaciones con bultos distintos. Evita repetir la carga del grafo relacional sin cachear resultados monetarios. La publicación inmutable permite una vigencia larga. **Priorizar.** |
| Catálogo territorial incluido | Ya está en memoria del proceso mediante `Lazy`; introducir una lectura remota Redis agregaría coste a ese camino sin eliminar una consulta PostgreSQL. No priorizar. |
| Cobertura por coordenadas | Coordenadas de alta cardinalidad y varias causas de invalidación. Redondear para aumentar hits puede alterar la decisión en bordes de una zona. No priorizar sin medir repetición real. |
| Listas de envíos/estado público | Mutaciones frecuentes, filtros/páginas y requisitos de frescura/revocación. Mayor superficie de invalidación y de seguridad. No priorizar. |
| Operadores disponibles/permisos | El listado de operadores es pequeño y su estado tiene que revalidarse para operar; los permisos requieren revocación efectiva. Menor beneficio inicial o mayor riesgo de obsolescencia. |

Esta prioridad se apoya en consumidores y consultas del código, no en un perfil de carga medido. T6 debe medir el camino con y sin caché sobre datos sintéticos y registrar latencia y cargas del grafo/blob evitadas. Mantener la consulta pequeña de versión/autorización es deliberado: el beneficio esperado está en las lecturas pesadas, no en eliminar todo acceso a PostgreSQL.

## 3. Dos casos y sus políticas

Los valores siguientes son parámetros iniciales de implementación; deben quedar validados y documentados, no dispersos como constantes en consumidores.

| Política | Identidad visual | Tarifario publicado |
| --- | --- | --- |
| Perfil | Snapshot con recursos de presentación potencialmente grandes, compartido entre portales. La lectura pide la marca vigente. | Configuración relacional con tarifas y ajustes; una publicación sirve para muchas simulaciones y para consulta histórica explícita. |
| Alcance inicial verificable | `GET /api/configuracion/identidad-visual` y `GET /api/operadores/{operadorId}/identidad-visual`. Constituyen un solo caso de caché. | `GET /api/configuracion/tarifas/publicaciones/{versionId}` y el snapshot usado en `POST /api/configuracion/tarifas/simulaciones` cuando la versión está publicada. Constituyen un solo caso. |
| Contenido | DTO del snapshot con operador y versión; nombre comercial, contactos públicos, colores y logo. Sin permisos ni cuenta del usuario. | DTO de la versión publicada con sus metadatos de lectura, tarifas y ajustes; importes conservados como `decimal`. Sin bultos de una solicitud ni estado vivo de las zonas. |
| Expiración absoluta | 15 min por versión. | 6 h por publicación inmutable. |
| Variación de expiración | Reducir aleatoriamente hasta 10% el TTL para repartir expiraciones; nunca extender la vigencia máxima. | Igual; sin renovación deslizante. |
| Invalidación | Consultar la versión vigente en PostgreSQL en cada lectura; una nueva versión confirmada selecciona otra clave inmediatamente. | Consultar el puntero vigente en PostgreSQL cuando el consumidor pida «vigente»; una publicación nueva selecciona otra clave. Una consulta histórica explícita conserva su versión. |
| Ausencia/error | No cachear operador/identidad inexistentes; calcular el nombre de respaldo con datos actuales. | No cachear versiones inexistentes, errores ni borradores. Verificar pertenencia y estado publicado en PostgreSQL antes del lookup. |
| Estado que sigue vivo | Existencia/estado del operador, permisos y nombre de respaldo. | Estado activo de la zona consultado en cada simulación; borradores y selección de publicación vigente. |
| Si falla Redis | Leer el snapshot de PostgreSQL con RLS. | Leer tarifas y ajustes desde PostgreSQL con RLS y ejecutar la misma simulación de dominio. |

Claves propuestas, donde `scope` separa local/demo/pruebas y `v1` identifica el formato del payload:

```text
nexoruta:<scope>:cache:v1:operator-branding:<operadorUuid>:<version>
nexoruta:<scope>:cache:v1:published-tariff:<operadorUuid>:<versionUuid>
```

Incluir operador aunque los UUID de versión sean globalmente únicos. No usar una clave mutable sin versión como `vigente`, ni incluir bultos, peso, coordenadas o usuario: el objeto reutilizable es el snapshot, no la respuesta de una solicitud concreta.

### Invalidación y transacciones, sin doble escritura insegura

Para identidad visual, consultar primero **solo la versión vigente** en PostgreSQL dentro del contexto RLS autorizado. Después buscar el DTO de esa versión en Redis; ante miss, cargar exactamente esa misma versión desde PostgreSQL. No volver a consultar «la última» para rellenar una clave de una versión anterior. Validar que operador y versión del payload coincidan con la clave.

Las escrituras de identidad y publicación tarifaria conservan su validación y concurrencia actuales y **no escriben en Redis**. Tampoco se cachea el puntero a «vigente». Así, si la transacción revierte, no queda un snapshot no confirmado publicado en caché. Un lector concurrente anterior al commit puede terminar con la versión que observó; una lectura iniciada después del commit debe seleccionar la nueva. Incluso si un lector lento rellena la clave vieja, no puede sobrescribir la nueva. Las claves viejas expiran; no hace falta borrarlas físicamente para invalidar la lectura vigente.

Para tarifas, la cabecera leída con RLS debe confirmar que `versionUuid` pertenece al operador y tiene estado `Publicada`. Después cargar esa publicación exacta desde caché/origen. Un borrador mantiene el mismo UUID al publicarse: por eso no se cachea ninguna de sus revisiones editables y no basta con comprobar solo el UUID. El estado de la zona no forma parte del payload; `SimularTarifaUseCase` debe conservar la comprobación viva de `ZonaActiva` incluso ante hit. Una publicación histórica N sigue siendo válida por su ID cuando se publica N+1: no tratarla como obsoleta ni cambiarla por la vigente.

No agregar outbox de invalidación, Pub/Sub ni callbacks al middleware para estos dos casos: la selección por versión elimina esa necesidad. No usar `FLUSHALL`, `KEYS` ni borrado masivo sobre Redis. Si un cambio futuro cachea datos mutables bajo una clave estable, deberá diseñar por separado la invalidación después del commit y su recuperación ante fallos.

## 4. Diseño de código y configuración

### Integración con las capas existentes

- Crear `backend/src/NexoRuta.Infrastructure/Caching/` para cliente, serialización, políticas, claves y acceso observado. Usar `IDistributedCache` con `Microsoft.Extensions.Caching.StackExchangeRedis`. Fijar versiones compatibles con .NET 10 y actualizar los `packages.lock.json` afectados sin actualizar paquetes ajenos. [Integración oficial ASP.NET Core](https://learn.microsoft.com/en-us/aspnet/core/performance/caching/distributed?view=aspnetcore-10.0).
- Reutilizar la conexión/multiplexer del proveedor por proceso. No crear conexiones por petición ni otro cliente Redis solo para locks. Implementar async y cierre mediante DI. [Guía del cliente](https://seredis.dev/Basics.html).
- Mantener las interfaces de negocio en Application. Para identidad, extraer una consulta pequeña `IConsultaIdentidadVisualOperador` y un DTO de lectura en `Application/Administracion`; implementarla en Infrastructure. Los controladores conservan autorización, selección de operador y mapeo a contratos HTTP propios. La extracción se limita a las lecturas: no refactorizar toda la escritura de CU-05.
- El lector de identidad debe comprobar contexto/operador permitido antes de consultar Redis. El endpoint Commerce conserva `IOperadoresRepository.ObtenerAsync` y la selección RLS del operador objetivo. Un hit nunca reemplaza esas comprobaciones. No aceptar una clave o un operador arbitrario desde una interfaz genérica HTTP.
- Para tarifas, agregar un contrato de consulta y DTOs inmutables en `Application/Tarifas`, con implementación en `Infrastructure/Tarifas`. Compartir el lector del snapshot publicado entre detalle y simulación. `ConsultarTarifarioUseCase.ObtenerPublicacionAsync`, el camino de lectura de `SimularTarifaUseCase` y el mapeo API deben consumir esos DTOs/valores de dominio; no reconstruir una entidad `VersionTarifario` vía reflexión o deserialización de sus miembros privados para satisfacer los contratos actuales.
- Conservar los comandos/entidades de borrador en el repositorio de escritura. Para simulaciones de borrador, consultar su contenido actual y mapearlo a los mismos valores de cálculo sin pasar por Redis. El cálculo publicado puede construirse con los records de dominio `TarifaCalculo`/ajustes ya existentes. Preservar `decimal`, precisión, redondeo, orden de ajustes y errores de zona inactiva/tarifa no configurada. Eliminar métodos de lectura que queden sin consumidores después del refactor, sin aliases de contratos anteriores.
- No cachear listados paginados ni la respuesta de estado que combina borrador/vigente. El endpoint de estado mantiene su selección actual en PostgreSQL; el detalle por ID y la simulación publicada son los consumidores de Redis. No modificar `TarifasAdmision` ni las funciones SQL que cotizan/admiten envíos.
- No usar caché de respuestas HTTP ni introducir L1 de resultados. El flujo de ambos casos debe llegar a Redis para que se pueda demostrar que comparten entradas entre procesos.

Configuración propuesta:

| Clave | Contrato |
| --- | --- |
| `ConnectionStrings:Redis` | Reutilizar el nombre existente; valor secreto en GCP, configuración de prueba propia en fixtures. |
| `Caching:Enabled` | Explícito: true en Compose local/GCP; false en arranques mínimos sin Redis y pruebas no relacionadas. Estar deshabilitado es `bypass`, nunca un hit/miss ficticio. |
| `Caching:Namespace` | Prefijo obligatorio con caché habilitada; distinto por entorno y por fixture. No derivarlo del usuario. |
| `Caching:OperatorBranding:TtlSeconds` | Inicialmente 900. |
| `Caching:PublishedTariff:TtlSeconds` | Inicialmente 21600. |
| `Caching:OperationTimeoutMilliseconds` | Inicialmente 500; presupuesto finito que debe comprobarse ante desconexión real. |
| `Caching:MaxEntryBytes` | Inicialmente 2 MiB; admite un logo de 1 MiB serializado en JSON/base64. |

Validar rangos al arrancar. Caché habilitada sin endpoint/namespace es error de configuración. Endpoint bien configurado pero temporalmente caído permite arrancar y servir desde el origen: separar configuración inválida de indisponibilidad operativa. No introducir aliases de nombres anteriores ni `AddDistributedMemoryCache` como sustituto silencioso.

### Fallos, concurrencia y límites

- El acceso a caché devuelve un resultado explícito: hit, miss, error o bypass; captura únicamente fallos conocidos de Redis/serialización. Los errores del origen y la cancelación del solicitante conservan su semántica.
- Usar serialización `System.Text.Json` de tipos conocidos, payload acotado y envelope con versión de formato. Rechazar entradas de caché corruptas, demasiado grandes o de otro operador/versión; observar el fallo y consultar el origen. Si el origen devuelve un snapshot válido mayor al límite de caché, servirlo sin almacenarlo; no convertir el límite de caché en un nuevo rechazo funcional. No deserializar entidades EF con tracking ni nombres de tipos proporcionados por el payload.
- Redis no controla la disponibilidad de negocio. Mantener `/health/live` y `/health/ready` con su significado actual; exponer el estado de caché mediante señales operativas separadas. No retirar una API saludable del balanceador solo porque Redis cayó.
- Aplicar timeouts cortos, reconexión del cliente y política de cola que falle rápido durante desconexión; no agregar reintentos de aplicación por cada petición. Un circuito local breve puede evitar repetir el timeout, pero debe probar apertura, recuperación y contabilización como bypass. No ocultar fallos con un `catch (Exception)` general.
- Los rellenos concurrentes del mismo snapshot confirmado son idempotentes. Si la medición lo justifica, agregar coalescencia local por clave con espera acotada, limpieza de entradas y nueva lectura de Redis al entrar; no compartir un `DbContext` scoped entre peticiones ni mantener un diccionario de semáforos que crece sin límite. No hacen falta leases/locks distribuidos para este alcance.
- Con Redis caído, ambos caminos consultan PostgreSQL con sus restricciones actuales. No introducir otra caché de resultados en memoria para ocultar la caída.
- No escribir datos mutados por una petición antes de su commit. El llenado de caché queda en los caminos de lectura de snapshots confirmados, nunca en el flujo que publica/guarda.

## 5. Métricas y Grafana

Reutilizar `NexoRuta.Hosting` y el transporte OTLP existente. Agregar `DistributedCacheTelemetry` para los dos casos elegidos. La instrumentación local Geoapify existente sigue midiendo otra caché activa del código; no renombrarla como Redis ni incluirla entre los dos casos. Mantenerla no es compatibilidad histórica: conserva observación de una funcionalidad distinta, fuera del alcance de cambio.

| Instrumento .NET propuesto | Serie Prometheus esperada | Etiquetas acotadas |
| --- | --- | --- |
| Counter `nexoruta.cache.distributed.requests` | `nexoruta_cache_distributed_requests_total` | `cache=operator_branding/published_tariff`, `result=hit/miss/error/bypass/cancelled` |
| Counter `nexoruta.cache.distributed.operations` | `nexoruta_cache_distributed_operations_total` | `cache`, `operation=get/set/remove`, `result=success/error` |
| Histogram `nexoruta.cache.distributed.operation.duration`, segundos | `nexoruta_cache_distributed_operation_duration_seconds_*` | `cache`, `operation` |

Los nombres finales deben comprobarse contra los exporters local y GCP de sus versiones fijadas; no dar por cierta la transformación de nombres solo por compilar. `node` y `service_name` provienen del recurso/Collector. No agregar direcciones, UUID de operador, claves, consultas, versiones o mensajes de excepción como etiquetas. [Buenas prácticas de instrumentación Prometheus](https://prometheus.io/docs/practices/instrumentation/).

Semántica obligatoria:

- **Hit:** primer lookup del caso devuelve un payload válido para la clave solicitada.
- **Miss:** primer lookup saludable no tiene entrada. El origen puede fallar después; sigue siendo un miss de caché.
- **Error:** el primer lookup falla por backend, timeout o payload inválido. No sumarlo también como miss.
- **Bypass:** caché deshabilitada, circuito abierto o simulación de un borrador que debe leerse del origen. **Cancelled:** cancelación antes de resolver el lookup.
- Una lectura elegible registra exactamente un resultado; detalle y simulación cuentan sus accesos al mismo caso `published_tariff`. No sumar otra decisión al seleccionar una tarifa dentro del snapshot. Las relecturas de coalescencia no suman nuevos hits/misses; sí operaciones. Un `set` fallido después de un miss registra un error de operación y no modifica el resultado original. Un operador/versión inexistente detectado antes del lookup no es miss de Redis.
- Inicializar con cero las combinaciones conocidas necesarias para consultas y alertas. No confundir falta de tráfico con falta de telemetría.

Actualizar el dashboard existente, manteniendo UID `nexoruta-observabilidad`, datasources y filtros de nodo/servicio. Agregar un filtro de caso y una fila de caché con hits/s, misses/s, porcentaje de hit, errores/bypass y latencia p95. Mostrar por separado ambos casos y un total ponderado. El ratio de una ventana se calcula a partir de contadores, **no promediando ratios de procesos**.

Ejemplo de porcentaje por caso; adaptar `$cache` al filtro y usar `100 *` para el porcentaje:

```promql
(sum by (cache) (
  rate(nexoruta_cache_distributed_requests_total{
    service_name=~"$otel_service",node=~"$node",cache=~"$cache",result="hit"
  }[$__rate_interval])
) or on (cache) (0 * sum by (cache) (
  rate(nexoruta_cache_distributed_requests_total{
    service_name=~"$otel_service",node=~"$node",cache=~"$cache",result="miss"
  }[$__rate_interval])
)))
/
sum by (cache) (
  rate(nexoruta_cache_distributed_requests_total{
    service_name=~"$otel_service",node=~"$node",cache=~"$cache",result=~"hit|miss"
  }[$__rate_interval])
)
```

Con denominador cero mostrar «Sin tráfico»; con misses y sin hits, mostrar el 0% real. Errores y bypass se muestran aparte y no mejoran ni empeoran artificialmente ese ratio. El panel debe explicar que el ratio mide reutilización; una consulta nueva legítima puede tener miss.

En `deploy/observability/prometheus/alerts.yaml`, agregar `NexoRutaDistributedCacheHitRatioLow` a partir de los nuevos contadores de ventana. Usar inicialmente un umbral orientativo de 25%, más de 20 lookups válidos en 15 min y persistencia de 10 min, **por caso**, como warning. Añadir una alerta por errores sostenidos de operaciones Redis. Las nuevas reglas no consumen el gauge local Geoapify. No exigir un hit ratio mínimo para aprobar funcionalidad ni disparar alerta por ausencia de tráfico. Agregar pruebas `promtool` para poco tráfico, ratio ponderado entre nodos, reinicio de un contador, errores y recuperación.

Editar la fuente canónica del dashboard y sincronizar la copia GCP en el mismo cambio. No crear dos fuentes editables divergentes. Identificar la fila nueva como caché distribuida; el panel Geoapify existente puede conservarse separado e identificado como caché local. Actualizar las guías local/GCP y la comprobación de igualdad existente. Verificar en navegador títulos, unidades, leyendas, filtros y estados vacíos conforme a `frontend/DESIGN.md`, usando los controles de Grafana.

Las métricas `keyspace_hits/misses` de Redis no sustituyen las de negocio: incluyen operaciones auxiliares y no separan los casos. Un exporter de Redis para memoria/evicciones es ampliación opcional; no es necesario para cerrar los hits/misses pedidos.

## 6. Redis en GCP: elección y alternativas

**Elección implementada para la demo actual: Memorystore Basic de 1 GiB**, consumido por las APIs A y B mediante el endpoint privado PSA, AUTH y TLS. Evita usar cuota de CPU de las VMs y la conexión verifica certificado y nombre del servidor. No es una conclusión universal sobre producción.

| Alternativa | Ventaja | Costo o limitación | Encaje |
| --- | --- | --- | --- |
| Redis en VM A | Sin recurso administrado adicional; se apaga junto a A. | Administración propia, punto único, certificados/autenticación y más presión sobre la VM que ya aloja servicios compartidos. | Alternativa válida si el costo persistente de Memorystore no se acepta. |
| Memorystore for Redis | Servicio administrado, red privada, AUTH y TLS. | Capacidad provisionada facturable mientras exista; el stop/guard actual apaga VMs, pero no destruye este recurso. Basic no agrega réplica. | **Opción seleccionada e implementada**; aceptar el costo persistente y presupuestarlo. |
| VM Redis dedicada | Aísla recursos de aplicación; permite su propio ciclo de encendido. | Nuevo SO, mantenimiento, monitoreo y guard de apagado; requiere resolver la cuota de cómputo actual. Sin réplica sigue siendo un punto único. | No justificada para cinco usuarios sin medir presión de recursos. |

Memorystore está disponible en `southamerica-west1`. Su costo depende de región, tier y capacidad provisionada; calcular Santiago y las horas de existencia del recurso, sin copiar el precio mostrado por defecto para Iowa. El recurso permanece y factura después de apagar las VMs; esta decisión cambia el costo residual de la demo. No se verificaron cuotas ni facturación de la cuenta en vivo. [Regiones](https://docs.cloud.google.com/memorystore/docs/redis/instances), [tiers y precios](https://cloud.google.com/memorystore/docs/redis/pricing).

### Cambios concretos implementados para la opción seleccionada

1. `infra/gcp/demo/database.tf` crea Memorystore `BASIC`, 1 GiB, Redis 7.2 sobre `PRIVATE_SERVICE_ACCESS`, con AUTH y TLS server-authentication. Reutiliza la conexión de Service Networking ya usada por Cloud SQL.
2. La versión privada del secreto runtime transporta endpoint, AUTH y CA; `scripts/gcp/vm_deploy.py` valida que el host sea privado, no imprime el secreto y genera archivos `.env` con permisos restringidos. Ambas VMs reciben el mismo endpoint.
3. `deploy/gcp/compose.yaml` configura TLS, CA, password, namespace y TTLs solo en las APIs. `monitor_agent.py` sondea el endpoint privado desde ambas VMs y publica disponibilidad.
4. La API conserva PostgreSQL como origen y fallback. No hay volumen Redis que eliminar ni datos de negocio en Redis. **La sesión stop y el guard existente no destruyen Memorystore**; el recurso permanece y factura, igual que otros servicios administrados persistentes de la demo. Retirarlo requiere una operación de infraestructura separada y deliberada.
5. No se cambió la cuota de Cloud SQL, los discos persistentes, la política de cuatro horas ni los gitlinks del backend/frontend/mobile.

El contrato de aplicación permanece independiente de esta elección; no despliega Redis en VM A en paralelo ni mantiene selector de proveedores. No reemplazar ni destruir el peering de SQL para conectar Memorystore.

## 7. Trabajo dividido para agentes

Cada tarea comienza leyendo las instrucciones vigentes y su checkout. Las rutas nuevas y nombres de tipos propuestos se acuerdan en T1. Entregar commit, archivos, decisiones, comandos/resultados y pendientes. No mezclar trabajos ni modificar gitlinks ajenos. Este documento planifica el reparto; no inicia agentes ni da por ejecutadas las tareas.

| Tarea / repositorio | Responsabilidad y archivos principales | Depende de | Entrega y aceptación |
| --- | --- | --- | --- |
| **T1 — Contrato y base / backend** | `Infrastructure/Caching/`, DI en `Persistence/DependencyInjection.cs`, opciones, paquetes/locks; contrato de métricas y DTOs de identidad/tarifario acordados. | — | Cliente compartido, claves/payload/TTL acotados, bypass explícito, fallos controlados; unitarias y fixture Redis temporal. Publicar los contratos para los otros agentes. |
| **T2 — Identidad / backend** | Consulta/DTO Application, implementación en `Infrastructure/Administracion`, controlador de identidad y pruebas CU-05. | T1 | Miss en A/hit en B; lectura por versión, aislamiento, cambio confirmado visible entre instancias, rollback/concurrencia seguros y fallback de nombre actual. |
| **T3 — Tarifario publicado / backend** | Consulta/DTOs `Application/Tarifas`, `Infrastructure/Tarifas`, `ConsultarTarifarioUseCase`, `SimularTarifaUseCase`, mapper API y pruebas de tarifas. | T1 | Un snapshot reutilizado entre detalle y simulación; borradores directos, zona activa revalidada, precisión de cálculo y selección de publicación preservadas. |
| **T4 — Telemetría y Grafana / raíz + contrato backend** | Instrumentos acordados, dashboard canónico/copia, alertas/pruebas de reglas y guías de observabilidad. | Contrato T1; validación final tras T2/T3 | Nombres exportados reales, paneles por caso, ratio ponderado y pruebas de alertas; verificación de navegador registrada. |
| **T5 — Despliegue / raíz** | `deploy/gcp/compose.yaml`, configuración Redis, `infra/gcp/demo/`, runtime/deployer/monitor, Compose local, bundle y tests Python. | Contrato de configuración T1 | Endpoint común A/B, TLS/AUTH, secretos sin fugas, configuración reconciliada, recursos/apagado conservados; validación de infraestructura sin provisión automática. |
| **T6 — Integración y evidencia / raíz + backend** | Nuevas suites, `backend/tests/ci/integration-shards.json`, workflows solo si hace falta, continuidad Cloud y procedimiento NFR-07. | T2–T5 | Pruebas reales con dos procesos y Redis, dashboard local; smoke GCP durante una sesión explícitamente iniciada. Publicar hijos antes de actualizar gitlinks del root. |

T2 y T3 pueden avanzar en paralelo después de T1. T4 y T5 pueden preparar sus archivos en paralelo con esos trabajos, en checkout/rama aislada. Un único integrador es dueño de DI/locks, contratos compartidos y gitlinks; coordinar esos archivos para evitar ediciones simultáneas incompatibles. El agente de observabilidad y el de despliegue deben coordinar cambios a Compose y guías compartidas.

No hace falta cambiar código del submódulo frontend o mobile si se mantienen los contratos HTTP. Si el análisis de implementación demuestra que deben cambiar, actualizar productores/consumidores y snapshots OpenAPI juntos, sin aliases ni adaptadores de versiones previas. Los refactors mínimos de consulta no autorizan rediseñar los portales, modificar el cálculo del dominio ni cambiar los caminos SQL de cotización/admisión.

## 8. Verificación exigida para cerrar

### Pruebas automatizadas con PostgreSQL y Redis propios

1. **Distribución real:** Redis temporal propio y dos hosts API independientes, con conexiones/cachés de proceso diferentes. Namespace único por fixture, base PostgreSQL/RLS propia y ningún `.env` de usuario. No presentar dos servicios del mismo contenedor DI como prueba suficiente de distribución.
2. **Identidad:** calentar versión N desde A; leer desde B con miss/hit comprobados; guardar N+1 y leerla desde A y B sin esperar TTL. Intercalar un lector lento de N y comprobar que no contamina N+1. Forzar rollback después de `SaveChangesAsync`: no publicar el snapshot abortado. Probar 409 y cambio de nombre del operador sin nombre comercial. Sin identidad configurada, conservar la respuesta de respaldo actual.
3. **Tarifario:** publicar una configuración sintética; detalle desde A miss y simulación de esa misma versión desde B hit. Variar bultos: el snapshot se reutiliza y el resultado se recalcula. Comparar resultados exactos con caché deshabilitada, incluidos `decimal`, ajustes, redondeo, piso cero y errores de tarifa inexistente. Probar simulación de borrador, editarlo y volver a simular sin obtener datos viejos; publicar y verificar que solo desde el commit es elegible para caché.
4. **Invalidación y estado vivo:** publicar N+1; el endpoint de estado devuelve su ID y el detalle carga esa clave sin esperar TTL. N puede seguir consultándose como histórico. Calentar el tarifario, inactivar su zona y comprobar el rechazo de simulación incluso con hit; reactivarla y comprobar recuperación. Forzar rollback de publicación y una carrera con lectores lentos. Expirar ambos casos con TTL corto real de prueba y polling acotado; un nuevo acceso debe volver al origen.
5. **Seguridad:** dos operadores con marcas/tarifarios distintos, identidades válidas/revocadas/suspendidas y comercio consultando operador inválido. Intentar leer una publicación ajena, incluso ya cacheada. Un hit nunca evita autorización/RLS. Payload de operador/versión/estado incorrectos y JSON corrupto se rechazan. Logs/labels no contienen consultas, claves, secretos ni tokens.
6. **Fallos Redis:** inaccesible al arrancar, caída durante GET/SET, recuperación sin reiniciar la API y entrada desalojada. Se consulta el origen dentro del presupuesto y se conserva su error si también falla. Probar límites de tamaño y TTL finito. No usar un Redis operativo compartido como fixture.
7. **Métricas:** `MeterListener` verifica una decisión por lectura y separación de operaciones; un Collector real verifica nombres y etiquetas en Prometheus para `operator_branding` y `published_tariff`. Las relecturas de coalescencia no inflan hits. Scrape/remote write de A/B no sobreescriben series. Reiniciar API no rompe el ratio. Un borrador es bypass; no una lectura Redis fallida.
8. **Beneficio y regresión:** medir lecturas sintéticas representativas con caché habilitada/deshabilitada; registrar latencia y consultas que materializan logos o tarifas/ajustes, diferenciándolas de las comprobaciones pequeñas que permanecen. Ejecutar suites de identidad, tarifas, simulación y admisión tarifaria. Conservar los tests del selector y B1–B5 que correspondan a los cambios de DI/hosting. No debilitar el fallo arquitectónico previo documentado para declarar verde la tarea.

`RedisTestServer` usa Testcontainers con imagen fijada por defecto. En Linux/WSL sin acceso al daemon, `NEXORUTA_TEST_REDIS_MODE=native` ejecuta un proceso Redis 7.2.16 propio, aislado en loopback y con directorio temporal; `scripts/cloud/check-nfr-07.sh` selecciona esa ruta junto con el PostgreSQL/PostGIS efímero propio. No apunta a la instancia Redis del sistema ni sustituye distribución por memoria. En Cloud con Docker se conserva `environment-install.sh` y `env-agent.sh`. El inventario de shards incorpora la clase TTL y los casos nuevos de identidad/tarifario.

### Comandos orientativos del ejecutor

La ruta estándar con Docker puede usar estos comandos:

```powershell
dotnet restore backend/NexoRuta.sln --locked-mode
dotnet build backend/NexoRuta.sln -c Release --no-restore
dotnet test backend/tests/NexoRuta.UnitTests/NexoRuta.UnitTests.csproj -c Release --no-build --no-restore --filter "FullyQualifiedName~Caching|FullyQualifiedName~Tarifas|FullyQualifiedName~IdentidadVisual"
dotnet test backend/tests/NexoRuta.IntegrationTests/NexoRuta.IntegrationTests.csproj -c Release --no-build --no-restore --filter "FullyQualifiedName~Caching|FullyQualifiedName~IdentidadVisualOperador|FullyQualifiedName~Tarifario|FullyQualifiedName~TarifaAdmision"
python -m unittest discover -s scripts/gcp -p 'test_*.py'
python scripts/gcp/validate_compose.py
tofu fmt -check -recursive infra/gcp
```

En Linux/WSL sin daemon Docker, ejecutar `scripts/cloud/check-nfr-07.sh`; instala/selecciona las fixtures nativas versionadas y corre las unitarias, arquitectura y el subconjunto de integración NFR-07. No ejecutar en ese modo sobre una base compartida.

Agregar `tofu init -backend=false` / `validate` en un directorio temporal de validación con el lock existente, sin usar estado/variables reales, y `promtool check rules` / `test rules` para las reglas nuevas. Ajustar filtros a nombres finales y confirmar que ejecutan las pruebas esperadas. La CI completa sigue siendo el gate de integración existente; este listado no la reemplaza.

### Evidencia de Grafana y GCP

- Generar tráfico sintético identificado, esperar exportación/scrape y consultar la API de Prometheus: observar hits y misses no nulos para **cada caso**. PromQL válido sin muestras no acredita la integración.
- Abrir Grafana local en navegador; comprobar filtros caso/nodo/servicio, porcentajes/unidades, paneles con datos y sin tráfico, errores y recuperación. Guardar capturas sin secretos en la ubicación de evidencias acordada. Las capturas no sustituyen los contadores observados.
- En una sesión GCP autorizada, usar un operador/tarifario de prueba identificado y dirigir solicitudes sintéticas a cada API por el canal privado existente para demostrar miss en A/hit en B y viceversa **en los dos casos**, mediante los endpoints normales del producto. El balanceador por sí solo no garantiza alternancia. Verificar el dashboard `monitor` y el remote write de ambos nodos. No se necesita proveedor externo ni un modo de simulación del transporte HTTP.
- Clasificar el informe por **compilación**, **HTTP**, **automatización**, **revisión visual** y **despliegue GCP**. Informar explícitamente las categorías no ejecutadas. No afirmar NFR-07 desplegado si solo se validó Compose o el dashboard JSON.

## 9. Criterio de cierre y secuencia de entrega

- [ ] Los dos consumidores reales usan Redis compartido; se demuestran perfiles/TTL distintos.
- [ ] Se demuestra expiración real y selección de nuevas versiones confirmadas; el histórico tarifario continúa consultable por ID.
- [ ] Ningún hit permite saltar permisos, RLS, selección del operador o comprobación viva de zona activa; los borradores no se cachean.
- [ ] Redis vacío o caído no pierde datos ni vuelve inservible la API; la simulación conserva resultados y errores del cálculo actual.
- [ ] Grafana muestra hit y miss por caso, ratio de ventana correcto y errores/bypass; alerta probada con y sin tráfico.
- [ ] Ambas APIs GCP usan el mismo endpoint privado; TLS/AUTH y actualización de configuración están verificados para la opción elegida.
- [ ] Tests/CI, documentación de operación e invalidación, y límites de evidencia acompañan los commits.
- [ ] Solo tras evidencias suficientes se propone cerrar la card; el plan no cambia su estado en Notion.

Entregar primero los commits del backend y sus pruebas; luego integrarlos por gitlink en el root junto con infraestructura y dashboard de la misma versión. El despliegue actual admite un corte coordinado: no introducir compatibilidad de releases ni revertir migraciones por este trabajo. No se prevé una migración de esquema para la caché; cualquier índice adicional necesita evidencia de consulta, no una migración especulativa.

Como salida operativa de emergencia, deshabilitar `Caching:Enabled` coordinadamente en las APIs y verificar bypass/lecturas PostgreSQL, manteniendo reglas y datos. No borrar bases, migraciones o volúmenes para recuperar el servicio.

## 10. Evidencia de la planificación original

La planificación original leyó la card, extrajo filas pertinentes de los XLSM/XLSX sin ejecutar macros e inspeccionó código/configuración/tests. La sección siguiente registra lo implementado después y diferencia los resultados ejecutados de las verificaciones bloqueadas por herramientas ausentes.

## 11. Estado de implementación y evidencia

- Backend: `DistributedCacheAccess` usa entradas versionadas, TTL absoluto con jitter y límites; Redis es opcional al arrancar, los errores de caché hacen fallback a PostgreSQL y las métricas tienen etiquetas acotadas por caso/operación. Los lectores usan snapshots DTO de identidad y tarifario; el estado del operador, autorización/RLS y zona activa permanecen consultados en vivo. Las escrituras no publican entradas antes del commit. El middleware RLS conserva la excepción primaria cuando también falla el rollback posterior a un commit diferido.
- Observabilidad: los dashboards local/GCP están sincronizados y muestran hit/s, miss/s, ratio ponderado, errores/bypass y p95. El ratio presenta 0% si hay misses pero todavía no hits; queda vacío cuando no hay tráfico. Las alertas requieren volumen suficiente y las pruebas cubren ausencia de tráfico, ratio ponderado, bajo ratio, errores y recuperación.
- Despliegue: Redis local Compose tiene memoria acotada y no se añadió persistencia; Memorystore se configura privado con AUTH/TLS en GCP. Memorystore permanece aprovisionado y factura cuando se detienen las VMs; está documentado en `infra/gcp/README.md`. No se aplicaron cambios de infraestructura ni se desplegó.
- Compilación y automatización .NET: `dotnet restore backend/NexoRuta.sln --locked-mode` pasó; la solución compila Release con 0 errores y una advertencia NU1510 sobre un paquete explícito. Pasaron las 305 pruebas unitarias y las 3 de arquitectura. El inventario dinámico descubrió 662 casos en 77 clases; el manifiesto conserva los pesos históricos y registra los casos NFR-07 de identidad (7), tarifario (6) y Redis (2: TTL y desalojo LRU). Clases sin medición histórica reciben el peso de respaldo por caso del algoritmo de shards.
- Integración HTTP/cache: pasaron los 26 casos seleccionados por `scripts/cloud/check-nfr-07.sh` en Linux/WSL, con PostgreSQL 18/PostGIS y Redis 7.2.16 efímeros propios. Incluyen dos hosts API con Redis compartido, invalidación por nueva versión, lectores lentos de identidad/tarifario, payload inválido, aislamiento/RLS, borradores, verificación viva de zonas, fallo de commit, caída/recuperación Redis, expiración TTL y desalojo LRU real. La suite no usó el daemon Docker ni la base/Redis del sistema.
- Automatización Python: `python -m unittest discover -s scripts/gcp -p 'test_*.py'` pasó con 107 pruebas y 5 omitidas. Las omisiones incluyen comprobaciones de permisos POSIX que no aplican al sistema Windows de esta sesión. `scripts/gcp/validate_compose.py` pasa con entorno sintético limpio; la validación local de `compose.yaml` también pasó con valores sintéticos, sin conectar al daemon.
- Prometheus e infraestructura: `promtool check rules` encontró 11 reglas válidas y `promtool test rules` pasó toda la suite. Como `promtool` no estaba instalado, se descargó temporalmente el binario oficial Prometheus 3.15.1 y se verificó su SHA-256 publicado antes de ejecutarlo. `tofu fmt -check -recursive infra/gcp`, `init -backend=false` y `validate` pasaron para `infra/gcp/demo` y `infra/gcp/bootstrap`.
- HTTP y Compose: los endpoints HTTP se ejercitaron en `TestServer` con Redis/PostgreSQL propios; no se levantó el stack Compose completo. Ambos manifiestos Compose validaron con valores sintéticos. No hubo smoke sobre una API/Grafana local conectadas al Collector real.
- Revisión visual: se ejecutó Grafana 13.2.3 aislado en un puerto temporal, con Prometheus y un exporter de métricas sintéticas. En navegador se comprobaron los filtros `operator_branding` y `published_tariff`, las consultas PromQL con el caso seleccionado y los paneles de hit/s, miss/s, ratio, errores/bypass y p95. Los ratios observados fueron 66.7% y 33.3%, respectivamente, bajo el tráfico sintético preparado. Esto valida la presentación e interacción del dashboard, no la emisión de métricas por las APIs. Las capturas quedaron en el directorio temporal de la sesión y no son evidencia de tráfico real.
- GCP: no se desplegó ni se consultó facturación. No se verificó en vivo la conexión TLS/AUTH de Memorystore, métricas del API exportadas por Collector/remote write ni el hit en una API GCP distinta. La integración entre dos hosts GCP y la revisión visual del dashboard desplegado siguen pendientes; no afirmar despliegue o cierre de la card hasta obtener esa evidencia.
