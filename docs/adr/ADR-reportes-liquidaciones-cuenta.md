# ADR: proyecciones reconciliables y documentos económicos estables

Estado: implementado para revisión. Responsable de aceptación docente: equipo NexoRuta; asistencia de implementación: Codex. Fuentes: letra original §4/30 y cambios 31–41. Alcance y reglas detalladas en `../gestion/reportes-liquidaciones-cuenta.md`.

## Contexto

El resumen por tipo/estado agrupaba envíos enteros en memoria y Backoffice duplicaba su implementación. No acreditaba cumplimiento, motivos, atribución por bulto ni liquidación. El sistema ya conserva reglas y tarifas versionadas al admitir, diario inmutable, bultos, outbox y un stream operativo. Sus tarifas aplicadas son snapshots acumulados: sumar filas cobra la admisión repetidas veces. Parciales agregan visitas/autores y retiros agregan tarifa/ciclo propios. Hay RLS forzado y roles separados que deben conservarse.

## Decisión

Application define contratos/casos de uso y resuelve operador/comercio desde el acceso validado. Domain valida el cierre y las correcciones. Una proyección relacional de operación, bulto y motivos sirve reportes; un consumidor independiente del stream operativo reconcilia hechos persistidos, por generaciones y lotes. El reloj de la consulta clasifica operaciones abiertas vencidas; no requiere un nuevo evento a medianoche. Repetir o invertir mensajes relee el estado canónico, sin hacer retroceder la proyección ni crear cargos. El detalle permite explicar cantidades y atribución histórica por autor del hecho físico.

La economía permanece en PostgreSQL: vista con diferencias entre cargos inmutables y movimientos compensatorios explícitos. Preparar congela conceptos; confirmar los reclama atómicamente, con PK única, bloqueo por cuenta y validación de estado/fuente. Documentos confirmados quedan inmutables. Los casos sin política económica publicada quedan visibles y retenidos. Lecturas GET coherentes usan RepeatableRead; comandos usan transacción y bloqueos de la arquitectura existente. RLS, funciones definer acotadas y permisos separados cubren también la persistencia. No se incorpora otra fuente económica ni pagos inexistentes.

## Alternativas

- Agrupar envíos en cada llamada: menor cambio inicial, pero carga todo, duplica parciales y no cumple el procesamiento worker.
- Analítica Mongo de eventos para todos los reportes: útil para historia técnica, pero contar eventos no cuenta operaciones y no garantiza integridad económica ni deduplicación de cargos.
- Libro nuevo duplicando cada cargo mediante Kafka: introduce consistencia eventual económica y riesgo de cobro duplicado en replay; la fuente consistente ya existe.
- Recalcular tarifas con el catálogo actual: rompe los importes históricos y las reglas capturadas.
- Asignar el envío completo al último repartidor: atribuye al autor equivocado los bultos entregados en visitas previas. Se adopta unidad por bulto para ese corte, con denominador explícito.
- Editar documentos confirmados o simular pagos: destruye trazabilidad o inventa hechos. Se usan correcciones firmadas y cuenta operativa.

## Consecuencias

Se requieren dos migraciones aditivas, índices y proyecciones recuperables; el worker añade carga de lectura por operación sucia, acotada por lote, no por consulta. Existe consistencia eventual visible en reportes. La economía y el detalle confirmado son consistentes y no dependen de Kafka/Mongo. Una operación con varias visitas no aparece repetida en volumen, pero sus bultos pueden participar en cortes de autores diferentes: las unidades se explican en la interfaz. El máximo de 1000 conceptos exige dividir períodos grandes. No existe política definitiva para cobrar cancelaciones/devoluciones/extravíos: se retienen explícitamente hasta que el negocio publique esa regla; no se presenta la decisión mínima como exigencia docente.

Incorporar parciales resultó directo porque el diario y los resultados por bulto ya existían. Lo más delicado fue distinguir tarifas acumuladas de movimientos, reconstruir autoría sin usar rutas actuales y coordinar confirmaciones. Las pruebas nuevas ejercitan esos límites con PostgreSQL, Kafka y navegador; no amplían webhooks, push, cierre diario, Android o infraestructura remota.
