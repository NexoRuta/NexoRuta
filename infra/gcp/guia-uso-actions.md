# Guía rápida: desplegar la demo

El despliegue se controla desde **NexoRuta/NexoRuta → Actions → “NexoRuta - publish images / manual VM controls”**. Elegí la rama `main`, pulsá **Run workflow** y seleccioná la operación.

| Operación | Qué hace | Cuándo usarla |
| --- | --- | --- |
| `start` | Lee y fija la última release completa ya publicada; enciende Cloud SQL y las dos VMs; despliega esas imágenes y verifica la aplicación. | Para iniciar una sesión nueva de pruebas. |
| `update` | Usa las últimas imágenes ya publicadas y actualiza las dos VMs por rotación. No enciende VMs apagadas. | Después de que el CI/publicación haya terminado y quieras aplicar esas imágenes. |
| `stop` | Apaga ambas VMs y Cloud SQL. Los datos se conservan para la siguiente sesión. | Al terminar de probar; también hay apagado automático al vencer las cuatro horas. |

Un push a `main` ejecuta CI y publica imágenes, pero **nunca enciende la VM**. Los cambios en los repos de Backend, Frontend y Mobile también notifican al repo madre para publicar. Esperá a que termine esa publicación para que `start` o `update` puedan seleccionar esa release; ambos usan la última publicación completa si hay otra publicación en curso.

Cada combinación que pasa CI recibe un tag `integration-<run-id>-<intento>` en el
repo madre. En **Releases** aparece su prerelease cuando termina la publicación,
con el manifiesto de commits e imágenes. Un tag sin prerelease puede indicar un build fallido. Ver [el flujo de integración](integration-tags.md).

Para empezar: integrá los cambios en las ramas `main` de los repos, esperá la publicación y ejecutá `start`. En el resumen de esa ejecución están los endpoints y la release seleccionada. `monitor` muestra CPU, RAM, disco, latencia, errores y procesos; requiere una de las cuentas Google configuradas en el environment `nexoruta-demo`. El endpoint `mail` pide contraseña. Para cambios posteriores, esperá la publicación y ejecutá `update`. Al finalizar, ejecutá `stop`.

La identidad de GitHub Actions accede a GCP con OIDC; no configures claves JSON de GCP en GitHub. La configuración necesaria ya está en el environment `nexoruta-demo`.
