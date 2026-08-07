"""
Warum nur 48% BESTAND-Lagernummern in Stock-Analysis?
Charakterisierung der nicht-matchenden Geräte.
"""
import sys, io, os, glob
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', line_buffering=True)
from pathlib import Path
import pandas as pd

USERHOME = Path(os.environ.get('USERPROFILE', os.path.expanduser('~')))

# === BESTAND (aktuellste) ===
BESTAND_DIR = USERHOME / 'OneDrive - elvinci.de GmbH' / 'elvinci - Bestandslisten AMM'
b_files = sorted(glob.glob(str(BESTAND_DIR / 'BESTAND134_*.CSV')))
latest_b = b_files[-1]
print(f'BESTAND: {Path(latest_b).name}')
bdf = pd.read_csv(latest_b, sep=';', encoding='ISO-8859-1', skiprows=1, header=None, low_memory=False)
bdf.columns = ['Lager-Nr','Anzahl','Bezeichnung','LagerNr2','Lagerplatz','Klassif','Menge',
               'WE-Datum','Notiz','Status','Auftrag-Nr','col11'][:bdf.shape[1]]
bdf['Lager-Nr'] = bdf['Lager-Nr'].astype(str).str.strip()
print(f'  BESTAND Records: {len(bdf):,}')
print(f'  Unique Lager-Nrn: {bdf["Lager-Nr"].nunique():,}')

# === Stock-Analysis (aktuellste) ===
STOCK_DIRS = [
    USERHOME / 'OneDrive - elvinci.de GmbH' / 'Digital Experience - KI-Tools' / 'Stock Analysis',
    USERHOME / 'OneDrive - elvinci.de GmbH' / 'elvinci - Portal STOCK ANALYSIS',
]
sa_files = []
for d in STOCK_DIRS:
    if d.exists():
        sa_files += glob.glob(str(d / 'Stock-Analysis-*.xlsx'))
sa_files = sorted(sa_files)
latest_sa = sa_files[-1]
print(f'\nStock-Analysis: {Path(latest_sa).name}')
sa = pd.read_excel(latest_sa)
sa['lager_number'] = sa['lager_number'].astype(str).str.strip()
print(f'  Stock-Analysis Records: {len(sa):,}')
print(f'  Unique Lager-Nrn: {sa["lager_number"].nunique():,}')

# === Match-Berechnung (reproduziert die Dashboard-48%) ===
stock_set = set(sa['lager_number'])
bdf['in_stock'] = bdf['Lager-Nr'].isin(stock_set)
match_pct = bdf['in_stock'].mean()*100
print(f'\n{"="*70}')
print(f'  MATCH: {bdf["in_stock"].sum():,} / {len(bdf):,} = {match_pct:.1f}%  ← Dashboard zeigt 48%')
print(f'{"="*70}')

# === Charakterisierung der NICHT-matchenden BESTAND-Records ===
missing = bdf[~bdf['in_stock']].copy()
print(f'\nNICHT in Stock-Analysis: {len(missing):,} Records')

print(f'\n--- Status-Verteilung der fehlenden Records ---')
print(missing['Status'].value_counts().head(15).to_string())

print(f'\n--- Bezeichnung der fehlenden Records (Top-20) ---')
print(missing['Bezeichnung'].value_counts().head(20).to_string())

print(f'\n--- Lagerplatz-Bereiche der fehlenden Records ---')
missing['lagerbereich'] = missing['Lagerplatz'].astype(str).str.extract(r'^(H\d+|[A-Z]\d+)')[0]
print(missing['lagerbereich'].value_counts().head(15).to_string())

print(f'\n--- WE-Datum-Verteilung (Monat) der fehlenden ---')
missing['we_dt'] = pd.to_datetime(missing['WE-Datum'], errors='coerce', dayfirst=True)
print(missing.groupby(missing['we_dt'].dt.to_period('M')).size().tail(12).to_string())

# === Vergleich: matchende vs nicht-matchende ===
matched = bdf[bdf['in_stock']]
print(f'\n{"="*70}')
print(f'  VERGLEICH matchende vs. fehlende Records')
print(f'{"="*70}')
print(f'\n  Status-Verteilung MATCHENDE (in Stock-Analysis):')
print(matched['Status'].value_counts().head(8).to_string())

# === Datums-Differenz BESTAND vs Stock-Analysis ===
print(f'\n{"="*70}')
print(f'  ZEITVERSATZ-CHECK')
print(f'{"="*70}')
bdate = Path(latest_b).name
sa_date = pd.to_datetime(sa['datetime_upload'], errors='coerce').max() if 'datetime_upload' in sa.columns else None
print(f'  BESTAND-Datei: {bdate}')
print(f'  Stock-Analysis letztes Upload: {sa_date}')

# === Sammelposten/Container-Check ===
print(f'\n{"="*70}')
print(f'  SAMMELPOSTEN / CONTAINER-CHECK')
print(f'{"="*70}')
sammel_keywords = ['unsortiert','palette','sammel','kleingerät','mix','konvolut','posten']
for kw in sammel_keywords:
    n = missing['Bezeichnung'].astype(str).str.lower().str.contains(kw, na=False).sum()
    if n>0:
        print(f'  "{kw}" in fehlender Bezeichnung: {n:,}')

print(f'\nFAZIT:')
print(f'  Die {len(missing):,} fehlenden Records ({100-match_pct:.0f}%) sind Geräte, die im physischen')
print(f'  Lager (BESTAND) sind, aber NICHT im Verkaufs-Portal (Stock-Analysis).')
print(f'  Häufigste Gründe: Status (nicht klassifiziert/QE), Sammelposten, Versandbereich.')
