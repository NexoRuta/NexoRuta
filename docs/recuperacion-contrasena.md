# Recuperación de contraseña

El flujo público confirma la solicitud de forma genérica, conserve o no el sistema la cuenta. Recuperar credenciales no reactiva accesos desactivados ni organizaciones suspendidas. La persona establece la contraseña nueva en la API al abrir el enlace; ningún worker cambia contraseñas.

## Flujo

1. La API busca la identidad y genera un token de ASP.NET Identity. Para una cuenta existente, protege con Data Protection el destinatario, el token y el enlace; en una transacción de PostgreSQL agrega un comando de correo y el evento `PasswordRecoveryRequested` a `SecurityOutboxMessages`. Una identidad inexistente no genera mensajes.
2. Los workers reclaman filas con reserva, las publican y marcan como publicadas solo después de la confirmación de RabbitMQ o Kafka. La API no conecta con esos brokers ni con SMTP.
3. RabbitMQ entrega el comando cifrado a `nexoruta.password-recovery.email.v1`. `worker-mail` lo descifra con el anillo estable de Data Protection, verifica la caducidad y envía SMTP. Un enlace vencido se marca `Expired` y no se envía. Ante fallas transitorias espera 5 segundos y rechaza con requeue; el límite de 10 entregas de la cola quorum lo deriva a `nexoruta.password-recovery.email.dead.v1`. Usa `basic.reject` para que RabbitMQ 4.3 incremente el contador de fallas; `basic.nack` permitiría reencolar sin límite.
4. Kafka recibe el evento versionado `nexoruta.password-recovery.requested.v1`. Su contrato incluye `eventId`, `schemaVersion`, `usuarioId` y `occurredAt`; no incluye correo, token, enlace, contraseña, IP ni cuerpo de correo. No significa que el correo se entregó.
5. `worker-mongodb` persiste el evento en `nexoruta_security.password_recovery_requested`, usando `eventId` como campo único. El consumidor confirma el offset después de insertar o reconocer una reentrega duplicada.
6. El portal conserva el enlace para restablecer la contraseña por la API. ASP.NET Identity valida vigencia y uso único; la transacción de cambio incrementa `VersionCredencial` y conserva la revocación de JWT en todos los ámbitos.

SMTP es **al menos una vez**, no exactamente una vez: si el servidor aceptó el mensaje y el worker cae antes de guardar el estado o confirmar el ACK Rabbit, el reintento puede enviar un duplicado. El estado final evita la mayoría de las reentregas posteriores, pero no puede cerrar esa ventana sin soporte idempotente del servidor SMTP.

## Entorno local y observación

Ejecutá `levantar-entorno-dev.bat` desde Windows o `docker compose -p nexoruta -f compose.yaml -f compose.dev.yaml --profile kafka up -d --build`. El script verifica que las migraciones apunten a `Host=postgres;Database=nexoruta`, provisiona los roles restringidos, aplica migraciones locales pendientes y levanta los brokers, workers, portales y Mailpit sin borrar volúmenes.

| Componente | Cómo observar |
| --- | --- |
| Mailpit | Abrí <http://localhost:8025>. SMTP local es `mailpit:1025`, remitente `noreply@nexoruta.local`. |
| RabbitMQ | Abrí <http://localhost:15672> con las credenciales técnicas de `.env`. Revisá `nexoruta.password-recovery.email.v1` y `nexoruta.password-recovery.email.dead.v1`; el mensaje Rabbit contiene solo el payload cifrado. La cola de seguimiento existente se conserva separada. |
| Kafka | El tópico local es `nexoruta.password-recovery.requested.v1` y conserva eventos por 30 días. Para inspeccionarlo: `docker compose -p nexoruta -f compose.yaml -f compose.dev.yaml --profile kafka exec kafka kafka-console-consumer --bootstrap-server kafka:9092 --topic nexoruta.password-recovery.requested.v1 --from-beginning --max-messages 1`. El evento contiene identificadores y fecha, nunca datos del correo. |
| MongoDB | El worker escribe en la base `nexoruta_security`, colección `password_recovery_requested`; el puerto local es `127.0.0.1:27017`. Usá las credenciales Mongo de `.env` desde `mongosh` o MongoDB Compass y consultá `eventId`, `schemaVersion`, `usuarioId` y `occurredAt`. |
| PostgreSQL | `SecurityOutboxMessages` contiene el outbox del correo y del evento. El payload de correo está protegido y el estado de entrega se observa en `DeliveryState` (`Pending`, `Delivered`, `Expired` o `Failed`). La tabla global no tiene `OperadorId`/`EnvioId` ficticios ni amplía la lectura RLS de envíos. |

MongoDB agrega índice único en `eventId` e índice TTL en `occurredAt` con retención de **90 días**; documentos vencidos se eliminan automáticamente. Kafka conserva eventos 30 días en Compose local para permitir la recuperación del consumidor.

## Configuración de despliegue

Configurá el relay SMTP en el worker de correo (`Email__Smtp__...`): host/puerto, TLS, remitente y credenciales opcionales. Producción debe usar un relay real, no Mailpit.

| Clave | Uso |
| --- | --- |
| `PasswordRecovery__ResetPageUrl` | URL HTTPS fija del portal Commerce, sin query ni fragmento. |
| `PasswordRecovery__TokenLifespanSeconds` | Vigencia del token entre 1 y 3600 segundos; Compose usa 900. |
| `DataProtection__KeysDirectory` | Anillo persistente y protegido, compartido entre API y worker de correo. El worker solo necesita lectura; todas las instancias deben usar `NexoRuta.Api` como nombre de aplicación. |
| `MongoDb__ConnectionString`, `MongoDb__Database`, `MongoDb__PasswordRecoveryCollection` | Conexión técnica y destino del consumidor Mongo. |

No registres correo, destinatario, token, enlace, cuerpo, credenciales ni respuestas SMTP. Los logs de recuperación usan solo etapa, tipo de excepción e identificador de correlación. La migración `AddPasswordRecoverySecurityOutbox` además inicializa los `SecurityStamp` nulos de identidades heredadas; el token provider de Identity los requiere para generar enlaces de restablecimiento.
