"""
WE → Bezahlt Cycle-Time — BEREINIGTE Version mit FRISCHEN Daten
Stand: 11.05.2026 + zusätzliche Quellen
"""
import sys, io, glob, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', line_buffering=True)
from pathlib import Path
import pandas as pd

USERHOME = Path(os.environ.get('USERPROFILE', os.path.expanduser('~')))
DL = USERHOME / 'Downloads'
ALLSOLD_DIR  = DL / 'All Sold 2025 - 2026'
BESTAND_DIR  = USERHOME / 'OneDrive - elvinci.de GmbH' / 'elvinci - Bestandslisten AMM'
WE_PIPE_DIR  = USERHOME / 'OneDrive - elvinci.de GmbH' / 'elvinci - WE Pipeline elvinci'
STOCK_DIR_1  = USERHOME / 'OneDrive - elvinci.de GmbH' / 'Digital Experience - KI-Tools' / 'Stock Analysis'
STOCK_DIR_2  = USERHOME / 'OneDrive - elvinci.de GmbH' / 'elvinci - Portal STOCK ANALYSIS'
JTL_FILE     = r'W:\DUSTIN EXPORTE 2026\JTL-Export-Aufträge-11052026.csv'   # ★ NEU 11.05.
WP_NEW       = DL / 'WARENEINGANG_PIPELINE_optimiert(Wareneingänge) (8).csv'  # ★ NEU

print('='*72)
print('  STEP 1 — Portal-Sold')
print('='*72)
files = sorted(glob.glob(str(ALLSOLD_DIR / 'All-Sold-2026-05-07T*.xlsx')))
portal = pd.concat([pd.read_excel(f) for f in files], ignore_index=True)
portal = portal.drop_duplicates(subset=['Lager Nr.'], keep='first').copy()
portal['sold_dt'] = pd.to_datetime(portal['Date'], errors='coerce').dt.normalize()
portal['lager_nr_str'] = portal['Lager Nr.'].astype(str).str.strip().str.replace(r'\.0+$', '', regex=True)
portal['supply_clean'] = portal['Supply'].astype(str).str.strip()
print(f'  Portal-Sold n: {len(portal):,}')

print('\n' + '='*72)
print('  STEP 2 — TIER 1 Stock-Analysis (datetime_upload)')
print('='*72)
stock_files = sorted(set(glob.glob(str(STOCK_DIR_1 / 'Stock-Analysis-*.xlsx'))
                       + glob.glob(str(STOCK_DIR_2 / 'Stock-Analysis-*.xlsx'))))
print(f'  Files: {len(stock_files)}')
all_stock = []
for f in stock_files:
    try:
        df = pd.read_excel(f)
        if 'lager_number' in df.columns and 'datetime_upload' in df.columns:
            df = df[['lager_number', 'datetime_upload']].copy()
            all_stock.append(df)
    except Exception:
        pass
stock_union = pd.concat(all_stock, ignore_index=True)
stock_union['lager_nr_str'] = stock_union['lager_number'].astype(str).str.strip().str.replace(r'\.0+$', '', regex=True)
stock_union['we_dt_t1'] = pd.to_datetime(stock_union['datetime_upload'], errors='coerce').dt.normalize()
tier1 = (stock_union.dropna(subset=['we_dt_t1', 'lager_nr_str'])
         .sort_values('we_dt_t1')
         .drop_duplicates('lager_nr_str', keep='first')
         [['lager_nr_str', 'we_dt_t1']])
print(f'  T1: {len(tier1):,} unique Lager-Nrn   ({tier1["we_dt_t1"].min().date()}–{tier1["we_dt_t1"].max().date()})')

print('\n' + '='*72)
print('  STEP 3 — TIER 2 WP-Pipeline (alt + NEU)')
print('='*72)
wp_files = sorted(glob.glob(str(WE_PIPE_DIR / 'WARENEINGANG_PIPELINE*.csv')))
wp_files.append(str(WP_NEW))  # NEU ergänzen
print(f'  Files: {len(wp_files)} (inkl. neuer Download)')
all_wp = []
for f in wp_files:
    try:
        # Encoding-Auto
        encoding = 'cp1252'
        try:
            pd.read_csv(f, sep=';', encoding='utf-8', nrows=1)
            encoding = 'utf-8'
        except Exception:
            try:
                pd.read_csv(f, sep=';', encoding='cp1252', nrows=1)
                encoding = 'cp1252'
            except Exception:
                encoding = 'iso-8859-1'
        df = pd.read_csv(f, sep=';', encoding=encoding, low_memory=False)
        bn_col = None; wd_col = None
        for c in df.columns:
            cl = c.lower()
            if (('bestell' in cl) or ('lieferschein' in cl)) and not bn_col: bn_col = c
            if 'wareneingangs' in cl and not wd_col: wd_col = c
        if bn_col and wd_col:
            sub = df[[bn_col, wd_col]].copy()
            sub.columns = ['bestell_nr', 'we_datum']
            all_wp.append(sub)
    except Exception as e:
        print(f'  WARN {Path(f).name}: {e}')
wp = pd.concat(all_wp, ignore_index=True)
wp['we_dt_t2'] = pd.to_datetime(wp['we_datum'], errors='coerce', dayfirst=True)
wp['bestell_nr_clean'] = wp['bestell_nr'].astype(str).str.strip()
tier2 = (wp.dropna(subset=['we_dt_t2', 'bestell_nr_clean'])
         .sort_values('we_dt_t2')
         .drop_duplicates('bestell_nr_clean', keep='first')
         [['bestell_nr_clean', 'we_dt_t2']])
print(f'  T2: {len(tier2):,} unique Bestell-Nrn   ({tier2["we_dt_t2"].min().date()}–{tier2["we_dt_t2"].max().date()})')

print('\n' + '='*72)
print('  STEP 4 — TIER 3 BESTAND')
print('='*72)
bestand_files = sorted(glob.glob(str(BESTAND_DIR / 'BESTAND134_*.CSV')))
all_b = []
for f in bestand_files:
    df = pd.read_csv(f, sep=';', encoding='ISO-8859-1', skiprows=1, header=None, low_memory=False)
    if df.shape[1] >= 8:
        df = df[[0, 7]].rename(columns={0:'lager_nr', 7:'we_datum'})
        all_b.append(df)
bestand = pd.concat(all_b, ignore_index=True)
bestand['we_dt_t3'] = pd.to_datetime(bestand['we_datum'], errors='coerce', dayfirst=True)
bestand['lager_nr_str'] = bestand['lager_nr'].astype(str).str.strip()
tier3 = (bestand.dropna(subset=['we_dt_t3', 'lager_nr_str'])
         .sort_values('we_dt_t3')
         .drop_duplicates('lager_nr_str', keep='first')
         [['lager_nr_str', 'we_dt_t3']])
print(f'  T3: {len(tier3):,} unique Lager-Nrn   ({tier3["we_dt_t3"].min().date()}–{tier3["we_dt_t3"].max().date()})')

print('\n' + '='*72)
print('  STEP 5 — JTL frisch (11.05.2026)')
print('='*72)
jtl = pd.read_csv(JTL_FILE, sep=';', encoding='iso-8859-1', low_memory=False)
jtl['Bezahlt_dt'] = pd.to_datetime(jtl['Datum Zahlungseingang'], errors='coerce', dayfirst=True)
jtl['Auftrag_dt'] = pd.to_datetime(jtl['Auftragsdatum'], errors='coerce', dayfirst=True)
jtl['lager_nr_str'] = jtl['Artikelnummer'].astype(str).str.strip().str.replace(r'\.0+$', '', regex=True)
jtl_per_lager = (jtl.dropna(subset=['Auftrag_dt', 'lager_nr_str'])
                 .sort_values('Auftrag_dt')
                 .drop_duplicates('lager_nr_str', keep='first')
                 [['lager_nr_str', 'Auftrag_dt', 'Bezahlt_dt']])
print(f'  JTL: {len(jtl):,} Aufträge · {len(jtl_per_lager):,} unique Lager-Nrn')
print(f'  Bezahlt-Datum-Range: {jtl["Bezahlt_dt"].min().date() if jtl["Bezahlt_dt"].notna().any() else "?"} – {jtl["Bezahlt_dt"].max().date() if jtl["Bezahlt_dt"].notna().any() else "?"}')

print('\n' + '='*72)
print('  STEP 6 — Multi-Tier Coalesce')
print('='*72)
m = portal.copy()
m = m.merge(tier1, on='lager_nr_str', how='left')
m = m.merge(tier3, on='lager_nr_str', how='left')
m = m.merge(tier2.rename(columns={'bestell_nr_clean': 'supply_clean'}), on='supply_clean', how='left')
m = m.merge(jtl_per_lager, on='lager_nr_str', how='left')

def coalesce(row):
    if pd.notna(row['we_dt_t1']): return row['we_dt_t1'], 'T1_Stock'
    if pd.notna(row['we_dt_t3']): return row['we_dt_t3'], 'T3_BESTAND'
    if pd.notna(row['we_dt_t2']): return row['we_dt_t2'], 'T2_WP'
    return pd.NaT, 'NONE'

we_data = m.apply(coalesce, axis=1, result_type='expand')
m['we_dt'] = we_data[0]
m['we_tier'] = we_data[1]

m['t_we_to_sold']   = (m['sold_dt']    - m['we_dt']).dt.days
m['t_sold_to_paid'] = (m['Bezahlt_dt'] - m['sold_dt']).dt.days
m['t_we_to_paid']   = (m['Bezahlt_dt'] - m['we_dt']).dt.days

# === COVERAGE-VERGLEICH 2026 drehend ===
DREHEND = ['OTTO_MIX', 'AEG_Schrott']
m26 = m[(m['sold_dt'].dt.year == 2026) & (m['Supply Type'].isin(DREHEND))].copy()
N_DREH = len(m26)
n_we   = m26['we_dt'].notna().sum()
n_paid = m26['Bezahlt_dt'].notna().sum()
n_both = (m26['we_dt'].notna() & m26['Bezahlt_dt'].notna()).sum()
n_kette = ((m26['t_we_to_paid']>=-3) & (m26['t_we_to_paid']<=1500)).sum()

print(f'\n  Drehende 2026 (OTTO_MIX + AEG_Schrott): {N_DREH:,}')
print(f'  WE-Datum:                {n_we:>6,}  ({n_we/N_DREH*100:.1f}%)')
print(f'  Bezahlt-Datum:           {n_paid:>6,}  ({n_paid/N_DREH*100:.1f}%)')
print(f'  Beides:                  {n_both:>6,}  ({n_both/N_DREH*100:.1f}%)')
print(f'  Plausibel (Outlier-frei): {n_kette:>6,}  ({n_kette/N_DREH*100:.1f}%)  ← FINALE Coverage')

# Vorher-Vergleich
print('\n  VORHER (07.05.2026 Daten): 10.255 (60.6%) — siehe v8')
print(f'  NACHHER (11.05.2026 + neue WP): {n_kette:,} ({n_kette/N_DREH*100:.1f}%)')

# Tier-Distribution
print('\n  Tier-Verteilung (drehend 2026):')
for t in ['T1_Stock', 'T2_WP', 'T3_BESTAND', 'NONE']:
    n = (m26['we_tier']==t).sum()
    print(f'    {t:<14} {n:>6,}  ({n/N_DREH*100:.1f}%)')

# === Speichern ===
out = USERHOME / 'Downloads' / 'we_to_paid_full_v2.csv'
cols = ['lager_nr_str', 'Supply Type', 'sold_dt', 'we_dt', 'we_tier',
        'Auftrag_dt', 'Bezahlt_dt', 't_we_to_sold', 't_sold_to_paid', 't_we_to_paid',
        'JTL Selling Price', 'Portal Buying Price']
m[[c for c in cols if c in m.columns]].to_csv(out, sep=';', encoding='utf-8-sig', index=False)
print(f'\n  ✓ Detail-CSV: {out}')
