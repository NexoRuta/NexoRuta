# Envíos — decisiones funcionales y diseño de historia inmutable

> **Estado vigente:** la historia canónica, DEC-01 opción B, DEC-04 opción A, DEC-05 opción A y DEC-06 opción B están implementados en los bloques 13–17. DEC-05/06 requieren el rol administrativo protegido del operador o el rol protegido `despachador_operador`, más `envios.gestionar`; `usuario_operador`/roles personalizados no califican por el permiso solo. DEC-07, CU-08, cliente offline y el resto de la máquina siguen pendientes. La revisión nativa continúa pendiente.

**Corte:** 25/10/2026  
**Alcance original:** aclarar el fallo de Reparto y preparar decisiones/diseño para las transiciones conectadas; al corte no implementaba temporizadores, extravío, nuevos estados, CU-08 ni el historial propuesto.  
**Control nativo:** sigue pendiente; este documento y la revisión manual no son aprobación nativa.

## 1. Fuentes consultadas

| Fuente | Referencia utilizada |
|---|---|
| `docs/alcance/Laboratorio__NET_2026.pdf` | p. física 4 / impresa 3, §5.1 req. 4 (reglas, intentos, evidencia y plazos); p. física 5 / impresa 4, §§5.2–5.4 reqs. 8, 10–12 y 18–24 (bultos, recepción, máquina explícita, historia inmutable, prueba, intentos, devolución y offline); p. física 5 / impresa 4, reqs. 27–28 (avisos); p. física 6 / impresa 5, §§6.4–6.6 (concurrencia, aislamiento y versionado). |
| `docs/alcance/Calcs/Casos de Uso - Responsables.xlsm` | Inspeccionado directamente como ZIP/XML, sin ejecutar macros. Hojas enumeradas: `Módulos`, `CU obligatorios`, `Alcance aplicaciones`, `Dependencias`, `No funcionales`, `Opcionales`. `CU obligatorios!A14:I15` CU-11/12; `A21:I27` CU-18–24; `A30:I31` CU-27/28. `Dependencias!A6:I6` D03, `A9:I9` D06, `A11:I17` D08–D14 y `A20:I21` D17/D18. No se usó un valor vacío de caché de fórmula como requisito; las filas citadas contienen valores almacenados. |
| `docs/alcance/Diagramas/Maquina-De-Estados-Propuesta.pdf` | Página 1: transiciones, vencimiento de prueba, intento/reprogramación, devolución y extravío; la propia figura está identificada como propuesta. |
| `docs/alcance/Diagramas/maquina-estados-envio-corregida.png` | Inspección visual directa. Añade la regla transversal de Cancelado terminal, permitido solo desde los siete estados indicados en el pedido previo. No muestra salidas desde Entrega sin validación. |
| `backend/docs/cu/CU-04-reglas-operativas.md` | D03/versiones asociadas al envío; semántica de intentos, reprogramación, intervalo, máximo, `DecisionOperativa` e `IniciarAutomaticamente`. Distingue ejemplos de configuración de valores predeterminados y marca estas definiciones como decisiones del equipo, no texto literal del taller. |
| `backend/docs/cu/cierre-jornada.md` | D18 conserva sus reglas de cierre, incidencias y custodia; su cláusula anterior sobre prueba pendiente fue reemplazada por DEC-01 opción B. Véase el documento actualizado y el informe 14. |
| `backend/docs/cu/CU-08-bultos.md`, `backend/docs/cu/destinos-envios.md` | CU-08 obligatorio y separado, cobertura actual de un bulto y confirmación de destino previa a planificar. |
| `docs/auditorias/envios/11-matriz-transiciones-y-brechas.md`, `docs/auditorias/cu07/07-bloque-cancelacion-terminal.md` | Evidencia y límites de la matriz previa y de la regla terminal, respectivamente; se preservan sus alcances. |

## 2. Resolución del fallo de Reparto

### Qué esperaba la prueba

`OperacionesRepartoHttpTests.EvidenciaCifradaEsInmutableYCompletaLaPruebaAutomaticamente` preparaba una ruta y carga, podía cancelar el envío en el servidor mientras la operación estaba pendiente, y luego enviaba:

1. `EntregaFisica` con una versión offline anterior.
2. La subida repetida de una foto cifrada e inmutable.
3. `EvidenciaEntrega` con foto, receptor y ubicación.
4. El reintento de la misma operación de evidencia.

La aserción que esperaba `Aplicada` para la operación de evidencia era compatible con conservar el hecho y su prueba. La aserción posterior que esperaba `Entregado` no lo era: `Cancelado` no puede reactivarse.

### Causa confirmada

El bloque 07 ya había probado que una `EntregaFisica` offline tardía puede fijar `EntregaFisicaEnUtc`, entregar la custodia física al destinatario y dejar `Estado = Cancelado`. También verificó el replay de esa misma operación sin repetir efectos. La prueba que falló iba un paso más allá: primero conciliaba el hecho sin prueba completa y luego enviaba una operación separada `EvidenciaEntrega`.

`EfOperacionesRepartoRepository.Ejecucion.cs` aceptaba `EvidenciaEntrega` únicamente cuando el estado actual era `EntregaPendienteValidacion`. Como la conciliación correcta conserva `Cancelado`, el segundo comando terminaba como `Conflicto` y no asociaba la evidencia subida a `PruebaEntrega`. Por eso había un defecto de producción en la conservación de la prueba, además de una expectativa incorrecta sobre el estado final.

### Corrección acotada

- `Envio.RegistrarPruebaTardiaTrasCancelacion` permite avanzar la versión solo si el estado sigue `Cancelado`, existe `EntregaFisicaEnUtc` y coincide la versión esperada. No cambia el estado.
- La rama nueva de `EvidenciaEntrega` exige que todos los bultos del envío estén bajo custodia del destinatario y que la custodia conserve el repartidor y ruta originales; reutiliza `AplicarPrueba`, que valida las evidencias y su pertenencia.
- La operación completa conserva el estado `Cancelado`; registra prueba, versión y fila de operación en la transacción existente. La operación repetida con el mismo ID/hash recupera el resultado almacenado y no vuelve a ejecutar escrituras.
- La ruta normal `EntregaPendienteValidacion → Entregado` no cambió. Sin hecho físico conciliado, con otra custodia o desde otra ruta, el servidor continúa rechazando la operación; no se convierte cualquier conflicto en éxito.
- No se creó una migración, endpoint, tipo de outbox ni transición `Cancelado → Cancelado`.

### Evidencia de ejecución

Docker se inspeccionó en modo de solo lectura: `docker context show` → `desktop-linux`; el endpoint reportado fue `npipe:////./pipe/dockerDesktopLinuxEngine`. `PostgresFixture` crea bases efímeras aleatorias en el contenedor.

| Check | Resultado | Alcance |
|---|---:|---|
| En rojo, tras actualizar la expectativa de la prueba | 1 caso normal pasó; los dos casos con cancelación fallaron porque la evidencia recibía `Conflicto` en vez de `Aplicada`. | Confirmó el defecto, tanto con API normal como con rol restringido. |
| `dotnet test tests/NexoRuta.IntegrationTests/NexoRuta.IntegrationTests.csproj --no-restore --filter 'FullyQualifiedName~EvidenciaCifradaEsInmutableYCompletaLaPruebaAutomaticamente' --logger 'console;verbosity=minimal'` | 3/3 | Flujo normal, cancelación terminal y variante con API conectada mediante rol PostgreSQL restringido. Verifica estado, instante físico, custodia, prueba cifrada, versión y replay sin duplicar operación. |
| `dotnet test tests/NexoRuta.IntegrationTests/NexoRuta.IntegrationTests.csproj --no-restore --filter FullyQualifiedName~NexoRuta.IntegrationTests.Reparto --logger 'console;verbosity=minimal'` | 39/39 | Suite Reparto completa con PostgreSQL efímero; incluye la nueva variante restringida. |
| Filtro de ocho regresiones autenticadas, públicas, de rollback, RLS y carreras descrito en 11 | 21/21 | PostgreSQL efímero. Incluye matriz terminal, rollback estado/historial/outbox de cancelación, operación offline tardía y concurrencia. |
| `dotnet test tests/NexoRuta.UnitTests/NexoRuta.UnitTests.csproj --no-restore --filter FullyQualifiedName~EnvioCancellationRulesTests --logger 'console;verbosity=minimal'` | 27/27 | No regresión unitaria de las reglas de cancelación terminal. |

Son pruebas TestServer con PostgreSQL real, no un Kestrel expuesto por socket ni un recorrido de navegador. No se publicaron ni consumieron brokers. Ninguna prueba utilizó una base compartida o de producción; el setup del escenario usa el contexto de dueño del fixture, pero las llamadas HTTP de la regresión se ejecutaron además con el rol API restringido `NOSUPERUSER NOBYPASSRLS`.

## 3. Decisiones funcionales: qué está resuelto y qué falta

### Decisiones que sí están documentadas

- **Reglas por envío:** D03 (`Dependencias!A6:I6`) establece que los estados de intento, devolución y plazo usan la versión de reglas asociada al envío. El código carga `Envio.VersionReglasId`; una publicación posterior no debe reemplazar el snapshot del envío.
- **Intento frente a reprogramación:** CU-04 define una visita física con resultado como intento; volver a enviar el mismo ID es idempotente; reprogramar no crea intento, no reinicia contador ni desplaza el intervalo. El máximo y el intervalo son los de la versión aplicable. Los ejemplos de tres intentos/24 horas documentados allí no son valores predeterminados universales.
- **Agotamiento:** con `IniciarAutomaticamente`, la última falla inicia `EnDevolucion`; con `DecisionOperativa`, no se habilita otro intento y el envío queda `NoEntregado` hasta la acción humana confirmada en DEC-05 opción A. Esta decisión del proyecto permite que administrador del operador o despachador autorizado inicie devolución con motivo, sin cambiar custodia; se implementó en el bloque 16.
- **Destino:** Commerce confirma destino mientras el envío está `Admitido`; planificación rechaza una dirección sin coordenadas confirmadas (`backend/docs/cu/destinos-envios.md`, `EfRutasRepository.PlanificarAsync`). La importación no confirma destinos automáticamente.
- **Cancelación:** la decisión definitiva del pedido anterior prevalece sobre los diagramas: siete orígenes habilitados, cinco prohibidos; Cancelado es terminal. Un hecho físico tardío no permite otra transición.
- **CU-08:** es obligatorio y separado. El alta crea actualmente un bulto, no uno o más; esta auditoría no presume una regla de agregación que todavía no se haya definido.

### Preguntas funcionales pendientes

DEC-01, DEC-02 y el alcance de plazo de DEC-03 quedaron resueltos por la decisión explícita del usuario y el bloque 14. DEC-04 opción A se resolvió e implementó en el bloque 15. DEC-05 opción A quedó confirmada e implementada en el bloque 16; su fila conserva las alternativas históricas solo para explicar qué quedó reemplazado. DEC-06 a DEC-08 siguen siendo preguntas funcionales; las recomendaciones de esas filas no están aprobadas.

| ID / transición | Fuente y comportamiento actual | Qué falta definir y alternativas | Recomendación (no aprobada) y qué depende de ella |
|---|---|---|---|
| **DEC-01 — `EntregaPendienteValidacion → EntregaSinValidacion` — RESUELTA (opción B)** | El diagrama propone vencimiento temporal. La cláusula original D18, según la cual cerrar jornada cambiaba estado, fue reemplazada solo en ese punto. | `FinJornada` conserva Pendiente. Una prueba completa recibida con hora UTC del servidor estrictamente anterior al vencimiento puede producir Entregado; un Worker durable produce EntregaSinValidacion cuando `now >= vencimiento`. | Decisión confirmada e implementada; detalle, código y evidencia en el informe 14. No crea salidas desde EntregaSinValidacion ni altera el resto de D18. |
| **DEC-02 — duración/versionado — RESUELTA** | Los plazos Estándar/Urgente continúan siendo compromisos comerciales y no se usan como plazo de evidencia. | La duración es `PlazoValidacionPruebaMinutos`, positiva y configurable por operador, asociada a la versión inmutable fijada en el envío. No se fija un default; nuevas publicaciones incompletas no se publican. Para una versión histórica nula no se inventa duración ni se vence automáticamente; queda identificable como pendiente de política histórica. | Implementado y visible en edición/consulta de publicaciones. La migración es nullable/aditiva para conservar versiones previas; informe 14. |
| **DEC-03 — inicio/offline/evidencia tardía — RESUELTA en el alcance del plazo** | La operación conserva el instante físico del dispositivo y la primera recepción válida del servidor; no son intercambiables. La conciliación tardía sobre Cancelado continúa como hecho sin transición ni deadline. | El plazo empieza al aceptar por primera vez el hecho físico: `first receipt UTC + duration from shipment rule version`. Replay, evidencia parcial, reenvío, cierre, publicación posterior o reinicio no lo reinician. Evidencia se decide con recepción del servidor; al límite o después no valida automáticamente y se conserva como hecho bajo los controles existentes. No se agrega tolerancia nueva a la hora del dispositivo. | Implementado por el deadline persistido/lock y probado contra Worker concurrente; informe 14. La sincronización offline del cliente MAUI sigue pendiente y no se resuelve aquí. |
| **DEC-04 — nuevo intento, reprogramación y ruta — RESUELTA (opción A, bloque 15)** | La decisión confirmada exige `NoEntregado → Reprogramado → AsignadoRuta → EnTransito`; no hay retry sobre la misma parada/ruta fallida. Una nueva UUID no salta la secuencia. | Se confirma que el operador autorizado debe reprogramar explícitamente y que la planificación existente asigna una ruta nueva. Reprogramar no cuenta, no reinicia el contador/intervalo y conserva `VersionReglasId`; `OcurridaEn` persiste como reloj de CU-04. El comportamiento de reprogramación no otorga permisos nuevos. | Implementado y verificado para flujo servidor/Backoffice con el modelo actual de un bulto. Se bloqueó `NoEntregado → EnTransito`, se agregó la acción de negocio reprogramar, se suspende la parada vieja sin mover custodia y se utiliza la planificación existente. La integración de Reparto pasó 33/33 en PostgreSQL efímero con principal API restringido, incluida carrera de agotamiento automático contra reprogramación obsoleta; el recorrido Backoffice Kestrel/Chromium pasó 1/1. Código, demás pruebas y límites en el informe 15. El retry de cliente mobile offline y el comportamiento multi-bulto no se declaran completos. Las preguntas originales sobre retry por la misma ruta quedaron reemplazadas; las reasignaciones desde estados activos siguen en DEC-07. |
| **DEC-05 — `DecisionOperativa` al agotar intentos — RESUELTA (opción A, bloque 16; autorización alineada en bloque 17)** | CU-04 ya exigía que no hubiera otro intento tras el máximo y dejaba la decisión al responsable; la opción A es una decisión del proyecto, no una frase literal del PDF. | El administrador protegido del operador o el rol protegido `despachador_operador` puede iniciar devolución desde Backoffice con motivo. Ambos requieren `envios.gestionar` vigente, acceso/organización activos y pertenencia del envío al operador. `usuario_operador` y roles personalizados no quedan autorizados por el permiso solo. La acción exige estado/versión vigentes, regla `DecisionOperativa` fijada al envío y máximo agotado; no cambia custodia ni habilita intentos adicionales. | Implementado como acción específica `POST /api/envios/{id}/iniciar-devolucion`, con decisión append-only, historia y efectos existentes en transacción. El predicado de rol protegido compartido con DEC-06 quedó corregido en bloque 17 para incluir códigos administrativos generados por aprovisionamiento (`administrador_operador`, `administrador`, `dueno`) y el dispatcher dedicado. Evidencia en `16-decision-operativa-devolucion.md` y `17-confirmacion-operativa-extravio.md`. |
| **DEC-06 — pérdida confirmada / `Extraviado` — RESUELTA (opción B, bloque 17)** | El diagrama marca pérdida confirmada desde `EnDeposito`, `AsignadoRuta`, `EnTransito` y `EnDevolucion`; el taller no prescribe el actor, el motivo ni la estructura del comando. `NoEntregado` continúa significando intento fallido y no extravío. | Decisión del equipo: confirmación directa por el administrador protegido del operador o `despachador_operador`, con permiso vigente `envios.gestionar`, acceso/organización activos, pertenencia del envío y motivo obligatorio. No exige denuncia/foto no documentada, no mueve custodia y deja el estado terminal. Solo los cuatro orígenes del diagrama se admiten. | Implementado por `POST /api/envios/{id}/confirmar-extravio`, con identidad durable de comando, confirmación append-only, historia, suspensión de parada y outbox existente atómicos. Aprovisiona `despachador_operador` para organizaciones existentes/nuevas sin asignar usuarios automáticamente. Pruebas, riesgos y el punto abierto de hechos físicos offline tardíos están en `17-confirmacion-operativa-extravio.md`. |
| **DEC-07 — salidas presentes en dominio pero no en la figura** | `Envio.Permite` incluye transiciones adicionales: EnDeposito → EnDevolucion; AsignadoRuta → EnDeposito/Reprogramado; EnTransito → Reprogramado; Reprogramado → EnDevolucion; EntregaPendienteValidacion/Entregado/EntregaSinValidacion → EnDevolucion. Algunas no tienen caller; otras aparecen en fin de jornada, recepción o reasignación. FinJornada puede llevar AsignadoRuta → EnDeposito cuando todos sus bultos siguen en depósito. | Confirmar si estos caminos de recuperación/reasignación son transiciones de negocio válidas o efectos técnicos que deben eliminarse. D18 confirma que una carga parcial no se convierte automáticamente en EnDeposito, pero no explica todos los casos de ruta no cargada. | Mantener Cancelado terminal y no agregar salidas desde estados sin ruta documentada. Para los demás extras, alinear el mapa antes de borrar permisos de dominio; el primer bloque de historia puede registrar lo realmente persistido sin aprobar nuevas aristas. |
| **DEC-08 — CU-08 y agregación por envío** | PDF §5.2 req. 8 y `CU obligatorios!A11:I11` exigen uno o más bultos. CU-08 actual confirma que solo hay uno. CU-08/Dependencias D06 vincula peso, dimensiones y cantidad a planificación. El código de reparto itera todos los bultos para confirmar carga/entrega/rendición, pero el estado de envío se modifica en bloque. | ¿Qué constituye recepción completa con escaneos parciales, faltantes/sobrantes o bultos bajo custodios distintos? ¿Cuándo el envío completo queda Entregado, Reprogramado o Devuelto? ¿Puede una operación parcial afectar solo custodia de un bulto sin mover estado global? | No elegir una agregación por inferencia. Cerrar CU-08 antes de certificar recepción, capacidad, carga, entrega, rendición, devolución y extravío multi-bulto. Un registro de transición a nivel de envío puede prepararse ahora; los eventos por bulto deben esperar el contrato CU-08. |

## 4. Diseño propuesto de historia inmutable

### 4.1 Estructuras existentes y sus límites

- `CancelacionEnvio` / tabla `CancelacionesEnvio` guarda origen de estado, versión, actor/organización o autorización pública, motivo y fecha para la cancelación. Es un buen registro especializado y participa en la función SQL/outbox de cancelación; no contiene las transiciones de recepción, ruta, entrega o intento.
- `OperacionJornada` guarda ID, operador/acceso, ruta, secuencia, envío, tipo, hash, payload, resultado/respuesta e instante recibido. Su clave de operación permite replay offline idempotente y el cierre tiene incidencias inmutables. Es un diario de comandos móviles, no cubre Backoffice ni todas las transiciones; una operación puede terminar en el mismo estado visible o no cambiar estado.
- `PruebaEntrega` y `EvidenciasReparto` conservan la prueba y sus artefactos. Describen evidencia/custodia actual, no una secuencia de cambios de estado.
- `OutboxMessage` y `OutboxMessages` son una cola durable pero operativa: estado de publicación, intentos y despacho cambian. No sustituyen un historial permanente. Hoy se crean `GenerarSeguimiento`/`EnvioCreado` en alta, mensajes de cancelación y `RepartoModificado` en reasignación; no hay un mensaje general para cada transición existente.
- No se encontró `DbSet`/entidad de historial general de envíos ni interceptor común de `SaveChanges` que cree eventos de estado.

Por eso reutilizar únicamente uno de esos registros dejaría sin historia los otros caminos. La propuesta agrega una fuente durable mínima para eventos del envío; mantiene los registros especializados y no copia payloads sensibles.

### 4.2 Modelo lógico propuesto en el corte original (implementación vigente en el informe 13)

Nombre tentativo de la tabla: `EnvioEventos`. Una fila inmutable representa una sola clase de observación:

| Tipo | Significado | Campos de estado |
|---|---|---|
| `Creacion` | Estado inicial de un envío nuevo, dentro de su transacción de alta. | Anterior nulo, estado observado/nuevo `Admitido`; no se presenta como una transición desde un envío previo. |
| `TransicionEstado` | Cambio de estado efectivamente persistido. | Anterior y nuevo obligatorios y distintos; versión anterior/nueva. |
| `Hecho` | Hecho físico u operativo confirmado sin cambio de estado, por ejemplo EntregaFisica tardía en Cancelado o intento repetido que deja NoEntregado. | Sin anterior/nuevo; `EstadoObservado` conserva el estado vigente en el momento de registro. Nunca `Cancelado → Cancelado`. |
| `EstadoObservadoInicio` | Fotografía de estado para un envío existente al comenzar el historial. | Solo `EstadoObservado`; no simula creación ni transición histórica. |

Campos mínimos propuestos:

- `Id`, `OperadorId`, `ComercioId`, `EnvioId` y versión de esquema del evento.
- Tipo; `EstadoAnterior`, `EstadoNuevo` o `EstadoObservado` según el tipo; `VersionAnterior`, `VersionNueva` y `VersionReglasId` asociados al envío.
- Actor tipado y referencia: acceso/usuario autenticado; identificador de autorización pública sin token; o proceso/worker con identidad de job. La API nunca acepta el actor desde el DTO.
- `OrigenTipo` y `OrigenId` (operación móvil, ruta, recepción, cancelación, tarea u otro comando controlado), `OperacionJornadaId`/`RutaId` opcionales y correlación. Un comando con varios cambios usa ordinal estable.
- `OcurridaEnUtc` y `RegistradaEnUtc` separadas. La primera puede ser el instante del dispositivo declarado y validado; la segunda siempre la asigna el servidor/DB. Para registros de baseline, `OcurridaEnUtc` es nulo.
- Geolocalización solo si aplica y está validada por el flujo. No duplicar fotos, firmas, nombre/documento ni payload completo; referenciar `OperacionJornada`/`PruebaEntrega` y aplicar la proyección de acceso correspondiente.

Restricciones sugeridas:

- FK compuesta por operador/envío; constraints que obligan la forma correcta de cada tipo.
- Unicidad para transición efectiva por `OperadorId + EnvioId + VersionNueva`; para hechos, unicidad por origen/id/tipo/ordinal. Reintentar la misma operación no añade otra fila.
- Prohibir `UPDATE` y `DELETE` a roles de runtime y añadir una guarda de BD para impedir edición/borrado accidental. Correcciones serían nuevos eventos compensatorios, nunca reescrituras.
- Al escribir estado, capturar el `OLD.Estado/Version` y el `NEW.Estado/Version` realmente persistidos. No registrar ciclos de dominio que se revierten antes del `SaveChanges`: por ejemplo, un intento que transitoriamente pasa por EnTransito y persiste NoEntregado no se convierte en dos transiciones imaginarias.

### 4.3 Captura, RLS, transacción e idempotencia propuestas (contrastar con implementación del informe 13)

1. Usar una migración aditiva nueva y hacer de `EnvioEventos` la fuente canónica de la línea de tiempo. Un trigger `AFTER INSERT/UPDATE OF Estado` registra creación y cada cambio efectivo de estado confirmado, tanto si la fila la escribe EF como si la función SQL de cancelación la modifica. Solo inserta `TransicionEstado` cuando `OLD.Estado IS DISTINCT FROM NEW.Estado`; los ciclos que no se persisten no aparecen. Un hecho sin cambio de `Estado` se agrega explícitamente mediante una función acotada desde el repositorio dentro de la misma transacción.
2. Actor/origen/correlación deben venir del contexto de request validado por `RlsTransactionMiddleware`/`RlsTransaction` o del worker autorizado; la operación móvil agrega su ID/secuencia y `OcurridaEn` validada. Usar `set_config(..., true)` transaccional para que los valores no se filtren por conexiones reutilizadas. `FinJornada` y las tareas futuras deben usar identidad de proceso, no suplantar un usuario.
3. Mantener RLS forzada con las políticas tenant vigentes para `OperadorId` y `ComercioId`, FK compuestas y lectura restringida al actor autorizado. `nexoruta_api` no recibe INSERT/UPDATE/DELETE generales sobre la tabla: la captura se hace por trigger/función de dueño NOLOGIN/NOBYPASSRLS, con `search_path` fijo, grants mínimos y validación del envío/contexto/versión. `nexoruta_worker` solo usa la función que necesite; no obtiene escritura general.
4. Estado, versión, hecho, historia y los mensajes outbox que correspondan se confirman en la transacción actual (`RlsTransactionMiddleware` + `BeginOrJoinAsync`) o se revierten juntos. Si insertar la historia o el outbox falla, no confirmar cambio de estado; una respuesta exitosa no se produce antes del commit.
5. La concurrencia sigue protegida por versión optimista, bloqueo de fila/operador que ya utiliza cada camino y secuencia móvil. El trigger observa el ganador real; la versión nueva y clave única evitan dos transiciones para el mismo estado confirmado. Operaciones móviles repetidas devuelven la respuesta almacenada en `OperacionJornada`; no vuelven a llamar el grabador.
6. La auditoría especializada `CancelacionEnvio` continúa siendo fuente del motivo y validación/autorización. El evento canónico de transición `… → Cancelado` guarda `OrigenTipo = CancelacionEnvio` y `OrigenId = CancelacionesEnvio.Id`; la función de cancelación deberá exponer ese ID en contexto transaccional antes del `UPDATE` que dispara el trigger. Así se correlaciona sin depender del orden actual, donde el `UPDATE Envios` ocurre antes del `INSERT CancelacionesEnvio`. No se sustituye el núcleo SQL ni su idempotencia. La conciliación física sobre Cancelado agrega un `Hecho` con `EstadoObservado = Cancelado`, operación y custodia; no inserta transición.

El trigger/función de historia no publica mensajes. La historia es permanente; Outbox conserva el ciclo mutable de entrega. Cuando se agregue el contrato de avisos CU-27/28, los mensajes requeridos deben insertarse dentro de la misma transacción y referenciar el mismo `EventoId`. No crear un evento/broker nuevo por flecha sin contrato: CU-28 exige webhooks en cambios de estado y CU-27 cambios relevantes, pero el payload y la selección de relevancia aún no son un contrato general en el código.

### 4.4 Datos existentes sin historia demostrable

No inventar alta, actor ni fecha original. Durante la migración, insertar para cada envío existente un marcador `EstadoObservadoInicio`: `EstadoObservado` igual al estado leído durante la migración, `OcurridaEnUtc = NULL`, `RegistradaEnUtc = clock_timestamp()` y origen `Migracion`. La UI/read model lo presenta como “registro de historia iniciado; estado observado al habilitarlo”, no como un cambio histórico.

La migración debe poblar el registro canónico con cada cancelación previa usando solo los datos demostrables de `CancelacionesEnvio`: estado anterior, versión, actor/tipo o referencia de autorización pública y `CreadaEnUtc`. La fila conserva `OrigenTipo = CancelacionEnvio` y su ID original; `RegistradaEnUtc` refleja cuándo se incorporó a la historia, mientras `OcurridaEnUtc` conserva la fecha probada de la cancelación. `CancelacionesEnvio` sigue siendo el registro especializado para motivo y autorización, pero la línea de tiempo consulta un único historial canónico. No reconstruir estados intermedios de ruta/entrega que no tengan registro.

Los envíos creados después de la migración reciben un evento `Creacion` con el actor y momento reales de la transacción. Los hechos anteriores a ese corte que no estén en un registro durable quedan explícitamente desconocidos.

### 4.5 Primer bloque implementable en el corte original (ejecutado de forma acotada; véase el informe 13)

El siguiente bloque puede implementar solo la base de historia para lo que hoy ya se persiste, manteniendo exactamente las reglas de estado actuales mientras las decisiones DEC-01 a DEC-08 esperan:

1. Añadir `EnvioEventos`, constraints/FKs, RLS forzada, grants mínimos, funciones/trigger y marcador de observación inicial con migración nueva.
2. Capturar creación y cada cambio de estado SQL efectivamente persistido; agregar el evento de hecho físico tardío de la ruta cancelada y correlacionarlo con la operación ya idempotente.
3. Enlazar metadatos reales de actor, fuente, operación y fechas desde contexto transaction-scoped; preservar `CancelacionEnvio` y funciones existentes.
4. Hacer una proyección de lectura autorizada de la historia, sin ampliar el token público ni exponer IDs internos/datos personales. No modificar acciones ni hacer que una historia decida por sí sola una transición.
5. Verificar con PostgreSQL efímero y rol `NOSUPERUSER NOBYPASSRLS`: migración/baseline; alta inicial; transición confirmada y rollback; hechos sin cambio de estado; operaciones repetidas; dos transiciones concurrentes; lectura por comercio/operador; rechazo de UPDATE/DELETE por roles runtime; atomicidad con outbox ya generado; ausencia de `Cancelado → Cancelado`.

Archivos a revisar al implementar: `NexoRutaDbContext.cs`, `RlsTransaction.cs`, `RlsSqlFunctionContract.cs`, nueva migración y snapshot; `EfEnviosRepository.cs`, `EfRutasRepository.cs`, `EfRutasRepository.Reasignaciones.cs`, `EfOperacionesRepartoRepository.cs` y `.Ejecucion.cs`; función/migración de cancelación sin cambiar su contrato; pruebas `tests/NexoRuta.IntegrationTests/Reparto/` y `Seguridad/`. El historial por bulto, el temporizador, nuevas acciones y los cambios de estados quedan fuera.

## 5. Dependencias y límites

- **CU-08 antes de cerrar estados de todos los bultos.** Debe preceder completar recepción/escaneo y discrepancias, la decisión de elegibilidad/capacidad de rutas, confirmación de carga, entrega/rendición y devolución/extravío cuando una misma operación afecte varios bultos. No agregar múltiples bultos ni asumir que recibir/entregar uno cambia todo el envío.
- **Destino confirmado antes de planificación.** Sigue siendo requisito y conducta real: Commerce debe confirmar destino durante Admitido; importar o registrar historia no lo sustituye.
- **Tarea temporizada DEC-01/02/03.** Implementada en el bloque 14: usa deadline persistido, la versión de regla del envío y una función SQL restringida. Versiones históricas nulas no se vencen automáticamente y conservan pendiente la política histórica; véase el informe 14.
- **Extravío después de DEC-06 y CU-08.** La confirmación de servidor para un bulto quedó implementada en bloque 17. CU-08 aún debe definir los efectos cuando haya más de un bulto. Sigue pendiente la conciliación de hechos físicos offline que lleguen después de `Extraviado`; no deben reactivarlo ni borrar el hecho.
- **CU-27/28 y outbox.** El historial no completa notificaciones. Definir/implementar el contrato de evento, destinatarios, payload y reintentos junto a sus consumidores; preservar los dispatchers actuales.
- **Cancelación y máquina completa.** El arreglo de evidencia tardía conserva `Cancelado` y no cierra las otras aristas. La revisión nativa sigue pendiente y no hay aprobación ni cierre global.
