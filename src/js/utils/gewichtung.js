/* ============================================================
   SILO: Gewichtungsfaktoren (Weighting Factors)
   Faktor = how much pallet space a device occupies (in PUNKTE)
   ============================================================ */

const GEWICHTUNG_MAP = [
  { faktor: 4.0, typen: ['side-by-side kühlschrank', 'gefriertruhe', 'freistehender gefrierschrank'] },
  { faktor: 2.0, typen: ['kühlschrank', 'kühl-/gefrierkombination', 'kühl-gefrierkombination', 'einbaukühlschrank', 'fernseher'] },
  { faktor: 1.0, typen: ['waschmaschine', 'trockner', 'geschirrspüler', 'backofen', 'herd', 'dunstabzugshaube', 'klimagerät', 'weinkühlschrank'] },
  { faktor: 0.8, typen: ['luftreiniger'] },
  { faktor: 0.5, typen: ['set-artikel'] },
  { faktor: 0.4, typen: ['mikrowelle', 'staubsauger', 'saugroboter', 'kaffeevollautomat'] },
  { faktor: 0.2, typen: ['kochfeld', 'monitor'] }
];

/* FIX #13: Case-insensitive, includes()-based matching
   Normalizes Bezeichner to lowercase and checks via includes()
   so "Kühl-Gefrierkombination" matches "kühl-gefrierkombination" */
function getGewichtung(bezeichner) {
  if (!bezeichner) return 1.0;
  const norm = bezeichner.toLowerCase().trim();

  for (const entry of GEWICHTUNG_MAP) {
    for (const typ of entry.typen) {
      if (norm.includes(typ)) return entry.faktor;
    }
  }
  return 1.0; // default fallback
}

/* FIX #14: Set-Artikel logic with explicit fallback chain
   Artikelnummer ending determines factor:
   .001 = Hauptgerät (Herd) = 1.0
   .002 = Zubehör (Kochfeld) = 0.2
   .003+ = Weiteres Zubehör = 0.2
   no dot = use Bezeichner-based lookup (default) */
function getSetArtikelFaktor(artikelNr) {
  if (!artikelNr) return null; // no override, use Bezeichner
  const str = String(artikelNr).trim();
  const dotIdx = str.lastIndexOf('.');
  if (dotIdx === -1) return null; // no dot, no set-artikel

  const suffix = str.substring(dotIdx + 1);
  if (suffix === '001') return 1.0;
  if (suffix === '002') return 0.2;
  // .003, .004, ... = further accessories
  if (/^\d{3,}$/.test(suffix) && parseInt(suffix) > 2) return 0.2;
  return null; // not a set-artikel pattern
}
