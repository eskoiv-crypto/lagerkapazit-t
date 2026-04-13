/* ============================================================
   SILO: Effizienz-Tracker
   Daily throughput: WE + WA devices
   Target: 470/day | History: 90 days
   ============================================================ */

/* Save daily efficiency data */
function saveEffizienzTag(datum, we, wa) {
  const history = safeStorageGet(CONFIG.storageKeys.effizienz) || {};
  const dateKey = typeof datum === 'string' ? datum : formatGermanDate(datum);

  history[dateKey] = {
    we: we,
    wa: wa,
    total: we + wa
  };

  // Trim to 90 days
  const keys = Object.keys(history).sort();
  while (keys.length > CONFIG.effizienzHistorieTage) {
    delete history[keys.shift()];
  }

  safeStorageSet(CONFIG.storageKeys.effizienz, history); // FIX #16
}

/* Load efficiency history */
function loadEffizienzHistorie() {
  return safeStorageGet(CONFIG.storageKeys.effizienz) || {};
}

/* Update efficiency display from current uploads */
function updateEffizienzTracker() {
  const todayStr = formatGermanDate(today());
  let weCount = 0;
  let waCount = 0;

  // Count from WE-IST
  if (state.flags.weIstLoaded) {
    weCount = state.weIstData.reduce((sum, item) => sum + item.menge, 0);
  }

  // Count from WA-IST
  if (state.flags.waIstLoaded) {
    waCount = state.waIstData.reduce((sum, item) => sum + item.menge, 0);
  }

  // Save today's data
  if (weCount > 0 || waCount > 0) {
    saveEffizienzTag(todayStr, weCount, waCount);
  }

  const total = weCount + waCount;
  const ziel = CONFIG.effizienzZiel;
  const pct = ziel > 0 ? Math.round((total / ziel) * 100) : 0;

  // FIX #18: textContent only
  setText('eff-we', weCount.toLocaleString('de-DE'));
  setText('eff-wa', waCount.toLocaleString('de-DE'));
  setText('eff-total', total.toLocaleString('de-DE'));
  setText('eff-pct', pct + '%');

  // Update chart
  updateEffizienzChart();
}

/* Update efficiency bar chart */
function updateEffizienzChart() {
  if (!window.effizienzChart) return;

  const history = loadEffizienzHistorie();
  const dates = Object.keys(history).sort().slice(-14); // last 14 days

  const labels = dates;
  const weData = dates.map(d => history[d].we || 0);
  const waData = dates.map(d => history[d].wa || 0);

  window.effizienzChart.data.labels = labels;
  window.effizienzChart.data.datasets[0].data = weData;
  window.effizienzChart.data.datasets[1].data = waData;
  window.effizienzChart.update();
}
