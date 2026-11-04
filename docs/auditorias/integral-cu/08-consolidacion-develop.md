# Consolidation into develop — 4 November 2026

Engineering integration is not acceptance of any CU. All 30 CU remain pending human validation. This supplements the historical audit, without rewriting its observed RED results.

## Initial source inventory

| Source | Root | Backend | Frontend | Mobile |
|---|---|---|---|---|
| Habitual fix/cu0708 | 486633d | 9ad5c86 | a65c131 | 74a25f1 |
| Remote develop | 6c3d624 | 947b3f7 | 5c1c008 root pin | 4b9032b root pin |
| Optional browsers | 13aefdb | bf4da61 | 1ca0172 | 74a25f1 |
| Independent audit | 6d6ae29 | 5fbefe1 | 9c07de4 | 74a25f1 |
| Older CU08/CU09/redesign | a697d45 | 4462a9f | 1a5a670 | 5302b20 |

- **Included by history:** older CU08/CU09/redesign is already an ancestor of current work and remote develop. No separate cherry-pick or replacement design is needed.
- **Cumulative chain:** initial local implementation → CU12/14/15/16 → CU10 → session → Fleet/Depot regression → CU11 → optional browsers → audit. These are not independent branches to merge mechanically.
- **Equivalent trees:** frontend root pin 5c1c008 equals remote develop 1a2e698; mobile root pin 4b9032b equals remote develop d570ddb. Retain published merge ancestry.
- **Develop-exclusive work retained:** observability, Redis distributed cache/tests, remote-load infrastructure, supervision and CI corrections. No remote load or deployment is authorized here.
- **Audit-chain-exclusive work retained:** labels, coverage/operator alternatives, manual-window history/concurrency, scanned receiving/history, session rejection ordering, shipment-state policy, browser harnesses and the two RED reproductions.
- **Joint conflict resolution:** backend IntegrationTests lock must retain Redis/Pipelines and PdfPig/ZXing from the combined project graph. Root gitlinks are resolved only after child integration. Frontend startup retains instrumentation and newer session behavior.
- **Local work outside publication:** the uncommitted CU workbook is privately backed up and remains a local modification, not silently included.

## Correction scope

| Finding | Engineering outcome sought | Human acceptance |
|---|---|---|
| H01 | Bounded actual PNG/JPEG decoding before evidence persistence; preserve encryption, positive photo/signature and transactions | Pending |
| H02 | Release late JS resources and ignore disposed callbacks | Pending |
| H07 | Deliberate consumer locks, keeping locked-mode | Pending |
| H08 | Explicit PDF contract/content checks; preserve JSON DTO and layer rules | Pending |
| H09 | Verify selected HEAD gitlinks; separate source selection and installation | Pending |

H03–H06 are not feature work in this task. H03–H05 remain functional gaps. H06 was absent from the audited branch, while remote develop contains a separate distributed-cache implementation. Integration and automated proof do not approve NFR-07 or erase the historical observation.

## Decisions reserved for manual examples

- **D-P01:** agree temporal commitment, accepted/rejected examples and actors before treating estimates or manual windows as contractual promises.
- **D-P02:** agree real receiving discrepancies through physical-custody examples. Do not fabricate reconciliations, permit departures artificially or substitute returns for first admission.

## Verification and runtime

**Partial engineering result; not ready for publication or human acceptance.** Backups, credentials, logs, TRX and captures remain private.

| Check | Observed result |
|---|---|
| Backend focused fixes | Original H01 unchanged RED→GREEN; Unit 328/328, Architecture 4/4, strict evidence HTTP 8/8; locked restore/Release build pass |
| Frontend | Original H02 unchanged RED→GREEN; final full suite 496/496 with live OpenAPI and all five browser flags; Node 21/21; locked restore/Release build pass |
| Mobile | Portable 217/217 with original locked restores; Android arm64 Release APK built, not installed; three existing Mapbox 16 KB warnings remain |
| Root/CI tooling | GCP 169 distinct tests covered on applicable Windows/Linux platforms; per-platform skips and Windows POSIX failure retained; actionlint four repos, shell syntax, H09 fixtures, isolated CloudSQL and release Python checks pass |
| Initial Windows integration | 687 cases: 685 pass / 2 fail / 0 skip; bad positive PNG fixture corrected after isolated reproduction, affected matrix 12/12 pass; isolated lock-timeout case passed unchanged |
| Canonical Linux integration | 687 cases: 646 pass / 41 fail / 0 skip; browsers 9 cases: 6 pass / 3 fail / 0 skip; 696 distinct completed cases, no overlapping diagnostic runs added |

The required live OpenAPI comparison exposed two existing CU10 paths, six schemas and the Recepcion tag missing from the versioned snapshot. The additive synchronization preserves every previous path/schema and the stable server URL. Final live comparison matches 115 paths.

The Linux failure evidence includes a same-connection backward wall-clock jump of approximately 132 seconds, followed by `token_not_yet_valid`. The admission screenshot is an expired-session login, not a demonstrated map regression. Other Npgsql timeouts/unauthorized results do not all have proven causality. No skew, timeout, assertion or skip was weakened.

Windows UTC matches the runtime clock reference; Docker guest UTC is approximately 132–133 seconds ahead. A supported `docker desktop restart --timeout 180` completed, preserving the 15 original container identities, images and mounts, but **did not correct the offset**. Five non-autostarting original containers were explicitly started again, without recreation. Ubuntu-22.04 and docker-desktop are both running under WSL2. A wider/shared-clock recovery requires a consequential scope decision before proceeding; no `wsl --shutdown`, privileged clock mutation or Windows time change was performed.

Two private custom PostgreSQL backups were generated and fully parsed with `pg_restore`; the latest is before the Desktop recovery. Only pending migration identified: `20261103000000_AddDepotParcelReceipts`; **not applied**. No excluded human records were queried and no physical event was registered. Habitual sources still remain on fix/cu0708; no integration/develop push has been performed. Emulator-5554 is absent, so installed Mobile version could not be read; app/data were not changed.

OpenTofu is unavailable; no remote infrastructure/load/deployment or published Cloud configuration was changed. Full pipeline PASS, remote publication, clean remote clone and habitual develop rollout remain pending.

## First manual step

Open http://localhost:5101, sign in with the intended operator administrator and begin CU-01 using a new identifiable validation actor. Follow the circuits in 03-guia-manual.md and record actor/date/commit/evidence. Do not reuse the two excluded human-test records.

## Local branch inventory before publication

All 55 local tips are covered by the selected child integration commits or by the intended union of the two root merge parents. No local branch history needs discarding or an extra blind merge. This ancestry proof does not claim every historical behavior was accepted. Original checkout/submodules remain on fix/cu0708 until final publication and service preparation.


### .

| Local branch | Commit | Upstream | Tracking |
|---|---|---|---|
| checkpoint/codex-cloud-20261102 | 8323f29 | origin/checkpoint/codex-cloud-20261102 | - |
| develop | ec424f3 | origin/develop | [behind 26] |
| feature/cu01-gestion-accesos | a3a8742 | origin/feature/cu01-gestion-accesos | [ahead 1] |
| feature/cu02 | 3b67572 | origin/feature/cu02 | - |
| feature/cu03 | 737526f | origin/feature/cu03 | - |
| feature/cu04 | 54603ce | origin/feature/cu04 | - |
| feature/cu05 | 058ab30 | origin/feature/cu05 | - |
| feature/cu07 | 29483ce | origin/feature/cu07 | - |
| feature/integracion-mensajeria | 89a5770 | origin/feature/integracion-mensajeria | [gone] |
| feature/m05-seguimiento | 2d9630c | origin/develop | [behind 206] |
| feature/mailpitypassword | 9be8e1d | origin/feature/mailpitypassword | - |
| feature/sync-feature-first-submodules | 1f0dd22 | origin/feature/sync-feature-first-submodules | [gone] |
| fix/cu0708 | 486633d | origin/fix/cu0708 | - |
| integration/consolidacion-cu | 6c3d624 | origin/develop | - |
| main | 92ae4c8 | origin/main | [behind 206] |

### backend

| Local branch | Commit | Upstream | Tracking |
|---|---|---|---|
| checkpoint/codex-cloud-20261102 | 5bd165c | origin/checkpoint/codex-cloud-20261102 | - |
| develop | 0e31790 | origin/develop | [behind 33] |
| feature/cu01-gestion-accesos | 710a7a3 | origin/feature/cu01-gestion-accesos | - |
| feature/cu02 | b5d4f3e | origin/feature/cu02 | - |
| feature/cu03 | cceb4ed | origin/feature/cu03 | - |
| feature/cu04 | 0c08470 | origin/feature/cu04 | - |
| feature/cu05 | 8920574 | origin/feature/cu05 | - |
| feature/cu07 | 83cfb12 | origin/feature/cu07 | - |
| feature/deploy | 363e188 | origin/feature/deploy | [gone] |
| feature/integracion-mensajeria | e0f2c5a | origin/feature/integracion-mensajeria | [gone] |
| feature/m05-seguimiento | b00254a | origin/feature/m05-seguimiento | [gone] |
| feature/mailpitypassword | 731122a | origin/feature/mailpitypassword | - |
| feature/refactor-envios | efc63b8 | origin/feature/refactor-envios | [gone] |
| fix/cu0708 | 9ad5c86 | origin/fix/cu0708 | - |
| fix/zonacobertura | a0aa204 | origin/fix/zonacobertura | - |
| integration/consolidacion-cu | 525ffee | origin/develop | [ahead 10] |
| main | 51ed314 | origin/main | [behind 128] |

### frontend

| Local branch | Commit | Upstream | Tracking |
|---|---|---|---|
| checkpoint/codex-cloud-20261102 | 904af71 | origin/checkpoint/codex-cloud-20261102 | - |
| develop | bd837a9 | origin/develop | [behind 14] |
| feature/cu01-gestion-accesos | 8a4db50 | origin/feature/cu01-gestion-accesos | - |
| feature/cu02 | 46e56ec | origin/feature/cu02 | - |
| feature/cu03 | ca4f043 | origin/feature/cu03 | - |
| feature/cu04 | e6aeb7a | origin/feature/cu04 | - |
| feature/cu05 | 9dae34f | origin/feature/cu05 | - |
| feature/cu07 | e94b7a5 | origin/feature/cu07 | - |
| feature/deploy | c5baf68 | origin/feature/deploy | [gone] |
| feature/m05-tracking | 9a8cd45 | origin/feature/m05-tracking | [gone] |
| feature/mailpitypassword | c2d71e9 | origin/feature/mailpitypassword | - |
| feature/refactor-envios | dbe9c64 | origin/feature/refactor-envios | [gone] |
| fix/cu0708 | a65c131 | origin/fix/cu0708 | - |
| fix/zonacobertura | e05c0de | origin/fix/zonacobertura | - |
| integration/consolidacion-cu | b3a6148 | - | - |
| main | 70d9e80 | origin/main | [behind 91] |

### mobile

| Local branch | Commit | Upstream | Tracking |
|---|---|---|---|
| checkpoint/codex-cloud-20261102 | 5302b20 | origin/checkpoint/codex-cloud-20261102 | - |
| develop | 78f65e1 | origin/develop | [behind 4] |
| feature/cu07 | 37ca0da | origin/feature/cu07 | - |
| fix/cu0708 | 74a25f1 | origin/fix/cu0708 | - |
| fix/zonacobertura | 78f65e1 | - | - |
| integration/consolidacion-cu | 8a71b3f | - | - |
| main | 01f094d | origin/main | [behind 7] |
