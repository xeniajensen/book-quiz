#!/usr/bin/env python3
"""
Rebuilds .continue.json for the Up Next "📖 Continue a series" card.

Unlike the live 🔖 hero (which only covers series you're ACTIVELY reading — one of
your last 3 finishes), this card covers EVERY series you've ever read a book in that
has a next installment waiting on your TBR, however long ago you read it.

Logic:
  • Fetch all READ books (status 3) that belong to a series → per series, your read
    positions and where you left off (highest read position + its title/rating).
  • Fetch all WANT-TO-READ books (status 1) that belong to a series → your TBR, with
    each book's series + position (these are the English editions you actually added,
    so no translation/language mix-up).
  • For each series present in both: next = the lowest TBR position strictly above where
    you left off that you haven't already read. Map next_book_id → {et, er, pos}.

Writes .continue.json in the existing format:
  { "<next_tbr_book_id>": {"et": "<book you left off at>", "er": <your rating>, "pos": <next #>} }

Requires HC token in .hc_token (same folder) or HC_TOKEN env var. Run where Hardcover
is reachable (your Mac / the pipeline). On any error it leaves .continue.json untouched.
"""
import os, sys, time, json

try:
    import requests
except ImportError:
    import subprocess
    subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'requests', '--break-system-packages', '-q'])
    import requests

DIR        = os.path.dirname(os.path.abspath(__file__))
TOKEN_FILE = os.path.join(DIR, '.hc_token')
REC_FULL   = os.path.join(DIR, '.rec_full.json')
OUT        = os.path.join(DIR, '.continue.json')
HC_API     = "https://api.hardcover.app/v1/graphql"
USER_ID    = 125471
SLEEP      = 0.65

_TOKEN = None
def get_token():
    global _TOKEN
    if _TOKEN: return _TOKEN
    tok = os.environ.get("HC_TOKEN")
    if not tok and os.path.exists(TOKEN_FILE):
        tok = open(TOKEN_FILE).read().strip()
    if not tok:
        raise RuntimeError("HC token ikke fundet (.hc_token eller HC_TOKEN).")
    _TOKEN = tok
    return _TOKEN

def gql(query):
    r = requests.post(HC_API,
        headers={"Authorization": get_token(), "Content-Type": "application/json"},
        json={"query": query}, timeout=30)
    r.raise_for_status()
    time.sleep(SLEEP)
    data = r.json()
    if "errors" in data:
        raise RuntimeError(f"GraphQL fejl: {data['errors']}")
    return data.get("data") or {}

def fetch_status(status_id):
    """All user_books at a status that belong to a series -> list of
    {id, title, rating, series_id, position}."""
    out, offset = [], 0
    while True:
        data = gql(f"""{{
            user_books(where:{{user_id:{{_eq:{USER_ID}}}, status_id:{{_eq:{status_id}}}}},
                       limit:100, offset:{offset}){{
                rating
                book{{ id title book_series{{ position series{{ id }} }} }}
            }}
        }}""")
        batch = data.get("user_books", [])
        for ub in batch:
            b = ub.get("book") or {}
            for bs in (b.get("book_series") or []):
                ser = bs.get("series") or {}
                if ser.get("id") is None or bs.get("position") is None:
                    continue
                out.append({"id": b["id"], "title": b.get("title") or "",
                            "rating": ub.get("rating"),
                            "series_id": ser["id"], "position": bs["position"]})
        if len(batch) < 100:
            break
        offset += 100
    return out

def norm_pos(p):
    return int(p) if isinstance(p, (int, float)) and float(p).is_integer() else p

def main():
    tbr_ids = set()
    if os.path.exists(REC_FULL):
        tbr_ids = {b["id"] for b in json.load(open(REC_FULL))}

    print("⏳ Henter læste bøger (status 3) …")
    read = fetch_status(3)
    print(f"   {len(read)} serie-medlemskaber i læste bøger")
    print("⏳ Henter want-to-read (status 1) …")
    wtr = fetch_status(1)
    print(f"   {len(wtr)} serie-medlemskaber i TBR")

    read_book_ids = {r["id"] for r in read}

    # per series: read positions + where you left off (highest read position)
    read_by_series = {}
    for r in read:
        s = read_by_series.setdefault(r["series_id"], {"positions": set(), "anchor": None})
        s["positions"].add(r["position"])
        a = s["anchor"]
        if a is None or r["position"] > a["position"]:
            s["anchor"] = r
        # keep a rated anchor for the message if the top one is unrated
        if r.get("rating") is not None:
            ra = s.get("rated_anchor")
            if ra is None or r["position"] > ra["position"]:
                s["rated_anchor"] = r

    # per series: TBR books
    tbr_by_series = {}
    for w in wtr:
        tbr_by_series.setdefault(w["series_id"], []).append(w)

    cont = {}
    for sid, info in read_by_series.items():
        cands = tbr_by_series.get(sid)
        if not cands:
            continue
        left_at = info["anchor"]["position"]
        nexts = [w for w in cands
                 if w["position"] > left_at
                 and w["position"] not in info["positions"]
                 and w["id"] not in read_book_ids
                 and (not tbr_ids or w["id"] in tbr_ids)]
        if not nexts:
            continue
        nxt = min(nexts, key=lambda w: w["position"])
        anchor = info.get("rated_anchor") or info["anchor"]
        cont[str(nxt["id"])] = {"et": anchor["title"], "er": anchor.get("rating"),
                                "pos": norm_pos(nxt["position"])}

    json.dump(cont, open(OUT, "w"), ensure_ascii=False)
    print(f"✅ .continue.json: {len(cont)} serier at fortsætte "
          f"(på tværs af {len(read_by_series)} læste serier)")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"⚠️  build_continue fejlede ({e}) — beholder eksisterende .continue.json", file=sys.stderr)
        sys.exit(1)
