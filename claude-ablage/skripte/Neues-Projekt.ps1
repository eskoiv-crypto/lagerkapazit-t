#Requires -Version 5.1
<#
.SYNOPSIS
    Legt ein neues Claude-Projekt in der Ablage an und vergibt die nächste Kennung (z. B. FIN-002).

.DESCRIPTION
    Version 1.0 · 2026-09-28
    Ohne Parameter startet eine Abfrage (Bereich, Titel, Ziel). Die Desktop-Verknüpfung
    "Neues Claude-Projekt" ruft das Skript so auf.
    Danach liegt in der Zwischenablage ein Satz, den du in Claude einfügst, damit alle
    Dateien richtig benannt werden.

.EXAMPLE
    .\Neues-Projekt.ps1 -Bereich LOG -Titel "GBL Tarifvergleich 2027" -Beschreibung "Tarife GBL vs. AMM ab 01.01.2027"
#>
[CmdletBinding()]
param(
    [string]$Bereich,
    [string]$Titel,
    [string]$Beschreibung = '',
    [string]$LiveOrt = '',
    [switch]$NichtOeffnen
)

Import-Module (Join-Path $PSScriptRoot 'AblageKern.psm1') -Force
$interaktiv = -not ($Bereich -and $Titel)

try {
    $konfig = Read-AblageKonfig
    if (-not (Test-Path -LiteralPath $konfig.Ablage)) { throw "Ablage nicht erreichbar: $($konfig.Ablage) – läuft OneDrive?" }

    if ($interaktiv) {
        Write-Host ''
        Write-Host '  Neues Claude-Projekt' -ForegroundColor Cyan
        Write-Host '  --------------------'
        $i = 1
        foreach ($b in $konfig.Bereiche) {
            Write-Host ('  [{0}] {1}  {2,-22} {3}' -f $i, $b.Kuerzel, $b.Ordner, $b.Beschreibung)
            $i++
        }
        while (-not $Bereich) {
            $eingabe = (Read-Host '  Bereich (Nummer oder Kürzel)').Trim()
            if ($eingabe -match '^\d+$' -and [int]$eingabe -ge 1 -and [int]$eingabe -le $konfig.Bereiche.Count) {
                $Bereich = $konfig.Bereiche[[int]$eingabe - 1].Kuerzel
            } elseif (Get-Bereich -Konfig $konfig -Kuerzel $eingabe) {
                $Bereich = $eingabe.ToUpperInvariant()
            } else { Write-Host '  Ungültig – bitte erneut.' -ForegroundColor Yellow }
        }
        while (-not $Titel) { $Titel = (Read-Host '  Projekttitel (kurz, z. B. "GBL Tarifvergleich 2027")').Trim() }
        if (-not $Beschreibung) { $Beschreibung = (Read-Host '  Ziel in einem Satz (optional, Enter = später)').Trim() }
        if (-not $LiveOrt) { $LiveOrt = (Read-Host '  Live-Ort / Link, falls Kollegen es nutzen (optional)').Trim() }
    }

    $projekt = New-AblageProjekt -Konfig $konfig -Kuerzel $Bereich -Titel $Titel -Beschreibung $Beschreibung -LiveOrt $LiveOrt
    Update-Projektregister -Konfig $konfig | Out-Null

    $prompt = ('Projekt {0} "{1}". Benenne jede Datei, die du erstellst, nach dem Muster ' +
               '{0}_JJJJ-MM-TT_Beschreibung_vN.ext (Endversion mit _FINAL, Rohdaten mit _INPUT, Mail-Entwürfe mit _MAIL).') -f $projekt.Kennung, $Titel.Trim()
    try { Set-Clipboard -Value $prompt } catch { }

    Write-Host ''
    if ($projekt.Neu) {
        Write-Host ('  Angelegt: {0}' -f $projekt.Kennung) -ForegroundColor Green
    } else {
        Write-Host ('  Gibt es schon: {0} (nichts neu angelegt)' -f $projekt.Kennung) -ForegroundColor Yellow
    }
    Write-Host ('  Ordner:   {0}' -f $projekt.Pfad)
    Write-Host ''
    Write-Host '  In der Zwischenablage (in Claude einfügen):' -ForegroundColor Cyan
    Write-Host ('  {0}' -f $prompt)
    if (-not $NichtOeffnen -and $IstWindows) { Start-Process explorer.exe -ArgumentList ('"{0}"' -f $projekt.Pfad) }
    $projekt | Select-Object Kennung, Titel, Bereich, Pfad
} catch {
    Write-Host ('  FEHLER: {0}' -f $_.Exception.Message) -ForegroundColor Red
    Write-AblageLog -Stufe FEHLER -Meldung ("Neues-Projekt: {0}" -f $_.Exception.Message)
    if (-not $interaktiv) { throw }
} finally {
    if ($interaktiv) { Write-Host ''; Read-Host '  Enter zum Schließen' | Out-Null }
}
