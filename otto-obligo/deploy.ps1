<#
    Otto-Obligo-Cockpit -> Live-Datei im SharePoint-/OneDrive-Ordner austauschen.

    Uebernimmt aus der ALTEN Datei zwei Dinge, damit nichts verloren geht:
      * die eingebettete Otto-Historie (HIST_CSV)
      * das Passwort der Einstellungen (CFG_PW)
    Beides bleibt dadurch im Haus - der Build muss es nicht kennen.

    Gebaut wird vorher mit einem Platzhalter als Passwort:
        OTTO_CFG_PW='__UEBERNAHME_AUS_ALTER_DATEI__' node _build-kit/build.cjs --out OttoObligoCockpit.new.html --no-hist

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
$PLATZHALTER = '__UEBERNAHME_AUS_ALTER_DATEI__'
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

Schritt "Historie und Passwort aus der alten Datei uebernehmen"
# Regex NUR zum Lesen. Das Ersetzen laeuft ueber String.Replace mit festen Zeichenketten:
# [regex]::Replace mit vier Argumenten trifft in PowerShell die Ueberladung (..., MatchEvaluator, RegexOptions) -
# das vierte Argument ist also KEINE Trefferanzahl, und ein Scriptblock als MatchEvaluator kann je nach
# PowerShell-Version in einem Scope laufen, in dem die Variablen von aussen fehlen. Beides vermeiden wir hier.
$mHist = [regex]::Match($inhaltAlt, 'const HIST_CSV=("(?:[^"\\]|\\.)*");')
$mPw   = [regex]::Match($inhaltAlt, 'const CFG_PW=("(?:[^"\\]|\\.)*");')

if (-not $mPw.Success) { throw "In der alten Datei steht kein CFG_PW - ist das wirklich das Cockpit? Abgebrochen." }
if ($mPw.Groups[1].Value -match [regex]::Escape($PLATZHALTER)) {
    throw @"
Die Live-Datei traegt bereits den Platzhalter als Passwort.
Das heisst: dort wurde schon einmal eine frisch gebaute Datei direkt hineinkopiert,
statt sie ueber dieses Skript auszutauschen. Damit ist das echte Passwort - und sehr
wahrscheinlich auch die eingebettete Historie - aus der Live-Datei verschwunden.

Bitte zuerst die Vorgaengerversion zurueckholen:
  Rechtsklick auf '$Datei' -> Versionsverlauf -> Version von vor dem Austausch
  wiederherstellen. Danach dieses Skript erneut starten.
"@
}

$pwZeileNeu   = [regex]::Match($inhaltNeu, 'const CFG_PW=("(?:[^"\\]|\\.)*");')
if (-not $pwZeileNeu.Success) { throw "In der neuen Datei steht kein CFG_PW - falscher Build? Abgebrochen." }
$inhaltNeu = $inhaltNeu.Replace($pwZeileNeu.Value, 'const CFG_PW=' + $mPw.Groups[1].Value + ';')
Ok "Passwort der Einstellungen uebernommen (Wert wird nicht angezeigt)"

if ($mHist.Success -and $mHist.Groups[1].Value.Length -gt 4) {
    $histZeileNeu = [regex]::Match($inhaltNeu, 'const HIST_CSV=("(?:[^"\\]|\\.)*");')
    if ($histZeileNeu.Success) {
        $inhaltNeu = $inhaltNeu.Replace($histZeileNeu.Value, 'const HIST_CSV=' + $mHist.Groups[1].Value + ';')
        Ok "Historie uebernommen ($([math]::Round($mHist.Groups[1].Value.Length/1KB)) KB)"
    } else { Warnung "In der neuen Datei kein HIST_CSV gefunden - Historie nicht uebernommen." }
} else {
    Warnung "Keine eingebettete Historie in der alten Datei - die neue startet ohne (Historie-Kachel bleibt leer)."
}

Schritt "Ergebnis pruefen"
if ($inhaltNeu.Contains($PLATZHALTER)) { throw "Passwort-Platzhalter steht noch drin - abgebrochen, nichts geschrieben." }
foreach ($marke in @('Otto-Obligo-Cockpit', 'kontinuitaet', 'obligoVerlauf', 'ZAHLZIEL')) {
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
    Write-Host "  - Historie-Kachel meldet 'automatisch geladen'"
    Write-Host "  - Einstellungen lassen sich mit dem gewohnten Passwort oeffnen"
    Write-Host "`nHinweis: Die Kontinuitaetspruefung braucht EINEN gespeicherten Vortagesstand und meldet sich"
    Write-Host "deshalb erst ab der zweiten taeglichen Auswertung (Agicap UND Bestellungen geladen)."
    Write-Host "`nZurueckrollen: Sicherung wieder nach '$Datei' kopieren." -ForegroundColor DarkGray
} else {
    Warnung "Testlauf (-WhatIf) - es wurde nichts geschrieben."
    Write-Host "   Sicherung waere: $backup"
    Write-Host "   Ersetzt wuerde : $alt"
}
