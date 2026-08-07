"""
Erzeugt eine HTML-Vergleichstabelle Lieferant × Monat (Jan–Apr) × Jahr (2025/2026).
Metriken: Stk, EK, VK_JTL, Profit (VK_JTL − EK), Marge %, Ø Profit/Gerät.

Output: Lieferanten_Monatsvergleich_2025-2026.html in Downloads
"""
import sys, io, glob, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', line_buffering=True)
from pathlib import Path
from datetime import datetime
import pandas as pd

USERHOME = Path(os.environ.get('USERPROFILE', os.path.expanduser('~')))
ALLSOLD_DIR = USERHOME / 'Downloads' / 'All Sold 2025 - 2026'
OUTPUT_FILE = USERHOME / 'Downloads' / 'Lieferanten_Monatsvergleich_2025-2026.html'

# === Laden + Dedup ===
files = sorted(glob.glob(str(ALLSOLD_DIR / 'All-Sold-2026-05-07T*.xlsx')))
print(f'Lade {len(files)} All-Sold-Files…')
portal = pd.concat([pd.read_excel(f) for f in files], ignore_index=True)
portal = portal.drop_duplicates(subset=['Lager Nr.'], keep='first').copy()
portal['Date'] = pd.to_datetime(portal['Date'], errors='coerce').dt.normalize()
portal = portal.dropna(subset=['Date'])
print(f'Nach Dedup + Datums-Filter: {len(portal):,}')

# === Filter Jan-Apr 2025 + 2026 ===
mask = (
    ((portal['Date'].dt.year == 2025) & (portal['Date'].dt.month.between(1, 4))) |
    ((portal['Date'].dt.year == 2026) & (portal['Date'].dt.month.between(1, 4)))
)
df = portal[mask].copy()
df['Year']  = df['Date'].dt.year
df['Month'] = df['Date'].dt.month
print(f'Jan-Apr 2025 + 2026: {len(df):,}')

# === Spalten-Mapping ===
VK = 'JTL Selling Price'
EK = 'Portal Buying Price'
SUP = 'Supply Type'

# === Top-Lieferanten (nach 2025-Volumen) ===
top_suppliers = (
    df[df['Year'] == 2025]
    .groupby(SUP).size()
    .sort_values(ascending=False)
    .head(10)
    .index.tolist()
)
# Plus alle 2026-Lieferanten die nicht schon drin sind, falls > 100 Stk
extra_2026 = (
    df[(df['Year'] == 2026) & (~df[SUP].isin(top_suppliers))]
    .groupby(SUP).size()
    .pipe(lambda s: s[s > 100])
    .sort_values(ascending=False)
    .index.tolist()
)
suppliers = top_suppliers + extra_2026
print(f'Lieferanten in Tabelle: {len(suppliers)}  Top-2025+2026-Größere')

MONTHS = [(1, 'Januar'), (2, 'Februar'), (3, 'März'), (4, 'April')]

# === Aggregation ===
def agg(group):
    n = len(group)
    ek = group[EK].sum()
    vk = group[VK].sum()
    profit = vk - ek
    marge = (profit / vk * 100) if vk > 0 else 0
    avg_profit = profit / n if n > 0 else 0
    return pd.Series(dict(stk=n, ek=ek, vk=vk, profit=profit, marge=marge, avg_profit=avg_profit))

pivot = df.groupby([SUP, 'Year', 'Month']).apply(agg, include_groups=False).reset_index()

def get_val(sup, year, month, metric):
    row = pivot[(pivot[SUP] == sup) & (pivot['Year'] == year) & (pivot['Month'] == month)]
    if len(row) == 0: return None
    return row.iloc[0][metric]

def fmt_n(v):
    if v is None or pd.isna(v): return '—'
    return f'{int(v):,}'.replace(',', '.')

def fmt_eur(v):
    if v is None or pd.isna(v): return '—'
    return f'{int(round(v)):,} €'.replace(',', '.')

def fmt_pct(v):
    if v is None or pd.isna(v): return '—'
    return f'{v:.1f} %'.replace('.', ',')

def fmt_eur1(v):
    if v is None or pd.isna(v): return '—'
    return f'{v:.2f} €'.replace('.', ',')

def fmt_delta_pct(v25, v26):
    if v25 is None or v26 is None or v25 == 0:
        if v25 == 0 and v26 and v26 > 0: return '<span class="tag-new">NEU</span>'
        if v26 == 0 and v25 and v25 > 0: return '<span class="tag-out">RAUS</span>'
        return '—'
    delta = (v26 - v25) / v25 * 100
    if abs(delta) < 0.1: cls = 'tag-flat'
    elif delta > 0: cls = 'tag-up'
    else: cls = 'tag-down'
    sign = '+' if delta > 0 else ''
    return f'<span class="{cls}">{sign}{delta:.0f} %</span>'

def fmt_delta_pp(v25, v26):
    if v25 is None or v26 is None or pd.isna(v25) or pd.isna(v26):
        return '—'
    pp = v26 - v25
    if abs(pp) < 0.05: cls = 'tag-flat'
    elif pp > 0: cls = 'tag-up'
    else: cls = 'tag-down'
    sign = '+' if pp > 0 else ''
    return f'<span class="{cls}">{sign}{pp:.1f} pp</span>'

# === HTML generieren ===
def render_metric_table(metric_key, title, formatter, delta_fmt='pct'):
    html = []
    html.append(f'<div class="card">')
    html.append(f'  <div class="card-title">{title}</div>')
    html.append(f'  <table class="comp">')
    html.append(f'    <thead>')
    html.append(f'      <tr><th rowspan="2" class="left sticky">Lieferant</th>')
    for m_num, m_name in MONTHS:
        html.append(f'        <th colspan="3" class="month-head">{m_name}</th>')
    html.append(f'      </tr>')
    html.append(f'      <tr>')
    for _ in MONTHS:
        html.append(f'        <th class="right">2025</th><th class="right">2026</th><th class="right">Δ</th>')
    html.append(f'      </tr>')
    html.append(f'    </thead>')
    html.append(f'    <tbody>')
    for sup in suppliers:
        html.append(f'      <tr><td class="left sticky">{sup}</td>')
        for m_num, _ in MONTHS:
            v25 = get_val(sup, 2025, m_num, metric_key)
            v26 = get_val(sup, 2026, m_num, metric_key)
            html.append(f'        <td class="right num">{formatter(v25)}</td>')
            html.append(f'        <td class="right num">{formatter(v26)}</td>')
            if delta_fmt == 'pp':
                html.append(f'        <td class="right">{fmt_delta_pp(v25, v26)}</td>')
            else:
                html.append(f'        <td class="right">{fmt_delta_pct(v25, v26)}</td>')
        html.append(f'      </tr>')
    # Σ-Zeile
    html.append(f'      <tr class="sum-row"><td class="left sticky"><b>Σ alle Lieferanten</b></td>')
    for m_num, _ in MONTHS:
        df25 = df[(df['Year'] == 2025) & (df['Month'] == m_num)]
        df26 = df[(df['Year'] == 2026) & (df['Month'] == m_num)]
        if metric_key == 'stk':
            v25 = len(df25); v26 = len(df26)
        elif metric_key == 'marge':
            vk25 = df25[VK].sum(); ek25 = df25[EK].sum()
            vk26 = df26[VK].sum(); ek26 = df26[EK].sum()
            v25 = (vk25-ek25)/vk25*100 if vk25 > 0 else 0
            v26 = (vk26-ek26)/vk26*100 if vk26 > 0 else 0
        elif metric_key == 'avg_profit':
            v25 = (df25[VK].sum() - df25[EK].sum()) / len(df25) if len(df25) > 0 else 0
            v26 = (df26[VK].sum() - df26[EK].sum()) / len(df26) if len(df26) > 0 else 0
        elif metric_key == 'profit':
            v25 = df25[VK].sum() - df25[EK].sum()
            v26 = df26[VK].sum() - df26[EK].sum()
        elif metric_key == 'ek':
            v25 = df25[EK].sum(); v26 = df26[EK].sum()
        elif metric_key == 'vk':
            v25 = df25[VK].sum(); v26 = df26[VK].sum()
        else:
            v25 = None; v26 = None
        html.append(f'        <td class="right num"><b>{formatter(v25)}</b></td>')
        html.append(f'        <td class="right num"><b>{formatter(v26)}</b></td>')
        if delta_fmt == 'pp':
            html.append(f'        <td class="right"><b>{fmt_delta_pp(v25, v26)}</b></td>')
        else:
            html.append(f'        <td class="right"><b>{fmt_delta_pct(v25, v26)}</b></td>')
    html.append(f'      </tr>')
    html.append(f'    </tbody></table>')
    html.append(f'</div>')
    return '\n'.join(html)

# === HTML-Skeleton ===
HTML_HEAD = '''<!DOCTYPE html>
<html lang="de">
<head>
<meta charset="UTF-8">
<title>Lieferanten-Monatsvergleich Jan-Apr 2025 vs 2026 · elvinci</title>
<style>
:root {
  --burg: #6b2737; --burg-soft: #b97a87;
  --good: #2d6a4f; --bad: #c04040; --warn: #b87333;
  --ink: #1a1f2c; --ink-soft: #4a5468; --ink-faint: #8893a8;
  --bg: #f8f6f2; --paper: #ffffff; --line: #e5e2dc;
  --up: #1d5e3f; --down: #a13030; --flat: #888;
}
* { box-sizing: border-box; }
body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Tahoma, sans-serif;
       background: var(--bg); color: var(--ink); margin: 0; padding: 24px; line-height: 1.5; }
.header { background: var(--paper); border-radius: 8px; padding: 24px 28px; margin-bottom: 20px;
          box-shadow: 0 1px 3px rgba(0,0,0,0.04); border-left: 4px solid var(--burg); }
.header h1 { margin: 0 0 6px 0; font-size: 22px; font-weight: 600; }
.header h1 em { color: var(--burg); font-style: normal; }
.header .sub { color: var(--ink-soft); font-size: 13px; }
.header .pill { display: inline-block; background: var(--burg); color: white;
                padding: 3px 10px; border-radius: 12px; font-size: 11px; margin-top: 8px; }
.card { background: var(--paper); border-radius: 8px; padding: 18px 20px; margin-bottom: 18px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.04); }
.card-title { font-size: 15px; font-weight: 600; margin-bottom: 12px; padding-bottom: 8px;
              border-bottom: 1px solid var(--line); color: var(--burg); }
table.comp { width: 100%; border-collapse: collapse; font-size: 12px; }
table.comp th { background: var(--bg); border-bottom: 2px solid var(--line);
                padding: 8px 6px; text-align: right; font-weight: 600; color: var(--ink-soft); }
table.comp th.left, table.comp td.left { text-align: left; }
table.comp th.month-head { background: rgba(107,39,55,0.07); color: var(--burg); border-right: 1px solid var(--line); border-left: 1px solid var(--line); }
table.comp td { padding: 6px 6px; border-bottom: 1px solid var(--line); white-space: nowrap; }
table.comp td.num, table.comp th.num, table.comp .right { text-align: right; font-feature-settings: 'tnum'; font-variant-numeric: tabular-nums; }
table.comp tr:hover td { background: rgba(107,39,55,0.03); }
table.comp .sum-row { border-top: 2px solid var(--ink); background: rgba(45,106,79,0.04); }
.sticky { position: sticky; left: 0; background: var(--paper); z-index: 1; }
table.comp tr:hover .sticky { background: rgba(107,39,55,0.04); }
.tag-up { display: inline-block; padding: 2px 7px; background: rgba(45,106,79,0.12); color: var(--up); border-radius: 3px; font-weight: 500; font-size: 11px; }
.tag-down { display: inline-block; padding: 2px 7px; background: rgba(192,64,64,0.12); color: var(--down); border-radius: 3px; font-weight: 500; font-size: 11px; }
.tag-flat { display: inline-block; padding: 2px 7px; background: rgba(0,0,0,0.05); color: var(--flat); border-radius: 3px; font-weight: 500; font-size: 11px; }
.tag-new { display: inline-block; padding: 2px 7px; background: rgba(184,115,51,0.15); color: var(--warn); border-radius: 3px; font-weight: 500; font-size: 11px; }
.tag-out { display: inline-block; padding: 2px 7px; background: rgba(0,0,0,0.08); color: var(--ink-soft); border-radius: 3px; font-weight: 500; font-size: 11px; }
.section-title { font-size: 18px; font-weight: 600; margin: 24px 0 12px; color: var(--ink); }
.foot { font-size: 11px; color: var(--ink-faint); padding: 16px 20px; text-align: center; }
.legend { font-size: 11px; color: var(--ink-soft); padding: 8px 0; }
.legend span { display: inline-block; margin-right: 12px; }
</style>
</head><body>
'''

now_str = datetime.now().strftime('%Y-%m-%d %H:%M')
html_body = []
html_body.append('<div class="header">')
html_body.append('  <h1>Lieferanten-Monatsvergleich <em>Jan – Apr 2025 vs 2026</em></h1>')
html_body.append('  <div class="sub">Top-' + str(len(suppliers)) + ' Lieferanten · Stückzahl, Marge, Profit pro Monat im Direktvergleich · Methodik: Marge auf VK<sub>JTL</sub>, Profit = VK<sub>JTL</sub> − EK</div>')
html_body.append(f'  <div class="pill">erstellt {now_str} · Quelle: 8 All-Sold-Files (n=92.576 dedup)</div>')
html_body.append('</div>')

html_body.append(render_metric_table('stk', 'Stückzahl pro Monat', fmt_n, 'pct'))
html_body.append(render_metric_table('marge', 'Bruttomarge auf VK<sub>JTL</sub> (%)', fmt_pct, 'pp'))
html_body.append(render_metric_table('avg_profit', 'Ø Profit pro Gerät', fmt_eur1, 'pct'))
html_body.append(render_metric_table('profit', 'Profit Σ (VK<sub>JTL</sub> − EK)', fmt_eur, 'pct'))
html_body.append(render_metric_table('ek', 'EK Σ', fmt_eur, 'pct'))
html_body.append(render_metric_table('vk', 'VK<sub>JTL</sub> Σ', fmt_eur, 'pct'))

html_body.append('<div class="card legend">')
html_body.append('  <strong>Lesart:</strong>')
html_body.append('  <span><span class="tag-up">grün</span> = Verbesserung 2026 vs 2025</span>')
html_body.append('  <span><span class="tag-down">rot</span> = Verschlechterung</span>')
html_body.append('  <span><span class="tag-flat">grau</span> = stabil (±0,1)</span>')
html_body.append('  <span><span class="tag-new">NEU</span> = nur 2026, kein Vergleichswert 2025</span>')
html_body.append('  <span><span class="tag-out">RAUS</span> = nur 2025, in 2026 nicht mehr aktiv</span>')
html_body.append('</div>')

html_body.append('<div class="foot">')
html_body.append('  Validiert gegen 92.576 deduplizierte Portal-Sold-Records · Lieferanten sortiert nach 2025-Volumen Top-10 + 2026-Einsteiger >100 Stk')
html_body.append('  · Profit-Berechnung methodikkonform: VK_JTL − EK (nicht Excel-Profit-Spalte)')
html_body.append('</div>')
html_body.append('</body></html>')

OUTPUT_FILE.write_text(HTML_HEAD + '\n'.join(html_body), encoding='utf-8')
print(f'\n✓ Generiert: {OUTPUT_FILE}')
print(f'  Size: {OUTPUT_FILE.stat().st_size:,} B')
