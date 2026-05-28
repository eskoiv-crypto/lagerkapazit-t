import sys, io, os, glob
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', line_buffering=True)
from pathlib import Path
import pandas as pd
USERHOME = Path(os.environ.get('USERPROFILE', os.path.expanduser('~')))

disk = pd.read_csv(USERHOME/'Downloads'/'Datenqualität_Diskrepanzen_2026-05-27.csv', sep=';', encoding='utf-8', dtype={'Lagernummer':str})
disk['Lagernummer'] = disk['Lagernummer'].astype(str).str.strip().str.replace(r'\.0$','',regex=True)
disk = disk[disk['Typ']=='lagernr']
nrs = set(disk['Lagernummer'])

b_files = sorted(glob.glob(str(USERHOME/'OneDrive - elvinci.de GmbH'/'elvinci - Bestandslisten AMM'/'BESTAND134_*.CSV')))
bdf = pd.read_csv(b_files[-1], sep=';', encoding='ISO-8859-1', skiprows=1, header=None, low_memory=False)
cols=['Lager-Nr','Anzahl','Bez','LagerNr2','Lagerplatz','Klassif','Menge','WE','Notiz','Status','Auftrag','c11','c12','c13'][:bdf.shape[1]]
bdf.columns=cols
bdf['Lager-Nr']=bdf['Lager-Nr'].astype(str).str.strip()
m = bdf[bdf['Lager-Nr'].isin(nrs)].copy()
m['we_dt']=pd.to_datetime(m['WE'],errors='coerce',dayfirst=True)
m['platz']=m['Lagerplatz'].astype(str)
m['lnr']=m['Lager-Nr'].astype(str)

# Stock-Cutoff
sa=pd.read_excel(sorted(glob.glob(str(USERHOME/'OneDrive - elvinci.de GmbH'/'elvinci - Portal STOCK ANALYSIS'/'Stock-Analysis-*.xlsx')))[-1])
cutoff=pd.to_datetime(sa['datetime_upload'],errors='coerce').max()
print(f"Stock-Snapshot-Cutoff: {cutoff.date()}")
print(f"BESTAND-Datei: {Path(b_files[-1]).name}\n")
print(f"Im BESTAND gefundene Diskrepanzen: {len(m):,} von {len(disk):,}\n")

# Kategorisierung (Priorität von oben nach unten, jede Nr nur 1 Kategorie)
m['kat'] = 'Sonstige'
# 1. SSCC-Paletten / Sammelcontainer (18-stellig ODER "Unsortiert"/"Bestand" Bezeichnung)
sscc = m['lnr'].str.match(r'^\d{18}$') | m['Bez'].astype(str).str.contains('Unsortiert|^Bestand$', case=False, regex=True, na=False)
m.loc[sscc, 'kat'] = '1_Sammelcontainer/Palette (SSCC)'
# 2. ELHR-Umlagerbereich (Eingang/Umlagerung/Retoure)
elhr = (m['kat']=='Sonstige') & m['platz'].str.startswith('ELHR')
m.loc[elhr, 'kat'] = '2_Umlager-/Eingangsbereich (ELHR)'
# 3. Frischware (WE nach Stock-Snapshot = noch nicht im Portal-Export)
frisch = (m['kat']=='Sonstige') & (m['we_dt'] > cutoff)
m.loc[frisch, 'kat'] = '3_Frischware (WE nach Snapshot)'
# 4. Verkauft/Versand
m.loc[(m['kat']=='Sonstige') & (m['Status']=='VS'), 'kat'] = '4_Verkauft/Versand (VS)'
# 5. Rest = echte Klärfälle (alt, QE, im normalen Lager, vor Snapshot)
m.loc[m['kat']=='Sonstige', 'kat'] = '5_Echter Klaerfall (alt, QE, im Lager)'

print("=== KATEGORISIERUNG der Diskrepanzen ===")
kat = m['kat'].value_counts().sort_index()
for k,v in kat.items():
    print(f"  {k:<42} {v:>5,}  ({v/len(m)*100:>4.1f}%)")

# Detail Kategorie 5 (echte Klärfälle) — das ist das eigentlich Interessante
print(f"\n=== Detail Kategorie 5: echte Klaerfaelle ===")
k5 = m[m['kat'].str.startswith('5_')]
print(f"  Anzahl: {len(k5):,}")
print(f"  WE-Alter:")
print(f"    aelter als 180 Tage: {(k5['we_dt'] < pd.Timestamp.now()-pd.Timedelta(days=180)).sum():,}")
print(f"    aelter als 365 Tage: {(k5['we_dt'] < pd.Timestamp.now()-pd.Timedelta(days=365)).sum():,}")
print(f"  Lagerplatz-Bereiche:")
k5['bereich']=k5['platz'].str.extract(r'^([A-Z]\d+)')[0]
print(k5['bereich'].value_counts().head(8).to_string())
print(f"\n  Notiz-Muster (Bestell-/Lieferschein-Nrn = frisch eingegangen?):")
print(k5['Notiz'].value_counts().head(12).to_string())

# WE-Datum-Verteilung Kategorie 5
print(f"\n  WE-Monat (Kat 5):")
print(k5.groupby(k5['we_dt'].dt.to_period('M')).size().tail(8).to_string())
