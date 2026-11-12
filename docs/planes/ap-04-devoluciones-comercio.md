# AP-04 — Plan de implementación de devoluciones del comercio

Análisis inicial: 09/11/2026; actualización de ejecución: 12/11/2026 (America/Montevideo). Destinatario: agente de IA que implementa la feature. Estado: **implementación en develop, Integrated CI verde y aceptación pendiente; la card AP-04 está en Do tests**. Los resultados y límites verificados se registran en `docs/auditorias/ap-04/validacion.md`.

Card consultada mediante MCP de Notion: [AP-04 — Consulta y gestión de devoluciones del comercio](https://app.notion.com/p/40a032f1caff816a8c01c160a9e10c18). Estaba en **In progress** al comenzar; el 12/11 se movió a **Do tests** tras completar implementación/CI y registrar los gaps de aceptación. Prioridad Media, módulo M02. Pasar a Done solo cuando se prueben los criterios de cierre.

## 1. Fuentes y resultado requerido

Se leyó el PDF y el contenido OOXML de la planilla sin ejecutar macros. No interpretar colores ni reportes de otras revisiones como prueba del código actual.

| Fuente | Exigencia que afecta AP-04 |
| --- | --- |
| `docs/alcance/Laboratorio__NET_2026.pdf`, §4, página física 4 / impresa 3 | El portal del comercio es Blazor y debe ofrecer gestión de devoluciones. Backoffice conserva la gestión operativa del operador. |
| Mismo PDF, §3.3 | El comercio accede exclusivamente a su información y puede trabajar con varios operadores. El operador es el tenant. |
| `docs/alcance/Calcs/Casos de Uso - Responsables.xlsm`, `Alcance aplicaciones!A7:G7` | AP-04: «El comercio consulta y gestiona devoluciones de sus envíos». M02, Portal Blazor, §4. Estado de definición: **Detalle funcional a diseñar**. Es una capacidad obligatoria, sin CU propio. |
| `docs/alcance/Entregas/Entrega-10-4-2026-Grupo-4.pdf`, Anexo B, página 12 | Reitera AP-04 y que esas capacidades son obligatorias y necesitan definición funcional. |
| PDF original, §5.1/4, §5.2/11–12 y §5.4/22; planilla CU-04/11/12/22 y D03/D13 | Reglas versionadas por operador, transiciones declarativas, eventos inmutables y devolución/rendición al depósito. |
| `docs/alcance/ADR-MT-001-PostgreSQL-RLS.md` | Identidad contextual, operador por envío, roles restringidos, contexto transaccional y aislamiento también en PostgreSQL. No exigir una membresía permanente comercio–operador inexistente. |
| `docs/cambios-requerimientos/Cambios de Requerimientos Planificados.pdf`, requisitos 31–34 | Cada bulto puede entregarse, quedar pendiente o devolverse independientemente. El estado agregado puede permanecer EntregadoParcialmente. Reglas capturadas y visitas históricas se conservan. |
| Mismo documento, requisitos 37–41 | El retiro desde el comprador tiene un ciclo y modalidad propios. Reutilizarlo solo si se necesita ese caso; no confundir un retiro nuevo con la devolución de un envío existente. |
| PDF original §6.1–6.6, §6.8, §6.12–6.15 | Arquitectura modular, autorización, migraciones, concurrencia, outbox donde corresponda, observabilidad, ejecución multiinstancia, CI y despliegue remoto HTTPS. |

**Resultado verificable:** el comercio autorizado encuentra las devoluciones de sus envíos por operador, comprende la situación de cada bulto y puede realizar una acción de gestión persistente y trazable. Una pantalla de solo lectura o mostrar `Devuelto` en Mis envíos no basta para cerrar AP-04.

La letra no define quién solicita la devolución, un proceso de aprobación, una devolución posventa, una devolución de dinero, una prueba de recepción del comercio ni un plazo para esa recepción. Las decisiones del apartado 3 son una propuesta concreta del proyecto, no texto docente.

## 2. Base actual y brechas confirmadas

Snapshot inspeccionado, que el agente debe volver a verificar al comenzar:

| Repositorio | HEAD materializado |
| --- | --- |
| Raíz, develop | `d420dfefc70f0b4e789ae350d4d66bba9e4180a0` |
| Backend, develop | `3a7cffefb03967e6a9135a5575676403b7c12d8f` |
| Frontend, develop | `84444f6a8b42c0f9f164229f520ef6f005bed205` |
| Mobile, develop | `329dd3454704c0f45b615d609f469b7fd4b2dd5f` |

Los submódulos están limpios, pero sus HEAD difieren de los gitlinks registrados en la raíz. Es trabajo existente: no ejecutar un submodule update que lo sustituya ni usar `--remote`. `scripts/cloud/checkpoint.json` es histórico y no selecciona las fuentes de esta implementación.

| Capacidad existente | Evidencia de código | Consecuencia para el plan |
| --- | --- | --- |
| Inicio de devolución por decisión operativa | `GestionarRutasUseCase.IniciarDevolucionAsync`, `EfRutasRepository.Reasignaciones.cs`, `POST /api/envios/{id}/iniciar-devolucion` | Reutiliza reglas capturadas, intentos, versión, actor y ComandoId. Commerce no debe obtener esa autorización de operador. |
| Resultados independientes y custodia por bulto | `Domain/Envios/ResultadoBulto.cs`, `Bulto.cs`, `AgregacionBultos` | Consultar resultados/custodia por bulto, no solo EstadoEnvio. No modificar bultos entregados para devolver otros. |
| Rendición, recepción y cierre con incidencias | `EfOperacionesRepartoRepository.*`, `EfRutasRepository.RecibirAsync`, `backend/docs/cu/cierre-jornada.md` | Rendición declarada no prueba recepción física; cierre, retorno y liberación de recursos son hechos distintos. |
| Devolución física al comercio | `EfRutasRepository.Recepcion.cs`, `POST /api/deposito/envios/{id}/devolucion-comercio`, Backoffice `Pages/Rutas/_Deposito.cshtml` | Ya mueve bultos EnDevolucion desde Deposito a Comercio y registra Devuelto. Está limitado al actor operador y usa versión del envío. |
| Semántica de devolución total | `EfRutasRepository.RecibirAsync` | En el recorrido de envío completo EnDevolucion, recibir en depósito ya cambia resultados a Devuelto y estado a Devuelto. Por tanto **Devuelto no demuestra custodia Comercio**. |
| Brecha entre recorridos total/parcial | El comando de devolución al comercio selecciona solo Resultado=EnDevolucion; la UI usa el mismo criterio | Los bultos Devuelto que siguen en Deposito pueden quedar fuera de esa acción. Debe reproducirse y resolverse como parte del circuito AP-04. No suponer que ambos recorridos ya son equivalentes. |
| Lectura Commerce | `MisEnvios.razor` muestra EnDevolucion/Devuelto; `ListarEnviosUseCase`/`EfEnviosRepository` | No existe bandeja/gestión propia de devoluciones. Evitar descargar todos los envíos y filtrar en el navegador. |
| Permisos | `Domain/Administracion/CatalogoPermisos.cs` | `envios.consultar` sirve a ambos ámbitos; `envios.gestionar` es exclusivo de Operador. No ampliarlo a Comercio. |
| Navegación y host | `CommerceNavigationCatalog.cs`, Commerce `Program.cs` | Blazor InteractiveServer, cookies, ApiClient, autorización API, antiforgery y Data Protection ya existen. |
| Finanzas | `docs/gestion/reportes-liquidaciones-cuenta.md` | Los cargos de devoluciones permanecen visibles/retenidos según política existente. Un acuse no genera reembolso, pago ni liquidación. |

## 3. Decisión funcional propuesta para completar «gestionar»

Adoptar el siguiente flujo en una especificación/ADR de AP-04 antes de escribir comandos. Es la propuesta mínima completa de este plan; el equipo debe confirmar su adecuación al alcance académico durante la revisión del diseño. Si solicita otra interpretación, registrar el cambio y revisar contrato/matriz antes de implementar; nunca presentar esa decisión como requisito literal.

1. El **operador** inicia la devolución según las reglas capturadas y registra rendición, recepción y transferencia física. Sus autorizaciones permanecen separadas.
2. El **comercio** consulta una bandeja de devoluciones y su detalle por bulto. Puede registrar un **acuse de recepción conforme o con observaciones** sobre bultos que el operador ya entregó físicamente a ese comercio.
3. El acuse es un hecho propio, inmutable, con actor, fecha y selección de bultos. No cambia EstadoEnvio, ResultadoBulto, custodia, rutas, precios ni reservas. Las observaciones permiten gestionar una diferencia sin declarar automáticamente un extravío ni cerrar una incidencia AP-01.
4. El operador registra la transferencia física para un conjunto explícito de bultos elegibles y presentes. Esa operación sí cambia custodia y, cuando corresponda, resultado/estado mediante las reglas canónicas. No es un simple click de «visto» del comercio.
5. No introducir solicitudes de devolución posventa ni permitir al comercio forzar EnDevolucion o Devuelto. Si se requiere recoger mercancía desde el comprador, usar el retiro existente bajo su contrato; AP-04 no lo crea automáticamente.
6. No exigir fotos, firma, documento personal o GPS del navegador para un acuse si el equipo no adopta explícitamente esa política adicional. Fecha de registro: reloj UTC del servidor. Nunca generar evidencia física o ubicación ficticia.

### Estados de presentación y acciones

Son situaciones derivadas, no nuevos valores de EstadoEnvio:

| Situación por bulto | Información visible | Acción Commerce |
| --- | --- | --- |
| EnDevolucion y custodia Repartidor/PendienteDeposito | En retorno / recepción pendiente | Consultar; sin acuse |
| EnDevolucion o Devuelto y custodia Deposito con procedencia de devolución verificable | En depósito, pendiente de entrega al comercio | Consultar; sin acuse |
| Resultado Devuelto, custodia Comercio y transferencia trazable posterior al corte | Entregado al comercio, pendiente de acuse | Registrar acuse si tiene permiso |
| Transferencia con acuse | Recibido conforme / recibido con observaciones, actor y fecha | Consultar el acuse; no editarlo |
| Envío EntregadoParcialmente con bultos devueltos | Conservar el agregado y mostrar cada resultado | Operar solo los bultos de devolución elegibles |
| Cancelado/Extraviado u otra excepción con historia de retorno | Mostrar estado y custodia reales, explicar bloqueo | Consulta; no habilitar una transición por el mero historial |
| Hecho anterior al corte sin transferencia suficientemente atribuible | Histórico; acuse no disponible y motivo | Consulta; no fabricar transferencia ni acuse |

Al mostrar datos legados, separar «lo que dice el estado comercial», «custodia actual» y «hechos acreditados». Si existe evidencia histórica suficiente puede reutilizarse como fuente identificada; no backfillear una entrega física deduciéndola solo de Devuelto. Una corrección histórica exige un procedimiento explícito, fuera del backfill automático.

## 4. Arquitectura y contratos objetivo

### Distribución de responsabilidades

- **M02 / Domain.Envios:** invariantes de transferencia y acuse en tipos pequeños; mantener estado/custodia existentes como autoridad. No agregar dependencias EF/ASP.NET, red ni reloj estático al dominio.
- **Application.Envios/Devoluciones:** consultas/DTOs, validación, autorización del actor y coordinación mediante puertos tipados. Crear casos de uso separados de lectura, transferencia operativa y acuse de comercio. No crecer el caso de uso de rutas con toda la feature.
- **Infrastructure.Envios/Devoluciones:** implementaciones PostgreSQL/EF, transacciones, bloqueos, RLS y escritura auditada. La transferencia existente debe tener un solo escritor: extraer/delegar su lógica a esta capacidad o a un puerto compartido de aplicación, manteniendo la entrada operativa. No duplicar algoritmos en Reparto y Commerce.
- **API.Features.Envios/Devoluciones:** DTOs HTTP propios, políticas, errores y composición. No devolver entidades EF ni DTOs internos de Application como contrato público. Usar las convenciones de `ShipmentBoundaryTests`.
- **ApiClient.Features.Devoluciones** y **Commerce.Components.Features.Devoluciones:** cliente HTTP tipado y páginas Blazor InteractiveServer. Reutilizar sesión/errores/servicios y componentes existentes.
- **Backoffice:** ajustar su acción de entrega física y su ApiClient al contrato común; no darle acceso al acuse del comercio ni rediseñar todo Depósito.
- **Workers y Mobile:** conservar responsabilidades existentes. AP-04 no requiere un proceso nuevo, un broker nuevo ni cambiar la app móvil. Revisar consumidores existentes si cambia un contrato que realmente comparten.

### Contrato HTTP propuesto

Los nombres nuevos son propuesta de implementación. Congelar nombres, unidades, límites, ejemplos y códigos en la especificación antes de usarlos en tests/clientes. Actualizar productores y consumidores juntos; no agregar aliases o un contrato v1 paralelo para mantener versiones anteriores.

| Método/ruta propuesta | Contrato |
| --- | --- |
| `GET /api/devoluciones?operadorId=...&desde=...&hasta=...&situacion=...&cursor=...&limite=...` | Comercio contextual; filtro por operador explícito, período de actividad de devolución, situación y búsqueda acotada por referencia. Paginación estable en servidor. |
| `GET /api/devoluciones/envios/{envioId}?operadorId=...` | Resumen propio, estado real y cantidades por situación; referencias para páginas de bultos, transferencias y acuses. |
| `GET /api/devoluciones/envios/{envioId}/bultos?...` | Página de bultos de devolución; resultado, custodia, motivo permitido, versión y acciones disponibles con causa de bloqueo. |
| `GET /api/devoluciones/envios/{envioId}/historial?...` | Hechos de devolución/transferencia/acuse autorizados y paginados; separar fecha física acreditada y registrada. No exponer payloads de operaciones móviles ni evidencias privadas por defecto. |
| `POST /api/devoluciones/transferencias/{transferenciaId}/acuses` | `ComandoId`, versión de la transferencia, IDs/versiones o pertenencia estable de bultos, resultado conforme/con observaciones y observaciones por bulto. Comercio/actor inferidos de la sesión. |
| Existente `POST /api/deposito/envios/{id}/devolucion-comercio` | Enriquecer a comando explícito con ComandoId, VersionEnvio, conjunto de bultos/versiones y confirmación de transferencia física. Misma operación de negocio para todos los caminos. Actualizar endpoint/cliente/Backoffice/tests juntos. |

Reglas del contrato:

1. `ComercioId`, usuario y acceso nunca vienen como autoridad desde el body. `OperadorId` identifica el contexto elegido y se valida contra la propiedad real del envío; no equivale a autorización.
2. Páginas de 1–100 elementos y cursor estable por `(FechaActividadUtc, Id)`, con corte superior de consulta si se necesita estabilidad entre páginas. Definir el cursor como opaco, validado y asociado a los filtros, sin SQL interpolado. Orden total también para fechas iguales.
3. Período `[desde,hasta)`, ISO-8601 UTC en API; convertir fechas de UI explícitamente desde America/Montevideo. Definir qué evento determina FechaActividad; no filtrar solamente por fecha de admisión y perder devoluciones recientes de envíos viejos. Rechazar rangos inválidos y limitar el rango interactivo, proponiendo 90 días y paginación para histórico.
4. Detalle, historial y bultos no pueden crecer sin límite. Soportar envíos con 501/1500 bultos; un máximo de 100 bultos por comando es un límite de lote de transporte, no un máximo comercial. Cada lote es atómico y la UI permite completar el resto sin perder contexto.
5. Lecturas devuelven capacidades calculadas en servidor (`PuedeAcusar`, razón de bloqueo y versiones pertinentes). Son ayudas de UI: el comando revalida todo.
6. Errores: 400 validación, 401 sesión, 403 ámbito/permiso, 404 recurso ajeno o inexistente bajo política uniforme, 409 versión/estado/custodia/comando incompatible, 503 dependencia indisponible. Usar ProblemDetails y códigos funcionales estables; no devolver mensajes SQL ni información de otro tenant.
7. `Cache-Control: no-store` para estas lecturas y respuestas privadas. Propagar CancellationToken, tiempos de espera y correlación; no cachear permisos ni datos entre organizaciones.

## 5. Secuencia de implementación para el agente

Ejecutar las fases en orden. En cada una registrar archivos, decisiones, evidencia y pendientes. Un exit code verde sin aserciones pertinentes no cierra una fase.

### Fase 0 — Preparar y congelar las fuentes

1. Leer `AGENTS.md`, `frontend/AGENTS.md`, `frontend/DESIGN.md`, `docs/continuidad/cloud-agent.md`, `codex-cloud.md` y `scripts/cloud/checkpoint.json`. Leer este plan y las fuentes del apartado 1.
2. Registrar rama/HEAD/status de los cuatro repositorios y los gitlinks registrados (`git ls-tree HEAD backend frontend mobile`). Identificar cambios del usuario y preservar los tres submódulos materializados. No hacer reset, stash, checkout de otra punta ni submodule update sobre este workspace sin una selección de fuente deliberada.
3. Preparar ramas de feature o un checkout aislado desde la combinación elegida; si se usan los HEAD actuales, fijarlos explícitamente. No usar checkpoint.json como selector ni actualizar submódulos para resolver builds.
4. Inventariar comandos de construcción, SDK/locks, Compose efectivo, fixtures PostgreSQL y harness navegador vigentes. No instalar herramientas globales ni cambiar la configuración publicada del entorno para esta feature.
5. Registrar la base en `docs/auditorias/ap-04/estado-inicial.md` con inventario de hallazgos. Revalidar rutas y métodos de este plan si el checkout avanzó.

**Salida:** inventario reproducible y fuentes elegidas, sin alteraciones de datos existentes.

### Fase 1 — Especificar comportamiento y reproducir las brechas

6. Crear `backend/docs/cu/AP-04-devoluciones-comercio.md` y una decisión breve de arquitectura/alcance con la propuesta del apartado 3. Trazar cada requisito literal, decisión de producto, estado, actor, comando y prueba; no escribir «la letra exige un acuse».
7. Construir una matriz de elegibilidad por EstadoEnvio × ResultadoBulto × Custodia × EsRetiro × permiso. Incluir entregas parciales, retorno total, cancelación, extravío, versión obsoleta e historial anterior al corte.
8. Reproducir en fixtures propias: devolución total → recepción depósito → Devuelto/Deposito; devolución parcial → EnDevolucion/Deposito → devolución al comercio. Verificar el comando y la UI existentes. Añadir una regresión que demuestre el hueco de transferencia total antes de corregirlo.
9. Definir el corte de nueva auditoría, la procedencia de hechos históricos y los mensajes de casos no acreditados. No reconstruir custodia a partir del estado agregado.
10. Revisar que el flujo incluya una acción Commerce real y una historia consultable. Si el equipo requiere solicitudes/aprobación o RMA, actualizar primero esta definición con sus reglas; no improvisarlas dentro de un controlador.

**Salida:** especificación revisable, contrato y matriz congelados; reproducción de los dos recorridos.

### Fase 2 — Modelar dominio y persistencia

11. Reutilizar Bulto/ResultadoBulto/EstadoCustodiaBulto/AgregacionBultos. Diseñar entidades de auditoría propuestas `TransferenciaDevolucion` + líneas por bulto y `AcuseDevolucionComercio` + líneas, con IDs estables. Estos registros describen hechos; no son una máquina de estados de envío alternativa.
12. Cada transferencia conserva operador, comercio, envío, actor/acceso, comando, fecha UTC de registro y bultos/versions antes y después. Cada acuse referencia una transferencia y líneas concretas, resultado, observaciones normalizadas, actor/acceso y fecha UTC. FK compuestas deben impedir mezclar operador/comercio/envío/bultos.
13. Definir identidad única de comando con ámbito y huella canónica de entrada normalizada: mismo actor/ámbito/contenido reproduce la respuesta original; distinta selección, actor o contenido con el mismo ID da 409. Guardar el resultado estable, no reconstruirlo desde el estado futuro.
14. Impedir doble acuse definitivo por línea transferida mediante restricción única. Un acuse no se edita ni se elimina; observaciones posteriores, si se necesitan, serán hechos nuevos especificados, no UPDATE de historia.
15. Crear una migración aditiva nueva y el snapshot/configuraciones EF pertinentes. No modificar/borrar migraciones históricas ni agregar filas ficticias para envíos previos. Índices por comercio/operador/fecha/ID, envío, transferencia y pendientes de acuse; comprobar el plan de consultas con datos selectivos.
16. Habilitar y forzar RLS en todas las tablas nuevas, incluidas líneas. Conceder solo lecturas/escrituras necesarias; prohibir UPDATE/DELETE/TRUNCATE de hechos incluso por vías SQL directas según el patrón del sistema. Revisar permisos de propietario/migrador sin dejar al runtime como dueño.
17. Si se usan funciones SECURITY DEFINER, limitar argumento/resultado/operación, dueño NOLOGIN sin superusuario/BYPASSRLS, search_path fijo, EXECUTE revocado a PUBLIC y revalidación completa del actor y recurso. No conceder acceso general a Envios/Bultos para evitar una función acotada.
18. Aplicar la cadena en PostgreSQL/PostGIS efímero desde vacío y desde la revisión inmediatamente anterior a AP-04, usando el migrador restringido y roles runtime reales. Validar grants, FORCE RLS e inmutabilidad. No probar upgrades apuntando al PostgreSQL compartido de desarrollo o Cloud SQL.

**Salida:** migración/grants verificables, modelo inmutable y consultas indexadas, sin pérdida de datos.

### Fase 3 — Autorización y límites de aplicación

19. Lectura Commerce: reutilizar `envios.consultar` y el ámbito Comercio. Para el acuse, agregar `devoluciones.gestionar` aplicable únicamente a Comercio en `CatalogoPermisos`; no habilitar `envios.gestionar` para Comercio.
20. Actualizar catálogo persistido, validadores, listados de permisos, políticas API/portal y tests. Definir una asignación inicial mínima: rol propietario/administrador protegido del comercio mediante el mecanismo idempotente existente; roles personalizados solo por concesión explícita. Verificar cuentas ya existentes y altas nuevas en local/GCP.
21. Los comandos operativos conservan `envios.gestionar` y actor Operador; la decisión de iniciar devolución conserva además su comprobación específica de decisiones operativas. Un administrador de plataforma no hereda por eso acceso al envío.
22. Resolver usuario/comercio desde `IUsuarioActual`, validar acceso activo, organización y permiso vigentes dentro de la transacción usando los contratos existentes. Revalidar también antes de devolver un replay. La comprobación de un menú o claims antiguos no basta.
23. Para un comercio con varios operadores, listar únicamente operadores presentes en sus datos autorizados o usar el catálogo permitido con respuestas que no revelen envíos ajenos. Cambiar operador cancela cargas anteriores y vacía la selección pendiente; evitar que una respuesta tardía contamine el contexto nuevo.

**Salida:** políticas y casos de uso con pruebas negativas reales, sin ampliar permisos de operador al comercio.

### Fase 4 — Implementar lectura consistente

24. Crear los puertos/DTOs/casos de uso tipados de M02 y su registro DI. Reutilizar transacción contextual/RLS de los módulos existentes. SQL y EF pertenecen a Infrastructure.
25. Consultar PostgreSQL canónico para estado, resultado, custodia, transferencias y acuses; no depender de Mongo/Kafka ni una proyección eventualmente consistente para decidir si el comercio puede actuar.
26. Incluir devoluciones totales, parciales y completadas por existencia de hechos/resultados apropiados; no filtrar únicamente `Envio.Estado IN (EnDevolucion,Devuelto)`. Conservar la visibilidad histórica si el agregado cambia después.
27. Proyectar solo datos necesarios: referencia del envío, operador, código de bulto propio, situación, motivo permitido, cantidades y fechas. No copiar fotos/firmas/documentos del destinatario, payloads privados, tokens de seguimiento ni datos de otros comercios.
28. Implementar filtros/paginación y conteos SQL sin N+1 ni materializar todo el comercio. Asegurar una lectura coherente del detalle y capacidades mediante una consulta o transacción apropiada; no unir resultados tomados en instantes incompatibles.
29. Probar consulta con miles de registros, iguales timestamps, múltiples páginas, cambios concurrentes y envíos antiguos con actividad reciente. Documentar índices/EXPLAIN sin atribuir capacidad productiva no medida.

**Salida:** consultas seguras, acotadas y correctas para parciales y grandes colecciones.

### Fase 5 — Completar transferencia física y acuse

30. Refactorizar el escritor existente de devolución al comercio hacia el puerto común sin duplicación. Actualizar `RecepcionController`, `GestionarRutasUseCase.Recepcion.cs`, `IRutasRepository`, `RutasApiClient` y los handlers/formularios de Backoffice afectados para el contrato nuevo.
31. Releer con bloqueo las filas del envío y bultos seleccionados, respetando el orden de bloqueos existente por operador y un orden determinista por ID. Validar actor, versiones, pertenencia y procedencia de devolución dentro de la misma transacción.
32. Permitir transferencia tanto de bultos EnDevolucion/Deposito como de Devuelto/Deposito con procedencia de devolución acreditada. Mantener el significado histórico de Devuelto; no hacer un UPDATE masivo que lo convierta en otro estado para arreglar la UI.
33. Seleccionar explícitamente los bultos físicamente presentes. Rechazar bultos entregados al destinatario, de retiro, ajenos, con custodia Repartidor/PendienteDeposito o de otra transferencia. Validar la política de excepciones de la matriz; no inferir presencia de GPS, cierre, rendición ni estado agregado.
34. Guardar custodia Comercio, resultados/agregado cuando corresponda, versiones, transferencia y contexto de historia/eventos en una sola transacción. Para un bulto ya Devuelto, no inventar una transición Devuelto→Devuelto: registrar el hecho real de transferencia/custodia y conservar la semántica de versiones acordada.
35. Implementar el acuse del comercio sobre líneas transferidas, con selección explícita, permiso vigente y observaciones obligatorias cuando declara diferencias. No tocar las filas operativas del envío/bulto. Registrar el resultado de comando y el acuse atómicamente.
36. Demostrar carreras operador/operador, comercio/comercio y transferencia/acuse con conexiones PostgreSQL independientes: una confirmación válida, replay estable o conflicto controlado; sin líneas parciales ni duplicados. La autorización se comprueba también si el comando ya existe.
37. Simular respuesta perdida después del commit, reinicio de API y reintento en otra instancia. Reutilizar el mismo ComandoId y contenido hasta resultado conocido. Con 409, recargar y requerir nueva intención explícita; no reescribir silenciosamente versiones del comando fallido.
38. Reutilizar historia canónica y outbox para efectos que ya genera una transferencia. Verificar rollback completo si fallan auditoría/outbox. Evitar publicar dos veces desde trigger y código. El acuse no es entrega al destinatario ni inicia otro correo/webhook de éxito; un evento nuevo solo se agrega si se especifica su consumidor y semántica.
39. Mantener importes, tarifas capturadas, reservas/ocupación, intentos, prueba de entrega, fechas físicas previas y retención de historia. No convertir observaciones del comercio en un reembolso o un extravío automático.

**Salida:** ambos recorridos de transferencia funcionan y Commerce tiene una acción de gestión idempotente y auditable.

### Fase 6 — API, ApiClient y UI

40. Implementar rutas/DTOs y ProblemDetails declarando respuestas propias de API. Actualizar OpenAPI exportándolo desde la API ejecutable y el snapshot `frontend/contracts/nexoruta.openapi.json`; no editar el snapshot para ocultar una diferencia del servidor.
41. Crear el ApiClient tipado y registrarlo en Commerce. Propagar token por petición con el patrón existente, nunca mediante estado global compartido. Mapear 401/403/404/409/503 a estados de sesión, permisos o error recuperable coherentes.
42. Agregar `/devoluciones` y detalle bajo `Components/Features/Devoluciones`, con la política de lectura. Agregar el destino a `CommerceNavigationCatalog.cs`, consumido por Razor/Blazor, y acceso contextual desde Mis envíos sin duplicar el menú ni modificar su agrupación de estados ajena a AP-04.
43. Bandeja: operador, fechas, situación y referencia; resultados paginados con resumen de bultos. Detalle: estado agregado real, progreso de devolución, filas de bultos con resultado/custodia, transferencia y acuse. No llamar «recibido por comercio» a un Devuelto/Deposito.
44. Acción principal por contexto: abrir detalle o registrar recepción. Mostrar claramente el conjunto de bultos y la consecuencia del acuse; conforme/con observaciones con ayuda y errores junto a los campos. Un usuario de consulta conserva la información y no recibe controles de escritura.
45. Reutilizar `shared/portal-design.css`, Bootstrap y componentes/patrones existentes. Skeleton solo durante lectura, `aria-busy`, mensaje de estado accesible y movimiento reducido. Conservar datos al refrescar; un guardado mantiene formulario/selección y muestra progreso sin sustituirlos por skeleton.
46. Implementar carga, vacío, error recuperable, permisos, sesión vencida, organización suspendida, datos históricos sin evidencia, conflicto y éxito persistido. Preservar ComandoId/entrada en error de transporte, bloquear doble envío y cancelar solicitudes al navegar/cambiar filtros/operador.
47. Soportar 320 CSS px, texto 200 %, teclado, foco visible y devolución de foco tras confirmación, nombres accesibles y contraste. Paginación de bultos/selecciones explícitas; no depender del color ni de hover. No perder selección silenciosamente al cambiar de página.
48. Revisar la acción operativa de Backoffice para lotes totales/parciales con los mismos estados, permisos, versiones y errores. Conservar antiforgery y el patrón de envío único existente.

**Salida:** recorrido operativo y autogestión completos usando el stack actual.

### Fase 7 — Observabilidad y regresiones transversales

49. Usar logs estructurados/TraceId/CorrelationId y métricas existentes de API. Registrar operación, resultado y duración; evitar documentos personales, observaciones libres, tokens y credenciales en logs. No usar IDs de envío/usuario como etiquetas métricas de alta cardinalidad.
50. Si se añaden métricas de negocio, limitar etiquetas a tipo/resultado e integrarlas en la fuente de dashboards existente; no crear otro stack. Mostrar fallos y conflictos en los paneles existentes o consultas documentadas.
51. Verificar que Kafka, historial Mongo, tablero, seguimiento público, notificaciones y webhooks conservan significado e idempotencia al cambiar custodia/versión. Actualizar aserciones por evento semántico, no relajando conteos globales. Un fallo de broker no debe bloquear una consulta/acuse canónicos de PostgreSQL ni perder un outbox persistido.
52. Verificar que los reportes/cuenta mantienen los cargos de devolución retenidos según la política actual. El acuse no recalcula precios ni liquida automáticamente.

### Fase 8 — Pruebas y CI obligatorios

Crear pruebas que detecten las brechas y riesgos reales. Aprovechar `PostgresFixture`, `IntegrationApiFactory`, conexiones restringidas y el patrón Kestrel/portales de `GestionBrowserTests`; no usar una base del usuario. Nombres propuestos: `DevolucionesHttpTests`, `DevolucionesConcurrencyTests`, `DevolucionesBrowserTests`, `backend/tests/browser/returns.cjs`. Para verificar la aplicación renderizada, navegación, estados de interacción y capturas se autoriza además el uso de la skill `browser-act` solicitado por el usuario. Puede complementar la automatización reproducible existente; no reemplaza sus aserciones de PostgreSQL, RLS, HTTP ni concurrencia. La autorización es para verificar esta aplicación en local y no para iniciar sesiones, cambiar infraestructura ni operar GCP.

| Grupo | Aserciones mínimas |
| --- | --- |
| Dominio | Elegibilidad total/parcial, custodia, acuse conforme/con observaciones, terminalidad/inmutabilidad, selección mixta atómica. |
| Autorización/RLS | Dos operadores, dos comercios, comercio con ambos operadores, mismo código en tenants distintos; acceso revocado, rol revocado, solo lectura, operador contra acuse, comercio contra inicio/transferencia, ID ajeno en lista/detalle/comando/cursor/replay. SQL directo bajo runtime también rechazado. |
| Estado/custodia | Total EnDevolucion→Devuelto/Deposito→Comercio; parcial entregado+devuelto; rendición sin recepción; cierre con incidencias; cancelación/extravío; retiro separado; bulto ajeno/ya entregado; agregado y bultos no elegidos intactos. |
| Concurrencia/idempotencia | Dos APIs/actores con conexiones independientes; una transferencia/acuse por línea; mismo comando idéntico tras reinicio y cambio posterior; mismo ID con distinto actor/payload; autorización revocada antes de replay. |
| Atomicidad | Excepción antes de commit y fallo de auditoría/outbox no dejan custodia/líneas/versiones parciales; respuesta cortada después del commit se recupera sin duplicación. |
| Lecturas | Filtros SQL, [desde,hasta), fechas iguales, cursor inválido/otro filtro, cambio de operador, actividad reciente de envío viejo, histórico sin evidencia; 1/100/101 elementos y 501/1500 bultos sin truncamiento. |
| Integraciones | Historia/outbox/Kafka/webhook correctos por evento, sin notificación falsa por acuse; cuenta/reportes/precios/custodia de otros flujos intactos. |
| Migraciones | Base nueva y upgrade real a AP-04, migrador sin superusuario/BYPASSRLS, roles/grants/FORCE RLS, FK compuestas e índices; datos previos preservados y sin acuses ficticios. |
| ApiClient/OpenAPI | DTOs, nulos, enums, parámetros, límites, errores tipados, contrato real y cancelación; API no expone entidades internas. |
| Navegador real | Commerce→API→PostgreSQL y Backoffice→misma API; dos sesiones aisladas, filtro, detalle parcial, transferencia, acuse, reapertura, 409, doble click, pérdida de respuesta, permiso revocado y error/red lenta reales. |
| Visual/a11y | 1440 y 320 px, texto 200 %, teclado/foco, carga/vacío/error/solo lectura, capturas inspeccionadas y axe complementario. Captura o HTTP no sustituyen revisión visual. |

53. Implementar unitarias enfocadas en Domain/Application y HTTP/SQL con PostgreSQL real. Añadir pruebas de arquitectura de fronteras. Ejecutarlas antes de navegador para localizar fallos funcionales.
54. Crear fixture sintética con comercio C1 en operadores A y B, C2 en A, devolución total, parcial con entregado al destinatario, transferencia pendiente, acuse conforme/con observaciones y registros previos al corte. Usar cuentas `example.test` y datos nuevos.
55. Automatizar navegador con API Kestrel y ambos portales reales, puertos y key rings propios. Bloquear llamadas Mapbox/Geoapify y correo a terceros; no sembrar estados con UPDATE directo para el circuito principal: crear los hechos mediante comandos reales.
56. Agregar `NEXORUTA_RETURNS_E2E_DIR` como gate explícito propuesto del harness y habilitarlo en `.github/workflows/ci.yml` raíz y CI Backend, con sus companions Frontend exactos. Descargar/restaurar dependencias con locks. CI debe publicar TRX, JSON y capturas, y demostrar que el test no fue omitido.
57. Actualizar el inventario/sharding de integración existente si corresponde para que cada prueba nueva se ejecute, no solo se compile. Mantener los gates actuales de cobertura y los contratos de roles/migraciones.
58. Ejecutar primero suites afectadas; después el CI obligatorio de los repositorios/PRs y del conjunto raíz. No repetir suites verdes por rutina sin cambios. Documentar fallos/omitidas y no convertir una ejecución parcial en aceptación completa.

Comandos de referencia desde la raíz, una vez creados los tests y con Docker/SDK/locks preparados (el filtro nombra clases propuestas, no pruebas existentes):

```bash
dotnet restore backend/NexoRuta.sln --locked-mode
dotnet build backend/NexoRuta.sln -c Release --no-restore
dotnet restore frontend/NexoRuta.sln --locked-mode
dotnet build frontend/NexoRuta.sln -c Release --no-restore
dotnet test backend/tests/NexoRuta.UnitTests -c Release --no-build --no-restore --filter 'FullyQualifiedName~Devolucion'
dotnet test backend/tests/NexoRuta.ArchitectureTests -c Release --no-build --no-restore
dotnet test backend/tests/NexoRuta.IntegrationTests -c Release --no-build --no-restore --filter 'FullyQualifiedName~DevolucionesHttpTests|FullyQualifiedName~DevolucionesConcurrencyTests'
# Configurar el módulo Playwright y Chromium con las versiones fijadas del harness existente.
export NEXORUTA_RETURNS_E2E_DIR="$PWD/.local/ap04-evidence/browser"
dotnet test backend/tests/NexoRuta.IntegrationTests -c Release --no-build --no-restore --filter 'FullyQualifiedName~DevolucionesBrowserTests'
dotnet test frontend/tests/NexoRuta.ApiClient.Tests -c Release --no-build --no-restore --filter 'FullyQualifiedName~Devolucion|FullyQualifiedName~OpenApiContractTests'
```

Registrar cantidad descubierta/ejecutada; un filtro sin tests es fallo del procedimiento. Mantener HTTP y navegador en invocaciones separadas. Usar los scripts/companion configurados del checkout y no suponer que `bin` antiguo es la implementación probada.

## 6. Aceptación local con Docker y WSL

59. En WSL comprobar `docker version`, `docker info`, `docker compose version`, SDK y acceso al daemon de Docker Desktop/Engine elegido. Registrar contexto del daemon y Compose project; no usar simultáneamente dos runtimes sobre los mismos puertos/bases.
60. Preferir checkout en el filesystem Linux para rendimiento/casing. Si se usa `/mnt/c`, comprobar volúmenes/permisos/casing y mantener bin/obj separados de procesos Windows. No recompilar DLLs cargadas por portales ni depender de procesos de otra tarea.
61. Usar datos sintéticos en un proyecto/volúmenes propios para aceptación automática. Las fixtures HTTP/browser crean su PostgreSQL/PostGIS con roles restringidos. Para inspección persistente del entorno habitual, identificar expresamente el destino antes de migrar y conservar su respaldo/procedimiento; no usar `down -v`, reset de offsets ni borrados como preparación.
62. Revisar `compose.yaml` + `compose.override.yaml` efectivos y las variables ignoradas locales, sin imprimir secretos. Aplicar el orden actual: `rls-migrator` → `rls-role-provisioner` → API/workers/portales. API mantiene migraciones/seeds automáticos deshabilitados. No editar `__EFMigrationsHistory` para simular un upgrade.
63. En un entorno propio autorizado y preparado, el arranque normal es:

```bash
docker compose config --quiet
docker compose build
docker compose up -d
docker compose ps
```

El migrador manual documentado usa `docker compose --profile rls-admin run --rm --build rls-migrator`, solo tras confirmar el destino local. Usar el Compose efectivo y sus servicios reales; no fijar contraseñas del README histórico. `compose.dev.yaml` es opcional para desarrollo, no una condición de funcionamiento.

64. Verificar API `localhost:5000`, Backoffice `localhost:5101`, Commerce `localhost:5102`; dentro de Compose el ApiClient usa el host/puerto interno configurado (`api:8080`), no localhost del contenedor. No agregar URLs de Windows, rutas absolutas ni `host.docker.internal` como requisito de AP-04.
65. Repetir el circuito sintético completo: decisión/retorno/recepción/transferencia en Backoffice → bandeja y acuse en Commerce → reapertura. Verificar roles reales y persistencia después de reiniciar API/Commerce conservando volúmenes. Probar broker detenido en un entorno propio: consultas/acuses canónicos no deben depender de su disponibilidad.
66. Registrar build, HTTP/SQL, automatización y revisión visual por separado en `docs/auditorias/ap-04/validacion.md`; adjuntar archivos sintéticos a `.local/ap04-evidence`, excluyendo claves, sesiones y observaciones privadas.

Alternativa para un agente Linux Cloud con Docker: usar `scripts/cloud/environment-install.sh`, cargar `scripts/cloud/env-agent.sh` y seguir `dev.py` según continuidad vigente, con fuentes exactas. El runtime mínimo no levanta todos los brokers: las pruebas de efectos asíncronos usan fixtures propias o el stack documentado completo. Este camino no depende de `.env`/DPAPI/servicios del Windows del usuario y tampoco demuestra operación GCP por sí solo.

## 7. Entrega y aceptación remota en GCP

67. Construir AP-04 con la misma configuración y contratos que en local. No crear un modo «devoluciones GCP», endpoints Development para operar devoluciones, almacenamiento local de acuses, SQLite por VM ni locks en memoria. PostgreSQL/Cloud SQL es la autoridad compartida de concurrencia/idempotencia.
68. Revisar `deploy/gcp/compose.yaml`, `scripts/gcp/delivery.py`, `vm_deploy.py`, `deploy/gcp/sql/postflight.sql`, provisioning de roles y el comando `database-migrate`. Incluir la migración/grants nuevos en las imágenes/artefactos existentes. No se prevé nuevo recurso IaC, broker o secreto; justificar y documentar cualquier cambio que aparezca durante implementación.
69. Validar la cadena de migraciones/grants con una base efímera representativa de Cloud SQL y migrador sin privilegios globales. API/worker no reciben CREATE ROLE, superusuario ni BYPASSRLS. Verificar que el provisionador reaplica permisos de forma idempotente sin borrar accesos existentes.
70. Publicar primero los commits de Backend y Frontend en sus ramas de feature; después fijar esos SHA exactos en el principal y abrir las PRs según flujo vigente. Mantener Mobile en su SHA elegido salvo cambio justificado. No usar tags `latest` mezclados; la evidencia debe identificar combinación exacta y digests.
71. Pasar CI de componentes y CI integrado obligatorio del principal, incluido navegador AP-04 no omitido y migraciones/roles. Actualizar documentación del contrato, permisos, operación y demostración antes de solicitar promoción/despliegue.
72. **Gate de operación remota:** preparar un diff/release y plan de datos revisables. El pedido actual autoriza elaborar este plan; ejecutar `start`, `update`, migraciones de la base compartida, bootstrap/apply o publicación operativa requiere autorización para ese destino. No tomar el acceso a GCP como aprobación implícita.
73. Con despliegue autorizado, usar los workflows vigentes y una release completa. `main` consume la última release publicada; `develop` construye/despliega su combinación y comparte VMs/Cloud SQL. Por eso no probar migraciones sobre develop suponiendo una base descartable. Inspeccionar workflow y manifiesto del canal elegido antes de dispararlo.

```bash
# Solo en la fase autorizada, con el canal y release previamente comprobados.
gh workflow run vm-controls.yml --repo NexoRuta/NexoRuta --ref main -f operation=update
gh run list --repo NexoRuta/NexoRuta --workflow vm-controls.yml
gh run watch ID_EJECUCION --repo NexoRuta/NexoRuta
```

Si las VMs están apagadas, `update` no las enciende; `start` inicia una sesión y costos por su ventana vigente. No dispararlo por rutina. Ver `infra/gcp/guia-uso-actions.md`, `infra/gcp/README.md` e `infra/gcp/integration-tags.md`.

74. El procedimiento actual retira ambos nodos del balanceador, detiene escritores, migra una vez y arranca la release objetivo. Conservar ese corte coordinado al cambiar el contrato de transferencia; no exigir compatibilidad entre binarios viejos/nuevos. Si el workflow real avanzó, reconciliar su procedimiento sin saltar protecciones.
75. Confirmar en A y B: misma release/digest, migración aplicada una vez, roles runtime acotados, variables API internas, Data Protection compartida y permisos/keys correctos para sesiones Commerce. Conservar HTTPS, forwarded headers, antiforgery, WebSocket de Blazor y configuración del balanceador actuales.
76. Hacer smoke HTTPS con cuentas sintéticas dedicadas y operadores/comercios propios: listado, parcial, transferencia, acuse, historial, refresh y rechazos cruzados. No reutilizar envíos del usuario ni leer secretos en los artefactos. Tomar hosts del resumen efectivo de sesión, sin copiar IPs históricas de documentos.
77. Probar concurrencia y replay entre API A y B identificadas por separado mediante el mecanismo operativo aprobado, conservando TLS/autenticación. Confirmar por telemetría el nodo que procesó cada llamada; el balanceador alternando por azar no demuestra multiinstancia. No publicar puertos privados ni añadir un header de bypass a producción.
78. Reiniciar una instancia y repetir el mismo comando en la superviviente: mismo resultado persistido, sin acuse/transferencia/evento duplicados. Ejecutar únicamente sobre datos/servicios autorizados; no usar esa prueba para apagar infraestructura ajena.
79. Verificar métricas, errores, correlación y comportamiento de colas/proyecciones existentes. Comparar datos de cuenta/reportes antes/después. Registrar tiempos y contexto reales sin afirmar SLO/capacidad productiva a partir de un smoke.
80. Fallo de migración: mantener escritores detenidos según el runbook y diagnosticar. Fallo posterior: aislar nodo fallido y corregir hacia delante con nueva release compatible con el esquema presente. No hacer Down destructivo, restaurar contenedores viejos contra esquema nuevo por intuición ni borrar datos/volúmenes para recuperar. La demo no dispone de recuperación automática por backups; preparar previamente cualquier protección adicional necesaria y no inventar que existe.

## 8. Criterios de cierre y entregables

AP-04 podrá pasar a Done cuando se demuestre todo lo siguiente, en una combinación de fuentes identificada:

- [x] Fuente literal, interpretación de gestión y reglas de actor/estado documentadas y aceptadas para AP-04.
- [ ] Bandeja/detalle Commerce propios por operador, con devoluciones totales, parciales, históricas y completadas; filtros y paginación en servidor.
- [x] Acción de gestión Commerce persistente: acuse conforme/con observaciones, permisos vigentes, auditoría inmutable y reapertura.
- [x] Transferencia operativa correcta tanto para EnDevolucion/Deposito como para Devuelto/Deposito, sin confundir custodia con el agregado ni tocar bultos entregados.
- [x] Comandos atómicos/idempotentes y conflictos probados con dos APIs/actores y PostgreSQL real; replay vuelve a autorizar.
- [x] RLS/grants/migración cumplen aislamiento y se aplican a cuentas existentes/nuevas; ninguna lectura/escritura ajena por API o SQL runtime.
- [x] Historia, outbox y consumidores conservan significado; no hay reembolsos, cambios de tarifa, liberaciones o datos físicos inventados.
- [x] OpenAPI, ApiClient, Commerce y Backoffice actualizados juntos, sin aliases de compatibilidad innecesarios; rutas y campos clave verificados por el test de contrato versionado.
- [x] Tests pertinentes y CI integrado verdes, cantidades/omitidas comprobadas; test browser nuevo realmente ejecutado.
- [x] Revisión visual/teclado a 1440/320 px y texto 200 %, con estados lentos/errores activados y evidencia separada. `browser-act` está autorizado para revisar la app desde navegador local o GCP cuando se requieran comprobaciones; usar Chrome aislado, no el perfil personal, guardar capturas dentro de la auditoría AP-04 y cerrar la sesión al terminar. Complementar con el harness de navegador fijado del repositorio.
- [x] Circuito local Docker/WSL reproducible, reinicio sin pérdida de acuses y sin dependencia de archivos privados de otra máquina.
- [x] Estado operativo GCP registrado: release/health en ambos nodos y HTTPS/permisos smoke pasaron; digests y replay dirigido A/B pendientes explícitos, por lo que permanece Do tests y no Done.
- [x] Documentación y evidencias publicables sin secretos/datos privados; SHAs de componentes y gitlinks de raíz coherentes.

Entregables de implementación: especificación AP-04 y decisión de alcance; cambios Domain/Application/Infrastructure/API; migración y permisos; OpenAPI/ApiClient; UI Commerce y adaptación puntual Backoffice; tests y configuración CI; guía local/GCP y demostración con fixtures; informe de validación por categoría y manifest de fuentes. Actualizar la card con enlaces a PRs/artefactos, brechas reales y estado correspondiente. No cerrar CU-06, AP-01, AP-09 ni validación nativa por haber completado este circuito web.

## 9. Instrucción de ejecución resumida para el próximo agente

«Implementá AP-04 siguiendo este plan y las instrucciones del checkout. Primero revalidá las fuentes y la matriz funcional; después resolvé la transferencia total/parcial, permisos/RLS, lectura, acuse y UI. Reutilizá el dominio y los contratos de aplicación; mantené separado el hecho físico del acuse comercial. Trabajá con datos sintéticos y validá PostgreSQL restringido, ambos portales y el replay multiinstancia. Conservá la selección de código, datos, secretos y protecciones existentes. Entregá cambios revisables, pruebas/evidencia y un procedimiento local/GCP; no ejecutes operaciones remotas sin autorización del destino. Si falta una capacidad de ejecución, identificá exactamente qué criterio queda sin probar y mantené la card abierta».

## 10. Comprobaciones y estado de ejecución (11/11/2026)

La card se consultó mediante MCP el 10/11 y figuraba en **In progress**. Mantenerla abierta: faltan aceptación visual/interactiva autenticada, replay explícito entre A/B, Compose local con reinicio y persistencia, CI integrado y pruebas responsive. El usuario autorizó el despliegue AP-04 sobre GCP develop; se ejecutó primero `42957078788` y, tras crear un Chrome aislado de BrowserAct, se repitió `start` en `42962778569` para realizar la comprobación en navegador. Después del `stop` `42964630303`, el usuario autorizó usar una cuenta del seed general y se ejecutó un nuevo `start` (`42967468460`) para continuar.

- **Fuentes y release GCP:** `42962778569` terminó `success` con root `58e8b170b8fdbc8516edda81bd4a1610c7779ce5`, backend `013e11eeeaf177a00e9fbf1ff96c054bd7226084`, frontend `49d44f347a75c473aa39fffda272b4e3a944b269` y mobile `53f6be2cdec48f48e30e390060feeaefb5be0ead`. Publicó `release-5de601c6e4e24723bc6ce4550770da54`; el mismo release se aplicó en A y B. Los digests completos de imágenes están en `docs/auditorias/ap-04/validacion.md`; no registrar hosts/IP ni secretos.
- **Migración y operación:** servicios compartidos quedaron saludables antes de migrar; drenaje del balanceador, preflight, migración de esquema, provisión runtime/hosting y bootstrap pasaron. A y B pasaron arranque y health directo; el balanceador reportó Commerce saludable. Los roles API/bootstrap/worker no tienen superusuario ni `BYPASSRLS`. El workflow completó HTTPS público y login smoke. BrowserAct llegó a `/devoluciones`, que redirigió a `/ingresar` sin sesión.
- **BrowserAct remoto:** el usuario autorizó crear `ap04-gcp-verification`, Chrome local aislado y vacío. BrowserAct 1.6.2 lo abrió sin reiniciar el Chrome preexistente y navegó al Commerce GCP. El intento único con la cuenta sintética publicada en `docs/demo/README.md` fue rechazado por el portal; no se probaron más contraseñas ni se crearon usuarios/envíos. Se guardó y revisó `docs/auditorias/ap-04/evidencia/commerce-devoluciones-gcp-login-rejected.png` (1904 × 985), que solo muestra el formulario de acceso y el error genérico. No están validados filtros, bandeja, detalle, acuse ni interacción Blazor autenticada.
- **Cierre de la ventana GCP:** el workflow `42964630303` ejecutó `stop` con resultado `success`; Compute Engine confirmó ambas VMs `TERMINATED` y Cloud SQL `RUNNABLE`. No se ejecutó `/api/admin/demo-data` ni se crearon registros de prueba en Cloud SQL.
- **Nuevo despliegue GCP:** workflow `42967468460` terminó `success` sobre root `81694be93d312935e784075d82a568fa57733a5b5` y publicó `release-4d7a613a7f1c47ad9525e6bf6975e418` (seis imágenes construidas). El mismo release quedó aplicado en A y B; pasaron health directo, health del balanceador, HTTPS público y `public_https_and_login_smoke`. El nodo A reportó `healthy`. No registrar host/IP ni secretos. Tras cerrar la revisión parcial, workflow `42969621808` (`stop`) terminó `success`; el log informa ambas VMs detenidas o ausentes y Cloud SQL todavía ejecutándose.
- **BrowserAct y seed general:** tras el nuevo `start`, BrowserAct 1.6.2 abrió `/devoluciones`, siguió la redirección a `/ingresar` y renderizó el formulario normal; la captura revisada `docs/auditorias/ap-04/evidencia/commerce-devoluciones-gcp-login-required.png` (1904 × 985) no contiene la bandeja AP-04. El usuario autorizó el seed general, pero aún no se llamó `POST /api/admin/demo-data`: la política exige una sesión de plataforma y la credencial de plataforma de GCP no está en la documentación. No leer el secreto de despliegue ni inventar credenciales. Se requiere acceso temporal autorizado o que el responsable ejecute el endpoint con la cuenta de plataforma; después se podrá ingresar como C1. No generar transferencias ni acuses que pretendan acreditar un hecho físico.
- **Validación local/automatizada:** se mantiene la evidencia previa de compilación selectiva, OpenAPI, PostgreSQL/PostGIS sintético, C31 (3/3 variantes) y contrato frontend (1/1) descrita en `docs/auditorias/ap-04/validacion.md`. Windows no tenía Docker CLI y el socket Docker de WSL no era accesible; no se borraron volúmenes ni se usaron `.env` o servicios del usuario. Esto no acredita Compose, persistencia tras reinicio, CI integrado ni pruebas concurrentes entre dos APIs.
- **Evidencia visual y card:** la captura local anterior es de 1366 px; GCP muestra el login con el estado requerido y no se logró todavía una sesión autenticada para AP-04. No se verificaron autenticación Commerce, viewports 1440/320 px, texto al 200 %, teclado completo, estados lentos/error ni transacción de acuse. La última consulta de Notion registró `In progress`; no mover a `Do tests` o `Done` hasta que se completen/acepten los criterios aplicables. El informe `docs/auditorias/ap-04/validacion.md` contiene la evidencia por categoría y los límites.

La evidencia detallada por categoría, comandos y límites está en `docs/auditorias/ap-04/validacion.md`. Los criterios de cierre del apartado 8 permanecen pendientes salvo donde se documente explícitamente una comprobación parcial; la card no se mueve a Do tests ni a Done en esta ejecución.

## 11. Actualización de despliegue, seed y BrowserAct (11/11/2026)

Esta sección complementa y, para los resultados que contradiga, reemplaza la instantánea de ejecución del apartado 10 y del informe de validación. El usuario pidió desplegar la feature AP-04, comprobar únicamente que el workflow pasara, leer la configuración runtime necesaria para identificar la cuenta de plataforma y ejecutar el seed general. Se mantuvo el alcance en AP-04 y no se imprimieron ni guardaron secretos.

- **Despliegue:** `vm-controls.yml` operation `update`, run `43062369357`, terminó `success` sobre `develop`, root `6d258a77d990bb3e6bc3aac53876ceb3a5f68d86`, backend `39cebff2cf5e0c49ce1d16bbdd99e0478b4e5be4`, frontend `49d44f347a75c473aa39fffda272b4e3a944b269` y mobile `53f6be2cdec48f48e30e390060feeaefb5be0ead`. No se hizo una comprobación HTTP directa independiente en esta pasada.
- **Seed general:** run `43064530696` terminó `success`. La operación devolvió `synchronized-existing`, con `seededBefore=true`: 5 operadores, 5 comercios, 70 envíos, 35 rutas y 252 operaciones. Se sincronizó la contraseña sintética existente del operador Commerce C1 con el valor del secreto runtime, sin mostrarlo ni escribirlo en archivos. No se agregaron duplicados ni se fabricaron transferencias o acuses AP-04.
- **Correcciones necesarias para poder sincronizar:** el actor de plataforma necesitó una política RLS acotada para leer la fila del usuario objetivo y seleccionar su organización antes de consultar roles. Además, el endpoint debe confirmar éxito idempotente con HTTP 200: el HTTP 409 previo se interpretaba como error por el middleware transaccional y revertía la sincronización. Los cambios quedaron incluidos en los SHAs desplegados indicados arriba.
- **BrowserAct en GCP:** después del seed, C1 pudo iniciar sesión y cargar `/devoluciones` con el Chrome local aislado. La pantalla mostró filtros por rango de fechas, operador, situación y referencia, actualización, aplicación de filtros y estado vacío. Se revisó el rango predeterminado y uno de 89 días (14/08/2026–11/11/2026); ambos siguieron vacíos. Capturas revisadas: `docs/auditorias/ap-04/evidencia/commerce-devoluciones-gcp-authenticated-empty.png` y `docs/auditorias/ap-04/evidencia/commerce-devoluciones-gcp-empty-89-days.png` (1904 × 985). La sesión BrowserAct se cerró.
- **Límite funcional:** el seed general no produjo devoluciones AP-04 ni hechos de entrega/traslado/acuses para mostrar. No se pudo validar el detalle por bulto, registrar/leer un acuse, ni verificar refresh/reapertura sobre una operación real. Tampoco se ejecutaron Compose con reinicio, replay multiinstancia, CI integrado ni revisión responsive/teclado/zoom. La card continúa `In progress`; no promoverla hasta completar los criterios aplicables y revisar la aceptación.

## 12. Corrección de recepción inicial en la bandeja AP-04 (11/11/2026)

Esta actualización registra una regresión encontrada al inspeccionar la lista y el detalle autenticados en GCP. No cambia la decisión funcional: una recepción normal en depósito no es una devolución ni debe aparecer como un retorno histórico.

- BrowserAct inició sesión en Commerce C2 después de preparar el escenario sintético. La bandeja incluyó un envío recién admitido y recibido en depósito como `Histórica`, con cero bultos en retorno, depósito o pendientes de acuse. El detalle mostró `EnDeposito`, dos bultos fuera del circuito y un único hecho `RecepcionDeposito`. Evidencia anterior al arreglo: `docs/auditorias/ap-04/evidencia/commerce-devoluciones-gcp-false-history-before-fix.png`.
- Causa: la consulta AP-04 incluía cualquier evento `RecepcionDeposito`; ese tipo también registra la recepción inicial normal. Se ajustó la selección de actividad, detalle e historial para aceptar ese evento solo cuando el estado nuevo sea `Devuelto` o `EnDevolucion`. Se mantienen los eventos explícitos de decisión de devolución y transferencia al comercio.
- Se añadió una aserción de regresión a `C31_EntregaParcialRespetaPoliticaCustodiaPruebaReintentosYConflictoPorBulto`: después de la recepción inicial y antes de una devolución, el envío no debe aparecer en la bandeja Commerce. La aserción posterior a la transferencia AP-04 queda vigente.
- Compilación de `NexoRuta.IntegrationTests` en Windows: aprobada, cero errores y tres warnings existentes (NU1510, xUnit2031 y EF1003). La prueba no se ejecutó: WSL no tiene `dotnet` y el intento nativo se detuvo por esa dependencia. La build no valida la consulta contra PostgreSQL.
- El ensayo GCP dejó dos bultos sintéticos recibidos en depósito, sin ruta, devolución, transferencia ni acuse. Planificar la ruta respondió HTTP 409 indicando que al envío le falta una revisión de cobertura verificable, aunque el historial de tarifa muestra revisión 2. No se fabricó custodia, no se usó SQL directo y no se continuó el flujo físico. La regla de prueba de entrega parcial se publicó temporalmente y luego se restauró en una nueva publicación con los valores originales; no queda un borrador abierto.
- Desplegar el commit de backend y comprobar con BrowserAct que el envío normal ya no contamine la bandeja. No usar ese envío como prueba de devolución real: el detalle/acuse con una devolución válida sigue sin verificarse. Mantener pendientes Compose local con reinicio, CI integrado, replay entre A/B y revisión responsive/teclado/zoom.

## 13. Deploy y seed general posteriores (11/11/2026)

- La raíz `8e5ded9007c25029e5287bdde5c284b03ef1eec0` quedó desplegada en `develop` con `vm-controls.yml` operation `update`, run `43076158807` (`success`). El job `deploy` completó en 8m15s e incluyó el backend AP-04 `bac0b0b41c21993a515bacc420915d66a2fd3095`.
- Se ejecutó el seed general con `vm-controls.yml` operation `seed-demo`, run `43078138229` (`success`, 33s). El helper usó la credencial de plataforma obtenida desde Secret Manager en la VM; el secreto no se imprimió ni se guardó.
- A pedido del usuario, esta pasada terminó al confirmar los workflows: no se hizo BrowserAct ni otra comprobación posterior de la app. Por eso sigue pendiente verificar que la recepción inicial ya no aparezca en AP-04 y completar el ciclo con una devolución válida. No promover la card; permanece `In progress`.

## 14. Redeploy y verificación BrowserAct en GCP (11/11/2026)

Esta actualización complementa la sección 13. Se verificó el cambio de exclusión de recepciones iniciales y el manejo UI del 404 para un envío que no pertenece al circuito AP-04.

- **Fuente publicada:** raíz `593095831d4b09e736df61b13f1f331e60d92225`, Backend `bac0b0b41c21993a515bacc420915d66a2fd3095`, Frontend `8974044e59f4b52940c5e16841174d0ca83f3460` y Mobile `53f6be2cdec48f48e30e390060feeaefb5be0ead`.
- **Workflow GCP:** `vm-controls.yml`, operation `update`, run `43082801986`, `success`; `publish_develop` pasó y `deploy` terminó en 8m08s. `seed_demo` y `repair_ssh` quedaron omitidos. El run confirma el despliegue de esos gitlinks en `develop`.
- **Compilación:** la build Frontend posterior a la corrección de 404 terminó con 0 errores y 1 warning existente NU1510. La build de `NexoRuta.IntegrationTests` del cambio Backend terminó con 0 errores y 3 warnings existentes (NU1510, xUnit2031, EF1003). No se ejecutó C31 contra PostgreSQL en este paso.
- **BrowserAct, consulta AP-04:** Commerce C2 inició sesión en el Chrome aislado. `/devoluciones` cargó y aplicar por mouse la referencia `AP04-GCP-20261111-bf71bf21` devolvió “No hay devoluciones para estos filtros”; repetir Enter desde el campo referencia conservó el estado vacío. Esto confirma que la recepción normal en depósito de ese envío ya no contamina la bandeja.
- **BrowserAct, detalle no elegible:** visitar el detalle del mismo envío con operador mostró “No encontramos una devolución disponible para este envío.” y el enlace “Volver a devoluciones”; no se presentó botón de reintento. Captura final: `docs/auditorias/ap-04/evidencia/commerce-devoluciones-gcp-after-fix-detail-es.png` (1904 × 985). La bandeja filtrada quedó en `docs/auditorias/ap-04/evidencia/commerce-devoluciones-gcp-after-fix-filter-final.png` (1904 × 985); ambas fueron revisadas visualmente.
- **Revisión responsive anterior:** las capturas `commerce-devoluciones-gcp-after-fix-1440.png` y `commerce-devoluciones-gcp-after-fix-320.png` revisan la bandeja antes del pequeño despliegue posterior que solo ajustó el estado de error del detalle. El layout de bandeja no cambió en ese ajuste. `commerce-devoluciones-gcp-after-fix-zoom-equivalent.png` es una aproximación del reflow con 720 CSS px y DPR 2; no acredita el zoom de texto nativo al 200 %.
- **HTTP y transporte:** la carga autenticada y las llamadas nuevas de `/_blazor/initializers` y `/_blazor/negotiate` respondieron 200; la interacción de filtro y Enter se completó. Hubo 503 repetidos de negotiate cuando la sesión BrowserAct previa ya estaba vencida; tras autenticarse y recargar, la sesión interactiva se recuperó. No se hizo una llamada HTTP directa independiente al API para el caso de detalle.
- **Alcance y pendientes:** el escenario continúa sin decisión de devolución, traslado físico ni acuse; la discrepancia de cobertura que impidió preparar una ruta sigue pendiente. No se probó una devolución elegible de extremo a extremo, acuse, persistencia local tras reinicio, CI integrada ni replay A/B. AP-04 permanece `In progress`.
- **Hallazgo HTTP transversal:** BrowserAct registró GET `/js/portal-interactions.js` con 404 en páginas de Commerce. Las interacciones AP-04 verificadas funcionaron; registrar este recurso faltante para triage fuera del flujo AP-04.

## 15. Sesión GCP y revisión BrowserAct posterior (11/11/2026)

- **Despliegue y estado:** las VMs estaban `TERMINATED` cuando los portales dieron 503; había vencido la ventana automática de cuatro horas. `vm-controls.yml` operation `start`, run `43090048785`, terminó `success` en `develop` y aplicó `release-98c273022b504feeb522d7062c948481`. Fuentes fijadas: root `8412c6160d937085e59e6699c6149f008c32e240`, Backend `bac0b0b41c21993a515bacc420915d66a2fd3095`, Frontend `8974044e59f4b52940c5e16841174d0ca83f3460` y Mobile `53f6be2cdec48f48e30e390060feeaefb5be0ead`. A y B pasaron aplicación, salud del balanceador y verificación HTTPS/login; el smoke Redis pasó desde ambos nodos.
- **Seed general:** operation `seed-demo`, run `43092178888`, terminó `success` en 33 s con `synchronized-existing`: 5 operadores, 5 comercios, 70 envíos, 35 rutas y 252 operaciones. No añadió una devolución AP-04 ni creó hechos físicos o acuses.
- **BrowserAct autenticado:** Commerce C2 cargó la bandeja `/devoluciones` sin errores y mostró el estado vacío para el rango predeterminado 13/10/2026–11/11/2026. El detalle de prueba del envío admitido mostró `No encontramos una devolución disponible para este envío.`. Capturas revisadas: `evidencia/commerce-devoluciones-gcp-after-start-list.png` y `evidencia/commerce-devoluciones-gcp-after-start-detail.png` (1904 × 985).
- **Búsqueda en Backoffice:** el código `AP04-GCP-RET-MN-01` fue encontrado y mostró el bulto `01a1cc1b-f22a-7f20-aade-d0269eb451de`, envío `01a1cc1b-f229-733b-8da7-bf69475c71a0`, estado `Admitido`, custodia `Sin recepción`; captura revisada `evidencia/backoffice-recepcion-gcp-admitido-full.png`. El pedido sintético de dos bultos, creado previamente desde Commerce, permanece admitido. No se confirmó recepción porque no se observó presencia física; por lo mismo no se registraron intento fallido, decisión de devolución, transferencia ni acuse. La pantalla de seguimiento desde la lista mostró un error genérico; queda sin diagnóstico y fuera del alcance AP-04.
- **Cierre y límite:** la lista vacía y el 404 localizado se verificaron; no hubo una devolución elegible en el seed general. Mantener `In progress`. Para completar consulta con filas, acuse, refresh/reapertura y recorrido operativo hace falta una fixture de prueba que cumpla los invariantes físicos sin inventar hechos en GCP, o una devolución válida existente. Siguen pendientes CI integrado, Compose local con persistencia, replay A/B, revisión nativa responsive/teclado/200 % y los criterios de cierre del apartado 8.

- Las sesiones BrowserAct de Commerce y Backoffice se cerraron después de guardar la evidencia; el Chrome aislado permanece disponible.

## 16. Fixture AP-04 en el seed general (11/11/2026)

El usuario autorizó crear datos sintéticos si el seed general no contiene una devolución elegible, y autorizó expresamente el despliegue y la verificación BrowserAct de AP-04 en GCP. Esta autorización de GCP se limita a esta feature; la restricción anterior de no operar GCP queda reemplazada para este objetivo.

- Extender `DatosDemoSeeder.SembrarAsync` en las rutas de primera ejecución y repetición. La repetición actual sincroniza actores y retorna temprano, por lo que debe asegurar la fixture antes de retornar.
- Reservar una referencia externa fija por comercio y verificarla bajo el contexto Commerce con los locks/consultas de importación existentes. Una repetición debe confirmar que la identidad apunta a la fixture prevista y salir sin mutar el acuse ni rehacer hechos; un conflicto con otra declaración debe fallar explícitamente.
- Crear la declaración con `IEnviosRepository.GuardarImportadosAsync`, tarifa y huella de importación V2. No crear filas por SQL ni forzar estados de envío o bulto.
- Usar Commerce C2 y Operador 1 del seed general. Registrar admisión mediante cotejo de bulto, tres visitas fallidas separadas al menos por `IntervaloEntreIntentosMinutos`, rendición y recepción en depósito mediante los repositorios y `EjecutarRepartoUseCase` existentes. Reprogramar entre las primeras visitas; iniciar la devolución con `IniciarDevolucionAsync`, recibirla y completar la transferencia a Comercio mediante `IDevolucionesRepository`. La fixture debe quedar pendiente de acuse.
- La cobertura general del operador demo es de lunes. Para que la fixture funcione cualquier día sin publicar cambios de cobertura ni APIs externas, fijar su ruta sintética al lunes local más reciente y usar un `RelojDemo` consistente en admisión, despacho, visitas y recepción. Mantener la creación dentro del lock/transaction del seed, sin resetear datos ni credenciales.
- Identificar cada registro como sintético en la referencia, el código del bulto y observaciones de prueba. No presentarlo como una constatación de un hecho real. El resto del flujo debe ejecutarse con el mismo PostgreSQL/RLS y sin consumos Mapbox o Geoapify.
- En Docker/WSL, ejecutar dos veces el seed y comprobar una única referencia/transferencia; la segunda ejecución no debe duplicar ni reabrir el acuse. En GCP develop, desplegar los gitlinks exactos, ejecutar `seed-demo`, iniciar sesión con la cuenta del seed general en el Chrome BrowserAct aislado, comprobar bandeja, filtro por referencia y detalle, presentar el acuse, recargar y reabrir el detalle. Registrar build, workflow, HTTP, automatización y revisión visual por separado. Mantener `In progress` hasta completar los criterios generales de cierre del apartado 8.

### Resultado local antes de GCP (11/11/2026)

- La primera ejecución debe ocurrir en el proyecto Compose aislado `ap04local`, con un volumen Postgres propio. Nunca cambiar al volumen persistente `nexoruta_postgres_data` ni borrar volúmenes.
- Construir y levantar API/Commerce con los mismos Dockerfiles que producción. Mantener migrador y roles runtime restringidos; el bootstrap local usa credenciales sintéticas guardadas fuera de Git. Geoapify real permanece desactivado y Mapbox temporal no se usa.
- Probar el endpoint de readiness de API y Commerce, iniciar sesión como `admin.comercio2@demo.nexoruta.test`, y recorrer bandeja, filtro, detalle y formulario de acuse. Confirmar la transición del bulto a `Recibido conforme` en una sesión nueva y en la API.
- Ejecutar `POST /api/admin/demo-data` dos veces con credenciales de Plataforma todavía válidas. La segunda ejecución debe conservar el mismo envío, transferencia y acuse, no duplicar la fixture y no reemplazar la contraseña del administrador con la contraseña compartida de los actores demo.
- Si BrowserAct no puede alcanzar `localhost` desde su Chrome aislado, probar la app con un Chrome local temporal y registrar la limitación; usar BrowserAct aislado una vez que GCP esté desplegado. No exponer el servicio local públicamente para unir ambas redes.

## 17. Cierre con seed general y limpieza de aislamiento (12/11/2026)

Esta sección actualiza la ejecución de la fixture y reemplaza las instrucciones previas que pedían mantener el proyecto Compose `ap04local`. El usuario eligió usar los datos del seed general y autorizó retirar el entorno aislado. La evidencia histórica del entorno local se conserva en la auditoría; no debe recrearse ese Compose para continuar.

- Se desplegó en GCP con `vm-controls.yml` `start`, run `43164074196`, release `release-402db30efd0348aa8bac1cc3e224f97f`. Backend AP-04 `ae8b450c3d19711483fcd9bb48ac75317890f08f`, Frontend `c34764eb46444007f69cb525df959a7850f7891d` y Mobile `329dd3454704c0f45b615d609f469b7fd4b2dd5f`; el mismo release quedó saludable en A y B, HTTPS/login y smoke Redis cruzado pasaron. El commit Backend posterior `2ec11a9163291d44634f7647665df5af80bd1476` solo actualiza expectativas/harness de pruebas y no cambia runtime.
- Se ejecutó `seed-demo` run `43165457098` sin duplicar el seed existente. Las dos referencias AP-04 de C2 cubren un detalle inicialmente pendiente y otro ya recibido; se usó el navegador BrowserAct autorizado para registrar un acuse sintético conforme y comprobar persistencia al recargar/reabrir. Las capturas y el resultado API están en `docs/auditorias/ap-04/validacion.md`.
- Se repitió el seed tras el acuse: run `43168257113`, `success`, mismas cantidades 5 operadores / 5 comercios / 70 envíos / 35 rutas / 252 operaciones. La identidad de fixture existente se validó y omitió su creación; no se duplicaron registros ni se reabrió el acuse.
- El seed general comprueba paginación de dos páginas (`limite=1`) y el filtro de recibidas. No acredita por sí solo toda la matriz 307 (total, parcial, histórica y completada). Tampoco se ejecutó replay dirigido API A/B con correlación de nodo ni se obtuvieron digests por instancia: mantener estos puntos abiertos.
- La limpieza de `ap04local` ya terminó: no quedan sus contenedores, red, imágenes ni volúmenes dedicados. No borrar volúmenes globales/ajenos. Usar únicamente datos del seed general para nuevas comprobaciones autorizadas; conservar la auditoría histórica como evidencia.
- Se recompiló `NexoRuta.IntegrationTests` en Windows tras `dotnet restore --locked-mode`: 0 errores, 3 warnings preexistentes. Los arreglos del harness están en Backend `c2be99d` y raíz `1476b06`. Integrated CI `43169249651` terminó `success`: 735/735 pruebas de los tres shards, 0 omitidas, y prueba crítica adicional 1/1. Source policy, builds de Backend/Frontend/Mobile, infraestructura, Cloud SQL/migraciones, pruebas portables y Android pasaron.
- El artefacto `backend-ap04-browser-shard-0` del run verde reporta cuatro checks AP-04 completados y cero errores: autenticación, lista pendiente única, acuse con observaciones, historial/API y reapertura persistida.
- Con el gate verde y el recorrido de seed realizado, el estado de la card queda `Do tests`, no `Done`. Siguen pendientes el dataset que pruebe toda la matriz 307 y el replay dirigido/digests por nodo A/B del criterio 317. El run se puede consultar en GitHub Actions `43169249651`.
- Repositorios en `develop` y gitlinks coherentes al publicar docs/evidencia: raíz `eb7d432f3b8499925d493a75e98fb894b6290c9a`, Backend `c2be99d3070accb724c700fd72595a5636de1cea`, Frontend `c34764eb46444007f69cb525df959a7850f7891d` y Mobile `329dd3454704c0f45b615d609f469b7fd4b2dd5f`. El CI corrió sobre raíz `1476b06`; el commit raíz posterior solo agrega documentación/evidencia y conserva los mismos gitlinks.

## 18. Deploy directo de develop y revalidación final (12/11/2026)

- A pedido del usuario se canceló el CI en curso `43241165368`; no se lanzó otro CI. El despliegue operativo `vm-controls.yml` `update`, run `43241195973`, terminó `success` con la combinación `develop`: raíz `143105f178b7511006d040ec5a4e579d01c2ced8`, Backend `3bd94953c032ed28ffb0a6bc518968fa87004541`, Frontend `c34764eb46444007f69cb525df959a7850f7891d`, Mobile `329dd3454704c0f45b615d609f469b7fd4b2dd5f`; release `release-da53cae5c4064a6b9fa5dcc895600f8e`. Health directo A/B, HTTPS/login smoke y Redis TLS/auth desde ambos nodos pasaron. El run no registra digests A/B ni ejecuta replay dirigido.
- El build local de Backend `3bd9495` pasó sin errores. El `seed-demo` general (runs `43243306693` y `43244352027`) terminó dos veces `success`/`synchronized-existing` con 5 operadores, 5 comercios, 70 envíos, 35 rutas y 252 operaciones. La segunda ejecución posterior al acuse conservó el acuse sin duplicar la fixture.
- BrowserAct en GCP verificó la bandeja C2, filtro por referencia y `Pendiente de acuse`, detalle parcial, acuse conforme, recarga/reapertura e historial persistido. La lista final conserva tres resultados completados. Las páginas/handshake de Blazor observados devolvieron HTTP 200; no se atribuye eso a una llamada directa del navegador a la API.
- El filtro `Histórica` no encuentra datos en el seed. No se inventó un hecho histórico: el criterio 307 sigue abierto por falta de ese caso, aunque total, parcial y completado están representados. El criterio 317 sigue abierto hasta obtener digests por instancia y ejecutar el mismo comando directamente contra API A y B con telemetría que identifique cada nodo. Mantener la card `Do tests`; no cambiarla a `Done`.
- Evidencia nueva revisada visualmente en `docs/auditorias/ap-04/validacion.md`. Se conserva el entorno general GCP de desarrollo y no se recrea el Compose `ap04local`.

### Continuación autorizada: dataset histórico sintético (12/11/2026)

- A pedido del usuario se amplía el seed general para incluir `AP04-GCP-DEV-C2-04-HIST`. El caso se construye como estado heredado sintético: el seed registra el recorrido de retorno y recepción en depósito con sus operaciones existentes y luego usa el método de dominio para representar custodia comercial histórica sin fila de transferencia AP-04 ni acuse. Esto permite comprobar la clasificación `Histórica` y el bloqueo del acuse; no se presenta como una nueva constatación de entrega física.
- La fecha queda dentro del filtro predeterminado de 30 días de Commerce. La identidad de referencia/código se comprueba para que el seed repetido no duplique ni altere hechos existentes.
- Backend `db38a2ac31d69e2a70411c283238e28400636d77` se publicó en `develop`; compilación local de Infrastructure pasó con 0 errores. Por instrucción del usuario no se lanza CI de GitHub. Falta desplegar esta combinación, repetir el seed general y verificar en BrowserAct la matriz total/parcial/histórica/completada y los filtros/cursor.
- El replay dirigido entre API A/B y los digests por instancia siguen pendientes hasta realizar la operación con correlación de nodo y telemetría. Mantener la card `Do tests` mientras esos resultados no estén registrados.
