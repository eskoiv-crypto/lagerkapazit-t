# Otto-Obligo-Cockpit — START HIER

**Version:** v2.1 · **Stand:** 2026-09-18 (Neu: einzelne Rechnungs-PDFs direkt einlesen)

**Zweck:** Zeigt jederzeit das **tatsächliche Obligo** gegenüber Otto vs. dem **500.000 €-Kreditlimit** — als reine **Ist-Aufnahme** (keine Prognose):

> **Obligo heute = ALLE offenen Agicap-Rechnungen + LKW mit Lieferschein, aber noch KEINER Rechnung**

Wo eine Rechnung vorliegt (egal ob geprüft, „zu prüfen", im Posteingang **oder als einzelnes PDF**), kommt der Betrag aus dem Beleg bzw. aus Agicap. Nur die LKW, für die es noch **gar keine** Rechnung gibt (nur Lieferschein), werden zusätzlich aus den Bestellungen addiert. So greifst du den bevorstehenden Rechnungen vor — ohne etwas doppelt zu zählen.

**Zugriff:** nur GF / Backoffice-Lead / Buchhaltung. Die Rohdaten enthalten Otto-Konditionen → **nicht nach außen geben.**

---

## Tages-Routine (3 Schritte)

### 1. Exporte ziehen → Ordner `01_Taegliche-Exporte_HIER-ABLEGEN`

| # | Datei | Quelle in Agicap / Odoo / Outlook |
|---|---|---|
| 1 | `1_Agicap_Geprueft.csv` | Agicap → Lieferantenrechnungen → Tab **„Geprüft"** → CSV herunterladen |
| 2 | `2_Agicap_ZuPruefen.zip` | Agicap → Lieferantenrechnungen → Tab **„Zu prüfen"** → Rechnungen exportieren (kommt als **ZIP** mit PDF-Belegen) |
| 3 | `3_Bestellungen.xlsx` | Odoo → `purchase.order` „Bestellung" → Export (letzte ~45 Tage, Filter Otto). **Spalte „Lieferantenreferenz" mit exportieren** — sie enthält die Plombe und schaltet den zuverlässigen Plombe-Abgleich frei. |
| 4 *(neu, optional)* | `Otto GmbH … 1001EO….pdf` | **Einzelne Otto-Rechnungs-PDFs**, die noch **nicht in Agicap** sind (z. B. gerade per Mail eingetroffen) — direkt aus Outlook speichern. |

> **Wichtig:** Beide Agicap-Teile laden — „Geprüft" **und** „Zu prüfen". Fehlt „Zu prüfen", ist das Obligo zu niedrig. Falls Agicap dir einen Tab **„Ausstehende Rechnungen"** (= alles Offene) als eine CSV gibt, reicht die statt 1+2.

### 2. Tool öffnen und Dateien reinziehen
`Otto-Obligo-Cockpit.html` doppelklicken. Dann:
- **Feld „Agicap / Rechnungen":** CSV („Geprüft"), ZIP („Zu prüfen") **und einzelne PDFs** hineinziehen — **auch alle auf einmal** (mehrere Dateien markieren und ablegen). Das Tool **addiert** alles (Anzeige „Σ … offen") und **entdoppelt über die Rechnungsnummer**: Eine Rechnung, die als PDF **und** in der Agicap-CSV/ZIP steckt, zählt genau einmal.
- **Feld „Bestellungen":** die `3_Bestellungen.xlsx`.

Unter den Kacheln erscheint ein **Lade-Protokoll**: je Datei ✓ mit Rechnungsnummer und Betrag (bei PDFs) bzw. Anzahl offener Rechnungen; fehlerhafte Dateien stehen mit Grund in einer roten Box — die gültigen Dateien desselben Drops zählen trotzdem.

Neu laden der Seite = zurücksetzen (falls du dich vertan hast).

### 3. PDF erstellen
Button **„📄 PDF-Auswertung"** → als `Otto-Obligo_JJJJ-MM-TT.pdf` in `02_PDF-Auswertungen_teilbar` speichern.
Danach die Rohexporte des Tages nach `03_Archiv_Rohdaten_vertraulich/JJJJ-MM-TT/` verschieben.

---

## Einzelne PDFs — was das Tool daraus liest (und was nicht)

| Feld | Woher | Hinweis |
|---|---|---|
| **Brutto-Betrag** | erster Betrag nach **„Gesamt Rechnungsbetrag"** im Beleg | Rückfall: letzter Betrag im PDF → dann steht **⚠️ „bitte prüfen"** im Protokoll (z. B. wenn Otto das Layout ändert). Bei Belegen mit angehängter Artikel-Aufstellung ist der Anker entscheidend — der letzte Betrag wäre dort ein Artikelpreis. |
| **Rechnungsnummer** | „Rechnungsnummer: 1001EO…" im Text, sonst aus dem Dateinamen | Grundlage der Entdopplung. Ohne Nummer wird über Betrag + Datum entdoppelt. |
| **Rechnungsdatum** | „Hamburg, TT. Monat JJJJ" | nur intern für den Fälligkeits-Zeitstrahl (+30 Tage); wird nicht angezeigt |
| **Plombe** | 7 Ziffern nach „Plombe" (nur auf LKW-Belegen) | Plombe-Abgleich gegen die Bestellungen wie bisher |
| **Warenart** | nur aus dem Agicap-Dateinamen („… Purchase Otto Mix.pdf") | bei einem selbst gespeicherten PDF meist „—"; hat keinen Einfluss auf das Obligo |

**Abgewiesen werden** (mit Meldung, ohne die anderen Dateien zu stören): PDFs ohne „Otto GmbH" im Text (Fremdbelege), Scans/Bilder ohne Textebene, Dateien, die keine PDF sind.
**Gutschriften/Retourenvergütungen:** Es zählt immer der ausgewiesene **Rechnungsbetrag (brutto)** des Belegs — Vergütungen, die Otto bereits auf dem Beleg verrechnet hat, sind darin schon abgezogen.

---

## Was das Cockpit anzeigt

**Drei Kacheln:**
1. **Tatsächliches Obligo an Otto — heute** (ampelfarbig gegen das 500k-Limit)
2. **Offene Rechnungen (Agicap)** — alle vorliegenden, noch nicht bezahlten Rechnungen (geprüft + zu prüfen + Posteingang + Einzel-PDFs)
3. **Warten auf Rechnung** — gelieferte LKW mit Lieferschein, für die noch KEINE Rechnung da ist

Dazu: **Balken gegen das Limit**, Liste der „warten auf Rechnung"-LKW und ein **Validierungs-Panel** (Abgleich aller Zahlen, keine Doppelzählung).

## Zwei Zustände nicht verwechseln
- **„Zu prüfen"** (Agicap, elvinci-intern) = die **Rechnung liegt vor**, wird nur noch intern geprüft/freigegeben. → zählt über **Agicap**.
- **„Warten auf Rechnung"** (Odoo-Status „Blockiert") = es gibt **noch gar keine** Rechnung, nur den Lieferschein. → zählt über die **Bestellungen**.
- **Einzel-PDF** = Rechnung liegt vor, ist aber noch nicht in Agicap. → zählt über das **PDF**; sobald sie in Agicap auftaucht und mitgeladen wird, greift die Entdopplung über die Rechnungsnummer.

## Referenz = Lieferschein
Jede Otto-Bestellung in Odoo mit **Referenznummer** (P000xx) hat einen Lieferschein — der LKW ist verladen und wird sicher zur Rechnung. Nur **stornierte** Positionen zählen nicht. LKW **ohne** Lieferschein stehen gar nicht in Odoo → tauchen im Tool nicht auf.

## Doppelzählungs-Schutz — zweistufig
1. **Plombe-Abgleich (zuverlässig, grün ✓):** Die **Plombe** auf der Rechnung (aus dem PDF gelesen) = **Lieferantenreferenz** der Bestellung → derselbe LKW. Passt beides, wird der LKW aus „warten" entfernt. Funktioniert **auch bei kleinen Betragsdifferenzen** — die Plombe ist der harte Schlüssel, nicht der Betrag. Dafür muss die Spalte **Lieferantenreferenz** im Odoo-Export enthalten sein.
2. **100 %-Cent-Alarm (Rückfall, rot 🚨):** Gibt es keine Plombe, aber ein „warten"-LKW stimmt **auf den Cent** mit einer offenen Rechnung überein, erscheint ein Alarm und der LKW wird entfernt. **Nur** bei centgenauer Deckung.

Beides steht transparent im **Validierungs-Panel**.

## Was das PDF zeigt (und bewusst NICHT)
**Zeigt:** Obligo heute vs. Limit · Aufteilung (offene Rechnungen / warten auf Rechnung) · Balken · Liste der „warten auf Rechnung"-LKW.
**Zeigt NICHT:** Fälligkeiten, das 30-Tage-Zahlungsziel, einzelne Rechnungs-Fälligkeiten.

## Historie (fest eingebettet, hinter 🔒 — lädt automatisch)
Die Otto-Historie ist **fest ins Tool eingebettet** und wird bei **jedem Öffnen automatisch geladen**. Nach dem 🔒-Entsperren zeigt sie „Otto-Volumen" als Balken (Rechnungen / Gezahlt · Tag / Woche / Monat). Frischeren Stand einspielen: Register-Export ins Feld „Historie" ziehen (nur diese Sitzung) oder neu einbetten lassen (siehe `REFRESH-Historie.md`; Build jetzt mit `node build.cjs`).

## Fälligkeiten-Zeitstrahl (intern, hinter 🔒)
Nach dem Entsperren erscheint ein **Fälligkeits-Zeitstrahl** (nächste 30 Tage). **Bewusst OHNE Rechnungsdatum und ohne 30-Tage-Ziel** — und **nicht** im teilbaren PDF.

## Einstellungen
Hinter „🔒 Einstellungen" (Passwort): Stichtag + Kreditlimit + der Fälligkeiten-Zeitstrahl. **Weicher Schutz** — hält Gelegenheitsblicke ab, keine echte Verschlüsselung. Passwort ändern: beim Bauen über `OTTO_CFG_PW` bzw. `_build-kit/local.config.json` (siehe README) — nicht mehr im Template.

*Master bleibt intern · Otto bekommt nie diese Dateien.*
