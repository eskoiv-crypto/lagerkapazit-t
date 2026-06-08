"""
BRÜCKE bauen: palette_otto → echte verkaufte Lager-Nrn
über BESTAND-Auftrags-Nr + Bestell-Nr-Muster "Ohrdruf"
"""
import sys, io, os, glob
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', line_buffering=True)
from pathlib import Path
import pandas as pd

USERHOME = Path(os.environ.get('USERPROFILE', os.path.expanduser('~')))

# === Schritt 1: ALLE palette_otto-IDs in ALLEN BESTAND-Snapshots suchen ===
print('='*78)
print('  Schritt 1: palette_otto-IDs durch alle BESTAND-Snapshots verfolgen')
print('='*78)
stock_rec = pd.read_excel(USERHOME/'Downloads'/'Stock_Received_April_2025_April_2026.xlsx')
po_ids = set(stock_rec[stock_rec['Supply Type']=='palette_otto']['Lager ID'].astype(str).str.strip().str.replace(r'\.0+$', '', regex=True))

BESTAND_DIR = USERHOME / 'OneDrive - elvinci.de GmbH' / 'elvinci - Bestandslisten AMM'
b_files = sorted(glob.glob(str(BESTAND_DIR / 'BESTAND134_*.CSV')))
print(f'  BESTAND-Files: {len(b_files)}')

# Alle BESTAND-Records mit palette_otto-IDs sammeln
all_bestand_po = []
for f in b_files:
    df = pd.read_csv(f, sep=';', encoding='ISO-8859-1', skiprows=1, header=None, low_memory=False)
    df[0] = df[0].astype(str)
    matches = df[df[0].isin(po_ids)].copy()
    matches['file'] = Path(f).name
    all_bestand_po.append(matches)

all_po = pd.concat(all_bestand_po, ignore_index=True)
print(f'  Gesamt-Records gefunden: {len(all_po):,}')
# Unique Lager-IDs in BESTAND
unique_po_in_bestand = all_po[0].unique()
print(f'  Unique palette_otto-IDs in BESTAND: {len(unique_po_in_bestand):,}')

# Spalte 10 = Auftrags-Nr
print(f'\n  Spalte 10 (Auftrags-Nrn) gefüllt: {all_po[10].notna().sum():,}')
print(f'  Unique Auftrags-Nrn: {all_po[10].dropna().nunique():,}')

# Spalte 8 = Notiz (OHRDRUF-...)
ohrdruf_notiz = all_po[all_po[8].astype(str).str.contains('OHRDRUF|Ohrdruf', regex=True, na=False)]
print(f'  Records mit OHRDRUF-Notiz: {len(ohrdruf_notiz):,}')

# Status
print(f'\n  Status-Spalte (9):')
print(all_po[9].value_counts().head(10).to_string())

# === Schritt 2: Diese Auftrags-Nrn in All-Sold suchen ===
print('\n' + '='*78)
print('  Schritt 2: Auftrags-Nrn (BESTAND→AU2026…) in All-Sold finden')
print('='*78)
auftrags_nrn = set(all_po[10].dropna().unique())
print(f'  Suche {len(auftrags_nrn):,} Auftrags-Nrn in All-Sold-Master…')

sold = pd.read_excel(USERHOME/'Downloads'/'All-Sold-Apr2025-Apr2026.xlsx')
sold_match = sold[sold['Order Nr.'].isin(auftrags_nrn)].copy()
print(f'  Treffer: {len(sold_match):,} Verkäufe aus diesen Aufträgen')

if len(sold_match)>0:
    print(f'\n  Klassifikation der gefundenen Verkäufe (Supply Type):')
    print(sold_match['Supply Type'].value_counts().to_string())
    print(f'\n  Produktgruppen:')
    print(sold_match['Product Group'].value_counts().head(15).to_string())
    print(f'\n  Top-Brands:')
    print(sold_match['Brand'].value_counts().head(10).to_string())
    print(f'\n  Verkaufs-Zeitraum:')
    sold_match['Date_dt'] = pd.to_datetime(sold_match['Date'])
    print(f'    {sold_match["Date_dt"].min().date()} – {sold_match["Date_dt"].max().date()}')

# === Schritt 3: Suche nach Bestell-Nr-Muster "Ohrdruf" in All-Sold Supply-Spalte ===
print('\n' + '='*78)
print('  Schritt 3: Direktsuche "Ohrdruf" im Supply-Feld von All-Sold')
print('='*78)
sold['Supply'] = sold['Supply'].astype(str)
ohrdruf_in_sold = sold[sold['Supply'].str.lower().str.contains('ohrdruf', na=False, regex=False)]
print(f'  Treffer: {len(ohrdruf_in_sold):,}')
if len(ohrdruf_in_sold)>0:
    print(f'  Supply-Werte:')
    print(ohrdruf_in_sold['Supply'].value_counts().head(10).to_string())
    print(f'\n  Supply Type bei diesen Treffern:')
    print(ohrdruf_in_sold['Supply Type'].value_counts().to_string())

# === Schritt 4: WP-Pipeline → Otto Kleingeräte Bestell-Nrn → All-Sold Supply ===
print('\n' + '='*78)
print('  Schritt 4: Verbindung WP-Pipeline → All-Sold über Bestell-Nr')
print('='*78)
wp_new = USERHOME / 'Downloads' / 'WARENEINGANG_PIPELINE_optimiert(Wareneingänge) (8).csv'
wp = pd.read_csv(wp_new, sep=';', encoding='cp1252', low_memory=False)
otto_kl = wp[wp['Lieferant (ELVINCI)']=='Otto Kleingeräte']
print(f'  Otto-Kleingeräte-Einträge in WP-Pipeline: {len(otto_kl):,}')
print(f'\n  Bestell-/Lieferschein-Nrn:')
for bn in otto_kl['Bestell-Nr./Lieferschein-Nr. (ELVINCI)'].dropna().unique()[:15]:
    print(f'    "{bn}"')
    # In All-Sold suchen mit DIESEM Pattern
    bn_clean = str(bn).strip()
    matches_sold = sold[sold['Supply'].str.contains(bn_clean, na=False, regex=False)]
    if len(matches_sold)>0:
        print(f'      ✓ {len(matches_sold)} Verkäufe gefunden!')

# === Schritt 5: Strategisch: alle möglichen Match-Wege auflisten ===
print('\n' + '='*78)
print('  Schritt 5: ZUSAMMENFASSUNG der Match-Strategien')
print('='*78)
print(f'  Direkte palette_otto-Lager-Nr in All-Sold: {sold["Lager Nr."].isin([int(x) for x in po_ids if x.isdigit()]).sum():,}')
print(f'  Via BESTAND-Auftrags-Nr → Sold: {len(sold_match):,} Verkäufe')
print(f'  Direkter "Ohrdruf"-String in Supply: {len(ohrdruf_in_sold):,}')

# Best estimate: WIE können wir Ohrdruf-Geräte tracken?
print('\n' + '='*78)
print('  LÖSUNG: Welche bekannten Lager-Nrn gehören zu Ohrdruf-Aufträgen?')
print('='*78)
if len(sold_match)>0:
    print(f'  Wir können {len(sold_match):,} verkaufte Geräte sicher Ohrdruf zuordnen.')
    print(f'  Methode: BESTAND-Lager-Nr → Auftrags-Nr → alle Geräte im selben Auftrag')
    out_csv = USERHOME / 'Downloads' / 'ohrdruf_lager_nrn.csv'
    sold_match[['Lager Nr.','Order Nr.','Date','Supply','Supply Type','Brand','Product Group','JTL Selling Price']].to_csv(out_csv, sep=';', encoding='utf-8-sig', index=False)
    print(f'  ✓ Liste exportiert: {out_csv}')

    # Bonus-Info: in welchem Zustand sind die in BESTAND?
    print(f'\n  Charakteristik der Bestand-Records:')
    for col_idx in range(min(12, all_po.shape[1])):
        sample_vals = all_po[col_idx].dropna().unique()[:3]
        print(f'    Spalte {col_idx}: {sample_vals}')
