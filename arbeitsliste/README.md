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

## Stand am 01.09.2026

| | Aufträge | Geräte |
|---|---:|---:|
| Termin verstrichen, nicht abgeholt | 11 | 668 |
| Kommissioniert, kein Termin | 4 | 143 |
| Kommissionierung offen / Restmenge unklar | 7 | 436 |
| **Offen gesamt** | **22** | **1.247** |
| Aufräumen (storniert / Geisterzeilen) | 4 | 157 |
| Prüffall S01254 (Rati Marti, Ware der Altzeilen) | 1 | 133 |

Ältester Vorgang ohne Termin: **S00622, Aurora Solar Energy — 33 Tage kommissioniert.**

## Drei Befunde, die nicht in der Liste stehen

1. **Das Dashboard meldet fälschlich „kein WA-Backlog“.** Seit dem Odoo-Wechsel tragen
   alle Aufträge `S00xxx`-Nummern. Die Zählformeln in `00_DASHBOARD` und `05_LIVE`
   filtern weiter auf `LINKS(Auftragsnr;2)="AU"` — im August trifft das auf **0 von 65**
   Aufträgen zu. Betroffen: `05_LIVE` C12, C13, C17, C25, C26, C30, C39, C40, D25, D26,
   D39, D40 und `00_DASHBOARD` C11. Fix: Bedingung streichen oder auf
   `ODER(LINKS(…;2)="AU"; LINKS(…;1)="S")` erweitern.

2. **Restmengen aus Teilverladungen existieren in keiner Pipeline-Zeile.** Wenn ein LKW
   nicht alles fasst, meldet AMM die zurückgelagerten Lagernummern nur per Mail. Aktuell
   offen: `S01307` (Outlet Simex, 27.08.) und `S01315` (Geo Hansi, 26.08.).

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
