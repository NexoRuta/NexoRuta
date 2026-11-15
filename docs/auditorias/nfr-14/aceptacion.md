# NFR-14 — Matriz de aceptación

**Estado de seguimiento: cerrada por decisión explícita del usuario el 15/11/2026; card `Done`. Estado de evidencia técnica: parcial.** Registro del worktree local, actualizado el 15/11/2026. La implementación se publica en `develop`.

La decisión de cierre administrativa acepta dejar sin ejecución los gates operativos identificados abajo. No significa que P0–P8 se hayan demostrado completos ni que exista una CI/publicación candidata en `main`, recreación aislada, inspección de Billing o prueba viva P6.

El usuario
indicó no ejecutar recreaciones aisladas/cleanup en GCP ni la CI/publicación de
la candidata en `main`; no se despacharon esos flujos ni se cambió infraestructura.
La matriz separa evidencia local, observaciones históricas y gates pendientes.

## Fuentes de implementación

| Identidad | SHA/estado | Alcance |
| --- | --- | --- |
| Raíz base inspeccionada | `86e234e7bc0a2be1ce8911cc186ecf0e55d628e4`, árbol base `6f4011e136ced28f02b9330fb218af085e61c44c` | Base previa a NFR-14. La candidata integrada está en `develop`; la card enlazada registra el SHA publicado. |
| Backend gitlink publicado | `7562ca95b91028b682fb0aa72883be79cd038441` | Commit de backend integrado en `develop` y fijado por el gitlink raíz. |
| Frontend gitlink/base | `2540041ba267d8a48e6c2b8a644247134f5b47f4` | Sin avanzar a otra punta para esta implementación. |
| Mobile gitlink/base | `90976706c7db6a54c06ac552811f20f04d90375e` | Sin avanzar a otra punta para esta implementación. |

La revisión de fuentes/versiones está en [`evidencia/sources.json`](evidencia/sources.json).
El cierre administrativo y el SHA raíz publicado en `develop` quedan registrados
en la card enlazada. No presentar los SHA base como la publicación de esta implementación.

## Historial que no acredita la candidata

| Run | Resultado observado | Referencia | Por qué no cierra P4 |
| --- | --- | --- | --- |
| `41946941369` (`main`, 05/11/2026) | Éxito histórico; tag `integration-41946941369-1`; release `release-17bcf47546124de5acb87adc7f84e00d`; Cloud Build `cbe278fd-f40a-49fb-8103-a559cc2df99b`; bundle SHA-256 `8ecf512be79d2b849e19f328ac70d73912080eb7ccc5ff184af6b6642332ced2`. | [Diagnóstico](diagnostico.md), [manifiestos/canales](evidencia/delivery-channels-2026-11-14.json) | Es anterior al cambio local; no prueba los SHA ni artefactos finales NFR-14. |
| `43631884438` (`develop`, 14/11/2026) | `update/develop` exitoso; release `release-bd39c48fde2b49fa80b18a01f173ebd6`; Cloud Build `b47edff9-9be1-4275-a9f2-cee3be4c4da6`; bundle SHA-256 `12bb73c4caaae928c0a6d934e4fdb9d3e718734b0705221c5ac68819e5cebdf4`. | [Diagnóstico](diagnostico.md), [manifiestos/canales](evidencia/delivery-channels-2026-11-14.json) | Develop no ejecuta Integrated CI; además es anterior al cambio local y comparte la demo. |

No existe run/attempt, tag, build, manifest, bundle hash ni conjunto de seis
digests de la candidata actual. No hay artifact de CI candidato ligado al SHA raíz
y gitlinks finales; el push a `develop` no ejecuta por sí solo la CI integrada ni publica desde `main`.

## Gates

| Gate / criterio | Estado | Evidencia disponible | Pendiente para aceptar |
| --- | --- | --- | --- |
| P0 — fuentes, destino e inventario | Parcial | Diagnóstico y capturas sanitizadas; gitlinks base exactos; recursos demo inventariados. | Finalizar identidad del candidato y resolver con evidencia el historial de digest/schema en cada VM; confirmar todas las precondiciones. |
| P1 — credenciales y contrato actualizado | Implementada en `develop`; CI/operación pendientes | Código/contrato en los commits publicados; build y pruebas backend locales. | CI de la combinación final; transición operativa del admin existente con respaldo y ventana aprobados. |
| P2 — insumos, manifiesto y retención | Implementada en `develop`; publicación pendiente | Checks locales; el bundle incorpora validador de host y el smoke NFR-14 serializa versiones sanitizadas de ambos nodos. | Publicación candidata, verificación remota del manifiesto/digests, consumo del artifact de CI/Android y evidencia real de hosts en la release desplegada. |
| P3 — bootstrap y planes seguros | Implementación local; bootstrap remoto pendiente | `tofu init/validate` local en copia sin backend; pruebas de guards y scripts. | Aplicación autorizada del bootstrap y verificación de WIF/permisos en el entorno que opere. |
| P4 — CI → publicación → despliegue | Pendiente; aceptado sin ejecución para el cierre administrativo | Solo publicaciones históricas de la tabla anterior. | No existe CI/publicación candidata en `main`; se omitió por instrucción del usuario. La card Done no afirma que haya ocurrido. |
| P5 — recreación/cleanup/segunda recreación | Pendiente; aceptado sin ejecución para el cierre administrativo | Implementación local de `reproduce.py`, módulo, workflow, pruebas y runbook; sin proyecto de ensayo creado. | No se creó, recreó ni limpió un proyecto GCP; no hay segunda recreación. Se omitió por instrucción del usuario. |
| P6 — HTTPS y sistema real | Parcial | Verificador local actualizado para exigir en el smoke v3 el inventario exacto de Compose y los healthchecks declarados de A/B; pruebas unitarias locales. HTTP/TLS histórico del 14/11 pasó en la demo; el corte posterior observó A/B detenidas. | Verificación del candidato en ensayo autorizado; schema/PostGIS/RLS entre organizaciones, salud funcional de dependencias compartidas, captura de correo, segunda recreación, login/lecturas, stop y revisión manual en navegador. |
| P7 — costo y presupuesto | Pendiente; aceptado sin completar evidencia para el cierre administrativo | Presupuesto observado: USD 80/mes, `EXCLUDE_ALL_CREDITS`, umbrales 50/80/100 %. [`costos-observados.json`](evidencia/costos-observados.json) registra explícitamente que no se consultó Billing Reports. | No hay Billing Report/Cost table con bruto/créditos/neto ni presupuesto de ensayo porque no se creó el proyecto aislado. |
| P8 — documentación/evidencia/cierre | Parcial local | README, requisitos, environment, tags, guía, proyecto, runbook, costos y esta matriz revisados. | Actualizar valores finales tras gates reales; limpiar campos pendientes sin reescribir observaciones históricas. |

## Validaciones locales y límites

| Categoría | Resultado local | Qué demuestra / qué no demuestra |
| --- | --- | --- |
| Compilación | Restore `--locked-mode` y build de la solución backend: éxito. 382 unit tests y 7 architecture tests: éxito. | No es build de Cloud Build ni de las seis imágenes del candidato. No equivale a CI integrado remoto. |
| Automatización | `scripts/gcp`: 339 casos, 331 aprobados, 8 skips documentados y 0 fallidos. El grupo focal de NFR-14 ejecutó 112 casos con 1 skip. Backend/Testcontainers con Docker WSL y PostgreSQL 18/PostGIS: 42 casos seleccionados; luego 13 retest tras cambiar nombres de casos para no exponer passwords en logs. | Los tests cloud son simulados/locales o usan fixtures; no crean recursos GCP ni comprueban factura. |
| Validación estática | `tofu fmt`; init/validate de bootstrap/demo/reproduction-project en copias temporales; `compileall`; `bash -n`; actionlint con ignore acotado para la extensión `queue`; Compose validado desde WSL. | No aplica estado ni autentica contra GCP. |
| HTTP/TLS | Inspección histórica a las 19:56 UTC del 14/11: endpoints de salud/ingreso respondieron 200 con TLS normal; Grafana y Mailpit rechazaron requests anónimos con 401 como correspondía. | No es el candidato nuevo ni el estado actual: a las 20:21 UTC las VMs ya estaban detenidas. |
| Revisión visual | No realizada. | Falta navegador con login, navegación y lectura por rol en la candidata, con capturas sanitizadas. |
| Costos | No hay Billing Reports ni Cost table capturados. | El presupuesto es solo alerta y no prueba gasto observado. |

Detalle adicional de pruebas y límites en [diagnostico.md](diagnostico.md).

## Recursos al terminar esta implementación local

- No se creó ni destruyó un proyecto de reproducción NFR-14; no hay limpieza de
  GCP pendiente atribuible a esta implementación.
- No se lanzó `ci.yml`, `publish.yml`, `vm-controls.yml` ni `reproduce.yml` durante
  este trabajo local. No se inició el runtime de la demo ni se modificó GCP.
- La observación remota del 14/11 reportó A/B detenidas, Cloud SQL principal
  `RUNNABLE`/`ALWAYS`, SQL de restauración detenido, Memorystore `READY`, y
  recursos persistentes descritos en el diagnóstico. No se volvió a consultar.
- No se leyeron valores de secretos, estados/planes OpenTofu ni datos de negocio.

## Decisión

**Decisión de cierre:** el usuario pidió marcar la card `Done` y publicar en
`develop`. Se registra como cierre administrativo con brechas conocidas
aceptadas, no como aprobación de los gates técnicos que siguen pendientes.
Mantener esta distinción en futuras referencias y no mover NFR-13/NFR-12 por
esta evidencia.
