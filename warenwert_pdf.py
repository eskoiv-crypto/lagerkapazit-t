#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Einseiter "Warenwert zum Stichtag" aus der Faktendatei von warenwert_stichtag.py.

  python3 warenwert_pdf.py --json warenwert_facts_2026-08-31.json \
                           --serie warenwert_monatsende.csv \
                           --out  Warenwert_31-08-2026.pdf

Die erzeugte PDF enthaelt Geschaeftszahlen und bleibt lokal (siehe .gitignore).
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_JUSTIFY, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (HRFlowable, Paragraph, SimpleDocTemplate, Spacer,
                                Table, TableStyle)

INK      = colors.HexColor('#1d1d1f')
INK_SOFT = colors.HexColor('#424245')
SUBTLE   = colors.HexColor('#86868b')
DIVIDER  = colors.HexColor('#d2d2d7')
CARD     = colors.HexColor('#f5f5f7')
PAPER    = colors.HexColor('#fbfbfd')
BLUE     = colors.HexColor('#0071e3')
BLUE_BG  = colors.HexColor('#e8f1fc')
GREEN    = colors.HexColor('#2da14d')
AMBER    = colors.HexColor('#d97706')

EYEBROW = ParagraphStyle('e', fontName='Helvetica-Bold', fontSize=9, leading=12,
                         textColor=BLUE, spaceAfter=4)
TITLE   = ParagraphStyle('t', fontName='Helvetica-Bold', fontSize=26, leading=30,
                         textColor=INK, spaceAfter=2)
SUB     = ParagraphStyle('s', fontName='Helvetica', fontSize=12, leading=16,
                         textColor=SUBTLE, spaceAfter=4)
H2      = ParagraphStyle('h', fontName='Helvetica-Bold', fontSize=13, leading=17,
                         textColor=INK, spaceBefore=12, spaceAfter=6)
BODY    = ParagraphStyle('b', fontName='Helvetica', fontSize=9.5, leading=14,
                         textColor=INK_SOFT, alignment=TA_JUSTIFY, spaceAfter=3)
SMALL   = ParagraphStyle('sm', fontName='Helvetica', fontSize=8, leading=11,
                         textColor=SUBTLE)


def eur(x: float) -> str:
    return f"{x:,.0f}".replace(",", ".") + " €"


def de(n) -> str:
    return f"{int(n):,}".replace(",", ".")


def lade_serie(pfad: Path | None):
    if not pfad or not pfad.exists():
        return []
    zeilen = pfad.read_text(encoding="utf-8").splitlines()[1:]
    out = []
    for z in zeilen:
        if not z.strip():
            continue
        tag, stk, wert = z.split(";")[:3]
        out.append((tag, int(stk), float(wert)))
    return out


def bau(f: dict, serie: list, out: Path) -> Path:
    tag = datetime.fromisoformat(f["stichtag"]).strftime("%d.%m.%Y")
    umfang_txt = ("Alles physisch im Lager, inkl. bereits verkaufter Ware "
                  "(AMM-Status QE + VS + AA)" if f["umfang"] == "gesamt"
                  else "Nur freiverkäufliche Ware (AMM-Status QE)")

    def kopf_fuss(canv, doc):
        canv.saveState()
        canv.setFont('Helvetica-Bold', 8.5); canv.setFillColor(INK)
        canv.drawString(2*cm, 28.3*cm, 'ELVINCI.DE GMBH')
        canv.setFont('Helvetica', 8.5); canv.setFillColor(SUBTLE)
        canv.drawString(5*cm, 28.3*cm, '·  Warenwert')
        canv.setFillColor(BLUE)
        canv.drawRightString(19*cm, 28.3*cm, 'VERTRAULICH · INTERN')
        canv.setStrokeColor(DIVIDER); canv.setLineWidth(0.4)
        canv.line(2*cm, 28.05*cm, 19*cm, 28.05*cm)
        canv.line(2*cm, 1.6*cm, 19*cm, 1.6*cm)
        canv.setFont('Helvetica', 8); canv.setFillColor(SUBTLE)
        canv.drawString(2*cm, 1.1*cm,
                        f'Stichtag {tag} · erstellt {datetime.now():%d.%m.%Y}')
        canv.setFillColor(INK_SOFT); canv.setFont('Helvetica-Bold', 8)
        canv.drawRightString(19*cm, 1.1*cm, f'Seite {doc.page}')
        canv.restoreState()

    doc = SimpleDocTemplate(str(out), pagesize=A4, leftMargin=2*cm, rightMargin=2*cm,
                            topMargin=2.2*cm, bottomMargin=2*cm)
    st = []
    st.append(Paragraph(f'MONATSREIHE · STICHTAG {tag}', EYEBROW))
    st.append(Paragraph('Warenwert', TITLE))
    st.append(Paragraph(umfang_txt, SUB))
    st.append(Spacer(1, 0.5*cm))

    # Hero
    hero = Table([[
        Table([[Paragraph('WARENWERT · EINKAUF (EK)',
                          ParagraphStyle('hl', fontName='Helvetica-Bold', fontSize=8.5,
                                         leading=11, textColor=SUBTLE))],
               [Spacer(1, 3)],
               [Paragraph(eur(f["ek_gesamt"]),
                          ParagraphStyle('hv', fontName='Helvetica-Bold', fontSize=42,
                                         leading=48, textColor=INK))],
               [Spacer(1, 5)],
               [Paragraph(f'{de(f["geraete"])} Geräte · Ø {eur(f["ek_gesamt"]/max(f["geraete"],1))} je Gerät',
                          ParagraphStyle('hs', fontName='Helvetica', fontSize=10.5,
                                         leading=14, textColor=INK_SOFT))]],
              colWidths=[15.8*cm], style=TableStyle([
                  ('LEFTPADDING', (0,0), (-1,-1), 0), ('RIGHTPADDING', (0,0), (-1,-1), 0),
                  ('TOPPADDING', (0,0), (-1,-1), 0), ('BOTTOMPADDING', (0,0), (-1,-1), 0)]))
    ]], colWidths=[16.6*cm])
    hero.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), CARD),
        ('LINEBEFORE', (0,0), (0,-1), 3, BLUE),
        ('LEFTPADDING', (0,0), (-1,-1), 22), ('RIGHTPADDING', (0,0), (-1,-1), 22),
        ('TOPPADDING', (0,0), (-1,-1), 20), ('BOTTOMPADDING', (0,0), (-1,-1), 20)]))
    st.append(hero)
    st.append(Spacer(1, 0.5*cm))

    # Aufschlüsselung
    st.append(Paragraph('Aufschlüsselung', H2))
    rows = [['Herkunft des Werts', 'Geräte', 'EK']]
    rows.append(['Einkaufspreis aus Odoo (belegt)', de(f["n_odoo"]), eur(f["ek_odoo"])])
    if f.get("n_portal"):
        rows.append(['Portal-Restbestand (belegt)', de(f["n_portal"]), eur(f["ek_portal"])])
    rows.append(['Ø-Schätzung — kein EK hinterlegt', de(f["n_geschaetzt"]), eur(f["ek_geschaetzt"])])
    if f.get("n_schrott_ek0"):
        rows.append(['Schrottware — echter EK 0 €', de(f["n_schrott_ek0"]), '—'])
    rows.append(['Summe', de(f["geraete"]), eur(f["ek_gesamt"])])
    t = Table(rows, colWidths=[9.6*cm, 3*cm, 4*cm])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), INK), ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'), ('FONTSIZE', (0,0), (-1,0), 8),
        ('FONTSIZE', (0,1), (-1,-1), 9.5), ('TEXTCOLOR', (0,1), (-1,-1), INK_SOFT),
        ('ALIGN', (1,0), (-1,-1), 'RIGHT'),
        ('FONTNAME', (0,-1), (-1,-1), 'Helvetica-Bold'), ('TEXTCOLOR', (0,-1), (-1,-1), INK),
        ('BACKGROUND', (0,-1), (-1,-1), BLUE_BG),
        ('LINEBELOW', (0,0), (-1,-1), 0.4, DIVIDER),
        ('ROWBACKGROUNDS', (0,1), (-1,-2), [colors.white, PAPER]),
        ('LEFTPADDING', (0,0), (-1,-1), 10), ('RIGHTPADDING', (0,0), (-1,-1), 10),
        ('TOPPADDING', (0,0), (-1,-1), 7), ('BOTTOMPADDING', (0,0), (-1,-1), 7),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE')]))
    st.append(t)

    # Monatsreihe
    if serie:
        st.append(Paragraph('Monatsreihe', H2))
        letzte = serie[-7:]
        kopf = ['Monatsende'] + [z[0][:6] + z[0][8:] for z in letzte]
        stk = ['Geräte'] + [de(z[1]) for z in letzte]
        wrt = ['EK-Wert'] + [f'{z[2]/1000:,.0f} k'.replace(',', '.') for z in letzte]
        ts = Table([kopf, stk, wrt], colWidths=[2.6*cm] + [2*cm]*len(letzte))
        ts.setStyle(TableStyle([
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
            ('FONTNAME', (0,0), (0,-1), 'Helvetica-Bold'),
            ('FONTSIZE', (0,0), (-1,-1), 8.5),
            ('TEXTCOLOR', (0,0), (-1,-1), INK_SOFT),
            ('TEXTCOLOR', (-1,1), (-1,-1), INK),
            ('BACKGROUND', (-1,0), (-1,-1), BLUE_BG),
            ('ALIGN', (1,0), (-1,-1), 'RIGHT'),
            ('LINEBELOW', (0,0), (-1,-2), 0.4, DIVIDER),
            ('TOPPADDING', (0,0), (-1,-1), 5), ('BOTTOMPADDING', (0,0), (-1,-1), 5),
            ('LEFTPADDING', (0,0), (-1,-1), 6), ('RIGHTPADDING', (0,0), (-1,-1), 6)]))
        st.append(ts)

    # Hinweise
    st.append(Paragraph('Wichtige Hinweise', H2))
    for w in f.get("warnungen", []):
        st.append(Paragraph(f'–&nbsp;&nbsp;{w}', BODY))
    st.append(Paragraph(
        '–&nbsp;&nbsp;Mengengerüst ist die AMM-Bestandsliste vom Stichtag — die physische '
        'Wahrheit. Der Preis kommt je Lager-Nr aus dem Odoo-Export. Wo kein Einkaufspreis '
        'hinterlegt ist, wird mit dem Durchschnitt der Produktkategorie gerechnet '
        '(ersatzweise Marke, Bezeichner, Gesamtdurchschnitt).', BODY))
    st.append(Paragraph(
        '–&nbsp;&nbsp;Der Odoo-Export wurde nach dem Stichtag gezogen; die Bestandsliste setzt '
        'den Stichtag. Ein Export exakt zum Monatsletzten 00:00 Uhr aus der Datenbank wäre '
        'genauer.', BODY))

    st.append(Spacer(1, 0.35*cm))
    st.append(HRFlowable(width="100%", thickness=0.4, color=DIVIDER,
                         spaceBefore=4, spaceAfter=6))
    quellen = f'Quellen: {f["quelle_bestand"]}'
    if f.get("quelle_odoo"):
        quellen += f' · {f["quelle_odoo"]}'
    if f.get("quelle_portal"):
        quellen += f' · {f["quelle_portal"]}'
    st.append(Paragraph(
        quellen + f' · verknüpft über die Lager-Nr · AMM-Bestand '
        f'{de(f["bestand_zeilen_gesamt"])} Zeilen '
        f'({", ".join(f"{k} {de(v)}" for k, v in sorted(f["status_verteilung"].items()))})'
        ' · erzeugt mit warenwert_stichtag.py · keine personenbezogenen Daten.', SMALL))

    doc.build(st, onFirstPage=kopf_fuss, onLaterPages=kopf_fuss)
    return out


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--json", required=True)
    p.add_argument("--serie")
    p.add_argument("--out", required=True)
    a = p.parse_args()
    f = json.loads(Path(a.json).read_text(encoding="utf-8"))
    out = bau(f, lade_serie(Path(a.serie) if a.serie else None), Path(a.out))
    print(f"PDF erstellt: {out.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
