"""
Schuldner-Liste — operative Inkasso-Bearbeitung
Welche Kunden bearbeiten wir, um die 31,9 % Vorfin-Rate zu senken?
"""
import sys, io, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', line_buffering=True)
from pathlib import Path
import pandas as pd

USERHOME = Path(os.environ.get('USERPROFILE', os.path.expanduser('~')))
MASTER_CSV = USERHOME / 'Downloads' / 'we_to_paid_MASTER.csv'
JTL_FILE   = r'W:\DUSTIN EXPORTE 2026\JTL-Export-Aufträge-11052026.csv'
ALL_SOLD   = USERHOME / 'Downloads' / 'All-Sold-Apr2025-Apr2026.xlsx'

# === Lade Master + Filter drehende Ware in 9-Monats-Periode ===
m = pd.read_csv(MASTER_CSV, sep=';', encoding='utf-8-sig', low_memory=False)
m['sold_dt']    = pd.to_datetime(m['sold_dt'])
m['we_dt']      = pd.to_datetime(m['we_dt'])
m['Bezahlt_dt'] = pd.to_datetime(m['Bezahlt_dt'])
m['Portal Buying Price'] = pd.to_numeric(m['Portal Buying Price'], errors='coerce')
m['JTL Selling Price']   = pd.to_numeric(m['JTL Selling Price'], errors='coerce')

DREHEND = ['OTTO_MIX','AEG_Schrott','OTTO_Hanseatic','AEG_IT','Gorenje_Mix',
           'OTTO_B_Ware','OTTO_Lagerschäden_Ansbach','OTTO_Jura','Samsung PEDC']
START = pd.Timestamp('2025-07-01')
END   = pd.Timestamp('2026-03-31')

core = m[(m['sold_dt']>=START) & (m['sold_dt']<=END)
       & m['Supply Type'].isin(DREHEND)
       & m['we_dt'].notna() & m['Bezahlt_dt'].notna()
       & (m['t_we_to_paid']>=-3) & (m['t_we_to_paid']<=1500)].copy()

# Überzogene Geräte
ueb = core[core['t_we_to_paid']>30].copy()
ueb['vorfin_days'] = ueb['t_we_to_paid'] - 30
ueb['eur_days']    = ueb['Portal Buying Price'].fillna(0) * ueb['vorfin_days']
print(f'Überzogene Geräte: {len(ueb):,}')

# === Lade All-Sold für Kundennamen (Company) + JTL für Bestell-Nr ===
print('\nLade All-Sold-Master für Kundennamen…')
sold = pd.read_excel(ALL_SOLD, sheet_name='All Sold')
sold['lager_nr_str'] = sold['Lager Nr.'].astype(str).str.strip().str.replace(r'\.0+$', '', regex=True)
sold_minimal = sold[['lager_nr_str', 'Company', 'Order Nr.', 'Invoice Number']].drop_duplicates('lager_nr_str')
sold_minimal.columns = ['lager_nr_str', 'Kunde', 'Auftrag_Nr', 'Rechnungs_Nr']
print(f'  All-Sold Records mit Kundennamen: {sold_minimal["Kunde"].notna().sum():,}')
print(f'  Unique Kunden gesamt: {sold_minimal["Kunde"].nunique():,}')

# JTL nur für Bestell-Nr falls All-Sold leer
print('\nLade JTL für Auftrags-Status…')
jtl = pd.read_csv(JTL_FILE, sep=';', encoding='iso-8859-1', low_memory=False)
jtl['Artikelnummer'] = jtl['Artikelnummer'].astype(str).str.strip().str.replace(r'\.0+$', '', regex=True)
jtl_minimal = jtl[['Artikelnummer', 'Bestell Nr.', 'Kunden-Nr', 'Datum Zahlungseingang']].dropna(subset=['Artikelnummer']).copy()
jtl_minimal.columns = ['lager_nr_str', 'JTL_Bestell_Nr', 'Kunden_Nr', 'JTL_Bezahlt']
jtl_minimal = jtl_minimal.drop_duplicates('lager_nr_str', keep='first')

# === Match überzogene Geräte mit Kunde (aus All-Sold) und Bestell-Nr (aus JTL) ===
ueb['lager_nr_str'] = ueb['lager_nr_str'].astype(str)
ueb_with_cust = ueb.merge(sold_minimal, on='lager_nr_str', how='left')
ueb_with_cust = ueb_with_cust.merge(jtl_minimal, on='lager_nr_str', how='left')
print(f'\nKunden gemappt (All-Sold Company): {ueb_with_cust["Kunde"].notna().sum():,} von {len(ueb_with_cust):,} ({ueb_with_cust["Kunde"].notna().mean()*100:.1f}%)')

# === Aggregation pro Kunde ===
TOTAL_EUR_DAYS = ueb['eur_days'].sum()
schuldner = ueb_with_cust.groupby('Kunde').agg(
    geraete=('lager_nr_str','count'),
    sum_verspaetung_t=('vorfin_days','sum'),
    mean_verspaetung_t=('vorfin_days','mean'),
    max_verspaetung_t=('vorfin_days','max'),
    sum_ek_eur=('Portal Buying Price','sum'),
    sum_eur_days=('eur_days','sum'),
).sort_values('sum_eur_days', ascending=False)

schuldner['anteil_pct'] = schuldner['sum_eur_days']/TOTAL_EUR_DAYS*100
schuldner['cum_anteil_pct'] = schuldner['anteil_pct'].cumsum()

# WC-Beitrag pro Kunde (€)
periode_tage = (core['sold_dt'].max() - core['sold_dt'].min()).days
schuldner['wc_beitrag_eur'] = schuldner['sum_eur_days'] / periode_tage

# === Top-Liste ===
TOP_N = 50
top = schuldner.head(TOP_N).copy()

print('\n' + '='*100)
print(f'  TOP-{TOP_N} SCHULDNER — Inkasso-Priorität (sortiert nach blockiertem Working Capital)')
print('='*100)
print(f'\n  Gesamt-€-Tage überzogen: {TOTAL_EUR_DAYS:,.0f}')
print(f'  Davon Top-{TOP_N}: {top["sum_eur_days"].sum():,.0f} ({top["sum_eur_days"].sum()/TOTAL_EUR_DAYS*100:.1f} %)')
print(f'  Davon Top-10: {schuldner.head(10)["sum_eur_days"].sum():,.0f} ({schuldner.head(10)["sum_eur_days"].sum()/TOTAL_EUR_DAYS*100:.1f} %)')

print(f'\n  {"Rang":<5}{"Kunde":<40}{"Geräte":>8}{"Verspät.Σ":>12}{"⌀Versp.":>10}{"EK Σ":>11}{"WC-Beitrag":>13}{"%":>7}{"Σ%":>7}')
print('  ' + '-'*113)
for i, (kunde, row) in enumerate(top.iterrows(), 1):
    kn = str(kunde)[:38]
    print(f'  {i:<5}{kn:<40}{int(row["geraete"]):>8,}{int(row["sum_verspaetung_t"]):>11,}T{row["mean_verspaetung_t"]:>9.1f}T{row["sum_ek_eur"]:>9,.0f}€{row["wc_beitrag_eur"]:>11,.0f}€{row["anteil_pct"]:>6.1f}%{row["cum_anteil_pct"]:>6.1f}%')

# === Konzentrations-Analyse ===
print('\n' + '='*100)
print('  KONZENTRATIONS-ANALYSE — wie verteilt ist die Last?')
print('='*100)
n_total = len(schuldner)
for k in [5, 10, 20, 50, 100]:
    if k > n_total: continue
    sub = schuldner.head(k)
    pct = sub['sum_eur_days'].sum() / TOTAL_EUR_DAYS * 100
    wc = sub['sum_eur_days'].sum() / periode_tage
    print(f'  Top {k:>3} Kunden ({k/n_total*100:>4.1f} %) tragen {pct:>5.1f} % der Vorfin-Last  =  {wc:>7,.0f} € permanent gebunden')

# === Excel-Export ===
out_xlsx = USERHOME / 'Downloads' / 'Schuldner_Inkasso_Top.xlsx'
with pd.ExcelWriter(out_xlsx, engine='openpyxl') as w:
    # Sheet 1: Top-50 priorisiert
    top_export = top.reset_index().rename(columns={
        'Kunde':'Kunde',
        'geraete':'Anzahl Geräte',
        'sum_verspaetung_t':'Σ Verspätungs-Tage',
        'mean_verspaetung_t':'Ø Verspätung (T)',
        'max_verspaetung_t':'Max Verspätung (T)',
        'sum_ek_eur':'EK-Summe (€)',
        'sum_eur_days':'€-Tage (Vorfin-Beitrag)',
        'wc_beitrag_eur':'WC-Beitrag (€)',
        'anteil_pct':'Anteil an Vorfin %',
        'cum_anteil_pct':'Kumulativ %',
    })
    top_export.insert(0, 'Rang', range(1, len(top_export)+1))
    top_export.to_excel(w, sheet_name='Top-Schuldner', index=False)

    # Sheet 2: alle Kunden vollständig
    full = schuldner.reset_index().rename(columns={
        'Kunde':'Kunde',
        'geraete':'Anzahl Geräte',
        'sum_verspaetung_t':'Σ Verspätungs-Tage',
        'mean_verspaetung_t':'Ø Verspätung (T)',
        'max_verspaetung_t':'Max Verspätung (T)',
        'sum_ek_eur':'EK-Summe (€)',
        'sum_eur_days':'€-Tage',
        'wc_beitrag_eur':'WC-Beitrag (€)',
        'anteil_pct':'Anteil %',
        'cum_anteil_pct':'Kumulativ %',
    })
    full.to_excel(w, sheet_name='Alle Schuldner', index=False)

    # Sheet 3: Detail-Auflistung pro Top-50-Kunde (alle Geräte)
    detail = ueb_with_cust[ueb_with_cust['Kunde'].isin(top.index)][[
        'Kunde','lager_nr_str','Supply Type','sold_dt','we_dt','Bezahlt_dt',
        'vorfin_days','Portal Buying Price','eur_days','Auftrag_Nr','Rechnungs_Nr'
    ]].copy()
    detail.columns = ['Kunde','Lager-Nr','Lieferant','Verkaufs-Datum','WE-Datum','Bezahlt-Datum',
                      'Verspätung (T)','EK (€)','€-Tage','Auftrag-Nr','Rechnungs-Nr']
    detail = detail.sort_values(['Kunde','€-Tage'], ascending=[True, False])
    detail.to_excel(w, sheet_name='Geräte-Detail Top-50', index=False)

print(f'\n  ✓ Excel-Export: {out_xlsx}')
print(f'    Sheet 1: Top-{TOP_N} Schuldner-Liste (sortiert nach Inkasso-Priorität)')
print(f'    Sheet 2: Alle {n_total:,} Schuldner-Kunden')
print(f'    Sheet 3: Geräte-Detail für Top-50 (für konkrete Mahn-Aktionen)')
