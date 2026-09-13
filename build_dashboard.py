"""Build the dashboard page from paddle.sqlite.

    python build_dashboard.py                 # single file: dashboard.html (data embedded; open locally)
    python build_dashboard.py --split site/   # index.html + data/*.json, one file per league (for hosting)

Re-run after `python main.py ...` to refresh.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import utils.db as db

HERE = Path(__file__).resolve().parent

LINES_SQL = """select l.id_line, l.id_schedule, l.no_line, l.id_division, l.cd_winner,
    v.id_h1, v.id_h2, v.id_a1, v.id_a2, coalesce(v.score,''), coalesce(v.games_home,0), coalesce(v.games_away,0),
    case when v.id_h1 is null then v.nm_h1 end, case when v.id_h2 is null then v.nm_h2 end,
    case when v.id_a1 is null then v.nm_a1 end, case when v.id_a2 is null then v.nm_a2 end
    from raw.match_line l join raw.v_line v using(id_line) join raw.match m using(id_schedule) {where}"""


def q(sql, params=()):
    return [list(r) for r in db.get_db_conn().execute(sql, params).fetchall()]


def index_data() -> dict:
    return {
        "leagues": q("select id_league, nm_league from raw.league where id_league in (select distinct id_league from raw.match) order by nm_league"),
        "seasons": q("select id_season, id_league, nm_season from raw.season where id_season in (select distinct id_season from raw.match) order by id_season"),
        "winner": q("select cd_winner, ds_winner, cd_result from raw.winner_code"),
    }


def league_data(id_league: int | None) -> dict:
    """Everything needed for one league (or all leagues when id_league is None)."""
    w = "where id_league = ?" if id_league else ""
    wm = "where m.id_league = ?" if id_league else ""
    p = (id_league,) if id_league else ()
    ps = "where id_season in (select id_season from raw.season " + w + ")"
    return {
        "locations": q("select id_location, nm_club, nm_city, nm_state, ct_hard_courts from raw.location " + w, p),
        "groups": q("select id_division_group, nm_division_group from raw.division_group " + w, p),
        "divisions": q("select id_division, id_division_group, nm_division from raw.division " + w, p),
        "teams": q("select id_team, nm_team, id_location, id_league from raw.team " + w, p),
        "team_seasons": q("select id_team, id_season, id_division, nm_team from raw.team_season " + ps, p),
        "players": q("select id_player, nm_player from raw.player where id_player in (select id_player from raw.player_season " + ps + ")", p),
        "player_seasons": q("select id_player, id_season, id_location, am_rating_start from raw.player_season " + ps, p),
        "matches": q("select id_schedule, id_season, dt_match, id_team_home, id_team_away, is_league, is_bye from raw.match " + w, p),
        "lines": q(LINES_SQL.format(where=wm), p),
    }


def dumps(d) -> str:
    return json.dumps(d, separators=(",", ":")).replace("</", "<\\/")


def build_single(out: Path) -> None:
    data = index_data(); data.update(league_data(None))
    template = (HERE / "dashboard_template.html").read_text(encoding="utf-8")
    out.write_text(template.replace("__DATA__", dumps(data)), encoding="utf-8")
    print(f"wrote {out} ({out.stat().st_size / 1e6:.1f} MB)")


def build_split(out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True); (out_dir / "data").mkdir(exist_ok=True)
    idx = index_data(); idx["lazy"] = True
    template = (HERE / "dashboard_template.html").read_text(encoding="utf-8")
    (out_dir / "index.html").write_text(template.replace("__DATA__", dumps(idx)), encoding="utf-8")
    for id_league, _ in idx["leagues"]:
        f = out_dir / "data" / f"league_{id_league}.json"
        f.write_text(dumps(league_data(id_league)), encoding="utf-8")
        print(f"wrote {f} ({f.stat().st_size / 1e6:.1f} MB)")


if __name__ == "__main__":
    args = sys.argv[1:]
    if args and args[0] == "--split":
        build_split(Path(args[1]) if len(args) > 1 else HERE / "dashboard_site")
    else:
        build_single(Path(args[0]) if args else HERE / "dashboard.html")
    db.close()
