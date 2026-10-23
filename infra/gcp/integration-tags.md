# Versiones automáticas mediante tags de integración

Cada integración publicada se identifica con un tag anotado del repo madre:
`integration-<GITHUB_RUN_ID>-<GITHUB_RUN_ATTEMPT>`. No se abre una PR ni se hace
un commit automático sobre `main` o `develop`.

## Secuencia

1. Un push al `main` del madre o la notificación de un componente solicita publicar.
   `start` manual también solicita probar y publicar antes de iniciar la sesión.
2. CI resuelve una sola vez los `main` de backend, frontend y mobile. Sus tres SHAs
   se reutilizan para todas las pruebas de aplicaciones y Cloud SQL.
3. Solo si todos los jobs de CI terminan bien, se crea un commit de integración
   cuyo padre es el commit exacto del madre que ejecutó CI. Únicamente cambian los
   tres gitlinks de submódulos; infraestructura y configuración conservan sus bytes.
4. Se publica un tag anotado sobre ese commit. Los reintentos sobre el mismo tag
   aceptan solamente el mismo commit; nunca se usa force push ni se mueve un tag.
5. El build hace checkout del tag con sus submódulos y comprueba sus SHAs. No vuelve
   a resolver ramas de componentes. Las seis imágenes se publican por digest y el
   manifiesto incluye `integration_tag`, `root_sha`, `sources` y `publication_order`.
6. Después de publicar imágenes y assets se crea una **GitHub prerelease** con ese
   tag y el manifiesto completo en sus notas. No se marca como release estable/latest.
7. `start` despliega esa release. Su APK se construye con el mobile fijado en el tag,
   se guarda en el artifact de Actions y se adjunta a la GitHub prerelease con sus
   checksums. Si Android falla, la release de imágenes sigue existiendo sin APK.

El tag significa **código probado**. La GitHub prerelease significa **imágenes y
bundle publicados**. Ninguno de los dos significa que una VM esté encendida ni
que el despliegue haya terminado correctamente. Si el build falla después de CI,
queda el tag probado, pero no se publica una nueva GitHub prerelease.

## Ejecuciones simultáneas y reintentos

El canal privado `channels/main.json` cambia únicamente después de publicar las
seis imágenes y sus assets. La escritura utiliza una precondición de generación
de Cloud Storage: ante una colisión, se vuelve a leer el objeto antes de intentar
actualizarlo. La pareja `(GITHUB_RUN_NUMBER, GITHUB_RUN_ATTEMPT)` impide que una
publicación antigua, aunque termine después, reemplace una más reciente. Su tag
y release pueden conservarse para inspección, sin convertirse en la versión del canal.

Se admiten las releases previas sin tag para que `update` pueda seguir usando la
última publicación válida durante la transición. La primera publicación nueva
agrega el tag y la información de orden al canal. Los números de ejecución se
comparan dentro del mismo workflow `demo-vm.yml`; no publicar ese canal desde otro
workflow con una numeración independiente.

`update` selecciona una sola release completa del canal. No prueba ni compila de
nuevo y no modifica la duración de la sesión. `stop` no necesita crear tags.
Los pushes de tags no son un trigger del workflow, por lo que no generan bucles;
los jobs continúan en la misma ejecución que los creó.

## Permisos y operación

El job `integration` necesita `contents: write` únicamente para publicar el tag.
`github_release` lo necesita para crear la prerelease y Android para adjuntar el
APK. El resto conserva permisos de lectura sobre GitHub. Ninguno modifica ramas.
Las reglas del repositorio deben permitir al token de Actions crear tags con el
prefijo `integration-`; las protecciones de ramas pueden permanecer activas.
Se mantiene `SUBMODULES_TOKEN` de lectura para repositorios privados. El token de
notificación de los componentes sigue sirviendo únicamente para solicitar la integración.

Las credenciales GCP solo se usan en los jobs existentes de publicación/despliegue.
El job que escribe tags no necesita secretos de GCP ni el environment de despliegue.
El permiso de Storage existente para escribir el canal permite la escritura condicional.

Para inspeccionar exactamente el código de una release:

```sh
git fetch origin tag integration-123456789-1
git switch --detach integration-123456789-1
git submodule update --init --recursive
```

Esto es una inspección de una versión, no una rama de desarrollo. Las modificaciones
del proyecto se preparan en `develop`; el pipeline operativo sigue publicando fuentes
aprobadas que llegaron a los `main` de los componentes.

Los punteros de submódulos visibles en la rama del madre pueden ser anteriores a
una integración. Para reproducir una release se usa su **tag**, no los punteros de
la rama. No se requiere crear tags en cada repositorio secundario.

## Verificación local

```sh
python3 -m unittest discover -s scripts/gcp -p 'test_*.py' -v
go run github.com/rhysd/actionlint/cmd/actionlint@v1.7.12 .github/workflows/*.yml
```

Las pruebas de integración Git crean remotos bare temporales; las peticiones a
GitHub, Cloud Storage y Cloud Build están simuladas. No publican tags reales,
no suben imágenes y no operan la VM.
