## Diseño de interfaz

Antes de diseñar, modificar o revisar una interfaz, leer y aplicar `frontend/DESIGN.md`.
Aplicar sus cuatro principios: estados de carga con skeletons cuando correspondan; decisiones simples y jerarquía visual; design tokens semánticos; accesibilidad.
Reutilizar el stack y los componentes existentes. Las referencias y skills externas complementan estas reglas; no las sustituyen.
Verificar en navegador los cambios visuales y de interacción. Informar por separado lo comprobado por compilación, HTTP, automatización y revisión visual.

## Compatibilidad de versiones

Este repositorio está en desarrollo, no en producción. No agregues ni mantengas compatibilidad hacia atrás con APIs, contratos, configuración, mensajes o releases anteriores salvo que el usuario lo pida explícitamente. Cuando cambie un contrato, actualiza productores y consumidores juntos y elimina aliases, adaptadores y fallbacks que solo sirvan a versiones anteriores. Se puede aceptar una interrupción durante despliegues o migraciones para evitar mantener dos versiones compatibles.

No borres migraciones de esquema, datos ni volúmenes persistentes solo por ser antiguos: eso puede perder estado de desarrollo y requiere un cambio deliberado. Conserva las protecciones contra pérdida de datos y secretos; no son compatibilidad de versiones.

## Continuidad en Codex Cloud

Leer `docs/continuidad/cloud-agent.md`, `docs/continuidad/codex-cloud.md` y `scripts/cloud/checkpoint.json` antes de instalar o arrancar. Para Cloud como agent con Docker disponible, usar `scripts/cloud/environment-install.sh` y cargar `scripts/cloud/env-agent.sh`; no requiere sudo ni borradores históricos. Usar los gitlinks exactos; no actualizar submódulos a otras puntas para resolver un build. `scripts/cloud/install.sh`, `dev.py` y `check.sh` preparan una base sintética propia y fixtures PostgreSQL/PostGIS nativas sin exigir Docker. Nunca usar `.env`, respaldos DPAPI ni servicios del Windows del usuario como dependencia Cloud.

Mantener Mapbox temporal (`permanent=false`) y Geoapify vial/geocodificación sin consumo real durante pruebas; usar respuestas controladas. Conservar B1–B5 y el selector con selección, ajuste, guardado y reapertura. Próximo objetivo: CU08 → CU09 → rediseño, sin iniciar etapas no solicitadas. Revisión nativa, habilitación operativa, artefacto Stage y fallo arquitectónico previo siguen siendo pendientes documentados, no aprobaciones implícitas.
