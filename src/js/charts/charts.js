/* ============================================================
   SILO: Chart.js Initialization
   Gauge, Forecast, Effizienz charts
   ============================================================ */

function initCharts() {
  initGaugeChart();
  initForecastChart();
  initEffizienzChart();
}

/* Half-doughnut gauge for capacity */
function initGaugeChart() {
  const ctx = document.getElementById('gauge-canvas');
  if (!ctx) return;

  const calc = CONFIG.calculated;
  window.gaugeChart = new Chart(ctx, {
    type: 'doughnut',
    data: {
      datasets: [{
        data: [0, calc.lagerKapazitaet],
        backgroundColor: ['var(--green)', '#e5e7eb'],
        borderWidth: 0
      }]
    },
    options: {
      rotation: -90,
      circumference: 180,
      cutout: '75%',
      responsive: true,
      maintainAspectRatio: true,
      plugins: {
        legend: { display: false },
        tooltip: { enabled: false }
      }
    }
  });
}

/* Line chart for 5-day forecast */
function initForecastChart() {
  const ctx = document.getElementById('forecast-chart');
  if (!ctx) return;

  window.forecastChart = new Chart(ctx, {
    type: 'line',
    data: {
      labels: [],
      datasets: [
        {
          label: 'Bestand (Prognose)',
          data: [],
          borderColor: '#3b82f6',
          backgroundColor: 'rgba(59,130,246,0.1)',
          fill: true,
          tension: 0.3
        },
        {
          label: 'Kapazitätsgrenze',
          data: [],
          borderColor: '#ef4444',
          borderDash: [5, 5],
          pointRadius: 0,
          fill: false
        }
      ]
    },
    options: {
      responsive: true,
      plugins: {
        legend: { position: 'bottom' }
      },
      scales: {
        y: { beginAtZero: true, title: { display: true, text: 'Punkte' } }
      }
    }
  });
}

/* Stacked bar chart for daily WE/WA */
function initEffizienzChart() {
  const ctx = document.getElementById('effizienz-chart');
  if (!ctx) return;

  window.effizienzChart = new Chart(ctx, {
    type: 'bar',
    data: {
      labels: [],
      datasets: [
        {
          label: 'WE (Wareneingang)',
          data: [],
          backgroundColor: '#3b82f6'
        },
        {
          label: 'WA (Warenausgang)',
          data: [],
          backgroundColor: '#f97316'
        }
      ]
    },
    options: {
      responsive: true,
      plugins: {
        legend: { position: 'bottom' }
      },
      scales: {
        x: { stacked: true },
        y: {
          stacked: true,
          beginAtZero: true,
          title: { display: true, text: 'Geräte' }
        }
      }
    }
  });
}
