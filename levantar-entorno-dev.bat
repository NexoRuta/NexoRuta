@echo off
setlocal EnableExtensions DisableDelayedExpansion

rem Guardar este archivo en la raiz de NexoRuta, junto a compose.yaml y .env.
pushd "%~dp0" || exit /b 1

if not exist "compose.yaml" goto missing_files
if not exist "compose.dev.yaml" goto missing_files
if not exist ".env" goto missing_files

docker info >nul 2>&1
if errorlevel 1 goto docker_unavailable

rem El Worker publicado necesita Microsoft.AspNetCore.App. Este override temporal
rem corrige tanto worker como worker-kafka sin modificar compose.yaml.
set "RUNTIME_OVERRIDE=%TEMP%\nexoruta-runtime-%RANDOM%-%RANDOM%.yaml"
> "%RUNTIME_OVERRIDE%" (
    echo services:
    echo   worker:
    echo     build:
    echo       args:
    echo         RUNTIME_IMAGE: mcr.microsoft.com/dotnet/aspnet:10.0
    echo   worker-kafka:
    echo     build:
    echo       args:
    echo         RUNTIME_IMAGE: mcr.microsoft.com/dotnet/aspnet:10.0
)
if errorlevel 1 goto failed

echo [1/7] Comprobando Compose y destino local de la migracion...
docker compose -p nexoruta -f compose.yaml -f compose.dev.yaml -f "%RUNTIME_OVERRIDE%" config --quiet
if errorlevel 1 goto failed
docker compose -p nexoruta -f compose.yaml -f compose.dev.yaml -f "%RUNTIME_OVERRIDE%" --profile rls-admin config --format json | powershell.exe -NoProfile -Command "$c = [Console]::In.ReadToEnd() | ConvertFrom-Json; $s = [string]$c.services.'rls-migrator'.environment.ConnectionStrings__Postgres; try { $b = [System.Data.Common.DbConnectionStringBuilder]::new(); $b.set_ConnectionString($s); $h = [string]$b['Host']; $d = [string]$b['Database']; $aliases = @('Server','Data Source','Address','Addr','Network Address','Initial Catalog'); $ambiguous = @($aliases | Where-Object { $b.ContainsKey($_) }).Count -gt 0; if ($h -ne 'postgres' -or $d -ne 'nexoruta' -or $ambiguous) { throw 'La conexion de migracion debe resolverse a Host=postgres;Database=nexoruta' } } catch { Write-Error 'La conexion de migracion debe apuntar solo al PostgreSQL local nexoruta'; exit 1 }"
if errorlevel 1 goto failed

echo [2/7] Iniciando PostgreSQL local...
docker compose -p nexoruta -f compose.yaml -f compose.dev.yaml -f "%RUNTIME_OVERRIDE%" up -d --wait postgres
if errorlevel 1 goto failed

echo [3/7] Aplicando migraciones a la base local...
docker compose -p nexoruta -f compose.yaml -f compose.dev.yaml -f "%RUNTIME_OVERRIDE%" --profile rls-admin run --rm --no-deps --build rls-migrator
if errorlevel 1 goto failed

echo [4/7] Importando el catalogo departamental versionado...
docker compose -p nexoruta -f compose.yaml -f compose.dev.yaml -f "%RUNTIME_OVERRIDE%" --profile rls-admin run --rm --no-deps --entrypoint dotnet rls-migrator NexoRuta.Api.dll department-catalog-import
if errorlevel 1 goto failed

echo [5/7] Provisionando los roles restringidos creados por las migraciones...
docker compose -p nexoruta -f compose.yaml -f compose.dev.yaml -f "%RUNTIME_OVERRIDE%" --profile rls-admin run --rm --no-deps rls-role-provisioner
if errorlevel 1 goto failed

echo [6/7] Inicializando las seis cuentas de desarrollo configuradas en .env...
docker compose -p nexoruta -f compose.yaml -f compose.dev.yaml -f "%RUNTIME_OVERRIDE%" --profile bootstrap run --rm --no-deps local-bootstrap
if errorlevel 1 goto failed

echo [7/7] Iniciando API, portales, Mailpit, RabbitMQ, Kafka, MongoDB y los dos workers...
docker compose -p nexoruta -f compose.yaml -f compose.dev.yaml -f "%RUNTIME_OVERRIDE%" --profile kafka up -d --build --remove-orphans
if errorlevel 1 goto failed

docker compose -p nexoruta -f compose.yaml -f compose.dev.yaml -f "%RUNTIME_OVERRIDE%" --profile kafka ps
echo.
echo Entorno iniciado. Mailpit: http://localhost:8025
echo Commerce: http://localhost:5102  Backoffice: http://localhost:5101  Admin: http://localhost:5104
set "EXITCODE=0"
goto finish

:missing_files
echo ERROR: coloca este .bat junto a compose.yaml, compose.dev.yaml y .env.
set "EXITCODE=1"
goto finish

:docker_unavailable
echo ERROR: Docker Desktop no esta iniciado o no responde.
set "EXITCODE=1"
goto finish

:failed
echo ERROR: el entorno no termino de iniciar. Revisa el error anterior.
set "EXITCODE=1"

:finish
if defined RUNTIME_OVERRIDE if exist "%RUNTIME_OVERRIDE%" del /q "%RUNTIME_OVERRIDE%" >nul 2>&1
popd
pause
exit /b %EXITCODE%
