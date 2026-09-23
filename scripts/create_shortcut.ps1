[CmdletBinding()]
param([string]$OutputPath)

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot
$launcher = Join-Path $repoRoot "ResearchAgent-启动.bat"
$icon = Join-Path $repoRoot "web\app\favicon.ico"
if (-not (Test-Path -LiteralPath $launcher -PathType Leaf)) {
  throw "Launcher not found: $launcher"
}
if (-not (Test-Path -LiteralPath $icon -PathType Leaf)) {
  throw "Icon not found: $icon"
}
if (-not $OutputPath) {
  $OutputPath = Join-Path $repoRoot "ResearchAgent-新版.lnk"
} elseif (-not [IO.Path]::IsPathRooted($OutputPath)) {
  $OutputPath = Join-Path $repoRoot $OutputPath
}
$OutputPath = [IO.Path]::GetFullPath($OutputPath)
if (-not (Test-Path -LiteralPath (Split-Path -Parent $OutputPath) -PathType Container)) {
  throw "Shortcut directory not found: $(Split-Path -Parent $OutputPath)"
}
$shortcut = (New-Object -ComObject WScript.Shell).CreateShortcut($OutputPath)
$shortcut.TargetPath = $launcher
$shortcut.WorkingDirectory = $repoRoot
$shortcut.IconLocation = "$icon,0"
$shortcut.Description = "ResearchAgent 新版（8000 / 3000）"
$shortcut.WindowStyle = 1
$shortcut.Save()
Write-Output $OutputPath
