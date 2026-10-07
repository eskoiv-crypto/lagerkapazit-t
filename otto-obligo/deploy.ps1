<#
    Otto-Obligo-Cockpit -> Live-Datei im SharePoint-/OneDrive-Ordner austauschen.

    Uebernimmt aus der ALTEN Datei die eingebettete Otto-Historie (HIST_CSV),
    damit sie beim Austausch nicht verloren geht. Die Historie bleibt dadurch
    im Haus - der Build muss sie nicht kennen.

    Seit v2.4 gibt es KEIN Passwort mehr fuer die Einstellungen. Es wird
    deshalb auch nichts mehr uebernommen; ein Passwort in der alten Datei
    wird einfach verworfen.

    Gebaut wird vorher ohne Historie:
        node _build-kit/build.cjs --out OttoObligoCockpit.new.html --no-hist

    Aufruf:
        .\deploy.ps1 -WhatIf     # zeigt nur, was passieren wuerde
        .\deploy.ps1
#>
[CmdletBinding(SupportsShouldProcess = $true)]
param(
    [string]$Pfad  = "C:\Users\DustinEskofier\OneDrive - elvinci.de GmbH\Digital Experience - KI-Tools\Otto_Obligo_View",
    [string]$Datei = "OttoObligoCockpit.html",
    [string]$Neu   = (Join-Path $PSScriptRoot "OttoObligoCockpit.new.html")
)

$ErrorActionPreference = "Stop"
function Schritt($t) { Write-Host "`n== $t" -ForegroundColor Cyan }
function Ok($t)      { Write-Host "   OK  $t" -ForegroundColor Green }
function Warnung($t) { Write-Host "   !!  $t" -ForegroundColor Yellow }

$alt = Join-Path $Pfad $Datei

Schritt "Dateien pruefen"
if (-not (Test-Path $Neu)) { throw "Neue Datei nicht gefunden: $Neu" }
if (-not (Test-Path $alt)) { throw "Live-Datei nicht gefunden: $alt" }
Ok "neu : $Neu  ($([math]::Round((Get-Item $Neu).Length/1KB)) KB)"
Ok "alt : $alt  ($([math]::Round((Get-Item $alt).Length/1KB)) KB, geaendert $((Get-Item $alt).LastWriteTime))"

$utf8      = New-Object System.Text.UTF8Encoding($false)   # UTF-8 ohne BOM, so schreibt auch build.cjs
$inhaltAlt = [System.IO.File]::ReadAllText($alt, $utf8)
$inhaltNeu = [System.IO.File]::ReadAllText($Neu, $utf8)

if (-not $inhaltAlt.Contains('Otto-Obligo-Cockpit')) { throw "Die Live-Datei ist kein Otto-Obligo-Cockpit - abgebrochen." }

Schritt "Historie aus der alten Datei uebernehmen"
# Regex NUR zum Lesen. Das Ersetzen laeuft ueber String.Replace mit festen Zeichenketten:
# [regex]::Replace mit vier Argumenten trifft in PowerShell die Ueberladung (..., MatchEvaluator, RegexOptions) -
# das vierte Argument ist also KEINE Trefferanzahl, und ein Scriptblock als MatchEvaluator kann je nach
# PowerShell-Version in einem Scope laufen, in dem die Variablen von aussen fehlen. Beides vermeiden wir hier.
$mHist = [regex]::Match($inhaltAlt, 'const HIST_CSV=("(?:[^"\\]|\\.)*");')
if ($mHist.Success -and $mHist.Groups[1].Value.Length -gt 4) {
    $histZeileNeu = [regex]::Match($inhaltNeu, 'const HIST_CSV=("(?:[^"\\]|\\.)*");')
    if (-not $histZeileNeu.Success) { throw "In der neuen Datei kein HIST_CSV gefunden - falscher Build? Abgebrochen." }
    $inhaltNeu = $inhaltNeu.Replace($histZeileNeu.Value, 'const HIST_CSV=' + $mHist.Groups[1].Value + ';')
    Ok "Historie uebernommen ($([math]::Round($mHist.Groups[1].Value.Length/1KB)) KB)"
} else {
    Warnung "Keine eingebettete Historie in der alten Datei - die neue startet ohne (Historie-Kachel bleibt leer)."
    Warnung "Nachholen: .\historie-uebernehmen.ps1 -Alt <aeltere Kopie aus dem Versionsverlauf>"
}

Schritt "Ergebnis pruefen"
if ($inhaltNeu.Contains('CFG_PW')) { throw "Die neue Datei enthaelt noch einen Passwort-Riegel - falscher Build (vor v2.4)? Abgebrochen, nichts geschrieben." }
foreach ($marke in @('Otto-Obligo-Cockpit', 'kontinuitaet', 'obligoVerlauf', 'ZAHLZIEL', 'Einstellungen & Details')) {
    if (-not $inhaltNeu.Contains($marke)) { throw "Pruefmarke '$marke' fehlt - abgebrochen, nichts geschrieben." }
}
Ok "alle Pruefmarken vorhanden, Ergebnis $([math]::Round($inhaltNeu.Length/1KB)) KB"

Schritt "Austausch"
$backup = Join-Path $Pfad ("_backup_" + (Get-Date -Format "yyyy-MM-dd_HHmm") + "_" + $Datei)
if ($PSCmdlet.ShouldProcess($alt, "Sicherung nach '$backup' und Ersetzen")) {
    Copy-Item $alt $backup -Force
    Ok "Sicherung: $backup"
    [System.IO.File]::WriteAllText($alt, $inhaltNeu, $utf8)
    Ok "ersetzt  : $alt  ($([math]::Round((Get-Item $alt).Length/1KB)) KB)"
    Write-Host "`nFertig. Datei im Browser oeffnen und pruefen:" -ForegroundColor Green
    Write-Host "  - Badge oben rechts zeigt die neue Version"
    Write-Host "  - Knopf 'Einstellungen & Details' oeffnet OHNE Passwort"
    Write-Host "  - Historie-Kachel (unter 'Einstellungen & Details') meldet 'automatisch geladen'"
    Write-Host "`nZurueckrollen: Sicherung wieder nach '$Datei' kopieren." -ForegroundColor DarkGray
} else {
    Warnung "Testlauf (-WhatIf) - es wurde nichts geschrieben."
    Write-Host "   Sicherung waere: $backup"
    Write-Host "   Ersetzt wuerde : $alt"
}
