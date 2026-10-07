#!/usr/bin/env python3
# Builds up_next.html — "what to read next" recommender over the TBR.
# Data: .rec_full.json (rating, source, avail, spice, series, tags, pages, slug, readers)
#       .ae.json (audiobook hours), .ml.json (AI vibe + picks, refreshed weekly)
# Covers are fetched live at page load via the Cloudflare worker (like the quiz).
import json, os, datetime

data = json.load(open('.rec_full.json'))
audio = json.load(open('.ae.json')).get('audio', {})
for b in data:
    b['hrs'] = audio.get(str(b['id']))

RECENT = [
    {"t": "Archer's Voice", "a": "Mia Sheridan"}, {"t": "28 Summers", "a": "Elin Hilderbrand"},
    {"t": "Instructions for Dancing", "a": "Nicola Yoon"}, {"t": "The Paradise Problem", "a": "Christina Lauren"},
    {"t": "Twenty Years Later", "a": "Charlie Donlea"},
]
BAKED = {
  "vibe": "Emotional, character-driven contemporary romance with an angsty, bittersweet edge — plus a soft spot for the occasional twisty thriller.",
  "picks": [
    {"id": 2513956, "reason": "Reflective, melancholic and quietly devastating — the bittersweet register your last reads keep circling, from an author barely anyone's found."},
    {"id": 1195040, "reason": "Dark, emotional and intense — leans into the angsty ache without going soft."},
    {"id": 1933803, "reason": "Hopeful, found-family emotional romance echoing 28 Summers' reflective heart."},
    {"id": 2182766, "reason": "Balances raw vulnerability with humour — bridges your romance and rom-com moods."},
    {"id": 1465502, "reason": "Emotional thriller-romance with dark suspense, for the twisty side of your taste."},
  ],
}
WORKER = "https://lucky-cloud-343c.xenia-9cc.workers.dev"
ALL_TBR_LIST = 471213
UP_NEXT_LIST = 465056   # Xenia's hand-curated "Up Next" list on Hardcover; fetched live each page load

# Baked "Something completely different" — deterministic anti-vibe fallback for the
# web (non-Cowork) view: light/funny/low-angst books, the opposite of the usual reads.
# Live in Cowork this is replaced by an AI pick; refreshed weekly via .ml.json if present.
_LIGHT = ('funny', 'humor', 'humour', 'lighthearted', 'light-hearted', 'rom-com', 'romantic comedy',
          'comedy', 'cozy', 'feel-good', 'feel good', 'heartwarming', 'banter', 'cute', 'wholesome', 'whimsical')
_HEAVY = ('angst', 'sad', 'grief', 'dark', 'heartbreaking', 'tragic', 'tear', 'trauma', 'emotional')
def _has(b, kws): t = (b.get('tags') or ''); return any(k in t for k in kws)
_opp = sorted([b for b in data if b.get('rating') and b['rating'] >= 3.6 and _has(b, _LIGHT) and not _has(b, _HEAVY)],
              key=lambda b: -(b['rating'] or 0))
BAKED_OPP = {
  "vibe": "The opposite of your usual: light, funny, low-angst reads — banter over heartbreak, for when you want to flip the mood.",
  "picks": [{"id": b["id"], "reason": "Light, funny and low on angst — a palate-cleanser from your usual emotional reads."} for b in _opp[:5]],
}

if os.path.exists('.ml.json'):
    try:
        _ml = json.load(open('.ml.json'))
        if _ml.get('recent'): RECENT = _ml['recent']
        if _ml.get('vibe') and _ml.get('picks'): BAKED = {"vibe": _ml['vibe'], "picks": _ml['picks']}
        if _ml.get('opp_vibe') and _ml.get('opp_picks'): BAKED_OPP = {"vibe": _ml['opp_vibe'], "picks": _ml['opp_picks']}
    except Exception: pass

CONT = {}
if os.path.exists('.continue.json'):
    try: CONT = json.load(open('.continue.json'))
    except Exception: pass

# Abonnements-budget (timer brugt/tilbage). Skrives af pipelinen fra BookBeat +
# Spotify. Mangler filen, falder siden tilbage til ren pris-prioritering.
BUDGET = {}
if os.path.exists('.budget.json'):
    try:
        BUDGET = json.load(open('.budget.json'))
        # dage tilbage af BookBeat-perioden udregnes friskt ved hver build
        pe = (BUDGET.get('bb') or {}).get('periodEnd')
        if pe:
            d = (datetime.date.fromisoformat(pe) - datetime.date.today()).days
            BUDGET['bb']['daysLeft'] = max(0, d)
    except Exception: BUDGET = {}

slim = [{"i": b["id"], "t": b["title"], "a": b["author"], "s": b["source"], "av": b["avail"],
         "r": round(b["rating"], 2) if b["rating"] else None, "hrs": b["hrs"], "p": b.get("pages"),
         "sp": b["spice"], "se": b["series"], "sn": b["snum"], "d": b["dateAdded"], "lb": b["libby"],
         "rd": b["readers"], "tg": b["tags"], "sl": b["slug"]} for b in data]
PAYLOAD = json.dumps({"books": slim, "recent": RECENT, "baked": BAKED, "bakedOpp": BAKED_OPP, "cont": CONT, "worker": WORKER, "list": ALL_TBR_LIST, "upnext": UP_NEXT_LIST, "budget": BUDGET}, ensure_ascii=False)

HTML = r'''<!DOCTYPE html><html lang="da"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Up Next — from your TBR</title><link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin><link href="https://fonts.googleapis.com/css2?family=Instrument+Sans:wght@400;500;600;700&family=Newsreader:opsz,wght@6..72,400;6..72,600&display=swap" rel="stylesheet"><style>
:root{color-scheme:light;--paper:#f5f1e9;--card:#fff;--line:#e7dfd0;--ink:#2b2620;--ink2:#6b6257;--acc:#8a5a14;--ok:#1f7a3d;--warn:#a16207;--none:#6b6257;--serif:"Newsreader",Georgia,"Times New Roman",serif;--sans:"Instrument Sans",-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif}
*{box-sizing:border-box}
body{margin:0;background:var(--paper);color:var(--ink);font:15px/1.5 var(--sans)}
.tabs{display:flex;gap:4px;border-bottom:1px solid var(--line);margin:0 0 20px}.tabs a{padding:10px 14px;min-height:44px;display:flex;align-items:center;text-decoration:none;color:var(--ink2);font-weight:600;font-size:14px;border-bottom:2px solid transparent;margin-bottom:-1px}.tabs a[aria-current=page]{color:var(--ink);border-bottom-color:var(--ink)}
.wrap{max-width:1120px;margin:0 auto;padding:24px 18px 60px}
h1{font-family:var(--serif);font-weight:600;font-size:36px;line-height:1.1;margin:0 0 4px;letter-spacing:-.01em}
h2{font-family:var(--serif);font-weight:600;font-size:24px;line-height:1.2;margin:34px 0 4px;color:var(--ink)}
.h2sub{color:var(--ink2);font-size:13px;margin:0 0 14px}
.sub{color:var(--ink2);margin:0 0 10px;font-size:13px}
a{color:inherit}
:focus-visible{outline:2px solid var(--acc);outline-offset:2px}
.status{display:flex;flex-wrap:wrap;gap:6px 18px;align-items:baseline;color:var(--ink2);font-size:13px;margin:0 0 18px}
.status b{color:var(--ink);font-weight:600}
.status details{display:inline}.status summary{cursor:pointer;color:var(--acc);font-weight:600}
.budget{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:12px 14px;margin:8px 0 0;font-size:13px;line-height:1.65;color:var(--ink);flex-basis:100%}
.budget .bhdr{font-weight:700;margin-bottom:4px}
.budget .brec{margin-top:7px;padding-top:7px;border-top:1px dashed var(--line);color:var(--ink2)}
/* hero: eneste tonede flade */
.hero{display:flex;gap:18px;background:#fbf0dc;border:1px solid #ecd9ae;border-radius:16px;padding:18px 20px;margin:0 0 22px}
.hero .hcov,.hero .hph{width:104px;height:156px;object-fit:cover;border-radius:8px;border:1px solid var(--line);background:#f0e8d8;flex:none}
.hbody{display:flex;flex-direction:column;min-width:0;flex:1}
.hlbl,.lbl{font-size:12px;font-weight:700;letter-spacing:.06em;text-transform:uppercase;color:var(--acc)}
.lbl .note{font-weight:500;text-transform:none;letter-spacing:0;color:var(--ink2)}
.htitle{font-family:var(--serif);font-size:24px;font-weight:600;line-height:1.2;margin-top:4px}
.htitle a{text-decoration:none}.htitle a:hover{text-decoration:underline}
.hau{color:var(--ink2);font-size:13px;margin:2px 0 8px}
.hwhy{font-size:15px;color:var(--ink);line-height:1.5}
/* kort: flade, hvide */
.cards{display:grid;grid-template-columns:repeat(auto-fill,minmax(min(100%,340px),1fr));gap:14px}
.card{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:16px;display:flex;gap:14px}
.card .body{display:flex;flex-direction:column;flex:1;min-width:0}
.cov,.ph{width:74px;height:111px;object-fit:cover;border-radius:6px;border:1px solid var(--line);background:#f0e8d8;flex:none}
.ph{display:flex;align-items:flex-end;padding:6px;font-family:var(--serif);font-size:12px;line-height:1.15;font-weight:600;color:#4a3f2c;overflow:hidden}
.hero .hph{font-size:14px;padding:9px}
.row .rcov,.row .rph{width:42px;height:63px;border-radius:4px;border:1px solid var(--line);flex:none}
.row .rph{display:block;padding:0;font-size:0}
.lblrow{margin-bottom:3px}
.bt{font-family:var(--serif);font-size:18px;font-weight:600;line-height:1.2}
.bt a{text-decoration:none}.bt a:hover{text-decoration:underline}
.au{color:var(--ink2);font-size:13px;margin-bottom:6px}
.why{font-size:14px;color:var(--ink);line-height:1.5}
.upnextwrap .why{display:-webkit-box;-webkit-line-clamp:6;-webkit-box-orient:vertical;overflow:hidden}
.meta{display:flex;flex-wrap:wrap;gap:4px 12px;align-items:center;margin-top:9px;font-size:13px;color:var(--ink2)}
.star{color:var(--ink);font-weight:600}
.st{display:inline-flex;align-items:center;gap:6px;font-weight:600;color:var(--ink)}
.st i{width:8px;height:8px;border-radius:50%;background:var(--none);display:inline-block}
.st-now i{background:var(--ok)}.st-short i{background:var(--warn)}.st-long i{background:var(--none);opacity:.55}.st-none i{background:transparent;border:1.5px solid var(--none)}
.acts{display:flex;gap:8px;flex-wrap:wrap;margin-top:auto;padding-top:12px}
.btn{font:inherit;font-size:14px;font-weight:600;min-height:36px;padding:6px 16px;border-radius:999px;border:1px solid var(--ink);background:var(--ink);color:#fff;cursor:pointer}
.btn:hover{background:#000}.btn:disabled{opacity:.65;cursor:default}
.btn.ghost{background:transparent;color:var(--ink);border-color:#cfc4ae}.btn.ghost:hover{background:#efe8d9}
/* filtre */
.controls{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:14px 16px}
.searchrow{display:flex;gap:10px;align-items:center}
input[type=search],select,input[type=number]{font:inherit;padding:8px 10px;border:1px solid #cfc4ae;border-radius:10px;background:#fff;color:var(--ink)}
input[type=search]{flex:1;min-width:0}
.quick{display:flex;flex-wrap:wrap;gap:8px;margin-top:12px;align-items:center}
.tg{font:inherit;font-size:13px;font-weight:600;min-height:34px;border:1px solid #cfc4ae;background:#fff;color:var(--ink2);border-radius:999px;padding:5px 13px;cursor:pointer}
.tg[aria-pressed=true]{background:var(--ink);border-color:var(--ink);color:#fff}
details.more{margin-top:12px;border-top:1px solid var(--line);padding-top:10px}
details.more>summary{cursor:pointer;font-weight:600;font-size:14px;color:var(--acc)}
.grp{margin-top:14px}.grp h3{font-size:12px;letter-spacing:.06em;text-transform:uppercase;color:var(--ink2);margin:0 0 6px;font-weight:700}
.grp .row2{display:flex;flex-wrap:wrap;gap:8px;align-items:center}
.grp .hint{font-size:12px;color:var(--ink2);margin-top:6px}
input[type=range]{width:200px;accent-color:var(--ink)}
.rad{display:flex;flex-wrap:wrap;gap:6px 14px;font-size:14px}.rad label{display:flex;gap:6px;align-items:center;cursor:pointer}
.active{display:flex;flex-wrap:wrap;gap:8px;align-items:center;margin-top:12px}
.achip{display:inline-flex;gap:6px;align-items:center;background:#efe8d9;border-radius:999px;padding:3px 6px 3px 12px;font-size:13px}
.achip button{font:inherit;border:0;background:none;cursor:pointer;color:var(--ink2);min-width:24px;min-height:24px;font-size:15px;line-height:1}
.linkbtn{font:inherit;font-size:13px;font-weight:600;border:0;background:none;color:var(--acc);cursor:pointer;padding:4px}
.rowcount{color:var(--ink2);font-size:13px;margin:14px 0 6px}
.chips{display:flex;flex-wrap:wrap;gap:6px;margin:10px 0 0}.chip{font-size:12px;padding:4px 11px;border-radius:999px;background:transparent;border:1px solid #d9cdb8;color:var(--ink2);cursor:pointer}.chip:hover{background:#efe8d9}
.row{display:flex;gap:11px;padding:11px 4px;border-bottom:1px solid var(--line);align-items:center}
.row .rcov{object-fit:cover;background:#f0e8d8}.row .rcov.blank{visibility:hidden}
.row .ti{font-weight:600;overflow-wrap:anywhere}.row .ti a{text-decoration:none}.row .ti a:hover{text-decoration:underline}
.row .ra{color:var(--ink2);font-size:13px;font-weight:400}.tagline{color:var(--ink2);font-size:12px;margin-top:2px}
.row .rrank{color:var(--ink2);font-size:12px;min-width:22px;flex:none}
.row .rmid{flex:1;min-width:0}
.row .rmeta{text-align:right;flex:none;display:flex;flex-direction:column;gap:2px;align-items:flex-end;font-size:13px;color:var(--ink2)}
.foot{margin-top:34px;color:var(--ink2);font-size:12px;border-top:1px solid var(--line);padding-top:12px}
/* Din Up Next + serie-række */
.upnextwrap{margin:0 0 6px}
.unhead{display:flex;align-items:flex-end;gap:10px}
.unhead .arrows{margin-left:auto;display:flex;gap:6px}
.arrow{font:inherit;width:36px;height:36px;border-radius:50%;border:1px solid #cfc4ae;background:#fff;cursor:pointer;font-size:16px;color:var(--ink)}
.arrow:hover{background:#efe8d9}
.slider{display:flex;gap:12px;margin-top:10px;overflow-x:auto;scroll-snap-type:x mandatory;padding:2px 2px 10px;-webkit-overflow-scrolling:touch;scrollbar-width:thin;scrollbar-color:#cfc4ae transparent}
.slider .card{flex:0 0 min(300px,82%);max-width:300px;scroll-snap-align:start}
@media (max-width:560px){
 h1{font-size:28px}h2{font-size:21px}
 .hero{flex-direction:column;gap:12px}.hero .hcov,.hero .hph{width:88px;height:132px}
 .btn,.tg,.arrow{min-height:44px}.tg{padding:8px 14px}.achip button{min-width:32px;min-height:32px}
 .searchrow input{min-height:44px}
 .row{flex-wrap:wrap;align-items:flex-start}
 .row .rmeta{flex-basis:100%;flex-direction:row;flex-wrap:wrap;gap:4px 12px;align-items:center;text-align:left;margin-top:6px;padding-left:53px}
 input[type=range]{width:100%}
}
</style></head><body><div class="wrap"><nav class="tabs" aria-label="Sider"><a href="./">Quiz</a><a href="up_next.html" aria-current="page">Up Next</a></nav>
<h1>Up Next</h1>
<p class="sub" id="sub"></p>
<div class="status" id="statusline"><span>Seneste læsninger: <b id="vibe">Læser dine seneste bøger…</b></span><span id="hoursline"></span><div id="budgetbox" style="flex-basis:100%"></div></div>
<div id="serieshero"></div>
<div id="upnext"></div>

<h2>Andre forslag</h2>
<p class="h2sub">Tilfældigt trukket blandt bøger, der passer til hvert kort.</p>
<div class="cards" id="picks"></div>

<h2>Udforsk din TBR</h2>
<div class="controls">
  <div class="searchrow"><input type="search" id="fText" aria-label="Søg" placeholder="Søg stemning, trope eller titel — fx enemies to lovers, mørk, sjov"></div>
  <div class="quick" role="group" aria-label="Hurtigfiltre">
    <button type="button" class="tg" id="qNow" aria-pressed="false">Klar nu</button>
    <button type="button" class="tg" id="qFree" aria-pressed="false">Gratis</button>
    <button type="button" class="tg" id="qFit" aria-pressed="false">Passer i mine timer</button>
    <button type="button" class="tg" id="qDeep" aria-pressed="false">Deep cuts</button>
    <button type="button" class="tg" id="qSeries" aria-pressed="false">Serie-starter</button>
  </div>
  <details class="more" id="moreBox"><summary>Flere filtre</summary>
    <div class="grp"><h3>Adgang</h3><div class="row2" id="fSrc" role="group" aria-label="Kilde"></div><div class="hint">Vælg en eller flere kilder. "Gratis" = ejet eller Libby.</div></div>
    <div class="grp"><h3>Længde</h3><div class="row2"><label for="fHours">Max timer: <b id="fhVal">alle</b></label><input type="range" id="fHours" min="4" max="30" step="1" value="30"></div><div class="hint" id="fitHint"></div></div>
    <div class="grp"><h3>Bedømmelse</h3><div class="row2" id="fRate" role="group" aria-label="Min. bedømmelse"></div></div>
    <div class="grp"><h3>Spice</h3><div class="row2" id="fSpice" role="group" aria-label="Min. spice"></div></div>
    <div class="grp"><h3>Sortering</h3><div class="rad" id="fSort"></div></div>
    <div class="grp"><h3>Forslag til søgning</h3><div class="chips" id="chips"></div></div>
  </details>
  <div class="active" id="active"></div>
</div>
<div class="rowcount" id="rc" aria-live="polite"></div>
<div id="results"></div>
<div class="foot" id="foot"></div>
</div>
<script>
const P=__DATA__; const DATA=P.books; let RECENT=P.recent; const BAKED=P.baked; const BAKED_OPP=P.bakedOpp||{picks:[]}; const CONT=P.cont||{}; const COV={};
const has=(b,...kw)=>{const t=(b.tg||'');return kw.some(k=>t.includes(k));};
const availNow=b=>b.av==='now'; const availSoon=b=>b.av==='now'||b.av==='short';
const srcBadge=b=>`<span class="badge src-${b.s}">${b.s}</span>`;
const avLabel={now:'Available now',short:'Short wait',long:'Long wait',none:'Not available'};
const avBadge=b=>`<span class="pill av-${b.av}">${avLabel[b.av]}</span>`;
const link=b=>b.sl?`<a href="https://hardcover.app/books/${b.sl}" target="_blank" rel="noopener">${b.t}</a>`:b.t;
const rat=b=>b.r!=null?`<span class="star">★ ${b.r.toFixed(2)}</span>`:'';
const lenB=b=>b.hrs?`<span class="badge">🎧 ${b.hrs} hrs</span>`:(b.p?`<span class="badge">${b.p} pp</span>`:'');
const readB=b=>b.rd!=null?`<span class="badge">${b.rd.toLocaleString()} readers</span>`:'';
const covImg=(b,cls)=>{const u=COV[b.i];return u?`<img class="${cls}" src="${u}" alt="" loading="lazy" onerror="this.classList.add('blank')">`:`<img class="${cls} blank" alt="">`;};
const dc=b=>(b.r||3.5)+0.4*Math.max(0,3-Math.log10((b.rd||300)+10));
const byId=Object.fromEntries(DATA.map(b=>[b.i,b]));
// Startable = safe to recommend as an entry point: a standalone, a #1 (or prequel),
// or the legitimate next-in-series she can pick up (present in CONT). A book that's
// #2+ in a series she hasn't caught up on is NOT startable, so it never gets suggested.
const startable=b=>!(b.sn>1)||!!CONT[b.i];

// ── Kilde-omkostning ─────────────────────────────────────────────────────────
// owned = Lokal/Audible (ejet, 0 kr). lib = Libby (gratis, men lånekvote/kø).
// inc = Spotify (12 gratis timer/md i Premium). paid = BookBeat (129 kr/md).
const costTier=b=>{
  if(b.s==='Lokal'||b.s==='Audible') return 'owned';
  if(b.s==='Libby') return 'lib';
  if(b.s==='Spotify') return 'inc';
  if(b.s==='BookBeat') return 'paid';
  return 'none';
};
// ── Kilde-filter, hurtigfiltre og timer ───────────────────────────────────────
const srcGroup=b=>(b.s==='Lokal'||b.s==='Audible')?'Ejet':b.s;
const SRCS=['BookBeat','Spotify','Libby','Ejet','Ingen'];
let SRCSEL=new Set(SRCS);
try{const sv=JSON.parse(localStorage.getItem('un_src')||'null');if(Array.isArray(sv)){const f=sv.filter(x=>SRCS.includes(x));if(f.length)SRCSEL=new Set(f);}}catch(e){}
const srcOK=b=>SRCSEL.has(srcGroup(b));
const F={now:false,free:false,fit:false,deep:false,series:false,rate:0,spice:0,maxh:30,sort:'useit',txt:''};
const fmt=n=>String(Math.round(n*10)/10).replace('.',',');
function remFor(k){const o=k==='BookBeat'?BUD.bb:(k==='Spotify'?BUD.sp:null);return o?Math.max(0,Math.round(((o.limit||0)-(o.used||0))*10)/10):null;}
// Passer i mine timer: BookBeat/Spotify-bøger må ikke være længere end timerne tilbage på netop den kilde.
// Ejede bøger og Libby er ikke begrænset af et timebudget.
// Ukendt længde skaetzes (sider/30 eller gennemsnit) - aldrig 'passer' bare fordi tallet mangler.
const estHrs=b=>b.hrs||(b.p?b.p/30:(BUD.avgBookHours||12.5));
const fitsOwn=b=>{const r=(b.s==='BookBeat'||b.s==='Spotify')?remFor(b.s):null;return r==null||estHrs(b)<=r+0.25;};
function mkTg(label,pressed,fn){const x=document.createElement('button');x.type='button';x.className='tg';x.setAttribute('aria-pressed',pressed?'true':'false');x.textContent=label;x.onclick=fn;return x;}
function renderSrcFilter(){const h=document.getElementById('fSrc');if(!h)return;h.innerHTML='';const all=SRCSEL.size===SRCS.length;
  h.appendChild(mkTg('Alle',all,()=>{SRCSEL=new Set(SRCS);saveSrc();}));
  SRCS.forEach(k=>{h.appendChild(mkTg(k==='Ejet'?'Ejet (Lokal/Audible)':k,!all&&SRCSEL.has(k),()=>{
    if(SRCSEL.size===SRCS.length){SRCSEL=new Set([k]);}else if(SRCSEL.has(k)){SRCSEL.delete(k);if(!SRCSEL.size)SRCSEL=new Set(SRCS);}else{SRCSEL.add(k);}saveSrc();}));});}
function saveSrc(){try{localStorage.setItem('un_src',JSON.stringify([...SRCSEL]));}catch(e){}renderSrcFilter();renderPicks();renderNext();update();}
const costRank={owned:0,lib:1,inc:2,paid:3,none:4};
const costLabel={owned:'💰 Ejet',lib:'💰 Gratis (Libby)',inc:'💰 Spotify-timer',paid:'💳 BookBeat',none:''};
const costPill=b=>{const c=costTier(b);return costLabel[c]?`<span class="badge cost-${c}">${costLabel[c]}</span>`:'';};
// Gratis og klar til at starte nu: ejet, eller Libby-eksemplar der er ledigt.
const freeNow=b=>costTier(b)==='owned'||(b.s==='Libby'&&b.av==='now');
// Spotify har kun få timer tilbage: en bog der er længere end resten kan ikke nås i denne periode.
const spLeft=()=>BUD.sp?Math.max(0,(BUD.sp.limit||0)-(BUD.sp.used||0)):null;
const spFits=b=>{if(b.s!=='Spotify')return true;const r=spLeft();return r==null||estHrs(b)<=r+0.25;};
const lbDays=b=>{const m=/(\d+)\s*dage/.exec(b.lb||'');return m?+m[1]:0;};

// ── Budget: brug-det-eller-mist-det ──────────────────────────────────────────
// Betalte timer nulstilles hver periode — ubrugte timer er spildte penge.
// Ejede boeger udloeber aldrig, saa de er bufferen, ikke foersteprioriteten.
//
// Prioritering = EDF (earliest deadline first). Timerne konkurrerer om ET
// faelles lyttetempo, saa den storste bunke er IKKE altid den rigtige at jage:
// hvis en mindre bunke udloeber foerst, doer den mens man jager den store.
// Derfor vinder den kilde der fornyes foerst — men kun for de timer hun
// realistisk NAAR at bruge (atRisk). Timer over kapaciteten er tabt uanset
// hvad, og skal ikke traekke valget.
const BUD=P.budget||{};
const CAP=(+BUD.dailyCapacity>0)?+BUD.dailyCapacity:2.0;   // t/dag hun faktisk lytter
// raw = det gamle maal: hvor mange t/dag hun SKULLE lytte for at bruge alt.
// Bruges stadig til at afgoere OM der er betalt tid i overskud.
// Mangler daysLeft (fx uparsebar periodEnd), saa antag 30 dage — en manglende
// dato skal IKKE tolkes som "udloeber i morgen" og kapre hele rangeringen.
const dl=d=>Number.isFinite(+d)&&+d>=0?Math.max(1,+d):30;
const rawUrg=(rem,d)=>rem<=0?-99:rem/dl(d);
const urgCalc=(rem,d)=>{
  if(rem<=0) return -99;                       // opbrugt
  const dd=dl(d);
  const atRisk=Math.min(rem,CAP*dd);           // timer der realistisk kan reddes
  if(atRisk<1) return 0.05;                    // for lidt paa spil til at styre valget
  return (10/dd)*Math.min(1,atRisk/CAP);       // EDF, daempet hvis under én dags lytning
};
const urg=src=>{
  if(src==='BookBeat'){const b=BUD.bb;if(!b)return 1;return urgCalc((b.limit||0)-(b.used||0),b.daysLeft);}
  if(src==='Spotify'){const s=BUD.sp;if(!s)return 0.6;return urgCalc((s.limit||0)-(s.used||0),s.daysLeft);}
  return 0;
};
// Rangering: hoejest spild-risiko foerst. Libby-ledig faar en fast lille
// hastesag (laanekvoten nulstilles ogsaa). Ejet = 0 (aldrig spildt).
const urgency=b=>{
  const c=costTier(b);
  if(c==='paid') return urg('BookBeat');
  if(c==='inc')  return spFits(b)?urg('Spotify'):-5;   // passer ikke i de resterende timer
  if(c==='lib')  return b.av==='now'?0.5:(b.av==='short'?0.2:0.05);
  if(c==='owned')return 0;
  return -50;
};
function budgetBanner(){
  if(!BUD.bb&&!BUD.sp) return '';
  const parts=[]; let push=null, pushU=-1, levelU=-99, pushDays=0;
  const line=(navn,o,srcKey)=>{
    const rem=Math.round(((o.limit||0)-(o.used||0))*10)/10, d=dl(o.daysLeft), u=urg(srcKey);
    const naar=Math.min(rem,CAP*d);               // hvor meget hun reelt naar
    const spildt=Math.round((rem-naar)*10)/10;
    parts.push(`<b>${navn}</b> ${o.used||0} / ${o.limit} t brugt · ${rem} t tilbage på ${d} dage`
      +(rem>0?` · når ca. <b>${Math.round(naar*10)/10} t</b> i dit tempo${spildt>0.5?` (${spildt} t udløber uanset hvad)`:''}`:' · <b>loft nået</b>'));
    if(u>pushU){pushU=u;push=navn;pushDays=d;}
    levelU=Math.max(levelU,rawUrg(rem,d));
  };
  if(BUD.bb) line('BookBeat',BUD.bb,'BookBeat');
  if(BUD.sp) line('Spotify',BUD.sp,'Spotify');
  if(BUD.bb&&BUD.bb.nextLimit&&BUD.bb.nextLimit!==BUD.bb.limit)
    parts.push(`<span style="color:#9a3412">Loftet falder til ${BUD.bb.nextLimit} t fra ${BUD.bb.periodEnd}</span>`);
  // levelU (raa t/dag) afgoer OM der er betalt tid i overskud — samme 0.5-taerskel
  // som et ledigt Libby-laan. pushU (EDF) afgoer HVILKEN kilde der naevnes.
  const rec = pushU<=0
    ? `Alle betalte timer er brugt — <b>gå efter gratis kilder</b> (ejet + Libby) resten af perioden.`
    : levelU<0.5
      ? `Kun lidt betalt tid tilbage på ${push} — <b>bland</b>: tag den med, men et ledigt Libby-lån er lige så presserende.`
      : `Du har betalte timer i overskud — <b>brug ${push} først</b>: den fornyes om ${pushDays} dage, så dens timer dør før de andres. Gem de ejede bøger til bufferen.`;
  return `<div class="budget"><div class="bhdr">💳 Dine lyttetimer</div>${parts.map(p=>`<div>${p}</div>`).join('')}<div class="brec">${rec}</div></div>`;
}

// Everyday picks: uniform-random draw from books that FIT the card (equal odds, popular or
// obscure). Only Deep cut and Hype check deliberately lean. Light rating floors keep out duds.
const PICKS=[
 {k:'useit',lb:'Brug dine betalte timer',pool:()=>{const order=['BookBeat','Spotify'].sort((a,b)=>urg(b)-urg(a));
   for(const best of order){if(urg(best)<=0)continue;
     const pl=DATA.filter(b=>b.s===best&&b.r&&b.r>=3.4&&startable(b)&&spFits(b)&&srcOK(b));
     if(pl.length)return pl;}
   return [];},
  why:b=>{const bd=b.s==='BookBeat'?BUD.bb:BUD.sp;const rem=bd?((bd.limit||0)-(bd.used||0)):null;
   return `Du har ${rem!=null?fmt(rem)+' t ':''}tilbage på ${b.s} i denne periode. Timerne nulstilles, uanset om du bruger dem, så start her før de ejede bøger.`;}},
 {k:'free',lb:'Gratis nu',note:'Libby eller ejet',pool:()=>DATA.filter(b=>freeNow(b)&&b.r&&b.r>=3.4&&startable(b)),why:b=>b.s==='Libby'?`Ledig på Libby nu. Det koster ingenting, så lån den, før køen vender tilbage.`:`Du ejer den allerede (${b.s}): ingen kø og ingen abonnementstimer.`},
 {k:'nowait',lb:'Ingen ventetid',pool:()=>DATA.filter(b=>availNow(b)&&b.r&&b.r>=3.5&&startable(b)),why:b=>`Klar på ${b.s} lige nu uden venteliste. Start den, når du vil.`},
 {k:'quick',lb:'Kort lytning',pool:()=>DATA.filter(b=>availNow(b)&&b.hrs&&b.hrs<=9&&b.r&&b.r>=3.4&&startable(b)),why:b=>`Kun ${fmt(b.hrs)} timer og klar nu. Nem at gennemføre.`},
 {k:'wreck',lb:'Knus mig',pool:()=>DATA.filter(b=>b.r&&b.r>=3.8&&startable(b)&&has(b,'sad','angst','emotional','grief','heartbreaking','tear')),why:b=>`Følelsesladet og lidt ødelæggende, til når du vil mærke noget.`},
 {k:'cozy',lb:'Hyggeaften',pool:()=>DATA.filter(b=>availNow(b)&&startable(b)&&has(b,'cute','lighthearted','funny','cozy','heartwarming','feel-good','small town','wholesome')),why:b=>`Let og trøstende, og klar nu. Skænk noget at drikke og slap af.`},
 {k:'series',lb:'Start en serie',pool:()=>DATA.filter(b=>b.sn===1&&b.r&&b.r>=3.5),why:b=>`${b.se} #1: begynd på en ny serie.`},
 {k:'cont',lb:'Fortsæt en serie',pool:()=>DATA.filter(b=>CONT[b.i]),why:b=>{const c=CONT[b.i];const lead=(c.er!=null)?`Du gav “${c.et}” ${c.er}★`:`Du har læst “${c.et}”`;return `${lead}. Tag ${b.se||'serien'} op igen (#${c.pos}).`;}},
 {k:'deep',lb:'Deep cut',note:'vægtet mod mindre kendte',pool:()=>DATA.filter(b=>b.r&&b.r>=4.0&&b.rd!=null&&b.rd<4000&&startable(b)),why:b=>`Kun ${b.rd?b.rd.toLocaleString('da-DK'):'få'} læsere, men ${b.r} i rating: en skjult perle.`},
 {k:'backlog',lb:'Længst på din TBR',pool:()=>DATA.filter(b=>b.d&&b.r&&startable(b)).sort((a,b)=>a.d.localeCompare(b.d)).slice(0,30),why:b=>`Været på din liste siden ${b.d}. Måske er tiden kommet.`},
 {k:'spicy',lb:'Spicy valg',pool:()=>DATA.filter(b=>b.sp&&b.sp>=4&&availNow(b)&&startable(b)),why:b=>`Spice ${b.sp}/5 og klar nu. Skru op for varmen.`},
 {k:'hype',lb:'Hype check',note:'vægtet mod populære',pool:()=>DATA.filter(b=>b.rd!=null&&startable(b)).sort((a,b)=>b.rd-a.rd).slice(0,25),why:b=>`Blandt de mest læste på din liste, med ${b.rd?b.rd.toLocaleString('da-DK'):'mange'} læsere. Se om hypen holder.`},
 {k:'surprise',lb:'Overrask mig',note:'helt tilfældig',pool:()=>DATA.filter(b=>b.r&&startable(b)),why:b=>`Et helt tilfældigt træk fra hele din TBR, populær eller obskur med lige odds.`},
];
const idx={};
const stLabel={now:'Klar nu',short:'Kort ventetid',long:'Lang ventetid',none:'Ingen adgang'};
const stHTML=b=>b.s?`<span class="st st-${b.av||'none'}"><i></i>${stLabel[b.av]||stLabel.none}</span>`:'';
const srcTxt=b=>{const c=costTier(b);const m={owned:'Ejet',lib:'Libby · gratis',inc:'Spotify · inkluderet',paid:'BookBeat · inkluderet'};return m[c]||(b.s&&b.s!=='Ingen'?b.s:'');};
const hrsTxt=b=>b.hrs?`${fmt(b.hrs)} t`:(b.p?`${b.p} s.`:'');
function cover(b,cls){const u=COV[b.i];
  if(u)return `<img class="${cls}" src="${u}" alt="" loading="lazy" onerror="this.classList.add('blank')">`;
  let h=0;const t=b.t||'';for(let i=0;i<t.length;i++)h=(h*31+t.charCodeAt(i))%360;
  const pc=cls==='rcov'?'rcov rph':(cls==='hcov'?'ph hph':'ph');
  return `<div class="${pc}" style="background:hsl(${h} 38% 86%)">${cls==='rcov'?'':(t.length>38?t.slice(0,36)+'…':t)}</div>`;}
const readBtn=b=>`<button type="button" class="btn readbtn" data-id="${b.i}">Læs nu</button>`;
function metaLine(b){return `${b.r!=null?`<span class="star">★ ${b.r.toFixed(2).replace('.',',')}</span>`:''}${stHTML(b)}${b.hrs?`<span>${hrsTxt(b)}</span>`:''}${srcTxt(b)?`<span>${srcTxt(b)}</span>`:''}${b.sp?`<span>🌶 ${b.sp}</span>`:''}`;}
function card(label,b,why,cyc,ai,note){return `<div class="card">${cover(b,'cov')}<div class="body">
  <div class="lblrow"><span class="lbl">${label}${note?` <span class="note">· ${note}</span>`:''}</span></div>
  <div class="bt">${link(b)}</div>
  <div class="au">${b.a||''}${b.se?` · ${b.se}${b.sn?(' #'+b.sn):''}`:''}</div>
  <div class="why">${why||''}</div>
  <div class="meta">${metaLine(b)}</div>
  <div class="acts">${readBtn(b)}${cyc||''}</div>
</div></div>`;}
function renderPicks(){
 const host=document.getElementById('picks');host.innerHTML='';
 const ml=window._ml;
 if(ml&&ml.picks){const list=ml.picks.filter(pk=>byId[pk.id]&&startable(byId[pk.id])&&srcOK(byId[pk.id]));
   if(list.length){ if(window._mlIdx==null)window._mlIdx=Math.floor(Math.random()*list.length);
     const pk=list[window._mlIdx%list.length];
     const el=document.createElement('div');el.innerHTML=card('Din stemning',byId[pk.id],pk.reason||'',list.length>1?'<button type="button" class="btn ghost cyc" id="mlcyc">↻ Træk ny</button>':'',true,'ud fra dine seneste læsninger');host.appendChild(el.firstChild);}}
 const opp=window._opp;
 if(opp&&opp.picks){const list=opp.picks.filter(pk=>byId[pk.id]&&startable(byId[pk.id])&&srcOK(byId[pk.id]));
   if(list.length){ if(window._oppIdx==null)window._oppIdx=Math.floor(Math.random()*list.length);
     const pk=list[window._oppIdx%list.length];
     const el=document.createElement('div');el.innerHTML=card('Noget helt andet',byId[pk.id],pk.reason||'',list.length>1?'<button type="button" class="btn ghost cyc" id="oppcyc">↻ Træk ny</button>':'',true,'det modsatte af dine seneste læsninger');host.appendChild(el.firstChild);}}
 PICKS.forEach(p=>{const pool=p.pool().filter(srcOK);if(!pool.length)return;
   if(idx[p.k]==null)idx[p.k]=Math.floor(Math.random()*pool.length);
   const b=pool[Math.min(idx[p.k],pool.length-1)];
   const el=document.createElement('div');el.innerHTML=card(p.lb,b,p.why(b),`<button type="button" class="btn ghost cyc" data-k="${p.k}">↻ Træk ny</button>`,false,p.note||'');host.appendChild(el.firstChild);});
 const mb=document.getElementById('mlcyc');if(mb)mb.onclick=()=>{const list=window._ml.picks.filter(pk=>byId[pk.id]&&startable(byId[pk.id])&&srcOK(byId[pk.id]));window._mlIdx=(window._mlIdx+1)%list.length;renderPicks();};
 const ob=document.getElementById('oppcyc');if(ob)ob.onclick=()=>{const list=window._opp.picks.filter(pk=>byId[pk.id]&&startable(byId[pk.id])&&srcOK(byId[pk.id]));window._oppIdx=(window._oppIdx+1)%list.length;renderPicks();};
 host.querySelectorAll('.cyc[data-k]').forEach(btn=>btn.onclick=()=>{const p=PICKS.find(x=>x.k===btn.dataset.k);const pool=p.pool().filter(srcOK);
   idx[p.k]=Math.floor(Math.random()*pool.length);renderPicks();});
}
function applyML(vibe,picks){window._ml={vibe:vibe,picks:picks};window._mlIdx=null;
 const v=document.getElementById('vibe');if(v)v.textContent=vibe||'';renderPicks();}
function applyOpp(vibe,picks){window._opp={vibe:vibe,picks:picks};window._oppIdx=null;renderPicks();}
document.addEventListener('click',async e=>{
 const t=e.target.closest('.readbtn');
 if(t){t.disabled=true;t.textContent='Starter…';
   try{const r=await fetch(P.worker,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({action:'add_currently_reading',book_id:+t.dataset.id})});
     const d=await r.json();if(d&&!d.error&&!d.errors){t.textContent='✓ Læser nu';}else{t.textContent='Kunne ikke opdatere';t.disabled=false;}}
   catch(err){t.textContent='Kunne ikke opdatere';t.disabled=false;}
   return;}
 const a=e.target.closest('.arrow');
 if(a){const s=a.closest('.upnextwrap').querySelector('.slider');s.scrollBy({left:(+a.dataset.dir)*300,behavior:'smooth'});}
});
async function loadML(){
 const cands=DATA.filter(b=>b.r&&startable(b)).sort((a,b)=>dc(b)-dc(a)).slice(0,150).map(b=>({id:b.i,title:b.t,author:b.a,tags:(b.tg||'').split(',').slice(0,8).join(','),readers:b.rd,rating:b.r}));
 // Uden for Cowork: hent vibe'en live via workeren, som selv slår dine seneste
 // finishes op og cacher svaret indtil du har læst noget nyt. Fejler det, falder
 // vi tilbage til den bagte vibe fra det ugentlige build.
 if(!(window.cowork&&window.cowork.askClaude)){
   const v=document.getElementById('vibe');
   if(v)v.textContent='Reading the vibe across your recent finishes…';
   try{
     const r=await fetch(P.worker,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({action:'vibe',candidates:cands})});
     const d=await r.json();
     if(d&&d.vibe&&d.picks&&d.picks.length){
       const known=new Set(DATA.map(b=>b.i));
       const vp=d.picks.filter(p=>known.has(p.id)), op=(d.opp_picks||[]).filter(p=>known.has(p.id));
       if(d.recent&&d.recent.length)RECENT=d.recent;
       applyML(d.vibe,vp.length?vp:BAKED.picks);
       applyOpp(d.opp_vibe||BAKED_OPP.vibe,op.length?op:BAKED_OPP.picks);
       return;
     }
   }catch(e){}
   applyML(BAKED.vibe,BAKED.picks); applyOpp(BAKED_OPP.vibe,BAKED_OPP.picks); return;
 }
 document.getElementById('vibe').textContent='Reading the vibe across your last '+RECENT.length+' finishes…';
 const rl=RECENT.map(r=>`"${r.t}" by ${r.a}`).join('; ');
 const prompt=`My last ${RECENT.length} finished books, newest first: ${rl}. Work only from the candidate TBR list (JSON), favoring lesser-known DEEP CUTS (lower "readers") over obvious bestsellers, and never repeat an ID between the two lists.\n1) In ONE sentence capture the overall VIBE/mood these suggest I'm craving right now — synthesize across all of them, do NOT just list them — then pick 5 books that fit it.\n2) In ONE sentence capture the OPPOSITE mood — something completely different from these recent reads, for when I want to flip my usual pattern (e.g. flip heavy→light, romance→other genre, dark→funny) — then pick 5 books that fit that opposite.\nReturn ONLY, in exactly this structure:\nVIBE: <one sentence>\n<5 lines, each "ID :: reason it fits the vibe">\nOPPOSITE: <one sentence>\n<5 lines, each "ID :: reason it contrasts my recent reads">`;
 try{
   const res=await window.cowork.askClaude(prompt,cands);
   let txt=(res==null)?'':(typeof res==='string'?res:(res.text||res.output||res.result||(res.content?(typeof res.content==='string'?res.content:(Array.isArray(res.content)?res.content.map(c=>c&&(c.text||c.content||'')||'').join(''):'')):'')));if(!txt)txt=String(res);
   txt=txt.replace(/```[a-z]*|```/g,'').trim();
   let vibe=BAKED.vibe, oppVibe=BAKED_OPP.vibe, sec='v'; const picks=[], opicks=[];
   txt.split(/\r?\n/).map(l=>l.trim()).filter(Boolean).forEach(l=>{
     const om=l.match(/^opposite\s*[:\-]\s*(.+)/i); if(om){oppVibe=om[1].trim();sec='o';return;}
     const vm=l.match(/^vibe\s*[:\-]\s*(.+)/i); if(vm){vibe=vm[1].trim();sec='v';return;}
     const m=l.match(/(\d{2,})\s*(?:::|\||\-|:)\s*(.+)/);
     if(m){(sec==='o'?opicks:picks).push({id:parseInt(m[1]),reason:m[2].trim().replace(/^["'\s]+|["'\s]+$/g,'')});}
   });
   applyML(vibe,picks.length?picks:BAKED.picks);
   applyOpp(oppVibe,opicks.length?opicks:BAKED_OPP.picks);
 }catch(e){ applyML(BAKED.vibe,BAKED.picks); applyOpp(BAKED_OPP.vibe,BAKED_OPP.picks); }
}
async function loadCovers(){
 try{const r=await fetch(P.worker,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({action:'get_list',list_id:P.list})});
   const d=await r.json();(d.books||[]).forEach(x=>{if(x.cover)COV[x.id]=x.cover;});}catch(e){}
 renderPicks();update();renderHero(window._heroPick||null);renderUpNext(window._upnext);
}
async function loadUpNext(){
 try{const r=await fetch(P.worker,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({action:'get_list',list_id:P.upnext})});
   const d=await r.json();renderUpNext((d&&d.books)||[]);}catch(e){renderUpNext([]);}
}
async function loadNextInSeries(){
 try{const r=await fetch(P.worker,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({action:'next_in_series'})});
   const d=await r.json(); renderHero(d&&d.pick?d.pick:null);}catch(e){renderHero(null);}
}
// Din Up Next: din håndplukkede liste på Hardcover, hentet live via workeren. Vises altid (omgår pool/startable).
// Beskrivelse til Up Next-kort: Hardcover-synopsis hvis workeren leverer den, ellers bygget af tags/serie/vurdering.
function upWhy(b,x){
 const esc=t=>String(t).replace(/&/g,'&amp;').replace(/</g,'&lt;');
 let d=(x&&x.desc)?String(x.desc).replace(/<[^>]*>/g,' ').replace(/\s+/g,' ').trim():'';
 if(d){if(d.length>240)d=d.slice(0,240).replace(/\s+\S*$/,'')+'…';return esc(d);}
 const bits=[];
 const tags=(b.tg||'').split(',').map(t=>t.trim()).filter(t=>t&&!/^(fiction|romance|contemporary|medium-paced|fast-paced|slow-paced)$/i.test(t)).slice(0,5);
 if(tags.length)bits.push(esc(tags.join(' · ')));
 if(b.se)bits.push(`${b.sn?'Bind '+b.sn+' i':'Del af'} serien ${esc(b.se)}`);
 if(b.sp)bits.push(`spice ${b.sp}/5`);
 const src=srcTxt(b);
 if(b.av==='now'&&src)bits.push(`klar nu (${esc(src)})`);else if(b.s&&b.s!=='Ingen')bits.push(esc(b.s));
 return bits.length?bits.join('. ')+'.':'Ligger på din Up Next-liste på Hardcover. Ingen yderligere data om bogen endnu.';
}
function renderUpNext(list){
 window._upnext=list; const host=document.getElementById('upnext'); if(!host)return;
 if(!list||!list.length){host.innerHTML='';return;}
 list.forEach(x=>{if(x.cover)COV[x.id]=x.cover;});
 const cards=list.map(x=>{const b=byId[x.id]||{i:x.id,t:x.t,a:x.a,sl:x.hc};
   return card('Up Next',b,upWhy(b,x),'',false);}).join('');
 host.innerHTML=`<div class="upnextwrap"><div class="unhead"><div><h2 style="margin-top:6px">Din Up Next</h2><p class="h2sub" style="margin-bottom:0">Håndplukket af dig på Hardcover. Hentes live, hver gang siden åbnes.</p></div><div class="arrows"><button type="button" class="arrow" data-dir="-1" aria-label="Forrige">←</button><button type="button" class="arrow" data-dir="1" aria-label="Næste">→</button></div></div><div class="slider">${cards}</div></div>`;
}
// Næste bog: næste i en serie du er i gang med (live fra workeren). Findes den ikke, trækkes en bog fra "Brug dine betalte timer"/"Gratis".
function renderHero(pick){window._heroPick=pick;renderNext();}
function nextPool(){for(const k of ['useit','free','nowait']){const p=PICKS.find(x=>x.k===k);const pool=p?p.pool().filter(srcOK):[];if(pool.length)return {pool,p};}return {pool:[],p:null};}
function renderNext(){
 const host=document.getElementById('serieshero'); if(!host)return;
 const pick=window._heroPick; let b,why,label,cyc='';
 if(pick){
   if(pick.cover)COV[pick.id]=pick.cover;
   const onTbr=byId[pick.id];
   b=onTbr||{i:pick.id,t:pick.t,a:pick.a,sl:pick.sl,se:pick.series,sn:pick.snum};
   const f=pick.from||{}; const rated=(f.r!=null)?` (${f.r}★)`:''; const dt=f.date?(' den '+String(f.date).slice(0,10)):'';
   why=`Du har lige læst “${f.t||'den forrige bog'}”${rated}${dt}. Her er #${pick.snum} i ${pick.series}.`;
   label='Næste bog · næste i din serie';
   if(!onTbr)b=Object.assign({},b,{s:null});
 } else {
   const {pool,p}=nextPool(); if(!pool.length){host.innerHTML='';return;}
   if(window._nextIdx==null)window._nextIdx=Math.floor(Math.random()*pool.length);
   b=pool[window._nextIdx%pool.length]; why=p.why(b); label='Næste bog';
   cyc='<button type="button" class="btn ghost" id="nextcyc">↻ Træk ny</button>';
 }
 host.innerHTML=`<div class="hero">${cover(b,'hcov')}<div class="hbody">
   <div class="hlbl">${label}</div>
   <div class="htitle">${link(b)}</div>
   <div class="hau">${b.a||''}${b.se?` · ${b.se}${b.sn?(' #'+b.sn):''}`:''}</div>
   <div class="hwhy">${why}</div>
   <div class="meta">${b.s?metaLine(b):'<span>Ikke på din TBR endnu</span>'}</div>
   <div class="acts">${readBtn(b)}${cyc}</div>
 </div></div>`;
 const nc=document.getElementById('nextcyc');if(nc)nc.onclick=()=>{window._nextIdx=(window._nextIdx||0)+1+Math.floor(Math.random()*5);renderNext();};
}
function renderStatus(){
 const h=document.getElementById('hoursline'),bx=document.getElementById('budgetbox');
 const r1=remFor('BookBeat'),r2=remFor('Spotify'),p=[];
 if(r1!=null)p.push(`BookBeat <b>${fmt(r1)} t</b>`);if(r2!=null)p.push(`Spotify <b>${fmt(r2)} t</b>`);
 if(h)h.innerHTML=p.length?'Timer tilbage: '+p.join(' · '):'';
 const bb=budgetBanner();if(bx)bx.innerHTML=bb?`<details><summary>Hvad skal jeg bruge først?</summary>${bb}</details>`:'';
}
const CHIPS=['enemies to lovers','grumpy sunshine','forced proximity','slow burn','found family','small town','fake relationship','forbidden love','second chance','dark','emotional','funny','fantasy','thriller','historical'];
function renderChips(){const c=document.getElementById('chips');c.innerHTML='';CHIPS.forEach(t=>{const s=document.createElement('button');s.type='button';s.className='chip';s.textContent=t;s.onclick=()=>{fText.value=t;update();};c.appendChild(s);});}
const SORTS=[['useit','Brug mine timer'],['cheap','Billigst først'],['rating','Højest bedømt'],['hours','Kortest'],['added','Længst på TBR'],['deep','Deep-cut score'],['rand','Tilfældig']];
function buildGroups(){
 const r=document.getElementById('fRate'),s=document.getElementById('fSpice'),so=document.getElementById('fSort');
 r.innerHTML='';[[0,'Alle'],[3.75,'★ 3,75+'],[4,'★ 4+'],[4.25,'★ 4,25+']].forEach(([v,l])=>{const b=mkTg(l,F.rate===v,()=>{F.rate=v;update();});b.dataset.v=v;r.appendChild(b);});
 s.innerHTML='';[[0,'Alle'],[1,'1+'],[2,'2+'],[3,'3+'],[4,'4+']].forEach(([v,l])=>{const b=mkTg(l,F.spice===v,()=>{F.spice=v;update();});b.dataset.v=v;s.appendChild(b);});
 so.innerHTML=SORTS.map(([k,l])=>`<label><input type="radio" name="fs" value="${k}"${F.sort===k?' checked':''}> ${l}</label>`).join('');
 so.querySelectorAll('input').forEach(i=>i.onchange=()=>{F.sort=i.value;update();});
}
function syncUI(){
 const set=(id,v)=>document.getElementById(id).setAttribute('aria-pressed',v?'true':'false');
 set('qNow',F.now);set('qFree',F.free);set('qFit',F.fit);set('qDeep',F.deep);set('qSeries',F.series);
 document.querySelectorAll('#fRate .tg').forEach(b=>b.setAttribute('aria-pressed',(+b.dataset.v===F.rate)?'true':'false'));
 document.querySelectorAll('#fSpice .tg').forEach(b=>b.setAttribute('aria-pressed',(+b.dataset.v===F.spice)?'true':'false'));
 document.querySelectorAll('#fSort input').forEach(i=>i.checked=(i.value===F.sort));
 const q=document.getElementById('qFit');const r1=remFor('BookBeat'),r2=remFor('Spotify');
 q.title=(r1!=null||r2!=null)?`BookBeat ${r1!=null?fmt(r1)+' t':'–'} · Spotify ${r2!=null?fmt(r2)+' t':'–'} tilbage`:'';
 document.getElementById('fHours').disabled=F.fit;
 document.getElementById('fhVal').textContent=F.fit?'låst til dit budget':(F.maxh>=30?'alle':('≤ '+F.maxh+' t'));
 document.getElementById('fitHint').textContent=F.fit?`Låst, mens "Passer i mine timer" er slået til: BookBeat ${r1!=null?fmt(r1):'–'} t, Spotify ${r2!=null?fmt(r2):'–'} t. Ejede bøger og Libby er ikke begrænset.`:'';
}
function resetAll(){Object.assign(F,{now:false,free:false,fit:false,deep:false,series:false,rate:0,spice:0,maxh:30,txt:''});document.getElementById('fText').value='';document.getElementById('fHours').value=30;SRCSEL=new Set(SRCS);try{localStorage.removeItem('un_src');}catch(e){}renderSrcFilter();renderPicks();renderNext();update();}
function update(){
 F.txt=fText.value.trim().toLowerCase(); F.maxh=+fHours.value;
 let rows=DATA.filter(b=>{
   if(!srcOK(b))return false;
   if(F.now&&!availNow(b))return false;
   if(F.free){const ct=costTier(b);if(!(ct==='owned'||ct==='lib'))return false;}
   if(F.fit){if(!fitsOwn(b))return false;}else if(F.maxh<30){if(!b.hrs||b.hrs>F.maxh)return false;}
   if(F.rate>0&&(!b.r||b.r<F.rate))return false;
   if(F.spice>0&&(!b.sp||b.sp<F.spice))return false;
   if(F.deep&&(b.rd==null||b.rd>=8000))return false;
   if(F.series&&b.sn!==1)return false;
   if(F.txt){const hay=(b.t+' '+b.a+' '+(b.tg||'')+' '+(b.se||'')).toLowerCase();if(!hay.includes(F.txt))return false;}
   if(!F.txt&&!startable(b))return false;
   return true;});
 const sort=F.sort;
 if(sort==='useit')rows.sort((a,b)=>(urgency(b)-urgency(a))||dc(b)-dc(a));
 else if(sort==='cheap')rows.sort((a,b)=>(costRank[costTier(a)]-costRank[costTier(b)])||(lbDays(a)-lbDays(b))||dc(b)-dc(a));
 else if(sort==='deep')rows.sort((a,b)=>dc(b)-dc(a));else if(sort==='rating')rows.sort((a,b)=>(b.r||0)-(a.r||0));
 else if(sort==='hours')rows.sort((a,b)=>(a.hrs||999)-(b.hrs||999));else if(sort==='added')rows.sort((a,b)=>(a.d||'9999').localeCompare(b.d||'9999'));
 else if(sort==='rand')rows.sort(()=>Math.random()-.5);
 const act=[];
 if(SRCSEL.size<SRCS.length)act.push(['Kilde: '+[...SRCSEL].join(', '),()=>{SRCSEL=new Set(SRCS);saveSrc();}]);
 if(F.now)act.push(['Klar nu',()=>{F.now=false;update();}]);
 if(F.free)act.push(['Gratis',()=>{F.free=false;update();}]);
 if(F.fit)act.push(['Passer i mine timer',()=>{F.fit=false;update();}]);
 if(!F.fit&&F.maxh<30)act.push(['Max '+F.maxh+' t',()=>{fHours.value=30;update();}]);
 if(F.deep)act.push(['Deep cuts',()=>{F.deep=false;update();}]);
 if(F.series)act.push(['Serie-starter',()=>{F.series=false;update();}]);
 if(F.rate>0)act.push(['★ '+String(F.rate).replace('.',',')+'+',()=>{F.rate=0;update();}]);
 if(F.spice>0)act.push(['Spice '+F.spice+'+',()=>{F.spice=0;update();}]);
 if(F.txt)act.push(['“'+F.txt+'”',()=>{fText.value='';update();}]);
 const ah=document.getElementById('active');ah.innerHTML='';
 act.forEach(([l,fn])=>{const s=document.createElement('span');s.className='achip';s.appendChild(document.createTextNode(l));const x=document.createElement('button');x.type='button';x.setAttribute('aria-label','Fjern filter: '+l);x.textContent='×';x.onclick=fn;s.appendChild(x);ah.appendChild(s);});
 if(act.length){const n=document.createElement('button');n.type='button';n.className='linkbtn';n.textContent='Nulstil';n.onclick=resetAll;ah.appendChild(n);}
 syncUI();
 const sl=(SORTS.find(x=>x[0]===sort)||[0,''])[1];
 rc.textContent=`${rows.length} ${rows.length===1?'bog':'bøger'} · sorteret efter ${sl.toLowerCase()}`;
 const res=document.getElementById('results');res.innerHTML='';
 if(!rows.length){res.innerHTML='<div class="rowcount">Ingen bøger matcher. <button type="button" class="linkbtn" id="resetEmpty">Nulstil filtre</button></div>';document.getElementById('resetEmpty').onclick=resetAll;}
 rows.slice(0,80).forEach((b,n)=>{const d=document.createElement('div');d.className='row';
   d.innerHTML=`<div class="rrank">${n+1}</div>${cover(b,'rcov')}<div class="rmid"><div class="ti">${link(b)} <span class="ra">· ${b.a}</span></div>
     <div class="tagline">${(b.tg||'').split(',').slice(0,6).map(s=>s.trim()).filter(Boolean).join(' · ')}</div></div>
     <div class="rmeta">${stHTML(b)}<span>${[b.r!=null?'★ '+b.r.toFixed(2).replace('.',','):'',hrsTxt(b),srcTxt(b)].filter(Boolean).join(' · ')}</span></div>`;res.appendChild(d);});
 if(rows.length>80)res.insertAdjacentHTML('beforeend',`<div class="rowcount">…og ${rows.length-80} flere. Indsnævr med filtrene.</div>`);
}
function wire(){
 [['qNow','now'],['qFree','free'],['qFit','fit'],['qDeep','deep'],['qSeries','series']].forEach(([id,k])=>document.getElementById(id).onclick=()=>{F[k]=!F[k];update();});
 ['fText','fHours'].forEach(id=>{const e=document.getElementById(id);e.addEventListener('input',update);e.addEventListener('change',update);});
}
document.getElementById('sub').textContent=`${DATA.length} bøger · ${DATA.filter(availNow).length} klar nu · opdateret ${new Date().toISOString().slice(0,10)}`;
document.getElementById('foot').innerHTML='Deep-cut score = rating + bonus for få læsere, så skjulte perler rykker op over bestsellere. Længde = lydbogstimer. Covers hentes live fra Hardcover. "Din stemning" bygger på dine seneste læsninger, og "Noget helt andet" er det modsatte, så du kan bryde mønsteret. Begge opdateres, når du har læst noget nyt.';
renderSrcFilter();buildGroups();wire();renderStatus();renderChips();applyML(BAKED.vibe,BAKED.picks);applyOpp(BAKED_OPP.vibe,BAKED_OPP.picks);loadML();update();loadNextInSeries();loadCovers();loadUpNext();
</script></body></html>'''
HTML = HTML.replace('__DATA__', PAYLOAD)
open('up_next.html', 'w').write(HTML)
print("wrote up_next.html", len(HTML), "bytes;", len(slim), "books")
