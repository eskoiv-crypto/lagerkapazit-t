/* ============================================================
   SILO: Upload Handler (Orchestrator)
   Fixes: #5 (re-upload), #7 (multi-file), #9 (validation),
          #10 (feedback), #11 (async), #12 (drag-drop)
   ============================================================ */

/* FIX #9: Validate file type before processing */
function validateFile(file, expectedFormat) {
  const name = file.name.toLowerCase();
  if (expectedFormat === 'csv') {
    if (!name.endsWith('.csv') && !name.endsWith('.txt')) {
      throw new Error('Erwartetes Format: CSV. Erhalten: ' + file.name);
    }
  } else if (expectedFormat === 'xlsx') {
    if (!name.endsWith('.xlsx') && !name.endsWith('.xls')) {
      throw new Error('Erwartetes Format: XLSX. Erhalten: ' + file.name);
    }
  }
  if (file.size === 0) {
    throw new Error('Datei ist leer: ' + file.name);
  }
  if (file.size > 50 * 1024 * 1024) {
    throw new Error('Datei zu groß (max 50MB): ' + file.name);
  }
}

/* FIX #11: Main upload handler — fully async, Promise-based
   FIX #5: Resets input.value AFTER processing
   FIX #7: Copies file references BEFORE any async work
   FIX #10: Updates visual status per slot */
async function handleFileUpload(input, type) {
  const slotId = 'slot-' + type;

  // FIX #7: Copy file list immediately (FileList is live!)
  const files = Array.from(input.files);
  if (files.length === 0) return;

  // FIX #10: Show loading
  setUploadStatus(slotId, 'loading', 'Verarbeite...');

  try {
    for (const file of files) {
      // FIX #9: Validate file type
      const isCSV = ['bestand', 'we-ist', 'wa-ist'].includes(type);
      validateFile(file, isCSV ? 'csv' : 'xlsx');

      if (isCSV) {
        await handleCSVUpload(file, type);
      } else {
        await handleXLSXUpload(file, type);
      }
    }

    // FIX #10: Show success
    const fileNames = files.map(f => f.name).join(', ');
    setUploadStatus(slotId, 'success', fileNames);

    // FIX #11: Only update dashboard AFTER all files processed
    updateDashboard();

  } catch (err) {
    // FIX #10: Show error with message
    console.error('[Upload]', type, err);
    setUploadStatus(slotId, 'error', err.message);
  } finally {
    // FIX #5: Reset input so same file can be re-uploaded
    input.value = '';
  }
}

/* Process a single CSV file */
async function handleCSVUpload(file, type) {
  const text = await readCSVFile(file);     // FIX #1: ISO-8859-1
  const rows = parseCSV(text, type);        // FIX #2, #3, #4

  switch (type) {
    case 'bestand':
      state.bestandData = processBestandCSV(rows);
      state.flags.bestandLoaded = true;
      break;
    case 'we-ist':
      state.weIstData = processWeIstCSV(rows);
      state.flags.weIstLoaded = true;
      break;
    case 'wa-ist':
      state.waIstData = processWaIstCSV(rows);
      state.flags.waIstLoaded = true;
      break;
  }
}

/* Process a single XLSX file */
async function handleXLSXUpload(file, type) {
  const workbook = await readXLSXFile(file);   // FIX #6: ArrayBuffer
  const rows = getSheetData(workbook);          // FIX #8: sheet selection

  switch (type) {
    case 'we-pipe':
      state.wePipeData = processWePipeXLSX(rows);
      state.flags.weLoaded = true;
      break;
    case 'wa-pipe':
      state.fulfillmentDataMap = processFulfilmentXLSX(rows);
      state.flags.waLoaded = true;
      break;
    case 'auftrag-status':
      state.auftragStatusMap = processAuftragStatusXLSX(rows);
      break;
    case 'planner':
      state.plannerDataMap = processPlannerXLSX(rows);
      break;
  }
}

/* FIX #12: Setup drag-and-drop on all upload slots */
function setupDragAndDrop() {
  document.querySelectorAll('.upload-slot').forEach(slot => {
    const input = slot.querySelector('input[type="file"]');
    if (!input) return;
    const type = input.dataset.type;

    slot.addEventListener('dragover', (e) => {
      e.preventDefault();
      slot.classList.add('dragover');
    });

    slot.addEventListener('dragleave', () => {
      slot.classList.remove('dragover');
    });

    slot.addEventListener('drop', (e) => {
      e.preventDefault();
      slot.classList.remove('dragover');
      if (e.dataTransfer.files.length > 0) {
        // Create a synthetic input-like object
        handleFileUpload({ files: e.dataTransfer.files, value: '', dataset: { type } }, type);
      }
    });
  });
}

/* Bind all upload inputs */
function setupUploadHandlers() {
  document.querySelectorAll('.upload-slot input[type="file"]').forEach(input => {
    const type = input.dataset.type;
    input.addEventListener('change', () => handleFileUpload(input, type));

    // Make the styled button trigger the hidden input
    const btn = input.parentElement.querySelector('.upload-btn');
    if (btn) btn.addEventListener('click', () => input.click());
  });

  // FIX #12: drag-and-drop
  setupDragAndDrop();
}
