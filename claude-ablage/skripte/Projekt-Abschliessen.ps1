#Requires -Version 5.1
<#
.SYNOPSIS
    Schließt ein Projekt ab: Status "Abgeschlossen (Datum)" und Umzug nach <Bereich>\_Archiv.

.DESCRIPTION
    Version 1.0 · 2026-09-28
    Der Ordner wird verschoben, nicht kopiert – SharePoint behält den Versionsverlauf.
    Downloads mit der Kennung werden weiterhin ins archivierte Projekt einsortiert.

.EXAMPLE
    .\Projekt-Abschliessen.ps1 -Kennung FIN-001
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory)][string]$Kennung,
    [switch]$OhneRueckfrage
)

Import-Module (Join-Path $PSScriptRoot 'AblageKern.psm1') -Force
$konfig = Read-AblageKonfig
$projekt = Find-AblageProjekt -Konfig $konfig -Kennung $Kennung
if (-not $projekt) { throw "Projekt $Kennung nicht gefunden." }
if ($projekt.Archiviert) { Write-Host "$($projekt.Kennung) ist bereits archiviert: $($projekt.Pfad)"; return }

if (-not $OhneRueckfrage) {
    $antwort = Read-Host ("{0}_{1} abschließen und nach _Archiv verschieben? (J/N)" -f $projekt.Kennung, $projekt.Titel)
    if ($antwort -notmatch '^[JjYy]') { Write-Host 'Abgebrochen – nichts geändert.'; return }
}

$bereich = Get-Bereich -Konfig $konfig -Kuerzel $projekt.Bereich
$archiv = Join-Path (Join-Path $konfig.Ablage $bereich.Ordner) '_Archiv'
if (-not (Test-Path -LiteralPath $archiv)) { New-Item -ItemType Directory -Path $archiv -Force | Out-Null }
$ziel = Join-Path $archiv (Split-Path -Leaf $projekt.Pfad)
if (Test-Path -LiteralPath $ziel) { throw "Im Archiv existiert bereits ein Ordner $ziel – bitte von Hand prüfen." }

Set-ProjektFeld -ProjektPfad $projekt.Pfad -Feld 'Status' -Wert ('Abgeschlossen ({0})' -f (Get-Date -Format 'yyyy-MM-dd'))
Move-Item -LiteralPath $projekt.Pfad -Destination $ziel
Write-Ablageprotokoll -Konfig $konfig -Aktion 'Projekt abgeschlossen' -Datei $projekt.Kennung -Ziel $ziel
Write-AblageLog -Meldung "Projekt abgeschlossen: $($projekt.Kennung) -> $ziel"
Update-Projektregister -Konfig $konfig | Out-Null
Write-Host "Abgeschlossen: $ziel" -ForegroundColor Green
