# Existing local environment refreshed to develop

The habitual Windows/Docker environment runs the requested sources with its existing database, accounts, configuration, API protection-key volume and TLS gateway. No product fix, commit, push, bootstrap/password reset or volume deletion was performed. Android and end-to-end audit results are separate.

## Effective versions

| Component | Source/version |
|---|---|
| Root develop | `4e5c233dc751736ed59cc234582f157f5c9c278a` |
| Backend | `09538d989399b511473ad5af063754ea76d554a6` |
| Frontend | `d328e98c27db7c5cef018ab3492c54fc563eed49` |
| Mobile gitlink; parent-owned Android work | `683766d6d8cd6c1bd9ce45bb12f6581ddb19b98c` |
| .NET SDK / API and worker runtime | 10.0.401 / .NETCore.App and AspNetCore.App 10.0.14 |
| Docker client/server / Compose | 28.0.4 / 2.34.0 |
| Database | PostgreSQL 18.6; existing `nexoruta` in `nexoruta-postgres` |
| Built images | `nexoruta-api:audit-20261105`, `nexoruta-worker:audit-20261105` |

Container labels identified the actual Compose layers: `compose.yaml`, `compose.dev.yaml`, existing private CU06 activation and Mapbox-temporal overrides, and `.local/windows-refresh-images.json`. An additional ignored audit override selects current images and safe runtime settings. Exact paths and ordered argument tokens remain in ignored `.local/auditoria-excel-20261105/compose-files.json` and `compose-command.json`. Default `compose.override.yaml` was not silently substituted. Existing infrastructure was reused; no second habitual API/database was started.

## Backup and preservation

API/workers and old web containers were stopped before migrations. Private backup directory: `.local/auditoria-excel-20261105/backup/`. It contains a custom-format PostgreSQL dump, globals/roles SQL, `.env`, API data-protection keys and existing TLS files. **Do not publish these files: they contain secrets.**

- Dump: 9,801,507 bytes; SHA256 `6ef860484cc794cf643325b2e40de6a90b32cd0e91f94e80b757e3ef89a56e99`.
- `pg_restore --list` and full decode with `pg_restore --file=/dev/null` exited 0; key archive listing exited 0. No restore drill was performed.
- Existing `nexoruta_postgres_data` and `nexoruta_api_dataprotection_keys` volumes were preserved.
- Before/after fingerprints over every **original column** of all 70 public tables, measured before application restart: 69 tables identical; only `__EFMigrationsHistory` changed. This includes users/accounts/configuration and all existing operational rows. Additive new columns were excluded from the after projection.
- `.env`, CA certificate, server certificate and server private key match their private backups byte-for-byte.
- Post-start: Nov5 route `01a1aa09-9b84-7f67-9fc4-14fef5a82376` remains Finalizada with end timestamp and inactive reservation; Nov9 route `01a1a9cf-3b9f-7771-ad5b-c4f76ca835b6` remains Planificada with active reservation. Six `OcupacionesRuta` rows remain.
- No `local-bootstrap` ran. Restricted database-login passwords were synchronized from the same existing `.env` using the versioned provisioner; application-account hashes were not reset.

## Commands and migrations

`<layers>` below means the exact effective ordered layers above plus the ignored audit override, always with `-p nexoruta`. Exact invocation arrays/private logs remain under `.local/auditoria-excel-20261105/`.

| Operation | Command shape | Exit |
|---|---|---:|
| Validate | `docker compose <layers> --profile kafka config --quiet` | 0 |
| Stop writers | `docker stop nexoruta-api nexoruta-worker nexoruta-worker-kafka nexoruta-backoffice nexoruta-commerce nexoruta-admin nexoruta-tracking` | 0 |
| Dump | `docker exec nexoruta-postgres pg_dump -U nexoruta -d nexoruta -Fc -f /tmp/audit-20261105-before.dump` | 0 |
| Decode dump | `docker exec nexoruta-postgres pg_restore --file=/dev/null /tmp/audit-20261105-before.dump` | 0 |
| Build API/Worker | `docker compose <layers> --profile kafka build api worker` | 0 |
| Migrate | `docker compose <layers> --profile rls-admin run --rm --no-deps rls-migrator` | 0 |
| Department catalog | `docker compose <layers> --profile rls-admin run --rm --no-deps --entrypoint dotnet rls-migrator NexoRuta.Api.dll department-catalog-import` | 0 |
| Provision roles | `docker compose <layers> --profile rls-admin run --rm --no-deps rls-role-provisioner` | 0 |
| Start together | `docker compose <layers> --profile kafka up -d --no-deps --no-build api worker worker-kafka worker-push dashboard admin backoffice commerce tracking` | 0 |

Migration history advanced from 74 to 79 entries, adding exactly:

1. `20261105060707_ParcelResultsAndHomePickups`
2. `20261105061008_ExplicitVisitOutcome`
3. `20261105061723_RegisterCommerceNoticeContract`
4. `20261105063923_SnapshotParcelsPerVisit`
5. `20261105180000_IndependentParcelProofDeadlines`

Department catalog already imported: 19 rows, SHA256 `6853cf948843aeaaefe277c09ecbfc01fe824231ede4e824aa03a045c6864219`; no replacement.

## Verification by method

### Compilation

- Current API/Worker Docker Release publishes: exit 0; existing NU1510 warnings remain.
- Complete frontend solution Release build, SDK 10.0.401, read-only host sources and container-local artifacts: exit 0, 0 errors, 35 warnings (package/nullable/component/test analyzers).
- Development portal containers rebuilt current sources and serve HTTP. Exact image IDs are recorded in the inventory.

### HTTP and security

- API live/ready/OpenAPI: 200; unauthenticated `/api/envios`: 401.
- Existing configured Admin/Operator/Commerce logins: 200. Operator authenticated envios/flota/vehiculos reads: 200; Commerce operadores read: 200.
- Backoffice 5101, Commerce 5102, Admin 5104 `/ingresar`: 200; Tracking 5103 and Mailpit 8025 `/`: 200.
- `https://localhost:5843/health/ready`: 200 with existing CA validation, not insecure TLS. Existing loopback gateway still proxies habitual API 5000; Android reverse/connectivity is separate parent evidence.
- API connects as `nexoruta_api_runtime`. All three restricted runtime logins: no superuser, bypassRls, createDb or createRole. Sixty public tables have forced RLS.

### Automated tests

| Check | Result | Exit |
|---|---|---:|
| Backend UnitTests | 336 passed, 0 failed/skipped | 0 |
| Backend ArchitectureTests | 4 passed, 0 failed/skipped; historical endpoint-boundary failure does not reproduce here | 0 |
| Bounded PostgreSQL integration: C31_EntregaParcial and H1H2_SegundaVisita | 6 theory cases passed, 0 failed/skipped; fixture-owned PostgreSQL18/PostGIS, restricted API and controlled providers | 0 |
| Initial frontend suite with external `/tmp/audit-tests` artifact root | 490 passed, 1 failed, 5 skipped; path-sensitive TemplateHeaderExactlyMatchesBackendParserContract could not find source ancestry | 1 |
| Same complete frontend suite from ephemeral source copy, artifacts beneath that source | 491 passed, 0 failed, 5 skipped | 0 |

The first frontend failure was caused by this invocation layout, not patched: its FindRepositoryRoot starts at AppContext.BaseDirectory and walks ancestors. Repeating unchanged sources with a matching temporary source ancestry resolves it. The five opt-in browser/fullstack tests remain skipped; neither successful unit/component tests nor HTTP checks replace them.

Exact commands/results: [initial tests](entorno-test-results.json), [architecture and bounded integration](entorno-extended-test-results.json), [frontend repeat](entorno-frontend-repeat-result.json). Tests ran with read-only host sources, writable container-local artifacts; copied sources and test artifacts disappeared with their `--rm` containers. The integration filter intentionally excludes the 500/501/1500-parcel load scenarios and the rest of the complete backend integration suite.

### Browser/visual and end-to-end

No browser/visual review was performed by this refresh worker. HTTP 200 does not prove visual correctness or an authenticated browser/mobile business flow. The parent owns these checks and the separate AUD-20261105 fixture. No synthetic audit data was created by this refresh step.

## Access, services and safety

API 5000; gateway HTTPS 5843; Backoffice/Commerce/Tracking/Admin 5101/5102/5103/5104; PostgreSQL loopback 55433; Mailpit HTTP/SMTP loopback 8025/1025; RabbitMQ management 15672; MongoDB loopback 27017; Aspire loopback 18888. Rabbit/Kafka/Push workers are healthy. Redis/Kafka remain internal. See service inventory for exact images/ports/volumes.

Use existing ignored `.env` key pairs `NEXORUTA_ADMIN_MAIL`/`NEXORUTA_ADMIN_PASSWORD`, `NEXORUTA_OPERADOR_MAIL`/`NEXORUTA_OPERADOR_PASSWORD`, `NEXORUTA_COMERCIO_MAIL`/`NEXORUTA_COMERCIO_PASSWORD`. No secret values or tokens are published here.

Mapbox temporal configuration/token was preserved, not exercised by refresh probes; source retains `permanent=false`. Both real Geoapify switches are false. Subsequent browser audits must block/control provider requests before map/search use. SMTP is Mailpit only; development push worker explicitly uses `Push__NoSend=true`. Frontend development cookie keys retain their existing ephemeral-container pattern: recreation can require re-login but does not reset stored accounts. API keys remain in the existing named volume.

## Later preparation corrections and evidence

### Required Kafka v2 topic provisioning

The later synthetic circuit exposed a second omitted preparation step: the current source-declared commerce-notice topic did not exist in the retained broker. `CommerceNoticeConsumer.Topic` and publisher require `nexoruta.comercios.v2`; both disable automatic topic creation. Current `compose.yaml` already declares this topic in `kafka-init`, but the existing older one-shot initializer had not been rerun during manual no-dependency application restoration. This was local preparation, not a product source defect.

Before: broker topic list contained only `__consumer_offsets`, `nexoruta.envios.creados.v1`, `nexoruta.password-recovery.requested.v1`. Two authenticated Commerce notice reads returned 200 with an empty list. Three retained synthetic v2 outbox IDs were Error with `Kafka:Local_UnknownTopic`, attempts 22 immediately before correction (earlier attempts 18/20 are retained in HTTP audit evidence).

Created **only the missing new topic**, using exact existing source options on the local broker:

```text
docker exec nexoruta-kafka kafka-topics --bootstrap-server kafka:9092 --create --if-not-exists --topic nexoruta.comercios.v2 --partitions 3 --replication-factor 1 --config min.insync.replicas=1 --config retention.ms=604800000
```

Exit 0; broker image `confluentinc/cp-kafka:7.9.10`, CLI observed `7.9.10-ccs`. New topic describes three partitions, one replica, minimum ISR 1 and retention 604800000 ms. All existing topic descriptors were identical in the writer's in-memory before/after comparison, and the only topic-list addition was `nexoruta.comercios.v2`. Equality booleans and current descriptor text are retained; raw historical descriptor text was not saved, so that historical comparison is not independently replayable. No existing topic/config/data was deleted, no offsets rewound, no service restarted, and no event manually published.

Normal already-running worker retries then published all three exact retained events: attempts 22 to 23, errors cleared, publication timestamps 18:52:55–57 UTC. Each persisted exactly once in `AvisosComercio` (three matching rows, three distinct event IDs). The single delayed authenticated Commerce GET returned 200 with 39 tenant notices; each of the three initially failed event IDs appears exactly once in that actual response. No manual republish was needed. Source-version updates must include the existing idempotent `kafka-init` provisioning step, not merely rebuild/restart applications. See [topic command, before/after state and delivery proof](entorno-kafka-commerce-topic-preparation.json).

### Necessary preparation correction: evidence upload 503

The later HTTP audit exposed a missing mandatory local deployment secret, not an image/filesystem/product defect. Actual API environment lacked `Reparto__EvidenciasEncryptionKey`; `EfOperacionesRepartoRepository.Evidencias.cs` requires a base64 32-byte key and deliberately fails closed before storing evidence. Evidence ciphertext is stored in PostgreSQL, so adding a directory or changing filesystem permissions would not fix this cause.

The failed request had trace `99184556d994e199f8c98a40f2dbdc37`, journey `01a1ad04-7dd7-7965-afe0-cf8598600800`, file `f2b641b8-3d2c-42ab-8a32-659afbf14e1f`. Pre-refresh and immediately pre-fix `EvidenciasReparto` counts were both zero; no prior evidence deployment key was present in the actual runtime or retained private runtime JSON inspected.

Provisioned the **first dedicated evidence key** once in ignored `.local/auditoria-excel-20261105/evidence-key-private.json`, property `Reparto__EvidenciasEncryptionKey`, with a private backup at `backup/evidence-key-provisioned.json`. It is 32 decoded bytes, distinct from the existing unchanged Seguimiento key. The same property was added only to API environment in the ignored `runtime-override.json`. Preserve this key and override for subsequent starts; never regenerate it over accepted evidence. Ordinary startup commands that omit this effective override do not supply the new evidence secret.

Only API was recreated with the same built image using `docker compose <layers> --profile kafka up -d --no-deps --no-build api`: exit 0, 2.92 seconds. No database, worker, `.env`, certificate, volume or existing encryption key changed. API ready and CA-validated gateway ready both returned 200 afterward.

The HTTP worker retried the retained **same file UUID and identical request body**: 503 before, 204 after. Read back both archived HTTP requests and independently confirmed equality. PostgreSQL afterward had four synthetic audit evidence rows; all had 12-byte nonces, 16-byte tags and nonempty ciphertext; the original failed file UUID existed exactly once. See [before/after preparation and storage evidence](entorno-evidence-key-preparation.json). The worker then continued its separate business circuit; those results belong to the HTTP audit, not this refresh report. No product source was changed.

- [Backup](entorno-backup-verification.json), [all-table preservation and migration history](entorno-preservation-result.json), [protected routes](entorno-protected-state.json).
- [HTTP/auth/RLS](entorno-runtime-verification.json), [image IDs/ports/health/volumes](entorno-service-inventory.json), [config/certificate equality](entorno-config-preservation.json).
- [Backend build](entorno-build-backend-result.json), [frontend build](entorno-build-frontend-result.json), [startup](entorno-startup-result.json), [migration/provision commands](entorno-migration-results.json).

No remote deployment, source commit/push, destructive reset, rollback or volume removal occurred. No native RDD lifecycle was started for environment-only preparation. Parent independent spot checks remain separate. Engram mutation was unavailable because the native session was unregistered; no identity was invented.

Risk: item 1 (explicit existing schema/data-format migrations), item 2 (first dedicated local evidence encryption secret), item 5 (local runtime/image/service preparation); no product source changed.
