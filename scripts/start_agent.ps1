[CmdletBinding()]
param([switch]$NoBrowser)

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$pythonPath = Join-Path $repoRoot ".venv\Scripts\python.exe"
if ($env:PYTHON_EXE) { $pythonPath = $env:PYTHON_EXE }
$webRoot = Join-Path $repoRoot "web"
$backendPort = if ($env:RESEARCH_API_PORT) { [int] $env:RESEARCH_API_PORT } else { 8000 }
$frontendPort = if ($env:RESEARCH_WEB_PORT) { [int] $env:RESEARCH_WEB_PORT } else { 3000 }
$frontendUrl = "http://localhost:$frontendPort"
$backendUrl = "http://127.0.0.1:$backendPort"
$startedBackend = $null
$startedFrontend = $null
$runId = [guid]::NewGuid().ToString("N")
$logRoot = Join-Path $repoRoot "logs\launcher-$runId"
New-Item -ItemType Directory -Path $logRoot -Force | Out-Null
$stopFile = Join-Path $logRoot "backend.stop"
$frontendStopFile = Join-Path $logRoot "frontend.stop"
Write-Host "Runtime logs: $logRoot"

function Get-ListeningProcess([int] $port) {
  return Get-NetTCPConnection -State Listen -LocalPort $port -ErrorAction SilentlyContinue |
    Select-Object -First 1
}

function Wait-ForHttp([string] $uri, [scriptblock] $validator, [int] $attempts = 60) {
  for ($attempt = 0; $attempt -lt $attempts; $attempt++) {
    if ($startedBackend -and $startedBackend.HasExited) { throw "Backend exited during startup. Logs: $logRoot" }
    if ($startedFrontend -and $startedFrontend.HasExited) { throw "Frontend exited during startup. Logs: $logRoot" }
    try {
      $response = Invoke-RestMethod -Uri $uri -TimeoutSec 2
      if (& $validator $response) {
        return $response
      }
    } catch {
      # The process is still starting. Retry without printing transient errors.
    }
    Start-Sleep -Milliseconds 500
  }
  throw "Timed out waiting for $uri."
}

if (-not (Test-Path -LiteralPath $pythonPath)) {
  throw "Python virtual environment not found: $pythonPath"
}
if (-not (Get-Command npm.cmd -ErrorAction SilentlyContinue)) {
  throw "npm.cmd was not found. Install Node.js before starting Research Agent."
}

Set-Location $repoRoot
$env:ENVIRONMENT = "development"
$env:RESEARCH_RUNNER_MODE = "real"
$env:NEXT_PUBLIC_API_BASE_URL = $backendUrl
$env:CORS_ORIGINS = "http://localhost:$frontendPort,http://127.0.0.1:$frontendPort"

# Health responses cannot establish which checkout owns an existing service.
# Refuse reuse so this checkout never sends tasks or settings to another one.
foreach ($port in @($backendPort, $frontendPort)) {
  if ($port -lt 1 -or $port -gt 65535) { throw "Invalid port: $port" }
  if (Get-ListeningProcess $port) {
    throw "Port $port is occupied. Choose RESEARCH_API_PORT / RESEARCH_WEB_PORT or stop that service yourself. No existing process was changed."
  }
}

try {
  $backendListener = Get-ListeningProcess $backendPort
  if ($backendListener) {
    throw "Port $backendPort became occupied before launch."
  } else {
    $startedBackend = Start-Process `
      -FilePath $pythonPath `
      -ArgumentList @("scripts/owned_process.py", "--parent-pid", "$PID", "--stop-file", "`"$stopFile`"", "--graceful", "--", "`"$pythonPath`"", "scripts/serve_backend.py", "--port", "$backendPort", "--stop-file", "`"$stopFile`"", "--parent-pid", "$PID") `
      -WorkingDirectory $repoRoot `
      -WindowStyle Hidden `
      -RedirectStandardOutput (Join-Path $logRoot "backend.stdout.log") `
      -RedirectStandardError (Join-Path $logRoot "backend.stderr.log") `
      -PassThru

    [void] $startedBackend.Handle
    [void] (Wait-ForHttp "$backendUrl/health" { param($response) $response.status -eq "ok" -and $response.runner_mode -eq "real" })
    Write-Host "Real backend is ready on $backendUrl (PID $($startedBackend.Id))." -ForegroundColor Green
  }

  $frontendListener = Get-ListeningProcess $frontendPort
  if ($frontendListener) {
    throw "Port $frontendPort became occupied before launch."
  } else {
    $startedFrontend = Start-Process `
      -FilePath $pythonPath `
      -ArgumentList @("scripts/owned_process.py", "--parent-pid", "$PID", "--stop-file", "`"$frontendStopFile`"", "--", "`"$((Get-Command npm.cmd).Source)`"", "--prefix", "`"$webRoot`"", "run", "dev", "--", "--hostname", "127.0.0.1", "--port", "$frontendPort") `
      -WorkingDirectory $repoRoot `
      -WindowStyle Hidden `
      -RedirectStandardOutput (Join-Path $logRoot "frontend.stdout.log") `
      -RedirectStandardError (Join-Path $logRoot "frontend.stderr.log") `
      -PassThru

    [void] $startedFrontend.Handle
    [void] (Wait-ForHttp $frontendUrl { param($response) $true })
    Write-Host "Frontend is ready on $frontendUrl (PID $($startedFrontend.Id))." -ForegroundColor Green
  }

  if (-not $NoBrowser) { Start-Process $frontendUrl | Out-Null }
  Write-Host "Research Agent is running. Close this window to stop processes started by this script." -ForegroundColor Cyan

  while ($true) {
    $startedBackend.Refresh()
    $startedFrontend.Refresh()
    if ($startedBackend.HasExited) {
      throw "Backend exited unexpectedly (code $($startedBackend.ExitCode)). Logs: $logRoot"
    }
    if ($startedFrontend.HasExited) {
      if ($startedFrontend.ExitCode -ne 0) { throw "Frontend exited with code $($startedFrontend.ExitCode). Logs: $logRoot" }
      break
    }
    Start-Sleep -Seconds 1
  }
} finally {
  if ($startedFrontend -and -not $startedFrontend.HasExited) {
    New-Item -ItemType File -Path $frontendStopFile -Force | Out-Null
    if (-not $startedFrontend.WaitForExit(2000)) { $startedFrontend.Kill() }
  }
  if ($startedBackend -and -not $startedBackend.HasExited) {
    Write-Host "Stopping backend; active research will become interrupted. Logs: $logRoot"
    New-Item -ItemType File -Path $stopFile -Force | Out-Null
    if (-not $startedBackend.WaitForExit(15000)) {
      $startedBackend.Kill()
    }
  }
}
