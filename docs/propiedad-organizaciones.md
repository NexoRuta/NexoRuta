# Propiedad de organizaciones — etapa de persistencia

`AccesoUsuario.EsPropietario` se introdujo históricamente en `AccountOwnerAndShipmentOperator` (2026-10-08) como marca nullable/default-false de accesos a comercios, protegida por una restricción que impedía usarla en operadores. `NormalizeCu01Initialization` la volvió nullable y la conservó para compatibilidad/rollback; el modelo de ejecución solo la mapeaba como propiedad EF sombra, explícitamente fuera de autorización. Por eso la marca anterior no era una fuente completa ni actual para identificar todos los dueños.

La migración aditiva `EstablishOrganizationOwnership` promueve la marca a propiedad de dominio explícita, no nula, de un acceso. Las altas propia y administrativa crean el acceso dueño en la misma transacción que la organización. La pertenencia única por `AccesosUsuario.UsuarioId` se conserva; un índice parcial adicional limita a un dueño por organización. La consulta de aplicación verifica el `UsuarioId` y `AccesoId` de la sesión autenticada contra el acceso persistido, no el nombre del rol.

## Compatibilidad y datos anteriores

- Solo una marca histórica positiva y única para un comercio se conserva como dueño: es evidencia directa, acotada al comercio donde existía.
- Si un comercio tiene varias marcas históricas positivas, todas se limpian; no se elige un usuario arbitrariamente.
- Marcas nulas/falsas, organizaciones sin marca y operadores históricos quedan sin dueño registrado. No se promueven administradores por su rol, permisos o fecha de alta.
- La migración emite un `NOTICE` con los totales ambiguos y sin dueño. Para revisar los IDs concretos luego de aplicar la migración en un entorno autorizado, usar esta consulta de solo lectura:

```sql
SELECT 'Comercio' AS tipo, c."Id", c."Nombre"
FROM "Comercios" c
WHERE NOT EXISTS (
    SELECT 1 FROM "AccesosUsuario" a
    WHERE a."ComercioId" = c."Id" AND a."EsPropietario" IS TRUE
)
UNION ALL
SELECT 'Operador' AS tipo, o."Id", o."Nombre"
FROM "Operadores" o
WHERE NOT EXISTS (
    SELECT 1 FROM "AccesosUsuario" a
    WHERE a."OperadorId" = o."Id" AND a."EsPropietario" IS TRUE
)
ORDER BY 1, 2;
```

La salida requiere revisión y una decisión autorizada para cada organización; no corregirla automáticamente con roles o permisos. Esta etapa no aplica migraciones a bases persistentes.

## Etapa 2: consulta y edición del perfil

Los miembros con una sesión organizacional vigente consultan `GET /api/organizacion/actual`; el comercio u operador se deriva de `ContextoUsuario`. El dueño persistido puede renombrar con `PUT /api/organizacion/actual` y un cuerpo limitado a `nombre` y `version`. Los campos desconocidos se rechazan. El endpoint vuelve a verificar `EsPropietarioOrganizacionUseCase`; las cuentas de plataforma y las identidades sin organización no satisfacen la política de organización.

`Version` es un token de concurrencia optimista por organización. Cada cambio de nombre incrementa la versión y un token obsoleto responde `409 Conflict`; el cliente debe volver a consultar antes de reintentar. Los cambios actualizan el nombre de la organización, no sus IDs, accesos ni roles. Las consultas existentes de contexto, envíos disponibles, envíos y administración leen el nombre actual de la organización, sin reescribir envíos o snapshots históricos.

Commerce muestra el perfil en `/mi-comercio` mediante Blazor; Backoffice lo muestra en `/mi-operador` mediante Razor Pages. Si no hay dueño registrado, los miembros pueden consultar el nombre y la interfaz explica que la edición queda deshabilitada. No se atribuye propiedad automáticamente.

Las migraciones pendientes son `20261016194611_EstablishOrganizationOwnership` y `20261016202513_UpdateOrganizationNameConcurrency`. La primera conserva únicamente evidencia histórica inequívoca para comercios y deja sin dueño el resto; la segunda agrega `Version bigint NOT NULL DEFAULT 0` a `Comercios` y `Operadores`. Ninguna se ha aplicado a una base persistente durante esta implementación.

Cuando se autorice actualizar una base concreta, desde `backend` ejecutar la actualización contra la cadena de conexión explícita del destino; no habilitar el arranque automático de migraciones o seeders:

```powershell
dotnet ef database update --project src/NexoRuta.Infrastructure/NexoRuta.Infrastructure.csproj --startup-project src/NexoRuta.Api/NexoRuta.Api.csproj --configuration Release --connection "<connection string del destino autorizado>"
```

Mantener `DatabaseInitialization:ApplyMigrations=false` y `DatabaseInitialization:SeedData=false` para el arranque normal. No ejecutar este procedimiento contra una base persistente sin autorización específica para ese destino y esa operación.
