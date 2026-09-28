#Requires -Version 5.1
<#
    Selbsttest der Claude-Ablage – läuft komplett in einem Temp-Ordner, fasst nichts Echtes an.
    Aufruf:  powershell -NoProfile -ExecutionPolicy Bypass -File .\tests\Test-Ablage.ps1
    Version 1.0 · 2026-09-28
#>
$ErrorActionPreference = 'Stop'
$skripte = Join-Path (Split-Path -Parent $PSScriptRoot) 'skripte'

$wurzel = Join-Path ([IO.Path]::GetTempPath()) ('ClaudeAblageTest_' + [guid]::NewGuid().ToString('N').Substring(0, 8))
$env:CLAUDE_ABLAGE_HOME = Join-Path $wurzel 'install'
$ablage = Join-Path $wurzel 'Eskofier - Dokumente\Allgemein\Claude-Projekte'
$downloads = Join-Path $wurzel 'Downloads'
$onedrive = Join-Path $wurzel 'OneDrive - elvinci.de GmbH'
New-Item -ItemType Directory -Path $downloads, $onedrive -Force | Out-Null

$script:fehler = 0
$script:ok = 0
function Pruefe([string]$Name, [bool]$Bedingung) {
    if ($Bedingung) { $script:ok++; Write-Host "  OK    $Name" -ForegroundColor Green }
    else { $script:fehler++; Write-Host "  FEHLT $Name" -ForegroundColor Red }
}
function Neu([string]$Name, [string]$Inhalt = 'x', [int]$AlterSek = 60) {
    $p = Join-Path $downloads $Name
    [IO.File]::WriteAllText($p, $Inhalt)
    (Get-Item -LiteralPath $p).LastWriteTime = (Get-Date).AddSeconds(-$AlterSek)
    return $p
}

try {
    Write-Host "Testordner: $wurzel"

    # ------------------------------------------------------------ Einrichten (ohne Windows-Teile)
    Write-Host "`n[1] Einrichten" -ForegroundColor Cyan
    & (Join-Path $skripte 'Einrichten.ps1') -Ablage $ablage -Ja -OhneAufgabe -OhneVerknuepfungen | Out-Null
    Import-Module (Join-Path $env:CLAUDE_ABLAGE_HOME 'AblageKern.psm1') -Force
    $k = Read-AblageKonfig
    $k.Downloadordner = $downloads
    $k.MindestAlterSekunden = 0
    Save-AblageKonfig -Konfig $k

    Pruefe 'config.json installiert' (Test-Path (Join-Path $env:CLAUDE_ABLAGE_HOME 'config.json'))
    Pruefe 'Skripte installiert' (Test-Path (Join-Path $env:CLAUDE_ABLAGE_HOME 'Downloads-Sortieren.ps1'))
    foreach ($o in '00_Eingang', '10_Fulfillment', '20_Logistik-Partner', '30_Finanzen-Kosten', '40_Bestand-Lager', '99_Vorlagen\Projektvorlage\02_Arbeitsstand', '_System\Protokoll', 'LIESMICH.md') {
        Pruefe "Struktur: $o" (Test-Path (Join-Path $ablage $o))
    }
    $fin = Join-Path $ablage '30_Finanzen-Kosten\FIN-001_Otto-Obligo'
    $log = Join-Path $ablage '20_Logistik-Partner\LOG-001_Frachtkostenrechner'
    $bes = Join-Path $ablage '40_Bestand-Lager\BES-001_Warenwert-Bestandsrechner'
    Pruefe 'Bestandsprojekt FIN-001_Otto-Obligo' (Test-Path (Join-Path $fin '03_Ergebnis'))
    Pruefe 'Bestandsprojekt LOG-001_Frachtkostenrechner' (Test-Path $log)
    Pruefe 'Bestandsprojekt BES-001_Warenwert-Bestandsrechner' (Test-Path $bes)
    $md = [IO.File]::ReadAllText((Join-Path $fin '_Projekt.md'))
    Pruefe '_Projekt.md ausgefüllt (Kennung, Live-Ort)' ($md -match '\| Kennung \| FIN-001 \|' -and $md -match 'Otto_Obligo_View' -and $md -notmatch '\{\{')

    # ------------------------------------------------------------ Idempotenz + Nummernvergabe
    Write-Host "`n[2] Wiederholung & Kennungen" -ForegroundColor Cyan
    & (Join-Path $skripte 'Einrichten.ps1') -Ablage $ablage -Ja -OhneAufgabe -OhneVerknuepfungen | Out-Null
    $k = Read-AblageKonfig
    Pruefe 'Zweites Einrichten: keine Doppel-Projekte' (@(Get-AblageProjekte -Konfig $k).Count -eq 3)
    Pruefe 'Zweites Einrichten: Downloadordner-Anpassung bleibt' ($k.Downloadordner -eq $downloads)
    $p2 = New-AblageProjekt -Konfig $k -Kuerzel fin -Titel 'Rechnungsprüfung AMM / Q3 2026'
    Pruefe 'Nächste Kennung FIN-002' ($p2.Kennung -eq 'FIN-002')
    Pruefe 'Titel bereinigt (Slash, Leerzeichen)' ($p2.Titel -eq 'Rechnungsprüfung-AMM-Q3-2026')
    $p2b = New-AblageProjekt -Konfig $k -Kuerzel FIN -Titel 'Rechnungsprüfung AMM / Q3 2026'
    Pruefe 'Gleicher Titel -> kein neues Projekt' ($p2b.Kennung -eq 'FIN-002' -and -not $p2b.Neu)
    $fehlerGeworfen = $false
    try { New-AblageProjekt -Konfig $k -Kuerzel XXX -Titel 'Test' | Out-Null } catch { $fehlerGeworfen = $true }
    Pruefe 'Unbekannter Bereich -> Fehler' $fehlerGeworfen

    Update-Projektregister -Konfig $k | Out-Null
    $reg = [IO.File]::ReadAllText((Join-Path $ablage 'Projektregister.csv'))
    Pruefe 'Register enthält 4 Projekte' ((($reg -split "`r`n") | Where-Object { $_ -match '^[A-Z]{3}-\d{3};' }).Count -eq 4)
    Pruefe 'Register ohne Änderung wird nicht neu geschrieben' (-not (Update-Projektregister -Konfig $k))

    # ------------------------------------------------------------ Neues-Projekt.ps1 (Parameter-Modus)
    $r = & (Join-Path $env:CLAUDE_ABLAGE_HOME 'Neues-Projekt.ps1') -Bereich LOG -Titel 'GBL Tarifvergleich 2027' -NichtOeffnen 6>$null
    Pruefe 'Neues-Projekt.ps1 -> LOG-002' ((@($r) | Where-Object { $_ -and $_.PSObject.Properties['Kennung'] } | Select-Object -Last 1).Kennung -eq 'LOG-002')

    # ------------------------------------------------------------ Sortierung
    Write-Host "`n[3] Download-Sortierung" -ForegroundColor Cyan
    Neu 'FIN-001_2026-09-28_Test_v1.txt' 'A' | Out-Null
    Neu 'fin-001_2026-09-28_Bericht_v2_FINAL.pdf' | Out-Null
    Neu 'LOG-001_2026-09-28_Tarife_INPUT.xlsx' | Out-Null
    Neu 'BES-001_2026-09-28_Anschreiben-AMM_MAIL_v1.docx' | Out-Null
    Neu 'FIN-001_2026-09-28_FINALISIERUNG_v1.txt' | Out-Null
    Neu 'FIN-001_2026-09-28_[Klammer]_v1.txt' | Out-Null
    Neu 'XYZ-009_2026-09-28_Unbekannt.txt' | Out-Null
    Neu 'Rechnung_123.pdf' | Out-Null
    Neu 'FIN-001_2026-09-28_Halb.pdf.crdownload' | Out-Null
    Neu 'FIN-001_2026-09-28_Frisch_v1.txt' 'x' 0 | Out-Null

    $test = @(Invoke-DownloadSortierung -Konfig (Read-AblageKonfig) -Testlauf)
    Pruefe 'Testlauf meldet Aktionen' ($test.Count -ge 7)
    Pruefe 'Testlauf verschiebt nichts' (Test-Path (Join-Path $downloads 'FIN-001_2026-09-28_Test_v1.txt'))

    $k = Read-AblageKonfig
    $k.MindestAlterSekunden = 5
    Save-AblageKonfig -Konfig $k
    $erg = @(Invoke-DownloadSortierung -Konfig $k)
    Pruefe 'Standard -> 02_Arbeitsstand' (Test-Path (Join-Path $fin '02_Arbeitsstand\FIN-001_2026-09-28_Test_v1.txt'))
    Pruefe 'Kleinbuchstaben-Kennung + _FINAL -> 03_Ergebnis' (Test-Path (Join-Path $fin '03_Ergebnis\fin-001_2026-09-28_Bericht_v2_FINAL.pdf'))
    Pruefe '_INPUT -> 01_Input' (Test-Path (Join-Path $log '01_Input\LOG-001_2026-09-28_Tarife_INPUT.xlsx'))
    Pruefe '_MAIL -> 04_Kommunikation' (Test-Path (Join-Path $bes '04_Kommunikation\BES-001_2026-09-28_Anschreiben-AMM_MAIL_v1.docx'))
    Pruefe '_FINALISIERUNG ist kein _FINAL' (Test-Path (Join-Path $fin '02_Arbeitsstand\FIN-001_2026-09-28_FINALISIERUNG_v1.txt'))
    Pruefe 'Eckige Klammern im Namen' (Test-Path -LiteralPath (Join-Path $fin '02_Arbeitsstand\FIN-001_2026-09-28_[Klammer]_v1.txt'))
    Pruefe 'Unbekannte Kennung -> 00_Eingang' (Test-Path (Join-Path $ablage '00_Eingang\XYZ-009_2026-09-28_Unbekannt.txt'))
    Pruefe 'Ohne Kennung bleibt liegen' (Test-Path (Join-Path $downloads 'Rechnung_123.pdf'))
    Pruefe '.crdownload bleibt liegen' (Test-Path (Join-Path $downloads 'FIN-001_2026-09-28_Halb.pdf.crdownload'))
    Pruefe 'Noch nicht fertige (frische) Datei bleibt liegen' (Test-Path (Join-Path $downloads 'FIN-001_2026-09-28_Frisch_v1.txt'))
    $prot = Get-ChildItem (Join-Path $ablage '_System\Protokoll') -Filter 'Ablageprotokoll_*.csv'
    Pruefe 'Ablageprotokoll geschrieben' ($prot -and ([IO.File]::ReadAllLines($prot[0].FullName).Count -ge 8))

    Write-Host "`n[4] Duplikate & Namenskonflikte" -ForegroundColor Cyan
    Neu 'FIN-001_2026-09-28_Test_v1 (1).txt' 'A' | Out-Null     # identisch (Chrome-Zähler)
    Neu 'FIN-001_2026-09-28_Test_v1 (2).txt' 'B' | Out-Null     # gleicher Name, anderer Inhalt
    $erg = @(Invoke-DownloadSortierung -Konfig $k)
    $ordner = Join-Path $fin '02_Arbeitsstand'
    # Unter Windows landet die Datei im echten Papierkorb, sonst im Test-Papierkorb des Installationsordners
    $imKorb = $IstWindows -or (Test-Path (Join-Path $env:CLAUDE_ABLAGE_HOME '_Papierkorb\FIN-001_2026-09-28_Test_v1 (1).txt'))
    Pruefe 'Identisches Duplikat -> Papierkorb' ((-not (Test-Path (Join-Path $downloads 'FIN-001_2026-09-28_Test_v1 (1).txt'))) -and $imKorb)
    Pruefe 'Anderer Inhalt -> "Name (2)", Original unverändert' ((Test-Path (Join-Path $ordner 'FIN-001_2026-09-28_Test_v1 (2).txt')) -and
        ([IO.File]::ReadAllText((Join-Path $ordner 'FIN-001_2026-09-28_Test_v1.txt')) -eq 'A'))
    $k.DuplikatAktion = 'Behalten'
    Neu 'FIN-001_2026-09-28_Test_v1 (3).txt' 'A' | Out-Null
    Invoke-DownloadSortierung -Konfig $k | Out-Null
    Pruefe 'DuplikatAktion=Behalten lässt Datei liegen' (Test-Path (Join-Path $downloads 'FIN-001_2026-09-28_Test_v1 (3).txt'))

    Write-Host "`n[5] Abschließen & Archiv" -ForegroundColor Cyan
    & (Join-Path $env:CLAUDE_ABLAGE_HOME 'Projekt-Abschliessen.ps1') -Kennung FIN-002 -OhneRueckfrage 6>$null
    $arch = Join-Path $ablage '30_Finanzen-Kosten\_Archiv\FIN-002_Rechnungsprüfung-AMM-Q3-2026'
    Pruefe 'Projekt nach _Archiv verschoben' (Test-Path $arch)
    Pruefe 'Status = Abgeschlossen' ((Read-ProjektFeld -ProjektPfad $arch -Feld 'Status') -like 'Abgeschlossen (*')
    Neu 'FIN-002_2026-09-28_Nachtrag_v1.txt' | Out-Null
    Invoke-DownloadSortierung -Konfig $k | Out-Null
    Pruefe 'Downloads für archiviertes Projekt kommen ins Archiv' (Test-Path (Join-Path $arch '02_Arbeitsstand\FIN-002_2026-09-28_Nachtrag_v1.txt'))
    $p3 = New-AblageProjekt -Konfig $k -Kuerzel FIN -Titel 'Neues nach Archiv'
    Pruefe 'Nummernvergabe berücksichtigt Archiv (FIN-003)' ($p3.Kennung -eq 'FIN-003')

    Write-Host "`n[6] Migration" -ForegroundColor Cyan
    $q1 = Join-Path $onedrive 'Dokumente'
    $q2 = Join-Path $onedrive 'Microsoft Teams-Chatdateien'
    $q3 = Join-Path $onedrive 'Dokumente\Zeug bis 16.06.2026'
    New-Item -ItemType Directory -Path $q1, $q2, $q3 -Force | Out-Null
    [IO.File]::WriteAllText((Join-Path $q1 'Otto-Obligo_2026-07-20.pdf'), 'obligo')
    [IO.File]::WriteAllText((Join-Path $q2 'Otto-Obligo_2026-07-20.pdf'), 'obligo')                 # Duplikat (Name+Größe)
    [IO.File]::WriteAllText((Join-Path $q1 '2026-07-01_Otto-Obligo-Forecast_v6.xlsx'), 'fc')
    [IO.File]::WriteAllText((Join-Path $q3 'Frachtkostenrechner_2026_v3_FINAL.html'), 'fk')
    [IO.File]::WriteAllText((Join-Path $q2 'Warenwert_30-06-2026.pdf'), 'ww')
    [IO.File]::WriteAllText((Join-Path $q1 'Urlaubsantrag.pdf'), 'privat')
    $mig = Join-Path $env:CLAUDE_ABLAGE_HOME 'Migration-Kopieren.ps1'
    & $mig -Quelle $onedrive 6>$null | Out-Null
    Pruefe 'Migration Testlauf kopiert nichts' (-not (Test-Path (Join-Path $fin '09_Altbestand')))
    Pruefe 'Migration Testlauf schreibt Bericht' (@(Get-ChildItem $env:CLAUDE_ABLAGE_HOME -Filter 'Migration_TESTLAUF_*.csv').Count -ge 1)
    & $mig -Quelle $onedrive -Ausfuehren 6>$null | Out-Null
    $alt = Join-Path $fin '09_Altbestand\OneDrive-elvinci.de-GmbH'
    Pruefe 'Obligo kopiert (Unterpfad erhalten)' (Test-Path (Join-Path $alt 'Dokumente\Otto-Obligo_2026-07-20.pdf'))
    Pruefe 'Duplikat nur einmal kopiert' (-not (Test-Path (Join-Path $alt 'Microsoft Teams-Chatdateien\Otto-Obligo_2026-07-20.pdf')))
    Pruefe 'Frachtkostenrechner -> LOG-001' (Test-Path (Join-Path $log '09_Altbestand\OneDrive-elvinci.de-GmbH\Dokumente\Zeug bis 16.06.2026\Frachtkostenrechner_2026_v3_FINAL.html'))
    Pruefe 'Warenwert -> BES-001' (Test-Path (Join-Path $bes '09_Altbestand\OneDrive-elvinci.de-GmbH\Microsoft Teams-Chatdateien\Warenwert_30-06-2026.pdf'))
    Pruefe 'Nicht passende Datei nicht kopiert' (@(Get-ChildItem $ablage -Recurse -Filter 'Urlaubsantrag.pdf').Count -eq 0)
    Pruefe 'Originale unverändert vorhanden' ((Test-Path (Join-Path $q1 'Otto-Obligo_2026-07-20.pdf')) -and (Test-Path (Join-Path $q2 'Warenwert_30-06-2026.pdf')))
    & $mig -Quelle $onedrive -Ausfuehren 6>$null | Out-Null
    Pruefe 'Zweite Migration kopiert nichts doppelt' (@(Get-ChildItem $alt -Recurse -File -Filter 'Otto-Obligo_2026-07-20*').Count -eq 1)

    Write-Host "`n[7] Sortierer-Skript (einzelner Durchlauf)" -ForegroundColor Cyan
    $k = Read-AblageKonfig; $k.MindestAlterSekunden = 0; Save-AblageKonfig -Konfig $k
    Neu 'LOG-002_2026-09-28_Vergleich_v1.xlsx' | Out-Null
    & (Join-Path $env:CLAUDE_ABLAGE_HOME 'Downloads-Sortieren.ps1') 6>$null | Out-Null
    Pruefe 'Downloads-Sortieren.ps1 verschiebt' (Test-Path (Join-Path $ablage '20_Logistik-Partner\LOG-002_GBL-Tarifvergleich-2027\02_Arbeitsstand\LOG-002_2026-09-28_Vergleich_v1.xlsx'))
} finally {
    Write-Host ''
    $farbe = $(if ($script:fehler -eq 0) { 'Green' } else { 'Red' })
    Write-Host ("Ergebnis: {0} OK, {1} Fehler" -f $script:ok, $script:fehler) -ForegroundColor $farbe
    Remove-Item -LiteralPath $wurzel -Recurse -Force -ErrorAction SilentlyContinue
    Remove-Item Env:\CLAUDE_ABLAGE_HOME -ErrorAction SilentlyContinue
}
if ($script:fehler -gt 0) { exit 1 }
