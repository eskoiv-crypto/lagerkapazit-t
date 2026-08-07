"""Inspiziere die zwei großen Master-Files"""
import sys, io, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', line_buffering=True)
from pathlib import Path
import pandas as pd

USERHOME = Path(os.environ.get('USERPROFILE', os.path.expanduser('~')))
DL = USERHOME / 'Downloads'

print('='*78)
print('FILE A: All-Sold-Apr2025-Apr2026.xlsx')
print('='*78)
all_sold = DL / 'All-Sold-Apr2025-Apr2026.xlsx'
print(f'  Size: {all_sold.stat().st_size:,} B')
xls = pd.ExcelFile(all_sold)
print(f'  Sheets: {xls.sheet_names}')
for sh in xls.sheet_names:
    df = pd.read_excel(all_sold, sheet_name=sh, nrows=5)
    print(f'\n  Sheet "{sh}": {len(pd.read_excel(all_sold, sheet_name=sh)):,} rows × {len(df.columns)} cols')
    for i, c in enumerate(df.columns):
        sample = df[c].dropna().head(2).tolist()
        print(f'    [{i:>2}] {str(c)[:40]:<40}  → {str(sample)[:50]}')

# Volle Anzahl + Date-Range
print('\n  Full load:')
sold = pd.read_excel(all_sold)
print(f'    n: {len(sold):,}')
if 'Date' in sold.columns:
    dt = pd.to_datetime(sold['Date'], errors='coerce')
    print(f'    Date-Range: {dt.min().date()} – {dt.max().date()}')
    print(f'    Verkäufe pro Monat:')
    print(sold.assign(M=dt.dt.to_period('M')).groupby('M').size().to_string())
if 'Supply Type' in sold.columns:
    print(f'    Lieferant-Verteilung:')
    print(sold['Supply Type'].value_counts().head(10).to_string())

print('\n' + '='*78)
print('FILE B: Stock_Received_April_2025_April_2026.xlsx')
print('='*78)
stock_rec = DL / 'Stock_Received_April_2025_April_2026.xlsx'
print(f'  Size: {stock_rec.stat().st_size:,} B')
xls2 = pd.ExcelFile(stock_rec)
print(f'  Sheets: {xls2.sheet_names}')
for sh in xls2.sheet_names:
    full = pd.read_excel(stock_rec, sheet_name=sh)
    df = full.head(5)
    print(f'\n  Sheet "{sh}": {len(full):,} rows × {len(df.columns)} cols')
    for i, c in enumerate(df.columns):
        sample = df[c].dropna().head(2).tolist()
        print(f'    [{i:>2}] {str(c)[:40]:<40}  → {str(sample)[:50]}')

# Welche Spalte ist das WE-Datum?
stock = pd.read_excel(stock_rec)
print('\n  Full load Stock-Received:')
print(f'    n: {len(stock):,}')
date_cols = [c for c in stock.columns if any(t in str(c).lower() for t in ['date', 'datum', 'received', 'upload', 'eingang'])]
for dc in date_cols:
    try:
        dt = pd.to_datetime(stock[dc], errors='coerce')
        if dt.notna().sum() > 0:
            print(f'    {dc}: {dt.min()} – {dt.max()}  (n={dt.notna().sum():,})')
    except Exception:
        pass

# Lager-Nr-Spalte
id_cols = [c for c in stock.columns if any(t in str(c).lower() for t in ['lager', 'number', 'sku', 'artikel'])]
print(f'  ID-Kandidaten: {id_cols}')

# Supplier-Spalte
sup_cols = [c for c in stock.columns if any(t in str(c).lower() for t in ['supply', 'lieferant', 'supplier'])]
print(f'  Supplier-Kandidaten: {sup_cols}')
