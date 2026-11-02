# Estado de la tarea Cloud: CU08 implementado; CU09 y rediseño pendientes

Se obtuvo `NexoRuta/NexoRuta`, rama `checkpoint/codex-cloud-agent-20261102`, y se comprobó que su punta era el commit inicial solicitado `8991321593f9092e18aac83d6a9a11df4c388cb3`. Se respetaron sus tres gitlinks y se partió de árboles limpios. Los repositorios hermanos publicados anteriormente no se utilizaron como sustitutos. No se modificó ni publicó la configuración del entorno.

## Checkpoints

- Raíz `740e3df`: primera implementación CU08 y trazabilidad. Su cierre fue reabierto al detectar que las pruebas multibulto nuevas utilizaban la conexión propietaria de la fixture.
- Backend `00fad6f`: corrige la admisión completa en función SECURITY DEFINER; no concede INSERT directo de bultos al rol API. Añade migración `20261102020000_AdmitMultipleParcels`, con firma única de creación JSON; conserva los datos existentes.
- Frontend `5a9ab7d`: contrato, formulario agregar/quitar, CSV multibulto y OpenAPI generado.
- Raíz `772c467`: checkpoint CU08 corregido, con verificación multibulto bajo rol restringido. Ver `docs/auditorias/cu08/01-requisitos-y-trazabilidad.md` y `02-verificacion.md`.
- Mobile conserva `5302b2014f547035fdea92167e2333b1bf6395fc` sin cambios funcionales.

`scripts/cloud/checkpoint.json` identifica los gitlinks revisados del checkpoint de trabajo. El commit inicial requerido queda registrado por separado; no se sustituye por main. Las ramas de trabajo son locales, sin merge, despliegue ni publicación de configuración.

## Preparación y verificación

Se ejecutaron `environment-install.sh`, `env-agent.sh`, `dev.py start/verify` y `check.sh`. Se usó el permiso de red admitido por la herramienta para Git, descargas y Docker. Sin apt ni sudo. Node y SDK fijados por los helpers, Chromium ejecutable y PostgreSQL18/PostGIS reales en Docker. La API usa un rol sin superusuario ni bypassrls; se comprobó FORCE RLS, login y tres GET autenticados. Tras CU08 hay 71 migraciones.

La regresión obligatoria posterior a la corrección SQL pasó: destinos HTTP5, selector fullstack1, frontend/Chromium9, mobile Core3 y Node3. Se verificaron selección, ajuste, dirección/coordenadas guardadas, reapertura y conflicto. Se conserva `permanent=false`; proveedores simulados y sin consumo externo. CU08 también se revisó visualmente a 1440 y 320 px, sin desbordamiento horizontal general.

No se acredita una batería global completa de arquitectura ni una certificación WCAG. Se mantienen los pendientes B1–B5 y CU06 documentados previamente.

## CU09: auditoría y trabajo no integrado

Fuentes oficiales: PDF 5.2 numeral9 (tarifa automática al alta), PDF6.6 (versionado/tratamiento original), XLSM CU obligatorios A12:I12 y dependencias D02/D22. Deben reutilizarse `CalculadoraTarifas`, `TarifariosOperador`, `VersionesTarifario`, `TarifasZonaModalidad`, `AjustesTarifario` y `ZonasCobertura`.

El alta actual solo declara dirección textual; no contiene ubicación ni zona/modalidad para seleccionar una tarifa inequívoca. La simulación tarifaria existente no satisface CU09: no se aplica ni conserva un cargo durante el alta. Las consultas existentes de cobertura/tarifas son de operador; no basta con exponerlas al comercio sin revisar RLS.

Se exploró un contrato explícito de servicio (zona, coordenadas y modalidad), oferta geográfica con PostGIS, snapshots inmutables de tarifa y validación de cambios de destino contra la publicación original. El borrador no está integrado ni verificado y no se considera implementación aceptada. Se conserva localmente, ignorado, en `.local/codex-cloud/cu09-wip/`, incluidos parches y fuentes de la segunda revisión. No aplicarlo sin completar consumidores, fixtures, revisión de aislamiento y pruebas.

Falta implementar y verificar: alta individual y CSV; rechazo HTTP directo de Rivera cuando el operador no cubre el destino; publicación vigente, pesos/volúmenes de todos los bultos y ajustes; rollback de lotes con un destino no cubierto; conservación de cargos/versiones ante publicaciones posteriores; cambios de destino y operador según el alcance real de las APIs. No hay precios ni cobertura nuevos en las fuentes activas.

## Rediseño pendiente

No se realizó la unificación general solicitada. Se leyó `frontend/DESIGN.md` y se mantuvieron stack y componentes existentes. La fuente compartida continúa siendo `frontend/shared/portal-design.css`.

Las capturas de CU08 muestran oportunidades pendientes de composición: shell/navegación y enlace de salto, excesiva longitud de formularios en escritorio, jerarquía de acciones y errores. El rediseño debe abarcar los portales y comprobar teclado, foco, feedback, reflujo320 y escritorio en Chromium, preservando rutas, permisos, antiforgery, B1–B5 y selector. No se debe inferir su cumplimiento de las pruebas del formulario multibulto.
