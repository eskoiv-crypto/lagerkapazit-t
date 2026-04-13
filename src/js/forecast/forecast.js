/* ============================================================
   SILO: Forecast Engine
   5-workday capacity projection
   ============================================================ */

function renderForecastTable() {
  const table = document.getElementById('forecast-table');
  if (!table) return;
  table.innerHTML = ''; // safe: no user data in structure

  const thead = document.createElement('thead');
  thead.appendChild(createTableRow(['Tag', 'Datum', 'WE (Prognose)', 'WA (Prognose)', 'Bestand (Prognose)', 'Auslastung'], true));
  table.appendChild(thead);

  const tbody = document.createElement('tbody');
  const days = getWorkdays(today(), 5);
  const calc = CONFIG.calculated;
  let currentBestand = state.capacity ? state.capacity.lager : 0;

  // Estimate daily WE/WA from pipeline data or historical average
  const avgWE = getAverageDaily('we');
  const avgWA = getAverageDaily('wa');

  for (const day of days) {
    const prognoseWE = avgWE;
    const prognoseWA = avgWA;
    currentBestand = currentBestand + prognoseWE - prognoseWA;
    if (currentBestand < 0) currentBestand = 0;

    const auslastung = calc.lagerKapazitaet > 0
      ? Math.round((currentBestand / calc.lagerKapazitaet) * 100)
      : 0;

    const row = createTableRow([
      ['Mo','Di','Mi','Do','Fr','Sa','So'][day.getDay() - 1] || '?',
      formatGermanDate(day),
      prognoseWE.toLocaleString('de-DE'),
      prognoseWA.toLocaleString('de-DE'),
      currentBestand.toLocaleString('de-DE'),
      auslastung + '%'
    ]);
    tbody.appendChild(row);
  }
  table.appendChild(tbody);
}

/* Get average daily WE or WA from efficiency history */
function getAverageDaily(type) {
  const history = safeStorageGet(CONFIG.storageKeys.effizienz) || {};
  const values = Object.values(history).map(d => d[type] || 0).filter(v => v > 0);
  if (values.length === 0) return type === 'we' ? 150 : 200; // sensible defaults
  return Math.round(values.reduce((a, b) => a + b, 0) / values.length);
}

function updateChart() {
  if (!window.forecastChart) return;

  const days = getWorkdays(today(), 5);
  const calc = CONFIG.calculated;
  let currentBestand = state.capacity ? state.capacity.lager : 0;
  const avgWE = getAverageDaily('we');
  const avgWA = getAverageDaily('wa');

  const labels = days.map(d => formatGermanDate(d));
  const dataPoints = [];
  const capacityLine = [];

  for (const day of days) {
    currentBestand = currentBestand + avgWE - avgWA;
    if (currentBestand < 0) currentBestand = 0;
    dataPoints.push(currentBestand);
    capacityLine.push(calc.lagerKapazitaet);
  }

  window.forecastChart.data.labels = labels;
  window.forecastChart.data.datasets[0].data = dataPoints;
  window.forecastChart.data.datasets[1].data = capacityLine;
  window.forecastChart.update();
}
