# Warenwert zum Stichtag 31.08.2026

**Status: gerechnet.** Die beiden fehlenden Exporte wurden am 01.09.2026
nachgeliefert; der Wert liegt als Einseiter `Warenwert_31-08-2026.pdf` vor
(bleibt lokal, siehe Hinweis unten).

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
| Stichtag | 31.08.2026 |
| Mengengerüst | `BESTAND134_20260831_1700.CSV` (AMM, Stand 31.08.2026 17:00) |
| Preise | `LosSerie (stock.lot)`-Export, gezogen am 01.09.2026 |
| Ergebnis | `Warenwert_31-08-2026.pdf` + `warenwert_facts_2026-08-31.json` — **lokal**, nicht im Repo |
| Zweite Sicht | `--umfang freiverkaeuflich` (nur AMM-Status QE) als eigener Einseiter |

Der Reihenwert ist damit fortgeschrieben. Vorbehalte und Gegenproben stehen in
Abschnitt 3.

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

## 3. Belastbarkeit und Vorbehalte

### 3.1 Gegenproben zum Lauf vom 01.09.2026

| Prüfung | Ergebnis |
|---|---|
| Doppelte Lager-Nrn im AMM-Bestand | keine |
| Anteil Geräte mit belegtem Einkaufspreis aus Odoo | rund 88 % |
| Rest ohne Preis | teils in Odoo ohne EK, überwiegend gar nicht in Odoo geführt (Klassifizierungs-Rückstand: Einbaugeräte, Mikrowellen, Set-Artikel) |
| Anteil des Ø-geschätzten Werts am Gesamtwert | rund 13 % (engere QE-Sicht: rund 10 %) |
| Gegenprobe gegen Odoos eigenen Vorrat | Odoo führt etwas weniger Lose als die AMM-Liste; die Differenz erklärt sich aus dem Klassifizierungs-Rückstand einerseits und Zugängen nach dem Stichtag andererseits |

Die Ø-Schätzung ist der einzige echte Unsicherheitsblock. Bei ±10 % darauf
bewegt sich der Gesamtwert um gut ein Prozent.

### 3.2 Zwei offene Punkte

1. **Stichtagsschärfe.** Die Bestandsliste ist vom 31.08. 17:00 Uhr, nicht vom
   Monatsletzten 24:00 Uhr; der Preis-Export stammt vom 01.09. Der angekündigte
   Datenbank-Weg (Monatsletzter, 00:00 Uhr) räumt das aus.
2. **Schrottware.** Die Korrektur „echter EK 0 €, kein Ø-Fill" greift im
   aktuellen Export **nicht**: weder Lieferant, Lieferantentyp,
   Produktkategorie noch Produktbezeichnung enthalten eine Schrott-Kennzeichnung,
   und die AMM-Bezeichner ebenso wenig. Solange es kein Kennzeichen gibt, ist
   der Ø-Fill für diese Ware zu hoch. Nötig ist ein Merkmal in Odoo (oder eine
   Liste der betroffenen Lieferantentypen), dann greift `--ek0-muster`.

### 3.3 Der Datenfluss ist unterbrochen 🔴

`proWMS@amm-spedition.de` liefert normalerweise **täglich** um ~21:34 Uhr
„Bestand (Elvinci.de GmbH) im Lager AMM vom …". Die letzte automatische Mail kam
am **18.08.2026**; seither weder im Postfach noch im SharePoint-Ordner
`01 TÄGLICH HOCHLADEN / 02 AMM BESTAND134` etwas Neues. Auch „Eingänge",
„Ausgänge" und „Auftragsstand" enden dort. Die Liste zum Stichtag musste
deshalb von Hand beschafft werden.

Das ist unabhängig vom Warenwert zu klären — dem Cockpit fehlen seit zwei
Wochen die täglichen Bestandsdaten.

### 3.4 Das Portal ist tot

Laut `_LIESMICH - ORDNERSTRUKTUR.txt` (Stand 24.07.2026) ist das Portal seit
**03.07.2026** endgültig abgeschaltet; die Exporte vom 02.07.2026
(Stock-Analysis, All-Sold) sind der Endstand. Sie bleiben über
`--stock-analysis` als **EK-Quelle für Altbestand** nutzbar und könnten einen
Teil der heute unbepreisten Geräte abdecken — im Lauf vom 01.09.2026 wurden sie
nicht herangezogen.

## 4. Der Rechenweg: `warenwert_stichtag.py`

Setzt die Definition aus Abschnitt 2 um und schreibt die Monatsreihe fort.
Selbsttest: `python3 tests/test_warenwert_stichtag.py` — prüft beide Umfänge,
Dubletten-Entfernung, Schrott-Regel, Ø-Fill-Kaskade, Stichtags-Wächter und
Reihen-Fortschreibung gegen von Hand nachgerechnete Sollwerte (synthetische
Testdaten, keine echten Bestände).

```bash
python3 warenwert_stichtag.py \
    --stichtag 2026-08-31 \
    --bestand "data/amm/BESTAND134_20260831_1700.CSV" \
    --odoo    "data/odoo/LosSerie (stock.lot)_2026-09-01.xlsx" \
    --stock-analysis "data/elvinci/Stock-Analysis-2026-07-02.xlsx" \
    --serie   warenwert_monatsende.csv \
    --json    warenwert_facts_2026-08-31.json

python3 warenwert_pdf.py --json warenwert_facts_2026-08-31.json \
    --serie warenwert_monatsende.csv --out Warenwert_31-08-2026.pdf
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

## 5. Offen

1. **Tägliche AMM-Zustellung wieder in Gang bringen** (siehe 3.3) — ohne sie
   muss die Bestandsliste jeden Monat von Hand angefordert werden.
2. **Schrottware kennzeichnen** (siehe 3.2), damit der Ø-Fill sie nicht
   überzeichnet.
3. **Datenbank-Weg** für den Monatsletzten 00:00 Uhr — macht die manuelle
   Beschaffung und die Stichtags-Unschärfe überflüssig.

---

## 6. Wo gesucht wurde

Repo `lagerkapazit-t` · SharePoint `KI-Tools / Lager_Sales Dashboard`
(inkl. `_LIESMICH` und den `_INFO`-Dateien der Tagesordner) · SharePoint
`KI-Tools / ODOO_dashboard` · OneDrive Teams-Chatdateien · die Teams-Threads zur
Monatsreihe · Outlook (`proWMS@amm-spedition.de`).

In keiner dieser Quellen lag ein Bestands- oder Odoo-Stand zum 31.08.2026; für
August 2026 war bis dahin kein Warenwert gerechnet oder kommuniziert. Beide
Exporte wurden am 01.09.2026 manuell nachgeliefert.
