"""
Interaktives HTML-Dashboard für Schuldner-Bearbeitung
Filter: Kunde / Produkt / Lieferant / Datum
"""
import sys, io, os, json
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', line_buffering=True)
from pathlib import Path
from datetime import datetime
import pandas as pd

USERHOME = Path(os.environ.get('USERPROFILE', os.path.expanduser('~')))
MASTER_CSV = USERHOME / 'Downloads' / 'we_to_paid_MASTER.csv'
ALL_SOLD   = USERHOME / 'Downloads' / 'All-Sold-Apr2025-Apr2026.xlsx'
JTL_FILE   = r'W:\DUSTIN EXPORTE 2026\JTL-Export-Aufträge-11052026.csv'

# === Lade Daten ===
m = pd.read_csv(MASTER_CSV, sep=';', encoding='utf-8-sig', low_memory=False)
m['sold_dt']    = pd.to_datetime(m['sold_dt'])
m['we_dt']      = pd.to_datetime(m['we_dt'])
m['Bezahlt_dt'] = pd.to_datetime(m['Bezahlt_dt'])
m['Portal Buying Price'] = pd.to_numeric(m['Portal Buying Price'], errors='coerce')
m['JTL Selling Price']   = pd.to_numeric(m['JTL Selling Price'], errors='coerce')

# Drehende Lieferanten = Hauptlieferanten (Default-Markierung)
DREHEND = ['OTTO_MIX','AEG_Schrott','OTTO_Hanseatic','AEG_IT','Gorenje_Mix',
           'OTTO_B_Ware','OTTO_Lagerschäden_Ansbach','OTTO_Jura','Samsung PEDC']
# Hinweis: Ohrdruf-Klassifizierung benötigt Stammdaten-Pflege beim Vereinzeln —
# kein Workaround im Dashboard (siehe Hilfe-Panel)
m['lager_nr_str'] = m['lager_nr_str'].astype(str)
# MAX-PERIODE: All-Sold-Master deckt Apr 2025 – Mär 2026 ab (= 12 Monate)
START = pd.Timestamp('2025-04-01')
END   = pd.Timestamp('2026-03-31')

# NEU: ALLE Lieferanten einbeziehen (statt nur drehende) — Filter im Dashboard
core = m[(m['sold_dt']>=START) & (m['sold_dt']<=END)
       & m['we_dt'].notna() & m['Bezahlt_dt'].notna()
       & (m['t_we_to_paid']>=-3) & (m['t_we_to_paid']<=1500)].copy()
print(f'\n  Core (alle Lieferanten in Periode): {len(core):,}')

ueb = core[core['t_we_to_paid']>30].copy()
ueb['vorfin_days'] = ueb['t_we_to_paid'] - 30
ueb['eur_days']    = ueb['Portal Buying Price'].fillna(0) * ueb['vorfin_days']

# === Kundennamen + Produkt-Info + Supply + Rechnungsdatum aus All-Sold ===
sold = pd.read_excel(ALL_SOLD, sheet_name='All Sold')
sold['lager_nr_str'] = sold['Lager Nr.'].astype(str).str.strip().str.replace(r'\.0+$', '', regex=True)
sold['Invoice_dt'] = pd.to_datetime(sold['Invoice Date'], errors='coerce').dt.normalize()
sold_min = sold[['lager_nr_str','Company','Brand','Product Group','Article','Order Nr.','Invoice Number','Final Grade','Supply','Invoice_dt']].drop_duplicates('lager_nr_str')

ueb['lager_nr_str'] = ueb['lager_nr_str'].astype(str)
ueb = ueb.merge(sold_min, on='lager_nr_str', how='left')

# === JTL: Zahlungsziel + Auftragsdatum pro Lager-Nr (robust mit Fallback) ===
JTL_FALLBACK = USERHOME / 'Downloads' / 'JTL-Export-Aufträge-11052026.csv'
print('\n  Lade JTL für Zahlungsziel + Auftragsdatum…')
jtl_path = None
for path in [JTL_FILE, str(JTL_FALLBACK)]:
    if Path(path).exists():
        jtl_path = path
        break
if jtl_path:
    print(f'    Quelle: {jtl_path}')
    jtl = pd.read_csv(jtl_path, sep=';', encoding='iso-8859-1', low_memory=False)
    jtl['Artikelnummer'] = jtl['Artikelnummer'].astype(str).str.strip().str.replace(r'\.0+$', '', regex=True)
    jtl['Zahlungsziel'] = pd.to_numeric(jtl['Zahlungsziel'], errors='coerce')
    jtl['Auftrag_dt_jtl'] = pd.to_datetime(jtl['Auftragsdatum'], errors='coerce', dayfirst=True).dt.normalize()
    jtl_min = jtl[['Artikelnummer','Zahlungsziel','Auftrag_dt_jtl']].dropna(subset=['Artikelnummer']).drop_duplicates('Artikelnummer')
    jtl_min.columns = ['lager_nr_str','payment_term','Auftrag_dt_jtl']
    ueb = ueb.merge(jtl_min, on='lager_nr_str', how='left')
else:
    print('    ⚠ JTL-Datei nicht zugänglich (W: getrennt) — Zahlungsziel/Auftragsdatum werden auf NaN gesetzt')
    ueb['payment_term'] = pd.NA
    ueb['Auftrag_dt_jtl'] = pd.NaT

# === Volle Pipeline-Kette berechnen ===
ueb['t_invoice_to_paid'] = (ueb['Bezahlt_dt'] - ueb['Invoice_dt']).dt.days
# Soll-Zahlungsdatum = Rechnungsdatum + vereinbartes Zahlungsziel
ueb['target_paid_dt'] = ueb['Invoice_dt'] + pd.to_timedelta(ueb['payment_term'].fillna(0), unit='D')
# Überschreitung = Bezahlt − Soll-Zahlungsdatum (positive = zu spät, negative = pünktlich/früh)
ueb['target_delay'] = (ueb['Bezahlt_dt'] - ueb['target_paid_dt']).dt.days

n_with_term = ueb['payment_term'].notna().sum()
print(f'  Zahlungsziel verfügbar: {n_with_term:,} / {len(ueb):,} ({n_with_term/len(ueb)*100:.1f}%)')
print(f'  Median Zahlungsziel: {ueb["payment_term"].median()} T  ·  Mean {ueb["payment_term"].mean():.1f} T')
within = (ueb['target_delay']<=0).sum()
overdue = (ueb['target_delay']>0).sum()
print(f'  Zahlungsziel eingehalten: {within:,} ({within/len(ueb)*100:.1f}%)')
print(f'  Zahlungsziel überschritten: {overdue:,} ({overdue/len(ueb)*100:.1f}%)')
print(f'  Ø Überschreitung wenn überzogen: {ueb[ueb["target_delay"]>0]["target_delay"].mean():.1f} T  (Median {ueb[ueb["target_delay"]>0]["target_delay"].median():.0f} T)')

# === Datensatz für JS aufbereiten ===
print(f'  Überzogene Geräte: {len(ueb):,}')
records = []
for _, r in ueb.iterrows():
    records.append({
        'lager': str(r['lager_nr_str']),
        'kunde': str(r.get('Company','—')) if pd.notna(r.get('Company')) else '—',
        'brand': str(r.get('Brand','—')) if pd.notna(r.get('Brand')) else '—',
        'product': str(r.get('Product Group','—')) if pd.notna(r.get('Product Group')) else '—',
        'article': str(r.get('Article','—')) if pd.notna(r.get('Article')) else '—',
        'lieferant': str(r['Supply Type']),
        'sold': r['sold_dt'].strftime('%Y-%m-%d'),
        'we': r['we_dt'].strftime('%Y-%m-%d'),
        'paid': r['Bezahlt_dt'].strftime('%Y-%m-%d'),
        'delay': int(r['vorfin_days']),
        'ek': float(r['Portal Buying Price']) if pd.notna(r['Portal Buying Price']) else 0,
        'eurd': float(r['eur_days']),
        'order': str(r.get('Order Nr.','—')) if pd.notna(r.get('Order Nr.')) else '—',
        'invNr': str(r.get('Invoice Number','—')) if pd.notna(r.get('Invoice Number')) else '—',
        'grade': str(r.get('Final Grade','—')) if pd.notna(r.get('Final Grade')) else '—',
        'supply': str(r.get('Supply','—')) if pd.notna(r.get('Supply')) else '—',
        'lagerD': int(r['t_we_to_sold']) if pd.notna(r['t_we_to_sold']) else 0,        # WE→Verkauf = Lager-Verweildauer
        'customer': int(r['t_sold_to_paid']) if pd.notna(r['t_sold_to_paid']) else 0,  # Verkauf→Bezahlt
        'invoice': int(r['t_invoice_to_paid']) if pd.notna(r['t_invoice_to_paid']) else None,  # Rechnung→Bezahlt
        'invDate': r['Invoice_dt'].strftime('%Y-%m-%d') if pd.notna(r['Invoice_dt']) else '—',
        'cycle': int(r['t_we_to_paid']),                                                # WE→Bezahlt = Gesamt-Cycle
        'payTerm': int(r['payment_term']) if pd.notna(r['payment_term']) else None,    # vereinbartes Zahlungsziel (Tage ab Rechnung)
        'targetDelay': int(r['target_delay']) if pd.notna(r['target_delay']) else None, # Überschreitung des vereinbarten Ziels
    })

PERIODE_TAGE = (core['sold_dt'].max() - core['sold_dt'].min()).days

# Vollständige Lieferanten-Liste aus All-Sold-Master + palette_otto-Hinweis aus Stock-Received
all_supply_in_sold = sorted([s for s in sold['Supply Type'].dropna().unique()])
# palette_otto aus Stock-Received zusätzlich aufnehmen, auch wenn keine Verkäufe matchen
try:
    stock_x = pd.read_excel(USERHOME/'Downloads'/'Stock_Received_April_2025_April_2026.xlsx')
    stock_supply_only = sorted([s for s in stock_x['Supply Type'].dropna().unique() if s not in all_supply_in_sold])
    all_supply_full = all_supply_in_sold + stock_supply_only
except Exception:
    all_supply_full = all_supply_in_sold

# Unique-Werte für Dropdowns
kunden = sorted({r['kunde'] for r in records if r['kunde']!='—'})
# Lieferanten = ALLE bekannten Supply Types (auch wenn 0 überzogene Geräte) — Transparenz
lieferanten = all_supply_full
produkte = sorted({r['product'] for r in records if r['product']!='—'})
brands = sorted({r['brand'] for r in records if r['brand']!='—'})

print(f'  Unique Kunden: {len(kunden)}')
print(f'  Lieferanten im Dropdown (gesamt): {len(lieferanten)}')
print(f'  davon mit überzogenen Geräten: {len({r["lieferant"] for r in records})}')
print(f'  davon drehend (Default-Markierung): {len(DREHEND)}')
print(f'  Unique Produktgruppen: {len(produkte)}')
print(f'  Unique Brands: {len(brands)}')

DATA_JSON = json.dumps(records, ensure_ascii=False)
META_JSON = json.dumps({
    'kunden': kunden,
    'lieferanten': lieferanten,
    'drehend': DREHEND,
    'produkte': produkte,
    'brands': brands,
    'periode_tage': PERIODE_TAGE,
    'total_geraete': len(records),
    'periode_start': '2025-04-01',
    'periode_end': '2026-03-31',
}, ensure_ascii=False)

now = datetime.now().strftime('%d.%m.%Y · %H:%M')

# === HTML ===
out_html = USERHOME / 'Downloads' / 'Schuldner_Dashboard.html'

html = f'''<!DOCTYPE html>
<html lang="de"><head>
<meta charset="UTF-8">
<title>Schuldner-Dashboard · Vorfinanzierung 2025/26</title>
<style>
* {{ box-sizing: border-box; margin: 0; padding: 0; }}
:root {{
  --black: #1d1d1f; --grey-1: #6e6e73; --grey-2: #86868b; --grey-3: #d2d2d7;
  --grey-bg: #f5f5f7; --paper: #ffffff;
  --blue: #0071e3; --blue-dim: rgba(0,113,227,0.08);
  --green: #00a82d; --orange: #ff9500; --red: #ff3b30;
  --shadow: 0 4px 16px rgba(0,0,0,0.04), 0 1px 4px rgba(0,0,0,0.03);
}}
html {{ -webkit-font-smoothing: antialiased; }}
body {{
  font-family: -apple-system, BlinkMacSystemFont, "SF Pro Display", "SF Pro Text", "Helvetica Neue", sans-serif;
  background: var(--grey-bg); color: var(--black); font-size: 14px; line-height: 1.4;
  letter-spacing: -0.022em;
}}
.app {{ max-width: 1600px; margin: 0 auto; padding: 32px 28px; }}

/* Header */
header {{ margin-bottom: 24px; }}
header h1 {{ font-size: 32px; font-weight: 700; letter-spacing: -0.03em; margin-bottom: 6px; }}
header .sub {{ font-size: 13px; color: var(--grey-1); }}

/* KPI Strip */
.kpis {{ display: grid; grid-template-columns: repeat(7, 1fr); gap: 8px; margin-bottom: 22px; }}
.kpi {{ padding: 16px 14px !important; }}
.kpi .lbl {{ font-size: 10px !important; }}
.kpi .val {{ font-size: 24px !important; }}
.kpi .sub {{ font-size: 11px !important; }}
.kpi {{ background: var(--paper); border-radius: 12px; padding: 18px 20px; box-shadow: var(--shadow); }}
.kpi .lbl {{ font-size: 10px; font-weight: 700; color: var(--grey-1); text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 6px; }}
.kpi .val {{ font-size: 28px; font-weight: 700; letter-spacing: -0.02em; font-variant-numeric: tabular-nums; }}
.kpi .val.red {{ color: var(--red); }}
.kpi .val.orange {{ color: var(--orange); }}
.kpi .val.blue {{ color: var(--blue); }}
.kpi .sub {{ font-size: 11px; color: var(--grey-2); margin-top: 2px; }}

/* Filter Bar */
/* Quick-Filter-Buttons */
.quick-filters {{ background: var(--paper); border-radius: 12px; padding: 14px 18px; box-shadow: var(--shadow); margin-bottom: 12px; display: flex; gap: 10px; align-items: center; flex-wrap: wrap; }}
.quick-filters .qf-lbl {{ font-size: 11px; font-weight: 700; color: var(--grey-1); text-transform: uppercase; letter-spacing: 0.5px; margin-right: 8px; }}
.qf-btn {{ padding: 7px 14px; border: 1px solid var(--grey-3); background: white; border-radius: 8px; font-size: 12.5px; font-weight: 500; cursor: pointer; transition: all 0.15s; font-family: inherit; }}
.qf-btn:hover {{ background: var(--grey-bg); border-color: var(--blue); color: var(--blue); }}
.qf-btn.active {{ background: var(--blue); color: white; border-color: var(--blue); font-weight: 600; }}

.filters {{
  background: var(--paper); border-radius: 12px; padding: 16px 18px;
  box-shadow: var(--shadow); margin-bottom: 18px;
  display: grid; grid-template-columns: 1.2fr 1fr 1fr 1fr 1fr 0.8fr 0.8fr 0.8fr auto; gap: 10px; align-items: end;
}}
.filter-grp label {{ display: block; font-size: 10px; font-weight: 700; color: var(--grey-1); text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 4px; }}
.filter-grp input, .filter-grp select {{
  width: 100%; padding: 8px 10px; border: 1px solid var(--grey-3); border-radius: 8px;
  font-size: 13px; font-family: inherit; background: white;
  color: var(--black);
}}
.filter-grp input:focus, .filter-grp select:focus {{ outline: 2px solid var(--blue); outline-offset: -1px; border-color: var(--blue); }}
.btn-reset {{
  padding: 8px 14px; background: var(--grey-bg); border: 1px solid var(--grey-3); border-radius: 8px;
  font-size: 13px; cursor: pointer; color: var(--grey-1); font-weight: 500;
}}
.btn-reset:hover {{ background: white; color: var(--black); }}

/* Profil-Box */
.profile {{
  background: linear-gradient(135deg, #1d1d1f 0%, #2d2d30 100%); color: white;
  border-radius: 14px; padding: 22px 26px; margin-bottom: 18px; box-shadow: var(--shadow);
}}
.profile .eyebrow {{ font-size: 11px; font-weight: 700; color: #5ac8fa; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 8px; }}
.profile .title {{ font-size: 22px; font-weight: 700; letter-spacing: -0.02em; margin-bottom: 12px; }}
.profile .narrative {{ font-size: 14px; line-height: 1.6; color: rgba(255,255,255,0.92); margin-bottom: 14px; }}
.profile .narrative b {{ color: white; font-weight: 600; }}
.profile .narrative .hi {{ color: #5ac8fa; font-weight: 600; }}
.profile .narrative .warn {{ color: #ff9500; font-weight: 600; }}
.profile .narrative .bad {{ color: #ff6b5b; font-weight: 600; }}
.profile .ministats {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin-top: 14px; padding-top: 14px; border-top: 1px solid rgba(255,255,255,0.12); }}
.profile .ministats .item {{ }}
.profile .ministats .item .lbl {{ font-size: 10px; text-transform: uppercase; letter-spacing: 0.5px; color: rgba(255,255,255,0.6); margin-bottom: 4px; }}
.profile .ministats .item .val {{ font-size: 18px; font-weight: 700; font-variant-numeric: tabular-nums; }}
.profile .ministats .item .sub {{ font-size: 11px; color: rgba(255,255,255,0.6); margin-top: 2px; }}
.profile.empty {{ background: var(--paper); color: var(--grey-1); }}
.profile.empty .title {{ color: var(--black); }}
.profile.empty .eyebrow {{ color: var(--blue); }}

/* Top-Schuldner-Strip */
.top-schuldner {{
  background: var(--paper); border-radius: 12px; padding: 16px 18px;
  box-shadow: var(--shadow); margin-bottom: 18px;
}}
.top-schuldner h3 {{ font-size: 12px; font-weight: 700; color: var(--grey-1); text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 10px; }}
.top-schuldner .chips {{ display: flex; gap: 8px; flex-wrap: wrap; }}
.chip {{
  display: inline-flex; align-items: center; gap: 6px; padding: 6px 12px;
  background: var(--grey-bg); border: 1px solid var(--grey-3); border-radius: 18px;
  font-size: 12px; cursor: pointer; transition: all 0.15s;
}}
.chip:hover {{ background: var(--blue-dim); border-color: var(--blue); color: var(--blue); }}
.chip.active {{ background: var(--blue); color: white; border-color: var(--blue); }}
.chip .pct {{ font-weight: 700; }}

/* Tabelle */
.table-wrap {{ background: var(--paper); border-radius: 12px; box-shadow: var(--shadow); overflow: hidden; }}
.table-header {{ display: flex; justify-content: space-between; align-items: center; padding: 14px 20px; border-bottom: 1px solid var(--grey-3); }}
.table-header .info {{ font-size: 12px; color: var(--grey-1); }}
.table-header .info b {{ color: var(--black); font-weight: 600; }}
.table-header .actions {{ display: flex; gap: 8px; align-items: center; }}
.table-header select {{
  padding: 6px 10px; border: 1px solid var(--grey-3); border-radius: 6px;
  font-size: 12px; background: white;
}}
.btn-csv {{
  padding: 6px 12px; background: var(--blue); border: none; border-radius: 6px;
  color: white; font-size: 12px; font-weight: 500; cursor: pointer;
}}
.btn-csv:hover {{ background: #0064cc; }}

table {{ width: 100%; border-collapse: collapse; font-size: 12.5px; }}
table th {{
  position: sticky; top: 0; background: var(--paper); z-index: 1;
  text-align: left; font-weight: 600; color: var(--grey-1);
  font-size: 10px; text-transform: uppercase; letter-spacing: 0.4px;
  padding: 11px 12px; border-bottom: 1px solid var(--grey-3);
  cursor: pointer; user-select: none; white-space: nowrap;
}}
table th.right {{ text-align: right; }}
table th:hover {{ color: var(--black); }}
table th .arrow {{ display: inline-block; font-size: 9px; margin-left: 3px; opacity: 0.4; }}
table th.sorted .arrow {{ opacity: 1; color: var(--blue); }}
table td {{ padding: 9px 12px; border-bottom: 1px solid #f0f0f3; font-variant-numeric: tabular-nums; white-space: nowrap; }}
table td.right {{ text-align: right; }}
table td.bold {{ font-weight: 600; }}
table tr:hover td {{ background: var(--grey-bg); }}
.pill {{ display: inline-block; padding: 2px 8px; border-radius: 12px; font-size: 11px; font-weight: 600; }}
.pill-bad {{ background: rgba(255,59,48,0.12); color: var(--red); }}
.pill-warn {{ background: rgba(255,149,0,0.12); color: var(--orange); }}
.pill-mid {{ background: rgba(0,113,227,0.10); color: var(--blue); }}
.pill-good {{ background: rgba(0,168,45,0.12); color: var(--green); }}

.pagination {{ display: flex; justify-content: space-between; align-items: center; padding: 12px 20px; border-top: 1px solid var(--grey-3); font-size: 12px; }}
.pagination .pages {{ display: flex; gap: 4px; }}
.pagination button {{ padding: 5px 11px; border: 1px solid var(--grey-3); background: white; border-radius: 6px; cursor: pointer; font-size: 12px; }}
.pagination button.active {{ background: var(--blue); color: white; border-color: var(--blue); }}
.pagination button:disabled {{ opacity: 0.4; cursor: not-allowed; }}

footer {{ margin-top: 24px; text-align: center; font-size: 11px; color: var(--grey-2); padding-bottom: 80px; }}

/* Hilfe-Panel */
.help-toggle {{
  position: fixed; bottom: 24px; right: 24px; z-index: 999;
  width: 48px; height: 48px; border-radius: 50%; background: var(--blue); color: white;
  border: none; font-size: 22px; font-weight: 700; cursor: pointer;
  box-shadow: 0 6px 20px rgba(0,113,227,0.4); transition: transform 0.15s;
}}
.help-toggle:hover {{ transform: scale(1.08); }}
.help-overlay {{
  position: fixed; inset: 0; background: rgba(0,0,0,0.4); z-index: 998;
  display: none; opacity: 0; transition: opacity 0.2s;
}}
.help-overlay.open {{ display: block; opacity: 1; }}
.help-panel {{
  position: fixed; top: 5vh; right: 24px; width: min(740px, calc(100vw - 48px));
  max-height: 90vh; background: var(--paper); border-radius: 16px;
  box-shadow: 0 20px 60px rgba(0,0,0,0.25); z-index: 1000;
  display: none; overflow: hidden; flex-direction: column;
}}
.help-panel.open {{ display: flex; }}
.help-header {{
  padding: 22px 28px; border-bottom: 1px solid var(--grey-3);
  display: flex; justify-content: space-between; align-items: center;
  background: linear-gradient(135deg, #1d1d1f 0%, #2d2d30 100%); color: white;
}}
.help-header h2 {{ font-size: 22px; font-weight: 700; letter-spacing: -0.02em; }}
.help-header .close {{
  background: rgba(255,255,255,0.15); border: none; color: white; cursor: pointer;
  width: 32px; height: 32px; border-radius: 50%; font-size: 18px;
}}
.help-content {{ padding: 24px 28px; overflow-y: auto; flex: 1; font-size: 13.5px; line-height: 1.55; }}
.help-content h3 {{
  font-size: 13px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.5px;
  color: var(--blue); margin: 22px 0 10px;
}}
.help-content h3:first-child {{ margin-top: 0; }}
.help-content p {{ margin-bottom: 8px; color: var(--grey-1); }}
.help-content table {{ width: 100%; border-collapse: collapse; margin: 6px 0 14px; font-size: 13px; }}
.help-content th, .help-content td {{ padding: 8px 10px; border-bottom: 1px solid var(--grey-3); text-align: left; vertical-align: top; }}
.help-content th {{ font-weight: 600; color: var(--black); font-size: 11px; text-transform: uppercase; letter-spacing: 0.4px; }}
.help-content td b {{ color: var(--black); }}
.help-content code {{
  background: var(--grey-bg); padding: 1px 6px; border-radius: 4px;
  font-family: "SF Mono", Menlo, monospace; font-size: 12px;
}}
.help-content .formula {{
  background: var(--grey-bg); padding: 14px 18px; border-radius: 8px; margin: 8px 0 12px;
  font-family: "SF Mono", Menlo, monospace; font-size: 12.5px; line-height: 1.7;
  border-left: 3px solid var(--blue);
}}
.help-content .example {{
  background: rgba(0,168,45,0.05); border-radius: 8px; padding: 12px 16px; margin: 8px 0 12px;
  border-left: 3px solid var(--green); font-size: 12.5px;
}}
.help-content .example b {{ color: var(--green); }}
.help-tip {{ display: flex; gap: 10px; align-items: flex-start; margin-bottom: 8px; }}
.help-tip .num {{ width: 20px; height: 20px; border-radius: 50%; background: var(--blue); color: white;
  font-size: 11px; font-weight: 700; display: flex; align-items: center; justify-content: center;
  flex-shrink: 0; margin-top: 2px; }}
.help-pill {{ display: inline-block; padding: 2px 8px; border-radius: 12px; font-size: 11px; font-weight: 600; }}
</style>
</head>
<body>
<div class="app">

<header>
  <h1>Schuldner-Dashboard</h1>
  <div class="sub">Default: 2026 · Hauptlieferanten · Lager ≤ 60 T (aktive Posten ohne Altlasten) — über Schnellfilter umschaltbar</div>
</header>

<div class="kpis">
  <div class="kpi">
    <div class="lbl">Geräte gefiltert</div>
    <div class="val blue" id="kpi-n">—</div>
    <div class="sub" id="kpi-n-sub">von {{TOTAL}} überzogenen</div>
  </div>
  <div class="kpi" title="WE → Bezahlt = Gesamtdauer von Wareneingang bis Geld da">
    <div class="lbl">⌀ WE → Bezahlt</div>
    <div class="val orange" id="kpi-cycle">—</div>
    <div class="sub" id="kpi-cycle-sub">Gesamtdauer ab Wareneingang</div>
  </div>
  <div class="kpi" title="Verkauf → Bezahlt = wie lange brauchte der Kunde nach Verkaufsdatum">
    <div class="lbl">⌀ Verk. → Bez.</div>
    <div class="val red" id="kpi-customer">—</div>
    <div class="sub" id="kpi-customer-sub">ab Verkaufsdatum</div>
  </div>
  <div class="kpi" title="Rechnung → Bezahlt = ECHTE Kunden-DSO ab Rechnungsstellung">
    <div class="lbl">⌀ Rechn. → Bez.</div>
    <div class="val red" id="kpi-invoice">—</div>
    <div class="sub" id="kpi-invoice-sub">ab Rechnungsdatum · DSO</div>
  </div>
  <div class="kpi" title="Überschreitung des vereinbarten Zahlungsziels — die MAHN-relevante Kennzahl">
    <div class="lbl">⌀ Ziel überschritten</div>
    <div class="val red" id="kpi-target">—</div>
    <div class="sub" id="kpi-target-sub">über vereinbartes Zahlungsziel</div>
  </div>
  <div class="kpi" title="Lagerverweildauer = unsere operative Geschwindigkeit">
    <div class="lbl">⌀ Lager-Tage</div>
    <div class="val" id="kpi-lager">—</div>
    <div class="sub" id="kpi-lager-sub">WE → Verkauf</div>
  </div>
  <div class="kpi">
    <div class="lbl">WC-Beitrag</div>
    <div class="val red" id="kpi-wc">—</div>
    <div class="sub" id="kpi-wc-sub">Dauerhaft blockierte Liquidität</div>
  </div>
</div>

<div class="quick-filters">
  <span class="qf-lbl">Schnellfilter</span>
  <button class="qf-btn active" onclick="applyQuickFilter('2026-active', event)">📊 2026 · Hauptlieferanten (Default)</button>
  <button class="qf-btn" onclick="applyQuickFilter('q1-2026', event)">Q1 2026 · Hauptlieferanten</button>
  <button class="qf-btn" onclick="applyQuickFilter('2025-active', event)">2025 · Hauptlieferanten</button>
  <button class="qf-btn" onclick="applyQuickFilter('letzte-30', event)">Letzte 30 Tage · Hauptlieferanten</button>
  <button class="qf-btn" onclick="applyQuickFilter('all-incl-altlast', event)">Alle inkl. Altlasten</button>
  <span style="margin-left: auto; display: flex; align-items: center; gap: 6px; font-size: 12.5px; color: var(--grey-1);">
    <input type="checkbox" id="f-drehend" checked style="width: 14px; height: 14px; cursor: pointer;">
    <label for="f-drehend" style="cursor: pointer;">Nur Hauptlieferanten (drehende Ware)</label>
  </span>
</div>

<div class="filters">
  <div class="filter-grp">
    <label>Kunde (Suche)</label>
    <input type="text" id="f-kunde" placeholder="Tippen zum Filtern…" autocomplete="off">
  </div>
  <div class="filter-grp">
    <label>Lieferant</label>
    <select id="f-lieferant"><option value="">Alle</option></select>
  </div>
  <div class="filter-grp">
    <label>Produktgruppe</label>
    <select id="f-product"><option value="">Alle</option></select>
  </div>
  <div class="filter-grp">
    <label>Brand</label>
    <select id="f-brand"><option value="">Alle</option></select>
  </div>
  <div class="filter-grp">
    <label>Supply-Nr (Suche)</label>
    <input type="text" id="f-supply" placeholder="z. B. 3390022" autocomplete="off">
  </div>
  <div class="filter-grp">
    <label>Verkauf ab</label>
    <input type="date" id="f-date-from" min="2025-04-01" max="2026-03-31">
  </div>
  <div class="filter-grp">
    <label>Verkauf bis</label>
    <input type="date" id="f-date-to" min="2025-04-01" max="2026-03-31">
  </div>
  <div class="filter-grp" title="Geräte ausblenden, deren Lager-Verweildauer (WE→Verkauf) diesen Wert übersteigt. Entfernt Altlast-Restposten, die als drehende Ware fehl-klassifiziert sind.">
    <label>Max Lager (T)</label>
    <input type="number" id="f-maxlager" placeholder="z. B. 60" min="0">
  </div>
  <button class="btn-reset" onclick="resetFilters()">Zurücksetzen</button>
</div>

<div class="profile" id="profile">
  <div class="eyebrow" id="profile-eyebrow">Gesamt-Übersicht</div>
  <div class="title" id="profile-title">Drehende Ware · 9 Monate</div>
  <div class="narrative" id="profile-narrative"></div>
  <div class="ministats" id="profile-ministats"></div>
</div>

<div class="top-schuldner">
  <h3>Top-10 Schuldner — Klick für Filter</h3>
  <div class="chips" id="top-chips"></div>
</div>

<div class="table-wrap">
  <div class="table-header">
    <div class="info">Zeige <b id="show-from">0</b>–<b id="show-to">0</b> von <b id="show-total">0</b> Geräten</div>
    <div class="actions">
      <select id="page-size" onchange="render()">
        <option value="50">50 / Seite</option>
        <option value="100" selected>100 / Seite</option>
        <option value="250">250 / Seite</option>
        <option value="500">500 / Seite</option>
      </select>
      <button class="btn-csv" onclick="exportCSV()">CSV-Export</button>
    </div>
  </div>
  <div style="max-height: 65vh; overflow: auto;">
    <table id="tbl">
      <thead>
        <tr>
          <th data-key="kunde">Kunde<span class="arrow">▾</span></th>
          <th data-key="lager">Lager-Nr<span class="arrow">▾</span></th>
          <th data-key="brand">Brand<span class="arrow">▾</span></th>
          <th data-key="product">Produkt<span class="arrow">▾</span></th>
          <th data-key="lieferant">Lieferant<span class="arrow">▾</span></th>
          <th data-key="sold">Verkauf<span class="arrow">▾</span></th>
          <th data-key="we">WE<span class="arrow">▾</span></th>
          <th data-key="paid">Bezahlt<span class="arrow">▾</span></th>
          <th data-key="lagerD" class="right" title="Lager-Verweildauer = WE → Verkauf (unsere Operations)">Lager (T)<span class="arrow">▾</span></th>
          <th data-key="customer" class="right" title="ab Verkaufsdatum = Verkauf → Bezahlt">Verk→Bez (T)<span class="arrow">▾</span></th>
          <th data-key="invoice" class="right" title="ab Rechnungsdatum = ECHTE Kunden-DSO">Rechn→Bez (T)<span class="arrow">▾</span></th>
          <th data-key="payTerm" class="right" title="Vereinbartes Zahlungsziel ab Rechnungsdatum">Ziel (T)<span class="arrow">▾</span></th>
          <th data-key="targetDelay" class="right" title="Überschreitung des vereinbarten Ziels = MAHN-RELEVANT">Über (T)<span class="arrow">▾</span></th>
          <th data-key="cycle" class="right" title="Gesamt-Cycle = WE → Bezahlt">Cycle (T)<span class="arrow">▾</span></th>
          <th data-key="ek" class="right">EK (€)<span class="arrow">▾</span></th>
          <th data-key="eurd" class="right">€-Tage<span class="arrow">▾</span></th>
          <th data-key="order">Auftrag<span class="arrow">▾</span></th>
        </tr>
      </thead>
      <tbody id="tbl-body"></tbody>
    </table>
  </div>
  <div class="pagination">
    <div>Seite <b id="page-current">1</b> von <b id="page-total">1</b></div>
    <div class="pages" id="pagination"></div>
  </div>
</div>

<footer>
  Erstellt {now} · Daten: All-Sold-Master (Apr 2025–Mär 2026) · Stock-Received-Master (Apr 2025–Apr 2026) · JTL 11.05.2026<br>
  Drehende Ware: 9 Lieferanten · Periode {{PERIODE}} Tage · Vorfinanzierung = Bezahlt > Tag 30 nach Wareneingang
</footer>

</div>

<!-- Floating Help Button -->
<button class="help-toggle" onclick="toggleHelp()" title="Erklärung & Legende">?</button>

<div class="help-overlay" id="help-overlay" onclick="toggleHelp()"></div>

<div class="help-panel" id="help-panel">
  <div class="help-header">
    <h2>Erklärung & Legende</h2>
    <button class="close" onclick="toggleHelp()">×</button>
  </div>
  <div class="help-content">

    <h3>1 · Was zeigt dieses Dashboard?</h3>
    <p>Dieses Dashboard listet alle <b>Geräte aus dem Drehgeschäft 2025/26</b>, die <b>nach mehr als 30 Tagen nach Wareneingang bezahlt wurden</b>. Diese 30-Tage-Schwelle entspricht unserer Zahlungsfrist gegenüber den Hauptlieferanten OTTO und AEG. Alles darüber bedeutet: <b>wir mussten den Lieferanten bezahlen, bevor das Kundengeld da war</b> — Working Capital wurde dauerhaft blockiert.</p>

    <h3>2 · Datenbasis</h3>
    <table>
      <tr><td><b>Periode</b></td><td><b>01.04.2025 – 31.03.2026</b> (365 Tage, 12 Monate · maximaler Zeitraum unserer Datenlage)</td></tr>
      <tr><td><b>Lieferanten</b></td><td><b>Alle Lieferanten sind sichtbar</b> — im Dropdown gruppiert in „✓ Drehende Ware" (Hauptgeschäft, schnell durchlaufend) und „⚠ Altlasten / nicht-drehend" (langsam drehende Quellen).</td></tr>
      <tr><td><b>palette_otto / Ohrdruf</b></td><td>OTTO Kleingeräte aus Ohrdruf werden in der Stock-Analysis als <code>palette_otto</code> eingebucht, aber als <b>nicht-klassifizierte Container-Lager-IDs</b> ohne Brand/Article/Product Group. Beim späteren Klassifizieren werden die Geräte aufgesplittet und bekommen neue Lager-Nrn unter einem anderen Supply Type — daher derzeit kein 1:1-Verkaufs-Match möglich. Aufgabe für Stammdaten-Pflege: konsequente Re-Klassifizierung als „OTTO_Kleingeraete" bei Auflösung.</td></tr>
      <tr><td><b>Drehende Lieferanten</b></td><td>OTTO_MIX, AEG_Schrott, OTTO_Hanseatic, AEG_IT, Gorenje_Mix, OTTO_B_Ware, OTTO_Lagerschäden_Ansbach, OTTO_Jura, Samsung PEDC</td></tr>
      <tr><td><b>Filter-Kriterien Lieferant</b></td><td>P75 WE→Verkauf ≤ 22 T, Coverage ≥ 70 %, n ≥ 100</td></tr>
      <tr><td><b>Ausgeschlossen</b></td><td>OSF, AEG_Klein_Geräte, OTTO_Liebherr, OTTO_Erfurt, Samsung_Halle, Samsung_Rennerod, Pollin, Whirlpool_Bauknecht, Digital_Group — alle mit struktureller Altlast-Charakteristik</td></tr>
      <tr><td><b>Geräte gesamt überzogen</b></td><td>17.226 (von 51.018 mit voller Datenkette in der 12-Monats-Periode)</td></tr>
      <tr><td><b>Quellen</b></td><td>All-Sold-Master (70.395 Verkäufe), Stock-Received-Master (63.910 WE), JTL-Export 11.05.2026</td></tr>
    </table>

    <h3>2a · Coverage pro Monat (Transparenz)</h3>
    <p>Die folgende Tabelle zeigt, wie viel Prozent der drehenden Verkäufe pro Monat eine vollständige Datenkette haben. Frühjahr 2025 hat geringere Coverage, weil das Stock-Received-File erst am 01.04.2025 startet — Geräte mit WE in Q1 2025 fehlen.</p>
    <table>
      <tr><th>Monat</th><th style="text-align:right;">Verkäufe</th><th style="text-align:right;">Datenkette</th><th style="text-align:right;">Coverage</th><th></th></tr>
      <tr><td>April 2025</td><td style="text-align:right;">5.857</td><td style="text-align:right;">2.716</td><td style="text-align:right;">46,4 %</td><td>⚠ Anlauf</td></tr>
      <tr><td>Mai 2025</td><td style="text-align:right;">4.766</td><td style="text-align:right;">2.551</td><td style="text-align:right;">53,5 %</td><td>⚠ Anlauf</td></tr>
      <tr><td>Juni 2025</td><td style="text-align:right;">5.995</td><td style="text-align:right;">4.284</td><td style="text-align:right;">71,5 %</td><td>—</td></tr>
      <tr><td>Juli 2025</td><td style="text-align:right;">6.256</td><td style="text-align:right;">5.432</td><td style="text-align:right;">86,8 %</td><td>✓</td></tr>
      <tr><td>August 2025</td><td style="text-align:right;">4.879</td><td style="text-align:right;">4.154</td><td style="text-align:right;">85,1 %</td><td>✓</td></tr>
      <tr><td>September 2025</td><td style="text-align:right;">5.657</td><td style="text-align:right;">4.447</td><td style="text-align:right;">78,6 %</td><td>—</td></tr>
      <tr><td>Oktober 2025</td><td style="text-align:right;">3.469</td><td style="text-align:right;">3.220</td><td style="text-align:right;">92,8 %</td><td>✓</td></tr>
      <tr><td>November 2025</td><td style="text-align:right;">5.528</td><td style="text-align:right;">4.889</td><td style="text-align:right;">88,4 %</td><td>✓</td></tr>
      <tr><td>Dezember 2025</td><td style="text-align:right;">3.774</td><td style="text-align:right;">3.663</td><td style="text-align:right;">97,1 %</td><td>✓✓</td></tr>
      <tr><td>Januar 2026</td><td style="text-align:right;">5.783</td><td style="text-align:right;">5.665</td><td style="text-align:right;">98,0 %</td><td>✓✓</td></tr>
      <tr><td>Februar 2026</td><td style="text-align:right;">5.131</td><td style="text-align:right;">5.084</td><td style="text-align:right;">99,1 %</td><td>✓✓</td></tr>
      <tr><td>März 2026</td><td style="text-align:right;">5.057</td><td style="text-align:right;">4.913</td><td style="text-align:right;">97,2 %</td><td>✓✓</td></tr>
    </table>
    <p style="font-size:12px;">Über 12 Monate gemittelt <b>82,1 % Coverage</b>. Für sehr strikte Aussagen kann der Datumsfilter auf Juli 2025+ gesetzt werden — dann steigt die Coverage auf 91 %.</p>

    <h3>3 · Die volle Pipeline — vier Stationen</h3>
    <div class="formula" style="font-size:13px; line-height:2;">
      <b>1.</b> Wareneingang (WE) →
      <b>2.</b> Verkauf / Angebot →
      <b>3.</b> Rechnungsstellung →
      <b>4.</b> Zahlungseingang ↔ vereinbartes Zahlungsziel
    </div>
    <p style="font-size:12px; color:var(--grey-1); margin-bottom:10px;">Die Pfeile zeigen die zeitliche Abfolge (links = früher, rechts = später). Die Spaltenwerte sind immer die <b>Anzahl Tage zwischen den beiden Stationen</b> (positive Zahl).</p>
    <table>
      <tr><th>Bezeichnung</th><th>Anzahl Tage zwischen…</th><th>Was bedeutet das?</th></tr>
      <tr>
        <td><b>Lager (T)</b><br><span style="color:var(--grey-2); font-size:11px;">WE → Verkauf</span></td>
        <td><b>WE</b> und <b>Verkauf</b><br><span style="color:var(--grey-2); font-size:11px;">Bsp.: WE 01.05., Verkauf 10.05. → 9 T</span></td>
        <td>Wie lange das Gerät im Lager lag bis verkauft wurde. <b>Unsere Operations</b> (Klassifizierung, Listing). Wir steuern das selbst.</td>
      </tr>
      <tr>
        <td><b>Verk → Bez (T)</b><br><span style="color:var(--grey-2); font-size:11px;">Verkauf → Bezahlt</span></td>
        <td><b>Verkauf</b> und <b>Bezahlt</b><br><span style="color:var(--grey-2); font-size:11px;">Bsp.: Verkauf 10.05., Bezahlt 30.05. → 20 T</span></td>
        <td>Tage vom Verkauf bis zum Geldeingang. Enthält noch unseren internen Rechnungsstellungs-Lag (~7–11 T Median).</td>
      </tr>
      <tr>
        <td><b>Rechn → Bez (T)</b><br><span style="color:var(--grey-2); font-size:11px;">Rechnung → Bezahlt</span></td>
        <td><b>Rechnung</b> und <b>Bezahlt</b><br><span style="color:var(--grey-2); font-size:11px;">Bsp.: Rechnung 18.05., Bezahlt 30.05. → 12 T</span></td>
        <td><b>Echte Kunden-DSO</b>. Ab Rechnungsstellung läuft das Zahlungsziel des Kunden. Fairer Vergleich mit der vereinbarten Frist.</td>
      </tr>
      <tr>
        <td><b>Ziel (T)</b><br><span style="color:var(--grey-2); font-size:11px;">Zahlungsziel</span></td>
        <td>Stammdaten-Wert<br><span style="color:var(--grey-2); font-size:11px;">aus JTL pro Auftrag</span></td>
        <td><b>Vereinbartes Zahlungsziel</b> in Tagen ab Rechnung — pro Auftrag in JTL gepflegt. 0 T = Vorkasse. Häufig 7 T, 14 T, 21 T.</td>
      </tr>
      <tr style="background:rgba(0,113,227,0.04);">
        <td><b>Über (T)</b><br><span style="color:var(--grey-2); font-size:11px;">Ziel überschritten</span></td>
        <td><b>Bezahlt</b> und <b>(Rechnung + Ziel)</b><br><span style="color:var(--grey-2); font-size:11px;">+ = Kunde zu spät, − = pünktlich</span></td>
        <td><b>⭐ DIE MAHN-RELEVANTE KENNZAHL.</b> Positive Werte = Kunde hat seine eigene Vereinbarung gebrochen → mahnfähig. Negative oder 0 = pünktlich.</td>
      </tr>
      <tr>
        <td><b>Cycle (T)</b><br><span style="color:var(--grey-2); font-size:11px;">WE → Bezahlt</span></td>
        <td><b>WE</b> und <b>Bezahlt</b><br><span style="color:var(--grey-2); font-size:11px;">Bsp.: WE 01.05., Bezahlt 30.05. → 29 T</span></td>
        <td>Gesamtdauer Wareneingang bis Geldeingang. <b>Im Wettstreit mit der 30-T-Lieferantenfrist (OTTO/AEG).</b></td>
      </tr>
    </table>

    <h3>4 · Geld-Spalten</h3>
    <table>
      <tr><th>Spalte</th><th>Definition</th></tr>
      <tr><td><b>EK (€)</b></td><td>Einkaufspreis pro Gerät (Portal Buying Price). Das ist der Betrag, den wir an den Lieferanten zahlen.</td></tr>
      <tr>
        <td><b>€-Tage</b></td>
        <td>
          <b>Das ist die zentrale Vorfinanzierungs-Kennzahl.</b><br>
          <span class="formula" style="margin:6px 0; display:block;">€-Tage = EK × Verspätungs-Tage über 30-T-Limit</span>
          Beispiel: Gerät mit EK 90 €, Cycle 61 T → Verspätung = 61 − 30 = 31 T → €-Tage = 90 € × 31 = <b>2.790 €-Tage</b>.<br>
          Bedeutung: An diesem einen Gerät waren <b>90 € für 31 Tage</b> blockiert. Die Summe aller €-Tage geteilt durch die Periode (273 T) = das permanent gebundene Working Capital.
        </td>
      </tr>
    </table>

    <h3>5 · Pill-Farben (Bewertungslogik)</h3>
    <table>
      <tr><th>Spalte</th><th>🟢 Grün</th><th>🔵 Blau</th><th>🟠 Orange</th><th>🔴 Rot</th></tr>
      <tr><td><b>Lager (T)</b></td><td>≤ 7 T</td><td>8–14 T</td><td>15–30 T</td><td>&gt; 30 T</td></tr>
      <tr><td><b>Verk → Bez (T)</b></td><td>≤ 14 T</td><td>—</td><td>15–30 T</td><td>&gt; 30 T</td></tr>
      <tr><td><b>Rechn → Bez (T)</b></td><td>≤ 14 T</td><td>—</td><td>15–30 T</td><td>&gt; 30 T</td></tr>
      <tr><td><b>Cycle (T)</b></td><td>—</td><td>31–45 T<br><span style="font-size:11px;color:var(--grey-2);">leicht überzogen</span></td><td>46–60 T<br><span style="font-size:11px;color:var(--grey-2);">bemerkbar</span></td><td>&gt; 60 T<br><span style="font-size:11px;color:var(--grey-2);">&gt;90 dunkelrot · kritisch</span></td></tr>
      <tr style="background:rgba(0,113,227,0.04);"><td><b>Über (T)</b><br>Zahlungsziel</td><td>≤ 0 T<br><span style="font-size:11px;color:var(--grey-2);">pünktlich</span></td><td>—</td><td>+1 bis +7 T<br><span style="font-size:11px;color:var(--grey-2);">verspätet</span></td><td>+8 bis +30 T<br><span style="font-size:11px;color:var(--grey-2);">mahnpflichtig</span></td></tr>
    </table>
    <p style="font-size:12px;"><b>Über (T) — Spezialfall:</b> &gt; +30 T wird mit dunkelrot markiert (Inkasso-Eskalation)</p>
    <p style="font-size:12px;">14 T = übliches Netto-Zahlungsziel · 30 T = Lieferantenfrist (OTTO/AEG) · 60 T = doppelt überzogen · 90+ T = Kreditrisiko<br>
    <b>Hinweis Cycle:</b> Da im Dashboard nur überzogene Geräte (Cycle > 30 T) gezeigt werden, gibt es hier kein „Grün" — die Skala beginnt direkt bei „leicht überzogen".</p>

    <h3>6 · Was bedeuten die KPIs oben?</h3>
    <table>
      <tr><td><b>Geräte gefiltert</b></td><td>Anzahl Geräte in der aktuellen Filterauswahl</td></tr>
      <tr><td><b>⌀ WE → Bezahlt</b></td><td>Mittlere Gesamtdauer ab Wareneingang bis Zahlungseingang</td></tr>
      <tr><td><b>⌀ Verk. → Bez.</b></td><td>Mittlere Dauer ab Verkaufsdatum</td></tr>
      <tr><td><b>⌀ Rechn. → Bez.</b></td><td>Echte Kunden-DSO ab Rechnungsstellung — die fairste Kennzahl für Kunden-Zahlungsverhalten</td></tr>
      <tr><td><b>⌀ Lager-Tage</b></td><td>Mittlere Verweildauer im Lager (operative Geschwindigkeit)</td></tr>
      <tr><td><b>WC-Beitrag</b></td><td>Dauerhaft blockiertes Working Capital = Σ €-Tage ÷ Perioden-Tage</td></tr>
    </table>
    <p style="font-size:12px;"><b>Hinweis:</b> Sowohl <b>WE→Bezahlt</b> als auch <b>Lager-Tage</b> haben rechtsschiefe Verteilungen (einige sehr alte Geräte ziehen den Mean hoch). Bei großer Schiefe erscheint ein <b>⚠ Long-Tail</b>-Hinweis im Untertitel der jeweiligen Karte — Median ist dann die typischere Realität.</p>

    <h3>7 · Die drei operativen Hebel (wer ist verantwortlich?)</h3>
    <div class="help-tip"><div class="num">1</div><div><b>Hoher „Lager (T)"</b> → unser Problem. Klassifizierung &amp; Listing-Geschwindigkeit. <i>Operations / Backoffice ansprechen.</i></div></div>
    <div class="help-tip"><div class="num">2</div><div><b>Hohes „Verk → Bez" aber niedriges „Rechn → Bez"</b> → Rechnungsstellung dauert zu lang. <i>Buchhaltung / Auftragsabwicklung ansprechen.</i></div></div>
    <div class="help-tip"><div class="num">3</div><div><b>Hohes „Über (T)"</b> → Kunde bricht seine eigene Zahlungsziel-Vereinbarung. <i>Mahnstufe / Telefonat / Skonto / Vorkasse-Umstellung.</i> ⭐ Die wichtigste Mahn-relevante Kennzahl.</div></div>

    <h3>8 · Berechnungs-Beispiel komplett</h3>
    <div class="example">
      Gerät 900223767 · PRIVILEG Waschtrockner · OTTO_MIX · Enterijer doo<br><br>
      WE: 29.01.2026 · Verkauf: 02.03.2026 · Rechnung: 02.03.2026 · Bezahlt: 31.03.2026 · EK: 90 €<br><br>
      <b>Lager (T)</b> = 02.03. − 29.01. = <b>32 T</b> (lang im Lager — unser Operations-Problem)<br>
      <b>Verk → Bez (T)</b> = 31.03. − 02.03. = <b>29 T</b> (etwas über Standard-Netto)<br>
      <b>Rechn → Bez (T)</b> = 31.03. − 02.03. = <b>27 T</b> (Kunde brauchte fast 4 Wochen — orange)<br>
      <b>Cycle (T)</b> = 31.03. − 29.01. = <b>61 T</b><br>
      <b>Verspätung über 30 T</b> = 61 − 30 = <b>31 T</b><br>
      <b>€-Tage</b> = 90 € × 31 T = <b>2.790 €-Tage</b>
    </div>

    <h3>9 · Schnellfilter (oben über den normalen Filtern)</h3>
    <p>Die obere Leiste ist die schnelle Filter-Vorauswahl — kombiniert Zeitraum + Lager-Alter + Hauptlieferanten-Filter in einem Klick.</p>
    <table>
      <tr><th>Button</th><th>Was passiert?</th></tr>
      <tr><td><b>📊 2026 · Hauptlieferanten (Default)</b></td><td>Periode 2026 + Max-Lager 60 T + <b>nur drehende Hauptlieferanten</b> (OTTO_MIX, AEG_Schrott, OTTO_Hanseatic, …). Altlast-Lieferanten wie OSF, AEG_Klein_Geräte, OTTO_Liebherr werden ausgeblendet. <b>Die KPIs oben zeigen die echte Realität des aktiven Drehgeschäfts 2026.</b></td></tr>
      <tr><td><b>Q1 2026 · Hauptlieferanten</b></td><td>Januar – März 2026 mit Lager ≤ 60 T, nur Hauptlieferanten.</td></tr>
      <tr><td><b>2025 · Hauptlieferanten</b></td><td>Verkäufe 2025 mit Lager ≤ 60 T, nur Hauptlieferanten.</td></tr>
      <tr><td><b>Letzte 30 Tage · Hauptlieferanten</b></td><td>Rolling-Window ab heutiger Datenlage (12.05.2026 zurück 30 T) mit Lager ≤ 60 T.</td></tr>
      <tr><td><b>Alle inkl. Altlasten</b></td><td>Voller Datenzeitraum Apr 2025 – Mär 2026 ohne jegliche Vorauswahl — auch Altlast-Lieferanten und alte Lagerbestände sind dabei.</td></tr>
    </table>
    <p style="font-size:12px;"><b>Empfehlung:</b> Für tägliche Mahn-Entscheidungen mit dem Default <b>„2026 · Hauptlieferanten"</b> arbeiten. Die KPIs zeigen dann die <b>echte aktuelle Realität</b> ohne historische Altlast-Verzerrung und ohne Lieferanten die nicht zum Drehgeschäft gehören.</p>
    <p style="font-size:12px;"><b>Checkbox „Nur Hauptlieferanten":</b> rechts in der Schnellfilter-Leiste — kann unabhängig ein-/ausgeschaltet werden, ohne den Zeitraum zu ändern.</p>

    <h3>10 · Manuelle Filter-Tipps</h3>
    <div class="help-tip"><div class="num">A</div><div><b>Kunde-Suchfeld</b> akzeptiert Teilstrings — „hanse" findet Hanseatic Georgia.</div></div>
    <div class="help-tip"><div class="num">B</div><div><b>Supply-Nr-Suchfeld</b> filtert auf konkrete Lieferungen — z. B. „3390022" oder „AEG_NH".</div></div>
    <div class="help-tip"><div class="num">C</div><div><b>Top-Schuldner-Chips</b> sind One-Click-Filter — Klick zum Aktivieren, zweiter Klick zum Deaktivieren.</div></div>
    <div class="help-tip"><div class="num">D</div><div><b>Spaltenüberschriften sind klickbar</b> für Sortierung. Erneuter Klick kehrt die Richtung um.</div></div>
    <div class="help-tip"><div class="num">E</div><div><b>CSV-Export</b> exportiert genau die aktuelle Filterauswahl in der aktuellen Sortierung — direkt einsetzbar für Mahn-Mails oder Telefonlisten.</div></div>

    <h3>10 · Herleitung des 30-Tage-Schwellwerts</h3>
    <p>OTTO und AEG sind unsere Hauptlieferanten und gewähren standardmäßig <b>30 Tage Zahlungsziel ab Wareneingang</b>. Innerhalb dieser 30 Tage muss das Kundengeld bei uns sein, sonst gehen wir in Vorlage (Working Capital wird blockiert). Jeder Tag jenseits 30 T = direkte Liquiditätslücke.</p>
    <div class="formula">
Cycle (T) ≤ 30 → ✓ Kundengeld vor Lieferantenstichtag<br>
Cycle (T) &gt; 30 → ✗ Wir finanzieren vor (Geld auf Konto blockiert)
    </div>

    <h3>11 · Validierung der WC-Zahl</h3>
    <p>Die Working-Capital-Zahl ist mathematisch durch vier unabhängige Methoden validiert:</p>
    <table>
      <tr><td><b>Tagesdurchschnitt-Integral</b></td><td>Σ(EK × Verspätung) ÷ Periode</td></tr>
      <tr><td><b>Little's Law</b></td><td>L = λ × W (Queueing-Theorie)</td></tr>
      <tr><td><b>Tag-für-Tag-Aufsummung</b></td><td>für jeden Tag der Periode wird gebundenes Kapital aufaddiert, dann gemittelt</td></tr>
      <tr><td><b>Coverage-Bereinigung</b></td><td>auf 100 % der Drehmenge skaliert</td></tr>
    </table>
    <p>Alle vier Methoden ergeben Werte im Bereich <b>106 – 129 k €</b>, die im Dashboard angezeigte Zahl (105.827 €) ist die konservative untere Schranke (Methode A). <b>Stabilität-Check:</b> bei Ausweitung von 9 auf 12 Monate ändert sich WC nur um <b>+1,4 %</b> — bestätigt: WC ist eine echte stationäre Größe, kein Aufstauer.</p>

    <h3>12a · Methodik-Hinweise zum Verständnis</h3>
    <table>
      <tr><td><b>WC-Beitrag (Working Capital)</b></td><td>Σ(EK × Verspätungs-Tage) ÷ <b>dynamische Filter-Periode</b> der angezeigten Daten. Wenn du auf Q1 2026 filterst (90 Tage), wird durch 90 geteilt — nicht durch 365.</td></tr>
      <tr><td><b>Mean &lt; Median bei Verk→Bez</b></td><td>Normal in dieser Auswertung. Selection-Bias durch die 30-T-Überziehungs-Definition: Geräte mit kurzem Lager (z. B. 4 T) brauchen Verk→Bez &gt; 26 T zum Überziehen; Geräte mit langem Lager (z. B. 50 T) können Verk→Bez = 0 T haben und trotzdem überzogen sein. Die Long-Lager-Gruppe drückt den Mean nach unten.</td></tr>
      <tr><td><b>Ziel überschritten zeigt %</b></td><td>Prozentsatz der Aufträge mit Überschreitung — nicht der Mean (der wird durch Frühzahler/Skonto-Nutzer verzerrt nach unten). Subtitle zeigt zusätzlich „Ø wenn überschritten" als operativ relevante Zahl.</td></tr>
    </table>

    <h3>12 · Mean vs. Median — warum die Zahlen oft auseinanderlaufen</h3>
    <p>Beide Werte sind mathematisch korrekt, messen aber unterschiedliche Aspekte:</p>
    <table>
      <tr><td><b>Median</b></td><td>typische Realität (50 % der Geräte sind schneller, 50 % langsamer). Robust gegen Ausreißer.</td></tr>
      <tr><td><b>Mean (Mittelwert)</b></td><td>kapitalbindungs-relevant — wenige Altlast-Restposten mit langer Lagerdauer ziehen ihn hoch.</td></tr>
    </table>
    <p>Wenn Median und Mean stark auseinanderliegen (z. B. Mean 51,8 T, Median 39 T), zeigt ein <b>⚠ Long-Tail-Warnhinweis</b> in der KPI-Karte. Ursache sind meist <b>Altlast-Geräte aus drehenden Lieferanten</b> — also OTTO/AEG-Artikel die ausnahmsweise 6–12 Monate liegen, weil sie schlecht verkäuflich waren.</p>
    <div class="example">
      <b>Beispiel Q1 2026 mit allen Geräten:</b> Mean 51,8 T, Median 39 T<br>
      <b>Nach Filter „Max Lager 60 T":</b> Mean 42,6 T, Median 38 T<br>
      → 416 Altlast-Geräte (8,4 %) ziehen den Mean um <b>9 Tage</b> hoch.<br><br>
      <b>Tipp:</b> Setze den <b>„Max Lager (T)"</b>-Filter auf 60 oder 90, um echte Drehgeschäfts-Kennzahlen ohne Altlasten zu sehen.
    </div>

    <h3>13 · KPI-Validation (Cross-Check 12-Monats-Periode)</h3>
    <p>Jede der sechs KPIs oben ist gegen die Rohdaten cross-validiert:</p>
    <table>
      <tr><th>Check</th><th>Wert</th><th>Status</th></tr>
      <tr><td>Mean WE→Bezahlt</td><td>56,6 T</td><td>✓ exakt</td></tr>
      <tr><td>Mean Verk→Bez</td><td>33,1 T</td><td>✓ exakt</td></tr>
      <tr><td>Mean Rechn→Bez</td><td>22,4 T</td><td>✓ exakt</td></tr>
      <tr><td>Mean Lager</td><td>23,5 T</td><td>✓ exakt</td></tr>
      <tr><td><b>Additivität</b>: Lager + Verk→Bez = WE→Bez</td><td>23,5 + 33,1 = 56,6 ✓</td><td>✓ konsistent</td></tr>
      <tr><td><b>Rechnungs-Lag</b>: Verk→Bez − Rechn→Bez</td><td>33,1 − 22,4 = 10,7 T</td><td>Verkauf-bis-Rechnungsstellung</td></tr>
      <tr><td>WC = Σ €-Tage ÷ Periode</td><td>38,6 Mio €-Tage ÷ 362 T = 105.827 €</td><td>✓ exakt</td></tr>
      <tr><td>Kapitalkosten 10 % p.a.</td><td>105.827 × 0,10 = 10.583 €</td><td>✓ exakt</td></tr>
    </table>
    <p style="font-size:12px;">Validation-Skript: <code>validate_dashboard.py</code> · Reproduzierbar gegen die Rohdaten <code>we_to_paid_MASTER.csv</code>.</p>

  </div>
</div>

<script>
const DATA = {DATA_JSON};
const META = {META_JSON};

// Populate dropdowns
const fLieferant = document.getElementById('f-lieferant');
// Pro Lieferant: Anzahl überzogener Geräte zählen
const lieferantCounts = {{}};
DATA.forEach(r => {{ lieferantCounts[r.lieferant] = (lieferantCounts[r.lieferant]||0) + 1; }});
// Optgroups: drehend zuerst, dann Rest
const optGroupDrehend = document.createElement('optgroup');
optGroupDrehend.label = '✓ Drehende Ware (Hauptgeschäft)';
const optGroupRest = document.createElement('optgroup');
optGroupRest.label = '⚠ Altlasten / nicht-drehend';
META.lieferanten.forEach(v => {{
  const n = lieferantCounts[v] || 0;
  const isDrehend = META.drehend.includes(v);
  const o = document.createElement('option');
  o.value = v;
  o.textContent = `${{v}} (${{n.toLocaleString('de-DE')}})`;
  if (isDrehend) optGroupDrehend.appendChild(o);
  else optGroupRest.appendChild(o);
}});
fLieferant.appendChild(optGroupDrehend);
fLieferant.appendChild(optGroupRest);
const fProduct = document.getElementById('f-product');
META.produkte.forEach(v => {{ const o = document.createElement('option'); o.value = v; o.textContent = v; fProduct.appendChild(o); }});
const fBrand = document.getElementById('f-brand');
META.brands.forEach(v => {{ const o = document.createElement('option'); o.value = v; o.textContent = v; fBrand.appendChild(o); }});

let state = {{
  filter: {{ kunde: '', lieferant: '', product: '', brand: '', supply: '', dateFrom: '', dateTo: '', maxLager: '', onlyDrehend: true }},
  sort: {{ key: 'eurd', dir: 'desc' }},
  page: 1,
}};

// Top-Schuldner-Chips
function buildTopChips() {{
  const agg = {{}};
  DATA.forEach(r => {{
    if (!agg[r.kunde]) agg[r.kunde] = {{ n: 0, eurd: 0 }};
    agg[r.kunde].n += 1;
    agg[r.kunde].eurd += r.eurd;
  }});
  const total_eurd = DATA.reduce((s,r)=>s+r.eurd,0);
  const top = Object.entries(agg).sort((a,b)=>b[1].eurd-a[1].eurd).slice(0,10);
  const wrap = document.getElementById('top-chips');
  top.forEach(([kunde, v]) => {{
    const c = document.createElement('div'); c.className = 'chip';
    const pct = (v.eurd/total_eurd*100).toFixed(1);
    c.innerHTML = `<span>${{kunde}}</span> <span class="pct">${{pct}} %</span>`;
    c.onclick = () => {{
      const inp = document.getElementById('f-kunde');
      if (inp.value === kunde) {{ inp.value = ''; }} else {{ inp.value = kunde; }}
      document.querySelectorAll('.chip').forEach(x=>x.classList.remove('active'));
      if (inp.value) c.classList.add('active');
      state.filter.kunde = inp.value.toLowerCase();
      state.page = 1; render();
    }};
    wrap.appendChild(c);
  }});
}}
buildTopChips();

function applyFilters() {{
  const f = state.filter;
  return DATA.filter(r => {{
    if (f.kunde && !r.kunde.toLowerCase().includes(f.kunde)) return false;
    if (f.lieferant && r.lieferant !== f.lieferant) return false;
    if (f.product && r.product !== f.product) return false;
    if (f.brand && r.brand !== f.brand) return false;
    if (f.supply && !r.supply.toLowerCase().includes(f.supply)) return false;
    if (f.dateFrom && r.sold < f.dateFrom) return false;
    if (f.dateTo && r.sold > f.dateTo) return false;
    if (f.maxLager !== '' && r.lagerD > parseInt(f.maxLager)) return false;
    if (f.onlyDrehend && !META.drehend.includes(r.lieferant)) return false;
    return true;
  }});
}}

// ===== PROFIL-GENERATOR =====
function buildProfile(filtered) {{
  const profEl = document.getElementById('profile');
  const eyebrow = document.getElementById('profile-eyebrow');
  const title = document.getElementById('profile-title');
  const narr = document.getElementById('profile-narrative');
  const mini = document.getElementById('profile-ministats');
  const f = state.filter;
  const n = filtered.length;
  if (n === 0) {{
    profEl.className = 'profile empty';
    eyebrow.textContent = 'Keine Treffer';
    title.textContent = 'Aktuelle Filterkombination findet 0 Geräte';
    narr.innerHTML = 'Filter zurücksetzen oder Suchbegriff anpassen.';
    mini.innerHTML = '';
    return;
  }}

  const sumDays = filtered.reduce((s,r)=>s+r.delay,0);
  const sumEk   = filtered.reduce((s,r)=>s+r.ek,0);
  const sumEurd = filtered.reduce((s,r)=>s+r.eurd,0);
  const wc = sumEurd / periodeTageDyn(filtered);
  const avgDelay = sumDays / n;
  const avgCycle = filtered.reduce((s,r)=>s+r.cycle,0) / n;     // WE→Bezahlt gesamt
  const avgCust  = filtered.reduce((s,r)=>s+r.customer,0) / n;  // Verkauf→Bezahlt
  const avgLager = filtered.reduce((s,r)=>s+r.lagerD,0) / n;    // WE→Verkauf (uns)
  const invArr   = filtered.filter(r=>r.invoice!==null).map(r=>r.invoice);
  const avgInv   = invArr.length ? invArr.reduce((s,v)=>s+v,0)/invArr.length : 0;
  const termArr  = filtered.filter(r=>r.payTerm!==null).map(r=>r.payTerm);
  const avgTerm  = termArr.length ? termArr.reduce((s,v)=>s+v,0)/termArr.length : 0;
  const tdArr    = filtered.filter(r=>r.targetDelay!==null).map(r=>r.targetDelay);
  const avgTd    = tdArr.length ? tdArr.reduce((s,v)=>s+v,0)/tdArr.length : 0;
  const overdueShare = tdArr.length ? tdArr.filter(v=>v>0).length/tdArr.length*100 : 0;
  const totalGlobal = DATA.reduce((s,r)=>s+r.eurd,0);
  const share = sumEurd / totalGlobal * 100;

  function topByEurd(field, k=3) {{
    const agg = {{}};
    filtered.forEach(r => {{
      const key = r[field] || '—';
      if (!agg[key]) agg[key] = {{ n:0, eurd:0 }};
      agg[key].n++; agg[key].eurd += r.eurd;
    }});
    return Object.entries(agg).sort((a,b)=>b[1].eurd-a[1].eurd).slice(0,k);
  }}

  // Profil-Typ bestimmen
  const activeFilters = Object.entries(f).filter(([k,v])=>v).map(([k])=>k);

  function tone(v, good, warn) {{
    if (v >= warn) return 'bad';
    if (v >= good) return 'warn';
    return 'hi';
  }}

  let titleTxt = '', eyebrowTxt = '', narrativeHTML = '';

  if (f.kunde && activeFilters.length === 1) {{
    // KUNDEN-PROFIL — DSO ist hier die zentrale Kennzahl, nicht Lagerdauer
    const kundeName = filtered[0]?.kunde || f.kunde;
    const topLief = topByEurd('lieferant', 3);
    const topProd = topByEurd('product', 3);
    const maxCust = Math.max(...filtered.map(r=>r.customer));
    const worstShare = topLief[0] ? (topLief[0][1].eurd/sumEurd*100).toFixed(0) : '0';
    eyebrowTxt = 'Kunden-Profil · Pipeline-Analyse';
    titleTxt = kundeName;
    // PRIMÄRE BEWERTUNG: Überschreitung des vereinbarten Zahlungsziels (= echte Mahn-Relevanz)
    const tdClass = avgTd > 14 ? 'bad' : (avgTd > 0 ? 'warn' : 'hi');
    const ratingTxt = avgTd > 14
      ? '<b class="bad">🔴 KRITISCH — Mahn-Eskalation einleiten. Kunde überschreitet sein vereinbartes Zahlungsziel im Schnitt um mehr als 14 Tage.</b>'
      : avgTd > 0
      ? '<b class="warn">🟠 MAHN-PFLICHTIG — Kunde überschreitet das vereinbarte Zahlungsziel regelmäßig. Mahnstufe + Telefonat empfohlen.</b>'
      : '<b class="hi">🟢 VERTRAGSKONFORM — Kunde hält das vereinbarte Zahlungsziel ein. Vorfinanzierung kommt nicht von hier.</b>';
    const termInfo = termArr.length
      ? `<b>Vereinbartes Zahlungsziel</b>: Ø <span class="hi">${{avgTerm.toFixed(0)}} T</span> netto ab Rechnung.<br>
        <b>Überschreitung des Ziels</b>: Ø <span class="${{tdClass}}">${{avgTd>=0?'+':''}}${{avgTd.toFixed(1)}} T</span> · <b>${{overdueShare.toFixed(0)}} %</b> der Aufträge zu spät.<br>`
      : '';
    narrativeHTML = `
      <b>${{kundeName}}</b> · <b>${{fmtN(n)}} Geräte</b> über die 30-T-Lieferantenfrist hinaus.<br><br>
      <span style="color:rgba(255,255,255,0.6); font-size:12px; text-transform:uppercase; letter-spacing:0.5px;">Pipeline-Kette (Ø Tage):</span><br>
      ${{termInfo}}<br>
      <b>Wareneingang → Verkauf</b> (Lagerdauer · unsere Operations): Ø <span class="hi">${{avgLager.toFixed(1)}} T</span><br>
      <b>Verkauf → Rechnung</b> (interner Rechnungs-Lag): Ø <span class="hi">${{(avgCust-avgInv).toFixed(1)}} T</span><br>
      <b>Rechnung → Bezahlt</b> (echte Kunden-DSO): Ø <span class="${{tdClass}}">${{avgInv.toFixed(1)}} T</span><br>
      <b>Gesamt WE → Bezahlt</b>: Ø <span class="warn">${{avgCycle.toFixed(1)}} T</span><br><br>
      Das blockiert dauerhaft <b class="bad">${{fmtE(wc)}}</b> Working Capital — <b>${{share.toFixed(1)}} %</b> der Gesamt-Vorfinanzierung.
      Hauptlieferant: <span class="hi">${{topLief[0][0]}}</span> (${{worstShare}} %), Produktgruppe <span class="hi">${{topProd[0][0]}}</span>.<br><br>
      ${{ratingTxt}}
    `;
  }}
  else if (f.lieferant && activeFilters.length === 1) {{
    // LIEFERANTEN-PROFIL
    const topKunden = topByEurd('kunde', 3);
    const topProd = topByEurd('product', 3);
    const totalLief = DATA.filter(r=>r.lieferant===f.lieferant).length;
    eyebrowTxt = 'Lieferanten-Profil';
    titleTxt = f.lieferant;
    const delayClass = avgDelay > 30 ? 'warn' : 'hi';
    narrativeHTML = `
      Aus Lieferant <b>${{f.lieferant}}</b> sind <b>${{fmtN(n)}} Geräte</b> über die 30-Tage-Frist hinaus —
      Ø <span class="${{delayClass}}">${{avgDelay.toFixed(1)}} T Verspätung</span>, blockiert <b class="bad">${{fmtE(wc)}}</b> Working Capital
      (<b>${{share.toFixed(1)}} %</b> der gesamten Vorfin-Last).<br>
      Die drei größten Schuldner bei diesem Lieferanten: <span class="hi">${{topKunden[0][0]}}</span>
      ${{topKunden[1] ? '· <span class="hi">'+topKunden[1][0]+'</span>' : ''}}
      ${{topKunden[2] ? '· <span class="hi">'+topKunden[2][0]+'</span>' : ''}}.
      Schwerpunkt-Produkte: <span class="hi">${{topProd.map(([k])=>k).slice(0,2).join(', ')}}</span>.
    `;
  }}
  else if (f.supply && activeFilters.length === 1) {{
    // SUPPLY-PROFIL
    const topKunden = topByEurd('kunde', 3);
    const supplyVal = filtered[0]?.supply || f.supply;
    eyebrowTxt = 'Supply-/Lieferungs-Profil';
    titleTxt = 'Supply ' + supplyVal;
    narrativeHTML = `
      Aus dieser Supply-Nummer (<b>${{supplyVal}}</b>) sind <b>${{fmtN(n)}} Geräte</b> mit Verspätung —
      Ø ${{avgDelay.toFixed(1)}} T, blockiert <b class="bad">${{fmtE(wc)}}</b>.
      Hauptkunden dieser Lieferung: <span class="hi">${{topKunden.map(([k])=>k).slice(0,3).join(', ')}}</span>.
    `;
  }}
  else if (f.product && activeFilters.length === 1) {{
    const topKunden = topByEurd('kunde', 3);
    const topLief = topByEurd('lieferant', 2);
    eyebrowTxt = 'Produkt-Profil';
    titleTxt = f.product;
    narrativeHTML = `
      Produktgruppe <b>${{f.product}}</b>: <b>${{fmtN(n)}} verspätete Geräte</b>, Ø ${{avgDelay.toFixed(1)}} T,
      blockiert <b class="bad">${{fmtE(wc)}}</b> WC. Schwerpunkt-Kunden: <span class="hi">${{topKunden.map(([k])=>k).slice(0,3).join(', ')}}</span>.
      Hauptlieferanten: <span class="hi">${{topLief.map(([k])=>k).join(', ')}}</span>.
    `;
  }}
  else if (f.brand && activeFilters.length === 1) {{
    const topKunden = topByEurd('kunde', 3);
    eyebrowTxt = 'Brand-Profil';
    titleTxt = f.brand;
    narrativeHTML = `
      Brand <b>${{f.brand}}</b>: <b>${{fmtN(n)}} verspätete Geräte</b>, Ø ${{avgDelay.toFixed(1)}} T,
      blockiert <b class="bad">${{fmtE(wc)}}</b> WC. Hauptkunden: <span class="hi">${{topKunden.map(([k])=>k).slice(0,3).join(', ')}}</span>.
    `;
  }}
  else if (activeFilters.length > 1) {{
    // KOMBINIERTE FILTER
    const topKunden = topByEurd('kunde', 2);
    const parts = [];
    if (f.kunde) parts.push(`Kunde „${{filtered[0]?.kunde||f.kunde}}"`);
    if (f.lieferant) parts.push(`Lieferant „${{f.lieferant}}"`);
    if (f.supply) parts.push(`Supply „${{f.supply}}"`);
    if (f.product) parts.push(`Produkt „${{f.product}}"`);
    if (f.brand) parts.push(`Brand „${{f.brand}}"`);
    if (f.dateFrom || f.dateTo) parts.push(`Zeitraum ${{f.dateFrom||'…'}} – ${{f.dateTo||'…'}}`);
    eyebrowTxt = 'Kombinations-Filter';
    titleTxt = parts.join(' + ');
    narrativeHTML = `
      <b>${{fmtN(n)}} Geräte</b> erfüllen alle gewählten Kriterien · Ø Verspätung <b>${{avgDelay.toFixed(1)}} T</b> ·
      EK <b>${{fmtE(sumEk)}}</b> · blockiert <b class="bad">${{fmtE(wc)}}</b> WC
      (${{share.toFixed(1)}} % der Gesamt-Vorfinanzierung).
      ${{topKunden[0] ? 'Größter Anteil bei <span class="hi">'+topKunden[0][0]+'</span>.' : ''}}
    `;
  }}
  else {{
    // GESAMT-ÜBERSICHT (keine Filter)
    const topKunden = topByEurd('kunde', 3);
    const topLief = topByEurd('lieferant', 2);
    eyebrowTxt = 'Gesamt-Übersicht';
    titleTxt = 'Drehende Ware · 12 Monate';
    narrativeHTML = `
      <b>${{fmtN(n)}} überzogene Geräte</b> über 12 Monate (Apr 2025 – Mär 2026) blockieren dauerhaft <b class="bad">${{fmtE(wc)}}</b>
      Working Capital — Ø Verspätung <b class="warn">${{avgDelay.toFixed(1)}} T</b> über die 30-T-Lieferantenfrist hinaus.<br>
      Top-Schuldner: <span class="hi">${{topKunden[0][0]}}</span> (${{(topKunden[0][1].eurd/sumEurd*100).toFixed(1)}} %),
      <span class="hi">${{topKunden[1][0]}}</span> (${{(topKunden[1][1].eurd/sumEurd*100).toFixed(1)}} %),
      <span class="hi">${{topKunden[2][0]}}</span> (${{(topKunden[2][1].eurd/sumEurd*100).toFixed(1)}} %).
      Setze einen Filter (Kunde/Lieferant/Supply) für ein detailliertes Profil.
    `;
  }}

  profEl.className = 'profile';
  eyebrow.textContent = eyebrowTxt;
  title.textContent = titleTxt;
  narr.innerHTML = narrativeHTML;

  // Mini-Stats — die vier Cycle-Time-Bausteine
  const invDisp = invArr.length ? avgInv.toFixed(1) + ' T' : '—';
  const invSub  = invArr.length ? 'echte Kunden-DSO' : 'keine Rechnungsdaten';
  mini.innerHTML = `
    <div class="item"><div class="lbl">⌀ Lager (WE→Verk.)</div><div class="val">${{avgLager.toFixed(1)}} T</div><div class="sub">unsere Operations</div></div>
    <div class="item"><div class="lbl">⌀ Rechng. → Bez.</div><div class="val">${{invDisp}}</div><div class="sub">${{invSub}}</div></div>
    <div class="item"><div class="lbl">⌀ Cycle (WE→Bez.)</div><div class="val">${{avgCycle.toFixed(1)}} T</div><div class="sub">Gesamtdauer</div></div>
    <div class="item"><div class="lbl">WC blockiert</div><div class="val">${{fmtE(wc)}}</div><div class="sub">${{share.toFixed(1)}} % Gesamt-Last</div></div>
  `;
}}

function sortData(data) {{
  const {{ key, dir }} = state.sort;
  const factor = dir === 'asc' ? 1 : -1;
  return [...data].sort((a,b) => {{
    const va = a[key], vb = b[key];
    if (typeof va === 'number') return (va-vb)*factor;
    return String(va).localeCompare(String(vb)) * factor;
  }});
}}

function fmtN(v) {{ return new Intl.NumberFormat('de-DE').format(v); }}
function fmtE(v) {{ return new Intl.NumberFormat('de-DE',{{maximumFractionDigits:0}}).format(v) + ' €'; }}
function periodeTageDyn(arr) {{
  // Dynamische Periode = Spanne (max-min)+1 Tage der filtered sold-Daten
  if (!arr.length) return META.periode_tage;
  let mn=Infinity, mx=-Infinity;
  for (const r of arr) {{ const t=new Date(r.sold).getTime(); if (t<mn) mn=t; if (t>mx) mx=t; }}
  return Math.max(1, Math.round((mx-mn)/86400000)+1);
}}
function median(arr) {{
  if (!arr.length) return 0;
  const s = [...arr].sort((a,b)=>a-b);
  const m = Math.floor(s.length/2);
  return s.length%2 ? s[m] : (s[m-1]+s[m])/2;
}}

function render() {{
  const filtered = applyFilters();
  const sorted = sortData(filtered);
  const pageSize = parseInt(document.getElementById('page-size').value);
  const totalPages = Math.max(1, Math.ceil(sorted.length / pageSize));
  if (state.page > totalPages) state.page = totalPages;
  const from = (state.page-1) * pageSize;
  const to = Math.min(from + pageSize, sorted.length);
  const slice = sorted.slice(from, to);

  // KPIs — vier separate Cycle-Time-Metriken
  const n = filtered.length;
  const sumEk    = filtered.reduce((s,r)=>s+r.ek,0);
  const sumEurd  = filtered.reduce((s,r)=>s+r.eurd,0);
  const avgCycle = n ? filtered.reduce((s,r)=>s+r.cycle,0) / n : 0;
  const avgCust  = n ? filtered.reduce((s,r)=>s+r.customer,0) / n : 0;
  const avgLager = n ? filtered.reduce((s,r)=>s+r.lagerD,0) / n : 0;
  const invArr = filtered.filter(r=>r.invoice!==null).map(r=>r.invoice);
  const avgInv = invArr.length ? invArr.reduce((s,v)=>s+v,0)/invArr.length : 0;
  const targetArr = filtered.filter(r=>r.targetDelay!==null).map(r=>r.targetDelay);
  const avgTarget = targetArr.length ? targetArr.reduce((s,v)=>s+v,0)/targetArr.length : 0;
  const overdueN = targetArr.filter(v=>v>0).length;
  const wc = sumEurd / periodeTageDyn(filtered);

  // PROFIL aktualisieren
  buildProfile(filtered);

  document.getElementById('kpi-n').textContent = fmtN(n);
  document.getElementById('kpi-n-sub').textContent = `von ${{fmtN(DATA.length)}} überzogenen`;
  const medCycle = median(filtered.map(r=>r.cycle));
  document.getElementById('kpi-cycle').textContent = avgCycle.toFixed(1) + ' T';
  // Skew-Warnung wenn Mean/Median > 1.25 (= deutlicher Long-Tail)
  const skewRatio = medCycle > 0 ? avgCycle/medCycle : 1;
  const skewHint = skewRatio > 1.25
    ? `Median <b style="color:var(--green);">${{medCycle.toFixed(0)}} T</b> · <span style="color:var(--orange);" title="Mean wird von Altlast-Restposten hochgezogen — Median ist die typischere Realität.">⚠ Long-Tail</span>`
    : `Median ${{medCycle.toFixed(0)}} T · WE → Bezahlt`;
  document.getElementById('kpi-cycle-sub').innerHTML = skewHint;
  document.getElementById('kpi-customer').textContent = avgCust.toFixed(1) + ' T';
  document.getElementById('kpi-customer-sub').textContent = `Median ${{median(filtered.map(r=>r.customer)).toFixed(0)}} T · ab Verkauf`;
  document.getElementById('kpi-invoice').textContent = avgInv ? avgInv.toFixed(1) + ' T' : '—';
  document.getElementById('kpi-invoice-sub').textContent = invArr.length ? `Median ${{median(invArr).toFixed(0)}} T · echte Kunden-DSO` : 'keine Rechnungsdaten';
  // KPI "Ziel überschritten": zeige Quote zuerst (relevanter als Mean, da Mean von Frühzahlern verzerrt)
  const overduePct = targetArr.length ? overdueN/targetArr.length*100 : 0;
  document.getElementById('kpi-target').textContent = targetArr.length
    ? `${{overduePct.toFixed(0)}} %`
    : '—';
  document.getElementById('kpi-target-sub').innerHTML = targetArr.length
    ? `${{fmtN(overdueN)}}/${{fmtN(targetArr.length)}} · Ø wenn überschritten: +${{(targetArr.filter(v=>v>0).reduce((s,v)=>s+v,0)/Math.max(1,overdueN)).toFixed(1)}} T`
    : 'kein Zahlungsziel hinterlegt';
  const medLager = median(filtered.map(r=>r.lagerD));
  document.getElementById('kpi-lager').textContent = avgLager.toFixed(1) + ' T';
  const lagerSkew = medLager > 0 ? avgLager/medLager : 1;
  document.getElementById('kpi-lager-sub').innerHTML = lagerSkew > 1.5
    ? `Median <b style="color:var(--green);">${{medLager.toFixed(0)}} T</b> · <span style="color:var(--orange);" title="Mean wird von Altlast-Geräten hochgezogen — Median ist die typische Lagerdauer.">⚠ Long-Tail</span>`
    : `Median ${{medLager.toFixed(0)}} T · WE → Verkauf`;
  document.getElementById('kpi-wc').textContent = fmtE(wc);
  document.getElementById('kpi-wc-sub').textContent = `bei 10 % Kontokorrent: ${{fmtE(wc*0.10)}} p. a. Zinslast`;

  // Tabelle
  const body = document.getElementById('tbl-body');
  if (slice.length === 0) {{
    body.innerHTML = '<tr><td colspan="17" style="text-align:center; padding:40px; color:var(--grey-1);">Keine Geräte mit aktueller Filterkombination.</td></tr>';
  }} else {{
    body.innerHTML = slice.map(r => {{
      // Lager-Verweildauer-Pill (operative Sicht)
      let lagerPill;
      if (r.lagerD > 30)      lagerPill = `<span class="pill pill-bad">${{r.lagerD}} T</span>`;
      else if (r.lagerD > 14) lagerPill = `<span class="pill pill-warn">${{r.lagerD}} T</span>`;
      else if (r.lagerD > 7)  lagerPill = `<span class="pill pill-mid">${{r.lagerD}} T</span>`;
      else                    lagerPill = `<span class="pill pill-good">${{r.lagerD}} T</span>`;

      // Kunden-Delay-Pill (ab VERKAUFSDATUM)
      let custPill;
      if (r.customer > 30)      custPill = `<span class="pill pill-bad">${{r.customer}} T</span>`;
      else if (r.customer > 14) custPill = `<span class="pill pill-warn">${{r.customer}} T</span>`;
      else                      custPill = `<span class="pill pill-good">${{r.customer}} T</span>`;

      // Rechnung → Bezahlt = ECHTE Kunden-DSO ab Rechnungsstellung
      let invPill;
      if (r.invoice === null)        invPill = `<span class="pill" style="background:var(--grey-bg);color:var(--grey-2);">—</span>`;
      else if (r.invoice > 30)       invPill = `<span class="pill pill-bad">${{r.invoice}} T</span>`;
      else if (r.invoice > 14)       invPill = `<span class="pill pill-warn">${{r.invoice}} T</span>`;
      else                           invPill = `<span class="pill pill-good">${{r.invoice}} T</span>`;

      // Vereinbartes Zahlungsziel (nur Anzeige, neutral)
      let termPill;
      if (r.payTerm === null)        termPill = `<span class="pill" style="background:var(--grey-bg);color:var(--grey-2);">—</span>`;
      else if (r.payTerm === 0)      termPill = `<span class="pill" style="background:rgba(0,113,227,0.10);color:var(--blue);">Vorkasse</span>`;
      else                           termPill = `<span class="pill" style="background:var(--grey-bg);color:var(--black);">${{r.payTerm}} T</span>`;

      // Überschreitung — DIE entscheidende Mahn-Kennzahl
      let overPill;
      if (r.targetDelay === null)        overPill = `<span class="pill" style="background:var(--grey-bg);color:var(--grey-2);">—</span>`;
      else if (r.targetDelay <= 0)       overPill = `<span class="pill pill-good">${{r.targetDelay}} T</span>`;  // pünktlich oder früh
      else if (r.targetDelay <= 7)       overPill = `<span class="pill pill-warn">+${{r.targetDelay}} T</span>`;
      else if (r.targetDelay <= 30)      overPill = `<span class="pill pill-bad">+${{r.targetDelay}} T</span>`;
      else                               overPill = `<span class="pill pill-bad" style="background:rgba(255,59,48,0.22);">+${{r.targetDelay}} T</span>`;

      // Gesamt-Cycle-Pill — Schwellen über der 30-T-Lieferantenfrist (alle Geräte sind >30T per Definition):
      //   31-45 mid (kurz drüber) · 46-60 warn (bemerkbar) · 61-90 bad (schlimm) · >90 dunkelrot (kritisch)
      let cyclePill;
      if (r.cycle > 90)      cyclePill = `<span class="pill pill-bad" style="background:rgba(255,59,48,0.22);">${{r.cycle}} T</span>`;
      else if (r.cycle > 60) cyclePill = `<span class="pill pill-bad">${{r.cycle}} T</span>`;
      else if (r.cycle > 45) cyclePill = `<span class="pill pill-warn">${{r.cycle}} T</span>`;
      else                   cyclePill = `<span class="pill pill-mid">${{r.cycle}} T</span>`;

      return `<tr>
        <td class="bold">${{r.kunde}}</td>
        <td>${{r.lager}}</td>
        <td>${{r.brand}}</td>
        <td>${{r.product}}</td>
        <td>${{r.lieferant}}</td>
        <td>${{r.sold}}</td>
        <td>${{r.we}}</td>
        <td>${{r.paid}}</td>
        <td class="right">${{lagerPill}}</td>
        <td class="right">${{custPill}}</td>
        <td class="right">${{invPill}}</td>
        <td class="right">${{termPill}}</td>
        <td class="right">${{overPill}}</td>
        <td class="right">${{cyclePill}}</td>
        <td class="right">${{fmtE(r.ek)}}</td>
        <td class="right bold">${{fmtN(Math.round(r.eurd))}}</td>
        <td>${{r.order}}</td>
      </tr>`;
    }}).join('');
  }}

  // Info
  document.getElementById('show-from').textContent = filtered.length ? from+1 : 0;
  document.getElementById('show-to').textContent = to;
  document.getElementById('show-total').textContent = fmtN(filtered.length);
  document.getElementById('page-current').textContent = state.page;
  document.getElementById('page-total').textContent = totalPages;

  // Pagination
  const p = document.getElementById('pagination');
  p.innerHTML = '';
  const prev = document.createElement('button'); prev.textContent = '‹'; prev.disabled = state.page<=1;
  prev.onclick = () => {{ state.page--; render(); }};
  p.appendChild(prev);
  let pages = [];
  if (totalPages <= 7) {{ for (let i=1; i<=totalPages; i++) pages.push(i); }}
  else {{
    pages.push(1);
    if (state.page > 3) pages.push('…');
    for (let i=Math.max(2,state.page-1); i<=Math.min(totalPages-1,state.page+1); i++) pages.push(i);
    if (state.page < totalPages-2) pages.push('…');
    pages.push(totalPages);
  }}
  pages.forEach(pg => {{
    const b = document.createElement('button');
    b.textContent = pg;
    if (pg === '…') {{ b.disabled = true; b.style.border = 'none'; b.style.background = 'transparent'; }}
    else {{
      if (pg === state.page) b.classList.add('active');
      b.onclick = () => {{ state.page = pg; render(); }};
    }}
    p.appendChild(b);
  }});
  const next = document.createElement('button'); next.textContent = '›'; next.disabled = state.page>=totalPages;
  next.onclick = () => {{ state.page++; render(); }};
  p.appendChild(next);

  // Sort-Indicator
  document.querySelectorAll('th[data-key]').forEach(th => {{
    th.classList.toggle('sorted', th.dataset.key === state.sort.key);
    const arr = th.querySelector('.arrow');
    if (th.dataset.key === state.sort.key) arr.textContent = state.sort.dir === 'asc' ? '▴' : '▾';
    else arr.textContent = '▾';
  }});
}}

// Filter-Events
document.getElementById('f-kunde').addEventListener('input', e => {{
  state.filter.kunde = e.target.value.toLowerCase();
  document.querySelectorAll('.chip').forEach(c => c.classList.remove('active'));
  state.page = 1; render();
}});
document.getElementById('f-supply').addEventListener('input', e => {{
  state.filter.supply = e.target.value.toLowerCase();
  state.page = 1; render();
}});
document.getElementById('f-maxlager').addEventListener('input', e => {{
  state.filter.maxLager = e.target.value;
  state.page = 1; render();
}});
['f-lieferant','f-product','f-brand','f-date-from','f-date-to'].forEach(id => {{
  document.getElementById(id).addEventListener('change', e => {{
    const k = id.replace('f-','').replace('-','');
    const map = {{'lieferant':'lieferant','product':'product','brand':'brand','datefrom':'dateFrom','dateto':'dateTo'}};
    state.filter[map[k]] = e.target.value;
    state.page = 1; render();
  }});
}});

// Sort
document.querySelectorAll('th[data-key]').forEach(th => {{
  th.addEventListener('click', () => {{
    const key = th.dataset.key;
    if (state.sort.key === key) state.sort.dir = state.sort.dir === 'asc' ? 'desc' : 'asc';
    else {{ state.sort.key = key; state.sort.dir = ['delay','ek','eurd'].includes(key) ? 'desc' : 'asc'; }}
    render();
  }});
}});

function resetFilters() {{
  // Reset = zurück zum Default „2026 aktiv · Hauptlieferanten"
  state.filter = {{ kunde:'', lieferant:'', product:'', brand:'', supply:'', dateFrom:'2026-01-01', dateTo:'2026-12-31', maxLager:'60', onlyDrehend:true }};
  document.getElementById('f-kunde').value = '';
  document.getElementById('f-lieferant').value = '';
  document.getElementById('f-product').value = '';
  document.getElementById('f-brand').value = '';
  document.getElementById('f-supply').value = '';
  document.getElementById('f-date-from').value = '2026-01-01';
  document.getElementById('f-date-to').value = '2026-12-31';
  document.getElementById('f-maxlager').value = '60';
  document.getElementById('f-drehend').checked = true;
  document.querySelectorAll('.chip').forEach(c => c.classList.remove('active'));
  document.querySelectorAll('.qf-btn').forEach((b,i) => b.classList.toggle('active', i===0));
  state.page = 1; render();
}}

function exportCSV() {{
  const filtered = sortData(applyFilters());
  const headers = ['Kunde','Lager-Nr','Brand','Produkt','Lieferant','Supply','Verkauf','WE','Rechnungsdatum','Bezahlt','Lager_T','VerkBez_T','RechnBez_T','Zahlungsziel_T','UeberschrittenZiel_T','Cycle_T','EK_EUR','EUR_Tage','Grade','Auftrag','RechnungsNr'];
  const headers2 = headers;
  const rows2 = filtered.map(r => [r.kunde,r.lager,r.brand,r.product,r.lieferant,r.supply,r.sold,r.we,r.invDate,r.paid,r.lagerD,r.customer,r.invoice??'',r.payTerm??'',r.targetDelay??'',r.cycle,r.ek,Math.round(r.eurd),r.grade,r.order,r.invNr].map(v=>`"${{String(v).replace(/"/g,'""')}}"`).join(';'));
  const csv = '\\uFEFF' + headers2.join(';') + '\\n' + rows2.join('\\n');
  const blob = new Blob([csv], {{type:'text/csv;charset=utf-8'}});
  const a = document.createElement('a'); a.href = URL.createObjectURL(blob);
  a.download = 'Schuldner_export_' + new Date().toISOString().slice(0,10) + '.csv';
  a.click();
}}

function applyQuickFilter(preset, evt) {{
  document.querySelectorAll('.qf-btn').forEach(b => b.classList.remove('active'));
  if (evt && evt.target) evt.target.classList.add('active');

  let dateFrom = '', dateTo = '', maxLager = '', onlyDrehend = true;
  if (preset === '2026-active') {{
    dateFrom = '2026-01-01'; dateTo = '2026-12-31'; maxLager = '60'; onlyDrehend = true;
  }} else if (preset === 'q1-2026') {{
    dateFrom = '2026-01-01'; dateTo = '2026-03-31'; maxLager = '60'; onlyDrehend = true;
  }} else if (preset === '2025-active') {{
    dateFrom = '2025-01-01'; dateTo = '2025-12-31'; maxLager = '60'; onlyDrehend = true;
  }} else if (preset === 'letzte-30') {{
    const heute = new Date('2026-05-12');
    const vor30 = new Date(heute); vor30.setDate(heute.getDate()-30);
    dateFrom = vor30.toISOString().slice(0,10);
    dateTo = heute.toISOString().slice(0,10);
    maxLager = '60'; onlyDrehend = true;
  }} else {{  // 'all-incl-altlast'
    dateFrom = ''; dateTo = ''; maxLager = ''; onlyDrehend = false;
  }}

  state.filter.dateFrom = dateFrom;
  state.filter.dateTo = dateTo;
  state.filter.maxLager = maxLager;
  state.filter.onlyDrehend = onlyDrehend;
  document.getElementById('f-date-from').value = dateFrom;
  document.getElementById('f-date-to').value = dateTo;
  document.getElementById('f-maxlager').value = maxLager;
  document.getElementById('f-drehend').checked = onlyDrehend;
  state.page = 1;
  render();
}}

// Drehend-Checkbox separat
document.getElementById('f-drehend').addEventListener('change', e => {{
  state.filter.onlyDrehend = e.target.checked;
  state.page = 1; render();
}});

// Default beim Page-Load: 2026 aktiv · Hauptlieferanten · ≤60T
function initDefaultFilter() {{
  state.filter.dateFrom = '2026-01-01';
  state.filter.dateTo = '2026-12-31';
  state.filter.maxLager = '60';
  state.filter.onlyDrehend = true;
  document.getElementById('f-date-from').value = '2026-01-01';
  document.getElementById('f-date-to').value = '2026-12-31';
  document.getElementById('f-maxlager').value = '60';
  document.getElementById('f-drehend').checked = true;
}}
initDefaultFilter();

function toggleHelp() {{
  const panel = document.getElementById('help-panel');
  const overlay = document.getElementById('help-overlay');
  panel.classList.toggle('open');
  overlay.classList.toggle('open');
}}
document.addEventListener('keydown', e => {{
  if (e.key === 'Escape') {{
    const p = document.getElementById('help-panel');
    if (p.classList.contains('open')) toggleHelp();
  }}
}});

render();
</script>
</body></html>'''

html = html.replace('{{TOTAL}}', f'{len(records):,}'.replace(',', '.')).replace('{{PERIODE}}', str(PERIODE_TAGE))
out_html.write_text(html, encoding='utf-8')
print(f'\n  ✓ Dashboard: {out_html}')
print(f'    Größe: {out_html.stat().st_size / 1024 / 1024:.1f} MB')
print(f'    {len(records):,} Geräte interaktiv filterbar')
