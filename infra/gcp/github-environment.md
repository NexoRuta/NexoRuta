# ConfiguraciÃ³n de GitHub Actions

En el repo madre `NexoRuta/NexoRuta`, abrir **Settings â†’ Environments â†’ New
environment**, crear **`nexoruta-demo`** y agregar los siguientes valores en
**Environment variables** y **Environment secrets**. Permitir despliegues desde
`main`. Los jobs de publicaciÃ³n, operaciÃ³n de VM y Android declaran ese environment.

No hace falta duplicar `GCP_PROJECT_ID` ni otras variables a nivel del repositorio.
Los workflows validan la configuraciÃ³n dentro del runner, despuÃ©s de cargar el
environment. Un valor requerido faltante produce un error con su nombre.

## Variables requeridas

Reemplazar `PROJECT_ID` por el ID textual del proyecto y `PROJECT_NUMBER` por su
nÃºmero, que son valores diferentes.

| Nombre | Valor |
| --- | --- |
| `GCP_PROJECT_ID` | `PROJECT_ID` |
| `GCP_REGION` | `southamerica-west1` |
| `GCP_ZONE` | `southamerica-west1-a` |
| `GCP_STATE_BUCKET` | `PROJECT_ID-tofu-state` |
| `GCP_DELIVERY_BUCKET` | `PROJECT_ID-nexoruta-delivery` |
| `GCP_WORKLOAD_IDENTITY_PROVIDER` | `projects/PROJECT_NUMBER/locations/global/workloadIdentityPools/nexoruta-github/providers/demo-vm` |
| `GCP_DEPLOY_SERVICE_ACCOUNT` | `nexoruta-demo-deployer@PROJECT_ID.iam.gserviceaccount.com` |

Estos son los nombres generados por OpenTofu. La preparaciÃ³n inicial con
`scripts/gcp/setup.ps1` crea WIF, IAM, buckets y secretos en GCP y escribe las siete
variables en el environment. Se pueden obtener sus valores exactos con:

```powershell
tofu -chdir=infra/gcp/bootstrap output -json github_variables
gcloud projects describe PROJECT_ID --format='value(projectNumber)'
```

La autenticaciÃ³n de GCP usa **OIDC / Workload Identity Federation**. Los valores
de provider y service account identifican la relaciÃ³n de confianza; no son claves
privadas. `google-github-actions/auth` solicita el token temporal para cada job.
**No hay que cargar una clave JSON ni un access token como secret**. La confianza tambi?n contempla el sujeto OIDC con IDs inmutables que usa GitHub en este repo; no hay que desactivar esa opci?n en GitHub. Google Cloud
debe tener creado el provider y los permisos definidos en bootstrap antes de la
primera ejecuciÃ³n. [DocumentaciÃ³n de la acciÃ³n](https://github.com/google-github-actions/auth).

## Variables GCP opcionales en GitHub

| Nombre | Valor si se omite | Uso |
| --- | --- | --- |
| `GCP_BASE_DOMAIN` | VacÃ­o | Dominio propio, por ejemplo `demo.ejemplo.uy`; sin Ã©l se usa `sslip.io`. |
| `GCP_MANAGE_DNS` | `false` | `true` para gestionar el dominio indicado mediante Cloud DNS. |

## ConfiguraciÃ³n pÃºblica de aplicaciones en Compose

Estas variables se configuran en **`compose.yaml` de la raÃ­z, bloque
`x-app-settings`**, junto con las demÃ¡s variables locales. No requieren variables
de GitHub. Los workflows usan `docker compose config` para leer el bloque despuÃ©s
del checkout y cargar sus valores en el runner. No necesitan un daemon Docker.
Al cambiarlo, publicar el cambio en `main` y ejecutar `start` o `update`.

| Nombre en `x-app-settings` | Valor inicial | Uso |
| --- | --- | --- |
| `MAPBOX_PUBLIC_TOKEN` | VacÃ­o | Token pÃºblico Mapbox del APK; necesario para probar mapas. |
| `SMTP_HOST` | `mailpit` | Servidor SMTP; con Mailpit los mensajes quedan en la demo. |
| `SMTP_PORT` | `1025` | Puerto del servidor SMTP; definirlo al usar un proveedor externo. |
| `SMTP_SSL` | `false` | `true` o `false`, segÃºn el servidor SMTP. |
| `SMTP_FROM` | `demo@nexoruta.test` | Remitente; usar una direcciÃ³n autorizada por el proveedor externo. |

## Secrets del repo madre, environment nexoruta-demo

| Nombre | CuÃ¡ndo configurarlo |
| --- | --- |
| `SUBMODULES_TOKEN` | Si los repos de backend/frontend/mobile son privados: token dedicado con acceso de lectura a los tres (`Contents: read`). |
| `SMTP_USERNAME` | Si el proveedor SMTP requiere autenticaciÃ³n. |
| `SMTP_PASSWORD` | Junto con `SMTP_USERNAME`. |
| `GEOAPIFY_API_KEY` | Para probar geocodificaciÃ³n con Geoapify. |

Antes de `start` o `update`, el runner combina la configuraciÃ³n pÃºblica de Compose
con los secrets de GitHub y los copia al secreto privado
`nexoruta-demo-integrations` de GCP. Compose y GitHub Secrets son la fuente de
esos ajustes; el siguiente despliegue vuelve a aplicar sus valores. La VM
lee el secreto con su propia cuenta de servicio; los valores no aparecen en los
argumentos de los comandos ni se imprimen en logs. `stop` no sincroniza secretos.

El bloque `x-app-settings` contiene solo configuraciÃ³n pÃºblica. El archivo `.env`
privado generado dentro de la VM contiene ademÃ¡s credenciales y no se publica en Git.
Si ya creaste `SMTP_HOST`, `SMTP_PORT`, `SMTP_SSL`, `SMTP_FROM` o
`MAPBOX_PUBLIC_TOKEN` como variables de GitHub, podÃ©s eliminarlas: se usa Compose.

Las contraseÃ±as de PostgreSQL, RabbitMQ, MongoDB y usuarios iniciales, las claves
JWT/cifrado y las credenciales de firma Android se generan y conservan mediante
OpenTofu/Secret Manager. No necesitan entradas manuales en GitHub. Tampoco se
copia la sesiÃ³n personal de `gcloud` del PC al runner.

## Secrets de los tres repos de aplicaciones

En **cada uno** de `NexoRuta-Backend`, `NexoRuta-Frontend` y `NexoRuta-Mobile`, crear
tambiÃ©n el environment **`nexoruta-demo`**, permitido desde `main`, con este secret:

| Nombre | Valor |
| --- | --- |
| `NEXORUTA_INTEGRATION_TOKEN` | Token con acceso al repo madre: `Contents: write` si es fine-grained, o scope `repo` si es OAuth/clÃ¡sico, para enviar `repository_dispatch`. Preferir uno dedicado. |

Esos jobs solo notifican una publicaciÃ³n de imÃ¡genes. No necesitan variables ni
credenciales de GCP y no inician la VM.

Este secret es necesario para publicar automÃ¡ticamente al pushear en los repos de
aplicaciones. Los botones manuales `start`, `update` y `stop` del repo madre pueden
usarse sin Ã©l. La CLI `gh` guarda secrets, pero no crea PATs nuevos: un PAT dedicado
se genera en GitHub con acceso Ãºnicamente a `NexoRuta/NexoRuta` y luego se carga
en los tres environments. TambiÃ©n es posible usar un token OAuth existente con
scope `repo`, teniendo en cuenta que conserva todos sus permisos originales.

Para cargar el token dedicado con una sola entrada privada en la terminal:

```powershell
./scripts/gcp/setup-integration-token.ps1
```

Crear el fine-grained PAT con Resource owner `NexoRuta`, **Only select repositories**
seleccionando Ãºnicamente `NexoRuta/NexoRuta`, `Contents: Read and write` y hasta
90 dÃ­as de vigencia. El script pide el valor sin mostrarlo, comprueba el permiso
de dispatch con un evento de prueba fuera de los tipos de delivery, lo carga en
los tres environments y verifica su existencia. Usa la sesiÃ³n administrativa de
`gh` para guardar secrets; el PAT nuevo no necesita administrar los repos de apps.

## CI de pull requests

El CI de cÃ³digo de PR usa un environment independiente **`nexoruta-ci`**, sin
credenciales de despliegue ni secrets de aplicaciones. Si necesita descargar
submÃ³dulos privados, agregar allÃ­ Ãºnicamente `SUBMODULES_TOKEN` con lectura.
El CI de `main`, incluyendo el workflow reutilizado por delivery, usa
`nexoruta-demo`. No se habilita OIDC de GCP en los jobs de pruebas.

## Configurar desde la terminal

```powershell
gh api --method PUT repos/NexoRuta/NexoRuta/environments/nexoruta-demo
gh variable set GCP_REGION --repo NexoRuta/NexoRuta --env nexoruta-demo --body southamerica-west1
gh variable set GCP_ZONE --repo NexoRuta/NexoRuta --env nexoruta-demo --body southamerica-west1-a

# Sin pasar el valor sensible por argumentos: gh solicita el secret.
gh secret set SUBMODULES_TOKEN --repo NexoRuta/NexoRuta --env nexoruta-demo
gh secret set GEOAPIFY_API_KEY --repo NexoRuta/NexoRuta --env nexoruta-demo
gh secret set SMTP_USERNAME --repo NexoRuta/NexoRuta --env nexoruta-demo
gh secret set SMTP_PASSWORD --repo NexoRuta/NexoRuta --env nexoruta-demo
```

La configuraciÃ³n no cambia los disparadores: push a `main` prueba y publica;
`start`, `update` y `stop` se eligen manualmente en **Run workflow**.
