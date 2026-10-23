$ErrorActionPreference = 'Stop'
$env:Path = [Environment]::GetEnvironmentVariable('Path', 'Machine') + ';' + [Environment]::GetEnvironmentVariable('Path', 'User')
& python (Join-Path $PSScriptRoot 'setup_integration_token.py')
if ($LASTEXITCODE -ne 0) { throw 'La configuracion del token no se completo. Revisar el mensaje anterior.' }
