"""
VOLLE Brücke: alle Ohrdruf-Geräte aus BESTAND → All-Sold mappen
Output: ohrdruf_lagernrn_komplett.csv mit allen verkauften Ohrdruf-Geräten
"""
import sys, io, os, glob
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', line_buffering=True)
from pathlib import Path
import pandas as pd

USERHOME = Path(os.environ.get('USERPROFILE', os.path.expanduser('~')))
BESTAND_DIR = USERHOME / 'OneDrive - elvinci.de GmbH' / 'elvinci - Bestandslisten AMM'
b_files = sorted(glob.glob(str(BESTAND_DIR / 'BESTAND134_*.CSV')))
print(f'BESTAND-Files: {len(b_files)}')

# === Schritt 1: Alle BESTAND-Records mit OHRDRUF in Notiz-Spalte ===
print('\nSuche OHRDRUF in allen BESTAND-Snapshots…')
all_ohrdruf = []
for f in b_files:
    df = pd.read_csv(f, sep=';', encoding='ISO-8859-1', skiprows=1, header=None, low_memory=False)
    df.columns = ['Lager-Nr','col1','Bezeichnung','col3','Lagerplatz','col5','col6',
                  'WE-Datum','Notiz','Status','Auftrag-Nr','col11']
    matches = df[df['Notiz'].astype(str).str.contains('OHRDRUF|Ohrdruf', regex=True, na=False)].copy()
    matches['source_file'] = Path(f).name
    all_ohrdruf.append(matches)

oh = pd.concat(all_ohrdruf, ignore_index=True)
print(f'  Gesamt-Records mit OHRDRUF-Notiz: {len(oh):,}')
# Dedup auf Lager-Nr
oh_unique = oh.drop_duplicates(subset='Lager-Nr', keep='first')
print(f'  Unique Container-Lager-Nrn: {len(oh_unique):,}')
print(f'\n  Aufschlüsselung der Notizen:')
print(oh_unique['Notiz'].value_counts().to_string())
print(f'\n  Aufschlüsselung der Auftrags-Nrn:')
print(f'  Unique Auftrags-Nrn: {oh_unique["Auftrag-Nr"].dropna().nunique():,}')

print('\n  Detaillierte Records:')
print(oh_unique[['Lager-Nr','Bezeichnung','WE-Datum','Notiz','Status','Auftrag-Nr']].to_string(index=False))

# === Schritt 2: Diese Auftrags-Nrn in All-Sold suchen ===
print('\n' + '='*78)
print('  Schritt 2: All-Sold-Match über Auftrags-Nr')
print('='*78)
sold = pd.read_excel(USERHOME/'Downloads'/'All-Sold-Apr2025-Apr2026.xlsx')
au_nrn = set(oh_unique['Auftrag-Nr'].dropna().unique())
print(f'  Auftrags-Nrn zu suchen: {len(au_nrn):,}')

sold_match = sold[sold['Order Nr.'].isin(au_nrn)].copy()
print(f'  Treffer in All-Sold: {len(sold_match):,} Verkäufe')
print(f'  Unique Auftrags-Nrn mit Verkäufen: {sold_match["Order Nr."].nunique():,}')

print(f'\n  Aktueller Supply Type dieser Geräte (vor Re-Klassifikation):')
print(sold_match['Supply Type'].value_counts().to_string())
print(f'\n  Top-Brands:')
print(sold_match['Brand'].value_counts().head(10).to_string())
print(f'\n  Verkaufs-Zeitraum:')
sold_match['Date_dt'] = pd.to_datetime(sold_match['Date'])
print(f'    {sold_match["Date_dt"].min().date()} – {sold_match["Date_dt"].max().date()}')

# Pro Auftrags-Nr ein Mapping ausgeben
print(f'\n  Pro Auftrags-Nr:')
for au, grp in sold_match.groupby('Order Nr.'):
    notiz = oh_unique[oh_unique['Auftrag-Nr']==au]['Notiz'].iloc[0] if au in oh_unique['Auftrag-Nr'].values else '?'
    print(f'    {au}  ({grp["Date_dt"].iloc[0].date()})  →  {len(grp):,} Geräte  Notiz: {notiz}')

# === Schritt 3: Lager-Nr-Liste für Dashboard exportieren ===
print('\n' + '='*78)
print('  Schritt 3: Export der Ohrdruf-Lager-Nrn als CSV für Dashboard')
print('='*78)
out_csv = USERHOME / 'Downloads' / 'ohrdruf_lagernrn_komplett.csv'
sold_match['lager_nr_str'] = sold_match['Lager Nr.'].astype(str).str.strip().str.replace(r'\.0+$', '', regex=True)
sold_match[['lager_nr_str','Order Nr.','Date','Supply','Supply Type','Brand','Product Group','JTL Selling Price','Portal Buying Price','Company']].to_csv(out_csv, sep=';', encoding='utf-8-sig', index=False)
print(f'  ✓ {out_csv}')
print(f'    {len(sold_match):,} Lager-Nrn als „OTTO_Kleingeraete_Ohrdruf" markierbar')

# Auch eine Liste der Bezahlt-Daten
print(f'\n  Verkaufs-Zustand:')
print(f'    Invoice Paid Y: {(sold_match["Invoice Paid"]=="Y").sum():,}')
print(f'    Invoice Paid N: {(sold_match["Invoice Paid"]=="N").sum():,}')
print(f'    Profit-Summe: {sold_match["Profit"].sum():,.0f} €')
print(f'    EK-Summe:     {sold_match["Portal Buying Price"].sum():,.0f} €')
print(f'    VK-Summe:     {sold_match["JTL Selling Price"].sum():,.0f} €')
