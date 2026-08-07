"""
WE → Bezahlt — NEU mit Master-Files
==============================================================================
Quellen:
  • All-Sold-Apr2025-Apr2026.xlsx       → Verkäufe (12 Monate)
  • Stock_Received_Apr2025-Apr2026.xlsx → WE-Datum pro Lager-Nr (12 Monate)
  • JTL-Export-Aufträge-11052026.csv    → Bezahlt-Datum
==============================================================================
"""
import sys, io, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', line_buffering=True)
from pathlib import Path
import pandas as pd

USERHOME = Path(os.environ.get('USERPROFILE', os.path.expanduser('~')))
DL = USERHOME / 'Downloads'

ALL_SOLD_MASTER = DL / 'All-Sold-Apr2025-Apr2026.xlsx'
STOCK_RECEIVED  = DL / 'Stock_Received_April_2025_April_2026.xlsx'
JTL_FILE        = r'W:\DUSTIN EXPORTE 2026\JTL-Export-Aufträge-11052026.csv'

print('='*78)
print('  STEP 1 — All-Sold Master (Apr 2025 – Apr 2026)')
print('='*78)
sold = pd.read_excel(ALL_SOLD_MASTER)
sold['sold_dt'] = pd.to_datetime(sold['Date'], errors='coerce').dt.normalize()
sold['lager_nr_str'] = sold['Lager Nr.'].astype(str).str.strip().str.replace(r'\.0+$', '', regex=True)
# Deduplizieren auf Lager-Nr (gleiche wie früher)
sold = sold.drop_duplicates(subset=['lager_nr_str'], keep='first').copy()
print(f'  Verkäufe gesamt: {len(sold):,}')
print(f'  Range: {sold["sold_dt"].min().date()} – {sold["sold_dt"].max().date()}')

print('\n='*1 + '='*78)
print('  STEP 2 — Stock-Received Master = NEUE PRIMÄRE WE-QUELLE')
print('='*78)
stock = pd.read_excel(STOCK_RECEIVED)
stock['we_dt'] = pd.to_datetime(stock['DateTime'], errors='coerce').dt.normalize()
stock['lager_nr_str'] = stock['Lager ID'].astype(str).str.strip().str.replace(r'\.0+$', '', regex=True)
# Deduplizieren — pro Lager-Nr frühester WE-Eintrag
stock_wd = (stock.dropna(subset=['we_dt', 'lager_nr_str'])
           .sort_values('we_dt')
           .drop_duplicates('lager_nr_str', keep='first')
           [['lager_nr_str', 'we_dt']])
print(f'  Wareneingänge: {len(stock):,}  → unique Lager-Nrn: {len(stock_wd):,}')
print(f'  WE-Datum-Range: {stock_wd["we_dt"].min().date()} – {stock_wd["we_dt"].max().date()}')

print('\n' + '='*78)
print('  STEP 3 — JTL Bezahlt-Datum')
print('='*78)
jtl = pd.read_csv(JTL_FILE, sep=';', encoding='iso-8859-1', low_memory=False)
jtl['Bezahlt_dt'] = pd.to_datetime(jtl['Datum Zahlungseingang'], errors='coerce', dayfirst=True)
jtl['Auftrag_dt'] = pd.to_datetime(jtl['Auftragsdatum'], errors='coerce', dayfirst=True)
jtl['lager_nr_str'] = jtl['Artikelnummer'].astype(str).str.strip().str.replace(r'\.0+$', '', regex=True)
jtl_per_lager = (jtl.dropna(subset=['Auftrag_dt', 'lager_nr_str'])
                 .sort_values('Auftrag_dt')
                 .drop_duplicates('lager_nr_str', keep='first')
                 [['lager_nr_str', 'Auftrag_dt', 'Bezahlt_dt']])
print(f'  JTL: {len(jtl):,} Aufträge · {len(jtl_per_lager):,} unique Lager-Nrn')
print(f'  Bezahlt-Range: {jtl["Bezahlt_dt"].min().date()} – {jtl["Bezahlt_dt"].max().date()}')

print('\n' + '='*78)
print('  STEP 4 — Master-Join')
print('='*78)
m = sold.merge(stock_wd, on='lager_nr_str', how='left')
m = m.merge(jtl_per_lager, on='lager_nr_str', how='left')
m['t_we_to_sold']   = (m['sold_dt']    - m['we_dt']).dt.days
m['t_sold_to_paid'] = (m['Bezahlt_dt'] - m['sold_dt']).dt.days
m['t_we_to_paid']   = (m['Bezahlt_dt'] - m['we_dt']).dt.days

# === Coverage gesamt ===
n_we   = m['we_dt'].notna().sum()
n_paid = m['Bezahlt_dt'].notna().sum()
n_both = (m['we_dt'].notna() & m['Bezahlt_dt'].notna()).sum()
n_plaus= ((m['t_we_to_paid']>=-3) & (m['t_we_to_paid']<=1500)).sum()
N = len(m)
print(f'\n  Verkäufe gesamt:             {N:,}')
print(f'  WE-Datum verfügbar:          {n_we:>6,}  ({n_we/N*100:.1f}%)')
print(f'  Bezahlt-Datum verfügbar:     {n_paid:>6,}  ({n_paid/N*100:.1f}%)')
print(f'  BEIDE:                       {n_both:>6,}  ({n_both/N*100:.1f}%)')
print(f'  Plausibel (Outlier-frei):    {n_plaus:>6,}  ({n_plaus/N*100:.1f}%)  ★')

# === Coverage pro Monat — drehende Ware ===
DREHEND = ['OTTO_MIX', 'AEG_Schrott']
m['sold_month'] = m['sold_dt'].dt.to_period('M').astype(str)
md = m[m['Supply Type'].isin(DREHEND)].copy()
md['has_chain'] = (md['we_dt'].notna() & md['Bezahlt_dt'].notna()
                  & (md['t_we_to_paid']>=-3) & (md['t_we_to_paid']<=1500))
print(f'\n  Coverage pro Monat (drehende Ware OTTO_MIX + AEG_Schrott):')
print(f'  {"Monat":<10}{"n":>8}{"WE":>10}{"Bezahlt":>10}{"Beide":>10}{"Coverage":>10}')
for mo in sorted(md['sold_month'].unique()):
    sub = md[md['sold_month']==mo]
    n = len(sub)
    nw = sub['we_dt'].notna().sum()
    np_ = sub['Bezahlt_dt'].notna().sum()
    nb = sub['has_chain'].sum()
    cov = nb/n*100 if n else 0
    flag = ' ✓✓' if cov>=95 else (' ✓' if cov>=85 else ('  ⚠' if cov>=70 else '  ✗'))
    print(f'  {mo:<10}{n:>8,}{nw:>9,}{np_:>9,}{nb:>9,}{cov:>9.1f}%{flag}')

# === Bestimme belastbare Periode ===
print('\n' + '='*78)
print('  STEP 5 — Bestimme belastbare Periode (Coverage ≥ 85%)')
print('='*78)
monthly = md.groupby('sold_month').agg(n=('sold_dt','count'), n_chain=('has_chain','sum'))
monthly['cov'] = monthly['n_chain']/monthly['n']*100
clean_months = monthly[monthly['cov']>=85].index.tolist()
if clean_months:
    start_period = sorted(clean_months)[0]
    end_period   = sorted(clean_months)[-1]
    print(f'  Belastbare Monate: {start_period} – {end_period}')
    print(f'  Anzahl belastbare Monate: {len(clean_months)}')
else:
    print('  Keine Monate mit ≥85% Coverage')

# === Output speichern ===
out = USERHOME / 'Downloads' / 'we_to_paid_MASTER.csv'
cols = ['lager_nr_str', 'Supply Type', 'sold_dt', 'we_dt',
        'Auftrag_dt', 'Bezahlt_dt', 't_we_to_sold', 't_sold_to_paid', 't_we_to_paid',
        'JTL Selling Price', 'Portal Buying Price', 'Profit', 'Invoice Paid', 'Invoice Date']
m[[c for c in cols if c in m.columns]].to_csv(out, sep=';', encoding='utf-8-sig', index=False)
print(f'\n  ✓ Master-CSV: {out}')

# === Quick-Stats pro Lieferant (für strikten Filter Validation) ===
print('\n' + '='*78)
print('  STEP 6 — Validation: pro Lieferant')
print('='*78)
v = m[(m['t_we_to_paid']>=-3) & (m['t_we_to_paid']<=1500)].copy()
sup_v = v.groupby('Supply Type').agg(
    n=('t_we_to_paid','count'),
    we_sold_med=('t_we_to_sold','median'),
    we_sold_p75=('t_we_to_sold', lambda x: x.quantile(0.75)),
    we_paid_med=('t_we_to_paid','median'),
).sort_values('n', ascending=False).head(15)
# Coverage pro Lieferant
sup_v['portal_n'] = m.groupby('Supply Type').size().reindex(sup_v.index)
sup_v['cov'] = sup_v['n']/sup_v['portal_n']*100
print(sup_v.round(1).to_string())
