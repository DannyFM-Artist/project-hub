# Creates or replaces the Startup shortcut that launches the project-hub tray app at login.
# Dry run by default (prints what it would do); pass -Apply to write the shortcut.
param([switch]$Apply)

$exe = (Get-Command project-hub-tray -ErrorAction Stop).Source
$icon = Join-Path (Split-Path $PSScriptRoot) 'project_hub\static\icons\app.ico'
if (-not (Test-Path $icon)) {
    $icon = python -c "import project_hub,pathlib;print(pathlib.Path(project_hub.__file__).parent/'static'/'icons'/'app.ico')"
}
$lnk = Join-Path $env:APPDATA 'Microsoft\Windows\Start Menu\Programs\Startup\project-hub dashboard.lnk'
$action = if (Test-Path $lnk) { 'replace' } else { 'create' }

Write-Output "Shortcut: $lnk ($action)"
Write-Output "Target:   $exe"
Write-Output "Icon:     $icon"
Write-Output "Args:     (none)"
if (-not $Apply) { Write-Output 'Dry run: nothing written. Run with -Apply to write it.'; return }

$s = (New-Object -ComObject WScript.Shell).CreateShortcut($lnk)
$s.TargetPath = $exe
$s.IconLocation = $icon
$s.WorkingDirectory = Split-Path $exe
$s.Save()
Write-Output 'Written.'
