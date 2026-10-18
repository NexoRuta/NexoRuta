# Recuperación de contraseña: flujo y observación local

La API responde igual para cuentas existentes e inexistentes. Para una cuenta real, guarda dos mensajes en la única tabla `OutboxMessages`; dos workers por broker se encargan de publicarlos y procesarlos. El correo nunca se envía desde la API y ningún worker cambia contraseñas.

## Recorrido

1. La API genera el token ASP.NET Identity, cifra el comando de correo con Data Protection y escribe atómicamente el comando Rabbit y el evento Kafka. La cuenta inexistente no crea filas ni evento.
2. `worker` (RabbitWorker) publica mensajes de Rabbit y ejecuta consumidores separados para seguimiento y correo. El comando de correo viaja como JSON `{ "protectedCommand": "..." }`; el destinatario, token y enlace solo aparecen dentro del contenido protegido.
3. `worker-kafka` (KafkaWorker) publica eventos de Kafka y persiste `PasswordRecoveryRequested` en MongoDB. El evento lleva únicamente `eventId`, `schemaVersion`, `usuarioId` y `occurredAt`; Kafka usa el usuario como clave de partición para conservar el orden del agregado.
4. El RabbitWorker valida la vigencia del enlace antes de SMTP. Si ya venció, marca `EstadoEntrega=Expired` y lo confirma sin mandar un enlace inútil. Si SMTP acepta el correo, marca `Delivered` y recién entonces confirma Rabbit.
5. El enlace vuelve al portal y el usuario envía el token y la contraseña nueva a la API. Identity valida vigencia, uso único y política; la transacción incrementa `VersionCredencial` y mantiene la revocación de sesiones/JWT. El flujo no activa accesos ni organizaciones suspendidas.

`OutboxMessages.Estado=Publicado` significa que el broker confirmó la publicación; **no** significa que SMTP entregó el mensaje. El estado de correo es independiente: `Pending`, `Delivered`, `Expired` o `Failed`. `Failed` se escribe al procesar la cola de fallidos después de agotar los reintentos Rabbit.

## Iniciar desarrollo

En Windows, ejecutá `levantar-entorno-dev.bat`. El script valida el destino local (`nexoruta` / `postgres` / base `nexoruta`), aplica migraciones pendientes, provisiona los roles restringidos, ejecuta el bootstrap de las seis cuentas de desarrollo configuradas en `.env` y levanta el entorno combinado sin borrar volúmenes.

El entorno combinado conserva dos procesos de mensajería:

| Proceso | Publica | Consume |
| --- | --- | --- |
| `worker` | RabbitMQ | Seguimiento y correo de recuperación |
| `worker-kafka` | Kafka | Solicitudes de recuperación y persistencia MongoDB |

Mailpit queda disponible en <http://localhost:8025>; los servicios usan SMTP `mailpit:1025`. El anillo persistente de Data Protection se comparte entre API y RabbitWorker; el worker solo necesita leer las claves.

## Observar una solicitud

| Dónde | Qué revisar |
| --- | --- |
| Mailpit | Abrí <http://localhost:8025> y verificá el correo recibido, su enlace y fecha. No copies el enlace a logs ni tickets. |
| RabbitMQ | Abrí <http://localhost:15672> con las credenciales técnicas de `.env`. Revisá `nexoruta.password-recovery.email.v1` y `nexoruta.password-recovery.email.dead.v1`. La cola de seguimiento sigue separada. |
| Kafka | El tópico es `nexoruta.password-recovery.requested.v1`. Observá eventos nuevos con `docker compose -p nexoruta -f compose.yaml -f compose.dev.yaml --profile kafka exec kafka kafka-console-consumer --bootstrap-server kafka:9092 --topic nexoruta.password-recovery.requested.v1 --from-beginning --max-messages 5 --property print.key=true`. Los valores no contienen datos del correo. |
| MongoDB | Base `nexoruta_security`, colección `password_recovery_requested`; conectate con las credenciales de `.env` desde MongoDB Compass o `mongosh`. Cada documento contiene `eventId`, `schemaVersion`, `usuarioId` y `occurredAt`. |
| PostgreSQL | `OutboxMessages` contiene ambos ámbitos. Las filas de envío tienen `OperadorId`/`EnvioId`; las de identidad tienen ambos nulos y `ClaveAmbito=usuarioId`. La API no tiene lectura general de esta tabla. Usá logs con `docker compose -p nexoruta -f compose.yaml -f compose.dev.yaml --profile kafka logs -f worker worker-kafka`. |

Mongo crea un índice único en `eventId` para reentregas idempotentes y un índice TTL de 90 días sobre `occurredAt`. Kafka local conserva los eventos durante 30 días. Un offset solo se confirma después de insertar el documento o reconocer una duplicación por índice único.

## Reintentos, prioridades y límite SMTP

- Seguimiento y correo usan prioridad alta; `EnvioCreado` es normal; `PasswordRecoveryRequested` es baja porque es un evento de auditoría/observabilidad y no una señal de entrega.
- El reclamo ordena por prioridad efectiva y antigüedad. Cada cinco minutos de espera promueve un nivel, hasta alta: un mensaje bajo alcanza alta tras diez minutos y, dentro del nivel, se respeta FIFO. Así una carga continua de altas no deja las bajas esperando indefinidamente.
- RabbitMQ local corre 4.3.6. La cola de correo es quorum y ya soporta prioridades estrictas; el publicador envía 0/16/31 para baja/normal/alta, sin añadir argumentos incompatibles a la cola existente. La cola de seguimiento es classic sin `x-max-priority`; allí decide el planificador del outbox.
- Kafka aplica prioridad solo antes de publicar. No reordena eventos ya escritos: el outbox bloquea mensajes posteriores del mismo ámbito/clave mientras el anterior siga sin publicar.
- Los enlaces vencidos nunca se envían, independientemente de su prioridad. SMTP es al menos una vez: si el servidor acepta el correo y el proceso cae antes de guardar `Delivered` o confirmar el ACK Rabbit, el reintento puede duplicarlo. No existe garantía exactamente-una-vez sin idempotencia del relay SMTP.

## Configuración

| Clave | Uso |
| --- | --- |
| `PasswordRecovery__ResetPageUrl` | URL fija HTTPS de la página Commerce; sin query ni fragmento. |
| `PasswordRecovery__TokenLifespanSeconds` | Vigencia entre 1 y 3600 segundos; desarrollo usa 900. |
| `DataProtection__KeysDirectory` | Anillo persistente compartido; todas las instancias usan `NexoRuta.Api` como nombre de aplicación. |
| `Email__Smtp__...` | Relay y remitente. Desarrollo apunta a Mailpit; producción debe configurar un SMTP real. |
| `MongoDb__ConnectionString`, `MongoDb__Database`, `MongoDb__PasswordRecoveryCollection` | Credenciales técnicas y destino MongoDB. |

Los logs de recuperación registran etapa, tipo de excepción e identificador de correlación, nunca correo, destinatario, token, enlace, cuerpo, credenciales ni respuesta SMTP.
