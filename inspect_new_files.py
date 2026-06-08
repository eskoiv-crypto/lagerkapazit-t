"""Inspiziere die neuen Daten-Quellen vor der Berechnung"""
import sys, io, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', line_buffering=True)
from pathlib import Path
import pandas as pd

USERHOME = Path(os.environ.get('USERPROFILE', os.path.expanduser('~')))
DL = USERHOME / 'Downloads'

print('='*75)
print('FILE 1: WARENEINGANG_PIPELINE_optimiert (8).csv  — NEUE WP-Pipeline')
print('='*75)
wp_new = DL / 'WARENEINGANG_PIPELINE_optimiert(Wareneingänge) (8).csv'
print(f'  Size: {wp_new.stat().st_size:,} B')

# Encoding-Detection
for enc in ['utf-8-sig', 'utf-8', 'cp1252', 'iso-8859-1']:
    try:
        df = pd.read_csv(wp_new, sep=';', encoding=enc, nrows=3, low_memory=False)
        print(f'  ✓ Encoding: {enc}')
        encoding = enc
        break
    except Exception as e:
        continue
wp = pd.read_csv(wp_new, sep=';', encoding=encoding, low_memory=False)
print(f'  Rows: {len(wp):,}  Cols: {len(wp.columns)}')
print(f'  Columns:')
for i, c in enumerate(wp.columns):
    samples = wp[c].dropna().head(2).tolist()
    print(f'    [{i:>2}] {c[:45]:<45}  → {str(samples)[:60]}')

# Suche nach Datum-Spalten und Lager/Bestell-Nr
date_cols = [c for c in wp.columns if any(t in c.lower() for t in ['datum', 'date', 'eingang'])]
ident_cols = [c for c in wp.columns if any(t in c.lower() for t in ['lager', 'bestell', 'lieferschein', 'palette', 'sscc'])]
print(f'\n  Datum-Spalten: {date_cols}')
print(f'  Ident-Spalten: {ident_cols}')

print('\n' + '='*75)
print('FILE 2: FULFILMENT PIPELINE (Aufträge) (9).csv  — NEU')
print('='*75)
ff_new = DL / 'FULFILMENT PIPELINE(Aufträge) (9).csv'
print(f'  Size: {ff_new.stat().st_size:,} B')
for enc in ['utf-8-sig', 'utf-8', 'cp1252', 'iso-8859-1']:
    try:
        df = pd.read_csv(ff_new, sep=';', encoding=enc, nrows=3, low_memory=False)
        encoding = enc
        break
    except Exception:
        continue
ff = pd.read_csv(ff_new, sep=';', encoding=encoding, low_memory=False)
print(f'  Encoding: {encoding}  ·  Rows: {len(ff):,}  Cols: {len(ff.columns)}')
print(f'  Columns:')
for i, c in enumerate(ff.columns):
    samples = ff[c].dropna().head(2).tolist()
    print(f'    [{i:>2}] {c[:50]:<50}  → {str(samples)[:55]}')

print('\n' + '='*75)
print('FILE 3: JTL-Export-Aufträge-11052026.csv  — FRISCHER JTL-EXPORT')
print('='*75)
jtl_path = Path('W:/DUSTIN EXPORTE 2026/JTL-Export-Aufträge-11052026.csv')
print(f'  Size: {jtl_path.stat().st_size:,} B')
for enc in ['utf-8-sig', 'iso-8859-1', 'cp1252', 'utf-8']:
    try:
        df = pd.read_csv(jtl_path, sep=';', encoding=enc, nrows=3, low_memory=False)
        encoding = enc
        break
    except Exception:
        continue
jtl = pd.read_csv(jtl_path, sep=';', encoding=encoding, low_memory=False)
print(f'  Encoding: {encoding}  ·  Rows: {len(jtl):,}  Cols: {len(jtl.columns)}')

# Bezahlt-Datum-Statistik
bez_col = [c for c in jtl.columns if 'zahlung' in c.lower() and 'datum' in c.lower()]
art_col = [c for c in jtl.columns if 'artikelnummer' in c.lower() or c.lower() == 'artikelnr'][:1]
print(f'  Zahlungs-Spalte: {bez_col}')
print(f'  Artikel-Spalte: {art_col}')
if bez_col:
    paid = pd.to_datetime(jtl[bez_col[0]], errors='coerce', dayfirst=True)
    print(f'  Bezahlt-Datum-Range: {paid.min()} – {paid.max()}')
    print(f'  Aufträge mit Bezahlt-Datum: {paid.notna().sum():,} / {len(jtl):,}')
    print(f'  Aufträge nach 2026-05-07 bezahlt: {(paid >= pd.Timestamp("2026-05-07")).sum():,}  (NEU seit letztem Export!)')

# Vergleich mit altem JTL
old_jtl = Path('W:/DUSTIN EXPORTE 2026/JTL-Export-Aufträge-07052026.csv')
if old_jtl.exists():
    jtl_old = pd.read_csv(old_jtl, sep=';', encoding='iso-8859-1', low_memory=False)
    print(f'\n  Vergleich alt vs. neu:')
    print(f'    Alt (07.05.): {len(jtl_old):,} Aufträge')
    print(f'    Neu (11.05.): {len(jtl):,} Aufträge')
    print(f'    Delta: +{len(jtl)-len(jtl_old):,}')
