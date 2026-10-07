#!/usr/bin/env python3
"""
Genererer næste_læsning_quiz.html fra audioboeger_tbr.xlsx.
Køres automatisk af den ugentlige pipeline eller manuelt.

Boglisten i Excel opdateres separat med fetch_hardcover_books.py.
"""
import json, openpyxl, os, re

EXCEL_PATH = os.path.join(os.path.dirname(__file__), 'audioboeger_tbr.xlsx')
OUT_PATH   = os.path.join(os.path.dirname(__file__), 'næste_læsning_quiz.html')
BUDGET_PATH = os.path.join(os.path.dirname(__file__), '.budget.json')

def build_data():
    wb = openpyxl.load_workbook(EXCEL_PATH)
    ws = wb.active
    books = []
    for row in range(2, ws.max_row + 1):
        title = ws.cell(row, 2).value
        if not title:
            continue
        sg  = ws.cell(row, 5).value or ''
        rio = ws.cell(row, 6).value or ''
        spice_raw = ws.cell(row, 7).value or ''
        rating_raw = ws.cell(row, 8).value or ''
        source = ws.cell(row, 4).value or 'Ingen'

        all_tags = set()
        for t in (sg + ',' + rio).split(','):
            tag = t.strip().lower()
            if tag:
                all_tags.add(tag)

        sp = 0
        if spice_raw:
            try: sp = int(str(spice_raw)[0])
            except: pass

        sl = ''
        if spice_raw and ' - ' in str(spice_raw):
            sl = str(spice_raw).split(' - ', 1)[1][:30]

        src = {'BookBeat':'BB','Libby':'LB','Spotify':'SP','Lokal':'LK',
               'Audible':'AB','Ingen':'–'}.get(source, '–')

        # Libby-ventestatus fra kolonne N -> 'a' ledig / 'k' kort / 'l' lang
        wait = ''
        if src == 'LB':
            n = str(ws.cell(row, 14).value or '')
            if n.startswith('Ledig'):   wait = 'a'
            elif n.startswith('Kort'):  wait = 'k'
            elif n.startswith('Lang'):  wait = 'l'
            mday = re.search(r'(\d+)\s*dage', n)
            wait_days = int(mday.group(1)) if mday else 0
        else:
            wait_days = 0

        try: r = float(rating_raw)
        except: r = 0.0

        books.append({"t": title, "a": ws.cell(row,3).value or "",
                      "s": src, "g": list(all_tags),
                      "sp": sp, "r": r, "sl": sl,
                      "w": wait, "wd": wait_days,
                      "id": ws.cell(row, 9).value or 0})
    return books

# NOTE: Template uses plain { } — we use str.replace(), NOT .format()
HTML_TEMPLATE = r'''<!DOCTYPE html>
<html lang="da">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Hvad skal jeg læse næste?</title>
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Instrument+Sans:wght@400;500;600;700&family=Newsreader:wght@500;600&display=swap" rel="stylesheet">
<style>
:root{color-scheme:light;--paper:#f5f1e9;--card:#fff;--line:#e7dfd0;--ink:#2b2620;--ink2:#6b6257;--acc:#8a5a14;--ok:#1f7a3d;--warn:#a16207;--none:#6b6257;--serif:"Newsreader",Georgia,"Times New Roman",serif;--sans:"Instrument Sans",-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif}
*{box-sizing:border-box}
body{margin:0;background:var(--paper);color:var(--ink);font:15px/1.5 var(--sans)}
.wrap{max-width:680px;margin:0 auto;padding:18px 16px 60px}
:focus-visible{outline:2px solid var(--acc);outline-offset:2px}
.tabs{display:flex;gap:4px;border-bottom:1px solid var(--line);margin:0 0 22px}
.tabs a{padding:10px 14px;min-height:44px;display:flex;align-items:center;text-decoration:none;color:var(--ink2);font-weight:600;font-size:14px;border-bottom:2px solid transparent;margin-bottom:-1px}
.tabs a[aria-current=page]{color:var(--ink);border-bottom-color:var(--ink)}
h1{font-family:var(--serif);font-weight:600;font-size:34px;line-height:1.1;margin:0 0 6px;letter-spacing:-.01em}
.sub{color:var(--ink2);margin:0 0 20px;font-size:14px}
.prog{display:flex;align-items:center;gap:12px;margin:0 0 14px}
.bar{flex:1;height:4px;background:var(--line);border-radius:2px;overflow:hidden}
.bar i{display:block;height:100%;background:var(--ink);width:0;transition:width .25s}
.plabel{font-size:13px;color:var(--ink2);white-space:nowrap}
.live{font-size:13px;color:var(--ink2);margin:0 0 6px}
.live b{color:var(--ink)}
.qcard{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:22px}
.qtitle{font-family:var(--serif);font-size:25px;font-weight:600;line-height:1.2;margin:0 0 4px}
.qtitle:focus{outline:none}
.qsub{color:var(--ink2);font-size:14px;margin:0 0 16px}
.opts{display:grid;gap:10px;grid-template-columns:1fr 1fr}
.opt{display:flex;align-items:flex-start;gap:12px;background:#fff;border:1.5px solid var(--line);border-radius:12px;padding:12px 14px;min-height:56px;text-align:left;font:inherit;color:var(--ink);cursor:pointer;width:100%;touch-action:manipulation;-webkit-tap-highlight-color:transparent}
@media(hover:hover){.opt:hover:not([aria-disabled=true]){border-color:var(--ink2)}}
.opt[aria-checked=true],.opt[aria-pressed=true]{border-color:var(--ink);background:#faf6ee}
.opt[aria-disabled=true]{opacity:.45;cursor:not-allowed}
.mark{flex:none;width:20px;height:20px;border:1.5px solid var(--ink2);margin-top:2px;display:flex;align-items:center;justify-content:center;font-size:13px;line-height:1;color:#fff}
.mark.r{border-radius:50%}.mark.s{border-radius:5px}
.opt[aria-checked=true] .mark,.opt[aria-pressed=true] .mark{background:var(--ink);border-color:var(--ink)}
.opt[aria-checked=true] .mark::after,.opt[aria-pressed=true] .mark::after{content:"✓"}
.oe{font-size:20px;flex:none;line-height:1.3}
.ot{flex:1;min-width:0}
.ol{font-weight:600;display:flex;gap:8px;align-items:baseline;justify-content:space-between}
.od{color:var(--ink2);font-size:13px;display:block;margin-top:1px}
.oc{font-size:12px;font-weight:600;color:var(--ink2);background:#f0e8d8;border-radius:10px;padding:1px 8px;flex:none}
.oc.z{background:transparent;color:var(--ink2);font-weight:500}
.foot{display:flex;align-items:center;gap:12px;margin-top:16px;flex-wrap:wrap}
.foot .sp{flex:1}
.btn{font:inherit;font-weight:600;font-size:14px;border-radius:999px;padding:0 20px;min-height:44px;cursor:pointer;border:1.5px solid var(--ink);background:var(--ink);color:#fff;touch-action:manipulation}
.btn:disabled{opacity:.35;cursor:not-allowed}
.btn.ghost{background:transparent;color:var(--ink);border-color:var(--line)}
@media(hover:hover){.btn.ghost:hover{border-color:var(--ink2)}}
.link{font:inherit;font-size:14px;background:none;border:0;color:var(--acc);font-weight:600;cursor:pointer;min-height:44px;padding:0 4px;text-decoration:underline;text-underline-offset:3px}
.counter{font-size:13px;color:var(--ink2)}
#results{display:none}
.rh{font-family:var(--serif);font-size:26px;font-weight:600;margin:0 0 4px}
.rh:focus{outline:none}
.rsub{color:var(--ink2);font-size:13px;margin:0 0 12px}
.chips{display:flex;flex-wrap:wrap;gap:8px;margin:0 0 12px}
.chip{display:inline-flex;align-items:center;gap:8px;font:inherit;font-size:13px;background:#efe7d6;border:0;border-radius:999px;padding:0 14px;min-height:44px;color:var(--ink);cursor:pointer;touch-action:manipulation}
.chip em{font-style:normal;color:var(--ink2)}
.chip u{color:var(--acc);font-weight:600;text-underline-offset:3px}
.toggles{display:flex;flex-wrap:wrap;gap:8px;margin:0 0 16px}
.tg{display:inline-flex;align-items:center;gap:8px;font:inherit;font-size:14px;font-weight:600;background:#fff;border:1.5px solid var(--line);border-radius:999px;padding:0 16px;min-height:44px;color:var(--ink);cursor:pointer;touch-action:manipulation}
.tg[aria-pressed=true]{background:var(--ink);border-color:var(--ink);color:#fff}
.card{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:16px;margin:0 0 12px;display:flex;gap:14px}
.rank{font-family:var(--serif);font-size:20px;font-weight:600;color:var(--ink2);width:26px;flex:none;text-align:center}
.cb{flex:1;min-width:0}
.bt{font-family:var(--serif);font-size:19px;font-weight:600;line-height:1.2}
.au{color:var(--ink2);font-size:13px;margin:2px 0 6px}
.match{font-size:14px;margin:0 0 8px}
.match b{font-weight:600}
.meta{display:flex;flex-wrap:wrap;gap:4px 14px;align-items:center;font-size:13px;color:var(--ink2)}
.st{display:inline-flex;align-items:center;gap:6px;font-weight:600;color:var(--ink)}
.st::before{content:"";width:8px;height:8px;border-radius:50%;background:var(--none)}
.st.ok::before{background:var(--ok)}.st.warn::before{background:var(--warn)}
.star{color:var(--acc)}
.dots{display:inline-flex;gap:2px;align-items:center}
.dots i{width:7px;height:7px;border-radius:50%;background:var(--line)}
.dots i.on{background:var(--acc)}
.add{margin-top:10px;font:inherit;font-size:13px;font-weight:600;background:transparent;border:1.5px solid var(--line);border-radius:999px;min-height:44px;padding:0 16px;cursor:pointer;color:var(--ink);touch-action:manipulation}
@media(hover:hover){.add:hover:not(:disabled){border-color:var(--ink)}}
.add.done{border-color:var(--ok);color:var(--ok);cursor:default}
.none{text-align:center;padding:30px 10px;color:var(--ink2)}
.more{display:block;margin:14px auto 0}
@media(max-width:520px){.opts{grid-template-columns:1fr}h1{font-size:28px}.card{flex-direction:column;gap:8px}.rank{text-align:left;width:auto}}
</style>
</head>
<body>
<div class="wrap">
  <nav class="tabs" aria-label="Sider"><a href="./" aria-current="page">Quiz</a><a href="up_next.html">Up Next</a></nav>
  <h1>Hvad skal jeg læse næste?</h1>
  <p class="sub">Fire spørgsmål, så får du anbefalinger fra din to-read liste · <span id="total-count"></span> bøger</p>

  <div id="quiz">
    <div class="prog"><div class="bar"><i id="barfill"></i></div><span class="plabel" id="plabel"></span></div>
    <p class="live" id="live" aria-live="polite"></p>
    <section class="qcard" id="qcard">
      <h2 class="qtitle" id="qtitle" tabindex="-1"></h2>
      <p class="qsub" id="qsub"></p>
      <div class="opts" id="opts"></div>
      <div class="foot">
        <button class="btn ghost" id="back" type="button"></button>
        <span class="sp"></span>
        <span class="counter" id="counter" aria-live="polite"></span>
        <button class="btn" id="next" type="button"></button>
      </div>
      <div class="foot" style="margin-top:4px"><button class="link" id="skip" type="button">Spring over</button></div>
    </section>
  </div>

  <div id="results">
    <h2 class="rh" id="rh" tabindex="-1">Dine anbefalinger</h2>
    <p class="rsub" id="rsub"></p>
    <div class="chips" id="chips"></div>
    <div class="toggles">
      <button class="tg" id="tgAvail" type="button" aria-pressed="true">Kun dem jeg kan lytte til nu</button>
      <button class="tg" id="tgFree" type="button" aria-pressed="true">Optimér efter mine timer</button>
    </div>
    <div id="book-list"></div>
    <button class="btn ghost more" id="more" type="button" style="display:none"></button>
    <button class="btn ghost more" id="restart" type="button">Start forfra</button>
  </div>
</div>
<script>
const BOOKS = BOOKS_DATA_PLACEHOLDER;
// ── Budget-bevidst kilde-prioritet ───────────────────────────────────────────
// Betalte timer nulstilles hver periode: ubrugte timer = spildte penge.
// Ejede bøger udløber aldrig, så de er bufferen — ikke førsteprioriteten.
// Prioritering = EDF (earliest deadline first). Timerne konkurrerer om ET
// fælles lyttetempo, så den største bunke er ikke altid den rigtige at jage:
// udløber en mindre bunke først, dør den mens man jager den store. Kun de
// timer hun realistisk NÅR at bruge (atRisk) tæller — resten er tabt uanset.
const BUDGET = BUDGET_DATA_PLACEHOLDER;
const CAP = (+BUDGET.dailyCapacity > 0) ? +BUDGET.dailyCapacity : 2.0;  // t/dag
function remHours(k) {
  const o = BUDGET[k]; if(!o) return null;
  return Math.max(0, (o.limit||0) - (o.used||0));
}
// Det gamle mål: hvor mange t/dag hun SKULLE lytte for at nå det hele.
// Bruges kun til at afgøre OM der er betalt tid i overskud.
// Mangler daysLeft (fx uparsebar periodEnd), så antag 30 dage — en manglende
// dato må IKKE tolkes som "udløber i morgen" og kapre hele rangeringen.
const dl = d => (Number.isFinite(+d) && +d>=0) ? Math.max(1,+d) : 30;
function rawUrgOf(k) {
  const o = BUDGET[k]; if(!o) return 0;
  const rem = remHours(k); if(rem<=0) return -99;
  return rem / dl(o.daysLeft);
}
function reachableHours(k) {
  const o = BUDGET[k]; if(!o) return 0;
  return Math.min(remHours(k), CAP * dl(o.daysLeft));
}
function urgOf(k) {
  const o = BUDGET[k]; if(!o) return (k==='bb'?1:0.6);
  const rem = remHours(k);
  if(rem<=0) return -99;                      // opbrugt
  const d = dl(o.daysLeft);
  const atRisk = reachableHours(k);
  if(atRisk < 1) return 0.05;                 // for lidt på spil til at styre valget
  return (10/d) * Math.min(1, atRisk/CAP);    // EDF, dæmpet under én dags lytning
}
let _freeFirst = true;   // "optimér efter pris/timer" til/fra
function srcBonus(b) {
  if(!_freeFirst) return 0;
  const scale = 1.4;                          // vægt mod smagsmatch
  if((b.s==='BB'||b.s==='SP') && !fits(b)) return -2;   // kan ikke nås på de resterende timer
  if(b.s==='BB') return scale * Math.max(-3, Math.min(4, urgOf('bb')));
  if(b.s==='SP') return scale * Math.max(-3, Math.min(4, urgOf('sp')));
  if(b.s==='LB') return scale * (b.w==='a' ? 0.5 : b.w==='k' ? 0.2 : 0.05);
  if(b.s==='LK' || b.s==='AB') return 0;      // ejet: aldrig spildt, gem som buffer
  return -2;                                  // ingen adgang
}
function budgetLine() {
  const bb=BUDGET.bb, sp=BUDGET.sp;
  if(!bb && !sp) return '';
  const bits=[];
  if(bb) bits.push(`BookBeat ${bb.used||0}/${bb.limit} t${bb.daysLeft!=null?` · ${bb.daysLeft} dg tilbage`:''}`);
  if(sp) bits.push(`Spotify ${sp.used||0}/${sp.limit} t${sp.daysLeft!=null?` · ${sp.daysLeft} dg tilbage`:''}`);
  const ub=urgOf('bb'), us=urgOf('sp');
  const best = ub>=us ? 'bb' : 'sp';
  const bu = Math.max(ub, us);
  const lvl = Math.max(rawUrgOf('bb'), rawUrgOf('sp'));   // er der overskud?
  const bd = (BUDGET[best]||{}).daysLeft;
  const rec = bu<=0 ? 'alle betalte timer brugt → gratis kilder først'
            : lvl<0.5 ? 'kun lidt betalt tid tilbage → bland med Libby'
            : `brug ${best==='bb'?'BookBeat':'Spotify'} først${bd!=null?` (fornyes om ${bd} dg)`:''}`;
  return `${bits.join(' · ')} · ${rec}`;
}


// ── Spørgsmål ────────────────────────────────────────────────────────────────
const T = (b, ...tags) => tags.some(t => b.g.includes(t));
const HEAVY = ['dark','sad','depressing','depression','death / grief','grief','suicide / ideation','self harm','abuse','tragic','horror'];
const SPORT = ['sports','hockey','football','tennis','basketball','baseball','swimming'];
const QS = [
  {id:'q1', title:'Hvilken tone har du lyst til?', sub:'Kun stemningen — genren kommer bagefter.', multi:false, skip:'any', chip:'Tone', skipTxt:'alle toner',
   opts:[
    {v:'light', e:'☀️', l:'Let & sjov', d:'Fluffy, sjov og feel-good', f:b=>T(b,'funny','lighthearted','hopeful')&&!T(b,...HEAVY)},
    {v:'emotional', e:'💔', l:'Dyb & følelsesladet', d:'Angst, tårer og den gode smerte', f:b=>T(b,'emotional','angst','sad')},
    {v:'dark', e:'🌑', l:'Mørk & intens', d:'Spændende, dyster og anspændt', f:b=>T(b,'dark','tense','thriller','mystery','suspense','dark romance')}]},
  {id:'q2', title:'Hvilken plot-dynamik tiltrækker dig?', sub:'Vælg op til 3.', multi:true, max:3, skip:['any_trope'], chip:'Dynamik', skipTxt:'alle dynamikker',
   opts:[
    {v:'enemies to lovers', e:'⚔️', l:'Enemies to lovers', d:'Fra had til kærlighed'},
    {v:'forced proximity', e:'🏠', l:'Forced proximity', d:'Fanget sammen mod deres vilje'},
    {v:'grumpy & sunshine', e:'☀️', l:'Grumpy & sunshine', d:'Den sure og den solrige'},
    {v:'slow burn', e:'🕯️', l:'Slow burn', d:'Spænding der bygger langsomt op'},
    {v:'friends to lovers', e:'💫', l:'Friends to lovers', d:'Venskab der bliver til kærlighed'},
    {v:'second chances', e:'🔄', l:'Second chances', d:'Gamle flammer mødes igen'},
    {v:'fake relationship', e:'🎭', l:'Fake relationship', d:'Det starter som en aftale …'}]},
  {id:'q3', title:'Hvilken verden vil du ind i?', sub:'Genre og setting.', multi:false, skip:'any_genre', chip:'Verden', skipTxt:'alle verdener',
   opts:[
    {v:'contemporary', e:'🏙️', l:'Moderne virkelighed', d:'Nutidens verden', f:b=>T(b,'contemporary')},
    {v:'fantasy', e:'🐉', l:'Fantasy & magi', d:'Overnaturlig, fae, paranormal', f:b=>T(b,'fantasy','magic','paranormal','fae','high fantasy')},
    {v:'historical', e:'🏰', l:'Historisk', d:'Regency, viktoriansk, fortiden', f:b=>T(b,'historical','regency')},
    {v:'thriller', e:'🔪', l:'Thriller & krimi', d:'Mystery og suspense', f:b=>T(b,'thriller','mystery','suspense')},
    {v:'sports', e:'🏒', l:'Sports romance', d:'Hockey, fodbold, tennis …', f:b=>T(b,...SPORT)}]},
  {id:'q4', title:'Hvor meget spice skal der være?', sub:'Romance.io spice-skala 1–5. Bøger uden data tæller med.', multi:false, skip:'any_spice', chip:'Spice', skipTxt:'alle niveauer',
   opts:[
    {v:'low', e:'🌸', l:'Kysk (1–2)', d:'Kys og glimt — uden eksplicit indhold', f:b=>!b.sp||(b.sp>=1&&b.sp<=2)},
    {v:'medium', e:'🔥', l:'Medium (3)', d:'Open door, men med smag', f:b=>!b.sp||b.sp===3},
    {v:'high', e:'🌶️', l:'Hedt (4–5)', d:'Eksplicit og rigeligt', f:b=>!b.sp||b.sp>=4}]}
];
// q2: trope-optioner filtrerer på tagget selv
QS[1].opts.forEach(o => o.f = b => b.g.includes(o.v));

const answers = {q1:null, q2:[], q3:null, q4:null};
let step = 0, editing = false, onlyAvail = true, freeFirst = true;
const $ = id => document.getElementById(id);
const esc = s => String(s).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const isSkip = (q, a) => q.multi ? (a.length === 1 && a[0] === q.skip[0]) : a === q.skip;
const answered = i => { const q = QS[i], a = answers[q.id]; return q.multi ? a.length > 0 : a !== null; };

// Filter for ét besvaret spørgsmål (bruges til optælling og live-antal)
function qFilter(i) {
  const q = QS[i], a = answers[q.id];
  if (!answered(i) || isSkip(q, a)) return () => true;
  if (q.multi) return b => a.some(v => b.g.includes(v));
  const o = q.opts.find(o => o.v === a);
  return o ? o.f : () => true;
}
function poolBefore(i) {
  let p = BOOKS;
  for (let k = 0; k < i; k++) p = p.filter(qFilter(k));
  return p;
}

// ── Rendering af spørgsmål ───────────────────────────────────────────────────
function renderStep() {
  const q = QS[step], a = answers[q.id], pool = poolBefore(step);
  $('qtitle').textContent = q.title;
  $('qsub').textContent = q.sub;
  $('plabel').textContent = `Trin ${step + 1} af ${QS.length}`;
  $('barfill').style.width = ((step + 1) / QS.length * 100) + '%';
  const live = BOOKS.filter(b => QS.every((_, k) => k >= step ? true : qFilter(k)(b))).length;
  $('live').innerHTML = `<b>${pool.length}</b> bøger matcher indtil nu`;
  const box = $('opts');
  box.setAttribute('role', q.multi ? 'group' : 'radiogroup');
  box.setAttribute('aria-labelledby', 'qtitle');
  box.innerHTML = q.opts.map(o => {
    const n = pool.filter(o.f).length;
    const sel = q.multi ? a.includes(o.v) : a === o.v;
    const attr = q.multi ? `role="button" aria-pressed="${sel}"` : `role="radio" aria-checked="${sel}"`;
    const dis = n === 0 && !sel ? ' aria-disabled="true"' : '';
    return `<button type="button" class="opt" data-v="${esc(o.v)}" ${attr}${dis}><span class="mark ${q.multi ? 's' : 'r'}" aria-hidden="true"></span><span class="oe" aria-hidden="true">${o.e}</span><span class="ot"><span class="ol"><span>${esc(o.l)}</span><span class="oc${n === 0 ? ' z' : ''}">${n === 0 ? '0 match' : n}</span></span><span class="od">${esc(o.d)}</span></span></button>`;
  }).join('');
  const back = $('back'), next = $('next');
  back.textContent = editing ? '← Til resultater' : '← Tilbage';
  back.style.visibility = (step === 0 && !editing) ? 'hidden' : 'visible';
  next.style.display = q.multi ? '' : 'none';
  next.textContent = editing ? 'Se anbefalinger' : (step === QS.length - 1 ? 'Se anbefalinger' : 'Næste');
  next.disabled = q.multi ? a.length === 0 : true;
  $('counter').textContent = q.multi ? `${a.length} af ${q.max} valgt` : '';
}

function showStep(i, focus = true) {
  step = i;
  $('results').style.display = 'none';
  $('quiz').style.display = 'block';
  renderStep();
  if (focus) $('qtitle').focus({preventScroll: false});
}

function advance() {
  if (editing || step === QS.length - 1) { editing = false; showResults(); }
  else showStep(step + 1);
}

function pick(v) {
  const q = QS[step];
  if (q.multi) {
    let a = answers[q.id].filter(x => x !== q.skip[0]);
    if (a.includes(v)) a = a.filter(x => x !== v);
    else if (a.length < q.max) a.push(v);
    else return;
    answers[q.id] = a;
    renderStep();
    const el = document.querySelector(`#opts [data-v="${CSS.escape(v)}"]`); if (el) el.focus();
  } else {
    answers[q.id] = v;
    renderStep();
    setTimeout(advance, 260);
  }
}

$('opts').addEventListener('click', e => {
  const b = e.target.closest('.opt'); if (!b || b.getAttribute('aria-disabled') === 'true') return;
  pick(b.dataset.v);
});
$('next').addEventListener('click', advance);
$('skip').addEventListener('click', () => { const q = QS[step]; answers[q.id] = q.skip; advance(); });
$('back').addEventListener('click', () => { if (editing) { editing = false; showResults(); } else if (step > 0) showStep(step - 1); });

// ── Scoring ──────────────────────────────────────────────────────────────────
function scoreBook(book) {
  let score = 0;
  const tags = book.g;
  const has = (...t) => t.some(tag => tags.includes(tag));
  const mood = answers.q1;
  if (mood==='light')     { if(has('funny','lighthearted'))score+=3; if(has('hopeful'))score+=1; if(has('tense','angst'))score-=2; if(has(...HEAVY))score-=4; }
  if (mood==='emotional') { if(has('emotional','angst'))score+=3; if(has('sad','hopeful'))score+=1; if(has('lighthearted','funny'))score-=1; }
  if (mood==='dark')      { if(has('dark','tense','thriller','mystery','suspense','dark romance'))score+=3; if(has('possessive hero','alpha male'))score+=1; if(has('lighthearted','funny'))score-=2; }
  const tropes = answers.q2;
  if (!tropes.includes('any_trope')) {
    tropes.forEach(t => { if(tags.includes(t)) score+=3; });
    if(tropes.length>0 && !tropes.some(t=>tags.includes(t))) score-=1;
  }
  const genre = answers.q3;
  if(genre==='contemporary'&& has('contemporary'))score+=3;
  else if(genre==='fantasy'  && has('fantasy','magic','paranormal','fae','high fantasy'))score+=4;
  else if(genre==='historical'&&has('historical','regency'))score+=4;
  else if(genre==='thriller' && has('thriller','mystery','suspense'))score+=3;
  else if(genre==='sports'   && has(...SPORT))score+=4;
  else if(genre && genre!=='any_genre') score-=2;
  const spice = answers.q4;
  if(spice==='low'    && book.sp>0) { score += book.sp<=2?2:book.sp>=4?-3:0; }
  if(spice==='medium') { score += book.sp===3?2:book.sp===2||book.sp===4?1:0; }
  if(spice==='high')   { score += book.sp>=4?2:book.sp>=3?1:book.sp>0?-1:0; }
  if(book.r>=4.0) score+=1;
  if(book.r>=4.3) score+=1;
  return score;
}

// "Matcher: …" — hvilke af dine svar bogen opfylder
function matchTxt(b) {
  const out = [];
  QS.forEach((q, i) => {
    const a = answers[q.id];
    if (!answered(i) || isSkip(q, a)) return;
    if (q.multi) a.forEach(v => { if (b.g.includes(v)) out.push(v); });
    else { const o = q.opts.find(o => o.v === a); if (o && o.f(b) && !(q.id === 'q4' && !b.sp)) out.push(q.id === 'q4' ? `spice ${b.sp}` : o.l.toLowerCase()); }
  });
  return out;
}

// ── Resultater ───────────────────────────────────────────────────────────────
const PAGE_SIZE = 8;
let _scored = [], _shown = 0, _nHit = 0;
const estH = b => b.h || (b.p ? b.p/30 : (BUDGET.avgBookHours || 12.5));
// Passer i timerne tilbage på BookBeat/Spotify (ukendt længde skønnes, tæller aldrig som 'passer' af sig selv)
const fits = b => { const k = b.s==='BB'?'bb':(b.s==='SP'?'sp':null); if(!k) return true; const r = remHours(k); return r==null || estH(b) <= r + 0.25; };
const startable = b => b.st !== 0;
const listenable = b => b.s !== '–' && !(b.s === 'LB' && b.w === 'l') && fits(b) && startable(b);
const matchesAll = b => QS.every((_, k) => qFilter(k)(b));

function statusOf(b) {
  if (b.s === 'LB') {
    if (b.w === 'a') return ['ok', 'Klar nu', 'Libby'];
    if (b.w === 'k') return ['warn', `Kø ~${b.wd} dg`, 'Libby'];
    if (b.w === 'l') return ['warn', `Lang kø ~${b.wd} dg`, 'Libby'];
    return ['warn', 'Kø', 'Libby'];
  }
  const nm = {BB:'BookBeat', SP:'Spotify', LK:'Lokal', AB:'Audible'}[b.s];
  return nm ? ['ok', 'Klar nu', nm] : ['', 'Ingen adgang', ''];
}
function dots(n) { return `<span class="dots" role="img" aria-label="spice ${n} af 5">${Array.from({length:5},(_,i)=>`<i class="${i<n?'on':''}"></i>`).join('')}</span>`; }

function card(b, rank) {
  const [cls, stTxt, src] = statusOf(b);
  const m = matchTxt(b);
  const add = b.id ? `<button type="button" class="add" data-id="${b.id}">+ Sæt på Up Next</button>` : '';
  return `<article class="card"><div class="rank" aria-hidden="true">${rank + 1}</div><div class="cb">
    <div class="bt">${esc(b.t)}</div><div class="au">${esc(b.a)}</div>
    ${m.length ? `<p class="match"><b>Matcher:</b> ${esc(m.join(', '))}</p>` : ''}
    <div class="meta"><span class="st ${cls}">${esc(stTxt)}</span>${b.r ? `<span><span class="star">★</span> ${b.r.toFixed(2).replace(/0$/, '')}</span>` : ''}${src ? `<span>${src}</span>` : ''}${b.sp ? dots(b.sp) : ''}</div>
    ${add}</div></article>`;
}

function chipsHTML() {
  return QS.map((q, i) => {
    const a = answers[q.id];
    let t;
    if (!answered(i) || isSkip(q, a)) t = q.skipTxt;
    else if (q.multi) t = a.join(', ');
    else t = q.opts.find(o => o.v === a).l;
    return `<button type="button" class="chip" data-step="${i}" aria-label="Ret ${q.chip}: ${esc(t)}"><span><em>${q.chip}:</em> ${esc(t)}</span><u>Ret</u></button>`;
  }).join('');
}

function showResults() {
  $('quiz').style.display = 'none';
  $('results').style.display = 'block';
  resort();
  $('rh').focus();
}

function resort() {
  const pool = onlyAvail ? BOOKS.filter(listenable) : BOOKS;
  _freeFirst = freeFirst;
  const sc = b => ({...b, score: scoreBook(b) + srcBonus(b) - (startable(b) ? 0 : 3)});
  const byScore = (a, b) => b.score - a.score || b.r - a.r;
  const hit = pool.filter(matchesAll).map(sc).sort(byScore);
  const near = pool.filter(b => !matchesAll(b)).map(sc).filter(b => b.score > 0).sort(byScore).map(b => ({...b, near: true}));
  _nHit = hit.length;
  _scored = hit.concat(near);
  _shown = 0;
  $('chips').innerHTML = chipsHTML();
  $('tgAvail').setAttribute('aria-pressed', onlyAvail);
  $('tgFree').setAttribute('aria-pressed', freeFirst);
  const bl = budgetLine();
  $('rsub').textContent = `${_nHit} af ${pool.length} bøger matcher alle dine svar` + (freeFirst && bl ? ' · ' + bl : '');
  $('book-list').innerHTML = '';
  if (!_scored.length) {
    $('book-list').innerHTML = '<div class="none">Ingen bøger matcher alle svar. Prøv at slå “Kun dem jeg kan lytte til nu” fra eller ret et svar ovenfor.</div>';
    $('more').style.display = 'none';
    return;
  }
  more();
}

function more() {
  const batch = _scored.slice(_shown, _shown + PAGE_SIZE);
  $('book-list').insertAdjacentHTML('beforeend', batch.map((b, i) => {
    const k = _shown + i;
    const div = (k === _nHit) ? `<div class="none" style="margin:14px 0 6px">${_nHit ? 'Tæt på: disse matcher ikke alle dine svar' : 'Ingen bøger matcher alle dine svar. Her er de nærmeste'}</div>` : '';
    return div + card(b, k);
  }).join(''));
  _shown += batch.length;
  const btn = $('more'), rem = _scored.length - _shown;
  if (rem > 0) { btn.textContent = `Vis ${Math.min(PAGE_SIZE, rem)} flere (${rem} tilbage)`; btn.style.display = ''; }
  else btn.style.display = 'none';
}

$('more').addEventListener('click', more);
$('tgAvail').addEventListener('click', () => { onlyAvail = !onlyAvail; resort(); });
$('tgFree').addEventListener('click', () => { freeFirst = !freeFirst; resort(); });
$('chips').addEventListener('click', e => {
  const c = e.target.closest('.chip'); if (!c) return;
  editing = true; showStep(+c.dataset.step);
});
$('restart').addEventListener('click', () => {
  answers.q1 = null; answers.q2 = []; answers.q3 = null; answers.q4 = null;
  editing = false; showStep(0);
  window.scrollTo(0, 0);
});

// ── Hardcover "Up Next" ──────────────────────────────────────────────────────
const HC_UP_NEXT_LIST = 465056;
const HC_WORKER_URL = 'https://lucky-cloud-343c.xenia-9cc.workers.dev';
$('book-list').addEventListener('click', async e => {
  const btn = e.target.closest('.add'); if (!btn || btn.disabled || btn.classList.contains('done')) return;
  btn.disabled = true; btn.textContent = 'Tilføjer …';
  try {
    const r = await fetch(HC_WORKER_URL, {method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({book_id: +btn.dataset.id, list_id: HC_UP_NEXT_LIST})});
    const d = await r.json();
    if (d.data?.insert_list_book?.list_book?.id) { btn.textContent = '✓ Sat på Up Next'; btn.classList.add('done'); }
    else { btn.textContent = 'Fejl — prøv igen'; btn.disabled = false; }
  } catch (err) { btn.textContent = 'Fejl — prøv igen'; btn.disabled = false; }
});

// Start
$('total-count').textContent = BOOKS.length;
showStep(0, false);
</script>
</body>
</html>
'''

def load_budget():
    """Abonnements-timer fra .budget.json (skrives af pipelinen). Dage tilbage
    udregnes friskt, så tallet ikke bliver forældet mellem kørsler."""
    import datetime
    b = {}
    if os.path.exists(BUDGET_PATH):
        try:
            b = json.load(open(BUDGET_PATH, encoding='utf-8'))
            pe = (b.get('bb') or {}).get('periodEnd')
            if pe:
                b['bb']['daysLeft'] = max(0, (datetime.date.fromisoformat(pe) - datetime.date.today()).days)
        except Exception:
            b = {}
    return b

def enrich(books):
    """Brug samme rensede data som Up Next: tags (renset i build_rec_data.py), blended rating,
    lydbogstimer og om bogen kan startes (ikke #2+ i en serie hun ikke er i gang med)."""
    base = os.path.dirname(__file__)
    def _load(name, default):
        try: return json.load(open(os.path.join(base, name), encoding='utf-8'))
        except Exception: return default
    rec = {b['id']: b for b in _load('.rec_full.json', [])}
    audio = _load('.ae.json', {}).get('audio', {})
    cont = _load('.continue.json', {})
    for b in books:
        try: bid = int(b['id'])
        except Exception: continue
        rb = rec.get(bid)
        if rb:
            if rb.get('tags'): b['g'] = [t.strip() for t in rb['tags'].split(',') if t.strip()]
            if rb.get('rating'): b['r'] = round(rb['rating'], 2)
            b['p'] = rb.get('pages')
            sn = rb.get('snum')
            b['st'] = 0 if (sn and sn > 1 and str(bid) not in cont) else 1
        b['h'] = audio.get(str(bid))
    return books

def generate():
    books = enrich(build_data())
    data_js = json.dumps(books, ensure_ascii=False, separators=(',',':'))
    html = HTML_TEMPLATE.replace('BOOKS_DATA_PLACEHOLDER', data_js)
    html = html.replace('BUDGET_DATA_PLACEHOLDER', json.dumps(load_budget(), ensure_ascii=False))
    with open(OUT_PATH, 'w', encoding='utf-8') as f:
        f.write(html)
    print(f"Quiz genereret: {len(books)} bøger → {OUT_PATH}")
    return len(books)

if __name__ == '__main__':
    n = generate()
    print(f"✓ Færdig ({n} bøger)")
