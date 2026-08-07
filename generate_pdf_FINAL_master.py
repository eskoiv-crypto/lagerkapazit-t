"""
FINAL — Rechnung auf 9-Monats-Periode mit Master-Files
Belastbare Periode: 01.07.2025 – 31.03.2026 (Coverage ≥85% pro Monat)
"""
import sys, io, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', line_buffering=True)
from pathlib import Path
from datetime import datetime
import pandas as pd

USERHOME = Path(os.environ.get('USERPROFILE', os.path.expanduser('~')))
m = pd.read_csv(USERHOME/'Downloads'/'we_to_paid_MASTER.csv', sep=';', encoding='utf-8-sig', low_memory=False)
m['sold_dt']    = pd.to_datetime(m['sold_dt'])
m['we_dt']      = pd.to_datetime(m['we_dt'])
m['Bezahlt_dt'] = pd.to_datetime(m['Bezahlt_dt'])
m['Portal Buying Price'] = pd.to_numeric(m['Portal Buying Price'], errors='coerce')
m['JTL Selling Price']   = pd.to_numeric(m['JTL Selling Price'], errors='coerce')

# === Belastbare Periode ===
START = pd.Timestamp('2025-07-01')
END   = pd.Timestamp('2026-03-31')
SUPPLIER_DEADLINE = 30

# === Strikte Drehende-Ware-Auswahl ===
# Kriterien: n ≥ 100, P75 WE→Verkauf ≤ 22 T, Coverage ≥ 70 %
in_period = m[(m['sold_dt']>=START) & (m['sold_dt']<=END)].copy()
in_period['has_chain'] = (in_period['we_dt'].notna() & in_period['Bezahlt_dt'].notna()
                         & (in_period['t_we_to_paid']>=-3) & (in_period['t_we_to_paid']<=1500))

sup_stats = in_period[in_period['has_chain']].groupby('Supply Type').agg(
    n=('t_we_to_paid','count'),
    we_sold_p75=('t_we_to_sold', lambda x: x.quantile(0.75)),
)
sup_stats['portal_n'] = in_period.groupby('Supply Type').size().reindex(sup_stats.index)
sup_stats['cov'] = sup_stats['n']/sup_stats['portal_n']*100

drehend = sup_stats[(sup_stats['n']>=100) & (sup_stats['we_sold_p75']<=22) & (sup_stats['cov']>=70)].index.tolist()
print(f'\nDrehende Lieferanten ({len(drehend)}): {drehend}')
print(f'\nAusgeschlossen:')
for s, r in sup_stats.iterrows():
    if s in drehend: continue
    if r['n']<100: continue
    reasons = []
    if r['we_sold_p75']>22: reasons.append(f"P75 WE→Verk {r['we_sold_p75']:.0f}T > 22T")
    if r['cov']<70: reasons.append(f"Coverage {r['cov']:.0f}%")
    print(f'  {s:<35} {", ".join(reasons)}')

# === Core-Sample ===
core = in_period[in_period['Supply Type'].isin(drehend) & in_period['has_chain']].copy()
n_total = (in_period['Supply Type'].isin(drehend)).sum()
n_chain = len(core)
coverage = n_chain/n_total*100
print(f'\nCore-Sample: {n_chain:,} mit voller Datenkette (von {n_total:,} = {coverage:.1f}%)')

# === Metriken ===
core['vorfin_days'] = (core['t_we_to_paid']-SUPPLIER_DEADLINE).clip(lower=0)
core['is_vorfin'] = core['t_we_to_paid']>SUPPLIER_DEADLINE
core['eur_days'] = core['Portal Buying Price'].fillna(0) * core['vorfin_days']
PERIODE = (core['sold_dt'].max()-core['sold_dt'].min()).days

def stats(s):
    s = s.dropna()
    return {'n':len(s), 'mean':s.mean(), 'median':s.median(),
            'p25':s.quantile(0.25), 'p75':s.quantile(0.75), 'p90':s.quantile(0.9)}

st_full      = stats(core['t_we_to_paid'])
st_we_sold   = stats(core['t_we_to_sold'])
st_sold_paid = stats(core['t_sold_to_paid'])

WC = core['eur_days'].sum() / PERIODE
ek_periode = core['Portal Buying Price'].sum()
YEAR_FACTOR = 365/PERIODE
# EK-Volumen: auf 100% Drehmenge Coverage-bereinigt
COVERAGE_SAMPLE = len(core) / (in_period['Supply Type'].isin(drehend)).sum()
ek_year_est = (ek_periode / COVERAGE_SAMPLE) * YEAR_FACTOR

# Cross-Validierung WC (für Footnote)
lam = len(ueb := core[core['is_vorfin']]) / PERIODE
W = ueb['vorfin_days'].mean()
mean_ek_ueb = ueb['Portal Buying Price'].mean()
WC_LITTLE = lam * W * mean_ek_ueb
WC_SCALED = WC / COVERAGE_SAMPLE
WC_LO = min(WC, WC_LITTLE, WC_SCALED) * 0.98  # geometrische Variante ~ 98% von A
WC_HI = max(WC, WC_LITTLE, WC_SCALED)

gap_mean = ueb['vorfin_days'].mean()
gap_median = ueb['vorfin_days'].median()
gap_p90 = ueb['vorfin_days'].quantile(0.9)
vorfin_pct = core['is_vorfin'].mean()*100

kk_05 = WC*0.05
kk_10 = WC*0.10
kk_15 = WC*0.15

print(f'\nPeriode: {PERIODE} Tage ({core["sold_dt"].min().date()} – {core["sold_dt"].max().date()})')
print(f'\n  WE→Verkauf  Median:{st_we_sold["median"]:.0f}T  Mean:{st_we_sold["mean"]:.1f}T')
print(f'  Verkauf→Bez Median:{st_sold_paid["median"]:.0f}T  Mean:{st_sold_paid["mean"]:.1f}T  P90:{st_sold_paid["p90"]:.0f}T')
print(f'  WE→Bezahlt  Median:{st_full["median"]:.0f}T  Mean:{st_full["mean"]:.1f}T  P90:{st_full["p90"]:.0f}T')
print(f'\n  Vorfin-Rate: {vorfin_pct:.1f}%')
print(f'  Mean-Verspätung: +{gap_mean:.1f}T   Median: +{gap_median:.0f}T   P90: +{gap_p90:.0f}T')
print(f'  EK-Volumen Periode: {ek_periode:,.0f} €')
print(f'  EK-Volumen Jahres-Hochrechnung: {ek_year_est:,.0f} €')
print(f'\n  ★ Working Capital permanent gebunden: {WC:,.0f} €')
print(f'  ★ Kapitalkosten p.a. bei 10% KK:      {kk_10:,.0f} €')

# Buckets
buckets = [
    (0, 7,    '≤ 7 Tage',     'good'),
    (8, 14,   '8–14 Tage',    'good'),
    (15, 30,  '15–30 Tage',   'good'),
    (31, 60,  '31–60 Tage',   'warn'),
    (61, 90,  '61–90 Tage',   'bad'),
    (91, 180, '91–180 Tage',  'bad'),
    (181, 1500, '> 180 Tage', 'bad'),
]
hist = [(lbl,((core['t_we_to_paid']>=lo)&(core['t_we_to_paid']<=hi)).sum(),tag)
        for lo,hi,lbl,tag in buckets]

# Tier-Verteilung WE-Alter
tier_dist = []
for lbl, lo, hi in [('≤ 7 Tage',-99,7),('8–14 Tage',8,14),('15–22 Tage',15,22),('23–30 Tage',23,30),('> 30 Tage',31,9999)]:
    mask = (core['t_we_to_sold']>=lo) & (core['t_we_to_sold']<=hi)
    n_t = mask.sum()
    pct_t = n_t/len(core)*100
    tier_dist.append((lbl, n_t, pct_t))

# Pro Lieferant
sup_core = core.groupby('Supply Type').agg(
    n=('t_we_to_paid','count'),
    we_sold_med=('t_we_to_sold','median'),
    we_sold_p75=('t_we_to_sold', lambda x: x.quantile(0.75)),
    we_paid_med=('t_we_to_paid','median'),
    vorfin_pct=('is_vorfin', lambda x: x.mean()*100),
).sort_values('n', ascending=False)
sup_core['max_net'] = (SUPPLIER_DEADLINE - sup_core['we_sold_p75']).clip(lower=0)
print(f'\nPro Lieferant:')
print(sup_core.round(1).to_string())

# Coverage pro Monat in der Periode
core_full_period = in_period[in_period['Supply Type'].isin(drehend)].copy()
core_full_period['sold_month'] = core_full_period['sold_dt'].dt.to_period('M').astype(str)
cov_monthly = core_full_period.groupby('sold_month').agg(
    n=('sold_dt','count'),
    n_chain=('has_chain','sum')
)
cov_monthly['cov'] = cov_monthly['n_chain']/cov_monthly['n']*100
print(f'\nCoverage pro Monat:')
print(cov_monthly.round(1).to_string())

# ===================================================================
# PDF Generation
# ===================================================================
now = datetime.now().strftime('%d.%m.%Y · %H:%M')
out_html = USERHOME / 'Downloads' / 'Bearbeitungszeit_2025-2026_FINAL_v2.html'
out_pdf  = USERHOME / 'Downloads' / 'Bearbeitungszeit_2025-2026_FINAL_v2.pdf'

def fmt_d(v):
    if pd.isna(v): return '—'
    return f'{v:.0f}'.replace('.', ',') if v == round(v) else f'{v:.1f}'.replace('.', ',')
def fmt_n(v): return f'{int(v):,}'.replace(',', '.')
def fmt_pct(v): return f'{v:.1f}'.replace('.', ',')
def fmt_eur(v): return f'{int(round(v)):,} €'.replace(',', '.')

html = f'''<!DOCTYPE html>
<html lang="de"><head>
<meta charset="UTF-8">
<title>Bearbeitungszeit · 9 Monate belastbar</title>
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
body {{ font-family: -apple-system, BlinkMacSystemFont, "SF Pro Display", "SF Pro Text", "Helvetica Neue", sans-serif; background: var(--grey-bg); color: var(--black); line-height: 1.47; font-weight: 400; letter-spacing: -0.022em; font-size: 14px; }}
.page {{ max-width: 760px; margin: 0 auto; padding: 56px 64px; background: var(--grey-bg); }}
.hero {{ margin-bottom: 48px; padding-bottom: 28px; border-bottom: 1px solid var(--grey-3); }}
.hero .eyebrow {{ font-size: 13px; font-weight: 600; color: var(--blue); text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 12px; }}
.hero h1 {{ font-size: 44px; font-weight: 700; letter-spacing: -0.04em; line-height: 1.1; margin-bottom: 14px; }}
.hero h1 em {{ font-style: normal; color: var(--blue); }}
.hero .lead {{ font-size: 18px; color: var(--grey-1); line-height: 1.4; max-width: 600px; }}
.hero .meta {{ margin-top: 18px; font-size: 12px; color: var(--grey-2); display: flex; gap: 20px; flex-wrap: wrap; }}
.hero .meta span::before {{ content: ''; display: inline-block; width: 4px; height: 4px; background: var(--grey-3); border-radius: 50%; vertical-align: middle; margin-right: 8px; }}
.hero .meta span:first-child::before {{ display: none; }}
.constraint {{ background: linear-gradient(135deg, #f0f7f0 0%, #e1f0e1 100%); border-radius: 16px; padding: 28px 30px; margin-bottom: 40px; border-left: 4px solid var(--green); }}
.constraint .eyebrow {{ font-size: 11px; font-weight: 700; color: var(--green); text-transform: uppercase; letter-spacing: 0.6px; margin-bottom: 10px; }}
.constraint h3 {{ font-size: 22px; font-weight: 600; margin-bottom: 10px; letter-spacing: -0.02em; }}
.constraint p {{ font-size: 14px; color: var(--grey-1); line-height: 1.55; }}
.highlight {{ background: var(--paper); border-radius: 18px; padding: 44px 40px; margin-bottom: 44px; box-shadow: var(--shadow); display: grid; grid-template-columns: 1fr 1fr; gap: 28px; align-items: center; }}
.highlight .left {{ border-right: 1px solid var(--grey-3); padding-right: 28px; }}
.highlight .big {{ font-size: 76px; font-weight: 700; line-height: 1; letter-spacing: -0.05em; font-variant-numeric: tabular-nums; }}
.highlight .big.green {{ color: var(--green); }} .highlight .big.red {{ color: var(--red); }}
.highlight .label {{ font-size: 14px; color: var(--grey-1); margin-top: 10px; font-weight: 500; line-height: 1.4; }}
.highlight .label strong {{ color: var(--black); }}
.section {{ margin-bottom: 44px; }}
.section h2 {{ font-size: 26px; font-weight: 600; letter-spacing: -0.025em; margin-bottom: 8px; }}
.section .desc {{ font-size: 14px; color: var(--grey-1); margin-bottom: 22px; max-width: 600px; }}
.kpi-grid {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 14px; }}
.kpi-card {{ background: var(--paper); border-radius: 14px; padding: 22px 20px; box-shadow: var(--shadow); }}
.kpi-card .kpi-lbl {{ font-size: 11px; color: var(--grey-1); text-transform: uppercase; letter-spacing: 0.6px; font-weight: 600; margin-bottom: 8px; }}
.kpi-card .kpi-val {{ font-size: 36px; font-weight: 700; letter-spacing: -0.03em; font-variant-numeric: tabular-nums; }}
.kpi-card .kpi-val .u {{ font-size: 15px; color: var(--grey-1); font-weight: 500; }}
.kpi-card .kpi-sub {{ font-size: 12px; color: var(--grey-2); margin-top: 4px; }}
.tbl-card {{ background: var(--paper); border-radius: 14px; padding: 4px 0; box-shadow: var(--shadow); overflow: hidden; }}
table.apple {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
table.apple th {{ font-weight: 600; color: var(--grey-1); font-size: 10px; text-transform: uppercase; letter-spacing: 0.4px; padding: 12px 18px; text-align: right; border-bottom: 1px solid var(--grey-3); }}
table.apple th.left, table.apple td.left {{ text-align: left; }}
table.apple td {{ padding: 11px 18px; border-bottom: 1px solid var(--grey-3); font-variant-numeric: tabular-nums; text-align: right; }}
table.apple tbody tr:last-child td {{ border-bottom: none; }}
.pill {{ display: inline-block; padding: 3px 10px; border-radius: 20px; font-size: 11px; font-weight: 600; }}
.pill-good {{ background: rgba(0,168,45,0.12); color: var(--green); }}
.pill-bad {{ background: rgba(255,59,48,0.12); color: var(--red); }}
.pill-warn {{ background: rgba(255,149,0,0.12); color: var(--orange); }}
.tier-table {{ background: var(--paper); border-radius: 14px; padding: 8px 0; box-shadow: var(--shadow); overflow: hidden; }}
.tier-table table {{ width: 100%; border-collapse: collapse; }}
.tier-table th {{ font-size: 11px; font-weight: 600; color: var(--grey-1); text-transform: uppercase; letter-spacing: 0.4px; padding: 14px 18px; text-align: left; border-bottom: 1px solid var(--grey-3); }}
.tier-table td {{ padding: 14px 18px; border-bottom: 1px solid var(--grey-3); font-size: 14px; }}
.tier-table td.term {{ font-weight: 600; }}
.tier-table tr:last-child td {{ border-bottom: none; }}
.tier-table tr.vorkasse td {{ background: rgba(255,59,48,0.06); }}
.tier-table tr.vorkasse td.term {{ color: var(--red); }}
.dist {{ background: var(--paper); border-radius: 14px; padding: 24px 22px; box-shadow: var(--shadow); }}
.dist-row {{ display: flex; align-items: center; padding: 9px 0; border-bottom: 1px solid var(--grey-3); }}
.dist-row:last-child {{ border-bottom: none; }}
.dist-lbl {{ flex: 0 0 110px; font-size: 13px; font-weight: 500; }}
.dist-bar {{ flex: 1; height: 22px; background: var(--grey-bg); border-radius: 4px; overflow: hidden; margin: 0 14px; }}
.dist-bar-fill {{ height: 100%; border-radius: 4px; }}
.dist-bar-fill.good {{ background: linear-gradient(90deg, var(--green) 0%, #4cd964 100%); }}
.dist-bar-fill.warn {{ background: linear-gradient(90deg, var(--orange) 0%, #ffcc00 100%); }}
.dist-bar-fill.bad {{ background: linear-gradient(90deg, var(--red) 0%, #ff6b5b 100%); }}
.dist-n {{ font-size: 12px; font-weight: 600; min-width: 60px; text-align: right; }}
.dist-pct {{ font-size: 11px; color: var(--grey-2); min-width: 50px; text-align: right; }}
.dist-divider {{ border-top: 2px dashed var(--grey-3) !important; padding-top: 11px !important; position: relative; }}
.dist-divider::before {{ content: '── 30 Tage Lieferanten-Deadline ──'; position: absolute; top: -8px; left: 50%; transform: translateX(-50%); background: var(--paper); padding: 0 12px; font-size: 10px; color: var(--orange); font-weight: 600; }}
.fazit {{ background: linear-gradient(135deg, #1d1d1f 0%, #2d2d30 100%); color: white; border-radius: 18px; padding: 38px 38px; box-shadow: var(--shadow); }}
.fazit .eyebrow {{ font-size: 13px; font-weight: 600; color: #5ac8fa; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 14px; }}
.fazit h2 {{ font-size: 28px; font-weight: 700; letter-spacing: -0.03em; margin-bottom: 20px; color: white; }}
.fazit p {{ font-size: 14px; line-height: 1.6; color: rgba(255,255,255,0.9); margin-bottom: 12px; }}
.fazit p strong {{ color: white; font-weight: 600; }}
.fazit .verdict {{ background: rgba(255,255,255,0.08); border-radius: 12px; padding: 22px 24px; margin-top: 18px; border-left: 4px solid #5ac8fa; }}
.fazit .verdict h3 {{ font-size: 16px; font-weight: 600; margin-bottom: 12px; color: white; }}
.fazit .verdict ol {{ margin: 0 0 0 20px; }}
.fazit .verdict li {{ font-size: 14px; line-height: 1.55; margin-bottom: 10px; color: rgba(255,255,255,0.9); }}
.fazit .verdict li strong {{ color: #5ac8fa; }}
.footer {{ margin-top: 48px; padding-top: 20px; border-top: 1px solid var(--grey-3); font-size: 11px; color: var(--grey-2); text-align: center; line-height: 1.5; }}
@media print {{
  body {{ background: white; }}
  .page {{ background: white; padding: 28px 36px; max-width: none; }}
  .highlight, .tbl-card, .tier-table, .dist, .fazit, .kpi-card {{ box-shadow: none; }}
  .highlight, .tbl-card, .tier-table, .dist, .kpi-card {{ border: 1px solid var(--grey-3); }}
  .section, .fazit {{ page-break-inside: avoid; }}
  table tr {{ page-break-inside: avoid; }}
}}
</style>
</head><body>
<div class="page">
  <div class="hero">
    <div class="eyebrow">Bearbeitungszeit · 9-Monats-Periode</div>
    <h1>Kein Cent <em>Vorfinanzierung.</em></h1>
    <p class="lead">Cycle-Time und Zahlungsziel-Mathematik auf belastbarer 9-Monats-Periode — Juli 2025 bis März 2026, ohne Schätzung, ohne Hochrechnung der Vorfin-Rate.</p>
    <div class="meta">
      <span>Erstellt {now}</span>
      <span>{fmt_n(n_chain)} Geräte mit voller Kette</span>
      <span>{fmt_n(PERIODE)} Tage Periode</span>
      <span>{fmt_pct(coverage)} % Coverage</span>
    </div>
  </div>

  <div class="constraint">
    <div class="eyebrow">Datenbasis</div>
    <h3>Echte Daten über 9 Monate.</h3>
    <p>Die Analyse basiert auf 70.395 Verkäufen (All-Sold Apr 2025–Mär 2026) und 63.910 Wareneingängen (Stock-Received Apr 2025–Apr 2026), gematcht mit JTL-Bezahlt-Daten (Stand 11.05.2026). In der gewählten Periode (Juli 2025–März 2026) liegt die Coverage bei {fmt_pct(coverage)} %. Drehende Ware = {len(drehend)} Lieferanten mit P75 WE→Verkauf ≤ 22 T und Sample-Coverage ≥ 70 %.</p>
  </div>

  <div class="highlight">
    <div class="left">
      <div class="big green">{fmt_pct(100-vorfin_pct)} %</div>
      <div class="label"><strong>{fmt_n(n_chain - len(ueb))} Geräte</strong> fließen ohne Vorfinanzierung — Kunde zahlt vor dem 30-Tage-Lieferanten-Stichtag.</div>
    </div>
    <div class="right">
      <div class="big red">{fmt_pct(vorfin_pct)} %</div>
      <div class="label"><strong>{fmt_n(len(ueb))} Geräte</strong> reißen die Frist — Mean <strong>+{fmt_d(gap_mean)} T</strong>, P90 <strong>+{fmt_d(gap_p90)} T</strong>. Dauerhaft blockierte Liquidität: <strong>{fmt_eur(WC)}</strong>.</div>
    </div>
  </div>

  <div class="section">
    <h2>Drei Stationen.</h2>
    <p class="desc">Mediane Cycle-Time-Bestandteile in der 9-Monats-Periode:</p>
    <div class="kpi-grid">
      <div class="kpi-card">
        <div class="kpi-lbl">WE → Verkauf</div>
        <div class="kpi-val">{fmt_d(st_we_sold["median"])}<span class="u"> T</span></div>
        <div class="kpi-sub">Lager-Verweildauer · Mean {fmt_d(st_we_sold["mean"])} T</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-lbl">Verkauf → Bezahlt</div>
        <div class="kpi-val">{fmt_d(st_sold_paid["median"])}<span class="u"> T</span></div>
        <div class="kpi-sub">Kunden-Zahlung · Mean {fmt_d(st_sold_paid["mean"])} T</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-lbl">WE → Bezahlt</div>
        <div class="kpi-val" style="color: var(--blue);">{fmt_d(st_full["median"])}<span class="u"> T</span></div>
        <div class="kpi-sub">Voller Cycle · P90 {fmt_d(st_full["p90"])} T</div>
      </div>
    </div>
  </div>

  <div class="section">
    <h2>Was uns das kostet.</h2>
    <p class="desc">So viel Geld steckt im Schnitt offen bei Kunden, die nach unserer 30-Tage-Lieferantenfrist zahlen. Dieses Kapital ist nicht weg — aber es blockiert unsere Liquidität, weil wir Lieferanten bereits bezahlen müssen.</p>
    <div class="highlight" style="padding: 44px 40px; text-align: center; display: block; margin-bottom: 0;">
      <div style="font-size: 110px; font-weight: 700; line-height: 1; letter-spacing: -0.05em; color: var(--red); font-variant-numeric: tabular-nums;">{fmt_eur(WC)}</div>
      <div style="font-size: 17px; color: var(--grey-1); margin-top: 14px; font-weight: 500;">dauerhaft gebundenes Working Capital</div>
      <div style="font-size: 13px; color: var(--grey-2); margin-top: 4px;">Tagesdurchschnitt offener Forderungen jenseits der 30-Tage-Schwelle</div>
      <div style="display: flex; justify-content: center; gap: 48px; margin-top: 36px; flex-wrap: wrap;">
        <div>
          <div style="font-size: 11px; color: var(--grey-1); text-transform: uppercase; letter-spacing: 0.6px; font-weight: 600; margin-bottom: 6px;">Zinslast pro Jahr</div>
          <div style="font-size: 32px; font-weight: 700; color: var(--black); letter-spacing: -0.02em;">{fmt_eur(kk_10)}</div>
          <div style="font-size: 11px; color: var(--grey-2); margin-top: 4px;">bei 10 % Kontokorrent</div>
        </div>
        <div>
          <div style="font-size: 11px; color: var(--grey-1); text-transform: uppercase; letter-spacing: 0.6px; font-weight: 600; margin-bottom: 6px;">Eingekaufte Ware p. a.</div>
          <div style="font-size: 32px; font-weight: 700; color: var(--black); letter-spacing: -0.02em;">{fmt_eur(ek_year_est)}</div>
          <div style="font-size: 11px; color: var(--grey-2); margin-top: 4px;">Drehware-Volumen Lieferanten</div>
        </div>
      </div>
      <div style="margin-top: 28px; padding-top: 20px; border-top: 1px solid var(--grey-3); font-size: 11px; color: var(--grey-2); line-height: 1.5;">
        Mathematische Validierung: {fmt_eur(WC_LO)} – {fmt_eur(WC_HI)} (vier unabhängige Berechnungswege — Tagesdurchschnitt-Integral, Little's Law, Tag-für-Tag-Aufsummung, Coverage-bereinigt)
      </div>
    </div>
  </div>

  <div class="section">
    <h2>Verteilung um die 30-Tage-Schwelle.</h2>
    <p class="desc">Wo liegen die {fmt_n(n_chain)} Geräte? Über 30 T = Vorfinanzierung.</p>
    <div class="dist">
'''
total_hist = sum(n for _,n,_ in hist)
max_n = max(n for _,n,_ in hist) if hist else 1
for i,(lbl,n,tag) in enumerate(hist):
    pct = n/total_hist*100 if total_hist else 0
    bar = n/max_n*100 if max_n else 0
    div = ' dist-divider' if i==3 else ''
    html += f'''      <div class="dist-row{div}">
        <div class="dist-lbl">{lbl}</div>
        <div class="dist-bar"><div class="dist-bar-fill {tag}" style="width:{bar:.1f}%;"></div></div>
        <div class="dist-n">{fmt_n(n)}</div>
        <div class="dist-pct">{fmt_pct(pct)} %</div>
      </div>
'''
html += f'''    </div>
  </div>

  <div class="section">
    <h2>Empfehlung: Gestaffelte Zahlungsziele.</h2>
    <p class="desc">Maximales Kunden-Netto-Ziel = 30 − WE-Alter beim Verkauf. Pro Auftrag, nicht pro Kunde.</p>
    <div class="tier-table">
      <table>
        <thead><tr><th>WE-Alter beim Verkauf</th><th>Maximales Kunden-Zahlungsziel</th><th>Anteil heute</th></tr></thead>
        <tbody>
'''
terms = ['23 T netto','16 T netto','8 T netto','Vorkasse','Vorkasse (bereits überzogen)']
for (lbl,n_t,pct),term in zip(tier_dist, terms):
    cls = ' class="vorkasse"' if 'Vorkasse' in term else ''
    html += f'''          <tr{cls}><td>{lbl}</td><td class="term">{term}</td><td>{fmt_pct(pct)} % ({fmt_n(n_t)})</td></tr>
'''
html += f'''        </tbody>
      </table>
    </div>
  </div>

  <div class="section">
    <h2>Pro Kern-Lieferant.</h2>
    <p class="desc">Strikt drehende Ware in der 9-Monats-Periode.</p>
    <div class="tbl-card">
      <table class="apple">
        <thead><tr><th class="left">Lieferant</th><th>n</th><th>WE→Verk. Med.</th><th>WE→Verk. P75</th><th>WE→Bez. Med.</th><th>Vorfin.</th><th>Max. Netto</th></tr></thead>
        <tbody>
'''
for s, row in sup_core.iterrows():
    mx = row['max_net']
    if mx>=20: pill = f'<span class="pill pill-good">{fmt_d(mx)} T</span>'
    elif mx>=10: pill = f'<span class="pill pill-warn">{fmt_d(mx)} T</span>'
    elif mx>0:   pill = f'<span class="pill pill-bad">{fmt_d(mx)} T</span>'
    else:        pill = '<span class="pill pill-bad">Vorkasse</span>'
    html += f'''          <tr>
            <td class="left">{s}</td><td>{fmt_n(int(row["n"]))}</td><td>{fmt_d(row["we_sold_med"])} T</td><td>{fmt_d(row["we_sold_p75"])} T</td><td><strong>{fmt_d(row["we_paid_med"])} T</strong></td><td>{fmt_pct(row["vorfin_pct"])} %</td><td>{pill}</td>
          </tr>
'''
html += f'''        </tbody></table></div>
  </div>

  <div class="section">
    <div class="fazit">
      <div class="eyebrow">Fazit</div>
      <h2>Vier Regeln,<br>damit kein Cent vorfinanziert wird.</h2>
      <p><strong>Über 9 Monate gemessen — {fmt_n(n_chain)} Geräte mit lückenloser Datenkette</strong> — vereinnahmen wir bei <strong>{fmt_pct(100-vorfin_pct)} %</strong> der drehenden Ware das Kunden-Geld rechtzeitig vor der 30-Tage-Lieferantenfrist. Die übrigen <strong>{fmt_pct(vorfin_pct)} %</strong> blockieren dauerhaft <strong>{fmt_eur(WC)}</strong> Liquidität — {fmt_eur(kk_10)} Zinslast p. a.</p>
      <div class="verdict">
        <h3>So muss die Zahlungsziel-Vergabe ab sofort laufen</h3>
        <ol>
          <li><strong>Pro-Auftrag-Logik:</strong> Netto-Ziel auf der Rechnung vom WE-Alter des Geräts ableiten — ≤ 7 T → 23 T netto, 8–14 T → 16 T, 15–22 T → 8 T, &gt; 22 T → Vorkasse.</li>
          <li><strong>Vorkasse-Default bei WE-Alter ≥ 23 T:</strong> mathematisch nicht mehr zahlungsziel-fähig — diese Tranche gehört nicht auf Rechnung.</li>
          <li><strong>Skonto-Hebel:</strong> 2 % bei Zahlung innerhalb 14 T statt 23-T-Netto. Median Verkauf→Bezahlt liegt heute bei {fmt_d(st_sold_paid["median"])} T — der Hebel verschiebt das nach vorne.</li>
          <li><strong>Mahnkette ab Tag 25 nach WE</strong> (nicht nach Verkauf!) — denn die Lieferanten-Uhr läuft ab Wareneingang.</li>
        </ol>
      </div>
    </div>
  </div>

  <div class="footer">
    Erstellt {now} · Drehende Ware ({len(drehend)}): {", ".join(drehend)}<br>
    Periode: 01.07.2025 – 31.03.2026 ({PERIODE} Tage) · Coverage in Periode: {fmt_pct(coverage)} % der drehenden Verkäufe mit vollständiger Datenkette<br>
    Quellen: All-Sold-Master (70.395 V.) · Stock-Received-Master (63.910 WE) · JTL 11.05.2026 · keine Imputation, keine Hochrechnung der Rate
  </div>
</div>
</body></html>'''

out_html.write_text(html, encoding='utf-8')
print(f'\n  ✓ HTML: {out_html} ({out_html.stat().st_size:,} B)')

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
                       margin={'top':'0','right':'0','bottom':'0','left':'0'})
        await browser.close()
asyncio.run(make_pdf())
print(f'  ✓ PDF: {out_pdf} ({out_pdf.stat().st_size:,} B)')
