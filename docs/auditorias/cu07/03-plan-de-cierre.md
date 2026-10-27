# CU-07 — plan de cierre

**Estado vigente tras los bloques 08–10:** el contrato de trabajo acordado para importación y su integración en Commerce están implementados y verificados con PostgreSQL aislado, rol API restringido, Kestrel y navegador. La revisión manual 10 detectó y corrigió una afirmación de éxito de operación para una fila duplicada que no se había procesado por rechazo atómico y el ApiClient ahora rechaza cuerpos JSON incompletos; componente, cliente y escenario de navegador quedaron probados. Las tareas de implementación T1–T5 quedan completadas para este alcance. La revisión nativa sigue pendiente por falta de la captura `external.select_intended_untracked`, sin aprobación inferida. Esto no equivale a cerrar CU-07 junto con todos sus requisitos transversales: X02, X04, X05 y X06 conservan los límites descritos en `01-requisitos-y-trazabilidad.md`, `09-commerce-importacion-y-verificacion.md` y `10-revision-tecnica-manual.md`.

Los documentos 04, 06 y 08 conservan cortes históricos. Las decisiones CSV/referencia/atomicidad se adoptaron como decisiones de proyecto, no como texto literal del PDF/XLSM. CU-08 es obligatorio y separado; la máquina de estados y la mensajería transversal tampoco quedan cerradas por completar importación.

## Estado de tareas

- **T1 — semánticas de importación:** completada. Decisiones adoptadas en `06-diseno-tecnico-y-plan.md`; no se elevaron a requisitos oficiales.
- **T2 — backend idempotente:** completada. Parser, validación, identidad por Comercio/referencia, transacción atómica, endpoint y outbox en `08-backend-importacion.md`; el corte 09 registra además la corrección del orden de locks efectivos y del contexto RLS de outbox.
- **T3 — ApiClient y Commerce:** completada. Multipart, plantilla, selección de operador histórico acotada, resultados por fila, reintento manual, accesibilidad observada y doble submit en `09-commerce-importacion-y-verificacion.md`.
- **T4 — evidencia integrada:** completada para los recorridos documentados: Testcontainers, API Kestrel con rol restringido, proceso Commerce, navegador Chromium y pruebas de límites. Las verificaciones de publicación/consumo de brokers y NFR transversales no se consideran parte de esta tarea ni quedan declaradas completas.
- **T5 — documentación:** completada para los cortes actuales; las afirmaciones sustituidas se identifican como históricas en 09 y en el diseño 06.

## Evidencia de cierre de importación

El informe `09-commerce-importacion-y-verificacion.md` registra comandos, resultados y limitaciones. La prueba Kestrel con Chromium aprobó en PostgreSQL efímero; comprobó importación nueva, reimportaciones completa y parcial, mezcla, duplicados equivalentes, conflicto atómico, operador histórico inactivo, sesión revocada, doble clic, plantilla y alta individual. El login API del recorrido fue restringido (`NOSUPERUSER`, `NOBYPASSRLS`, miembro de `nexoruta_api`). El archivo de 5 MiB válido atravesó Kestrel; 5 MiB + 1 byte respondió 413. El lote de 500 tomó 7.979 ms y la pareja concurrente en orden inverso 118 ms en ese entorno puntual; no son benchmarks de producción.

Las pruebas de cliente/componente y de integración con Testcontainers se informan por separado en 08/09. La revisión visual cubrió importación en escritorio y 320 CSS px, con tabulación/foco y ausencia de overflow horizontal; la pantalla individual `/envios/crear` se ejercitó funcionalmente en navegador, no recibió una auditoría visual exhaustiva. No se certificó WCAG 2.2 AA completo.

## Condiciones para cierre y estado

- [x] Alta individual y por API preservadas; regresión HTTP y recorrido funcional Commerce comprobados.
- [x] Alta por archivo integrada en Commerce con la plantilla del parser.
- [x] Reimportación completa y de subconjuntos sin duplicados; identidades nuevas dentro de Comercio, concurrencia y colisión de payload verificadas con PostgreSQL real.
- [x] Archivo atómico: ante error/conflicto no se confirman creaciones nuevas; resultados por fila no presentan las filas no procesadas como creadas.
- [x] Comercio autenticado fija el tenant; selección de operador validada; se verificaron permisos, aislamiento y funciones RLS restringidas en fixtures, y Kestrel con rol API restringido.
- [x] Envío, hijos, identidad y dos mensajes outbox por cada nueva creación se confirman bajo la misma transacción; reimportaciones no agregan mensajes.
- [x] Compilación y pruebas unitarias, cliente/componente, integración PostgreSQL, HTTP Kestrel y flujo Commerce/browser ejecutadas; cada modalidad de evidencia se distingue en los informes.
- [x] Importación comprobada con teclado y viewport móvil de 320 CSS px; queda pendiente una auditoría WCAG completa.
- [x] Documentación secundaria distingue monitoreo inicial, implementación actual, CU-08 obligatorio y separación entre implementación/cobertura/ejecución.
- [ ] Cerrar la matriz transversal de dos operadores/identidad de despliegue y la revisión documental de D01; no cambia la regla actual de selección de operador por envío ni habilita membresía permanente.
- [ ] Resolver los pendientes globales de entrega/reintento creciente y administración de mensajes fallidos descritos por X04/X06. Persistir outbox no demuestra publicación exactly-once ni completa por sí sola estos NFR.

## Pendientes y límites

1. **D01** (`docs/alcance/Calcs/Casos de Uso - Responsables.xlsm`, hoja `Dependencias`, rango `A4:I4`): requiere aclaración documental del término «vínculo comercio-operador». La ADR vigente define selección por envío; no se agregó una membresía permanente ni una regla de acceso.
2. **X02**: quedan pendientes evidencias completas de las configuraciones diferenciadas de dos operadores y del principal/configuración de un despliegue real. Las pruebas de aislamiento locales no deben presentarse como evidencia de producción.
3. **X04/X06**: la importación escribe `GenerarSeguimiento` y `EnvioCreado` de forma transaccional; este bloque no ejecutó publishers/consumers. El backoff creciente y la administración operativa de fallidos siguen pendientes transversales.
4. La revisión visual no cubre todos los estados, 200 % de zoom/reflow, lector de pantalla ni contraste instrumental; no es una certificación de conformidad.

No queda una decisión funcional abierta para comenzar Commerce o el contrato CSV ya implementado. La incertidumbre de D01 es documental y no debe resolverse inventando una política.

## Fuera de este cierre

La multiplicidad de bultos corresponde a **CU-08, obligatorio y separado**; la tarifa corresponde a CU-09. La importación de CU-07 no declara terminados esos casos, la máquina de estados completa ni la mensajería transversal.

El bloque de cancelación terminal está preservado en [`07-bloque-cancelacion-terminal.md`](07-bloque-cancelacion-terminal.md). Su evidencia no reemplaza la verificación integral de otras transiciones.
