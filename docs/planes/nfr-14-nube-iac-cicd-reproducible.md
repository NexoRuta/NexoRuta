# NFR-14 — Plan de implementación y aceptación para un agente de IA

Fecha del análisis: 14/11/2026. **Estado: plan; NFR-14 no aceptado.** Este pedido autoriza elaborar el plan. No se aplicó infraestructura, no se publicó código ni se operaron las VMs para elaborarlo.

## 1. Resultado exigido y autoridad

Cerrar [NFR-14 — Nube, IaC y CI/CD reproducible](https://app.notion.com/p/40a032f1caff815bb8c7fc579b68e8b3), consultada mediante MCP de Notion. Tiene prioridad Alta y estado "In progress". Su descripción del 09/11 y edición del 10/11 no describen por completo los despliegues posteriores.

La hoja "No funcionales", fila 17, del [XLSM de alcance](../alcance/Calcs/Casos%20de%20Uso%20-%20Responsables.xlsm), leída sin ejecutar macros, identifica NFR-14, sección 6.14, M01/Todos: nube remota HTTPS; IaC reproducible, variables, secretos, CI/CD y evidencia de costo. La sección 6.14 también está transcrita en la [card NFR-13](https://app.notion.com/p/40a032f1caff81718c15f6b38911247f): servidor remoto real, certificado válido, infraestructura en código, planificación/aplicación/destrucción ejecutables, pipeline que compile/pruebe/despliegue y reconstrucción integral con un comando.

El resultado será:

1. Una combinación exacta de raíz y tres gitlinks validada por el CI integrado.
2. Sus seis imágenes y bundle publicados de forma inmutable, con procedencia verificable.
3. Un despliegue por Actions con HTTPS válido, migraciones y RLS, secretos externos y comprobaciones del sistema real.
4. Una recreación desde un proyecto de ensayo vacío, sin archivos privados del equipo ni reutilizar infraestructura de aplicación del ambiente existente.
5. Un procedimiento ejecutable de destrucción del ensayo y conservación deliberada del ambiente que contiene datos.
6. Costos estimados actualizados, gasto real observado y presupuesto verificado.

Aplicar [AGENTS.md](../../AGENTS.md) y la [continuidad Cloud](../continuidad/cloud-agent.md). El checkout seleccionado y sus gitlinks son autoridad de fuentes; [checkpoint.json](../../scripts/cloud/checkpoint.json) es histórico. Leer también codex-cloud.md antes de instalar/arrancar. En Codex Cloud usar los helpers de agent, sin depender del Windows del usuario, su .env o respaldos DPAPI.

No iniciar CU08, CU09, rediseño, Kubernetes, autoscaling, otra nube, HA de SQL, clústeres de brokers ni una reimplementación del CI. NFR-15 figura "Done" en Notion: conservar sus gates. NFR-13 continúa pendiente: una recreación correcta no acredita failover, jobs únicos o estabilidad sostenida. No repetir pruebas de fallos o carga para cerrar esta card.

## 2. Fuentes y comprobaciones de este análisis

### 2.1 Identidades

| Fuente | Identidad inspeccionada |
| --- | --- |
| Raíz del worktree | 86e234e7bc0a2be1ce8911cc186ecf0e55d628e4 |
| Backend, gitlink y checkout | 5b6f0f9f052348aed27da40ed202da953b39ea2a |
| Frontend, gitlink y checkout | 2540041ba267d8a48e6c2b8a644247134f5b47f4 |
| Mobile, gitlink y checkout | 90976706c7db6a54c06ac552811f20f04d90375e |
| main remoto observado | 27f69c62bc974deee8879374d6d14b1db051a0f6 |
| develop remoto observado después | 7c397dcd53d88d8b21011d209bf79cb642fc1f6d |

Los submódulos estaban sin inicializar; se inicializaron en los gitlinks exactos, sin avanzar ramas. El avance remoto posterior de develop solo modificaba docs/planes/nfr-12-observabilidad.md según la comparación de GitHub. No se incorporó al checkout. Revalidar estas identidades al implementar; no tomar los SHA anteriores como una instrucción para retroceder fuentes.

### 2.2 Resultados nuevos, separados por categoría

| Categoría | Resultado y límite |
| --- | --- |
| Automatización local | "python -m unittest discover -s scripts/gcp -p 'test_*.py'": 265 tests ejecutados, 257 aprobados y 8 omitidos; 0 fallidos, exit 0, Python 3.13.5/Windows. Sus operaciones de publicación/despliegue son simuladas. No son 265 validaciones GCP reales |
| GitHub | Consulta de workflows, releases, ruleset y nombres de configuración. Se verificó "Integrated CI / result" obligatorio y actualizado para main, PR obligatoria y ningún actor de bypass en el ruleset observado |
| GCP, solo lectura | Proyecto ACTIVE, billing habilitado; A/B RUNNING, n4-custom-6-16384, zonas a/b de Santiago; SQL principal RUNNABLE, PostgreSQL 18, db-g1-small, activationPolicy ALWAYS, backups automáticos/PITR deshabilitados; Memorystore BASIC de 1 GiB READY; instancia aislada de restauración NFR-13 STOPPED |
| HTTP nuevo | A las 19:56 UTC: API /live, /ready y /health; Admin/Backoffice/Commerce /ingresar; Tracking /ready; Grafana /api/health: 200 con validación TLS normal. Grafana /api/search y Mailpit /: 401 esperados sin autenticación |
| Compilación | No se compiló .NET, Android ni imágenes y no se ejecutó OpenTofu en este análisis |
| Revisión visual | No se abrió navegador ni se revisaron pantallas. HTTP 200 no acredita interacción ni revisión visual |
| Facturación | Existe presupuesto del proyecto de USD 80/mes antes de créditos, con umbrales 50/80/100 %. No se obtuvo gasto real, saldo de crédito ni fecha de vencimiento |

El [update de develop 43631884438](https://github.com/NexoRuta/NexoRuta/actions/runs/43631884438), sobre la raíz inspeccionada, terminó success a las 19:35:56 UTC. Pasaron publish_develop y deploy, incluido bootstrap, sincronización de integraciones y operación manual. Es evidencia histórica verificable de ese run; no prueba un CI integrado de ese conjunto ni una recreación desde cero.

La [última publicación main observada](https://github.com/NexoRuta/NexoRuta/actions/runs/41946941369) terminó success y corresponde a la [prerelease integration-41946941369-1](https://github.com/NexoRuta/NexoRuta/releases/tag/integration-41946941369-1), del 05/11. No confundirla con la release de develop del 14/11.

Las lecturas no modificaron GitHub/GCP ni accedieron al contenido de secretos o filas de negocio. No se comprobó la configuración de variables a nivel organización por falta de permiso; no se solicitó ampliar scopes. Sí se comprobaron repo y environment. Usar paginación al listar: una consulta inicial sin per_page=100 omitía MONITOR_ALLOWED_EMAILS.

## 3. Arquitectura que se debe conservar

### 3.1 Camino real del código

- [.github/workflows/ci.yml](../../.github/workflows/ci.yml): PRs a develop/main, ejecución manual y semanal. Resuelve los gitlinks del checkout, hace selección conservadora mediante ci_plan.py y termina en el gate "Integrated CI / result".
- [.github/workflows/publish.yml](../../.github/workflows/publish.yml): push a main; plan, tag integrado, Cloud Build, manifiesto completo y prerelease. No ejecuta tests; depende del CI previo y la protección de main. No enciende ni actualiza VMs.
- [.github/workflows/vm-controls.yml](../../.github/workflows/vm-controls.yml): operación manual. En main, start/update consumen una release publicada. En develop, start/update primero construyen los gitlinks exactos y publican el canal develop, sin CI integrado. Stop no publica.
- [integration.py](../../scripts/gcp/integration.py): tag anotado inmutable, comprobación de los tres gitlinks y prerelease. No resolver puntas de main de componentes para sustituir los gitlinks.
- [delivery.py](../../scripts/gcp/delivery.py) y [publication.py](../../scripts/gcp/publication.py): manifiesto de seis imágenes por digest, bundle con SHA-256 y promoción GCS con precondición de generación y orden de publicación.
- [bootstrap.py](../../scripts/gcp/bootstrap.py): sincroniza una fundación que ya tiene estado remoto. Rechaza estado ausente y planes con delete/replacement. No sirve como primer bootstrap.
- [setup.ps1](../../scripts/gcp/setup.ps1): primer bootstrap, migración local a GCS, WIF y escritura de variables de GitHub. Tiene supuestos que deben corregirse antes de usarlo para un segundo ambiente.
- [demo_session.py](../../scripts/gcp/demo_session.py): start/update/stop, lease de cuatro horas y lock compartido. Start aplica IaC; update no aplica la topología demo ni reinicia/amplía la sesión; stop conserva SQL encendido. El workflow sí sincroniza bootstrap antes de start/update.
- [vm_deploy.py](../../scripts/gcp/vm_deploy.py): prepare, parada de apps, migración única en A, aplicación B/A y smoke. Usa imágenes publicadas; no compila en las VMs.

El despliegue actual drena ambos nodos y detiene sus apps antes de migrar, luego admite B y A. Existe una interrupción deliberada para cambiar contratos/esquemas juntos. La documentación que promete una rotación sin corte no describe este código y debe corregirse.

### 3.2 Topología y estado persistente

OpenTofu 1.13.1; providers google/google-beta 7.46.1 y random 3.7.2, con locks versionados. Mantener versiones salvo necesidad demostrada; no hacer init -upgrade.

Dos VMs N4 de 6 vCPU/16 GiB con Hyperdisk Balanced de datos de 80 GiB por nodo; balanceador HTTPS global y certificado gestionado; cuatro portales y API; Cloud SQL privado/PostGIS/RLS; RabbitMQ/Kafka/MongoDB y parte de la observabilidad en A; Redis con AUTH/TLS en B según el runtime actual; workers existentes y correo capturado por Mailpit.

Hay además un google_redis_instance.cache declarado y un Memorystore real READY. El runtime inspeccionado apunta al Redis de B, no a ese Memorystore. No borrar ni migrar Redis dentro de esta card: inventariar ambos, demostrar el endpoint efectivo y contabilizar el recurso remanente. Su retirada requiere una decisión explícita y comprobación de dependencias de NFR-07.

Estados GCS independientes:

- bootstrap: foundation/default.tfstate.
- demo: demo/vm/default.tfstate, con prefix demo/vm.
- leases y locks existentes: conservar su coordinación, sin desbloqueos forzados.

El estado, los planes JSON, .env de VM, hosting PFX, certificados privados, firma Android y credenciales son privados. Una marca "sensitive" no los elimina del estado. Conservar versionado GCS, IAM, prevent_destroy, deletion_protection, force_destroy=false, claves de Data Protection y volúmenes.

### 3.3 Configuración existente de GitHub

El usuario confirmó que las variables/secretos están en un environment. Se verificó el environment **nexoruta-demo** del repo raíz, autorizado para main y develop:

- Variables presentes: GCP_PROJECT_ID, GCP_REGION, GCP_ZONE, GCP_STATE_BUCKET, GCP_DELIVERY_BUCKET, GCP_WORKLOAD_IDENTITY_PROVIDER, GCP_DEPLOY_SERVICE_ACCOUNT, GCP_LOAD_SERVICE_ACCOUNT, GCP_LOAD_PREPARER_SERVICE_ACCOUNT, GCP_MANAGE_DNS y MONITOR_ALLOWED_EMAILS.
- Secrets presentes por nombre: MONITOR_GOOGLE_CLIENT_ID y MONITOR_GOOGLE_CLIENT_SECRET.
- GCP_SECONDARY_ZONE no está configurada: el workflow usa explícitamente southamerica-west1-b. No es hoy un valor requerido faltante.
- No se observaron SMTP_USERNAME/SMTP_PASSWORD/GEOAPIFY_API_KEY/SUBMODULES_TOKEN. Los primeros son condicionales; Mailpit y geocodificación deshabilitada no los requieren. Los repos inspeccionados son públicos, por lo que la ausencia del token de submódulos no es por sí misma una falla.
- nexoruta-ci está separado, sin secrets observados ni credenciales de despliegue. Conservar esa separación.

Los ajustes públicos comunes SMTP_HOST/PORT/SSL/FROM y MAPBOX_PUBLIC_TOKEN vienen hoy de compose.yaml raíz, x-app-settings. Las variables específicas GCP y secretos externos vienen del environment. No duplicar valores en repository variables ni crear .env local como fuente de despliegue. Los secretos internos persistentes se generan/guardan en OpenTofu/Secret Manager; no deben cargarse todos manualmente en GitHub.

## 4. Brechas que determinan el trabajo

| ID | Hallazgo | Trabajo obligatorio |
| --- | --- | --- |
| B1 | No hay ensayo acreditado desde infraestructura de aplicación vacía; start existente reutiliza estado/datos | Crear un ensayo aislado y un comando orquestador reproducible; no destruir el ambiente actual para demostrarlo |
| B2 | database.tf fija una contraseña de demo para admin y preparador; DatosDemoSeeder.cs fija una contraseña compartida de actores que puede volver a imponer al sincronizar | Eliminar esos valores operativos del código; definir contrato único de secretos y transición deliberada de las cuentas existentes |
| B3 | integration-tags.md/requirements.md/README/project.md mezclan resolución de ramas, notificaciones, CI y topologías anteriores | Reescribir secciones vigentes según los workflows y scripts reales; conservar historial identificado como tal |
| B4 | costs.md contiene totales de una VM/SQL anterior y admite que no representan el diseño actual | Recalcular desde inventario real y obtener gasto observado, incluidos recursos siempre encendidos y remanentes |
| B5 | setup.ps1 fija environment, consulta n4-highcpu-8 y guarda/aplica planes sin el control de borrados de bootstrap.py | Parametrizar destino de forma controlada, corregir capacidad y compartir validación de planes/identidad |
| B6 | El bucket delivery elimina objetos por edad de 30 días sin restringir prefijos | Proteger canales y assets referenciados; no permitir que la última release válida pierda su bundle por inactividad |
| B7 | Parte de imágenes base/auxiliares usa tags mutables; el host usa una familia de imagen | Registrar y fijar los insumos de despliegue/build aceptados y distinguir fuente reproducible de build idéntico byte a byte |
| B8 | Los permisos del deployer incluyen roles/owner y WIF acepta dos formatos de sujeto OIDC | Registrar el riesgo y comprobar el sujeto realmente usado. No ampliar la confianza para el ensayo; retirar el formato obsoleto tras comprobar el template actual. No convertir este cierre en una auditoría IAM integral |
| B9 | Hay despliegues de develop exitosos sin CI del conjunto final | Acreditar el camino protegido de main para la candidata, sin presentar develop como una integración probada |
| B10 | delivery.py calcula android_verified_mobile_sha a partir de components.mobile_android.run; el plan por defecto de build develop lo pone true aunque no ejecute Android | Separar selección de jobs de evidencia aprobada; un build solo no puede producir una afirmación de verificación |

## 5. Orden de implementación

Cada fase termina en su gate. Si falla, conservar evidencia y corregir esa fase; no continuar con operaciones dependientes. Las rutas indicadas como nuevas son entregables futuros: no existen por el solo hecho de estar nombradas aquí.

### P0 — Fijar candidata e inventario sin modificar infraestructura

1. Leer los documentos de continuidad; comprobar git status en raíz y tres repos, gitlinks, remotos y reglas locales. Preservar cambios ajenos. Crear rama de trabajo del plan sobre la base acordada.
2. Crear docs/auditorias/nfr-14/diagnostico.md y evidencia/sources.json con SHA raíz, árbol Git raíz, tres gitlinks y HEAD reales. Registrar versiones de Python, SDK de global.json, OpenTofu y locks, sin instalar otra versión para evadir un fallo.
3. Repetir lecturas paginadas de environments/variables/secrets por nombre, ruleset de main, últimas publicaciones completas y último control de VMs. No descargar secretos.
4. Inventariar con gcloud explícitamente dirigido al proyecto: VMs, discos, SQL principal/restauración, Redis B/Memorystore, LB/IP/certificado, buckets, Artifact Registry, Scheduler/Workflows, Cloud Run de carga y presupuesto. Incluir costos de recursos históricos sin tomarlos como permiso para eliminarlos.
5. Registrar esquema aplicado, release/digests A/B, estado de lease y locks con herramientas de diagnóstico existentes, sin ejecutar subcomandos de fallo. Si hace falta acceso a datos de negocio, reemplazarlo por metadatos/recuentos estrictamente necesarios.
6. Mantener una matriz de requisitos→código→evidencia→pendiente. No convertir toda tarea pendiente de NFR-07/12/13 en requisito adicional de NFR-14.

**Gate P0:** fuentes exactas y destino identificados; ninguna divergencia de submódulos sin explicar; precondiciones del ensayo/costo anotadas. Una VM RUNNING o una release antigua no reemplaza este registro.

### P1 — Credenciales sintéticas de desarrollo

Archivos: infra/gcp/demo/database.tf; scripts/gcp/github_environment.py, vm_deploy.py, seed_demo_data.py, prepare_load_fixture.py si consume ese contrato; deploy/gcp/compose.yaml; backend/src/NexoRuta.Infrastructure/Persistence/DatosDemoSeeder.cs, inicializadores y tests que realmente consumen la contraseña.

1. Para el demo de desarrollo, el seed usa `ChangeMe123!` para los administradores y actores sintéticos, incluidos los usuarios OPT-06. No reutilizar esta contraseña en cuentas ni entornos productivos.
2. El runtime Secret Manager conserva exclusivamente configuración y secretos de infraestructura; no contiene contraseñas de usuarios sintéticos. El preparador de carga usa la contraseña del seed y `nexoruta-load-fixtures` continúa almacenando el fixture reproducible.
3. El bootstrap de plataforma es create-only para una identidad existente. Un cambio de contraseña requiere la operación administrativa explícita `platform-admin sync-demo-password`; la contraseña no se rota automáticamente al desplegar.
4. El seed general puede sincronizar actores sintéticos durante la operación manual de seed. El preparador OPT-06 actualiza las cuentas sintéticas existentes al valor uniforme y revoca sus sesiones previas.
5. Conservar endpoints, transacciones, RLS y revocación de sesiones. No pasar credenciales en query, argumentos CLI, resúmenes o evidencia pública.
6. Mantener hosting_identity.ensure y redis_identity.ensure: una versión válida existente es autoritativa; una identidad malformada debe fallar. No regenerar PFX, claves de Grafana o CA Redis para lograr un smoke verde.

Pruebas necesarias: ausencia de credencial detiene seed sin escrituras; credencial externa crea los actores y su segundo seed conserva entidades; fixture de carga independiente sigue funcionando; admin nuevo/preparador autentican con la misma credencial; transición del admin existente preserva identidad/permisos/datos y revoca sesiones; logs/error no contienen canarios secretos.

**Gate P1:** ningún valor fijo permite entrar al ambiente; contrato nuevo actualizado de punta a punta. Publicar backend antes de actualizar su gitlink raíz. No borrar migraciones ni hashes históricos para limpiar coincidencias de un scanner.

### P2 — Hacer explícitos insumos, manifiestos y retención

Archivos: deploy/gcp/Dockerfile y compose.yaml; infra/gcp/demo/main.tf y startup.sh; infra/gcp/bootstrap/delivery.tf; scripts/gcp/delivery.py, integration.py, publication.py y tests correspondientes.

1. Conservar las seis aplicaciones api/worker/admin/backoffice/commerce/tracking por digest. Mantener sources, root_sha, integration_tag cuando corresponde, build ID, bundle_sha256, image_sources, bundle_source y publication_order. No agregar un "latest" ni resolver ramas en la VM. Corregir B10: separar el plan que solicita correr Android de la prueba de que terminó aprobado. Publicaciones develop sin esa prueba deben dejar android_verified_mobile_sha y android_input_sha256 de verificación sin acreditar, y nunca alimentar el baseline main. Main debe acompañar esos campos con identidad de la evidencia real de CI o reutilizar prueba previa del mismo digest de inputs, explícitamente referenciada y validada. Actualizar ci_plan.py, writer, readers y tests juntos; no aceptar un booleano "run" como evidencia.
2. Registrar en el manifiesto el inventario de imágenes auxiliares y bases de build efectivamente aceptadas. Resolver sus digests desde registries oficiales en una actualización deliberada, fijarlos junto al tag legible y comprobar arquitectura. No inventar hashes ni mover versiones mayores de brokers para esta card.
3. Esta implementación conserva `debian-cloud/debian-12` como familia mutable y documenta que no promete identidad binaria del host. Cada preparación registra en evidencia sanitizada el Debian/kernel y las versiones efectivas de Docker/Compose/containerd/paquetes para ambos nodos. La familia se resuelve a una imagen vigente al crear el disco; no se presenta como pin inmutable. No sustituir discos N4 por pd-balanced ni iniciar una sustitución de VMs con datos como efecto lateral de documentar el límite. Cualquier pin concreto o reemplazo posterior requiere un cambio explícito y ensayo descartable.
4. Mantener locks .NET, providers y SDK; las actualizaciones de seguridad serán cambios explícitos del manifiesto. El criterio es poder reconstruir y verificar una release exacta; no prometer builds de bytes idénticos si apt o herramientas externas no están fijados.
5. Sustituir la regla genérica de 30 días de delivery por limpieza limitada a fuentes temporales bajo sources/. Conservar channels/ y releases/ durante la vida del proyecto, igual que las imágenes, para no borrar el bundle de la release que sigue publicada. Documentar crecimiento y costo. No agregar un GC de releases más complejo en esta feature.
6. Hacer que un manifiesto/imagen/bundle ausente o inconsistente falle antes de drenar nodos. Conservar selección única del canal y precondición de generación. No conservar compatibilidad con manifests viejos incompletos: actualizar productores, consumidores y fixtures juntos.
7. Documentar que start/update despliegan una release completa seleccionada una vez. No confundir assets de GitHub con la existencia comprobada de los objetos GCS.

Pruebas: manifest completo aceptado; fuente/digest/bundle alterado rechazado; falta de imagen o bundle no drena; reintento idéntico no mueve tag; publicación antigua no gana la carrera; cambio docs-only no inventa CI nuevo; ciclo de retención no alcanza canales ni releases.

**Gate P2:** una release publicada conserva todos sus insumos desplegables y su identidad; ningún test sustituye un digest inválido con una versión anterior.

### P3 — Unificar planificación y bootstrap seguro

Archivos: scripts/gcp/setup.ps1, bootstrap.py, demo_session.py, github_environment.py, un núcleo nuevo bootstrap_setup.py y test_setup.py/test_bootstrap.py/test_demo_session.py.

1. Extraer/reutilizar una comprobación común de planes: rechazar delete/replacement en el ambiente persistente antes de apply. Mantener la excepción precisa de versión de secreto con ABANDON ya admitida por demo_session; no convertirla en permiso para borrar secretos o persistencia. El primer bootstrap permite creates, no destrucción de recursos existentes.
2. Comprobar project ID/número, repo ID/owner ID, bucket y prefix antes de init/plan/apply. Un 403, timeout o fallo de red no equivale a estado ausente. Un bucket existente sin estado no autoriza adoptarlo o sobrescribir estado local.
3. Corregir la comprobación de capacidad de setup.ps1 a n4-custom-6-16384 en ambas zonas y cuotas reales. Mantener requisito de 12 vCPU, discos Hyperdisk y región. Reusar capacidades de prueba existentes; no levantar VMs para testear el validador.
4. Separar primer bootstrap de sincronización: extraer el núcleo de primer setup a bootstrap_setup.py, invocable desde Python en Linux/Windows, y hacer que setup.ps1 delegue en él. Reusar controles de plan/estado; no mantener dos implementaciones diferentes. Admitir destino público explícito de repo, project ID, environment y workflows WIF permitidos; no aceptar un nombre arbitrario sin validarlo contra el perfil de ejecución. Usar project explícito en CLI y evitar cambiar la configuración global de gcloud del usuario. setup crea fundación y migra su estado; bootstrap.py exige la fundación remota. No agregar un fallback automático de bootstrap.py a "crear todo" al fallar una lectura. La migración de un estado local propio al bucket recién creado es válida; no confundirla con adopción de un estado remoto ajeno.
5. Encapsular inputs/plan/state local transitorio en directorio privado; no subirlos como artifacts. Guardar únicamente resumen permitido: direcciones, tipo de acción, conteos, identidades públicas y hash del plan. El JSON crudo de tofu show puede revelar secretos aunque la consola los oculte.
6. Comprobar el template OIDC del repo mediante API y mantener solo el sujeto actual con IDs inmutables, junto a repo/owner IDs, ref, event y workflow exactos. Antes de retirar la variante antigua, ensayar la condición y conservar un procedimiento administrativo de reparación de WIF. No desactivar validaciones para desbloquear un job.
7. Documentar roles/owner existente en el módulo compartido. Reutilizar ese módulo no debe añadir permisos del deployer sobre la organización, la cuenta de facturación o el proyecto principal: su alcance en el ensayo termina en su proyecto. La creación/vinculación de proyectos y presupuesto usa una identidad administrativa de preparación separada del runtime/deployer. La reducción de owner exige inventariar permisos y probar todo el ciclo, incluido bootstrap; si se aborda, hacerlo primero en el ensayo y luego en un cambio acotado del principal. No afirmar que se aplicó mínimo privilegio si se conservó el rol actual ni introducir un for_each diferente sin verificar ambos perfiles.

**Gate P3:** primer bootstrap y sincronización usan los mismos controles de identidad/planes; credenciales del runner no se copian a VMs; PRs siguen sin OIDC ni secrets del ambiente de despliegue.

### P4 — Acreditar la cadena CI → publicación → despliegue

1. Conservar los triggers actuales. No agregar despliegue automático a push ni repository_dispatch solo porque documentación antigua los mencione. Mantener el botón manual y duración de cuatro horas.
2. Comprobar que el ruleset requerido sigue exigiendo "Integrated CI / result" y base actualizada; que una PR a main solo admite develop del mismo repo; que result falla si falta cualquier job requerido y acepta skips únicamente cuando el plan demuestra que son correctos.
3. Registrar CI de la candidata con run/attempt, conclusión y árbol raíz validado, gitlinks y plan. Una PR puede probar un merge sintético: comparar el árbol efectivo y fuentes con la integración publicada, no exigir que dos SHA de commits con la misma fuente sean idénticos ni aceptar un CI verde de otro árbol.
4. Integrar componentes y raíz mediante el flujo normal sin bypass. El agente no debe avanzar gitlinks a puntas remotas para arreglar un build. Resolver conflictos como cambios de fuente y volver a validar si cambian el árbol.
5. Dejar que el push protegido a main publique. Correlacionar CI, commit de main, tag anotado, manifiesto, Cloud Build, digests y prerelease. Si falla el build/release no declarar una publicación nueva completa.
6. Desplegar mediante vm-controls.yml desde main, con start si está apagado o update si hay una sesión activa sana y con margen suficiente. No usar start para extender una sesión. La autorización de ejecución/despliegue se obtiene al implementar, no de este documento.
7. Acreditar el caso de error con pruebas controladas: CI fallido no habilita integración; bundle/manifiesto inválido no despliega; update apagado no enciende VMs; fallo de despliegue no marca saludable el nodo; cleanup/cancelación conserva lease acotada, SQL y datos.

**Gate P4:** evidencia del conjunto candidato en main, sin reutilizar el éxito histórico de develop como CI. Publicación y operación manual quedan identificadas por separado.

### P5 — Implementar recreación aislada con un comando

Esta es la parte nueva principal. No llamar "recreación completa" a tofu validate, a otro start contra el mismo estado ni a copiar volúmenes de la demo.

#### P5.1 Contrato y aislamiento

Crear scripts/gcp/reproduce.py, test_reproduce.py, .github/workflows/reproduce.yml e infra/gcp/reproduction-project/ para el contenedor de proyecto de ensayo. Reutilizar bootstrap/demo/delivery/vm_deploy, sin una segunda topología escrita a mano.

El ensayo usa **otro proyecto GCP**, con ID único por ejecución y etiqueta de propiedad NFR-14. Puede conservar los mismos nombres internos de recursos porque el proyecto los aísla. Nunca usar otro prefix del mismo estado para intentar crear recursos homónimos en el proyecto actual.

El módulo externo crea el proyecto, vinculación de facturación y presupuesto del ensayo mediante IaC. Entradas públicas obligatorias del perfil administrativo: cuenta de facturación autorizada, padre si corresponde, bucket/prefix de control y límite/ventana de gasto aprobados. No inferirlas del primer proyecto/cuenta que devuelva gcloud. La identidad que crea/vincula proyectos necesita permisos administrativos explícitos en el padre/cuenta. No concederlos al runtime ni presuponer que owner del proyecto actual permite crear otros proyectos. Si esos permisos no están disponibles, preparar scripts y planes, registrar el bloqueo del ensayo real y no declarar NFR-14 terminado.

Mantener el presupuesto del ensayo en el estado externo junto al proyecto, con filtro a su número y dependencia del proyecto. Pasar billing_account_id vacío al bootstrap interno del ensayo para no crear otro presupuesto de cuenta que sobreviviría a la eliminación del proyecto. El bootstrap de la demo conserva su presupuesto actual. El orquestador debe limitar sus cambios al ID de presupuesto de ensayo registrado; no modificar otros presupuestos de la cuenta aunque la identidad administrativa tenga permisos de Billing más amplios.

Su estado debe persistir fuera del proyecto descartable, en un bucket de control autorizado, con prefix exclusivo por ejecución y versionado. No cambiar foundation/demo de la demo para alojarlo. El estado interno bootstrap/demo del ensayo vive en su propio bucket. Registrar lineage/serial y project ID/número en el inventario privado del ensayo.

Mantener **nexoruta-demo** como environment de GitHub para aprovechar los secretos externos ya configurados, sin solicitar al usuario que los exponga o que los copie al equipo. Añadir allí únicamente estas variables públicas; solo las consume reproduce.yml, y publish.yml/vm-controls.yml conservan sus variables GCP actuales:

| Variable nueva | Contrato |
| --- | --- |
| NFR14_REPRO_RUN_ID | Identidad del ensayo, igual al input del workflow y al inventario de control |
| NFR14_REPRO_INTEGRATION_TAG | Tag validado y fijado antes de crear recursos |
| NFR14_REPRO_PROJECT_ID | Proyecto único de ensayo; distinto del principal |
| NFR14_REPRO_PROJECT_NUMBER | Número observado tras crear ese proyecto |
| NFR14_REPRO_STATE_BUCKET | Bucket de estado del ensayo, coherente con su project ID |
| NFR14_REPRO_DELIVERY_BUCKET | Bucket de delivery del ensayo, coherente con su project ID |
| NFR14_REPRO_WORKLOAD_IDENTITY_PROVIDER | Provider de ese project number |
| NFR14_REPRO_DEPLOY_SERVICE_ACCOUNT | SA del proyecto de ensayo |

La región y las dos zonas mantienen los valores explícitos de Santiago del perfil validado; no dependen de defaults del gcloud local. El perfil de reproducción pasa base_domain vacío y manage_dns=false para no reutilizar ni cambiar una zona DNS propia de la demo.

Serializar toda la operación administrativa, incluyendo escritura de esas variables, ejecución y cleanup, con un lock GCS independiente en el bucket de control, adquisición por precondición de generación y lease renovable. No reutilizar el lock/lease de la demo. Añadir concurrency del workflow de reproducción, pero no confiar solo en ella: dos procesos locales podrían sobrescribir variables antes de que un job empiece. Un run debe revalidar su identidad justo antes de autenticarse/aplicar. Si no tiene el lock, no cambia variables.

El job reproduce.yml traduce explícitamente esas variables al contrato GCP de scripts existentes y comprueba que ningún valor apunta al proyecto principal, su bucket, su cuenta de servicio o su provider. El código debe rechazar también mezclas de proyectos entre variables. No resolver el destino por valores por defecto.

El WIF **del proyecto de ensayo** confía en el environment existente, IDs inmutables, ref main, evento workflow_dispatch y únicamente reproduce.yml. Parametrizar github_environment, refs/eventos y paths exactos de workflow en el módulo bootstrap; pasar los valores originales para la demo y los de reproducción para el ensayo. Actualizar bootstrap.py/settings y setup juntos para no revertir esos inputs al sincronizar. No añadir reproduce.yml a la confianza del proyecto principal si solo opera el ensayo.

El workflow es solo workflow_dispatch, con inputs run_id e integration_tag; valida igualdad con environment e inventario. No acepta project, SA, bucket, comandos o URLs arbitrarios como inputs. No necesita crear tags integration-* ni GitHub releases y no recibe contents:write. Usar id-token:write solo en el job que despliega el proyecto aislado. El control de sesiones/canales/locks del ensayo utiliza sus buckets propios.

#### P5.2 Comando y secuencia

Interfaz implementada en `scripts/gcp/reproduce.py`; `recreate` requiere aprobación explícita de destino y costo. Todas las acciones administrativas posteriores requieren identificar el bucket de control:

~~~text
python scripts/gcp/reproduce.py recreate --integration-tag TAG_VALIDADO --run-id IDENTIDAD_UNICA --evidence-dir DIRECTORIO_VACIO --control-project-id PROJECT_CONTROL --control-bucket BUCKET_CONTROL --main-project-id PROJECT_DEMO --parent organizations/ID_APROBADO --billing-account-id CUENTA_APROBADA --monthly-alert-budget-usd USD_ENTERO --approved-cost-ceiling-usd USD_APROBADO --estimated-window-cost-usd USD_ESTIMADO --window-hours HORAS_1_A_4
python scripts/gcp/reproduce.py plan --run-id IDENTIDAD_UNICA --control-project-id PROJECT_CONTROL --control-bucket BUCKET_CONTROL
python scripts/gcp/reproduce.py inspect --run-id IDENTIDAD_UNICA --control-project-id PROJECT_CONTROL --control-bucket BUCKET_CONTROL
python scripts/gcp/reproduce.py destroy-plan --run-id IDENTIDAD_UNICA --control-project-id PROJECT_CONTROL --control-bucket BUCKET_CONTROL
python scripts/gcp/reproduce.py destroy --run-id IDENTIDAD_UNICA --control-project-id PROJECT_CONTROL --control-bucket BUCKET_CONTROL --confirm-project ID_EXACTO
~~~

No existe un subcomando administrativo `apply`: `recreate` aplica el plan guardado de creación después de validar destino, inventario, proyecto vacío y aprobaciones; `plan` es una comprobación de drift sin escritura; `destroy` aplica únicamente el plan de destrucción guardado y versionado que produjo `destroy-plan`.

El comando recreate se ejecuta desde un checkout limpio con herramientas y autenticación administrativa de preparación ya disponibles. Esa autenticación solo prepara el proyecto/fundación/WIF; **no se traslada al runner**. Luego dispara Actions y espera su conclusión. Cloud ejecuta esta preparación con una identidad propia disponible allí o registra la falta de capacidad; nunca usa la sesión/archivos del Windows del usuario.

Secuencia obligatoria:

1. Resolver una vez el tag main probado y su prerelease completa; verificar tag anotado, raíz, gitlinks y procedencia del CI conforme a P4. Rechazar un tag arbitrario o una release incompleta.
2. Trabajar en checkout/directorios de estado aislados. Comprobar que no existen .env, bin/obj, .local, credenciales ni volúmenes reutilizados de la demo. No borrar el checkout habitual para lograrlo.
3. Mostrar plan resumido y estimación/costo máximo de la ventana previamente acordados. Comprobar cuotas, facturación y disponibilidad de servicios en el proyecto nuevo.
4. Crear proyecto/fundación desde sus módulos, guardar prueba de estado vacío inicial y migración segura del primer estado a GCS; configurar WIF y variables NFR14_REPRO_ sin modificar las variables GCP de la demo.
5. Disparar reproduce.yml desde la ref autorizada, pasando el tag exacto y la identidad del ensayo. Esperar el run específico, no "el último run" de cualquier actor.
6. Checkout del tag y submódulos exactos para build e infraestructura. Construir las seis imágenes y bundle en el registry/bucket del ensayo con el código de delivery existente. No intentar reutilizar digests de otro proyecto que latest_manifest rechazaría.
7. Reutilizar RELEASE_CHANNEL=main dentro del bucket aislado, con la comprobación del integration_tag. Forzar build completo y bundle nuevo cuando no existe baseline local. La prueba de CI se hereda únicamente de las fuentes exactas ya probadas; no inventar una verificación Android nueva porque se haya forzado el build. Si se agrega un campo de procedencia al manifiesto, actualizar todos sus productores/consumidores/tests juntos.
8. El único escritor de ese canal en el ensayo es reproduce.yml: su numeración de publication_order no se mezcla con publish.yml. No publicar una prerelease adicional en el repo para el ensayo.
9. Sincronizar integraciones mediante el mismo camino de Secret Manager, conservando hosting/Redis generados para ese proyecto. Mantener geocodificación y routing externos apagados y Mapbox permanent=false. No copiar tokens reales de consumo a fixtures ni efectuar peticiones Mapbox/Geoapify en las pruebas.
10. Ejecutar start con el mismo ciclo de migración/RLS/roles/importación/bootstrap y smoke. El proyecto está vacío: no requiere conciliación de legados. La demo con datos sí conserva los procedimientos Stage/B1–B5; este ensayo no los autoriza ni los reemplaza.
11. Capturar release/digests y salud A/B, HTTPS, PostgreSQL/PostGIS, roles runtime sin superuser/BYPASSRLS y evidencias P6. Aplicar límites de tiempo y reintentos finitos; certificados gestionados pueden necesitar espera DNS. No usar --insecure o ssl sin validación como solución.
12. Volver a planificar con los mismos inputs. Exigir ausencia de cambios inesperados. Separar el estado de sesión manejado fuera de IaC: no aplicar a ciegas un drift de desired_status/deadline ni ignorar todos los cambios. Registrar la excepción precisa si la normalización de Compute la requiere.
13. Guardar evidencia sanitizada y cierre/cleanup. Tras stop, SQL/discos/LB/Memorystore siguen costando: stop del ensayo tampoco equivale a destrucción.

No agregar un environment de ensayo duplicando secretos como requisito oculto. Grafana reutiliza las credenciales OAuth del environment; una IP nueva cambia el redirect URI. Comprobar que el URI que genera el ensayo es correcto, y documentar el registro externo necesario si se quiere probar el login completo. El smoke NFR-14 verifica HTTPS, /api/health y bloqueo anónimo; no necesita acreditar el dashboard autenticado de NFR-12 ni habilitar callbacks de OAuth silenciosamente.

#### P5.3 Destrucción y segunda recreación

El comando destroy-plan prepara un plan **del módulo externo de proyecto descartable**, no un destroy indiscriminado de los módulos protegidos de la demo. Aplicar una política de destrucción explícita del proyecto de ensayo en el módulo externo, comprobada con google 7.46.1. No simular que prevent_destroy puede variar por una variable ordinaria de lifecycle.

Antes de destroy: cerrar lease/carga, recoger evidencia y estado privado necesario para auditoría, comprobar ownership/ID/número exactos del proyecto y que todo dato es sintético. Generar el plan de destrucción externo y validar que solo contiene el proyecto del ensayo y sus recursos de control asociados. Rechazar el proyecto principal y cualquier destino diferente al inventario del run. Aplicar con identidad administrativa externa al proyecto que se destruye, no con la SA que está siendo eliminada.

Esta destrucción deliberada del contenedor de proyecto no debe retirar protecciones de SQL, discos o buckets del ambiente persistente. Confirmar el comportamiento real de GCP ante recursos protegidos; si una política/hold bloquea la eliminación, detenerse y preparar el ajuste exclusivamente del proyecto descartable. No aplicar una sustitución global de true→false ni eliminar estados para superar el bloqueo.

El recurso externo google_project debe declarar deletion_policy="DELETE" exclusivamente para el proyecto descartable; en google 7.46.1 el default es PREVENT y ABANDON no elimina el proyecto. Crear un plan guardado de destrucción y aplicar ese mismo plan. El presupuesto del ensayo también debe destruirse desde ese estado externo; no dejarlo como recurso huérfano de la cuenta de facturación.

Google puede mantener un proyecto en borrado pendiente y no permite reutilizar su ID. La segunda recreación usa otro ID único, el mismo tag e inputs de aplicación, y estados nuevos. No intentar resucitar el proyecto borrado ni usar el estado anterior como prueba de creación vacía. Tras confirmar cleanup, retirar las variables NFR14_REPRO_ de ese run bajo el lock de control. Ante cleanup incompleto, conservar inventario y referencias para inspect/reintento, sin permitir apropiación por otro run.

**Gate P5:** recreación real, cleanup verificable y segunda recreación ejecutables desde el mismo comando y fuentes; ninguna dependencia en servicios/datos de la demo. Preservar evidencia fuera del proyecto destruido. Si solo se logra idempotencia contra el ambiente existente, P5 no está aprobado.

### P6 — Verificar HTTPS y el sistema real

Crear scripts/gcp/verify_nfr14.py y test_verify_nfr14.py. Reutilizar lectores comunes cuando corresponda; no debilitar las restricciones del verificador de fallos NFR-13 para apuntarlo al ensayo.

El stage `apply` captura por VM los contenedores activos del proyecto Compose, usando `docker inspect --format` limitado a etiqueta de servicio, estado y estado de healthcheck. Valida el conjunto exacto esperado de A/B; Redis solo pertenece a B con cache habilitado. La captura no puede incluir `Config.Env`, comandos, logs ni IDs de contenedor. Adjuntarla al comprobante con versionado de esquema y allowlist estricta. Esto acredita inventario/proceso y healthchecks declarados, pero no reemplaza las pruebas funcionales de dependencias sin healthcheck.

Entradas: inventario del run, project ID/número, release esperada, endpoints y manifiesto exactos. Destino fuera del inventario, certificado inválido o identidad inconsistente debe fallar.

| Comprobación | Evidencia exigida |
| --- | --- |
| TLS público | Certificado y hostname válidos, cadena verificada, vigencia, HTTP→HTTPS. No basta la existencia de un recurso certificado en IaC |
| API | /live, /ready, /health 200; readiness de PostgreSQL, claves compartidas y cuotas según contrato actual; release/node sin exponer configuración privada |
| Portales | Admin/Backoffice/Commerce /ingresar y Tracking /ready; login con cuentas sintéticas y una lectura autenticada real por los caminos existentes |
| Persistencia | Migraciones aplicadas, PostGIS, roles runtime restringidos, RLS forzado donde corresponde y aislamiento de dos organizaciones sintéticas usando los tests existentes |
| Release | Manifest/digests de seis apps y bundle corresponden a la candidata; A/B sirven el mismo conjunto; no hay compilación en VM |
| Compartidos | Redis B acepta CA/hostname/AUTH desde A y B; RabbitMQ/Kafka/Mongo y workers requeridos están operativos; comprobar el inventario exacto de Compose y cada healthcheck declarado; no usar solo readiness de API para declarar sano todo Compose |
| Correo/monitor | Mailpit y API de dashboard rechazan anónimos como corresponde; correo de prueba se captura sin envío externo; Grafana /api/health responde por HTTPS |
| Sesión | Lease/deadlines acotados, update no amplía plazo, stop detiene A/B y conserva SQL/datos; registrar identidades de claves antes/después sin publicar sus valores |
| Recreación | Misma fuente reconstruida desde recursos de aplicación vacíos; segundo plan sin cambios inesperados; segunda ejecución independiente acreditada |

No forzar un seed general de negocio si los inicializadores restringidos y fixtures existentes cubren la prueba. Las verificaciones autenticadas/SQL se ejecutan dentro del runner/VM autorizado con secretos en memoria o archivos privados, y solo emiten resultados sanitizados.

Para revisión en navegador: aplicar frontend/DESIGN.md, usar los portales existentes y comprobar login, navegación y una lectura por rol con capturas limpias sin tokens ni datos personales. No introducir una pantalla de infraestructura en el producto. Si se modifica interacción/interfaz, añadir comprobación de teclado/foco/errores y viewport reducido. Un fallo de navegador queda pendiente como tal; no reemplazarlo por "curl pasó".

**Gate P6:** informe separado de compilación, HTTP, automatización y revisión visual, con release/run exactos. No se exige cerrar los gaps de failover/estabilidad NFR-13 para afirmar el alcance específico de este gate.

### P7 — Costos y presupuesto observado

Archivos: infra/gcp/costs.md, requirements.md; docs/auditorias/nfr-14/costos.md y evidencia/costos-observados.json.

1. Reconstruir estimación desde el inventario P0: dos N4 custom; boot y data Hyperdisks; SQL siempre encendido y crecimiento de SSD; LB/IPv4; Memorystore real y Redis B; SQL de restauración detenido y su disco; tráfico entre zonas/Internet; buckets/versionado; Artifact Registry; Cloud Build; Secret Manager; Scheduler/Workflows; logs/métricas/trazas; Cloud Run solo si se usa. Contar lo realmente facturado, no solo lo necesario para tráfico de usuario.
2. Para cada línea: región, SKU/unidad, cantidad, horas/mes, tarifa consultada y enlace oficial/fecha. No reutilizar totales de una VM ni el costo antiguo de SQL 2vCPU/8GiB. No estimar en pesos ni mezclar impuestos/créditos con costo bruto USD.
3. Separar costo fijo con VMs detenidas, costo incremental por sesión de cuatro horas, por publicación y costo del ensayo. Mostrar escenarios 8 y 20 sesiones/mes con cantidades explícitas, y tres meses solo con duración/saldo de crédito verificados.
4. Obtener Cloud Billing Reports/Cost table filtrado por el proyecto y período. Usar export existente de BigQuery si lo hay; no asumir que la API de budgets devuelve consumo ni inventar un comando gcloud para consultar facturas. Si no hay export, descarga CSV desde Console con la identidad autorizada.
5. Conservar resumen sanitizado por servicio/SKU y período: costo bruto, créditos, neto, moneda, hora de consulta y fecha máxima de consumo incluida. Retirar IDs de cuenta, correos, datos de pagos y recursos privados de los artifacts públicos. Adjuntar captura con filtro/fechas visibles si ayuda.
6. Billing puede aparecer con demora. No exigir que el gasto del ensayo recién terminado ya esté completo: registrar desfase y repetir lectura cuando esté disponible. Una captura del presupuesto no reemplaza costo observado.
7. Verificar presupuesto del proyecto principal USD 80, EXCLUDE_ALL_CREDITS, filtro project number y umbrales 0.5/0.8/1.0. Preservarlo al sincronizar bootstrap; no tomar el presupuesto distinto de "Laboratorios" como presupuesto de NexoRuta.
8. Verificar destinatarios/canal y evidencia de notificación si ya existe; no gastar para disparar una alerta. No afirmar que USD 80 detiene recursos: el presupuesto configurado es de alertas. No deshabilitar billing automáticamente para frenar gasto porque puede afectar datos.
9. El proyecto de ensayo necesita su propio presupuesto y ventana/costo autorizados. El límite de cuatro horas de VMs no limita el gasto de SQL/LB/discos. Programar el cleanup y verificarlo aunque un workflow falle; si no se puede ejecutar, informar proyecto/recursos pendientes y costo que sigue corriendo.

**Gate P7:** tarifas/cantidades actuales + consumo real identificable + presupuesto comprobado. Si solo hay estimación o presupuesto, "evidencia de costos" permanece pendiente.

### P8 — Documentación, evidencia y cierre

1. Actualizar infra/gcp/README.md, requirements.md, github-environment.md, integration-tags.md, guia-uso-actions.md y project.md para reflejar gitlinks, triggers, canales main/develop, corte durante migración, Redis B/Memorystore, topología/costos y controles disponibles. No reescribir evidencia histórica como si se hubiese ejecutado de nuevo.
2. Crear docs/auditorias/nfr-14/runbook.md con precondiciones y comandos reales ya implementados de plan/apply/recreate/inspect/destroy-plan/destroy. Diferenciar stop, desmontaje descartable y baja definitiva de la demo persistente.
3. Para la demo con datos, documentar plan -destroy y los bloqueos esperados por protección, exportación/restauración de datos y decisión explícita antes de levantar protecciones. Un destroy bloqueado no es una prueba de destrucción exitosa. La prueba ejecutable de destrucción se hace sobre el proyecto descartable.
4. Guardar docs/auditorias/nfr-14/aceptacion.md con matriz final, SHAs, runs/attempts, build IDs, tag, manifiesto, hashes, HTTPS, pruebas, costo observado y recursos al terminar. Evidencia pública solo por allowlist.
5. No publicar .env, tofu show/state/plan crudos, tokens, keyrings, contraseñas, PFX, firma Android, cookies, JWT o capturas de cuentas de facturación.
6. Mantener los ocho skips locales de este análisis como limitación histórica. En el CI Linux correr los casos aplicables; documentar cada omisión nueva por capacidad concreta, no aceptar skips de comprobaciones obligatorias.
7. Actualizar la card NFR-14 con enlace a implementación/evidencia únicamente cuando se ejecute este plan. Mantener "In progress" hasta completar los criterios de la sección 7. No mover NFR-13/12 ni otros pendientes por arrastre.

## 6. Validaciones y secuencia de entrega

El verificador automatizado implementa solo una parte de P6: procedencia CI/release, digests, TLS/HTTP a HTTPS, endpoints de salud y denegación anónima, login/lectura sintética por rol, Redis TLS/AUTH, versiones host y una captura sanitizada del inventario Compose/healthchecks declarados en A/B, además de stop de VMs conservando SQL. La captura exige todos los servicios esperados en estado `running` y `healthy` donde Compose declara healthcheck; no afirma readiness funcional de servicios sin healthcheck. PostGIS/esquema aplicado y privilegios/RLS entre dos organizaciones, salud funcional de todas las dependencias compartidas, captura de correo de prueba, revisión visual, segunda recreación y consumo facturado siguen pendientes explícitos; el artifact no los presenta como aprobados.

Los cambios de contrato/backend de P1 se publican en su repo y se integran antes de fijar el gitlink raíz. No se requiere cambiar frontend/mobile salvo un consumidor real afectado; actualizar fuentes y tests juntos.

Orden sugerido de PRs: P1; P2/P3; P5/P6 y sus pruebas; corrección documental; integración develop→main; ejecución P4/P5/P6/P7; evidencia final. Cada PR debe explicar el comportamiento final y validación real, sin mezclar credenciales ni evidencia ajena.

Comprobaciones locales mínimas para cambios de scripts/IaC; usar los comandos del CI vigente:

~~~bash
python3 -m unittest discover -s scripts/gcp -p 'test_*.py' -v
tofu fmt -check -recursive infra/gcp
tofu -chdir=infra/gcp/bootstrap init -backend=false -input=false -lockfile=readonly
tofu -chdir=infra/gcp/bootstrap validate
tofu -chdir=infra/gcp/demo init -backend=false -input=false -lockfile=readonly
tofu -chdir=infra/gcp/demo validate
bash -n infra/gcp/demo/startup.sh
python3 scripts/gcp/validate_compose.py
go run github.com/rhysd/actionlint/cmd/actionlint@v1.7.12 -ignore 'unexpected key "queue" for "concurrency" section' .github/workflows/*.yml
~~~

Añadir init/validate del módulo nuevo de proyecto con backend deshabilitado. Estos comandos deben ejecutarse en una copia de validación sin backend.generated.tf ni metadata de un backend remoto para que la validación estática no reutilice estado por accidente. Un fallo de acceso a provider no se arregla actualizando el lock.

Para P1 ejecutar las suites de backend/Cloud SQL y sus regresiones de autenticación/seed a través del CI existente; no sustituir PostgreSQL/PostGIS/RLS reales por mocks. El CI integrado final debe cubrir la combinación completa candidata, incluyendo frontend y mobile cuando el plan lo requiere. No relajar el gate arquitectónico ni reabrir el fallo histórico esperado2/actual7 por rutina.

Casos nuevos mínimos de reproduce/verify:

| Caso | Resultado obligatorio |
| --- | --- |
| Intento de recrear/destruir proyecto principal | Rechazo antes de cualquier mutación |
| Proyecto/SA/provider/bucket de distintos destinos | Rechazo |
| 403/red al inspeccionar estado | Error, nunca "vacío" |
| Estado/recursos ya existentes de otro run | Rechazo de apropiación |
| Plan con reemplazo de persistencia de demo | Rechazo antes de apply |
| Tag/CI/gitlinks distintos | Rechazo de reconstrucción |
| Digest/checksum faltante o alterado | Rechazo antes de drenaje |
| Falla tras bootstrap/build/deploy | Evidencia parcial honesta y cleanup del ensayo; SQL demo intacto |
| Reintento mismo run | Reanuda únicamente recursos propios; no duplica proyecto ni reinicia plazo |
| Cancelación | Cloud Build cancelado y cleanup/guard verificables; no depender solo del proceso cancelado |
| Credencial canario | Ningún artifact/log/resumen la contiene |
| TLS inválido, rol SQL privilegiado o dependencia requerida caída | Verificador falla; no "saludable" por API 200 |
| Teardown correcto | Solo proyecto sintético esperado queda en eliminación; evidencia externa preservada |
| Segundo ensayo | Nuevo ID y estados, misma fuente, sin volúmenes/secretos internos del primero |

Los tests de unidad simulan APIs de administración. Los ensayos GCP separados demuestran ejecución real. No confundir esos resultados.

## 7. Definición de terminado

NFR-14 puede proponerse como terminada solo cuando todos los ítems siguientes tengan evidencia:

- [ ] Candidata y tres gitlinks exactos; CI integrado requerido aprobado sobre las mismas fuentes/árbol.
- [ ] Publicación main completa y trazable: tag, build, manifiesto, seis digests y bundle disponibles.
- [ ] Despliegue manual por Actions desde esa publicación; configuración del environment y WIF temporario; secretos operativos fuera del código.
- [ ] HTTPS/certificado, login/lectura, PostgreSQL/PostGIS/RLS y dependencias del despliegue comprobados.
- [ ] Navegador revisado y limitaciones expresadas aparte de HTTP/compilación/automatización.
- [ ] Primer ensayo creado desde proyecto/infraestructura de aplicación vacíos mediante el comando implementado; sin usar datos de la demo.
- [ ] Replanificación idempotente explicada y segunda recreación independiente con las mismas fuentes.
- [ ] Destrucción deliberada del proyecto sintético comprobada, con estado/evidencia fuera de él; demo persistente conservada.
- [ ] Estimación actual, consumo real con período/desfase, presupuesto del proyecto y costos residuales documentados.
- [ ] Runbook de plan/apply/destroy/recreación ejecutable; documentos coherentes con el código; sin aliases/fallbacks para contratos anteriores.
- [ ] No quedaron proyectos/recursos de ensayo facturando sin inventario y decisión explícita.

Un bloqueo de permisos, cuotas, billing, TLS, navegador o evidencia de costos no se resuelve con una afirmación de aceptación. Entregar la implementación verificable, identificar exactamente el gate pendiente y conservar la card abierta.

## 8. Referencias técnicas verificadas

- [OpenTofu: backend GCS](https://opentofu.org/docs/language/settings/backends/gcs/): bucket previo, locking y versionado; fundamento del bootstrap y aislamiento de estado.
- [OpenTofu: datos sensibles en estado](https://opentofu.org/docs/language/state/sensitive-data/): planes/estado privados aunque los valores tengan marca sensitive.
- [OpenTofu: plan](https://opentofu.org/docs/cli/commands/plan/): planificar no aplica cambios; el plan guardado determina qué se aplica.
- [GitHub: environments](https://docs.github.com/en/actions/reference/workflows-and-actions/deployments-and-environments): alcance de variables/secrets y reglas de despliegue.
- [GitHub: OIDC con GCP](https://docs.github.com/en/actions/how-tos/secure-your-work/security-harden-deployments/oidc-in-google-cloud-platform): identidad temporal, condiciones de confianza y sujeto inmutable.
- [GCP: presupuestos y alertas](https://docs.cloud.google.com/billing/docs/how-to/budgets): interpretar el presupuesto de alertas existente sin atribuirle un tope de gasto.
- [GCP: Billing Reports](https://docs.cloud.google.com/billing/docs/how-to/reports) y [Cost table](https://docs.cloud.google.com/billing/docs/how-to/cost-table): obtener gasto y créditos reales, separados de estimaciones.
- [GCP: protección contra borrado de Cloud SQL](https://docs.cloud.google.com/sql/docs/postgres/deletion-protection): protección adicional al lifecycle de IaC; no levantarla en la demo para probar reconstrucción.
- [Provider google 7.46.1: google_project](https://github.com/hashicorp/terraform-provider-google/blob/v7.46.1/website/docs/r/google_project.html.markdown): creación/vinculación, permisos y política explícita DELETE frente al default PREVENT.
