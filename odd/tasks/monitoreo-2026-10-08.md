# Monitoreo NexoRuta 08/10/2026

## Objetivo

Demostrar en el entorno local Compose el alta individual de un envío en el portal, su persistencia en PostgreSQL con operador/comercio/usuario de prueba y bulto, su consulta en Backoffice y una ejecución local de CI.

## Alcance y restricciones

- Fuentes rectoras: `docs/alcance/Monitoreo_2026-10-08_CU.xlsx`, `docs/alcance/Laboratorio__NET_2026.pdf`, `docs/alcance/Entregas/Entrega-10-4-2026-Grupo-4.pdf`, `architecture.md` y `backend/docs/workflow/arquitectura-backend.md`.
- Implementar CU-01 solo como relaciones/datos de demo; CU-07 solo alta individual; CU-08 un bulto o más; T-01 entorno Compose con base, caché, cola y observabilidad; T-02 lectura en Backoffice del mismo envío; T-03 pipeline CI localmente verificable.
- No adelantar autenticación, perfiles completos, RLS/dos operadores, tarifas CU-09, máquina de estados completa, cache funcional, cola funcional, móvil, despliegue remoto ni otros hitos.
- Mantener README, `architecture.md` y `docs/` existentes. No commit ni push; todo cambio de código queda en ramas `feature/monitoreo-2026-10-08` de los repositorios editados.

## Tareas

- [x] M01 — Persistir entidades mínimas de operador/comercio/usuario y crear envíos/bultos por API usando EF Core, PostgreSQL y migración; pruebas de dominio e integración.
- [x] M02 — Completar el portal de comercio para el alta individual y Backoffice para consultar el registro persistido, demostrando el mismo ID de extremo a extremo.
- [x] M03 — Completar Compose con health/observabilidad requeridos por el hito y agregar workflow CI de compilación/pruebas; validar comandos localmente y demo Compose.

## Verificación y estado

- Resultado esperado: los casos CU-01, CU-07, CU-08 y condiciones T-01/T-02/T-03 quedan reproducibles con evidencia local; la CI remota no se considera ejecutada ni publicada.
- Ruta de implementación: directa en línea, por instrucción explícita del usuario de no delegar.
- Evidencia: `dotnet test NexoRuta.sln --configuration Release` pasó con 2 unitarias y 1 integración contra PostgreSQL efímero limpio; las compilaciones Release de backend/frontend pasaron; `docker compose config --quiet`, `docker compose build`, `docker compose up -d` y `actionlint` sobre el workflow CI pasaron. Chrome headless envió el formulario real del portal; el mismo ID se confirmó por `GET /api/envios` y en el HTML de Backoffice; portal y dashboard respondieron HTTP 200.
- CI: workflow preparado en `.github/workflows/ci.yml`; la configuración Compose y los comandos equivalentes se comprobaron localmente. No hubo ejecución remota porque no se publicó ni se hizo push.
- Limitaciones: el alta usa identidad demo fija en ambiente Development; sin autenticación ni autorización real. Worker, RabbitMQ y Redis están presentes en Compose pero no integrados al flujo; no se implementaron RLS ni multitenencia; no se validó MAUI.
- Estado: implementación y verificaciones locales completadas; queda ejecutar el workflow remoto después de que el usuario publique las ramas y actualice los punteros de submódulos.
