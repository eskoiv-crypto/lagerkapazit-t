# Warenbestand Verpackungsmaterial — Stichtag 31.08.2026

**elvinci.de GmbH · Backoffice & Fulfillment**
**Erstellt:** 17.09.2026 · **Version:** v1 · **Status:** Werte festgelegt · Ausfertigung als PDF: `2026-08-31_Bestandsbewertung_Verpackungsmaterial_v1.pdf`
**Zweck:** Rückwirkende Bestandsbewertung zum Geschäftsjahresende (GJ 01.09.2025–31.08.2026), Konto 4710

---

## 1. Ergebnis

| | Wert netto |
|---|---:|
| **Warenbestand 31.08.2026 (festgelegter Ansatz)** | **17.858,60 €** |
| Untergrenze (pessimistisches Szenario) | 9.277 € |
| Obergrenze (optimistisches Szenario) | 22.563 € |

> Alle Werte `[ESTIMATED]`. Keine körperliche Inventur zum Stichtag verfügbar — die Bewertung
> ist eine Rückrechnung aus belegten Lieferungen und Verbrauchskennzahlen.

---

## 2. Methodik

Angewandt wurde die **Methodik der Vorjahre** (SharePoint: *Zentrale Ablage → Abteilungen →
Fulfillment → Verpackungsrichtlinien → Warenbestand_Verpackungsmaterial*):

> Restmenge je Artikel zum Stichtag × **Nettopreis der letzten Lieferung**

Restmenge wurde je Artikel rückgerechnet als:

```
Restmenge = Menge der letzten Lieferung vor dem 31.08.2026
          − (Jahresbedarf ÷ 250 Arbeitstage × Arbeitstage zwischen Lieferung und Stichtag)
          + belegter Restbestand aus Vorlieferungen
```

**Verbrauchsbasis:** eigener, neu berechneter Jahresbedarf aus
`2026-07-15_Preisanfrage_Verpackung_Paletten.xlsx` (Basis Vorjahr inkl. Bedarfspuffer),
versendet an Ahrbach-Süd am 15.07.2026.

| Material | Jahresbedarf | je Arbeitstag |
|---|---:|---:|
| Einwegpaletten (alle 8 Formate) | 10.950 Stk | 43,8 |
| Wellpappe-Zuschnitte | 75.200 Stk | 300,8 |
| Maschinenstretchfolie | 560 Rollen | 2,24 |
| Handstretchfolie | 965 Rollen | 3,86 |
| PVC-Packband | 1.340 Rollen | 5,36 |

Nachvollziehbar in `lagerwert_verpackung_2026-08-31.py`.

---

## 3. Positionen im Einzelnen

### A. Wellpappe-Zuschnitte (Art. 268144) — **5.584,18 €**

| | |
|---|---|
| Letzte Lieferung | **19.08.2026** (geplantes Lieferdatum lt. AB) |
| Menge | 22.110 Stk (33 Paletten à 670 Stk) |
| Preis | **287,80 €/1.000 Stk** = 0,2878 €/Stk |
| Quelle | Prodinger **AB 20097713** vom 07.08.2026, netto 6.363,26 € |
| Verbrauch 19.–31.08. | 9 AT × 300,8 = 2.707 Stk |
| **Restmenge 31.08.** | **19.403 Stk** |

*Restbestand Vorcharge = 0 angesetzt:* Die März-Charge (AB 20031858, 22.110 Stk @ 259,00 €/1.000,
Lieferung 23.03.2026) reichte rechnerisch bis Anfang Juli. Die Nachbestellung am 03.08. war
dringend, eine Teillieferung wurde von Prodinger ausdrücklich ausgeschlossen — der Bestand lief
also gegen Null.

**Preisentwicklung:** 259,00 € → 287,80 €/1.000 Stk = **+11,1 %** innerhalb von 5 Monaten.

### B. Einwegpaletten (ZELSEN) — **11.992,50 €**

| | |
|---|---|
| Letzte Lieferung | **18.08.2026** (Zusage K. Kurz vom 06.08.2026) |
| Menge | 1 LKW: ½ à 100×80, ½ à 120×80 → **1.000 Stk** |
| Preis | **10,25 €/Stk** (Mischpreis) |
| Restbestand Vorlieferungen | 874 Stk (09.07.) + 960 Stk (22.07.) − 28 AT × 43,8 = 607 Stk |
| Verbrauch 18.–31.08. | 10 AT × 43,8 = 438 Stk |
| **Restmenge 31.08.** | **1.170 Stk** |

*Preisquelle:* ZELSEN-Preisanpassung vom 26.03.2026 — 120×80 IPPC 10,50 € / 100×80 IPPC 10,25 € /
80×80 IPPC 9,90 € / 120×60 IPPC 10,25 €. Deckt sich mit dem verifizierten Kostenvergleich v5
(„neue Stückpreise 10,00–10,25 € ab den Mai-Rechnungen").

*LKW-Menge:* Referenzwerte sind Lieferschein LS0007 (24.02.2026) mit 1.166 Stk gemischt
(140 × 120×80, 210 × 100×80, 816 × 120×60; Rechnung RE260005 = 11.007 € netto) und die
Bestellung vom 16.07.2026 mit 960 Stk. Da die Lieferung vom 18.08. ausschließlich Großformate
enthielt, wurden 1.000 Stk angesetzt.

### C. Maschinenstretchfolie (Art. 517606) — **0 €**

| | |
|---|---|
| Letzte belegte Lieferung | 22.07.2026 (AB 20087796), 2 Paletten = 60 Rollen |
| Preis | 56,90 €/Rolle = 1.707 €/Palette |
| Verbrauch 22.07.–31.08. | 29 AT × 2,24 = 65 Rollen |
| **Restmenge 31.08.** | **0 Rollen** (rechnerisch aufgebraucht) |

Die Bestellung vom 03.08.2026 (2 Paletten) ist als Lieferung **bis zum 31.08. nicht belegt**.
Die Prodinger-Historie zeigt für diesen Artikel lange Vorlaufzeiten (AB 20055740: Bestellung
29.04. → geplantes Lieferdatum 29.07.). Der rechnerische Nullbestand ist konsistent mit der
dringenden Nachbestellung Anfang August.

### D. Handstretchfolie — **199,60 €** (schwach belegt)

Kein Lieferbeleg für 2026 auffindbar. Angesetzt: halber Monatsbedarf = 40 Rollen à 4,99 €
(Preis aus Angebot Ahrbach-Süd AN2602363 vom 24.08.2026).

### E. PVC-Packband (Art. 106598) — **82,32 €** (schwach belegt)

Letzte belegte Lieferung 05.05.2026: 180 Rollen à 1,47 € (Prodinger AB 20055740). Reichweite
ca. 1,6 Monate → Ende Juni erschöpft. Folgelieferung nicht belegt. Angesetzt: halber
Monatsbedarf = 56 Rollen.

---

## 4. Plausibilisierung

| Referenz | Wert |
|---|---:|
| Warenbestand 31.08.2021 (Ist) | 2.944 € |
| Warenbestand 31.08.2022 (Ist) | 10.361 € |
| Warenbestand 31.08.2023 (Ist) | 13.154 € |
| Verpackungseinkauf 2025 (Ist) | 139.984 € |
| Verpackungseinkauf 2026 (hochgerechnet aus Jan–Mai) | 196.406 € (+40 %) |
| **31.08.2023 mit Einkaufsvolumen skaliert** | **18.456 €** |
| **Festgelegter Ansatz** | **17.858,60 €** |

Abweichung zur skalierten Referenz: **−3 %**. Die Bestandsreichweite beträgt rechnerisch
**23 Arbeitstage** — plausibel für ein Lager mit monatlichem Bestellrhythmus, das 13 Tage vor
dem Stichtag zwei Großlieferungen erhalten hat.

---

## 5. ⚠️ Offene Punkte

```
⚠️ CONCERN: Zwei Lieferungen unmittelbar vor dem Stichtag dominieren das Ergebnis
WHAT:            94 % des Bestandswerts stammen aus zwei Lieferungen (18.08. Paletten,
                 19.08. Wellpappe) innerhalb von 13 Tagen vor dem Stichtag. Für beide
                 liegt kein abgezeichneter Wareneingangsbeleg vor — die Wellpappe-Lieferung
                 ist nur ein "geplantes Lieferdatum" der Auftragsbestätigung (Prodinger
                 vermerkt dort ausdrücklich Unverbindlichkeit und "LZ ca. 3-4 Wochen",
                 was auf Ende August bis Anfang September deuten würde).
WHY IT MATTERS:  Verschiebt sich die Wellpappe-Lieferung um wenige Tage über den Stichtag,
                 sinkt der Bestandswert um 5.584 € (−31 %). Die Bandbreite von
                 9.277 € bis 22.563 € ist zu weit für einen Jahresabschlusswert.
ALTERNATIVE:     (a) Lieferscheine/Wareneingänge bei AMM (Hr. Meyer / Hr. Pusankov,
                     Rampe 20) für den Zeitraum 15.–31.08.2026 anfordern;
                 (b) ZELSEN-Rechnung zur Lieferung 18.08. bei rechnung@zelsen.de bzw.
                     im Rechnungseingang re@elvinci.de ziehen — sie enthält die exakte
                     Stückzahl und Preise;
                 (c) Prodinger-Rechnung zu AB 20097713 auf das tatsächliche Lieferdatum prüfen.
RECOMMENDATION:  (a)–(c) vor Weitergabe an Steuerberater/GF abarbeiten. Das ersetzt die
                 beiden größten Schätzgrößen (LKW-Menge und Wellpappe-Lieferdatum) durch
                 Belege und verengt die Bandbreite auf ca. ±5 %.
```

**Weitere Unsicherheiten, nach Wesentlichkeit:**

1. **LKW-Menge ZELSEN 18.08.** — ±25 % entsprechen ±2.998 €. Auflösbar über die Rechnung.
2. **Handstretchfolie und PVC-Packband** — zusammen 282 €, also unwesentlich, aber ohne
   Lieferbeleg reine Annahme. Bei Bedarf über Konto 4710 GJ 2025/26 verifizierbar.
3. **Verbrauchsbasis** — es wurde der geplante Jahresbedarf verwendet, nicht der Ist-Verbrauch.
   Der Kostenvergleich v5 weist für Jan–Mai 2026 einen Paletten-*Einkauf* von 7.538 Stk aus
   (≈ 18.091 Stk/Jahr hochgerechnet) gegenüber 10.950 Stk geplantem Jahresbedarf. Ein Teil
   davon ist ausgewiesene Bevorratung (Jan-Aktionskauf 1.360 IPPC à 8,10 €, Vorkauf vor der
   ZELSEN-Preiserhöhung am 26.03.), ein Teil aber möglicherweise echter Mehrverbrauch. Läge
   der Ist-Verbrauch höher, wäre der Stichtagsbestand entsprechend niedriger.
4. **Konto 4710 für GJ 2025/26 liegt nicht vor.** Für die Vorjahre existieren DATEV-Auswertungen
   in SharePoint (2021/22, 2022/23); für 2023/24 und 2024/25 fehlen sie ebenfalls. Mit der
   aktuellen Auswertung ließe sich die Bewertung vollständig belegbasiert statt rückgerechnet
   aufbauen.

---

## 6. Quellenverzeichnis

| Quelle | Inhalt |
|---|---|
| Prodinger AB **20097713** (07.08.2026) | Wellpappe 22.110 Stk @ 287,80 €/1.000, LD 19.08.2026 |
| Prodinger AB **20031858** (09.03.2026) | Wellpappe 22.110 Stk @ 259,00 €/1.000, LD 23.03.2026 |
| Prodinger AB **20055740** (29.04.2026) | PVC-Packband 180 Ro. @ 1,47 €; Stretchfolie @ 56,90 €/Ro. |
| ZELSEN **LS0007 / RE260005** (24.02. / 30.03.2026) | 1.166 Paletten, 11.007 € netto, Einzelpreise |
| ZELSEN Preisanpassung (26.03.2026) | Neue Palettenpreise 9,90–10,50 € |
| ZELSEN Bestellung 05.08. / Zusage 06.08.2026 | 1 LKW, Lieferung 18.08.2026 |
| `2026-07-15_Preisanfrage_Verpackung_Paletten.xlsx` | Jahresbedarf je Artikel |
| `2026-07-31_Kostenvergleich_2025-vs-2026_v5.pdf` | Einkaufsvolumina, ZELSEN-Mengen (verifiziert) |
| SharePoint `Warenbestand_Verpackungsmaterial/` | Methodik und Stichtagswerte 2021–2023 |
| Ahrbach-Süd AN2602361/2363/2364 (24./27.08.2026) | Marktpreise zum Stichtag (Vergleichsbasis) |

---

## 7. Nächster Schritt

Vor Weitergabe an Steuerberater oder Geschäftsführung: Wareneingangsbelege AMM für
15.–31.08.2026 sowie die beiden Rechnungen (ZELSEN 18.08., Prodinger AB 20097713) beiziehen.
Danach Neurechnung über `lagerwert_verpackung_2026-08-31.py` — die Struktur ist so angelegt,
dass nur die belegten Mengen/Daten einzutragen sind.
