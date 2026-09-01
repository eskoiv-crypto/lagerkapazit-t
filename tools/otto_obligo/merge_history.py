#!/usr/bin/env python3
"""Otto-Obligo-Cockpit: eingebettete Historie (HIST_CSV) mit neuen Agicap-Exporten erweitern.

Das Cockpit (Otto-Obligo-Cockpit.html) traegt die Otto-Rechnungshistorie als
JS-Konstante `const HIST_CSV="..."` im Markup. Sie speist das Diagramm
"Otto-Volumen je Monat" und wird beim Oeffnen automatisch geladen.

Dieses Skript liest die eingebettete Historie, mischt beliebig viele frische
Agicap-CSV-Exporte hinzu und schreibt das Cockpit mit erweiterter Historie neu.

  python3 tools/otto_obligo/merge_history.py \
      --cockpit Otto-Obligo-Cockpit.html \
      --out     Otto-Obligo-Cockpit.html \
      supplier_invoices_*.csv

Regeln:
  * Identitaet einer Rechnung = normalisierte Rechnungsnummer (gleiche Logik wie
    refKey() im Cockpit: 1001EO... und 1001E0... sind dieselbe Rechnung),
    ersatzweise die Raten-ID.
  * Bei Dubletten gewinnt der neue Export - er traegt den frischeren Status
    (z. B. "Zu bezahlen" -> "Bezahlt").
  * Zeilen, die nur in der alten Historie stehen, bleiben erhalten. Agicap
    exportiert je nach Filter nicht immer alle Status.
  * Spaltennamen und Zahlungsmethode werden auf das Schema der eingebetteten
    Historie normalisiert, damit der Bestand homogen bleibt.
"""
import argparse
import csv
import io
import json
import re
import sys
from collections import Counter

# Schema der eingebetteten Historie. Neue Agicap-Exporte benennen Spalte 4 um.
HIST_FIELDS = [
    "Typ", "Raten-ID", "Rechnungs-ID", "Rechnungs-/Ratenbezeichnung",
    "Rechnungsnummer", "Status", "Begünstigter", "Rechnungsdatum",
    "Fälligkeitsdatum", "Zahlungsdatum", "Rechnungsbetrag exkl. Steuern",
    "Rechnungsbetrag inkl. Steuern", "Ratenbetrag inkl. Steuern", "Währung",
    "Zahlungsmethode", "Bestellnummer", "IBAN", "Abteilung", "Ausgabenarten",
]
FIELD_ALIASES = {"Titel der Rechnung/Rate": "Rechnungs-/Ratenbezeichnung"}
# Agicap exportiert dieselbe Zahlungsart mal so, mal so.
PAYMENT_ALIASES = {"Banküberweisung": "Überweisung"}

HIST_DECL = 'const HIST_CSV="'


def find_literal(html):
    """Position des HIST_CSV-Stringliterals (ohne Anfuehrungszeichen) finden."""
    start = html.find(HIST_DECL)
    if start < 0:
        raise SystemExit("HIST_CSV nicht im Cockpit gefunden - falsche Datei?")
    start += len(HIST_DECL)
    i = start
    while i < len(html):
        if html[i] == "\\":
            i += 2
            continue
        if html[i] == '"':
            return start, i
        i += 1
    raise SystemExit("HIST_CSV-Literal ist nicht terminiert.")


def read_csv_text(text):
    return list(csv.DictReader(io.StringIO(text.lstrip("﻿"))))


def normalize(row):
    out = {}
    for key, val in row.items():
        if key is None:
            continue
        out[FIELD_ALIASES.get(key, key)] = (val or "").strip()
    out["Zahlungsmethode"] = PAYMENT_ALIASES.get(
        out.get("Zahlungsmethode", ""), out.get("Zahlungsmethode", "")
    )
    return {f: out.get(f, "") for f in HIST_FIELDS}


def ref_key(row):
    """Spiegelt refKey() aus dem Cockpit: 1001EO... == 1001E0..."""
    m = re.search(r"1001E[O0]?\d+", row.get("Rechnungsnummer", ""), re.I)
    if m:
        return m.group(0).upper().replace("1001EO", "1001E0")
    return "raten:" + row.get("Raten-ID", "")


def sort_key(row):
    d = row.get("Rechnungsdatum", "")
    m = re.match(r"^(\d{2})-(\d{2})-(\d{4})$", d)
    iso = (m.group(3), m.group(2), m.group(1)) if m else ("9999", "99", "99")
    return iso + (ref_key(row),)


def month_counts(rows):
    c = Counter()
    for r in rows:
        m = re.match(r"^\d{2}-(\d{2})-(\d{4})$", r.get("Rechnungsdatum", ""))
        if m:
            c[f"{m.group(2)}-{m.group(1)}"] += 1
    return c


def to_csv_text(rows):
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=HIST_FIELDS, lineterminator="\n",
                       quoting=csv.QUOTE_MINIMAL)
    w.writeheader()
    w.writerows(rows)
    return "﻿" + buf.getvalue()


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("exports", nargs="+", help="Agicap-CSV-Export(e)")
    ap.add_argument("--cockpit", required=True, help="Otto-Obligo-Cockpit.html (Basis)")
    ap.add_argument("--out", required=True, help="Zieldatei")
    args = ap.parse_args()

    html = open(args.cockpit, encoding="utf-8").read()
    lo, hi = find_literal(html)
    old = [normalize(r) for r in read_csv_text(json.loads('"' + html[lo:hi] + '"'))]

    new = []
    for path in args.exports:
        rows = [normalize(r) for r in read_csv_text(open(path, encoding="utf-8-sig").read())]
        print(f"  gelesen: {path} -> {len(rows)} Zeilen")
        new += rows

    merged = {ref_key(r): r for r in old}
    before = set(merged)
    updated = added = 0
    for r in new:
        k = ref_key(r)
        if k in before:
            if merged[k] != r:
                updated += 1
        else:
            added += 1
        merged[k] = r  # neuer Export gewinnt: frischerer Status
    rows = sorted(merged.values(), key=sort_key)

    kept = len(before - {ref_key(r) for r in new})
    print(f"\nHistorie: {len(old)} -> {len(rows)} Rechnungen")
    print(f"  neu aufgenommen : {added}")
    print(f"  aktualisiert    : {updated} (u. a. Statuswechsel)")
    print(f"  nur alt, behalten: {kept}")
    print(f"  Status          : {dict(Counter(r['Status'] for r in rows))}")
    if rows:
        print(f"  Zeitraum        : {rows[0]['Rechnungsdatum']} bis {rows[-1]['Rechnungsdatum']}")
    old_m, new_m = month_counts(old), month_counts(rows)
    print("\n  Monat     alt   neu")
    for m in sorted(set(old_m) | set(new_m)):
        mark = "  <-" if new_m[m] != old_m[m] else ""
        print(f"  {m}  {old_m[m]:4d}  {new_m[m]:4d}{mark}")

    literal = json.dumps(to_csv_text(rows), ensure_ascii=False)[1:-1]
    out_html = html[:lo] + literal + html[hi:]
    with open(args.out, "w", encoding="utf-8") as fh:
        fh.write(out_html)
    print(f"\ngeschrieben: {args.out} ({len(out_html):,} Zeichen)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
