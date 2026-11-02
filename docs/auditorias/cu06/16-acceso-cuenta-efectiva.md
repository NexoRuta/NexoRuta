# CU06 — acceso de operador@nexoruta.local corregido

## Resultado backend y sesión del usuario

**La misma cuenta indicada por el usuario obtiene GET `/api/reparto/flota`200.** No se sustituyó por `cu06.operaciones.taller@example.test` ni se usaron fixtures/healthchecks como prueba de autorización.

Se autenticó `operador@nexoruta.local` contra API5000 con su contraseña local, sin publicarla. Antes de modificar datos se reprodujo403. Después de la asignación, **el mismo JWT emitido antes del cambio obtuvo200**, y `/api/usuarios/actual` mostró la autoridad operativa vigente. Tras reconstruir/reiniciar API por la corrección Mapbox, se autenticó nuevamente esa cuenta y volvió a obtener200. La cuenta autenticada sin permisos sigue obteniendo403.

La sesión abierta del usuario en su navegador **no fue controlada ni verificada**. Cerrar sesión en Backoffice y volver a entrar con la misma cuenta para renovar token/cookie e indicadores cacheados; luego comprobar Rutas y depósito. Esto es diferente de la asignación ya verificada en backend.

## Causa y cambio acotado

- Cuenta efectiva: `operador@nexoruta.local`, acceso propietario del operador `1b41be96-6f3e-42b9-99d0-f2e9b3c7c52a`.
- Tenía rol **protegido** `propietario_operador`, con los permisos ordinarios necesarios. La causa no era falta de `envios.gestionar`/`envios.consultar`, falta de protección o un JWT vencido durante la reproducción: **el código no está admitido por la regla operativa**.
- `EfPermisosUsuarioRepository.PuedeGestionarDecisionesOperativasEnvioAsync` admite administrador_operador/administrador/dueno/despachador_operador protegidos, de la misma organización, con grant vigente. No se alteró ese predicado ni la autorización del controlador.
- Se cambió exclusivamente la asociación del acceso indicado al rol canónico **`administrador_operador` ya existente en ese mismo operador**. No se añadieron permisos globales, no se quitaron restricciones ni se deshabilitó RLS. Se conservó EsPropietario y no se cambiaron contraseñas ni identificadores.

La API ordinaria de asignación impide cambiar el rol de un propietario; no se eliminó esa protección. Para la reparación administrativa local explícitamente autorizada se reutilizó **`AccesoUsuario.AsignarRol(Rol)`**, validando organización/código/protección y guardando en transacción. Se retuvo el rol previo para trazabilidad y reversibilidad, sin cambiar su código/protección/grants para otros usuarios.

Fuente y log del comando administrativo, estado previo/posterior y datos de identidad están en el directorio privado `%LOCALAPPDATA%/NexoRuta/mapbox-temporal/` de esta ejecución. [Resultado antes/después](../geocodificacion/evidencias/mapbox-temporal/account-result.json), [comprobación después del reinicio](../geocodificacion/evidencias/mapbox-temporal/account-after-restart.json). Credenciales y tokens no se exportaron.

## Alcance preservado

Sin cambio de políticas de producto, endpoints, RLS, rama, commits o remoto. B1–B5 y migraciones conservados. La selección manual Commerce sigue separada de esta corrección; Geoapify no se habilitó para reparar el403.

Revisión nativa y fallo arquitectónico previo siguen pendientes; no se fabricó aprobación. La comprobación en el navegador abierto del usuario sigue pendiente de su reingreso.

Risk: item2 (asignación administrativa local autorizada, acotada a una cuenta y organización).
