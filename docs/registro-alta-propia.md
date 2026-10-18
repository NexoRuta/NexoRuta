# Self-service registration and organization onboarding

Self-service is the normal onboarding path; Admin is reserved for support or explicitly administrative provisioning. Current CU-01 behavior and its traceability matrix are documented in [the CU-01 audit](../backend/docs/cu/CU-01-comercios-usuarios.md). The workshop's literal Backoffice/operator responsibility differs from the adopted Commerce self-service model; academic acceptance remains with the team/instructor.

## User journey

1. Open the public Commerce home `/` and choose **Crear cuenta** (`/registrarse`). Enter email, password (at least 12 characters) and matching confirmation.
2. Sign in at `/ingresar`. An unassigned identity goes directly to `/organizacion`, never through commerce/operator-only pages.
3. Choose commerce or operator and enter `Nombre` (required, up to 160 characters), the organization's only current business field.
4. Creation signs out the identity-only cookie and redirects to `/organizacion-creada/comercio` or `/organizacion-creada/operador`.
5. Sign in again with the **same** credentials at Commerce or Backoffice. Commerce opens `/envios`; its existing shipment form now lives at `/envios/crear`. Each application establishes its own protected session. No SSO or token transfer is introduced.

Commerce config `Portales:BackofficeLoginUrl` supplies the trusted operator login destination. Local launch defaults to `http://localhost:5046/ingresar`; Compose sets `http://localhost:5101/ingresar`. Configure the deployed HTTPS Backoffice URL for other environments. No destination comes from user input; ReturnUrl remains unused and cannot redirect to an external host.

## Public home and protected workspace

The Blazor home at `/` uses `[AllowAnonymous]` and a dedicated public layout. Global Commerce authorization remains on the other component endpoints; no operator/platform account is newly admitted. The home uses only the protected cookie's existing session type to offer `/organizacion` for `SinOrganizacion` or `/envios` for `Comercio`; it makes no operational API query for anonymous visitors. Backoffice and Admin are separate configured browser links, not Commerce sessions or SSO.

| Route | Access / purpose |
| --- | --- |
| `/` | Public Blazor welcome and session-aware entry actions |
| `/registrarse`, `/ingresar` | Public existing forms, reciprocal links and return to home |
| `/organizacion` | Existing authenticated self-service flow |
| `/envios` | Protected commerce work area: existing shipment list |
| `/envios/crear` | Protected existing shipment creation component; only its route changed |
| `/usuarios`, `/roles` | Existing current-permission checks unchanged |
| `POST /salir` | Existing antiforgery-protected logout, now returns to public `/` |

`Portales:AdminLoginUrl` defaults to `http://localhost:5104/ingresar`; Compose also sets this external browser URL. `Portales:BackofficeLoginUrl` retains the local/Docker values documented above. Neither destination uses Docker service DNS names. Login still ignores untrusted ReturnUrl and uses the fixed `/organizacion` or `/envios` destination.

Local diagnosis before this change found **both** missing public navigation and stale application images: `/` was `CrearEnvio` behind global Commerce authorization, the running login had no registration link, `/registrarse` was missing in the running image (re-executing its 404 into a protected page), and the running API's OpenAPI had no registration/self-service paths. Only local `api` and `commerce` are rebuilt/recreated; PostgreSQL, its volume, other services and existing initialization settings are preserved.

## HTTP contracts

| Endpoint | Request | Result |
| --- | --- | --- |
| `POST /api/auth/register` | `{ "email": "person@example.test", "password": "..." }` | 201 `{ usuarioId, email }`; 400 invalid/extra fields; 409 duplicate email |
| `POST /api/auth/login` | Existing email/password contract | Existing 15-minute bearer-token response; now also accepts identities without membership |
| `GET /api/usuarios/actual` | Bearer token | Explicit `tipo: "SinOrganizacion"`, `accesoId`, `rolId`, `rolCodigo`, organization IDs/names and `tipoAcceso` all null; identity ID and email remain populated |
| `GET /api/usuarios/actual/permisos` | Identity-only bearer | 200 `[]` |
| `POST /api/alta-propia/comercios` | `{ "nombre": "My commerce" }` | 201 existing `AltaOrganizacion` shape: organization, original user ID, access ID and role ID |
| `POST /api/alta-propia/operadores` | `{ "nombre": "My operator" }` | Same shape for an operator |

Self-service requires authentication (401 otherwise), rejects platform accounts (403) and existing organizational memberships, including inactive/role-less ones (409). Unknown JSON members are rejected (400): registration and self-service do not accept owner IDs, roles, permissions, access types or replacement credentials. A stale identity-only token is 401 after successful creation; a currently authenticated organization token attempting a second creation is 409. Truly overlapping admitted requests race at the membership constraint: exactly one 201 and one 409.

Registration and login each retain an independent five-requests-per-minute/IP limiter (429). Error responses and rendered forms never include passwords or hashes. Registration confirmation stays in the frontend, not in API requests. Frontend handles controlled 400/401/403/409 responses, transport failures and timeouts, renders antiforgery tokens, ignores external ReturnUrl values, clears password fields on errors and uses the existing single-submit script.

## Session and authority boundaries

Identity-only JWTs have `nexoruta:ambito = identidad`, version 0 and **no** `nexoruta:acceso_id`. Validation verifies that the persisted identity exists, has credentials and has neither an organizational nor platform access (irrespective of access state). It stores only `IdentidadSinOrganizacion`, never `ContextoUsuario` or `ContextoPlataforma`. Organization/platform policies and permission handlers therefore reject this identity.

Creation does not refresh tokens implicitly: the previous JWT immediately becomes invalid once membership commits. A fresh password login issues an organizational access-bound token. Organizational/platform `VersionSesion`, active-state checks and revocation behavior remain unchanged. There is no provisional organizational role and no platform authority associated with an owner.

## Reused implementation and atomicity

- ASP.NET Core Identity's `UserManager<Usuario>` and its standard EF Core store own account creation, password hashing/verification, normalized email and email updates. The API continues issuing the existing JWT; Identity does not create global NexoRuta roles.
- Existing normalized email uniqueness (`IX_Usuarios_EmailNormalizado`) translates concurrent registration conflicts to 409.
- `EfPlataformaRepository` shares its organization initializer with the new `IAltaPropiaRepository` entry point. Administrative creation still creates an explicitly requested new identity under platform authorization; self-service reuses the authenticated identity unchanged.
- Every organization, protected role, scope permission/catalog row and active `AccesoUsuario` is created inside one PostgreSQL transaction. The unique `AccesosUsuario.UsuarioId` index remains unchanged and arbitrates same-type and mixed commerce/operator races. Losing transactions roll back all their rows; injected failures after SaveChanges also roll back.
- The new owner role (`dueno`) uses `CatalogoPermisos.Para(tipo)`, is protected through `ProtegerComoRolSistema`, and preserves existing self-access and own/protected-role guards. Existing accounts are not reclassified as owners.
- Existing internal employee/role administration and Admin are retained. An existing email, even for an unassigned person, is a conflict, never an invitation, reassignment or password replacement.
- `SesionUsuario`, API clients and protected per-application cookies are reused; JWTs stay server-side in protected authentication tickets, outside JavaScript and HTML.

## Persistence and compatibility

The current migration history includes AddIdentityUserStore and EnablePostgreSqlRls; they preserve the existing account GUIDs and establish the EF Identity store and restricted tenant policies. Normal startup keeps ApplyMigrations=false and SeedData=false. The current audit did not apply migrations, run seeders or write to persistent PostgreSQL. Regression tests use fixture-owned ephemeral PostgreSQL.

## Runnable checks

From the repository root:

```powershell
dotnet build backend/NexoRuta.sln -c Release
dotnet test backend/NexoRuta.sln -c Release --no-build
dotnet build frontend/NexoRuta.sln -c Release
dotnet test frontend/NexoRuta.sln -c Release --no-build
node frontend/scripts/check-onboarding-browser.mjs
git diff --check
git -C backend diff --check
git -C frontend diff --check
```

Run builds/tests sequentially within each solution on Windows: running another build against a currently executing test assembly can cause MSB3021/MSB3027 file-lock failures. Docker is required for integration and browser checks. The browser check needs Node 22+ and Chromium (`NEXORUTA_BROWSER` overrides the Windows Edge default), no npm packages. It starts owned ephemeral PostgreSQL and local Kestrel hosts, applies migrations only to that container, runs both complete browser journeys, and stops its processes/container. Screenshots/logs are temporary; the browser profile is removed. It is **not** WebApplicationFactory: the frontend HTTP tests use WebApplicationFactory with a fake upstream API, whereas the browser check uses real Kestrel/API/PostgreSQL.

## Fuera del alcance obligatorio documentado

La matriz vigente de CU-01 está en [CU-01](../backend/docs/cu/CU-01-comercios-usuarios.md). Recuperación de contraseña, invitaciones, planes, pagos, suscripciones, límites comerciales, vinculación automática de correos, SSO y borrado físico no se tratan como requisitos obligatorios de CU-01. Identity ya es el almacén de cuentas/credenciales y RLS ya es un límite de filas. Los JWT de identidad sin organización tienen expiración corta y se invalidan cuando se crea una membresía; las sesiones organizacionales/plataforma conservan sus reglas de revocación.

## Historical verification snapshot (2026-10-16)

Los conteos que siguen corresponden a esa entrega, no a la auditoría actual. Los resultados actuales deben leerse en la sección Verificación de backend/docs/cu/CU-01-comercios-usuarios.md.

- Backend and frontend Release builds: zero warnings and zero errors.
- Backend: 95 unit, 3 architecture and 220 PostgreSQL-isolated integration tests passed.
- Frontend: 185 tests passed, including the generated OpenAPI contract and affected HTTP flows.
- Real headless Edge: both commerce and operator journeys passed against owned ephemeral PostgreSQL and real Kestrel hosts, with fresh destination login, HttpOnly cookies, no JWT in HTML/storage/URLs, and double-submit protection exercised.
- EF pending-model-change checks and root/backend/frontend `git diff --check`: passed. No migration needed or historical migration edited.
- An intermediate attempted rebuild while the full integration suite held its DLL failed with Windows file locks; a sequential rerun passed. A registration/login limiter sharing issue found by the two-owner test was corrected with independent policies; the final suite passed.
- Independent delegated/native review was not executed under the explicit no-subagents constraint. Native read-only assessment reports high risk and requires explicit new-file selection before review; no review approval is claimed. Engram writes/mirror are unavailable because its host session is not registered.

### Public-entry follow-up verification

- New public Blazor `/` and protected `/envios/crear` route: 191 frontend tests passed; Release build has zero warnings/errors. Existing shipment component changed only its route; HTTP contracts remain unchanged.
- Real Edge at mobile width: public home → visible registration link → registration → identity-only login → home action → organization creation → fresh Commerce/Backoffice login passed against owned ephemeral PostgreSQL. Commerce work-area navigation reaches the existing shipment form.
- Local Compose: only `api` and `commerce` images rebuilt and containers recreated with `--no-deps`; every other service kept its container identity. PostgreSQL container and volume unchanged. API initialization flags remain false and platform bootstrap settings match their original configuration.
- Read-only before/after fingerprint of users, accesses, roles/grants, organizations and shipments is identical. No accounts or test shipments were created in the persistent database.
- Deployed `http://localhost:5102/`, `/registrarse` and `/ingresar` return 200. Real Edge on that deployed URL navigated home → registration → login → home without submitting forms; anonymous `/envios/crear` redirects to login once. Configured browser links point to localhost:5101 (Backoffice) and localhost:5104 (Admin), not Docker service names.
- Root/frontend/backend diff checks passed. Existing local changes and branch/HEAD identities preserved; no commits or subagents. Engram persistence remains unavailable due to unregistered host session.

### Commerce roles and permission navigation

`/roles` already implements scoped role listing/creation, rename/delete, the centralized commerce permission catalog and editable role grants. `/usuarios` already supports role selection for employees and assignment changes. These flows are reused, not rebuilt.

The missing link from `/usuarios` was caused by both administrative Razor Pages having `Layout = null`, so neither rendered the Blazor `NavMenu`. A shared `_CommerceNavigation` partial now links Inicio, Mis envíos, Crear envío, Usuarios and Roles y permisos from either direct-entry page. Administrative links use the same current-permission policies as their pages; the existing per-request permission cache avoids duplicate API permission queries. The Blazor shipment area's menu and the public home/work-area journey remain intact.

Read-only inspection of the local self-service owner confirmed the four commerce grants: `configuracion.gestionar`, `usuarios.gestionar`, `envios.crear`, `envios.consultar`. The initializer already uses `CatalogoPermisos.Para(Comercio)` and a protected role. No initialization fix, manual privilege update or reconciliation is needed for that owner. Historical roles lacking permissions must be assessed separately through an explicitly authorized administrative workflow; this slice never adds grants to existing accounts.

Real browser verification also found unrelated create-form validation messages after role-grant/employee-assignment posts. The existing shared reload methods now clear creation fields only for non-creation handlers, retaining failed-create validation and password cleanup. No API security or ownership guards changed.

Verification: frontend Release zero warnings/errors, 196 frontend tests; backend Release zero warnings/errors, 95 unit + 3 architecture + 221 isolated integration tests. New regression covers self-service owner's effective configuration permission, role CRUD/assignment, assigned-role deletion conflicts, own/protected-role refusals, foreign commerce/operator scope and operator/platform permission rejection. Real Edge desktop/mobile completes owner → roles → create/rename editable role → scope grants → users → employee creation/assignment → home on owned ephemeral PostgreSQL, including read-only Owner and absence of unrelated validation errors. Only the local Commerce application needs rebuilding/recreation. At that snapshot, organization profile editing and RLS had not yet landed. They are covered by later source changes; physical deletion is not part of the current CU-01 scope.

Local update completed: only `commerce` was rebuilt/recreated. The published Commerce assembly contains the new navigation partial. API, PostgreSQL and every other service retained their container identities; PostgreSQL mounts and the read-only business-data fingerprint were identical before/after. Migration/seeding flags and platform bootstrap configuration were preserved. `/` returns 200 and direct `/usuarios`/`/roles` keep their authentication requirement; signed-in owners can use the new links at `http://localhost:5102/usuarios` and `http://localhost:5102/roles`. No persistent account was used for test writes.
