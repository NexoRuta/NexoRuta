# Entrega parcial: resultado ejecutado y guion de demostración

**Estado: circuito de dos visitas completado y comprobado, primero 1/2 y finalmente 2/2, mediante el cliente portable real y la API habitual.** Se rindió y recibió físicamente solo el pendiente, se conservó la primera entrega y se cerraron ambas jornadas con retorno/liberación explícitos. La interacción visual nativa Android sigue bloqueada y no se ejecutó; no se declara una demostración nativa completa.

## Datos nuevos del ensayo

| Dato | Valor |
| --- | --- |
| Envío | `01a1ae70-a111-79ca-b3f8-826660160e44` |
| Bulto 1 | `PARCIAL-B1-B43B7A`, 100 g |
| Bulto 2 | `PARCIAL-B2-B43B7A`, 100 g |
| Primera ruta | `01a1ae70-a220-7ee0-a46c-7a59a15f059a` |
| Primera jornada | `01a1ae70-a220-741d-a6fe-6238e3f11b15` |
| Fecha operativa | 05/11/2026, `America/Montevideo` |
| Repartidor | Identidad autorizada `demo@gmail.com`; sin cambiar ni cerrar la sesión de la aplicación nativa. |
| Vehículo | `PREDEMO01`, liberado previamente por el circuito normal. |
| Estado final | Envío `Entregado`, versión 7; ambos bultos `Entregado` y custodia `Destinatario`; dos rutas finalizadas y recursos liberados. |

## Política y preservación

Se verificó que no existía un borrador ajeno. Se publicó la versión **4**, clonando la política vigente y cambiando únicamente `intervaloEntreIntentosMinutos` de 60 a 1 mediante la API normal. Permanecen entrega parcial permitida, nueva visita sin recargo, tres intentos y las mismas pruebas/plazos/motivos. El nuevo envío conserva ese snapshot.

La lectura de PostgreSQL confirmó que el snapshot anterior de PREDEMO no cambió. No se modificaron su comando rechazado, sus versiones ni su historial. Tampoco se alteraron relojes, certificados, claves, datos del emulador ni otros ensayos.

## Verificación portable preparada

El ejecutable privado enlaza los componentes reales Core, Application, Api y Storage y los archivos reales `HojaRutaViewModel`/`EntregaViewModel`. Utiliza SQLite y archivos cifrados reales y una sesión portable cifrada, en un directorio ignorado independiente de la aplicación Android. Los secretos del host de prueba no equivalen a Android SecureStorage ni a biometría real.

El transporte mantiene `https://localhost:5843/`, confía específicamente en la CA existente y conserva la validación del nombre TLS. No contiene aceptación indiscriminada de certificados ni reescritura a HTTP. La interacción de escaneo se alimenta con códigos sintéticos encolados; GPS, cámara, firma y verificación local son sustitutos portables explícitos, no sensores nativos.

Compilación observada: `dotnet build .local/parcial-demo-20261105/e2e/Runner.csproj --no-restore --nologo -v:q` → **exit 0, cero errores y cero advertencias**.

## Primera visita: resultados ejecutados

Los modos `capture`, `sync-loss` y `sync` se ejecutaron en **tres procesos distintos**, todos con exit 0 y contra HTTPS verdadero con la CA existente. Los comandos reales de los ViewModels iniciaron jornada, escanearon/cargaron ambos bultos y confirmaron salida. Los acuses de carga del servidor devolvieron versiones **2 y 2**; esas mismas versiones llegaron a la proyección local y al nuevo sobre de entrega.

Con todo HTTP bloqueado, `EntregaViewModel` recibió un único código de escaneo: B1. B2 quedó sin escanear con motivo individual `AUSENTE`. Se completó el nombre exigido por el snapshot; esa política no exige foto ni firma, por lo que no se inventó una captura física. Se guardó una entrega pendiente en SQLite cifrado y terminó el proceso.

Un proceso nuevo recuperó la sesión cifrada y la cola, envió la entrega a la API real y perdió su respuesta de forma controlada después de recibir HTTP 200. Otro proceso recuperó el comando todavía pendiente y reenvió **exactamente los mismos bytes**, SHA-256 `00E3EC6B063E698371D484BED18A4A3BF46AB9079B9300D6C03A4A13B5006130`. No se editó ni reemplazó el comando.

| Evidencia | Resultado observado |
| --- | --- |
| Comando de entrega | `01a1ae79-bf4c-7221-b68e-057dca93f442`, secuencia 5, `Aplicada` |
| Comandos en base | Cinco IDs distintos, todos aplicados; una sola entrega persistida pese al reenvío |
| Pruebas de entrega | Una, asociada únicamente a B1 y a la primera ruta |
| B1 | `01a1ae70-a111-7d21-88ad-3d13a90b91a6`, `Entregado`, versión 4, custodia `Destinatario` |
| B2 | `01a1ae70-a111-7e90-ba01-c8a93258d5f1`, `Pendiente`, versión 3, custodia `Repartidor`, motivo `AUSENTE` |
| Envío | `EntregadoParcialmente`, versión 4, snapshot V4 conservado |
| Seguimiento público | HTTPS 200, 1/2, sin `bultoId` ni `operadorId` |
| Backoffice SSR autenticado | HTTP 200; ambos códigos, estado parcial y custodias diferenciadas en el HTML |
| Almacenamiento portable | SQLite sin cabecera plana y sesión cifrada recuperados entre procesos; nombre y comando durables |

La lectura SSR no es revisión visual. El transporte, los ViewModels y la persistencia se ejecutaron; no se afirma escáner, GPS, cámara, biometría ni navegación Android nativos. El checkpoint 1/2 se conservó para la comprobación del padre y quedó registrado antes de autorizar y ejecutar la segunda fase.

## Segunda visita y estado final: ejecutados

El comando real `Rendir` del ViewModel incluyó **solo B2** y `Finalizar` cerró la primera jornada. El Backoffice actualizado ofreció su formulario normal de recepción; se envió con autenticación, antiforgery y versión vigente, devolviendo HTTP 200 y confirmación de recepción. PostgreSQL confirmó B2 en depósito y que **toda la fila de B1 seguía idéntica** a la primera entrega. Se confirmó el retorno y se liberó el vehículo por las operaciones normales de flota.

La elegibilidad siguiente era **06/11/2026 01:30:36.8446995 UTC**; al planificar eran **01:34:51.620455 UTC**, todavía 05/11 en Montevideo. El minuto real ya había transcurrido: no hizo falta una espera adicional, no se alteró ningún reloj ni se omitió la comprobación.

| Segunda visita | Resultado |
| --- | --- |
| Ruta | `01a1ae7e-8d7f-7878-8187-68d96f96a0ee` |
| Jornada | `01a1ae7e-8d7f-7596-8725-527b80e4d07a` |
| Bultos incluidos | Únicamente B2: `01a1ae70-a111-7e90-ba01-c8a93258d5f1` |
| Ejecución | `HojaRutaViewModel`/`EntregaViewModel` reales: inicio, escaneo, carga, salida, identificación de B2, receptor, entrega y sincronización por TLS real, cierre de jornada. Exit 0. |
| Cierre operativo | Retorno y liberación explícitos después del cierre; sin carga pendiente ni ocupación activa. |

Contraste final observado:

- Envío **`Entregado`, versión 7**. B1 entregado versión 4 y B2 entregado versión 8; ambos en custodia del destinatario.
- Primera ruta e historial conservan B1+B2; la segunda contiene solo B2. Ambas rutas están `Finalizada`.
- **Doce comandos distintos**, todos `Aplicada`; exactamente dos comandos de entrega, uno por visita.
- **Dos pruebas**, una por bulto y visita. La prueba de B1 no se duplicó y su fila completa no cambió durante recepción ni revisita.
- Seguimiento público HTTPS **200, 2/2**, sin IDs internos de bulto u operador.
- Backoffice SSR autenticado **200** para ambas rutas, con estado final de entrega. Es comprobación de HTML, no revisión visual.
- PREDEMO conserva exactamente ruta, envío, snapshot, bultos y operación rechazada frente al estado posterior a la recuperación T3; su snapshot sigue sin admitir entrega parcial y sus bultos continúan en depósito.

La regresión de conflicto de versiones y resolución explícita corresponde a las pruebas dirigidas T2. No se fabricó un rechazo ni se modificó un comando aceptado en este nuevo caso exitoso.

### Identidad del recorrido almacenado en Android: contraste puntual

El diagnóstico nativo comunicado por el padre conservaba la ruta `01a1ae48-fb40-7f11-a283-65d2cbf0aa57` y jornada `01a1ae48-fb40-7512-afdd-d8e707d2a791`, cerrada y sin pendientes locales. Una consulta SQL de solo lectura confirmó que **ese recorrido pertenece a `correodemo@gmail.com`**, nombre `repartidor demo nico 2`, acceso `01a1ae44-cc6d-7da7-80a8-077378ea32e2`. No corresponde al acceso de `demo@gmail.com` que ejecutó las dos visitas portables.

Esto acredita al propietario en la base del recorrido observado por el padre; **no es una lectura directa ni un descifrado de la sesión Android**. No se cambiaron cuentas, diarios ni operaciones para hacer coincidir las identidades. La conectividad del APK y la interacción nativa deben seguir informándose aparte del circuito portable.

## Comandos ejecutados y continuidad

Los tres comandos siguientes **ya se ejecutaron** en procesos separados. Se muestran como evidencia reproducible, no para repetir `capture` sobre el diario existente. No recrear el envío ni borrar SQLite para resolver errores:

```powershell
$runner = '.local/parcial-demo-20261105/e2e/bin/Debug/net10.0/Runner.dll'
dotnet $runner 'C:\Users\Josec\NexoRuta' capture
dotnet $runner 'C:\Users\Josec\NexoRuta' sync-loss
dotnet $runner 'C:\Users\Josec\NexoRuta' sync
```

1. `capture` inicia por el ViewModel real, escanea/carga ambos, verifica las versiones confirmadas 2, bloquea **todo** HTTP y registra una entrega con un único escaneo, motivo `AUSENTE` en el otro bulto y receptor. Termina conservando trabajo pendiente en SQLite.
2. `sync-loss` reabre la misma sesión/SQLite y pierde de forma controlada la respuesta **después** de enviarla a la API real; el comando permanece pendiente localmente.
3. `sync` reabre otra vez y exige que el sobre reenviado tenga exactamente el mismo hash de bytes. Verifica ausencia de pendientes y que los acuses sean `Aplicada`, sin convertir conflictos en éxito.
4. Contrastar PostgreSQL, Backoffice SSR y seguimiento público **1/2**; conservar IDs/sobres y pruebas de ambas visitas.
5. Ejecutar el modo `close`: rendir únicamente el pendiente y cerrar mediante los ViewModels. Recibir físicamente el pendiente por la operación de depósito; confirmar retorno y liberación por separado.
6. Esperar el minuto real de elegibilidad de la política capturada. Planificar/despachar una segunda ruta que contenga solo B2, guardando sus datos en `e2e-state.json` como `visit2`.
7. Ejecutar `dotnet $runner 'C:\Users\Josec\NexoRuta' visit2 2`; verificar **2/2**, custodias finales y que la primera prueba/historia no se duplicó.

Los pasos 4–7 ya se ejecutaron y contrastaron en la segunda fase. No repetir los comandos de captura sobre estos diarios ni borrar su estado; para una nueva demostración crear otro envío con códigos únicos y conservar el historial existente.

Comandos adicionales observados, todos exit 0:

```powershell
dotnet $runner 'C:\Users\Josec\NexoRuta' close
python .local/parcial-demo-20261105/e2e/phase2.py receive-plan
dotnet $runner 'C:\Users\Josec\NexoRuta' visit2 2
python .local/parcial-demo-20261105/e2e/phase2.py release-final
python .local/parcial-demo-20261105/e2e/verify-final.py
```

## Guion para el profesor

Crear un envío nuevo de dos bultos bajo la política parcial vigente → cotejar ambos en depósito → planificar/despachar → obtener con el repartidor correcto → escanear ambos y confirmar salida → identificar solo B1 para entrega y marcar B2 `AUSENTE` → completar receptor/pruebas → sincronizar y mostrar 1/2 → rendir B2 y confirmar su recepción física → esperar elegibilidad → segunda visita con solo B2 → entregar/sincronizar y mostrar 2/2, conservando las dos visitas.

La captura offline con cierre/reapertura de proceso y pérdida de respuesta **ya fue comprobada con el cliente portable** y sus evidencias pueden mostrarse por separado. No presentarla como interacción nativa Android mientras no se haya ejecutado visualmente. Para mostrar la interfaz Android en directo sigue siendo necesaria la verificación visual nativa, sin borrar datos ni cambiar identidades a la fuerza.

## Evidencia privada reproducible

- `.local/parcial-demo-20261105/e2e-state.json`: checkpoints de creación, reglas, recepción y despacho.
- `.local/parcial-demo-20261105/e2e-prepared.json`: snapshot SQL inicial del caso nuevo.
- `.local/parcial-demo-20261105/e2e-preparation.json`: alcance completado y límites pendientes.
- `.local/parcial-demo-20261105/e2e-build.log`: compilación.
- `.local/parcial-demo-20261105/e2e-phase1-verification.json`: contraste de versiones/selección, reintento, cifrado, PostgreSQL, SSR y seguimiento 1/2.
- `.local/parcial-demo-20261105/e2e-partial.json`: snapshot de base tras la entrega parcial, con comandos y pertenencia a la ruta.
- `.local/parcial-demo-20261105/e2e-mobile-capture-1.json`, `e2e-mobile-sync-loss-1.json` y `e2e-mobile-sync-1.json`: checkpoints de los tres procesos.
- `.local/parcial-demo-20261105/e2e/wire-sync-loss-1.json` y `wire-sync-1.json`: sobres idénticos, sin cabeceras de autenticación.
- `.local/parcial-demo-20261105/e2e-final-verification.json`: resultado final 2/2, dos visitas, pruebas, recursos libres, SSR/público y preservación PREDEMO.
- `.local/parcial-demo-20261105/e2e-android-cached-route-owner.json`: relación SQL del recorrido almacenado comunicado por el padre con su propietario; sin secretos ni cambio de cuenta.
- `.local/parcial-demo-20261105/e2e-rendered-closed.json`, `e2e-partial-depot-received.json`, `e2e-second-visit-dispatched.json` y `e2e-final-released.json`: transiciones SQL de solo lectura.
- `.local/parcial-demo-20261105/e2e-receive-plan.log`, `e2e-visit2.log`, `e2e-final-release.log` y `e2e-verify-final.log`: comandos y resultados observados de la segunda fase.
- `.local/parcial-demo-20261105/e2e/`: fuentes del runner y su estado cifrado propio, sin tocar el almacenamiento Android.

Risk: none — esta unidad prepara datos sintéticos por operaciones normales y artefactos de verificación; no modifica código del producto. El cambio operativo autorizado de intervalo queda documentado y no altera snapshots previos.


## Correcciones de producto y causas

### Recepción de depósito

El bloqueo se reprodujo en el Backoffice vivo antes de corregirlo: PREDEMO estaba `EnTransito`, con ambos resultados pendientes y custodia `PendienteDeposito`, pero no existía una incidencia de cierre. La pantalla exigía esa incidencia mientras el repositorio admitía la recepción de los bultos rendidos.

`RutasModel.AdmiteRecepcion` ahora contrasta resultados y custodias de los bultos objetivo; no habilita indiscriminadamente todos los envíos en tránsito. Excluye entregados, exige todos los pendientes admisibles y rechaza los que siguen con el repartidor salvo una incidencia de cierre actual y coincidente en ID/versión. La recepción ya completada no se vuelve a ofrecer. `_Detalle` reutiliza el mismo criterio y `_Deposito` distingue declaración de rendición de recepción física.

La recepción PREDEMO se ejecutó con el formulario real autenticado y antiforgery: ambos bultos quedaron `Pendiente`/`Deposito`, versión 4. Su ruta ya estaba finalizada (versión100/secuencia94); no se volvió a cerrar. Retorno y liberación normales dejaron PREDEMO01 sin carga/ocupación activa. El envío conserva `EnTransito`, versión3: no se falsificó una entrega ni se alteró el snapshot antiguo que prohíbe parcial. Permisos/comando obsoleto dieron 403/409 sin cambios comerciales.

### Acuses, versiones y selección

- El ACK histórico inicial sin cambios de bultos puede contener mapa nulo/vacío. Se conserva la normalización preexistente del DTO, pero una nueva operación aplicada que sí cambia bultos exige sus IDs y versiones avanzadas; no se convierte cualquier respuesta defectuosa en éxito.
- La regresión reproduce el cliente histórico que persistió ACK truncado: se recuperan sus versiones mediante el **mismo sobre congelado/UUID** y la respuesta idempotente del servidor, únicamente en memoria. Ni el ACK ni el sobre histórico de SQLite se reescriben. En este ensayo nuevo se comprobaron acuses/proyección/payload con versión2 para ambos bultos. La cuenta local activa en Android no contiene la jornada PREDEMO; por tanto no se afirma haber leído sus antiguos ACK5/6 directamente del dispositivo.
- Se reprodujo que asignar motivo a un bulto ya escaneado no lo deseleccionaba y generaba `entregado=true` junto a `AUSENTE`. Ahora seleccionar motivo deselecciona entrega; volver a escanear limpia el motivo. El nuevo payload real fue B1=true/B2=false+AUSENTE.
- Una entrega rechazada ya no acredita hecho físico aceptado ni éxito pendiente de prueba. El conflicto queda explícito; el reintento exige decisión y genera nueva operación vinculada, sin mutar el rechazo. Una jornada cerrada/inadmisible no se reabre.
- El backend admite esa resolución de `EntregaBultos` con los guards compartidos de actor/ruta/envío/rechazo, sin repetir efectos. La verificación independiente detectó una regresión de texto de retiro; se corrigió y revalidó conservando exactamente el contrato anterior de `RetirarBultos`.

### Archivos: previos frente a nuevos

**Cambios anteriores conservados:** el normalizador de `ConfirmacionOperacion.cs`, diagnóstico de `SincronizadorJornada.cs` y log Android del catch en `HojaRutaViewModel.cs`; cinco `packages.lock.json` Mobile se preservaron byte por byte desde las copias del usuario, no desde Git. El Excel y los otros archivos locales previos no se sobrescribieron.

**Frontend:** `Features/Reparto/Pages/RutasModel.cs`, `Pages/Rutas/_Deposito.cshtml`, `Pages/Rutas/_Detalle.cshtml`, `tests/NexoRuta.ApiClient.Tests/RutasPagesTests.cs` y nuevo `DepotRendicionTests.cs`.

**Mobile:** recuperación/validación en `NexoRuta.Mobile.Application/SincronizadorJornada.cs`; proyección/estado en `Presentacion/HojaRutaViewModel.cs`, selección en `Presentacion/EntregaViewModel.cs`, metadata DEBUG de ACK en `Presentacion/PrincipalViewModel.cs`, confirmación compartida en `Captura/IInteraccionReparto.cs`/`InteraccionReparto.cs`, `EntregaPage.xaml`, `docs/cambios-31-41.md`; pruebas `ActualizarRecorridoTests.cs`, `EntregaBultosInterfazTests.cs`, `SincronizadorJornadaTests.cs`, nuevos `ParcialAcknowledgementTests.cs` y `ConfirmacionOperacionTests.cs`.

**Backend:** `NexoRuta.Infrastructure/Reparto/EfOperacionesRepartoRepository.cs` y `tests/NexoRuta.IntegrationTests/Reparto/OperacionesRepartoHttpTests.Cambios.cs`. Sin migración ni cambio de formato persistido.

## Pruebas y compilaciones efectivamente ejecutadas

| Tipo | Resultado |
| --- | --- |
| Frontend RED de recepción | 8 fallos de19 antes del arreglo; reproducía bloqueo y límites. |
| Frontend GREEN dirigido | 28/28. |
| Frontend conjunto de páginas/rutas/depot/recepción | 190 aprobadas, 5 omitidas de195; log `frontend-suite.log`. Las omisiones incluyen navegador opt-in: no equivalen a revisión visual. Un primer filtro por nombre de archivo no encontró pruebas y se descartó. |
| Mobile sincronizador | 27/27; DTO2/2; selección por comandos públicos1/1. RED previo observado4/4. |
| Backend parcial/resolución/regresiones | 7/7 dirigidas y retiroC37 existente1/1; resolución nueva fallaba RED antes del arreglo. |
| Verificador independiente | Mobile27+DTO2; Frontend25+3; Backend5 pruebas producto, detectó B1 de texto antiguo. Tras único lote correctivo, recheck exclusivo2/2 con estado y ACK idempotente conservados. |
| Spot-check padre posterior a B1 | 2/2 resoluciónEntrega+mensaje/estado/reintentoRetiro; `backend-b1-parent-spot.log`. |
| Circuito real | Preparación, parcial, captura offline, reapertura de procesos, respuesta perdida/reintento, rendición/recepción, revisita2/2 y liberación, todos contra API habitual/BD existente. Sin SQL de escritura comercial. |
| Builds | API y APK x86_64 exit0. Advertencias existentes NU1510 y XA0141 de bibliotecas nativas Mapbox/16KB; sin cambiar dependencias. |
| Check de diff | Backend, Frontend y Mobile sin errores de whitespace. |

Los fixtures de pruebas independientes usan estado PostgreSQL/PostGIS desechable propio y proveedores controlados; no sustituyen el circuito real descrito arriba. Los cinco casos omitidos y el bloqueo CUA no son aprobaciones.

## Entorno realmente aplicado

| Repositorio | HEAD de base, con cambios locales compilados |
| --- | --- |
| Principal | `4e5c233dc751736ed59cc234582f157f5c9c278a` |
| Backend | `09538d989399b511473ad5af063754ea76d554a6` |
| Frontend | `d328e98c27db7c5cef018ab3492c54fc563eed49` |
| Mobile | `683766d6d8cd6c1bd9ce45bb12f6581ddb19b98c` |

No se hizo checkout/reset, commit, merge ni push. Estos SHA **no identifican por sí solos los cambios locales**: los manifiestos de build y los diffs distinguen las fuentes utilizadas.

- API actual: `nexoruta-api:parcial-demo-20261105`, imagen `sha256:d5d886191cc5e2564705e5b93fa5418c45cee89761404d410b49ec6c6d2ed426`; HTTP5000 y HTTPS5843 con CA validada devolvieron200 después de la corrección final. Solo se recreó API; sin seeds/migraciones/otra base.
- Backoffice real utiliza fuente montada y `dotnet watch`/polling. El formulario corregido se ejecutó en5101, sin recrear servicios ajenos.
- Se preservaron todas las capas privadas Compose; cadena efectiva en `.local/parcial-demo-20261105/compose-command.json`. No publicar su contenido ni claves. `environmentExactlyPreserved`/`mountsExactlyPreserved` comprobados en el resultado de despliegue.
- Respaldo PostgreSQL consistente previo a recuperación, decodificado y validado: `.local/parcial-demo-20261105/backup/20261106T010545Z/postgres-before-recovery.dump`; SHA256 `d467047f3dd55a254377a96a27637d6729c0a9cb12b31c57c3ec923ada495731`.
- Host05/11 Montevideo y emulador06/11 GMT representan el mismo instante. La fecha operativa05/11 se obtuvo sin cambiar relojes. No confundir UTC con fecha comercial.

## Android instalado: evidencia separada

Se utilizó únicamente **f7a-qa-api36 / emulator-5554 / x86_64**, dentro de Android Studio; no se inició otro emulador.

- APK anterior SHA256 `cb3634935be075c4a43f401b5cff2c3502501efdb87e396fa3a22290424b7796`.
- Compilación e instalación real `adb install -r`: **Success**. APK extraído después de instalar coincide con el compilado: SHA256 **`4df28b95a7a2802fbdfaa90b3609ea94f39a985fe1690d4a6bdcceab0092a253`**, versión1/1.0, target36.
- Certificado antes/compilado/después idéntico: `41ff9ffbcad5c0ac6edfd2a9d6d42e9b8e801b8678da375d6012b465a67463c7`; UID **10217** antes/después.
- Se detuvo el proceso y se respaldaron `files` y `shared_prefs` en directorio privado AppData. **754 archivos persistentes idénticos byte por byte antes/después de instalar, antes de abrir**; sin desinstalación, borrado ni Wipe Data.
- Antes de la apertura se consultó el diagnóstico histórico y se retiró temporalmente únicamente el reverse5843 para impedir sincronización durante la inspección. La nueva inicialización confirmó `local_work.pending=False` y tokens locales presentes. Se restauró reverse5843 y la app quedó abierta.
- Diagnóstico del **cliente TLS de la propia aplicación**, posterior al despliegue final: `probe=6d1dda37-9f07-47f2-b309-645f4d8fd250;origin=https://localhost:5843/;status=200`.
- HTTPS/red **comprobados nativamente**. Autenticación/consulta de rutas nativa después de instalar: **no verificada**. Tokens presentes no equivalen a sesión aceptada. El caché observado pertenece al recorrido de `correodemo@gmail.com`; no se cambió la identidad para hacerlo coincidir con el ensayo `demo@gmail.com`.
- El helper inicialmente falló bajo redirección combinada de stderr en PowerShell5 al recibir el diagnóstico exitoso de nginx. Ejecutado directamente terminó exit0; no se cambió el helper ni se desactivó TLS. Reverse y conectividad quedaron restaurados.

APK: `C:\Users\Josec\AppData\Local\NexoRuta\parcial-demo-20261105\android-build-20261106T012633Z\bin\NexoRuta.Mobile\debug_net10.0-android_android-x64\uy.nexoruta.repartidor-Signed.apk`.
Evidencia privada: `android-install-result.json`, `android-current-diagnostics.log`, `final-preservation-and-native.json`, `android-build-result-20261106T012633Z.json`, `b1-api-result-20261106T013810Z.json`, bajo `.local/parcial-demo-20261105/`.

## Pendientes concretos para la demostración nativa

1. El permiso de control visual de Android Studio fue denegado. No se sustituyó por taps, teclado ni capturas de pantalla ADB. Cámara/escáner/firma y navegación Android no se acreditan mediante el runner portable.
2. Revisar con el usuario la identidad de la cuenta abierta antes de ingresar como `demo@gmail.com`: el caché actual corresponde a otro repartidor. No cerrar sesión con descarte, no borrar diarios y no imponer un cambio de cuenta. Las credenciales autorizadas de demo funcionaron por API; no falta inventar/restablecer contraseña.
3. Con permiso nativo y la identidad acordada, repetir el guion con **otro envío nuevo**: obtener ruta autenticada; escaneo real de carga y de soloB1; motivo individualB2; receptor/pruebas que exija su snapshot; captura offline y cierre/reapertura **Android** antes de sincronizar; recepción físicaB2 y revisita soloB2. Mostrar1/2 y2/2. Estos pasos no deben declararse ya ejecutados nativamente.
4. Verificar visualmente la acción de depósito, teclado/foco y mensajes de conflicto en navegador. El HTML autenticado y la automatización de páginas sí se comprobaron; revisión visual/accesibilidad no realizada.
5. Revisión nativa RDD: Mobile autorizada, ejecutada en cuatro lentes, corregido R2 en un único lote y validado; aprobación reconocida y autoridad consumida. Backend recibió consentimiento separado y su revisión terminó aprobada, sin nuevos hallazgos. Frontend devolvió `rdd_disabled`; se respetó el modo deshabilitado sin iniciar revisión ni cambiar preferencias. Ningún candidato hereda consentimiento o aprobación de otro.

La memoria Engram no tiene sesión host registrada: no se intentan más escrituras atribuidas ni se inventa session_id. El registro local `odd/tasks/parcial-demo-20261105.md` conserva el avance y su espejo permanece pendiente.

**Conclusión:** entrega parcial y segunda visita implementadas y ejecutadas contra el entorno real mediante cliente portable/HTTP/SSR/SQL; bloqueo de recepción corregido y recuperación PREDEMO completada. APK actualizado y HTTPS nativo comprobado. **No se declara lista una demostración Android completa** hasta resolver los pendientes nativos y de identidad indicados.

Risk: items 3/4 — contrato compartido de resolución y orden causal de acuses/versiones. Sin migración ni reescritura de diarios históricos.


## Revisión Mobile autorizada y corrección R2 — 05/11/2026 23:01

El usuario eligió **1 — Revisar este cambio** para el candidato Mobile. Los cuatro lentes inspeccionaron las fuentes inmutables. Riesgo, resiliencia y fiabilidad no establecieron bloqueos nuevos; legibilidad encontró **R2-user-facing-diagnostic**: el catch mostraba al repartidor el volcado técnico de IDs/versiones del acuse inválido.

Se conservó la excepción detallada preexistente en `SincronizadorJornada.cs` y su diagnóstico Android. Solo se corrigieron los mensajes de los dos caminos de `HojaRutaViewModel`; Android mantiene `NexoRuta.Sync` y el host portable usa `Trace`. El texto de pantalla explica que no pudo actualizar, que los datos se conservan y cómo reintentar. No confirma ni elimina operaciones ante el error.

El único lote correctivo cambió tres archivos: `HojaRutaViewModel.cs`, `ActualizarRecorridoTests.cs` y `mobile/docs/cambios-31-41.md`. El nuevo test parametrizado por actualización/directo falló **2/2 RED** con el dump visible; después pasó **2/2 GREEN**, con cola y operaciones intactas. El conjunto dirigido pasó **29/29**; tras el ajuste de logging portable el check final2/2 volvió a pasar sin las advertencias CS0168 transitorias. Un primer intento `--no-restore` en un artifacts nuevo falló por assets ausentes; no se contó como RED funcional y se reutilizaron los assets externos existentes.

La validación nativa dirigida al único hallazgo aprobó el candidato corregido. Se ejecutó exactamente el reconocimiento devuelto: `gentle-ai.review-acknowledged/v1`, `action=acknowledged`, `authority=burned`. Linaje `review-77b72a89d4802b2c`, candidato final `sha256:69f8214d9e3d3d12d595f202a95842a228e062c827f77f505b3ff1d9cb0bfa42`. Evidencia íntegra en `.local/parcial-demo-20261105/mobile-review-closed.json`.

**La revisión nativa es inspección estática/validación dirigida de fuentes; no ejecutó pruebas ni acreditó Android visual.** Sus conclusiones no sustituyen las pruebas ejecutadas por separado ni autorizan commits/push/publicación.

### APK vigente después de R2 — sustituye al APK inicial indicado arriba

- Helper Android exit0; un único APK firmado x86_64 en `C:\Users\Josec\AppData\Local\NexoRuta\parcial-demo-20261105\android-build-20261106T015357Z\bin\NexoRuta.Mobile\debug_net10.0-android_android-x64\uy.nexoruta.repartidor-Signed.apk`.
- **SHA256 instalado vigente: `c065a6bba39387eac6b73f8ec05b487e1fefe31b53923023caf3677a6404fee4`.** Se extrajo de nuevo desde Android y coincide con el construido. `adb install -r` devolvió Success.
- Certificado idéntico, UID10217 y **754 archivos persistentes idénticos byte por byte antes/después de esta segunda instalación**, antes de abrir. Se generó un respaldo privado nuevo; no se sobrescribió el anterior.
- Antes de permitir red, nueva inicialización Android: `local_work.pending=False`, tokens presentes. Reverse5843 restablecido, app abierta en el mismo AVD/Android Studio.
- HTTPS mediante el cliente de la app: `probe=a056a6f4-60e2-442d-a82c-0cbff5d01720;origin=https://localhost:5843/;status=200`.
- Excel y cinco lockfiles vuelven a contrastarse idénticos a sus baselines. No hubo operaciones comerciales nuevas durante revisión/corrección/instalación; el caso real final sigue documentado2/2.

Evidencias nuevas bajo `.local/parcial-demo-20261105/`: `r2-red.log`, `r2-green.log`, `r2-final-green.log`, `android-build-result-20261106T015357Z.json`, `r2-build-preservation-final-20261106T015357Z.json`, `android-install-r2-result.json`, `android-r2-diagnostics.log`, `r2-final-preservation-and-native.json` y `mobile-review-closed.json`.

Permanecen **sin verificar** la consulta autenticada de rutas posterior a instalar, navegación/escaneo/cámara/firma/offline-reapertura Android y revisión visual del Backoffice. Permiso visual denegado; no se cambió la cuenta ni se automatizó pantalla mediante ADB. El pendiente de identidad se mantiene tal como se explicó antes.


## Cierre de revisión Backend y estado Frontend

El usuario respondió nuevamente **1**, autorizando únicamente la revisión del candidato Backend de dos archivos/65líneas. Se ejecutaron concurrentemente los tres lentes devueltos —riesgo, resiliencia y fiabilidad— sobre los parches inmutables. **Los tres retornaron sin hallazgos**. Se admitió la aprobación y se ejecutó exactamente su reconocimiento: `gentle-ai.review-acknowledged/v1`, `action=acknowledged`, `authority=burned`, linaje `review-26ab8e46947f6dcd`, candidato `sha256:85c1a23741310567af4152d2c7e47a876e744fe475eea1002ab43574cf9eb824`.

No se hizo otra corrección, build ni despliegue Backend durante esta revisión porque sus fuentes no cambiaron. La revisión fue estática: las pruebas ejecutadas siguen acreditadas por sus logs anteriores, no por una afirmación de los revisores. Evidencia completa: `.local/parcial-demo-20261105/backend-review-closed.json`.

El preflight independiente de Frontend devolvió **`rdd_disabled`**. Se conservó esa preferencia efectiva; no se habilitó RDD, no se lanzó una revisión ni se fabricó una aprobación. Estado: **disabled/unmanaged**, con pruebas dirigidas e independientes y recepción SSR efectiva documentadas arriba. Evidencia: `.local/parcial-demo-20261105/frontend-review-disabled.json`.

Por tanto, el estado final de revisión es: **Mobile aprobada después del único lote R2; Backend aprobada sin nuevos hallazgos; Frontend deshabilitada/no revisada nativamente**. Esto no cambia los límites de demostración Android: HTTPS nativo200 comprobado y APK actualizado; interacción, autenticación/consulta de rutas y reapertura offline Android permanecen sin verificar por el impedimento visual y la diferencia de identidad ya documentados. Sin commits, push, merges ni operaciones comerciales adicionales durante las revisiones.


### Archivo de pruebas y limpieza de temporales

Se copiaron **38 archivos de evidencia** (logs/TRX/hashes del ejecutor y verificador) a `.local/parcial-demo-20261105/verification-logs/`, conservando subdirectorios `t2`, `independent` y `b1-recheck`. Los logs Frontend ya estaban en el directorio privado de la tarea. Así no dependen exclusivamente de TEMP.

El intento de limpieza de cuatro directorios temporales propios fue rechazado por la política del runtime antes de ejecutarse. No se reintentó la eliminación por otra herramienta ni se modificó la política. Se conservaron los directorios, listados exactamente en `.local/parcial-demo-20261105/scratch-archive.json`. Esto es únicamente limpieza pendiente; no altera el resultado funcional, los datos protegidos ni el estado de los servicios.
