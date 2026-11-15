# NFR-14 — Diagnóstico de implementación

Observación base: 14/11/2026, aproximadamente 20:22 UTC. Estado: implementación en curso; NFR-14 sigue abierta. Este diagnóstico usa lecturas sin modificación de GitHub ni GCP. No se descargaron secretos, estados OpenTofu, planes ni datos de negocio.

## Fuentes y candidato

- Raíz: `codex/nfr-14-implementation`, commit base `86e234e7bc0a2be1ce8911cc186ecf0e55d628e4`, árbol base `6f4011e136ced28f02b9330fb218af085e61c44c`.
- Gitlinks y HEAD iniciales: backend `5b6f0f9f052348aed27da40ed202da953b39ea2a`; frontend `2540041ba267d8a48e6c2b8a644247134f5b47f4`; mobile `90976706c7db6a54c06ac552811f20f04d90375e`. Los tres checkouts coincidían con sus gitlinks y estaban limpios antes de empezar los cambios.
- Puntas remotas consultadas: raíz main `27f69c62bc974deee8879374d6d14b1db051a0f6`, develop `7c397dcd53d88d8b21011d209bf79cb642fc1f6d`; backend main `54165fb2d169c907730f1f991fd694b30101f6b0`, develop `5b6f0f9f052348aed27da40ed202da953b39ea2a`; frontend main `5c1c008d5a62ea3f7e5f043b2b3a178e154a4ef6`, develop `162bf08ec9ad1428fa56dc81b5ce289ac1208a61`; mobile main `4b9032bc54be3faf7549b33a65315aca87a69df5`, develop `90976706c7db6a54c06ac552811f20f04d90375e`.
- Los archivos `sources.json` guardan las identidades y versiones observadas. No se avanzaron gitlinks para igualarlos a ramas remotas.

## Toolchain y controles remotos

- Python 3.13.5; .NET SDK 10.0.401, fijado con `global.json` y `rollForward: disable`; OpenTofu 1.13.1.
- Locks existentes: google y google-beta 7.46.1, random 3.7.2. SHA-256: bootstrap `682b6c9aa77052244666c42fca5a74d8a6f15696a365157dc8db1a55d1a9c117`; demo `5c588920b244dcc86469c5398dd8641b658dae097a4fab9ef0e9f6267640ce4c`. No se actualizó ningún proveedor.
- GitHub Environment `nexoruta-demo`: están configuradas las 11 variables y los dos secretos esperados. Solo se registraron sus nombres; los valores secretos no se leyeron. El ruleset activo de main exige PR, base actualizada y `Integrated CI / result`, sin bypass.
- La publicación main observada es el run 41946941369 sobre `27f69c62bc974deee8879374d4d14b1db051a0f6`, éxito del 05/11, prerelease `integration-41946941369-1`. El último control de VMs observado es el run 43631884438, `update/develop`, éxito sobre el commit base del worktree. Ninguno acredita CI integrado ni publicación del candidato NFR-14.

## Proyecto GCP existente

Destino identificado: proyecto `nexoruta-demo-20261022`, número `1090571196455`, región `southamerica-west1`. Billing está habilitado. No se usó ni cambió la configuración global de `gcloud`.

La captura sanitizada [demo-inspect-2026-11-14.json](evidencia/demo-inspect-2026-11-14.json), generada por `verify_nfr13.py inspect`, confirma a las 20:21:58 UTC:

- Las VMs A/B están `TERMINATED`; la lease de demo está inactiva. Los API backends no reportan nodos saludables mientras están detenidos. No se inició ni detuvo una VM durante este análisis; la observación anterior de lease activa venció naturalmente.
- Los discos de arranque de 20 GiB y datos Hyperdisk Balanced de 80 GiB siguen adjuntos a ambas VMs.
- Cloud SQL `nexoruta-demo-db` sigue `RUNNABLE`, `ALWAYS`, `db-g1-small`, PostgreSQL 18, zonal, sin backup automatizado ni PITR. La instancia aislada de restauración `nexoruta-nfr13-restore-check` está `STOPPED`/`NEVER`.
- Memorystore `nexoruta-demo-cache` sigue `READY`, Basic, 1 GiB. El runtime declarado usa Redis TLS/Auth en VM B; Memorystore es un recurso adicional que se conserva e inventaría, no se retira en esta feature.
- El balanceador HTTPS global, IP `34.49.146.66` y certificado administrado `ACTIVE` existen. Hay siete backend services; no se declara salud HTTP actual porque A/B están detenidas.
- Artifact Registry contiene `nexoruta`. Hay cinco buckets en Santiago: delivery, load-control, load-fixtures, load-results y tofu-state. El estado remoto contiene `foundation/default.tfstate`, `demo/vm/default.tfstate` y `leases/demo.json`. Los objetos de canal y releases sí existen; sus punteros y manifests públicos permitidos quedaron resumidos en [delivery-channels-2026-11-14.json](evidencia/delivery-channels-2026-11-14.json).
- El canal main apunta a `release-17bcf47546124de5acb87adc7f84e00d`, build `cbe278fd-f40a-49fb-8103-a559cc2df99b`, seis digests y bundle SHA-256 `8ecf512be79d2b849e19f328ac70d73912080eb7ccc5ff184af6b6642332ced2`, integrado en `integration-41946941369-1`. El canal develop apunta a `release-bd39c48fde2b49fa80b18a01f173ebd6`, build `b47edff9-9be1-4275-a9f2-cee3be4c4da6`, seis digests y bundle SHA-256 `12bb73c4caaae928c0a6d934e4fdb9d3e718734b0705221c5ac68819e5cebdf4`, desde la fuente base observada.
- El manifest develop deja `android_input_sha256` sin evidencia, pero sí afirma `android_verified_mobile_sha` igual al gitlink móvil. Esto reproduce B10: el productor deriva una afirmación de verificación del indicador `components.mobile_android.run`. El manifest main tampoco incluye identidad del run/check que produjo esa verificación. Corregir productor y consumidor antes de aceptar manifests nuevos.
- Workflow guard `nexoruta-demo-guard` activo en Workflows, con Cloud Scheduler habilitado cada minuto en `southamerica-east1`. El Cloud Run Job `nexoruta-load-tests` está `Ready`; su última ejecución creada terminó `EXECUTION_SUCCEEDED` el 14/11 a las 17:29:44 UTC. No hay servicios Cloud Run desplegados en Santiago. La lectura del objeto de lock compartido devolvió generación ausente (sin lock vigente).
- La lectura del presupuesto encontró USD 80/mes para el número de este proyecto, filtro `EXCLUDE_ALL_CREDITS` y umbrales 50/80/100 %. Es un sistema de alertas, no un límite de gasto. El consumo real y los costos residuales no se han consultado.

No se leyó el Secret Manager ni el estado OpenTofu. Como las VMs están detenidas, no se pudo comprobar ahora el historial aplicado de migraciones ni los digests actualmente instalados en A/B. La evidencia histórica más reciente registra A/B sanas durante una sesión anterior, pero no sustituye esas comprobaciones.

## Matriz de requisitos, código y evidencia

| Requisito | Código o control vigente | Evidencia disponible | Pendiente |
| --- | --- | --- | --- |
| Fuentes integradas exactas | `.github/workflows/ci.yml`, gitlinks raíz | SHAs base en `sources.json` | CI requerido para el árbol candidato aún no existe |
| Publicación inmutable completa | `publish.yml`, `integration.py`, `delivery.py`, `publication.py` | Los dos punteros actuales tienen manifests, seis digests y bundle; main histórico 41946941369 | Acreditar run de CI de Android en el manifest; A/B detenidas impiden afirmar qué digest está aplicado ahora |
| Despliegue manual protegido | `vm-controls.yml`, `demo_session.py`, `vm_deploy.py` | Run develop 43631884438 histórico | Run main candidato; A/B están detenidas |
| HTTPS, Postgres/PostGIS/RLS y dependencias | balanceador, migraciones y smoke de `vm_deploy.py` | Recursos y certificado existen | Verificación viva, schema aplicado, login y dependencias cuando exista candidata aprobada |
| Credenciales fuera del código | Cambios locales en backend, bootstrap, sincronización de integraciones y environment de GitHub | Nombres configurados; ninguna lectura de valores secretos; tests locales con PostGIS | CI/publicación candidata y transición explícita del admin existente con respaldo/ventana |
| Recreación integral | Orquestador local en `scripts/gcp/reproduce.py`, módulo `infra/gcp/reproduction-project` y workflow manual | Tests/validaciones locales; ningún ensayo remoto acreditado | P4 autorizado; luego P5 con proyecto nuevo, presupuesto y ventana aprobados |
| Destrucción segura del ensayo | Estados separados y protecciones de demo | Estado/recursos persistentes inventariados | P5; no borrar ni alterar la demo |
| Costos | Presupuesto USD 80/mes | Configuración del presupuesto observada | Tarifas vigentes, consumo real, créditos, desfase y costos residuales |

## Estado del gate P0

Destino, gitlinks base, canales y digests publicados están identificados. Las VMs permanecen intactas y la sesión está vencida/inactiva; SQL y otros recursos persistentes siguen generando costo. El gate P0 no está aprobado todavía: falta demostrar qué release quedó instalada por última vez en cada nodo y obtener el schema aplicado sin arrancar la demo. Para crear un proyecto aislado también falta un perfil administrativo confirmado, el alcance/padre, la cuenta de billing autorizada, y presupuesto y ventana aprobados; no se infieren del proyecto existente.

Los cambios de implementación P1 están hechos localmente y son independientes de esa información. Siguen sin publicarse ni desplegarse. No aplicarlos a la base de demo hasta documentar la transición del admin, respaldo verificable y ventana operativa.

## Actualización local de la implementación

El árbol de trabajo contiene la implementación NFR-14 y su plan detallado. Se agregaron el módulo de proyecto descartable, el orquestador de recreación, la verificación de salud y seguridad, los workflows y el runbook. La suite completa de `scripts/gcp`, reejecutada el 15/11/2026, detectó 332 casos: 324 aprobados, 8 omitidos y 0 fallidos. También pasaron restore locked y build de la solución backend, 381 tests unitarios y 7 de arquitectura. En WSL Ubuntu 24.04.3 con Docker Engine 29.1.3 pasaron `validate_compose.py` y 42 pruebas backend seleccionadas de administración/seed/RLS con PostgreSQL 18/PostGIS de Testcontainers; después del ajuste para que xUnit no liste valores de password, pasaron otras 13 pruebas afectadas y una inspección de salida sin esos valores. Los fixtures quedaron sin contenedores, volúmenes ni redes Testcontainers. También pasaron `compileall`, `tofu fmt`, `tofu init -backend=false`/`validate` de bootstrap, demo y reproduction-project en copias temporales, `bash -n`, actionlint y `git diff --check`. La implementación local registra versiones efectivas del host y captura el inventario de servicios Compose/healthchecks declarados por nodo con datos allowlisted; no se ha publicado ni desplegado. Nada de esto se presenta como ensayo GCP.

El socket Docker de WSL no estaba disponible para el usuario Linux normal; se
usó root solamente para lanzar los contenedores efímeros de Testcontainers. No se
cambiaron grupos/permisos del socket ni se tocó el runtime de la demo.

No se inició el runtime de la demo, no se modificaron GCP/Actions ni se leyeron
valores de secretos del GitHub Environment. Los checks locales no sustituyen el
CI integrado ni la evidencia de publicación candidata.

## Cierre documental local

Se armonizaron `infra/gcp/README.md`, `requirements.md`, `github-environment.md`,
`integration-tags.md`, `guia-uso-actions.md`, `project.md` y `costs.md` con los
workflows, topología Redis B/Memorystore y ventana de corte actuales. Se añadieron
el [estado de costos](costos.md), el registro explícito de costo observado
pendiente, el [runbook de teardown protegido](runbook.md) y la [matriz de aceptación](aceptacion.md).
La matriz conserva por separado runs históricos y checks locales. P4 y P5 siguen
pendientes; P6 solo está implementado parcialmente y requiere verificación del
sistema candidato; P7 sigue pendiente de tarifas regionales verificadas y consumo
facturado.

Por instrucción del usuario no se ejecutaron recreaciones aisladas ni cleanup en
GCP, ni la CI/publicación de la candidata en `main`. No se consultó Billing
Reports/Cost table; el presupuesto observado no se presenta como gasto ni límite.
El 15/11/2026 el usuario decidió cerrar administrativamente la card como `Done`;
esa decisión acepta estas brechas como no ejecutadas y no las convierte en
evidencia técnica aprobada.
