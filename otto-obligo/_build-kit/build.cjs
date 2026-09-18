#!/usr/bin/env node
// Build: SheetJS + jsPDF + pako + (optional) Otto-Historie in app_template.html einbetten -> Otto-Obligo-Cockpit.html
//
//   OTTO_CFG_PW=… node otto-obligo/_build-kit/build.cjs                      -> otto-obligo/dist/Otto-Obligo-Cockpit.html
//   node otto-obligo/_build-kit/build.cjs --out <pfad> [--hist <csv>] [--no-hist]
//
// Historie:   _build-kit/hist_register.csv oder --hist <pfad>  (Agicap-Register-Export, VERTRAULICH -> .gitignore, nie committen)
//             --no-hist erzwingt einen Build ohne Historie (Tests).
// Passwort:   PFLICHT — Umgebungsvariable OTTO_CFG_PW oder _build-kit/local.config.json {"cfgPw":"…"} (beides nie committen).
//             Das Repo ist öffentlich: hier steht bewusst kein Standard-Passwort.
"use strict";
const fs = require("fs"), path = require("path"), vm = require("vm");

const KIT = __dirname;
const ROOT = path.resolve(KIT, "..", "..");            // Repo-Wurzel (node_modules liegt dort)
const args = process.argv.slice(2);
const argOf = k => { const i = args.indexOf(k); return i >= 0 ? args[i + 1] : null; };
const OUT = path.resolve(argOf("--out") || path.join(KIT, "..", "dist", "Otto-Obligo-Cockpit.html"));
const NO_HIST = args.includes("--no-hist");

function lib(rel) {
  const p = path.join(ROOT, "node_modules", rel);
  if (!fs.existsSync(p)) { console.error("Bibliothek fehlt: " + p + "\n-> im Repo-Root `npm install` ausführen."); process.exit(1); }
  return fs.readFileSync(p, "utf8");
}
const T = fs.readFileSync(path.join(KIT, "app_template.html"), "utf8");
for (const ph of ["__SHEETJS__", "__JSPDF__", "__PAKO__", "__HISTCSV__", "__CFGPW__"])
  if (!T.includes(ph)) { console.error("Platzhalter " + ph + " fehlt im Template."); process.exit(1); }

const sheetjs = lib("xlsx/dist/xlsx.full.min.js");
const jspdf   = lib("jspdf/dist/jspdf.umd.min.js");
const pako    = lib("pako/dist/browser/pako.umd.min.js");

// Historie (optional). Kein CSV -> leerer String -> Cockpit startet ohne eingebettete Historie (Drop-Feld bleibt nutzbar).
const histPath = path.resolve(argOf("--hist") || path.join(KIT, "hist_register.csv"));
let hist = "";
if (NO_HIST) {
  console.log("--no-hist: Build ohne eingebettete Historie.");
} else if (fs.existsSync(histPath)) {
  hist = fs.readFileSync(histPath, "utf8").replace(/^﻿/, "");
  const otto = hist.split(/\r?\n/).filter(l => /otto/i.test(l) && !/aeg/i.test(l)).length;
  console.log("Historie eingebettet: " + histPath + " (" + otto + " Otto-Zeilen)");
} else {
  console.log("Hinweis: keine hist_register.csv -> Build OHNE eingebettete Historie (öffentlich unkritisch).");
}

// Passwort für 🔒 Einstellungen
let cfgPw = process.env.OTTO_CFG_PW || null;
const localCfg = path.join(KIT, "local.config.json");
if (!cfgPw && fs.existsSync(localCfg)) { try { cfgPw = JSON.parse(fs.readFileSync(localCfg, "utf8")).cfgPw || null; } catch (e) { console.error("local.config.json unlesbar: " + e.message); } }
if (!cfgPw) { console.error("Passwort für 🔒 Einstellungen fehlt: OTTO_CFG_PW=… setzen oder _build-kit/local.config.json {\"cfgPw\":\"…\"} anlegen."); process.exit(1); }

// Einbetten. Ersetzung über Funktion, damit "$&"/"$1" im Bibliothekscode nicht als Replace-Pattern wirken.
const put = (src, ph, val) => src.split(ph).join(val);
let html = put(T, "__SHEETJS__", sheetjs);
html = put(html, "__JSPDF__", jspdf);
html = put(html, "__PAKO__", pako);
html = put(html, "__HISTCSV__", JSON.stringify(hist));
html = put(html, "__CFGPW__", JSON.stringify(cfgPw));
if (html.includes("</script>") && /<\/script>/.test(hist)) { console.error("Historie enthält </script> — abgebrochen."); process.exit(1); }

// Syntax-Check des App-Skripts (letzter <script>-Block)
const scripts = [...html.matchAll(/<script>([\s\S]*?)<\/script>/g)].map(m => m[1]);
const app = scripts[scripts.length - 1];
try { new vm.Script(app, { filename: "app_template.html <script>" }); }
catch (e) { console.error("Syntaxfehler im App-Skript: " + e.message); process.exit(1); }

fs.mkdirSync(path.dirname(OUT), { recursive: true });
fs.writeFileSync(OUT, html, "utf8");
console.log("OK -> " + OUT + " (" + (html.length / 1024).toFixed(0) + " KB, Historie " + (hist ? "ja" : "nein") + ")");
