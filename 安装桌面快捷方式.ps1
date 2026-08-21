$ErrorActionPreference = "Stop"

$projectRoot = $PSScriptRoot
$launcherPath = Join-Path $projectRoot "ResearchAgent-启动.bat"
$iconPath = Join-Path $projectRoot "ResearchAgent.ico"
$desktopPath = [Environment]::GetFolderPath("Desktop")
$shortcutPath = Join-Path $desktopPath "ResearchAgent.lnk"

if (-not (Test-Path -LiteralPath $launcherPath)) {
  throw "Launcher not found: $launcherPath"
}
if (-not (Test-Path -LiteralPath $iconPath)) {
  throw "Icon not found: $iconPath"
}

$shell = New-Object -ComObject WScript.Shell
$shortcut = $shell.CreateShortcut($shortcutPath)
$shortcut.TargetPath = $launcherPath
$shortcut.WorkingDirectory = $projectRoot
$shortcut.IconLocation = "$iconPath,0"
$shortcut.Description = "Start Research Agent"
$shortcut.Save()

Write-Host "Desktop shortcut created: $shortcutPath" -ForegroundColor Green
