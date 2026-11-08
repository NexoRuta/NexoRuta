# Webhooks HTTP: escenario reproducible en Cloud

Se partió del remoto principal `develop` **3da5374e10c82d4b4c00b69fed17e368dddd4354**, consultado al iniciar el trabajo. Gitlinks iniciales exactos:

| Componente | SHA |
|---|---|
| backend | `0d14dddb3b3ba6cc7c32389e415a8776e61bc370` |
| frontend | `fa94588955c9de877190b411ae6543fd4c3e9b98` |
| mobile (sin cambios) | `53f6be2cdec48f48e30e390060feeaefb5be0ead` |

El checkout generado antes de fetch tenía raíz `27f69c62bc974deee8879374d6d14b1db051a0f6`; no se utilizó como base. Se inicializaron los hijos con `submodule update --init --recursive`, sin seleccionar otras puntas para arreglar builds. Los cambios de gestión, reportes, cuenta y liquidaciones incluidos en esos árboles se conservan. Los SHAs de entrega son los gitlinks del PR principal y sus PR de componentes, no los históricos de `checkpoint.json`.

## Arranque interactivo

```bash
cd /workspace/NexoRuta
bash scripts/cloud/environment-install.sh
source scripts/cloud/env-agent.sh
export NEXORUTA_CLOUD_WEBHOOK_DEMO=1
python3 scripts/cloud/dev.py start
python3 scripts/cloud/dev.py verify
dotnet run --project tests/Webhooks.Demo
node scripts/cloud/verify-webhooks-browser.cjs
```

El helper prepara reglas, cobertura y tarifas **sintéticas** en la base propia que valida `private.json`; no recibe conexiones externas ni lee `.env`. Si el runtime ya está activo, detenerlo con `dev.py stop` antes de recompilar. La base, el receptor SQLite, claves y credenciales quedan en `.local/codex-cloud`; stop/start no los borra. No depende de Windows ni de una sesión anterior.

- Commerce: **http://localhost:5102/webhooks**.
- Nueva pestaña humana: **http://localhost:5103/comercio**.
- URL de suscripción que usa el worker Cloud: **http://127.0.0.1:5103/comercio/webhook**.
- API: `http://127.0.0.1:5000/`.

Usar los campos privados `commerceEmail`/`commercePassword` para Commerce, `webhookAdmin` para controles del receptor y `webhookSigning` como clave compartida. No copiar esos valores a documentos, capturas o logs. En el formulario el secreto es un campo password; el listado muestra solo el identificador de clave.

## Ensayo manual

1. Entrar a Commerce, elegir operador, Nueva suscripción; cargar URL del worker y la clave compartida; contrato v2; habilitar creación, cambios de estado, resultados de bulto, nueva visita y retiros; guardar.
2. Usar **Abrir receptor de prueba en otra pestaña**. Ingresar la clave de controles. La ruta es `/comercio`, separada del seguimiento público.
3. Crear un envío sintético desde Commerce (cobertura preparada, coordenadas −34.901/−56.201) o por la API existente; cancelarlo mediante la acción real para generar una transición adicional. El receptor debe indicar firma válida y Commerce `Entregado` con HTTP 200.
4. Activar **Simular caída HTTP 503**. Crear otro envío. Consultar `Reintento`, intentos y próximo intento en Commerce. Restaurar la recepción y esperar recuperación automática.
5. Dejar la simulación durante tres intentos (base 2 s, tope 10 s en Cloud). Consultar `Fallido`. Restaurar y pulsar **Reenviar aviso fallido**; consultar actor y resultado.
6. Pulsar **Repetir para comprobar deduplicación** sobre uno entregado: aumenta intentos, sin incrementar eventos procesados.
7. Activar **Interrumpir próxima respuesta** y crear otro envío. El receptor persiste y corta la conexión sin respuesta; el worker reintenta con la misma identidad y Tracking muestra duplicado.
8. Editar URL/eventos/contrato o rotar la clave con pendientes y comprobar que su detalle conserva revisión y destino anteriores. Deshabilitar drena; **Revocar y cancelar pendientes** invalida los pendientes y exige clave nueva para reactivar.
9. Para parciales, nueva visita y el ciclo completo del retiro con evidencia/custodia, ejecutar el ensayo automatizado siguiente. Reutiliza los casos operativos existentes, registra hechos reales y entrega los contratos al receptor Tracking real. No inventa mensajes desde la interfaz.

## Ensayo automatizado obligatorio

```bash
bash scripts/cloud/check-webhooks.sh
```

Crea bases PostgreSQL/PostGIS propias de cada fixture, roles API/worker restringidos, Kestrel API, Commerce, Tracking y dos workers. Chromium configura la suscripción por la interfaz y abre el receptor en otra pestaña. Comprueba firma, estado real, 503, agotamiento/reenvío, repetición, body alterado, respuesta interrumpida, conexión realmente rechazada al detener Tracking, timeout TCP sin respuesta HTTP, recuperación y reinicios. Las fixtures de parciales/retiros verifican custodia/pruebas y transmiten sus contratos por HTTP. Los proveedores de mapas/viales se controlan; no hay consumo facturable ni envíos a terceros.

Evidencias locales en `.local/webhooks-evidence` (TRX, JSON sintéticos y PNG). CI conserva sus artefactos en la ejecución del PR. Son categorías distintas: build, HTTP/persistencia, automatización de navegador y revisión visual humana de capturas; un screenshot no certifica WCAG. Se revisan escritorio 1440 px, 320 px, teclado/foco y texto al 200 %. El ensayo no acredita funcionamiento en producción ni latencia bajo carga.

## Compose local

La base se provisiona con los comandos locales ya documentados; aplicar migraciones y roles a una base **propia** antes de levantar escritores. Generar contraseñas/clave compartida en un `.env` local ignorado, con al menos 24 caracteres para controles y `whsec_` + Base64 de 32 bytes aleatorios para firma.

```bash
docker compose -f compose.yaml -f compose.override.yaml -f compose.webhooks-demo.yaml up --build -d
```

El override demo se habilita explícitamente. Navegador: `http://localhost:5103/comercio`; URL de suscripción/worker: **`http://tracking:8080/comercio/webhook`** (puerto interno **8080**, host publicado **5103**). `localhost:5103` dentro del worker sería su propio contenedor. El volumen `tracking_commerce_demo_data` conserva SQLite; no usar `down -v` para simular recuperación. API y worker comparten el key ring existente. No incluir el override demo en producción.

Política de destinos, contrato, firma, ciclo de claves, garantías y límites: [contrato backend](../../backend/docs/webhooks/http.md). Decisión y alternativas: [ADR](../../backend/docs/adr/002-http-commerce-webhooks.md). Este trabajo no ejecuta merge, despliegue, operaciones de VM, apply/destroy ni modificaciones a bases compartidas.
