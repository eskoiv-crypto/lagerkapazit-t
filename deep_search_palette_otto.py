"""
DEEP SEARCH: palette_otto in ALLEN Datenquellen
Stock-Analysis-Snapshots (≠ Stock-Received!), BESTAND, WP-Pipeline, JTL
"""
import sys, io, os, glob
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', line_buffering=True)
from pathlib import Path
import pandas as pd

USERHOME = Path(os.environ.get('USERPROFILE', os.path.expanduser('~')))

# === Erst: Liste der palette_otto-Lager-IDs aus Stock-Received ===
stock_rec = pd.read_excel(USERHOME/'Downloads'/'Stock_Received_April_2025_April_2026.xlsx')
po = stock_rec[stock_rec['Supply Type']=='palette_otto'].copy()
po_ids = set(po['Lager ID'].astype(str).str.strip().str.replace(r'\.0+$', '', regex=True))
print(f'palette_otto Lager-IDs aus Stock-Received: {len(po_ids):,}')
print(f'Beispiele: {sorted(list(po_ids))[:5]}')

print('\n' + '='*78)
print('  Quelle A: Stock-Analysis-Snapshots (≠ Stock-Received!)')
print('='*78)
STOCK_AN_DIRS = [
    USERHOME / 'OneDrive - elvinci.de GmbH' / 'Digital Experience - KI-Tools' / 'Stock Analysis',
    USERHOME / 'OneDrive - elvinci.de GmbH' / 'elvinci - Portal STOCK ANALYSIS',
]
sa_files = []
for d in STOCK_AN_DIRS:
    if d.exists():
        sa_files += list(d.glob('Stock-Analysis-*.xlsx'))
print(f'  Files gefunden: {len(sa_files)}')

found_po_in_sa = []
for f in sa_files[:15]:  # Sample der ersten 15
    try:
        df = pd.read_excel(f, nrows=5)
        # Spalten checken
        cols = list(df.columns)
        if 'supply_type' in [c.lower() for c in cols] or 'supply' in [c.lower() for c in cols]:
            df_full = pd.read_excel(f)
            sup_col = [c for c in df_full.columns if 'supply' in c.lower() and 'type' in c.lower()]
            if not sup_col:
                sup_col = [c for c in df_full.columns if c.lower()=='supply_type']
            if sup_col:
                po_in_file = df_full[df_full[sup_col[0]]=='palette_otto']
                if len(po_in_file)>0:
                    found_po_in_sa.append((f.name, len(po_in_file), df_full.columns.tolist()))
    except Exception as e:
        pass

if found_po_in_sa:
    print(f'\n  ✓ palette_otto in Stock-Analysis gefunden!')
    for name, n, cols in found_po_in_sa[:3]:
        print(f'    {name}: {n} Einträge')
        print(f'      Spalten: {cols}')
else:
    # Spalten der ersten Datei zeigen
    if sa_files:
        first = sa_files[0]
        df = pd.read_excel(first, nrows=3)
        print(f'\n  Spalten der ersten Stock-Analysis-Datei ({first.name}):')
        for c in df.columns:
            print(f'    {c}')

# Auch in einem aktuellen Stock-Analysis-File suchen
if sa_files:
    latest = sorted(sa_files)[-1]
    print(f'\n  Aktuellster Stock-Analysis: {latest.name}')
    df = pd.read_excel(latest)
    print(f'  Zeilen: {len(df):,}')
    print(f'  Alle Spalten: {df.columns.tolist()}')
    # Suche nach palette_otto in JEDER Text-Spalte
    for col in df.columns:
        try:
            mask = df[col].astype(str).str.lower().str.contains('palette_otto', regex=False, na=False)
            if mask.sum()>0:
                print(f'\n  ✓ Treffer in Spalte "{col}": {mask.sum()}')
                print(f'    Beispiele:')
                print(df[mask].head(3).to_string())
        except: pass

print('\n' + '='*78)
print('  Quelle B: BESTAND-Files (AMM-Bestandslisten)')
print('='*78)
BESTAND_DIR = USERHOME / 'OneDrive - elvinci.de GmbH' / 'elvinci - Bestandslisten AMM'
b_files = sorted(glob.glob(str(BESTAND_DIR / 'BESTAND134_*.CSV'))) if BESTAND_DIR.exists() else []
print(f'  Files: {len(b_files)}')
if b_files:
    # Lade aktuellstes
    latest_b = b_files[-1]
    print(f'  Aktuellstes: {Path(latest_b).name}')
    bdf = pd.read_csv(latest_b, sep=';', encoding='ISO-8859-1', skiprows=1, header=None, low_memory=False, nrows=5)
    print(f'  Spalten: {bdf.shape[1]}')
    bdf_full = pd.read_csv(latest_b, sep=';', encoding='ISO-8859-1', skiprows=1, header=None, low_memory=False)
    bdf_full[0] = bdf_full[0].astype(str)
    matches_b = bdf_full[bdf_full[0].isin(po_ids)]
    print(f'  palette_otto-Lager-IDs in BESTAND: {len(matches_b):,}')
    if len(matches_b)>0:
        print(f'  Beispiele:')
        print(matches_b.head(5).to_string())

print('\n' + '='*78)
print('  Quelle C: WP-Pipeline + Optimiert-File (Notizen / Bestell-Nrn)')
print('='*78)
WE_DIR = USERHOME / 'OneDrive - elvinci.de GmbH' / 'elvinci - WE Pipeline elvinci'
wp_files = list(WE_DIR.glob('WARENEINGANG_PIPELINE*.csv')) if WE_DIR.exists() else []
wp_new = USERHOME / 'Downloads' / 'WARENEINGANG_PIPELINE_optimiert(Wareneingänge) (8).csv'
if wp_new.exists():
    wp_files.append(wp_new)
print(f'  Files: {len(wp_files)}')

# Suche nach "Ohrdruf" oder "Kleingerät" oder "palette" in allen WP-Files
po_hits = []
for f in wp_files:
    try:
        try:
            df = pd.read_csv(f, sep=';', encoding='cp1252', low_memory=False)
        except:
            df = pd.read_csv(f, sep=';', encoding='iso-8859-1', low_memory=False)
        for col in df.columns:
            try:
                s = df[col].astype(str).str.lower()
                mask = s.str.contains('ohrdruf|kleingerät|kleingerat|palette_otto', regex=True, na=False)
                if mask.sum()>0:
                    print(f'\n  ✓ {Path(f).name} — Spalte "{col}": {mask.sum()} Treffer')
                    for _, row in df[mask].head(5).iterrows():
                        bn_col = [c for c in df.columns if 'bestell' in c.lower() or 'lieferschein' in c.lower()]
                        wd_col = [c for c in df.columns if 'wareneingang' in c.lower()]
                        bn = row[bn_col[0]] if bn_col else 'n/a'
                        wd = row[wd_col[0]] if wd_col else 'n/a'
                        print(f'    Bestell-Nr: {bn}  WE: {wd}  Spalte-Wert: {row[col][:60]}')
                        po_hits.append({'bn': bn, 'wd': wd, 'val': row[col][:80]})
            except: pass
    except Exception as e:
        pass

print('\n' + '='*78)
print('  Quelle D: JTL-Export — Bezeichnung / Hinweis / Bestell Nr.')
print('='*78)
JTL_LOCAL = USERHOME / 'Downloads' / 'JTL-Export-Aufträge-11052026.csv'
if JTL_LOCAL.exists():
    jtl = pd.read_csv(JTL_LOCAL, sep=';', encoding='iso-8859-1', low_memory=False)
    for col in ['Bezeichnung','Hinweis','Bestell Nr.']:
        if col in jtl.columns:
            mask = jtl[col].astype(str).str.lower().str.contains('ohrdruf|kleingerät|kleingerat|palette', regex=True, na=False)
            if mask.sum()>0:
                print(f'  ✓ Spalte "{col}": {mask.sum()} Treffer')
                print(jtl[mask][[col,'Artikelnummer','Auftragsdatum']].head(10).to_string())
else:
    print(f'  ⚠ JTL nicht lokal verfügbar')

print('\n' + '='*78)
print('  Quelle E: Alle palette_otto-Lager-IDs in JTL?')
print('='*78)
if JTL_LOCAL.exists():
    jtl = pd.read_csv(JTL_LOCAL, sep=';', encoding='iso-8859-1', low_memory=False)
    jtl['Artikelnummer'] = jtl['Artikelnummer'].astype(str).str.strip().str.replace(r'\.0+$', '', regex=True)
    jtl_match = jtl[jtl['Artikelnummer'].isin(po_ids)]
    print(f'  palette_otto-IDs in JTL: {len(jtl_match):,}')
    if len(jtl_match)>0:
        print(f'  Beispiele:')
        print(jtl_match[['Bestell Nr.','Kunden-Nr','Artikelnummer','Bezeichnung','Auftragsdatum','Datum Zahlungseingang']].head(10).to_string())

print('\n' + '='*78)
print('  Quelle F: BESTAND aktuell — wo sind die palette_otto-IDs heute?')
print('='*78)
if b_files:
    # Status der palette_otto-IDs prüfen
    bdf = pd.read_csv(b_files[-1], sep=';', encoding='ISO-8859-1', skiprows=1, header=None, low_memory=False)
    bdf[0] = bdf[0].astype(str)
    in_bestand = bdf[bdf[0].isin(po_ids)]
    print(f'  In aktuellem BESTAND ({Path(b_files[-1]).name}): {len(in_bestand):,}')
    if len(in_bestand)>0:
        # Welche Spalten? Schau dir das an
        print(f'  Spalten-Beispiel:')
        print(in_bestand.iloc[0].head(15).to_string())

# === ZIEL: gibt es ein Mapping palette_otto-ID → reale verkaufte Lager-Nr? ===
print('\n' + '='*78)
print('  HYPOTHESE: Ist eine palette_otto-ID eventuell ein Original-Eingangs-ID,')
print('  die später zu mehreren konkreten Lager-Nrn aufgesplittet wurde?')
print('='*78)
# Schau ob im aktuellen Stock-Analysis-File die palette_otto-IDs noch sind UND ob sie eine Brand bekommen haben
if sa_files:
    latest_sa = sorted(sa_files)[-1]
    df = pd.read_excel(latest_sa)
    print(f'  Letzter Stock-Analysis: {latest_sa.name}')
    if 'lager_number' in df.columns:
        df['lager_number'] = df['lager_number'].astype(str)
        po_in_sa = df[df['lager_number'].isin(po_ids)]
        print(f'  palette_otto-IDs noch im aktuellen Stock-Analysis: {len(po_in_sa):,}')
        if len(po_in_sa)>0:
            print(f'  Beispiele mit Status:')
            cols_to_show = [c for c in df.columns if c in ['lager_number','supply_type','brand','product_group','article','datetime_upload','product_life_days']]
            print(po_in_sa[cols_to_show].head(10).to_string())
