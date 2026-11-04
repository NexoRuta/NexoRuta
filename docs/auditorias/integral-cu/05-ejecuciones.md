# Ejecuciones nuevas observadas y límites

Corte03/11/2026 America/Montevideo. Las cantidades proceden de TRX nuevos, no de tablas de informes anteriores. [ejecuciones.json](ejecuciones.json) conserva nombres/resultados y SHA-256 de los TRX privados, sin credenciales ni logs. Los comandos exactos están en04. No se declara aceptado ningún CU por estos resultados.

| Ejecución nueva | Resultado observado | Qué demuestra / qué no |
|---|---|---|
| `install-agent.sh` | Aprobada; SDK/dependencias, Chromium y Docker PostGIS disponibles | No ejecutó environment-install ni movió gitlinks. Sin apt/sudo |
| Backend UnitTests completo | 308 pasadas,0 fallidas/omitidas | Lógica/oráculos existentes, no circuito humano |
| Integraciones focales | 73 pasadas,0 fallidas/omitidas,2m53s | Recepción CU-10, guard CU-11, historia/migración, rutas/restricciones/concurrencia, capacidad, RLS, diagnóstico/auth y sesiones móviles; no todos los endpoints del sistema |
| Frontend suite ORIGINAL completa, cinco optativos activados | 482 pasadas,0 fallidas/omitidas,1m29s | Incluye Flota/Depósito, recuperación/sesión, reentrada mapa y cinco browsers controlados. Se ejecutó antes de añadir reproducción H02, no se excluyó un fallo para declararla verde |
| Node frontend completo | 21 pasadas,0 fallidas/omitidas | Mapas/cámara/JS con dobles; no hardware |
| Cuatro optativos integrados | 4 pasadas,0 fallidas/omitidas,1m03s | Commerce selector y alta; vehículos; recepción/PDF/QR; API real con PostgreSQL/PostGIS/RLS propio; proveedores controlados |
| Browser real de sesión | 1 pasada,0 fallidas/omitidas,1m06s | Ambos portales,401 demorado/nueva generación, retorno seguro/transitorios; no origen del401 de arranque histórico |
| Mobile Core | 36 pasadas,0 fallidas/omitidas | Lógica portátil; no Android |
| Mobile Application | 85 pasadas,0 fallidas/omitidas | Cola/sincronización/proyección; no SO ni cámara/GPS |
| Mobile Api | 63 pasadas,0 fallidas/omitidas | Contratos/transporte controlado; no conectividad Android real |
| Reproducción nueva H01 | **1 fallida**,0 pasadas/omitidas,18s | Esperado Not Entregado; actual Entregado con PNG estructuralmente inválido. Rol restringido real. Se deja roja, sin corregir producto |
| Reproducción nueva H02 | **1 fallida**,0 pasadas/omitidas,45ms | Dispose tardío del mapa: esperado1, actual0. Barrera determinista JS, no SDK/dispositivo físico |
| ArchitectureTests después de restore ordinario diagnóstico | **2 pasadas,1 fallida**,0 omitidas | H08: oráculo DTO universal incompatible con PDF; dependencia dominio/aplicación sí pasa |
| Restore ArchitectureTests con lock ORIGINAL y `--locked-mode` | **Falla NU1004** | H07 reproducible; no es el antiguo fallo expected2/actual7. No se declara resuelto ningún diagnóstico previo de arquitectura |
| Runtime manual NUEVO start/verify | Aprobado | API y cuatro portales arrancados; API autenticada200; rol API no superuser/no bypassrls; FORCE RLS verificado; PostgreSQL18/PostGIS3.6.4; **74 migraciones** |
| Preparación de actores/zonas nueva | Aprobada | A/B/C1/C2 y usuarios/roles nuevos; geometría oficial UY-MO/franjas; no envíos/rutas/recepciones/carga/salida/entrega/retorno/liberación |
| CSV nuevos con parser real | Aprobada,9/2/2/1 registros de13 columnas | Sintaxis y contrato del archivo; no admisión/cálculo ni presencia física |
| Python helpers | `py_compile` aprobado | Sintaxis, no prueba de todas sus ramas de error |

## Fallos de preparación y honestidad de resultados

- El entorno tardó en iniciar; no se trabajó sobre el checkout viejo mientras arrancaba.
- No se ejecutó environment-install porque su manifiesto es incoherente con los gitlinks. Se leyó y usó install-agent que no hace checkout.
- Un restore no bloqueado de ArchitectureTests actualizó incidentalmente su lock por PdfPig/ZXing. Se inspeccionó el diff y se restituyó **solo ese archivo generado** al original antes de repetir locked-mode: NU1004. El commit de revisión no contiene el cambio.
- El primer polígono sintético de preparación de zona obtuvo400 por geometría fuera del territorio de Uruguay. Se eligió después el departamento oficial existente UY-MO en el runtime nuevo. No se debilitó validación ni se cambió territorio. Esa400 no se clasifica como defecto.
- El primer juego CSV de preparación usaba una referencia ya equivalente como fila válida del negativo de atomicidad. Se preservó sin importarlo y se generó otro juego **nuevo** con referencia ATOMICO única. Se usará solo `auditoria03novfinal`. El oráculo debe probar ausencia de un alta NUEVA, no la ausencia de un duplicado que ya sería idempotente.
- Las dos reproducciones nuevas fallan por las aserciones esperadas, no por compilación, conexión, Skip o tiempo de espera. Se conservan rojas deliberadamente en ramas de revisión; ejecutar suite completa de esas ramas debe mostrarlas.

## Calidad y alcance de los oráculos

La independencia es acotada: la prueba de PNG deriva su invalidez del formato, no de `GuardarEvidencia`; el mapa comprueba que el recurso retornado después de abandonar se libere. La paridad SQL/dominio sí usa la misma función de dominio como referencia y por ello no es un oráculo independiente de las decisiones de negocio; se complementó leyendo unitarias de aristas, diagramas y políticas. Una prueba que exige las mismas reglas que implementó no puede decidir D-P01/D-P02.

En concurrencia se inspeccionaron barreras/esperas PostgreSQL y efectos finales, no solo ejecución paralela nominal. El browser de recepción introduce una pérdida de respuesta después del commit y comprueba retry sin nuevos hechos; la API en memoria de cinco browsers no demuestra persistencia. Los errores de SDK/proxy no deben contarse como defectos de negocio ni ocultarse con `.first()` o ampliaciones de timeout. No se añadieron exclusiones ni se cambiaron aserciones existentes.

## No ejecutado / pendiente

Suite completa de integración Backend (solo73 focales +4browser +sesión +repro); todas las migraciones con datos legados de cada corte; todos los roles/tablas RLS; stack SMTP/broker/Kafka/Mongo/observabilidad real; carga/costos remotos, dos API balanceadas, IaC/deploy; Android/MAUI, almacenamiento cifrado inspeccionado en dispositivo, cámara/lector/firma/biometría/GPS/Bluetooth/push real; validación humana de los30CU. No se afirma revisión nativa/Gentle-AI/Engram ni resolución de CU-06/401 histórico.
