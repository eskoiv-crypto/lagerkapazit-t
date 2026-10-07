# Fachkonzept Otto-Obligo

**Einstufung:** INTERN · Stand 07.10.2026 · gilt für Tool-Version v2.3

---

## 1. Definition

> **Obligo = alles, was elvinci der Otto GmbH & Co. KGaA zum Stichtag schuldet.**

Das ist mehr als die Summe der offenen Rechnungen. Ein LKW, der heute entladen
wird, ist bereits eine Verbindlichkeit — auch wenn die Rechnung erst in ein paar
Tagen kommt. Otto rechnet genauso. Wer nur offene Rechnungen zählt, sieht das
Limit zu spät.

```
Obligo  =  (A) offene, noch nicht bezahlte Otto-Rechnungen
         + (B) gelieferte LKW, für die noch GAR KEINE Rechnung existiert
```

Dazwischen darf **nichts doppelt** liegen. Das ist die zentrale Anforderung
dieses Fachkonzepts und der Grund, warum die Automatisierung nicht trivial ist.

---

## 2. Die drei Zustände eines LKW

Jede Otto-Anlieferung durchläuft dieselben Stationen. Entscheidend ist, in
welchem Topf sie dabei liegt:

| # | Zustand | Erkennungsmerkmal heute | zählt in |
|---|---|---|---|
| 1 | LKW geliefert, Lieferschein da, **keine Rechnung** | Odoo `purchase.order`, Spalte **Klassifizierungsstatus = „Blockiert"** | **(B)** |
| 2 | Rechnung da, **nicht bezahlt** | Agicap-Export „Ausstehende Rechnungen" | **(A)** |
| 3 | Rechnung **bezahlt** | fällt aus dem Agicap-Export heraus | nirgends |

Der Wechsel von 1 nach 2 ist **wertneutral**: derselbe LKW, anderer Topf. Das
Obligo darf sich dadurch nicht ändern. Nur zwei Dinge bewegen es wirklich:

```
Obligo(heute) = Obligo(gestern) + neue Anlieferungen − Zahlungen
```

Diese Gleichung ist im Tool als **Kontinuitätsprüfung** implementiert
(`kontinuitaet()` im Template). Sie ist das wichtigste Kontrollinstrument und
muss die Automatisierung überleben.

---

## 3. Die bekannte Lücke — warum die Automatisierung überhaupt gebraucht wird

Zwischen Zustand 1 und 2 gibt es ein Loch:

> Ein LKW wird in Odoo klassifiziert und wechselt von „Blockiert" auf
> „Validiert" — **verlässt damit Topf (B)**. Die zugehörige Otto-Rechnung ist
> aber noch nicht in Agicap angekommen — **ist also noch nicht in Topf (A)**.

Der LKW zählt in dieser Phase **nirgends**. Das Obligo ist zu niedrig. Wenn die
Rechnungen dann in einem Schub nachkommen, springt die Zahl.

**Belegter Fall:** Zwischen zwei aufeinanderfolgenden Auswertungen stieg das
Obligo um mehr als das Doppelte dessen, was an diesem Tag angeliefert worden
war — obwohl **keine einzige Rechnung** bezahlt worden war. Die Differenz waren
Rechnungen zu LKW, die vorher in dieser Lücke verschwunden waren.
*(Beträge: siehe `ABNAHME-Referenzwerte_INTERN.md` im Übergabepaket.)*

**Genau das soll der Outlook-Abgriff schließen:** Die Rechnung ist per Mail da,
bevor sie in Agicap oder Odoo gebucht ist. Dieser Zeitvorsprung ist der
fachliche Kern der ganzen Idee.

---

## 4. Die Doppelzählungs-Falle

Mit dem Outlook-Abgriff gibt es künftig **drei** Quellen, die denselben
Geschäftsvorfall kennen können:

```
            ┌──────────────┐
   Otto ───►│  Mail-PDF    │  (sofort)
            └──────┬───────┘
                   │ wird gebucht
                   ▼
            ┌──────────────┐
            │ Odoo Rechnung│  (Tage später)
            └──────────────┘

   Otto ───►│ LKW-Lieferung│──► Odoo Bestellung, Status „Blockiert"
            └──────────────┘
```

Derselbe LKW kann also gleichzeitig als Mail-PDF **und** als gebuchte Rechnung
**und** als blockierte Bestellung auftauchen. Wer alle drei addiert, bekommt ein
dreifach zu hohes Obligo.

### Die beiden Schlüssel

Das Tool löst das heute mit zwei Identifikatoren. Beide müssen in der
Automatisierung zwingend erhalten bleiben:

**Schlüssel 1 — Rechnungsnummer.** Format `1001E0…` bzw. `1001EO…`.
*Falle:* Otto schreibt dieselbe Nummer mal mit Buchstabe `O`, mal mit Null `0`.
Die Funktion `refKey()` im Template normalisiert das. Ohne Normalisierung gilt
dieselbe Rechnung als zwei verschiedene.

**Schlüssel 2 — Plombe.** Siebenstellige Nummer. Steht
- auf der Rechnung (aus dem PDF ausgelesen) und
- in Odoo `purchase.order` in der Spalte **Lieferantenreferenz**.

Die Plombe ist die **einzige zuverlässige Brücke zwischen Rechnung und LKW**.
Nur über sie lässt sich sagen: „dieser blockierte LKW ist in Wahrheit schon
fakturiert, also nicht zusätzlich zählen."

### Vorrangregel (verbindlich)

```
1. Eine Rechnung zählt genau EINMAL.
   Liegt sie in Odoo UND als Mail vor  →  Odoo gewinnt (gebuchter Betrag).
   Nur als Mail                        →  Mail zählt (vorläufig, markiert).

2. Ein LKW (Bestellung) zählt NUR, wenn zu seiner Plombe
   WEDER in Odoo NOCH in Outlook eine Rechnung existiert.

3. Im Zweifel: LKW NICHT zusätzlich zählen.
   Ein zu hohes Obligo bremst Anlieferungen ohne Grund.
   Die Lücke sichtbar machen, nicht wegrechnen.
```

Regel 3 ist eine bewusste fachliche Entscheidung. Es wurde geprüft, ob man
nicht zuordenbare LKW automatisch addieren kann — das erzeugte gegen echte
Daten **Doppelzählungen**, weil eine Rechnung **älter sein kann als der
Odoo-Datensatz des LKW**. Das Feld „Erstellt am" in `purchase.order` ist
**kein Lieferdatum**. Nicht als solches verwenden.

---

## 5. Wie ein Otto-Betrag entsteht

Für jede Bestellung gilt, über alle Datensätze verifiziert:

```
Warenwert (Listenwert der Geräte)  ×  Preisfaktor  =  Nettobetrag
Nettobetrag                        ×  1,19         =  Gesamt (brutto)
```

Der **Preisfaktor** hängt am Lieferantentyp (Spalte `Lieferantentyp` bzw.
`Preisfaktor (%)` im Odoo-Export) und unterscheidet sich je nach Warenkategorie
erheblich. Er wird **erst mit der Klassifizierung gesetzt**.

**Daraus folgt der wichtigste Prüfpunkt:** Bei einer Bestellung im Status
„Blockiert" ist die Klassifizierung per Definition noch nicht gelaufen. Steht
dort trotzdem schon ein „Gesamt", ist nicht garantiert, dass der Preisfaktor
angewendet wurde. Ohne Preisfaktor zeigt das Feld näherungsweise den
**Warenwert** statt des Einkaufswerts — und der ist ein Vielfaches davon.

### Beobachteter Fall (30.09.2026)

Ein einzelner blockierter LKW trug rund das **Fünffache** einer normalen
Ladung. Rückrechnung gegen alle realen Bestellungen:

- Damit dieser Gesamtbetrag bei normalem Preisfaktor korrekt wäre, müsste auf
  dem LKW Ware im **gut Dreifachen** des höchsten je beobachteten Warenwerts
  einer Ladung liegen.
- Der Betrag selbst liegt dagegen **mitten in der normalen Bandbreite der
  Warenwerte**.

→ Mit hoher Wahrscheinlichkeit ist der Betrag der **Warenwert ohne Preisfaktor**.
Der echte Einkaufswert läge im Bereich einer völlig normalen Ladung.
`[ESTIMATED]` — Methode: Rückrechnung über die oben verifizierte Formel,
Annahme Standard-Preisfaktor (trifft auf die große Mehrheit der Bestellungen zu).

**Wirkung:** Das Obligo war an diesem Tag deutlich zu hoch und zeigte fast
Limitauslastung, wo real noch erheblich Luft war.
*(Beträge: siehe `ABNAHME-Referenzwerte_INTERN.md` im Übergabepaket.)*

→ **AP-5 im Änderungsauftrag.** Die Prüfung **verändert die Summe nicht**, sie
markiert nur. Ein automatisches Korrigieren wäre eine Interpretation von
Fremddaten und ist ausdrücklich nicht gewollt.

---

## 6. Zweiter offener Punkt: identische Produktlisten

Zwei Bestellungen trugen **identische Produktlisten über 129 Positionen**, in
identischer Reihenfolge, mit cent-gleichem Netto- und Bruttobetrag — bei
**unterschiedlicher Lieferantenreferenz** und knapp drei Tagen Abstand im Feld
„Erstellt am". Beide standen auf „Blockiert" und zählten beide ins Obligo.

Zwei physisch verschiedene LKW können keine identische 129-Positionen-Liste
haben. Entweder wurde in Odoo kopiert, oder dieselbe Anlieferung ist doppelt
erfasst. **Nicht geklärt — Odoo-Thema.**

Das Tool prüft heute blockierte LKW nur **gegen die Rechnungen**, nicht
**gegeneinander**. Diese Lücke schließt AP-6.

---

## 7. Was heute bereits abgesichert ist

Damit nichts davon versehentlich wegrefaktoriert wird — diese Mechanismen
existieren und sind durch Tests abgedeckt:

| Mechanismus | Zweck |
|---|---|
| **Plombe-Abgleich** | blockierter LKW, dessen Plombe auf einer offenen Rechnung steht → aus (B) entfernt, grüner Hinweis |
| **100-%-Cent-Alarm** | blockierter LKW ohne Plombe, dessen Betrag **auf den Cent** einer offenen Rechnung entspricht → aus (B) entfernt, roter Alarm. Greift bewusst **nur** bei Cent-Gleichheit; ähnliche Beträge sind bei Otto normal |
| **Kontinuitätsprüfung** | vergleicht gegen den gespeicherten Vortagesstand, meldet unerklärte Sprünge mit Zahlen |
| **Retouren-Abzug** | Otto zieht Retouren ab und schreibt das in zwei verschiedenen Bezeichnungen. Beide werden erkannt |
| **Zahlungsziel** | nur für Belege **ohne** Fälligkeitsdatum aus der Quelldatei; liegt ein echtes Datum vor, hat es immer Vorrang |
| **Spalten-Wächter** | fehlt im Odoo-Export die Spalte „Klassifizierungsstatus", meldet das Tool ausdrücklich „nicht bestimmbar" statt still zu niedrig zu rechnen |

---

## 8. Grenzen der heutigen Datenlage

| Grenze | Folge | löst sich durch |
|---|---|---|
| Der Agicap-Export enthält **nur** Rechnungen mit Status „zu zahlen" — bezahlte verschwinden daraus | Es lässt sich **kein echter Obligo-Verlauf** rekonstruieren. Die Verlaufskurve im Tool zeigt deshalb ausdrücklich nur den *Aufbau des offenen Bestands*, startet zwangsläufig bei 0 und kann nie fallen | **den Odoo-Rechnungsexport mit Zahlungsstatus** — dann wird daraus automatisch der echte Verlauf inkl. Limit-Riss-Markierung. Dafür ist im Tool nichts umzustellen, die Umschaltung erkennt das selbst |
| Nur ein kleiner Teil der Rechnungen trägt in der CSV eine Plombe | Zuordnung Rechnung ↔ LKW oft nicht möglich | PDF-Belege mitladen (dort steht die Plombe) — in der Automatisierung kommt sie über den Outlook-Abgriff ohnehin mit |
| „Erstellt am" in `purchase.order` ist kein Lieferdatum | zeitliche Zuordnung unzuverlässig | offen — `[ENTSCHEIDUNG DUSTIN]`, ob ein echtes Wareneingangsdatum im Export ergänzt werden kann |
