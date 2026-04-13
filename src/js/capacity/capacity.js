/* ============================================================
   SILO: Capacity Calculation Engine
   Unit: PUNKTE (not devices!)
   ============================================================ */

function updateCapacity() {
  if (!state.flags.bestandLoaded) return;

  const data = state.bestandData;
  let lager = 0, versand = 0, weZone = 0, quPunkte = 0;
  let totalGeraete = 0, quGeraete = 0;

  for (const item of data) {
    totalGeraete += item.menge;
    switch (item.zone) {
      case 'lager':   lager += item.punkte; break;
      case 'versand': versand += item.punkte; break;
      case 'we-zone': weZone += item.punkte; break;
    }
    if (item.isQU) {
      quPunkte += item.punkte;
      quGeraete += item.menge;
    }
  }

  state.capacity = {
    lager, versand, weZone, quPunkte,
    totalPunkte: lager + versand + weZone,
    totalGeraete, quGeraete
  };

  updateStats();
  updateGauge();
  updateQUDisplay();

  // Save daily snapshot — FIX #16: safe write
  const dateKey = formatGermanDate(today());
  const snapshots = safeStorageGet(CONFIG.storageKeys.snapshots) || {};
  snapshots[dateKey] = {
    lager, versand, weZone, quPunkte,
    total: lager + versand + weZone,
    geraete: totalGeraete,
    timestamp: Date.now()
  };
  safeStorageSet(CONFIG.storageKeys.snapshots, snapshots);
}

/* FIX #18: Update stat cards using textContent */
function updateStats() {
  const cap = state.capacity;
  const calc = CONFIG.calculated;

  setText('val-lager', cap.lager.toLocaleString('de-DE'));
  setText('val-versand', cap.versand.toLocaleString('de-DE'));
  setText('val-we', cap.weZone.toLocaleString('de-DE'));
  setText('val-qu', cap.quPunkte.toLocaleString('de-DE'));
  setText('val-geraete', cap.totalGeraete.toLocaleString('de-DE'));
  setText('val-kapazitaet', calc.lagerKapazitaet.toLocaleString('de-DE'));
}

function updateQUDisplay() {
  const cap = state.capacity;
  const quMax = CONFIG.defaults.quKapazitaet;
  const pct = quMax > 0 ? Math.round((cap.quPunkte / quMax) * 100) : 0;
  setText('val-qu-pct', pct + '%');
}

function updateGauge() {
  const cap = state.capacity;
  const calc = CONFIG.calculated;
  const used = cap.lager;
  const max = calc.lagerKapazitaet;
  const pct = max > 0 ? Math.round((used / max) * 100) : 0;

  // Color based on utilization
  let color = 'var(--green)';
  if (pct >= 95) color = 'var(--red)';
  else if (pct >= 85) color = '#f97316';
  else if (pct >= 70) color = 'var(--yellow)';

  setText('gauge-pct', pct + '%');
  setText('gauge-detail', used.toLocaleString('de-DE') + ' / ' + max.toLocaleString('de-DE') + ' Punkte');

  // Update Chart.js gauge if available
  if (window.gaugeChart) {
    window.gaugeChart.data.datasets[0].data = [used, Math.max(0, max - used)];
    window.gaugeChart.data.datasets[0].backgroundColor = [color, '#e5e7eb'];
    window.gaugeChart.update();
  }
}
