# Solicitudes de baja y suspensión de organizaciones

## Estados y auditoría

El estado `Activa`/`Suspendida` pertenece a Comercio u Operador y no reemplaza el estado individual `AccesoUsuario.Activo`. Suspender conserva la organización, sus miembros, roles, envíos e historial. Cada solicitud y cambio de estado registra actor, motivo y fecha UTC; las solicitudes resueltas conservan su resultado.

El dueño persistido puede crear una solicitud indicando un motivo. Una solicitud pendiente no suspende la organización y solo puede haber una por organización, incluso ante concurrencia. Plataforma puede aprobarla (la resolución y la suspensión se confirman en una transacción) o rechazarla con motivo. Plataforma también puede suspender o reactivar por soporte. Las acciones repetidas para el estado actual son idempotentes; versiones obsoletas y resoluciones incompatibles devuelven conflicto.

## API

- `GET/POST /api/organizacion/actual/solicitudes-baja`: historial del ámbito autenticado y solicitud del dueño.
- `GET /api/organizacion/suspendida`: datos mínimos de estado para una sesión autenticada y restringida.
- `GET /api/admin/solicitudes-baja`, `GET /api/admin/solicitudes-baja/{id}` y `POST /api/admin/solicitudes-baja/{id}/resolver`: consulta y resolución de plataforma.
- `GET /api/admin/comercios` y `GET /api/admin/operadores` admiten filtro por estado; `PUT /api/admin/{tipo}/{id}/estado` suspende o reactiva.

Las rutas de plataforma requieren autoridad de plataforma vigente. Las rutas propias derivan organización y actor del acceso autenticado y verifican la propiedad persistida. No se confía en IDs de actor enviados por el cliente.

## Sesiones

Al suspender se incrementa `VersionSesion` para los accesos de la organización, sin cambiar su campo `Activo`. Los JWT anteriores quedan revocados y no vuelven a ser válidos al reactivar; sus titulares deben iniciar sesión otra vez. Un login posterior a la suspensión puede recibir solo el contexto restringido para consultar el estado y salir: no habilita operaciones organizacionales. El logout continúa disponible.

## Envíos y trabajos en curso

Una suspensión bloquea nuevas operaciones del comercio y excluye al operador de nuevas selecciones; la API también rechaza el ID suspendido enviado manualmente. La creación de envíos y el cambio de estado se serializan con bloqueos de fila en un orden estable. Si la suspensión confirma primero, la nueva creación no se confirma.

No se cancelan ni reasignan envíos existentes. Se conservan relaciones, historial y enlaces públicos de seguimiento; las contrapartes activas mantienen el acceso autorizado a su historial. Los Workers siguen procesando trabajo ya existente y no se pausan globalmente. El comportamiento de negocio de envíos que estaban en tránsito al suspender permanece sujeto a las transiciones existentes; este cambio no inventa una transición adicional.

## Actualización local

La migración `20261016215624_AddOrganizationSuspensionAndCancellation` es aditiva: inicializa organizaciones existentes como activas, añade auditoría, concurrencia y el índice único filtrado para solicitudes pendientes. En entornos habituales, `ApplyMigrations=false` y `SeedData=false` deben permanecer desactivados. La actualización debe aplicarse explícitamente después de respaldar y verificar la base destino; no requiere reset ni seeder.

## Solicitudes de reactivación

Una organización suspendida mantiene su pertenencia. El dueño con acceso individual activo puede iniciar sesión con alcance `OrganizacionSuspendida` y usar `GET/POST /api/organizacion/suspendida/solicitudes-reactivacion`; el historial y el envío de solicitudes están reservados al dueño persistido. Un empleado solo ve el aviso. Una solicitud pendiente no reactiva la organización y el índice `UX_SolicitudesReactivacion_Pendiente` impide duplicados aun ante concurrencia. Tras un rechazo puede solicitar nuevamente sin perder el historial.

Plataforma dispone de `GET /api/admin/solicitudes-reactivacion`, `GET /api/admin/solicitudes-reactivacion/{id}` y `POST /api/admin/solicitudes-reactivacion/{id}/resolver` con filtros, paginación y versión. Aprobar resuelve y activa en una transacción; rechazar conserva la suspensión. La reactivación directa de soporte cierra cualquier solicitud pendiente como `AtendidaPorSoporte`, con actor y motivo, en la misma transacción. No modifica `AccesoUsuario.Activo` ni vuelve válidos los JWT anteriores. La sesión restringida deja de ser válida al activar: el usuario debe ingresar de nuevo.

Las pantallas son `/reactivacion` (Blazor de Commerce, enlazada desde `/organizacion-suspendida`), `/OrganizacionSuspendida` (Backoffice) y `/solicitudes-reactivacion` más su detalle (Admin). Los formularios requieren motivo, confirmación y antiforgery. No se transmiten JWT en HTML ni URL.

`20261017032009_AddOrganizationReactivationRequests` agrega únicamente la tabla de solicitudes de reactivación y sus restricciones, sin alterar las solicitudes de baja ni datos existentes.
