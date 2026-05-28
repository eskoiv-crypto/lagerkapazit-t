"""
Apple-Like Bearbeitungszeit-Analyse — NUR 2026
WE → Bezahlt mit 30-Tage-Lieferanten-Zahlungsziel & Fazit
"""
import sys, io, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', line_buffering=True)
from pathlib import Path
from datetime import datetime
import pandas as pd

USERHOME = Path(os.environ.get('USERPROFILE', os.path.expanduser('~')))
DETAIL_CSV = USERHOME / 'Downloads' / 'we_to_paid_full.csv'

print('  Lade Detail-CSV…')
m = pd.read_csv(DETAIL_CSV, sep=';', encoding='utf-8-sig', low_memory=False)
m['sold_dt'] = pd.to_datetime(m['sold_dt'])
m['we_dt'] = pd.to_datetime(m['we_dt'])
m['Bezahlt_dt'] = pd.to_datetime(m['Bezahlt_dt'])

# === FILTER: nur 2026, plausible Werte ===
clean = m[(m['t_we_to_paid'] >= -3) & (m['t_we_to_paid'] <= 1500)
          & (m['sold_dt'].dt.year == 2026)].copy()
total_2026 = (m['sold_dt'].dt.year == 2026).sum()
n_full = len(clean)

# === ZAHLUNGSZIEL-KONSTANTE ===
SUPPLIER_DEADLINE = 30  # Tage Zahlungsziel an OTTO/AEG/etc.

def stats(s):
    s = s.dropna()
    if len(s) == 0: return None
    return dict(n=len(s), mean=s.mean(), median=s.median(),
                p25=s.quantile(0.25), p75=s.quantile(0.75),
                p90=s.quantile(0.9))

st_full     = stats(clean['t_we_to_paid'])
st_we_sold  = stats(clean['t_we_to_sold'])
st_sold_paid= stats(clean['t_sold_to_paid'])

# === ZAHLUNGSZIEL-ANALYSE ===
within = (clean['t_we_to_paid'] <= SUPPLIER_DEADLINE).sum()
within_pct = within / n_full * 100
over = n_full - within
over_pct = 100 - within_pct
# Cash-Gap: Tage über 30 für die kritischen Fälle
gap = clean[clean['t_we_to_paid'] > SUPPLIER_DEADLINE]['t_we_to_paid'] - SUPPLIER_DEADLINE
gap_median = gap.median() if len(gap) > 0 else 0
gap_p90 = gap.quantile(0.9) if len(gap) > 0 else 0

# === PRO LIEFERANT (2026) — mit 30T-Ampel ===
sup = (clean.groupby('Supply Type').agg(
    n=('t_we_to_paid', 'count'),
    med_d=('t_we_to_paid', 'median'),
    avg_d=('t_we_to_paid', 'mean'),
    p90_d=('t_we_to_paid', lambda x: x.quantile(0.9)),
    we_sold=('t_we_to_sold', 'median'),
    sold_paid=('t_sold_to_paid', 'median'),
).sort_values('n', ascending=False).head(12))
sup['within_30'] = clean.groupby('Supply Type').apply(
    lambda g: (g['t_we_to_paid'] <= SUPPLIER_DEADLINE).mean() * 100
).reindex(sup.index)

# === BUCKETS um 30T-Schwelle ===
buckets = [
    (0, 7, '≤ 7 Tage', 'good'),
    (8, 14, '8–14 Tage', 'good'),
    (15, 30, '15–30 Tage', 'good'),
    (31, 60, '31–60 Tage', 'warn'),
    (61, 90, '61–90 Tage', 'bad'),
    (91, 180, '91–180 Tage', 'bad'),
    (181, 1500, '> 180 Tage', 'bad'),
]
hist = [(lbl, ((clean['t_we_to_paid'] >= lo) & (clean['t_we_to_paid'] <= hi)).sum(), tag)
        for lo, hi, lbl, tag in buckets]

# === KUNDEN-ZAHLUNGSZIEL-PUFFER ===
# WE → Verkauf = Lager-Verweildauer (vor Verkauf bereits Zeit verbrannt)
# Verkauf → Bezahlt = aktuelles Kunden-Zahlungsverhalten
# Maximal-Puffer für Kunden = 30T - Median(WE→Sold)
buffer_median = SUPPLIER_DEADLINE - st_we_sold['median']
buffer_p25 = SUPPLIER_DEADLINE - clean['t_we_to_sold'].quantile(0.25)
buffer_p75 = SUPPLIER_DEADLINE - clean['t_we_to_sold'].quantile(0.75)
current_customer = st_sold_paid['median']

now = datetime.now().strftime('%d.%m.%Y · %H:%M')
out_html = USERHOME / 'Downloads' / 'Bearbeitungszeit_2026.html'
out_pdf  = USERHOME / 'Downloads' / 'Bearbeitungszeit_2026.pdf'

def fmt_d(v): return f'{v:.0f}'.replace('.', ',') if v == round(v) else f'{v:.1f}'.replace('.', ',')
def fmt_n(v): return f'{int(v):,}'.replace(',', '.')
def fmt_pct(v): return f'{v:.1f}'.replace('.', ',')

html = f'''<!DOCTYPE html>
<html lang="de"><head>
<meta charset="UTF-8">
<title>Bearbeitungszeit 2026 · WE → Bezahlt</title>
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

.hero {{ margin-bottom: 56px; padding-bottom: 28px; border-bottom: 1px solid var(--grey-3); }}
.hero .eyebrow {{ font-size: 13px; font-weight: 600; color: var(--blue); text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 12px; }}
.hero h1 {{ font-size: 44px; font-weight: 700; letter-spacing: -0.04em; line-height: 1.1; margin-bottom: 14px; }}
.hero h1 em {{ font-style: normal; color: var(--blue); }}
.hero .lead {{ font-size: 18px; color: var(--grey-1); line-height: 1.4; max-width: 600px; }}
.hero .meta {{ margin-top: 20px; font-size: 12px; color: var(--grey-2); display: flex; gap: 20px; flex-wrap: wrap; }}
.hero .meta span::before {{ content: ''; display: inline-block; width: 4px; height: 4px; background: var(--grey-3); border-radius: 50%; vertical-align: middle; margin-right: 8px; }}
.hero .meta span:first-child::before {{ display: none; }}

.highlight {{ background: var(--paper); border-radius: 18px; padding: 44px 40px; margin-bottom: 44px; box-shadow: var(--shadow); text-align: center; }}
.highlight .big {{ font-size: 96px; font-weight: 700; line-height: 1; letter-spacing: -0.05em; color: var(--blue); font-variant-numeric: tabular-nums; }}
.highlight .big .unit {{ font-size: 38px; color: var(--grey-1); font-weight: 500; margin-left: 8px; }}
.highlight .label {{ font-size: 17px; color: var(--grey-1); margin-top: 12px; font-weight: 500; }}
.highlight .sub {{ font-size: 13px; color: var(--grey-2); margin-top: 14px; }}

.section {{ margin-bottom: 48px; }}
.section h2 {{ font-size: 26px; font-weight: 600; letter-spacing: -0.025em; margin-bottom: 8px; }}
.section .desc {{ font-size: 14px; color: var(--grey-1); margin-bottom: 22px; max-width: 600px; }}

.kpi-grid {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 14px; }}
.kpi-card {{ background: var(--paper); border-radius: 14px; padding: 22px 20px; box-shadow: var(--shadow); }}
.kpi-card .kpi-lbl {{ font-size: 11px; color: var(--grey-1); text-transform: uppercase; letter-spacing: 0.6px; font-weight: 600; margin-bottom: 8px; }}
.kpi-card .kpi-val {{ font-size: 36px; font-weight: 700; letter-spacing: -0.03em; font-variant-numeric: tabular-nums; }}
.kpi-card .kpi-val .u {{ font-size: 15px; color: var(--grey-1); font-weight: 500; }}
.kpi-card .kpi-sub {{ font-size: 12px; color: var(--grey-2); margin-top: 4px; }}

/* Zahlungsziel-30T-Karte */
.deadline {{ background: var(--paper); border-radius: 18px; padding: 36px 36px; box-shadow: var(--shadow); display: grid; grid-template-columns: 1fr 1fr; gap: 32px; align-items: center; }}
.deadline .left .num {{ font-size: 72px; font-weight: 700; letter-spacing: -0.04em; line-height: 1; font-variant-numeric: tabular-nums; }}
.deadline .left .num.good {{ color: var(--green); }}
.deadline .left .num.bad {{ color: var(--red); }}
.deadline .left .lbl {{ font-size: 14px; color: var(--grey-1); margin-top: 8px; }}
.deadline .right p {{ font-size: 14px; color: var(--black); line-height: 1.55; }}
.deadline .right p + p {{ margin-top: 10px; }}
.deadline .right strong {{ font-weight: 600; }}
.deadline .scale {{ grid-column: 1/3; height: 14px; background: linear-gradient(90deg, var(--green) 0%, var(--green) {within_pct:.0f}%, var(--red) {within_pct:.0f}%, var(--red) 100%); border-radius: 7px; margin-top: 8px; position: relative; }}
.deadline .scale::after {{ content: '30 Tage Zahlungsziel'; position: absolute; left: {within_pct:.0f}%; top: -22px; transform: translateX(-50%); font-size: 11px; color: var(--grey-1); white-space: nowrap; }}
.deadline .scale-lbl {{ grid-column: 1/3; display: flex; justify-content: space-between; font-size: 11px; color: var(--grey-2); margin-top: 6px; }}

.dist {{ background: var(--paper); border-radius: 14px; padding: 24px 22px; box-shadow: var(--shadow); }}
.dist-row {{ display: flex; align-items: center; padding: 9px 0; border-bottom: 1px solid var(--grey-3); }}
.dist-row:last-child {{ border-bottom: none; }}
.dist-lbl {{ flex: 0 0 110px; font-size: 13px; font-weight: 500; }}
.dist-bar {{ flex: 1; height: 22px; background: var(--grey-bg); border-radius: 4px; overflow: hidden; margin: 0 14px; }}
.dist-bar-fill {{ height: 100%; border-radius: 4px; }}
.dist-bar-fill.good {{ background: linear-gradient(90deg, var(--green) 0%, #4cd964 100%); }}
.dist-bar-fill.warn {{ background: linear-gradient(90deg, var(--orange) 0%, #ffcc00 100%); }}
.dist-bar-fill.bad {{ background: linear-gradient(90deg, var(--red) 0%, #ff6b5b 100%); }}
.dist-n {{ font-size: 12px; font-weight: 600; min-width: 60px; text-align: right; font-variant-numeric: tabular-nums; }}
.dist-pct {{ font-size: 11px; color: var(--grey-2); min-width: 50px; text-align: right; font-variant-numeric: tabular-nums; }}
.dist-divider {{ border-top: 2px dashed var(--grey-3) !important; padding-top: 11px !important; margin-top: 4px; position: relative; }}
.dist-divider::before {{ content: '── 30-Tage-Lieferanten-Deadline ──'; position: absolute; top: -8px; left: 50%; transform: translateX(-50%); background: var(--paper); padding: 0 12px; font-size: 10px; color: var(--orange); font-weight: 600; letter-spacing: 0.5px; }}

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
.pill-neutral {{ background: var(--grey-bg); color: var(--grey-1); }}

.fazit {{ background: linear-gradient(135deg, #1d1d1f 0%, #2d2d30 100%); color: white; border-radius: 18px; padding: 40px 40px; box-shadow: var(--shadow); }}
.fazit .eyebrow {{ font-size: 13px; font-weight: 600; color: #5ac8fa; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 14px; }}
.fazit h2 {{ font-size: 30px; font-weight: 700; letter-spacing: -0.03em; margin-bottom: 22px; color: white; }}
.fazit p {{ font-size: 15px; line-height: 1.6; color: rgba(255,255,255,0.9); margin-bottom: 14px; }}
.fazit p strong {{ color: white; font-weight: 600; }}
.fazit .verdict {{ background: rgba(255,255,255,0.08); border-radius: 12px; padding: 22px 24px; margin-top: 22px; border-left: 4px solid #5ac8fa; }}
.fazit .verdict h3 {{ font-size: 17px; font-weight: 600; margin-bottom: 10px; color: white; }}
.fazit .verdict ul {{ margin: 8px 0 0 18px; }}
.fazit .verdict li {{ font-size: 14px; line-height: 1.55; margin-bottom: 6px; color: rgba(255,255,255,0.85); }}
.fazit .verdict li strong {{ color: #5ac8fa; }}

.footer {{ margin-top: 48px; padding-top: 20px; border-top: 1px solid var(--grey-3); font-size: 11px; color: var(--grey-2); text-align: center; }}

@media print {{
  body {{ background: white; }}
  .page {{ background: white; padding: 32px 40px; max-width: none; }}
  .highlight, .deadline, .dist, .tbl-card, .kpi-card, .fazit {{ box-shadow: none; }}
  .kpi-card, .deadline, .dist, .tbl-card {{ border: 1px solid var(--grey-3); }}
  .section {{ page-break-inside: avoid; }}
  .fazit {{ page-break-inside: avoid; }}
  table.apple tr {{ page-break-inside: avoid; }}
}}
</style>
</head><body>
<div class="page">

  <div class="hero">
    <div class="eyebrow">Bearbeitungszeit-Analyse · 2026</div>
    <h1>Vom Wareneingang<br>zum <em>Zahlungseingang.</em></h1>
    <p class="lead">Cycle-Time-Auswertung Januar–Mai 2026 mit Abgleich gegen das 30-Tage-Lieferanten-Zahlungsziel (OTTO, AEG &amp; Co.) — und welche Konsequenz das für unsere Kunden-Zahlungsziele hat.</p>
    <div class="meta">
      <span>Stand {now}</span>
      <span>{fmt_n(total_2026)} Verkäufe 2026</span>
      <span>{fmt_n(n_full)} mit voller Datenkette</span>
    </div>
  </div>

  <div class="highlight">
    <div class="big">{fmt_d(st_full["median"])}<span class="unit">Tage</span></div>
    <div class="label">Median Wareneingang → Zahlungseingang</div>
    <div class="sub">Mean {fmt_d(st_full["mean"])} T · P90 {fmt_d(st_full["p90"])} T · n = {fmt_n(st_full["n"])}</div>
  </div>

  <div class="section">
    <h2>Drei Stationen.</h2>
    <p class="desc">Aus welchen Komponenten setzt sich die Cycle-Time zusammen?</p>
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
        <div class="kpi-lbl">WE → Bezahlt (gesamt)</div>
        <div class="kpi-val" style="color: var(--blue);">{fmt_d(st_full["median"])}<span class="u"> T</span></div>
        <div class="kpi-sub">Volle Cycle · P90 {fmt_d(st_full["p90"])} T</div>
      </div>
    </div>
  </div>

  <div class="section">
    <h2>30-Tage-Zahlungsziel.</h2>
    <p class="desc">OTTO, AEG &amp; Co. erwarten Zahlung innerhalb von 30 Tagen ab Wareneingang. Schaffen wir es, das Kunden-Geld vorher zu kassieren?</p>
    <div class="deadline">
      <div class="left">
        <div class="num good">{fmt_pct(within_pct)} %</div>
        <div class="lbl">Geräte mit Bezahlung <strong>innerhalb 30 Tagen</strong> ({fmt_n(within)} von {fmt_n(n_full)})</div>
      </div>
      <div class="right">
        <p><strong>{fmt_pct(over_pct)} % der Geräte</strong> ({fmt_n(over)}) werden erst <strong>nach</strong> dem 30-Tage-Limit bezahlt.</p>
        <p>In diesen Fällen entsteht eine Cash-Lücke von typischerweise <strong>+{fmt_d(gap_median)} Tagen</strong> (Median; P90: +{fmt_d(gap_p90)} T) — wir müssen den Lieferanten <strong>vorfinanzieren</strong>.</p>
      </div>
      <div class="scale"></div>
      <div class="scale-lbl"><span>0 T</span><span>schnell genug</span><span style="color: var(--red);">zu spät</span><span>P90: {fmt_d(st_full["p90"])} T</span></div>
    </div>
  </div>

  <div class="section">
    <h2>Verteilung um die 30-Tage-Schwelle.</h2>
    <p class="desc">Wo genau liegen die {fmt_n(n_full)} Fälle? Buckets oberhalb 30 T sind kritisch (Vorfinanzierung).</p>
    <div class="dist">
'''
total_hist = sum(n for _, n, _ in hist)
max_n = max(n for _, n, _ in hist)
for i, (lbl, n, tag) in enumerate(hist):
    pct = n / total_hist * 100 if total_hist else 0
    bar_w = (n / max_n * 100) if max_n else 0
    divider_class = ' dist-divider' if i == 3 else ''  # vor Bucket 31-60 die Trennlinie
    html += f'''      <div class="dist-row{divider_class}">
        <div class="dist-lbl">{lbl}</div>
        <div class="dist-bar"><div class="dist-bar-fill {tag}" style="width: {bar_w:.1f}%;"></div></div>
        <div class="dist-n">{fmt_n(n)}</div>
        <div class="dist-pct">{fmt_pct(pct)} %</div>
      </div>
'''
html += f'''    </div>
  </div>

  <div class="section">
    <h2>Pro Lieferant.</h2>
    <p class="desc">Top-12 Lieferanten 2026 — der Anteil „≤ 30 T bezahlt" zeigt, bei welcher Quelle die Vorfinanzierung droht.</p>
    <div class="tbl-card">
      <table class="apple">
        <thead>
          <tr>
            <th class="left">Lieferant</th>
            <th>n</th>
            <th>WE→Verk.</th>
            <th>Verk.→Bez.</th>
            <th>WE→Bez. (Med.)</th>
            <th>≤ 30 T</th>
            <th>Bewertung</th>
          </tr>
        </thead>
        <tbody>
'''
for s_name, row in sup.iterrows():
    w30 = row['within_30']
    if w30 >= 70:   pill = '<span class="pill pill-good">solide</span>'
    elif w30 >= 50: pill = '<span class="pill pill-warn">grenzwertig</span>'
    elif w30 >= 30: pill = '<span class="pill pill-bad">kritisch</span>'
    else:           pill = '<span class="pill pill-bad">Vorfinanzierung</span>'
    html += f'''          <tr>
            <td class="left">{s_name}</td>
            <td>{fmt_n(int(row["n"]))}</td>
            <td>{fmt_d(row["we_sold"])} T</td>
            <td>{fmt_d(row["sold_paid"])} T</td>
            <td><strong>{fmt_d(row["med_d"])} T</strong></td>
            <td>{fmt_pct(w30)} %</td>
            <td>{pill}</td>
          </tr>
'''

# === FAZIT-LOGIK ===
# Verfügbarer Puffer = 30 - Median(WE→Sold)
# Aktuelles Kunden-Zahlungsverhalten = Median(Sold→Paid)
buffer_safe = max(0, SUPPLIER_DEADLINE - st_we_sold['median'])
recommend_target = max(7, int(buffer_safe))   # Ziel-Zahlungsziel an Kunden
current_avg_paid = st_sold_paid['median']
diff_to_target = current_avg_paid - buffer_safe

if buffer_safe >= current_avg_paid:
    fazit_color = 'good'
    fazit_short = f'Wir haben Spielraum: Kunden zahlen im Median nach {fmt_d(current_avg_paid)} T — der Puffer bis zur 30-T-Lieferanten-Deadline beträgt {fmt_d(buffer_safe)} T.'
else:
    fazit_color = 'tight'
    fazit_short = f'Der Puffer ist eng: Nach Verkauf bleiben uns nur {fmt_d(buffer_safe)} T bis zur Lieferanten-Deadline, Kunden zahlen aber im Median erst nach {fmt_d(current_avg_paid)} T.'

html += f'''        </tbody>
      </table>
    </div>
  </div>

  <!-- FAZIT -->
  <div class="section">
    <div class="fazit">
      <div class="eyebrow">Fazit · Empfehlung</div>
      <h2>Was bedeutet das für<br>unsere Kunden-Zahlungsziele?</h2>

      <p><strong>Die Mathematik:</strong> Vom Wareneingang bis zum Verkauf vergehen im Median <strong>{fmt_d(st_we_sold["median"])} Tage</strong> Lager-Liegezeit. Bis zur 30-T-Lieferanten-Deadline bleiben uns danach noch <strong>{fmt_d(buffer_safe)} Tage</strong>, in denen der Kunde sein Geld an uns überwiesen haben muss — sonst gehen wir in Vorfinanzierung.</p>

      <p><strong>Heute:</strong> Kunden zahlen aktuell im Median nach <strong>{fmt_d(current_avg_paid)} Tagen</strong> nach Verkauf. {fmt_pct(within_pct)} % aller Geräte sind innerhalb 30 T bezahlt — {fmt_pct(over_pct)} % erfordern Vorfinanzierung mit einer Cash-Lücke von Median +{fmt_d(gap_median)} T (P90: +{fmt_d(gap_p90)} T).</p>

      <p><strong>Das Stellgrad-Problem:</strong> Die Lager-Verweildauer können wir kaum steuern (Marktnachfrage, Klassifizierung, Listing). Stellgröße bleibt das <strong>Kunden-Zahlungsziel</strong>.</p>

      <div class="verdict">
        <h3>Empfehlung für die Zahlungsziel-Vergabe an Kunden</h3>
        <ul>
          <li><strong>Maximum {fmt_d(buffer_safe)} Tage netto</strong> — alles darüber hinaus erzeugt strukturelle Vorfinanzierung gegenüber OTTO/AEG-Lieferanten</li>
          <li><strong>Default {recommend_target} Tage netto</strong> für Standard-B2B-Kunden — gibt Sicherheits-Puffer für Verzögerungen im Verkaufsprozess (Picking, Versand, Rechnung)</li>
          <li><strong>Vorkasse / Sofortzahlung</strong> bei Lieferanten mit hoher Lager-Verweildauer (z. B. Long-Tail-Quellen mit WE→Verk. &gt; 30 T) — sonst ist die Deadline schon vor Verkauf gerissen</li>
          <li><strong>Skonto-Anreiz {recommend_target - 7}-T-Frist</strong> (2 % Skonto bei Zahlung innerhalb {recommend_target - 7} T) — schiebt Median näher an heutige {fmt_d(current_avg_paid)} T und erhöht den 30-T-Anteil von {fmt_pct(within_pct)} % Richtung 80 %+</li>
          <li><strong>Mahnkette bei Tag 25 nach Verkauf</strong> aktivieren — damit der 30-T-Anteil nicht weiter Richtung kritischen 60-T-Bucket abrutscht ({fmt_pct(sum(n for lbl,n,_ in hist[3:5])/total_hist*100)} % aller Fälle aktuell)</li>
        </ul>
      </div>
    </div>
  </div>

  <div class="footer">
    Erstellt {now} · 2026er Geschäft · Quellen: Portal-Sold, Stock-Analysis, WP-Pipeline, BESTAND, JTL · Outlier-Filter [-3, 1500] T
  </div>
</div>
</body></html>
'''

out_html.write_text(html, encoding='utf-8')
print(f'  ✓ HTML: {out_html} ({out_html.stat().st_size:,} B)')

print('\n  Konvertiere zu PDF via Playwright headless…')
import asyncio
async def make_pdf():
    from playwright.async_api import async_playwright
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        await page.goto(f'file:///{str(out_html).replace(chr(92), "/")}')
        await page.emulate_media(media='print')
        await page.pdf(
            path=str(out_pdf), format='A4', print_background=True,
            margin={'top': '0', 'right': '0', 'bottom': '0', 'left': '0'},
        )
        await browser.close()
asyncio.run(make_pdf())
print(f'  ✓ PDF: {out_pdf} ({out_pdf.stat().st_size:,} B)')

# Kurz-Echo der Kern-Zahlen
print(f'''
  ─── KERN-ZAHLEN 2026 ───────────────────────────
  WE → Bezahlt Median:    {fmt_d(st_full["median"])} T  (Mean {fmt_d(st_full["mean"])} T, P90 {fmt_d(st_full["p90"])} T)
  WE → Verkauf Median:    {fmt_d(st_we_sold["median"])} T
  Verkauf → Bezahlt Med.: {fmt_d(st_sold_paid["median"])} T
  ≤ 30 T bezahlt:         {fmt_pct(within_pct)} %  ({fmt_n(within)}/{fmt_n(n_full)})
  Cash-Lücke wenn >30 T:  +{fmt_d(gap_median)} T (Median), +{fmt_d(gap_p90)} T (P90)
  Empfohlenes Kunden-Zahlungsziel: max. {fmt_d(buffer_safe)} T netto, Default {recommend_target} T
  ─────────────────────────────────────────────────
''')
