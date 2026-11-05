# Trazabilidad de requisitos 31–41

| Req. | Implementación | Evidencia reproducible |
|---|---|---|
| 31 | Resultado de bulto, agregación y matrices dominio/PostgreSQL | `CambiosRequerimientosTests`, `ShipmentStatePolicySqlTests`, `C31_EntregaParcial...` |
| 32 | Escaneo y motivo por bulto, prueba por bulto; diario y versiones independientes | `C31_EntregaParcial...`, `BultosConEvidenciaPersistenTrasReinicio...`, demostración portátil con API real |
| 33 | Publicación de política parcial y monto de recargo; snapshot al admitir | Editor de reglas, pruebas permitida/rechazada/devolución, ajuste único al despachar |
| 34 | Snapshot de bultos de visita; solo pendientes en planificación/reasignación | `C31_EntregaParcial...` comprueba nueva ruta con un solo pendiente y conserva visita original |
| 35 | Conteos públicos autorizados por capability | `demo-cambios.py finish`: 2/3 y ausencia de IDs internos; portal Tracking |
| 36 | Outbox v2, topic dedicado, consumidor Kafka e inbox RLS; v1 preservado | Broker Kafka real en demo; `C31_EntregaParcial...` verifica ingreso idempotente |
| 37 | Commerce `/retiros/crear`, API `POST /api/retiros` y `/api/envios` con datos de retiro | `C37_RetiroPorApi...`, prueba del formulario en Chromium |
| 38 | Ciclo declarativo propio y resultado fallido replanificable | `C37_RetiroPorApi...`, matriz SQL/dominio exhaustiva |
| 39 | Ruta mixta ordenada; máximo por tramo en peso/volumen; capacidad física al retirar | `OrdenMixtoPermiteDescargarAntes...`, `C37_RetiroPorApi...`, demo mixta |
| 40 | Identificación, foto y firma obligatorias; almacenamiento y subida existentes | `C37_RetiroPorApi...`, prueba SQLite/reinicio y cliente portátil contra API real |
| 41 | Modalidad tarifaria Retiro; mismo enlace; avisos, tablero y reportes | `C37_RetiroPorApi...`, `demo-cambios.py finish`, Commerce Avisos y Backoffice Reporte |

Los tests de integración están en `backend/tests/NexoRuta.IntegrationTests/Reparto/OperacionesRepartoHttpTests.Cambios.cs` y `.Retiros.cs`. Las pruebas portátiles están en `mobile/tests/NexoRuta.Mobile.Application.Tests/SincronizadorJornadaTests.cs`. La herramienta de demostración completa usa los mismos ensamblados Mobile, en `tests/Cambios.DemoMobile` del principal.

Los límites de ejecución, incluido Android, se registran por separado en [VALIDACION.md](VALIDACION.md).

## Estado en la continuidad H1–H6

| Req. | Implementación revisada/corregida | Validación de esta ejecución | Manual pendiente |
|---|---|---|---|
|31|Resultados y agregado; primera fecha y plazos independientes|Matrices SQL/dominio; H1H2 con PostgreSQL real|Revisión operativa de políticas elegidas|
|32|Captura y evidencia por bulto; proyección local y pertenencia a visita|H3/H4, reinicio/cifrado, demo portable mediante ViewModels/API|Cámara, firma y escáner Android|
|33|Reglas publicadas; nueva visita con/sin cargo o devolución|C31, edición/reapertura web; demo recargo único|Aceptación de configuración del operador|
|34|Snapshot histórico y nueva visita solo con pendientes|H1H2; segunda entrega real portable; recálculo vial|Recorrido Android de revisita|
|35|Conteos públicos sin identidades internas|Demo 2/3 y después 3/3, Chromium y privacidad HTTP|Aceptación visual en dispositivos objetivo|
|36|V1 preservado, V2 por bulto; outbox/inbox|Kafka real e inbox Commerce; reintentos de comandos|Entrega externa a sistemas de comercios|
|37|Solicitud de retiro portal/API|Solicitud real Chromium y C37 restringida|Aceptación operativa del formulario|
|38|Ciclo propio y reprogramación de fallido|C37 fallido/replanificación y exitoso hasta comercio|Recorrido nativo completo|
|39|Capacidad por tramo, custodia física y rutas mixtas|Unitarias peso/volumen; C37 rechaza exceso físico; H5 vial controlado|Carga física de campo|
|40|Foto/firma, diario offline y conflicto explícito|H4 conserva acuse y resolución; pérdida de respuesta; demo API|Capturas y almacenamiento en Android real|
|41|Tarifa, enlace, avisos, tablero y reportes|Demo Kafka/RabbitMQ, siete pantallas web, C37|Avisos externos y aceptación operativa|

La feature queda disponible para revisión técnica dentro de 31–41; estas evidencias no cierran los demás CU ni sustituyen la validación nativa.

## Integración en develop

Los requerimientos 31–41 se incorporan a develop conservando los avances existentes. La evidencia automatizada nueva, los conflictos resueltos y el alcance de validación se registran en [INTEGRACION-DEVELOP.md](INTEGRACION-DEVELOP.md). El recorrido Android continúa pendiente y, por autorización expresa, no bloquea esta integración. El borde de sobres/acuses de 1500/2000 bultos permanece como observación secundaria, sin cambios adicionales.
