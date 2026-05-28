"""
Prüfe JTL-Zahlungsziel + Auftragsdatum für volle Pipeline-Kette
"""
import sys, io, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', line_buffering=True)
from pathlib import Path
import pandas as pd

JTL = r'W:\DUSTIN EXPORTE 2026\JTL-Export-Aufträge-11052026.csv'
jtl = pd.read_csv(JTL, sep=';', encoding='iso-8859-1', low_memory=False)
print('JTL-Spalten:', list(jtl.columns))
print(f'\nZeilen: {len(jtl):,}')

# Zahlungsziel
zz = pd.to_numeric(jtl['Zahlungsziel'], errors='coerce')
print(f'\nZahlungsziel-Statistik:')
print(f'  Nicht-leer:    {zz.notna().sum():,} ({zz.notna().mean()*100:.1f}%)')
print(f'  Verteilung:')
print(zz.value_counts().sort_index().head(20).to_string())
print(f'\n  Min/Max: {zz.min()} / {zz.max()}')
print(f'  Median:  {zz.median()}')
print(f'  Mean:    {zz.mean():.1f}')

# Auftragsdatum vs ggf weitere
print(f'\nAuftragsdatum-Range:')
ad = pd.to_datetime(jtl['Auftragsdatum'], errors='coerce', dayfirst=True)
print(f'  {ad.min()} – {ad.max()}  (n={ad.notna().sum():,})')

# Beispiel: 10 Zeilen mit allen Datum-Spalten
print(f'\nBeispielzeilen mit Pipeline-Stages:')
sample = jtl[['Bestell Nr.','Kunden-Nr','Auftragsdatum','Artikelnummer','Zahlungsziel','Datum Zahlungseingang']].dropna(subset=['Datum Zahlungseingang']).head(10)
print(sample.to_string())

# Pro Kunde: ist Zahlungsziel konstant?
print(f'\nIst Zahlungsziel pro Kunde konstant?')
zz_per_cust = jtl.dropna(subset=['Kunden-Nr','Zahlungsziel']).groupby('Kunden-Nr')['Zahlungsziel'].nunique()
print(f'  Kunden mit konstantem Zahlungsziel: {(zz_per_cust==1).sum():,}')
print(f'  Kunden mit wechselndem Zahlungsziel: {(zz_per_cust>1).sum():,}')
