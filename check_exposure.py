import sys, io, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', line_buffering=True)
import pandas as pd
from pathlib import Path
USERHOME = Path(os.environ.get('USERPROFILE', os.path.expanduser('~')))
m = pd.read_csv(USERHOME/'Downloads'/'we_to_paid_full.csv', sep=';', encoding='utf-8-sig', low_memory=False)
m['sold_dt'] = pd.to_datetime(m['sold_dt'])
m['JTL Selling Price'] = pd.to_numeric(m['JTL Selling Price'], errors='coerce')
m['Portal Buying Price'] = pd.to_numeric(m['Portal Buying Price'], errors='coerce')
c = m[(m['t_we_to_paid']>=-3)&(m['t_we_to_paid']<=1500)&(m['sold_dt'].dt.year==2026)].copy()
sup_m = c.groupby('Supply Type')['t_we_to_sold'].median()
keep = sup_m[sup_m<=30].index
c = c[c['Supply Type'].isin(keep)]
print(f'n drehend: {len(c):,}')
print(f'EK  Median: {c["Portal Buying Price"].median():.2f} EUR | Mean: {c["Portal Buying Price"].mean():.2f}')
print(f'VK  Median: {c["JTL Selling Price"].median():.2f} EUR | Mean: {c["JTL Selling Price"].mean():.2f}')
print(f'EK-Summe Drehgeschaeft: {c["Portal Buying Price"].sum():,.0f} EUR')
print(f'VK-Summe Drehgeschaeft: {c["JTL Selling Price"].sum():,.0f} EUR')
ueb = c[c['t_we_to_paid']>30].copy()
ueb['delay'] = ueb['t_we_to_paid']-30
print()
print(f'Anzahl ueberzogen: {len(ueb):,}  ({len(ueb)/len(c)*100:.1f}%)')
print(f'Mean Verspaetung: {ueb["delay"].mean():.1f} T | Median: {ueb["delay"].median():.1f} | P90: {ueb["delay"].quantile(0.9):.1f}')
print(f'EK-Summe ueberzogene Geraete: {ueb["Portal Buying Price"].sum():,.0f} EUR')
print(f'VK-Summe ueberzogene Geraete: {ueb["JTL Selling Price"].sum():,.0f} EUR')
ek_tage = (ueb['Portal Buying Price'].fillna(0) * ueb['delay']).sum()
vk_tage = (ueb['JTL Selling Price'].fillna(0) * ueb['delay']).sum()
print(f'EK x Verspaetungs-Tage Summe: {ek_tage:,.0f} EUR-Tage')
print(f'VK x Verspaetungs-Tage Summe: {vk_tage:,.0f} EUR-Tage')
periode = (c['sold_dt'].max()-c['sold_dt'].min()).days
print(f'Periode: {periode} Tage  ({c["sold_dt"].min().date()} - {c["sold_dt"].max().date()})')
print()
print(f'>>> Avg gebundenes WC (EK-Basis): {ek_tage/periode:,.0f} EUR  (=Tagesdurchschnitt im Konto fehlend)')
print(f'>>> Avg gebundenes WC (VK-Basis): {vk_tage/periode:,.0f} EUR  (=Forderungsausfall-Pendant)')
print()
year_factor = 365/periode
print(f'Hochgerechnet auf 12 Monate (linear x {year_factor:.2f}):')
print(f'  Vorfinanzierte EK-Tage/Jahr: {ek_tage*year_factor:,.0f} EUR-Tage')
for r in [0.05, 0.08, 0.10, 0.15]:
    print(f'  Kapitalkosten p.a. bei {r*100:.0f}%: {ek_tage*year_factor*r/365:,.0f} EUR')
