# CU08 — verificación Cloud

Ejecutado el 2 de noviembre de 2026 sobre el checkpoint requerido y los gitlinks originales, con helpers versionados, Docker como agent y datos sintéticos. No se modificó ni publicó la configuración del entorno.

| Comprobación | Resultado |
|---|---|
| Instalación `environment-install.sh` | SDK/Node con locks, Chromium ejecutable, imagen PostgreSQL18/PostGIS disponible |
| `dev.py start` / `verify` | API/Backoffice/Commerce activos; login y tres GET autenticados 200; rol API sin superusuario/bypass RLS; tablas FORCE RLS; 70 migraciones |
| Backend unitarias | 298 aprobadas, incluye colección completa/vacía, códigos repetidos y precisión |
| Persistencia/importación/validación existentes | 41 aprobadas |
| Nuevas pruebas HTTP `MultiParcel` | 2 aprobadas tras recompilación completa; alta y CSV con dos bultos, invalidación atómica y reimportación reordenada |
| Cliente de envíos y doble envío | 30 aprobadas |
| Contratos OpenAPI | Exportación desde API real 1 aprobada; comparación frontend 55 aprobadas |
| Selector HTTP | 5 aprobadas |
| Selector fullstack | 1 aprobada con PostgreSQL/RLS; selección, ajuste, dirección/coordenadas, guardar, reabrir y conflicto |
| Selector frontend/Chromium | 9 aprobadas |
| Mobile Core cierre | 3 aprobadas |
| Mapbox Node | 3 aprobadas, `permanent=false`, sin geocodificación desde SDK ni fallback externo |
| Chromium CU08 | Agregar/quitar bultos a 1440 y 320 px; sin desbordamiento horizontal general; solicitudes externas bloqueadas; capturas inspeccionadas |

Fuentes de pruebas nuevas: `backend/tests/NexoRuta.UnitTests/Envios/CrearEnvioUseCaseTests.cs`, `backend/tests/NexoRuta.IntegrationTests/Envios/ShipmentCsvImportHttpTests.cs`; reproducción visual con `source scripts/cloud/env-agent.sh` y `node scripts/cloud/verify-cu08.cjs`. Capturas y credenciales permanecen ignoradas en `.local`.

La exportación real reveló que la búsqueda publicaba un esquema distinto del snapshot anterior: se trasladaron sus validaciones al DTO de propiedades para que OpenAPI conserve minLength=3/maxLength=240. Las pruebas resuelven `$ref` y colecciones `List<>` sin debilitar las aserciones.

Los primeros intentos de verificación detectaron fallos del contrato anterior y un binario incremental que no descubría las pruebas nuevas. No se acreditan como aprobados. Los resultados de la tabla corresponden a las ejecuciones posteriores identificadas.

## Evaluación

El cierre de `740e3df` se reabrió al comprobar que las dos pruebas multibulto usaban la conexión propietaria de la fixture. Se corrigió la admisión para insertar la colección completa en la función SECURITY DEFINER, sin conceder INSERT al rol API. Las dos pruebas HTTP multibulto con conexión restringida pasaron; también pasó la prueba SQL directa de admisión con su contexto de acceso completo. Las restantes 37 pruebas de persistencia/importación/correo pasaron. Se repitió `check.sh` completo tras la migración: HTTP5, fullstack1, frontend9, mobile3 y Node3 aprobados; runtime autenticado verificado con 71 migraciones. CU08 queda cerrado técnicamente sobre esta corrección, que reemplaza la conclusión prematura del primer checkpoint. Los lectores de reparto, capacidad, Backoffice y mobile consumen colecciones; no requieren un contrato alternativo. No se declara cierre de CU09, CU06, habilitación operativa ni de todo el producto. Se mantienen los pendientes históricos documentados.

La revisión visual detectó problemas preexistentes de composición del shell (navegación y enlace de salto), a abordar durante el rediseño solicitado; no se toma la compilación como revisión visual ni se certifica WCAG global.
