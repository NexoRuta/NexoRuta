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

## Probar develop en GCP

En main y develop, start y update aplican primero el módulo bootstrap desde su estado remoto GCS (prefijo foundation), antes de sincronizar integraciones y desplegar la demo. Esto aprovisiona las nuevas identidades, secretos y permisos declarados en la revisión seleccionada. El plan conserva el presupuesto opcional existente y bloquea eliminaciones o reemplazos de recursos; si falla, no continúa el despliegue. Stop omite este paso para conservar su capacidad de apagado.

La instalación inicial del proyecto, bucket/estado remoto y la identidad WIF sigue usando scripts/gcp/setup.ps1: el workflow necesita esos recursos para autenticarse. No utiliza archivos de configuración ni credenciales del Windows del operador.

En **Run workflow**, seleccione la rama `develop`. `start` o `update` construye y despliega los commits fijados en el root y sus gitlinks en el canal privado `develop`; no ejecuta el Integrated CI. Despues, inicie `NexoRuta - pruebas de carga` desde `develop`. Para el camino publicado y probado, seleccione `main`. Ambos canales comparten VMs y Cloud SQL, por lo que las migraciones de `develop` quedan en la base compartida.
