#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PDF: Bestandsbewertung Verpackungsmaterial zum Stichtag 31.08.2026
elvinci.de GmbH - Backoffice & Fulfillment
Hausstil analog generate_apple_pdf_2026_v3.py (HTML -> Chromium -> A4-PDF)
"""
from pathlib import Path
from datetime import datetime

OUT = Path(__file__).parent / '2026-08-31_Bestandsbewertung_Verpackungsmaterial_v1.pdf'

# --- Positionen: Menge x Nettopreis der letzten Lieferung -------------------
POSITIONEN = [
    # Bezeichnung, Artikel, Menge, ME, Preis, Preisbasis
    ("Einwegpaletten, alle Formate", "—",      1170, "Stk",   10.25,
     "ZELSEN, Preisliste ab 26.03.2026"),
    ("Wellpappe-Zuschnitte 1180 x 780 mm", "268144", 19400, "Stk", 0.2878,
     "Prodinger AB 20097713, 287,80 €/1.000 Stk"),
    ("Handstretchfolie transparent", "—",        40, "Ro.",    4.99,
     "Ahrbach Süd AN2602363"),
    ("PVC-Packband 50 mm x 66 m", "106598",      56, "Ro.",    1.47,
     "Prodinger AB 20055740"),
    ("Maschinenstretchfolie 500 x 0,023 mm", "517606", 0, "Ro.", 56.90,
     "Prodinger AB 20087796"),
]
SUMME = sum(m * p for _, _, m, _, p, _ in POSITIONEN)


def eur(v, dec=2):
    s = f'{v:,.{dec}f}'.replace(',', '#').replace('.', ',').replace('#', '.')
    return s


def num(v):
    return f'{v:,.0f}'.replace(',', '.')


rows = ""
for bez, art, menge, me, preis, basis in POSITIONEN:
    wert = menge * preis
    dim = ' class="null"' if menge == 0 else ''
    artikel = f'<span class="art">{art}</span>' if art != "—" else ''
    rows += f'''
    <tr{dim}>
      <td class="bez">{bez}{artikel}</td>
      <td class="r">{num(menge)} {me}</td>
      <td class="r">{eur(preis, 4 if preis < 1 else 2)} €</td>
      <td class="r strong">{eur(wert)} €</td>
      <td class="src">{basis}</td>
    </tr>'''

html = f'''<!DOCTYPE html>
<html lang="de"><head><meta charset="UTF-8">
<title>Bestandsbewertung Verpackungsmaterial 31.08.2026</title>
<style>
@page {{ size: A4; margin: 0; }}
* {{ box-sizing: border-box; margin: 0; padding: 0; -webkit-print-color-adjust: exact; print-color-adjust: exact; }}
:root {{
  --black: #1d1d1f; --grey-1: #6e6e73; --grey-2: #86868b; --grey-3: #d2d2d7;
  --grey-bg: #f5f5f7; --paper: #ffffff; --blue: #0071e3;
  --shadow: 0 4px 16px rgba(0,0,0,0.04), 0 1px 4px rgba(0,0,0,0.03);
}}
html {{ -webkit-font-smoothing: antialiased; }}
body {{
  font-family: -apple-system, BlinkMacSystemFont, "SF Pro Display", "SF Pro Text", "Helvetica Neue", sans-serif;
  background: var(--grey-bg); color: var(--black);
  line-height: 1.47; letter-spacing: -0.022em; font-size: 14px;
}}
.page {{ max-width: 760px; margin: 0 auto; padding: 52px 60px; background: var(--grey-bg); }}

.hero {{ margin-bottom: 34px; padding-bottom: 24px; border-bottom: 1px solid var(--grey-3); }}
.hero .eyebrow {{ font-size: 12px; font-weight: 600; color: var(--blue); text-transform: uppercase; letter-spacing: .5px; margin-bottom: 11px; }}
.hero h1 {{ font-size: 34px; font-weight: 700; letter-spacing: -.04em; line-height: 1.12; }}
.hero .sub {{ font-size: 15px; color: var(--grey-1); margin-top: 10px; }}
.hero .meta {{ margin-top: 16px; font-size: 11.5px; color: var(--grey-2); display: flex; gap: 18px; flex-wrap: wrap; }}
.hero .meta span::before {{ content:''; display:inline-block; width:4px; height:4px; background: var(--grey-3); border-radius:50%; vertical-align: middle; margin-right: 7px; }}

.headline {{ background: var(--paper); border-radius: 18px; padding: 32px 36px; margin-bottom: 34px; box-shadow: var(--shadow); text-align: center; }}
.headline .label {{ font-size: 11px; font-weight: 700; color: var(--grey-1); text-transform: uppercase; letter-spacing: .6px; }}
.headline .big {{ font-size: 54px; font-weight: 700; letter-spacing: -.045em; margin-top: 10px; line-height: 1; }}
.headline .big .unit {{ font-size: 26px; color: var(--grey-1); font-weight: 500; margin-left: 6px; letter-spacing: -.02em; }}
.headline .note {{ font-size: 13px; color: var(--grey-1); margin-top: 12px; }}

.section {{ margin-bottom: 32px; }}
.section h2 {{ font-size: 20px; font-weight: 600; letter-spacing: -.025em; margin-bottom: 14px; }}

table {{ width: 100%; border-collapse: collapse; background: var(--paper); border-radius: 14px; overflow: hidden; box-shadow: var(--shadow); }}
th {{ font-size: 10.5px; font-weight: 700; color: var(--grey-1); text-transform: uppercase; letter-spacing: .5px;
     text-align: left; padding: 13px 14px; background: #fafafa; border-bottom: 1px solid var(--grey-3); }}
td {{ padding: 13px 14px; font-size: 13px; border-bottom: 1px solid #ededf0; vertical-align: top; }}
tr:last-child td {{ border-bottom: none; }}
.r {{ text-align: right; white-space: nowrap; }}
.strong {{ font-weight: 600; }}
.bez {{ font-weight: 500; }}
.art {{ display: block; font-family: "SF Mono", Menlo, monospace; font-size: 10.5px; color: var(--grey-2); margin-top: 3px; letter-spacing: 0; }}
.src {{ font-size: 11px; color: var(--grey-1); }}
tr.null td {{ color: var(--grey-2); }}
tfoot td {{ background: #fafafa; border-top: 1.5px solid var(--grey-3); font-size: 14px; font-weight: 700; padding: 15px 14px; }}

.method {{ background: var(--paper); border-radius: 14px; padding: 22px 26px; box-shadow: var(--shadow); }}
.method p {{ font-size: 13px; color: var(--grey-1); line-height: 1.6; }}
.method .formula {{ font-family: "SF Mono", Menlo, monospace; background: var(--grey-bg); padding: 13px 16px;
   border-radius: 8px; margin: 14px 0 0; font-size: 11.5px; color: var(--black); letter-spacing: 0; line-height: 1.6; }}

.srclist {{ background: var(--paper); border-radius: 14px; padding: 8px 26px; box-shadow: var(--shadow); }}
.srclist .row {{ display: flex; gap: 16px; padding: 11px 0; border-bottom: 1px solid #ededf0; font-size: 12.5px; }}
.srclist .row:last-child {{ border-bottom: none; }}
.srclist .doc {{ font-family: "SF Mono", Menlo, monospace; font-size: 11px; color: var(--black); min-width: 210px; letter-spacing: 0; }}
.srclist .what {{ color: var(--grey-1); }}

.sign {{ margin-top: 38px; padding-top: 22px; border-top: 1px solid var(--grey-3); display: flex; gap: 60px; }}
.sign .box {{ flex: 1; }}
.sign .line {{ border-bottom: 1px solid var(--grey-3); height: 34px; }}
.sign .cap {{ font-size: 10.5px; color: var(--grey-2); margin-top: 7px; }}
.footer {{ margin-top: 26px; font-size: 10.5px; color: var(--grey-2); text-align: center; }}
</style></head>
<body><div class="page">

  <div class="hero">
    <div class="eyebrow">elvinci.de GmbH · Backoffice &amp; Fulfillment</div>
    <h1>Bestandsbewertung<br>Verpackungsmaterial</h1>
    <div class="sub">Stichtag 31.08.2026 · Geschäftsjahr 01.09.2025 – 31.08.2026 · Konto 4710</div>
    <div class="meta">
      <span>Lagerort AMM Spedition, Beuthener Str. 57, Nürnberg</span>
      <span>Erstellt {datetime.now().strftime('%d.%m.%Y')}</span>
      <span>Version v1</span>
    </div>
  </div>

  <div class="headline">
    <div class="label">Bestandswert zum 31.08.2026</div>
    <div class="big">{eur(SUMME)}<span class="unit">€ netto</span></div>
    <div class="note">Bewertung zu Anschaffungskosten der jeweils letzten Lieferung</div>
  </div>

  <div class="section">
    <h2>Positionen</h2>
    <table>
      <thead><tr>
        <th style="width:31%">Material</th><th class="r">Bestand</th><th class="r">€ / Einheit</th>
        <th class="r">Wert netto</th><th style="width:26%">Preisbasis</th>
      </tr></thead>
      <tbody>{rows}
      </tbody>
      <tfoot><tr>
        <td>Bestandswert Verpackungsmaterial</td><td></td><td></td>
        <td class="r">{eur(SUMME)} €</td><td></td>
      </tr></tfoot>
    </table>
  </div>

  <div class="section">
    <h2>Bewertungsmethode</h2>
    <div class="method">
      <p>Fortführung der in den Vorjahren angewandten Methode: Der Bestand je Artikel wird aus den
      Zugängen des Geschäftsjahres und dem Materialverbrauch bis zum Stichtag fortgeschrieben und
      mit dem Nettopreis der jeweils letzten Lieferung bewertet. Verbrauchsbasis ist die
      Bedarfsrechnung vom 15.07.2026 mit 250 Arbeitstagen im Jahr.</p>
      <div class="formula">Bestand = letzte Lieferung + Restbestand Vorlieferungen − Verbrauch/AT × AT bis Stichtag</div>
    </div>
  </div>

  <div class="section">
    <h2>Belegkette</h2>
    <div class="srclist">
      <div class="row"><div class="doc">ZELSEN, Lieferung 18.08.2026</div><div class="what">Einwegpaletten 100 × 80 und 120 × 80, ein LKW</div></div>
      <div class="row"><div class="doc">ZELSEN LS0007 / RE260005</div><div class="what">1.166 Paletten, 11.007,00 € netto — Referenz Ladungsgröße</div></div>
      <div class="row"><div class="doc">ZELSEN Preisliste 26.03.2026</div><div class="what">120 × 80 IPPC 10,50 € · 100 × 80 IPPC 10,25 € · 80 × 80 IPPC 9,90 €</div></div>
      <div class="row"><div class="doc">Prodinger AB 20097713</div><div class="what">Wellpappe-Zuschnitte 22.110 Stk, 6.363,26 € netto, Lieferung 19.08.2026</div></div>
      <div class="row"><div class="doc">Prodinger AB 20031858</div><div class="what">Wellpappe-Zuschnitte 22.110 Stk, Lieferung 23.03.2026 — Vorcharge</div></div>
      <div class="row"><div class="doc">Prodinger AB 20087796</div><div class="what">Maschinenstretchfolie 2 Paletten, Lieferung 22.07.2026</div></div>
      <div class="row"><div class="doc">Prodinger AB 20055740</div><div class="what">PVC-Packband 180 Rollen à 1,47 €, Lieferung 05.05.2026</div></div>
      <div class="row"><div class="doc">Bedarfsrechnung 15.07.2026</div><div class="what">Jahresbedarf je Artikel — Verbrauchsbasis</div></div>
    </div>
  </div>

  <div class="sign">
    <div class="box"><div class="line"></div><div class="cap">Erstellt · Backoffice &amp; Fulfillment</div></div>
    <div class="box"><div class="line"></div><div class="cap">Freigegeben · Geschäftsführung</div></div>
  </div>

  <div class="footer">elvinci.de GmbH · Ostendstraße 100 · 90482 Nürnberg · Bestandsbewertung Verpackungsmaterial 31.08.2026 · v1</div>
</div></body></html>'''

tmp = Path(__file__).parent / '_lagerwert_verpackung.html'
tmp.write_text(html, encoding='utf-8')

import subprocess
CHROME = '/opt/pw-browsers/chromium-1194/chrome-linux/chrome'
subprocess.run([CHROME, '--headless', '--disable-gpu', '--no-sandbox',
                '--no-pdf-header-footer', f'--print-to-pdf={OUT}',
                tmp.resolve().as_uri()], check=True,
               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

tmp.unlink()
print(f'Summe: {eur(SUMME)} EUR netto')
print(f'PDF:   {OUT} ({OUT.stat().st_size:,} B)')
