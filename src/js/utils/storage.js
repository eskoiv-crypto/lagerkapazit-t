/* ============================================================
   SILO: localStorage Utilities
   FIX #16: Quota guard with try/catch + size management
   ============================================================ */

/* Safe localStorage write — catches QuotaExceededError */
function safeStorageSet(key, value) {
  try {
    const json = JSON.stringify(value);
    localStorage.setItem(key, json);
    return true;
  } catch (e) {
    if (e.name === 'QuotaExceededError' || e.code === 22) {
      console.warn('[Storage] Quota exceeded for key:', key);
      // Try to free space by trimming oldest snapshots
      trimSnapshots();
      try {
        localStorage.setItem(key, JSON.stringify(value));
        return true;
      } catch (e2) {
        console.error('[Storage] Still over quota after trim:', e2);
        return false;
      }
    }
    console.error('[Storage] Write failed:', e);
    return false;
  }
}

/* Safe localStorage read — returns null on failure */
function safeStorageGet(key) {
  try {
    const raw = localStorage.getItem(key);
    return raw ? JSON.parse(raw) : null;
  } catch (e) {
    console.error('[Storage] Read failed for key:', key, e);
    return null;
  }
}

/* Remove a key */
function safeStorageRemove(key) {
  try { localStorage.removeItem(key); } catch (e) { /* ignore */ }
}

/* Trim oldest BESTAND snapshots to stay under quota */
function trimSnapshots() {
  const key = 'elvinci_bestand_snapshots';
  const data = safeStorageGet(key);
  if (!data || typeof data !== 'object') return;

  const dates = Object.keys(data).sort();
  // Keep only last 30 days instead of 90 when over quota
  while (dates.length > 30) {
    delete data[dates.shift()];
  }
  try {
    localStorage.setItem(key, JSON.stringify(data));
  } catch (e) { /* last resort: clear snapshots entirely */
    localStorage.removeItem(key);
  }
}

/* Approximate localStorage usage in bytes */
function getStorageUsage() {
  let total = 0;
  for (let i = 0; i < localStorage.length; i++) {
    const key = localStorage.key(i);
    total += key.length + (localStorage.getItem(key) || '').length;
  }
  return total * 2; // UTF-16 = 2 bytes per char
}

/* Clear all dashboard keys */
function clearAllLocalStorage() {
  ['elvinci_dashboard_settings', 'elvinci_effizienz_daily', 'elvinci_bestand_snapshots'].forEach(k => {
    safeStorageRemove(k);
  });
}
