# Revisión UX/UI de los portales

Base consultada mediante fetch explícito de `refs/heads/develop`: raíz `d420dfefc70f0b4e789ae350d4d66bba9e4180a0`; Backend `1d5e912263368d91135884f9895b71513b99509a`; Frontend `fedb7731bb62dcb29a093bc98893c593d4cd8ba7`; Mobile `53f6be2cdec48f48e30e390060feeaefb5be0ead`. Los checkouts hermanos y la rama local `work` se conservan. Los submódulos se inicializaron con esos gitlinks; no se sustituyeron por puntas independientes para resolver compilaciones.

## Cambios

- Reportes: comercio, zona y repartidor por nombre, «Todos», búsqueda explícita, páginas de 50 opciones y recuperación sin perder la selección. Los cortes se agrupan en desplegables; porcentaje, base, exclusiones, volumen y motivos siguen disponibles. Los motivos anteriores no se filtran por el resultado final del envío.
- Detalle: código comercial del bulto, autor resuelto por su identidad histórica y ruta identificada por fecha/matrícula. Los nombres se indican como actuales; no se fabrica un snapshot histórico. El enlace de regreso conserva los filtros.
- Cuenta y liquidaciones: comercio por nombre, resumen compacto, acceso «Ver cuenta» con comercio y fechas, documentos identificados por fecha/estado/importe, UUID e historial secundarios. La confirmación sigue diferenciada de un pago; la corrección conserva su efecto y el documento original.
- Commerce: las referencias a envíos usan códigos de bulto; la consulta sigue limitada a la cuenta del comercio de la sesión. Webhooks agrupa datos de integración/diagnóstico, conserva destino/estado y guarda operador/filtros/página/detalle en URL.
- Tracking `/comercio`: disponibilidad, eventos e intentos separados; controles sintéticos agrupados en un desplegable accesible por teclado y tacto.
- Tablero: la navegación a solicitudes de nueva visita tiene apariencia de acción secundaria. Se conserva la navegación HTML y los comandos/formularios existentes.

No se modifica MAUI, estados de negocio, tarifas, denominadores, firma, autenticación, claves, reintentos, deduplicación ni documentos confirmados. No se ejecutan despliegues ni se usan bases compartidas o proveedores facturables.

## Lectura mínima

`GET /api/gestion/operadores/{operador}/opciones/{tipo}` reutiliza el módulo de gestión y su permiso `envios.consultar`. Tipos de filtro: Comercio, Zona, Repartidor; referencias: Envio, Bulto, Ruta. Búsqueda literal por nombre, orden nombre/UUID, páginas de 50 con `hayMas`; resolución de hasta 100 identidades por petición. No se carga un catálogo completo en el navegador. La selección fuera de la primera página se resuelve aparte.

Los casos de uso validan el operador de la sesión. Commerce solamente puede resolver Envio/Bulto, con selección de operador y RLS existentes; no recibe catálogos de otros comercios. Se incluyen entidades inactivas para consultas anteriores. Comercios homónimos se distinguen por código de un envío autorizado; repartidores homónimos, por correo disponible bajo RLS; zonas homónimas, por su fecha de creación en Uruguay. No se amplían grants ni políticas. La tabla de identidad de importación no es legible por el rol API: no se consulta ni se amplía su acceso para este rediseño.

Los nombres son actuales. Los identificadores de autor/ruta provienen de la proyección histórica; la presentación no los reemplaza por asignaciones actuales. Los códigos de bulto existentes identifican los enlaces a envíos; no se crea numeración nueva.

## Semántica temporal

Se conserva `Hasta (excluido)` y el intervalo `[Inicio(Desde), Inicio(Hasta))` en America/Montevideo. No se transforma la fecha final en un día inclusivo ni se modifica la pertenencia de movimientos o admisiones al período. Corte y período del documento permanecen visibles. La cuenta usa fecha de registro; el reporte mantiene admisión para volumen/cumplimiento y fecha física para motivos.

## Atribución histórica: diagnóstico y trabajo separado

El registro Windows `01a1b821-8cbd-74e4-9c78-e0a0ae953903` no está disponible en Cloud. No se afirma haberlo consultado ni reparado.

La función `reconcile_management`, en la migración `20261108010000_ManagementReporting.cs`, resuelve autor/ruta mediante operaciones `Aplicada` de `EntregaFisica`/`EntregaBultos` y exige igualdad exacta entre `(Payload->>'ocurridaEn')::timestamptz` y `Bultos.EntregadoEnUtc`. Para parciales exige además el resultado entregado del bulto. El intento fallido usa su propio hecho y no demuestra por sí solo la autoría de la entrega posterior.

Existe un riesgo verificable de precisión: JSON de .NET conserva siete decimales de segundo; Npgsql escribe timestamps con precisión de microsegundos truncada, mientras el parser textual de PostgreSQL redondea. Una fracción de 0,7 microsegundos puede producir fechas diferentes en esa igualdad, aun existiendo el hecho canónico con autor y ruta. La prueba sintética `PrecisionDeFechaCanonicaExplicaAtribucionAusenteSinReescribirHistoria` documenta este caso sin modificar datos del usuario.

Corregir esa relación requiere cambiar la reconstrucción de la proyección, fuera del alcance autorizado para el defecto de presentación. Trabajo separado: inspeccionar payload, bulto y diario canónicos del registro concreto; confirmar si la diferencia es precisión u otra causa; definir una normalización determinista consistente con el almacenamiento, limitada al tipo, bulto y resultado aplicado; probar visitas múltiples y evidencia posterior; publicar una migración de la función y reconstruir únicamente la proyección con su procedimiento autorizado. No atribuir por proximidad temporal arbitraria ni por asignación actual. No cambiar documentos confirmados ni reescribir el diario.

## Evidencia

Los resultados finales y capturas comparables se registran en `verificacion.md`. Los ensayos originales pasaron: circuito de gestión y circuito integral HTTP de webhooks, cada uno con API/PostgreSQL y sesiones propios. Los ensayos no dependen de Windows ni de credenciales pegadas en el chat. `dev.py start`/`verify` comprobó API autenticada, PostGIS y rol restringido/RLS. El smoke interactivo previo de webhooks encontró HTTP 409 en la admisión de su envío; se conserva como límite de ese helper, sin debilitar reglas para hacerlo pasar. El circuito integral aislado sí verificó las entregas HTTP reales.

## Publicación

- [Backend #55](https://github.com/NexoRuta/NexoRuta-Backend/pull/55): `c786977580dc5fb01839ee8c9816118c7e8dbf1e`.
- [Frontend #54](https://github.com/NexoRuta/NexoRuta-Frontend/pull/54): `b994957d3ae30c3a6290e8d990b95ba00273232c`.
- Mobile permanece en `53f6be2cdec48f48e30e390060feeaefb5be0ead`.

Ambos hijos se publicaron antes de actualizar los gitlinks raíz. Sus ramas develop contienen commits de integración con árboles idénticos a los gitlinks iniciales; se comprobó esa igualdad sin cambiar la base de fuentes seleccionada. Las PR quedan abiertas hacia develop, sin merge ni auto-merge. La última compilación de los commits publicados pasó y la repetición final de ambos circuitos, con zoom nativo y capturas revisadas, aprobó 2/2.

El CI de Backend fija el companion Frontend exactamente en `b994957d3ae30c3a6290e8d990b95ba00273232c`, para que las regresiones de selectores se ejecuten contra el mismo portal publicado, sin cambiar otros componentes para resolver builds. El encabezado del detalle también resuelve la zona por nombre actual cuando la proyección solo conserva su identidad. Su recorrido completo se volvió a comprobar (1 prueba aprobada).
