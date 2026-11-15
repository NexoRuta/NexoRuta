# Proyecto GCP de la demo

## Registro inicial

El proyecto se creó por CLI el 22/10/2026. Estos datos identifican el proyecto;
los estados de recursos se actualizan en el inventario de solo lectura enlazado
más abajo.

| Dato | Valor registrado |
| --- | --- |
| Project ID | `nexoruta-demo-20261022` |
| Project number | `1090571196455` |
| Región | `southamerica-west1` (Santiago) |
| Zona principal | `southamerica-west1-a` |

[Abrir el proyecto](https://console.cloud.google.com/home/dashboard?project=nexoruta-demo-20261022).

## Observación remota del 14/11/2026

La inspección de solo lectura registrada en [diagnóstico NFR-14](../../docs/auditorias/nfr-14/diagnostico.md)
observó el proyecto `ACTIVE` con billing habilitado. Las VMs A/B estaban
`TERMINATED`, ambas de tipo `n4-custom-6-16384`; Cloud SQL PostgreSQL 18
`db-g1-small` permanecía `RUNNABLE` y `ALWAYS`. También seguían adjuntos los discos de arranque y datos, el balanceador
HTTPS, la IP global, el certificado activo, Artifact Registry, buckets, Scheduler,
Workflows y Memorystore Basic de 1 GiB `READY`. La instancia SQL aislada de
restauración aparecía detenida. No se leyó el estado de OpenTofu, Secret Manager,
ni datos de negocio en esa inspección.

La fuente IaC del worktree actual declara dos VMs `n4-custom-6-16384` en zonas
`southamerica-west1-a/b`, cada una con discos Hyperdisk Balanced de arranque y
datos. El registro del 22/10 indicaba que se denegó una cuota solicitada para C4
y que entonces se usaba `n4-highcpu-8`; no describir ese dato antiguo como la
capacidad actual. Cloud SQL mantiene la configuración persistente sin backups
automáticos/PITR, por lo que la demo no es un destino
seguro para probar destrucción.

El runtime usa Redis TLS/AUTH en el contenedor del nodo B, puerto 6378, accesible
desde A y B. El módulo de demo también declara `google_redis_instance.cache`; el
inventario encontró Memorystore activo, pero el runtime actual no se conecta a
ese recurso. Conservarlo y contabilizarlo hasta que una revisión de dependencias
y costos autorice su retirada.

## Imagen del host y versiones efectivas

Las dos VMs declaran `debian-cloud/debian-12`, una referencia a la familia pública
Debian 12, no al nombre de una imagen versionada. Compute Engine resuelve una
familia a su imagen no obsoleta más reciente; la versión puede variar entre
zonas. Esta implementación documenta ese límite y no promete hosts idénticos
bit a bit. [Documentación de familias de imágenes de Compute Engine](https://docs.cloud.google.com/compute/docs/images)
y [mejores prácticas de familias](https://docs.cloud.google.com/compute/docs/images/image-families-best-practices).

El bootstrap registra el Debian, kernel, arquitectura y versiones efectivas de
Docker Engine, Compose, Buildx, containerd y paquetes instalados. Antes del
drenaje, `prepare` refresca y valida ese inventario en cada nodo; solo copia los
campos allowlisted al comprobante sanitizado de recreación. La identidad
versionada de la aplicación sigue siendo el commit/gitlinks, manifiesto, seis
digests y bundle. Un pin concreto de host y el reemplazo de VMs se dejan para un
cambio posterior ensayado por separado.

El presupuesto observado es USD 80/mes antes de créditos, filtrado por el número
de este proyecto, con `EXCLUDE_ALL_CREDITS` y umbrales 50/80/100 %. Es una alerta,
no un tope de gasto. No se consultó el consumo real ni créditos disponibles.
Consultar el [informe de costos NFR-14](../../docs/auditorias/nfr-14/costos.md).

## Código y controles de GitHub

El Environment `nexoruta-demo` contiene configuración GCP para publicación,
operación y jobs autorizados. La inspección del 14/11 registró los nombres de
11 variables y dos secretos OAuth de monitor, sin leer valores. El workflow
normal usa OIDC/WIF, no una clave JSON. La fuente actual del bootstrap comprueba
el sujeto OIDC inmutable; el provider remoto observado aún admitía un formato
antiguo adicional y el cambio local no se ha aplicado en GCP.

`ci.yml` valida PRs a `develop`/`main`, despachos manuales y el schedule semanal.
`publish.yml` se activa por push a `main`, publica imágenes por digest y una
prerelease sin encender VMs. `vm-controls.yml` requiere despacho manual. Desde
`develop`, `start`/`update` publica el canal develop sin Integrated CI y comparte
las VMs/Cloud SQL con main. Un `update` retira A/B, detiene apps, migra una vez y
admite B y después A; hay una interrupción deliberada.

El módulo aislado de NFR-14 y `reproduce.yml` aún no se han operado contra GCP.
No se creó ni limpió un proyecto de ensayo y no se lanzó CI/publicación de la
candidata main. La matriz de aceptación mantiene esos gates pendientes; no se
presentan como una recreación ya demostrada.

Para variables y secretos, consultar [github-environment.md](github-environment.md).
Para stop, recreación aislada, inspect y destrucción, consultar el [runbook NFR-14](../../docs/auditorias/nfr-14/runbook.md).
