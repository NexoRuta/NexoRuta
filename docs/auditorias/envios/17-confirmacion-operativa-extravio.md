# DEC-06 — Confirmación operativa de extravío

**Estado:** opción B implementada para el recorrido de servidor/Backoffice y la cardinalidad actual de un bulto.  
**Corte:** 27/10/2026.  
**Control nativo:** pendiente. Esta implementación y sus pruebas son evidencia técnica/manual, no aprobación nativa.

## Decisión funcional del equipo

El equipo eligió **opción B: confirmación directa**. Un administrador protegido del operador o un usuario asignado al rol protegido de código estable `despachador_operador` puede confirmar extravío indicando un motivo. También debe tener acceso vigente, pertenecer al operador del envío y conservar el permiso `envios.gestionar`.

La acción admite únicamente estos orígenes del diagrama:

- `EnDeposito → Extraviado`
- `AsignadoRuta → Extraviado`
- `EnTransito → Extraviado`
- `EnDevolucion → Extraviado`

No se agregó reporte/sospecha intermedia, evidencia documental obligatoria, recuperación ni otra salida de `Extraviado`. La opción B y el requisito de motivo son una decisión del equipo; el diagrama solo muestra pérdida confirmada y el PDF del taller no define esos detalles. El motivo no representa por sí mismo evidencia de una denuncia.

`Extraviado` sigue terminal. La confirmación no cambia custodia, no registra entrega/rendición/recepción y la interfaz presenta custodia como el último registro conocido. Una parada activa se suspende para impedir nuevas acciones incompatibles. La conciliación tardía especial de `Cancelado` no se extendió por analogía a `Extraviado`; el tratamiento de hechos físicos offline recibidos después de confirmarlo queda pendiente, sin permitir que reactiven ese estado.

## Autorización y rol dedicado

El endpoint conserva `[Authorize(Policy = "envios.gestionar")]` y vuelve a comprobar el acceso desde datos persistidos antes de consultar un comando repetido. La organización, el operador, el usuario, el acceso y el rol provienen del contexto autenticado/seleccionado y del acceso persistido; ninguno se recibe como identidad confiable en el DTO.

La validación focalizada compartida por DEC-05 y DEC-06 comprueba acceso activo, usuario autenticado, operador activo, scope de operador, rol protegido, permiso `envios.gestionar` actual y coincidencia con el operador del recurso. Acepta solo:

- El rol de administración protegido que el aprovisionamiento vigente asigna al operador: `administrador_operador`, `administrador` o `dueno` (se comparan códigos persistidos, no nombres visibles).
- El rol del dispatcher dedicado `despachador_operador`.

El dispatcher necesita también `envios.gestionar`; el código del rol por sí solo no concede acción cuando se revoca ese grant. `usuario_operador` y otros roles personalizados quedan denegados aunque tengan el permiso. Comercio, repartidor, accesos revocados y operadores ajenos tampoco autorizan. Ser dispatcher no amplía la autorización de cancelación.

La auditoría de código encontró que `EfPlataformaRepository` aprovisiona administradores protegidos con códigos `administrador` (identidad nueva) o `dueno` (identidad preexistente), mientras el bootstrap usa `administrador_operador`. El gate inicial reconocía solo el último; un nuevo administrador de operador recibía permiso funcional en su rol, pero su indicador `puedeGestionarDecisionesOperativasEnvio` era falso. Se corrigió el allowlist por códigos protegidos realmente creados por el proyecto. Un test TestServer falló primero con `false` y pasó después de la corrección; se conserva la denegación de `usuario_operador` y roles personalizados.

### Aprovisionamiento del dispatcher

- Organizaciones existentes: la migración aditiva `20261027020542_ConfirmOperationalShipmentLoss` crea `despachador_operador` por operador, lo marca protegido y le concede `envios.gestionar` y `envios.consultar`. Si el código reservado ya está ocupado por un rol no protegido, la migración falla explícitamente en vez de convertir el rol personalizado.
- Organizaciones creadas por plataforma: `EfPlataformaRepository` añade el rol y sus dos grants en la misma transacción de aprovisionamiento.
- Bootstrap: `DatosInicialesSeeder.EnsureDispatcherRoleAsync` crea/valida el rol y completa los grants registrados.
- Asignación: se reutiliza `GET /api/roles/asignables` y `POST /api/usuarios`. Crear el rol no asigna automáticamente ningún usuario. Las pruebas verifican que solo el flujo administrativo existente asigna el rol.

La tabla `ConfirmacionesExtravioEnvio` y el aprovisionamiento del nuevo rol están en la migración aditiva de DEC-06; la autorización usa los roles/grants persistidos existentes y no introduce otro catálogo.

## Contrato y recorrido técnico

`POST /api/envios/{id}/confirmar-extravio` recibe:

```json
{
  "versionEnvio": 7,
  "comandoId": "c2b07b7a-9c50-4e31-b606-70e53d49c21c",
  "motivo": "Pérdida confirmada durante el retorno"
}
```

La versión esperada es obligatoria; `comandoId` debe ser GUID no vacío y el motivo, tras `Trim`, debe contener entre 1 y 500 caracteres. El API devuelve el resultado de la confirmación, sus versiones/instante/identificador y el estado actual. Un request incompleto responde 400, actor no autorizado 401/403, recurso ajeno/no visible 404 y estado/versión/reutilización incompatible 409.

Flujo existente:

1. `RutasController.ConfirmarExtravio` requiere `envios.gestionar` y traduce el DTO HTTP a la operación tipada.
2. `GestionarRutasUseCase.ActorConGestionOperativaAsync` valida actor operador y llama `EfPermisosUsuarioRepository.PuedeGestionarDecisionesOperativasEnvioAsync`; el mismo guard de negocio se usa para DEC-05. Esto ocurre antes de entrar a resolver replay.
3. `EfRutasRepository.ConfirmarExtravioAsync` valida entrada, se une a la transacción de la solicitud, aplica el contexto RLS, serializa por operador y, para comando nuevo, bloquea/relee la fila de envío `FOR UPDATE`.
4. Comprueba pertenencia, versión actual, uno de los cuatro orígenes y ausencia de hecho físico de entrega que contradiga la pérdida. Si existe más de una parada activa, rechaza sin elegir una arbitrariamente.
5. Inserta la confirmación, la transición de dominio a `Extraviado`, la historia disparada por el cambio de estado, la suspensión de la parada y el aviso/outbox existente si la hoja está en curso. `SaveChanges` y el commit del middleware comparten la transacción; un fallo revierte los efectos.
6. La custodia permanece intacta. No se crea un evento RabbitMQ/Kafka nuevo ni un webhook sin contrato.

El request no permite fijar estado ni actor. La historia registra al actor/acceso autenticado, origen, correlación del comando, estado/versiones y fecha UTC; la confirmación conserva motivo y política/versiones relacionadas conforme al esquema. `ConfirmacionesExtravioEnvio` está separada del outbox, usa RLS `ENABLE`/`FORCE`, acceso de API restringido a `SELECT, INSERT`, índice único por `(OperadorId, ComandoId)` y por envío, y trigger append-only que rechaza `UPDATE`/`DELETE`. Funciones SECURITY DEFINER de la migración tienen propietario de esquema, `search_path` fijo y grants revocados a roles runtime.

### Replay y concurrencia

- Mismo actor autorizado, mismo `ComandoId` y payload equivalente: devuelve el resultado persistido original con `repetida = true` y el estado/version actual. No duplica confirmación, transición, historia, suspensión ni outbox.
- Mismo comando con envío, versión, motivo o contexto diferente: 409.
- Otro comando para el mismo envío ya confirmado: 409; no se infiere equivalencia porque el estado actual sea `Extraviado`.
- Estado/versión cambiados, cancelación concurrente, operación de ruta o recepción incompatible: relee bajo bloqueo y aplica el estado vigente; como máximo un cambio de estado incompatible puede confirmarse.
- Revocar acceso o permiso impide incluso recuperar un replay. La matriz de estado no concede actor.

## Backoffice

`Rutas.cshtml` muestra la acción únicamente si el estado de envío está entre los cuatro permitidos y `RutasModel` informa que el actor puede gestionar decisiones operativas. El formulario solicita motivo, confirmación explícita y evita doble submit. La respuesta explica “Extravío confirmado” y la última custodia permanece etiquetada como antecedente, no como recepción actual. Un conflicto de versión actualiza la ruta y conserva el motivo; un error incierto permite reintentar el mismo comando sin duplicar. `Extraviado` no ofrece reactivación ni confirmación adicional.

No se implementó cliente mobile offline ni lógica de DEC-07. La automatización visual usó Kestrel y Chromium en el entorno local aislado, cubrió desktop, viewport de 320 px y teclado; no equivale a una revisión exhaustiva de accesibilidad en todos los navegadores/dispositivos.

## Verificación ejecutada

Docker se inspeccionó en solo lectura antes de los fixtures: `docker context inspect desktop-linux --format '{{.Endpoints.docker.Host}}'` devolvió `npipe:////./pipe/dockerDesktopLinuxEngine`. Testcontainers confirmó Docker Desktop 28.0.4. Las integraciones usaron bases efímeras; los caminos de autorización DEC-05/06 corrieron con rol PostgreSQL API restringido (`NOSUPERUSER NOBYPASSRLS`), no con conexión superusuario para las peticiones HTTP.

| Nivel | Comando/prueba | Resultado | Qué demuestra / límites |
|---|---|---:|---|
| Dominio/terminalidad | Desde `backend`: `dotnet test tests/NexoRuta.UnitTests/NexoRuta.UnitTests.csproj --no-restore --filter 'FullyQualifiedName~EnvioLossRulesTests|FullyQualifiedName~EnvioCancellationRulesTests' --logger 'console;verbosity=minimal'` | **43/43** | Permite solo los cuatro orígenes para extravío, rechaza todos los demás y conserva terminalidad/cancelación. Es unitario; se complementa con integración real. |
| Integración de Reparto y regresiones de estado | Desde `backend`: `dotnet test tests/NexoRuta.IntegrationTests/NexoRuta.IntegrationTests.csproj --no-restore --filter 'FullyQualifiedName~NexoRuta.IntegrationTests.Reparto.OperacionesRepartoHttpTests' --logger 'console;verbosity=minimal'` | **50/50** | PostgreSQL efímero/TestServer. Incluye los cuatro orígenes permitidos, transiciones no admitidas, doble comando, carreras de extravío/cancelación, rollback de historia/outbox y regresiones de reprogramación/devolución. No prueba integración con brokers externos ni CU-08. |
| Roles/autorización/provisión DEC-05/06 | Mismo proyecto, filtro OR `DispatcherConfirmsLossButCannotCancelAndReplaysRecheckCurrentAccess`, `AdministradorConfirmaExtravioDesdeDepositoSinMoverCustodia`, `DespachadorDedicadoPuedeDecidirYRolesSinCorrespondenciaNoPuedenRepetirla`, `LossConfirmationMigrationProvisionsDispatcherForExistingOperatorsWithoutAssigningUsers` | **4/4** | Admin bootstrap protegido y dispatcher autorizado; rechazo de `usuario_operador`, custom manager, courier, comercio, operador ajeno y dispatcher sin permiso; cancelación no concedida; revocación de acceso/permisos antes de replay; migración de roles existentes sin asignar usuarios. |
| Organizaciones nuevas/flujo de asignación | Filtro OR `RestrictedApiCreatesOperatorOnlyForAuthorizedPlatformAndRejectsUnauthorizedUsersAtomically` y `IdentityOnlySessionCreatesOwnProtectedOrganizationAndRequiresNewLogin` | **3/3** | API restringida aprovisiona el dispatcher en organización nueva, conserva los grants de administrador y deja el rol sin asignación automática; el endpoint administrativo lo expone para asignación manual. También valida las variantes protegidas `administrador` y `dueno`. |
| Matriz autenticada de cancelación | `dotnet test tests/NexoRuta.IntegrationTests/NexoRuta.IntegrationTests.csproj --no-build --no-restore --filter 'FullyQualifiedName~CancelacionAutenticadaRespetaLaMatrizDeEstados' --logger 'console;verbosity=minimal'` | **12/12** | Valida completa la matriz vigente. La acción del dispatcher sigue separada y no concede cancelación. El primer intento normal de ejecutar este filtro encontró un error interno CLR/MSBuild durante resolución de conflictos; reejecutar sobre los ensamblados ya compilados con `--no-build` completó 12/12. |
| Red/rol API real aislado | `DispatcherConfirmsLossButCannotCancelAndReplaysRecheckCurrentAccess` y `AdministradorConfirmaExtravioDesdeDepositoSinMoverCustodia` dentro de la suite anterior | **2/2** | Requests TestServer contra PostgreSQL efímero con API restringida. Confirma estados, motivo recortado, custodia, historial, outbox/replay, y denegación de UPDATE/DELETE de confirmaciones. |
| Kestrel + navegador Backoffice | `BackofficeBrowserIniciaDecisionOperativaConConflictoYReintentoSeguro` | **1/1** | Kestrel local, Chromium y PostgreSQL efímero/restringido. La cuenta de administrador protegido ve el formulario y los campos requeridos; el dispatcher asignado por el flujo existente completa DEC-05/06 en la UI. Incluye motivo, confirmación, conflicto de versión, nuevo comando solo tras conflicto conocido, teclado, 320 px y desaparición de acción terminal. No se ejecutó la acción completa como administrador en navegador; su autorización de endpoint se verificó por integración/TestServer. |
| ApiClient/UI/OpenAPI | Desde `frontend`: `dotnet test tests/NexoRuta.ApiClient.Tests/NexoRuta.ApiClient.Tests.csproj --no-restore --filter 'FullyQualifiedName~RutasPagesTests|FullyQualifiedName~OpenApiContractTests' --logger 'console;verbosity=minimal'` | **52/52** | Compila proyectos clientes y fija contratos/pantalla. Los componentes usan handlers de prueba; el recorrido Kestrel/Chromium separado es la evidencia HTTP/navegador real. |

La autorización de la organización nueva se añadió como prueba de regresión tras observar primero RED (`puedeGestionarDecisionesOperativasEnvio = false` en un administrador protegido `administrador` recién aprovisionado). Tras permitir únicamente códigos protegidos que realmente crea la plataforma, la prueba quedó GREEN. También se corrigieron assertions de fixture de alta propia: los operadores ahora tienen el rol dispatcher adicional; las verificaciones consultan grants del rol de propietario y comprueban el dispatcher por separado. En el navegador real, además de ejecutar el flujo como dispatcher, se comprobó que el administrador protegido ve la acción DEC-06 y sus controles obligatorios; la petición real de ese botón no se ejecutó con esa cuenta.

Una ejecución anterior del filtro completo de Reparto en esta misma sesión había fallado 39 casos en la preparación compartida `Cargada` (`InicioJornada` devolvió `Conflicto`); un caso aislado pasó 1/1 y la repetición completa posterior pasó 50/50. No se estableció la causa de aquel primer resultado, así que no se atribuye a una regresión concreta. La matriz autenticada de cancelación también tuvo un primer intento abortado por un error interno CLR/MSBuild; la ejecución `--no-build` sobre los ensamblados compilados pasó 12/12.

No se probó publicación/consumo de RabbitMQ/Kafka en esta tarea. La evidencia Kestrel/Chromium no representa ejecución en todos los navegadores ni reemplaza la revisión nativa pendiente.

## Pendientes y límites

- CU-08 sigue obligatorio y separado. Esta acción solo se verifica para la cardinalidad actual de un bulto; no se decide cómo agrupar pérdidas parciales de multi-bulto.
- DEC-07 (reasignaciones desde estados activos/salidas adicionales) continúa pendiente.
- Cliente offline y política de conciliación de una entrega/rendición física recibida después de `Extraviado` continúan pendientes. No debe reactivarse el estado terminal ni borrarse el hecho cuando se defina esa política.
- No se agregaron eventos de broker/webhooks ni se verificó mensajería transversal.
- La revisión nativa continúa pendiente; no hay aprobación nativa ni cierre de la máquina de estados.

**Risk:** item 1 (nueva confirmación/estado persistidos), item 2 (autorización y RLS), item 4 (locks, replay y carreras), item 3 (contrato HTTP consumido por Backoffice).
