# CU-07 — diseño de implementación propuesto

**Estado:** propuesta técnica; no se modificó código. La fuente oficial obliga a importar por archivo y a evitar duplicados al reimportar un lote completo o parcial. No prescribe formato de archivo, identidad externa ni política para filas inválidas o referencias con payload diferente.

**Nota de estado (corte histórico):** esta versión registró preguntas abiertas antes de las decisiones de trabajo posteriores. `06-diseno-tecnico-y-plan.md` recoge las decisiones de proyecto y los informes `08-backend-importacion.md` y `09-commerce-importacion-y-verificacion.md` evidencian su implementación por bloques. Esos parámetros no se convierten en requisitos literales del PDF/XLSM. Las afirmaciones de este documento de que no se habían agregado migraciones/endpoints/formularios o que las semánticas seguían pendientes describen únicamente su corte anterior y quedan sustituidas por 06/08/09; este informe conserva su valor histórico.

## Fuentes reconsultadas

- docs/alcance/Laboratorio__NET_2026.pdf: sección 5.2, requisito 7 (p. impresa 4, página física 6); sección 3.3 (p. impresa 2, página física 4); secciones 6.3, 6.5, 6.6 y 6.8 (p. impresas 5–6, páginas físicas 7–8).
- docs/alcance/Calcs/Casos de Uso - Responsables.xlsm: CU obligatorios!A10:I10 y Dependencias!A4:I4.
- docs/auditorias/cu07/01-requisitos-y-trazabilidad.md, 02-hallazgos.md y 03-plan-de-cierre.md.
- Contrato/modelo actual: CrearEnvioRequest, CrearEnvioUseCase, Envio, NexoRutaDbContext, función create_shipment, EfEnviosRepository y pantalla CrearEnvio de Commerce (rutas con líneas en el informe 01).

La letra exige alta individual, por archivo y por API; la importación masiva debe ser idempotente para reimportaciones completas o parciales. CU-08 conserva el requisito separado de uno o más bultos. La fila del XLSM no define un flujo textual completo ni columnas/formato.

## Requisitos documentados vs. decisiones técnicas

| Tema | Lo que prescribe la fuente | Propuesta técnica no normativa | Estado |
|---|---|---|---|
| Formato | Importar envíos por archivo; no fija CSV/XLSX, codificación, delimitador ni nombres de campos. | CSV UTF-8, encabezados exactos en lower camel case, delimitador coma, quoting RFC 4180 y BOM opcional. Rechazar encabezados ausentes/desconocidos y secuencias UTF-8 inválidas. No aceptar XLS/XLSX ni ejecutar macros. | Propuesto |
| Campos del archivo | CU-07 no enumera campos. CU-08 exige identificación, peso y dimensiones del bulto; el request actual ya contiene los campos de una creación. | Una fila representa un envío con el único bulto que soporta hoy el flujo: externalReference, recipientName, recipientEmail, address, packageCode, weightGrams, lengthCentimeters, widthCentimeters y heightCentimeters. Reutilizar longitudes y rangos del request actual; decimales con punto y cultura invariante. No agregar columnas para tarifa, tracking o estado. | Propuesto |
| Operador | El PDF indica que el comercio puede operar con más de un operador, pero no dice si un archivo mezcla operadores. El request actual selecciona uno por envío. | Para reducir error, seleccionar un operador disponible una vez por archivo y enviarlo como dato del lote; no confiar en CommerceId del formulario. El archivo no tendría columna operatorId. | Decisión funcional pendiente |
| Referencia externa | La letra exige que la repetición no duplique, pero no especifica la clave. | Exigir externalReference estable provista por el comercio en cada fila. Recortar espacios exteriores, no derivarla de los demás datos, límite inicial propuesto 128 caracteres. La igualdad propuesta es ordinal y sensible a mayúsculas/minúsculas. | Propuesto; confirmar ámbito |
| Ámbito de unicidad | El PDF dice que un comercio puede operar con más de un operador. La ADR actual ubica el operador en cada envío y descarta una membresía permanente. No se define la clave del importador. | Índice único parcial por (ComercioId, ReferenciaExterna), independiente de OperadorId. El comercio es el dueño de la referencia externa; cambiar operador no crearía otra identidad para el mismo envío. | Decisión funcional pendiente |
| Límites | No están fijados por la letra. | Máximo 5 MiB por archivo y 500 filas de datos por importación, más límites de campos del request vigente. Limitar bytes antes de parsear y detener al exceder filas para acotar memoria/tiempo. | Propuesto, ajustable |
| Parser/dependencias | No hay requisito tecnológico de parsing. | El backend actual apunta a .NET 10; el reference pack instalado incluye Microsoft.VisualBasic.Core y su TextFieldParser. Puede parsear texto delimitado/campos entrecomillados sin agregar NuGet. Verificar compilación y casos RFC 4180 antes de adoptarlo; no agregar dependencia solo para CSV. | Propuesta técnica |

## Identidad e idempotencia propuestas

1. El importador exige una referencia externa no vacía por fila. Nunca usa hash del destinatario, dirección, bulto ni otros datos del envío como identidad: dos envíos legítimos pueden compartirlos.
2. Reimportar un subconjunto significa volver a enviar algunas filas con las mismas referencias externas. No hace falta un identificador de lote ni guardar el archivo completo; la identidad es por fila.
3. Propongo que la referencia sea única dentro del ComercioId, a través de todos sus operadores. OperadorId se selecciona por envío/lote, mientras que la referencia representa el pedido del comercio. Esto evita duplicar el pedido si se reimporta bajo otro operador, pero puede ser demasiado amplio si el comercio reutiliza la misma referencia para pedidos independientes; se necesita confirmación.
4. Si referencia y payload validado/normalizado coinciden, devolver estado Existing y el identificador del envío ya creado, sin modificarlo, llamar el camino de creación ni publicar eventos.
5. Si la referencia existe y cualquier dato de creación difiere, propongo conflicto/rechazo sin modificar el envío existente. No hacer upsert implícito: el envío pudo haber avanzado de estado y el contrato no define corrección. La alternativa de actualizar solo envíos aún Admitido debe ser elegida explícitamente.
6. Los registros creados por los canales individuales/API existentes no tienen referencia externa. Para preservar su request y comportamiento, la columna sería nullable y el índice parcial solo aplicaría a referencias no nulas. Por ello esta primera versión garantiza reimportación idempotente entre importaciones que usan la referencia, pero no reconoce automáticamente una creación manual/API previa sin referencia. Ampliar la deduplicación entre canales requiere agregar una referencia opcional al contrato individual y decidir si la UI la solicita.

## Filas inválidas: decisión funcional bloqueante

La exigencia de reimportar un subconjunto no implica procesar parcialmente un archivo que contiene filas inválidas.

Alternativas:

- **A. Archivo atómico (recomendación):** validar sintaxis y todas las filas antes de insertar. Si existe una fila inválida o una referencia con datos distintos, crear cero filas nuevas en ese envío del archivo; devolver errores por línea y marcar filas nuevas válidas como no procesadas. Los Existing siguen siendo solo lectura. Corregido el archivo, puede reimportarse el subconjunto requerido sin duplicar.
- **B. Procesamiento parcial:** crear cada fila válida nueva, devolver Existing para coincidencias idénticas y Rejected para las inválidas/conflictivas. Un fallo de una fila no revierte otras ya confirmadas; cada fila nueva conserva agregado y outbox atómicos.

La documentación no elige A o B. Cambia qué envíos se crean ante el mismo archivo, por lo que no se implementará hasta confirmación.

## Contrato de resultado propuesto

La API responde por fila con número de línea, externalReference, estado y errores legibles; además devuelve totales de creados, existentes, rechazados y, para alternativa A, no procesados. Estados propuestos: Created, Existing, Rejected y NotProcessed. Un error de sintaxis/global (archivo vacío, cabecera incorrecta, bytes excedidos, CSV malformado) rechaza el archivo completo antes de crear datos.

La ruta sugerida es un endpoint nuevo autenticado de importación multipart en la feature Envios, con el operador elegido en el nivel del lote y el archivo. La ruta, nombre del DTO y status HTTP son contrato de implementación, no requisitos literales. Se conserva sin cambios el POST /api/envios individual. El contexto ComercioId siempre proviene de IUsuarioActual/RLS; no se acepta como autoridad un CommerceId del request.

## Persistencia, concurrencia y outbox

- Agregar ReferenciaExterna nullable a Envio, migración y restricción única parcial con ComercioId (o el ámbito que se confirme). Los registros actuales quedan nulos; no se reconstruye identidad a partir de sus campos.
- La consulta previa no da garantía frente a carreras. La restricción única de PostgreSQL debe arbitrar la inserción concurrente; la operación de base debe retornar si creó, encontró el mismo payload o detectó conflicto, sin dejar transacción abortada.
- Reutilizar la validación/aplicación que crea Envio, Destinatario, Dirección y un Bulto. Evitar una ruta separada que omita reglas publicadas, permisos, RLS o contexto.
- Solo una fila insertada por primera vez agrega sus dos mensajes outbox, dentro de la misma transacción que el agregado. Existing y Rejected no generan mensajes de creación.
- Con opción A, la transacción del lote confirma todo el conjunto nuevo o ninguno. Con opción B, cada fila se confirma de forma independiente. En ambos casos, error de persistencia no debe dejar envío sin sus mensajes outbox ni eventos huérfanos.

La migración de identidad y la garantía de concurrencia requieren verificación con PostgreSQL real de Testcontainers. No se ejecutará contra un destino Docker cuya conexión no haya sido comprobada como local/aislada.

## Integración de Commerce

Usar el componente InputFile de Blazor y el ApiClient existente; no agregar librería o framework. La UI propone seleccionar un operador y un CSV, explicar formato/campos, mostrar progreso y resultado por fila, conservar estado ante error y bloquear doble submit. Un error parcial nunca se mostrará como éxito global. Los nombres exactos de estados dependen de la decisión de procesamiento de filas.

## Decisiones identificadas en la versión histórica de este informe

1. ¿Se confirma referencia única por comercio a través de operadores, o debe ser única por comercio y operador?
2. ¿El operador se elige una vez para todo el archivo o puede variar por fila?
3. Ante filas inválidas/conflictivas: ¿A, archivo atómico, o B, procesar válidas y rechazar el resto?
4. Ante la misma referencia con datos distintos: ¿A, conflicto sin modificar (recomendado), o B, actualizar solo si el envío aún está Admitido y nunca si avanzó?
5. ¿El identificador externo debe deduplicar también contra envíos creados por el alta individual/API, lo que exigiría hacerlo opcional en esos contratos, o solo contra filas de importaciones?

En esta versión, esas decisiones seguían pendientes y no se agregaron migraciones, endpoints ni formularios. Las bases de trabajo posteriores están recogidas —sin iniciar implementación— en [06-diseno-tecnico-y-plan.md](06-diseno-tecnico-y-plan.md); son propuestas de proyecto que deberán verificarse contra el código antes de implementarse, no requisitos oficiales.

## Verificación independiente antes de cerrar decisiones

**Corte histórico de la auditoría anterior:** los resultados que siguen son previos al 23/10/2026 y quedan supersedidos para el alta existente por `05-verificacion-flujo-existente.md`. Siguen siendo válidos sólo como evidencia de que esas suites base no probaban la importación.

En el corte de esta versión se ejecutaron los checks locales que no dependen de la semántica de importación:

- `dotnet test backend/tests/NexoRuta.UnitTests/NexoRuta.UnitTests.csproj --no-restore --logger "console;verbosity=minimal"` — correcto: 174 aprobadas, 0 fallidas, 0 omitidas.
- `dotnet test frontend/tests/NexoRuta.ApiClient.Tests/NexoRuta.ApiClient.Tests.csproj --no-restore --logger "console;verbosity=minimal"` — correcto: 324 aprobadas, 0 fallidas, 0 omitidas. Esta suite incluye pruebas de aplicación con API simulada; no demuestra una importación HTTP/backend real.
- No se ejecutaron pruebas de integración con PostgreSQL ni se iniciaron contenedores. La inspección inicial de `docker context inspect` falló al procesar su plantilla de salida, así que el destino de Docker no se considera verificado. La fixture existente crea bases `integration_<uuid>` dentro de su propio contenedor, pero la futura ejecución queda pendiente de confirmar el destino Docker.

Estos resultados son línea base de los repositorios y no prueban comportamiento de importación CU-07, que aún no está implementada.
