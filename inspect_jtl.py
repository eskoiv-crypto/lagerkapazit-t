"""JTL-Export Spalten-Inventur — was ist überhaupt verfügbar für 'Bearbeitungszeit'?"""
import sys, io, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', line_buffering=True)
import pandas as pd

JTL = r'W:\DUSTIN EXPORTE 2026\JTL-Export-Aufträge-07052026.csv'
print(f'Lade {JTL}…')

# Probiere mehrere Encodings + Delimiter
for enc in ['utf-8', 'utf-8-sig', 'cp1252', 'iso-8859-1']:
    for sep in [';', ',', '\t']:
        try:
            df = pd.read_csv(JTL, sep=sep, encoding=enc, nrows=5, low_memory=False)
            if len(df.columns) > 5:
                print(f'  ✓ enc={enc}, sep="{sep}", n_cols={len(df.columns)}')
                # Volle Spalten-Liste
                full = pd.read_csv(JTL, sep=sep, encoding=enc, nrows=2000, low_memory=False)
                print(f'\n  === ALLE {len(full.columns)} SPALTEN ===')
                for i, c in enumerate(full.columns):
                    sample = full[c].dropna().head(2).tolist()
                    sample_str = str(sample)[:80]
                    print(f'    [{i:>3}] {c:<35}  Beispiele: {sample_str}')

                # Datums-Spalten finden
                print(f'\n  === DATUMS-Spalten (Auto-Detect) ===')
                date_cols = []
                for c in full.columns:
                    cl = c.lower()
                    if any(k in cl for k in ['datum', 'date', 'zeit', 'time', 'bezahl', 'rechn', 'erstell', 'eingang', 'ausgang', 'liefer', 'vers']):
                        date_cols.append(c)
                        sample = full[c].dropna().head(3).tolist()
                        print(f'    {c:<40}  → {sample}')

                # Bezahlung / Status
                print(f'\n  === BEZAHL/STATUS-Spalten ===')
                for c in full.columns:
                    cl = c.lower()
                    if 'bezahl' in cl or 'paid' in cl or 'status' in cl:
                        vc = full[c].value_counts().head(5)
                        print(f'    {c}: {vc.to_dict()}')
                sys.exit(0)
        except Exception as e:
            continue
print('Konnte CSV nicht parsen!')
