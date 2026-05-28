"""Schnell-Debug: warum 0 Matches für palette_otto?"""
import sys, io, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', line_buffering=True)
from pathlib import Path
import pandas as pd

USERHOME = Path(os.environ.get('USERPROFILE', os.path.expanduser('~')))
stock = pd.read_excel(USERHOME/'Downloads'/'Stock_Received_April_2025_April_2026.xlsx')
sold = pd.read_excel(USERHOME/'Downloads'/'All-Sold-Apr2025-Apr2026.xlsx')

po = stock[stock['Supply Type']=='palette_otto'].copy()
print(f'palette_otto Einträge: {len(po):,}')
print(f'\nErste 10 Lager IDs:')
print(po[['Lager ID','Brand','Product','Article','Product Group','DateTime']].head(10).to_string(index=False))
print(f'\nLager ID Range: {po["Lager ID"].min()} – {po["Lager ID"].max()}')
print(f'Brand-Verteilung:')
print(po['Brand'].value_counts().head(20).to_string())
print(f'\nProduct Group:')
print(po['Product Group'].value_counts().head(20).to_string())

# Versuche Match anders
print(f'\nLager IDs aus palette_otto-Stock in All-Sold suchen…')
po_ids = po['Lager ID'].unique()
sold_match = sold[sold['Lager Nr.'].isin(po_ids)]
print(f'  Match auf Lager Nr.: {len(sold_match):,}')

if len(sold_match):
    print(f'\n  Beispiele:')
    print(sold_match[['Lager Nr.','Brand','Product Group','Supply Type','Date']].head(10).to_string(index=False))
    print(f'\n  Supply Type-Verteilung in den verkauften palette_otto-Geräten:')
    print(sold_match['Supply Type'].value_counts().to_string())
