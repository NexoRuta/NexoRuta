# Evidencia ejecutada: gestión, liquidaciones y cuenta

Entorno: Codex Cloud Linux; servicios, datos y sesiones sintéticos propios. No se usaron Windows, respaldos, bases compartidas, sesiones manuales previas ni servicios facturables de mapas. No se ejecutó despliegue, apply/destroy, operación de VM ni merge a develop/main.

## Fuentes y SHAs

Fetch inicial de develop: `6001eb5cf6dba189f2be4d4777459b5bb554e7c9`. Gitlinks de partida: backend `d7b1a3ee2c9fdbd023158b299342530d6f7e2f77`, frontend `a2118d8f74759425af1a1a69d12c7bc2693e4d07`, mobile `53f6be2cdec48f48e30e390060feeaefb5be0ead`. Checkouts hermanos originales preservados. Se leyeron AGENTS, continuidad Cloud, DESIGN y ambos PDF normativos.

Durante el trabajo avanzó develop a `14a17b67d6a61be8bf56d52bc026fd9e63458896`, exclusivamente con límite de memoria del provisionador Mongo y su prueba. Sus gitlinks son idénticos a los iniciales; se preserva ese cambio de infraestructura al integrar la rama de revisión, sin ejecutar despliegues.

Gitlinks de la entrega:

| Componente | SHA exacto | PR hacia develop |
| --- | --- | --- |
| Backend | `7c2ddb8657cd791195aba2f7c9e4dd1f54ee1cfb` | [Backend #53](https://github.com/NexoRuta/NexoRuta-Backend/pull/53) |
| Frontend | `fa94588955c9de877190b411ae6543fd4c3e9b98` | [Frontend #52](https://github.com/NexoRuta/NexoRuta-Frontend/pull/52) |
| Mobile | `53f6be2cdec48f48e30e390060feeaefb5be0ead` | Sin modificación |

El frontend fija como productor de contrato `981cb4a9a26096516268f609f51e7b460c98ec1b`. El posterior `7c2ddb8` solo fija en CI el companion frontend exacto; no cambia código del producto. La raíz integra los gitlinks de la tabla. Su SHA final se identifica en los checks de la PR principal y con `git rev-parse HEAD`, evitando intentar contener su propio hash en el commit.

## Comprobaciones locales

| Verificación | Resultado ejecutado |
| --- | --- |
| Backend Debug y Release | Compilación aprobada |
| Frontend completo | Compilación aprobada |
| Dominio/unidad backend | 367 aprobadas |
| Arquitectura backend | 7 aprobadas, incluyendo independencia de Domain/Application y contratos HTTP de gestión propios de API |
| Integración focalizada final | 10 aprobadas, 0 omitidas: 5 nuevas de gestión + 5 escenarios existentes de retiro ampliados |
| Frontend con contrato OpenAPI servido por API real | 513 aprobadas; 5 escenarios históricos opt-in sin activar en esta invocación local, habilitados por sus variables en CI integrado |
| Migración/roles estilo Cloud SQL | Cadena con NOSUPERUSER/CREATEROLE/CREATEDB, roles runtime, bootstrap repetido, RLS forzado, aislamiento de key rings y cuota compartida: aprobados en PostgreSQL local desechable |
| Retiro fallido | Se verifica como FalloRetiro y no como IntentoFallido de entrega |
| Pruebas Python del superproyecto (incluido monitor del nuevo grupo) | 237 aprobadas y 3 omitidas por condiciones existentes (240 descubiertas); servicios externos simulados, sin operaciones de VM |
| Mapas | Sin consumo real; transporte controlado en los escenarios existentes de retiro/routing |

Pruebas principales: `GestionCircuitTests`, `GestionWorkerTests`, `GestionBrowserTests`, `ManagementBoundaryTests`, `LiquidacionRulesTests` y la ampliación de `OperacionesRepartoHttpTests.Retiros`.

Se verificaron cantidades, denominadores, autoría de dos visitas parciales, filtros/páginas y límites temporales; franja nocturna en America/Montevideo con inicio inclusivo/fin exclusivo; cargos originales y recargo de 25 UYU; tarifas/reglas y perfil de repartidor modificados después sin alterar historia; dos confirmaciones competidoras, reintento, prevención de doble liquidación, documento estable y corrección compensatoria; consulta sin gestión, RLS, IDs manipulados y dos operadores/dos comercios con un comercio compartido. La migración sobre hechos anteriores conserva los cargos. Kafka real entrega notificaciones repetidas e invertidas y reconstruye con rol worker restringido, sin generar efectos económicos.

Resultados esperados independientes: comercio A/operador A 661,30 UYU; liquidable 330,70 UYU en cuatro conceptos; comercio A/operador B 220,40 UYU; corrección −10,25 deja saldo 651,05 sin modificar el documento confirmado. Entregas: 7 operaciones/8 bultos para operador A (incluido otro comercio), 2 cumplidas, 2 incumplidas, 1 sin compromiso, 1 con prueba pendiente y 1 no evaluable; denominador 4. Retiro: 1 operación cumplida. Segunda persona de la entrega parcial: exactamente su bulto, incumplido.

## Navegador y revisión visual

Se arrancaron Backoffice Razor, Commerce Blazor y API/Kestrel reales con PostgreSQL/PostGIS y rol API sin privilegios globales. Sesiones nuevas y separadas. Recorrido ejecutado: reportes → conservar filtros → detalle de bultos y autores → cuenta → preparar → revisar cuatro conceptos → confirmar → Commerce consulta documento/movimientos → cambia operador → intenta documento ajeno; un segundo comercio también queda bloqueado.

Se probaron seis vistas a 1440 y 320 px (12 comprobaciones), sin desbordamiento horizontal de página; tablas con desplazamiento local. Teclado, enlace de salto, foco visible y texto al 200 %. El retraso real del API de fixture activa carga en Commerce; el ID ajeno activa el estado de error. Axe no encontró incidencias en esas vistas. Se inspeccionaron capturas reales de confirmación de escritorio y cuenta de Commerce/operador a 320 px; esto es evidencia visual, separada de build/HTTP y sin afirmar certificación WCAG completa.

La prueba guarda `acceptance.json` y PNG en subdirectorios por ejecución de `NEXORUTA_GESTION_E2E_DIR`; key rings quedan en un directorio temporal aparte y no se publican como evidencia. El CI integrado adjunta los JSON/PNG de gestión junto con los TRX del shard correspondiente. No se acredita Android con estos ensayos ni con pruebas portables.

## CI y revisión

[PR principal #75 y checks integrados por SHA](https://github.com/NexoRuta/NexoRuta/pull/75/checks).

- [Corrida backend](https://github.com/NexoRuta/NexoRuta-Backend/actions/runs/42430219281).
- [Corrida frontend](https://github.com/NexoRuta/NexoRuta-Frontend/actions/runs/42430222723).
- La PR principal publica el resultado integrado por SHA y los artefactos de las corridas. No se usa el verde de develop como sustituto del CI de esta entrega.

El procedimiento reproducible está en `reportes-liquidaciones-cuenta.md`. Los resultados del control Cloud general y del CI integrado se registran en los checks de la PR, además de los ensayos focalizados anteriores.

## Límites explícitos

No existe un registro de pagos en el dominio actual: el saldo es operativo, no una conciliación bancaria. La letra no determina reintegros/cobros definitivos para cancelaciones, devoluciones y extravíos; esos conceptos y los de operaciones/pruebas pendientes están visibles y retenidos. Confirmar no paga. Una confirmada se corrige solo con movimiento compensatorio trazable. Máximo 1000 conceptos por documento, sin truncamiento silencioso. No se agregaron fiscalidad, impuestos, pasarelas, webhooks, push, cierre diario general ni modificaciones móviles. Las revisiones nativas/operativas ajenas a este alcance siguen pendientes según continuidad anterior.
