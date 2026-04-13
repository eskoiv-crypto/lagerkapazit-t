/* ============================================================
   SILO: Blockierer-Erkennung (Blocker Detection)
   Priority-sorted problem identification
   ============================================================ */

function detectBlockers() {
  if (!state.flags.bestandLoaded) return [];

  const now = today();
  const auftraege = new Map(); // group by Auftragsnummer

  // Group BESTAND items by Auftragsnummer
  for (const item of state.bestandData) {
    if (!item.auftragsnummer) continue;
    if (!auftraege.has(item.auftragsnummer)) {
      auftraege.set(item.auftragsnummer, { items: [], auNr: item.auftragsnummer });
    }
    auftraege.get(item.auftragsnummer).items.push(item);
  }

  const blockerList = [];

  for (const [auNr, auftrag] of auftraege) {
    const fulfillment = state.fulfillmentDataMap.get(auNr) || {};
    const auftragStatus = state.auftragStatusMap.get(auNr) || {};
    const plannerNotiz = state.plannerDataMap.get(auNr) || '';

    const hasQU = auftrag.items.some(i => i.isQU);
    const totalMenge = auftrag.items.reduce((s, i) => s + i.menge, 0);
    const totalPunkte = auftrag.items.reduce((s, i) => s + i.punkte, 0);

    // FIX #15: Parse dates properly
    const versanddatum = parseGermanDate(fulfillment.versanddatum);
    const weDatum = parseGermanDate(auftrag.items[0]?.weDatum);

    // Blocker: QU status + no future valid pickup date
    const hatZukunftTermin = versanddatum && versanddatum >= now;
    const istBlockierer = hasQU && !hatZukunftTermin;

    // Days since WE (how long in warehouse)
    const tageImLager = weDatum ? daysBetween(weDatum, now) : 0;

    // Kritischer Blockierer: blocked >= 3 days
    const istKritischerBlockierer = istBlockierer && tageImLager >= 3;

    // Überfällig: Versanddatum in the past
    const istUeberfaellig = versanddatum && versanddatum < now;
    const tageUeberfaellig = istUeberfaellig ? daysBetween(versanddatum, now) : 0;

    // Planner label present
    const hatPlannerLabel = plannerNotiz.length > 0;

    // "Warte" text in planner
    const istWarteText = plannerNotiz.toLowerCase().includes('warte');

    // Heute fällig
    const istHeuteFaellig = versanddatum && daysBetween(versanddatum, now) === 0;

    // Problemfall criteria
    const istProblemfall =
      istKritischerBlockierer ||
      hatPlannerLabel ||
      (istUeberfaellig && tageUeberfaellig >= 3) ||
      (istWarteText && istBlockierer) ||
      (auftragStatus.status === 'AK' && tageUeberfaellig >= 7);

    // Priority score for sorting
    let prioritaet = 7; // default: fallback
    if (istKritischerBlockierer) prioritaet = 1;
    else if (istProblemfall) prioritaet = 2;
    else if (istBlockierer) prioritaet = 3;
    else if (istUeberfaellig) prioritaet = 4;
    else if (istHeuteFaellig) prioritaet = 5;
    else if (hatZukunftTermin) prioritaet = 6;

    // Only include relevant entries
    if (istBlockierer || istUeberfaellig || istHeuteFaellig || istProblemfall) {
      blockerList.push({
        auNr,
        kunde: fulfillment.kunde || auftragStatus.kunde || '—',
        land: fulfillment.land || auftragStatus.land || '',
        spediteur: fulfillment.spediteur || auftragStatus.spediteur || '',
        status: hasQU ? 'QU' : (auftragStatus.status || '—'),
        versanddatum: fulfillment.versanddatum || '—',
        menge: totalMenge,
        punkte: totalPunkte,
        tageImLager,
        tageUeberfaellig,
        plannerNotiz,
        prioritaet,
        istKritischerBlockierer,
        istBlockierer,
        istUeberfaellig,
        istHeuteFaellig,
        istProblemfall
      });
    }
  }

  // Sort per spec
  blockerList.sort((a, b) => {
    if (a.prioritaet !== b.prioritaet) return a.prioritaet - b.prioritaet;
    // Within same priority: oldest first for blockers, nearest date for planned
    if (a.prioritaet <= 3) return b.tageImLager - a.tageImLager;
    if (a.prioritaet === 6) return a.versanddatum.localeCompare(b.versanddatum);
    return b.menge - a.menge; // fallback: by article count
  });

  state.blockerList = blockerList;
  return blockerList;
}

/* FIX #18: Render blocker table with textContent */
function renderBlockerTable(filter) {
  const tbody = document.querySelector('#blocker-table tbody');
  if (!tbody) return;
  tbody.innerHTML = ''; // safe: clearing, not injecting user data

  let list = state.blockerList || [];

  if (filter && filter !== 'all') {
    switch (filter) {
      case 'kritisch': list = list.filter(b => b.istKritischerBlockierer); break;
      case 'blockierer': list = list.filter(b => b.istBlockierer); break;
      case 'ueberfaellig': list = list.filter(b => b.istUeberfaellig); break;
    }
  }

  if (list.length === 0) {
    const tr = document.createElement('tr');
    const td = document.createElement('td');
    td.colSpan = 7;
    td.textContent = 'Keine Einträge';
    td.style.textAlign = 'center';
    td.style.color = 'var(--text-muted)';
    tr.appendChild(td);
    tbody.appendChild(tr);
    return;
  }

  for (const b of list) {
    const tr = createTableRow([
      b.prioritaet <= 2 ? 'KRITISCH' : (b.prioritaet <= 3 ? 'Blockierer' : (b.istUeberfaellig ? 'Überfällig' : 'Geplant')),
      b.auNr,
      b.kunde,
      b.status,
      b.istBlockierer ? b.tageImLager + ' T.' : (b.istUeberfaellig ? b.tageUeberfaellig + ' T.' : '—'),
      b.menge,
      b.plannerNotiz || b.versanddatum
    ]);

    if (b.prioritaet <= 2) tr.style.background = 'rgba(239,68,68,0.08)';
    else if (b.prioritaet <= 3) tr.style.background = 'rgba(249,115,22,0.06)';
    tbody.appendChild(tr);
  }
}
