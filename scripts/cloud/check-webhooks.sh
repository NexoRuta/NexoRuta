#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../.."
source scripts/cloud/env-agent.sh
export NEXORUTA_PLAYWRIGHT_MODULE="$PWD/scripts/cloud/node_modules/playwright"
export NEXORUTA_WEBHOOK_E2E_DIR="${NEXORUTA_WEBHOOK_E2E_DIR:-$PWD/.local/webhooks-evidence}"
dotnet restore frontend/NexoRuta.sln --locked-mode
dotnet build frontend/NexoRuta.sln --no-restore --nologo
dotnet test backend/tests/NexoRuta.UnitTests --filter FullyQualifiedName~WebhookSecurityTests --logger trx --results-directory "$NEXORUTA_WEBHOOK_E2E_DIR/unit"
dotnet test frontend/tests/NexoRuta.ApiClient.Tests --filter FullyQualifiedName~CommerceReceiverTests --logger trx --results-directory "$NEXORUTA_WEBHOOK_E2E_DIR/receiver"
dotnet test backend/tests/NexoRuta.IntegrationTests --filter 'FullyQualifiedName~WebhooksHttpTests|FullyQualifiedName~WebhooksFullStackTests|FullyQualifiedName~C31_EntregaParcial|FullyQualifiedName~C37_RetiroPorApi' --logger trx --results-directory "$NEXORUTA_WEBHOOK_E2E_DIR/integration"
