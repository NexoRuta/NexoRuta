# Proyecto GCP de la demo

Creado y verificado mediante Google Cloud CLI el 22/10/2026.

| Dato | Valor |
| --- | --- |
| Nombre | `NexoRuta Demo` |
| Project ID | `nexoruta-demo-20261022` |
| Project number | `1090571196455` |
| Estado | `ACTIVE` |
| Facturación | Vinculada a una cuenta abierta; `billingEnabled=true` |
| Región configurada en la CLI | `southamerica-west1` |
| Zona configurada en la CLI | `southamerica-west1-a` |

[Abrir el proyecto en Google Cloud](https://console.cloud.google.com/home/dashboard?project=nexoruta-demo-20261022).

La CLI creó el proyecto, vinculó la cuenta de facturación y habilitó Service Usage
y Cloud Resource Manager como requisitos iniciales del bootstrap. La sesión local
y las Application Default Credentials están autenticadas, con este proyecto como
quota project. Las credenciales se guardan fuera del repositorio.

El bootstrap de OpenTofu se aplicó el 22/10/2026: cuentas de servicio y permisos,
WIF activo, buckets privados, Artifact Registry, Secret Manager, Firebase/Android,
alerta de presupuesto y controlador de apagado. Su estado quedó migrado a
`gs://nexoruta-demo-20261022-tofu-state/foundation/default.tfstate`.

Las siete variables requeridas y `GCP_MANAGE_DNS=false` quedaron cargadas en el
environment `nexoruta-demo` del repo madre en GitHub. Los workflows y el código de
infraestructura siguen pendientes de publicación desde el checkout local.

La máquina `c4-highcpu-8` se verificó en `southamerica-west1-a`: ocho vCPU y
16384 MiB. No se inició una VM ni se creó Cloud SQL en esta preparación. El
proyecto y su vínculo de facturación se administran por CLI y no forman parte
del estado OpenTofu.

Para volver a sincronizar el bootstrap y sus variables en GitHub:

```powershell
./scripts/gcp/setup.ps1 -ProjectId nexoruta-demo-20261022
```

Este paso aplica los cambios del bootstrap y necesita autenticación en GitHub. El inicio de
la VM continúa siendo una operación manual de GitHub Actions.

Para las variables de GitHub, usar `GCP_PROJECT_ID=nexoruta-demo-20261022`. El
provider creado por OpenTofu tiene el nombre:

```text
projects/1090571196455/locations/global/workloadIdentityPools/nexoruta-github/providers/demo-vm
```

El resto de valores se obtiene del bootstrap según la
[lista de variables y secrets](github-environment.md).
