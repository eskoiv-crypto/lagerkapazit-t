#!/usr/bin/env python3
"""
WA-Pipeline -> Arbeitsliste Terminierung / Kommissionierplanung.

Liest den Text-Export des Sheets 20_WA_PIPELINE (bzw. der Datei
'Abhol-und_Liefertermine_Tagesaktuell.xlsx', Tabelle1) und kippt die offenen
Vorgaenge in Buckets, die man abarbeiten kann:

  A  kommissioniert + Termin verstrichen  -> nicht abgeholt
  B  kommissioniert, kein Termin          -> terminieren
  C  kommissioniert, Termin in der Zukunft-> nur beobachten
  D  Kommissionierung offen/ueberfaellig
  E  storniert                            -> aus der Pipeline nehmen

Der Export ist tab-separiert; Notizen laufen ueber Folgezeilen ohne
Auftragsnummer, die hier an den Vorgaenger angehaengt werden.

Aufruf:  python3 parse_wa_pipeline.py <export.txt> [--stichtag JJJJ-MM-TT] [--csv out.csv]
"""
import argparse, csv, re, sys
from collections import Counter, defaultdict
from datetime import date, datetime

COLS = [
    "KW", "ID", "UebermitteltAMM", "Auftragsnr", "Kunde", "Geraete",
    "Kommissioniertag", "Versandart", "Status", "NotizAMM", "NotizELVINCI",
    "AnmeldedatumAMM", "KommAbgeschlossenAMM", "Paletten", "EW100x80",
    "EW120x60", "EUR120x80", "EW120x80", "EW80x80", "LDM",
    "VersandAnmeldung", "GeplantesVersanddatum", "Anlieferdatum", "TageDiff",
]

BUCKETS = {
    "A": "Kommissioniert + Termin verstrichen -> nicht abgeholt",
    "B": "Kommissioniert, kein Termin -> terminieren",
    "C": "Kommissioniert, Termin steht (Zukunft)",
    "D": "Kommissionierung offen / ueberfaellig",
    "E": "Storniert -> aus der Pipeline nehmen",
    "F": "Sonstige / unvollstaendig",
}


def parse_date(raw):
    """'21.08.2026 00:00' -> date. Jahresdreher (2062) werden korrigiert."""
    raw = (raw or "").strip().split(" ")[0]
    m = re.match(r"^(\d{1,2})\.(\d{1,2})\.(\d{2,4})$", raw)
    if not m:
        return None
    day, month, year = (int(g) for g in m.groups())
    if year < 100:
        year += 2000
    if year > 2100:          # Tippfehler wie 10.08.2062
        year = int(str(year)[:2] + str(year)[3:]) if len(str(year)) == 4 else 2026
    try:
        return date(year, month, day)
    except ValueError:
        return None


def parse_int(raw):
    raw = (raw or "").strip().replace(".", "").replace(",", ".")
    try:
        return int(float(raw))
    except ValueError:
        return 0


def parse_float(raw):
    raw = (raw or "").strip().replace(",", ".")
    try:
        return float(raw)
    except ValueError:
        return 0.0


def load(path):
    lines = open(path, encoding="utf-8").read().split("\n")
    try:
        start = next(i for i, l in enumerate(lines) if l.startswith("KW (auto)")) + 1
    except StopIteration:
        sys.exit(f"Kopfzeile 'KW (auto)' in {path} nicht gefunden.")
    end = next((i for i, l in enumerate(lines) if l.startswith("Formulas:")), len(lines))

    records = []
    for line in lines[start:end]:
        cells = line.split("\t")
        cells += [""] * (len(COLS) - len(cells))
        row = {key: cells[i].strip() for i, key in enumerate(COLS)}

        if not row["Auftragsnr"]:
            # Folgezeile: Notiz gehoert zum vorherigen Auftrag
            if records:
                spill = " ".join(c.strip() for c in cells
                                 if c.strip() and c.strip() != "… Neu")
                if spill:
                    records[-1]["NotizELVINCI"] = (
                        records[-1]["NotizELVINCI"] + " | " + spill).strip(" |")
            continue

        row["d_komm"] = parse_date(row["Kommissioniertag"])
        row["d_kommfertig"] = parse_date(row["KommAbgeschlossenAMM"])
        row["d_versand"] = parse_date(row["GeplantesVersanddatum"])
        row["d_anlief"] = parse_date(row["Anlieferdatum"])
        row["n_geraete"] = parse_int(row["Geraete"])
        row["n_paletten"] = parse_int(row["Paletten"])
        row["n_ldm"] = parse_float(row["LDM"])
        row["storniert"] = bool(re.search(
            r"storn", (row["NotizAMM"] + " " + row["NotizELVINCI"]).lower()))
        records.append(row)
    return records


def is_open(row):
    """Status faengt mit ● / ◐ an = bereits versendet."""
    return not row["Status"].startswith(("●", "◐"))


def bucket(row, stichtag):
    if row["storniert"]:
        return "E"
    fertig = row["d_kommfertig"] is not None
    termin = row["d_versand"]
    if fertig and termin:
        return "A" if termin < stichtag else "C"
    if fertig:
        return "B"
    if row["d_komm"] and row["d_komm"] < stichtag:
        return "D"
    return "F"


def sammelverladung(row, alle):
    """Auftragsnummern, mit denen dieser Auftrag zusammen verladen werden soll."""
    text = row["NotizAMM"] + " " + row["NotizELVINCI"]
    refs = set(re.findall(r"\b(S\d{4,6}|AU\d{10,})\b", text)) - {row["Auftragsnr"]}
    return sorted(refs)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("export")
    ap.add_argument("--stichtag", default=date.today().isoformat())
    ap.add_argument("--csv")
    args = ap.parse_args()
    stichtag = datetime.fromisoformat(args.stichtag).date()

    records = load(args.export)
    offen = [r for r in records if is_open(r)]

    print(f"Datensaetze gesamt : {len(records)}")
    print(f"davon offen        : {len(offen)}   (Stichtag {stichtag:%d.%m.%Y})\n")

    # Warnung: Dashboard-Formeln filtern auf LEFT(Auftragsnr,2)="AU"
    au = sum(1 for r in records if r["Auftragsnr"].upper().startswith("AU"))
    s_nr = len(records) - au
    aug = [r for r in records if r["d_komm"] and r["d_komm"] >= date(2026, 8, 1)]
    aug_au = sum(1 for r in aug if r["Auftragsnr"].upper().startswith("AU"))
    print(f"Auftragsnummern    : {au}x AU..., {s_nr}x S...")
    if aug and aug_au == 0:
        print("  ACHTUNG: seit 08/2026 ausschliesslich S-Nummern. Alle Dashboard-\n"
              "  Formeln mit LEFT(Auftragsnr,2)=\"AU\" liefern dadurch 0.\n")

    grouped = defaultdict(list)
    for row in offen:
        grouped[bucket(row, stichtag)].append(row)

    for key in "ABDCEF":
        rows = grouped.get(key)
        if not rows:
            continue
        rows.sort(key=lambda r: (r["d_versand"] or date(2099, 1, 1),
                                 r["d_komm"] or date(2099, 1, 1)))
        print(f"--- {key} · {BUCKETS[key]} --- "
              f"{len(rows)} Auftraege · {sum(r['n_geraete'] for r in rows)} Geraete "
              f"· {sum(r['n_paletten'] for r in rows)} Paletten")
        for r in rows:
            verzug = (stichtag - r["d_versand"]).days if r["d_versand"] else 0
            mit = sammelverladung(r, records)
            print(f"  {r['Auftragsnr']:<9} {r['Kunde'][:28]:<28} "
                  f"{r['n_geraete']:>4} Ger  "
                  f"Komm {str(r['d_komm'] or '-'):<10} "
                  f"fertig {str(r['d_kommfertig'] or '-'):<10} "
                  f"Termin {str(r['d_versand'] or '-'):<10}"
                  + (f" ({verzug} Tg ueberfaellig)" if verzug > 0 else "")
                  + (f"  [mit {', '.join(mit)}]" if mit else ""))
        print()

    if args.csv:
        with open(args.csv, "w", newline="", encoding="utf-8-sig") as fh:
            w = csv.writer(fh, delimiter=";")
            w.writerow(["Bucket", "Auftragsnr", "Kunde", "Geraete", "Paletten", "LDM",
                        "Versandart", "Kommissioniertag", "KommFertig", "Termin",
                        "TageUeberfaellig", "Anmeldung", "Sammelverladung",
                        "NotizAMM", "NotizELVINCI", "StatusSheet"])
            for key in "ABDCEF":
                for r in grouped.get(key, []):
                    verzug = (stichtag - r["d_versand"]).days if r["d_versand"] else ""
                    w.writerow([key, r["Auftragsnr"], r["Kunde"].strip(), r["n_geraete"],
                                r["n_paletten"], r["n_ldm"], r["Versandart"],
                                r["Kommissioniertag"], r["KommAbgeschlossenAMM"],
                                r["GeplantesVersanddatum"], verzug,
                                r["VersandAnmeldung"],
                                ", ".join(sammelverladung(r, records)),
                                r["NotizAMM"], r["NotizELVINCI"], r["Status"]])
        print(f"CSV geschrieben: {args.csv}")


if __name__ == "__main__":
    main()
