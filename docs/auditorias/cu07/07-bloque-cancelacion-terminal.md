# Bloque de cancelación terminal — verificación y cambios

**Fecha:** 24/10/2026  
**Alcance:** matriz de cancelación y terminalidad de `Cancelado` en dominio, API, PostgreSQL y superficies que presentan la acción. No incluye importación de archivos ni el resto de la máquina de estados.

**Vigencia:** este corte no implementaba importación, lo cual era correcto para su alcance. La brecha de importación CU-07 se cerró después por bloques de backend y Commerce, con evidencia en `08-backend-importacion.md` y `09-commerce-importacion-y-verificacion.md`; esta nota de cancelación no se actualiza como evidencia de importación ni de las demás transiciones.

## Estado del checkout y límites de preservación

| Repositorio | Rama / HEAD | Estado previo relevante |
|---|---|---|
| Raíz | `feature/cu07` / `23ae885` | Conserva cambios locales en `architecture.md`, submódulos, `mobile`, imagen de estados y documentación de auditoría. |
| Backend | `feature/cu07` / `cb628c2` | Conserva cambios existentes en README, documentación CU-07/CU-08 y `RlsRestrictedHttpFlowTests.cs`; este bloque añadió los cambios enumerados abajo. |
| Frontend | `feature/cu07` / `10a1768` | Estaba limpio al iniciar este bloque; ahora contiene los ajustes acotados de disponibilidad de cancelación y pruebas listados abajo. |

No se cambiaron ramas, no se usaron reset/clean/stash, y no se hicieron commits, push ni despliegues. Se conservaron los cambios locales preexistentes. No se inspeccionaron archivos `.env`.

## Regla aplicada

| Decisión | Estados |
|---|---|
| Cancelación permitida (si actor y versión están autorizados) | `Admitido`, `EnDeposito`, `AsignadoRuta`, `EnTransito`, `NoEntregado`, `Reprogramado`, `EnDevolucion` |
| Cancelación prohibida | `Entregado`, `Devuelto`, `Extraviado`, `EntregaPendienteValidacion`, `EntregaSinValidacion` |
| Terminal | Desde `Cancelado` no se permite ninguna transición de estado. Un hecho físico offline posterior puede quedar registrado sin cambiar `Estado = Cancelado`. |
| Repetición | Una repetición autorizada conserva el resultado original y no crea otra transición, auditoría, aviso ni outbox. La validación de actor/permisos o del código público se realiza antes de devolver el resultado. |

## Hallazgos confirmados y conservados

1. El dominio permitía cancelar desde seis estados, omitiendo `EnDevolucion`; la función SQL autenticada y las funciones de elegibilidad pública repetían la misma omisión. Una prueba de PostgreSQL previa a la migración mostró que las once combinaciones restantes de la matriz pasaban y que `EnDevolucion` respondía `409 Conflict`.
2. La conciliación de una entrega offline tardía podía sustituir `Cancelado` por `Entregado` o `EntregaPendienteValidacion`. También existía `CK_Envios_Cancelacion`, que impedía guardar un timestamp físico en un envío cancelado; sin conservar ese hecho, la alternativa sería perder evidencia histórica.
3. El núcleo SQL de cancelación trataba una repetición como idéntica solo si `VersionEnvio` de la auditoría coincidía con la versión actual del envío. Como una conciliación factual incrementa la versión actual, la repetición autorizada posterior no podía recuperar el resultado original.
4. No se encontró una restricción de persistencia que impidiera que una escritura cambiara un estado `Cancelado` a otro estado fuera del método de dominio. Se agregó una guarda a nivel de tabla para cubrir los caminos que no pasen por `Envio.CambiarEstado`.
5. El repositorio ya invocaba `cancel_shipment` ante repetición. **No era por sí mismo un defecto:** el SQL comprobaba autorización, bloqueaba el envío y devolvía la auditoría existente antes de suspender rutas o insertar outbox. Se conservó ese camino y se probó que no duplica efectos.

## Cambios realizados

- `backend/src/NexoRuta.Domain/Envios/Envio.cs`: agregó `EnDevolucion → Cancelado`; al conciliar una entrega física tardía conserva `Estado = Cancelado`, registra fecha y avanza la versión. La entrega no se confunde con una transición de estado.
- `backend/src/NexoRuta.Infrastructure/Persistence/Migrations/20261024120000_EnforceCancellationTerminalState.cs`: migración nueva, sin editar migraciones históricas. Centraliza la lista permitida en `nexoruta_app.cancel_state_is_allowed(text)`, con `EXECUTE` solo para los roles privados existentes de cancelación; actualiza las funciones públicas y el núcleo compartido; mantiene propietarios/`SECURITY DEFINER`/`search_path`/grants; habilita reintento autenticado según el dato original de cancelación aunque exista una versión factual posterior; permite que el código público consumido válido recupere el resultado tras el hecho físico; agrega `tr_envios_cancelado_terminal`; elimina el check que prohibía conservar el hecho físico junto con `Cancelado`. No se amplían privilegios DML de `nexoruta_api`. El `Down` restaura la lista histórica y no procede si ya hay hechos físicos tardíos que el check volvería inválidos.
- `backend/src/NexoRuta.Infrastructure/Persistence/NexoRutaDbContext.cs` y `.../Migrations/NexoRutaDbContextModelSnapshot.cs`: retiraron del modelo el check incompatible. El check que exige timestamp para estados de entrega sigue vigente.
- `backend/src/NexoRuta.Infrastructure/Reparto/EfOperacionesRepartoRepository.Ejecucion.cs`: el resultado de una conciliación tardía comunica que conserva `Cancelado`; se preservan prueba, custodia y hechos existentes.
- `frontend/src/NexoRuta.ApiClient/Features/Envios/Contracts/Responses/EnvioResponse.cs` y `frontend/src/NexoRuta.Tracking/Components/Pages/Seguimiento.razor`: `EnDevolucion` permite presentar la acción; los cinco estados prohibidos siguen ocultándola. Commerce y Backoffice reutilizan `AdmiteCancelacion()`.
- Pruebas añadidas/actualizadas en `backend/tests/NexoRuta.UnitTests/Envios/EnvioCancellationRulesTests.cs`, `backend/tests/NexoRuta.IntegrationTests/Notificaciones/CancelacionPushTests.cs`, `CancelacionPublicaPushTests.cs`, `.../Reparto/ConciliacionEntregaHttpTests.cs`, `.../Seguimiento/PublicCancellationTests.cs` y frontend `CancelacionCommerceTests.cs` / `SeguimientoCancelacionPagesTests.cs`.
- No se modificaron el contrato de alta individual, `EfCancelacionesEnvioRepository`, rutas de API ni mensajes existentes. Se reutilizaron el núcleo autenticado/público, bloqueo por operador, transacción request-scoped, auditoría inmutable y outbox existentes.

### Evidencia de seguridad, atomicidad y concurrencia

- `cancel_shipment` y el núcleo compartido siguen validando contexto autenticado, acceso/actor/rol/permiso, pertenencia del envío y versión; la rama idempotente va después de validar autorización. El flujo público continúa exigiendo enlace vigente y código que corresponda al hash; la repetición con código inválido no se convierte en éxito.
- `apply_shipment_cancellation` sigue bloqueando el operador y luego el envío; vuelve a leer el estado bajo `FOR UPDATE`. Estado, parada suspendida, auditoría, aviso y outbox conservan la misma transacción. La repetición retorna la auditoría antes de esas escrituras.
- La migración no agrega privilegios de escritura de tablas al API. La función de matriz es inmutable y `EXECUTE` se revoca a `PUBLIC`; se concede a `nexoruta_cancel_fn` y `nexoruta_cancel_public_fn`, que ya son los propietarios de las funciones SECURITY DEFINER pertinentes.
- La prueba de rollback induce una excepción en la inserción del outbox después de ejecutar el núcleo con una parada activa y consulta posteriormente estado, versión, auditoría, aviso, outbox y parada: los cambios de la función no quedan confirmados.
- Las pruebas de carrera aceptan el resultado serializado: si entrega se confirma primero, cancelar produce conflicto; si cancelar se confirma primero, el hecho físico tardío no reactiva el envío. La recepción de una devolución que gana lleva a `Devuelto` y cancela la petición concurrente; si cancela primero, recibir con versión anterior produce conflicto y no reactiva el envío.

## Verificaciones ejecutadas

El destino Docker se confirmó por inspección de solo lectura:

```text
docker context inspect desktop-linux --format '{{json .Endpoints.docker}}'
→ {"Host":"npipe:////./pipe/dockerDesktopLinuxEngine","SkipTLSVerify":false}
docker info --format 'Name={{.Name}} ServerVersion={{.ServerVersion}}'
→ Name=docker-desktop ServerVersion=28.0.4
```

Las pruebas PostgreSQL usaron el fixture Testcontainers existente: bases `integration_<uuid>` aisladas, migraciones aplicadas a cada base efímera y descartadas por el fixture. No se resetearon ni modificaron bases compartidas o de producción.

| Comando/check | Resultado | Qué demuestra y qué no |
|---|---:|---|
| `dotnet test tests/NexoRuta.UnitTests/NexoRuta.UnitTests.csproj --no-restore --filter FullyQualifiedName~EnvioCancellationRulesTests --logger "console;verbosity=minimal"` | 27/27 | Dominio: siete orígenes permitidos, cinco prohibidos, terminalidad contra destinos y conciliación completa/incompleta que conserva `Cancelado`. |
| `dotnet test tests/NexoRuta.IntegrationTests/NexoRuta.IntegrationTests.csproj --no-restore --filter "FullyQualifiedName~CancelacionAutenticadaRespetaLaMatrizDeEstados|FullyQualifiedName~CancelacionPublicaAdmiteEnDevolucion|FullyQualifiedName~PersistenciaImpideReactivarUnEnvioCancelado|FullyQualifiedName~FalloAlInsertarOutboxRevierteEstadoHistorialAvisoYParada" --logger "console;verbosity=minimal"` | 15/15 | Matriz autenticada sobre PostgreSQL/HTTP de integración, elegibilidad pública desde `EnDevolucion`, trigger de estado terminal y rollback real de escrituras/outbox. El flujo HTTP usa `IntegrationApiFactory`/TestServer, no un Kestrel expuesto por socket. |
| `dotnet test tests/NexoRuta.IntegrationTests/NexoRuta.IntegrationTests.csproj --no-restore --filter FullyQualifiedName~FuncionDeMatrizConservaEjecucionSoloParaLosRolesPrivados --logger "console;verbosity=minimal"` | 1/1 | `has_function_privilege` confirma que `nexoruta_api` no puede ejecutar la función auxiliar y que los dos roles privados de cancelación sí pueden. |
| `dotnet test tests/NexoRuta.IntegrationTests/NexoRuta.IntegrationTests.csproj --no-restore --filter "FullyQualifiedName~CancelacionConcurrenteNoDeshaceEntregaFisicaNiExigeRendirla|FullyQualifiedName~EntregaYCancelacionConcurrentesRespetanElPrimerResultadoConfirmado|FullyQualifiedName~CancelacionConcurrenteConRecepcionDeDevolucionNuncaReactivaCancelado|FullyQualifiedName~DestinatarioVerificadoNotificaAlActualYPreservaEntregaOffline" --logger "console;verbosity=minimal"` | 6/6 | Entrega física offline, carrera entrega/cancelación, carrera cancelación/recepción y repetición pública válida/ inválida con ausencia de efectos duplicados. Transporte push usa el test double existente, no FCM remoto. |
| `dotnet test tests/NexoRuta.IntegrationTests/NexoRuta.IntegrationTests.csproj --no-restore --filter "FullyQualifiedName~ComercioAjenoNoPuedeCancelarPorHttpNiPorLaFuncionSql|FullyQualifiedName~DespachadorConGestionDeEnviosNoPuedeCancelar|FullyQualifiedName~CodigoSinVencimientoCancelaUnaVezYAuditaSinInventarUsuario|FullyQualifiedName~ConfirmacionesConcurrentesConservanUnaSolaCancelacion|FullyQualifiedName~MigracionPuedeRevertirseSinHechosPublicosYVolverAAplicarse|FullyQualifiedName~DespuesDeEntregaFisicaNoCancelaAunqueLaPruebaEstePendiente" --logger "console;verbosity=minimal"` | 7/7 | Aislamiento/denegación de actor, cancelación pública válida y concurrente, rechazo tras entrega y migración Down/Up en base efímera. |
| `dotnet build src/NexoRuta.Infrastructure/NexoRuta.Infrastructure.csproj --no-restore --verbosity minimal` | Correcto, 0 advertencias | Compila dominio/infraestructura afectada; no prueba por sí solo el comportamiento, que se cubrió arriba. |
| `dotnet test tests/NexoRuta.ApiClient.Tests/NexoRuta.ApiClient.Tests.csproj --no-restore --filter "FullyQualifiedName~ComercioConfirmaCancelacionConMotivoYVersionSinExponerCredenciales|FullyQualifiedName~TrackingOcultaCancelacionDespuesDeEntregaOCancelacion|FullyQualifiedName~TrackingPermiteSolicitarCancelacionEnDevolucion" --logger "console;verbosity=minimal"` | 10/10 | Pruebas de componentes con HTTP simulado y renderer Blazor: acción disponible en `EnDevolucion`, no visible en estados terminales/prohibidos y regresión de Commerce. Backoffice comparte el helper. Build muestra warning preexistente `CS8629` en `Backoffice/.../DetalleModel.cs:75`. |

Durante la secuencia test-first, el dominio dio RED con tres fallos de 27, incluyendo estados sobreescritos por conciliación; la matriz PostgreSQL dio RED con 11/12 casos y `EnDevolucion` como `409`. Tras los cambios, las suites anteriores quedaron verdes. Una aserción inicial esperaba `400` para repetir código público inválido y observó `404`; se ajustó a `404` (respuesta no disponible/no enumerativa del endpoint), verificando que el código incorrecto no obtiene éxito ni duplica efectos.

## Verificación no realizada y límites

- No se hizo revisión visual/interactiva en navegador: no había una herramienta de navegador disponible en esta sesión; la interfaz solo se verificó con pruebas de componente Blazor/HTTP simulado. No se instalaron herramientas ni se inició un stack local/browser.
- No se probó un broker o un proveedor FCM/SMTP real en este bloque. Se verificaron escrituras outbox en PostgreSQL y se reutilizaron pruebas con transportes controlados; no se afirma entrega externa exactamente una vez.
- La prueba de rollback fuerza un error SQL en el outbox dentro de la función. No simula pérdida de conexión durante `COMMIT`; el resultado de commit incierto sigue requiriendo reconciliación/reintento del cliente.
- No se ejecutó el conjunto completo backend/frontend. La cobertura ejecutada es acotada a cancelación, migración, seguridad inmediata y componentes afectados.
- La migración fue ejercitada por fixtures efímeros y por Down/Up; no fue desplegada ni aplicada en bases reales.

## Pendientes fuera de este bloque

- **CU-07 — corte reemplazado por 08/09:** al cerrar este bloque de cancelación, importación CSV, identidad externa/idempotencia y UX Commerce seguían pendientes; el backend y Commerce se implementaron después y tienen evidencia en `08-backend-importacion.md` y `09-commerce-importacion-y-verificacion.md`. El resto de esta sección solo delimita el alcance de la cancelación y no es estado vigente de importación.
- **Máquina de estados / otros casos:** no se cerraron las transiciones completas de depósito, ruta, intentos, reglas versionadas, plazos de validación, extravío, devolución ni consumidores/tareas tardías fuera de los caminos de cancelación probados. CU-08 continúa separado y obligatorio.
- **Mensajería transversal:** retries con espera creciente y administración de fallidos continúan pendientes; no se amplió su alcance.

**Conclusión del bloque:** la cancelación autenticada y pública conserva la matriz indicada, `Cancelado` queda terminal también ante escrituras SQL y una entrega offline tardía puede conservarse como hecho sin cambiar el estado. Esta evidencia cierra únicamente cancelación. El flujo directo de CU-07 se implementó después en 08/09; la auditoría global CU-07 conserva los pendientes transversales de 01/03, y el resto de la máquina de estados permanece abierto.
