# Runbook de recreación aislada NFR-14

Este runbook describe la operación implementada por `scripts/gcp/reproduce.py` para crear, revisar y destruir un proyecto de prueba aislado. La card quedó `Done` por decisión explícita del usuario el 15/11/2026; esa decisión de seguimiento no acredita que la operación se haya ejecutado ni que los gates P0–P8 estén técnicamente completos. P4–P8 mantienen verificaciones remotas y operativas pendientes según la matriz de aceptación.

## Límites y credenciales

- El único destino destructible es el proyecto derivado de un `run_id` nuevo: `nfr14-r-` seguido por sus primeros 16 caracteres hexadecimales. Nunca apuntar al proyecto persistente de la demo.
- El bucket de control y su proyecto viven fuera del proyecto persistente y del proyecto descartable. El código exige versionado, acceso uniforme y prevención de acceso público en ese bucket.
- La creación requiere un principal administrativo de Google Cloud con capacidad explícita para crear proyectos bajo el padre autorizado, vincular la cuenta de facturación, crear el presupuesto y preparar WIF/IAM. El proyecto de control debe tener habilitados Service Usage y Billing Budgets; el principal requiere `serviceusage.services.use` sobre ese proyecto. El módulo fija ese proyecto como `billing_project` de cuota, sin inferirlo de la configuración local. El mismo principal debe estar disponible para `gcloud` y OpenTofu mediante credenciales de corta duración/ADC. No crear ni guardar claves de servicio.
- La operación GitHub usa `GH_TOKEN` o una sesión `gh auth` con permisos para leer artifacts/runs, crear y borrar variables del environment `nexoruta-demo` y disparar `reproduce.yml` desde `main`. No imprimir ni copiar el token.
- Los ocho valores `NFR14_REPRO_*` son variables públicas de identidad del ensayo, se agregan bajo el lock del bucket de control y solo se borran después de comprobar que el proyecto y su presupuesto ya no existen. Si el cleanup queda incompleto, conservar variables e inventario para reintentar.
- Los secretos existentes del environment de GitHub siguen siendo la fuente para las integraciones de aplicación. El ensayo no crea duplicados ni registra sus valores en el repo, el inventario o la evidencia. La geocodificación externa permanece desactivada.
- No ejecutar la recreación desde este checkout de trabajo: `recreate` exige `main` limpio, gitlinks exactos y un directorio de evidencia nuevo y vacío.

## Datos que deben aprobarse antes de crear

Completar y revisar todos estos datos fuera del código. `estimated-window-cost-usd` debe cubrir SQL, VM, LB/IP, discos, Redis, builds, logs y recursos que sigan activos durante la ventana; no asumir que el límite de cuatro horas de VM limita el costo total.

- Tag anotado de integración de `main`, publicación completa y evidencia del CI integrado de esa candidata.
- `run_id`: 32 caracteres hexadecimales minúsculos, nuevo y no usado.
- ID del proyecto principal, proyecto y bucket de control versionado.
- Padre autorizado `organizations/<id>` o `folders/<id>`.
- ID explícito de la cuenta de facturación autorizada.
- Presupuesto mensual de alerta en USD, techo aprobado de costo del ensayo, estimación para la ventana y ventana entre 1 y 4 horas.
- Cuotas, disponibilidad regional, límites de IP/LB/SQL/Redis y procedimiento de cleanup atendible.

El presupuesto es una alerta, no un freno automático del gasto. Si falta una autorización, el ensayo real queda pendiente; no completar el valor por inferencia.

## Crear y verificar

Usar una PowerShell con OpenTofu en la versión fijada por `.opentofu-version`, Python y `gcloud` disponibles, checkout limpio en `main`, y las credenciales administrativas configuradas. Sustituir cada marcador por el valor aprobado. No poner secretos en las variables del ejemplo.

~~~powershell
$RunId = "<32-hex-nuevo>"
$Tag = "<tag-integration-main-validado>"
$Evidence = Join-Path $env:TEMP "nfr14-$RunId"
$ControlProjectId = "<proyecto-control>"
$ControlBucket = "<bucket-control-versionado>"
$MainProjectId = "<proyecto-persistente>"
$Parent = "organizations/<id-aprobado>" # o folders/<id-aprobado>
$BillingAccountId = "<cuenta-billing-aprobada>"
$MonthlyAlertBudgetUsd = "<usd-entero>"
$ApprovedCostCeilingUsd = "<usd-aprobado>"
$EstimatedWindowCostUsd = "<usd-estimado>"
$WindowHours = "<1-a-4>"

python scripts/gcp/reproduce.py recreate `
  --run-id $RunId `
  --integration-tag $Tag `
  --evidence-dir $Evidence `
  --control-project-id $ControlProjectId `
  --control-bucket $ControlBucket `
  --main-project-id $MainProjectId `
  --parent $Parent `
  --billing-account-id $BillingAccountId `
  --monthly-alert-budget-usd $MonthlyAlertBudgetUsd `
  --approved-cost-ceiling-usd $ApprovedCostCeilingUsd `
  --estimated-window-cost-usd $EstimatedWindowCostUsd `
  --window-hours $WindowHours
~~~

`recreate` valida el tag y la procedencia del CI, registra primero el inventario externo, crea únicamente el proyecto y su presupuesto con un plan OpenTofu guardado, configura la fundación, escribe las variables `NFR14_REPRO_*`, dispara el workflow exacto, espera ese run y recoge el artifact sanitizado en el directorio privado y el bucket de control. Si falla, no repetir con el mismo ID a ciegas: inspeccionar el run y el inventario, corregir la causa y conservar el destino para su recuperación/cleanup.

Después de una recreación exitosa, la siguiente comprobación es de solo lectura y debe mostrar cero cambios inesperados:

~~~powershell
python scripts/gcp/reproduce.py inspect `
  --run-id $RunId --control-project-id $ControlProjectId --control-bucket $ControlBucket
python scripts/gcp/reproduce.py plan `
  --run-id $RunId --control-project-id $ControlProjectId --control-bucket $ControlBucket
~~~

`plan` compara el estado externo del proyecto/presupuesto con sus fuentes fijadas; no aplica cambios. El inicio de VM y de la sesión de aplicación se hace dentro del workflow, mediante el plan de sesión con guardas existente. No hay un subcomando administrativo independiente `apply` en `reproduce.py`.

El artifact no afirma que P6 esté completo. El verificador automatizado cubre identidad del CI/release, digests, TLS, HTTP→HTTPS, endpoints de salud, accesos anónimos, login/lectura sintética, Redis TLS/AUTH y parada de VM conservando SQL. Quedan pendientes la consulta de aislamiento RLS entre dos organizaciones, dependencias compartidas completas/roles de base y extensiones PostGIS, revisión manual en navegador, segunda recreación independiente y consumo real de facturación. No reemplazar esos gates por `curl` o mocks.

## Detener la sesión

El workflow para las dos VMs de aplicación y conserva Cloud SQL, discos y recursos compartidos. El `stop` no es teardown ni limita por sí solo el costo residual. Si el workflow falla/cancela, revisar primero su cleanup y la lease; no iniciar otro ensayo hasta confirmar que no hay VM, build ni lock activos.

## Demo persistente: inspección de un posible `destroy`

La demo existente contiene datos y secretos persistentes. No usarla para probar
recreación ni ejecutar `tofu apply` de un plan `-destroy` como parte de NFR-14.
Una inspección de plan puede fallar por `lifecycle.prevent_destroy` en discos y
recursos persistentes; Cloud SQL además mantiene `deletion_protection` y
`deletion_protection_enabled`. Un plan bloqueado solo confirma que la protección
actuó: no acredita destrucción ni autoriza retirarla.

Si en el futuro una baja de la demo se aprueba por separado, primero exportar la
base y los datos requeridos a almacenamiento con acceso controlado, verificar
checksum y restaurar en una instancia independiente; revisar volúmenes,
Data Protection, buckets/versiones, claves, certificados, imágenes, leases,
dependencias y costos residuales. La decisión de desactivar cada protección y
la ventana de baja debe quedar aprobada antes del cambio. No quitar protecciones
ni ejecutar apply por inferencia.

Para solo inspeccionar el plan de destrucción de la configuración actualmente
declarada, usar un terminal privado con credenciales autorizadas y el bucket
exacto del estado de demo. El comando descarga/lee el estado remoto y refresca
recursos; el plan local puede incluir datos sensibles, así que no subirlo ni
copiar la salida a tickets públicos:

~~~powershell
$ProjectId = "<proyecto-demo-confirmado>"
$StateBucket = "<bucket-estado-demo-confirmado>"
$PrivateTofuData = Join-Path $env:TEMP "nfr14-demo-destroy-review"
if (Test-Path -LiteralPath $PrivateTofuData) { throw "Use a new private TF_DATA_DIR path." }
New-Item -ItemType Directory -Force -Path $PrivateTofuData | Out-Null
$env:TF_DATA_DIR = $PrivateTofuData

tofu -chdir=infra/gcp/demo init -reconfigure -input=false -lockfile=readonly `
  -backend-config="bucket=$StateBucket" -backend-config="prefix=demo/vm"
tofu -chdir=infra/gcp/demo plan -destroy -input=false -lock-timeout=5m -no-color `
  -var="project_id=$ProjectId"
~~~

Revisar el resultado sin guardar un plan binario ni aplicar nada. Si OpenTofu
rechaza destrucción por protección, detenerse y conservarla. Si el plan propone
una baja completa porque la protección ya no está activa, detenerse igualmente:
no aplicar y verificar cómo cambió la protección/estado antes de cualquier otra
acción. P5 prueba destrucción solamente en el proyecto descartable, no aquí.

## Inspeccionar y destruir el proyecto descartable

Conservar el directorio `$Evidence` y el inventario externo. Revisar el estado exacto y los blockers antes de preparar el plan:

~~~powershell
python scripts/gcp/reproduce.py inspect `
  --run-id $RunId --control-project-id $ControlProjectId --control-bucket $ControlBucket
python scripts/gcp/reproduce.py destroy-plan `
  --run-id $RunId --control-project-id $ControlProjectId --control-bucket $ControlBucket
~~~

`destroy-plan` rechaza leases/locks, VMs activas, builds activos, un estado distinto y cualquier plan que no destruya exactamente el proyecto registrado y su presupuesto. El artifact queda fuera del proyecto. Confirmar además que los datos son sintéticos y que ya se guardó la evidencia necesaria; este teardown sí elimina SQL, discos y los demás datos del proyecto descartable.

Solo después de revisar el resumen devuelto, aplicar el mismo plan guardado al mismo ID:

~~~powershell
$DisposableProjectId = "nfr14-r-$($RunId.Substring(0, 16))"
python scripts/gcp/reproduce.py destroy `
  --run-id $RunId `
  --control-project-id $ControlProjectId `
  --control-bucket $ControlBucket `
  --confirm-project $DisposableProjectId
~~~

El cleanup espera confirmación de borrado del proyecto y ausencia del presupuesto antes de retirar las ocho variables del environment. Si Google sigue mostrando `DELETE_REQUESTED`, el proyecto o el presupuesto permanece, GitHub no autoriza la limpieza o hay un lock/lease, detenerse: variables e inventario se conservan para `inspect` y reintento. No borrar estado ni cambiar protecciones globales.

La segunda recreación usa un `run_id`, proyecto y estado nuevos, conserva el mismo tag y parámetros aprobados, y solo empieza tras verificar la ausencia del proyecto y del presupuesto del primer run. Los IDs de proyectos pendientes de borrado no se reutilizan.

## Estado actual de evidencia

La implementación local y las pruebas automatizadas no son un ensayo real. Aún requieren ejecución desde `main`/CI y las identidades aprobadas el primer y segundo ensayo en GCP, su cleanup, la revisión visual, la inspección RLS/dependencias acordadas y el informe de consumo/costos. Mantener NFR-14 abierta hasta que esos gates queden documentados con sus run IDs, hashes, fuentes, artifacts y costos reales.
