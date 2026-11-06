# Cobertura de la demo

Inventario contrastado con el PDF (§4–7 y §9.3) y la planilla de `docs/alcance`. Indica dónde mostrar o constatar cada requisito; no declara aceptación ni una ejecución E2E nueva. Contrato detallado: [workflow.json](workflow.json).

`implementado_pendiente_ensayo`: hay recorrido/código, falta ejecutarlo en remoto. `parcial`: solo parte disponible. `brecha`: falta funcionalidad. `requiere_evidencia`: revisar artefactos/servicios del entorno y SHA. `no_seleccionado`: opcional descartado en la planilla.

## CU

| ID | Feature | Escenas | Situación |
|---|---|---|---|
| CU-01 | Comercios y usuarios | `CFG-01` | implementado_pendiente_ensayo |
| CU-02 | Zonas y franjas | `CFG-02` | implementado_pendiente_ensayo |
| CU-03 | Tarifas | `CFG-03`, `EXT-01` | implementado_pendiente_ensayo |
| CU-04 | Reglas | `CFG-04`, `EXT-01` | implementado_pendiente_ensayo |
| CU-05 | Identidad visual | `CFG-05`, `EXT-04` | parcial |
| CU-06 | Flota | `CFG-06`, `RUT-04`, `CIE-03` | parcial |
| CU-07 | Alta individual/CSV/API | `WEB-01`, `WEB-02`, `WEB-03` | implementado_pendiente_ensayo |
| CU-08 | Bultos | `WEB-01`, `WEB-02`, `WEB-04` | implementado_pendiente_ensayo |
| CU-09 | Precio | `WEB-01`, `WEB-02`, `EXT-01` | implementado_pendiente_ensayo |
| CU-10 | Recepción | `DEP-01`, `DEP-02` | parcial |
| CU-11 | Estados | `DEP-01`, `RUT-04`, `MOV-02`, `MOV-04`, `MOV-06`, `CIE-01`, `CIE-03`, `EXT-02`, `EXT-03`, `EXT-04`, `TEC-01` | implementado_pendiente_ensayo |
| CU-12 | Historia | `DEP-01`, `MOV-06`, `TEC-01` | parcial |
| CU-13 | Rutas | `RUT-03` | implementado_pendiente_ensayo |
| CU-14 | Restricciones | `CFG-06`, `RUT-01`, `RUT-03` | parcial |
| CU-15 | Exclusión | `RUT-02` | implementado_pendiente_ensayo |
| CU-16 | Orden | `RUT-03` | implementado_pendiente_ensayo |
| CU-17 | Despacho | `RUT-04` | implementado_pendiente_ensayo |
| CU-18 | Descarga offline | `MOV-01`, `MOV-03` | implementado_pendiente_ensayo |
| CU-19 | Escaneo carga | `MOV-02` | implementado_pendiente_ensayo |
| CU-20 | Entrega | `MOV-04`, `MOV-06`, `EXT-03` | implementado_pendiente_ensayo |
| CU-21 | Intento fallido | `MOV-05`, `MOV-06`, `CIE-01` | implementado_pendiente_ensayo |
| CU-22 | Rendición/devolución | `CIE-01`, `CIE-02`, `CIE-03` | implementado_pendiente_ensayo |
| CU-23 | Posición | `MOV-01`, `MOV-06` | implementado_pendiente_ensayo |
| CU-24 | Sincronización/conflictos | `MOV-03`, `MOV-04`, `MOV-05`, `MOV-06`, `CIE-02`, `EXT-02` | implementado_pendiente_ensayo |
| CU-25 | Seguimiento | `WEB-04`, `EXT-04`, `GAP-01` | parcial |
| CU-26 | Reprogramación pública | `GAP-02` | brecha |
| CU-27 | Avisos destinatario | `GAP-03` | brecha |
| CU-28 | Webhooks | `GAP-03` | brecha |
| CU-29 | Tablero vivo | `GAP-04` | brecha |
| CU-30 | Reportes/liquidación | `GAP-04` | brecha |

## AP

| ID | Feature | Escenas | Situación |
|---|---|---|---|
| AP-01 | Incidencias | `DEP-02`, `CIE-01`, `CIE-03`, `GAP-05` | parcial |
| AP-02 | Etiquetas | `WEB-04` | implementado_pendiente_ensayo |
| AP-03 | Consulta propia | `WEB-01`, `WEB-04`, `MOV-06` | implementado_pendiente_ensayo |
| AP-04 | Devoluciones comercio | `CIE-01`, `CIE-03`, `GAP-05` | parcial |
| AP-05 | Suscripción avisos | `GAP-03` | brecha |
| AP-06 | Cuenta corriente | `GAP-04` | brecha |
| AP-07 | Ventana estimada | `GAP-01` | brecha |
| AP-08 | Navegación paradas | `MOV-01` | implementado_pendiente_ensayo |
| AP-09 | Cierre diario | `GAP-04` | brecha |

## NFR

| ID | Feature | Escenas | Situación |
|---|---|---|---|
| NFR-01 | Arquitectura | `PRE-01`, `TEC-03` | requiere_evidencia |
| NFR-02 | Web | `CFG-05`, `WEB-01`, `TEC-03` | requiere_evidencia |
| NFR-03 | Seguridad | `PRE-01`, `CFG-01`, `WEB-03` | requiere_evidencia |
| NFR-04 | Persistencia | `PRE-01`, `CFG-06`, `RUT-01`, `RUT-02`, `EXT-02`, `TEC-01` | requiere_evidencia |
| NFR-05 | Multitenancy | `CFG-01`, `CFG-02`, `CFG-05`, `RUT-02` | requiere_evidencia |
| NFR-06 | Configurabilidad | `CFG-02`, `CFG-03`, `CFG-04`, `EXT-01` | requiere_evidencia |
| NFR-07 | Caché | `TEC-02` | requiere_evidencia |
| NFR-08 | Mensajería | `WEB-04`, `EXT-04`, `TEC-02` | requiere_evidencia |
| NFR-09 | Avisos comercio | `GAP-03` | brecha |
| NFR-10 | Tiempo real | `GAP-04` | brecha |
| NFR-11 | MAUI | `PRE-01`, `CFG-04`, `MOV-01`, `MOV-03`, `CIE-02`, `EXT-05` | requiere_evidencia |
| NFR-12 | Observabilidad | `TEC-02` | requiere_evidencia |
| NFR-13 | Escalabilidad | `PRE-01`, `TEC-02`, `TEC-04` | requiere_evidencia |
| NFR-14 | Nube/IaC | `PRE-01`, `TEC-04` | requiere_evidencia |
| NFR-15 | Calidad | `TEC-01`, `TEC-03` | requiere_evidencia |

## OPT

| ID | Feature | Escenas | Situación |
|---|---|---|---|
| OPT-01 | Seguimiento independiente | Descartado | no_seleccionado |
| OPT-02 | gRPC | Descartado | no_seleccionado |
| OPT-03 | Kafka/flota | `GAP-06` | parcial |
| OPT-04 | Autoescalado | Descartado | no_seleccionado |
| OPT-05 | NoSQL | `GAP-06` | parcial |
| OPT-06 | Carga | `TEC-04` | requiere_evidencia |
| OPT-07 | Cobertura | `TEC-03` | requiere_evidencia |
| OPT-08 | E2E | `TEC-03` | requiere_evidencia |
| OPT-09 | Push | `EXT-05` | requiere_evidencia |
| OPT-10 | Geocercas | Descartado | no_seleccionado |
| OPT-11 | Bluetooth | Descartado | no_seleccionado |
| OPT-12 | Optimización | Descartado | no_seleccionado |
| OPT-13 | API pública | Descartado | no_seleccionado |
| OPT-14 | Flags | Descartado | no_seleccionado |
| OPT-15 | Resiliencia | Descartado | no_seleccionado |

## Escenarios anunciados de defensa (PDF §9.3)

| Escenario | Recorrido/evidencia |
|---|---|
| Caída de una API con tráfico | TEC-04; evidencia de continuidad en dos API; corte coordinado fuera de la demo compartida. |
| Entregas e incidencias sin red | MOV-03–06 y CIE-01–03. |
| Conflicto de sincronización | EXT-02; versión obsoleta, Conflicto y custodia conservada. |
| Dos operadores simultáneos | CFG-01–05; contraste B/C2 en WEB-01/MOV-06. |
| Cambio tarifa/regla en caliente | EXT-01; publicaciones anteriores y nuevas. |
| Receptor de avisos caído y recuperación | GAP-03: CU-28 no implementado. |
| Destruir/reconstruir con IaC | TEC-04; entorno efímero autorizado o ensayo previo, conservando datos de demo. |

Los seis opcionales seleccionados suman14 puntos teóricos; esta tabla no adjudica puntos. OPT-03/05 parciales. OPT-06 tiene un run remoto reciente exitoso que debe revisarse por escenario/SLO: [estado observado](estado-observado.md). No usar la auditoría histórica como estado de carga actual.

\n