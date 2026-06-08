# 🎯 NH5 Dashboard — Master Improvement Backlog

**Stand:** 2026-04-20
**Methode:** 10X-Think · Killcritic · Doppel-Challenge
**Quelle:** Deep Audit über 4 parallele Prüfachsen (CSS/HTML, JS-Logik, File-Handler, Versionsvergleich)

---

## 🚨 P0 — KRITISCHE BUGS (sofort fixen, Risiko: falsche Zahlen)

| # | Issue | Zeile | Impact |
|---|-------|-------|--------|
| P0-1 | **Backslash statt Division `\` → `/`** bei Marge-Berechnungen | 5907, 5908, 5940, 6010 | Verkäufer/Dead-Stock/Marge-Zahlen falsch |
| P0-2 | **Division durch Null** in `avgOrderValue` (kunden.reduce → 0) | 6243 | Infinity in Kunden-Tab |
| P0-3 | **Division durch Null** in Angebots-Analyse avg | 7983-7984 | NaN bei leerem Angebot |
| P0-4 | **Doppelte IDs** `file-jtl-main`, `file-allsold-main`, `file-stock-main` | 4356, 4364, 4372 + 4414-4422 | `getElementById` liefert zufälliges Element |
| P0-5 | **Undefined CSS-Variable** `--border-color` (korrekt wäre `--border`) | 584, 1411, 2891 | Borders unsichtbar in Settings-Panel |
| P0-6 | **Undefined CSS-Variable** `--font-mono` (7x referenziert) | 2461, 2492, 2519, 2567, 2648, 2682 | Monospace-Fallback statt JetBrains |
| P0-7 | **Inkonsistente Datenstruktur** `stockAnalysisData` (Objekt vs. Array) | 5624 vs. 5929 | Runtime-Crash bei Tab-Wechsel |
| P0-8 | **Silent Data Loss** bei verschobenen CSV-Spalten (fixe Indizes 0,1,2,4,6) | 12431-12481, 12658-12683 | User sieht "✓ 1200 Items" obwohl nur 600 geparst |

---

## 🔴 P1 — HIGH (Datenintegrität & UX-Blocker)

### Daten & State
- [ ] **P1-1 State-Reset unvollständig** in `clearDailyDataIfNewDay()` (Z. 8559-8592): `pipelineWE`, `pipelineWA`, `bestandAuftragMap`, `fulfillmentDataMap`, `stockAnalysisData`, `allSoldData` werden nicht geleert → gestrige Daten leaken in neuen Tag
- [ ] **P1-2 Race Condition** bei Multi-File Upload (keine Queue/Mutex): BESTAND + WA-Pipeline gleichzeitig → letzter Upload überschreibt → `updateStats()` läuft mit halben Daten
- [ ] **P1-3 AUFTRAG_STATUS Upload** triggert `combineAndRenderAuftragData()` NICHT → Kommissioniert-Tab zeigt alte Daten
- [ ] **P1-4 Orphan Orders** nicht UI-sichtbar: Aufträge in Fulfillment aber nicht in BESTAND (oder umgekehrt) nur als Toast — Risiko: Auftrag versendet der nicht im Lager ist
- [ ] **P1-5 Keine 4-Way-Cross-Check**: BESTAND × AUFTRAG_STATUS × Fulfillment × Stock-Analysis als Matrix mit Lücken-Report
- [ ] **P1-6 Keine Encoding-Detection**: ISO-8859-1 hartkodiert (Z. 12278). UTF-8-BOM-CSVs werden kaputt geparst
- [ ] **P1-7 Keine Delimiter-Auto-Detection**: Nur `;` → Komma/Tab-CSVs scheitern ohne klare Fehlermeldung
- [ ] **P1-8 Keine Magic-Number-Prüfung**: CSV umbenannt zu `.xlsx` crasht XLSX.js mit kryptischem Fehler

### Sicherheit
- [ ] **P1-9 XSS-Risiko** bei `innerHTML` mit Kundennamen aus CSV (Z. 12701, 12766, 12974, 13299, 11247). Attack-Vektor: AUFTRAG_STATUS mit `<img src=x onerror=...>` in Kundenspalte
- [ ] **P1-10 DSGVO-Check**: Snapshot-Dateinamen (`BESTAND134_20260407.CSV`) in localStorage persistiert → potentieller Leak (elvinci:datenschutz-richtlinie beachten!)

### Performance
- [ ] **P1-11 Synchrones Parsing** friert UI 2-3s bei 50k-Zeilen-BESTAND (keine Web Worker, keine Chunks, kein Progress)
- [ ] **P1-12 O(n²) Fuzzy-Match** in `getArtikelFaktorLocal()` (Z. 5572-5576) bei 1000 Items × 500 Keywords → 500k Iterationen pro Upload

---

## 🟡 P2 — MEDIUM (Synergien & Refactoring)

### DRY-Verstöße
- [ ] **P2-1** Seller/Brand/Kunden-Aggregation 3× dupliziert (Z. 5843, 6214, 7331) → extrahieren zu `aggregateEntities(data, keyField, metrics)`
- [ ] **P2-2** Marge-Berechnung 5× (Z. 5849, 5907, 5909, 6010, 6273) → Helper `calculateMargin(profit, umsatz)` + `calculateMarginFromEkVk(ek, vk)`
- [ ] **P2-3** WE-IST/WA-IST AMM-Parsing 3× dupliziert (Z. 12647-12773) → `parseAMMDataRows(rows, dateStr, mode)`
- [ ] **P2-4** Post-Upload-Refresh in 5 Handlern identisch (updateStats + updateChart + renderForecastTable) → `refreshAllDashboards()` Single-Point
- [ ] **P2-5** Zwei Validierungs-Loops (`validateAuftraege` + `runValidation`, Z. 10550 & 10621) → zusammenführen
- [ ] **P2-6** `.stat-card` / `.gesamt-block` / `.analyse-kpi` sharen Accent-Bar-Pattern 10+× → Utility `.card-with-accent`
- [ ] **P2-7** Badge-Styles (`.gesamt-badge`, `.mark-count-badge`, `.filter-count`) → `.badge` Base + Modifier

### Dead Code
- [ ] **P2-8** `updateEffizienzDisplay()` + `updateWorktimePrognose()` auskommentiert (Z. 8547, 9091) aber Config wird weiter geladen → entscheiden: aktivieren oder entfernen
- [ ] **P2-9** `clearLookup()` (Z. 8190) ohne sichtbaren UI-Trigger → entfernen oder Button hinzufügen
- [ ] **P2-10** `WORKTIME_CONFIG` (Z. 5160-5195) wird geladen aber nie gerendert
- [ ] **P2-11** `--gradient-red` definiert aber nie verwendet

### Accessibility
- [ ] **P2-12** `.import-box` Divs mit `onclick` → `<button>` oder `role="button" tabindex="0"` + Keyboard-Handler
- [ ] **P2-13** Alle `<button>` ohne `type="button"` (Z. 4014, 4015, 4168, 4382, 4502, 4505, 4506)
- [ ] **P2-14** `<select>` ohne `<label>` (slowmover-threshold, topseller-metric, angebot-sort)
- [ ] **P2-15** Settings-Modal ohne Focus-Trap → `<dialog>` Element nutzen (native Trap + Escape-Close)
- [ ] **P2-16** Filter-Buttons ohne `aria-pressed`
- [ ] **P2-17** Light-Mode Kontrast: `--text-muted: #9ca3af` auf Weiß = 4:1 (WCAG AA fail bei kleinen Schriften wie Timeline-Labels 0.55rem)
- [ ] **P2-18** Drop-Zone ohne `aria-describedby` und `aria-busy` während Parse

### UX
- [ ] **P2-19** Kein Loading-Spinner / Progress-Bar bei CSV/XLSX-Parsing > 5MB
- [ ] **P2-20** Keine Empty-States in dynamischen Tabellen (slowmover-tbody, topseller-pg, …) → "Lade BESTAND" statt leere Box
- [ ] **P2-21** Error-Toast ohne Retry-Button
- [ ] **P2-22** Kein Byte-Count/Prozent bei großen Uploads

---

## 🟢 P3 — LOW (Kosmetik, Cleanup)

- [ ] P3-1 Alte HTML-Version `elvinci_lagerkapazitaet_dashboard (3).html` löschen (voll überholt)
- [ ] P3-2 `README.md` aktualisieren (aktuell 7-Zeilen-Stub, kein Feature-Overview)
- [ ] P3-3 `NH5_Dashboard_Transcript.json` referenziert v1.0 / 2026-04-09 → aktualisieren
- [ ] P3-4 `README.md.txt` Duplikat löschen
- [ ] P3-5 `test_commit.txt` löschen nach Sync-Verifikation
- [ ] P3-6 Type-Inkonsistenz `parseFloat(.toFixed(1))` (Z. 6751) → numerisch bis Display
- [ ] P3-7 PDF-Export Spalten-Breiten explizit setzen (aktuell auto → abgeschnittene Bezeichnungen)
- [ ] P3-8 Snapshots-CSV-Export ohne BOM (Z. 9808) → Excel zeigt Umlaute falsch

---

## 🚀 10X-VORSCHLÄGE (strategisch, Challenge doppelt)

Diese Ideen gehen **über "Bugs fixen" hinaus** — sie verwandeln das Dashboard in ein operatives Nervensystem.

### 🧠 10X-1 — Einheitliches Data-Model + Single Source of Truth
**Challenge:** `dashboardState` ist ein 40-Felder-Gott-Objekt mit Naming-Kollisionen (`stockAnalysisData` vs. `stockAnalysisRaw`).
**Vorschlag:** Strukturieren nach Domain:
```js
state = {
  inventory: { bestand, snapshots, faktoren },
  pipeline:  { we, wa, fulfillment },
  portal:    { stock, sold },
  analysis:  { angebote, validierung, diskrepanzen },
  config:    { kapazitaet, worktime, theme }
}
```
**Doppel-Challenge:** "Reicht nicht ein Rename?" — Nein: die **Inkonsistenz zwischen Objekt-Map und Array** (P0-7) ist ein **Architekturfehler**, kein Name-Fehler. Nur ein klares Schema verhindert, dass künftige Features diesen Bug wieder einbauen.

### 🔄 10X-2 — Event-Bus statt manueller Refresh-Kaskaden
**Challenge:** Jeder Handler ruft 5-7 `updateX()` in fester Reihenfolge. P1-3 (AUFTRAG_STATUS triggert nichts) zeigt: vergisst man einen Call, zeigt die UI lügen.
**Vorschlag:** `EventBus.emit('bestand:loaded', data)` → alle Tabs registrieren Listener. Neuer Tab = 1 Listener, kein Handler-Code anfassen.
**Doppel-Challenge:** "Overkill für ein Single-File-Dashboard?" — Nein: **genau in Single-File-JS** lohnt sich Pub/Sub, weil Review-Komplexität linear mit Feature-Zahl steigt. 90 neue Funktionen seit v1 beweisen das.

### 📦 10X-3 — Offline-fähig via Service Worker + IndexedDB
**Bereits im Backlog (P3).** Aber denke größer: **Service Worker + IndexedDB** → echter Offline-Modus mit automatischer Daten-Historie (Snapshots der letzten 30 Tage). Dashboard lädt auch ohne Internet, zeigt letzten Stand, synchronisiert bei Verbindung.
**Doppel-Challenge:** "Wir haben doch CDN-Fallback?" — CDN offline hilft nix wenn AMM-VPN ausfällt. Warehouse-Manager brauchen das Dashboard **auch im Lager ohne LAN**.

### 🎯 10X-4 — Auto-Daily-Diff / Anomalie-Detektor
**Heute:** Dashboard zeigt heute. User müssen selbst erkennen, dass "Side-by-Side-Bestand um 40% in 1 Tag gefallen" ist.
**Vorschlag:** Auto-Vergleich gegen Snapshot-Historie (30d Rolling). Anomalien (>2σ) als **proaktive Badge** im jeweiligen Tab. "⚠️ Ungewöhnlich: Electrolux-Bestand -37% seit gestern"
**Doppel-Challenge:** "Kann der User nicht selbst schauen?" — Operative Realität: Dustin schaut nicht jeden Tab jeden Tag. Frühwarnung ist genau der Business-Wert, der aus 15k-Zeilen-Daten einen Vorteil macht.

### 🔌 10X-5 — SharePoint-Integration mit Sync-Status-UI
**P3 hat es.** Aber: sauber machen heißt **bidirektional + Audit**:
- Auto-Pull-Mode: alle 15 Min neuester BESTAND
- Push-Mode: Snapshots zurück nach SharePoint
- **Sync-Log-Panel:** "Letzter Pull: vor 3 Min ✓ | Next: 12 Min | Last Push-Fehler: 2026-04-18"
**Doppel-Challenge:** "Browser kann kein SharePoint auth?" — MSAL.js + Graph API, PKCE-Flow, funktioniert seit 2022 client-seitig im Browser. Kein Backend nötig.

### 🛡️ 10X-6 — Compliance-Layer (DSGVO + elvinci-Richtlinie)
**Erinnerung:** Skill `elvinci-datenschutz-richtlinie` ist aktiv. Dashboard verarbeitet Kundendaten im Browser.
**Vorschlag:**
- Daten-Klassifizierung beim Upload (🟢/🟡/🔴 Ampel pro Datei-Typ)
- Auto-Maskierung in Screenshots (Kundenname → "Kunde_XX")
- localStorage nur für 🟢-Daten
- Audit-Log: Wer hat wann welche Datei geladen? (IndexedDB)
**Doppel-Challenge:** "Ist das nicht IT-Thema?" — Nein: Dashboard ist das **Frontline-Tool**, das mit sensiblen B2B-Kundendaten arbeitet. Compliance-by-Design im Dashboard spart später Review-Zyklen.

### 🤖 10X-7 — Lokales LLM für Natural-Language-Queries
**Vision:** Dustin tippt: "Zeig mir alle Siemens-Paletten über 180 Tage mit Marge < 10%"  → Dashboard filtert. Via `chrome://flags` Prompt API oder WebLLM (lokal, ohne Cloud).
**Doppel-Challenge:** "Gimmick?" — Für 12 Tabs × 20 Filter-Kombinationen × 36 Nutzer: spart im Schnitt 5 Klicks/Query = realer Zeitgewinn. Und: kein Cloud = DSGVO-safe.

### 📊 10X-8 — Automatisierte Angebots-Analyse PRO v2
**Heute:** User uploaded Angebot, bekommt Ampel.
**Vision:** **Batch-Analyse aller offenen Angebote** mit Pareto-Score, Kunden-Vorab-Matching (wer kauft das seit 12 Monaten?), automatische E-Mail-Draft mit Gegenangebot.
**Doppel-Challenge:** "Mail-Draft ist Outlook-Job?" — Kein Job-Wechsel: `mailto:`-Link mit vorgeneriertem Body reicht. Zero Extra-Tooling.

### 🧪 10X-9 — Regression-Test-Harness via Playwright (einmal einrichten)
**Heute:** 20+ Sessions, jedes Mal manuelles Testen mit Paletten_*.xlsx.
**Vorschlag:** Playwright-Script mit 5 Fixture-Files, 20 Assertions. In 30s weißt du: alles grün.
**Doppel-Challenge:** "Für Single-File-HTML?" — Gerade dort: HTML wird immer instabiler je mehr Features (P0-1 bis P0-8 zeigen das). Tests kosten 4h einmal, sparen 20h/Jahr.

### 🔐 10X-10 — Passwort-Gate richtig machen
**Heute:** Hardcoded `elvinci` (Z. 530). Jeder mit DevTools sieht es.
**Vorschlag:** Argon2/bcrypt-Hash im HTML + WebAuthn für Admin-Features, oder OAuth via Azure AD (elvinci ist sowieso MS365). Nutzer-spezifische Rollen (Backoffice ≠ Sales ≠ Leadership).
**Doppel-Challenge:** "Brauchen wir das?" — Sobald Stock-EK-Preise (einkaufskritisch) im Portal-Export sichtbar sind: JA. Heute ist das Gate Security-Theater.

---

## 📋 EMPFOHLENE REIHENFOLGE (Sprint-Plan)

### Sprint 1 (1 Tag) — "Blutungen stoppen"
P0-1 bis P0-8 durcharbeiten. Danach stimmen die angezeigten Zahlen wieder.

### Sprint 2 (2 Tage) — "Datenintegrität härten"
P1-1, P1-2, P1-3, P1-4, P1-6, P1-7, P1-8. Ergebnis: Keine stillen Daten-Verluste mehr.

### Sprint 3 (1 Tag) — "Security & DSGVO"
P1-9, P1-10, P3-1 bis P3-5 (Hausputz).

### Sprint 4 (3 Tage) — "Refactor-Kur"
P2-1 bis P2-11. 30% Code-Reduktion realistisch.

### Sprint 5 (1 Tag) — "A11y & UX Polish"
P2-12 bis P2-22.

### Sprint 6+ — "10X Features"
10X-1 (Data-Model) + 10X-2 (Event-Bus) ZUERST — sie sind Fundament für alles andere.
Dann: 10X-3 (Offline) oder 10X-4 (Anomalie-Detektor) — abhängig von Prio mit Dustin.

---

## 🎤 KILLCRITIC — Was ich bewusst NICHT vorgeschlagen habe (und warum)

- **Framework-Migration (React/Vue):** 15k Zeilen Vanilla sind ein Asset, kein Problem. Migration wäre 3 Monate Arbeit für 0 Business-Value.
- **Backend + DB:** Widerspricht dem "client-only"-Designprinzip. Wenn nötig, dann nur SharePoint als Backend (10X-5).
- **Kompletter Rewrite:** Nein. Der Dashboard-Stack liefert. Inkrementelle Härtung schlägt Big-Bang.
- **TypeScript:** Verführerisch, aber würde 15k Zeilen anfassen müssen. Stattdessen: JSDoc-Types punktuell an den P0/P1-Hotspots.

---

**Nächster Schritt, Dustin:** Freigabe für Sprint 1 (P0-Fixes). Ich kann die 8 kritischen Bugs in einem Zug patchen, Commit, Push nach GitHub. Sag einfach "los" — oder nenne mir welche Todos du anders priorisieren willst.
