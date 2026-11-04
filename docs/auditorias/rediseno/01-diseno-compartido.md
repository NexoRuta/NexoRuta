# Unificación de los cuatro portales

Se conserva Razor Pages/Blazor y Bootstrap. No se añade un framework de interfaz. Las rutas, catálogos de permisos, políticas del servidor y formularios con antiforgery siguen en sus hosts originales.

## Fuentes y adaptación

Se consultaron las guías oficiales de Apple el 2/11/2026, mediante sus versiones Markdown, junto con `frontend/DESIGN.md`:

- [Layout](https://developer.apple.com/design/human-interface-guidelines/layout): importancia relativa, agrupación, alineación y adaptación a tamaños de pantalla; los detalles secundarios se muestran bajo demanda. Se adapta a grillas CSS y controles nativos del navegador.
- [Typography](https://developer.apple.com/design/human-interface-guidelines/typography): tipografía del sistema, jerarquía legible y escalado del contenido. Se emplean unidades relativas y tamaños adaptables; no se descarga una tipografía externa.
- [Accessibility](https://developer.apple.com/design/human-interface-guidelines/accessibility): señales perceptibles, operación por teclado y contraste. Se comprueban controles, foco, enlace de salto y reflujo; axe complementa la inspección real, sin certificar accesibilidad global.

No se imita una interfaz nativa ni se aplican efectos visuales que perjudiquen legibilidad en la web.

## Componentes compartidos primero

`frontend/shared/portal-design.css` continúa como fuente única de tokens y patrones. Se elimina la copia editable accidental de Admin: los cuatro hosts reciben el asset generado mediante `Directory.Build.targets`. El JavaScript compartido `shared/portal-interactions.js` se genera de la misma manera. No se editan archivos vendorizados de Bootstrap.

- Superficies neutras, texto principal/secundario, acción, foco y estados semánticos compartidos.
- Tipografía del sistema, encabezados y escalas consistentes.
- Shell, navegación lateral, acciones de cabecera y pie comunes; Admin conserva su propio catálogo de destinos y autorización.
- Controles táctiles principales de 44px, foco visible y enlace de salto al contenido. Menú móvil con Escape y foco devuelto; los destinos cerrados no quedan enfocables.
- Tablas con encabezados y regiones desplazables identificadas cuando requieren dos dimensiones.
- Errores, éxito y procesamiento perceptibles sin depender solo del color. Los datos conservados permanecen visibles ante fallos.

## Pantallas

- Commerce: alta con selector previo y cotización CU09, dos columnas en escritorio, bultos compactos y una columna en móvil. Listado muestra cargos guardados y abre su desglose/historial bajo demanda. El flujo de destino conserva selección, ajuste, guardado, reapertura y conflictos.
- Backoffice: shell, listados, acciones y formularios de configuración/reparto consumen el patrón compartido. La configuración y las acciones operativas conservan sus propios permisos, contratos y efectos.
- Admin: mismo shell y navegación, rótulos en español, identificadores secundarios bajo un disclosure y datos sintéticos de demostración separados de la tarea principal. Se preservan los nombres de campos y tokens antiforgery.
- Tracking: tipografía, superficies, feedback y foco compartidos en el recorrido público, sin añadir una búsqueda de códigos ni acceso a datos privados.

Las capturas `docs/evidencias/rediseno/antes-*` se tomaron en Chromium antes de editar la capa compartida. La verificación posterior y sus límites se registran por separado, con capturas reales y resultados observados.
