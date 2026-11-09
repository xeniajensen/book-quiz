// Cloudflare Worker: HC API proxy for book-quiz
// Sæt HC_TOKEN som environment variable (Secret) i CF dashboard
// Deploy URL: bruges i generate_quiz.py som WORKER_URL
//
// Understøtter FEM handlinger (POST JSON body):
//   1. Tilføj bog til liste:      { book_id, list_id }
//   2. Hent bøger på en liste:    { action: "get_list", list_id }
//   3. Næste bog i serie (live):  { action: "next_in_series" }
//   3b. Live status (want/done):   { action: "tbr_status", ids: [...] }
//   4. Markér som i gang (status2):{ action: "add_currently_reading", book_id }
//   5. Live vibe + anti-vibe:     { action: "vibe", candidates: [...] }
// (2) bruges af quizzen til at vise "Up Next"-listen dynamisk ved hver page load,
// så bøger tilføjet i løbet af ugen straks dukker op uden en ny build.
// (3) kigger på dine SENESTE 3 læste bøger; hvis en af dem er i en uafsluttet
// serie, returnerer den den næste ulæste bog i den serie (nyeste finish først).
// (5) henter dine seneste 5 finishes LIVE fra HC og lader Claude syntetisere en
// vibe + en modsat vibe. Kræver ANTHROPIC_API_KEY som Secret. Svaret caches på
// dine seneste 5 bog-id'er, så Claude kun kaldes igen når du har læst noget nyt.

const HC_API = 'https://api.hardcover.app/v1/graphql';
const ALLOWED_ORIGIN = 'https://xeniajensen.github.io';
const USER_ID = 125471;      // Xenias Hardcover user_id
const LOOKBACK = 3;          // kig kun på de seneste N færdiglæste bøger
const VIBE_LOOKBACK = 5;     // vibe'en syntetiseres på tværs af de seneste N finishes
const VIBE_MODEL = 'claude-sonnet-5';
const VIBE_TTL = 2592000;    // 30 dage — cachen invalideres alligevel af nye finishes
const VIBE_MIN_CANDS = 50;   // afvis mistænkeligt små kandidatlister (siden sender 150)

// Kort, stabil hash (FNV-1a) af kandidat-id'erne. Indgår i cache-nøglen, så en
// ændret TBR giver et friskt svar i stedet for at genbruge et forældet.
function fnv1a(str) {
  let h = 0x811c9dc5;
  for (let i = 0; i < str.length; i++) {
    h ^= str.charCodeAt(i);
    h = (h + ((h << 1) + (h << 4) + (h << 7) + (h << 8) + (h << 24))) >>> 0;
  }
  return h.toString(36);
}

// Parser Claudes svar til { vibe, picks, opp_vibe, opp_picks }.
// Samme format som Cowork-stien i generate_up_next.py forventer.
function parseVibe(txt) {
  const out = { vibe: '', picks: [], opp_vibe: '', opp_picks: [] };
  let sec = 'v';
  String(txt || '').replace(/```[a-z]*|```/g, '').split(/\r?\n/)
    // fjern markdown-fedt og punkttegn, så "**123** - grund" også fanges
    .map(l => l.replace(/\*\*/g, '').replace(/^\s*[-•*]\s+/, '').trim())
    .filter(Boolean).forEach(l => {
      const om = l.match(/^opposite\s*[:\-]\s*(.+)/i);
      if (om) { out.opp_vibe = om[1].trim(); sec = 'o'; return; }
      const vm = l.match(/^vibe\s*[:\-]\s*(.+)/i);
      if (vm) { out.vibe = vm[1].trim(); sec = 'v'; return; }
      const m = l.match(/(\d{2,})\s*(?:::|\||\-|:)\s*(.+)/);
      if (m) {
        (sec === 'o' ? out.opp_picks : out.picks).push({
          id: parseInt(m[1], 10),
          reason: m[2].trim().replace(/^["'\s]+|["'\s]+$/g, '')
        });
      }
    });
  return out;
}

export default {
  async fetch(request, env) {
    const corsHeaders = {
      'Access-Control-Allow-Origin': ALLOWED_ORIGIN,
      'Access-Control-Allow-Methods': 'POST, OPTIONS',
      'Access-Control-Allow-Headers': 'Content-Type',
    };

    if (request.method === 'OPTIONS') {
      return new Response(null, { headers: corsHeaders });
    }

    if (request.method !== 'POST') {
      return new Response('Method not allowed', { status: 405, headers: corsHeaders });
    }

    const json = (obj, status = 200) => new Response(JSON.stringify(obj), {
      status, headers: { ...corsHeaders, 'Content-Type': 'application/json' }
    });

    const gql = async (query) => {
      const r = await fetch(HC_API, {
        method: 'POST',
        headers: { 'Authorization': env.HC_TOKEN, 'Content-Type': 'application/json' },
        body: JSON.stringify({ query })
      });
      const j = await r.json();
      if (j && j.errors) lastErr = j.errors[0] && j.errors[0].message;
      return j?.data || {};
    };
    let lastErr = null;

    try {
      const body = await request.json();
      const { action, book_id, list_id } = body;

      // ── (3) Næste ulæste bog i en aktivt igangværende serie ───────────────
      // Kigger på de seneste LOOKBACK færdiglæste bøger (status 3). For den
      // NYESTE af dem der ligger i en serie med en ulæst fortsættelse,
      // returneres den næste bog. Ellers { pick: null }.
      if (action === 'next_in_series') {
        const recent = (await gql(
          `query{user_books(where:{user_id:{_eq:${USER_ID}}, status_id:{_eq:3}, last_read_date:{_is_null:false}},` +
          ` order_by:{last_read_date:desc}, limit:${LOOKBACK}){` +
          ` rating last_read_date book{ id title book_series{ position series{ id name } } } }}`
        )).user_books || [];

        for (const ub of recent) {                       // nyeste finish først
          const bk = ub.book || {};
          const memberships = (bk.book_series || []).filter(bs => bs.series && bs.position != null);
          for (const bs of memberships) {
            const sid = bs.series.id, pos = bs.position;

            // dine læste positioner i denne serie (for at springe alt du har læst over)
            const mine = (await gql(
              `query{user_books(where:{user_id:{_eq:${USER_ID}}, status_id:{_eq:3},` +
              ` book:{book_series:{series_id:{_eq:${sid}}}}}){` +
              ` book{ book_series(where:{series_id:{_eq:${sid}}}){ position } } }}`
            )).user_books || [];
            const readPos = new Set();
            mine.forEach(m => (m.book?.book_series || []).forEach(x => { if (x.position != null) readPos.add(x.position); }));

            // Sprog på den netop læste bog = hyppigste language_id blandt dens editions.
            // Hardcover gemmer oversættelser som SEPARATE bog-records i samme serie/position,
            // så vi filtrerer serien til bøger med en edition på samme sprog (fx engelsk=1),
            // ellers foreslår vi en tysk/spansk udgave ved et uheld.
            const eds = (await gql(`query{editions(where:{book_id:{_eq:${bk.id}}}){language_id}}`)).editions || [];
            const counts = {};
            eds.forEach(e => { if (e.language_id != null) counts[e.language_id] = (counts[e.language_id] || 0) + 1; });
            let lang = null, best = 0;
            for (const k in counts) { if (counts[k] > best) { best = counts[k]; lang = parseInt(k, 10); } }
            const langFilter = lang != null ? `, book:{editions:{language_id:{_eq:${lang}}}}` : '';

            const rosterQ = (extra) => gql(
              `query{book_series(where:{series_id:{_eq:${sid}}${extra}}, order_by:{position:asc}){` +
              ` position book{ id title slug cached_image contributions{ author{name} contribution } } }}`
            ).then(d => d.book_series || []);
            const pickNext = (roster) => roster.find(e => e.position != null && e.position > pos && !readPos.has(e.position) && e.book);

            // næste = første bog med position > den netop læste, som du IKKE har læst, på samme sprog.
            let roster = await rosterQ(langFilter);
            let next = pickNext(roster);
            // fallback: intet på dit sprog -> prøv uden sprogfilter (hellere en udgave end ingenting)
            if (!next && langFilter) { roster = await rosterQ(''); next = pickNext(roster); }
            if (next) {
              const nb = next.book;
              const author = (nb.contributions || []).filter(c => !c.contribution || c.contribution === 'Author')
                .map(c => c.author && c.author.name).filter(Boolean).join(', ');
              return json({ pick: {
                id: nb.id, t: nb.title || '', a: author, sl: nb.slug || '',
                cover: nb.cached_image && nb.cached_image.url ? nb.cached_image.url : '',
                series: bs.series.name, snum: next.position,
                from: { t: bk.title || '', r: ub.rating, pos, date: ub.last_read_date }
              }});
            }
          }
        }
        return json({ pick: null, debug: { recent: recent.length, hasToken: !!env.HC_TOKEN, tokenStart: String(env.HC_TOKEN || '').slice(0, 7), lastErr } });
      }

      // ── (5) Live vibe + anti-vibe via Claude ──────────────────────────────
      // Siden sender sin kandidatliste (top deep-cuts fra TBR); workeren henter
      // selv de seneste finishes, så vibe'en følger din læsning og ikke det
      // ugentlige build. Cache-nøglen udledes KUN server-side (dine bog-id'er),
      // så nøglerummet er lukket og endpointet ikke kan spammes til nye kald.
      if (action === 'vibe') {
        if (!env.ANTHROPIC_API_KEY) return json({ error: 'ANTHROPIC_API_KEY mangler i worker' }, 503);
        const candidates = Array.isArray(body.candidates) ? body.candidates.slice(0, 150) : [];
        if (candidates.length < VIBE_MIN_CANDS) {
          return json({ error: `mindst ${VIBE_MIN_CANDS} candidates er påkrævet` }, 400);
        }

        const recentRaw = (await gql(
          `query{user_books(where:{user_id:{_eq:${USER_ID}}, status_id:{_eq:3}},` +
          ` order_by:{last_read_date:desc_nulls_last}, limit:${VIBE_LOOKBACK}){` +
          ` rating book{ id title contributions{ author{name} contribution } } }}`
        )).user_books || [];
        const recent = recentRaw.map(ub => {
          const bk = ub.book || {};
          return {
            id: bk.id,
            t: bk.title || '',
            a: (bk.contributions || []).filter(c => !c.contribution || c.contribution === 'Author')
                 .map(c => c.author && c.author.name).filter(Boolean).join(', ')
          };
        }).filter(r => r.t);
        if (!recent.length) return json({ error: 'ingen læste bøger fundet' }, 404);

        const cache = caches.default;
        // Nøgle = dine seneste finishes + hvilke bøger der var i puljen.
        const candFp = fnv1a(candidates.map(c => c.id).sort((a, b) => a - b).join(','));
        const cacheKey = new Request(
          'https://vibe.cache/v3?k=' + recent.map(r => r.id).join('-') + '&c=' + candFp);
        const hit = await cache.match(cacheKey);
        if (hit) { const c = await hit.json(); c.cached = true; return json(c); }

        const rl = recent.map(r => `"${r.t}" by ${r.a}`).join('; ');
        const prompt = `My last ${recent.length} finished books, newest first: ${rl}. Work only from the candidate TBR list (JSON), favoring lesser-known DEEP CUTS (lower "readers") over obvious bestsellers, and never repeat an ID between the two lists.
1) In ONE sentence capture the overall VIBE/mood these suggest I'm craving right now — synthesize across all of them, do NOT just list them — then pick 5 books that fit it.
2) In ONE sentence capture the OPPOSITE mood — something completely different from these recent reads, for when I want to flip my usual pattern (e.g. flip heavy→light, romance→other genre, dark→funny) — then pick 5 books that fit that opposite.
Return ONLY, in exactly this structure:
VIBE: <one sentence>
<5 lines, each "ID :: reason it fits the vibe">
OPPOSITE: <one sentence>
<5 lines, each "ID :: reason it contrasts my recent reads">

You MUST return exactly 5 IDs under VIBE and exactly 5 different IDs under OPPOSITE, all taken from the candidate list. If few candidates are a perfect fit for the opposite mood, pick the 5 closest ones rather than returning fewer. Keep each reason to one short sentence.

Candidate TBR list (JSON):
${JSON.stringify(candidates)}`;

        const ar = await fetch('https://api.anthropic.com/v1/messages', {
          method: 'POST',
          headers: {
            'x-api-key': env.ANTHROPIC_API_KEY,
            'anthropic-version': '2023-06-01',
            'content-type': 'application/json'
          },
          body: JSON.stringify({
            model: VIBE_MODEL,
            max_tokens: 2000,
            messages: [{ role: 'user', content: prompt }]
          })
        });
        const aj = await ar.json();
        if (!ar.ok || aj.error) {
          return json({ error: (aj.error && aj.error.message) || 'Anthropic-kald fejlede' }, 502);
        }
        const txt = (aj.content || []).map(c => c.text || '').join('');
        const parsed = parseVibe(txt);
        if (!parsed.vibe || !parsed.picks.length) {
          return json({ error: 'kunne ikke parse svaret fra Claude' }, 502);
        }

        const payload = { recent, ...parsed, cached: false, stop_reason: aj.stop_reason || null };
        // Cache KUN et fuldt svar (2x5 picks, ikke afkortet). Ellers ville et halvt
        // svar låse sig fast i 30 dage — netop det der skete med 2 anti-vibe picks.
        const complete = parsed.vibe && parsed.opp_vibe &&
                         parsed.picks.length >= 5 && parsed.opp_picks.length >= 5 &&
                         aj.stop_reason !== 'max_tokens';
        payload.complete = !!complete;
        if (complete) {
          await cache.put(cacheKey, new Response(JSON.stringify(payload), {
            headers: { 'Content-Type': 'application/json', 'Cache-Control': `max-age=${VIBE_TTL}` }
          }));
        }
        return json(payload);
      }

      // ── (4) Markér bog som "currently reading" (status 2) ─────────────────
      if (action === 'add_currently_reading') {
        if (!book_id) return json({ error: 'book_id er påkrævet' }, 400);
        const r = await fetch(HC_API, {
          method: 'POST',
          headers: { 'Authorization': env.HC_TOKEN, 'Content-Type': 'application/json' },
          body: JSON.stringify({ query:
            `mutation{insert_user_book(object:{book_id:${parseInt(book_id, 10)}, status_id:2}){id}}` })
        });
        return json(await r.json());
      }

      // ── (2) Læs bøger på en liste ─────────────────────────────────────────
      // ── (5) Live status: hvilke af bogens id'er står stadig som want-to-read? ──
      // Siden bruger det til at skjule bøger, der er læst / læses nu / droppet / fjernet fra TBR.
      // Svar: { want:[id], done:[id], ok:true }. done = ids (fra body.ids) med anden status end 1.
      if (action === 'tbr_status') {
        const ids = (Array.isArray(body.ids) ? body.ids : []).map(n => parseInt(n, 10)).filter(Boolean).slice(0, 1200);
        const want = [];
        for (let off = 0; off < 3000; off += 100) {
          const d = await gql(`query{user_books(where:{user_id:{_eq:${USER_ID}}, status_id:{_eq:1}}, limit:100, offset:${off}, order_by:{id:asc}){book_id}}`);
          const rows = d.user_books || [];
          rows.forEach(r => want.push(r.book_id));
          if (rows.length < 100) break;
        }
        const done = [];
        for (let i = 0; i < ids.length; i += 100) {
          const chunk = ids.slice(i, i + 100);
          const d = await gql(`query{user_books(where:{user_id:{_eq:${USER_ID}}, status_id:{_neq:1}, book_id:{_in:[${chunk.join(',')}]}}, limit:100){book_id}}`);
          (d.user_books || []).forEach(r => done.push(r.book_id));
        }
        return json({ want, done, ok: want.length > 0 });
      }

      if (action === 'get_list') {
        if (!list_id) return json({ error: 'list_id er påkrævet' }, 400);

        const query = `query{list_books(where:{list_id:{_eq:${parseInt(list_id, 10)}}}, order_by:{created_at:desc}){book_id book{title slug description cached_image contributions{author{name} contribution}}}}`;
        const hcResponse = await fetch(HC_API, {
          method: 'POST',
          headers: { 'Authorization': env.HC_TOKEN, 'Content-Type': 'application/json' },
          body: JSON.stringify({ query })
        });
        const data = await hcResponse.json();

        const books = (data?.data?.list_books || []).map(lb => {
          const bk = lb.book || {};
          const author = (bk.contributions || [])
            .filter(c => !c.contribution || c.contribution === 'Author')
            .map(c => c.author && c.author.name)
            .filter(Boolean)
            .join(', ');
          return {
            id: lb.book_id,
            t: bk.title || '',
            a: author,
            hc: bk.slug || '',
            desc: bk.description || '',
            cover: bk.cached_image && bk.cached_image.url ? bk.cached_image.url : ''
          };
        });
        return json({ books });
      }

      // ── (1) Tilføj bog til liste (uændret adfærd) ─────────────────────────
      if (!book_id || !list_id) {
        return json({ error: 'book_id og list_id er påkrævet' }, 400);
      }

      const hcResponse = await fetch(HC_API, {
        method: 'POST',
        headers: { 'Authorization': env.HC_TOKEN, 'Content-Type': 'application/json' },
        body: JSON.stringify({
          query: `mutation{insert_list_book(object:{list_id:${list_id},book_id:${book_id}}){list_book{id}}}`
        })
      });
      const data = await hcResponse.json();
      return json(data);

    } catch (e) {
      return json({ error: e.message }, 500);
    }
  }
};
