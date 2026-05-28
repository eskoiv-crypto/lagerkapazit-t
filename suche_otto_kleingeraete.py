"""
Suche nach OTTO_Kleingeräte / Ohrdruf in allen Datenquellen
"""
import sys, io, os, glob
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', line_buffering=True)
from pathlib import Path
import pandas as pd

USERHOME = Path(os.environ.get('USERPROFILE', os.path.expanduser('~')))

print('='*72)
print('  CHECK 1: Alle Supply Types in All-Sold-Master')
print('='*72)
sold = pd.read_excel(USERHOME/'Downloads'/'All-Sold-Apr2025-Apr2026.xlsx')
all_supply_types = sold['Supply Type'].value_counts()
print(f'\n  Total Unique Supply Types: {len(all_supply_types)}')
print('\n  Alle Supply Types sortiert nach Häufigkeit:')
for s, n in all_supply_types.items():
    flag = ' ← OTTO!' if 'otto' in str(s).lower() else ''
    flag = ' ← OHRDRUF!' if 'ohrdruf' in str(s).lower() else flag
    flag = ' ← KLEIN!' if 'klein' in str(s).lower() else flag
    print(f'    {n:>6,}  {s}{flag}')

print('\n' + '='*72)
print('  CHECK 2: Suche im "Supply"-Feld (Bestell-Referenz)')
print('='*72)
sold['Supply'] = sold['Supply'].astype(str)
matches = sold[sold['Supply'].str.lower().str.contains('ohrdruf|kleingeräte|kleingerate', regex=True, na=False)]
print(f'  Treffer in Supply-Feld: {len(matches):,}')
if len(matches):
    print(f'  Supply-Werte mit Match:')
    print(matches['Supply'].value_counts().head(20).to_string())
    print(f'\n  Zugeordnete Supply Types:')
    print(matches['Supply Type'].value_counts().head(10).to_string())

print('\n' + '='*72)
print('  CHECK 3: Suche in Stock-Received-Master')
print('='*72)
stock = pd.read_excel(USERHOME/'Downloads'/'Stock_Received_April_2025_April_2026.xlsx')
print(f'  Total Records: {len(stock):,}')
print(f'  Supply Types in Stock-Received:')
for s, n in stock['Supply Type'].value_counts().items():
    flag = ' ← OTTO!' if 'otto' in str(s).lower() else ''
    flag = ' ← OHRDRUF!' if 'ohrdruf' in str(s).lower() else flag
    flag = ' ← KLEIN!' if 'klein' in str(s).lower() else flag
    print(f'    {n:>6,}  {s}{flag}')

# Supply-Feld
stock['Supply'] = stock['Supply'].astype(str)
matches2 = stock[stock['Supply'].str.lower().str.contains('ohrdruf|kleingeräte|kleingerate', regex=True, na=False)]
print(f'\n  Treffer für "Ohrdruf/Kleingeräte" im Supply-Feld: {len(matches2):,}')
if len(matches2):
    print(matches2['Supply'].value_counts().head(10).to_string())

print('\n' + '='*72)
print('  CHECK 4: Suche in WP-Pipeline (Wareneingang)')
print('='*72)
wp_files = list((USERHOME/'OneDrive - elvinci.de GmbH'/'elvinci - WE Pipeline elvinci').glob('WARENEINGANG_PIPELINE*.csv'))
wp_files.append(USERHOME/'Downloads'/'WARENEINGANG_PIPELINE_optimiert(Wareneingänge) (8).csv')
all_wp = []
for f in wp_files:
    try:
        df = pd.read_csv(f, sep=';', encoding='cp1252', low_memory=False)
        df['file'] = f.name
        all_wp.append(df)
    except Exception:
        try:
            df = pd.read_csv(f, sep=';', encoding='iso-8859-1', low_memory=False)
            df['file'] = f.name
            all_wp.append(df)
        except: pass
wp = pd.concat(all_wp, ignore_index=True)
print(f'  Total WP-Records: {len(wp):,}')

# Suche in allen Text-Spalten
text_cols = [c for c in wp.columns if wp[c].dtype == object]
for col in text_cols:
    series = wp[col].astype(str).str.lower()
    mask = series.str.contains('ohrdruf|kleingerät|kleingerat', regex=True, na=False)
    if mask.sum() > 0:
        print(f'\n  Spalte "{col}" hat {mask.sum()} Treffer:')
        print(wp[mask][[col,'file']].head(15).to_string(index=False))

print('\n' + '='*72)
print('  CHECK 5: Wie ähnliche Supply Types existieren? (Liste anderer Lieferanten)')
print('='*72)
print('  Alle Supply Types mit "Otto" oder "Klein" oder "Ohr":')
matches5 = [s for s in sold['Supply Type'].unique() if any(t in str(s).lower() for t in ['otto','klein','ohr'])]
for s in sorted(matches5):
    n = (sold['Supply Type']==s).sum()
    print(f'    {n:>6,}  {s}')

# In Stock-Received auch
matches5_stock = [s for s in stock['Supply Type'].unique() if any(t in str(s).lower() for t in ['otto','klein','ohr'])]
print(f'\n  Im Stock-Received-File:')
for s in sorted(matches5_stock):
    n = (stock['Supply Type']==s).sum()
    print(f'    {n:>6,}  {s}')
