# 🚀 NH5 Lagerkapazitäts-Dashboard — Claude Code Handoff

**Stand:** 2026-04-20
**Dashboard:** 15.313 Zeilen
**Datei:** `elvinci_lagerkapazitaet_dashboard.html`

---

## 📋 INHALTSVERZEICHNIS

1. [Projekt-Übersicht](#1-projekt-übersicht)
2. [Technologie-Stack](#2-technologie-stack)
3. [Kapazitäts-System](#3-kapazitäts-system)
4. [Datenquellen & Upload-Sektionen](#4-datenquellen--upload-sektionen)
5. [DashboardState — Zentrale Datenstruktur](#5-dashboardstate--zentrale-datenstruktur)
6. [Analytics Center — 12 Tabs](#6-analytics-center--12-tabs)
7. [Wichtige JavaScript-Funktionen](#7-wichtige-javascript-funktionen)
8. [Änderungen dieser Session (2026-04-20)](#8-änderungen-dieser-session-2026-04-20)
9. [Bekannte Bugs & Fixes](#9-bekannte-bugs--fixes)
10. [Partner & Team](#10-partner--team)
11. [Backlog & Nächste Schritte](#11-backlog--nächste-schritte)
12. [Claude Code Nutzung](#12-claude-code-nutzung)

---

## 1. PROJEKT-ÜBERSICHT

### Zweck
Standalone HTML-Dashboard für die Lagerkapazitätsüberwachung des NH5-Standorts (Nürnberg) der **elvinci.de GmbH**. B2B-Remarketing von Markenware (Retouren, Überbestände bei Elektrogroßgeräten).

### Unternehmen
- **Firma:** elvinci.de GmbH
- **Standort:** Nürnberg
- **Mitarbeiter:** ~36 Personen
- **Branche:** Remarketing von Elektrogeräten (Retouren, B-Ware)
- **Fulfillment-Partner:** AMM Spedition (primär), GBL Logistics (sekundär)

### Projekt-Historie
- **Entwicklungsstart:** März 2026
- **Sessions:** 20+ Claude-Sessions
- **Aktuelle Version:** 15.313 Zeilen
- **Letzte Änderung:** 2026-04-20 (Angebots-Analyse PRO, Multi-File Upload)

---

## 2. TECHNOLOGIE-STACK

### Frontend
```
- Vanilla JavaScript (ES6+)
- HTML5
- CSS3 (CSS Variables für Dark/Light Mode)
```

### Libraries (CDN)
```javascript
// Chart.js 4.4.1 — Diagramme
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1"></script>

// PapaParse 5.4.1 — CSV-Parsing
<script src="https://cdnjs.cloudflare.com/ajax/libs/PapaParse/5.4.1/papaparse.min.js"></script>

// XLSX.js 0.18.5 — Excel-Parsing
<script src="https://cdn.sheetjs.com/xlsx-0.20.0/package/dist/xlsx.full.min.js"></script>

// jsPDF 2.5.1 + AutoTable — PDF-Export
<script src="https://cdnjs.cloudflare.com/ajax/libs/jspdf/2.5.1/jspdf.umd.min.js"></script>
<script src="https://cdnjs.cloudflare.com/ajax/libs/jspdf-autotable/3.5.28/jspdf.plugin.autotable.min.js"></script>
```

### Datenspeicherung
```javascript
// localStorage Keys:
'elvinci_artikel_faktoren'      // Manuelle Punkt-Faktoren
'elvinci_bestand_snapshots'     // Historische Snapshots
'elvinci_effizienz_history'     // Effizienz-Historie
'elvinci_dark_mode'             // Theme-Präferenz
```

### Keine Backend-Abhängigkeiten
- Alle Daten werden client-seitig verarbeitet
- Dateien werden via Drag & Drop oder File-Input geladen
- Export als Excel/PDF möglich

---

## 3. KAPAZITÄTS-SYSTEM

### Punkte-basierte Kapazität
```
TOTAL NH5 KAPAZITÄT: 10.131 Punkte
├── Lagerkapazität:   7.781 Pkt (dashboardState.kapazitaet)
└── QU-Kapazität:     2.350 Pkt (dashboardState.quKapazitaet)
```

### Kapazitätseinheit
- **1 Punkt ≈ 1 Waschmaschine (Standardgerät)**
- Side-by-Side Kühlschrank = 4.0 Punkte
- Staubsauger = 0.1 Punkte
- Durchschnitt: 0.72 Punkte pro Gerät

### Hardcoded Defaults (Zeile ~5080)
```javascript
const DEFAULT_SETTINGS = {
    flaeche: 2766,           // qm Lagerfläche
    palettenProQm: 0.565,    // Paletten/qm
    bodenflaecheKap: 6251,   // Punkte Bodenfläche
    regaleKap: 1530,         // Punkte Regale
    quWaKap: 2350,           // Punkte QU/WA
    effizienzZiel: 470       // Geräte/Tag
};
```

### Punktefaktoren (artikelFaktoren, Zeile ~5355)
```javascript
// 122 Keywords definiert
// Logik: getArtikelFaktorLocal(bezeichner, artikelnummer)
// Priorität: 1. manualFaktoren, 2. Set-Spezial, 3. Exakt, 4. Teil-Match, 5. Lookup, 6. Standard 1.0

// Beispiele:
"side-by-side": 4.0,
"gefriertruhe": 4.0,
"kühl-gefrier": 2.0,
"waschmaschine": 1.0,
"wäschetrockner": 1.0,
"staubsauger": 0.1,
"set": 0.5,
"monitor": 0.05
```

---

## 4. DATENQUELLEN & UPLOAD-SEKTIONEN

### Upload-Bereiche im Dashboard
| # | Sektion | Dateien | Farbe | Beschreibung |
|---|---------|---------|-------|--------------|
| 1️⃣ | STAMMDATEN | BESTAND CSV | 🟢 Grün | AMM BESTAND (Lagernummern, Status) |
| 2️⃣ | PLANUNG | WE PIPELINE, FULFILMENT | 🔵 Cyan | Wareneingänge, Versandplanung |
| 3️⃣ | VALIDIERUNG | AUFTRAG_STATUS, PLANNER | 🟣 Purple | Auftrags-Status, Teams Planner |
| 4️⃣ | PORTAL | JTL EXPORT, ALL SOLD, STOCK ANALYSIS | 🟠 Orange | JTL-Verkaufsdaten, Portal-Exporte |
| 5️⃣ | ANALYSE PRO | Warenwert | 🟠 Orange | Passwortgeschützt: `elvinci` |

### Datei-Erkennung (detectFileType, Zeile ~4680)
```javascript
function detectFileType(filename) {
    const lower = filename.toLowerCase();
    
    if (/bestand/i.test(lower)) return 'bestand';
    if (/^we[_-]/i.test(lower) && lower.endsWith('.csv')) return 'we-ist';
    if (/^wa[_-]/i.test(lower) && lower.endsWith('.csv')) return 'wa-ist';
    if (/wareneingang|we.?pipe/i.test(lower)) return 'we-pipe';
    if (/fulfilment|fulfillment|wa.?pipe/i.test(lower)) return 'wa-pipe';
    if (/status|auftrag.*status/i.test(lower)) return 'auftrag-status';
    if (/planner|aufgaben/i.test(lower)) return 'planner';
    
    // NEU (2026-04-20): Angebots-Dateien
    if (/^paletten[_-]|angebot|offer|quotation/i.test(lower) && 
        (lower.endsWith('.xlsx') || lower.endsWith('.xls') || lower.endsWith('.csv'))) {
        return 'angebot';
    }
    
    return null;
}
```

### BESTAND CSV Spalten (AMM Export)
```
Palette (=Lagernummer), Artikel, Bezeichner, Charge, LgPlatz, 
Standort, Menge, WE-Datum, Bestellnummer, Status, Auftrag
```

### Stock-Analysis Spalten (Portal Export)
```
Buying_Price, Selling_Price, Online_Price, article_number, brand,
datetime_upload, final_grade, grade_points, lager_number, model,
price_percent, product_group, product_life_days, status, supply_id,
supply_type, usage
```

### All-Sold Spalten (Portal Export)
```
Portal Buying Price, Portal Selling Price, Profit, Lager Nr.,
Order Nr., Article, Brand, Product Group, Date, Company, Sold By,
Final Grade, Supply, Supply Type, JTL Selling Price, Invoice Paid
```

---

## 5. DASHBOARDSTATE — ZENTRALE DATENSTRUKTUR

```javascript
const dashboardState = {
    // === KAPAZITÄT ===
    kapazitaet: 7781,           // Lager-Punkte
    quKapazitaet: 2350,         // QU-Punkte
    
    // === BESTAND ===
    bestandLoaded: false,
    bestandLager: 0,            // Punkte Lager
    bestandKomm: 0,             // Punkte Versandfläche
    bestandGesamt: 0,           // Lager + Versand
    bestandLagerStueck: 0,      // Stückzahl Lager
    bestandKommStueck: 0,       // Stückzahl Versand
    bestandRaw: [],             // Rohdaten für Validierung
    bestandAuftragMap: {},      // Auftrag → {count, status, vsCount, aaCount, geraete[]}
    avgPktProGeraet: 0.72,      // Ø Punkte pro Gerät
    
    // === PIPELINE WE/WA ===
    weLoaded: false,
    waLoaded: false,
    pipelineWE: {},             // Datum → Stückzahl
    pipelineWA: {},             // Datum → Stückzahl
    
    // === FULFILLMENT ===
    fulfillmentDataMap: {},     // AuftragNr → {versandDatum, versandart, kunde, ...}
    kommissioniertListe: [],    // Sortierte Auftragsliste
    quBereit: 0,                // QU ohne Termin (Blockierer)
    
    // === STOCK-ANALYSIS (Portal) ===
    stockAnalysisLoaded: false,
    stockAnalysisData: {},      // LagerNr → {ek, vk, pg, brand, status, isReserved, isAvailable, ...}
    stockAnalysisRaw: [],       // Array für Analysen
    stockAnalysisCount: 0,
    stockTotalEK: 0,
    stockTotalVK: 0,
    stockAvgLifeDays: 0,
    stockLageralterBuckets: {}, // 0-30, 31-90, 91-180, 180+
    
    // NEU (2026-04-20): Verfügbarkeits-Statistiken
    stockReservedCount: 0,      // Status A/M = reserviert
    stockAvailableCount: 0,     // Ohne A/M = frei
    stockReservedEK: 0,
    stockReservedVK: 0,
    stockAvailableEK: 0,
    stockAvailableVK: 0,
    stockPgStats: {},           // WG → {lagerCount, availableCount, reservedCount, ekSum, vkSum, ...}
    stockBrandStats: {},        // Marke → {lagerCount, availableCount, reservedCount, ...}
    
    // === ALL-SOLD (Portal) ===
    allSoldLoaded: false,
    allSoldData: [],            // Array aller Verkäufe
    allSoldCount: 0,
    allSoldProfit: 0,
    allSoldAvgProfit: 0,
    allSoldTotalEK: 0,
    allSoldTotalVK: 0,
    
    // Erweiterte Statistiken
    soldPgStats: {},            // WG → {count, profit, vkSum, ekSum, ...}
    soldBrandStats: {},         // Marke → {count, profit, vkSum, ...}
    soldByStats: {},            // Verkäufer → {count, profit, umsatz}
    kundenStats: {},            // Kunde → {umsatz, profit, count, ordersCount}
    kundenWgStats: {},          // Kunde → WG → {count, umsatz}
    lieferantenStats: {},       // Supply Type → {count, profit, ...}
    margeDistribution: {},      // Marge-Bucket → Count
    dailySales: {},             // Datum → {count, profit, vk, umsatz}
    monthlyRevenue: {},         // YYYY-MM → {umsatz, profit, count}
    
    // === JTL ===
    artikelLookup: {},          // ArtNr → {faktor, bezeichnung}
    artikelLookupCount: 0,
    
    // === ZONEN ===
    zonen: {},                  // Zone → Punkte (Top 10)
    zonenStueck: {},            // Zone → Stückzahl
    
    // === DATENQUALITÄT ===
    diskrepanzen: [],           // Cross-Referenz-Fehler
    
    // === ANGEBOTS-ANALYSE (NEU 2026-04-20) ===
    angebotAnalyseResults: []   // Analyse-Ergebnisse
};
```

---

## 6. ANALYTICS CENTER — 12 TABS

| Tab | ID | Icon | Funktion | Datenquelle |
|-----|----|------|----------|-------------|
| Übersicht | `uebersicht` | 📈 | KPIs, Lageralter, Marge, Tortendiagramme | Stock + Sold |
| Datenqualität | `datenqualitaet` | 🔍 | Cross-Referenz-Validierung | Alle |
| Verkäufer | `verkaeufer` | 👤 | Sales Team Performance | All-Sold |
| Kunden | `kunden` | 🏢 | Ranking mit %-Anteilen | All-Sold |
| Kunden×WG | `kundenmatrix` | 📊 | Heatmap, Best-Fit | All-Sold |
| Warengruppen | `produktgruppen` | 🏷️ | Lager/Frei/Reserv./Verkauft | Stock + Sold |
| Marken | `brands` | 🏭 | Lager/Frei/Reserv./Verkauft | Stock + Sold |
| Lieferanten | `lieferanten` | 📦 | Supply Type Analyse | All-Sold |
| Dead Stock | `deadstock` | 💀 | Artikel >180d | Stock-Analysis |
| Verkaufspriorität | `potenzial` | 🎯 | Score-System | Stock + Sold |
| Top-Seller | `topseller` | 🏆 | Bestseller | All-Sold |
| **Angebots-Analyse** | `angebotsanalyse` | 💼 | **NEU** Lieferanten-Angebote bewerten | Stock + Sold |

### NEU: Angebots-Analyse Tab (2026-04-20)

**Funktionen:**
- Upload von Lieferanten-Angeboten (Excel/CSV)
- Automatisches WG-/Marken-Matching
- Max-EK Berechnung (bei 45% Ziel-Marge)
- Ø Verkaufszeit Prognose
- Top-Kunden Matching
- Ampel-System: 🟢 Kaufen | 🟡 Verhandeln | 🔴 Ablehnen
- Excel-Export der Analyse

**Verfügbar wenn:** `stockAnalysisLoaded && allSoldLoaded`

**Erkannte Datei-Muster:**
- `Paletten_*.xlsx`
- `Angebot_*.xlsx`
- `Offer_*.csv`
- `Quotation_*.xlsx`

---

## 7. WICHTIGE JAVASCRIPT-FUNKTIONEN

### Daten-Handler (Zeile ~13000+)
```javascript
// BESTAND CSV Handler
handleFileUpload(input, 'bestand')  // Zeile ~13180
// Parst: Palette, Artikel, Bezeichner, LgPlatz, Status, Auftrag

// STOCK-ANALYSIS Handler
handleFileUpload(input, 'stock-analysis')  // Zeile ~13500
// Parst: lager_number, Buying_Price, Selling_Price, product_group, brand

// ALL-SOLD Handler
handleFileUpload(input, 'all-sold')  // Zeile ~13700
// Parst: alle Verkaufsdaten mit Kunden, Verkäufer, Profit
```

### Berechnungs-Funktionen
```javascript
updateStats()                    // Zeile ~8200 - Hauptkarten aktualisieren
updateGauge()                    // Auslastungs-Gauge
renderForecastTable()            // 14-Tage-Prognose
combineAndRenderAuftragData()    // Zeile ~10600 - Auftrags-Kombination
runDataValidation()              // Zeile ~6350 - Datenqualitäts-Checks
```

### Analyse-Funktionen
```javascript
updateAnalyseProPanel()          // Zeile ~5750 - Analyse-Center aktualisieren
updateAnalyseKPIs()              // KPIs berechnen
updateKundenTab()                // Zeile ~6050
updateKundenMatrix()             // Zeile ~6200
updateLieferantenTab()           // Zeile ~7100
updateProduktgruppenTable()      // Zeile ~6950
updateBrandsTable()              // Zeile ~7300
updateDeadStockTab()             // Zeile ~5850
updatePotenzialTab()             // Zeile ~5920
updateVerfuegbarkeitsAnzeige()   // Zeile ~6900 - Frei/Reserviert Stats
updateVerfuegbarkeitsPieCharts() // Tortendiagramme
```

### NEU: Angebots-Analyse Funktionen (Zeile ~7640)
```javascript
checkAngebotsAnalyseAvailability()  // Prüft ob Feature verfügbar
processMultipleAngebotFiles(files)  // Multi-File Support
processAngebotFile(file)            // Einzeldatei
analyzeAngebot(data, fileName)      // Hauptanalyse
renderAngebotResults()              // UI rendern
sortAngebotResults()                // Sortierung
exportAngebotAnalyse()              // Excel-Export
```

### Utility-Funktionen
```javascript
getArtikelFaktorLocal(bezeichner, artikelnummer)  // Punkte-Faktor ermitteln
normalizeAuftragNr(auftragNr)                     // AU-Prefix + Trimming
showToast(type, title, message)                   // Benachrichtigungen
formatCurrency(value)                             // €-Formatierung
setEl(id, value)                                  // DOM-Helper
```

---

## 8. ÄNDERUNGEN DIESER SESSION (2026-04-20)

### A) Angebots-Analyse PRO Feature
**Implementiert:**
- Neuer Tab "💼 Angebots-Analyse" im Analytics Center
- Upload-Zone für Lieferanten-Angebote (Drag & Drop)
- Automatische Spalten-Erkennung (Bezeichnung, Menge, VK, Artikelgruppe)
- WG-Mapping (Angebots-Format → Portal-Format)
- Marken-Erkennung aus Bezeichnung
- Historisches Matching mit All-Sold Daten
- Kalkulation: Max-EK, Marge-Prognose, Verkaufsgeschwindigkeit
- Ampel-System mit Score-basierter Empfehlung
- Excel-Export der Analyse

**Neue Funktionen:**
```javascript
checkAngebotsAnalyseAvailability()
processMultipleAngebotFiles(files)
processAngebotFile(file)
analyzeAngebot(data, fileName)
renderAngebotResults()
sortAngebotResults()
exportAngebotAnalyse()
```

### B) Multi-File Angebots-Upload
**Problem:** Mehrere Paletten-Dateien gleichzeitig droppen führte zu Fehlermeldungen
**Lösung:** 
- `detectFileType()` um Angebots-Muster erweitert
- Drop-Handler sammelt alle Angebots-Dateien
- `processMultipleAngebotFiles()` kombiniert alle zu einem Sammel-Angebot
- Automatischer Tab-Wechsel zur Angebots-Analyse

**Code-Änderungen:**
```javascript
// detectFileType() erweitert (Zeile ~4680):
if (/^paletten[_-]|angebot|offer|quotation/i.test(lower) && 
    (lower.endsWith('.xlsx') || lower.endsWith('.xls') || lower.endsWith('.csv'))) {
    return 'angebot';
}

// Drop-Handler (Zeile ~4650):
// Sammelt alle angebotFiles[] und ruft processMultipleAngebotFiles() auf
```

### C) Verfügbarkeits-Filter (aus vorheriger Session)
- Status A/M = reserviert (in Angebot)
- Ohne A/M = frei verfügbar
- Neue dashboardState Properties: stockReservedCount, stockAvailableCount, etc.
- Neue Spalten in WG-/Marken-Tabs: Lager | Frei | Reserv.
- Zwei Tortendiagramme im Übersicht-Tab

---

## 9. BEKANNTE BUGS & FIXES

### Behoben (letzte Sessions)
| Datum | Problem | Fix | Zeile |
|-------|---------|-----|-------|
| 2026-04-20 | Paletten_*.xlsx nicht erkannt | detectFileType erweitert | ~4680 |
| 2026-04-17 | JTL Label "22.271 Aufträge" falsch | Label → "Artikelstamm" | ~3330 |
| 2026-04-17 | "Stk bereit" zeigte Blockierer | vsReadyCount Berechnung | ~8200 |
| 2026-04-17 | BESTAND Status nur 1x gespeichert | vsCount/aaCount separat | ~13250 |
| 2026-04-14 | Syntax Error duplicate const | EFFIZIENZ_STORAGE_KEY entfernt | ~3260 |
| 2026-04-14 | FULFILMENT Matching fehlerhaft | normalizeAuftragNr() | ~10650 |

### Offen / Bekannt
- [ ] CDN-Bibliotheken lokal einbetten für Offline-Modus
- [ ] Chart-Rendering manchmal verzögert bei großen Datenmengen

---

## 10. PARTNER & TEAM

### Externe Partner
| Partner | Kontakte | Rolle | Datenquellen |
|---------|----------|-------|--------------|
| AMM Spedition | Stefan Dehm, Björn Stadler | Primary Fulfillment | BESTAND, WE-IST, WA-IST (orange Ordner) |
| GBL Logistics | Sebastian Reidl | Secondary Fulfillment | WE > WA Priorität |
| Electrolux | Aneta Szpulak | Lieferant | — |

### elvinci Team
| Bereich | Personen |
|---------|----------|
| Backoffice | Janna, Igor, Mirko, Siyad, Johannes, Nikoloz, Inesa |
| Sales | Nikos Celaj, Nikoloz Artiukhov, Siyad Mutaschar |
| Leadership | Konstantinos Vasiadis (CEO) |
| Dashboard-Verantwortlicher | Dustin Eskofier |

---

## 11. BACKLOG & NÄCHSTE SCHRITTE

### Priorisiert
- [ ] **CDN-Bibliotheken lokal einbetten** (Offline-Modus)
- [ ] **Automatischer BESTAND↔Portal Abgleich** (IT-Übergabe Report bereits erstellt)
- [ ] **SharePoint-Integration** Ziel: `elvinci.de → Backoffice! → Spedition+Logistik → AMM DASHBOARD`

### Nice-to-Have
- [ ] Gewinn-Prognose basierend auf Pipeline
- [ ] Lagerumschlag-Analyse (product_life_days tiefere Analyse)
- [ ] Mobile-optimierte Ansicht
- [ ] Automatischer Daten-Refresh (bei SharePoint-Integration)

### Dokumentation
- [x] PDF User Manual (bereits erstellt, ReportLab)
- [x] Claude Code Handoff (dieses Dokument)
- [ ] Video-Tutorial für Endanwender

---

## 12. CLAUDE CODE NUTZUNG

### Projekt-Setup
```bash
# Dashboard öffnen
code /path/to/elvinci_lagerkapazitaet_dashboard.html

# Oder mit Claude Code:
claude code /path/to/elvinci_lagerkapazitaet_dashboard.html
```

### Wichtige Zeilenbereiche
| Bereich | Zeilen | Beschreibung |
|---------|--------|--------------|
| CSS Styles | 1-2800 | Alle Styles inkl. Dark/Light Mode |
| HTML Structure | 2800-4900 | Dashboard-Layout, Tabs, Modals |
| artikelFaktoren | ~5355 | 122 Punkte-Faktoren |
| DEFAULT_SETTINGS | ~5080 | Kapazitäts-Konstanten |
| dashboardState | ~5000 | Zentrale Datenvariablen |
| Analytics Functions | 5700-7900 | Alle Tab-Update-Funktionen |
| **Angebots-Analyse** | ~7640-8100 | **NEU** Upload + Analyse |
| updateStats | ~8200 | Hauptkarten-Berechnung |
| combineAndRenderAuftragData | ~10600 | Auftrags-Kombination |
| detectFileType | ~4680 | Datei-Erkennung |
| Drop-Handler | ~4650 | Multi-File Upload |
| BESTAND Handler | ~13180 | CSV-Parsing |
| STOCK-ANALYSIS Handler | ~13500 | Excel-Parsing |
| ALL-SOLD Handler | ~13700 | Excel-Parsing |

### Suchen nach Funktionen
```bash
# Funktion finden
grep -n "function analyzeAngebot" elvinci_lagerkapazitaet_dashboard.html

# Alle dashboardState Zuweisungen
grep -n "dashboardState\." elvinci_lagerkapazitaet_dashboard.html | head -50
```

### Admin-Zugang
```
Passwort: elvinci
```

### Test-Workflow
1. Dashboard in Browser öffnen
2. BESTAND CSV hochladen (Stammdaten)
3. Stock-Analysis + All-Sold hochladen (Portal)
4. Angebots-Analyse testen mit Paletten_*.xlsx
5. F12 Console für Fehler prüfen

---

## ANHANG: DATEIEN

```
Projekt-Struktur:
├── elvinci_lagerkapazitaet_dashboard.html    (15.313 Zeilen, Haupt-Dashboard)
├── CLAUDE_CODE_HANDOFF_2026-04-20.md         (diese Datei)
├── claude_code_handoff/
│   ├── elvinci_lagerkapazitaet_dashboard_v2026-04-20.html
│   ├── HANDOFF_NH5_DASHBOARD.md              (älteres Handoff)
│   └── CLAUDE_CODE_CONTEXT.json              (strukturierte Daten)
└── IT_Abgleich_BESTAND_Portal_2026-04-20.xlsx (IT-Report)
```

---

**Erstellt:** 2026-04-20
**Autor:** Claude (Anthropic)
**Projekt:** elvinci.de NH5 Lagerkapazitäts-Dashboard
**Kontakt:** Dustin Eskofier (Backoffice & Fulfillment)
