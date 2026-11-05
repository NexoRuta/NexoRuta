# Integración de requerimientos 31–41 en develop — 5/11/2026

Se integra la entrega parcial de bultos (31–36) y el retiro en domicilio (37–41), incluyendo las correcciones H1–H6 publicadas. El merge a develop fue autorizado expresamente por el usuario. Android nativo y el borde de tamaño de sobres/acuses Mobile para 1500/2000 bultos son pendientes no bloqueantes de esta integración. No se implementaron cambios adicionales para esos bordes, caché distribuido, banderas ni rediseños.

## Fuentes consultadas y preservadas

Se consultaron los remotos antes de integrar. La feature seguía en los commits revisados, sin avances posteriores:

| Repositorio | develop inicial | Feature integrada |
|---|---|---|
|Principal|`871626c14d2c4ef899e818b56d1cd5b5a2be4236`|`d0917509990d3c39a88e986ccc36842615e26806`|
|Backend|`39f8741a094b135fd6ac434d068029648a7c2574`|`f71b114ec0d4c0f832625e5e220befe654ad1850`|
|Frontend|`b3a61482c210eceda672c65a77211da857a9ee79`|`5190efff4d21e9a1a203915a9a57369dacfe2dae`|
|Mobile|`8a71b3f9d89f2e33a9dd4d6b078b514b29b01262`|`683766d6d8cd6c1bd9ce45bb12f6581ddb19b98c`|

El principal develop apuntaba además a Frontend `ce86c68de07ef3160fe63d2472bb5f08f039da16`, posterior al develop de ese submódulo. Se recuperó ese commit publicado y se incorporó también, conservando su actualización OpenAPI de OPT-06.

Backend conserva el fixture de carga agregado en develop y sus controles de plataforma, permisos mínimos y reintentos. El principal conserva los seis commits posteriores de develop, incluidos los scripts, workflows y configuración de carga remota. Se comprobó que los nuevos gitlinks tienen como ancestros tanto los anteriores del principal develop como la feature completa. No se alteraron main, las ramas feature ni las protecciones, y no hubo force push.

## Resultado y conflictos

| Repositorio | Integración | Commit de componente publicado |
|---|---|---|
|Backend|Merge de ambas historias, sin conflictos textuales|`09538d989399b511473ad5af063754ea76d554a6`|
|Frontend|Incorporación de ce86c68 y merge de la feature|`d328e98c27db7c5cef018ab3492c54fc563eed49`|
|Mobile|Avance directo de develop a la feature|`683766d6d8cd6c1bd9ce45bb12f6581ddb19b98c`|
|Principal|Merge de la feature sobre develop y selección explícita de los gitlinks anteriores|El SHA raíz se obtiene con `git rev-parse HEAD` del checkout integrado|

El único conflicto de contenido fue `frontend/contracts/nexoruta.openapi.json`: las URLs de servidor eran diferentes por el entorno de generación. Se conservó la URL existente en develop y se combinaron estructuralmente rutas y esquemas de ambas versiones, incluyendo OPT-06 y retiros. La comparación con la API integrada en ejecución, excluyendo únicamente `servers` como hace el workflow existente, confirmó igualdad exacta de las **121 rutas y sus esquemas**.

Los conflictos de gitlinks Backend/Frontend del principal se resolvieron con los commits integrados ya publicados; no se eligió una rama completa para descartar la otra. Mobile avanzó al commit integrado. No fue necesario cambiar código funcional para resolver regresiones del merge.

## Verificación nueva sobre el conjunto integrado

Estos resultados pertenecen a esta integración; los números de la primera implementación y de H1–H6 siguen siendo históricos en VALIDACION.md.

| Comprobación | Resultado |
|---|---|
|Build API y Worker|Cero errores; advertencia NU1510 existente|
|Build solución Frontend y demo portable|Cero errores; advertencias existentes de analizadores y CA1416|
|Unitarias focalizadas Backend|34 aprobadas: agregación, transiciones, capacidad, creación y contrato Kafka v1|
|H1H2 con PostgreSQL real|3 aprobadas: dos visitas, segunda entrega, primera fecha inmutable, motivos, plazos independientes y recálculo vial|
|C31 con PostgreSQL real|3 aprobadas: parcial permitida/prohibida, devolución, replanificación, evidencia por bulto, versión, reintento y outbox/inbox|
|C37 con un bulto|2 aprobadas: solicitud, ruta mixta, foto/firma, capacidad física, resolución, rendición, depósito/comercio; retiro fallido y reprogramación|
|Regresión de develop OPT-06|1 aprobada: fixture de carga con cuenta de privilegio mínimo y reenvíos estables/idempotentes|
|Frontend focalizado|171 aprobadas: contrato servido, creación, reglas, tarifas, rutas y seguimiento|
|Mobile portable focalizado|6 aprobadas: comandos/ViewModels offline, evidencia, reinicio, pertenencia a visita, conflicto, resolución y estabilidad del sobre|

La migración `20261105180000_IndependentParcelProofDeadlines` se ejecutó junto al resto de migraciones del Backend integrado. H1H2 crea una base en `20261105063923_SnapshotParcelsPerVisit` y aplica la actualización; C31/C37 y OPT-06 crean bases nuevas. Se preservaron las 79 migraciones y sus controles de RLS, versiones, custodia y fechas físicas. Develop no añadió migraciones divergentes en este corte.

El contrato de avisos v1 permanece sin cambios y se verifica con sus unitarias; los eventos por bulto/agregado v2 y el inbox se comprueban en C31. No se repitió el recorrido con brokers de la tarea anterior: aquella evidencia Kafka/RabbitMQ sigue identificada como histórica y el código de esos productores/consumidores se preservó sin cambios de integración.

Comandos, con el entorno de `scripts/cloud/env-agent.sh`, cachés en `/workspace`, `DOTNET_PROCESSOR_COUNT=1` y transporte vial controlado:

```bash
dotnet build backend/src/NexoRuta.Api --no-restore
dotnet build backend/src/NexoRuta.Worker --no-restore
dotnet build frontend/NexoRuta.sln --no-restore
dotnet build tests/Cambios.DemoMobile --no-restore
dotnet test backend/tests/NexoRuta.UnitTests --no-restore --filter 'FullyQualifiedName~CambiosRequerimientos|FullyQualifiedName~EnvioStateMachineTests|FullyQualifiedName~KafkaEnvioCreadoPublisherTests|FullyQualifiedName~CrearEnvioUseCaseTests|FullyQualifiedName~Capacidad'
dotnet test backend/tests/NexoRuta.IntegrationTests --filter 'FullyQualifiedName~H1H2_'
dotnet test backend/tests/NexoRuta.IntegrationTests --no-build --no-restore --filter 'FullyQualifiedName~C31_'
dotnet test backend/tests/NexoRuta.IntegrationTests --no-build --no-restore --filter 'FullyQualifiedName~C37_&DisplayName~cantidad: 1&DisplayName!~1500'
dotnet test backend/tests/NexoRuta.IntegrationTests --no-build --no-restore --filter 'FullyQualifiedName~DatosDemoFixtureCargaHttpTests'
dotnet test frontend/tests/NexoRuta.ApiClient.Tests --no-build --no-restore --filter 'FullyQualifiedName~OpenApiContractTests|FullyQualifiedName~CrearEnvio|FullyQualifiedName~OperationalRules|FullyQualifiedName~PlanificarRuta|FullyQualifiedName~Seguimiento|FullyQualifiedName~Tarifa|FullyQualifiedName~Rutas'
dotnet test mobile/tests/NexoRuta.Mobile.Application.Tests --no-restore --filter 'FullyQualifiedName~H3_|FullyQualifiedName~H4_|FullyQualifiedName~BultosConEvidenciaPersisten'
```

La comparación OpenAPI y las pruebas Frontend se ejecutaron también con `NEXORUTA_OPENAPI_URL=http://127.0.0.1:58080/openapi/v1.json`, usando el arranque aislado del workflow existente: migración/seed desactivados y conexión de base no operativa. No se usaron bases, certificados ni servicios del Windows del usuario, proveedores pagos ni datos manuales reservados. No se presenta esta ejecución HTTP como una revisión visual nueva.

Se liberaron únicamente bin/obj regenerables del clon de validación anterior, conservando sus fuentes y los volúmenes. Esta integración no tuvo suites interrumpidas por infraestructura o falta de espacio.

## Pendientes no bloqueantes

- Android nativo: no se ejecutó en esta integración. Continúa la limitación documentada de workload MAUI Android y ADB/emulador ausentes; no se acredita APK, cámara, escáner, firma ni XAML nativo.
- Sobres/acuses Mobile con 1500/2000 bultos: observación secundaria; no se abrió otra ronda de correcciones ni se usó como impedimento del merge.
- Para el recorrido manual Android: descargar una ruta sintética con dos o tres bultos; declarar entrega parcial en modo avión; completar evidencia y reabrir la app; sincronizar y ejecutar la segunda visita solo con pendientes. Repetir retiro con foto/firma, conflicto y resolución explícita, rendición, recepción en depósito y entrega al comercio.
- Estas comprobaciones no constituyen aceptación de todos los Casos de Uso ni despliegue a main.

## Publicación y verificación desde checkout limpio

El merge del principal se publicó en develop como `4ec8ecf8ba1531c97fd1dfe76065974b5561b1fb`, con los tres commits de componentes de la tabla anterior ya publicados. Se clonó desde GitHub con `git clone --depth 1 --branch develop --recurse-submodules --shallow-submodules`. Git descargó exactamente esos tres SHA y `python3 scripts/cloud/verify-gitlinks.py` confirmó su coincidencia.

No se copiaron binarios, obj, estado privado, configuración de conexión ni bases desde el checkout de trabajo; únicamente se reutilizaron SDK y cachés de paquetes del entorno. En el clon nuevo se ejecutaron:

- Build API, Worker, solución Frontend y demo portable: **cero errores**, con advertencias existentes.
- H1H2/PostgreSQL: **3 aprobadas**, incluyendo actualización de las migraciones, entrega parcial, segunda visita y plazos independientes.
- C37/PostgreSQL con un bulto: **2 aprobadas**, retiro exitoso hasta comercio y fallido/reprogramación.
- Mobile portable focalizado: **6 aprobadas**, evidencia offline, reinicio, conflicto y resolución.
- OpenAPI servido por la API integrada: coincidencia exacta de **121 rutas y esquemas**, excluyendo únicamente la URL de servidor variable por entorno; **55 pruebas de contrato aprobadas** con `NEXORUTA_OPENAPI_URL` apuntando a esa API aislada.

Al finalizar, el principal y los tres submódulos estaban limpios. Se volvieron a verificar los gitlinks. Este registro documental posterior conserva los mismos componentes y no cambia código funcional. El SHA final del principal es HEAD del commit que contiene el cierre; el informe final proporciona ese SHA completo y su enlace canónico.

**Resultado:** entrega parcial y retiro en domicilio incorporados en develop, con la historia y los avances previos preservados y el checkout integrado comprobado. La prueba manual Android y la observación secundaria sobre sobres/acuses de grandes cantidades permanecen pendientes no bloqueantes, conforme a la autorización del usuario. No se avanzó a main ni se declaran aceptados los demás Casos de Uso.
