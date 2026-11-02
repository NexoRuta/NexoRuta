# Verificación del checkpoint Cloud

02/11/2026. Ensayo local aislado, no una publicación del entorno Codex Cloud.

## Preparación observada

- Inventario inicial: raíz276 archivos modificados/nuevos (incluida evidencia local), backend117, frontend52, mobile2. Captura y copias privadas previas a cualquier edición; se conserva todo el trabajo anterior.
- Se excluyen evidencias locales/logs/capturas, .env, binarios, backups y estado privado. Las credenciales Cloud se generan nuevas y no usan valores del taller. El ejemplo de entorno queda con placeholders.
- Submódulos publicados primero en sus ramas checkpoint/codex-cloud-20261102, con gitlinks exactos en el manifiesto; sin merge/force-push/despliegue.
- Instalación ensayada en Linux Ubuntu24.04 dentro de aislamiento local, sin Docker CLI/socket disponibles al runner: SDK10.0.401, Node24.22.2, PostgreSQL18.6/PostGIS3.7.0, Chromium151 de Playwright1.62.1.

## Pruebas ejecutadas antes de clonar

| Comprobación | Observado |
|---|---|
|Fixture anterior sin Docker|5 fallos DockerUnavailableException; evidencia RED de la dependencia que impedía Cloud|
|Fixture nativa con mismo HTTP/RLS|5/5 correctas|
|Selector fullstack nativo, invocación separada|1/1 correcta: selección/ajuste/guardado/reapertura/conflicto, HTTP y SDK controlados|
|Frontend componente/APIClient/Chromium|9/9 correctas|
|Mobile Core cierre|3/3 correctas, además de3/3 en Windows|
|JS selector/permanente/teclado|3/3 correctas|
|Fixture Docker original, regresión Windows|1/1 HTTP restringida correcta|
|Arranque native Cloud + reinicio propio|Correcto;70 migraciones y mismos datos/cuentas al reiniciar|
|API real del runtime nuevo|Login y GET envíos/flota/perfiles-viales200; rol API no superuser/no bypass RLS|

Correcciones del setup durante el ensayo: Node18 de Ubuntu no satisface Playwright, por eso se fijó Node24.22.2; el limitador HTTP necesita nexoruta_hosting, por eso se reutiliza su bloque SQL existente. El ensayo combinado HTTP+fullstack devolvió401 en browser; el procedimiento definitivo los separa y ambos pasan. No se cambia producto/autorización para ocultarlo.

## Copia limpia final

Ejecutada desde clones Git locales separados en `/clean`, sin .env, bin/obj, .local, node_modules ni respaldos del checkout habitual. Base de código raíz `8157ffeb51856aebe9db5731ce983f58b82858f9`; hijos5bd165c/904af71/5302b20 coincidentes con los gitlinks publicados. Los clones no requirieron ninguna credencial Windows para ejecutar la aplicación; se usó un clúster nativo nuevo y otras credenciales aleatorias.

Install y start correctos. Pruebas limpias: HTTP5/5, fullstack1/1, frontend9/9, mobile3/3, Node3/3; login y los tres GET200,70 migraciones y rol API restringido. Las capturas Chromium reales de los tests cubren320px y escritorio con SDK/HTTP simulados; no se validan mapas ni tiempos viales reales.

La primera restauración de mobile Core reescribió su lock por el RID android-x64 preexistente. `--locked-mode` confirmó NU1004; se resolvió exclusivamente en los scripts Cloud mediante lock portátil en obj/ y test sin nuevo restore. Esa variante pasó3/3 y dejó `git status --porcelain` vacío en raíz y submódulos; el lock Android original no cambia. Los cambios posteriores al commit de código probado son esa configuración de restore verificada aparte y documentación/normalización de saltos CR duplicados en dos auditorías nuevas, sin alterar su contenido.

Las ramas remotas de los tres hijos fueron comprobadas con ls-remote y sus SHAs completos coinciden con checkpoint.json. El commit raíz final registra el resultado y los mismos gitlinks; se verifica también su checkout y publicación antes de entregar. No se atribuye aprobación nativa ni validación vial a respuestas controladas.

Entorno habitual Windows: API y portales permanecen arriba; login/GET200 de usuario/permisos/envíos/flota verificados, y Chromium con sesión nueva muestra10 filas y destino persistido versión3 al reabrir. Un primer intento del browser encontró sesión expirada; renovar la sesión en una ejecución nueva pasó sin cambiar datos ni políticas. No se hizo una auditoría de ese transitorio ni se lo atribuye a Cloud.

## Límites

No hay entorno Codex Cloud adjunto a esta sesión. Falta conectar/publicar desde su interfaz y comprobar allí apt/sudo/procesos, red de instalación y permisos de los cuatro repositorios. La prueba Linux local sin Docker no acredita una VM Cloud que no se ha abierto.

Revisión nativa, habilitación operativa, artefacto Stage y fallo arquitectónico previo permanecen como indica codex-cloud.md. Los servicios habituales no se detuvieron ni se migraron durante esta preparación.
