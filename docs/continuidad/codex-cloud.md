> Preparación actual: usar el checkout solicitado y sus gitlinks; ver [procedimiento vigente](cloud-agent.md). Las referencias de checkpoint siguientes documentan una reproducción histórica explícita, no seleccionan fuentes durante la instalación.

# Continuar NexoRuta en Codex Cloud

Para la preparación versionada de **agent con Docker**, usar [Cloud para agent](cloud-agent.md). Sus helpers publicados sustituyen el borrador de onboarding; las instrucciones nativas siguientes se conservan como procedimiento alternativo.

Checkpoint del estado local B1–B5, selector persistido y mobile, del 02/11/2026. Próximo objetivo: **CU08 → CU09 → rediseño**, en ese orden. Esta preparación no implementa esas etapas. Leer AGENTS.md, frontend/DESIGN.md, docs/alcance y las especificaciones antes de cambiar comportamiento.

## 1. Repositorios y checkout

Rama en los cuatro repositorios: `checkpoint/codex-cloud-20261102`. [URLs y SHAs exactos de los submódulos](../../scripts/cloud/checkpoint.json). Backend tiene el checkpoint funcional846e79c y el posterior5bd165c de fixture Dockerless; frontend904af71; mobile5302b20. El SHA raíz se obtiene con `git rev-parse HEAD` tras seleccionar esta rama: no puede contenerse a sí mismo en su commit.

```bash
git clone --branch checkpoint/codex-cloud-20261102 https://github.com/NexoRuta/NexoRuta.git
cd NexoRuta
git submodule update --init --recursive
git submodule status
```

Los hijos se publican antes de la raíz. No usar `submodule update --remote` ni otras puntas de rama para sustituir los gitlinks. Conectar los cuatro repositorios a Cloud y conceder acceso GitHub para sus submódulos privados. Si Cloud los coloca como hermanos, materializar los hijos en backend/, frontend/, mobile/ con los SHA de los gitlinks del checkout seleccionado (no los de un manifiesto histórico). No transferir tokens, Git Credential Manager, .env ni credenciales de Windows.

## 2. Instalación y servicios sin Docker

La [documentación oficial de Cloud environments](https://learn.chatgpt.com/docs/environments/cloud-environments) describe repositorios, **Install script** y **Start skill**. Configurar esos campos, probar y publicar el entorno desde Cloud. Esta sesión no tiene una VM Cloud adjunta ni herramienta para configurar/publicar ese entorno; no se afirma haberlo hecho. Docker no se presupone ni se necesita en el camino siguiente.

Requisitos: Linux Debian/Ubuntu, apt y root/sudo, procesos en segundo plano y loopback/TCP local, espacio para .NET y Chromium. Se ensayó en Ubuntu24.04 x86_64 **sin Docker CLI ni socket dentro del entorno de prueba**. Si Cloud no concede esas capacidades, registrar el bloqueo: no apuntar a Windows o una base externa como sustituto.

**Install script:**
```bash
bash scripts/cloud/install.sh
```

Instala .NET SDK **10.0.401**, rollForward=disable según los cuatro global.json; PostgreSQL18/PostGIS real; Node24.22.2, tar oficial verificado por SHA256; Playwright1.62.1/Chromium fijado por package-lock; NuGet de API/tests/portales/mobile Core. Razor/Blazor no necesita otro build npm de aplicación: el nuevo npm solo instala herramientas de prueba.

Red de instalación: permitir los repositorios apt Debian/Ubuntu, apt.postgresql.org, www.postgresql.org (clave PGDG), dot.net/builds.dotnet.microsoft.com, nodejs.org, registry.npmjs.org, api.nuget.org/globalcdn.nuget.org y los CDN de Playwright (cdn.playwright.dev y playwright.download.prss.microsoft.com, incluidos redirects necesarios). Mantener Mapbox/Geoapify fuera de las pruebas. La disponibilidad de esas descargas se comprueba en el setup del entorno, no se deduce de tener un repositorio conectado. En el ensayo .NET ya estaba instalado con la versión exacta; no se ejecutó la rama que descarga un SDK ausente.

**Start skill / cada tarea nueva:**
```bash
export DOTNET_ROOT="${DOTNET_ROOT:-$HOME/.dotnet}"
export PATH="$DOTNET_ROOT:$PATH"
python3 scripts/cloud/dev.py start
python3 scripts/cloud/dev.py verify
```

Crea un clúster privado en `.local/codex-cloud/postgres`, puerto15432 de **la VM Cloud**, no del Windows del usuario. Base `nexoruta_cloud_<aleatorio>` con marcador de propiedad; no acepta conexiones operativas ni restaura dumps. Genera claves/credenciales exclusivas en `.local/codex-cloud/private.json` (600, ignorado), cuentas distintas admin/operator/commerce@cloud.example.test y dos organizaciones sintéticas. Consultar ese archivo privado para entrar; nunca publicarlo ni copiar credenciales a logs.

Migra solo esa base propia. Usa los roles existentes de `backend/scripts/provision-rls-runtime-roles.sql`, bootstrap restringido y el bloque de límites de `deploy/gcp/sql/hosting.sql`. API usa `nexoruta_api_runtime` NOSUPERUSER/NOBYPASSRLS/NOCREATEDB/NOCREATEROLE, no el usuario que migra. El bootstrap genera `administrador_operador` protegido y permisos del catálogo, evitando repetir el403 del antiguo código propietario_operador. Migraciones/seeds automáticos false. Se conserva el limitador HTTP PostgreSQL: el ensayo detectó503 por falta de nexoruta_hosting y se corrigió provisionando su contrato existente, no debilitando el límite.

Arranca API5000, Backoffice5101 y Commerce5102 desde DLLs compiladas en salida exclusiva, **sin watch/Hot Reload**. Usar los previews de puertos proporcionados por Cloud. Loopback comunica procesos de esa VM y nunca depende del equipo del usuario. Backoffice: Envíos en `/` (no `/envios`), vehículos `/vehiculos`, rutas `/rutas`; Commerce `/envios`.

Para recompilar, detener primero los procesos propios; no reescribir DLLs cargadas:
```bash
python3 scripts/cloud/dev.py stop
python3 scripts/cloud/dev.py start
```
Stop verifica PID/identidad y conserva los datos. El bootstrap queda marcado: reiniciar no resetea cuentas. Este procedimiento no toca servicios del taller.

## 3. Comprobaciones

```bash
bash scripts/cloud/check.sh
```

- `NEXORUTA_TEST_POSTGRES_MODE=native`: cada fixture crea su propio initdb clúster PostgreSQL18 temporal, puerto y credenciales aleatorios. No acepta ConnectionStrings externos ni usa la base de desarrollo Cloud. Mismas migraciones, roles RLS y aserciones; Docker permanece como predeterminado para quien lo tenga.
- Ejecuta HTTP destinos5; selector fullstack1 (Commerce→API→PostgreSQL restringido); frontend9; mobile cierre3; Node3. SDK y transporte Mapbox controlados, sin consumo externo. Incluye selección, ajuste, persistencia, reapertura y conflicto de versión.
- HTTP y fullstack en invocaciones separadas: una ejecución combinada Linux devolvió401 durante la sesión del browser; las aisladas pasaron. Es una limitación observada del harness, no evidencia para cambiar autorización/RLS del producto. Mantener esa secuencia para reproducir.
- Mobile Core tiene un lock compartido con un RID android-x64 del desarrollo MAUI. El restore portátil usa `-p:NuGetLockFilePath=obj/cloud.packages.lock.json` y el test `--no-restore`, conservando el lock Android versionado sin reescribirlo. No se agrega workload Android para probar Core. Se comprobó el árbol limpio después de esta variante.
- `verify` exige login real Cloud y GET200 de envíos/flota/perfiles-viales, PostGIS y rol API sin privilegios globales. Regresión del modo Docker: una prueba HTTP restringida pasó aparte en Windows.
- El operador recién creado no tiene rutas ni envíos inventados; el listado puede estar vacío. Configurar reglas operativas mediante la pantalla/API existente antes de admitir envíos. Las fixtures publican las reglas sintéticas que necesitan.

Mapbox conserva `permanent=false`, búsqueda explícita/debounce/cancelación/cuotas y selección→ajuste→confirmación→dirección/coordenadas guardadas→reapertura. Cloud arranca sin token Mapbox y llamadas reales false; Geoapify geocodificación/routing apagados. El flujo se verifica con respuestas controladas; no se habilita consumo externo ni se acredita precisión vial.

## 4. Migraciones y transición

70 migraciones al preparar el checkpoint. Dependencias recientes:

| Orden | Migración | Alcance |
|---|---|---|
|1|20261101184716_StageFleetOccupations|Stage es una etapa de esquema/transición, no un ambiente de despliegue|
|2|20261101185119_EnforceFleetOccupationExclusivity|Exclusión sin filtro por fecha; conciliar legados antes|
|3|20261101203256_AddOperationalBaseAndTemporalPlan|B3 base y snapshots temporales|
|4|20261101213104_AddRoadEstimationHistory|Histórico B4/B5|
|5|20261102000000_LimitGeocodingConsumption|Cuota PostgreSQL compartida|
|6|20261102010000_ConfirmSelectedDestinationAddress|Texto/coordenadas/versionado atómicos|

La base Cloud vacía puede migrar hasta70 antes de sembrar: no hay legados que conciliar. Esto **no** autoriza database-migrate sobre una base Stage/del taller con datos anteriores. Para ella rigen14-ensayo-transicion.md y15-activacion-local-b1-b5.md: detener escritores, respaldo, Stage, conciliación, Enforce y posteriores. No reconstruir versiones históricas eliminando cambios. Un artefacto B2 compatible con Stage sigue siendo requisito para futuras conciliaciones: este checkpoint no acredita por sí solo un artefacto Stage publicado. No se transfieren binarios ni respaldos DPAPI. No se inventan retornos o constataciones físicas.

## 5. Continuidad y límites

- B1 capacidad/precisión; B2 ocupación exclusiva, cierre separado de retorno/liberación y custodia; B3 base/tiempos; B4 Geoapify estático y manuales paralelos; B5 proyección explícita desde GPS admisible. Preservar snapshots, idempotencia y aislamiento.
- B2 técnicamente verificado conforme a08-aceptacion-funcional-aislada-b2.md: no reabrir por rutina.
- Revisión nativa pendiente: external.select_intended_untracked no expuesta. No cambiar preferencias ni fabricar aprobación.
- Habilitación operativa y precisión vial en Uruguay pendientes. ETA/GPS no liberan recursos ni reciben carga. CU06 no está cerrado.
- Fallo arquitectónico previo esperado2/actual7, documentado en B1, no corregido/debilitado. Advertencias NU1510/CS8629/BL0005 existentes.
- BadImageFormatException de Backoffice dejó de reproducirse tras reinicio; causalidad de Hot Reload no demostrada. Cloud no recompila sobre procesos activos.
- El arranque mínimo no levanta Kafka/RabbitMQ workers, Mongo, Tracking público, SMTP o Android/MAUI; no acredita esos flujos. Resolver sus servicios documentados cuando CU09 lo requiera, sin fingir entregas externas.
- Capturas/logs, binarios, respaldos y estado privado quedan localmente, excluidos del checkpoint. Enlaces históricos a evidencias locales pueden no existir en Cloud; fuentes de tests/fixtures y procedimientos sí se incluyen. No confundir reportes históricos con nuevas ejecuciones.
- Engram sin identidad runtime registrada: continuidad en Git/documentos, sin afirmar escritura atribuida de memoria.

## 6. Publicación y copia limpia

Se preservaron los árboles originales en carpeta privada y se crearon ramas de checkpoint, sin tocar ramas protegidas ni sustituir gitlinks. .env no se publica; .env.example tiene placeholders y appsettings.Development ya no contiene contraseña de conexión utilizable. Sin merge, force-push o despliegue remoto.

La verificación final usa clone limpio separado con gitlinks exactos, sin .env, bin/obj, node_modules, .local ni respaldos del checkout habitual. Resultado en `verificacion-checkpoint.md`. Publicar los repositorios no crea automáticamente un entorno Codex Cloud: conectar repositorios, configurar red/instalación y publicar el entorno requiere la capacidad Cloud del usuario.

Risk: items2/4/5 (bootstrap privado, ciclo de fixtures/procesos y preparación de entorno); sin cambio funcional B1–B5.
