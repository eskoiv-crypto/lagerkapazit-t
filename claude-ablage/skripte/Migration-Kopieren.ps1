#Requires -Version 5.1
<#
.SYNOPSIS
    Kopiert bestehende Dateien (Otto-Obligo, Frachtkostenrechner, Warenwert …) aus OneDrive in die Projekte.

.DESCRIPTION
    Version 1.0 · 2026-09-28
    - STANDARD IST EIN TESTLAUF: Es wird nur angezeigt, was kopiert würde. Erst mit -Ausfuehren wird kopiert.
    - Es wird nur KOPIERT, nie verschoben oder gelöscht. Originale, Links in Teams-Chats und
      Live-Dateien der Kollegen bleiben unverändert.
    - Ziel: <Projekt>\09_Altbestand\<Quellordner>\<ursprünglicher Unterpfad>\Datei
    - Zuordnung über migration-regeln.csv (Muster;Kennung;Hinweis). Erste passende Regel gilt.
    - Gleicher Name + gleiche Größe gilt als Duplikat und wird nur einmal kopiert.

.PARAMETER Quelle
    Ein oder mehrere lokale Ordner. Standard: dein OneDrive (Umgebungsvariable OneDriveCommercial).
    Weitere synchronisierte Bibliotheken (z. B. PlattformenTeams) einfach zusätzlich angeben.

.EXAMPLE
    .\Migration-Kopieren.ps1                      # Testlauf, zeigt Plan
    .\Migration-Kopieren.ps1 -Ausfuehren          # kopiert wirklich
#>
[CmdletBinding()]
param(
    [string[]]$Quelle,
    [string]$Regeln = (Join-Path $PSScriptRoot 'migration-regeln.csv'),
    [switch]$Ausfuehren
)

Import-Module (Join-Path $PSScriptRoot 'AblageKern.psm1') -Force
$konfig = Read-AblageKonfig

if (-not $Quelle) {
    if ($env:OneDriveCommercial) { $Quelle = @($env:OneDriveCommercial) }
    else { throw 'Kein OneDrive gefunden. Bitte -Quelle "C:\Pfad" angeben.' }
}
if (-not (Test-Path -LiteralPath $Regeln)) { throw "Regeldatei fehlt: $Regeln" }

$regelListe = @(Import-Csv -LiteralPath $Regeln -Delimiter ';' | Where-Object { $_.Muster -and -not $_.Muster.StartsWith('#') })
$projekte = Get-AblageProjekte -Konfig $konfig
$ablageVoll = [IO.Path]::GetFullPath($konfig.Ablage).TrimEnd('\', '/')

$plan = @()
$gesehen = @{}
foreach ($q in $Quelle) {
    if (-not (Test-Path -LiteralPath $q)) { Write-Warning "Quelle nicht gefunden: $q"; continue }
    $wurzel = [IO.Path]::GetFullPath((Resolve-Path -LiteralPath $q).ProviderPath).TrimEnd('\', '/')
    $quellName = ConvertTo-SichererName -Text (Split-Path -Leaf $wurzel)
    Write-Host "Durchsuche $wurzel …"
    # Feste Reihenfolge: Teams-Chat-Anhänge zuletzt, damit bei Duplikaten die Originalablage gewinnt
    $dateien = Get-ChildItem -LiteralPath $wurzel -Recurse -File -ErrorAction SilentlyContinue |
        Sort-Object @{ Expression = { $_.FullName -like '*Teams-Chatdateien*' } }, FullName
    foreach ($f in $dateien) {
        if ($f.FullName.StartsWith($ablageVoll, [StringComparison]::OrdinalIgnoreCase)) { continue }
        $regel = $null
        foreach ($r in $regelListe) { if ($f.Name -like $r.Muster) { $regel = $r; break } }
        if (-not $regel) { continue }

        $projekt = Find-AblageProjekt -Konfig $konfig -Kennung $regel.Kennung -Projekte $projekte
        $relativ = $f.DirectoryName.Substring($wurzel.Length).TrimStart('\', '/')
        $eintrag = [pscustomobject]@{
            Kennung = $regel.Kennung.ToUpperInvariant(); Datei = $f.Name; Quelle = $f.FullName
            Ziel = ''; KB = [math]::Round($f.Length / 1KB, 0); Aktion = ''; Hinweis = $regel.Hinweis
        }
        $schluessel = '{0}|{1}|{2}' -f $eintrag.Kennung, $f.Name.ToLowerInvariant(), $f.Length
        if (-not $projekt) {
            $eintrag.Aktion = 'Übersprungen: Projekt fehlt'
        } elseif ($gesehen.ContainsKey($schluessel)) {
            $eintrag.Aktion = 'Übersprungen: Duplikat'
            $eintrag.Ziel = $gesehen[$schluessel]
        } else {
            $zielOrdner = Join-Path (Join-Path (Join-Path $projekt.Pfad '09_Altbestand') $quellName) $relativ
            $zielPfad = Join-Path $zielOrdner $f.Name
            if ((Test-Path -LiteralPath $zielPfad) -and ((Get-Item -LiteralPath $zielPfad).Length -eq $f.Length)) {
                $eintrag.Aktion = 'Übersprungen: bereits kopiert'
            } else {
                if (Test-Path -LiteralPath $zielPfad) { $zielPfad = Get-FreierPfad -Ordner $zielOrdner -Name $f.Name }
                $eintrag.Aktion = 'Kopieren'
            }
            $eintrag.Ziel = $zielPfad
            $gesehen[$schluessel] = $zielPfad
        }
        $plan += $eintrag
    }
}

if ($plan.Count -eq 0) { Write-Host 'Keine passenden Dateien gefunden.'; return }

$kopieren = @($plan | Where-Object { $_.Aktion -eq 'Kopieren' })
Write-Host ''
Write-Host 'Zusammenfassung je Projekt:' -ForegroundColor Cyan
$plan | Group-Object Kennung, Aktion | Sort-Object Name | ForEach-Object {
    '  {0,-40} {1,5} Dateien  {2,8:N1} MB' -f $_.Name, $_.Count, (($_.Group | Measure-Object KB -Sum).Sum / 1024)
} | Out-Host

$zeit = Get-Date -Format 'yyyy-MM-dd_HHmm'
if (-not $Ausfuehren) {
    $bericht = Join-Path (Get-AblageInstallPfad) ("Migration_TESTLAUF_$zeit.csv")
    $plan | Export-Csv -LiteralPath $bericht -Delimiter ';' -NoTypeInformation -Encoding UTF8
    Write-Host ''
    Write-Host "TESTLAUF – nichts kopiert. Vollständige Liste: $bericht" -ForegroundColor Yellow
    Write-Host 'Bitte prüfen (v. a. Einträge mit [PRÜFEN]). Danach: .\Migration-Kopieren.ps1 -Ausfuehren'
    return
}

$i = 0
foreach ($e in $kopieren) {
    $i++
    Write-Progress -Activity 'Kopiere in Claude-Ablage' -Status $e.Datei -PercentComplete (100 * $i / $kopieren.Count)
    try {
        $ordner = Split-Path -Parent $e.Ziel
        if (-not (Test-Path -LiteralPath $ordner)) { New-Item -ItemType Directory -Path $ordner -Force | Out-Null }
        Copy-Item -LiteralPath $e.Quelle -Destination $e.Ziel
        $e.Aktion = 'Kopiert'
    } catch {
        $e.Aktion = 'FEHLER: ' + $_.Exception.Message
        Write-AblageLog -Stufe FEHLER -Meldung ("Migration {0}: {1}" -f $e.Quelle, $_.Exception.Message)
    }
}
Write-Progress -Activity 'Kopiere in Claude-Ablage' -Completed

$protokoll = Join-Path (Join-Path (Join-Path $konfig.Ablage '_System') 'Protokoll') ("Migration_$zeit.csv")
$plan | Export-Csv -LiteralPath $protokoll -Delimiter ';' -NoTypeInformation -Encoding UTF8
$fehler = @($plan | Where-Object { $_.Aktion -like 'FEHLER*' })
Write-Host ''
Write-Host ('Kopiert: {0} · Fehler: {1} · Protokoll: {2}' -f @($plan | Where-Object { $_.Aktion -eq 'Kopiert' }).Count, $fehler.Count, $protokoll) -ForegroundColor Green
if ($fehler.Count -gt 0) { Write-Host 'Fehler stehen im Protokoll (häufig: Pfad zu lang oder Datei gesperrt).' -ForegroundColor Yellow }
