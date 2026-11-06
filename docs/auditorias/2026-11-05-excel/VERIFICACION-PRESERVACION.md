# Original state preserved across the local refresh

Independent read-only checks found no lost original business/account rows or product-source changes. The existing environment is healthy after the API-only evidence-key configuration. This is preservation evidence, **not** functional acceptance, native review approval or a successful restore drill.

## Observed checks

| Area | Independent observation |
|---|---|
| Database backup | Local custom dump is 9,801,507 bytes; SHA256 `6ef860484cc794cf643325b2e40de6a90b32cd0e91f94e80b757e3ef89a56e99`. Piped the actual local bytes into `pg_restore --list` and `pg_restore --data-only --file=-`; both exit 0, 70 COPY blocks decoded. No restore executed. |
| Before-restart snapshots | Recomputed comparison of saved original-column snapshots: 69/70 unchanged, only migration history differs. These historical snapshots were produced by the refresh worker; the verifier did not observe their capture. |
| Current original rows | Independently decoded original keys from the backup in memory, queried current database under READ ONLY transactions, and compared original-column fingerprints against the pre-refresh snapshot. 69/70 original-table projections match; the exception is two original OutboxMessages whose Estado, Intentos and PublicadoEnUtc advanced after worker restart. Original counts are unchanged. This is processing metadata, not shipment/account modification. |
| Synthetic additions | Original-key filtering excludes newly created audit rows. Empty-before tables contain no original rows to lose. PruebasEntrega uses its original OperadorId/EnvioId/RutaId natural key because the migrated primary key adds BultoId. Its single original row remains byte-equivalent under the original projection. |
| Protected state | All 10 original HojasRuta, 6 OcupacionesRuta and 3 Vehiculos match original-column fingerprints. The Nov5 route remains Finalizada and the Nov9 route remains Planificada. Original users/configuration and operational tables match as well. |
| Migrations and roles | 79 migration entries; expected five new entries present. All three runtime roles have superuser, bypassRls, createDb and createRole false. 60 public tables force RLS. |
| Runtime | One habitual API and one PostgreSQL container; API/workers/PostgreSQL healthy. API uses current image `sha256:b4906c9016dc1f60dcf2b29d8e6ab8b69550637d4e2047c3a49b4a3787a4cc83`. Existing PostgreSQL and API data-protection named volumes remain mounted. |
| Configuration and keys | `.env`, CA/server certificate and server private key equal their private pre-refresh backups. The backed-up API data-protection key equals the current mounted key byte-for-byte. Dedicated evidence key matches its ignored persistent file, decodes to 32 bytes and differs from Seguimiento; Seguimiento still matches the original private environment. No secret values are recorded. |
| Source | Root `4e5c233`; exact backend `09538d9`, frontend `d328e98`, mobile `683766d` gitlinks. All three source worktrees clean. Root has only the original human Excel modification plus audit artifacts. Excel SHA256 remains `8de7fcf3c84c113788b71a89e5e51cc852aafd0e690a0d35f4b944e855220cf4`. |
| Android persistence | Fresh ADB read-only file reads independently match all six initial sizes/hashes. Current UID 10217. Pulled installed APK into system TEMP and independently ran apksigner verify: signer SHA256 `41ff9ffbcad5c0ac6edfd2a9d6d42e9b8e801b8678da375d6012b465a67463c7`. No app launch or UI operation. |

## Verification methods and limits

- **Compilation:** not repeated by this verifier; refresh-worker build evidence is separate.
- **HTTP:** post-configuration API readiness 200, unauthenticated envios 401, gateway HTTPS readiness 200 using the existing CA (no insecure TLS).
- **Automation:** actual backup decoding, READ ONLY SQL, Docker inspection, Git/hash comparisons, ADB file reads and installed-APK signature verification; exact safe results are in [preservation-independent.json](preservation-independent.json).
- **Visual/interaction:** not performed. Existing computer-use denial was respected. Android camera, scanner, signature, updated-app lifecycle and browser acceptance remain pending.
- No restoration over any database, schema migration, source change, service change, commit, push or deletion was performed by this verifier. Backup decoding does not prove restore recoverability. Native RDD approval is not asserted.

## Temporary material

Verifier scratch is outside the worktree: `%TEMP%/nexoruta-preservation-a111794078d941f79507877ac1cdd1ad/`. It contains scripts and a pulled installed APK. The parent owns cleanup of this exact directory; it is not part of the audit deliverables.

Risk: item 1 (verification of existing persistent migrations) and item 5 (verification of local environment refresh); this verifier made no product/runtime mutations.

## Supplemental check: source-required commerce topic

At 18:54 UTC the verifier independently read the live broker after the topic-only preparation:

- The only addition against the saved prior topic list is `nexoruta.comercios.v2`; all three old topics remain. Its live descriptor matches the current `compose.yaml` initializer: three partitions, replication one, min ISR one, retention 604800000 ms. Current complete descriptors are retained in the JSON supplement.
- **Historical limit:** original existing-topic descriptor text was not saved. Before/after descriptor equality was observed by the environment worker in memory, not independently reproducible. Current descriptors/topic presence are independently checked; no claim is made about historical message contents or offsets.
- API, PostgreSQL and Kafka are healthy. Their actual start times precede the 18:52:42 topic preparation: API 18:46:37, PostgreSQL/Kafka 18:21:27 UTC. No restart during the topic operation is evidenced.
- API and CA-validated gateway readiness both return 200. Persistent evidence key remains the configured 32-byte distinct key; tracking, original `.env`, TLS and API data-protection key remain unchanged. Product worktrees remain clean and Excel hash unchanged.
- Independent READ ONLY SQL now finds the exact three previously failed synthetic outbox IDs as Publicado, with non-null publication times and no error; the same event IDs appear exactly once each in AvisosComercio (three rows, three distinct events). The verifier did not publish, reset offsets or mutate messages.

This bounded supplement does not rerun the backup decode or broaden functional/visual acceptance. See `kafkaSupplement` in [preservation-independent.json](preservation-independent.json). The same previously disclosed TEMP directory contains the supplemental scripts; no new scratch directory was created.
