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

HTML = r'''<!DOCTYPE html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Up Next — from your TBR</title><style>
:root{color-scheme:light}*{box-sizing:border-box}
body{margin:0;background:#faf7f2;color:#2b2b2b;font:15px/1.5 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif}
.wrap{max-width:1120px;margin:0 auto;padding:20px 18px 60px}
h1{font-size:26px;margin:0 0 2px}.sub{color:#8a7f70;margin:0 0 6px;font-size:13px}
.note{color:#8a7f70;font-size:12px;margin:0 0 12px}
.vibe{background:#fff4e2;border:1px solid #f0dcbb;border-radius:12px;padding:10px 14px;margin:0 0 14px;font-size:14px;color:#8a5a1a}
.vibe b{color:#6e460f}
.hero{display:flex;gap:16px;background:linear-gradient(135deg,#ffffff,#fdf3e1);border:1.5px solid #e6c98f;border-radius:16px;padding:16px 18px;margin:0 0 14px;box-shadow:0 2px 10px rgba(140,100,30,.09)}
.hero .hcov{width:88px;height:132px;object-fit:cover;border-radius:7px;border:1px solid #e6dcc9;background:#f0e8d8;flex:none}
.hbody{display:flex;flex-direction:column;min-width:0}
.hlbl{font-size:11px;font-weight:700;letter-spacing:.04em;text-transform:uppercase;color:#a06a2c;margin-bottom:4px}
.htitle{font-size:20px;font-weight:700;line-height:1.2}
.htitle a{color:#1f2937;text-decoration:none;border-bottom:1px solid transparent}.htitle a:hover{border-bottom-color:#c9a86a}
.hau{color:#7b7264;font-size:13px;margin:2px 0 7px}
.hwhy{font-size:14.5px;color:#3d382f;line-height:1.5;margin-bottom:2px}
.addbtn{font:inherit;font-size:12px;font-weight:600;padding:3px 12px;border-radius:999px;border:1px solid #16a34a;background:#16a34a;color:#fff;cursor:pointer}.addbtn:hover{background:#15803d}.addbtn:disabled{opacity:.7;cursor:default}
h2{font-size:15px;letter-spacing:.03em;text-transform:uppercase;color:#8a6d3b;margin:24px 0 12px;border-bottom:1px solid #eadfce;padding-bottom:6px}
.cards{display:grid;grid-template-columns:repeat(auto-fill,minmax(360px,1fr));gap:14px}
.card{background:#fff;border:1px solid #ece3d5;border-radius:14px;padding:15px;box-shadow:0 1px 2px rgba(0,0,0,.03);display:flex;gap:13px}
.card.ai{border-color:#e6c98f;background:#fffdf8}
.card .body{display:flex;flex-direction:column;flex:1;min-width:0}
.cov{width:74px;height:111px;object-fit:cover;border-radius:6px;border:1px solid #e6dcc9;background:#f0e8d8;flex:none}
.cov.blank{visibility:hidden}
.lblrow{display:flex;align-items:center;gap:8px;margin-bottom:3px}
.lbl{font-size:11px;font-weight:700;letter-spacing:.03em;text-transform:uppercase;color:#a06a2c}
.bt{font-size:17px;font-weight:700;line-height:1.2}
.bt a{color:#1f2937;text-decoration:none;border-bottom:1px solid transparent}.bt a:hover{border-bottom-color:#c9a86a}
.au{color:#7b7264;font-size:12.5px;margin-bottom:6px}
.why{font-size:14px;color:#3d382f;line-height:1.5}
.meta{display:flex;flex-wrap:wrap;gap:6px;align-items:center;margin-top:9px}
.badge{font-size:10.5px;padding:2px 7px;border-radius:5px;background:#f3efe7;color:#7d746353}
.badge{color:#7a7060}
.src-Audible{background:#fce4d6;color:#9a3412}.src-BookBeat{background:#dbeafe;color:#1e40af}.src-Libby{background:#dcfce7;color:#166534}.src-Spotify{background:#ecfccb;color:#3f6212}.src-Lokal{background:#ede9fe;color:#5b21b6}.src-Ingen{background:#f1f1f1;color:#777}
.pill{font-size:10.5px;font-weight:600;padding:2px 8px;border-radius:999px;color:#fff}
.av-now{background:#16a34a}.av-short{background:#ca8a04}.av-long{background:#b45309}.av-none{background:#9ca3af}
.cost-owned{background:#dcfce7;color:#14532d}.cost-lib{background:#d1fae5;color:#065f46}.cost-inc{background:#fef9c3;color:#713f12}.cost-paid{background:#fee2e2;color:#991b1b}
.budget{background:#fffbeb;border:1px solid #fde68a;border-radius:10px;padding:12px 14px;margin:0 0 18px;font-size:13px;line-height:1.65;color:#5c4a1a}
.budget .bhdr{font-weight:800;font-size:13.5px;color:#8a6a1e;margin-bottom:5px}
.budget .brec{margin-top:7px;padding-top:7px;border-top:1px dashed #fde68a}
.star{color:#b8860b;font-weight:700}
.cyc{margin-left:auto;font-size:12px;background:#f3ece0;border:1px solid #e2d5bf;color:#7a5c22;border-radius:8px;padding:2px 9px;cursor:pointer;flex:none}.cyc:hover{background:#ece0c9}
.controls{background:#fff;border:1px solid #ece3d5;border-radius:14px;padding:14px 16px;display:flex;flex-wrap:wrap;gap:14px;align-items:flex-end}
.controls label{font-size:12px;color:#6b6257;display:flex;flex-direction:column;gap:3px;font-weight:600}
select,input[type=search]{font:inherit;padding:6px 8px;border:1px solid #d9cdb8;border-radius:8px;background:#fff}
input[type=range]{width:140px}
.chips{display:flex;flex-wrap:wrap;gap:6px;margin:12px 0}.chip{font-size:12px;padding:4px 11px;border-radius:999px;background:#f1e8d8;border:1px solid #e2d5bf;color:#6b5320;cursor:pointer}.chip:hover{background:#e7d9bf}
.rowcount{color:#8a7f70;font-size:13px;margin:10px 0}
.row{display:flex;gap:11px;padding:11px 4px;border-bottom:1px solid #f0e8da;align-items:center}
.row .rcov{width:42px;height:63px;object-fit:cover;border-radius:4px;border:1px solid #e6dcc9;background:#f0e8d8;flex:none}.row .rcov.blank{visibility:hidden}
.row .ti{font-weight:600}.row .ti a{color:#1f2937;text-decoration:none}.row .ti a:hover{text-decoration:underline}
.row .ra{color:#7b7264;font-size:13px}.tagline{color:#9a8f7d;font-size:11.5px;margin-top:2px}
.row .rrank{color:#b8a988;font-size:12px;min-width:22px;flex:none}
.row .rmid{flex:1;min-width:0}
.row .ti{overflow-wrap:anywhere}
.row .rmeta{text-align:right;white-space:nowrap;flex:none}
@media (max-width:560px){
 .row{flex-wrap:wrap;align-items:flex-start}
 .row .rmeta{flex-basis:100%;white-space:normal;text-align:left;margin-top:7px;padding-left:53px;display:flex;flex-wrap:wrap;gap:6px;align-items:center}
 .row .rmeta br{display:none}
}
.foot{margin-top:34px;color:#9a8f7d;font-size:12px;border-top:1px solid #eadfce;padding-top:12px}
.upnextwrap{margin:0 0 18px;padding:15px 17px;border:1.5px solid #e6c98f;border-radius:16px;background:linear-gradient(135deg,#fffdf8,#fdf3e1);box-shadow:0 2px 10px rgba(140,100,30,.09)}
.upnextwrap .unhdr{font-weight:800;color:#8a6a1e;font-size:15px;letter-spacing:.02em;margin:0 0 4px}
.upnextwrap .unsub{font-weight:500;color:#a9946a;font-size:12.5px}
.upnextwrap .slider{display:flex;gap:12px;margin-top:12px;overflow-x:auto;scroll-snap-type:x mandatory;padding:2px 2px 10px;-webkit-overflow-scrolling:touch;scrollbar-width:thin;scrollbar-color:#e6c98f transparent}
.upnextwrap .slider .card{flex:0 0 300px;max-width:300px;scroll-snap-align:start}
.upnextwrap .slider::-webkit-scrollbar{height:8px}
.upnextwrap .slider::-webkit-scrollbar-thumb{background:#e6c98f;border-radius:4px}
.upnextwrap .slider::-webkit-scrollbar-track{background:transparent}
</style></head><body><div class="wrap">
<h1>Up Next — from your TBR</h1>
<p class="sub" id="sub"></p>
<div id="upnext"></div>
<div id="serieshero"></div>
<div class="vibe" id="vibe">Reading your recent finishes…</div>
<p class="note">Each card is a <b>random draw</b> from books that fit it — popular and obscure at equal odds. Only 💎 Deep cut and 🔥 Hype check deliberately lean. Hit <b>↻</b> for a fresh option.</p>

<div id="budgetbox"></div>
<div class="cards" id="picks"></div>

<h2>Explore your TBR</h2>
<div class="controls">
  <label>Availability<select id="fAvail"><option value="any">Any</option><option value="now">Available now</option><option value="soon">Now + short wait</option></select></label>
  <label>Pris<select id="fCost"><option value="any">Alle kilder</option><option value="freenow">Gratis &amp; klar nu</option><option value="free">Gratis (ejet + Libby)</option><option value="nobb">Uden BookBeat</option><option value="owned">Kun ejet</option></select></label>
  <label>Search mood / trope / title<input type="search" id="fText" placeholder="e.g. enemies to lovers, dark, funny"></label>
  <label>Max hours: <span id="fhVal">any</span><input type="range" id="fHours" min="4" max="30" step="1" value="30"></label>
  <label>Min rating: <span id="frVal">any</span><input type="range" id="fRate" min="0" max="4.6" step="0.1" value="0"></label>
  <label>Min spice<select id="fSpice"><option value="0">any</option><option>1</option><option>2</option><option>3</option><option>4</option><option>5</option></select></label>
  <label style="flex-direction:row;align-items:center;gap:6px"><input type="checkbox" id="fDeep"> Deep cuts only</label>
  <label style="flex-direction:row;align-items:center;gap:6px"><input type="checkbox" id="fSeries"> Series openers only</label>
  <label>Sort<select id="fSort"><option value="useit">Brug mine timer</option><option value="cheap">Billigst først</option><option value="deep">Deep-cut score</option><option value="rating">Rating</option><option value="hours">Shortest</option><option value="added">Longest on TBR</option><option value="rand">Random</option></select></label>
</div>
<div class="chips" id="chips"></div>
<div class="rowcount" id="rc"></div>
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
const costRank={owned:0,lib:1,inc:2,paid:3,none:4};
const costLabel={owned:'💰 Ejet',lib:'💰 Gratis (Libby)',inc:'💰 Spotify-timer',paid:'💳 BookBeat',none:''};
const costPill=b=>{const c=costTier(b);return costLabel[c]?`<span class="badge cost-${c}">${costLabel[c]}</span>`:'';};
// Gratis og klar til at starte nu: ejet, eller Libby-eksemplar der er ledigt.
const freeNow=b=>costTier(b)==='owned'||(b.s==='Libby'&&b.av==='now');
const lbDays=b=>{const m=/(\d+)\s*dage/.exec(b.lb||'');return m?+m[1]:0;};

// ── Budget: brug-det-eller-mist-det ──────────────────────────────────────────
// Betalte timer nulstilles hver periode — ubrugte timer er spildte penge.
// Ejede boeger udloeber aldrig, saa de er bufferen, ikke foersteprioriteten.
// urgency = timer tilbage / dage tilbage = hvor mange t/dag hun SKAL lytte
// for ikke at spilde dem. Falder automatisk efterhaanden som hun bruger dem.
const BUD=P.budget||{};
const urg=src=>{
  if(src==='BookBeat'){const b=BUD.bb;if(!b)return 1;const rem=(b.limit||0)-(b.used||0);
    if(rem<=0)return -99; return rem/Math.max(1,b.daysLeft||1);}
  if(src==='Spotify'){const s=BUD.sp;if(!s)return 0.6;const rem=(s.limit||0)-(s.used||0);
    if(rem<=0)return -99; return rem/Math.max(1,s.daysLeft||1);}
  return 0;
};
// Rangering: hoejest spild-risiko foerst. Libby-ledig faar en fast lille
// hastesag (laanekvoten nulstilles ogsaa). Ejet = 0 (aldrig spildt).
const urgency=b=>{
  const c=costTier(b);
  if(c==='paid') return urg('BookBeat');
  if(c==='inc')  return urg('Spotify');
  if(c==='lib')  return b.av==='now'?0.5:(b.av==='short'?0.2:0.05);
  if(c==='owned')return 0;
  return -50;
};
function budgetBanner(){
  if(!BUD.bb&&!BUD.sp) return '';
  const parts=[]; let push=null, pushU=-1;
  if(BUD.bb){const rem=(BUD.bb.limit||0)-(BUD.bb.used||0),d=BUD.bb.daysLeft||0,u=urg('BookBeat');
    parts.push(`<b>BookBeat</b> ${BUD.bb.used||0} / ${BUD.bb.limit} t brugt · ${rem} t tilbage på ${d} dage${rem>0?` · ${u.toFixed(1)} t/dag for at bruge dem`:' · <b>loft nået</b>'}`);
    if(u>pushU){pushU=u;push='BookBeat';}}
  if(BUD.sp){const rem=(BUD.sp.limit||0)-(BUD.sp.used||0),u=urg('Spotify');
    parts.push(`<b>Spotify</b> ${BUD.sp.used||0} / ${BUD.sp.limit} t brugt · ${rem} t tilbage${rem>0?` · ${u.toFixed(1)} t/dag`:''}`);
    if(u>pushU){pushU=u;push='Spotify';}}
  if(BUD.bb&&BUD.bb.nextLimit&&BUD.bb.nextLimit!==BUD.bb.limit)
    parts.push(`<span style="color:#9a3412">Loftet falder til ${BUD.bb.nextLimit} t fra ${BUD.bb.periodEnd}</span>`);
  // Samme taerskel som urgency() bruger for et ledigt Libby-laan (0.5 t/dag),
  // saa banneret altid siger det samme som sorteringen goer.
  const rec = pushU<=0
    ? `Alle betalte timer er brugt — <b>gå efter gratis kilder</b> (ejet + Libby) resten af perioden.`
    : pushU<0.5
      ? `Kun lidt betalt tid tilbage på ${push} — <b>bland</b>: tag den med, men et ledigt Libby-lån er lige så presserende.`
      : `Du har betalte timer i overskud — <b>brug ${push} først</b>, gem de ejede bøger til når timerne er opbrugt.`;
  return `<div class="budget"><div class="bhdr">💳 Dine lyttetimer</div>${parts.map(p=>`<div>${p}</div>`).join('')}<div class="brec">${rec}</div></div>`;
}

// Everyday picks: uniform-random draw from books that FIT the card (equal odds, popular or
// obscure). Only Deep cut and Hype check deliberately lean. Light rating floors keep out duds.
const PICKS=[
 {k:'useit',ic:'⏳',lb:'Brug dine betalte timer',pool:()=>{const best=urg('BookBeat')>=urg('Spotify')?'BookBeat':'Spotify';
   if(urg(best)<=0)return [];
   return DATA.filter(b=>b.s===best&&b.r&&b.r>=3.4&&startable(b));},
  why:b=>{const bd=b.s==='BookBeat'?BUD.bb:BUD.sp;const rem=bd?((bd.limit||0)-(bd.used||0)):null;
   return `Du har ${rem!=null?rem+' ':''}timer tilbage på ${b.s} i denne periode — de nulstilles uanset om du bruger dem. Start her før du går til de ejede bøger.`;}},
 {k:'free',ic:'💰',lb:'Gratis lige nu',pool:()=>DATA.filter(b=>freeNow(b)&&b.r&&b.r>=3.4&&startable(b)),why:b=>b.s==='Libby'?`Ledig på Libby nu — koster dig ingenting. Lån den før køen vender tilbage.`:`Du ejer den allerede (${b.s}) — nul kroner, ingen kø, ingen abonnementstimer.`},
 {k:'nowait',ic:'⚡',lb:'No waiting',pool:()=>DATA.filter(b=>availNow(b)&&b.r&&b.r>=3.5&&startable(b)),why:b=>`On ${b.s} right now — no waitlist, start it whenever.`},
 {k:'quick',ic:'🎧',lb:'Quick listen',pool:()=>DATA.filter(b=>availNow(b)&&b.hrs&&b.hrs<=9&&b.r&&b.r>=3.4&&startable(b)),why:b=>`Just ${b.hrs} hours on audio and available now — an easy one to finish.`},
 {k:'wreck',ic:'😭',lb:'Wreck me',pool:()=>DATA.filter(b=>b.r&&b.r>=3.8&&startable(b)&&has(b,'sad','angst','emotional','grief','heartbreaking','tear')),why:b=>`Emotional and a little devastating — for when you want to feel something.`},
 {k:'cozy',ic:'☕',lb:'Cozy night',pool:()=>DATA.filter(b=>availNow(b)&&startable(b)&&has(b,'cute','lighthearted','funny','cozy','heartwarming','feel-good','small town','wholesome')),why:b=>`Low-stakes comfort you can start now. Pour a drink and relax.`},
 {k:'series',ic:'📚',lb:'Start a series',pool:()=>DATA.filter(b=>b.sn===1&&b.r&&b.r>=3.5),why:b=>`${b.se} #1 — kick off a new series.`},
 {k:'cont',ic:'📖',lb:'Continue a series',pool:()=>DATA.filter(b=>CONT[b.i]),why:b=>{const c=CONT[b.i];const lead=(c.er!=null)?`You rated “${c.et}” ${c.er}★`:`You've read “${c.et}”`;return `${lead} — pick up ${b.se||'the series'} where you left off (#${c.pos}).`;}},
 {k:'deep',ic:'💎',lb:'Deep cut',pool:()=>DATA.filter(b=>b.r&&b.r>=4.0&&b.rd!=null&&b.rd<4000&&startable(b)),why:b=>`Only ${b.rd?b.rd.toLocaleString():'a few'} readers but rated ${b.r} — a hidden gem. (This card leans obscure on purpose.)`},
 {k:'backlog',ic:'🕰️',lb:'Longest on your TBR',pool:()=>DATA.filter(b=>b.d&&b.r&&startable(b)).sort((a,b)=>a.d.localeCompare(b.d)).slice(0,30),why:b=>`Been on your list since ${b.d}. Maybe it's finally time.`},
 {k:'spicy',ic:'🌶️',lb:'Spicy pick',pool:()=>DATA.filter(b=>b.sp&&b.sp>=4&&availNow(b)&&startable(b)),why:b=>`Spice ${b.sp}/5 and available now. Turn up the heat.`},
 {k:'hype',ic:'🔥',lb:'Hype check',pool:()=>DATA.filter(b=>b.rd!=null&&startable(b)).sort((a,b)=>b.rd-a.rd).slice(0,25),why:b=>`One of the most-read on your list — ${b.rd?b.rd.toLocaleString():'lots of'} readers. See if the hype holds. (This card leans popular on purpose.)`},
 {k:'surprise',ic:'🎲',lb:'Surprise me',pool:()=>DATA.filter(b=>b.r&&startable(b)),why:b=>`A totally random roll of your whole TBR — popular or obscure, equal odds.`},
];
const idx={};
function card(label,b,why,cyc,ai){return `<div class="card${ai?' ai':''}">${covImg(b,'cov')}<div class="body">
  <div class="lblrow"><span class="lbl">${label}</span>${cyc||''}</div>
  <div class="bt">${link(b)}</div>
  <div class="au">${b.a}${b.se?` · ${b.se}${b.sn?(' #'+b.sn):''}`:''}</div>
  <div class="why">${why}</div>
  <div class="meta">${rat(b)} ${srcBadge(b)} ${avBadge(b)} ${lenB(b)} ${b.sp?`<span class="badge">🌶️${b.sp}</span>`:''} ${readB(b)}</div>
</div></div>`;}
function renderPicks(){
 const host=document.getElementById('picks');host.innerHTML='';
 // AI vibe card first, in the same grid
 const ml=window._ml;
 if(ml&&ml.picks){const list=ml.picks.filter(pk=>byId[pk.id]&&startable(byId[pk.id]));
   if(list.length){ if(window._mlIdx==null)window._mlIdx=Math.floor(Math.random()*list.length);
     const pk=list[window._mlIdx%list.length];
     const el=document.createElement('div');el.innerHTML=card('🤖 Your vibe',byId[pk.id],pk.reason||'',list.length>1?'<button class="cyc" id="mlcyc">↻</button>':'',true);host.appendChild(el.firstChild);}}
 // Anti-vibe card, right after the vibe card
 const opp=window._opp;
 if(opp&&opp.picks){const list=opp.picks.filter(pk=>byId[pk.id]&&startable(byId[pk.id]));
   if(list.length){ if(window._oppIdx==null)window._oppIdx=Math.floor(Math.random()*list.length);
     const pk=list[window._oppIdx%list.length];
     const el=document.createElement('div');el.innerHTML=card('🔀 Something completely different',byId[pk.id],pk.reason||'',list.length>1?'<button class="cyc" id="oppcyc">↻</button>':'',true);host.appendChild(el.firstChild);}}
 PICKS.forEach(p=>{const pool=p.pool();if(!pool.length)return;
   if(idx[p.k]==null)idx[p.k]=Math.floor(Math.random()*pool.length);
   const b=pool[Math.min(idx[p.k],pool.length-1)];
   const el=document.createElement('div');el.innerHTML=card(`${p.ic} ${p.lb}`,b,p.why(b),`<button class="cyc" data-k="${p.k}">↻</button>`,false);host.appendChild(el.firstChild);});
 const mb=document.getElementById('mlcyc');if(mb)mb.onclick=()=>{const list=window._ml.picks.filter(pk=>byId[pk.id]&&startable(byId[pk.id]));window._mlIdx=(window._mlIdx+1)%list.length;renderPicks();};
 const ob=document.getElementById('oppcyc');if(ob)ob.onclick=()=>{const list=window._opp.picks.filter(pk=>byId[pk.id]&&startable(byId[pk.id]));window._oppIdx=(window._oppIdx+1)%list.length;renderPicks();};
 host.querySelectorAll('.cyc[data-k]').forEach(btn=>btn.onclick=()=>{const p=PICKS.find(x=>x.k===btn.dataset.k);const pool=p.pool();
   idx[p.k]=Math.floor(Math.random()*pool.length);renderPicks();});
}
function applyML(vibe,picks){window._ml={vibe:vibe,picks:picks};window._mlIdx=null;
 const v=document.getElementById('vibe');if(v)v.innerHTML=vibe?('<b>Your vibe right now:</b> “'+vibe+'”'):'';renderPicks();}
function applyOpp(vibe,picks){window._opp={vibe:vibe,picks:picks};window._oppIdx=null;renderPicks();}
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
// Featured section: your hand-curated "Up Next" list on Hardcover, fetched LIVE from the
// worker on every page load — books you add during the week appear immediately, no rebuild.
// These bypass the startable/pool logic entirely: you picked them, so they're always shown.
function renderUpNext(list){
 window._upnext=list; const host=document.getElementById('upnext'); if(!host)return;
 if(!list||!list.length){host.innerHTML='';return;}
 list.forEach(x=>{if(x.cover)COV[x.id]=x.cover;});
 const cards=list.map(x=>{const b=byId[x.id]||{i:x.id,t:x.t,a:x.a,sl:x.hc};
   return card('⭐ Up Next',b,'You added this to your Up Next list on Hardcover.','',false);}).join('');
 host.innerHTML=`<div class="upnextwrap"><div class="unhdr">⭐ Your Up Next</div><div class="unsub">Hand-picked by you on Hardcover — pulled live every time this page loads. Swipe →</div><div class="slider">${cards}</div></div>`;
}
async function loadUpNext(){
 try{const r=await fetch(P.worker,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({action:'get_list',list_id:P.upnext})});
   const d=await r.json();renderUpNext((d&&d.books)||[]);}catch(e){renderUpNext([]);}
}
// Pinned hero: next unread book in a series you're ACTIVELY reading — i.e. one of
// your last 3 finished books is in an unfinished series. Live via the worker; if
// none qualify (or the worker isn't updated yet), the hero stays hidden.
function renderHero(pick){
 window._heroPick=pick;
 const host=document.getElementById('serieshero'); if(!host)return;
 if(!pick){host.innerHTML='';return;}
 if(pick.cover)COV[pick.id]=pick.cover;
 const onTbr=byId[pick.id];
 const b=onTbr||{i:pick.id,t:pick.t,a:pick.a,sl:pick.sl,se:pick.series,sn:pick.snum};
 const cov=COV[pick.id]?`<img class="hcov" src="${COV[pick.id]}" alt="" onerror="this.style.visibility='hidden'">`:`<div class="hcov"></div>`;
 const f=pick.from||{}; const rated=(f.r!=null)?` (${f.r}★)`:''; const dt=f.date?(' on '+String(f.date).slice(0,10)):'';
 const why=`You just finished “${f.t||'the previous book'}”${rated}${dt} — here's #${pick.snum} in ${pick.series}.`;
 const meta=onTbr?`${rat(b)} ${srcBadge(b)} ${avBadge(b)} ${lenB(b)} ${readB(b)} `:`<span class="pill av-none">Not on your TBR yet</span> `;
 const avail=meta+`<button class="addbtn" id="heroAdd">＋ Start reading</button>`;
 host.innerHTML=`<div class="hero">${cov}<div class="hbody">
   <div class="hlbl">📚 Next in a series you're reading</div>
   <div class="htitle">${link(b)}</div>
   <div class="hau">${b.a||pick.a||''}${pick.series?` · ${pick.series} #${pick.snum}`:''}</div>
   <div class="hwhy">${why}</div>
   <div class="meta">${avail}</div>
 </div></div>`;
 const add=document.getElementById('heroAdd');
 if(add)add.onclick=async()=>{add.disabled=true;add.textContent='Starting…';
   try{const r=await fetch(P.worker,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({action:'add_currently_reading',book_id:pick.id})});
     const d=await r.json(); if(d&&!d.error&&!d.errors){add.textContent='✓ Currently reading';}else{add.textContent='Couldn’t update';add.disabled=false;}}
   catch(e){add.textContent='Couldn’t update';add.disabled=false;}};
}
async function loadNextInSeries(){
 try{const r=await fetch(P.worker,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({action:'next_in_series'})});
   const d=await r.json(); renderHero(d&&d.pick?d.pick:null);}catch(e){renderHero(null);}
}
const CHIPS=['enemies to lovers','grumpy sunshine','forced proximity','slow burn','found family','small town','fake relationship','forbidden love','second chance','dark','emotional','funny','fantasy','thriller','historical'];
function renderChips(){const c=document.getElementById('chips');CHIPS.forEach(t=>{const s=document.createElement('span');s.className='chip';s.textContent=t;s.onclick=()=>{fText.value=t;update();};c.appendChild(s);});}
function update(){
 const av=fAvail.value,cost=fCost.value,txt=fText.value.trim().toLowerCase(),maxh=+fHours.value,minr=+fRate.value,minsp=+fSpice.value,deep=fDeep.checked,seriesOnly=fSeries.checked,sort=fSort.value;
 fhVal.textContent=maxh>=30?'any':('≤'+maxh+'h');frVal.textContent=minr<=0?'any':('≥'+minr.toFixed(1));
 let rows=DATA.filter(b=>{
   if(av==='now'&&!availNow(b))return false;if(av==='soon'&&!availSoon(b))return false;
   if(cost!=='any'){const ct=costTier(b);
     if(cost==='freenow'&&!freeNow(b))return false;
     if(cost==='free'&&!(ct==='owned'||ct==='lib'))return false;
     if(cost==='nobb'&&(ct==='paid'||ct==='none'))return false;
     if(cost==='owned'&&ct!=='owned')return false;}
   if(txt){const hay=(b.t+' '+b.a+' '+(b.tg||'')+' '+(b.se||'')).toLowerCase();if(!hay.includes(txt))return false;}
   if(maxh<30){if(!b.hrs||b.hrs>maxh)return false;} if(minr>0){if(!b.r||b.r<minr)return false;}
   if(minsp>0){if(!b.sp||b.sp<minsp)return false;} if(deep){if(b.rd==null||b.rd>=8000)return false;}
   if(seriesOnly&&b.sn!==1)return false;
   if(!txt&&!startable(b))return false; // hide un-startable mid-series books unless searching by name
   return true;});
 if(sort==='useit')rows.sort((a,b)=>(urgency(b)-urgency(a))||dc(b)-dc(a));
 else if(sort==='cheap')rows.sort((a,b)=>(costRank[costTier(a)]-costRank[costTier(b)])||(lbDays(a)-lbDays(b))||dc(b)-dc(a));
 else if(sort==='deep')rows.sort((a,b)=>dc(b)-dc(a));else if(sort==='rating')rows.sort((a,b)=>(b.r||0)-(a.r||0));
 else if(sort==='hours')rows.sort((a,b)=>(a.hrs||999)-(b.hrs||999));else if(sort==='added')rows.sort((a,b)=>(a.d||'9999').localeCompare(b.d||'9999'));
 else if(sort==='rand')rows.sort(()=>Math.random()-.5);
 rc.textContent=`${rows.length} book${rows.length===1?'':'s'} match`;
 const res=document.getElementById('results');res.innerHTML='';
 rows.slice(0,80).forEach((b,n)=>{const d=document.createElement('div');d.className='row';
   d.innerHTML=`<div class="rrank">${n+1}</div>${covImg(b,'rcov')}<div class="rmid"><div class="ti">${link(b)} <span class="ra">· ${b.a}</span></div>
     <div class="tagline">${(b.tg||'').split(',').slice(0,6).map(s=>s.trim()).filter(Boolean).join(' · ')}</div></div>
     <div class="rmeta">${rat(b)}<br>${srcBadge(b)} ${costPill(b)} ${avBadge(b)} ${lenB(b)} ${readB(b)}</div>`;res.appendChild(d);});
 if(rows.length>80)res.insertAdjacentHTML('beforeend',`<div class="rowcount">…and ${rows.length-80} more — narrow with filters.</div>`);
}
['fAvail','fCost','fText','fHours','fRate','fSpice','fDeep','fSeries','fSort'].forEach(id=>{const e=document.getElementById(id);e.addEventListener('input',update);e.addEventListener('change',update);});
document.getElementById('sub').textContent=`${DATA.length} books · ${DATA.filter(availNow).length} available right now · snapshot ${new Date().toISOString().slice(0,10)}`;
document.getElementById('foot').innerHTML='Deep-cut score = rating + a bonus for few readers, so hidden gems rise above bestsellers. Length = audiobook hours. Covers load live from Hardcover. The 🤖 vibe pick is synthesized across your last 5 reads; 🔀 Something completely different is its opposite, for when you want to flip your pattern — both are generated live from your latest finishes, and refresh whenever you finish a new book.';
document.getElementById('budgetbox').innerHTML=budgetBanner();
renderChips();applyML(BAKED.vibe,BAKED.picks);applyOpp(BAKED_OPP.vibe,BAKED_OPP.picks);loadML();update();loadNextInSeries();loadCovers();loadUpNext();
</script></body></html>'''
HTML = HTML.replace('__DATA__', PAYLOAD)
open('up_next.html', 'w').write(HTML)
print("wrote up_next.html", len(HTML), "bytes;", len(slim), "books")
