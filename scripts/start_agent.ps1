$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$pythonPath = if ($env:RESEARCH_AGENT_PYTHON) {
  $env:RESEARCH_AGENT_PYTHON
} else {
  Join-Path $repoRoot ".venv\Scripts\python.exe"
}
$webRoot = Join-Path $repoRoot "web"
$backendPort = 8000
$frontendPort = 3000
$frontendUrl = "http://127.0.0.1:$frontendPort"
$backendUrl = "http://127.0.0.1:$backendPort"
$startedBackend = $null
$startedFrontend = $null

function Get-ListeningProcess([int] $port) {
  return Get-NetTCPConnection -State Listen -LocalPort $port -ErrorAction SilentlyContinue |
    Select-Object -First 1
}

function Wait-ForHttp([string] $uri, [scriptblock] $validator, [int] $attempts = 60) {
  for ($attempt = 0; $attempt -lt $attempts; $attempt++) {
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

function Stop-ProcessTree([int] $rootPid) {
  $allProcesses = @(Get-CimInstance Win32_Process)
  $pending = [System.Collections.Generic.Queue[int]]::new()
  $descendants = [System.Collections.Generic.HashSet[int]]::new()
  $pending.Enqueue($rootPid)
  [void] $descendants.Add($rootPid)

  while ($pending.Count -gt 0) {
    $parentPid = $pending.Dequeue()
    foreach ($child in ($allProcesses | Where-Object { $_.ParentProcessId -eq $parentPid })) {
      if ($descendants.Add([int] $child.ProcessId)) {
        $pending.Enqueue([int] $child.ProcessId)
      }
    }
  }

  foreach ($processId in ($descendants | Sort-Object -Descending)) {
    Stop-Process -Id $processId -Force -ErrorAction SilentlyContinue
  }
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

try {
  $backendListener = Get-ListeningProcess $backendPort
  if ($backendListener) {
    $backendHealth = Wait-ForHttp "$backendUrl/health" { param($response) $response.status -eq "ok" -and $response.runner_mode -eq "real" } 5
    Write-Host "Reusing the existing real backend on port $backendPort (PID $($backendListener.OwningProcess))." -ForegroundColor DarkGray
  } else {
    $startedBackend = Start-Process `
      -FilePath $pythonPath `
      -ArgumentList @("-m", "uvicorn", "backend.main:app", "--host", "127.0.0.1", "--port", "$backendPort") `
      -WorkingDirectory $repoRoot `
      -WindowStyle Hidden `
      -PassThru

    [void] (Wait-ForHttp "$backendUrl/health" { param($response) $response.status -eq "ok" -and $response.runner_mode -eq "real" })
    Write-Host "Real backend is ready on $backendUrl (PID $($startedBackend.Id))." -ForegroundColor Green
  }

  $frontendListener = Get-ListeningProcess $frontendPort
  if ($frontendListener) {
    $frontendResponse = Invoke-WebRequest -UseBasicParsing -Uri $frontendUrl -TimeoutSec 5
    if ($frontendResponse.StatusCode -ne 200 -or $frontendResponse.Content -notmatch "Research Agent") {
      throw "Port $frontendPort is already used by another application. Stop it before starting Research Agent."
    }
    Write-Host "Reusing the existing frontend on port $frontendPort (PID $($frontendListener.OwningProcess))." -ForegroundColor DarkGray
  } else {
    $startedFrontend = Start-Process `
      -FilePath (Get-Command npm.cmd).Source `
      -ArgumentList @("--prefix", $webRoot, "run", "dev", "--", "--hostname", "127.0.0.1", "--port", "$frontendPort") `
      -WorkingDirectory $repoRoot `
      -PassThru

    [void] (Wait-ForHttp $frontendUrl { param($response) $true })
    Write-Host "Frontend is ready on $frontendUrl (PID $($startedFrontend.Id))." -ForegroundColor Green
  }

  Start-Process $frontendUrl | Out-Null
  Write-Host "Research Agent is running. Close this window to stop processes started by this script." -ForegroundColor Cyan

  if ($startedFrontend) {
    Wait-Process -Id $startedFrontend.Id
  } else {
    while (Get-ListeningProcess $frontendPort) {
      Start-Sleep -Seconds 2
    }
  }
} finally {
  if ($startedFrontend -and -not $startedFrontend.HasExited) {
    Stop-ProcessTree $startedFrontend.Id
  }
  if ($startedBackend -and -not $startedBackend.HasExited) {
    Stop-ProcessTree $startedBackend.Id
  }
}
