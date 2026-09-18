# Otto-Obligo-Cockpit · Build-Kit (Repo-Kopie)

**Stand:** 2026-09-18 · **Version:** v2.1 (PDF-Import) · Sprache: Deutsch

Das Otto-Obligo-Cockpit ist eine Single-File-HTML-App (offline, keine Server), die das tatsächliche
Obligo gegenüber Otto gegen das Kreditlimit zeigt. **Quelle der Wahrheit für den Betrieb** bleibt SharePoint:
`PlattformenTeams › Tools und Automatisieren › KI-Tools › Otto_Obligo_View` (Cockpit + `_build-kit`).
Dieses Verzeichnis ist die versionierte Kopie des Build-Kits, damit Änderungen nachvollziehbar und getestet sind.

## Was ist neu in v2.1 (2026-09-18)

- **Einzelne Otto-Rechnungs-PDFs** können direkt in die Kachel „Agicap / Rechnungen“ gezogen werden
  (z. B. eine Rechnung aus dem Posteingang, bevor sie in Agicap ist). Bisher gingen PDFs nur verpackt in der Agicap-„Zu prüfen“-ZIP.
- **Mehrere Dateien auf einmal** (CSV + ZIP + PDFs gemischt) — jede wird gelesen, Fehler je Datei werden einzeln gemeldet,
  gültige Dateien zählen trotzdem.
- **Rechnungsnummer aus dem Beleg-Text** („Rechnungsnummer: 1001EO…“), Rückfall Dateiname. Dadurch entdoppelt das Tool
  eine Rechnung auch dann, wenn sie einmal per PDF und einmal per Agicap-CSV/ZIP geladen wird.
- **Rückfall-Kennzeichen:** Wird der Anker „Gesamt Rechnungsbetrag“ im PDF nicht gefunden und der letzte Betrag im PDF
  genommen, steht ein ⚠️-Hinweis im Lade-Protokoll („bitte prüfen“).
- **Fremd-PDFs** (kein „Otto GmbH“ im Text), Scans ohne Text und Nicht-PDFs werden mit klarer Meldung abgewiesen.
- PDF-Textextraktion robuster: `TJ`-Arrays, Escapes (`\(`, `\)`, `\ddd`), Zeilenfortsetzungen; nur Inhalts-Streams werden gelesen.
- Passwort der 🔒-Einstellungen ist ein Build-Parameter (siehe unten) statt Klartext im Template.

## Dateien

| Datei | Zweck |
|---|---|
| `_build-kit/app_template.html` | Quelltemplate der App (Platzhalter `__SHEETJS__`, `__JSPDF__`, `__PAKO__`, `__HISTCSV__`, `__CFGPW__`) |
| `_build-kit/build.cjs` | Build-Skript: bettet Bibliotheken (aus `node_modules`), optional die Historie und das Passwort ein, prüft die Syntax |
| `_build-kit/hist_register.csv` | **nicht im Repo** (`.gitignore`) — Agicap-Register-Export mit Otto-Konditionen, vertraulich |
| `_build-kit/local.config.json` | **nicht im Repo** — `{"cfgPw":"…"}` für das Einstellungs-Passwort |
| `dist/` | **nicht im Repo** — Build-Ausgaben (der Test baut hier `Otto-Obligo-Cockpit.test.html` ohne Historie) |
| `00_START-HIER_Anleitung.md` | Bedienungsanleitung (aktualisierte Fassung für SharePoint) |

## Bauen

```bash
npm install                                   # einmalig: xlsx, jspdf, pako, @playwright/test

# Produktiv-Build für SharePoint (MIT Historie):
#   1. aktuellen Agicap-Register-Export als otto-obligo/_build-kit/hist_register.csv ablegen (bleibt git-ignoriert)
#   2. Passwort der 🔒-Einstellungen setzen: OTTO_CFG_PW=… oder otto-obligo/_build-kit/local.config.json {"cfgPw":"…"}
#      (Pflicht — das Repo ist öffentlich, deshalb steht kein Standard-Passwort im Code)
OTTO_CFG_PW=… node otto-obligo/_build-kit/build.cjs      # -> otto-obligo/dist/Otto-Obligo-Cockpit.html (git-ignoriert)

# Build ohne Historie (z. B. zum Testen):  … build.cjs --no-hist --out <pfad>
```

Der Ordner `dist/` ist git-ignoriert: Der fertige Build enthält die Historie (Otto-Konditionen) und gehört **nur** nach SharePoint, nie ins Repo.

Der fertige Build wird in die bekannten SharePoint-Ablagen kopiert (siehe `REFRESH-Historie.md` im SharePoint-Build-Kit):
`Otto_Obligo_View/OttoObligoCockpit.html`, `Dokumente/Otto-Obligo-Cockpit/…`, `Dokumente/Otto-Obligo-Cockpit.html`.

## Testen

```bash
node tests/fixtures/make_otto_fixture.cjs     # synthetische Otto-PDFs / ZIP / CSV neu erzeugen (bereits eingecheckt)
npx playwright test tests/otto-obligo.spec.js # baut vorher selbst nach dist/ (ohne Historie, Test-Passwort)
# Cloud-Sandbox mit vorinstalliertem Chromium: PW_CHROMIUM_PATH=/opt/pw-browsers/chromium npx playwright test …
```

Die Fixtures sind **synthetisch** (Struktur wie echte Otto-Belege: Type1/WinAnsi, FlateDecode, `Tj`/`TJ`), enthalten keine echten
Rechnungsdaten. Echte Belege werden nicht ins Repo gelegt (Otto-Konditionen, personenbezogene Daten).

## Rechenlogik (unverändert)

Obligo heute = alle offenen Agicap-Rechnungen (Geprüft + Zu prüfen + Posteingang, jetzt auch Einzel-PDFs)
+ LKW mit Lieferschein, aber noch keiner Rechnung (Odoo „Blockiert“). Doppelzählungsschutz: Plombe-Abgleich, dann 100 %-Cent-Alarm.
Je PDF-Beleg: Brutto = erster Betrag nach „Gesamt Rechnungsbetrag“ (Rückfall: letzter Betrag im PDF, dann ⚠️),
Rechnungsdatum aus „DD. Monat JJJJ“, Fälligkeit intern = Rechnungsdatum + 30 Tage, Plombe = 7 Ziffern nach „Plombe“.
