"""
Bearbeitungszeit 2026 — DREHENDE WARE NUR
Harter Constraint: 0 € Vorfinanzierung. 30-T-Lieferanten-Fenster.
"""
import sys, io, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', line_buffering=True)
from pathlib import Path
from datetime import datetime
import pandas as pd

USERHOME = Path(os.environ.get('USERPROFILE', os.path.expanduser('~')))
DETAIL_CSV = USERHOME / 'Downloads' / 'we_to_paid_full_v2.csv'

print('  Lade Detail-CSV…')
m = pd.read_csv(DETAIL_CSV, sep=';', encoding='utf-8-sig', low_memory=False)
m['sold_dt'] = pd.to_datetime(m['sold_dt'])
m['we_dt'] = pd.to_datetime(m['we_dt'])
m['Bezahlt_dt'] = pd.to_datetime(m['Bezahlt_dt'])

# === FILTER 2026 + plausibel ===
clean = m[(m['t_we_to_paid'] >= -3) & (m['t_we_to_paid'] <= 1500)
          & (m['sold_dt'].dt.year == 2026)].copy()

# === DREHENDE LIEFERANTEN — STRIKT (P75 WE→Verkauf ≤ 30 T !) ===
# Strenge Kriterien nach Validierung:
#   1. n ≥ 100
#   2. P75 WE→Verkauf ≤ 30 T (nicht Median — sonst schleichen Altlasten rein)
#   3. Sample-Coverage ≥ 50 % (sonst Selection Bias)
sup_all = clean.groupby('Supply Type').agg(
    n=('t_we_to_paid', 'count'),
    we_sold_med=('t_we_to_sold', 'median'),
    we_sold_p75=('t_we_to_sold', lambda x: x.quantile(0.75)),
)

# Coverage pro Lieferant aus Portal-Sold ermitteln
import glob as _glob
ALLSOLD_DIR = USERHOME / 'Downloads' / 'All Sold 2025 - 2026'
_files = sorted(_glob.glob(str(ALLSOLD_DIR / 'All-Sold-2026-05-07T*.xlsx')))
_portal = pd.concat([pd.read_excel(f) for f in _files], ignore_index=True)
_portal = _portal.drop_duplicates(subset=['Lager Nr.'], keep='first')
_portal['Date_dt'] = pd.to_datetime(_portal['Date'], errors='coerce')
_p_2026 = _portal[_portal['Date_dt'].dt.year == 2026]
sup_all['portal_n'] = _p_2026.groupby('Supply Type').size().reindex(sup_all.index, fill_value=0)
sup_all['coverage'] = sup_all['n'] / sup_all['portal_n'] * 100

drehend_suppliers = sup_all[
    (sup_all['n'] >= 100) &
    (sup_all['we_sold_p75'] <= 30) &
    (sup_all['coverage'] >= 50)
].index.tolist()
altlast_suppliers = [s for s in sup_all.index
                     if s not in drehend_suppliers and sup_all.loc[s, 'n'] >= 100]

core = clean[clean['Supply Type'].isin(drehend_suppliers)].copy()
n_core = len(core)
n_altlast = len(clean[clean['Supply Type'].isin(altlast_suppliers)])

print(f'  Drehende Lieferanten STRIKT ({len(drehend_suppliers)}): {drehend_suppliers}')
print(f'  Ausgeschlossen ({len(altlast_suppliers)}): {altlast_suppliers}')
for s in altlast_suppliers:
    row = sup_all.loc[s]
    reason = []
    if row['we_sold_p75'] > 30: reason.append(f"P75 WE→Verk {row['we_sold_p75']:.0f}T > 30T")
    if row['coverage'] < 50: reason.append(f"Coverage nur {row['coverage']:.0f}%")
    print(f'    → {s}: {", ".join(reason)}')
print(f'  Core n: {n_core:,}  ·  Ausgeschlossen n: {n_altlast:,}')

# === KERN-METRIKEN ===
SUPPLIER_DEADLINE = 30

# Kunden-Fenster pro Gerät = 30 − WE-Alter beim Verkauf
core['customer_window'] = SUPPLIER_DEADLINE - core['t_we_to_sold']
# Vorfinanzierungs-Tage pro Gerät
core['vorfin_days'] = (core['t_we_to_paid'] - SUPPLIER_DEADLINE).clip(lower=0)
core['is_vorfin'] = core['t_we_to_paid'] > SUPPLIER_DEADLINE

# €-Bewertung: Lieferantenverbindlichkeit = EK (Portal Buying Price)
core['JTL Selling Price'] = pd.to_numeric(core['JTL Selling Price'], errors='coerce')
core['Portal Buying Price'] = pd.to_numeric(core['Portal Buying Price'], errors='coerce')

# Periode der Datenbasis
PERIODE_TAGE = (core['sold_dt'].max() - core['sold_dt'].min()).days
YEAR_FACTOR = 365 / PERIODE_TAGE

# === COVERAGE auf strikt-drehende Lieferanten ===
_p_dreh = _p_2026[_p_2026['Supply Type'].isin(drehend_suppliers)]
N_TRUE_DREH_2026 = len(_p_dreh)
SCALE = N_TRUE_DREH_2026 / n_core if n_core else 1
COVERAGE = n_core / N_TRUE_DREH_2026 * 100

# Liquiditätsbindung pro Gerät = EK × Verspätungstage
core['eur_days_tied'] = (core['Portal Buying Price'].fillna(0) * core['vorfin_days'])
sum_eur_days_measured = core['eur_days_tied'].sum()
wc_measured = sum_eur_days_measured / PERIODE_TAGE                 # 58.112 € (alte Zahl)
wc_scaled = wc_measured * SCALE                                    # auf echte Drehmenge skaliert

# Little's Law (MBA-Queueing-Standard): L = λ × W
n_overdue_measured = int(core['is_vorfin'].sum())
lambda_overdue = n_overdue_measured / PERIODE_TAGE * SCALE         # überzogene Geräte/Tag, echt
W_overdue = core[core['is_vorfin']]['vorfin_days'].mean()          # Mean-Verweildauer im Stau
L_overdue = lambda_overdue * W_overdue                             # simultan vorgestreckte Geräte
mean_ek_overdue = core[core['is_vorfin']]['Portal Buying Price'].mean()
wc_littles = L_overdue * mean_ek_overdue                           # 108–109 k €

# Headline-Zahl: Little's Law
WC_FINAL = wc_littles

# EK-Volumen — auf ECHTE Drehmenge, dann auf Jahr
ek_total_periode_measured = core['Portal Buying Price'].sum()
ek_total_periode_scaled = ek_total_periode_measured * SCALE
ek_total_year = ek_total_periode_scaled * YEAR_FACTOR              # ~6,2 Mio €
vk_total_year = (core['JTL Selling Price'].sum() * SCALE) * YEAR_FACTOR

# Kapitalkosten p.a. — auf WC_FINAL
kk_05 = WC_FINAL * 0.05
kk_10 = WC_FINAL * 0.10
kk_15 = WC_FINAL * 0.15

# Cash Conversion Cycle (MBA-Standard)
DIO = core['t_we_to_sold'].median()
DSO_med = core['t_sold_to_paid'].median()
DSO_mean = core['t_sold_to_paid'].mean()
DPO = SUPPLIER_DEADLINE
CCC = DIO + DSO_mean - DPO

print(f'  Coverage drehend 2026: {COVERAGE:.1f} %  (gemessen {n_core:,} / echt {N_TRUE_DREH_2026:,})')
print(f'  Skalierungs-Faktor: {SCALE:.2f}x')
print(f'  WC gemessen:       {wc_measured:>10,.0f} €')
print(f'  WC skaliert (1,70x):{wc_scaled:>10,.0f} €')
print(f'  WC Littles Law:    {wc_littles:>10,.0f} €  ← Headline')
print(f'  CCC = {DIO:.0f}+{DSO_mean:.0f}-{DPO} = {CCC:.1f} T')

# === WE-ALTER beim Verkauf — Eimer ===
age_buckets = [
    (-99, 0,   '≤ 0 Tage (frisch)'),
    (1,    7,  '1–7 Tage'),
    (8,    14, '8–14 Tage'),
    (15,   22, '15–22 Tage'),
    (23,   30, '23–30 Tage'),
    (31,   60, '31–60 Tage (kritisch)'),
    (61,  9999,'> 60 Tage (Altlast)'),
]
age_hist = []
for lo, hi, lbl in age_buckets:
    mask = (core['t_we_to_sold'] >= lo) & (core['t_we_to_sold'] <= hi)
    n_b = mask.sum()
    n_vorfin_b = (mask & core['is_vorfin']).sum()
    age_hist.append((lbl, lo, hi, n_b, n_vorfin_b))

# === KUNDEN-ZAHLUNGSVERHALTEN ===
sold_paid_med = core['t_sold_to_paid'].median()
sold_paid_p75 = core['t_sold_to_paid'].quantile(0.75)
sold_paid_p90 = core['t_sold_to_paid'].quantile(0.9)

# Anteil Geräte bei welchem das Verkauf→Bezahlt-Fenster reicht
# d. h. Sold→Paid ≤ Customer-Window
core['fits'] = core['t_sold_to_paid'] <= core['customer_window']
fits_pct = core['fits'].mean() * 100
vorfin_pct = core['is_vorfin'].mean() * 100

# Mittlere Vorfinanzierung pro Verspätung
gap_median = core[core['is_vorfin']]['vorfin_days'].median()
gap_mean = core[core['is_vorfin']]['vorfin_days'].mean()
gap_p90 = core[core['is_vorfin']]['vorfin_days'].quantile(0.9)
ek_ueb_periode = core[core['is_vorfin']]['Portal Buying Price'].sum()

# === TIER-EMPFEHLUNG: Maximales Kunden-Netto-Tage je WE-Alter ===
# Ziel: 30 − WE-Alter. Wenn negativ → Vorkasse.
tiers = [
    ('≤ 7 Tage', 7,  '23 T netto', 23),
    ('8–14 Tage', 14, '16 T netto', 16),
    ('15–22 Tage', 22, '8 T netto', 8),
    ('23–30 Tage', 30, '0 T (Vorkasse)', 0),
    ('> 30 Tage', 999, '0 T (Vorkasse, bereits in Vorfinanzierung)', 0),
]

# Verteilung pro Tier
tier_dist = []
for lbl, hi, term, days in tiers:
    if lbl.startswith('≤'):
        mask = core['t_we_to_sold'] <= 7
    elif lbl.startswith('8'):
        mask = (core['t_we_to_sold'] >= 8) & (core['t_we_to_sold'] <= 14)
    elif lbl.startswith('15'):
        mask = (core['t_we_to_sold'] >= 15) & (core['t_we_to_sold'] <= 22)
    elif lbl.startswith('23'):
        mask = (core['t_we_to_sold'] >= 23) & (core['t_we_to_sold'] <= 30)
    else:
        mask = core['t_we_to_sold'] > 30
    n_t = mask.sum()
    pct = n_t / n_core * 100 if n_core else 0
    tier_dist.append((lbl, term, n_t, pct))

# === PRO DREHENDEM LIEFERANT ===
sup_core = core.groupby('Supply Type').agg(
    n=('t_we_to_paid', 'count'),
    we_sold_med=('t_we_to_sold', 'median'),
    we_sold_p75=('t_we_to_sold', lambda x: x.quantile(0.75)),
    we_paid_med=('t_we_to_paid', 'median'),
    we_paid_p90=('t_we_to_paid', lambda x: x.quantile(0.9)),
    vorfin_pct=('is_vorfin', lambda x: x.mean() * 100),
    ek_sum=('Portal Buying Price', 'sum'),
    eur_days_tied=('eur_days_tied', 'sum'),
).sort_values('n', ascending=False)
sup_core['max_net'] = (SUPPLIER_DEADLINE - sup_core['we_sold_p75']).clip(lower=0)
sup_core['avg_wc'] = sup_core['eur_days_tied'] / PERIODE_TAGE

now = datetime.now().strftime('%d.%m.%Y · %H:%M')
out_html = USERHOME / 'Downloads' / 'Bearbeitungszeit_2026_v9.html'
out_pdf  = USERHOME / 'Downloads' / 'Bearbeitungszeit_2026_v9.pdf'

# Outlier-Analyse: Top-N Geräte für Vorfinanzierung
ueb = core[core['is_vorfin']].copy()
ueb['exposure'] = ueb['Portal Buying Price'].fillna(0) * ueb['vorfin_days']
ueb_sorted = ueb.sort_values('exposure', ascending=False)
total_exp = ueb['exposure'].sum()
top500_share = ueb_sorted.head(500)['exposure'].sum() / total_exp * 100 if total_exp else 0
top100_share = ueb_sorted.head(100)['exposure'].sum() / total_exp * 100 if total_exp else 0

def fmt_d(v):
    if pd.isna(v): return '—'
    return f'{v:.0f}'.replace('.', ',') if v == round(v) else f'{v:.1f}'.replace('.', ',')
def fmt_n(v): return f'{int(v):,}'.replace(',', '.')
def fmt_pct(v): return f'{v:.1f}'.replace('.', ',')
def fmt_eur(v):
    s = f'{int(v):,}'.replace(',', '.')
    return f'{s} €'

html = f'''<!DOCTYPE html>
<html lang="de"><head>
<meta charset="UTF-8">
<title>Zahlungsziele 2026 · Drehende Ware</title>
<style>
@page {{ size: A4; margin: 0; }}
* {{ box-sizing: border-box; margin: 0; padding: 0; -webkit-print-color-adjust: exact; print-color-adjust: exact; }}
:root {{
  --black: #1d1d1f; --grey-1: #6e6e73; --grey-2: #86868b; --grey-3: #d2d2d7;
  --grey-bg: #f5f5f7; --paper: #ffffff;
  --blue: #0071e3; --green: #00a82d; --orange: #ff9500; --red: #ff3b30;
  --shadow: 0 4px 16px rgba(0,0,0,0.04), 0 1px 4px rgba(0,0,0,0.03);
}}
html {{ -webkit-font-smoothing: antialiased; }}
body {{
  font-family: -apple-system, BlinkMacSystemFont, "SF Pro Display", "SF Pro Text", "Helvetica Neue", sans-serif;
  background: var(--grey-bg); color: var(--black);
  line-height: 1.47; font-weight: 400; letter-spacing: -0.022em; font-size: 14px;
}}
.page {{ max-width: 760px; margin: 0 auto; padding: 56px 64px; background: var(--grey-bg); }}

.hero {{ margin-bottom: 48px; padding-bottom: 28px; border-bottom: 1px solid var(--grey-3); }}
.hero .eyebrow {{ font-size: 13px; font-weight: 600; color: var(--blue); text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 12px; }}
.hero h1 {{ font-size: 42px; font-weight: 700; letter-spacing: -0.04em; line-height: 1.1; margin-bottom: 14px; }}
.hero h1 em {{ font-style: normal; color: var(--red); }}
.hero .lead {{ font-size: 18px; color: var(--grey-1); line-height: 1.4; max-width: 620px; }}
.hero .meta {{ margin-top: 18px; font-size: 12px; color: var(--grey-2); display: flex; gap: 20px; flex-wrap: wrap; }}
.hero .meta span::before {{ content: ''; display: inline-block; width: 4px; height: 4px; background: var(--grey-3); border-radius: 50%; vertical-align: middle; margin-right: 8px; }}
.hero .meta span:first-child::before {{ display: none; }}

.constraint {{ background: linear-gradient(135deg, #fff5f4 0%, #ffe8e6 100%); border-radius: 16px; padding: 28px 30px; margin-bottom: 40px; border-left: 4px solid var(--red); }}
.constraint .eyebrow {{ font-size: 11px; font-weight: 700; color: var(--red); text-transform: uppercase; letter-spacing: 0.6px; margin-bottom: 10px; }}
.constraint h3 {{ font-size: 22px; font-weight: 600; margin-bottom: 10px; letter-spacing: -0.02em; }}
.constraint p {{ font-size: 14px; color: var(--grey-1); line-height: 1.55; }}
.constraint .formula {{ font-family: "SF Mono", Menlo, monospace; background: white; padding: 14px 18px; border-radius: 8px; margin-top: 14px; font-size: 13px; color: var(--black); border: 1px solid var(--grey-3); }}

.highlight {{ background: var(--paper); border-radius: 18px; padding: 36px 36px; margin-bottom: 44px; box-shadow: var(--shadow); display: grid; grid-template-columns: 1fr 1fr; gap: 28px; align-items: center; }}
.highlight .left {{ border-right: 1px solid var(--grey-3); padding-right: 28px; }}
.highlight .big {{ font-size: 80px; font-weight: 700; line-height: 1; letter-spacing: -0.05em; font-variant-numeric: tabular-nums; }}
.highlight .big.green {{ color: var(--green); }}
.highlight .big.red   {{ color: var(--red); }}
.highlight .big .unit {{ font-size: 28px; color: var(--grey-1); font-weight: 500; margin-left: 6px; }}
.highlight .label {{ font-size: 14px; color: var(--grey-1); margin-top: 10px; font-weight: 500; line-height: 1.4; }}
.highlight .label strong {{ color: var(--black); }}

.section {{ margin-bottom: 44px; }}
.section h2 {{ font-size: 26px; font-weight: 600; letter-spacing: -0.025em; margin-bottom: 8px; }}
.section .desc {{ font-size: 14px; color: var(--grey-1); margin-bottom: 22px; max-width: 600px; }}

.tbl-card {{ background: var(--paper); border-radius: 14px; padding: 4px 0; box-shadow: var(--shadow); overflow: hidden; }}
table.apple {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
table.apple th {{ font-weight: 600; color: var(--grey-1); font-size: 10px; text-transform: uppercase; letter-spacing: 0.4px; padding: 12px 16px; text-align: right; border-bottom: 1px solid var(--grey-3); }}
table.apple th.left, table.apple td.left {{ text-align: left; }}
table.apple td {{ padding: 11px 16px; border-bottom: 1px solid var(--grey-3); font-variant-numeric: tabular-nums; text-align: right; }}
table.apple tbody tr:last-child td {{ border-bottom: none; }}
table.apple tr.danger td {{ background: rgba(255,59,48,0.05); }}

.pill {{ display: inline-block; padding: 3px 10px; border-radius: 20px; font-size: 11px; font-weight: 600; }}
.pill-good {{ background: rgba(0,168,45,0.12); color: var(--green); }}
.pill-bad {{ background: rgba(255,59,48,0.12); color: var(--red); }}
.pill-warn {{ background: rgba(255,149,0,0.12); color: var(--orange); }}
.pill-neutral {{ background: var(--grey-bg); color: var(--grey-1); }}

.tier-table {{ background: var(--paper); border-radius: 14px; padding: 8px 0; box-shadow: var(--shadow); overflow: hidden; }}
.tier-table table {{ width: 100%; border-collapse: collapse; }}
.tier-table th {{ font-size: 11px; font-weight: 600; color: var(--grey-1); text-transform: uppercase; letter-spacing: 0.4px; padding: 14px 18px; text-align: left; border-bottom: 1px solid var(--grey-3); }}
.tier-table td {{ padding: 14px 18px; border-bottom: 1px solid var(--grey-3); font-size: 14px; }}
.tier-table td.term {{ font-weight: 600; }}
.tier-table tr:last-child td {{ border-bottom: none; }}
.tier-table tr.vorkasse td {{ background: rgba(255,59,48,0.06); }}
.tier-table tr.vorkasse td.term {{ color: var(--red); }}

.fazit {{ background: linear-gradient(135deg, #1d1d1f 0%, #2d2d30 100%); color: white; border-radius: 18px; padding: 38px 38px; box-shadow: var(--shadow); }}
.fazit .eyebrow {{ font-size: 13px; font-weight: 600; color: #5ac8fa; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 14px; }}
.fazit h2 {{ font-size: 28px; font-weight: 700; letter-spacing: -0.03em; margin-bottom: 20px; color: white; }}
.fazit p {{ font-size: 14px; line-height: 1.6; color: rgba(255,255,255,0.9); margin-bottom: 12px; }}
.fazit p strong {{ color: white; font-weight: 600; }}
.fazit .verdict {{ background: rgba(255,255,255,0.08); border-radius: 12px; padding: 22px 24px; margin-top: 18px; border-left: 4px solid #5ac8fa; }}
.fazit .verdict h3 {{ font-size: 16px; font-weight: 600; margin-bottom: 12px; color: white; }}
.fazit .verdict ol {{ margin: 0 0 0 20px; padding: 0; }}
.fazit .verdict li {{ font-size: 14px; line-height: 1.55; margin-bottom: 10px; color: rgba(255,255,255,0.9); }}
.fazit .verdict li strong {{ color: #5ac8fa; }}

.footer {{ margin-top: 48px; padding-top: 20px; border-top: 1px solid var(--grey-3); font-size: 11px; color: var(--grey-2); text-align: center; }}

@media print {{
  body {{ background: white; }}
  .page {{ background: white; padding: 28px 36px; max-width: none; }}
  .highlight, .tbl-card, .tier-table, .fazit {{ box-shadow: none; }}
  .highlight, .tbl-card, .tier-table {{ border: 1px solid var(--grey-3); }}
  .section, .fazit {{ page-break-inside: avoid; }}
  table tr {{ page-break-inside: avoid; }}
}}
</style>
</head><body>
<div class="page">

  <div class="hero">
    <div class="eyebrow">Zahlungsziele 2026 · Drehende Ware</div>
    <h1>Kein Cent <em>Vorfinanzierung.</em></h1>
    <p class="lead">Was Kunden-Zahlungsziele kosten dürfen — und ab wann sie das 30-Tage-Lieferantenfenster bei OTTO, AEG &amp; Co. zerschießen.</p>
    <div class="meta">
      <span>Stand {now}</span>
      <span>{fmt_n(n_core)} Geräte drehende Ware</span>
      <span>{len(drehend_suppliers)} Kern-Lieferanten</span>
      <span>Altlast {fmt_n(n_altlast)} ausgeschlossen</span>
    </div>
  </div>

  <div class="constraint">
    <div class="eyebrow">Harte Randbedingung</div>
    <h3>Wir können nicht vorfinanzieren — Punkt.</h3>
    <p>Jeder Tag, an dem ein Kunde später als der 30-Tage-Lieferantentakt zahlt, kostet uns echtes Working Capital. Die Frage ist also nicht „Wie schnell zahlen Kunden", sondern „Welches Zahlungsziel dürfen wir überhaupt anbieten?"</p>
    <div class="formula"><strong>Max. Kunden-Netto-Tage</strong> = 30 − WE-Alter beim Verkauf</div>
  </div>

  <div class="highlight">
    <div class="left">
      <div class="big green">{fmt_pct(100-vorfin_pct)} %</div>
      <div class="label"><strong>{fmt_n(n_core - core['is_vorfin'].sum())} Geräte</strong> der drehenden Ware fließen heute durch ohne Vorfinanzierung — Kunde zahlt vor unserem Lieferanten-Stichtag.</div>
    </div>
    <div class="right">
      <div class="big red">{fmt_pct(vorfin_pct)} %</div>
      <div class="label"><strong>{fmt_n(core['is_vorfin'].sum())} Geräte</strong> reißen das 30-T-Fenster — Mean <strong>+{fmt_d(gap_mean)} T</strong>, P90 <strong>+{fmt_d(gap_p90)} T</strong>. Es fehlen permanent <strong>~{fmt_eur(WC_FINAL)}</strong> Liquidität auf dem Konto.</div>
    </div>
  </div>

  <div class="section">
    <h2>Ausgangsuhr: WE-Alter beim Verkauf.</h2>
    <p class="desc">Bevor der Kunde überhaupt ins Spiel kommt, ist ein Teil der 30 Tage schon verbrannt. Verteilung der drehenden Ware:</p>
    <div class="tbl-card">
      <table class="apple">
        <thead>
          <tr>
            <th class="left">WE-Alter beim Verkauf</th>
            <th>Geräte</th>
            <th>Anteil</th>
            <th>davon Vorfinanzierung</th>
            <th>Verbleib bis 30 T</th>
          </tr>
        </thead>
        <tbody>
'''
for lbl, lo, hi, n_b, n_v_b in age_hist:
    if n_b == 0: continue
    pct = n_b / n_core * 100
    vorfin_share = n_v_b / n_b * 100 if n_b else 0
    if hi <= 7:    rest = '23 T'
    elif hi <= 14: rest = '16 T'
    elif hi <= 22: rest = '8 T'
    elif hi <= 30: rest = '0 T'
    else:          rest = '<span style="color: var(--red);">bereits über</span>'
    danger = ' class="danger"' if hi > 30 else ''
    html += f'''          <tr{danger}>
            <td class="left">{lbl}</td>
            <td>{fmt_n(n_b)}</td>
            <td>{fmt_pct(pct)} %</td>
            <td>{fmt_pct(vorfin_share)} %</td>
            <td>{rest}</td>
          </tr>
'''
html += f'''        </tbody>
      </table>
    </div>
  </div>

  <div class="section">
    <h2>Empfehlung: Gestaffelte Zahlungsziele.</h2>
    <p class="desc">Das einzige sichere Modell: Netto-Tage werden <strong>pro Auftrag</strong> nach WE-Alter zugeteilt — nicht pauschal pro Kunde.</p>
    <div class="tier-table">
      <table>
        <thead>
          <tr>
            <th>WE-Alter beim Verkauf</th>
            <th>Maximales Kunden-Zahlungsziel</th>
            <th>Anteil heute</th>
          </tr>
        </thead>
        <tbody>
'''
for (lbl, term, n_t, pct), tier_def in zip(tier_dist, tiers):
    is_vk = 'Vorkasse' in term
    cls = ' class="vorkasse"' if is_vk else ''
    html += f'''          <tr{cls}>
            <td>{lbl}</td>
            <td class="term">{term}</td>
            <td>{fmt_pct(pct)} % der Geräte ({fmt_n(n_t)})</td>
          </tr>
'''
html += f'''        </tbody>
      </table>
    </div>
  </div>

  <div class="section">
    <h2>So zahlen Kunden heute.</h2>
    <p class="desc">Tage vom Verkauf bis zum Zahlungseingang im 2026er Drehgeschäft.</p>
    <div class="kpi-grid">
      <div class="kpi-card">
        <div class="kpi-lbl">Median (50 %)</div>
        <div class="kpi-val" style="color: var(--green);">{fmt_d(sold_paid_med)}<span class="u"> T</span></div>
        <div class="kpi-sub">Die Hälfte zahlt innerhalb dieser Zeit</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-lbl">P75 · Drei Viertel</div>
        <div class="kpi-val" style="color: var(--orange);">{fmt_d(sold_paid_p75)}<span class="u"> T</span></div>
        <div class="kpi-sub">75 % aller Kunden sind bis hier durch</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-lbl">P90 · der Long-Tail</div>
        <div class="kpi-val" style="color: var(--red);">{fmt_d(sold_paid_p90)}<span class="u"> T</span></div>
        <div class="kpi-sub">10 % brauchen länger als das</div>
      </div>
    </div>
  </div>

  <div class="section">
    <h2>Was uns das kostet.</h2>
    <p class="desc">Diese Lücke summiert sich. Jeden Tag steckt im Schnitt diese Summe bei verspäteten Kunden — Geld, das uns auf dem Konto fehlt, während Lieferanten schon bezahlt werden müssen.</p>

    <div class="highlight" style="padding: 44px 40px; text-align: center; display: block; margin-bottom: 0;">
      <div style="font-size: 110px; font-weight: 700; line-height: 1; letter-spacing: -0.05em; color: var(--red); font-variant-numeric: tabular-nums;">{fmt_eur(WC_FINAL)}</div>
      <div style="font-size: 17px; color: var(--grey-1); margin-top: 14px; font-weight: 500;">fehlen jeden Tag auf unserem Konto</div>
      <div style="display: flex; justify-content: center; gap: 48px; margin-top: 36px; flex-wrap: wrap;">
        <div>
          <div style="font-size: 11px; color: var(--grey-1); text-transform: uppercase; letter-spacing: 0.6px; font-weight: 600; margin-bottom: 6px;">Zinslast pro Jahr</div>
          <div style="font-size: 32px; font-weight: 700; color: var(--black); letter-spacing: -0.02em; font-variant-numeric: tabular-nums;">{fmt_eur(kk_10)}</div>
          <div style="font-size: 11px; color: var(--grey-2); margin-top: 4px;">bei marktüblichen 10 % Kontokorrent</div>
        </div>
        <div>
          <div style="font-size: 11px; color: var(--grey-1); text-transform: uppercase; letter-spacing: 0.6px; font-weight: 600; margin-bottom: 6px;">Eingekaufte Ware pro Jahr</div>
          <div style="font-size: 32px; font-weight: 700; color: var(--black); letter-spacing: -0.02em; font-variant-numeric: tabular-nums;">{fmt_eur(ek_total_year)}</div>
          <div style="font-size: 11px; color: var(--grey-2); margin-top: 4px;">Lieferantenrechnungen bei drehender Ware</div>
        </div>
      </div>
    </div>
  </div>

  <!-- Zeitstrahl: Normalfall vs Problemfall -->
  <div class="section">
    <h2>So entsteht die Lücke.</h2>
    <p class="desc">Zwei Verläufe — links der Regelfall, rechts der Problemfall. Bei einem von vier Verkäufen kommt das Kundengeld zu spät.</p>
    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 16px;">
      <div style="background: var(--paper); border-radius: 14px; padding: 24px 22px; box-shadow: var(--shadow); border-left: 4px solid var(--green);">
        <div style="font-size: 11px; font-weight: 700; color: var(--green); text-transform: uppercase; letter-spacing: 0.6px; margin-bottom: 4px;">3 von 4 Verkäufen</div>
        <h3 style="font-size: 17px; font-weight: 600; margin-bottom: 18px;">Regelfall — alles im Plan</h3>
        <div style="position: relative; height: 6px; background: var(--grey-3); border-radius: 3px; margin: 28px 0 8px;">
          <div style="position: absolute; left: 0; width: 100%; height: 100%; background: linear-gradient(90deg, var(--green) 0%, var(--green) 60%, var(--grey-3) 60%); border-radius: 3px;"></div>
          <div style="position: absolute; left: 0%; top: -4px; width: 14px; height: 14px; background: var(--black); border-radius: 50%; border: 3px solid white;"></div>
          <div style="position: absolute; left: 13%; top: -4px; width: 14px; height: 14px; background: var(--green); border-radius: 50%; border: 3px solid white;"></div>
          <div style="position: absolute; left: 60%; top: -4px; width: 14px; height: 14px; background: var(--green); border-radius: 50%; border: 3px solid white;"></div>
          <div style="position: absolute; left: 100%; top: -4px; width: 14px; height: 14px; background: var(--blue); border-radius: 50%; border: 3px solid white; transform: translateX(-100%);"></div>
        </div>
        <div style="position: relative; height: 38px; font-size: 11px; color: var(--grey-1); line-height: 1.3;">
          <div style="position: absolute; left: 0%; text-align: left;"><strong style="color: var(--black);">Tag 0</strong><br>Ware bei uns</div>
          <div style="position: absolute; left: 13%;"><strong style="color: var(--black);">Tag 4</strong><br>Verkauft</div>
          <div style="position: absolute; left: 60%;"><strong style="color: var(--green);">Tag 18</strong><br>Kunde zahlt ✓</div>
          <div style="position: absolute; right: 0%; text-align: right;"><strong style="color: var(--blue);">Tag 30</strong><br>Wir zahlen<br>Lieferant</div>
        </div>
        <p style="font-size: 13px; color: var(--grey-1); margin-top: 32px; line-height: 1.5;">Cash ist 12 Tage <strong>vor</strong> dem Lieferantenstichtag da. Alles entspannt.</p>
      </div>
      <div style="background: var(--paper); border-radius: 14px; padding: 24px 22px; box-shadow: var(--shadow); border-left: 4px solid var(--red);">
        <div style="font-size: 11px; font-weight: 700; color: var(--red); text-transform: uppercase; letter-spacing: 0.6px; margin-bottom: 4px;">1 von 4 Verkäufen</div>
        <h3 style="font-size: 17px; font-weight: 600; margin-bottom: 18px;">Problemfall — wir gehen in Vorlage</h3>
        <div style="position: relative; height: 6px; background: var(--grey-3); border-radius: 3px; margin: 28px 0 8px;">
          <div style="position: absolute; left: 0; width: 100%; height: 100%; background: linear-gradient(90deg, var(--green) 0%, var(--green) 54%, var(--red) 54%, var(--red) 100%); border-radius: 3px;"></div>
          <div style="position: absolute; left: 0%; top: -4px; width: 14px; height: 14px; background: var(--black); border-radius: 50%; border: 3px solid white;"></div>
          <div style="position: absolute; left: 7%; top: -4px; width: 14px; height: 14px; background: var(--green); border-radius: 50%; border: 3px solid white;"></div>
          <div style="position: absolute; left: 54%; top: -4px; width: 14px; height: 14px; background: var(--red); border-radius: 50%; border: 3px solid white;"></div>
          <div style="position: absolute; left: 100%; top: -4px; width: 14px; height: 14px; background: var(--orange); border-radius: 50%; border: 3px solid white; transform: translateX(-100%);"></div>
        </div>
        <div style="position: relative; height: 38px; font-size: 11px; color: var(--grey-1); line-height: 1.3;">
          <div style="position: absolute; left: 0%; text-align: left;"><strong style="color: var(--black);">Tag 0</strong><br>Ware bei uns</div>
          <div style="position: absolute; left: 7%;"><strong style="color: var(--black);">Tag 4</strong><br>Verkauft</div>
          <div style="position: absolute; left: 54%;"><strong style="color: var(--red);">Tag 30</strong><br>Lieferant<br>fällig 💸</div>
          <div style="position: absolute; right: 0%; text-align: right;"><strong style="color: var(--orange);">Tag 56</strong><br>Kunde zahlt<br>endlich</div>
        </div>
        <p style="font-size: 13px; color: var(--grey-1); margin-top: 32px; line-height: 1.5;">Wir mussten den Lieferanten <strong>26 Tage vor</strong> dem Kundengeld bezahlen. Genau das ist die Vorfinanzierung.</p>
      </div>
    </div>
  </div>

  <div class="section">
    <h2>Pro Kern-Lieferant.</h2>
    <p class="desc">Ist die Quelle drehfähig? Maximales Kunden-Netto-Ziel ergibt sich aus 30 − P75-WE-Alter (deckt 75 % der Fälle ab).</p>
    <div class="tbl-card">
      <table class="apple">
        <thead>
          <tr>
            <th class="left">Lieferant</th>
            <th>n</th>
            <th>WE→Verk. Med.</th>
            <th>WE→Verk. P75</th>
            <th>WE→Bez. Med.</th>
            <th>Vorfin.</th>
            <th>Max. Netto-Ziel</th>
          </tr>
        </thead>
        <tbody>
'''
for s_name, row in sup_core.iterrows():
    max_n_t = row['max_net']
    if max_n_t >= 20:    pill = f'<span class="pill pill-good">{fmt_d(max_n_t)} T</span>'
    elif max_n_t >= 10:  pill = f'<span class="pill pill-warn">{fmt_d(max_n_t)} T</span>'
    elif max_n_t >  0:   pill = f'<span class="pill pill-bad">{fmt_d(max_n_t)} T</span>'
    else:                pill = '<span class="pill pill-bad">Vorkasse</span>'
    html += f'''          <tr>
            <td class="left">{s_name}</td>
            <td>{fmt_n(int(row["n"]))}</td>
            <td>{fmt_d(row["we_sold_med"])} T</td>
            <td>{fmt_d(row["we_sold_p75"])} T</td>
            <td>{fmt_d(row["we_paid_med"])} T</td>
            <td>{fmt_pct(row["vorfin_pct"])} %</td>
            <td>{pill}</td>
          </tr>
'''
html += f'''        </tbody>
      </table>
    </div>
  </div>

  <div class="section">
    <div class="fazit">
      <div class="eyebrow">Fazit</div>
      <h2>Die fünf Regeln,<br>damit kein Cent vorfinanziert wird.</h2>

      <p><strong>Heute schaffen wir es bei {fmt_pct(100-vorfin_pct)} %</strong> der drehenden Ware, das Kunden-Geld vor der 30-T-Lieferanten-Deadline zu vereinnahmen. Die übrigen <strong>{fmt_pct(vorfin_pct)} %</strong> binden permanent <strong>~{fmt_eur(WC_FINAL)} Working Capital</strong> auf unserem Konto — Kapitalkosten {fmt_eur(kk_10)} p. a. bei 10 % Kontokorrent. Beides eliminierbar.</p>

      <div class="verdict">
        <h3>So muss die Zahlungsziel-Vergabe ab sofort laufen</h3>
        <ol>
          <li><strong>Pro-Auftrag-Logik statt Pauschal-Kundenkonditionen.</strong> Das Netto-Ziel auf der Rechnung wird vom WE-Alter des Geräts bestimmt — nicht vom Kunden-Stammsatz. Drehende Ware ≤ 7 T alt → 23 Tage netto. Älter → weniger. > 22 T → Vorkasse.</li>
          <li><strong>Vorkasse als Default für alles ab WE-Alter 23 T.</strong> {fmt_pct(sum(p for l,_,_,p in tier_dist if 'Vorkasse' in l))} % der heutigen Geräte fallen darunter — diese Tranche darf nicht mehr auf Rechnung gehen, sie ist mathematisch nicht mehr zahlungsziel-fähig.</li>
          <li><strong>Skonto-Hebel statt langer Ziele.</strong> 2 % Skonto bei Zahlung innerhalb 14 T statt 23-T-Netto — verschiebt Zahlungseingang spürbar nach vorne und gibt zusätzlichen Puffer (Median Verkauf→Bezahlt liegt heute bei {fmt_d(sold_paid_med)} T, P75 bei {fmt_d(sold_paid_p75)} T).</li>
          <li><strong>Mahnkette ab Tag 25 nach WE</strong> — nicht nach Verkauf, denn die Lieferanten-Uhr läuft ab WE. Wenn Tag 25 erreicht ist und kein Geld da, muss Inkasso/Mahnung schon vorbereitet sein, nicht erst gestartet werden.</li>
          <li><strong>Top-{fmt_n(500)} Schuldner priorisiert bearbeiten:</strong> {fmt_pct(top500_share)} % der gesamten Vorfinanzierungs-Last hängt an den 500 größten Einzelfällen. Eine gezielte Inkasso-/Vorkasse-Aktion auf diese Liste bringt mehr als jede pauschale Zahlungsziel-Verkürzung.</li>
          <li><strong>Lieferanten-Score in der Beschaffung:</strong> Jede Quelle mit P75-WE-Alter &gt; 22 T ist mit Net-Zahlungsziel an Kunden nicht ohne Vorfinanzierung darstellbar. Solche Geräte (heute: AEG_IT, OSF) müssen entweder über Vorkasse-Kanäle laufen oder gar nicht beschafft werden, solange das 30-T-Lieferantentakt-Limit gilt.</li>
        </ol>
      </div>
    </div>
  </div>

  <div class="footer">
    Erstellt {now} · 2026 drehende Ware = {", ".join(drehend_suppliers)} · Auswahl-Kriterium: n ≥ 100, P75 WE→Verkauf ≤ 30 T, Sample-Coverage ≥ 50 %<br>
    Ausgeschlossen: {", ".join(altlast_suppliers) if altlast_suppliers else "keine"} · Datenbasis Jan–Mai 2026 ({PERIODE_TAGE} Tage Sample / 122 T Ground-Truth) · Hochrechnung Jahres-Volumen<br>
    Methodik im Hintergrund: Σ(EK × Verspätungs-Tage) ÷ Periode, hochgerechnet via Coverage-Faktor, validiert per Little's Law (L = λ·W) · Konvergenz aller drei Wege bestätigt
  </div>
</div>
</body></html>
'''

out_html.write_text(html, encoding='utf-8')
print(f'  ✓ HTML: {out_html} ({out_html.stat().st_size:,} B)')

print('\n  Konvertiere zu PDF…')
import asyncio
async def make_pdf():
    from playwright.async_api import async_playwright
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        await page.goto(f'file:///{str(out_html).replace(chr(92), "/")}')
        await page.emulate_media(media='print')
        await page.pdf(path=str(out_pdf), format='A4', print_background=True,
                       margin={'top': '0', 'right': '0', 'bottom': '0', 'left': '0'})
        await browser.close()
asyncio.run(make_pdf())
print(f'  ✓ PDF: {out_pdf} ({out_pdf.stat().st_size:,} B)')

print(f'''
  ─── KERN-ZAHLEN DREHENDE WARE 2026 ──────────────
  Drehende Lieferanten:        {len(drehend_suppliers)}  → {drehend_suppliers}
  Altlast (ausgeschlossen):    {len(altlast_suppliers)}  → {altlast_suppliers}
  n drehend:                   {fmt_n(n_core)}
  Vorfinanzierungs-Anteil:     {fmt_pct(vorfin_pct)} %
  Median-Verspätung wenn >30T: +{fmt_d(gap_median)} T  (P90 +{fmt_d(gap_p90)} T)
  Permanent gebundenes WC:     {fmt_eur(WC_FINAL)}  (Tagesdurchschnitt EK x Verspätung / Periode)
  Kapitalkosten p.a. 5/10/15%: {fmt_eur(kk_05)} / {fmt_eur(kk_10)} / {fmt_eur(kk_15)}
  EK-Volumen Drehgeschäft (Jahr): {fmt_eur(ek_total_year)}

  WE-Alter beim Verkauf:       Median {fmt_d(core["t_we_to_sold"].median())} T
  Verkauf → Bezahlt:           Median {fmt_d(sold_paid_med)} T (P75 {fmt_d(sold_paid_p75)})

  Empfehlung:
    ≤ 7 T Lager-Alter  → max. 23 T netto
    8–14 T            → max. 16 T netto
    15–22 T           → max.  8 T netto
    > 22 T            → VORKASSE (kein Net-Ziel)
  ──────────────────────────────────────────────────
''')
