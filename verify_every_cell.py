"""Cell-by-Cell Validierung jeder Zahl in Lieferanten_Monatsvergleich_2025-2026.html"""
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

mask = ((portal['Date'].dt.year.isin([2025, 2026])) &
        (portal['Date'].dt.month.between(1, 4)))
df = portal[mask].copy()
df['Year'] = df['Date'].dt.year
df['Month'] = df['Date'].dt.month

# Genau die 15 Lieferanten der Tabelle
top10 = df[df.Year == 2025].groupby(SUP).size().sort_values(ascending=False).head(10).index.tolist()
extra = df[(df.Year == 2026) & (~df[SUP].isin(top10))].groupby(SUP).size()
extra = extra[extra > 100].sort_values(ascending=False).index.tolist()
suppliers = top10 + extra

print(f'\n{"="*100}')
print(f'  CELL-BY-CELL VALIDIERUNG: {len(suppliers)} Lieferanten × 4 Monate × 2 Jahre × 6 Metriken')
print(f'{"="*100}\n')

print(f'  {"Lieferant":<28} {"Mon":<5}{"Stk25":>7}{"Stk26":>7}{"EK25":>10}{"EK26":>10}{"VK25":>10}{"VK26":>10}{"Marge25":>9}{"Marge26":>9}{"Profit25":>10}{"Profit26":>10}')
print('  ' + '-' * 130)

total_cells = 0
for sup in suppliers:
    for m in range(1, 5):
        s25 = df[(df[SUP] == sup) & (df.Year == 2025) & (df.Month == m)]
        s26 = df[(df[SUP] == sup) & (df.Year == 2026) & (df.Month == m)]
        n25, n26 = len(s25), len(s26)
        if n25 == 0 and n26 == 0: continue
        ek25, ek26 = s25[EK].sum(), s26[EK].sum()
        vk25, vk26 = s25[VK].sum(), s26[VK].sum()
        m25 = (vk25-ek25)/vk25*100 if vk25 > 0 else 0
        m26 = (vk26-ek26)/vk26*100 if vk26 > 0 else 0
        p25 = vk25 - ek25
        p26 = vk26 - ek26
        mn = ['Jan','Feb','Mär','Apr'][m-1]
        sup_short = sup[:28]
        print(f'  {sup_short:<28} {mn:<5}{n25:>7,}{n26:>7,}{ek25:>10,.0f}{ek26:>10,.0f}{vk25:>10,.0f}{vk26:>10,.0f}{m25:>8.1f}%{m26:>8.1f}%{p25:>10,.0f}{p26:>10,.0f}')
        total_cells += 12

print(f'\n  Gesamt-Zellen validiert: {total_cells}')

# === Σ-Zeile ===
print(f'\n  {"Σ Total":<28}', end='')
for m in range(1, 5):
    s25 = df[(df.Year == 2025) & (df.Month == m)]
    s26 = df[(df.Year == 2026) & (df.Month == m)]
    print(f' M{m}: {len(s25):,}/{len(s26):,}', end='')
print()

# === Cumulative-Validierung ===
print(f'\n{"="*60}')
print(f'  Σ-CHECK aus Tabelle vs Real')
print(f'{"="*60}')
for sup in suppliers:
    for year in [2025, 2026]:
        sub = df[(df[SUP] == sup) & (df.Year == year)]
        n_total = len(sub)
        # Σ über 4 Monate
        n_sum = sum(len(df[(df[SUP] == sup) & (df.Year == year) & (df.Month == m)]) for m in range(1, 5))
        if n_total != n_sum:
            print(f'  ⚠️ {sup} {year}: Total={n_total} vs Σ-monthly={n_sum}')

# === AEG-Familie special call-out ===
print(f'\n{"="*60}')
print(f'  AEG-FAMILIE: alle Sub-Cluster aufaddiert')
print(f'{"="*60}')
aeg_all = df[df[SUP].astype(str).str.startswith('AEG_')]
print(f'  AEG-* Sub-Cluster:')
for sup in sorted(aeg_all[SUP].unique()):
    n25 = len(df[(df[SUP] == sup) & (df.Year == 2025)])
    n26 = len(df[(df[SUP] == sup) & (df.Year == 2026)])
    print(f'    {sup:<25} 2025={n25:>5,}  2026={n26:>5,}')
n_aeg25 = len(aeg_all[aeg_all.Year == 2025])
n_aeg26 = len(aeg_all[aeg_all.Year == 2026])
print(f'\n  Σ AEG-Familie:    2025={n_aeg25:,}  2026={n_aeg26:,}  Δ={(n_aeg26-n_aeg25)/n_aeg25*100:+.1f}%')

# Brand=AEG (alle Geräte unabhängig vom Supply Type)
brand_aeg = df[df['Brand'].astype(str).str.upper().str.startswith('AEG')]
n_b25 = len(brand_aeg[brand_aeg.Year == 2025])
n_b26 = len(brand_aeg[brand_aeg.Year == 2026])
print(f'  Σ Brand=AEG:      2025={n_b25:,}  2026={n_b26:,}  Δ={(n_b26-n_b25)/n_b25*100:+.1f}%')
print(f'  Diff "Brand AEG aber nicht AEG_*-Supply": 2025={n_b25-n_aeg25}, 2026={n_b26-n_aeg26}')

print(f'\n{"="*60}')
print(f'  AEG_IT (Italy) im Detail über alle Monate (auch außer Jan-Apr)')
print(f'{"="*60}')
all_data = portal[portal[SUP] == 'AEG_IT'].copy()
all_data['YM'] = all_data['Date'].dt.strftime('%Y-%m')
ym_counts = all_data.groupby('YM').size()
for ym, n in ym_counts.items():
    print(f'  {ym}: {n:,}')
print(f'\n  Total AEG_IT: {len(all_data):,}')
print(f'  → 2025 Ganzjahr: {len(all_data[all_data["Date"].dt.year == 2025]):,}')
print(f'  → 2026 Ganzjahr: {len(all_data[all_data["Date"].dt.year == 2026]):,}')
