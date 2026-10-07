# Änderungsauftrag: Automatisierung Otto-Obligo

**Einstufung:** INTERN · Stand 07.10.2026
**Voraussetzung:** `01_Fachkonzept_Obligo.md` gelesen
**Auftraggeber fachlich:** Dustin Eskofier · **Umsetzung:** IT

---

## 1. Ziel

Das Otto-Obligo soll **einmal täglich automatisch** ermittelt und gemeldet
werden, ohne dass jemand drei Dateien von Hand exportiert und in ein HTML-Tool
zieht.

Zusätzlich — und fachlich wichtiger als die Zeitersparnis — soll die in
`01_Fachkonzept`, Abschnitt 3 beschriebene **Lücke zwischen Lieferung und
Rechnungsbuchung** geschlossen werden. Dafür werden Otto-Rechnungen **bereits
bei Mail-Eingang** erfasst, nicht erst nach der Buchung.

---

## 2. Zielarchitektur

```
  QUELLEN                      VERARBEITUNG                AUSGABE

┌───────────────────┐
│ Odoo: Rechnungen  │──┐
│ (mit Zahlstatus)  │  │
└───────────────────┘  │     ┌──────────────────┐
                       ├────►│  obligo-core.js  │
┌───────────────────┐  │     │                  │
│ Odoo: Bestellungen│──┤     │  normalisieren   │    ┌──────────────────┐
│ (purchase.order)  │  │     │  deduplizieren   │───►│ Tagesmeldung      │
└───────────────────┘  │     │  rechnen         │    │ (Mail/Teams)      │
                       │     │  prüfen          │    └──────────────────┘
┌───────────────────┐  │     └──────────────────┘
│ Outlook via n8n:  │──┘              │                ┌──────────────────┐
│ Otto-Rechnungs-   │                 └───────────────►│ Cockpit-HTML      │
│ PDFs bei Eingang  │                                  │ (Detail + Prüfung)│
└───────────────────┘                                  └──────────────────┘
```

**Leitgedanke:** Es gibt **genau eine** Stelle, an der das Obligo gerechnet wird
(`obligo-core.js`). Die Tagesmeldung und das Cockpit-HTML sind nur zwei Sichten
auf dasselbe Ergebnis. Wird die Logik zweimal implementiert, driften die Zahlen
auseinander, und niemand merkt es — das ist bei einer Kreditlimit-Überwachung
der teuerste denkbare Fehler.

### Was Agicap ersetzt — und was nicht

Der Odoo-Rechnungsexport **ersetzt Agicap als Datenquelle** und ist dabei in
einem Punkt deutlich besser: Er trägt den **Zahlungsstatus**. Der Agicap-Export
enthält nur Rechnungen mit Status „zu zahlen"; bezahlte verschwinden daraus
spurlos. Damit lässt sich heute kein echter Obligo-Verlauf rekonstruieren
(siehe Fachkonzept, Abschnitt 8). Mit Zahlungsstatus geht das.

> **`[ENTSCHEIDUNG DUSTIN]`** Agicap wird **nicht abgeschaltet**, sondern läuft
> mindestens bis zum ersten Monatsabschluss nach Inbetriebnahme **parallel**.
> Einmal pro Woche wird manuell gegengeprüft. Agicap ist das Treasury-System;
> ob der dortige Stand noch anderweitig gebraucht wird, ist nicht abschließend
> geklärt. Erst nach vier sauberen Vergleichen entscheiden wir über die
> Abschaltung.

---

## 3. Arbeitspakete

Reihenfolge ist bindend: AP-0 ist die Grundlage für alles Weitere.

---

### AP-0 — Rechenkern extrahieren (Pflicht, zuerst)

**Problem:** Die gesamte Logik steckt heute in `app_template.html` zwischen
Oberflächen-Code. Ein n8n-Workflow kann sie so nicht aufrufen.

**Auftrag:** Die **reine Logik** unverändert in ein eigenes Modul
`obligo-core.js` herausziehen (UMD oder ESM + CJS-Wrapper, damit es in Node
**und** im Browser läuft). Das Cockpit-HTML lädt danach dieses Modul, statt die
Funktionen selbst zu definieren.

**Was in den Kern gehört** (Zeilenangaben beziehen sich auf `app_template.html`):

| Funktion | ab Zeile | Aufgabe |
|---|---|---|
| `num`, `toDate`, `midnight`, `addDays` | 154 | Zahlen-/Datumsnormalisierung (deutsche Formate) |
| `refKey` | 178 | **Rechnungsnummer normalisieren** (`O` ↔ `0`) — kritisch |
| `csvParse` | 179 | CSV ohne Datumsverdreher |
| `warenartFrom` | 194 | Lieferantentyp ableiten |
| `parseAgicap` | 212 | Rechnungsliste → Items (wird in AP-1 ersetzt/ergänzt) |
| `pdfCMap`, `pdfDecodeContent`, `pdfPagesText`, `pdfText` | 251–326 | PDF-Textextraktion inkl. Sonderzeichensatz |
| `pdfInvoice` | 355 | **Otto-Rechnung aus PDF lesen** — Betrag, Datum, Plombe, Nummer, Retouren-Abzug, Mehrfachrechnungs-Erkennung |
| `parseZipInvoices` | 419 | Sammel-ZIP auspacken |
| `parseBestellung` | 449 | Odoo-Bestellungen → Orders |
| `compute` | 487 | **die Obligo-Berechnung inkl. Dedup** |
| `obligoVerlauf`, `offeneKeys`, `offeneKeyPaare`, `kontinuitaet` | 677–743 | Verlauf und Kontinuitätsprüfung |

**Was NICHT in den Kern gehört:** `gauge`, `faelligChart`, `histChart`,
`histCard`, `verlaufChart`, `verlaufCard`, `render`, das gesamte Wiring ab
Zeile 923, der PDF-Export. Das ist Oberfläche.

**Zwei Umbauten sind dabei nötig:**

1. `compute()` liest heute aus der globalen Variable `state` und direkt aus dem
   DOM (`$("#limit").value`). Signatur ändern auf:
   ```js
   computeObligo({ rechnungen, bestellungen, limit, asof })  →  R
   ```
2. `kontinuitaet()` liest `PREV_SNAP` aus `localStorage`. Vortagesstand als
   **Parameter** übergeben, Persistenz nach außen verlagern (im Browser weiter
   `localStorage`, im n8n-Lauf eine Datei oder DB-Zeile).

**Abnahme AP-0:** `tests/otto-obligo.spec.js` läuft **unverändert** grün
(14 Tests). Die Zahl auf dem Bildschirm ist vor und nach dem Umbau mit
denselben Eingabedateien **auf den Cent identisch**.

> ⚠️ Keine „Verbesserungen" am Kern während der Extraktion. Reines Verschieben.
> Fachliche Änderungen erst ab AP-5, und dann einzeln testbar.

---

### AP-1 — Odoo-Rechnungsexport als Quelle

**Auftrag:** Neuen Parser `parseOdooRechnungen(rows)` schreiben, der dieselbe
Struktur liefert wie `parseAgicap` heute.

**Benötigte Felder** aus dem Odoo-Rechnungsexport (Lieferantenrechnungen /
`account.move`, Typ Eingangsrechnung, Partner = Otto):

| Feld | Zweck | Pflicht |
|---|---|---|
| Rechnungsnummer des Lieferanten | Schlüssel 1 — **durch `refKey()` normalisieren** | ja |
| Rechnungsdatum | Verlauf, Fälligkeit | ja |
| Fälligkeitsdatum | Zahlungsplan | ja |
| Betrag brutto | Summenbildung | ja |
| **Zahlungsstatus** (offen / teilweise / bezahlt) | Topf (A) oder gar nicht | ja |
| **Zahlungsdatum** | echter Obligo-Verlauf | ja |
| Offener Restbetrag | bei Teilzahlungen | ja |
| Lieferantenreferenz / Plombe | Schlüssel 2 | wenn verfügbar |
| Partner | Otto-Filter | ja |

**Zielstruktur** (identisch zu heute, damit `compute` unverändert bleibt):
```js
{ ref, brutto, rd, faellig, zd, paid, art, plombe }
```
`paid` ist `true`, sobald der offene Restbetrag 0 ist. Bei Teilzahlung zählt
der **Restbetrag**, nicht der Rechnungsbetrag.

**Filter:** Nur Otto. Die bestehenden Parser nehmen jede Zeile, deren Partner
„Otto" enthält, schließen aber Zeilen aus, die zusätzlich „AEG" enthalten
(`/otto/i` und nicht `/aeg/i`). Diesen Filter übernehmen, nicht neu erfinden —
und im Odoo-Export prüfen, ob die Partnernamen dort gleich lauten.

**Abnahme AP-1:** Für einen Stichtag, für den noch ein Agicap-Export existiert,
weichen die offenen Rechnungen zwischen Agicap und Odoo **um höchstens den
Betrag der Rechnungen ab, die nachweislich nur in einem der Systeme stehen** —
und jede dieser Abweichungen ist namentlich erklärt. Keine stille Differenz.

---

### AP-2 — Outlook-Abgriff über n8n

**Auftrag:** n8n-Workflow, der Otto-Rechnungen bei Mail-Eingang erfasst.

**Ablauf:**
1. **Trigger:** Microsoft-Outlook-Node, Ordner und Absenderfilter nach Absprache
   mit Mirko (Rechnungswesen). Kein Polling über das gesamte Postfach.
2. **Anhänge filtern:** nur PDF.
3. **PDF parsen:** über `pdfInvoice()` aus `obligo-core.js`.
   **Nicht neu implementieren.** Die Funktion behandelt bereits: eingebettete
   Sonderzeichensätze, zwei Schreibweisen des Retouren-Abzugs, Rechnungsdatum
   aus dem Briefkopf (statt versehentlich aus einem zitierten Mailverlauf), die
   Plombe (genau sieben Ziffern), und sie **erkennt Sammel-PDFs mit mehreren
   Rechnungen und meldet sie, statt zu raten**.
4. **Ergebnis ablegen** in einem Zwischenspeicher (JSON-Datei, SharePoint-Liste
   oder DB — freie Wahl), Datensatz:
   ```js
   { ref, brutto, rd, plombe, quelle:"outlook",
     messageId, empfangenAm, dateiname, parseStatus }
   ```

**Zwingende Eigenschaft — Idempotenz.** Ein Postfach ist kein Buchungsjournal.
Mails werden weitergeleitet, doppelt versendet, verschoben, gelöscht.

```
Der Zwischenspeicher wird über die normalisierte Rechnungsnummer geführt,
NICHT über Mails.
Zweites Auftreten derselben Nummer  →  Datensatz aktualisieren, NICHT addieren.
Nummer nicht lesbar                 →  in die Fehlerliste, NICHT ins Obligo.
```

Niemals über Mails summieren. Dieser eine Satz entscheidet darüber, ob die
Automatisierung belastbar ist.

**Aufräumen:** Sobald eine Rechnungsnummer im Odoo-Export auftaucht, ist der
Outlook-Datensatz überflüssig (Vorrangregel 1 aus dem Fachkonzept). Nach
30 Tagen ohne Odoo-Treffer: in die Fehlerliste, weil eine Rechnung, die einen
Monat lang nicht gebucht wird, ein echtes Problem anzeigt.

**Abnahme AP-2:** Workflow zweimal über dieselben 20 Mails laufen lassen →
identischer Zwischenspeicher, Summe unverändert. Eine Mail doppelt zustellen →
Summe unverändert.

---

### AP-3 — Zusammenführung mit Dedup

**Auftrag:** `compute()` um die dritte Quelle erweitern. Die Vorrangregeln aus
`01_Fachkonzept`, Abschnitt 4 sind **wörtlich** umzusetzen:

```js
// 1) Rechnungen zusammenführen, Odoo gewinnt
for (const r of outlook) {
  if (odooRefs.has(r.ref)) continue;          // schon gebucht -> Odoo zaehlt
  rechnungen.push({ ...r, vorlaeufig: true }); // nur Mail -> vorlaeufig
}

// 2) Blockierte LKW nur zaehlen, wenn ZU IHRER PLOMBE nirgends eine
//    Rechnung existiert — weder in Odoo noch in Outlook
const fakturierePlomben = new Set(
  rechnungen.filter(r => r.plombe).map(r => r.plombe)
);
```

**Wichtig:** Der bestehende Plombe-Abgleich und der 100-%-Cent-Alarm in
`compute()` bleiben **unverändert bestehen**. Die Outlook-Quelle erweitert die
Menge der bekannten Plomben — sie ersetzt die Prüfung nicht.

**In der Ausgabe getrennt ausweisen:**
```
(A1) gebuchte offene Rechnungen        (Odoo)
(A2) eingegangene, noch nicht gebuchte (nur Outlook)   ← neu, vorläufig
(B)  gelieferte LKW ohne jede Rechnung (Odoo Bestellungen, "Blockiert")
```
(A2) ist genau der Betrag, der heute unsichtbar ist. Er muss **separat sichtbar**
sein, sonst ist der fachliche Hauptnutzen verschenkt.

**Abnahme AP-3:** Testfall T-5 in `03_Abnahme_und_Testfaelle.md`.

---

### AP-4 — Tagesmeldung

**Auftrag:** Einmal täglich (Uhrzeit nach Absprache, Vorschlag: werktags nach
dem Odoo-Export) eine Meldung an Dustin und Vertretung.

**Die Meldung muss mehr als eine Zahl enthalten.** Eine nackte Zahl liest nach
zwei Wochen niemand mehr. Pflichtinhalt:

```
Otto-Obligo  <Betrag>            (<Auslastung> % des Limits)
Veränderung zum Vortag           <Delta>  (+Anlieferungen / −Zahlungen)

  gebuchte offene Rechnungen     <Betrag>   (<n>)
  eingegangen, nicht gebucht     <Betrag>   (<n>)   ← neu
  geliefert, keine Rechnung      <Betrag>   (<n> LKW)

Kontinuitätsprüfung:             <ok  /  Abweichung <Betrag>, Ursache offen>
Warnungen:                       <Liste oder "keine">
```

**Eskalation:** Überschreitet das Obligo eine einstellbare Schwelle (Vorschlag:
90 % des Limits), geht die Meldung zusätzlich sofort raus, nicht erst am
nächsten Tag.

> **`[ENTSCHEIDUNG DUSTIN]`** Empfänger sind zunächst **ausschließlich intern**.
> Die Zahl geht **nicht** an Otto oder sonstige Externe. Der Verteiler wird nach
> dem Urlaub festgelegt.

**Abnahme AP-4:** Meldung an einem Tag mit bekannter Abweichung auslösen → die
Abweichung steht drin, mit Betrag.

---

### AP-5 — Plausibilitätsprüfung Preisfaktor (fachlich dringend)

**Hintergrund:** `01_Fachkonzept`, Abschnitt 5. Ein blockierter LKW trug rund
das Fünffache einer normalen Ladung — rechnerisch unmöglich, vermutlich
Warenwert ohne Preisfaktor. Das Obligo war dadurch deutlich zu hoch und zeigte
fast Limitauslastung.

**Auftrag:** Für jede Bestellung in Topf (B):

```js
const warenwert = netto / preisfaktor;
if (warenwert < UNTERGRENZE || warenwert > OBERGRENZE) {
  warnung({
    ref, gesamt,
    text: `${gesamt} € entspricht ${warenwert} € Warenwert — unplausibel,
           vermutlich Preisfaktor nicht angewendet.
           Plausibler Wert: ${gesamt * preisfaktor * 1.19} €`
  });
}
```

Grenzwerte als **Konfiguration**, nicht fest verdrahtet. Sinnvoller Startwert:
Minimum und Maximum der Warenwerte aller Bestellungen der letzten zwölf Monate,
mit 20 % Puffer nach beiden Seiten.

> **Die Summe wird NICHT verändert.** Nur markieren. Eine automatische Korrektur
> wäre eine Interpretation von Fremddaten; ob der Wert falsch ist, entscheidet
> ein Mensch in Odoo, nicht das Tool. `[ENTSCHEIDUNG DUSTIN]`

**Zweite Prüfung im selben Paket:** Fehlt bei einer blockierten Bestellung der
Preisfaktor ganz oder steht er auf 100 %, ist das **immer** eine Warnung —
unabhängig von den Grenzwerten.

**Abnahme AP-5:** Testfall T-6.

---

### AP-6 — Blockierte LKW gegeneinander prüfen

**Hintergrund:** `01_Fachkonzept`, Abschnitt 6. Heute werden blockierte LKW nur
**gegen die Rechnungen** geprüft, nie **gegeneinander**. Zwei Bestellungen mit
identischer 129-Positionen-Produktliste sind so durchgerutscht.

**Auftrag:** Innerhalb von Topf (B) zusätzlich prüfen:
- zwei Bestellungen mit **cent-gleichem** Gesamtbetrag → Warnung
- zwei Bestellungen mit **identischer Produktliste** (Anzahl Positionen und
  Produktnamen gleich) → **starke** Warnung

Auch hier: **nur markieren, Summe unverändert.** Es ist nicht auszuschließen,
dass Otto zwei gleich beladene LKW schickt — unwahrscheinlich, aber nicht
unmöglich. Die Entscheidung trifft ein Mensch.

---

### AP-7 — Cockpit-HTML weiterbetreiben

Das HTML wird **nicht abgelöst**. Es bleibt die Prüf- und Detailsicht: Wenn die
Tagesmeldung eine Abweichung zeigt, schaut man dort nach, welche Rechnung oder
welcher LKW dahintersteckt, und exportiert bei Bedarf das PDF.

**Auftrag:** Nach AP-0 lädt das HTML `obligo-core.js`, statt die Logik selbst zu
enthalten. Der Einzeldatei-Charakter (offline, keine Installation, Doppelklick)
**muss erhalten bleiben** — das Tool läuft auf Rechnern ohne Node und ohne
Admin-Rechte. Das heißt: `obligo-core.js` wird beim Build **eingebettet**, genau
wie heute SheetJS, jsPDF und pako. `build.cjs` entsprechend erweitern.

**Zusätzlich:** Das HTML soll die von n8n erzeugte Tages-JSON laden können, damit
man ohne manuellen Export denselben Stand sieht, den die Meldung zeigt.

---

## 4. Nicht-funktionale Anforderungen

| Thema | Vorgabe |
|---|---|
| **Vertraulichkeit** | Otto-Konditionen (Preisfaktoren, Beträge, Limit) sind vertraulich. Das Repo `eskoiv-crypto/lagerkapazit-t` ist derzeit **öffentlich** — dort dürfen weder echte Beträge noch Konditionen noch das Einstellungs-Passwort landen. Testdaten im Repo bleiben synthetisch. |
| **Passwort** | Das Passwort der 🔒 Einstellungen wird beim Build als Parameter übergeben (`OTTO_CFG_PW`), steht nie im Quellcode. |
| **Nachvollziehbarkeit** | Jeder Tageslauf legt seine Eingangsdaten revisionssicher ab. Wenn in drei Monaten jemand fragt, warum das Obligo an Tag X so hoch war, muss das beantwortbar sein. |
| **Fehlerverhalten** | Fehlt eine Quelle oder eine Pflichtspalte: **Meldung mit ausdrücklichem Hinweis**, dass die Zahl unvollständig ist. **Niemals still weiterrechnen.** Das Tool macht das heute schon so (siehe Spalten-Wächter im Fachkonzept) — dieses Verhalten ist zu übernehmen. |
| **Zeitzone** | Alle Stichtage lokal (Europe/Berlin), Tagesgrenze Mitternacht. Der bestehende Kern normalisiert bereits auf Mitternacht (`midnight()`). |
| **Betrieb** | Der Workflow darf nicht an einem einzelnen Postfach oder Benutzerkonto hängen, das beim nächsten Personalwechsel verschwindet. Technischer Benutzer. |

---

## 5. Aufwandsschätzung `[ESTIMATED]`

Methode: Erfahrungswert nach Umfang der betroffenen Funktionen und Zahl der
Integrationspunkte. Keine Messung. Ein Entwickler, der n8n und Odoo kennt.

| AP | Inhalt | Aufwand |
|---|---|---|
| AP-0 | Kern extrahieren | 1–2 Tage |
| AP-1 | Odoo-Rechnungsexport | 1 Tag |
| AP-2 | Outlook via n8n | 2–3 Tage |
| AP-3 | Zusammenführung + Dedup | 1–2 Tage |
| AP-4 | Tagesmeldung | 1 Tag |
| AP-5 | Plausibilität Preisfaktor | 0,5 Tage |
| AP-6 | LKW gegeneinander | 0,5 Tage |
| AP-7 | HTML anbinden | 1 Tag |
| | **Summe** | **8–11 Tage** |

Unsicherster Posten ist AP-2: Hängt davon ab, wie sauber die Otto-Rechnungen im
Postfach ankommen (einzeln oder gesammelt, einheitlicher Absender oder nicht).
Das lässt sich vorab in einer Stunde klären, indem man zwei Wochen Posteingang
durchsieht — **das sollte der erste Schritt sein**, bevor AP-2 geschätzt wird.

---

## 6. Empfohlene Reihenfolge der Inbetriebnahme

1. **AP-0** — danach ist alles andere überhaupt erst möglich.
2. **AP-5 und AP-6** vorziehen. Beide sind klein, beide verändern die Summe
   nicht, beide adressieren real aufgetretene Fehler. Sie bringen sofort Nutzen,
   auch wenn die Automatisierung noch gar nicht läuft.
3. **AP-1**, dann vier Wochen **parallel** zu Agicap laufen lassen und
   wöchentlich vergleichen.
4. **AP-2 und AP-3** — der eigentliche Mehrwert.
5. **AP-4 und AP-7**.

Nicht alles auf einmal scharf schalten. Jedes Paket einzeln gegen den
bisherigen, bekannten Stand prüfen.
