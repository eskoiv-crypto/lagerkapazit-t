# NH5 Dashboard — Regression-Test-Harness

Playwright-basierte Tests gegen die Single-File-HTML-App (`file://` load, kein Dev-Server nötig).
Deckt die kritischen Invarianten aus Sprints 1-5 ab.

## Setup (einmalig)

Node.js ≥ 18 vorausgesetzt.

```bash
cd C:\Users\DustinEskofier\Projekt\lagerkapazität
npm install
npx playwright install chromium
```

`npm install` holt `@playwright/test`. `playwright install chromium` zieht das Browser-Binary
(~150 MB einmalig, danach gecacht).

## Tests laufen lassen

```bash
npm test               # alle Tests, headless
npm run test:headed    # mit sichtbarem Browser-Fenster
npm run test:ui        # interaktiver UI-Mode (empfohlen beim Schreiben neuer Tests)
npm run test:report    # nach Lauf: HTML-Report öffnen
```

## Struktur

```
tests/
├── helpers.js              Gemeinsame Utilities (openDashboard, uploadFixture)
├── smoke.spec.js           Bootstrap + Global-Surface (Sprint 1-5)
├── units.spec.js           Direkt-Aufrufe von escapeHtml, calculateMargin etc.
├── upload.spec.js          End-to-End BESTAND-CSV-Upload + State-Check
├── a11y.spec.js            Button-Typen, import-box role=button, Focus-Trap
└── fixtures/
    └── BESTAND_sample.csv  7-Zeilen Test-CSV mit VS/AA-Status + Auftragsnummern
```

## Aktuelle Test-Matrix (10 Tests)

| Spec | Test | Sichert ab |
|------|------|-----------|
| smoke | Dashboard lädt ohne JS-Fehler | Keine Regression-Crashes |
| smoke | Core-Helper global verfügbar | Sprint-1-bis-5 API-Oberfläche |
| units | calculateMargin + Guards | Sprint 1 P0-2/P0-3 |
| units | calculateMarginFromEkVk + Guards | Sprint 4 P2-2 |
| units | escapeHtml neutralisiert XSS | Sprint 3 P1-9 |
| units | resetAllSessionState leert alles | Sprint 2 P1-1 |
| upload | BESTAND-CSV parsing → Stats updaten | Sprint 2 gesamt |
| upload | P0-8 Header-Detection greift | Sprint 1 P0-8 |
| upload | Upload-Overlay wird ausgeblendet | Sprint 3 P1-11 |
| a11y | Alle <button> haben type | Sprint 5 P2-13 |
| a11y | .import-box keyboard-accessible | Sprint 5 P2-12 |
| a11y | .filter-btn aria-pressed | Sprint 5 P2-16 |
| a11y | <select> haben aria-label | Sprint 5 P2-14 |
| a11y | Settings-Modal Focus-Trap + ESC | Sprint 5 P2-15 |

## Regeln fürs Erweitern

1. **Ein Test pro Invariante, nicht pro Feature.** Wir wollen kleine, präzise Tests die nur
   eine Sache prüfen. Bei Bruch zeigt der Report sofort welche Invariante betroffen ist.
2. **Fixtures klein halten.** `BESTAND_sample.csv` hat absichtlich nur 7 Zeilen. Dadurch
   sind Counts rechenbar und Assertions lesbar.
3. **Helper vor Boilerplate.** Neue Upload-Szenarien bitte über `uploadFixture()` in
   `helpers.js` — nicht in jedem Spec einzeln neu aufbauen.
4. **Test-Hooks sauber halten.** Der Test-Hook-Block ganz unten in
   `elvinci_lagerkapazitaet_dashboard_v2026-04-20.html` (`window.xxx = xxx`) darf wachsen,
   aber nur für Funktionen, die per Natur genested sind oder mit `let`/`const` deklariert
   wurden.

## Bei Fehlern

- **"Cannot find module '@playwright/test'"** → `npm install` vergessen.
- **"browser not found"** → `npx playwright install chromium`.
- **Test hängt bei `file://` + Umlaut im Pfad**: Playwright ≥ 1.40 handhabt das via
  `pathToFileURL`. Ältere Versionen updaten.
- **Unerwartete console-Errors**: Siehe `test-results/*.webm` und HTML-Report
  (`npm run test:report`).
