# Requisitos operativos de la demo y NFR-14

Este documento describe el contrato vigente en el código del repositorio. La
implementación local de NFR-14 sigue pendiente de validación en `main` y de dos
ensayos reales; esta descripción no es una aceptación de la card.

## Demo persistente

- Proyecto dedicado en `southamerica-west1` (Santiago), con dos VMs `n4-custom-6-16384`
  en las zonas `southamerica-west1-a` y `southamerica-west1-b`. Cada VM tiene
  Hyperdisk Balanced de arranque y datos. La cuota y disponibilidad deben comprobarse
  antes de cualquier nuevo proyecto o cambio de topología.
- Cloud SQL PostgreSQL 18 Enterprise `db-g1-small`, con IP privada y estado
  `ALWAYS`. La configuración observada no tiene backups automáticos ni PITR;
  no tratar la demo como si tuviera recuperación garantizada.
- HTTPS público mediante balanceador global y certificado administrado. El
  certificado debe validarse desde el endpoint; que exista el recurso de IaC no
  acredita HTTPS funcional.
- Compose aloja la API, cuatro portales, workers, RabbitMQ, Kafka, MongoDB,
  Mailpit y observabilidad. Los datos y secretos runtime persisten entre sesiones.
- Las aplicaciones usan Redis con TLS y AUTH en un contenedor del nodo B,
  accesible por la red privada desde A y B. La infraestructura también declara
  `google_redis_instance.cache`, y el inventario del 14/11/2026 observó un
  Memorystore Basic de 1 GiB `READY`. El runtime actual no apunta a Memorystore;
  conservarlo e incluirlo en el inventario/costo hasta una decisión explícita de
  dependencias y retirada.
- Hasta cinco usuarios simultáneos es un objetivo de uso, no una carga ya medida
  ni una garantía de capacidad.

El acuerdo inicial mencionaba un crédito de USD 300 y un horizonte de hasta tres
meses. Saldo, elegibilidad y vencimiento no se verificaron en esta revisión; no
usarlos como presupuesto disponible ni para aprobar una sesión o ensayo.

## Código, CI y publicación

- El repositorio raíz fija Backend, Frontend y Mobile mediante tres gitlinks.
  El conjunto candidato es el commit raíz y esos tres SHA exactos; no reemplazar
  los gitlinks por las puntas actuales de ramas secundarias.
- `ci.yml` valida PRs a `develop` y `main`, ejecuciones manuales y semanales. Las
  PRs a `main` deben venir de `develop`. El job `Integrated CI / result` agrega los
  gates; la protección de `main` requiere ese check y PR.
- CI prueba los gitlinks del commit de la PR y emite evidencia inmutable para la
  integración aprobada. El job de Android y su artifact de verificación son
  evidencia propia; una selección de job o una compilación no equivalen a una
  prueba Android exitosa.
- `publish.yml` solo se dispara al hacer push a `main`. Consume la combinación
  fijada por los gitlinks y la evidencia de CI requerida, crea un tag anotado
  inmutable, publica seis imágenes por digest y el bundle, actualiza el canal
  `main` y crea una prerelease. No vuelve a correr los tests ni enciende VMs.
- Las operaciones sobre VM son `workflow_dispatch` de `vm-controls.yml`. Desde
  `main` consumen la última publicación completa de `main`. Desde `develop`,
  `start`/`update` construyen y publican los gitlinks exactos del commit elegido
  al canal `develop`, sin el gate Integrated CI. Ambos canales son punteros
  separados pero usan las mismas VMs y Cloud SQL.
- Un `update` produce una interrupción deliberada: retira A y B del balanceador,
  detiene las aplicaciones, ejecuta una migración única y admite primero B y
  después A. Los contratos y migraciones deben ser compatibles con esa ventana;
  un fallo puede dejar las apps detenidas y no hay rollback automático de SQL.
- `stop` detiene A y B y conserva Cloud SQL, discos, direcciones, secretos,
  buckets, Memorystore y otros recursos persistentes. El límite de cuatro horas
  gobierna las VMs, no la factura completa.

## Variables, secretos y ambientes de GitHub

- La configuración GCP de publicación y despliegue reside en variables del
  Environment `nexoruta-demo`. Actions se autentica mediante OIDC/WIF con tokens
  temporales; no se guarda una clave JSON de servicio.
- Las variables públicas SMTP viven en `compose.yaml`, bloque
  `x-app-settings`. `SMTP_USERNAME`, `SMTP_PASSWORD` y `GEOAPIFY_API_KEY` son
  opcionales según la integración que se habilite. Si se usa autenticación SMTP,
  se configuran ambos secretos de usuario y contraseña.
- El mapa de Comercio y la geocodificación temporal de la API usan los secretos
  separados `MAPBOX_COMMERCE_PUBLIC_TOKEN` y `MAPBOX_GEOCODING_TOKEN`.
- El inventario de nombres consultado el 14/11/2026 encontró en `nexoruta-demo`
  las variables documentadas y los dos nombres de secretos OAuth de monitor.
  No se observaron secretos SMTP, Geoapify ni de submódulos; no se leyeron valores
  de secretos. No asumir que un secreto opcional está configurado.
- Las PRs usan `nexoruta-ci`, separado de credenciales de despliegue. Solo se
  agrega `SUBMODULES_TOKEN` si los repositorios de componentes requieren lectura
  privada. No duplicar variables/secrets del Environment como configuración de
  repositorio.
- Los ocho `NFR14_REPRO_*` son variables públicas y temporales creadas por el
  orquestador durante cada ensayo aislado. No se cargan manualmente ni contienen
  credenciales. Se eliminan únicamente tras verificar la destrucción del proyecto
  y su presupuesto; ante cleanup incompleto se conservan para inspección/reintento.

## Recreación aislada NFR-14

- `reproduce.yml` solo puede ejecutarse desde `main` y requiere un `run_id` nuevo
  y el tag exacto de una publicación main validada. El orquestador comprueba
  candidato, procedencia, identidades de proyecto y bucket antes de operar.
- El proyecto descartable usa un ID derivado de `run_id`; su proyecto y bucket de
  estado son distintos del proyecto de demo. El bucket de control versionado vive
  además fuera de ambos. El padre de organización/carpeta, billing, presupuesto,
  techo de costo y ventana requieren autorización explícita.
- El límite de cuatro horas de las VMs no limita Cloud SQL, balanceador, IP,
  discos, Redis, builds ni otros recursos. Al terminar el smoke se paran las VMs;
  el proyecto descartable se destruye con un plan guardado revisado y queda
  evidencia fuera del proyecto.
- NFR-14 permanece `In progress` hasta obtener los gates P4–P8. Tests locales,
  validación estática, HTTP histórico o un presupuesto de alertas no sustituyen
  una publicación/costo/recreación observados.

Para configuración exacta de GitHub, consultar [github-environment.md](github-environment.md).
Para operaciones aisladas, consultar el [runbook NFR-14](../../docs/auditorias/nfr-14/runbook.md).
