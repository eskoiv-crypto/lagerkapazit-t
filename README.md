# NH5 Lagerkapazitäts-Dashboard

Real-time warehouse capacity dashboard for **elvinci.de GmbH** — Standort NH5 Nürnberg.

Single-file HTML app. No backend required — runs 100% client-side with localStorage persistence.

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | Vanilla HTML / CSS / JavaScript |
| Charts | [Chart.js](https://www.chartjs.org/) |
| Excel Import | [SheetJS (XLSX)](https://sheetjs.com/) |
| CSV Import | [PapaParse](https://www.papaparse.com/) |
| PDF Export | [jsPDF](https://github.com/parallax/jsPDF) |
| Storage | localStorage |

## Features

- **Kapazitäts-Monitoring** — Live gauge showing warehouse utilization in PUNKTE (points)
- **Prognose** — 5-workday capacity forecast with chart visualization
- **Blockierer-Erkennung** — Identifies and prioritizes blocked orders (QU status, overdue, critical)
- **Effizienz-Tracker** — Daily WE+WA throughput tracking (target: 470/day), 90-day history
- **Daten-Validierung** — Cross-references AMM inventory against elvinci fulfilment pipeline
- **Admin Panel** — Configurable capacity parameters, weighting factors, maintenance tools

## Data Sources

### Orange — AMM Spedition (CSV, semicolon-separated, ISO-8859-1)

| File | Pattern | Content |
|---|---|---|
| Bestandsliste | `BESTAND134_YYYYMMDD.CSV` | Current warehouse inventory |
| Wareneingang IST | `WE_YYYYMMDD.CSV` | Actual goods received |
| Warenausgang IST | `WA_YYYYMMDD.CSV` | Actual goods dispatched |

### Blue — elvinci intern (XLSX)

| File | Source | Content |
|---|---|---|
| WE Pipeline | SharePoint | Incoming goods pipeline |
| Fulfilment Pipeline | SharePoint | Outbound orders pipeline |
| Auftrag Status | JTL Wawi Export | Order status data |
| Planner | Teams Planner Export | Task/planner notes |

## Capacity Calculation

Unit: **PUNKTE** (not devices)

```
Bodenfläche   = Fläche(qm) × Paletten/qm × Punkte/Palette
              = 2766 × 0.565 × 4 = 6251

Regalkapazität = Halle1 + Halle2 = 702 + 828 = 1530
Lagerkapazität = Boden + Regal = 6251 + 1530 = 7781
QU-Kapazität   = 2350
Gesamt NH5     = 7781 + 2350 = 10131
```

## Gewichtungsfaktoren (Points per device)

| Faktor | Gerätetypen |
|---|---|
| 4.0 | Side-by-Side Kühlschrank, Gefriertruhe, Freistehender Gefrierschrank |
| 2.0 | Kühlschrank, Kühl-/Gefrierkombination, Einbaukühlschrank, Fernseher |
| 1.0 | Waschmaschine, Trockner, Geschirrspüler, Backofen, Herd, Dunstabzugshaube, Klimagerät, Weinkühlschrank |
| 0.8 | Luftreiniger |
| 0.5 | Set-Artikel (Fallback) |
| 0.4 | Mikrowelle, Staubsauger, Saugroboter, Kaffeevollautomat |
| 0.2 | Kochfeld, Monitor |

## Local Path

```
C:\Users\DustinEskofier\Projekt\lagerkapazität
```

## Project Documents

- `CLAUDE_CODE_HANDOFF_2026-04-20.md` — full project manifest (architecture, state model, data flow)
- `MASTER_TODO_2026-04-20.md` — audit, sprint plan & 10X roadmap

## Author

**Dustin Eskofier** — elvinci.de GmbH

## Version

v2026-04-20 — Sprints 1–3 applied (P0 bug fixes, data-integrity hardening, security & cleanup).
Current file: `elvinci_lagerkapazitaet_dashboard_v2026-04-20.html` (~15,660 lines).

### Recent highlights

- **Sprint 1 (P0):** Division-by-zero guards, CSS var fixes, header-based BESTAND column mapping.
- **Sprint 2 (P1 integrity):** Upload queue (serial), unified `refreshAllDashboards()`, full state reset, encoding/delimiter/magic-number autodetection, 4-way cross-check (BESTAND × STATUS × Fulfillment × Planner).
- **Sprint 3 (P1 security + perf):** `escapeHtml()` applied to customer/brand/model render paths, DSGVO-minimized filenames in snapshots, memoized faktor lookup, loading overlay during parse, 4-way orphan UI.
