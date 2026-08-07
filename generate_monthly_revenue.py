"""
Monatliche Gegenüberstellung: Rechnungsstellung vs. Zahlungseingang
Als Apple-Style PDF.
"""
import sys, io, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', line_buffering=True)
from pathlib import Path
from datetime import datetime
import pandas as pd

USERHOME = Path(os.environ.get('USERPROFILE', os.path.expanduser('~')))
ALL_SOLD = USERHOME / 'Downloads' / 'All-Sold-Apr2025-Apr2026.xlsx'
JTL_FILE = r'W:\DUSTIN EXPORTE 2026\JTL-Export-Aufträge-11052026.csv'

print('Lade Daten…')
sold = pd.read_excel(ALL_SOLD, sheet_name='All Sold')
sold['Invoice_dt']  = pd.to_datetime(sold['Invoice Date'], errors='coerce').dt.normalize()
sold['lager_nr_str']= sold['Lager Nr.'].astype(str).str.strip().str.replace(r'\.0+$', '', regex=True)
sold['VK'] = pd.to_numeric(sold['JTL Selling Price'], errors='coerce')
sold['EK'] = pd.to_numeric(sold['Portal Buying Price'], errors='coerce')
sold['Profit_v'] = pd.to_numeric(sold['Profit'], errors='coerce')

jtl = pd.read_csv(JTL_FILE, sep=';', encoding='iso-8859-1', low_memory=False)
jtl['Artikelnummer'] = jtl['Artikelnummer'].astype(str).str.strip().str.replace(r'\.0+$', '', regex=True)
jtl['Bezahlt_dt'] = pd.to_datetime(jtl['Datum Zahlungseingang'], errors='coerce', dayfirst=True).dt.normalize()
jtl_min = jtl[['Artikelnummer','Bezahlt_dt']].dropna(subset=['Artikelnummer']).drop_duplicates('Artikelnummer')
jtl_min.columns = ['lager_nr_str','Bezahlt_dt']

# Join
df = sold.merge(jtl_min, on='lager_nr_str', how='left')
df = df.dropna(subset=['Invoice_dt'])
df['Invoice_M'] = df['Invoice_dt'].dt.to_period('M')
df['Bezahlt_M'] = df['Bezahlt_dt'].dt.to_period('M')

print(f'  Verkäufe gesamt:       {len(df):,}')
print(f'  Mit Rechnungsdatum:    {df["Invoice_dt"].notna().sum():,}')
print(f'  Mit Zahlungsdatum:     {df["Bezahlt_dt"].notna().sum():,}')
print(f'  Rechnungsdatum-Range:  {df["Invoice_dt"].min().date()} – {df["Invoice_dt"].max().date()}')
print(f'  Zahlungsdatum-Range:   {df["Bezahlt_dt"].min().date()} – {df["Bezahlt_dt"].max().date()}')

# Monatliche Aggregation
rech = df.groupby('Invoice_M').agg(
    n_rech=('VK', 'count'),
    sum_rech=('VK', 'sum'),
    sum_ek=('EK', 'sum'),
    sum_profit=('Profit_v', 'sum'),
).reset_index().rename(columns={'Invoice_M':'Monat'})

cash = df.dropna(subset=['Bezahlt_dt']).groupby('Bezahlt_M').agg(
    n_cash=('VK', 'count'),
    sum_cash=('VK', 'sum'),
).reset_index().rename(columns={'Bezahlt_M':'Monat'})

monthly = rech.merge(cash, on='Monat', how='outer').fillna(0).sort_values('Monat')
monthly['delta'] = monthly['sum_rech'] - monthly['sum_cash']
monthly['cum_delta'] = monthly['delta'].cumsum()
monthly['Monat_str'] = monthly['Monat'].astype(str)

# Filter auf Periode mit Daten in beiden Spalten
PERIOD_START = pd.Period('2025-04','M')
PERIOD_END   = pd.Period('2026-04','M')   # April 2026 zeigt Cash-Eingänge für Mär-Rechnungen
monthly_main = monthly[(monthly['Monat']>=PERIOD_START) & (monthly['Monat']<=PERIOD_END)].copy()

print(f'\nMonatsverlauf:')
for _, r in monthly_main.iterrows():
    print(f'  {r["Monat_str"]}  Rechn: {int(r["n_rech"]):>5,} = {r["sum_rech"]:>10,.0f} €  ·  Cash: {int(r["n_cash"]):>5,} = {r["sum_cash"]:>10,.0f} €  ·  Δ {r["delta"]:>+10,.0f} €')

total_rech = monthly_main['sum_rech'].sum()
total_cash = monthly_main['sum_cash'].sum()
total_profit = monthly_main['sum_profit'].sum()
total_ek = monthly_main['sum_ek'].sum()
delta_total = total_rech - total_cash
print(f'\nGesamt Apr 2025 – Apr 2026:')
print(f'  Rechnungs-Umsatz: {total_rech:,.0f} €')
print(f'  Cash-Eingang:     {total_cash:,.0f} €')
print(f'  Δ (offene Forder. ggü. Periodenstart): {delta_total:+,.0f} €')
print(f'  Brutto-Marge:     {total_profit:,.0f} €')

# === PDF ===
now = datetime.now().strftime('%d.%m.%Y · %H:%M')
out_html = USERHOME / 'Downloads' / 'Umsatz_vs_Cash_2025-2026.html'
out_pdf  = USERHOME / 'Downloads' / 'Umsatz_vs_Cash_2025-2026.pdf'

def fmt_eur(v):
    if pd.isna(v) or v==0: return '0 €'
    s = f'{int(round(v)):,}'.replace(',', '.')
    return f'{s} €'
def fmt_eur_sign(v):
    if pd.isna(v) or v==0: return '0 €'
    s = f'{int(round(abs(v))):,}'.replace(',', '.')
    return ('+' if v>0 else '−') + f'{s} €'
def fmt_n(v): return f'{int(v):,}'.replace(',', '.')

max_val = max(monthly_main['sum_rech'].max(), monthly_main['sum_cash'].max())

html = f'''<!DOCTYPE html>
<html lang="de"><head>
<meta charset="UTF-8">
<title>Umsatz vs. Cash 2025/26</title>
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
body {{ font-family: -apple-system, BlinkMacSystemFont, "SF Pro Display", "SF Pro Text", sans-serif;
  background: var(--grey-bg); color: var(--black); font-size: 13px; line-height: 1.45;
  letter-spacing: -0.022em; }}
.page {{ max-width: 800px; margin: 0 auto; padding: 48px 56px; background: var(--grey-bg); }}
header {{ margin-bottom: 40px; padding-bottom: 24px; border-bottom: 1px solid var(--grey-3); }}
header .eyebrow {{ font-size: 12px; font-weight: 600; color: var(--blue); text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 10px; }}
header h1 {{ font-size: 38px; font-weight: 700; letter-spacing: -0.04em; line-height: 1.1; margin-bottom: 12px; }}
header h1 em {{ font-style: normal; color: var(--blue); }}
header .lead {{ font-size: 16px; color: var(--grey-1); max-width: 600px; }}
header .meta {{ margin-top: 16px; font-size: 11px; color: var(--grey-2); }}

.kpi-strip {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; margin-bottom: 36px; }}
.kpi {{ background: var(--paper); border-radius: 12px; padding: 18px 18px; box-shadow: var(--shadow); }}
.kpi .lbl {{ font-size: 10px; font-weight: 600; color: var(--grey-1); text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 6px; }}
.kpi .val {{ font-size: 22px; font-weight: 700; letter-spacing: -0.02em; font-variant-numeric: tabular-nums; }}
.kpi .val.green {{ color: var(--green); }} .kpi .val.blue {{ color: var(--blue); }} .kpi .val.red {{ color: var(--red); }} .kpi .val.orange {{ color: var(--orange); }}
.kpi .sub {{ font-size: 11px; color: var(--grey-2); margin-top: 3px; }}

.section {{ margin-bottom: 36px; }}
.section h2 {{ font-size: 22px; font-weight: 600; letter-spacing: -0.02em; margin-bottom: 6px; }}
.section .desc {{ font-size: 13px; color: var(--grey-1); margin-bottom: 18px; max-width: 600px; }}

/* Bar-Chart */
.chart {{ background: var(--paper); border-radius: 14px; padding: 24px 24px; box-shadow: var(--shadow); }}
.chart-legend {{ display: flex; gap: 18px; margin-bottom: 18px; font-size: 12px; }}
.legend-item {{ display: flex; align-items: center; gap: 6px; }}
.legend-dot {{ width: 12px; height: 12px; border-radius: 3px; }}
.month-row {{ display: grid; grid-template-columns: 80px 1fr 90px 90px 90px; gap: 12px; align-items: center; padding: 8px 0; border-bottom: 1px solid #f0f0f3; font-variant-numeric: tabular-nums; }}
.month-row:last-child {{ border-bottom: none; }}
.month-label {{ font-size: 12px; font-weight: 600; }}
.month-bars {{ display: flex; flex-direction: column; gap: 4px; }}
.bar-wrap {{ display: flex; align-items: center; gap: 6px; height: 14px; }}
.bar-label {{ font-size: 10px; width: 26px; color: var(--grey-2); }}
.bar-track {{ flex: 1; height: 14px; background: var(--grey-bg); border-radius: 3px; position: relative; overflow: hidden; }}
.bar-fill {{ height: 100%; border-radius: 3px; }}
.bar-rech {{ background: linear-gradient(90deg, var(--blue) 0%, #5ac8fa 100%); }}
.bar-cash {{ background: linear-gradient(90deg, var(--green) 0%, #4cd964 100%); }}
.month-val {{ text-align: right; font-size: 12px; font-weight: 600; }}
.month-delta {{ text-align: right; font-size: 11px; font-weight: 500; }}
.month-delta.pos {{ color: var(--red); }} .month-delta.neg {{ color: var(--green); }}

/* Tabelle */
.tbl-card {{ background: var(--paper); border-radius: 14px; box-shadow: var(--shadow); padding: 4px 0; overflow: hidden; }}
table {{ width: 100%; border-collapse: collapse; font-size: 12px; font-variant-numeric: tabular-nums; }}
th {{ font-size: 10px; text-transform: uppercase; letter-spacing: 0.4px; color: var(--grey-1); font-weight: 600;
     padding: 11px 14px; text-align: right; border-bottom: 1px solid var(--grey-3); }}
th.left, td.left {{ text-align: left; }}
td {{ padding: 9px 14px; border-bottom: 1px solid #f0f0f3; }}
tr:last-child td {{ border-bottom: none; }}
tr.totals td {{ border-top: 2px solid var(--grey-3); font-weight: 700; background: var(--grey-bg); }}

.insight {{ background: linear-gradient(135deg, #1d1d1f 0%, #2d2d30 100%); color: white;
  border-radius: 14px; padding: 26px 28px; box-shadow: var(--shadow); }}
.insight .eyebrow {{ font-size: 11px; font-weight: 700; color: #5ac8fa; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 10px; }}
.insight h3 {{ font-size: 20px; font-weight: 700; margin-bottom: 12px; }}
.insight p {{ font-size: 13px; line-height: 1.6; color: rgba(255,255,255,0.9); margin-bottom: 10px; }}
.insight p strong {{ color: white; }}
.insight .hi {{ color: #5ac8fa; font-weight: 600; }}
.insight ul {{ margin: 6px 0 0 18px; }}
.insight li {{ font-size: 12.5px; margin-bottom: 6px; color: rgba(255,255,255,0.88); }}

footer {{ margin-top: 32px; padding-top: 18px; border-top: 1px solid var(--grey-3); font-size: 10px; color: var(--grey-2); text-align: center; line-height: 1.5; }}

@media print {{
  body {{ background: white; }}
  .page {{ background: white; padding: 28px 36px; max-width: none; }}
  .kpi, .chart, .tbl-card, .insight {{ box-shadow: none; border: 1px solid var(--grey-3); }}
  .section, .insight {{ page-break-inside: avoid; }}
  .month-row {{ page-break-inside: avoid; }}
  tr {{ page-break-inside: avoid; }}
}}
</style>
</head><body>
<div class="page">

<header>
  <div class="eyebrow">Cash Flow vs. Umsatz · {monthly_main['Monat_str'].min()} – {monthly_main['Monat_str'].max()}</div>
  <h1>Umsatz und <em>Zahlungseingang</em><br>im Monatsvergleich.</h1>
  <p class="lead">Monatliche Gegenüberstellung: was wurde in Rechnung gestellt — was kam tatsächlich rein. Differenz zeigt den Aufbau oder Abbau offener Forderungen pro Monat.</p>
  <div class="meta">Stand {now} · Datenbasis All-Sold-Master + JTL 11.05.2026 · Netto-Umsatz (JTL Selling Price)</div>
</header>

<div class="kpi-strip">
  <div class="kpi"><div class="lbl">Rechnungs-Umsatz</div><div class="val blue">{fmt_eur(total_rech)}</div><div class="sub">{fmt_n(monthly_main["n_rech"].sum())} Geräte fakturiert</div></div>
  <div class="kpi"><div class="lbl">Zahlungseingang</div><div class="val green">{fmt_eur(total_cash)}</div><div class="sub">{fmt_n(monthly_main["n_cash"].sum())} Geräte bezahlt</div></div>
  <div class="kpi"><div class="lbl">Δ Offene Forderung</div><div class="val {"red" if delta_total>0 else "green"}">{fmt_eur_sign(delta_total)}</div><div class="sub">{"Forderungs-Aufbau" if delta_total>0 else "Forderungs-Abbau"}</div></div>
  <div class="kpi"><div class="lbl">Brutto-Marge gesamt</div><div class="val orange">{fmt_eur(total_profit)}</div><div class="sub">{(total_profit/total_rech*100 if total_rech else 0):.1f} % vom Umsatz</div></div>
</div>

<div class="section">
  <h2>Monats-Bars im Vergleich.</h2>
  <p class="desc">Blau = Rechnungsstellung (Umsatz), Grün = Zahlungseingang (Cash). Die Δ-Spalte rechts zeigt, ob in diesem Monat mehr offene Forderungen entstanden als eingingen (rot) oder umgekehrt (grün).</p>
  <div class="chart">
    <div class="chart-legend">
      <div class="legend-item"><div class="legend-dot bar-rech"></div>Rechnungs-Umsatz (Monat)</div>
      <div class="legend-item"><div class="legend-dot bar-cash"></div>Zahlungseingang (Monat)</div>
    </div>
'''

for _, r in monthly_main.iterrows():
    rech_w = (r['sum_rech']/max_val*100) if max_val else 0
    cash_w = (r['sum_cash']/max_val*100) if max_val else 0
    delta = r['delta']
    delta_cls = 'pos' if delta>0 else 'neg'
    html += f'''    <div class="month-row">
      <div class="month-label">{r["Monat_str"]}</div>
      <div class="month-bars">
        <div class="bar-wrap"><span class="bar-label">R</span><div class="bar-track"><div class="bar-fill bar-rech" style="width:{rech_w:.1f}%;"></div></div></div>
        <div class="bar-wrap"><span class="bar-label">C</span><div class="bar-track"><div class="bar-fill bar-cash" style="width:{cash_w:.1f}%;"></div></div></div>
      </div>
      <div class="month-val" style="color: var(--blue);">{fmt_eur(r["sum_rech"])}</div>
      <div class="month-val" style="color: var(--green);">{fmt_eur(r["sum_cash"])}</div>
      <div class="month-delta {delta_cls}">{fmt_eur_sign(delta)}</div>
    </div>
'''

html += f'''  </div>
</div>

<div class="section">
  <h2>Detail-Tabelle.</h2>
  <p class="desc">Monats-Daten im Detail — inklusive kumulierter Forderungsentwicklung.</p>
  <div class="tbl-card">
    <table>
      <thead><tr>
        <th class="left">Monat</th>
        <th>Geräte (R)</th>
        <th>Rechnungs-Umsatz</th>
        <th>Geräte (Z)</th>
        <th>Zahlungseingang</th>
        <th>Δ Monat</th>
        <th>Δ Kumuliert</th>
      </tr></thead>
      <tbody>
'''
for _, r in monthly_main.iterrows():
    delta = r['delta']
    cum = r['cum_delta']
    html += f'''        <tr>
          <td class="left">{r["Monat_str"]}</td>
          <td>{fmt_n(r["n_rech"])}</td>
          <td>{fmt_eur(r["sum_rech"])}</td>
          <td>{fmt_n(r["n_cash"])}</td>
          <td>{fmt_eur(r["sum_cash"])}</td>
          <td style="color:{"var(--red)" if delta>0 else "var(--green)"}">{fmt_eur_sign(delta)}</td>
          <td style="color:{"var(--red)" if cum>0 else "var(--green)"}">{fmt_eur_sign(cum)}</td>
        </tr>
'''
html += f'''        <tr class="totals">
          <td class="left">Σ Gesamt</td>
          <td>{fmt_n(monthly_main["n_rech"].sum())}</td>
          <td>{fmt_eur(total_rech)}</td>
          <td>{fmt_n(monthly_main["n_cash"].sum())}</td>
          <td>{fmt_eur(total_cash)}</td>
          <td style="color:{"var(--red)" if delta_total>0 else "var(--green)"}">{fmt_eur_sign(delta_total)}</td>
          <td>—</td>
        </tr>
      </tbody>
    </table>
  </div>
</div>

<div class="section">
  <div class="insight">
    <div class="eyebrow">Fazit</div>
    <h3>Was sagen die Zahlen?</h3>
    <p>Über die 13 Monate (Apr 2025 – Apr 2026) wurden <span class="hi">{fmt_eur(total_rech)}</span> in Rechnung gestellt und <span class="hi">{fmt_eur(total_cash)}</span> als Zahlungseingang verbucht. Differenz: <strong>{fmt_eur_sign(delta_total)}</strong> — das entspricht dem Aufbau bzw. Abbau des offenen Forderungsbestands über den Zeitraum.</p>
    <p>Brutto-Marge gesamt: <strong>{fmt_eur(total_profit)}</strong> ({(total_profit/total_rech*100 if total_rech else 0):.1f} % vom Umsatz). EK-Volumen Lieferanten gesamt: <strong>{fmt_eur(total_ek)}</strong>.</p>
    <p><strong>Interpretation der Δ-Spalte:</strong></p>
    <ul>
      <li><span style="color:#ff6b5b;">Rot (Δ &gt; 0)</span> — in diesem Monat mehr fakturiert als bezahlt → Forderungsbestand wächst → Cash-Engpass-Risiko.</li>
      <li><span style="color:#4cd964;">Grün (Δ &lt; 0)</span> — Cash-Eingang höher als Neufakturierung → Forderungsbestand schmilzt → entspannte Liquiditätslage.</li>
      <li><strong>Kumulativ:</strong> zeigt den aufgelaufenen Effekt vom Periodenstart bis zum jeweiligen Monat. Ein Bilanz-ähnliches Forderungsdelta.</li>
    </ul>
  </div>
</div>

<footer>
  Erstellt {now} · Quellen: All-Sold-Master (Rechnungsdaten + VK) · JTL-Export 11.05.2026 (Zahlungseingänge)<br>
  Periode: {monthly_main['Monat_str'].min()} – {monthly_main['Monat_str'].max()} · Netto-Umsatz (JTL Selling Price) ohne USt.
</footer>

</div>
</body></html>
'''

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
