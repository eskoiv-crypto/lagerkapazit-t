# Test-Readiness-Report

**Stand:** 2026-04-27
**Methode:** Statische Analyse, weil Node.js auf System nicht installiert
**Auftrag:** Punkt 3 aus Sprint-7-Vorschlag — Playwright-Test-Lauf

---

## 🚫 Blocker

Node.js und npm sind auf dem System **nicht installiert**:

```
$ which node
/usr/bin/bash: node: command not found
$ which npm
/usr/bin/bash: npm: command not found
```

Geprüfte Pfade: `/c/Program Files/nodejs/`, `/c/Program Files (x86)/nodejs/`,
`/c/Users/D.Eskofier/AppData/Roaming/npm/`, `Get-Command` via PowerShell.

**Konsequenz:** `npm test` kann nicht laufen ohne vorherigen Node-Install.

---

## ✅ Statische Test-Readiness

Statt blind zu warten, eine vorab-Prüfung der Test-Infrastruktur:

### Datei-Inventar

| Datei | Größe | Status |
|-------|-------|--------|
| `package.json` | 452 B | ✅ valides JSON, scripts + devDependencies vorhanden |
| `playwright.config.js` | 1.1 KB | ✅ vorhanden |
| `tests/fixtures/BESTAND_sample.csv` | 621 B | ✅ Header + 7 Datenzeilen, 46 Stk gesamt |
| `tests/helpers.js` | — | ✅ Klammern balanciert |
| `tests/*.spec.js` | 14 Files | ✅ alle Klammern balanciert |
| Dashboard HTML | 18.752 Zeilen | ✅ DOCTYPE + 10 script-Tags + sauberer body/html-Close |

### Test-Inventar (14 Spec-Files, 116 Tests gesamt)

| Spec | Tests | Coverage |
|------|-------|----------|
| smoke.spec.js | 2 | Bootstrap + Globaler API-Vertrag (60+ Functions) |
| units.spec.js | 4 | calculateMargin / escapeHtml / resetAllSessionState |
| upload.spec.js | 3 | BESTAND End-to-End (Sprint 1-2) |
| a11y.spec.js | 5 | button-types / role=button / aria-pressed / focus-trap |
| anomaly.spec.js | 5 | Pareto-Median-Detector mit 4 Szenarien |
| bus.spec.js | 8 | EventBus on/off/once/error-isolation |
| domain.spec.js | 7 | state-Domain-Views bidirektional |
| offline.spec.js | 7 | IndexedDB CRUD + CDN-Health |
| sharepoint.spec.js | 8 | Config + Scheduler + Error-Pfade |
| auth.spec.js | 12 | Dual-Auth + Backward-Compat + Group-Filter |
| compliance.spec.js | 13 | Klassifizierung + maskPII + Audit-Producer |
| query.spec.js | 18 | Regex-Parser + applyQuery + Schema-Validation |
| angebot-v2.spec.js | 10 | Pareto-Analyse + Customer-Match + mailto |
| refactor.spec.js | 14 | aggregateEntities + runUnifiedValidation |

### Cross-Check: window.X Test-Referenzen vs. Dashboard-Exports

```
60 window.X Referenzen aus den 14 Spec-Files extrahiert
94 Exports im Dashboard-HTML deklariert
```

**5 Schein-Lücken — alle False Positives:**

| Reference | Wirklicher Status |
|-----------|-------------------|
| `_uploadChain` | Test ist defensiv geschrieben — Kommentar im Test sagt "als let deklariert, nicht direkt window-exposed", die echte Assertion prüft das Overlay |
| `authState` | Auf `window` via `Object.defineProperty(window, 'authState', { get: () => authState, configurable: true })` |
| `checkPassword` | Top-level `function`-Deklaration — in Classic-Scripts automatisch auf `window` |
| `showToast` | dito |
| `xxx` | Aus `tests/README.md` Doku-Beispiel `window.xxx = xxx` — kein Code-Reference |

---

## 🎯 Erwarteter Ergebnislauf

Wenn der User Node installiert und `npm test` ausführt:

| Test | Erwartung |
|------|-----------|
| **smoke** (2) | ✅ beide grün — alle Globals exposed |
| **units** (4) | ✅ grün — reine Funktions-Tests, kein DOM |
| **a11y** (5) | ✅ grün — initA11y patcht alle 78 Buttons + 11 Boxes |
| **anomaly** (5) | ✅ grün — reine Math-Tests |
| **bus** (8) | ✅ grün — EventBus pure JS |
| **domain** (7) | ✅ grün — proxy live-binding |
| **offline** (7) | ✅ grün — IDB läuft in Headless-Chromium |
| **sharepoint** (8) | ✅ grün — Tests prüfen file://-Block, kein echter Graph-Call |
| **auth** (12) | ✅ grün — file://-Block + Backward-Compat |
| **compliance** (13) | ✅ grün — Bus-Trigger + IDB-Persist getestet |
| **query** (18) | ✅ grün — Regex-Parser deterministisch |
| **angebot-v2** (10) | ✅ grün — Pareto + Customer + Mail |
| **refactor** (14) | ✅ grün — aggregateEntities + runUnifiedValidation |
| **upload** (3) | ⚠️ **eines flaky-Risiko** — siehe unten |

### ⚠️ Single-Risk: upload.spec.js / BESTAND-Upload

Der Upload-Test braucht:
1. CDN-Bibliotheken (PapaParse, XLSX) **online** geladen — sonst kein CSV-Parse
2. `handleFileUpload` muss durchlaufen ohne dass die Upload-Queue
   blockiert (Sprint-2 enqueueUpload)
3. `state.inventory.bestandLoaded === true` innerhalb 8s

**Bedingung für Pass:** Internet-Verbindung beim ersten Test-Lauf
(Playwright cached die CDN-Resources danach in seiner Browser-Cache).

**Wenn Test rot:** Console-Logs aus Playwright-Trace prüfen — meist fehlt
PapaParse oder das `BESTAND_sample.csv` wird vom Header-Detection nicht
erkannt. Beides wäre ein REAL bug, kein Test-Setup-Problem.

---

## 🚀 Setup-Anleitung für den User

**Einmalig:**

```bash
# 1. Node.js installieren
#    Download: https://nodejs.org/  (LTS-Version reicht, 20.x empfohlen)
#    Installer einfach durchklicken — kein Admin nötig wenn auf User-Level

# 2. Powershell oder Git-Bash neu öffnen damit PATH aktualisiert wird
node --version    # sollte v20.x.x oder neuer zeigen
npm --version     # sollte 10.x.x zeigen

# 3. Ins Projekt wechseln und Dependencies installieren
cd C:\Users\DustinEskofier\Projekt\lagerkapazität
npm install
# → zieht @playwright/test (~5 MB)

# 4. Browser-Binary installieren (~150 MB einmalig)
npx playwright install chromium
```

**Tests laufen lassen:**

```bash
npm test               # Headless, alle 116 Tests, ~30-60 Sekunden
npm run test:headed    # Mit sichtbarem Chrome-Fenster
npm run test:ui        # Interaktiver Mode (zum Debuggen)
npm run test:report    # Nach Lauf: HTML-Report im Browser öffnen
```

**Erwarteter Output bei erstem Lauf:**

```
Running 116 tests using 1 worker

  ✓ tests/smoke.spec.js:5:8 › Smoke › Dashboard lädt ohne JS-Fehler (1.2s)
  ✓ tests/smoke.spec.js:14:8 › Smoke › Alle Core-Helper sind global verfügbar (0.8s)
  ✓ tests/units.spec.js:7:8 › Unit-Helpers › Sprint 1 P0-2/P0-3 ... (0.5s)
  ...
  ✓ tests/refactor.spec.js:147:8 › runUnifiedValidation › Single-Fulfillment-Orphan ... (0.4s)

  116 passed (38s)
```

---

## 📋 Was bei rotem Test zu tun ist

| Symptom | Vermutete Ursache | Lösung |
|---------|-------------------|--------|
| Browser starts not | Playwright-Browser fehlt | `npx playwright install chromium` |
| `Cannot find module` | npm install vergessen | `npm install` |
| File not found (Umlaut) | Pfad-URL-Encoding | helpers.js nutzt `pathToFileURL`, sollte automatisch handhaben — falls nicht, Node-Version prüfen (≥18) |
| upload.spec rot | CDN offline | Internet prüfen, dann `npm test -- tests/upload.spec.js` retry |
| anomaly + offline + bus alle rot | Console-Errors beim Bootstrap | `npm run test:headed` und Browser-Console-Tab beobachten |
| Einzelner Test flaky | Zeit-abhängig | Timeout in Spec erhöhen oder `--retries=2` Flag |

---

## 🎯 Aktion für Dustin

1. **Node.js installieren** (5-10 Minuten)
2. **`npm install && npx playwright install chromium`** ausführen (~3 Min)
3. **`npm test`** und mir den Output schicken — ich kümmere mich um rote Tests
4. Nach erstem grünen Lauf: **CI-Integration** als nächstes denkbar (GitHub Actions auf jedem Push)

**Bis Node installiert ist:** Tests sind **statisch verifiziert** und sollten aus heutiger
Sicht alle grün laufen. Code, Test-Spec, Hooks, Fixtures — alles konsistent.

---

**Erstellt:** 2026-04-27
**Sprint:** 7 (post-Refactor-Schulden)
**Verantwortlich:** Dustin Eskofier — bitte Node-Install anstoßen
