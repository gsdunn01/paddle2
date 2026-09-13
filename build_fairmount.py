"""Build the Fairmount Country Club app (iPhone-first) from paddle.sqlite.

    python build_fairmount.py                 # writes fairmount_site/index.html + fairmount_site/data/league.js
    python build_fairmount.py --single out.html   # one self-contained file

Computes an Elo rating for every player from the full line history of the
league (chronological, pair rating = mean of the two partners, K = 24) and ships
the pre-match pair ratings on every line so the page can flag upsets and price
upcoming matches.
"""
from __future__ import annotations

import json
import sys
import time
from collections import defaultdict
from pathlib import Path

import utils.db as db

HERE = Path(__file__).resolve().parent
LEAGUE = 475          # New Jersey Men's Platform Tennis Association
CLUB_LOC = 16091      # Fairmount Country Club in that league
K = 24


def q(sql, params=()):
    return [list(r) for r in db.get_db_conn().execute(sql, params).fetchall()]


def dumps(d) -> str:
    return json.dumps(d, separators=(",", ":")).replace("</", "<\\/")


def elo_pass(lines):
    """lines: [id, sched, no, div, winner, h1, h2, a1, a2, score, gh, ga, res, date] sorted by date.
    Returns per-player rating, per-player count, per-line (pre_home, pre_away), per-player per-season snapshot."""
    rating = defaultdict(lambda: 1500.0)
    played = defaultdict(int)
    pre = {}
    for l in lines:
        h = [p for p in (l[5], l[6]) if p]
        a = [p for p in (l[7], l[8]) if p]
        rh = sum(rating[p] for p in h) / len(h) if h else 1500.0
        ra = sum(rating[p] for p in a) / len(a) if a else 1500.0
        pre[l[0]] = (round(rh), round(ra))
        if l[12] not in ("home", "away") or not h or not a:
            continue
        exp_h = 1 / (1 + 10 ** ((ra - rh) / 400))
        s_h = 1.0 if l[12] == "home" else 0.0
        d = K * (s_h - exp_h)
        for p in h:
            rating[p] += d; played[p] += 1
        for p in a:
            rating[p] -= d; played[p] += 1
    return rating, played, pre


def export() -> dict:
    L = (LEAGUE,)
    seasons = q("select id_season, nm_season from raw.season where id_league=? order by id_season", L)
    season_ids = [s[0] for s in seasons]
    ps = "where id_season in (select id_season from raw.season where id_league=?)"
    lines = q("""select l.id_line, l.id_schedule, l.no_line, l.id_division, l.cd_winner,
                 h1.id_player, h2.id_player, a1.id_player, a2.id_player,
                 coalesce((select group_concat(am_games_home||'-'||am_games_away,' ') from
                    (select * from raw.match_line_set x where x.id_line=l.id_line and not (am_games_home=0 and am_games_away=0) order by no_set)),''),
                 coalesce((select sum(am_games_home) from raw.match_line_set x where x.id_line=l.id_line),0),
                 coalesce((select sum(am_games_away) from raw.match_line_set x where x.id_line=l.id_line),0),
                 w.cd_result, m.dt_match, m.id_season
               from raw.match_line l join raw.match m using(id_schedule)
               left join raw.winner_code w on w.cd_winner=l.cd_winner
               left join raw.match_line_player h1 on h1.id_line=l.id_line and h1.cd_side='h' and h1.no_slot=1
               left join raw.match_line_player h2 on h2.id_line=l.id_line and h2.cd_side='h' and h2.no_slot=2
               left join raw.match_line_player a1 on a1.id_line=l.id_line and a1.cd_side='a' and a1.no_slot=1
               left join raw.match_line_player a2 on a2.id_line=l.id_line and a2.cd_side='a' and a2.no_slot=2
               where m.id_league=? order by m.dt_match, m.id_schedule, l.no_line""", L)
    # merge duplicate accounts: the feed lists every id a person has played under (player_alias);
    # map each group to the id with the most lines so a player's history is complete
    canon = {}
    parent = {}
    def find(x):
        while parent.get(x, x) != x:
            parent[x] = parent.get(parent[x], parent[x]); x = parent[x]
        return x
    for a, b in q("select id_player, id_player_alias from raw.player_alias"):
        ra, rb = find(a), find(b)
        if ra != rb: parent[ra] = rb
    counts = defaultdict(int)
    for l in lines:
        for pid in (l[5], l[6], l[7], l[8]):
            if pid: counts[pid] += 1
    groups = defaultdict(list)
    for pid in set(list(counts) + [x for pair in q("select id_player, id_player_alias from raw.player_alias") for x in pair]):
        groups[find(pid)].append(pid)
    for members in groups.values():
        best = max(members, key=lambda x: (counts.get(x, 0), x))
        for m in members:
            if m != best: canon[m] = best
    if canon:
        for l in lines:
            for i in (5, 6, 7, 8):
                if l[i] in canon: l[i] = canon[l[i]]
    # season snapshots: run elo season by season so we can record end-of-season ratings
    rating, played, pre = elo_pass(lines)
    snap = defaultdict(dict)   # player -> season -> rating at end of that season
    r2 = defaultdict(lambda: 1500.0)
    cur_season = None
    def close_season(sid):
        for p, v in r2.items():
            snap[p][sid] = round(v)
    for l in lines:
        if l[14] != cur_season:
            if cur_season is not None:
                close_season(cur_season)
            cur_season = l[14]
        h = [p for p in (l[5], l[6]) if p]; a = [p for p in (l[7], l[8]) if p]
        if l[12] not in ("home", "away") or not h or not a:
            continue
        rh = sum(r2[p] for p in h) / len(h); ra = sum(r2[p] for p in a) / len(a)
        d = K * ((1.0 if l[12] == "home" else 0.0) - 1 / (1 + 10 ** ((ra - rh) / 400)))
        for p in h: r2[p] += d
        for p in a: r2[p] -= d
    if cur_season is not None:
        close_season(cur_season)

    players = q("select id_player, nm_player from raw.player where id_player in (select id_player from raw.player_season " + ps + ")"
                " or id_player in (select p.id_player from raw.match_line_player p join raw.match_line l using(id_line) join raw.match m using(id_schedule) where m.id_league=? and p.id_player is not null)", (LEAGUE, LEAGUE))
    players = [p for p in players if p[0] not in canon]
    player_seasons = q("select id_player, id_season, id_location from raw.player_season " + ps, L)
    seen = set(); merged = []
    for r in player_seasons:
        r[0] = canon.get(r[0], r[0])
        if (r[0], r[1]) not in seen:
            seen.add((r[0], r[1])); merged.append(r)
    player_seasons = merged
    print(f"merged {len(canon)} duplicate player ids")
    # ---------------------------------------------------------------- official PTI (scraped from njflex.tenniscores.com)
    pti_official, pti_hist, line_pti = {}, {}, {}
    pti_file = HERE / "pti_scrape.json"
    if pti_file.exists():
        import re as _re
        scraped = json.loads(pti_file.read_text())
        def norm(n):
            n = _re.sub(r"\(.*?\)", " ", n or "").lower()
            n = _re.sub(r"\b(jr\.?|sr\.?|iii|ii)\b", " ", n)
            return " ".join(n.replace(".", " ").split())
        by_name = defaultdict(list)
        for pl in players:
            by_name[norm(pl[1])].append(pl[0])
        # which teams has each feed player played for (to disambiguate duplicate names)
        played_teams = defaultdict(set)
        match_team = {m[0]: (m[3], m[4]) for m in q("select id_schedule, id_league, id_season, id_team_home, id_team_away from raw.match where id_league=?", L)}
        for l in lines:
            th, ta = match_team.get(l[1], (None, None))
            for pid in (l[5], l[6]):
                if pid and th: played_teams[pid].add(th)
            for pid in (l[7], l[8]):
                if pid and ta: played_teams[pid].add(ta)
        # lines indexed by (player, date, line number) for pre-match PTI
        by_key = {}
        for l in lines:
            d = (l[13] or "").replace("-", "")
            for pid in (l[5], l[6], l[7], l[8]):
                if pid: by_key[(pid, d, l[2])] = l[0]
        matched = 0
        for sp in scraped:
            key = norm(sp[0] + " " + sp[1])
            cands = by_name.get(key) or []
            if len(cands) > 1 and sp[5]:
                cands = sorted(cands, key=lambda c: -len(played_teams[c] & set(sp[5]))) 
            if not cands:
                continue
            pid = cands[0]; matched += 1
            pti_official[pid] = sp[4] if sp[4] is not None else sp[2]
            hist = []
            for h in sp[8]:   # [yyyymmdd, line, start, end, W/L]
                hist.append([h[0], h[2], h[3]])
                lid = by_key.get((pid, h[0], h[1]))
                if lid: line_pti.setdefault(lid, {})[pid] = h[2]
            hist.sort()
            pti_hist[pid] = hist
        print(f"official PTI matched for {matched} of {len(scraped)} scraped players; {len(line_pti)} lines with pre-match PTI")
    # estimated PTI for everyone else: linear map from the internal rating, fitted on the official pairs
    xs = [(rating[p], pti_official[p]) for p in pti_official if played.get(p, 0) >= 8 and p in rating]
    a_fit, b_fit = 0.0, 0.0
    if len(xs) >= 30:
        n = len(xs); mx = sum(x for x, _ in xs) / n; my = sum(y for _, y in xs) / n
        sxx = sum((x - mx) ** 2 for x, _ in xs); sxy = sum((x - mx) * (y - my) for x, y in xs)
        b_fit = sxy / sxx if sxx else 0.0; a_fit = my - b_fit * mx
        resid = [y - (a_fit + b_fit * x) for x, y in xs]
        print(f"PTI ~ {a_fit:.1f} + {b_fit:.4f} * rating  (n={n}, resid sd={ (sum(r*r for r in resid)/n) ** .5:.1f})")
    def est_pti(pid):
        if pid in pti_official: return pti_official[pid], "official"
        if played.get(pid, 0) >= 5 and b_fit: return round(a_fit + b_fit * rating[pid], 1), "est"
        return None, None
    # odds calibration: P(home wins line) as a function of (away pair PTI - home pair PTI), lines where all four are known
    obs = []
    for l in lines:
        if l[12] not in ("home", "away"): continue
        lp = line_pti.get(l[0]) or {}
        h = [lp.get(p) for p in (l[5], l[6]) if p]; a = [lp.get(p) for p in (l[7], l[8]) if p]
        if len(h) == 2 and len(a) == 2 and None not in h and None not in a:
            obs.append(((a[0] + a[1]) / 2 - (h[0] + h[1]) / 2, 1.0 if l[12] == "home" else 0.0))
    import math
    best_k, best_ll = 0.1, -1e18
    for k in [i / 200 for i in range(1, 120)]:
        ll = sum(math.log(max(1e-9, (1 / (1 + math.exp(-k * d))) if y else (1 - 1 / (1 + math.exp(-k * d))))) for d, y in obs)
        if ll > best_ll: best_ll, best_k = ll, k
    print(f"odds calibration: {len(obs)} lines with full PTI, k={best_k:.3f} per PTI point")
    # only keep snapshots for seasons a player actually played in (rating changed) — cheaper: keep where they have lines
    played_in = defaultdict(set)
    for l in lines:
        for p in (l[5], l[6], l[7], l[8]):
            if p: played_in[p].add(l[14])
    snaps = [[p, s, snap[p][s]] for p in played_in for s in sorted(played_in[p]) if s in snap[p]]

    def pair_pti(l):
        lp = line_pti.get(l[0]) or {}
        h = [lp[p] for p in (l[5], l[6]) if p and p in lp]; a = [lp[p] for p in (l[7], l[8]) if p and p in lp]
        return [round(sum(h) / len(h), 1) if len(h) == 2 else None, round(sum(a) / len(a), 1) if len(a) == 2 else None]
    out = {
        "club": CLUB_LOC, "league": LEAGUE, "built": time.strftime("%Y-%m-%d"),
        "seasons": seasons,
        "locations": q("select id_location, nm_club, nm_city, nm_state, ad_club from raw.location where id_league=?", L),
        "divisions": q("select d.id_division, d.nm_division, g.nm_division_group from raw.division d join raw.division_group g using(id_division_group) where d.id_league=?", L),
        "teams": q("select id_team, nm_team, id_location from raw.team where id_league=?", L),
        "team_seasons": q("select id_team, id_season, id_division, nm_team from raw.team_season " + ps, L),
        "players": [[p[0], p[1], est_pti(p[0])[0], played.get(p[0], 0), est_pti(p[0])[1]] for p in players],
        "pti_hist": pti_hist,
        "odds_k": best_k,
        "rules": json.loads((HERE / "rules_njmpta.json").read_text(encoding="utf-8")),
        "player_seasons": player_seasons,
        "matches": q("select id_schedule, id_season, dt_match, id_team_home, id_team_away, is_league, is_bye from raw.match where id_league=?", L),
        "winner": q("select cd_winner, ds_winner, cd_result from raw.winner_code"),
        "lines": [[l[0], l[1], l[2], l[3], l[4], l[5], l[6], l[7], l[8], l[9], l[10], l[11]] + pair_pti(l) for l in lines],
    }
    return out


def build(out_dir: Path, single: Path | None = None) -> None:
    data = export()
    template = (HERE / "fairmount_template.html").read_text(encoding="utf-8")
    import base64
    logo = HERE / "fcc_logo.png"
    if logo.exists():
        template = template.replace("__LOGO__", "data:image/png;base64," + base64.b64encode(logo.read_bytes()).decode())
    if single:
        single.write_text(template.replace("__DATA__", dumps(data)).replace("__LAZY__", "false"), encoding="utf-8")
        print(f"wrote {single} ({single.stat().st_size / 1e6:.1f} MB)")
        return
    out_dir.mkdir(parents=True, exist_ok=True); (out_dir / "data").mkdir(exist_ok=True)
    (out_dir / "index.html").write_text(template.replace("__DATA__", "null").replace("__LAZY__", '"data/league.js?v=' + time.strftime("%Y%m%d%H%M%S") + '"'), encoding="utf-8")
    f = out_dir / "data" / "league.js"
    f.write_text("window.__paddle(" + dumps(data) + ");", encoding="utf-8")
    print(f"wrote {out_dir / 'index.html'} and {f} ({f.stat().st_size / 1e6:.1f} MB); players {len(data['players'])}, lines {len(data['lines'])}")


if __name__ == "__main__":
    args = sys.argv[1:]
    if args and args[0] == "--single":
        build(HERE, Path(args[1]) if len(args) > 1 else HERE / "fairmount.html")
    else:
        build(Path(args[0]) if args else HERE / "fairmount_site")
    db.close()
