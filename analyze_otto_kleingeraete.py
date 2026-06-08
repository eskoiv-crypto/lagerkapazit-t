"""
Quick-Win-Analyse: lassen sich OTTO Kleingeräte über Produktgruppen abgrenzen?
"""
import sys, io, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', line_buffering=True)
from pathlib import Path
import pandas as pd

USERHOME = Path(os.environ.get('USERPROFILE', os.path.expanduser('~')))
sold = pd.read_excel(USERHOME/'Downloads'/'All-Sold-Apr2025-Apr2026.xlsx')

# Alle OTTO-Quellen
otto_sup = [s for s in sold['Supply Type'].unique() if 'otto' in str(s).lower()]
otto = sold[sold['Supply Type'].isin(otto_sup)].copy()
print(f'OTTO-Verkäufe gesamt: {len(otto):,}')
print(f'Aufgeteilt nach Supply Type:')
print(otto['Supply Type'].value_counts().to_string())

print('\n' + '='*72)
print('ALLE Produktgruppen über OTTO-Verkäufe sortiert nach Anzahl:')
print('='*72)
pg = otto['Product Group'].value_counts()
print(f'\n  Anzahl unique Produktgruppen: {len(pg)}\n')
for p, n in pg.items():
    print(f'  {n:>6,}  {p}')

print('\n' + '='*72)
print('Klassifikation: was sind eindeutige Kleingeräte?')
print('='*72)

# Klassifikation
KLEINGERAETE_KEYWORDS = [
    'wasserkocher','bügeleisen','buegeleisen','kaffeemaschine','espresso',
    'kaffeevollautomat','toaster','mixer','stabmixer','küchenmaschine',
    'kuechenmaschine','heissluftfritteuse','heißluftfritteuse','fritteuse',
    'mikrowelle','rasierer','bartschneider','föhn','foehn','glätteisen','glaetteisen',
    'staubsauger','saugroboter','dampfreiniger','dampfgarer','eierkocher',
    'küchengerät','kuechengeraet','warmluftbürste','heizlüfter','heizluefter',
    'wasserfilter','sandwichmaker','waffeleisen','reiskocher','zerkleinerer',
    'pürierstab','puerierstab','entsafter','elektrogrill','kontaktgrill',
    'raumheizgerät','luftbefeuchter','luftreiniger','ventilator','heizdecke',
    'maniküre','epilier','zahnreiniger','wärmflasche','warmflasche'
]
GROSSGERAETE_KEYWORDS = [
    'waschmaschine','waschtrockner','trockner','wärmepumpe','waermepumpe',
    'kühlschrank','kuehlschrank','gefrierschrank','geschirrspüler','geschirrspueler',
    'backofen','herd','side by side','side-by-side','dunstabzug','kochfeld',
    'einbau','weinklimaschrank','minibar','range','weinkühlschrank'
]

def klassifiziere(pg_str):
    p = str(pg_str).lower()
    if any(kw in p for kw in GROSSGERAETE_KEYWORDS): return 'Großgerät'
    if any(kw in p for kw in KLEINGERAETE_KEYWORDS): return 'Kleingerät'
    return 'Unklar/Mix'

otto['Kategorie'] = otto['Product Group'].apply(klassifiziere)
print('\nKategorisierung der OTTO-Geräte:')
kat = otto['Kategorie'].value_counts()
for k, n in kat.items():
    print(f'  {k:<15} {n:>7,}  ({n/len(otto)*100:>5.1f}%)')

print('\n  Beispiele Kleingerät:')
print(otto[otto['Kategorie']=='Kleingerät']['Product Group'].value_counts().head(15).to_string())

print('\n  Beispiele Unklar/Mix:')
unklar = otto[otto['Kategorie']=='Unklar/Mix']['Product Group'].value_counts().head(20)
print(unklar.to_string())

# Nur in OTTO_MIX
otto_mix = otto[otto['Supply Type']=='OTTO_MIX']
otto_mix_klein = otto_mix[otto_mix['Kategorie']=='Kleingerät']
print(f'\n  OTTO_MIX → davon Kleingerät: {len(otto_mix_klein):,} ({len(otto_mix_klein)/len(otto_mix)*100:.1f}%)')

# Welche Marken sind diese Kleingeräte?
print('\n  Top-Marken bei OTTO_MIX Kleingeräten:')
print(otto_mix_klein['Brand'].value_counts().head(15).to_string())
