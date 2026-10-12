# Frontend Hot Reload in Docker

Run these commands from the repository root with the existing API and infrastructure running. The optional overlay replaces only the three frontend containers, keeping their names, ports and API connections. It does not run migrations or seeding.

## Start development

```powershell
docker compose -f compose.yaml -f compose.dev.yaml config --quiet
docker compose -f compose.yaml -f compose.dev.yaml up -d --no-deps --no-build backoffice commerce tracking
```

Open Backoffice at `http://localhost:5101`, Commerce at `http://localhost:5102` and Tracking at `http://localhost:5103`. Existing frontend sessions may require signing in again after switching modes.

The SDK image runs `dotnet watch` in Debug against the mounted `./frontend` source. Initial startup restores dependencies and builds once. Supported Razor/C# edits apply through Hot Reload; no Docker image build is involved. Polling detects Windows/Docker Desktop bind-mount changes. Build outputs are isolated per container under `/tmp/nexoruta-artifacts`, including the shared ApiClient project, rather than overwriting Windows `bin`/`obj` files.

## Observe changes

```powershell
docker compose -f compose.yaml -f compose.dev.yaml logs -f --tail 50 backoffice commerce tracking
```

Look for `Hot reload enabled`, file changes and `C# and Razor changes applied`. Ctrl+C exits the log viewer without stopping services.

Edits unsupported by Hot Reload automatically restart the affected application because watch runs non-interactively. Changes to project dependencies require restore/build; startup/service registrations may require a frontend restart. Static/server-rendered pages may need a browser refresh to request updated HTML. These are normal [dotnet watch limitations](https://learn.microsoft.com/en-us/dotnet/core/tools/dotnet-watch), not reasons to rebuild images or modify infrastructure.

## Return to normal Docker

```powershell
docker compose -f compose.yaml up -d --no-deps --no-build backoffice commerce tracking
```

This stops watch and restores the existing normal frontend images. It does not rebuild them, so they contain the last published code; build only the frontends when you intentionally want a new normal image. API, Workers, brokers and data volumes are untouched. Do not use `down` to switch modes.

To stop only the development frontends instead:

```powershell
docker compose -f compose.yaml -f compose.dev.yaml stop backoffice commerce tracking
```

## Verification

The effective merged configuration was checked: SDK 10, watch entrypoints, no inherited production build, original ports/API connections and identical infrastructure definitions. All three frontends returned HTTP 200 and rendered correctly. An existing Commerce shipment opened public Tracking; a temporary `.razor` heading edit appeared automatically in the already-open browser, then reverted automatically, with no manual browser refresh, container restart or image rebuild. Source bytes were restored afterwards.
