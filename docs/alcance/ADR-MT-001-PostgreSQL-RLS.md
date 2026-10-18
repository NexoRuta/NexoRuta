# ADR-MT-001 — Multitenancy con PostgreSQL RLS

**Implementación del ADR aceptado** · Estado: migración RLS implementada; verificación y aplicación local registradas al final · 17 de octubre de 2026

Este documento concreta para PostgreSQL la decisión archivada en [`PDF_s/ADR-Multitenancy.pdf`](PDF_s/ADR-Multitenancy.pdf). La sección **Implementación efectiva** al final es la fuente de verdad de la migración, permisos, recorridos y evidencia; las secciones previas conservan el diseño usado como punto de partida y cualquier lenguaje de “propuesta/futura entrega” queda supersedido por esa sección.

## Decisión

Se conserva una base y esquema compartidos, con RLS obligatorio en las tablas de negocio con datos organizacionales. La migración aplica `ENABLE ROW LEVEL SECURITY` y `FORCE ROW LEVEL SECURITY` a las 20 tablas protegidas; no se confía en filtros de EF como barrera de seguridad. Las políticas son *deny by default*: contexto ausente o inválido no ve filas y no puede insertar o modificar filas.

La unidad de autorización de un envío es la fila de `Envios`: contiene simultáneamente `ComercioId` y `OperadorId`, que identifica el operador seleccionado para **ese envío**. No existe ni se agregará una relación permanente comercio-operador como requisito para leer o escribir envíos. Un comercio puede tener envíos con operadores distintos; cada operador ve solamente los envíos cuyo `OperadorId` es el suyo.

El acceso de plataforma no equivale a acceso a todos los datos operativos. Plataforma administra organizaciones, usuarios y ciclos de vida; no obtiene acceso implícito a envíos, destinatarios, direcciones ni eventos de entrega. Un caso de soporte que requiera PII deberá tener una operación puntual, auditada y acotada, no una política general de plataforma.

## Modelo de contexto y roles PostgreSQL

### Roles

| Rol | Uso y permisos propuestos |
|---|---|
| `nexoruta_api` | Credencial de ejecución de la API. `LOGIN`, no es dueño de esquema/tablas, `NOSUPERUSER`, `NOBYPASSRLS`, sin membresía que permita `SET ROLE` a un rol privilegiado. CRUD solo en tablas necesario para los recorridos de API; sujeto a RLS. Las tablas globales de Identity son una excepción deliberada. |
| `nexoruta_worker` | Credencial separada de workers, `NOBYPASSRLS`, sin privilegios de dueño. Sin lectura global directa de negocio ni de la cola: ejecuta funciones acotadas para reclamar/finalizar trabajos y luego procesa cada trabajo bajo contexto de operador derivado de la fila reclamada. |
| `nexoruta_bootstrap` | Principal separado para un comando de bootstrap explícito, nunca una credencial de la API ni un seeder general al arranque. `NOBYPASSRLS`; ejecuta solo funciones de aprovisionamiento idempotentes y limitadas a las cuentas/filas iniciales definidas. No recibe CRUD irrestricto sobre todas las tablas. |
| `nexoruta_schema_owner` | Rol `NOLOGIN` dueño del esquema y los objetos. No se usa en conexiones de API/worker. RLS se fuerza también al dueño de tablas. |
| `nexoruta` (solo Compose local) | Conexión administrativa de una ejecución para EF migrations y provisioning de roles. No se configura en API/worker. Es el principal administrador inicial de PostgreSQL del Compose, no un login de runtime ni un rol que se herede desde ellos. |
| `nexoruta_public_fn` | Rol `NOLOGIN`, `NOBYPASSRLS`, dueño de una función de lectura pública de tracking; recibe solo los privilegios mínimos para esa función y políticas limitadas a un hash de enlace validado. La API recibe `EXECUTE`, no acceso directo a filas de tracking público. |
| `nexoruta_shipment_fn` | Rol `NOLOGIN`, `NOBYPASSRLS`, dueño de `create_shipment`; solo esta función puede insertar el agregado en orden consistente. La API recibe `EXECUTE`, no INSERT directo en destinatarios/direcciones/envíos de esa operación. |
| `nexoruta_queue_fn` | Rol `NOLOGIN`, `NOBYPASSRLS`, dueño de las funciones de claim/lease/ack/idempotencia de la cola. Worker recibe solo `EXECUTE`; no enumera ni modifica la cola directamente. |
| `nexoruta_auth_fn` | Rol `NOLOGIN`, `NOBYPASSRLS`, dueño de lookups mínimos de login/revalidación de acceso. No tiene acceso de lectura general concedido al rol API sobre `AccesosUsuario`/`AccesosPlataforma`. |
| `nexoruta_role_fn` | Rol `NOLOGIN`, `NOBYPASSRLS`, dueño de `fn_delete_unused_role`, con permisos mínimos para comprobar que el rol del tenant no está protegido ni asignado y eliminarlo. |
| `nexoruta_org_fn` | Rol `NOLOGIN`, `NOBYPASSRLS`, dueño de transición de estado y revocación acotada de sesiones para una organización validada por plataforma. |
| `nexoruta_job_fn` | Rol `NOLOGIN`, `NOBYPASSRLS`, dueño de la validación del mensaje de seguimiento persistido; no reclama ni enumera colas. |

Los nombres del cuadro son los roles de grupo/función implementados. Los logins reales `nexoruta_api_runtime`, `nexoruta_worker_runtime` y `nexoruta_bootstrap_runtime` se provisionan por separado con secretos inyectados. En Compose la API no migra ni ejecuta seeders generales al iniciar. La migración se ejecuta mediante el servicio explícito `rls-migrator` con la conexión administrativa local; el bootstrap de las tres cuentas se ejecuta por separado con el login restringido `nexoruta_bootstrap_runtime`.

### Contexto transaccional

Cada unidad de trabajo de API, incluidas las de solo lectura, debe:

1. Autenticar JWT y validar `UsuarioId`, `AccesoUsuarioId`/`AccesoPlataformaId`, `VersionSesion`, estado de la cuenta y estado vigente de la organización. Los IDs de organización del cuerpo/query del cliente no son autoridad.
2. Abrir una transacción PostgreSQL antes de cualquier consulta protegida.
3. Resolver el contexto a partir del acceso validado en servidor: `actor_kind` (`comercio`, `operador`, `plataforma`, `onboarding` o `worker`), `user_id`, `access_id`, `org_id` y, solo en alta de envío, `selected_operator_id`. El operador seleccionado se valida como activo para esa creación; no se persiste como membresía del comercio.
4. En esa transacción ejecutar `set_config(name, value, true)` (equivalente a `SET LOCAL`) con parámetros, antes de la primera consulta protegida. El último argumento `true` hace local el valor a la transacción. No se usa `SET` de sesión ni estado del pool.
5. Ejecutar todas las lecturas y escrituras de esa unidad en la misma conexión/transacción y confirmar o revertir. Una solicitud con varias unidades de trabajo vuelve a establecer y validar contexto en cada transacción.

El resolvedor de contexto debe volver a comprobar el acceso vigente en la frontera de la transacción (mediante una consulta de autenticación acotada) para que una suspensión o revocación entre validación JWT y ejecución no otorgue una ventana de acceso. Las lecturas también requieren transacción/contexto: aplicar `SET LOCAL` solo antes de `SaveChanges` deja las consultas previas expuestas o vacías.

Sin contexto, `current_setting(..., true)` se trata como `NULL`/vacío y todas las condiciones de tenant dan falso. SELECT retorna cero filas; INSERT/UPDATE no pueden satisfacer `WITH CHECK` y PostgreSQL rechaza la escritura; UPDATE/DELETE sobre una fila invisible afectan cero filas. La API conserva sus respuestas controladas sin revelar si una fila de otro tenant existe.

El cierre normal, `COMMIT` y `ROLLBACK` eliminan los ajustes `LOCAL`; al reciclar la conexión no debe quedar contexto previo. No se permite mantener una conexión contextualizada fuera de su transacción ni compartirla entre solicitudes. Las pruebas deben reutilizar deliberadamente el mismo backend físico después de commit y rollback.

Los settings de sesión no son una credencial criptográfica: el rol API puede ejecutar `set_config`. Este diseño evita fugas por filtros omitidos y uso accidental de otra organización; no pretende proteger contra SQL arbitrario ejecutado por un proceso API comprometido. Se requieren consultas parametrizadas, sin SQL dinámico proveniente del usuario, credenciales de DB privadas y los límites de privilegios anteriores. Un proceso/rol de aplicación comprometido sigue siendo una amenaza distinta que RLS no resuelve por sí sola.

### Flujos sin contexto organizacional ordinario

- **Login/JWT:** `Usuarios` y sus tablas auxiliares de Identity son datos de cuenta globales y se consultan por los servicios de Identity. El store EF estándar requiere que `nexoruta_api` tenga los permisos globales mínimos sobre esas tablas (`Usuarios`: SELECT/INSERT/UPDATE; claims/logins/tokens: solo las operaciones CRUD que sus stores usan; sin borrado de cuentas). RLS no puede distinguir una llamada a `UserManager` de otro SQL bajo esa misma credencial: las rutas API deben encapsular esos accesos y nunca devolver hashes/filas globales. La resolución de `AccesosUsuario`/`AccesosPlataforma` y la revalidación de sesión no se harán mediante una política `USING (true)` sobre tablas organizacionales: usarán funciones `SECURITY DEFINER` pequeñas que devuelven solo los datos de acceso mínimos, con `search_path` fijo, dueño `NOLOGIN`, `EXECUTE` revocado a `PUBLIC` y permisos concedidos solo a la API. La función toma el usuario ya autenticado o los claims de sesión y no devuelve listas de otros usuarios. Si se exigiera aislamiento a nivel DB también para cuentas globales, sería un cambio separado del store/credenciales de Identity, no una excepción tenant encubierta.
- **Registro:** el usuario sin organización puede crear su propia cuenta a través de Identity, pero no obtiene contexto tenant ni permiso para explorar organizaciones. Alta propia ejecuta una función/transacción de onboarding que verifica el usuario autenticado sin acceso organizacional y crea una sola organización y su acceso propietario; no se habilita INSERT global genérico a `Comercios`, `Operadores` o `AccesosUsuario`.
- **Catálogo de operadores:** el comercio autenticado puede leer una proyección segura de operadores activos para seleccionar uno por envío. Es catálogo explícito, no acceso a sus envíos o usuarios. Plataforma puede consultar todos; el usuario sin organización no recibe acceso salvo que un recorrido de registro lo requiera y se implemente una proyección pública separada.
- **Seguimiento público:** no hay política que interprete contexto nulo como público. Un token opaco válido se resuelve por su hash dentro de una función `SECURITY DEFINER` limitada que aplica las reglas vigentes del token y retorna solo la proyección pública permitida del envío. `nexoruta_api` no lee las tablas por esa ruta. Token inválido o no vigente retorna el mismo resultado no encontrado; no se expone PII innecesaria.
- **Workers:** el claim de cola se realiza por función con `FOR UPDATE SKIP LOCKED`, propietario `NOLOGIN` y salida mínima (ID/lease/operador/envío). El worker luego abre una transacción por tenant/trabajo, establece el operador del mensaje reclamado y accede solo a ese operador y al envío relacionado. La finalización/idempotencia usa funciones limitadas al ID de mensaje y lease del propio worker. No se otorga al worker una política global de negocio.
- **Bootstrap:** solo el proceso explícito usa funciones de lista blanca para cuentas/roles/organizaciones iniciales. Cada invocación es idempotente y no acepta SQL ni un tenant arbitrario del llamador. No habilita tablas para usuarios sin organización, no se invoca desde login/API y no reactiva seeders generales.

## Matriz de acceso por tabla y operación

La matriz expresa operaciones autorizadas para el actor en los recorridos API actuales; cada celda enumera las operaciones permitidas (`S/I/U/D` = SELECT/INSERT/UPDATE/DELETE) y toda operación omitida queda denegada. La RLS aplica esas fronteras a las filas de negocio; no convierte cada actor en un rol SQL. `—` significa sin operación autorizada. Los calificadores limitan la fila/flujo; `fn` indica únicamente una función `SECURITY DEFINER` enumerada arriba/abajo. `C` comercio, `O` operador, `P` plataforma con acceso de plataforma validado, `N` identidad sin organización, `B` bootstrap explícito, `W` worker. DELETE físico de negocio no se concede salvo las operaciones de roles especificadas en la matriz.

| Tabla | C | O | P | N | B | W |
|---|---|---|---|---|---|---|
| `Usuarios` | `S` propia/miembros autorizados; `I/U` solo cuenta autorizada; `D` — | Igual, miembros del operador | `S/I/U` solo administración/provisión permitida; `D` — | `S/U` propia; `I` registro propio; `D` — | `S/I/U` filas iniciales vía `fn`; `D` — | — |
| `AspNetUserClaims` | — directo; Identity solo por servicio para cuenta autorizada | — directo; Identity solo por servicio para cuenta autorizada | — directo; Identity solo por servicio en administración autorizada | — directo; solo servicio Identity | Claims iniciales vía `fn` | — |
| `AspNetUserLogins` | — directo; Identity solo por servicio para cuenta autorizada | — directo; Identity solo por servicio para cuenta autorizada | — directo; Identity solo por servicio en administración autorizada | — directo; solo servicio Identity | Logins iniciales vía `fn` | — |
| `AspNetUserTokens` | — directo; Identity solo por servicio para cuenta autorizada | — directo; Identity solo por servicio para cuenta autorizada | — directo; Identity solo por servicio en administración autorizada | — directo; solo servicio Identity | Tokens iniciales vía `fn` | — |
| `AccesosUsuario` | `S/I/U` del mismo `ComercioId`; no `D` propietario | `S/I/U` del mismo `OperadorId`; no `D` propietario | `S/I` solo primer propietario vía alta de organización; cambios globales por `fn`/workflow auditado | Sin consulta directa; lookup propio de login por `fn` | Solo acceso inicial por `fn` | — |
| `AccesosPlataforma` | — | — | `S/U` acceso de plataforma autorizado; no auto-concesión ni `D` | Login por `fn`, no SQL directo | Solo cuentas locales iniciales por `fn` | — |
| `Operadores` | `S` catálogo de activos (proyección segura) | `S/U` propio; no administra otros | `S/I/U/D` organizaciones según workflow de plataforma | — | `I/U` iniciales por `fn` | `S` solo datos requeridos por el trabajo del operador |
| `Comercios` | `S/U` propio | `S` solo si hay un envío visible para ese operador | `S/I/U/D` según workflow de plataforma | — | `I/U` iniciales por `fn` | `S` solo si lo requiere el envío reclamado |
| `Roles` | `S/I/U` mismo comercio; `D` solo rol propio no protegido/sin accesos, vía `fn` | `S/I/U` mismo operador; `D` solo rol propio no protegido/sin accesos, vía `fn` | — (roles de plataforma separados) | — | Roles iniciales por `fn` | — |
| `Permisos` | `S` catálogo | `S` catálogo | `S` catálogo | — | `I/U/D` catálogo durante bootstrap/migración controlada | — |
| `RolesPermisos` | `S/I/D` solo asignaciones de roles del comercio; `U` — | `S/I/D` solo asignaciones de roles del operador; `U` — | — | — | Semillas por `fn` | — |
| `RolesPlataforma` | — | — | `S/I/U` plataforma; no `D` del rol protegido en uso | — | Roles iniciales por `fn` | — |
| `RolesPlataformaPermisos` | — | — | `S/I/U` roles/plataforma | — | Semillas por `fn` | — |
| `SolicitudesBajaOrganizacion` | `S/I` propia solicitud/comercio | `S/I` propia solicitud/operador | `S/U` todas para resolución; no `D` | — | — | — |
| `SolicitudesReactivacionOrganizacion` | `S/I` propia solicitud/comercio | `S/I` propia solicitud/operador | `S/U` todas para resolución; no `D` | — | — | — |
| `CambiosEstadoOrganizacion` | `S` auditoría de su organización | `S` auditoría de su organización | `S/I` auditoría global de plataforma; no `U/D` (append-only) | — | Estado inicial por `fn` | — |
| `Destinatarios` | `S` solo si los referencia un envío propio; `I/U` solo `create_shipment`; `D` — | `S` solo filas vinculadas a envíos visibles de su operador; `I/U/D` — | — | — | — | `S` solo si es necesario para el envío reclamado; `I/U/D` — |
| `Direcciones` | Igual que `Destinatarios` | Igual que `Destinatarios` | — | — | — | Igual que `Destinatarios` |
| `Envios` | `S` propio; `I` solo `create_shipment`, con `ComercioId` propio y operador activo elegido para este envío; `U` solo campos aún editables por el comercio | `S/U` solo `OperadorId` propio y transiciones de operador; no reasigna tenant | — salvo función de soporte puntual auditada | — | — | `S` solo operador/envío reclamados; `I/U/D` — salvo una transición futura explícita |
| `Bultos` | `S/U` por envío propio; `I` solo `create_shipment`; `D` — | `S` solo por envío visible de su operador; `I/U/D` — | — | — | — | — |
| `EnlacesSeguimiento` | `S` propio; `I` al crear envío vía `create_shipment`; `U` revocación solo por servicio autorizado | `S` envíos de su operador; `I/U` emisión/revocación por servicio | — | — | — | `S/I/U` solo envío reclamado por servicio de worker |
| `EntregasSeguimiento` | — directo; solo `fn` pública devuelve proyección sin material secreto del token | — directo; solo servicio de seguimiento autorizado | — | — | — | `S/I` capability del envío reclamado; `U/D` — |
| `OutboxMessages` | `I` solo `create_shipment`; no `S/U/D` | — | — | — | — | Claim/lease/finalización solo por `fn`; procesar contenido bajo contexto operador |
| `ProcessedMessages` | — | — | — | — | — | `S/I` solo mediante función de idempotencia; no `U/D` directo |

La matriz de `Usuarios` reconoce una excepción necesaria de identidad global: login/registro, unicidad de correo y servicios de Identity deben encontrar la cuenta por email antes de conocer el tenant. Esa excepción solo aplica al almacén de cuentas y al servicio de Identity; no hace globales los accesos, roles, envíos ni datos de contacto de otras organizaciones. Las API de gestión de usuarios primero autorizan el `AccesoUsuario` del tenant y devuelven solo esos miembros.

Privilegios efectivos del rol DB para el store estándar de Identity: `Usuarios` permite SELECT/INSERT/UPDATE global y no DELETE; `AspNetUserClaims` y `AspNetUserLogins` permiten SELECT/INSERT/DELETE según los métodos del store (sin UPDATE directo); `AspNetUserTokens` permite SELECT/INSERT/UPDATE/DELETE. No hay políticas RLS de organización en estas cuatro tablas. En las columnas C/O/P/N de la matriz, la autorización de cuenta es por API (propia/miembros autorizados/registro), no un aislamiento que RLS pueda imponer dentro de la cuenta global. El acceso global del rol DB queda limitado a esas tablas; la RLS sigue bloqueando datos operativos.

## Política de envíos compartidos y tablas hijas

Para una fila `e` de `Envios`:

- Comercio `C` puede SELECT si `e.ComercioId = app.org_id`.
- Operador `O` puede SELECT si `e.OperadorId = app.org_id`.
- Worker ve solo el trabajo reclamado y el operador de ese trabajo.
- Plataforma no obtiene ninguna de las dos condiciones; su contexto no puede satisfacer una política de envíos.
- INSERT de comercio exige `e.ComercioId = app.org_id`, `e.OperadorId = app.selected_operator_id` y que ese operador exista y esté activo. `selected_operator_id` se deriva de la solicitud actual después de validación de servidor, se limpia al terminar la transacción y no es una relación de pertenencia persistente.
- UPDATE no puede mover el `ComercioId` ni el `OperadorId`: las columnas de identidad de tenant no se conceden para UPDATE ordinario. La reasignación futura, si se agrega, debe ser una operación explícita con autorización de ambos lados, auditoría y una función/política propia.

`Bultos`, `Destinatarios`, `Direcciones` y `EnlacesSeguimiento` se filtran por el padre `Envios` (ID y `OperadorId`), además de verificar las claves compuestas existentes. Para los datos PII de destinatario/dirección, la política de SELECT usa `EXISTS` contra un envío visible: el operador no puede leer filas huérfanas ni filas de otro operador; el comercio solo ve las que aparecen en sus envíos, incluso cuando comparte operador con otros comercios. **No se permite insertar esos hijos directamente desde EF:** el FK actual obliga a crear destinatario/dirección antes de `Envios`, por lo que una policy `WITH CHECK EXISTS(Envios)` no puede autorizar esa secuencia, aun dentro de una transacción. El servicio de API debe llamar `create_shipment` (función `SECURITY DEFINER`, dueño `nexoruta_shipment_fn`) que valida contexto comercio, operador activo seleccionado y payload, inserta destinatario/dirección, envío, bultos y outbox en ese orden y de forma atómica. La API no recibe INSERT directo en esas tablas; la función retorna el ID del envío y la API lo relee bajo RLS. El mismo patrón de ejecución `SECURITY DEFINER` con rol dueño restringido se usa en `fn_delete_unused_role` y en las funciones de cola/auth, sin conceder esos privilegios al proceso llamador.

`EntregasSeguimiento` almacena el capability/credencial del enlace (hash y material cifrado), no una historia de eventos de entrega. Se trata como secreto operativo ligado al envío. No se consulta desde las pantallas de comercio/operador ni se devuelve en el tracking público; el worker de generación y la función pública son los únicos caminos y solo manejan columnas necesarias.

## Políticas propuestas

Este SQL es una especificación de predicates, no una migración ni un script ejecutable. Las funciones `app.ctx_*()` representan lecturas tipadas de `current_setting(..., true)` con `NULLIF(..., '')`; entradas ausentes o mal formadas fallan cerradas. Los predicados de subconsulta también quedan sujetos a RLS.

```sql
-- Cada tabla de negocio listada en la matriz: ENABLE + FORCE.
-- No crear una policy general para plataforma, contexto vacío, PUBLIC o rol de aplicación sin actor.

CREATE POLICY envios_comercio_select ON "Envios"
  FOR SELECT TO nexoruta_api
  USING (app.ctx_actor_kind() = 'comercio'
         AND "ComercioId" = app.ctx_org_id());

CREATE POLICY envios_operador_select ON "Envios"
  FOR SELECT TO nexoruta_api
  USING (app.ctx_actor_kind() = 'operador'
         AND "OperadorId" = app.ctx_org_id());

CREATE POLICY envios_insert_comercio ON "Envios"
  FOR INSERT TO nexoruta_shipment_fn
  WITH CHECK (app.ctx_actor_kind() = 'comercio'
              AND "ComercioId" = app.ctx_org_id()
              AND "OperadorId" = app.ctx_selected_operator_id()
              AND EXISTS (SELECT 1 FROM "Operadores" o
                          WHERE o."Id" = "OperadorId" AND o."Estado" = 'Activa'));

CREATE POLICY envios_update_comercio ON "Envios"
  FOR UPDATE TO nexoruta_api
  USING (app.ctx_actor_kind() = 'comercio'
         AND "ComercioId" = app.ctx_org_id())
  WITH CHECK (app.ctx_actor_kind() = 'comercio'
              AND "ComercioId" = app.ctx_org_id());

CREATE POLICY envios_update_operador ON "Envios"
  FOR UPDATE TO nexoruta_api
  USING (app.ctx_actor_kind() = 'operador'
         AND "OperadorId" = app.ctx_org_id())
  WITH CHECK (app.ctx_actor_kind() = 'operador'
              AND "OperadorId" = app.ctx_org_id());

CREATE POLICY envios_worker_select ON "Envios"
  FOR SELECT TO nexoruta_worker
  USING (app.ctx_actor_kind() = 'worker'
         AND "OperadorId" = app.ctx_org_id()
         AND "Id" = app.ctx_job_envio_id());

CREATE POLICY envios_shipment_fn_select ON "Envios"
  FOR SELECT TO nexoruta_shipment_fn
  USING (app.ctx_actor_kind() = 'comercio'
         AND "ComercioId" = app.ctx_org_id()
         AND "OperadorId" = app.ctx_selected_operator_id()
         AND "Id" = app.ctx_creating_envio_id());

CREATE POLICY destinatarios_create_shipment ON "Destinatarios"
  FOR INSERT TO nexoruta_shipment_fn
  WITH CHECK (app.ctx_actor_kind() = 'comercio'
              AND "OperadorId" = app.ctx_selected_operator_id());

CREATE POLICY direcciones_create_shipment ON "Direcciones"
  FOR INSERT TO nexoruta_shipment_fn
  WITH CHECK (app.ctx_actor_kind() = 'comercio'
              AND "OperadorId" = app.ctx_selected_operator_id());

CREATE POLICY bultos_create_shipment ON "Bultos"
  FOR INSERT TO nexoruta_shipment_fn
  WITH CHECK (EXISTS (SELECT 1 FROM "Envios" e
                      WHERE e."Id" = "EnvioId"
                        AND e."OperadorId" = "OperadorId"
                        AND e."Id" = app.ctx_creating_envio_id()));

CREATE POLICY outbox_create_shipment ON "OutboxMessages"
  FOR INSERT TO nexoruta_shipment_fn
  WITH CHECK ("OperadorId" = app.ctx_selected_operator_id()
              AND "EnvioId" = app.ctx_creating_envio_id());

CREATE POLICY rolespermisos_delete_same_org ON "RolesPermisos"
  FOR DELETE TO nexoruta_api
  USING (EXISTS (SELECT 1 FROM "Roles" r
                 WHERE r."Id" = "RolId"
                   AND ((app.ctx_actor_kind() = 'comercio' AND r."ComercioId" = app.ctx_org_id())
                     OR (app.ctx_actor_kind() = 'operador' AND r."OperadorId" = app.ctx_org_id()))));

CREATE POLICY public_token_lookup ON "EntregasSeguimiento"
  FOR SELECT TO nexoruta_public_fn
  USING ("TokenHash" = app.ctx_public_token_hash());

CREATE POLICY public_tracking_envio ON "Envios"
  FOR SELECT TO nexoruta_public_fn
  USING (EXISTS (SELECT 1 FROM "EntregasSeguimiento" t
                 WHERE t."EnvioId" = "Envios"."Id"
                   AND t."OperadorId" = "Envios"."OperadorId"
                   AND t."TokenHash" = app.ctx_public_token_hash()));

-- Sin policy DELETE: el rol API no puede borrar envíos físicamente.
```

Las expresiones UPDATE anteriores se combinan con `GRANT UPDATE` por columna: ni el comercio ni el operador puede cambiar `ComercioId`, `OperadorId`, `Id` o autoría. Las columnas de negocio editables se corresponden con las transiciones ya autorizadas por los casos de uso. Una policy adicional de `WITH CHECK` exige que el nuevo estado, claves hijas y operador sigan siendo válidos. RLS limita filas, no reemplaza validación de máquina de estados ni protección de columnas. Las asignaciones `RolesPermisos` permiten DELETE solamente en roles de la organización actual; borrar un `Rol` sigue pasando por `fn_delete_unused_role`, que también verifica la ausencia de accesos y protección del sistema.

Para filas hijas, el patrón propuesto es `USING (EXISTS (SELECT 1 FROM "Envios" e WHERE e."OperadorId" = child."OperadorId" AND e."Id" = child."EnvioId"))`, y el mismo `EXISTS` en `WITH CHECK`; la policy de `Envios` visible al actor limita el padre al comercio u operador correcto. `Destinatarios`/`Direcciones` usan la FK correspondiente para SELECT/UPDATE; INSERT ocurre solamente dentro de `create_shipment`, por el orden FK descrito arriba. En `RolesPermisos`, SELECT/INSERT/DELETE requieren que el `RolId` resuelva a un rol visible del mismo tenant; DELETE se permite porque el caso actual reemplaza/remueve asignaciones. DELETE de `Roles` se hace solo mediante `fn_delete_unused_role`, que verifica mismo tenant, `EsProtegidoSistema = false` y ausencia de accesos/referencias antes de borrar. `Roles`, `AccesosUsuario` y solicitudes de organización comparan el discriminador y el `OperadorId` o `ComercioId` con `app.actor_kind()` y `app.org_id()`; el `WITH CHECK` conserva ese mismo par. Los permisos de plataforma usan políticas separadas sobre `RolesPlataforma*`, no una policy global sobre `Roles`.

Las familias restantes quedan con estos predicados equivalentes, siempre destinados a `nexoruta_api` solo en las tablas de negocio y con `WITH CHECK` en todo INSERT/UPDATE:

- `Operadores`: plataforma ve filas globales; operador ve/actualiza solo su `Id`; comercio solo hace SELECT de columnas de catálogo permitidas donde `Estado = Activa`; `WITH CHECK` de cambios exige conservar `Id` y el contexto plataforma.
- `Comercios`: comercio ve/actualiza su `Id`; operador ve solo cuando `EXISTS Envios` visible con el mismo `OperadorId` y `ComercioId`; plataforma puede administrar organización explícitamente. Los cambios no pueden modificar la clave.
- `AccesosUsuario` y `Roles`: `USING` requiere coincidencia del par de contexto `(actor_kind, org_id)` con las columnas generadas `TipoOrganizacion/OrganizacionId` o con el FK de organización; `WITH CHECK` repite el mismo par. `EsPropietario` no puede cambiarse por las rutas de empleados.
- `RolesPermisos`: `USING` y `WITH CHECK` para SELECT/INSERT/UPDATE resuelven `RolId` a un `Rol` visible del mismo tenant; DELETE usa el predicate explícito del ejemplo anterior. `Permisos` es un catálogo global de lectura; escrituras solo por migración/bootstrap controlado.
- Solicitudes de baja/reactivación comparan la organización con el contexto para SELECT/INSERT/UPDATE de resolución. `CambiosEstadoOrganizacion` permite SELECT por organización y SELECT/INSERT de plataforma; no admite UPDATE/DELETE (auditoría append-only).
- `RolesPlataforma`, `RolesPlataformaPermisos` y `AccesosPlataforma` requieren actor `plataforma` y la autorización de plataforma validada. `WITH CHECK` no permite crear otra identidad/plataforma ni alterar la fila de bootstrap protegida.
- `Bultos`, `EnlacesSeguimiento` y `EntregasSeguimiento` aplican `EXISTS Envios` sobre `(OperadorId, EnvioId)` y el contexto de actor; el worker usa además `job_envio_id`. La función pública añade `TokenHash = ctx_public_token_hash()` en `EntregasSeguimiento`, y la policy pública de `Envios` exige `EXISTS` del mismo capability. Nunca se configura una policy pública para contexto vacío.

Para tablas de autenticación, onboarding, bootstrap, público y cola se implementan funciones concretas, no una policy de tenant abierta. Cada función es `SECURITY DEFINER`, fija `search_path`, valida sus parámetros, limita columnas/salida, revoca ejecución a `PUBLIC`, y tiene un dueño `NOLOGIN` sin `BYPASSRLS`. `FORCE ROW LEVEL SECURITY` permanece activado; el rol de función recibe solo las policies estrictas necesarias para su fila/lease/token.

## Diseño base (reemplazado por la implementación efectiva al final)

| Área | Cambio necesario |
|---|---|
| API/auth | Añadir un resolvedor de contexto y un límite transaccional para toda consulta de tenant; revalidar acceso/versión/estado al abrir la transacción; mantener respuestas actuales para filas invisibles; no aceptar `org_id` del cliente. Separar expresamente plataforma, onboarding y tracking público. |
| EF Core | Configurar la transacción antes de la primera consulta (incluidas lecturas); establecer variables con `set_config(..., true)` parametrizado. Adaptar `ExecuteUpdate`, SQL `FOR UPDATE`, lecturas para Identity, consultas de relaciones e inserciones agregadas para ejecutarse en la misma transacción. Los filtros globales EF quedan como optimización/defensa secundaria. |
| Envíos | Mantener `Envio.OperadorId` y `Envio.ComercioId` como fuente de la relación por envío. Al crear, validar operador activo y usar contexto de comercio más `selected_operator_id`; no persistir ni consultar una tabla de membresía comercio-operador. Reemplazar el INSERT EF fragmentado por `create_shipment`, que crea el agregado completo de forma atómica por el orden FK. Proteger claves de tenant contra UPDATE ordinario. |
| Identity y usuarios | Mantener `Usuarios` como almacén global de cuentas Identity; usar `UserManager` para las operaciones actuales. Resolver membresías y accesos por funciones de login/sesión acotadas o por el contexto de tenant; nunca conceder SELECT global genérico de `AccesosUsuario`. |
| Workers | Usar rol/credencial distinto. Reemplazar lectura/actualización directa global de `OutboxMessages` y `ProcessedMessages` por claim/finalización/idempotencia limitados; después procesar cada fila con contexto de operador del trabajo reclamado. Partir lotes que abarcan operadores en transacciones por operador/trabajo. |
| SQL/migración | Crear roles, grants, policies RLS y `FORCE ROW LEVEL SECURITY`; funciones de autenticación/onboarding/worker/tracking con `search_path` seguro; grants por columna; índices para predicados/FK. No permitir que runtime sea dueño, superusuario o `BYPASSRLS`. Migraciones desde una credencial y operación separadas, nunca desde inicio de API. |
| Configuración | Inyectar credenciales separadas de API, worker, bootstrap y migrator en el despliegue futuro. Compose local conserva en este corte la configuración actual con migraciones y seeders generales desactivados; no se cambia aquí. |

## Operaciones actuales que requieren adaptación

1. `EfUsuariosLoginRepository` resuelve accesos y organizaciones con una consulta global, y JWT revalida acceso/versión. Una policy tenant-only la dejaría sin filas. Se resuelve con lookup de autenticación acotado que devuelve solo el acceso de ese usuario, no con `USING (true)` en `AccesosUsuario`.
2. Registro y alta propia comienzan con identidad sin organización y luego crean organización/acceso propietario. El primer paso continúa por Identity; el segundo usa onboarding atómico que solo crea una organización vinculada al usuario. No se concede acceso general a filas de otras organizaciones.
3. La consulta de operadores activos para crear envíos es hoy un catálogo global. Se conserva únicamente como lectura segura de catálogo activo. La creación se autoriza en la fila del envío para el operador elegido esa vez; no se añade vínculo permanente.
4. La creación actual inserta destinatario/dirección antes de insertar el envío por los FK no anulables (`NexoRutaDbContext.cs:257–265`, `EfEnviosRepository.cs:62–72`). Una policy de INSERT que requiera un envío padre existente bloquearía esa secuencia. `create_shipment` reemplaza los INSERT EF individuales, valida actor/operador y crea todos los elementos del agregado en una única transacción. Lecturas de PII siguen filtradas por referencias desde `Envios`; INSERT directo queda denegado.
5. Gestión de usuarios/roles y ciclos de suspensión/reactivación toca usuarios, accesos, estado organizacional y auditoría. Las consultas de tenant se acotan a la organización; las resoluciones de plataforma usan contexto de plataforma; las tablas de Identity siguen disponibles solo por los servicios de cuenta. `CambiosEstadoOrganizacion` es append-only. La gestión actual de permisos elimina asignaciones `RolesPermisos` al reemplazar permisos, por lo que DELETE scoped debe seguir permitido; la eliminación de un rol no protegido y sin accesos/referencias se conserva mediante `fn_delete_unused_role`.
6. El seguimiento público actual consulta por token sin login. Contexto ausente ahora denegará su SQL directo; se conserva el contrato mediante una función token-capability limitada que verifica hash, expiración y revocación y devuelve una proyección pública, nunca acceso general a `Envios`.
7. El worker reclama mensajes globalmente con SQL/`SKIP LOCKED`, consulta/actualiza outbox e idempotencia e inserta seguimiento. RLS bloqueará su acceso directo global; se separa claim/finalización (funciones acotadas) de la lectura/escritura por operador con contexto.
8. Bootstrap/seeders ejecutan escrituras transversales. Solo un proceso explícito con principal bootstrap y funciones de lista blanca podrá crear las filas iniciales. No se activa el seeder general de Compose.

## Pruebas de aceptación (ejecutables; evidencia pendiente al cierre)

Las pruebas deben conectarse con el mismo login/rol `nexoruta_api` (y los roles worker/bootstrap solo en sus suites), `NOSUPERUSER`, `NOBYPASSRLS`, que usará la aplicación. La fixture de pruebas podrá crear roles/datos como administrador, pero las aserciones ejecutarán las operaciones protegidas con la credencial restringida. No vale probar RLS como superusuario, dueño de tablas o usando una policy simulada.

1. **Dos operadores y varios comercios:** crear O1/O2, C1/C2; C1 crea un envío con O1 y otro con O2; C2 crea uno con O1. C1 ve ambos propios; O1 ve el envío C1-O1 y C2-O1; O2 ve solo C1-O2. Ninguno ve el envío de otro operador/comercio. Verificar que no existe ni se necesita una membresía C1-O1/C1-O2.
2. **Lecturas y datos hijos:** omitir deliberadamente filtros EF y consultar por IDs/SQL crudo; envíos, bultos, destinatarios, direcciones y enlaces siguen limitados por el envío padre visible. La tabla `EntregasSeguimiento` no expone hashes/secretos. IDs de filas hijas de otra organización no revelan datos.
3. **INSERT/WITH CHECK:** sin contexto y con contexto comercio/operador incorrecto, insertar envío, bulto, dirección, destinatario, rol o acceso de otra organización falla. Comercio crea el agregado solo por `create_shipment`; la inserción del hijo antes del padre funciona dentro de esa función, se revierte toda junta ante error, y la API no puede insertar hijos huérfanos directamente. Comercio puede elegir cualquier operador activo en esa operación; operador inactivo o asignación cruzada falla. No se crea vínculo permanente.
4. **UPDATE/DELETE:** una fila ajena es invisible; UPDATE/DELETE afectan cero filas o son rechazados. Modificar `ComercioId`, `OperadorId`, `UsuarioId`, el padre de una fila hija o claves de tenant mediante UPDATE es rechazado. Eliminar asignaciones de permisos en roles propios funciona; `fn_delete_unused_role` elimina un rol propio no protegido solo cuando ya no tiene accesos/referencias; eliminar un rol protegido/en uso falla. Otros DELETE físicos de negocio quedan denegados desde runtime.
5. **Contexto vacío/falso:** sin `set_config`, con setting vacío, actor no reconocido o tenant ausente, SELECT devuelve cero y todas las escrituras quedan denegadas. No se acepta el ID de organización de query/body como contexto.
6. **Pool/concurrencia:** en el mismo backend pooled, comenzar con O1, commit; luego sin contexto (cero filas); luego rollback; luego C1; ninguno hereda contexto. Dos solicitudes concurrentes de tenants distintos no comparten transacción ni resultado.
7. **Autenticación/Identity:** login de cuenta de operador, comercio, plataforma y sin organización; unicidad global de email; registro crea solo su identidad; JWT de sesión suspendida/obsoleta sigue rechazado. Lookup de login/versión devuelve solo datos mínimos y no permite listar accesos ajenos por SQL normal.
8. **Plataforma:** puede crear/editar/suspender/reactivar organizaciones y resolver solicitudes/auditoría según el caso actual, pero SELECT directo de `Envios`, `Bultos`, direcciones y destinatarios no devuelve filas. Una futura operación de soporte requeriría función auditada con un envío explícito.
9. **Tracking público:** token válido retorna solo la proyección pública del envío exacto; no devuelve `TokenCifrado`, `Nonce`, `Tag` ni otros secretos de `EntregasSeguimiento`. Token inválido o no vigente según reglas actuales no revela si un envío existe. El rol/API no puede consultar filas arbitrarias de tracking sin el capability.
10. **Worker/bootstrap:** dos workers concurrentes no reclaman el mismo lease; un worker procesa únicamente el operador/envío del mensaje reclamado; no puede enumerar otras colas ni tenant. Bootstrap es idempotente, solo produce las filas de lista blanca y no obtiene SELECT/UPDATE global de negocio.
11. **Rol/policies:** verificar en `pg_roles` `rolsuper=false`, `rolbypassrls=false`, dueño diferente y ausencia de `SET ROLE` privilegiado; `relrowsecurity` y `relforcerowsecurity` activos para cada tabla protegida; probar INSERT/UPDATE con predicates `WITH CHECK` y SELECT/UPDATE/DELETE con `USING`.

## Implementación efectiva

Esta sección reemplaza las descripciones en futuro anteriores. La autoridad ejecutable es la migración `20261017201732_EnablePostgreSqlRls`; el estado de instalación local y las pruebas se completan en la bitácora inferior después de ejecutar las verificaciones. La migración protege 20 tablas de negocio con `ENABLE ROW LEVEL SECURITY` y `FORCE ROW LEVEL SECURITY`. No se agrega una tabla de membresía comercio-operador.

### Tabla por actor y operación

La matriz describe privilegios SQL efectivos, no concede por sí misma permisos HTTP. `C` = comercio autenticado; `O` = operador autenticado; `P` = plataforma con `plataforma.organizaciones.gestionar`; `I` = identidad sin organización; `B` = proceso bootstrap restringido a las cuentas/organizaciones configuradas; `W` = worker restringido a un trabajo reclamado. `S/I/U/D` significan SELECT/INSERT/UPDATE/DELETE. “Función” indica una operación explícita, validada y con salida acotada, no DML directo. `—` es denegación. Los permisos dinámicos y las reglas de dominio siguen comprobándose en API además de RLS.

| Tabla (24) | Comercio | Operador | Plataforma | Identidad sin org. | Bootstrap | Worker |
|---|---|---|---|---|---|---|
| `Usuarios` (Identity) | S/I/U por UserManager, global | S/I/U por UserManager, global | S/I/U por UserManager, global | S/I/U por UserManager, global | S/I/U solo identidad configurada | — |
| `AspNetUserClaims` | S/I/D por almacén Identity | S/I/D por almacén Identity | S/I/D por almacén Identity | S/I/D por almacén Identity | S/I/D de cuentas de bootstrap | — |
| `AspNetUserLogins` | S/I/D por almacén Identity | S/I/D por almacén Identity | S/I/D por almacén Identity | S/I/D por almacén Identity | S/I/D de cuentas de bootstrap | — |
| `AspNetUserTokens` | S/I/D por almacén Identity | S/I/D por almacén Identity | S/I/D por almacén Identity | S/I/D por almacén Identity | S/I/D de cuentas de bootstrap | — |
| `AccesosUsuario` | S/I/U de empleados propios; dueño excluido | S/I/U de empleados propios; dueño excluido | I solamente para el propietario inicial de la organización creada; no enumeración | S/I del propio usuario/acceso y alta propia | S/I del propietario de las cuentas iniciales | — |
| `AccesosPlataforma` | — | — | S del acceso validado actual | — | S/I únicamente `Id = 1` | — |
| `Comercios` | S/U del propio comercio; I durante alta propia | S solo si comparte un envío visible | S/I/U con capability de gestión de organizaciones | I del comercio propio durante alta propia | S/I/U del comercio configurado | — |
| `Operadores` | S del catálogo activo y de operadores asociados a envíos propios (incluidos suspendidos para conservar historial) | S/U del operador propio; I durante alta propia | S/I/U con capability de gestión de organizaciones | I del operador propio durante alta propia | S/I/U del operador configurado | — |
| `SolicitudesBajaOrganizacion` | S/I de su organización | S/I de su organización | S/U con capability de gestión; solo resolución | — | — | — |
| `SolicitudesReactivacionOrganizacion` | S/I de su organización | S/I de su organización | S/U con capability de gestión; solo resolución | — | — | — |
| `CambiosEstadoOrganizacion` | S de historial propio | S de historial propio | S/I de transiciones de organizaciones | — | — | — |
| `Roles` | S/I/U en su organización; D por función de rol | S/I/U en su organización; D por función de rol | S/I en la organización seleccionada; sin listado general | S/I durante creación propia de organización | S/I/U de roles propios de cuentas iniciales | — |
| `RolesPermisos` | S/I/D de roles visibles propios | S/I/D de roles visibles propios | — | — | S/I/D en los roles iniciales configurados | — |
| `RolesPlataforma` | — | — | S del rol de plataforma actual; UPDATE no está concedido al runtime | — | S/U solo roles de sistema protegidos | — |
| `RolesPlataformaPermisos` | — | — | S/I del rol actual; UPDATE/DELETE no están concedidos al runtime | — | S/I de asignaciones a roles protegidos; DELETE no está concedido | — |
| `Permisos` (catálogo) | S; sin editar | S; sin editar | S/I de códigos incluidos en allowlist | S/I de códigos incluidos en allowlist | S/I de códigos incluidos en allowlist | — |
| `Envios` | S de envíos propios; I atómico por función; sin DML de actualización directa | S de envíos elegidos para ese operador; sin crear para comercios | — | — | — | S del envío del trabajo validado |
| `Destinatarios` | S de hijos de envíos visibles; I solo dentro de creación atómica | S de hijos de envíos visibles; I solo dentro de creación atómica | — | — | — | — |
| `Direcciones` | S de hijos de envíos visibles; I solo dentro de creación atómica | S de hijos de envíos visibles; I solo dentro de creación atómica | — | — | — | — |
| `Bultos` | S de hijos de envíos visibles; I solo dentro de creación atómica | S de hijos de envíos visibles; I solo dentro de creación atómica | — | — | — | — |
| `EnlacesSeguimiento` | S de envíos visibles | S de envíos visibles | — | — | — | S/I del trabajo validado |
| `EntregasSeguimiento` | S de entregas enlazadas a envíos visibles | S de entregas enlazadas a envíos visibles | — | — | — | S/I del trabajo validado |
| `OutboxMessages` | I de los dos eventos permitidos para el envío seleccionado | — | — | — | — | Solo mediante claim/finish acotados; luego S de su trabajo validado |
| `ProcessedMessages` | — | — | — | — | — | S/I del mensaje y consumer actuales del trabajo validado |

Las cuatro tablas Identity no llevan RLS porque UserManager necesita resolver una identidad global y las credenciales son globalmente únicas. Esto no globaliza `AccesosUsuario`, `Roles`, `Envios` ni sus hijos: cada una de esas tablas conserva RLS. Las consultas/ediciones de cuenta siguen siendo servicio interno de Identity, no endpoints predeterminados expuestos. La aplicación nunca debe tratar `Usuarios` como autorización organizacional.

### Predicados, envíos y funciones excepcionales

Las policies de API aplican `USING` para filas existentes y `WITH CHECK` para nuevas versiones/filas. Los accesos, roles, solicitudes, organización y catálogo se restringen por actor, organización actual, acceso/permiso dinámico y claves estables; no hay `USING (true)` para negocio. Para envíos `USING` permite comercio por `ComercioId` y operador por `OperadorId` del propio envío. Los hijos se filtran por `EXISTS` en un envío visible y por las claves compuestas `EnvioId`/`OperadorId`. Un comercio puede leer un operador inactivo solo si aparece en uno de sus envíos visibles; esto conserva el detalle histórico sin habilitarlo en el catálogo activo. Plataforma no tiene policy de envío, dirección ni PII.

Al crear envío, el comercio puede elegir cualquier operador activo en esa solicitud. La API valida acceso persistido y operador, fija `selected_operator_id` y el contexto de creación dentro de la transacción; `create_shipment` vuelve a bloquear y comprobar el operador seleccionado frente a una suspensión concurrente, y crea destinatario, dirección, envío, bultos y outbox en el orden exigido por los FK, de forma atómica. Se retorna el ID y la API relee bajo RLS. No se concede a la API INSERT/UPDATE directo en esas tablas de hijos/envíos; no hay una membresía permanente. Las claves tenant no se actualizan por una policy genérica.

Las únicas operaciones que cruzan políticas de propósito general se encapsulan en funciones `SECURITY DEFINER` con `search_path` fijo, rol dueño `NOLOGIN`/`NOBYPASSRLS`, EXECUTE revocado a PUBLIC, parámetros comprobados y grants mínimos:

* `login_lookup`, `lookup_access`, `lookup_platform_access`, `lookup_unassigned_identity`: Identity global valida correo/cuenta; función devuelve solo acceso de login o acceso por ID/usuario para revalidar, no permite listar accesos organizacionales arbitrarios.
* `public_tracking`: recibe el token presentado, calcula/valida internamente su hash, vigencia y revocación, y devuelve únicamente la proyección pública; no confía en un hash de GUC suministrado por el llamador ni entrega secretos de enlace.
* `create_shipment`: única escritura del agregado con sus children/outbox; bloquea solo el operador elegido, verifica que siga activo y no deja destinatarios/direcciones huérfanos.
* `claim_outbox` y `finish_outbox`: worker reclama con lease/`SKIP LOCKED` y salida `OutboxClaim` mínima (sin lease, estado interno, procesador ni último error); completa solo si ID y procesador coinciden.
* `begin_tracking_job`: valida que el message ID sea un evento RabbitMQ de seguimiento persistido y devuelve la asociación exacta operador/envío. El worker establece luego un nuevo contexto de trabajo para sus lecturas/escrituras scoped e idempotencia.
* `lock_owned_role`: toma un lock booleano acotado a un rol del tenant actual, incluido el rol protegido para permitir asignación autorizada; no modifica ni devuelve la fila del rol. `delete_unused_role` borra únicamente un rol no protegido del tenant actual, solo si no tiene accesos ni referencias. `set_organization_state` y `revoke_org_sessions` actualizan la organización objetivo y revocan sus sesiones con columnas explícitas, sin leer los envíos.

`Permisos` es un catálogo global de códigos, no catálogo de autorización por tenant: lectura global, alta restringida a allowlist en provisioning/uso actual y sin UPDATE/DELETE. El endpoint de login es una operación global de Identity más lookup de acceso acotado. Registro/alta propia opera como `identidad` sin organización y solo crea su propia organización y acceso propietario. Tracking público es una capability por token, no acceso anónimo a tablas. Bootstrap tiene login separado de lista blanca; el seeder general permanece desactivado. Workers usan el principal worker y funciones de cola, y solo procesan el operador/envío del evento persistido.

### Roles, contexto y ciclo de conexión

`nexoruta_api`, `nexoruta_worker` y `nexoruta_bootstrap` son roles grupales `NOLOGIN`; los servicios usan los logins separados `nexoruta_api_runtime`, `nexoruta_worker_runtime` y `nexoruta_bootstrap_runtime`. Todos son `NOSUPERUSER`, `NOBYPASSRLS`, no dueños, y no heredan acceso a rol dueño. `nexoruta_schema_owner` y los roles dueños de funciones (`nexoruta_auth_fn`, `_public_fn`, `_shipment_fn`, `_queue_fn`, `_role_fn`, `_org_fn`, `_job_fn`) son `NOLOGIN` y sin `BYPASSRLS`. La conexión `nexoruta` en el Compose local es solo administradora del migrator/provisioner explícitos; nunca se carga en API/worker. Roles y passwords se provisionan fuera de la API desde variables separadas.

El middleware API inicia transacción (incluidas solicitudes solo lectura), consulta la sesión/acceso persistidos y deriva `actor_kind`, `user_id`, acceso, organización/rol y capacidad efectiva del servidor. No acepta IDs de organización como fuente de autoridad. Establece valores parametrizados con `set_config(name, value, true)` antes de la primera consulta de negocio; todo el request usa el mismo DbContext, conexión y transacción. Una respuesta fallida revierte; commit o rollback termina el alcance local. La siguiente solicitud comienza sin contexto anterior porque el valor es local a transacción. La ausencia de contexto es deny-by-default. La operación pública usa su función capability aislada. El worker primero valida/claim mediante funciones y, por trabajo, establece dentro de la transacción un contexto derivado de la fila de outbox persistida. Los jobs no heredan un GUC del pool ni confían en el payload del broker como autorización.

### Instalación y verificación

La instalación soportada en Compose es explícita: (1) confirmar que el destino es el servicio PostgreSQL local `nexoruta` y el volumen de desarrollo del proyecto; (2) obtener y validar un respaldo; (3) ejecutar el servicio de migración con la credencial local administradora; (4) provisionar roles/logins restringidos con el script dedicado; (5) ejecutar solo el bootstrap acotado con las seis variables de las tres cuentas; (6) recrear API/worker y comprobar portales y recorridos. La API mantiene `DatabaseInitialization__ApplyMigrations=false` y `SeedData=false`; no activar seeders generales ni migrar otro proyecto/host. El detalle de destino, respaldo, resultados y smoke debe registrarse al concluir. Si una comprobación crítica falla, no declarar la instalación completa y restaurar/rollback únicamente en ese destino local verificado.

#### Evidencia preinstalación local

* PostgreSQL efímero (Testcontainers 18): migración completa desde esquema vacío y actualización desde la migración Identity previa. `UpgradeFromThePreviousSchemaPreservesUserAccessAndShipmentGuids` conserva GUID de usuario, acceso, organización, envío, destinatario y dirección.
* `RlsPolicyTests` y `RlsRestrictedHttpFlowTests`: el conjunto RLS enfocado pasó 38/38 bajo logins efímeros sin `SUPERUSER`/`BYPASSRLS` que heredan el mismo rol grupal `nexoruta_api`/`nexoruta_worker`. Incluye las 20 tablas forzadas, ausencia de contexto, dos comercios y dos operadores con elección por envío, PII de plataforma, contexto local tras commit/rollback/reuso de backend, transacciones concurrentes, registro/alta propia, bootstrap, funciones públicas/worker, claim/idempotencia concurrentes, alta de envío HTTP, historia de operador suspendido, permisos dinámicos y asignación del rol protegido.
* `dotnet test backend/NexoRuta.sln -c Release --no-restore`: 270 integración, 100 unitarias y 3 de arquitectura correctas; el conjunto completo terminó sin fallos.
* `dotnet test frontend/NexoRuta.sln -c Release`: 219 correctas; incluye `OpenApiContractTests` y las suites de ApiClient/portales.
* `dotnet build backend/NexoRuta.sln -c Release --no-restore`: correcto, 0 warnings/errores. `dotnet ef migrations has-pending-model-changes`: sin cambios pendientes en snapshot.
* SQL de `AddIdentityUserStore` a `EnablePostgreSqlRls` generado por `dotnet ef migrations script`: 113,117 bytes; se verificaron 20 `FORCE ROW LEVEL SECURITY`, 106 `CREATE POLICY` y 15 funciones. `git diff --check` pasó en raíz y backend.
* Revisión independiente final de solo lectura: aprobó el parche después de corregir DELETE de permisos dinámicos, creación de envíos al bloquear el operador seleccionado, asignación protegida de roles e historial del nombre de operador suspendido. Hallazgo final comprobado en scratch contra árboles inmutables.

La revisión nativa RDD quedó bloqueada en el preflight `collect(intended_untracked_selection_required)`: el contrato exige `gentle-ai.review-intended-untracked-selection/v1`, pero la instalación solo expone `external.select_intended_untracked` y un dominio `schema_bound_json`, sin ruta de captura ni esquema serializable. No se inventó un payload ni se creó linaje. Por ese gate pendiente no se aplicaron cambios al PostgreSQL local ni se obtuvo respaldo, no se recrearon servicios y no se hicieron smoke persistentes. Antes de continuar, resolver el preflight de selección de archivos y terminar el ciclo de revisión nativo; después confirmar por identidad SQL que el destino es exclusivamente el Compose local `nexoruta`, respaldar, migrar/provisionar/bootstrap y ejecutar los smoke. No declarar CU-01 cerrado; la migración solo se probó en PostgreSQL efímero y no se aplicó a una base persistente.
