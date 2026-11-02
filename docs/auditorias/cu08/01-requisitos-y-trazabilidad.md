# CU08 — bultos múltiples

Base: raíz `8991321593f9092e18aac83d6a9a11df4c388cb3`, backend `5bd165c`, frontend `904af71`, mobile `5302b20`. Auditoría e implementación sobre las ramas `task-cu08-cu09-20261102` y `task-cu08-cu09-hig-20261102`.

## Fuentes oficiales

- `docs/alcance/Laboratorio__NET_2026.pdf`, sección 5.2, numeral 8 (página impresa 4): «Un envío puede contener uno o más bultos, cada uno con su identificación, peso y dimensiones».
- `docs/alcance/Calcs/Casos de Uso - Responsables.xlsm`, hoja CU obligatorios, A11:I11: CU-08 obligatorio, comercio, Portal/API. Lectura XML sin ejecutar macros.
- Dependencias D06 y D09: capacidad/paradas y escaneo consumen la colección completa.
- CU07 conserva idempotencia y rechazo atómico de lotes; CU09 es una etapa independiente.

## Hallazgo inicial

El modelo relacional y los lectores ya admitían varios bultos, pero CrearEnvioRequest, CrearEnvioCommand, CrearEnvioUseCase y la respuesta de alta reducían el agregado a uno. El portal tampoco permitía agregar otro. No corresponde declarar cumplido CU08 con la cardinalidad de la tabla solamente.

## Trazabilidad

| Requisito | Implementación | Verificación |
|---|---|---|
| Uno o más bultos | Contrato `Bultos`, alta individual y portal agregar/quitar | Unitarias de colección vacía y colección completa; HTTP multibulto |
| Identificación por bulto | Código obligatorio, hasta 80 caracteres; rechazo de repetidos normalizados en un envío | Unitarias de duplicados; persistencia/listado HTTP |
| Peso/dimensiones por bulto | Dominio Bulto y validación recursiva del contrato; precisión B1 de dos decimales efectivos | Unitarias existentes de precisión; HTTP segundo bulto inválido sin efectos |
| Persistencia íntegra | Colección completa mediante función de admisión SECURITY DEFINER existente con nuevo contrato JSON; RLS por bulto sin conceder INSERT al rol API; outbox por envío | HTTP PostgreSQL/PostGIS con rol restringido; regresiones roundtrip/importación |
| Importación de varios bultos | Una fila declara un bulto; misma referencia y destinatario agrupan el envío; distinto código distingue cada bulto | Reordenar/repetir filas conserva identidad y no duplica bultos/outbox |
| Idempotencia | Huella incluye todos los bultos ordenados por código; identidad original inmutable | Reimportación completa/reordenada; conflictos y rechazo de lote existentes |
| Consumidores | Listado agrupa todos los bultos; Backoffice suma pesos; reparto obtiene la colección por envío; mobile conserva `Bultos[]`; calculadora tarifaria suma colección | Regresiones unitarias y pruebas del selector; ver registro de ejecución |

Una reimportación parcial de lote puede seleccionar envíos completos. Omitir un bulto de un envío ya importado cambia la declaración original y debe generar conflicto, sin alterar el envío existente. Datos de destinatario distintos para una misma referencia o medidas distintas para un mismo código también generan conflicto.

## Límites

La evaluación y el cierre se registran con resultados ejecutados en el informe de verificación. Este documento por sí solo no acredita cierre ni CU09, CU06 o habilitación operativa. No se cambia RLS ni se consumen proveedores externos.
