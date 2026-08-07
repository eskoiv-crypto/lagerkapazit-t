"""
Lagerwert (EK) zum 29.05.2026 — Executive Brief für die Geschäftsführung.
KILLCRITIC-validierte Auswertung mit transparenter Methodik.
Design: Apple-inspirierte ruhige Typografie, hohe visuelle Hierarchie.
"""
import json
from pathlib import Path
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm, mm
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_RIGHT, TA_CENTER, TA_JUSTIFY
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, Table,
                                 TableStyle, PageBreak, HRFlowable, KeepTogether)

with open('lagerwert_facts.json', 'r', encoding='utf-8') as f:
    F = json.load(f)

def eur(v):
    """Format euro values German-style with thin spaces and proper grouping."""
    s = f"{v:,.0f}".replace(',', '.')
    return f"{s} €"

def eur_compact(v):
    """Compact: '309 k €' for very large numbers, normal otherwise."""
    return eur(v)

OUT = Path('Lagerwert_29-05-2026_GF-Brief.pdf')

# ===== APPLE-INSPIRED PALETTE =====
INK       = colors.HexColor('#1d1d1f')
INK_SOFT  = colors.HexColor('#424245')
SUBTLE    = colors.HexColor('#86868b')
DIVIDER   = colors.HexColor('#d2d2d7')
PAPER     = colors.HexColor('#fbfbfd')
CARD      = colors.HexColor('#f5f5f7')
CARD_DARK = colors.HexColor('#1d1d1f')

BLUE      = colors.HexColor('#0071e3')
BLUE_BG   = colors.HexColor('#e8f1fc')
GREEN     = colors.HexColor('#2da14d')
GREEN_BG  = colors.HexColor('#e8f5ec')
AMBER     = colors.HexColor('#d97706')
AMBER_BG  = colors.HexColor('#fef3e7')
RED       = colors.HexColor('#d70015')
RED_BG    = colors.HexColor('#fce8e8')
PURPLE    = colors.HexColor('#6b46c1')

# ===== STYLES =====
TITLE = ParagraphStyle('Title', fontName='Helvetica-Bold', fontSize=30,
                       leading=34, textColor=INK, spaceAfter=2, alignment=TA_LEFT)
SUBTITLE = ParagraphStyle('Sub', fontName='Helvetica', fontSize=14,
                          leading=18, textColor=SUBTLE, spaceAfter=4, alignment=TA_LEFT)
EYEBROW = ParagraphStyle('Eye', fontName='Helvetica-Bold', fontSize=9,
                         leading=12, textColor=BLUE, spaceAfter=4,
                         alignment=TA_LEFT)
H2 = ParagraphStyle('H2', fontName='Helvetica-Bold', fontSize=16,
                    leading=20, textColor=INK, spaceBefore=16, spaceAfter=8,
                    alignment=TA_LEFT)
H3 = ParagraphStyle('H3', fontName='Helvetica-Bold', fontSize=11,
                    leading=14, textColor=INK, spaceBefore=10, spaceAfter=4)
BODY = ParagraphStyle('Body', fontName='Helvetica', fontSize=10,
                      leading=15, textColor=INK_SOFT, alignment=TA_LEFT,
                      spaceAfter=4)
BODY_J = ParagraphStyle('BodyJ', parent=BODY, alignment=TA_JUSTIFY)
LEAD = ParagraphStyle('Lead', fontName='Helvetica', fontSize=11,
                      leading=17, textColor=INK, alignment=TA_LEFT,
                      spaceAfter=6)
SMALL = ParagraphStyle('Small', fontName='Helvetica', fontSize=8.5,
                       leading=12, textColor=SUBTLE)
CAPTION = ParagraphStyle('Cap', fontName='Helvetica', fontSize=7.5,
                         leading=10, textColor=SUBTLE,
                         alignment=TA_LEFT, textTransform='uppercase')

def section_title(eyebrow_text, title_text):
    """Returns flowables: small colored eyebrow + larger title."""
    return [
        Paragraph(eyebrow_text.upper(), EYEBROW),
        Paragraph(title_text, H2),
    ]

def divider(thickness=0.4, space=8):
    return HRFlowable(width="100%", thickness=thickness, color=DIVIDER,
                      spaceBefore=space, spaceAfter=space)

# ===== KPI CARD =====
def kpi_card(label, value, sub, accent_color, big=True):
    """An elegant KPI card with subtle backdrop and accent bar."""
    label_style = ParagraphStyle('kl', fontName='Helvetica-Bold', fontSize=7.5,
                                  leading=10, textColor=SUBTLE,
                                  textTransform='uppercase')
    value_style = ParagraphStyle('kv', fontName='Helvetica-Bold',
                                  fontSize=26 if big else 20, leading=30,
                                  textColor=INK)
    sub_style = ParagraphStyle('ks', fontName='Helvetica', fontSize=8.5,
                                leading=11, textColor=INK_SOFT)

    inner = Table(
        [[Paragraph(label.upper(), label_style)],
         [Spacer(1, 2)],
         [Paragraph(value, value_style)],
         [Spacer(1, 4)],
         [Paragraph(sub, sub_style)]],
        colWidths=[5.2*cm]
    )
    inner.setStyle(TableStyle([
        ('LEFTPADDING', (0,0), (-1,-1), 0),
        ('RIGHTPADDING', (0,0), (-1,-1), 0),
        ('TOPPADDING', (0,0), (-1,-1), 0),
        ('BOTTOMPADDING', (0,0), (-1,-1), 0),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
    ]))

    # Outer card with left accent bar
    outer = Table(
        [['', inner]],
        colWidths=[0.18*cm, 5.4*cm]
    )
    outer.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (0,0), accent_color),
        ('BACKGROUND', (1,0), (1,0), CARD),
        ('LEFTPADDING', (1,0), (1,0), 16),
        ('RIGHTPADDING', (1,0), (1,0), 14),
        ('TOPPADDING', (1,0), (1,0), 14),
        ('BOTTOMPADDING', (1,0), (1,0), 14),
        ('LEFTPADDING', (0,0), (0,0), 0),
        ('RIGHTPADDING', (0,0), (0,0), 0),
        ('TOPPADDING', (0,0), (0,0), 0),
        ('BOTTOMPADDING', (0,0), (0,0), 0),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
    ]))
    return outer

# ===== STATUS BADGE =====
def status_badge(text, bg, fg):
    p = Paragraph(f'<font color="{fg.hexval()}"><b>{text}</b></font>',
                  ParagraphStyle('sb', fontName='Helvetica-Bold', fontSize=7.5,
                                  leading=10, alignment=TA_CENTER))
    t = Table([[p]], colWidths=[2.4*cm], rowHeights=[0.5*cm])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), bg),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('LEFTPADDING', (0,0), (-1,-1), 4),
        ('RIGHTPADDING', (0,0), (-1,-1), 4),
    ]))
    return t

# ===== FACTS (mit Paletten-Detail) =====
BELASTBAR_STOCK = F['ek_matched_sum']                # 309.691 nur Stock
BELASTBAR       = F['ek_belastbar_neu']              # 327.826 mit Paletten exakt
PALETTEN_EK     = F['pallets_detail_sum_ek']         # 18.135
PALETTEN_DEV    = F['pallets_detail_devices']        # 432
PALETTEN_N      = F['pallets_detail_count']          # 17
UNMATCHED_REST  = F['ek_unmatched_rest_est']         # 43.083 (491 Geräte)
UNMATCHED_RESTN = F['qe_unmatched_rest']             # 491
AA_EST          = F['ek_aa_est']                     # 9.411
INVENTUR        = F['total_inventur_neu']            # 380.319
COVERAGE_EXAKT  = (F['qe_matched'] + PALETTEN_N) / F['qe_real_at_2905'] * 100

# ===== HEADER / FOOTER =====
def header_footer(canv, doc):
    canv.saveState()
    # Top brand strip
    canv.setFont('Helvetica-Bold', 8.5)
    canv.setFillColor(INK)
    canv.drawString(2*cm, 28.3*cm, 'ELVINCI.DE GMBH')
    canv.setFont('Helvetica', 8.5)
    canv.setFillColor(SUBTLE)
    canv.drawString(5*cm, 28.3*cm, '·  Lagerwert-Brief')
    canv.setFillColor(BLUE)
    canv.drawRightString(19*cm, 28.3*cm, 'VERTRAULICH · GF-INTERN')
    canv.setStrokeColor(DIVIDER); canv.setLineWidth(0.4)
    canv.line(2*cm, 28.05*cm, 19*cm, 28.05*cm)

    # Footer
    canv.setStrokeColor(DIVIDER); canv.setLineWidth(0.4)
    canv.line(2*cm, 1.6*cm, 19*cm, 1.6*cm)
    canv.setFont('Helvetica', 8); canv.setFillColor(SUBTLE)
    canv.drawString(2*cm, 1.1*cm, 'Stichtag 29.05.2026 · erstellt 01.06.2026')
    canv.setFillColor(INK_SOFT); canv.setFont('Helvetica-Bold', 8)
    canv.drawRightString(19*cm, 1.1*cm, f'Seite {doc.page}')
    canv.restoreState()

# ===== DOC =====
doc = SimpleDocTemplate(str(OUT), pagesize=A4,
                        leftMargin=2*cm, rightMargin=2*cm,
                        topMargin=2.2*cm, bottomMargin=2*cm)
story = []

# =================================================
# 1. COVER / EXECUTIVE
# =================================================
story.append(Paragraph('EXECUTIVE BRIEF · STICHTAG 29.05.2026', EYEBROW))
story.append(Paragraph('Lagerwert-Bewertung', TITLE))
story.append(Paragraph('Buchwert-Einkauf (EK) zum Stichtag · KILLCRITIC-validiert',
                       SUBTITLE))

story.append(Spacer(1, 0.7*cm))

# Hero number block — the headline
hero_label = Paragraph(
    'BELASTBARE UNTERGRENZE',
    ParagraphStyle('hl', fontName='Helvetica-Bold', fontSize=9, leading=11,
                   textColor=SUBTLE, textTransform='uppercase')
)
hero_value = Paragraph(
    f'<font color="{INK.hexval()}">{eur(BELASTBAR)}</font>',
    ParagraphStyle('hv', fontName='Helvetica-Bold', fontSize=48, leading=56,
                   textColor=INK)
)
hero_sub_text = (f'{F["qe_matched_nonzero"] + PALETTEN_DEV:,} Geräte mit verifiziertem '
                 f'EK · {COVERAGE_EXAKT:.1f} % Coverage (inkl. Paletten-Detail)'.replace(',', '.'))
hero_sub = Paragraph(hero_sub_text,
    ParagraphStyle('hs', fontName='Helvetica', fontSize=11, leading=14,
                   textColor=INK_SOFT)
)
hero_range = Paragraph(
    f'Volle Inventur-Hochrechnung inkl. Schätzungen: <b>{eur(INVENTUR)}</b>',
    ParagraphStyle('hr', fontName='Helvetica', fontSize=10, leading=13,
                   textColor=BLUE)
)

hero_inner = Table(
    [[hero_label], [Spacer(1, 4)],
     [hero_value], [Spacer(1, 6)],
     [hero_sub], [Spacer(1, 4)],
     [hero_range]],
    colWidths=[16*cm]
)
hero_inner.setStyle(TableStyle([
    ('LEFTPADDING', (0,0), (-1,-1), 0),
    ('RIGHTPADDING', (0,0), (-1,-1), 0),
    ('TOPPADDING', (0,0), (-1,-1), 0),
    ('BOTTOMPADDING', (0,0), (-1,-1), 0),
]))

hero_outer = Table(
    [['', hero_inner]],
    colWidths=[0.25*cm, 16.5*cm]
)
hero_outer.setStyle(TableStyle([
    ('BACKGROUND', (0,0), (0,0), BLUE),
    ('BACKGROUND', (1,0), (1,0), CARD),
    ('LEFTPADDING', (1,0), (1,0), 24),
    ('RIGHTPADDING', (1,0), (1,0), 24),
    ('TOPPADDING', (1,0), (1,0), 22),
    ('BOTTOMPADDING', (1,0), (1,0), 22),
    ('LEFTPADDING', (0,0), (0,0), 0),
    ('RIGHTPADDING', (0,0), (0,0), 0),
    ('VALIGN', (0,0), (-1,-1), 'TOP'),
]))
story.append(hero_outer)
story.append(Spacer(1, 0.6*cm))

# Executive summary — short & sharp
story.append(Paragraph(
    f"Zum Stichtag <b>29.05.2026</b> beträgt der belastbare Lagerwert (EK) "
    f"<b>{eur(BELASTBAR)}</b> — basierend auf 3.256 Stock-gematchten Geräten "
    f"plus 17 gemischten Paletten mit Einzelgerät-EK-Detail (432 Geräte, Σ {eur(PALETTEN_EK)}). "
    f"Die Inventur-Hochrechnung inklusive der verbliebenen Schätzungen "
    f"(491 nicht-gelistete Einzelgeräte, 88 AA-auftragsgebundene) "
    f"liegt bei <b>{eur(INVENTUR)}</b>. "
    f"Alle Bestandteile wurden gegen 9 unabhängige Plausibilitätsprüfungen geprüft.",
    LEAD
))

story.append(Spacer(1, 0.4*cm))

# 3-Spalten-Übersicht KPIs
k1 = kpi_card('Belastbar (exakt)', eur(BELASTBAR),
              f'Stock + 17 Paletten · {F["qe_matched_nonzero"] + PALETTEN_DEV:,} Geräte'.replace(',', '.'),
              GREEN)
k2 = kpi_card('Inventur (Hochrechn.)', eur(INVENTUR),
              f'{F["qe_real_at_2905"]+F["aa_real_at_2905"]:,} Geräte gesamt'.replace(',', '.'),
              BLUE)
k3 = kpi_card('Coverage', f'{COVERAGE_EXAKT:.1f} %'.replace('.', ','),
              'Lager mit verifiziertem EK', INK)
kpi_row = Table([[k1, k2, k3]], colWidths=[5.6*cm, 5.6*cm, 5.6*cm])
kpi_row.setStyle(TableStyle([
    ('VALIGN', (0,0), (-1,-1), 'TOP'),
    ('LEFTPADDING', (0,0), (-1,-1), 0),
    ('RIGHTPADDING', (0,0), (-1,-1), 0),
]))
story.append(kpi_row)

# =================================================
# 2. HERLEITUNG (Trichter)
# =================================================
story.append(PageBreak())
for f in section_title('Methodik', 'Wie die Zahl zustande kommt'):
    story.append(f)

story.append(Paragraph(
    "Der Lagerbestand wird aus drei unabhängigen Quellen rekonstruiert: dem "
    "AMM-BESTAND (Stichtag 29.05.2026, alle physisch geführten Geräte), dem "
    "Portal-Snapshot Stock-Analysis (01.06.2026, EK-Preise) und der "
    "All-Sold-Verkaufshistorie zur Bereinigung des Status-Lags zwischen "
    "Lagerverwaltung und Verkaufsportal.",
    BODY_J
))
story.append(Spacer(1, 0.3*cm))

trichter = [
    ['Schritt', 'Geräte', 'Anmerkung'],
    [Paragraph('<b>BESTAND 29.05.2026</b><br/><font size="8" color="#86868b">alle Status, vollständig</font>', BODY),
     Paragraph(f'<b>{F["bestand_total"]:,}</b>'.replace(',', '.'), BODY),
     'AMM-Lagerverwaltung'],
    ['  −  Status VS (Versand-Pipeline)',
     f'−{F["vs_total"]:,}'.replace(',', '.'),
     f'{F["vs_in_asold"]}/{F["vs_total"]:,} in All-Sold = wirklich verkauft → Forderung, nicht Lager'.replace(',', '.')],
    ['  −  Status AA (Auftragsbindung)',
     f'−{F["aa_total"]:,}'.replace(',', '.'),
     f'{F["aa_total"]-F["aa_real_at_2905"]} verkauft · {F["aa_real_at_2905"]} echt im Lager (Schätzung {eur(AA_EST)})'],
    [Paragraph('<b>=  Status QE im BESTAND</b>', BODY),
     Paragraph(f'<b>{F["qe_total"]:,}</b>'.replace(',', '.'), BODY),
     'Klassifiziert, theoretisch verkaufsbereit'],
    ['  −  QE bereits VOR 29.05 verkauft',
     f'−{F["qe_sold_before_2905"]:,}'.replace(',', '.'),
     'Status-Lag (Median 12 T WE→Verkauf · nur 1 Retoure-Verdacht)'],
    [Paragraph('<b>=  Im Lager AM Stichtag 29.05</b>', BODY),
     Paragraph(f'<b>{F["qe_real_at_2905"]:,}</b>'.replace(',', '.'), BODY),
     'Bewertungsbasis (stichtagsrein)'],
    [Paragraph('  •  davon mit Portal-EK gematcht', BODY),
     f'{F["qe_matched"]:,}'.replace(',', '.'),
     Paragraph(f'Σ EK Stock-Analysis: <b>{eur(BELASTBAR_STOCK)}</b>', BODY)],
    [Paragraph('  •  davon Paletten mit Detail-EK', BODY),
     f'{PALETTEN_N}',
     Paragraph(f'Detail-Datei: {PALETTEN_DEV} Einzelgeräte · Σ EK <b>{eur(PALETTEN_EK)}</b>', BODY)],
    [Paragraph('  •  davon ohne EK-Daten (Restschätzung)', BODY),
     f'{UNMATCHED_RESTN:,}'.replace(',', '.'),
     Paragraph(f'Schätzung Ø EK je Bezeichnung: <b>{eur(UNMATCHED_REST)}</b>', BODY)],
]
tt = Table(trichter, colWidths=[7.2*cm, 2*cm, 7.8*cm])
tt.setStyle(TableStyle([
    # header
    ('BACKGROUND', (0,0), (-1,0), INK),
    ('TEXTCOLOR', (0,0), (-1,0), colors.white),
    ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
    ('FONTSIZE', (0,0), (-1,0), 8),
    ('TEXTTRANSFORM', (0,0), (-1,0), 'uppercase'),
    # body
    ('FONTSIZE', (0,1), (-1,-1), 9.5),
    ('FONTNAME', (0,1), (-1,-1), 'Helvetica'),
    ('TEXTCOLOR', (0,1), (-1,-1), INK_SOFT),
    ('ALIGN', (1,0), (1,-1), 'RIGHT'),
    ('FONTNAME', (1,1), (1,-1), 'Helvetica-Bold'),
    ('TEXTCOLOR', (1,1), (1,-1), INK),
    ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ('LINEBELOW', (0,0), (-1,-1), 0.4, DIVIDER),
    ('LEFTPADDING', (0,0), (-1,-1), 10),
    ('RIGHTPADDING', (0,0), (-1,-1), 10),
    ('TOPPADDING', (0,0), (-1,-1), 8),
    ('BOTTOMPADDING', (0,0), (-1,-1), 8),
    # highlight rows (Schritt 4 = "= QE", Schritt 6 = "= im Lager")
    ('BACKGROUND', (0,4), (-1,4), BLUE_BG),
    ('BACKGROUND', (0,6), (-1,6), GREEN_BG),
    # exakter Belastbar-Block hervorheben (Stock-match + Paletten-Detail)
    ('BACKGROUND', (0,7), (-1,8), CARD),
]))
story.append(tt)

# =================================================
# 3. KILLCRITIC
# =================================================
story.append(PageBreak())
for f in section_title('Plausibilitätsprüfung', 'KILLCRITIC — 9 unabhängige Checks'):
    story.append(f)
story.append(Paragraph(
    "Jede Bestandteilszahl wurde gegen mindestens eine unabhängige Quelle geprüft. "
    "Sieben von neun Prüfungen sind <b>bestätigt</b> (grün), zwei bleiben mit "
    "Schätzungs-Bandbreite ausgewiesen (gelb).",
    BODY_J
))
story.append(Spacer(1, 0.35*cm))

checks = [
    ('1', 'BESTÄTIGT', GREEN_BG, GREEN,
     'VS-Status korrekt ausgeschlossen',
     f'{F["vs_in_asold"]}/{F["vs_total"]:,} VS-Geräte ({F["vs_in_asold"]/F["vs_total"]*100:.1f} %) in All-Sold = wirklich verkauft. VS = Forderung, nicht Lager. 6 Altfälle (Ø WE 2023) ohne Match — vernachlässigbar.'.replace(',', '.')),
    ('2', 'BESTÄTIGT', GREEN_BG, GREEN,
     'QE-Status-Lag echter Statusverzug',
     'Median 12 Tage zwischen Wareneingang und Verkauf (P75 = 47 T). Nur 1 Retoure-Verdacht in 1.057 Fällen. Bestätigt: das sind echte verkaufte Geräte, die im AMM noch als QE geführt werden.'),
    ('3', 'BESTÄTIGT', GREEN_BG, GREEN,
     'Buying_Price = EK',
     'Verhältnis Buying_Price ÷ Selling_Price = Median 60,6 % (P25–P75: 49–68 %). Liegt im typischen B-Ware-Bereich für Einkaufspreise. EK-Konvention plausibel.'),
    ('4', 'BERÜCKSICHTIGT', AMBER_BG, AMBER,
     '0 €-Einträge in der Datei',
     '360 von 3.256 matched-Geräten haben EK = 0 € — vor allem Set-Artikel-Kochfelder, deren EK am Hauptartikel des Kombi-Sets hängt. Kein Datenfehler; korrekt mit 0 € stehengelassen.'),
    ('5', 'GESCHLOSSEN', GREEN_BG, GREEN,
     'Blind Spot 29.05 – 01.06',
     'Zweite All-Sold-Datei (Cutoff 01.06.2026) hinzugezogen: 279 Verkäufe zwischen 29.05 und 01.06 verifiziert. Diese Geräte waren am Stichtag noch physisch im Lager → korrekt in der Bewertung enthalten.'),
    ('6', 'BESTÄTIGT', GREEN_BG, GREEN,
     'Set-Artikel-Paletten realistisch bewertet',
     '581 Paletten matched: Median EK 61 € (Max 258 €). 799/820 Set-Artikel haben Anzahl ≠ 1 = echte Sammelposten. Ø 50 €/Palette spiegelt elvincis tatsächlich günstigen Sammelposten-Einkauf wider.'),
    ('7', 'BESTÄTIGT', GREEN_BG, GREEN,
     'Keine Duplikate im BESTAND',
     '0 Lager-Nrn doppelt. Jede Lager-Nr genau einmal vertreten. Kein Risiko der Doppelzählung in der Bewertungssumme.'),
    ('8', 'BERÜCKSICHTIGT', AMBER_BG, AMBER,
     'AA-Status (Auftragsbindung)',
     f'{F["aa_real_at_2905"]} Geräte mit Auftragsbindung physisch im Lager, ohne Portal-EK. Schätzung mit Ø EK matched (95 €) = {eur(AA_EST)}. In der Hochrechnung enthalten. ±20 % Bandbreite.'),
    ('9', 'BESTÄTIGT', GREEN_BG, GREEN,
     'Paletten-Detail eingebunden',
     f'Zusätzliche Quelle (unsold_pallets_products.xlsx) liefert für 17 gemischte Paletten die {PALETTEN_DEV} Einzelgerät-EKs (Σ {eur(PALETTEN_EK)}). Cross-Check: alle 17 in BESTAND-QE, keine in Stock-Analysis, keine vor 29.05 verkauft → keine Doppelzählung. Ersetzt vorherige Ø-Schätzung von 1,8 k € durch exakte 18,1 k € (+16,3 k € Uplift).'),
]

for num, status, bg, fg, title, body in checks:
    # Number circle
    num_p = Paragraph(f'<font color="{fg.hexval()}"><b>{num}</b></font>',
        ParagraphStyle('cn', fontName='Helvetica-Bold', fontSize=14, leading=18,
                       alignment=TA_CENTER))
    num_cell = Table([[num_p]], colWidths=[0.9*cm], rowHeights=[0.9*cm])
    num_cell.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), bg),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('LEFTPADDING', (0,0), (-1,-1), 0),
        ('RIGHTPADDING', (0,0), (-1,-1), 0),
        ('TOPPADDING', (0,0), (-1,-1), 0),
        ('BOTTOMPADDING', (0,0), (-1,-1), 0),
    ]))
    title_p = Paragraph(f'<b>{title}</b>',
        ParagraphStyle('ct', fontName='Helvetica-Bold', fontSize=10.5,
                       leading=13, textColor=INK))
    body_p = Paragraph(body, BODY)
    sb = status_badge(status, bg, fg)

    title_row = Table([[title_p, sb]], colWidths=[12.6*cm, 2.5*cm])
    title_row.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('LEFTPADDING', (0,0), (-1,-1), 0),
        ('RIGHTPADDING', (0,0), (-1,-1), 0),
        ('ALIGN', (1,0), (1,0), 'RIGHT'),
    ]))

    right_stack = Table(
        [[title_row], [Spacer(1, 4)], [body_p]],
        colWidths=[15.2*cm]
    )
    right_stack.setStyle(TableStyle([
        ('LEFTPADDING', (0,0), (-1,-1), 0),
        ('RIGHTPADDING', (0,0), (-1,-1), 0),
        ('TOPPADDING', (0,0), (-1,-1), 0),
        ('BOTTOMPADDING', (0,0), (-1,-1), 0),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
    ]))

    row = Table([[num_cell, right_stack]],
                colWidths=[1.1*cm, 15.5*cm])
    row.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('LEFTPADDING', (0,0), (-1,-1), 0),
        ('RIGHTPADDING', (0,0), (-1,-1), 0),
        ('TOPPADDING', (0,0), (-1,-1), 0),
        ('BOTTOMPADDING', (0,0), (-1,-1), 0),
    ]))
    story.append(KeepTogether(row))
    story.append(Spacer(1, 0.35*cm))

# =================================================
# 4. DETAIL-AUFSCHLÜSSELUNG
# =================================================
story.append(PageBreak())
for f in section_title('Detail', 'Wo der Wert konkret liegt'):
    story.append(f)

# Three cards in a row
def detail_card(title, value, body, width=8.2):
    label_p = Paragraph(title.upper(),
        ParagraphStyle('dl', fontName='Helvetica-Bold', fontSize=8,
                       leading=10, textColor=SUBTLE, textTransform='uppercase'))
    val_p = Paragraph(f'<b>{value}</b>',
        ParagraphStyle('dv', fontName='Helvetica-Bold', fontSize=18,
                       leading=22, textColor=INK))
    body_p = Paragraph(body, ParagraphStyle('db', fontName='Helvetica',
                       fontSize=8.5, leading=12, textColor=INK_SOFT))
    t = Table([[label_p],[Spacer(1,2)],[val_p],[Spacer(1,6)],[body_p]],
              colWidths=[width*cm])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), CARD),
        ('LEFTPADDING', (0,0), (-1,-1), 12),
        ('RIGHTPADDING', (0,0), (-1,-1), 12),
        ('TOPPADDING', (0,0), (0,0), 12),
        ('BOTTOMPADDING', (0,-1), (-1,-1), 12),
        ('LEFTPADDING', (0,1), (-1,1), 12),
        ('RIGHTPADDING', (0,1), (-1,1), 12),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
    ]))
    return t

d1 = detail_card('1. Stock-Analysis (Portal)', eur(BELASTBAR_STOCK),
    f'{F["qe_matched"]:,} Geräte gematcht. {F["qe_matched_nonzero"]:,} mit EK&gt;0, '
    f'{F["qe_matched_zero"]} mit EK = 0 € (Set-Komponenten — EK am Hauptartikel).'.replace(',', '.'))
d2 = detail_card('2. Paletten-Detail', eur(PALETTEN_EK),
    f'{PALETTEN_N} Paletten mit Einzelgerät-Aufstellung ({PALETTEN_DEV} Geräte). '
    f'EXAKTE EKs aus separater Quelle — keine Schätzung mehr nötig.')
d3 = detail_card('3. Rest-Schätzung', eur(UNMATCHED_REST),
    f'{UNMATCHED_RESTN} Geräte ohne EK-Daten (Klassif.-Rückstand, ELHR). '
    f'Schätzung Ø EK je Bezeichnung. ±10 %.')
d4 = detail_card('4. AA-Auftragsbindung', eur(AA_EST),
    f'{F["aa_real_at_2905"]} Geräte mit Auftrag, physisch im Lager. '
    f'Schätzung Ø EK matched (95 €).')
detail_row1 = Table([[d1, d2]], colWidths=[8.5*cm, 8.5*cm])
detail_row1.setStyle(TableStyle([
    ('VALIGN', (0,0), (-1,-1), 'TOP'),
    ('LEFTPADDING', (0,0), (-1,-1), 0),
    ('RIGHTPADDING', (0,0), (-1,-1), 0),
]))
story.append(detail_row1)
story.append(Spacer(1, 0.3*cm))
detail_row = Table([[d3, d4]], colWidths=[8.5*cm, 8.5*cm])
detail_row.setStyle(TableStyle([
    ('VALIGN', (0,0), (-1,-1), 'TOP'),
    ('LEFTPADDING', (0,0), (-1,-1), 0),
    ('RIGHTPADDING', (0,0), (-1,-1), 0),
]))
story.append(detail_row)

story.append(Spacer(1, 0.4*cm))

# Quellen
for f in section_title('Datenquellen', 'Vier unabhängige Snapshots'):
    story.append(f)

sources = [
    ['Quelle', 'Datum', 'Inhalt', 'Verwendung'],
    ['BESTAND (AMM)', '29.05.2026',
     f'{F["bestand_total"]:,} Zeilen, alle Status'.replace(',', '.'),
     'Physische Bestandsbasis'],
    ['Stock-Analysis (Portal)', '01.06.2026',
     f'{F["stock_total"]:,} verkaufsbereite Artikel'.replace(',', '.'),
     'EK-Preise (Buying_Price)'],
    ['All-Sold (kombiniert)', F['allsold_combined_range'],
     f'{F["allsold_combined_rows"]:,} Verkäufe'.replace(',', '.'),
     'Status-Lag-Bereinigung'],
    ['Unsold-Pallets-Detail', '01.06.2026',
     f'{PALETTEN_DEV} Einzelgeräte in {PALETTEN_N} Paletten',
     'Exakte EKs für gemischte Paletten'],
]
ts = Table(sources, colWidths=[4.5*cm, 3.2*cm, 5*cm, 4.3*cm])
ts.setStyle(TableStyle([
    ('BACKGROUND', (0,0), (-1,0), INK),
    ('TEXTCOLOR', (0,0), (-1,0), colors.white),
    ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
    ('FONTSIZE', (0,0), (-1,0), 8),
    ('TEXTTRANSFORM', (0,0), (-1,0), 'uppercase'),
    ('FONTSIZE', (0,1), (-1,-1), 9),
    ('FONTNAME', (0,1), (0,-1), 'Helvetica-Bold'),
    ('TEXTCOLOR', (0,1), (-1,-1), INK_SOFT),
    ('TEXTCOLOR', (0,1), (0,-1), INK),
    ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ('LEFTPADDING', (0,0), (-1,-1), 10),
    ('RIGHTPADDING', (0,0), (-1,-1), 10),
    ('TOPPADDING', (0,0), (-1,-1), 8),
    ('BOTTOMPADDING', (0,0), (-1,-1), 8),
    ('LINEBELOW', (0,0), (-1,-1), 0.4, DIVIDER),
    ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, PAPER]),
]))
story.append(ts)

story.append(Spacer(1, 0.5*cm))

# Methodik-Box
for f in section_title('Formel', 'Bewertungsmethode & Restrisiken'):
    story.append(f)

method_text = (
    "<b>Bewertungsformel:</b> Σ Buying_Price (Stock-Analysis) je Lager-Nr aus "
    "BESTAND-QE, sofern nicht bereits vor dem 29.05.2026 in All-Sold verkauft. "
    "Für 17 gemischte Paletten: Σ Unit_Price aus Unsold-Pallets-Detail-Datei (exakt). "
    "Für 491 Restgeräte ohne EK-Daten: Ø EK je Bezeichnung der gematchten Vergleichsgruppe.<br/><br/>"
    "<b>Ausgeschlossen:</b> Status VS (Versand-Pipeline = Forderung) und 1.057 QE-Geräte "
    "mit Status-Lag (faktisch verkauft, AMM-Status nachhinkend).<br/><br/>"
    "<b>Restrisiken (nach KILLCRITIC):</b> Schätzung der 491 nicht im Portal "
    "gelisteten Einzelgeräte (±10 % ≈ ±4,3 k €) sowie 88 AA-Geräte (±20 % ≈ ±2 k €). "
    "Gesamt-Bandbreite Inventur: ~374 k € … ~387 k €."
)
method_p = Paragraph(method_text, BODY_J)

mt = Table([[method_p]], colWidths=[16.6*cm])
mt.setStyle(TableStyle([
    ('BACKGROUND', (0,0), (-1,-1), BLUE_BG),
    ('LEFTPADDING', (0,0), (-1,-1), 16),
    ('RIGHTPADDING', (0,0), (-1,-1), 16),
    ('TOPPADDING', (0,0), (-1,-1), 14),
    ('BOTTOMPADDING', (0,0), (-1,-1), 14),
    ('LINEABOVE', (0,0), (-1,0), 2, BLUE),
]))
story.append(mt)

story.append(Spacer(1, 0.5*cm))

# Closing line
story.append(divider())
story.append(Paragraph(
    'Reproduzierbar: Quellcode (lagerwert_pdf.py) und Roh-Auswertung '
    '(lagerwert_facts.json) im GitHub-Repo lagerkapazit-t. '
    'DSGVO: keine personenbezogenen Daten enthalten.',
    SMALL
))

# =================================================
doc.build(story, onFirstPage=header_footer, onLaterPages=header_footer)
print(f'PDF erstellt: {OUT.resolve()}')
print(f'Endzahlen:')
print(f'  Belastbar (Stock+Paletten):  {eur(BELASTBAR)}')
print(f'  + Paletten exakt:            +{eur(PALETTEN_EK)} (von {eur(BELASTBAR_STOCK)} Stock)')
print(f'  + Rest-Schaetzung:           +{eur(UNMATCHED_REST)}')
print(f'  + AA:                        +{eur(AA_EST)}')
print(f'  HOCHRECHNUNG:                {eur(INVENTUR)}')
