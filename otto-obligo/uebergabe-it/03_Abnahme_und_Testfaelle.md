# Abnahme und Testfälle

**Einstufung:** INTERN · Stand 07.10.2026

---

## 1. Die bestehenden Tests zuerst

Im Repo liegt `tests/otto-obligo.spec.js` — 14 Playwright-Tests gegen die
Rechenlogik. **Sie müssen nach jeder Änderung grün sein.**

```bash
npm install
npx playwright test tests/otto-obligo.spec.js
```

Läuft gegen eine lokal gebaute HTML-Datei über `file://`. Falls Chromium nicht
gefunden wird, Pfad setzen:
```bash
PW_CHROMIUM_PATH=/pfad/zu/chromium npx playwright test tests/otto-obligo.spec.js
```

Build für die Tests (ohne Historie, Passwort beliebig):
```bash
OTTO_CFG_PW='test' node otto-obligo/_build-kit/build.cjs --no-hist \
  --out otto-obligo/dist/Otto-Obligo-Cockpit.test.html
```

**Die Testdaten im Repo sind synthetisch** (`tests/fixtures/make_otto_fixture.cjs`
erzeugt Fake-Rechnungen mit erfundenen Beträgen). Das ist Absicht: Das Repo ist
öffentlich. Echte Otto-Beträge gehören dort nicht hinein — auch nicht in Tests.

Wer einen neuen Fall abdecken will, erweitert den Fixture-Generator um einen
synthetischen Beleg. **Keine echten Rechnungen committen.**

---

## 2. Woher die Testdaten für die fachliche Abnahme kommen

Für die echte Abnahme braucht es echte Exporte. Die liegen **nicht** in diesem
Paket. Dustin oder Mirko ziehen sie bei Bedarf:

| Datei | Quelle | Wichtig |
|---|---|---|
| Bestellungen | Odoo, Modell `purchase.order`, Lieferant Otto | Spalte **„Klassifizierungsstatus"** muss im Export enthalten sein. Ohne sie kann Topf (B) nicht bestimmt werden und das Tool meldet ausdrücklich „nicht bestimmbar". Ebenso **„Lieferantenreferenz"** (= Plombe) und **„Preisfaktor (%)"**. |
| Rechnungen (neu) | Odoo, Lieferantenrechnungen | mit **Zahlungsstatus**, **Zahlungsdatum** und **offenem Restbetrag** |
| Rechnungen (alt, Vergleich) | Agicap, Tab „Ausstehende Rechnungen" | muss **alle** offenen enthalten: Geprüft + Zu prüfen + Posteingang. Fehlt ein Teil, ist das Obligo zu niedrig. |
| Rechnungs-PDFs | Agicap-Sammel-ZIP „Zu prüfen" oder einzelne Mail-Anhänge | nur hier steht die Plombe zuverlässig |

Die Dateien enthalten Otto-Konditionen. **Nicht ins Repo, nicht nach außen.**

---

## 3. Fachliche Testfälle

### T-1 · Kein Doppelzählen bei Topfwechsel *(Kernanforderung)*

> **Aufbau:** Stand von Tag 1 mit einem LKW in Topf (B). An Tag 2 ist die
> Rechnung zu genau diesem LKW da (gleiche Plombe), der LKW steht in Odoo nicht
> mehr auf „Blockiert".
>
> **Erwartet:** Das Obligo ist an Tag 2 **unverändert** (bis auf echte neue
> Anlieferungen und Zahlungen). Der Betrag ist von (B) nach (A) gewandert.
> Die Kontinuitätsprüfung meldet **keine** Abweichung.
>
> **Fehlerbild, auf das zu achten ist:** Obligo springt um genau den Betrag
> dieses LKW nach oben → Dedup greift nicht, Plombe wird nicht verglichen.

### T-2 · Dieselbe Rechnung aus zwei Quellen *(ab AP-3)*

> **Aufbau:** Eine Rechnung liegt als Mail-PDF im Outlook-Zwischenspeicher
> **und** gebucht im Odoo-Export.
>
> **Erwartet:** Sie zählt **einmal**, mit dem **Odoo-Betrag**. In der Aufgliederung
> erscheint sie unter (A1), **nicht** unter (A2).

### T-3 · Idempotenz des Mail-Abgriffs *(ab AP-2)*

> **Aufbau:** Den n8n-Workflow zweimal über dieselben Mails laufen lassen.
> Zusätzlich eine Mail manuell ein zweites Mal zustellen.
>
> **Erwartet:** Zwischenspeicher und Summe **identisch**. Kein Datensatz doppelt.

### T-4 · Zahlung senkt das Obligo

> **Aufbau:** Zwei aufeinanderfolgende Odoo-Rechnungsexporte, dazwischen wurde
> eine Rechnung bezahlt.
>
> **Erwartet:** Obligo sinkt um **genau** den Rechnungsbetrag. Die Kontinuitäts-
> prüfung weist die Zahlung als Abfluss aus und meldet **keine** Abweichung.
>
> **Hinweis:** Das ist der Fall, der mit dem alten Agicap-Export **nicht**
> prüfbar war, weil bezahlte Rechnungen dort spurlos verschwinden. Mit dem
> Zahlungsstatus aus Odoo wird daraus erstmals ein echter Verlauf.

### T-5 · Die Lücke wird sichtbar *(der fachliche Hauptnutzen, ab AP-3)*

> **Aufbau:** Ein LKW wird in Odoo klassifiziert (verlässt Topf B), die Rechnung
> liegt als Mail vor, ist aber noch nicht gebucht.
>
> **Erwartet:** Der Betrag erscheint unter **(A2) „eingegangen, nicht gebucht"**.
> Das Obligo bleibt gegenüber dem Vortag **stabil**.
>
> **Fehlerbild:** Das Obligo fällt und steigt Tage später wieder — dann wirkt
> der Outlook-Abgriff nicht. Genau das ist der Zustand, der heute zu dem
> beobachteten sprunghaften Anstieg an einem einzigen Tag geführt hat.

### T-6 · Unplausibler Bestellwert *(ab AP-5)*

> **Aufbau:** Eine blockierte Bestellung, deren Gesamtbetrag geteilt durch den
> Preisfaktor einen Warenwert weit außerhalb der üblichen Bandbreite ergibt.
>
> **Erwartet:** **Warnung** mit Rückrechnung und plausiblem Alternativwert.
> Die **Obligo-Summe bleibt unverändert**.
>
> **Fehlerbild:** Die Summe ändert sich → das Tool korrigiert eigenmächtig
> Fremddaten. Das ist ausdrücklich nicht gewollt.

### T-7 · Fehlende Pflichtspalte

> **Aufbau:** Odoo-Bestellexport **ohne** Spalte „Klassifizierungsstatus".
>
> **Erwartet:** Ausdrückliche Meldung, dass Topf (B) nicht bestimmbar und das
> Obligo **womöglich zu niedrig** ist. **Kein** stilles Weiterrechnen.
>
> Dieses Verhalten existiert heute bereits — es darf beim Umbau nicht verloren
> gehen.

### T-8 · Rechnungsnummer mit Buchstabe O statt Null

> **Aufbau:** Dieselbe Rechnung einmal als `1001EO…`, einmal als `1001E0…`.
>
> **Erwartet:** Gilt als **eine** Rechnung. `refKey()` normalisiert das.
>
> **Fehlerbild:** Zählt doppelt → `refKey()` wurde beim Umbau umgangen.
> Dieser Fall ist real: Otto schreibt beide Varianten.

### T-9 · Sammel-PDF mit mehreren Rechnungen

> **Aufbau:** Ein PDF-Anhang, der mehrere Otto-Rechnungen enthält.
>
> **Erwartet:** Das Tool **meldet** das und rät **nicht**. Die Datei landet in
> der Fehlerliste zur manuellen Behandlung.
>
> Die bestehende Funktion `pdfInvoice()` erkennt das bereits (Feld `multi`).
> Der n8n-Workflow muss darauf reagieren.

### T-10 · Retouren-Abzug in beiden Schreibweisen

> **Aufbau:** Zwei Rechnungs-PDFs, die den Retouren-Abzug unterschiedlich
> benennen.
>
> **Erwartet:** In **beiden** Fällen wird der Abzug erkannt und der Brutto-Betrag
> stimmt mit der Gegenprobe (netto + USt) überein.
>
> Ist als Test bereits vorhanden und muss grün bleiben.

---

## 4. Abnahme-Gesamtkriterium

Die Automatisierung ist abgenommen, wenn über **vier aufeinanderfolgende Wochen**:

1. Der automatisch ermittelte Stand und der manuell über das Cockpit ermittelte
   Stand **übereinstimmen** — oder jede Abweichung namentlich erklärt ist.
2. Die **Kontinuitätsprüfung** an keinem Tag eine unerklärte Abweichung meldet.
3. Jeder Tag, an dem (A2) ungleich null war, nachvollziehbar zeigt, dass der
   Betrag später in (A1) aufgetaucht ist — damit ist belegt, dass der
   Outlook-Abgriff die Lücke wirklich schließt und nicht doppelt zählt.

Erst danach steht die Entscheidung über Agicap an. `[ENTSCHEIDUNG DUSTIN]`

---

## 5. Was im Zweifel gilt

> Lieber eine Meldung „Zahl unvollständig, Quelle X fehlt" als eine glatte Zahl,
> der niemand ansieht, dass sie falsch ist.

Eine Kreditlimit-Überwachung, die still falsch rechnet, ist schlechter als gar
keine — denn man verlässt sich auf sie.
