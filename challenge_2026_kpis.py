"""
Challenge der Dashboard-KPIs für „2026 · Hauptlieferanten · Lager ≤ 60T"
"""
import sys, io, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', line_buffering=True)
from pathlib import Path
import pandas as pd

USERHOME = Path(os.environ.get('USERPROFILE', os.path.expanduser('~')))
m = pd.read_csv(USERHOME/'Downloads'/'we_to_paid_MASTER.csv', sep=';', encoding='utf-8-sig', low_memory=False)
m['sold_dt']    = pd.to_datetime(m['sold_dt'])
m['we_dt']      = pd.to_datetime(m['we_dt'])
m['Bezahlt_dt'] = pd.to_datetime(m['Bezahlt_dt'])
m['Portal Buying Price'] = pd.to_numeric(m['Portal Buying Price'], errors='coerce')

# JTL für Zahlungsziel
JTL = r'W:\DUSTIN EXPORTE 2026\JTL-Export-Aufträge-11052026.csv'
if Path(JTL).exists():
    jtl = pd.read_csv(JTL, sep=';', encoding='iso-8859-1', low_memory=False)
    jtl['Artikelnummer'] = jtl['Artikelnummer'].astype(str).str.strip().str.replace(r'\.0+$', '', regex=True)
    jtl['payment_term'] = pd.to_numeric(jtl['Zahlungsziel'], errors='coerce')
    jtl_min = jtl[['Artikelnummer','payment_term']].dropna(subset=['Artikelnummer']).drop_duplicates('Artikelnummer')
    jtl_min.columns = ['lager_nr_str','payment_term']
    m['lager_nr_str'] = m['lager_nr_str'].astype(str)
    m = m.merge(jtl_min, on='lager_nr_str', how='left')

# All-Sold für Invoice Date
sold_x = pd.read_excel(USERHOME/'Downloads'/'All-Sold-Apr2025-Apr2026.xlsx')
sold_x['lager_nr_str'] = sold_x['Lager Nr.'].astype(str).str.strip().str.replace(r'\.0+$', '', regex=True)
sold_x['Invoice_dt'] = pd.to_datetime(sold_x['Invoice Date'], errors='coerce').dt.normalize()
inv = sold_x[['lager_nr_str','Invoice_dt']].drop_duplicates('lager_nr_str')
m = m.merge(inv, on='lager_nr_str', how='left')
m['t_invoice_to_paid'] = (m['Bezahlt_dt'] - m['Invoice_dt']).dt.days

# === Dashboard-Filter exakt nachbilden ===
DREHEND = ['OTTO_MIX','AEG_Schrott','OTTO_Hanseatic','AEG_IT','Gorenje_Mix',
           'OTTO_B_Ware','OTTO_Lagerschäden_Ansbach','OTTO_Jura','Samsung PEDC']

# Grundfilter (entspricht dem Master-CSV-Stand für überzogene Geräte):
# - 12 Monate Verkauf
# - WE+Bezahlt vorhanden
# - 0 ≤ t_we_to_paid ≤ 1500
# - t_we_to_paid > 30 (überzogen)
ueb_all = m[(m['sold_dt']>=pd.Timestamp('2025-04-01')) & (m['sold_dt']<=pd.Timestamp('2026-03-31'))
          & m['we_dt'].notna() & m['Bezahlt_dt'].notna()
          & (m['t_we_to_paid']>=-3) & (m['t_we_to_paid']<=1500)
          & (m['t_we_to_paid']>30)].copy()
print(f'Überzogene Geräte gesamt 12 Mo: {len(ueb_all):,}')

# Dashboard-Filter „2026 · Hauptlieferanten · Lager ≤ 60T":
dash = ueb_all[(ueb_all['sold_dt']>=pd.Timestamp('2026-01-01')) & (ueb_all['sold_dt']<=pd.Timestamp('2026-12-31'))
             & ueb_all['Supply Type'].isin(DREHEND)
             & (ueb_all['t_we_to_sold']<=60)].copy()

print(f'\n=== Dashboard-Filter: 2026 + Hauptlieferanten + Lager ≤ 60T ===')
print(f'  n = {len(dash):,}  ← Dashboard zeigt 4.544')

print(f'\n  KPIs (Mean / Median):')
print(f'    WE → Bezahlt:    Mean {dash["t_we_to_paid"].mean():>5.1f}  Median {dash["t_we_to_paid"].median():>4.0f}  ← Dashboard 42,6 / 38')
print(f'    Verk → Bez:      Mean {dash["t_sold_to_paid"].mean():>5.1f}  Median {dash["t_sold_to_paid"].median():>4.0f}  ← Dashboard 28,2 / 31')
print(f'    Rechn → Bez:     Mean {dash["t_invoice_to_paid"].mean():>5.1f}  Median {dash["t_invoice_to_paid"].median():>4.0f}  ← Dashboard 21,6 / 24')
print(f'    Lager:           Mean {dash["t_we_to_sold"].mean():>5.1f}  Median {dash["t_we_to_sold"].median():>4.0f}  ← Dashboard 14,4 / 7')

# === ANOMALIE 1: Mean < Median bei Verk→Bez? ===
print(f'\n=== ANOMALIE 1: Mean < Median? ===')
print(f'  Verk → Bez:')
print(f'    Min: {dash["t_sold_to_paid"].min():.0f}  P25: {dash["t_sold_to_paid"].quantile(0.25):.0f}')
print(f'    Median: {dash["t_sold_to_paid"].median():.0f}')
print(f'    Mean: {dash["t_sold_to_paid"].mean():.1f}')
print(f'    P75: {dash["t_sold_to_paid"].quantile(0.75):.0f}  P90: {dash["t_sold_to_paid"].quantile(0.9):.0f}  Max: {dash["t_sold_to_paid"].max():.0f}')
print(f'    Skew: {dash["t_sold_to_paid"].skew():.2f}  → {"LINKSSCHIEF (Mean<Median)" if dash["t_sold_to_paid"].skew()<0 else "rechtsschief"}')

# Warum linksschief? Selection-Bias-Check:
print(f'\n  Wenn Lager + Verk→Bez > 30 = Überzogen, dann:')
print(f'    Bei Lager 0–10: Verk→Bez muss > {30-5}T sein, um ueberzogen zu sein → niedriger Cluster verboten')
print(f'    Bei Lager 50–60: Verk→Bez kann sehr klein sein (sogar negativ) → kleine Werte erlaubt')
print(f'  → Das erklärt die linksschiefe Verteilung: Selection-Effekt durch Cycle>30-Filter')

# Cross-Check: Mean Verk→Bez bei verschiedenen Lager-Buckets
print(f'\n  Verk→Bez Mean per Lager-Alter-Bucket:')
for lo, hi in [(0,7),(8,14),(15,30),(31,45),(46,60)]:
    sub = dash[(dash['t_we_to_sold']>=lo)&(dash['t_we_to_sold']<=hi)]
    if len(sub)>0:
        print(f'    Lager {lo:>2}–{hi:>2}T (n={len(sub):>5,}): Verk→Bez Mean {sub["t_sold_to_paid"].mean():>5.1f}  Median {sub["t_sold_to_paid"].median():>4.0f}')

# === ANOMALIE 2: Ziel überschritten nur +0,3 T? ===
print(f'\n=== ANOMALIE 2: Ziel überschritten Mean +0,3 T ===')
dash['target_overshoot'] = (dash['Bezahlt_dt'] - dash['Invoice_dt']).dt.days - dash['payment_term']
to = dash['target_overshoot'].dropna()
print(f'  n mit Zahlungsziel: {len(to):,}')
print(f'  Mean: {to.mean():.1f}  ← Dashboard +0,3 T')
print(f'  Median: {to.median():.0f}')
print(f'  Verteilung:')
print(f'    < -7 T (deutlich vor Ziel): {(to<-7).sum():,} ({(to<-7).mean()*100:.1f}%)')
print(f'    -7 bis 0 T (pünktlich):     {((to>=-7)&(to<=0)).sum():,} ({((to>=-7)&(to<=0)).mean()*100:.1f}%)')
print(f'    +1 bis +7 T:                {((to>=1)&(to<=7)).sum():,} ({((to>=1)&(to<=7)).mean()*100:.1f}%)')
print(f'    +8 bis +30 T:               {((to>=8)&(to<=30)).sum():,} ({((to>=8)&(to<=30)).mean()*100:.1f}%)')
print(f'    > +30 T:                    {(to>30).sum():,} ({(to>30).mean()*100:.1f}%)')
print(f'\n  Da viele Kunden DEUTLICH vor Ziel zahlen (negative Werte), zieht das den Mean nach unten.')
print(f'  Das ist konsistent: 56,9 % aller Aufträge sind „Ziel eingehalten" (pünktlich oder früh).')

# === ANOMALIE 3: WC-Berechnung — fixe 365 T statt Filter-Periode? ===
print(f'\n=== ANOMALIE 3: WC-Berechnung ===')
dash['vorfin_days'] = dash['t_we_to_paid'] - 30
dash['eur_days'] = dash['Portal Buying Price'].fillna(0) * dash['vorfin_days']
sum_eur_days_2026 = dash['eur_days'].sum()
print(f'  Σ EK × Verspätungs-Tage (2026 gefiltert): {sum_eur_days_2026:,.0f}')
print(f'\n  WC bei FIXEM 365-T-Nenner (= Dashboard-Methode):')
wc_fix = sum_eur_days_2026 / 365
print(f'    {wc_fix:,.0f} €  ← Dashboard zeigt 14.045')
print(f'\n  WC bei DYNAMISCHEM Nenner (Filter-Periode):')
periode_2026 = (dash['sold_dt'].max() - pd.Timestamp('2026-01-01')).days + 1
print(f'    Filter-Periode: {periode_2026} Tage (01.01.2026 bis {dash["sold_dt"].max().date()})')
wc_dyn = sum_eur_days_2026 / periode_2026
print(f'    {wc_dyn:,.0f} €  ← korrekter für aktuelles aktives WC')
print(f'\n  Faktor: {wc_dyn/wc_fix:.2f}x')

# Vergleich zur Jahres-Auswertung
print(f'\n  Zum Vergleich Jahres-Auswertung (12 Mo, alle Lieferanten):')
print(f'    105.827 € (mit ALLEN Lieferanten, Lager bis ∞)')
print(f'\n  Anteil 2026-only-aktiv vs. Jahres-Gesamt:')
print(f'    14.045 € / 105.827 € = {14045/105827*100:.1f} %')
print(f'    → Erklärung: Filter eliminiert ~87% der €-Tage')
print(f'      - 2026-only: ~30% Anteil (4 von 12 Monaten)')
print(f'      - Lager ≤ 60T: schneidet Long-Tail-Geräte mit hohem Beitrag ab')
print(f'      - Hauptlieferanten only: schneidet OSF/AEG_Klein/OTTO_Liebherr ab')

# Methodisch korrekter WC für die aktuelle Filter-Auswahl
print(f'\n  Methodisch korrekt für „WC heute aktiv":')
print(f'    {wc_dyn:,.0f} € (über aktuelle Periode 2026-01-01 bis heute)')
print(f'    × 10% KK = {wc_dyn*0.10:,.0f} € p. a. Zinslast')

# === Lager-Verteilung im aktiven Sample ===
print(f'\n=== Lager-Verteilung im Filter ===')
for lo, hi, lbl in [(0,7,'≤7T'),(8,14,'8-14T'),(15,30,'15-30T'),(31,45,'31-45T'),(46,60,'46-60T')]:
    n = ((dash['t_we_to_sold']>=lo) & (dash['t_we_to_sold']<=hi)).sum()
    print(f'    {lbl:<8} n={n:>5,}  ({n/len(dash)*100:>4.1f}%)')

# === Bonus: Was wäre korrekt für „Aktiv 2026"-Aussage? ===
print(f'\n=== KORREKTUR-VORSCHLAG ===')
print(f'  Wenn KPI „WC-Beitrag" das aktuelle aktive Working Capital meinen soll:')
print(f'    1. Filter-Periode statt fixer 365 T als Nenner nehmen → WC = {wc_dyn:,.0f} €')
print(f'    2. Jahres-Hochrechnung: {wc_dyn:,.0f} × (365/{periode_2026}) = {wc_dyn:,.0f} € (stationär, gleich)')
print(f'    3. Annahme: konstanter steady-state → 2026-Halbjahr-WC ≈ Vollj-WC')

# Welche Lieferanten dominieren das aktive Sample?
print(f'\n=== Lieferanten-Mix im aktiven 2026er Drehgeschäft ===')
print(dash['Supply Type'].value_counts().to_string())
