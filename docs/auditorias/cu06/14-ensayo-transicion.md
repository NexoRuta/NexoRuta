# CU06 — transición preparada y ensayada en aislamiento

> Estado histórico del ensayo. Con autorización posterior del usuario para regularizar exclusivamente datos ficticios, la intervención habitual se completó y verificó en [15-activacion-local-b1-b5.md](15-activacion-local-b1-b5.md). La evidencia y las limitaciones de este ensayo se conservan sin reinterpretarlas como constataciones físicas.

## Resultado y bloqueo de activación

**No intervenir todavía la instancia habitual.** Se produjo un artefacto administrativo compatible con Stage, un respaldo cifrado recuperado y SQL separado para las cuatro etapas. El ensayo con datos locales **se detuvo correctamente en Stage**: Enforce encontró conflictos. En una línea exclusivamente sintética, las cuatro etapas y la API/Backoffice publicados funcionaron, incluidos los tres GET y Chromium a 320 px.

No se ejecutó `database-migrate`, `levantar-entorno-dev.bat`, despliegue, conciliación operativa, cambio de rama, commit ni push. Sin subagentes ni llamadas viales reales. Los **404 habituales no se declaran resueltos**: no se sustituyeron sus servicios.

| Línea | Observado | Límite |
|---|---|---|
| Respaldo local restaurado | Dos restauraciones coinciden en 61 tablas; Stage aplicado; Enforce rechazado | No acredita disponibilidad física |
| Artefacto Stage + datos restaurados | Inicio con rol restringido; login200; flota401 anónima y **403 con la cuenta configurada**; operaciones normales503 | No se ocultó el rechazo de autorización |
| Stage exacto + fixtures | Autenticación, lectura de ruta/ocupación, comando existente, idempotencia y rechazo sin cambios parciales aprobados | Hechos sintéticos, no conciliación local |
| Cuatro etapas + fixtures | API publicada: vehículos/flota/perfiles/histórico200; Backoffice publicado + Chromium, CRUD y320px aprobados | No es habilitación operativa ni precisión vial en Uruguay |

Evidencia: [procedencia](evidencias/transicion/provenance.json), [Stage](evidencias/transicion/stage-probes.json), [API publicada](evidencias/transicion/published-current-probes.json), [reconstrucción](evidencias/transicion/reproducibility.json).

## 1. Qué significa Stage y qué puede ejecutarse

**Stage es una migración preparatoria y una pausa de mantenimiento**, no un ambiente staging, rama ni release histórico.

| Desde → destino | Cambios y condición | Código admisible después |
|---|---|---|
| `20261030120000_ListImportedShipmentReferences` → `20261101184716_StageFleetOccupations` | Verificación inicial, OcupacionesRuta/HechosFlota, RLS/FKs/guards. Backfill Despachada/EnCurso como Legada, versión0, adquisición/actor/retorno desconocidos. Sin índices físicos exclusivos | Solo mantenimiento Stage explícito, escritores anteriores detenidos |
| Stage → `20261101185119_EnforceFleetOccupationExclusivity` | Rechaza conflictos globales de vehículo/repartidor y legadas sin adquisición constatada; instala índices únicos activos sin fecha | Detener mantenimiento antes del SQL; no abrir tráfico |
| Enforce → `20261101203256_AddOperationalBaseAndTemporalPlan` | BasesOperativas, HojasRuta.PlanTemporal, ParadasRuta.ServicioMinutos | Aplicaciones normales detenidas: falta B4 |
| B3 → `20261101213104_AddRoadEstimationHistory` | Perfiles, historial y presupuesto de estimaciones | API normal B1–B5 con StageOnly=false, migración/seed/routing real apagados |

B5 no agrega migración. El modelo normal actual **no es compatible con Stage**: selecciona PlanTemporal/ServicioMinutos todavía inexistentes. RED observado: `42703 column h.PlanTemporal does not exist`. No se añadieron/borraron migraciones.

Los [cuatro SQL](evidencias/transicion/sql) registran exclusivamente su destino y conservan transacciones. Aplicarlos por separado, ON_ERROR_STOP, con identidad autorizada que vea todos los tenants; nunca rol API ni concatenación de pendientes.

## 2. Artefacto Stage: solución explícita, no historia inventada

No se acreditó un artefacto preexistente compatible. Se construyó desde las fuentes actuales dirty, **sin quitar B3–B5**:

- `FleetTransition__StageOnly=true`: modelo EF administrativo ignora solo PlanTemporal y ServicioMinutos. Nunca generar migraciones con esta proyección.
- Reutiliza controladores, dominio, repositorio, permisos, RLS, bloqueo por operador, versiones e idempotencia actuales.
- Inicio exige historial cuyo último registro sea exactamente Stage; rechaza otro esquema. Rechaza CLI, auto-migración, seed, inicialización y routing real.
- Allowlist: salud, login, usuario/permisos, GET flota y seis POST existentes: conciliar, anular, retorno, liberar, verificar-inicial, recibir-carga-inicial. El resto503 antes de ejecutarse: no despacho, sync móvil, importación o cálculos.
- El primer arranque restringido falló cerrado:42501 SELECT denegado sobre `__EFMigrationsHistory`. Se ensayó [GRANT SELECT temporal](evidencias/transicion/sql/stage-maintenance-read.sql), sin privilegio de migrar. Revocarlo después de detener mantenimiento.
- La cuenta configurada obtiene permisos listados200 pero flota403. La política existente exige además rol operativo protegido y código permitido (`EfPermisosUsuarioRepository.PuedeGestionarDecisionesOperativasEnvioAsync`). No se cambiaron roles/cuentas ni se debilitó esa política. Debe seleccionarse/provisionarse legítimamente un acceso autorizado antes de conciliar.

### Procedencia y reproducción

```powershell
$W = "$env:LOCALAPPDATA\NexoRuta\cu06-transition\c83b359a6bfe"
```

Entrega privada: `source/`, manifiesto SHA256 de fuentes/HEAD/dirty, `api/`, `backoffice/`, manifiestos de publicación, SQL, logs, dumps cifrados e inventario de revisión humana. SDK **10.0.401**. La cápsula congela el código de aplicación verificado; las ampliaciones posteriores de tests están en el checkout/evidencias, sin modificar el binario congelado.

Git preservado: raíz develop `1ef21751106e727bb15f4f75d3976196857e2ca1`; backend fix/zonacobertura `a0aa204ffc3390606b9f04bc8a57424b598c205c`; frontend fix/zonacobertura `e05c0de27702cf9909656bed0a0d389152c25806`; mobile fix/zonacobertura `78f65e1ca534888270028d68e7abe86460989e12`. Gitlinks sin mover. De 304 archivos locales preexistentes respaldados, solo Program.cs recibió la adición de mantenimiento; todos los demás permanecieron byte a byte.

```powershell
# $NuevoW: directorio privado NUEVO producido por backup; no sobrescribe source.
python scripts/cu06/prepare-artifact.py --work $NuevoW
python scripts/cu06/verify-artifact.py --work $W
```

Segunda compilación no incremental/publicación: **49/49 archivos API idénticos**. Backoffice244/245 idénticos; solo difiere staticwebassets.endpoints.json por headers Last-Modified generados. Comparación estructural quitando únicamente esos headers coincide; **no se afirma identidad binaria integral de Backoffice**. Originales/hashes conservados.

Se verificaron DLL publicados en Windows/.NET10, no una imagen Linux desplegada. Antes de sustituir el API Docker habitual hay que comprobar artefacto/configuración de esa ejecución; no se aprobó un release operativo.

## 3. Respaldo y recuperación ejecutados

`transition.py backup` leyó la base habitual con pg_dump custom/CREATE/owners/ACL, globals sin passwords y .env cifrado aparte. Snapshot MVCC consistente durante actividad: **no reemplaza el respaldo final con escritores congelados**.

- ACL: cuenta Windows actual y SYSTEM; DPAPI CurrentUser. Cifrar/descifrar y SHA256 comprobados antes de quitar plaintext temporal propio. Recuperación ligada a esta cuenta/máquina; falta definir custodia/exportación autorizada portable.
- Clone `nexoruta-cu06-rehearsal-c83b359a6bfe`, misma imagen PostgreSQL/PostGIS por digest, credenciales nuevas, puerto127.0.0.1:1887, redes propias, tmpfs. Runner valida label e ID exactos antes de escribir; apply/restore no aceptan la base habitual.
- Dos restores coincidieron en61 tablas. Recuperación de checkpoints comparó historial, filas y esquema con owners/ACL/RLS/triggers/constraints. Solo excluye nonce aleatorio de `\restrict` del hash de esquema. MD5 agregado sirve para comparar filas; SHA256 protege integridad de archivos.
- Globals PG18 requirió remapear **solo en el clon** el grantor de tres membresías al bootstrap nuevo. Miembros/privilegios conservados, no identidad del grantor de cluster. Owners/ACL de objetos restaurados/verificados. Ante pérdida total de cluster hay que reprovisionar passwords por canal seguro; no están en globals.
- Se restauraron realmente baseline-verified, stage-recoverable y stage-held en bases nuevas `cu06_recovery_*`, sin sobrescribir datos.
- Intentos iniciales: red internal no publicaba puerto; se corrigió solo el clon y restauró nuevamente. Restore se detuvo por grantor PG18 hasta corregirlo. No se ignoraron errores ni se tocaron servicios habituales.

```powershell
python scripts/cu06/transition.py backup
# Usar la ruta privada NUEVA impresa como $NuevoW:
python scripts/cu06/transition.py restore --work $NuevoW
python scripts/cu06/transition.py verify-restore --work $NuevoW
# Ya ejecutados; repetir el mismo nombre se RECHAZA para no sobrescribir:
python scripts/cu06/transition.py verify-checkpoint --work $W --name baseline-verified
python scripts/cu06/transition.py verify-checkpoint --work $W --name stage-held
```

Tmpfs no sobrevive restart; los dumps cifrados en disco sí. No reiniciar el clon para conservar su estado. No se borraron volúmenes.

## 4. Ensayo sobre los datos restaurados

1. Baseline64 migraciones, checkpoint recuperado.
2. Stage aplicado exclusivamente y checkpoint recuperado.
3. **4 ocupaciones activas, 4 adquisiciones desconocidas, 4 retornos desconocidos; 1 grupo conflictivo de vehículo y 1 de repartidor.**
4. Enforce rechazado: `Fleet occupation conflicts detected...`; rollback de transacción, historial todavía Stage y sin índices nuevos.
5. Ninguna conciliación/anulación/recepción/retorno/liberación/verificación sobre datos copiados. **HechosFlota=0**. No se eligió ganador.
6. Intentar saltar Stage→B3 con runner rechaza antes de SQL por etapa inesperada.
7. Comparación de columnas del baseline después de migración/login: solo cambió `__EFMigrationsHistory`; filas de negocio preexistentes iguales.

`$W/human-review-private.json` conserva IDs/estados/fechas/versiones para inspección humana bajo ACL, no en el repositorio. Cada caso requiere constatar el trabajo/custodia real. Anular únicamente si nunca inició/cargó/salió y el comando lo admite; confirmar vigencia o resolver jornada/custodia en los demás casos. No se seleccionaron actores ni confeccionaron constataciones físicas.

## 5. Pruebas y revisión real de los artefactos

`FleetBoundedTransitionTests` parte de baseline vacío y aplica cuatro SQL independientes comprobando historial y ausencia de hechos inventados entre etapas. Luego usa fixtures. Opt-in inicia **DLL Release de la cápsula**, rol API NOSUPERUSER/NOBYPASSRLS, API/Backoffice en loopback y Chromium; procesos terminados al finalizar.

| GET publicado / fixture | HTTP |
|---|---|
| `/api/reparto/vehiculos` |200|
| `/api/reparto/flota` |200|
| `/api/reparto/perfiles-viales` |200|
| `/api/rutas/{id-sintetico}/estimaciones` |200|

Chromium: menú→Vehículos, alta/edición, precisión, habilitación, versión, valores, teclado, doble envío, perfiles/flota/histórico y320px. Escrituras exclusivamente sintéticas; sin Geoapify. Capturas nuevas generadas e inspeccionadas: [vehículos320](evidencias/transicion/vehiculos-320.png), [1440](evidencias/transicion/vehiculos-1440.png), [flota](evidencias/transicion/flota-320.png), [perfiles](evidencias/transicion/perfiles-320.png), [histórico](evidencias/transicion/historial-320.png), [menú](evidencias/transicion/menu-320.png).

- RED Stage por PlanTemporal inexistente: [log](evidencias/transicion/cu06-transition-stage-red2.log).
- **12/12**: siete checks Stage (ruta/ocupación y retorno rechazado sin inicio incluidos), cuatro etapas, CRUD HTTP, browser checkout, transición/conflicto/conciliación sintética y aislamiento HTTP/RLS/hechos inmutables. [Log](evidencias/transicion/cu06-transition-functional.log).
- Capacidad vigente/snapshot al despacho: **2/2**. En ese lote falló solo el nuevo runner publicado: exigía Pooling=false, pero la fixture restringida usa Pooling=true. Guard del runner corregido, no producto. [Log inicial](evidencias/transicion/cu06-transition-published.log).
- Reejecución acotada con artefactos publicados **1/1**, incluye cuatro etapas/API/Backoffice/Chromium. [Log final](evidencias/transicion/cu06-transition-published-final.log). No sumar reintentos como aceptaciones distintas.
- `git diff --check` backend y compilación Python aprobados. No se repitió aceptación completa B2.
- Fallo arquitectónico previo `ShipmentBoundaryTests.ShipmentEndpoints_DeclareApiOwnedResponses` (esperado2/actual7): **pendiente, no corregido ni reejecutado aquí**. Warnings NU1510/CS8629 ajenos conservados.

```powershell
$env:NEXORUTA_REHEARSAL_ARTIFACTS = $W
$env:NEXORUTA_PLAYWRIGHT_MODULE = 'C:\Users\Josec\topaz-docs\node_modules\playwright-core'
dotnet test backend/tests/NexoRuta.IntegrationTests --no-restore --filter FullyQualifiedName~FleetBoundedTransitionTests
```

## 6. Aplicación futura: comandos preparados, NO ejecutados en operación

### Antes de Stage: ventana y ausencia verificable de escritores

Inventario real Compose: api, worker, backoffice, commerce, admin, tracking; worker-kafka/migradores bajo perfiles. Flags normales ApplyMigrations=false/SeedData=false **no detienen `database-migrate`**, que llama MigrateAsync sin destino.

1. Autorizar ventana/destino/identidades. No usar batch general, `compose up` general, profile rls-admin, rls-migrator, bootstrap ni pipeline migrate. La segunda etapa se impide **manteniendo fuera de ejecución ese job/comando**, no confiando solamente en flags.
2. Detener escritores API/worker/worker-kafka, importadores/scripts y portales de la ventana. Impedir relanzamientos por watch/servicios/jobs/restart policies. Conservar colas y sync móvil pendiente, no vaciarlos.
3. Verificar `docker compose --profile '*' ps -a`, inventario completo de containers, procesos dotnet/python pertinentes con `Get-CimInstance Win32_Process`, tareas y servicios autorizados; registrar imágenes/revisiones/estado detenido sin exponer argv secretos. No se hicieron esas paradas aquí.
4. Complementar con sesiones PostgreSQL y transacciones preparadas; **sin texto de consultas**. Cero sesiones no demuestra que un proceso no pueda reconectar: verificar también su relanzamiento deshabilitado. Cero escritores anteriores antes del mantenimiento.

```sql
SELECT usename, application_name, client_addr, state, count(*)
FROM pg_stat_activity WHERE datname=current_database() AND pid<>pg_backend_pid()
GROUP BY 1,2,3,4;
SELECT gid, prepared FROM pg_prepared_xacts WHERE database=current_database();
SELECT "MigrationId" FROM "__EFMigrationsHistory" ORDER BY "MigrationId" DESC LIMIT 1;
```

Crear respaldo **nuevo durante el congelamiento** y restaurarlo/verificarlo, no reutilizar ciegamente el snapshot activo del ensayo:

```powershell
python scripts/cu06/transition.py backup --expected-migration 20261030120000_ListImportedShipmentReferences
# Retener ruta nueva; restore/verify-restore antes de autorizar Stage.
```

### Un SQL por vez, con parada obligatoria

Definición para la futura ventana autorizada. Antes comprobar ID/destino/historial y SHA256 contra provenance.json. Recibe bytes por stdin y no expone passwords en argv. **No se invocó esta función aquí.**

```powershell
$Sql = (Resolve-Path docs/auditorias/cu06/evidencias/transicion/sql).Path
function Invoke-Cu06StageSql([ValidateSet('stage','enforce','b3','b4')] [string]$Step) {
@'
import pathlib,subprocess,sys
result=subprocess.run(['docker','exec','-i','nexoruta-postgres','sh','-c',
 'exec psql -X -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB"'],
 input=pathlib.Path(sys.argv[1]).read_bytes())
raise SystemExit(result.returncode)
'@ | python - "$Sql\$Step.sql"
    if ($LASTEXITCODE -ne 0) { throw 'Etapa rechazada: detener, no continuar.' }
}
# SOLO tras ventana autorizada, baseline verificado y respaldo final recuperable:
Invoke-Cu06StageSql stage
# PARAR hasta conciliación autorizada y prechecks aprobados:
# Invoke-Cu06StageSql enforce
# Después, todavía sin aplicaciones normales:
# Invoke-Cu06StageSql b3
# Invoke-Cu06StageSql b4
```

Historial después de cada SQL. Durante conciliación debe estar Stage y **no Enforce**. Mantenimiento Stage rechaza iniciar con Enforce/B3/B4; no puede impedir que un migrador externo actúe, que debe permanecer detenido. Aplicar temporalmente `stage-maintenance-read.sql` mediante identidad autorizada. Arrancar solo mantenimiento, con conexión restringida/JWT por canal seguro, sin ponerlos en documentación/logs:

```powershell
# Proceso dedicado; cwd $W/api y configuración de aplicación válida.
$env:FleetTransition__StageOnly = 'true'
$env:DatabaseInitialization__ApplyMigrations = 'false'
$env:DatabaseInitialization__SeedData = 'false'
$env:PlatformInitialization__Enabled = 'false'
$env:RoutingGeoapify__PermitirLlamadasReales = 'false'
$env:RoutingGeoapify__ApiKey = ''
$env:ASPNETCORE_URLS = 'http://127.0.0.1:5189'
$env:DataProtection__KeysDirectory = "$W\maintenance-keys"
# dotnet "$W\api\NexoRuta.Api.dll"
```

`python scripts/cu06/probe-stage.py --work $W` **solo usa el clon propio**; arranca/detiene el artefacto, consulta/login y no confirma hechos. En esta copia registra403 explícito.

### Conciliar y continuar

1. Disponer de un acceso legítimo con autoridad operativa. Motivo/ComandoId/ocupación/versión actuales en los POST existentes. No reintentar automáticamente con versión nueva.
2. Constatar los cuatro casos privados y usar los comandos pertinentes. Fecha/GPS/ETA/cierre/desactivación nunca prueban retorno o descarga. No elegir un ganador por fecha ni acreditar hechos para que pase Enforce.
3. Detener mantenimiento, guardar respaldo Stage final recuperable y recibos; revocar SELECT temporal de historial. Aplicar solo Enforce tras prechecks. Si falla, conservar Stage y volver a conciliación, no saltar ni deshabilitar índices.
4. Antes de B3/B4, respaldos independientes por etapa esperada, recuperar/verificar y mantener escritores detenidos:

```powershell
# Antes de Enforce, después de la conciliación real:
python scripts/cu06/transition.py backup --expected-migration 20261101184716_StageFleetOccupations
# Solo después: Invoke-Cu06StageSql enforce
python scripts/cu06/transition.py backup --expected-migration 20261101185119_EnforceFleetOccupationExclusivity
# Solo después: Invoke-Cu06StageSql b3
python scripts/cu06/transition.py backup --expected-migration 20261101203256_AddOperationalBaseAndTemporalPlan
# Solo después: Invoke-Cu06StageSql b4
```

5. Después de B4, StageOnly=false y migración/seed/routing real todavía apagados. Comprobar artefacto efectivo y Backoffice apuntando a esa API; verificar vehículos y los tres GET **desde la instancia habitual**. Solo entonces evaluar sus404. No reactivar el migrador general como parte de la pausa.

## 7. Recuperación por etapa y escrituras posteriores

| Fallo | Snapshot para recuperar | Estado acreditado |
|---|---|---|
| Stage o conciliación | Baseline para deshacer todo; Stage final para conservar hechos constatados | Baseline y dos Stage recuperados/comparados |
| Enforce rechazado | Stage se mantiene por rollback del SQL | Rechazo real, historial Stage confirmado |
| Enforce aplicado, problema posterior | Stage final anterior a Enforce | No alcanzado con datos locales; no se inventó checkpoint post-conciliación |
| B3 | Snapshot Enforce inmediatamente anterior | Solo línea sintética; producir respaldo en ventana real |
| B4/arranque B1–B5 | Snapshot B3 y código correspondiente | Solo línea sintética; no existe respaldo operativo acreditado de una etapa no alcanzada |

Para **cada backup nuevo**, `restore --work <su-ruta>` y `verify-restore --work <su-ruta>` crean una copia privada nueva con su historial, sin sobrescribir operación. Para checkpoints del clon, `verify-checkpoint --work $W --name <nombre>` restaura a base nueva, rechazando si ya existe. Son las recuperaciones automatizadas seguras. Cambiar servicios a un destino restaurado requiere autorización separada, credenciales/RLS/consumidores y esquema/binario comprobados; no se automatizó borrado o reemplazo de la base habitual.

Si hubo **escrituras nuevas después del snapshot**, restaurarlo también pierde esas escrituras: recibos, versiones, sync aceptado, custodia, retornos y avisos. No es rollback sin pérdida. Congelar escritores, conservar también el estado fallido y diarios/colas, comparar comandos ya aplicados y decidir recuperación hacia delante o conciliación explícita. No reinyectar sync ciegamente. No hay PITR/WAL acreditado; no se promete recuperar un instante posterior al dump. No usar Down como atajo: Stage protege datos poblados y B3/B4 contienen snapshots/historial que deben preservarse.

## 8. Cambios y decisiones concretas pendientes

Nuevos: `FleetStageMaintenance.cs`, integración en `Program.cs`, `FleetStageModelCustomizer.cs`; tests `FleetStageMaintenanceTests.cs`, `FleetBoundedTransitionTests.cs`; herramientas `scripts/cu06/{transition,prepare-artifact,verify-artifact,probe-stage,probe-current}.py`; este documento/evidencia. Sin cambios de interfaz ni de reglas B1–B5.

Revisión nativa **pendiente**: modo backend ON global conservado. Assess high/unassessable por untracked; STATUS sin opciones de START devuelve `collect intended_untracked_selection_required`, operación `external.select_intended_untracked`, no expuesta en esta sesión. No se fabricaron selección, consentimiento ni PASS, ni se cambiaron preferencias. Pruebas/revisión propia no equivalen a aprobación nativa o independiente. Engram sin identidad runtime registrada: sin writes ni supuesto espejo guardado; trazabilidad local preservada.

**Antes de intervenir la instancia habitual:**

- **Responsable operativo:** constatar cuatro ocupaciones legadas y custodia/uso reales; decidir qué autorización puede anularse y qué ocupación está vigente; verificar disponibilidad inicial cuando corresponda. Sin firmas/constataciones atribuidas por esta tarea.
- **Responsable de accesos:** seleccionar/provisionar por procedimiento autorizado un acceso con autoridad operativa. La lista de permisos de la cuenta antigua no basta; no ocultar403.
- **Responsable técnico:** ventana, ausencia comprobada de escritores/reinicios, respaldo final restaurable y custodia/exportación DPAPI; artefacto/configuración de ejecución habitual por procedencia comprobada y pruebas HTTP/Backoffice allí tras intervención autorizada.
- Mantener **revisión nativa, habilitación operativa y fallo arquitectónico previo pendientes**. Ahora existe artefacto Stage administrativo explícito del checkout, no un supuesto release B2 histórico ni una imagen operativa aprobada.

Risk: items 2 y 5 (guard administrativo y procedimiento de transición/recuperación). No se declara CU06 completo.
