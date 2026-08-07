"""
GAP-Diagnose: wo genau brechen die 39,4% der Datenkette?
Strikt drehende Ware = OTTO_MIX + AEG_Schrott
"""
import sys, io, os, glob
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', line_buffering=True)
from pathlib import Path
import pandas as pd

USERHOME = Path(os.environ.get('USERPROFILE', os.path.expanduser('~')))
DREHEND = ['OTTO_MIX', 'AEG_Schrott']

# === Portal-Sold = Ground Truth ===
ALLSOLD_DIR = USERHOME / 'Downloads' / 'All Sold 2025 - 2026'
files = sorted(glob.glob(str(ALLSOLD_DIR / 'All-Sold-2026-05-07T*.xlsx')))
portal = pd.concat([pd.read_excel(f) for f in files], ignore_index=True)
portal = portal.drop_duplicates(subset=['Lager Nr.'], keep='first')
portal['Date_dt'] = pd.to_datetime(portal['Date'], errors='coerce')
portal['lager_nr_str'] = portal['Lager Nr.'].astype(str).str.strip().str.replace(r'\.0+$', '', regex=True)

dreh_2026 = portal[(portal['Date_dt'].dt.year==2026) & (portal['Supply Type'].isin(DREHEND))].copy()
print(f'Ground Truth: {len(dreh_2026):,} drehende Verkäufe 2026')

# === Sample mit Datenkette ===
m = pd.read_csv(USERHOME/'Downloads'/'we_to_paid_full.csv', sep=';', encoding='utf-8-sig', low_memory=False)
m['sold_dt'] = pd.to_datetime(m['sold_dt'])
m['Bezahlt_dt'] = pd.to_datetime(m['Bezahlt_dt'])
m['we_dt'] = pd.to_datetime(m['we_dt'])
m_dreh = m[(m['sold_dt'].dt.year==2026) & (m['Supply Type'].isin(DREHEND))].copy()
print(f'In we_to_paid_full enthalten: {len(m_dreh):,}')

# Lager-Nrn die in Portal-Sold sind aber NICHT in m_dreh
missing_lager = set(dreh_2026['lager_nr_str']) - set(m_dreh['lager_nr_str'].astype(str))
in_both = set(dreh_2026['lager_nr_str']) & set(m_dreh['lager_nr_str'].astype(str))
print(f'In beiden Listen: {len(in_both):,}')
print(f'NICHT in we_to_paid_full: {len(missing_lager):,}')

# Bei den vorhandenen: was fehlt im Detail?
print('\n' + '='*70)
print('BRUCHSTELLEN-Analyse für ALLE Portal-Sold drehend 2026')
print('='*70)

# Merge: jeder Verkauf aus Portal + Detail-Status
dreh_2026['lager_str'] = dreh_2026['lager_nr_str']
m_dreh['lager_str'] = m_dreh['lager_nr_str'].astype(str)
merged = dreh_2026.merge(m_dreh[['lager_str', 'we_tier', 'Bezahlt_dt', 'we_dt']],
                          on='lager_str', how='left')

# Klassifikation pro Gerät
def classify(row):
    in_sample = pd.notna(row['we_tier'])
    has_we = in_sample and row['we_tier'] != 'NONE'
    has_paid = pd.notna(row['Bezahlt_dt'])
    if has_we and has_paid: return '✓ vollständig'
    if not in_sample:         return '✗ nicht in we_to_paid_full überhaupt'
    if not has_we:            return '✗ kein WE-Datum'
    if not has_paid:          return '✗ kein Bezahlt-Datum (JTL)'
    return '?'

merged['status'] = merged.apply(classify, axis=1)
status_counts = merged['status'].value_counts()
print(f'\nGesamtaufschlüsselung (n={len(merged):,}):')
for s, n in status_counts.items():
    print(f'  {s:<50} {n:>6,}  ({n/len(merged)*100:>5.1f}%)')

# Pro Bruchstellen-Typ — was hilft?
print('\n' + '='*70)
print('Bruchstelle 1: Kein Bezahlt-Datum (JTL-Mismatch)')
print('='*70)
no_paid = merged[merged['status'] == '✗ kein Bezahlt-Datum (JTL)']
print(f'  n = {len(no_paid):,}')
print(f'  Verkaufsmonate-Verteilung:')
print(no_paid['Date_dt'].dt.to_period('M').value_counts().sort_index().to_string())
print(f'\n  Pro Lieferant:')
print(no_paid['Supply Type'].value_counts().to_string())
print(f'\n  → Diese Geräte sind in unserer Stock-Analysis/BESTAND/WP gefunden')
print(f'    aber haben KEINE JTL-Rechnung — vermutlich Marketplace-Verkäufe!')
print(f'    (Amazon, eBay, Kaufland, Otto-Market — Zahlung direkt vom Marketplace)')

# Welche Lager-Nr-Form? Vielleicht JTL-Match-Logik-Problem
sample_no_paid = no_paid.head(5)[['Lager Nr.', 'Date_dt', 'Supply Type']]
print(f'\n  Beispiel-Lager-Nrn (für JTL-Quercheck):')
for _, r in sample_no_paid.iterrows():
    print(f'    {r["Lager Nr."]} | {r["Date_dt"].date()} | {r["Supply Type"]}')

print('\n' + '='*70)
print('Bruchstelle 2: Kein WE-Datum (Stock/WP/BESTAND alle leer)')
print('='*70)
no_we = merged[merged['status'].isin(['✗ kein WE-Datum', '✗ nicht in we_to_paid_full überhaupt'])]
print(f'  n = {len(no_we):,}')
print(f'  Verkaufsmonate-Verteilung:')
print(no_we['Date_dt'].dt.to_period('M').value_counts().sort_index().to_string())
print(f'\n  → Geräte ohne ein einziges WE-Snapshot in keiner unserer 3 Quellen.')
print(f'    Ursache: Daten-Lücke vor März 2026 (BESTAND-Snapshot-Start),')
print(f'    Stock-Analysis-Snapshot-Lücken, WP-Pipeline-Unvollständigkeit.')

# Wann begann das BESTAND-Snapshot-Sampling?
BESTAND_DIR = USERHOME / 'OneDrive - elvinci.de GmbH' / 'elvinci - Bestandslisten AMM'
bestand_files = sorted(glob.glob(str(BESTAND_DIR / 'BESTAND134_*.CSV')))
if bestand_files:
    first = Path(bestand_files[0]).name
    last = Path(bestand_files[-1]).name
    print(f'\n  BESTAND-Snapshot-Range: {first} – {last} ({len(bestand_files)} Files)')

WE_PIPE_DIR = USERHOME / 'OneDrive - elvinci.de GmbH' / 'elvinci - WE Pipeline elvinci'
wp_files = sorted(glob.glob(str(WE_PIPE_DIR / 'WARENEINGANG_PIPELINE*.csv')))
if wp_files:
    print(f'  WP-Pipeline-Files: {len(wp_files)}')
    for f in wp_files:
        print(f'    {Path(f).name}')

STOCK_DIR = USERHOME / 'OneDrive - elvinci.de GmbH' / 'Digital Experience - KI-Tools' / 'Stock Analysis'
stock_files = sorted(glob.glob(str(STOCK_DIR / 'Stock-Analysis-*.xlsx')))
if stock_files:
    print(f'  Stock-Analysis-Files: {len(stock_files)}')
    for f in stock_files[-5:]:
        print(f'    {Path(f).name}')

print('\n' + '='*70)
print('AKTIONS-PLAN zur Gap-Schließung')
print('='*70)
print(f'''
  GAP 1 — Kein Bezahlt-Datum ({len(no_paid):,} Geräte):
    → Marketplace-Daten beschaffen:
        • Amazon Seller Central (Settlement-Reports → Auszahlungs-Datum)
        • eBay Verkäufer-Konto (Bestellungen-Export mit Bezahlt-Datum)
        • Kaufland.de Händler-Center
        • Otto Market Partner-Portal
      → Schließt voraussichtlich 80 %+ der no_paid-Lücke
    → Alternativ: JTL-Export VOLLSTÄNDIG (alle Aufträge, nicht nur 1 Tag)
        • Aktueller Export = 07.05.2026 Snapshot — könnte unvollständig sein
        • Vollexport mit allen 2025+2026 Aufträgen prüfen

  GAP 2 — Kein WE-Datum ({len(no_we):,} Geräte):
    → BESTAND-Historie 2025 nachladen:
        • Alle 2025er BESTAND_*.CSV einlesen (Pre-März-Snapshots)
        • Schließt WE-Lücke für 2025-Eingänge die 2026 verkauft werden
    → Lieferanten-Belege (OneDrive/Outlook):
        • OTTO/AEG-Lieferavise enthalten WE-Datum exakt
        • Email-Parsing analog zum Rechnungsprüfung-Outlook-Projekt
    → AMM-Roh-Daten (falls vorhanden):
        • WE-Buchungen im Lagerverwaltungssystem direkt anzapfen
        • SQL-Query gegen AMM-DB statt CSV-Snapshots

  PRAGMATISCHE Alternative bei zeitkritischer Auswertung:
    → Imputation: für Geräte ohne WE-Datum schätzen mit
      Median-WE-Alter ihres Lieferanten (OTTO 3T, AEG 6T)
    → ergibt eine valide statistische Hochrechnung
    → ehrlicher Hinweis "X% imputiert" im Report
''')

# Zeige auch die Lager-Nr-Pattern der fehlenden — vielleicht ist es ein Format-Problem
print('='*70)
print('Lager-Nr-Format-Check: gibt es ein systematisches Match-Problem?')
print('='*70)
print('  Beispiele in_both (matched):')
for x in list(in_both)[:5]:
    print(f'    "{x}"')
print('  Beispiele missing (nicht gematcht):')
for x in list(missing_lager)[:5]:
    print(f'    "{x}"')
