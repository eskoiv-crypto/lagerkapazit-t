"""
IMPUTATION v2 — drei Szenarien (optimistisch / realistisch / konservativ)
Statt einer naiven Median-Imputation: pro Verkaufsmonat des Sample-Medians.
"""
import sys, io, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', line_buffering=True)
from pathlib import Path
import pandas as pd

USERHOME = Path(os.environ.get('USERPROFILE', os.path.expanduser('~')))
SRC = USERHOME / 'Downloads' / 'we_to_paid_full_v2.csv'

m = pd.read_csv(SRC, sep=';', encoding='utf-8-sig', low_memory=False)
m['sold_dt']    = pd.to_datetime(m['sold_dt'])
m['we_dt']      = pd.to_datetime(m['we_dt'])
m['Bezahlt_dt'] = pd.to_datetime(m['Bezahlt_dt'])
m['Portal Buying Price'] = pd.to_numeric(m['Portal Buying Price'], errors='coerce')

DREHEND = ['OTTO_MIX', 'AEG_Schrott']
m26d = (m['sold_dt'].dt.year==2026) & (m['Supply Type'].isin(DREHEND))

# === Gemessenes WE-Alter pro VERKAUFSMONAT + Lieferant ===
valid = m[m26d & m['we_dt'].notna() & (m['t_we_to_sold']>=0) & (m['t_we_to_sold']<=365)].copy()
valid['sold_month'] = valid['sold_dt'].dt.to_period('M').astype(str)
month_age = valid.groupby(['sold_month', 'Supply Type'])['t_we_to_sold'].median().unstack()
print('  Median WE-Alter pro Verkaufsmonat × Lieferant (gemessen):')
print(month_age.round(1).to_string())

# === Drei Imputations-Szenarien ===
def impute_scenario(data, scenario_fn, label):
    """scenario_fn(supply_type, sold_month) → days_to_subtract"""
    d = data.copy()
    no_we = m26d & d['we_dt'].isna()
    d.loc[no_we, 'sold_month'] = d.loc[no_we, 'sold_dt'].dt.to_period('M').astype(str)
    for sup in DREHEND:
        for month in d.loc[no_we, 'sold_month'].dropna().unique():
            sel = no_we & (d['Supply Type']==sup) & (d['sold_month']==month)
            if sel.sum()==0: continue
            days = scenario_fn(sup, month)
            d.loc[sel, 'we_dt'] = d.loc[sel, 'sold_dt'] - pd.Timedelta(days=days)
            d.loc[sel, 't_we_to_sold'] = days
            d.loc[sel, 't_we_to_paid'] = (d.loc[sel, 'Bezahlt_dt'] - d.loc[sel, 'we_dt']).dt.days

    c = d[m26d].copy()
    c = c[(c['t_we_to_paid']>=-3) & (c['t_we_to_paid']<=1500)]
    c['vorfin_days'] = (c['t_we_to_paid']-30).clip(lower=0)
    c['is_vorfin'] = c['t_we_to_paid'] > 30
    c['eur_days'] = c['Portal Buying Price'].fillna(0) * c['vorfin_days']
    periode = (c['sold_dt'].max()-c['sold_dt'].min()).days
    wc = c['eur_days'].sum() / periode
    ueb = c[c['is_vorfin']]
    if len(ueb)>0:
        W = ueb['vorfin_days'].mean()
        mek = ueb['Portal Buying Price'].mean()
        lam = len(ueb)/periode
        wc_little = lam * W * mek
    else:
        wc_little = 0
    return {
        'label': label, 'n': len(c),
        'vorfin_pct': c['is_vorfin'].mean()*100,
        'mean_delay': ueb['vorfin_days'].mean() if len(ueb) else 0,
        'wc': wc, 'wc_little': wc_little,
    }

# Szenario 1: OPTIMISTISCH — Lieferanten-Median (3 / 5 T)
def opt(sup, month): return {'OTTO_MIX':3, 'AEG_Schrott':5}[sup]

# Szenario 2: REALISTISCH — Verkaufsmonats-Median aus gemessenen Daten
def realistic(sup, month):
    try: return month_age.loc[month, sup]
    except KeyError: return {'OTTO_MIX':3, 'AEG_Schrott':5}[sup]

# Szenario 3: KONSERVATIV — Januar-Verkäufe = WE im Vorjahr (Annahme: 45 T)
#  Februar-Verkäufe: 30 T,  März+: gemessen wie üblich
def conservative(sup, month):
    if month == '2026-01': return 60
    if month == '2026-02': return 30
    if month == '2026-03': return 14
    return realistic(sup, month)

results = []
for fn, label in [(opt, 'OPTIMISTISCH (Median 3/5 T)'),
                  (realistic, 'REALISTISCH (Monatsmedian gemessen)'),
                  (conservative, 'KONSERVATIV (Jan=60T, Feb=30T)')]:
    r = impute_scenario(m, fn, label)
    results.append(r)

print('\n' + '='*78)
print('  Sensitivity-Analyse — drei Imputations-Szenarien')
print('='*78)
print(f'  {"Szenario":<40}{"Vorfin%":>10}{"MeanDelay":>12}{"WC (Avg)":>14}{"WC (Little)":>14}')
print('  ' + '-'*84)
for r in results:
    print(f'  {r["label"]:<40}{r["vorfin_pct"]:>9.1f}%{r["mean_delay"]:>11.1f}T{r["wc"]:>13,.0f}€{r["wc_little"]:>13,.0f}€')

# === Kombiniert mit gemessen + skaliert ===
core_meas = m[m26d & m['we_dt'].notna()].copy()
core_meas = core_meas[(core_meas['t_we_to_paid']>=-3) & (core_meas['t_we_to_paid']<=1500)]
core_meas['vorfin_days'] = (core_meas['t_we_to_paid']-30).clip(lower=0)
core_meas['eur_days'] = core_meas['Portal Buying Price'].fillna(0) * core_meas['vorfin_days']
periode = (core_meas['sold_dt'].max()-core_meas['sold_dt'].min()).days
wc_meas = core_meas['eur_days'].sum() / periode
scale = 16931 / len(core_meas)
wc_scaled = wc_meas * scale
print(f'\n  Methode "skaliert": gemessen {wc_meas:,.0f}€ × {scale:.2f} = {wc_scaled:,.0f}€')

# Bandbreite finalisieren
all_estimates = [r['wc'] for r in results] + [r['wc_little'] for r in results] + [wc_scaled]
print('\n  Alle Schätzungen (sortiert):')
for v in sorted(all_estimates):
    print(f'    {v:>10,.0f} €')
print(f'\n  → Belastbare Bandbreite: {min(all_estimates):,.0f} – {max(all_estimates):,.0f} €')
print(f'  → Median der 7 Methoden: {sorted(all_estimates)[3]:,.0f} €')
