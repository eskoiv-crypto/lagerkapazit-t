# Terminierung & Kommissionierplanung — Abarbeitungsliste

Entstanden am 01.09.2026, nachdem Janna Baranowski (Backoffice & Fulfillment) das
Unternehmen verlassen hat. Ihre Aufgaben — Termine mit Kunden, Bereitstellungs- und
Freigabemeldungen an AMM, Pflege der WA-Pipeline — müssen aufgefangen werden.

**Interaktive Liste:** `arbeitsliste.html` (im Browser öffnen, Haken bleiben lokal gespeichert)

---

## Datenlage

| Quelle | Stand | Verwendung |
|---|---|---|
| `Abhol-und_Liefertermine_Tagesaktuell.xlsx` (SharePoint, ODOO_dashboard) | 26.08.2026 | WA-Pipeline, 298 Aufträge seit April |
| `NH5_Pipeline_MAX-STATUS.xlsx`, Blätter `00_DASHBOARD` / `05_LIVE` | 01.09.2026 | Live-Kennzahlen, Formelprüfung |
| Outlook: `elvinci@amm-spedition.de`, `proWMS@amm-spedition.de` | 16.–31.08.2026 | Abgleich je Auftrag |

> **Lücke:** Das Master-Sheet liefert über den SharePoint-Zugriff nur die ersten vier
> Blätter; `20_WA_PIPELINE` wird abgeschnitten. Die auswertbare WA-Pipeline ist deshalb
> sechs Tage alt. Aufträge, die zwischen dem **27.08. und heute** neu dazugekommen sind,
> fehlen in dieser Liste. Alles darin wurde gegen die Mails bis zum 31.08. geprüft.

## Maßgebliches Kriterium: Spalte AC

Im Blatt `20_WA_PIPELINE` gibt es die Spalte **`AC — Auftrag abgeschlossen (Ware hat das
Lager verlassen) (AMM)`**. Steht dort ein Datum, ist die Ware raus. Das ist der einzige
verlässliche Beleg für einen Warenausgang.

> **Korrektur vom 01.09.2026.** Die erste Fassung dieser Auswertung stützte sich auf die
> Spalte „Status (automatisch)“ aus dem reduzierten Export `Abhol-und_Liefertermine_
> Tagesaktuell.xlsx`, der nur die Spalten A:X enthält — **ohne AB, AC, AF, AG**. Ergebnis:
> zwölf Aufträge standen als überfällig in der Liste, obwohl sie laut Spalte AC zwischen
> dem 18.08. und dem 31.08. verladen wurden, und mindestens sechs offene Aufträge fehlten.
> Der Status ist abgeleitet und im Export nur eine Momentaufnahme — er ist kein Ersatz für AC.

Fehlende Spalten im reduzierten Export:

| Spalte | Bedeutung |
|---|---|
| `AB` | Bezahlt? (JANNA) |
| `AC` | **Auftrag abgeschlossen — Ware hat das Lager verlassen (AMM)** |
| `AF` | Reste vorhanden NACH Verladung (AMM) |
| `AG` | Reste Lagernummern (AMM) |

## Stand am 01.09.2026 (Zeilen 267–309, KW 34–36)

| | Aufträge | Geräte |
|---|---:|---:|
| Ware noch im Lager (`AC` leer) | 13 | 855 |
| davon ohne Anmeldung oder ohne Kommissioniertag | 4 | 162 |
| davon nach dem 26.08. dazugekommen, Details fehlen | 6 | 598 |
| Restmengen nach Verladung offen (`AF` = ja) | 4 | — |
| Storniert, Ware trotzdem da | 1 | 13 |

**Zeilen 5–266 sind nicht gegen Spalte AC geprüft.** Ohne Export des Blatts fehlt der
Zugriff — über SharePoint bricht die Datei nach dem vierten Blatt ab, `20_WA_PIPELINE`
kommt dort nie an. Offen aus dem älteren Stand: `S00622` (Aurora Solar), `S00755` und
`S00642` (Euroda), `S00288` (Alma Trading, storniert).

Um das zu vervollständigen: Blatt `20_WA_PIPELINE` als CSV speichern, mindestens die
Spalten `D, E, F, G, U, AB, AC, AF, AG`.

## Drei Befunde, die nicht in der Liste stehen

1. **Das Dashboard meldet fälschlich „kein WA-Backlog“.** Seit dem Odoo-Wechsel tragen
   alle Aufträge `S00xxx`-Nummern. Die Zählformeln in `00_DASHBOARD` und `05_LIVE`
   filtern weiter auf `LINKS(Auftragsnr;2)="AU"` — im August trifft das auf **0 von 65**
   Aufträgen zu. Betroffen: `05_LIVE` C12, C13, C17, C25, C26, C30, C39, C40, D25, D26,
   D39, D40 und `00_DASHBOARD` C11. Fix: Bedingung streichen oder auf
   `ODER(LINKS(…;2)="AU"; LINKS(…;1)="S")` erweitern.

2. **Restmengen aus Teilverladungen haben eine eigene Spalte, aber keinen Vorgang.** Die
   Spalten `AF`/`AG` erfassen sie, es entsteht daraus aber kein terminierbarer Auftrag.
   Aktuell offen: `S01222`, `S01100`, `S01314`, `S01315`.

3. **Eine Rückfrage von AMM ist seit dem 21.08. unbeantwortet:** „Soll der Auftrag S01150
   noch zurückgehalten werden?“ Die Pipeline-Notiz dazu lautet „Warten auf Freigabe Janna“.

## Wiederkehrende Handgriffe, die jetzt niemand macht

| Handgriff | Zuletzt | Wozu |
|---|---|---|
| Mail „Abholung S0xxxx — bitte bereitstellen“ an AMM | 31.08. (S00944) | ohne sie stellt AMM nicht an die Rampe; 2–4×/Woche fällig |
| Mail „Freigabe S0xxxx“ an AMM | 28.08. (S00565) | Zahlung eingegangen, Ware darf raus |
| Zollabfertigung / LRN an AMM | 28.08. (Geo Hansi) | ohne LRN keine Verladung ins Nicht-EU-Ausland |
| Pflege der Spalten `Versand-/Abholanmeldung`, `geplantes Versand-/Abholdatum`, `Anlieferdatum` | 26.08. | in der Pipeline mit „(JANNA)“ überschrieben — Quelle jeder Terminaussage |
| Rückfragen von AMM beantworten | — | siehe S01150 |

## Auswertung reproduzieren

```bash
# Text-Export der WA-Pipeline (SharePoint -> read_resource) als Eingabe
python3 parse_wa_pipeline.py <export.txt> --stichtag 2026-09-01 --csv offene.csv
```

Das Skript kippt die offenen Vorgänge in die Buckets A–F, erkennt Sammelverladungen aus
den Notizspalten und warnt, sobald der `LEFT(...)="AU"`-Filter greift.

* `parse_wa_pipeline.py` — Parser und Bucket-Logik
* `wa_offene_auftraege_2026-08-26.csv` — Export der 26 offenen Vorgänge (Semikolon, UTF-8-BOM, Excel-tauglich)
* `arbeitsliste.html` — die Abarbeitungsliste

Kundenkontaktdaten sind bewusst nicht enthalten; für die Terminierung reichen
Auftragsnummer und Firmenname, die Kontakte stehen in Odoo.
