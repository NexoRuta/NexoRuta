# Checkpoint integrado CU09 y rediseño

Continuación de `d3ae05c`; CU08 permanece cerrado. Ver trazabilidad en `docs/auditorias/cu09/02-implementacion-y-trazabilidad.md`, resultados en `03-resultados.md` y matriz/capturas en `docs/auditorias/rediseno/02-verificacion-y-capturas.md`.

## Publicación y preservación

El transporte Git devolvió ausencia de credencial y `gh auth status` indicó token inválido. Se utilizó el conector GitHub para publicar árboles completos, comprobando igualdad exacta del SHA del árbol local y remoto. Los commits originales se conservan en las ramas locales `task-cu09-tarifa-cobertura-20261102` de cada submódulo y los checkpoints previos; no se descartaron cambios. Los metadatos de los commits publicados se importaron y verificaron por SHA en el almacén Git local, para que el checkout y los gitlinks apunten a objetos reales publicados.

| Repositorio | Checkpoint local conservado | Checkpoint publicado | Árbol idéntico |
|---|---|---|---|
| Backend CU08 | `00fad6f81b18df51cfa897d6615e3a9c427ba90e` | `2d476ee6a9f1a37a8a1f7e2b14f2f27cb075e715` | `d976eac27af5adfe28d1a678fc6bdee2260d6b81` |
| Backend CU09 | `0392f43b1ec32bf25d0baca9a99cb0ce5a6ba4ba` | `4462a9f70380843ea616fbce5568acd1aa42c89b` | `530262c73cb0e271fafea8b95a5ff51f5f393e5d` |
| Frontend CU08 | `5a9ab7d6d7fef08c66087e9816a063cf3cb608ed` | `fdf1c80445dc5c79f1c56a4db68888d965a9d482` | `63c5faf869458be7127cb155e214883018904f2c` |
| Frontend CU09/diseño | `a23daba` | `1a5a670088a69fbfb3bd7e605c11cb5330d680ac` | `2209ad1063b6241df9119811c1b4b4314f130947` |

PRs: [Backend #46](https://github.com/NexoRuta/NexoRuta-Backend/pull/46), [Frontend #43](https://github.com/NexoRuta/NexoRuta-Frontend/pull/43). Bases de revisión `checkpoint/cu08-verified-20261102`, con contenido CU08 preservado y sin usar main como sustituto. Los submódulos se publicaron antes de los gitlinks del superproyecto. Mobile conserva `5302b2014f547035fdea92167e2333b1bf6395fc`.

La raíz conserva `d3ae05c` y el checkpoint de integración `f423299`. Su base publicada de revisión conserva ese contenido CU08, reemplazando únicamente las referencias locales de submódulos por sus equivalentes publicados y el manifiesto correspondiente. La rama de revisión final integra los gitlinks publicados, contratos, scripts de verificación, trazabilidad y capturas reales.

## Reanudación local

Cargar `scripts/cloud/env-agent.sh`. Infraestructura sintética existente: API5000, Backoffice5101, Commerce5102, Admin5103, Tracking5104. Para reiniciar, detener primero previews con `python3 scripts/cloud/portals.py stop`, después el runtime con `dev.py stop`; arrancar `dev.py start`, luego `portals.py start`. Credenciales sólo en `.local/codex-cloud/private.json`, ignorado. No publicar ese archivo ni los logs privados. Para navegador: `node scripts/cloud/verify-portals.cjs`; para regresiones afectadas: `bash scripts/cloud/check.sh`. No ejecutar verificación del runtime simultáneamente con su reinicio.

El archivo `scripts/cloud/checkpoint.json` es un manifiesto versionado de fuentes, no la configuración publicada del entorno. No se modificó/publicó esta última, ni se hicieron merges automáticos o despliegues. Los pendientes históricos ajenos (revisión nativa, habilitación operativa, Stage y arquitectura previa) conservan su estado documentado.
