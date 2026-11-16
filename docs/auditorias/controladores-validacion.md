# C1/C2 — Controladores y validación de bultos

## Base elegida

Se leyó `AGENTS.md` y la continuidad Cloud. Checkouts limpios; `git fetch origin`
y `git pull --ff-only origin develop` ejecutados en raíz y backend antes de editar.
El clon inicial solo seguía `main`; se trajo explícitamente `develop` sin cambiar
`main`. Rama raíz y backend: `fix/controladores-validacion`.

| Revisión | SHA |
| --- | --- |
| Raíz al abrir el checkout | `27f69c62bc974deee8879374d6d14b1db051a0f6` |
| Raíz `origin/develop` elegida | `3b00ef8ad43d525b1276cb7116c2dc8cec65590a` |
| Backend gitlink y `origin/develop` | `ad63712d649b4c178f75ebecf7ac3aa3b0e3d3d5` |
| Frontend gitlink y `origin/develop` | `d8a81a2a5d7d24810148ee72c647573586463324` |
| Mobile gitlink y `origin/develop` | `8aa3a5fd8a52a089e32e339c8f85dd870f5a8ea8` |

Gitlinks iniciales del checkout: backend `947b3f7e2c90f05b01d4911b1512e07b827d4528`,
frontend `5c1c008d5a62ea3f7e5f043b2b3a178e154a4ef6`, mobile
`4b9032bc54be3faf7549b33a65315aca87a69df5`. Se actualizaron primero las bases
remotas y se inicializaron los tres submódulos en los gitlinks exactos de
`3b00ef8`, sin `--remote`. Se revisó la historia backend desde el gitlink inicial:
el avance ya está integrado en la raíz actualizada (incluye #59 y #61).
Los componentes no presentan diferencias entre su develop y el gitlink elegido;
no se incorpora ningún avance adicional de componente.

## Alcance y evidencia

Solo C1, C2, regresiones y documentación. `main` y producción fuera del alcance.
SDK 10.0.401, datos sintéticos, PostgreSQL/PostGIS efímero y proveedor simulado;
sin consumo Mapbox/Geoapify. Base previa: 24/24 (búsqueda simulada, destinos HTTP
y validación de request). OpenAPI generado antes de C2 capturado para comparación.

### C1

Commit `3a7fa502ff254e4356f63b1530914ac879365332`.
`EjecutarGeocodificacionAsync` traduce solo indisponibilidad y límite de
geocodificación. Las acciones conservan validación, conflictos y éxitos.
33/33: `BusquedaDestinoSimuladaHttpTests` (26), `DestinosEnvioHttpTests` (6) y
OpenAPI previo a C2 (1). Simulación aislada posterior: 26/26.
Se verificaron detalles, `ProblemDetails`, códigos, `Retry-After`, `no-store`,
cancelación y excepciones ajenas, y el 429 vacío del middleware real.
Las nuevas aserciones se ajustaron a la forma ya existente de los 429 MVC
simulados (sin `title`/`type`) y al token vinculado de HttpClient; sin cambios
al contrato para satisfacer esas aserciones.

### C2

Commit `515a119509b6bc11f3bdababd73801a270a9b1a3`.
La definición única `Domain.Envios.MedidasBulto` provee límites invariantes,
rango inclusivo y precisión efectiva. Dominio, request API y CSV la usan;
DosDecimales consume solo precisión y conserva los rangos de vehículos.
Se mantienen excepciones del constructor y validación por campo, sin redondeo.

57/57: request/culturas 21, CSV HTTP 20 y capacidad/vehículos/OpenAPI 16.
Unitarias específicas 39/39, repetidas sobre el árbol final: 39/39.
Extremos, cero, negativos, fuera de rango, 1.230/1.234, unidades y atomicidad
comprobados. CSV conserva negativos como InvalidDecimal, mientras JSON conserva
su error de rango por campo; es una diferencia anterior que no se modifica.

OpenAPI completo idéntico byte a byte antes/después; SHA-256 de ambos archivos:
`74878960b26457a5c6a6667d4dfac598c57037a23e720e02e5288fedfe4eb71e`.
Los cuatro campos de bulto conservan minimum/multipleOf 0.01, maximum 999999999.
Vehículos conserva sus máximos propios. No se detectaron cambios de contrato.
Las capturas temporales se retiraron del código de prueba; quedan aserciones
permanentes de mínimos, máximos y multipleOf en la prueba OpenAPI existente.

## Publicación e integración

[Backend #62](https://github.com/NexoRuta/NexoRuta-Backend/pull/62), base
`ad63712`, head `515a119`, conserva C1/C2 como dos commits. Incluye documentación
de CU-07/CU-08, geocodificación y el registro de refactor del backend.

Regresión combinada final 106/106: búsqueda simulada 26, destinos HTTP 6,
request 21, CSV HTTP 20, capacidad/OpenAPI 16, tarifas/admisión 12, retiros C37 5.
Retiros incluye 1/500/501/1500 bultos, idempotencia, recepción y entrega.
Los resultados se añadieron a la documentación de C2 antes del merge; el cambio
desde el primer head publicado es únicamente Markdown. Se preservan dos commits.

Comandos principales (desde la raíz, con `source scripts/cloud/env-agent.sh`):

```bash
dotnet test backend/tests/NexoRuta.IntegrationTests --no-restore --filter 'FullyQualifiedName~BusquedaDestinoSimuladaHttpTests|FullyQualifiedName~DestinosEnvioHttpTests|FullyQualifiedName~CrearEnvioRequestTests|FullyQualifiedName~ShipmentCsvImportHttpTests|FullyQualifiedName~CapacidadVigenteHttpTests|FullyQualifiedName~TarifaAdmisionHttpTests|FullyQualifiedName~C37_RetiroPorApiIdempotenteEnRutaMixtaConFotoFirmaRecepcionYEntregaComercio'
dotnet test backend/tests/NexoRuta.UnitTests --no-restore --filter 'FullyQualifiedName~PrecisionCargaTests|FullyQualifiedName~CrearEnvioUseCaseTests|FullyQualifiedName~GeocodificadorMapboxTemporalTests|FullyQualifiedName~CsvEnviosParserTests'
```

Avisos existentes NU1510, EF1003 y xUnit2031 durante compilación; sin errores.
El primer build simultáneo produjo un reintento MSB3026 de copia; las
compilaciones y ejecuciones finales se completaron correctamente.

CI backend, head `515a119`, [ejecución 164](https://github.com/NexoRuta/NexoRuta-Backend/actions/runs/43785939777):
compilación aprobada, unitarias completas 399/399 y arquitectura 7/7.
Integración remota completa aprobada: prueba crítica 1/1 y shards 203/203,
245/245 y 353/353; sin omitidas. Cobertura Domain 1911/2066 (92.50 %) y
Application 1835/1945 (94.34 %), ambas superiores al 70 %. El check final
`Backend CI / result` pasó.

Backend #62 mergeada sin squash: `74362b80c706bd6b7941654def7e7c5184b8b2b8`.
Tras el merge se hizo fetch y pull ff-only de backend develop; se verificaron
ese SHA remoto y sus padres `ad63712` + `515a119`. Su árbol es idéntico al head
validado, y contiene C1/C2 como commits separados. No hubo avance adicional ni
conflictos. Fetch raíz previo a la integración mantiene develop en `3b00ef8`.

La PR raíz actualiza únicamente el gitlink backend al merge real `74362b8` y
este registro. Frontend y mobile conservan sus gitlinks originales. Se exige
que Integrated CI resuelva y pruebe ese gitlink antes del merge raíz; el SHA de
merge raíz y el resultado final de sus checks se consultan en la PR enlazada.

[PR raíz #82](https://github.com/NexoRuta/NexoRuta/pull/82), destino develop.
Sus checks `sources`, `backend`, `backend_integration` e `Integrated CI / result` aportan la evidencia
de los gitlinks resueltos y su validación integrada. El merge requiere todos los
checks exigidos por el plan de Integrated CI; este registro no sustituye ese gate.
