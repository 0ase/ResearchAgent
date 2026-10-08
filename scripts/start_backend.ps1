param(
    [ValidateRange(1, 65535)]
    [int]$Port = 3000,
    [switch]$Reload
)

$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$condaCommand = Get-Command conda -CommandType Application -ErrorAction Stop | Select-Object -First 1
$backendArguments = @(
    'run', '--no-capture-output', '-n', 'BIGONE',
    'python', '-m', 'uvicorn', 'backend.main:app',
    '--host', '127.0.0.1', '--port', $Port.ToString()
)
if ($Reload) {
    $backendArguments += @('--reload', '--reload-dir', (Join-Path $projectRoot 'backend'))
}

Push-Location -LiteralPath $projectRoot
try {
    & $condaCommand.Source @backendArguments
    exit $LASTEXITCODE
} finally {
    Pop-Location
}
