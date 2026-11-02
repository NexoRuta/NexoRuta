# CU-06 — estado local y trazabilidad

> **Actualización B1 (01/11/2026, posterior a esta auditoría):** se implementaron las correcciones de capacidad vigente, precisión, presentación y permiso puntual. Este documento conserva el corte original; la resolución y las verificaciones actuales están en [05-implementacion-b1.md](05-implementacion-b1.md). CU-06 no se declara cerrado: B2–B5 y aceptación visual siguen separados.

Corte: **01/11/2026**. Auditoría funcional y técnica del checkout local, sin implementación funcional, commits, cambios de rama ni subagentes.

**Conclusión:** la gestión de vehículos está implementada e integrada, no ausente. La validación de carga también existe. No se declara cerrado CU-06: faltan garantías frente a cambios de capacidad, coherencia de precisión y evidencia operativa de la pantalla. La disponibilidad física y las estimaciones solicitadas requieren un incremento explícito, separado del enunciado original.

## Lectura rápida

- [Hallazgos y verificaciones](02-hallazgos.md).
- [Plan mínimo de corrección, sin ejecutar](03-plan-de-correccion.md).
- [Disponibilidad, retorno y estimaciones propuestos](04-disponibilidad-y-estimaciones.md).

## 1. Fuentes, alcance y preservación

Se leyeron `AGENTS.md` raíz, `frontend/AGENTS.md`, las instrucciones proporcionadas y `frontend/DESIGN.md`. No se encontraron otros `AGENTS.md` en los submódulos mediante búsqueda de archivos. Se respetaron el stack Razor Pages/Bootstrap, los límites de tenant y la separación entre inspección estática, HTTP, pruebas y navegador.

| Fuente | Evidencia y autoridad |
|---|---|
| `docs/alcance/Laboratorio__NET_2026.pdf`, §5.1 n.º 6, p. impresa 4/física 5 | Texto original: «Gestión de repartidores y vehículos, con su capacidad de carga.» Extraído directamente con `pdftotext`; no se modificó el PDF. |
| `docs/alcance/Calcs/Casos de Uso - Responsables.xlsm`, `CU obligatorios!A9:I9` | CU-06: «Gestionar repartidores, vehículos y capacidad de carga.» M03, Backoffice, operador/administrador, obligatorio. Leído como ZIP/XML, sin macros. |
| Mismo XLSM, `CU obligatorios!A11:I11`; PDF §5.2 n.º 8, misma página | «Registrar uno o más bultos por envío, con identificación, peso y dimensiones.» Dependencia acotada, no autorización para completar CU-08. |
| `docs/alcance/Monitoreo_2026-10-08_CU.xlsx`, fila CU-08, A9:D9 de la primera hoja | Pide «al menos un bulto» para el primer monitoreo. Leído como ZIP/XML: ese recorte no sustituye la cardinalidad del CU-08 original. No se encontró fila CU-06 en esa búsqueda. |
| `backend/docs/workflow/alcance-funcional.md:14-16` | Catálogo secundario concordante; no sustituye el enunciado. |
| `backend/docs/cu/CU-08-bultos.md` | Reconoce alta de un único bulto; fuente secundaria contrastada con código. No se encontró especificación dedicada `CU-06*.md`. |
| `backend/docs/cu/cierre-jornada.md` | D18 permite cerrar con incidencias y conserva custodia; DEC-01/DEC-07 delimitan efectos. Comportamiento vigente, no defecto automático. |
| `docs/auditorias/cu07/01-requisitos-y-trazabilidad.md` y convenciones de `docs/auditorias/` | Se leyó documentación previa; conserva cortes históricos. No se sobrescribió. No existía `docs/auditorias/cu06/`. |
| Solicitud de esta auditoría | Fuente de las necesidades adicionales: base, horarios, retorno confirmado, aviso y reutilización física segura. |

Solo se inspeccionaron planificación, despacho, jornada, posición y cierre para explicar las dependencias de flota/carga. No se auditó integralmente CU-09 en adelante ni usuarios/permisos. La integración de repartidores se verificó sin rehacer su gestión.

## 2. Repositorios al inicio

Superproyecto con tres submódulos Git (`.gitmodules`), no carpetas de una única solución. Cada componente conserva su propio historial y árbol.

| Checkout | Rama | HEAD efectivo local | Estado inicial |
|---|---|---|---|
| Raíz | `develop` | `1ef21751106e727bb15f4f75d3976196857e2ca1` | ` M backend`, ` M frontend`, ` M mobile` |
| backend | `fix/zonacobertura` | `a0aa204ffc3390606b9f04bc8a57424b598c205c` | Limpio internamente |
| frontend | `fix/zonacobertura` | `e05c0de27702cf9909656bed0a0d389152c25806` | Limpio internamente |
| mobile | `fix/zonacobertura` | `78f65e1ca534888270028d68e7abe86460989e12` | Limpio internamente |

Gitlinks registrados por HEAD raíz:

| Submódulo | Gitlink registrado | Diferencia preservada |
|---|---|---|
| backend | `83cfb12876f042c1d9fe48e2c279fea1503fe63f` | HEAD local distinto; coincide con el antecedente remoto suministrado, **no** con el checkout efectivo. |
| frontend | `e94b7a533df6366ff2a2ff3fdb9177493966eb99` | Misma distinción. |
| mobile | `37ca0da3bcbd044e56bba50726df841fc8cbd5f5` | HEAD local distinto. |

No había archivos funcionales sin commit dentro de los tres submódulos. El `M` de raíz representa gitlinks divergentes, no autoriza actualizarlos. Se usaron los HEAD efectivos y sus archivos locales como fuente de verdad.

El contraste **local** entre los hashes de antecedentes y HEAD encontró tres archivos distintos en backend (controller/repository/tests de zonas) y uno en frontend (`Pages/ZonasCobertura/Detalle.cshtml`). En las superficies de reparto inspeccionadas no hubo diferencias respecto de esos snapshots. Esto no comprueba qué está publicado hoy en GitHub: no se hizo fetch ni consulta remota y no se asumió que `feature/cu07` fuera la rama activa.

Comandos de captura: `git -C <repo> branch --show-current`, `rev-parse HEAD`, `status --short`, `git submodule status`, `git ls-tree HEAD backend frontend mobile` y `git -C <repo> diff --name-only <antecedente> HEAD`.

## 3. Separación de requisitos

| Grupo | Qué se exige o analiza | Qué no se atribuye al original |
|---|---|---|
| **A — CU-06 original** | Gestionar repartidores, vehículos y capacidad. Se inspeccionan alta/consulta/edición/habilitación, validaciones e integración que vuelven útil esa capacidad. | El texto no prescribe DELETE físico, endpoint de detalle, formato nacional de matrícula, algoritmo de empaquetado, base geográfica ni ETA. |
| **B — dependencia CU-08** | Identidad, cantidad, peso y dimensiones de **todos** los bultos usados por la carga. | Completar el alta multibulto o auditar recepción/tarifas como CU independientes. |
| **C — necesidad adicional/aclarada** | Distinguir reserva de ocupación, confirmar retorno, reutilizar con seguridad, base operativa, salida planificada, llegadas/regreso estimados y aviso. | No convertir cada ausencia en incumplimiento literal de CU-06 ni llamar bug a D18. |

La desactivación/reactivación cubre la baja administrativa sin perder referencias. Un DELETE físico o una página de detalle separada no son necesarios para cerrar A si el listado permite consultar y editar lo requerido.

## 4. Recorrido completo de vehículos

| Capa | Implementación observada | Evidencia local |
|---|---|---|
| Navegación | Configuración → **Configuración de reparto**; Repartidores está en Operador y equipo. La flota no tiene entrada titulada «Vehículos». | `frontend/src/NexoRuta.Backoffice/Core/Navigation/BackofficeNavigation.cs:49-58` |
| Pantalla | `/configuracion-reparto`: alta y listado editable de matrícula, peso g, volumen cm³ y Activo; ocultos Id/Version; antiforgery de Razor y `data-single-submit`. | `frontend/src/NexoRuta.Backoffice/Pages/ConfiguracionReparto.cshtml:30-58` |
| PageModel | GET carga política y vehículos; POST conserva objeto/ModelState ante error; no guarda si las lecturas fallan. | `frontend/src/NexoRuta.Backoffice/Features/Reparto/Pages/ConfiguracionRepartoModel.cs:47-81` |
| HTTP cliente | GET/PUT `api/reparto/vehiculos`, JSON y Bearer. | `frontend/src/NexoRuta.ApiClient/Features/Reparto/Clients/ConfiguracionRepartoApiClient.cs:18-26` |
| API | Política `configuracion.gestionar`; listado y upsert, con 400/403/404/409. No GET por Id ni DELETE: no implica falta de consulta/baja lógica. | `backend/src/NexoRuta.Api/Features/Reparto/Controllers/ConfiguracionRepartoController.cs:9-10,40-64` |
| Aplicación | Deriva operador del usuario actual; no lo acepta desde el cuerpo. | `backend/src/NexoRuta.Application/Reparto/UseCases/ConfigurarRepartoUseCase.cs:10-17` |
| Dominio | Trim + mayúsculas invariantes, matrícula hasta 20, capacidades positivas con máximos, Activo y Version. | `backend/src/NexoRuta.Domain/Reparto/Vehiculo.cs:14-34` |
| Repositorio | Bloqueo por operador, creación con Id vacío/versión cero, actualización con versión, búsqueda tenant+Id, unicidad por operador. | `backend/src/NexoRuta.Infrastructure/Reparto/EfConfiguracionRepartoRepository.cs:47-79` |
| Persistencia | UUID; índice único operador/matrícula; `numeric(18,2)` y `numeric(24,2)`; check positivo; token de concurrencia; RLS y FK restrictivas. | `backend/src/NexoRuta.Infrastructure/Reparto/VehiculoConfiguration.cs:12-21`; migración `20261017191056_AddDeliveryPoliciesAndVehicles.cs:76-84` |
| Consumo | Recursos de planificación filtra activos; planificador y reasignaciones verifican carga; hoja guarda snapshot del vehículo. | `RutasController.cs:12-25`, `EfRutasRepository.cs:29-96`, `EfRutasRepository.Reasignaciones.cs:195-215`, `HojaRuta.cs:26-34`, en las mismas carpetas backend de reparto. |

No hay ausencia de CRUD funcional: hay **gestión disponible, con defectos técnicos puntuales y verificación visual pendiente**. Su descubribilidad es mejorable; no se demostró que un usuario real no pueda encontrarla.

## 5. Matriz requisito → evidencia → verificación → estado

Abreviaturas de verificación: **E** análisis estático; **T** pruebas existentes ejecutadas; **P** sonda aislada de auditoría; **V** navegador. Los resultados y filtros exactos están en el documento 02. «Implementado» no equivale a aceptación operativa.

| Grupo / criterio | Implementación y evidencia | Verificación | Estado |
|---|---|---|---|
| A: alta y listado | Flujo completo anterior; prueba `VehiculoTieneCapacidadesYControlDeVersionSinDuplicarMatricula`. | E + T HTTP/PostgreSQL | Implementado |
| A: consulta y edición | Consulta desde listado; PUT por Id; no hace falta detalle separado. | E + T | Implementado |
| A: desactivar/reactivar | Checkbox → PUT → `Actualizar(...activo)`; historial y FK se conservan. | E + P (02) | Implementado, sin aceptación visual |
| A: matrícula y unicidad | Trim/mayúsculas + índice por operador; conflicto 409. Espacios interiores y guiones no se unifican. | E + T | Implementado bajo esa definición de identidad; formato legal pendiente, no exigido |
| A: capacidades positivas | API mínimo 0,01; dominio >0; precisión de DB de dos decimales. | E + P06/P10 | Mínimos/máximos verificados; falta política de escala coherente |
| A: concurrencia de edición | Bloqueo operador + Version + token EF; mensajes de recarga. | E + T + P11 (200/409 concurrentes) | Implementado; UI de conflicto operativa pendiente |
| A: aislamiento | Operador desde sesión, filtro tenant+Id, RLS, FK compuesta con hoja. | E + T con rol restringido + P09 (GET/PUT Id ajeno) | Verificado en escenarios descritos, sin certificar toda combinación de roles |
| A: formulario ante error | Conserva valores y no aumenta versión automáticamente; error global visible. | E; T cubre carga fallida de política, no toda edición de vehículo | Parcialmente verificado |
| A: acceso y localización | Menú requiere configuración; API también. PageModel hereda solo política general de operador. | E + HTTP 302 sin sesión | Disponible; alineación de política de página pendiente |
| A: integración repartidor | Perfil y cuenta activos, rol con `reparto.ejecutar` en plan/despacho; reserva compartida con vehículo. | E + T flujo restringido | Integración implementada; no se reaudita usuarios |
| A/B: carga de todos los bultos | `Sum` sobre conjunto de envíos; no primer elemento. Peso y volumen separados en comparación. | E + T + P | Implementado, con límites de cobertura anotados |
| A/B: composición de ruta | Duplicados de envío rechazados; reasignación usa paradas activas y nueva carga. | E + T | Implementado; no hay editor genérico multibulto |
| A/B: capacidad vigente al despacho | Se revisan habilitación/custodia/estado, no suma ni capacidad actual. | E + P | Defecto de integración H01 |
| B: origen de medidas | `Bultos` persistidos en g/cm; alta CU-07 crea uno. | E + P sobre datos de prueba | Dependencia parcial de CU-08; no se completa aquí |
| A/B: resumen visual | Peso total de todos; no volumen total. Unidad de volumen Razor incorrecta hasta corrección JS. | E, V bloqueada | Defecto H03 + mejora de feedback |
| C: reserva | Al planificar, incluso vacío; por recurso/operador/fecha. Cancelar vacío libera. | E + T | Implementado con semántica por día |
| C: ocupación física entre fechas | No hay garantía independiente de la fecha. | E + P | Brecha H02 frente a necesidad adicional |
| C: fin y reutilización | `RegistrarFin` libera; sucesivas el mismo día son posibles tras cierre aplicado. | E + T + P12 (nueva reserva 200) | Vigente; no prueba retorno físico |
| C: offline | Fin local queda en cola; servidor no libera hasta aplicarlo; replay idempotente. | E + T backend/mobile | Implementado para sincronización, no certificación de retorno |
| C: cierre con pendientes | D18 conserva custodia/incidencias y finaliza hoja/libera reserva. | E + T | Decisión vigente; requiere extensión explícita para nueva disponibilidad |
| C: base operativa | No aparece en Operador, identidad visual ni ConfiguracionReparto. | E | Ausente en superficies inspeccionadas |
| C: salida y ETA | Salida real en ConfirmarCarga; llegadas manuales; sin retorno estimado ni cálculo vial. | E | Funcionalidad adicional por diseñar |
| C: GPS y aviso | Posición con precisión/instante se registra; no alimenta ETA ni aviso confirmado de disponibilidad. | E + T móvil de estados, no proveedor | Dependencia reutilizable, integración faltante |

## 6. Límites del veredicto

- No se certifica producción ni una versión desplegada. La instancia local existente respondió redirección al login; no se escribió en ella.
- El host de navegador y la tubería de Computer Use no estaban disponibles: no hubo revisión visual, teclado, zoom, reflujo ni contraste reales. HTML y pruebas HTTP no sustituyen esa evidencia.
- Se ejecutaron pruebas aisladas con las fixtures existentes; no se migró ni reinicializó la base operativa, no se levantó otra API operativa ni servicios persistentes. TestServer ejecutó HTTP en memoria.
- Gentle-AI: `review mode status` confirmó **on (decided by global)**, sin cambiarlo. Esta entrega es documentación de auditoría, no candidato de implementación funcional; no se inició revisión nativa ni se inventó aprobación.
- Engram resolvió correctamente `nexoruta` y el directorio, pero el hook rechazó acceso por sesión host no registrada. La auditoría no dependió de memoria histórica ni la usó como evidencia del checkout.

**Estado global:** CU-06 original **implementado de manera sustancial, no cerrado**. CU-08 sigue separado y parcial. Disponibilidad física y estimaciones son un incremento planificado, no implementado por esta tarea.
