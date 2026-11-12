# Verificación UX/UI

Fecha: 8 de noviembre de 2026, Uruguay. Datos y sesiones exclusivamente sintéticos.

## Compilación y runtime

Se ejecutó `bash scripts/cloud/environment-install.sh` con los gitlinks exactos y locks versionados; Docker/PostGIS, SDK 10.0.401, Node 24.22.2 y Chromium del proyecto. `dev.py start` y `dev.py verify` comprobaron login, GET autenticados, PostGIS, rol API sin superuser/bypassrls y 90 tablas con RLS forzado. Se detuvo el runtime antes de recompilar. Las pruebas integrales inician servicios propios con los mismos helpers/fixtures del proyecto.

`dotnet build frontend/NexoRuta.sln --no-restore`: pasó. Se conservaron advertencias existentes NU1510, CS8629 y de pruebas; no se cambiaron dependencias ni componentes para resolverlas. La compilación de API/Worker y capas backend está incluida en las pruebas de integración.

`dotnet test frontend/tests/NexoRuta.ApiClient.Tests --no-restore --filter FullyQualifiedName~CommerceReceiverTests`: 2 pruebas aprobadas (firma y persistencia/deduplicación del receptor).

## Pruebas de comportamiento y navegador

Comando de aceptación, con `env-agent.sh`, `NEXORUTA_PLAYWRIGHT_MODULE`, `NEXORUTA_GESTION_E2E_DIR` y `NEXORUTA_WEBHOOK_E2E_DIR` apuntando a carpetas propias:

```bash
dotnet test backend/tests/NexoRuta.IntegrationTests --no-restore \
  --filter 'FullyQualifiedName~GestionCircuitTests|FullyQualifiedName~GestionBrowserTests|FullyQualifiedName~WebhooksFullStackTests'
```

La corrida de aceptación aprobó **7 pruebas, sin fallos ni omisiones**: cinco pruebas de gestión HTTP/persistencia/reglas, un circuito de navegador de gestión y un circuito integral de webhooks. Una corrida adicional de ambos circuitos de navegador aprobó **2 pruebas** e incorporó zoom nativo. Los JSON sintéticos de resultados se adjuntan con las capturas de esta carpeta. Las capturas anteriores provinieron de ejecuciones exitosas sobre los binarios originales. Se inspeccionaron visualmente, no solamente se generaron.

La evidencia de gestión separa HTTP/RLS/cálculos de automatización del navegador. Chromium usa sesiones distintas, API y PostgreSQL reales; el comercio consulta el mismo documento confirmado por Backoffice. Comprueba nombres, filtros, limpieza, URL/recarga, regreso desde detalle, comercio/período al abrir cuenta, preparación/revisión/confirmación, opciones sin coincidencias y error recuperable. La navegación relacionada incluye envíos, rutas, depósito, flota y solicitudes de nueva visita.

Webhooks usa dos workers reales y receptor Tracking propio. Conserva verificaciones de firma inválida, caída 503, espera/reintento, agotamiento y reenvío, deduplicación, respuesta perdida, conexión rechazada, timeout y reinicios. Verifica estados vacío/carga/error recuperable y usuario con permiso limitado; el detalle de intentos se recupera por URL.

## Visual y accesibilidad

Gestión: escritorio 1440 y anchos 768, 375 y 320 CSS px. Cada vista comprueba ausencia de desbordamiento general, foco/teclado/enlace de salto y axe para las etiquetas WCAG seleccionadas. Tablas anchas conservan desplazamiento local y todo su contenido. Aumento de texto al 200 % en las vistas de gestión; receptor también al 200 %. Además se verificó zoom nativo al 200 % mediante la API de Chromium `tabs.setZoom`: `tabs.getZoom=2`, viewport CSS de 720 px y `devicePixelRatio=2` sobre una ventana de 1440 px. Se comprobó teclado y ausencia de desbordamiento general en reportes, liquidación, cuenta Commerce, webhooks y receptor. Un helper de prueba aislado genera una extensión local de Chromium con permiso `tabs`; no es una dependencia del producto. Las capturas nativas usan CDP para conservar la región correcta con zoom. No es una certificación WCAG. Webhooks incluye capturas a 1440, 768, 375 y 320 px y movimiento de foco por teclado.

Las capturas antes/después comparan tareas y viewport, con identidades sintéticas nuevas en cada ejecución. Los códigos largos usados por la fixture incluyen GUID deliberadamente; la aplicación muestra el código comercial existente sin inventar un correlativo.

## Límites y pendientes

La precisión temporal de la atribución es un defecto de reconstrucción, documentado en [revision.md](revision.md). No se cambia la función de proyección ni se afirma reparar el registro Windows. La prueba crea los hechos sintéticos originales con fracciones submicrosegundo, sin actualizar un diario inmutable.

No se modifican MAUI, servicios facturables, bases compartidas ni documentos confirmados. No se acredita una certificación integral de contraste/accesibilidad de pantallas no modificadas. El smoke interactivo previo devolvió 409 al admitir su envío; el circuito aislado de webhooks valida los transportes reales con su configuración sintética controlada.

El CI remoto aprobó 380 pruebas unitarias backend y el build frontend. Detectó que el endpoint nuevo no declaraba su DTO de respuesta API; se corrigió la frontera HTTP con DTOs propios y el mismo JSON, sin relajar la prueba de arquitectura. Los resultados de la repetición enfocada se registran junto con las evidencias finales.

Resultados posteriores a esas correcciones: arquitectura 7 aprobadas; regresión HTTP de gestión 5 aprobadas; repetición enfocada de opciones autorizadas/homónimos/paginación 1 aprobada. La corrección visual del encabezado de zona pasó otra ejecución del circuito completo (1 aprobada, 24 vistas y zoom nativo). No se deshabilitó ninguna aserción.
