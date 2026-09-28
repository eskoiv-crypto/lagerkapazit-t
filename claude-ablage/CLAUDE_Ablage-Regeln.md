# Ergänzung für deine CLAUDE.md / Claude-Einstellungen

Version 1.0 · 2026-09-28

**Wohin:** claude.ai › Einstellungen › Profil › „Persönliche Präferenzen“ (dort steht deine CLAUDE.md v2.0).
Damit gilt die Regel in jeder neuen Claude-Session, auch in Claude Code.

---

## A) Diesen Block unter „## Workflow-Specific Rules“ einfügen

```markdown
### Projektablage (Team „Eskofier“)
- Jedes Projekt hat eine Kennung `BBB-NNN` (Bereich + laufende Nummer).
  Bereiche: FUL Fulfillment · LOG Logistik-Partner · FIN Finanzen & Kosten · BES Bestand & Lager ·
  VER Vertrieb & Kunden · ORG Organisation & Team · SON Sonstiges.
- Bestehend: FIN-001 Otto-Obligo · LOG-001 Frachtkostenrechner · BES-001 Warenwert-Bestandsrechner.
  BES-001 ist der wiederkehrende Chat „Lagerwert zum Stichtag“.
  Aktuelle Liste: `Projektregister.csv` auf der SharePoint-Seite „Eskofier“ (per M365-Connector lesbar;
  der Suchindex kann hinterherhinken – im Zweifel fragen).
- Nennt Dustin keine Kennung → vor dem ersten erzeugten Dokument fragen:
  „Zu welchem Projekt gehört das – Kennung, oder neues Projekt?“
  Bei neuem Projekt Bereich + Kurztitel vorschlagen. Dustin legt es über „Neues Claude-Projekt“ an und
  nennt die Kennung. **Nie selbst eine Kennung vergeben** – die Nummer vergibt nur das Skript.
- Jede Datei, die du erzeugst (auch ZIP-Pakete): `KENNUNG_JJJJ-MM-TT_Beschreibung_vN.ext`
  Kennung immer ganz vorne, Bindestriche statt Leerzeichen.
- Stichtagsauswertungen (z. B. BES-001 Lagerwert/Warenwert): im Namen steht der **Stichtag**, nicht das
  Erstelldatum – `BES-001_2026-09-30_Warenwert_v1.pdf`. Vor jeder Auswertung die Abgrenzung bestätigen lassen
  (nur unverkauft QE, oder inkl. verkaufter Ware QE+VS+AA) und im Dokument ausweisen.
- Aktuelle Fassung: die gültige Fassung des Hauptergebnisses zusätzlich als `KENNUNG_Beschreibung_AKTUELL.ext`
  (fester Name, ohne Datum/Version) → liegt direkt im Projektordner, ersetzt die vorige. Jede Fassung auch mit
  Datum/Version im Verlauf ablegen.
- Zusätze im Namen steuern den Zielordner:
  `_FINAL` → 03_Ergebnis · `_INPUT` → 01_Input · `_MAIL` → 04_Kommunikation · ohne Zusatz → 02_Arbeitsstand.
- Am Ende jeder Session: Liste der erzeugten Dateien + Links (Session, Artefakte, Repo, PR) als Block zum
  Einfügen in `_Projekt.md` des Projekts.
```

## B) Im Abschnitt „### Naming“ die Datumszeile ersetzen

Bisher:

```markdown
- Include date: `YYYY-MM-DD_description.ext`
```

Neu (sonst widersprechen sich die Regeln – bisher steht das Datum vorne):

```markdown
- Include project code and date: `KENNUNG_YYYY-MM-DD_description.ext` (siehe Projektablage)
```

## C) Version anheben

`**Version:** 2.0` → `**Version:** 2.1`
