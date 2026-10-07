<#
    Holt die eingebettete Otto-Historie aus einer ALTEN Cockpit-Datei in die neue Fassung (ab v2.3).

    Brauchst du nur, wenn die Historie-Kachel in der neuen Datei leer bleibt
    (statt "automatisch geladen (eingebetteter Stand)").

    Als Quelle taugt jede aeltere Kopie:
      - eine  _backup_*.html  aus einem frueheren deploy.ps1-Lauf
      - die Vorgaengerversion aus dem OneDrive-/SharePoint-Versionsverlauf
        (Rechtsklick auf die Datei -> Versionsverlauf -> gewuenschte Version
         herunterladen, NICHT wiederherstellen)

    Aufruf:
        .\historie-uebernehmen.ps1 -Alt "C:\Pfad\zur\alten\OttoObligoCockpit.html"
        .\historie-uebernehmen.ps1 -Alt "...alt.html" -WhatIf
#>
[CmdletBinding(SupportsShouldProcess = $true)]
param(
    [Parameter(Mandatory = $true)][string]$Alt,
    [string]$Neu = (Join-Path $PSScriptRoot "OttoObligoCockpit.html")
)

$ErrorActionPreference = "Stop"
function Ok($t) { Write-Host "   OK  $t" -ForegroundColor Green }

if (-not (Test-Path $Alt)) { throw "Alte Datei nicht gefunden: $Alt" }
if (-not (Test-Path $Neu)) { throw "Neue Datei nicht gefunden: $Neu" }

$utf8 = New-Object System.Text.UTF8Encoding($false)
$inhaltAlt = [System.IO.File]::ReadAllText($Alt, $utf8)
$inhaltNeu = [System.IO.File]::ReadAllText($Neu, $utf8)

# Nur LESEN per Regex; das Ersetzen laeuft ueber String.Replace mit festen Zeichenketten.
# So gibt es keine Mehrdeutigkeit bei den [regex]::Replace-Ueberladungen und keine
# Scriptblock-zu-Delegate-Konvertierung, die je nach PowerShell-Version anders auffaellt.
$m = [regex]::Match($inhaltAlt, 'const HIST_CSV=("(?:[^"\\]|\\.)*");')
if (-not $m.Success)                   { throw "In '$Alt' steht kein HIST_CSV - falsche Datei?" }
if ($m.Groups[1].Value.Length -le 4)   { throw "In '$Alt' ist die Historie leer - diese Datei hilft nicht weiter." }
Ok "Historie in der alten Datei gefunden ($([math]::Round($m.Groups[1].Value.Length/1KB)) KB)"

$suchen = 'const HIST_CSV="";'
if (-not $inhaltNeu.Contains($suchen)) { throw "Die neue Datei hat schon eine Historie oder einen unerwarteten Aufbau - nichts geaendert." }

$ersetzen  = 'const HIST_CSV=' + $m.Groups[1].Value + ';'
$inhaltNeu = $inhaltNeu.Replace($suchen, $ersetzen)

foreach ($marke in @('Otto-Obligo-Cockpit', 'kontinuitaet', 'obligoVerlauf')) {
    if (-not $inhaltNeu.Contains($marke)) { throw "Pruefmarke '$marke' fehlt - abgebrochen, nichts geschrieben." }
}
Ok "Pruefmarken vorhanden, Ergebnis $([math]::Round($inhaltNeu.Length/1KB)) KB"

if ($PSCmdlet.ShouldProcess($Neu, "Historie aus '$Alt' eintragen")) {
    [System.IO.File]::WriteAllText($Neu, $inhaltNeu, $utf8)
    Ok "geschrieben: $Neu"
    Write-Host "`nDiese Datei jetzt nach Otto_Obligo_View\OttoObligoCockpit.html kopieren." -ForegroundColor Green
} else {
    Write-Host "   Testlauf (-WhatIf) - nichts geschrieben." -ForegroundColor Yellow
}
