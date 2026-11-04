# CU-07 — diseño técnico y plan de cierre por importación idempotente

**Estado vigente:** las decisiones de proyecto descritas aquí se implementaron por bloques en backend (`08-backend-importacion.md`) y en ApiClient/Commerce con verificación Kestrel/navegador (`09-commerce-importacion-y-verificacion.md`). No son requisitos literales del PDF. Los estados pendientes de los cortes anteriores de este documento quedan sustituidos por 09; la auditoría integral de requisitos transversales aún conserva brechas.

**Alcance:** documento de diseño base para extender el alta individual; las afirmaciones de estado en sus secciones históricas 14–15 se actualizaron para enlazar los cortes posteriores 08 y 09.
**Base:** decisiones indicadas por el usuario, auditoría de 04 y 05, y componentes actuales citados abajo.

Fuentes de trabajo: `docs/auditorias/cu07/01-requisitos-y-trazabilidad.md`, `02-hallazgos.md`, `03-plan-de-cierre.md`, `04-diseno-de-implementacion.md` y `05-verificacion-flujo-existente.md`; fuentes primarias `docs/alcance/Laboratorio__NET_2026.pdf` y `docs/alcance/Calcs/Casos de Uso - Responsables.xlsm`; implementación de alta, transacción, persistencia, contratos y Commerce citada en §3. Las decisiones de §2.2 proceden de la instrucción de trabajo actual, no se atribuyen a esos documentos originales.

## 1. Conclusión ejecutiva

CU-07 se cerraría agregando una importación CSV síncrona y atómica que comparta la creación de envío actual, su transacción RLS y sus dos mensajes outbox. La identidad de reimportación sería una referencia externa del comercio, almacenada en una tabla privada separada del envío, con una restricción única por comercio y una huella versionada de los datos originales. La huella sirve para comparar equivalencia; nunca sustituye la referencia como identidad.

El POST /api/envios individual permanece intacto. Las referencias se aplican solo a envíos creados por importación: no se alteran registros previos ni se agregan campos al contrato individual. No se propone procesamiento parcial, actualización implícita, varios bultos, broker/evento/job nuevo ni trabajo offline del navegador.

## 2. Alcance y clasificación de decisiones

### 2.1 Requisitos de la letra y límites funcionales

La matriz de 01-requisitos-y-trazabilidad.md y las fuentes primarias definen el alcance CU-07. Este documento no vuelve a atribuirle detalles de formato o idempotencia que esas fuentes no prescriban. El archivo, la referencia, las respuestas HTTP y las reglas de conflicto que siguen son **decisiones de proyecto propuestas en esta etapa**, no citas ni requisitos literales del PDF/taller.

Se mantienen como límites: un envío con un bulto, el alta individual existente, el operador seleccionado para el envío y los eventos/outbox actuales. CU-08 sigue siendo separado y obligatorio en su propio alcance; no se adelanta aquí.

### 2.2 Decisiones propuestas para el trabajo y adoptadas en la implementación

| Tema | Decisión propuesta |
|---|---|
| Archivo | CSV UTF-8 estricto, BOM opcional, coma, campos entrecomillados estándar y comillas internas escapadas como `""`. |
| Entrada | Una plantilla estática descargable y ayuda explícita sobre columnas, unidades y decimales. |
| Identidad | referenciaExterna estable proporcionada por el comercio, única dentro del comercio, independientemente del operador. |
| Operador | Un operadorId elegido para el archivo completo; no se toma del CSV. |
| Atomicidad | Un error de validación/admisión o conflicto de identidad impide confirmar todos los envíos nuevos del archivo. No hay procesamiento parcial. |
| Repetición | Mismo comercio + referencia + datos normalizados + operador: «ya existente», sin mutación ni nuevos eventos. Diferencias de datos u operador: conflicto, sin actualización. |
| Reimportación | El lote completo o cualquier subconjunto se puede repetir sin duplicar envíos. |
| Duplicados internos | Filas con la misma referencia y payload equivalente se coalescen en una creación y se correlacionan a su fila canónica. Payload diferente: conflicto de archivo. |
| Cobertura inicial | Solo importaciones con referencia. No se deduplican retrospectivamente altas individuales/API sin referencia. |
| Límites | 5 MiB y 500 filas de datos como límites iniciales propuestos; se conservan sujetos a prueba aislada de duración/locks antes de habilitar. |

### 2.3 Decisiones técnicas reversibles incluidas en este diseño

Son propuestas para que la implementación tenga un contrato preciso: encabezados exactos, límite de referencia de 128 caracteres, comparación de referencia ordinal sensible a mayúsculas, tabla de identidad privada, huella SHA-256 versionada, nombres sugeridos de DTOs/funciones, ruta y estados HTTP. Se pueden ajustar antes de migrar, pero cualquier ajuste debe conservar unicidad, idempotencia, aislamiento y atomicidad. No deben documentarse como texto oficial del caso de uso.

## 3. Componentes reales y cambios propuestos

Los nombres bajo «existente» corresponden al código observado; los nombres bajo «propuesto» son nuevos salvo que se indique «modificar». La tabla describia el diseno inicial; el estado real del backend al 24/10/2026 se registra en la seccion 15.

| Capa | Existente y reutilizable | Propuesto para implementación |
|---|---|---|
| API | backend/src/NexoRuta.Api/Features/Envios/Controllers/EnviosController.cs, acción CreateShipment; request backend/src/NexoRuta.Api/Features/Envios/Contracts/Requests/CrearEnvioRequest.cs. | Agregar acción ImportarAsync al controlador, ruta POST api/envios/importaciones, contrato multipart ImportarEnviosRequest. No modificar el contrato individual. |
| Aplicación | backend/src/NexoRuta.Application/Envios/UseCases/CrearEnvioUseCase.cs, CrearEnvioCommand, IEnviosRepository, IUsuarioActual e IOperadoresRepository. | Agregar ImportarEnviosUseCase y resultado de importación. Extraer/reutilizar dentro del flujo de creación la construcción de Destinatario, Direccion, Envio y un Bulto; no copiar reglas ni hacer un segundo alta paralela. |
| Persistencia | backend/src/NexoRuta.Infrastructure/Envios/Repositories/EfEnviosRepository.cs, NexoRutaDbContext.BeginOrJoinAsync, función nexoruta_app.create_shipment(...); RlsSqlFunctionContract. | Agregar GuardarLoteAsync a IEnviosRepository y su implementación. Añadir migración privada de identidad, índices, políticas y funciones SQL acotadas; registrar esas firmas en RlsSqlFunctionContract. |
| Transacción/seguridad | backend/src/NexoRuta.Api/Core/Security/RlsTransactionMiddleware.cs establece contexto transaccional por solicitud; la creación participa con BeginOrJoinAsync. | Mantener middleware, rol API, contexto Commerce y límite de SECURITY DEFINER. La implementación debe comprobar READ COMMITTED para la estrategia de bloqueo/lectura descrita en §6. |
| Eventos | OutboxMessage.ForShipment(...); OutboxMessageTypes.GenerarSeguimiento y OutboxMessageTypes.EnvioCreado; consumidores/publicadores existentes del Worker. | Para cada nuevo envío canónico, ejecutar exactamente los mismos dos ForShipment. No generar outbox para existentes ni duplicados internos. No crear evento de importación. |
| Cliente HTTP | frontend/src/NexoRuta.ApiClient/Features/Envios/Clients/EnviosApiClient.cs; IdentidadVisualApiClient es patrón existente de multipart. | Agregar ImportarAsync con MultipartFormDataContent, stream fresco por intento, bearer token y cancelación. Agregar DTOs de solicitud/respuesta en contratos de Envios. |
| Commerce | frontend/src/NexoRuta.Commerce/Components/Features/Envios/Pages/CrearEnvio.razor; ShipmentsCreatePolicy; registro tipado en Program.cs; operadores cargados por OperadoresApiClient. | Nueva página Components/Features/Envios/Pages/ImportarEnvios.razor, permiso existente, enlace discreto desde alta y plantilla bajo wwwroot/plantillas/alta-envios.csv. Aplicar frontend/DESIGN.md al implementar y verificar en navegador. |

### Responsabilidades

- **Endpoint/contratos:** autorizar exactamente el actor Comercio con permiso envios.crear, recibir solo archivo y operador, aplicar límites HTTP, traducir resultados de aplicación a HTTP. No recibir ComercioId ni confiar en un comercio enviado por el cliente.
- **Parser:** decodificar UTF-8 estrictamente, reconocer encabezados/formato y crear registros con número lógico de fila. No tocar persistencia ni cambiar decisiones de negocio.
- **Caso de uso:** validar el archivo completo, agrupar referencias internas, adquirir identidad de comercio del contexto autenticado, clasificar existentes/conflictos, validar admisión solo para nuevas filas y coordinar el único lote.
- **Reglas compartidas:** el builder usado por alta individual e importación crea los mismos objetos de dominio y un único Bulto; la ruta individual continúa usando el mismo comportamiento que hoy.
- **Persistencia:** usar la transacción middleware; llamar el SQL actual de admisión/creación; guardar la identidad externa solo para filas nuevas; escribir eventos outbox actuales dentro de la misma frontera.
- **RLS/SQL:** las funciones nuevas son estrechas y explícitas; no ampliar grants de escritura directa del rol API. ComercioId se deriva del GUC autenticado, no del multipart.
- **Commerce:** seleccionar archivo y operador; explicar plantilla/unidades; mostrar estados HTTP y estado por registro; impedir doble submit mientras una petición está en vuelo.

## 4. Formato CSV propuesto

### Encabezados y mapeo

Encabezado obligatorio, en este orden y con estos nombres exactos:

~~~csv
referenciaExterna,nombreDestinatario,emailDestinatario,direccion,codigoBulto,pesoGramos,largoCentimetros,anchoCentimetros,altoCentimetros
~~~

operadorId es un campo multipart único de archivo, no una columna. Cada fila representa exactamente un envío y un bulto, compatible con CrearEnvioRequest. No se agregan múltiples bultos ni campos de CU-08.

| Campo | Regla de formato/unidad propuesta |
|---|---|
| referenciaExterna | Obligatorio; trim de extremos, Unicode NFC, 1–128 caracteres, sin controles; igualdad ordinal sensible a mayúsculas. Se conserva el valor normalizado. |
| nombreDestinatario | Obligatorio, hasta el límite actual (160); validar con reglas del dominio. |
| emailDestinatario | Obligatorio, hasta 254; validación actual del dominio (MailAddress.TryCreate); no cambiar mayúsculas/minúsculas, trim de extremos. |
| direccion | Obligatoria, límite actual 240; trim como dominio. |
| codigoBulto | Obligatorio, límite actual 80; trim como dominio. |
| pesoGramos | Decimal positivo en gramos; valor y rango compatibles con CrearEnvioRequest. |
| largoCentimetros, anchoCentimetros, altoCentimetros | Decimales positivos en centímetros; compatibles con los rangos del alta individual. |

Números usan punto decimal (p. ej. 1200.50), cultura invariante, sin separador de miles ni notación exponencial. La escala almacenada actual debe verificarse en la migración/modelo: si PostgreSQL redondea a numeric(12,2), la huella debe registrar el valor decimal original normalizado de la solicitud, no releerlo de columnas redondeadas. No cambiar silenciosamente los rangos del alta individual; probar valores con más de dos decimales y documentar el resultado del tipo SQL actual.

Parser: usar primero una dependencia ya instalada si ofrece el comportamiento requerido; la inspección actual no encontró CsvHelper ni otro paquete CSV declarado. La opción sin dependencia nueva es Microsoft.VisualBasic.FileIO.TextFieldParser del runtime .NET, configurado UTF-8, delimitador coma y comillas; verificar con pruebas sus errores de comillas, BOM y saltos dentro de campos antes de elegirlo. No usar Split(','). Aceptar CRLF y LF; admitir comas y saltos de línea dentro de campos entrecomillados y "" escapado. Rechazar columnas adicionales, ausentes, duplicadas o encabezados distintos. Ignorar registros completamente vacíos; no contar esos registros para el límite. El número correlacionado es el ordinal lógico de registro de datos (encabezado no incluido), aunque un campo contenga saltos físicos.

Plantilla de ejemplo:

~~~csv
referenciaExterna,nombreDestinatario,emailDestinatario,direccion,codigoBulto,pesoGramos,largoCentimetros,anchoCentimetros,altoCentimetros
PED-2026-0001,María Pérez,maria@example.test,"18 de Julio, 1234 apto 2",BX-001,1200.50,30.00,20.00,10.00
~~~

Validar bytes/tamaño antes de parsear; contar máximo 500 filas de datos no vacías. Rechazar UTF-8 malformado en vez de reemplazar caracteres. No asumir accept=".csv" como validación de seguridad.

## 5. Identidad, equivalencia y operador

### Identidad externa

Identidad: (Comercio autenticado, referenciaExterna normalizada). El operador no forma parte de la clave única, pero sí del contenido equivalente. Dos comercios pueden usar la misma referencia. El límite de 128, trim, NFC y sensibilidad a mayúsculas son convenciones técnicas propuestas; deben reflejarse igual en parser, canonicalizador, collation y pruebas.

### Huella versionada de la solicitud original

Comparar las filas con datos de **admisión originales**, no el estado actual mutable del envío. Propuesta: almacenar VersionHuella y SHA-256 de una codificación canónica determinista: dominio/version NexoRuta/EnvioImport/V1 con terminador NUL; campos en orden fijo con longitudes UTF-8 big-endian; UUIDs en formato D minúscula; decimales con G29 y cultura invariante. Incluir ComercioId, OperadorId, nombre/email/dirección/código de bulto y las cuatro medidas normalizadas. La referencia es la clave por separado y no se usa como hash de contenido. No devolver la huella al cliente.

La normalización de esos campos se limita a la del dominio actual (trim de textos y validación actual; conservar caja y secuencia Unicode para nombre/email/dirección/código) más canonicalización numérica. No convertir email a minúsculas ni actualizar datos existentes. El digest versionado conserva una representación suficiente para equivalencia sin copiar otra vez los datos personales. La implementación debe conservar el comparador v1 mientras existan registros v1; una versión desconocida no se considera equivalente: respuesta segura de conflicto no actualizable, con diagnóstico interno. Cambiar formato/semántica exige nuevo comparador/migración explícita, no recomputar a partir del envío mutable.

No incluir EnvioId, fecha de creación, estado, versión de reglas, seguimiento, coordenadas, confirmación de destino ni otros campos internos posteriores al alta. Por tanto, el mismo archivo sigue siendo «ya existente» después de cambios de estado, publicación de nuevas reglas, eventos de seguimiento o edición posterior de dirección/coordenadas. La prueba compara contra la huella original almacenada, nunca contra columnas mutables del envío.

### Persistencia propuesta

Tabla nueva sugerida IdentidadesEnvioImportado (nombre sujeto a convención de migración), vacía al instalar y con una fila solo por envío importado:

- ComercioId, ReferenciaExterna (normalizada, collation C), EnvioId, OperadorId.
- VersionHuella pequeña y Huella de 32 bytes.
- PK/unique (ComercioId, ReferenciaExterna); unique adicional (ComercioId, EnvioId) para impedir dos referencias por envío salvo que el producto decida lo contrario antes de migrar.
- FK compuesta al envío por comercio y, si el esquema lo permite, operador (verificar claves compuestas existentes; agregar clave única solo si hace falta y es compatible).
- Sin backfill de envíos existentes: no tienen identidad del importador y no se puede inferir una referencia sin inventarla.

La tabla contiene metadatos privados de deduplicación, no sustituye Envios. Habilitar y forzar RLS; políticas para rol de función limitadas al Commerce del contexto. nexoruta_api no recibe grants directos de lectura/escritura sobre la tabla. La migración no debe modificar rows de negocio ni reescribir el contrato individual.

### Autorización versus admisión

Cada solicitud autentica y revalida el Commerce desde identidad/acceso persistido, y el middleware fija el contexto transaccional. El request solo propone operadorId; el backend valida que exista y que corresponde a una operación permitida. Sin membresía permanente Comercio–Operador: la selección sigue siendo por envío, según ADR.

La consulta de identidad existente se limita al Commerce autenticado por RLS. Para una referencia existente, si el OperadorId y la huella coinciden, se devuelve «ya existente» **sin exigir que el operador siga activo ni que las reglas sigan siendo las mismas**: no se admite ni modifica un envío nuevo. La autenticación del Commerce sigue siendo obligatoria. Para una nueva referencia sí se aplican las verificaciones actuales de operador activo y versión publicada de reglas. Si el operador inactivo es seleccionado y hay cualquier fila nueva, el archivo se rechaza entero.

**Corte de diseño previo a implementación, resuelto en 09:** la pantalla conserva el operador elegido y el backend agrega un catálogo mínimo limitado al Commerce autenticado con activos e históricos de sus importaciones; solo retorna ID/nombre/estado, requiere `envios.crear` y no concede `envios.consultar`. La prueba de autorización/aislamiento se describe en 09. El texto de esta sección que proponía revisar `GET /api/envios` ya no es una tarea pendiente.

## 6. Transacción, RLS y carreras

### Una sola frontera para el archivo

1. RlsTransactionMiddleware abre la transacción/contexto autenticado para la solicitud; ImportarEnviosUseCase y EfEnviosRepository participan mediante un solo BeginOrJoinAsync del lote.
2. Validar tamaño, CSV, columnas, referencia, payload y duplicados internos antes de crear datos de negocio.
3. Tomar bloqueos de referencia; consultar identidades existentes con el Commerce del contexto.
4. Resolver conflictos/existentes y admitir solo las referencias nuevas. Si hay error/conflicto, responder 4xx sin inserts; el middleware revierte igualmente.
5. Para cada fila nueva canónica: setear contexto de envío actual, ejecutar nexoruta_app.create_shipment(...), asociar identidad externa y crear los dos OutboxMessage actuales. Ejecutar SaveChangesAsync por fila mientras el GUC/contexto RLS apunta a ese envío. El commit real lo hace el middleware una vez al final.
6. Solo devolver el resultado con filas Creado después de que toda la acción haya finalizado correctamente. Una excepción/cancelación/constraint inesperada después de crear una fila debe subir al middleware; no convertirla en una respuesta parcial. El middleware revierte todo y descarta cualquier respuesta exitosa bufferizada. Error de commit produce 5xx sin afirmar creaciones.

No llamar a un commit independiente por fila. Si el lease de BeginOrJoinAsync ofrece CommitAsync, en el contexto ya abierto debe ser no-op conforme al patrón existente; confirmarlo en prueba. Los errores conocidos de validación/conflicto ocurren antes del primer insert, por lo que pueden mapearse a 422/409 sin escrituras. La cancelación aborta el lote y se traduce por la infraestructura habitual.

### RLS y funciones acotadas

Las nuevas funciones SECURITY DEFINER (nombres propuestos: nexoruta_app.lock_import_references(text[]), nexoruta_app.find_import_references(text[]), nexoruta_app.bind_import_identity(...)) deben:

- Tener propietario dedicado existente de funciones, search_path fijo (pg_catalog y esquema necesario explícito), EXECUTE revocado a PUBLIC y concedido solo al rol autorizado.
- Validar expresamente actor_kind='comercio', org_id no nulo y coincidencia del contexto de envío/comercio/operador al asociar identidad.
- Derivar el Commerce de nexoruta_app.setting/ctx_uuid('org_id'), no de un UUID multipart/parámetro confiado.
- Ejecutar las consultas bajo FORCE ROW LEVEL SECURITY y políticas de tabla limitadas al Commerce actual. El rol API no recibe DML directo ni BYPASSRLS.
- Exponer al caso de uso solo los campos necesarios para comparar (ref, envío, operador, versión de huella y digest), no conceder acceso general a la tabla.

find_import_references debe filtrar Commerce incluso si se invoca con referencias ajenas. bind_import_identity se llama solo tras el create_shipment actual y valida que el envío pertenezca al Commerce/operador y sea el contexto actual. Integrar las firmas exactas al contrato de allowlist RlsSqlFunctionContract y sumar pruebas de privilegios/ejecución y RLS.

### Unicidad concurrente y deadlocks

La restricción única (ComercioId, ReferenciaExterna) es la garantía final; una consulta previa sola no sirve. Todas las importaciones adquieren `pg_advisory_xact_lock` por (Commerce, referencia) antes de consultar y crear. La función deduce Commerce del contexto; la migración correctiva `20261025005447_OrderImportLocksByEffectiveKey` deriva, deduplica y ordena numéricamente las claves `bigint` efectivas del hash antes de bloquear (no ordena solo las referencias fuente). Una colisión de hash solo serializa referencias extra; la constraint conserva la verdad. Ver prueba y evidencia en `09-commerce-importacion-y-verificacion.md`.

La espera por el advisory lock y la lectura existente deben ser **comandos SQL separados** bajo READ COMMITTED: la segunda consulta recibe snapshot posterior a la espera y ve el commit competidor. Verificar en implementación el isolation level real de middleware/contexto; si no es READ COMMITTED, no usar esta estrategia sin resolver snapshots. Dos lotes con refs solapadas en distinto orden usan el mismo orden global, evitando el deadlock de lock por orden de archivo.

Si el primer lote confirma, el segundo despierta, lee la identidad ya persistida y devuelve existente o conflicto según la huella. Si el primero revierte, el segundo puede crear. Una violación inesperada de unique (writer fuera del protocolo, cambio de código o condición excepcional) no se atrapa para seguir consultando en la transacción abortada: propagarla y hacer rollback total; el cliente puede reintentar el archivo, que la identidad ya confirmada resolverá idempotentemente. No devolver mezcla de filas creadas y fallidas.

500 filas y 5 MiB son límites finitos pero aumentan duración de transacción, retención del lock de comercio/operador y escrituras (dos mensajes por nuevo envío). Con el middleware actual la transacción existe durante la solicitud, incluso la recepción del multipart. Mantener estos límites como máximos iniciales del diseño, añadir timeout/limitación de cuerpo por endpoint consistente con la API y medir duración/contención con PostgreSQL aislado antes de habilitar; no subirlos por encima de 500 ni convertir el flujo en job. Si 500 filas exceden el presupuesto de duración/locks acordado, reducir el límite antes del rollout y actualizar la plantilla/ayuda; no partir el lote en transacciones parciales.

## 7. Outbox y mensajería

Para cada envío nuevo canónico, conservar la generación actual dentro de la transacción:

| Tipo existente | Destino actual | Contenido relevante |
|---|---|---|
| GenerarSeguimiento | RabbitMQ, consumidor GenerarSeguimientoConsumer | envioId, operadorId. |
| EnvioCreado | Kafka, publicador KafkaEnvioCreadoPublisher | envioId, operadorId, comercioId, estado. |

Los dos mensajes se insertan junto al envío, destinatario, dirección, bulto e identidad; el middleware confirma o revierte el conjunto. El OutboxMessage actual debe conservar su identificador estable por mensaje. Reutilizar OutboxMessage.ForShipment(...) sin generar mensajes para existentes, duplicados coalescidos o filas inválidas. El dispatcher actual sigue publicando tras commit.

El modelo es al menos una vez, no exactamente una vez: una caída después de publicar y antes de marcar como procesado permite redelivery. Mantener identidad estable y el control de duplicados ya existente en consumer/publicadores donde exista; no afirmar que RabbitMQ/Kafka y SQL comparten una única transacción. Reintentos crecientes (el monitoreo observó intervalo fijo) y administración operativa de fallidos/DLQ siguen como pendientes transversales separados; no son parte de esta importación ni se agregan aquí. No se propone consumidor local de Kafka, broker, evento ni worker nuevo.

## 8. Contrato HTTP y resultado por fila propuestos

### Solicitud

~~~http
POST /api/envios/importaciones
Authorization: Bearer <token>
Content-Type: multipart/form-data

archivo: <CSV>
operadorId: <UUID>
~~~

Aplicar Authorize, envios.crear y política de actor Comercio como en CreateShipment. No aceptar ComercioId, operador por fila ni campos de estado/reglas/outbox. Límite de archivo: 5 MiB; 500 registros de datos no vacíos.

### Respuesta de aplicación

ImportacionEnviosResponse propuesta:

~~~json
{
  "estado": "Completada",
  "resumen": {"creados": 1, "existentes": 1, "duplicadosEnArchivo": 0, "conflictos": 0, "invalidos": 0, "noProcesados": 0},
  "filas": [
    {"registro": 1, "referenciaExterna": "PED-2026-0001", "estado": "Creado", "envioId": "11111111-1111-1111-1111-111111111111", "errores": []},
    {"registro": 2, "referenciaExterna": "PED-2026-0002", "estado": "YaExistente", "envioId": "22222222-2222-2222-2222-222222222222", "errores": []}
  ]
}
~~~

Estados de fila propuestos: Creado, YaExistente, DuplicadoDe, Conflicto, Invalido, NoProcesado; incluir registro, referenciaExterna cuando pudo parsearse, envioId solo para creado/existente y mismoQueRegistro para DuplicadoDe. Errores estructurados {codigo,campo,mensaje}. estado de lote Completada o RechazadaAtomica.

En rechazo atómico: creados=0; referencias existentes exactas pueden seguir apareciendo como YaExistente (son lecturas, no efectos); conflictos/invalidaciones identifican fila; candidatos nuevos válidos aparecen NoProcesado. noProcesados cuenta esas filas canónicas y duplicadosEnArchivo filas adicionales correlacionadas; definir y testear que los totales no dupliquen conteos. No devolver Creado si el middleware todavía no confirmó commit.

Precedencia propuesta: error de encoding/sintaxis/encabezado de archivo da 400 antes del análisis de filas. Con archivo parseable, cualquier conflicto de identidad hace que el status global sea 409; las filas inválidas siguen identificadas como Invalido y las filas nuevas válidas como NoProcesado. Sin conflictos, errores de validación/admisión dan 422. En ambos casos no se confirman filas nuevas.

### Estados HTTP propuestos

| HTTP | Uso |
|---|---|
| 200 | Archivo procesado, incluidos todos existentes o mezcla existente/nuevo; el resultado explica por fila. |
| 400 | Multipart faltante, CSV/UTF-8/encabezado/comillas malformados. Sin escrituras. |
| 401 / 403 | Autenticación, actor/política de Commerce o permiso, igual que endpoints existentes. |
| 409 | Misma referencia con huella u operador distinto, incluyendo duplicados internos incompatibles; lote rechazado atómicamente. |
| 413 | Más de 5 MiB o más de 500 filas. |
| 422 | Filas con campos inválidos o admisión de operador/reglas rechazada; lote atómico. |
| 5xx | Error de base/commit/outbox persistido inesperado; rollback total, respuesta sin resultados de creación. |

Una solicitud repetida tras timeout de red se reenvía completa: tras un commit confirmado la referencia vuelve YaExistente; tras rollback puede crear. Un HTTP 200 perdido por el cliente no puede implicar crear duplicado. No usar 202 ni porcentaje de procesamiento porque no existe job ni canal de progreso del servidor.

## 9. Ejemplos de contrato

En todos los ejemplos operadorId es un campo multipart común del archivo; UUIDs son ilustrativos.

### 1. Archivo nuevo válido

~~~csv
referenciaExterna,nombreDestinatario,emailDestinatario,direccion,codigoBulto,pesoGramos,largoCentimetros,anchoCentimetros,altoCentimetros
PED-2026-0001,María Pérez,maria@example.test,"18 de Julio, 1234 apto 2",BX-001,1200.50,30.00,20.00,10.00
~~~

HTTP 200:

~~~json
{"estado":"Completada","resumen":{"creados":1,"existentes":0,"duplicadosEnArchivo":0,"conflictos":0,"invalidos":0,"noProcesados":0},"filas":[{"registro":1,"referenciaExterna":"PED-2026-0001","estado":"Creado","envioId":"11111111-1111-1111-1111-111111111111","errores":[]}]}
~~~

En la transacción: un envío, destinatario, dirección, bulto, identidad y dos outbox.

### 2. Reimportación idéntica

Archivo completo:

~~~csv
referenciaExterna,nombreDestinatario,emailDestinatario,direccion,codigoBulto,pesoGramos,largoCentimetros,anchoCentimetros,altoCentimetros
PED-2026-0001,María Pérez,maria@example.test,"18 de Julio, 1234 apto 2",BX-001,1200.50,30.00,20.00,10.00
~~~

Con el mismo operadorId de la importación inicial, HTTP 200:

~~~json
{"estado":"Completada","resumen":{"creados":0,"existentes":1,"duplicadosEnArchivo":0,"conflictos":0,"invalidos":0,"noProcesados":0},"filas":[{"registro":1,"referenciaExterna":"PED-2026-0001","estado":"YaExistente","envioId":"11111111-1111-1111-1111-111111111111","errores":[]}]}
~~~

El conteo outbox no cambia. Se obtiene igual resultado aunque el estado, versión de reglas o tracking interno haya avanzado.

### 3. Existentes y nuevas

Archivo completo, mismo operador para ambas filas:

~~~csv
referenciaExterna,nombreDestinatario,emailDestinatario,direccion,codigoBulto,pesoGramos,largoCentimetros,anchoCentimetros,altoCentimetros
PED-2026-0001,María Pérez,maria@example.test,"18 de Julio, 1234 apto 2",BX-001,1200.50,30.00,20.00,10.00
PED-2026-0002,Juan Díaz,juan@example.test,"Rambla 100",BX-002,800,25,15,10
~~~

HTTP 200:

~~~json
{"estado":"Completada","resumen":{"creados":1,"existentes":1,"duplicadosEnArchivo":0,"conflictos":0,"invalidos":0,"noProcesados":0},"filas":[{"registro":1,"referenciaExterna":"PED-2026-0001","estado":"YaExistente","envioId":"11111111-1111-1111-1111-111111111111","errores":[]},{"registro":2,"referenciaExterna":"PED-2026-0002","estado":"Creado","envioId":"22222222-2222-2222-2222-222222222222","errores":[]}]}
~~~

Se insertan dos outbox solo para PED-2026-0002.

### 4. Conflicto revierte todo

Archivo completo, suponiendo que PED-2026-0001 existe con los datos anteriores:

~~~csv
referenciaExterna,nombreDestinatario,emailDestinatario,direccion,codigoBulto,pesoGramos,largoCentimetros,anchoCentimetros,altoCentimetros
PED-2026-0003,Laura Soto,laura@example.test,"Av. Italia 500",BX-003,900,25,15,12
PED-2026-0001,María Pérez,maria@example.test,"18 de Julio 999",BX-001,1200.50,30.00,20.00,10.00
~~~

HTTP 409:

~~~json
{"estado":"RechazadaAtomica","resumen":{"creados":0,"existentes":0,"duplicadosEnArchivo":0,"conflictos":1,"invalidos":0,"noProcesados":1},"filas":[{"registro":1,"referenciaExterna":"PED-2026-0003","estado":"NoProcesado","errores":[]},{"registro":2,"referenciaExterna":"PED-2026-0001","estado":"Conflicto","errores":[{"codigo":"ReferenciaConDatosDiferentes","campo":"direccion","mensaje":"La referencia ya existe con datos u operador distintos."}]}]}
~~~

Sin nuevo envío, identidad ni outbox para PED-2026-0003.

### 5. CSV malformado

~~~csv
referenciaExterna,nombreDestinatario,emailDestinatario,direccion,codigoBulto,pesoGramos,largoCentimetros,anchoCentimetros,altoCentimetros
PED-2026-0004,Ana,ana@example.test,"Calle 1,BX-4,100,20,20,20
~~~

La comilla sin cerrar produce HTTP 400 con error de sintaxis y fila/línea si el parser puede identificarla; no hay escritura. Respuesta ilustrativa:

~~~json
{"type":"about:blank","title":"CSV malformado","status":400,"errors":[{"codigo":"CsvComillasSinCerrar","registro":1,"campo":"direccion","mensaje":"No se pudo leer el campo entrecomillado."}]}
~~~

La respuesta es error de archivo, no éxito parcial.

### 6. Referencias repetidas en el mismo archivo

**Misma referencia y payload equivalente**, archivo completo:

~~~csv
referenciaExterna,nombreDestinatario,emailDestinatario,direccion,codigoBulto,pesoGramos,largoCentimetros,anchoCentimetros,altoCentimetros
PED-2026-0005,Elena Paz,elena@example.test,"Colonia 10",BX-005,700,20,12,8
PED-2026-0005,Elena Paz,elena@example.test,"Colonia 10",BX-005,700,20,12,8
~~~

Se coalescen: primera Creado (o YaExistente si ya estaba), segunda DuplicadoDe con mismoQueRegistro: 1; una sola operación de persistencia y un solo par outbox. Si era nuevo, HTTP 200:

~~~json
{"estado":"Completada","resumen":{"creados":1,"existentes":0,"duplicadosEnArchivo":1,"conflictos":0,"invalidos":0,"noProcesados":0},"filas":[{"registro":1,"referenciaExterna":"PED-2026-0005","estado":"Creado","envioId":"55555555-5555-5555-5555-555555555555","errores":[]},{"registro":2,"referenciaExterna":"PED-2026-0005","estado":"DuplicadoDe","mismoQueRegistro":1,"envioId":"55555555-5555-5555-5555-555555555555","errores":[]}]}
~~~

**Misma referencia y payload diferente**, archivo completo:

~~~csv
referenciaExterna,nombreDestinatario,emailDestinatario,direccion,codigoBulto,pesoGramos,largoCentimetros,anchoCentimetros,altoCentimetros
PED-2026-0006,Elena Paz,elena@example.test,"Colonia 10",BX-006,700,20,12,8
PED-2026-0006,Elena Paz,elena@example.test,"Colonia 10",BX-006,701,20,12,8
~~~

Genera HTTP 409; el lote completo se rechaza, ambas filas se correlacionan como conflicto y ninguna fila nueva se confirma:

~~~json
{"estado":"RechazadaAtomica","resumen":{"creados":0,"existentes":0,"duplicadosEnArchivo":0,"conflictos":2,"invalidos":0,"noProcesados":0},"filas":[{"registro":1,"referenciaExterna":"PED-2026-0006","estado":"Conflicto","errores":[{"codigo":"ReferenciaDuplicadaConPayloadDiferente","campo":"referenciaExterna","mensaje":"La misma referencia aparece con datos distintos en el archivo."}]},{"registro":2,"referenciaExterna":"PED-2026-0006","estado":"Conflicto","errores":[{"codigo":"ReferenciaDuplicadaConPayloadDiferente","campo":"referenciaExterna","mensaje":"La misma referencia aparece con datos distintos en el archivo."}]}]}
~~~

Operador diferente no puede repetirse dentro del archivo porque es campo común; sí produce conflicto si difiere del operador almacenado para esa referencia.

## 10. Experiencia Commerce

Nueva ruta propuesta /envios/importar, autorizada con ShipmentsCreatePolicy, reutilizando EnviosApiClient, OperadoresApiClient, AuthenticationStateProvider y el patrón multipart actual de IdentidadVisualApiClient. La pantalla actual CrearEnvio.razor conserva campos, endpoint y resultado.

- InputFile, selección de operador, enlace de plantilla estática y explicación corta de columnas, unidades y punto decimal; incluir ejemplo con coma entrecomillada.
- Mostrar nombre/tamaño de archivo y error de formato/tamaño local detectable. Validación en cliente es orientativa: API vuelve a validar todo.
- Estados precisos: Seleccionando archivo, Subiendo archivo si el cliente puede observar la transferencia, Validando y procesando sin porcentaje mientras espera respuesta, Completada, Rechazada o Error de comunicación. No presentar porcentaje de filas si API no lo emite.
- Deshabilitar selección/envío durante una petición (enviando), prevenir doble submit, preservar archivo/operador y permitir reintento explícito con stream nuevo. No deshabilitar permanentemente al recibir error.
- Éxito completo solo si respuesta HTTP y resultado son Completada. Si hay rechazos, banner de archivo rechazado, total cero creados, conflictos/errores por número de fila y nuevos no procesados por atomicidad. «Ya existente» debe decir claramente que no se modificó.
- Para carga asíncrona real usar skeleton donde corresponda; asociar labels/descripciones, resumen accesible, aria-busy, región role=status/alert, foco visible, teclado y tokens semánticos conforme frontend/DESIGN.md y WCAG 2.2 AA.

La opción del operador debe incluir el mismo operador de referencias existentes. Reutilizar histórico de GET /api/envios solo si el permiso de consulta ya está presente, porque la ruta está protegida por envios.consultar; no concederlo por esta función ni imponer membresía. Confirmar esta limitación antes de implementar como se indica en §5.

## 11. Migración y compatibilidad

Una migración nueva y aditiva crea tabla, constraint/índice, RLS, políticas, grants y funciones acotadas. No altera la tabla Envios, datos existentes, datos de configuración ni reglas de roles globales. Verificar claves compuestas existentes para FK Commerce/Envio/Operador. Agregar solo la clave referencial mínima si es necesaria; no backfill de referencias. Si rollback de migración se requiere en desarrollo, que sea solo sobre la base efímera de fixture; no ejecutar migración destructiva en datos compartidos.

La compatibilidad del alta individual se cubre por su request/route/response actual, una prueba de regresión y el mismo builder/reglas de creación. La API individual no empieza a emitir referencia ni a reclamar idempotencia. Registros creados antes de la migración no se reconocen automáticamente como importados.

## 12. Plan de implementación verificable y estado al 24/10/2026

| Orden | Tarea pequeña | Componentes/repo | Criterio verificable |
|---|---|---|---|
| 1 | Cerrar contrato de CSV, validador y plantilla estática; probar parser con BOM, UTF-8 inválido, quotes/comas/saltos, encabezados, fila vacía, tamaño y límite. | Backend parser/request; Commerce wwwroot/plantillas/alta-envios.csv; tests unitarios propuestos. | Campos exactos se mapean a CrearEnvioRequest; ningún input inválido llega a persistencia; 5 MiB/500 se rechazan en límite + 1. |
| 2 | Migrar tabla privada de identidad, collation/unique/FK, RLS, roles y funciones de lock/find/bind; actualizar allowlist RlsSqlFunctionContract. | Backend Infrastructure migration/SQL. | API no tiene DML directo/BYPASSRLS; Comercio A no lee identidad B; referencia igual en comercios distintos funciona; funciones validan contexto, propietario/search_path/EXECUTE. |
| 3 | Reutilizar preparación de dominio del alta; agregar GuardarLoteAsync con contexto RLS por envío, create_shipment, identidad y los dos eventos existentes. | Application CrearEnvioUseCase/IEnviosRepository; Infrastructure EfEnviosRepository. | Alta individual conserva contrato y persistencia. Falla simulada tras la primera fila revierte hijos, identidades y todos los outbox del lote. |
| 4 | Implementar caso de uso de importación: validar todo, normalizar identidad, agrupar duplicados, locks ordenados, comparar huella, admitir nuevas, mapear atomicidad. | Application ImportarEnviosUseCase y resultados. | Pruebas reales PostgreSQL de completa/subconjunto, equivalentes, conflictos, operador inactivo, rollback y carrera concurrente. |
| 5 | Exponer multipart en EnviosController y DTOs HTTP con límites/estados acordados. | API Contracts/Controller; OpenAPI. | HTTP real 200/400/401/403/409/413/422/5xx; Commerce no puede fijar ComercioId; errores de archivo y filas localizables. |
| 6 | Integrar EnviosApiClient.ImportarAsync y página Commerce, plantilla, errores, estados, reintento y doble submit. | ApiClient; Commerce ImportarEnvios.razor, navegación mínima. | Tests de componente/cliente y revisión navegadora con éxito, existente, mixto, conflicto, validación, retry y doble clic; accesibilidad básica. |
| 7 | Cierre integrado en entorno aislado: medir 500 filas/5 MiB, duración de transacción/locks y comprobar dispatchers. | Fixtures backend, PostgreSQL temporal, broker(es) aislados, API/Commerce local. | Evidencia HTTP y navegador aparte de mocks. Ajustar máximo si excede presupuesto acordado; verificar eventos y no duplicación. |

### Pruebas de aceptación necesarias

- CSV válido con UTF-8 BOM/no BOM, comillas escapadas, coma y newline en campo, filas vacías; malformado, encabezado duplicado/ausente, UTF-8 inválido, tamaño y número de filas límite y límite + 1.
- Alta nueva; reimportación completa y subconjunto; archivo de existentes+nuevos; dos filas repetidas equivalentes; repetidas incompatibles; misma ref con datos u operador distintos; ausencia de actualización.
- PostgreSQL real: concurrencia de dos archivos con identidades coincidentes (mismo y distinto digest) y lote común en orden inverso; bloqueo/unique, sin deadlock o transacción abortada seguida de consulta; reintento de archivo tras rollback.
- Aislamiento real entre dos comercios y dos operadores; consultas de metadatos y tablas hijas bajo RLS; IDs, headers o campos manipulados no cambian el Commerce autenticado.
- Reimportar después de modificar estado, versión/reglas actuales, seguimiento o destino/coordenadas y seguir obteniendo YaExistente; probar hash/normalización versionada.
- Operador desactivado: referencia existente exacta con mismo operador devuelve YaExistente; cualquier fila nueva para operador inactivo rechaza todo el archivo.
- Fallar luego de crear el primer registro del lote, luego de insertar identidad o al persistir outbox: ninguna fila, hija, identidad ni mensaje nuevo queda confirmado. Cancelación también revierte.
- Por envío nuevo: exactamente un GenerarSeguimiento y un EnvioCreado con IDs estables; existente/repetido/invalidado: cero eventos nuevos. Confirmar publicación/consumo mediante componentes actuales si los brokers aislados están disponibles; reconocer redelivery al menos una vez.
- Regresión del alta individual: mismo request público, status/respuesta, un bulto, reglas y dos eventos; no recibe ni requiere referencia.
- HTTP y navegador real en entorno aislado: actor correcto, rechazo autorización, respuesta/resultados, corrección/reintento y bloqueo doble submit. Mock tests complementan, no sustituyen PostgreSQL/RLS/outbox.

## 13. Pendientes transversales y verificaciones posteriores

1. **Verificado en el bloque backend:** la solicitud usa la transaccion READ COMMITTED del middleware, la lectura ocurre despues de adquirir locks y el middleware solo publica la respuesta tras commit; ver `08-backend-importacion.md`.
2. **Resuelto en 09:** el endpoint acotado `GET /api/operadores/importacion-envios` devuelve solo operadores activos e históricos usados por importaciones del Comercio autenticado, requiere `envios.crear` y no amplía `envios.consultar`; la prueba de autorización/aislamiento está en `09-commerce-importacion-y-verificacion.md`.
3. **Verificado en el bloque backend:** límites byte/registro y flujo HTTP de 500 filas; 2.905 ms en una medición TestServer/PostgreSQL local de ese corte. La medición posterior con Kestrel fue 7.979 ms; ninguna es benchmark de producción. Ver `08-backend-importacion.md` y `09-commerce-importacion-y-verificacion.md`.
4. La auditoría 05 observó retry fijo de dispatch y falta de administración de fallidos identificada; dejar el backoff creciente y gestión operacional de fallidos como issues transversales separados. El dispatcher no equivale a entrega exactamente una vez.
5. Offline en navegador no está incluido: el outbox cubre trabajo asíncrono del servidor después del commit, no creación local sin conexión del cliente. No hay base para prometer modo offline.

## 14. Criterio para considerar CU-07 cerrado

Los criterios de diseño anteriores se contrastaron con backend y Commerce en los bloques 08/09: plantilla y pantalla accesibles al flujo; identidad única por comercio/RLS; atomicidad; reimportación estable; conflicto sin actualizar; repetidos equivalentes coalescidos; outbox en la transacción; alta individual compatible; pruebas PostgreSQL; HTTP Kestrel y navegador; límites de 5 MiB/500 medidos localmente. Esto acredita los recorridos directos de importación, no el cierre de todos los NFR transversales (X02/X04/X05/X06); sus limitaciones están en 01/09.


## 15. Estado de implementación backend (24/10/2026)

Las decisiones de trabajo listadas en seccion 2 se adoptaron para este bloque por instruccion expresa del usuario; siguen siendo decisiones de proyecto y no texto literal de las fuentes originales. El backend cubierto por las tareas 1-5 de seccion 12 quedo implementado y verificado, con estas precisiones frente al plan inicial:

| Componente | Resultado observado |
|---|---|
| Parser/validacion | `CsvEnviosParser`, `ImportarEnviosUseCase` y `HuellaSolicitudEnvio` implementados en Application. Se reutiliza `TextFieldParser`; el contrato se confirma con `CrearEnvioRequest` y las entidades actuales. |
| Identidad/migracion | `20261024130000_AddShipmentImportIdentity`: tabla privada por comercio/referencia, hash versionado, FKs, RLS y funciones acotadas. La clave `Envios(ComercioId,Id)` se agrega para FK; el indice existente `IX_Envios_ComercioId` se conserva sin cambios ni backfill. |
| Creacion | `CrearEnvioUseCase` comparte admision y construccion de agregado; `EfEnviosRepository.CrearEnBaseAsync` mantiene la misma `create_shipment` y agrega identidad/outbox solo en filas nuevas. El alta individual conserva request/ruta/respuesta y no requiere referencia. |
| Endpoint | `POST /api/envios/importaciones` multipart `archivo`/`operadorId`, politicas Comercio+`envios.crear`, codigos/DTOs de resultado y OpenAPI generado por el mecanismo actual. |
| Transacción/carreras | Una transacción por solicitud, `READ COMMITTED`; se deduplican y bloquean las claves hash `bigint` efectivas en orden numérico global antes de la lectura posterior; la unique de base es guardia final. Test de respuesta perdida después de commit demuestra recuperación por reintento. Corrección y prueba en 09. |
| Outbox | Solo los envios nuevos obtienen un `GenerarSeguimiento` RabbitMQ y un `EnvioCreado` Kafka, persistidos en la misma transaccion. Esta etapa no ejecuta brokers ni publica/consume eventos. |
| Verificacion | Unit y HTTP/PostgreSQL Testcontainers, RLS/privilegios, rollback, carreras, commit incierto, alta individual/cancelacion y medicion local; resultados exactos en `08-backend-importacion.md`. |

**Corte histórico reemplazado por 09:** ApiClient/Commerce, plantilla, estados/resultados, reintento, doble envío y navegador aislado se completaron y se documentan en `09-commerce-importacion-y-verificacion.md`. Las mediciones siguen siendo locales, no son validación de carga o producción; quedan pendientes X02/X04/X05/X06 conforme a la matriz actual. CU-08 y la máquina de estados completa no se cierran por esta implementación.
