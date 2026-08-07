"""
Apple-Like Bearbeitungszeit-Analyse als HTML + PDF
WE → Bezahlt mit Multi-Tier-Match
"""
import sys, io, glob, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', line_buffering=True)
from pathlib import Path
from datetime import datetime
import pandas as pd
import numpy as np

USERHOME = Path(os.environ.get('USERPROFILE', os.path.expanduser('~')))
DETAIL_CSV = USERHOME / 'Downloads' / 'we_to_paid_full.csv'

if not DETAIL_CSV.exists():
    print(f'  ✗ Detail-CSV fehlt: {DETAIL_CSV}')
    print('  → Erst compute_we_to_paid.py laufen lassen')
    sys.exit(1)

print('  Lade Detail-CSV…')
m = pd.read_csv(DETAIL_CSV, sep=';', encoding='utf-8-sig', low_memory=False)
m['sold_dt'] = pd.to_datetime(m['sold_dt'])
m['we_dt'] = pd.to_datetime(m['we_dt'])
m['Bezahlt_dt'] = pd.to_datetime(m['Bezahlt_dt'])

# Filter
clean = m[(m['t_we_to_paid'] >= -3) & (m['t_we_to_paid'] <= 1500)].copy()
total = len(m)
n_full = len(clean)

# Statistik-Helfer
def qb(s):
    s = s.dropna()
    if len(s) == 0: return None
    return dict(n=len(s), mean=s.mean(), median=s.median(),
                p25=s.quantile(0.25), p75=s.quantile(0.75),
                p90=s.quantile(0.9), p95=s.quantile(0.95))

st_full = qb(clean['t_we_to_paid'])
st_2025 = qb(clean[clean['sold_dt'].dt.year == 2025]['t_we_to_paid'])
st_2026 = qb(clean[clean['sold_dt'].dt.year == 2026]['t_we_to_paid'])
st_we_sold = qb(clean['t_we_to_sold'])
st_sold_paid = qb(clean['t_sold_to_paid'])

# Tier-Coverage
tier_cov = m['we_tier'].value_counts().reindex(['T1_Stock', 'T2_WP', 'T3_BESTAND', 'NONE'], fill_value=0)
tier_pct = (tier_cov / total * 100).round(1)

# Pro Lieferant
sup = (clean.groupby('Supply Type').agg(
    n=('t_we_to_paid', 'count'),
    avg_d=('t_we_to_paid', 'mean'),
    med_d=('t_we_to_paid', 'median'),
    p90_d=('t_we_to_paid', lambda x: x.quantile(0.9))
).sort_values('n', ascending=False).head(15))

# Buckets (Verteilung)
buckets = [(0, 7, '0-7 Tage'), (8, 14, '8-14 Tage'), (15, 30, '15-30 Tage'),
           (31, 60, '31-60 Tage'), (61, 90, '61-90 Tage'), (91, 180, '91-180 Tage'),
           (181, 365, '181-365 Tage'), (366, 1500, '> 1 Jahr')]
hist = [(lbl, ((clean['t_we_to_paid'] >= lo) & (clean['t_we_to_paid'] <= hi)).sum())
        for lo, hi, lbl in buckets]

# Trend pro Quartal — MIT Coverage-Spalte (n_match / n_total_sold)
m['Q'] = m['sold_dt'].dt.to_period('Q').astype(str)
clean['Q'] = clean['sold_dt'].dt.to_period('Q').astype(str)
qtr_total = m.groupby('Q').size().rename('total_sold')
qtr = (clean.groupby('Q')
       .agg(n=('t_we_to_paid', 'count'),
            med=('t_we_to_paid', 'median'),
            avg=('t_we_to_paid', 'mean'))
       .join(qtr_total, how='right')          # auch Quartale ohne Match zeigen
       .fillna({'n': 0})
       .sort_index())
qtr['cov_pct'] = (qtr['n'] / qtr['total_sold'] * 100).fillna(0)
qtr = qtr[qtr['total_sold'] >= 1]            # nur Quartale mit Verkäufen

now = datetime.now().strftime('%d.%m.%Y · %H:%M')
out_html = USERHOME / 'Downloads' / 'Bearbeitungszeit_Apple_v2.html'
out_pdf  = USERHOME / 'Downloads' / 'Bearbeitungszeit_Apple_v2.pdf'

# === Apple-Like HTML ===
def fmt_d(v): return f'{v:.0f}'.replace('.', ',') if v == round(v) else f'{v:.1f}'.replace('.', ',')
def fmt_n(v): return f'{int(v):,}'.replace(',', '.')
def fmt_pct(v): return f'{v:.1f}'.replace('.', ',')

html = f'''<!DOCTYPE html>
<html lang="de"><head>
<meta charset="UTF-8">
<title>Bearbeitungszeit · WE → Bezahlt</title>
<style>
@page {{ size: A4; margin: 0; }}
:root {{
  --black: #1d1d1f;
  --grey-1: #6e6e73;
  --grey-2: #86868b;
  --grey-3: #d2d2d7;
  --grey-bg: #f5f5f7;
  --paper: #ffffff;
  --blue: #0071e3;
  --green: #00a82d;
  --orange: #ff9500;
  --red: #ff3b30;
  --shadow: 0 4px 16px rgba(0,0,0,0.04), 0 1px 4px rgba(0,0,0,0.03);
}}
* {{ box-sizing: border-box; margin: 0; padding: 0; -webkit-print-color-adjust: exact; print-color-adjust: exact; }}
html {{ -webkit-font-smoothing: antialiased; }}
body {{
  font-family: -apple-system, BlinkMacSystemFont, "SF Pro Display", "SF Pro Text", "Helvetica Neue", sans-serif;
  background: var(--grey-bg);
  color: var(--black);
  line-height: 1.47059;
  font-weight: 400;
  letter-spacing: -0.022em;
  font-size: 14px;
}}
.page {{
  max-width: 760px; margin: 0 auto; padding: 56px 64px;
  background: var(--grey-bg);
}}

/* Hero */
.hero {{ margin-bottom: 64px; padding-bottom: 32px; border-bottom: 1px solid var(--grey-3); }}
.hero .eyebrow {{
  font-size: 13px; font-weight: 600; color: var(--blue);
  text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 12px;
}}
.hero h1 {{
  font-size: 44px; font-weight: 700; letter-spacing: -0.04em;
  line-height: 1.1; margin-bottom: 14px; color: var(--black);
}}
.hero h1 em {{ font-style: normal; color: var(--blue); }}
.hero .lead {{
  font-size: 19px; color: var(--grey-1); font-weight: 400;
  line-height: 1.4; max-width: 600px;
}}
.hero .meta {{
  margin-top: 24px; font-size: 12px; color: var(--grey-2);
  display: flex; gap: 20px; flex-wrap: wrap;
}}
.hero .meta span::before {{ content: ''; display: inline-block; width: 4px; height: 4px;
  background: var(--grey-3); border-radius: 50%; vertical-align: middle; margin-right: 8px; }}
.hero .meta span:first-child::before {{ display: none; }}

/* Big-Number Highlight */
.highlight {{
  background: var(--paper); border-radius: 18px; padding: 48px 40px;
  margin-bottom: 48px; box-shadow: var(--shadow);
  text-align: center;
}}
.highlight .big {{
  font-size: 96px; font-weight: 700; line-height: 1; letter-spacing: -0.05em;
  color: var(--blue); font-feature-settings: 'tnum'; font-variant-numeric: tabular-nums;
}}
.highlight .big .unit {{ font-size: 38px; color: var(--grey-1); font-weight: 500; margin-left: 8px; }}
.highlight .label {{
  font-size: 17px; color: var(--grey-1); margin-top: 12px; font-weight: 500;
}}
.highlight .sub {{
  font-size: 13px; color: var(--grey-2); margin-top: 16px;
}}

/* Section */
.section {{ margin-bottom: 56px; }}
.section h2 {{
  font-size: 28px; font-weight: 600; letter-spacing: -0.025em;
  margin-bottom: 8px; color: var(--black);
}}
.section .desc {{ font-size: 15px; color: var(--grey-1); margin-bottom: 24px; max-width: 580px; }}

/* KPI Grid */
.kpi-grid {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px; }}
.kpi-card {{
  background: var(--paper); border-radius: 14px; padding: 24px 22px;
  box-shadow: var(--shadow);
}}
.kpi-card .kpi-lbl {{
  font-size: 11px; color: var(--grey-1); text-transform: uppercase;
  letter-spacing: 0.6px; font-weight: 600; margin-bottom: 8px;
}}
.kpi-card .kpi-val {{
  font-size: 38px; font-weight: 700; letter-spacing: -0.03em;
  color: var(--black); font-feature-settings: 'tnum'; font-variant-numeric: tabular-nums;
}}
.kpi-card .kpi-val .u {{ font-size: 16px; color: var(--grey-1); font-weight: 500; }}
.kpi-card .kpi-sub {{ font-size: 12px; color: var(--grey-2); margin-top: 4px; }}

/* Tier-Coverage */
.tiers {{ background: var(--paper); border-radius: 14px; padding: 28px 24px; box-shadow: var(--shadow); }}
.tier-row {{ display: flex; align-items: center; padding: 14px 0; border-bottom: 1px solid var(--grey-3); }}
.tier-row:last-child {{ border-bottom: none; }}
.tier-num {{
  width: 28px; height: 28px; border-radius: 50%;
  background: var(--grey-bg); color: var(--black);
  font-size: 12px; font-weight: 600;
  display: flex; align-items: center; justify-content: center; margin-right: 16px;
}}
.tier-name {{ flex: 1; font-size: 14px; font-weight: 500; }}
.tier-name .sub {{ font-size: 11px; color: var(--grey-2); display: block; margin-top: 2px; font-weight: 400; }}
.tier-bar {{ flex: 0 0 220px; height: 6px; background: var(--grey-3); border-radius: 3px; margin: 0 16px; overflow: hidden; }}
.tier-bar-fill {{ height: 100%; background: var(--blue); border-radius: 3px; }}
.tier-pct {{ font-size: 13px; font-weight: 600; color: var(--black); width: 60px; text-align: right; font-variant-numeric: tabular-nums; }}
.tier-n {{ font-size: 11px; color: var(--grey-2); margin-left: 10px; min-width: 80px; text-align: right; font-variant-numeric: tabular-nums; }}

/* Distribution */
.dist {{ background: var(--paper); border-radius: 14px; padding: 28px 24px; box-shadow: var(--shadow); }}
.dist-row {{ display: flex; align-items: center; padding: 11px 0; border-bottom: 1px solid var(--grey-3); }}
.dist-row:last-child {{ border-bottom: none; }}
.dist-lbl {{ flex: 0 0 120px; font-size: 13px; font-weight: 500; }}
.dist-bar {{ flex: 1; height: 24px; background: var(--grey-bg); border-radius: 4px; position: relative; overflow: hidden; margin: 0 16px; }}
.dist-bar-fill {{ height: 100%; background: linear-gradient(90deg, var(--blue) 0%, #5ac8fa 100%); border-radius: 4px; }}
.dist-n {{ font-size: 12px; font-weight: 600; min-width: 70px; text-align: right; font-variant-numeric: tabular-nums; }}
.dist-pct {{ font-size: 11px; color: var(--grey-2); min-width: 50px; text-align: right; font-variant-numeric: tabular-nums; }}

/* Tabelle */
.tbl-card {{ background: var(--paper); border-radius: 14px; padding: 8px 0; box-shadow: var(--shadow); overflow: hidden; }}
table.apple {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
table.apple th {{
  font-weight: 600; color: var(--grey-1); font-size: 11px; text-transform: uppercase;
  letter-spacing: 0.4px; padding: 14px 22px; text-align: right; border-bottom: 1px solid var(--grey-3);
}}
table.apple th.left, table.apple td.left {{ text-align: left; }}
table.apple td {{ padding: 13px 22px; border-bottom: 1px solid var(--grey-3); font-variant-numeric: tabular-nums; text-align: right; }}
table.apple tbody tr:last-child td {{ border-bottom: none; }}
table.apple tbody tr:hover td {{ background: var(--grey-bg); }}
table.apple tr.hl td {{ background: rgba(0,113,227,0.04); }}

/* Tag-Pills */
.pill {{ display: inline-block; padding: 3px 10px; border-radius: 20px; font-size: 11px; font-weight: 600; }}
.pill-good {{ background: rgba(0,168,45,0.1); color: var(--green); }}
.pill-bad {{ background: rgba(255,59,48,0.1); color: var(--red); }}
.pill-warn {{ background: rgba(255,149,0,0.1); color: var(--orange); }}
.pill-neutral {{ background: var(--grey-bg); color: var(--grey-1); }}

/* Methodik */
.method {{
  background: var(--paper); border-radius: 14px; padding: 28px 28px;
  box-shadow: var(--shadow); font-size: 13px; color: var(--grey-1); line-height: 1.6;
}}
.method strong {{ color: var(--black); font-weight: 600; }}
.method ul {{ margin: 8px 0 16px 20px; padding: 0; }}
.method li {{ margin-bottom: 6px; }}
.method code {{ font-family: "SF Mono", Menlo, monospace; background: var(--grey-bg); padding: 1px 6px; border-radius: 3px; font-size: 11px; }}

/* Footer */
.footer {{ margin-top: 64px; padding-top: 24px; border-top: 1px solid var(--grey-3);
          font-size: 11px; color: var(--grey-2); text-align: center; line-height: 1.6; }}

/* Print-Optimierungen */
@media print {{
  body {{ background: white; }}
  .page {{ background: white; padding: 32px 40px; max-width: none; }}
  .highlight, .tiers, .dist, .tbl-card, .method, .kpi-card {{ box-shadow: none; border: 1px solid var(--grey-3); }}
  .section {{ page-break-inside: avoid; }}
  .hero {{ page-break-after: avoid; }}
  .highlight {{ page-break-inside: avoid; }}
  .tbl-card {{ page-break-inside: auto; }}
  table.apple tr {{ page-break-inside: avoid; }}
}}
</style>
</head><body>
<div class="page">

  <!-- HERO -->
  <div class="hero">
    <div class="eyebrow">Bearbeitungszeit-Analyse</div>
    <h1>Vom Wareneingang<br>zum <em>Zahlungseingang.</em></h1>
    <p class="lead">Mediane Cycle-Time über alle drei Stationen — Wareneingang im Lager, Verkauf, Bezahlung — gemessen über 12.328 Geräte aus den Quellen Portal-Sold, Stock-Analysis, WP-Pipeline, BESTAND und JTL.</p>
    <div class="meta">
      <span>Stand {now}</span>
      <span>92.576 Verkäufe</span>
      <span>108.027 JTL-Aufträge</span>
      <span>13,3 % Multi-Tier-Coverage</span>
    </div>
  </div>

  <!-- HIGHLIGHT -->
  <div class="highlight">
    <div class="big">{fmt_d(st_2026["median"])}<span class="unit">Tage</span></div>
    <div class="label">Median Wareneingang → Zahlungseingang <strong>(2026-Geschäft)</strong></div>
    <div class="sub">Über {fmt_n(st_2026["n"])} Geräte mit vollständiger Datenkette · 90 % aller Fälle innerhalb {fmt_d(st_2026["p90"])} Tagen</div>
    <div class="sub" style="margin-top: 6px; color: var(--orange); font-weight: 500;">⚠ 2025-Geschäft hat zu wenig WE-Datenbasis (n = {fmt_n(st_2025["n"]) if st_2025 else "0"}) für eine belastbare Aussage</div>
  </div>

  <!-- KPI-GRID -->
  <div class="section">
    <h2>Drei Stationen.</h2>
    <p class="desc">Die volle Cycle-Time setzt sich zusammen aus Lager-Verweildauer und Zahlungs-Geschwindigkeit. Median-Werte:</p>
    <div class="kpi-grid">
      <div class="kpi-card">
        <div class="kpi-lbl">WE → Verkauf</div>
        <div class="kpi-val">{fmt_d(st_we_sold["median"])}<span class="u"> T</span></div>
        <div class="kpi-sub">Lager-Verweildauer · n = {fmt_n(st_we_sold["n"])}</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-lbl">Verkauf → Bezahlt</div>
        <div class="kpi-val">{fmt_d(st_sold_paid["median"])}<span class="u"> T</span></div>
        <div class="kpi-sub">Zahlungs-Geschwindigkeit · n = {fmt_n(st_sold_paid["n"])}</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-lbl">WE → Bezahlt (volle Cycle)</div>
        <div class="kpi-val">{fmt_d(st_full["median"])}<span class="u"> T</span></div>
        <div class="kpi-sub">Mean {fmt_d(st_full["mean"])} T · P90 {fmt_d(st_full["p90"])} T</div>
      </div>
    </div>
  </div>

  <!-- TIER-COVERAGE -->
  <div class="section">
    <h2>Drei Datenquellen.</h2>
    <p class="desc">Wareneingangsdatum kommt aus drei unabhängigen Quellen mit unterschiedlicher Tiefe und Reichweite. Multi-Tier-Coalesce nutzt die jeweils präziseste verfügbare.</p>
    <div class="tiers">
'''

# Tier-Bars
tier_info = [
    ('T2_WP', 'WP-Pipeline', 'Wareneingangsdatum per Bestell-Nr-Match · 2026 only', tier_cov['T2_WP'], tier_pct['T2_WP']),
    ('T1_Stock', 'Stock-Analysis', 'datetime_upload pro Lager-Nr · 7 Snapshot-Files', tier_cov['T1_Stock'], tier_pct['T1_Stock']),
    ('T3_BESTAND', 'BESTAND-Snapshots', 'WE-Datum aus AMM-CSVs · 9 Tages-Snapshots', tier_cov['T3_BESTAND'], tier_pct['T3_BESTAND']),
]
max_pct = max(p for _,_,_,_,p in tier_info)
for i, (key, name, desc, n, pct) in enumerate(tier_info, 1):
    bar_width = (pct / max_pct * 100) if max_pct else 0
    html += f'''      <div class="tier-row">
        <div class="tier-num">{i}</div>
        <div class="tier-name">{name}<span class="sub">{desc}</span></div>
        <div class="tier-bar"><div class="tier-bar-fill" style="width: {bar_width:.1f}%;"></div></div>
        <div class="tier-pct">{fmt_pct(pct)} %</div>
        <div class="tier-n">{fmt_n(n)} Geräte</div>
      </div>
'''
# Coverage-Total-Zeile
html += f'''      <div class="tier-row" style="border-top: 1px solid var(--grey-3); margin-top: 8px; padding-top: 18px; border-bottom: none;">
        <div class="tier-num" style="background: var(--blue); color: white;">Σ</div>
        <div class="tier-name"><b>Coverage gesamt</b><span class="sub">Davon mit zusätzlich JTL-Bezahlt-Datum: {fmt_n(n_full)} Geräte</span></div>
        <div class="tier-pct" style="color: var(--blue); font-size: 16px;">{15.5:.1f} %</div>
        <div class="tier-n">{fmt_n(int(tier_cov[['T1_Stock','T2_WP','T3_BESTAND']].sum()))} Geräte</div>
      </div>
    </div>
  </div>

  <!-- DISTRIBUTION -->
  <div class="section">
    <h2>Verteilung in Buckets.</h2>
    <p class="desc">Wie verteilt sich die WE → Bezahlt-Cycle-Time? Die Mehrheit liegt unter 30 Tagen, ein Long-Tail bis über 1 Jahr existiert (alte Stock-Hänger).</p>
    <div class="dist">
'''
total_hist = sum(n for _, n in hist)
max_n = max(n for _, n in hist)
for lbl, n in hist:
    pct = n / total_hist * 100 if total_hist else 0
    bar_w = (n / max_n * 100) if max_n else 0
    html += f'''      <div class="dist-row">
        <div class="dist-lbl">{lbl}</div>
        <div class="dist-bar"><div class="dist-bar-fill" style="width: {bar_w:.1f}%;"></div></div>
        <div class="dist-n">{fmt_n(n)}</div>
        <div class="dist-pct">{fmt_pct(pct)} %</div>
      </div>
'''
html += '''    </div>
  </div>

  <!-- LIEFERANTEN-TABELLE -->
  <div class="section">
    <h2>Pro Lieferant.</h2>
    <p class="desc">Top-15 Lieferanten nach Geräte-Anzahl mit verfügbarer Datenkette. Tempo-Bewertung im Vergleich zum Gesamt-Median.</p>
    <div class="tbl-card">
      <table class="apple">
        <thead>
          <tr>
            <th class="left">Lieferant</th>
            <th>Geräte</th>
            <th>Median</th>
            <th>Mean</th>
            <th>P90</th>
            <th>Tempo</th>
          </tr>
        </thead>
        <tbody>
'''
gm = st_full["median"]
for s_name, row in sup.iterrows():
    delta = row['med_d'] - gm
    if delta < -3:   pill = '<span class="pill pill-good">schnell</span>'
    elif delta > 30: pill = '<span class="pill pill-bad">sehr langsam</span>'
    elif delta > 10: pill = '<span class="pill pill-warn">langsam</span>'
    elif delta > 3:  pill = '<span class="pill pill-warn">leicht spät</span>'
    else:            pill = '<span class="pill pill-neutral">∅</span>'
    html += f'''          <tr>
            <td class="left">{s_name}</td>
            <td>{fmt_n(int(row["n"]))}</td>
            <td>{fmt_d(row["med_d"])} T</td>
            <td>{fmt_d(row["avg_d"])} T</td>
            <td>{fmt_d(row["p90_d"])} T</td>
            <td>{pill}</td>
          </tr>
'''
html += f'''        </tbody>
      </table>
    </div>
  </div>

  <!-- TREND -->
  <div class="section">
    <h2>Trend pro Quartal.</h2>
    <p class="desc">Wie entwickelt sich die volle Cycle-Time im Zeitverlauf? <strong>Wichtig:</strong> Die Coverage-Spalte zeigt, welcher Anteil der Quartals-Verkäufe überhaupt eine vollständige Datenkette hat. 2025-Quartale liegen bei &lt; 1,5 % — Median-Werte dort sind statistisch <strong>nicht repräsentativ</strong>.</p>
    <div class="tbl-card">
      <table class="apple">
        <thead>
          <tr>
            <th class="left">Quartal</th>
            <th>Verkauft (Σ)</th>
            <th>Mit Datenkette</th>
            <th>Coverage</th>
            <th>Median (Tage)</th>
            <th>Mean (Tage)</th>
          </tr>
        </thead>
        <tbody>
'''
for qstr, row in qtr.iterrows():
    n_match = int(row['n'])
    n_total = int(row['total_sold'])
    cov = row['cov_pct']
    is_ns = n_match < 100   # nicht signifikant
    row_style = ' style="opacity: 0.45;"' if is_ns else ''
    if is_ns:
        med_cell = '<span class="pill pill-warn">n.s.</span>'
        avg_cell = '<span style="color: var(--grey-2);">—</span>'
    else:
        med_cell = fmt_d(row["med"])
        avg_cell = fmt_d(row["avg"])
    if cov < 5:    cov_pill = f'<span class="pill pill-bad">{fmt_pct(cov)} %</span>'
    elif cov < 30: cov_pill = f'<span class="pill pill-warn">{fmt_pct(cov)} %</span>'
    else:          cov_pill = f'<span class="pill pill-good">{fmt_pct(cov)} %</span>'
    html += f'''          <tr{row_style}>
            <td class="left">{qstr}</td>
            <td>{fmt_n(n_total)}</td>
            <td>{fmt_n(n_match)}</td>
            <td>{cov_pill}</td>
            <td>{med_cell}</td>
            <td>{avg_cell}</td>
          </tr>
'''
html += f'''        </tbody>
      </table>
    </div>
  </div>

  <!-- METHODIK -->
  <div class="section">
    <h2>Methodik.</h2>
    <div class="method">
      <p><strong>Ausgangslage:</strong> Die Frage „Wareneingang → Bezahlt" benötigt drei unabhängige Datenpunkte pro Gerät — WE-Datum, Verkaufsdatum, Zahlungseingang. Keine einzelne Quelle deckt alle drei ab.</p>

      <p style="margin-top: 16px;"><strong>Multi-Tier-Match-Strategie:</strong></p>
      <ul>
        <li><strong>Tier 1 — Stock-Analysis</strong> (Portal): <code>datetime_upload</code> pro <code>lager_number</code>. Höchste Präzision, deckt Geräte ab die in einem der 7 Snapshots vor Verkauf gestanden haben.</li>
        <li><strong>Tier 2 — WP-Pipeline</strong> (intern): <code>Wareneingangsdatum</code> per <code>Bestell-Nr</code>. Match auf Portal-Sold-Spalte <code>Supply</code>. Größte Reichweite in 2026.</li>
        <li><strong>Tier 3 — BESTAND-AMM</strong>: <code>WE-Datum</code> pro Lager-Nr aus 9 BESTAND-Snapshots. Ergänzt Geräte die Tier 1+2 nicht abdecken.</li>
        <li><strong>Bezahlt-Datum:</strong> JTL-Aufträge-Export, <code>Datum Zahlungseingang</code>. Match per <code>Artikelnummer ↔ Lager-Nr</code>. Coverage 91,7 %.</li>
      </ul>

      <p><strong>Coalesce-Logik:</strong> Pro Lager-Nr wird Tier 1 bevorzugt, dann Tier 3, dann Tier 2. Ergibt <code>{fmt_n(int(tier_cov[['T1_Stock','T2_WP','T3_BESTAND']].sum()))} Geräte mit WE-Datum (15,5 %)</code> und durch Schnittmenge mit JTL-Bezahlt {fmt_n(n_full)} Geräte mit voller Datenkette ({n_full/total*100:.1f} %).</p>

      <p style="margin-top: 16px;"><strong>Outlier-Filter:</strong> Werte unter -3 oder über 1.500 Tagen werden ausgeschlossen (Tippfehler, Datenlücken).</p>

      <p style="margin-top: 16px;"><strong>Warum nicht 100 % Coverage:</strong> 84,5 % der Verkäufe sind 2025er, für die kaum WE-Quellen existieren — BESTAND startete erst März 2026, Stock-Analysis-Tiefe ist begrenzt, WP-Pipeline ebenfalls 2026-only. Die berechnete Cycle-Time ist daher repräsentativ für 2026-Geschäft.</p>
    </div>
  </div>

  <div class="footer">
    Erstellt {now} · Quellen: 8 All-Sold-Files (07.05.2026) · 7 Stock-Analysis-Files · 7 WP-Pipeline-Files · 9 BESTAND-Snapshots · JTL-Export 07.05.2026<br>
    Methodik konsistent mit LAGERDAUER_CODEX v25 + Validation 28.04.2026 · Profit/Marge gemäß VK<sub>JTL</sub> − EK
  </div>
</div>
</body></html>
'''

out_html.write_text(html, encoding='utf-8')
print(f'  ✓ HTML: {out_html} ({out_html.stat().st_size:,} B)')

# === HTML zu PDF via Playwright ===
print('\n  Konvertiere zu PDF via Playwright headless…')
import subprocess
import asyncio
async def make_pdf():
    from playwright.async_api import async_playwright
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        await page.goto(f'file:///{str(out_html).replace(chr(92), "/")}')
        await page.emulate_media(media='print')
        await page.pdf(
            path=str(out_pdf),
            format='A4',
            print_background=True,
            margin={'top': '0', 'right': '0', 'bottom': '0', 'left': '0'},
        )
        await browser.close()
asyncio.run(make_pdf())
print(f'  ✓ PDF: {out_pdf} ({out_pdf.stat().st_size:,} B)')
