# Resultados CU09 y regresiones afectadas

2026-11-02. Ejecución Cloud con Docker como agent, sin apt/sudo ni cambios a la configuración publicada.

| Verificación | Resultado |
|---|---|
| `TarifaAdmisionHttpTests` y exportación OpenAPI | 12 aprobadas (11 CU09 + 1 contrato) |
| `ShipmentCsvImportHttpTests` | 18 aprobadas |
| CrearEnvioUseCaseTests + CsvEnviosParserTests | 21 aprobadas |
| OpenApiContractTests + EnviosApiClientTests + CrearEnvioComponentTests | 84 aprobadas |
| `DestinosEnvioHttpTests` | 5 aprobadas |
| `GeocodificacionFullStackBrowserTests` | 2 aprobadas; alta previa y selector/conflicto |
| Páginas del destino + recorrido Chromium del cliente | 9 aprobadas |
| Regresión móvil de incidencias/cierre | 3 aprobadas |
| `destino-mapbox.test.cjs` | 3 aprobadas |
| Matriz general de portales Chromium/axe | 28 comprobaciones sin fallos |
| Verificación runtime | API autenticada 200, PostgreSQL18/PostGIS3.6, 72 migraciones, rol API no superusuario/no bypassrls y FORCE RLS |

Los primeros pases descubrieron fixtures CSV aún con 9 columnas y localizadores ambiguos tras introducir regiones accesibles; se corrigieron las fixtures y selectores, manteniendo las aserciones funcionales. El pase final de `check.sh` aprobó sus pruebas, pero su última consulta de runtime coincidió con un reinicio de previews; se repitió únicamente `dev.py verify` una vez arrancado y aprobó. No se presenta ese primer código de salida como un pase completo del script.

El informe de superficies y las capturas se encuentran en `docs/auditorias/rediseno/02-verificacion-y-capturas.md`. No hubo consumo externo de geocodificación, mapas ni cálculo vial. CU08 conserva su cierre técnico; se verificaron únicamente las regresiones afectadas.

Criterios CU09 implementados y comprobados: cobertura geográfica real, tarifa publicada y modalidad, cálculo multibulto, servidor como autoridad, persistencia atómica/versionada, historia D02/D22, importación atómica e idempotente y aislamiento. No hay un criterio funcional CU09 pendiente identificado dentro del alcance oficial. Los envíos antiguos sin cargo verificable no reciben precios inventados y rechazan ediciones que exigen esa procedencia, según el límite documentado.
