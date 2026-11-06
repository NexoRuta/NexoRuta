# Android: actualización conservadora y límites de la auditoría

Se compiló e instaló el gitlink Mobile `683766d6d8cd6c1bd9ce45bb12f6581ddb19b98c` sobre la aplicación existente. No se desinstaló, borró almacenamiento ni ejecutó Wipe Data. La aceptación interactiva de la versión actualizada queda **bloqueada**, no aprobada: el control de aplicaciones denegó acceso al emulador.

## Preparación y comprobaciones ejecutadas

| Comprobación | Resultado efectivo |
|---|---|
| Dispositivo inicial | No había emulador iniciado ni dispositivos ADB. Se inició el AVD existente `f7a-qa-api36`, serial `emulator-5554`, x86_64. |
| Arranque | Arranque en frío con `-no-snapshot-load -no-snapshot-save`, sin modificar ni borrar el disco persistente. |
| Cámara | Configuración existente conservada: trasera `webcam0`, frontal `none`. Esto no acredita captura ni lectura de códigos. |
| Protección frente a sincronización antigua | Antes de abrir la app anterior: sin reverse y Wi-Fi/datos deshabilitados. Se usó **Continuar sin conexión**, sin ingresar credenciales ni pulsar Actualizar. |
| Pendientes de la identidad activa | Diagnóstico nativo existente `NexoRuta.Session`: `local_work.pending=False`; jornada `01a1aa09-9b84-7f85-b6ae-fd736d59dd16`, ruta `01a1aa09-9b84-7f67-9fc4-14fef5a82376`, fecha 05/11/2026, `local_closed=True`, `local_pending=False`. No se descartaron ni sincronizaron operaciones. |
| Reapertura anterior offline | Se leyó la hoja finalizada: 2/2 bultos cargados y 1/1 entrega confirmada. Corresponde a la app **anterior**, no a una nueva entrega de esta auditoría. |
| Respaldo antes de instalar | Copia cifrada de `files/operacion` y `shared_prefs` en `%LOCALAPPDATA%\NexoRuta\auditoria-excel-20261105\android-preservacion\before.tar`; sin exportar claves a los informes. Se conservaron las cuatro bases por cuenta. El diagnóstico de pendientes corresponde a la identidad activa; no se pretende haber descifrado las otras cuentas. |
| Compilación | Helper inspeccionado `mobile/tools/local/compilar-emulador.ps1 -Serial emulator-5554 -ArtifactsDirectory <directorio privado de esta auditoría>`: salida 0, Debug, net10.0-android, android-x64, assemblies embebidos, CA y configuración Mapbox existentes. |
| Advertencias | Tres XA0141 de bibliotecas Mapbox y páginas nativas de 16 KB. La compilación y actualización fueron exitosas; no se convierten en bloqueo funcional general. |
| Firma | SHA-256 del firmante anterior y construido idéntico: `41ff9ffbcad5c0ac6edfd2a9d6d42e9b8e801b8678da375d6012b465a67463c7`. |
| Instalación | `adb -s emulator-5554 install -r <APK construido>`: `Success`. Mismo paquete `uy.nexoruta.repartidor`, appId/UID `10217`, versionName `1.0`, versionCode `1`, actualización 05/11/2026 18:36 UTC. La versión comercial no identifica el commit; se registra arriba el SHA compilado. |
| Datos tras instalar, antes de abrir | Los seis archivos persistentes respaldados —cuatro SQLite y dos preferencias— conservan exactamente tamaño y SHA-256. `android-preservacion-final.json`: `identical=true`. |
| Conectividad preparada | Helper inspeccionado `reconectar-emulador.ps1` **sin** `-ProbeApp`: gateway habitual 5843 hacia API5000, CA/SAN validados, `adb reverse tcp:5843 tcp:5843`. Se restauraron Wi-Fi/datos. No se desactivó TLS ni se aceptaron certificados indiscriminadamente. |

El restore de MAUI produjo un cambio automático de `packages.lock.json`. Se conservó una copia privada de ese efecto y se repusieron únicamente los bytes originales de ese archivo —que estaba limpio al inicio—, sin modificar código ni dependencias del producto.

## Bloqueo interactivo exacto

El control visual devolvió `Computer Use was not approved to use qemu-system-x86_64`. También falló el acceso al navegador: `The browser access host is unavailable` y `Computer Use was not approved to use Brave`. Se solicitó habilitación durante el trabajo; no se eludió la denegación con otro controlador.

La app actualizada quedó detenida después de instalar. No se ejecutó su recorrido, cámara, escáner ni firma bajo la versión actualizada. **No usar los tests portables como sustituto de estas pruebas nativas.** Los XML `android-old-*.xml` y `android-pending-check.xml` son evidencia ADB de lectura de la versión anterior offline, no capturas de aceptación de la nueva.

## Comprobación manual pendiente

1. Habilitar el control del emulador o efectuar el recorrido manualmente; mantener `emulator-5554` y la firma existente.
2. La ruta sintética preparada es `01a1ad02-7fe9-71e6-8007-c637e5b86d2a`, con cuenta separada en el archivo privado de la auditoría. **No cerrar sesión, borrar hojas ni limpiar almacenamiento para cambiar a esa cuenta.** La app protege el cambio de identidad cuando conserva hojas/jornadas; primero comprobar un mecanismo normal de cambio que preserve el trabajo anterior, o preparar expresamente una ruta sintética para la identidad existente sin reutilizar su operación cerrada. Si no es posible sin descartar datos, detener esa prueba y dejarlo documentado. No reutilizar `01A1AA`, la planificación de Nico del 09/11 ni `CU06-LOCAL-V`.
3. Comprobar ingreso, descarga y carga normal por escáner. Si se prueba el lector con webcam, mostrar un código sintético: escribir el código manualmente no acredita cámara/decodificación.
4. Realizar captura de foto y trazo de firma; comprobar previsualización, validación, guardado, cierre del proceso y reapertura con evidencia conservada.
5. Ejecutar una entrega parcial y un retiro offline de cantidades normales; reabrir antes de reconectar. Verificar cola, ACK durable, persistencia y vistas de ambos portales después de sincronizar.
6. Verificar custodia, rendición física y liberación por separado. No inferirlas del cierre de la jornada.

## Evidencia relacionada

- `android-pendientes-preactualizacion.json`: resumen seguro del diagnóstico previo.
- `android-install.json`: APK y firma efectivamente instalados.
- `android-preservacion-inicial.json`, `android-preservacion-final.json`: integridad de archivos persistentes.
- `test-mobile-*.log`: pruebas portables nuevas; no son evidencia Android nativa.
