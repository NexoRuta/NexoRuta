# Integración de entrega parcial hacia develop

Corrección de NexoRuta/NexoRuta#73, NexoRuta/NexoRuta-Backend#48 y
NexoRuta/NexoRuta-Mobile#22. Frontend#49 ya está integrada. No se integraron PR,
no se hizo force-push ni se accedió a la VM/base real.

## Causas y correcciones

- Mobile: el build x64 del emulador contaminaba los locks compartidos sin RID.
  Selección por RID en todo el grafo; locks portables, arm64 y x64 versionados;
  locked-mode también en helpers locales. Android no impone su framework a los
  proyectos net10.0. CI restaura portable → Android arm64, compila APK, restaura
  x64 y vuelve a portable, exigiendo cero cambios de locks.
- Backend/navegador: el companion 5528cd9 no implementaba las rutas y el flujo
  esperados por las pruebas. Se fija el SHA integrado inmutable c7b69ba. Las
  cuatro pruebas CommerceCsvImportKestrelTests aprobaron con ese companion,
  conservando conflictos/reintentos y sin aumentar esperas. También se activan
  las pruebas optativas de navegador y se selecciona su configuración Release.
- Históricos: las fixtures bajaban desde el esquema actual, atravesando
  IndependentParcelProofDeadlines.Down. Ahora parten de bases aisladas en la
  migración pertinente. No se modificó ninguna migración ni su protección. La
  prueba de corte histórico usa columnas y función de cancelación de su época;
  no agrega columnas futuras ni falsifica __EFMigrationsHistory.
- Stage: el modelo de mantenimiento consultaba campos posteriores de bultos.
  Se amplía su proyección explícita, manteniendo el esquema Stage exacto, su
  autenticación, dominio, idempotencia y bloqueo de escritores normales.
- Tracking: el contrato vigente permite contadores agregados por bulto; la
  prueba exige una lista exacta de propiedades públicas y verifica valores y
  exclusión de códigos privados. No se agregaron datos de destinatarios,
  direcciones, identificadores de bultos ni motivos a la respuesta pública.
- Cancelación: el fallo de los siete casos estaba en el total de outbox, no en
  la versión del envío. El trigger produce un evento Kafka v2 OperacionActualizada.
  Se exige uno, su versión causal, el push opcional y que repetir el comando no
  duplique versión, historial ni outbox. Se conserva el incremento de una unidad.
- Escenarios de retiro/segunda visita: algunas operaciones de fixture usaban la
  llegada planificada como fecha física, posterior a su muestra GPS. Se corrige
  el reloj de la fixture; se conservan las reglas temporales y la admisión GPS.

## Comparación con develop

Estado remoto consultado antes de editar: Backend aeeab684, Mobile 683766d6,
Frontend c7b69ba0 y principal 9d805b65. Los heads originales de #48/#22/#73
coincidían con el diagnóstico recibido.

En otro checkout de Backend develop aeeab684 se reprodujeron 16 fallos de las
21 pruebas seleccionadas de las familias iniciales, y los cuatro fallos de
CommerceCsvImportKestrelTests con el companion antiguo. También se reprodujeron
los 12 fallos adicionales que el paso crítico de CI ocultaba en el shard 0:
fixtures de migración/base y reloj de retiro/segunda visita. Son bloqueos ya
presentes en develop; se corrigen para permitir la integración.

El NU1004 se reprodujo desde un clon limpio del Mobile original. Las cuatro
suites corregidas aprobaron desde otro clon, sin bin/obj y con directorios NuGet
nuevos: Core 36, Api 63, Storage 35 y Application 101.

## Preservación e integración

Los cambios de runtime se limitan al modelo explícito de mantenimiento Stage.
No se cambian recepción física, rendición, retorno/liberación de vehículo,
resultados aceptados, rechazo histórico, resolución vinculada, motivos por
bulto, reglas capturadas, versiones o idempotencia de los circuitos operativos.
Las pruebas de esos circuitos forman parte de los shards completos.

La planilla de develop coincide byte a byte con el ancestro común (SHA-256
fe1a0843dd8a7c5075414fc2796ab65c630e955b598edb123ce1840a1f9de389).
Se conserva íntegra la versión de entrega parcial (SHA-256
74c0beea12096c2e3fbf9013fe86c02c579881252509fb8450081e9ce2d75f21),
ZIP íntegro con sus 28 partes. No hubo edición binaria arbitraria. Se preservan
los cambios posteriores de develop en documentación, infraestructura y scripts.

Orden: Frontend#49 ya integrada → Backend#48 y Mobile#22 → principal#73.
Los gitlinks publicados exactos y sus repositorios están en
scripts/cloud/checkpoint.json y en el árbol Git de este commit. La integración
principal debe esperar los checks de los hijos y del conjunto. Las PR contienen
los enlaces de CI y la validación final; una ejecución fallida, cancelada o
impedida no se considera aprobada.

La ejecución local simultánea de shards agotó disco por copias VFS de Docker;
no se cambió cobertura ni se ocultó ese fallo. Se conservaron logs y se repitió
con menor concurrencia; CI remoto usa runners separados. El intento de instalar
SDK Android local encontró un JDK incompleto y validación TLS del instalador;
la compilación acreditada es la de GitHub Actions, desde checkout sin bin/obj y
sin hit de caché NuGet. No se realizó revisión visual ni instalación Android
en Cloud, ni se atribuye a Cloud la demostración manual previa.
