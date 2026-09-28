#Requires -Version 5.1
<#
.SYNOPSIS
    Einmalige Einrichtung der Claude-Ablage (Team "Eskofier").

.DESCRIPTION
    Version 1.0 · 2026-09-28
    1. Findet die synchronisierte Bibliothek der Teams-Seite "Eskofier" (oder fragt nach dem Pfad).
    2. Legt die Struktur an: 00_Eingang, Bereiche, 99_Vorlagen, _System, LIESMICH.md.
    3. Installiert die Skripte nach %LOCALAPPDATA%\ClaudeAblage und schreibt config.json.
    4. Legt die Bestandsprojekte an: Otto-Obligo, Frachtkostenrechner, Warenwert-Bestandsrechner.
    5. Richtet den Download-Sortierer ein (Aufgabenplanung bei Anmeldung, sonst Autostart).
    6. Legt Desktop-Verknüpfungen an: "Neues Claude-Projekt" und "Claude-Projekte".

    Das Skript kann gefahrlos erneut ausgeführt werden: Vorhandenes bleibt erhalten, nichts wird überschrieben.

.EXAMPLE
    .\Einrichten.ps1
    .\Einrichten.ps1 -Ablage "C:\Users\ich\elvinci.de GmbH\Eskofier - Dokumente\Allgemein\Claude-Projekte"
#>
[CmdletBinding()]
param(
    [string]$Ablage,
    [switch]$OhneAufgabe,
    [switch]$OhneVerknuepfungen,
    [switch]$OhneBestandsprojekte,
    [switch]$Ja
)

$ErrorActionPreference = 'Stop'
$quelle = $PSScriptRoot
Import-Module (Join-Path $quelle 'AblageKern.psm1') -Force

function Frage-JaNein([string]$Text) {
    if ($Ja) { return $true }
    return ((Read-Host "$Text (J/N)") -match '^[JjYy]')
}
function Schritt([string]$Text) { Write-Host ''; Write-Host "» $Text" -ForegroundColor Cyan }

Write-Host ''
Write-Host '  Claude-Ablage · Einrichtung · v1.0' -ForegroundColor Cyan
Write-Host '  ==================================='

# ---------------------------------------------------------------- 1. Ablage finden
Schritt 'Ablage suchen'
if (-not $Ablage) {
    $kandidaten = @(Get-SyncOrdner | Where-Object { $_.Url -match '/sites/Eskofier' })
    if ($kandidaten.Count -eq 0 -and $env:USERPROFILE) {
        # Rückfall: OneDrive legt SharePoint-Bibliotheken unter %USERPROFILE%\<Organisation>\<Seite> - <Bibliothek> ab
        $kandidaten = @(Get-ChildItem -LiteralPath $env:USERPROFILE -Directory -ErrorAction SilentlyContinue |
            ForEach-Object { Get-ChildItem -LiteralPath $_.FullName -Directory -Filter 'Eskofier*' -ErrorAction SilentlyContinue } |
            ForEach-Object { [pscustomobject]@{ Url = ''; Pfad = $_.FullName } })
    }
    $basis = $null
    if ($kandidaten.Count -eq 1) {
        $basis = $kandidaten[0].Pfad
    } elseif ($kandidaten.Count -gt 1) {
        for ($i = 0; $i -lt $kandidaten.Count; $i++) { Write-Host ('  [{0}] {1}  {2}' -f ($i + 1), $kandidaten[$i].Pfad, $kandidaten[$i].Url) }
        $wahl = [int](Read-Host '  Welche Bibliothek? (Nummer)')
        $basis = $kandidaten[$wahl - 1].Pfad
    }
    if (-not $basis) {
        Write-Host '  Keine synchronisierte Eskofier-Bibliothek gefunden.' -ForegroundColor Yellow
        Write-Host '  Bitte in Teams › Eskofier › Dateien › "In SharePoint öffnen" › "Synchronisieren" klicken,'
        Write-Host '  oder hier den lokalen Pfad der Bibliothek einfügen (Explorer › Adressleiste kopieren).'
        $basis = (Read-Host '  Pfad').Trim('"', ' ')
    }
    if (-not (Test-Path -LiteralPath $basis)) { throw "Pfad existiert nicht: $basis" }
    foreach ($kanal in @('Allgemein', 'General')) {
        if (Test-Path -LiteralPath (Join-Path $basis $kanal)) { $basis = Join-Path $basis $kanal; break }
    }
    $Ablage = Join-Path $basis 'Claude-Projekte'
}
$Ablage = [IO.Path]::GetFullPath($Ablage)
Write-Host "  Ablage: $Ablage"
if (-not (Frage-JaNein '  Diesen Ort verwenden?')) { Write-Host '  Abgebrochen – nichts geändert.'; return }

# ---------------------------------------------------------------- 2. Konfiguration
Schritt 'Konfiguration'
$konfigPfad = Get-AblageKonfigPfad
if (Test-Path -LiteralPath $konfigPfad) {
    $konfig = Read-AblageKonfig
    Write-Host '  Vorhandene config.json wird weiterverwendet (Bereiche/Einstellungen bleiben).'
} else {
    $konfig = Get-StandardKonfig
}
$konfig.Ablage = $Ablage
Write-Host "  Download-Ordner: $($konfig.Downloadordner)"
if (-not $Ja) {
    $anderer = (Read-Host '  Stimmt das? Enter = ja, sonst Pfad eingeben (Chrome › Einstellungen › Downloads)').Trim('"', ' ')
    if ($anderer) {
        if (-not (Test-Path -LiteralPath $anderer)) { throw "Download-Ordner existiert nicht: $anderer" }
        $konfig.Downloadordner = $anderer
    }
}

# ---------------------------------------------------------------- 3. Skripte installieren
Schritt 'Skripte installieren'
$installPfad = Get-AblageInstallPfad
if (-not (Test-Path -LiteralPath $installPfad)) { New-Item -ItemType Directory -Path $installPfad -Force | Out-Null }
$quelleVoll = [IO.Path]::GetFullPath($quelle).TrimEnd('\', '/')
if ($quelleVoll -ne [IO.Path]::GetFullPath($installPfad).TrimEnd('\', '/')) {
    foreach ($datei in Get-ChildItem -LiteralPath $quelle -File) {
        $ziel = Join-Path $installPfad $datei.Name
        if ($datei.Name -eq 'migration-regeln.csv' -and (Test-Path -LiteralPath $ziel)) { continue }   # eigene Anpassungen behalten
        Copy-Item -LiteralPath $datei.FullName -Destination $ziel -Force
    }
}
if ($IstWindows) { Get-ChildItem -LiteralPath $installPfad -File | Unblock-File -ErrorAction SilentlyContinue }
Save-AblageKonfig -Konfig $konfig
Write-Host "  Installiert nach $installPfad"

# ---------------------------------------------------------------- 4. Struktur + Bestandsprojekte
Schritt 'Ordnerstruktur anlegen'
Initialize-AblageStruktur -Konfig $konfig
$konfig.Bereiche | ForEach-Object { Write-Host ('  {0}  {1}' -f $_.Kuerzel, $_.Ordner) }

if (-not $OhneBestandsprojekte) {
    Schritt 'Bestandsprojekte anlegen'
    $bestand = @(
        @{ K = 'FIN'; T = 'Otto-Obligo'; B = 'Obligo gegenüber Otto vs. Kreditlimit: Status-PDFs, Forecast, Obligo-Cockpit'
           L = 'https://elvinci.sharepoint.com/sites/PlattformenTeams/Freigegebene Dokumente/Tools und Automatisieren/KI-Tools/Otto_Obligo_View' }
        @{ K = 'LOG'; T = 'Frachtkostenrechner'; B = 'Frachtkostenrechner auf Basis der AMM-Tarife (v6 gültig ab 01.07.2026)'
           L = 'https://elvinci.sharepoint.com/sites/PlattformenTeams/Freigegebene Dokumente/Tools und Automatisieren/KI-Tools/Frachtkostenrechner' }
        @{ K = 'BES'; T = 'Warenwert-Bestandsrechner'; B = 'Warenwert/Bestandsbewertung zum Monatsende'; L = '' }
    )
    foreach ($p in $bestand) {
        $r = New-AblageProjekt -Konfig $konfig -Kuerzel $p.K -Titel $p.T -Beschreibung $p.B -LiveOrt $p.L
        Write-Host ('  {0}  {1}{2}' -f $r.Kennung, $r.Titel, $(if ($r.Neu) { '' } else { '  (war schon da)' }))
    }
}
Update-Projektregister -Konfig $konfig | Out-Null

# ---------------------------------------------------------------- 5. Sortierer starten
$sortierer = Join-Path $installPfad 'Downloads-Sortieren.ps1'
$psExe = 'powershell.exe'
if ($env:SystemRoot) { $psExe = Join-Path $env:SystemRoot 'System32\WindowsPowerShell\v1.0\powershell.exe' }
$sortArgs = '-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File "{0}" -Dauerbetrieb' -f $sortierer
$aufgabeName = 'Claude-Ablage Downloads-Sortieren'
$autostart = $null

if (-not $OhneAufgabe -and $IstWindows) {
    Schritt 'Download-Sortierer einrichten'
    # Liefert auch auf Entra-/AzureAD-Geräten den richtigen Kontonamen (z. B. AzureAD\DustinEskofier)
    $benutzer = [System.Security.Principal.WindowsIdentity]::GetCurrent().Name
    try {
        $aktion = New-ScheduledTaskAction -Execute $psExe -Argument $sortArgs
        $ausloeser = New-ScheduledTaskTrigger -AtLogOn -User $benutzer
        $einstellungen = New-ScheduledTaskSettingsSet -ExecutionTimeLimit ([TimeSpan]::Zero) -RestartCount 3 `
            -RestartInterval (New-TimeSpan -Minutes 1) -MultipleInstances IgnoreNew -AllowStartIfOnBatteries `
            -DontStopIfGoingOnBatteries -StartWhenAvailable
        $prinzipal = New-ScheduledTaskPrincipal -UserId $benutzer -LogonType Interactive -RunLevel Limited
        Register-ScheduledTask -TaskName $aufgabeName -Action $aktion -Trigger $ausloeser -Settings $einstellungen `
            -Principal $prinzipal -Description 'Verschiebt Downloads mit Projektkennung in die Claude-Ablage (Eskofier).' -Force | Out-Null
        Stop-ScheduledTask -TaskName $aufgabeName -ErrorAction SilentlyContinue
        Start-ScheduledTask -TaskName $aufgabeName
        Write-Host "  Aufgabenplanung: '$aufgabeName' (startet bei jeder Anmeldung, läuft unsichtbar)"
    } catch {
        # Rückfall ohne Adminrechte: Verknüpfung im Autostart-Ordner
        Write-Host "  Aufgabenplanung nicht möglich ($($_.Exception.Message)) – nutze Autostart-Ordner." -ForegroundColor Yellow
        $autostart = Join-Path ([Environment]::GetFolderPath('Startup')) 'Claude-Ablage Downloads-Sortieren.lnk'
        $shell = New-Object -ComObject WScript.Shell
        $lnk = $shell.CreateShortcut($autostart)
        $lnk.TargetPath = $psExe; $lnk.Arguments = $sortArgs; $lnk.WindowStyle = 7; $lnk.Save()
        Start-Process -FilePath $psExe -ArgumentList $sortArgs -WindowStyle Hidden
        Write-Host "  Autostart: $autostart"
    }
}

# ---------------------------------------------------------------- 6. Verknüpfungen
if (-not $OhneVerknuepfungen -and $IstWindows) {
    Schritt 'Desktop-Verknüpfungen'
    $desktop = [Environment]::GetFolderPath('Desktop')
    $shell = New-Object -ComObject WScript.Shell
    $lnk = $shell.CreateShortcut((Join-Path $desktop 'Neues Claude-Projekt.lnk'))
    $lnk.TargetPath = $psExe
    $lnk.Arguments = '-NoProfile -ExecutionPolicy Bypass -File "{0}"' -f (Join-Path $installPfad 'Neues-Projekt.ps1')
    $lnk.IconLocation = "$env:SystemRoot\System32\shell32.dll,279"
    $lnk.Description = 'Neues Claude-Projekt anlegen und Kennung vergeben'
    $lnk.Save()
    $lnk = $shell.CreateShortcut((Join-Path $desktop 'Claude-Projekte.lnk'))
    $lnk.TargetPath = $Ablage
    $lnk.Save()
    Write-Host "  'Neues Claude-Projekt' und 'Claude-Projekte' auf dem Desktop angelegt."
}

# ---------------------------------------------------------------- Zusammenfassung
Write-Host ''
Write-Host '  Fertig.' -ForegroundColor Green
Write-Host "  Ablage:        $Ablage"
Write-Host "  Konfiguration: $konfigPfad"
Write-Host "  Protokolle:    $installPfad\Protokoll  und  $Ablage\_System\Protokoll"
Write-Host ''
Write-Host '  Nächste Schritte:' -ForegroundColor Cyan
Write-Host '  1. Testlauf Migration:   & "' -NoNewline; Write-Host (Join-Path $installPfad 'Migration-Kopieren.ps1') -NoNewline; Write-Host '"'
Write-Host '  2. Regeln in CLAUDE_Ablage-Regeln.md in deine Claude-Einstellungen übernehmen (siehe ANLEITUNG.md).'
Write-Host '  3. Test: Datei "FIN-001_2026-09-28_Test_v1.txt" in Downloads legen – nach ~30 s liegt sie im Projekt.'
