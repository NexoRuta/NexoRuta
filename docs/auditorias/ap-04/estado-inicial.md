# AP-04 — Estado inicial de implementación

Fecha: 09/11/2026 (America/Montevideo). Rama seleccionada: `develop` en raíz y submódulos. No se modificaron ni actualizaron gitlinks para arrancar el trabajo.

## Fuentes fijadas

| Árbol | HEAD actual | Gitlink de `develop` | Estado al comenzar |
|---|---|---|---|
| Raíz | `d420dfefc70f0b4e789ae350d4d66bba9e4180a0` | — | sin cambios versionados; ya existían `backend`, `frontend`, `mobile` como gitlinks distintos y `docs/planes/ap-04-devoluciones-comercio.md` sin seguimiento |
| `backend` | `3a7cffefb03967e6a9135a5575676403b7c12d8f` | `1d5e912263368d91135884f9895b71513b99509a` | `develop`, limpio |
| `frontend` | `84444f6a8b42c0f9f164229f520ef6f005bed205` | `fedb7731bb62dcb29a093bc98893c593d4cd8ba7` | `develop`, limpio |
| `mobile` | `329dd3454704c0f45b615d609f469b7fd4b2dd5f` | `53f6be2cdec48f48e30e390060feeaefb5be0ead` | `develop`, limpio |

La combinación implementada se fija a los HEAD materializados de `develop` que aparecen arriba. Los gitlinks divergentes son cambios preexistentes del checkout compartido; no se reemplazan por el manifiesto histórico de `scripts/cloud/checkpoint.json` ni se restauran por rutina. El gitlink de raíz se actualizará al SHA final de cada componente solamente cuando esos cambios estén listos para integrar.

## Herramientas y ejecución

- .NET SDK disponible: `10.0.401`, coincide con `global.json` de los repositorios.
- Los proyectos tienen `packages.lock.json`; restaurar con `--locked-mode`.
- Hay Compose raíz (`compose.yaml`, `compose.override.yaml`, `compose.dev.yaml`) y configuración GCP en `deploy/gcp/compose.yaml`.
- En PowerShell de Windows, `docker` no está en PATH. WSL2 tiene una distribución `Ubuntu`; verificar allí la integración con Docker Desktop/Engine antes de cualquier arranque. No se inició ningún contenedor ni se seleccionó una base persistente.
- `browser-act` y `uv` no estaban instalados inicialmente. El usuario autorizó su instalación; el 10/11/2026 se usó BrowserAct 1.6.2 para inspeccionar Commerce local con cuenta sintética. El circuito interactivo Blazor no llegó a conectarse; ver resultados separados en `validacion.md`.
- Las pruebas de API deben usar `PostgresFixture`/`IntegrationApiFactory` y PostgreSQL/PostGIS propio con los roles runtime. Las pruebas de navegador siguen el aislamiento de `GestionBrowserTests`; HTTP y navegador se ejecutan por separado.

## Base funcional confirmada

- Backend .NET modular: Domain, Application, Infrastructure EF/PostgreSQL y API; `EfRutasRepository` concentra el comando físico existente de devolución. Commerce usa Blazor InteractiveServer, sesión con cookies y ApiClient tipado; Backoffice usa Razor Pages.
- El operador inicia la devolución bajo `envios.gestionar`; la lectura actual de envíos usa `envios.consultar`. Estos permisos no habilitan al comercio a efectuar transiciones operativas.
- En devolución total, recepción en depósito puede registrar `ResultadoBulto.Devuelto` mientras `Custodia=Deposito`. La transferencia actual busca solamente `EnDevolucion`, por lo que deja fuera ese recorrido. El flujo parcial sí llega con `EnDevolucion/Deposito`.
- No hay bandeja AP-04, acuse comercial ni hechos nuevos que acrediten una transferencia física para las operaciones históricas. No derivar acuse ni entrega física solo de `Devuelto`.
- Persistencia nueva requiere migración aditiva, RLS forzada, permisos runtime mínimos y hechos inmutables. No tocar migraciones anteriores, datos existentes ni volúmenes.
- Se mantienen las protecciones B1–B5, la selección persistida, Mapbox temporal (`permanent=false`) y Geoapify simulado/apagado en verificaciones.

## Límites de esta implementación

Implementar AP-04 y validar el camino local disponible. No desplegar a GCP ni ejecutar migraciones sobre Cloud SQL: el plan exige autorización explícita para el destino remoto y la operación. Preparar los artefactos y dejar registrado el gate remoto pendiente. La card no se cierra mientras falte aceptación requerida.
