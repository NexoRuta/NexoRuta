# Demostración sintética y reproducible

Ejecutar desde el superproyecto con sus gitlinks publicados. Requiere .NET del `global.json`, Docker local, Node y Chromium de Playwright. No usa VM, bases existentes, proveedores SMTP ni servicios de mapas facturables. No ejecutar `dev.py reset`, apply/destroy/import, despliegues, borrados de topics ni cambios de offsets de otros ambientes. Las validaciones estáticas autorizadas se ejecutan mediante el CI existente, con backend remoto deshabilitado.

## Preparar binarios y navegador

```bash
dotnet restore backend/NexoRuta.sln --locked-mode
dotnet restore frontend/NexoRuta.sln --locked-mode
dotnet build backend/NexoRuta.sln -c Release --no-restore
dotnet build frontend/NexoRuta.sln -c Release --no-restore \
  -p:OfficialDepartmentSource="$PWD/backend/src/ZonasCobertura/Data/departamentos-uruguay.geojson"
npm ci --prefix backend/tests/browser
backend/tests/browser/node_modules/.bin/playwright install chromium
export NEXORUTA_PLAYWRIGHT_MODULE="$PWD/backend/tests/browser/node_modules/playwright"
export NEXORUTA_OPERATIONAL_E2E_DIR="$PWD/backend/artifacts/browser/operational"
```

En Cloud cargar antes `scripts/cloud/env-agent.sh` y usar caches escribibles. Si Node debe usar el proxy configurado por el entorno, habilitar `NODE_USE_ENV_PROXY=1`; no se reemplazan los SDK de mapas por imitaciones ni se realizan consultas a proveedores de geocodificación.

## Recorrido breve

```bash
dotnet test backend/tests/NexoRuta.IntegrationTests/NexoRuta.IntegrationTests.csproj \
  -c Release --no-build --no-restore \
  --filter 'FullyQualifiedName~NexoRuta.IntegrationTests.Operacion' \
  --logger trx --results-directory backend/artifacts/operacion
```

Los nueve escenarios crean sus servicios y bases efímeros. La colección se ejecuta de forma exclusiva para reducir el pico de disco del driver Docker VFS; no reduce los casos.

1. **Seguimiento y tablero reales en Chromium.** Crear un envío sintético, despachar, cargar y confirmar. Publicar por el circuito legítimo su token cifrado. Comprobar el intervalo manual previsto de cinco minutos y su procedencia. Registrar un intento fallido aceptado: el intervalo deja de aplicar. Registrar GPS aceptado. Abrir el seguimiento sin cuenta, solicitar otra visita y repetir la solicitud sin duplicarla. Ingresar en Backoffice, revisar la solicitud y aprobarla con el comando privado. El tablero ya abierto observa `Reprogramado` mediante outbox → Kafka → proyección → SignalR. La custodia permanece en el repartidor; no hay recepción ni nueva asignación automática. Forzar un error de conexión WebSocket y reconectar con teclado. Guardar capturas de escritorio/320 px y resultado axe.
2. **Dos consumidores y replay.** Crear un topic aleatorio y grupos independientes para tablero e historial, con destinos PostgreSQL/MongoDB aislados. Publicar posiciones, envío parcial, bultos, ruta, parada, estimación y flota, incluyendo duplicado, versión atrasada y GPS futuro. Reconstruir otra proyección desde el principio con grupos nuevos. Comparar el estado completo y los documentos por identidad; la posición vigente no retrocede. El broker y sus topics pertenecen solo a esta prueba.
3. **Aislamiento documental.** Consultar dos operadores y dos comercios por API con rol restringido. Comprobar resultados y agregados propios, límites, TTL y deduplicación. Detener únicamente el MongoDB de la prueba y comprobar 503, sin presentar el resultado anterior como actual.
4. **Dos API y reconexión SignalR.** Abrir dos Kestrel reales con la misma base de lectura. Comprobar fotografías equivalentes, actualización sin afinidad de sesión, reconexión, ausencia de filas de otro operador y rechazo anónimo.
5. **Mailpit y recuperación.** Usar RabbitMQ y Mailpit reales. El primer intento apunta a un puerto loopback cerrado; comprobar que no se marca enviado. Restituir SMTP al Mailpit de la prueba, esperar el reintento de la cola y consultar su API HTTP: un correo con marca del operador y enlace público opaco. Repetir el mensaje y comprobar que el total sigue siendo uno. Nunca usar un SMTP externo.
6. **Paginación pública.** Con 250 bultos y API real restringida, Chromium recorre páginas de 200/50 sin cuenta, vuelve con teclado y conserva el foco. Se guardan capturas a 1280/320 px. El flujo de retiro CU-37 verifica además 1/500/501/1500 bultos y los estados públicos antes del retiro, con el repartidor, en depósito y entregados al comercio.
7. **Upgrade poblado.** Migrar una base con hechos previos: se agrega el log derivado, sin cambiar hechos/estado canónico, enviar avisos históricos ni dejar políticas temporales de bootstrap.
8. **Particiones vacías y reinicio.** Crear un topic y grupo aislados con dos particiones vacías y comprobar sus latidos con atraso cero. Publicar el primer evento, esperar su procesamiento/confirmación y detener el consumidor. Reiniciar el mismo grupo: debe volver a publicar salud sin reprocesar ese evento confirmado. No reiniciar offsets ni usar un grupo de otro entorno.

## Configuración de una demo local seleccionada explícitamente

`backend/compose.operacion.yaml` es un overlay de servicios de aplicación para combinar con el Compose existente. Agrega solo el topic operativo nuevo, configuración MongoDB de lectura y URL pública del worker. No se arrancó una pila persistente del usuario como parte de la validación. Para revisar la composición sin arrancar servicios:

```bash
docker compose --env-file /dev/null \
  -f backend/tests/fixtures/compose-operational-base.yaml \
  -f backend/compose.operacion.yaml --profile kafka config --no-interpolate --quiet
```

## Cobertura y comprobaciones completas

Recoger Cobertura del mismo código compilado en unitarias e integración. Habilitar los cinco E2E históricos mediante las variables declaradas en `.github/workflows/ci.yml` del Backend. El pipeline ejecuta tres shards exhaustivos y publica reportes de líneas, TRX y capturas. La unión no cuenta dos veces una línea cubierta por varias suites y cada capa debe superar 70% por separado:

```bash
python3 backend/scripts/coverage/report.py 'backend/artifacts/**/coverage.cobertura.xml' \
  --minimum-reports 4 --output backend/artifacts/coverage-summary
```

Las mediciones iniciales están en `backend/docs/seguimiento-tablero/evidencias/cobertura-inicial/`. Un resultado inicial con pruebas fallidas/omitidas no constituye una validación verde. Mobile no fue modificado; el CI integrado verifica sus pruebas portable, compilación Android y lockfiles por separado. No se atribuye cobertura adicional ni revisión visual nativa Android.
