#!/usr/bin/env node
/*
 * Selbsttest für lagerwert_core.js (Rechenkern des Lagerwert-Rechners).
 *
 *  1. Synthetischer Bestand + Odoo-Export mit von Hand nachgerechneten Sollwerten
 *     (Dublette, Schrott, Ø-Fill-Kaskade, Korrekturliste, Monatsreihe, Stichtag).
 *  2. Abgleich gegen das Python-Skript: liegen die echten Stichtagsdateien lokal
 *     (data/…, gitignored) und die Faktendateien warenwert_facts_*.json vor,
 *     muss der JS-Kern auf den Cent dieselben Summen liefern wie warenwert_stichtag.py.
 *
 * Aufruf:  node tests/test_lagerwert_core.cjs
 */
const fs = require("fs");
const path = require("path");
const ROOT = path.resolve(__dirname, "..");
// Die Repo-package.json setzt "type": "module"; die UMD-Bibliotheken und der
// Rechenkern werden deshalb über einen kleinen CommonJS-Loader geladen.
function ladeCjs(file) {
  const m = { exports: {} };
  new Function("module", "exports", "require", "self", "window", fs.readFileSync(file, "utf8"))(m, m.exports, require, globalThis, undefined);
  return m.exports;
}
const XLSX = ladeCjs(path.join(ROOT, "vendor", "xlsx.full.min.js"));
const { jsPDF } = ladeCjs(path.join(ROOT, "vendor", "jspdf.umd.min.js"));
const C = ladeCjs(path.join(ROOT, "lagerwert_core.js"));

const fehler = [];
function ok(cond, msg) { if (!cond) fehler.push(msg); }
function nah(a, b, msg, tol = 0.01) { if (Math.abs(a - b) > tol) fehler.push(`${msg}: ${a} != ${b}`); }

function odooAusXlsx(file) {
  const wb = XLSX.read(fs.readFileSync(file), { type: "buffer" });
  const rows = XLSX.utils.sheet_to_json(wb.Sheets[wb.SheetNames[0]], { header: 1, defval: null, raw: true });
  return C.parseOdoo(rows);
}
function bestandAusCsv(file) {
  return C.parseBestand(new TextDecoder("iso-8859-1").decode(fs.readFileSync(file)));
}

// ------------------------------------------------------------ 1. synthetisch
(function synthetisch() {
  const kopf = "Palette;Artikel;Bezeichner;Charge;LgPlatz;Standort;Menge;WE-Datum;Bestellnummer;Status;Auftrag";
  const B = [
    ["900000001", "Kühlschrank", "QE"], ["900000002", "Kühlschrank", "QE"],
    ["900000003", "Kühlschrank", "QE"],            // nicht in Odoo -> Ø Bezeichner
    ["900000004", "Herd", "VS"], ["900000005", "Herd", "AA"], // 005: EK 0 -> Ø Kategorie
    ["900000006", "Schrottpalette", "QE"],         // Schrott -> 0
    ["900000007", "Kühlschrank", "QE"],            // nicht in Odoo -> Ø Bezeichner
    ["900000001", "Kühlschrank", "QE"]             // Dublette
  ];
  const csv = [kopf].concat(B.map(b => `${b[0]};007733982913;${b[1]};${b[0]};H05-WA-02-00 ;NH5;1;04.08.2025;20250717_DIG;${b[2]};`)).join("\n") + "\n";
  const bestand = C.parseBestand(csv);
  ok(bestand.length === 8, "Bestand: 8 Zeilen erwartet");

  const H = ["Los-/Seriennummer", "Produkt", "Marke", "Produktkategorie", "Lieferant", "Lieferantentyp", "Lager-Code", "Einkaufspreis"];
  const O = [H,
    ["ELV-1", "Kühlschrank A", "AEG", "Kühlschränke", "AEG GmbH", "AEG_DE", "900000001", 200],
    ["ELV-2", "Kühlschrank B", "AEG", "Kühlschränke", "AEG GmbH", "AEG_DE", "900000002", 300],
    ["ELV-4", "Herd D", "Bosch", "Herde", "Otto GmbH", "OTTO_B", "900000004", 500],
    ["ELV-5", "Herd E", "Bosch", "Herde", "Otto GmbH", "OTTO_B", "900000005", 0],
    ["ELV-6", "Palette", "AEG", "Sonstiges", "AEG GmbH", "AEG_Schrott", "900000006", 0],
    ["ELV-9", "Herd Z", "Bosch", "Herde", "Otto GmbH", "OTTO_B", "900000099", 999],
    ["Customers (6)", "", "", "", "", "", "", 99999]];        // Gruppenzeile
  const odoo = C.parseOdoo(O);
  ok(odoo.ek["900000001"] === 200 && !("" in odoo.ek), "Odoo-Preise gelesen, Gruppenzeile ignoriert");

  // Soll ohne Korrektur: Odoo 200+300+500 = 1000 (3) | Ø: 003,007 -> Ø Bez. Kühlschrank 250, 005 -> Ø Kat. Herde 500 => 1000 (3) | Schrott 1
  let r = C.berechne({ stichtag: "2026-08-31", bestand, bestandName: "BESTAND134_20260831_2330.CSV", odoo, odooName: "T.xlsx" });
  ok(r.erg.geraete === 7, "7 eindeutige Geräte"); ok(r.erg.duplikate === 1, "1 Dublette");
  nah(r.erg.ek_odoo, 1000, "ek_odoo"); ok(r.erg.n_odoo === 3, "n_odoo");
  nah(r.erg.ek_geschaetzt, 1000, "ek_geschaetzt"); ok(r.erg.n_geschaetzt === 3, "n_geschaetzt");
  ok(r.erg.n_schrott_ek0 === 1, "Schrott"); nah(r.erg.ek_gesamt, 2000, "ek_gesamt");
  const split = C.statusAufteilung(r.geraete);
  nah(split.gesamt.ek, 2000, "split gesamt"); nah(split.verkauft.ek, 1000, "split VS+AA"); ok(split.verkauft.n === 2, "split n");

  // Korrekturliste: 002 -> 350, 005 -> 120, 099 nicht im Bestand
  const korr = C.korrekturenAusCsv("Lager-Nr;EK;Grund\n900000002;350;Neuklassifizierung\n900000005;120,00;Nachgezogen\n900000099;10;Test\n");
  r = C.berechne({ stichtag: "2026-08-31", bestand, odoo, korr, korrName: "k.csv" });
  // Odoo 200+500 = 700 | Korrektur 470 | Ø Bez. Kühlschrank = (200+350)/2 = 275 -> 003,007 = 550 | gesamt 1720
  nah(r.erg.ek_odoo, 700, "korr: ek_odoo"); nah(r.erg.ek_korrektur, 470, "korr: ek_korrektur");
  ok(r.erg.n_korrektur === 2 && r.erg.n_korrektur_nicht_im_bestand === 1, "korr: Zähler");
  nah(r.erg.ek_geschaetzt, 550, "korr: Ø-Fill"); nah(r.erg.ek_gesamt, 1720, "korr: gesamt");
  ok(r.erg.korrektur_gruende["Neuklassifizierung"].ek_vorher_odoo === 300, "korr: vorher Odoo");
  ok(r.erg.korrektur_gruende["Nachgezogen"].n_vorher_ohne_ek === 1, "korr: vorher ohne EK");
  let dup = false; try { C.korrekturenAusCsv("Lager-Nr;EK;Grund\n1;1;a\n1;2;b\n"); } catch (e) { dup = true; }
  ok(dup, "doppelte Lager-Nr in Korrekturliste muss abgelehnt werden");

  // Monatsreihe
  const serie = C.serieFortschreiben("Monatsende;Stück;EK-Wert\n31.07.2026;5719;690125\n", r.erg);
  ok(serie.indexOf("31.08.2026;7;1720") > 0 && serie.indexOf("31.07.2026;5719;690125") > 0, "Reihe fortgeschrieben");
  ok(C.stichtagAusDateiname("BESTAND134_20260930_2300.CSV") === "2026-09-30", "Stichtag aus Dateiname");
  ok(C.eur(612830.4) === "612.830 €" && C.eur(2.5) === "2 €" && C.eur(3.5) === "4 €", "eur() rundet wie Python");
  ok(C.zuZahl("1.234,56") === 1234.56 && C.zuZahl("216.61") === 216.61 && C.zuZahl("abc") === 0, "zuZahl");

  // Odoo gewinnt, wenn sich der Preis seit der Korrektur geändert hat (Referenzspalte)
  const korrRef = C.korrekturenAusCsv("Lager-Nr;EK;Grund;EK Odoo bei Korrektur\n900000002;350;Neuklassifizierung;300\n900000004;999;Alt;400\n");
  r = C.berechne({ stichtag: "2026-08-31", bestand, odoo, korr: korrRef });
  ok(r.erg.n_korrektur_ueberholt === 1, "ref: 1 Korrektur überholt (004: Odoo 500 ≠ Referenz 400)");
  ok(r.erg.n_korrektur === 1 && r.geraete.find(g => g["Lager-Nr"] === "900000004")["EK bewertet"] === 500, "ref: Odoo-Preis übernommen");
  ok(r.korrAusgabe.length === 1 && r.korrAusgabe[0].ref === 300, "ref: Ausgabe nur angewandte Korrektur mit aktuellem Odoo-EK");

  // AEG-Satz: Lose ohne EK von AEG (Lieferant/Bestellnr/Migration+Produkt) -> fester Satz; Schrott bleibt 0
  const B2 = csv.replace("900000003;H05-WA-02-00 ;NH5;1;04.08.2025;20250717_DIG;", "900000003;H05-WA-02-00 ;NH5;1;04.08.2025;5022851282_AEG_IT;");
  const bestand2 = C.parseBestand(B2);
  r = C.berechne({ stichtag: "2026-08-31", bestand: bestand2, odoo, aegSatz: 216.61 });
  // 003: über AMM-Bestellnr AEG -> 216,61 | 006: AEG-Schrott -> 0 | 005 (Bosch/OTTO) und 007 (unbekannt) -> Ø-Fill
  ok(r.erg.n_aeg_satz === 1, "AEG-Satz: genau 1 Los (003)"); ok(r.erg.n_schrott_ek0 === 1, "AEG-Satz: Schrott bleibt Schrott");
  ok(Math.abs(r.geraete.find(g => g["Lager-Nr"] === "900000003")["EK bewertet"] - 216.61) < 0.001, "AEG-Satz: 003 = 216,61");
  ok(C.istAeg("Migration Altbestand", "nan", "[ELV-1] AEG Einbaukühlgefrierkombination", "") === true, "istAeg: Migration Altbestand + AEG-Produkt");
  ok(C.istAeg("Otto GmbH & Co. KGaA", "OTTO_Mix (18.5%)", "AEG Waschmaschine", "") === false, "istAeg: OTTO-Ware mit Marke AEG zählt nicht");

  // PDF baut
  const doc = C.bauPdf(jsPDF, r.erg, C.serieLesen(serie), "05.10.2026", "Test");
  ok(doc.output("arraybuffer").byteLength > 2000, "PDF erzeugt");
  console.log("✓ synthetisch: 7 Geräte / 2000 € · Korrekturliste 1720 € · Odoo-gewinnt · AEG-Satz · Dublette, Schrott, Ø-Fill, Reihe, PDF ok");
})();

// ------------------------------------------------------------ 2. gegen Python
function vergleich(label, bestandDatei, odooDatei, korrDatei, factsDatei, stichtag) {
  const p = f => path.join(ROOT, f);
  if (![bestandDatei, odooDatei, factsDatei].every(f => fs.existsSync(p(f)))) {
    console.log(`– ${label}: Quelldateien nicht lokal vorhanden, Abgleich übersprungen`); return;
  }
  const F = JSON.parse(fs.readFileSync(p(factsDatei), "utf8"));
  const bestand = bestandAusCsv(p(bestandDatei));
  const odoo = odooAusXlsx(p(odooDatei));
  const korr = korrDatei && fs.existsSync(p(korrDatei)) ? C.korrekturenAusCsv(fs.readFileSync(p(korrDatei), "utf8")) : {};
  const r = C.berechne({ stichtag, bestand, bestandName: path.basename(bestandDatei), odoo, odooName: path.basename(odooDatei), korr, korrName: korrDatei ? path.basename(korrDatei) : null });
  const felder = ["geraete", "n_odoo", "n_korrektur", "n_geschaetzt", "n_schrott_ek0", "duplikate", "bestand_zeilen_gesamt"];
  felder.forEach(k => ok(r.erg[k] === F[k], `${label} ${k}: JS ${r.erg[k]} != Python ${F[k]}`));
  ["ek_odoo", "ek_korrektur", "ek_geschaetzt", "ek_belegt", "ek_gesamt"].forEach(k => nah(r.erg[k], F[k], `${label} ${k}`, 0.01));
  Object.keys(F.korrektur_gruende || {}).forEach(g => {
    ok(g in r.erg.korrektur_gruende, `${label} Gruppe fehlt: ${g}`);
    if (g in r.erg.korrektur_gruende) nah(r.erg.korrektur_gruende[g].ek, F.korrektur_gruende[g].ek, `${label} Gruppe ${g}`);
  });
  console.log(`✓ ${label}: ${C.eur(r.erg.ek_gesamt)} / ${r.erg.geraete} Geräte — identisch mit ${factsDatei}`);
  return r;
}
vergleich("August 2026", "data/amm/BESTAND134_20260831_1700.CSV", "data/odoo/LosSerie (stock.lot)_upload1.xlsx",
  "korrekturen_2026-08-31_AEG.csv", "warenwert_facts_2026-08-31_v2.json", "2026-08-31");
// September aus der übernommenen August-Teilliste (194 Lose) + AEG-Satz: muss dieselbe Zahl ergeben
(function () {
  const p = f => path.join(ROOT, f);
  const fs_ = ["data/amm/BESTAND134_20260930_2300.CSV", "data/odoo/LosSerie (stock.lot)_2026-10-02.xlsx", "korrekturen_2026-09-30_AEG_vorbereitet.csv", "warenwert_facts_2026-09-30_v1.json"];
  if (!fs_.every(f => fs.existsSync(p(f)))) { console.log("– September (194 + AEG-Satz): übersprungen"); return; }
  const F = JSON.parse(fs.readFileSync(p(fs_[3]), "utf8"));
  const r = C.berechne({ stichtag: "2026-09-30", bestand: bestandAusCsv(p(fs_[0])), odoo: odooAusXlsx(p(fs_[1])),
    korr: C.korrekturenAusCsv(fs.readFileSync(p(fs_[2]), "utf8")), aegSatz: 216.61 });
  ok(r.erg.n_aeg_satz === 353, `Sep 194+Satz: n_aeg_satz ${r.erg.n_aeg_satz} != 353`);
  nah(r.erg.ek_gesamt, F.ek_gesamt, "Sep 194+Satz ek_gesamt"); ok(r.korrAusgabe.length === 547, "Sep 194+Satz: Korrekturliste 547");
  console.log(`✓ September aus August-Teilliste + AEG-Satz: ${C.eur(r.erg.ek_gesamt)} — identisch`);
})();
const sep = vergleich("September 2026", "data/amm/BESTAND134_20260930_2300.CSV", "data/odoo/LosSerie (stock.lot)_2026-10-02.xlsx",
  "korrekturen_2026-09-30_AEG.csv", "warenwert_facts_2026-09-30_v1.json", "2026-09-30");
if (sep && process.env.PDF_OUT) {
  const serie = fs.existsSync(path.join(ROOT, "warenwert_monatsende.csv")) ? C.serieLesen(fs.readFileSync(path.join(ROOT, "warenwert_monatsende.csv"), "utf8")) : [];
  const doc = C.bauPdf(jsPDF, sep.erg, serie, "02.10.2026", "warenwert_stichtag.py");
  fs.writeFileSync(process.env.PDF_OUT, Buffer.from(doc.output("arraybuffer")));
  console.log("  → PDF geschrieben:", process.env.PDF_OUT);
}

if (fehler.length) { console.log("FEHLGESCHLAGEN:"); fehler.forEach(f => console.log("  ✗", f)); process.exit(1); }
console.log("✓ Alle Prüfungen bestanden");
