# Warenwert zum Stichtag 31.08.2026

**Status: keine belastbare Zahl berechenbar — die Stichtagsdaten fehlen.**
Stand der Recherche: 01.09.2026 (Repo, SharePoint/OneDrive, Teams-Chats, Outlook).

---

## 1. Kurzfassung

| | |
|---|---|
| **Warenwert 31.08.2026** | **nicht berechenbar** — es existiert keine Datenquelle mit Stand 31.08.2026 |
| Letzter bestätigter Wert | **31.07.2026 · 5.719 Geräte · 690.125 €** |
| Vorletzter Wert | 30.06.2026 · 5.433 Geräte · 661.584 € |
| Jüngste AMM-Bestandsliste | **18.08.2026** (5.468 Geräte: QE 4.162 · VS 926 · AA 380) |
| Jüngster Odoo-Export | **25.08.2026** (`LosSerie (stock.lot) (6).xlsx`, ODOO_dashboard) |
| Fehlt für den Stichtag | Bestandsliste **31.08.2026** + Odoo-Export **≥ 31.08.2026** |

Es wäre möglich gewesen, aus den vorhandenen Ständen (18.08. / 25.08.) eine Zahl
zu erzeugen — sie wäre aber weder stichtagsrein noch gegenüber der Steuerkanzlei
vertretbar und hätte sich nicht in die Monatsreihe eingereiht. Deshalb steht hier
keine Zahl, sondern der fertige Rechenweg (Abschnitt 4) und die zwei Handgriffe,
die noch fehlen (Abschnitt 5).

---

## 2. Was „wie zuletzt immer berechnet" konkret heißt

Die Definition wurde am **13./14.08.2026** im Teams-Thread (Vasiadis · Eskofier ·
Schneider) für die Abstimmung mit der Steuerkanzlei festgelegt:

> „ich benötige die Warenbestände für jeden Monat seit September 2025 anhand der
> Waren die wir **tatsächlich im Lager** haben (**inklusive Waren die an die Kunden
> verkauft sind**) — das wäre der **große Wert der bei ODOO KPIs erscheint** und
> **nicht nur die freiverkäufliche Ware**."  — K. Vasiadis, 13.08.2026

Daraus:

```
Warenwert(S) = Σ Einkaufspreis aller Geräte, die am Stichtag S
               physisch im Lager NH5 standen — unabhängig vom Verkaufsstatus
```

| Baustein | Regel | Quelle |
|---|---|---|
| Mengengerüst | alle Zeilen der AMM-Bestandsliste, Status **QE + VS + AA** | `BESTAND134_<Stichtag>.CSV` |
| Preis | Einkaufspreis je Lager-Nr | Odoo `stock.lot` |
| Preis (Altbestand) | `Buying_Price` je Lager-Nr | Portal Stock-Analysis, **Endstand 02.07.2026** |
| fehlender EK | Ø-EK: Produktkategorie → Marke → Bezeichner → global | aus demselben Stichtag |
| Schrottware | echter EK **0 €**, kein Ø-Fill | Korrektur D. Schneider, 14.08.2026 |

**Abgrenzung — nicht verwechseln:** Der Einseiter `Warenwert_30-06-2026.pdf`
(226.987 € / 3.171 Geräte) ist die **engere** Sicht „nur freiverkäufliche Ware,
nur mit belegtem EK". Das ist *nicht* der Reihenwert. Der Reihenwert für denselben
Stichtag lautet 661.584 € / 5.433 Geräte. Das Skript kann beides
(`--umfang gesamt` bzw. `--umfang freiverkaeuflich`).

### Bekannte Unschärfen (D. Schneider, 14.08.2026, von allen akzeptiert)

1. Ein **manuell gezogener** Export ist nicht der Mitternachtsstand des
   Monatsletzten — im Juli waren das zwei Tage Differenz.
2. Wo kein EK hinterlegt ist, wird mit **Durchschnittswerten** gerechnet.
   Herausgerechnet gehört die **AEG-Schrottware**, deren EK tatsächlich 0 ist.

> „Nach dem Urlaub baue ich das ins Cockpit rein, damit wir nicht mehr
> rückrechnen müssen." — D. Schneider, 14.08.2026

---

## 3. Datenlage am 01.09.2026 — warum die Zahl fehlt

### 3.1 Die AMM-Bestandsmails sind seit dem 18.08.2026 abgerissen 🔴

`proWMS@amm-spedition.de` liefert normalerweise **täglich** um ~21:34 Uhr
„Bestand (Elvinci.de GmbH) im Lager AMM vom …". Die letzte Mail kam am
**18.08.2026** (an dem Tag ungewöhnlich um 13:04 / 14:04 / 15:04 Uhr).
Seither: **nichts** — weder im Postfach noch im SharePoint-Ordner
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

### 3.4 Was ich als Anhaltspunkt messen konnte

Aus der jüngsten vorhandenen Bestandsliste, **BESTAND134_20260818_1600.CSV**:

| Status | Bedeutung | Geräte |
|---|---|---|
| QE | klassifiziert, freiverkäuflich | 4.162 |
| VS | Versandpipeline (verkauft, noch im Lager) | 926 |
| AA | auftragsgebunden | 380 |
| **Σ** | **Mengengerüst Reihenwert** | **5.468** |

Keine doppelten Lager-Nrn (5.468 Zeilen = 5.468 eindeutige Nummern).
Zum Vergleich: 30.06.2026 → 5.374 · 28.07.2026 → 5.837 AMM-Zeilen, gegenüber
5.433 bzw. 5.719 Stück in der Reihe. Die AMM-Zeilenzahl trägt das Mengengerüst,
weicht aber je nach Exportzeitpunkt um 1–2 % vom Odoo-KPI ab.

**Eine EK-Summe daraus ist nicht möglich**: Der Microsoft-365-Connector gibt
Tabellen nur bis ~400 Zeilen zurück (der Odoo-Export hat 12.632), die
Einkaufspreise sind darüber nicht auslesbar. Deshalb der Weg über das Skript,
das lokal auf den echten Dateien läuft.

---

## 4. Der fertige Rechenweg: `warenwert_stichtag.py`

Neu in diesem Branch. Das Skript setzt die Definition aus Abschnitt 2 exakt um
und schreibt die Monatsreihe fort. Selbsttest:
`python3 tests/test_warenwert_stichtag.py` (prüft beide Umfänge,
Dubletten-Entfernung, Schrott-Regel, Ø-Fill-Kaskade, Stichtags-Wächter und
Reihen-Fortschreibung gegen von Hand nachgerechnete Sollwerte).

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

Die bestätigte Historie liegt als `warenwert_monatsende.csv` im Repo
(Sep-2025 … Jul-2026, aus `Warenwert zum Monatsende Sep25-Jul26 1.xlsx`).
Hinweis: Der Wert für 31.08.2025 wurde nachträglich von 538.297 € auf
**558.695 €** korrigiert (Abgleich mit der Zahl aus der Buchhaltung,
„3980 Bestand Waren 558.695,00 zum 31.08.2025"); im Repo steht die korrigierte
Fassung.

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

Danach den Befehl aus Abschnitt 4 laufen lassen; die Zahl steht in der Konsole,
in `warenwert_facts_2026-08-31.json` und als neue Zeile in
`warenwert_monatsende.csv`.

**Sauberer für die Zukunft:** Daniels angekündigter Datenbank-Weg
(Monatsletzter, 00:00 Uhr, direkt aus Odoo) macht die Rückrechnung überflüssig
und behebt Unschärfe 1 aus Abschnitt 2.

---

## 6. Wo ich gesucht habe

| Quelle | Ergebnis |
|---|---|
| Repo `lagerkapazit-t` | `lagerwert_pdf.py` + `lagerwert_facts.json` (Methodik Stichtag 29.05.2026), Vertriebs-Cockpit |
| SharePoint `KI-Tools / Lager_Sales Dashboard` | Ordnerstruktur + `_LIESMICH`, `_INFO`-Dateien, Tagesordner AMM/Odoo |
| SharePoint `KI-Tools / ODOO_dashboard` | jüngster Odoo-Export (25.08.2026), Marge-/4-Ebenen-Dashboards |
| OneDrive (Teams-Chatdateien) | `Warenwert zum Monatsende Sep25-Jul26 (1).xlsx`, `Warenwert_30-06-2026.pdf`, `Lagerwert_29-05-2026.pdf` |
| Teams-Chat (Gruppe Finanzen) | Definition + Freigabe der Reihe, 13./14.08.2026 |
| Teams-Chat 1:1 | monatliche Übergabe der Lagerwert-/Warenwert-Auswertungen |
| Outlook | `proWMS@amm-spedition.de` — Bestand/Eingänge/Ausgänge, letzte Mail 18.08.2026 |

Nirgends existiert ein Bestands- oder Odoo-Stand zum 31.08.2026, und für
August 2026 wurde bislang kein Warenwert gerechnet oder kommuniziert.
