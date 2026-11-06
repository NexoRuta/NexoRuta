# Circuitos HTTP integrados con datos sintéticos

Se ejecutaron alta, cotización, recepción, planificación, despacho, entrega completa, entrega parcial, retiro, rendición y cierre en la API habitual actualizada (`http://127.0.0.1:5000`). El circuito transaccional terminó correctamente. La prueba es HTTP y persistencia real: **no demuestra interfaz nativa, funcionamiento sin conectividad, sensores físicos ni cumplimiento completo de cada CU**.

## Resultado comprobado

| Circuito separado de la aplicación Android | Resultado observado |
| --- | --- |
| Entrega normal, un bulto | `Entregado`; bulto en custodia del destinatario; una prueba de entrega. |
| Entrega parcial, dos bultos | `EntregadoParcialmente`; uno entregado y otro pendiente. El pendiente fue rendido, recibido en depósito y posteriormente seleccionado para una revisita. |
| Retiro, un bulto | `Retirado` → `RetiroEnDeposito` → `EntregadoComercio`; fotografía y firma sintéticas, recepción y entrega al comercio. |
| Jornada HTTP | Diez comandos distintos persistidos, todos `Aplicada`; secuencia final 10 y ruta `Finalizada`. |
| Reintentos | Tres comandos de entrega/retiro reenviados con el mismo ID devolvieron el mismo resultado, sin aumentar los diez comandos persistidos. |
| Evidencias | Cuatro filas cifradas: nonce de 12 bytes, tag de 16 bytes y contenido distinto del PNG plano. El UUID del primer envío fallido existe una sola vez tras reintentar. |
| Seguimiento público | Tres enlaces reales generados por el worker; consulta pública sin `bultoId` ni `operadorId`; parcial muestra 1/2. |
| Avisos por Kafka v2 | Tras preparar el topic faltante, una lectura diferida devolvió 28 avisos de los tres envíos del circuito; los tres eventos inicialmente fallidos estaban presentes por su ID exacto. |
| Flota HTTP | Cierre de jornada, retorno físico explícito, recepción del pendiente en depósito y liberación del vehículo. |

Las imágenes y la firma son fixtures PNG sintéticos válidos del repositorio. Su aceptación no acredita captura de cámara ni firma manuscrita en un dispositivo real.

## Alcance y protección del entorno

- Se crearon únicamente entidades nuevas con prefijo `AUD-20261105`: un operador, un comercio, tres usuarios, un rol de repartidor, zona/franjas, reglas versionadas, tarifas, dos vehículos, seis envíos/retiros y tres rutas sintéticas.
- Se utilizó PostgreSQL habitual. Las comprobaciones directas de base fueron exclusivamente `SELECT`; las mutaciones de negocio se hicieron por API.
- No se editaron contraseñas, operadores, configuraciones, rutas ni vehículos anteriores. No se limpiaron volúmenes, cachés ni datos de la aplicación móvil.
- Se compararon hashes por clave de **todas las filas originales de doce tablas**: Operadores (4), Comercios (1), Usuarios (14), AccesosUsuario (12), HojasRuta (10), OcupacionesRuta (6), ParadasRuta (10), Vehiculos (3), Envios (45), ReglasOperativasOperador (3), TarifariosOperador (2) y ZonasCobertura (6). **Ninguna fila original cambió**. Las filas sintéticas nuevas se contabilizaron aparte.
- Esta comprobación incluye las filas originales de las rutas y recursos protegidos; no se basa solo en sus nombres visibles. No es una afirmación sobre todas las tablas operativas del sistema, que pueden cambiar por workers.
- Se usaron direcciones de correo `@example.test`, Mailpit y coordenadas explícitas de Uruguay. No se invocaron búsquedas/propuestas geográficas ni estimaciones viales. Los indicadores de llamadas reales Geoapify estaban deshabilitados. No se deshabilitó Mapbox ni se consumió su API.
- Credenciales y tokens propios se conservaron solo en `.local/auditoria-excel-20261105/audit-private.json`, ignorado por Git. Este informe no contiene sus valores.

## Rechazos y concurrencia observados

| Solicitud o situación | Resultado | Comprobación adicional |
| --- | --- | --- |
| Alta de envío con peso cero | 400 | Hash de envíos del operador sin cambios tras la batería de rechazos. |
| Repartidor sin permiso intenta configurar reparto | 403 | No modifica configuración. |
| Repartidor sin permiso consulta lista administrativa de envíos | 403 | No se entrega la lista. |
| Consulta de envíos sin autenticación | 401 | Sin contenido administrativo. |
| Repetir despacho con versión obsoleta | 409 | Sin nuevo despacho ni cambio de envíos. |
| Dos actualizaciones simultáneas de un vehículo propio con la misma versión | 200 + 409 | Solo una actualización aceptada. |
| Dos planificaciones simultáneas del mismo envío parcial pendiente | 200 + 409 | Solo una ruta aceptada; incluye únicamente el bulto pendiente. |
| Otro comercio consulta tarifa y enlace de seguimiento del envío sintético | 404 + 404 | No expone datos del comercio auditado. |
| Retiro con franja que ya no era futura | 400 | Se corrigió la entrada sintética a `ahora + 1 minuto`; el alta válida fue 201. |
| Liberar vehículo con bulto pendiente de recepción física | 409 | Tras recibir el pendiente por el circuito correcto, liberación 200. |
| Cancelar ruta con parada activa | 409 | No se canceló el envío para eludir la protección; se conserva la revisita planificada. |
| Múltiples inicios de sesión en la misma ventana | 429 | Se esperó la ventana y se reutilizaron tokens propios; no se alteró el limitador. |

Los rechazos anteriores son comportamiento esperado; no se clasifican como defectos de producto.

## Incidencias de preparación y reproducción

### Evidencias: configuración obligatoria inicialmente ausente, resuelta

1. Precondición: jornada HTTP iniciada, tres bultos cargados y carga confirmada; la regla publicada exige fotografía y nombre.
2. `PUT /api/mobile/jornadas/01a1ad04-7dd7-7965-afe0-cf8598600800/evidencias/f2b641b8-3d2c-42ab-8a32-659afbf14e1f` con PNG válido y contexto propio devolvió **503**, en lugar de 204. Mensaje: `El almacenamiento de evidencias no está disponible.` Trace: `99184556d994e199f8c98a40f2dbdc37`.
3. La API no tenía `Reparto:EvidenciasEncryptionKey`. `backend/src/NexoRuta.Infrastructure/Reparto/EfOperacionesRepartoRepository.Evidencias.cs:31–33` exige una clave de despliegue base64 de 32 bytes y rechaza guardar imágenes sin protección.
4. El responsable de preparación verificó cero evidencias previas y ausencia de una clave existente; provisionó **la primera clave dedicada** en configuración privada ignorada y recreó solo la API. No sustituyó la clave de seguimiento ni rotó una clave con datos existentes.
5. Se repitieron **el mismo UUID y los mismos bytes**, con resultado **204**. La base confirmó una sola fila para ese UUID. No se reiniciaron ni inventaron nuevos comandos para las cinco operaciones móviles ya aplicadas.

La causa observada fue una carencia de configuración operativa, no un fallo del validador PNG. No se modificó código del producto ni se eliminaron pruebas obligatorias.

### Avisos de comercio: falta de topic v2

Las dos consultas iniciales a `/api/avisos-comercio` devolvieron `[]`. La lectura de outbox mostró `GenerarSeguimiento` de RabbitMQ y `EnvioCreado` v1 publicados, pero eventos v2 `BultoActualizado`/`OperacionActualizada` pendientes o en error `Kafka:Local_UnknownTopic`.

Tres eventos sintéticos fallidos quedaron identificados en `http-evidence.json` (`initialKafkaErrors`). El worker Kafka estaba ejecutándose y registraba el mismo error; por tanto, **no se dedujo que todo Kafka estuviera caído** ni que bastara la existencia del contenedor para acreditar entrega.

El responsable de preparación creó exclusivamente el topic nuevo declarado `nexoruta.comercios.v2`, conservando topics y datos anteriores, sin reinicios, borrados, cambios de offsets ni publicación manual. La **única lectura diferida devolvió 200**, con 39 avisos del tenant sintético: **28 corresponden a los tres envíos HTTP ejecutados**. Incluye los tres IDs de evento inicialmente fallidos. La lectura SQL diferida muestra 15 eventos `BultoActualizado` y 13 `OperacionActualizada` v2 publicados, sin último error; los mensajes inicialmente fallidos se publicaron por reintento natural, en el intento 23. Se conservan ambas fotografías de estado en `initialKafkaErrors`, `delayedCommerceNotices` y `delayedOutbox`.

Esta carencia operativa quedó **resuelta para el circuito**. No demuestra firma, reintentos, fallidos y reenvío de un webhook HTTP externo, ni replay/múltiples consumidores completos del opcional Kafka.

### Errores del auditor, no del producto

Se corrigieron una guardia inicial excesiva sobre Mapbox habilitado, la precedencia de una concatenación SQL de lectura, la expectativa inicial 200 en una creación de borrador que correctamente devuelve 201 y la lectura UTF-8 del auditor. Los intentos se conservan separados en `attemptHistory` y `harnessNotes`. Los textos descriptivos sintéticos se normalizaron para lectura; IDs, números, métodos, rutas, estados y PNG/base64 ASCII permanecen iguales. La versión previa sin normalizar queda solo en el directorio privado. No se afirma identidad de bytes para descripciones no ASCII.

## Identificadores para continuidad

| Entidad | ID / estado |
| --- | --- |
| Operador sintético | `01a1ad00-8173-726a-b017-814e54c6fe59` |
| Comercio sintético | `01a1ad00-855e-75bc-a2b7-38800579379e` |
| Ruta preparada, **no ejecutada** por Android | `01a1ad02-7fe9-71e6-8007-c637e5b86d2a` — `Despachada`, secuencia 0 |
| Jornada preparada para continuidad | `01a1ad02-7fe9-7c75-b343-4e1f703188a4` |
| Repartidor de esa ruta | `01a1ad01-3348-7fc3-92bf-5b6d450a45db` — credenciales privadas `accounts.courier` |
| Entrega normal preparada: dos bultos | `01a1ad02-46ec-76ac-ab70-31a7777c2957` |
| Entrega parcial preparada: tres bultos | `01a1ad02-5309-7ed3-8c55-a20c9dd9537b` |
| Retiro preparado: un bulto | `01a1ad02-7d0e-72b6-9461-ef2e0618e39c` |
| Ruta HTTP **ejecutada y cerrada** | `01a1ad04-7dd7-718e-a8b8-974471c6afa9` — `Finalizada`, secuencia 10 |
| Jornada HTTP | `01a1ad04-7dd7-7965-afe0-cf8598600800` |
| Entrega normal HTTP | `01a1ad04-71da-76d1-99b5-fb54f9a0ea77` |
| Entrega parcial HTTP | `01a1ad04-7653-78aa-b058-74ffb8244f78` |
| Retiro HTTP | `01a1ad04-7c64-7166-8dec-bb8225768201` |
| Revisita sintética retenida de la carrera | `01a1ad0a-cdf7-738f-afca-8b62c660630b` — `Planificada`, sin despacho |

**No cambiar la identidad de la aplicación móvil ni borrar su almacenamiento para usar estos fixtures.** La aplicación conserva información de la identidad anterior y puede impedir un cambio mientras exista trabajo/cache local. La continuación nativa requiere verificar una transición segura que preserve esos datos, o una alternativa autorizada por el usuario. La auditoría HTTP no tocó la identidad ni el almacenamiento móvil.

## Relación con el Excel y límites de la prueba

| Ejes | Evidencia aportada aquí | Lo que no se acredita solo con esta prueba |
| --- | --- | --- |
| CU01–CU04, CU06 | Alta aislada, usuario/rol, zona/franjas, publicación de reglas y tarifas, repartidor y vehículo. | Todo el ABM, diseño de interfaz, historial visual y todas las variantes de permisos/configuración. |
| CU07–CU12 | Alta individual, bultos, cotización/cargo, recepción escaneada, estados y eventos persistidos. | Importación masiva/parcial idempotente completa, todas las transiciones, inmutabilidad exhaustiva. |
| CU13–CU19 | Ruta mixta, despacho, doble asignación rechazada, descarga HTTP y carga por bulto. | Optimización/criterio de orden documentado, todas las restricciones límite, navegación y escáner físicos. |
| CU20, CU22, CU24 | Protocolo móvil HTTP, evidencia cifrada, rendición, cierre y reintentos exactamente una vez. | Operación sin red, cola SQLite/cifrado móvil, cámara/firma/geolocalización reales y resolución completa de conflictos offline. |
| CU25 | Seguimiento público real y avance parcial sin IDs internos. | Exhaustividad de privacidad, reprogramación y comunicaciones multicanal. |
| CU28 / OPT03 | Outbox v2, diagnóstico de topic y lectura diferida de avisos. | Webhook HTTP saliente con firma/reintentos/fallidos/reenvío; múltiples consumidores y replay completos de Kafka. |
| Cambios 31–41 | Derivación parcial observada, motivo por bulto, una revisita con solo pendiente, retiro y ruta mixta. | Toda política alternativa, recargo de revisita efectivamente despachada, demostración offline y ADR requerido. |

No se otorgan “CU completos” por un endpoint 200 ni puntos opcionales por selección o presencia de un proceso. El resto de los ejes requiere las pruebas de interfaz, automatización, arquitectura y operación detalladas en la matriz principal.

## Evidencia y comandos

- `http-evidence.json`: solicitudes/respuestas saneadas, estados, resultados de concurrencia, conteos SQL, preservación, incidencias iniciales y lectura diferida. Las geometrías grandes de respuesta se resumen por tamaño/hash; no se alteraron las solicitudes materiales de reproducción.
- Script local ignorado: `python .local/auditoria-excel-20261105/http-circuit.py`. Se ejecutaron los modos `setup`, `configure`, `route`, `http-fixture`, `reject`, `execute`, `verify-business`, `isolation-assignment` y `preservation`. Los modos de preparación **mutan solo fixtures propios**; no son un comando genérico para ejecutar en otro entorno.
- Compilación: únicamente comprobación sintáctica del script de auditoría; builds de producto se informan por separado.
- HTTP: circuito y rechazos ejecutados en API habitual.
- Automatización: Python/HTTP más consultas SQL de solo lectura; no automatización de navegador ni Android.
- Revisión visual: **no ejecutada en esta unidad**. No se usó CUA ni se sustituyó la aplicación por un prototipo.

Risk: none — no se modificó código del producto; las mutaciones de negocio se limitaron a entidades sintéticas nuevas y se verificó preservación de todas las filas originales de las doce tablas controladas.
