# CU06 — B1–B5 funcionando en la instancia local habitual

## Resultado

**Transición local completada.** PostgreSQL habitual quedó en B4, la API Docker ejecuta el checkout actual, workers y portales están funcionando y las consultas de flota, compatibilidad vial e histórico ya responden200 con la identidad autorizada. Chromium verificó la instancia habitual a1440/320px, con escrituras de prueba autorizadas. No es otro ensayo aislado.

La autorización que habilitó esta intervención fue: «toda la base local [...] contiene exclusivamente datos de prueba del taller. No hay operaciones reales». Las regularizaciones descritas son **sintéticas**, no constataciones físicas ni firmas de personas. El bloqueo operativo del documento14 se resolvió para **este entorno ficticio**, no como autorización de uso real.

### URLs y acceso de prueba

- Gestión completa: **http://localhost:5101/vehiculos** — menú Operador y equipo → Vehículos, junto a Repartidores.
- Rutas y depósito: **http://localhost:5101/rutas**.
- Ruta de prueba conciliada: **http://localhost:5101/rutas?fecha=2026-10-30&rutaSeleccionadaId=01a18afb-48f1-75a9-91bc-afdd3ac252a0**.
- Configuración/perfiles: **http://localhost:5101/configuracion-reparto**.
- API: **http://localhost:5000**; Admin5104, Commerce5102 y Tracking5103 también respondieron health/ready200.

Cuenta autorizada: **`cu06.operaciones.taller@example.test`**. Su contraseña es el valor local ya configurado como `NEXORUTA_OPERADOR_PASSWORD` en `.env`; no se publica el secreto. No se cambió la contraseña del operador original ni de ningún repartidor.

Evidencia: [HTTP habitual](evidencias/activacion-local/http-final.json), [runtime/flags](evidencias/activacion-local/runtime-final.json), [Chromium](evidencias/activacion-local/browser.json), [filtro diario y negativo](evidencias/activacion-local/local-extra.json).

## 1. Preservación, parada y respaldo final

Se registraron ramas/HEAD/estado e identidades de contenedores antes de intervenir. Raíz develop1ef2175, backend fix/zonacobertura a0aa204, frontend fix/zonacobertura e05c0de, mobile fix/zonacobertura78f65e1 permanecen sin cambios de rama/HEAD/gitlinks. B1–B5 no fueron editados. Sin commits, push, remoto, borrado de base ni volúmenes.

Se detuvieron temporalmente API, worker RabbitMQ, worker-kafka, Backoffice, Commerce, Admin y Tracking. PostgreSQL e infraestructura persistente no se reiniciaron. Se comprobó la parada y ausencia de otras sesiones de aplicación en PostgreSQL antes del respaldo. La API anterior se abrió después únicamente para las altas controladas de usuarios, y volvió a detenerse antes de Stage; no se permitió tráfico general durante migración/conciliación.

Se reutilizó `transition.py backup`, DPAPI CurrentUser/ACL y restauración independiente ya ensayados. **Respaldo final anterior a mutaciones restaurado y comparado en61 tablas**. El checkpoint Stage posterior a regularización también se restauró dos veces y coincidió en63 tablas. Enforce/B3 y el estado exitoso posterior también tienen dumps cifrados y verificación de cifrado/descifrado/hash; no se afirma haber restaurado los cinco snapshots.

| Punto | Directorio bajo `%LOCALAPPDATA%/NexoRuta/cu06-transition/` |
|---|---|
| Baseline final congelado, antes de roles/usuarios | `a79fa1cbd272` |
| Stage con recibos y conciliación sintética | `a30d4e3b32fb` |
| Enforce antes de B3 | `879e79f80541` |
| B3 antes de B4 | `ce44d6b9e8e2` |
| Éxito B4 después de pruebas | Ver entrada post-success en [manifiesto](evidencias/activacion-local/backups-summary.json) |

DPAPI está ligado a esta cuenta/máquina; dumps, globals sin passwords y copia cifrada de `.env` permanecen fuera del repositorio. El último snapshot fue con servicios funcionando y es consistente MVCC, no otro congelamiento. No sustituye al baseline final detenido.

## 2. Acceso403 resuelto sin excepción de producto

La cuenta antigua conservaba el rol protegido `propietario_operador`, que no satisface el código de rol requerido por la autoridad operativa actual aunque tenga permisos listados. **No se debilitó esa política, no se renombró ese rol ni se elevó automáticamente a sus usuarios.**

Se provisionó puntualmente un rol protegido canónico **`administrador_operador`** para el operador local `1b41be96-6f3e-42b9-99d0-f2e9b3c7c52a`, usando las entidades/métodos existentes `Rol`, `ProtegerComoRolSistema`, `CatalogoPermisos.Para(Operador)` y `RolPermiso`, como en el bootstrap administrativo existente. Fue una actuación administrativa local autorizada mediante un ejecutable temporal, **no un cambio de código, seed de aplicación o SQL que omita la política**. Su fuente/hash/log están conservados en el directorio privado.

Con la cuenta propietaria existente y su API de usuarios se creó `cu06.operaciones.taller@example.test` mediante **POST `/api/usuarios`201**, asignando ese rol. La API valida permisos del creador y pertenencia del rol; no se alteró la prohibición de autoasignación o modificación de propietarios. El usuario nuevo obtiene autoridad operativa y configuración por los mecanismos existentes.

Se creó además `cu06.sin-permisos.taller@example.test`, con rol ordinario `cu06_sin_permisos` sin grants, mediante las APIs existentes de roles/usuarios. Es un negativo del mismo operador, no una identidad anónima: login200 seguido de cuatro GET403. Backoffice muestra Acceso denegado y no expone el formulario de vehículos. [Acceso configurado](evidencias/activacion-local/configured-access.json).

## 3. Regularización sintética de las cuatro ocupaciones

Con Stage y el host de mantenimiento restringido, se autenticó la cuenta nueva. Se usaron **los POST existentes de flota**, con ComandoId, ocupación exacta, versión0 y motivo explícito «Regularización SINTÉTICA autorizada CU06 [...] No acredita hechos reales». Recibos de servidor conservados: [cuatro hechos](evidencias/activacion-local/synthetic-receipts.json).

| Ruta / fecha | Estado previo y evidencia | Actuación y resultado |
|---|---|---|
| `01a18418-978a-7f86-a290-fb35fbc4855e` /28-10 | Despachada, sin inicio/salida/carga aplicada | `anular`200; hoja Cancelada, reserva diaria inactiva, ocupación anulada versión1 |
| `01a18620-ee91-7b8c-9bbc-02b0397a4b64` /29-10 | Despachada, sin inicio/salida/carga aplicada | `anular`200; mismo resultado |
| `01a189d3-cb04-7af3-8ae7-99525b4edef7` /31-10 | Despachada; un InicioJornada en **Conflicto**, ninguno aplicado y sin carga | `anular`200; conflicto histórico conservado, no reinterpretado como inicio |
| `01a18afb-48f1-75a9-91bc-afdd3ac252a0` /30-10 | EnCurso, inicio/salida existentes | Tras resolver los otros conflictos, `conciliar`200; ocupación vigente versión1, adquisición administrativa actual, sin retorno ni liberación |

Las anulaciones suspendieron paradas mediante el dominio, **sin cancelar envíos** ni borrar diarios. Las hojas pasaron de versión3 a4; la hoja EnCurso mantuvo versión1588. Las cuatro ocupaciones permanecen en historial. No se inventaron timestamps históricos: los instantes nuevos son del servidor para estas actuaciones sintéticas actuales.

La inspección de custodia encontró **cero bultos con RutaCustodiaId** y el panel confirmó carga pendiente0. Por tanto no fue necesario simular recepción, descargar bultos ni conciliar pérdidas. No se registró retorno, cierre ni disponibilidad física. La jornada iniciada se conservó como escenario ficticio activo, y **vehículo/repartidor siguen ocupados** hasta completar su flujo B2. No es un fallo de transición ni se muestra disponible.

Después de regularizar no quedaron grupos activos incompatibles ni legadas activas sin adquisición; Enforce aprobó sin deshabilitar restricciones ni editar el diario. Los índices únicos activos por operador/vehículo y operador/repartidor están presentes **sin filtro por fecha**. La disponibilidad inicial de otros vehículos sigue siendo desconocida cuando no tiene confirmación: no se convirtió en disponible por ser datos de prueba.

## 4. Migraciones y ejecución Docker efectiva

SQL de14 con hash cotejado, historial previo comprobado y ON_ERROR_STOP, por etapas independientes:

1. `20261101184716_StageFleetOccupations` — [log](evidencias/activacion-local/stage-apply.log).
2. Pausa, actuaciones sintéticas y checkpoint Stage.
3. `20261101185119_EnforceFleetOccupationExclusivity` — [log](evidencias/activacion-local/enforce-apply.log).
4. Checkpoint Enforce; `20261101203256_AddOperationalBaseAndTemporalPlan` — [log](evidencias/activacion-local/b3-apply.log).
5. Checkpoint B3; `20261101213104_AddRoadEstimationHistory` — [log](evidencias/activacion-local/b4-apply.log).

Nunca se ejecutó `database-migrate`, el batch general, bootstrap/seed automático ni un migrador de todas las pendientes. El SELECT temporal de historial para mantenimiento fue revocado; se comprobó `has_table_privilege(...)=false` para nexoruta_api.

Se construyeron API y Worker desde **backend dirty actual** con el Dockerfile existente, SDK10.0.401 y runtime tools para healthchecks. Primero se produjo una API sin runtime tools, que no se usó como servicio final; se reconstruyó con la configuración del Dockerfile para conservar curl/healthcheck. No se atribuyó funcionalidad a un binario viejo.

| Artefacto ejecutado | Image ID/digest |
|---|---|
| `nexoruta-api:cu06-local-b1-b5` | `sha256:f2565af1df6d4d7518ebcb760a328d7812a6b3e7285e6da71eaae3bb1d1a37bf` |
| `nexoruta-worker:cu06-local-b1-b5` (RabbitMQ/Kafka) | `sha256:d75a70ac0729d4950350403c47ab81ddf7302e028de8a1e5377a7f72642f7545` |

Los tags locales anteriores se actualizaron al artefacto nuevo; imágenes previas conservadas por digest para recuperación, sin prune. API/workers se recrearon controladamente con `--no-deps --no-build` y override local; los portales retomaron su mecanismo existente dotnet watch con bind del frontend actual. [Hashes de DLL dentro del contenedor](evidencias/activacion-local/api-runtime-binary-sha256.txt) y [estado final](evidencias/activacion-local/runtime-final.json).

Flags efectivos API: StageOnly=false, ApplyMigrations=false, SeedData=false, PlatformInitialization=false, RoutingGeoapify.PermitirLlamadasReales=false y ApiKey vacío. No hubo llamadas viales, contratación ni piloto. Base/perfil/GPS faltantes continúan como estados explícitos, no se suplieron con tiempos inventados.

## 5. Verificación sobre la instancia habitual

| Comprobación | Resultado |
|---|---|
| GET `/api/reparto/vehiculos` |200|
| GET `/api/reparto/flota` |200|
| GET `/api/reparto/perfiles-viales` |200|
| GET `/api/rutas/01a18afb-48f1-75a9-91bc-afdd3ac252a0/estimaciones` |200; ruta propia preexistente, sin historial inventado|
| Mismos cuatro GET, usuario autenticado sin permisos |403 en todos|
| Health/ready API5000, Backoffice5101, Commerce5102, Tracking5103, Admin5104 |200 en todos; API/workers healthy|

**Chromium151.0.7922.34 real contra localhost5101**, no FakeApi ni fixture:

- Menú Operador y equipo → Vehículos, junto a Repartidores; navegación/teclado.
- Alta `CU06-LOCAL-V`; 1.005 rechazado y valores conservados; 1000.00 aceptado; doble click no duplicó alta.
- Edición a3000.01g/8000000.01cm³; deshabilitación/reactivación; estado final Activo=true, Version2. No se tocó capacidad/snapshot de vehículos anteriores.
- Flota, perfiles e histórico sin los tres errores HTTP anteriores. «Falta determinar perfil» y «Disponibilidad desconocida: verificación inicial pendiente» son estados de datos válidos, no errores escondidos.
- Bajo filtro diario actual se conserva visible la ocupación del30/10, con enlace y requisitos de cierre/retorno. No se filtró la ocupación por fecha.
- Cuenta sin permisos: formulario inaccesible; redirección a `/acceso-denegado` (página informativa200, **no** gestión200).

Capturas nuevas generadas e inspeccionadas: [vehículos320](evidencias/activacion-local/vehiculos-320.png), [1440](evidencias/activacion-local/vehiculos-1440.png), [validación](evidencias/activacion-local/validacion-320.png), [menú](evidencias/activacion-local/menu-320.png), [flota320](evidencias/activacion-local/flota-320.png), [otra fecha](evidencias/activacion-local/flota-otra-fecha-320.png), [perfiles](evidencias/activacion-local/perfiles-320.png), [histórico](evidencias/activacion-local/historial-320.png), [denegación](evidencias/activacion-local/sin-permisos-320.png).

El primer intento de navegador encontró ERR_EMPTY_RESPONSE mientras dotnet watch aún compilaba; se esperó readiness y el recorrido completo pasó. El reporte de la plantilla heredaba la descripción «ephemeral PostgreSQL»: se corrigió **solo esa descripción** para este destino habitual, preservando el original privado y anotando la corrección, sin cambiar resultados.

Regresión proporcionada: **3/3** — FleetTenantIsolationIsEnforcedByHttpAndRlsAndFactsCannotBeMutated y los dos casos DispatchUsesCurrentCapacityWithoutRewritingSnapshot. [Log](evidencias/activacion-local/targeted-regressions.log). Justificación: despliegue local del modelo y restricciones nuevos; no se repitieron todas las aceptaciones B1–B5. El flujo real de vehículos también ejercitó precisión/concurrencia/versiones. Sin cambios funcionales de producto para hacer pasar pruebas.

## 6. Artefactos, reproducción y recuperación

Directorio privado: `%LOCALAPPDATA%/NexoRuta/cu06-local-activation/20261101-220826`. Contiene inventario inicial, configuración anterior/override, código/log del bootstrap administrativo puntual, recibos, manifiesto SHA de fuentes y build, logs HTTP y navegador. No publicar `containers-private.json` ni backups/.env/tokens/credenciales. [Hashes de ejecución](evidencias/activacion-local/execution-source-sha256.json).

Se añadieron únicamente herramientas de esta actuación y documentación/evidencias: `scripts/cu06/local-activation.py`, `scripts/cu06/verify-local.cjs`, logbook `odd/tasks/cu06-transicion-local.md`, este documento. No se modificaron Domain/API/ApiClient/OpenAPI ni reglas B1–B5.

No repetir la regularización como seed. El runner rechaza preparación de acceso fuera de baseline y aplica cada SQL solo desde su etapa previa exacta. Comandos empleados:

```powershell
python scripts/cu06/local-activation.py prepare-access
python scripts/cu06/local-activation.py apply --step stage
python scripts/cu06/local-activation.py stage
# Respaldo Stage previo a Enforce, después:
python scripts/cu06/local-activation.py apply --step enforce
# Respaldo Enforce, después:
python scripts/cu06/local-activation.py apply --step b3
# Respaldo B3, después:
python scripts/cu06/local-activation.py apply --step b4
```

Para arrancar la configuración efectiva actual sin migrar ni rebuild general:

```powershell
$W = "$env:LOCALAPPDATA\NexoRuta\cu06-local-activation\20261101-220826"
docker compose -f compose.yaml -f compose.dev.yaml -f "$W\compose-cu06-local.yaml" --profile kafka up -d --no-deps --no-build api worker worker-kafka
docker start nexoruta-backoffice nexoruta-commerce nexoruta-admin nexoruta-tracking
```

Recuperación segura: `restore --work <directorio-de-backup>` y `verify-restore --work <directorio-de-backup>` crean/verifican **otra copia**, no sobrescriben la base habitual. Para copias ya restauradas no repetir sobre otro historial. Volver al baseline perdería las altas/regularizaciones/pruebas posteriores: no se promete rollback sin pérdida ni PITR. Congelar escritores, conservar también estado actual/diarios/colas y decidir reconciliación o recuperación hacia delante antes de conmutar. No borrar base/volúmenes ni ejecutar Down para ocultar hechos. Véase procedimiento14 para límites DPAPI/roles y recuperación por etapa.

## 7. Pendientes que no invalidan este resultado local

- **Revisión nativa pendiente**, sin cambiar preferencias ni fabricar aprobación. La operación `external.select_intended_untracked` requerida por el proveedor sigue sin estar expuesta; no se repitió indefinidamente.
- **Fallo arquitectónico preexistente** ShipmentBoundaryTests.ShipmentEndpoints_DeclareApiOwnedResponses (esperado2/actual7), no resuelto ni reejecutado por rutina.
- **Precisión vial en Uruguay no validada**; proveedor real apagado, sin piloto. Configurar base/perfil y probar tiempos reales requiere su autorización específica.
- La jornada ficticia conservada EnCurso está ocupando correctamente su recurso. Sus futuras acciones de cierre/retorno/liberación son pruebas operativas posteriores, no una transición de esquema pendiente.

El entorno local autorizado está funcionando. Esto no acredita operación real, aceptación vial ni cierre total CU06. Engram sin identidad runtime: trazabilidad local, sin afirmar memoria guardada.

Risk: items 2 y 5 (provisión local autorizada y transición/reconstrucción de servicios). Sin excepciones de autorización de producto.
