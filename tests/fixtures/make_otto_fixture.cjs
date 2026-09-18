// Erzeugt SYNTHETISCHE Otto-Rechnungs-PDFs (Struktur wie echte Otto-Belege: Type1/WinAnsi, FlateDecode, Tj/TJ-Operatoren)
// plus eine "Zu prüfen"-ZIP daraus. Keine echten Daten — nur für die Playwright-Tests des Otto-Obligo-Cockpits.
//   node tests/fixtures/make_otto_fixture.cjs
"use strict";
const fs = require("fs"), path = require("path"), zlib = require("zlib");
const OUT = __dirname;

function pdfStr(s) { return "(" + s.replace(/\\/g, "\\\\").replace(/\(/g, "\\(").replace(/\)/g, "\\)") + ")"; }
// lines: [{x,y,size,text}] oder {x,y,size,tj:[...]} für TJ-Arrays
function makePdf(pages) {
  const objs = [];
  const add = o => (objs.push(o), objs.length);
  const fontH = add("<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>");
  const fontB = add("<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold /Encoding /WinAnsiEncoding >>");
  const pageIds = [];
  const pagesId = objs.length + 1 + pages.length * 2; // wird unten befüllt
  for (const lines of pages) {
    let cs = "BT\n";
    for (const l of lines) {
      cs += "/" + (l.bold ? "F2" : "F1") + " " + (l.size || 9) + " Tf\n1 0 0 1 " + l.x + " " + l.y + " Tm\n";
      if (l.tj) cs += "[" + l.tj.map(p => typeof p === "number" ? p : pdfStr(p)).join(" ") + "] TJ\n";
      else cs += pdfStr(l.text) + " Tj\n";
    }
    cs += "ET";
    const comp = zlib.deflateSync(Buffer.from(cs, "latin1"));
    const contId = add(Buffer.concat([Buffer.from("<< /Length " + comp.length + " /Filter /FlateDecode >>\nstream\n", "latin1"), comp, Buffer.from("\nendstream", "latin1")]));
    pageIds.push(add("<< /Type /Page /Parent " + pagesId + " 0 R /MediaBox [0 0 595 842] /Resources << /Font << /F1 " + fontH + " 0 R /F2 " + fontB + " 0 R >> >> /Contents " + contId + " 0 R >>"));
  }
  const realPagesId = add("<< /Type /Pages /Kids [" + pageIds.map(i => i + " 0 R").join(" ") + "] /Count " + pageIds.length + " >>");
  if (realPagesId !== pagesId) throw new Error("Pages-Id-Rechnung falsch");
  const catId = add("<< /Type /Catalog /Pages " + pagesId + " 0 R >>");
  let out = Buffer.from("%PDF-1.4\n%\xE2\xE3\xCF\xD3\n", "latin1");
  const offs = [];
  objs.forEach((o, i) => {
    offs.push(out.length);
    out = Buffer.concat([out, Buffer.from((i + 1) + " 0 obj\n", "latin1"), Buffer.isBuffer(o) ? o : Buffer.from(o, "latin1"), Buffer.from("\nendobj\n", "latin1")]);
  });
  const xref = out.length;
  let x = "xref\n0 " + (objs.length + 1) + "\n0000000000 65535 f \n";
  for (const o of offs) x += String(o).padStart(10, "0") + " 00000 n \n";
  x += "trailer\n<< /Size " + (objs.length + 1) + " /Root " + catId + " 0 R >>\nstartxref\n" + xref + "\n%%EOF\n";
  return Buffer.concat([out, Buffer.from(x, "latin1")]);
}

// Layout wie ein Otto-Beleg: Kopf, Datum, Rechnungsnummer, Positionen, Summenblock mit "Gesamt Rechnungsbetrag (brutto)".
function ottoInvoice({ nr, datum, netto, brutto, ust, plombe, extraPages = 0, anchor = true }) {
  const p1 = [
    { x: 40, y: 800, size: 7, text: "Otto GmbH & Co. KGaA \x95 Werner-Otto-Stra\xDFe 1-7 \x95 22179 Hamburg \x95 A member of the otto group \x95 www.otto.com" },
    { x: 40, y: 760, size: 9, text: "Hamburg, " + datum },
    { x: 40, y: 740, size: 9, text: "Testkunde GmbH" },
    { x: 300, y: 740, size: 9, tj: ["Rechnungsnummer:", -400, nr] },
    { x: 40, y: 700, size: 9, text: "Rechnung - Lieferung - Lieferdatum 01.09.2026" },
    { x: 40, y: 680, size: 9, text: "Pos. Bezeichnung Menge/Einheit Einzelpreis (netto) Gesamt (netto) W\xE4hrung" },
    { x: 40, y: 665, size: 9, text: "000001 Testware gem\xE4\xDF Aufstellung" },
    ...(plombe ? [{ x: 40, y: 652, size: 9, tj: ["Plombe", -300, plombe, -300, "1"] }] : []),
    { x: 300, y: 665, size: 9, text: "1,00 St\xFCck" },
    { x: 400, y: 665, size: 9, text: netto }, { x: 470, y: 665, size: 9, text: netto }, { x: 540, y: 665, size: 9, text: "EUR" },
    { x: 300, y: 630, size: 9, text: "Zwischensumme (netto)" }, { x: 470, y: 630, size: 9, text: netto }, { x: 540, y: 630, size: 9, text: "EUR" },
    { x: 300, y: 615, size: 9, text: "Umsatzsteuer (19%)" }, { x: 470, y: 615, size: 9, text: ust }, { x: 540, y: 615, size: 9, text: "EUR" },
    { x: 300, y: 600, size: 9, bold: true, text: anchor ? " Gesamt Rechnungsbetrag (brutto)" : " Endsumme" },
    { x: 470, y: 600, size: 9, bold: true, text: brutto }, { x: 540, y: 600, size: 9, text: "EUR" },
    { x: 40, y: 560, size: 9, text: "Die Zahlung ist sofort nach Rechnungserhalt ohne Abzug f\xE4llig. Verwendungszweck \"" + nr + "/10041799/081755\"." },
  ];
  const pages = [p1];
  for (let k = 0; k < extraPages; k++) {           // Anlage-Seiten mit Artikelliste (kleinere Beträge NACH der Summe -> "letzter Betrag" wäre falsch)
    const rows = [{ x: 40, y: 800, size: 8, text: "Paletten-Nr LS-Datum LS-Nummer Kanal Artikel Collo Menge Artikel-Bez Einzel-VKP Gesamt-VKP" }];
    for (let r = 0; r < 25; r++) rows.push({ x: 40, y: 780 - r * 14, size: 8, text: (250 + k) + " 27.08.2026 26022 Fundgrube 6738090" + r + " 1 1 Testartikel " + r + " 17,99 17,99 \x80" });
    rows.push({ x: 40, y: 30, size: 7, text: "Referenznummer: " + nr });
    pages.push(rows);
  }
  return makePdf(pages);
}

// --- ZIP (store/deflate, wie Agicap-Export) ---
const CRC = (() => { const t = new Int32Array(256); for (let n = 0; n < 256; n++) { let c = n; for (let k = 0; k < 8; k++) c = c & 1 ? 0xEDB88320 ^ (c >>> 1) : c >>> 1; t[n] = c; } return buf => { let c = -1; for (const b of buf) c = t[(c ^ b) & 255] ^ (c >>> 8); return (c ^ -1) >>> 0; }; })();
function makeZip(entries) {
  const locals = [], centrals = []; let off = 0;
  for (const { name, data } of entries) {
    const nm = Buffer.from(name, "utf8"), comp = zlib.deflateRawSync(data), crc = CRC(data);
    const lh = Buffer.alloc(30); lh.writeUInt32LE(0x04034b50, 0); lh.writeUInt16LE(20, 4); lh.writeUInt16LE(0x0800, 6); lh.writeUInt16LE(8, 8);
    lh.writeUInt16LE(0, 10); lh.writeUInt16LE(0, 12); lh.writeUInt32LE(crc, 14); lh.writeUInt32LE(comp.length, 18); lh.writeUInt32LE(data.length, 22); lh.writeUInt16LE(nm.length, 26); lh.writeUInt16LE(0, 28);
    const ch = Buffer.alloc(46); ch.writeUInt32LE(0x02014b50, 0); ch.writeUInt16LE(20, 4); ch.writeUInt16LE(20, 6); ch.writeUInt16LE(0x0800, 8); ch.writeUInt16LE(8, 10);
    ch.writeUInt16LE(0, 12); ch.writeUInt16LE(0, 14); ch.writeUInt32LE(crc, 16); ch.writeUInt32LE(comp.length, 20); ch.writeUInt32LE(data.length, 24); ch.writeUInt16LE(nm.length, 28);
    ch.writeUInt16LE(0, 30); ch.writeUInt16LE(0, 32); ch.writeUInt16LE(0, 34); ch.writeUInt16LE(0, 36); ch.writeUInt32LE(0, 38); ch.writeUInt32LE(off, 42);
    locals.push(lh, nm, comp); centrals.push(ch, nm); off += lh.length + nm.length + comp.length;
  }
  const cd = Buffer.concat(centrals);
  const eo = Buffer.alloc(22); eo.writeUInt32LE(0x06054b50, 0); eo.writeUInt16LE(0, 4); eo.writeUInt16LE(0, 6); eo.writeUInt16LE(entries.length, 8); eo.writeUInt16LE(entries.length, 10);
  eo.writeUInt32LE(cd.length, 12); eo.writeUInt32LE(off, 16); eo.writeUInt16LE(0, 20);
  return Buffer.concat([...locals, cd, eo]);
}

// --- Fixtures ---
const A = ottoInvoice({ nr: "1001EO26990001", datum: "08. September 2026", netto: "1.037,74", ust: "197,17", brutto: "1.234,91", extraPages: 2 });   // Einzel-PDF mit Anlage
const B = ottoInvoice({ nr: "1001EO26990002", datum: "01. September 2026", netto: "8.403,36", ust: "1.596,64", brutto: "10.000,00", plombe: "4473125" }); // mit Plombe
const C = ottoInvoice({ nr: "1001EO26990003", datum: "02. September 2026", netto: "420,17", ust: "79,83", brutto: "500,00", anchor: false });          // ohne Anker -> Rückfall "letzter Betrag"
fs.writeFileSync(path.join(OUT, "otto_test_invoice.pdf"), A);
fs.writeFileSync(path.join(OUT, "otto_test_invoice_plombe.pdf"), B);
fs.writeFileSync(path.join(OUT, "otto_test_invoice_no_anchor.pdf"), C);
fs.writeFileSync(path.join(OUT, "Otto GmbH Co. KGaA - 1001EO26990001 Purchase Otto Mix.pdf"), A);   // Agicap-Dateinamensschema
fs.writeFileSync(path.join(OUT, "otto_test_zupruefen.zip"), makeZip([
  { name: "Otto GmbH Co. KGaA - 1001EO26990002 Purchase Otto Mix.pdf", data: B },
  { name: "Otto GmbH Co. KGaA - 1001EO26990003 Purchase Otto Hanseatic.pdf", data: C },
  { name: "readme.txt", data: Buffer.from("kein pdf") },
]));
// Nicht-Otto-PDF (muss abgewiesen werden)
fs.writeFileSync(path.join(OUT, "fremd_test_invoice.pdf"), makePdf([[{ x: 40, y: 800, text: "Muster AG Rechnung 4711" }, { x: 40, y: 780, text: "Gesamt Rechnungsbetrag (brutto) 99,00 EUR" }]]));
// Agicap-"Geprüft"-CSV mit derselben Rechnung wie A (Dedup-Test) + einer weiteren
fs.writeFileSync(path.join(OUT, "otto_test_agicap_geprueft.csv"), [
  "Typ,Raten-ID,Rechnungs-ID,Rechnungs-/Ratenbezeichnung,Rechnungsnummer,Status,Begünstigter,Rechnungsdatum,Fälligkeitsdatum,Zahlungsdatum,Rechnungsbetrag exkl. Steuern,Rechnungsbetrag inkl. Steuern,Ratenbetrag inkl. Steuern,Währung,Zahlungsmethode,Bestellnummer,IBAN,Abteilung,Ausgabenarten",
  'Rechnung,r1,i1,"Otto GmbH & Co. KGaA Test",1001EO26990001,Zu bezahlen,"Otto GmbH & Co. KGaA",08-09-2026,08-10-2026,,1037.74,1234.91,1234.91,EUR,Überweisung,,,,"Wareneinkauf|OTTO_Mix"',
  'Rechnung,r2,i2,"Otto GmbH & Co. KGaA Test",1001EO26990009,Zu bezahlen,"Otto GmbH & Co. KGaA",05-09-2026,05-10-2026,,4201.68,5000.00,5000.00,EUR,Überweisung,,,,"Wareneinkauf|OTTO_Mix"',
  'Rechnung,r3,i3,"AEG Test",AEG-1,Zu bezahlen,"AEG Hausgeräte",05-09-2026,05-10-2026,,100.00,119.00,119.00,EUR,Überweisung,,,,"Wareneinkauf|AEG"',
  "",
].join("\n"));
console.log("Fixtures geschrieben nach " + OUT);
