#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Selbsttest fuer warenwert_stichtag.py.

Baut einen synthetischen AMM-Bestand + Odoo-Export + Portal-Restbestand mit
von Hand nachgerechnetem Soll-Ergebnis und prueft:
  * Umfang 'gesamt' (QE+VS+AA)  = Reihenwert
  * Umfang 'freiverkaeuflich'   (nur QE)
  * Dubletten-Entfernung, Schrott-Regel, Durchschnitts-Fill-Kaskade
  * Stichtags-Waechter bei abweichender Bestandsliste
  * Fortschreibung der Monatsreihe

Aufruf:  python3 tests/test_warenwert_stichtag.py
"""
import json
import subprocess
import sys
import tempfile
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SKRIPT = ROOT / "warenwert_stichtag.py"
STICHTAG = "2026-08-31"

# ---- AMM-Bestand: Palette;Artikel;Bezeichner;Charge;LgPlatz;Standort;Menge;WE;BestellNr;Status;Auftrag
BESTAND = [
    ("900000001", "Kühlschrank", "QE"),
    ("900000002", "Kühlschrank", "QE"),
    ("900000003", "Kühlschrank", "QE"),      # Preis nur im Portal
    ("900000004", "Herd",        "VS"),      # verkauft, aber physisch im Lager
    ("900000005", "Herd",        "AA"),      # auftragsgebunden, EK 0 -> Ø Kategorie
    ("900000006", "Schrottpalette", "QE"),   # Schrott -> echter EK 0
    ("900000007", "Kühlschrank", "QE"),      # nirgends bepreist -> Ø Bezeichner
    ("900000001", "Kühlschrank", "QE"),      # Dublette
]

ODOO_SPALTEN = ["Los-/Seriennummer", "Produkt", "Marke", "Produktkategorie",
                "Lieferant", "Lieferantentyp", "Lager-Code", "Einkaufspreis"]
ODOO = [
    ("ELV-1", "Kühlschrank A", "AEG",   "Kühlschränke", "AEG GmbH", "AEG_DE",      "900000001", 200.0),
    ("ELV-2", "Kühlschrank B", "AEG",   "Kühlschränke", "AEG GmbH", "AEG_DE",      "900000002", 300.0),
    ("ELV-4", "Herd D",        "Bosch", "Herde",        "Otto GmbH", "OTTO_B",     "900000004", 500.0),
    ("ELV-5", "Herd E",        "Bosch", "Herde",        "Otto GmbH", "OTTO_B",     "900000005", 0.0),
    ("ELV-6", "Palette",       "AEG",   "Sonstiges",    "AEG GmbH", "AEG_Schrott", "900000006", 0.0),
    ("ELV-9", "Herd Z",        "Bosch", "Herde",        "Otto GmbH", "OTTO_B",     "900000099", 999.0),
    ("Customers (6)", "", "", "", "", "", "", 99999.0),   # Gruppenzeile -> ignorieren
]
PORTAL = [("900000003", 150.0)]

# ---------- Soll, von Hand nachgerechnet ----------
# gesamt (QE+VS+AA), 7 eindeutige Geräte
#   belegt : 200 + 300 + 500 (Odoo) = 1000 | 150 (Portal) = 150  -> 1150
#   Ø-Fill : 900000005 -> Ø Kategorie "Herde" = 500
#            900000007 -> Ø Bezeichner "Kühlschrank" = (200+300+150)/3 = 216,667
#   Schrott: 900000006 -> 0 €
SOLL_GESAMT = {"geraete": 7, "ek_odoo": 1000.0, "ek_portal": 150.0,
               "ek_belegt": 1150.0, "ek_geschaetzt": 500.0 + (650.0 / 3),
               "n_geschaetzt": 2, "n_schrott_ek0": 1}
SOLL_GESAMT["ek_gesamt"] = SOLL_GESAMT["ek_belegt"] + SOLL_GESAMT["ek_geschaetzt"]

# freiverkäuflich (nur QE), 5 eindeutige Geräte
SOLL_FREI = {"geraete": 5, "ek_belegt": 650.0, "ek_geschaetzt": 650.0 / 3,
             "n_geschaetzt": 1, "n_schrott_ek0": 1}
SOLL_FREI["ek_gesamt"] = SOLL_FREI["ek_belegt"] + SOLL_FREI["ek_geschaetzt"]


def baue(ordner: Path, bestand_name: str):
    kopf = ("Palette;Artikel;Bezeichner;Charge;LgPlatz;Standort;Menge;"
            "WE-Datum;Bestellnummer;Status;Auftrag")
    zeilen = [kopf]
    for nr, bez, st in BESTAND:
        zeilen.append(f"{nr};007733982913;{bez};{nr};H05-WA-02-00 ;NH5;1;"
                      f"04.08.2025;20250717_DIG;{st};")
    b = ordner / bestand_name
    b.write_text("\n".join(zeilen) + "\n", encoding="iso-8859-1")

    o = ordner / "LosSerie (stock.lot)TEST.xlsx"
    pd.DataFrame(ODOO, columns=ODOO_SPALTEN).to_excel(o, index=False)

    p = ordner / "Stock-Analysis-TEST.xlsx"
    pd.DataFrame(PORTAL, columns=["lager_number", "Buying_Price"]).to_excel(p, index=False)
    return b, o, p


def pruefe(f: dict, soll: dict, label: str, fehler: list):
    for k, v in soll.items():
        ist = f[k]
        if isinstance(v, float):
            if abs(ist - v) > 0.01:
                fehler.append(f"[{label}] {k}: {ist:.4f} != {v:.4f}")
        elif ist != v:
            fehler.append(f"[{label}] {k}: {ist} != {v}")


def main() -> int:
    fehler: list[str] = []
    with tempfile.TemporaryDirectory() as tmp:
        ordner = Path(tmp)
        bestand, odoo, portal = baue(ordner, "BESTAND134_20260831_2330.CSV")
        serie = ordner / "serie.csv"
        serie.write_text("Monatsende;Stück;EK-Wert\n31.07.2026;5719;690125\n", encoding="utf-8")

        # --- Umfang gesamt ---
        j1 = ordner / "gesamt.json"
        r = subprocess.run(
            [sys.executable, str(SKRIPT), "--stichtag", STICHTAG,
             "--bestand", str(bestand), "--odoo", str(odoo),
             "--stock-analysis", str(portal), "--json", str(j1), "--serie", str(serie)],
            capture_output=True, text=True)
        print(r.stdout)
        if r.returncode != 0:
            print(r.stderr, file=sys.stderr)
            return 1
        pruefe(json.loads(j1.read_text(encoding="utf-8")), SOLL_GESAMT, "gesamt", fehler)

        # --- Umfang freiverkäuflich ---
        j2 = ordner / "frei.json"
        r = subprocess.run(
            [sys.executable, str(SKRIPT), "--stichtag", STICHTAG,
             "--bestand", str(bestand), "--odoo", str(odoo),
             "--stock-analysis", str(portal), "--umfang", "freiverkaeuflich",
             "--json", str(j2)],
            capture_output=True, text=True)
        if r.returncode != 0:
            print(r.stderr, file=sys.stderr)
            return 1
        pruefe(json.loads(j2.read_text(encoding="utf-8")), SOLL_FREI, "freiverkäuflich", fehler)

        # --- Dublette gemeldet? ---
        if json.loads(j1.read_text(encoding="utf-8"))["duplikate"] != 1:
            fehler.append("Dublette wurde nicht erkannt")

        # --- Monatsreihe fortgeschrieben? ---
        inhalt = serie.read_text(encoding="utf-8")
        erwartet = f"31.08.2026;7;{SOLL_GESAMT['ek_gesamt']:.0f}"
        if erwartet not in inhalt or "31.07.2026;5719;690125" not in inhalt:
            fehler.append(f"Reihe falsch fortgeschrieben (erwartet '{erwartet}'):\n{inhalt}")

        # --- Stichtags-Wächter ---
        alt, _, _ = baue(ordner, "BESTAND134_20260818_1600.CSV")
        r3 = subprocess.run(
            [sys.executable, str(SKRIPT), "--stichtag", STICHTAG,
             "--bestand", str(alt), "--odoo", str(odoo)],
            capture_output=True, text=True)
        if r3.returncode == 0 or "ABBRUCH" not in (r3.stdout + r3.stderr):
            fehler.append("Stichtags-Wächter greift nicht bei abweichender Bestandsliste")

        # --- EK-Korrekturliste + Brücke zur Erstfassung + Geräteliste ---
        #   900000002: Odoo 300 -> echter EK 350 (Neuklassifizierung)
        #   900000005: Odoo 0 (vorher Ø Kategorie 500) -> nachgezogener EK 120
        #   900000099: steht nicht im Bestand -> nur Warnung, nicht bewertet
        korr = ordner / "korrektur.csv"
        korr.write_text("Lager-Nr;EK;Grund\n900000002;350;AEG-Neuklassifizierung\n"
                        "900000005;120,00;Preisrecherche nachgezogen\n900000099;10;Test\n",
                        encoding="utf-8")
        j4 = ordner / "korr.json"
        liste = ordner / "geraete.xlsx"
        r4 = subprocess.run(
            [sys.executable, str(SKRIPT), "--stichtag", STICHTAG,
             "--bestand", str(bestand), "--odoo", str(odoo), "--stock-analysis", str(portal),
             "--ek-korrektur", str(korr), "--vergleich", str(j1),
             "--fassung", "2 (Test)", "--geraete-liste", str(liste), "--json", str(j4)],
            capture_output=True, text=True)
        if r4.returncode != 0:
            print(r4.stdout); print(r4.stderr, file=sys.stderr)
            return 1
        f4 = json.loads(j4.read_text(encoding="utf-8"))
        # Soll: Odoo 200+500=700 | Portal 150 | Korrektur 350+120=470 | belegt 1320
        #       Ø-Fill nur 900000007 -> Ø Bezeichner Kühlschrank = (200+350+150)/3
        soll_korr = {"geraete": 7, "ek_odoo": 700.0, "ek_portal": 150.0, "ek_korrektur": 470.0,
                     "n_korrektur": 2, "n_korrektur_nicht_im_bestand": 1,
                     "ek_belegt": 1320.0, "ek_geschaetzt": 700.0 / 3, "n_geschaetzt": 1,
                     "n_schrott_ek0": 1}
        soll_korr["ek_gesamt"] = soll_korr["ek_belegt"] + soll_korr["ek_geschaetzt"]
        pruefe(f4, soll_korr, "korrektur", fehler)
        g = f4["korrektur_gruende"]
        if (g.get("AEG-Neuklassifizierung", {}).get("ek_vorher_odoo") != 300.0
                or g.get("Preisrecherche nachgezogen", {}).get("n_vorher_ohne_ek") != 1):
            fehler.append(f"Korrektur-Gründe falsch aufgeschlüsselt: {g}")
        v = f4["vergleich"]
        if abs(v["delta_ek_gesamt"] - (soll_korr["ek_gesamt"] - SOLL_GESAMT["ek_gesamt"])) > 0.01:
            fehler.append(f"Brücke alt/neu falsch: {v}")
        if f4["fassung"] != "2 (Test)":
            fehler.append("Fassung nicht übernommen")
        gl = pd.read_excel(liste)
        if len(gl) != 7 or abs(gl["EK bewertet"].sum() - soll_korr["ek_gesamt"]) > 0.01:
            fehler.append(f"Geräteliste inkonsistent: {len(gl)} Zeilen, Σ {gl['EK bewertet'].sum():.2f}")
        if set(gl["Preisquelle"]) != {"odoo", "portal", "korrektur", "schaetzung", "schrott"}:
            fehler.append(f"Preisquellen in Geräteliste unvollständig: {set(gl['Preisquelle'])}")
        # --- Pauschalkorrekturen ohne Los-Bezug (getrennt ausgewiesen, im Gesamtwert) ---
        j6 = ordner / "pauschal.json"
        r6 = subprocess.run(
            [sys.executable, str(SKRIPT), "--stichtag", STICHTAG, "--bestand", str(bestand),
             "--odoo", str(odoo), "--stock-analysis", str(portal),
             "--pauschal-korrektur", "100;Grund A", "--pauschal-korrektur", "-25,50;Grund B",
             "--vergleich", str(j1), "--json", str(j6)], capture_output=True, text=True)
        if r6.returncode != 0:
            print(r6.stdout); print(r6.stderr, file=sys.stderr)
            return 1
        f6 = json.loads(j6.read_text(encoding="utf-8"))
        if abs(f6["ek_pauschal"] - 74.5) > 0.01 or len(f6["pauschal_korrekturen"]) != 2:
            fehler.append(f"Pauschalkorrekturen falsch: {f6['pauschal_korrekturen']} Σ {f6['ek_pauschal']}")
        if abs(f6["ek_gesamt"] - (SOLL_GESAMT["ek_gesamt"] + 74.5)) > 0.01:
            fehler.append(f"Pauschal nicht im Gesamtwert: {f6['ek_gesamt']}")
        if abs(f6["vergleich"]["delta_ek_gesamt"] - 74.5) > 0.01:
            fehler.append("Brücke berücksichtigt Pauschal nicht")
        r7 = subprocess.run(
            [sys.executable, str(SKRIPT), "--stichtag", STICHTAG, "--bestand", str(bestand),
             "--odoo", str(odoo), "--pauschal-korrektur", "100"], capture_output=True, text=True)
        if r7.returncode == 0:
            fehler.append("Pauschalkorrektur ohne Grund wurde nicht abgelehnt")

        # falscher Stichtag im Vergleich muss abbrechen
        j_falsch = ordner / "falsch.json"
        j_falsch.write_text(json.dumps({"stichtag": "2026-07-31", "umfang": "gesamt", "ek_gesamt": 1}),
                            encoding="utf-8")
        r5 = subprocess.run(
            [sys.executable, str(SKRIPT), "--stichtag", STICHTAG, "--bestand", str(bestand),
             "--odoo", str(odoo), "--vergleich", str(j_falsch)], capture_output=True, text=True)
        if r5.returncode == 0:
            fehler.append("--vergleich mit fremdem Stichtag wurde nicht abgelehnt")

    if fehler:
        print("FEHLGESCHLAGEN:")
        for x in fehler:
            print("  ✗", x)
        return 1
    print(f"✓ Alle Prüfungen bestanden "
          f"(gesamt: {SOLL_GESAMT['geraete']} Geräte / {SOLL_GESAMT['ek_gesamt']:.2f} € · "
          f"freiverkäuflich: {SOLL_FREI['geraete']} / {SOLL_FREI['ek_gesamt']:.2f} € · "
          f"Dublette, Schrott, Ø-Fill, Reihe, Wächter, Korrekturliste, Brücke, Geräteliste, Pauschal ok)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
