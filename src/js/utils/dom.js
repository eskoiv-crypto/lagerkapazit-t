/* ============================================================
   SILO: Safe DOM Utilities
   FIX #18: Always use textContent, never innerHTML for user data
   ============================================================ */

/* Create element with text content (safe from XSS) */
function createEl(tag, text, className) {
  const el = document.createElement(tag);
  if (text !== undefined && text !== null) el.textContent = String(text);
  if (className) el.className = className;
  return el;
}

/* Create a table row from array of cell values (all textContent) */
function createTableRow(cells, isHeader) {
  const tr = document.createElement('tr');
  cells.forEach(cellValue => {
    const cell = document.createElement(isHeader ? 'th' : 'td');
    cell.textContent = cellValue !== undefined && cellValue !== null ? String(cellValue) : '—';
    tr.appendChild(cell);
  });
  return tr;
}

/* Safely set text on an element by ID */
function setText(id, text) {
  const el = document.getElementById(id);
  if (el) el.textContent = String(text);
}

/* Show/hide element */
function show(el) { if (typeof el === 'string') el = document.getElementById(el); if (el) el.classList.remove('hidden'); }
function hide(el) { if (typeof el === 'string') el = document.getElementById(el); if (el) el.classList.add('hidden'); }

/* Set upload status indicator — FIX #10 */
function setUploadStatus(slotId, status, message) {
  const slot = document.getElementById(slotId);
  if (!slot) return;
  const statusEl = slot.querySelector('.upload-status');
  if (!statusEl) return;

  statusEl.className = 'upload-status ' + status;
  const icons = { loading: '\u23F3', success: '\u2705', error: '\u274C' };
  statusEl.textContent = (icons[status] || '') + ' ' + (message || '');
}
