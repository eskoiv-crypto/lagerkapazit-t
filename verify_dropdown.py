"""
Verifiziere alle Lieferanten in allen Datenquellen
"""
import sys, io, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', line_buffering=True)
from pathlib import Path
import pandas as pd

USERHOME = Path(os.environ.get('USERPROFILE', os.path.expanduser('~')))

print('='*78)
print('  Quelle 1: All-Sold-Master')
print('='*78)
sold = pd.read_excel(USERHOME/'Downloads'/'All-Sold-Apr2025-Apr2026.xlsx')
sold_sup = sorted(sold['Supply Type'].dropna().unique())
print(f'  Unique Supply Types: {len(sold_sup)}')
for s in sold_sup:
    n = (sold['Supply Type']==s).sum()
    print(f'    {n:>6,}  {s}')

print('\n' + '='*78)
print('  Quelle 2: Stock-Received-Master')
print('='*78)
stock = pd.read_excel(USERHOME/'Downloads'/'Stock_Received_April_2025_April_2026.xlsx')
stock_sup = sorted(stock['Supply Type'].dropna().unique())
print(f'  Unique Supply Types: {len(stock_sup)}')
for s in stock_sup:
    n = (stock['Supply Type']==s).sum()
    flag = ''
    if s not in sold_sup: flag = '  ← NUR IN STOCK!'
    print(f'    {n:>6,}  {s}{flag}')

print('\n' + '='*78)
print('  Quelle 3: we_to_paid_MASTER.csv (im Dashboard genutzt)')
print('='*78)
m = pd.read_csv(USERHOME/'Downloads'/'we_to_paid_MASTER.csv', sep=';', encoding='utf-8-sig', low_memory=False)
m_sup = sorted(m['Supply Type'].dropna().unique())
print(f'  Unique Supply Types: {len(m_sup)}')
for s in m_sup:
    n = (m['Supply Type']==s).sum()
    print(f'    {n:>6,}  {s}')

# Unique zusammenführen
all_unique = sorted(set(sold_sup) | set(stock_sup))
print('\n' + '='*78)
print('  UNION aller Lieferanten')
print('='*78)
print(f'  Total unique: {len(all_unique)}')
for s in all_unique:
    in_sold = s in sold_sup
    in_stock = s in stock_sup
    in_master = s in m_sup
    tags = []
    if in_sold: tags.append('SOLD')
    if in_stock: tags.append('STOCK')
    if in_master: tags.append('MASTER')
    print(f'    {s:<32}  {", ".join(tags)}')

print('\n  → Vollständige Dropdown-Liste sollte enthalten:')
print(f'    All-Sold-Quelle: {len(sold_sup)} Lieferanten')
print(f'    + Stock-Received zusätzlich: {len(set(stock_sup)-set(sold_sup))} (palette_otto, ggf. Dummy_Type)')
print(f'    = Insgesamt: {len(all_unique)}')

# Welcher kommt im aktuellen Dashboard nicht?
print('\n' + '='*78)
print('  Lieferanten IN HTML-Dashboard (Stand letzter Build)')
print('='*78)
import re
html_file = USERHOME/'Downloads'/'Schuldner_Dashboard.html'
if html_file.exists():
    html_content = html_file.read_text(encoding='utf-8')
    # Suche nach "lieferanten":[...]
    match = re.search(r'"lieferanten":\s*\[(.*?)\]', html_content)
    if match:
        liste = re.findall(r'"([^"]+)"', match.group(1))
        print(f'  Im HTML eingebettet: {len(liste)} Lieferanten')
        for s in liste:
            in_all = s in all_unique
            flag = '' if in_all else '  ← UNBEKANNT'
            print(f'    {s}{flag}')

        missing = set(all_unique) - set(liste)
        if missing:
            print(f'\n  ⚠ Fehlend im HTML: {len(missing)}')
            for s in sorted(missing):
                print(f'    {s}')
        else:
            print('\n  ✓ Alle Lieferanten im HTML enthalten')
