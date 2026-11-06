# Auditoria estatica integral contra el Excel vigente

**Resultado:** hay implementacion extensa de configuracion, admision, bultos, rutas y operacion offline, pero no corresponde declarar cumplimiento integral. Las brechas de producto prioritarias estan en solicitud publica de reprogramacion, avisos de destinatario y HTTP del comercio, tablero vivo, reportes/liquidacion y cierre diario. El alcance literal de CU-01 requiere aceptacion expresa de la desviacion ya acordada.

Fecha: 2026-11-05. Base integrada: principal `4e5c233`, backend `09538d9`, frontend `d328e98`, mobile `683766d`. Solo informes: sin cambios de producto, servicios, Git o migraciones por este worker.

## Lectura rapida

1. Resolver la celda NFR10 corrupta y la aceptacion academica de CU-01.
2. Revisar el plan por circuitos; no construir opciones descartadas ni atribuir puntos por paquetes instalados.
3. Ejecutar las recetas normales con los datos sinteticos del equipo; separar HTTP, automatizacion, compilacion y revision visual.

## Fuentes y significado del dictamen

- Fuente primaria: [inventory.json](inventory.json), 93 registros originales: 30 CU, 9 AP, 24 D, 15 NFR y 15 OPT; conserva nombres, hojas, filas, requisitos, seleccion y procedencia del responsable. [Seleccion de fuente](source-selection.md): comparar contenido/revision, no solo fecha de archivo. La copia solicitada con sufijo `(2)` no fue encontrada y no se inventa.
- [extension-source.json](extension-source.json) conserva el PDF de cambio. Requisitos originales 31–41 se presentan aparte como `EXT31`–`EXT41` para navegacion de esta auditoria, no como nuevos CU del Excel. Los titulos de navegacion de extensiones no son titulos originales.
- [assessment.json](assessment.json) es la evaluacion estructurada con citas de codigo; [assessment.csv](assessment.csv) tiene las 104 filas con todas las columnas solicitadas.
- **Implementacion Completa**: la inspeccion encontro los componentes del alcance descrito y sus consumidores, sin brecha funcional concreta identificada. No es aceptacion ni certificacion; los otros ejes y dependencias pueden seguir abiertos. **Parcial**: hay comportamiento aprovechable pero una parte concreta falta. **Ausente**: no se encontro el comportamiento solicitado, aunque existan insumos cercanos.
- **Verificacion Comprobado** exige prueba observada del requisito completo. **Falla** exige fallo actual reproducido. **No verificado** significa evidencia actual insuficiente. **Bloqueado** identifica prueba requerida impedida por fuente corrupta o interaccion nativa denegada. No se usa existencia de clase/endpoint/test como cumplimiento.
- Pruebas fuente citadas abajo fueron inspeccionadas; solo las listadas como nuevas ejecuciones cuentan como ejecutadas. `docs/cambios-requerimientos/INTEGRACION-DEVELOP.md`, VALIDACION y auditorias anteriores son antecedentes historicos, no evidencia de esta sesion.

### Anomalias documentales que no se reparan durante la auditoria

- `No funcionales!F13` (NFR10) contiene literalmente **e**. La version HEAD contiene el requisito de SignalR autenticado, autorizado, aislado por tenant y varias API. Se conserva ambos en inventario; falta confirmar/corregir la fuente. El tablero CU29 sigue siendo obligatorio por su propio texto.
- CU01 documenta explicitamente una decision vigente distinta del actor/superficie del Excel: el operador no administra comercios. No es autorizacion para revertir esa decision; se requiere aceptacion del docente/equipo.
- Hay documentos de arquitectura/presentacion obsoletos: por ejemplo, dicen RLS pendiente o Tracking sin funcionalidad mientras el codigo actual si los tiene. Reconciliar tras la validacion, sin sustituir evidencia por prosa.

## Evidencia nueva y limites

| Canal | Evidencia actual | Limite |
|---|---|---|
| Compilacion | Equipo padre gestiona builds vigentes; consultar informe de entorno y ANDROID.md | Compilar no prueba flujo de negocio |
| Pruebas automatizadas | Backend Unit 336/336; Architecture 4/4; Mobile Core36 + Api61 + Application92 + Storage35 = 224/224 | Bibliotecas portables, no hardware/Android; no aceptacion completa por CU |
| Frontend | Primera invocacion 490 pasan, 1 falla, 5 omitidas por raiz de fuente del harness externo; rerun corregido propiedad del agente de entorno | No presentar fallo del harness como defecto de producto ni omisiones como aprobadas |
| HTTP SSR | [portal-http.json](portal-http.json): login y rutas autenticas del operador/Commerce devuelven 200 sin errores SSR reconocidos | No se enviaron formularios de negocio ni se uso navegador |
| Automatizacion navegador | Sin ejecucion nueva de navegador por este worker | Tests/capturas historicos no cuentan |
| Revision visual y Android nativo | Bloqueada por denegacion de interaccion Brave/qemu; ver ANDROID.md y sintesis del padre | No se afirma foco, teclado, 320px, zoom, contraste, camara/GPS o firma |
| Servicios externos | No se invoco Mapbox/Geoapify de pago, nube remota ni push productivo | Ensayos pendientes requieren autorizacion y respuestas controladas |

Resumen de los 93 registros (incluye dependencias y opciones descartadas; no es porcentaje de avance): {'Parcial': 31, 'Completa': 44, 'Ausente': 18}. Verificacion: {'No verificado': 83, 'Bloqueado': 10}. Ningun requisito se promueve a Comprobado solo por tests unitarios/SSR.

## Plan recomendado, por circuitos

| Prioridad | Requisitos exactos | Modulo / actor | Siguiente resultado verificable |
|---|---|---|---|
| P0 | NFR10 | M06; responsable de fuente | Confirmar texto de celda F13; no sustituirlo automaticamente |
| P1 decision | CU01 | M01; operador/administrador | Aceptacion de desviacion de autogestion/plataforma respecto al Excel |
| P1 | CU26; D16 | M05; destinatario | Solicitud publica de reprogramacion, reglas e historial de tratamiento |
| P1 | CU28/AP05/NFR09/D18; EXT36/41 | M05; sistema/comercio | Suscripcion, HTTP firmado, reintentos crecientes, fallidos, historial/reenvio y receptor de prueba |
| P1 | CU27/D17/D24 | M05; sistema/destinatario | Aviso unico tras commit, incluso entrega offline sincronizada |
| P1 | CU29/D19-D21; EXT41 | M06; despachador | Tablero vivo de posicion y riesgo con aislamiento y dos instancias |
| P1 | CU30/AP06/D22-D23; EXT41 | M06; operador/comercio | Cumplimiento por zona/repartidor/comercio, motivos, volumen, liquidacion y cuenta corriente |
| P1 | AP09 | M06; Worker | Cierre diario idempotente y unico por operador/fecha, no FinJornada manual |
| P1 | AP01/AP04/AP07 | M06/M02/M05; backoffice/comercio/destinatario | Incidencia general resuelta, gestion de devolucion propia y ventana publica |
| P1 evidencia | NFR03/07/08/11-15; OPT03/05/06/07/09 | Transversal, ver responsables por modulo | Completar controles faltantes y pruebas de aceptacion indicadas; cache solo auditar al equipo propietario |
| P2 | CU02-CU24/AP02/AP03/AP08/EXT31-35/37-40 | Actores de cada fila | Ejecutar circuitos normales actuales, preservar diario/datos, registrar evidencia separada |

### Opcionales: seleccion no es acreditacion

**Seleccionados: 14 puntos potenciales; acreditados por esta auditoria: 0.** OPT03 Kafka3, OPT05 NoSQL2, OPT06 carga2, OPT07 cobertura2, OPT08 E2E2 y OPT09 push3. OPT08 tiene implementacion estatica completa, pero sus resultados actuales y condiciones de aceptacion aun no se acreditaron. Las condiciones especificas faltantes estan en cada fila. Los otros nueve siguen descartados y no son pendientes de implementacion obligatoria.

## Matriz completa del Excel

| ID y nombre original | Fuente | Modulo / actor | Implementacion | Verificacion | Prioridad |
|---|---|---|---|---|---|
| [CU-01 — Comercios y usuarios](#cu01) | CU obligatorios!A4:I4 (fila 4) | M01 / Operador / administrador | Parcial | No verificado | P1 |
| [CU-02 — Zonas y franjas](#cu02) | CU obligatorios!A5:I5 (fila 5) | M01 / Operador / administrador | Completa | No verificado | P2 |
| [CU-03 — Tarifas configurables](#cu03) | CU obligatorios!A6:I6 (fila 6) | M01 / Operador / administrador | Completa | No verificado | P2 |
| [CU-04 — Reglas operativas](#cu04) | CU obligatorios!A7:I7 (fila 7) | M01 / Operador / administrador | Completa | No verificado | P2 |
| [CU-05 — Identidad visual](#cu05) | CU obligatorios!A8:I8 (fila 8) | M01 / Operador / administrador | Completa | No verificado | P2 |
| [CU-06 — Repartidores y vehículos](#cu06) | CU obligatorios!A9:I9 (fila 9) | M03 / Operador / administrador | Completa | No verificado | P2 |
| [CU-07 — Alta de envíos](#cu07) | CU obligatorios!A10:I10 (fila 10) | M02 / Comercio | Completa | No verificado | P2 |
| [CU-08 — Bultos](#cu08) | CU obligatorios!A11:I11 (fila 11) | M02 / Comercio | Completa | No verificado | P2 |
| [CU-09 — Cálculo de tarifa](#cu09) | CU obligatorios!A12:I12 (fila 12) | M02 / Comercio | Completa | No verificado | P2 |
| [CU-10 — Recepción en depósito](#cu10) | CU obligatorios!A13:I13 (fila 13) | M02 / Operario de depósito | Completa | No verificado | P2 |
| [CU-11 — Estado del envío](#cu11) | CU obligatorios!A14:I14 (fila 14) | M02 / Sistema | Completa | No verificado | P2 |
| [CU-12 — Eventos del envío](#cu12) | CU obligatorios!A15:I15 (fila 15) | M02 / Sistema | Completa | No verificado | P2 |
| [CU-13 — Armar rutas](#cu13) | CU obligatorios!A16:I16 (fila 16) | M03 / Despachador | Completa | No verificado | P2 |
| [CU-14 — Validar restricciones](#cu14) | CU obligatorios!A17:I17 (fila 17) | M03 / Despachador | Completa | No verificado | P2 |
| [CU-15 — Evitar doble asignación](#cu15) | CU obligatorios!A18:I18 (fila 18) | M03 / Despachador | Completa | No verificado | P2 |
| [CU-16 — Ordenar paradas](#cu16) | CU obligatorios!A19:I19 (fila 19) | M03 / Despachador | Parcial | No verificado | P1 |
| [CU-17 — Despachar ruta](#cu17) | CU obligatorios!A20:I20 (fila 20) | M03 / Despachador | Completa | No verificado | P2 |
| [CU-18 — Descargar ruta](#cu18) | CU obligatorios!A21:I21 (fila 21) | M04 / Repartidor | Completa | Bloqueado | P2 |
| [CU-19 — Escanear carga](#cu19) | CU obligatorios!A22:I22 (fila 22) | M04 / Repartidor | Completa | Bloqueado | P2 |
| [CU-20 — Registrar entrega](#cu20) | CU obligatorios!A23:I23 (fila 23) | M04 / Repartidor | Completa | Bloqueado | P2 |
| [CU-21 — Registrar intento fallido](#cu21) | CU obligatorios!A24:I24 (fila 24) | M04 / Repartidor | Completa | Bloqueado | P2 |
| [CU-22 — Devolución y rendición](#cu22) | CU obligatorios!A25:I25 (fila 25) | M04 / Repartidor / depósito | Completa | Bloqueado | P2 |
| [CU-23 — Posición del vehículo](#cu23) | CU obligatorios!A26:I26 (fila 26) | M04 / Repartidor / despachador | Parcial | Bloqueado | P1 |
| [CU-24 — Sincronización diferida](#cu24) | CU obligatorios!A27:I27 (fila 27) | M04 / Repartidor / sistema | Completa | Bloqueado | P2 |
| [CU-25 — Seguimiento público](#cu25) | CU obligatorios!A28:I28 (fila 28) | M05 / Destinatario | Completa | No verificado | P2 |
| [CU-26 — Reprogramación](#cu26) | CU obligatorios!A29:I29 (fila 29) | M05 / Destinatario | Ausente | No verificado | P1 |
| [CU-27 — Avisos al destinatario](#cu27) | CU obligatorios!A30:I30 (fila 30) | M05 / Sistema | Ausente | No verificado | P1 |
| [CU-28 — Avisos a comercios](#cu28) | CU obligatorios!A31:I31 (fila 31) | M05 / Sistema / comercio | Ausente | No verificado | P1 |
| [CU-29 — Tablero en vivo](#cu29) | CU obligatorios!A32:I32 (fila 32) | M06 / Despachador | Parcial | No verificado | P1 |
| [CU-30 — Reportes y liquidación](#cu30) | CU obligatorios!A33:I33 (fila 33) | M06 / Operador / comercio | Parcial | No verificado | P1 |
| [AP-01 — Gestión de incidencias](#ap01) | Alcance aplicaciones!A4:G4 (fila 4) | M06 / — | Parcial | No verificado | P1 |
| [AP-02 — Etiquetas](#ap02) | Alcance aplicaciones!A5:G5 (fila 5) | M02 / — | Completa | No verificado | P2 |
| [AP-03 — Consulta del comercio](#ap03) | Alcance aplicaciones!A6:G6 (fila 6) | M02 / — | Completa | No verificado | P2 |
| [AP-04 — Devoluciones del comercio](#ap04) | Alcance aplicaciones!A7:G7 (fila 7) | M02 / — | Parcial | No verificado | P1 |
| [AP-05 — Suscripción de avisos](#ap05) | Alcance aplicaciones!A8:G8 (fila 8) | M05 / — | Ausente | No verificado | P1 |
| [AP-06 — Cuenta corriente](#ap06) | Alcance aplicaciones!A9:G9 (fila 9) | M06 / — | Ausente | No verificado | P1 |
| [AP-07 — Ventana estimada](#ap07) | Alcance aplicaciones!A10:G10 (fila 10) | M05 / — | Ausente | No verificado | P1 |
| [AP-08 — Navegación de ruta](#ap08) | Alcance aplicaciones!A11:G11 (fila 11) | M04 / — | Completa | Bloqueado | P2 |
| [AP-09 — Cierre diario](#ap09) | Alcance aplicaciones!A12:G12 (fila 12) | M06 / — | Ausente | No verificado | P1 |
| [D01 — (sin titulo original; dependencia)](#d01) | Dependencias!A4:I4 (fila 4) | M02 / — | Completa | No verificado | P2 |
| [D02 — (sin titulo original; dependencia)](#d02) | Dependencias!A5:I5 (fila 5) | M02 / — | Completa | No verificado | P2 |
| [D03 — (sin titulo original; dependencia)](#d03) | Dependencias!A6:I6 (fila 6) | M02 / — | Completa | No verificado | P2 |
| [D04 — (sin titulo original; dependencia)](#d04) | Dependencias!A7:I7 (fila 7) | M03 / — | Completa | No verificado | P2 |
| [D05 — (sin titulo original; dependencia)](#d05) | Dependencias!A8:I8 (fila 8) | M03 / — | Completa | No verificado | P2 |
| [D06 — (sin titulo original; dependencia)](#d06) | Dependencias!A9:I9 (fila 9) | M03 / — | Completa | No verificado | P2 |
| [D07 — (sin titulo original; dependencia)](#d07) | Dependencias!A10:I10 (fila 10) | M03 / — | Completa | No verificado | P2 |
| [D08 — (sin titulo original; dependencia)](#d08) | Dependencias!A11:I11 (fila 11) | M04 / — | Completa | No verificado | P2 |
| [D09 — (sin titulo original; dependencia)](#d09) | Dependencias!A12:I12 (fila 12) | M04 / — | Completa | No verificado | P2 |
| [D10 — (sin titulo original; dependencia)](#d10) | Dependencias!A13:I13 (fila 13) | M04 / — | Completa | No verificado | P2 |
| [D11 — (sin titulo original; dependencia)](#d11) | Dependencias!A14:I14 (fila 14) | M04 / — | Completa | No verificado | P2 |
| [D12 — (sin titulo original; dependencia)](#d12) | Dependencias!A15:I15 (fila 15) | M04 / — | Completa | No verificado | P2 |
| [D13 — (sin titulo original; dependencia)](#d13) | Dependencias!A16:I16 (fila 16) | M04 / — | Completa | No verificado | P2 |
| [D14 — (sin titulo original; dependencia)](#d14) | Dependencias!A17:I17 (fila 17) | M05 / — | Parcial | No verificado | P1 |
| [D15 — (sin titulo original; dependencia)](#d15) | Dependencias!A18:I18 (fila 18) | M05 / — | Completa | No verificado | P2 |
| [D16 — (sin titulo original; dependencia)](#d16) | Dependencias!A19:I19 (fila 19) | M05 / — | Ausente | No verificado | P1 |
| [D17 — (sin titulo original; dependencia)](#d17) | Dependencias!A20:I20 (fila 20) | M05 / — | Parcial | No verificado | P1 |
| [D18 — (sin titulo original; dependencia)](#d18) | Dependencias!A21:I21 (fila 21) | M05 / — | Ausente | No verificado | P1 |
| [D19 — (sin titulo original; dependencia)](#d19) | Dependencias!A22:I22 (fila 22) | M06 / — | Parcial | No verificado | P1 |
| [D20 — (sin titulo original; dependencia)](#d20) | Dependencias!A23:I23 (fila 23) | M06 / — | Parcial | No verificado | P1 |
| [D21 — (sin titulo original; dependencia)](#d21) | Dependencias!A24:I24 (fila 24) | M06 / — | Parcial | No verificado | P1 |
| [D22 — (sin titulo original; dependencia)](#d22) | Dependencias!A25:I25 (fila 25) | M06 / — | Parcial | No verificado | P1 |
| [D23 — (sin titulo original; dependencia)](#d23) | Dependencias!A26:I26 (fila 26) | M06 / — | Parcial | No verificado | P1 |
| [D24 — (sin titulo original; dependencia)](#d24) | Dependencias!A27:I27 (fila 27) | M05 / — | Parcial | No verificado | P1 |
| [NFR-01 — Plataforma y arquitectura](#nfr01) | No funcionales!A4:F4 (fila 4) | M01 / — | Completa | No verificado | P2 |
| [NFR-02 — Presentación web](#nfr02) | No funcionales!A5:F5 (fila 5) | M01 / — | Parcial | No verificado | P2 |
| [NFR-03 — Seguridad](#nfr03) | No funcionales!A6:F6 (fila 6) | M01 / — | Parcial | No verificado | P1 |
| [NFR-04 — Persistencia](#nfr04) | No funcionales!A7:F7 (fila 7) | M02 / — | Completa | No verificado | P2 |
| [NFR-05 — Multitenancy](#nfr05) | No funcionales!A8:F8 (fila 8) | M01 / — | Completa | No verificado | P2 |
| [NFR-06 — Configurabilidad](#nfr06) | No funcionales!A9:F9 (fila 9) | M01 / — | Completa | No verificado | P2 |
| [NFR-07 — Caché distribuido](#nfr07) | No funcionales!A10:F10 (fila 10) | M05 / — | Parcial | No verificado | P1 |
| [NFR-08 — Mensajería y worker](#nfr08) | No funcionales!A11:F11 (fila 11) | M05 / — | Parcial | No verificado | P1 |
| [NFR-09 — Avisos a comercios](#nfr09) | No funcionales!A12:F12 (fila 12) | M05 / — | Ausente | No verificado | P1 |
| [NFR-10 — Tiempo real](#nfr10) | No funcionales!A13:F13 (fila 13) | M06 / — | Ausente | Bloqueado | P0 |
| [NFR-11 — MAUI](#nfr11) | No funcionales!A14:F14 (fila 14) | M04 / — | Parcial | Bloqueado | P1 |
| [NFR-12 — Observabilidad](#nfr12) | No funcionales!A15:F15 (fila 15) | M06 / — | Parcial | No verificado | P1 |
| [NFR-13 — Escalabilidad](#nfr13) | No funcionales!A16:F16 (fila 16) | M01 / — | Parcial | No verificado | P1 |
| [NFR-14 — Nube e IaC](#nfr14) | No funcionales!A17:F17 (fila 17) | M01 / — | Parcial | No verificado | P1 |
| [NFR-15 — Calidad](#nfr15) | No funcionales!A18:F18 (fila 18) | M02 / — | Parcial | No verificado | P1 |
| [OPT-01 — Seguimiento público como servicio independiente](#opt01) | Opcionales!A4:G4 (fila 4) | M05 / — | Ausente | No verificado | Sin accion |
| [OPT-02 — gRPC para sincronización y telemetría móvil](#opt02) | Opcionales!A5:G5 (fila 5) | M04 / — | Ausente | No verificado | Sin accion |
| [OPT-03 — Kafka para eventos de flota](#opt03) | Opcionales!A6:G6 (fila 6) | M04 / M06 / — | Parcial | No verificado | P1 |
| [OPT-04 — Autoescalado horizontal](#opt04) | Opcionales!A7:G7 (fila 7) | M01 / — | Ausente | No verificado | Sin accion |
| [OPT-05 — NoSQL para historial y analítica](#opt05) | Opcionales!A8:G8 (fila 8) | M02 / M06 / — | Parcial | No verificado | P1 |
| [OPT-06 — Pruebas de carga automatizadas](#opt06) | Opcionales!A9:G9 (fila 9) | M06 / — | Parcial | No verificado | P1 |
| [OPT-07 — Cobertura de pruebas](#opt07) | Opcionales!A10:G10 (fila 10) | Transversal / — | Parcial | No verificado | P1 |
| [OPT-08 — Pruebas extremo a extremo](#opt08) | Opcionales!A11:G11 (fila 11) | Transversal / — | Completa | No verificado | P2 |
| [OPT-09 — Notificaciones remotas en producción](#opt09) | Opcionales!A12:G12 (fila 12) | M04 / — | Parcial | No verificado | P1 |
| [OPT-10 — Geocercas](#opt10) | Opcionales!A13:G13 (fila 13) | M04 / — | Ausente | No verificado | Sin accion |
| [OPT-11 — Impresión Bluetooth](#opt11) | Opcionales!A14:G14 (fila 14) | M04 / — | Ausente | No verificado | Sin accion |
| [OPT-12 — Optimización del orden de paradas](#opt12) | Opcionales!A15:G15 (fila 15) | M03 / — | Ausente | No verificado | Sin accion |
| [OPT-13 — API pública para comercios](#opt13) | Opcionales!A16:G16 (fila 16) | M02 / — | Parcial | No verificado | Sin accion |
| [OPT-14 — Banderas de funcionalidad](#opt14) | Opcionales!A17:G17 (fila 17) | M01 / — | Ausente | No verificado | Sin accion |
| [OPT-15 — Pruebas de resiliencia](#opt15) | Opcionales!A18:G18 (fila 18) | Transversal / — | Parcial | No verificado | Sin accion |

## Evaluacion detallada y recetas normales

Las recetas son propuestas reproducibles, **no ejecuciones observadas**. Usar organizaciones y destinatarios sinteticos, cuentas/credenciales del fixture autorizado, geocodificacion/routing controlados y bases efimeras. No reutilizar secretos ni datos persistentes del usuario; no bajar servicios ni aplicar migraciones a su base. La comprobacion comprende respuesta/salida, estado persistido y ausencia de efectos duplicados, no solo HTTP 200.

<a id="cu01"></a>
### CU-01 — Comercios y usuarios

**Fuente:** CU obligatorios!A4:I4 (fila 4). **Modulo:** M01. **Actor:** Operador / administrador. **Responsable:** José Garcia (derivado de Modulos, no asignacion individual de esta fila).

> ABM de comercios y usuarios, perfiles y permisos.

**Implementacion:** Parcial. **Verificacion:** No verificado. **Prioridad:** P1.

- Existe: Alta/listado de organizaciones, edicion propia, baja/reactivacion, usuarios activos/inactivos y roles/permisos, con portales diferenciados.
- Falta / limite: Desviacion de alcance explicita, no bug a reparar automaticamente: modelo acordado autogestiona comercio y plataforma, mientras el Excel ubica ABM en Backoffice del operador. Aceptacion academica pendiente.
- Siguiente accion y receta no ejecutada: Obtener aceptacion de la desviacion del actor/superficie respecto al Excel; no conceder al operador administracion de comercios sin nueva decision de producto.
- Evidencia: [`backend/src/NexoRuta.Api/Controllers/UsuariosController.cs:13`](../../../backend/src/NexoRuta.Api/Controllers/UsuariosController.cs#L13); [`backend/src/NexoRuta.Api/Features/Usuarios/Controllers/AltaPropiaController.cs:18`](../../../backend/src/NexoRuta.Api/Features/Usuarios/Controllers/AltaPropiaController.cs#L18); [`backend/src/NexoRuta.Api/Features/Organizaciones/Controllers/OrganizacionPropiaController.cs:17`](../../../backend/src/NexoRuta.Api/Features/Organizaciones/Controllers/OrganizacionPropiaController.cs#L17); [`backend/src/NexoRuta.Api/Features/Plataforma/OrganizacionesController.cs:12`](../../../backend/src/NexoRuta.Api/Features/Plataforma/OrganizacionesController.cs#L12); [`backend/tests/NexoRuta.IntegrationTests/Administracion/RolesHttpTests.cs:13`](../../../backend/tests/NexoRuta.IntegrationTests/Administracion/RolesHttpTests.cs#L13); [`backend/docs/cu/CU-01-comercios-usuarios.md:9`](../../../backend/docs/cu/CU-01-comercios-usuarios.md#L9).

<a id="cu02"></a>
### CU-02 — Zonas y franjas

**Fuente:** CU obligatorios!A5:I5 (fila 5). **Modulo:** M01. **Actor:** Operador / administrador. **Responsable:** José Garcia (derivado de Modulos, no asignacion individual de esta fila).

> Definir zonas de cobertura y franjas de entrega ofrecidas por zona.

**Implementacion:** Completa. **Verificacion:** No verificado. **Prioridad:** P2.

- Existe: Cobertura geometrica versionada, franjas, API y editor Razor, con persistencia PostGIS.
- Falta / limite: Pendiente ejecutar flujo normal y aislamiento.
- Siguiente accion y receta no ejecutada: Crear zona/franja en Backoffice, guardar/reabrir y comprobar oferta Commerce.
- Evidencia: [`backend/src/NexoRuta.Api/Features/ZonasCobertura/Controllers/ZonasCoberturaController.cs:51`](../../../backend/src/NexoRuta.Api/Features/ZonasCobertura/Controllers/ZonasCoberturaController.cs#L51); [`backend/src/NexoRuta.Infrastructure/ZonasCobertura/EfZonasCoberturaRepository.cs:12`](../../../backend/src/NexoRuta.Infrastructure/ZonasCobertura/EfZonasCoberturaRepository.cs#L12); [`frontend/src/NexoRuta.Backoffice/Pages/ZonasCobertura/Detalle.cshtml:1`](../../../frontend/src/NexoRuta.Backoffice/Pages/ZonasCobertura/Detalle.cshtml#L1); [`backend/tests/NexoRuta.IntegrationTests/ZonasCobertura/ZonaCoberturaPostgisTests.cs:13`](../../../backend/tests/NexoRuta.IntegrationTests/ZonasCobertura/ZonaCoberturaPostgisTests.cs#L13).

<a id="cu03"></a>
### CU-03 — Tarifas configurables

**Fuente:** CU obligatorios!A6:I6 (fila 6). **Modulo:** M01. **Actor:** Operador / administrador. **Responsable:** José Garcia (derivado de Modulos, no asignacion individual de esta fila).

> Configurar tarifas por zona, peso, volumen y modalidad, con recargos y bonificaciones, desde la interfaz.

**Implementacion:** Completa. **Verificacion:** No verificado. **Prioridad:** P2.

- Existe: Tarifario por zona/modalidad, peso/volumen y ajustes; borrador/publicacion, simulador e historial.
- Falta / limite: Publicacion y lectura sin despliegue no ejecutadas.
- Siguiente accion y receta no ejecutada: Publicar tarifa con recargo/bonificacion y cotizar desde Commerce sin reiniciar.
- Evidencia: [`backend/src/NexoRuta.Domain/Tarifas/CalculadoraTarifas.cs:3`](../../../backend/src/NexoRuta.Domain/Tarifas/CalculadoraTarifas.cs#L3); [`frontend/src/NexoRuta.Backoffice/Pages/Tarifas/Borrador.cshtml:1`](../../../frontend/src/NexoRuta.Backoffice/Pages/Tarifas/Borrador.cshtml#L1); [`backend/tests/NexoRuta.IntegrationTests/Tarifas/TarifarioHttpTests.cs:20`](../../../backend/tests/NexoRuta.IntegrationTests/Tarifas/TarifarioHttpTests.cs#L20).

<a id="cu04"></a>
### CU-04 — Reglas operativas

**Fuente:** CU obligatorios!A7:I7 (fila 7). **Modulo:** M01. **Actor:** Operador / administrador. **Responsable:** José Garcia (derivado de Modulos, no asignacion individual de esta fila).

> Configurar intentos, intervalos, prueba exigida, motivos, devoluciones y plazos por modalidad.

**Implementacion:** Completa. **Verificacion:** No verificado. **Prioridad:** P2.

- Existe: Publicaciones de intentos, intervalo, prueba, motivos, devoluciones/plazos; version fijada al admitir.
- Falta / limite: Conservacion de version y aplicacion operacional no ejecutadas.
- Siguiente accion y receta no ejecutada: Publicar dos versiones y comprobar intento/prueba de envio anterior con version original.
- Evidencia: [`backend/src/NexoRuta.Domain/ReglasOperativas/VersionReglasOperativas.cs:3`](../../../backend/src/NexoRuta.Domain/ReglasOperativas/VersionReglasOperativas.cs#L3); [`backend/src/NexoRuta.Api/Features/ReglasOperativas/Controllers/ReglasOperativasController.cs:26`](../../../backend/src/NexoRuta.Api/Features/ReglasOperativas/Controllers/ReglasOperativasController.cs#L26); [`backend/src/NexoRuta.Infrastructure/Envios/Repositories/EfEnviosRepository.cs:69`](../../../backend/src/NexoRuta.Infrastructure/Envios/Repositories/EfEnviosRepository.cs#L69); [`backend/tests/NexoRuta.IntegrationTests/ReglasOperativas/ReglasOperativasHttpTests.cs:15`](../../../backend/tests/NexoRuta.IntegrationTests/ReglasOperativas/ReglasOperativasHttpTests.cs#L15).

<a id="cu05"></a>
### CU-05 — Identidad visual

**Fuente:** CU obligatorios!A8:I8 (fila 8). **Modulo:** M01. **Actor:** Operador / administrador. **Responsable:** José Garcia (derivado de Modulos, no asignacion individual de esta fila).

> Configurar marca, colores y contacto para portal, seguimiento y comunicaciones.

**Implementacion:** Completa. **Verificacion:** No verificado. **Prioridad:** P2.

- Existe: Marca/colores/contacto/logo versionados y consumidores Commerce, Tracking y correo de cancelacion.
- Falta / limite: Sin consumo visual/SMTP comprobado de todas las superficies.
- Siguiente accion y receta no ejecutada: Cambiar marca y comprobar Commerce, Tracking y correo capturado con dos operadores.
- Evidencia: [`backend/src/NexoRuta.Api/Features/IdentidadVisual/Controllers/IdentidadVisualOperadorController.cs:29`](../../../backend/src/NexoRuta.Api/Features/IdentidadVisual/Controllers/IdentidadVisualOperadorController.cs#L29); [`frontend/src/NexoRuta.Tracking/Components/Pages/Seguimiento.razor:30`](../../../frontend/src/NexoRuta.Tracking/Components/Pages/Seguimiento.razor#L30); [`backend/src/NexoRuta.Infrastructure/Seguimiento/Processing/CorreoCodigoCancelacion.cs:6`](../../../backend/src/NexoRuta.Infrastructure/Seguimiento/Processing/CorreoCodigoCancelacion.cs#L6); [`backend/tests/NexoRuta.IntegrationTests/Administracion/IdentidadVisualOperadorHttpTests.cs:21`](../../../backend/tests/NexoRuta.IntegrationTests/Administracion/IdentidadVisualOperadorHttpTests.cs#L21); [`backend/src/NexoRuta.Worker/Messaging/ProcesarCorreoCodigoCancelacion.cs:33`](../../../backend/src/NexoRuta.Worker/Messaging/ProcesarCorreoCodigoCancelacion.cs#L33).

<a id="cu06"></a>
### CU-06 — Repartidores y vehículos

**Fuente:** CU obligatorios!A9:I9 (fila 9). **Modulo:** M03. **Actor:** Operador / administrador. **Responsable:** Nacho (derivado de Modulos, no asignacion individual de esta fila).

> Gestionar repartidores, vehículos y capacidad de carga.

**Implementacion:** Completa. **Verificacion:** No verificado. **Prioridad:** P2.

- Existe: Perfil de repartidor, vehiculos con capacidad, gestion UI y ocupacion de flota.
- Falta / limite: Altas/ediciones desde navegador no ejecutadas.
- Siguiente accion y receta no ejecutada: Crear repartidor/vehiculo, cambiar capacidad y comprobar planificacion.
- Evidencia: [`backend/src/NexoRuta.Api/Features/Reparto/Controllers/RepartidoresController.cs:31`](../../../backend/src/NexoRuta.Api/Features/Reparto/Controllers/RepartidoresController.cs#L31); [`backend/src/NexoRuta.Api/Features/Reparto/Controllers/ConfiguracionRepartoController.cs:54`](../../../backend/src/NexoRuta.Api/Features/Reparto/Controllers/ConfiguracionRepartoController.cs#L54); [`frontend/src/NexoRuta.Backoffice/Pages/Vehiculos.cshtml:1`](../../../frontend/src/NexoRuta.Backoffice/Pages/Vehiculos.cshtml#L1); [`backend/tests/NexoRuta.IntegrationTests/Reparto/VehiculosIntegracionBackofficeHttpTests.cs:9`](../../../backend/tests/NexoRuta.IntegrationTests/Reparto/VehiculosIntegracionBackofficeHttpTests.cs#L9).

<a id="cu07"></a>
### CU-07 — Alta de envíos

**Fuente:** CU obligatorios!A10:I10 (fila 10). **Modulo:** M02. **Actor:** Comercio. **Responsable:** sin asignacion individual (derivado de Modulos, no asignacion individual de esta fila).

> Alta individual, por archivo y API; importación masiva idempotente, incluso parcial.

**Implementacion:** Completa. **Verificacion:** No verificado. **Prioridad:** P2.

- Existe: Alta REST/Commerce y CSV, identidad de importacion y bloqueo transaccional para reimportacion parcial idempotente.
- Falta / limite: No se ejecuto importacion/reintento vigente.
- Siguiente accion y receta no ejecutada: Importar dos filas, reimportar una y contrastar identidad y numero de envios.
- Evidencia: [`backend/src/NexoRuta.Api/Features/Envios/Controllers/EnviosController.cs:180`](../../../backend/src/NexoRuta.Api/Features/Envios/Controllers/EnviosController.cs#L180); [`backend/src/NexoRuta.Infrastructure/Envios/Repositories/EfEnviosRepository.cs:44`](../../../backend/src/NexoRuta.Infrastructure/Envios/Repositories/EfEnviosRepository.cs#L44); [`frontend/src/NexoRuta.Commerce/Components/Features/Envios/Pages/ImportarEnvios.razor:1`](../../../frontend/src/NexoRuta.Commerce/Components/Features/Envios/Pages/ImportarEnvios.razor#L1); [`backend/tests/NexoRuta.IntegrationTests/Envios/ShipmentCsvImportHttpTests.cs:24`](../../../backend/tests/NexoRuta.IntegrationTests/Envios/ShipmentCsvImportHttpTests.cs#L24).

<a id="cu08"></a>
### CU-08 — Bultos

**Fuente:** CU obligatorios!A11:I11 (fila 11). **Modulo:** M02. **Actor:** Comercio. **Responsable:** sin asignacion individual (derivado de Modulos, no asignacion individual de esta fila).

> Registrar uno o más bultos por envío, con identificación, peso y dimensiones.

**Implementacion:** Completa. **Verificacion:** No verificado. **Prioridad:** P2.

- Existe: Alta admite lista de bultos con codigo, peso/dimensiones; dominio y etiquetas usan identidad persistida.
- Falta / limite: Sin alta normal ni escaneo Android por este worker.
- Siguiente accion y receta no ejecutada: Admitir envio de tres bultos, reabrir y comprobar codigos/medidas.
- Evidencia: [`backend/src/NexoRuta.Domain/Envios/Bulto.cs:3`](../../../backend/src/NexoRuta.Domain/Envios/Bulto.cs#L3); [`backend/src/NexoRuta.Application/Envios/UseCases/CrearEnvioUseCase.cs:94`](../../../backend/src/NexoRuta.Application/Envios/UseCases/CrearEnvioUseCase.cs#L94); [`frontend/src/NexoRuta.Commerce/Components/Features/Envios/Pages/CrearEnvio.razor:1`](../../../frontend/src/NexoRuta.Commerce/Components/Features/Envios/Pages/CrearEnvio.razor#L1); [`backend/tests/NexoRuta.UnitTests/Envios/CrearEnvioUseCaseTests.cs:14`](../../../backend/tests/NexoRuta.UnitTests/Envios/CrearEnvioUseCaseTests.cs#L14).

<a id="cu09"></a>
### CU-09 — Cálculo de tarifa

**Fuente:** CU obligatorios!A12:I12 (fila 12). **Modulo:** M02. **Actor:** Comercio. **Responsable:** sin asignacion individual (derivado de Modulos, no asignacion individual de esta fila).

> Calcular la tarifa automáticamente al alta según el cuadro vigente.

**Implementacion:** Completa. **Verificacion:** No verificado. **Prioridad:** P2.

- Existe: Admision calcula/persiste snapshot tarifario; cotizacion e historial REST/Commerce.
- Falta / limite: No se comparo admision real con cuadro vigente.
- Siguiente accion y receta no ejecutada: Publicar tarifa, admitir envio y contrastar importe/version almacenados.
- Evidencia: [`backend/src/NexoRuta.Infrastructure/Envios/Repositories/EfEnviosRepository.cs:85`](../../../backend/src/NexoRuta.Infrastructure/Envios/Repositories/EfEnviosRepository.cs#L85); [`backend/src/NexoRuta.Infrastructure/Envios/Repositories/TarifasAdmision.cs:37`](../../../backend/src/NexoRuta.Infrastructure/Envios/Repositories/TarifasAdmision.cs#L37); [`backend/tests/NexoRuta.IntegrationTests/Envios/TarifaAdmisionHttpTests.cs:11`](../../../backend/tests/NexoRuta.IntegrationTests/Envios/TarifaAdmisionHttpTests.cs#L11).

<a id="cu10"></a>
### CU-10 — Recepción en depósito

**Fuente:** CU obligatorios!A13:I13 (fila 13). **Modulo:** M02. **Actor:** Operario de depósito. **Responsable:** sin asignacion individual (derivado de Modulos, no asignacion individual de esta fila).

> Escanear y cotejar bultos contra lo declarado; registrar discrepancias.

**Implementacion:** Completa. **Verificacion:** No verificado. **Prioridad:** P2.

- Existe: Escaneo/entrada codigo o UUID, cotejo de medidas, discrepancia con observacion e historia; ingreso operativo cuando todos conformes.
- Falta / limite: Escaner real y circuito de deposito no ejecutados.
- Siguiente accion y receta no ejecutada: Cotejar tres bultos, uno discrepante, luego revalidarlo sin borrar antecedentes.
- Evidencia: [`backend/src/NexoRuta.Infrastructure/Reparto/EfRutasRepository.Recepcion.cs:60`](../../../backend/src/NexoRuta.Infrastructure/Reparto/EfRutasRepository.Recepcion.cs#L60); [`frontend/src/NexoRuta.Backoffice/Pages/Deposito/_CotejoRecepcion.cshtml:6`](../../../frontend/src/NexoRuta.Backoffice/Pages/Deposito/_CotejoRecepcion.cshtml#L6); [`backend/tests/NexoRuta.IntegrationTests/Reparto/RecepcionDepositoHttpTests.cs:44`](../../../backend/tests/NexoRuta.IntegrationTests/Reparto/RecepcionDepositoHttpTests.cs#L44).

<a id="cu11"></a>
### CU-11 — Estado del envío

**Fuente:** CU obligatorios!A14:I14 (fila 14). **Modulo:** M02. **Actor:** Sistema. **Responsable:** sin asignacion individual (derivado de Modulos, no asignacion individual de esta fila).

> Aplicar máquina de estados explícita y transiciones declarativas verificables.

**Implementacion:** Completa. **Verificacion:** No verificado. **Prioridad:** P2.

- Existe: Matrices declarativas de envio/bulto en dominio y protecciones SQL.
- Falta / limite: Matrices y triggers PostgreSQL no ejecutados por este worker.
- Siguiente accion y receta no ejecutada: Ejecutar matrices dominio/SQL y ciclo normal con transicion rechazada sin efectos.
- Evidencia: [`backend/src/NexoRuta.Domain/Envios/TransicionesEstadoEnvio.cs:7`](../../../backend/src/NexoRuta.Domain/Envios/TransicionesEstadoEnvio.cs#L7); [`backend/src/NexoRuta.Domain/Envios/ResultadoBulto.cs:5`](../../../backend/src/NexoRuta.Domain/Envios/ResultadoBulto.cs#L5); [`backend/tests/NexoRuta.UnitTests/Envios/EnvioStateMachineTests.cs:5`](../../../backend/tests/NexoRuta.UnitTests/Envios/EnvioStateMachineTests.cs#L5).

<a id="cu12"></a>
### CU-12 — Eventos del envío

**Fuente:** CU obligatorios!A15:I15 (fila 15). **Modulo:** M02. **Actor:** Sistema. **Responsable:** sin asignacion individual (derivado de Modulos, no asignacion individual de esta fila).

> Guardar historial completo e inmutable con fecha, origen, responsable y ubicación cuando corresponda.

**Implementacion:** Completa. **Verificacion:** No verificado. **Prioridad:** P2.

- Existe: Historia canonica inmutable; operaciones guardan actor, origen, tiempo y GPS cuando aplica.
- Falta / limite: No se ejecuto rechazo de mutacion ni traza del ciclo actual.
- Siguiente accion y receta no ejecutada: Admitir/recibir/entregar, consultar eventos e intentar alterar uno en base sintetica.
- Evidencia: [`backend/src/NexoRuta.Infrastructure/Envios/EnvioEvento.cs:3`](../../../backend/src/NexoRuta.Infrastructure/Envios/EnvioEvento.cs#L3); [`backend/src/NexoRuta.Infrastructure/Persistence/Migrations/20261025222429_AddCanonicalShipmentHistory.cs:187`](../../../backend/src/NexoRuta.Infrastructure/Persistence/Migrations/20261025222429_AddCanonicalShipmentHistory.cs#L187); [`backend/src/NexoRuta.Infrastructure/Reparto/EfOperacionesRepartoRepository.cs:56`](../../../backend/src/NexoRuta.Infrastructure/Reparto/EfOperacionesRepartoRepository.cs#L56); [`backend/tests/NexoRuta.IntegrationTests/Envios/EnvioEventsHttpTests.cs:15`](../../../backend/tests/NexoRuta.IntegrationTests/Envios/EnvioEventsHttpTests.cs#L15).

<a id="cu13"></a>
### CU-13 — Armar rutas

**Fuente:** CU obligatorios!A16:I16 (fila 16). **Modulo:** M03. **Actor:** Despachador. **Responsable:** Nacho (derivado de Modulos, no asignacion individual de esta fila).

> Asignar envíos a repartidor y vehículo en una hoja de ruta.

**Implementacion:** Completa. **Verificacion:** No verificado. **Prioridad:** P2.

- Existe: Hoja asigna envios a repartidor/vehiculo y snapshot de bultos.
- Falta / limite: Circuito UI/API no ejecutado aqui.
- Siguiente accion y receta no ejecutada: Planificar hoja de dos envios con repartidor y vehiculo.
- Evidencia: [`backend/src/NexoRuta.Infrastructure/Reparto/EfRutasRepository.cs:30`](../../../backend/src/NexoRuta.Infrastructure/Reparto/EfRutasRepository.cs#L30); [`frontend/src/NexoRuta.Backoffice/Pages/Rutas/Planificar.cshtml:1`](../../../frontend/src/NexoRuta.Backoffice/Pages/Rutas/Planificar.cshtml#L1); [`backend/tests/NexoRuta.IntegrationTests/Reparto/RutasHttpTests.cs:441`](../../../backend/tests/NexoRuta.IntegrationTests/Reparto/RutasHttpTests.cs#L441).

<a id="cu14"></a>
### CU-14 — Validar restricciones

**Fuente:** CU obligatorios!A17:I17 (fila 17). **Modulo:** M03. **Actor:** Despachador. **Responsable:** Nacho (derivado de Modulos, no asignacion individual de esta fila).

> Validar máximo de paradas, peso, volumen y compatibilidad de franjas.

**Implementacion:** Completa. **Verificacion:** No verificado. **Prioridad:** P2.

- Existe: Limite de paradas, capacidad por tramo y franjas historicas incluido servicio.
- Falta / limite: Falta ejecucion funcional actual de aceptacion/rechazo.
- Siguiente accion y receta no ejecutada: Planificar dos paradas dentro de capacidad/franja, luego superar un limite.
- Evidencia: [`backend/src/NexoRuta.Infrastructure/Reparto/EfRutasRepository.cs:38`](../../../backend/src/NexoRuta.Infrastructure/Reparto/EfRutasRepository.cs#L38); [`backend/src/NexoRuta.Domain/Reparto/CapacidadCarga.cs:8`](../../../backend/src/NexoRuta.Domain/Reparto/CapacidadCarga.cs#L8); [`backend/src/NexoRuta.Infrastructure/Reparto/RestriccionesTemporales.cs:10`](../../../backend/src/NexoRuta.Infrastructure/Reparto/RestriccionesTemporales.cs#L10); [`backend/tests/NexoRuta.IntegrationTests/Reparto/RutasHttpTests.cs:556`](../../../backend/tests/NexoRuta.IntegrationTests/Reparto/RutasHttpTests.cs#L556).

<a id="cu15"></a>
### CU-15 — Evitar doble asignación

**Fuente:** CU obligatorios!A18:I18 (fila 18). **Modulo:** M03. **Actor:** Despachador. **Responsable:** Nacho (derivado de Modulos, no asignacion individual de esta fila).

> Impedir que dos despachadores asignen simultáneamente el mismo envío a rutas distintas.

**Implementacion:** Completa. **Verificacion:** No verificado. **Prioridad:** P2.

- Existe: Bloqueo por operador y comprobacion de parada activa impiden asignacion duplicada.
- Falta / limite: Concurrencia inspeccionada, no demostrada en esta ejecucion.
- Siguiente accion y receta no ejecutada: Enviar dos planificaciones simultaneas del mismo envio y comprobar una asignacion.
- Evidencia: [`backend/src/NexoRuta.Infrastructure/Reparto/EfRutasRepository.cs:35`](../../../backend/src/NexoRuta.Infrastructure/Reparto/EfRutasRepository.cs#L35); [`backend/src/NexoRuta.Infrastructure/Reparto/EfRutasRepository.cs:73`](../../../backend/src/NexoRuta.Infrastructure/Reparto/EfRutasRepository.cs#L73); [`backend/tests/NexoRuta.IntegrationTests/Reparto/RutasHttpTests.cs:580`](../../../backend/tests/NexoRuta.IntegrationTests/Reparto/RutasHttpTests.cs#L580).

<a id="cu16"></a>
### CU-16 — Ordenar paradas

**Fuente:** CU obligatorios!A19:I19 (fila 19). **Modulo:** M03. **Actor:** Despachador. **Responsable:** Nacho (derivado de Modulos, no asignacion individual de esta fila).

> Ordenar paradas con criterio razonable y documentado; no se exige optimización.

**Implementacion:** Parcial. **Verificacion:** No verificado. **Prioridad:** P1.

- Existe: Orden manual explicito preservado; estimacion vial respeta orden, no optimiza.
- Falta / limite: Entrada manual y test no acreditan por si solos un criterio razonable documentado.
- Siguiente accion y receta no ejecutada: Documentar criterio operativo sencillo y demostrarlo con tres paradas; no activar OPT12 por defecto.
- Evidencia: [`frontend/src/NexoRuta.Backoffice/Pages/Rutas/Planificar.cshtml:117`](../../../frontend/src/NexoRuta.Backoffice/Pages/Rutas/Planificar.cshtml#L117); [`backend/src/NexoRuta.Infrastructure/Reparto/EfRutasRepository.cs:251`](../../../backend/src/NexoRuta.Infrastructure/Reparto/EfRutasRepository.cs#L251); [`backend/tests/NexoRuta.IntegrationTests/Reparto/RutasHttpTests.cs:496`](../../../backend/tests/NexoRuta.IntegrationTests/Reparto/RutasHttpTests.cs#L496).

<a id="cu17"></a>
### CU-17 — Despachar ruta

**Fuente:** CU obligatorios!A20:I20 (fila 20). **Modulo:** M03. **Actor:** Despachador. **Responsable:** Nacho (derivado de Modulos, no asignacion individual de esta fila).

> Publicar la ruta despachada para la aplicación del repartidor.

**Implementacion:** Completa. **Verificacion:** No verificado. **Prioridad:** P2.

- Existe: Despacho versionado; rutas propias excluyen planificadas/canceladas y cliente obtiene hoja asignada.
- Falta / limite: Publicacion/descarga E2E no ejecutada aqui.
- Siguiente accion y receta no ejecutada: Despachar y comprobar que solo repartidor asignado puede descargar.
- Evidencia: [`backend/src/NexoRuta.Infrastructure/Reparto/EfRutasRepository.cs:105`](../../../backend/src/NexoRuta.Infrastructure/Reparto/EfRutasRepository.cs#L105); [`backend/src/NexoRuta.Infrastructure/Reparto/EfRutasRepository.cs:22`](../../../backend/src/NexoRuta.Infrastructure/Reparto/EfRutasRepository.cs#L22); [`backend/src/NexoRuta.Api/Features/Reparto/Controllers/RutasController.cs:57`](../../../backend/src/NexoRuta.Api/Features/Reparto/Controllers/RutasController.cs#L57); [`backend/tests/NexoRuta.IntegrationTests/Reparto/RutasHttpTests.cs:441`](../../../backend/tests/NexoRuta.IntegrationTests/Reparto/RutasHttpTests.cs#L441).

<a id="cu18"></a>
### CU-18 — Descargar ruta

**Fuente:** CU obligatorios!A21:I21 (fila 21). **Modulo:** M04. **Actor:** Repartidor. **Responsable:** Nacho (derivado de Modulos, no asignacion individual de esta fila).

> Descargar hoja de ruta del día para uso sin conectividad.

**Implementacion:** Completa. **Verificacion:** Bloqueado. **Prioridad:** P2.

- Existe: Servicio de hojas y SQLite persisten rutas para abrir sin red.
- Falta / limite: Android offline pendiente de evidencia del padre.
- Siguiente accion y receta no ejecutada: Descargar hoja, reiniciar sin red y comprobar paradas.
- Evidencia: [`mobile/src/NexoRuta.Mobile.Application/ServicioHojasRuta.cs:8`](../../../mobile/src/NexoRuta.Mobile.Application/ServicioHojasRuta.cs#L8); [`mobile/src/NexoRuta.Mobile.Storage/RepositorioJornadasSqlite.HojasRemotas.cs:4`](../../../mobile/src/NexoRuta.Mobile.Storage/RepositorioJornadasSqlite.HojasRemotas.cs#L4); [`mobile/tests/NexoRuta.Mobile.Application.Tests/ServicioHojasRutaTests.cs:10`](../../../mobile/tests/NexoRuta.Mobile.Application.Tests/ServicioHojasRutaTests.cs#L10).

<a id="cu19"></a>
### CU-19 — Escanear carga

**Fuente:** CU obligatorios!A22:I22 (fila 22). **Modulo:** M04. **Actor:** Repartidor. **Responsable:** Nacho (derivado de Modulos, no asignacion individual de esta fila).

> Escanear bultos al cargar y alertar faltantes o sobrantes.

**Implementacion:** Completa. **Verificacion:** Bloqueado. **Prioridad:** P2.

- Existe: Evaluacion de carga por bulto alerta faltantes/sobrantes; escaner usa identificacion.
- Falta / limite: Lector/camara real no ejecutado.
- Siguiente accion y receta no ejecutada: Escanear carga de dos bultos dejando uno faltante y agregando uno ajeno.
- Evidencia: [`mobile/src/NexoRuta.Mobile.Application/EvaluacionCargaSalida.cs:5`](../../../mobile/src/NexoRuta.Mobile.Application/EvaluacionCargaSalida.cs#L5); [`mobile/src/NexoRuta.Mobile/Captura/EscanerPage.cs:4`](../../../mobile/src/NexoRuta.Mobile/Captura/EscanerPage.cs#L4); [`mobile/tests/NexoRuta.Mobile.Application.Tests/EvaluacionCargaSalidaTests.cs:6`](../../../mobile/tests/NexoRuta.Mobile.Application.Tests/EvaluacionCargaSalidaTests.cs#L6).

<a id="cu20"></a>
### CU-20 — Registrar entrega

**Fuente:** CU obligatorios!A23:I23 (fila 23). **Modulo:** M04. **Actor:** Repartidor. **Responsable:** Nacho (derivado de Modulos, no asignacion individual de esta fila).

> Capturar prueba exigida (firma, foto, nombre y documento), hora y geolocalización del dispositivo.

**Implementacion:** Completa. **Verificacion:** Bloqueado. **Prioridad:** P2.

- Existe: Formulario captura prueba configurable, tiempo/GPS; archivos cifrados y validacion de pertenencia/completitud.
- Falta / limite: Camara, firma, GPS y permisos no se ejecutaron aqui.
- Siguiente accion y receta no ejecutada: Entregar con politica nombre/documento/foto/firma y revisar prueba/hora/GPS persistidos.
- Evidencia: [`mobile/src/NexoRuta.Mobile/Presentacion/EntregaViewModel.cs:39`](../../../mobile/src/NexoRuta.Mobile/Presentacion/EntregaViewModel.cs#L39); [`backend/src/NexoRuta.Infrastructure/Reparto/EfOperacionesRepartoRepository.Ejecucion.cs:280`](../../../backend/src/NexoRuta.Infrastructure/Reparto/EfOperacionesRepartoRepository.Ejecucion.cs#L280); [`backend/tests/NexoRuta.IntegrationTests/Reparto/OperacionesRepartoHttpTests.Evidencias.cs:11`](../../../backend/tests/NexoRuta.IntegrationTests/Reparto/OperacionesRepartoHttpTests.Evidencias.cs#L11).

<a id="cu21"></a>
### CU-21 — Registrar intento fallido

**Fuente:** CU obligatorios!A24:I24 (fila 24). **Modulo:** M04. **Actor:** Repartidor. **Responsable:** Nacho (derivado de Modulos, no asignacion individual de esta fila).

> Elegir motivo configurado y guardar evidencia.

**Implementacion:** Completa. **Verificacion:** Bloqueado. **Prioridad:** P2.

- Existe: Motivos de catalogo publicado y foto exigida se validan en intento; diario conserva evidencia.
- Falta / limite: Sin intento real Android.
- Siguiente accion y receta no ejecutada: Registrar motivo habilitado/foto offline, sincronizar y revisar intento/intervalo.
- Evidencia: [`mobile/src/NexoRuta.Mobile/Presentacion/EntregaViewModel.cs:114`](../../../mobile/src/NexoRuta.Mobile/Presentacion/EntregaViewModel.cs#L114); [`backend/src/NexoRuta.Infrastructure/Reparto/EfOperacionesRepartoRepository.Ejecucion.cs:161`](../../../backend/src/NexoRuta.Infrastructure/Reparto/EfOperacionesRepartoRepository.Ejecucion.cs#L161); [`mobile/tests/NexoRuta.Mobile.Core.Tests/ReglasEnvioTests.cs:6`](../../../mobile/tests/NexoRuta.Mobile.Core.Tests/ReglasEnvioTests.cs#L6).

<a id="cu22"></a>
### CU-22 — Devolución y rendición

**Fuente:** CU obligatorios!A25:I25 (fila 25). **Modulo:** M04. **Actor:** Repartidor / depósito. **Responsable:** Nacho (derivado de Modulos, no asignacion individual de esta fila).

> Gestionar devolución y rendición al regreso al depósito.

**Implementacion:** Completa. **Verificacion:** Bloqueado. **Prioridad:** P2.

- Existe: Rendicion separa custodia, retorno, recepcion fisica y entrega al comercio; cierre no inventa recepcion.
- Falta / limite: Sin recorrido normal completo de retorno.
- Siguiente accion y receta no ejecutada: Rendir no entregado, recibir en deposito y confirmar devolucion al comercio.
- Evidencia: [`mobile/src/NexoRuta.Mobile/Captura/RendicionPage.cs:3`](../../../mobile/src/NexoRuta.Mobile/Captura/RendicionPage.cs#L3); [`backend/src/NexoRuta.Infrastructure/Reparto/EfRutasRepository.Recepcion.cs:11`](../../../backend/src/NexoRuta.Infrastructure/Reparto/EfRutasRepository.Recepcion.cs#L11); [`mobile/tests/NexoRuta.Mobile.Core.Tests/IncidenciasCierreTests.cs:6`](../../../mobile/tests/NexoRuta.Mobile.Core.Tests/IncidenciasCierreTests.cs#L6).

<a id="cu23"></a>
### CU-23 — Posición del vehículo

**Fuente:** CU obligatorios!A26:I26 (fila 26). **Modulo:** M04. **Actor:** Repartidor / despachador. **Responsable:** Nacho (derivado de Modulos, no asignacion individual de esta fila).

> Seguir la ubicación del vehículo durante la jornada.

**Implementacion:** Parcial. **Verificacion:** Bloqueado. **Prioridad:** P1.

- Existe: Servicio Android foreground captura posicion; diario/proyeccion eligen GPS admisible para recorrido.
- Falta / limite: Posicion no aparece en tablero vivo del despachador; segundo plano/bateria real no comprobados.
- Siguiente accion y receta no ejecutada: Demostrar GPS en segundo plano y presentar posicion con antiguedad al despachador.
- Evidencia: [`mobile/src/NexoRuta.Mobile/Ubicacion/TrackingJornada.cs:14`](../../../mobile/src/NexoRuta.Mobile/Ubicacion/TrackingJornada.cs#L14); [`backend/src/NexoRuta.Infrastructure/Reparto/EfRutasRepository.Recorrido.cs:40`](../../../backend/src/NexoRuta.Infrastructure/Reparto/EfRutasRepository.Recorrido.cs#L40); [`mobile/tests/NexoRuta.Mobile.Application.Tests/RegistroUbicacionTests.cs:10`](../../../mobile/tests/NexoRuta.Mobile.Application.Tests/RegistroUbicacionTests.cs#L10).

<a id="cu24"></a>
### CU-24 — Sincronización diferida

**Fuente:** CU obligatorios!A27:I27 (fila 27). **Modulo:** M04. **Actor:** Repartidor / sistema. **Responsable:** Nacho (derivado de Modulos, no asignacion individual de esta fila).

> Operar sin red y sincronizar con política explícita para estados incompatibles.

**Implementacion:** Completa. **Verificacion:** Bloqueado. **Prioridad:** P2.

- Existe: Diario SQLite, archivos cifrados, sobres congelados/idempotencia; servidor registra conflictos sin duplicar efectos.
- Falta / limite: Sin desconexion/reinicio/sync ejecutados aqui.
- Siguiente accion y receta no ejecutada: Sin red registrar operaciones, reiniciar, sincronizar y provocar conflicto de version por bulto.
- Evidencia: [`mobile/src/NexoRuta.Mobile.Application/SincronizadorJornada.cs:10`](../../../mobile/src/NexoRuta.Mobile.Application/SincronizadorJornada.cs#L10); [`mobile/src/NexoRuta.Mobile.Storage/RepositorioJornadasSqlite.Sincronizacion.cs:4`](../../../mobile/src/NexoRuta.Mobile.Storage/RepositorioJornadasSqlite.Sincronizacion.cs#L4); [`backend/src/NexoRuta.Infrastructure/Reparto/EfOperacionesRepartoRepository.cs:22`](../../../backend/src/NexoRuta.Infrastructure/Reparto/EfOperacionesRepartoRepository.cs#L22); [`mobile/tests/NexoRuta.Mobile.Application.Tests/SincronizadorJornadaTests.cs:11`](../../../mobile/tests/NexoRuta.Mobile.Application.Tests/SincronizadorJornadaTests.cs#L11).

<a id="cu25"></a>
### CU-25 — Seguimiento público

**Fuente:** CU obligatorios!A28:I28 (fila 28). **Modulo:** M05. **Actor:** Destinatario. **Responsable:** José Hernández (derivado de Modulos, no asignacion individual de esta fila).

> Consultar por enlace sin autenticación, sin datos personales de terceros ni IDs internos.

**Implementacion:** Completa. **Verificacion:** No verificado. **Prioridad:** P2.

- Existe: Token opaco, SQL autorizado por capability, DTO publico sin IDs/evidencia privada; conteo por bulto.
- Falta / limite: No hubo peticiones anonimas cruzadas ejecutadas aqui.
- Siguiente accion y receta no ejecutada: Consultar enlace valido/invalido sin login y comprobar ausencia de IDs/datos ajenos.
- Evidencia: [`backend/src/NexoRuta.Application/Seguimiento/UseCases/ConsultarSeguimientoPublicoUseCase.cs:30`](../../../backend/src/NexoRuta.Application/Seguimiento/UseCases/ConsultarSeguimientoPublicoUseCase.cs#L30); [`backend/src/NexoRuta.Api/Features/Seguimiento/Contracts/SeguimientoEstadoResponse.cs:5`](../../../backend/src/NexoRuta.Api/Features/Seguimiento/Contracts/SeguimientoEstadoResponse.cs#L5); [`backend/src/NexoRuta.Infrastructure/Seguimiento/Repositories/EfEnlacesSeguimientoRepository.cs:53`](../../../backend/src/NexoRuta.Infrastructure/Seguimiento/Repositories/EfEnlacesSeguimientoRepository.cs#L53); [`backend/tests/NexoRuta.UnitTests/Seguimiento/ConsultarSeguimientoPublicoUseCaseTests.cs:10`](../../../backend/tests/NexoRuta.UnitTests/Seguimiento/ConsultarSeguimientoPublicoUseCaseTests.cs#L10).

<a id="cu26"></a>
### CU-26 — Reprogramación

**Fuente:** CU obligatorios!A29:I29 (fila 29). **Modulo:** M05. **Actor:** Destinatario. **Responsable:** José Hernández (derivado de Modulos, no asignacion individual de esta fila).

> Solicitar reprogramación sujeta a las reglas del operador.

**Implementacion:** Ausente. **Verificacion:** No verificado. **Prioridad:** P1.

- Existe: Backoffice reprograma intento fallido con permiso envios.gestionar.
- Falta / limite: No existe solicitud del destinatario en contrato/controlador publico ni Tracking; cancelacion no sustituye reprogramacion.
- Siguiente accion y receta no ejecutada: Agregar solicitud por enlace con validacion de intentos/plazos y tratamiento operativo.
- Evidencia: [`backend/src/NexoRuta.Api/Features/Reparto/Controllers/RutasController.cs:77`](../../../backend/src/NexoRuta.Api/Features/Reparto/Controllers/RutasController.cs#L77); [`backend/src/NexoRuta.Api/Features/Seguimiento/Controllers/SeguimientoPublicoController.cs:17`](../../../backend/src/NexoRuta.Api/Features/Seguimiento/Controllers/SeguimientoPublicoController.cs#L17); [`frontend/src/NexoRuta.Tracking/Components/Pages/Seguimiento.razor:102`](../../../frontend/src/NexoRuta.Tracking/Components/Pages/Seguimiento.razor#L102).

<a id="cu27"></a>
### CU-27 — Avisos al destinatario

**Fuente:** CU obligatorios!A30:I30 (fila 30). **Modulo:** M05. **Actor:** Sistema. **Responsable:** José Hernández (derivado de Modulos, no asignacion individual de esta fila).

> Notificar automáticamente los cambios de estado relevantes.

**Implementacion:** Ausente. **Verificacion:** No verificado. **Prioridad:** P1.

- Existe: Outbox genera enlace de seguimiento; SMTP sirve recuperacion/cancelacion.
- Falta / limite: Generar enlace no notifica cada cambio relevante; no se encontro consumidor/correo de estado al destinatario.
- Siguiente accion y receta no ejecutada: Emitir notificaciones de estados relevantes desde cambios persistidos; demostrar entrega/reintento.
- Evidencia: [`backend/src/NexoRuta.Infrastructure/Seguimiento/Processing/ProcesarGeneracionSeguimiento.cs:75`](../../../backend/src/NexoRuta.Infrastructure/Seguimiento/Processing/ProcesarGeneracionSeguimiento.cs#L75); [`backend/src/NexoRuta.Worker/Messaging/OutboxHandlerRegistry.cs:37`](../../../backend/src/NexoRuta.Worker/Messaging/OutboxHandlerRegistry.cs#L37); [`backend/src/NexoRuta.Worker/Program.cs:35`](../../../backend/src/NexoRuta.Worker/Program.cs#L35).

<a id="cu28"></a>
### CU-28 — Avisos a comercios

**Fuente:** CU obligatorios!A31:I31 (fila 31). **Modulo:** M05. **Actor:** Sistema / comercio. **Responsable:** José Hernández (derivado de Modulos, no asignacion individual de esta fila).

> Enviar HTTP saliente ante cambios de estado, con garantías de entrega del apartado 6.9.

**Implementacion:** Ausente. **Verificacion:** No verificado. **Prioridad:** P1.

- Existe: Kafka bulto/operacion alimenta bandeja interna Commerce.
- Falta / limite: Bandeja no es HTTP saliente firmado: faltan suscripcion por evento, entrega HTTP, firma, historial/reenvio/receptor.
- Siguiente accion y receta no ejecutada: Implementar suscripcion HTTP firmada sobre outbox con reintentos/fallidos y receptor controlado.
- Evidencia: [`backend/src/NexoRuta.Api/Features/Envios/Controllers/AvisosComercioController.cs:9`](../../../backend/src/NexoRuta.Api/Features/Envios/Controllers/AvisosComercioController.cs#L9); [`backend/src/NexoRuta.Infrastructure/Notificaciones/EfAvisosComercioRepository.cs:10`](../../../backend/src/NexoRuta.Infrastructure/Notificaciones/EfAvisosComercioRepository.cs#L10); [`backend/src/NexoRuta.Worker/Messaging/CommerceNoticeConsumer.cs:8`](../../../backend/src/NexoRuta.Worker/Messaging/CommerceNoticeConsumer.cs#L8).

<a id="cu29"></a>
### CU-29 — Tablero en vivo

**Fuente:** CU obligatorios!A32:I32 (fila 32). **Modulo:** M06. **Actor:** Despachador. **Responsable:** José Hernández (derivado de Modulos, no asignacion individual de esta fila).

> Mostrar flota y envíos en riesgo de incumplir su ventana.

**Implementacion:** Parcial. **Verificacion:** No verificado. **Prioridad:** P1.

- Existe: Flota muestra ocupacion/retorno y detalle de ruta tiene estimaciones.
- Falta / limite: Razor bajo consulta no es tablero vivo de flota y envios en riesgo; no se encontro hub SignalR.
- Siguiente accion y receta no ejecutada: Construir proyeccion de riesgo por compromiso y actualizacion autenticada/aislada del tablero.
- Evidencia: [`frontend/src/NexoRuta.Backoffice/Pages/Rutas/_Operacion.cshtml:21`](../../../frontend/src/NexoRuta.Backoffice/Pages/Rutas/_Operacion.cshtml#L21); [`frontend/src/NexoRuta.Backoffice/Pages/Rutas/_Flota.cshtml:1`](../../../frontend/src/NexoRuta.Backoffice/Pages/Rutas/_Flota.cshtml#L1); [`backend/src/NexoRuta.Infrastructure/Reparto/EfRutasRepository.Recorrido.cs:10`](../../../backend/src/NexoRuta.Infrastructure/Reparto/EfRutasRepository.Recorrido.cs#L10).

<a id="cu30"></a>
### CU-30 — Reportes y liquidación

**Fuente:** CU obligatorios!A33:I33 (fila 33). **Modulo:** M06. **Actor:** Operador / comercio. **Responsable:** José Hernández (derivado de Modulos, no asignacion individual de esta fila).

> Reportar cumplimiento por zona, repartidor y comercio; motivos, volumen y liquidación.

**Implementacion:** Parcial. **Verificacion:** No verificado. **Prioridad:** P1.

- Existe: Reporte REST/Razor/CSV agrega operaciones/bultos/entregados/importe por tipo y estado.
- Falta / limite: Sin cumplimiento por zona/repartidor/comercio ni motivos ni liquidacion; suma de tarifa no es liquidacion contable.
- Siguiente accion y receta no ejecutada: Agregar dimensiones e indicadores desde historial/cargos y liquidacion por comercio trazable.
- Evidencia: [`backend/src/NexoRuta.Api/Features/Envios/Controllers/ReporteOperacionesController.cs:13`](../../../backend/src/NexoRuta.Api/Features/Envios/Controllers/ReporteOperacionesController.cs#L13); [`frontend/src/NexoRuta.Backoffice/Pages/ReporteOperaciones.cshtml:8`](../../../frontend/src/NexoRuta.Backoffice/Pages/ReporteOperaciones.cshtml#L8).

<a id="ap01"></a>
### AP-01 — Gestión de incidencias

**Fuente:** Alcance aplicaciones!A4:G4 (fila 4). **Modulo:** M06. **Actor:** no especificado en fuente. **Responsable:** José Hernández (derivado de Modulos, no asignacion individual de esta fila).

> Registrar y resolver incidencias desde el backoffice.

**Implementacion:** Parcial. **Verificacion:** No verificado. **Prioridad:** P1.

- Existe: Incidencias de cierre, conciliacion, discrepancias y confirmacion de extravio.
- Falta / limite: No se encontro ciclo general de registro/resolucion de incidencias Backoffice.
- Siguiente accion y receta no ejecutada: Demostrar registrar/asignar/resolver incidencia enlazada a envio.
- Evidencia: [`frontend/src/NexoRuta.Backoffice/Pages/Rutas/_Detalle.cshtml:54`](../../../frontend/src/NexoRuta.Backoffice/Pages/Rutas/_Detalle.cshtml#L54); [`backend/src/NexoRuta.Infrastructure/Reparto/EfRutasRepository.Extravio.cs:14`](../../../backend/src/NexoRuta.Infrastructure/Reparto/EfRutasRepository.Extravio.cs#L14); [`backend/src/NexoRuta.Infrastructure/Reparto/EfRutasRepository.Recepcion.cs:60`](../../../backend/src/NexoRuta.Infrastructure/Reparto/EfRutasRepository.Recepcion.cs#L60).

<a id="ap02"></a>
### AP-02 — Etiquetas

**Fuente:** Alcance aplicaciones!A5:G5 (fila 5). **Modulo:** M02. **Actor:** no especificado en fuente. **Responsable:** sin asignacion individual (derivado de Modulos, no asignacion individual de esta fila).

> Imprimir etiquetas de envíos desde el portal del comercio.

**Implementacion:** Completa. **Verificacion:** No verificado. **Prioridad:** P2.

- Existe: PDF de etiquetas y pagina de impresion Commerce con identidad persistida.
- Falta / limite: Impresion real no ejecutada.
- Siguiente accion y receta no ejecutada: Descargar/imprimir etiqueta propia y comprobar QR/codigo.
- Evidencia: [`backend/src/NexoRuta.Api/Features/Envios/Controllers/EnviosController.cs:227`](../../../backend/src/NexoRuta.Api/Features/Envios/Controllers/EnviosController.cs#L227); [`frontend/src/NexoRuta.Commerce/Pages/Envios/Etiquetas.cshtml:1`](../../../frontend/src/NexoRuta.Commerce/Pages/Envios/Etiquetas.cshtml#L1); [`backend/tests/NexoRuta.IntegrationTests/Envios/EtiquetasEnvioHttpTests.cs:14`](../../../backend/tests/NexoRuta.IntegrationTests/Envios/EtiquetasEnvioHttpTests.cs#L14).

<a id="ap03"></a>
### AP-03 — Consulta del comercio

**Fuente:** Alcance aplicaciones!A6:G6 (fila 6). **Modulo:** M02. **Actor:** no especificado en fuente. **Responsable:** sin asignacion individual (derivado de Modulos, no asignacion individual de esta fila).

> El comercio consulta y sigue exclusivamente sus propios envíos.

**Implementacion:** Completa. **Verificacion:** No verificado. **Prioridad:** P2.

- Existe: Consulta Commerce usa contexto validado y filtrado por organizacion/RLS.
- Falta / limite: Aislamiento de dos comercios no ejecutado aqui.
- Siguiente accion y receta no ejecutada: Con dos comercios, comprobar listado/detalle y rechazo de enlace ajeno.
- Evidencia: [`backend/src/NexoRuta.Application/Envios/UseCases/ListarEnviosUseCase.cs:13`](../../../backend/src/NexoRuta.Application/Envios/UseCases/ListarEnviosUseCase.cs#L13); [`frontend/src/NexoRuta.Commerce/Components/Features/Envios/Pages/MisEnvios.razor:1`](../../../frontend/src/NexoRuta.Commerce/Components/Features/Envios/Pages/MisEnvios.razor#L1); [`backend/tests/NexoRuta.IntegrationTests/Seguridad/RlsRestrictedHttpFlowTests.cs:15`](../../../backend/tests/NexoRuta.IntegrationTests/Seguridad/RlsRestrictedHttpFlowTests.cs#L15).

<a id="ap04"></a>
### AP-04 — Devoluciones del comercio

**Fuente:** Alcance aplicaciones!A7:G7 (fila 7). **Modulo:** M02. **Actor:** no especificado en fuente. **Responsable:** sin asignacion individual (derivado de Modulos, no asignacion individual de esta fila).

> El comercio consulta y gestiona devoluciones de sus envíos.

**Implementacion:** Parcial. **Verificacion:** No verificado. **Prioridad:** P1.

- Existe: Commerce ve estado y cancela; operador efectua devolucion fisica.
- Falta / limite: Sin circuito Commerce encontrado para gestionar devoluciones propias; retiro a domicilio es distinto.
- Siguiente accion y receta no ejecutada: Recorrer solicitud/consulta/gestion de devolucion como comercio y completar accion faltante.
- Evidencia: [`frontend/src/NexoRuta.Commerce/Components/Features/Envios/Pages/DetalleEnvio.razor:1`](../../../frontend/src/NexoRuta.Commerce/Components/Features/Envios/Pages/DetalleEnvio.razor#L1); [`backend/src/NexoRuta.Api/Features/Reparto/Controllers/RecepcionController.cs:10`](../../../backend/src/NexoRuta.Api/Features/Reparto/Controllers/RecepcionController.cs#L10); [`backend/src/NexoRuta.Api/Features/Envios/Controllers/EnviosController.cs:113`](../../../backend/src/NexoRuta.Api/Features/Envios/Controllers/EnviosController.cs#L113).

<a id="ap05"></a>
### AP-05 — Suscripción de avisos

**Fuente:** Alcance aplicaciones!A8:G8 (fila 8). **Modulo:** M05. **Actor:** no especificado en fuente. **Responsable:** José Hernández (derivado de Modulos, no asignacion individual de esta fila).

> El comercio configura los avisos automáticos a sus sistemas.

**Implementacion:** Ausente. **Verificacion:** No verificado. **Prioridad:** P1.

- Existe: Commerce tiene bandeja de avisos.
- Falta / limite: No hay formulario/API de suscripcion a sistemas externos por comercio/evento.
- Siguiente accion y receta no ejecutada: Agregar configuracion de suscripcion HTTP con validacion de destino y clave.
- Evidencia: [`frontend/src/NexoRuta.Commerce/Components/Features/Envios/Pages/Avisos.razor:1`](../../../frontend/src/NexoRuta.Commerce/Components/Features/Envios/Pages/Avisos.razor#L1); [`backend/src/NexoRuta.Api/Features/Envios/Controllers/AvisosComercioController.cs:9`](../../../backend/src/NexoRuta.Api/Features/Envios/Controllers/AvisosComercioController.cs#L9).

<a id="ap06"></a>
### AP-06 — Cuenta corriente

**Fuente:** Alcance aplicaciones!A9:G9 (fila 9). **Modulo:** M06. **Actor:** no especificado en fuente. **Responsable:** José Hernández (derivado de Modulos, no asignacion individual de esta fila).

> El comercio consulta cuenta corriente y liquidaciones.

**Implementacion:** Ausente. **Verificacion:** No verificado. **Prioridad:** P1.

- Existe: Importes existen en envio y reporte.
- Falta / limite: No hay cuenta corriente, movimientos/saldo ni liquidaciones consultables por comercio.
- Siguiente accion y receta no ejecutada: Agregar consulta de movimientos/saldo y liquidaciones a partir de cargos persistidos.
- Evidencia: [`backend/src/NexoRuta.Api/Features/Envios/Controllers/ReporteOperacionesController.cs:17`](../../../backend/src/NexoRuta.Api/Features/Envios/Controllers/ReporteOperacionesController.cs#L17); [`frontend/src/NexoRuta.Commerce/Components/Features/Envios/Pages/MisEnvios.razor:1`](../../../frontend/src/NexoRuta.Commerce/Components/Features/Envios/Pages/MisEnvios.razor#L1).

<a id="ap07"></a>
### AP-07 — Ventana estimada

**Fuente:** Alcance aplicaciones!A10:G10 (fila 10). **Modulo:** M05. **Actor:** no especificado en fuente. **Responsable:** José Hernández (derivado de Modulos, no asignacion individual de esta fila).

> El destinatario ve la ventana horaria estimada en el seguimiento público.

**Implementacion:** Ausente. **Verificacion:** No verificado. **Prioridad:** P1.

- Existe: Publico muestra estado/marca/conteos.
- Falta / limite: DTO/pantalla no exponen ventana estimada.
- Siguiente accion y receta no ejecutada: Exponer ventana estimada por token con antiguedad/indisponible.
- Evidencia: [`backend/src/NexoRuta.Api/Features/Seguimiento/Contracts/SeguimientoEstadoResponse.cs:5`](../../../backend/src/NexoRuta.Api/Features/Seguimiento/Contracts/SeguimientoEstadoResponse.cs#L5); [`frontend/src/NexoRuta.Tracking/Components/Pages/Seguimiento.razor:58`](../../../frontend/src/NexoRuta.Tracking/Components/Pages/Seguimiento.razor#L58).

<a id="ap08"></a>
### AP-08 — Navegación de ruta

**Fuente:** Alcance aplicaciones!A11:G11 (fila 11). **Modulo:** M04. **Actor:** no especificado en fuente. **Responsable:** Nacho (derivado de Modulos, no asignacion individual de esta fila).

> El repartidor navega entre las paradas de la hoja de ruta.

**Implementacion:** Completa. **Verificacion:** Bloqueado. **Prioridad:** P2.

- Existe: Lista ordenada permite abrir cada parada y volver; mapa del recorrido/destino y paquete offline complementan la navegacion.
- Falta / limite: Interaccion nativa entre lista, parada y retorno offline no observada; el requisito no exige navegacion giro-a-giro ni proveedor externo.
- Siguiente accion y receta no ejecutada: En Android autorizado abrir parada A, volver a hoja y abrir B sin red; comprobar orden/estado/mapa sin perder operaciones.
- Evidencia: [`mobile/src/NexoRuta.Mobile/HojaRutaPage.xaml.cs:46`](../../../mobile/src/NexoRuta.Mobile/HojaRutaPage.xaml.cs#L46); [`mobile/src/NexoRuta.Mobile/HojaRutaPage.xaml.cs:50`](../../../mobile/src/NexoRuta.Mobile/HojaRutaPage.xaml.cs#L50); [`mobile/src/NexoRuta.Mobile/Mapas/MapaDestinoPage.cs:42`](../../../mobile/src/NexoRuta.Mobile/Mapas/MapaDestinoPage.cs#L42).

<a id="ap09"></a>
### AP-09 — Cierre diario

**Fuente:** Alcance aplicaciones!A12:G12 (fila 12). **Modulo:** M06. **Actor:** no especificado en fuente. **Responsable:** José Hernández (derivado de Modulos, no asignacion individual de esta fila).

> El worker ejecuta el cierre diario de la operación.

**Implementacion:** Ausente. **Verificacion:** No verificado. **Prioridad:** P1.

- Existe: Worker procesa outbox/vencimientos/push/consumidores.
- Falta / limite: No se registro servicio de cierre diario; FinJornada movil cierra una hoja manualmente.
- Siguiente accion y receta no ejecutada: Agregar job diario idempotente por operador/fecha y demostrar dos instancias sin duplicar.
- Evidencia: [`backend/src/NexoRuta.Worker/Program.cs:35`](../../../backend/src/NexoRuta.Worker/Program.cs#L35); [`backend/src/NexoRuta.Worker/Program.cs:43`](../../../backend/src/NexoRuta.Worker/Program.cs#L43); [`backend/src/NexoRuta.Infrastructure/Reparto/EfOperacionesRepartoRepository.cs:20`](../../../backend/src/NexoRuta.Infrastructure/Reparto/EfOperacionesRepartoRepository.cs#L20).

<a id="d01"></a>
### D01 — (dependencia sin titulo original)

**Fuente:** Dependencias!A4:I4 (fila 4). **Modulo:** M02. **Actor:** no especificado en fuente. **Responsable:** sin asignacion individual (derivado de Modulos, no asignacion individual de esta fila).

> El alta identifica comercio y operador; el mismo comercio puede operar con varios operadores.

**Implementacion:** Completa. **Verificacion:** No verificado. **Prioridad:** P2.

- Existe: Origen de envio conserva comercio y operador; seleccion no exige relacion comercial previa.
- Falta / limite: No se ejecuto la dependencia completa.
- Siguiente accion y receta no ejecutada: Con dos operadores, admitir envios del mismo comercio y comprobar aislamiento.
- Evidencia: [`backend/src/NexoRuta.Api/Features/Envios/Controllers/EnviosController.cs:180`](../../../backend/src/NexoRuta.Api/Features/Envios/Controllers/EnviosController.cs#L180); [`backend/src/NexoRuta.Infrastructure/Envios/Repositories/EfEnviosRepository.cs:44`](../../../backend/src/NexoRuta.Infrastructure/Envios/Repositories/EfEnviosRepository.cs#L44); [`frontend/src/NexoRuta.Commerce/Components/Features/Envios/Pages/ImportarEnvios.razor:1`](../../../frontend/src/NexoRuta.Commerce/Components/Features/Envios/Pages/ImportarEnvios.razor#L1); [`backend/tests/NexoRuta.IntegrationTests/Envios/ShipmentCsvImportHttpTests.cs:24`](../../../backend/tests/NexoRuta.IntegrationTests/Envios/ShipmentCsvImportHttpTests.cs#L24).

<a id="d02"></a>
### D02 — (dependencia sin titulo original)

**Fuente:** Dependencias!A5:I5 (fila 5). **Modulo:** M02. **Actor:** no especificado en fuente. **Responsable:** sin asignacion individual (derivado de Modulos, no asignacion individual de esta fila).

> El precio usa la versión tarifaria vigente al alta.

**Implementacion:** Completa. **Verificacion:** No verificado. **Prioridad:** P2.

- Existe: Cotizacion/admision conserva version tarifaria y cargo original.
- Falta / limite: No se ejecuto la dependencia completa.
- Siguiente accion y receta no ejecutada: Cambiar tarifa luego de admitir y contrastar cargo anterior.
- Evidencia: [`backend/src/NexoRuta.Infrastructure/Envios/Repositories/EfEnviosRepository.cs:85`](../../../backend/src/NexoRuta.Infrastructure/Envios/Repositories/EfEnviosRepository.cs#L85); [`backend/src/NexoRuta.Infrastructure/Envios/Repositories/TarifasAdmision.cs:37`](../../../backend/src/NexoRuta.Infrastructure/Envios/Repositories/TarifasAdmision.cs#L37); [`backend/tests/NexoRuta.IntegrationTests/Envios/TarifaAdmisionHttpTests.cs:11`](../../../backend/tests/NexoRuta.IntegrationTests/Envios/TarifaAdmisionHttpTests.cs#L11).

<a id="d03"></a>
### D03 — (dependencia sin titulo original)

**Fuente:** Dependencias!A6:I6 (fila 6). **Modulo:** M02. **Actor:** no especificado en fuente. **Responsable:** sin asignacion individual (derivado de Modulos, no asignacion individual de esta fila).

> Estados de intento, devolución y plazos aplican reglas del operador.

**Implementacion:** Completa. **Verificacion:** No verificado. **Prioridad:** P2.

- Existe: Intentos, devoluciones y vencimientos consultan publicacion del envio.
- Falta / limite: No se ejecuto la dependencia completa.
- Siguiente accion y receta no ejecutada: Ejecutar intento/devolucion con version original tras cambio de reglas.
- Evidencia: [`backend/src/NexoRuta.Domain/ReglasOperativas/VersionReglasOperativas.cs:3`](../../../backend/src/NexoRuta.Domain/ReglasOperativas/VersionReglasOperativas.cs#L3); [`backend/src/NexoRuta.Api/Features/ReglasOperativas/Controllers/ReglasOperativasController.cs:26`](../../../backend/src/NexoRuta.Api/Features/ReglasOperativas/Controllers/ReglasOperativasController.cs#L26); [`backend/src/NexoRuta.Infrastructure/Envios/Repositories/EfEnviosRepository.cs:69`](../../../backend/src/NexoRuta.Infrastructure/Envios/Repositories/EfEnviosRepository.cs#L69); [`backend/tests/NexoRuta.IntegrationTests/ReglasOperativas/ReglasOperativasHttpTests.cs:15`](../../../backend/tests/NexoRuta.IntegrationTests/ReglasOperativas/ReglasOperativasHttpTests.cs#L15).

<a id="d04"></a>
### D04 — (dependencia sin titulo original)

**Fuente:** Dependencias!A7:I7 (fila 7). **Modulo:** M03. **Actor:** no especificado en fuente. **Responsable:** Nacho (derivado de Modulos, no asignacion individual de esta fila).

> La planificación necesita zona y ventana comprometida.

**Implementacion:** Completa. **Verificacion:** No verificado. **Prioridad:** P2.

- Existe: Planificacion exige revision de cobertura y llegada/servicio en franja.
- Falta / limite: No se ejecuto la dependencia completa.
- Siguiente accion y receta no ejecutada: Planificar envio con compromiso valido y rechazar fuera de franja.
- Evidencia: [`backend/src/NexoRuta.Infrastructure/Reparto/EfRutasRepository.cs:38`](../../../backend/src/NexoRuta.Infrastructure/Reparto/EfRutasRepository.cs#L38); [`backend/src/NexoRuta.Domain/Reparto/CapacidadCarga.cs:8`](../../../backend/src/NexoRuta.Domain/Reparto/CapacidadCarga.cs#L8); [`backend/src/NexoRuta.Infrastructure/Reparto/RestriccionesTemporales.cs:10`](../../../backend/src/NexoRuta.Infrastructure/Reparto/RestriccionesTemporales.cs#L10); [`backend/tests/NexoRuta.IntegrationTests/Reparto/RutasHttpTests.cs:556`](../../../backend/tests/NexoRuta.IntegrationTests/Reparto/RutasHttpTests.cs#L556).

<a id="d05"></a>
### D05 — (dependencia sin titulo original)

**Fuente:** Dependencias!A8:I8 (fila 8). **Modulo:** M03. **Actor:** no especificado en fuente. **Responsable:** Nacho (derivado de Modulos, no asignacion individual de esta fila).

> Solo envíos elegibles pueden asignarse a ruta.

**Implementacion:** Completa. **Verificacion:** No verificado. **Prioridad:** P2.

- Existe: Planificacion valida estado, custodia y pertenencia al operador.
- Falta / limite: No se ejecuto la dependencia completa.
- Siguiente accion y receta no ejecutada: Intentar planificar admitido/no recibido y comprobar rechazo sin asignar.
- Evidencia: [`backend/src/NexoRuta.Infrastructure/Reparto/EfRutasRepository.cs:30`](../../../backend/src/NexoRuta.Infrastructure/Reparto/EfRutasRepository.cs#L30); [`frontend/src/NexoRuta.Backoffice/Pages/Rutas/Planificar.cshtml:1`](../../../frontend/src/NexoRuta.Backoffice/Pages/Rutas/Planificar.cshtml#L1); [`backend/tests/NexoRuta.IntegrationTests/Reparto/RutasHttpTests.cs:441`](../../../backend/tests/NexoRuta.IntegrationTests/Reparto/RutasHttpTests.cs#L441).

<a id="d06"></a>
### D06 — (dependencia sin titulo original)

**Fuente:** Dependencias!A9:I9 (fila 9). **Modulo:** M03. **Actor:** no especificado en fuente. **Responsable:** Nacho (derivado de Modulos, no asignacion individual de esta fila).

> Capacidad y paradas dependen de peso, dimensiones y cantidad de bultos.

**Implementacion:** Completa. **Verificacion:** No verificado. **Prioridad:** P2.

- Existe: Capacidad suma peso/volumen de bultos; maximo cuenta paradas/envios.
- Falta / limite: No se ejecuto la dependencia completa.
- Siguiente accion y receta no ejecutada: Usar dos bultos normales y exceder por separado peso/volumen/paradas.
- Evidencia: [`backend/src/NexoRuta.Infrastructure/Reparto/EfRutasRepository.cs:38`](../../../backend/src/NexoRuta.Infrastructure/Reparto/EfRutasRepository.cs#L38); [`backend/src/NexoRuta.Domain/Reparto/CapacidadCarga.cs:8`](../../../backend/src/NexoRuta.Domain/Reparto/CapacidadCarga.cs#L8); [`backend/src/NexoRuta.Infrastructure/Reparto/RestriccionesTemporales.cs:10`](../../../backend/src/NexoRuta.Infrastructure/Reparto/RestriccionesTemporales.cs#L10); [`backend/tests/NexoRuta.IntegrationTests/Reparto/RutasHttpTests.cs:556`](../../../backend/tests/NexoRuta.IntegrationTests/Reparto/RutasHttpTests.cs#L556).

<a id="d07"></a>
### D07 — (dependencia sin titulo original)

**Fuente:** Dependencias!A10:I10 (fila 10). **Modulo:** M03. **Actor:** no especificado en fuente. **Responsable:** Nacho (derivado de Modulos, no asignacion individual de esta fila).

> Las restricciones de franja dependen de configuración por zona.

**Implementacion:** Completa. **Verificacion:** No verificado. **Prioridad:** P2.

- Existe: Restriccion temporal usa revision de zona capturada al alta.
- Falta / limite: No se ejecuto la dependencia completa.
- Siguiente accion y receta no ejecutada: Cambiar franja vigente y demostrar compromiso historico.
- Evidencia: [`backend/src/NexoRuta.Infrastructure/Reparto/EfRutasRepository.cs:38`](../../../backend/src/NexoRuta.Infrastructure/Reparto/EfRutasRepository.cs#L38); [`backend/src/NexoRuta.Domain/Reparto/CapacidadCarga.cs:8`](../../../backend/src/NexoRuta.Domain/Reparto/CapacidadCarga.cs#L8); [`backend/src/NexoRuta.Infrastructure/Reparto/RestriccionesTemporales.cs:10`](../../../backend/src/NexoRuta.Infrastructure/Reparto/RestriccionesTemporales.cs#L10); [`backend/tests/NexoRuta.IntegrationTests/Reparto/RutasHttpTests.cs:556`](../../../backend/tests/NexoRuta.IntegrationTests/Reparto/RutasHttpTests.cs#L556).

<a id="d08"></a>
### D08 — (dependencia sin titulo original)

**Fuente:** Dependencias!A11:I11 (fila 11). **Modulo:** M04. **Actor:** no especificado en fuente. **Responsable:** Nacho (derivado de Modulos, no asignacion individual de esta fila).

> La app descarga solo rutas despachadas para el repartidor.

**Implementacion:** Completa. **Verificacion:** No verificado. **Prioridad:** P2.

- Existe: Rutas propias filtran repartidor y excluyen planificadas/canceladas.
- Falta / limite: No se ejecuto la dependencia completa.
- Siguiente accion y receta no ejecutada: Consultar con dos repartidores antes/despues del despacho.
- Evidencia: [`backend/src/NexoRuta.Infrastructure/Reparto/EfRutasRepository.cs:105`](../../../backend/src/NexoRuta.Infrastructure/Reparto/EfRutasRepository.cs#L105); [`backend/src/NexoRuta.Infrastructure/Reparto/EfRutasRepository.cs:22`](../../../backend/src/NexoRuta.Infrastructure/Reparto/EfRutasRepository.cs#L22); [`backend/src/NexoRuta.Api/Features/Reparto/Controllers/RutasController.cs:57`](../../../backend/src/NexoRuta.Api/Features/Reparto/Controllers/RutasController.cs#L57); [`backend/tests/NexoRuta.IntegrationTests/Reparto/RutasHttpTests.cs:441`](../../../backend/tests/NexoRuta.IntegrationTests/Reparto/RutasHttpTests.cs#L441).

<a id="d09"></a>
### D09 — (dependencia sin titulo original)

**Fuente:** Dependencias!A12:I12 (fila 12). **Modulo:** M04. **Actor:** no especificado en fuente. **Responsable:** Nacho (derivado de Modulos, no asignacion individual de esta fila).

> El escaneo compara carga física con bultos asignados.

**Implementacion:** Completa. **Verificacion:** No verificado. **Prioridad:** P2.

- Existe: Evaluacion compara identidades escaneadas con lista esperada.
- Falta / limite: No se ejecuto la dependencia completa.
- Siguiente accion y receta no ejecutada: Escanear faltante/sobrante y confirmar alertas.
- Evidencia: [`mobile/src/NexoRuta.Mobile.Application/EvaluacionCargaSalida.cs:5`](../../../mobile/src/NexoRuta.Mobile.Application/EvaluacionCargaSalida.cs#L5); [`mobile/src/NexoRuta.Mobile/Captura/EscanerPage.cs:4`](../../../mobile/src/NexoRuta.Mobile/Captura/EscanerPage.cs#L4); [`mobile/tests/NexoRuta.Mobile.Application.Tests/EvaluacionCargaSalidaTests.cs:6`](../../../mobile/tests/NexoRuta.Mobile.Application.Tests/EvaluacionCargaSalidaTests.cs#L6).

<a id="d10"></a>
### D10 — (dependencia sin titulo original)

**Fuente:** Dependencias!A13:I13 (fila 13). **Modulo:** M04. **Actor:** no especificado en fuente. **Responsable:** Nacho (derivado de Modulos, no asignacion individual de esta fila).

> La prueba de entrega requerida varía por operador.

**Implementacion:** Completa. **Verificacion:** No verificado. **Prioridad:** P2.

- Existe: Formulario y backend consumen requisitos de prueba publicados.
- Falta / limite: No se ejecuto la dependencia completa.
- Siguiente accion y receta no ejecutada: Usar dos operadores con pruebas distintas y comparar validaciones.
- Evidencia: [`mobile/src/NexoRuta.Mobile/Presentacion/EntregaViewModel.cs:39`](../../../mobile/src/NexoRuta.Mobile/Presentacion/EntregaViewModel.cs#L39); [`backend/src/NexoRuta.Infrastructure/Reparto/EfOperacionesRepartoRepository.Ejecucion.cs:280`](../../../backend/src/NexoRuta.Infrastructure/Reparto/EfOperacionesRepartoRepository.Ejecucion.cs#L280); [`backend/tests/NexoRuta.IntegrationTests/Reparto/OperacionesRepartoHttpTests.Evidencias.cs:11`](../../../backend/tests/NexoRuta.IntegrationTests/Reparto/OperacionesRepartoHttpTests.Evidencias.cs#L11).

<a id="d11"></a>
### D11 — (dependencia sin titulo original)

**Fuente:** Dependencias!A14:I14 (fila 14). **Modulo:** M04. **Actor:** no especificado en fuente. **Responsable:** Nacho (derivado de Modulos, no asignacion individual de esta fila).

> Los motivos válidos de no entrega provienen del catálogo del operador.

**Implementacion:** Completa. **Verificacion:** No verificado. **Prioridad:** P2.

- Existe: Motivo viaja por codigo del catalogo fijado en la hoja.
- Falta / limite: No se ejecuto la dependencia completa.
- Siguiente accion y receta no ejecutada: Probar motivo valido, obsoleto y ajeno; revisar no aplicacion.
- Evidencia: [`mobile/src/NexoRuta.Mobile/Presentacion/EntregaViewModel.cs:114`](../../../mobile/src/NexoRuta.Mobile/Presentacion/EntregaViewModel.cs#L114); [`backend/src/NexoRuta.Infrastructure/Reparto/EfOperacionesRepartoRepository.Ejecucion.cs:161`](../../../backend/src/NexoRuta.Infrastructure/Reparto/EfOperacionesRepartoRepository.Ejecucion.cs#L161); [`mobile/tests/NexoRuta.Mobile.Core.Tests/ReglasEnvioTests.cs:6`](../../../mobile/tests/NexoRuta.Mobile.Core.Tests/ReglasEnvioTests.cs#L6).

<a id="d12"></a>
### D12 — (dependencia sin titulo original)

**Fuente:** Dependencias!A15:I15 (fila 15). **Modulo:** M04. **Actor:** no especificado en fuente. **Responsable:** Nacho (derivado de Modulos, no asignacion individual de esta fila).

> La sincronización debe validar transiciones y resolver conflicto con el servidor.

**Implementacion:** Completa. **Verificacion:** No verificado. **Prioridad:** P2.

- Existe: Comando versionado se aplica o registra conflicto/idempotencia en servidor.
- Falta / limite: No se ejecuto la dependencia completa.
- Siguiente accion y receta no ejecutada: Conflicto por bulto tras operacion remota sin perder diario local.
- Evidencia: [`mobile/src/NexoRuta.Mobile.Application/SincronizadorJornada.cs:10`](../../../mobile/src/NexoRuta.Mobile.Application/SincronizadorJornada.cs#L10); [`mobile/src/NexoRuta.Mobile.Storage/RepositorioJornadasSqlite.Sincronizacion.cs:4`](../../../mobile/src/NexoRuta.Mobile.Storage/RepositorioJornadasSqlite.Sincronizacion.cs#L4); [`backend/src/NexoRuta.Infrastructure/Reparto/EfOperacionesRepartoRepository.cs:22`](../../../backend/src/NexoRuta.Infrastructure/Reparto/EfOperacionesRepartoRepository.cs#L22); [`mobile/tests/NexoRuta.Mobile.Application.Tests/SincronizadorJornadaTests.cs:11`](../../../mobile/tests/NexoRuta.Mobile.Application.Tests/SincronizadorJornadaTests.cs#L11).

<a id="d13"></a>
### D13 — (dependencia sin titulo original)

**Fuente:** Dependencias!A16:I16 (fila 16). **Modulo:** M04. **Actor:** no especificado en fuente. **Responsable:** Nacho (derivado de Modulos, no asignacion individual de esta fila).

> La rendición y devolución generan eventos de envío trazables.

**Implementacion:** Completa. **Verificacion:** No verificado. **Prioridad:** P2.

- Existe: Recepcion/entrega al comercio fija contexto de historia y custodia.
- Falta / limite: No se ejecuto la dependencia completa.
- Siguiente accion y receta no ejecutada: Recorrer rendicion/recepcion/devolucion y consultar eventos.
- Evidencia: [`mobile/src/NexoRuta.Mobile/Captura/RendicionPage.cs:3`](../../../mobile/src/NexoRuta.Mobile/Captura/RendicionPage.cs#L3); [`backend/src/NexoRuta.Infrastructure/Reparto/EfRutasRepository.Recepcion.cs:11`](../../../backend/src/NexoRuta.Infrastructure/Reparto/EfRutasRepository.Recepcion.cs#L11); [`mobile/tests/NexoRuta.Mobile.Core.Tests/IncidenciasCierreTests.cs:6`](../../../mobile/tests/NexoRuta.Mobile.Core.Tests/IncidenciasCierreTests.cs#L6).

<a id="d14"></a>
### D14 — (dependencia sin titulo original)

**Fuente:** Dependencias!A17:I17 (fila 17). **Modulo:** M05. **Actor:** no especificado en fuente. **Responsable:** José Hernández (derivado de Modulos, no asignacion individual de esta fila).

> El seguimiento presenta estado e historial del envío.

**Implementacion:** Parcial. **Verificacion:** No verificado. **Prioridad:** P1.

- Existe: Estado y avance publico existen.
- Falta / limite: Historial no existe en DTO publico; exponer historial publico saneado y probarlo.
- Siguiente accion y receta no ejecutada: Historial no existe en DTO publico; exponer historial publico saneado y probarlo.
- Evidencia: [`backend/src/NexoRuta.Application/Seguimiento/UseCases/ConsultarSeguimientoPublicoUseCase.cs:30`](../../../backend/src/NexoRuta.Application/Seguimiento/UseCases/ConsultarSeguimientoPublicoUseCase.cs#L30); [`backend/src/NexoRuta.Api/Features/Seguimiento/Contracts/SeguimientoEstadoResponse.cs:5`](../../../backend/src/NexoRuta.Api/Features/Seguimiento/Contracts/SeguimientoEstadoResponse.cs#L5); [`backend/src/NexoRuta.Infrastructure/Seguimiento/Repositories/EfEnlacesSeguimientoRepository.cs:53`](../../../backend/src/NexoRuta.Infrastructure/Seguimiento/Repositories/EfEnlacesSeguimientoRepository.cs#L53); [`backend/tests/NexoRuta.UnitTests/Seguimiento/ConsultarSeguimientoPublicoUseCaseTests.cs:10`](../../../backend/tests/NexoRuta.UnitTests/Seguimiento/ConsultarSeguimientoPublicoUseCaseTests.cs#L10).

<a id="d15"></a>
### D15 — (dependencia sin titulo original)

**Fuente:** Dependencias!A18:I18 (fila 18). **Modulo:** M05. **Actor:** no especificado en fuente. **Responsable:** José Hernández (derivado de Modulos, no asignacion individual de esta fila).

> La consulta pública usa marca y contacto del operador.

**Implementacion:** Completa. **Verificacion:** No verificado. **Prioridad:** P2.

- Existe: Marca/contacto se retornan por token con el estado.
- Falta / limite: No se ejecuto la dependencia completa.
- Siguiente accion y receta no ejecutada: Abrir dos enlaces de operadores y comprobar marcas/contacto aislados.
- Evidencia: [`backend/src/NexoRuta.Api/Features/IdentidadVisual/Controllers/IdentidadVisualOperadorController.cs:29`](../../../backend/src/NexoRuta.Api/Features/IdentidadVisual/Controllers/IdentidadVisualOperadorController.cs#L29); [`frontend/src/NexoRuta.Tracking/Components/Pages/Seguimiento.razor:30`](../../../frontend/src/NexoRuta.Tracking/Components/Pages/Seguimiento.razor#L30); [`backend/src/NexoRuta.Infrastructure/Seguimiento/Processing/CorreoCodigoCancelacion.cs:6`](../../../backend/src/NexoRuta.Infrastructure/Seguimiento/Processing/CorreoCodigoCancelacion.cs#L6); [`backend/tests/NexoRuta.IntegrationTests/Administracion/IdentidadVisualOperadorHttpTests.cs:21`](../../../backend/tests/NexoRuta.IntegrationTests/Administracion/IdentidadVisualOperadorHttpTests.cs#L21); [`backend/src/NexoRuta.Worker/Messaging/ProcesarCorreoCodigoCancelacion.cs:33`](../../../backend/src/NexoRuta.Worker/Messaging/ProcesarCorreoCodigoCancelacion.cs#L33).

<a id="d16"></a>
### D16 — (dependencia sin titulo original)

**Fuente:** Dependencias!A19:I19 (fila 19). **Modulo:** M05. **Actor:** no especificado en fuente. **Responsable:** José Hernández (derivado de Modulos, no asignacion individual de esta fila).

> La solicitud de reprogramación respeta intentos y plazos.

**Implementacion:** Ausente. **Verificacion:** No verificado. **Prioridad:** P1.

- Existe: Backoffice valida reglas de reprogramacion; destinatario no tiene solicitud.
- Falta / limite: Completar solicitud publica y validar intentos/plazos.
- Siguiente accion y receta no ejecutada: Completar solicitud publica y validar intentos/plazos.
- Evidencia: [`backend/src/NexoRuta.Api/Features/Reparto/Controllers/RutasController.cs:77`](../../../backend/src/NexoRuta.Api/Features/Reparto/Controllers/RutasController.cs#L77); [`backend/src/NexoRuta.Api/Features/Seguimiento/Controllers/SeguimientoPublicoController.cs:17`](../../../backend/src/NexoRuta.Api/Features/Seguimiento/Controllers/SeguimientoPublicoController.cs#L17); [`frontend/src/NexoRuta.Tracking/Components/Pages/Seguimiento.razor:102`](../../../frontend/src/NexoRuta.Tracking/Components/Pages/Seguimiento.razor#L102).

<a id="d17"></a>
### D17 — (dependencia sin titulo original)

**Fuente:** Dependencias!A20:I20 (fila 20). **Modulo:** M05. **Actor:** no especificado en fuente. **Responsable:** José Hernández (derivado de Modulos, no asignacion individual de esta fila).

> Las notificaciones nacen de cambios de estado persistidos.

**Implementacion:** Parcial. **Verificacion:** No verificado. **Prioridad:** P1.

- Existe: Outbox e historia persistida existen, pero no notificacion general de estados.
- Falta / limite: Emitir notificacion de destinatario solo tras commit de transicion.
- Siguiente accion y receta no ejecutada: Emitir notificacion de destinatario solo tras commit de transicion.
- Evidencia: [`backend/src/NexoRuta.Infrastructure/Seguimiento/Processing/ProcesarGeneracionSeguimiento.cs:75`](../../../backend/src/NexoRuta.Infrastructure/Seguimiento/Processing/ProcesarGeneracionSeguimiento.cs#L75); [`backend/src/NexoRuta.Worker/Messaging/OutboxHandlerRegistry.cs:37`](../../../backend/src/NexoRuta.Worker/Messaging/OutboxHandlerRegistry.cs#L37); [`backend/src/NexoRuta.Worker/Program.cs:35`](../../../backend/src/NexoRuta.Worker/Program.cs#L35).

<a id="d18"></a>
### D18 — (dependencia sin titulo original)

**Fuente:** Dependencias!A21:I21 (fila 21). **Modulo:** M05. **Actor:** no especificado en fuente. **Responsable:** José Hernández (derivado de Modulos, no asignacion individual de esta fila).

> Los webhooks del comercio nacen de cambios de estado.

**Implementacion:** Ausente. **Verificacion:** No verificado. **Prioridad:** P1.

- Existe: Eventos llegan a inbox propio, no webhook de comercio.
- Falta / limite: Generar entrega HTTP solo desde cambios persistidos.
- Siguiente accion y receta no ejecutada: Generar entrega HTTP solo desde cambios persistidos.
- Evidencia: [`backend/src/NexoRuta.Api/Features/Envios/Controllers/AvisosComercioController.cs:9`](../../../backend/src/NexoRuta.Api/Features/Envios/Controllers/AvisosComercioController.cs#L9); [`backend/src/NexoRuta.Infrastructure/Notificaciones/EfAvisosComercioRepository.cs:10`](../../../backend/src/NexoRuta.Infrastructure/Notificaciones/EfAvisosComercioRepository.cs#L10); [`backend/src/NexoRuta.Worker/Messaging/CommerceNoticeConsumer.cs:8`](../../../backend/src/NexoRuta.Worker/Messaging/CommerceNoticeConsumer.cs#L8).

<a id="d19"></a>
### D19 — (dependencia sin titulo original)

**Fuente:** Dependencias!A22:I22 (fila 22). **Modulo:** M06. **Actor:** no especificado en fuente. **Responsable:** José Hernández (derivado de Modulos, no asignacion individual de esta fila).

> La posición de la flota alimenta el tablero en vivo.

**Implementacion:** Parcial. **Verificacion:** No verificado. **Prioridad:** P1.

- Existe: Diario GPS/proyeccion existen, sin alimentacion de tablero vivo.
- Falta / limite: Conectar posicion valida a tablero aislado por operador.
- Siguiente accion y receta no ejecutada: Conectar posicion valida a tablero aislado por operador.
- Evidencia: [`frontend/src/NexoRuta.Backoffice/Pages/Rutas/_Operacion.cshtml:21`](../../../frontend/src/NexoRuta.Backoffice/Pages/Rutas/_Operacion.cshtml#L21); [`frontend/src/NexoRuta.Backoffice/Pages/Rutas/_Flota.cshtml:1`](../../../frontend/src/NexoRuta.Backoffice/Pages/Rutas/_Flota.cshtml#L1); [`backend/src/NexoRuta.Infrastructure/Reparto/EfRutasRepository.Recorrido.cs:10`](../../../backend/src/NexoRuta.Infrastructure/Reparto/EfRutasRepository.Recorrido.cs#L10).

<a id="d20"></a>
### D20 — (dependencia sin titulo original)

**Fuente:** Dependencias!A23:I23 (fila 23). **Modulo:** M06. **Actor:** no especificado en fuente. **Responsable:** José Hernández (derivado de Modulos, no asignacion individual de esta fila).

> El tablero detecta envíos en riesgo según estado y compromiso.

**Implementacion:** Parcial. **Verificacion:** No verificado. **Prioridad:** P1.

- Existe: Estimaciones y compromisos disponibles, sin listado vivo de riesgo.
- Falta / limite: Calcular riesgo por estado/ETA/ventana y demostrar actualizacion.
- Siguiente accion y receta no ejecutada: Calcular riesgo por estado/ETA/ventana y demostrar actualizacion.
- Evidencia: [`frontend/src/NexoRuta.Backoffice/Pages/Rutas/_Operacion.cshtml:21`](../../../frontend/src/NexoRuta.Backoffice/Pages/Rutas/_Operacion.cshtml#L21); [`frontend/src/NexoRuta.Backoffice/Pages/Rutas/_Flota.cshtml:1`](../../../frontend/src/NexoRuta.Backoffice/Pages/Rutas/_Flota.cshtml#L1); [`backend/src/NexoRuta.Infrastructure/Reparto/EfRutasRepository.Recorrido.cs:10`](../../../backend/src/NexoRuta.Infrastructure/Reparto/EfRutasRepository.Recorrido.cs#L10).

<a id="d21"></a>
### D21 — (dependencia sin titulo original)

**Fuente:** Dependencias!A24:I24 (fila 24). **Modulo:** M06. **Actor:** no especificado en fuente. **Responsable:** José Hernández (derivado de Modulos, no asignacion individual de esta fila).

> El tablero relaciona envíos con rutas y repartidores.

**Implementacion:** Parcial. **Verificacion:** No verificado. **Prioridad:** P1.

- Existe: Hoja relaciona envio/repartidor y vehiculo, no tablero vivo.
- Falta / limite: Exponer relaciones y acciones en tablero en vivo.
- Siguiente accion y receta no ejecutada: Exponer relaciones y acciones en tablero en vivo.
- Evidencia: [`frontend/src/NexoRuta.Backoffice/Pages/Rutas/_Operacion.cshtml:21`](../../../frontend/src/NexoRuta.Backoffice/Pages/Rutas/_Operacion.cshtml#L21); [`frontend/src/NexoRuta.Backoffice/Pages/Rutas/_Flota.cshtml:1`](../../../frontend/src/NexoRuta.Backoffice/Pages/Rutas/_Flota.cshtml#L1); [`backend/src/NexoRuta.Infrastructure/Reparto/EfRutasRepository.Recorrido.cs:10`](../../../backend/src/NexoRuta.Infrastructure/Reparto/EfRutasRepository.Recorrido.cs#L10).

<a id="d22"></a>
### D22 — (dependencia sin titulo original)

**Fuente:** Dependencias!A25:I25 (fila 25). **Modulo:** M06. **Actor:** no especificado en fuente. **Responsable:** José Hernández (derivado de Modulos, no asignacion individual de esta fila).

> La liquidación usa cargos calculados al alta.

**Implementacion:** Parcial. **Verificacion:** No verificado. **Prioridad:** P1.

- Existe: Reporte suma tarifa vigente del envio; no hay liquidacion.
- Falta / limite: Crear liquidacion con procedencia del cargo admitido y ajustes trazables.
- Siguiente accion y receta no ejecutada: Crear liquidacion con procedencia del cargo admitido y ajustes trazables.
- Evidencia: [`backend/src/NexoRuta.Api/Features/Envios/Controllers/ReporteOperacionesController.cs:13`](../../../backend/src/NexoRuta.Api/Features/Envios/Controllers/ReporteOperacionesController.cs#L13); [`frontend/src/NexoRuta.Backoffice/Pages/ReporteOperaciones.cshtml:8`](../../../frontend/src/NexoRuta.Backoffice/Pages/ReporteOperaciones.cshtml#L8).

<a id="d23"></a>
### D23 — (dependencia sin titulo original)

**Fuente:** Dependencias!A26:I26 (fila 26). **Modulo:** M06. **Actor:** no especificado en fuente. **Responsable:** José Hernández (derivado de Modulos, no asignacion individual de esta fila).

> Los indicadores se agregan desde el historial de envíos.

**Implementacion:** Parcial. **Verificacion:** No verificado. **Prioridad:** P1.

- Existe: Reporte agrega estado actual, no indicadores historicos.
- Falta / limite: Agregar indicadores de cumplimiento desde historial inmutable.
- Siguiente accion y receta no ejecutada: Agregar indicadores de cumplimiento desde historial inmutable.
- Evidencia: [`backend/src/NexoRuta.Api/Features/Envios/Controllers/ReporteOperacionesController.cs:13`](../../../backend/src/NexoRuta.Api/Features/Envios/Controllers/ReporteOperacionesController.cs#L13); [`frontend/src/NexoRuta.Backoffice/Pages/ReporteOperaciones.cshtml:8`](../../../frontend/src/NexoRuta.Backoffice/Pages/ReporteOperaciones.cshtml#L8).

<a id="d24"></a>
### D24 — (dependencia sin titulo original)

**Fuente:** Dependencias!A27:I27 (fila 27). **Modulo:** M05. **Actor:** no especificado en fuente. **Responsable:** José Hernández (derivado de Modulos, no asignacion individual de esta fila).

> Entregas offline notifican luego de sincronizarse y persistirse.

**Implementacion:** Parcial. **Verificacion:** No verificado. **Prioridad:** P1.

- Existe: Persistencia de operaciones precede efectos de outbox; falta envio al destinatario.
- Falta / limite: Entregar offline, sincronizar y comprobar una notificacion posterior al commit.
- Siguiente accion y receta no ejecutada: Entregar offline, sincronizar y comprobar una notificacion posterior al commit.
- Evidencia: [`backend/src/NexoRuta.Infrastructure/Seguimiento/Processing/ProcesarGeneracionSeguimiento.cs:75`](../../../backend/src/NexoRuta.Infrastructure/Seguimiento/Processing/ProcesarGeneracionSeguimiento.cs#L75); [`backend/src/NexoRuta.Worker/Messaging/OutboxHandlerRegistry.cs:37`](../../../backend/src/NexoRuta.Worker/Messaging/OutboxHandlerRegistry.cs#L37); [`backend/src/NexoRuta.Worker/Program.cs:35`](../../../backend/src/NexoRuta.Worker/Program.cs#L35).

<a id="nfr01"></a>
### NFR-01 — Plataforma y arquitectura

**Fuente:** No funcionales!A4:F4 (fila 4). **Modulo:** M01. **Actor:** no especificado en fuente. **Responsable:** José Garcia (derivado de Modulos, no asignacion individual de esta fila).

> NET 10; monolito modular API/web; worker separado por cola; dominio independiente; prueba de arquitectura; ADR; Docker Compose.

**Implementacion:** Completa. **Verificacion:** No verificado. **Prioridad:** P2.

- Existe: Soluciones net10, capas Domain/Application/Infrastructure/API, Worker separado, Compose y prueba de limites.
- Falta / limite: Build/test actual pendiente; una prueba arquitectonica existente no acredita todas las reglas del sistema.
- Siguiente accion y receta no ejecutada: Ejecutar build y suite arquitectonica del checkout, revisar ADR/componentes contra despliegue real.
- Evidencia: [`backend/global.json:3`](../../../backend/global.json#L3); [`backend/src/NexoRuta.Worker/Program.cs:20`](../../../backend/src/NexoRuta.Worker/Program.cs#L20); [`backend/tests/NexoRuta.ArchitectureTests/ShipmentBoundaryTests.cs:16`](../../../backend/tests/NexoRuta.ArchitectureTests/ShipmentBoundaryTests.cs#L16); [`compose.yaml:11`](../../../compose.yaml#L11).

<a id="nfr02"></a>
### NFR-02 — Presentación web

**Fuente:** No funcionales!A5:F5 (fila 5). **Modulo:** M01. **Actor:** no especificado en fuente. **Responsable:** José Garcia (derivado de Modulos, no asignacion individual de esta fila).

> Backoffice Razor Pages; portal y público Blazor; ADR del modo de renderizado y su efecto operativo.

**Implementacion:** Parcial. **Verificacion:** No verificado. **Prioridad:** P2.

- Existe: Backoffice Razor Pages; Commerce/Tracking Blazor InteractiveServer y hosts propios.
- Falta / limite: No se acredita ADR vigente de modo de renderizado y su efecto operativo; revision visual bloqueada sin navegador autorizado.
- Siguiente accion y receta no ejecutada: Localizar/completar ADR del renderizado y demostrar reconexion/estado por instancia.
- Evidencia: [`frontend/src/NexoRuta.Backoffice/Pages/Rutas/_Operacion.cshtml:1`](../../../frontend/src/NexoRuta.Backoffice/Pages/Rutas/_Operacion.cshtml#L1); [`frontend/src/NexoRuta.Tracking/Components/Pages/Seguimiento.razor:2`](../../../frontend/src/NexoRuta.Tracking/Components/Pages/Seguimiento.razor#L2); [`frontend/docs/presentation-structure.md:1`](../../../frontend/docs/presentation-structure.md#L1).

<a id="nfr03"></a>
### NFR-03 — Seguridad

**Fuente:** No funcionales!A6:F6 (fila 6). **Modulo:** M01. **Actor:** no especificado en fuente. **Responsable:** José Garcia (derivado de Modulos, no asignacion individual de esta fila).

> OIDC/OAuth 2.1 con PKCE o Identity; autorización API por rol/tenant/comercio; secretos, TLS, CORS, rate limit, cabeceras y cifrado móvil.

**Implementacion:** Parcial. **Verificacion:** No verificado. **Prioridad:** P1.

- Existe: IdentityCore, JWT, politicas de API/RLS y rate limits; cifrado de archivos/SQLite movil y biometria nativa.
- Falta / limite: No se verificaron TLS/CORS/cabeceras/secretos y ciclo de sesion en ejecucion; no se afirma certificacion de seguridad.
- Siguiente accion y receta no ejecutada: Ejecutar flujos restringidos y comprobar HTTPS, cabeceras, revocacion, aislamiento y cifrado en dispositivo.
- Evidencia: [`backend/src/NexoRuta.Infrastructure/Persistence/DependencyInjection.cs:104`](../../../backend/src/NexoRuta.Infrastructure/Persistence/DependencyInjection.cs#L104); [`backend/src/NexoRuta.Api/Program.cs:134`](../../../backend/src/NexoRuta.Api/Program.cs#L134); [`backend/src/NexoRuta.Api/Program.cs:217`](../../../backend/src/NexoRuta.Api/Program.cs#L217); [`mobile/src/NexoRuta.Mobile.Storage/RepositorioArchivosCifrados.cs:8`](../../../mobile/src/NexoRuta.Mobile.Storage/RepositorioArchivosCifrados.cs#L8); [`mobile/src/NexoRuta.Mobile/Seguridad/VerificacionLocal.cs:5`](../../../mobile/src/NexoRuta.Mobile/Seguridad/VerificacionLocal.cs#L5).

<a id="nfr04"></a>
### NFR-04 — Persistencia

**Fuente:** No funcionales!A7:F7 (fila 7). **Modulo:** M02. **Actor:** no especificado en fuente. **Responsable:** sin asignacion individual (derivado de Modulos, no asignacion individual de esta fila).

> Base principal con EF Core y migraciones; SQLite móvil; concurrencia optimista demostrada.

**Implementacion:** Completa. **Verificacion:** No verificado. **Prioridad:** P2.

- Existe: EF Core y migraciones PostgreSQL/PostGIS; SQLite movil y versiones optimistas de comandos/agregados.
- Falta / limite: Demostracion de dos escritores y reinicio SQLite no ejecutada aqui.
- Siguiente accion y receta no ejecutada: Ejecutar migracion sintentica/concurrencia y reinicio local sin perder operaciones.
- Evidencia: [`backend/src/NexoRuta.Infrastructure/Persistence/NexoRutaDbContext.cs:16`](../../../backend/src/NexoRuta.Infrastructure/Persistence/NexoRutaDbContext.cs#L16); [`mobile/src/NexoRuta.Mobile.Storage/RepositorioJornadasSqlite.cs:10`](../../../mobile/src/NexoRuta.Mobile.Storage/RepositorioJornadasSqlite.cs#L10); [`backend/tests/NexoRuta.IntegrationTests/Reparto/RutasHttpTests.cs:580`](../../../backend/tests/NexoRuta.IntegrationTests/Reparto/RutasHttpTests.cs#L580); [`backend/tests/NexoRuta.IntegrationTests/Administracion/Cu01MigrationTests.cs:12`](../../../backend/tests/NexoRuta.IntegrationTests/Administracion/Cu01MigrationTests.cs#L12).

<a id="nfr05"></a>
### NFR-05 — Multitenancy

**Fuente:** No funcionales!A8:F8 (fila 8). **Modulo:** M01. **Actor:** no especificado en fuente. **Responsable:** José Garcia (derivado de Modulos, no asignacion individual de esta fila).

> Estrategia y resolución de tenant; aislamiento lectura/escritura y de comercios; tests, branding, migraciones y dos operadores.

**Implementacion:** Completa. **Verificacion:** No verificado. **Prioridad:** P2.

- Existe: Contexto transaccional RLS con roles restringidos y politicas; organizacion validada y branding aislado.
- Falta / limite: No se probaron hoy dos operadores/comercios y reutilizacion de conexion.
- Siguiente accion y receta no ejecutada: Ejecutar RLS SQL/HTTP con roles runtime y dos operadores/comercios.
- Evidencia: [`backend/tests/NexoRuta.IntegrationTests/Seguridad/RlsRestrictedHttpFlowTests.cs:15`](../../../backend/tests/NexoRuta.IntegrationTests/Seguridad/RlsRestrictedHttpFlowTests.cs#L15); [`backend/tests/NexoRuta.IntegrationTests/Seguridad/RlsPolicyTests.cs:27`](../../../backend/tests/NexoRuta.IntegrationTests/Seguridad/RlsPolicyTests.cs#L27); [`backend/tests/NexoRuta.IntegrationTests/Seguridad/RlsActorContractTests.cs:11`](../../../backend/tests/NexoRuta.IntegrationTests/Seguridad/RlsActorContractTests.cs#L11); [`backend/src/NexoRuta.Application/Envios/UseCases/ListarEnviosUseCase.cs:13`](../../../backend/src/NexoRuta.Application/Envios/UseCases/ListarEnviosUseCase.cs#L13); [`backend/src/NexoRuta.Infrastructure/Administracion/EfConsultaIdentidadVisualOperador.cs:15`](../../../backend/src/NexoRuta.Infrastructure/Administracion/EfConsultaIdentidadVisualOperador.cs#L15).

<a id="nfr06"></a>
### NFR-06 — Configurabilidad

**Fuente:** No funcionales!A9:F9 (fila 9). **Modulo:** M01. **Actor:** no especificado en fuente. **Responsable:** José Garcia (derivado de Modulos, no asignacion individual de esta fila).

> Tarifas y reglas editables en caliente y versionadas; envíos previos conservan tratamiento.

**Implementacion:** Completa. **Verificacion:** No verificado. **Prioridad:** P2.

- Existe: Reglas y tarifas se publican/versionan; admision fija referencias y cobertura.
- Falta / limite: No se demostro cambio caliente conservando envio previo en esta sesion.
- Siguiente accion y receta no ejecutada: Publicar versiones nuevas sin reiniciar y completar envio anterior.
- Evidencia: [`backend/src/NexoRuta.Domain/ReglasOperativas/VersionReglasOperativas.cs:3`](../../../backend/src/NexoRuta.Domain/ReglasOperativas/VersionReglasOperativas.cs#L3); [`backend/src/NexoRuta.Infrastructure/Envios/Repositories/TarifasAdmision.cs:37`](../../../backend/src/NexoRuta.Infrastructure/Envios/Repositories/TarifasAdmision.cs#L37); [`backend/src/NexoRuta.Infrastructure/Reparto/RestriccionesTemporales.cs:9`](../../../backend/src/NexoRuta.Infrastructure/Reparto/RestriccionesTemporales.cs#L9); [`backend/tests/NexoRuta.IntegrationTests/Envios/ReglasEnvioAdmisionHttpTests.cs:13`](../../../backend/tests/NexoRuta.IntegrationTests/Envios/ReglasEnvioAdmisionHttpTests.cs#L13).

<a id="nfr07"></a>
### NFR-07 — Caché distribuido

**Fuente:** No funcionales!A10:F10 (fila 10). **Modulo:** M05. **Actor:** no especificado en fuente. **Responsable:** José Hernández (derivado de Modulos, no asignacion individual de esta fila).

> Dos casos de uso con perfiles distintos, expiración e invalidación y métricas hit/miss.

**Implementacion:** Parcial. **Verificacion:** No verificado. **Prioridad:** P1.

- Existe: Adaptador Redis compartido con hit/miss/error/timeout, TTL/jitter; dos consumidores: branding por operador/version y snapshot del tarifario publicado.
- Falta / limite: No se verificaron dos perfiles completos, invalidacion y metricas con dos API en este checkout. Trabajo de cache pertenece a companeros: auditoria solamente.
- Siguiente accion y receta no ejecutada: Pedir al responsable evidencia de ambos casos, perfiles, expiracion/invalidacion y hit/miss entre instancias, sin implementar aqui.
- Evidencia: [`backend/src/NexoRuta.Infrastructure/Tarifas/EfTarifariosRepository.cs:178`](../../../backend/src/NexoRuta.Infrastructure/Tarifas/EfTarifariosRepository.cs#L178); [`backend/src/NexoRuta.Infrastructure/Caching/DistributedCacheAccess.cs:37`](../../../backend/src/NexoRuta.Infrastructure/Caching/DistributedCacheAccess.cs#L37); [`backend/src/NexoRuta.Infrastructure/Caching/DistributedCacheAccess.cs:118`](../../../backend/src/NexoRuta.Infrastructure/Caching/DistributedCacheAccess.cs#L118); [`backend/src/NexoRuta.Infrastructure/Administracion/EfConsultaIdentidadVisualOperador.cs:24`](../../../backend/src/NexoRuta.Infrastructure/Administracion/EfConsultaIdentidadVisualOperador.cs#L24); [`backend/tests/NexoRuta.IntegrationTests/Caching/DistributedCacheRedisTests.cs:12`](../../../backend/tests/NexoRuta.IntegrationTests/Caching/DistributedCacheRedisTests.cs#L12).

<a id="nfr08"></a>
### NFR-08 — Mensajería y worker

**Fuente:** No funcionales!A11:F11 (fila 11). **Modulo:** M05. **Actor:** no especificado en fuente. **Responsable:** José Hernández (derivado de Modulos, no asignacion individual de esta fila).

> Outbox; consumidor idempotente; reintentos crecientes, cola de fallidos y panel de reintento.

**Implementacion:** Parcial. **Verificacion:** No verificado. **Prioridad:** P1.

- Existe: Outbox con reserva, confirmacion/reintento, consumidores idempotentes y DLQ de recuperacion/seguimiento.
- Falta / limite: Panel funcional para inspeccionar/reintentar fallidos no encontrado; infraestructura de cola no sustituye operacion.
- Siguiente accion y receta no ejecutada: Completar panel de fallidos/reintento e integrar evidencias de backoff/idempotencia.
- Evidencia: [`backend/src/NexoRuta.Worker/Worker.cs:81`](../../../backend/src/NexoRuta.Worker/Worker.cs#L81); [`backend/src/NexoRuta.Infrastructure/Seguimiento/Processing/ProcesarGeneracionSeguimiento.cs:61`](../../../backend/src/NexoRuta.Infrastructure/Seguimiento/Processing/ProcesarGeneracionSeguimiento.cs#L61); [`backend/src/NexoRuta.Worker/Messaging/PasswordRecoveryEmailDeadLetterConsumer.cs:8`](../../../backend/src/NexoRuta.Worker/Messaging/PasswordRecoveryEmailDeadLetterConsumer.cs#L8); [`backend/src/NexoRuta.Infrastructure/Outbox/EfOutboxRepository.cs:6`](../../../backend/src/NexoRuta.Infrastructure/Outbox/EfOutboxRepository.cs#L6).

<a id="nfr09"></a>
### NFR-09 — Avisos a comercios

**Fuente:** No funcionales!A12:F12 (fila 12). **Modulo:** M05. **Actor:** no especificado en fuente. **Responsable:** José Hernández (derivado de Modulos, no asignacion individual de esta fila).

> Suscripción por comercio y evento; firma, reintentos, fallidos, historial/reenvío y receptor de prueba.

**Implementacion:** Ausente. **Verificacion:** No verificado. **Prioridad:** P1.

- Existe: Outbox e inbox de Commerce disponibles, sin HTTP saliente.
- Falta / limite: Falta circuito suscripcion/eventos/firma/reintentos/fallidos/historial/reenvio/receptor de prueba.
- Siguiente accion y receta no ejecutada: Resolver como circuito conjunto CU28/AP05, con firma y receptor controlado.
- Evidencia: [`backend/src/NexoRuta.Api/Features/Envios/Controllers/AvisosComercioController.cs:9`](../../../backend/src/NexoRuta.Api/Features/Envios/Controllers/AvisosComercioController.cs#L9); [`backend/src/NexoRuta.Worker/Messaging/CommerceNoticeConsumer.cs:8`](../../../backend/src/NexoRuta.Worker/Messaging/CommerceNoticeConsumer.cs#L8); [`backend/src/NexoRuta.Worker/Messaging/OutboxHandlerRegistry.cs:13`](../../../backend/src/NexoRuta.Worker/Messaging/OutboxHandlerRegistry.cs#L13).

<a id="nfr10"></a>
### NFR-10 — Tiempo real

**Fuente:** No funcionales!A13:F13 (fila 13). **Modulo:** M06. **Actor:** no especificado en fuente. **Responsable:** José Hernández (derivado de Modulos, no asignacion individual de esta fila).

> e

**Implementacion:** Ausente. **Verificacion:** Bloqueado. **Prioridad:** P0.

- Existe: En codigo hay paginas Razor de flota/rutas, no hubs SignalR encontrados.
- Falta / limite: La celda vigente No funcionales!F13 dice literalmente e. HEAD dice SignalR con autenticacion/autorizacion/aislamiento y varias API; no se repara ni usa como requisito vigente en silencio.
- Siguiente accion y receta no ejecutada: Confirmar/corregir la celda fuente antes de aceptar la especificacion; si se confirma HEAD, implementar SignalR autenticado/aislado multinstancia.
- Evidencia: [`frontend/src/NexoRuta.Backoffice/Pages/Rutas/_Operacion.cshtml:21`](../../../frontend/src/NexoRuta.Backoffice/Pages/Rutas/_Operacion.cshtml#L21); [`backend/src/NexoRuta.Api/Program.cs:275`](../../../backend/src/NexoRuta.Api/Program.cs#L275).

<a id="nfr11"></a>
### NFR-11 — MAUI

**Fuente:** No funcionales!A14:F14 (fila 14). **Modulo:** M04. **Actor:** no especificado en fuente. **Responsable:** Nacho (derivado de Modulos, no asignacion individual de esta fila).

> MVVM, ubicación segundo plano, escaneo, evidencia, offline cifrado, biometría y avisos con app cerrada.

**Implementacion:** Parcial. **Verificacion:** Bloqueado. **Prioridad:** P1.

- Existe: MAUI/MVVM, servicio Android ubicacion, escaneo/foto/firma, persistencia cifrada, biometria y registro FCM.
- Falta / limite: Ejecucion nativa background/biometria/camara y push con app cerrada no acreditadas; bibliotecas portables no las sustituyen.
- Siguiente accion y receta no ejecutada: Ensayo Android real de permisos, captura, reinicio offline, biometria y app cerrada con FCM controlado autorizado.
- Evidencia: [`mobile/src/NexoRuta.Mobile/Presentacion/EntregaViewModel.cs:11`](../../../mobile/src/NexoRuta.Mobile/Presentacion/EntregaViewModel.cs#L11); [`mobile/src/NexoRuta.Mobile/Ubicacion/TrackingJornada.cs:14`](../../../mobile/src/NexoRuta.Mobile/Ubicacion/TrackingJornada.cs#L14); [`mobile/src/NexoRuta.Mobile/Seguridad/VerificacionLocal.cs:5`](../../../mobile/src/NexoRuta.Mobile/Seguridad/VerificacionLocal.cs#L5); [`mobile/src/NexoRuta.Mobile/Notificaciones/RegistroPushPlataforma.cs:12`](../../../mobile/src/NexoRuta.Mobile/Notificaciones/RegistroPushPlataforma.cs#L12).

<a id="nfr12"></a>
### NFR-12 — Observabilidad

**Fuente:** No funcionales!A15:F15 (fila 15). **Modulo:** M06. **Actor:** no especificado en fuente. **Responsable:** José Hernández (derivado de Modulos, no asignacion individual de esta fila).

> Serilog, OpenTelemetry, correlación extremo a extremo y tablero con latencia, errores, cola, sync, fallidos y caché.

**Implementacion:** Parcial. **Verificacion:** No verificado. **Prioridad:** P1.

- Existe: Serilog/OpenTelemetry, correlacion de API/Worker y metricas API/sync/cache; Grafana/alertas versionadas.
- Falta / limite: No se observaron trazas y paneles vivos para latencia/error/cola/sync/fallidos/cache.
- Siguiente accion y receta no ejecutada: Generar flujo controlado y capturar correlacion E2E y cada panel con fuente/tiempo.
- Evidencia: [`backend/src/NexoRuta.Infrastructure/Hosting/HostingTelemetry.cs:14`](../../../backend/src/NexoRuta.Infrastructure/Hosting/HostingTelemetry.cs#L14); [`backend/src/NexoRuta.Infrastructure/Hosting/ApiTelemetry.cs:20`](../../../backend/src/NexoRuta.Infrastructure/Hosting/ApiTelemetry.cs#L20); [`backend/src/NexoRuta.Worker/WorkerTelemetry.cs:8`](../../../backend/src/NexoRuta.Worker/WorkerTelemetry.cs#L8); [`deploy/observability/grafana/nexoruta.json:19`](../../../deploy/observability/grafana/nexoruta.json#L19).

<a id="nfr13"></a>
### NFR-13 — Escalabilidad

**Fuente:** No funcionales!A16:F16 (fila 16). **Modulo:** M01. **Actor:** no especificado en fuente. **Responsable:** José Garcia (derivado de Modulos, no asignacion individual de esta fila).

> Dos API balanceadas, continuidad, API sin estado, health/ready/live, cierre controlado, claves compartidas y jobs únicos.

**Implementacion:** Parcial. **Verificacion:** No verificado. **Prioridad:** P1.

- Existe: IaC/balanceador, readiness/liveness, anillo DataProtection compartido y reservas de jobs/outbox.
- Falta / limite: No se verificaron dos API, caida/continuidad, cierre controlado ni unicidad diaria; AP09 ausente.
- Siguiente accion y receta no ejecutada: Ensayo autorizado local de dos API/failover/claves compartidas y jobs unicos; no acceder remoto sin permiso.
- Evidencia: [`backend/src/NexoRuta.Api/Program.cs:276`](../../../backend/src/NexoRuta.Api/Program.cs#L276); [`backend/src/NexoRuta.Infrastructure/Hosting/SharedDataProtection.cs:31`](../../../backend/src/NexoRuta.Infrastructure/Hosting/SharedDataProtection.cs#L31); [`infra/gcp/demo/load-balancer.tf:17`](../../../infra/gcp/demo/load-balancer.tf#L17); [`backend/src/NexoRuta.Worker/Worker.cs:33`](../../../backend/src/NexoRuta.Worker/Worker.cs#L33).

<a id="nfr14"></a>
### NFR-14 — Nube e IaC

**Fuente:** No funcionales!A17:F17 (fila 17). **Modulo:** M01. **Actor:** no especificado en fuente. **Responsable:** José Garcia (derivado de Modulos, no asignacion individual de esta fila).

> Nube remota HTTPS; IaC reproducible, variables, secretos, CI/CD y evidencia de costo.

**Implementacion:** Parcial. **Verificacion:** No verificado. **Prioridad:** P1.

- Existe: Terraform/OpenTofu y pipelines de despliegue, variables/secretos y costos documentados.
- Falta / limite: Existencia IaC no acredita nube HTTPS vigente ni ejecucion/costo; no hubo autorizacion remota para esta auditoria.
- Siguiente accion y receta no ejecutada: Con autorizacion explicita del destino/sesion, presentar deploy reproducible, HTTPS y costo; conservar pendiente hasta entonces.
- Evidencia: [`infra/gcp/demo/main.tf:71`](../../../infra/gcp/demo/main.tf#L71); [`infra/gcp/costs.md:1`](../../../infra/gcp/costs.md#L1); [`.github/workflows/publish.yml:1`](../../../.github/workflows/publish.yml#L1).

<a id="nfr15"></a>
### NFR-15 — Calidad

**Fuente:** No funcionales!A18:F18 (fila 18). **Modulo:** M02. **Actor:** no especificado en fuente. **Responsable:** sin asignacion individual (derivado de Modulos, no asignacion individual de esta fila).

> Pruebas unitarias de dominio, integración crítica, arquitectura y aislamiento, todas en pipeline.

**Implementacion:** Parcial. **Verificacion:** No verificado. **Prioridad:** P1.

- Existe: Suites dominio/integracion/arquitectura/RLS y workflows versionados.
- Falta / limite: No se ejecutaron aqui ni se consulto CI; cobertura funcional incompleta de capacidades ausentes.
- Siguiente accion y receta no ejecutada: Ejecutar suites actuales y registrar fallas/base, luego cubrir circuitos faltantes en CI.
- Evidencia: [`backend/tests/NexoRuta.ArchitectureTests/ShipmentBoundaryTests.cs:16`](../../../backend/tests/NexoRuta.ArchitectureTests/ShipmentBoundaryTests.cs#L16); [`backend/tests/NexoRuta.IntegrationTests/Seguridad/RlsRestrictedHttpFlowTests.cs:15`](../../../backend/tests/NexoRuta.IntegrationTests/Seguridad/RlsRestrictedHttpFlowTests.cs#L15); [`.github/workflows/ci.yml:133`](../../../.github/workflows/ci.yml#L133); [`backend/.github/workflows/ci.yml:123`](../../../backend/.github/workflows/ci.yml#L123).

<a id="opt01"></a>
### OPT-01 — Seguimiento público como servicio independiente

**Fuente:** Opcionales!A4:G4 (fila 4). **Modulo:** M05. **Actor:** no especificado en fuente. **Responsable:** José Hernández (derivado de Modulos, no asignacion individual de esta fila).

> Base propia de solo lectura alimentada solo por cola; consistencia eventual medida y escalado independiente.

**Implementacion:** Ausente. **Verificacion:** No verificado. **Prioridad:** Sin accion.

- Existe: Tracking es host web separado que consulta API principal.
- Falta / limite: No es servicio de lectura con base propia alimentada solo por cola ni consistencia/escala medidas.
- Siguiente accion y receta no ejecutada: Descartado en Excel: no implementar ni exigir puntos.
- Evidencia: [`frontend/src/NexoRuta.Tracking/Program.cs:4`](../../../frontend/src/NexoRuta.Tracking/Program.cs#L4); [`backend/src/NexoRuta.Api/Features/Seguimiento/Controllers/SeguimientoPublicoController.cs:14`](../../../backend/src/NexoRuta.Api/Features/Seguimiento/Controllers/SeguimientoPublicoController.cs#L14).
- Decision original: **Descartado**. Seleccionado: **False**. Potencial: **4** puntos; acreditados: **0**. Excluido del plan obligatorio; no implementar por esta auditoria.

<a id="opt02"></a>
### OPT-02 — gRPC para sincronización y telemetría móvil

**Fuente:** Opcionales!A5:G5 (fila 5). **Modulo:** M04. **Actor:** no especificado en fuente. **Responsable:** Nacho (derivado de Modulos, no asignacion individual de esta fila).

> Client streaming, protobuf y comparación medida con REST en red degradada.

**Implementacion:** Ausente. **Verificacion:** No verificado. **Prioridad:** Sin accion.

- Existe: Sincronizacion actual HTTP REST.
- Falta / limite: No se encontro gRPC streaming/protobuf ni comparativa degradada.
- Siguiente accion y receta no ejecutada: Descartado: conservar REST y no exigir este opcional.
- Evidencia: [`backend/src/NexoRuta.Api/Features/Reparto/Controllers/OperacionesRepartoController.cs:11`](../../../backend/src/NexoRuta.Api/Features/Reparto/Controllers/OperacionesRepartoController.cs#L11).
- Decision original: **Descartado**. Seleccionado: **False**. Potencial: **4** puntos; acreditados: **0**. Excluido del plan obligatorio; no implementar por esta auditoria.

<a id="opt03"></a>
### OPT-03 — Kafka para eventos de flota

**Fuente:** Opcionales!A6:G6 (fila 6). **Modulo:** M04 / M06. **Actor:** no especificado en fuente. **Responsable:** sin asignacion individual.

> Más de un consumidor y reconstrucción por replay; justificar coexistencia con cola obligatoria.

**Implementacion:** Parcial. **Verificacion:** No verificado. **Prioridad:** P1.

- Existe: Kafka publica EnvioCreado, recuperacion y avisos de bulto/operacion; existen consumidores separados.
- Falta / limite: Los eventos no son de flota; mas de un consumidor de eventos de flota y reconstruccion por replay no demostrados.
- Siguiente accion y receta no ejecutada: Publicar flujo de flota, dos consumidores y reconstruccion desde cero con resultado comparable, justificando coexistencia RabbitMQ.
- Evidencia: [`backend/src/NexoRuta.Worker/Messaging/KafkaEnvioCreadoPublisher.cs:11`](../../../backend/src/NexoRuta.Worker/Messaging/KafkaEnvioCreadoPublisher.cs#L11); [`backend/src/NexoRuta.Worker/Messaging/CommerceNoticeConsumer.cs:8`](../../../backend/src/NexoRuta.Worker/Messaging/CommerceNoticeConsumer.cs#L8); [`backend/src/NexoRuta.Worker/Messaging/PasswordRecoveryMongoConsumer.cs:10`](../../../backend/src/NexoRuta.Worker/Messaging/PasswordRecoveryMongoConsumer.cs#L10).
- Decision original: **Seleccionado**. Seleccionado: **True**. Potencial: **3** puntos; acreditados: **0**. Obligacion del opcional seleccionado completo.

<a id="opt04"></a>
### OPT-04 — Autoescalado horizontal

**Fuente:** Opcionales!A7:G7 (fila 7). **Modulo:** M01. **Actor:** no especificado en fuente. **Responsable:** José Garcia (derivado de Modulos, no asignacion individual de esta fila).

> Escalado automático por métricas con prueba de carga.

**Implementacion:** Ausente. **Verificacion:** No verificado. **Prioridad:** Sin accion.

- Existe: Hay balanceador y numero de instancias configurado.
- Falta / limite: No se encontro autoescalado por metricas con carga demostrada.
- Siguiente accion y receta no ejecutada: Descartado: no confundir dos instancias fijas con autoescalado ni exigir puntos.
- Evidencia: [`infra/gcp/demo/load-balancer.tf:17`](../../../infra/gcp/demo/load-balancer.tf#L17).
- Decision original: **Descartado**. Seleccionado: **False**. Potencial: **3** puntos; acreditados: **0**. Excluido del plan obligatorio; no implementar por esta auditoria.

<a id="opt05"></a>
### OPT-05 — NoSQL para historial y analítica

**Fuente:** Opcionales!A8:G8 (fila 8). **Modulo:** M02 / M06. **Actor:** no especificado en fuente. **Responsable:** sin asignacion individual.

> Base documental, índices, retención y API paginada y filtrable.

**Implementacion:** Parcial. **Verificacion:** No verificado. **Prioridad:** P1.

- Existe: Mongo guarda solicitudes de recuperacion con indice unico y TTL de 90 dias.
- Falta / limite: No es historial/analitica de operacion; falta API de lectura paginada/filtrable.
- Siguiente accion y receta no ejecutada: Agregar proyeccion documental de historial/analitica, indices/retencion y API paginada con filtros/aislamiento.
- Evidencia: [`backend/src/NexoRuta.Worker/Messaging/PasswordRecoveryMongoConsumer.cs:36`](../../../backend/src/NexoRuta.Worker/Messaging/PasswordRecoveryMongoConsumer.cs#L36); [`backend/src/NexoRuta.Worker/Messaging/PasswordRecoveryMongoConsumer.cs:58`](../../../backend/src/NexoRuta.Worker/Messaging/PasswordRecoveryMongoConsumer.cs#L58).
- Decision original: **Seleccionado**. Seleccionado: **True**. Potencial: **2** puntos; acreditados: **0**. Obligacion del opcional seleccionado completo.

<a id="opt06"></a>
### OPT-06 — Pruebas de carga automatizadas

**Fuente:** Opcionales!A9:G9 (fila 9). **Modulo:** M06. **Actor:** no especificado en fuente. **Responsable:** José Hernández (derivado de Modulos, no asignacion individual de esta fila).

> Escenarios, objetivos previos y sincronización simultánea en ambiente remoto.

**Implementacion:** Parcial. **Verificacion:** No verificado. **Prioridad:** P1.

- Existe: Escenarios k6, perfiles/objetivos, runner y workflow de carga remota.
- Falta / limite: Sin ejecucion remota vigente/sincronizacion simultanea y resultado real; scripts no acreditan puntos.
- Siguiente accion y receta no ejecutada: Ejecutar escenario remoto autorizado con objetivos previos, sync concurrente y artefacto k6 del mismo build.
- Evidencia: [`tests/load/scenario.js:1`](../../../tests/load/scenario.js#L1); [`tests/load/profiles.json:1`](../../../tests/load/profiles.json#L1); [`.github/workflows/load-tests.yml:1`](../../../.github/workflows/load-tests.yml#L1).
- Decision original: **Seleccionado**. Seleccionado: **True**. Potencial: **2** puntos; acreditados: **0**. Obligacion del opcional seleccionado completo.

<a id="opt07"></a>
### OPT-07 — Cobertura de pruebas

**Fuente:** Opcionales!A10:G10 (fila 10). **Modulo:** Transversal. **Actor:** no especificado en fuente. **Responsable:** sin asignacion individual.

> Más de 70 % de cobertura en dominio y aplicación, publicada por pipeline.

**Implementacion:** Parcial. **Verificacion:** No verificado. **Prioridad:** P1.

- Existe: coverlet.collector instalado y multiples suites disponibles.
- Falta / limite: Workflows inspeccionados no recolectan/publican cobertura Domain/Application >70%; paquete instalado no es medicion.
- Siguiente accion y receta no ejecutada: Agregar medicion/publicacion en pipeline y comprobar ambos ensamblados >70% con exclusiones justificadas.
- Evidencia: [`backend/tests/NexoRuta.UnitTests/NexoRuta.UnitTests.csproj:11`](../../../backend/tests/NexoRuta.UnitTests/NexoRuta.UnitTests.csproj#L11); [`.github/workflows/ci.yml:131`](../../../.github/workflows/ci.yml#L131); [`backend/.github/workflows/ci.yml:123`](../../../backend/.github/workflows/ci.yml#L123).
- Decision original: **Seleccionado**. Seleccionado: **True**. Potencial: **2** puntos; acreditados: **0**. Obligacion del opcional seleccionado completo.

<a id="opt08"></a>
### OPT-08 — Pruebas extremo a extremo

**Fuente:** Opcionales!A11:G11 (fila 11). **Modulo:** Transversal. **Actor:** no especificado en fuente. **Responsable:** sin asignacion individual.

> Playwright o equivalente para flujos críticos, integrado al pipeline.

**Implementacion:** Completa. **Verificacion:** No verificado. **Prioridad:** P2.

- Existe: Pruebas navegador Kestrel/Playwright y flujo operativo critico integrados en workflow.
- Falta / limite: No se ejecutaron ni consultaron los resultados CI actuales; no se adjudican puntos de cumplimiento.
- Siguiente accion y receta no ejecutada: Ejecutar flujo critico actual y guardar TRX/capturas; comprobar que usa gitlinks integrados.
- Evidencia: [`backend/.github/workflows/ci.yml:120`](../../../backend/.github/workflows/ci.yml#L120); [`.github/workflows/ci.yml:181`](../../../.github/workflows/ci.yml#L181); [`backend/tests/NexoRuta.IntegrationTests/Envios/CommerceCsvImportKestrelTests.cs:23`](../../../backend/tests/NexoRuta.IntegrationTests/Envios/CommerceCsvImportKestrelTests.cs#L23); [`backend/tests/NexoRuta.IntegrationTests/Reparto/RecepcionDepositoBrowserTests.cs:16`](../../../backend/tests/NexoRuta.IntegrationTests/Reparto/RecepcionDepositoBrowserTests.cs#L16).
- Decision original: **Seleccionado**. Seleccionado: **True**. Potencial: **2** puntos; acreditados: **0**. Obligacion del opcional seleccionado completo.

<a id="opt09"></a>
### OPT-09 — Notificaciones remotas en producción

**Fuente:** Opcionales!A12:G12 (fila 12). **Modulo:** M04. **Actor:** no especificado en fuente. **Responsable:** Nacho (derivado de Modulos, no asignacion individual de esta fila).

> Push real con app cerrada ante reasignación urgente y ciclo de vida de IDs de dispositivo.

**Implementacion:** Parcial. **Verificacion:** No verificado. **Prioridad:** P1.

- Existe: FCM transporte real/worker, registro de dispositivos y avisos por reasignacion; no-send solo Development.
- Falta / limite: Push con app cerrada en produccion y rotacion/revocacion real no acreditados; no-send no cuenta.
- Siguiente accion y receta no ejecutada: Ensayo autorizado FCM de reasignacion urgente con app cerrada, rotar token y comprobar baja; no enviar push productivo en esta auditoria.
- Evidencia: [`backend/src/NexoRuta.Worker/Program.cs:79`](../../../backend/src/NexoRuta.Worker/Program.cs#L79); [`backend/src/NexoRuta.Worker/Messaging/TransporteFcm.cs:5`](../../../backend/src/NexoRuta.Worker/Messaging/TransporteFcm.cs#L5); [`backend/tests/NexoRuta.IntegrationTests/Notificaciones/ReasignacionPushTests.cs:17`](../../../backend/tests/NexoRuta.IntegrationTests/Notificaciones/ReasignacionPushTests.cs#L17); [`mobile/src/NexoRuta.Mobile/Notificaciones/RegistroPushPlataforma.cs:12`](../../../mobile/src/NexoRuta.Mobile/Notificaciones/RegistroPushPlataforma.cs#L12).
- Decision original: **Seleccionado**. Seleccionado: **True**. Potencial: **3** puntos; acreditados: **0**. Obligacion del opcional seleccionado completo.

<a id="opt10"></a>
### OPT-10 — Geocercas

**Fuente:** Opcionales!A13:G13 (fila 13). **Modulo:** M04. **Actor:** no especificado en fuente. **Responsable:** Nacho (derivado de Modulos, no asignacion individual de esta fila).

> Llegada y salida automáticas de parada y análisis de batería.

**Implementacion:** Ausente. **Verificacion:** No verificado. **Prioridad:** Sin accion.

- Existe: Captura GPS existe.
- Falta / limite: No se encontro llegada/salida automatica por geocerca y analisis de bateria.
- Siguiente accion y receta no ejecutada: Descartado: no exigir ni implementar.
- Evidencia: [`mobile/src/NexoRuta.Mobile/Ubicacion/TrackingJornada.cs:3`](../../../mobile/src/NexoRuta.Mobile/Ubicacion/TrackingJornada.cs#L3).
- Decision original: **Descartado**. Seleccionado: **False**. Potencial: **3** puntos; acreditados: **0**. Excluido del plan obligatorio; no implementar por esta auditoria.

<a id="opt11"></a>
### OPT-11 — Impresión Bluetooth

**Fuente:** Opcionales!A14:G14 (fila 14). **Modulo:** M04. **Actor:** no especificado en fuente. **Responsable:** Nacho (derivado de Modulos, no asignacion individual de esta fila).

> Etiqueta o comprobante desde móvil a impresora térmica.

**Implementacion:** Ausente. **Verificacion:** No verificado. **Prioridad:** Sin accion.

- Existe: Etiquetas PDF disponibles desde web.
- Falta / limite: No se encontro impresion Bluetooth termica movil.
- Siguiente accion y receta no ejecutada: Descartado: no exigir ni implementar.
- Evidencia: [`frontend/src/NexoRuta.Commerce/Pages/Envios/Etiquetas.cshtml:1`](../../../frontend/src/NexoRuta.Commerce/Pages/Envios/Etiquetas.cshtml#L1).
- Decision original: **Descartado**. Seleccionado: **False**. Potencial: **2** puntos; acreditados: **0**. Excluido del plan obligatorio; no implementar por esta auditoria.

<a id="opt12"></a>
### OPT-12 — Optimización del orden de paradas

**Fuente:** Opcionales!A15:G15 (fila 15). **Modulo:** M03. **Actor:** no especificado en fuente. **Responsable:** Nacho (derivado de Modulos, no asignacion individual de esta fila).

> Algoritmo o servicio, comparado con el criterio obligatorio del CU-16.

**Implementacion:** Ausente. **Verificacion:** No verificado. **Prioridad:** Sin accion.

- Existe: Orden manual y estimacion vial presentes.
- Falta / limite: Estimacion de ruta fija no es optimizacion comparada con CU16.
- Siguiente accion y receta no ejecutada: Descartado: mantener criterio obligatorio sin exigir optimizacion.
- Evidencia: [`frontend/src/NexoRuta.Backoffice/Pages/Rutas/Planificar.cshtml:117`](../../../frontend/src/NexoRuta.Backoffice/Pages/Rutas/Planificar.cshtml#L117); [`backend/src/NexoRuta.Infrastructure/Reparto/EfRutasRepository.Recorrido.cs:17`](../../../backend/src/NexoRuta.Infrastructure/Reparto/EfRutasRepository.Recorrido.cs#L17).
- Decision original: **Descartado**. Seleccionado: **False**. Potencial: **2** puntos; acreditados: **0**. Excluido del plan obligatorio; no implementar por esta auditoria.

<a id="opt13"></a>
### OPT-13 — API pública para comercios

**Fuente:** Opcionales!A16:G16 (fila 16). **Modulo:** M02. **Actor:** no especificado en fuente. **Responsable:** sin asignacion individual (derivado de Modulos, no asignacion individual de esta fila).

> API documentada/versionada con claves por comercio, sandbox y rate limit diferenciado.

**Implementacion:** Parcial. **Verificacion:** No verificado. **Prioridad:** Sin accion.

- Existe: REST de alta/importacion usa autenticacion de usuario.
- Falta / limite: No hay API publica completa con claves por comercio, sandbox y rate limit diferenciado acreditados.
- Siguiente accion y receta no ejecutada: Descartado: no convertir REST obligatorio CU07 en acreditacion de opcional.
- Evidencia: [`backend/src/NexoRuta.Api/Features/Envios/Controllers/EnviosController.cs:123`](../../../backend/src/NexoRuta.Api/Features/Envios/Controllers/EnviosController.cs#L123); [`backend/src/NexoRuta.Api/Program.cs:134`](../../../backend/src/NexoRuta.Api/Program.cs#L134).
- Decision original: **Descartado**. Seleccionado: **False**. Potencial: **3** puntos; acreditados: **0**. Excluido del plan obligatorio; no implementar por esta auditoria.

<a id="opt14"></a>
### OPT-14 — Banderas de funcionalidad

**Fuente:** Opcionales!A17:G17 (fila 17). **Modulo:** M01. **Actor:** no especificado en fuente. **Responsable:** José Garcia (derivado de Modulos, no asignacion individual de esta fila).

> Activación por tenant en caliente, sin despliegue.

**Implementacion:** Ausente. **Verificacion:** No verificado. **Prioridad:** Sin accion.

- Existe: Reglas configurables no equivalen a feature flags.
- Falta / limite: No se encontro sistema de banderas por tenant en caliente.
- Siguiente accion y receta no ejecutada: Descartado: no exigir; aclaracion PDF no convierte opcion no seleccionada en obligacion.
- Evidencia: [`backend/src/NexoRuta.Domain/ReglasOperativas/VersionReglasOperativas.cs:3`](../../../backend/src/NexoRuta.Domain/ReglasOperativas/VersionReglasOperativas.cs#L3).
- Decision original: **Descartado**. Seleccionado: **False**. Potencial: **2** puntos; acreditados: **0**. Excluido del plan obligatorio; no implementar por esta auditoria.

<a id="opt15"></a>
### OPT-15 — Pruebas de resiliencia

**Fuente:** Opcionales!A18:G18 (fila 18). **Modulo:** Transversal. **Actor:** no especificado en fuente. **Responsable:** sin asignacion individual.

> Cortes deliberados de caché, cola, BD y servicio externo con comparación esperado/observado.

**Implementacion:** Parcial. **Verificacion:** No verificado. **Prioridad:** Sin accion.

- Existe: Hay pruebas de error/reintento/cache y escenarios controlados.
- Falta / limite: No se acredito bateria completa de cortes cache/cola/BD/proveedor con comparacion esperado/observado.
- Siguiente accion y receta no ejecutada: Descartado: no exigir ni dar puntos; preservar pruebas de error utiles existentes.
- Evidencia: [`backend/tests/NexoRuta.IntegrationTests/Caching/DistributedCacheRedisTests.cs:12`](../../../backend/tests/NexoRuta.IntegrationTests/Caching/DistributedCacheRedisTests.cs#L12); [`backend/tests/NexoRuta.UnitTests/Seguimiento/GenerarSeguimientoRetryTests.cs:9`](../../../backend/tests/NexoRuta.UnitTests/Seguimiento/GenerarSeguimientoRetryTests.cs#L9).
- Decision original: **Descartado**. Seleccionado: **False**. Potencial: **2** puntos; acreditados: **0**. Excluido del plan obligatorio; no implementar por esta auditoria.

## Extensiones originales 31–41, separadas del Excel

Fuente: [PDF original](../../cambios-requerimientos/Cambios%20de%20Requerimientos%20Planificados.pdf); texto integro por pagina en [extension-source.json](extension-source.json). El PDF exige 31–36 para todos los equipos y tambien 37–41 para cuatro integrantes. Los titulos siguientes son solo etiquetas de auditoria; se conserva el texto fuente verbatim. El ADR existe, pero la demostracion nativa/avisos/tablero completos no se infiere de su estado declarado.

### Requisito 31 — Estado y resultado por bulto

**Fuente:** PDF pagina fisica 2; numeracion original 31. **Modulo:** M02 / M04 (mapeo de auditoria, no responsabilidad original).

> 31. El estado se registra a nivel de bulto, y el estado del envío se deriva de los estados de sus
> bultos. Se incorpora el estado entregado parcialmente. Las transiciones, tanto de bultos como
> de envíos, siguen definidas de forma declarativa y verificable.

**Implementacion:** Completa. **Verificacion:** No verificado. **Prioridad:** P2.

- Existe: Resultado independiente de custodia, agregacion de envio y matrices declarativas dominio/SQL.
- Falta / limite: No se ejecutaron matrices ni dos visitas en esta auditoria.
- Siguiente accion y receta no ejecutada: Ejecutar envio normal de tres bultos con entrega parcial, agregacion y posterior visita.
- Evidencia: [`backend/src/NexoRuta.Domain/Envios/ResultadoBulto.cs:5`](../../../backend/src/NexoRuta.Domain/Envios/ResultadoBulto.cs#L5); [`backend/src/NexoRuta.Domain/Envios/TransicionesEstadoEnvio.cs:17`](../../../backend/src/NexoRuta.Domain/Envios/TransicionesEstadoEnvio.cs#L17); [`backend/tests/NexoRuta.IntegrationTests/Reparto/OperacionesRepartoHttpTests.Cambios.cs:19`](../../../backend/tests/NexoRuta.IntegrationTests/Reparto/OperacionesRepartoHttpTests.Cambios.cs#L19).

### Requisito 32 — Escaneo, motivos y prueba por bulto sin conectividad

**Fuente:** PDF pagina fisica 2; numeracion original 32. **Modulo:** M02 / M04 (mapeo de auditoria, no responsabilidad original).

> 32. En cada parada, el repartidor indica mediante escaneo qué bultos entrega. Para los que no se
> entregan se registra el motivo, seleccionado del catálogo configurado por el operador. La prueba
> de entrega queda asociada a los bultos efectivamente entregados. Todo esto debe funcionar sin
> conectividad, y la política de resolución de conflictos debe contemplar los casos que se producen
> a nivel de bulto.

**Implementacion:** Completa. **Verificacion:** Bloqueado. **Prioridad:** P2.

- Existe: Escaneo por bulto/motivo publicado, prueba por bulto, SQLite y conflictos versionados.
- Falta / limite: Camara/escaneo/firma offline Android no acreditados en ejecucion.
- Siguiente accion y receta no ejecutada: Entregar 2/3 sin red, reiniciar y sincronizar; revisar prueba solo de entregados y conflicto por bulto.
- Evidencia: [`mobile/src/NexoRuta.Mobile/Presentacion/EntregaViewModel.cs:11`](../../../mobile/src/NexoRuta.Mobile/Presentacion/EntregaViewModel.cs#L11); [`backend/src/NexoRuta.Infrastructure/Reparto/EfOperacionesRepartoRepository.Bultos.cs:8`](../../../backend/src/NexoRuta.Infrastructure/Reparto/EfOperacionesRepartoRepository.Bultos.cs#L8); [`mobile/tests/NexoRuta.Mobile.Application.Tests/EntregaBultosInterfazTests.cs:13`](../../../mobile/tests/NexoRuta.Mobile.Application.Tests/EntregaBultosInterfazTests.cs#L13); [`mobile/src/NexoRuta.Mobile.Storage/RepositorioJornadasSqlite.Capturas.cs:3`](../../../mobile/src/NexoRuta.Mobile.Storage/RepositorioJornadasSqlite.Capturas.cs#L3).

### Requisito 33 — Politica versionada de entrega parcial

**Fuente:** PDF pagina fisica 2; numeracion original 33. **Modulo:** M01 (mapeo de auditoria, no responsabilidad original).

> 33. Cada operador define en sus reglas operativas si admite la entrega parcial y qué sucede con
> los bultos pendientes: una nueva visita, con o sin recargo, o su devolución al comercio. Estas
> reglas son configurables y versionadas, igual que el resto.

**Implementacion:** Completa. **Verificacion:** No verificado. **Prioridad:** P2.

- Existe: Publicacion define entrega parcial, politica de pendientes y recargo; snapshot al admitir.
- Falta / limite: Falta aceptar politicas e importe/momento de recargo elegidos por implementacion.
- Siguiente accion y receta no ejecutada: Publicar politica con/sin cargo/devolucion y comprobar un ciclo simple por alternativa.
- Evidencia: [`backend/src/NexoRuta.Domain/ReglasOperativas/VersionReglasOperativas.cs:8`](../../../backend/src/NexoRuta.Domain/ReglasOperativas/VersionReglasOperativas.cs#L8); [`backend/src/NexoRuta.Infrastructure/Reparto/EfRutasRepository.cs:105`](../../../backend/src/NexoRuta.Infrastructure/Reparto/EfRutasRepository.cs#L105); [`backend/tests/NexoRuta.IntegrationTests/Reparto/OperacionesRepartoHttpTests.Cambios.cs:19`](../../../backend/tests/NexoRuta.IntegrationTests/Reparto/OperacionesRepartoHttpTests.Cambios.cs#L19).

### Requisito 34 — Replanificacion de bultos pendientes

**Fuente:** PDF pagina fisica 2; numeracion original 34. **Modulo:** M02 / M04 (mapeo de auditoria, no responsabilidad original).

> 34. Los bultos pendientes quedan disponibles para ser asignados a una nueva hoja de ruta.

**Implementacion:** Completa. **Verificacion:** No verificado. **Prioridad:** P2.

- Existe: Snapshot de visita y planificacion con solo bultos pendientes conservan historia anterior.
- Falta / limite: Nueva visita normal no ejecutada aqui.
- Siguiente accion y receta no ejecutada: Replanificar el bulto pendiente y comprobar que completados no vuelven a cargarse.
- Evidencia: [`backend/src/NexoRuta.Infrastructure/Reparto/EfRutasRepository.cs:78`](../../../backend/src/NexoRuta.Infrastructure/Reparto/EfRutasRepository.cs#L78); [`backend/src/NexoRuta.Infrastructure/Reparto/EfRutasRepository.cs:96`](../../../backend/src/NexoRuta.Infrastructure/Reparto/EfRutasRepository.cs#L96); [`backend/tests/NexoRuta.IntegrationTests/Reparto/OperacionesRepartoHttpTests.Cambios.cs:19`](../../../backend/tests/NexoRuta.IntegrationTests/Reparto/OperacionesRepartoHttpTests.Cambios.cs#L19).

### Requisito 35 — Avance publico por bulto

**Fuente:** PDF pagina fisica 3; numeracion original 35. **Modulo:** M05 (mapeo de auditoria, no responsabilidad original).

> 35. El seguimiento público muestra el avance de la entrega (por ejemplo, dos de tres bultos entre-
> gados) sin exponer identificadores internos.

**Implementacion:** Completa. **Verificacion:** No verificado. **Prioridad:** P2.

- Existe: DTO/pantalla publicos muestran conteos de entregados/total sin IDs internos.
- Falta / limite: No se abrio enlace ni se inspecciono visualmente ahora.
- Siguiente accion y receta no ejecutada: Abrir enlace despues de 2/3 y revisar conteo y ausencia de IDs privados.
- Evidencia: [`backend/src/NexoRuta.Api/Features/Seguimiento/Contracts/SeguimientoEstadoResponse.cs:8`](../../../backend/src/NexoRuta.Api/Features/Seguimiento/Contracts/SeguimientoEstadoResponse.cs#L8); [`frontend/src/NexoRuta.Tracking/Components/Pages/Seguimiento.razor:71`](../../../frontend/src/NexoRuta.Tracking/Components/Pages/Seguimiento.razor#L71); [`backend/src/NexoRuta.Infrastructure/Seguimiento/Repositories/EfEnlacesSeguimientoRepository.cs:53`](../../../backend/src/NexoRuta.Infrastructure/Seguimiento/Repositories/EfEnlacesSeguimientoRepository.cs#L53).

### Requisito 36 — Avisos de bulto y versionado de contrato

**Fuente:** PDF pagina fisica 3; numeracion original 36. **Modulo:** M05 (mapeo de auditoria, no responsabilidad original).

> 36. Los avisos a comercios incorporan los eventos de bulto. Como los sistemas de los comercios ya
> reciben avisos con el formato actual, el cambio no puede afectarlos, por lo que el contrato de
> los avisos deberá versionarse.

**Implementacion:** Parcial. **Verificacion:** No verificado. **Prioridad:** P1.

- Existe: Outbox v2 para bulto/operacion y topic dedicado; conserva contrato/topic v1 e inbox idempotente.
- Falta / limite: El aviso a sistema externo original CU28 esta ausente; inbox propio no demuestra no ruptura de consumidores HTTP.
- Siguiente accion y receta no ejecutada: Probar consumidores v1/v2 y completar entrega HTTP del comercio conservando versionado explicito exigido por PDF.
- Evidencia: [`backend/src/NexoRuta.Worker/Messaging/KafkaEnvioCreadoPublisher.cs:150`](../../../backend/src/NexoRuta.Worker/Messaging/KafkaEnvioCreadoPublisher.cs#L150); [`backend/src/NexoRuta.Worker/Messaging/CommerceNoticeConsumer.cs:17`](../../../backend/src/NexoRuta.Worker/Messaging/CommerceNoticeConsumer.cs#L17); [`backend/src/NexoRuta.Worker/Messaging/OutboxHandlerRegistry.cs:53`](../../../backend/src/NexoRuta.Worker/Messaging/OutboxHandlerRegistry.cs#L53).

### Requisito 37 — Solicitud de retiro desde portal y API

**Fuente:** PDF pagina fisica 3; numeracion original 37. **Modulo:** M02 / M03 / M04 / M05 / M06 (mapeo de auditoria, no responsabilidad original).

> 37. El comercio solicita el retiro desde el portal y por API, indicando los bultos, el domicilio, la
> franja horaria y el motivo.

**Implementacion:** Completa. **Verificacion:** No verificado. **Prioridad:** P2.

- Existe: Commerce comparte formulario de alta en ruta retiros/crear y POST /api/retiros con bultos/domicilio/franja/motivo.
- Falta / limite: Formulario/API no ejecutados por este worker.
- Siguiente accion y receta no ejecutada: Solicitar retiro de un bulto desde portal y API, reabrir y comprobar datos.
- Evidencia: [`backend/src/NexoRuta.Api/Features/Envios/Controllers/EnviosController.cs:113`](../../../backend/src/NexoRuta.Api/Features/Envios/Controllers/EnviosController.cs#L113); [`frontend/src/NexoRuta.Commerce/Components/Features/Envios/Pages/CrearEnvio.razor:2`](../../../frontend/src/NexoRuta.Commerce/Components/Features/Envios/Pages/CrearEnvio.razor#L2); [`backend/tests/NexoRuta.IntegrationTests/Reparto/OperacionesRepartoHttpTests.Retiros.cs:24`](../../../backend/tests/NexoRuta.IntegrationTests/Reparto/OperacionesRepartoHttpTests.Retiros.cs#L24).

### Requisito 38 — Ciclo de vida propio de retiro

**Fuente:** PDF pagina fisica 3; numeracion original 38. **Modulo:** M02 / M03 / M04 / M05 / M06 (mapeo de auditoria, no responsabilidad original).

> 38. El retiro tiene su propio ciclo de vida dentro de la máquina de estados y convive con el de los
> envíos. A modo de referencia, sus estados podrían ser: solicitado, asignado a ruta, retirado, no
> retirado, en depósito y entregado al comercio.

**Implementacion:** Completa. **Verificacion:** No verificado. **Prioridad:** P2.

- Existe: Ciclo declarativo RetiroSolicitado/Asignado/Fallido/Retirado/Deposito/EntregadoComercio.
- Falta / limite: No se ejecuto ciclo normal ni fallido/reprogramado aqui.
- Siguiente accion y receta no ejecutada: Ejecutar retiro y retiro fallido con reprogramacion, sin convertirlo en devolucion de entrega.
- Evidencia: [`backend/src/NexoRuta.Domain/Envios/TransicionesEstadoEnvio.cs:19`](../../../backend/src/NexoRuta.Domain/Envios/TransicionesEstadoEnvio.cs#L19); [`backend/src/NexoRuta.Infrastructure/Reparto/EfRutasRepository.Recepcion.cs:27`](../../../backend/src/NexoRuta.Infrastructure/Reparto/EfRutasRepository.Recepcion.cs#L27); [`backend/tests/NexoRuta.IntegrationTests/Reparto/OperacionesRepartoHttpTests.Retiros.cs:24`](../../../backend/tests/NexoRuta.IntegrationTests/Reparto/OperacionesRepartoHttpTests.Retiros.cs#L24).

### Requisito 39 — Rutas mixtas y capacidad por tramo

**Fuente:** PDF pagina fisica 3; numeracion original 39. **Modulo:** M02 / M03 / M04 / M05 / M06 (mapeo de auditoria, no responsabilidad original).

> 39. Las hojas de ruta pasan a ser mixtas, con paradas de entrega y paradas de retiro. La validación
> de capacidad del vehículo debe considerar cómo varía la carga a lo largo del recorrido, ya que
> los bultos retirados ocupan lugar desde la parada en que se suben.

**Implementacion:** Completa. **Verificacion:** No verificado. **Prioridad:** P2.

- Existe: Ruta mezcla entregas/retiros; capacidad por tramo y control fisico al retirar.
- Falta / limite: Sin recorrido mixto real ni Android observado en este worker.
- Siguiente accion y receta no ejecutada: Ruta simple entrega->retiro dentro de capacidad, rechazar retiro previo que excede carga.
- Evidencia: [`backend/src/NexoRuta.Domain/Reparto/CapacidadCarga.cs:8`](../../../backend/src/NexoRuta.Domain/Reparto/CapacidadCarga.cs#L8); [`backend/src/NexoRuta.Infrastructure/Reparto/EfRutasRepository.cs:82`](../../../backend/src/NexoRuta.Infrastructure/Reparto/EfRutasRepository.cs#L82); [`backend/tests/NexoRuta.IntegrationTests/Reparto/OperacionesRepartoHttpTests.Retiros.cs:24`](../../../backend/tests/NexoRuta.IntegrationTests/Reparto/OperacionesRepartoHttpTests.Retiros.cs#L24).

### Requisito 40 — Captura de retiro con foto/firma offline

**Fuente:** PDF pagina fisica 3; numeracion original 40. **Modulo:** M02 / M03 / M04 / M05 / M06 (mapeo de auditoria, no responsabilidad original).

> 40. La aplicación del repartidor registra el retiro con la identificación del bulto, una fotografía de
> su estado y la firma de quien lo entrega, también sin conectividad.

**Implementacion:** Completa. **Verificacion:** Bloqueado. **Prioridad:** P2.

- Existe: Captura de retiro exige foto/firma e identificacion, almacenadas cifradas/diario antes de envio.
- Falta / limite: Captura nativa offline no acreditada; tests portables no equivalen a Android.
- Siguiente accion y receta no ejecutada: Retirar un bulto sin red con escaneo/foto/firma, reiniciar y sincronizar sin perder prueba.
- Evidencia: [`mobile/src/NexoRuta.Mobile/Presentacion/EntregaViewModel.cs:25`](../../../mobile/src/NexoRuta.Mobile/Presentacion/EntregaViewModel.cs#L25); [`backend/src/NexoRuta.Infrastructure/Reparto/EfOperacionesRepartoRepository.Bultos.cs:30`](../../../backend/src/NexoRuta.Infrastructure/Reparto/EfOperacionesRepartoRepository.Bultos.cs#L30); [`mobile/src/NexoRuta.Mobile.Storage/RepositorioJornadasSqlite.Capturas.cs:3`](../../../mobile/src/NexoRuta.Mobile.Storage/RepositorioJornadasSqlite.Capturas.cs#L3); [`mobile/tests/NexoRuta.Mobile.Application.Tests/EntregaBultosInterfazTests.cs:13`](../../../mobile/tests/NexoRuta.Mobile.Application.Tests/EntregaBultosInterfazTests.cs#L13).

### Requisito 41 — Tarifa, seguimiento, avisos, tablero y reportes de retiro

**Fuente:** PDF pagina fisica 3; numeracion original 41. **Modulo:** M02 / M03 / M04 / M05 / M06 (mapeo de auditoria, no responsabilidad original).

> 41. El retiro tiene su propia tarifa dentro del cuadro tarifario. El comprador puede seguirlo me-
> diante el mismo enlace público que se utiliza para los envíos, y tanto los avisos a comercios
> como el tablero de operación y los reportes deben incorporarlo.

**Implementacion:** Parcial. **Verificacion:** No verificado. **Prioridad:** P1.

- Existe: Modalidad tarifaria Retiro, seguimiento publico y avisos/inbox, reporte por tipo.
- Falta / limite: El tablero vivo CU29 y HTTP de avisos CU28 no existen; reporte basico no cubre CU30 integral.
- Siguiente accion y receta no ejecutada: Incorporar retiro a tablero real, contrato HTTP y reportes/liquidacion una vez completados esos circuitos.
- Evidencia: [`backend/src/NexoRuta.Domain/Tarifas/CalculadoraTarifas.cs:3`](../../../backend/src/NexoRuta.Domain/Tarifas/CalculadoraTarifas.cs#L3); [`backend/src/NexoRuta.Api/Features/Envios/Controllers/ReporteOperacionesController.cs:13`](../../../backend/src/NexoRuta.Api/Features/Envios/Controllers/ReporteOperacionesController.cs#L13); [`frontend/src/NexoRuta.Tracking/Components/Pages/Seguimiento.razor:70`](../../../frontend/src/NexoRuta.Tracking/Components/Pages/Seguimiento.razor#L70); [`backend/src/NexoRuta.Worker/Messaging/CommerceNoticeConsumer.cs:8`](../../../backend/src/NexoRuta.Worker/Messaging/CommerceNoticeConsumer.cs#L8).

## Checklist de cierre de esta auditoria

- [x] Inventario completo, nombres y filas originales: 93/93; extensiones separadas: 11/11.
- [x] Dos ejes independientes, puntos potenciales/acreditados separados y descartados conservados.
- [x] Citas path:line verificadas; no referencias sin resolver.
- [x] Reglas de frontend y DESIGN.md leidas antes de revisar marcado.
- [ ] Resultados finales de Frontend y circuito HTTP sintetico del equipo padre incorporados al cierre general.
- [ ] Revision visual/teclado/foco/320px/zoom y hardware Android con autorizacion de interaccion.
- [ ] Ensayos remotos/FCM productivo solo con autorizacion explicita posterior.

## Key Learnings:

1. La bandeja Kafka de Commerce no implementa el HTTP firmado externo exigido por CU28 y NFR09.
2. El reporte agregado por tipo y estado no constituye cumplimiento, liquidacion ni cuenta corriente por comercio.
3. Las pruebas portables de Mobile no verifican camara, biometria, GPS en segundo plano ni push con app cerrada.
