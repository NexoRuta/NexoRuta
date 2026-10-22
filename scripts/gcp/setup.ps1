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

function Write-GcsBackend {
    param([string]$Path)
    $backendText = "terraform {`n  backend `"gcs`" {}`n}`n"
    [System.IO.File]::WriteAllText($Path, $backendText, [System.Text.UTF8Encoding]::new($false))
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
    if (@($projects).Count -eq 1) { $ProjectId = $projects[0].projectId }
    else {
        $projects | Select-Object projectId, name | Format-Table | Out-Host
        $ProjectId = Read-Host 'Project ID for the NexoRuta demo'
    }
}
if ($ProjectId -notmatch '^[a-z][a-z0-9-]{4,28}[a-z0-9]$') { throw 'Invalid project ID.' }
Invoke-Tool -Name gcloud -Arguments @('config', 'set', 'project', $ProjectId)
Invoke-Tool -Name gcloud -Arguments @('auth', 'application-default', 'set-quota-project', $ProjectId)
$billing = & gcloud billing projects describe $ProjectId --format=json | ConvertFrom-Json
if ($LASTEXITCODE -ne 0 -or !$billing.billingEnabled) { throw 'The project needs an active billing account before bootstrap.' }
$repoInfo = & gh api "repos/$Repository" | ConvertFrom-Json
if ($LASTEXITCODE -ne 0) { throw 'Could not read the GitHub repository.' }

$bootstrap = Join-Path $workspace 'infra/gcp/bootstrap'
$settings = @{
    project_id = $ProjectId
    region = 'southamerica-west1'
    github_repository = $Repository
    github_repository_id = [string]$repoInfo.id
    github_owner_id = [string]$repoInfo.owner.id
    billing_account_id = $(if ($SkipBudget) { '' } else { $billing.billingAccountName -replace '^billingAccounts/', '' })
}
$encoding = [System.Text.UTF8Encoding]::new($false)
[System.IO.File]::WriteAllText((Join-Path $bootstrap 'terraform.tfvars.json'), ($settings | ConvertTo-Json), $encoding)
$bucket = "$ProjectId-tofu-state"
$backendFile = Join-Path $bootstrap 'backend.generated.tf'
$remoteState = "gs://$bucket/foundation/default.tfstate"
$hasRemoteState = Test-Tool -Name gcloud -Arguments @('storage', 'objects', 'describe', $remoteState, '--format=value(name)') -NotFoundOnly
if ($hasRemoteState) {
    Write-GcsBackend -Path $backendFile
    Invoke-Tool -Name tofu -Arguments @("-chdir=$bootstrap", 'init', '-reconfigure', "-backend-config=bucket=$bucket", '-backend-config=prefix=foundation')
} elseif (Test-Path -LiteralPath $backendFile) {
    # Recover if creation succeeded but the first local-to-GCS migration failed.
    $localStatePath = Join-Path $bootstrap 'terraform.tfstate'
    if (!(Test-Path -LiteralPath $localStatePath)) {
        throw 'Backend exists locally but remote state and local migration state are inaccessible.'
    }
    $localState = Get-Content -LiteralPath $localStatePath -Raw | ConvertFrom-Json
    if ($localState.outputs.github_variables.value.GCP_PROJECT_ID -ne $ProjectId) {
        throw 'Local migration state belongs to a different or unknown project. Resolve state before continuing.'
    }
    Write-GcsBackend -Path $backendFile
    Invoke-Tool -Name tofu -Arguments @("-chdir=$bootstrap", 'init', '-migrate-state', '-force-copy', "-backend-config=bucket=$bucket", '-backend-config=prefix=foundation')
    $hasRemoteState = $true
} else {
    Invoke-Tool -Name tofu -Arguments @("-chdir=$bootstrap", 'init')
}
Invoke-Tool -Name tofu -Arguments @("-chdir=$bootstrap", 'plan', '-out=bootstrap.tfplan')
Invoke-Tool -Name tofu -Arguments @("-chdir=$bootstrap", 'apply', 'bootstrap.tfplan')
if (!$hasRemoteState) {
    Write-GcsBackend -Path $backendFile
    Invoke-Tool -Name tofu -Arguments @("-chdir=$bootstrap", 'init', '-migrate-state', '-force-copy', "-backend-config=bucket=$bucket", '-backend-config=prefix=foundation')
}

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
Invoke-Tool -Name gcloud -Arguments @('compute', 'machine-types', 'describe', 'n4-highcpu-8', '--zone=southamerica-west1-a')
Invoke-Tool -Name gcloud -Arguments @('compute', 'regions', 'describe', 'southamerica-west1', '--format=json(quotas)')
Write-Host 'Bootstrap complete. Publish the workflows to main, then run demo-vm.yml with operation=start.'
