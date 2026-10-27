# Guía rápida: desplegar la demo

El despliegue se controla desde **NexoRuta/NexoRuta → Actions → “NexoRuta - publish images / manual VM controls”**. Elegí la rama `main`, pulsá **Run workflow** y seleccioná la operación.

| Operación | Qué hace | Cuándo usarla |
| --- | --- | --- |
| `start` | Comprueba el código actual de `main` en Backend, Frontend y Mobile; publica las imágenes; enciende Cloud SQL y las dos VMs; despliega y verifica la aplicación. También genera el APK Android como artifact. | Para iniciar una sesión nueva de pruebas. |
| `update` | Usa las últimas imágenes ya publicadas y actualiza las dos VMs por rotación. No enciende VMs apagadas. | Después de que el CI/publicación haya terminado y quieras aplicar esas imágenes. |
| `stop` | Apaga ambas VMs y Cloud SQL. Los datos se conservan para la siguiente sesión. | Al terminar de probar; también hay apagado automático al vencer las cuatro horas. |

Un push a `main` ejecuta CI y publica imágenes, pero **nunca enciende la VM**. Los cambios en los repos de Backend, Frontend y Mobile también notifican al repo madre para publicar. Esperá a que termine esa publicación antes de elegir `update`.

Cada combinación que pasa CI recibe un tag `integration-<run-id>-<intento>` en el
repo madre. En **Releases** aparece su prerelease cuando termina la publicación,
con el manifiesto de commits e imágenes. Al completar `start`, se adjuntan también
el APK firmado y sus checksums. Un tag sin prerelease puede indicar un build fallido;
`update` conserva la última publicación completa. Ver [el flujo de integración](integration-tags.md).

Para empezar: integrá los cambios en las ramas `main` de los repos, esperá la publicación y ejecutá `start`. En el resumen de esa ejecución están los endpoints y el artifact Android firmado para descargar. `monitor` muestra CPU, RAM, disco, latencia, errores y procesos; requiere una de las cuentas Google configuradas en el environment `nexoruta-demo`. El endpoint `mail` pide contraseña. Para cambios posteriores, esperá la publicación y ejecutá `update`. Al finalizar, ejecutá `stop`.

La identidad de GitHub Actions accede a GCP con OIDC; no configures claves JSON de GCP en GitHub. La configuración necesaria ya está en el environment `nexoruta-demo`.
