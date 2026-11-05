# Ejecución por un agente

El agente usa el mismo [guion humano](README.md) y [workflow.json](workflow.json). Este JSON es una **especificación de trabajo**, no un runner instalado: el agente necesita navegador automatizable y control de Android(Appium/UIAutomator u otra herramienta disponible). No existe en este cambio una suite única que ejecute ya los41 pasos ni integración nueva de ese runner a CI.

## Entrada y selección de escenarios

1. Leer AGENTS, `frontend/DESIGN.md`, continuidad y el guion. Ejecutar `python scripts/demo/workflow.py validar`.
2. Elegir `run_id` nuevo. Completar `.local/demo/ID/manifest.json`: URLs vigentes, release/SHAs desplegados, vencimiento de sesión, actores/credenciales por referencia privada, Android serial/target/SHA APK, IDs de recursos y publicaciones. Los SHAs locales no sustituyen los desplegados.
3. Preparar CFG-01–06 en un tenant exclusivo de datos sintéticos reservado al ensayo. Generar archivos con `preparar` después de obtener operador/zona; generación no aprovisiona nada. No operar registros de otras pruebas ni crear hechos en su nombre.
4. Elegir `principal` con cierre transitivo de dependencias. `extension`, `tecnico` y `brecha` se registran aparte; su ausencia no se transforma en éxito del alcance completo. Ejecutar las extensiones en escenarios nuevos, liberando recursos por sus comandos reales, sin borrar jornadas ni reusar una cerrada.
5. Un agente puede automatizar recepciones, cargas, pruebas y retornos **simulados** sobre los datos sintéticos del tenant reservado: marcar `mode=simulacion`, nunca afirmar constatación de una entrega/medición real. Hardware y hechos reales necesitan evidencia propia y se reportan por separado. Si falta el aislamiento o la herramienta Android, bloquear la rama dependiente.

Los IDs de escena son estables entre guía/JSON/resultados. `requirements` los vincula con la planilla; `depends_on` expresa orden causal; `actions` indica acciones; **todas** las `assertions` deben tener evidencia para aprobar. `availability` describe implementación, no resultado de ejecución.

## Algoritmo del agente

```text
validar(workflow)
cargar(manifest, resultados existentes del mismo run_id)
comprobar release remota, fecha, salud, actores, Android y aislamiento
para cada paso elegido en orden topológico:
    si ya aprobado: reconciliar sus outputs persistidos antes de omitirlo
    si alguna dependencia no logró sus aserciones: bloquear con causa
    si falta funcionalidad (GAP-*): registrar brecha; nunca fabricar acción
    comprobar precondiciones y abrir sesión independiente del actor
    ejecutar actions por la superficie indicada
    capturar IDs/versiones/acuse y guardar manifest tras cada mutación
    esperar condición hasta timeout_seconds, conservando payloads de reintento
    comprobar TODAS las assertions por UI + lectura persistida/acuse
    guardar resultado, observaciones y evidencias sin secretos
restaurar conectividad y conservar datos/colas/evidencias
emitir resultado del circuito, cobertura por requisito y bloqueos
```

Un paso con alcance parcial puede aprobar solo las aserciones de su parte implementada; el requisito sigue `parcial` por GAP relacionado. Un paso bloqueado no habilita acciones que requieran sus outputs. El seguimiento WEB-04 es una rama paralela a depósito: sus etiquetas pueden comprobarse, el enlace puede quedar bloqueado y DEP-01 puede continuar. Si una rama agrupa varias aserciones, registrar resultado por aserción para evitar perder la evidencia parcial.

## Navegador

- Un `BrowserContext` por A1,A2,C1,C2,B y destinatario. Ingreso por el portal real; no inyectar JWT en cookies ni desactivar antiforgery/permisos.
- Preferir `getByRole`/`getByLabel` y nombres visibles existentes. Ejemplos de navegación: Commerce **Crear envío**, **Importar CSV**, **Mis envíos**; Backoffice **Depósito**, **Rutas**, **Flota**. Usar la referencia/código del manifiesto para acotar una fila antes de abrir acciones.
- Backoffice de envíos está en `/`, no `/envios`. Ver rutas exactas en las escenas. Guardar `fecha=yyyy-MM-dd` del operador al volver a rutas y capturar el ID devuelto al crearla.
- Esperar desaparición del estado de carga, mensaje de resultado y lectura posterior. En Blazor/SignalR no usar `networkidle` como única condición. Un200 de Razor puede contener error de validación; revisar contenido y persistencia.
- Al descargar etiquetas, esperar el `download`, comprobar `application/pdf`, número de páginas y decodificar QR; comparar con UUID persistidos. La captura del PDF no acredita impresión física.
- Capturar estados cargando/vacío/error cuando se activen realmente. Si se hace revisión de UI, comprobar teclado/foco/valores conservados y escritorio/320px según DESIGN; no presentar HTTP como revisión visual ni escaneo como certificación WCAG.
- Mantener `permanent=false`. Bloquear Mapbox/Geoapify externos en el perfil de prueba y controlar SDK/transporte con los harnesses existentes. Un mock de API completa no acredita integración. Si el remoto no admite fixture del proveedor, declarar bloqueada búsqueda/estimación y continuar solo la alternativa manual real disponible.

## Android y operación sin red

`MainPage.xaml` expone `AutomationId=CorreoIngreso` y `ClaveIngreso`; el resto se localiza por textos/semántica de la jerarquía nativa, dentro de la pantalla adecuada. Ejemplos: **Mi recorrido**, **Actualizar**, **Iniciar jornada**, **Escanear bulto**, **Comenzar reparto**, **Detalle de parada**, **Confirmar entrega**, **Registrar intento**, **Rendir bultos en depósito**, **Terminar jornada**. No inventar AutomationIds ausentes ni usar coordenadas de una captura como selectores permanentes.

- Declarar serial explícito en todas las órdenes ADB; el APK debe ser `GcpDemo` contra HTTPS remoto válido, sin CA/gateway/reverse local.
- Emulador: cámara/posición/escáner pueden usar entradas sintéticas de laboratorio. Si la herramienta no puede aportar una imagen QR/captura válida a la cámara o completar la firma, bloquear esa aserción nativa; el test API equivalente se informa aparte.
- Cortar todas las vías a la API **del dispositivo** y verificar una petición nueva fallida; conservar el navegador del operador conectado. `context.setOffline(true)` de Playwright no afecta MAUI. No apagar servidores ni borrar sesiones para simular la falta de Internet.
- Antes del corte, descargar e iniciar jornada y confirmar carga/salida con acuse. La inicialización exige hora/día del operador; no adelantar reloj. El mapa offline es opcional en el código actual; no se acredita cartografía offline si no hay paquete descargado.
- Registrar operaciones/evidencias, reabrir proceso sin limpiar almacenamiento y comprobar persistencia local. Al reconectar, distinguir acuse `Aplicada`, `Conflicto` y pendiente/transitorio. La sincronización puede consumir45s; dar120s al paso completo, sin esperas fijas que oculten un error.
- Reintentar el mismo sobre con su ID,secuencia,payload,hash y versiones; conservar orden causal y límite existente de100 operaciones por lote. No cambiar a la versión más reciente para forzar una aceptación.
- EXT-02 usa **IntentoFallido** concurrente con cancelación para demostrar rechazo de versión. `EntregaFisica` concurrente con Cancelado tiene conciliación específica y puede ser aplicada conservando Cancelado: no es el mismo oráculo.
- Cierre pendiente no equivale a confirmado. Reintentar desde **Actualizar**, sin otro FinJornada. Cerrar no recibe carga ni libera flota. El reporte identifica por separado custodia, estado comercial, estado de ruta y ocupación.
- Debug omite desbloqueo local; Release lo requiere. Un bypass de Debug no acredita biometría. FCM aceptado no acredita notificación mostrada; push real requiere app cerrada sin force-stop, dispositivo/permiso y observación.

## API, concurrencia y oráculos

Leer OpenAPI del candidato/contratos versionados; resolver valores con la sesión del actor autorizado y capturarlos, no usar UUID de documentación. `api-alta.json` generado sigue `CrearEnvioRequest`: operador, destinatario, dirección, servicio, bultos. Resolver `servicio.versionTarifarioEsperada`; no agregar `ComercioId` ni precio ni campos fuera del contrato.

- Envío individual/API: capturar ID de respuesta y asociarlo a código único; no asumir idempotencia del POST individual. Ante timeout, buscar/reconciliar por su código antes de reenviar.
- Importación: multipart con operador, archivo y `VersionFormato=2` según OpenAPI; comparar referencias antes/después. El lote inválido incluye ATOMICO **nuevo**, no una referencia ya importada que ocultaría un alta parcial.
- Recepción: consultar bulto y leer versiones antes del cotejo. Reintento conserva `ComandoId`/actor/payload; conflicto requiere releer y decidir. Medidas distintas exigen discrepancia, no «Conforme» falso.
- Exclusión CU-15: dos peticiones realmente concurrentes con mismo envío y **recursos diferentes** libres, barrera de salida y lectura final de paradas activas. Dos clics secuenciales o compartir vehículo no prueban el conflicto correcto.
- Cálculo independiente: MULTI v1=115,individual v1=109, MULTI Urgente=165, MULTI v2 base120=135 UYU. Ruta principal=3 paradas/4 bultos/2000g/4000cm³. Capturar publicación/reglas al alta y comprobar que se conservan tras EXT-01.
- Historia CU-12 no dispone de visor general ni endpoint genérico: comprobar inmutabilidad en fixture PostgreSQL con suites existentes. No consultar una base remota con privilegios globales para sustituir una autorización de producto.

## Reutilizar las suites existentes

En un checkout de pruebas separado, con dependencias del repositorio y fixtures propias; no recompilar DLLs cargadas por un runtime activo. Estos comandos complementan el recorrido, **no reemplazan el Android nativo ni ejecutan el circuito completo en remoto**. Docker/PostgreSQL/Node/Chromium son prerrequisitos de los harnesses; para Cloud seguir continuidad y gitlinks exactos. Mantener HTTP y fullstack/navegador en invocaciones distintas.

```powershell
# HTTP de recepción, estados/historia y conflicto: bases temporales propias.
dotnet test backend/tests/NexoRuta.IntegrationTests --filter 'FullyQualifiedName~RecepcionDepositoHttpTests|FullyQualifiedName~ShipmentStatePolicySqlTests|FullyQualifiedName~EnvioEventsHttpTests|FullyQualifiedName~EnvioHistoryMigrationTests|FullyQualifiedName~OperacionesRepartoHttpTests'

# Navegador real: exige módulo Playwright/Chromium existente y portales compilados.
$env:NEXORUTA_GEOCODING_FULLSTACK_DIR = 'RUTA-PRIVADA/destino'
$env:NEXORUTA_RECEIPT_E2E_DIR = 'RUTA-PRIVADA/recepcion'
$env:NEXORUTA_PLAYWRIGHT_MODULE = 'RUTA-ABSOLUTA/scripts/cloud/node_modules/playwright'
dotnet test backend/tests/NexoRuta.IntegrationTests --filter 'FullyQualifiedName~GeocodificacionFullStackBrowserTests|FullyQualifiedName~RecepcionDepositoBrowserTests'

# Mobile portátil: contrato/lógica; no controla dispositivo Android.
dotnet test mobile/tests/NexoRuta.Mobile.Core.Tests
dotnet test mobile/tests/NexoRuta.Mobile.Application.Tests
dotnet test mobile/tests/NexoRuta.Mobile.Api.Tests
dotnet test mobile/tests/NexoRuta.Mobile.Storage.Tests
```

Los paths/variables son ejemplos que deben completarse. En Cloud usar el lock portátil indicado en continuidad sin reescribir locks Android. Ver [reproducción histórica](../auditorias/integral-cu/04-reproduccion-y-datos.md) para más harnesses; usar el código/estado integrado actual, no sus antiguos oráculos rojos como resultado esperado vigente.

## Resultados

El generador deja `resultados.json` con todas las escenas pendientes. Por cada escena registrar:

- `status`: pendiente/aprobado/fallido/bloqueado/parcial; `mode`: humano/simulacion/contrato/artefacto.
- `started_at`, `finished_at` UTC, actor, release/SHA y referencias nuevas relevantes en `observed`.
- `assertions`: resultado de cada aserción, observado concreto y evidencia asociada. Toda aserción debe existir en el reporte, incluso bloqueada.
- `evidence`: paths privados de capturas/logs/lecturas sanitizadas; URLs de artefactos CI cuando proceda. Manifest de IDs/tokens y evidencias sensibles permanecen privados; redactar tokens en capturas/trace/HAR antes de compartir.

Formato de una aserción, sin rellenarlo como si hubiera pasado:

```json
{"assertion":"MULTI queda Entregado con prueba validada","status":"pendiente","observed":"","evidence":[]}
```

Emitir cuatro apartados independientes: **compilación**, **HTTP**, **automatización**(indicando web/API/Android), **revisión visual**. Añadir resultados de circuito principal, extensiones y cobertura total; enumerar brechas y dependencias. Un agente puede completar un circuito simulado y seguir teniendo requisitos bloqueados: nunca resumirlo como30 CU aprobados.

## Prompt para iniciar un agente

```text
Ejecuta el ensayo remoto NexoRuta usando docs/demo/README.md y docs/demo/workflow.json.
Lee AGENTS, frontend/DESIGN.md y continuidad. Usa el manifest privado indicado para
este run_id y los SHAs/release DESPLEGADOS. Verifica salud, vencimiento, aislamiento
de datos sintéticos y APK Android GcpDemo. Trabaja por dependencias; usa UI real para
los pasos de UI y API solo para los pasos de API y oráculos autorizados. Toda acción
física automatizada es una simulación identificada del tenant de ensayo. Conserva
IDs/payloads/colas ante reintentos, sin inventar resultados ni cambiar proveedores,
seguridad o políticas para pasar. Registra GAP-* como brechas. Si faltan medios de
Android o el enlace Production, bloquea esa rama y continúa pasos independientes.
Guarda manifest, resultados y evidencias privadas tras cada paso; informa compilación,
HTTP, automatización y revisión visual por separado. No despliegues, ejecutes carga
remota, cortes instancias ni destruyas infraestructura como parte del ensayo funcional.
```
