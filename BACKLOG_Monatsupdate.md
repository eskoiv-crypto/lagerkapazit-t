# Backlog: Monatliches Self-Service-Update für Schuldner-Dashboard

**Aufgabe (Dustin, 11.05.2026):** Im Dashboard sollen monatlich die aktuellen Portal- und JTL-Exporte direkt hochgeladen werden können, um den jeweils vergangenen Monat zu analysieren — ohne dass jedes Mal ein Python-Skript neu laufen muss.

---

## Anforderungen

1. **Self-Service:** Backoffice-Kollegen (nicht-technisch) müssen selbständig den Upload durchführen können
2. **Browser-only:** kein Server, keine Python-Installation, keine IT-Abhängigkeit
3. **SharePoint-kompatibel:** muss als einzelne HTML-Datei auf SharePoint laufen
4. **Offline-fähig:** Internet-Verbindung darf nicht nötig sein
5. **Monatszyklus:** primärer Use-Case ist "Wie sah der letzte Monat aus?"
6. **Privacy:** Daten verlassen den lokalen Browser nicht

## Erforderliche Uploads (monatlich)

| File | Quelle | Inhalt |
|---|---|---|
| **All-Sold-Export** | Portal (Excel `.xlsx`) | Verkäufe + Rechnungsdatum + Kundennamen |
| **Stock-Received-Export** | Portal (Excel `.xlsx`) | Wareneingänge mit `DateTime` |
| **JTL-Export-Aufträge** | JTL (`.csv`) | Bezahlt-Datum + Zahlungsziel |

## Technische Lösung — Vorschlag

**Architektur:** Browser-only HTML mit eingebetteter JavaScript-Library [SheetJS / xlsx.js](https://github.com/SheetJS/sheetjs) zur Excel-Verarbeitung.

**Workflow im Dashboard:**
1. Drei Drag-and-Drop-Zonen oben im Dashboard
2. Beim Upload werden Dateien im Speicher geparst (SheetJS)
3. Join-Logik (Lager-Nr-Mapping, Cycle-Time-Berechnung) läuft in JavaScript
4. Dashboard rebuilt sich live mit den neuen Daten
5. Optional: Persistenz via `localStorage` für Offline-Zugriff

**Komponenten neu zu bauen:**
- File-Upload-UI mit Drag-and-Drop
- Excel/CSV-Parser in JS (SheetJS einbinden, ~600 KB)
- Portierung der Cycle-Time-Berechnung von Python nach JS
  - Coalesce-Logik für WE-Datum
  - Match-Logik Portal-Sold ↔ Stock-Received (Lager-Nr)
  - Match-Logik All-Sold ↔ JTL (Artikelnummer = Lager-Nr)
  - Zahlungsziel-Überschreitungs-Berechnung
- Status-Anzeige während Verarbeitung
- Validierungs-Hinweise bei fehlerhaften Files

## Alternative — Hybrid-Ansatz (geringerer Aufwand)

1. Kleines Python-Script `update_dashboard.py` mit GUI-File-Picker (z. B. Tkinter)
2. Liest Files ein, generiert HTML wie bisher
3. Backoffice-Mitarbeiter doppelt-klickt das Script
4. Vorteil: ~80 % der Logik bleibt unverändert; nur Datei-Auswahl wird interaktiv
5. Nachteil: Python muss auf dem PC installiert sein

## Datei-Erwartungen / Validierung

| File | Pflichtspalten | Beispielwerte |
|---|---|---|
| All-Sold | `Lager Nr.`, `Date`, `Invoice Date`, `Company`, `Supply Type`, `JTL Selling Price`, `Portal Buying Price` | aus aktuellem Export 1:1 |
| Stock-Received | `Lager ID`, `DateTime`, `Supply Type` | Spaltennamen können variieren — Mapping-Logik einbauen |
| JTL | `Artikelnummer`, `Auftragsdatum`, `Datum Zahlungseingang`, `Zahlungsziel`, `Kunden-Nr`, `Bestell Nr.` | CSV mit `;`-Separator, ISO-8859-1 |

## Edge Cases / Risiken

- **Excel-Dateigrößen:** All-Sold-Master ist ~10 MB, Stock-Received ~7 MB → JS-Parser kann an Limits stoßen
- **Datums-Formate:** deutsche vs. internationale Notation (Portal liefert beides)
- **Encoding JTL:** ISO-8859-1 muss explizit gesetzt werden, sonst Umlaut-Probleme
- **Periode-Definition:** "vergangener Monat" — fix oder rollierend?
- **Coverage-Hochrechnung:** wenn nur 1 Monat hochgeladen wird, ist Stock-Received-Datei vom 01.04.2025–01.04.2026 immer noch nötig → Logik muss klären

## Open Questions

1. Soll das Dashboard primär den **letzten Monat** zeigen oder die **rollierenden 12 Monate** mit Monatsfilter?
2. Werden die hochgeladenen Files **lokal gespeichert** (z. B. localStorage) oder bei jedem Reload neu hochgeladen?
3. Soll es einen **Vergleichs-Modus** geben (z. B. März 2026 vs. Februar 2026)?
4. Wer pflegt die Lieferanten-Klassifizierung ("drehende Ware" = aktuell 9 Lieferanten)?
5. Soll der **Monats-Umsatz-Bericht** (Umsatz_vs_Cash) auch integriert werden, oder bleibt das ein separates PDF?

## Empfohlene Reihenfolge der Umsetzung

1. **Phase 1 (Quick Win, 1–2 Tage):** Hybrid-Ansatz mit `update_dashboard.py` + GUI-Filepicker — funktioniert sofort für 1 Power-User
2. **Phase 2 (1 Woche):** Browser-Self-Service mit SheetJS — funktioniert für alle Backoffice-Kollegen
3. **Phase 3 (2 Wochen):** Vergleichs-Modus + automatische Trend-Analysen Monat-zu-Monat

## Verknüpfte Dateien (Stand 11.05.2026)

- `generate_dashboard.py` — aktuelle Generierung (statisch)
- `compute_we_to_paid_v3_master.py` — Master-Join-Logik
- `we_to_paid_MASTER.csv` — aktueller Datenstand 12 Monate

---

**Status:** Anforderung erfasst, noch nicht in Umsetzung.
**Nächster Schritt bei Wiederaufnahme:** Mit Dustin die Open Questions oben durchgehen, dann Phase 1 oder direkt Phase 2 starten.
