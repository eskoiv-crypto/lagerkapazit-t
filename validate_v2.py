"""V2: Erweiterte Validierung — Profit-Logik klären, Hänger, Verweildauer"""
import sys, io, glob, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', line_buffering=True)
from pathlib import Path
import pandas as pd

USERHOME = Path(os.environ.get('USERPROFILE', os.path.expanduser('~')))
ALLSOLD_DIR = USERHOME / 'Downloads' / 'All Sold 2025 - 2026'
BESTAND_DIR = USERHOME / 'OneDrive - elvinci.de GmbH' / 'elvinci - Bestandslisten AMM'

# Lade + dedup
files = sorted(glob.glob(str(ALLSOLD_DIR / 'All-Sold-2026-05-07T*.xlsx')))
portal = pd.concat([pd.read_excel(f) for f in files], ignore_index=True)
portal = portal.drop_duplicates(subset=['Lager Nr.'], keep='first').copy()
portal['Date'] = pd.to_datetime(portal['Date'], errors='coerce').dt.normalize()

print(f'\n=== ALLE Spalten in All-Sold ===')
for i, col in enumerate(portal.columns):
    print(f'  [{i:2d}] {col}')

# === Profit-Logik genau prüfen ===
print(f'\n=== Profit-Spalte vs VK-EK ===')
slc25 = portal[(portal['Date'] >= '2025-01-01') & (portal['Date'] <= '2025-04-30')]
slc26 = portal[(portal['Date'] >= '2026-01-01') & (portal['Date'] <= '2026-04-30')]

vk_jtl = 'JTL Selling Price'
vk_portal = 'Portal Selling Price' if 'Portal Selling Price' in portal.columns else None
ek = 'Portal Buying Price'
profit_col = next((c for c in portal.columns if c.lower().strip() == 'profit'), None)

print(f'  VK (JTL):      {vk_jtl}')
print(f'  VK (Portal):   {vk_portal}')
print(f'  EK:            {ek}')
print(f'  Profit-Col:    {profit_col}')

for label, df in [('Jan-Apr 2025', slc25), ('Jan-Apr 2026', slc26)]:
    n = len(df)
    vk_jtl_sum = df[vk_jtl].sum()
    vk_portal_sum = df[vk_portal].sum() if vk_portal else 0
    ek_sum = df[ek].sum()
    profit_calc_jtl = vk_jtl_sum - ek_sum
    profit_calc_portal = vk_portal_sum - ek_sum
    profit_spalte = df[profit_col].sum() if profit_col else 0

    print(f'\n  {label} (n={n:,})')
    print(f'    VK JTL    Σ = {vk_jtl_sum:>12,.0f} €')
    print(f'    VK Portal Σ = {vk_portal_sum:>12,.0f} €')
    print(f'    EK        Σ = {ek_sum:>12,.0f} €')
    print(f'    Profit-Spalte         = {profit_spalte:>12,.0f} €')
    print(f'    Profit calc (VK-EK JTL)  = {profit_calc_jtl:>12,.0f} €')
    print(f'    Profit calc (VK-EK Port) = {profit_calc_portal:>12,.0f} €')
    if profit_spalte > 0:
        diff_jtl = profit_spalte - profit_calc_jtl
        diff_port = profit_spalte - profit_calc_portal
        print(f'    → Diff Spalte−calc(JTL)  = {diff_jtl:>+12,.0f} €  ({diff_jtl/n:+.2f} €/Stk)')
        print(f'    → Diff Spalte−calc(Port) = {diff_port:>+12,.0f} €  ({diff_port/n:+.2f} €/Stk)')

# === Verweildauer/Hänger ===
print(f'\n=== Lifetime-Spalten suchen ===')
for col in portal.columns:
    if 'life' in col.lower() or 'days' in col.lower() or 'tag' in col.lower():
        print(f'  Kandidat: {col}')

# === Codex Profit Σ 17-Monate ===
print(f'\n=== 17-Monats-Total ===')
total = portal[(portal['Date'] >= '2025-01-01') & (portal['Date'] <= '2026-05-31')]
print(f'  n           = {len(total):,}')
print(f'  VK JTL Σ    = {total[vk_jtl].sum()/1e6:,.2f} Mio €')
print(f'  EK Σ        = {total[ek].sum()/1e6:,.2f} Mio €')
print(f'  Profit calc = {(total[vk_jtl].sum() - total[ek].sum())/1e6:,.2f} Mio €  (VK-EK)')
if profit_col: print(f'  Profit-Sp.  = {total[profit_col].sum()/1e6:,.2f} Mio €  (Spalte)')

# === Codex-Hänger-Definition prüfen ===
print(f'\n=== Hänger > 38 Tage (2026er Verkäufe) ===')
# Lifetime aus Date - WE-Datum? oder gibt es eine Lifetime-Spalte?
# Wir prüfen mehrere Kandidaten
for cand in ['product_life_days', 'Product Life Days', 'Product life days', 'Verweildauer', 'Tage', 'Days']:
    if cand in portal.columns:
        print(f'  Lifetime-Spalte gefunden: {cand}')
        sold26 = slc26.copy()
        sold26[cand] = pd.to_numeric(sold26[cand], errors='coerce')
        haenger = sold26[sold26[cand] > 38]
        print(f'  > 38 T: {len(haenger):,} ({len(haenger)/len(slc26)*100:.1f}%)')
        print(f'  Codex: 1.436 (10%), 108.749€ EK')
        print(f'  Real EK Σ: {haenger[ek].sum():,.0f} €')
        break
else:
    print('  Keine Lifetime-Spalte gefunden — Codex-Hänger via WP-Pipeline-Match')

# === Cluster-Risk: OTTO-Konzentration ===
print(f'\n=== Konzentrations-Analyse ===')
sup_col = next((c for c in portal.columns if 'supply type' in c.lower()), None)
if sup_col:
    g25 = slc25[sup_col].value_counts()
    g26 = slc26[sup_col].value_counts()
    n25 = len(slc25)
    n26 = len(slc26)
    otto25 = g25.filter(like='OTTO').sum() if any('OTTO' in str(s) for s in g25.index) else 0
    otto26 = g26.filter(like='OTTO').sum() if any('OTTO' in str(s) for s in g26.index) else 0
    print(f'  OTTO-Familie 2025: {otto25:,} / {n25:,} = {otto25/n25*100:.1f}%')
    print(f'  OTTO-Familie 2026: {otto26:,} / {n26:,} = {otto26/n26*100:.1f}%')
    # Top-3-Konzentration
    top3_25 = g25.head(3).sum() / n25 * 100
    top3_26 = g26.head(3).sum() / n26 * 100
    print(f'  Top-3-Konzentration 2025: {top3_25:.1f}%  (Codex sagt 81,8% → 89,0% war falsch)')
    print(f'  Top-3-Konzentration 2026: {top3_26:.1f}%')
