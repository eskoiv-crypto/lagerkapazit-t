# Ware noch im Lager — Terminierung & Kommissionierplanung

Entstanden am 01.09.2026, nachdem die zuständige Kollegin im Backoffice das Unternehmen
verlassen hat. Terminierung, Bereitstellungs- und Freigabemeldungen an AMM und die Pflege
der WA-Pipeline müssen aufgefangen werden.

**Interaktive Liste:** `arbeitsliste.html` — im Browser öffnen, Haken bleiben lokal gespeichert.

## Das maßgebliche Kriterium

Im Blatt `20_WA_PIPELINE` gibt es die Spalte

> **`AC — Auftrag abgeschlossen (Ware hat das Lager verlassen) (AMM)`**

Steht dort ein Datum, ist die Ware raus. **Das ist der einzige verlässliche Beleg für einen
Warenausgang.** Die Spalte `I — Status (automatisch)` ist davon abgeleitet und taugt nicht
als Ersatz: ein Auftrag kann „Versand überfällig“ anzeigen und trotzdem seit Tagen aus dem
Haus sein.

> **Korrekturhinweis.** Die erste Fassung dieser Auswertung beruhte auf dem reduzierten
> Export `Abhol-und_Liefertermine_Tagesaktuell.xlsx`, der nur die Spalten A:X enthält —
> ohne `AB`, `AC`, `AF`, `AG`. Sie stufte deshalb zwölf bereits verladene Aufträge als
> überfällig ein und übersah sechs offene. Seit dem CSV-Export des vollständigen Blatts
> ist das behoben.

## Stand 01.09.2026

316 Auftragszeilen seit April · 280 mit gefüllter Spalte AC · 36 ohne.

| Gruppe | Vorgänge | Geräte |
|---|---:|---:|
| **A · Kein Termin bei AMM** (Anmeldung „warten“ oder leer) | 14 | 721 |
| **B · Angemeldet, Ware trotzdem im Lager** | 13 | 1.020 |
| **Ware im Lager gesamt** | **27** | **1.741** |
| C · Ware raus, Restmenge geblieben (Spalte `AF`) | 4 | — |
| D · Karteileichen (storniert / von AMM ersetzt) | 4 | 157 |
| E · Altzeilen vor Juni, Spalte AC nie gepflegt | 5 | 634 |

Auf 495 Paletten. **10 Vorgänge mit 799 Geräten sind bezahlt und liegen trotzdem im Lager.**
Längste Liegezeit seit Kommissionierung: 34 Tage (`S00642`, Euroda).

Nur ein Auftrag hat gar keinen Kommissioniertag: `S01150` (Marketvibe) — dort wartet AMM
seit dem 21.08. auf eine Antwort.

## Zwei Baustellen in der Datei selbst

1. **Der AU-Filter.** Seit dem Odoo-Wechsel tragen alle Aufträge `S00xxx`-Nummern. Die
   Zählformeln filtern weiter auf `LINKS(Auftragsnr;2)="AU"` — im August traf das auf
   0 von 65 Aufträgen zu. Betroffen: `05_LIVE` C12, C13, C17, C25, C26, C30, C39, C40,
   D25, D26, D39, D40 und `00_DASHBOARD` C11. Fix: Bedingung streichen oder auf
   `ODER(LINKS(…;2)="AU"; LINKS(…;1)="S")` erweitern.

2. **Die Backlog-Formel zeigt ins Leere.** `00_DASHBOARD` prüft
   `NICHT(ISTZAHL('20_WA_PIPELINE'!$AD$5:$AD$542))`. Spalte `AD` hat weder Überschrift
   noch in einer der 316 Zeilen einen Wert — die Bedingung ist immer wahr. Gemeint ist
   `AC`. Fix: `$AD$` durch `$AC$` ersetzen.

Zusammen erklären die beiden, warum das Dashboard „WA-Pipeline offen – kein Backlog“
meldet, während 27 Vorgänge im Lager stehen.

## Wiederkehrende Handgriffe ohne Nachfolge

| Handgriff | Zuletzt | Wozu |
|---|---|---|
| Mail „Abholung S0xxxx — bitte bereitstellen“ an AMM | 31.08. | ohne sie stellt AMM nicht an die Rampe; 2–4× pro Woche fällig |
| Mail „Freigabe S0xxxx“ an AMM | 28.08. | Zahlung eingegangen, Ware darf raus |
| Zollabfertigung / LRN an AMM | 28.08. | ohne LRN keine Verladung ins Nicht-EU-Ausland |
| Pflege der Spalten mit „(JANNA)“ im Kopf | 31.08. | Anmeldung, geplantes Datum, Zollpapiere, „Bezahlt?“ |
| Rückfragen von AMM beantworten | — | `S01150` wartet seit dem 21.08. |

## Liste neu erzeugen

Blatt `20_WA_PIPELINE` als CSV speichern (Semikolon, Windows-1252), dann:

```bash
python3 build_arbeitsliste.py 20_WA_PIPELINE.csv --stichtag 2026-09-01
```

Das Skript liest alle 33 Spalten, gruppiert nach Spalte AC und schreibt den Datenblock
direkt in `arbeitsliste.html` (zwischen den Markern `/* DATA-START */` und `/* DATA-END */`).
Verifizierte Zusatzinfos aus dem AMM-Mailverkehr stehen im Dict `NOTIZ`.

| Datei | Inhalt |
|---|---|
| `build_arbeitsliste.py` | Parser, Gruppierung, HTML-Injektion |
| `arbeitsliste.html` | die Liste |
| `arbeitsliste.data.json` | erzeugter Datenstand |
| `20_WA_PIPELINE_2026-09-01.csv` | Quellexport |
| `parse_wa_pipeline.py` | älterer Parser für den reduzierten A:X-Export |

Kundenkontaktdaten sind bewusst nicht enthalten; für die Terminierung reichen
Auftragsnummer und Firmenname, die Kontakte stehen in Odoo.
