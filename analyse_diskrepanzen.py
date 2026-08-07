"""
Präzise Analyse der 1476 Diskrepanzen: BESTAND-QE nicht in Stock-Analysis.
Ziel: echte, datenbelegte Hintergründe für die fehlenden Geräte.
"""
import sys, io, os, glob
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', line_buffering=True)
from pathlib import Path
import pandas as pd
USERHOME = Path(os.environ.get('USERPROFILE', os.path.expanduser('~')))

# Diskrepanz-CSV — Lagernummer ZWINGEND als String (sonst Float-Verfälschung)
disk = pd.read_csv(USERHOME/'Downloads'/'Datenqualität_Diskrepanzen_2026-05-27.csv', sep=';', encoding='utf-8',
                   dtype={'Lagernummer':str, 'Wert A':str, 'Wert B':str})
# .0-Suffix + Scientific Notation bereinigen (falls doch numerisch interpretiert)
disk['Lagernummer'] = disk['Lagernummer'].astype(str).str.strip().str.replace(r'\.0$', '', regex=True)
print(f"Diskrepanzen gesamt: {len(disk):,}")
print(f"Typen: {disk['Typ'].value_counts().to_dict()}")

# Lager-Nr-Format-Analyse
print(f"\n=== 1. Lagernummer-Format der Diskrepanzen ===")
disk['len'] = disk['Lagernummer'].str.len()
disk['is_9stellig'] = disk['Lagernummer'].str.match(r'^9\d{8}$')
print(f"  9-stellig (90xxxxxxx): {disk['is_9stellig'].sum():,}")
print(f"  Andere Formate: {(~disk['is_9stellig']).sum():,}")
print(f"  Längen-Verteilung:")
print(disk['len'].value_counts().sort_index().to_string())
print(f"\n  Beispiele Nicht-9-stellig:")
print(disk[~disk['is_9stellig']]['Lagernummer'].head(10).to_string())

# BESTAND laden + matchen
b_files = sorted(glob.glob(str(USERHOME/'OneDrive - elvinci.de GmbH'/'elvinci - Bestandslisten AMM'/'BESTAND134_*.CSV')))
bdf = pd.read_csv(b_files[-1], sep=';', encoding='ISO-8859-1', skiprows=1, header=None, low_memory=False)
ncols = bdf.shape[1]
cols = ['Lager-Nr','Anzahl','Bez','LagerNr2','Lagerplatz','Klassif','Menge','WE','Notiz','Status','Auftrag','c11','c12','c13'][:ncols]
bdf.columns = cols
bdf['Lager-Nr'] = bdf['Lager-Nr'].astype(str).str.strip()
print(f"\n=== 2. Match gegen BESTAND ({Path(b_files[-1]).name}) ===")
matched = bdf[bdf['Lager-Nr'].isin(set(disk['Lagernummer']))].copy()
print(f"  Von {len(disk):,} Diskrepanzen im BESTAND gefunden: {len(matched):,}")
print(f"  NICHT im aktuellen BESTAND: {len(disk) - matched['Lager-Nr'].nunique():,}")

# Status-Verteilung der gematchten
print(f"\n=== 3. BESTAND-Status der Diskrepanz-Geräte ===")
print(matched['Status'].value_counts().to_string())

# Lagerplatz-Analyse
print(f"\n=== 4. Lagerplatz-Bereiche (wo liegen sie physisch?) ===")
matched['bereich'] = matched['Lagerplatz'].astype(str).str.extract(r'^([A-Z]\d+|[A-Z]+)')[0]
print(matched['bereich'].value_counts().head(15).to_string())

# WE-Datum-Analyse
print(f"\n=== 5. WE-Datum (Lager-Alter) ===")
matched['we_dt'] = pd.to_datetime(matched['WE'], errors='coerce', dayfirst=True)
print(f"  Range: {matched['we_dt'].min()} – {matched['we_dt'].max()}")
print(f"  Pro Monat:")
print(matched.groupby(matched['we_dt'].dt.to_period('M')).size().tail(10).to_string())

# Notiz-Analyse (Hinweise auf Sperrgründe?)
print(f"\n=== 6. Notiz-Spalte (Hinweise auf Sperr-/Sondergründe) ===")
print(f"  Nicht-leere Notizen: {matched['Notiz'].notna().sum():,}")
print(f"  Top-Notizen:")
print(matched['Notiz'].value_counts().head(20).to_string())

# Bezeichnungs-Analyse
print(f"\n=== 7. Bezeichnungen ===")
print(matched['Bez'].value_counts().head(12).to_string())

# Auftrags-Nr: sind sie reserviert/verkauft?
print(f"\n=== 8. Auftrags-Nr-Belegung (reserviert?) ===")
print(f"  Mit Auftrags-Nr: {matched['Auftrag'].notna().sum():,} ({matched['Auftrag'].notna().mean()*100:.1f}%)")
print(f"  Ohne Auftrags-Nr: {matched['Auftrag'].isna().sum():,}")

# Klassif-Spalte
print(f"\n=== 9. Klassifizierungs-Spalte (Spalte 5) ===")
print(matched['Klassif'].value_counts().head(10).to_string())

# Sonder-Lager-Nrn (nicht 9-stellig) im Detail
print(f"\n=== 10. Sonderformate im BESTAND ===")
sonder = matched[~matched['Lager-Nr'].str.match(r'^9\d{8}$')]
print(f"  Anzahl: {len(sonder):,}")
if len(sonder):
    print(sonder[['Lager-Nr','Bez','Lagerplatz','Status','Notiz']].head(15).to_string())
