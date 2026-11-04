# Cloud para agent: preparación versionada

Current source authority: the selected checkout HEAD and its exact gitlinks, not the historical scripts/cloud/checkpoint.json manifest. The installer recursively verifies initialized submodules and never checks out, switches or rewrites sources.

## Source selection is separate from dependency installation

For a new checkout: `git clone --branch develop --recurse-submodules https://github.com/NexoRuta/NexoRuta.git`. In an existing checkout, preserve local work first, explicitly select the requested branch/commit, then run `git submodule update --init --recursive` as a deliberate source-selection step. Run `python3 scripts/cloud/verify-gitlinks.py` before installing dependencies. Never use `--remote` or take current source SHAs from a historical checkpoint manifest.

To reproduce a historical checkpoint, explicitly select its commit/tag in a separate clone before initializing its submodules. `checkpoint.json` remains a historical source inventory, not implicit installation instructions. `install-agent.sh` installs dependencies and restores locks without selecting sources; `environment-install.sh` checks gitlinks first. No published Codex Cloud configuration is changed by this procedure.

Se recuperaron los cuatro archivos efectivos existentes de la adaptación Cloud: dev.py, check.sh, env-agent.sh e install-agent.sh. No son reconstrucciones históricas. environment-install.sh y verify-restart.py son helpers nuevos, escritos para esta publicación. Los contenidos exactos del borrador previo se conservan en cloud-agent-original-install.txt y cloud-agent-original-start.md como archivo histórico; no se ejecutan ni se necesitan para instalar.

Install script exacto:
```bash
cd /workspace/NexoRuta
bash scripts/cloud/environment-install.sh
```

Start skill exacta:
```text
Desde /workspace/NexoRuta, leer AGENTS.md y docs/continuidad/cloud-agent.md. Usar el checkout existente y sus gitlinks; no crear worktrees ni sustituirlos por main. Ejecutar en Bash:
source scripts/cloud/env-agent.sh
python3 scripts/cloud/dev.py start
python3 scripts/cloud/dev.py verify
Para validar: bash scripts/cloud/check.sh y python3 scripts/cloud/verify-restart.py. Si el runtime ya está activo, verificarlo; antes de recompilar, detenerlo con dev.py stop. No depender de procesos vivos de otra tarea. No iniciar CU08/CU09/rediseño sin pedido.
```

Requiere Linux, acceso al daemon Docker local, loopback y red de descarga mediante proxy/CA del entorno. Docker client e info del servidor se comprueban; una denegación del sandbox puede requerir ejecutar la herramienta fuera de él, siempre como agent. No requiere apt, sudo ni cambios de permisos del sistema. Node24.22.2 oficial se comprueba con SHA256, SDK10.0.401, NuGet con locks y Playwright1.62.1/Chromium. El instalador comprueba que Chromium puede ejecutarse con las bibliotecas de la VM; si faltan, falla sin desactivar verificación.

Los scripts no dependen de archivos de esta conversación. Se puede clonar esta rama, inicializar los gitlinks y ejecutar el Install script. Dependencias globales en /workspace/.dotnet y /workspace/.nexoruta-tools pueden reutilizarse, pero el instalador las descarga si faltan. No copiar .local, .env, bases ni claves desde otro checkout.

El runtime crea credenciales aleatorias en .local/codex-cloud/private.json (600, ignorado) y una base Docker exclusiva PostgreSQL18/PostGIS; comprueba etiqueta de propiedad antes de reutilizarla. Migración: cloud_owner. Bootstrap: nexoruta_bootstrap_runtime. API: nexoruta_api_runtime sin superuser, bypassrls, createdb ni createrole. Conserva SQL de roles/RLS/hosting,70 migraciones y seed único contra datos sintéticos. verify comprueba login, tres GET autenticados, conexiones del rol API y tablas con RLS forzado. Si el snapshot conserva archivos pero no contenedor, recrea esquema y bootstrap; no promete conservar datos Docker fuera del snapshot. No borrar contenedores/volúmenes para reiniciar.

Puertos: PostgreSQL15432, API5000, Backoffice5101, Commerce5102. Solo ejecutar un runtime a la vez: para comprobar desde otro clon detener el propio primero, conservando su base y archivos. Stop verifica identidades. Los procesos deben arrancar en cada tarea nueva.

check.sh, con env-agent.sh, usa fixtures Docker propias y conserva aserciones: HTTP5, fullstack1, frontend/Chromium9, Mobile Core3 y Node3. HTTP y fullstack separados. El selector fullstack prueba selección, ajuste, guardado, reapertura y conflicto con PostgreSQL real/RLS. Mapbox permanent=false; SDK/HTTP controlados y solicitudes externas bloqueadas. Sin tokens ni consumo Mapbox/Geoapify. Mobile utiliza lock portátil en obj sin reescribir el Android versionado.

verify-restart.py verifica login y huellas de filas persistidas/estado privado antes y después de stop/start. No imprime filas, contraseñas ni claves. Logs, bases, imágenes y capturas son locales, no fuentes de preparación ni artefactos Git. No se accede a Windows ni a sus bases. No se publica el entorno automáticamente.

Para validar otro clon sin reutilizar el contenedor del checkout anterior, detener el runtime anterior y exportar NEXORUTA_CLOUD_CONTAINER con un nombre nuevo exclusivo antes de start/check/verify-restart. No copiar private.json. Esta variable debe mantenerse para todas las operaciones de ese clon.

## Investigación posterior de sesión (03/11/2026)

[Diagnóstico y reproducción](../auditorias/sesion-401/01-diagnostico-y-verificacion.md): respuesta 401 demorada que invalidaba un ingreso posterior. El origen del 401 histórico de arranque sigue sin determinar. El harness optativo ejecuta portales reales, API Kestrel y PostgreSQL aislado; no requiere ni usa los datos de la prueba manual Mobile. Mantener HTTP y navegador en invocaciones separadas, y no recompilar DLLs mientras los portales del harness las están usando. No se cierran CU pendientes por este corte.
