# Recuperación de contraseña

El flujo público permite que cada persona recupere únicamente su propia cuenta demostrando control del correo registrado. No existe una operación de restablecimiento desde la gestión de usuarios. Recuperar credenciales no reactiva accesos ni organizaciones suspendidas.

## Uso

En Commerce (`http://localhost:5102`), Backoffice (`http://localhost:5101`) y Admin (`http://localhost:5104`), elegí **¿Olvidaste tu contraseña?**, ingresá el correo y abrí el enlace recibido. El sistema presenta la misma confirmación para correos existentes y desconocidos. Los enlaces vencen en 15 minutos por defecto, y solo pueden usarse una vez.

El correo lleva a la página fija configurada en `PasswordRecovery:ResetPageUrl`; la API no deriva su autoridad del encabezado `Host` ni recibe una URL de retorno. La página retira el token de la URL antes de renderizar, lo conserva temporalmente en una cookie protegida `HttpOnly` y lo envía a la API solo al guardar la contraseña nueva.

En Compose de desarrollo, Mailpit recibe SMTP dentro de la red (`mailpit:1025`). Su bandeja está publicada únicamente en loopback: <http://localhost:8025>. Los mensajes y enlaces locales son de prueba y no deben usarse para recuperación real.

## Configuración de despliegue

Configurá el envío SMTP con estas claves (`Email__Smtp__...` en variables de entorno):

| Clave | Descripción |
| --- | --- |
| `Email__Smtp__Host`, `Email__Smtp__Port` | Servidor y puerto del relay SMTP real. |
| `Email__Smtp__UseSsl` | Habilita TLS según el relay. |
| `Email__Smtp__FromAddress`, `Email__Smtp__FromName` | Remitente visible. |
| `Email__Smtp__Username`, `Email__Smtp__Password` | Credenciales opcionales del relay; almacenarlas en el gestor de secretos del despliegue. |
| `PasswordRecovery__ResetPageUrl` | URL HTTPS fija de la página de restablecimiento del portal Commerce, sin query ni fragmento. |
| `PasswordRecovery__TokenLifespanSeconds` | Vigencia entre 1 y 3600 segundos; el valor predeterminado es 900. |
| `DataProtection__KeysDirectory` | Directorio persistente y protegido para las claves de ASP.NET Data Protection. |

Producción debe configurar su propio relay SMTP: Mailpit solo está definido en el Compose de desarrollo. Conservá el anillo de claves de Data Protection en almacenamiento persistente, con acceso restringido y compartido por todas las instancias de la API; de lo contrario, los enlaces aún vigentes pueden dejar de validarse tras un reinicio o entre réplicas. No registrar cuerpos de correo, tokens ni secretos SMTP.

La migración `AddUsuarioCredentialVersion` agrega una versión global de credenciales para revocar JWT anteriores al cambio de contraseña, incluso para identidades todavía sin organización. Aplicá la migración como una operación administrativa separada antes de desplegar la API que la requiere.
