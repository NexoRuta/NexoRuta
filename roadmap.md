## La historia que vamos a mostrar

> “Un comercio registra un envío de dos bultos. El operador los recibe, organiza el reparto y publica la ruta. El repartidor verifica la carga, realiza la entrega y el destinatario puede consultar el resultado.”

Usaremos tres superficies:

- **Commerce:** http://localhost:5102
- **Backoffice:** http://localhost:5101
- **Aplicación Android del repartidor.**

También dejaremos abierto el enlace público de seguimiento del envío.

## Antes de presentar

Ensayar el recorrido completo con un envío nuevo. Para la presentación crear otro, con códigos diferentes.

Dejar preparado:

- Las sesiones de comercio y operador en ventanas separadas.
- El emulador con su cuenta de repartidor, cámara y conexión comprobadas.
- Un vehículo disponible para el día de la demostración.
- Una dirección dentro de la cobertura del operador.
- Las reglas de evidencia conocidas: qué pide de nombre, documento, foto y firma.
- GPS del emulador funcionando.
- Una forma ensayada de mostrar los códigos de las etiquetas a la webcam.

La ruta debe tener la fecha operativa del día y horarios compatibles con la franja elegida.

## 1. El comercio crea el envío

**Pantalla:** Commerce → Crear envío.

Datos de ejemplo:

| Campo | Valor |
|---|---|
| Destinatario | Demo Profesor |
| Correo | demo.profesor@example.test |
| Dirección | Una dirección ya cubierta por el operador |
| Modalidad | Estándar |
| Bulto 1 | Código único, 1000 g, 20 × 20 × 20 cm |
| Bulto 2 | Código único, 1500 g, 30 × 20 × 10 cm |

**Total:** 2 bultos, 2,5 kg y 0,014 m³.

Acciones:

1. Seleccionar operador.
2. Completar destinatario y destino.
3. Seleccionar el servicio disponible.
4. Agregar ambos bultos.
5. Calcular la tarifa.
6. Mostrar el importe y confirmar el envío.

**Qué explicar:**

> “El comercio declara qué necesita enviar. El sistema calcula el precio con la configuración vigente del operador.”

**Resultado que mostrar:** el envío creado, sus dos bultos y la tarifa aplicada.

## 2. Mostrar las etiquetas y el seguimiento

Desde el envío, descargar las etiquetas y abrir su enlace público.

Mostrar que cada bulto tiene su identificación.

**Qué explicar:**

> “El envío agrupa dos bultos, pero cada uno se identifica individualmente para controlar su recepción y su carga.”

Dejar el seguimiento abierto para volver al final.

## 3. Recibir los bultos en depósito

**Pantalla:** Backoffice → Depósito → recepción.

Acciones:

1. Identificar o escanear el primer bulto.
2. Cotejar peso y dimensiones.
3. Confirmar la recepción conforme.
4. Repetir con el segundo.

Para este recorrido, las medidas físicas coinciden con las declaradas.

**Qué explicar:**

> “Crear un envío no significa que el operador ya tenga los paquetes. La recepción registra que los bultos llegaron físicamente al depósito.”

**Resultado que mostrar:** los dos bultos recibidos y su custodia en depósito.

## 4. Planificar la ruta

**Pantalla:** Backoffice → Rutas → Planificar ruta.

Acciones:

1. Seleccionar el repartidor que está usando el emulador.
2. Seleccionar un vehículo disponible.
3. Elegir la fecha operativa del día.
4. Seleccionar el envío.
5. Revisar salida, llegada y tiempo de servicio.
6. Mostrar peso y volumen frente a la capacidad.
7. Guardar la planificación.

**Qué explicar:**

> “Ahora asignamos el trabajo a un repartidor y un vehículo. El sistema comprueba las restricciones de la ruta y su capacidad.”

**Resultado que mostrar:** ruta planificada con una parada y dos bultos.

## 5. Despachar la ruta

Abrir el detalle y pulsar **Despachar ruta**.

**Qué explicar:**

> “El despacho publica la hoja para el repartidor. La carga física se confirma después, desde la aplicación.”

Mostrar que la ruta queda despachada y los bultos todavía figuran en depósito.

## 6. Descargar la hoja e iniciar la jornada

**Pantalla:** Android → Mi jornada.

Acciones:

1. Actualizar y abrir la ruta correspondiente.
2. Mostrar la parada y los dos bultos.
3. Pulsar **Iniciar jornada**.

**Qué explicar:**

> “El repartidor recibe su hoja de trabajo y comienza la preparación de la jornada.”

## 7. Verificar la carga y comenzar el reparto

En Android:

1. Escanear el código del primer bulto.
2. Mostrar el avance de la carga.
3. Escanear el segundo.
4. Comprobar **2 de 2 bultos confirmados por el servidor**.
5. Pulsar **Comenzar reparto**.

**Qué explicar:**

> “El repartidor verifica los bultos que realmente lleva. Al comenzar el reparto queda registrada la salida.”

Volver brevemente al Backoffice y actualizar.

**Resultado que mostrar:**

- Ruta en curso.
- Salida física registrada.
- Envío en tránsito.
- Bultos bajo custodia del repartidor.

## 8. Registrar la entrega

**Pantalla:** Android → parada → Registrar entrega.

Acciones:

1. Identificar los dos bultos entregados.
2. Completar el nombre del receptor.
3. Completar documento, foto y firma según las reglas aplicables.
4. Confirmar la entrega.
5. Comprobar su confirmación por el servidor.

**Qué explicar:**

> “La entrega conserva la identificación de los bultos, los datos del receptor y las pruebas exigidas por el operador, junto con la hora y ubicación.”

**Resultado que mostrar:** estado **Entregado**.

Si aparece **Entrega pendiente de validación**, revisar y completar la prueba faltante antes de presentar la entrega como terminada.

## 9. Mostrar el mismo resultado en las otras aplicaciones

Actualizar:

- **Backoffice:** envío entregado y custodia del destinatario.
- **Commerce:** resultado del envío e historial.
- **Seguimiento público:** estado Entregado.

**Qué explicar:**

> “La operación registrada por el repartidor se refleja en las consultas del operador, del comercio y del destinatario.”

Cerrar el recorrido mostrando el historial y la transición desde la creación hasta la entrega.

## 10. Cierre operativo, si queda tiempo

En Android, terminar la jornada.

En Backoffice → Flota:

1. Mostrar la jornada cerrada.
2. Confirmar el retorno físico.
3. Confirmar disponibilidad y liberar el vehículo.

**Qué explicar:**

> “El cierre de la jornada, el regreso del vehículo y su disponibilidad se registran por separado.”

## Extensiones después del recorrido principal

Cuando el circuito normal esté ensayado, podemos agregar:

- **Entrega parcial:** entregar uno de dos bultos y registrar el motivo del pendiente.
- **Sin conexión:** registrar una entrega offline y mostrar su confirmación después de sincronizar.
- **Retiro en domicilio:** mostrar su solicitud y recorrido hasta el comercio.

Cada extensión necesita su propio envío de prueba. Primero dejamos sólido el recorrido principal.

## Frase final

> “Mostramos el circuito completo de un envío: alta, tarifa, identificación de bultos, recepción física, planificación, despacho, carga, entrega y seguimiento.”