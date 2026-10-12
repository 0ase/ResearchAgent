[CmdletBinding()]
param(
    [switch]$Observe,
    [switch]$Stop,
    [switch]$CheckOnly,
    [switch]$NoBrowser,
    [string]$CondaPath,
    [string]$NpmPath,
    [ValidateSet('Backend', 'Frontend')]
    [string]$Service,
    [ValidateRange(1, 65535)]
    [int]$ServicePort = 3000,
    [ValidateRange(5, 300)]
    [int]$StartupTimeout = 90
)

$ErrorActionPreference = 'Stop'

function New-ProjectLaunchConfig {
    param([string]$Root, [bool]$WithObservation = $false)
    $rootPath = [IO.Path]::GetFullPath($Root).TrimEnd('\')
    $logDirectory = Join-Path $rootPath 'logs'
    [pscustomobject]@{
        Root = $rootPath
        ScriptPath = Join-Path $rootPath 'scripts/start_project.ps1'
        PowerShellPath = Join-Path $PSHOME 'powershell.exe'
        CondaPath = $null
        NpmPath = $null
        Observe = $WithObservation
        BackendPort = 3000
        FrontendPort = 5173
        BackendUrl = 'http://127.0.0.1:3000/health'
        FrontendUrl = 'http://127.0.0.1:5173/'
        LogDirectory = $logDirectory
        StatePath = Join-Path $logDirectory 'launcher-state.json'
        LockPath = Join-Path $logDirectory 'launcher.lock'
    }
}

function Resolve-LauncherTool {
    param([string]$Requested, [string]$CommandName, [string[]]$Candidates = @())
    if ($Requested) {
        if (-not (Test-Path -LiteralPath $Requested -PathType Leaf)) {
            throw "Executable not found: $Requested"
        }
        return [IO.Path]::GetFullPath($Requested)
    }
    $command = Get-Command $CommandName -CommandType Application -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($command) { return $command.Source }
    foreach ($candidate in $Candidates) {
        if ($candidate -and (Test-Path -LiteralPath $candidate -PathType Leaf)) {
            return [IO.Path]::GetFullPath($candidate)
        }
    }
    throw "$CommandName was not found. Install it or supply its path to the launcher."
}

function Assert-ProjectLaunchDependencies {
    param($Config, [string]$RequestedConda, [string]$RequestedNpm)
    $driveRoot = [IO.Path]::GetPathRoot($Config.Root)
    $condaCandidates = @($env:CONDA_EXE)
    foreach ($basePath in @($env:USERPROFILE, $env:LOCALAPPDATA, $driveRoot)) {
        if (-not $basePath) { continue }
        foreach ($directory in @('anaconda', 'anaconda3', 'miniconda3', 'miniforge3')) {
            $condaCandidates += Join-Path $basePath "$directory/condabin/conda.bat"
        }
    }
    $Config.CondaPath = Resolve-LauncherTool $RequestedConda 'conda' $condaCandidates
    $Config.NpmPath = Resolve-LauncherTool $RequestedNpm 'npm.cmd'
    $null = Resolve-LauncherTool '' 'node' @((Join-Path (Split-Path -Parent $Config.NpmPath) 'node.exe'))
    foreach ($required in @('backend/main.py', 'web/package.json')) {
        if (-not (Test-Path -LiteralPath (Join-Path $Config.Root $required) -PathType Leaf)) {
            throw "Project file missing: $required"
        }
    }
    if (-not (Test-Path -LiteralPath (Join-Path $Config.Root 'web/node_modules/vite/bin/vite.js') -PathType Leaf)) {
        throw "Frontend dependencies are missing. Run npm ci in: $(Join-Path $Config.Root 'web')"
    }
    Write-Host 'Checking the BIGONE Conda environment...'
    $importCheck = 'import fastapi, uvicorn'
    if ($Config.Observe) { $importCheck += ', openai' }
    & $Config.CondaPath run --no-capture-output -n BIGONE python -c $importCheck | ForEach-Object { Write-Host $_ }
    if ($LASTEXITCODE -ne 0) {
        throw 'The BIGONE environment or backend dependencies are unavailable. See README.md for setup.'
    }
    Write-Host "Conda: $($Config.CondaPath)"
    Write-Host "npm:   $($Config.NpmPath)"
}

function Get-ProjectServiceCommand {
    param($Config, [ValidateSet('Backend', 'Frontend')][string]$Name)
    if ($Name -eq 'Backend') {
        $entry = if ($Config.Observe) { 'evaluation.observed_app:app' } else { 'backend.main:app' }
        return [pscustomobject]@{
            FilePath = $Config.CondaPath
            Arguments = @('run', '--no-capture-output', '-n', 'BIGONE', 'python', '-u', '-m', 'uvicorn', $entry,
                          '--host', '127.0.0.1', '--port', $Config.BackendPort.ToString())
            WorkingDirectory = $Config.Root
        }
    }
    [pscustomobject]@{
        FilePath = $Config.NpmPath
        Arguments = @('run', 'dev', '--', '--port', $Config.FrontendPort.ToString())
        WorkingDirectory = Join-Path $Config.Root 'web'
    }
}

function Join-ProjectProcessArguments {
    param([string[]]$Arguments)
    # Start-Process joins its argument array; quote each path explicitly for Windows.
    ($Arguments | ForEach-Object {
        if ($_ -match '"' -or $_ -match '[\r\n]') { throw 'Unexpected character in a launcher argument.' }
        '"' + $_ + '"'
    }) -join ' '
}

function New-ProjectProcessIdentity {
    param([Diagnostics.Process]$Process, [string]$Name)
    [pscustomobject]@{
        Name = $Name
        ProcessId = $Process.Id
        StartedAtUtc = $Process.StartTime.ToUniversalTime().ToString('o')
    }
}

function Get-OwnedProjectProcess {
    param($Identity)
    if (-not $Identity -or -not $Identity.ProcessId -or -not $Identity.StartedAtUtc) { return $null }
    $serviceProcess = Get-Process -Id $Identity.ProcessId -ErrorAction SilentlyContinue
    if (-not $serviceProcess) { return $null }
    try {
        if ($serviceProcess.StartTime.ToUniversalTime().ToString('o') -eq $Identity.StartedAtUtc) { return $serviceProcess }
    } catch { return $null }
    return $null
}

function Start-ManagedProjectService {
    param($Config, [ValidateSet('Backend', 'Frontend')][string]$Name)
    $port = if ($Name -eq 'Backend') { $Config.BackendPort } else { $Config.FrontendPort }
    $arguments = @('-NoLogo', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', $Config.ScriptPath,
                   '-Service', $Name, '-ServicePort', $port.ToString(), '-CondaPath', $Config.CondaPath,
                   '-NpmPath', $Config.NpmPath)
    if ($Config.Observe) { $arguments += '-Observe' }
    $outputLog = Join-Path $Config.LogDirectory ('launcher-' + $Name.ToLowerInvariant() + '.out.log')
    $errorLog = Join-Path $Config.LogDirectory ('launcher-' + $Name.ToLowerInvariant() + '.err.log')
    $serviceProcess = Start-Process -FilePath $Config.PowerShellPath -ArgumentList (Join-ProjectProcessArguments $arguments) `
        -WorkingDirectory $Config.Root -WindowStyle Hidden -PassThru -RedirectStandardOutput $outputLog -RedirectStandardError $errorLog
    New-ProjectProcessIdentity $serviceProcess $Name
}

function Stop-OwnedProjectServices {
    param([object[]]$Identities)
    $taskkill = Join-Path $env:SystemRoot 'System32/taskkill.exe'
    $stopErrors = @()
    foreach ($identity in $Identities) {
        $serviceProcess = Get-OwnedProjectProcess $identity
        if (-not $serviceProcess) { continue }
        $previousErrorAction = $ErrorActionPreference
        try {
            # A second stop request can race with the controller's own cleanup.
            $ErrorActionPreference = 'Continue'
            $killOutput = & $taskkill /PID $serviceProcess.Id /T /F 2>&1
            $killResult = $LASTEXITCODE
        } finally { $ErrorActionPreference = $previousErrorAction }
        if ($killResult -ne 0 -and (Get-OwnedProjectProcess $identity)) {
            $stopErrors += "Could not stop managed $($identity.Name) process $($identity.ProcessId): $killOutput"
        }
    }
    if ($stopErrors.Count) { throw ($stopErrors -join [Environment]::NewLine) }
}

function Read-ProjectLaunchState {
    param($Config)
    if (-not (Test-Path -LiteralPath $Config.StatePath -PathType Leaf)) { return $null }
    try {
        $state = Get-Content -LiteralPath $Config.StatePath -Raw -Encoding UTF8 | ConvertFrom-Json
        if ($state.ProjectRoot -eq $Config.Root -and $state.LaunchId -and @($state.Services).Count) { return $state }
    } catch { return $null }
    return $null
}

function Write-ProjectLaunchState {
    param($Config, $State)
    $temporaryPath = $Config.StatePath + '.' + [guid]::NewGuid().ToString('N') + '.tmp'
    $json = $State | ConvertTo-Json -Depth 6
    try {
        [IO.File]::WriteAllText($temporaryPath, $json, [Text.Encoding]::UTF8)
        for ($attempt = 0; $attempt -lt 5; $attempt++) {
            try {
                if (Test-Path -LiteralPath $Config.StatePath) { [IO.File]::Replace($temporaryPath, $Config.StatePath, [NullString]::Value) }
                else { [IO.File]::Move($temporaryPath, $Config.StatePath) }
                return
            } catch [IO.IOException] { Start-Sleep -Milliseconds 100 }
        }
        # Windows readers can allow writes while denying rename/delete sharing.
        # State readers reject incomplete JSON and retry on the next controller tick.
        [IO.File]::WriteAllText($Config.StatePath, $json, [Text.Encoding]::UTF8)
    } finally {
        if (Test-Path -LiteralPath $temporaryPath) { [IO.File]::Delete($temporaryPath) }
    }
}

function Test-ProjectHttpReady {
    param([string]$Url, [switch]$Backend)
    try {
        $response = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 2
        if ($response.StatusCode -ne 200) { return $false }
        if ($Backend) {
            $content = $response.Content
            if ($content -is [byte[]]) { $content = [Text.Encoding]::UTF8.GetString($content) }
            return ($content | ConvertFrom-Json).status -eq 'ok'
        }
        return $true
    } catch { return $false }
}

function Wait-ProjectServices {
    param($Config, [object[]]$Identities, [int]$TimeoutSeconds)
    $deadline = [DateTime]::UtcNow.AddSeconds($TimeoutSeconds)
    do {
        foreach ($identity in $Identities) {
            if (-not (Get-OwnedProjectProcess $identity)) {
                throw "$($identity.Name) exited before startup completed. Check launcher logs in: $($Config.LogDirectory)"
            }
        }
        if ((Test-ProjectHttpReady $Config.BackendUrl -Backend) -and (Test-ProjectHttpReady $Config.FrontendUrl)) { return }
        Start-Sleep -Milliseconds 400
    } while ([DateTime]::UtcNow -lt $deadline)
    throw "Startup timed out. Check launcher logs in: $($Config.LogDirectory)"
}

function Get-ProjectPortConflicts {
    param($Config)
    @(Get-NetTCPConnection -State Listen -ErrorAction SilentlyContinue |
        Where-Object { $_.LocalPort -in @($Config.BackendPort, $Config.FrontendPort) } |
        Select-Object LocalPort, OwningProcess -Unique)
}

function Invoke-ProjectLauncher {
    param($Config)
    if ($Stop) {
        $state = Read-ProjectLaunchState $Config
        if (-not $state) { Write-Host 'No saved B1GONE launcher session was found.'; return 0 }
        $state.StopRequested = $true
        Write-ProjectLaunchState $Config $state
        Stop-OwnedProjectServices @($state.Services)
        if (-not (Get-OwnedProjectProcess $state.Controller)) { Remove-Item -LiteralPath $Config.StatePath -Force }
        Write-Host 'Managed B1GONE services stopped.'
        return 0
    }
    if ($CheckOnly) {
        Assert-ProjectLaunchDependencies $Config $CondaPath $NpmPath
        $conflicts = Get-ProjectPortConflicts $Config
        if ($conflicts.Count) { Write-Host ('Currently occupied ports: ' + (($conflicts.LocalPort | Sort-Object -Unique) -join ', ')) }
        Write-Host 'Checks passed. No services were started.'
        return 0
    }

    $null = New-Item -ItemType Directory -Path $Config.LogDirectory -Force
    $serviceLock = $null
    $started = @()
    $launchId = [guid]::NewGuid().ToString('N')
    try {
        try { $serviceLock = [IO.File]::Open($Config.LockPath, [IO.FileMode]::OpenOrCreate, [IO.FileAccess]::ReadWrite, [IO.FileShare]::None) }
        catch [IO.IOException] {
            $existing = Read-ProjectLaunchState $Config
            if ($existing -and -not $existing.StopRequested -and
                @($existing.Services | Where-Object { Get-OwnedProjectProcess $_ }).Count -eq 2 -and
                (Test-ProjectHttpReady $Config.BackendUrl -Backend) -and (Test-ProjectHttpReady $Config.FrontendUrl)) {
                $mode = if ($existing.Observe) { 'observation enabled' } else { 'normal mode' }
                Write-Host "B1GONE is already running ($mode): $($Config.FrontendUrl)"
                if (-not $NoBrowser) { Start-Process -FilePath $Config.FrontendUrl }
            } else { Write-Host 'Another B1GONE launcher is starting or stopping. Check its control window.' }
            return 0
        }
        $existing = Read-ProjectLaunchState $Config
        if ($existing) { Stop-OwnedProjectServices @($existing.Services); Remove-Item -LiteralPath $Config.StatePath -Force }
        Assert-ProjectLaunchDependencies $Config $CondaPath $NpmPath
        $conflicts = Get-ProjectPortConflicts $Config
        if ($conflicts.Count) {
            $details = ($conflicts | ForEach-Object { "$($_.LocalPort) (PID $($_.OwningProcess))" }) -join ', '
            throw "Ports already in use: $details. Stop the existing services in their original terminals, then try again."
        }

        $mode = if ($Config.Observe) { 'observation enabled' } else { 'normal mode' }
        Write-Host "Starting B1GONE ($mode)..."
        $controller = New-ProjectProcessIdentity (Get-Process -Id $PID) 'Controller'
        foreach ($name in @('Backend', 'Frontend')) {
            $started += Start-ManagedProjectService $Config $name
            Write-ProjectLaunchState $Config ([pscustomobject]@{
                ProjectRoot = $Config.Root; LaunchId = $launchId; Observe = $Config.Observe
                Controller = $controller; Services = $started; StopRequested = $false
            })
        }
        Wait-ProjectServices $Config $started $StartupTimeout
        Write-Host "Ready: $($Config.FrontendUrl)"
        Write-Host "Logs:  $($Config.LogDirectory)"
        Write-Host 'Keep this window open. Press Enter or Q to stop both services; Ctrl+C also exits.'
        if (-not $NoBrowser) { Start-Process -FilePath $Config.FrontendUrl }
        while ($true) {
            if ([Console]::KeyAvailable) {
                $key = [Console]::ReadKey($true)
                if ($key.Key -in @([ConsoleKey]::Enter, [ConsoleKey]::Q)) { break }
            }
            $currentState = Read-ProjectLaunchState $Config
            if ($currentState -and $currentState.StopRequested) { break }
            foreach ($identity in $started) {
                if (-not (Get-OwnedProjectProcess $identity)) {
                    throw "$($identity.Name) stopped unexpectedly. Check logs in: $($Config.LogDirectory)"
                }
            }
            Start-Sleep -Milliseconds 400
        }
        return 0
    } finally {
        try { Stop-OwnedProjectServices $started }
        finally {
            $currentState = Read-ProjectLaunchState $Config
            if ($currentState -and $currentState.LaunchId -eq $launchId) { Remove-Item -LiteralPath $Config.StatePath -Force }
            if ($serviceLock) { $serviceLock.Dispose() }
        }
    }
}

# Dot-sourcing loads functions for isolated launcher tests without starting services.
if ($MyInvocation.InvocationName -ne '.') {
    try {
        $config = New-ProjectLaunchConfig (Split-Path -Parent $PSScriptRoot) ([bool]$Observe)
        if ($Service) {
            $config.CondaPath = $CondaPath
            $config.NpmPath = $NpmPath
            if ($Service -eq 'Backend') { $config.BackendPort = $ServicePort }
            else { $config.FrontendPort = $ServicePort; $env:PATH = (Split-Path -Parent $NpmPath) + ';' + $env:PATH }
            $command = Get-ProjectServiceCommand $config $Service
            Push-Location -LiteralPath $command.WorkingDirectory
            try { & $command.FilePath @($command.Arguments); exit $LASTEXITCODE }
            finally { Pop-Location }
        }
        exit (Invoke-ProjectLauncher $config)
    } catch {
        Write-Host "B1GONE launcher: $($_.Exception.Message)" -ForegroundColor Red
        exit 1
    }
}
