# Integración de checkpoints Cloud en develop

2026-11-02. Integra CU06 B1–B5, selector de destino, CU08, CU09 y rediseño compartido con los cambios de observabilidad, Docker y sincronización que ya estaban en develop. No promociona main ni activa despliegues.

## Combinación fijada

| Componente | Commit de integración |
|---|---|
| Backend | `7b88c603e521b1eb013b755ed8cd6827bb37404a` |
| Frontend | `017ecc89a0353236aa1d77a9902a5c953133baf1` |
| Mobile | `0c88a4aaddb517976a3de993be0da78743024014` |

PRs de integración: [Backend #47](https://github.com/NexoRuta/NexoRuta-Backend/pull/47), [Frontend #44](https://github.com/NexoRuta/NexoRuta-Frontend/pull/44), [Mobile #20](https://github.com/NexoRuta/NexoRuta-Mobile/pull/20). Conservan los checkpoints publicados y la historia de develop; sin reemplazar ramas ni force-push.

## Resoluciones y validación

Se combinaron el arranque Stage con logging/telemetría y los límites de Geoapify con sus métricas de caché. El seed demo explícito usa el contrato CU09 con cobertura y tarifa sintéticas de sus propios operadores nuevos; no evita RLS ni altera tarifas existentes. La respuesta de servicios geográficos se mapea a un DTO de API conservando su JSON y actualizando OpenAPI. La prueba de arquitectura exige respuesta propia de API en cada endpoint, sin una cantidad fija obsoleta.

Las regresiones actualizadas conservan sus aserciones: CSV v2, texto español del rediseño, descubrimiento de frontend en checkout independiente y firma móvil vigente. Los hosts de pruebas frontend usan polling de archivos para no agotar inotify del runner.

Las ejecuciones CI de estos PRs y del superproyecto son la evidencia de la combinación final. Los resultados originales de Cloud permanecen documentados en las auditorías CU08/CU09 y rediseño; no sustituyen los checks de integración.
