# Costos de la demo en Santiago

Estimación en USD, sin impuestos, consultada el 22/10/2026. Precios de lista por
uso, sin compromisos anuales ni Spot. Seleccionar **Santiago** en las tablas
oficiales: su vista inicial muestra Iowa, cuyos precios son diferentes.

| Recurso definido | Tarifa | Costo calculado |
| --- | --- | --- |
| VM N4 highcpu, 8 vCPU / 16 GiB | 0,4378088/h | 1,75 por cuatro horas |
| Cloud SQL Enterprise, 2 vCPU / 8 GiB | 2 × 0,0578 + 8 × 0,0098/h | 0,78 por cuatro horas |
| Hyperdisk Balanced, 20 + 80 GiB | 0,114/GiB-mes | 11,40/mes, incluso apagada |
| Cloud SQL SSD, 20 GiB iniciales | 0,238/GiB-mes | 4,76/mes, incluso apagada |
| IPv4 estática asociada a la VM | 0,005/h | 3,65/mes de 730 horas |
| Backups SQL | 0,112/GiB-mes utilizado | Variable según datos y retención |

Fuentes: [VM](https://cloud.google.com/products/compute/pricing/general-purpose),
[Cloud SQL](https://cloud.google.com/sql/pricing),
[discos](https://cloud.google.com/compute/disks-image-pricing) y
[IPv4](https://cloud.google.com/vpc/network-pricing#ipaddress).
La dirección asociada sigue considerándose en uso con la VM detenida.
Los discos usan los primeros 3000 IOPS y 140 MiB/s por volumen, incluidos en la
[capacidad base](https://docs.cloud.google.com/compute/docs/disks/hd-types/hyperdisk-balanced).

El cómputo de una sesión suma aproximadamente **USD 2,53 por cuatro horas**.
SQL puede estar encendido antes de arrancar la VM y tardar en detenerse después;
esas transiciones agregan consumo. La base persistente cuesta aproximadamente
**USD 19,81/mes**, antes de backups, objetos, imágenes, secretos, control de
apagado, red y builds. El disco SQL puede crecer automáticamente hasta 50 GiB.

Para presupuestar, reservar otros **USD 5–20/mes** para esos servicios auxiliares
con poco tráfico. Es una reserva orientativa, no una tarifa fija ni un tope:
cada push puede ejecutar pruebas, publicar seis imágenes y consumir Cloud Build.
Los bundles se eliminan a los 30 días; las imágenes se conservan durante el
proyecto y su almacenamiento crece con las releases.

| Uso durante un mes | Cómputo de sesiones | Persistencia inicial | Reserva auxiliar | Total orientativo |
| --- | --- | --- | --- | --- |
| 8 sesiones de 4 horas | 20,22 | 19,81 | 5–20 | 45–60 |
| 20 sesiones de 4 horas | 50,54 | 19,81 | 5–20 | 75–90 |

Tres meses de 20 sesiones mensuales serían aproximadamente **USD 226–271**,
antes de impuestos, variaciones de uso y crecimiento. Es compatible como objetivo
con el crédito de USD 300 si no lo consumen otros proyectos, pero hay que observar
Billing. El saldo y la fecha real de vencimiento requieren acceso a tu cuenta.
El presupuesto configurado avisa desde USD 40, 64 y 80 de consumo mensual antes
de créditos; no detiene recursos ni garantiza permanecer bajo el crédito.

GitHub Actions en repos privados, dominio propio, SMTP externo, Geoapify y Mapbox
pueden tener costos adicionales que no cubre el crédito GCP. Las pruebas y el
APK se ejecutan en GitHub; las imágenes se compilan en Cloud Build.

La alternativa más barata sería PostgreSQL dentro de la misma VM, con backups
propios: quitaría el cómputo y SSD de Cloud SQL, pero agregaría carga a los 16 GiB
y trabajo de administración. Se implementa Cloud SQL porque permite aislar la
base y probar la integración administrada solicitada. Cloud Run requeriría
adaptar los workers y la mensajería actuales; no es una sustitución directa de
este Compose.
