"""Standalone local viewer for Wikidata-sourced security candidates; no network requests.

Separate from the SEC market catalogue (reports/market_catalog.py): this file only
covers the Swiss foundation's ``security_candidates`` export, which are explicitly
unverified company-level claims, never confirmed issuer/ISIN mappings.
"""

import json

from jinja2 import Environment
from markupsafe import Markup

TEMPLATE = """<!doctype html>
<html lang="de-CH"><meta charset="utf-8"><meta name="viewport" content="width=device-width">
<title>Wertpapierkandidaten (Wikidata) · Schweizer Fundament</title>
<style>
body{font:16px system-ui,sans-serif;margin:2rem auto;max-width:1200px;padding:0 1rem;color:#172c3d;
background:#f7fafb}h1{margin-bottom:.5rem}
section{background:white;padding:1rem;margin:1rem 0;
border:1px solid #ccd8df;border-radius:8px}
input{font:inherit;padding:.5rem;margin:.3rem;width:min(90%,36rem)}
table{width:100%;border-collapse:collapse}th,td{text-align:left;
border-bottom:1px solid #ddd;padding:.5rem;vertical-align:top}th{background:#eef4f6}
small{display:block;color:#536878}a{color:#145c80}
</style><h1>Wertpapierkandidaten (Wikidata)</h1>
<p><strong>{{ count }} Kandidaten</strong>, {{ company_count }} Unternehmen. Jede Zeile ist eine
<strong>unbestätigte unternehmensbezogene ISIN-Angabe aus Wikidata</strong> (CC0), kein
bestätigtes Emittentenmapping, keine Handelbarkeit und kein Nachhaltigkeitsurteil. Keine
Fusion über Namen oder Ticker. Kein Vollständigkeitsnachweis für SIX oder sonst ein Markt.</p>
<section><label for="search">Name, ISIN, Ticker oder LEI suchen</label><br>
<input id="search" type="search" placeholder="z. B. Roche, Nestlé, CH0012032048 oder ROG">
<p id="count" role="status"></p>
<table><thead><tr><th>Name</th><th>ISIN</th><th>Ticker</th><th>LEI / Land</th>
<th>Quelle</th></tr></thead><tbody id="rows"></tbody></table></section>
<p>Quelle: Wikidata contributors, strukturierte Daten CC0 1.0. Keine Übernahme von
Wikipedia-Texten, keine Billigung durch Wikidata. Separat vom SEC-Marktkatalog
(<code>market-search</code> / <code>catalogue.html</code>).</p>
<script type="application/json" id="data">{{ data }}</script>
<script>
const data=JSON.parse(document.getElementById('data').textContent);
const search=document.getElementById('search'),rows=document.getElementById('rows');
const index=data.map(r=>[r.name,r.isin,r.lei,r.wikidata_id,...r.tickers]
.filter(Boolean).join(' ').toLocaleLowerCase());
function text(tag,value,parent){const e=document.createElement(tag);e.textContent=value;
parent.append(e);return e;}
function draw(){const q=search.value.trim().toLocaleLowerCase();
const matches=data.filter((r,i)=>index[i].includes(q));
rows.replaceChildren();
for(const r of matches.slice(0,300)){const tr=document.createElement('tr');
const a=text('td',r.name,tr);
text('small','wikidata:'+r.wikidata_id,a);
text('td',r.isin,tr);
text('td',r.tickers.join(', ')||'–',tr);
const d=text('td',r.lei||'keine LEI',tr);
text('small',r.country||'Land unbekannt',d);
const e=text('td',r.mapping_status,tr);
text('small','Quelle: '+r.source_key,e);
rows.append(tr);}
document.getElementById('count').textContent=matches.length+' Treffer'+
(matches.length>300?' (erste 300 angezeigt)':'');}
search.addEventListener('input',draw);draw();
</script></html>"""


def render_security_candidates(rows: list[dict]) -> str:
    # Literal '<' must never terminate the JSON script, including hostile source names.
    data = json.dumps(rows, ensure_ascii=False).replace("<", "\\u003c")
    companies = {r["wikidata_id"] for r in rows if r.get("wikidata_id")}
    return Environment(autoescape=True).from_string(TEMPLATE).render(
        count=len(rows), company_count=len(companies), data=Markup(data))
