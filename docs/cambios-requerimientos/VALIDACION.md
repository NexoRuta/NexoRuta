# Verificación ejecutada — 5/11/2026

La evidencia corresponde a Linux Cloud con datos sintéticos propios, .NET SDK 10.0.401, PostgreSQL 18/PostGIS y conexiones runtime sin superusuario ni BYPASSRLS. No se accedió a Windows ni a sus bases/emulador. Se distingue el alcance de cada comprobación; no constituye aceptación integral de todos los CU.

## Compilación y pruebas automatizadas

| Comprobación | Resultado |
|---|---|
| API y Worker .NET | Compilan; advertencia NU1510 existente |
| Solución frontend: Backoffice, Commerce, Tracking, ApiClient | Compila; advertencias de analizadores existentes |
| Unitarias backend focalizadas: creación, agregación/transiciones y capacidad | 24 pasan |
| Frontend: tarifas, reglas, envíos del operador y rutas | 37 pasan |
| Mobile Application portátil, incluyendo ViewModels enlazados | 88 pasan en la ejecución final, incluidos ViewModels y distinción de visita completada |
| Integración nueva parcial permitida/rechazada/devolución y retiro exitoso/fallido | 5 pasan en tanda serial; parcial extendida y devolución operativa: 4 pasan |
| Regresión focalizada de intentos/devolución | Dos tandas de 6 pasan |
| Retiro y rechazo de imágenes corruptas con cifrado preservado | 6 pasan |
| Matrices SQL/dominio exhaustivas de envío y resultado de bulto | 2 pasan, incluyen todas las parejas de ambos enums |
| Firmas/contratos de funciones RLS | 1 pasa |
| Recorrido completo con conexión restringida | 1 pasa |

La tanda extendida de parcial verifica además carga incompleta permitida, asociación de prueba al bulto, reenvío idéntico, conflicto por versión, nueva ruta con solo pendientes, conservación de membresía histórica, segundo intento y conteo por bulto, devolución física y aislamiento de inbox por comercio/operador. La de retiro comprueba idempotencia de solicitud, franja/tarifa, foto y firma, visita fallida sin custodia inventada y entrega final al comercio.

Una regresión amplia inicial dio 82/83: una aserción contaba todo el outbox y asumía un solo evento. Se ajustó para contar el evento v1 cuyo significado debe conservarse; las nuevas notificaciones v2 son adicionales. La prueba específica pasa y conserva la aserción de un único aviso de ruta. Una ejecución amplia posterior dio 39/84 y 45 fallos por `ENOSPC` al acumular bases temporales. **No se declara verde esa suite completa.** Se continuó con tandas pequeñas y los recorridos relevantes, sin borrar volúmenes persistentes ni cambiar fixtures para ocultar el problema.

Comandos principales, con el entorno de [DEMOSTRACION.md](DEMOSTRACION.md) cargado:

```bash
dotnet build backend/src/NexoRuta.Api
dotnet build backend/src/NexoRuta.Worker
dotnet build frontend/NexoRuta.sln
dotnet test backend/tests/NexoRuta.UnitTests --filter 'FullyQualifiedName~CrearEnvio|FullyQualifiedName~Capacidad|FullyQualifiedName~CambiosRequerimientos'
dotnet test backend/tests/NexoRuta.IntegrationTests --filter 'FullyQualifiedName~C31_'
dotnet test backend/tests/NexoRuta.IntegrationTests --filter 'FullyQualifiedName~C37_'
dotnet test mobile/tests/NexoRuta.Mobile.Application.Tests -p:NuGetLockFilePath=obj/cloud.packages.lock.json
```

Usar `DOTNET_PROCESSOR_COUNT=1` para contener las bases concurrentes. Ejecutar filtros de integración en procesos separados en máquinas con poco disco.

## Demostración integrada y sin conexión

Ejecutada la secuencia setup → cliente portátil offline → terminación del proceso → cliente nuevo sync → finish → revisit. SQLite y tres archivos cifrados sobreviven al proceso; durante el tramo offline toda petición del cliente falla. La sincronización posterior entrega a API real, con confirmaciones persistidas. No es un mock del servidor ni una cola solo en memoria.

Se comprobaron parcial 2/3, retiro con foto/firma, rendición/cierre, recepción, entrega al comercio, retorno físico y liberación separados. `revisit` confirmó exclusivamente el pendiente y el recargo único de 25 UYU sobre snapshot histórico. Kafka local procesó contratos v2 hasta la bandeja Commerce; RabbitMQ generó enlaces públicos reales; se comprobó el conteo público y la ausencia de IDs internos. No se envió correo externo ni se consumieron servicios pagos.

`dev.py verify` comprueba la base migrada (78 migraciones), autenticación y rol API restringido. Las nuevas funciones y bandeja conservan RLS; tests usan actores ajenos para validar rechazo/filtrado.

## Navegador y límites nativos

Verificación con Chromium/Playwright, automatización, capturas y revisión visual en escritorio y 320 CSS px. La guía incluye el script reproducible y los artefactos locales. Se completó una solicitud real de retiro desde Commerce, con cotización y error recuperable por motivo vacío; se guardaron y reabrieron las tres reglas nuevas. Se revisaron envíos, ruta, reporte, reglas, retiro, avisos y seguimiento: sin desborde general a 320 px ni con texto al 200 %, foco alcanzable por teclado y cero hallazgos axe en esas siete pantallas tras corregir la lista de datos de carga y el título interactivo de Tracking. Las capturas de retiro a 320 px, ruta de escritorio y seguimiento a 320 px se inspeccionaron visualmente. Esto no certifica WCAG del producto completo.

La compilación Android fue intentada y se detuvo con NETSDK1147: falta el workload `maui-android`. Tampoco hay adb/emulador. No se declara build APK, cámara/escáner/firma nativos ni recorrido Android ejecutado. Los ViewModels se compilan en las pruebas portátiles; XAML y los componentes nativos requieren validación en una máquina Android habilitada.

## Publicación

Los commits se publican primero en los tres submódulos y después en el principal, todos en `feature/cambiosrequerimientos`, sin merge ni force push. Las bases efectivas están en el ADR. El manifiesto de esta entrega registra SHAs de componentes; el `checkpoint.json` anterior conserva su carácter histórico y no selecciona fuentes. Se clonó de GitHub la rama publicada en un directorio nuevo de `/tmp`, con `--depth 1 --recurse-submodules --shallow-submodules`. Git descargó los tres SHAs publicados y `verify-gitlinks.py` comprobó los tres sin cambiar fuentes. Desde ese clon se compilaron API, Worker, solución frontend completa y la herramienta portátil Mobile: cero errores. El ejemplo portátil Linux presenta dos advertencias CA1416 por permisos Unix; no afecta al cliente Android. El principal y cada submódulo permanecieron limpios tras las compilaciones. La corrección documental posterior conserva esos mismos gitlinks.
