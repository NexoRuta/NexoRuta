# RLS en NexoRuta

RLS (*Row-Level Security*) es un filtro que PostgreSQL aplica a cada fila de una tabla. No reemplaza los permisos de NexoRuta: la API sigue validando roles, permisos, propiedad y estado de la organización; PostgreSQL agrega una segunda barrera para que una consulta que olvide un filtro no lea filas ajenas.

## ¿Quién soy?

El JWT autentica una sesión, pero PostgreSQL no lo lee ni lo interpreta. ASP.NET valida firma, emisor, audiencia y vencimiento; después la API vuelve a consultar el acceso persistido indicado por la sesión y comprueba usuario, organización, estado y versión de sesión. El identificador de organización que llega desde el cliente no es la fuente del contexto RLS.

## ¿Cómo llega ese dato a PostgreSQL?

Para una petición autenticada, `RlsTransactionMiddleware` abre una transacción, revalida el acceso persistido y entrega el actor verificado a `RlsTransaction.ApplyAsync`. Este escribe los datos del actor en variables `nexoruta.*` con `set_config(..., true)`: son locales a esa transacción, que comparte conexión con EF Core. La consulta del endpoint se ejecuta después, dentro de la misma transacción. Una respuesta de error o una excepción revierte; una respuesta exitosa confirma. Al cerrar la transacción, PostgreSQL descarta su contexto local.

Login, registro anónimo y seguimiento público tienen recorridos separados y acotados: no necesitan fingir que son una sesión de organización ya autenticada. Usan tablas globales de Identity o funciones SQL específicas con permisos mínimos.

## ¿Cómo decide PostgreSQL qué filas mostrar?

Cada consulta pasa por la ACL normal del rol y por las políticas RLS. `USING` determina qué filas existentes puede ver o modificar el comando; `WITH CHECK` valida las filas nuevas o los valores que dejaría un `INSERT`/`UPDATE`. Sin una política que coincida, RLS deniega las filas. Tener una política tampoco concede el privilegio SQL necesario: deben coincidir ambas capas.

**Ejemplo:** el comercio `C-1` crea un envío y elige al operador `O-7` para ese envío. `C-1` puede consultar ese envío por `ComercioId`; `O-7` también puede consultarlo por `OperadorId`. Si otro envío del mismo comercio se asignó a `O-9`, `O-7` no lo ve. No existe una membresía permanente comercio–operador: el vínculo se obtiene del propio envío y sus hijos (destinatario, dirección y bultos) siguen ese mismo vínculo. La plataforma puede gestionar organizaciones, pero no recibe una lectura general de envíos ni de sus datos personales.

## Diagramas existentes

Se enlazan los archivos existentes en su ubicación original; no se copian ni se recrean.

- [Esquema RLS A](../alcance/rls/image.png) · [Esquema RLS B](../alcance/rls/image%20copy.png)
- [Arquitectura lógica](../alcance/Diagramas/Diagrama-Arquitectura-Logica.png) · [Despliegue](../alcance/Diagramas/Diagrama-Desplegue.png) · [Dominio](../alcance/Diagramas/Diagrama-Dominio.png)
- [Flujo de colas](../../backend/docs/workflow/colas.png)

## Cómo agregar una tabla nueva

1. Agregá la entidad y su mapping EF Core; identificá qué organización posee cada fila o cuál es la fila padre que determina su alcance.
2. Agregá una **migración nueva** (no edites una migración ya aplicada), asigná la tabla al dueño restringido `nexoruta_schema_owner` y empezá con `REVOKE`; concedé a API, workers o bootstrap solo los privilegios necesarios.
3. Habilitá **ambas** opciones: `ENABLE ROW LEVEL SECURITY` y `FORCE ROW LEVEL SECURITY`.
4. Escribí políticas explícitas por operación: `USING` para filas existentes y `WITH CHECK` para inserciones y filas resultantes de actualizaciones. No tomes una política por equivalente a un `GRANT`.
5. Probá en PostgreSQL efímero con los mismos roles restringidos de runtime: sin contexto, tenant propio y ajeno, y cada operación permitida y denegada. Incluí la tabla en la prueba de catálogo de RLS y revisá el SQL generado.

Reutilizá el actor existente si la tabla se aísla por el mismo comercio, operador, plataforma, identidad, bootstrap o trabajo ya validado. Extendé `RlsActorContext` y su contrato cerrado solo si la operación necesita un dato de actor nuevo; obtenelo de un acceso persistido o del registro durable del worker, nunca de un ID de organización enviado por el cliente. Si hace falta una función `SECURITY DEFINER`, limitá su propósito y salida, usá `search_path` fijo, dueño sin login ni `BYPASSRLS`, revocá `EXECUTE` a `PUBLIC` y añadí una prueba con el rol restringido.

Para el inventario, los recorridos y los límites comprobados, ver [Auditoría de RLS](AUDITORIA.md).
