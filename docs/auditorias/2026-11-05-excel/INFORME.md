# NexoRuta frente al Excel: estado al 05/11/2026

**El núcleo transaccional funciona en el entorno local actualizado:** se ejecutaron por HTTP entrega completa, parcial y retiro, con persistencia real, rendición, cierre, reintentos idempotentes, seguimiento y consumo de avisos Kafka. **La entrega académica todavía tiene faltantes funcionales y de demostración.** No se acreditó aceptación visual/nativa ni puntos opcionales.

No se implementaron faltantes del producto, no se hicieron commits/push ni se modificó la planilla original. Se corrigieron exclusivamente dos carencias de preparación que impedían auditar: la clave inicial de evidencias y un topic nuevo de Kafka.

La comprobación definitiva de Git partió del principal local `f55bf1f`, no de una versión posterior a la integración indicada. Tras consultar GitHub, `origin/develop` resolvió a `4e5c233dc751736ed59cc234582f157f5c9c278a`, exactamente el antecedente indicado; se avanzó por fast-forward y se materializaron sus gitlinks `09538d9`/`d328e98`/`683766d`, sin moverlos a otras puntas. Los SHA completos están en el registro de entorno. No se modificó `main`.

## Leer primero

1. **[MATRIZ-FINAL.csv](MATRIZ-FINAL.csv)**: matriz consolidada, 104 filas, UTF-8 y separador `;`. Incluye los 93 registros originales y 11 ampliaciones identificadas expresamente como tales. No es una nueva versión del Excel original.
2. **[ACTUALIZACION-ENTORNO.md](ACTUALIZACION-ENTORNO.md)**: versiones, respaldo, migraciones, servicios, comprobaciones y correcciones de preparación.
3. **[HTTP-CIRCUITOS.md](HTTP-CIRCUITOS.md)**: recorridos ejecutados, rechazos, concurrencia, datos sintéticos, pasos de reproducción y límites.
4. **[COMPROBACION-MANUAL.md](COMPROBACION-MANUAL.md)** y **[ANDROID.md](ANDROID.md)**: pendientes exactos de interfaz/dispositivo y cómo continuar sin perder datos.

La fuente y sus diferencias están en [source-selection.md](source-selection.md). La evaluación detallada de código está en [auditoria-estatica.md](auditoria-estatica.md); esa fotografía **estática** conserva algunos pendientes anteriores al circuito HTTP. Para el estado consolidado prevalecen este informe, `MATRIZ-FINAL.csv` y [assessment-final.json](assessment-final.json), no los contadores intermedios de `assessment.csv/json`.

## Fuente utilizada y alcance íntegro

Se usó `docs/alcance/Calcs/Casos de Uso - Responsables.xlsm`, la copia local modificada del usuario, revisión interna 13 del 03/11. La copia en el checkout vecino tenía fecha de archivo posterior, pero contenido interno anterior e idéntico al versionado. No se encontró `Casos de Uso - Responsables(2).xlsm` en las ubicaciones revisadas; esa ausencia se deja documentada, sin afirmar que ambas copias sean la misma.

SHA-256 inicial y final de la planilla: `8de7fcf3c84c113788b71a89e5e51cc852aafd0e690a0d35f4b944e855220cf4`.

| Inventario original | Revisados |
|---|---:|
| CU obligatorios | 30 |
| Capacidades AP, separadas de los CU | 9 |
| Dependencias D | 24 |
| No funcionales NFR | 15 |
| Opcionales OPT, incluidos los descartados | 15 |
| Total original | **93** |
| Ampliaciones 31–36 y 37–41, fuera del Excel original | **11** |

Dos inconsistencias se conservaron sin editar la fuente:

- El encabezado dice que no hay opcionales seleccionados; las **filas** seleccionan seis y suman 14 puntos previstos.
- `No funcionales!F13`, NFR-10, contiene literalmente **«e»**. La obligación se precisa explícitamente con el enunciado original, `Laboratorio__NET_2026.pdf`, §6.10, página física 7: tablero SignalR autenticado/autorizado, aislado por tenant y funcional con varias API. No se inventa una obligación ni se sustituye silenciosamente la celda. Aclararla no bloquea el resto de la auditoría.

Los responsables se conservaron únicamente donde los indica la hoja Módulos. La matriz distingue esa asignación de módulo de una asignación individual por requisito; no se crearon responsables nuevos.

## Qué tenemos y qué no debe declararse terminado

Las dimensiones son independientes. **Completa** en implementación significa que la inspección del flujo y sus consumidores no identificó una brecha concreta del alcance; **no** significa que una pantalla o integración nativa se haya aceptado. La columna Verificación y la evidencia ejecutada deben leerse siempre juntas.

| Grupo | Implementación completa | Parcial | Ausente |
|---|---:|---:|---:|
| 30 CU | 22 | 5 | 3 |
| 9 AP | 3 | 2 | 4 |
| 24 D | 14 | 8 | 2 |
| 15 NFR | 4 | 9 | 2 |

No sumar estas cifras como porcentaje de avance: requisitos y dependencias tienen alcances distintos. Los opcionales descartados tampoco son trabajo obligatorio.

### Funcionamiento observado en cantidades normales

- Alta individual/API, cotización, bultos, recepción, configuración versionada de reglas/tarifas, repartidor/vehículo, planificación y despacho de fixtures nuevos.
- Entrega normal de un bulto; entrega parcial de uno de dos; retiro de un bulto hasta **EntregadoComercio**. Cuatro evidencias sintéticas cifradas y diez comandos distintos persistidos; tres reenvíos conservaron sus resultados sin duplicar comandos.
- Rendición y cierre no se confundieron con recepción física/liberación: el vehículo no pudo liberarse hasta recibir el pendiente en depósito. La protección se respetó y después la liberación funcionó.
- Dos carreras devolvieron **200 + 409**; una nueva asignación incluyó solamente el bulto pendiente. Se comprobaron peso inválido 400, acceso anónimo 401, permisos insuficientes 403 y acceso de otro comercio 404 sin cambios indebidos.
- Tres enlaces públicos reales, avance parcial sin IDs internos y **28 avisos de los tres envíos del circuito** en la bandeja Kafka del comercio. Esa bandeja no equivale al webhook HTTP firmado exigido.

Estas ejecuciones aportan evidencia a varios CU, no aceptación completa de todos ellos. No se ejecutaron mediante formularios de negocio del navegador ni mediante sensores Android.

### Qué tenemos a medias

- **CU-01:** existe gestión de organizaciones/usuarios/roles, pero el modelo vigente de plataforma/autogestión no coincide literalmente con la administración de comercios por el operador del Excel. Requiere aceptación académica; no se propone cambiar permisos silenciosamente.
- **CU-16:** orden manual preservado y estimación sobre ese orden; falta justificar/documentar el criterio razonable pedido. No se exige optimización ni activar OPT-12.
- **CU-23/CU-29:** ubicación y piezas operativas existen, pero falta el tablero vivo completo del despachador; segundo plano/batería nativos no quedaron demostrados.
- **CU-30:** reporte por tipo/estado, bultos e importe disponible; no sustituye cumplimiento por zona/repartidor/comercio, motivos y liquidación/cuenta corriente.
- **AP-01/AP-04:** hay piezas de incidencias/devolución operativa, no el ciclo general completo de resolución y gestión por el comercio.

### Qué falta implementar, por inspección

| Faltante concreto | Requisitos vinculados | Dependencia/impacto para la entrega |
|---|---|---|
| Solicitud pública de reprogramación por destinatario; la reprogramación privada del operador no la sustituye | CU-26, D16 | Completa el circuito del enlace público |
| Aviso final al destinatario tras entrega confirmada, incluida sincronización offline | CU-27, D17/D24 | Debe nacer del resultado confirmado, sin duplicación |
| Suscripción por comercio/evento, webhook HTTP firmado, reintentos, fallidos, historial y reenvío | CU-28, AP-05, NFR-09, D18; ampliaciones36/41 | Kafka/bandeja son insumos, no el contrato externo exigido |
| Tablero vivo de posición/riesgo y canal SignalR de negocio con aislamiento y varias API | CU-29, NFR-10, D19–D21 | Requiere eventos/proyecciones y demostración multinstancia |
| Reportes completos, liquidación y cuenta corriente del comercio | CU-30, AP-06, D22–D23 | Requiere datos/cargos/historial trazables; sumar tarifas no es liquidar |
| Ventana estimada pública | AP-07 | La planificación dispone de horas, pero el DTO/pantalla públicos no las exponen |
| Cierre diario automático del worker | AP-09 | Debe ser idempotente/único; FinJornada manual no lo acredita |

Cada fila de la matriz contiene el requisito literal, qué existe, brecha, referencias `path:line`, próxima acción y prioridad. Los hallazgos de ausencia son **inspección**, no supuestos recorridos de UI ejecutados. Los procedimientos de confirmación se indican en la guía manual.

### Fichas de confirmación de brechas funcionales

Estas fichas **no afirman reproducción visual**: describen precondiciones/pasos para confirmar el comportamiento cuando se habilite la UI, y el resultado observado por inspección ahora. Las referencias exactas están en la fila de la matriz.

| Requisito | Precondición y pasos de confirmación pendientes | Esperado | Observado por inspección |
|---|---|---|---|
| CU-26 | Envío sintético con enlace válido y estado que permita reprogramar; abrir como destinatario y solicitar otra visita | Solicitud validada, persistida y tratada por operación | Tracking/controlador público no ofrecen la solicitud; existe solo reprogramación privada con permiso `envios.gestionar` |
| CU-27 | Entrega sintética confirmada por sincronización; revisar receptor local y repetir mismo comando | Aviso final al destinatario, una sola vez | No se encontró flujo completo de ese aviso; seguimiento e inbox no lo sustituyen |
| CU-28/AP-05/NFR-09 | Comercio con envío; configurar evento y receptor HTTP local, provocar cambio, simular error y pedir reenvío | Suscripción, firma verificable, historial, reintentos/fallidos/reenvío | Existe outbox/Kafka/bandeja; no se encontró el circuito externo completo |
| CU-29/NFR-10 | Dos operadores y dos API autorizadas; actualizar posición/riesgo y reconectar tablero | Actualización viva aislada por tenant y continuidad multinstancia | No se encontró hub/tablero de negocio que cumpla ese alcance |
| CU-30/AP-06 | Operaciones sintéticas finalizadas con cargos distintos; filtrar por zona/repartidor/comercio y abrir liquidación/saldo | Indicadores, motivos y liquidación/cuenta corriente trazable | Reporte agrupa solo tipo/estado y suma importes; no hay esos libros/dimensiones completos |
| AP-01/AP-04/AP-07/AP-09 | Crear incidencia/devolución propia; abrir seguimiento; observar cierre automático de fecha operativa sintética | Resolver/gestionar, mostrar ETA y ejecutar job diario único | Solo piezas operativas de incidencia/devolución; faltan gestión Commerce, ETA pública y servicio automático de cierre |

## Las nueve capacidades adicionales

| ID y nombre | Implementación | Pendiente principal |
|---|---|---|
| AP-01 Gestión de incidencias | Parcial | Ciclo general de registro/resolución Backoffice |
| AP-02 Etiquetas | Completa por inspección | Impresión real y lectura/consistencia del código |
| AP-03 Consulta del comercio | Completa por inspección | UI completa; el aislamiento HTTP sí se ejercitó |
| AP-04 Devoluciones del comercio | Parcial | Gestión propia en Commerce; retiro no equivale a devolución |
| AP-05 Suscripción de avisos | Ausente | Configuración por evento y sistema receptor |
| AP-06 Cuenta corriente | Ausente | Movimientos, saldos y liquidaciones consultables |
| AP-07 Ventana estimada | Ausente | Exposición pública del rango estimado |
| AP-08 Navegación de ruta | Completa por inspección | Lista/parada/retorno en Android; no se agrega exigencia giro a giro |
| AP-09 Cierre diario | Ausente | Job automático con unicidad e idempotencia |

## No funcionales: implementación local no es demostración remota

Los quince NFR tienen fila individual. NFR-01 y NFR-04 se comprobaron en su alcance local con builds, arquitectura, migraciones, SQLite y concurrencia; NFR-05/06 tienen implementación inspeccionada, pero su demostración integral sigue pendiente. Seguridad, mensajería, observabilidad y calidad tienen controles existentes, no una certificación completa por tener paquetes o contenedores.

- **NFR-07:** Redis consume identidad visual y tarifas publicadas; faltan pruebas completas de invalidación/perfiles/métricas y distribución. **Solo se auditó: no se implementó ni invadió el trabajo de los compañeros.**
- **NFR-08/09:** el circuito local publicó/consumió mensajes; eso no acredita todos los reintentos/fallidos/reenvíos ni avisos HTTP firmados.
- **NFR-11:** MAUI, almacenamiento y pruebas portables existen; cámara, escáner, firma, GPS/segundo plano y ciclo actualizado permanecen bloqueados para aceptación nativa.
- **NFR-12/13/14/15:** falta completar/demostrar observabilidad extremo a extremo, varias API balanceadas y continuidad/jobs únicos, despliegue remoto/IaC/costo y cobertura de todos los controles en pipeline. No se ejecutó GCP ni CI remota.

Se consultaron los cuatro commits exactos en GitHub mediante el conector disponible: no identificó una ejecución utilizable, pero limita eventos/paginación y no enumera todos los check-runs. **No se concluye que no exista CI.** [CI-REMOTA.md](CI-REMOTA.md) deja el alcance, commits consultados y prueba concreta faltante para E2E/cobertura/calidad.

## Opcionales seleccionados y puntos

| ID | Seleccionado | Puntos previstos | Qué impide acreditarlo hoy |
|---|---|---:|---|
| OPT-03 Kafka para eventos de flota | Sí | 3 | Los avisos de operación/bulto funcionan; faltan eventos de flota, varios consumidores y reconstrucción por replay demostrados |
| OPT-05 NoSQL para historial y analítica | Sí | 2 | Mongo se usa para recuperación de contraseña, no para el historial/analítica paginado y filtrable pedido |
| OPT-06 Pruebas de carga automatizadas | Sí | 2 | Hay escenarios/runner/workflow; faltan resultados en el ambiente remoto y sincronización simultánea exigidos |
| OPT-07 Cobertura de pruebas | Sí | 2 | Hay suites/collector, no medición >70% Domain/Application publicada por pipeline |
| OPT-08 Pruebas extremo a extremo | Sí | 2 | Implementación de tests/pipeline inspeccionada; cinco pruebas opt-in de navegador omitidas y sin aceptación CI vigente |
| OPT-09 Notificaciones remotas en producción | Sí | 3 | FCM implementado/antecedentes históricos; falta app cerrada en producción y ciclo real de IDs; NoSend no acredita push |
| **Total** | **6** | **14** | **0 puntos completos acreditables con esta evidencia** |

Los otros nueve opcionales conservan su decisión **descartada**. No se pide implementarlos ni se cuentan sus puntos. Cero acreditados significa falta de evidencia/condiciones completas para otorgarlos, no ausencia de toda infraestructura.

## Ampliaciones: parcial 31–36 y retiro37–41

No se crearon CU-31 a CU-41 del Excel. `EXT31`–`EXT41` son rótulos locales de navegación; se conservan número/texto/página del PDF y se vinculan los CU originales en una columna separada.

| Ampliación | Qué se comprobó ahora | Qué queda |
|---|---|---|
| 31–35 Entrega parcial | Resultado1/2, prueba por entregado, regla publicada, pendiente rendido/recibido y selección exclusiva en revisita; progreso público | Escáner/offline/captura nativos, políticas alternativas y recargo de revisita ejecutado; seis integraciones PostgreSQL adicionales aportan parcial/segunda visita |
| 36 Avisos por bulto/versionado | Contrato v2 en outbox, topic, consumo y bandeja del comercio | La exigencia de comunicación a sistemas de comercio sigue incompleta sin webhook firmado |
| 37–40 Retiro | Solicitud API, tarifa, ruta mixta, prueba sintética con foto/firma, estados, recepción y entrega al comercio | Formulario real y adaptadores Android/offline; no se sustituyen por payloads PNG |
| 41 Superficies del retiro | Tarifa, seguimiento y avisos internos observados; reporte tipo/estado inspeccionado/servido | Tablero, reporte completo/liquidación y comunicación externa |

Las observaciones históricas de sobres/acuses y cantidades1500/2000 son secundarias y **no** se usaron como bloqueos generales. Se priorizaron cantidades normales; el filtro de integración no ejecutó esos escenarios de carga.

## Evidencia por método

| Método | Resultado nuevo | Límite explícito |
|---|---|---|
| Compilación | API/Worker, solución frontend y Android x64 correctos | Advertencias documentadas; compilar no acredita el negocio |
| Tests | Backend336 unitarias +4 arquitectura +6 integraciones; frontend491; Mobile224: **1061 pasan** | Cinco pruebas frontend opt-in omitidas; no se ejecutó toda la suite de integración backend |
| Fallo de invocación de tests | Primer frontend490/1/5: raíz externa de artefactos impedía encontrar fuente | Repetición con fuentes idénticas y ascendencia correcta491/0/5; no se corrigió producto |
| HTTP/API/persistencia | 153 solicitudes documentadas por el circuito y comprobaciones SQL; sesiones/roles y aislamiento | No acreditan una pantalla |
| Portales HTTP | Login y nueve rutas SSR auténticas200 sin errores SSR reconocidos | No hay navegación visual ni formularios de negocio ejecutados en navegador |
| Android | APK actualizado `install -r`, firma/UID conservados, seis archivos persistentes idénticos | App actualizada no abierta; cámara/escáner/firma/GPS/reapertura actualizada no aceptados |
| Navegación/visual | **Bloqueada**: host de navegador indisponible y Brave/qemu no aprobados | Se solicitó habilitación; no se eludió mediante otro controlador |
| Histórica | Documentación previa leída como antecedente | Sus pruebas no se adjudican a esta ejecución |

## Preparación corregida, preservación y siguiente arranque

1. Evidencias: PUT503 por clave ausente → primera clave dedicada persistente, con cero evidencias anteriores → mismo UUID/cuerpo204 y una sola fila cifrada.
2. Avisos: outbox `UnknownTopic`, bandeja vacía → solo topic nuevo `nexoruta.comercios.v2` con los parámetros del Compose vigente → reintento natural, publicación y consumo únicos. No se borraron topics ni movieron offsets.

Se preservaron PostgreSQL/volúmenes, cuentas, `.env`, certificados, claves previas, las rutas `01A1AA` del jueves05 y Nico del lunes09, recursos `CU06-LOCAL-V`, planilla y almacenamiento Mobile. [La verificación independiente](VERIFICACION-PRESERVACION.md) comparó claves originales del respaldo contra la base actual; solo dos outbox antiguos avanzaron metadatos normales de procesamiento, sin pérdida de filas. No hubo restauración destructiva. Decodificar el respaldo no equivale a un simulacro completo de restauración.

**Conservar el override privado de esta auditoría para reiniciar.** La invocación efectiva está en `.local/auditoria-excel-20261105/compose-command.json`; incluye las capas privadas habituales y la clave persistente de evidencias. No volver al `.bat` omitiendo ese override: reaparecería el503. No publicar `.local`, respaldos o credenciales. Los servicios quedan levantados y saludables; la app Android actualizada queda detenida para no forzar una transición de identidad.

## Orden recomendado para terminar la entrega

1. **Obligatorios pendientes:** cerrar M05 (reprogramación/avisos externos y destinatario) y M06 (tablero, reportes/liquidación/cuenta corriente, cierre diario), con las dependencias de la matriz.
2. **Capacidades y decisiones:** resolver incidencias/devoluciones/ETA, aceptar explícitamente la desviación CU-01 y documentar el criterio CU-16 sin convertirlo en optimización.
3. **Demostrar lo existente:** habilitar revisión visual/nativa segura, completar recorridos del profesor, dos operadores/instancias, fallidos/reintentos/observabilidad y entorno remoto exigido. No sustituirlos por este informe.
4. **Acreditar opcionales seleccionados:** priorizar las condiciones completas de los seis; medir/publicar resultados antes de sumar puntos.

No se asignaron tareas nuevas a personas ni se publicó nada. Engram rechazó guardados/resúmenes por sesión host no registrada; toda la continuidad queda en estos archivos locales.

La eliminación de dos scratch propios fuera del repositorio fue rechazada por la política de ejecución y no se reintentó por otro mecanismo: `%TEMP%/nexoruta-static-audit.py` y `%TEMP%/nexoruta-preservation-a111794078d941f79507877ac1cdd1ad/`. No son entregables ni cambios del producto. Se conservan deliberadamente los respaldos, claves privadas y artefactos Android de continuidad en sus directorios privados.

Risk: items1,2,5 por migraciones autorizadas y preparación local de secretos/servicios. No cambió código del producto; hay respaldo y verificación independiente. La aceptación visual/nativa y remota sigue pendiente.
