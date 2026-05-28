"""
Validiere alle 6 KPIs im Schuldner-Dashboard
Cross-Check Mittelwerte, Mediane, WC-Berechnung gegen Rohdaten.
"""
import sys, io, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', line_buffering=True)
from pathlib import Path
import pandas as pd
import numpy as np

USERHOME = Path(os.environ.get('USERPROFILE', os.path.expanduser('~')))
m = pd.read_csv(USERHOME/'Downloads'/'we_to_paid_MASTER.csv', sep=';', encoding='utf-8-sig', low_memory=False)
m['sold_dt']    = pd.to_datetime(m['sold_dt'])
m['we_dt']      = pd.to_datetime(m['we_dt'])
m['Bezahlt_dt'] = pd.to_datetime(m['Bezahlt_dt'])
m['Portal Buying Price'] = pd.to_numeric(m['Portal Buying Price'], errors='coerce')

ALL_SOLD = USERHOME / 'Downloads' / 'All-Sold-Apr2025-Apr2026.xlsx'
sold = pd.read_excel(ALL_SOLD, sheet_name='All Sold')
sold['lager_nr_str'] = sold['Lager Nr.'].astype(str).str.strip().str.replace(r'\.0+$', '', regex=True)
sold['Invoice_dt'] = pd.to_datetime(sold['Invoice Date'], errors='coerce').dt.normalize()
inv_lookup = sold[['lager_nr_str','Invoice_dt']].drop_duplicates('lager_nr_str')
m['lager_nr_str'] = m['lager_nr_str'].astype(str)
m = m.merge(inv_lookup, on='lager_nr_str', how='left')
m['t_invoice_to_paid'] = (m['Bezahlt_dt'] - m['Invoice_dt']).dt.days

DREHEND = ['OTTO_MIX','AEG_Schrott','OTTO_Hanseatic','AEG_IT','Gorenje_Mix',
           'OTTO_B_Ware','OTTO_Lagerschäden_Ansbach','OTTO_Jura','Samsung PEDC']

# =============================================================================
print('='*78)
print('  PROBE A — aktuelle Dashboard-Periode (01.07.2025 – 31.03.2026)')
print('='*78)
START = pd.Timestamp('2025-07-01'); END = pd.Timestamp('2026-03-31')

core = m[(m['sold_dt']>=START) & (m['sold_dt']<=END)
       & m['Supply Type'].isin(DREHEND)
       & m['we_dt'].notna() & m['Bezahlt_dt'].notna()
       & (m['t_we_to_paid']>=-3) & (m['t_we_to_paid']<=1500)].copy()

ueb = core[core['t_we_to_paid']>30].copy()
ueb['vorfin_days'] = ueb['t_we_to_paid']-30
ueb['eur_days']    = ueb['Portal Buying Price'].fillna(0) * ueb['vorfin_days']

print(f'\n  Überzogene Geräte (n): {len(ueb):,}  ← Dashboard zeigt 13.247')
print(f'\n  Ø WE → Bezahlt:   Mean {ueb["t_we_to_paid"].mean():>5.1f} T  Median {ueb["t_we_to_paid"].median():>4.0f} T  ← Dashboard 55,7 T / Median 42')
print(f'  Ø Verk. → Bez.:   Mean {ueb["t_sold_to_paid"].mean():>5.1f} T  Median {ueb["t_sold_to_paid"].median():>4.0f} T  ← Dashboard 31,8 T / Median 31')
print(f'  Ø Rechn. → Bez.:  Mean {ueb["t_invoice_to_paid"].mean():>5.1f} T  Median {ueb["t_invoice_to_paid"].median():>4.0f} T  ← Dashboard 21,6 T / Median 22')
print(f'  Ø Lager-Tage:     Mean {ueb["t_we_to_sold"].mean():>5.1f} T  Median {ueb["t_we_to_sold"].median():>4.0f} T  ← Dashboard 23,8 T / Median 7')

print(f'\n  Additivitäts-Check (sollte aufgehen):')
print(f'    Lager Mean {ueb["t_we_to_sold"].mean():.1f} + Verk→Bez Mean {ueb["t_sold_to_paid"].mean():.1f} = {ueb["t_we_to_sold"].mean()+ueb["t_sold_to_paid"].mean():.1f}  vs WE→Bez Mean {ueb["t_we_to_paid"].mean():.1f}')
print(f'    Verk→Bez Mean {ueb["t_sold_to_paid"].mean():.1f} − Rechn→Bez Mean {ueb["t_invoice_to_paid"].mean():.1f} = {ueb["t_sold_to_paid"].mean()-ueb["t_invoice_to_paid"].mean():.1f}  (= mittlerer Rechnungs-Lag nach Verkauf)')

# WC-Berechnung
periode = (core['sold_dt'].max()-core['sold_dt'].min()).days
WC = ueb['eur_days'].sum() / periode
print(f'\n  WC-Beitrag:')
print(f'    Σ EK × Verspätungs-Tage = {ueb["eur_days"].sum():>14,.0f} €-Tage')
print(f'    ÷ Periode {periode} T = {WC:>10,.0f} €  ← Dashboard 104.370 €')
print(f'    × 10% Kontokorrent     = {WC*0.10:>10,.0f} € p.a.  ← Dashboard 10.437 €')

# =============================================================================
print('\n' + '='*78)
print('  PROBE B — MAX. PERIODE (01.04.2025 – 31.03.2026, 12 Monate)')
print('='*78)
START_MAX = pd.Timestamp('2025-04-01'); END_MAX = pd.Timestamp('2026-03-31')

core_max = m[(m['sold_dt']>=START_MAX) & (m['sold_dt']<=END_MAX)
           & m['Supply Type'].isin(DREHEND)
           & m['we_dt'].notna() & m['Bezahlt_dt'].notna()
           & (m['t_we_to_paid']>=-3) & (m['t_we_to_paid']<=1500)].copy()

ueb_max = core_max[core_max['t_we_to_paid']>30].copy()
ueb_max['vorfin_days'] = ueb_max['t_we_to_paid']-30
ueb_max['eur_days']    = ueb_max['Portal Buying Price'].fillna(0) * ueb_max['vorfin_days']

print(f'\n  Total Drehende Verkäufe (Apr-Mär): {(m[(m["sold_dt"]>=START_MAX)&(m["sold_dt"]<=END_MAX)&m["Supply Type"].isin(DREHEND)]).shape[0]:,}')
print(f'  Davon mit voller Datenkette:       {len(core_max):,}')
print(f'  Davon überzogen (>30 T):           {len(ueb_max):,}  ({len(ueb_max)/len(core_max)*100:.1f}%)')

print(f'\n  Ø WE → Bezahlt:   Mean {ueb_max["t_we_to_paid"].mean():>5.1f} T  Median {ueb_max["t_we_to_paid"].median():>4.0f} T')
print(f'  Ø Verk. → Bez.:   Mean {ueb_max["t_sold_to_paid"].mean():>5.1f} T  Median {ueb_max["t_sold_to_paid"].median():>4.0f} T')
print(f'  Ø Rechn. → Bez.:  Mean {ueb_max["t_invoice_to_paid"].mean():>5.1f} T  Median {ueb_max["t_invoice_to_paid"].median():>4.0f} T')
print(f'  Ø Lager-Tage:     Mean {ueb_max["t_we_to_sold"].mean():>5.1f} T  Median {ueb_max["t_we_to_sold"].median():>4.0f} T')

periode_max = (core_max['sold_dt'].max()-core_max['sold_dt'].min()).days
WC_max = ueb_max['eur_days'].sum() / periode_max
print(f'\n  Periode: {periode_max} Tage')
print(f'  WC-Beitrag (Max-Periode): {WC_max:,.0f} €')
print(f'  Kapitalkosten 10% p.a.:   {WC_max*0.10:,.0f} €')

# Coverage pro Monat
print(f'\n  Coverage pro Monat (Apr 2025 – Mär 2026):')
month_data = m[(m['sold_dt']>=START_MAX) & (m['sold_dt']<=END_MAX) & m['Supply Type'].isin(DREHEND)].copy()
month_data['has_chain'] = (month_data['we_dt'].notna() & month_data['Bezahlt_dt'].notna() &
                          (month_data['t_we_to_paid']>=-3) & (month_data['t_we_to_paid']<=1500))
month_data['sold_month'] = month_data['sold_dt'].dt.to_period('M').astype(str)
monthly = month_data.groupby('sold_month').agg(n=('sold_dt','count'), nc=('has_chain','sum'))
monthly['cov'] = monthly['nc']/monthly['n']*100
for mo, r in monthly.iterrows():
    flag = '✓✓' if r["cov"]>=95 else ('✓' if r["cov"]>=85 else ('⚠' if r["cov"]>=70 else '✗'))
    print(f'    {mo}  n={r["n"]:>5,}  chain={int(r["nc"]):>5,}  {r["cov"]:>5.1f}%  {flag}')

print(f'\n  ───── FAZIT ─────')
print(f'  Periode 9 Monate (Jul-Mär):    {len(ueb):,} überzogen, WC {WC:,.0f} €')
print(f'  Periode 12 Monate (Apr-Mär):   {len(ueb_max):,} überzogen, WC {WC_max:,.0f} €')
print(f'  Δ:                              +{len(ueb_max)-len(ueb):,} Geräte, Δ WC {WC_max-WC:+,.0f} €')
