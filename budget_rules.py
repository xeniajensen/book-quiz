#!/usr/bin/env python3
"""Faelles budgetregler for up_next.html og næste_læsning_quiz.html.

Begge generatorer henter budgettet herfra, saa de altid foreslaar de samme
BookBeat/Spotify-boeger:
  * timer tilbage = min(loft - brugt, dailyCapacity x dage til fornyelse)
  * er det mindre end en standardbog (avgBookHours), foreslaas hoejst FILL_MAX
    boeger med kendt laengde der (naesten) fylder resten op ("fyld-boeger");
    alt andet peger paa gratis/ejet/Libby
  * ellers skal bogens laengde blot passe i timerne tilbage
"""
import json, os, datetime

BASE = os.path.dirname(os.path.abspath(__file__))
FILL_MAX = 2          # hoejst saa mange fyld-boeger pr. kilde
FILL_MIN_RATING = 3.4 # mindste blended rating for en fyld-bog
TOL = 0.1             # timers tolerance naar en bog skal passe
SRC = {'bb': 'BookBeat', 'sp': 'Spotify'}

def _load(name, default):
    try:
        with open(os.path.join(BASE, name), encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return default

def load_budget(today=None):
    """.budget.json med friske 'dage tilbage' for begge kilder."""
    today = today or datetime.date.today()
    b = _load('.budget.json', {})
    if not isinstance(b, dict):
        return {}
    try:
        pe = (b.get('bb') or {}).get('periodEnd')
        if pe:
            b['bb']['daysLeft'] = max(0, (datetime.date.fromisoformat(pe) - today).days)
    except Exception:
        pass
    try:
        # Spotify kender kun 'dage tilbage' paa hentedagen: traek dagene siden fra
        sp, fe = b.get('sp'), b.get('fetched')
        if sp and fe and sp.get('daysLeft') is not None:
            gone = (today - datetime.date.fromisoformat(fe)).days
            sp['daysLeft'] = max(0, int(sp['daysLeft']) - max(0, gone))
    except Exception:
        pass
    return b

def _dl(d):
    try:
        d = float(d)
        return max(1.0, d) if d >= 0 else 30.0
    except (TypeError, ValueError):
        return 30.0

def cap(b):
    try: c = float(b.get('dailyCapacity') or 0)
    except (TypeError, ValueError): c = 0
    return c if c > 0 else 2.0

def std(b):
    try: s = float(b.get('avgBookHours') or 0)
    except (TypeError, ValueError): s = 0
    return s if s > 0 else 12.5

def reachable(b, key):
    o = b.get(key)
    if not o:
        return None
    rem = max(0.0, (o.get('limit') or 0) - (o.get('used') or 0))
    return round(min(rem, cap(b) * _dl(o.get('daysLeft'))), 1)

def fill_ids(b):
    """{'bb': [id, id], 'sp': [...]} for kilder i fyld-tilstand."""
    rec = _load('.rec_full.json', [])
    audio = _load('.ae.json', {}).get('audio', {})
    cont = _load('.continue.json', {})
    out = {}
    for key, src in SRC.items():
        r = reachable(b, key)
        if r is None or r >= std(b) or r < 1:
            continue
        cands = []
        for x in rec:
            if x.get('source') != src or x.get('avail') not in ('now', 'short'):
                continue
            h = audio.get(str(x['id']))
            if not h or h > r + TOL:
                continue
            if not x.get('rating') or x['rating'] < FILL_MIN_RATING:
                continue
            sn = x.get('snum')
            if sn and sn > 1 and str(x['id']) not in cont:
                continue
            cands.append((h, x['rating'], x['id']))
        cands.sort(key=lambda t: (-t[0], -t[1]))
        out[key] = [c[2] for c in cands[:FILL_MAX]]
    return out

def budget_payload():
    """Budget klar til at blive bagt ind i en side."""
    b = load_budget()
    if not b:
        return {}
    b['std'] = std(b)
    b['tol'] = TOL
    b['fill'] = fill_ids(b)
    return b

if __name__ == '__main__':
    p = budget_payload()
    print(json.dumps({k: p.get(k) for k in ('bb', 'sp', 'std', 'fill')}, ensure_ascii=False))
    print('reachable bb/sp:', reachable(p, 'bb'), reachable(p, 'sp'))
