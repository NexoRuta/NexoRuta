# NFR-14 — Inventario y estado de costos

**Estado: P7 pendiente.** Este informe no presenta una tarifa actualizada ni
gasto observado como si se hubiera medido. La consulta de solo lectura del
14/11/2026 inventarió recursos y el presupuesto; no consultó Cloud Billing
Reports/Cost table ni obtuvo créditos o costo neto. El detalle de evidencia
pendiente está en [`evidencia/costos-observados.json`](evidencia/costos-observados.json).

## Inventario que debe entrar en la estimación

La inspección incluida en [diagnostico.md](diagnostico.md) observó A/B detenidas,
Cloud SQL principal encendido, SQL de restauración detenido, balanceador global,
IP/certificado, discos de ambas VMs, Memorystore Basic 1 GiB, Artifact Registry,
buckets de estado/delivery/carga, Secret Manager, Scheduler/Workflows y un Cloud
Run Job de carga listo. El runtime además declara Redis TLS/AUTH como contenedor
en VM B. Memorystore permanece como recurso adicional: no asumir que una parada
de VM lo destruye ni que el runtime lo utiliza.

El siguiente cálculo debe usar cantidades y SKUs confirmados en la fecha de
consulta, región de Santiago y precios oficiales. No mezclar impuestos, créditos
o moneda local con costo bruto en USD.

| Grupo | Cantidad/base observada | Precio actual | Estado |
| --- | --- | --- | --- |
| Compute Engine N4 custom | Dos VMs de 6 vCPU/16 GiB; sesiones limitadas a 4 h, ambas detenidas en el corte. | Pendiente por SKU/uso y región. | No calculado. |
| Discos Hyperdisk Balanced | Dos boot de 20 GiB y dos data de 80 GiB; conservar ambos estados aunque VM esté detenida. | Pendiente por GB-mes/provisioning. | No calculado. |
| Cloud SQL principal | PostgreSQL 18 Enterprise `db-g1-small`, `ALWAYS`, SSD 20 GiB iniciales con auto-resize. | Pendiente por cómputo, almacenamiento y crecimiento. | No calculado. |
| SQL de restauración | Una instancia observada `STOPPED`/`NEVER`; verificar almacenamiento y otros recursos asociados. | Pendiente. | No calculado. |
| Balanceador e IP | Balanceador global HTTPS con IP reservada/activa. | Pendiente por reglas, forwarding, bytes y horas. | No calculado. |
| Redis | Redis en VM B más Memorystore Basic 1 GiB `READY` observado. | Pendiente; separar runtime y recurso residual. | No calculado. |
| Delivery/build | Artifact Registry, buckets versionados, bundles, seis imágenes por release y Cloud Build. | Pendiente por GB-mes, operaciones y minutos de build. | No calculado. |
| Control/observabilidad | Secret Manager, Scheduler/Workflows, logs/métricas/trazas y Cloud Run Job de carga listo. | Pendiente por invocaciones, almacenamiento y ejecución. | No calculado. |
| Red | Tráfico interzona, salida pública, IAP y transferencia de build. | Pendiente por bytes/destino. | No calculado. |

## Escenarios obligatorios

P7 debe presentar, con unidades/cantidades, tarifa oficial, fecha/enlace y
fórmula reproducible:

1. **Fijo mensual con A/B detenidas:** SQL, discos, balanceador/IP, Memorystore,
   buckets, Artifact Registry, secretos, control y observabilidad.
2. **Incremento por sesión de cuatro horas:** VM A/B, SQL durante la preparación
   y ventana adicional, red interzona, despliegue y telemetría.
3. **Publicación:** CI, Cloud Build, almacenamiento de imágenes y bundle.
4. **Ensayo:** proyecto aislado, build/despliegue, ventana aprobada, cleanup y
   recursos facturables hasta la confirmación de borrado.
5. Escenarios de 8 y 20 sesiones mensuales; horizonte de tres meses solo con
   vencimiento/saldo de crédito verificados.

Fuentes de tarifas a revisar para la fecha del cálculo: [Compute Engine](https://cloud.google.com/compute/pricing),
[Cloud SQL](https://cloud.google.com/sql/pricing), [discos](https://cloud.google.com/compute/disks-image-pricing),
[balanceo](https://cloud.google.com/vpc/network-pricing), [Memorystore](https://cloud.google.com/memorystore/pricing),
[Cloud Storage](https://cloud.google.com/storage/pricing), [Artifact Registry](https://cloud.google.com/artifact-registry/pricing)
y [Cloud Build](https://cloud.google.com/build/pricing). Registrar la URL/SKU
exactos y fecha consultada en la tabla final; estos enlaces no son por sí solos
una estimación.

### Revisión pública de fuentes — 14/11/2026

Se revisaron las páginas oficiales de precio de N4/custom Compute Engine, Cloud
SQL, Hyperdisk, Memorystore y red. Sus tablas ofrecen selector de región; el
contenido indexado puede mostrar Iowa como selección por defecto. No copiar esa
tarifa como Santiago sin confirmar `southamerica-west1` en la tabla. No se
registraron números parciales porque no quedó evidencia de una tabla seleccionada
para Santiago para cada SKU. La [Pricing API](https://docs.cloud.google.com/billing/docs/how-to/get-pricing-information-api)
requiere una API key para consultar SKUs/precios públicos; no se usó ni se
solicitó una credencial para esta revisión.

Para el gasto real, usar [Billing Reports](https://cloud.google.com/billing/docs/how-to/reports)
y la [Cost table](https://cloud.google.com/billing/docs/how-to/pricing-table)
desde una identidad autorizada. Filtrar por el proyecto y el período solicitado,
desglosar por servicio/SKU, y guardar una exportación sanitizada con costo bruto,
créditos, neto, moneda y fecha máxima de uso incluida. No incluir ID de billing,
correo, pago ni recursos privados en el artifact.

## Consumo facturado

Falta descargar el Billing Report/Cost table filtrado por proyecto y período con
una identidad autorizada. El resumen debe separar costo bruto, créditos, neto,
moneda, período y última fecha de consumo disponible. Registrar el desfase de
facturación y repetir la lectura cuando incluya la ventana completa. El
presupuesto USD 80/mes observado, `EXCLUDE_ALL_CREDITS`, filtro por número de
proyecto y umbrales 50/80/100 % es una alerta: no reemplaza el costo real ni
detiene recursos.

La recreación no debe ejecutarse hasta que estén aprobados padre GCP, cuenta de
billing, presupuesto del proyecto descartable, techo de costo y ventana. La
decisión explícita actual del usuario es no ejecutar las recreaciones aisladas,
su cleanup ni la CI/publicación candidata de `main`; esos campos quedan
pendientes sin inventar valores.
