# Pendientes de comprobación para la entrega

Usar [MATRIZ-FINAL.csv](MATRIZ-FINAL.csv) para la próxima acción de cada requisito. Esta guía agrupa recorridos para no repetir trabajo. **Son pendientes, no pruebas ya ejecutadas.**

## Antes de tocar datos

- Entorno habitual: Backoffice5101, Commerce5102, Tracking5103, Admin5104; API5000 y HTTPS5843; Mailpit8025. Mantener el override privado registrado en `compose-command.json`.
- Solo datos nuevos `AUD-20261105`. Cuentas privadas en `.local/auditoria-excel-20261105/audit-private.json`, `accounts.operator/commerce/courier`; no copiarlas a capturas o informes.
- No reutilizar el jueves05 `01A1AA`, Nico lunes09 ni `CU06-LOCAL-V`. No borrar volúmenes, almacenamiento móvil, certificados ni cambiar fechas.
- No activar proveedores reales ni enviar correos/push a terceros. Mantener respuestas controladas, `permanent=false`, Mailpit y NoSend para la auditoría local.
- El control visual fue denegado a Brave y al emulador, y el host de navegador está indisponible. Se requiere habilitarlo o ejecutar estos pasos manualmente. No presentar otra llamada HTTP como prueba de interfaz.

## Recorridos agrupados

| Recorrido | Pasos pendientes | Resultado que debe conservarse como evidencia |
|---|---|---|
| Configuración y acceso — CU01–06, NFR03/05/06 | Entrar con roles diferenciados; comprobar altas/edición/estado permitidos y denegados; publicar reglas/tarifas nuevas en tenant sintético y reabrir un envío anterior | Pantalla y persistencia; el envío anterior conserva su snapshot. Documentar la decisión CU01, sin conceder permisos no autorizados |
| Alta e ingreso — CU07–12, AP02/03 | Crear envío multibulto por formulario; importar archivo válido/inválido y reintentar; comprobar API; imprimir etiqueta y recibir cada bulto | Mismo ID/cargo/bultos en Commerce/Backoffice; errores sin duplicar/persistir parcialmente; impresión legible. Alta individual no acredita importación |
| Planificación — CU13–17 | Usar tres paradas normales, documentar criterio de orden; editar/reabrir; probar dos despachadores contra el mismo envío; despachar | Orden y restricciones persistidas, una sola asignación y descarga de la misma hoja. No se exige optimización |
| Android — CU18–24, AP08, NFR11 | Aplicar el protocolo específico siguiente: descarga/carga, cámara/escáner/firma, offline, cierre de proceso y reapertura antes de reconectar | XML/capturas y efecto persistido; ACK sin duplicados, evidencia recuperada y custodia/rendición coherentes. Escribir códigos o enviar PNG no acredita sensores |
| Público y comunicaciones — CU25–28, AP05/07 | Abrir enlace válido/inválido, parcial1/2, ETA y solicitud de reprogramación; comprobar aviso final y suscripción/webhook en receptor local | Privacidad, estado persistido, firma, reintentos/fallidos/reenvío e historial. Donde falta implementación, registrar ausencia; no simular éxito con bandeja Kafka |
| Operación y cierre — CU29–30, AP01/04/06/09 | Seguir ubicación/riesgo en tablero, registrar/resolver incidencia, devolver al comercio, revisar reportes/liquidación/cuenta corriente y job diario | Cambios visibles y persistidos por actor; conciliación de cargos y cierre automático único. Las piezas ausentes requieren implementación antes de ejecutar |
| Varias instancias — NFR07/08/10/12/13 | En ambiente expresamente autorizado: dos API, aislamiento, invalidación de caché, correlación, fallidos, reconexión y continuidad al retirar una instancia | Capturas/mediciones vinculadas con logs y datos. No interferir con el trabajo de caché de otros compañeros |
| Remoto/opcionales — NFR14/15, OPT03/05/06/07/08/09 | Preparar ambiente/credenciales autorizados; ejecutar las condiciones literales de cada opcional y publicar resultados del pipeline | Replay de flota, analítica paginada, carga remota simultánea, >70% Domain/Application, E2E y push productivo con app cerrada, según fila. No contar infraestructura sola |

## Protocolo Android sin pérdida de datos

La app actualizada está instalada, detenida, con firma/UID/datos originales conservados. Antes de abrirla se comprobó offline que la identidad activa no tenía pendientes. **No se comprobó que se pueda cambiar a la cuenta sintética sin descartar cache.**

1. Revisar [ANDROID.md](ANDROID.md). No desinstalar, limpiar almacenamiento, cerrar sesión con descarte ni saltar la protección de identidad.
2. La ruta sintética preparada, aún sin operaciones, es `01a1ad02-7fe9-71e6-8007-c637e5b86d2a`, jornada `01a1ad02-7fe9-7c75-b343-4e1f703188a4`: entrega2 bultos, parcial3 y retiro1. Está asignada a la cuenta sintética `accounts.courier`.
3. Si la transición normal de cuenta no preserva todo lo anterior, **detener esa transición**. Preparar una alternativa expresamente segura —por ejemplo otra ruta nueva para la identidad existente— sin reutilizar su operación cerrada. No resolverlo borrando datos.
4. Mantener AVD `f7a-qa-api36`, serial `emulator-5554`, x86_64, trasera `webcam0`, frontal deshabilitada, CA existente y `adb reverse tcp:5843 tcp:5843`.
5. En una jornada sintética: descargar, escanear carga, confirmar salida, cortar red; capturar entrega/parcial/retiro con cámara y firma. Mostrar un código de prueba a la webcam para demostrar decodificación real. No fotografiar personas/documentos reales.
6. Cerrar el proceso y reabrir **sin red**. Comprobar bultos, motivos y evidencias conservados. Reconectar y comprobar ACK, reintento sin duplicado y los mismos resultados en API/base/portales.
7. Rendir el pendiente/retiro, cerrar y comprobar recepción física y liberación separadas. El retiro debe terminar entregado al comercio; no detener la prueba en «Retirado».

La ruta HTTP ya finalizada `01a1ad04-7dd7-718e-a8b8-974471c6afa9` es evidencia cerrada, no un fixture para repetir operaciones. La revisita `01a1ad0a-cdf7-738f-afca-8b62c660630b` quedó planificada con solo el pendiente: puede servir para una continuación deliberada, no despacharla automáticamente.

## Registro mínimo por comprobación

Guardar fecha, SHA, cuenta/rol sin contraseña, IDs sintéticos, precondiciones, pasos, esperado/observado, estado persistido y canal de evidencia. Para un fallo, conservar respuesta/correlación y demostrar que el rechazo no alteró datos. Para un bloqueo, identificar herramienta/infraestructura faltante; no reclasificarlo como funcionalidad ausente.

Revisar en navegador escritorio y320px, teclado/foco, zoom200%, etiquetas/errores y contraste conforme `frontend/DESIGN.md`. No hubo certificación WCAG en esta auditoría.
