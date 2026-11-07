# OPT-05 — Implementación y aceptación

**Fecha:** 2026-11-07

**Estado:** implementación local lista; aceptación integrada y operativa pendiente.

**Plan:** [`docs/planes/opt-05-historial-y-analitica-nosql.md`](../../planes/opt-05-historial-y-analitica-nosql.md)
**Base de trabajo:** rama `develop`, superproyecto `d9e56ac4fc09514766a28744d8c9318f055e20d2`, Backend `8c8cffdd2a7c841857023af06dcf8d7243c9d10c`. Los cambios están locales y sin commit.

## Implementado

- Separación Application/API/Infrastructure para historial y volumen: interfaces de repositorio, casos de uso, resultados, requests/responses tipados y rutas `GET /api/operacion/historial` y `GET /api/operacion/analitica/volumen`.
- Autorización mediante `IUsuarioActual`, policy `envios.consultar`, contexto RLS existente, filtro documental de operador/comercio, límites de fechas/página/tipo, orden estable y respuesta de frescura conservadora antes/después de consultar Mongo.
- Idempotencia Mongo por `EventId`, igualdad semántica del payload sin depender del orden de propiedades, rechazo de reuso divergente, expiración original de 90 días y exclusión lógica de documentos vencidos.
- Permisos Mongo separados: la API consulta únicamente la colección de historial; el worker mantiene permisos limitados de proyección y recuperación. La lectura no intenta crear índices. Cliente singleton con límites explícitos de conexión/socket y operaciones.
- Preparación GCP con topic de tres particiones y retención validada. Roles/usuarios Mongo se reconcilian mediante un servicio temporal e idempotente sobre el volumen persistente existente; no borra datos ni requiere rotar la cuenta raíz.
- Observabilidad GCP para lag de los grupos board/history/recovery, tamaño y cantidad de documentos del historial, y alerta de retraso de la proyección.
- Las métricas HTTP ya configuradas en `ApiTelemetry` registran duración, ruta y status code para separar fallos y latencia de estos endpoints; la respuesta expone además estado de frescura.
- Pruebas unitarias y de infraestructura ampliadas. La prueba de integración Mongo ahora cubre usuario de solo lectura, orden semántico, expiración lógica, límites HTTP y aislamiento, pero no se pudo ejecutar sin Docker.

## Contrato HTTP

- Historial: `GET /api/operacion/historial?operadorId={uuid}&desde={ISO-8601}&hasta={ISO-8601}[&envioId={uuid}&tipo={tipo}&offset=0&limite=50]`.
- Volumen: `GET /api/operacion/analitica/volumen?operadorId={uuid}&desde={ISO-8601}&hasta={ISO-8601}`.
- `volumenPorTipo` cuenta eventos y no envíos únicos. Ambos contratos documentan frescura, retención y errores en [la guía del módulo](../../../backend/docs/operacion/historial-y-analitica.md).
- Errores esperados: 400 por parámetros, 401 por sesión ausente/inválida, 403 por permiso/ámbito, 503 por dependencia o ámbito actual indisponible. Las rutas usan `Cache-Control: no-store`.

## Evidencia ejecutada

| Capa | Resultado |
|---|---|
| Compilación | `dotnet build backend/NexoRuta.sln --no-restore --nologo -v minimal`: correcta, 0 errores, 3 advertencias existentes (`NU1510`, `xUnit2031`, `EF1003`). Configuración Debug/.NET 10. |
| Unitarias | `dotnet test backend/tests/NexoRuta.UnitTests/NexoRuta.UnitTests.csproj --no-build --no-restore --nologo`: 357 aprobadas, 0 fallidas. |
| Arquitectura | `dotnet test backend/tests/NexoRuta.ArchitectureTests/NexoRuta.ArchitectureTests.csproj --no-build --no-restore --nologo`: 4 aprobadas, 0 fallidas. |
| Despliegue VM | `python -m unittest discover -s scripts/gcp -p test_vm_deploy.py -v`: 26 ejecutadas, aprobadas, 1 omitida por contrato de permisos exclusivo de Linux. |
| Bundle GCP | `python -m unittest discover -s scripts/gcp -p test_delivery.py -v`: 36 aprobadas. Comprueba que se incluye el script de usuarios Mongo. |
| Script Mongo | `node --check deploy/gcp/mongo/create-operational-users.js`: sintaxis correcta. |
| Formato Terraform | No comprobado: `terraform` no está instalado en este entorno. |
| HTTP/Mongo/Kafka/PostgreSQL | No ejecutado: `docker` no está disponible. Los proyectos de integración sí compilaron. No afirmar aislamiento real, grants, índices, TTL físico, replay Kafka ni comportamiento HTTP como verificados por esta ejecución. |
| GCP | No hubo despliegue, llamada a servicios ni mutación de datos persistentes. |
| Revisión visual | No aplica: no se modificó interfaz. |

## Aceptación integrada pendiente

En un runner Linux preparado, ejecutar el filtro previsto en el plan sobre `OperationalMongoIsolationTests`, `OperationalProjectionTests`, `OperationalConsumerHealthTests` y `OperationalBootstrapTests`. Verificar además `listIndexes`, el TTL real y `explain("executionStats")` con datos sintéticos selectivos. Comprobar el rol lector con Mongo real y el provisionamiento idempotente en un volumen efímero. Mantener MongoDB 8 con la protección de kernel actual.

La preparación no ejecuta el provisionador contra GCP. En el siguiente despliegue autorizado, `prepare` del nodo A ejecuta `mongo-provisioner` después de iniciar los servicios compartidos. La colección y el volumen se conservan. Un topic operativo ya existente con retención o particiones incompatibles detendrá la preparación y requiere una decisión operativa explícita.

No se actualizó el estado de la card en Notion. Este informe no equivale a aceptación completa ni a autorización de despliegue.
