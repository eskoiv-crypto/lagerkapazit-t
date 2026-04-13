/* ============================================================
   SILO: Date Utilities
   FIX #15: Enforce DD.MM.YYYY parsing for German dates
   ============================================================ */

/* Parse German date string "DD.MM.YYYY" → Date object
   Returns null on invalid input instead of Invalid Date */
function parseGermanDate(dateStr) {
  if (!dateStr) return null;
  const str = String(dateStr).trim();

  // Try DD.MM.YYYY
  const dotMatch = str.match(/^(\d{1,2})\.(\d{1,2})\.(\d{4})$/);
  if (dotMatch) {
    const [, day, month, year] = dotMatch;
    const d = new Date(+year, +month - 1, +day);
    if (!isNaN(d.getTime())) return d;
  }

  // Try YYYY-MM-DD (ISO fallback)
  const isoMatch = str.match(/^(\d{4})-(\d{2})-(\d{2})$/);
  if (isoMatch) {
    const [, year, month, day] = isoMatch;
    const d = new Date(+year, +month - 1, +day);
    if (!isNaN(d.getTime())) return d;
  }

  return null;
}

/* Format Date → "DD.MM.YYYY" */
function formatGermanDate(date) {
  if (!date || isNaN(date.getTime())) return '—';
  const dd = String(date.getDate()).padStart(2, '0');
  const mm = String(date.getMonth() + 1).padStart(2, '0');
  return `${dd}.${mm}.${date.getFullYear()}`;
}

/* Days between two dates (ignoring time) */
function daysBetween(a, b) {
  const msPerDay = 86400000;
  const utcA = Date.UTC(a.getFullYear(), a.getMonth(), a.getDate());
  const utcB = Date.UTC(b.getFullYear(), b.getMonth(), b.getDate());
  return Math.floor((utcB - utcA) / msPerDay);
}

/* Get next N workdays from a start date */
function getWorkdays(startDate, count) {
  const days = [];
  const d = new Date(startDate);
  while (days.length < count) {
    d.setDate(d.getDate() + 1);
    const dow = d.getDay();
    if (dow !== 0 && dow !== 6) days.push(new Date(d));
  }
  return days;
}

/* Today at midnight */
function today() {
  const now = new Date();
  return new Date(now.getFullYear(), now.getMonth(), now.getDate());
}
