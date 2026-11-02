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

Pendiente de ejecutar tras el primer commit raíz; el resultado observado se agrega aquí antes de entregar. No se atribuye aprobación nativa ni validación vial a las respuestas controladas.

## Límites

No hay entorno Codex Cloud adjunto a esta sesión. Falta conectar/publicar desde su interfaz y comprobar allí apt/sudo/procesos, red de instalación y permisos de los cuatro repositorios. La prueba Linux local sin Docker no acredita una VM Cloud que no se ha abierto.

Revisión nativa, habilitación operativa, artefacto Stage y fallo arquitectónico previo permanecen como indica codex-cloud.md. Los servicios habituales no se detuvieron ni se migraron durante esta preparación.
