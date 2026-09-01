#!/usr/bin/env python3
"""Otto-Historie auffrischen — die komplette Kette, lokal auf dem Arbeitsplatz.

Setzt die Prozedur aus `_build-kit/REFRESH-Historie.md` in ein Kommando um:

  1. neue Agicap-Register-CSV(s) in `hist_register.csv` mischen (Backup vorher)
  2. `node build.js` im `_build-kit`-Ordner  -> Otto-Obligo-Cockpit.html
  3. gebautes Cockpit pruefen (Historie decodierbar, Zeilenzahl plausibel)
  4. in alle Zielkopien verteilen

Aufruf (Ordner werden selbst gefunden):

  python3 refresh_local.py supplier_invoices_*.csv
  python3 refresh_local.py --dry-run supplier_invoices_*.csv

Laeuft nur dort, wo der OneDrive-Ordner tatsaechlich liegt - also auf dem
Arbeitsplatz, nicht in einer Cloud-Sitzung. Ohne Node greift automatisch der
Direkt-Patch des eingebetteten Literals; das Ergebnis ist dasselbe.
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from merge_history import (  # noqa: E402
    find_literal, normalize, read_csv_text, ref_key, sort_key, to_csv_text,
)

REGISTER = "hist_register.csv"
COCKPIT = "Otto-Obligo-Cockpit.html"
BUILD = "build.js"

# Zielkopien laut REFRESH-Historie.md, relativ zu einem OneDrive-Stammordner.
# Der Ordnername "Digital Experience - KI-Tools" existiert mit Bindestrich und
# mit Gedankenstrich - beide Schreibweisen werden probiert.
TARGET_PATTERNS = [
    "Digital Experience*KI-Tools/Otto_Obligo_View/" + COCKPIT,
    "Dokumente/Otto-Obligo-Cockpit/" + COCKPIT,
    "Dokumente/" + COCKPIT,
]


def onedrive_roots():
    """OneDrive-Stammordner aus der Umgebung, sonst unterhalb des Profils."""
    roots = []
    for var in ("OneDriveCommercial", "OneDriveConsumer", "OneDrive"):
        val = os.environ.get(var)
        if val and Path(val).is_dir():
            roots.append(Path(val))
    home = Path.home()
    if home.is_dir():
        roots += [p for p in home.glob("OneDrive*") if p.is_dir()]
    seen, out = set(), []
    for r in roots:
        rp = r.resolve()
        if rp not in seen:
            seen.add(rp)
            out.append(rp)
    return out


def find_build_kit(explicit=None):
    """Den _build-kit-Ordner finden - erkannt an hist_register.csv + build.js."""
    if explicit:
        p = Path(explicit).expanduser().resolve()
        if not (p / REGISTER).is_file():
            raise SystemExit(f"In {p} liegt keine {REGISTER}.")
        return p
    for root in onedrive_roots():
        for cand in root.rglob("_build-kit"):
            if (cand / REGISTER).is_file() and (cand / BUILD).is_file():
                return cand.resolve()
    raise SystemExit(
        "_build-kit nicht gefunden. Ordner mit --build-kit angeben, z. B.\n"
        '  --build-kit "%USERPROFILE%\\OneDrive - elvinci.de GmbH\\'
        'Digital Experience - KI-Tools\\Otto_Obligo_View\\_build-kit"'
    )


def find_targets(build_kit):
    """Zielkopien auflisten. Ein noch fehlender Zielort zaehlt mit - die
    Prozedur nennt ihn, also wird er angelegt statt uebersprungen."""
    targets, seen = [], set()
    for root in onedrive_roots():
        for pattern in TARGET_PATTERNS:
            for hit in root.glob(pattern):
                if hit.resolve() not in seen:
                    seen.add(hit.resolve())
                    targets.append(hit)
            # Zielordner vorhanden, Datei fehlt -> trotzdem als Ziel fuehren
            parent_pat = pattern.rsplit("/", 1)[0]
            for folder in root.glob(parent_pat):
                cand = folder / COCKPIT
                if folder.is_dir() and cand.resolve() not in seen:
                    seen.add(cand.resolve())
                    targets.append(cand)
    return [t for t in targets if t.resolve() != (build_kit / COCKPIT).resolve()]


def merge_register(build_kit, exports, dry_run):
    """Neue Exporte in hist_register.csv mischen. Gibt (Text, Bilanz) zurueck."""
    reg = build_kit / REGISTER
    old = [normalize(r) for r in read_csv_text(reg.read_text(encoding="utf-8-sig"))]

    new = []
    for path in exports:
        rows = [normalize(r) for r in read_csv_text(
            Path(path).read_text(encoding="utf-8-sig"))]
        print(f"  gelesen: {Path(path).name} -> {len(rows)} Zeilen")
        new += rows
    if not new:
        raise SystemExit("Keine Zeilen in den angegebenen Exporten.")

    merged = {ref_key(r): r for r in old}
    before = set(merged)
    added = updated = 0
    for r in new:
        k = ref_key(r)
        if k in before:
            updated += r != merged[k]
        else:
            added += 1
        merged[k] = r  # neuer Export gewinnt: frischerer Status
    rows = sorted(merged.values(), key=sort_key)
    text = to_csv_text(rows)

    print(f"\n  Register: {len(old)} -> {len(rows)} Rechnungen "
          f"(+{added} neu, {updated} aktualisiert)")
    print(f"  Zeitraum: {rows[0]['Rechnungsdatum']} bis {rows[-1]['Rechnungsdatum']}")

    if not dry_run:
        stamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
        backup = reg.with_name(f"{REGISTER}.{stamp}.bak")
        shutil.copy2(reg, backup)
        reg.write_text(text, encoding="utf-8", newline="")
        print(f"  geschrieben: {reg.name}  (Backup: {backup.name})")
    return text, len(rows)


def run_build(build_kit, register_text, dry_run):
    """`node build.js` ausfuehren; ohne Node das Literal direkt patchen."""
    cockpit = build_kit / COCKPIT
    if dry_run:
        print("\n  [dry-run] node build.js wird nicht ausgefuehrt")
        return None

    node = shutil.which("node")
    if node:
        before = cockpit.stat().st_mtime if cockpit.is_file() else 0
        print(f"\n  {node} {BUILD} (in {build_kit.name})")
        res = subprocess.run([node, BUILD], cwd=build_kit,
                             capture_output=True, text=True)
        if res.stdout.strip():
            print("    " + res.stdout.strip().replace("\n", "\n    "))
        if res.returncode != 0:
            print("    " + (res.stderr.strip() or "(keine Meldung)"))
            raise SystemExit(f"build.js endete mit Code {res.returncode} - "
                             "nichts verteilt, Register-Backup liegt daneben.")
        if not cockpit.is_file() or cockpit.stat().st_mtime <= before:
            raise SystemExit(f"build.js hat {COCKPIT} nicht neu geschrieben - "
                             "nichts verteilt.")
        return cockpit

    # Fallback: dasselbe Ergebnis ohne Node, indem nur HIST_CSV ersetzt wird.
    print("\n  node nicht gefunden -> Direkt-Patch des HIST_CSV-Literals")
    html = cockpit.read_text(encoding="utf-8")
    lo, hi = find_literal(html)
    literal = json.dumps(register_text, ensure_ascii=False)[1:-1]
    cockpit.write_text(html[:lo] + literal + html[hi:], encoding="utf-8")
    return cockpit


def verify(cockpit, expected_rows):
    """Gebautes Cockpit gegenlesen, bevor irgendetwas verteilt wird."""
    html = cockpit.read_text(encoding="utf-8")
    lo, hi = find_literal(html)
    rows = read_csv_text(json.loads('"' + html[lo:hi] + '"'))
    keys = {ref_key(r) for r in rows}
    if len(rows) != expected_rows:
        raise SystemExit(f"Pruefung: {len(rows)} Rechnungen eingebettet, "
                         f"{expected_rows} erwartet - nichts verteilt.")
    if len(keys) != len(rows):
        raise SystemExit(f"Pruefung: {len(rows) - len(keys)} doppelte "
                         "Rechnungsnummern - nichts verteilt.")
    # Direkt hinter dem Literal muss die JS-Anweisung enden. Bleibt beim Bauen
    # ein Rest des alten Literals stehen, decodiert die Historie zwar sauber,
    # dahinter steht aber Datenmuell im Skript - das faellt nur hier auf.
    tail = html[hi + 1:hi + 40].lstrip()
    if not tail.startswith(";"):
        raise SystemExit(f"Pruefung: hinter HIST_CSV steht {tail[:20]!r} statt "
                         "';' - Literal nicht sauber ersetzt. Nichts verteilt.")
    if html.count("const HIST_CSV=") != 1:
        raise SystemExit("Pruefung: HIST_CSV mehr als einmal deklariert - "
                         "nichts verteilt.")
    if not html.rstrip().endswith("</html>"):
        raise SystemExit("Pruefung: Datei endet nicht auf </html> - "
                         "abgeschnitten? Nichts verteilt.")
    print(f"  geprueft: {len(rows)} Rechnungen eingebettet, "
          f"{len(html):,} Zeichen, Datei vollstaendig")


def deploy(cockpit, targets, dry_run):
    if not targets:
        print("\n  keine Zielkopien gefunden - nur _build-kit aktualisiert")
        return
    print()
    for t in targets:
        if dry_run:
            print(f"  [dry-run] wuerde schreiben: {t}")
            continue
        t.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(cockpit, t)
        print(f"  verteilt: {t}")


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("exports", nargs="+", help="Agicap-Register-CSV(s)")
    ap.add_argument("--build-kit", help="Pfad zum _build-kit-Ordner "
                                        "(sonst unter OneDrive gesucht)")
    ap.add_argument("--dry-run", action="store_true",
                    help="nur zeigen, was passieren wuerde")
    args = ap.parse_args()

    build_kit = find_build_kit(args.build_kit)
    print(f"_build-kit: {build_kit}")

    text, n = merge_register(build_kit, args.exports, args.dry_run)
    cockpit = run_build(build_kit, text, args.dry_run)
    if cockpit:
        verify(cockpit, n)
    deploy(cockpit or (build_kit / COCKPIT), find_targets(build_kit), args.dry_run)

    print("\nfertig." if not args.dry_run else "\ndry-run beendet - nichts geaendert.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
