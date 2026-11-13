# Demo de NexoRuta: comercio → depósito → reparto → retorno

Guía para presentar el producto desde **el ambiente remoto**, con navegador en Windows y la aplicación Android apuntando a esa misma API. Preparada el 5/11/2026 sobre develop. El [workflow estructurado](workflow.json) contiene 41 escenas con dependencias, actores, acciones, aserciones y evidencias para un agente. La [matriz](cobertura.md) ubica 30 CU, 9 capacidades de aplicaciones, 15 requisitos no funcionales y los 15 opcionales del catálogo, distinguiendo los 6 seleccionados.

**Ambiente disponible:** [Actions run 42104311807](https://github.com/NexoRuta/NexoRuta/actions/runs/42104311807) terminó correctamente con `release-c5904be94e0e41f6b5ff20fc21dd1bb4`. El bootstrap ya corre automáticamente antes de start/update en develop; el plan aplicado tuvo 0 altas, 1 cambio y 0 eliminaciones. El sondeo HTTPS de las 21:48 UTC dio 200 en `/ready`. Las VMs tienen vencimiento aproximado a las 23:32 UTC (20:32 Uruguay). Los PR #68 y #69 están integrados. El ensayo web autenticó Commerce, Backoffice y Admin, pero no completó el circuito: el enlace de seguimiento falla, Demo Uruguay no tiene zona ni tarifa, la pantalla para crear zonas queda cargando y Flota responde 403 para el actor propietario. No se crearon datos de negocio nuevos porque falta un tenant exclusivo preparado. En Android se instaló y abrió en un Galaxy S21 el APK ARM64 de develop; solo se comprobó la pantalla de acceso, porque el almacén del ensayo no ofrece credenciales de repartidor. El E2E continúa bloqueado hasta preparar tenant y actor, según E2E-DMO-15. El workflow valida 41 escenas, pero es una especificación para persona/agente, no un runner; Integrated CI sigue con fallos en los tres shards backend del run [42103517263](https://github.com/NexoRuta/NexoRuta/actions/runs/42103517263). Ver [estado observado](estado-observado.md) e [issues E2E](issues-e2e-20261105.md).

## Abrir estas cuatro cosas

1. Este documento, para el presentador.
2. Backoffice A, Commerce C1 y Backoffice B/Commerce C2, en perfiles de navegador separados. Una ventana privada adicional representa al destinatario.
3. Android y su pantalla compartida: **NexoRuta Repartidor**, paquete `uy.nexoruta.repartidor`.
4. El manifiesto privado del ensayo y [la hoja de resultados](automatizacion.md#resultados). No proyectar credenciales, tokens ni correo con códigos de seguridad.

## Historia y tiempos

«Un comercio prepara tres envíos. El operador recibe cuatro bultos, arma una ruta y la despacha. El repartidor entrega uno y registra dos intentos sin Internet. Al recuperar la conexión se actualiza la operación. Un envío se reprograma, otro se devuelve, se rinde la carga y se libera la flota con las confirmaciones del depósito».

| Bloque en vivo | Tiempo orientativo | Escenas |
|---|---:|---|
| Actores, configuración y marca ya preparadas |5min| CFG-01–06 |
| Alta, cotización, CSV, consulta y etiquetas |8min| WEB-01/02/04 |
| Recepción, restricciones, planificación y despacho |8min| DEP-01; RUT-01/03/04 |
| Android: descarga, carga, entrega e intentos offline, sincronización |12min| MOV-01–06 |
| Reprogramación, devolución, rendición y flota |7min| CIE-01–03 |
| Observabilidad y pendientes de alcance |5min| TEC-02; GAP-01–06 |

Reservar **45min**, más15–25min si se muestran las extensiones. Preparar configuración/actores antes; no intentar todos los ABM desde cero durante la reunión. Si falta tiempo, reducir explicaciones o extensiones, conservando la entrega offline y el retorno. La cobertura completa exige ejecutar también las extensiones y revisar las brechas: el recorrido principal por sí solo no acredita todo el alcance.

## Preparar el ambiente remoto

### PRE-01 — Versión, sesión y conectividad

Tomar las URLs y la release del resumen de **Actions → NexoRuta - manual VM controls**, repositorio madre. La IP/host puede cambiar: usar el resumen vigente, no memorizar los hosts del último ensayo. Consultar [operación remota](../../infra/gcp/guia-uso-actions.md) y [tags de integración](../../infra/gcp/integration-tags.md).

- Si el entorno está apagado, el responsable inicia `start`. Si ya está encendido y necesita otros commits, elige `update`. En `develop` esas operaciones construyen/despliegan el root publicado con sus gitlinks; no ejecutan Integrated CI. En `main` usan el canal publicado de main. Ambos canales comparten VMs y Cloud SQL.
- Registrar los SHAs **desplegados**, la release y el vencimiento: las sesiones se apagan automáticamente a las cuatro horas. Un `start` sobre una sesión activa no la extiende. Programar el arranque de modo que cubra ensayo y reunión.
- Comparar con los SHAs locales de [workflow.json](workflow.json). El fetch local no actualiza el servidor. Verificar CI del candidato y migraciones con el procedimiento existente antes de actualizar; no reemplazar gitlinks ni borrar datos para conseguir un arranque.
- Exigir HTTP200 de `/live` y `/ready`, ingreso correcto de cada portal y acceso al mismo operador/comercio. Un503 bloquea el recorrido; no esperar a descubrirlo frente al cliente.
- Preparar una organización/tenant **exclusivo para datos sintéticos de la demo**, identificados por `run_id`. Ningún actor opera envíos de otras pruebas. Toda recepción, foto, entrega o retorno de este ensayo se identifica como simulación de demo, sin afirmar constataciones del mundo real.

Desde PowerShell, con `$Api` tomado del resumen vigente:

```powershell
$Api = 'https://api.HOST-VIGENTE/'
Invoke-WebRequest -UseBasicParsing ($Api.TrimEnd('/') + '/ready')
git rev-parse HEAD
git submodule status
adb devices -l
```

**Android remoto:** usar APK configurado con `NexoRutaBackendTarget=GcpDemo` y `NexoRutaGcpApiOrigin` igual al origen HTTPS de esa sesión. Registrar versión, SHA256 y ABI. El APK descargable de una release main puede corresponder a otra versión: no asumir que incluye develop. Para compilar el candidato seguir [Mobile](../../mobile/README.md#configuración-de-servicios) y [CI/distribución](../../mobile/docs/ci-distribucion.md), eligiendo `android-x64` para emulador x86_64 o `android-arm64` para teléfono compatible. Un Debug instalado manualmente requiere `EmbedAssembliesIntoApk=true`.

El target GcpDemo usa confianza TLS normal: **no necesita gateway local, CA local ni `adb reverse`**. Si hay un reverse5843 antiguo, no demuestra conexión al remoto; comprobar el target del APK. Para actualizar usar el mismo paquete y firma (`adb -s SERIAL install -r RUTA_APK`); no desinstalar ni limpiar datos/colas. Release exige desbloqueo del dispositivo; Debug lo omite por configuración de compilación. Emulador permite prueba funcional simulada; cámara, GPS en segundo plano, biometría y push reales requieren dispositivo y observación propia.

### Actores de la demo

| Alias | Sesión y tarea |
|---|---|
| Administrador A / B | Configuración de dos operadores distintos. |
| A1 / A2 | Despachadores de A; `envios.consultar`, `envios.gestionar`; A2 para competencia/conflictos. |
| C1 / C2 | Comercios diferentes, `envios.crear` y `envios.consultar`. |
| R1 / R2 | Repartidores de A con `reparto.ejecutar` y perfil habilitado; sin privilegios de despachador. |
| Solo consulta | Mostrar rechazo de acceso a gestión. |
| Destinatario | Anónimo, únicamente enlace legítimo del envío nuevo. |
| Admin plataforma | Alta/soporte de organizaciones cuando corresponda; no acceso operativo implícito. |

El seed `POST /api/admin/demo-data` prepara estos accesos: A/B son `admin.operador1@demo.nexoruta.test` y `admin.operador2@demo.nexoruta.test`; C1/C2 son `admin.comercio1@demo.nexoruta.test` y `admin.comercio2@demo.nexoruta.test`; A1/A2 son `a1@demo.nexoruta.test` y `a2@demo.nexoruta.test`; R1/R2 son `r1@demo.nexoruta.test` y `r2@demo.nexoruta.test`; Solo consulta es `consulta@demo.nexoruta.test`. `admin@nexoruta.test` es Admin plataforma. El seed deja estas cuentas con la contraseña compartida `Demo12345!2026`; al repetirse sincroniza usuarios y permisos sin borrar organizaciones ni historia. El comercio elige operador en cada envío: no es necesario inventar un vínculo permanente comercio–operador. El alta por autogestión o plataforma se explica con su actor real; no acredita por sí sola el ABM de comercios clientes desde Backoffice requerido literalmente por CU-01.

### CFG-01–06 — Configuración sintética reproducible

Preparar y guardar todo por las interfaces existentes, con permisos reales. Mostrar brevemente los valores y volver a abrirlos para demostrar persistencia. Para los negativos de capacidad preparar vehículos auxiliares libres: V-peso con999g/100000cm³ y V-volumen con10000g/1999cm³; MULTI(1000g/2000cm³) debe superar respectivamente cada límite. Para el negativo de paradas, admitir por WEB-03 y recibir el envío API auxiliar: intentar los cuatro envíos con máximo3, comprobar rechazo y luego excluir API del plan principal.

| Pantalla Backoffice | Valores de ejemplo / comprobación |
|---|---|
| `/usuarios`, `/roles` | A1/A2/R1/R2 y usuario solo consulta; este último no accede a `/deposito` por URL directa. B/C2 no ven una referencia nueva de A/C1. |
| `/zonas` | Zona del departamento oficial UY-MO que contenga(-34.9,-56.2), franjas diarias00:00–23:59 en America/Montevideo para el ensayo. Rivera(-30.905,-55.55) queda fuera. B diferente. |
| `/tarifas` | Publicación v1 UYU; Estandar: base100,10/kg,1000/m³, recargo fijo5 y bonificación fija2. Urgente: base150, mismos componentes. B diferente. |
| `/reglas-operativas` | Dos intentos, intervalo1minuto, motivo Ausente, prueba nombre+foto, devolución/plazos por modalidad explícitos. Guardar UUID/número de publicación. |
| `/identidad-visual` | Nombre Demo A, logo de prueba, colores accesibles y contacto sintético. B con otra marca. Reabrir; contrastar Commerce y, si puede abrirse, Tracking. |
| `/configuracion-reparto` | America/Montevideo, máximo3 paradas, bloquear diferencias de carga; definir foto en intento y base operativa confirmada(-34.9,-56.2). |
| `/repartidores`, `/vehiculos`, `/flota` | R1/R2 habilitados y V1/V2:10000g,100000cm³. Registrar disponibilidad inicial explícita de recursos sintéticos; no confundir habilitado con disponible. |

Las franjas amplias y el intervalo corto son **configuración de ensayo**, no políticas propuestas al cliente. Mantener Mapbox `permanent=false`. En pruebas automatizadas se usan proveedores/respuestas controlados; Geoapify geocodificación/routing sin llamadas reales. La guía no habilita proveedores ni cambia planes. El selector debe conservar selección→ajuste→confirmación→guardado→reapertura. Si el remoto no ofrece modo controlado para la búsqueda, registrar esa parte bloqueada y usar solo la selección manual existente cuando esté disponible; no fingir respuesta del proveedor.

### Generar el juego nuevo

Después de crear A y su zona, desde la raíz en Windows:

```powershell
python scripts/demo/workflow.py validar
python scripts/demo/workflow.py preparar --run-id Demo05NovA --operador-id UUID-NUEVO-A --zona-id UUID-NUEVO-ZONA --fecha 2026-11-05
```

Sustituir UUID, fecha y `run_id` por los del ensayo; no reutilizar la jornada finalizada de un ensayo anterior. El generador rechaza carpeta existente y UUID reservados. Solo escribe `.local/demo/ID/`, ignorada por Git; **no hace HTTP/SQL ni crea cuentas, envíos, jornadas o hechos físicos**. Completar `manifest.json` con URLs/release/actores/recursos y capturar IDs durante el recorrido. `individual.json` y `api-alta.json` necesitan la publicación vigente antes de enviar por API. El CSV usa la versión2 de13 columnas, sin formatos históricos.

| Datos | Canal | Uso y oráculo |
|---|---|---|
| MULTI,2 bultos500g y20×10×5cm cada uno | UI, `individual.json` como ficha | Entrega completa offline.1kg/0.002m³:100+10+2+5−2=**115 UYU**. |
| INTENTO,1 bulto igual | `01-alta-v2.csv` | Intento Ausente→reprogramación operativa; **109 UYU**. |
| RETORNO,1 bulto igual | Mismo CSV | Intento→devolución→rendición→recepción; **109 UYU**. |
| API | `api-alta.json` | Extensión de alta por API autenticada;109 UYU; no incluir en ruta principal. |
| Reimportación parcial | `02-reimportacion-parcial-v2.csv` | Solo INTENTO; ningún duplicado. |
| ATOMICO nuevo + INVALIDO peso−1 | `03-lote-invalido-atomico-v2.csv` | Cero altas en ambos, incluso en la fila válida. |
| FUERACOBERTURA | `04-sin-cobertura-v2.csv` | Rivera rechazado sin alta/cargo. |
| DISCREPANCIA,CAPACIDAD,CONFLICTO,PRUEBA,CANCELACION,HISTORIA,AISLAMIENTO | `05-extensiones-v2.csv` | Admitir solo los necesarios para cada extensión; nunca sumar a la ruta principal. |

Los correos `example.test` son sintéticos y no reciben correo público. Para mostrar cancelación/código usar un buzón de prueba propio autorizado y modificar ese destinatario **antes del alta**. No enviar correos a terceros.

## Recorrido principal en vivo

### WEB-01/02/04 — El comercio prepara el trabajo

**Decir:** «Cada comercio ve sus envíos; selecciona operador y servicio, declara bultos y conoce el precio antes de confirmar».

1. C1 abre **Crear envío** (`/envios/crear`), elige A y Estandar, carga MULTI, confirma su destino y agrega los dos bultos de la ficha. Mostrar cotización115 UYU y desglose; confirmar una vez.
2. En **Mis envíos** (`/envios`) reabrir destino/datos/precio; anotar ID/UUID de bultos. En Backoffice A abrir `/`, buscar el código y comprobar el mismo envío. B y C2 no lo ven.
3. C1 abre **Importar CSV** (`/envios/importar`), importa el lote de INTENTO/RETORNO con `VersionFormato=2`; cada uno109 UYU. Repetir lote completo y parcial: siguen siendo dos envíos nuevos, sin duplicados. Mostrar rechazo atómico y cobertura con los archivos negativos; ninguna referencia rechazada debe quedar creada.
4. Descargar etiquetas de MULTI: dos páginas100×150mm, una por bulto; QR contiene UUID-D, código visible coincide. Mostrar PDF o imprimir al tamaño real. PDF descargado no acredita impresora/lector físico.
5. Mostrar **Ver seguimiento** únicamente si se obtuvo un enlace legítimo en el entorno. En este corte GCP Production bloquea su recuperación desde Commerce: registrar bloqueo y continuar con depósito, sin cambiar Production a Development. Si se dispone de enlace legítimo, abrirlo sin sesión: solo estado y marca, sin historial ni ventana (GAP-01).

**Resultado:** MULTI Admitido/2 bultos, INTENTO y RETORNO Admitido/1 bulto cada uno; precio/reglas capturados por envío.

### DEP-01 — El depósito recibe lo declarado

**Decir:** «Una declaración del comercio y una recepción en depósito son hechos distintos».

1. A1 abre `/deposito/recepcion`, escanea QR o usa UUID/código del primer bulto. Consultar no escribe. Registrar medidas observadas conforme al escenario sintético y confirmar.
2. Antes del segundo bulto, MULTI permanece **Admitido**. Recibir el segundo: pasa a **EnDeposito**. Repetir la consulta/recepción no duplica hechos.
3. Recibir INTENTO/RETORNO por el mismo circuito. Mostrar actor, medidas declaradas/observadas y últimos cotejos.

Una discrepancia se muestra con envío auxiliar en DEP-02; no bloquear la ruta principal con ella ni marcar medidas ficticias iguales para resolverla. Su resolución operativa continúa pendiente(D-P02).

### RUT-01/03/04 — Planificar y despachar

**Decir:** «Se validan recursos, carga y horarios; el orden queda explícito y la asignación es exclusiva».

1. Mostrar rechazo de un plan que exceda capacidad usando los vehículos auxiliares pequeños y MULTI recibido. Para máximo3 paradas usar los cuatro envíos(MULTI/INTENTO/RETORNO/API recibido) y comprobar rechazo; no modificar recursos ya ocupados. Para horario inválido, una llegada23:58 con servicio2min no cabe completa en la franja00:00–23:59. Comprobar cero asignaciones parciales y volver al plan válido.
2. Abrir `/rutas/planificar`; elegir **hoy del operador**, R1/V1 y orden MULTI→INTENTO→RETORNO. Como plan sintético, tomar H=próximo minuto local, salida H, llegadas H+5/H+10/H+15min, servicio2min por parada y retorno H+25min; configurar servicio/margen de base coherentes y mantener todo dentro de la franja y el mismo día. Guardar y reabrir detalle `/rutas/{id}`.
3. Comparar **3 paradas,4 bultos,2000g,4000cm³**, base, recursos, orden y plan temporal. El orden es manual/documentado; no se afirma optimización automática. Las franjas elegibles no prueban un compromiso individual no capturado al alta(D-P01).
4. Despachar. Ruta **Despachada**, envíos **AsignadoRuta**, R1/V1 ocupados. Los bultos aún están en depósito: despacho no es carga ni salida.

### MOV-01/02 — El repartidor recibe y verifica su hoja

**Decir:** «La app conoce la hoja, las reglas de cada envío y los bultos que realmente se cargaron».

1. Android R1 ingresa y descarga hoja de hoy; abre **Mi recorrido**. Mostrar matrícula, tres paradas, detalle **Ver destino** y reglas. **Iniciar jornada** requiere conexión, día correcto y confirmación del servidor.
2. Escanear un QR extraño: rechazado. Escanear tres de cuatro: mostrar faltante y bloqueo de **Comenzar reparto**. Escanear el cuarto; repetir un código no duplica carga.
3. **Comenzar reparto** y esperar acuse. Comprobar ruta **EnCurso**, envíos **EnTransito** y custodia **Repartidor**. La UI distingue salida guardada localmente de salida confirmada.

El mapa offline es **opcional en el código actual**; no bloquear el circuito por la afirmación antigua de Mobile README. Ver `HojaRutaViewModel.EstadoMapa` y `ConfirmarCarga`. Sin mapa descargado no se afirma navegación cartográfica offline. Coordenadas del emulador son simuladas.

### MOV-03–06 — Trabajar sin conexión y sincronizar

**Decir:** «El teléfono conserva el trabajo y sus pruebas aunque pierda Internet».

1. Cortar Wi-Fi/datos **del Android**, dejando navegador/servidor conectados. En emulador verificar realmente que una consulta nueva a API falla: desactivar una interfaz no basta si existe otro camino de red. No apagar la VM para este paso.
2. Abrir MULTI, completar nombre receptor Demo y **Tomar foto** de un objeto de prueba. Capturar firma/documento si su publicación lo exige. Pulsar **Confirmar entrega** una vez. Mostrar guardado local pendiente; Backoffice todavía no muestra entrega.
3. Reabrir app sin limpiar datos. Recuperar jornada y prueba. En INTENTO y RETORNO seleccionar **Ausente**, capturar evidencia configurada y **Registrar intento**.
4. Restablecer conectividad original. **Actualizar** y esperar los acuses, hasta120s. Una actualización puede consumir hasta45s de sincronización más consultas locales/remotas; observar condición, no asumir éxito por desaparecer un spinner.
5. Confirmar en A/C1: MULTI **Entregado** con prueba validada; INTENTO/RETORNO **NoEntregado**. Repetir **Actualizar**: sin duplicar entregas, intentos ni archivos. Comparar hora capturada con hora recibida; mostrar ubicación/precisión con su procedencia.

Si quedan pendientes, conservar sobres/IDs y reintentar la misma cola; registrar error. No borrar almacenamiento ni generar una segunda entrega. Falta de GPS/cámara/permisos se reporta como dependencia, sin inventar evidencia.

### CIE-01–03 — Decidir, rendir y liberar

**Decir:** «Entregar, cerrar la jornada, devolver carga y liberar un vehículo son confirmaciones diferentes».

1. A1 abre `/deposito`: reprogramar INTENTO con versión actual e intervalo permitido; iniciar devolución de RETORNO. Deben quedar **Reprogramado** y **EnDevolucion**, todavía bajo custodia R1. El intervalo de ensayo1minuto suele transcurrir durante la explicación; si no, esperar o mostrar rechazo sin cambiar el reloj.
2. R1 vuelve al recorrido, **Rendir bultos en depósito**, selecciona solo INTENTO/RETORNO y confirma. Release exige desbloqueo local. Quedan **PendienteDeposito**; MULTI entregado no se rinde.
3. **Terminar jornada**, esperar cierre confirmado. Si queda pendiente, **Actualizar** conservando el mismo cierre. GPS se detiene. Mostrar que R1/V1 todavía requieren retorno/liberación.
4. A1 confirma recepción por el circuito de **retorno en `/deposito`**, distinto del primer cotejo CU-10. RETORNO llega a **Devuelto**; INTENTO conserva **Reprogramado** y custodia **Deposito**, listo para nueva planificación cuando sus reglas lo permitan.
5. En `/flota`, constatar retorno y requisitos pendientes y liberar. Solo ahora se muestran recursos disponibles. ETA/GPS y cierre no liberan por sí solos.

**Foto final:** C1 ve sus tres envíos con estados Entregado/Reprogramado/Devuelto y sus cargos originales. A ve los mismos resultados y recursos liberados; B/C2 no tienen acceso. Esto no acredita cuenta corriente/liquidación ni autogestión completa de devoluciones.

## Extensiones para completar la cobertura

Ejecutar en escenas separadas, con referencias/recursos nuevos y suficiente tiempo; no reutilizar una jornada cerrada ni un recurso ocupado.

| Escena | Mostrar y verificar |
|---|---|
| WEB-03, alta API | POST `/api/envios` autenticado como C1 con `api-alta.json`, publicación vigente;201,109 UYU, mismo ID visible en C1/A. No enviar ComercioId/precio inventado ni repetir POST incierto sin reconciliar. |
| DEP-02, discrepancia | DISCREPANCIA: observado distinto, Conforme=false, observación. Admitido/discrepancia pendiente, custodia Deposito, declarado intacto. Resolución D-P02 pendiente. |
| RUT-02, competencia | A1/A2 planifican el mismo envío auxiliar con recursos diferentes libres y una barrera concurrente: un éxito, un409, una sola parada activa. |
| EXT-01, configuración en caliente | HISTORIA-ANTES v1; publicar base Estandar120 y regla firma adicional; nuevo multibulto135 UYU. MULTI anterior115/reglas v1. Cotización antigua frente a publicación nueva da conflicto sin alta parcial. |
| EXT-02, conflicto offline | CONFLICTO R2/V2 aparte: cargar/salir online; offline registrar intento; A2 cancela antes de reconectar; sincronizar mismo sobre: **Conflicto**, Cancelado no se reactiva, evidencia/custodia conservadas. Resolver y rendir explícitamente. La entrega física concurrente con cancelación tiene conciliación especial, no sirve como negativo genérico. |
| EXT-03, prueba pendiente | PRUEBA: confirmar hecho sin foto→EntregaPendienteValidacion; **Completar entrega** con foto válida→Entregado. Foto truncada solo se ensaya por HTTP en fixture. |
| EXT-04, cancelación pública | Enlace legítimo y buzón controlado: pedir código, ver correo/marca, confirmar una vez y repetir sin duplicar. Bloqueada si no se consigue enlace legítimo en remoto. |
| EXT-05, push | Dispositivo real/FID/permiso/FCM autorizado, app cerrada sin force-stop; reasignación **antes de salida** avisa al custodio original. Observar aceptación,recepción,apertura,confirmación por separado. NoSend o simulación no acreditan push real. |

## Cierre con el cliente: alcance actual

Mostrar monitor/Grafana con rango temporal de la demo, métricas de latencia/errores/cola/sync/caché y una correlación de acción(TEC-02). Los perfiles de caché actuales son marca15min y publicación tarifaria6h. Consultar artefactos del CI, carga remota y dos API por release(TEC-03/04); no ejecutar carga ni provocar cortes sobre la reunión para mostrar un gráfico.

Explicar estos pendientes con claridad, sin navegar a pantallas inexistentes:

- Seguimiento público tiene estado/marca; faltan historial/ventana y existe el bloqueo remoto de recuperación del enlace.
- CU-26/27/28: faltan solicitud pública de reprogramación, avisos automáticos de estado y webhooks/suscripciones de comercios. Reprogramación del operador y correos de códigos tienen otro alcance.
- CU-29/30: faltan tablero de riesgo/flota en vivo SignalR, reportes y liquidaciones; tampoco hay cuenta corriente ni cierre diario agregado. `/flota`, Grafana y cierre móvil no los acreditan.
- Gestión general de incidencias y devoluciones desde Commerce es parcial. Kafka/Mongo existentes no acreditan por sí solos los opcionales de flota/replay e historial analítico.

Ver [cobertura por requisito](cobertura.md). Las brechas forman parte del resultado, no se ocultan con un check de éxito. La aceptación humana de los CU, la precisión vial y las decisiones D-P01/D-P02 siguen separadas de esta guía.

## Si algo falla durante la presentación

| Observación | Acción concreta |
|---|---|
|503 general| Revisar sesión/apagado, salud y responsable del entorno. No sustituirlo por local sin decirlo. |
|No aparece la hoja| Verificar APK/API/tenant/R1, fecha del operador y despacho; no crear otra jornada a ciegas. |
|No sale por faltantes| Comparar cuatro UUID y política; resolver carga, sin desactivar regla para pasar. |
|401/403| Verificar sesión/actor/permisos vigentes; renovar por flujo normal. No relajar RLS/seguridad. |
|Sincronización pendiente/conflicto| Conservar trabajo, distinguir transitorio de Conflicto y reintentar con IDs originales. Continuar solo escenas independientes. |
|Sin mapa/GPS/push| Mostrar dependencia y límite; pruebas simuladas no acreditan proveedor/hardware real. |
|Sin enlace público remoto| Registrar bloqueo Production y seguir depósito/reparto; no cambiar entorno ni fabricar token. |

Al terminar: restaurar red del Android, guardar manifest/resultados/evidencias privadas, registrar pendientes y coordinar el apagado remoto con el responsable para no cortar a otros. No borrar volúmenes, bases, cuentas ajenas ni cola móvil. La repetición usa un `run_id` nuevo y recursos/jornada disponibles.
