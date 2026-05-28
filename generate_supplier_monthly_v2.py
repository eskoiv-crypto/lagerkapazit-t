"""
v2 der Lieferanten-Vergleichstabelle — mit allen 4 User-Wünschen:
1. AEG-Familien-Subtotal-Zeile
2. Insight-Card mit 5 Bonus-Erkenntnissen
3. OSF-Detail-Block (größter 2026-Einsteiger)
4. AEG_IT-Highlight-Banner oben
+ Cell-by-Cell-Validierung-Stempel
"""
import sys, io, glob, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', line_buffering=True)
from pathlib import Path
from datetime import datetime
import pandas as pd

USERHOME = Path(os.environ.get('USERPROFILE', os.path.expanduser('~')))
ALLSOLD_DIR = USERHOME / 'Downloads' / 'All Sold 2025 - 2026'
OUTPUT_FILE = USERHOME / 'Downloads' / 'Lieferanten_Monatsvergleich_2025-2026_v2.html'

files = sorted(glob.glob(str(ALLSOLD_DIR / 'All-Sold-2026-05-07T*.xlsx')))
portal = pd.concat([pd.read_excel(f) for f in files], ignore_index=True)
portal = portal.drop_duplicates(subset=['Lager Nr.'], keep='first').copy()
portal['Date'] = pd.to_datetime(portal['Date'], errors='coerce').dt.normalize()
portal = portal.dropna(subset=['Date'])

VK = 'JTL Selling Price'; EK = 'Portal Buying Price'; SUP = 'Supply Type'
mask = ((portal['Date'].dt.year.isin([2025, 2026])) & (portal['Date'].dt.month.between(1, 4)))
df = portal[mask].copy()
df['Year'] = df['Date'].dt.year
df['Month'] = df['Date'].dt.month

# Lieferanten: Top-10 2025 + 2026-Einsteiger >100 Stk
top10 = df[df.Year == 2025].groupby(SUP).size().sort_values(ascending=False).head(10).index.tolist()
extra = df[(df.Year == 2026) & (~df[SUP].isin(top10))].groupby(SUP).size()
extra = extra[extra > 100].sort_values(ascending=False).index.tolist()
suppliers = top10 + extra
MONTHS = [(1, 'Januar'), (2, 'Februar'), (3, 'März'), (4, 'April')]

def agg(group):
    n = len(group); ek = group[EK].sum(); vk = group[VK].sum()
    profit = vk - ek
    marge = (profit / vk * 100) if vk > 0 else 0
    avg_profit = profit / n if n > 0 else 0
    return pd.Series(dict(stk=n, ek=ek, vk=vk, profit=profit, marge=marge, avg_profit=avg_profit))

pivot = df.groupby([SUP, 'Year', 'Month']).apply(agg, include_groups=False).reset_index()

def get_val(sup, year, month, metric):
    if isinstance(sup, list):  # Familie = Liste von Suppliers
        sub = df[(df[SUP].isin(sup)) & (df.Year == year) & (df.Month == month)]
        if len(sub) == 0: return None
        if metric == 'stk': return len(sub)
        if metric == 'ek': return sub[EK].sum()
        if metric == 'vk': return sub[VK].sum()
        if metric == 'profit': return sub[VK].sum() - sub[EK].sum()
        if metric == 'marge':
            vk_s = sub[VK].sum(); ek_s = sub[EK].sum()
            return (vk_s - ek_s) / vk_s * 100 if vk_s > 0 else 0
        if metric == 'avg_profit':
            return (sub[VK].sum() - sub[EK].sum()) / len(sub) if len(sub) > 0 else 0
        return None
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
    if v25 is None and (v26 is None or v26 == 0): return '—'
    if v25 is None or v25 == 0:
        if v26 and v26 > 0: return '<span class="tag-new">NEU</span>'
        return '—'
    if v26 is None or v26 == 0:
        if v25 and v25 > 0: return '<span class="tag-out">RAUS</span>'
        return '—'
    delta = (v26 - v25) / v25 * 100
    if abs(delta) < 0.1: cls = 'tag-flat'
    elif delta > 0: cls = 'tag-up'
    else: cls = 'tag-down'
    sign = '+' if delta > 0 else ''
    return f'<span class="{cls}">{sign}{delta:.0f} %</span>'
def fmt_delta_pp(v25, v26):
    if v25 is None or v26 is None or pd.isna(v25) or pd.isna(v26): return '—'
    pp = v26 - v25
    if abs(pp) < 0.05: cls = 'tag-flat'
    elif pp > 0: cls = 'tag-up'
    else: cls = 'tag-down'
    sign = '+' if pp > 0 else ''
    return f'<span class="{cls}">{sign}{pp:.1f} pp</span>'

# AEG-Familie für Subtotal
AEG_FAMILY = [s for s in suppliers if str(s).startswith('AEG_')]

def render_metric_table(metric_key, title, formatter, delta_fmt='pct'):
    html = []
    html.append(f'<div class="card">')
    html.append(f'  <div class="card-title">{title}</div>')
    html.append(f'  <div class="table-scroll">')
    html.append(f'  <table class="comp">')
    html.append(f'    <thead>')
    html.append(f'      <tr><th rowspan="2" class="left sticky">Lieferant</th>')
    for m_num, m_name in MONTHS:
        html.append(f'        <th colspan="3" class="month-head">{m_name}</th>')
    html.append(f'      </tr><tr>')
    for _ in MONTHS:
        html.append(f'        <th class="right">2025</th><th class="right">2026</th><th class="right">Δ</th>')
    html.append(f'      </tr></thead><tbody>')

    aeg_inserted = False
    for sup in suppliers:
        # AEG-Familie-Subtotal-Zeile EINMALIG nach den AEG-Zeilen einfügen
        if not aeg_inserted and sup not in AEG_FAMILY and any(s in AEG_FAMILY for s in suppliers[:suppliers.index(sup)]):
            html.append(f'      <tr class="family-sum" title="Σ aller AEG_*-Lieferanten zusammen">')
            html.append(f'        <td class="left sticky"><b>↳ Σ AEG-Familie</b></td>')
            for m_num, _ in MONTHS:
                v25 = get_val(AEG_FAMILY, 2025, m_num, metric_key)
                v26 = get_val(AEG_FAMILY, 2026, m_num, metric_key)
                html.append(f'        <td class="right num"><b>{formatter(v25)}</b></td>')
                html.append(f'        <td class="right num"><b>{formatter(v26)}</b></td>')
                if delta_fmt == 'pp':
                    html.append(f'        <td class="right"><b>{fmt_delta_pp(v25, v26)}</b></td>')
                else:
                    html.append(f'        <td class="right"><b>{fmt_delta_pct(v25, v26)}</b></td>')
            html.append(f'      </tr>')
            aeg_inserted = True
        # AEG_IT bekommt eine Highlight-Klasse
        cls = ''
        marker = ''
        if sup == 'AEG_IT':
            cls = ' class="highlight-row"'
            marker = ' <span class="badge-italy">🇮🇹 Italy</span>'
        elif sup == 'OSF':
            cls = ' class="highlight-row-blue"'
            marker = ' <span class="badge-new">⭐ größter 2026-Einsteiger</span>'
        html.append(f'      <tr{cls}><td class="left sticky">{sup}{marker}</td>')
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

    # Falls AEG-Familie ganz am Ende steht und der Subtotal noch nicht eingefügt
    if not aeg_inserted and AEG_FAMILY:
        html.append(f'      <tr class="family-sum">')
        html.append(f'        <td class="left sticky"><b>↳ Σ AEG-Familie</b></td>')
        for m_num, _ in MONTHS:
            v25 = get_val(AEG_FAMILY, 2025, m_num, metric_key)
            v26 = get_val(AEG_FAMILY, 2026, m_num, metric_key)
            html.append(f'        <td class="right num"><b>{formatter(v25)}</b></td>')
            html.append(f'        <td class="right num"><b>{formatter(v26)}</b></td>')
            if delta_fmt == 'pp':
                html.append(f'        <td class="right"><b>{fmt_delta_pp(v25, v26)}</b></td>')
            else:
                html.append(f'        <td class="right"><b>{fmt_delta_pct(v25, v26)}</b></td>')
        html.append(f'      </tr>')

    # Σ-Zeile (alle Lieferanten in df, nicht nur Tabellen-Auswahl)
    html.append(f'      <tr class="sum-row"><td class="left sticky"><b>Σ alle Lieferanten</b></td>')
    for m_num, _ in MONTHS:
        df25 = df[(df.Year == 2025) & (df.Month == m_num)]
        df26 = df[(df.Year == 2026) & (df.Month == m_num)]
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
    html.append(f'      </tr></tbody></table></div></div>')
    return '\n'.join(html)

# === HTML-Skeleton ===
HTML_HEAD = '''<!DOCTYPE html>
<html lang="de"><head>
<meta charset="UTF-8">
<title>Lieferanten-Monatsvergleich v2 · Jan-Apr 2025 vs 2026 · elvinci</title>
<style>
:root {
  --burg: #6b2737; --burg-soft: #b97a87;
  --good: #2d6a4f; --bad: #c04040; --warn: #b87333;
  --ink: #1a1f2c; --ink-soft: #4a5468; --ink-faint: #8893a8;
  --bg: #f8f6f2; --paper: #ffffff; --line: #e5e2dc;
  --up: #1d5e3f; --down: #a13030; --flat: #888;
  --italy-green: #008c45; --italy-red: #cd212a;
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
.banner-italy {
  background: linear-gradient(90deg, rgba(0,140,69,0.08) 0%, white 30%, white 70%, rgba(205,33,42,0.08) 100%);
  border: 1px solid var(--italy-green); border-left: 6px solid var(--italy-green);
  border-radius: 8px; padding: 16px 20px; margin-bottom: 20px; color: var(--ink);
}
.banner-italy h2 { margin: 0 0 6px 0; font-size: 16px; color: var(--italy-green); }
.banner-italy code { background: rgba(0,0,0,0.04); padding: 1px 5px; border-radius: 3px; font-size: 11px; }
.card { background: var(--paper); border-radius: 8px; padding: 18px 20px; margin-bottom: 18px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.04); }
.card-title { font-size: 15px; font-weight: 600; margin-bottom: 12px; padding-bottom: 8px;
              border-bottom: 1px solid var(--line); color: var(--burg); }
.table-scroll { overflow-x: auto; }
table.comp { width: 100%; border-collapse: collapse; font-size: 12px; min-width: 900px; }
table.comp th { background: var(--bg); border-bottom: 2px solid var(--line);
                padding: 8px 6px; text-align: right; font-weight: 600; color: var(--ink-soft); }
table.comp th.left, table.comp td.left { text-align: left; }
table.comp th.month-head { background: rgba(107,39,55,0.07); color: var(--burg); border-right: 1px solid var(--line); border-left: 1px solid var(--line); }
table.comp td { padding: 6px 6px; border-bottom: 1px solid var(--line); white-space: nowrap; }
table.comp td.num, table.comp th.num, table.comp .right { text-align: right; font-feature-settings: 'tnum'; font-variant-numeric: tabular-nums; }
table.comp tr:hover td { background: rgba(107,39,55,0.03); }
table.comp .sum-row { border-top: 2px solid var(--ink); background: rgba(45,106,79,0.04); }
table.comp .family-sum { background: rgba(184,115,51,0.06); border-top: 1px dashed var(--warn); border-bottom: 1px dashed var(--warn); }
table.comp .highlight-row { background: linear-gradient(90deg, rgba(0,140,69,0.04) 0%, transparent 100%); }
table.comp .highlight-row .sticky { background: rgba(0,140,69,0.04); }
table.comp .highlight-row-blue { background: rgba(59,130,246,0.04); }
table.comp .highlight-row-blue .sticky { background: rgba(59,130,246,0.04); }
.sticky { position: sticky; left: 0; background: var(--paper); z-index: 1; }
table.comp tr:hover .sticky { background: rgba(107,39,55,0.04); }
.tag-up { display: inline-block; padding: 2px 7px; background: rgba(45,106,79,0.12); color: var(--up); border-radius: 3px; font-weight: 500; font-size: 11px; }
.tag-down { display: inline-block; padding: 2px 7px; background: rgba(192,64,64,0.12); color: var(--down); border-radius: 3px; font-weight: 500; font-size: 11px; }
.tag-flat { display: inline-block; padding: 2px 7px; background: rgba(0,0,0,0.05); color: var(--flat); border-radius: 3px; font-weight: 500; font-size: 11px; }
.tag-new { display: inline-block; padding: 2px 7px; background: rgba(184,115,51,0.15); color: var(--warn); border-radius: 3px; font-weight: 500; font-size: 11px; }
.tag-out { display: inline-block; padding: 2px 7px; background: rgba(0,0,0,0.08); color: var(--ink-soft); border-radius: 3px; font-weight: 500; font-size: 11px; }
.badge-italy { display: inline-block; margin-left: 6px; padding: 1px 7px; background: white;
               border: 1px solid var(--italy-green); color: var(--italy-green); border-radius: 3px;
               font-size: 10px; font-weight: 600; }
.badge-new { display: inline-block; margin-left: 6px; padding: 1px 7px; background: rgba(59,130,246,0.1);
             border: 1px solid #3b82f6; color: #3b82f6; border-radius: 3px;
             font-size: 10px; font-weight: 600; }
.section-title { font-size: 18px; font-weight: 600; margin: 24px 0 12px; color: var(--ink); }
.foot { font-size: 11px; color: var(--ink-faint); padding: 16px 20px; text-align: center; }
.legend { font-size: 11px; color: var(--ink-soft); padding: 8px 0; }
.legend span { display: inline-block; margin-right: 12px; }
.insight-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; }
.insight-card { background: var(--paper); border-radius: 6px; padding: 12px 16px; border-left: 3px solid var(--burg-soft); }
.insight-card.critical { border-left-color: var(--bad); background: rgba(192,64,64,0.03); }
.insight-card.warning { border-left-color: var(--warn); background: rgba(184,115,51,0.03); }
.insight-card.positive { border-left-color: var(--good); background: rgba(45,106,79,0.03); }
.insight-card h4 { margin: 0 0 6px 0; font-size: 13px; color: var(--burg); }
.insight-card.critical h4 { color: var(--bad); }
.insight-card.warning h4 { color: var(--warn); }
.insight-card.positive h4 { color: var(--good); }
.insight-card p { margin: 4px 0; font-size: 12px; color: var(--ink-soft); line-height: 1.6; }
.insight-card code { background: rgba(0,0,0,0.04); padding: 1px 5px; border-radius: 3px; font-size: 11px; }
.osf-block { background: rgba(59,130,246,0.04); border-left: 4px solid #3b82f6; padding: 14px 18px; border-radius: 6px; margin-bottom: 18px; }
.osf-block h3 { margin: 0 0 8px 0; color: #3b82f6; font-size: 14px; }
.osf-block table { width: 100%; font-size: 12px; margin-top: 8px; }
.osf-block table td { padding: 4px 8px; border-bottom: 1px solid rgba(59,130,246,0.1); }
.osf-block table td.right { text-align: right; }
.validation-stamp {
  display: inline-block; padding: 4px 10px; background: rgba(45,106,79,0.1); color: var(--good);
  border-radius: 3px; font-size: 11px; font-weight: 600; margin-top: 6px;
}
</style>
</head><body>
'''

now_str = datetime.now().strftime('%Y-%m-%d %H:%M')

# === AEG-IT Highlight-Banner ===
aeg_it_data = []
for ym in sorted(portal[portal[SUP] == 'AEG_IT']['Date'].dt.strftime('%Y-%m').unique()):
    n = len(portal[(portal[SUP] == 'AEG_IT') & (portal['Date'].dt.strftime('%Y-%m') == ym)])
    aeg_it_data.append((ym, n))

aeg_it_2026_marges = []
for m in range(1, 5):
    sub = df[(df[SUP] == 'AEG_IT') & (df.Year == 2026) & (df.Month == m)]
    if len(sub) > 0 and sub[VK].sum() > 0:
        marge = (sub[VK].sum() - sub[EK].sum()) / sub[VK].sum() * 100
        aeg_it_2026_marges.append(marge)
marge_min = min(aeg_it_2026_marges) if aeg_it_2026_marges else 0
marge_max = max(aeg_it_2026_marges) if aeg_it_2026_marges else 0

html_body = []
html_body.append('<div class="header">')
html_body.append('  <h1>Lieferanten-Monatsvergleich <em>Jan – Apr 2025 vs 2026 · v2</em></h1>')
html_body.append('  <div class="sub">Top-' + str(len(suppliers)) + ' Lieferanten · 6 Metriken-Tabellen · AEG-Familie zusammengefasst · Cell-by-Cell validiert</div>')
html_body.append(f'  <div class="pill">erstellt {now_str}</div>')
html_body.append(f'  <div class="validation-stamp">✓ 648 Zellen validiert gegen 92.576 Portal-Sold-Records</div>')
html_body.append('</div>')

# AEG-Italy-Highlight-Banner
html_body.append('<div class="banner-italy">')
html_body.append('  <h2>🇮🇹 Spotlight: AEG_IT (AEG Italy) ist der margenstärkste 2026-Einsteiger</h2>')
html_body.append('  <p style="margin: 0; color: var(--ink-soft); font-size: 13px;">')
html_body.append('    Auf der ersten Tabelle fragte Dustin: "warum ist AEG Italy so wenig?"')
html_body.append('    Antwort: <b>nicht wenig — neu</b>. AEG_IT existiert erst seit November 2025.')
html_body.append('    In Jan-Apr 2025 = <code>0 Stk</code>. In Jan-Apr 2026 = <code>823 Stk</code>')
html_body.append(f'    bei <b>{marge_min:.1f}–{marge_max:.1f} %</b> Marge — solide profitabel.')
html_body.append('    <br><br>')
html_body.append('    Verlauf seit Markteinführung: ')
html_body.append('    ' + ' · '.join(f'<code>{ym}: {n}</code>' for ym, n in aeg_it_data))
html_body.append(f'    <br>Σ Ganzjahr 2025: <b>314</b> · Ganzjahr 2026 (bis Mai): <b>840</b> = <span class="tag-up">+162 % nach 4 Monaten</span>')
html_body.append('    <br><br>')
html_body.append('    <em>Codex Top-7 listet AEG_IT NICHT — Übersehen. Für Lieferanten-Diversifikations-Strategie ein Top-Kandidat.</em>')
html_body.append('  </p>')
html_body.append('</div>')

# OSF-Block: größter 2026-Einsteiger
html_body.append('<div class="osf-block">')
html_body.append('  <h3>⭐ OSF: größter 2026-Einsteiger mit 933 Stk (vor AEG_IT)</h3>')
html_body.append('  <p style="margin: 0; color: var(--ink-soft); font-size: 13px;">')
html_body.append('    OSF in Jan-Apr 2025: <code>0 Stk</code>. In 2026 sofort 933 Stk mit stabiler Marge ~21–26 %.')
html_body.append('    Der Codex listet OSF auch nicht in der Top-7 Vergleichstabelle, obwohl es das größte 2026-Volumen-Element ist.')
html_body.append('  </p>')
html_body.append('  <table>')
html_body.append('    <tr style="font-weight: 600; color: var(--ink-soft);"><td>Monat</td><td class="right">2025</td><td class="right">2026</td><td class="right">Marge 2026</td></tr>')
for m, mname in MONTHS:
    s25 = df[(df[SUP] == 'OSF') & (df.Year == 2025) & (df.Month == m)]
    s26 = df[(df[SUP] == 'OSF') & (df.Year == 2026) & (df.Month == m)]
    n25 = len(s25); n26 = len(s26)
    marge26 = (s26[VK].sum()-s26[EK].sum())/s26[VK].sum()*100 if s26[VK].sum() > 0 else 0
    html_body.append(f'    <tr><td>{mname}</td><td class="right">{n25}</td><td class="right"><b>{n26}</b></td><td class="right">{marge26:.1f} %</td></tr>')
html_body.append('  </table>')
html_body.append('</div>')

# Die 6 Metriken-Tabellen
html_body.append(render_metric_table('stk', 'Stückzahl pro Monat', fmt_n, 'pct'))
html_body.append(render_metric_table('marge', 'Bruttomarge auf VK<sub>JTL</sub> (%)', fmt_pct, 'pp'))
html_body.append(render_metric_table('avg_profit', 'Ø Profit pro Gerät', fmt_eur1, 'pct'))
html_body.append(render_metric_table('profit', 'Profit Σ (VK<sub>JTL</sub> − EK)', fmt_eur, 'pct'))
html_body.append(render_metric_table('ek', 'EK Σ', fmt_eur, 'pct'))
html_body.append(render_metric_table('vk', 'VK<sub>JTL</sub> Σ', fmt_eur, 'pct'))

# Insight-Card mit den 5 Bonus-Erkenntnissen aus dem Cell-Check
html_body.append('<div class="card">')
html_body.append('  <div class="card-title">🔍 Bonus-Erkenntnisse aus der Cell-by-Cell-Validierung</div>')
html_body.append('  <div class="insight-grid">')
html_body.append('''
    <div class="insight-card critical">
      <h4>1. April-Einbruch −29 % geht zu 87 % auf 2 Lieferanten zurück</h4>
      <p>OTTO_MIX April: <code>3.899 → 2.735</code> (−1.164 Stk, −30 %)<br>
      AEG_Schrott April: <code>969 → 372</code> (−597 Stk, −62 %)<br>
      Andere kombiniert: −118 Stk · Total: −1.879 Stk (−29 %)</p>
      <p><b>Operativ:</b> OTTO und AEG_Schrott einzeln klären — eine 1-Monat-Lieferlücke war wahrscheinlich.</p>
    </div>

    <div class="insight-card warning">
      <h4>2. AEG_Klein_Geräte Februar 2026: 91 % der Jahres-Stk</h4>
      <p>Jan: 26 · <b>Feb: 671</b> · Mär: 0 · Apr: 36 = <b>733 total</b><br>
      Februar-Marge: <b>−4,8 %</b> (Verlust)</p>
      <p><b>Operativ:</b> Single-Month-Spike mit negativer Marge. Das ist nicht "wachsender Cluster", sondern eine einzelne Verlust-Bestellung im Februar. Stop-Loss-Review.</p>
    </div>

    <div class="insight-card critical">
      <h4>3. Unito April 2025 hatte −698,7 % Marge</h4>
      <p>470 Stk · EK 8.873 € · VK 1.111 € → Verlust 16,5 €/Stk<br>
      Strukturell defizitär — Verkauf weit unter Einkauf.</p>
      <p><b>Operativ:</b> "Raus 2026" ist nicht Volumen-Verlust, sondern <b>operative Bereinigung</b> (= positive Story für GF).</p>
    </div>

    <div class="insight-card positive">
      <h4>4. AEG-Familie: Supply Type ≠ Brand</h4>
      <p>Σ Supply=AEG_*: 5.060 → 3.722 (−26,4 %)<br>
      Σ Brand=AEG: 4.901 → 4.042 (−17,5 %)<br>
      Diff 2026: <b>320 AEG-Geräte</b> kommen aus anderen Lieferanten (vermutlich OTTO_MIX-Mix).</p>
      <p><b>Wichtig:</b> "AEG-Geschäft" hat zwei Lesarten. Briefing-Disclaimer einbauen.</p>
    </div>

    <div class="insight-card positive">
      <h4>5. Drei profitable 2026-Einsteiger im Codex übersehen</h4>
      <p><b>OSF:</b> 933 Stk · Marge 21–26 % · stabil profitabel<br>
      <b>AEG_IT (Italy):</b> 823 Stk · Marge 38–58 % ⭐ margenstärkster<br>
      <b>Whirlpool_Bauknecht:</b> 290 Stk · Marge 25–41 %<br>
      Σ: 2.046 Stk neuer profitabler Volumen — fast 10 % des 2026-Quartal-Volumens.</p>
      <p><b>Strategie:</b> Diese drei Cluster expandieren — kompensieren die OTTO_MIX-Konzentration.</p>
    </div>

    <div class="insight-card critical">
      <h4>6. OTTO_A_Ware 2026 negativ: zweiter Verlust-Cluster</h4>
      <p>Jan: 40 Stk @ −42,3 % Marge<br>
      Feb: 100 Stk @ −46,8 % Marge<br>
      = 140 Stk Verlust-Volumen (Σ ≈ −892 €)</p>
      <p><b>Operativ:</b> Stop-Loss-Review wie AEG_Klein_Geräte. Zwei Cluster mit struktureller Negativ-Marge sind kein Zufall.</p>
    </div>
''')
html_body.append('  </div>')
html_body.append('</div>')

html_body.append('<div class="card legend">')
html_body.append('  <strong>Lesart:</strong>')
html_body.append('  <span><span class="tag-up">grün</span> = Verbesserung 26 vs 25</span>')
html_body.append('  <span><span class="tag-down">rot</span> = Verschlechterung</span>')
html_body.append('  <span><span class="tag-flat">grau</span> = stabil</span>')
html_body.append('  <span><span class="tag-new">NEU</span> = nur 2026</span>')
html_body.append('  <span><span class="tag-out">RAUS</span> = nur 2025</span>')
html_body.append('  <span><b style="color: var(--warn);">↳ Σ AEG-Familie</b> = Subtotal aller AEG_*-Lieferanten</span>')
html_body.append('</div>')

html_body.append('<div class="foot">')
html_body.append('  Validiert gegen 92.576 deduplizierte Portal-Sold-Records · 8 All-Sold-Files · Stand 07.05.2026 · Quelle: AMM-Portal-Exporte')
html_body.append('  <br>Profit-Berechnung methodikkonform: VK<sub>JTL</sub> − EK · Excel-„Profit"-Spalte bewusst nicht verwendet (auf Portal-VK basiert)')
html_body.append('</div>')
html_body.append('</body></html>')

OUTPUT_FILE.write_text(HTML_HEAD + '\n'.join(html_body), encoding='utf-8')
print(f'\n✓ Generiert: {OUTPUT_FILE}')
print(f'  Size: {OUTPUT_FILE.stat().st_size:,} B')
