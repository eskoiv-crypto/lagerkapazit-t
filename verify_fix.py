import sys, io, os, glob
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', line_buffering=True)
from pathlib import Path
import pandas as pd
USERHOME = Path(os.environ.get('USERPROFILE', os.path.expanduser('~')))
b_files = sorted(glob.glob(str(USERHOME/'OneDrive - elvinci.de GmbH'/'elvinci - Bestandslisten AMM'/'BESTAND134_*.CSV')))
bdf = pd.read_csv(b_files[-1], sep=';', encoding='ISO-8859-1', skiprows=1, header=None, low_memory=False)
bdf.columns = ['Lager-Nr','Anzahl','Bez','LagerNr2','Lagerplatz','Klassif','Menge','WE','Notiz','Status','Auftrag','c11'][:bdf.shape[1]]
bdf['Lager-Nr']=bdf['Lager-Nr'].astype(str).str.strip()
bdf['we_dt']=pd.to_datetime(bdf['WE'],errors='coerce',dayfirst=True)
sa_files=sorted(glob.glob(str(USERHOME/'OneDrive - elvinci.de GmbH'/'Digital Experience - KI-Tools'/'Stock Analysis'/'Stock-Analysis-*.xlsx')))
sa=pd.read_excel(sa_files[-1]); sa['lager_number']=sa['lager_number'].astype(str).str.strip()
stock_set=set(sa['lager_number'])
cutoff=pd.to_datetime(sa['datetime_upload'],errors='coerce').max()
print(f'Stock-Cutoff (juengstes Upload): {cutoff.date()}')
alt=bdf['Lager-Nr'].isin(stock_set).mean()*100
print(f'ALT (alle BESTAND):                 {bdf["Lager-Nr"].isin(stock_set).sum()}/{len(bdf)} = {alt:.1f}%')
rel=bdf[~bdf['Status'].isin(['VS','AA'])]
fix1=rel['Lager-Nr'].isin(stock_set).mean()*100
print(f'FIX1 (ohne VS/AA):                  {rel["Lager-Nr"].isin(stock_set).sum()}/{len(rel)} = {fix1:.1f}%')
rel2=rel[~(rel['we_dt']>cutoff)]
fix2=rel2['Lager-Nr'].isin(stock_set).mean()*100
print(f'FIX2 (ohne VS/AA + ohne Frischware): {rel2["Lager-Nr"].isin(stock_set).sum()}/{len(rel2)} = {fix2:.1f}%')
