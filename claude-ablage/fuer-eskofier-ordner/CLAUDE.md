# CLAUDE.md · Claude-Ablage „Eskofier“

Version 1.1 · 2026-09-28 · gilt für lokale Claude-Code-Sessions in diesem Ordner

Dieser Ordner ist der per OneDrive synchronisierte Kanalordner der Teams-Seite **Eskofier**
(SharePoint › Dokumente › Eskofier). Alles, was hier gespeichert wird, lädt OneDrive nach SharePoint hoch
und ist in Teams › Eskofier › Dateien sichtbar. Es gelten zusätzlich Dustins persönliche Claude-Regeln (CLAUDE.md v2.x).

## Aufbau
```
Claude-Projekte/
├─ 00_Eingang/                  Dateien mit unbekannter Kennung
├─ 10_Fulfillment/         FUL
├─ 20_Logistik-Partner/    LOG
├─ 30_Finanzen-Kosten/     FIN
├─ 40_Bestand-Lager/       BES
├─ 50_Vertrieb-Kunden/     VER
├─ 60_Organisation-Team/   ORG
├─ 90_Sonstiges/           SON
│   └─ <Bereich>/KENNUNG_Projekttitel/
│         01_Input/  02_Arbeitsstand/  03_Ergebnis/  04_Kommunikation/  _Projekt.md
│   └─ <Bereich>/_Archiv/     abgeschlossene Projekte
├─ 99_Vorlagen/Projektvorlage/  Vorlage für neue Projekte (inkl. _Projekt.md)
├─ _System/Protokoll/
├─ Projektregister.csv          Kennung;Bereich;Titel;Status;Angelegt;Ordner (UTF-8 mit BOM, Semikolon)
└─ LIESMICH.md
```
Bestehende Projekte: **FIN-001_Otto-Obligo** · **LOG-001_Frachtkostenrechner** · **BES-001_Warenwert-Bestandsrechner**
(BES-001 = wiederkehrende Auswertung „Lagerwert zum Stichtag“).

**Fehlt `Claude-Projekte/` noch:** Lege die Struktur genau wie oben an, inklusive der drei Projekte, Projektvorlage,
LIESMICH.md und Projektregister.csv. Liegt `2026-09-28_Claude-Projekte_Struktur_v1.zip` im Ordner oder in Downloads,
entpacke stattdessen dessen Inhalt hierher (enthält die fertig ausgefüllten `_Projekt.md`). Vorher Plan nennen.

## Regeln beim Ablegen
1. **Projekt klären.** Keine Kennung genannt → fragen: „Zu welchem Projekt gehört das – Kennung oder neues Projekt?“
2. **Neues Projekt:** Bereich + Titel mit Dustin abstimmen. Nächste Nummer = höchste vorhandene Nummer im Bereich
   (auch in `_Archiv`) + 1. Ordner aus `99_Vorlagen/Projektvorlage` kopieren, `_Projekt.md` ausfüllen,
   Zeile in `Projektregister.csv` ergänzen.
3. **Dateiname:** `KENNUNG_JJJJ-MM-TT_Beschreibung_vN.ext` – Kennung vorne, Bindestriche statt Leerzeichen.
   Stichtagsauswertungen (BES-001): Datum = **Stichtag**.
4. **Zielordner:** Rohdaten/Exporte → `01_Input` · Entwürfe → `02_Arbeitsstand` · freigegebene Endversion (`_FINAL`)
   → `03_Ergebnis` · Mail-/Brief-Entwürfe (`_MAIL`) → `04_Kommunikation`.
5. **Aktuelle Fassung immer ganz oben:** Die gültige Fassung des Hauptergebnisses (z. B. das Cockpit-HTML) liegt
   **direkt im Projektordner** unter festem Namen ohne Datum/Version: `KENNUNG_Beschreibung_AKTUELL.ext`
   (z. B. `FIN-001_Otto-Obligo-Cockpit_AKTUELL.html`). Bei jeder neuen Fassung: (a) mit Datum/Version in den
   Verlauf (`02_Arbeitsstand`/`03_Ergebnis`) legen, (b) die AKTUELL-Datei damit ersetzen – einzige erlaubte
   Überschreibung; SharePoint behält die vorige im Versionsverlauf. `_Projekt.md` › „Aktuelle Fassung“ nachführen.
6. **Sonst nie überschreiben, nie löschen.** Neue Fassung = neue Versionsnummer. Löschen oder Verschieben bestehender
   Dateien nur nach ausdrücklicher Bestätigung.
7. **Originale in `01_Input` nie verändern** – Transformationen als Kopie in `02_Arbeitsstand`.
8. **`_Projekt.md` pflegen:** am Ende jeder Session erzeugte Dateien, Entscheidungen, offene Punkte, Links ergänzen.
9. **Live-Tools der Kollegen** (PlattformenTeams › KI-Tools: Obligo-Cockpit, Frachtkostenrechner) liegen NICHT hier und
   werden von hier aus nie verändert. Freigaben dorthin macht Dustin.
10. `Projektregister.csv` kann in Excel geöffnet und damit gesperrt sein → melden, nicht erzwingen.

## Vertraulichkeit
Lagerwert-, Obligo- und Kostendaten sind intern/vertraulich. Keine Inhalte aus diesem Ordner in öffentliche Repos,
Artefakte oder externe Dienste übertragen.
