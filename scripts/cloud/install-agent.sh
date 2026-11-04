#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
source "$ROOT/scripts/cloud/env-agent.sh"
docker --host=unix:///var/run/docker.sock version
docker --host=unix:///var/run/docker.sock info --format '{{.ServerVersion}}'
mkdir -p "$NEXORUTA_AGENT_TOOLS"
if ! "$DOTNET_ROOT/dotnet" --list-sdks 2>/dev/null | rg -q '^10\.0\.401 '; then
 curl -fsSL https://dot.net/v1/dotnet-install.sh -o "$NEXORUTA_AGENT_TOOLS/dotnet-install.sh"
 bash "$NEXORUTA_AGENT_TOOLS/dotnet-install.sh" --version 10.0.401 --install-dir "$DOTNET_ROOT"
fi
if [[ "$(node --version 2>/dev/null || true)" != v24.22.2 ]]; then
 case "$(uname -m)" in x86_64) arch=x64;; aarch64) arch=arm64;; *) exit 2;; esac
 stage="$(mktemp -d "$NEXORUTA_AGENT_TOOLS/node-download.XXXXXX")"
 curl -fsSL "https://nodejs.org/dist/v24.22.2/node-v24.22.2-linux-$arch.tar.xz" -o "$stage/node-v24.22.2-linux-$arch.tar.xz"
 curl -fsSL https://nodejs.org/dist/v24.22.2/SHASUMS256.txt -o "$stage/SHASUMS256.txt"
 (cd "$stage"; rg " node-v24.22.2-linux-$arch.tar.xz$" SHASUMS256.txt | sha256sum -c -)
 mkdir -p "$NEXORUTA_AGENT_TOOLS/node"
 tar -xJf "$stage/node-v24.22.2-linux-$arch.tar.xz" --strip-components=1 -C "$NEXORUTA_AGENT_TOOLS/node"
 rm -rf "$stage"
fi
cd "$ROOT"
for project in backend/NexoRuta.sln frontend/NexoRuta.sln; do
 dotnet restore "$project" --locked-mode
done
for layer in Core Api Storage Application; do
 dotnet restore "mobile/tests/NexoRuta.Mobile.$layer.Tests" --locked-mode
done
npm ci --prefix scripts/cloud --ignore-scripts
scripts/cloud/node_modules/.bin/playwright install chromium
# Validate browser shared libraries and process permissions, without apt or external navigation.
node - <<'JS'
const {chromium}=require('./scripts/cloud/node_modules/playwright');
(async()=>{const b=await chromium.launch({headless:true});const p=await b.newPage();await p.setContent('<title>cloud-ready</title>');if(await p.title()!=='cloud-ready')throw Error('browser failed');console.log('Chromium launch verified');await b.close()})().catch(e=>{console.error(e);process.exit(1)});
JS
docker pull postgis/postgis:18-3.6-alpine
