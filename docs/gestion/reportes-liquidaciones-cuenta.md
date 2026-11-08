# Reportes de gestión, liquidaciones y cuenta operativa

Fuentes normativas: `docs/alcance/Laboratorio__NET_2026.pdf`, §§4, 5.5/30, 6.4–6.6, 6.8 y 6.15; `docs/cambios-requerimientos/Cambios de Requerimientos Planificados.pdf`, requisitos 31–41. Se leyeron ambos PDF. Excel y auditorías anteriores no fijan este alcance.

Base integrada consultada mediante fetch de develop: raíz `6001eb5cf6dba189f2be4d4777459b5bb554e7c9`; backend `d7b1a3ee2c9fdbd023158b299342530d6f7e2f77`; frontend `a2118d8f74759425af1a1a69d12c7bc2693e4d07`; mobile `53f6be2cdec48f48e30e390060feeaefb5be0ead`. No se cambió mobile. Los checkouts hermanos originales quedaron preservados. El manifiesto Cloud anterior no sustituye esos gitlinks.

## Trazabilidad y decisiones funcionales

| Requisito literal | Definición adoptada | Datos y regla temporal/cálculo | Pantalla/API y verificación |
| --- | --- | --- | --- |
| «reportes de gestión»; «cumplimiento por zona, repartidor y comercio» (30) | Evaluación explícita con seis clases; porcentaje sobre cumplidos + incumplidos. Se muestran los excluidos del denominador. | Admisión dentro de [desde,hasta). Plazo Estandar/Urgente desde CreadoEnUtc usando VersionReglasId y modalidad persistida. Cobertura/revisión del primer cargo; franjas de su snapshot. Sin plazo/cobertura suficiente: SinCompromiso. Una llegada estimada no es compromiso. | Menú Reportes de gestión; GET /api/gestion/operadores/{op}/reportes. GestionCircuitTests verifica cantidades y denominadores. |
| «Cada bulto tiene su propio resultado» (31–34) | Zona/comercio cuentan una operación; fin físico = máximo de fechas de sus bultos cuando todos fueron entregados. Prueba pendiente/vencida se identifica y excluye de la evaluación definitiva. | Bultos.Resultado, EntregadoEnUtc; la operación completa cumple si todos fueron entregados dentro de sus franjas capturadas y antes del plazo. Cancelación/devolución/extravío: NoEvaluable; operaciones abiertas vencidas: Incumplido, abiertas aún en plazo: EnPlazo. | Detalle de operación y bultos; tests de parcial con visitas de autores distintos, incumplimiento final y prueba pendiente. |
| «cumplimiento por ... repartidor» (30) | Unidad propia explícita: bultos entregados físicamente o retirados. Evita atribuir toda una entrega parcial al último repartidor. | Autor y ruta del diario inmutable OperacionesJornada, comando aplicado de EntregaFisica/EntregaBultos que coincide con EntregadoEnUtc; evidencia posterior no cuenta otra entrega. RetirarBultos para retiros. Sin autor verificable permanece identificado; nunca se usa la asignación actual. | Agregado Repartidor y detalle por bulto; GestionCircuitTests y navegador. |
| «motivos de no entrega» (30); resultados de pendientes (32) | Intentos fallidos, resultados de bulto pendiente por visita y fallos de retiro se muestran separados, con unidad. | OperacionesJornada Aplicada, identidad única; IntentoFallido/RetiroFallido cuentan intentos. EntregaBultos fallidos cuentan resultados por bulto/visita. Fecha física ocurridaEn en [desde,hasta), sin restringir admisión a ese período. Conflictos/repeticiones/evidencias no se suman como intentos. | Frecuencias y detalle paginado de visitas con autor/ruta/operación. Tests de replay y escenario de retiro existente ampliado. |
| «volumen por período» (30); «los reportes deben incorporarlo» (41) | Operaciones de entrega y retiro separadas, estado, bultos, peso kg, volumen m³ y resultados. | Una fila proyectada por operación; datos declarados de bultos: gramos/1000, cm³/1000000. No se cuentan documentos Mongo ni mensajes Kafka como operaciones. | Cortes Tipo y Resultado; detalle paginado ordenado por admisión, ID. |
| «recálculo de indicadores de cumplimiento» (4) | Consumidor de worker independiente, proyección PostgreSQL, reconstrucción y reconciliación por lotes. | Notificaciones por stream operativo/outbox existente; hechos antes de proyectar. Generación capturada transaccionalmente. Mensajes repetidos/viejos releen hechos aceptados y no hacen retroceder estado. SKIP LOCKED coordina consumidores; lecturas muestran pendientes y fechas. | ManagementReportingConsumer; GestionWorkerTests usa Kafka/PostgreSQL reales, mensajes invertidos, repetidos y reconstrucción. |
| «liquidación por comercio» (30); tarifa propia de retiro (41) | Borrador revisable → Confirmada o Descartada. Cada cargo se confirma una sola vez. Corte registrado al preparar. | Movimientos de TarifasEnvio: primer TotalFinalUyu, luego diferencias entre snapshots ordenados por CreadoEnUtc,Id. No sumar snapshots acumulados. Incluye recargo persistido de nueva visita; no vuelve a cobrar admisión. Todos los cálculos monetarios son numeric/decimal de dos decimales. | Liquidaciones y cuentas en Backoffice; preparación, detalle original, confirmación y descarte. Test de dos borradores concurrentes, reintentos, doble liquidación y corrección. |
| «consulta de su cuenta corriente y liquidaciones» (4) | Cuenta por comercio y operador, solo consulta para Commerce. Saldo operativo acumulado reconstruible, movimientos del período y documentos confirmados. | Suma de movimientos y correcciones; no existe en el dominio un registro de pagos/créditos bancarios. Confirmar no paga y no reduce saldo. No se representa un pago inexistente. | /cuenta en Commerce; Cuenta, Liquidaciones y detalles bajo sesión. Dos operadores y dos comercios, incluido uno con ambos operadores. |

La franja de cobertura es una disponibilidad semanal capturada; no fija por sí sola un día prometido. Se combina con el plazo publicado de modalidad, que sí fija el límite desde la admisión. Es una decisión de producto que reutiliza la semántica actual de RestriccionesTemporales y del tablero; no una exigencia literal del docente. Para retiro, el cumplimiento mide la recolección dentro de la franja solicitada. Su entrega al comercio es otro resultado visible y requisito para liquidarlo; no se inventa un plazo para ese segundo tramo.

## Reglas económicas y estados

La letra exige liquidaciones pero no determina cuándo se devenga cada cargo ni una regla de reintegro para cada desenlace. Decisión mínima: todo cargo persistido se muestra desde su registro; solo entra en un documento definitivo cuando la entrega está completa y validada, o el retiro llegó al comercio. Cancelación, devolución, extravío, operaciones abiertas y pruebas pendientes/vencidas quedan **retenidos**, con el motivo visible. No se inventan reintegros ni penalizaciones automáticos. Esto es una política prudente adoptada, no texto docente. Una operación sin cargo aplicado no genera un importe artificial.

`TarifasEnvio` ya es inmutable y guarda **snapshots acumulados**. `MovimientosCuenta` es una vista con invocador y RLS: cada versión aporta su diferencia respecto de la anterior del mismo envío. Mantiene importes originales, incluso cuando cambian tarifas/reglas actuales. El primer cargo puede contener recargos/bonificaciones del tarifario; ya están incluidos en su total original. Una nueva visita aporta solo el recargo persistido. Los movimientos de valor cero siguen siendo trazables.

Preparación: [desde,hasta) por fecha de registro del movimiento, y hasta el corte capturado. Incluye movimientos liquidables aún no reclamados. Cada línea congela identidad, operación, fecha, concepto, importe y JSON original (servicio, resultado, versión tarifaria, cobertura y total anterior). Máximo 1000 conceptos por documento; ante exceso se exige un período menor, sin truncar. Borradores no reservan cargos y pueden superponerse. Confirmación revalida sus conceptos, bloquea la cuenta y los envíos, reclama IDs con PK única y registra transición/actor/hora en la misma transacción. Un reintento del mismo documento devuelve su estado estable; un borrador competidor devuelve conflicto. El período y la identidad idempotente de preparación no se pueden reutilizar con otro contenido.

Una confirmada es inmutable, tanto cabecera como líneas y reclamos. No se descarta ni se edita. Una corrección requiere permiso de gestión, movimiento confirmado de esa cuenta, importe firmado con precisión monetaria, identidad idempotente y motivo de 10–500 caracteres. Se agrega un movimiento compensatorio fechado al registrarlo, liquidable en un documento posterior. Positivo agrega débito; negativo reduce saldo. El documento anterior conserva su total y detalle. No se agregan impuestos, facturación fiscal, pagos, comisiones ni conciliación bancaria.

## Lecturas, seguridad y recuperación

Application contiene contratos/casos de uso y resuelve el actor de la sesión; Domain valida transiciones y correcciones. Infrastructure ejecuta lecturas paginadas y comandos transaccionales; API aplica permisos y mapea errores. Portales conservan Razor Pages y Blazor, clientes HTTP tipados y tokens visuales compartidos. No hay una segunda tabla económica mutable: la vista se deriva de cargos originales y correcciones explícitas.

Permisos existentes separados: `envios.consultar` para lecturas y `envios.gestionar` para comandos. Reportes requieren actor operador; Commerce recibe su ComercioId desde la sesión. Un ID ajeno en la consulta es rechazado. Las liquidaciones de Commerce se limitan a confirmadas y al operador elegido. RLS forzado protege proyecciones, documentos, líneas, reclamos, transiciones y correcciones; API no tiene INSERT/UPDATE de documentos. Funciones definer restringidas revalidan identidad, pertenencia y permiso al escribir. Worker solo ejecuta la función de reconciliación; no adquiere privilegios globales ni escribe cargos.

GET del módulo usa una transacción RepeatableRead: totales, páginas y metadatos ven la misma fotografía. Las páginas conservan filtros y orden estable. Los motivos tienen criterio temporal independiente de las admisiones. Las tablas anchas tienen región local desplazable, sin desplazar horizontalmente la página.

El stream existente `nexoruta.operacion.v1` dispara `ManagementReportingConsumer` (grupo `nexoruta-management-v1`). Los triggers de hechos incrementan `GestionPendientes.Generacion` en la transacción de origen. La reconciliación bloquea filas pendientes por lotes, lee hechos canónicos y reemplaza solo sus filas derivadas. Una escritura concurrente queda pendiente en otra generación. Repetir o invertir notificaciones no cambia el resultado ni genera movimientos económicos. El heartbeat también reconcilia lotes limitados para recuperación de una notificación o un worker detenido. `GestionPendientes` conserva fecha y generación aplicada; el reporte distingue Actualizada/Atrasada/Indisponible y muestra la última reconciliación y pendientes.

Reconstrucción autorizada usando **la conexión restringida del worker** en una base sintética propia:

```sql
SELECT nexoruta_app.request_management_rebuild('<operador>'::uuid);
-- El consumidor recupera los lotes. Para un ensayo controlado sin broker:
SELECT nexoruta_app.reconcile_management(NULL,NULL,100);
```

Repetir el lote hasta devolver 0. No borrar tablas, historia, cargos, migraciones ni volúmenes. El SQL de reconstrucción no está expuesto a Commerce ni al rol API. Los índices cubren operador/fecha, comercio/zona, autor y pendientes; la agrupación y paginación ocurren en PostgreSQL, no cargando todos los envíos en cada petición. Mongo conserva su propósito documental previo y no decide importes.

## Demostración y evidencia

El escenario de `backend/tests/NexoRuta.IntegrationTests/Gestion/GestionScenario.cs` crea bases propias con el fixture PostgreSQL/PostGIS, dos operadores, dos comercios y otro repartidor. No recibe una conexión externa ni reutiliza sesiones anteriores. Genera hechos de entrega completa, parcial con segunda visita/recargo, intento fallido, cancelación, retiro completo, falta de compromiso y prueba pendiente. El mismo comercio opera con ambos operadores. Importes esperados calculados a mano: 110,20 + 145,40 + 110,20 + 110,20 + 75,10 + 110,20 = **661,30 UYU** para comercio A/operador A; liquidable **330,70 UYU** (4 movimientos). Operador B de ese comercio: **220,40 UYU**. Una corrección −10,25 deja **651,05 UYU** en la primera cuenta, sin alterar la liquidación confirmada.

Desde el conjunto integrado y sus gitlinks:

```bash
source scripts/cloud/env-agent.sh
# En entornos cuyo home es de solo lectura, usar caches propios:
export NUGET_PACKAGES=/workspace/.nexoruta-tools/nuget
export NUGET_HTTP_CACHE_PATH=/workspace/.nexoruta-tools/nuget-http
export DOTNET_CLI_HOME=/workspace/.nexoruta-tools/dotnet-home
export PLAYWRIGHT_BROWSERS_PATH=/workspace/.nexoruta-tools/browsers
export NEXORUTA_PLAYWRIGHT_MODULE="$PWD/scripts/cloud/node_modules/playwright"
export NEXORUTA_GESTION_E2E_DIR="$PWD/work/gestion-browser"
bash scripts/cloud/environment-install.sh
dotnet build frontend/NexoRuta.sln --no-restore
dotnet test backend/tests/NexoRuta.IntegrationTests --filter FullyQualifiedName~Gestion
```

El test de navegador inicia Kestrel/API con rol restringido y ambos portales reales, inicia sesiones sintéticas nuevas y ejecuta: operador → reporte → filtro → detalle por bulto → preparar → revisar → confirmar; comercio → cuenta → documento → otro operador → intento de ID ajeno. Capturas a 1440 y 320 px, teclado/foco/reflujo, aumento de texto y escaneo axe; resultados en el directorio indicado. La suite es parte del CI integrado, no una acreditación de Android. El escenario de worker usa Kafka real y la conexión limitada del worker. Los fixtures se crean y liberan con su propio ciclo de vida, sin tocar servicios compartidos.

Resultados ejecutados, SHAs finales y corridas: ver `evidencia.md`. No confundir compilación, HTTP, automatización y revisión visual; una prueba portable no acredita Android. Las cuentas sintéticas existen solo durante cada ensayo y su contraseña de fixture no es una credencial operativa.
