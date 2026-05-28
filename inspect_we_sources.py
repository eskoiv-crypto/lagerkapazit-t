"""Vollständige Inspektion ALLER potentiellen WE-Datum-Quellen"""
import sys, io, glob, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', line_buffering=True)
from pathlib import Path
import pandas as pd

USERHOME = Path(os.environ.get('USERPROFILE', os.path.expanduser('~')))
ALLSOLD_DIR = USERHOME / 'Downloads' / 'All Sold 2025 - 2026'
BESTAND_DIR = USERHOME / 'OneDrive - elvinci.de GmbH' / 'elvinci - Bestandslisten AMM'
WE_PIPE_DIR = USERHOME / 'OneDrive - elvinci.de GmbH' / 'elvinci - WE Pipeline elvinci'
STOCK_DIR   = USERHOME / 'OneDrive - elvinci.de GmbH' / 'Digital Experience - KI-Tools' / 'Stock Analysis'

print('=' * 70)
print('  QUELLE 1: All-Sold (Portal) — alle 26 Spalten genau ansehen')
print('=' * 70)
files = sorted(glob.glob(str(ALLSOLD_DIR / 'All-Sold-2026-05-07T*.xlsx')))
portal = pd.read_excel(files[0], nrows=200)
print(f'  n_cols: {len(portal.columns)}')
for i, c in enumerate(portal.columns):
    sample = portal[c].dropna().head(2).tolist()
    sample_str = str(sample)[:80]
    dtype = portal[c].dtype
    print(f'    [{i:>2}] {c:<28} ({dtype})  Beispiele: {sample_str}')

# Turnover-Spalte deutet auf Lifetime hin — was ist Turnover Ratio?
print('\n  Turnover-Spalten Detail:')
for col in ['Turnover', 'Turnover Ratio']:
    if col in portal.columns:
        s = pd.to_numeric(portal[col], errors='coerce').dropna()
        if len(s) > 0:
            print(f'    {col}: min={s.min():.1f}, mean={s.mean():.1f}, median={s.median():.1f}, max={s.max():.1f}')

# Date vs Invoice Date — gibt es eine Differenz?
print('\n  Date vs Invoice Date Differenz:')
portal['Date_dt'] = pd.to_datetime(portal['Date'], errors='coerce')
portal['Inv_dt'] = pd.to_datetime(portal['Invoice Date'], errors='coerce')
diff = (portal['Inv_dt'] - portal['Date_dt']).dt.days.dropna()
print(f'    n: {len(diff)}, mean: {diff.mean():.1f}T, median: {diff.median():.1f}T')

print('\n' + '=' * 70)
print('  QUELLE 2: BESTAND-Snapshots (AMM)')
print('=' * 70)
bestand_files = sorted(glob.glob(str(BESTAND_DIR / 'BESTAND134_*.CSV')))
print(f'  Files: {len(bestand_files)}')
print(f'  Erster: {Path(bestand_files[0]).name}')
print(f'  Letzter: {Path(bestand_files[-1]).name}')
all_bestand = []
for f in bestand_files:
    df = pd.read_csv(f, sep=';', encoding='ISO-8859-1', skiprows=1, header=None, low_memory=False)
    if df.shape[1] >= 8:
        df = df[[0, 1, 7]].rename(columns={0:'palette', 1:'lager_nr', 7:'we_datum'})
        all_bestand.append(df)
bestand = pd.concat(all_bestand, ignore_index=True)
bestand['we_dt'] = pd.to_datetime(bestand['we_datum'], errors='coerce', dayfirst=True)
unique_bestand = bestand.drop_duplicates(subset=['lager_nr'])
print(f'  Total Records: {len(bestand):,}')
print(f'  Unique Lager-Nrn: {len(unique_bestand):,}')
print(f'  WE-Datum-Range: {bestand["we_dt"].min().date()} – {bestand["we_dt"].max().date()}')
print(f'  Älteste 10% WE-Datum: {bestand["we_dt"].quantile(0.1).date()}')

print('\n' + '=' * 70)
print('  QUELLE 3: WP-Pipeline (Wareneingang)')
print('=' * 70)
wp_files = sorted(glob.glob(str(WE_PIPE_DIR / 'WARENEINGANG_PIPELINE*.csv')))
print(f'  Files: {len(wp_files)}')
for f in wp_files[:2]:
    print(f'    {Path(f).name}')
# Spalten der letzten Datei
wp_sample = pd.read_csv(wp_files[-1], sep=';', encoding='ISO-8859-1', nrows=20)
print(f'\n  Spalten letzter Datei ({Path(wp_files[-1]).name}):')
for i, c in enumerate(wp_sample.columns):
    sample = wp_sample[c].dropna().head(2).tolist()
    print(f'    [{i:>2}] {c:<35}  → {str(sample)[:70]}')
# Auch Header-Zeile checken (manchmal ist Zeile 0 die Sektion, Zeile 1 der Header)
print(f'\n  Zeile 0 Inhalt:')
wp_full = pd.read_csv(wp_files[-1], sep=';', encoding='ISO-8859-1', header=None, nrows=4)
for i in range(min(15, wp_full.shape[1])):
    print(f'    Col[{i}]: {wp_full.iloc[:3, i].tolist()}')

print('\n' + '=' * 70)
print('  QUELLE 4: Stock-Analysis (Portal)')
print('=' * 70)
stock_files = sorted(glob.glob(str(STOCK_DIR / 'Stock-Analysis-2026-*.xlsx')))
print(f'  Files: {len(stock_files)}')
if stock_files:
    sa = pd.read_excel(stock_files[-1], nrows=200)
    print(f'  Letzter: {Path(stock_files[-1]).name}')
    print(f'  n_cols: {len(sa.columns)}')
    for c in sa.columns:
        sample = sa[c].dropna().head(2).tolist()
        print(f'    {c:<32}  → {str(sample)[:60]}')

print('\n' + '=' * 70)
print('  KRITISCHE FRAGE: Wie viele All-Sold-Lager-Nrn matchen mit BESTAND-Lagern?')
print('=' * 70)
portal_full = pd.concat([pd.read_excel(f) for f in files], ignore_index=True)
portal_full = portal_full.drop_duplicates(subset=['Lager Nr.'], keep='first')
portal_full['lager_nr_str'] = portal_full['Lager Nr.'].astype(str).str.strip().str.replace(r'\.0+$', '', regex=True)
unique_bestand['lager_nr_str'] = unique_bestand['lager_nr'].astype(str).str.strip().str.replace(r'\.0+$', '', regex=True)

both = portal_full[portal_full['lager_nr_str'].isin(unique_bestand['lager_nr_str'])]
print(f'  Portal-Sold n: {len(portal_full):,}')
print(f'  BESTAND unique Lager-Nrn: {len(unique_bestand):,}')
print(f'  Intersection: {len(both):,} ({len(both)/len(portal_full)*100:.1f}%)')

# Erweiterung: gibt es WE-Datum aus BESTAND auch retroaktiv?
# Wenn Lager-Nr in BESTAND und Verkauf später → WE bekannt
print('\n  Retroaktive Suche: Lager-Nrn aus BESTAND × verkaufte Lager-Nrn:')
join = portal_full.merge(unique_bestand[['lager_nr_str', 'we_dt']], on='lager_nr_str', how='inner')
join['Date_dt'] = pd.to_datetime(join['Date'], errors='coerce').dt.normalize()
join['t_we_to_sold'] = (join['Date_dt'] - join['we_dt']).dt.days
filt = join[(join['t_we_to_sold'] >= 0) & (join['t_we_to_sold'] <= 1500)]
print(f'  WE→Sold-Median: {filt["t_we_to_sold"].median():.1f}T  (n={len(filt):,})')
print(f'  Davon 2025-Verkäufe: {(filt["Date_dt"].dt.year == 2025).sum():,}')
print(f'  Davon 2026-Verkäufe: {(filt["Date_dt"].dt.year == 2026).sum():,}')
