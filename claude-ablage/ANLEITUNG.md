# Claude-Ablage „Eskofier“ · Anleitung

**Version 1.0 · 2026-09-28** · für Dustin Eskofier, Backoffice & Fulfillment

---

## Was das ist

Eine eigene Teams-/SharePoint-Seite **„Eskofier“** für alle Projekte, die du mit Claude bearbeitest.
Jedes Projekt bekommt eine **Kennung** (z. B. `FIN-001`). Jede Datei, die Claude erstellt, beginnt mit dieser Kennung.
Ein kleiner Hintergrunddienst auf deinem PC verschiebt solche Dateien **direkt nach dem Download** in den richtigen Projektordner.
OneDrive lädt sie dann nach SharePoint hoch.

```
Eskofier › Dokumente › Allgemein › Claude-Projekte
├─ 00_Eingang                      ← Downloads mit unbekannter Kennung
├─ 10_Fulfillment            FUL
├─ 20_Logistik-Partner       LOG
│   └─ LOG-001_Frachtkostenrechner
├─ 30_Finanzen-Kosten        FIN
│   ├─ FIN-001_Otto-Obligo
│   │   ├─ 01_Input               ← Rohdaten, Originale (nie verändern)
│   │   ├─ 02_Arbeitsstand        ← Entwürfe _v1, _v2 …
│   │   ├─ 03_Ergebnis            ← freigegebene Endversionen (_FINAL)
│   │   ├─ 04_Kommunikation       ← Mail-/Brief-Entwürfe (_MAIL)
│   │   ├─ 09_Altbestand          ← kopierte Altdateien (Migration)
│   │   └─ _Projekt.md            ← Ziel, Status, Live-Ort, Links, Entscheidungen
│   └─ _Archiv                    ← abgeschlossene Projekte
├─ 40_Bestand-Lager          BES
│   └─ BES-001_Warenwert-Bestandsrechner
├─ 50_Vertrieb-Kunden        VER
├─ 60_Organisation-Team      ORG
├─ 90_Sonstiges              SON
├─ 99_Vorlagen                    ← Projektvorlage (anpassbar)
├─ _System › Protokoll            ← was wann wohin abgelegt wurde
├─ Projektregister.csv            ← alle Projekte (automatisch gepflegt)
└─ LIESMICH.md
```

> **Bereiche sind ein Vorschlag.** Ich habe sie aus deinen bisherigen Claude-Themen abgeleitet
> (Artefakte, Repos, SharePoint-Dateien). Ändern kannst du sie vor dem ersten Start in `config.json`
> (siehe „Anpassen“).

---

## 1 · Einmalig einrichten (ca. 15 Minuten)

### A) Team „Eskofier“ anlegen *(das kannst nur du – ich habe nur Leserechte in M365)*
1. Teams › **Teams** › **+** › **Team erstellen** › *Von Grund auf*
2. Vertraulichkeit **Privat**, Name **Eskofier** › Erstellen. Niemanden hinzufügen.
3. Falls „Team erstellen“ fehlt: Die IT hat die Team-Erstellung eingeschränkt. Dann bitte die IT, das Team anzulegen.

### B) Bibliothek synchronisieren
1. Im Team › Kanal **Allgemein** › Reiter **Dateien** › **In SharePoint öffnen**
2. In SharePoint oben **Synchronisieren** › Chrome fragt „OneDrive öffnen?“ › **Zulassen**
3. Im Explorer erscheint links unter **elvinci.de GmbH** der Ordner **Eskofier - Dokumente**. Warte, bis der Sync fertig ist.

### C) Paket einrichten
1. `2026-09-28_Claude-Ablage_v1.zip` entpacken, z. B. nach `Dokumente\Claude-Ablage-Setup`.
   *Nicht* im Download-Ordner lassen.
2. **`EINRICHTEN.cmd`** doppelklicken. Falls Windows „Der Computer wurde geschützt“ meldet:
   *Weitere Informationen › Trotzdem ausführen*.
3. Das Skript findet die Eskofier-Bibliothek selbst und fragt einmal nach. Dann:
   - legt die Struktur und die drei Bestandsprojekte an:
     **FIN-001 Otto-Obligo · LOG-001 Frachtkostenrechner · BES-001 Warenwert-Bestandsrechner**
   - richtet den Download-Sortierer ein (startet bei jeder Anmeldung unsichtbar, beim Anmelden blitzt kurz ein Fenster auf)
   - legt zwei Desktop-Symbole an: **Neues Claude-Projekt** und **Claude-Projekte**

### D) Claude-Regeln übernehmen
Die Blöcke aus **`CLAUDE_Ablage-Regeln.md`** in claude.ai › Einstellungen › Profil › Persönliche Präferenzen einfügen.
Ohne diesen Schritt benennt Claude die Dateien nicht mit Kennung, und der Sortierer erkennt sie nicht.

### E) Altbestand übernehmen (Migration) – erst prüfen, dann kopieren
PowerShell öffnen, dann:
```powershell
& "$env:LOCALAPPDATA\ClaudeAblage\Migration-Kopieren.ps1"              # TESTLAUF: zeigt nur an
& "$env:LOCALAPPDATA\ClaudeAblage\Migration-Kopieren.ps1" -Ausfuehren  # kopiert wirklich
```
- **Standard ist der Testlauf.** Die vollständige Liste landet als CSV in `%LOCALAPPDATA%\ClaudeAblage`. Bitte vor `-Ausfuehren` durchsehen.
- Es wird **nur kopiert**. Originale, Links in Teams-Chats und die Live-Dateien der Kollegen bleiben, wo sie sind.
- Durchsucht wird dein OneDrive. Zuordnung über `migration-regeln.csv`:

| Muster | Projekt | Gefunden bei der Suche am 28.09. (Auszug) |
|---|---|---|
| `*Otto-Obligo*`, `*OttoObligo*` | FIN-001 | Otto-Obligo_2026-07-xx.pdf, 2026-07-01_Otto-Obligo-Forecast_v6.xlsx, Otto-Obligo-Cockpit.html / _Ordnerstruktur.zip |
| `*Frachtkostenrechner*`, `Frachtangebot_El-vinci*` | LOG-001 | Frachtkostenrechner_v1 … _2026_v3_FINAL.html, Frachtkostenrechner.zip |
| `*Warenwert*`, `*Bestandsstatus*`, `*Bestandsbewertung*`, `*Bestandsverifikation*` | BES-001 **[PRÜFEN]** | Warenwert-PDFs 30.06./31.08.2026, „Warenwert zum Monatsende“, Bestandsstatus 31.08.2025 v1–v4 |

> ⚠️ **Bei BES-001 bitte prüfen:** Ein Tool namens „Bestandsrechner“ habe ich nicht gefunden, nur Berichte (PDF/Excel).
> Wenn der Rechner anders heißt, ergänze eine Zeile in `%LOCALAPPDATA%\ClaudeAblage\migration-regeln.csv`.

**PlattformenTeams (Live-Tools):** Obligo-Cockpit v2.3 und Frachtkostenrechner v6 liegen in
*PlattformenTeams › Tools und Automatisieren › KI-Tools* und werden dort von Kollegen genutzt.
**Bitte nicht verschieben.** Der Link steht als **Live-Ort** in `_Projekt.md`. Wenn du diese Bibliothek
ebenfalls synchronisiert hast und eine Kopie in der Werkstatt willst, gib ihren Pfad zusätzlich an:
```powershell
& "$env:LOCALAPPDATA\ClaudeAblage\Migration-Kopieren.ps1" -Quelle $env:OneDriveCommercial, "C:\Users\…\elvinci.de GmbH\Plattformen Teams - Dokumente"
```

### F) Funktionstest
Lege eine Textdatei `FIN-001_2026-09-28_Test_v1.txt` in deinen Download-Ordner. Nach etwa 30 Sekunden
liegt sie in `FIN-001_Otto-Obligo\02_Arbeitsstand`, und rechts unten erscheint ein Hinweis.

---

## 2 · Täglich nutzen

| Schritt | Was du tust |
|---|---|
| **Neues Projekt** | Desktop › **Neues Claude-Projekt** › Bereich + Titel. Die Kennung (z. B. `LOG-002`) wird vergeben, der Ordner geöffnet. Ein fertiger Satz für Claude liegt in der Zwischenablage. |
| **Mit Claude arbeiten** | Satz aus der Zwischenablage in den Chat einfügen, oder einfach „Projekt LOG-002“ schreiben. |
| **Herunterladen** | Ganz normal in Chrome. Dateien mit Kennung wandern automatisch ins Projekt. |
| **Links festhalten** | Session-, Artefakt- und Repo-Links in `_Projekt.md` eintragen. Claude liefert sie am Ende als Block. |
| **Abschließen** | `& "$env:LOCALAPPDATA\ClaudeAblage\Projekt-Abschliessen.ps1" -Kennung LOG-002` › Ordner wandert nach `_Archiv` |

### Dateinamen

`KENNUNG_JJJJ-MM-TT_Beschreibung_vN.ext`, z. B. `FIN-001_2026-09-28_Obligo-Status_v1.pdf`

| Zusatz im Namen | landet in |
|---|---|
| (keiner) | 02_Arbeitsstand |
| `_FINAL` | 03_Ergebnis |
| `_INPUT` | 01_Input |
| `_MAIL` | 04_Kommunikation |

---

## 3 · Was passiert in Sonderfällen

| Fall | Verhalten |
|---|---|
| Datei ohne Kennung (Rechnung, Bild, …) | **wird nicht angefasst** |
| Download läuft noch (`.crdownload`) | wartet, bis er fertig ist |
| Kennung unbekannt (Tippfehler) | → `00_Eingang`, Eintrag im Protokoll |
| Gleicher Name, **anderer** Inhalt | nichts wird überschrieben › neue Datei heißt `Name (2).ext` |
| Gleicher Name, **identischer** Inhalt (doppelt geladen) | Download-Kopie → **Windows-Papierkorb**, wiederherstellbar. Abschaltbar, siehe unten. |
| Chrome-Zähler `Datei (1).pdf` | wird entfernt, Datei heißt wieder `Datei.pdf` |
| Projekt archiviert | Dateien gehen trotzdem in das archivierte Projekt |
| PC aus / OneDrive nicht gestartet | Dateien bleiben im Download-Ordner, werden beim nächsten Lauf abgelegt |

---

## 4 · Grenzen – ehrlich

- **Claude kann nicht selbst in SharePoint speichern.** Der M365-Connector hat nur Leserechte. Deshalb der Weg über Download + Sortierer.
- **Artefakte auf claude.ai** (veröffentlichte Seiten) sind keine Dateien. Sie werden als Link in `_Projekt.md` festgehalten.
- **Claude-Code-Ergebnisse** liegen in GitHub-Repos. Auch dafür gehört der Repo-/PR-Link in `_Projekt.md`.
- Bei Downloads, deren Name Claude nicht bestimmt (z. B. Exporte aus JTL/Odoo), fehlt die Kennung. Entweder vor dem Speichern umbenennen, oder die Datei bleibt im Download-Ordner.
- **Getestet** habe ich die Logik mit einem automatischen Selbsttest (53 Prüfungen, alle grün) in PowerShell 7 unter Linux.
  **Nicht testen konnte ich die Windows-Teile:** Aufgabenplanung, Desktop-Symbole, Papierkorb, Hinweis-Fenster und OneDrive-Erkennung.
  Den Selbsttest kannst du auf deinem PC wiederholen: `powershell -ExecutionPolicy Bypass -File .\tests\Test-Ablage.ps1`

---

## 5 · Anpassen

Datei: `%LOCALAPPDATA%\ClaudeAblage\config.json`. Änderungen wirken ohne Neustart.

| Feld | Bedeutung | Standard |
|---|---|---|
| `Bereiche` | Kürzel (3 Buchstaben), Ordnername, Beschreibung | 7 Bereiche (s. o.) |
| `Unterordner` | Zusatz im Namen → Zielordner | `_FINAL`, `_INPUT`, `_MAIL` |
| `DuplikatAktion` | `Papierkorb` oder `Behalten` | `Papierkorb` |
| `IntervallSekunden` | Prüfintervall Download-Ordner | 20 |
| `Benachrichtigung` | Hinweis rechts unten | `true` |
| `Downloadordner` | falls Chrome woanders speichert | Windows-Downloads |

Neue Bereiche: Eintrag ergänzen, dann `Einrichten.ps1` erneut ausführen (legt nur fehlende Ordner an).
Projektvorlage ändern: `99_Vorlagen\Projektvorlage` in SharePoint bearbeiten. Das gilt dann für alle neuen Projekte.

---

## 6 · Fehlerbehebung

| Problem | Prüfen |
|---|---|
| Nichts wird verschoben | Aufgabenplanung › „Claude-Ablage Downloads-Sortieren“ läuft? Protokoll: `%LOCALAPPDATA%\ClaudeAblage\Protokoll\*_technisch.log` |
| „Ablage nicht erreichbar“ | OneDrive gestartet und angemeldet? |
| Register nicht aktuell | `Projektregister.csv` ist in Excel geöffnet › schließen, wird innerhalb von 5 Min. aktualisiert |
| Migration: „Pfad zu lang“ | Betroffene Datei steht im Migrationsprotokoll › von Hand kopieren |

**Entfernen:** `& "$env:LOCALAPPDATA\ClaudeAblage\Deinstallieren.ps1"` entfernt Sortierer, Symbole und Skripte. Die SharePoint-Ablage bleibt.

---

## Paketinhalt

| Datei | Zweck |
|---|---|
| `EINRICHTEN.cmd` | Start per Doppelklick |
| `CLAUDE_Ablage-Regeln.md` | Ergänzung für deine Claude-Einstellungen |
| `skripte\Einrichten.ps1` | einmalige Einrichtung (wiederholbar) |
| `skripte\Downloads-Sortieren.ps1` | Sortierer (Hintergrund; `-Testlauf` zeigt nur an) |
| `skripte\Neues-Projekt.ps1` | neues Projekt + Kennung |
| `skripte\Projekt-Abschliessen.ps1` | Projekt ins Archiv |
| `skripte\Migration-Kopieren.ps1` + `migration-regeln.csv` | Altbestand kopieren |
| `skripte\Deinstallieren.ps1` | alles Lokale entfernen |
| `skripte\AblageKern.psm1` | gemeinsame Funktionen |
| `tests\Test-Ablage.ps1` | Selbsttest (läuft im Temp-Ordner, fasst nichts Echtes an) |
