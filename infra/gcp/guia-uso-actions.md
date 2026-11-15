# Guía de operación de la demo desde GitHub Actions

Las operaciones de demo se ejecutan manualmente en **NexoRuta/NexoRuta → Actions →
NexoRuta - publish integration images** con `workflow_dispatch`. La publicación
automática del canal main es otro workflow; ver [integration-tags.md](integration-tags.md).

| Operación | Comportamiento | Estado que conserva |
| --- | --- | --- |
| `start` desde `main` | Selecciona una publicación main completa, enciende Cloud SQL y las dos VMs y ejecuta despliegue y smoke. | Establece una sesión de hasta cuatro horas para las VMs. |
| `update` desde `main` | Aplica la última publicación main completa a una demo activa; no ejecuta CI ni compila imágenes. | Conserva vencimiento de sesión y SQL. Produce un corte durante migración. |
| `start`/`update` desde `develop` | Construye los gitlinks exactos de develop y publica el canal develop antes de desplegarlo. No ejecuta Integrated CI. | Comparte VMs, Cloud SQL y datos con main. |
| `stop` | Detiene A y B. Puede ejecutarse desde main/develop. | Mantiene Cloud SQL encendido, discos, datos y recursos compartidos. No es destrucción ni limita el costo residual. |

Un push a `main` ejecuta `publish.yml` para publicar una combinación aprobada; no
enciende ni actualiza VMs. `ci.yml` valida PRs a `develop`/`main`, ejecución
manual y semanal. Los cambios en repos de componentes deben llegar al repo raíz
como gitlinks para que la combinación quede fijada y evaluada. Consultar el
resumen de Actions para comprobar el SHA raíz, los tres SHAs de componentes, el
run/attempt y los artifacts de evidencia.

## Actualización y ventana de interrupción

Cada `update` retira ambos nodos del balanceador, detiene las aplicaciones,
ejecuta migraciones una sola vez y aplica/reincorpora primero B y después A. Hay
una interrupción deliberada. Si falla la migración, las aplicaciones siguen
detenidas; si falla la aplicación de un nodo, no se restauran automáticamente
contenedores anteriores ni se revierten migraciones. Corregir el código y
publicar una versión nueva. No programar esta operación como si fuera una
rotación sin corte.

`start`/`update` desde `develop` actualiza el esquema compartido. Una migración de
develop puede impedir el retorno a una release anterior de main. Elegir la rama
con intención y no ejecutar pruebas de develop sobre datos que no deban cambiar.

## Acceso y configuración

La identidad de Actions usa OIDC/WIF y tokens temporales, no claves JSON. El
environment persistente es `nexoruta-demo`; revisar [variables y secretos](github-environment.md).
La configuración pública de SMTP/Mapbox se mantiene en
`compose.yaml > x-app-settings`. SMTP autenticado y Geoapify son opcionales; no
asumir que sus secretos están presentes. La revisión del 14/11/2026 confirmó
nombres de variables y secretos, no valores.

La URL de monitor está protegida por Google OAuth y restringida a
`MONITOR_ALLOWED_EMAILS`. Mailpit requiere credenciales runtime. No copiar
contraseñas, tokens ni contenido de `.env` al resumen o a artifacts.

## Comandos de despacho e inspección

```powershell
# Iniciar la última publicación main completa.
gh workflow run vm-controls.yml --repo NexoRuta/NexoRuta --ref main -f operation=start

# Actualizar una sesión activa desde main. Hay un corte durante migración.
gh workflow run vm-controls.yml --repo NexoRuta/NexoRuta --ref main -f operation=update

# Detener A/B; SQL y recursos persistentes se conservan.
gh workflow run vm-controls.yml --repo NexoRuta/NexoRuta --ref main -f operation=stop

# Inspeccionar runs y esperar el resultado.
gh run list --repo NexoRuta/NexoRuta --workflow vm-controls.yml
gh run watch ID_EJECUCION --repo NexoRuta/NexoRuta
```

No se despachó ningún workflow durante la implementación local de NFR-14. El
camino `reproduce.yml` y sus condiciones se documentan en el [runbook aislado](../../docs/auditorias/nfr-14/runbook.md);
su ejecución requiere aprobaciones GCP y no se sustituye con esta guía.
