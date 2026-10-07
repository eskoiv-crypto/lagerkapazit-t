# Otto-Obligo — Übergabe an die IT

**Für:** IT-Kollege/in, Vertretung während Urlaub Backoffice & Lager
**Von:** Dustin Eskofier (Backoffice & Warehouse Manager)
**Stand:** 07.10.2026 · Version des bestehenden Tools: v2.3
**Einstufung:** INTERN — enthält Otto-Konditionslogik, nicht nach außen geben

---

## Worum es geht, in fünf Sätzen

elvinci kauft bei Otto laufend LKW-Ladungen Weißware. Otto räumt uns ein
**Kreditlimit** ein. Was wir Otto zu einem Stichtag schulden, heißt **Obligo**.
Reißt das Obligo das Limit, stoppt Otto die Anlieferungen — das trifft die
Klassifizierung und damit den gesamten Durchsatz im Lager.

Heute wird das Obligo **manuell** ermittelt: drei Dateien exportieren, in ein
HTML-Tool ziehen, Zahl ablesen. Das soll automatisiert werden.

---

## Was in diesem Paket liegt

| Datei | Inhalt |
|---|---|
| `00_START-HIER.md` | dieses Dokument |
| `01_Fachkonzept_Obligo.md` | **Zuerst lesen.** Was das Obligo ist, wie es gerechnet wird, warum nichts doppelt gezählt werden darf |
| `02_Aenderungsauftrag_Automatisierung.md` | **Der eigentliche Auftrag.** Zielarchitektur, Arbeitspakete, Feldmapping, Abnahmekriterien |
| `03_Abnahme_und_Testfaelle.md` | Womit du prüfst, ob es richtig rechnet |
| `app/OttoObligoCockpit_v2.3_ohne-Passwort.html` | das lauffähige Ist-Tool (Doppelklick, offline, keine Installation) |
| `app/_build-kit/app_template.html` | **die Quelle.** Hier steht die gesamte Rechenlogik, ~1.100 Zeilen, kommentiert |
| `app/_build-kit/build.cjs` | Build-Skript (bettet SheetJS/jsPDF/pako ein) |
| `app/tests/otto-obligo.spec.js` | 14 Playwright-Tests gegen die Rechenlogik — **die müssen grün bleiben** |
| `ABNAHME-Referenzwerte_INTERN.md` | echte Vergleichszahlen — **liegt nur im Übergabe-ZIP**, bewusst nicht im (öffentlichen) Repo |

**Arbeitsbasis ist das Repo** `eskoiv-crypto/lagerkapazit-t`, Ordner `otto-obligo/`
(Quelle) und `tests/` (Tests). Der Ordner `app/` hier ist ein Schnappschuss
davon zum Lesen und Ausprobieren — gebaut und getestet wird im Repo
(`03_Abnahme_und_Testfaelle.md`, Abschnitt 1). `app/_build-kit/vendor/` enthält
die drei Bibliotheken, damit der Build auch ohne `npm install` läuft.

**Einstellungen (🔒) im Paket-HTML:** Das Passwort ist hier bewusst nur der
Platzhalter `__BITTE_BEIM_BUILD_SETZEN__`. Das echte Passwort steht nur in der
Live-Datei im SharePoint-Ordner `Otto_Obligo_View` und wird beim Austausch per
`otto-obligo/deploy.ps1` übernommen — **nie die neu gebaute Datei direkt
darüberkopieren**, sonst sind Passwort und eingebettete Historie weg.

---

## Reihenfolge für den ersten Tag

1. **`app/OttoObligoCockpit_v2.3_ohne-Passwort.html` doppelklicken.** Läuft offline
   im Browser, keine Installation, kein Server. Du siehst sofort, was das Tool tut.
   Zum Befüllen brauchst du Exporte — die liegen nicht im Paket (vertraulich),
   siehe `03_Abnahme_und_Testfaelle.md`, Abschnitt „Woher die Testdaten kommen".
2. **`01_Fachkonzept_Obligo.md` lesen.** Ohne das Fachverständnis baust du die
   Automatisierung falsch — es gibt eine Falle (Doppelzählung), die rechnerisch
   nicht auffällt, aber die Zahl wertlos macht.
3. **`02_Aenderungsauftrag_Automatisierung.md`** durchgehen und die Arbeitspakete
   AP-0 bis AP-7 bewerten. AP-0 und AP-1 sind die Pflicht, der Rest baut darauf auf.
4. Rückfragen sammeln — siehe unten.

---

## Was du NICHT tun sollst

- **Die Rechenlogik nicht neu schreiben.** Sie ist gegen echte Otto-Rechnungen
  gehärtet (PDF-Parser inkl. Schriftart-Sonderfall, Retouren-Abzug in zwei
  Schreibweisen, Rechnungsnummern-Normalisierung). Nachbauen kostet Wochen und
  produziert stille Abweichungen. Siehe AP-0: Kern extrahieren, nicht ersetzen.
- **Das Obligo nicht „optimieren", bis das Fachkonzept verstanden ist.** Ein zu
  hohes Obligo ist gefährlicher als ein zu niedriges: es bremst Anlieferungen,
  die gar nicht gebremst werden müssten.
- **Das Einstellungs-Passwort nicht ins Repo schreiben.** Das Repo
  `eskoiv-crypto/lagerkapazit-t` ist derzeit öffentlich.

---

## Rückfragen

**Während des Urlaubs** entscheidest du eigenständig über technische Mittel
(n8n-Node-Auswahl, Ablageort, Sprache). **Nicht eigenständig** entscheidest du über:

- die Obligo-**Formel** (was zählt mit, was nicht)
- das Abschalten von Agicap als Quelle
- den Versand einer Obligo-Zahl an Otto oder andere Externe

Diese drei Punkte sind in `02_…` als `[ENTSCHEIDUNG DUSTIN]` markiert. Bitte dort
aufsetzen lassen und nach dem Urlaub klären — die Automatisierung läuft auch
ohne diese Entscheidungen erst mal parallel zum bisherigen Weg.

**Fachliche Ansprechpartner im Haus:** Mirko (Rechnungswesen/Eingangsrechnungen),
Janna und Igor (Versand), Siyad und Johannes (Lager/Klassifizierung).

---

## Zwei offene Datenqualitäts-Punkte

Beide sind in `01_Fachkonzept_Obligo.md` ausführlich beschrieben, hier nur als
Vorwarnung, damit du sie beim Testen nicht für deinen eigenen Fehler hältst:

1. **Ein blockierter LKW trug zuletzt einen Wert, der rechnerisch nicht sein kann**
   (grob das Fünffache einer normalen Ladung). Vermutlich hat Odoo den
   Preisfaktor nicht angewendet, weil die Klassifizierung noch nicht gelaufen war.
   → AP-5 ist genau dafür da.
2. **Zwei Bestellungen mit identischer Produktliste** über 129 Positionen bei
   unterschiedlicher Lieferantenreferenz. Entweder eine Kopie in Odoo oder eine
   Doppelerfassung. Ist nicht geklärt.

Beides sind **Odoo-Themen**, keine Tool-Fehler. Das Tool zeigt getreu an, was in
den Exporten steht.
