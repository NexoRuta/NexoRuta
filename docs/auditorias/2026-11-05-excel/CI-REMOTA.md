# CI remota: evidencia insuficiente en los SHAs efectivos

**Dictamen:** OPT08, NFR15 y OPT07 quedan **No verificado** respecto de su prueba remota. Se consulto GitHub en modo solo lectura; no se encontro un run identificable mediante las consultas disponibles. Esto **no demuestra ausencia de pipelines, pruebas ni artefactos**.

Consulta: **2026-11-05 19:01:54 UTC**. Alcance autorizado: consultar ejecuciones existentes de los cuatro SHAs exactos. No se dispararon/reintentaron workflows, no se publico nada, no se opero infraestructura remota ni se inspeccionaron credenciales.

## Resultado por repositorio

| Repositorio | SHA efectivo | Runs PR devueltos | Statuses devueltos | URL/run/workflow/fecha/resultado/job |
|---|---|---:|---:|---|
| NexoRuta/NexoRuta | [`4e5c233dc751736ed59cc234582f157f5c9c278a`](https://github.com/NexoRuta/NexoRuta/commit/4e5c233dc751736ed59cc234582f157f5c9c278a) | 0 | 0 | No disponibles; no se inventan |
| NexoRuta/NexoRuta-Backend | [`09538d989399b511473ad5af063754ea76d554a6`](https://github.com/NexoRuta/NexoRuta-Backend/commit/09538d989399b511473ad5af063754ea76d554a6) | 0 | 0 | No disponibles; no se inventan |
| NexoRuta/NexoRuta-Frontend | [`d328e98c27db7c5cef018ab3492c54fc563eed49`](https://github.com/NexoRuta/NexoRuta-Frontend/commit/d328e98c27db7c5cef018ab3492c54fc563eed49) | 0 | 0 | No disponibles; no se inventan |
| NexoRuta/NexoRuta-Mobile | [`683766d6d8cd6c1bd9ce45bb12f6581ddb19b98c`](https://github.com/NexoRuta/NexoRuta-Mobile/commit/683766d6d8cd6c1bd9ce45bb12f6581ddb19b98c) | 0 | 0 | No disponibles; no se inventan |

## Que se consulto y que no permite concluir

1. `gh` no esta disponible en PATH; tampoco aparecio en las tres ubicaciones estandar comprobadas. No se instalo ni cambio autenticacion.
2. Se uso el conector GitHub disponible: `github_fetch_commit_workflow_runs` para cada SHA. Las cuatro respuestas fueron `workflow_runs: []`. **Su contrato filtra eventos `pull_request` y solo devuelve la primera pagina**; no cubre exhaustivamente push, schedule, workflow_dispatch ni todos los tipos de ejecucion.
3. Una segunda consulta acotada uso `github_get_commit_combined_status` para cada SHA: las cuatro respuestas fueron `statuses: []`. No equivale a enumerar exhaustivamente los check-runs/check-suites de Actions.
4. Sin un run ID identificado no corresponde consultar jobs o artefactos ni atribuir URL, fecha, workflow, conclusion o nombre de job a una ejecucion desconocida. Los enlaces de la tabla son a **commits**, no a ejecuciones aprobadas.

Ocho consultas GitHub de lectura en dos lotes, sin arqueologia recursiva. El registro estructurado esta en [ci-remote.json](ci-remote.json).

## Condiciones de acreditacion

| Requisito | Hallazgo actual | Recomendacion al cierre |
|---|---|---|
| OPT08: E2E en pipeline | El workflow fuente integra pruebas de navegador, pero estas consultas no acreditan que los flujos criticos hayan corrido para el candidato efectivo, ni resuelven las cinco omisiones opt-in locales. | No acreditar solo por la existencia del workflow. Inspeccionar run/job/TRX del candidato y las condiciones opt-in de sus flujos criticos. |
| NFR15: calidad en pipeline | Las pruebas locales actuales son evidencia diferente; no se obtuvieron conclusiones remotas de unitarias, integracion, arquitectura y aislamiento. | Mantener No verificado para la condicion pipeline completa hasta revisar los jobs aplicables y justificar omisiones. |
| OPT07: cobertura >70% | No hubo run ID para consultar un artefacto de cobertura. No se afirma que el artefacto no exista. La dependencia coverlet por si sola no mide cobertura. | Exigir reporte/artefacto de Domain y Application superior al 70%, publicado por el pipeline y asociado a un run concreto. |

**Puntos:** no se otorgan ni se retiran silenciosamente puntos con respuestas vacias de alcance limitado. Esta comprobacion no cambia la seleccion de 14 puntos potenciales ni sustituye el dictamen del padre.

## Siguiente paso exacto

Obtener una URL/ID conocida de GitHub Actions del candidato efectivo, o habilitar una lectura que enumere todos los tipos de eventos y check-runs. Revisar sus jobs y artefactos sin ejecutar/reintentar nada. Mientras esa prueba no este disponible, informar **No verificado**, no «pipeline ausente» ni «E2E aprobado».

## Key Learnings:

1. El conector de runs por commit solo devuelve eventos pull_request y no prueba ausencia de otros workflows.
2. Una lista vacia de statuses no acredita el estado de todos los check-runs de GitHub Actions.
3. Los artefactos de cobertura y E2E requieren identificar una ejecucion concreta antes de atribuir resultados.

