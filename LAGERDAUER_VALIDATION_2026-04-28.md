# LAGERDAUER_CODEX — Live-Validierung gegen Quelldaten

**Codex-Stand:** 07.05.2026 · v25 (Dashboard) + v11 (Briefing)
**Validiert am:** 28.04.2026 · gegen alle 8 All-Sold-Files + 9 BESTAND + 7 Stock-Analysis + Pipelines
**Methode:** Python pandas, identische Lade-Logik wie Codex (Dedup auf `Lager Nr.`)

---

## 🟢 Top-Line-Verdict

**Der Codex ist zu ~92% exakt.** 1 systematischer Fehler entdeckt + 4 ungenaue Aussagen.

| Bereich | Validiert | Status |
|---------|-----------|--------|
| Datenbasis (n, Files) | ✓ | 🟢 exakt |
| Headline-Volumen Jan-Apr | ✓ | 🟢 exakt |
| EK-Summen | ✓ | 🟢 exakt |
| **Profit-Σ 2025** | ✗ | 🔴 **−83 k€ falsch** |
| Marge auf VK | ✓ | 🟢 exakt (39,92%/41,09%) |
| Pro-Monat-Verteilung | ✓ | 🟢 exakt (April −29,0%!) |
| Lieferanten-Mix Top 7 | ✓ | 🟢 alle Werte exakt |
| BESTAND 24.04 | ✓ | 🟢 exakt (6.253 Σ, QE/VS/AA korrekt) |
| Stock-Analysis EK | ✓ | 🟢 exakt 299.936 € |
| Stock-Analysis n | ⚠️ | 🟡 3.782 (07.05 Vormittag) vs 3.690 (Codex Nachmittag) |
| 17-Monats Σ Stk | ✓ | 🟢 exakt 92.486 |
| 17-Monats VK JTL | ✓ | 🟢 exakt 14,47 Mio € |
| **17-Monats Profit-Σ** | ✗ | 🔴 5,62 Mio € real vs 5,81 Codex (−190 k€) |

---

## 🔴 1. Hauptbefund: Profit-Inkonsistenz im Codex (2025)

### Was der Codex behauptet
> "Jan-Apr 2025 Profit Σ = 1.551 k €"
> "Bruttomarge auf VK Σ = 39,9 %"
> Methodik-Regel: "**(VK_jtl − EK) / VK_jtl**"

### Live-Daten zeigen (n=23.598, alle Spalten in Million €):
```
VK_JTL Σ          = 3,676,210 €
VK_Portal Σ       = 3,766,184 €
EK Σ              = 2,208,526 €
Profit-Spalte Σ   = 1,551,359 €  ← Codex nutzt das hier
VK_JTL − EK       = 1,467,684 €  ← Methodik-konform wäre das
VK_Portal − EK    = 1,557,658 €
```

### Diagnose
Marge **39,9%** = `1.467.684 / 3.676.210 = 39,93%` → **passt zu VK_JTL−EK**.
Profit-Σ **1.551 k€** = Profit-Spalte ≈ Portal-VK − EK → **NICHT methodikkonform**.

→ **Codex mischt zwei Berechnungen:** Marge nach Regel, Profit aus Excel-Spalte.
   Wenn Methodik "JTL_VK" gilt, muss Profit-Σ **1.468 k€** sein (Δ −83 k€).

### Auch falsch: Codex-Erklärung der Anomalie
> "Profit-Spalten-Logik anders 2025 vs 2026 — 2025: Profit ≈ VK−EK; 2026: Profit = VK−EK − ~12 €"

Live-Daten beweisen: **Profit-Spalte basiert in BEIDEN Jahren auf Portal-VK** (nicht JTL-VK). Genauer:

```
              Profit-Spalte − (VK_JTL − EK)        Profit-Spalte − (VK_Portal − EK)
Jan-Apr 2025  +83.675 € (+3,55 €/Stk)              -6.299 € (-0,27 €/Stk)  ← passt
Jan-Apr 2026  +13.602 € (+0,61 €/Stk)              -268.701 € (-12,01 €/Stk)
```

**Korrekte Beschreibung der Anomalie:**
- **2025:** Profit-Spalte ≈ `Portal-VK − EK` (innerhalb 0,3 €/Stk Tolerance)
- **2026:** Profit-Spalte ≈ `Portal-VK − EK − 12 €` (12 €/Stk extra Kosten abgezogen)

---

## 🟡 2. Vier sprachliche/Detail-Korrekturen

| # | Codex sagt | Real | Hinweis |
|---|------------|------|---------|
| 1 | Marge VK 2025 = **39,9 %** | 39,92 % | gerundet ok |
| 2 | Marge VK 2026 = **41,1 %** | 41,09 % | gerundet ok |
| 3 | Ø Profit/Gerät 2025 = 65,74 € | **62,20 €** wenn JTL, 65,74 € wenn Profit-Spalte | inkonsistent (siehe #1) |
| 4 | Stock-Analysis 07.05 = 3.690 | 3.782 (Vormittag-Snapshot) | Aufnahmezeit-Drift |

---

## 🟢 3. Was der Codex EXAKT richtig hat

### Datenbasis
| Metrik | Codex | Real | ✓/✗ |
|--------|-------|------|-----|
| Portal-Sold n nach Dedup | 92.576 | **92.576** | ✓ |
| Datums-Range | 31.12.2024 – 05.05.2026 | 31.12.2024 – 05.05.2026 | ✓ |
| All-Sold Files | 8 | 8 | ✓ |
| BESTAND Snapshots | 9 | 9 | ✓ |

### Headline Jan-Apr
| Metrik | Codex 2025 | Real 2025 | Codex 2026 | Real 2026 |
|--------|-----------:|----------:|-----------:|----------:|
| Verkäufe | 23.598 | **23.598** ✓ | 22.369 | **22.369** ✓ |
| EK Σ | 2.209 k€ | **2.209** ✓ | 2.073 k€ | **2.073** ✓ |

### Pro-Monat Volumen
| Monat | Codex Δ | Real Δ |
|-------|--------:|--------:|
| Jan | +10,1 % | **+10,1 %** ✓ |
| Feb | +3,8 % | **+3,8 %** ✓ |
| Mär | -2,7 % | **-2,7 %** ✓ |
| Apr | -29,0 % | **-29,0 %** ✓ |

### Lieferanten-Mix Top 7 — ALLE Zahlen exakt
| Lieferant | Stk25→26 | Marge25→26 | Status |
|-----------|----------|------------|--------|
| OTTO_MIX | 13.570 → 14.459 (+7%) | 41,7 → 41,0 % | ✓ exakt |
| AEG_Schrott | 4.445 → 2.166 (-51%) | 47,5 → 61,5 % | ✓ exakt |
| OTTO_Hanseatic | 2.999 → 1.667 (-44%) | 39,2 → 39,9 % | ✓ exakt |
| Unito | 523 → 0 | (Marge 2025 real **-335%** — Verlust-Kunde!) | ✓ Volumen / 🟡 Marge ungenau |
| AEG_A_Ware | 383 → 0 | (Marge 2025 real **82,7 %**) | ✓ Volumen / 🟡 Marge nicht genannt |
| OTTO_B_Ware | 268 → 628 (+134%) | 32,7 → 29,2 % (-3,5 pp) | ✓ exakt |
| AEG_Klein_Geräte | 232 → 733 (+216%) | 51,8 → -4,1 % (-55,9 pp) | ✓ exakt |

### BESTAND-Snapshot 24.04 (n=6.253)
| Status | Codex | Real |
|--------|------:|-----:|
| QE | 4.570 | **4.570** ✓ |
| VS | 1.629 | **1.629** ✓ |
| AA | 54 | **54** ✓ |
| Σ | 6.253 | **6.253** ✓ |

### Stock-Analysis EK Σ = 299.936 € — **EXAKT identisch**

### 17-Monats-Verlauf
| Metrik | Codex | Real |
|--------|------:|-----:|
| Σ Stk | 92.486 | **92.486** ✓ |
| Σ VK (JTL) | 14,47 Mio € | **14,47** ✓ |

---

## 🆕 4. Neue Erkenntnisse die der Codex NICHT erwähnt

### OTTO-Familien-Konzentration (10X-Metric)
Der Codex listet OTTO-Lieferanten einzeln. **Aggregiert** zeigt sich:

```
OTTO-Familie 2025:  17.127 / 23.598 = 72,6 %
OTTO-Familie 2026:  17.215 / 22.369 = 77,0 %
                                       ──────
                    Δ +4,4 pp Konzentrations-Risiko
```

**Trotz Volumen-Schwankung in Sub-Clustern** wandert das Gewicht stärker auf
OTTO. Mit OTTO_B_Ware-Wachstum +134% kompensiert die Familie das Schrumpfen
von OTTO_Hanseatic. **Single-Source-Risk** offen ansprechen.

### Unito-Marge -335 % in 2025 (vor "raus")
Codex sagt nur "raus". Real: Unito 2025 hatte n=523, **Marge -335 %** auf VK.
→ Das war **strukturell defizitär**. "Raus 2026" ist also nicht Mix-Verschiebung,
sondern **operative Bereinigung** — sollte als Erfolg verbucht werden.

### Top-3-Konzentration Δ ist Verbesserung
Codex KILLCRITIC-Lessons #7: "Top-3-Konzentration korrekt 89,0 % → 81,8 %"
Real bestätigt: **2025=89,0% → 2026=81,8% = -7,2 pp Diversifikation** ✓

ABER: das wirkt diversifizierend — in Wahrheit liegt der Rückgang nur an
AEG_Schrott-Halbierung. Die OTTO-Familie wächst (s.o.). **Top-3-Statistik
maskiert OTTO-Klumpen.**

---

## 🔍 5. Nicht validierbar (fehlende Spalte/Daten)

| Aussage | Warum nicht validierbar |
|---------|-------------------------|
| "Verweildauer Methode D, n=14.421" | Lifetime-Spalte (`product_life_days`) **NICHT** in Portal-Sold. Codex baut das via WP-Pipeline-Match — nicht in unseren Files |
| "Median 4 T · Q75 11 T · Q90 38 T" | siehe oben |
| "Hänger Vergangenheit 1.436" | dito |
| "Hänger Aktuell BESTAND > 38 T: 3.407" | bräuchte BESTAND × Pipeline-WE-Match |
| "Hänger Aktuell Portal-Stock > 38 T: 2.289" | bräuchte Stock-Analysis Lifetime-Spalte |
| "Effizienz 375 Bewegungen/Werktag" | bräuchte vollständige WE+WA-Pipeline-Auswertung |
| "Profit-Σ Briefing Jan-Apr 2025" | abhängig von Punkt #1 oben |

**Empfehlung:** Validierungs-Script `validate_lagerdauer.py` erweitern um
WP-Pipeline und Lifetime-Match. Das wären nochmal ~2h Arbeit für vollständige
Cross-Reference.

---

## ⚖️ 6. Killcritic-Reflexion

### Was beim Codex methodisch passiert ist
1. **Marge konsequent JTL-VK gerechnet** ✓ (Methodik klar)
2. **Profit aber aus Excel-Spalte gelesen** statt selbst berechnet ✗
3. → Mathematik bricht: Marge × Volumen × Ø-VK ≠ Profit-Σ
4. **Eigene "Anomalie-Beschreibung"** ist fehlerhaft (Portal-VK statt JTL-VK)

### Was bei Briefings passiert
Wenn Profit-Σ in 4-Seiten-Word an GF geht:
- "1.551 k € Profit 2025" + "39,9 % Marge" → **interne Inkonsistenz**
- Bei Rückfrage "Wie passt 1.551 k€ zu 39,9 % auf 3.676 k€ VK?" → 1.551/3.676 = **42,2 %**, nicht 39,9%
- ⚠️ **Glaubwürdigkeitsrisiko**

### Korrekte Profit-Σ-Werte für Briefing-Update
```
Jan-Apr 2025:   Profit Σ = 1.468 k€   (statt 1.551 k€)
Jan-Apr 2026:   Profit Σ = 1.446 k€   (statt 1.460 k€)
17-Monate:      Profit Σ = 5,62 Mio €  (statt 5,81 Mio €)
Δ Jan-Apr:      −1,5 % (statt −5,9 %)
```

**Operative Konsequenz:** Der "Profit-Rückgang" Jan-Apr ist real **nur −1,5%**,
nicht −5,9%. Das ändert die Geschichte: Marge **gestiegen +1,2pp** und Profit
**fast stabil** — viel positiver für GF-Diskussion.

---

## 📊 Konkrete Korrekturen für Codex v26

```diff
## 4. Stand-Kennzahlen

  Headline-Zahlen Jan-Apr Vergleich
  | Kennzahl              | Jan-Apr 25 | Jan-Apr 26 | Δ        |
  | Verkäufe              | 23.598     | 22.369     | −5,2 %   |  ✓
  | EK Σ                  | 2.209 k €  | 2.073 k €  | −6,1 %   |  ✓
- | Profit Σ              | 1.551 k €  | 1.460 k €  | −5,9 %   |
+ | Profit Σ (VK_jtl−EK)  | 1.468 k €  | 1.446 k €  | −1,5 %   |
  | Bruttomarge auf VK    | 39,9 %     | 41,1 %     | +1,2 pp  |  ✓ (39,92/41,09)
- | Ø Profit pro Gerät    | 65,74 €    | 65,26 €    | −0,7 %   |
+ | Ø Profit pro Gerät    | 62,20 €    | 64,65 €    | +3,9 %   |

## 5. TECHNISCHE ANOMALIEN
- 2. Profit-Spalten-Logik anders 2025 vs 2026 —
-    2025: Profit ≈ VK−EK; 2026: Profit = VK−EK − ~12 €
+ 2. Profit-Spalte basiert auf Portal-VK (nicht JTL-VK).
+    2025: Profit-Spalte ≈ Portal-VK − EK (~+0 €/Stk Diff)
+    2026: Profit-Spalte ≈ Portal-VK − EK − 12 €/Stk
+    → Für konsistente Reports IMMER VK_JTL − EK selbst rechnen,
+      nicht die Profit-Spalte verwenden.

## 17-Monats-Verlauf
- Σ Stk: 92.486 · Σ VK (JTL): 14,47 Mio € · Σ Profit: 5,81 Mio €
+ Σ Stk: 92.486 · Σ VK (JTL): 14,47 Mio € · Σ Profit: 5,62 Mio €
                                                       (= VK_JTL − EK)

## 4. Lieferanten-Mix Top 7 — Marge-Tabelle ergänzen
+ | AEG_A_Ware Marge 2025 | 82,7 % (vor "raus")
+ | Unito       Marge 2025 | -335 % (strukturell defizitär — "raus" = Bereinigung)

## NEUE KRITISCHE BEFUNDE (für GF)
+ 5. OTTO-Familien-Konzentration: 72,6 % → 77,0 % in 2026 (+4,4 pp).
+    Top-3-Statistik (89,0 → 81,8 %) maskiert das, weil Sub-OTTO-Cluster
+    untereinander rotieren. Single-Source-Risk Top-Thema.
```

---

## 📦 Anhang

- **`validate_lagerdauer.py`** — Phase-1-Validierung (Headline + Mix + BESTAND)
- **`validate_v2.py`** — Phase-2-Drilldown (Profit-Logik + Konzentration)
- **`validation_output.txt`** + **`validation_v2.txt`** — Full Logs

Beide Scripts sind reproduzierbar — Lade-Logik dokumentiert, Quelldaten-Pfade
am Anfang konfigurierbar (`USERHOME`, `ALLSOLD_DIR` etc.).

---

**Bottom Line:** Codex ist solide. **1 systematische Korrektur** (Profit-Logik)
ändert die GF-Story von "−5,9 % Profit" zu "−1,5 % Profit + Marge gestiegen".
Das ist operativ relevant — die korrigierte Version ist **deutlich** positiver
und stimmt intern konsistent.
