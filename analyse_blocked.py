import sys, io, os, glob
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', line_buffering=True)
from pathlib import Path
import pandas as pd
USERHOME = Path(os.environ.get('USERPROFILE', os.path.expanduser('~')))

# Stock-Analysis aktuell
sa_files = sorted(glob.glob(str(USERHOME/'OneDrive - elvinci.de GmbH'/'elvinci - Portal STOCK ANALYSIS'/'Stock-Analysis-*.xlsx')))
sa = pd.read_excel(sa_files[-1])
sa['lager_number'] = sa['lager_number'].astype(str).str.strip()
print(f"Stock-Analysis: {Path(sa_files[-1]).name}  ({len(sa):,} Zeilen)")
print(f"\nSpalten: {list(sa.columns)}")

# status-Spalte?
if 'status' in sa.columns:
    print(f"\n=== status-Verteilung in Stock-Analysis ===")
    print(sa['status'].value_counts().to_string())

# Ist 900243089 drin?
target = '900243089'
print(f"\n=== Ist {target} in Stock-Analysis? ===")
hit = sa[sa['lager_number']==target]
print(f"  Treffer: {len(hit)}")
if len(hit): print(hit[['lager_number','status','brand','product_group']].to_string())

# BESTAND aktuell
b_files = sorted(glob.glob(str(USERHOME/'OneDrive - elvinci.de GmbH'/'elvinci - Bestandslisten AMM'/'BESTAND134_*.CSV')))
bdf = pd.read_csv(b_files[-1], sep=';', encoding='ISO-8859-1', skiprows=1, header=None, low_memory=False)
bdf.columns = ['Lager-Nr','Anzahl','Bez','LagerNr2','Lagerplatz','Klassif','Menge','WE','Notiz','Status','Auftrag','c11'][:bdf.shape[1]]
bdf['Lager-Nr']=bdf['Lager-Nr'].astype(str).str.strip()
print(f"\n=== Ist {target} im BESTAND ({Path(b_files[-1]).name})? ===")
bhit = bdf[bdf['Lager-Nr']==target]
print(f"  Treffer: {len(bhit)}")
if len(bhit): print(bhit[['Lager-Nr','Bez','WE','Status','Lagerplatz']].to_string())

# Kernfrage: BESTAND-QE-Geräte die NICHT in Stock-Analysis sind — sind das BLOCKED im Portal?
print(f"\n=== Diskrepanz-Analyse: BESTAND-QE nicht in Stock ===")
stock_set = set(sa['lager_number'])
qe = bdf[bdf['Status']=='QE'].copy()
qe_missing = qe[~qe['Lager-Nr'].isin(stock_set)]
print(f"  BESTAND-QE gesamt: {len(qe):,}")
print(f"  davon NICHT in Stock-Analysis: {len(qe_missing):,}")
# WE-Datum der fehlenden
qe_missing['we_dt'] = pd.to_datetime(qe_missing['WE'], errors='coerce', dayfirst=True)
cutoff = pd.to_datetime(sa['datetime_upload'], errors='coerce').max()
print(f"  Stock-Snapshot-Cutoff (juengstes Upload): {cutoff.date() if pd.notna(cutoff) else '?'}")
frisch = (qe_missing['we_dt'] > cutoff).sum()
print(f"  davon Frischware (WE nach Cutoff): {frisch:,}")
print(f"  davon NICHT-frisch (echte Diskrepanz): {len(qe_missing)-frisch:,}")
print(f"\n  → Diese Nicht-frischen QE-Geraete sind im Lager, aber nicht im Portal-Export.")
print(f"     Wahrscheinlichste Ursache: Portal-Status BLOCKED/gesperrt → nicht im Stock-Analysis-Export.")
print(f"\n  Bezeichnungen dieser Diskrepanzen (Top-15):")
print(qe_missing[qe_missing['we_dt']<=cutoff]['Bez'].value_counts().head(15).to_string())
