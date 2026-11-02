# CU-06 — plan mínimo de corrección

> **Estado vigente B3 (seguimiento):** B1 implementado (05), B2 técnicamente verificado (08) y B3 implementado con evidencia en [09](09-implementacion-b3.md). B4/B5 y habilitación operativa/revisión nativa siguen pendientes. Las notas anteriores conservadas abajo describen momentos previos, no el estado vigente.

> **Actualización posterior:** B1 ya tiene implementación; [05-implementacion-b1.md](05-implementacion-b1.md) contiene su evidencia. El texto siguiente conserva el plan y estado originales de auditoría. B2–B5 no comenzaron.

**Este plan no fue implementado.** Se apoya en los [hallazgos](02-hallazgos.md) del checkout del 01/11/2026. No autoriza completar CU-08 ni desarrollar CU-09 en adelante.

**Primer bloque recomendado:** hacer confiable la capacidad vigente, su precisión y su presentación, reutilizando el CRUD y las sumatorias actuales. No construir otra gestión de vehículos ni empezar por un proveedor de mapas.

## 1. Orden por dependencias

| Bloque | Objetivo / dependencia | Reutilizar | Construir o corregir |
|---|---|---|---|
| B1 — cierre técnico de capacidad CU-06 | H01/H03/H04; no depende de ETA ni de completar CU-08 | Vehiculo, pantalla, cliente, contrato, repositorio, snapshot, locks, consultas de bultos | Revalidación vigente, escala explícita, HTML/JS coherentes, feedback de volumen; pruebas faltantes |
| B2 — disponibilidad física | H02/H05/H06; requiere decisiones D1–D5 del documento 04 | Reserva, HojaRuta, control de versión, diario idempotente, custodia/incidencias | Separar fin de jornada de retorno/disponibilidad; exclusión física entre fechas; confirmación y aviso |
| B3 — base y planificación temporal | Requiere base confirmada y política de tiempos; independiente del proveedor concreto | Zona horaria, patrones de confirmación de destino, geocodificador, formularios y tokens | Una base por operador, salida planificada, servicio/margen, snapshot; estados «sin estimación» |
| B4 — estimación inicial vial | B3 + decisión de proveedor/contrato D7 | HTTP client, DI, cancelación, manejo de errores del stack | Adaptador de routing, cálculo secuencial y retorno, trazabilidad/calidad de estimación |
| B5 — actualización durante recorrido | B4 + política GPS y sincronización D8 | Registro Posicion, fecha/precisión, diario y sincronizador mobile | Selección de posición reciente, recálculo de pendientes, revisión de estimaciones sin tocar ocupación |

B1 puede corregirse sin resolver proveedor, base o retorno. B2 no debe esperar a disponer de ETA para proteger el uso físico. B5 es el último incremento, no requisito para cerrar A.

## 2. B1 — capacidad vigente y contrato coherente

### Cambios mínimos

1. Acordar y aplicar **dos decimales como máximo** en capacidades g/cm³, con mínimo 0,01 y máximos existentes. Recomendación: rechazar escala adicional con error por campo, no redondeo silencioso. Si se elige normalizar, hacerlo antes de persistir y devolver exactamente ese valor; no mantener comportamiento divergente API/DB.
2. En `EfRutasRepository.DespacharAsync`, bajo el bloqueo/transacción actuales, leer vehículo vigente y sumar todos los bultos de paradas activas. Comparar peso y volumen por separado, con mensajes identificables y unidades. No usar el snapshot como autorización de capacidad física actual.
3. Revalidar contra vehículo vigente al agregar un envío mediante `ReasignarAsync`; preservar snapshot de planificación para historia. Antes de salida/ConfirmarCarga, volver a exigir capacidad vigente, porque todavía puede cambiar después de despachar. Evitar permitir cambios administrativos que invaliden la carga en preparación sin avisar; no impedir rendiciones/fin de una ruta ya en calle.
4. Reutilizar las consultas/reglas existentes. Si planificar, reasignar y despachar necesitan exactamente la misma sumatoria, mover esa regla puntual compartida dentro del módulo; no añadir framework de flota ni repositorio paralelo. No cambiar cálculos de tarifas ni completar el alta multibulto.
5. Corregir `Planificar.cshtml:68` dividiendo cm³ por 1.000.000. Mostrar volumen total con la misma fórmula/unidades y distinguir exceso de peso/volumen. JS solo orienta; el servidor decide. Conservar decimales de cálculo hasta comparación final; no truncar cada bulto a dos decimales de volumen.
6. Alinear `min/max/step`, validación servidor, límites y mensajes por campo; conservar datos/versiones ante 400/409/caída HTTP. Alinear la política de `/ConfiguracionReparto` con el menú/API, sin auditar ni rehacer permisos generales.
7. Acordar significado de espacios interiores/guiones en matrícula. Mantener por ahora Trim+ToUpperInvariant: no eliminar caracteres ni fusionar fichas existentes sin una regla confirmada. Reutilizar la ficha inactiva cuando la misma matrícula vuelve al servicio.

### Componentes afectados

- Backend: `VehiculoContract`, `Vehiculo`, `EfConfiguracionRepartoRepository`, `EfRutasRepository` y su parcial de reasignaciones, ejecución de ConfirmarCarga; contratos de error/OpenAPI si se refinan.
- Frontend: `VehiculoResponse` o modelo de entrada existente, `ConfiguracionRepartoModel`, `ConfiguracionReparto.cshtml`, `Program.cs`, `Planificar.cshtml`, `rutas-planificacion.js` y contratos locales.
- Pruebas: ampliar los archivos existentes `ConfiguracionRepartoHttpTests`, `RutasHttpTests`, los tests de reparto/cliente/page ya existentes. No crear una suite ni dependencia nuevas sin necesidad.

### Persistencia y contratos

No se necesita migración para leer capacidad vigente o corregir UI. Las columnas ya tienen escala dos; sí cambia su validación explícita. Un límite adicional en DB o nuevo registro histórico de cambios de capacidad necesitaría una migración deliberada, pero no son requisitos para el arreglo mínimo. El snapshot actual no se borra ni se sobrescribe para «arreglar» el historial.

Los contratos públicos deben actualizarse junto con ApiClient, OpenAPI y consumidores. El repositorio está en desarrollo: no agregar aliases/fallbacks para versiones anteriores. No borrar migraciones, datos ni volúmenes.

### Criterios de aceptación / prueba

- Dos bultos 1.000 + 2.000 g, 10×10×10 cm cada uno: 3.000 g y 2.000 cm³ exactos aceptados. Capacidad 2.999,99 g rechaza **peso**; 1.999,99 cm³ rechaza **volumen**. Rechazo conserva estados, versiones, reservas y número de hojas.
- Tras planificar con 3.000/2.000, reducir a 1.500/1.000: despacho rechazado de forma controlada. Mismo caso al reasignar y antes de confirmar salida. Aumentar capacidad no cambia snapshots históricos.
- Duplicar un envío o agregar un bulto ajeno no duplica carga ni cruza tenant. Suspendidas no suman al plan asignable; carga física residual no desaparece por suspensión.
- Cero, negativos y sobre máximo rechazados; mínimo y máximo aceptados; 1.005 se rechaza por escala si se adopta la recomendación. PUT y GET deben coincidir exactamente en valores/versiones.
- Matrícula normalizada única dentro del operador, permitida en otro; PUT con Id de otro operador responde 404 sin cambios; comercio/operador sin permiso no obtiene escritura.
- Dos editores con misma versión: uno guarda, otro recibe 409 conservando lo escrito. No reintentar automáticamente con una versión nueva ni perder el formulario.
- HTML inicial y JS muestran 4.000.000 cm³ como 4 m³; peso 1.000 g como 1 kg. Feedback para ambos excesos. Con JS ausente no se miente en unidades.
- Verificación real de navegador sobre datos temporales: navegación, labels, teclado/foco, error/éxito, doble envío, 320 CSS px y zoom. SSR no necesita skeleton artificial; usarlo solo ante carga asíncrona real.

## 3. B2 — reservas, ocupación y retorno confirmado

**Prerequisito de negocio:** aceptar explícitamente que FinJornada siga cerrando el trabajo con incidencias, pero deje de certificar por sí solo disponibilidad física. Conservar D18 y agregar el hecho de retorno/aptitud, no reinterpretarlo.

### Cambios propuestos

- Extender la hoja o el modelo de recurso con hechos de toma de ocupación, retorno y disponibilidad confirmados, actor y timestamps. Separar los instantes del dispositivo y recepción servidor cuando provengan de mobile. Modelo mínimo detallado en el documento 04.
- Antes de despacho operativo/adquisición de recurso, comprobar ocupación del vehículo **sin filtro de fecha** y la del repartidor cuando corresponda. Repetir al autorizar salida si despacho significara solo publicación anticipada. Hacerlo en la misma transacción que adquiere la ocupación; lock actual de operador + restricción única de ocupación activa como defensa final.
- La finalización administrativa no libera la nueva ocupación; la confirmación de disponibilidad sí. Cancelación de ruta vacía nunca iniciada sigue liberando su reserva, sin inventar un retorno.
- Una ruta finalizada con retorno pendiente debe ser visible aunque sea de ayer; no ocultarla por el filtro diario habitual. Mostrar «retorno no confirmado», no «libre» ni «ETA vencida = disponible».
- Permitir confirmar retorno aun con jornada cerrada. Custodia y descarga continúan sus comandos existentes; retorno no entrega ni recibe bultos. Recomendar que la habilitación siguiente requiera carga residual resuelta o excepción explícita, no contar la custodia pendiente como espacio libre.
- Aviso Backoffice derivado de la transición **confirmada en servidor** a disponible. Primer corte: listado/indicador y actualización por consulta; usar mensajería/outbox existente solo si hace falta aviso activo confiable. Evitar un nuevo canal paralelo por defecto.

### Contrato / migración

Requiere campos/índices o registro de ocupación/retorno, comandos de confirmación y DTO de disponibilidad, consumidores Backoffice/mobile y contratos OpenAPI actualizados juntos. Migración aditiva; **no** marcar todos los cierres históricos como retorno confirmado. Conciliación inicial explícita para activos, conservando historial/incidencias. No hacer esa migración durante esta auditoría.

### Aceptación

- D en curso y D+1 reservado: plan futuro permitido; adquisición de uso físico rechazada hasta liberar D. Dos intentos concurrentes adquieren como máximo una ocupación; errores no alteran ambas hojas.
- Varias rutas sucesivas del día: después de retorno/aptitud confirmado, nueva ruta puede ocupar; antes no. La primera versión puede conservar la reserva diaria actual; ventanas horarias solo si se necesitan varias reservas anticipadas el mismo día.
- Cruce de medianoche no libera nada. Una hoja vieja abierta sigue bloqueando uso físico; ruta futura publicada no vence ese bloqueo.
- Fin local offline muestra pendiente; Fin aplicado cierra jornada pero no libera ocupación nueva. Reintento de Fin/retorno conserva UUID/secuencia/respuesta y no duplica avisos. Un evento antiguo no puede liberar la ocupación de una ruta posterior.
- Cierre con incidencias preserva bultos y diario, incluso si retorno se confirma después. Retorno sin descarga puede quedar confirmado mientras disponibilidad permanece pendiente. No fabricar recepción ni entrega.
- Desactivar vehículo ocupado no libera ni bloquea resolver su custodia/retorno; sí impide volver a asignarlo al liberar.

Estas pruebas deben usar fixtures efímeras y reloj controlable existentes, no modificar hora ni datos de operación.

## 4. B3/B4 — base y estimación inicial

### Cambios mínimos y reutilización

- Configurar una base por operador, dirección + coordenadas confirmadas + versión/autor/fecha. Reutilizar patrón de propuestas/confirmación y geocodificación; contacto de identidad visual no es fuente de base.
- Agregar salida planificada separada de `SalidaEnUtc`; servicio por parada con valor por defecto del operador y margen de retorno configurable. La fecha/hora completa admite cruce de medianoche, usando zona IANA/UTC del stack existente.
- Guardar el snapshot de base, orden/versión de ruta, parámetros y calidad/fecha/proveedor del cálculo. Modificar la base actual no cambia rutas históricas ni confirma nuevos tiempos por sí solo.
- Contrato propuesto de routing: coordenadas ordenadas, salida, perfil de vehículo; segmentos con duración/distancia, datos de generación y errores tipados. No optimiza el orden ni devuelve promesas exactas.
- Calcular secuencialmente base → paradas activas en orden → base, incluyendo servicio y margen; detalle en 04. Mostrar desconocido cuando falte información, no cero minutos.

### Migración/contratos y pruebas

Se requieren persistencia de base/salida prevista/parámetros/estimación y DTO/campos de UI. No credenciales hasta seleccionar y autorizar proveedor. Un adaptador puede probarse contra un proveedor de prueba determinista sin tráfico real ni contratación.

Criterios: tenant A/B; coordenadas inválidas/no confirmadas; viaje y servicio por cada tramo; igualdad de orden; sin paradas; cruza medianoche; fallo/timeout/cuota; no vial posible; tiempos viejos quedan rotulados; retraso no confirma retorno; cambiar composición/base invalida o recalcula estimación. Preservar las horas manuales actuales como **datos manuales identificados**, no llamarlas calculadas; decidir si se reemplazan o conviven antes del cambio de contrato.

## 5. B5 — actualización desde posición reciente

- Reutilizar Posicion con su timestamp/precisión y el sincronizador; distinguir recepción reciente de GPS antiguo. Solo usar posición del operador/repartidor/ocupación actual y no futura.
- Recalcular recorrido pendiente desde posición admisible, no volver a sumar tramos recorridos. Conservar estimación inicial para comparar plan/real y mostrar última actualización.
- GPS viejo/impreciso/offline o fallo proveedor: conservar estimación anterior rotulada como desactualizada o pasar a desconocida; no inventar una posición ni liberar recursos.
- Frecuencia, umbrales GPS y política de retrasos son parámetros pendientes con recomendaciones del documento 04. No construir optimización dinámica de rutas.

Aceptación: GPS fuera de orden, respuesta vieja del proveedor, posición de otra ruta, desconexión/reintento, retraso y cruce de día no regresan estado confirmado ni reemplazan un cálculo nuevo con uno viejo. Aviso de disponibilidad solo por confirmación aplicada.

## 6. Qué NO hace falta construir

- Otro CRUD de vehículos, una nueva gestión de repartidores o un framework genérico de flota.
- DELETE físico para satisfacer una baja lógica que conserva historia.
- Empaquetado 3D, peso volumétrico tarifario, optimización avanzada o tracking completo.
- Completar CU-08 como prerequisito artificial de la corrección actual: el consumidor ya debe sumar colecciones, y el alta multibulto se entrega aparte.
- Contratar proveedor, agregar credenciales, cambiar despliegue/CI o base operativa durante la auditoría.

## 7. Secuencia de entrega futura

1. Autorizar implementación B1 con las decisiones de escala/capacidad explícitas; reproducir H01/H04 con tests de regresión RED antes de corregir.
2. Acordar D1–D5 y realizar B2 sin depender de ETA; preservar D18 y conciliar recursos existentes.
3. Configurar base y parámetros B3; elegir contrato/proveedor B4 sin asumir que geocodificación resuelve routing.
4. B5 solo cuando existan B4 y política de calidad de posición.

Cada bloque entrega su código, pruebas y documentación juntos, bajo instrucciones del proyecto y Gentle-AI. Este documento **no inicia** esas entregas, no crea ramas ni commits y no reemplaza el consentimiento de implementación.

## Actualización de implementación B3 — 2026-11-01

El plan y sus antecedentes anteriores se conservan como históricos. B1 está documentado en05 y B2 permanece técnicamente verificado conforme a08, sin reapertura de su aceptación. B3 se implementó según la separación de la tabla1: base y planificación temporal, no cálculo vial. Ver [09-implementacion-b3.md](09-implementacion-b3.md) para código, pruebas, contrato, migración y limitaciones. B4/B5, revisión nativa y habilitación operativa siguen pendientes. CU06 no se declara completo.
