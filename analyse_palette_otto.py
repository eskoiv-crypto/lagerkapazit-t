"""
Analyse: palette_otto in Stock-Received vs. Klassifikation in All-Sold
"""
import sys, io, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', line_buffering=True)
from pathlib import Path
import pandas as pd

USERHOME = Path(os.environ.get('USERPROFILE', os.path.expanduser('~')))

# Stock-Received: alle palette_otto-Lager-Nrn
stock = pd.read_excel(USERHOME/'Downloads'/'Stock_Received_April_2025_April_2026.xlsx')
stock['lager_nr_str'] = stock['Lager ID'].astype(str).str.strip().str.replace(r'\.0+$', '', regex=True)
po = stock[stock['Supply Type']=='palette_otto'].copy()
po_lager_nrn = set(po['lager_nr_str'])
print(f'Stock-Received: palette_otto-Geräte = {len(po):,} unique Lager-Nrn')
print(f'  DateTime-Range: {pd.to_datetime(po["DateTime"]).min()} – {pd.to_datetime(po["DateTime"]).max()}')
print(f'  Produktgruppen-Verteilung:')
print(po['Product Group'].value_counts().head(20).to_string())
print(f'\n  Top-Brands:')
print(po['Brand'].value_counts().head(15).to_string())

# Wie werden diese in All-Sold klassifiziert?
print('\n' + '='*72)
print('Cross-Check: wie sind die palette_otto-Geräte in All-Sold klassifiziert?')
print('='*72)
sold = pd.read_excel(USERHOME/'Downloads'/'All-Sold-Apr2025-Apr2026.xlsx')
sold['lager_nr_str'] = sold['Lager Nr.'].astype(str).str.strip().str.replace(r'\.0+$', '', regex=True)
po_sold = sold[sold['lager_nr_str'].isin(po_lager_nrn)].copy()
print(f'  Davon verkauft (in All-Sold): {len(po_sold):,} ({len(po_sold)/len(po)*100:.1f}% der eingegangenen)')
print(f'\n  Supply Type im verkauften Zustand:')
print(po_sold['Supply Type'].value_counts().to_string())
print(f'\n  Produktgruppen der verkauften palette_otto-Geräte:')
print(po_sold['Product Group'].value_counts().head(15).to_string())

# Wieviele in unserem überzogenen Dashboard-Sample?
print('\n' + '='*72)
print('palette_otto im Dashboard-Sample (überzogene drehende Geräte)')
print('='*72)
master = pd.read_csv(USERHOME/'Downloads'/'we_to_paid_MASTER.csv', sep=';', encoding='utf-8-sig', low_memory=False)
master['sold_dt'] = pd.to_datetime(master['sold_dt'])
master['lager_nr_str'] = master['lager_nr_str'].astype(str)
DREHEND = ['OTTO_MIX','AEG_Schrott','OTTO_Hanseatic','AEG_IT','Gorenje_Mix',
           'OTTO_B_Ware','OTTO_Lagerschäden_Ansbach','OTTO_Jura','Samsung PEDC']
core = master[(master['sold_dt']>=pd.Timestamp('2025-04-01')) & (master['sold_dt']<=pd.Timestamp('2026-03-31'))
            & master['Supply Type'].isin(DREHEND)
            & master['we_dt'].notna() & master['Bezahlt_dt'].notna()
            & (master['t_we_to_paid']>=-3) & (master['t_we_to_paid']<=1500)].copy()
ueb = core[core['t_we_to_paid']>30]
po_in_ueb = ueb[ueb['lager_nr_str'].isin([str(x) for x in po_lager_nrn])]
print(f'  Überzogene Geräte gesamt: {len(ueb):,}')
print(f'  Davon palette_otto:       {len(po_in_ueb):,}  ({len(po_in_ueb)/len(ueb)*100:.2f}%)')
if len(po_in_ueb)>0:
    print(f'\n  Klassifikation der palette_otto im überzogenen Sample:')
    print(po_in_ueb['Supply Type'].value_counts().to_string())
    print(f'\n  Mean WE→Bezahlt: {po_in_ueb["t_we_to_paid"].mean():.1f} T  Median {po_in_ueb["t_we_to_paid"].median():.0f} T')

# Beispiel-Lager-Nrn als Liste exportieren
out_csv = USERHOME / 'Downloads' / 'palette_otto_lager_nrn.csv'
po[['lager_nr_str','DateTime','Brand','Product Group']].to_csv(out_csv, sep=';', encoding='utf-8-sig', index=False)
print(f'\n  ✓ Liste exportiert: {out_csv}')
print(f'    → {len(po):,} Lager-Nrn als palette_otto klassifiziert')
