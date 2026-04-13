/* ============================================================
   SILO: Admin Panel
   FIX #17: Password is a deterrent only (visible in source)
   Settings, maintenance, reset
   ============================================================ */

function openSettingsPanel() {
  show('settings-overlay');
  hide('settings-content');
  show('password-gate');
  const pw = document.getElementById('admin-pw');
  if (pw) { pw.value = ''; pw.focus(); }
}

function closeSettingsPanel() {
  hide('settings-overlay');
}

/* FIX #17: Password check — deterrent, not real security */
function checkAdminPassword() {
  const pw = document.getElementById('admin-pw');
  if (!pw) return;
  if (pw.value === CONFIG.adminPassword) {
    hide('password-gate');
    show('settings-content');
    loadSettingsIntoForm();
  } else {
    pw.style.borderColor = 'var(--red)';
    pw.value = '';
    pw.placeholder = 'Falsches Passwort';
  }
}

/* Load current settings into admin form fields */
function loadSettingsIntoForm() {
  const s = state.settings || CONFIG.defaults;
  const fields = {
    'set-flaeche': s.flaecheQm,
    'set-paletten': s.palettenProQm,
    'set-punkte': s.punkteProPalette,
    'set-regal1': s.regalHalle1,
    'set-regal2': s.regalHalle2,
    'set-qu': s.quKapazitaet
  };
  for (const [id, val] of Object.entries(fields)) {
    const el = document.getElementById(id);
    if (el) el.value = val;
  }
}

/* Save settings from admin form */
function saveAllSettings() {
  state.settings = {
    flaecheQm: parseFloat(document.getElementById('set-flaeche')?.value) || CONFIG.defaults.flaecheQm,
    palettenProQm: parseFloat(document.getElementById('set-paletten')?.value) || CONFIG.defaults.palettenProQm,
    punkteProPalette: parseFloat(document.getElementById('set-punkte')?.value) || CONFIG.defaults.punkteProPalette,
    regalHalle1: parseInt(document.getElementById('set-regal1')?.value) || CONFIG.defaults.regalHalle1,
    regalHalle2: parseInt(document.getElementById('set-regal2')?.value) || CONFIG.defaults.regalHalle2,
    quKapazitaet: parseInt(document.getElementById('set-qu')?.value) || CONFIG.defaults.quKapazitaet
  };

  // Update CONFIG defaults so calculated getters work
  Object.assign(CONFIG.defaults, state.settings);

  // FIX #16: Safe storage
  safeStorageSet(CONFIG.storageKeys.settings, state.settings);

  // Recalculate
  updateDashboard();
  closeSettingsPanel();
}

function resetToDefaults() {
  Object.assign(CONFIG.defaults, {
    flaecheQm: 2766, palettenProQm: 0.565, punkteProPalette: 4,
    regalHalle1: 702, regalHalle2: 828, quKapazitaet: 2350
  });
  state.settings = { ...CONFIG.defaults };
  safeStorageRemove(CONFIG.storageKeys.settings);
  loadSettingsIntoForm();
  updateDashboard();
}

function setupAdminHandlers() {
  document.getElementById('btn-settings')?.addEventListener('click', openSettingsPanel);
  document.getElementById('btn-pw-submit')?.addEventListener('click', checkAdminPassword);
  document.getElementById('admin-pw')?.addEventListener('keydown', (e) => { if (e.key === 'Enter') checkAdminPassword(); });
  document.getElementById('btn-save-settings')?.addEventListener('click', saveAllSettings);
  document.getElementById('btn-reset-defaults')?.addEventListener('click', resetToDefaults);
  document.getElementById('btn-clear-storage')?.addEventListener('click', () => {
    if (confirm('Alle lokalen Daten löschen?')) { clearAllLocalStorage(); location.reload(); }
  });
  document.getElementById('btn-close-settings')?.addEventListener('click', closeSettingsPanel);
  document.getElementById('settings-overlay')?.addEventListener('click', (e) => {
    if (e.target.id === 'settings-overlay') closeSettingsPanel();
  });
}
