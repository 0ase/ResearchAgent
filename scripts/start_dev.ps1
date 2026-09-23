$ErrorActionPreference = "Stop"
$backendPort = if ($env:E2E_API_PORT) { [int]$env:E2E_API_PORT } else { 8000 }
$frontendPort = if ($env:E2E_WEB_PORT) { [int]$env:E2E_WEB_PORT } else { 3000 }

$repoRoot = Split-Path -Parent $PSScriptRoot
$pythonPath = Join-Path $repoRoot ".venv\Scripts\python.exe"
if ($env:PYTHON_EXE) { $pythonPath = $env:PYTHON_EXE }
$demoId = [guid]::NewGuid().ToString("N")
$demoInstanceId = [guid]::NewGuid().ToString("N")
$databasePath = Join-Path $repoRoot "data\demo-e2e-$demoId.db"

$env:ENVIRONMENT = "development"
$env:RESEARCH_RUNNER_MODE = "demo"
$env:DEMO_DELAY_SECONDS = if ($env:E2E_DEMO_DELAY_SECONDS) { $env:E2E_DEMO_DELAY_SECONDS } else { "0.25" }
$env:NEXT_PUBLIC_API_BASE_URL = "http://127.0.0.1:$backendPort"
$env:CORS_ORIGINS = "http://localhost:$frontendPort,http://127.0.0.1:$frontendPort"
$env:DEMO_INSTANCE_ID = $demoInstanceId
$env:DATABASE_PATH = $databasePath

foreach ($port in @($backendPort, $frontendPort)) {
  if (Get-NetTCPConnection -State Listen -LocalPort $port -ErrorAction SilentlyContinue) {
    throw "Required development port $port is already in use. Stop the existing process before starting the isolated demo stack."
  }
}

foreach ($path in @($databasePath, "$databasePath-wal", "$databasePath-shm")) {
  if (Test-Path -LiteralPath $path) {
    Remove-Item -LiteralPath $path -Force -ErrorAction SilentlyContinue
  }
}

$backend = Start-Process `
  -FilePath $pythonPath `
  -ArgumentList @("-m", "uvicorn", "backend.main:app", "--host", "127.0.0.1", "--port", "$backendPort") `
  -WorkingDirectory $repoRoot `
  -WindowStyle Hidden `
  -PassThru

try {
  $healthReady = $false
  for ($attempt = 0; $attempt -lt 60; $attempt++) {
    if ($backend.HasExited) {
      throw "FastAPI demo server exited before becoming ready (exit code $($backend.ExitCode))."
    }
    try {
      $response = Invoke-RestMethod -Uri "http://127.0.0.1:$backendPort/health" -TimeoutSec 2
      if (
        $response.status -eq "ok" -and
        $response.runner_mode -eq "demo" -and
        $response.demo_instance_id -eq $demoInstanceId
      ) {
        $healthReady = $true
        break
      }
    } catch {
      Start-Sleep -Milliseconds 250
    }
  }

  if (-not $healthReady) {
    throw "FastAPI demo server did not become ready."
  }

  & npm --prefix (Join-Path $repoRoot "web") run dev -- --hostname 127.0.0.1 --port $frontendPort
  exit $LASTEXITCODE
}
finally {
  if ($backend -and -not $backend.HasExited) {
    Stop-Process -Id $backend.Id -Force -ErrorAction SilentlyContinue
  }

  foreach ($path in @($databasePath, "$databasePath-wal", "$databasePath-shm")) {
    if (Test-Path -LiteralPath $path) {
      Remove-Item -LiteralPath $path -Force -ErrorAction SilentlyContinue
    }
  }
}
