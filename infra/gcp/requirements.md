# Requisitos acordados para la demo

- GCP con crédito de USD 300 y horizonte de hasta tres meses, cerrando el proyecto
  antes de que expire. Evitar cómputo permanente; conservar datos entre sesiones.
- Hasta cinco usuarios simultáneos. VM de **16 GiB**, priorizando CPU y tiempos de
  respuesta. No dimensionar a 32 GiB sin mediciones que lo justifiquen.
- Cercanía a Uruguay: Santiago elegido tras comparar HTTP desde el equipo local.
  Servicios de aplicación/datos/build en `southamerica-west1`. Scheduler usa
  São Paulo porque no existe en Santiago; solo realiza control de apagado.
- N4 highcpu de ocho vCPU conserva 16 GiB; SQL tiene sus propios 2 vCPU/8 GiB.
  Comprobar cuotas de la cuenta de prueba antes de crear recursos.
- Infraestructura declarada con OpenTofu; operación desde PowerShell y CLIs.
- Repo madre en `main`; el despliegue toma lo último de `main` de backend,
  frontend y mobile. Los checkouts locales pueden permanecer en `develop`.
  Resolver SHAs una vez y construir únicamente esos commits probados.
- CI/CD integral: pruebas, imágenes, infraestructura, PostgreSQL/PostGIS y RLS,
  migraciones, datos iniciales, API, cuatro webs, workers Rabbit/Kafka/Push,
  RabbitMQ, Kafka, MongoDB, correo de prueba, HTTPS y APK.
- El inicio de una nueva sesión es manual y dura cuatro horas desde el arranque
  de la VM. Las actualizaciones de código no deben reiniciar ni ampliar la sesión.
- Un push a `main` solo ejecuta CI y publica imágenes; no opera la VM, ni siquiera
  cuando está encendida. El botón manual `update` usa la última release completa
  del registry, descarga sus imágenes y recrea los contenedores sin recompilar.
- Apagar Cloud SQL junto con la VM, incluso ante cancelación/fallo del runner.
  Mantener backups, claves, contraseñas, datos y volúmenes entre sesiones.
- Autenticación de GitHub mediante WIF, sin claves JSON permanentes de GCP.
  Variables GCP y secrets externos en el environment de GitHub `nexoruta-demo`,
  sin duplicar variables del proyecto a nivel del repositorio. Configuración
  no secreta de aplicaciones en `compose.yaml`, bloque `x-app-settings`. Secrets de PR
  separados en `nexoruta-ci`.
  Los permisos iniciales, OAuth y credenciales externas requieren la cuenta real.
- Probar HTTPS, salud y acceso a PostgreSQL antes de declarar un deploy saludable.
  Validación estática/mocks no acredita despliegue real ni rendimiento medido.
