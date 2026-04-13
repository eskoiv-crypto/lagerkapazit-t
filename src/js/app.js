/* ============================================================
   SILO: App State & Initialization
   Master controller — wires all silos together
   ============================================================ */

/* Global application state */
const state = {
  bestandData: [],
  weIstData: [],
  waIstData: [],
  wePipeData: [],
  fulfillmentDataMap: new Map(),
  auftragStatusMap: new Map(),
  plannerDataMap: new Map(),
  blockerList: [],
  capacity: null,
  settings: {},

  flags: {
    bestandLoaded: false,
    weLoaded: false,
    waLoaded: false,
    weIstLoaded: false,
    waIstLoaded: false
  }
};

/* Central dashboard refresh — called after any data upload */
function updateDashboard() {
  updateCapacity();
  detectBlockers();
  renderBlockerTable('all');
  renderForecastTable();
  updateChart();
  updateEffizienzTracker();
}

/* Validation runner */
function runValidation() {
  const results = document.getElementById('validation-results');
  if (!results) return;
  results.innerHTML = ''; // safe: clearing

  const checks = [];

  // Check data loaded
  if (!state.flags.bestandLoaded) checks.push({ level: 'error', msg: 'BESTAND CSV nicht geladen' });
  else checks.push({ level: 'ok', msg: 'BESTAND: ' + state.bestandData.length + ' Einträge geladen' });

  if (!state.flags.waLoaded) checks.push({ level: 'warn', msg: 'Fulfilment Pipeline nicht geladen' });
  else checks.push({ level: 'ok', msg: 'Fulfilment Pipeline: ' + state.fulfillmentDataMap.size + ' Aufträge' });

  if (!state.flags.weIstLoaded) checks.push({ level: 'warn', msg: 'WE-IST nicht geladen' });
  if (!state.flags.waIstLoaded) checks.push({ level: 'warn', msg: 'WA-IST nicht geladen' });

  // Cross-reference: BESTAND AU-Nr vs Fulfilment
  if (state.flags.bestandLoaded && state.flags.waLoaded) {
    const bestandAU = new Set(state.bestandData.map(i => i.auftragsnummer).filter(Boolean));
    let missing = 0;
    for (const auNr of bestandAU) {
      if (!state.fulfillmentDataMap.has(auNr)) missing++;
    }
    if (missing > 0) {
      checks.push({ level: 'warn', msg: missing + ' Aufträge in BESTAND ohne Fulfilment-Eintrag' });
    } else {
      checks.push({ level: 'ok', msg: 'Alle BESTAND-Aufträge in Fulfilment gefunden' });
    }
  }

  // Storage usage
  const usage = getStorageUsage();
  const usageMB = (usage / 1024 / 1024).toFixed(2);
  checks.push({ level: usage > 4000000 ? 'warn' : 'ok', msg: 'localStorage: ' + usageMB + ' MB belegt' });

  // FIX #18: Render with textContent
  for (const check of checks) {
    const div = createEl('div', (check.level === 'ok' ? '\u2705 ' : check.level === 'warn' ? '\u26A0\uFE0F ' : '\u274C ') + check.msg, 'validation-' + check.level);
    div.style.padding = '0.3rem 0';
    results.appendChild(div);
  }
}

/* Initialize everything on DOM ready */
function initApp() {
  // Load saved settings
  const saved = safeStorageGet(CONFIG.storageKeys.settings);
  if (saved) {
    state.settings = saved;
    Object.assign(CONFIG.defaults, saved);
  }

  // Set current date
  setText('current-date', formatGermanDate(today()));

  // Init charts
  initCharts();

  // Setup upload handlers (FIX #5, #7, #9, #10, #11, #12)
  setupUploadHandlers();

  // Setup admin panel (FIX #17)
  setupAdminHandlers();

  // Setup blocker filter buttons
  document.querySelectorAll('.filter-bar button').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('.filter-bar button').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      renderBlockerTable(btn.dataset.filter);
    });
  });

  // Validation button
  document.getElementById('btn-validate')?.addEventListener('click', runValidation);

  // Initial gauge with empty state
  updateGauge();
}

// Boot
document.addEventListener('DOMContentLoaded', initApp);
