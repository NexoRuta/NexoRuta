# Variables y secretos de GitHub Actions

El repositorio raíz `NexoRuta/NexoRuta` usa el Environment **`nexoruta-demo`**
para publicación, controles de VM y recreación NFR-14. La autenticación GCP es
OIDC/Workload Identity Federation. No almacenar claves JSON ni access tokens
permanentes. No duplicar valores del Environment como variables del repositorio.

La inspección de solo lectura del 14/11/2026 confirmó los nombres de 11 variables
y dos secretos del Environment `nexoruta-demo`; no leyó sus valores secretos.
Los nombres presentes incluyen la configuración requerida abajo y los secretos
OAuth de monitor. No se observaron `SMTP_USERNAME`, `SMTP_PASSWORD`,
`GEOAPIFY_API_KEY` ni `SUBMODULES_TOKEN`; los tres primeros son opcionales según
las integraciones activadas y los repos de componentes observados son públicos.
Revisar la configuración vigente en GitHub antes de una operación; este registro
es histórico y no una lectura actual.

## Variables GCP persistentes

| Nombre | Uso | Obligatoria |
| --- | --- | --- |
| `GCP_PROJECT_ID` | Proyecto persistente de la demo. | Publicación, despliegue y carga. |
| `GCP_REGION` | `southamerica-west1`. | Sí. |
| `GCP_ZONE` | `southamerica-west1-a`. | Sí. |
| `GCP_STATE_BUCKET` | Bucket privado del estado y locks de bootstrap/demo. | Sí. |
| `GCP_DELIVERY_BUCKET` | Bucket privado de manifiestos, canales y bundles. | Sí. |
| `GCP_WORKLOAD_IDENTITY_PROVIDER` | Resource name del proveedor WIF en `projects/PROJECT_NUMBER/locations/global/workloadIdentityPools/.../providers/...`. | Sí. |
| `GCP_DEPLOY_SERVICE_ACCOUNT` | Identidad de publicación y operación de VM. | Sí para publicación/despliegue. |
| `GCP_LOAD_SERVICE_ACCOUNT` | Controlador del workflow OPT-06. | Sí solo para carga. |
| `GCP_LOAD_PREPARER_SERVICE_ACCOUNT` | Preparación HTTP de fixtures sintéticas para OPT-06. | Sí solo para carga. |
| `MONITOR_ALLOWED_EMAILS` | Lista explícita de cuentas Google autorizadas a Grafana, separadas por coma o punto y coma. | Sí para `start`/`update`. |
| `GCP_MANAGE_DNS` | `true` solo con un dominio propio aprobado; por defecto `false`. | Opcional. |

`GCP_SECONDARY_ZONE` puede omitirse: los workflows usan
`southamerica-west1-b`. Si se configura, el código admite `southamerica-west1-b`
o `southamerica-west1-c`. `GCP_BASE_DOMAIN` es opcional; vacío usa `sslip.io`.
`NEXORUTA_CACHE_ENABLED` es opcional y por defecto `true`. `WEBHOOK_ALLOWED_ORIGINS`
es una lista opcional de orígenes HTTPS exactos, no URLs con rutas.

Variables adicionales de OPT-06 (`GCP_LOAD_*`) se generan mediante bootstrap y
no se necesitan para `publish.yml` o el `start`/`update` normal. Consultar el
runbook de carga y no copiar sus identidades al proyecto de reproducción.

## Secretos persistentes

| Nombre | Uso |
| --- | --- |
| `MONITOR_GOOGLE_CLIENT_ID` | OAuth de Google para Grafana. |
| `MONITOR_GOOGLE_CLIENT_SECRET` | Secreto del mismo cliente OAuth. |
| `SUBMODULES_TOKEN` | Solo si un repositorio de componente pasa a privado; lectura `Contents` de los tres repos. |
| `SMTP_USERNAME`, `SMTP_PASSWORD` | Ambos juntos, solo si se habilita un proveedor SMTP autenticado. |
| `GEOAPIFY_API_KEY` | Solo para habilitar y probar geocodificación Geoapify. |

El URI de redirect de OAuth debe corresponder al hostname activo de monitor,
`https://monitor.<dominio>/login/google`. No fijar un IP histórico si el balanceador
cambia. El secreto de OAuth y `MONITOR_ALLOWED_EMAILS` deben corresponder a ese
cliente. Mailpit es la configuración normal para capturar correo dentro de la
demo; no implica entrega externa.

## Configuración pública en Compose

Estas variables se definen en `compose.yaml`, bloque `x-app-settings`; el runner
lee el bloque con Docker Compose y no necesita un daemon Docker para exportar su
configuración. No trasladarlas a GitHub:

| Variable | Uso |
| --- | --- |
| `SMTP_HOST` | Host SMTP; por defecto `mailpit`. |
| `SMTP_PORT` | Puerto SMTP; por defecto `1025`. |
| `SMTP_SSL` | `true`/`false`; por defecto `false`. |
| `SMTP_FROM` | Remitente del correo sintético/de demo. |
| `MAPBOX_PUBLIC_TOKEN` | Token público usado por mapas y APK si se configura. |

Antes de `start`/`update`, `github_environment.py sync-integrations` combina
Compose con secretos opcionales y los sincroniza al secreto privado de GCP
`nexoruta-demo-integrations`. Solo se imprime el resultado de sincronización,
nunca los valores. Las contraseñas de SQL/brokers/actores, las claves de cifrado
y la firma Android se gestionan por IaC/Secret Manager, no como variables
manuales de Actions.

## Environment de CI

Las PRs usan **`nexoruta-ci`**, separado de identidades y secretos de despliegue.
Las ejecuciones programadas/manuales de CI sobre main y los jobs de publicación
usan `nexoruta-demo` cuando necesitan configuración. Los jobs que solo prueban
código no solicitan permiso OIDC. Agregar al Environment `nexoruta-ci` únicamente
`SUBMODULES_TOKEN` si los componentes pasan a privados.

## Variables temporales de recreación NFR-14

`reproduce.yml` usa ocho variables públicas `NFR14_REPRO_*` dentro del Environment
`nexoruta-demo`: `RUN_ID`, `INTEGRATION_TAG`, `PROJECT_ID`, `PROJECT_NUMBER`,
`STATE_BUCKET`, `DELIVERY_BUCKET`, `WORKLOAD_IDENTITY_PROVIDER` y
`DEPLOY_SERVICE_ACCOUNT`. El orquestador las crea bajo el lock externo justo
antes de ejecutar el workflow y valida que no existan ni se reemplacen. No
crearlas a mano. Se borran solamente después de confirmar que el proyecto
descartable y su presupuesto fueron eliminados; si falla el cleanup, se conservan
para inspección/reintento. El workflow usa los secretos persistentes existentes
de OAuth y SMTP donde correspondan; no crea copias de credenciales.

La preparación necesita una identidad GCP administrativa y un bucket de control
versionado externos a la demo y al proyecto descartable. Esa autorización y los
parámetros de billing/costo no son secrets de aplicación ni se agregan al
Environment. Ver [runbook NFR-14](../../docs/auditorias/nfr-14/runbook.md).

## Comprobación desde CLI

Usar GitHub CLI autenticado con acceso al repositorio. `gh variable list` y
`gh secret list` muestran nombres, no el contenido de secretos:

```powershell
gh variable list --repo NexoRuta/NexoRuta --env nexoruta-demo
gh secret list --repo NexoRuta/NexoRuta --env nexoruta-demo
gh variable list --repo NexoRuta/NexoRuta --env nexoruta-ci
gh secret list --repo NexoRuta/NexoRuta --env nexoruta-ci
```

Al definir un secreto, usar el prompt interactivo de `gh secret set` y no pasar
su valor en argumentos, logs, archivos versionados o salida de diagnóstico.
