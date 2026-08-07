"""Vollständige Validierung der Lieferanten-Monatstabelle + AEG-Italy-Diagnose"""
import sys, io, glob, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', line_buffering=True)
from pathlib import Path
import pandas as pd

USERHOME = Path(os.environ.get('USERPROFILE', os.path.expanduser('~')))
ALLSOLD_DIR = USERHOME / 'Downloads' / 'All Sold 2025 - 2026'

files = sorted(glob.glob(str(ALLSOLD_DIR / 'All-Sold-2026-05-07T*.xlsx')))
portal = pd.concat([pd.read_excel(f) for f in files], ignore_index=True)
portal = portal.drop_duplicates(subset=['Lager Nr.'], keep='first').copy()
portal['Date'] = pd.to_datetime(portal['Date'], errors='coerce').dt.normalize()
portal = portal.dropna(subset=['Date'])

VK = 'JTL Selling Price'; EK = 'Portal Buying Price'; SUP = 'Supply Type'

print('=' * 70)
print('  ALLE Supply-Types (gesamtes 2025+2026)')
print('=' * 70)
mask = ((portal['Date'].dt.year == 2025) | (portal['Date'].dt.year == 2026))
all_sup = portal[mask].groupby(SUP).size().sort_values(ascending=False)
for i, (sup, n) in enumerate(all_sup.items()):
    marker = '  ←' if 'AEG' in str(sup) or 'IT' in str(sup).upper() else ''
    print(f'  {i+1:>3}. {str(sup):<30} {n:>7,}{marker}')

print(f'\n  Total: {len(all_sup)} unterschiedliche Supply-Types, n={all_sup.sum():,}')

print('\n' + '=' * 70)
print('  AEG-Familie: Detail pro Monat')
print('=' * 70)
aeg_types = [s for s in all_sup.index if 'AEG' in str(s)]
print(f'  AEG-Varianten: {aeg_types}\n')

mask2 = ((portal['Date'].dt.year.isin([2025, 2026])) &
         (portal['Date'].dt.month.between(1, 4)))
df = portal[mask2].copy()
df['Year'] = df['Date'].dt.year
df['Month'] = df['Date'].dt.month

print(f'  {"Supply Type":<25}{"Monat":<10}', end='')
print(f'{"2025 Stk":>10}{"2026 Stk":>10}{"M25%":>8}{"M26%":>8}')
print('  ' + '-' * 71)
for at in aeg_types:
    sub = df[df[SUP] == at]
    for m in range(1, 5):
        s25 = sub[(sub.Year == 2025) & (sub.Month == m)]
        s26 = sub[(sub.Year == 2026) & (sub.Month == m)]
        n25, n26 = len(s25), len(s26)
        if n25 == 0 and n26 == 0: continue
        m25 = (s25[VK].sum() - s25[EK].sum()) / s25[VK].sum() * 100 if s25[VK].sum() > 0 else 0
        m26 = (s26[VK].sum() - s26[EK].sum()) / s26[VK].sum() * 100 if s26[VK].sum() > 0 else 0
        month_name = ['Jan','Feb','Mär','Apr'][m-1]
        print(f'  {at:<25}{month_name:<10}{n25:>10,}{n26:>10,}{m25:>7.1f}%{m26:>7.1f}%')

# Auch: Brand=AEG (alle Geräte unabhängig vom Supply Type)
print('\n  Brand=AEG (über alle Supply Types):')
brand = 'Brand'
if brand in df.columns:
    aeg_brand = df[df[brand].astype(str).str.upper().str.startswith('AEG')]
    for m in range(1, 5):
        s25 = aeg_brand[(aeg_brand.Year == 2025) & (aeg_brand.Month == m)]
        s26 = aeg_brand[(aeg_brand.Year == 2026) & (aeg_brand.Month == m)]
        month_name = ['Jan','Feb','Mär','Apr'][m-1]
        print(f'    {month_name}:  2025={len(s25):>5,}  2026={len(s26):>5,}')

print('\n' + '=' * 70)
print('  Welche 15 Lieferanten in der Tabelle sind?')
print('=' * 70)
top10 = df[df.Year == 2025].groupby(SUP).size().sort_values(ascending=False).head(10)
print(f'  Top-10 nach 2025-Volumen (Jan-Apr):')
for i, (sup, n) in enumerate(top10.items()):
    print(f'    {i+1:>2}. {str(sup):<28} {n:>6,}')

# Plus 2026-Einsteiger
extra = df[(df.Year == 2026) & (~df[SUP].isin(top10.index))].groupby(SUP).size()
extra = extra[extra > 100].sort_values(ascending=False)
print(f'\n  + 2026-Einsteiger (>100 Stk Jan-Apr 2026):')
for sup, n in extra.items():
    print(f'    {str(sup):<28} {n:>6,}')

# Was verpassen wir? 2025-Lieferanten unter Top-10 die >100 Stk haben
missed = df[df.Year == 2025].groupby(SUP).size()
missed = missed[(missed > 100) & (~missed.index.isin(top10.index))].sort_values(ascending=False)
print(f'\n  ⚠️ NICHT in Tabelle (2025 >100 Stk Jan-Apr aber nicht Top-10):')
for sup, n in missed.items():
    n26 = len(df[(df.Year == 2026) & (df[SUP] == sup)])
    print(f'    {str(sup):<28} 2025={n:>6,}  2026={n26:>6,}')

# Cross-Check: Σ aller Lieferanten Jan-Apr
print('\n' + '=' * 70)
print('  Σ-Check: Tabelle vs Real')
print('=' * 70)
for m in range(1, 5):
    s25 = df[(df.Year == 2025) & (df.Month == m)]
    s26 = df[(df.Year == 2026) & (df.Month == m)]
    month_name = ['Jan','Feb','Mär','Apr'][m-1]
    print(f'  {month_name}:  2025={len(s25):>5,}  2026={len(s26):>5,}')
print(f'  Σ:    2025={len(df[df.Year==2025]):,}  2026={len(df[df.Year==2026]):,}')
