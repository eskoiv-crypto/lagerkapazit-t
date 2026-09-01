---
name: otto-historie
description: Otto-Historie im Obligo-Cockpit auffrischen — neue Agicap-Register-CSVs in hist_register.csv mischen, Cockpit neu bauen und in alle Zielkopien verteilen. Auslösen bei „Otto-Historie auffrischen", „Otto-Obligo-Historie erweitern", „Otto-Volumen-Chart aktualisieren" oder wenn supplier_invoices-CSVs für Otto angehängt werden.
---

# Otto-Historie auffrischen

Setzt die Prozedur aus `_build-kit/REFRESH-Historie.md` um. Läuft **nur lokal auf
dem Arbeitsplatz** — der OneDrive-Ordner muss als Pfad erreichbar sein. In einer
Cloud-Sitzung (Claude Code auf claude.ai/code) gibt es diesen Ordner nicht;
dort nur die CSVs mergen und die fertigen Dateien zurückgeben.

## Ablauf

Ein Kommando, es findet die Ordner selbst:

```bash
python3 tools/otto_obligo/refresh_local.py <neue Agicap-CSVs...>
```

Vorher immer einmal trocken zeigen, was passieren würde:

```bash
python3 tools/otto_obligo/refresh_local.py --dry-run <CSVs...>
```

Das Skript mischt in `hist_register.csv` (Backup mit Zeitstempel daneben), ruft
`node build.js`, prüft das Ergebnis und verteilt erst dann in die Zielkopien.
Ohne Node greift automatisch der Direkt-Patch — gleiches Ergebnis.

Findet es den Ordner nicht, mit `--build-kit "<Pfad zu _build-kit>"` nachhelfen.

## Was zu berichten ist

Die Bilanz, die das Skript ausgibt: Rechnungen vorher → nachher, wie viele neu
und wie viele aktualisiert, der abgedeckte Zeitraum, und wohin verteilt wurde.

## Worauf zu achten ist

- **Bricht das Skript ab, ist nichts verteilt.** Das ist Absicht. Nicht mit
  `cp` von Hand nachhelfen — erst die gemeldete Ursache klären.
- **Der laufende Monat ist im Diagramm unvollständig** (Rechnungen treffen
  verzögert ein). Kein Fehler, steht auch als Hinweis im Chart.
- **Nie ins Repository committen:** das gebaute Cockpit, `hist_register.csv`
  oder die Agicap-Exporte. Das Repo ist öffentlich, die Daten sind intern
  (Einkaufsvolumen, Konditionen, Kreditlinie, IBAN). `.gitignore` hält die
  üblichen Namen fern — bei abweichenden Dateinamen selbst mitdenken.
- Identität einer Rechnung ist die normalisierte Rechnungsnummer, nicht die
  Raten-ID: Agicap stellt umgebuchte Rechnungen mit neuer Raten-ID neu aus.
  Details in `tools/otto_obligo/README.md`.
