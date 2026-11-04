# Prerrequisitos, comandos y datos nuevos

## 1. Base exacta y preparación que no cambia gitlinks

.NET SDK10.0.401, Node24.22.2, Docker local, PostgreSQL18/PostGIS3.6, Playwright/Chromium y `pdftotext`/`pdftoppm`. Mantener proxy/CA y TLS; para la descarga estática del SDK/CSS Mapbox desde Node24 usar `NODE_USE_ENV_PROXY=1`. Ninguna prueba necesita clave Mapbox/Geoapify real. Datos, credenciales, capturas, TRX y logs privados quedan fuera de Git.

```bash
git clone --branch test/navegador-optativos --recurse-submodules https://github.com/NexoRuta/NexoRuta.git NexoRuta-auditoria
cd NexoRuta-auditoria
git rev-parse HEAD                    # 13aefdb15d0f4d00cd870220e961717dcb48a1fd
git ls-tree HEAD backend frontend mobile
git submodule status
# bf4da61134e2c04db66f0e21bb99167dfb49306e
# 1ca0172bec203af3fa860b34925e4562ec11ee44
# 74a25f1b5b18c7dfc006cf7df747d73b0ec4910a
```

La rama publicada puede avanzar después de este corte: si los cuatro valores no coinciden, detener y obtener los objetos exactos indicados, sin usar otra rama como sustituto. Para reproducir además las dos pruebas rojas y helpers de **esta revisión**, clonar `review/auditoria-integral-cu` con sus gitlinks publicados; los únicos cambios de submódulos son archivos nuevos de pruebas. El principal conserva el inventario de la base original.

Leer AGENTS y continuidad. **No ejecutar environment-install.sh** con este manifiesto desactualizado (H09), ni ejecutar scripts que hagan checkout desde checkpoint.json. Después de verificar los gitlinks:

```bash
source scripts/cloud/env-agent.sh
bash scripts/cloud/install-agent.sh   # restore/dependencias, no cambia gitlinks
export NODE_USE_ENV_PROXY=1
export NEXORUTA_PLAYWRIGHT_MODULE="$PWD/scripts/cloud/node_modules/playwright"
mkdir -p /tmp/nexoruta-auditoria/resultados
```

No requiere apt/sudo. Si el sandbox exige red/Docker fuera de él, usar el permiso admitido de la herramienta (`sandbox_permissions=require_escalated`), sin desactivar TLS. No copiar `.env`, bases, secretos ni binarios de otra máquina. `scripts/cloud/checkpoint.json` no es la autoridad de esta auditoría: los SHA y gitlinks verificados sí.

## 2. Suites ejecutadas y reproducciones rojas

Las fixtures PostgreSQL crean contenedores/bases exclusivamente propios, con contraseñas aleatorias; no aceptan la base manual como conexión. No ejecutar `check.sh` indiscriminadamente para este objetivo: termina consultando el runtime normal. Los comandos siguientes no lo necesitan.

```bash
source scripts/cloud/env-agent.sh
dotnet test backend/tests/NexoRuta.UnitTests --logger 'trx;LogFileName=unit.trx' --results-directory /tmp/nexoruta-auditoria/resultados

dotnet test backend/tests/NexoRuta.IntegrationTests --filter 'FullyQualifiedName~RecepcionDepositoHttpTests|FullyQualifiedName~ShipmentStatePolicySqlTests|FullyQualifiedName~EnvioEventsHttpTests|FullyQualifiedName~EnvioHistoryMigrationTests|FullyQualifiedName~RutasHttpTests|FullyQualifiedName~CapacidadVigenteHttpTests|FullyQualifiedName~RlsRestrictedHttpFlowTests|FullyQualifiedName~AuthDiagnosticsHttpTests|FullyQualifiedName~SesionesMovilesHttpTests' --logger 'trx;LogFileName=integration.trx' --results-directory /tmp/nexoruta-auditoria/resultados

# Esperado ROJO, H01; fixture real/RLS, no afecta datos manuales:
dotnet test backend/tests/NexoRuta.IntegrationTests --filter FullyQualifiedName~AuditoriaIntegral_ --logger 'trx;LogFileName=reproduccion.trx' --results-directory /tmp/nexoruta-auditoria/resultados
# Esperado ROJO, H02; doble JS con barrera determinista:
dotnet test frontend/tests/NexoRuta.ApiClient.Tests --filter FullyQualifiedName~AuditoriaIntegral_ --logger 'trx;LogFileName=reproduccion-mapa.trx' --results-directory /tmp/nexoruta-auditoria/resultados
# Esperado fallo NU1004 con lock original (H07):
dotnet restore backend/tests/NexoRuta.ArchitectureTests --locked-mode
```

La suite ArchitectureTests pudo observarse tras un restore ordinario: 2/3 pasan, falla H08. Ese restore cambia el lock, por eso en esta auditoría se restauró únicamente ese cambio generado al contenido original antes de comprobar locked-mode. **No usar restore no bloqueado como solución ni publicar su cambio incidental**. Para diagnosticar H08 sin cambiar el lock fuente, usar un lock alternativo de ensayo (`-p:NuGetLockFilePath=obj/review.packages.lock.json`) o los artefactos locales ya compilados con `--no-build --no-restore`; no presentar eso como el restore correcto de CI.

### Nueve navegadores optativos

Las cinco flags frontend y las tres flags de integración habilitan nueve casos; su ausencia genera Skip y no equivale a éxito. Primero compilar los dos portales del checkout actual:

```bash
source scripts/cloud/env-agent.sh
export NODE_USE_ENV_PROXY=1 NEXORUTA_PLAYWRIGHT_MODULE="$PWD/scripts/cloud/node_modules/playwright"
dotnet build frontend/src/NexoRuta.Backoffice
dotnet build frontend/src/NexoRuta.Commerce
export NEXORUTA_B2_BROWSER_DIR=/tmp/nexoruta-auditoria/b2
export NEXORUTA_B3_BROWSER_DIR=/tmp/nexoruta-auditoria/b3
export NEXORUTA_B4_BROWSER_DIR=/tmp/nexoruta-auditoria/b4
export NEXORUTA_B5_BROWSER_DIR=/tmp/nexoruta-auditoria/b5
export NEXORUTA_DESTINATION_BROWSER_DIR=/tmp/nexoruta-auditoria/destino
# La base exacta original pasa 482. La rama de revisión añade la reproducción roja H02;
# la suite completa de esa rama debe conservarla visible, no excluirla para declarar verde.
dotnet test frontend/tests/NexoRuta.ApiClient.Tests --logger 'trx;LogFileName=frontend.trx' --results-directory /tmp/nexoruta-auditoria/resultados
node --test frontend/tests/*.test.cjs
export NEXORUTA_GEOCODING_FULLSTACK_DIR=/tmp/nexoruta-auditoria/geo-integrado
export NEXORUTA_VEHICLES_E2E_DIR=/tmp/nexoruta-auditoria/vehiculos
export NEXORUTA_RECEIPT_E2E_DIR=/tmp/nexoruta-auditoria/recepcion
dotnet test backend/tests/NexoRuta.IntegrationTests --no-build --filter 'FullyQualifiedName~GeocodificacionFullStackBrowserTests|FullyQualifiedName~VehiculosBackofficeBrowserTests|FullyQualifiedName~RecepcionDepositoBrowserTests' --logger 'trx;LogFileName=browser-integrado.trx' --results-directory /tmp/nexoruta-auditoria/resultados
export NEXORUTA_SESSION_E2E_DIR=/tmp/nexoruta-auditoria/sesion
dotnet test backend/tests/NexoRuta.IntegrationTests --no-build --filter FullyQualifiedName~SesionWebBrowserTests --logger 'trx;LogFileName=sesion.trx' --results-directory /tmp/nexoruta-auditoria/resultados
for project in Core Application Api; do
  dotnet test "mobile/tests/NexoRuta.Mobile.$project.Tests" -p:NuGetLockFilePath=obj/cloud.packages.lock.json
done
```

Nueve optativos: 4 integraciones (destino real, alta, vehículos, recepción) +5 frontend (base, destino, B4, Flota, B5). El browser de sesión es adicional. Los tests móviles son portátiles, no usan un dispositivo Android. Capturas producidas por harness solo acreditan sus condiciones controladas, no cámara/lector/entrega reales.

## 3. Runtime exclusivo y datos ya preparados para personas

Helpers de revisión (no modifican producto ni configuración publicada):

```bash
source scripts/cloud/env-agent.sh
python3 scripts/review/runtime-aislado.py start --run-id auditoria03nov
python3 scripts/review/runtime-aislado.py verify --run-id auditoria03nov
# Una sola vez, sobre ese runtime NUEVO; no repetir si ya tiene marker:
python3 scripts/review/sembrar-zona.py --run-id auditoria03nov
python3 scripts/review/sembrar-actores.py --run-id auditoria03nov
# Detener solo procesos propios, sin borrar base/volumen:
python3 scripts/review/runtime-aislado.py stop --run-id auditoria03nov
```

**En esta sesión ya se ejecutaron start, verify y preparación. No volver a sembrar.** Si start indica runtime vivo, usar verify. Puertos API5000, Backoffice5101, Commerce5102, Admin5103 y Tracking5104. El contenedor exclusivo es `nexoruta-review-auditoria03nov`; estado `.local/review/runtimes/auditoria03nov`. No se abre `.local/codex-cloud/private.json` del runtime normal. Para otro clon, detener únicamente el propio antes de usar los mismos puertos y elegir otro run-id; no copiar estado ni usar un contenedor ajeno.

Credenciales nuevas de bootstrap en `.local/review/runtimes/auditoria03nov/private.json` y actores de revisión en `manual-actors.private.json`, permisos0600. Abrirlos localmente solo para ingresar; no pegarlos en informes, terminal grabada, PR ni capturas. La clave aleatoria de evidencias queda en `evidence-key.json`; el wrapper la conserva entre reinicios y la inyecta solo en los procesos propios. No deshabilita seguridad ni usa una clave del taller.

Preparación ejecutada: operador A/comercio C1/plataforma por bootstrap; operador B, comercio C2 y usuarios A1/A2/D1/R1/R2/NEGATIVO mediante API en el runtime propio. Los permisos acotados se consultan en el JSON privado. **Los perfiles de repartidor/vehículos y su verificación física, tarifas y reglas deben completarse por el circuito humano CU-01 a06**; crear un acceso no acredita un repartidor/vehículo habilitado ni configura una promesa.

Se creó zona sintética A a partir del departamento **oficial UY-MO**, siete franjas09:00–18:00. No se crearon tarifas, reglas, envíos, rutas, recepciones ni hechos físicos. El primer polígono de ensayo fue rechazado por salir de Uruguay; no se amplió territorio para eludir esa validación. `manual-preparation.json` registra IDs nuevos y pendientes. B queda para la configuración distinta que verificará la persona.

Datos definitivos preparados en `.local/review/manual/auditoria03novfinal/` (un primer juego `auditoria03nov` se preservó y **no se debe usar** para atomicidad):

| Archivo | Datos y oráculo |
|---|---|
| `01-alta-v2.csv` | 9 filas, 8 referencias nuevas; MULTI tiene dos bultos; otras: HISTORIA, CAPACIDAD, INTENTO, RETORNO, PRUEBA, CANCELACION y AISLAMIENTO |
| `02-reimportacion-parcial-v2.csv` | Las dos filas de MULTI; repetir no duplica |
| `03-lote-invalido-atomico-v2.csv` | Una referencia válida **NUEVA** con sufijo ATOMICO y otra inválida por peso; ningún alta parcial. No usar una referencia ya equivalente como falso oráculo de rollback |
| `04-sin-cobertura-v2.csv` | Rivera, con zona A que no lo cubre; debe rechazarse |
| `manifest.json` | Solo parámetros sintéticos y nombres de referencia, sin credenciales; todas las acciones físicas pendientes |

Las cuatro cabeceras y registros se comprobaron contra **CsvEnviosParser real**: 9/2/2/1 registros de13 columnas. Eso comprueba sintaxis, no cotización ni alta: completar CU-03/04 y comprobar cobertura antes de importarlos. Formato de multipart `VersionFormato=2`; no volver al CSV de9 columnas. Las medidas del CSV son declaraciones sintéticas, no mediciones físicas.

Para generar otro juego sin sobrescribir el actual:

```bash
python3 scripts/review/preparar-datos.py --operador-id <UUID_NUEVO_A> --zona-id <UUID_ZONA_NUEVA_A> --run-id <identificadorNuevoAlfanumerico>
```

El generador no hace HTTP ni SQL, rechaza los UUID reservados como argumentos y falla si la carpeta ya existe. Los helpers de preparación anotan avance en archivos propios; ante fallo revisar el marker/JSON privado y no ejecutar a ciegas una segunda creación.

## 4. Validación por superficies y servicios

1. Navegador: seguir los 30 casos de [03](03-guia-manual.md), a escritorio/320px, teclado, foco, valores, conflictos y recuperación. No cambiar diseño aceptado.
2. Android/emulador: instalar con instrucciones Mobile propias, API del runtime nuevo accesible por red autorizada (loopback de emulador no es la VM). No se configuró red Android ni se afirma ejecución. Identificar dispositivo/versión/permisos.
3. Hardware: cámara/lector, firma/foto, posición/background, biometría y push con app cerrada los ejecuta y confirma una persona. No sustituir presencia por fixtures, lecturas sintéticas o un botón «Confirmar» automatizado.
4. Servicios locales: SMTP capturador, receptor HTTP de prueba, broker y observabilidad deben tener credenciales/volúmenes nuevos. Parte de los recorridos no está implementada (H03–06): registrar brecha, no simular una aceptación.
5. Remoto/nube/carga: solo preparar plan y prerrequisitos. Esta tarea no autoriza merges, despliegues, gastos, exposición de bases ni uso de servicios pagos.
