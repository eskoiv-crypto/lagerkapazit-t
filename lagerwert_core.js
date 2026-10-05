/*
 * Lagerwert-Rechner — Rechenkern (reine Logik, ohne DOM).
 *
 * 1:1-Nachbau von warenwert_stichtag.py (Rechenweg der Monatsreihe
 * "Warenwert zum Monatsende") und warenwert_pdf.py (Einseiter, Darstellung
 * "belegt"). Läuft im Browser (lagerwert_tool.html) und in Node
 * (tests/test_lagerwert_core.js). Keine Abhängigkeiten außer SheetJS (xlsx)
 * zum Lesen des Odoo-Exports und jsPDF für den Einseiter; beide werden von
 * außen übergeben.
 *
 * Definition (intern festgelegt 13./14.08.2026):
 *   Warenwert(S) = Σ Einkaufspreis aller Geräte, die am Stichtag S physisch
 *                  im Lager NH5 lagen – Status QE + VS + AA.
 *   Mengengerüst  = AMM-Bestandsliste BESTAND134 vom Stichtag
 *   Preis         = Einkaufspreis je Lager-Nr aus Odoo (stock.lot)
 *   Korrekturen   = Korrekturliste Lager-Nr;EK;Grund (ersetzt Odoo + Ø-Fill)
 *   fehlender EK  = Ø-EK Produktkategorie > Marke > Bezeichner > global
 *   Schrott       = echter EK 0 (Regex 'schrott'), kein Ø-Fill
 */
(function (root, factory) {
  if (typeof module === "object" && module.exports) module.exports = factory();
  else root.LagerwertCore = factory();
})(typeof self !== "undefined" ? self : this, function () {
  "use strict";

  var VERSION = "1.1 (05.10.2026)";
  var UMFANG_STATUS = ["QE", "VS", "AA"];

  var ODOO_SPALTEN = {
    lagernr: ["Lager-Code", "Lager Nr.", "Lager-Nr.", "Lagernummer"],
    los: ["Los-/Seriennummer", "Los/Seriennummer", "Name"],
    produkt: ["Produkt", "Artikel"],
    kategorie: ["Produktkategorie", "Produktgruppe", "Warengruppe"],
    marke: ["Marke", "Brand"],
    lieferant: ["Lieferant"],
    liefertyp: ["Lieferantentyp"],
    ek: ["Einkaufspreis", "EK"]
  };
  var KORREKTUR_SPALTEN = {
    lagernr: ["Lager-Nr", "Lager-Nr.", "Lager Nr.", "Lager-Code", "Lagernummer", "lagernr"],
    ek: ["EK", "Einkaufspreis", "EK neu", "EK_neu"],
    grund: ["Grund", "Kommentar", "Bemerkung", "Quelle"],
    ref: ["EK Odoo bei Korrektur", "EK_Odoo_bei_Korrektur"]
  };
  var AEG_GRUND = "AEG Electrolux: Einkaufspreis, vorher EK 0 im System";

  // AEG-Electrolux-Ware wie im September 2026 erkannt (identisch zu ist_aeg()
  // in warenwert_stichtag.py): Odoo-Lieferant/-typ AEG/Electrolux, AMM-
  // Bestellnummer mit 'AEG', oder 'Migration Altbestand' mit AEG im Produkt.
  function istAeg(lieferant, liefertyp, produkt, bestellnr) {
    if (/electrolux|aeg/i.test(lieferant + " " + liefertyp) || /aeg/i.test(bestellnr || "")) return true;
    return String(lieferant).trim().toLowerCase() === "migration altbestand" && /electrolux|aeg/i.test(produkt || "");
  }

  // ------------------------------------------------------------ Hilfen
  function lagernr(v) {
    var s = String(v === null || v === undefined ? "" : v).trim();
    if (s.slice(-2) === ".0") s = s.slice(0, -2);
    return s;
  }

  // Entspricht zu_zahl(): deutsche und englische Schreibweisen, sonst 0
  function zuZahl(v) {
    if (v === null || v === undefined) return 0;
    if (typeof v === "number") return isNaN(v) ? 0 : v;
    var s = String(v).trim().replace(/€/g, "").replace(/ /g, "").replace(/ /g, "");
    if (!s || s === "-" || s === "—" || s === "nan" || s === "None") return 0;
    if (s.indexOf(",") >= 0 && s.indexOf(".") >= 0) s = s.replace(/\./g, "").replace(",", ".");
    else if (s.indexOf(",") >= 0) s = s.replace(",", ".");
    if (!/^[-+]?(\d+\.?\d*|\.\d+)([eE][-+]?\d+)?$/.test(s)) return 0;
    var f = parseFloat(s);
    return isNaN(f) ? 0 : f;
  }

  // Python f"{x:,.0f}": kaufmännisch-gerade Rundung (round half to even)
  function rund0(x) {
    var neg = x < 0; x = Math.abs(x);
    var f = Math.floor(x), d = x - f, r;
    if (d > 0.5) r = f + 1; else if (d < 0.5) r = f; else r = (f % 2 === 0) ? f : f + 1;
    return neg ? -r : r;
  }
  function tausender(n) {
    var s = String(Math.abs(n)), out = "";
    while (s.length > 3) { out = "." + s.slice(-3) + out; s = s.slice(0, -3); }
    return (n < 0 ? "-" : "") + s + out;
  }
  function eur(x) { return tausender(rund0(x)) + " €"; }
  function de(n) { return tausender(Math.trunc(n)); }
  function sortedStatus(obj) {
    return Object.keys(obj).sort().map(function (k) { return k + " " + de(obj[k]); }).join(", ");
  }

  // Minimaler CSV-Parser (Semikolon/Komma, Anführungszeichen), wie csv.reader
  function csvZeilen(text, sep) {
    var rows = [], row = [], cell = "", q = false, i, c;
    for (i = 0; i < text.length; i++) {
      c = text[i];
      if (q) {
        if (c === '"') { if (text[i + 1] === '"') { cell += '"'; i++; } else q = false; }
        else cell += c;
      } else if (c === '"') q = true;
      else if (c === sep) { row.push(cell); cell = ""; }
      else if (c === "\n" || c === "\r") {
        if (c === "\r" && text[i + 1] === "\n") i++;
        row.push(cell); rows.push(row); row = []; cell = "";
      } else cell += c;
    }
    if (cell !== "" || row.length) { row.push(cell); rows.push(row); }
    return rows;
  }

  function findeSpalte(header, aliase) {
    var norm = {}, i, k, n;
    for (i = 0; i < header.length; i++) {
      n = String(header[i] === undefined ? "" : header[i]).trim().toLowerCase();
      if (!(n in norm)) norm[n] = i;           // erste Spalte gewinnt (wie dict)
    }
    for (i = 0; i < aliase.length; i++) {
      k = aliase[i].trim().toLowerCase();
      if (k in norm) return norm[k];
    }
    for (i = 0; i < aliase.length; i++) {
      k = aliase[i].trim().toLowerCase();
      for (n in norm) if (k && n.indexOf(k) >= 0) return norm[n];
    }
    return null;
  }

  // ------------------------------------------------------------ BESTAND134
  // text = Inhalt der CSV, bereits als ISO-8859-1 dekodiert
  function parseBestand(text) {
    var rows = csvZeilen(text, ";"), out = [], r, i, status, nr, pal;
    for (i = 0; i < rows.length; i++) {
      r = rows[i];
      if (!r || r.length < 10) continue;
      status = String(r[9] === undefined ? "" : r[9]).trim();
      if (status.toLowerCase() === "status") continue;      // Kopfzeile
      nr = lagernr(r[3]); pal = lagernr(r[0]);
      if (!/^\d{6,}$/.test(nr)) nr = pal;                   // Sammelpalette
      out.push({
        lagernr: nr, palette: pal,
        bezeichner: String(r[2] === undefined ? "" : r[2]).trim(),
        menge: Math.trunc(zuZahl(r[6]) || 1),
        we: String(r[7] === undefined ? "" : r[7]).trim(),
        bestellnr: String(r[8] === undefined ? "" : r[8]).trim(),
        status: status.toUpperCase()
      });
    }
    if (!out.length) throw new Error("Die Bestandsliste enthält keine auswertbaren Zeilen.");
    return out;
  }

  function stichtagAusDateiname(name) {
    var m = /(\d{8})/.exec(name || "");
    if (!m) return null;
    var y = m[1].slice(0, 4), mo = m[1].slice(4, 6), d = m[1].slice(6, 8);
    var dt = new Date(Date.UTC(+y, +mo - 1, +d));
    if (isNaN(dt.getTime()) || dt.getUTCMonth() !== +mo - 1) return null;
    return y + "-" + mo + "-" + d;
  }

  // ------------------------------------------------------------ Datenordner
  // Wählt aus einer Dateiliste (Ordner-Auswahl im Browser) die Eingaben für
  // einen Stichtag. liste: [{name, pfad, lastModified}], stichtag: JJJJ-MM-TT.
  //   Bestand:  BESTAND134_JJJJMMTT_HHMM.CSV vom Stichtag (bei mehreren die spätere Uhrzeit)
  //   Odoo:     LosSerie (stock.lot)*.xlsx – der erste Export am/nach dem Stichtag,
  //             sonst der jüngste davor (mit Warnung). Datum aus dem Namen, sonst Änderungsdatum.
  //   Korrektur: korrekturen_JJJJ-MM-TT*.csv|xlsx – die jüngste mit Datum <= Stichtag
  //   Reihe:    warenwert_monatsende*.csv – bei mehreren die zuletzt geänderte
  function isoAusMs(ms) {
    var d = new Date(ms);
    return d.getFullYear() + "-" + ("0" + (d.getMonth() + 1)).slice(-2) + "-" + ("0" + d.getDate()).slice(-2);
  }
  function gueltigIso(y, m, d) {
    var dt = new Date(Date.UTC(+y, +m - 1, +d));
    return (!isNaN(dt.getTime()) && dt.getUTCMonth() === +m - 1 && dt.getUTCDate() === +d) ? y + "-" + m + "-" + d : null;
  }
  function datumImNamen(name) {
    var m;
    if ((m = /(\d{4})-(\d{2})-(\d{2})/.exec(name))) return gueltigIso(m[1], m[2], m[3]);
    if ((m = /(\d{2})\.(\d{2})\.(\d{4})/.exec(name))) return gueltigIso(m[3], m[2], m[1]);
    if ((m = /(\d{4})(\d{2})(\d{2})/.exec(name))) return gueltigIso(m[1], m[2], m[3]);
    return null;
  }
  function istMonatsende(iso) {
    var d = new Date(Date.UTC(+iso.slice(0, 4), +iso.slice(5, 7) - 1, +iso.slice(8, 10) + 1));
    return d.getUTCDate() === 1;
  }
  function letzterMonatsletzter(heuteIso) {
    var d = new Date(Date.UTC(+heuteIso.slice(0, 4), +heuteIso.slice(5, 7) - 1, 0));
    return d.toISOString().slice(0, 10);
  }
  function waehleDateien(liste, stichtag, opts) {
    opts = opts || {};
    var out = { bestand: null, odoo: null, korr: null, serie: null, fehler: [], hinweise: [], abweichung: false };
    var best = [], odoo = [], korr = [], serie = [];
    (liste || []).forEach(function (f) {
      var n = f.name || "";
      if (/^[~.]/.test(n)) return;                       // Excel-Sperrdateien, versteckte Dateien
      var m;
      if ((m = /^BESTAND\d*_(\d{8})(?:_(\d{4}))?.*\.csv$/i.exec(n))) {
        var t = stichtagAusDateiname(m[1]); if (t) best.push({ f: f, tag: t, zeit: m[2] || "0000" });
      } else if (/^LosSerie|stock\.lot/i.test(n) && /\.xlsx?$/i.test(n)) {
        var od = datumImNamen(n.replace(/stock\.lot/i, "")), quelle = "Dateiname";
        if (!od && f.lastModified) { od = isoAusMs(f.lastModified); quelle = "Änderungsdatum"; }
        if (od) odoo.push({ f: f, tag: od, quelle: quelle });
      } else if ((m = /^korrekturen_(\d{4})-(\d{2})-(\d{2}).*\.(csv|xlsx)$/i.exec(n))) {
        var kt = gueltigIso(m[1], m[2], m[3]); if (kt) korr.push({ f: f, tag: kt });
      } else if (/^warenwert_monatsende.*\.csv$/i.test(n)) {
        serie.push({ f: f });
      }
    });
    function neuer(a, b) { return (b.f.lastModified || 0) - (a.f.lastModified || 0); }

    // Bestand
    var exakt = best.filter(function (b) { return b.tag === stichtag; })
      .sort(function (a, b) { return a.zeit < b.zeit ? 1 : a.zeit > b.zeit ? -1 : neuer(a, b); });
    if (exakt.length) {
      out.bestand = exakt[0].f;
      if (exakt.length > 1) out.hinweise.push("Mehrere Bestandslisten vom " + tagDE(stichtag) + ": verwendet wird die spätere (" + exakt[0].f.name + ").");
    } else {
      var davor = best.filter(function (b) { return b.tag < stichtag; }).sort(function (a, b) { return a.tag < b.tag ? 1 : a.tag > b.tag ? -1 : (a.zeit < b.zeit ? 1 : -1); });
      var tage = best.map(function (b) { return b.tag; }).filter(function (t, i, a) { return a.indexOf(t) === i; }).sort();
      if (opts.erlaubeAbweichung && davor.length) {
        out.bestand = davor[0].f; out.abweichung = true;
        out.hinweise.push("Keine Bestandsliste vom " + tagDE(stichtag) + ". Verwendet wird die letzte davor: " + davor[0].f.name + " (bewusst bestätigt).");
      } else {
        out.fehler.push("Im Ordner liegt keine AMM-Bestandsliste vom " + tagDE(stichtag) +
          " (BESTAND134_" + stichtag.replace(/-/g, "") + "_HHMM.CSV)." +
          (tage.length ? " Vorhanden: " + tage.map(tagDE).join(", ") + "." : " Es wurde gar keine Bestandsliste gefunden."));
      }
    }

    // Odoo
    var nach = odoo.filter(function (o) { return o.tag >= stichtag; }).sort(function (a, b) { return a.tag < b.tag ? -1 : a.tag > b.tag ? 1 : neuer(a, b); });
    var vor = odoo.filter(function (o) { return o.tag < stichtag; }).sort(function (a, b) { return a.tag < b.tag ? 1 : a.tag > b.tag ? -1 : neuer(a, b); });
    if (nach.length) out.odoo = nach[0].f;
    else if (vor.length) {
      out.odoo = vor[0].f;
      out.hinweise.push("Kein Odoo-Export vom " + tagDE(stichtag) + " oder später. Verwendet wird der Export vom " + tagDE(vor[0].tag) +
        ". Geräte, die danach eingegangen sind, haben dort noch keinen Einkaufspreis.");
    } else out.fehler.push("Im Ordner liegt kein Odoo-Export „LosSerie (stock.lot)…xlsx“.");
    var oSel = nach.length ? nach[0] : (vor.length ? vor[0] : null);
    if (oSel && oSel.quelle === "Änderungsdatum")
      out.hinweise.push("Datum des Odoo-Exports " + oSel.f.name + " aus dem Änderungsdatum der Datei (" + tagDE(oSel.tag) + "). Besser das Datum in den Dateinamen schreiben: LosSerie (stock.lot)_JJJJ-MM-TT.xlsx.");

    // Korrekturliste
    var k = korr.filter(function (x) { return x.tag <= stichtag; }).sort(function (a, b) { return a.tag < b.tag ? 1 : a.tag > b.tag ? -1 : neuer(a, b); });
    if (k.length) {
      out.korr = k[0].f;
      if (k.length > 1 && k[1].tag === k[0].tag) out.hinweise.push("Mehrere Korrekturlisten vom " + tagDE(k[0].tag) + ": verwendet wird die zuletzt geänderte (" + k[0].f.name + ").");
    } else out.hinweise.push("Keine Korrekturliste vom " + tagDE(stichtag) + " oder früher gefunden. Gerechnet wird nur mit Odoo-Preisen" + (korr.length ? "." : " (im Ordner liegt keine korrekturen_…csv)."));

    // Monatsreihe
    if (serie.length) {
      serie.sort(neuer); out.serie = serie[0].f;
      if (serie.length > 1) out.hinweise.push("Mehrere Monatsreihen im Ordner: verwendet wird die zuletzt geänderte (" + (serie[0].f.pfad || serie[0].f.name) + ").");
    } else out.hinweise.push("Keine Monatsreihe warenwert_monatsende.csv im Ordner. Der Einseiter zeigt dann nur diesen Stichtag.");
    return out;
  }

  // ------------------------------------------------------------ Odoo
  // sheetRows = Array of Arrays (SheetJS sheet_to_json({header:1, defval:null}))
  function parseOdoo(sheetRows) {
    if (!sheetRows || sheetRows.length < 2) throw new Error("Der Odoo-Export ist leer.");
    var header = sheetRows[0], col = {}, k;
    for (k in ODOO_SPALTEN) col[k] = findeSpalte(header, ODOO_SPALTEN[k]);
    if (col.lagernr === null || col.ek === null) {
      throw new Error("Im Odoo-Export fehlt die Spalte 'Lager-Code' oder 'Einkaufspreis'. " +
        "Bitte den LosSerie-Export MIT Einkaufspreis verwenden. Gefunden: " +
        header.slice(0, 12).join(", ") + " …");
    }
    var ek = {}, kat = {}, marke = {}, schrott = {}, info = {}, zeilen = 0;
    // pandas: str(NaN) == 'nan' und bool(NaN) == True  ->  fehlende Werte
    // werden als Text 'nan' geführt. Das wird hier bewusst nachgebildet,
    // damit die Ø-Gruppen identisch zum Python-Skript ausfallen.
    function txt(v) { return (v === null || v === undefined) ? "nan" : String(v); }
    function istLeer(v) { return v === null || v === undefined || String(v).trim() === ""; }
    for (var i = 1; i < sheetRows.length; i++) {
      var r = sheetRows[i]; if (!r) continue;
      if (col.los !== null) {
        var los = istLeer(r[col.los]) ? "nan" : String(r[col.los]).trim();
        if (/^.*\(\d+\)$/.test(los) || los === "" || los === "nan" || los === "None") continue;
      }
      zeilen++;
      var nr = lagernr(istLeer(r[col.lagernr]) ? "nan" : r[col.lagernr]);
      if (!nr) continue;
      var wert = zuZahl(istLeer(r[col.ek]) ? null : r[col.ek]);
      if (!(nr in ek) || wert > ek[nr]) ek[nr] = wert;
      if (col.kategorie !== null) kat[nr] = txt(r[col.kategorie]).trim();
      if (col.marke !== null) marke[nr] = txt(r[col.marke]).trim();
      var parts = [];
      ["lieferant", "liefertyp", "kategorie", "produkt"].forEach(function (key) {
        if (col[key] !== null) parts.push(txt(r[col[key]]));
      });
      schrott[nr] = parts.join(" ");
      info[nr] = ["lieferant", "liefertyp", "produkt"].map(function (key) {
        return col[key] !== null ? txt(r[col[key]]) : "nan";
      });
    }
    return { ek: ek, kat: kat, marke: marke, schrott: schrott, info: info, zeilen: zeilen };
  }

  // ------------------------------------------------------------ Korrekturliste
  // rows = Array of Arrays (CSV oder XLSX), erste Zeile = Kopf
  function parseKorrekturen(rows) {
    if (!rows || !rows.length) return {};
    var header = rows[0], col = {}, k;
    for (k in KORREKTUR_SPALTEN) col[k] = findeSpalte(header, KORREKTUR_SPALTEN[k]);
    if (col.lagernr === null || col.ek === null) {
      throw new Error("In der Korrekturliste fehlt 'Lager-Nr' oder 'EK'. Gefunden: " + header.join(", "));
    }
    var out = {};
    for (var i = 1; i < rows.length; i++) {
      var r = rows[i]; if (!r) continue;
      var nr = lagernr(r[col.lagernr]);
      if (!nr || nr.toLowerCase() === "nan" || nr.toLowerCase() === "none") continue;
      var g = col.grund !== null && r[col.grund] !== null && r[col.grund] !== undefined ?
        String(r[col.grund]).trim() : "";
      if (!g || g === "nan" || g === "None") g = "Korrektur";
      if (nr in out) throw new Error("Lager-Nr " + nr + " steht doppelt in der Korrekturliste – " +
        "bitte bereinigen, sonst ist die Korrektur nicht eindeutig.");
      var ref = null;
      if (col.ref !== null && r[col.ref] !== null && r[col.ref] !== undefined) {
        var rs = String(r[col.ref]).trim();
        if (rs && rs !== "nan" && rs !== "None") ref = zuZahl(rs);
      }
      out[nr] = { ek: zuZahl(r[col.ek]), grund: g, ref: ref };
    }
    return out;
  }
  function korrekturenAusCsv(text) {
    var first = text.split(/\r?\n/)[0] || "";
    var sep = ((first.match(/;/g) || []).length >= (first.match(/,/g) || []).length) ? ";" : ",";
    return parseKorrekturen(csvZeilen(text.replace(/^﻿/, ""), sep));
  }

  // ------------------------------------------------------------ Berechnung
  // opts: {stichtag:'YYYY-MM-DD', bestand:[rows], bestandName, odoo:{...},
  //        odooName, korr:{nr:{ek,grund}}, korrName, ek0Muster, fassung}
  function berechne(opts) {
    var rx = opts.ek0Muster === "" ? null : new RegExp(opts.ek0Muster || "schrott", "i");
    var bestand = opts.bestand, erg = {
      stichtag: opts.stichtag, umfang: "gesamt", quelle_bestand: opts.bestandName || "",
      quelle_odoo: opts.odooName || null, quelle_portal: null,
      bestand_zeilen_gesamt: bestand.length, status_verteilung: {},
      geraete: 0, menge: 0, duplikate: 0,
      ek_odoo: 0, n_odoo: 0, ek_portal: 0, n_portal: 0, ek_geschaetzt: 0, n_geschaetzt: 0, n_schrott_ek0: 0,
      ek_belegt: 0, ek_gesamt: 0,
      fassung: opts.fassung || null, quelle_korrektur: opts.korrName || null,
      n_korrektur: 0, ek_korrektur: 0, n_korrektur_nicht_im_bestand: 0,
      n_korrektur_ueberholt: 0, n_aeg_satz: 0, aeg_satz: null, korrektur_gruende: {},
      pauschal_korrekturen: [], ek_pauschal: 0, vergleich: null, warnungen: []
    };
    bestand.forEach(function (r) { erg.status_verteilung[r.status] = (erg.status_verteilung[r.status] || 0) + 1; });

    // Umfang gesamt + Dubletten
    var lager = [], gesehen = {}, fremd = {};
    bestand.forEach(function (r) {
      if (UMFANG_STATUS.indexOf(r.status) < 0) { if (r.status) fremd[r.status] = 1; return; }
      if (gesehen[r.lagernr]) { erg.duplikate++; return; }
      gesehen[r.lagernr] = 1; lager.push(r);
    });
    var fremdK = Object.keys(fremd).sort();
    if (fremdK.length) erg.warnungen.push("Unbekannte AMM-Status im Bestand: " + fremdK.join(", ") +
      " — nicht bewertet. Bitte prüfen, ob sie physisch im Lager stehen.");
    if (erg.duplikate) erg.warnungen.push(erg.duplikate + " doppelte Lager-Nrn entfernt (keine Doppelzählung).");
    erg.geraete = lager.length;
    erg.menge = lager.reduce(function (a, r) { return a + r.menge; }, 0);

    var ekOdoo = opts.odoo ? opts.odoo.ek : {}, katMap = opts.odoo ? opts.odoo.kat : {},
      markeMap = opts.odoo ? opts.odoo.marke : {}, schrottTxt = opts.odoo ? opts.odoo.schrott : {},
      infoMap = opts.odoo ? opts.odoo.info : {};
    var aegSatz = (opts.aegSatz === null || opts.aegSatz === undefined || opts.aegSatz === "") ? null : Number(opts.aegSatz);
    var korr = opts.korr || {};
    if (!Object.keys(ekOdoo).length) throw new Error("Keine Preisquelle: Odoo-Export fehlt oder ist leer.");

    // ---- Preisquellen: Korrektur (inkl. AEG-Satz) > Odoo > (Portal) > offen
    var preis = {}, quelle = {}, offen = [], korrInfo = {};
    var bezMap = {}; lager.forEach(function (r) { bezMap[r.lagernr] = r.bezeichner; });
    lager.forEach(function (r) {
      var nr = r.lagernr, w, k = (nr in korr) ? korr[nr] : null;
      if (k && k.ref !== null && k.ref !== undefined) {
        var jetzt = ekOdoo[nr] || 0;
        if (jetzt > 0 && Math.abs(jetzt - k.ref) > 0.01) { erg.n_korrektur_ueberholt++; k = null; }
      }
      if (!k && aegSatz !== null && (ekOdoo[nr] || 0) <= 0) {
        var inf = infoMap[nr] || ["nan", "nan", "nan"];
        var hit = rx && rx.test((schrottTxt[nr] || "") + " " + (bezMap[nr] || ""));
        if (!hit && istAeg(inf[0], inf[1], inf[2], r.bestellnr)) { k = { ek: aegSatz, grund: AEG_GRUND, ref: null }; erg.n_aeg_satz++; }
      }
      if (k) {
        w = k.ek; preis[nr] = w; quelle[nr] = "korrektur"; korrInfo[nr] = k;
        var g = erg.korrektur_gruende[k.grund] ||
          (erg.korrektur_gruende[k.grund] = { n: 0, ek: 0, ek_vorher_odoo: 0, n_vorher_ohne_ek: 0 });
        g.n++; g.ek += w;
        var vorher = ekOdoo[nr] || 0; g.ek_vorher_odoo += vorher; if (vorher <= 0) g.n_vorher_ohne_ek++;
        return;
      }
      w = ekOdoo[nr] || 0;
      if (w > 0) { preis[nr] = w; quelle[nr] = "odoo"; return; }
      offen.push(nr);
    });
    if (erg.n_korrektur_ueberholt) erg.warnungen.push(erg.n_korrektur_ueberholt + " Lose aus der Korrekturliste haben " +
      "inzwischen einen geänderten Einkaufspreis in Odoo; der Odoo-Preis wurde übernommen.");
    if (erg.n_aeg_satz) {
      erg.aeg_satz = aegSatz;
      erg.warnungen.push(erg.n_aeg_satz + " AEG-Electrolux-Lose ohne Einkaufspreis in Odoo mit festem Satz " +
        aegSatz.toFixed(2).replace(".", ",") + " € je Gerät bewertet (Σ " + eur(erg.n_aeg_satz * aegSatz) + ").");
    }
    Object.keys(korr).forEach(function (nr) { if (!gesehen[nr]) erg.n_korrektur_nicht_im_bestand++; });
    if (erg.n_korrektur_nicht_im_bestand) erg.warnungen.push(erg.n_korrektur_nicht_im_bestand +
      " Lager-Nrn aus der Korrekturliste stehen nicht im AMM-Bestand vom Stichtag und wurden nicht bewertet.");

    Object.keys(preis).forEach(function (nr) {
      if (quelle[nr] === "odoo") { erg.n_odoo++; erg.ek_odoo += preis[nr]; }
      else if (quelle[nr] === "korrektur") { erg.n_korrektur++; erg.ek_korrektur += preis[nr]; }
    });
    erg.ek_belegt = erg.ek_odoo + erg.ek_portal + erg.ek_korrektur;
    if (erg.n_korrektur) erg.warnungen.push(erg.n_korrektur + " Geräte mit nachträglich korrigiertem Einkaufspreis (Σ " +
      eur(erg.ek_korrektur) + ") aus " + (opts.korrName || "Korrekturliste") +
      "; die Korrektur ersetzt Odoo-Preis bzw. Durchschnittswert.");

    // ---- Durchschnitts-Fill (nur positive Preise in die Mittelwerte)
    function mittelwerte(keymap) {
      var s = {}, out = {}, nr, k;
      for (nr in preis) {
        if (preis[nr] <= 0) continue;
        k = keymap[nr];
        if (k) { (s[k] = s[k] || []).push(preis[nr]); }
      }
      for (k in s) out[k] = s[k].reduce(function (a, b) { return a + b; }, 0) / s[k].length;
      return out;
    }
    var mKat = mittelwerte(katMap), mMarke = mittelwerte(markeMap), mBez = mittelwerte(bezMap);
    var pos = Object.keys(preis).filter(function (nr) { return preis[nr] > 0; });
    var mGlobal = pos.length ? pos.reduce(function (a, nr) { return a + preis[nr]; }, 0) / pos.length : 0;

    var fillRegel = {};
    offen.forEach(function (nr) {
      var txt = (schrottTxt[nr] || "") + " " + (bezMap[nr] || "");
      if (rx && rx.test(txt)) { erg.n_schrott_ek0++; preis[nr] = 0; quelle[nr] = "schrott"; return; }
      var w, q;
      if (mKat[katMap[nr] === undefined ? "" : katMap[nr]]) { w = mKat[katMap[nr]]; q = "Ø Kategorie"; }
      else if (mMarke[markeMap[nr] === undefined ? "" : markeMap[nr]]) { w = mMarke[markeMap[nr]]; q = "Ø Marke"; }
      else if (mBez[bezMap[nr] === undefined ? "" : bezMap[nr]]) { w = mBez[bezMap[nr]]; q = "Ø Bezeichner"; }
      else { w = mGlobal; q = "Ø global"; }
      if (w && w > 0) { erg.ek_geschaetzt += w; erg.n_geschaetzt++; preis[nr] = w; quelle[nr] = "schaetzung"; fillRegel[nr] = q; }
    });
    erg.ek_gesamt = erg.ek_belegt + erg.ek_geschaetzt + erg.ek_pauschal;
    if (erg.n_geschaetzt) {
      var anteil = erg.ek_gesamt ? erg.ek_geschaetzt / erg.ek_gesamt * 100 : 0;
      erg.warnungen.push(erg.n_geschaetzt + " Geräte ohne Einkaufspreis wurden mit Durchschnittswerten belegt (" +
        anteil.toFixed(1).replace(".", ",") + " % des Warenwerts).");
    }
    if (erg.n_schrott_ek0) erg.warnungen.push(erg.n_schrott_ek0 + " Geräte als Schrottware erkannt (Muster '" +
      (opts.ek0Muster || "schrott") + "') und mit echtem EK 0 € bewertet.");

    // ---- Geräteliste (Prüfpfad je Lager-Nr), gleiche Spalten wie das Python-Skript
    var geraete = lager.map(function (r) {
      var nr = r.lagernr;
      return {
        "Lager-Nr": nr, "AMM-Status": r.status, "Bezeichner (AMM)": r.bezeichner, "Menge": r.menge,
        "Produktkategorie (Odoo)": katMap[nr] === undefined ? "" : katMap[nr],
        "Marke (Odoo)": markeMap[nr] === undefined ? "" : markeMap[nr],
        "Lieferant/-typ (Odoo)": schrottTxt[nr] === undefined ? "" : schrottTxt[nr],
        "EK Odoo": nr in ekOdoo ? ekOdoo[nr] : "", "EK Portal": "",
        "EK Korrektur": nr in korrInfo ? korrInfo[nr].ek : "",
        "Korrektur-Grund": nr in korrInfo ? korrInfo[nr].grund : "",
        "Preisquelle": quelle[nr] || "ohne", "Fill-Regel": fillRegel[nr] || "",
        "EK bewertet": nr in preis ? preis[nr] : 0,
        "AMM-Bestellnummer": r.bestellnr, "WE-Datum": r.we
      };
    });
    // Korrekturliste für den Folgemonat: alle angewandten Korrekturen der Lose,
    // die am Stichtag im Lager stehen, mit dem aktuellen Odoo-EK als Referenz
    var korrAusgabe = lager.filter(function (r) { return r.lagernr in korrInfo; }).map(function (r) {
      return { nr: r.lagernr, ek: korrInfo[r.lagernr].ek, grund: korrInfo[r.lagernr].grund, ref: ekOdoo[r.lagernr] || 0 };
    });
    return { erg: erg, geraete: geraete, korrAusgabe: korrAusgabe };
  }

  // Aufteilung gesamt / freiverkäuflich / verkauft-noch-nicht-verschickt
  function statusAufteilung(geraete) {
    var s = { QE: { n: 0, ek: 0 }, VS: { n: 0, ek: 0 }, AA: { n: 0, ek: 0 } };
    geraete.forEach(function (g) { var k = g["AMM-Status"]; if (s[k]) { s[k].n++; s[k].ek += g["EK bewertet"]; } });
    return {
      gesamt: { n: geraete.length, ek: s.QE.ek + s.VS.ek + s.AA.ek },
      frei: s.QE, verkauft: { n: s.VS.n + s.AA.n, ek: s.VS.ek + s.AA.ek }, vs: s.VS, aa: s.AA
    };
  }

  // ------------------------------------------------------------ Monatsreihe
  function serieLesen(text) {
    var out = [];
    (text || "").split(/\r?\n/).slice(1).forEach(function (z) {
      if (!z.trim()) return;
      var p = z.split(";"); out.push({ tag: p[0], stk: parseInt(p[1], 10), wert: parseFloat(p[2]) });
    });
    return out;
  }
  function tagDE(iso) { return iso.slice(8, 10) + "." + iso.slice(5, 7) + "." + iso.slice(0, 4); }
  function datumKey(tagDe) { var p = tagDe.split("."); return p[2] + p[1] + p[0]; }
  function serieFortschreiben(text, erg) {
    var tag = tagDE(erg.stichtag);
    var zeilen = (text || "").split(/\r?\n/).filter(function (z) { return z.length; });
    if (!zeilen.length) zeilen = ["Monatsende;Stück;EK-Wert"];
    var kopf = zeilen[0];
    var rest = zeilen.slice(1).filter(function (z) { return z.trim() && z.indexOf(tag + ";") !== 0; });
    rest.push(tag + ";" + erg.geraete + ";" + rund0(erg.ek_gesamt));
    rest.sort(function (a, b) { return datumKey(a.split(";")[0]) < datumKey(b.split(";")[0]) ? -1 : 1; });
    return [kopf].concat(rest).join("\n") + "\n";
  }

  // ------------------------------------------------------------ CSV-Ausgaben
  function csvZeile(arr) {
    return arr.map(function (v) {
      var s = (v === null || v === undefined) ? "" : String(v);
      return /[;"\n]/.test(s) ? '"' + s.replace(/"/g, '""') + '"' : s;
    }).join(";");
  }
  function csvGeraete(geraete) {
    if (!geraete.length) return "";
    var cols = Object.keys(geraete[0]);
    var lines = [csvZeile(cols)];
    geraete.forEach(function (g) {
      lines.push(csvZeile(cols.map(function (c) {
        var v = g[c];
        return (typeof v === "number") ? String(Math.round(v * 100) / 100).replace(".", ",") : v;
      })));
    });
    return "﻿" + lines.join("\n") + "\n";
  }
  function csvKorrekturen(korrAusgabe) {
    var lines = ["Lager-Nr;EK;Grund;EK Odoo bei Korrektur"];
    korrAusgabe.forEach(function (k) {
      lines.push(csvZeile([k.nr, k.ek.toFixed(2), k.grund, k.ref.toFixed(2)]));
    });
    return lines.join("\n") + "\n";
  }
  function csvStatusAufteilung(erg, split) {
    var t = tagDE(erg.stichtag);
    function z(label, o) { return csvZeile([label, o.n, String(Math.round(o.ek * 100) / 100).replace(".", ",")]); }
    return "﻿" + ["Warenwert zum " + t + " · Einkauf (EK) · Aufteilung nach AMM-Status;Geräte;EK",
      z("Gesamt physisch im Lager (QE + VS + AA)", split.gesamt),
      z("davon freiverkäuflich (QE)", split.frei),
      z("davon verkauft, noch nicht verschickt (VS + AA)", split.verkauft),
      z("   · Versandpipeline (VS)", split.vs),
      z("   · auftragsgebunden (AA)", split.aa)].join("\n") + "\n";
  }

  // ------------------------------------------------------------ Einseiter (jsPDF)
  // Millimetergenauer Nachbau von warenwert_pdf.py (reportlab, Darstellung
  // 'belegt'): Wert, Aufschlüsselung, Monatsreihe, Quellen. Geometrie aus dem
  // reportlab-Layout übernommen: Rand 2 cm + 6 pt Rahmenabstand, Tabellen
  // 16,6 cm breit, Zellabstände 10/7 pt, Zeilenhöhe = Leading 12 pt + Abstände.
  function bauPdf(jsPDF, erg, serie, erstelltAm, erzeugtMit) {
    var doc = new jsPDF({ unit: "mm", format: "a4" });
    var PT = 25.4 / 72;
    var INK = [29, 29, 31], INK_SOFT = [66, 66, 69], SUBTLE = [134, 134, 139], DIVIDER = [210, 210, 215],
      CARD = [245, 245, 247], PAPER = [251, 251, 253], BLUE = [0, 113, 227], BLUE_BG = [232, 241, 252], WHITE = [255, 255, 255];
    var tag = tagDE(erg.stichtag);
    var X0 = 20 + 6 * PT, FW = 170 - 12 * PT;          // Frame (SimpleDocTemplate, 6 pt Padding)
    var TW = 166, TX = X0 + (FW - TW) / 2;              // 16,6-cm-Tabellen, zentriert
    function font(size, bold, col) { doc.setFont("helvetica", bold ? "bold" : "normal"); doc.setFontSize(size); doc.setTextColor(col[0], col[1], col[2]); }
    function rect(x, y, w, h, c) { doc.setFillColor(c[0], c[1], c[2]); doc.rect(x, y, w, h, "F"); }
    function hline(x1, x2, y, c) { doc.setDrawColor(c[0], c[1], c[2]); doc.setLineWidth(0.4 * PT); doc.line(x1, y, x2, y); }
    function txt(t, x, y, right) { doc.text(t, x, y, right ? { align: "right" } : undefined); }

    // Kopf/Fuß (canvas, wie kopf_fuss())
    font(8.5, true, INK); txt("ELVINCI.DE GMBH", 20, 14);
    font(8.5, false, SUBTLE); txt("·  Warenwert", 50, 14);
    font(8.5, false, BLUE); txt("VERTRAULICH · INTERN", 190, 14, true);
    hline(20, 190, 297 - 280.5, DIVIDER);
    hline(20, 190, 297 - 16, DIVIDER);
    font(8, false, SUBTLE); txt("Stichtag " + tag + " · erstellt " + erstelltAm, 20, 297 - 11);
    font(8, true, INK_SOFT); txt("Seite 1", 190, 297 - 11, true);

    var y = 22 + 6 * PT;
    function para(t, size, leading, after, col, bold, width) {
      font(size, bold, col);
      var lines = width ? doc.splitTextToSize(t, width) : [t];
      lines.forEach(function (l, k) { txt(l, X0, y + size * PT + k * leading * PT); });
      y += lines.length * leading * PT + after * PT;
    }
    para("MONATSREIHE · STICHTAG " + tag, 9, 12, 4, BLUE, true);
    para("Warenwert", 26, 30, 2, INK, true);
    para("Alles physisch im Lager, inkl. bereits verkaufter Ware (AMM-Status QE + VS + AA)", 12, 16, 4, SUBTLE, false);
    y += 5;

    // Hero
    var hh = (20 + 11 + 3 + 48 + 5 + 14 + 20) * PT, hx = TX + 22 * PT, hy = y + 20 * PT;
    rect(TX, y, TW, hh, CARD); rect(TX - 1.5 * PT, y, 3 * PT, hh, BLUE);
    font(8.5, true, SUBTLE); txt("WARENWERT · EINKAUF (EK)", hx, hy + 8.5 * PT); hy += (11 + 3) * PT;
    font(42, true, INK); txt(eur(erg.ek_gesamt), hx, hy + 42 * PT); hy += (48 + 5) * PT;
    font(10.5, false, INK_SOFT); txt(de(erg.geraete) + " Geräte · Ø " + eur(erg.ek_gesamt / Math.max(erg.geraete, 1)) + " je Gerät", hx, hy + 10.5 * PT);
    y += hh + 5;

    function h2(t) { y += 12 * PT; font(13, true, INK); txt(t, X0, y + 13 * PT); y += (17 + 6) * PT; }

    // Aufschlüsselung
    h2("Aufschlüsselung");
    var rows = [{ c: ["Herkunft des Werts", "Geräte", "EK"], head: true }];
    rows.push({ c: ["Einkaufspreis aus Odoo (belegt)", de(erg.n_odoo), eur(erg.ek_odoo)] });
    if (erg.n_portal) rows.push({ c: ["Portal-Restbestand (belegt)", de(erg.n_portal), eur(erg.ek_portal)] });
    Object.keys(erg.korrektur_gruende).forEach(function (g) {
      rows.push({ c: [g + " (belegt)", de(erg.korrektur_gruende[g].n), eur(erg.korrektur_gruende[g].ek)], para: true });
    });
    rows.push({ c: ["Gruppenbewertung zum Durchschnitts-EK der Warengruppe", de(erg.n_geschaetzt), eur(erg.ek_geschaetzt)] });
    if (erg.n_schrott_ek0) rows.push({ c: ["Schrottware — echter EK 0 €", de(erg.n_schrott_ek0), "—"] });
    rows.push({ c: ["Summe", de(erg.geraete), eur(erg.ek_gesamt)], sum: true });
    var LP = 10 * PT, VP = 7 * PT, LEAD = 12 * PT, C1R = TX + 96 + 30 - LP, C2R = TX + TW - LP;
    rows.forEach(function (r, i) {
      var fs = r.head ? 8 : 9.5, bold = r.head || r.sum, col = r.head ? WHITE : (r.sum ? INK : INK_SOFT);
      font(fs, bold, col);
      var lines = r.para ? doc.splitTextToSize(r.c[0], 96 - 2 * LP) : [r.c[0]];
      var ch = Math.max(lines.length * LEAD, LEAD), h = ch + 2 * VP;
      rect(TX, y, TW, h, r.head ? INK : (r.sum ? BLUE_BG : (i % 2 === 1 ? WHITE : PAPER)));
      font(fs, bold, col);
      if (r.para) lines.forEach(function (l, k) { txt(l, TX + LP, y + VP + fs * PT + k * LEAD); });
      var mid = y + VP + (ch - LEAD) / 2 + fs * PT;
      if (!r.para) txt(r.c[0], TX + LP, mid);
      txt(r.c[1], C1R, mid, true); txt(r.c[2], C2R, mid, true);
      y += h; hline(TX, TX + TW, y, DIVIDER);
    });

    // Monatsreihe
    if (serie && serie.length) {
      h2("Monatsreihe");
      var letzte = serie.slice(-7), n = letzte.length, RH = (12 + 10) * PT, P6 = 6 * PT;
      var reihen = [["Monatsende"].concat(letzte.map(function (z) { return z.tag.slice(0, 6) + z.tag.slice(8); })),
        ["Geräte"].concat(letzte.map(function (z) { return de(z.stk); })),
        ["EK-Wert"].concat(letzte.map(function (z) { return tausender(rund0(z.wert / 1000)) + " k"; }))];
      var mw = 26 + 20 * n;
      rect(TX + 26 + 20 * (n - 1), y, 20, 3 * RH, BLUE_BG);
      reihen.forEach(function (r, ri) {
        var base = y + 5 * PT + 8.5 * PT;
        font(8.5, true, INK_SOFT); txt(r[0], TX + P6, base);
        for (var ci = 1; ci <= n; ci++) {
          font(8.5, ri === 0, (ci === n && ri > 0) ? INK : INK_SOFT);
          txt(r[ci], TX + 26 + 20 * ci - P6, base, true);
        }
        y += RH; if (ri < 2) hline(TX, TX + mw, y, DIVIDER);
      });
    }

    // Quellen
    y += 3.5 + 4 * PT; hline(X0, X0 + FW, y, DIVIDER); y += (0.4 + 6) * PT;
    var quellen = "Quellen: " + erg.quelle_bestand;
    if (erg.quelle_odoo) quellen += " · " + erg.quelle_odoo;
    if (erg.quelle_portal) quellen += " · " + erg.quelle_portal;
    if (erg.quelle_korrektur) quellen += " · Korrekturliste " + erg.quelle_korrektur;
    quellen += " · verknüpft über die Lager-Nr · AMM-Bestand " + de(erg.bestand_zeilen_gesamt) + " Zeilen (" +
      sortedStatus(erg.status_verteilung) + ") · erzeugt mit " + (erzeugtMit || "warenwert_stichtag.py") +
      " · keine personenbezogenen Daten.";
    para(quellen, 8, 11, 0, SUBTLE, false, FW);
    return doc;
  }

  return {
    VERSION: VERSION, lagernr: lagernr, zuZahl: zuZahl, rund0: rund0, eur: eur, de: de, tagDE: tagDE, tausender: tausender,
    csvZeilen: csvZeilen, findeSpalte: findeSpalte,
    parseBestand: parseBestand, stichtagAusDateiname: stichtagAusDateiname,
    parseOdoo: parseOdoo, parseKorrekturen: parseKorrekturen, korrekturenAusCsv: korrekturenAusCsv,
    berechne: berechne, statusAufteilung: statusAufteilung, istAeg: istAeg, AEG_GRUND: AEG_GRUND,
    serieLesen: serieLesen, serieFortschreiben: serieFortschreiben,
    csvGeraete: csvGeraete, csvKorrekturen: csvKorrekturen, csvStatusAufteilung: csvStatusAufteilung,
    bauPdf: bauPdf, waehleDateien: waehleDateien, datumImNamen: datumImNamen,
    istMonatsende: istMonatsende, letzterMonatsletzter: letzterMonatsletzter
  };
});
