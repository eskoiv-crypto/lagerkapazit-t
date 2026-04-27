# NH5 Dashboard — Quickstart

**Stand:** 2026-04-27 · 117/117 Tests grün · Sprint 1–7+ abgeschlossen

## 🚀 Sofort loslegen — drei Wege

### Weg 1: Desktop-Shortcut (täglich nutzen)
Auf deinem Desktop liegt jetzt **`NH5 Dashboard`** — Doppelklick öffnet das
Dashboard im Default-Browser. Kein Install, kein Server. Funktioniert offline.

### Weg 2: Direkt im Explorer
Datei doppelklicken:
```
C:\Users\DustinEskofier\Projekt\lagerkapazität\elvinci_lagerkapazitaet_dashboard_v2026-04-20.html
```

### Weg 3: Lokaler Server (für OAuth-Features)
PowerShell öffnen:
```powershell
cd 'C:\Users\DustinEskofier\Projekt\lagerkapazität'
node serve.js
```
Dann im Browser:  **http://localhost:8080/elvinci_lagerkapazitaet_dashboard_v2026-04-20.html**

Den Server brauchst du nur, wenn:
- 🔌 SharePoint Auto-Sync aktiv werden soll (10X-5)
- 🪪 Azure AD Login gewünscht ist (10X-10)
- 🤖 Chrome Prompt API LLM (10X-7) genutzt werden soll
Beim Default-`file://`-Workflow läuft alles **außer OAuth + Service Worker**.

---

## 🔑 Admin-Zugang

| Zweck | Zugang |
|-------|--------|
| Standard-Dashboard | Kein Login nötig — direkt nutzen |
| Settings & Analyse PRO | Passwort: **`elvinci2026`** |
| Azure-AD-Login (optional) | Erst nach IT-Setup verfügbar — Settings → Auth |

---

## 📥 Daten-Upload — die 5 Sektionen

| # | Sektion | Datei-Typ | Klassifizierung |
|---|---------|-----------|-----------------|
| 1️⃣ | STAMMDATEN | `BESTAND*.csv` (AMM) | 🟢 grün |
| 2️⃣ | PLANUNG | `Wareneingang*.xlsx`, `Fulfilment*.xlsx` | 🟡 gelb |
| 3️⃣ | VALIDIERUNG | `Auftrag_Status*.xlsx`, `Planner*.xlsx` | 🟡 gelb |
| 4️⃣ | PORTAL | `JTL_Export*.csv`, `All_Sold*.xlsx`, `Stock_Analysis*.xlsx` | 🔴 rot |
| 5️⃣ | ANALYSE PRO | `Paletten_*.xlsx` (Lieferanten-Angebot) | 🟡 gelb |

**Drag & Drop:** alle Dateien können einfach ins Browserfenster gezogen werden.
Der Upload-Queue (Sprint 2) verarbeitet sie seriell, ohne Race-Conditions.

---

## 🎯 Power-Features (alle live, alle getestet)

| Feature | Wo | Sprint |
|---------|-----|--------|
| 🔍 Natural-Language-Query | Datenqualität-Tab → Query-Bar | 6.9 |
| 📊 Anomalie-Radar | Datenqualität-Tab → Anomaly-Card | 6.2 |
| 💼 Angebots-Analyse v2 (Pareto + Mail-Drafts) | Analytics → Angebots-Analyse | 6.10 |
| 🛡️ PII-Maskierung Toggle | Settings → Compliance | 6.8 |
| 📋 Audit-Log Viewer | Settings → Compliance → "Audit-Log anzeigen" | 6.8 |
| 🪪 User-Badge | Oben rechts (zeigt eingeloggte Identity) | 6.7 |

### NLQ-Beispiele für die Query-Bar
```
siemens älter 180 tage
marge unter 10%
wäschetrockner status QU
ek > 200 lagertage > 90
lager 9001234567
```

### Mail-Drafts (Lieferanten-Angebote)
Nach Upload eines `Paletten_*.xlsx`:
- 📧 **Lieferant: Gegenangebot** — Top-25 Items mit unseren Max-EK-Preisen
- 📧 **Lieferant: Annahme (🟢-Items)** — nur Empfehlung KAUFEN
- 📧 **Lieferant: Ablehnung** — nur Empfehlung ABLEHNEN
- 📧 **Customer-Match** — pro Top-Kunden ein eigener Draft

---

## 🧪 Tests laufen lassen (jederzeit)

```powershell
cd 'C:\Users\DustinEskofier\Projekt\lagerkapazität'
npm test               # 117 Tests, ~2 Min
npm run test:headed    # mit sichtbarem Chrome-Fenster
npm run test:ui        # interaktiver Mode (zum Debuggen)
npm run test:report    # nach Lauf: HTML-Report öffnen
```

Vor jeder Änderung am Dashboard solltest du Tests laufen lassen — gibt
sofort Sicherheit dass nichts gebrochen ist.

---

## 📚 Wichtige Dateien

| Datei | Inhalt |
|-------|--------|
| `elvinci_lagerkapazitaet_dashboard_v2026-04-20.html` | **Das Dashboard** — 18.764 Zeilen Single-File |
| `MASTER_TODO_2026-04-20.md` | Sprint-Plan, Architektur, alle 10X-Vorschläge |
| `CLAUDE_CODE_HANDOFF_2026-04-20.md` | Ursprüngliches Manifest |
| `TEST_READINESS_REPORT.md` | Diagnose-Report vom statischen Pre-Check |
| `QUICKSTART.md` | **Diese Datei** |
| `tests/` | 14 Spec-Files mit 117 Tests |
| `serve.js` | Lokaler HTTP-Server für OAuth-Workflows |
| `package.json` | npm scripts (test, test:headed, test:ui, test:report) |

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
| Dashboard öffnet leer | Browser-Console (F12) öffnen — meistens CDN offline. Internet-Verbindung prüfen. |
| Upload zeigt ❌ Fehler | Klick auf 🔁 **Erneut versuchen** im Toast — meistens reicht das |
| Tests rot nach Code-Änderung | `npm run test:report` öffnet HTML-Report mit Trace + Screenshot |
| Settings-Modal lässt sich nicht öffnen | Passwort: `elvinci2026` (oder ESC für Schließen) |
| Daten verschwinden über Nacht | Korrekt — täglicher Reset (10X-3 + Sprint 2 P1-1). Snapshots der letzten 90 Tage in IndexedDB |

Bei tieferen Problemen: GitHub-Issue auf dem Repo erstellen oder Output von
`npm test` an mich schicken — dann diagnostiziere ich gezielt.

---

**🎉 Tool ist live, getestet, gepusht. Viel Spaß!**
