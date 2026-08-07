"""
WE → Bezahlt Cycle-Time mit Multi-Tier-Match-Strategie:
Tier 1: Stock-Analysis datetime_upload (direkt pro lager_number) ← Goldquelle
Tier 2: WP-Pipeline Wareneingangsdatum (über Supply-Bestell-Nr-Match)
Tier 3: BESTAND WE-Datum (für aktuell-Lager-Geräte)
+ JTL für Bezahlt-Datum
"""
import sys, io, glob, os, re
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', line_buffering=True)
from pathlib import Path
import pandas as pd
import numpy as np

USERHOME = Path(os.environ.get('USERPROFILE', os.path.expanduser('~')))
ALLSOLD_DIR  = USERHOME / 'Downloads' / 'All Sold 2025 - 2026'
BESTAND_DIR  = USERHOME / 'OneDrive - elvinci.de GmbH' / 'elvinci - Bestandslisten AMM'
WE_PIPE_DIR  = USERHOME / 'OneDrive - elvinci.de GmbH' / 'elvinci - WE Pipeline elvinci'
STOCK_DIR_1  = USERHOME / 'OneDrive - elvinci.de GmbH' / 'Digital Experience - KI-Tools' / 'Stock Analysis'
STOCK_DIR_2  = USERHOME / 'OneDrive - elvinci.de GmbH' / 'elvinci - Portal STOCK ANALYSIS'
JTL_FILE     = r'W:\DUSTIN EXPORTE 2026\JTL-Export-Aufträge-07052026.csv'

print('=' * 70)
print('  STEP 1: Portal-Sold (All-Sold) laden + dedup')
print('=' * 70)
files = sorted(glob.glob(str(ALLSOLD_DIR / 'All-Sold-2026-05-07T*.xlsx')))
portal = pd.concat([pd.read_excel(f) for f in files], ignore_index=True)
portal = portal.drop_duplicates(subset=['Lager Nr.'], keep='first').copy()
portal['sold_dt'] = pd.to_datetime(portal['Date'], errors='coerce').dt.normalize()
portal['lager_nr_str'] = portal['Lager Nr.'].astype(str).str.strip().str.replace(r'\.0+$', '', regex=True)
print(f'  Portal-Sold n: {len(portal):,}')

print('\n' + '=' * 70)
print('  STEP 2: TIER 1 — Stock-Analysis datetime_upload (PRIMARY!)')
print('=' * 70)
stock_files = sorted(set(glob.glob(str(STOCK_DIR_1 / 'Stock-Analysis-*.xlsx'))
                       + glob.glob(str(STOCK_DIR_2 / 'Stock-Analysis-*.xlsx'))))
print(f'  Files: {len(stock_files)}')
all_stock = []
for f in stock_files:
    try:
        df = pd.read_excel(f)
        if 'lager_number' in df.columns and 'datetime_upload' in df.columns:
            df = df[['lager_number', 'datetime_upload', 'product_life_days']].copy()
            df['source'] = Path(f).name
            all_stock.append(df)
    except Exception as e:
        print(f'  WARN: {f}: {e}')
stock_union = pd.concat(all_stock, ignore_index=True)
stock_union['lager_nr_str'] = stock_union['lager_number'].astype(str).str.strip().str.replace(r'\.0+$', '', regex=True)
stock_union['we_dt_t1'] = pd.to_datetime(stock_union['datetime_upload'], errors='coerce').dt.normalize()
print(f'  Stock-Records (alle Snapshots): {len(stock_union):,}')
# Pro Lager-Nr frühestes datetime_upload nehmen
tier1 = (stock_union.dropna(subset=['we_dt_t1', 'lager_nr_str'])
         .sort_values('we_dt_t1')
         .drop_duplicates('lager_nr_str', keep='first')
         [['lager_nr_str', 'we_dt_t1', 'product_life_days']])
print(f'  Unique Lager-Nrn (frühestes WE): {len(tier1):,}')
print(f'  WE-Range: {tier1["we_dt_t1"].min()} – {tier1["we_dt_t1"].max()}')

# Match auf Portal-Sold
match1 = portal['lager_nr_str'].isin(tier1['lager_nr_str']).sum()
print(f'  Match auf Portal-Sold: {match1:,} ({match1/len(portal)*100:.1f}%)')

print('\n' + '=' * 70)
print('  STEP 3: TIER 2 — WP-Pipeline Wareneingangsdatum (per Bestell-Nr)')
print('=' * 70)
wp_files = sorted(glob.glob(str(WE_PIPE_DIR / 'WARENEINGANG_PIPELINE*.csv')))
all_wp = []
for f in wp_files:
    try:
        # Header ist Zeile 0
        df = pd.read_csv(f, sep=';', encoding='ISO-8859-1', low_memory=False)
        # Bestell-Nr-Spalte + Wareneingangsdatum-Spalte finden
        bn_col = None; wd_col = None
        for c in df.columns:
            cl = c.lower()
            if 'bestell' in cl or 'lieferschein' in cl: bn_col = c
            if 'wareneingangs' in cl: wd_col = c
        if bn_col and wd_col:
            df = df[[bn_col, wd_col]].copy()
            df.columns = ['bestell_nr', 'we_datum']
            all_wp.append(df)
    except Exception as e:
        print(f'  WARN {f}: {e}')
wp = pd.concat(all_wp, ignore_index=True) if all_wp else pd.DataFrame()
print(f'  WP-Records (alle Files): {len(wp):,}')
wp['we_dt_t2'] = pd.to_datetime(wp['we_datum'], errors='coerce', dayfirst=True)
wp['bestell_nr_clean'] = wp['bestell_nr'].astype(str).str.strip()
tier2 = (wp.dropna(subset=['we_dt_t2', 'bestell_nr_clean'])
         .sort_values('we_dt_t2')
         .drop_duplicates('bestell_nr_clean', keep='first')
         [['bestell_nr_clean', 'we_dt_t2']])
print(f'  Unique Bestell-Nrn (frühestes WE): {len(tier2):,}')
print(f'  WE-Range: {tier2["we_dt_t2"].min()} – {tier2["we_dt_t2"].max()}')

# Match Portal-Sold "Supply" ↔ WP "bestell_nr"
portal['supply_clean'] = portal['Supply'].astype(str).str.strip()
match2 = portal['supply_clean'].isin(tier2['bestell_nr_clean']).sum()
print(f'  Match Portal-Sold.Supply auf WP.Bestell-Nr: {match2:,} ({match2/len(portal)*100:.1f}%)')

print('\n' + '=' * 70)
print('  STEP 4: TIER 3 — BESTAND WE-Datum')
print('=' * 70)
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
print(f'  Unique Lager-Nrn: {len(tier3):,}')
match3 = portal['lager_nr_str'].isin(tier3['lager_nr_str']).sum()
print(f'  Match auf Portal-Sold: {match3:,} ({match3/len(portal)*100:.1f}%)')

print('\n' + '=' * 70)
print('  STEP 5: JTL-Aufträge → Bezahlt-Datum')
print('=' * 70)
jtl = pd.read_csv(JTL_FILE, sep=';', encoding='iso-8859-1', low_memory=False)
jtl['Bezahlt_dt'] = pd.to_datetime(jtl['Datum Zahlungseingang'], errors='coerce', dayfirst=True)
jtl['Auftrag_dt'] = pd.to_datetime(jtl['Auftragsdatum'], errors='coerce', dayfirst=True)
jtl['lager_nr_str'] = jtl['Artikelnummer'].astype(str).str.strip().str.replace(r'\.0+$', '', regex=True)
jtl_per_lager = (jtl.dropna(subset=['Auftrag_dt', 'lager_nr_str'])
                 .sort_values('Auftrag_dt')
                 .drop_duplicates('lager_nr_str', keep='first')
                 [['lager_nr_str', 'Auftrag_dt', 'Bezahlt_dt']])
print(f'  JTL Lager-Nrn: {len(jtl_per_lager):,}')

print('\n' + '=' * 70)
print('  STEP 6: MULTI-TIER JOIN — WE-Datum als Coalesce(T1, T2, T3)')
print('=' * 70)
m = portal.copy()
m = m.merge(tier1, on='lager_nr_str', how='left')
m = m.merge(tier3, on='lager_nr_str', how='left')
m = m.merge(tier2.rename(columns={'bestell_nr_clean': 'supply_clean'}),
            on='supply_clean', how='left')
m = m.merge(jtl_per_lager, on='lager_nr_str', how='left')

# Coalesce: priorisiere T1 > T3 > T2
def coalesce(row):
    if pd.notna(row['we_dt_t1']): return row['we_dt_t1'], 'T1_Stock'
    if pd.notna(row['we_dt_t3']): return row['we_dt_t3'], 'T3_BESTAND'
    if pd.notna(row['we_dt_t2']): return row['we_dt_t2'], 'T2_WP'
    return pd.NaT, 'NONE'

we_data = m.apply(coalesce, axis=1, result_type='expand')
m['we_dt'] = we_data[0]
m['we_tier'] = we_data[1]

# Cycle-Time
m['t_we_to_sold']  = (m['sold_dt'] - m['we_dt']).dt.days
m['t_sold_to_paid'] = (m['Bezahlt_dt'] - m['sold_dt']).dt.days
m['t_we_to_paid']   = (m['Bezahlt_dt'] - m['we_dt']).dt.days

# Coverage-Statistik
print(f'\n  Coverage-Quellen:')
tier_counts = m['we_tier'].value_counts()
total = len(m)
for t, n in tier_counts.items():
    print(f'    {t:<15} {n:>7,}  ({n/total*100:>5.1f}%)')

cov_we = m['we_dt'].notna().sum()
cov_paid = m['Bezahlt_dt'].notna().sum()
cov_both = (m['we_dt'].notna() & m['Bezahlt_dt'].notna()).sum()
print(f'\n  WE-Datum verfügbar:        {cov_we:>7,} ({cov_we/total*100:.1f}%)')
print(f'  Bezahlt-Datum verfügbar:   {cov_paid:>7,} ({cov_paid/total*100:.1f}%)')
print(f'  BEIDE (WE→Bezahlt möglich): {cov_both:>7,} ({cov_both/total*100:.1f}%)')

# Statistiken
def quantile_block(s, label):
    s = s.dropna()
    s = s[(s >= -3) & (s <= 1500)]
    if len(s) == 0:
        print(f'\n  {label}: KEINE Daten')
        return
    print(f'\n  {label} (n={len(s):,}, nach Outlier-Filter)')
    print(f'    Median: {s.median():>7.1f} Tage')
    print(f'    Mean:   {s.mean():>7.1f} Tage')
    print(f'    P25:    {s.quantile(0.25):>7.1f} Tage')
    print(f'    P75:    {s.quantile(0.75):>7.1f} Tage')
    print(f'    P90:    {s.quantile(0.90):>7.1f} Tage')
    print(f'    P95:    {s.quantile(0.95):>7.1f} Tage')

print('\n' + '=' * 70)
print('  STEP 7: Bearbeitungszeit-Statistiken')
print('=' * 70)
quantile_block(m['t_we_to_sold'],   'WE → Verkauf (Lager-Verweildauer)')
quantile_block(m['t_sold_to_paid'], 'Verkauf → Bezahlt (Zahlungsgeschwindigkeit)')
quantile_block(m['t_we_to_paid'],   'WE → Bezahlt (FULL CYCLE — User-Frage)')

# Tier-by-Tier WE→Bezahlt
print('\n  WE → Bezahlt pro Tier:')
for t in ['T1_Stock', 'T2_WP', 'T3_BESTAND']:
    sub = m[m['we_tier'] == t]['t_we_to_paid'].dropna()
    sub = sub[(sub >= -3) & (sub <= 1500)]
    if len(sub) > 0:
        print(f'    {t:<12} n={len(sub):>6,}  Median {sub.median():>5.0f}T  Mean {sub.mean():>5.1f}T  P90 {sub.quantile(0.9):>5.0f}T')

print('\n' + '=' * 70)
print('  STEP 8: Pro Lieferant (Top-15)')
print('=' * 70)
sup = (m.dropna(subset=['t_we_to_paid'])
       .pipe(lambda d: d[(d['t_we_to_paid'] >= -3) & (d['t_we_to_paid'] <= 1500)])
       .groupby('Supply Type').agg(
           n=('t_we_to_paid', 'count'),
           avg_d=('t_we_to_paid', 'mean'),
           med_d=('t_we_to_paid', 'median'),
           p90_d=('t_we_to_paid', lambda x: x.quantile(0.9))
       ).sort_values('n', ascending=False).head(15))
print(f'\n  {"Lieferant":<28}{"n":>7}{"Median":>9}{"Mean":>9}{"P90":>8}')
print('  ' + '-' * 60)
for s, row in sup.iterrows():
    print(f'  {str(s)[:28]:<28}{int(row.n):>7,}{row.med_d:>8.0f}T{row.avg_d:>8.1f}T{row.p90_d:>7.0f}T')

# Save für HTML
out_csv = USERHOME / 'Downloads' / 'we_to_paid_full.csv'
m_out = m[['lager_nr_str', 'Supply Type', 'sold_dt', 'we_dt', 'we_tier', 'Auftrag_dt', 'Bezahlt_dt',
           't_we_to_sold', 't_sold_to_paid', 't_we_to_paid',
           'JTL Selling Price', 'Portal Buying Price']].copy()
m_out.to_csv(out_csv, sep=';', index=False, encoding='utf-8-sig')
print(f'\n  ✓ Detail-CSV: {out_csv}')
