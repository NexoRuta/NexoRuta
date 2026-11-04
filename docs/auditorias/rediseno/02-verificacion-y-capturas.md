# Rediseño integrado: verificación observada

Fecha: 2026-11-02. Chromium real con Playwright; PostgreSQL18/PostGIS3.6 real, cuentas sintéticas y rol API restringido. No se publicó configuración del entorno ni se desplegó la aplicación.

## Matriz

`scripts/cloud/verify-portals.cjs` conserva el informe completo en [verificacion-portales.json](../../evidencias/rediseno/verificacion-portales.json). Resultado final: **28 comprobaciones, 0 fallos, 0 destinos externos contactados**.

| Portal | Superficies comprobadas | Tamaños |
|---|---|---|
| Commerce | Crear envío, Mis envíos, Importar CSV, Mi comercio | 1440 y 320 px |
| Backoffice | Envíos recibidos, Tarifas, Reglas operativas, Planificación de rutas, Vehículos, Zonas | 1440 y 320 px |
| Admin | Operadores, Crear organización | 1440 y 320 px |
| Tracking | Inicio público y página no encontrada | 1440 y 320 px |

En cada superficie: axe con reglas WCAG 2 A/AA, 2.1 AA y 2.2 AA, sin infracciones detectadas; documento sin desbordamiento horizontal; enlace de salto accesible con teclado, visible al enfocarse y con foco en contenido **sin cambiar ruta**; menú móvil por Enter/Escape y retorno de foco donde corresponde; texto al 200% a 320px sin desbordar el documento. Las tablas conservan desplazamiento interno cuando su estructura lo requiere.

La inspección visual de capturas detectó y corrigió la navegación de Blazor desde el enlace de salto, además de los contrastes heredados de variables RGB de Bootstrap. Se corrigió Escape durante la transición del menú móvil. La matriz final exige ruta estable para evitar aceptar una captura de Inicio en lugar de la pantalla solicitada.

## Capturas reales comparables

| Superficie | Antes 1440 | Después 1440 | Antes 320 | Después 320 |
|---|---|---|---|---|
| Alta Commerce | [antes](../../evidencias/rediseno/antes-commerce-1440.png) | [después](../../evidencias/rediseno/despues-commerce-1440.png) | [antes](../../evidencias/rediseno/antes-commerce-320.png) | [después](../../evidencias/rediseno/despues-commerce-320.png) |
| Backoffice | [antes](../../evidencias/rediseno/antes-backoffice-1440.png) | [después](../../evidencias/rediseno/despues-backoffice-1440.png) | [antes](../../evidencias/rediseno/antes-backoffice-320.png) | [después](../../evidencias/rediseno/despues-backoffice-320.png) |
| Tarifas | [antes](../../evidencias/rediseno/antes-configuracion-1440.png) | [después](../../evidencias/rediseno/despues-configuracion-1440.png) | [antes](../../evidencias/rediseno/antes-configuracion-320.png) | [después](../../evidencias/rediseno/despues-configuracion-320.png) |
| Admin | [antes](../../evidencias/rediseno/antes-admin-1440.png) | [después](../../evidencias/rediseno/despues-admin-1440.png) | [antes](../../evidencias/rediseno/antes-admin-320.png) | [después](../../evidencias/rediseno/despues-admin-320.png) |
| Tracking | [antes](../../evidencias/rediseno/antes-tracking-1440.png) | [después](../../evidencias/rediseno/despues-tracking-1440.png) | [antes](../../evidencias/rediseno/antes-tracking-320.png) | [después](../../evidencias/rediseno/despues-tracking-320.png) |

Capturas complementarias de las 14 superficies están en el mismo directorio. También se conservan [foco del salto](../../evidencias/rediseno/foco-salto-320.png), texto ampliado en cuatro portales y el recorrido de alta real con proveedor controlado: [cotización escritorio](../../evidencias/rediseno/cu09-alta-cotizada-1440.png), [cotización móvil](../../evidencias/rediseno/cu09-alta-cotizada-320.png), [destino reabierto](../../evidencias/rediseno/cu09-alta-reabierta-320.png) y [conflicto concurrente](../../evidencias/rediseno/cu09-conflicto-320.png).

## Compilación, interacción y límites

Los cuatro portales compilaron y arrancaron. El recorrido integrado de Commerce pasó con búsqueda simulada, selección por teclado, ajuste, error de validación que conserva dirección y bultos, cotización, confirmación y reapertura. El recorrido previo de edición conserva conflicto concurrente y datos revisables; se ejecutaron también las pruebas de doble envío del formulario. Las peticiones a proveedores externos están bloqueadas y las pruebas de Mapbox mantienen `permanent=false`.

La inspección visual y automatización cubren estas superficies y estados sintéticos. No constituyen certificación WCAG, prueba con lector de pantalla, ni aceptación de cada operación de negocio ajena a CU09. Los estados vacíos de configuración reflejan las publicaciones existentes; no se crearon tarifas/coberturas para las capturas. Los pendientes históricos de revisión nativa, habilitación operativa y Stage siguen fuera de este alcance.
