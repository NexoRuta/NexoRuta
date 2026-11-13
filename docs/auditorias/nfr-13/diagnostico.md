# NFR-13 — Diagnóstico de implementación

Fecha: 12/11/2026. Este diagnóstico resume el análisis del plan y los cambios locales preparados; no es evidencia de aceptación en GCP.

## Brechas confirmadas por el código

1. La API exponía `/health/ready` y `/health/live`, sin la tripleta `/health`, `/ready`, `/live`. El check PostgreSQL no tenía un timeout de registro explícito y las respuestas no tenían un escritor público que limitara los campos.
2. Los cuatro portales registraban `/health/ready` solamente. Scripts, Compose, IaC, sondas de desarrollo, mobile y verificadores consumían las rutas antiguas.
3. La función efectiva de vencimientos se redefine por última vez en `ParcelResultsAndHomePickups.Sql.cs`. Su búsqueda elige envíos antes de tomar el lock y, tras la espera, actualiza la versión del envío parcial aunque otro actor haya resuelto ya el bulto. El worker recibía solo un entero, así que no podía distinguir trabajo completado, contención y cooldown.
4. El worker periódico se registra en los transportes RabbitMQ, Kafka y Push; con dos nodos hay varios procesos que pueden intentar el mismo tick. No había lock distribuido ni fila de cooldown para este job.
5. El host no fijaba un presupuesto de apagado propio. Compose ya tenía 30 s para aplicaciones de GCP y entrega esperaba 35 s; faltaba alinear ese margen con el host y observar si alcanza.
6. Backoffice utiliza componentes interactivos de servidor, pero su configuración GCP no tenía afinidad cookie. Commerce ya la tenía. La afinidad ayuda a la negociación/circuito activo y no sustituye la reconstrucción del circuito tras perder el nodo.

## Respuesta implementada

- Salud separada en liveness independiente y readiness con SQL y almacén compartido de claves (cuando está configurado), cada uno con límite de 2 s; API y portales de producción requieren almacenamiento compartido. Estado de ciclo de vida impide admitir durante arranque/drenaje; JSON mínimo sin detalles de excepciones.
- Migración que cambia el resultado SQL, protege la coordinación con `pg_try_advisory_xact_lock` transaccional y un cooldown de 30 s medido por el reloj PostgreSQL. `MoreWork` permite drenar lotes completos inmediatamente.
- Relectura del estado después del `FOR UPDATE` por envío; actualizaciones y avance de coordinación en una transacción; tabla técnica con RLS forzado y acceso del rol definer únicamente.
- Métricas de intentos, duración, filas afectadas, continuación y frescura de última finalización, sin IDs de negocio.
- Host 20 s, Docker 30 s, LB 30 s y espera de entrega existente 35 s. Los ensayos locales de SIGTERM de API y worker terminaron dentro de 30 s; la validación en GCP sigue pendiente.
- Probes y documentos operativos actuales apuntan a rutas nuevas; rutas históricas de auditoría se conservan sin reescritura.

## Límites del diagnóstico

El gitlink raíz frontend (`723d02b`) y el checkout local frontend (`162bf08`) divergen. Los cambios de portal también se aplicaron y compilaron en un checkout aislado basado en el gitlink, donde pasaron las pruebas de contrato OpenAPI; no se actualizó el gitlink ni se calificó el conjunto como release candidata.

Las migraciones y pruebas focalizadas se ejecutaron con PostgreSQL/PostGIS en Docker sobre WSL; la matriz local completa sigue pendiente. No se provocaron fallos en GCP, no se ejecutó carga, no hubo `tofu apply`, despliegue, observación HTTP remota ni revisión de navegador. Los estados de aceptación y gates están en [aceptacion.md](aceptacion.md).
