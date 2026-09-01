# Otto-Obligo — Historie erweitern

Das **Otto-Obligo-Cockpit** (`Otto-Obligo-Cockpit.html`, liegt in SharePoint unter
`Tools und Automatisieren/KI-Tools/Otto_Obligo_View/`) trägt die Otto-Rechnungs­historie
fest eingebettet als JS-Konstante `const HIST_CSV="…"` im Markup. Sie wird beim Öffnen
automatisch geladen und speist das Diagramm **„Otto-Volumen je Monat"**.

`merge_history.py` mischt frische Agicap-Exporte in diesen eingebetteten Stand.

## Wie das Cockpit gebaut wird

Im SharePoint-Ordner `Otto_Obligo_View/_build-kit/` liegt eine Build-Kette:

| Datei | Rolle |
|---|---|
| `app_template.html` | Cockpit ohne eingebettete Libs/Historie |
| `hist_register.csv` | Register-Snapshot — **die Quelle der Historie** |
| `build.js` | bettet Libs **und** `hist_register.csv` ein → `Otto-Obligo-Cockpit.html` |
| `REFRESH-Historie.md` | die monatliche Prozedur |

Kanonisch ist also: **`hist_register.csv` ersetzen, dann `node build.js`.** Das
gebaute HTML wird laut `REFRESH-Historie.md` in vier Kopien verteilt.

## Anwendung

```bash
python3 tools/otto_obligo/merge_history.py \
    --cockpit Otto-Obligo-Cockpit.html \
    --out     Otto-Obligo-Cockpit.html \
    --csv-out hist_register.csv \
    supplier_invoices_*.csv
```

`--csv-out` schreibt den erweiterten Register-Snapshot für die Build-Kette.
Beide Ausgaben sind konsistent: der Snapshot ist byte-identisch mit dem, was
das Skript ins HTML einbettet — ein `node build.js` darüber ändert nichts mehr.
Wer die Build-Kette zur Hand hat, nimmt `--csv-out` und baut; wer nur die
fertige Datei ablegen will, nimmt `--out` direkt.

Das Skript gibt eine Bilanz aus (neu / aktualisiert / behalten, Monatsverteilung,
Zeitraum) und schreibt ausschließlich das `HIST_CSV`-Literal neu — der restliche
HTML-Code bleibt Byte für Byte unverändert.

## Merge-Regeln

| Fall | Verhalten |
|---|---|
| Rechnung in beiden Ständen | **neuer Export gewinnt** — er trägt den frischeren Status (`Zu bezahlen` → `Bezahlt`) |
| Rechnung nur im neuen Export | wird aufgenommen |
| Rechnung nur im alten Stand | bleibt erhalten (Agicap exportiert je nach Filter nicht alle Status) |

Identität einer Rechnung ist die **normalisierte Rechnungsnummer**, exakt wie
`refKey()` im Cockpit: `1001EO…` und `1001E0…` sind dieselbe Rechnung. Das ist
wichtig, weil Agicap eine Rechnung beim Umbuchen mit **neuer Raten-ID** neu
ausstellt — über die Raten-ID gemergt entstünden Dubletten.

Spaltennamen (`Titel der Rechnung/Rate` → `Rechnungs-/Ratenbezeichnung`) und die
Zahlungsart (`Banküberweisung` → `Überweisung`) werden auf das Schema des
eingebetteten Bestands normalisiert.

## Gegenprobe nach dem Merge

Cockpit im Browser öffnen — der Historie-Kachel meldet die geladene Zahl:

> `297 Otto-Rechnungen · automatisch geladen (eingebetteter Stand)`

Diese Zahl ist **kleiner als die Zeilenzahl der CSV**: `parseHist()` verwirft
Rechnungen mit Bruttobetrag 0 (stornierte/umgebuchte Belege).

## ⚠️ Nicht ins Repository

Das Cockpit ist ein **interner Master** (Einkaufsvolumen, Lieferantenkonditionen,
Kreditlinie, IBAN) — dieses Repository ist **öffentlich**. Die gemergte HTML-Datei
und die Agicap-Exporte gehören nach SharePoint, nicht in den Git-Verlauf.
`.gitignore` hält die üblichen Dateinamen fern; beim Umbenennen selbst mitdenken.

## Monatliches Auffrischen (lokal)

`refresh_local.py` fasst die ganze Prozedur zu einem Kommando zusammen:

```bash
python3 tools/otto_obligo/refresh_local.py --dry-run supplier_invoices_*.csv   # erst zeigen
python3 tools/otto_obligo/refresh_local.py          supplier_invoices_*.csv   # dann machen
```

Es findet `_build-kit` selbst unter OneDrive, mischt in `hist_register.csv`
(Backup mit Zeitstempel daneben), ruft `node build.js`, **prüft das Ergebnis**
und verteilt erst danach in die Zielkopien aus `REFRESH-Historie.md`. Ohne Node
greift der Direkt-Patch des Literals — nachweislich dasselbe Ergebnis.

Geprüft wird vor dem Verteilen: Zeilenzahl, keine doppelten Rechnungsnummern,
`</html>` am Ende, genau eine `HIST_CSV`-Deklaration und **ein `;` direkt hinter
dem Literal**. Der letzte Punkt fängt einen Build ab, der das alte Literal nicht
sauber ersetzt: die Historie decodiert dann zwar korrekt, dahinter steht aber
Datenmüll im Skript. Schlägt eine Prüfung fehl, wird **nichts** verteilt.

Damit eine lokale Claude-Code-Sitzung das von selbst kann, liegt der Ablauf als
Skill unter `.claude/skills/otto-historie/`. Auslöser: „Otto-Historie auffrischen".

**Nur lokal.** In einer Cloud-Sitzung existiert der OneDrive-Ordner nicht — dort
mergt `merge_history.py`, und die Dateien werden zurückgegeben.
