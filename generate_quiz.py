#!/usr/bin/env python3
"""
Genererer næste_læsning_quiz.html fra audioboeger_tbr.xlsx.
Køres automatisk af den ugentlige pipeline eller manuelt.

Boglisten i Excel opdateres separat med fetch_hardcover_books.py.
"""
import json, openpyxl, os

EXCEL_PATH = os.path.join(os.path.dirname(__file__), 'audioboeger_tbr.xlsx')
OUT_PATH   = os.path.join(os.path.dirname(__file__), 'næste_læsning_quiz.html')

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

        src = {'BookBeat':'BB','Libby':'LB','Spotify':'SP','Lokal':'LK','Ingen':'–'}.get(source, '–')

        try: r = float(rating_raw)
        except: r = 0.0

        books.append({"t": title, "a": ws.cell(row,3).value or "",
                      "s": src, "g": list(all_tags),
                      "sp": sp, "r": r, "sl": sl,
                      "id": ws.cell(row, 9).value or 0})
    return books

# NOTE: Template uses plain { } — we use str.replace(), NOT .format()
HTML_TEMPLATE = """\
<!DOCTYPE html>
<html lang="da">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>📚 Hvad skal jeg læse næste?</title>
<style>
:root{--bg:#0f1117;--card:#1a1d27;--card2:#22263a;--accent:#c084fc;--accent2:#818cf8;--gold:#fbbf24;--green:#34d399;--blue:#60a5fa;--pink:#f472b6;--orange:#fb923c;--text:#e2e8f0;--muted:#94a3b8;--border:#2d3148;}
*{box-sizing:border-box;margin:0;padding:0;}
body{background:var(--bg);color:var(--text);font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;min-height:100vh;padding:24px 16px 60px;}
.container{max-width:680px;margin:0 auto;}
h1{font-size:1.6rem;font-weight:700;text-align:center;margin-bottom:6px;background:linear-gradient(135deg,var(--accent),var(--accent2));-webkit-background-clip:text;-webkit-text-fill-color:transparent;}
.subtitle{text-align:center;color:var(--muted);font-size:0.9rem;margin-bottom:32px;}
.progress-wrap{display:flex;gap:8px;margin-bottom:28px;align-items:center;}
.progress-step{flex:1;height:4px;border-radius:2px;background:var(--border);transition:background 0.3s;}
.progress-step.done{background:var(--accent);}
.progress-step.active{background:linear-gradient(90deg,var(--accent),var(--accent2));}
.progress-label{color:var(--muted);font-size:0.78rem;white-space:nowrap;}
.question-card{background:var(--card);border:1px solid var(--border);border-radius:16px;padding:28px;margin-bottom:20px;}
.question-emoji{font-size:2rem;margin-bottom:10px;display:block;}
.question-title{font-size:1.15rem;font-weight:600;margin-bottom:6px;}
.question-sub{color:var(--muted);font-size:0.85rem;margin-bottom:20px;}
.options{display:grid;gap:10px;}
.options.two-col{grid-template-columns:1fr 1fr;}
.multi-hint{color:var(--muted);font-size:0.8rem;margin-bottom:12px;font-style:italic;}
.option-btn{background:var(--card2);border:1.5px solid var(--border);border-radius:12px;padding:14px 16px;cursor:pointer;text-align:left;color:var(--text);transition:border-color 0.18s,background 0.18s;display:flex;align-items:flex-start;gap:10px;font-size:0.9rem;line-height:1.4;width:100%;touch-action:manipulation;-webkit-tap-highlight-color:transparent;}
@media(hover:hover){.option-btn:hover:not(.zero-match){border-color:var(--accent);background:#2a2d45;}}
.option-btn.selected{border-color:var(--accent);background:#2e2050;color:#fff;}
.option-btn.multi-selected{border-color:var(--accent2);background:#1e2545;color:#fff;}
.option-btn.zero-match{opacity:0.35;cursor:not-allowed;}
.opt-icon{font-size:1.4rem;flex-shrink:0;margin-top:1px;}
.opt-label{font-weight:600;display:block;}
.opt-desc{color:var(--muted);font-size:0.8rem;margin-top:2px;display:block;}
.option-btn.selected .opt-desc,.option-btn.multi-selected .opt-desc{color:#c4b5fd;}
.opt-count{display:inline-block;margin-left:6px;font-size:0.73rem;font-weight:700;padding:1px 7px;border-radius:20px;background:#2a2d45;color:var(--muted);vertical-align:middle;}
.opt-count.good{background:#2e2050;color:#c4b5fd;}
.opt-count.zero{background:#2a2020;color:#ef4444;}
.nav-row{display:flex;gap:12px;justify-content:flex-end;margin-top:16px;}
.btn-back{background:transparent;border:1.5px solid var(--border);color:var(--muted);border-radius:10px;padding:10px 20px;cursor:pointer;font-size:0.9rem;transition:border-color 0.18s,color 0.18s;touch-action:manipulation;-webkit-tap-highlight-color:transparent;}
@media(hover:hover){.btn-back:hover{border-color:var(--muted);color:var(--text);}}
.btn-next{background:linear-gradient(135deg,var(--accent),var(--accent2));color:white;border:none;border-radius:10px;padding:10px 24px;cursor:pointer;font-size:0.9rem;font-weight:600;transition:opacity 0.18s;touch-action:manipulation;-webkit-tap-highlight-color:transparent;}
@media(hover:hover){.btn-next:hover{opacity:0.9;}}
.btn-next:disabled{opacity:0.4;cursor:not-allowed;}
#results{display:none;}
.results-header{text-align:center;margin-bottom:24px;}
.results-header h2{font-size:1.3rem;font-weight:700;}
.results-header p{color:var(--muted);font-size:0.88rem;margin-top:6px;}
.book-card{background:var(--card);border:1px solid var(--border);border-radius:14px;padding:18px 20px;margin-bottom:12px;display:flex;gap:16px;align-items:flex-start;}
.book-rank{font-size:1.5rem;flex-shrink:0;width:32px;text-align:center;margin-top:2px;}
.book-info{flex:1;min-width:0;}
.book-title{font-weight:700;font-size:1rem;margin-bottom:2px;}
.book-author{color:var(--muted);font-size:0.83rem;margin-bottom:8px;}
.book-meta{display:flex;flex-wrap:wrap;gap:6px;align-items:center;}
.badge{padding:3px 9px;border-radius:20px;font-size:0.73rem;font-weight:600;white-space:nowrap;}
.badge-bb{background:#1d3a2f;color:var(--green);border:1px solid #2d5a47;}
.badge-lb{background:#1a2d4a;color:var(--blue);border:1px solid #2a4a7a;}
.badge-sp{background:#1d2d1a;color:#4ade80;border:1px solid #2d4a27;}
.badge-lk{background:#2a1a3a;color:#e879f9;border:1px solid #5b2d8e;}
.badge-none{background:#2a2030;color:var(--muted);border:1px solid var(--border);}
.spice-dots{display:flex;gap:2px;align-items:center;}
.spice-dot{width:7px;height:7px;border-radius:50%;background:var(--border);}
.spice-dot.lit{background:var(--orange);}
.tag-pill{background:var(--card2);border:1px solid var(--border);padding:2px 8px;border-radius:20px;font-size:0.72rem;color:var(--muted);}
.star-rating{color:var(--gold);font-size:0.8rem;}
.restart-btn{display:block;margin:24px auto 0;background:transparent;border:1.5px solid var(--border);color:var(--muted);border-radius:10px;padding:10px 24px;cursor:pointer;font-size:0.9rem;touch-action:manipulation;-webkit-tap-highlight-color:transparent;}
@media(hover:hover){.restart-btn:hover{border-color:var(--accent);color:var(--text);}}
.load-more-btn{display:block;margin:16px auto 0;background:transparent;border:1.5px solid var(--accent2);color:var(--accent2);border-radius:10px;padding:10px 28px;cursor:pointer;font-size:0.9rem;font-weight:600;touch-action:manipulation;-webkit-tap-highlight-color:transparent;transition:border-color 0.18s,color 0.18s,background 0.18s;}
@media(hover:hover){.load-more-btn:hover{background:#1e2545;border-color:var(--accent);color:var(--accent);}}
.upnext-btn{background:transparent;border:1.5px solid var(--border);color:var(--muted);border-radius:8px;padding:5px 12px;cursor:pointer;font-size:0.78rem;touch-action:manipulation;-webkit-tap-highlight-color:transparent;transition:border-color 0.18s,color 0.18s;}
@media(hover:hover){.upnext-btn:hover{border-color:var(--accent);color:var(--accent);}}
.upnext-btn.success{border-color:var(--green);color:var(--green);cursor:default;}
.upnext-btn:disabled{opacity:0.6;cursor:default;}
.no-results{text-align:center;padding:40px;color:var(--muted);}
@media(max-width:520px){.options.two-col{grid-template-columns:1fr;}.book-card{flex-direction:column;gap:10px;}}
</style>
</head>
<body>
<div class="container">
  <h1>📚 Hvad skal jeg læse næste?</h1>
  <p class="subtitle">Svar på 5 spørgsmål og få anbefalinger fra din to-read liste · <span id="total-count"></span> bøger</p>
  <div class="progress-wrap">
    <div class="progress-step active" id="ps1"></div>
    <div class="progress-step" id="ps2"></div>
    <div class="progress-step" id="ps3"></div>
    <div class="progress-step" id="ps4"></div>
    <div class="progress-step" id="ps5"></div>
    <span class="progress-label" id="progress-label">1 / 5</span>
  </div>

  <div id="step1" class="question-card">
    <span class="question-emoji">🌡️</span>
    <div class="question-title">Hvad er din stemning lige nu?</div>
    <div class="question-sub">Vælg den vibe du har lyst til</div>
    <div class="options two-col" id="q1-opts">
      <button class="option-btn" data-val="light" onclick="selectSingle(this,'q1')">
        <span class="opt-icon">☀️</span><span><span class="opt-label">Let &amp; sjov <span class="opt-count" id="cnt-light"></span></span><span class="opt-desc">Fluffy, sjov og feel-good</span></span>
      </button>
      <button class="option-btn" data-val="emotional" onclick="selectSingle(this,'q1')">
        <span class="opt-icon">💔</span><span><span class="opt-label">Dyb &amp; følelsesladet <span class="opt-count" id="cnt-emotional"></span></span><span class="opt-desc">Angst, tårer og den gode smerte</span></span>
      </button>
      <button class="option-btn" data-val="dark" onclick="selectSingle(this,'q1')">
        <span class="opt-icon">🌑</span><span><span class="opt-label">Mørk &amp; intens <span class="opt-count" id="cnt-dark"></span></span><span class="opt-desc">Thriller, mystery eller dark romance</span></span>
      </button>
      <button class="option-btn" data-val="fantasy" onclick="selectSingle(this,'q1')">
        <span class="opt-icon">✨</span><span><span class="opt-label">Magisk &amp; eventyrlig <span class="opt-count" id="cnt-fantasy-mood"></span></span><span class="opt-desc">Fantasy, magi eller det overnaturlige</span></span>
      </button>
    </div>
    <div class="nav-row"><button class="btn-next" id="next1" disabled onclick="goNext(1)">Næste →</button></div>
  </div>

  <div id="step2" class="question-card" style="display:none">
    <span class="question-emoji">💘</span>
    <div class="question-title">Hvilken plot-dynamik tiltrækker dig?</div>
    <div class="question-sub">Vælg op til 3</div>
    <div class="multi-hint">☝️ Du kan vælge flere</div>
    <div class="options two-col" id="q2-opts">
      <button class="option-btn" data-val="enemies to lovers" onclick="selectMulti(this,'q2',3)">
        <span class="opt-icon">⚔️</span><span><span class="opt-label">Enemies to lovers <span class="opt-count" id="cnt-etl"></span></span><span class="opt-desc">Fra had til kærlighed</span></span>
      </button>
      <button class="option-btn" data-val="forced proximity" onclick="selectMulti(this,'q2',3)">
        <span class="opt-icon">🏠</span><span><span class="opt-label">Forced proximity <span class="opt-count" id="cnt-fp"></span></span><span class="opt-desc">Fanget sammen mod deres vilje</span></span>
      </button>
      <button class="option-btn" data-val="grumpy & sunshine" onclick="selectMulti(this,'q2',3)">
        <span class="opt-icon">😠☀️</span><span><span class="opt-label">Grumpy &amp; sunshine <span class="opt-count" id="cnt-gs"></span></span><span class="opt-desc">Den sure og den solrige</span></span>
      </button>
      <button class="option-btn" data-val="slow burn" onclick="selectMulti(this,'q2',3)">
        <span class="opt-icon">🕯️</span><span><span class="opt-label">Slow burn <span class="opt-count" id="cnt-sb"></span></span><span class="opt-desc">Spænding der bygger langsomt op</span></span>
      </button>
      <button class="option-btn" data-val="friends to lovers" onclick="selectMulti(this,'q2',3)">
        <span class="opt-icon">💫</span><span><span class="opt-label">Friends to lovers <span class="opt-count" id="cnt-ftl"></span></span><span class="opt-desc">Venskab der bliver til kærlighed</span></span>
      </button>
      <button class="option-btn" data-val="second chances" onclick="selectMulti(this,'q2',3)">
        <span class="opt-icon">🔄</span><span><span class="opt-label">Second chances <span class="opt-count" id="cnt-sc"></span></span><span class="opt-desc">Gamle flamme mødes igen</span></span>
      </button>
      <button class="option-btn" data-val="fake relationship" onclick="selectMulti(this,'q2',3)">
        <span class="opt-icon">🎭</span><span><span class="opt-label">Fake relationship <span class="opt-count" id="cnt-fr"></span></span><span class="opt-desc">Det starter som en aftale...</span></span>
      </button>
      <button class="option-btn" data-val="any_trope" onclick="selectMulti(this,'q2',3)">
        <span class="opt-icon">🎲</span><span><span class="opt-label">Overrask mig!</span><span class="opt-desc">Ingen præference</span></span>
      </button>
    </div>
    <div class="nav-row">
      <button class="btn-back" onclick="goBack(2)">← Tilbage</button>
      <button class="btn-next" id="next2" disabled onclick="goNext(2)">Næste →</button>
    </div>
  </div>

  <div id="step3" class="question-card" style="display:none">
    <span class="question-emoji">🌍</span>
    <div class="question-title">Hvilken verden vil du ind i?</div>
    <div class="question-sub">Vælg genre/setting</div>
    <div class="options two-col" id="q3-opts">
      <button class="option-btn" data-val="contemporary" onclick="selectSingle(this,'q3')">
        <span class="opt-icon">🏙️</span><span><span class="opt-label">Moderne virkelighed <span class="opt-count" id="cnt-contemp"></span></span><span class="opt-desc">Contemporary — nutidens verden</span></span>
      </button>
      <button class="option-btn" data-val="fantasy" onclick="selectSingle(this,'q3')">
        <span class="opt-icon">🐉</span><span><span class="opt-label">Fantasy &amp; magi <span class="opt-count" id="cnt-fantasy-genre"></span></span><span class="opt-desc">Overnaturlig, fae, paranormal</span></span>
      </button>
      <button class="option-btn" data-val="historical" onclick="selectSingle(this,'q3')">
        <span class="opt-icon">🏰</span><span><span class="opt-label">Historisk <span class="opt-count" id="cnt-hist"></span></span><span class="opt-desc">Regency, viktoriansk, fortiden</span></span>
      </button>
      <button class="option-btn" data-val="thriller" onclick="selectSingle(this,'q3')">
        <span class="opt-icon">🔪</span><span><span class="opt-label">Thriller &amp; krimi <span class="opt-count" id="cnt-thriller"></span></span><span class="opt-desc">Mystery, suspense, dark</span></span>
      </button>
      <button class="option-btn" data-val="sports" onclick="selectSingle(this,'q3')">
        <span class="opt-icon">🏒</span><span><span class="opt-label">Sports romance <span class="opt-count" id="cnt-sports"></span></span><span class="opt-desc">Hockey, fodbold, tennis...</span></span>
      </button>
      <button class="option-btn" data-val="any_genre" onclick="selectSingle(this,'q3')">
        <span class="opt-icon">🎯</span><span><span class="opt-label">Ligegyldigt</span><span class="opt-desc">Bare noget godt</span></span>
      </button>
    </div>
    <div class="nav-row">
      <button class="btn-back" onclick="goBack(3)">← Tilbage</button>
      <button class="btn-next" id="next3" disabled onclick="goNext(3)">Næste →</button>
    </div>
  </div>

  <div id="step4" class="question-card" style="display:none">
    <span class="question-emoji">🌶️</span>
    <div class="question-title">Hvor meget spice skal der være?</div>
    <div class="question-sub">Romance.io spice scale 1–5</div>
    <div class="options" id="q4-opts">
      <button class="option-btn" data-val="low" onclick="selectSingle(this,'q4')">
        <span class="opt-icon">🌸</span><span><span class="opt-label">Kysk (1–2) <span class="opt-count" id="cnt-spice-low"></span></span><span class="opt-desc">Glimpses &amp; kisses — romantik uden eksplicit indhold</span></span>
      </button>
      <button class="option-btn" data-val="medium" onclick="selectSingle(this,'q4')">
        <span class="opt-icon">🔥</span><span><span class="opt-label">Medium (3) <span class="opt-count" id="cnt-spice-med"></span></span><span class="opt-desc">Open door — der sker noget, men med smag</span></span>
      </button>
      <button class="option-btn" data-val="high" onclick="selectSingle(this,'q4')">
        <span class="opt-icon">🌶️🌶️</span><span><span class="opt-label">Hedt (4–5) <span class="opt-count" id="cnt-spice-high"></span></span><span class="opt-desc">Eksplicit og rigeligt</span></span>
      </button>
      <button class="option-btn" data-val="any_spice" onclick="selectSingle(this,'q4')">
        <span class="opt-icon">🎲</span><span><span class="opt-label">Ligegyldigt <span class="opt-count" id="cnt-spice-any"></span></span><span class="opt-desc">Alle spice-niveauer (inkl. bøger uden data)</span></span>
      </button>
    </div>
    <div class="nav-row">
      <button class="btn-back" onclick="goBack(4)">← Tilbage</button>
      <button class="btn-next" id="next4" disabled onclick="goNext(4)">Næste →</button>
    </div>
  </div>

  <div id="step5" class="question-card" style="display:none">
    <span class="question-emoji">🎧</span>
    <div class="question-title">Vil du lytte til den nu?</div>
    <div class="question-sub">Filter på tilgængelighed</div>
    <div class="options" id="q5-opts">
      <button class="option-btn" data-val="available" onclick="selectSingle(this,'q5')">
        <span class="opt-icon">✅</span><span><span class="opt-label">Ja — kun tilgængelige <span class="opt-count" id="cnt-avail"></span></span><span class="opt-desc">BookBeat, Libby, Spotify eller Lokal</span></span>
      </button>
      <button class="option-btn" data-val="all" onclick="selectSingle(this,'q5')">
        <span class="opt-icon">📚</span><span><span class="opt-label">Vis alle <span class="opt-count" id="cnt-all"></span></span><span class="opt-desc">Inkl. bøger uden adgang endnu</span></span>
      </button>
    </div>
    <div class="nav-row">
      <button class="btn-back" onclick="goBack(5)">← Tilbage</button>
      <button class="btn-next" id="next5" disabled onclick="showResults()">Se anbefalinger 🎉</button>
    </div>
  </div>

  <div id="results">
    <div class="results-header">
      <h2>Dine anbefalinger ✨</h2>
      <p id="results-sub"></p>
    </div>
    <div id="book-list"></div>
    <button class="load-more-btn" id="load-more-btn" style="display:none" onclick="loadMore()">Vis flere →</button>
    <button class="restart-btn" onclick="restart()">🔄 Prøv igen</button>
  </div>
</div>

<script>
const BOOKS = BOOKS_DATA_PLACEHOLDER;

const answers = {q1:null,q2:[],q3:null,q4:null,q5:null};
let currentStep = 1;

// ── Count helpers ─────────────────────────────────────────────────────────────
function hasTags(book, ...tags) { return tags.some(t => book.g.includes(t)); }

function moodFilter(mood) {
  return b => {
    if (mood === 'light')     return hasTags(b,'funny','lighthearted','hopeful');
    if (mood === 'emotional') return hasTags(b,'emotional','angst','sad');
    if (mood === 'dark')      return hasTags(b,'dark','tense','thriller','mystery','suspense','dark romance');
    if (mood === 'fantasy')   return hasTags(b,'fantasy','magic','paranormal','fae','adventurous');
    return true;
  };
}

function tropeFilter(tropes) {
  if (!tropes.length || tropes.includes('any_trope')) return () => true;
  return b => tropes.some(t => b.g.includes(t));
}

function genreFilter(genre) {
  if (!genre || genre === 'any_genre') return () => true;
  return b => {
    if (genre === 'contemporary') return hasTags(b,'contemporary');
    if (genre === 'fantasy')      return hasTags(b,'fantasy','magic','paranormal','fae','high fantasy');
    if (genre === 'historical')   return hasTags(b,'historical','regency');
    if (genre === 'thriller')     return hasTags(b,'thriller','mystery','suspense','dark');
    if (genre === 'sports')       return hasTags(b,'sports','hockey','football','tennis','basketball','baseball','swimming');
    return true;
  };
}

function spiceFilter(spice) {
  if (!spice || spice === 'any_spice') return () => true;
  return b => {
    if (spice === 'low')    return b.sp >= 1 && b.sp <= 2;
    if (spice === 'medium') return b.sp === 3;
    if (spice === 'high')   return b.sp >= 4;
    return true;
  };
}

function cnt(filterFn, base) {
  return (base || BOOKS).filter(filterFn).length;
}

function setCount(id, n) {
  const el = document.getElementById(id);
  if (!el) return;
  el.textContent = n;
  el.className = 'opt-count' + (n === 0 ? ' zero' : n > 10 ? ' good' : '');
  const btn = el.closest('.option-btn');
  if (btn) {
    btn.classList.toggle('zero-match', n === 0);
    if (n === 0 && (btn.classList.contains('selected') || btn.classList.contains('multi-selected'))) {
      btn.classList.remove('selected','multi-selected');
    }
  }
}

function updateCounts() {
  document.getElementById('total-count').textContent = BOOKS.length;

  // Q1 — full BOOKS
  setCount('cnt-light',        cnt(b => hasTags(b,'funny','lighthearted','hopeful')));
  setCount('cnt-emotional',    cnt(b => hasTags(b,'emotional','angst','sad')));
  setCount('cnt-dark',         cnt(b => hasTags(b,'dark','tense','thriller','mystery','suspense','dark romance')));
  setCount('cnt-fantasy-mood', cnt(b => hasTags(b,'fantasy','magic','paranormal','fae','adventurous')));

  // Q2 — filtered by Q1
  const q1pool = answers.q1 ? BOOKS.filter(moodFilter(answers.q1)) : BOOKS;
  setCount('cnt-etl', cnt(b => b.g.includes('enemies to lovers'), q1pool));
  setCount('cnt-fp',  cnt(b => b.g.includes('forced proximity'),  q1pool));
  setCount('cnt-gs',  cnt(b => b.g.includes('grumpy & sunshine'), q1pool));
  setCount('cnt-sb',  cnt(b => b.g.includes('slow burn'),         q1pool));
  setCount('cnt-ftl', cnt(b => b.g.includes('friends to lovers'), q1pool));
  setCount('cnt-sc',  cnt(b => b.g.includes('second chances'),    q1pool));
  setCount('cnt-fr',  cnt(b => b.g.includes('fake relationship'),  q1pool));

  // Q3 — filtered by Q1+Q2
  const q2pool = BOOKS.filter(answers.q1 ? moodFilter(answers.q1) : ()=>true).filter(tropeFilter(answers.q2));
  setCount('cnt-contemp',       cnt(b => hasTags(b,'contemporary'),                                     q2pool));
  setCount('cnt-fantasy-genre', cnt(b => hasTags(b,'fantasy','magic','paranormal','fae','high fantasy'), q2pool));
  setCount('cnt-hist',          cnt(b => hasTags(b,'historical','regency'),                             q2pool));
  setCount('cnt-thriller',      cnt(b => hasTags(b,'thriller','mystery','suspense','dark'),              q2pool));
  setCount('cnt-sports',        cnt(b => hasTags(b,'sports','hockey','football','tennis','basketball','baseball','swimming'), q2pool));

  // Q4 — filtered by Q1+Q2+Q3
  const q3pool = q2pool.filter(genreFilter(answers.q3));
  setCount('cnt-spice-low',  cnt(b => b.sp >= 1 && b.sp <= 2, q3pool));
  setCount('cnt-spice-med',  cnt(b => b.sp === 3,             q3pool));
  setCount('cnt-spice-high', cnt(b => b.sp >= 4,              q3pool));
  setCount('cnt-spice-any',  q3pool.length);

  // Q5 — filtered by Q1+Q2+Q3+Q4
  const q4pool = q3pool.filter(spiceFilter(answers.q4));
  setCount('cnt-avail', cnt(b => b.s !== '–', q4pool));
  setCount('cnt-all',   q4pool.length);
}

// ── Selection ─────────────────────────────────────────────────────────────────
function selectSingle(btn, q) {
  if (btn.classList.contains('zero-match')) return;
  document.querySelectorAll('#' + q + '-opts .option-btn').forEach(b => b.classList.remove('selected'));
  btn.classList.add('selected');
  answers[q] = btn.dataset.val;
  document.getElementById('next' + q.replace('q','')).disabled = false;
  updateCounts();
}

function selectMulti(btn, q, max) {
  if (btn.classList.contains('zero-match') && btn.dataset.val !== 'any_trope') return;
  if (btn.dataset.val === 'any_trope') {
    document.querySelectorAll('#' + q + '-opts .option-btn').forEach(b => b.classList.remove('multi-selected'));
    btn.classList.add('multi-selected');
    answers[q] = ['any_trope'];
  } else {
    const anyBtn = document.querySelector('#' + q + '-opts [data-val="any_trope"]');
    if (anyBtn) anyBtn.classList.remove('multi-selected');
    if (btn.classList.contains('multi-selected')) {
      btn.classList.remove('multi-selected');
      answers[q] = answers[q].filter(v => v !== btn.dataset.val);
    } else {
      const current = answers[q].filter(v => v !== 'any_trope');
      if (current.length >= max) return;
      btn.classList.add('multi-selected');
      answers[q] = [...current, btn.dataset.val];
    }
  }
  document.getElementById('next' + q.replace('q','')).disabled = answers[q].length === 0;
  updateCounts();
}

// ── Navigation ────────────────────────────────────────────────────────────────
function goNext(step) {
  document.getElementById('step' + step).style.display = 'none';
  document.getElementById('step' + (step+1)).style.display = 'block';
  currentStep = step + 1;
  updateProgress();
  updateCounts();
}

function goBack(step) {
  document.getElementById('step' + step).style.display = 'none';
  document.getElementById('step' + (step-1)).style.display = 'block';
  currentStep = step - 1;
  updateProgress();
}

function updateProgress() {
  for (let i=1;i<=5;i++) {
    const el = document.getElementById('ps'+i);
    el.className = 'progress-step' + (i<currentStep?' done':i===currentStep?' active':'');
  }
  document.getElementById('progress-label').textContent = currentStep + ' / 5';
}

// ── Scoring ───────────────────────────────────────────────────────────────────
function scoreBook(book) {
  let score = 0;
  const tags = book.g;
  const has = (...t) => t.some(tag => tags.includes(tag));

  const mood = answers.q1;
  if (mood==='light')     { if(has('funny','lighthearted'))score+=3; if(has('hopeful'))score+=1; if(has('dark','tense','angst'))score-=2; }
  if (mood==='emotional') { if(has('emotional','angst'))score+=3; if(has('sad','hopeful'))score+=1; if(has('lighthearted','funny'))score-=1; }
  if (mood==='dark')      { if(has('dark','tense','thriller','mystery','suspense','dark romance'))score+=3; if(has('possessive hero','alpha male'))score+=1; if(has('lighthearted','funny'))score-=2; }
  if (mood==='fantasy')   { if(has('fantasy','magic','paranormal','fae'))score+=4; if(has('adventurous','mysterious'))score+=1; if(has('contemporary'))score-=1; }

  const tropes = answers.q2;
  if (!tropes.includes('any_trope')) {
    tropes.forEach(t => { if(tags.includes(t)) score+=3; });
    if(tropes.length>0 && !tropes.some(t=>tags.includes(t))) score-=1;
  }

  const genre = answers.q3;
  if(genre==='contemporary'&& has('contemporary'))score+=3;
  else if(genre==='fantasy'  && has('fantasy','magic','paranormal','fae','high fantasy'))score+=4;
  else if(genre==='historical'&&has('historical','regency'))score+=4;
  else if(genre==='thriller' && has('thriller','mystery','suspense','dark'))score+=3;
  else if(genre==='sports'   && has('sports','hockey','football','tennis','basketball','baseball','swimming'))score+=4;
  else if(genre && genre!=='any_genre') score-=2;

  const spice = answers.q4;
  if(spice==='low'    && book.sp>0) { score += book.sp<=2?2:book.sp>=4?-3:0; }
  if(spice==='medium') { score += book.sp===3?2:book.sp===2||book.sp===4?1:0; }
  if(spice==='high')   { score += book.sp>=4?2:book.sp>=3?1:book.sp>0?-1:0; }

  if(book.r>=4.0) score+=1;
  if(book.r>=4.3) score+=1;
  return score;
}

// ── Results ───────────────────────────────────────────────────────────────────
const PAGE_SIZE = 8;
let _scoredBooks = [];
let _shownCount = 0;
let _rankOffset = 0;

function getBadge(src) {
  if(src==='BB') return '<span class="badge badge-bb">📗 BookBeat</span>';
  if(src==='LB') return '<span class="badge badge-lb">📘 Libby</span>';
  if(src==='SP') return '<span class="badge badge-sp">🎵 Spotify</span>';
  if(src==='LK') return '<span class="badge badge-lk">💾 Lokal</span>';
  return '<span class="badge badge-none">📖 Ingen adgang</span>';
}

function getSpice(sp,sl) {
  if(!sp) return '';
  const dots=Array.from({length:5},(_,i)=>`<span class="spice-dot${i<sp?' lit':''}"></span>`).join('');
  const lbl=sl?` <span style="color:var(--muted);font-size:0.72rem">${sl}</span>`:'';
  return `<span class="spice-dots">${dots}</span>${lbl}`;
}

function renderBookCard(b, rank) {
  const medals=['🥇','🥈','🥉','4️⃣','5️⃣','6️⃣','7️⃣','8️⃣','9️⃣','🔟'];
  const rankDisplay = rank < medals.length ? medals[rank] : `<span style="font-size:1rem;color:var(--muted)">#${rank+1}</span>`;
  const showTags=b.g.filter(t=>!['fiction','romance','medium-paced','fast-paced','slow-paced','m-f romance'].includes(t)).slice(0,4).map(t=>`<span class="tag-pill">${t}</span>`).join('');
  const rHTML=b.r?`<span class="star-rating">★</span> <span style="font-size:0.8rem">${b.r.toFixed(1)}</span>`:'';
  const safeTitle=b.t.replace(/\\\\/g,'\\\\\\\\').replace(/'/g,"\\\\'");
  const upnextBtn=b.id?`<button class="upnext-btn" onclick="addToUpNext(this,${b.id},'${safeTitle}')">📌 Up Next</button>`:'';
  return `<div class="book-card"><div class="book-rank">${rankDisplay}</div><div class="book-info"><div class="book-title">${b.t}</div><div class="book-author">${b.a}</div><div class="book-meta">${getBadge(b.s)}${b.sp?getSpice(b.sp,b.sl):''}${rHTML}</div><div style="margin-top:8px;display:flex;flex-wrap:wrap;gap:4px">${showTags}</div>${upnextBtn?`<div style="margin-top:10px">${upnextBtn}</div>`:''}</div></div>`;
}

function showResults() {
  for(let i=1;i<=5;i++) document.getElementById('step'+i).style.display='none';
  document.getElementById('results').style.display='block';

  const onlyAvail = answers.q5==='available';
  let pool = onlyAvail ? BOOKS.filter(b=>b.s!=='–') : BOOKS;
  _scoredBooks = pool.map(b=>({...b,score:scoreBook(b)})).sort((a,b)=>b.score-a.score||b.r-a.r);
  _shownCount = 0;

  document.getElementById('results-sub').textContent =
    `Vurderet ud fra ${pool.length} bøger · ${onlyAvail?'Kun tilgængelige på dine platforme':'Alle bøger i din to-read liste'}`;

  if(!_scoredBooks.length){
    document.getElementById('book-list').innerHTML='<div class="no-results"><div style="font-size:2.5rem">🔍</div><p style="margin-top:12px">Ingen bøger matchede. Prøv at justere filtrene.</p></div>';
    return;
  }

  document.getElementById('book-list').innerHTML = '';
  appendBooks();

  document.querySelectorAll('.progress-step').forEach(el=>el.className='progress-step done');
  document.getElementById('progress-label').textContent='Færdig! 🎉';
}

function appendBooks() {
  const batch = _scoredBooks.slice(_shownCount, _shownCount + PAGE_SIZE);
  const startRank = _shownCount;
  document.getElementById('book-list').insertAdjacentHTML('beforeend',
    batch.map((b, i) => renderBookCard(b, startRank + i)).join('')
  );
  _shownCount += batch.length;
  const btn = document.getElementById('load-more-btn');
  if (_shownCount < _scoredBooks.length) {
    const remaining = _scoredBooks.length - _shownCount;
    btn.textContent = `Vis ${Math.min(PAGE_SIZE, remaining)} flere → (${remaining} tilbage)`;
    btn.style.display = 'block';
  } else {
    btn.style.display = 'none';
  }
}

function loadMore() {
  appendBooks();
}

function restart() {
  answers.q1=null;answers.q2=[];answers.q3=null;answers.q4=null;answers.q5=null;
  currentStep=1;
  _scoredBooks=[];_shownCount=0;
  document.getElementById('results').style.display='none';
  document.getElementById('load-more-btn').style.display='none';
  document.querySelectorAll('.option-btn').forEach(b=>b.classList.remove('selected','multi-selected','zero-match'));
  ['next1','next2','next3','next4','next5'].forEach(id=>{const b=document.getElementById(id);if(b)b.disabled=true;});
  for(let i=2;i<=5;i++) document.getElementById('step'+i).style.display='none';
  document.getElementById('step1').style.display='block';
  updateProgress();
  updateCounts();
}

// ── Hardcover "Up Next" ───────────────────────────────────────────────────────
const HC_UP_NEXT_LIST = 465056;
const HC_WORKER_URL = 'https://lucky-cloud-343c.xenia-9cc.workers.dev';

async function addToUpNext(btn, bookId, title) {
  btn.disabled = true;
  btn.textContent = '⏳';
  try {
    const r = await fetch(HC_WORKER_URL, {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({book_id: bookId, list_id: HC_UP_NEXT_LIST})
    });
    const d = await r.json();
    if (d.data?.insert_list_book?.list_book?.id) {
      btn.textContent = '✅ Tilføjet';
      btn.classList.add('success');
    } else {
      btn.textContent = '❌ Fejl';
      btn.disabled = false;
    }
  } catch(e) {
    btn.textContent = '❌ Fejl';
    btn.disabled = false;
  }
}

// Init
updateCounts();
</script>
</body>
</html>
"""

def generate():
    books = build_data()
    data_js = json.dumps(books, ensure_ascii=False, separators=(',',':'))
    html = HTML_TEMPLATE.replace('BOOKS_DATA_PLACEHOLDER', data_js)
    with open(OUT_PATH, 'w', encoding='utf-8') as f:
        f.write(html)
    print(f"Quiz genereret: {len(books)} bøger → {OUT_PATH}")
    return len(books)

if __name__ == '__main__':
    n = generate()
    print(f"✓ Færdig ({n} bøger)")
