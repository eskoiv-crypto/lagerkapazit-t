"""
Bearbeitungszeit-Analyse: Wareneingang → Verkauf → Bezahlt
Multi-Source-Join: BESTAND × Portal-Sold × JTL-Aufträge
"""
import sys, io, glob, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', line_buffering=True)
from pathlib import Path
import pandas as pd
import numpy as np

USERHOME = Path(os.environ.get('USERPROFILE', os.path.expanduser('~')))
ALLSOLD_DIR = USERHOME / 'Downloads' / 'All Sold 2025 - 2026'
BESTAND_DIR = USERHOME / 'OneDrive - elvinci.de GmbH' / 'elvinci - Bestandslisten AMM'
JTL_FILE = r'W:\DUSTIN EXPORTE 2026\JTL-Export-Aufträge-07052026.csv'

# === 1. BESTAND laden — WE-Datum pro Lager-Nr ===
print('=' * 70)
print('  SCHRITT 1: BESTAND-Snapshots → WE-Datum pro Lager-Nr')
print('=' * 70)

bestand_files = sorted(glob.glob(str(BESTAND_DIR / 'BESTAND134_*.CSV')))
print(f'  {len(bestand_files)} Snapshots')

# Erst eine Datei inspizieren — Header
sample = pd.read_csv(bestand_files[0], sep=';', encoding='ISO-8859-1', nrows=3, header=None)
print(f'  Spalten Sample (Zeile 0/1):')
for i in range(min(15, sample.shape[1])):
    print(f'    Col[{i}]: {[str(sample.iloc[r, i])[:30] for r in range(min(2, len(sample)))]}')

# Aus Codex/Validierung: typischerweise Spalte 0=Palette, Col 7=WE-Datum (laut Dashboard-Code)
# Lass uns Spalte 7 prüfen
sample_full = pd.read_csv(bestand_files[0], sep=';', encoding='ISO-8859-1', skiprows=1, header=None, nrows=10)
print(f'\n  Spalten ab Zeile 1 (skip Header):')
for i in range(min(15, sample_full.shape[1])):
    print(f'    Col[{i}]: {sample_full.iloc[:3, i].tolist()}')

# Alle Snapshots zu einer Union mergen, frühestes WE-Datum pro Lager-Nr
all_bestand = []
for f in bestand_files:
    df = pd.read_csv(f, sep=';', encoding='ISO-8859-1', skiprows=1, header=None, low_memory=False)
    if df.shape[1] >= 8:
        # Col 0 = Palette, Col 1 = Artikel/Lager-Nr, Col 7 = WE-Datum
        df = df[[0, 1, 7]].copy()
        df.columns = ['palette', 'lager_nr', 'we_datum']
        df['source_file'] = Path(f).name
        all_bestand.append(df)

bestand_union = pd.concat(all_bestand, ignore_index=True)
print(f'\n  Total BESTAND-Records: {len(bestand_union):,}')
print(f'  Unique Lager-Nrn:      {bestand_union["lager_nr"].nunique():,}')

# WE-Datum parsen (Format: vermutlich DD.MM.YYYY)
bestand_union['we_datum_parsed'] = pd.to_datetime(bestand_union['we_datum'], errors='coerce', dayfirst=True)
print(f'  Davon WE-Datum geparst: {bestand_union["we_datum_parsed"].notna().sum():,}')
print(f'  Datums-Range: {bestand_union["we_datum_parsed"].min()} – {bestand_union["we_datum_parsed"].max()}')

# Pro Lager-Nr das früheste WE-Datum
we_per_lager = (
    bestand_union.dropna(subset=['we_datum_parsed'])
    .groupby('lager_nr')['we_datum_parsed'].min()
    .reset_index()
    .rename(columns={'we_datum_parsed': 'we_datum'})
)
we_per_lager['lager_nr_str'] = we_per_lager['lager_nr'].astype(str).str.strip()
print(f'  Lager-Nrn mit WE-Datum: {len(we_per_lager):,}')

# === 2. Portal-Sold laden ===
print('\n' + '=' * 70)
print('  SCHRITT 2: Portal-Sold → Sold-Datum + Lager-Nr')
print('=' * 70)
files = sorted(glob.glob(str(ALLSOLD_DIR / 'All-Sold-2026-05-07T*.xlsx')))
portal = pd.concat([pd.read_excel(f) for f in files], ignore_index=True)
portal = portal.drop_duplicates(subset=['Lager Nr.'], keep='first').copy()
portal['Date'] = pd.to_datetime(portal['Date'], errors='coerce').dt.normalize()
portal['lager_nr_str'] = portal['Lager Nr.'].astype(str).str.strip().str.replace(r'\.0+$', '', regex=True)
print(f'  Portal-Sold n: {len(portal):,}')
print(f'  Sold-Datums-Range: {portal["Date"].min().date()} – {portal["Date"].max().date()}')

# Order Nr. (für JTL-Match)
print(f'  Order Nr. Beispiele: {portal["Order Nr."].dropna().head(3).tolist()}')

# === 3. JTL-Aufträge laden ===
print('\n' + '=' * 70)
print('  SCHRITT 3: JTL-Aufträge → Auftragsdatum + Bezahlt-Datum')
print('=' * 70)
jtl = None
for enc in ['cp1252', 'iso-8859-1', 'utf-8-sig']:
    try:
        jtl = pd.read_csv(JTL_FILE, sep=';', encoding=enc, low_memory=False)
        print(f'  Encoding: {enc} ✓')
        break
    except UnicodeDecodeError:
        continue
if jtl is None:
    raise SystemExit('JTL nicht parsbar')
print(f'  JTL Rows: {len(jtl):,}')
print(f'  Bestell-Nrn (unique): {jtl["Bestell Nr."].nunique():,}')

# Datums parsen (DE-Format DD.MM.YYYY)
jtl['Auftragsdatum_dt'] = pd.to_datetime(jtl['Auftragsdatum'], errors='coerce', dayfirst=True)
jtl['Bezahlt_dt'] = pd.to_datetime(jtl['Datum Zahlungseingang'], errors='coerce', dayfirst=True)
print(f'  Auftragsdatum geparst: {jtl["Auftragsdatum_dt"].notna().sum():,}')
print(f'  Bezahldatum geparst:   {jtl["Bezahlt_dt"].notna().sum():,}')

# Lager-Nr (= Artikelnummer)
jtl['lager_nr_str'] = jtl['Artikelnummer'].astype(str).str.strip().str.replace(r'\.0+$', '', regex=True)
print(f'  Artikelnr Beispiele: {jtl["lager_nr_str"].head(3).tolist()}')

# Pro Lager-Nr (Artikelnr) den ersten Auftrag (frühestes Auftragsdatum + zugehöriges Bezahlt)
jtl_per_lager = jtl.dropna(subset=['Auftragsdatum_dt', 'lager_nr_str']).copy()
# Bezahlt-Datum: pro Bestellung (eine Bestellung = ein Bezahlt)
jtl_per_lager = jtl_per_lager.sort_values('Auftragsdatum_dt').drop_duplicates('lager_nr_str', keep='first')
print(f'  Lager-Nrn in JTL: {len(jtl_per_lager):,}')

# === 4. JOIN: Lager-Nr × WE × Sold × Bezahlt ===
print('\n' + '=' * 70)
print('  SCHRITT 4: Multi-Source-JOIN auf Lager-Nr.')
print('=' * 70)

portal['sold_dt'] = portal['Date']
portal['Invoice_Date_dt'] = pd.to_datetime(portal['Invoice Date'], errors='coerce').dt.normalize()
merged = portal[['lager_nr_str', 'sold_dt', 'Order Nr.', 'Supply Type',
                 'JTL Selling Price', 'Portal Buying Price', 'Invoice_Date_dt', 'Invoice Paid']].copy()

# Join WE-Datum
merged = merged.merge(we_per_lager[['lager_nr_str', 'we_datum']], on='lager_nr_str', how='left')

# Join JTL Bezahlt
merged = merged.merge(jtl_per_lager[['lager_nr_str', 'Auftragsdatum_dt', 'Bezahlt_dt']],
                       on='lager_nr_str', how='left')

print(f'  Total merged rows:                {len(merged):,}')
print(f'  Davon mit WE-Datum:               {merged["we_datum"].notna().sum():,}  ({merged["we_datum"].notna().mean()*100:.1f}%)')
print(f'  Davon mit Bezahlt-Datum (JTL):    {merged["Bezahlt_dt"].notna().sum():,}  ({merged["Bezahlt_dt"].notna().mean()*100:.1f}%)')
print(f'  Davon mit BEIDEN:                 {(merged["we_datum"].notna() & merged["Bezahlt_dt"].notna()).sum():,}')

# Cycle-Time-Berechnung
merged['t_we_to_sold']    = (merged['sold_dt'] - merged['we_datum']).dt.days
merged['t_sold_to_paid']  = (merged['Bezahlt_dt'] - merged['sold_dt']).dt.days
merged['t_we_to_paid']    = (merged['Bezahlt_dt'] - merged['we_datum']).dt.days
merged['t_order_to_paid'] = (merged['Bezahlt_dt'] - merged['Auftragsdatum_dt']).dt.days

# Filter unsinnige Werte (negative Tage = Datenqualität)
def stats(series, label):
    s = series.dropna()
    s = s[(s >= -10) & (s <= 1000)]   # extreme Outlier wegschneiden
    if len(s) == 0: return
    print(f'\n  {label} (n={len(s):,})')
    print(f'    Mean:   {s.mean():>7.1f} Tage')
    print(f'    Median: {s.median():>7.1f} Tage')
    print(f'    P25:    {s.quantile(0.25):>7.1f} Tage')
    print(f'    P75:    {s.quantile(0.75):>7.1f} Tage')
    print(f'    P90:    {s.quantile(0.90):>7.1f} Tage')
    print(f'    P95:    {s.quantile(0.95):>7.1f} Tage')

print('\n' + '=' * 70)
print('  SCHRITT 5: Bearbeitungszeit-Statistiken')
print('=' * 70)
stats(merged['t_we_to_sold'],   'WE → Verkauf (Lager-Verweildauer)')
stats(merged['t_sold_to_paid'], 'Verkauf → Bezahlt (Zahlungs-Geschwindigkeit)')
stats(merged['t_we_to_paid'],   'WE → Bezahlt (FULL CYCLE = User-Frage)')
stats(merged['t_order_to_paid'],'Bestellung → Bezahlt (JTL-only)')

# === Pro Lieferant ===
print('\n' + '=' * 70)
print('  SCHRITT 6: Full-Cycle-Time pro Lieferant (Top-15)')
print('=' * 70)
sup_stats = merged.dropna(subset=['t_sold_to_paid']).groupby('Supply Type').agg(
    n=('t_sold_to_paid', 'count'),
    mean_d=('t_sold_to_paid', 'mean'),
    median_d=('t_sold_to_paid', 'median'),
    p90_d=('t_sold_to_paid', lambda x: x.quantile(0.9))
).sort_values('n', ascending=False).head(15)
print(f'\n  {"Lieferant":<28}{"n":>7}{"Mean":>8}{"Median":>8}{"P90":>8}')
print('  ' + '-' * 60)
for sup, row in sup_stats.iterrows():
    print(f'  {str(sup)[:28]:<28}{int(row.n):>7,}{row.mean_d:>7.1f}T{row.median_d:>7.1f}T{row.p90_d:>7.1f}T')

# === Speichern fürs HTML-Generator ===
out_csv = USERHOME / 'Downloads' / 'cycle_time_analysis.csv'
keep_cols = ['lager_nr_str', 'Supply Type', 'we_datum', 'sold_dt', 'Auftragsdatum_dt', 'Bezahlt_dt',
             't_we_to_sold', 't_sold_to_paid', 't_we_to_paid', 't_order_to_paid',
             'JTL Selling Price', 'Portal Buying Price']
merged[keep_cols].to_csv(out_csv, sep=';', index=False, encoding='utf-8-sig')
print(f'\n  ✓ Detail-CSV gespeichert: {out_csv}')

# === Match-Quote: wie viele Geräte erreichen wir wirklich? ===
print('\n' + '=' * 70)
print('  SCHRITT 7: Datenqualität / Match-Quote')
print('=' * 70)
sold_2026_we = (
    portal.merge(we_per_lager[['lager_nr_str', 'we_datum']], on='lager_nr_str', how='left')
)
print(f'  Portal-Sold 2025+2026:                {len(portal):,}')
print(f'  Davon Match auf BESTAND-WE-Datum:    {sold_2026_we["we_datum"].notna().sum():,} ({sold_2026_we["we_datum"].notna().mean()*100:.1f}%)')
print(f'  Davon Match auf JTL-Bezahlt:         {merged["Bezahlt_dt"].notna().sum():,} ({merged["Bezahlt_dt"].notna().mean()*100:.1f}%)')
print(f'  Beide vorhanden (für FULL-CYCLE):    {(merged["we_datum"].notna() & merged["Bezahlt_dt"].notna()).sum():,}')

print('\n  Hinweis warum Match-Quote begrenzt:')
print('  - BESTAND-Snapshots nur 9 Tage (07.04. - 24.04.2026) → WE-Datum nur für 2026er Verkäufe ab März')
print('  - 2025-Verkäufe: WE war vor BESTAND-Aufzeichnung → keine WE-Daten')
print('  - JTL-Aufträge: nur Stk mit gespeicherter Zahlung — Online-Verkäufe ohne JTL-Auftrag fehlen')
