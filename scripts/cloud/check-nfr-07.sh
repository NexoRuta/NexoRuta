#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
REDIS_SERVER="/opt/nexoruta-redis-7.2.16/bin/redis-server"
[[ -x "$REDIS_SERVER" ]] || { echo "Redis 7.2.16 is missing; run scripts/cloud/install.sh first." >&2; exit 2; }
export DOTNET_ROOT="${DOTNET_ROOT:-$HOME/.dotnet}"
export PATH="$DOTNET_ROOT:$PATH"
export NEXORUTA_TEST_POSTGRES_MODE=native
export NEXORUTA_TEST_REDIS_MODE=native
export NEXORUTA_TEST_REDIS_SERVER="$REDIS_SERVER"
cd "$ROOT"

dotnet restore backend/NexoRuta.sln --locked-mode
dotnet build backend/NexoRuta.sln -c Release --no-restore
dotnet test backend/tests/NexoRuta.UnitTests/NexoRuta.UnitTests.csproj -c Release --no-build --no-restore
dotnet test backend/tests/NexoRuta.ArchitectureTests/NexoRuta.ArchitectureTests.csproj -c Release --no-build --no-restore
dotnet test backend/tests/NexoRuta.IntegrationTests/NexoRuta.IntegrationTests.csproj -c Release --no-build --no-restore \
  --filter 'FullyQualifiedName~Caching|FullyQualifiedName~IdentidadVisualOperadorHttpTests|FullyQualifiedName~TarifarioHttpTests|FullyQualifiedName~TarifaAdmision'
