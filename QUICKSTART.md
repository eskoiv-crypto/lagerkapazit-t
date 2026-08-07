# NH5 Dashboard — Quickstart

**Stand:** 2026-04-27 · **147 Tests grün** · **19.317 Zeilen** · 18 Sprints + 6 User-Reports

---

## 🚀 Sofort loslegen — drei Wege

### Weg 1: Desktop-Shortcut (täglich nutzen)
Auf deinem Desktop liegt **`NH5 Dashboard`** — Doppelklick öffnet das Dashboard im Default-Browser. Kein Install, kein Server. Funktioniert offline (CDN-Bibliotheken müssen einmal pro Tag online geladen werden).

### Weg 2: Direkt im Explorer
```
C:\Users\DustinEskofier\Projekt\lagerkapazität\elvinci_lagerkapazitaet_dashboard_v2026-04-20.html
```

### Weg 3: Lokaler Server (für OAuth-Features)
PowerShell oder CMD öffnen:
```bash
cd 'C:\Users\DustinEskofier\Projekt\lagerkapazität'
node serve.js
```
Dann im Browser: **http://localhost:8080/elvinci_lagerkapazitaet_dashboard_v2026-04-20.html**

Server brauchst du nur wenn:
- 🔌 SharePoint Auto-Sync aktiv werden soll
- 🪪 Azure AD Login gewünscht ist
- 🤖 Chrome Prompt API LLM genutzt werden soll

---

## 🎛️ Department-Sichten (NEU 2026-04-27)

Sticky Top-Leiste mit 5 Abteilungs-Sichten — Wahl persistiert in localStorage:

```
[🌐 Alle] [🏭 Lager] [📦 Auftragsabwicklung] [💰 Sales] [💵 Finance]
```

| Sicht | Zeigt |
|-------|-------|
| 🌐 **Alle** | Vollbild — alle Sections sichtbar |
| 🏭 **Lager** | Füllstand, Auslastung, Prognose, Anomalie-Radar, 2-Wochen-Forecast |
| 📦 **Auftragsabwicklung** | Sidebar + Datenqualität + Kommissioniert-Liste mit Suche |
| 💰 **Sales** | Verkaufsanalyse PRO (Verkäufer, Kunden, Top-Seller, Angebots-Analyse) |
| 💵 **Finance** | Verkaufsanalyse PRO (Warengruppen, Marken, Lieferanten, Dead Stock) |

---

## 🔍 Suche in Auftragsabwicklung (NEU 2026-04-27)

Über der Filter-Bar im Kommissioniert-Panel:

```
🔍 Suche: Kunde oder Auftragsnummer (z.B. AU2026..., Müller GmbH)  [✕]  3 Treffer
```

**Matcht 4 Felder gleichzeitig:** Auftragsnummer, Kunde, Land, Spediteur (case-insensitive).
**Schnittmenge mit Filter-Reitern:** Suche "müller" + Reiter "QU" zeigt nur Müller-Aufträge im Status QU.

---

## 🔑 Admin-Zugang

| Zweck | Zugang |
|-------|--------|
| Standard-Dashboard | Kein Login nötig — direkt nutzen |
| Settings & Analyse PRO | Passwort: **`elvinci2026`** |
| Azure-AD-Login | Erst nach IT-Setup verfügbar |

---

## 📥 Daten-Upload — die 5 Sektionen

| # | Sektion | Datei-Typ | Klassifizierung |
|---|---------|-----------|-----------------|
| 1️⃣ | STAMMDATEN | `BESTAND*.csv` (AMM) | 🟢 grün |
| 2️⃣ | PLANUNG | `Wareneingang*.xlsx`, `Fulfilment*.xlsx` | 🟡 gelb |
| 3️⃣ | VALIDIERUNG | `Auftrag_Status*.xlsx`, `Planner*.xlsx` | 🟡 gelb |
| 4️⃣ | PORTAL | `JTL_Export*.csv`, `All_Sold*.xlsx`, `Stock_Analysis*.xlsx` | 🔴 rot |
| 5️⃣ | ANALYSE PRO | `Paletten_*.xlsx` (Lieferanten-Angebot) | 🟡 gelb |

**Drag & Drop:** alle Dateien können einfach ins Browserfenster gezogen werden — Upload-Queue verarbeitet sie seriell.

**Versanddatum-Formate die jetzt funktionieren** (Sprint 7+ User-Report):
- `23.04.2026` ✅
- `28. Apr` ✅ (Jahr aus Heuristik)
- `28.04 - 30.04` ✅ als Range
- `Warte auf Rückmeldung` ✅ als Text-Marker

---

## 🎯 Power-Features

| Feature | Wo | Sprint |
|---------|-----|--------|
| 🔍 Natural-Language-Query | Datenqualität-Tab → Query-Bar | 6.9 |
| 📊 Anomalie-Radar | Datenqualität-Tab → Anomaly-Card | 6.2 |
| 💼 Angebots-Analyse v2 (Pareto + Mail-Drafts) | Analytics → Angebots-Analyse | 6.10 |
| 🛡️ PII-Maskierung Toggle | Settings → Compliance | 6.8 |
| 📋 Audit-Log Viewer | Settings → Compliance → "Audit-Log anzeigen" | 6.8 |
| 🪪 User-Badge | Oben rechts | 6.7 |
| 🎛️ Department-Switcher | Sticky-Leiste oben | User-Report |
| 🔍 Auftrags-Suche | Über Kommissioniert-Filter | User-Report |

### NLQ-Beispiele
```
siemens älter 180 tage
marge unter 10%
wäschetrockner status QU
ek > 200 lagertage > 90
```

### Mail-Drafts (Lieferanten-Angebote)
Nach Upload eines `Paletten_*.xlsx`:
- 📧 **Lieferant: Gegenangebot** — Top-25 Items mit Max-EK-Preisen
- 📧 **Lieferant: Annahme (🟢-Items)** — nur Empfehlung KAUFEN
- 📧 **Lieferant: Ablehnung** — nur Empfehlung ABLEHNEN
- 📧 **Customer-Match** — pro Top-Kunden ein eigener Draft

### Lifecycle-Anomalien (NEU 2026-04-27)
Im Datenqualität-Tab automatisch sichtbar:
- ⏰ **Alter Auftrag ohne Termin** — >14 Tage in Pipeline ohne Versanddatum
- 📋 **Versand bei AMM nicht angemeldet** — Termin steht aber Spalte I leer
- 🐢 **Lange Lead-Time** — Anmeldung→Versand >21 Tage

---

## 🧪 Tests laufen lassen

### PowerShell
```powershell
cd 'C:\Users\DustinEskofier\Projekt\lagerkapazität'
npm test               # 147 Tests, ~2 Min
npm run test:headed    # mit sichtbarem Chrome-Fenster
npm run test:ui        # interaktiver Mode (zum Debuggen)
npm run test:report    # nach Lauf: HTML-Report öffnen
```

### CMD (mit Auto-PATH-Fix)
```cmd
cd C:\Users\DustinEskofier\Projekt\lagerkapazität
run-tests.cmd               # alle Tests
run-tests.cmd headed        # mit Browser
run-tests.cmd ui            # interaktiv
run-tests.cmd report        # HTML-Report
```

Vor jeder Änderung am Dashboard solltest du Tests laufen lassen — gibt sofort Sicherheit dass nichts gebrochen ist.

---

## 📚 Wichtige Dateien

| Datei | Inhalt |
|-------|--------|
| `elvinci_lagerkapazitaet_dashboard_v2026-04-20.html` | **Das Dashboard** — 19.317 Zeilen Single-File |
| `MASTER_TODO_2026-04-20.md` | Sprint-Plan, Architektur, alle 10X-Vorschläge |
| `CLAUDE_CODE_HANDOFF_2026-04-20.md` | Ursprüngliches Manifest |
| `TEST_READINESS_REPORT.md` | Diagnose-Report vom statischen Pre-Check |
| **`QUICKSTART.md`** | **Diese Datei** |
| `tests/` | 16 Spec-Files mit 147 Tests |
| `serve.js` | Lokaler HTTP-Server für OAuth-Workflows |
| `run-tests.cmd` | CMD-tauglicher Test-Runner mit Auto-PATH-Fix |
| `package.json` | npm scripts |

---

## 🛠️ Updates & Sync

```powershell
cd 'C:\Users\DustinEskofier\Projekt\lagerkapazität'

# Lokale Änderungen prüfen
git status

# Aktualisierungen aus GitHub holen
git pull

# Lokale Änderungen sichern
git add .
git commit -m "deine Beschreibung"
git push
```

GitHub-Repo: **https://github.com/eskoiv-crypto/lagerkapazit-t**

---

## 🆘 Wenn was nicht läuft

| Problem | Lösung |
|---------|--------|
| Dashboard öffnet leer | Browser-Console (F12) öffnen — meist CDN offline. Internet prüfen. |
| Upload zeigt ❌ Fehler | Klick auf 🔁 **Erneut versuchen** im Toast |
| "Geplant: 0" trotz Aufträge | Sollte 2026-04-27 gefixt sein. F5 drücken. Wenn weiterhin: `npm test -- tests/upload.spec.js` und Output schicken |
| Kommissioniert-Liste zeigt zu wenig | Suchfeld leeren mit ✕, Filter-Reiter auf "Alle" |
| `npm` not found in CMD | `run-tests.cmd` benutzen statt `npm test` |
| Tests rot nach Code-Änderung | `npm run test:report` öffnet HTML-Report mit Trace + Screenshot |
| Settings-Modal lässt sich nicht öffnen | Passwort: `elvinci2026` (oder ESC für Schließen) |

Bei tieferen Problemen: GitHub-Issue oder Output von `npm test` an mich schicken.

---

## 🆕 Was seit dem letzten Quickstart neu ist (User-Reports 2026-04-27)

| Bug-Report | Status |
|------------|--------|
| AKTUELLER FÜLLSTAND zeigte 3 von 4 Feldern leer | ✅ Gefixt (Doppel-ID + tote Render-Pfade) |
| "Geplant" zeigte 0 trotz 18 Aufträgen mit Termin | ✅ Gefixt (Konzept: Filter sind orthogonale Sichten) |
| Pipeline-Datumsformate (`28. Apr`, `28.04-30.04`) wurden nicht erkannt | ✅ Gefixt (robust parseFulfillmentDate) |
| Dashboard nach Abteilungen sortieren + Suche | ✅ Geliefert (Department-Switcher + Suchfeld) |

**Drei neue Lifecycle-Anomalien** im Datenqualität-Tab nutzen erstmals **Spalte F (Anmeldedatum)** und **Spalte I (Versandanmeldung)** aus der Fulfillment-Pipeline — vorher ungenutzte Spalten.

---

**🎉 Tool ist live, getestet (147 grün), gepusht. Viel Erfolg!**
