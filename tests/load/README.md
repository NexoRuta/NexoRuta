# Pruebas remotas de carga

El workflow `.github/workflows/load-tests.yml` corre k6 como Cloud Run Job en `southamerica-west1`. Primero reserva la sesión en GCS y exige que su vencimiento supere la duración del perfil y el margen de conciliación. La cancelación usa el `run_id` y la execution exactos. El guard intenta cancelar leases vencidas; stop cancela antes de detener las VMs.

## Fixtures sintéticas

Tras aplicar bootstrap y demo, crear en Secret Manager una versión de `nexoruta-load-fixtures` con JSON privado. No imprimir el archivo ni cargar usuarios o envíos existentes. Las cuentas y jornadas deben ser sintéticas, distintas entre sí y con permiso móvil `reparto.ejecutar`; se preparan por flujos administrativos existentes antes de habilitar la primera corrida.

El payload de Secret Manager queda acotado a credenciales e identificadores. Los eventos grandes viven en el bucket privado `GCP_LOAD_FIXTURES_BUCKET`, con nombre propio de versión y SHA-256. Secret Manager limita cada versión a 64 KiB; el Job rechaza secretos mayores, limita el objeto de eventos a 4 MiB y verifica el hash antes de cargar k6.

Ejemplo de contenido del secreto (guardar fuera del repositorio):

```json
{
  "readPath": "/api/mobile/perfil",
  "operationsObject": "fixtures/fixture-2026-11-03-v1/operations.json",
  "operationsSha256": "<sha256 del archivo de operaciones>",
  "accounts": [
    {
      "email": "load-01@nexoruta.test",
      "password": "<credencial sintética>",
      "jornadaId": "00000000-0000-4000-8000-000000000001"
    }
  ]
}
```

El objeto de operaciones es JSON con una propiedad por `jornadaId`; su valor contiene los 50 eventos en orden:

```json
{
  "00000000-0000-4000-8000-000000000001": [
    {
      "id": "10000000-0000-4000-8000-000000000001",
      "secuencia": 1,
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

Subir el objeto con una ruta nueva para cada versión, sin sobrescribir fixtures que sigan referenciadas; calcular su SHA-256 localmente y colocarlo en el secreto. El objeto de ejemplo abrevia los eventos; los perfiles de sincronización necesitan 50 por jornada.

Para ejecutar `smoke` alcanza una cuenta. `baseline` usa cinco cuentas y es de solo lectura. `sync` necesita veinte cuentas; `stress` cincuenta; `soak` cinco. Cada jornada usada por `smoke`, `sync`, `stress` o `soak` debe tener 50 eventos `Posicion` ya registrados en orden y con resultado `Aplicada`. Cada ID es único en su jornada. La prueba vuelve a enviar el mismo ID y payload en orden, por lo que mide reconexión e idempotencia sin crear nuevas filas ni alterar el estado. No cambiar secuencia, ID, timestamp ni payload entre corridas. El fixture mostrado abrevia la lista; para perfiles de sync se completa hasta la secuencia 50. Para medir nuevas escrituras o generar datos se necesita una jornada exclusiva y un flujo de conciliación/limpieza separado.

La política de login permite cinco intentos por minuto y el workflow limita el arranque secuencial a esa tasa. Los perfiles se ejecutan solo contra `api` de la release activa; no activan ni usan Mapbox/Geoapify, SMTP externo o FCM.

Guardar ambos archivos fuera del repositorio con permisos de usuario. Subir primero el objeto de operaciones de forma create-only y luego agregar una nueva versión del secreto, sin mostrar el contenido:

```powershell
gcloud storage cp RUTA_PRIVADA\operations.json gs://PROJECT_ID-nexoruta-load-fixtures/fixtures/fixture-2026-11-03-v1/operations.json --if-generation-match=0
gcloud secrets versions add nexoruta-load-fixtures --project=PROJECT_ID --data-file=RUTA_PRIVADA\fixtures.json
```

No habilitar el workflow hasta que las cuentas y jornadas existan en el entorno remoto y la secret version haya sido creada. Las fixtures no se generan ni se siembran automáticamente por esta feature; conservar su inventario privado y retirar cuentas de prueba por sus flujos administrativos cuando ya no se usen.

## Métricas e informes

k6 envía `run_id` y `profile` a un gateway privado de escritura limitada en A por Direct VPC. El gateway solo reenvía remote write y readiness; no permite consultas a Prometheus. El dashboard `nexoruta-load-tests` muestra solicitudes, p95/p99, errores, latencia server por nodo y CPU de las VMs. Cloud Storage conserva resumen privado por 30 días; Cloud Run y Cloud Logging retienen metadatos y logs del wrapper según las políticas de GCP. La salida cruda de k6 se retiene dentro del contenedor y no se publica.

La prueba todavía requiere aceptación visual en Grafana con una corrida real. Si no hay muestras, el dashboard no debe interpretarlas como cero; el usuario puede distinguir ausencia de ingesta del resultado del Job mediante el resumen y los logs. El smoke de la feature reenvía operaciones ya aplicadas; no sustituye el aprovisionamiento y la conciliación inicial de datos ni demuestra flujos externos de notificación.
