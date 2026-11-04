# CU-06 B2 — cierre técnico de aceptación

Fecha: 01/11/2026. Complementa [06-implementacion-b2.md](06-implementacion-b2.md), sin reemplazar su evidencia histórica. **B3 no se inició.** No hubo commits, ramas nuevas, despliegues ni acciones sobre datos operativos.

> **Aceptación funcional aislada completada:** [08-aceptacion-funcional-aislada-b2.md](08-aceptacion-funcional-aislada-b2.md) registra esperado/observado/evidencia por paso y 19 verificaciones aprobadas. B2 queda técnicamente verificado; la revisión nativa y la habilitación operativa continúan pendientes. No hay firmas ni constataciones físicas atribuidas.

## Resultado y límites de la evidencia

| Capa | Estado |
|---|---|
| Implementación funcional B1/B2 | Conservada. En este incremento solo se corrigió presentación/mensajes del panel de flota. Sin cambios de dominio, API, base, migraciones ni mobile. |
| Automatización funcional anterior | Se mantiene la evidencia de 06: B2 15, rutas/capacidad 29, diario 55, unitarias 227, mobile 35+76. No se repitieron suites de backend/mobile no modificadas. |
| Automatización de interfaz actual | Pruebas SSR y navegador focalizadas; resultados finales debajo. No confundir API simulada con prueba de persistencia o constatación física. |
| Revisión visual | **Realizada** con Chromium local 151.0.7922.34, en escritorio y viewports móviles de 390 y 320 CSS px. Capturas reales inspeccionadas. |
| Aceptación operativa y transición real | **Pendientes**, requieren responsables humanos y autorización de mantenimiento. Ninguna captura o fixture acredita retorno/descarga reales. |
| Arquitectura | Persiste el baseline de 06: `ShipmentEndpoints_DeclareApiOwnedResponses`, esperado 2 / real 7. No se modificó ni debilitó; no se volvió a ejecutar por cambios solo de interfaz. |
| Revisión nativa | No aprobada. Backend sigue ON global y frontend OFF clone-local, sin cambiar preferencias. La operación necesaria `external.select_intended_untracked` sigue sin estar expuesta en el inventario de herramientas; no se repitió START/STATUS ni se sustituyó por una aprobación propia. |

### Entorno aislado de revisión

Se reutilizó `BackofficeFactory` y su `FakeApi` en memoria. `UseKestrel(0)` sirve el **Razor real** en un puerto loopback aleatorio; Chromium usa sesión/antiforgery/HTML/CSS/JavaScript reales. El cliente HTTP del servidor se sustituye por la fixture: **no existe conexión con API o base operativa**, ni se creó otra API operativa. Las confirmaciones solo afectan la fixture. El navegador bloquea solicitudes fuera de su origen loopback.

`playwright-core` y Chromium ya estaban instalados localmente. No se instalaron dependencias ni se cambió el stack. La fixture reúne escenarios de presentación independientes; no representa asignaciones físicas reales ni una fotografía de la base. Se usó un único POST de flota simulado con conflicto 409; la liberación real y la idempotencia persistida corresponden a las pruebas de backend referenciadas en 06.

## Hallazgos de claridad corregidos

- Faltaban los requisitos concretos que impedían liberar. Ahora se enumeran **cierre**, **retorno** y **recepción/conciliación de bultos**, sin ocultar que un recurso continúa ocupado aunque su jornada esté cerrada. Si ya se cumplen, se aclara que todavía falta la confirmación explícita de liberación.
- Se identifica al repartidor y se mantiene el enlace a ruta/fecha responsable. La recepción tiene un enlace separado a la pestaña de depósito de esa fecha; no se transforma el retorno en recepción.
- Se distingue **disponibilidad desconocida**, **inactivo sin habilitación para despacho** y **ocupado**. Un error de consulta ahora anuncia explícitamente disponibilidad desconocida, nunca disponibilidad confirmada.
- Se explican cierre administrativo, retorno físico, recepción y liberación como hechos diferentes; se aclara el camino de anular una autorización nunca iniciada.
- Se corrigieron signos `?` residuales de codificación en mensajes B2 y en un separador de carga histórica. No se cambiaron reglas de negocio.

### Revisión real en navegador

Se comprobó:

1. Reflujo sin desplazamiento horizontal general: ancho de documento/viewport **1440/1440, 390/390 y 320/320**.
2. Ocupaciones de `02/01/2020` visibles y abiertas tanto al consultar `20/10/2026` como `03/02/2027`, con enlace a la fecha original. No dependen del filtro diario.
3. Acciones de retorno y liberación renderizadas en escritorio/móvil; textos, etiquetas y botones no quedan cortados. La liberación no se ofrece con carga pendiente.
4. Teclado: foco en el `summary`, Enter abre la confirmación, Tab llega al motivo y luego al botón. Etiqueta asociada y foco visible del campo comprobados mediante DOM y captura.
5. En el submit real por teclado, el handler existente deshabilita el botón y marca `aria-busy=true`. Un segundo evento de submit se cancela; se observó **un solo POST** de flota. No se modificó el JavaScript general para lograrlo.
6. Tras el 409, alerta visible y motivo conservado exactamente, junto con comando, ocupación y versión originales; no hubo reintento automático. El formulario de recuperación permite reenviar el mismo comando o descartar y consultar.
7. Sin errores JavaScript ni recursos HTTP fallidos en el recorrido final. Esto no certifica WCAG integral ni sustituye validación con lector de pantalla o dispositivo físico.

Capturas inspeccionadas:
- [Escritorio](evidencias/b2/rutas-1440-viewport.png), [390 CSS px](evidencias/b2/rutas-390-viewport.png), [320 CSS px](evidencias/b2/rutas-320-viewport.png).
- [Confirmación y foco a 320](evidencias/b2/confirmacion-320-viewport.png).
- [Liberación en escritorio](evidencias/b2/liberacion-escritorio.png) y [320](evidencias/b2/liberacion-320.png).
- [Conflicto a 320](evidencias/b2/conflicto-320-viewport.png); las variantes de página completa están en el mismo directorio.
- [Resultado de automatización](evidencias/b2/browser-results.json), con dimensiones, comprobaciones y eventos; no contiene credenciales operativas ni tokens.

## Checklist breve de aceptación operativa

**Preparación:** responsable operativo y QA, entorno de aceptación aislado, vehículo/repartidor habilitados y verificación inicial real o simulación expresamente identificada. Guardar IDs/versiones de A y de sus comandos. No acreditar hechos físicos en operación usando una simulación.

| Paso verificable | Resultado esperado / quién constata |
|---|---|
| 1. Despachar A en su fecha operativa, iniciar, cargar y confirmar salida | Ocupación de A adquirida. Capacidad B1 vigente respetada. QA contrasta IDs/estados; operador realiza el recorrido de aceptación. |
| 2. Cerrar con un bulto sin entrega/rendición | Jornada cerrada e incidencia histórica; custodia y ocupación siguen activas. Operador + depósito verifican el bulto. |
| 3. Consultar otra fecha en `/rutas` | A continúa visible, con fecha original, responsable y requisitos faltantes. QA/operador. |
| 4. Confirmar retorno de A sin recibir el bulto | Retorno registrado; carga y ocupación no se liberan. **Operador autorizado debe constatar físicamente el regreso** en la aceptación real. |
| 5. Intentar liberación incompatible con carga pendiente | 409 sin mutación parcial. La UI no ofrece la acción mientras falte carga; QA puede repetir el comando API documentado en fixture aislada. No eludir esta protección en operación. |
| 6. Recibir efectivamente el bulto en depósito o aplicar conciliación válida existente | Custodia resuelta; incidencia histórica conservada. **Responsable de depósito constata recepción**, no el mero clic de retorno. |
| 7. Liberar A con su ocupación/versión exactas | Disponibilidad confirmada, listado actualizado y aviso accesible. Operador autorizado + QA. |
| 8. Despachar B con el mismo recurso ese día; reenviar liberación vieja de A | B queda ocupando. Replay exacto de A devuelve su recibo sin tocar B; otro comando con versión vieja se rechaza. QA verifica IDs y auditoría, sin fabricar un nuevo retorno. |
| 9. Anular otra autorización nunca iniciada ni cargada | Ocupación anulada, sin retorno ficticio, envíos sin cancelar, historial conservado. Operador/QA. |
| 10. Repetir anulación cuando ya hubo inicio o carga | Rechazo; no desaparece ocupación ni custodia. QA/operador. |

No se duplicaron pruebas de concurrencia, medianoche o RLS: usar las de `OcupacionFlotaHttpTests.Ciclo.cs`, `.CustodiaInicial.cs`, `.Seguridad.cs`, `.Transicion.cs` y `OcupacionFlotaHttpTests.cs`, detalladas en 06. El ciclo completo con PostgreSQL restringido ya verifica custodia, retorno, rechazo, recepción, liberación, reutilización y comando A/B; las cuatro etapas de anulación cubren ausencia de inicio, inicio, carga y salida.

## Arranque real y bloqueo de la segunda migración

**Conclusión del contraste:** el arranque web normal puede mantenerse sin migrar, pero **no hay un selector de etapa en el comando `database-migrate`**. No basta con cambiar un booleano si se sigue usando ese comando/job.

| Evidencia local | Consecuencia para esta transición |
|---|---|
| `backend/src/NexoRuta.Api/appsettings.json`, `DatabaseInitialization.ApplyMigrations=false` y `SeedData=false`; `Program.cs:235–238` condiciona migración/seed del arranque web | Mantener ambos valores efectivos en false durante la conciliación; verificar overrides del ambiente autorizado sin volcar secretos. |
| `compose.yaml:87–88` y `deploy/gcp/compose.yaml:6–7` fijan ambos a false | Ayudan al arranque controlado, pero no constituyen una pausa del migrador externo. No se inspeccionaron sesiones/configuraciones remotas. |
| `Program.cs:95–102`, rama `database-migrate`, llama `MigrateAsync()` sin destino antes del arranque normal | **Ignora el gate del arranque web y aplica todas las pendientes.** No usarlo entre etapas ni suponer que acepta un nombre de migración adicional. |
| `Persistence/NexoRutaDbContextFactory.cs:10–16` usa `UseNexoRutaPostgres()` sin conexión; el overload por defecto pasa null | El comando EF orientativo de 06 **no obtiene automáticamente la conexión desde appsettings/variables** con esta factory. No ejecutarlo suponiendo que ya eligió el destino. `database update` requiere una conexión explícita; se recomienda generar SQL offline por etapa y que el DBA lo aplique con su canal autorizado. No se modificó la factory. |
| `compose.yaml:162–175`, `rls-migrator`, profile `rls-admin`, comando `database-migrate` | No activar ese profile/job para ejecutar la primera etapa de B2. |
| `scripts/gcp/delivery.py:521–540` detiene aplicaciones y luego ejecuta etapa `migrate`; `scripts/gcp/vm_deploy.py:344–355` ejecuta el servicio migrador | El despliegue normal no tiene una pausa humana entre estas dos migraciones. **No ejecutar ese pipeline completo para esta transición sin un procedimiento de mantenimiento separado/autorizado.** No se modificó ni ejecutó el despliegue. |

### Secuencia que debe ejecutar el responsable técnico/DBA, no ejecutada aquí

1. Autorizar ventana, inventario de nodos/procesos/jobs y respaldo recuperable. Bloquear ingreso de escrituras, incluido sync móvil; conservar colas locales y reintentos, no vaciarlos.
2. Detener y comprobar ausencia de escritores anteriores en **todos** los nodos: API, workers/consumidores y scripts/importadores/bootstrap/manuales. En Compose local el inventario incluye `api`, `worker`, `worker-kafka`; en GCP `vm_deploy.py:26` enumera API y workers rabbit/kafka/push más portales. Evitar que `dotnet watch`, servicios, jobs programados, políticas de reinicio o despliegues los relancen. Un balanceador drenado no detiene jobs ni acceso directo a API/DB.
3. Verificar inventario del orquestador y procesos, revisiones/imágenes y sesiones PostgreSQL. Antes de arrancar el acceso administrativo B2, no debe haber sesiones de aplicaciones anteriores. La consulta siguiente es **solo un control complementario**, no prueba de que un proceso detenido no pueda reconectar:

```sql
SELECT usename, application_name, client_addr, state, count(*)
FROM pg_stat_activity
WHERE datname = current_database()
  AND backend_type = 'client backend'
  AND pid <> pg_backend_pid()
GROUP BY usename, application_name, client_addr, state;
```

El DBA debe identificar cada conexión restante; no basta con que no tenga una consulta activa. No se consultó la base operativa en esta tarea ni se terminaron sesiones. `application_name` por sí solo tampoco acredita la versión del proceso: contrastar con inventario/imagen y dueño del servicio. Tras iniciar B2 administrativo, admitir únicamente esas instancias nuevas conocidas y las sesiones de mantenimiento autorizadas.

4. Deshabilitar explícitamente el job/pipeline externo de migración y cualquier seed. Generar/revisar los dos SQL offline con límites exactos (desde el superproyecto, sobre binarios B2 compilados):

```powershell
dotnet ef migrations script 20261030120000_ListImportedShipmentReferences 20261101184716_StageFleetOccupations --context NexoRutaDbContext --project backend/src/NexoRuta.Infrastructure --startup-project backend/src/NexoRuta.Api --no-build --output "$env:TEMP/cu06-b2-stage.sql"
dotnet ef migrations script 20261101184716_StageFleetOccupations 20261101185119_EnforceFleetOccupationExclusivity --context NexoRutaDbContext --project backend/src/NexoRuta.Infrastructure --startup-project backend/src/NexoRuta.Api --no-build --output "$env:TEMP/cu06-b2-enforce.sql"
```

Estos comandos **sí se ejecutaron aquí solo para generar SQL**, sin conexión ni aplicación a ninguna base. Se verificó que cada script registra exclusivamente su migración destino en `__EFMigrationsHistory`; Stage no crea los índices exclusivos y Enforce conserva sus prechecks. El DBA debe revisar la correspondencia con el esquema/historial real y aplicar **solo Stage** mediante su herramienta/destino/identidad de mantenimiento explícitamente autorizados, con parada ante error y respetando las transacciones del script. No concatenar los SQL ni aplicarlos juntos. No incluir secretos en argumentos, historial, repositorio ni logs. La identidad debe ver todos los tenants; no usar el rol API ni inferir disponibilidad de datos filtrados por RLS.
5. Arrancar únicamente B2 administrativo con valores efectivos `DatabaseInitialization__ApplyMigrations=false` y `DatabaseInitialization__SeedData=false`, acceso restringido y escritores viejos aún detenidos. Comprobar en `__EFMigrationsHistory` que está Stage y **no** `20261101185119_EnforceFleetOccupationExclusivity`. Este es el control verificable de que la segunda no se aplicó automáticamente.
6. Conciliar con responsables físicos según 06: conflictos nunca se resuelven eligiendo un ganador por fecha; las rutas iniciadas se resuelven por cierre/retorno/custodia. Desconocido no equivale a disponible. Conservar actores, versiones, motivos y recibos actuales, sin reconstruir retornos históricos.
7. Con conciliación firmada y escritores todavía controlados, aplicar explícitamente **solo el SQL Enforce**. Sus prechecks de conflictos y ocupaciones legadas sin verificar deben aprobar. Confirmar historial, índices únicos parciales y prueba aislada de permisos; después autorizar el tráfico normal. Un precheck rechazado detiene activación y vuelve a conciliación, no se salta ni se deshabilita el índice.

**Evidencia que falta del entorno real:** inventario completo/estado detenido de escritores, flags efectivos de las instancias autorizadas, historial entre etapas, inspecciones físicas y acta de conciliación. No se afirma que ya se cumplan.

## Reproducción y resultados actuales

El runner persistente es `frontend/tests/NexoRuta.ApiClient.Tests/FlotaBrowserTests.cs` + `frontend/tests/browser/cu06-b2.cjs`. Requiere Node y un módulo `playwright-core` ya disponible, indicado con `NEXORUTA_PLAYWRIGHT_MODULE`. `NEXORUTA_B2_BROWSER_DIR` elige la carpeta de capturas; sin esa variable el Fact queda **omitido explícitamente**, no aprobado sin navegador.

```powershell
# Variables solo para el proceso de prueba, sin API/base operativa.
$env:NEXORUTA_PLAYWRIGHT_MODULE = '<ruta local a playwright-core instalado>'
$env:NEXORUTA_B2_BROWSER_DIR = '<directorio de evidencia aislada>'
dotnet test frontend/tests/NexoRuta.ApiClient.Tests --no-restore --filter 'FullyQualifiedName~Fleet|FullyQualifiedName~Rutas|FullyQualifiedName~Capacidad|FullyQualifiedName~Configuration'
```

RED observado antes de las correcciones: faltaba explicar el retorno como requisito para liberar y faltaba anunciar disponibilidad desconocida ante 503. Logs locales `%TEMP%/cu06-b2-acceptance-red.log` y `cu06-b2-query-red.log`. Los intentos iniciales del harness revelaron errores de selectores/observación después de navegación, no fallos de la lógica de doble envío; se corrigió el probe para registrar el estado sincrónico antes de reemplazar el documento y distinguirlo de una segunda solicitud real.

Resultado final: **24/24 aprobadas, 0 fallos, 0 omitidas**, incluido el Fact opt-in con navegador real, en `%TEMP%/cu06-b2-acceptance-final24.log`. La compilación previa de frontend/Razor con `dotnet test --no-restore` no tuvo errores; el lote final usó `--no-build` sobre esos binarios y el script de navegador final. El intento inicial de ese lote tuvo 23 aprobadas y un fallo del probe de navegador, corregido como se explica arriba; no se lo cuenta como aprobado. No se repitieron suites amplias ya aprobadas. `git diff --check` no reportó problemas.

Archivos de este cierre: `frontend/src/NexoRuta.Backoffice/Pages/Rutas/_Flota.cshtml`, `Features/Reparto/Pages/RutasModel.cs`; `frontend/tests/NexoRuta.ApiClient.Tests/{FlotaPagesTests,RutasPagesTests,FlotaBrowserTests}.cs`; `frontend/tests/browser/cu06-b2.cjs`; este documento, referencia de actualización en 06 y 12 PNG + `browser-results.json` en `evidencias/b2/`. Se conservó una copia inicial de los archivos compartidos y estados Git en `%TEMP%/NexoRuta-B2-acceptance-initial-n9643rmh`. Ramas y HEAD siguen siendo los de 06, incluidos gitlinks divergentes y cambios locales anteriores. `odd/tasks/cu06-b2.md` conserva el log local; Engram no dispone de identidad de sesión registrada para escrituras atribuidas.

No se presenta revisión propia como aprobación nativa ni aceptación física.

## Para aceptar B2: responsables y pendientes exactos

- **QA + responsable operativo/despachador autorizado:** ejecutar y firmar el checklist en entorno de aceptación aislado, incluyendo el recorrido con dispositivo y los cambios de custodia. Esta revisión técnica del navegador no sustituye esa firma.
- **Operador autorizado y responsable de depósito:** constatar físicamente retorno y recepción/conciliación; acreditar cada vehículo legado solo con evidencia suficiente. Ninguna simulación de este documento cuenta como hecho físico.
- **Responsable técnico/DBA y dueño del despliegue:** demostrar congelamiento de escritores en todos los nodos, flags efectivos, pausa del migrador externo y separación verificable de etapas antes de cualquier transición real autorizada.
- **Responsable del proyecto/revisión:** dejar registrada la limitación nativa si la política exige esa aprobación, o completar la revisión cuando el host exponga la selección requerida, sin cambiar preferencias automáticamente. Mantener visible el fallo de arquitectura preexistente como seguimiento separado.

Hasta esas constataciones no corresponde declarar B2 aceptado operativamente ni CU-06 completo. B3 permanece fuera de este incremento.
