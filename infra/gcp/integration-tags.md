# Tags de integración y canales de publicación

## Qué activa cada workflow

- `.github/workflows/ci.yml` corre para PRs hacia `develop`/`main`, `workflow_dispatch`
  y el schedule semanal. Las PRs con destino `main` deben tener `develop` como
  rama de origen. El CI prueba el commit raíz y sus tres gitlinks de Backend,
  Frontend y Mobile; no sustituye esos punteros por las puntas actuales de sus ramas.
- `.github/workflows/publish.yml` se activa únicamente con `push` a `main`. Consume
  la combinación de gitlinks del commit que llegó a `main` y exige la evidencia
  Integrated CI correspondiente antes de publicar. Cambiar una rama secundaria,
  por sí solo, no dispara este workflow; integrar el gitlink en el repo raíz y
  pasar por el gate de `main`.
- `.github/workflows/vm-controls.yml` es manual (`workflow_dispatch`). Desde
  `main`, `start` y `update` usan el canal `main`. Desde `develop`, esas dos
  operaciones construyen los gitlinks exactos del commit seleccionado y avanzan
  el canal `develop`, sin presentar el resultado como Integrated CI aprobado.
  Ambos canales comparten las mismas VMs y Cloud SQL. `stop` detiene la sesión y
  no publica una versión.
- `.github/workflows/reproduce.yml` es manual y acepta solamente la rama `main`,
  un `run_id` aislado y un tag main completo que el orquestador valida. Ver el
  [runbook NFR-14](../../docs/auditorias/nfr-14/runbook.md).

## Snapshot inmutable de main

Cuando el push a `main` requiere publicación, `integration.py` crea el tag anotado
`integration-<GITHUB_RUN_ID>-<GITHUB_RUN_ATTEMPT>`. El tag apunta a un commit de
snapshot cuyo padre es el commit raíz probado y cuyos gitlinks identifican los
tres SHAs exactos. No actualiza ramas ni crea una PR. Si se reintenta el mismo
tag, solo se acepta el mismo commit; nunca se mueve ni se fuerza.

Después, `publish.yml` construye las seis imágenes, las publica por digest y
publica el bundle. El manifiesto registra el tag, la raíz, los tres componentes,
los digests, el orden de publicación y la evidencia aprobada de Integrated CI y
Android. El canal privado `channels/main.json` se cambia solo después de que
imágenes y assets estén completos. Finalmente se crea una GitHub prerelease con
el manifiesto; no es una release estable.

El tag identifica una combinación aprobada de fuentes. El manifiesto/release
identifica artefactos publicados. Ninguno acredita por sí solo que una VM esté
encendida o que el despliegue haya pasado smoke tests. Un tag sin prerelease puede
indicar que el build posterior falló.

La escritura del puntero usa precondición de generación de Cloud Storage. El orden
`(GITHUB_RUN_NUMBER, GITHUB_RUN_ATTEMPT)` impide que una publicación anterior que
termine tarde reemplace una posterior. Los jobs serializan escrituras del canal;
los reintentos vuelven a leer el objeto antes de actualizarlo. No publicar un
mismo canal desde workflows con numeración independiente.

`start`/`update` leen una versión completa del canal una vez y la validan antes
de desplegarla. No vuelven a ejecutar CI ni construyen APK/imágenes. `update`
retira A y B del balanceador, detiene las aplicaciones, migra una sola vez y
admite B y después A. Es un corte deliberado durante el cambio de esquema; si la
migración falla, no se garantiza que el runtime anterior se reactive. `stop` no
requiere tag y conserva Cloud SQL y otros recursos persistentes.

## Identidad y permisos

El tag se crea con `contents: write` en el job de integración. La prerelease usa
el permiso de contenido requerido en su job. La publicación/despliegue usa OIDC/
WIF en jobs separados; el job que crea el tag no necesita credenciales GCP. Los
tokens no escriben en `main` ni `develop`. Las protecciones de ramas se mantienen.

Para revisar exactamente una publicación:

```sh
git fetch origin tag integration-123456789-1
git switch --detach integration-123456789-1
git submodule update --init --recursive
python3 scripts/gcp/integration.py check
```

El tag es un checkout de inspección; preparar cambios en `develop` y promoverlos
por PR. Para reconstruirlo, conservar los gitlinks del tag, no actualizar los
submódulos a `main`.

## Camino directo de develop

`vm-controls.yml` puede ejecutarse manualmente desde `develop` con `start` o
`update`. Comprueba el commit del evento y sus tres gitlinks, publica seis
imágenes completas en `channels/develop.json` y despliega esa versión. No crea un
tag `integration-*`, una prerelease de main ni evidencia de Integrated CI. La
separación de canales no separa recursos: las migraciones cambian la base
compartida y pueden impedir volver a una versión anterior de `main`.

## Validación local

```sh
python3 -m unittest discover -s scripts/gcp -p 'test_*.py' -v
go run github.com/rhysd/actionlint/cmd/actionlint@v1.7.12 -ignore 'unexpected key "queue" for "concurrency" section' .github/workflows/*.yml
```

Las pruebas de scripts simulan operaciones GitHub/GCP/Cloud Build. No crean tags
remotos, publican imágenes ni operan las VMs.
