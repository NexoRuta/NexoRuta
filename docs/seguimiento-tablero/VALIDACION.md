# Registro de validación

La implementación está publicada en las PR [Backend #49](https://github.com/NexoRuta/NexoRuta-Backend/pull/49) y [Frontend #51](https://github.com/NexoRuta/NexoRuta-Frontend/pull/51), con destino `develop`.

Candidato Backend: `655edd3a2f2e2326e7a9d99bb2a405b81ee7b6e8`. Frontend: `7ce3e969924e1157d2eaa80b5c933bea9560f5b0`. Mobile conserva `f2b3db412ce23b0b36215fd301f6d3d3d6959252`.

El [CI final de Frontend](https://github.com/NexoRuta/NexoRuta-Frontend/actions/runs/42305724340) pasó. El [CI del SHA final Backend](https://github.com/NexoRuta/NexoRuta-Backend/actions/runs/42305992972) está en curso. No se integra una PR hasta completar los checks finales verdes.

## Cobertura

Métrica: líneas de fuente ejecutables, unión por archivo/línea de unitarias e integración, por capa. El control es estrictamente **>70% en cada capa**, sin exclusiones personalizadas. No hay atributos de exclusión añadidos en Domain/Application. Los valores y fallos/omitidas iniciales están publicados en `backend/docs/seguimiento-tablero/evidencias/`.

| Capa | Inicial | Última medición completa de CI | Estado del cierre final |
|---|---:|---:|---|
| Domain | 1880/2038 — 92,25% | 1880/2038 — 92,25% | Esperando CI final |
| Application | 1543/1638 — 94,20% | 1576/1673 — 94,20% | Esperando CI final |

La última medición completa corresponde al [CI verde de cd8cdcb](https://github.com/NexoRuta/NexoRuta-Backend/actions/runs/42301253993). El ajuste posterior afecta Infrastructure; el pipeline vuelve a comprobar todo sobre el SHA final. La cobertura de Mobile no se mezcla con Backend; no se midió cobertura adicional de Mobile.

## Evidencias locales

- 346 unitarias y 4 de arquitectura de Backend aprobadas.
- 96 verificaciones focalizadas de regresión, aislamiento, importación, segunda visita y retiros aprobadas.
- 8 escenarios operativos completos aprobados; 2 adicionales de MongoDB/replay verifican igualdad JSON sin depender del orden de propiedades.
- 7 casos de seguimiento/contrato/retiro público aprobados, incluidos retiros con 1/500/501/1500 bultos, y 6 casos de reserva de outbox aprobados.
- Frontend: 518 pruebas aprobadas sin omitidas, incluidos los navegadores opt-in; 21 pruebas Node aprobadas.
- Principal: 221 controles Python aprobados sin omitidas, prueba de gitlinks y actionlint aprobados. PowerShell ejecuta únicamente un receptor Python de argumentos; no se ejecuta el cuerpo de setup ni un motor IaC.
- Migración completa y controles de roles, RLS, hosting y cuotas en PostgreSQL **efímero** con migrador sin superusuario/BYPASSRLS aprobados. No se conectó a Cloud SQL ni a una VM real.

`evidencias/operacion.json` conserva identidades de topic/grupos aislados, 12 eventos únicos y 9 filas reconstruidas idénticas, además de la recepción en Mailpit y recuperación SMTP. Las capturas y resúmenes de Chromium quedan en los artefactos de CI. Se revisaron escritorio y web a 320 px, teclado y foco; axe del tablero no encontró violaciones. No se realizó una validación visual nativa Android.

La corrida local completa anterior se interrumpió tras fallos de aserciones ya actualizadas y falta de disco temporal de Docker VFS; **no cuenta como aprobada**. Los pipelines posteriores ejecutan el inventario exhaustivo en tres shards y publican TRX/Cobertura. Las ejecuciones canceladas o fallidas no se cuentan como verdes.

## Principal y límite de autorización

La PR del principal no se abrió: `.github/workflows/ci.yml`, job `infrastructure`, dispara `tofu fmt`, `tofu init -backend=false` y `tofu validate`. La base actual no coincide con la última combinación integrada publicada y, además, el cambio de runner exige esa validación. La instrucción de no ejecutar IaC se mantiene; está pendiente la aclaración solicitada al usuario sobre autorizar exclusivamente esas validaciones estáticas. La rama feature deja el conjunto revisable sin disparar ese workflow. No se omitieron protecciones de ramas.

El guion está en [DEMOSTRACION.md](DEMOSTRACION.md). CU-28 y los demás puntos expresamente fuera de alcance conservan su implementación actual; Kafka interno y correos no se acreditan como webhooks HTTP salientes.
