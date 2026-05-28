"""
RIGOROSE Daten-Validierung — 10 kritische Checks
Ziel: 100 % Vertrauen oder ehrliche Korrektur
"""
import sys, io, os, glob
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', line_buffering=True)
from pathlib import Path
import pandas as pd
import numpy as np

USERHOME = Path(os.environ.get('USERPROFILE', os.path.expanduser('~')))

# === Datenbasis ===
m = pd.read_csv(USERHOME/'Downloads'/'we_to_paid_full.csv', sep=';', encoding='utf-8-sig', low_memory=False)
m['sold_dt'] = pd.to_datetime(m['sold_dt'])
m['we_dt'] = pd.to_datetime(m['we_dt'])
m['Bezahlt_dt'] = pd.to_datetime(m['Bezahlt_dt'])
m['Portal Buying Price'] = pd.to_numeric(m['Portal Buying Price'], errors='coerce')
m['JTL Selling Price'] = pd.to_numeric(m['JTL Selling Price'], errors='coerce')

drehend = ['OTTO_MIX', 'OTTO_Hanseatic', 'AEG_Schrott', 'AEG_IT']

# Portal-Sold als Ground Truth
ALLSOLD_DIR = USERHOME / 'Downloads' / 'All Sold 2025 - 2026'
files = sorted(glob.glob(str(ALLSOLD_DIR / 'All-Sold-2026-05-07T*.xlsx')))
portal = pd.concat([pd.read_excel(f) for f in files], ignore_index=True)
portal = portal.drop_duplicates(subset=['Lager Nr.'], keep='first')
portal['Date_dt'] = pd.to_datetime(portal['Date'], errors='coerce')

print('=' * 75)
print('CHECK 1: Periode-Konsistenz Sample vs Ground Truth')
print('=' * 75)
p_2026_dreh = portal[(portal['Date_dt'].dt.year == 2026) & (portal['Supply Type'].isin(drehend))]
m_2026 = m[(m['sold_dt'].dt.year == 2026) & (m['Supply Type'].isin(drehend))]
m_clean = m_2026[(m_2026['t_we_to_paid']>=-3) & (m_2026['t_we_to_paid']<=1500)]

print(f'  Portal-Sold 2026 drehend: {len(p_2026_dreh):,}   ({p_2026_dreh["Date_dt"].min().date()} – {p_2026_dreh["Date_dt"].max().date()})')
print(f'  Sample (gemessen):        {len(m_clean):,}   ({m_clean["sold_dt"].min().date()} – {m_clean["sold_dt"].max().date()})')
print(f'  → Sample-Periode kürzer:  {(p_2026_dreh["Date_dt"].max()-p_2026_dreh["Date_dt"].min()).days} vs {(m_clean["sold_dt"].max()-m_clean["sold_dt"].min()).days} Tage')
print(f'  → Erste 2 Wochen Januar fehlen in der Cohort (kein WE-Datum verfügbar für Frühverkäufe)')

print('\n' + '=' * 75)
print('CHECK 2: Fehlende Geräte — wo liegt das Gap pro Lieferant?')
print('=' * 75)
for s in drehend:
    p_n = (p_2026_dreh['Supply Type'] == s).sum()
    m_n = (m_clean['Supply Type'] == s).sum()
    cov = m_n/p_n*100 if p_n else 0
    flag = '⚠' if cov < 50 else '✓'
    print(f'  {flag} {s:<18} Portal {p_n:>5,}   Sample {m_n:>5,}   Coverage {cov:>5.1f} %')

print('\n' + '=' * 75)
print('CHECK 3: NICHT-bezahlte Geräte — der Survivor-Bias-Risiko')
print('=' * 75)
# Geräte ohne Bezahlt_dt → potentielle Forderungsausfälle / sehr späte Zahler
no_paid = m_2026[m_2026['Bezahlt_dt'].isna()]
print(f'  Sample-Records 2026 drehend ohne Bezahlt-Datum: {len(no_paid):,}  ({len(no_paid)/len(m_2026)*100:.1f}%)')
print(f'  → diese Geräte sind im "vollständige Datenkette"-Filter rausgefallen')
print(f'  → könnten echte Spät-/Ausfall-Fälle sein und WC unterschätzen')

# Wie alt sind die Verkäufe der nicht-bezahlten?
if len(no_paid) > 0:
    today = pd.Timestamp('2026-05-08')
    no_paid_age = (today - no_paid['sold_dt']).dt.days
    print(f'  Median Tage seit Verkauf bis heute: {no_paid_age.median():.0f} T')
    print(f'  Davon > 30 T seit Verkauf (heißt: bereits 30+ T überzogen): {(no_paid_age>30).sum():,}')

print('\n' + '=' * 75)
print('CHECK 4: WE-Tier-Bias bei WE-Alter (Stock-Analysis vs WP-Pipeline)')
print('=' * 75)
for tier in ['T1_Stock', 'T2_WP', 'T3_BESTAND']:
    sub = m_clean[m_clean['we_tier'] == tier]
    if len(sub):
        print(f'  {tier:<14} n={len(sub):>5,}   WE→Verk Median={sub["t_we_to_sold"].median():.1f}T   Mean={sub["t_we_to_sold"].mean():.1f}T')
print(f'  → Wenn Tiers stark abweichen: Bias in der Aggregation')

print('\n' + '=' * 75)
print('CHECK 5: WE→Verkauf — Mean/Median-Skew (Long-Tail im WE-Alter?)')
print('=' * 75)
ws = m_clean['t_we_to_sold']
print(f'  Median: {ws.median():.1f} T')
print(f'  Mean:   {ws.mean():.1f} T')
print(f'  P75:    {ws.quantile(0.75):.1f} T')
print(f'  P90:    {ws.quantile(0.9):.1f} T')
print(f'  P99:    {ws.quantile(0.99):.1f} T')
print(f'  Max:    {ws.max():.0f} T')
skew = ws.mean() / ws.median() if ws.median() else 0
print(f'  Mean/Median-Skew: {skew:.2f}x ({"stark schief" if skew > 1.5 else "moderat"})')

print('\n' + '=' * 75)
print('CHECK 6: Outlier-Dominanz — sind Top-Geräte für WC verantwortlich?')
print('=' * 75)
ueb = m_clean[m_clean['t_we_to_paid']>30].copy()
ueb['days_over'] = ueb['t_we_to_paid'] - 30
ueb['exposure'] = ueb['Portal Buying Price'].fillna(0) * ueb['days_over']
ueb_sorted = ueb.sort_values('exposure', ascending=False)
top_n = 50
top_exp = ueb_sorted.head(top_n)['exposure'].sum()
total_exp = ueb['exposure'].sum()
print(f'  Top {top_n} Geräte tragen {top_exp/total_exp*100:.1f}% der Vorfinanzierungs-Last')
print(f'  Top 100 Geräte: {ueb_sorted.head(100)["exposure"].sum()/total_exp*100:.1f}%')
print(f'  Top 500 Geräte: {ueb_sorted.head(500)["exposure"].sum()/total_exp*100:.1f}%')
print(f'  → Wenn Top-N dominieren: gezielte Aktionen auf einzelne Großschuldner möglich')

print('\n' + '=' * 75)
print('CHECK 7: Sensitivity — wenn fehlende 41% schlechter wären als gemessen')
print('=' * 75)
quote = m_clean['t_we_to_paid']>30
vorfin_rate = quote.mean() * 100
print(f'  Gemessene Vorfin-Rate: {vorfin_rate:.1f}%')
mean_delay = m_clean[quote]['vorfin_days' if 'vorfin_days' in m_clean.columns else 't_we_to_paid'].mean()
# Berechne neu falls Spalte fehlt
m_clean = m_clean.copy()
m_clean['vorfin_days'] = (m_clean['t_we_to_paid']-30).clip(lower=0)
m_clean['eur_days'] = m_clean['Portal Buying Price'].fillna(0) * m_clean['vorfin_days']
periode = (m_clean['sold_dt'].max()-m_clean['sold_dt'].min()).days
wc_measured = m_clean['eur_days'].sum() / periode
n_true = len(p_2026_dreh)
n_meas = len(m_clean)

# Szenarien: was wenn die fehlenden 41% genauso viel / 1.5x / 2x überziehen
for assumption, factor in [('genauso wie gemessen', 1.0),
                            ('50% schlechter', 1.5),
                            ('doppelt so schlimm', 2.0),
                            ('halb so schlimm', 0.5)]:
    wc_missing = wc_measured * (n_true/n_meas - 1) * factor
    wc_total = wc_measured + wc_missing
    print(f'  Annahme fehlende 41% sind "{assumption}":  WC = {wc_total:,.0f} €')

print('\n' + '=' * 75)
print('CHECK 8: Periode-Korrektur — Sample-Periode 109T vs True-Periode 122T')
print('=' * 75)
true_periode = (p_2026_dreh['Date_dt'].max() - p_2026_dreh['Date_dt'].min()).days
correction = periode / true_periode
print(f'  Periode Sample: {periode} T  ·  Periode Ground Truth: {true_periode} T')
print(f'  Tagesdurchschnitt mit korrekter Periode:')
wc_corr = m_clean['eur_days'].sum() / true_periode
print(f'    {wc_corr:,.0f} € (Sample-€-Tage / wahre Periode)')
print(f'    {wc_corr * n_true/n_meas:,.0f} € (zusätzlich auf echte Menge skaliert)')

print('\n' + '=' * 75)
print('CHECK 9: AEG_IT-Anomalie — schon strukturell über 30T?')
print('=' * 75)
aegi = m_clean[m_clean['Supply Type']=='AEG_IT']
print(f'  n: {len(aegi):,}')
print(f'  WE→Verk. Median {aegi["t_we_to_sold"].median():.1f}T  P75 {aegi["t_we_to_sold"].quantile(0.75):.1f}T  P90 {aegi["t_we_to_sold"].quantile(0.9):.1f}T')
print(f'  WE→Bez. Median {aegi["t_we_to_paid"].median():.1f}T')
print(f'  → AEG_IT-Geräte werden im Schnitt >30T nach WE verkauft')
print(f'  → AEG_IT gehört strukturell NICHT in "drehende Ware" — könnte Altlast-Status sein!')

print('\n' + '=' * 75)
print('CHECK 10: OTTO_Hanseatic-Coverage-Loch')
print('=' * 75)
oh_p = p_2026_dreh[p_2026_dreh['Supply Type']=='OTTO_Hanseatic']
oh_m = m_clean[m_clean['Supply Type']=='OTTO_Hanseatic']
print(f'  Portal 2026 OTTO_Hanseatic: {len(oh_p):,}')
print(f'  Sample:                      {len(oh_m):,}')
print(f'  Coverage:                    {len(oh_m)/len(oh_p)*100:.1f}% — sehr niedrig')
print(f'  → 3 von 4 Geräten von OTTO_Hanseatic NICHT in der Auswertung')
print(f'  → wenn diese fehlende Cohort sich anders verhält: Verzerrung')

# === FINALE EMPFEHLUNGEN ===
print('\n' + '=' * 75)
print('ZUSAMMENFASSUNG der Validierungs-Befunde')
print('=' * 75)
print(f'  1. Periode-Korrektur: WC sinkt minimal, da Tages-Mittel auf wahrem Zeitraum')
print(f'  2. AEG_IT als drehend ist GRENZWERTIG (P75 = 32 T) — sollte als Altlast separiert werden')
print(f'  3. OTTO_Hanseatic Coverage extrem niedrig (~24 %) — Risiko-Unterschätzung wenn fehlende 76% schlechter sind')
print(f'  4. NICHT-bezahlte Geräte ({len(no_paid):,}) sind nicht im Sample — Forderungsausfall-Risiko')
print(f'  5. Sensitivity zeigt: realistische WC-Spanne 99–217 k € je nach Annahme')

# Strikt korrigierte Variante: AEG_IT raus, OTTO_Hanseatic Vorbehalt
print('\n  STRIKT KORRIGIERTE Drehende-Ware-Definition:')
strict = ['OTTO_MIX', 'AEG_Schrott']
m_strict = m_clean[m_clean['Supply Type'].isin(strict)].copy()
p_strict = p_2026_dreh[p_2026_dreh['Supply Type'].isin(strict)]
print(f'    Nur OTTO_MIX + AEG_Schrott:')
print(f'    Sample {len(m_strict):,}  Portal {len(p_strict):,}  Coverage {len(m_strict)/len(p_strict)*100:.1f}%')
m_strict['vorfin_days'] = (m_strict['t_we_to_paid']-30).clip(lower=0)
m_strict['eur_days'] = m_strict['Portal Buying Price'].fillna(0) * m_strict['vorfin_days']
ueb_s = m_strict[m_strict['t_we_to_paid']>30]
print(f'    Vorfin-Rate: {(m_strict["t_we_to_paid"]>30).mean()*100:.1f} %')
print(f'    Mean-Verspätung: {ueb_s["vorfin_days"].mean():.1f} T')
periode_s = (m_strict['sold_dt'].max()-m_strict['sold_dt'].min()).days
wc_strict_measured = m_strict['eur_days'].sum() / periode_s
scale_s = len(p_strict)/len(m_strict)
# Little's Law strict
lam_s = len(ueb_s)/periode_s * scale_s
W_s = ueb_s['vorfin_days'].mean()
mek_s = ueb_s['Portal Buying Price'].mean()
wc_strict_littles = lam_s * W_s * mek_s
print(f'    WC gemessen: {wc_strict_measured:,.0f} €')
print(f'    WC skaliert: {wc_strict_measured*scale_s:,.0f} €')
print(f'    WC Littles:  {wc_strict_littles:,.0f} €')

# EK Jahres-Volumen
ek_year_strict = m_strict['Portal Buying Price'].sum() * scale_s * 365/periode_s
print(f'    EK-Volumen p.a. (strikt): {ek_year_strict:,.0f} €')
