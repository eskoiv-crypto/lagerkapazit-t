import sys, io, os, glob
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', line_buffering=True)
from pathlib import Path
import pandas as pd
USERHOME = Path(os.environ.get('USERPROFILE', os.path.expanduser('~')))

# BESTAND
b_files = sorted(glob.glob(str(USERHOME/'OneDrive - elvinci.de GmbH'/'elvinci - Bestandslisten AMM'/'BESTAND134_*.CSV')))
bdf = pd.read_csv(b_files[-1], sep=';', encoding='ISO-8859-1', skiprows=1, header=None, low_memory=False, dtype=str)
cols=['Lager-Nr','Anzahl','Bez','LagerNr2','Lagerplatz','Klassif','Menge','WE','Notiz','Status','Auftrag','c11','c12','c13'][:bdf.shape[1]]
bdf.columns=cols
bdf['Lager-Nr']=bdf['Lager-Nr'].astype(str).str.strip()
qe = bdf[bdf['Status']=='QE']

# Stock-Analysis (verkaufbar)
sa=pd.read_excel(sorted(glob.glob(str(USERHOME/'OneDrive - elvinci.de GmbH'/'elvinci - Portal STOCK ANALYSIS'/'Stock-Analysis-*.xlsx')))[-1])
stock_set=set(sa['lager_number'].astype(str).str.strip())

# All-Sold (verkauft)
asold=pd.read_excel(sorted(glob.glob(str(USERHOME/'OneDrive - elvinci.de GmbH'/'elvinci - Portal ALL SOLD'/'All-Sold-*.xlsx')))[-1])
asold['lnr']=asold['Lager Nr.'].astype(str).str.strip().str.replace(r'\.0$','',regex=True)
sold_set=set(asold['lnr'])

print(f"BESTAND-QE gesamt: {len(qe):,}")
print(f"Stock-Analysis: {len(stock_set):,} · All-Sold: {len(sold_set):,}\n")

qe_l = set(qe['Lager-Nr'])
in_stock = qe['Lager-Nr'].isin(stock_set)
in_sold  = qe['Lager-Nr'].isin(sold_set)

print("=== QE-Geräte: wo sind sie auffindbar? ===")
print(f"  in Stock-Analysis (verkaufbar):           {in_stock.sum():,}")
print(f"  in All-Sold (verkauft):                   {in_sold.sum():,}")
print(f"  in Stock ODER All-Sold (= erklärbar):     {(in_stock|in_sold).sum():,}")
print(f"  WEDER noch (= ECHTE Diskrepanz):          {(~in_stock & ~in_sold).sum():,}")
print(f"     → {(~in_stock & ~in_sold).sum()/len(qe)*100:.1f}% der QE-Geräte")

# Alte Check-Logik vs neue
alt = (~in_stock).sum()
neu = (~in_stock & ~in_sold).sum()
print(f"\n=== Check-Logik-Vergleich ===")
print(f"  ALT (nur gegen Stock):        {alt:,} 'Diskrepanzen' → {alt/len(qe)*100:.1f}%")
print(f"  NEU (gegen Stock + All-Sold): {neu:,} echte Diskrepanzen → {neu/len(qe)*100:.1f}%")
print(f"  → {alt-neu:,} der alten 'Diskrepanzen' sind in Wahrheit VERKAUFTE Geräte")

# Die echten Rest-Diskrepanzen charakterisieren
echte = qe[~in_stock & ~in_sold].copy()
echte['we_dt']=pd.to_datetime(echte['WE'],errors='coerce',dayfirst=True)
print(f"\n=== Die {len(echte):,} ECHTEN Diskrepanzen — was sind das? ===")
print(f"  WE-Monat:")
print(echte.groupby(echte['we_dt'].dt.to_period('M')).size().tail(8).to_string())
print(f"\n  Lagerplatz-Bereiche:")
echte['ber']=echte['Lagerplatz'].astype(str).str.extract(r'^([A-Z]+\d*)')[0]
print(echte['ber'].value_counts().head(8).to_string())
print(f"\n  Bezeichnungen:")
print(echte['Bez'].value_counts().head(8).to_string())
print(f"\n  SSCC-Paletten (18-stellig): {echte['Lager-Nr'].str.match(r'^[0-9]{{18}}$').sum():,}")
print(f"  ELHR-Umlager: {echte['Lagerplatz'].astype(str).str.startswith('ELHR').sum():,}")
