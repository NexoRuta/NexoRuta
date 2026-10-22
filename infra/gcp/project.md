# Proyecto GCP de la demo

Proyecto creado y configurado desde la CLI el 22/10/2026.

| Dato | Valor |
| --- | --- |
| Project ID | `nexoruta-demo-20261022` |
| Project number | `1090571196455` |
| Estado del proyecto | `ACTIVE` |
| Facturaci?n | Vinculada a una cuenta abierta; `billingEnabled=true` |
| Regi?n | `southamerica-west1` (Santiago) |
| Zona | `southamerica-west1-a` |
| VM | `n4-highcpu-8`: ocho vCPU y 16384 MiB |

[Abrir el proyecto](https://console.cloud.google.com/home/dashboard?project=nexoruta-demo-20261022).

El bootstrap de OpenTofu est? aplicado: APIs, cuentas de servicio e IAM, WIF,
buckets privados, Artifact Registry, Secret Manager, Firebase/Android,
alerta de presupuesto y controlador independiente de apagado. Su estado est? en
`gs://nexoruta-demo-20261022-tofu-state/foundation/default.tfstate`.

Se solicit? por CLI una cuota de ocho vCPU C4 en Santiago mediante
`nexoruta-demo-c4-santiago`; Google Cloud la deneg?. Se usa N4 highcpu, disponible
en la misma zona y con cuota suficiente, conservando ocho vCPU y 16 GiB.
La API de cuotas qued? incorporada al bootstrap. Los precios actualizados est?n
en [costs.md](costs.md).

El environment `nexoruta-demo` del repo madre tiene las siete variables GCP
requeridas y `GCP_MANAGE_DNS=false`. Los environments de los tres componentes
contienen el token dedicado de notificaci?n y permiten ?nicamente `main`.
Los workflows est?n publicados. Los pushes prueban y publican im?genes;
solo una ejecuci?n manual puede iniciar, actualizar o detener la VM.

GitHub usa sujetos OIDC con IDs inmutables en este repositorio. La condici?n WIF
acepta ese formato y el formato anterior, comprobando adem?s IDs de repo y
propietario, nombre del repo, branch `main`, environment, workflow y tipo de evento.
El provider es:

```text
projects/1090571196455/locations/global/workloadIdentityPools/nexoruta-github/providers/demo-vm
```

La infraestructura de aplicaci?n se gestiona desde `infra/gcp/demo` con estado
GCS independiente en `demo/vm`. El workflow manual crea o inicia Cloud SQL y la
VM, despliega contenedores por digest, ejecuta migraciones y comprueba HTTPS.
Los endpoints y el vencimiento real aparecen en el resumen de
[Actions](https://github.com/NexoRuta/NexoRuta/actions/workflows/demo-vm.yml).
Consultar ese resumen o `tofu output -json endpoints` para conocer las URLs;
el estado encendido/apagado cambia entre sesiones de cuatro horas.

La sesi?n local de Google Cloud y las Application Default Credentials est?n
fuera del repositorio, con este proyecto como quota project. GitHub usa tokens
temporales OIDC y no recibe una clave JSON ni la sesi?n personal de la CLI.
El proyecto y la vinculaci?n de facturaci?n se administran por CLI y quedan
fuera del estado OpenTofu.

Para sincronizar el bootstrap y sus variables:

```powershell
./scripts/gcp/setup.ps1 -ProjectId nexoruta-demo-20261022
```

El inicio de la VM sigue siendo manual. Ver [github-environment.md](github-environment.md)
para variables, secrets y configuraci?n p?blica centralizada en Compose.
