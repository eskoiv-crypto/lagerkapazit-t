#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Baut die Einzeldatei `lagerwert_tool.html` aus Vorlage, Rechenkern und den
eingebetteten Bibliotheken (vendor/). Ergebnis läuft ohne Internet und ohne
Installation im Browser (Edge/Chrome/Firefox).

  python3 build_lagerwert_tool.py
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parent
template = (ROOT / "lagerwert_tool.template.html").read_text(encoding="utf-8")
core = (ROOT / "lagerwert_core.js").read_text(encoding="utf-8")
xlsx = (ROOT / "vendor" / "xlsx.full.min.js").read_text(encoding="utf-8")
jspdf = (ROOT / "vendor" / "jspdf.umd.min.js").read_text(encoding="utf-8")

def safe(js: str) -> str:
    # '</script>' innerhalb eingebetteter Skripte entschärfen
    return js.replace("</script", "<\\/script")

out = (template
       .replace("/*__XLSX__*/", safe(xlsx))
       .replace("/*__JSPDF__*/", safe(jspdf))
       .replace("/*__CORE__*/", safe(core)))
(ROOT / "lagerwert_tool.html").write_text(out, encoding="utf-8")
print(f"lagerwert_tool.html geschrieben ({len(out)/1024:.0f} KB)")
