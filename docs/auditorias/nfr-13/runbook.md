# NFR-13 — Runbook de despliegue y recuperación

Este runbook documenta los contratos implementados y el verificador de GCP. Cada ensayo debe registrar la release exacta, la lease vigente y la evidencia resultante en [aceptacion.md](aceptacion.md). Leer ese informe antes de atribuir aceptación a una fuente o despliegue.

## Lectura de salud

- `GET /live`: proceso capaz de contestar; no verifica PostgreSQL ni servicios opcionales.
- `GET /ready`: en API admite tráfico cuando el proceso ya inició, no está drenando, PostgreSQL responde y los almacenes compartidos de Data Protection y cuotas son accesibles cuando están configurados. La API de producción exige ambos. Cada check de dependencia tiene límite de 2 s. Los portales comprueban proceso y almacén compartido de claves cuando corresponde.
- `GET /health`: resumen público de readiness. Responde solo estado general y nombres/estados de checks; no usarlo para recuperar secretos ni datos internos.
- `200` significa apto para ese contrato. `503` significa que no debe recibir tráfico. Las rutas retiradas `/health/ready` y `/health/live` no deben usarse como fallback.

Al revisar balanceo, usar los verificadores de despliegue existentes y atribuir A/B por logs/resource attributes `service.instance.id` y `service.version`. La telemetría de logs de Grafana en A no sirve como único observador durante una caída de A.

## Verificación NFR-13 en GCP

Desde la raíz del repositorio, `python scripts/gcp/verify_nfr13.py inspect` es de solo lectura: muestra las dos VM registradas, estado de Cloud SQL, lease acotada y backends de API. `--help` e importar el módulo no ejecutan comandos GCP. La herramienta rechaza proyectos, bucket y zonas distintos de la demo registrada.

Los subcomandos `api-container` y `vm` inyectan una sola falla explícita. Requieren release publicada exacta, `https://api.<dominio-demo>` y confirmación escrita, ambos backends sanos, Cloud SQL operativo y al menos 90 minutos restantes en la lease original. Adquieren el mismo control lock compartido por deploy y guard; no extienden ni renuevan la lease de sesión. Los ensayos miden hasta 90 muestras HTTP, exigen que el balanceador retire el backend fallado, que el par continúe sano y que haya diez respuestas `/ready` consecutivas; la recuperación HTTP debe comenzar dentro de 60 s. El proceso repara el servicio/VM en `finally` y verifica ambos backends antes de reportar `restored: true`.

```powershell
python scripts/gcp/verify_nfr13.py inspect --output docs/auditorias/nfr-13/evidencia/gcp-inventario.json
python scripts/gcp/verify_nfr13.py api-container --node a --release RELEASE_ID --api-origin https://api.DOMINIO_DEMO --confirm-fault NFR13-FAULT-API-CONTAINER-A --output docs/auditorias/nfr-13/evidencia/gcp-api-a.json
python scripts/gcp/verify_nfr13.py api-container --node b --release RELEASE_ID --api-origin https://api.DOMINIO_DEMO --confirm-fault NFR13-FAULT-API-CONTAINER-B --output docs/auditorias/nfr-13/evidencia/gcp-api-b.json
python scripts/gcp/verify_nfr13.py vm --node b --release RELEASE_ID --api-origin https://api.DOMINIO_DEMO --confirm-fault NFR13-FAULT-VM-B --output docs/auditorias/nfr-13/evidencia/gcp-vm-b.json
python scripts/gcp/verify_nfr13.py vm --node a --release RELEASE_ID --api-origin https://api.DOMINIO_DEMO --confirm-fault NFR13-FAULT-VM-A --output docs/auditorias/nfr-13/evidencia/gcp-vm-a.json
```

`RELEASE_ID` y `DOMINIO_DEMO` deben copiarse del resumen de despliegue vigente o de las salidas Terraform actuales; no reutilizar una captura o un manifiesto anterior. Ejecutar un escenario por vez. Confirmar el estado `passed` y `restored: true` del JSON antes de iniciar el siguiente. No iniciar si el control lock está ocupado, si faltan muestras actuales o si la ventana no deja 90 min para recuperación.

Si el proceso o la VM desaparece antes de ejecutar su `finally`, recuperar la misma VM de la sesión y no cambiar la release:

```powershell
gcloud compute instances start nexoruta-demo --project=nexoruta-demo-20261022 --zone=southamerica-west1-a --quiet
gcloud compute instances start nexoruta-demo-b --project=nexoruta-demo-20261022 --zone=southamerica-west1-b --quiet
```

Después de que la VM afectada esté `RUNNING`, recuperar API A/B con Compose desde la release objetivo, usando el `.env` privado ya existente en esa VM:

```bash
sudo docker compose --project-name nexoruta-demo --env-file /srv/nexoruta/releases/RELEASE_ID/.env -f /srv/nexoruta/releases/RELEASE_ID/compose.yaml up -d --no-deps --force-recreate --wait --wait-timeout=300 api
```

Comprobar `/ready`, los dos health backends, la release de ambos nodos, la lease original y la recuperación antes de concluir el ensayo. Estos comandos preservan los discos y volúmenes; no ejecutar `down -v`, migraciones ni `demo_session.py start` para recuperarse.

## Barrido de plazos de prueba

`ProofValidationDeadlineWorker` llama a `nexoruta_app.expire_pending_proof_deadlines(now, 100)`:

- `Completed`: lote comprometido. Si `MoreWork=true`, el mismo worker toma el próximo lote sin esperar 30 s.
- `Contended`: otra instancia mantiene el lock transaccional; esperar el siguiente ciclo.
- `NotDue`: el último ciclo completado sigue dentro del cooldown de 30 s de PostgreSQL.
- Error SQL: cuenta como fallo, no como cero vencimientos. La transacción revierte efectos y estado de coordinación; un competidor puede recuperarlo.
- Shutdown: cancelar la consulta sin confirmar un éxito. El lock de transacción se libera con rollback/cierre de sesión.

Métricas sin IDs de negocio: `nexoruta.worker.proof_deadline.sweeps`, `.shipments`, `.continuations`, `.duration` y `.last_success.age`. Edad `-1` indica que ese proceso todavía no observó una finalización; no significa cero segundos.

No borrar manualmente `ProofDeadlineJobState`, liberar el advisory lock con SQL de sesión ni elevar privilegios del worker. Si hay errores, revisar la excepción acotada del worker, conectividad PostgreSQL y permisos de la función; luego confirmar por lecturas restringidas que la fila/efectos se recuperan. No introducir reintentos de efectos externos como si fueran exactly-once.

## Mantenimiento y recuperación

El presupuesto preparado es 20 s para el host, 30 s para Docker y 30 s de drenaje del LB; la entrega existente espera 35 s. El ensayo debe confirmar que la app sale dentro de esos límites y que una reserva no confirmada vuelve a ser recuperable.

Durante una actualización, conservar el procedimiento coordinado existente: retirar ambos nodos, detener aplicaciones, aplicar migración una vez, actualizar B/A y readmitir solo nodos sanos. No ejecutar una versión binaria vieja contra el esquema nuevo. Mantener datos, respaldos, certificados, volúmenes y sesión; no usar `down -v`, borrar estado de coordinación ni reiniciar SQL como atajo.

Una falla de API en un nodo se ensaya por separado de una caída de VM o zona. Esta herramienta solo contempla contenedor API y VM; no detiene SQL/brokers ni ejecuta `tofu apply`. Toda ventana requiere autorización operativa vigente, release publicada y plan de restauración; el propio runbook no autoriza una ejecución futura.

La pérdida de una VM A puede degradar brokers, MongoDB y observabilidad que residen allí. SQL continúa siendo zonal. No afirmar HA completa a partir de la continuidad de la API.
