"""
MATHEMATIK-PROFESSOR-AUDIT der finalen Zahlen
Jede Größe gegen mehrere unabhängige Berechnungswege.
"""
import sys, io, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', line_buffering=True)
from pathlib import Path
import pandas as pd
import numpy as np

USERHOME = Path(os.environ.get('USERPROFILE', os.path.expanduser('~')))
m = pd.read_csv(USERHOME/'Downloads'/'we_to_paid_MASTER.csv', sep=';', encoding='utf-8-sig', low_memory=False)
m['sold_dt']    = pd.to_datetime(m['sold_dt'])
m['we_dt']      = pd.to_datetime(m['we_dt'])
m['Bezahlt_dt'] = pd.to_datetime(m['Bezahlt_dt'])
m['Portal Buying Price'] = pd.to_numeric(m['Portal Buying Price'], errors='coerce')
m['JTL Selling Price']   = pd.to_numeric(m['JTL Selling Price'], errors='coerce')

START = pd.Timestamp('2025-07-01')
END   = pd.Timestamp('2026-03-31')
DREHEND = ['OTTO_MIX', 'AEG_Schrott', 'OTTO_Hanseatic', 'AEG_IT', 'Gorenje_Mix',
           'OTTO_B_Ware', 'OTTO_Lagerschäden_Ansbach', 'OTTO_Jura', 'Samsung PEDC']

in_period = m[(m['sold_dt']>=START) & (m['sold_dt']<=END) & m['Supply Type'].isin(DREHEND)].copy()
core = in_period[in_period['we_dt'].notna() & in_period['Bezahlt_dt'].notna()
               & (in_period['t_we_to_paid']>=-3) & (in_period['t_we_to_paid']<=1500)].copy()

print('='*78)
print('  AUDIT 1: Stichprobengröße & Repräsentativität')
print('='*78)
print(f'  Drehende Verkäufe in Periode:  {len(in_period):>7,}')
print(f'  Mit vollständiger Datenkette:  {len(core):>7,}')
print(f'  Coverage:                      {len(core)/len(in_period)*100:.2f} %')

core['vorfin_days'] = (core['t_we_to_paid']-30).clip(lower=0)
core['is_vorfin'] = core['t_we_to_paid']>30
ueb = core[core['is_vorfin']].copy()
PERIODE = (core['sold_dt'].max()-core['sold_dt'].min()).days

print(f'  Periode-Tage:                  {PERIODE}')
print(f'  Davon überzogen (>30T):        {len(ueb):>7,}  ({len(ueb)/len(core)*100:.2f} %)')

print('\n' + '='*78)
print('  AUDIT 2: Mean EK pro Gerät — Plausibilität')
print('='*78)
ek_all = core['Portal Buying Price']
ek_ueb = ueb['Portal Buying Price']
print(f'  EK alle Geräte:        Median {ek_all.median():>7.2f} €  Mean {ek_all.mean():>7.2f} €')
print(f'  EK überzogene Geräte:  Median {ek_ueb.median():>7.2f} €  Mean {ek_ueb.mean():>7.2f} €')
print(f'  Skew überzogen/alle:   {ek_ueb.mean()/ek_all.mean():.3f}x')

print('\n' + '='*78)
print('  AUDIT 3: Working-Capital-Berechnung — 4 unabhängige Wege')
print('='*78)

# Methode A: Σ(EK × Verspätung) / Periode  [Tagesdurchschnitt]
core['eur_days'] = core['Portal Buying Price'].fillna(0) * core['vorfin_days']
sum_eur_days = core['eur_days'].sum()
wc_A = sum_eur_days / PERIODE
print(f'\n  A) Tagesdurchschnitt-Integral:')
print(f'     Σ(EK_i × Verspätung_i) = {sum_eur_days:>14,.0f} €-Tage')
print(f'     ÷ Periode = {PERIODE} Tage')
print(f'     = WC_A = {wc_A:>10,.0f} €')

# Methode B: Little's Law (L = λ × W)
lam = len(ueb) / PERIODE          # Rate überzogener Geräte pro Tag
W = ueb['vorfin_days'].mean()      # mean Verweildauer im Stau
L = lam * W                        # simultan im Stau
mean_ek = ueb['Portal Buying Price'].mean()
wc_B = L * mean_ek
print(f'\n  B) Little\'s Law (Queueing-Theorie):')
print(f'     λ = {len(ueb)} überz. ÷ {PERIODE} T = {lam:>6.2f} Geräte/Tag')
print(f'     W = {W:>6.2f} T (mean Verweildauer im Vorfin-Status)')
print(f'     L = λ × W = {L:>7.1f} simultan gebunden')
print(f'     × Mean EK {mean_ek:.2f} €')
print(f'     = WC_B = {wc_B:>10,.0f} €')

# Methode C: Direkt-Aufsumming am beliebigen Tag
# An jedem Tag d: alle Geräte deren we_dt+30 ≤ d ≤ Bezahlt_dt sind im Stau
ueb['t_overdue_start'] = ueb['we_dt'] + pd.Timedelta(days=30)
ueb['t_overdue_end']   = ueb['Bezahlt_dt']
# Für jeden Tag in der Periode: zähle gebundenes EK
days = pd.date_range(core['sold_dt'].min(), core['sold_dt'].max(), freq='D')
daily_wc = []
for d in days:
    active = ueb[(ueb['t_overdue_start']<=d) & (ueb['t_overdue_end']>=d)]
    daily_wc.append(active['Portal Buying Price'].sum())
wc_C = np.mean(daily_wc)
print(f'\n  C) Direkte Tag-für-Tag-Aufsummung (Σ EK an jedem Tag im Stau, dann Ø):')
print(f'     WC_C = {wc_C:>10,.0f} €  (geometrische Validierung)')
print(f'     Min/Max über Periode: {min(daily_wc):,.0f} – {max(daily_wc):,.0f} €')

# Methode D: hochgerechnet auf 100% Coverage
scale = len(in_period) / len(core)
wc_D = wc_A * scale
print(f'\n  D) Hochgerechnet auf vollständige Drehmenge (Coverage-Adjust):')
print(f'     WC_A × {scale:.4f} = {wc_D:>10,.0f} €')

print('\n  Konvergenz-Check (alle 4 Methoden):')
for v, lbl in [(wc_A,'A Integral'), (wc_B,'B Little'), (wc_C,'C Tag-für-Tag'), (wc_D,'D Skaliert')]:
    print(f'    {lbl:<15} {v:>10,.0f} €')
print(f'  ★ Spannweite: {min(wc_A,wc_B,wc_C):,.0f} – {max(wc_A,wc_B,wc_C):,.0f} €')

print('\n' + '='*78)
print('  AUDIT 4: Verteilungs-Plausibilität (Kolmogorow-Sicht)')
print('='*78)
t = core['t_we_to_paid']
print(f'  WE→Bezahlt n={len(t):,}')
print(f'    Mean   {t.mean():>6.2f} T')
print(f'    Median {t.median():>6.0f} T')
print(f'    Skew   {t.skew():>6.2f}  ({"stark schief" if t.skew()>1 else "moderat"})')
print(f'    Kurt   {t.kurt():>6.2f}  (Long-Tail-Indikator)')

# Bucket-Konsistenz
buckets = [(0,7), (8,14), (15,30), (31,60), (61,90), (91,180), (181,1500)]
total = 0
for lo, hi in buckets:
    n = ((t>=lo) & (t<=hi)).sum()
    total += n
print(f'  Bucket-Summe: {total:,} = {len(core):,} ✓' if total==len(core) else f'  ⚠ Lücke: {len(core)-total}')

print('\n' + '='*78)
print('  AUDIT 5: EK-Volumen — Hochrechnung Jahr')
print('='*78)
ek_periode_measured = core['Portal Buying Price'].sum()
ek_periode_all = ek_periode_measured * scale       # auf 100% Drehmenge
year_factor = 365 / PERIODE
ek_year_simple = ek_periode_measured * year_factor
ek_year_adj = ek_periode_all * year_factor
print(f'  EK in {PERIODE} T (gemessen 41k):    {ek_periode_measured:>11,.0f} €')
print(f'  Auf Drehmenge skaliert (45k):      {ek_periode_all:>11,.0f} €')
print(f'  → Jahr (×{year_factor:.3f}):')
print(f'    Punktwert gemessen (untere Schranke): {ek_year_simple:>11,.0f} €')
print(f'    Coverage-bereinigt (realistisch):     {ek_year_adj:>11,.0f} €')

print('\n' + '='*78)
print('  AUDIT 6: Sensitivity — was wenn fehlende 8,9% schlechter wären?')
print('='*78)
# Annahmen
for factor, label in [(1.0,'gleich wie gemessen'),(1.5,'50% schlimmer'),(2.0,'doppelt so schlimm')]:
    missing_wc_contribution = (scale-1) * wc_A * factor
    total_wc = wc_A + missing_wc_contribution
    print(f'  Fehlende 8,9% sind {label:<25}  → Gesamt-WC = {total_wc:,.0f} €')

# Forderungsausfall-Annahme
print('\n  Bonus: was wenn 2% der Drehgeschäft-Forderungen ausfallen (DEU-Schnitt B2B)?')
defaults_eur = ek_periode_all * 0.02
print(f'    EK-Verlust p.a.: {defaults_eur * year_factor:,.0f} €')

print('\n' + '='*78)
print('  FAZIT — MATHEMATIK-AUDIT')
print('='*78)
print(f'  WC permanent gebunden:')
print(f'    Konservativ (gemessen)        {wc_A:>9,.0f} €  ← Punktwert v_FINAL.pdf')
print(f'    Coverage-bereinigt            {wc_D:>9,.0f} €')
print(f'    Little\'s-Law-Validierung     {wc_B:>9,.0f} €')
print(f'    Geometrische Validierung      {wc_C:>9,.0f} €')
print(f'  → Ehrliche Bandbreite:          {min(wc_A,wc_B,wc_C):,.0f} – {wc_D:,.0f} €')
print(f'  → Empfohlene Headline-Zahl:     {round((wc_A+wc_D)/2/1000)*1000:,.0f} €  (Mitte konservativ + skaliert)')

print(f'\n  EK-Volumen p.a.:')
print(f'    Punktwert gemessen:           {ek_year_simple:,.0f} €')
print(f'    Coverage-bereinigt:           {ek_year_adj:,.0f} €')
print(f'  → Empfohlen: {ek_year_adj:,.0f} € (Coverage-bereinigt = ehrlicher)')

print(f'\n  Kapitalkosten bei 10% Kontokorrent:')
mid_wc = (wc_A+wc_D)/2
print(f'    Konservativ:  {wc_A*0.10:,.0f} €')
print(f'    Realistisch:  {mid_wc*0.10:,.0f} €')
print(f'    Skaliert:     {wc_D*0.10:,.0f} €')
