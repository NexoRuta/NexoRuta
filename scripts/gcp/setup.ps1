[CmdletBinding()]
param(
    [string]$ProjectId,
    [string]$Repository = 'NexoRuta/NexoRuta',
    [string]$BaseDomain = '',
    [switch]$ManageDns,
    [switch]$SkipBudget
)

$ErrorActionPreference = 'Stop'
$workspace = (Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
# Refresh tools installed after the terminal/application was opened.
$env:Path = [Environment]::GetEnvironmentVariable('Path', 'Machine') + ';' + [Environment]::GetEnvironmentVariable('Path', 'User')

function Invoke-Tool {
    param([string]$Name, [string[]]$Arguments)
    & $Name @Arguments
    if ($LASTEXITCODE -ne 0) { throw "$Name failed with exit code $LASTEXITCODE" }
}

function Test-Tool {
    param([string]$Name, [string[]]$Arguments, [switch]$NotFoundOnly)
    $previousPreference = $ErrorActionPreference
    try {
        # Windows PowerShell turns redirected native stderr into ErrorRecords.
        # Inspect the exit code for probes whose failure can be expected.
        $ErrorActionPreference = 'Continue'
        $probeOutput = & $Name @Arguments 2>&1
        $probeExitCode = $LASTEXITCODE
    } finally {
        $ErrorActionPreference = $previousPreference
    }
    if ($probeExitCode -eq 0) { return $true }
    if ($NotFoundOnly -and ($probeOutput | Out-String) -notmatch '\b404\b') {
        throw "Could not inspect remote state: $Name exited $probeExitCode. $($probeOutput | Out-String)"
    }
    return $false
}

foreach ($tool in @('gcloud', 'tofu', 'gh', 'git', 'python', 'ssh')) {
    if (!(Get-Command $tool -ErrorAction SilentlyContinue)) { throw "Install $tool first; see infra/gcp/README.md." }
}
$account = & gcloud auth list --filter=status:ACTIVE --format='value(account)'
if (!$account) { Invoke-Tool -Name gcloud -Arguments @('auth', 'login', '--brief') }
if (!(Test-Tool -Name gcloud -Arguments @('auth', 'application-default', 'print-access-token'))) {
    Invoke-Tool -Name gcloud -Arguments @('auth', 'application-default', 'login')
}
if (!(Test-Tool -Name gh -Arguments @('auth', 'status'))) {
    Invoke-Tool -Name gh -Arguments @('auth', 'login', '--hostname', 'github.com', '--git-protocol', 'https', '--web')
}

if (!$ProjectId) {
    $projects = & gcloud projects list --format=json | ConvertFrom-Json
    if ($LASTEXITCODE -ne 0) { throw 'Could not list Google Cloud projects.' }
    $projects | Select-Object projectId, name | Format-Table | Out-Host
    $ProjectId = Read-Host 'Enter the explicit project ID for the NexoRuta demo'
}
if ($ProjectId -notmatch '^[a-z][a-z0-9-]{4,28}[a-z0-9]$') { throw 'Invalid project ID.' }
if ($Repository -cne 'NexoRuta/NexoRuta') { throw 'Only the NexoRuta/NexoRuta bootstrap profile is supported.' }

$bootstrap = Join-Path $workspace 'infra/gcp/bootstrap'
$setupRunner = Join-Path $workspace 'scripts/gcp/bootstrap_setup.py'
$setupArguments = @($setupRunner, '--project-id', $ProjectId, '--repository', $Repository,
    '--environment', 'nexoruta-demo', '--region', 'southamerica-west1')
if ($SkipBudget) { $setupArguments += '--skip-budget' }
Invoke-Tool -Name python -Arguments $setupArguments

Invoke-Tool -Name gh -Arguments @('api', '--method', 'PUT', "repos/$Repository/environments/nexoruta-demo")
$variables = & tofu "-chdir=$bootstrap" output -json github_variables | ConvertFrom-Json
if ($LASTEXITCODE -ne 0) { throw 'Could not load bootstrap outputs.' }
foreach ($property in $variables.PSObject.Properties) {
    Invoke-Tool -Name gh -Arguments @('variable', 'set', $property.Name, '--repo', $Repository, '--env', 'nexoruta-demo', '--body', [string]$property.Value)
}
# An absent domain uses sslip.io. gh omits an empty --body from its API payload.
if ($BaseDomain) {
    Invoke-Tool -Name gh -Arguments @('variable', 'set', 'GCP_BASE_DOMAIN', '--repo', $Repository, '--env', 'nexoruta-demo', '--body', $BaseDomain)
}
Invoke-Tool -Name gh -Arguments @('variable', 'set', 'GCP_MANAGE_DNS', '--repo', $Repository, '--env', 'nexoruta-demo', '--body', $ManageDns.IsPresent.ToString().ToLowerInvariant())
Write-Host 'Bootstrap complete. Publish the workflows to main, then run vm-controls.yml with operation=start.'
