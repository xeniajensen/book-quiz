// Cloudflare Worker: HC API proxy for book-quiz
// Sæt HC_TOKEN som environment variable (Secret) i CF dashboard
// Deploy URL: bruges i generate_quiz.py som WORKER_URL
//
// Understøtter FIRE handlinger (POST JSON body):
//   1. Tilføj bog til liste:      { book_id, list_id }
//   2. Hent bøger på en liste:    { action: "get_list", list_id }
//   3. Næste bog i serie (live):  { action: "next_in_series" }
//   4. Markér som i gang (status2):{ action: "add_currently_reading", book_id }
// (2) bruges af quizzen til at vise "Up Next"-listen dynamisk ved hver page load,
// så bøger tilføjet i løbet af ugen straks dukker op uden en ny build.
// (3) kigger på dine SENESTE 3 læste bøger; hvis en af dem er i en uafsluttet
// serie, returnerer den den næste ulæste bog i den serie (nyeste finish først).

const HC_API = 'https://api.hardcover.app/v1/graphql';
const ALLOWED_ORIGIN = 'https://xeniajensen.github.io';
const USER_ID = 125471;      // Xenias Hardcover user_id
const LOOKBACK = 3;          // kig kun på de seneste N færdiglæste bøger

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
      return (await r.json())?.data || {};
    };

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
              const author = (nb.contributions || []).filter(c => !c.contribution)
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
        return json({ pick: null });
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
      if (action === 'get_list') {
        if (!list_id) return json({ error: 'list_id er påkrævet' }, 400);

        const query = `query{list_books(where:{list_id:{_eq:${parseInt(list_id, 10)}}}, order_by:{created_at:desc}){book_id book{title slug cached_image contributions{author{name} contribution}}}}`;
        const hcResponse = await fetch(HC_API, {
          method: 'POST',
          headers: { 'Authorization': env.HC_TOKEN, 'Content-Type': 'application/json' },
          body: JSON.stringify({ query })
        });
        const data = await hcResponse.json();

        const books = (data?.data?.list_books || []).map(lb => {
          const bk = lb.book || {};
          const author = (bk.contributions || [])
            .filter(c => !c.contribution)
            .map(c => c.author && c.author.name)
            .filter(Boolean)
            .join(', ');
          return {
            id: lb.book_id,
            t: bk.title || '',
            a: author,
            hc: bk.slug || '',
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
