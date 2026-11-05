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
