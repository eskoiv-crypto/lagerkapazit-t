# Warenwert zum Stichtag 31.08.2026

**Status: nicht berechenbar — es fehlen die Daten zum Stichtag.**
Stand der Recherche: 01.09.2026.

> **Hinweis:** Dieses Repository ist öffentlich. Konkrete Einkaufswerte,
> Stückzahlen und Zitate aus internen Abstimmungen stehen deshalb **nicht** in
> dieser Datei. Die Zahlen selbst gehören in die interne Ablage
> (`Warenwert zum Monatsende …xlsx` in Teams/OneDrive) — hier steht nur der
> Rechenweg. `warenwert_monatsende.csv` und `warenwert_facts_*.json` sind aus
> demselben Grund per `.gitignore` ausgeschlossen.

---

## 1. Kurzfassung

| | |
|---|---|
| Warenwert 31.08.2026 | **nicht berechenbar** — keine Datenquelle mit Stand 31.08.2026 |
| Letzter bestätigter Wert | 31.07.2026 (Reihe „Warenwert zum Monatsende", intern) |
| Jüngste AMM-Bestandsliste | **18.08.2026** (`BESTAND134_20260818_1600.CSV`) |
| Jüngster Odoo-Export | **25.08.2026** (`LosSerie (stock.lot) (6).xlsx`, ODOO_dashboard) |
| Fehlt für den Stichtag | Bestandsliste **31.08.2026** + Odoo-Export **≥ 31.08.2026** |

Aus den vorhandenen Ständen (18.08. / 25.08.) ließe sich eine Zahl erzeugen — sie
wäre aber weder stichtagsrein noch gegenüber der Steuerkanzlei vertretbar und
würde sich nicht in die Monatsreihe einreihen. Deshalb hier keine Zahl, sondern
der fertige Rechenweg (Abschnitt 4) und die zwei fehlenden Handgriffe
(Abschnitt 5).

---

## 2. Was „wie zuletzt immer berechnet" konkret heißt

Die Definition wurde am **13./14.08.2026** intern für die Abstimmung mit der
Steuerkanzlei festgelegt:

```
Warenwert(S) = Σ Einkaufspreis aller Geräte, die am Stichtag S
               physisch im Lager NH5 standen — unabhängig vom Verkaufsstatus
```

Bewertet wird also alles, was **tatsächlich im Lager liegt**, einschließlich
bereits an Kunden verkaufter, aber noch nicht ausgelieferter Ware — nicht nur die
freiverkäufliche. Das entspricht dem großen Wert aus den Odoo-KPIs.

| Baustein | Regel | Quelle |
|---|---|---|
| Mengengerüst | alle Zeilen der AMM-Bestandsliste, Status **QE + VS + AA** | `BESTAND134_<Stichtag>.CSV` |
| Preis | Einkaufspreis je Lager-Nr | Odoo `stock.lot` |
| Preis (Altbestand) | `Buying_Price` je Lager-Nr | Portal Stock-Analysis, **Endstand 02.07.2026** |
| fehlender EK | Ø-EK: Produktkategorie → Marke → Bezeichner → global | aus demselben Stichtag |
| Schrottware | echter EK **0 €**, kein Ø-Fill | interne Korrektur vom 14.08.2026 |

**Abgrenzung — nicht verwechseln:** Der Einseiter `Warenwert_30-06-2026.pdf`
zeigt die **engere** Sicht „nur freiverkäufliche Ware, nur mit belegtem EK" und
liegt deutlich unter dem Reihenwert desselben Stichtags. Das Skript kann beides:
`--umfang gesamt` (Reihenwert) bzw. `--umfang freiverkaeuflich`.

### Bekannte Unschärfen (intern festgehalten am 14.08.2026)

1. Ein **manuell gezogener** Export ist nicht der Mitternachtsstand des
   Monatsletzten — im Juli waren das zwei Tage Differenz.
2. Wo kein EK hinterlegt ist, wird mit **Durchschnittswerten** gerechnet.
   Herausgerechnet gehört die **AEG-Schrottware**, deren EK tatsächlich 0 ist.

Angekündigt ist, die Auswertung direkt aus der Datenbank ins Cockpit zu ziehen
(Monatsletzter, 00:00 Uhr); das erledigt Unschärfe 1 und macht die Rückrechnung
überflüssig.

---

## 3. Datenlage am 01.09.2026 — warum die Zahl fehlt

### 3.1 Die AMM-Bestandsmails sind seit dem 18.08.2026 abgerissen 🔴

`proWMS@amm-spedition.de` liefert normalerweise **täglich** um ~21:34 Uhr
„Bestand (Elvinci.de GmbH) im Lager AMM vom …". Die letzte Mail kam am
**18.08.2026** (an dem Tag ungewöhnlich um 13:04 / 14:04 / 15:04 Uhr).
Seither: nichts — weder im Postfach noch im SharePoint-Ordner
`01 TÄGLICH HOCHLADEN / 02 AMM BESTAND134` (letzte Datei
`BESTAND134_20260818_1600.CSV`). Auch „Eingänge", „Ausgänge" und
„Auftragsstand" enden am 18.08.2026.

Das ist unabhängig vom Warenwert ein Problem: dem Cockpit fehlen seit zwei
Wochen die täglichen Bestandsdaten. **Bitte bei AMM nachfassen.**

### 3.2 Odoo-Export endet am 25.08.2026

| Ort | Datei | Stand |
|---|---|---|
| `01 TÄGLICH HOCHLADEN / 01 Odoo (stock.lot)` | `LosSerie (stock.lot)19082026.xlsx` | 19.08.2026 |
| `KI-Tools / ODOO_dashboard` | `LosSerie (stock.lot) (6).xlsx` | 25.08.2026 |

Ein Export mit Stand **≥ 31.08.2026** existiert nirgends.

### 3.3 Das Portal ist tot

Laut `_LIESMICH - ORDNERSTRUKTUR.txt` (Stand 24.07.2026) ist das Portal seit
**03.07.2026** endgültig abgeschaltet; die Exporte vom 02.07.2026
(Stock-Analysis, All-Sold) sind der Endstand. Sie bleiben als **EK-Quelle für
Altbestand** relevant, liefern aber kein Mengengerüst mehr.

### 3.4 Warum die Zahl nicht per Connector zu holen ist

Der Microsoft-365-Connector gibt Tabellen nur bis ~400 Zeilen zurück; der
Odoo-Export hat gut 12.600. Die Einkaufspreise sind darüber nicht auslesbar.
Deshalb der Weg über das Skript, das lokal auf den echten Dateien läuft.

---

## 4. Der Rechenweg: `warenwert_stichtag.py`

Setzt die Definition aus Abschnitt 2 um und schreibt die Monatsreihe fort.
Selbsttest: `python3 tests/test_warenwert_stichtag.py` — prüft beide Umfänge,
Dubletten-Entfernung, Schrott-Regel, Ø-Fill-Kaskade, Stichtags-Wächter und
Reihen-Fortschreibung gegen von Hand nachgerechnete Sollwerte (synthetische
Testdaten, keine echten Bestände).

```bash
python3 warenwert_stichtag.py \
    --stichtag 2026-08-31 \
    --bestand "data/amm/BESTAND134_20260831_2330.CSV" \
    --odoo    "data/odoo/LosSerie (stock.lot)01092026.xlsx" \
    --stock-analysis "data/elvinci/Stock-Analysis-2026-07-02.xlsx" \
    --serie   warenwert_monatsende.csv \
    --json    warenwert_facts_2026-08-31.json
```

Das Skript **bricht ab**, wenn die Bestandsliste nicht vom Stichtag ist
(`--erlaube-abweichenden-stand` hebt das bewusst auf) — genau der Fehler, der
sonst still eine nicht stichtagsreine Zahl in die Steuer-Reihe schreibt.

Ausgabe: Warenwert, Gerätezahl, Aufteilung nach Preisquelle (Odoo / Portal /
Ø-Schätzung / Schrott), AMM-Statusverteilung und alle Vorbehalte als Hinweise.
Die Ergebnisdateien bleiben lokal (siehe `.gitignore`).

Die bestätigte Historie Sep-2025 … Jul-2026 steht in der internen Datei
`Warenwert zum Monatsende Sep25-Jul26 1.xlsx` (Teams/OneDrive). Als Startpunkt
für `--serie` daraus eine CSV mit den Spalten `Monatsende;Stück;EK-Wert`
(Datumsformat `TT.MM.JJJJ`, Semikolon) anlegen — sie bleibt lokal.
Hinweis: Der Wert für 31.08.2025 wurde nachträglich gegen die Zahl aus der
Buchhaltung korrigiert; die ältere Fassung der Datei trägt noch den alten Wert.

---

## 5. Was noch fehlt (2 Handgriffe)

1. **AMM-Bestandsliste zum 31.08.2026 beschaffen.**
   Die tägliche `proWMS`-Mail ist seit 18.08. abgerissen → bei AMM anfordern:
   Bestand Elvinci.de GmbH, Standort NH5, Stand 31.08.2026 23:59.
   Ablegen als `data/amm/BESTAND134_20260831_2330.CSV`.
   *(Und die tägliche Zustellung wieder in Gang bringen — sie fehlt dem
   gesamten Cockpit seit zwei Wochen.)*

2. **Odoo-Export ziehen** (Lager → Los/Seriennummern → Export, Feld
   *Einkaufspreis* enthalten), Stand ab 31.08.2026 — ein Export von heute
   genügt, solange die Bestandsliste den Stichtag setzt.
   Ablegen als `data/odoo/LosSerie (stock.lot)01092026.xlsx`.

Danach den Befehl aus Abschnitt 4 laufen lassen.

---

## 6. Wo gesucht wurde

Repo `lagerkapazit-t` · SharePoint `KI-Tools / Lager_Sales Dashboard`
(inkl. `_LIESMICH` und den `_INFO`-Dateien der Tagesordner) · SharePoint
`KI-Tools / ODOO_dashboard` · OneDrive Teams-Chatdateien · die Teams-Threads zur
Monatsreihe · Outlook (`proWMS@amm-spedition.de`).

Nirgends existiert ein Bestands- oder Odoo-Stand zum 31.08.2026, und für
August 2026 wurde bislang kein Warenwert gerechnet oder kommuniziert.
