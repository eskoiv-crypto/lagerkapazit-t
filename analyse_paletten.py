"""
KILLCRITIC: Paletten-Produkte verstehen.
900167869 = SOLD, Pal-Nr.399, 27 Geräte drin
900238367 = OFFERED, Pal-Nr.7, 29 Geräte drin
"""
import sys, io, os, glob
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', line_buffering=True)
from pathlib import Path
import pandas as pd
USERHOME = Path(os.environ.get('USERPROFILE', os.path.expanduser('~')))

T1, T2 = '900167869', '900238367'

# Quellen laden
b_files = sorted(glob.glob(str(USERHOME/'OneDrive - elvinci.de GmbH'/'elvinci - Bestandslisten AMM'/'BESTAND134_*.CSV')))
bdf = pd.read_csv(b_files[-1], sep=';', encoding='ISO-8859-1', skiprows=1, header=None, low_memory=False, dtype=str)
cols=['Lager-Nr','Anzahl','Bez','LagerNr2','Lagerplatz','Klassif','Menge','WE','Notiz','Status','Auftrag','c11','c12','c13'][:bdf.shape[1]]
bdf.columns=cols
bdf['Lager-Nr']=bdf['Lager-Nr'].astype(str).str.strip()

sa=pd.read_excel(sorted(glob.glob(str(USERHOME/'OneDrive - elvinci.de GmbH'/'elvinci - Portal STOCK ANALYSIS'/'Stock-Analysis-*.xlsx')))[-1])
sa['lager_number']=sa['lager_number'].astype(str).str.strip()

asold=pd.read_excel(sorted(glob.glob(str(USERHOME/'OneDrive - elvinci.de GmbH'/'elvinci - Portal ALL SOLD'/'All-Sold-*.xlsx')))[-1])
asold['lnr']=asold['Lager Nr.'].astype(str).str.strip().str.replace(r'\.0$','',regex=True)

for tid in [T1, T2]:
    print(f"\n{'='*60}\n  PALETTE {tid}\n{'='*60}")
    b = bdf[bdf['Lager-Nr']==tid]
    print(f"  BESTAND: {len(b)} Treffer")
    if len(b): print(b[['Bez','Lagerplatz','WE','Notiz','Status','Anzahl','Menge']].to_string(index=False))
    print(f"  Stock-Analysis: {len(sa[sa['lager_number']==tid])} Treffer")
    a = asold[asold['lnr']==tid]
    print(f"  All-Sold: {len(a)} Treffer")
    if len(a): print(a[['lnr','Date','Supply Type','Brand','Product Group','Company','JTL Selling Price']].to_string(index=False))

# Paletten-Muster im BESTAND: Bezeichnung "Set Artikel" oder Anzahl>1?
print(f"\n{'='*60}\n  PALETTEN-MUSTER IM BESTAND\n{'='*60}")
# Anzahl-Spalte: Paletten haben Anzahl > 1?
bdf['anz_n'] = pd.to_numeric(bdf['Anzahl'], errors='coerce')
print(f"  Anzahl-Verteilung (Spalte 'Anzahl'):")
print(bdf['anz_n'].value_counts().head(10).to_string())
multi = bdf[bdf['anz_n'] > 1]
print(f"\n  Geräte mit Anzahl > 1 (= Paletten/Bündel?): {len(multi):,}")
if len(multi): print(multi[['Lager-Nr','Bez','Anzahl','Status','Lagerplatz']].head(10).to_string(index=False))

# Bezeichnung 'Set Artikel' / 'Palette'
print(f"\n  Bezeichnungen die auf Bündel deuten:")
for kw in ['Set Artikel','Palette','gemischt','Konvolut','Bestand']:
    n = bdf['Bez'].astype(str).str.contains(kw, case=False, na=False).sum()
    if n: print(f"    '{kw}': {n:,}")

# Sind die 289 echten Diskrepanzen Paletten?
print(f"\n{'='*60}\n  Sind die echten Diskrepanzen PALETTEN?\n{'='*60}")
qe = bdf[bdf['Status']=='QE']
stock_set=set(sa['lager_number']); sold_set=set(asold['lnr'])
echte = qe[~qe['Lager-Nr'].isin(stock_set) & ~qe['Lager-Nr'].isin(sold_set)].copy()
print(f"  Echte Diskrepanzen (QE, weder Stock noch Sold): {len(echte):,}")
echte['anz_n']=pd.to_numeric(echte['Anzahl'],errors='coerce')
print(f"  davon Anzahl > 1 (Paletten/Bündel): {(echte['anz_n']>1).sum():,}")
print(f"  davon 'Set Artikel': {echte['Bez'].astype(str).str.contains('Set Artikel',case=False,na=False).sum():,}")
print(f"  Bezeichnungen der echten Diskrepanzen:")
print(echte['Bez'].value_counts().head(12).to_string())
