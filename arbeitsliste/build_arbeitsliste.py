#!/usr/bin/env python3
"""
Baut arbeitsliste.html direkt aus dem CSV-Export des Blatts 20_WA_PIPELINE.

Massgebliches Kriterium ist Spalte AC "Auftrag abgeschlossen (Ware hat das Lager
verlassen) (AMM)":  AC leer  ->  Ware ist noch im Lager.
Die Spalte I "Status (automatisch)" wird bewusst NICHT verwendet - sie ist
abgeleitet und kann "Versand ueberfaellig" zeigen, obwohl die Ware laengst raus ist.

Aufruf:  python3 build_arbeitsliste.py 20_WA_PIPELINE.csv [--stichtag JJJJ-MM-TT]
"""
import argparse, csv, json, re, unicodedata
from collections import defaultdict
from datetime import date, datetime
from pathlib import Path

KEYS = ["KW", "ID", "Uebermittelt", "Auftragsnr", "Kunde", "Geraete", "Kommissioniertag",
        "Versandart", "Status", "NotizAMM", "NotizELV", "AnmeldedatumAMM", "KommFertig",
        "Paletten", "EW100x80", "EW120x60", "EUR", "EW120x80", "EW80x80", "LDM",
        "Anmeldung", "GeplVersand", "Anlieferdatum", "LiegezeitX", "Zollpapiere",
        "Rechnungsdatum", "Zahlungsziel", "Bezahlt", "AC_abgeschlossen", "AD", "AE",
        "ResteJa", "ResteNr"]

# Zeilen, die nicht abgearbeitet, sondern bereinigt werden. Belege im Mailverkehr.
GEISTER = {
    "S00354": "AMM hat den Auftrag am 17.08. storniert und mit S00585 zu S01254 "
              "zusammengefasst. S01254 hat das Lager am 18.08. verlassen.",
    "S00585": "AMM hat den Auftrag am 17.08. storniert und mit S00354 zu S01254 "
              "zusammengefasst. S01254 hat das Lager am 18.08. verlassen.",
}
# April/Mai-Zeilen: Spalte AC wurde damals noch nicht gepflegt. Alle bezahlt,
# Status "Versendet", kein Anlieferdatum, kein Rechnungsdatum -> Pflegeluecke.
ALTZEILEN_BIS = date(2026, 6, 1)

# Kundennamen, die im Blatt in Varianten stehen und zusammengehoeren.
ALIAS = {"euroda transport": "euroda transport & handel",
         "techno planet": "techno planet ltd"}

# Verifizierte Zusatzinfos aus dem Mailverkehr mit AMM (16.-31.08.2026).
NOTIZ = {
 "S01150": ("<b>Der einzige Auftrag ganz ohne Kommissioniertag — und er hängt an einer "
            "unbeantworteten Mail.</b> AMM fragt seit dem 21.08., ob der Auftrag weiter "
            "zurückgehalten werden soll. Der Partnerauftrag S01144 ist am 21.08. raus.",
            "Soll der Auftrag S01150 noch zurückgehalten werden?",
            "Igor Vujica, AMM · 21.08.2026 · „AW: Abholung S01144“ — unbeantwortet"),
 "S00622": ("<b>Ältester Vorgang ohne jede Anmeldung.</b> Notiz: neue Preisabfrage gestellt, "
            "Zoll noch ungeklärt. Beides muss entschieden werden, sonst stehen 15 Paletten "
            "unbegrenzt. Wenn der Zoll nicht klärbar ist: zurücklagern.",
            "Neue Preisabfrage gestellt. Zoll muss noch geklärt werden.",
            "Notiz ELVINCI in der WA-Pipeline"),
 "S00755": ("<b>Im AMM-System steht ein Platzhalter-Datum.</b> Der Auftragsstand führt als "
            "Liefertag den 31.12.2026. Gleicher Kunde wie S00642 und S01408 — alle drei in "
            "einem Gespräch klären.",
            "S00755 AT QU 31.12.2026 0:00:00 Euroda Transport & Handel … ABHOLER 05 56 0 0 56",
            "proWMS AMM · Auftragsstand 18.08.2026"),
 "S00642": ("<b>Dritter LKW hat keinen Termin.</b> Der Auftrag wurde auf drei Ladungen "
            "geteilt, zwei sind abgeholt (13.08. und 24.08.), AMM wartet seit dem 24.08. auf "
            "eine Rückmeldung für die dritte.",
            "Dieser Auftrag wurde geteilt in 3 LKW's. Erster LKW wurde bereits abgeholt, die "
            "anderen 2 noch nicht, hier warten wir auch auf eine Rückmeldung, wann die …",
            "Igor Vujica, AMM · 24.08.2026 · „AW: Rückmeldung“"),
 "S00944": ("<b>Alles erledigt ausser der Abholung selbst.</b> Bezahlt, kommissioniert, "
            "angemeldet — am 31.08. wurde die Bereitstellung noch einmal angefordert. "
            "Es fehlt nur der Kunde.",
            "… bereitstellen: Kunde: SADI S00944",
            "J. Baranowski → AMM · 31.08.2026 · „Abholung S00944“"),
 "S01296": ("<b>Bereitgestellt am 27.08., seitdem nichts.</b> Kleiner Auftrag, schnell "
            "erledigt: verbindlichen Abholtag holen.",
            "… bereitstellen: Kunde: Artek Commerce LTD S01296",
            "J. Baranowski → AMM · 27.08.2026 · „Abholung S01296“"),
 "S01292": ("<b>Barzahler — erst Zahlung, dann Termin.</b> AMM hat den Auftrag mit „Todo Cash“ "
            "markiert, Spalte „Bezahlt?“ steht auf Nein. Zahlungsstatus klären, dann Freigabe "
            "an AMM.",
            "Todo Cash", "Notiz AMM in der WA-Pipeline"),
 "S01302": ("<b>Platzhalter, dessen Absprache nur Janna kannte.</b> Von den drei am 24.08. "
            "gleich angelegten Platzhaltern ist dieser als einziger noch im Lager — S01318 und "
            "S01266 sind am 28.08. raus. Mit AMM klären, was vereinbart war.",
            "warten/platzhalter/mit Janna besprochen", "Notiz AMM in der WA-Pipeline · 24.08.2026"),
 "S01285": ("<b>Angemeldet, zusammen mit S01327 zu verladen.</b> Achtung: derselbe Kunde hat "
            "mit S01361 eine dritte offene Zeile — prüfen, ob alle drei auf einen LKW gehen.",
            "… bereitstellen: Kunde: Les Petits Pieds S01327 S01285",
            "J. Baranowski → AMM · 25.08.2026 · „Abholung S01327 und S01285“"),
 "S01382": ("<b>Bezahlt, aber datenseitig kaputt.</b> Der Vorgängerauftrag S01340 wurde "
            "nachträglich zusammengeführt und führt Lagernummern doppelt mit S01382. "
            "Erst die Dublette in Odoo auflösen, dann terminieren.",
            "Der Auftrag S01340 — P&C Trading wurde im Nachgang zusammengefügt und beinhaltet "
            "nun doppelte Lagernummern in diesem Auftrag – S01382.",
            "J. Baranowski · 27.08.2026 · „S01340“"),
 "S01222": ("<b>Ältester offener Rest.</b> Notiz: „17 Stück versendet / 4,3 Lademeter stehen "
            "geblieben“. Gut vier Lademeter ohne eigenen Vorgang.", None, None),
 "S01315": ("<b>Hauptladung raus, Rest zurückgelagert.</b> AMM hat am 26.08. gemeldet, dass "
            "mangels Platz im LKW zurückgelagert wurde. Die Lagernummern stehen nur in der Mail.",
            "Folgendes wird zurückgelagert da kein Platz im LKW: 900255466 900255485 900255401 …",
            "AMM Spedition · 26.08.2026 · „AW: Abholung S01315“"),
 "S01314": ("<b>Ein einzelnes Gerät ist stehen geblieben.</b> Lagernummer 900254965 steht "
            "sauber in Spalte AG. Mit dem Kunden klären: nachliefern oder gutschreiben.",
            None, None),
 "S01100": ("<b>Rest seit dem 24.08. offen.</b> Auftrag ist bezahlt und verladen, Spalte AF "
            "meldet trotzdem eine Restmenge. Lagernummern aus der AMM-Mail holen.", None, None),
}


def parse_date(raw):
    raw = (raw or "").strip().split(" ")[0]
    m = re.match(r"^(\d{1,2})\.(\d{1,2})\.(\d{2,4})$", raw)
    if not m:
        return None
    day, month, year = (int(g) for g in m.groups())
    if year < 100:
        year += 2000
    if year > 2100:          # Tippfehler wie 10.08.2062
        year = 2026
    try:
        return date(year, month, day)
    except ValueError:
        return None


def parse_int(raw):
    try:
        return int(float((raw or "0").replace(".", "").replace(",", ".")))
    except ValueError:
        return 0


def load(path):
    rows = list(csv.reader(open(path, encoding="cp1252", newline=""), delimiter=";"))
    head = next(i for i, r in enumerate(rows) if r and r[0].strip() == "KW (auto)")
    out = []
    for raw in rows[head + 1:]:
        raw = raw + [""] * (len(KEYS) - len(raw))
        rec = {k: (raw[i] or "").strip() for i, k in enumerate(KEYS)}
        if not rec["Auftragsnr"]:
            continue
        rec["d_ac"] = parse_date(rec["AC_abgeschlossen"])
        rec["d_komm"] = parse_date(rec["Kommissioniertag"])
        rec["d_fertig"] = parse_date(rec["KommFertig"])
        rec["n"] = parse_int(rec["Geraete"])
        rec["pal"] = parse_int(rec["Paletten"])
        rec["angemeldet"] = rec["Anmeldung"] == "ist angemeldet"
        rec["bezahlt"] = rec["Bezahlt"] == "Ja"
        rec["storno"] = bool(re.search(r"storn", (rec["NotizAMM"] + " " + rec["NotizELV"]).lower()))
        out.append(rec)
    return out


def kundenschluessel(name):
    k = unicodedata.normalize("NFKD", name.strip().lower()).rstrip(". ")
    return ALIAS.get(k, k)


def klassifiziere(recs, stichtag):
    """-> dict bucket -> Liste. Nur AC entscheidet ueber 'noch im Lager'."""
    buckets = defaultdict(list)
    for r in recs:
        r["liegt"] = (stichtag - r["d_komm"]).days if r["d_komm"] else None
        if r["d_ac"]:
            if r["ResteJa"].lower().startswith("ja"):
                buckets["C"].append(r)          # Ware raus, Restmenge geblieben
            continue
        if r["Auftragsnr"] in GEISTER:
            buckets["D"].append(r)
        elif r["storno"]:
            buckets["D"].append(r)
        elif r["d_komm"] and r["d_komm"] < ALTZEILEN_BIS:
            buckets["E"].append(r)              # Pflegeluecke aus der Zeit vor Spalte AC
        elif not r["angemeldet"]:
            buckets["A"].append(r)              # kein Termin bei AMM
        else:
            buckets["B"].append(r)              # angemeldet, Ware trotzdem da
    for key in buckets:
        buckets[key].sort(key=lambda r: (-(r["liegt"] if r["liegt"] is not None else 999),
                                         -r["n"]))
    return buckets


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("csv")
    ap.add_argument("--stichtag", default=date.today().isoformat())
    ap.add_argument("--out", default=str(Path(__file__).parent / "arbeitsliste.data.json"))
    args = ap.parse_args()
    stichtag = datetime.fromisoformat(args.stichtag).date()

    recs = load(args.csv)
    buckets = klassifiziere(recs, stichtag)
    im_lager = buckets["A"] + buckets["B"]

    print(f"Auftragszeilen gesamt        : {len(recs)}")
    print(f"Spalte AC gefuellt (raus)    : {sum(1 for r in recs if r['d_ac'])}")
    print(f"Spalte AC leer               : {sum(1 for r in recs if not r['d_ac'])}\n")
    for key, titel in [("A", "kein Termin bei AMM (Anmeldung 'warten'/leer)"),
                       ("B", "angemeldet, Ware trotzdem im Lager"),
                       ("C", "Ware raus, Restmenge geblieben (Spalte AF)"),
                       ("D", "Zeilen bereinigen (Geisterzeilen / storniert)"),
                       ("E", "Altzeilen vor Juni: Spalte AC nie gepflegt")]:
        rs = buckets[key]
        print(f"  {key} · {titel}: {len(rs)} Vorgaenge · {sum(r['n'] for r in rs)} Geraete")
    print(f"\nECHT IM LAGER: {len(im_lager)} Vorgaenge · {sum(r['n'] for r in im_lager)} Geraete "
          f"· {sum(r['pal'] for r in im_lager)} Paletten")
    bez = [r for r in im_lager if r["bezahlt"]]
    print(f"davon bezahlt: {len(bez)} Vorgaenge · {sum(r['n'] for r in bez)} Geraete")

    payload = {"stichtag": stichtag.isoformat(),
               "buckets": {k: [{"nr": r["Auftragsnr"], "kunde": r["Kunde"].strip(),
                                "ger": r["n"], "pal": r["pal"], "ldm": r["LDM"],
                                "komm": r["Kommissioniertag"], "liegt": r["liegt"],
                                "anm": r["Anmeldung"], "bezahlt": r["Bezahlt"],
                                "art": r["Versandart"], "ac": r["AC_abgeschlossen"],
                                "reste": r["ResteNr"], "geist": GEISTER.get(r["Auftragsnr"]),
                                "notiz": NOTIZ.get(r["Auftragsnr"])}
                            for r in buckets[k]] for k in "ABCDE"}}
    Path(args.out).write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\ngeschrieben: {args.out}")

    html = Path(__file__).parent / "arbeitsliste.html"
    if html.exists():
        txt = html.read_text(encoding="utf-8")
        blob = "const DATA = " + json.dumps(payload, ensure_ascii=False) + ";"
        neu, n = re.subn(r"(?s)/\* DATA-START \*/.*?/\* DATA-END \*/",
                         "/* DATA-START */\n" + blob.replace("\\", "\\\\") + "\n/* DATA-END */", txt)
        if n:
            html.write_text(neu, encoding="utf-8")
            print(f"Datenblock in {html.name} ersetzt")
        else:
            print("WARNUNG: Marker /* DATA-START */ in arbeitsliste.html nicht gefunden")


if __name__ == "__main__":
    main()
