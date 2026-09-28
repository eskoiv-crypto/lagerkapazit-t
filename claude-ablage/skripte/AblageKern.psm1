#Requires -Version 5.1
<#
    Claude-Ablage · Kernfunktionen
    Version 1.0 · 2026-09-28

    Gemeinsame Funktionen für Einrichten, Neues-Projekt, Downloads-Sortieren,
    Projekt-Abschliessen und Migration-Kopieren.

    Grundsätze:
      - Es wird nie etwas überschrieben. Bei Namensgleichheit entsteht "Name (2).ext".
      - Es wird nichts endgültig gelöscht. Identische Duplikate gehen (je nach
        Konfiguration) in den Windows-Papierkorb oder bleiben liegen.
      - Kompatibel mit Windows PowerShell 5.1 und PowerShell 7.
#>

$script:IstWindows = ($PSVersionTable.PSEdition -eq 'Desktop') -or
                     ((Get-Variable -Name IsWindows -ValueOnly -ErrorAction SilentlyContinue) -eq $true)

$script:Utf8MitBom = New-Object System.Text.UTF8Encoding $true
$script:KennungMuster = '^(?<kennung>[A-Za-z]{3}-\d{3})_'
$script:ProjektOrdnerMuster = '^(?<kennung>[A-Z]{3}-\d{3})_(?<titel>.+)$'
$script:ArchivOrdner = '_Archiv'
$script:VorlagenOrdner = '99_Vorlagen'
$script:EingangOrdner = '00_Eingang'
$script:SystemOrdner = '_System'
$script:RegisterDatei = 'Projektregister.csv'

# ---------------------------------------------------------------------------
# Pfade & Konfiguration
# ---------------------------------------------------------------------------

function Get-AblageInstallPfad {
    if ($env:CLAUDE_ABLAGE_HOME) { return $env:CLAUDE_ABLAGE_HOME }
    return (Join-Path $env:LOCALAPPDATA 'ClaudeAblage')
}

function Get-AblageKonfigPfad {
    return (Join-Path (Get-AblageInstallPfad) 'config.json')
}

function Get-StandardBereiche {
    return @(
        [pscustomobject]@{ Kuerzel = 'FUL'; Ordner = '10_Fulfillment';          Beschreibung = 'Pipeline, Klassifizierung, Auftragsbearbeitung, Kapazität' }
        [pscustomobject]@{ Kuerzel = 'LOG'; Ordner = '20_Logistik-Partner';     Beschreibung = 'AMM, GBL, Tarife, Verträge, Frachtkosten' }
        [pscustomobject]@{ Kuerzel = 'FIN'; Ordner = '30_Finanzen-Kosten';      Beschreibung = 'Obligo, Rechnungsprüfung, Kostenanalysen' }
        [pscustomobject]@{ Kuerzel = 'BES'; Ordner = '40_Bestand-Lager';        Beschreibung = 'Warenwert, Bestand, Standzeiten, Lagerumzug' }
        [pscustomobject]@{ Kuerzel = 'VER'; Ordner = '50_Vertrieb-Kunden';      Beschreibung = 'Kundenanalysen, Vertriebs-Cockpit, Angebote' }
        [pscustomobject]@{ Kuerzel = 'ORG'; Ordner = '60_Organisation-Team';    Beschreibung = 'Stellenbeschreibungen, Anleitungen, Aufgabenlisten' }
        [pscustomobject]@{ Kuerzel = 'SON'; Ordner = '90_Sonstiges';            Beschreibung = 'Alles, was nirgends sonst passt' }
    )
}

function Get-StandardKonfig {
    return [pscustomobject]@{
        Version               = 1
        Ablage                = ''
        Downloadordner        = (Get-DownloadOrdner)
        Bereiche              = @(Get-StandardBereiche)
        StandardUnterordner   = '02_Arbeitsstand'
        Unterordner           = @(
            [pscustomobject]@{ Marker = '_FINAL'; Ordner = '03_Ergebnis' }
            [pscustomobject]@{ Marker = '_INPUT'; Ordner = '01_Input' }
            [pscustomobject]@{ Marker = '_MAIL';  Ordner = '04_Kommunikation' }
        )
        DuplikatAktion        = 'Papierkorb'   # Papierkorb | Behalten
        IntervallSekunden     = 20
        MindestAlterSekunden  = 5
        Benachrichtigung      = $true
    }
}

function Read-AblageKonfig {
    param([string]$Pfad = (Get-AblageKonfigPfad))
    if (-not (Test-Path -LiteralPath $Pfad)) {
        throw "Keine Konfiguration gefunden ($Pfad). Bitte zuerst Einrichten.ps1 ausführen."
    }
    $gelesen = [IO.File]::ReadAllText($Pfad) | ConvertFrom-Json
    # Fehlende Felder mit Standardwerten auffüllen (z. B. nach einem Update)
    $standard = Get-StandardKonfig
    foreach ($eigenschaft in $standard.PSObject.Properties) {
        if (-not $gelesen.PSObject.Properties[$eigenschaft.Name]) {
            $gelesen | Add-Member -NotePropertyName $eigenschaft.Name -NotePropertyValue $eigenschaft.Value
        }
    }
    return $gelesen
}

function Save-AblageKonfig {
    param([Parameter(Mandatory)]$Konfig, [string]$Pfad = (Get-AblageKonfigPfad))
    $ordner = Split-Path -Parent $Pfad
    if (-not (Test-Path -LiteralPath $ordner)) { New-Item -ItemType Directory -Path $ordner -Force | Out-Null }
    # Windows PowerShell 5.1: ohne diese Zeile werden Arrays teils als {"value":[…],"Count":n} gespeichert
    if ($PSVersionTable.PSEdition -eq 'Desktop') { Remove-TypeData -TypeName System.Array -ErrorAction SilentlyContinue }
    $json = ConvertTo-Json -InputObject $Konfig -Depth 6
    [IO.File]::WriteAllText($Pfad, $json, $script:Utf8MitBom)
}

function Get-DownloadOrdner {
    if ($script:IstWindows) {
        try {
            $wert = (Get-ItemProperty -LiteralPath 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders' -ErrorAction Stop).'{374DE290-123F-4565-9164-39C4925E467B}'
            if ($wert) { return [Environment]::ExpandEnvironmentVariables($wert) }
        } catch { }
    }
    $profil = $env:USERPROFILE
    if (-not $profil) { $profil = $env:HOME }
    return (Join-Path $profil 'Downloads')
}

function Get-SyncOrdner {
    <# Liefert alle per OneDrive synchronisierten SharePoint-/OneDrive-Bibliotheken (Url + lokaler Pfad). #>
    $treffer = @()
    if (-not $script:IstWindows) { return $treffer }
    $basis = 'HKCU:\Software\SyncEngines\Providers\OneDrive'
    if (-not (Test-Path -LiteralPath $basis)) { return $treffer }
    foreach ($schluessel in Get-ChildItem -LiteralPath $basis -ErrorAction SilentlyContinue) {
        $p = Get-ItemProperty -LiteralPath $schluessel.PSPath -ErrorAction SilentlyContinue
        if ($p -and $p.PSObject.Properties['MountPoint'] -and $p.MountPoint) {
            $url = ''
            if ($p.PSObject.Properties['UrlNamespace']) { $url = [string]$p.UrlNamespace }
            $treffer += [pscustomobject]@{ Url = $url; Pfad = [string]$p.MountPoint }
        }
    }
    return $treffer
}

# ---------------------------------------------------------------------------
# Protokoll
# ---------------------------------------------------------------------------

function Write-AblageLog {
    param([Parameter(Mandatory)][string]$Meldung, [ValidateSet('INFO', 'WARNUNG', 'FEHLER')][string]$Stufe = 'INFO')
    $ordner = Join-Path (Get-AblageInstallPfad) 'Protokoll'
    if (-not (Test-Path -LiteralPath $ordner)) { New-Item -ItemType Directory -Path $ordner -Force | Out-Null }
    $datei = Join-Path $ordner ((Get-Date -Format 'yyyy-MM') + '_technisch.log')
    $zeile = '{0} [{1}] {2}' -f (Get-Date -Format 'yyyy-MM-dd HH:mm:ss'), $Stufe, $Meldung
    [IO.File]::AppendAllText($datei, $zeile + [Environment]::NewLine, $script:Utf8MitBom)
}

function Write-Ablageprotokoll {
    <# Fachliches Protokoll im SharePoint (_System\Protokoll): was wurde wohin abgelegt. #>
    param([Parameter(Mandatory)]$Konfig, [string]$Aktion, [string]$Datei, [string]$Ziel, [string]$Hinweis = '')
    $ordner = Join-Path (Join-Path $Konfig.Ablage $script:SystemOrdner) 'Protokoll'
    if (-not (Test-Path -LiteralPath $ordner)) { New-Item -ItemType Directory -Path $ordner -Force | Out-Null }
    $protokollDatei = Join-Path $ordner ('Ablageprotokoll_' + (Get-Date -Format 'yyyy-MM') + '.csv')
    if (-not (Test-Path -LiteralPath $protokollDatei)) {
        [IO.File]::WriteAllText($protokollDatei, 'Zeitpunkt;Aktion;Datei;Ziel;Hinweis' + [Environment]::NewLine, $script:Utf8MitBom)
    }
    $felder = @((Get-Date -Format 'yyyy-MM-dd HH:mm:ss'), $Aktion, $Datei, $Ziel, $Hinweis) | ForEach-Object { ConvertTo-CsvFeld $_ }
    [IO.File]::AppendAllText($protokollDatei, ($felder -join ';') + [Environment]::NewLine, $script:Utf8MitBom)
}

function ConvertTo-CsvFeld {
    param([AllowNull()][AllowEmptyString()][string]$Wert)
    if ($null -eq $Wert) { return '' }
    if ($Wert -match '[;"\r\n]') { return '"' + ($Wert -replace '"', '""') + '"' }
    return $Wert
}

# ---------------------------------------------------------------------------
# Namen
# ---------------------------------------------------------------------------

function ConvertTo-SichererName {
    <# Macht aus einem Titel einen gültigen SharePoint-/Windows-Namen: "Warenwert/Bestandsrechner" -> "Warenwert-Bestandsrechner" #>
    param([Parameter(Mandatory)][string]$Text, [int]$MaxLaenge = 60)
    $n = $Text.Trim()
    $n = $n -replace '[\\/:*?"<>|#%~&{}]', '-'
    $n = $n -replace '\s+', '-'
    $n = $n -replace '-{2,}', '-'
    $n = $n.Trim('-', '.', '_', ' ')
    if ($n.Length -gt $MaxLaenge) { $n = $n.Substring(0, $MaxLaenge).TrimEnd('-', '.', '_') }
    if (-not $n) { throw "Aus '$Text' lässt sich kein gültiger Name bilden." }
    return $n
}

function Get-KennungAusDateiname {
    param([Parameter(Mandatory)][string]$Name)
    $m = [regex]::Match($Name, $script:KennungMuster)
    if ($m.Success) { return $m.Groups['kennung'].Value.ToUpperInvariant() }
    return $null
}

function Get-BereinigterDateiname {
    <# Entfernt Chrome-Zähler: "Datei_v1 (1).pdf" -> "Datei_v1.pdf" #>
    param([Parameter(Mandatory)][string]$Name)
    $ext = [IO.Path]::GetExtension($Name)
    $basis = [IO.Path]::GetFileNameWithoutExtension($Name)
    $basis = $basis -replace '\s\(\d+\)$', ''
    return $basis + $ext
}

function Get-FreierPfad {
    <# Liefert einen nicht existierenden Pfad: Name.ext, Name (2).ext, Name (3).ext … #>
    param([Parameter(Mandatory)][string]$Ordner, [Parameter(Mandatory)][string]$Name)
    $ziel = Join-Path $Ordner $Name
    if (-not (Test-Path -LiteralPath $ziel)) { return $ziel }
    $ext = [IO.Path]::GetExtension($Name)
    $basis = [IO.Path]::GetFileNameWithoutExtension($Name)
    $i = 2
    while ($true) {
        $ziel = Join-Path $Ordner ('{0} ({1}){2}' -f $basis, $i, $ext)
        if (-not (Test-Path -LiteralPath $ziel)) { return $ziel }
        $i++
    }
}

# ---------------------------------------------------------------------------
# Projekte
# ---------------------------------------------------------------------------

function Get-Bereich {
    param([Parameter(Mandatory)]$Konfig, [Parameter(Mandatory)][string]$Kuerzel)
    $k = $Kuerzel.ToUpperInvariant()
    foreach ($b in $Konfig.Bereiche) { if ($b.Kuerzel -eq $k) { return $b } }
    return $null
}

function Read-ProjektFeld {
    param([string]$ProjektPfad, [string]$Feld)
    $md = Join-Path $ProjektPfad '_Projekt.md'
    if (-not (Test-Path -LiteralPath $md)) { return '' }
    foreach ($zeile in [IO.File]::ReadAllLines($md)) {
        $m = [regex]::Match($zeile, '^\|\s*' + [regex]::Escape($Feld) + '\s*\|\s*(?<wert>.*?)\s*\|\s*$')
        if ($m.Success) { return $m.Groups['wert'].Value }
    }
    return ''
}

function Set-ProjektFeld {
    param([string]$ProjektPfad, [string]$Feld, [string]$Wert)
    $md = Join-Path $ProjektPfad '_Projekt.md'
    if (-not (Test-Path -LiteralPath $md)) { return }
    $zeilen = [IO.File]::ReadAllLines($md)
    $muster = '^\|\s*' + [regex]::Escape($Feld) + '\s*\|.*\|\s*$'
    for ($i = 0; $i -lt $zeilen.Length; $i++) {
        if ($zeilen[$i] -match $muster) { $zeilen[$i] = '| {0} | {1} |' -f $Feld, $Wert }
    }
    [IO.File]::WriteAllText($md, ($zeilen -join "`r`n") + "`r`n", $script:Utf8MitBom)
}

function Get-AblageProjekte {
    param([Parameter(Mandatory)]$Konfig)
    $liste = @()
    foreach ($b in $Konfig.Bereiche) {
        $bereichPfad = Join-Path $Konfig.Ablage $b.Ordner
        if (-not (Test-Path -LiteralPath $bereichPfad)) { continue }
        $kandidaten = @()
        $kandidaten += @(Get-ChildItem -LiteralPath $bereichPfad -Directory -ErrorAction SilentlyContinue | ForEach-Object { [pscustomobject]@{ Ordner = $_; Archiviert = $false } })
        $archiv = Join-Path $bereichPfad $script:ArchivOrdner
        if (Test-Path -LiteralPath $archiv) {
            $kandidaten += @(Get-ChildItem -LiteralPath $archiv -Directory -ErrorAction SilentlyContinue | ForEach-Object { [pscustomobject]@{ Ordner = $_; Archiviert = $true } })
        }
        foreach ($k in $kandidaten) {
            $m = [regex]::Match($k.Ordner.Name, $script:ProjektOrdnerMuster)
            if (-not $m.Success) { continue }
            $status = Read-ProjektFeld -ProjektPfad $k.Ordner.FullName -Feld 'Status'
            if (-not $status) { $status = $(if ($k.Archiviert) { 'Abgeschlossen' } else { 'Aktiv' }) }
            $angelegt = Read-ProjektFeld -ProjektPfad $k.Ordner.FullName -Feld 'Angelegt'
            if (-not $angelegt) { $angelegt = $k.Ordner.CreationTime.ToString('yyyy-MM-dd') }
            $liste += [pscustomobject]@{
                Kennung    = $m.Groups['kennung'].Value
                Titel      = $m.Groups['titel'].Value
                Bereich    = $b.Kuerzel
                Status     = $status
                Angelegt   = $angelegt
                Archiviert = $k.Archiviert
                Pfad       = $k.Ordner.FullName
            }
        }
    }
    return @($liste | Sort-Object Kennung)
}

function Find-AblageProjekt {
    param([Parameter(Mandatory)]$Konfig, [Parameter(Mandatory)][string]$Kennung, $Projekte = $null)
    if ($null -eq $Projekte) { $Projekte = Get-AblageProjekte -Konfig $Konfig }
    $k = $Kennung.ToUpperInvariant()
    $treffer = @($Projekte | Where-Object { $_.Kennung -eq $k })
    if ($treffer.Count -gt 1) {
        Write-AblageLog -Stufe WARNUNG -Meldung ("Kennung {0} ist mehrfach vergeben: {1}" -f $k, (($treffer | ForEach-Object { $_.Pfad }) -join ' | '))
    }
    if ($treffer.Count -ge 1) { return $treffer[0] }
    return $null
}

function Get-NaechsteKennung {
    param([Parameter(Mandatory)]$Konfig, [Parameter(Mandatory)][string]$Kuerzel)
    $k = $Kuerzel.ToUpperInvariant()
    $max = 0
    foreach ($p in Get-AblageProjekte -Konfig $Konfig) {
        if ($p.Kennung.StartsWith($k + '-')) {
            $nr = [int]$p.Kennung.Substring(4)
            if ($nr -gt $max) { $max = $nr }
        }
    }
    return ('{0}-{1:000}' -f $k, ($max + 1))
}

function Get-ProjektvorlageText {
    return @'
# {{KENNUNG}} · {{TITEL}}

| Feld | Inhalt |
|---|---|
| Kennung | {{KENNUNG}} |
| Titel | {{TITEL}} |
| Bereich | {{BEREICH}} |
| Angelegt | {{DATUM}} |
| Status | Aktiv |
| Live-Ort | {{LIVEORT}} |

> **Live-Ort** = wo die freigegebene Version liegt, die Kollegen nutzen (z. B. PlattformenTeams › KI-Tools).
> Diese Ablage ist die Werkstatt – der Live-Ort bleibt, wo er ist.

## Ziel
{{BESCHREIBUNG}}

## Dateinamen
Alle Dateien: `{{KENNUNG}}_JJJJ-MM-TT_Beschreibung_vN.ext`

| Zusatz im Namen | Ablage |
|---|---|
| (keiner) | 02_Arbeitsstand |
| `_FINAL` | 03_Ergebnis |
| `_INPUT` | 01_Input |
| `_MAIL` | 04_Kommunikation |

## Claude-Sessions, Artefakte, Repos
-

## Entscheidungen
| Datum | Entscheidung | Begründung |
|---|---|---|
|  |  |  |

## Offene Punkte
-
'@
}

function Initialize-Projektvorlage {
    <# Legt 99_Vorlagen\Projektvorlage in der Ablage an (falls nicht vorhanden). Der Nutzer darf sie anpassen. #>
    param([Parameter(Mandatory)]$Konfig)
    $vorlage = Join-Path (Join-Path $Konfig.Ablage $script:VorlagenOrdner) 'Projektvorlage'
    if (-not (Test-Path -LiteralPath $vorlage)) { New-Item -ItemType Directory -Path $vorlage -Force | Out-Null }
    foreach ($u in @('01_Input', '02_Arbeitsstand', '03_Ergebnis', '04_Kommunikation')) {
        $p = Join-Path $vorlage $u
        if (-not (Test-Path -LiteralPath $p)) { New-Item -ItemType Directory -Path $p -Force | Out-Null }
    }
    $md = Join-Path $vorlage '_Projekt.md'
    if (-not (Test-Path -LiteralPath $md)) {
        [IO.File]::WriteAllText($md, (Get-ProjektvorlageText), $script:Utf8MitBom)
    }
    return $vorlage
}

function New-AblageProjekt {
    param(
        [Parameter(Mandatory)]$Konfig,
        [Parameter(Mandatory)][string]$Kuerzel,
        [Parameter(Mandatory)][string]$Titel,
        [string]$Beschreibung = '',
        [string]$LiveOrt = '',
        [string]$Zusatz = ''          # optionaler Markdown-Abschnitt, wird an _Projekt.md angehängt
    )
    $bereich = Get-Bereich -Konfig $Konfig -Kuerzel $Kuerzel
    if (-not $bereich) { throw "Unbekannter Bereich '$Kuerzel'. Erlaubt: " + (($Konfig.Bereiche | ForEach-Object { $_.Kuerzel }) -join ', ') }
    $sicher = ConvertTo-SichererName -Text $Titel

    # Idempotent: gleicher Titel im gleichen Bereich -> bestehendes Projekt zurückgeben
    $vorhanden = @(Get-AblageProjekte -Konfig $Konfig | Where-Object { $_.Bereich -eq $bereich.Kuerzel -and $_.Titel -eq $sicher })
    if ($vorhanden.Count -gt 0) {
        $vorhanden[0] | Add-Member -NotePropertyName Neu -NotePropertyValue $false -Force
        return $vorhanden[0]
    }

    $kennung = Get-NaechsteKennung -Konfig $Konfig -Kuerzel $bereich.Kuerzel
    $bereichPfad = Join-Path $Konfig.Ablage $bereich.Ordner
    if (-not (Test-Path -LiteralPath $bereichPfad)) { New-Item -ItemType Directory -Path $bereichPfad -Force | Out-Null }
    $ziel = Join-Path $bereichPfad ($kennung + '_' + $sicher)

    $vorlage = Initialize-Projektvorlage -Konfig $Konfig
    New-Item -ItemType Directory -Path $ziel -Force | Out-Null
    foreach ($eintrag in Get-ChildItem -LiteralPath $vorlage -Force) {
        Copy-Item -LiteralPath $eintrag.FullName -Destination $ziel -Recurse -Force
    }

    $md = Join-Path $ziel '_Projekt.md'
    if (-not (Test-Path -LiteralPath $md)) { [IO.File]::WriteAllText($md, (Get-ProjektvorlageText), $script:Utf8MitBom) }
    $text = [IO.File]::ReadAllText($md)
    if (-not $Beschreibung) { $Beschreibung = '(noch offen – beim ersten Claude-Termin ergänzen)' }
    if (-not $LiveOrt) { $LiveOrt = '–' }
    $text = $text.Replace('{{KENNUNG}}', $kennung)
    $text = $text.Replace('{{TITEL}}', $Titel.Trim())
    $text = $text.Replace('{{BEREICH}}', ('{0} · {1}' -f $bereich.Kuerzel, $bereich.Ordner))
    $text = $text.Replace('{{DATUM}}', (Get-Date -Format 'yyyy-MM-dd'))
    $text = $text.Replace('{{BESCHREIBUNG}}', $Beschreibung)
    $text = $text.Replace('{{LIVEORT}}', $LiveOrt)
    if ($Zusatz) { $text = $text.TrimEnd() + "`r`n`r`n" + ($Zusatz.Trim() -replace '\r?\n', "`r`n") + "`r`n" }
    [IO.File]::WriteAllText($md, $text, $script:Utf8MitBom)

    Write-AblageLog -Meldung "Projekt angelegt: $kennung ($ziel)"
    return [pscustomobject]@{
        Kennung = $kennung; Titel = $sicher; Bereich = $bereich.Kuerzel; Status = 'Aktiv'
        Angelegt = (Get-Date -Format 'yyyy-MM-dd'); Archiviert = $false; Pfad = $ziel; Neu = $true
    }
}

function Update-Projektregister {
    <# Schreibt Projektregister.csv (Excel-tauglich: UTF-8 mit BOM, Semikolon). Nur bei Änderung – vermeidet Sync-Last. #>
    param([Parameter(Mandatory)]$Konfig)
    $zeilen = @('Kennung;Bereich;Titel;Status;Angelegt;Ordner')
    foreach ($p in Get-AblageProjekte -Konfig $Konfig) {
        $relativ = $p.Pfad.Substring($Konfig.Ablage.TrimEnd('\', '/').Length).TrimStart('\', '/')
        $zeilen += (@($p.Kennung, $p.Bereich, $p.Titel, $p.Status, $p.Angelegt, $relativ) | ForEach-Object { ConvertTo-CsvFeld $_ }) -join ';'
    }
    $neu = ($zeilen -join "`r`n") + "`r`n"
    $pfad = Join-Path $Konfig.Ablage $script:RegisterDatei
    if (Test-Path -LiteralPath $pfad) {
        $alt = [IO.File]::ReadAllText($pfad)
        if ($alt -eq $neu) { return $false }
    }
    try {
        [IO.File]::WriteAllText($pfad, $neu, $script:Utf8MitBom)
        return $true
    } catch {
        # Typisch: Datei ist gerade in Excel geöffnet. Nächster Durchlauf versucht es erneut.
        Write-AblageLog -Stufe WARNUNG -Meldung "Projektregister konnte nicht geschrieben werden: $($_.Exception.Message)"
        return $false
    }
}

function Initialize-AblageStruktur {
    param([Parameter(Mandatory)]$Konfig)
    foreach ($o in @($script:EingangOrdner, $script:VorlagenOrdner, (Join-Path $script:SystemOrdner 'Protokoll'))) {
        $p = Join-Path $Konfig.Ablage $o
        if (-not (Test-Path -LiteralPath $p)) { New-Item -ItemType Directory -Path $p -Force | Out-Null }
    }
    foreach ($b in $Konfig.Bereiche) {
        $p = Join-Path $Konfig.Ablage $b.Ordner
        if (-not (Test-Path -LiteralPath $p)) { New-Item -ItemType Directory -Path $p -Force | Out-Null }
    }
    Initialize-Projektvorlage -Konfig $Konfig | Out-Null

    $liesmich = Join-Path $Konfig.Ablage 'LIESMICH.md'
    if (-not (Test-Path -LiteralPath $liesmich)) {
        $bereiche = ($Konfig.Bereiche | ForEach-Object { '| {0} | {1} | {2} |' -f $_.Kuerzel, $_.Ordner, $_.Beschreibung }) -join "`r`n"
        $text = @"
# Claude-Projekte · Ablage Dustin Eskofier

Stand: $(Get-Date -Format 'yyyy-MM-dd') · Version 1.0

## Aufbau
``Bereich › Kennung_Projekttitel › 01_Input | 02_Arbeitsstand | 03_Ergebnis | 04_Kommunikation``

| Kürzel | Ordner | Inhalt |
|---|---|---|
$bereiche

- **00_Eingang** – abgelegte Downloads mit unbekannter Kennung (bitte von Hand zuordnen)
- **_Archiv** (je Bereich) – abgeschlossene Projekte
- **99_Vorlagen** – Projektvorlage (darf angepasst werden)
- **_System\Protokoll** – was wann wohin abgelegt wurde
- **Projektregister.csv** – alle Projekte (wird automatisch gepflegt, nicht von Hand bearbeiten)

## Dateinamen
``KENNUNG_JJJJ-MM-TT_Beschreibung_vN.ext`` – z. B. ``FIN-001_2026-09-28_Obligo-Status_v1.pdf``

Dateien mit Kennung am Anfang werden aus dem Download-Ordner automatisch in das passende Projekt verschoben.
"@
        [IO.File]::WriteAllText($liesmich, $text, $script:Utf8MitBom)
    }
}

# ---------------------------------------------------------------------------
# Download-Sortierung
# ---------------------------------------------------------------------------

function Get-Zielunterordner {
    param([Parameter(Mandatory)]$Konfig, [Parameter(Mandatory)][string]$Dateiname)
    $basis = [IO.Path]::GetFileNameWithoutExtension($Dateiname)
    foreach ($regel in $Konfig.Unterordner) {
        # Marker muss als eigenes Namenselement vorkommen: "_FINAL" gefolgt von "_", Leerzeichen oder Ende
        $muster = [regex]::Escape($regel.Marker) + '(?=$|[_\s.(-])'
        if ([regex]::IsMatch($basis, $muster, 'IgnoreCase')) { return $regel.Ordner }
    }
    return $Konfig.StandardUnterordner
}

function Test-DateiBereit {
    param([Parameter(Mandatory)][IO.FileInfo]$Datei, [int]$MindestAlterSekunden = 5)
    $unfertig = @('.crdownload', '.tmp', '.partial', '.part', '.download', '.opdownload')
    if ($unfertig -contains $Datei.Extension.ToLowerInvariant()) { return $false }
    if ($Datei.Name.StartsWith('~$')) { return $false }   # Office-Sperrdatei
    if (((Get-Date) - $Datei.LastWriteTime).TotalSeconds -lt $MindestAlterSekunden) { return $false }
    try {
        $s = [IO.File]::Open($Datei.FullName, 'Open', 'ReadWrite', 'None')
        $s.Close()
        return $true
    } catch { return $false }
}

function Test-DateiIdentisch {
    param([Parameter(Mandatory)][string]$A, [Parameter(Mandatory)][string]$B)
    $fa = Get-Item -LiteralPath $A
    $fb = Get-Item -LiteralPath $B
    if ($fa.Length -ne $fb.Length) { return $false }
    return ((Get-FileHash -LiteralPath $A -Algorithm SHA256).Hash -eq (Get-FileHash -LiteralPath $B -Algorithm SHA256).Hash)
}

function Move-InPapierkorb {
    param([Parameter(Mandatory)][string]$Pfad)
    if ($script:IstWindows) {
        Add-Type -AssemblyName Microsoft.VisualBasic
        [Microsoft.VisualBasic.FileIO.FileSystem]::DeleteFile($Pfad,
            [Microsoft.VisualBasic.FileIO.UIOption]::OnlyErrorDialogs,
            [Microsoft.VisualBasic.FileIO.RecycleOption]::SendToRecycleBin)
    } else {
        # Nur für Tests außerhalb von Windows
        $korb = Join-Path (Get-AblageInstallPfad) '_Papierkorb'
        if (-not (Test-Path -LiteralPath $korb)) { New-Item -ItemType Directory -Path $korb -Force | Out-Null }
        Move-Item -LiteralPath $Pfad -Destination (Get-FreierPfad -Ordner $korb -Name (Split-Path -Leaf $Pfad))
    }
}

function Invoke-DownloadSortierung {
    <#
        Ein Durchlauf: prüft den Download-Ordner (nur oberste Ebene) und verschiebt
        Dateien mit Projektkennung am Namensanfang in das passende Projekt.
        Dateien ohne Kennung werden NICHT angefasst.
    #>
    param([Parameter(Mandatory)]$Konfig, [switch]$Testlauf)
    $ergebnis = @()
    if (-not (Test-Path -LiteralPath $Konfig.Downloadordner)) {
        Write-AblageLog -Stufe WARNUNG -Meldung "Download-Ordner nicht gefunden: $($Konfig.Downloadordner)"
        return $ergebnis
    }
    if (-not (Test-Path -LiteralPath $Konfig.Ablage)) {
        Write-AblageLog -Stufe WARNUNG -Meldung "Ablage nicht erreichbar (OneDrive gestartet?): $($Konfig.Ablage)"
        return $ergebnis
    }

    $dateien = @(Get-ChildItem -LiteralPath $Konfig.Downloadordner -File -ErrorAction SilentlyContinue |
                 Where-Object { Get-KennungAusDateiname -Name $_.Name })
    if ($dateien.Count -eq 0) { return $ergebnis }

    $projekte = Get-AblageProjekte -Konfig $Konfig
    foreach ($d in $dateien) {
        try {
            if (-not (Test-DateiBereit -Datei $d -MindestAlterSekunden $Konfig.MindestAlterSekunden)) { continue }
            $kennung = Get-KennungAusDateiname -Name $d.Name
            $name = Get-BereinigterDateiname -Name $d.Name
            $projekt = Find-AblageProjekt -Konfig $Konfig -Kennung $kennung -Projekte $projekte
            $hinweis = ''
            if ($projekt) {
                $zielOrdner = Join-Path $projekt.Pfad (Get-Zielunterordner -Konfig $Konfig -Dateiname $name)
                if ($projekt.Archiviert) { $hinweis = 'Projekt ist archiviert' }
            } else {
                $zielOrdner = Join-Path $Konfig.Ablage $script:EingangOrdner
                $hinweis = "Kennung $kennung unbekannt – bitte zuordnen"
            }

            $aktion = 'Verschoben'
            $zielPfad = Join-Path $zielOrdner $name
            if (Test-Path -LiteralPath $zielPfad) {
                if (Test-DateiIdentisch -A $d.FullName -B $zielPfad) {
                    if ($Konfig.DuplikatAktion -eq 'Papierkorb') {
                        $aktion = 'Duplikat in Papierkorb'
                        if (-not $Testlauf) { Move-InPapierkorb -Pfad $d.FullName }
                    } else {
                        $aktion = 'Duplikat belassen'
                    }
                    $hinweis = (@($hinweis, 'identische Datei liegt bereits im Projekt') | Where-Object { $_ }) -join '; '
                } else {
                    $zielPfad = Get-FreierPfad -Ordner $zielOrdner -Name $name
                    $hinweis = (@($hinweis, 'Name existierte – neue Datei umbenannt') | Where-Object { $_ }) -join '; '
                }
            }
            if ($aktion -eq 'Verschoben' -and -not $Testlauf) {
                if (-not (Test-Path -LiteralPath $zielOrdner)) { New-Item -ItemType Directory -Path $zielOrdner -Force | Out-Null }
                Move-Item -LiteralPath $d.FullName -Destination $zielPfad
            }
            if ($Testlauf) { $aktion = "[TEST] $aktion" }

            $eintrag = [pscustomobject]@{
                Datei = $d.Name; Kennung = $kennung; Aktion = $aktion
                Ziel = $(if ($aktion -like '*Duplikat*') { Split-Path -Parent $zielPfad } else { $zielPfad }); Hinweis = $hinweis
            }
            $ergebnis += $eintrag
            if (-not $Testlauf -and $aktion -ne 'Duplikat belassen') {
                Write-Ablageprotokoll -Konfig $Konfig -Aktion $aktion -Datei $d.Name -Ziel $eintrag.Ziel -Hinweis $hinweis
            }
            Write-AblageLog -Meldung ("{0}: {1} -> {2} {3}" -f $aktion, $d.Name, $eintrag.Ziel, $hinweis)
        } catch {
            Write-AblageLog -Stufe FEHLER -Meldung ("{0}: {1}" -f $d.Name, $_.Exception.Message)
        }
    }
    return $ergebnis
}

function Show-AblageHinweis {
    param([string]$Titel, [string]$Text)
    if (-not $script:IstWindows) { return }
    try {
        Add-Type -AssemblyName System.Windows.Forms
        Add-Type -AssemblyName System.Drawing
        $n = New-Object System.Windows.Forms.NotifyIcon
        $n.Icon = [System.Drawing.SystemIcons]::Information
        $n.BalloonTipTitle = $Titel
        if ($Text.Length -gt 250) { $Text = $Text.Substring(0, 247) + '...' }
        $n.BalloonTipText = $Text
        $n.Visible = $true
        $n.ShowBalloonTip(6000)
        Start-Sleep -Seconds 7
        $n.Dispose()
    } catch {
        Write-AblageLog -Stufe WARNUNG -Meldung "Benachrichtigung fehlgeschlagen: $($_.Exception.Message)"
    }
}

Export-ModuleMember -Function * -Variable IstWindows
