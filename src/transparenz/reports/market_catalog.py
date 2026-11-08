"""Standalone local viewer: all entries searchable, no CDN and no network requests."""

import json

from jinja2 import Environment
from markupsafe import Markup

TEMPLATE = """<!doctype html>
<html lang="de-CH"><meta charset="utf-8"><meta name="viewport" content="width=device-width">
<title>Aktien- und Fonds-Katalog · lokaler Bestand</title>
<style>
body{font:16px system-ui,sans-serif;margin:2rem auto;max-width:1400px;padding:0 1rem;color:#172c3d;
background:#f7fafb}h1{margin-bottom:.5rem}
section{background:white;padding:1rem;margin:1rem 0;
border:1px solid #ccd8df;border-radius:8px}
input,select,button{font:inherit;padding:.5rem;margin:.3rem}
input{width:min(90%,36rem)}table{width:100%;border-collapse:collapse}th,td{text-align:left;
border-bottom:1px solid #ddd;padding:.5rem;vertical-align:top}th{background:#eef4f6}
small{display:block;color:#536878}.scroll{overflow:auto}button{cursor:pointer}
details{max-width:450px}pre{white-space:pre-wrap;font-size:12px}a{color:#145c80}
</style><h1>Aktien- und Fonds-Katalog</h1>
<p>Lokaler Aufbau für weltweite Aktien und ETFs ·
<strong>Weltweite Vollständigkeit noch offen</strong></p>
<section><strong>{{ report.catalogue_entry_count }} Katalogeinträge</strong>
<p>Das sind Quellenbeobachtungen. Mehrere Einträge können dasselbe Wertpapier betreffen.
Nicht klassifizierte Ticker sind keine bestätigten Aktien. Fonds-Anteilsklassen enthalten auch
Publikumsfonds ohne Börsenhandel. ISIN, Kurse und heutige Handelbarkeit sind hier nicht belegt.</p>
<details><summary>Abdeckung und fehlende Märkte anzeigen</summary>
{% for market in report.coverage %}<p><strong>{{ market.market }}</strong>: {{ market.status }}.
{% for gap in market.gaps|default([]) %}{{ gap }} {% endfor %}</p>{% endfor %}
{% for key, source in report.sources.items() %}<p>{{ key }}: Version {{ source.active_version }},
abgerufen {{ source.fetched_at|default('–',true) }}; letzter Lauf {{ source.last_run }}.
{{ source.attribution }}{% if source.license_block_reasons %}
Lizenzsperre: {{ source.license_block_reasons|join('; ') }}{% endif %}</p>{% endfor %}
</details></section>
<section><label for="search">Name, Ticker, CIK, Serien- oder Class-ID suchen</label><br>
<input id="search" type="search" placeholder="z. B. Apple, AAPL, Vanguard oder SPY">
<select id="kind" aria-label="Instrumenttyp"><option value="">Alle Einträge</option>
<option value="etf_reported_single_class">ETF: in Ein-Klassen-Meldung bestätigt</option>
<option value="etf_series_class_unresolved">ETF-Serie: einzelne Klasse offen</option>
<option value="listed_instrument_unclassified">Ticker/Börse: Instrumenttyp offen</option>
<option value="fund_class_unclassified">Fonds-Anteilsklasse: Typ offen</option>
<option value="fund_class_reported_non_etf">Fonds: gemeldet kein ETF</option>
<option value="identity_conflict">Identitätskonflikte</option></select>
<p id="count" role="status"></p><button id="prev">Zurück</button><button id="next">Weiter</button>
<div class="scroll"><table><thead><tr><th>Name / Ticker</th><th>Klassifikation</th>
<th>Kennungen / Börse</th><th>Quelle / Berichtsdatum</th></tr></thead><tbody id="rows"></tbody>
</table></div></section><p>Quelle: U.S. Securities and Exchange Commission. Lokal aufbereitet,
keine Billigung durch die SEC. Kein Nachhaltigkeitsurteil und keine Anlageempfehlung.</p>
<script type="application/json" id="data">{{ data }}</script>
<script>
const data=JSON.parse(document.getElementById('data').textContent);
const labels={etf_reported_single_class:'ETF: Ein-Klassen-Meldung',
etf_series_class_unresolved:'ETF-Serie; Anteilsklasse offen',
listed_instrument_unclassified:'Ticker/Börse; Typ offen',
fund_class_unclassified:'Fondsklasse; Typ offen',
fund_class_reported_non_etf:'Fonds: gemeldet kein ETF',identity_conflict:'Identitätskonflikt'};
const search=document.getElementById('search'),kind=document.getElementById('kind');
const rows=document.getElementById('rows');let offset=0;const size=100;
const index=data.map(r=>[r.name,r.class_name,r.registrant_cik,r.series_id,r.class_id,
...r.tickers,...r.reported_tickers].filter(Boolean).join(' ').toLocaleLowerCase());
function text(tag,value,parent){const e=document.createElement(tag);e.textContent=value;
parent.append(e);return e;}
function draw(){const q=search.value.trim().toLocaleLowerCase();
const matches=data.filter((r,i)=>(!kind.value||r.classification===kind.value)
&&index[i].includes(q));
matches.sort((a,b)=>Number(!a.tickers.some(t=>t.toLocaleLowerCase()===q))
-Number(!b.tickers.some(t=>t.toLocaleLowerCase()===q)));
offset=Math.max(0,Math.min(offset,Math.max(0,Math.ceil(matches.length/size)-1)*size));
rows.replaceChildren();
for(const r of matches.slice(offset,offset+size)){const tr=document.createElement('tr');
const a=text('td','',tr);text('strong',r.name||r.class_name||'Name nicht in Quelle enthalten',a);
text('small','Ticker: '+(r.tickers.join(', ')||'nicht in aktueller SEC-Tickerliste'),a);
if(r.reported_tickers.length)text('small','Gemeldet: '+r.reported_tickers.join(', '),a);
const b=text('td',labels[r.classification]||r.classification,tr);
text('small',r.classification_basis,b);
const c=text('td','',tr);for(const [label,v] of [['Class-ID',r.class_id],['Serie',r.series_id],
['Registrant-CIK',r.registrant_cik],['Börse laut SEC',r.exchange]])
if(v)text('small',label+': '+v,c);
const d=text('td',r.report_date?'Berichtsdatum: '+r.report_date:'Berichtsdatum unbekannt',tr);
if(r.filing_date)text('small','Eingereicht: '+r.filing_date,d);
const detail=document.createElement('details');text('summary','Quellen / Originalnachweis',detail);
for(const e of r.evidence){if(e.source_url.startsWith('https://www.sec.gov/')){
const link=text('a',e.source_key,detail);link.href=e.source_url;
link.target='_blank';link.rel='noopener';}
text('pre',JSON.stringify(e,null,2),detail);}d.append(detail);rows.append(tr);}
document.getElementById('count').textContent=matches.length+' Treffer · '+
(matches.length?offset+1:0)+'–'+Math.min(offset+size,matches.length)+' angezeigt';
document.getElementById('prev').disabled=offset===0;
document.getElementById('next').disabled=offset+size>=matches.length;}
search.addEventListener('input',()=>{offset=0;draw();});
kind.addEventListener('change',()=>{offset=0;draw();});
document.getElementById('prev').onclick=()=>{offset-=size;draw();};
document.getElementById('next').onclick=()=>{offset+=size;draw();};draw();
</script></html>"""


def render_catalogue(items: list[dict], report: dict) -> str:
    # Literal '<' must never terminate the JSON script, including hostile source names.
    data = json.dumps(items, ensure_ascii=False).replace("<", "\\u003c")
    return Environment(autoescape=True).from_string(TEMPLATE).render(
        report=report, data=Markup(data))
