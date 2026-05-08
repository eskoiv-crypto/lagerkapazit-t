"""
LAGERDAUER_CODEX Validierung — vollständiger Cross-Check der Codex-Zahlen
gegen die echten Quelldaten (All-Sold + BESTAND + Stock + Pipelines).

Codex-Stand: 07.05.2026, v25 / v11
Ausführung:  python validate_lagerdauer.py
"""
from __future__ import annotations
import glob, os, re, sys, io
# UTF-8-Output erzwingen (Windows cp1252 kann Σ/€ nicht)
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', line_buffering=True)
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', line_buffering=True)
from datetime import datetime
from pathlib import Path
import pandas as pd

USERHOME = Path(os.environ.get('USERPROFILE', os.path.expanduser('~')))
DEBUG = '--debug' in sys.argv

# === Quelldaten finden ===
ALLSOLD_DIR  = USERHOME / 'Downloads' / 'All Sold 2025 - 2026'
BESTAND_DIR  = USERHOME / 'OneDrive - elvinci.de GmbH' / 'elvinci - Bestandslisten AMM'
STOCK_DIR    = USERHOME / 'OneDrive - elvinci.de GmbH' / 'Digital Experience - KI-Tools' / 'Stock Analysis'
WE_PIPE_DIR  = USERHOME / 'OneDrive - elvinci.de GmbH' / 'elvinci - WE Pipeline elvinci'
FF_PIPE_DIR  = USERHOME / 'OneDrive - elvinci.de GmbH' / 'elvinci - Fulfilment Pipeline elvinci'

allsold_files  = sorted(glob.glob(str(ALLSOLD_DIR / 'All-Sold-2026-05-07T*.xlsx')))
bestand_files  = sorted(glob.glob(str(BESTAND_DIR / 'BESTAND134_*.CSV')))
stock_files    = sorted(glob.glob(str(STOCK_DIR / 'Stock-Analysis-2026-*.xlsx')))
we_pipe_files  = sorted(glob.glob(str(WE_PIPE_DIR / 'WARENEINGANG_PIPELINE*.csv')))
ff_pipe_files  = sorted(glob.glob(str(FF_PIPE_DIR / 'FULFILMENT PIPELINE*.csv')))

print('=' * 70)
print('  LAGERDAUER_CODEX — Validierung')
print('=' * 70)
print(f'\n  All-Sold:        {len(allsold_files)} Files  (Codex: 8)')
print(f'  BESTAND:         {len(bestand_files)} Files  (Codex: 9)')
print(f'  Stock-Analysis:  {len(stock_files)} Files  (Codex: 5)')
print(f'  WE-Pipeline:     {len(we_pipe_files)} Files')
print(f'  FF-Pipeline:     {len(ff_pipe_files)} Files')

results = []

# === All-Sold laden + dedup ===
print('\n--- All-Sold laden + dedup ---')
parts = []
for f in allsold_files:
    df = pd.read_excel(f)
    parts.append(df)
    if DEBUG: print(f'  {Path(f).name}: {len(df)} rows')
portal = pd.concat(parts, ignore_index=True)
n_before = len(portal)
portal = portal.drop_duplicates(subset=['Lager Nr.'], keep='first').copy()
n_after  = len(portal)
print(f'  Total raw:      {n_before:,}')
print(f'  Nach Dedup:     {n_after:,}  (Codex: 92.576)')
results.append(('Portal-Sold n nach Dedup', f'{n_after:,}', '92.576', n_after == 92576))

# Datumsspalte
portal['Date'] = pd.to_datetime(portal['Date'], errors='coerce').dt.normalize()
print(f'  Datums-Range:   {portal["Date"].min().date()} – {portal["Date"].max().date()}')
print(f'  Nicht-parsbar:  {portal["Date"].isna().sum():,}')

# === Headline Jan-Apr 2025 vs 2026 ===
print('\n--- Headline Jan-Apr 2025 vs 2026 ---')
def janapr_slice(df, year):
    return df[(df['Date'] >= f'{year}-01-01') & (df['Date'] <= f'{year}-04-30')]

slc25 = janapr_slice(portal, 2025)
slc26 = janapr_slice(portal, 2026)

# JTL-VK Spalte: bei Codex "JTL Selling Price" — finden
vk_col = None
ek_col = None
for col in portal.columns:
    cl = col.lower()
    if 'jtl' in cl and 'sell' in cl: vk_col = col
    if 'buying' in cl: ek_col = col
print(f'  VK-Spalte (JTL): {vk_col}')
print(f'  EK-Spalte:       {ek_col}')

def kpis(df, label):
    n = len(df)
    ek_sum = df[ek_col].sum() if ek_col else 0
    vk_sum = df[vk_col].sum() if vk_col else 0
    profit = vk_sum - ek_sum
    marge_vk = (profit / vk_sum * 100) if vk_sum > 0 else 0
    avg_profit = profit / n if n > 0 else 0
    print(f'\n  {label}:')
    print(f'    n        = {n:,}')
    print(f'    EK Σ     = {ek_sum:>10,.0f} €')
    print(f'    VK Σ     = {vk_sum:>10,.0f} €')
    print(f'    Profit Σ = {profit:>10,.0f} €')
    print(f'    Marge VK = {marge_vk:>5.2f} %')
    print(f'    Ø Profit = {avg_profit:>5.2f} €')
    return dict(n=n, ek=ek_sum, vk=vk_sum, profit=profit, marge=marge_vk, avg_profit=avg_profit)

k25 = kpis(slc25, 'Jan-Apr 2025')
k26 = kpis(slc26, 'Jan-Apr 2026')

print('\n  --- Codex-Vergleich Jan-Apr ---')
print(f'  {"Kennzahl":<25}{"Codex":>15}{"Real":>15}  {"Verdict"}')
print('  ' + '-' * 70)
def cmp(label, codex_val, real_val, fmt='{:,.0f}', tolerance=0.01):
    cv = float(str(codex_val).replace('.', '').replace(',', '.').replace('k €', '').replace('%', '').strip())
    if isinstance(real_val, str): rv = float(real_val.replace(',', '.'))
    else: rv = real_val
    diff = abs(cv - rv) / cv if cv != 0 else abs(rv)
    ok = diff < tolerance
    verdict = '✓' if ok else f'✗  Diff={diff:.1%}'
    print(f'  {label:<25}{fmt.format(cv):>15}{fmt.format(rv):>15}  {verdict}')
    results.append((label, fmt.format(rv), str(codex_val), ok))

cmp('Verkäufe 2025',     '23598',   k25['n'])
cmp('Verkäufe 2026',     '22369',   k26['n'])
cmp('EK Σ 2025 (k€)',    '2209',    k25['ek']/1000, fmt='{:,.0f}')
cmp('EK Σ 2026 (k€)',    '2073',    k26['ek']/1000, fmt='{:,.0f}')
cmp('Profit Σ 2025 (k€)', '1551',   k25['profit']/1000, fmt='{:,.0f}')
cmp('Profit Σ 2026 (k€)', '1460',   k26['profit']/1000, fmt='{:,.0f}')
cmp('Marge VK 2025 %',    '39.9',   k25['marge'], fmt='{:.2f}', tolerance=0.005)
cmp('Marge VK 2026 %',    '41.1',   k26['marge'], fmt='{:.2f}', tolerance=0.005)
cmp('Ø Profit 2025',      '65.74',  k25['avg_profit'], fmt='{:.2f}')
cmp('Ø Profit 2026',      '65.26',  k26['avg_profit'], fmt='{:.2f}')

# === Pro-Monat 2025 vs 2026 ===
print('\n--- Pro-Monat Jan-Apr (Volumen) ---')
for m in range(1, 5):
    n25 = len(slc25[slc25['Date'].dt.month == m])
    n26 = len(slc26[slc26['Date'].dt.month == m])
    delta = (n26 - n25) / n25 * 100 if n25 else 0
    print(f'  M{m:02d}:  2025={n25:>5,}   2026={n26:>5,}   Δ={delta:+.1f}%')

# === Lieferanten-Mix Jan-Apr 25 → 26 ===
print('\n--- Lieferanten-Mix Top 8 (Supply Type) ---')
supply_col = None
for col in portal.columns:
    if col.lower().strip() in ('supply', 'supply type', 'supply_type'): supply_col = col
if not supply_col:
    for col in portal.columns:
        if 'supply' in col.lower(): supply_col = col; break
print(f'  Supply-Spalte:  {supply_col}')
if supply_col:
    grp25 = slc25.groupby(supply_col).agg(stk=(supply_col, 'count'),
                                          ek_sum=(ek_col, 'sum'),
                                          vk_sum=(vk_col, 'sum')).sort_values('stk', ascending=False)
    grp26 = slc26.groupby(supply_col).agg(stk=(supply_col, 'count'),
                                          ek_sum=(ek_col, 'sum'),
                                          vk_sum=(vk_col, 'sum')).sort_values('stk', ascending=False)
    grp25['marge'] = (grp25.vk_sum - grp25.ek_sum) / grp25.vk_sum * 100
    grp26['marge'] = (grp26.vk_sum - grp26.ek_sum) / grp26.vk_sum * 100
    print(f'  Top-8 nach 2025-Volumen:')
    print(f'  {"Lieferant":<25}{"Stk25":>8}{"Stk26":>8}{"ΔStk":>8}{"M25%":>8}{"M26%":>8}{"ΔMpp":>8}')
    print('  ' + '-' * 73)
    for sup in grp25.head(8).index:
        s25 = int(grp25.loc[sup, 'stk'])
        s26 = int(grp26.loc[sup, 'stk']) if sup in grp26.index else 0
        m25 = grp25.loc[sup, 'marge']
        m26 = grp26.loc[sup, 'marge'] if sup in grp26.index else float('nan')
        d_stk = (s26-s25)/s25*100 if s25 else 0
        d_m = m26 - m25 if not pd.isna(m26) else float('nan')
        print(f'  {str(sup)[:25]:<25}{s25:>8,}{s26:>8,}{d_stk:>+7.0f}%{m25:>7.1f}%{m26:>7.1f}%{d_m:>+7.1f}')

# === BESTAND-Snapshots ===
print('\n--- BESTAND-Snapshots ---')
print(f'  {len(bestand_files)} Snapshots in {BESTAND_DIR}')
last_bestand = None
if bestand_files:
    last_bestand_path = bestand_files[-1]
    print(f'  Letzter:  {Path(last_bestand_path).name}')
    bestand = pd.read_csv(last_bestand_path, sep=';', encoding='ISO-8859-1', skiprows=1, header=None)
    last_bestand = bestand
    print(f'  n Zeilen: {len(bestand):,}')
    if len(bestand.columns) >= 11:
        # Status: typischerweise Spalte 9 (0-indexed)
        statusses = bestand.iloc[:, 9].astype(str).str.strip().str.upper().value_counts().head(8)
        print(f'  Status-Verteilung:')
        for s, n in statusses.items(): print(f'    {s:<8} {n:,}')
        # Codex sagt: 6.253 (QE 4.570 · VS 1.629 · AA 54)
        results.append(('BESTAND letzter Snapshot Σ', f'{len(bestand):,}', '6.253', False))

# === Stock-Analysis ===
print('\n--- Stock-Analysis ---')
last_stock = None
if stock_files:
    last_stock_path = sorted(stock_files)[-1]
    print(f'  Letzter:  {Path(last_stock_path).name}')
    stock = pd.read_excel(last_stock_path)
    last_stock = stock
    print(f'  n Zeilen: {len(stock):,}')
    print(f'  Codex 07.05: 3.690')
    # EK-Summe
    if 'Buying_Price' in stock.columns:
        ek_total = stock['Buying_Price'].sum()
        print(f'  EK Σ:     {ek_total:>10,.0f} €  (Codex: 299.936 €)')
    elif ek_col in stock.columns:
        ek_total = stock[ek_col].sum()
        print(f'  EK Σ:     {ek_total:>10,.0f} €  (Codex: 299.936 €)')

# === Hänger-Definitionen ===
print('\n--- Hänger-Definitionen Cross-Check ---')
# Definition 1: 2026er Verkäufe mit lifeDays > 38
if 'product_life_days' in portal.columns:
    lcol = 'product_life_days'
elif 'Product Life Days' in portal.columns:
    lcol = 'Product Life Days'
else:
    lcol = None
print(f'  Lifetime-Spalte: {lcol}')
if lcol:
    sold26 = slc26.copy()
    sold26[lcol] = pd.to_numeric(sold26[lcol], errors='coerce')
    haenger_vergangenheit = sold26[sold26[lcol] > 38]
    h_n = len(haenger_vergangenheit)
    h_pct = h_n / len(slc26) * 100 if len(slc26) else 0
    h_ek = haenger_vergangenheit[ek_col].sum() if ek_col else 0
    print(f'  Vergangenheit (verkauft 2026, >38T): {h_n:,} ({h_pct:.1f}%)  EK={h_ek:,.0f}€')
    print(f'  Codex: 1.436 (10%), 108.749€ EK')
    results.append(('Hänger Vergangenheit', f'{h_n:,}', '1.436', abs(h_n - 1436) / 1436 < 0.05))

# === Total-Volumen-Trend (17-Monats) ===
print('\n--- 17-Monats-Verlauf Σ ---')
total_25_26 = portal[(portal['Date'] >= '2025-01-01') & (portal['Date'] <= '2026-05-31')]
print(f'  n total Σ 25+26: {len(total_25_26):,}')
print(f'  Codex Σ Stk:     92.486')
results.append(('17-Monats Σ Stk', f'{len(total_25_26):,}', '92.486', abs(len(total_25_26) - 92486) / 92486 < 0.01))

vk_total = total_25_26[vk_col].sum() if vk_col else 0
profit_total = vk_total - (total_25_26[ek_col].sum() if ek_col else 0)
print(f'  VK Σ (JTL):      {vk_total/1e6:.2f} Mio €  (Codex: 14.47)')
print(f'  Profit Σ:        {profit_total/1e6:.2f} Mio €  (Codex: 5.81)')
results.append(('VK Σ Mio €', f'{vk_total/1e6:.2f}', '14.47', abs(vk_total/1e6 - 14.47) / 14.47 < 0.01))
results.append(('Profit Σ Mio €', f'{profit_total/1e6:.2f}', '5.81', abs(profit_total/1e6 - 5.81) / 5.81 < 0.01))

# === Final Summary ===
print('\n' + '=' * 70)
print('  ZUSAMMENFASSUNG')
print('=' * 70)
ok = [r for r in results if r[3]]
fail = [r for r in results if not r[3]]
print(f'\n  ✓ {len(ok)} Werte stimmen')
print(f'  ✗ {len(fail)} Werte abweichend')
if fail:
    print(f'\n  Abweichungen:')
    for label, real, codex, _ in fail:
        print(f'    {label:<35}  Real={real:<15}  Codex={codex}')
