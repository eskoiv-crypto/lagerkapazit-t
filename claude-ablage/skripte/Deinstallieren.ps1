#Requires -Version 5.1
<#
.SYNOPSIS
    Entfernt Download-Sortierer, Verknüpfungen und lokale Skripte. Die Ablage in SharePoint bleibt UNVERÄNDERT.

.DESCRIPTION
    Version 1.0 · 2026-09-28
#>
[CmdletBinding()]
param([switch]$KonfigBehalten)

$aufgabeName = 'Claude-Ablage Downloads-Sortieren'
if ((Read-Host 'Sortierer, Verknüpfungen und lokale Skripte entfernen? Die SharePoint-Ablage bleibt erhalten. (J/N)') -notmatch '^[JjYy]') {
    Write-Host 'Abgebrochen.'; return
}
Unregister-ScheduledTask -TaskName $aufgabeName -Confirm:$false -ErrorAction SilentlyContinue
Get-CimInstance Win32_Process -Filter "Name='powershell.exe'" -ErrorAction SilentlyContinue |
    Where-Object { $_.CommandLine -like '*Downloads-Sortieren.ps1*-Dauerbetrieb*' } |
    ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }

foreach ($lnk in @(
        (Join-Path ([Environment]::GetFolderPath('Startup')) 'Claude-Ablage Downloads-Sortieren.lnk'),
        (Join-Path ([Environment]::GetFolderPath('Desktop')) 'Neues Claude-Projekt.lnk'),
        (Join-Path ([Environment]::GetFolderPath('Desktop')) 'Claude-Projekte.lnk'))) {
    if (Test-Path -LiteralPath $lnk) { Remove-Item -LiteralPath $lnk -Force }
}

$install = Join-Path $env:LOCALAPPDATA 'ClaudeAblage'
if (Test-Path -LiteralPath $install) {
    Get-ChildItem -LiteralPath $install -File | Where-Object { -not ($KonfigBehalten -and $_.Name -in @('config.json', 'migration-regeln.csv')) } |
        Remove-Item -Force
}
Write-Host "Entfernt. Protokolle liegen weiter unter $install\Protokoll." -ForegroundColor Green
