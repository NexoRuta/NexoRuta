#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
[[ "$(uname -s)" == Linux ]] || { echo "Linux required; do not run against the workshop Windows services." >&2; exit 2; }
if [[ $EUID -eq 0 ]]; then SUDO=(); else command -v sudo >/dev/null; SUDO=(sudo); fi
"${SUDO[@]}" apt-get update -qq
"${SUDO[@]}" apt-get install -y --no-install-recommends ca-certificates curl gnupg python3 git xz-utils postgresql-common
# PostgreSQL18 matches the existing integration fixture; use the official PGDG repository.
. /etc/os-release
"${SUDO[@]}" install -d /usr/share/postgresql-common/pgdg
curl -fsSL https://www.postgresql.org/media/keys/ACCC4CF8.asc | "${SUDO[@]}" tee /usr/share/postgresql-common/pgdg/apt.postgresql.org.asc >/dev/null
printf 'deb [signed-by=/usr/share/postgresql-common/pgdg/apt.postgresql.org.asc] https://apt.postgresql.org/pub/repos/apt %s-pgdg main\n' "$VERSION_CODENAME" | "${SUDO[@]}" tee /etc/apt/sources.list.d/nexoruta-pgdg.list >/dev/null
"${SUDO[@]}" apt-get update -qq
"${SUDO[@]}" apt-get install -y --no-install-recommends postgresql-18 postgresql-18-postgis-3 postgresql-18-postgis-3-scripts
# Playwright1.62.1 needs Node>=20; pin Node rather than taking Ubuntu24's Node18.
NODE_VERSION=24.22.2
if [[ "$(node --version 2>/dev/null || true)" != "v$NODE_VERSION" ]]; then
  case "$(uname -m)" in x86_64) NODE_ARCH=x64;; aarch64) NODE_ARCH=arm64;; *) echo 'Unsupported Node architecture' >&2; exit 2;; esac
  node_tmp="$(mktemp -d)"
  curl -fsSL "https://nodejs.org/dist/v$NODE_VERSION/node-v$NODE_VERSION-linux-$NODE_ARCH.tar.xz" -o "$node_tmp/node-v$NODE_VERSION-linux-$NODE_ARCH.tar.xz"
  curl -fsSL "https://nodejs.org/dist/v$NODE_VERSION/SHASUMS256.txt" -o "$node_tmp/SHASUMS256.txt"
  (cd "$node_tmp"; grep " node-v$NODE_VERSION-linux-$NODE_ARCH.tar.xz$" SHASUMS256.txt | sha256sum -c -)
  "${SUDO[@]}" mkdir -p /opt/nexoruta-node
  "${SUDO[@]}" tar -xJf "$node_tmp/node-v$NODE_VERSION-linux-$NODE_ARCH.tar.xz" --strip-components=1 -C /opt/nexoruta-node
  for tool in node npm npx; do "${SUDO[@]}" ln -sf "/opt/nexoruta-node/bin/$tool" "/usr/local/bin/$tool"; done
  rm -rf "$node_tmp"
fi
export DOTNET_ROOT="${DOTNET_ROOT:-$HOME/.dotnet}"
export PATH="$DOTNET_ROOT:$PATH"
if [[ "$(dotnet --version 2>/dev/null || true)" != 10.0.401 ]]; then
  tmp="$(mktemp)"; trap 'rm -f "$tmp"' EXIT
  curl -fsSL https://dot.net/v1/dotnet-install.sh -o "$tmp"
  bash "$tmp" --version 10.0.401 --install-dir "$DOTNET_ROOT"
fi
cd "$ROOT"
dotnet --version
# Pure Razor/Blazor application: NuGet, not a new JS app build pipeline.
dotnet restore backend/src/NexoRuta.Api/NexoRuta.Api.csproj
dotnet restore frontend/tests/NexoRuta.ApiClient.Tests/NexoRuta.ApiClient.Tests.csproj
dotnet restore backend/tests/NexoRuta.UnitTests/NexoRuta.UnitTests.csproj
dotnet restore backend/tests/NexoRuta.IntegrationTests/NexoRuta.IntegrationTests.csproj
dotnet restore mobile/tests/NexoRuta.Mobile.Core.Tests/NexoRuta.Mobile.Core.Tests.csproj
npm ci --prefix scripts/cloud --ignore-scripts
"${SUDO[@]}" env PATH="$PATH" "$ROOT/scripts/cloud/node_modules/.bin/playwright" install-deps chromium
scripts/cloud/node_modules/.bin/playwright install chromium
echo 'Installed. Start with: python3 scripts/cloud/dev.py start'
