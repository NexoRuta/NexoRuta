# Demostraciones 31–41

Usar un checkout de `feature/cambiosrequerimientos` con sus gitlinks exactos. El [PDF de requisitos](Cambios%20de%20Requerimientos%20Planificados.pdf), el [ADR](ADR-031-041.md) y la [validación ejecutada](VALIDACION.md) acompañan esta guía. No usar bases, certificados ni archivos del Windows del usuario.

## Preparación aislada en Cloud/Linux

Se requieren Docker con acceso al daemon y red para descargar dependencias. Reservar espacio para PostgreSQL/PostGIS, Kafka, RabbitMQ, Mongo y artefactos .NET; este entorno de 32 GB agotó espacio al ejecutar muchas bases de integración simultáneamente. No borrar datos persistentes para obtener espacio.

```bash
git clone --branch feature/cambiosrequerimientos --recurse-submodules https://github.com/NexoRuta/NexoRuta.git
cd NexoRuta
python3 scripts/cloud/verify-gitlinks.py
bash scripts/cloud/environment-install.sh
source scripts/cloud/env-agent.sh
```

En un sandbox que solo permita escribir en `/workspace` y `/tmp`, configurar cachés escribibles antes de instalar/restaurar:

```bash
export NUGET_PACKAGES=/workspace/.nuget/packages
export NUGET_HTTP_CACHE_PATH=/workspace/.nuget/http-cache
export DOTNET_CLI_HOME=/workspace/.dotnet-home
export npm_config_cache=/workspace/.npm
export PLAYWRIGHT_BROWSERS_PATH=/workspace/.cache/ms-playwright
export DOTNET_PROCESSOR_COUNT=1
```

Arrancar una única base sintética propia. `env-agent.sh` selecciona PostgreSQL Docker. Si hay otro checkout con su contenedor, detener sus procesos y elegir un nombre distinto con `NEXORUTA_CLOUD_CONTAINER`; nunca copiar su `private.json`.

```bash
python3 scripts/cloud/dev.py start
python3 scripts/cloud/dev.py verify
python3 scripts/cloud/demo-brokers.py start
python3 scripts/cloud/demo-cambios.py setup
```

`setup` publica reglas que permiten parcial, nueva visita con recargo de 25 UYU, tarifa propia de retiro y cobertura sintética de Montevideo. Crea tres bultos de entrega y uno de retiro, recibe físicamente los de entrega, planifica y despacha una ruta mixta. No registra carga ni salida al despachar. Los scripts verifican la marca de propiedad del runtime y solo llaman HTTP loopback; no consumen proveedores pagos.

Las credenciales aleatorias quedan únicamente en `.local/codex-cloud/private.json`, ignorado y con modo 600. Para ingresar manualmente a los portales, leer de ese archivo `operatorEmail/operatorPassword` y `commerceEmail/commercePassword` en la máquina local. No pegar su contenido en incidencias, logs ni documentación. `demo-cambios.json` conserva las identidades de la demostración y, después de `finish`, sus enlaces públicos.

## A. Parcial sin conexión y reinicio

El ejecutable portátil usa los ensamblados reales Core, Application, Api y Storage de Mobile: SQLite y archivos cifrados en disco, sesión persistida y API/PostgreSQL reales. El transporte controlado bloquea **todas** sus peticiones HTTP durante la captura. No es un emulador Android.

```bash
dotnet run --project tests/Cambios.DemoMobile -- "$PWD" offline
# El proceso anterior termina con dos operaciones y tres evidencias guardadas.
dotnet run --project tests/Cambios.DemoMobile -- "$PWD" sync
python3 scripts/cloud/demo-cambios.py finish
```

El primer proceso descarga la hoja, inicia jornada, escanea solo dos de los tres bultos, confirma salida y corta su transporte. Registra entrega de dos, motivo AUSENTE para el tercero y un retiro con foto y firma. Comprueba que la sincronización falla por desconexión y termina. El segundo proceso abre la misma SQLite, sesión y claves, recupera evidencias, sincroniza y exige confirmaciones `Aplicada` de la API. Luego rinde el retiro y cierra la jornada. Las fotos sintéticas son PNG válidos; la firma de esta herramienta es una imagen de prueba, no una captura humana.

`finish` comprueba 2/3, el enlace generado por el Worker RabbitMQ, conteos públicos sin IDs internos y el aviso recibido por Kafka real en Commerce. Recibe el retiro y confirma entrega al comercio. Constata retorno y liberación del vehículo mediante comandos separados. Si los workers aún procesan el outbox, esperar a que estén listos antes de `finish`; no repetir comandos físicos manualmente para resolver un error de conectividad.

Comprobación visual:

- Backoffice `http://127.0.0.1:5101/`: envío parcial y detalle por bulto; `/rutas/{rutaId}` muestra visita completada, no suspensión ficticia. `/ReporteOperaciones` incluye entregas, retiros e importes.
- Commerce `http://127.0.0.1:5102/avisos`: cambios por bulto y operación. `/envios/{id}` conserva el circuito de seguimiento existente.
- Tracking `http://127.0.0.1:5103/seguimiento/{token}`: usar el token de `demo-cambios.json`, `links.entregaId.url`; se muestra «2 de 3 bultos entregados» sin identidad interna.

Para otra visita del pendiente:

```bash
python3 scripts/cloud/demo-cambios.py revisit
```

Se exige una ruta que incluya solamente el tercer bulto y un incremento acumulado de exactamente 25 UYU en la nueva versión tarifaria. La visita anterior conserva sus tres miembros históricos. Este paso deja la segunda ruta despachada para inspección; no inventa otra entrega.

## B. Ruta mixta y cierre del retiro

La misma demostración es deliberadamente mixta: vehículo de 3500 g y 3500 cm³, entrega inicial de tres bultos de 1000 g/1000 cm³, retiro de uno de 1000 g/1000 cm³. Entregar antes de retirar permite el plan; retirar antes de descargar produciría 4000 y debe rechazarse. El servidor comprueba también la carga física al retirar, porque una entrega fallida puede no haber descargado. Las pruebas `OrdenMixtoPermiteDescargarAntes...` cubren por separado peso y volumen; `C37_RetiroPorApi...` recorre planificación, retiro fallido/exitoso, recepción y entrega al comercio bajo rol restringido.

Inspeccionar la ruta en Backoffice y el formulario Commerce `/retiros/crear`: seleccionar operador, comprador, domicilio, coordenadas sintéticas (-34.9, -56.2), franja UTC, motivo, bulto y servicio Retiro; calcular tarifa y solicitar. Sin motivo se conserva el formulario y se informa el error. No usar un geocodificador real para esta prueba.

La automatización reproducible navega ambos portales, guarda/reabre un borrador de reglas sin publicarlo, solicita un retiro por el formulario real y revisa las pantallas a 1440 y 320 px, texto al 200 %, foco por teclado y axe:

```bash
node scripts/cloud/verify-cambios-ui.cjs
```

Necesita `finish` para disponer del enlace de seguimiento. Guarda resultados y capturas solo en `.local/codex-cloud/`. Agrega un retiro sintético y deja un borrador de reglas; no es una comprobación de solo lectura.

## Mobile Android

En una máquina con MAUI Android y dispositivo/emulador, usar la app existente contra una API HTTPS de desarrollo confiable. Repetir descarga, carga de dos, modo avión, escaneo/foto/firma, cierre del proceso y reapertura antes de reconectar; comprobar la cola y luego los mismos resultados en portales. Las imágenes XAML y acceso nativo a cámara/escáner/firma requieren ese recorrido. No se ejecutó aquí: faltan `maui-android`, adb y emulador. La prueba portátil no acredita esas integraciones nativas.

## Detener sin perder datos

```bash
python3 scripts/cloud/demo-brokers.py stop
python3 scripts/cloud/dev.py stop
```

Se detienen los procesos propios; se conservan brokers y datos. Para recompilar un runtime activo primero detenerlo. No ejecutar `docker volume prune`, restaurar respaldos ajenos ni borrar migraciones.
