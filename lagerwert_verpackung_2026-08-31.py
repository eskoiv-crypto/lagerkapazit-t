#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Bewertung Warenbestand Verpackungsmaterial zum Stichtag 31.08.2026 (Geschäftsjahresende)
elvinci.de GmbH - Backoffice & Fulfillment

Methodik (analog Vorjahre, Ordner SharePoint .../Verpackungsrichtlinien/Warenbestand_Verpackungsmaterial):
    Restmenge je Artikel zum Stichtag x Nettopreis der letzten Lieferung (Konto 4710)

Restmenge = Menge der letzten Lieferung vor Stichtag
          - (Verbrauch/Arbeitstag x Arbeitstage zwischen Lieferung und Stichtag)
          + belegter Restbestand aus Vorlieferungen

Alle Preise netto. Quellen je Position in QUELLE dokumentiert.
"""

AT_JAHR = 250          # Arbeitstage/Jahr (261 Werktage 2026 abzgl. ~11 Feiertage Bayern)
AT_MONAT = AT_JAHR / 12

# ---------------------------------------------------------------------------
# 1) VERBRAUCHSBASIS - Jahresbedarf lt. eigener Bedarfsrechnung
#    Quelle: 2026-07-15_Preisanfrage_Verpackung_Paletten.xlsx (neu berechneter Bedarf,
#    Basis Vorjahr inkl. Puffer), versendet an Ahrbach-Sued 15.07.2026
# ---------------------------------------------------------------------------
JAHRESBEDARF = {
    "Einwegpalette 1200x600":        4080,
    "Einwegpalette 1200x600 IPPC":   1360,
    "Einwegpalette 1200x800":        1880,
    "Einwegpalette 1200x800 IPPC":    630,
    "Einwegpalette 1000x800":        1275,
    "Einwegpalette 1000x800 IPPC":    425,
    "Einwegpalette 800x800":          975,
    "Einwegpalette 800x800 IPPC":     325,
    "Maschinenstretchfolie (Rollen)": 560,
    "Handstretchfolie (Rollen)":      965,
    "Wellpappe-Zuschnitte (Stueck)":75200,
    "PVC-Packband (Rollen)":         1340,
}
PALETTEN_JAHR = sum(v for k, v in JAHRESBEDARF.items() if k.startswith("Einwegpalette"))

def pro_at(jahresmenge):
    return jahresmenge / AT_JAHR

# ---------------------------------------------------------------------------
# 2) POSITIONEN
# ---------------------------------------------------------------------------
positionen = []

# --- A) Wellpappe-Zuschnitte 268144 -----------------------------------------
# QUELLE: Prodinger AB 20097713 v. 07.08.2026: 22,11 T Stk @ 287,80 EUR/1000 Stk
#         = 6.363,26 EUR netto, geplantes Lieferdatum 19.08.2026
#         Vorlieferung: AB 20031858 v. 09.03.2026, 22.110 Stk @ 259,00 EUR/1000, LD 23.03.2026
wp_menge   = 22110
wp_preis   = 287.80 / 1000
wp_at      = 9                      # Arbeitstage 19.08. - 31.08.2026
wp_verbr   = pro_at(JAHRESBEDARF["Wellpappe-Zuschnitte (Stueck)"]) * wp_at
# Restbestand Vorcharge = 0: Maerz-Charge (22.110 Stk) reicht bei 6.267 Stk/Monat
# rechnerisch bis Anfang Juli; Nachbestellung 03.08. war dringend, Teillieferung
# ausdruecklich nicht moeglich -> Bestand lief gegen Null.
wp_rest_alt = 0
wp_bestand  = wp_menge - wp_verbr + wp_rest_alt
positionen.append(("Wellpappe-Zuschnitte 268144", wp_bestand, "Stk", wp_preis,
                   "AB 20097713 (07.08.26), LD 19.08.26"))

# --- B) Einwegpaletten (ZELSEN) ---------------------------------------------
# QUELLE: Bestellung 05.08.2026 (1 LKW: 1/2 100x80 + 1/2 120x80),
#         Lieferzusage K. Kurz 06.08.2026 -> Lieferung 18.08.2026
# LKW-Menge: Referenz LS0007 (24.02.2026) = 1.166 Stk gemischt je LKW,
#         Bestellung 16.07. = 960 Stk (60x120). Angesetzt: 1.000 Stk
# Preis: Preisliste ZELSEN ab 26.03.2026: 120x80 IPPC 10,50 / 100x80 IPPC 10,25
#        -> Mischpreis 10,25 EUR (deckt sich mit Kostenvergleich v5: "10,00-10,25 EUR")
pal_lkw     = 1000
pal_preis   = 10.25
pal_at      = 10                    # Arbeitstage 18.08. - 31.08.2026
pal_verbr   = pro_at(PALETTEN_JAHR) * pal_at
# Restbestand vor der 18.08.-Lieferung:
#   Zugaenge 09.07. (874 Stk, Bestellung 23.06.) + 22.07. (960 Stk, Bestellung 16.07.)
#   abzgl. Verbrauch 09.07.-17.08. (28 AT)
pal_rest_alt = 874 + 960 - pro_at(PALETTEN_JAHR) * 28
pal_bestand  = pal_lkw - pal_verbr + max(pal_rest_alt, 0)
positionen.append(("Einwegpaletten (alle Formate)", pal_bestand, "Stk", pal_preis,
                   "ZELSEN Lieferung 18.08.26"))

# --- C) Maschinenstretchfolie 517606 ----------------------------------------
# QUELLE: Prodinger AB 20055740: 56,90 EUR/Rolle; 30 Rollen/Palette
#         (Gegenprobe Mail I. Mkhitarian 28.05.2026: 2.031,33 EUR brutto/Palette
#          = 1.706,99 netto / 30 = 56,90 EUR/Rolle)
#         Letzte gesicherte Lieferung: 22.07.2026 (AB 20087796), 2 Paletten = 60 Rollen
#         Bestellung 03.08.2026 (2 Pal.) - Lieferung bis 31.08. NICHT belegt
folie_zug   = 60
folie_preis = 56.90
folie_at    = 29                    # Arbeitstage 22.07. - 31.08.2026
folie_verbr = pro_at(JAHRESBEDARF["Maschinenstretchfolie (Rollen)"]) * folie_at
folie_bestand = max(folie_zug - folie_verbr, 0)
positionen.append(("Maschinenstretchfolie 517606", folie_bestand, "Rollen", folie_preis,
                   "Lieferung 22.07.26, 2 Pal."))

# --- D) Handstretchfolie ------------------------------------------------------
# KEIN Beleg einer Lieferung 2026 in Outlook/SharePoint auffindbar.
# Ansatz [ESTIMATED]: ein halber Monatsbedarf als Umlaufbestand.
# Preis: Angebot Ahrbach-Sued AN2602363 v. 24.08.2026: 4,99 EUR/Rolle
hand_bestand = JAHRESBEDARF["Handstretchfolie (Rollen)"] / 12 * 0.5
positionen.append(("Handstretchfolie", hand_bestand, "Rollen", 4.99,
                   "SCHAETZUNG - kein Lieferbeleg"))

# --- E) PVC-Packband 106598 ---------------------------------------------------
# QUELLE: Prodinger AB 20055740 v. 29.04.2026: 180 Rollen @ 1,47 EUR, LD 05.05.2026
# 180 Rollen decken bei 111,7 Rollen/Monat ca. 1,6 Monate -> Ende Juni erschoepft.
# Folgelieferung bis 31.08. nicht belegt. Ansatz [ESTIMATED]: halber Monatsbedarf.
band_bestand = JAHRESBEDARF["PVC-Packband (Rollen)"] / 12 * 0.5
positionen.append(("PVC-Packband 106598", band_bestand, "Rollen", 1.47,
                   "SCHAETZUNG - Folgelieferung nicht belegt"))

# ---------------------------------------------------------------------------
# 3) AUSGABE
# ---------------------------------------------------------------------------
print("=" * 88)
print("WARENBESTAND VERPACKUNGSMATERIAL - STICHTAG 31.08.2026 (netto)")
print("=" * 88)
print(f"Verbrauchsbasis: {AT_JAHR} AT/Jahr | Paletten gesamt {PALETTEN_JAHR} Stk/Jahr "
      f"= {pro_at(PALETTEN_JAHR):.1f} Stk/AT")
print(f"                 Wellpappe {JAHRESBEDARF['Wellpappe-Zuschnitte (Stueck)']} Stk/Jahr "
      f"= {pro_at(JAHRESBEDARF['Wellpappe-Zuschnitte (Stueck)']):.1f} Stk/AT")
print("-" * 88)
print(f"{'Position':<34}{'Menge':>10} {'ME':<8}{'EUR/ME':>9}{'Wert EUR':>12}  Basis")
print("-" * 88)
summe = 0.0
for name, menge, me, preis, basis in positionen:
    menge = round(menge)          # Bestand wird in ganzen Einheiten gefuehrt
    wert = menge * preis
    summe += wert
    print(f"{name:<34}{menge:>10,.0f} {me:<8}{preis:>9,.4f}{wert:>12,.2f}  {basis}")
print("-" * 88)
print(f"{'SUMME Warenbestand 31.08.2026':<34}{'':>10} {'':<8}{'':>9}{summe:>12,.2f} EUR netto")
print("=" * 88)

# Plausibilisierung
print("\nPLAUSIBILISIERUNG")
print("-" * 88)
vj = {"31.08.2021": 2943.86, "31.08.2022": 10360.56, "31.08.2023": 13154.14}
for k, v in vj.items():
    print(f"  Vorjahreswert {k}: {v:>10,.2f} EUR")
ek_2025 = 139984.21                       # Kostenvergleich v5: Verpackungseinkauf Gesamtjahr 2025
ek_2026_hr = 81835.66 / 5 * 12            # Jan-Mai 2026 hochgerechnet
print(f"\n  Verpackungseinkauf 2025 (Ist):        {ek_2025:>10,.2f} EUR")
print(f"  Verpackungseinkauf 2026 (hochgerechnet):{ek_2026_hr:>10,.2f} EUR  "
      f"(+{(ek_2026_hr/ek_2025-1)*100:.0f} %)")
print(f"  Referenzwert 31.08.2023 skaliert:     "
      f"{vj['31.08.2023'] * ek_2026_hr / ek_2025:>10,.2f} EUR")
print(f"  Bestandsreichweite:                   "
      f"{summe / ek_2026_hr * AT_JAHR:>10,.0f} Arbeitstage")

# Bandbreite
print("\nBANDBREITE (Sensitivitaet Hauptrisiken)")
print("-" * 88)
wp_wert = wp_bestand * wp_preis
pal_wert = pal_bestand * pal_preis
unten = summe - wp_wert - pal_wert * 0.25          # Wellpappe erst im Sept. geliefert, LKW kleiner
oben  = summe + 6363.26 * 0.0 + pal_wert * 0.25 + folie_bestand * 0 + 1707  # groesserer LKW + Folie 03.08. geliefert
print(f"  Untergrenze (Wellpappe-Lieferung erst nach Stichtag, LKW -25 %): {unten:>10,.2f} EUR")
print(f"  Punktschaetzung:                                                 {summe:>10,.2f} EUR")
print(f"  Obergrenze (LKW +25 %, Folienbestellung 03.08. noch geliefert):  {oben:>10,.2f} EUR")
