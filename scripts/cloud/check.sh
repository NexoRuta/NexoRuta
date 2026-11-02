#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../.."
export NEXORUTA_TEST_POSTGRES_MODE="${NEXORUTA_TEST_POSTGRES_MODE:-native}"
export NEXORUTA_PLAYWRIGHT_MODULE="$PWD/scripts/cloud/node_modules/playwright-core"
export NEXORUTA_DESTINATION_BROWSER_DIR="$(mktemp -d /tmp/nexoruta-cloud-browser-XXXXXX)"
export NEXORUTA_GEOCODING_FULLSTACK_DIR="$(mktemp -d /tmp/nexoruta-cloud-fullstack-XXXXXX)"
dotnet build frontend/src/NexoRuta.Commerce --nologo
dotnet test backend/tests/NexoRuta.IntegrationTests --filter FullyQualifiedName~DestinosEnvioHttpTests --logger 'console;verbosity=minimal'
dotnet test backend/tests/NexoRuta.IntegrationTests --no-build --filter FullyQualifiedName~GeocodificacionFullStackBrowserTests --logger 'console;verbosity=minimal'
dotnet test frontend/tests/NexoRuta.ApiClient.Tests --filter 'FullyQualifiedName~DestinosEnvioPagesTests|FullyQualifiedName~DestinationSearchSelectSaveEditAndManualFallbackInChromium' --logger 'console;verbosity=minimal'
dotnet test mobile/tests/NexoRuta.Mobile.Core.Tests --no-restore -p:NuGetLockFilePath=obj/cloud.packages.lock.json --filter FullyQualifiedName~IncidenciasCierreTests --logger 'console;verbosity=minimal'
node --test frontend/tests/destino-mapbox.test.cjs
python3 scripts/cloud/dev.py verify
