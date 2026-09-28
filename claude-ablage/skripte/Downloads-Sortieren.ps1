#Requires -Version 5.1
<#
.SYNOPSIS
    Verschiebt Downloads mit Projektkennung (z. B. "FIN-001_...") in das passende Projekt der Claude-Ablage.

.DESCRIPTION
    Version 1.0 · 2026-09-28
    - Nur Dateien, deren Name mit einer Kennung "BBB-NNN_" beginnt, werden angefasst.
    - Ziel-Unterordner nach Zusatz im Namen: _FINAL -> 03_Ergebnis, _INPUT -> 01_Input,
      _MAIL -> 04_Kommunikation, sonst 02_Arbeitsstand.
    - Unbekannte Kennung -> 00_Eingang.
    - Nie überschreiben: bei Namensgleichheit "Name (2).ext". Identische Duplikate -> Papierkorb
      (in config.json über "DuplikatAktion": "Behalten" abschaltbar).

.PARAMETER Dauerbetrieb
    Läuft endlos und prüft alle IntervallSekunden (Standard 20 s). So startet ihn die Aufgabenplanung.

.PARAMETER Testlauf
    Zeigt nur an, was passieren würde. Verschiebt nichts.

.EXAMPLE
    .\Downloads-Sortieren.ps1 -Testlauf
#>
[CmdletBinding()]
param(
    [switch]$Dauerbetrieb,
    [switch]$Testlauf
)

Import-Module (Join-Path $PSScriptRoot 'AblageKern.psm1') -Force

function Invoke-Durchlauf {
    param($Konfig)
    $ergebnis = @(Invoke-DownloadSortierung -Konfig $Konfig -Testlauf:$Testlauf)
    if ($ergebnis.Count -gt 0) {
        if (-not $Dauerbetrieb) { $ergebnis | Format-Table Datei, Aktion, Ziel, Hinweis -AutoSize -Wrap | Out-Host }
        if ($Dauerbetrieb -and $Konfig.Benachrichtigung) {
            $text = ($ergebnis | ForEach-Object { '{0} → {1}' -f $_.Datei, (Split-Path -Leaf (Split-Path -Parent $_.Ziel)) }) -join "`n"
            Show-AblageHinweis -Titel ('Claude-Ablage: {0} Datei(en) abgelegt' -f $ergebnis.Count) -Text $text
        }
    } elseif (-not $Dauerbetrieb) {
        Write-Host 'Keine Dateien mit Projektkennung im Download-Ordner gefunden.'
    }
}

if (-not $Dauerbetrieb) {
    Invoke-Durchlauf -Konfig (Read-AblageKonfig)
    return
}

# --- Dauerbetrieb: nur eine Instanz gleichzeitig ---
$mutex = New-Object System.Threading.Mutex($false, 'Local\ClaudeAblage-Downloads-Sortieren')
if (-not $mutex.WaitOne(0)) {
    Write-AblageLog -Meldung 'Sortierer läuft bereits – zweite Instanz beendet.'
    return
}
try {
    Write-AblageLog -Meldung 'Sortierer gestartet (Dauerbetrieb).'
    $konfigPfad = Get-AblageKonfigPfad
    $konfigStand = [datetime]::MinValue
    $konfig = $null
    $runde = 0
    while ($true) {
        try {
            # Konfiguration neu laden, wenn sie geändert wurde – Anpassungen wirken ohne Neustart
            $stand = (Get-Item -LiteralPath $konfigPfad).LastWriteTime
            if ($stand -ne $konfigStand) { $konfig = Read-AblageKonfig; $konfigStand = $stand }

            Invoke-Durchlauf -Konfig $konfig
            # Register etwa alle 5 Minuten abgleichen (erfasst auch von Hand angelegte Projektordner)
            if (($runde % [math]::Max(1, [int](300 / $konfig.IntervallSekunden))) -eq 0 -and (Test-Path -LiteralPath $konfig.Ablage)) {
                Update-Projektregister -Konfig $konfig | Out-Null
            }
        } catch {
            Write-AblageLog -Stufe FEHLER -Meldung $_.Exception.Message
        }
        $runde++
        $pause = 20
        if ($konfig -and $konfig.IntervallSekunden -ge 5) { $pause = [int]$konfig.IntervallSekunden }
        Start-Sleep -Seconds $pause
    }
} finally {
    $mutex.ReleaseMutex()
    $mutex.Dispose()
}
