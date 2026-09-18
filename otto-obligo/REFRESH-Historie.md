# Otto-Historie auffrischen (1× im Monat) — Stand v2.1 (2026-09-18)

Die Historie ist **fest ins Cockpit eingebettet** und lädt automatisch beim Öffnen — kein Drag&Drop nötig.
Damit sie aktuell bleibt, wird der eingebettete Stand **einmal im Monat** neu gebaut. Dauert ~2 Minuten.

## Schritt 1 — Register aus Agicap ziehen
Agicap → Lieferantenrechnungen → **kompletter Register-Export über den ganzen Zeitraum** (alle Status, alle Begünstigten) als CSV.
Das ist dieselbe Datei wie die „supplier_invoices"-Register-CSV.

## Schritt 2 — Datei an Claude geben zum Neu-Einbetten
Claude Code (Repo `lagerkapazit-t`, Ordner `otto-obligo/`) sagen: **„Otto-Historie im Cockpit auffrischen"** und die neue Register-CSV anhängen.
Claude legt sie als `_build-kit/hist_register.csv` ab (bleibt git-ignoriert), baut neu und liefert die fertige HTML.

## Was dann intern passiert (zur Nachvollziehbarkeit)
1. Neue CSV → `_build-kit/hist_register.csv` (überschreibt den alten Snapshot)
2. `OTTO_CFG_PW=… node _build-kit/build.cjs --out …` — bettet Bibliotheken **und** die Historie ein, prüft die Syntax
3. Ergebnis in **alle Kopien** kopieren (`deploy.ps1` aus dem Deploy-Paket erledigt das):
   - `Digital Experience – KI-Tools/Otto_Obligo_View/OttoObligoCockpit.html`  (Live-Datei)
   - `Digital Experience – KI-Tools/Otto_Obligo_View/_build-kit/Otto-Obligo-Cockpit.html`  (Referenz)
   - `Dokumente/Otto-Obligo-Cockpit/Otto-Obligo-Cockpit.html`
   - `Dokumente/Otto-Obligo-Cockpit.html`

## Manueller Fallback (ohne Claude, mit Node installiert)
Im `_build-kit`-Ordner auf SharePoint liegen `app_template.html`, `build.cjs` und `vendor/` (SheetJS, jsPDF, pako):
```
# neue Register-CSV als hist_register.csv hier ablegen, dann (PowerShell):
$env:OTTO_CFG_PW = "<Passwort der 🔒-Einstellungen>"
node build.cjs --out ..\OttoObligoCockpit.html
# danach die HTML in die übrigen Zielorte kopieren (deploy.ps1)
```
Ohne `OTTO_CFG_PW` bricht der Build absichtlich ab — das Passwort steht nicht mehr im Code.

## Hinweise
- Der **laufende Monat** (teils auch Vormonat) ist im Diagramm meist **unvollständig** — Rechnungen treffen verzögert ein.
- Die Historie sitzt hinter dem 🔒-Passwort — sie ist bewusst nicht im teilbaren PDF.
- Der eingebettete Stand ändert nichts am Obligo — Historie ist reine Rückschau, unabhängig von den Tages-Uploads.
