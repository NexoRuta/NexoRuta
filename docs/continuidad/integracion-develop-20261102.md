# Integración de checkpoints Cloud en develop

2026-11-02. Integra CU06 B1–B5, selector de destino, CU08, CU09 y rediseño compartido con los cambios de observabilidad, Docker y sincronización que ya estaban en develop. No promociona main ni activa despliegues.

## Combinación fijada

| Componente | Commit de integración |
|---|---|
| Backend | `1f3a3d006f223df2160795e450165738319adcca` |
| Frontend | `9ec7f39cc55f43983436a86443d2e6213fd01550` |
| Mobile | `d570ddb7c482c56070140e25fafb5a18e51cdbfa` |

PRs de integración: [Backend #47](https://github.com/NexoRuta/NexoRuta-Backend/pull/47), [Frontend #44](https://github.com/NexoRuta/NexoRuta-Frontend/pull/44), [Mobile #20](https://github.com/NexoRuta/NexoRuta-Mobile/pull/20). Conservan los checkpoints publicados y la historia de develop; sin reemplazar ramas ni force-push.

## Resoluciones y validación

Se combinaron el arranque Stage con logging/telemetría y los límites de Geoapify con sus métricas de caché. El seed demo explícito usa el contrato CU09 con cobertura y tarifa sintéticas de sus propios operadores nuevos; no evita RLS ni altera tarifas existentes. La respuesta de servicios geográficos se mapea a un DTO de API conservando su JSON y actualizando OpenAPI. La prueba de arquitectura exige respuesta propia de API en cada endpoint, sin una cantidad fija obsoleta.

Las regresiones actualizadas conservan sus aserciones: CSV v2, texto español del rediseño, descubrimiento de frontend en checkout independiente y firma móvil vigente. Los hosts de pruebas frontend usan polling de archivos para no agotar inotify del runner.

Las ejecuciones CI de estos PRs y del superproyecto son la evidencia de la combinación final. Los resultados originales de Cloud permanecen documentados en las auditorías CU08/CU09 y rediseño; no sustituyen los checks de integración.

La preparación para PostgreSQL administrado crea propietarios NOINHERIT y las migraciones del historial y del plazo de prueba sólo admiten membresía del propio migrador con CREATEROLE/superusuario. Las membresías ajenas siguen rechazadas; el harness exige que el rol API no pueda hacer SET ROLE al propietario del historial. Se conserva el identificador de la migración histórica. La regresión de preparación de VM exige reinicio de brokers existentes y reconciliación explícita del núcleo de observabilidad, sin tocar datos ni ejecutar despliegues.

Las suites completas detectaron fixtures anteriores a la admisión CU09. Se actualizan a cobertura/tarifa publicadas y destino inicial confirmado, manteniendo el aislamiento y los conflictos. Las pruebas de actualización siembran el esquema anterior real, sin intentar revertir el historial protegido. Los contratos de mensajería comparan JSON semánticamente, preservando IDs y cabeceras de trazabilidad.

La preparación administrada no hereda los grupos runtime (evita combinar sus políticas RLS), pero sí los propietarios de objetos. PostgreSQL exige EXECUTE para validar CREATE OR REPLACE; se restaura sólo el permiso del propietario NOLOGIN sobre sus propias funciones, tanto en el esquema inicial como en preflight de bases existentes. No se amplía el acceso API/worker/PUBLIC.

Las pruebas Kestrel construyen el frontend exacto y usan Chromium fijado también en Linux, en lugar de asumir binarios Debug y chrome.exe de Windows.

La reserva del despachador utiliza políticas de catálogo sólo para CURRENT_USER dentro de la transacción de migración y las elimina antes de confirmar. FORCE RLS permanece habilitado; no queda un acceso permanente para runtime.

B2 admite al migrador CREATEROLE que hereda al propietario del esquema mediante políticas SELECT completas, exclusivas de su transacción y con bloqueo de escritores. Rechaza políticas restrictivas que impidan asegurar visibilidad total. No concede BYPASSRLS ni SUPERUSER y conserva el rechazo de conflictos y ocupaciones legadas sin conciliación. La regresión de transición se ejecuta también con una identidad efímera no superusuario, detecta conflictos reales y sólo activa tras conciliación explícita. El harness verifica que no quedan políticas temporales después de confirmar. Esta corrección de compatibilidad no equivale a revisión nativa ni cierra CU06.
