"""Standalone local viewer for the global Wikidata ticker/exchange research snapshot.

Separate from the Swiss viewer (reports/swiss_security_candidates.py) and the SEC market
catalogue (reports/market_catalog.py): this covers the single worldwide CC0 snapshot from
scripts/download_global_candidates.py. Every row is an unverified company-level Wikidata
claim; see services/global_candidates.py for exactly what that means.
"""

import json

from jinja2 import Environment
from markupsafe import Markup

TEMPLATE = """<!doctype html>
<html lang="de-CH"><meta charset="utf-8"><meta name="viewport" content="width=device-width">
<title>Globale Firmen-/Ticker-Kandidaten (Wikidata)</title>
<style>
body{font:16px system-ui,sans-serif;margin:2rem auto;max-width:1300px;padding:0 1rem;
color:#172c3d;background:#f7fafb}h1{margin-bottom:.5rem}
section{background:white;padding:1rem;margin:1rem 0;border:1px solid #ccd8df;border-radius:8px}
input,select{font:inherit;padding:.5rem;margin:.3rem .3rem .3rem 0}
input{width:min(90%,30rem)}
table{width:100%;border-collapse:collapse}th,td{text-align:left;
border-bottom:1px solid #ddd;padding:.5rem;vertical-align:top}th{background:#eef4f6}
small{display:block;color:#536878}a{color:#145c80}
ul{margin:.3rem 0}
</style><h1>Globale Firmen-/Ticker-Kandidaten (Wikidata)</h1>
<p><strong>{{ counts.entries }} Zeilen</strong>, {{ counts.unique_companies }} eindeutige
Wikidata-Unternehmen, {{ counts.distinct_exchanges }} Börsen. Jede Zeile ist eine
<strong>unbestätigte Wikidata-Aussage</strong> (CC0) – kein bestätigtes Wertpapier, keine ISIN,
keine Handelbarkeit, kein Nachhaltigkeitsurteil. Keine Fusion über Namen oder Ticker.</p>
<section><strong>Qualitätsbericht</strong> (Stand Abruf: {{ snapshot_retrieved_at }})
<ul>
<li>{{ counts.companies_with_multiple_tickers }} Unternehmen mit mehr als einem Ticker
(z. B. Mehrfachkotierung) – keine Dublette, dieselbe Firma.</li>
<li>{{ counts.rows_missing_exchange_label }} Zeilen ohne aufgelösten Börsennamen,
{{ counts.rows_missing_exchange_country }} ohne bekanntes Börsen-Sitzland.</li>
<li>{{ counts.possible_duplicate_name_groups }} mögliche Namensdubletten (gleicher Name,
verschiedene Wikidata-Items) – nur zur Prüfung gelistet, nicht zusammengeführt.</li>
</ul></section>
<section><label for="search">Name, Ticker oder Wikidata-ID suchen</label><br>
<input id="search" type="search" placeholder="z. B. Siemens, Roche oder SAP">
<select id="country"><option value="">Alle Länder (Börsen-Sitz)</option></select>
<select id="exchange"><option value="">Alle Börsen</option></select>
<p id="count" role="status"></p>
<table><thead><tr><th>Name</th><th>Ticker</th><th>Börse</th><th>Land (Börsen-Sitz)</th>
<th>Herkunft</th></tr></thead><tbody id="rows"></tbody></table></section>
<p>Quelle: Wikidata contributors, strukturierte Daten CC0 1.0. Keine Übernahme von
Wikipedia-Texten, keine Billigung durch Wikidata. Separat vom Schweizer Fundament
(<code>swiss-search</code>) und vom SEC-Marktkatalog (<code>market-search</code>).</p>
<script type="application/json" id="data">{{ data }}</script>
<script>
const data=JSON.parse(document.getElementById('data').textContent);
const search=document.getElementById('search'),rows=document.getElementById('rows');
const countrySel=document.getElementById('country'),exchangeSel=document.getElementById('exchange');
const countries=[...new Set(data.flatMap(r=>r.country_labels))].sort();
const exchanges=[...new Set(data.map(r=>r.exchange_label||r.exchange_id))].sort();
for(const c of countries){const o=document.createElement('option');o.value=c;o.textContent=c;
countrySel.append(o);}
for(const e of exchanges){const o=document.createElement('option');o.value=e;o.textContent=e;
exchangeSel.append(o);}
const index=data.map(r=>[r.name,r.ticker,r.wikidata_id].join(' ').toLocaleLowerCase());
function text(tag,value,parent){const e=document.createElement(tag);e.textContent=value;
parent.append(e);return e;}
function link(href,label,parent){const a=document.createElement('a');a.href=href;
a.textContent=label;a.target='_blank';a.rel='noopener';parent.append(a);return a;}
function draw(){
const q=search.value.trim().toLocaleLowerCase();
const country=countrySel.value,exchange=exchangeSel.value;
const matches=data.filter((r,i)=>index[i].includes(q)
&&(!country||r.country_labels.includes(country))
&&(!exchange||(r.exchange_label||r.exchange_id)===exchange));
rows.replaceChildren();
for(const r of matches.slice(0,300)){const tr=document.createElement('tr');
const a=text('td','',tr);link(r.item_url,r.name,a);
text('small','wikidata:'+r.wikidata_id,a);
text('td',r.ticker,tr);
const b=text('td','',tr);link(r.exchange_url,r.exchange_label||r.exchange_id,b);
text('td',r.country_labels.join(', ')||'unbekannt',tr);
text('td','unbestätigte Wikidata-Angabe',tr);
rows.append(tr);}
document.getElementById('count').textContent=matches.length+' Treffer'+
(matches.length>300?' (erste 300 angezeigt)':'');}
search.addEventListener('input',draw);countrySel.addEventListener('change',draw);
exchangeSel.addEventListener('change',draw);draw();
</script></html>"""


def render_global_candidates(rows: list[dict], report: dict) -> str:
    # Literal '<' must never terminate the JSON script, including hostile source names.
    data = json.dumps(rows, ensure_ascii=False).replace("<", "\\u003c")
    return Environment(autoescape=True).from_string(TEMPLATE).render(
        counts=report["counts"], snapshot_retrieved_at=report["snapshot_retrieved_at"],
        data=Markup(data))
