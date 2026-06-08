"""
MBA-grade Sanity-Check der Working-Capital-Berechnung
"""
import sys, io, os, glob
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', line_buffering=True)
from pathlib import Path
import pandas as pd

USERHOME = Path(os.environ.get('USERPROFILE', os.path.expanduser('~')))
ALLSOLD_DIR = USERHOME / 'Downloads' / 'All Sold 2025 - 2026'

# === ECHTE 2026-Drehmenge aus Portal-Sold (alle Verkäufe, nicht nur die mit Datenkette) ===
print('=' * 70)
print('SCHRITT 1: Gesamtmenge 2026 drehende Lieferanten aus Portal-Sold')
print('=' * 70)
files = sorted(glob.glob(str(ALLSOLD_DIR / 'All-Sold-2026-05-07T*.xlsx')))
portal = pd.concat([pd.read_excel(f) for f in files], ignore_index=True)
portal = portal.drop_duplicates(subset=['Lager Nr.'], keep='first')
portal['Date_dt'] = pd.to_datetime(portal['Date'], errors='coerce')
portal_2026 = portal[portal['Date_dt'].dt.year == 2026].copy()
print(f'  Portal-Sold gesamt (unique Lager-Nr): {len(portal):,}')
print(f'  Davon 2026: {len(portal_2026):,}')

drehend = ['OTTO_MIX', 'OTTO_Hanseatic', 'AEG_Schrott', 'AEG_IT']
portal_dreh_2026 = portal_2026[portal_2026['Supply Type'].isin(drehend)]
print(f'  Davon drehende Lieferanten 2026: {len(portal_dreh_2026):,}')
print(f'\n  Pro Lieferant in 2026:')
print(portal_dreh_2026['Supply Type'].value_counts().to_string())

# Periode der Verkäufe
p_min = portal_dreh_2026['Date_dt'].min()
p_max = portal_dreh_2026['Date_dt'].max()
periode = (p_max - p_min).days
print(f'\n  Verkaufsperiode drehend 2026: {p_min.date()} - {p_max.date()} ({periode} Tage)')
print(f'  Verkäufe/Tag drehend: {len(portal_dreh_2026)/periode:.1f}')
print(f'  Hochrechnung Jahr: {len(portal_dreh_2026)/periode * 365:,.0f}')

# === Coverage der gemessenen Cohort ===
print('\n' + '=' * 70)
print('SCHRITT 2: Coverage-Berechnung — wie viele Geräte tatsächlich gemessen?')
print('=' * 70)
m = pd.read_csv(USERHOME/'Downloads'/'we_to_paid_full.csv', sep=';', encoding='utf-8-sig', low_memory=False)
m['sold_dt'] = pd.to_datetime(m['sold_dt'])
m['Portal Buying Price'] = pd.to_numeric(m['Portal Buying Price'], errors='coerce')
m['JTL Selling Price'] = pd.to_numeric(m['JTL Selling Price'], errors='coerce')

c = m[(m['t_we_to_paid']>=-3)&(m['t_we_to_paid']<=1500)
     &(m['sold_dt'].dt.year==2026)
     &(m['Supply Type'].isin(drehend))].copy()
n_measured = len(c)
n_total_dreh_2026 = len(portal_dreh_2026)
coverage = n_measured / n_total_dreh_2026 * 100
scale_factor = n_total_dreh_2026 / n_measured

print(f'  GEMESSEN (volle Datenkette WE+JTL): {n_measured:,}')
print(f'  ECHT verkauft 2026 drehend:         {n_total_dreh_2026:,}')
print(f'  Coverage:                           {coverage:.1f} %')
print(f'  Skalierungs-Faktor:                 {scale_factor:.2f}x')

# === Verspätung & EK in gemessener Cohort ===
print('\n' + '=' * 70)
print('SCHRITT 3: Vorfinanzierung in GEMESSENER Cohort')
print('=' * 70)
c['vorfin_days'] = (c['t_we_to_paid'] - 30).clip(lower=0)
c['is_vorfin'] = c['t_we_to_paid'] > 30
ueb = c[c['is_vorfin']].copy()
ueb['delay'] = ueb['vorfin_days']

print(f'  Überzogene Geräte (gemessen): {len(ueb):,}  ({len(ueb)/n_measured*100:.1f}%)')
print(f'  Mean Verspätung:   {ueb["delay"].mean():.1f} T')
print(f'  Median Verspätung: {ueb["delay"].median():.1f} T')
print(f'  P90 Verspätung:    {ueb["delay"].quantile(0.9):.1f} T')
print(f'  EK Median pro Gerät: {ueb["Portal Buying Price"].median():.2f} €')
print(f'  EK Mean pro Gerät:   {ueb["Portal Buying Price"].mean():.2f} €')

ek_tage_measured = (ueb['Portal Buying Price'].fillna(0) * ueb['delay']).sum()
print(f'\n  Σ EK × Verspätungs-Tage (Periode gemessen): {ek_tage_measured:,.0f} EUR-Tage')

periode_messung = (c['sold_dt'].max()-c['sold_dt'].min()).days
print(f'  Periode der Messung: {periode_messung} Tage')

# === STEADY-STATE Working Capital (klassische Methode) ===
print('\n' + '=' * 70)
print('SCHRITT 4: Working Capital — drei Berechnungswege')
print('=' * 70)

# A) Naiv: avg über Periode
wc_naive = ek_tage_measured / periode_messung
print(f'\n  A) Tagesdurchschnitt gemessen (steady-state):')
print(f'     WC = Σ(EK × Tage) / Periode_Tage = {ek_tage_measured:,.0f} / {periode_messung}')
print(f'        = {wc_naive:,.0f} €  ← bisherige v5-Zahl')

# B) Hochrechnung auf echte Drehmenge
wc_scaled = wc_naive * scale_factor
print(f'\n  B) Auf echte Drehmenge hochgerechnet:')
print(f'     WC = {wc_naive:,.0f} € × Skalierungs-Faktor {scale_factor:.2f} = {wc_scaled:,.0f} €')

# C) Little's Law: L = λ × W
# λ = Eingangs-Rate überzogener Geräte/Tag
# W = mean Aufenthaltsdauer im Überzogen-Status (Mean-Verspätung)
# L = simultan überzogene Geräte
lambda_overdue = len(ueb) / periode_messung * scale_factor  # hochgerechnet auf echte Drehmenge
W = ueb['delay'].mean()
L = lambda_overdue * W
mean_ek_overdue = ueb['Portal Buying Price'].mean()
wc_littles = L * mean_ek_overdue
print(f'\n  C) Littles Law (Queuing Theory, MBA-Standard):')
print(f'     λ = Rate überzogener Geräte/Tag (skaliert) = {lambda_overdue:.2f}')
print(f'     W = Mean Verweildauer im Überzogen-Status = {W:.1f} T')
print(f'     L = simultan im Vorfinanzierungs-Stau = {L:.0f} Geräte')
print(f'     × Mean EK {mean_ek_overdue:.2f} €')
print(f'     = {wc_littles:,.0f} € permanent gebunden')

# === Jahresvolumen Lieferantenverbindlichkeit ===
print('\n' + '=' * 70)
print('SCHRITT 5: Lieferantenverbindlichkeiten — Größenordnung')
print('=' * 70)
ek_sum_measured = c['Portal Buying Price'].sum()
ek_sum_scaled = ek_sum_measured * scale_factor
year_factor_period = 365 / periode_messung
ek_year = ek_sum_scaled * year_factor_period

print(f'  EK gemessene Cohort (Periode):        {ek_sum_measured:,.0f} €')
print(f'  EK echte Drehmenge (Periode):         {ek_sum_scaled:,.0f} €')
print(f'  EK echte Drehmenge (Jahres-Hochr.):   {ek_year:,.0f} €')
print(f'  → das ist die Σ Lieferanten-Verbindlichkeit p. a.')

# Sanity: WC sollte ~ 26.5% × EK_year × (Mean_Verspätung/365) sein
sanity = 0.265 * ek_year * (W/365)
print(f'\n  Cross-check: 26,5% × EK_jahr × W/365 = {sanity:,.0f} €')

# === Cash Conversion Cycle (MBA-Standard) ===
print('\n' + '=' * 70)
print('SCHRITT 6: Cash Conversion Cycle (DIO + DSO − DPO)')
print('=' * 70)
DIO = c['t_we_to_sold'].median()  # Days Inventory Outstanding
DSO_med = c['t_sold_to_paid'].median()
DSO_mean = c['t_sold_to_paid'].mean()
DPO = 30  # Days Payable Outstanding (Lieferanten-Ziel)
CCC_med = DIO + DSO_med - DPO
CCC_mean = DIO + DSO_mean - DPO
print(f'  DIO (Lager-Verweildauer Median): {DIO:.1f} T')
print(f'  DSO (Kunden-Zahlungsdauer):      Median {DSO_med:.1f} | Mean {DSO_mean:.1f}')
print(f'  DPO (Lieferanten-Zahlungsziel):  {DPO} T')
print(f'  CCC = DIO + DSO − DPO')
print(f'     Median-basiert: {CCC_med:.1f} T  ({"NEGATIV — gut" if CCC_med < 0 else "POSITIV — Vorfinanzierung"})')
print(f'     Mean-basiert:   {CCC_mean:.1f} T  ({"NEGATIV — gut" if CCC_mean < 0 else "POSITIV — Vorfinanzierung"})')

# === Cash Flow at Risk ===
print('\n' + '=' * 70)
print('SCHRITT 7: Cash-Flow-at-Risk bei Worst-Case (P90)')
print('=' * 70)
P90_delay = ueb['delay'].quantile(0.9)
n_at_p90_scaled = lambda_overdue * P90_delay  # bei extremer Verspätung
wc_p90 = n_at_p90_scaled * mean_ek_overdue
print(f'  Falls der Long-Tail (P90={P90_delay:.0f}T Verspätung) zur Norm wird:')
print(f'     WC würde springen auf: {wc_p90:,.0f} €')

print('\n' + '=' * 70)
print('FAZIT')
print('=' * 70)
print(f'  Bisherige v5-Zahl (Selbstbetrug):       58.112 €')
print(f'  Hochgerechnet auf echte Drehmenge:      {wc_scaled:,.0f} €')
print(f'  Bestätigt via Littles Law:              {wc_littles:,.0f} €')
print(f'  → Echte Größenordnung:                  {wc_scaled/1000:.0f}–{wc_littles/1000:.0f} k €')
print(f'  Kapitalkosten p.a. bei 10% Kontokorrent: {wc_scaled*0.10:,.0f}–{wc_littles*0.10:,.0f} €')
print(f'  ')
print(f'  EK-Volumen Drehgeschäft p. a.:          {ek_year/1e6:.2f} Mio €')
print(f'  Vorfinanzierungs-Quote:                 {len(ueb)/n_measured*100:.1f} %')
print(f'  Mean-Verspätung:                        {W:.1f} T')
