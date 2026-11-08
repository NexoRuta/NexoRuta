# Source from Bash before invoking the Cloud scripts.
export DOTNET_ROOT="${DOTNET_ROOT:-/workspace/.dotnet}"
export NEXORUTA_AGENT_TOOLS=/workspace/.nexoruta-tools
export PATH="$NEXORUTA_AGENT_TOOLS/node/bin:$DOTNET_ROOT:$PATH"
export DOTNET_PROCESSOR_COUNT=4 DOTNET_CLI_TELEMETRY_OPTOUT=1
# Node 24 fetch must honor the inherited Cloud proxy for static SDK downloads.
export NODE_USE_ENV_PROXY=1
export NEXORUTA_CLOUD_POSTGRES_MODE=docker NEXORUTA_TEST_POSTGRES_MODE=docker
if [[ -x /opt/nexoruta-redis-7.2.16/bin/redis-server ]]; then
  export NEXORUTA_TEST_REDIS_SERVER=/opt/nexoruta-redis-7.2.16/bin/redis-server
fi
export DOCKER_HOST=unix:///var/run/docker.sock
unset DOCKER_CONTEXT DOCKER_TLS DOCKER_TLS_VERIFY DOCKER_CERT_PATH
# Keep build workers owned by the current invocation in managed tool sessions.
export MSBUILDDISABLENODEREUSE=1 DOTNET_CLI_USE_MSBUILD_SERVER=0 UseSharedCompilation=false
# Managed executors mount the home directory read-only; use task-owned caches.
export NUGET_PACKAGES=/workspace/.nuget/packages
export NUGET_HTTP_CACHE_PATH=/workspace/.nuget/http-cache
export DOTNET_CLI_HOME=/workspace/.dotnet-cli
export npm_config_cache=/workspace/.cache/npm
export PLAYWRIGHT_BROWSERS_PATH=/workspace/.cache/ms-playwright
