# CU-06 — disponibilidad física, retorno y estimaciones

> **Actualización B1:** el usuario adoptó explícitamente la precisión efectiva de D11 y las guardias de capacidad/habilitación correspondientes a B1. Ver [implementación](05-implementacion-b1.md). El diseño restante conserva su carácter de propuesta: no se implementaron ocupación/retorno/base/estimaciones ni se cambió D18.

**Diseño propuesto, no implementado ni decisión de negocio ya aceptada.** La gestión administrativa y la carga existen; faltan hechos explícitos de retorno/aptitud y estimaciones viales. La recomendación central es separar el fin de jornada de la disponibilidad física, conservando la decisión D18 sobre incidencias.

> Una estimación de regreso informa la planificación. No confirma el retorno físico, no prueba descarga y nunca libera automáticamente un vehículo ocupado.

## 1. Reconstrucción del comportamiento vigente

| Momento | Hecho persistido / efecto actual | Evidencia |
|---|---|---|
| Habilitar vehículo | `Activo=true`; ficha puede editarse. No acredita ubicación ni disponibilidad. | `backend/src/NexoRuta.Domain/Reparto/Vehiculo.cs:6-11,21-24` |
| Planificar | Crea hoja Planificada con `ReservaRecursosActiva=true`, vehículo/repartidor/fecha y capacidades copiadas. | `HojaRuta.cs:16-17,26-34`; `EfRutasRepository.cs:29-96` |
| Ruta vacía | Reserva igualmente, permite recibir reasignaciones. No se despacha sin parada activa. | `EfRutasRepository.cs:59-64,109-112`; tests `BorradorVacioReservaRecursosPeroNoSeDespachaNiSeDescarga` |
| Cancelar última parada | Conserva reserva. Para liberar, cancelar explícitamente la hoja planificada sin paradas activas. | `HojaRuta.cs:55-61,89-93`; `EfRutasRepository.cs:117-130` |
| Despachar | Estado Despachada, todavía sin prueba de salida física. Revalida habilitación/custodia, no capacidad vigente ni otra ocupación de fecha diferente. | `EfRutasRepository.cs:99-114`; `HojaRuta.cs:48-52` |
| InicioJornada | EnCurso e InicioEnUtc del servidor, solo si fecha de hoja coincide con día del operador al recibir el inicio. | `EfOperacionesRepartoRepository.Ejecucion.cs:15-20`; `HojaRuta.cs:64-67` |
| Preparación de carga | CargarBulto asigna custodia al repartidor/ruta; no es todavía salida. ConfirmarCarga valida discrepancias según política, suspende incompletas si está permitido y registra salida. | `EfOperacionesRepartoRepository.Ejecucion.cs:34-51,115-121` |
| Salida | `SalidaEnUtc = op.OcurridaEn` en UTC. Es un hecho informado por dispositivo, no hora planificada ni llegada calculada. | `HojaRuta.cs:70-74` |
| Fin local sin red | FinJornada pendiente en almacenamiento móvil. No cambia al servidor ni su reserva. | `mobile/src/NexoRuta.Mobile.Core/Jornadas/JornadaLocal.cs:67-92`; `SincronizadorJornada.cs:39-65` en Mobile.Application |
| Fin aplicado | Finalizada, `ReservaRecursosActiva=false`, `FinEnUtc` informado; incidencias/custodia se conservan. | `HojaRuta.cs:77-80`; `EfOperacionesRepartoRepository.Ejecucion.cs:69-85`; repositorio principal `:72-86` |
| Uso siguiente | Puede planificarse con el mismo recurso/fecha tras liberar. No hay confirmación independiente de retorno ni inspección de carga residual del vehículo. | `EfRutasRepository.cs:41-65`; `HojaRutaConfiguration.cs:23-26` |

Los paths backend abreviados de esta tabla están en `src/NexoRuta.Domain/Reparto/` o `src/NexoRuta.Infrastructure/Reparto/` del submódulo backend.

### Mismo día, medianoche y concurrencia

- **Varias rutas sucesivas:** sí, una vez aplicado el fin de la anterior (o cancelada la planificada vacía), la reserva deja de entrar en el índice único. No hay soporte de múltiples reservas horarias anticipadas para el mismo recurso/día: la exclusión actual es diaria.
- **Ruta que cruza medianoche:** el dominio no finaliza por reloj. Inicio exige día correcto, pero una EnCurso puede seguir procesando operaciones al día siguiente; no hay TTL de reserva. Su reserva sigue asociada a la fecha original.
- **Planificación del día siguiente:** la reserva anterior no bloquea esa fecha; un test existente lo afirma para borradores. La sonda P07 además comprobó despacho de otra fecha con A todavía EnCurso. No se confundió ese test de reserva con prueba de disponibilidad física.
- **Visibilidad:** `EfRutasRepository.ListarAsync:15-21` filtra por fecha. Una hoja anterior abierta necesita consulta de su fecha o por Id propio; no equivale a un panel global de ocupaciones pendientes. Recomendar una vista de ocupación no cerrada independiente del filtro diario.
- **Carreras:** operaciones de configuración, planificación y jornada usan `FOR UPDATE` del operador, además de versiones e índices únicos de recurso/día. Las pruebas concurrentes pasaron para las reglas actuales; no cubren una exclusión entre fechas que no existe. El lock serializa decisiones, no agrega por sí solo la condición faltante.

## 2. Cinco conceptos que no conviene colapsar

| Concepto | Persistir o derivar | Propuesta mínima |
|---|---|---|
| Habilitado administrativamente | Persistido | Conservar `Vehiculo.Activo`. Inactivo no significa de regreso ni libre. |
| Reservado para trabajo futuro | Persistido | Reutilizar hoja/recurso/fecha/reserva. Mantener reserva diaria inicialmente; intervalos solo si negocio pide múltiples compromisos anticipados en el día. |
| Ocupación operativa exclusiva | Hechos persistidos, estado derivable | Toma de recurso y liberación confirmadas, vinculadas a hoja/recurso. Una sola ocupación no liberada por vehículo/operador, sin cortar en medianoche. |
| Regreso estimado | Resultado persistible con procedencia/versión | Instante previsto, calculadoEn, origen del cálculo, calidad y causa de desconocimiento. No es un hecho de retorno ni una autorización. |
| Retorno y aptitud confirmados | Hechos persistidos, disponibilidad derivada | Confirmador/fecha/servidor/versión y, cuando corresponda, instante físico declarado. Retorno puede preceder a disponibilidad si falta descarga o hay incidencia mecánica. |

No se propone un enum único que mezcle habilitación, reservas, ejecución y estimaciones. «Disponible ahora» se deriva de habilitación + ausencia de ocupación no liberada + ausencia de bloqueo operativo. «Reservable para una fecha» es otra consulta, dependiente de reservas, no una promesa de disponibilidad física futura.

### Extensión mínima de persistencia recomendada

Como primer corte, extender la **hoja existente** con hechos suficientes, en vez de crear un subsistema genérico de flota:

- `OcupacionIniciadaEnUtc`, fijado al otorgar el recurso para uso inmediato, no al crear una reserva futura.
- `RetornoConfirmadoEnUtc` y actor, ruta/recurso/versiones esperadas, instante de recepción y opcional instante físico declarado.
- `DisponibilidadConfirmadaEnUtc` y actor/motivo, separados del retorno si existe carga residual o bloqueo operativo.
- No duplicar esos timestamps en un booleano «libre» mantenido por varios comandos. Una ocupación sigue activa si comenzó y no tiene disponibilidad confirmada.

Índice único parcial propuesto sobre `(OperadorId, VehiculoId)` cuando `OcupacionIniciadaEnUtc IS NOT NULL AND DisponibilidadConfirmadaEnUtc IS NULL`; equivalente para repartidor si esa es la política de recurso humano. **No filtrar por Estado != Finalizada**, porque D18 permite jornada terminada con ocupación/retorno pendiente. El lock actual del operador permite una implementación inicial simple; conservarlo y justificar cualquier cambio futuro, sin introducir locks distribuidos por rutina.

Si una hoja puede cambiar de vehículo o tener varias tomas/devoluciones en el futuro, entonces estos hechos requerirán registros de ocupación separados. No se introduce esa abstracción para el alcance inicial de una hoja/un vehículo. Las fichas de vehículo conservan identidad; no borrar ni volver a crear para reactivarlas.

La nueva ocupación se adquiere y libera transaccionalmente con comprobación de versión y claves tenant. Una confirmación debe referenciar la ocupación/hoja exacta: un cierre o retorno atrasado de A **nunca** libera B. No confiar en un Id de vehículo sin tenant ni ruta.

## 3. Transiciones propuestas

```text
Reserva futura
  ├─ cancelar hoja vacía → libera reserva, conserva historia
  └─ autorizar uso inmediato → adquiere ocupación exclusiva
       ├─ iniciar jornada / cargar → todavía en preparación
       ├─ confirmar salida → vehículo en recorrido
       ├─ fin de jornada → jornada cerrada, ocupación puede seguir abierta
       ├─ confirmar retorno → regreso físico acreditado, posible descarga pendiente
       └─ confirmar disponibilidad → libera ocupación/reserva para siguiente uso
```

El regreso estimado es un dato lateral del recorrido; **no** hay flecha `ETA alcanzada → liberar`. Si se demora o vence la ETA, mostrar atraso/retorno desconocido, sin cambiar los hechos.

### Garantía al despachar

Antes de habilitar un uso inmediato: vehículo activo, conductor elegible, bultos/custodia/estado correctos, carga dentro de capacidad **vigente** y ninguna ocupación activa incompatible, aunque sea de ayer. Adquirir el recurso en la misma transacción; repetir la comprobación antes de salida si puede haber cambios entre despacho y carga.

**Decisión pendiente:** actualmente Despachada también permite descargar la hoja en mobile y puede ocurrir para fechas futuras. Si negocio necesita publicar con anticipación, esa publicación **no es** concesión de disponibilidad física: separar conceptualmente publicar/preparar de autorizar uso. Recomendación inicial: adquirir ocupación al despacho operativo inmediato y exigirla al inicio/salida; una publicación futura, si se conserva, no puede saltarse esta guardia. No cambiar silenciosamente el significado del endpoint actual sin actualizar contrato y pruebas.

### Desactivación y edición durante el uso

- Desactivar impide usos nuevos, pero no cancela la hoja ni libera el recurso ni elimina su historia.
- Dejar rendición, cierre y retorno accesibles al responsable habilitado para resolver hechos existentes.
- Capacidad/matrícula en hoja son snapshot histórico; capacidad vigente es restricción física. Mantener ambas fuentes identificadas.
- Reducir antes de salida exige revalidación y mensaje de impacto. En recorrido, no «ajustar» la historia de lo cargado: registrar/avisar la incidencia operativa y bloquear el siguiente uso si corresponde.

## 4. Cierre con incidencias y offline

### Conservar la decisión vigente

D18 permite cerrar con bultos no entregados ni rendidos. El servidor obtiene incidencias de su propia custodia, no de una lista elegida por el cliente. Cierre e incidencias son atómicos, journal inmutable e idempotencia por UUID/hash. La custodia pendiente no se convierte en depósito y DEC-07 mantiene separados hechos físicos y estado comercial.

Eso **alcanza para terminar la jornada administrativa actual**, pero no para asegurar vehículo vacío, en base y listo para otro trabajo. La extensión explícita es que FinJornada deje de ser el único hecho del que depende la disponibilidad física. No borrar D18 ni exigir completar entregas para poder cerrar.

### Casos propuestos

| Caso | Jornada | Vehículo / disponibilidad propuesta |
|---|---|---|
| Fin offline, aún no recibido | Cierre local pendiente; el servidor sigue en curso | Conserva ocupación y reserva. Aviso de retorno no confirmado; no asumir ubicación. |
| Fin recibido sin retorno | Finalizada con o sin incidencias | Ocupación sigue abierta. Retorno desconocido. |
| Regresa con carga pendiente | Jornada puede estar finalizada | Retorno confirmado; aptitud pendiente de descarga/conciliación. No inventar espacio libre. |
| Retorno y descarga/aptitud confirmados | Finalizada o cierre administrativo en conciliación | Liberación aplicada y aviso; siguiente uso exige activo y guardias actuales. |
| Dispositivo dice retornar pero sin red | Hecho declarado pendiente de sincronizar | No liberar globalmente. Si depósito confirma por Backoffice conectado, conciliar después con el mismo hecho/ocupación. |
| Retorno llega tarde después de otra intervención | Diario conserva orden/identidad | Aplicación idempotente o conflicto explícito; jamás liberar otra ocupación por timestamp antiguo. |

Recomendación inicial: confirmación conectada por depósito/despachador, con observación/recepción física y sin depender de GPS. Mobile puede declarar retorno cuando se implemente el comando, pero el dato local pendiente no es disponibilidad confirmada. No permitir reanudar una jornada cerrada solo para enviar retorno: el comando debe tener su propio ciclo y no reabrir entregas.

Si queda un bulto con custodia del repartidor pero físicamente no está en el vehículo, no deducir carga residual solo de ese estado: la incidencia debe conciliarse. Como alcance inicial conservador, bloquear la siguiente ocupación hasta confirmación de descarga/aptitud; una excepción con carga residual y cálculo de capacidad remanente sería una política posterior, no una liberación implícita.

### Migración de estado existente

Migración aditiva, sin borrar jornadas ni incidencias. Un FinEnUtc histórico no acredita RetornoConfirmadoEnUtc. Conciliar manualmente las ocupaciones actuales antes de aplicar la nueva restricción; registrar quién confirma la disponibilidad inicial. No establecer retorno ficticio para todos los registros antiguos ni dejar una migración que reserve para siempre todas las rutas históricas sin intervención diseñada.

## 5. Base operativa del operador

No se encontró base confirmada en `Operador`, `ConfiguracionReparto` ni `VersionIdentidadVisualOperador`. Correo/teléfono/colores/logo no reemplazan dirección y coordenadas operativas.

**Propuesta inicial:** una única base de salida y retorno por operador, gestionada desde configuración existente, con:

- Dirección descriptiva, latitud/longitud confirmadas, autor e instante de confirmación, versión.
- Zona horaria operativa ya existente; no crear otra fuente temporal divergente.
- Cambio de dirección invalida confirmación previa; geocodificar propone, una persona confirma el punto.
- Snapshot de base usado por la hoja/estimación. Cambiar base hoy no altera historia ni rutas en ejecución sin una acción explícita de recálculo.

Reutilizar patrón `Direccion.ConfirmarUbicacion`, validación finita/rangos, experiencia de propuestas/confirmación y `IGeocodificador`/Geoapify donde corresponda. No acoplar la base a un Destinatario ni a datos de contacto públicos. La reutilización es de reglas/adaptadores, no de una fila de dirección de un envío ajeno.

Falta de base/coordenadas confirmadas: se puede seguir administrando flota y trabajar con horas manuales identificadas, pero cálculo vial inicial y retorno se muestran **no disponibles**. No reemplazar por (0,0) ni el centro de la ciudad.

## 6. Planificación temporal inicial

### Datos diferenciados

| Dato | Estado actual | Propuesta |
|---|---|---|
| Fecha de ruta | Persistida | Conservar como fecha operativa, no límite artificial de un recorrido físico. |
| Salida planificada | No encontrada | Timestamp completo previsto, zona del operador/UTC; entrada del cálculo. |
| Inicio real | InicioJornada recibido | Conservar; no equivale a salida. |
| Salida real | ConfirmarCarga informado por dispositivo | Conservar; incluir instante de recepción cuando se muestre su confianza. |
| Llegada por parada | Hora manual convertida a UTC | Diferenciar manual/estimada/calculada; no etiquetar manual como ETA vial. |
| Servicio por parada | No encontrado como entrada del cálculo | Minutos no negativos, default del operador y override explícito por parada si es necesario. |
| Regreso estimado | No encontrado | Último tramo → base + servicio final + margen operativo. |
| Retorno/disponibilidad | No encontrados como hechos independientes | Confirmaciones explícitas separadas del cálculo y del fin. |

La validación actual exige llegadas dentro de la fecha de hoja (`EfRutasRepository.cs:89-90`). Para recorridos planificados que cruzan medianoche deberá cambiarse de forma explícita y conservar orden temporal; no forzar horas de D+1 a D ni asumir duración negativa. Hora local ambigua/inexistente por cambio de zona requiere validación; guardar UTC y zona aplicada, no sumar strings `HH:mm`.

### Fórmula mínima

Para paradas activas en orden, base B, salida prevista S, servicio sᵢ, duración vial t(a,b,instante):

```text
LlegadaEstimada[1] = S + t(B, P1, S)
SalidaEstimada[i]  = LlegadaEstimada[i] + Servicio[i]
LlegadaEstimada[i+1] = SalidaEstimada[i] + t(Pi, Pi+1, SalidaEstimada[i])
RegresoEstimadoBase = SalidaEstimada[n] + t(Pn, B, SalidaEstimada[n])
ListoPrevisto = RegresoEstimadoBase + MargenOperativo
```

Si el proveedor no usa tráfico/hora de salida, indicarlo; no afirmar que t modela tráfico cuando solo ofrece duración estática. No sumar margen a cada parada y de nuevo al retorno por accidente. El tiempo de servicio cubre entrega/atención; el margen final cubre descarga/preparación según decisión de negocio. `ListoPrevisto` sigue siendo previsión, no disponibilidad confirmada.

Ruta sin paradas: borrador/reserva, no calcular un circuito ficticio ni declarar retorno confirmado. Se puede mostrar «sin recorrido estimable»; cancelar explícitamente continúa liberando la reserva según reglas existentes.

### Contrato propuesto de proveedor vial (decisión pendiente)

No hay integración de tiempos por carretera encontrada. Geoapify actual usa `/v1/geocode/search`; Mapbox mobile prepara mapa/teselas. Ninguna evidencia observada demuestra routing en uso.

Propuesta de contrato de aplicación pequeño, independiente de vendedor:

```text
Entrada:
  puntos ordenados (base, paradas activas, base), salida UTC,
  perfil vial del vehículo y versión/huella del pedido
Salida válida:
  segmentos en el mismo orden, duración en segundos y distancia en metros,
  proveedor/modelo, calculadoEn, vigencia y si considera tráfico
Salida no calculable:
  faltan coordenadas | no hay recorrido vial | timeout | cuota |
  proveedor no disponible | respuesta inválida
```

Validar cantidad/orden de tramos, duraciones finitas/no negativas y límites de respuesta. Evitar precisión visual de segundos si entradas/proveedor no la justifican. Una huella/versionado del pedido impide aplicar a una ruta editada una respuesta vieja. Un timeout no convierte la duración en cero.

**Decisión de proveedor pendiente:** capacidades de routing/perfil, límites de puntos, SLA, tráfico, licencia, costo, conservación/caché y privacidad de coordenadas. Recomendación: evaluar primero si un proveedor ya aprobado puede satisfacer ese contrato; no asumir que contratar geocodificación autoriza otro servicio. No se eligió vendedor, investigó precio actual, contrató servicio, llamó APIs externas ni agregó credenciales. La evaluación comercial/técnica concreta debe usar documentación vigente del candidato antes de implementarlo.

No usar distancia en línea recta/velocidad fija como tiempo vial preciso. Si se decide una aproximación inicial, tendría que ser una opción explícita rotulada como aproximación y no sustituir silenciosamente routing; no se recomienda para esta primera garantía operativa.

## 7. Actualización durante el recorrido

La estimación inicial sale de la **base y horario planificado**. Una actualización usa **posición reciente del repartidor y paradas aún pendientes**, conservando ruta/ocupación actual. No son el mismo cálculo ni deben sobrescribir el plan histórico sin procedencia.

Flujo propuesto:

1. Obtener posición de la jornada/operador/repartidor vigentes con fecha de medición y precisión; distinguir de recepción servidor. Descartar puntos fuera de orden para la proyección actual, sin borrar su journal.
2. Exigir calidad configurada: como punto inicial a validar en operación, antigüedad máxima **2 minutos** y precisión ≤ **100 m**. Son recomendaciones, no umbrales existentes ni garantía universal; calibrarlos con dispositivos y geografía reales.
3. Partir del punto aceptado, instante actual y próxima parada pendiente según el estado vigente. Conservar servicio restante cuando una parada ya está en atención; no sumar de nuevo recorridos completados.
4. Solicitar tramos pendientes → base; aplicar solo si siguen vigentes orden/versiones/base y el resultado no es anterior al mostrado. Publicar procedencia y hora de actualización.
5. Limitar frecuencia de consulta y reutilizar resultado válido; recalcular por cambio material/atraso y no por cada GPS. Política de frecuencia/costo pendiente, no se implementa aquí.

| Problema | Información mostrada / conducta segura |
|---|---|
| Falta coordenada de base o parada | ETA parcial o desconocida con causa; no continuar circuito como si faltara cero tiempo. |
| GPS antiguo/impreciso | Última posición identificada por antigüedad/precisión; no usar como «actual». Mantener plan o cálculo anterior rotulado. |
| Sin conectividad mobile | Hechos locales pendientes; servidor conserva última información y antigüedad. Sin actualización no implica vehículo detenido ni libre. |
| Timeout/cuota/fallo proveedor | Mostrar último cálculo como desactualizado o no disponible. Reintento acotado, sin bucle ni nueva credencial automática. |
| Retraso o ETA superada | «Regreso demorado / por confirmar»; pedir actualización/confirmación operativa, no liberar. |
| Respuesta vieja tras edición de ruta | No reemplaza estimación de la versión nueva. Guardar motivo de descarte si hace falta diagnóstico. |
| Ruta ya retornada y confirmada | Hecho confirmado prevalece; un GPS tardío o ETA nueva no reabre ocupación. |

No se propone reoptimizar, alterar automáticamente orden, reasignar envíos ni auditar tracking completo.

## 8. Aviso de disponibilidad en Backoffice

Panel mínimo: matrícula, habilitación, ocupación/ruta actual, reserva futura, última posición con calidad, regreso/listo **previstos**, retorno/disponibilidad **confirmados**. No agrupar todo bajo una insignia verde «Disponible».

- Evento/aviso nace de una confirmación aplicada y comprometida en servidor. Incluir operador, recurso, ocupación/ruta y versión para evitar avisos de otro tenant o de una ocupación anterior.
- Primer corte: actualizar el listado y una región de estado accesible tras la confirmación; consulta periódica/manual según patrón existente. Si se pide notificación activa durable, reutilizar outbox/mensajería del proyecto con idempotencia, sin crear una segunda fuente de disponibilidad.
- Texto recomendado: «Retorno confirmado; descarga pendiente» o «Disponible confirmado a las …». No «Llegó» por haber vencido una ETA.
- Usar tokens semánticos, texto además de color, controles con labels, foco conservado y una acción principal clara. Skeleton solo al cargar asíncronamente estructura real; conservar datos anteriores durante actualización y señalar antigüedad/error.

Estas son propuestas; no se modificó UI ni se verificó visualmente su resultado.

## 9. Decisiones de negocio pendientes y recomendación concreta

| ID | Decisión pendiente | Recomendación inicial y motivo |
|---|---|---|
| D1 | ¿FinJornada libera físicamente o solo cierra trabajo? | Conservar cierre con incidencias; separar liberación por disponibilidad confirmada. D18 no prueba retorno/descarga. |
| D2 | ¿Quién confirma retorno/aptitud? | Depósito/despachador conectado, con hecho/actor/fecha. Mobile puede declarar; GPS o ETA no certifican. |
| D3 | ¿Permitir nuevo uso con carga pendiente? | No por defecto. Confirmar retorno por separado y exigir descarga/conciliación de aptitud. Una excepción con carga residual exige regla explícita de capacidad remanente. |
| D4 | ¿Reserva diaria o ventanas? ¿Varias rutas del día? | Conservar reserva diaria y reutilización tras liberación para el primer corte. Agregar ventanas solo si se necesitan varias reservas anticipadas en el mismo día; siempre ocupación exclusiva entre fechas. |
| D5 | ¿Despacho futuro publica o autoriza uso inmediato? | Separar publicación de concesión física si se necesita adelantar descarga mobile. Guardias físicas al despacho operativo y salida; no considerar índice por fecha prueba suficiente. |
| D6 | ¿Una base o múltiples depósitos? | Una base por operador con salida/retorno iguales y confirmación explícita. Snapshot por hoja; múltiples bases quedan fuera del primer corte. |
| D7 | ¿Proveedor vial/perfil y manejo de horarios manuales? | Contrato de tramos ordenados y duración/distancia; evaluar integración aprobada antes de contratar. Conservar manual como manual; cálculo no silencioso. Definir perfil real de vehículo antes de asegurar restricciones viales. |
| D8 | ¿Calidad GPS y frecuencia? | Empezar evaluación con 2 min/100 m, parámetros visibles/configurables y calibración real; consultas por cambio material y cuota. Posiciones viejas no dan falsa precisión. |
| D9 | ¿Tiempo de atención y margen? | Default por operador con unidades explícitas y override justificado; no fijar minutos universales sin medición. Margen final una vez para descarga/preparación; ETA y listo previsto separados. |
| D10 | ¿Editar/desactivar recursos comprometidos? | Desactivar bloquea nuevos usos, nunca resolución de hechos existentes. Reducción exige revalidación previa a salida y aviso; snapshots no se reescriben. |
| D11 | ¿Escala de capacidades y bultos? | Dos decimales de entrada en g/cm; rechazo explícito de escala adicional. Producto de dimensiones conserva precisión hasta suma/comparación; no redondeo por bulto. |

Ninguna de estas recomendaciones se tomó como decisión humana aceptada. Se registran para implementar con alcance claro, sin detener ni ampliar esta auditoría.
