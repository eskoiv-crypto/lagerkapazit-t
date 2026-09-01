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

    if fehler:
        print("FEHLGESCHLAGEN:")
        for x in fehler:
            print("  ✗", x)
        return 1
    print(f"✓ Alle Prüfungen bestanden "
          f"(gesamt: {SOLL_GESAMT['geraete']} Geräte / {SOLL_GESAMT['ek_gesamt']:.2f} € · "
          f"freiverkäuflich: {SOLL_FREI['geraete']} / {SOLL_FREI['ek_gesamt']:.2f} € · "
          f"Dublette, Schrott, Ø-Fill, Reihe, Wächter ok)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
