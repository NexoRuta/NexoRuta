# CU-06 B1 — capacidad vigente y precisión

Corte de implementación: **01/11/2026**, sobre los mismos HEAD de la auditoría. Se conservan sus documentos como evidencia histórica. Este incremento no implementa B2–B5 ni cierra todo CU-06.

## Cambios implementados

| Hallazgo | Resolución |
|---|---|
| H01 | Planificación, reasignación, despacho y confirmación de salida usan la ficha vigente del vehículo del operador, dentro de las transacciones/bloqueos existentes. La hoja conserva su snapshot histórico. |
| H03 | HTML inicial y JS convierten g→kg y cm³→m³; resumen con peso/volumen/capacidades y avisos independientes. El volumen extremo no rompe el render: se identifica como fuera de rango representable. |
| H04 | Capacidades entre 0,01 y máximos existentes; hasta dos decimales **efectivos**. `1.005` se rechaza por campo, `1.00`/`1.000` se aceptan sin cambiar su valor. Se aplica la misma regla mínima a las medidas de bultos. |
| H07, solo autorización puntual | `/ConfiguracionReparto` exige `configuracion.gestionar`, igual que menú/API. No se auditó ni rehízo la administración general de permisos. |
| H08 | Acumulación de carga acotada por capacidad; no necesita representar un total que ya excede el límite. Detecta peso, volumen o ambos sin overflow no controlado. |

### Carga y atomicidad

`Domain/Reparto/CapacidadCarga.cs` es una regla pequeña compartida; no depende de EF/HTTP ni introduce repositorios. Deduplica por UUID de bulto y compara igualdad como válida. Conserva el producto exacto de dimensiones antes de comparar; no redondea volumen por bulto. Cada dimensión se acumula solo mientras no se haya excedido. El producto extremo de un registro histórico también se convierte en exceso, no en excepción al consumidor.

Planificar/despachar/reasignar consultan todos los bultos de las paradas activas correspondientes. Reasignación no usa las capacidades del snapshot como permiso físico. La salida valida habilitación y **carga físicamente bajo custodia de la ruta**, incluyendo bultos de paradas suspendidas y rendiciones aún pendientes de recepción en depósito. Suspender o declarar rendición no prueba descarga.

En `ConfirmarCarga`, las comprobaciones de capacidad/estado preceden a suspensiones y transiciones. El mecanismo existente puede guardar el conflicto y avanzar su secuencia/versión de diario, pero no confirma salida ni altera parcialmente envíos, custodia o paradas. No se tocó la semántica de cierre con incidencias, ni se libera un recurso por desactivar vehículo.

### Precisión, cultura y consumidores

- Dominio protege capacidades y medidas de bultos; API y ApiClient tienen una anotación de precisión por campo, separada entre repositorios desplegables. No se agregó dependencia entre frontend y Domain.
- El POST de configuración interpreta los números HTML con cultura invariante y vuelve a validar esas propiedades. La regresión detectó que el binder cultural podía interpretar `1.005` como `1005`; se corrigió solo esta pantalla, no el binder global. Conserva los valores crudos de ModelState, errores y versión enviada, sin reintento con versión nueva.
- Formulario con min/max/step, mensajes asociados y labels existentes. Se conserva SSR sin skeleton artificial. Commerce reutiliza el contrato validado de alta de un bulto y alinea sus controles numéricos; no se implementa cardinalidad multibulto.
- CSV valida escala antes de crear candidatos/huellas. Error de fila `InvalidPrecision`, HTTP 422 y sin escrituras parciales. `HuellaSolicitudEnvio`, su versión y formato **no se modificaron**; `G29` sigue haciendo equivalentes ceros finales. Las identidades históricas no se recalculan ni eliminan.
- Cambio explícito de contrato: solicitudes nuevas/reintentos con precisión significativa adicional dejan de aceptarse; no se redondean para hacerlas coincidir con una referencia existente. Un CSV histórico con esos valores requiere corrección consciente del cliente y puede entrar en conflicto con su referencia previa. No se proporciona compatibilidad silenciosa ni se migra su huella.
- Dos fixtures de importación que usaban tres decimales como datos incidentales ahora usan valores válidos de dos, conservando sus asserts de idempotencia/estado terminal. La nueva regresión prueba expresamente el rechazo de `1.005` y la equivalencia `1.00`/`1.000`; no se eliminó el comportamiento de negocio cubierto por aquellas pruebas.
- OpenAPI generado y snapshot frontend agregan `multipleOf: 0.01` a las seis propiedades de entrada afectadas. No cambian nombres, rutas ni estructura JSON. No se agregaron ni aplicaron migraciones: las columnas actuales ya son de escala dos.

## Evidencia de pruebas

### RED observado antes de corregir

| Lote | Resultado baseline |
|---|---|
| `CapacidadVigenteHttpTests` | 10 fallos esperados / 4 aprobadas: reducción/salida/reasignación permitidas, mensaje sin dimensión/unidades, escala aceptada y overflow extremo. |
| `PrecisionCargaTests` inicial | 2 fallos esperados / 1 aprobada: dominio aceptaba precisión adicional; ceros finales ya eran equivalentes. |
| Tests iniciales de página/contrato de vehículo | 3 fallos esperados / 1 aprobada: política de página, resumen y precisión del modelo. |

Las pruebas HTTP persistentes usan múltiples bultos sembrados en la fixture aislada, no un alta pública multibulto nueva. Verifican estado persistido, snapshots, respuesta HTTP y ausencia de mutaciones operativas en rechazo; en el diario se admite únicamente el conflicto idempotente previsto.

### Comandos y resultados finales

| Verificación final | Resultado observado |
|---|---|
| Integración pertinente backend | **116 aprobadas**, 0 fallos/omitidas; exit 0; 7 m 38 s. Incluye carga vigente, escala, CSV/idempotencia, rutas, rol restringido y ejecución/cierre/discrepancias. |
| Recheck focalizado de aislamiento/OpenAPI tras agregar sus regresiones | **3 aprobadas**, 0 fallos/omitidas; exit 0; 29 s. No se suman como casos únicos al lote anterior. |
| Unitarias backend | **227 aprobadas**, 0 fallos/omitidas; exit 0; 4 s. Incluye dominio, no redondeo/duplicados y consumidores existentes de creación/tarifas sin modificar estos últimos. |
| Frontend pertinente final | **230 aprobadas**, 0 fallos/omitidas; exit 0; 36 s. Reejecución posterior a correcciones del formulario. |
| JS real con DOM de prueba | **1 aprobada**, exit 0; conversión 1.000 g→1 kg y 4.000.000 cm³→4 m³, todas las filas y excesos independientes. |
| Arquitectura | **2 aprobadas / 1 fallo preexistente**, exit 1. `ShipmentBoundaryTests.ShipmentEndpoints_DeclareApiOwnedResponses`, línea 30: esperaba 2 respuestas, encuentra 7. |
| Baseline de arquitectura | Mismo **2/1**, mismo assert 2 vs 7, en exportación externa del HEAD `a0aa204...` sin modificaciones. No causado por B1; no se corrigió fuera de alcance. |
| Integridad del diff | `git diff --check` en raíz/backend/frontend sin errores; documentos UTF-8, cercas y enlaces verificados. |

```powershell
# Regresiones funcionales y contrato (PostgreSQL efímero + TestServer).
dotnet test backend/tests/NexoRuta.IntegrationTests/NexoRuta.IntegrationTests.csproj --no-restore --filter 'FullyQualifiedName~CapacidadVigenteHttpTests|FullyQualifiedName~CrearEnvioRequestTests|FullyQualifiedName~ConfiguracionRepartoHttpTests|FullyQualifiedName~RutasHttpTests|FullyQualifiedName~RepartoRestrictedHttpTests|FullyQualifiedName~ShipmentCsvImportHttpTests|FullyQualifiedName~OperacionesRepartoHttpTests' --nologo --logger 'console;verbosity=minimal'

dotnet test backend/tests/NexoRuta.UnitTests/NexoRuta.UnitTests.csproj --no-restore --nologo --logger 'console;verbosity=minimal'
dotnet test backend/tests/NexoRuta.ArchitectureTests/NexoRuta.ArchitectureTests.csproj --no-restore --nologo --logger 'console;verbosity=minimal'

dotnet test frontend/tests/NexoRuta.ApiClient.Tests/NexoRuta.ApiClient.Tests.csproj --no-build --no-restore --filter 'FullyQualifiedName~BackofficeSessionAndPagesTests|FullyQualifiedName~SpecializedApiClientTests|FullyQualifiedName~OpenApiContractTests|FullyQualifiedName~ImportacionEnvios|FullyQualifiedName~CrearEnvioComponentTests|FullyQualifiedName~EnviosApiClientTests' --nologo --logger 'console;verbosity=minimal'
node --test frontend/tests/rutas-planificacion.test.cjs

# Regresiones nuevas de contrato/tenant, tras terminar el runner anterior.
dotnet test backend/tests/NexoRuta.IntegrationTests/NexoRuta.IntegrationTests.csproj --no-restore --filter 'FullyQualifiedName~LiveVehicleChecks|FullyQualifiedName~GeneratedOpenApi' --nologo --logger 'console;verbosity=minimal'
```

Logs de ejecución en TEMP: `cu06-b1-red-backend.log`, `cu06-b1-red-precision.log`, `cu06-b1-red-frontend.log`, `cu06-b1-regression-backend.log`, `cu06-b1-unit-regression.log`, `cu06-b1-architecture.log`, `cu06-b1-regression-frontend-final.log`. Son resultados de esta tarea, no de la auditoría anterior.

Baseline reproducible: `git -C backend archive HEAD` exportado fuera del checkout a `%LOCALAPPDATA%/Temp/NexoRuta-CU06-B1-baseline-8dc2c41ed2754efc921d9d8aaeaed139/`; restauración desde el caché local existente de NuGet, sin nuevos paquetes/dependencias. Se ejecutó allí el mismo `dotnet test tests/NexoRuta.ArchitectureTests/NexoRuta.ArchitectureTests.csproj --no-restore`. No se hizo checkout, worktree, cambio de rama ni modificación de la prueba para ocultar el fallo. Se conserva su log `architecture-baseline.log`.

Al cierre se verificó la ruta absoluta propia dentro de TEMP, ausencia de reparse point y ausencia de proceso de baseline; se copió el log a `%TEMP%/cu06-b1-architecture-baseline.log`. La retirada de ese directorio temporal fue rechazada por política **antes de ejecutarse**. Se conserva, sin intentar otro mecanismo de borrado; no se limpió el checkout ni se tocó el scratch de la auditoría anterior.

Incidentes intermedios: el test de validación de bulto contaba exactamente cuatro mensajes, pero ahora puede haber rango y precisión para un mismo campo; se ajustó a comprobar los cuatro campos inválidos, sin debilitar su rechazo. Una ejecución frontend tuvo timeout en el test de propagación de cancelación bajo carga; el recheck focalizado de los cuatro casos pasó sin tocar ese cliente/test. El formulario nuevo detectó dos detalles corregidos: cultura decimal y estado de validación de ModelState al revalidar. Un build de tests de integración lanzado mientras el runner anterior usaba su DLL falló por bloqueo Windows (MSB3027); no fue un fallo de negocio ni se cambió implementación por él.

### Separación de evidencia

- **Compilación:** compilaciones implícitas de los proyectos probados; no se afirma build de soluciones completas ni MAUI.
- **HTTP:** TestServer contra bases efímeras propias y fakes del cliente; no se escribió en la API operativa existente.
- **Automatización JS:** Node ejecuta el script real con DOM de prueba, no un navegador ni certificación visual.
- **Visual/navegador:** se intentó `cua.getState()`; sigue sin host de navegador ni tubería de Computer Use. Quedan pendientes formulario real, teclado/foco, 320 CSS px, zoom y revisión visual. No se sustituyen por HTML/HTTP.
- **Infraestructura:** fixtures temporales existentes; sin migrar/reinicializar DB operativa, desplegar, contratar servicios ni agregar dependencias.

### Gentle-AI y memoria

Modo de revisión existente: **on, global**, sin cambiar configuración. Assess se ejecutó en ambos submódulos con escalación por item 3 en backend (validaciones/contratos compartidos) e item 2 en frontend (autorización). Ambos devolvieron `risk: high`, `review_due: true`, `unassessable` por requerir declaración explícita del inventario untracked. No se excluyeron los tests/helpers nuevos para obtener un resultado favorable ni se afirmó aprobación. La continuación nativa se trata por su protocolo, separada del resultado funcional; no hay commits ni publicación autorizados.

Resultado de la continuación canónica, ejecutada con cada submódulo como cwd:

- **Backend:** `review.status` v9 devuelve `collect`, razón `intended_untracked_selection_required`, operación exacta `external.select_intended_untracked`. Inventario: anotación API, helper de carga y dos archivos nuevos de tests. La búsqueda de herramientas expuestas no encontró esa operación. **Revisión nativa pendiente por operación no disponible en este runtime**; no se fabricó selección, START, consentimiento, PASS ni recibo. El primer STATUS con lentes devolvió `invalid_request/not_started`; se corrigió conforme a su indicación usando el STATUS mínimo, no se intentó reutilizar autoridad.
- **Frontend:** STATUS devuelve `stop/rdd_disabled`, horizonte terminal. Se respetó ese resultado específico del repositorio; no se ejecutó enable ni se cambió preferencia. Revisión **disabled/unmanaged**, no aprobada.
- No hubo START ni transacción nativa congelada en ninguno de los dos. No se lanzó un revisor/subagente. La implementación y sus pruebas se entregan con estas limitaciones explícitas; no se usa el resultado para autorizar commits o publicación.

Engram sigue rechazando la sesión host no registrada. No se afirma guardado de memoria/espejo: la trazabilidad está en este informe y `odd/tasks/cu06-b1.md`. El usuario prohibió subagentes, por lo que se trabajó inline y no se simuló un verificador independiente.

## Archivos afectados

Backend (relativos a `backend/`):

```text
src/NexoRuta.Domain/Reparto/CapacidadCarga.cs
src/NexoRuta.Domain/Reparto/Vehiculo.cs
src/NexoRuta.Domain/Envios/Bulto.cs
src/NexoRuta.Infrastructure/Reparto/EfRutasRepository.cs
src/NexoRuta.Infrastructure/Reparto/EfRutasRepository.Reasignaciones.cs
src/NexoRuta.Infrastructure/Reparto/EfOperacionesRepartoRepository.Ejecucion.cs
src/NexoRuta.Api/Validation/DosDecimalesAttribute.cs
src/NexoRuta.Api/Features/Reparto/Contracts/VehiculoContract.cs
src/NexoRuta.Api/Features/Envios/Contracts/Requests/CrearEnvioRequest.cs
src/NexoRuta.Api/Program.cs
src/NexoRuta.Application/Envios/Importacion/ImportarEnviosUseCase.cs
tests/NexoRuta.IntegrationTests/Reparto/CapacidadVigenteHttpTests.cs
tests/NexoRuta.IntegrationTests/Envios/CrearEnvioRequestTests.cs
tests/NexoRuta.IntegrationTests/Envios/ShipmentCsvImportHttpTests.cs
tests/NexoRuta.UnitTests/Envios/PrecisionCargaTests.cs
```

Frontend (relativos a `frontend/`):

```text
src/NexoRuta.ApiClient/Core/Validation/DosDecimalesAttribute.cs
src/NexoRuta.ApiClient/Features/Reparto/Contracts/VehiculoResponse.cs
src/NexoRuta.ApiClient/Features/Envios/Contracts/Requests/CrearEnvioRequest.cs
src/NexoRuta.Backoffice/Features/Reparto/Pages/ConfiguracionRepartoModel.cs
src/NexoRuta.Backoffice/Pages/ConfiguracionReparto.cshtml
src/NexoRuta.Backoffice/Pages/Rutas/Planificar.cshtml
src/NexoRuta.Backoffice/Program.cs
src/NexoRuta.Backoffice/wwwroot/js/rutas-planificacion.js
src/NexoRuta.Commerce/Components/Features/Envios/Pages/CrearEnvio.razor
contracts/nexoruta.openapi.json
tests/NexoRuta.ApiClient.Tests/CapacidadCargaPagesTests.cs
tests/NexoRuta.ApiClient.Tests/RutasPagesTests.cs
tests/rutas-planificacion.test.cjs
```

Raíz: este informe, notas de resolución agregadas a los cuatro documentos previos y `odd/tasks/cu06-b1.md`. Mobile no se modificó. Ramas, HEAD, cambios locales previos y gitlinks divergentes se preservan; no hubo commits.

## Pendientes deliberadamente conservados

H02/H05/H09 siguen abiertos: ocupación entre fechas, retorno/disponibilidad confirmados separados del cierre, base y ETA vial/GPS. H06 solo recibe las guardias de habilitación/capacidad de B1, no un modelo nuevo de ocupación. H07 no se declara cerrado en toda su dimensión UX/accesibilidad sin revisión visual.

Siguiente bloque recomendado: B2, con decisión explícita sobre separar cierre administrativo de retorno/aptitud, preservando D18. No comenzó en esta tarea.

Risk: item 2 (política de autorización de página); item 3 (validación compartida de capacidad y precisión en productores/consumidores).
