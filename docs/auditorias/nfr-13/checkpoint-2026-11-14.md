# Checkpoint de ejecución NFR-13 — 14/11/2026

**Corte:** 2026-11-14 04:09 UTC. **Estado:** implementación integrada; aceptación GCP pendiente. La última sesión quedó en estado parcial y tiene parada automática prevista; no se ejecutó baseline ni prueba de fallos.

Este checkpoint registra la continuidad de la ejecución. No modifica el manifiesto histórico `scripts/cloud/checkpoint.json`, que sigue siendo un inventario de fuentes y no un estado de tarea.

## Fuentes y CI

- PR raíz [#78](https://github.com/NexoRuta/NexoRuta/pull/78), commit integrado `8b1392a815008918b5fd5352e2488025c3d11233`.
- PR correctivo [#79](https://github.com/NexoRuta/NexoRuta/pull/79), commit integrado actual de `develop`: `b439ea8195297ab2ae512bd24cafd92a9d0841bb`.
- Gitlinks en `develop`: backend `425634e743fed4e3217c77c8ef3cf56ec0e150c7`, frontend `2540041ba267d8a48e6c2b8a644247134f5b47f4`, mobile `840a5570cece18eb4de558b3b5004ae935dff771`.
- CI de NFR-13, run `43459956040`: todos los jobs verdes; tres integration shards, frontend, backend, Cloud SQL, infraestructura y Android.
- CI del correctivo, run `43467708390`: todos los jobs verdes; los tres integration shards también terminaron correctamente.
- Suite local `scripts/gcp`: 257 aprobadas, 0 fallidas, 8 omitidas por capacidades/plataforma opcionales. Pruebas focalizadas del preparador: 11/11.

El correctivo acepta el nombre canónico que Secret Manager devolvió como `projects/1090571196455/secrets/nexoruta-load-fixtures/versions/2`. El preparador antes solo aceptaba el ID de proyecto y abortaba antes de sembrar la fixture.

## GCP observado

- Deploy anterior: run `43462915487`, correcto para la release `release-9bab36bca9314719b484e3fc4aa0d0f7`; ambas VM quedaron `RUNNING`, API A/B `HEALTHY`, Cloud SQL `RUNNABLE` y las comprobaciones HTTPS pasaron. Su lease de cuatro horas venció durante la pausa; el inventario read-only del 14/11 a las 03:55 UTC confirmó ambas VM `TERMINATED`, SQL `RUNNABLE`, ningún backend sano y ninguna lease activa. Evidencia: `evidencia/gcp-inventario-2026-11-14-pretest.json`.
- La primera corrida de baseline, run `43466857758`, abortó durante preparación con `current fixture secret has an invalid version name`, antes del login del preparador y antes de cualquier escritura SQL o ejecución Cloud Run. Reserva `799a854e-119d-4eaa-b549-bb58a03b362c` cancelada explícitamente; `load_tests.assert_no_active` confirmó que no quedó una lease de carga.
- Se comprobó Prometheus desde VM A y desde el contenedor Grafana. `/api/v1/query?query=up` respondió JSON `success`; el PromQL exacto del panel **Servicios disponibles** respondió `success` con 23 series (A: 12, B: 11). HTTP externo: `/ready` API y portales 200; Grafana `/api/health` 200. Esto verifica la ruta de datos; no es una captura visual del panel.
- BrowserAct no pudo completar revisión visual: Chrome directo terminó con `230404` (ventana CDP expirada) y `stealth-extract` exige una API key que no está configurada.
- SQL continúa siendo zonal y varios servicios de observabilidad/brokers residen solo en A; no declarar HA completa.

## Operación y estado al cierre del checkpoint

- PR #79 ya integrado en `develop` con SHA `b439ea8195297ab2ae512bd24cafd92a9d0841bb`.
- Workflow manual de nueva sesión/redeploy: run [`43554138598`](https://github.com/NexoRuta/NexoRuta/actions/runs/43554138598), ref `develop`, SHA `b439ea8195297ab2ae512bd24cafd92a9d0841bb`. `publish_develop` terminó correctamente; el job `deploy` fue cancelado a las 04:08:19 UTC mientras ejecutaba `Run the requested manual VM operation`. No considerar el deploy completo ni asumir que ambos nodos tienen la misma release.
- Inventario read-only a las 04:09:33 UTC: ambas VM `RUNNING`; SQL `RUNNABLE`; solo el backend B aparece `HEALTHY`; sesión activa con 13 840 segundos restantes. La lease implica cierre automático esperado cerca de las 08:00 UTC. Evidencia: `evidencia/gcp-inventario-stop-checkpoint-2026-11-14.json`.
- Se solicitó el apagado coordinado con workflow [`43554645544`](https://github.com/NexoRuta/NexoRuta/actions/runs/43554645544), pero terminó fallido a las 04:08:47 UTC con `Another demo control operation holds the shared lock`. No alcanzó a modificar las VMs. Por indicación del usuario, no se reintentará: dejar vencer la lease y verificar mañana que el cierre automático se completó. Si no están `TERMINATED` luego de su vencimiento, apagar mediante `vm-controls.yml` antes de continuar.
- No se ejecutó baseline, carga, escenario de fallo ni prueba de estabilidad en esta ventana. La corrida anterior `43466857758` fue abortada antes de escribir datos; la corrección de Secret Manager ya está integrada, lista para el próximo intento.

## Continuar desde aquí

1. Confirmar que la sesión de este checkpoint venció y ambas VM quedaron `TERMINATED`; si no, detenerlas con `vm-controls.yml` antes de continuar. La evidencia más reciente aún las muestra encendidas y solo B `HEALTHY`.
2. Abrir una nueva sesión con el workflow autorizado desde `develop`; comprobar que termina `success`. No usar el release histórico ni la corrida cancelada como deploy válido.
3. Obtener la release nueva y el origen actual del resumen del run. Repetir `python scripts/gcp/verify_nfr13.py inspect --output docs/auditorias/nfr-13/evidencia/gcp-inventario-poststart-2026-11-14.json`. Exigir lease activa con margen suficiente, A/B `RUNNING`, ambos API backends `HEALTHY`, SQL `RUNNABLE`, misma release en los dos nodos y `/ready`, `/live`, `/health` HTTP 200.
4. Reintentar baseline con el código correctivo ya integrado: `gh workflow run load-tests.yml --repo NexoRuta/NexoRuta --ref develop -f operation=run -f profile=baseline`. Perfil: máximo 5 usuarios sintéticos y 15 minutos medidos. Registrar el run ID y confirmar resultado final `passed`; no considerar el intento anterior como carga ejecutada.
5. Con la release y el `api_origin` nuevos, correr de a uno los cuatro casos del [runbook](runbook.md): contenedor API A, contenedor API B, VM B y VM A. Usar confirmación tipada exacta y conservar cada JSON; verificar `passed`, restauración y ambos backends sanos antes del siguiente caso.
6. Después de los fallos, observar 30 minutos de estabilidad: ambos nodos sanos, sin restarts/OOM, y reconciliar outbox y job. Registrar recursos, errores y lease; si se pierde la sesión o quedan menos de 90 minutos para recuperar, no comenzar otro fallo.
7. Actualizar `aceptacion.md` con los resultados reales y la evidencia sanitizada. Mantener aceptación pendiente si falta cualquier gate; no incluir archivos no relacionados de `docs/auditorias/ap-04/`.

No ejecutar `tofu apply` de la topología, `docker compose down -v`, limpieza de discos/volúmenes ni cambios a SQL como recuperación. El workflow `start` es la operación autorizada de sesión con parada automática acotada; inspeccionar su resultado antes de probar.

## Estado local al checkpoint

- Rama local: `nfr13-checkpoint`, basada en `develop` `b439ea8`.
- El checkout de `frontend/` está localmente en `162bf08`, mientras el gitlink raíz fija `2540041`; figura `M frontend` por esa divergencia local conocida. No cambiarlo ni incorporarlo como gitlink.
- Hay evidencias locales sin seguimiento de AP-04 en `docs/auditorias/ap-04/`; conservarlas fuera de este commit.
- No hay cambios locales de producto pendientes de integrar. Este checkpoint, el plan actualizado y el inventario GCP de 04:09:33 UTC son las únicas evidencias que se deben registrar en este commit; conservar fuera del commit el estado divergente de `frontend/` y los archivos AP-04 sin seguimiento.
