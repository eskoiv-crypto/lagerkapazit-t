"""
Finde die Periode mit 100 % belastbarer Coverage.
Pro Verkaufs-Datum: wieviele Geräte mit voller Datenkette?
"""
import sys, io, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', line_buffering=True)
from pathlib import Path
import pandas as pd

USERHOME = Path(os.environ.get('USERPROFILE', os.path.expanduser('~')))
m = pd.read_csv(USERHOME/'Downloads'/'we_to_paid_full_v2.csv', sep=';', encoding='utf-8-sig', low_memory=False)
m['sold_dt']    = pd.to_datetime(m['sold_dt'])
m['we_dt']      = pd.to_datetime(m['we_dt'])
m['Bezahlt_dt'] = pd.to_datetime(m['Bezahlt_dt'])

DREHEND = ['OTTO_MIX', 'AEG_Schrott']
core = m[(m['sold_dt'].dt.year==2026) & (m['Supply Type'].isin(DREHEND))].copy()
core['has_chain'] = (core['we_dt'].notna() & core['Bezahlt_dt'].notna()
                    & (core['t_we_to_paid']>=-3) & (core['t_we_to_paid']<=1500))

# === Coverage pro KALENDERWOCHE ===
core['sold_week'] = core['sold_dt'].dt.to_period('W').astype(str)
weekly = core.groupby('sold_week').agg(
    n=('sold_dt','count'),
    n_chain=('has_chain','sum'),
)
weekly['cov'] = weekly['n_chain']/weekly['n']*100
print('Coverage pro Kalenderwoche (drehende Ware 2026):')
print('  Woche                          n       chain    Cov')
for w, r in weekly.iterrows():
    marker = '  ✓✓' if r['cov']>=95 else ('  ✓' if r['cov']>=90 else ('  ⚠' if r['cov']>=70 else '  ✗'))
    print(f'  {w}     {r["n"]:>6,}   {int(r["n_chain"]):>6,}   {r["cov"]:>5.1f}%{marker}')

# === Coverage pro MONAT ===
print('\nCoverage pro Verkaufs-Monat:')
core['sold_month'] = core['sold_dt'].dt.to_period('M').astype(str)
monthly = core.groupby('sold_month').agg(
    n=('sold_dt','count'),
    n_chain=('has_chain','sum'),
)
monthly['cov'] = monthly['n_chain']/monthly['n']*100
for mo, r in monthly.iterrows():
    print(f'  {mo}    {r["n"]:>6,}    chain {int(r["n_chain"]):>6,}    Coverage {r["cov"]:>5.1f}%')

# === Welche Quellen sind wann verfügbar? ===
print('\nQuellen-Verfügbarkeit (frühste Daten):')
print('  BESTAND-Snapshot 1:    07.04.2026')
print('  WP-Pipeline Files:     09.04.2026 (mit WE-Datum schon ab 22.01.2026 zurück)')
print('  Stock-Analysis File 1: 13.04.2026 (datetime_upload ab 19.10.2021)')
print('  JTL Bezahlt-Datum:     bis 08.05.2026')

# === Empfehlung: ab wann ist die Kette belastbar? ===
threshold = 90
clean_weeks = weekly[weekly['cov'] >= threshold]
print(f'\nWochen mit ≥ {threshold} % Coverage:')
print(clean_weeks.to_string())

if len(clean_weeks):
    first_clean = clean_weeks.index.min()
    print(f'\n→ ERSTE BELASTBARE WOCHE: {first_clean}')

# === Versuche mit Schwelle 80 ===
threshold = 80
print(f'\nWochen mit ≥ {threshold} % Coverage:')
clean_weeks = weekly[weekly['cov'] >= threshold]
print(clean_weeks.to_string())

# === Test: ab Verkaufs-Datum 2026-03-15 ===
for start in ['2026-03-01', '2026-03-15', '2026-04-01', '2026-04-15']:
    sub = core[core['sold_dt'] >= pd.Timestamp(start)]
    n = len(sub)
    n_chain = sub['has_chain'].sum()
    cov = n_chain/n*100 if n else 0
    print(f'  Ab {start}: n={n:,} chain={n_chain:,} Coverage {cov:.1f}%')
