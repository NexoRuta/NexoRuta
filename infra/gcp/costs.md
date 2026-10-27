# Costos de la demo en Santiago

Estimación histórica en USD, sin impuestos, consultada el 22/10/2026. La tabla
original describe **una VM** y ya no es el total de la arquitectura aprobada de
dos `n4-custom-6-16384`; no usar sus totales para estimar las nuevas sesiones.
Precios de lista por uso, sin compromisos anuales ni Spot.

| Recurso definido | Tarifa | Costo calculado |
| --- | --- | --- |
| VM N4 highcpu, 8 vCPU / 16 GiB | 0,4378088/h | 1,75 por cuatro horas |
| Cloud SQL Enterprise, 2 vCPU / 8 GiB | 2 × 0,0578 + 8 × 0,0098/h | 0,78 por cuatro horas |
| Hyperdisk Balanced, 20 + 80 GiB | 0,114/GiB-mes | 11,40/mes, incluso apagada |
| Cloud SQL SSD, 20 GiB iniciales | 0,238/GiB-mes | 4,76/mes, incluso apagada |
| IPv4 estática asociada a la VM | 0,005/h | 3,65/mes de 730 horas |
| Backups SQL | 0,112/GiB-mes utilizado | Variable según datos y retención |
| Application Load Balancer global, reglas 80/443 | 0,025/h por las primeras cinco reglas globales del proyecto | 18,25/mes si permanece creado 730 horas, antes de tráfico |

Fuentes: [VM](https://cloud.google.com/products/compute/pricing/general-purpose),
[Cloud SQL](https://cloud.google.com/sql/pricing),
[discos](https://cloud.google.com/compute/disks-image-pricing) y
[IPv4](https://cloud.google.com/vpc/network-pricing#ipaddress).
La dirección asociada sigue considerándose en uso con la VM detenida.
Los discos usan los primeros 3000 IOPS y 140 MiB/s por volumen, incluidos en la
[capacidad base](https://docs.cloud.google.com/compute/docs/disks/hd-types/hyperdisk-balanced).

El cómputo de una sesión del diseño anterior sumaba aproximadamente **USD 2,53
por cuatro horas para una VM**. El coste exacto de dos VMs custom debe recalcularse
en la calculadora oficial con Santiago y `6 vCPU / 16 GiB` por VM. SQL puede estar
encendido antes de arrancar las VMs y tardar en detenerse después;
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

Los totales de tres meses de esta tabla no aplican al diseño de dos VMs. El
balanceador global permanece facturando aunque las VMs estén apagadas; incluirlo
junto con el segundo disco, transferencia entre zonas y telemetría en la próxima
estimación de Billing. El saldo y la fecha real de vencimiento requieren acceso a
tu cuenta.
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
