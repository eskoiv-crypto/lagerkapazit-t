#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Warenwert (EK) zum Stichtag — Fortschreibung der Reihe "Warenwert zum Monatsende".

Definition (festgelegt im Teams-Thread Vasiadis / Eskofier / Schneider, 13.-14.08.2026,
Anlass: Abstimmung mit der Steuerkanzlei)

    "Warenbestaende fuer jeden Monat [...] anhand der Waren die wir tatsaechlich
     im Lager haben (inklusive Waren die an die Kunden verkauft sind) - das waere
     der grosse Wert der bei ODOO KPIs erscheint und nicht nur die freiverkaeufliche
     Ware."                                    - K. Vasiadis, 13.08.2026

  => Warenwert(S) = SUMME Einkaufspreis ALLER Geraete, die am Stichtag S physisch
                    im Lager NH5 lagen - unabhaengig davon, ob bereits verkauft.

  Physische Wahrheit  = AMM-Bestandsliste BESTAND134 vom Stichtag
                        (Status QE = frei, VS = Versandpipeline, AA = auftragsgebunden)
  Preis               = Einkaufspreis aus dem Odoo-Export (stock.lot),
                        Join ueber die Lager-Nr
  fehlender EK        = Durchschnitts-EK (Produktkategorie > Marke > Bezeichner >
                        global) - so wie bisher gerechnet
  Schrott-Ware        = echter EK 0 EUR, KEIN Durchschnitts-Fill
                        (Korrektur D. Schneider, 14.08.2026)

Bekannte Unschaerfen (D. Schneider, 14.08.2026)
  * Ein manuell gezogener Export ist nicht der Mitternachtsstand des Monatsletzten.
  * Der Durchschnitts-Fill ueberzeichnet AEG-Schrottware, deren EK echt 0 ist.

Aufruf
------
  python3 warenwert_stichtag.py \\
      --stichtag 2026-08-31 \\
      --bestand "data/amm/BESTAND134_20260831_2330.CSV" \\
      --odoo    "data/odoo/LosSerie (stock.lot)01092026.xlsx" \\
      --serie   warenwert_monatsende.csv \\
      --json    warenwert_facts_2026-08-31.json

  Zusaetzliche EK-Quelle (eingefrorener Portal-Restbestand, Endstand 02.07.2026):
      --stock-analysis "data/elvinci/Stock-Analysis-2026-07-02.xlsx"

  Engere Sicht (nur freiverkaeufliche Ware, wie im Vertriebs-Cockpit-Einseiter):
      --umfang freiverkaeuflich
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import re
import sys
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path

import pandas as pd


# --------------------------------------------------------------------------
# BESTAND134 (AMM, Semikolon, ISO-8859-1)
#   0 Palette | 1 Artikel | 2 Bezeichner | 3 Charge (= Lager-Nr) | 4 LgPlatz
#   5 Standort | 6 Menge | 7 WE-Datum | 8 Bestellnummer | 9 Status | 10 Auftrag
# --------------------------------------------------------------------------
BESTAND_SPALTEN = {"palette": 0, "artikel": 1, "bezeichner": 2, "charge": 3,
                   "lgplatz": 4, "standort": 5, "menge": 6, "we": 7,
                   "bestellnr": 8, "status": 9, "auftrag": 10}

UMFANG_STATUS = {
    # alles, was physisch im Lager steht - inkl. verkaufter Ware (Reihenwert)
    "gesamt": {"QE", "VS", "AA"},
    # nur freiverkaeufliche Ware (engere Cockpit-Sicht)
    "freiverkaeuflich": {"QE"},
}

# Odoo-Spalten (mehrere Schreibweisen zulassen)
ODOO_SPALTEN = {
    "lagernr":   ["Lager-Code", "Lager Nr.", "Lager-Nr.", "Lagernummer"],
    "los":       ["Los-/Seriennummer", "Los/Seriennummer", "Name"],
    "produkt":   ["Produkt", "Artikel"],
    "kategorie": ["Produktkategorie", "Produktgruppe", "Warengruppe"],
    "marke":     ["Marke", "Brand"],
    "lieferant": ["Lieferant"],
    "liefertyp": ["Lieferantentyp"],
    "ek":        ["Einkaufspreis", "EK"],
}

# Portal Stock-Analysis (eingefrorener Restbestand)
PORTAL_SPALTEN = {
    "lagernr": ["lager_number", "Lager Nr.", "lager_nr", "Lager-Nr."],
    "ek":      ["Buying_Price", "Portal Buying Price", "Einkaufspreis"],
}


def finde_spalte(df: pd.DataFrame, aliase: list[str]) -> str | None:
    norm = {str(c).strip().lower(): c for c in df.columns}
    for a in aliase:
        if a.strip().lower() in norm:
            return norm[a.strip().lower()]
    for a in aliase:
        k = a.strip().lower()
        for n, orig in norm.items():
            if k and k in n:
                return orig
    return None


def zu_zahl(v) -> float:
    if v is None:
        return 0.0
    if isinstance(v, (int, float)):
        return 0.0 if (isinstance(v, float) and math.isnan(v)) else float(v)
    s = str(v).strip().replace("€", "").replace("\xa0", "").replace(" ", "")
    if not s or s in {"-", "—", "nan", "None"}:
        return 0.0
    if "," in s and "." in s:
        s = s.replace(".", "").replace(",", ".")
    elif "," in s:
        s = s.replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return 0.0


def lagernr(v) -> str:
    """Lager-Nr normalisieren: '900246202', ' 900246202 ', 900246202.0 -> '900246202'"""
    s = str(v or "").strip()
    if s.endswith(".0"):
        s = s[:-2]
    return s


def eur(x: float) -> str:
    return f"{x:,.0f}".replace(",", ".") + " €"


def de(n: int) -> str:
    return f"{n:,}".replace(",", ".")


# --------------------------------------------------------------------------
@dataclass
class Ergebnis:
    stichtag: str
    umfang: str
    quelle_bestand: str
    quelle_odoo: str | None = None
    quelle_portal: str | None = None

    bestand_zeilen_gesamt: int = 0
    status_verteilung: dict = field(default_factory=dict)

    geraete: int = 0                 # Zeilen im gewaehlten Umfang
    menge: int = 0                   # Summe Spalte "Menge"
    duplikate: int = 0

    ek_odoo: float = 0.0
    n_odoo: int = 0
    ek_portal: float = 0.0
    n_portal: int = 0
    ek_geschaetzt: float = 0.0
    n_geschaetzt: int = 0
    n_schrott_ek0: int = 0

    ek_belegt: float = 0.0           # Odoo + Portal (echte Preise)
    ek_gesamt: float = 0.0           # Reihenwert

    warnungen: list[str] = field(default_factory=list)


# --------------------------------------------------------------------------
def lade_bestand(pfad: Path) -> pd.DataFrame:
    zeilen = []
    with open(pfad, "r", encoding="iso-8859-1", newline="") as fh:
        for row in csv.reader(fh, delimiter=";"):
            if not row or len(row) < 10:
                continue
            if str(row[BESTAND_SPALTEN["status"]]).strip().lower() == "status":
                continue                      # Kopfzeile
            zeilen.append(row)
    if not zeilen:
        raise SystemExit(f"FEHLER: {pfad.name} enthaelt keine auswertbaren Zeilen.")
    df = pd.DataFrame({
        "lagernr":    [lagernr(r[BESTAND_SPALTEN["charge"]]) for r in zeilen],
        "palette":    [lagernr(r[BESTAND_SPALTEN["palette"]]) for r in zeilen],
        "bezeichner": [str(r[BESTAND_SPALTEN["bezeichner"]]).strip() for r in zeilen],
        "menge":      [int(zu_zahl(r[BESTAND_SPALTEN["menge"]]) or 1) for r in zeilen],
        "status":     [str(r[BESTAND_SPALTEN["status"]]).strip().upper() for r in zeilen],
    })
    # Für Sammelpaletten steht die Lager-Nr nicht in "Charge" -> Palette als Ersatz
    ohne = ~df["lagernr"].str.fullmatch(r"\d{6,}")
    df.loc[ohne, "lagernr"] = df.loc[ohne, "palette"]
    return df


def lade_odoo_preise(pfad: Path) -> tuple[dict, dict, dict, dict]:
    """-> ek_map, kategorie_map, marke_map, schrott_map (je Lager-Nr)"""
    df = pd.read_excel(pfad, engine="openpyxl")
    col = {k: finde_spalte(df, v) for k, v in ODOO_SPALTEN.items()}
    if col["lagernr"] is None or col["ek"] is None:
        raise SystemExit(f"FEHLER: In {pfad.name} fehlt 'Lager-Code' oder 'Einkaufspreis'. "
                         f"Gefunden: {list(df.columns)[:12]} ...")
    # Gruppen-/Summenzeilen des Odoo-Exports verwerfen
    if col["los"]:
        s = df[col["los"]].astype(str).str.strip()
        df = df[~(s.str.match(r"^.*\(\d+\)$") | s.isin(["", "nan", "None"]))]

    ek, kat, marke, schrott = {}, {}, {}, {}
    for _, r in df.iterrows():
        nr = lagernr(r[col["lagernr"]])
        if not nr:
            continue
        wert = zu_zahl(r[col["ek"]])
        # groesster gefundener EK gewinnt (Dubletten im Export)
        if nr not in ek or wert > ek[nr]:
            ek[nr] = wert
        if col["kategorie"]:
            kat[nr] = str(r[col["kategorie"]] or "").strip()
        if col["marke"]:
            marke[nr] = str(r[col["marke"]] or "").strip()
        txt = " ".join(str(r[col[k]] or "") for k in ("lieferant", "liefertyp", "kategorie", "produkt")
                       if col[k])
        schrott[nr] = txt
    return ek, kat, marke, schrott


def lade_portal_preise(pfad: Path) -> dict:
    df = pd.read_excel(pfad, engine="openpyxl")
    col = {k: finde_spalte(df, v) for k, v in PORTAL_SPALTEN.items()}
    if col["lagernr"] is None or col["ek"] is None:
        raise SystemExit(f"FEHLER: In {pfad.name} fehlt Lager-Nr oder Buying_Price.")
    out = {}
    for nr, v in zip(df[col["lagernr"]], df[col["ek"]]):
        k = lagernr(nr)
        w = zu_zahl(v)
        if k and (k not in out or w > out[k]):
            out[k] = w
    return out


# --------------------------------------------------------------------------
def berechne(args) -> Ergebnis:
    stichtag = datetime.fromisoformat(args.stichtag).date()
    bestand_pfad = Path(args.bestand)
    print(f"→ AMM-Bestand: {bestand_pfad.name}")

    # Stichtags-Waechter: Dateiname BESTAND134_YYYYMMDD*.CSV
    m = re.search(r"(\d{8})", bestand_pfad.name)
    if m:
        try:
            datei_tag = datetime.strptime(m.group(1), "%Y%m%d").date()
            if datei_tag != stichtag and not args.erlaube_abweichenden_stand:
                raise SystemExit(
                    f"ABBRUCH: Die Bestandsliste ist vom {datei_tag.strftime('%d.%m.%Y')}, "
                    f"der Stichtag ist der {stichtag.strftime('%d.%m.%Y')}.\n"
                    f"         Der Warenwert waere damit nicht stichtagsrein.\n"
                    f"         Bitte BESTAND134 vom Stichtag verwenden "
                    f"(AMM-Mail 'Bestand (Elvinci.de GmbH) im Lager AMM vom ...').\n"
                    f"         (Bewusst trotzdem rechnen: --erlaube-abweichenden-stand)")
        except ValueError:
            pass

    bestand = lade_bestand(bestand_pfad)
    erg = Ergebnis(stichtag=str(stichtag), umfang=args.umfang,
                   quelle_bestand=bestand_pfad.name)
    erg.bestand_zeilen_gesamt = len(bestand)
    erg.status_verteilung = bestand["status"].value_counts().to_dict()

    erlaubt = UMFANG_STATUS[args.umfang]
    lager = bestand[bestand["status"].isin(erlaubt)].copy()
    fremd = set(bestand["status"]) - erlaubt - {""}
    if fremd and args.umfang == "gesamt":
        erg.warnungen.append(
            f"Unbekannte AMM-Status im Bestand: {sorted(fremd)} — nicht bewertet. "
            f"Bitte pruefen, ob sie physisch im Lager stehen.")

    vorher = len(lager)
    lager = lager.drop_duplicates(subset=["lagernr"], keep="first")
    erg.duplikate = vorher - len(lager)
    if erg.duplikate:
        erg.warnungen.append(f"{erg.duplikate} doppelte Lager-Nrn entfernt (keine Doppelzaehlung).")

    erg.geraete = len(lager)
    erg.menge = int(lager["menge"].sum())

    # ---------------- Preisquellen ----------------
    ek_odoo, kat_map, marke_map, schrott_txt = {}, {}, {}, {}
    if args.odoo:
        print(f"→ Odoo-Export: {Path(args.odoo).name}")
        ek_odoo, kat_map, marke_map, schrott_txt = lade_odoo_preise(Path(args.odoo))
        erg.quelle_odoo = Path(args.odoo).name
    ek_portal = {}
    if args.stock_analysis:
        print(f"→ Portal Stock-Analysis: {Path(args.stock_analysis).name}")
        ek_portal = lade_portal_preise(Path(args.stock_analysis))
        erg.quelle_portal = Path(args.stock_analysis).name
    if not ek_odoo and not ek_portal:
        raise SystemExit("FEHLER: Keine Preisquelle angegeben (--odoo und/oder --stock-analysis).")

    rx_schrott = re.compile(args.ek0_muster, re.IGNORECASE) if args.ek0_muster else None

    preis: dict[str, float] = {}
    quelle: dict[str, str] = {}
    offen: list[str] = []
    for nr in lager["lagernr"]:
        w = ek_odoo.get(nr, 0.0)
        if w > 0:
            preis[nr], quelle[nr] = w, "odoo"
            continue
        w = ek_portal.get(nr, 0.0)
        if w > 0:
            preis[nr], quelle[nr] = w, "portal"
            continue
        offen.append(nr)

    erg.n_odoo = sum(1 for q in quelle.values() if q == "odoo")
    erg.n_portal = sum(1 for q in quelle.values() if q == "portal")
    erg.ek_odoo = sum(v for k, v in preis.items() if quelle[k] == "odoo")
    erg.ek_portal = sum(v for k, v in preis.items() if quelle[k] == "portal")
    erg.ek_belegt = erg.ek_odoo + erg.ek_portal

    # ---------------- Durchschnitts-Fill ----------------
    bez_map = dict(zip(lager["lagernr"], lager["bezeichner"]))

    def mittelwerte(keymap: dict) -> dict:
        summe: dict[str, list[float]] = {}
        for nr, w in preis.items():
            k = keymap.get(nr)
            if k:
                summe.setdefault(k, []).append(w)
        return {k: sum(v) / len(v) for k, v in summe.items() if v}

    m_kat = mittelwerte(kat_map)
    m_marke = mittelwerte(marke_map)
    m_bez = mittelwerte(bez_map)
    m_global = (sum(preis.values()) / len(preis)) if preis else 0.0

    for nr in offen:
        txt = schrott_txt.get(nr, "") + " " + bez_map.get(nr, "")
        if rx_schrott and rx_schrott.search(txt):
            erg.n_schrott_ek0 += 1            # echter EK 0, kein Fill
            continue
        w = (m_kat.get(kat_map.get(nr, "")) or m_marke.get(marke_map.get(nr, ""))
             or m_bez.get(bez_map.get(nr, "")) or m_global)
        if w and w > 0:
            erg.ek_geschaetzt += float(w)
            erg.n_geschaetzt += 1

    erg.ek_gesamt = erg.ek_belegt + erg.ek_geschaetzt

    if erg.n_geschaetzt:
        anteil = erg.ek_geschaetzt / erg.ek_gesamt * 100 if erg.ek_gesamt else 0
        erg.warnungen.append(
            f"{erg.n_geschaetzt} Geraete ohne Einkaufspreis wurden mit Durchschnittswerten "
            f"belegt ({anteil:.1f} % des Warenwerts).")
    if erg.n_schrott_ek0:
        erg.warnungen.append(
            f"{erg.n_schrott_ek0} Geraete als Schrottware erkannt (Muster "
            f"'{args.ek0_muster}') und mit echtem EK 0 € bewertet.")
    return erg


# --------------------------------------------------------------------------
def drucke(erg: Ergebnis) -> None:
    b = "─" * 64
    tag = datetime.fromisoformat(erg.stichtag).strftime("%d.%m.%Y")
    umf = ("alles physisch im Lager, inkl. verkaufter Ware"
           if erg.umfang == "gesamt" else "nur freiverkaeufliche Ware (QE)")
    print(f"\n{b}\n  WARENWERT ZUM {tag} · EINKAUF (EK)\n  {umf}\n{b}")
    print(f"  Warenwert                  {eur(erg.ek_gesamt):>20}")
    print(f"  Geräte                     {de(erg.geraete):>20}")
    print(b)
    print(f"  EK aus Odoo                {eur(erg.ek_odoo):>20}   {de(erg.n_odoo)} Geräte")
    if erg.quelle_portal:
        print(f"  EK aus Portal (Restbest.)  {eur(erg.ek_portal):>20}   {de(erg.n_portal)} Geräte")
    print(f"  Ø-Schätzung (ohne EK)      {eur(erg.ek_geschaetzt):>20}   {de(erg.n_geschaetzt)} Geräte")
    print(f"  Schrottware (echt 0 €)     {'—':>20}   {de(erg.n_schrott_ek0)} Geräte")
    print(b)
    print(f"  AMM-Bestand gesamt         {de(erg.bestand_zeilen_gesamt)} Zeilen · "
          f"{', '.join(f'{k} {de(v)}' for k, v in sorted(erg.status_verteilung.items()))}")
    print(f"  Quelle Bestand             {erg.quelle_bestand}")
    if erg.quelle_odoo:
        print(f"  Quelle Preise              {erg.quelle_odoo}")
    if erg.warnungen:
        print(f"{b}\n  HINWEISE")
        for w in erg.warnungen:
            print(f"   · {w}")
    print(b + "\n")


def schreibe_json(erg: Ergebnis, pfad: Path) -> None:
    pfad.write_text(json.dumps(asdict(erg), indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"  → {pfad}")


def fortschreiben(erg: Ergebnis, pfad: Path) -> None:
    tag = datetime.fromisoformat(erg.stichtag).strftime("%d.%m.%Y")
    zeilen = pfad.read_text(encoding="utf-8").splitlines() if pfad.exists() else []
    if not zeilen:
        zeilen = ["Monatsende;Stück;EK-Wert"]
    kopf = zeilen[0]
    rest = [z for z in zeilen[1:] if z.strip() and not z.startswith(tag + ";")]
    rest.append(f"{tag};{erg.geraete};{erg.ek_gesamt:.0f}")
    rest.sort(key=lambda z: datetime.strptime(z.split(";")[0], "%d.%m.%Y"))
    pfad.write_text("\n".join([kopf] + rest) + "\n", encoding="utf-8")
    print(f"  → {pfad} (Reihe fortgeschrieben)")


def main(argv=None) -> int:
    p = argparse.ArgumentParser(
        description="Warenwert (EK) zum Stichtag — Reihe 'Warenwert zum Monatsende'.")
    p.add_argument("--stichtag", default="2026-08-31", help="ISO-Datum (Default 2026-08-31)")
    p.add_argument("--bestand", required=True,
                   help="BESTAND134_<JJJJMMTT>_*.CSV der AMM vom Stichtag")
    p.add_argument("--odoo", help="LosSerie (stock.lot)*.xlsx — Einkaufspreise")
    p.add_argument("--stock-analysis", help="Portal Stock-Analysis*.xlsx (Restbestand, Endstand 02.07.2026)")
    p.add_argument("--umfang", choices=list(UMFANG_STATUS), default="gesamt",
                   help="'gesamt' = QE+VS+AA (Reihenwert, Default) · "
                        "'freiverkaeuflich' = nur QE")
    p.add_argument("--serie", help="CSV der Monatsreihe, wird fortgeschrieben")
    p.add_argument("--json", dest="json_out", help="Pfad fuer die Faktendatei")
    p.add_argument("--ek0-muster", default=r"schrott",
                   help="Regex fuer Ware mit echtem EK 0 (Default: 'schrott')")
    p.add_argument("--erlaube-abweichenden-stand", action="store_true",
                   help="Auch rechnen, wenn die Bestandsliste nicht vom Stichtag ist")
    args = p.parse_args(argv)

    erg = berechne(args)
    drucke(erg)
    if args.json_out:
        schreibe_json(erg, Path(args.json_out))
    if args.serie:
        fortschreiben(erg, Path(args.serie))
    return 0


if __name__ == "__main__":
    sys.exit(main())
