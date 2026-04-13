/* ============================================================
   SILO: CSV Upload Handler
   Fixes: #1 (encoding), #2 (delimiter), #3 (row skip),
          #4 (positional indices), #5 (re-upload), #11 (async)
   ============================================================ */

/* FIX #1: Read CSV with ISO-8859-1 encoding (not UTF-8!)
   German chars ä ö ü ß will be garbled without this.
   Returns a Promise so callers can await. FIX #11 */
function readCSVFile(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = (e) => resolve(e.target.result);
    reader.onerror = (e) => reject(new Error('FileReader error: ' + e.target.error));
    reader.readAsText(file, 'ISO-8859-1'); // FIX #1: explicit encoding
  });
}

/* FIX #2 + #3 + #4: Parse CSV text into structured rows
   - delimiter: ";" (never auto-detect)                   — FIX #2
   - header: false (use positional indices, not names)     — FIX #4
   - WE-IST/WA-IST: skip row 0 (summary) + row 1 (header)— FIX #3
   - BESTAND: skip row 0 (header only)                            */
function parseCSV(text, type) {
  const result = Papa.parse(text, {
    delimiter: ';',       // FIX #2: explicit semicolon
    header: false,        // FIX #4: positional indices
    skipEmptyLines: true,
    dynamicTyping: false  // keep everything as strings for safety
  });

  if (result.errors && result.errors.length > 0) {
    console.warn('[CSV] Parse warnings:', result.errors);
  }

  let rows = result.data;

  // FIX #3: Skip summary + header for WE-IST / WA-IST
  if (type === 'we-ist' || type === 'wa-ist') {
    // Row 0 = Zusammenfassung (ignore), Row 1 = Header, Row 2+ = Data
    rows = rows.slice(2);
  } else {
    // BESTAND: Row 0 = Header, Row 1+ = Data
    rows = rows.slice(1);
  }

  return rows;
}

/* Process BESTAND CSV — FIX #4: column indices per spec
   Col 0: Palette, Col 1: Artikel, Col 2: Bezeichner,
   Col 4: Lagerplatz, Col 6: Menge, Col 7: WE-Datum,
   Col 9: Status, Col 10: Auftragsnummer */
function processBestandCSV(rows) {
  const items = [];
  for (const row of rows) {
    if (!row || row.length < 10) continue;

    const bezeichner = (row[2] || '').trim();
    const artikelNr = (row[1] || '').trim();
    const menge = parseInt(row[6]) || 0;
    const lagerplatz = (row[4] || '').trim();
    const status = (row[9] || '').trim().toUpperCase();

    // FIX #14: Set-Artikel factor takes priority, else use Bezeichner matching
    let faktor = getSetArtikelFaktor(artikelNr);
    if (faktor === null) faktor = getGewichtung(bezeichner); // FIX #13

    const punkte = menge * faktor;

    // Lagerplatz parsing per spec
    let zone = 'lager';
    if (lagerplatz.match(/^H05-WA/i)) zone = 'versand';
    else if (lagerplatz.match(/^H05-WE/i)) zone = 'we-zone';

    items.push({
      palette: (row[0] || '').trim(),
      artikel: artikelNr,
      bezeichner: bezeichner,
      lagerplatz: lagerplatz,
      menge: menge,
      weDatum: (row[7] || '').trim(),
      status: status,
      auftragsnummer: (row[10] || '').trim(),
      faktor: faktor,
      punkte: punkte,
      zone: zone,
      isQU: status === 'QU' || status === 'QE'
    });
  }
  return items;
}

/* Process WE-IST CSV — FIX #4: column indices per spec
   Col 2: Bezeichner, Col 5: Bestell-Nr, Col 6: Menge */
function processWeIstCSV(rows) {
  const items = [];
  for (const row of rows) {
    if (!row || row.length < 7) continue;
    items.push({
      bezeichner: (row[2] || '').trim(),
      bestellNr: (row[5] || '').trim(),
      menge: parseInt(row[6]) || 0
    });
  }
  return items;
}

/* Process WA-IST CSV — FIX #4: column indices per spec
   Col 2: Bezeichner, Col 5: Empfänger, Col 6: Auftrag/Beleg, Col 7: Menge */
function processWaIstCSV(rows) {
  const items = [];
  for (const row of rows) {
    if (!row || row.length < 8) continue;
    items.push({
      bezeichner: (row[2] || '').trim(),
      empfaenger: (row[5] || '').trim(),
      auftrag: (row[6] || '').trim(),
      menge: parseInt(row[7]) || 0
    });
  }
  return items;
}
