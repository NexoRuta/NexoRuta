# Pruebas remotas de carga

El workflow `.github/workflows/load-tests.yml` corre k6 como Cloud Run Job en `southamerica-west1`. Primero reserva en GCS hasta 30 minutos para preparar la fixture y exige que la sesión tenga tiempo para preparación, perfil y conciliación. Después fija la versión lista del fixture y la release en una lease de corrida. La cancelación usa el `run_id` y la execution exactos; también puede cancelar una preparación sin iniciar Cloud Run. El guard intenta cancelar leases vencidas; stop cancela antes de detener las VMs.

## Fixtures sintéticas

Después de aplicar bootstrap y demo, el workflow prepara la fixture por sí mismo. Requiere la variable `GCP_LOAD_PREPARER_SERVICE_ACCOUNT`, generada por bootstrap. La identidad preparadora inicia sesión como el administrador de plataforma reservado y llama al endpoint restringido `POST /api/admin/demo-data/load-fixture` en lotes de hasta cinco cuentas. El backend crea hasta 50 cuentas bajo organizaciones sintéticas reservadas, asigna solo `reparto.ejecutar` y prepara para cada una una jornada activa con `InicioJornada` y 50 posiciones aplicadas. El fixture no usa cuentas de demo ni SQL directo. Las cuentas comparten las organizaciones sintéticas OPT-06; esta suite no mide aislamiento entre tenants.

Antes de tocar la base, el preparador persiste las credenciales en Secret Manager con `fixtureStatus: "preparing"`. Una corrida interrumpida las reutiliza para que el retry no cambie contraseñas. Al completar los lotes, fija las operaciones en un objeto inmutable del bucket privado y publica una nueva versión `fixtureStatus: "ready"` con su SHA-256. El controlador verifica que siga vigente la lease, que la versión sea la última habilitada y que la sesión de VM conserve tiempo suficiente antes de habilitar Cloud Run.

El payload de Secret Manager queda acotado a credenciales e identificadores. Los eventos grandes viven en el bucket privado `GCP_LOAD_FIXTURES_BUCKET`, con nombre propio de versión y SHA-256. Secret Manager limita cada versión a 64 KiB; el Job rechaza secretos mayores, limita el objeto de eventos a 4 MiB y verifica el hash antes de cargar k6.

Ejemplo de contenido del secreto (guardar fuera del repositorio):

```json
{
  "fixtureStatus": "ready",
  "readPath": "/api/mobile/perfil",
  "operationsObject": "fixtures/opt06-<hash>/operations.json",
  "operationsSha256": "<sha256 del archivo de operaciones>",
  "accounts": [
    {
      "email": "opt06-load-001@nexoruta.test",
      "password": "<credencial sintética>",
      "jornadaId": "00000000-0000-4000-8000-000000000001"
    }
  ]
}
```

El objeto de operaciones es JSON con una propiedad por `jornadaId`; su valor contiene los 50 eventos en orden. No tiene que incluir una entrada para cada cuenta del secreto: `baseline` es de solo lectura y no necesita jornadas. Para `smoke`, `sync`, `stress` o `soak`, debe haber una secuencia válida para cada jornada asignada a un VU activo del perfil. El preflight comprueba antes del tráfico de aplicación que haya suficientes cuentas y que cada VU activo tenga sus operaciones; las cuentas adicionales sin eventos pueden permanecer en el fixture para perfiles de lectura.

```json
{
  "00000000-0000-4000-8000-000000000001": [
    {
      "id": "10000000-0000-4000-8000-000000000001",
      "secuencia": 2,
      "tipo": "Posicion",
      "envioId": null,
      "versionEnvio": null,
      "ocurridaEn": "2026-11-03T12:00:00Z",
      "datos": {
        "latitud": -34.9,
        "longitud": -56.16,
        "precisionMetros": 12,
        "posicionEnUtc": "2026-11-03T12:00:00Z"
      }
    }
  ]
}
```

El workflow sube el objeto con `ifGenerationMatch=0` y verifica el hash si ya existe una ruta de contenido idéntico. Las versiones anteriores del secreto y los objetos quedan privados para conservar la referencia de corridas previas. El objeto de ejemplo abrevia los eventos; los perfiles de sincronización necesitan 50 por jornada.

Para ejecutar `smoke` alcanza una cuenta. `baseline` usa cinco cuentas y es de solo lectura. `sync` necesita veinte cuentas; `stress` cincuenta; `soak` cinco. Cada jornada usada por `smoke`, `sync`, `stress` o `soak` debe tener primero un `InicioJornada` aplicado en la secuencia 1 y luego 50 eventos `Posicion` ya registrados en orden, con resultado `Aplicada`, en las secuencias 2–51. Esto refleja el contrato del backend: las posiciones solo se aceptan cuando la jornada está en curso. Cada ID es único en su jornada. La prueba vuelve a enviar solo las 50 posiciones con el mismo ID y payload en orden; el replay idempotente no agrega filas ni altera el estado. No cambiar secuencia, ID, timestamp ni payload entre corridas. El fixture mostrado abrevia la lista; el preparador genera las secuencias completas. Mantener las jornadas activas mientras se quieran repetir perfiles con sync; para medir nuevas escrituras o generar datos hace falta una jornada exclusiva y un flujo de conciliación separado.

La política de login permite cinco intentos por minuto. El wrapper autentica secuencialmente y espera 12,1 segundos después de cada respuesta; así la latencia variable no comprime las llegadas al servidor. Renueva las sesiones tres minutos antes de que venza el JWT de 15 minutos, incluidas las identidades aún inactivas. Refresh y logout comparten una pausa de 2,1 segundos después de cada respuesta, por debajo de 30 solicitudes/minuto. Un rechazo o una respuesta perdida de rotación abortan la corrida; no se reintenta con un refresh token cuyo estado es incierto. Los perfiles se ejecutan solo contra `api` de la release activa; no activan ni usan Mapbox/Geoapify, SMTP externo o FCM.

No cargar fixtures manualmente ni imprimir credenciales. El workflow controla la preparación y el `run_id` permite cancelar una preparación atascada desde Actions. Las cuentas sintéticas persistentes quedan reservadas para OPT-06; conservarlas para repetir corridas con credenciales estables.

Las cuentas y sus jornadas son persistentes para permitir repetir corridas con credenciales estables. El endpoint solo admite el rango reservado `opt06-load-001..050@nexoruta.test` y asegura la operación con un lock transaccional.

## Métricas e informes

La preparación autentica las cuentas secuencialmente y luego calienta exclusivamente la lectura de perfil durante 30 segundos. Las peticiones públicas tienen un timeout de 10 segundos y el timeout total de setup contempla las identidades del perfil, la pausa de login y el warm-up. Si la preparación no alcanza dentro de ese presupuesto, se aborta; no se amplía la sesión de la demo. Un fallo de warm-up impide iniciar la carga. Las operaciones de replay se envían únicamente en la ventana medida.

El wrapper conserva passwords y refresh tokens en su proceso. k6 recibe únicamente jornadas sintéticas y obtiene access tokens de un broker en `127.0.0.1`, protegido por una capacidad aleatoria por corrida. Las respuestas usan `no-store`, no siguen redirects y no se registran en logs. Las consultas locales llevan `phase=control`; no forman parte de los SLO. Cada VU mantiene su access token en memoria y solicita uno vigente antes de que venza, también durante un batch largo. Los refresh tokens nunca pasan al proceso k6 ni al reporte.

El manifiesto fija `thresholds_version` y `suite_sha256`. El runner recalcula el hash de las fuentes incluidas en su imagen —también el módulo de sesiones— antes de autenticar o generar tráfico de aplicación. Una imagen que no coincide con la reserva se rechaza. Los checkpoints y el resumen conservan únicamente estado y cantidades de autenticación; la evidencia de rotación local usa HTTP/reloj controlados y aún requiere verificación con k6/Cloud Run reales.

Al terminar se revocan únicamente las sesiones creadas por la corrida, sin borrar historia. La limpieza comparte la cuota de refresh y tiene un presupuesto total de 120 segundos; ante señal de apagado se prioriza exportar evidencia y puede quedar pendiente. `session_cleanup` registra cantidades e IDs de sesiones conocidas pendientes; `authentication.unresolved_account_indexes` identifica posiciones del fixture privado si una respuesta se perdió. No se publican credenciales. Una limpieza incompleta impide aprobar una corrida que de otro modo habría pasado.

Las peticiones llevan `phase=setup`, `phase=warmup` o `phase=measured`; los thresholds HTTP seleccionan solo `phase:measured`. Al comparar latencias en Prometheus, filtrar esa fase para excluir login y calentamiento. Las pruebas controladas de `scripts/gcp/load_scenario_test.mjs` ejecutan el scenario real con dobles de HTTP y reloj; no acreditan rendimiento remoto ni la ejecución del binario k6.

k6 envía `run_id` y `profile` a un gateway privado de escritura limitada en A por Direct VPC. El gateway solo reenvía remote write y readiness; no permite consultas a Prometheus. El dashboard `nexoruta-load-tests` muestra solicitudes, p95/p99, errores, latencia server por nodo y CPU de las VMs. Cloud Storage conserva resumen privado por 30 días; Cloud Run y Cloud Logging retienen metadatos y logs del wrapper según las políticas de GCP. La salida cruda de k6 se retiene dentro del contenedor y no se publica.

La prueba todavía requiere aceptación visual en Grafana con una corrida real. Si no hay muestras, el dashboard no debe interpretarlas como cero; el usuario puede distinguir ausencia de ingesta del resultado del Job mediante el resumen y los logs. El smoke de la feature reenvía operaciones ya aplicadas; no sustituye el aprovisionamiento y la conciliación inicial de datos ni demuestra flujos externos de notificación.

El runner consume además un stream JSON de k6 por un FIFO privado. Solo conserva contadores agregados de la fase medida y una ventana de 60 segundos; no guarda el stream ni respuestas HTTP. Una tasa superior a 5% en un minuto completo aborta el proceso. Las muestras del segundo actual se evalúan al completarlo, evitando depender del orden de llegada de los VUs.

Cada checkpoint conserva CPU normalizada a la cuota y memoria del cgroup v2 del Job. Treinta segundos de saturación (90% CPU o memoria), un nuevo OOM, menos de 64 MiB libres o un log local mayor a 16 MiB detienen la carga. La falta de límites de cgroup verificables invalida la medición; comprobar su disponibilidad en el primer smoke Cloud Run. Estos checkpoints no sustituyen los paneles de recursos del generador en Grafana, que siguen pendientes.

El resultado separa `passed`, `slo_failed`, `capacity_limit_found`, `cancelled`, `invalid_generator`, `invalid_generator_telemetry`, `invalid_telemetry`, `invalid_authentication`, `session_cleanup_incomplete`, `incomplete_evidence` e `infrastructure_failed`. Un límite encontrado durante stress sigue siendo una ejecución fallida y requiere diagnóstico. Un exit code cero sin resumen válido, sin requests medidas o con ventana incompleta no aprueba la corrida. El controlador guarda `controller-summary.json` y exige concordancia entre Cloud Run, autenticación, limpieza y resumen del runner; también registra el fallo cuando el contenedor muere sin resumen.

`evidence.measurement_report` conserva por escalón el tiempo observado, requests, error rate, replay iniciado/completado y p95/p99 por lectura, sync y batch. El reloj parte del inicio real del escenario k6, después del setup. `first_breached_stage` identifica el primer escalón con infracciones; `complete` distingue una ventana completa de un resultado parcial. Los percentiles usan muestras individuales, con un límite total de un millón de latencias (8 MiB de valores); superar ese límite invalida la evidencia. No se promedian percentiles de VUs. `maximum_observed_http_rps` cuenta respuestas HTTP por ventanas completas de 10 segundos; incluye las peticiones de replay y excluye la última ventana parcial.

Los targets de stress se fijan en `profiles.json` y se etiquetan como etapas 1–4 de la rampa de llegada, no como niveles constantes medidos. Se comprueba cada batch iniciado frente a los completados. Los 50 VUs son un techo de asignación; no se exige activar identidades innecesarias para alcanzar la tasa. Las pruebas nominales de VUs conservan la exigencia de completar el batch de cada usuario configurado. La recuperación de colas del servidor después de la carga sigue pendiente de medición remota y no se infiere de estos contadores de replay.
