# Otto-Obligo-Cockpit · Build-Kit (Repo-Kopie)

**Stand:** 2026-09-25 · **Version:** v2.3 (Kontinuitätsprüfung + Obligo-Verlauf) · Sprache: Deutsch

Das Otto-Obligo-Cockpit ist eine Single-File-HTML-App (offline, keine Server), die das tatsächliche
Obligo gegenüber Otto gegen das Kreditlimit zeigt. **Quelle der Wahrheit für den Betrieb** bleibt SharePoint:
`PlattformenTeams › Tools und Automatisieren › KI-Tools › Otto_Obligo_View` (Cockpit + `_build-kit`).
Dieses Verzeichnis ist die versionierte Kopie des Build-Kits, damit Änderungen nachvollziehbar und getestet sind.

## Was ist neu in v2.3 (2026-09-25)

Anlass: Das Obligo sprang von einem Tag auf den anderen deutlich stärker, als es durch die Anlieferungen
erklärbar war. Beide Tageswerte waren *für sich* korrekt — nur war am Vortag nichts zu sehen, was den Sprung
angekündigt hätte.

### Kontinuitätsprüfung (die eigentliche Neuerung)
Zwischen zwei Auswertungen darf sich das Obligo **nur** aus zwei Gründen ändern:

| | |
|---|---|
| neue LKW angeliefert | Obligo steigt |
| Rechnungen bezahlt | Obligo sinkt |

Der Wechsel eines LKW von „warten auf Rechnung“ nach Agicap ist **neutral** — derselbe LKW, anderer Topf.
Weicht die tatsächliche Änderung davon ab, fehlten Belege. Das Tool rechnet das beim Öffnen gegen den zuletzt
gespeicherten Stand und meldet die Abweichung im Klartext, inklusive Anzahl und Summe der neuen LKW, der
verbuchten Zahlungen und des erwarteten Werts.

Ursache solcher Lücken in der Praxis: Odoo setzt einen LKW auf „Validiert“, sobald die Ware klassifiziert ist —
die Rechnung von Otto kommt aber oft erst Tage später in Agicap an. In diesem Fenster steckt der LKW in
**keinem** der beiden Töpfe und fehlt im Obligo. Tauchen die Rechnungen dann gebündelt auf, springt die Zahl.

Der Stand liegt **lokal im Browser** (`localStorage`, nur Summen + Auftragsnummern, keine Beträge je Rechnung).
Fortgeschrieben wird nur eine **vollständige** Auswertung (Agicap **und** Bestellungen) — ein Stand ohne
Bestellungen enthält die „warten“-LKW nicht und wäre als Vergleichsbasis systematisch zu niedrig.

### Obligo-Verlauf, 45 Tage rückgerechnet
Der Agicap-Export trägt zu jeder Rechnung Rechnungs- und Zahlungsdatum. Damit ist der offene Betrag für jeden
vergangenen Tag **exakt** rekonstruierbar — keine Schätzung, keine Prognose. Die Kurve zeigt den Anstieg und
markiert den Tag, an dem das Limit gerissen wurde. Warnt zusätzlich, wenn seit ≥ 7 Tagen **kein
Zahlungseingang** verbucht ist: dann wächst das Obligo mit jedem LKW ungebremst.

Die „warten“-LKW sind in der Kurve **nicht** enthalten (rückwirkend nicht bestimmbar) — sie liegt also eher
etwas zu tief. Das steht auch unter der Grafik.

### Zahlungsziel 28 statt 30 Tage
Für Belege ohne Agicap-Fälligkeitsdatum (PDF-/ZIP-Pfad) galt bisher „Rechnungsdatum + 30“. Das tatsächliche
Zahlungsziel liegt bei **28** Tagen — in einem Referenz-Export tragen 20 von 24 Zeilen genau 28 Tage, drei 29,
eine 30. Betraf nur die Fälligkeits-Darstellung im Zahlungsplan, nie die Obligo-Summe.

### Zweite Bezeichnung für den Retouren-Abzug
Derselbe prozentuale Abzug wird auf den Belegen mal als „Retourenvergütung“, mal als „Retourenabschlag“
geführt. Nur die erste Variante wurde erkannt; bei der zweiten wäre die Gegenprobe auf die Zwischensumme
zurückgefallen und hätte fälschlich Alarm geschlagen. Jetzt greifen beide Schreibweisen.

### Plombe-Abdeckung sichtbar
Nur Rechnungen **mit Plombe** lassen sich zweifelsfrei einem LKW zuordnen. Die Agicap-CSV trägt sie selten, die
PDF-Belege fast immer. Das Tool zeigt die Quote und sagt, wie man sie erhöht (PDFs bzw. „Zu prüfen“-ZIP
zusätzlich laden).

### Bewusst NICHT umgesetzt: automatische Korrektur des Obligos
Naheliegend wäre: „zähle jeden gelieferten LKW, bis seine Rechnung in Agicap gefunden ist“. Gegen echte Daten
getestet **produziert das Doppelzählungen** und wurde deshalb verworfen:

* Eine Rechnung kann **älter** sein als der Odoo-Datensatz des LKW — „Erstellt am“ ist kein Lieferdatum. Belegt
  an einem Fall mit centgenau gleichem Betrag, bei dem die Rechnung drei Tage vor der Bestellung datiert.
* Ohne Plombe bleibt als Merkmal nur der Betrag. Der weicht zwischen Bestellung und Rechnung um bis zu einige
  hundert Euro ab, während die LKW-Werte eng beieinanderliegen — jeder Fehlgriff zählt LKW **und** Rechnung.

Ein zu hohes Obligo ist gefährlicher als ein zu niedriges, weil daran Zahlungsentscheidungen hängen. Das Obligo
bleibt deshalb konstruktionsgemäß doppelzählungsfrei (jeder LKW in genau einem Topf); die Kontinuitätsprüfung
macht die Lücke **sichtbar**, statt sie stillschweigend wegzurechnen.

## Was ist neu in v2.2 (2026-09-20)

Ausgelöst durch die Otto-Retourenrechnung `<Otto-Rechnungsnummer>` (11 Seiten: Rechnung + Mailverlauf + Artikel-Aufstellung):

- **CID-/Identity-H-Text wird gelesen.** In diesem Beleg liegen **1695 von 1764 Textstücken** in CID-Fonts —
  bisher konnte das Tool nur die erste Seite lesen. Der Extraktor löst jetzt je Seite die **ToUnicode-CMap** jedes
  Fonts auf. Die Byte-Breite kommt aus `/Encoding /Identity-H` und wird **nicht** aus den Code-Werten geraten
  (10 von 15 Fonts dieses Belegs haben nur Codes < 256 und würden sonst byteweise falsch dekodiert).
- **Betrags-Gegenprobe.** Zusätzlich zum Anker „Gesamt Rechnungsbetrag“ liest das Tool Zwischensumme,
  Retourenvergütung, Nettobetrag und Umsatzsteuer und prüft `netto + USt = brutto`. Ergebnis steht im Lade-Protokoll
  (`Gegenprobe ✓` bzw. 🚨 bei Abweichung).
- **Retourenvergütung wird ausgewiesen.** Bei Retourenbelegen zeigt das Protokoll Satz und Betrag der Vergütung
  sowie die Zwischensumme — so ist nachvollziehbar, warum aus <Betrag> Zwischensumme <Betrag> Rechnungsbetrag werden.
- **Rückfall entschärft.** Ohne Anker wird der Brutto-Betrag aus netto + USt rekonstruiert; erst danach greift
  „letzter Betrag“ — und zwar **nur auf Seite 1**. Der letzte Betrag des ganzen Dokuments wäre in diesem Beleg
  **<Betrag>** statt <Betrag> gewesen.
- **Mehrere Rechnungen in einer Datei** (zusammengefasstes Mail-PDF) werden erkannt und **abgewiesen**, statt still
  nur die erste zu zählen.
- **Rechnungsdatum** kommt bevorzugt aus dem Ort-Datum-Kopf („Hamburg, 08. September 2026“); sonst gewönne ein
  Datum aus dem eingebetteten Mailverlauf.

## Was war neu in v2.1 (2026-09-18)

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
Je PDF-Beleg (Kaskade, erste greifende Regel gewinnt):
1. erster Betrag nach **„Gesamt Rechnungsbetrag“**
2. anderer Brutto-Anker („Rechnungsbetrag (brutto)“, „Gesamtbetrag“, „Rechnungsendbetrag“)
3. **netto + USt** rekonstruiert (⚠️ markiert)
4. letzter Betrag **auf Seite 1** (⚠️ markiert)

Dazu Gegenprobe `netto + USt = brutto`, Rechnungsdatum bevorzugt aus dem Ort-Datum-Kopf,
Fälligkeit intern = Rechnungsdatum + 30 Tage, Plombe = 7 Ziffern nach „Plombe“.
