param([string]$PythonPath = 'D:\anaconda\envs\BIGONE\python.exe', [switch]$RealServices)
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot '../start_project.ps1')
$script:checkCount = 0

function Assert-LauncherCheck {
    param([bool]$Condition, [string]$Message)
    if (-not $Condition) { throw "FAILED: $Message" }
    $script:checkCount += 1
    Write-Host "PASS: $Message"
}

function Get-UnusedTestPort {
    $listener = New-Object Net.Sockets.TcpListener([Net.IPAddress]::Loopback, 0)
    $listener.Start()
    try { return $listener.LocalEndpoint.Port }
    finally { $listener.Stop() }
}

$projectRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
# Exercise spaces and Unicode without depending on PowerShell 5.1 source encoding.
$unicodeSuffix = [string][char]0x6D4B + [char]0x8BD5
$fixtureRoot = Join-Path $projectRoot ('tmp/launcher space ' + $unicodeSuffix + '-' + [guid]::NewGuid().ToString('N'))
$fixtureScripts = Join-Path $fixtureRoot 'scripts'
$null = New-Item -ItemType Directory -Path $fixtureScripts -Force
$config = New-ProjectLaunchConfig $fixtureRoot
$config.CondaPath = $PythonPath
$config.NpmPath = $PythonPath
$config.BackendPort = Get-UnusedTestPort
do { $config.FrontendPort = Get-UnusedTestPort } while ($config.FrontendPort -eq $config.BackendPort)
$config.BackendUrl = "http://127.0.0.1:$($config.BackendPort)/health"
$config.FrontendUrl = "http://127.0.0.1:$($config.FrontendPort)/"
$null = New-Item -ItemType Directory -Path $config.LogDirectory -Force

$command = Get-ProjectServiceCommand $config 'Backend'
Assert-LauncherCheck ($command.Arguments -contains 'backend.main:app') 'normal mode keeps the original backend entry'
Assert-LauncherCheck (-not ($command.Arguments -contains '--reload')) 'daily launch does not enable backend reload'
Assert-LauncherCheck ($command.WorkingDirectory -eq $fixtureRoot) 'backend runs at the project root'
$config.Observe = $true
$command = Get-ProjectServiceCommand $config 'Backend'
Assert-LauncherCheck ($command.Arguments -contains 'evaluation.observed_app:app') 'observation mode selects the independent observer'
$frontend = Get-ProjectServiceCommand $config 'Frontend'
Assert-LauncherCheck ($frontend.WorkingDirectory -eq (Join-Path $fixtureRoot 'web')) 'frontend runs inside web'
$quoted = Join-ProjectProcessArguments @('-File', $config.ScriptPath)
Assert-LauncherCheck ($quoted.Contains('"' + $config.ScriptPath + '"')) 'spaces and Unicode paths remain quoted'

# The fixture launches only disposable HTTP servers, never the research backend.
$fixtureScript = @'
param([string]$Service, [int]$ServicePort, [string]$CondaPath, [string]$NpmPath, [switch]$Observe)
& $CondaPath -u -m http.server $ServicePort --bind 127.0.0.1
exit $LASTEXITCODE
'@
[IO.File]::WriteAllText($config.ScriptPath, $fixtureScript, [Text.Encoding]::UTF8)
[IO.File]::WriteAllText((Join-Path $fixtureRoot 'health'), '{"status":"ok"}', [Text.Encoding]::ASCII)

$owned = @()
try {
    $owned += Start-ManagedProjectService $config 'Backend'
    $owned += Start-ManagedProjectService $config 'Frontend'
    Wait-ProjectServices $config $owned 25
    Assert-LauncherCheck (Test-ProjectHttpReady $config.BackendUrl -Backend) 'health check waits for valid backend JSON'
    Assert-LauncherCheck (Test-ProjectHttpReady $config.FrontendUrl) 'frontend readiness is verified'

    $state = [pscustomobject]@{
        ProjectRoot = $config.Root; LaunchId = 'test'; Observe = $true
        Controller = New-ProjectProcessIdentity (Get-Process -Id $PID) 'Controller'
        Services = $owned; StopRequested = $false
    }
    Write-ProjectLaunchState $config $state
    $restored = Read-ProjectLaunchState $config
    Assert-LauncherCheck (@($restored.Services).Count -eq 2) 'managed identities round-trip through saved state'
    $state.StopRequested = $true
    Write-ProjectLaunchState $config $state
    Assert-LauncherCheck ((Read-ProjectLaunchState $config).StopRequested) 'saved state supports a stop request'
    $state.ProjectRoot = Join-Path $fixtureRoot 'other-project'
    Write-ProjectLaunchState $config $state
    Assert-LauncherCheck ($null -eq (Read-ProjectLaunchState $config)) 'state belonging to another checkout is rejected'

    $wrongIdentity = [pscustomobject]@{
        Name = 'Wrong'; ProcessId = $owned[0].ProcessId
        StartedAtUtc = [DateTime]::UtcNow.AddYears(-1).ToString('o')
    }
    Stop-OwnedProjectServices @($wrongIdentity)
    Assert-LauncherCheck ($null -ne (Get-OwnedProjectProcess $owned[0])) 'a mismatched process start time cannot stop a live process'

    $unready = New-ProjectLaunchConfig $fixtureRoot
    $unready.BackendUrl = $config.BackendUrl
    $unready.FrontendUrl = "http://127.0.0.1:$(Get-UnusedTestPort)/"
    $timedOut = $false
    try { Wait-ProjectServices $unready $owned 1 }
    catch { $timedOut = $_.Exception.Message -match 'timed out' }
    Assert-LauncherCheck $timedOut 'startup fails clearly when a service never becomes ready'

    $listening = @(Get-NetTCPConnection -State Listen -ErrorAction Stop |
        Where-Object { $_.LocalPort -in @($config.BackendPort, $config.FrontendPort) })
    Assert-LauncherCheck ($listening.Count -eq 2) 'only the two disposable test ports are used'
    Stop-OwnedProjectServices $owned
    $deadline = [DateTime]::UtcNow.AddSeconds(8)
    do {
        $remaining = @(Get-ProjectPortConflicts $config)
        if (-not $remaining.Count) { break }
        Start-Sleep -Milliseconds 200
    } while ([DateTime]::UtcNow -lt $deadline)
    Assert-LauncherCheck (-not $remaining.Count) 'stopping helpers releases their child server ports'
    Assert-LauncherCheck (-not @($owned | Where-Object { Get-OwnedProjectProcess $_ }).Count) 'both managed helper processes exit'

    $failedEarly = $false
    try { Wait-ProjectServices $config $owned 5 }
    catch { $failedEarly = $_.Exception.Message -match 'exited before startup' }
    Assert-LauncherCheck $failedEarly 'early service exit is detected without waiting for the timeout'
} finally {
    Stop-OwnedProjectServices $owned
}

if ($RealServices) {
    $realConfig = New-ProjectLaunchConfig $projectRoot $true
    Assert-ProjectLaunchDependencies $realConfig '' ''
    $realConfig.BackendPort = Get-UnusedTestPort
    do { $realConfig.FrontendPort = Get-UnusedTestPort } while ($realConfig.FrontendPort -eq $realConfig.BackendPort)
    $realConfig.BackendUrl = "http://127.0.0.1:$($realConfig.BackendPort)/health"
    $realConfig.FrontendUrl = "http://127.0.0.1:$($realConfig.FrontendPort)/"
    $realOwned = @()
    try {
        $realOwned += Start-ManagedProjectService $realConfig 'Backend'
        $realOwned += Start-ManagedProjectService $realConfig 'Frontend'
        Wait-ProjectServices $realConfig $realOwned 90
        Assert-LauncherCheck (Test-ProjectHttpReady $realConfig.BackendUrl -Backend) 'real observed backend starts in BIGONE on a separate test port'
        Assert-LauncherCheck (Test-ProjectHttpReady $realConfig.FrontendUrl) 'real Vite frontend starts on a separate test port'
        Stop-OwnedProjectServices $realOwned
        $deadline = [DateTime]::UtcNow.AddSeconds(8)
        do {
            $remaining = @(Get-ProjectPortConflicts $realConfig)
            if (-not $remaining.Count) { break }
            Start-Sleep -Milliseconds 200
        } while ([DateTime]::UtcNow -lt $deadline)
        Assert-LauncherCheck (-not $remaining.Count) 'real test services release their ports when stopped'
    } finally { Stop-OwnedProjectServices $realOwned }

    $batchFile = Get-ChildItem -LiteralPath $projectRoot -Filter '*.bat' | Select-Object -First 1
    $batchOutput = ' ' | & $env:ComSpec /d /c ('"' + $batchFile.FullName + '" -CheckOnly')
    $batchExit = $LASTEXITCODE
    $batchOutput | ForEach-Object { Write-Host $_ }
    Assert-LauncherCheck ($batchExit -eq 0) 'the Unicode-named BAT forwards its arguments and returns success'
    Assert-LauncherCheck (($batchOutput -join ' ') -match 'No services were started') 'BAT check-only mode does not start project services'
}

Write-Host "Launcher checks passed: $script:checkCount. No research or model calls were made."
