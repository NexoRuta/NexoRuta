# Evidencias del circuito HTTP

Ensayo sintético de Codex Cloud del 07/11/2026 (America/Montevideo; ejecuciones del 08/11 UTC). No es un despliegue ni una certificación de producción.

## Compilación

Backend y portales .NET 10.0.401 compilados. Compose base + override + `compose.webhooks-demo.yaml` validado con `config --no-interpolate --quiet`. Python Cloud validado con `py_compile`. La CI del PR principal compila y prueba los gitlinks de [source-shas.json](../source-shas.json), sin cambiar otras puntas para resolver errores.

Regresión local: backend unitarias 380/380, arquitectura 7/7; frontend 515 aprobadas, cinco pruebas optativas de otros navegadores omitidas en esa invocación. El E2E específico de webhooks sí se ejecutó con Chromium. Los TRX completos y el conjunto integrado obligatorio se conservan como artefactos de CI; no se copian logs privados del runtime.

## HTTP y persistencia

Pruebas nuevas `WebhooksHttpTests`: fanout atómico/rollback, suscripción por comercio-operador-evento, contratos, configuración con pendientes, concurrencia optimista, leases entre dos workers, fencing de reservas vencidas, agotamiento, reenvío auditado, revocación irreversible para revisiones históricas y aislamiento de dos comercios/dos operadores. Pruebas unitarias de firma/política de destinos y del receptor SQLite validan alteración, replay, rotación, reinicio y efecto único.

El smoke [cloud-smoke.json](cloud-smoke.json) corresponde al runtime persistente accesible en `http://localhost:5103/comercio`. La llamada real la realizó el worker hacia `http://127.0.0.1:5103/comercio/webhook`; HTTP 200. Las credenciales y secretos permanecen en `.local`, fuera de esta evidencia.

## Automatización con navegador

[evidence.json](evidence.json) enumera las comprobaciones del ensayo Commerce → API Kestrel → dos workers → Tracking. Incluye caída simulada 503, backoff, agotamiento y reenvío por interfaz, respuesta cortada después del commit remoto, conexión realmente rechazada al detener el receptor, TCP que acepta sin responder hasta timeout, recuperación, reinicios y payload alterado rechazado. La repetición conserva el evento y no agrega otro efecto.

Las fixtures operativas existentes ejecutan entrega parcial, nueva visita y retiro solicitado/retirado/entregado al comercio con custodia/evidencias. En su modo de webhooks usan API Kestrel, worker restringido y Tracking reales; guardan los contratos efectivamente transmitidos. Una selección de esos payloads se publica en [examples.json](../../../backend/docs/webhooks/examples.json).

## Revisión visual

Capturas de Chromium revisadas por el agente, separadas de las aserciones HTTP y de compilación:

- [Commerce escritorio](commerce-history-desktop.png) y [320 px](commerce-320.png): navegación, operador, suscripciones, estado/fechas/diagnóstico y reenvío.
- [Receptor escritorio](receiver-events-desktop.png), [320 px](receiver-320.png), [texto 200 %](receiver-zoom200.png): firma válida, estado/progreso, evento frente a intento, duplicado y rechazo.
- Estados [carga](commerce-loading.png), [vacío](commerce-empty.png), [error recuperable](commerce-error.png), [permisos de consulta](commerce-permissions-320.png) y [receptor vacío](receiver-empty-desktop.png).
- [Receptor en localhost:5103](cloud-localhost-5103.png): validación adicional del destino humano solicitado.

Se comprobó reflujo sin scroll horizontal general a 320 px, navegación por teclado y foco en controles reales. La inspección de imágenes detectó y corrigió la versión Razor literal y el progreso capturado antes de completar la admisión. Se reutilizaron Bootstrap y `shared/portal-design.css`, sin otro framework.

Límites: no se declara certificación WCAG ni revisión con lector de pantalla. No se probaron carga sostenida, destinos reales, mapas facturables, Windows o producción. La entrega es al menos una vez con límite y fallidos durables; una respuesta perdida puede duplicar el HTTP, por lo que el receptor deduplica transaccionalmente. El receptor es de ensayo protegido y solo se habilita explícitamente en Development/Testing.
