/* ============================================================
   SILO: XLSX Upload Handler
   Fixes: #6 (ArrayBuffer), #7 (multi-file race),
          #8 (sheet selection), #11 (async)
   ============================================================ */

/* FIX #6: Read XLSX with readAsArrayBuffer (NOT readAsText!)
   FIX #11: Returns a Promise for proper async chaining */
function readXLSXFile(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = (e) => {
      try {
        const data = new Uint8Array(e.target.result);
        const workbook = XLSX.read(data, { type: 'array' }); // FIX #6
        resolve(workbook);
      } catch (err) {
        reject(new Error('XLSX parse error: ' + err.message));
      }
    };
    reader.onerror = (e) => reject(new Error('FileReader error: ' + e.target.error));
    reader.readAsArrayBuffer(file); // FIX #6: NOT readAsText or readAsBinaryString
  });
}

/* FIX #8: Get sheet data — tries first sheet, but accepts override.
   Returns array of objects (rows) using column headers from the sheet. */
function getSheetData(workbook, preferredSheet) {
  let sheetName;

  if (preferredSheet && workbook.SheetNames.includes(preferredSheet)) {
    sheetName = preferredSheet;
  } else {
    sheetName = workbook.SheetNames[0];
    if (workbook.SheetNames.length > 1) {
      console.info('[XLSX] Multiple sheets found:', workbook.SheetNames, '— using:', sheetName);
    }
  }

  const sheet = workbook.Sheets[sheetName];
  return XLSX.utils.sheet_to_json(sheet, { defval: '' });
}

/* Process WE Pipeline XLSX → array of incoming goods entries */
function processWePipeXLSX(rows) {
  return rows.map(row => ({
    bezeichner: String(row['Bezeichner'] || row['Artikelbezeichnung'] || '').trim(),
    bestellNr: String(row['Bestellnummer'] || row['Bestell-Nr'] || '').trim(),
    menge: parseInt(row['Menge'] || row['Anzahl'] || 0) || 0,
    lieferdatum: String(row['Lieferdatum'] || row['Datum'] || '').trim()
  }));
}

/* Process Fulfilment Pipeline XLSX → Map<AU-Nr, {...}>
   Key columns: Auftragsnummer, Versanddatum, Spediteur, Kunde, Land */
function processFulfilmentXLSX(rows) {
  const map = new Map();
  for (const row of rows) {
    const auNr = String(row['Auftragsnummer'] || row['AU-Nr'] || row['Auftrags-Nr'] || '').trim();
    if (!auNr) continue;

    // Sum Menge if same AU-Nr appears multiple times
    const existing = map.get(auNr);
    const menge = parseInt(row['Menge'] || row['Anzahl'] || 0) || 0;

    if (existing) {
      existing.summe += menge;
    } else {
      map.set(auNr, {
        kunde: String(row['Kunde'] || row['Kundenname'] || '').trim(),
        land: String(row['Land'] || '').trim(),
        versanddatum: String(row['Versanddatum'] || row['Versand'] || '').trim(),
        spediteur: String(row['Spediteur'] || row['Spedition'] || '').trim(),
        summe: menge
      });
    }
  }
  return map;
}

/* Process Auftrag Status XLSX → Map<AU-Nr, {...}> */
function processAuftragStatusXLSX(rows) {
  const map = new Map();
  for (const row of rows) {
    const auNr = String(row['Auftragsnummer'] || row['AU-Nr'] || '').trim();
    if (!auNr) continue;
    map.set(auNr, {
      status: String(row['Status'] || '').trim(),
      kunde: String(row['Kunde'] || '').trim(),
      land: String(row['Land'] || '').trim(),
      artikel: String(row['Artikel'] || row['Bezeichnung'] || '').trim(),
      spediteur: String(row['Spediteur'] || '').trim()
    });
  }
  return map;
}

/* Process Planner XLSX → Map<AU-Nr, Planner-Notiz> */
function processPlannerXLSX(rows) {
  const map = new Map();
  for (const row of rows) {
    const auNr = String(row['Auftragsnummer'] || row['AU-Nr'] || row['Titel'] || '').trim();
    if (!auNr) continue;
    const notiz = String(row['Notiz'] || row['Beschreibung'] || row['Label'] || '').trim();
    map.set(auNr, notiz);
  }
  return map;
}
