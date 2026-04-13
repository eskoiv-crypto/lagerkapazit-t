/* ============================================================
   SILO: Configuration & Defaults
   All tuneable parameters in one place
   ============================================================ */

const CONFIG = {
  // Capacity defaults
  defaults: {
    flaecheQm: 2766,
    palettenProQm: 0.565,
    punkteProPalette: 4,
    regalHalle1: 702,
    regalHalle2: 828,
    quKapazitaet: 2350
  },

  // Calculated capacity (derived from defaults)
  get calculated() {
    const d = this.defaults;
    const bodenKapazitaet = Math.round(d.flaecheQm * d.palettenProQm * d.punkteProPalette);
    const regalKapazitaet = d.regalHalle1 + d.regalHalle2;
    const lagerKapazitaet = bodenKapazitaet + regalKapazitaet;
    const gesamtNH5 = lagerKapazitaet + d.quKapazitaet;
    return { bodenKapazitaet, regalKapazitaet, lagerKapazitaet, gesamtNH5 };
  },

  // Effizienz
  effizienzZiel: 470,
  effizienzHistorieTage: 90,

  // localStorage keys
  storageKeys: {
    settings: 'elvinci_dashboard_settings',
    effizienz: 'elvinci_effizienz_daily',
    snapshots: 'elvinci_bestand_snapshots'
  },

  // Admin
  adminPassword: 'elvinci'
};
