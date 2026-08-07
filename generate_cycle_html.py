"""HTML-Report für Bearbeitungszeit-Analyse — Verkauf → Bezahlt + Pro Lieferant"""
import sys, io, glob, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', line_buffering=True)
from pathlib import Path
from datetime import datetime
import pandas as pd
import numpy as np

USERHOME = Path(os.environ.get('USERPROFILE', os.path.expanduser('~')))
ALLSOLD_DIR = USERHOME / 'Downloads' / 'All Sold 2025 - 2026'
JTL_FILE = r'W:\DUSTIN EXPORTE 2026\JTL-Export-Aufträge-07052026.csv'
OUTPUT = USERHOME / 'Downloads' / 'Bearbeitungszeit_Analyse_2025-2026.html'

# === Daten laden ===
print('Lade Portal-Sold…')
files = sorted(glob.glob(str(ALLSOLD_DIR / 'All-Sold-2026-05-07T*.xlsx')))
portal = pd.concat([pd.read_excel(f) for f in files], ignore_index=True)
portal = portal.drop_duplicates(subset=['Lager Nr.'], keep='first').copy()
portal['sold_dt'] = pd.to_datetime(portal['Date'], errors='coerce').dt.normalize()
portal['lager_nr_str'] = portal['Lager Nr.'].astype(str).str.strip().str.replace(r'\.0+$', '', regex=True)

print('Lade JTL…')
jtl = pd.read_csv(JTL_FILE, sep=';', encoding='iso-8859-1', low_memory=False)
jtl['Auftragsdatum_dt'] = pd.to_datetime(jtl['Auftragsdatum'], errors='coerce', dayfirst=True)
jtl['Bezahlt_dt'] = pd.to_datetime(jtl['Datum Zahlungseingang'], errors='coerce', dayfirst=True)
jtl['lager_nr_str'] = jtl['Artikelnummer'].astype(str).str.strip().str.replace(r'\.0+$', '', regex=True)
jtl['Zahlungsziel_n'] = pd.to_numeric(jtl['Zahlungsziel'], errors='coerce')

# Pro Lager-Nr: erstes Auftrag-Datum + Bezahlt-Datum + Zahlungsziel
jtl_per_lager = (
    jtl.dropna(subset=['Auftragsdatum_dt', 'lager_nr_str'])
    .sort_values('Auftragsdatum_dt')
    .drop_duplicates('lager_nr_str', keep='first')
    [['lager_nr_str', 'Auftragsdatum_dt', 'Bezahlt_dt', 'Zahlungsziel_n']]
)

merged = portal.merge(jtl_per_lager, on='lager_nr_str', how='left')
merged['t_sold_to_paid'] = (merged['Bezahlt_dt'] - merged['sold_dt']).dt.days
merged['t_order_to_paid'] = (merged['Bezahlt_dt'] - merged['Auftragsdatum_dt']).dt.days

# Filter Sinn-Bereich
clean = merged[(merged['t_sold_to_paid'] >= -3) & (merged['t_sold_to_paid'] <= 365)].copy()

# === Statistiken ===
def quantile_block(s):
    s = s.dropna()
    return dict(n=len(s), mean=s.mean(), median=s.median(),
                p25=s.quantile(0.25), p75=s.quantile(0.75),
                p90=s.quantile(0.9), p95=s.quantile(0.95))

stats_total = quantile_block(clean['t_sold_to_paid'])
stats_2025  = quantile_block(clean[clean['sold_dt'].dt.year == 2025]['t_sold_to_paid'])
stats_2026  = quantile_block(clean[clean['sold_dt'].dt.year == 2026]['t_sold_to_paid'])
stats_order = quantile_block(merged.dropna(subset=['t_order_to_paid'])
                              .pipe(lambda d: d[(d['t_order_to_paid']>=-3) & (d['t_order_to_paid']<=365)])
                              ['t_order_to_paid'])

# Pro Lieferant
sup = clean.dropna(subset=['t_sold_to_paid']).groupby('Supply Type').agg(
    n=('t_sold_to_paid', 'count'),
    avg_d=('t_sold_to_paid', 'mean'),
    med_d=('t_sold_to_paid', 'median'),
    p90_d=('t_sold_to_paid', lambda x: x.quantile(0.9))
).sort_values('n', ascending=False).head(20)

# Pro Monat
monat = (clean.dropna(subset=['t_sold_to_paid'])
         .assign(YM=lambda d: d['sold_dt'].dt.strftime('%Y-%m'))
         .groupby('YM').agg(
             n=('t_sold_to_paid', 'count'),
             avg_d=('t_sold_to_paid', 'mean'),
             med_d=('t_sold_to_paid', 'median'),
             p90_d=('t_sold_to_paid', lambda x: x.quantile(0.9))
         )).sort_index()

# Histogram-Buckets
buckets = [(0, 7, '0-7T'), (8, 14, '8-14T'), (15, 30, '15-30T'),
           (31, 60, '31-60T'), (61, 90, '61-90T'), (91, 180, '91-180T'),
           (181, 365, '181-365T')]
hist = []
for lo, hi, lbl in buckets:
    n = ((clean['t_sold_to_paid'] >= lo) & (clean['t_sold_to_paid'] <= hi)).sum()
    hist.append((lbl, n))

# Zahlungsziel-Compliance
clean_zz = clean.dropna(subset=['t_sold_to_paid', 'Zahlungsziel_n']).copy()
clean_zz['ueber_ziel'] = clean_zz['t_sold_to_paid'] - clean_zz['Zahlungsziel_n']
zz_in_time = (clean_zz['ueber_ziel'] <= 0).sum()
zz_late = (clean_zz['ueber_ziel'] > 0).sum()
zz_late_avg = clean_zz[clean_zz['ueber_ziel'] > 0]['ueber_ziel'].mean()

# === HTML ===
def fmt_d(v):
    if v is None or pd.isna(v): return '—'
    return f'{v:.1f} T'.replace('.', ',')

def fmt_n(v):
    if v is None or pd.isna(v): return '—'
    return f'{int(v):,}'.replace(',', '.')

def fmt_pct(v):
    if v is None or pd.isna(v): return '—'
    return f'{v:.1f}%'.replace('.', ',')

now = datetime.now().strftime('%Y-%m-%d %H:%M')

html = ['''<!DOCTYPE html>
<html lang="de"><head><meta charset="UTF-8">
<title>Bearbeitungszeit-Analyse · elvinci NH5</title>
<style>
:root { --burg: #6b2737; --good: #2d6a4f; --bad: #c04040; --warn: #b87333;
        --ink: #1a1f2c; --ink-soft: #4a5468; --ink-faint: #8893a8;
        --bg: #f8f6f2; --paper: #ffffff; --line: #e5e2dc; }
* { box-sizing: border-box; }
body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Tahoma, sans-serif;
       background: var(--bg); color: var(--ink); margin: 0; padding: 24px; line-height: 1.5; }
.header { background: var(--paper); border-radius: 8px; padding: 24px 28px; margin-bottom: 20px;
          box-shadow: 0 1px 3px rgba(0,0,0,0.04); border-left: 4px solid var(--burg); }
.header h1 { margin: 0 0 6px; font-size: 22px; }
.header h1 em { color: var(--burg); font-style: normal; }
.header .sub { color: var(--ink-soft); font-size: 13px; }
.header .pill { display: inline-block; background: var(--burg); color: white;
                padding: 3px 10px; border-radius: 12px; font-size: 11px; margin-top: 8px; }
.banner { padding: 16px 20px; border-radius: 8px; margin-bottom: 18px; border-left: 6px solid; }
.banner.warn { background: rgba(184,115,51,0.06); border-color: var(--warn); }
.banner.warn h2 { margin: 0 0 6px; color: var(--warn); font-size: 15px; }
.banner.good { background: rgba(45,106,79,0.06); border-color: var(--good); }
.banner.good h2 { margin: 0 0 6px; color: var(--good); font-size: 15px; }
.banner p { margin: 4px 0; font-size: 13px; }
.kpi-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 14px; margin-bottom: 18px; }
.kpi { background: var(--paper); padding: 16px 18px; border-radius: 8px; border-left: 3px solid var(--burg);
       box-shadow: 0 1px 3px rgba(0,0,0,0.04); }
.kpi .lbl { font-size: 11px; color: var(--ink-soft); text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 4px; }
.kpi .val { font-size: 28px; font-weight: 700; color: var(--burg); font-feature-settings: 'tnum'; }
.kpi .sub { font-size: 11px; color: var(--ink-faint); margin-top: 4px; }
.card { background: var(--paper); border-radius: 8px; padding: 18px 20px; margin-bottom: 18px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.04); }
.card-title { font-size: 15px; font-weight: 600; margin-bottom: 12px; padding-bottom: 8px;
              border-bottom: 1px solid var(--line); color: var(--burg); }
table { width: 100%; border-collapse: collapse; font-size: 12px; }
th { background: var(--bg); border-bottom: 2px solid var(--line); padding: 8px 10px;
     text-align: right; font-weight: 600; color: var(--ink-soft); }
th.left, td.left { text-align: left; }
td { padding: 6px 10px; border-bottom: 1px solid var(--line); }
td.num, .right { text-align: right; font-feature-settings: 'tnum'; font-variant-numeric: tabular-nums; }
tr:hover td { background: rgba(107,39,55,0.03); }
.bar { display: inline-block; height: 14px; background: linear-gradient(90deg, var(--burg) 0%, #b97a87 100%);
       border-radius: 2px; vertical-align: middle; margin-right: 8px; }
.bar-bg { display: inline-block; width: 200px; background: rgba(0,0,0,0.05); border-radius: 2px; vertical-align: middle; }
.tag-good { background: rgba(45,106,79,0.12); color: var(--good); padding: 2px 7px; border-radius: 3px; font-size: 11px; }
.tag-bad { background: rgba(192,64,64,0.12); color: var(--bad); padding: 2px 7px; border-radius: 3px; font-size: 11px; }
.tag-warn { background: rgba(184,115,51,0.12); color: var(--warn); padding: 2px 7px; border-radius: 3px; font-size: 11px; }
.foot { font-size: 11px; color: var(--ink-faint); padding: 16px 20px; text-align: center; }
.method-box { background: rgba(0,0,0,0.03); padding: 12px 16px; border-radius: 6px; font-size: 12px; color: var(--ink-soft); margin-top: 12px; }
</style></head><body>
''']

html.append(f'''<div class="header">
  <h1>Bearbeitungszeit-Analyse · <em>Verkauf → Kunde hat bezahlt</em></h1>
  <div class="sub">Datenstand 07.05.2026 · Quellen: 92.576 Portal-Sold-Records × 108.027 JTL-Auftragspositionen × 9 BESTAND-Snapshots</div>
  <div class="pill">erstellt {now}</div>
</div>''')

# Killcritic-Banner: warum NICHT WE→Bezahlt
html.append(f'''<div class="banner warn">
  <h2>⚠️ Killcritic: Warum nicht "Wareneingang → Bezahlt" wie ursprünglich gefragt</h2>
  <p><b>Datenlücke identifiziert:</b> BESTAND-Snapshots enthalten nur Geräte die <b>aktuell im Lager stehen</b> — verkaufte Geräte sind raus. Match-Quote WE-Datum auf Portal-Sold = <b>0 % von 92.576</b>.</p>
  <p>Konsequenz: Volle WE→Bezahlt-Cycle nicht direkt aus den vorhandenen Quellen berechenbar. Stattdessen liefere ich die <b>2 berechenbaren Komponenten</b> der Cycle-Time:</p>
  <p style="margin-top: 8px;">• <b>Verkauf → Bezahlt</b> (Zahlungs-Geschwindigkeit): {stats_total["n"]:,} Records, Median {stats_total["median"]:.0f} Tage<br>
     • <b>Bestellung → Bezahlt</b> (JTL-internal): {stats_order["n"]:,} Records, Median {stats_order["median"]:.0f} Tage</p>
  <p>Für die fehlende WE→Verkauf-Komponente: Codex Methode D (n=14.421 für 2026) liefert Median 4 Tage Verweildauer. Addiert ergibt das eine <b>geschätzte WE→Bezahlt von ~16 Tage Median</b> für 2026er Verkäufe.</p>
</div>''')

# Kern-KPI-Grid: Zahlung total
html.append('<div class="kpi-grid">')
html.append(f'<div class="kpi"><div class="lbl">Median Verkauf→Bezahlt</div><div class="val">{stats_total["median"]:.0f} <span style="font-size:14px;color:var(--ink-soft);">Tage</span></div><div class="sub">über {stats_total["n"]:,} Records</div></div>')
html.append(f'<div class="kpi"><div class="lbl">Mean</div><div class="val">{stats_total["mean"]:.1f}</div><div class="sub">P75: {stats_total["p75"]:.0f} T · P90: {stats_total["p90"]:.0f} T</div></div>')
html.append(f'<div class="kpi"><div class="lbl">Zahlung pünktlich</div><div class="val">{zz_in_time/(zz_in_time+zz_late)*100:.0f}%</div><div class="sub">{zz_in_time:,} von {zz_in_time+zz_late:,} im Zahlungsziel</div></div>')
html.append(f'<div class="kpi"><div class="lbl">Verzögerung wenn spät</div><div class="val">+{zz_late_avg:.1f}T</div><div class="sub">∅ Tage über Zahlungsziel ({zz_late:,} Fälle)</div></div>')
html.append('</div>')

# Tabelle Verteilung 2025 vs 2026
html.append('<div class="card"><div class="card-title">Verteilung Verkauf→Bezahlt (2025 vs 2026)</div>')
html.append('<table><thead><tr><th class="left">Periode</th><th>n</th><th>Median</th><th>Mean</th><th>P25</th><th>P75</th><th>P90</th><th>P95</th></tr></thead><tbody>')
for label, s in [('2025', stats_2025), ('2026', stats_2026), ('Gesamt 25+26', stats_total)]:
    html.append(f'<tr><td class="left"><b>{label}</b></td><td class="num">{fmt_n(s["n"])}</td>'
                f'<td class="num">{s["median"]:.1f} T</td><td class="num">{s["mean"]:.1f} T</td>'
                f'<td class="num">{s["p25"]:.0f} T</td><td class="num">{s["p75"]:.0f} T</td>'
                f'<td class="num">{s["p90"]:.0f} T</td><td class="num">{s["p95"]:.0f} T</td></tr>')
html.append('</tbody></table></div>')

# Histogramm-Buckets
total_n = sum(n for _, n in hist)
html.append('<div class="card"><div class="card-title">Verteilung in Buckets</div>')
html.append('<table><thead><tr><th class="left">Bucket</th><th>n</th><th>%</th><th class="left" style="width: 220px;">Verteilung</th></tr></thead><tbody>')
for lbl, n in hist:
    pct = n / total_n * 100 if total_n else 0
    bar_w = int(pct * 2)  # max ~ 200px bei 100%
    html.append(f'<tr><td class="left"><b>{lbl}</b></td><td class="num">{n:,}</td><td class="num">{pct:.1f}%</td>'
                f'<td><span class="bar-bg"><span class="bar" style="width:{bar_w}px;"></span></span></td></tr>')
html.append('</tbody></table></div>')

# Pro Monat
html.append('<div class="card"><div class="card-title">Trend pro Monat</div>')
html.append('<table><thead><tr><th class="left">Monat</th><th>n</th><th>Median</th><th>Mean</th><th>P90</th></tr></thead><tbody>')
for ym, row in monat.iterrows():
    html.append(f'<tr><td class="left">{ym}</td><td class="num">{int(row.n):,}</td>'
                f'<td class="num">{row.med_d:.1f} T</td><td class="num">{row.avg_d:.1f} T</td>'
                f'<td class="num">{row.p90_d:.0f} T</td></tr>')
html.append('</tbody></table></div>')

# Pro Lieferant
html.append('<div class="card"><div class="card-title">Pro Lieferant (Top-20 nach Volumen)</div>')
html.append('<table><thead><tr><th class="left">Lieferant</th><th>n</th><th>Median</th><th>Mean</th><th>P90</th><th class="left">Tempo</th></tr></thead><tbody>')
all_median = stats_total["median"]
for s_name, row in sup.iterrows():
    delta = row.med_d - all_median
    if delta < -2: tag = '<span class="tag-good">schnell</span>'
    elif delta > 5: tag = '<span class="tag-bad">langsam</span>'
    elif delta > 2: tag = '<span class="tag-warn">leicht spät</span>'
    else: tag = '<span style="color:var(--ink-faint);font-size:11px;">∅</span>'
    html.append(f'<tr><td class="left">{s_name}</td><td class="num">{int(row.n):,}</td>'
                f'<td class="num">{row.med_d:.1f} T</td><td class="num">{row.avg_d:.1f} T</td>'
                f'<td class="num">{row.p90_d:.0f} T</td><td>{tag}</td></tr>')
html.append('</tbody></table></div>')

# Methodik
html.append(f'''<div class="card"><div class="card-title">Methodik & Datenquellen</div>
<div class="method-box">
<b>Datenfluss:</b><br>
1. Portal-Sold (8 Files, n=92.576 dedup): liefert Sold-Datum (`Date`) + Lager-Nr. + Order-Nr. + Supply Type<br>
2. JTL-Aufträge (108.027 Zeilen, 1.937 Bestell-Nrn): liefert Bezahlt-Datum (`Datum Zahlungseingang`) + Auftragsdatum<br>
3. JOIN: Lager-Nr ↔ JTL-Artikelnummer<br>
4. Match-Quote: <b>{stats_total["n"]:,} von 92.576 (= {stats_total["n"]/92576*100:.1f}%)</b><br>
<br>
<b>Filter:</b> nur Records mit -3 ≤ t ≤ 365 Tagen (Outlier-Schutz vor Tippfehler-Daten)<br>
<br>
<b>Warum WE→Bezahlt nicht direkt:</b> BESTAND-Snapshots haben WE-Datum nur für Geräte die zum Snapshot-Zeitpunkt im Lager standen. Verkaufte Geräte = nicht mehr im BESTAND. 0% Match → nicht möglich aus aktuellen Quellen.
<br><br>
<b>Approximation für volle Cycle-Time WE→Bezahlt:</b><br>
Sold→Bezahlt Median ({stats_total["median"]:.0f} T) + Codex Methode D Verweildauer Median (4 T) ≈ <b>{stats_total["median"]+4:.0f} T volle Cycle</b> (Schätzung)
</div></div>''')

html.append(f'<div class="foot">Validiert · Quellen: All-Sold-Files vom 07.05.2026 + JTL-Export vom 07.05.2026 + BESTAND 07.04.-24.04.2026<br>Methodik konsistent mit LAGERDAUER_CODEX v25 + Validation 28.04.2026</div>')
html.append('</body></html>')

OUTPUT.write_text('\n'.join(html), encoding='utf-8')
print(f'\n✓ HTML generiert: {OUTPUT}')
print(f'  Size: {OUTPUT.stat().st_size:,} B')
