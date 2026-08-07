"""
KILLCRITIC: Prüfe die These (Diskrepanz = Klassifizierungs-Rückstand QE)
gegen den konkreten SOLD-Fall 900241676 mit Supply 1003881916.
"""
import sys, io, os, glob
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', line_buffering=True)
from pathlib import Path
import pandas as pd
USERHOME = Path(os.environ.get('USERPROFILE', os.path.expanduser('~')))

TARGET = '900241676'
SUPPLY = '1003881916'

# === Diskrepanz-CSV ===
disk = pd.read_csv(USERHOME/'Downloads'/'Datenqualität_Diskrepanzen_2026-05-27.csv', sep=';', encoding='utf-8', dtype=str)
disk['Lagernummer'] = disk['Lagernummer'].astype(str).str.strip().str.replace(r'\.0$','',regex=True)
print(f"=== 1. Ist {TARGET} (SOLD) in den Diskrepanzen? ===")
hit = disk[disk['Lagernummer']==TARGET]
print(f"  Treffer: {len(hit)}")
if len(hit): print(hit.to_string())

# === BESTAND ===
b_files = sorted(glob.glob(str(USERHOME/'OneDrive - elvinci.de GmbH'/'elvinci - Bestandslisten AMM'/'BESTAND134_*.CSV')))
bdf = pd.read_csv(b_files[-1], sep=';', encoding='ISO-8859-1', skiprows=1, header=None, low_memory=False, dtype=str)
cols=['Lager-Nr','Anzahl','Bez','LagerNr2','Lagerplatz','Klassif','Menge','WE','Notiz','Status','Auftrag','c11','c12','c13'][:bdf.shape[1]]
bdf.columns=cols
bdf['Lager-Nr']=bdf['Lager-Nr'].astype(str).str.strip()
print(f"\n=== 2. Ist {TARGET} im BESTAND ({Path(b_files[-1]).name})? ===")
bhit = bdf[bdf['Lager-Nr']==TARGET]
print(f"  Treffer: {len(bhit)}")
if len(bhit): print(bhit[['Lager-Nr','Bez','Lagerplatz','WE','Notiz','Status','Auftrag']].to_string())

# === Stock-Analysis ===
sa=pd.read_excel(sorted(glob.glob(str(USERHOME/'OneDrive - elvinci.de GmbH'/'elvinci - Portal STOCK ANALYSIS'/'Stock-Analysis-*.xlsx')))[-1])
sa['lager_number']=sa['lager_number'].astype(str).str.strip()
print(f"\n=== 3. Ist {TARGET} in Stock-Analysis? ===")
shit = sa[sa['lager_number']==TARGET]
print(f"  Treffer: {len(shit)}")

# === KERN-FRAGE: Notiz 1003881916 = Supply-Nr? Wie viele Geräte teilen sie? ===
print(f"\n=== 4. Notiz/Supply '{SUPPLY}' im BESTAND — wie viele Geräte, welche Status? ===")
supply_geraete = bdf[bdf['Notiz'].astype(str).str.strip()==SUPPLY]
print(f"  Geräte mit Notiz={SUPPLY}: {len(supply_geraete)}")
print(f"  Status-Verteilung:")
print(supply_geraete['Status'].value_counts().to_string())
print(f"  → Notiz ist offensichtlich eine SUPPLY-/Lieferungs-Nr (mehrere Geräte teilen sie)")

# === KERN-CHECK: Sind die DISKREPANZ-Geräte wirklich QE (unverkauft)? ===
print(f"\n=== 5. KILLCRITIC: Status der Diskrepanz-Geräte im BESTAND ===")
disk_lagernr = disk[disk['Typ']=='lagernr']['Lagernummer']
m = bdf[bdf['Lager-Nr'].isin(set(disk_lagernr))]
print(f"  Diskrepanzen im BESTAND gefunden: {len(m)}")
print(f"  Status:")
print(m['Status'].value_counts().to_string())

# === ENTSCHEIDENDE PRÜFUNG: Cross-Check Diskrepanz-Geräte gegen ALL-SOLD ===
# Wenn Diskrepanz-Geräte in All-Sold (verkauft) auftauchen → These FALSCH
print(f"\n=== 6. ENTSCHEIDEND: Sind Diskrepanz-Geräte in ALL-SOLD (verkauft)? ===")
allsold_files = sorted(glob.glob(str(USERHOME/'OneDrive - elvinci.de GmbH'/'elvinci - Portal ALL SOLD'/'All-Sold-*.xlsx')))
if allsold_files:
    asold = pd.read_excel(allsold_files[-1])
    asold['lnr'] = asold['Lager Nr.'].astype(str).str.strip().str.replace(r'\.0$','',regex=True)
    sold_set = set(asold['lnr'])
    disk_in_sold = m[m['Lager-Nr'].isin(sold_set)]
    print(f"  All-Sold-Datei: {Path(allsold_files[-1]).name} ({len(asold):,} Verkäufe)")
    print(f"  Diskrepanz-Geräte die VERKAUFT wurden (in All-Sold): {len(disk_in_sold)}")
    print(f"  → Wenn >0: diese Geräte sind verkauft, nicht 'Klassifizierungs-Rückstand'")
    if len(disk_in_sold) > 0:
        print(f"\n  Status dieser verkauften Diskrepanz-Geräte im BESTAND:")
        print(disk_in_sold['Status'].value_counts().to_string())
        # Verkaufsdatum dieser Geräte
        vd = asold[asold['lnr'].isin(set(disk_in_sold['Lager-Nr']))]
        vd['dt'] = pd.to_datetime(vd['Date'], errors='coerce')
        print(f"  Verkaufs-Zeitraum: {vd['dt'].min()} – {vd['dt'].max()}")

# === Ist TARGET in All-Sold? ===
print(f"\n=== 7. Ist {TARGET} in All-Sold (= bestätigt verkauft)? ===")
if allsold_files:
    th = asold[asold['lnr']==TARGET]
    print(f"  Treffer: {len(th)}")
    if len(th): print(th[['lnr','Date','Supply Type','Brand','Company']].to_string() if 'Company' in th.columns else th[['lnr','Date']].to_string())
