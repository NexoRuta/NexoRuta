# Backoffice: BadImageFormatException al abrir Envíos

02/11/2026. Incidente de ejecución local resuelto con reinicio completo. No cambia CU06 ni las reglas de destino.

## Evidencia y reparación

Los logs previos registran `System.BadImageFormatException` en `System.Reflection.CustomAttribute.IsCustomAttributeDefined` durante construcción de metadatos de System.Text.Json: `ApiHttp.SendAsync<T>` → `EnviosApiClient.ListarEnviosAsync` → `IndexModel.OnGetAsync`, línea91. La API había devuelto200; no era falta de permisos, base ni respuesta vacía. El proceso llevaba alrededor de una hora activo.

Se conservaron logs completos antes/después, metadatos del contenedor y estado Git en carpeta privada con ACL `%LOCALAPPDATA%/NexoRuta/backoffice-runtime/20261102-000541`. Se ejecutó `docker restart nexoruta-backoffice`: termina/recrea PID1, dotnet-watch y sus hijos. El arranque existente recompiló Backoffice y ApiClient dentro del contenedor Linux con su salida exclusiva `/tmp/nexoruta-artifacts`, fuera de bin/obj de Windows. Build correcto, sin errores; advertencias previas NU1510 y CS8629. No se limpiaron artefactos ni se tocaron fuentes porque el fallo dejó de reproducirse tras ese reinicio/recompilación normales.

SDK10.0.401, Microsoft.NETCore.App y AspNetCore.App10.0.12, x86_64. [Rutas y hashes efectivos de los artefactos](evidencias/backoffice-runtime/assemblies.txt): ApiClient compilado y copia en salida Backoffice son idénticos. Esto identifica la salida usada por el arranque actual, no prueba retrospectiva del ensamblado/metadato que estaba defectuoso dentro del proceso anterior.

**Límite del diagnóstico:** Hot Reload estaba habilitado antes y permanece habilitado después; ahora el listado funciona. Es compatible con estado de ejecución obsoleto, pero no se demostró que Hot Reload lo causara ni se identificó un tipo corrupto concreto. No se atribuye a arquitectura/bitness/dependencias sin evidencia. No fue necesario arrancar con --no-hot-reload ni introducir un workaround permanente. Si vuelve a reproducirse, conservar proceso/logs y comparar arranque limpio con --no-hot-reload antes de atribuir causalidad.

## Verificación funcional real, no health check

Chromium autenticado en la instancia habitual con la cuenta operativa local configurada: **GET http://localhost:5101/ →200**, título Envíos recibidos,31 resultados y10 filas de la primera página, sin excepción ni mensaje de fallo de consulta. Capturas inspeccionadas [escritorio](evidencias/backoffice-runtime/envios-1440.png) y [320px](evidencias/backoffice-runtime/envios-320.png). Se repitió navegación autenticada después del reinicio y siguió pasando.

**Diferencia de URL comprobada:** `http://localhost:5101/envios` devuelve404, no BadImageFormatException. El checkout publica Envíos mediante `Pages/Index.cshtml`, `@page` sin plantilla, en `/`; el menú usa esa página y no hay AddPageRoute para `/envios`. No se agregó un alias ni se modificó navegación para reparar una excepción de runtime. Usar la entrada Envíos o la URL raíz.

Commerce habitual5102: GET del destino propio200 y reapertura en Chromium320 muestran la dirección y el punto confirmados; sin vista previa/bloqueo temporal. La prueba inicial esperaba texto sintético de una ejecución anterior; comprobó que el usuario ya había editado ese destino (versión3). Se corrigió la expectativa leyendo el GET actual, sin restaurar/sobrescribir datos. [Resultado](evidencias/backoffice-runtime/result.json), [captura de reapertura](evidencias/backoffice-runtime/selector-reopen-320.png). Se bloquearon solicitudes externas: el mapa muestra error de carga esperado por ese bloqueo, no se afirma revisión de tiles reales.

Selección/ajuste/confirmación/guardado y conflictos permanecen cubiertos por la [verificación PostgreSQL/Mapbox controlado anterior](../geocodificacion/03-selector-guardar-reabrir.md). En esta intervención no se reenviaron confirmaciones ni búsquedas ni se repitieron esas suites; no hubo cambios de código. `permanent=false` permanece en el adaptador, sin tocar B1–B5, proveedor vial o límites.

## Preservación y estado final

Sin cambios a DTOs/contratos, permisos/RLS, fuentes, base, migraciones o datos del negocio; solo autenticaciones y lecturas para comprobar las páginas. Sin commits, ramas, push ni remoto. Git inicial/final idéntico antes de añadir esta documentación. API, Backoffice y Commerce quedan funcionando. No se devuelve una lista vacía ni se captura/silencia la excepción.

Revisión nativa pendiente, fallo de arquitectura previo y precisión vial no validada siguen pendientes; este reinicio no los resuelve ni cierra CU06. Engram sin identidad runtime registrada: trazabilidad local, sin escritura atribuida de memoria.

Risk: item5 (reinicio local de servicio); sin cambio de código ni datos de negocio.
