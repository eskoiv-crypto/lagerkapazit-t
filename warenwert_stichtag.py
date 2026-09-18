#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Warenwert (EK) zum Stichtag — Fortschreibung der Reihe "Warenwert zum Monatsende".

Definition (intern festgelegt am 13./14.08.2026, Anlass: Abstimmung mit der
Steuerkanzlei): bewertet wird die Ware, die tatsaechlich im Lager liegt -
einschliesslich bereits an Kunden verkaufter, aber noch nicht ausgelieferter
Ware; nicht nur die freiverkaeufliche.

  => Warenwert(S) = SUMME Einkaufspreis ALLER Geraete, die am Stichtag S physisch
                    im Lager NH5 lagen - unabhaengig davon, ob bereits verkauft.

  Physische Wahrheit  = AMM-Bestandsliste BESTAND134 vom Stichtag
                        (Status QE = frei, VS = Versandpipeline, AA = auftragsgebunden)
  Preis               = Einkaufspreis aus dem Odoo-Export (stock.lot),
                        Join ueber die Lager-Nr
  fehlender EK        = Durchschnitts-EK (Produktkategorie > Marke > Bezeichner >
                        global) - so wie bisher gerechnet
  Schrott-Ware        = echter EK 0 EUR, KEIN Durchschnitts-Fill
                        (interne Korrektur vom 14.08.2026)

Bekannte Unschaerfen (intern festgehalten am 14.08.2026)
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

Ergebnisdateien (Reihe, Faktendatei) bleiben lokal - siehe .gitignore.
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

    ek_belegt: float = 0.0           # Odoo + Portal + Korrektur (echte Preise)
    ek_gesamt: float = 0.0           # Reihenwert

    # Nachtraegliche EK-Korrekturen je Lager-Nr (--ek-korrektur), z. B. AEG-
    # Neuklassifizierung oder nachgezogene Einkaufspreise nach Preisrecherche
    fassung: str | None = None
    quelle_korrektur: str | None = None
    n_korrektur: int = 0
    ek_korrektur: float = 0.0
    n_korrektur_nicht_im_bestand: int = 0
    korrektur_gruende: dict = field(default_factory=dict)   # Grund -> {n, ek, ek_vorher}
    # Pauschale Korrekturen ohne Los-Bezug (--pauschal-korrektur), z. B. eine
    # vom Backoffice benannte Summe; werden getrennt ausgewiesen
    pauschal_korrekturen: list = field(default_factory=list)   # [{grund, betrag}]
    ek_pauschal: float = 0.0
    # Bruecke zu einer frueheren Fassung desselben Stichtags (--vergleich)
    vergleich: dict | None = None

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


KORREKTUR_SPALTEN = {
    "lagernr": ["Lager-Nr", "Lager-Nr.", "Lager Nr.", "Lager-Code", "Lagernummer", "lagernr"],
    "ek":      ["EK", "Einkaufspreis", "EK neu", "EK_neu"],
    "grund":   ["Grund", "Kommentar", "Bemerkung", "Quelle"],
}


def lade_korrekturen(pfad: Path) -> dict[str, tuple[float, str]]:
    """Lot-genaue EK-Korrekturen: CSV (Semikolon oder Komma) oder XLSX mit den
    Spalten Lager-Nr;EK;Grund. -> {lagernr: (ek, grund)}. Der EK darf 0 sein
    (echter EK 0, z. B. Schrott) - dann wird NICHT mit dem Durchschnitt gefuellt."""
    if pfad.suffix.lower() in {".xlsx", ".xls"}:
        df = pd.read_excel(pfad, engine="openpyxl")
    else:
        text = pfad.read_text(encoding="utf-8-sig")
        sep = ";" if text.splitlines()[0].count(";") >= text.splitlines()[0].count(",") else ","
        df = pd.read_csv(pfad, sep=sep, dtype=str, encoding="utf-8-sig")
    col = {k: finde_spalte(df, v) for k, v in KORREKTUR_SPALTEN.items()}
    if col["lagernr"] is None or col["ek"] is None:
        raise SystemExit(f"FEHLER: In {pfad.name} fehlt 'Lager-Nr' oder 'EK'. "
                         f"Gefunden: {list(df.columns)}")
    out: dict[str, tuple[float, str]] = {}
    for _, r in df.iterrows():
        nr = lagernr(r[col["lagernr"]])
        if not nr or nr.lower() in {"nan", "none"}:
            continue
        grund = str(r[col["grund"]]).strip() if col["grund"] and str(r[col["grund"]]) not in {"nan", "None"} else "Korrektur"
        if nr in out:
            raise SystemExit(f"FEHLER: Lager-Nr {nr} steht doppelt in {pfad.name} - "
                             f"bitte bereinigen, sonst ist die Korrektur nicht eindeutig.")
        out[nr] = (zu_zahl(r[col["ek"]]), grund)
    return out


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

    korr: dict[str, tuple[float, str]] = {}
    if args.ek_korrektur:
        print(f"→ EK-Korrekturen: {Path(args.ek_korrektur).name}")
        korr = lade_korrekturen(Path(args.ek_korrektur))
        erg.quelle_korrektur = Path(args.ek_korrektur).name
    erg.fassung = args.fassung

    rx_schrott = re.compile(args.ek0_muster, re.IGNORECASE) if args.ek0_muster else None

    preis: dict[str, float] = {}
    quelle: dict[str, str] = {}
    offen: list[str] = []
    im_bestand = set(lager["lagernr"])
    for nr in lager["lagernr"]:
        if nr in korr:                     # 1. nachtraegliche Korrektur = echter EK
            w, grund = korr[nr]
            preis[nr], quelle[nr] = w, "korrektur"
            g = erg.korrektur_gruende.setdefault(grund, {"n": 0, "ek": 0.0, "ek_vorher_odoo": 0.0,
                                                          "n_vorher_ohne_ek": 0})
            g["n"] += 1
            g["ek"] += w
            vorher = ek_odoo.get(nr, 0.0) or ek_portal.get(nr, 0.0)
            g["ek_vorher_odoo"] += vorher
            if vorher <= 0:
                g["n_vorher_ohne_ek"] += 1
            continue
        w = ek_odoo.get(nr, 0.0)           # 2. Odoo
        if w > 0:
            preis[nr], quelle[nr] = w, "odoo"
            continue
        w = ek_portal.get(nr, 0.0)         # 3. Portal-Restbestand
        if w > 0:
            preis[nr], quelle[nr] = w, "portal"
            continue
        offen.append(nr)                   # 4. Durchschnitts-Fill / Schrott

    erg.n_korrektur_nicht_im_bestand = sum(1 for nr in korr if nr not in im_bestand)
    if erg.n_korrektur_nicht_im_bestand:
        erg.warnungen.append(
            f"{erg.n_korrektur_nicht_im_bestand} Lager-Nrn aus der Korrekturliste stehen nicht im "
            f"AMM-Bestand vom Stichtag (Umfang '{args.umfang}') und wurden nicht bewertet.")

    erg.n_odoo = sum(1 for q in quelle.values() if q == "odoo")
    erg.n_portal = sum(1 for q in quelle.values() if q == "portal")
    erg.n_korrektur = sum(1 for q in quelle.values() if q == "korrektur")
    erg.ek_odoo = sum(v for k, v in preis.items() if quelle[k] == "odoo")
    erg.ek_portal = sum(v for k, v in preis.items() if quelle[k] == "portal")
    erg.ek_korrektur = sum(v for k, v in preis.items() if quelle[k] == "korrektur")
    erg.ek_belegt = erg.ek_odoo + erg.ek_portal + erg.ek_korrektur
    if erg.n_korrektur:
        erg.warnungen.append(
            f"{erg.n_korrektur} Geraete mit nachtraeglich korrigiertem Einkaufspreis "
            f"(Σ {eur(erg.ek_korrektur)}) aus {erg.quelle_korrektur}; die Korrektur ersetzt "
            f"Odoo-Preis bzw. Durchschnittswert.")

    # ---------------- Durchschnitts-Fill ----------------
    bez_map = dict(zip(lager["lagernr"], lager["bezeichner"]))

    def mittelwerte(keymap: dict) -> dict:
        summe: dict[str, list[float]] = {}
        for nr, w in preis.items():
            if w <= 0:                      # echte 0-EKs (Schrott-Korrektur) ziehen keinen Ø nach unten
                continue
            k = keymap.get(nr)
            if k:
                summe.setdefault(k, []).append(w)
        return {k: sum(v) / len(v) for k, v in summe.items() if v}

    m_kat = mittelwerte(kat_map)
    m_marke = mittelwerte(marke_map)
    m_bez = mittelwerte(bez_map)
    positiv = [w for w in preis.values() if w > 0]
    m_global = (sum(positiv) / len(positiv)) if positiv else 0.0

    fill_quelle: dict[str, str] = {}
    for nr in offen:
        txt = schrott_txt.get(nr, "") + " " + bez_map.get(nr, "")
        if rx_schrott and rx_schrott.search(txt):
            erg.n_schrott_ek0 += 1            # echter EK 0, kein Fill
            preis[nr], quelle[nr] = 0.0, "schrott"
            continue
        if m_kat.get(kat_map.get(nr, "")):
            w, q = m_kat[kat_map[nr]], "Ø Kategorie"
        elif m_marke.get(marke_map.get(nr, "")):
            w, q = m_marke[marke_map[nr]], "Ø Marke"
        elif m_bez.get(bez_map.get(nr, "")):
            w, q = m_bez[bez_map[nr]], "Ø Bezeichner"
        else:
            w, q = m_global, "Ø global"
        if w and w > 0:
            erg.ek_geschaetzt += float(w)
            erg.n_geschaetzt += 1
            preis[nr], quelle[nr], fill_quelle[nr] = float(w), "schaetzung", q

    # ---------------- Pauschale Korrekturen (ohne Los-Bezug) ----------------
    for eintrag in (args.pauschal_korrektur or []):
        if ";" not in eintrag:
            raise SystemExit(f"FEHLER: --pauschal-korrektur erwartet 'Betrag;Grund', bekommen: {eintrag!r}")
        betrag_s, grund = eintrag.split(";", 1)
        betrag = zu_zahl(betrag_s)
        if not grund.strip():
            raise SystemExit("FEHLER: --pauschal-korrektur ohne Grund ist nicht zulaessig.")
        erg.pauschal_korrekturen.append({"grund": grund.strip(), "betrag": betrag})
        erg.ek_pauschal += betrag
    if erg.pauschal_korrekturen:
        erg.warnungen.append(
            f"{len(erg.pauschal_korrekturen)} Pauschalkorrektur(en) ohne Los-Bezug, Σ {eur(erg.ek_pauschal)}: "
            + " · ".join(f"{p['grund']} ({p['betrag']:+,.0f} €)".replace(",", ".")
                         for p in erg.pauschal_korrekturen)
            + ". Nicht je Lager-Nr belegt; Ueberschneidung mit der Ø-Schaetzung ist nicht ausgeschlossen.")

    erg.ek_gesamt = erg.ek_belegt + erg.ek_geschaetzt + erg.ek_pauschal

    # ---------------- Geraeteliste (Pruefpfad je Lager-Nr) ----------------
    if args.geraete_liste:
        zeilen = []
        for _, r in lager.iterrows():
            nr = r["lagernr"]
            zeilen.append({
                "Lager-Nr": nr, "AMM-Status": r["status"], "Bezeichner (AMM)": r["bezeichner"],
                "Menge": r["menge"],
                "Produktkategorie (Odoo)": kat_map.get(nr, ""), "Marke (Odoo)": marke_map.get(nr, ""),
                "Lieferant/-typ (Odoo)": schrott_txt.get(nr, ""),
                "EK Odoo": ek_odoo.get(nr, ""), "EK Portal": ek_portal.get(nr, ""),
                "EK Korrektur": korr[nr][0] if nr in korr else "",
                "Korrektur-Grund": korr[nr][1] if nr in korr else "",
                "Preisquelle": quelle.get(nr, "ohne"), "Fill-Regel": fill_quelle.get(nr, ""),
                "EK bewertet": preis.get(nr, 0.0),
            })
        out = Path(args.geraete_liste)
        pd.DataFrame(zeilen).to_excel(out, index=False)
        print(f"  → {out} (Geraeteliste, {len(zeilen)} Zeilen)")

    # ---------------- Bruecke zu einer frueheren Fassung ----------------
    if args.vergleich:
        alt = json.loads(Path(args.vergleich).read_text(encoding="utf-8"))
        if alt.get("stichtag") != erg.stichtag or alt.get("umfang", "gesamt") != erg.umfang:
            raise SystemExit(f"FEHLER: --vergleich {Path(args.vergleich).name} gehoert zu Stichtag "
                             f"{alt.get('stichtag')} / Umfang {alt.get('umfang')}, nicht zu "
                             f"{erg.stichtag} / {erg.umfang}.")
        erg.vergleich = {
            "quelle": Path(args.vergleich).name,
            "fassung_alt": alt.get("fassung"),
            "geraete_alt": alt.get("geraete"),
            "ek_gesamt_alt": alt.get("ek_gesamt"),
            "ek_belegt_alt": alt.get("ek_belegt"),
            "n_geschaetzt_alt": alt.get("n_geschaetzt"),
            "ek_geschaetzt_alt": alt.get("ek_geschaetzt"),
            "ek_pauschal_alt": alt.get("ek_pauschal", 0.0),
            "delta_ek_gesamt": erg.ek_gesamt - float(alt.get("ek_gesamt") or 0),
            "delta_geraete": erg.geraete - int(alt.get("geraete") or 0),
        }
        if erg.vergleich["delta_geraete"]:
            erg.warnungen.append(
                f"Geraetezahl weicht von der Vergleichsfassung ab ({erg.vergleich['delta_geraete']:+d}) - "
                f"bei gleicher Bestandsliste darf das nicht sein; bitte Quellen pruefen.")

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
    if erg.fassung:
        print(f"  Fassung: {erg.fassung}")
    print(f"  Warenwert                  {eur(erg.ek_gesamt):>20}")
    print(f"  Geräte                     {de(erg.geraete):>20}")
    print(b)
    print(f"  EK aus Odoo                {eur(erg.ek_odoo):>20}   {de(erg.n_odoo)} Geräte")
    if erg.quelle_portal:
        print(f"  EK aus Portal (Restbest.)  {eur(erg.ek_portal):>20}   {de(erg.n_portal)} Geräte")
    if erg.quelle_korrektur:
        print(f"  EK korrigiert (Liste)      {eur(erg.ek_korrektur):>20}   {de(erg.n_korrektur)} Geräte")
        for grund, g in erg.korrektur_gruende.items():
            print(f"     · {grund[:40]:<40} {de(g['n']):>5} Ger. · neu {eur(g['ek'])} · "
                  f"vorher Odoo {eur(g['ek_vorher_odoo'])} ({g['n_vorher_ohne_ek']} ohne EK)")
    print(f"  Ø-Schätzung (ohne EK)      {eur(erg.ek_geschaetzt):>20}   {de(erg.n_geschaetzt)} Geräte")
    print(f"  Schrottware (echt 0 €)     {'—':>20}   {de(erg.n_schrott_ek0)} Geräte")
    for pk in erg.pauschal_korrekturen:
        print(f"  Pauschal: {pk['grund'][:48]:<48} {pk['betrag']:>+12,.0f} €".replace(",", "."))
    print(b)
    if erg.vergleich:
        v = erg.vergleich
        print(f"  BRÜCKE zur Fassung '{v.get('fassung_alt') or v['quelle']}'")
        print(f"    Warenwert alt            {eur(v['ek_gesamt_alt'] or 0):>20}   {de(v['geraete_alt'] or 0)} Geräte")
        print(f"    Warenwert neu            {eur(erg.ek_gesamt):>20}   {de(erg.geraete)} Geräte")
        print(f"    Δ                        {v['delta_ek_gesamt']:>+20,.0f} €".replace(",", "."))
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
    p.add_argument("--ek-korrektur",
                   help="CSV/XLSX 'Lager-Nr;EK;Grund' - lot-genaue EK-Korrekturen, die Odoo-Preis "
                        "und Durchschnitts-Fill ersetzen (z. B. AEG-Neuklassifizierung, "
                        "nachgezogene Preise nach Preisrecherche)")
    p.add_argument("--pauschal-korrektur", action="append", metavar="BETRAG;GRUND",
                   help="Pauschale Korrektur ohne Los-Bezug, mehrfach moeglich, z. B. "
                        "'12000;AEG Electrolux echter EK (Aussage Backoffice)'. Wird getrennt "
                        "ausgewiesen und geht in den Warenwert ein.")
    p.add_argument("--fassung", help="Kennung der Fassung, z. B. '2 (korrigiert 18.09.2026)'")
    p.add_argument("--vergleich",
                   help="Faktendatei einer frueheren Fassung desselben Stichtags -> Bruecke alt/neu")
    p.add_argument("--geraete-liste",
                   help="XLSX mit einer Zeile je Lager-Nr (Preisquelle, EK, Korrektur) als Pruefpfad")
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
