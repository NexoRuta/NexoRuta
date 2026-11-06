# Excel source selection and complete inventory

Audit date: 2026-11-05. Local read-only source audit; no workbook, macro, product source, service, index or commit was modified.

## Selected source

`docs/alcance/Calcs/Casos de Uso - Responsables.xlsm` is the latest **available internal content revision**, not a confirmed copy of the user-referenced `(2).xlsm`. The referenced filename was not found. All sources remain intact.

- SHA-256: `8de7fcf3c84c113788b71a89e5e51cc852aafd0e690a0d35f4b944e855220cf4`.
- Size: 48358 bytes. Filesystem modified UTC: 2026-11-03T03:30:17.839401+00:00.
- Office internal modified: `2026-11-03T00:30:17Z`; revision `13`.
- Filename and filesystem timestamp alone were not used as content-age evidence.

### Search boundaries

Recursively searched Downloads, Desktop, Documents, OneDrive, the active NexoRuta workspace and sibling NexoRuta-consolidacion-cu workspace. Dependency/build/git directories were skipped (`.git`, `node_modules`, `bin`, `obj`, `.venv`, `venv`, `packages`). Three legacy Documents junctions (Mi m?sica, Mis im?genes, Mis v?deos) denied access. This is not a whole-disk or cloud-provider search.

### Workbook comparison

| Candidate | File modified UTC | Office modified UTC / revision | SHA-256 | Decision |
| --- | --- | --- | --- | --- |
| `C:\Users\Josec\NexoRuta\docs\alcance\Calcs\Casos de Uso - Responsables.xlsm` | 2026-11-03T03:30:17.839401+00:00 | 2026-11-03T00:30:17Z / 13 | `8de7fcf3c84c113788b71a89e5e51cc852aafd0e690a0d35f4b944e855220cf4` | Selected: newer content revision |
| `C:\Users\Josec\NexoRuta-consolidacion-cu\docs\alcance\Calcs\Casos de Uso - Responsables.xlsm` | 2026-11-04T21:16:37.896270+00:00 | 2026-11-02T20:40:52Z / 12 | `fe1a0843dd8a7c5075414fc2796ab65c630e955b598edb123ce1840a1f9de389` | Older content; byte-identical to git HEAD |

Git HEAD `4e5c233dc751736ed59cc234582f157f5c9c278a` workbook SHA-256: `fe1a0843dd8a7c5075414fc2796ab65c630e955b598edb123ce1840a1f9de389` (48413 bytes). Baseline was read through `git show` in memory, without checkout or export.

Exactly one nonempty cell content difference exists against HEAD: `No funcionales!F13` (NFR-10) changed from `SignalR con autenticaci?n, autorizaci?n, aislamiento tenant y varias instancias API.` to literal `e`. Module responsibilities and optional row decisions already exist in HEAD; they are not changes unique to this modified file.

Six older PDF sheet exports were found in Downloads, all dated 2026-10-04. Their full filenames, sizes, UTC timestamps and hashes are retained in `inventory.json` under `source_selection.candidates`. They do not supersede the complete workbook.

## Inventory coverage

| Sheet (original name) | Entries | Original rows |
| --- | ---: | --- |
| Módulos | 6 | 4?9 |
| CU obligatorios | 30 | 4?33 |
| Alcance aplicaciones | 9 | 4?12 |
| Dependencias | 24 | 4?27 |
| No funcionales | 15 | 4?18 |
| Opcionales | 15 | 4?18 |

Total: **6 sheets, 6 modules and 93 requirement/dependency rows**: CU01?CU30 (30), AP01?AP09 (9), D01?D24 (24), NFR01?NFR15 (15), OPT01?OPT15 (15). No missing or duplicate expected IDs. All nonempty cells, original IDs, headers, names, module, actor, requirement, points, decisions and row locators are preserved in `inventory.json`.

Normalized IDs remove only the source hyphen; `original_id` preserves the exact identifier. Null means a field does not exist in that row, not an assessment of implementation. Dependency rows do not have a title; `name` remains null and the original dependency type, reason, contract and risk are preserved.

### Responsibilities

| Module | Original name | Source owner | Cell |
| --- | --- | --- | --- |
| M01 | Administración y configuración | José Garcia | M?dulos!F4 |
| M02 | Envíos y depósito | Not assigned (blank source cell) | M?dulos!F5 |
| M03 | Planificación, flota y despacho | Nacho | M?dulos!F6 |
| M04 | Ejecución y sincronización móvil | Nacho | M?dulos!F7 |
| M05 | Seguimiento y comunicaciones | José Hernández | M?dulos!F8 |
| M06 | Monitoreo y liquidaciones | José Hernández | M?dulos!F9 |

There is no per-CU responsibility column. An exact single-module match inherits only the module assignment with explicit `responsibility_source`; multi-module and transversal optional rows are not assigned to a person by guess. The blank M02 responsibility is preserved. The M?dulos!A11 note still says assignments are open despite populated owner cells.

## Selected optionals: row decisions override stale prose

`Opcionales!A1` says none are selected; `M?dulos!A13` says optionals remain unselected. Both are stale relative to actual row-level decisions. The following six rows explicitly say `Seleccionado`:

| ID | Original optional name | Points | Decision cell |
| --- | --- | ---: | --- |
| OPT-03 | Kafka para eventos de flota | 3 | Opcionales!F6 |
| OPT-05 | NoSQL para historial y analítica | 2 | Opcionales!F8 |
| OPT-06 | Pruebas de carga automatizadas | 2 | Opcionales!F9 |
| OPT-07 | Cobertura de pruebas | 2 | Opcionales!F10 |
| OPT-08 | Pruebas extremo a extremo | 2 | Opcionales!F11 |
| OPT-09 | Notificaciones remotas en producción | 3 | Opcionales!F12 |

**14 selected points**. The remaining 9 optionals explicitly say `Descartado`. Selection is scope intent, not implementation or earned points. The original laboratory PDF ?7, physical page 9, requires 12 points for four-member teams (8 for three-member teams), with no points for partially implemented optionals.

## Original PDF corroboration and source defects

- `docs/alcance/Laboratorio__NET_2026.pdf`, ?6.10, physical page 7, confirms SignalR realtime dashboard, authentication/authorization, tenant isolation and operation across multiple API instances. It corroborates the baseline NFR-10 text. The current Excel `e` is preserved and flagged, never silently repaired.
- The workbook summaries are not substitutes for full PDF acceptance conditions. No compliance conclusion is drawn solely from a title or selected flag.
- The subsequent change PDF is extracted separately in `extension-source.json`, retaining every physical page and source hash. New numbered requirements 31?36 concern partial package delivery (physical pages 2?3); 37?41 concern home pickup for four-member teams (physical page 3). They are absent from the Excel and are not invented as Excel CU rows. The change document also contains required runtime demonstrations/ADR and cache/feature-flag clarifications.

## Verification and limitations

- Automated structural check: all expected ID ranges present exactly once, 6 original sheets preserved, all 15 optional decisions present, selected sum 14, exactly one baseline cell change.
- Source integrity: source workbook hash rechecked after extraction; no source files were saved or opened in Excel. Macros were not executed.
- PDF text extraction: original section 6.10 and section 7 inspected; change PDF all five physical pages extracted. No PDF visual-layout claim is made.
- Compilation / HTTP / browser automation / visual review: not applicable to this source extraction. Product implementation/runtime compliance is assessed separately.
- Pending source proof: the referenced `(2).xlsm` is unavailable in searched local locations. If supplied, compare cell contents and timestamps before replacing this selection; do not assume it matches.

## Artifacts

- `inventory.json`: normalized complete Excel inventory, all source cells, metadata/hashes, baseline diff, source search evidence and PDF clarifications.
- `extension-source.json`: full embedded text of the subsequent requirement-change PDF, physical page locators and source SHA-256.
