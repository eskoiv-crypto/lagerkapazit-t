# Warenbestand Verpackungsmaterial — Stichtag 31.08.2026

**elvinci.de GmbH · Backoffice & Fulfillment**
**Erstellt:** 17.09.2026 · **Version:** v1 · **Status:** Werte festgelegt · Ausfertigung als PDF: `2026-08-31_Bestandsbewertung_Verpackungsmaterial_v1.pdf`
**Zweck:** Rückwirkende Bestandsbewertung zum Geschäftsjahresende (GJ 01.09.2025–31.08.2026), Konto 4710

---

## 1. Ergebnis

| | Wert netto |
|---|---:|
| **Warenbestand 31.08.2026 (festgelegter Ansatz)** | **35.482,76 €** |
| davon Lagerfeststellung Backoffice | 28.346,08 € |

| davon belegt (Wellpappe, Probepalette) | 7.136,68 € |


> Einwegpaletten und Maschinenstretchfolie: Bestand zum Stichtag durch Backoffice & Fulfillment
> festgestellt. Übrige Positionen: Rückrechnung aus belegten Lieferungen und Verbrauchskennzahlen.

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

### B. Einwegpaletten (ZELSEN) — **19.249,50 €**

| | |
|---|---|
| Letzte Lieferung | **18.08.2026** (Zusage K. Kurz vom 06.08.2026) |
| Menge | 1 LKW: ½ à 100×80, ½ à 120×80 → **1.000 Stk** |
| Preis | **10,25 €/Stk** (Mischpreis) |
| Vormonatsrest zum Stichtag | **878 Stk** — Feststellung Backoffice & Fulfillment (≈ 9.000 €) |
| Verbrauch 18.–31.08. | nach FIFO aus der älteren Charge, im Vormonatsrest bereits enthalten |
| **Restmenge 31.08.** | **1.878 Stk** (878 Vormonat + 1.000 Lieferung) |

*Preisquelle:* ZELSEN-Preisanpassung vom 26.03.2026 — 120×80 IPPC 10,50 € / 100×80 IPPC 10,25 € /
80×80 IPPC 9,90 € / 120×60 IPPC 10,25 €. Deckt sich mit dem verifizierten Kostenvergleich v5
(„neue Stückpreise 10,00–10,25 € ab den Mai-Rechnungen").

*LKW-Menge:* Referenzwerte sind Lieferschein LS0007 (24.02.2026) mit 1.166 Stk gemischt
(140 × 120×80, 210 × 100×80, 816 × 120×60; Rechnung RE260005 = 11.007 € netto) und die
Bestellung vom 16.07.2026 mit 960 Stk. Da die Lieferung vom 18.08. ausschließlich Großformate
enthielt, wurden 1.000 Stk angesetzt.

### C. Maschinenstretchfolie (Art. 517606) — **6.998,70 €**

| | |
|---|---|
| Preis | 56,90 €/Rolle = 1.707 €/Palette |
| **Bestand 31.08.** | **123 Rollen** — Feststellung Backoffice & Fulfillment (≈ 7.000 €) |

Die Menge entspricht gut 4 Paletten. Die Rückrechnung allein hätte 0 Rollen ergeben, weil sie
nur die Lieferung vom 22.07.2026 (2 Paletten = 60 Rollen) kannte; die Bestellung vom 03.08.2026
wurde demnach noch vor dem Stichtag geliefert.

### C2. Maschinenstretchfolie Probepalette, Ahrbach Süd — **1.552,50 €**

| | |
|---|---|
| Menge | 45 Rollen (eine Musterpalette) |
| Preis | **34,50 €/Rolle** — Preisangabe H.-J. Bonk vom 17.08.2026 |
| Lieferung | **20.08.2026**, bestätigt per Abliefernachweis (Mail Bonk 27.08.2026) |

Neuer Lieferant und anderer Artikel als die Prodinger-Folie 517606, daher eigene Position.
Der Musterauftrag wurde am 17.08.2026 zunächst über 2 Rollen ausgelöst; Ahrbach Süd liefert
Maschinenfolie nur palettenweise und hat eine volle Musterpalette gestellt.

### D. Handstretchfolie — **798,40 €**

**160 Rollen** à 4,99 € — Bestand durch Backoffice & Fulfillment festgestellt (≈ 800 €).
Preis aus Angebot Ahrbach-Süd AN2602363 vom 24.08.2026. Die Menge entspricht einer halben
Palette (312 Ro./Pal.) bzw. 2,0 Monaten Reichweite bei 965 Rollen Jahresbedarf.

### E. PVC-Packband (Art. 106598) — **1.299,48 €**

**884 Rollen** à 1,47 € — Bestand durch Backoffice & Fulfillment festgestellt (≈ 1.300 €).
Preis aus Prodinger AB 20055740 vom 29.04.2026 (Lieferung 180 Rollen am 05.05.2026).
Die Menge entspricht rund 25 Kartons (36 Ro./Kt.) bzw. 0,37 Paletten. Bei 1.340 Rollen
Jahresbedarf sind das 7,9 Monate Reichweite — die höchste Reichweite aller Positionen,
erklärbar über die bestätigten Zusatzeinkäufe.

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
| **Festgelegter Ansatz** | **35.482,76 €** |

Abweichung zur skalierten Referenz: **+92 %**. Die Bestandsreichweite beträgt rechnerisch
**45 Arbeitstage** — plausibel für ein Lager mit monatlichem Bestellrhythmus, das 13 Tage vor
dem Stichtag zwei Großlieferungen erhalten hat.

---

## 5. ⚠️ Offene Punkte

```
⚠️ CONCERN: Zwei der fünf Positionen stützen sich nicht auf Belege, sondern auf Feststellung
WHAT:            Einwegpaletten (Vormonatsanteil 9.000 €) und Maschinenstretchfolie
                 (7.000 €) beruhen auf der Bestandsfeststellung des Fachbereichs, nicht
                 auf Lieferscheinen. Zusammen sind das 15.998 € = 50 % des Gesamtwerts.
                 Grund: Die Rückrechnung kennt nur die per Mail belegten Lieferungen und
                 hat beide Positionen deutlich zu niedrig ausgewiesen (Paletten 608 statt
                 878 Stk Vormonatsrest, Maschinenfolie 0 statt 123 Rollen). Es gab
                 Zusatzeinkäufe, die im Mailverkehr nicht auftauchen.
WHY IT MATTERS:  Ein Prüfer, der die Herleitung nachvollzieht, kommt für diese beiden
                 Positionen auf andere Zahlen als das Dokument ausweist. Ohne
                 Belegunterlage lässt sich die Differenz nicht auflösen.
ALTERNATIVE:     (a) Konto 4710 für GJ 2025/26 aus DATEV ziehen — darin sind sämtliche
                     Einkäufe erfasst, auch die im Mailverkehr fehlenden;
                 (b) Wareneingänge bei AMM (Hr. Meyer / Hr. Pusankov, Rampe 20) für
                     15.–31.08.2026 anfordern;
                 (c) ZELSEN- und Prodinger-Rechnungen aus dem Rechnungseingang re@elvinci.de.
RECOMMENDATION:  (a) ist der wirksamste Schritt und ohnehin für den Abschluss nötig. Damit
                 wird die Bewertung vollständig belegbasiert statt teils rückgerechnet,
                 teils festgestellt.
```

**Weitere Punkte, nach Wesentlichkeit:**

1. **Wellpappe-Zuschnitte (5.584 €)** — angesetzt ist die Lieferung vom 19.08.2026. Das ist
   das *geplante* Lieferdatum der Auftragsbestätigung; Prodinger vermerkt dort ausdrücklich
   Unverbindlichkeit und „LZ ca. 3–4 Wochen", was auf Ende August bis Anfang September
   deuten würde. Ein Restbestand aus der März-Charge ist mit 0 angesetzt — angesichts der
   bestätigten Zusatzeinkäufe bei anderen Artikeln ist auch hier ein Restbestand denkbar.
   Beides über die Prodinger-Rechnung und den AMM-Wareneingang klärbar.
2. **LKW-Menge ZELSEN 18.08.** — mit 1.000 Stk angesetzt (Referenz LS0007: 1.166 Stk je LKW).
   ±25 % entsprechen ±2.563 €. Auflösbar über die ZELSEN-Rechnung.
3. **Nicht angesetzt: Umreifungsband.** Rund 30 Rollen (≈ 2.000 €) lagen am Stichtag im Lager,
   werden aber über AMM abgerechnet und sind im Aufwand enthalten. Wirtschaftliches Eigentum
   liegt bei AMM; eine Aktivierung würde fremdes Material ausweisen und den bereits gebuchten
   Aufwand doppelt erfassen. Das entspricht der Hauspraxis: AMM-Positionen auf Konto 4710
   (16.01.2023 über 1.600 €, 08.06.2022 über 61,80 €) sind in den Vorjahresblättern mit
   „Transport, Keine Ware" und 0 € Warenbestand geführt. Umreifungsband steht zudem nicht
   im Artikelstamm der Bedarfsrechnung.
4. **Verbrauchsbasis bestätigt.** Der Tagesverbrauch von 43,8 Paletten/AT aus der
   Bedarfsrechnung ist laut Fachbereich zutreffend. Die Abweichung zur Rückrechnung stammt
   nicht aus dem Verbrauch, sondern aus nicht erfassten Zusatzeinkäufen — konsistent mit
   dem Kostenvergleich v5, der für Jan–Mai 2026 einen Paletten-Einkauf von 7.538 Stk
   ausweist (≈ 18.100 Stk/Jahr) gegenüber 10.950 Stk Jahresbedarf.
5. **Verhältnis zum Vorjahr.** Der Wert liegt 74 % über dem mit dem Einkaufsvolumen
   skalierten Referenzwert (18.456 €) und entspricht 41 Arbeitstagen Reichweite statt
   der 22–23 Tage früherer Stichtage. Das ist die Folge der Bevorratung vor der
   ZELSEN-Preiserhöhung und der Zusatzeinkäufe, sollte gegenüber dem Steuerberater
   aber erklärbar hinterlegt sein.

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
