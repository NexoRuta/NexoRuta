# Análisis y optimización de CI/CD de NexoRuta

Fecha: 28/10/2026, America/Montevideo.

## 1. Resultado de la revisión

Baseline anterior a la aplicación: las pruebas de integración backend ocuparon **13 min 56 s** de una publicación de **21 min 17 s**. Un push principal iniciaba dos validaciones y cada publicación reconstruía seis imágenes sin importar qué cambió. La selección por SHAs, el paralelismo y la reutilización de digests descritos aquí son cambios locales; sus ahorros reales todavía necesitan runs posteriores.

La mejora recomendada es eliminar primero las ejecuciones redundantes, ejecutar solo los componentes afectados con una política conservadora de dependencias, y reducir el costo del backend mediante medición y distribución de sus pruebas. Después conviene mejorar las cachés y el empaquetado Docker. Paralelizar las seis imágenes tiene un beneficio acotado: su compilación sumó aproximadamente 2 min 34 s en Cloud Build.

La auditoría detectó dos condiciones de calidad: la compilación Android no bloqueaba la publicación integrada y las ramas no exigían checks exitosos. El código local ahora pone Android detrás del resultado integrado y define checks finales estables; los rulesets remotos siguen pendientes de activar tras integrar estos workflows.

El análisis inicial describía el estado previo a los cambios. Esta revisión también sigue la aplicación del plan. Los cambios locales están implementados y validados donde se indica; no se publicó nada a GitHub ni se modificaron recursos de GCP. La aplicación de rulesets y la comparación de 20 ejecuciones quedan pendientes de que los workflows lleguen a las ramas por defecto.

### Estado de aplicación del plan

| Estado | Hallazgos | Resultado local |
| --- | --- | --- |
| Implementado en código | 01, 03, 04, 06–17 | Gate Android exacto/por inputs, planificación conservadora, tres shards backend con verificación de resultados, paralelismo, lockfiles/cachés, manifiesto con digests reutilizados, pruebas OpenAPI reales, TRX y separación de workflows. |
| Instrumentado; optimización condicionada a mediciones | 05, 18 | Tiempos de fixtures y fases manuales; preparación por VM en paralelo. Las migraciones siguen aisladas y secuenciales. |
| Pendiente externo | 02, 17 | Crear rulesets para los checks finales y aplicar bootstrap para que Workload Identity Federation autorice `publish.yml` y `vm-controls.yml` antes de usarlos. |
| Pendiente de validación remota | 06 | La partición por clases usa pesos TRX y cada shard compara sus resultados con el inventario descubierto; falta un run verde en tres runners independientes. |
| Pendiente de datos de producción | Criterio de 20 ejecuciones | Reportar p50/p95, minutos de runner y aciertos de caché requiere ejecuciones en GitHub después de publicar. |

Los cambios se verifican localmente antes de integrar. La publicación, activación remota de reglas y operaciones GCP no forman parte de esta ejecución.

## 2. Alcance y fuentes de evidencia

La auditoría inicial revisó los ocho workflows que existían entonces en los cuatro repositorios, además de los scripts que resuelven fuentes, generan tags, publican imágenes y controlan VMs, los Dockerfiles usados, la preparación Android y las fixtures de integración relevantes. La implementación local añade entrypoints separados para publicar y operar VMs, y mantiene CI independiente por componente. Se consultaron por API los jobs, pasos y logs históricos de GitHub Actions, los rulesets y la configuración de protección de main. También se leyó la metadata del Cloud Build de la última publicación.

Se asume el uso actual: desarrollo con ramas develop/main, PRs, publicaciones automáticas de imágenes y controles manuales de la demo. Se busca reducir tanto el tiempo hasta obtener un resultado como los minutos de runner consumidos.

| Repositorio | Commit del checkout auditado | main remoto consultado |
| --- | --- | --- |
| NexoRuta | 1f5c92ecdfd9d94025ecacfcaee28644558bd81b | Igual al checkout |
| NexoRuta-Backend | 634cec27449c4f4736e40f629048f02908ee5730 | 2f741276bec414121675b29b10b35d15e0e41822 |
| NexoRuta-Frontend | e91c16706cadc0770630ffad67611307f91034f9 | Igual al checkout |
| NexoRuta-Mobile | 2e4c753c8531a43a36be7d36a507119652135547, con cambios locales existentes | e687541b79e4db490f76ba77ea671a94025ac83f |

En la fecha de la auditoría, los ocho archivos de workflow y la fixture PostgreSQL coincidían con main remoto. Los cambios locales posteriores ahora incluyen los lockfiles/toolchains, helper R8 mobile y workflows descritos abajo; el éxito histórico no valida estos cambios.

Los gitlinks del commit principal y el manifiesto de la última publicación apuntan a backend 2f741276…, frontend e91c1670… y mobile e687541b…. En esa publicación los inputs de ambos caminos de CI coinciden. En otros commits, el CI directo prueba los gitlinks y publicación resuelve los main actuales: la repetición de la estructura de pruebas no implica siempre igualdad de fuentes.

## 3. Estructura actual y recorrido completo

### Inventario de workflows

| Archivo | Disparadores | Trabajo principal | Relación con los demás |
| --- | --- | --- | --- |
| [Principal: ci.yml](../.github/workflows/ci.yml) | PR y workflow_call | Plan de SHAs, jobs paralelos para backend, frontend, mobile y Android, infraestructura y compatibilidad SQL | Reutilizado por publicación; el push a main no lo ejecuta por separado |
| [Principal: publish.yml](../.github/workflows/publish.yml) | Push main y repository_dispatch | CI → tag integrado → imágenes afectadas → manifiesto completo → GitHub prerelease | Cola de publicación; evita duplicar runs idénticos ya completados |
| [Principal: vm-controls.yml](../.github/workflows/vm-controls.yml) | workflow_dispatch | start/update/stop de la demo | Cola independiente; no publica imágenes |
| [Backend: ci.yml](../backend/.github/workflows/ci.yml) | PR a develop/main | Scripts Python, restore, build y tests .NET; publica TRX | La base PostgreSQL sin uso fue retirada |
| [Backend: release.yml](../backend/.github/workflows/release.yml) | Push main y manual | Notifica repository_dispatch con el SHA backend | La suite Python queda en Backend CI |
| [Frontend: ci.yml](../frontend/.github/workflows/ci.yml) | PR a develop/main | GeoJSON de backend main registrado con SHA/hash, restore, build y tests | La CI integrada valida OpenAPI contra la API del snapshot real |
| [Frontend: release.yml](../frontend/.github/workflows/release.yml) | Push main y manual | Envía repository_dispatch | El verde confirma que se envió el evento |
| [Mobile: ci.yml](../mobile/.github/workflows/ci.yml) | Push develop, PR a develop/main y manual | Cuatro suites portables, Android Release con R8 preparado y resultado estable | Push main duplicado retirado; el CI integrado conserva el gate Android |
| [Mobile: release.yml](../mobile/.github/workflows/release.yml) | Push main y manual | Notifica repository_dispatch con el SHA mobile | No declara por sí solo la validación Android |

Los entrypoints mantienen responsabilidades visibles: CI PR/reusable/manual/periódico, publicación automática y controles manuales. Los tres notify muestran componente y SHA; los checks finales tienen nombres estables.

### Flujo automático

~~~mermaid
flowchart TD
    C["Push main de un componente"] --> N["release.yml: repository_dispatch"]
    R["Push main del principal"] --> D["publish.yml"]
    R --> I["(sin CI paralelo)"]
    N --> D
    D --> V["verify: llama ci.yml"]
    V --> S["Resolver una combinación de SHAs"]
    S --> A["backend ∥ frontend ∥ mobile portable ∥ Android"]
    S --> Q["cloudsql: build API y comprobación SQL"]
    V --> F["Validación infraestructura y workflows"]
    A --> T["Tag integrado inmutable"]
    Q --> T
    F --> T
    T --> B["Cloud Build: imágenes afectadas en dos cadenas"]
    B --> M["Manifiesto completo y promoción del canal"]
    M --> G["GitHub prerelease"]
~~~

El camino automático actual no actualiza las VMs. Una ejecución manual selecciona el último manifiesto publicado y ejecuta start, update o stop; en el workflow vigente omite verify/integration/publish. Mantener esta separación operativa.

El empaquetado GCP usa [deploy/gcp/Dockerfile](../deploy/gcp/Dockerfile), copiado a los repositorios archivados por [stage_sources](../scripts/gcp/delivery.py). Optimizar solo backend/Dockerfile o frontend/Dockerfile no mejora esa publicación.

### Buenas prácticas ya presentes que deben conservarse

- Resolución de commits antes de las pruebas y publicación desde un tag que fija los tres submódulos. La publicación no vuelve a resolver sus ramas.
- Imágenes referenciadas por digest, manifiesto completo e inmutable y checksum del bundle.
- Promoción del canal mediante control de generación y orden de ejecución: una publicación vieja no reemplaza una nueva. Véase [publication.py](../scripts/gcp/publication.py).
- OIDC hacia GCP, permisos por job, entornos separados para PR y publicación, y varias acciones raíz fijadas por SHA.
- Bases efímeras de Testcontainers con credenciales y puertos propios. La comprobación cloudsql cubre roles restringidos y hosting, algo distinto de las pruebas funcionales.
- Backup, bloqueo de migraciones, drenaje, orden de aplicación y validaciones HTTP en despliegue.
- Uso de restore → build --no-restore → test --no-build en backend/frontend. No hay una segunda compilación completa implícita en esos pasos de test.

## 4. Mediciones reales

Los tiempos siguientes son el baseline histórico anterior a la implementación; no son benchmarks del código actualizado. El tiempo total incluye colas y coordinación. Los tiempos de pasos y de jobs no deben sumarse cuando corren en paralelo.

### Publicaciones automáticas exitosas

| Ejecución | Total | Job applications | Paso backend | Job publish |
| --- | ---: | ---: | ---: | ---: |
| [40625541980](https://github.com/NexoRuta/NexoRuta/actions/runs/40625541980), 28/10 | 21:17 | 15:50 | 13:56 | 4:46 |
| [40587916702](https://github.com/NexoRuta/NexoRuta/actions/runs/40587916702), 27/10 | 17:54 | 12:28 | 11:04 | 4:43 |
| [40583151786](https://github.com/NexoRuta/NexoRuta/actions/runs/40583151786), 27/10 | 15:48 | 10:24 | 9:19 | 4:38 |
| [40578988675](https://github.com/NexoRuta/NexoRuta/actions/runs/40578988675), 27/10 | 18:53 | 13:10 | 11:32 | 4:54 |

Son cuatro muestras, insuficientes para afirmar un p95 estable. Las ejecuciones anteriores también pueden usar revisiones distintas del workflow.

### Desglose de la última publicación

| Tramo | Tiempo | Lectura |
| --- | ---: | --- |
| infrastructure | 0:39 | Ya corre en paralelo; no domina el total |
| sources | 0:08 | Costo pequeño |
| cloudsql | 1:24 | Incluye 0:38 de build API y 0:33 de comprobación SQL; fuera del camino más lento |
| Paso backend | 13:56 | Restore/build/tests; integración reporta 456 casos y 13:10. Unitarias: 174; arquitectura: 3, ambas de duración interna inferior a un segundo |
| Paso frontend | 0:50 | 324 tests, duración interna de tests 0:27 |
| Paso mobile portable | 0:52 | 34 Core, 52 API, 35 Storage y 57 Application en el SHA remoto probado |
| Tag integrado | 0:05 | No es un cuello de botella |
| publish | 4:46 | Preparación, envío, espera de Cloud Build, imágenes y promoción |
| GitHub prerelease | 0:08 | No es un cuello de botella |

El CI directo del mismo push, [40625541965](https://github.com/NexoRuta/NexoRuta/actions/runs/40625541965), corrió simultáneamente y fue cancelado después de 8:05. Sus jobs consumieron aproximadamente 9:53 de tiempo agregado de runner antes de cancelar. Esto demuestra trabajo repetido real; no equivale a 8 minutos adicionales en serie dentro de la publicación.

### Cloud Build

Build consultado: e5534710-40ff-49f0-a30a-7d93bd648336, vinculado al [manifiesto de integración](https://github.com/NexoRuta/NexoRuta/releases/tag/integration-40625541980-1).

| Medida | Tiempo aproximado |
| --- | ---: |
| Creación → inicio, espera de servicio | 0:51 |
| Ejecución de las seis compilaciones | 2:34 |
| Push de imágenes | 0:24 |
| API / Worker / Admin / Backoffice / Commerce / Tracking | 0:50 / 0:32 / 0:14 / 0:21 / 0:20 / 0:17 |

Las marcas de tiempo confirman que una imagen comienza al terminar la anterior. Incluso con paralelismo ideal y recursos ilimitados, transformar 154 segundos en unos 50 ahorraría alrededor de 104 segundos en esa muestra. En una VM compartida el ahorro será menor; la espera inicial de Cloud Build permanece.

### CI de componentes y operación manual

- [Backend PR 40441907621](https://github.com/NexoRuta/NexoRuta-Backend/actions/runs/40441907621): total 14:49; tests 13:28; inicialización del PostgreSQL declarado 0:20.
- [Frontend PR 40441910453](https://github.com/NexoRuta/NexoRuta-Frontend/actions/runs/40441910453): total 1:13; build 0:18 y tests 0:28.
- [Mobile main 39802679706](https://github.com/NexoRuta/NexoRuta-Mobile/actions/runs/39802679706): total 3:08; job Android 3:03, compilación 2:20. Sus cuatro jobs portables tardaron entre 0:21 y 0:57.
- El mismo SHA mobile e687541b… tuvo CI por push a develop y main, con dos segundos entre disparos. Un PR abierto puede añadir otra validación.
- [Arranque manual 40627574385](https://github.com/NexoRuta/NexoRuta/actions/runs/40627574385): total 15:52; job deploy 15:47. No ejecutó pruebas ni compiló imágenes. Desde el inicio de la publicación precedente hasta terminar este arranque transcurrieron 37:04; hay unos segundos de solapamiento entre ambos runs.

Por tanto, conviene medir por separado **validación**, **publicación** y **start/update/stop**. Acelerar tests no reduce los 16 minutos de ese arranque manual.

## 5. Problemas y guía de implementación

Prioridades: P0 = corregir las condiciones de calidad antes de omitir validaciones; P1 = mejora principal de rendimiento/confiabilidad; P2 = simplificación o mejora secundaria.

### 01 — P0: Android no bloquea la publicación integrada

**Estado de aplicación.** Implementado: el resultado integrado exige Android cuando cambian sus inputs de build; el APK se construye desde el SHA resuelto antes del tag.

**Problema y evidencia histórica.** [Mobile release](../mobile/.github/workflows/release.yml) despacha sin depender de [Mobile CI](../mobile/.github/workflows/ci.yml). El [CI integrado](../.github/workflows/ci.yml) solo ejecuta las pruebas portables. Publicación puede terminar correctamente aunque el código Android no compile.

**Cómo afecta.** Un cambio de permisos, XAML, Java o dependencias nativas puede producir una combinación integrada verde y seis imágenes web/backend publicadas sin un APK válido. El notify verde solo confirma el HTTP 204 del dispatch.

**Solución.** Definir un único responsable de validar Android para cada SHA mobile que se incorpora.

**Guía.** En el diseño central recomendado, ejecutar Android en el principal cuando cambia mobile o su toolchain, antes de aprobar el tag/canal. Convertir el job existente mobile en una implementación reutilizable con checkout explícito de repositorio y SHA. Si se mantiene el build en el repo mobile, esperar y verificar su resultado exitoso para ese SHA y workflow autorizado; no aceptar el último run verde de otra revisión. Quitar el push main duplicado cuando el principal ya ejecute esta misma validación.

**Comprobación.** Introducir deliberadamente un error exclusivo de Android: la publicación debe bloquearse; frontend/backend sin cambios no deben reconstruirse por ese fallo.

### 02 — P0: las ramas no exigen los checks de CI

**Estado de aplicación.** Checks finales estables implementados en los cuatro repositorios; backend/frontend aceptan PRs de ramas del mismo repo hacia develop y reservan develop → main para promoción. Pendiente externo: activar rulesets después de publicar los workflows, cuando los checks aparezcan en las ramas por defecto.

**Problema y evidencia.** La API consultada devuelve ausencia de protección clásica para main en los cuatro repositorios. El principal no tiene rulesets; backend/frontend/mobile tienen reglas activas para develop y main que solo impiden borrado y non-fast-forward. No exigen PR ni checks exitosos.

**Cómo afecta.** Es posible incorporar cambios sin esperar el CI. Una estrategia de reutilización de resultados de componentes sería insegura si supone que main siempre está validado.

**Solución.** Requerir un check final estable y PR en las ramas de integración, según el circuito de trabajo acordado.

**Guía.** Los jobs finales tienen nombres únicos (`Backend CI / result`, `Frontend CI / result`, `Mobile CI / result`, `Integrated CI / result`) y backend/frontend aceptan validación previa hacia develop. En Settings → Rules → Rulesets, exigir esos checks y PR; revisar permisos de bypass. Trasladar la política de ramas a rulesets, en vez de fallar después de iniciar el runner.

**Comprobación.** Un check fallido debe impedir el merge. Un cambio documental clasificado correctamente debe terminar con el check final exitoso, sin quedar pendiente. [Referencia de protección y nombres de checks](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches).

### 03 — P1: un push al principal ejecuta dos CI

**Estado de aplicación.** Implementado: ci.yml ya no escucha push main; publish.yml es el único disparador de CI de publicación.

**Problema y evidencia histórica.** [ci.yml](../.github/workflows/ci.yml) escuchaba push main; [publish.yml](../.github/workflows/publish.yml) escucha el mismo push y vuelve a llamar a ci.yml en verify. La pareja de runs 40625541965/40625541980 confirma la duplicación.

**Cómo afecta.** Repite infraestructura, builds, bases y suites; consume runners y puede alargar colas. Cancelar a mano el run extra no recupera lo ya consumido.

**Solución.** Conservar PR + workflow_call en ci.yml y dejar que publicación sea el único punto de entrada automático en main.

**Guía.** Retirar únicamente el trigger push main de ci.yml. Mantener verify como requisito de integración/publicación. Revisar los checks requeridos para PR antes de renombrarlos. Documentar que PR valida la combinación propuesta y main valida/publica su combinación resuelta.

**Comprobación.** Un push main crea una sola familia de jobs de validación. Un PR sigue validándose y un fallo de verify impide publicar. No esperar una reducción del 50% del tiempo individual: gran parte de la duplicación corría en paralelo.

### 04 — P1: no se seleccionan componentes ni imágenes por cambios

**Estado de aplicación.** Implementado: el plan fail-closed clasifica los SHAs y devuelve suites/imágenes afectadas; baseline dudoso selecciona todo.

**Problema y evidencia histórica.** El flujo anterior ejecutaba siempre los tres componentes y construía siempre los seis servicios. El clasificador actual valida repositorio/SHA del dispatch y selecciona componentes e imágenes a partir de diffs y del último manifiesto completo.

**Cómo afecta.** Un cambio solo de mobile o frontend vuelve a pagar los 9–14 minutos del backend. Un cambio de mobile genera seis imágenes que no contienen la app móvil.

**Solución.** Añadir un plan de ejecución calculado sobre SHAs completos y dependencias reales; conservar resultados y digests de componentes que no cambiaron.

**Guía.** Resolver los tres SHAs una sola vez. Compararlos con el último manifiesto exitoso y comparar también sus inputs de infraestructura/toolchain. Para cambios del principal, leer sus gitlinks: un submódulo cambiado aparece como backend, frontend o mobile, no como todos sus archivos internos. Para dispatch, validar la allowlist de repositorios y el SHA; calcular el diff dentro de ese repositorio. Ante baseline ausente, historia insuficiente o clasificación incierta, ejecutar todo. Aplicar la matriz de la sección 6.

La salida sources debe pasar de [jobs.applications.outputs](../.github/workflows/ci.yml) a jobs.sources.outputs antes de permitir omitir applications. El manifiesto debe seguir conteniendo seis digests válidos; reutilizar los anteriores donde no haya cambios, con su procedencia.

**Comprobación.** Un cambio mobile puro no ejecuta toda la integración backend ni Cloud Build web. Un cambio de API/migración sí dispara la cobertura transversal correspondiente.

### 05 — P1: la preparación de integración backend repite trabajo costoso

**Estado de aplicación.** Instrumentado: la fixture mide inicio del contenedor, verificación, creación de base y migraciones. La plantilla PostgreSQL sigue diferida hasta validar el beneficio y las garantías de ownership/RLS.

**Problema y evidencia.** [PostgresFixture](../backend/tests/NexoRuta.IntegrationTests/Fixtures/PostgresFixture.cs) crea una base y ejecuta MigrateAsync en cada preparación. El conteo estático local encuentra 50 clases con esa fixture, 234 puntos de llamada y 57 migraciones; no son conteos de ejecuciones reales. Cada clase arranca su propio contenedor. Los logs señalan pruebas de territorio de 2:56 y 2:23, además de otras de 1:13 y 0:49.

**Cómo afecta.** Se repiten arranque, migraciones y preparación geográfica. El cuello está medido en integración; todavía no está medido qué porcentaje pertenece a cada tipo de preparación.

**Solución.** Medir primero sus fases y optimizar la preparación común sin compartir datos entre casos.

**Guía.** Registrar tiempos de start-container, create-database, migrate, import-catalog y cuerpo del test. Para casos funcionales que solo requieren el esquema actual, ensayar una base plantilla migrada una vez por contenedor y clonar bases aisladas. Cerrar conexiones a la plantilla antes de clonar. Dejar fuera del atajo los tests de migraciones, rollback, ownership y cambios de esquema, incluso si comienzan desde la versión actual. Probar explícitamente owners, grants, funciones y RLS en el clon: la configuración y los permisos a nivel de base no se copian automáticamente. [Restricciones de plantillas PostgreSQL](https://www.postgresql.org/docs/18/manage-ag-templatedbs.html).

**Comprobación.** Mismos tests y aserciones de seguridad; cada base sigue vacía al empezar. Una migración rota debe seguir fallando en la suite dedicada. No sustituir esta prueba por EnsureCreated ni usar la base de desarrollo.

### 06 — P1: toda la integración backend queda en un solo runner

**Estado de aplicación.** Implementado en tres shards con balance LPT por duración de clase del TRX local (456 casos). La planificación actual asigna 146/151/159 casos y un peso histórico de 651,4 s a cada shard; las clases nuevas se asignan por cantidad de casos. Cada shard descubre los tests al ejecutar y comprueba que su TRX contiene exactamente los casos de sus clases. Falta confirmar en GitHub el éxito y tiempo de la matriz en runners independientes.

**Problema y evidencia histórica.** El job invocaba [dotnet test sobre la solución](../.github/workflows/ci.yml) sin partición entre runners. Los 456 casos de integración de la última publicación tardaron 13:10. xUnit ya puede paralelizar clases: esto no implica que todo estuviera ejecutándose secuencialmente.

**Cómo afecta.** El runner comparte CPU, RAM y Docker entre muchas fixtures. Aumentar hilos dentro de él puede empeorar la contención.

**Solución aplicada.** Ejecutar tres grupos equilibrados de integración en runners distintos, manteniendo unitarias/arquitectura como validación rápida.

**Guía aplicada.** `integration_shards.py` lee el inventario actual, distribuye clases por peso histórico, incluye automáticamente clases nuevas y valida el conteo de cada TRX contra el inventario. Cada runner conserva sus Testcontainers; la matriz inicia tres shards con concurrencia acotada y limita `DOTNET_PROCESSOR_COUNT` para no sobrecargar al runner.

**Comprobación.** La prueba de planificación local cubre inventario, asignación única y clases nuevas; el chequeo TRX rechaza huecos/duplicados por shard. El ensayo concurrente local no pudo completar por el límite de inotify compartido del host. La confirmación de cobertura ejecutada y el ahorro real queda pendiente de un run exitoso de la matriz GitHub; no se promete dividir 13 minutos entre tres porque cada runner agrega preparación.

### 07 — P1: backend, frontend y mobile se esperan en serie

**Estado de aplicación.** Implementado: backend, frontend, mobile portable y Android son jobs separados que arrancan al resolver sources.

**Problema y evidencia histórica.** El job applications ejecutaba backend → frontend → mobile. En el último run frontend/mobile agregaron 1:42 al camino posterior al backend.

**Cómo afecta.** El resultado del frontend, que podría estar listo en menos de un minuto, aparece después de unos 14 minutos. También aumenta la demora final de publicación.

**Solución.** Separar backend, frontend y mobile-portable en jobs que dependan del mismo plan/snapshot.

**Guía.** Mantener explícitos los tres jobs y un único resultado final. Para mobile portable, empezar con un job y un filtro de solución que incluya solo los cuatro proyectos de pruebas; no cargar el proyecto MAUI en este corte. Medirlo contra la matriz actual: cuatro runners para pruebas de menos de un minuto no siempre compensan su setup y colas.

**Comprobación.** Frontend/mobile comienzan al resolver sources. Los tres usan los mismos SHAs. El ahorro máximo de mover solo esos pasos ronda 1:42 en la muestra, descontando setup.

### 08 — P1: las seis imágenes de Cloud Build se compilan en serie

**Estado de aplicación.** Implementado: Cloud Build usa dos cadenas limitadas y publica solo tras completar el manifiesto requerido.

**Problema y evidencia histórica.** Los steps generados por delivery.py no tenían id ni waitFor. Sus tiempos confirman seis builds sucesivos.

**Cómo afecta.** Se suma el tiempo de cada publish .NET aunque las imágenes sean independientes.

**Solución.** Ejecutar un paralelismo limitado, con dependencias visibles.

**Guía.** Asignar ids y comenzar con dos cadenas: api → worker, y admin → backoffice → commerce → tracking. La primera de cada cadena puede comenzar al inicio. Medir luego si convienen tres grupos. Los steps comparten la máquina E2_HIGHCPU_8; poner seis waitFor de inicio no crea seis runners ni garantiza seis veces más velocidad. No cambiar el manifiesto/promoción hasta que todas las imágenes requeridas existan. [Orden y waitFor de Cloud Build](https://docs.cloud.google.com/build/docs/configuring-builds/configure-build-step-order).

**Comprobación.** Comparar duración BUILD, RAM y errores contra el baseline de 2:34. Un fallo en cualquiera de las imágenes no debe avanzar main.

### 09 — P1: Docker invalida temprano la caché y no la conserva entre builds

**Estado de aplicación.** Implementado: Docker restaura antes de copiar fuentes y usa capas inline/cache-from de digests previos; un build GCP real aún debe medir hit/miss.

**Problema y evidencia histórica.** El Dockerfile GCP copiaba todo el repo antes de dotnet publish. El comando generado no usaba caché explícita. Cada publish por aplicación vuelve a resolver/compilar sus dependencias; la caché local de la misma ejecución puede ayudar en capas comunes, pero no está preparada como caché reutilizable entre builds.

**Cómo afecta.** Cambios en documentación o archivos ajenos invalidan capas previas a restore. NuGet y compilaciones comunes se repiten en contextos nuevos.

**Solución.** Separar dependencias de código y añadir una caché de build explícita.

**Guía.** Copiar primero csproj, archivos de props/targets, NuGet.Config y lockfiles necesarios para cada grafo de referencias; ejecutar restore; copiar código y ejecutar publish --no-restore. Incluir los inputs reales de frontend: shared/portal-design.css y el GeoJSON preparado. Excluir documentación/tests del contexto de una imagen solo si no son inputs de build. Usar BuildKit con caché de registry por servicio y toolchain, o comenzar con la caché de imágenes documentada por Cloud Build. La caché de paquetes de un RUN y la exportación de capas cumplen funciones distintas.

No trasladar bin/obj desde un runner de PR hacia una imagen privilegiada sin procedencia verificable. Reutilizar outputs compilados exige igual SDK, configuración, RID y propiedades de build/publish; hacerlo es una segunda etapa.

**Comprobación.** Medir un build frío, uno idéntico y uno con un solo archivo fuente cambiado. La ausencia o pérdida de caché debe afectar solo al tiempo. [Caché Docker](https://docs.docker.com/build/cache/optimize/), [caché en Cloud Build](https://docs.cloud.google.com/build/docs/optimize-builds/speeding-up-builds).

### 10 — P1: dependencias sin caché explícita ni política uniforme de SDK

**Estado de aplicación.** Implementado: SDK fijado, lockfiles, restore locked-mode y cache NuGet por componente.

**Problema y evidencia histórica.** Los setup-dotnet no habilitaban caché y faltaban lockfiles. Ahora root, backend, frontend y mobile fijan SDK/restore con lockfiles y caché NuGet por componente.

**Cómo afecta.** Hay descargas repetidas y el entorno puede cambiar sin modificar código. La diferencia de toolchain limita reutilizar resultados entre repositorios.

**Solución.** Fijar una política de SDK y restore reproducible, luego cachear paquetes.

**Guía.** Elegir la misma revisión/política de SDK para CI y empaquetado; registrar dotnet --info. Generar y versionar lockfiles de proyectos, activar restore --locked-mode y configurar setup-dotnet con cache y cache-dependency-path de ese componente. Activar cache:true sin crear los lockfiles falla. Si se implementa primero una caché manual, su clave debe incluir OS, SDK y archivos de dependencias; no sustituye al restore. Mantener caches de paquetes separadas de bin/obj y de resultados de pruebas. [Requisitos de setup-dotnet](https://github.com/actions/setup-dotnet#caching-nuget-packages).

**Comprobación.** Un segundo run muestra hit y reduce restore; cambiar un paquete invalida la clave apropiada. Comparar el costo de descargar la caché con el ahorro antes de guardar workloads Android de gran tamaño.

### 11 — P1: falta cancelación selectiva y la cola manual puede reemplazar solicitudes

**Estado de aplicación.** Implementado: cancelación limitada a PR; publish y control manual tienen colas separadas con `queue:max`. El ID del Cloud Build queda persistido y resumido; interrupción/timeout del script y una limpieza `always()` cancelan el build remoto si sigue activo.

**Problema y evidencia histórica.** Los CI de PR no tenían concurrency y un grupo manual conservaba solo una ejecución pendiente. Ahora los PR cancelan revisiones obsoletas; publish.yml y vm-controls.yml tienen grupos separados con queue:max.

**Cómo afecta.** Se siguen testeando revisiones obsoletas y, en una ráfaga de operaciones manuales, puede desaparecer una solicitud aún no ejecutada. Cancelar la espera de GitHub después de gcloud builds submit --async tampoco implica cancelar ese Cloud Build.

**Solución.** Cancelar únicamente validación obsoleta; conservar la exclusión y el orden seguro de publicación/despliegue. La publicación consulta el estado del build por ID y cancela builds sin terminar tras error o cancelación del job.

**Guía.** Usar grupo por workflow y PR/ref con cancel-in-progress:true en CI de validación. No aplicar esa política a migraciones o promoción a mitad de operación. Para controles manuales, configurar explícitamente una cola que conserve solicitudes pendientes; la documentación vigente ofrece queue:max. Actualizar/verificar el actionlint fijado antes de usar nueva sintaxis. Mostrar qué operación está activa y pendiente, sin prometer orden FIFO si no se implementa. Si se permite cancelar publicación, agregar cancelación explícita del build remoto y limpieza por su build_id.

**Comprobación.** El ID de build queda disponible para seguimiento y los tests locales verifican registro/cancelación; falta ensayar cancelación real en GCP. El CAS sigue impidiendo promover un manifiesto incompleto. Las colas y cancelación de PR siguen sujetas a verificación posterior en GitHub. [Semántica vigente de concurrency y queue](https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax#concurrency).

### 12 — P1: distintos eventos pueden publicar la misma combinación

**Estado de aplicación.** Implementado para eventos serializados: después de cada publicación la planificación vuelve a comparar contra el manifiesto completo y omite el mismo snapshot; un fallo parcial no aporta evidencia.

**Problema y evidencia histórica.** Cada componente enviaba repository_dispatch y el principal publicaba con su propio push. Cada run genera un tag y release nuevos, aunque al resolver main obtenga los mismos SHAs que otro evento.

**Cómo afecta.** Integrar varios componentes o actualizar gitlinks cerca de sus merges puede repetir toda la validación y las seis imágenes. El candado de concurrencia serializa trabajo; no deduplica combinaciones.

**Solución.** Identificar la combinación y sus inputs de pipeline antes del trabajo caro.

**Guía.** Calcular una huella de root SHA, los tres SHAs y la versión/configuración efectiva del pipeline. Bajo una exclusión breve, consultar si esa combinación ya tiene una publicación completa exitosa o está procesándose. Si ya existe, enlazarla; si está activa, evitar iniciar otra validación equivalente. Un run fallido o parcial nunca sirve como resultado reutilizable. Para eventos atrasados, decidir y documentar si se procesa el SHA notificado o si se agrupan cambios resolviendo los últimos main; el comportamiento actual es el segundo.

**Comprobación.** Dos notificaciones de la misma combinación producen una publicación. Cambiar un SHA o un input de build obliga a revalidar. Mantener el control CAS y publication_order del canal.

### 13 — P1: la integración no conecta todos los inputs de productor y consumidor

**Estado de aplicación.** Implementado en integración: los tests frontend leen el OpenAPI servido por el API construido desde el SHA resuelto; el GeoJSON informa SHA y checksum.

**Problema y evidencia histórica.** El CI frontend fijaba un SHA backend para GeoJSON y los tests OpenAPI leían solo el snapshot local. Ahora la CI de frontend registra SHA/hash del asset y la integración compila/arranca el API del snapshot exacto, pasando NEXORUTA_OPENAPI_URL a los tests de contrato.

**Cómo afecta.** El CI puede aprobar un consumidor frente a un snapshot antiguo, o generar assets diferentes entre CI aislado y empaquetado. Ejecutar dos suites independientes no prueba por sí mismo el contrato entre esos binarios.

**Solución.** Mantener pruebas locales rápidas y añadir una comprobación pequeña del contrato real de la combinación.

**Guía.** En integración, arrancar la API del SHA resuelto con configuración efímera y usar NEXORUTA_OPENAPI_URL para los tests existentes; comparar también el snapshot versionado con el contrato servido. Hacer explícito el SHA/hash del asset canónico usado por frontend. Cuando ese asset cambie, invalidar Backoffice aunque el SHA frontend no cambie. Agregar un smoke de arranque/health de imágenes antes de promover, sin repetir toda la suite dentro de cada contenedor.

**Comprobación.** Cambiar una ruta/DTO de la API sin actualizar el consumidor debe fallar. Cambiar el GeoJSON debe reconstruir/probar Backoffice. Una imagen que compila pero no arranca no debe convertirse en la última publicación válida.

### 14 — P1: el build Android de CI difiere de la distribución actual

**Estado de aplicación.** Implementado en CI mobile y central: R8 se prepara con el helper versionado y se conserva checksum del APK de verificación. El build local exacto de Release Android generó el APK. Emitió XA0141 para tres bibliotecas nativas de Mapbox 1.8.0 sin alineación de 16 KB; actualizar el paquete cuando el proveedor publique binarios compatibles y validar el APK nativo según [la guía de Android](https://developer.android.com/guide/practices/page-sizes). La distribución Firebase/firma sigue siendo un flujo distinto.

**Problema y evidencia histórica.** apk-distribucion.sh preparaba R8 9.1.31 con SHA-256 pero el job Android no lo hacía. Ahora CI portable y root usan el helper R8 del mismo SHA cuando existe. El helper R8 existe en el checkout más nuevo y no en main mobile auditado. El APK de verificación tampoco pasa configuración Firebase ni el destino GCP que usa distribución.

**Cómo afecta.** La corrección de toolchain local puede no llegar al CI. Un APK de verificación verde no demuestra que el artefacto de distribución tenga configuración de backend, Firebase y firma válidas. No se atribuye un fallo nuevo al CI actual: el último éxito corresponde al SHA antiguo.

**Solución.** Compartir la preparación real de toolchain y distinguir verificación de distribución en los nombres y artefactos.

**Guía.** Incorporar el helper y la propiedad R8 al build que procese el nuevo SHA, usando un paso común local al repo para CI/distribución. Mantener SDK/JDK/workload y configuración efectiva visibles. El build de PR puede producir un APK de verificación sin secretos; el build de distribución debe usar el origen correcto, configuración Firebase y clave de firma en un entorno protegido. Registrar SHA de fuente, SDK/R8, destino y fingerprint público del certificado junto al checksum. No llamar distribución al APK firmado con la clave de desarrollo.

**Comprobación.** El runner local compiló con R8 9.1.31 y produjo el APK de verificación. Falta confirmar el mismo build en runner limpio y resolver/verificar las bibliotecas XA0141 antes de dar por validado Android 16; el artefacto de CI no es el de distribución.

### 15 — P1: faltan resultados y tiempos comparables de las suites

**Estado de aplicación.** Implementado parcialmente: hay TRX, resúmenes de plan/SHA y tiempos de fixtures/despliegue; hit/miss de caché y percentiles requieren runs remotos posteriores.

**Problema y evidencia histórica.** El CI integrado no conservaba TRX de backend/frontend. Ahora los cuatro repositorios guardan resultados TRX por componente/job durante 14 días y fallan si no se produce el artefacto esperado.

**Cómo afecta.** Hay que descargar logs para identificar el cuello, no se pueden equilibrar bien los grupos y es fácil confundir build, preparación de datos y ejecución de tests.

**Solución.** Crear una observabilidad mínima de la propia pipeline.

**Guía.** Separar pasos de restore/build/test, publicar TRX con nombres únicos por componente/grupo y if:always, y generar un resumen con SHAs, casos ejecutados, duración, cache hit/miss, build_id e imágenes nuevas/reutilizadas. Medir setup de fixture por separado. Guardar resultados por 7–14 días, sin datos personales ni secretos; no activar binlogs indiscriminadamente en jobs con credenciales. Hacer que falle la ausencia inesperada de resultados.

**Comprobación.** Se pueden comparar al menos 20 ejecuciones equivalentes y obtener p50/p95, esperas y minutos agregados de runner. Cada propuesta de rendimiento debe mostrar antes/después y cobertura conservada.

### 16 — P2: PostgreSQL declarado en Backend CI está sin uso

**Estado de aplicación.** Implementado: el PostgreSQL sin uso se eliminó; Testcontainers/PostGIS sigue siendo la base exclusiva de integración.

**Problema y evidencia histórica.** Backend CI levantaba postgres:18-alpine aunque la fixture usa su propio contenedor PostGIS. El servicio y NEXORUTA_TEST_POSTGRES se retiraron; las fixtures ahora registran tiempos por fase.

**Cómo afecta.** Agrega unos 20 segundos de inicialización en el run observado, memoria y una configuración engañosa que parece ser la base de integración.

**Solución y guía.** Eliminar services.postgres y NEXORUTA_TEST_POSTGRES de ese workflow. Mantener Docker y los Testcontainers; no reemplazarlos por la base compartida del servicio.

**Comprobación.** La suite sigue verde en runner limpio y no se inicia el servicio adicional. Es una mejora pequeña de bajo riesgo, apropiada para el primer cambio.

### 17 — P2: responsabilidades, convenciones y lint están dispersos

**Estado de aplicación.** Implementado: entrypoints separados, nombres de notify explícitos, actionlint en todos los repos, Dependabot para Actions/NuGet y condición OIDC de bootstrap limitada a `publish.yml`/`vm-controls.yml`. Pendiente aplicar esa condición al provider de GCP antes de ejecutar los nuevos workflows con credenciales.

**Problema y evidencia histórica.** Un solo workflow mezclaba publish y controles manuales, los notify tenían nombres ambiguos y faltaba lint/dependabot uniforme. Ahora publish y vm-controls están separados, los notify declaran componente/SHA, actionlint corre en los cuatro repositorios y Dependabot revisa las acciones/dependencias.

**Cómo afecta.** Es más difícil saber qué publica un verde, mantener flags iguales y detectar errores YAML antes del paso caro.

**Solución.** Separar por responsabilidad y reutilizar únicamente lo que deba cambiar junto.

**Guía.** Mantener ci.yml para validación reusable/PR, publish.yml para publicación automática y vm-controls.yml para start/update/stop. Renombrar el notify como Notificar integración y mostrar un run-name con componente/SHA/operación. Extraer una implementación común de jobs .NET solo si evita divergencia real; no crear una acción por cada comando de dos líneas. En reusable workflows entre repositorios, fijar la revisión del workflow y pasar repository/ref al checkout: el checkout predeterminado puede ser el repositorio llamador. Fijar acciones por SHA con comentario de versión y actualizaciones automatizadas revisables. Ejecutar actionlint en los cuatro repositorios, con versión/caché de herramienta controlada.

**Comprobación.** Una persona puede seguir el flujo desde el trigger hasta el artefacto leyendo los entrypoints. Una modificación inválida del workflow mobile falla en su CI antes de compilar Android. [Reutilización](https://docs.github.com/en/actions/how-tos/reuse-automations/reuse-workflows), [seguridad y fijación de acciones](https://docs.github.com/en/actions/reference/security/secure-use).

### 18 — P2: el arranque manual tiene otro camino crítico de unos 16 minutos

**Estado de aplicación.** Instrumentado y parcialmente optimizado: las fases del start/update/stop publican duración; los dos prepares son concurrentes. El orden de stop, migración única, apply y health se mantiene; falta ensayo en entorno GCP descartable.

**Problema y evidencia histórica.** El último start exitoso tardó 15:47 en deploy. Ahora se emiten tiempos por fase de OpenTofu, SQL, backup, SSH/preparación, drain, migración, aplicación y health. La preparación de los dos nodos corre en paralelo tras validar readiness e instalar el mismo script; stop/migrate/apply/verificación conservan su orden.

**Cómo afecta.** Mejorar tests o Docker no elimina la espera de SQL/VMs, preparación remota y checks del balanceador. Los logs actuales no permiten atribuir con precisión esos 16 minutos a cada fase.

**Solución.** Medir el recorrido manual y paralelizar solo preparación independiente.

**Guía.** Emitir duración por SQL-start, tofu init/plan/apply, backup, prepare por nodo, migrate, apply y health. Separar muestras de start frío y update caliente. Ensayar prepare de ambos nodos en paralelo, validando que no modifiquen recursos compartidos a la vez. Conservar backup, bloqueo único de migraciones, drenaje y verificaciones. Sustituir una espera fija por una condición observable solo si respeta el período real de drenaje configurado. Optimizar imágenes/pulls y artefactos locales después de medir cuánto cuestan.

**Comprobación.** Tests de control/despliegue y ensayo en entorno descartable acreditan el orden prepare → stop → única migración → apply/health; no hay escrituras concurrentes al esquema ni despliegues parciales promovidos.

## 6. Cómo ejecutar solo las pruebas necesarias

### Regla recomendada

Seleccionar **componentes y dependencias afectadas**, no solo archivos de tests modificados. Un cambio en una librería, fixture, generador, migración, contrato o configuración puede afectar muchas suites aunque no cambie ningún archivo de test.

Primera etapa: selección gruesa por backend/frontend/mobile/infra. Segunda etapa: partición de pruebas backend para paralelismo manteniendo cobertura completa. La selección fina por módulos requiere un grafo de dependencias mantenido y contrastado contra ejecuciones completas.

| Cambio detectado | Validación mínima recomendada | Empaquetado |
| --- | --- | --- |
| Solo documentación sin impacto en build/configuración | Plan y check final; lint documental si existe | Ninguno |
| Backend fuente/librerías | Unitarias, arquitectura e integración backend; contratos reales de consumidores afectados | API/Worker; portales solo si cambian inputs compartidos |
| Migraciones, RLS, hosting SQL o bootstrap | Backend completo + compatibilidad cloudsql + contratos relevantes | API/Worker y bundle; consumidores si cambia contrato |
| API/OpenAPI/identidad/reglas consumidas por web/mobile | Backend + contratos frontend/mobile y smoke de integración | Servicios afectados; no omitir consumidores por SHA idéntico |
| Frontend aislado | Suite frontend; contrato contra backend resuelto; build de portales afectados | Inicialmente los cuatro portales como grupo conservador |
| GeoJSON canónico backend | Tests de catálogo/PostGIS + Backoffice y generación del asset | Backend y Backoffice aunque frontend SHA no cambie |
| Mobile portable | Las cuatro suites portables + Android al incorporar el SHA a la combinación aprobada | APK; reutilizar las seis imágenes si sus inputs no cambian |
| Mobile Android/XAML/recursos o dependencias nativas | Android y suites portables que correspondan | APK; no reconstruir imágenes web por defecto |
| Infraestructura, scripts GCP o Compose de despliegue | Python, lint de workflows, fmt/validate, validaciones de Compose; cloudsql si toca SQL | Bundle y servicios cuyos inputs cambien |
| global.json, props/targets, lockfiles, Dockerfile o lógica de clasificación | Invalidar los componentes dependientes; primera versión conservadora: validación completa | Todos los artefactos que usen esos inputs |
| Cambio no clasificable, primer run o baseline no confiable | Validación completa | Empaquetado completo |

Las filas son acumulativas: un PR que cambia backend y mobile ejecuta la unión.

### Implementación del clasificador

1. Crear un único plan con root SHA, sources, baseline, componentes afectados, motivo de cada decisión e imágenes a construir/reutilizar.
2. Para PR del principal, comparar merge-base con la revisión propuesta e inspeccionar gitlinks. Para publicación, comparar con el manifiesto exitoso previo y resolver los main una vez.
3. Para dispatch, aceptar solo los tres repositorios conocidos y SHAs válidos de su main autorizado. No interpolar el payload directamente en shell ni permitir ejecutar workflows de un fork con secretos.
4. Descargar los commits necesarios para comparar; si fetch-depth:1 no alcanza, profundizar específicamente. No interpretar un diff fallido como ausencia de cambios.
5. Mantener reglas explícitas para archivos compartidos y contratos. El plan fallido o sin baseline debe producir ejecución completa o fallo, nunca un skip silencioso.
6. Los jobs leen ese plan y un check final verifica que cada validación requerida tuvo éxito. Si un job requerido aparece skipped, canceled o sin resultado, el check falla. Un job opcional omitido debe tener motivo explícito.
7. Antes de publicar, exigir tests vigentes para todos los componentes del snapshot, ya sean ejecutados ahora o procedentes de un resultado confiable reutilizado. La clave debe incluir fuente, toolchain, workflow y dependencias externas relevantes.

Los filtros de evento paths pueden servir para repositorios aislados, pero no resuelven por sí solos los dispatch entre repositorios ni los gitlinks. Para checks obligatorios conviene que el workflow de planificación siempre se ejecute y decida sus jobs; omitir por completo el workflow puede dejar un check pendiente. [Filtros de GitHub Actions](https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax#onpushpull_requestpull_request_targetpathspaths-ignore).

### Qué repetir y qué reutilizar

| Trabajo | Decisión |
| --- | --- |
| CI directo y CI reusable del mismo push principal/snapshot | Eliminar el duplicado |
| Mismo snapshot notificado por dos eventos | Deduplicar |
| PR probado y merge posterior | La segunda prueba puede ser necesaria: el árbol de merge puede diferir |
| Componente sin cambios entre publicaciones | Reutilizar evidencia confiable del SHA exacto y sus inputs |
| Caché NuGet | Reutilizar paquetes; ejecutar restore y pruebas cuando correspondan |
| Cloudsql frente a integración funcional | Conservar ambos donde aplique: verifican propiedades diferentes |
| Build API de cloudsql frente al de backend | Duplicado técnico pequeño y paralelo. Reusar artefacto solo si no obliga a esperar toda la suite de 14 minutos |
| Build de CI frente a publish Docker | Hay trabajo repetido, pero también otra frontera de empaquetado. Optimizar con caché o artefactos con procedencia; no borrar esa validación sin reemplazo |
| Cuatro suites portables mobile | Son proyectos diferentes con cobertura distinta; no eliminar una por compartir dependencias |
| Scripts notify de unas veinte líneas en tres repositorios | Boilerplate pequeño; no justifica por sí solo un servicio o framework de sincronización |

No se recomienda comenzar con un sistema que decide éxito a partir de “solo se modificaron estos métodos”. Para este proyecto, primero rinde más evitar backend cuando no está afectado y distribuirlo correctamente cuando sí debe ejecutarse.

## 7. Flujo implementado y pendientes

~~~mermaid
flowchart TD
    E["PR o evento de publicación"] --> P["Resolver snapshot y plan de cambios"]
    P --> I["Infra/SQL cuando corresponda"]
    P --> U["Backend rápido"]
    P --> B["Backend: unitarias + arquitectura + integración"]
    P --> F["Frontend y OpenAPI real del snapshot"]
    P --> M["Mobile portable y Android"]
    I --> Q["Resultado final: todo lo requerido verificado"]
    U --> Q
    B --> Q
    F --> Q
    M --> Q
    Q --> A{"Publicación autorizada desde main"}
    A -->|sí| D["Tag con SHAs aprobados"]
    D --> C["Construir solo imágenes afectadas con caché"]
    C --> S["Verificación de manifiesto y bundle"]
    S --> R["Manifiesto completo: nuevos + reutilizados"]
    R --> G["Promover canal y GitHub prerelease"]
    V["Control manual start/update/stop"] --> H["Usar manifiesto completo aprobado"]
~~~

El CI semanal (lunes, 08:17 UTC) y la ejecución manual del workflow integrado fuerzan el snapshot completo. Las publicaciones automáticas siguen el plan selectivo. Cada versión del clasificador está cubierta por pruebas para fallos de baseline, cambios de contrato, gitlinks, GeoJSON, mobile y cambios de infraestructura.

Un reusable workflow evita duplicar una definición; no evita ejecuciones duplicadas por distintos triggers. Las dos decisiones deben resolverse por separado.

## 8. Estado de implementación y estimaciones

Los ahorros de las muestras históricas siguen siendo estimaciones; aún no hay mediciones de la nueva pipeline en GitHub.

| Orden | Cambios | Beneficio esperado y límite | Riesgo |
| --- | --- | --- | --- |
| 1 | Hallazgos 03, 15 y 16; gate 01 | Aplicado en workflows y código; el gate Android corre antes de publicar | Bajo |
| 2 | Plan por componente, 04/12 y check final | Aplicado con baseline fail-closed, pruebas del plan, digests reutilizados y manifiesto completo | Medio; requiere seguir observando falsos skips |
| 3 | Paralelizar aplicaciones y grupos backend, 06/07 | Aplicaciones paralelas y tres shards ponderados por TRX implementados; medir el resultado de runners separados después de publicar | Medio; observar balance y minutos agregados |
| 4 | Medir/optimizar fixtures, 05 | Instrumentación aplicada; la optimización por plantillas queda condicionada a demostrar ahorro y mantener owners, permisos y RLS | Medio/alto por seguridad y aislamiento |
| 5 | Cachés NuGet/Docker y dos grupos de imágenes, 08/09/10 | Código aplicado; comparar builds fríos/repetidos y el tiempo de Cloud Build después de integrar | Medio |
| 6 | Toolchain/contratos/lectura/controles, 11/13/14/17/18 | Aplicado; reglas remotas y ensayo GCP siguen pendientes | Variable |

Objetivo de evaluación: que un cambio documental no ejecute suites ni imágenes innecesarias; que uno mobile/frontend aislado no pague toda la integración backend; y que un cambio backend siga validándose completo, con menor duración medida. Para backend completo, una meta piloto de validación de 6–9 minutos puede usarse para evaluar grupos/fixtures; **no es una predicción ni un compromiso**, y no incluye publicación o arranque manual.

Siguiente secuencia después de integrar:

1. Aplicar y revisar la actualización de `infra/gcp/bootstrap` que autoriza los paths nuevos de workflow en Workload Identity Federation.
2. Activar los rulesets con los checks finales listados en el hallazgo 02.
3. Recoger TRX y métricas de caché durante al menos 20 ejecuciones equivalentes.
4. Confirmar que los tres shards pasan y comparar duración total/minutos agregados de runner con el baseline.
5. Comparar la preparación PostgreSQL antes de considerar una base plantilla.
6. Ensayar start frío y update caliente en entorno descartable; comprobar el paralelismo de prepare sin tocar esquema ni LB en paralelo.
7. Medir builds Cloud Build fríos y repetidos antes de ampliar cadenas o cambiar la caché.

No activar las reglas de ramas ni las optimizaciones restantes de datos/performance antes de contar con los checks y evidencia que se describen arriba.

El workflow manual y el schedule semanal ejecutan todas las validaciones. Si un run selectivo omite un input que la ejecución completa detecta, corregir el clasificador e invalidar evidencia de esa versión.

## 9. Criterios de cierre

- [x] Un push principal inicia una sola validación integrada.
- [x] Los eventos idénticos se vuelven a planificar después de la publicación completa y se omiten si el snapshot/inputs ya están verificados.
- [x] Todo skip tiene motivo y el check final falla si falta una validación requerida.
- [x] Contratos, persistencia, toolchain y cambios de inputs compartidos invalidan sus suites consumidoras.
- [x] Android se compila desde el SHA resuelto cuando cambian sus inputs; un digest de inputs idéntico puede reutilizarse para cambios solo de tests/docs.
- [ ] Los rulesets impiden merge con checks fallidos; falta activarlos en GitHub después de integrar los workflows.
- [ ] Un run de la matriz confirma en GitHub la cobertura ejecutada de los tres shards y registra sus tiempos; el host local no soportó la ejecución concurrente por su límite de inotify.
- [x] Cachés NuGet/Docker ausentes afectan tiempo, no resultado; restore/build es reproducible por lockfile.
- [x] Las imágenes sin cambios conservan digest/procedencia y el manifiesto publicado está completo.
- [x] El ID del Cloud Build async se persiste; la cancelación/timeout limpia el build activo o deja su ID e instrucción explícita para cancelarlo.
- [x] Testcontainers mantiene bases aisladas; migración y roles restringidos siguen validados en la suite existente.
- [ ] Hay 20 runs equivalentes con p50/p95, minutos de runner, tiempo Cloud Build y fallos/reintentos.
- [ ] start frío, update caliente y publicación tienen baseline/objetivos separados; hay instrumentación inicial, falta el ensayo GCP.

## 10. Cómo reproducir la consulta de tiempos

Ejemplos de lectura, sin iniciar pipelines:

~~~sh
gh run list -R NexoRuta/NexoRuta --limit 20
gh api repos/NexoRuta/NexoRuta/actions/runs/40625541980/jobs
gh api repos/NexoRuta/NexoRuta/actions/runs/40625541980/logs > logs.zip
gh api repos/NexoRuta/NexoRuta/rulesets
gh api repos/NexoRuta/NexoRuta-Backend/rulesets
gh api repos/NexoRuta/NexoRuta-Frontend/rulesets
gh api repos/NexoRuta/NexoRuta-Mobile/rulesets
gh release view integration-40625541980-1 -R NexoRuta/NexoRuta
~~~

El manifiesto de release permite relacionar los SHAs, build_id y digests con los tiempos de Cloud Build. Para comparar cambios de optimización, conservar esa identidad junto al reporte de resultados.

## 11. Límites del análisis

Se inspeccionaron workflows, scripts GCP, Dockerfiles, fixtures, contratos, logs históricos, rulesets y Cloud Build. Validación local: Python GCP 101 pasaron/3 omitidas; planificador backend 3 pasaron; backend 174 unitarias + 3 de arquitectura; integración backend 456/456 en 8:47 con `DOTNET_PROCESSOR_COUNT=2` y 1.582 registros de fases de fixture en TRX; frontend 324/324 en 12 s; mobile 182 pruebas portables; compilación frontend correcta con advertencias NU1510 y CS8629; APK Release Android generado con checksum y 3 advertencias XA0141 por bibliotecas nativas Mapbox 1.8.0. El plan de shards asignó las 456 pruebas a una matriz sin huecos ni duplicados. Ejecutar tres shards a la vez en esta máquina compartida agotó el límite local de inotify, así que no se obtuvo aquí un run verde concurrente; eso debe confirmarse en los runners separados de GitHub. El smoke local del OpenAPI servido también pasó. No se ejecutaron publicaciones, builds Cloud Build ni operaciones GCP. La implementación no es todavía un benchmark de ahorro: p50/p95, hit/miss real de cachés y efectos del paralelismo deben medirse después de integrar. No se hizo una auditoría completa del código de negocio.

Las causas estructurales están respaldadas por los archivos citados; los tiempos por test y job están medidos. La distribución interna del costo de las fixtures, el beneficio de las cachés, el paralelismo óptimo y el desglose del arranque manual necesitan las mediciones propuestas. Las reglas y los tiempos remotos pueden cambiar después de la fecha de esta revisión.
