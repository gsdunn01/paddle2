"""Pull league / season / division / player / match data from data.platform.tennis
and load it into the SQLite model defined in utils/db.py."""
from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

TZ = ZoneInfo("America/New_York")   # match dates in the feed are unix timestamps of the local start time
from typing import Any, Iterable, Optional

from utils.json_funcs import call_api
import utils.db as db

PLAYER_SLOTS = [("Player1H", "h", 1), ("Player2H", "h", 2), ("Player1A", "a", 1), ("Player2A", "a", 2)]


def _int(v: Any, default: Optional[int] = None) -> Optional[int]:
    try:
        return int(v) if v not in (None, "", " ") else default
    except (TypeError, ValueError):
        return default


def _id(v: Any) -> Optional[int]:
    """Feed uses 0 / -1 / -2 / None for 'no id'; store NULL."""
    i = _int(v)
    return i if i is not None and i > 0 else None


def _float(v: Any) -> Optional[float]:
    try:
        return float(v) if v not in (None, "", " ") else None
    except (TypeError, ValueError):
        return None


def _str(v: Any) -> Optional[str]:
    s = (v or "").strip() if isinstance(v, str) else v
    return s or None


def _log(msg: str) -> None:
    print(f"{datetime.now():%H:%M:%S}  {msg}", flush=True)


class PSRaw:
    """Fetches the raw feeds and writes them to the raw.* tables."""

    def __init__(self) -> None:
        self.season_league: dict[int, int] = {}   # id_season -> id_league (the seasons in scope)

    # ------------------------------------------------------------ scope
    def load_seasons_from_db(self, id_league: Optional[int] = None) -> None:
        sql, params = "select id_season, id_league from raw.season", []
        if id_league:
            sql += " where id_league = ?"; params.append(id_league)
        df = db.get_df(sql, params)
        self.season_league = {int(r.id_season): int(r.id_league) for r in df.itertuples()}

    def restrict_seasons(self, id_seasons: Iterable[int]) -> None:
        keep = {int(s) for s in id_seasons}
        self.season_league = {s: l for s, l in self.season_league.items() if s in keep}

    def latest_seasons(self, per_league: int = 1) -> None:
        """Keep only the N most recent seasons (highest ids) of every league in scope."""
        by_league: dict[int, list[int]] = {}
        for s, l in self.season_league.items():
            by_league.setdefault(l, []).append(s)
        keep: set[int] = set()
        for seasons in by_league.values():
            keep.update(sorted(seasons)[-per_league:])
        self.restrict_seasons(keep)

    # ------------------------------------------------------------ leagues + seasons
    def load_leagues(self, id_league_filter: int = 0) -> None:
        leagues, seasons = [], []
        for l_raw in call_api({"cmd": "leagues"}) or []:
            id_league = _int(l_raw.get("PSLeagueID"))
            if id_league_filter and id_league != id_league_filter:
                continue
            leagues.append((id_league, _str(l_raw.get("PSName")), _str(l_raw.get("PSLLName"))))
            for s_raw in call_api({"cmd": "seasons", "id_league": str(id_league)}) or []:
                id_season = _int(s_raw.get("SeasonID"))
                self.season_league[id_season] = id_league
                seasons.append((id_season, id_league, _str(s_raw.get("SeasonName"))))
        db.exec_many("insert or replace into raw.league (id_league, nm_league, nm_league_short) values (?,?,?)", leagues)
        db.exec_many("insert or replace into raw.season (id_season, id_league, nm_season) values (?,?,?)", seasons)
        _log(f"leagues: {len(leagues)}, seasons: {len(seasons)}")

    # ------------------------------------------------------------ divisions / teams / locations
    def load_divisions(self) -> None:
        locations, groups, divisions, teams, team_seasons = [], [], [], [], []
        for id_season, id_league in self.season_league.items():
            raw = call_api({"cmd": "divisions", "id_league": str(id_league), "id_season": str(id_season)})
            if not isinstance(raw, dict):
                continue
            for k, v in raw.items():
                if k == "Locations":
                    for r in v or []:
                        locations.append((
                            _id(r.get("LocationID")), id_league, _str(r.get("ClubName")), _str(r.get("LocAbbr")),
                            _str(r.get("ClubURL")), _str(r.get("ClubAddress")), _str(r.get("ClubCity")),
                            _str(r.get("ClubState")), _str(r.get("ClubZip")), _int(r.get("HardCourts")),
                            _int(r.get("ClayCourts")), _int(r.get("IndoorCourts")), _id(r.get("RepID")),
                            _str(r.get("RepDescription"))))
                    continue
                id_group = _id(k)
                if not id_group or not isinstance(v, dict):
                    continue
                groups.append((id_group, id_league, _str(v.get("DivGroupName"))))
                for k2, dv in (v.get("Divisions") or {}).items():
                    id_division = _id(k2)
                    divisions.append((id_division, id_group, id_league, _str(dv.get("Name"))))
                    for t in dv.get("Teams") or []:
                        id_team = _id(t.get("TeamID"))
                        teams.append((id_team, id_league, _id(t.get("LocationID")), _str(t.get("TeamName"))))
                        team_seasons.append((id_team, id_season, id_division, _str(t.get("TeamName")),
                                             _id(t.get("CaptainID")), _id(t.get("CoCaptainID")), _str(t.get("Points"))))
        locations = [r for r in locations if r[0]]
        db.exec_many("insert or replace into raw.location (id_location, id_league, nm_club, cd_club, id_club_url, ad_club,"
                     " nm_city, nm_state, id_zip, ct_hard_courts, ct_clay_courts, ct_indoor_courts, id_rep, nm_rep_role)"
                     " values (?,?,?,?,?,?,?,?,?,?,?,?,?,?)", locations)
        db.exec_many("insert or replace into raw.division_group (id_division_group, id_league, nm_division_group)"
                     " values (?,?,?)", groups)
        db.exec_many("insert or replace into raw.division (id_division, id_division_group, id_league, nm_division)"
                     " values (?,?,?,?)", divisions)
        db.exec_many("insert or replace into raw.team (id_team, id_league, id_location, nm_team) values (?,?,?,?)", teams)
        db.exec_many("insert or replace into raw.team_season (id_team, id_season, id_division, nm_team, id_captain,"
                     " id_co_captain, am_points) values (?,?,?,?,?,?,?)", team_seasons)
        _log(f"locations: {len(locations)}, divisions: {len(divisions)}, team-seasons: {len(team_seasons)}")

    # ------------------------------------------------------------ players
    def load_players(self) -> None:
        players, player_seasons, aliases = [], [], []
        for id_season, id_league in self.season_league.items():
            raw = call_api({"cmd": "players", "id_league": str(id_league), "id_season": str(id_season)})
            users = (raw or {}).get("Users")
            if not isinstance(users, dict):        # empty season comes back as []
                continue
            for u in users.values():
                id_player = _id(u.get("PlayerID"))
                if not id_player:
                    continue
                players.append((id_player, _str(u.get("PlayerName")), _str(u.get("Gender"))))
                player_seasons.append((id_player, id_season, _id(u.get("LocationID")),
                                       _float((u.get("Info") or {}).get("ELOStartRate"))))
                for a in u.get("Matches") or []:      # every id this person has appeared under
                    a = _id(a)
                    if a and a != id_player:
                        aliases.append((id_player, a))
        db.exec_many("insert or replace into raw.player (id_player, nm_player, cd_gender) values (?,?,?)", players)
        db.exec_many("insert or replace into raw.player_season (id_player, id_season, id_location, am_rating_start)"
                     " values (?,?,?,?)", player_seasons)
        db.exec_many("insert or ignore into raw.player_alias (id_player, id_player_alias) values (?,?)", aliases)
        _log(f"player-seasons: {len(player_seasons)}, aliases: {len(aliases)}")

    # ------------------------------------------------------------ matches
    def load_matches(self) -> None:
        matches, lines, line_players, sets = [], [], [], []
        for id_season, id_league in self.season_league.items():
            raw = call_api({"cmd": "matches", "id_league": str(id_league), "id_season": str(id_season)})
            for m in (raw or {}).get("Matches") or []:
                id_schedule = _int(m.get("ScheduleID"))
                if id_schedule is None:
                    continue
                ts = _int(m.get("Date"))
                dt = datetime.fromtimestamp(ts, TZ).strftime("%Y-%m-%d") if ts else None
                is_league = 0 if id_schedule < 0 or m.get("Main") is False else 1
                matches.append((id_schedule, id_season, id_league, ts, dt, _id(m.get("Team1ID")), _id(m.get("Team2ID")),
                                1 if _int(m.get("Bye"), 0) else 0, is_league))
                for r in m.get("Lines") or []:
                    id_line = _int(r.get("LineID"))
                    if id_line is None:
                        continue
                    lines.append((id_line, id_schedule, _int(r.get("LineNumber")), _id(r.get("DivisionID")),
                                  _int(r.get("Winner"), 0)))
                    for prefix, side, slot in PLAYER_SLOTS:
                        pid, name = _id(r.get(prefix + "ID")), _str(r.get(prefix + "Name"))
                        if pid or (name and name != "N/A"):
                            line_players.append((id_line, side, slot, pid, name))
                    for s in r.get("Sets") or []:
                        id_set = _int(s.get("SetID"))
                        if id_set is None:
                            continue
                        sets.append((id_set, id_line, _int(s.get("SetNumber")), _int(s.get("Team1Score"), 0),
                                     _int(s.get("Team2Score"), 0), _int(s.get("T1TieBreak"), 0), _int(s.get("T2TieBreak"), 0)))
        db.exec_many("insert or replace into raw.match (id_schedule, id_season, id_league, ts_match, dt_match,"
                     " id_team_home, id_team_away, is_bye, is_league) values (?,?,?,?,?,?,?,?,?)", matches)
        db.exec_many("insert or replace into raw.match_line (id_line, id_schedule, no_line, id_division, cd_winner)"
                     " values (?,?,?,?,?)", lines)
        db.exec_many("insert or replace into raw.match_line_player (id_line, cd_side, no_slot, id_player, nm_player)"
                     " values (?,?,?,?,?)", line_players)
        db.exec_many("insert or replace into raw.match_line_set (id_set, id_line, no_set, am_games_home, am_games_away,"
                     " am_tb_home, am_tb_away) values (?,?,?,?,?,?,?)", sets)
        _log(f"matches: {len(matches)}, lines: {len(lines)}, sets: {len(sets)}")

    # ------------------------------------------------------------ division ratings (global files)
    def load_ratings(self) -> None:
        """elodivs.json / elolines.json cover every league; keep the rows for the leagues in scope."""
        leagues = set(self.season_league.values())
        divs = [(_int(r["LeagueID"]), _int(r["SeasonID"]), _int(r["DivisionID"]), _float(r.get("Rating")),
                 _float(r.get("MeanPlayed")), _float(r.get("MedianPlayed")))
                for r in (call_api({"cmd": "elodivs"}) or {}).get("ELODivs") or []
                if not leagues or _int(r["LeagueID"]) in leagues]
        lines = [(_int(r["LeagueID"]), _int(r["SeasonID"]), _int(r["DivisionID"]), _int(r["LineNumber"]),
                  _float(r.get("Rating")))
                 for r in (call_api({"cmd": "elolines"}) or {}).get("ELOLines") or []
                 if not leagues or _int(r["LeagueID"]) in leagues]
        db.exec_many("insert or replace into raw.division_rating (id_league, id_season, id_division, am_rating,"
                     " am_mean_played, am_median_played) values (?,?,?,?,?,?)", divs)
        db.exec_many("insert or replace into raw.division_line_rating (id_league, id_season, id_division, no_line,"
                     " am_rating) values (?,?,?,?,?)", lines)
        _log(f"division ratings: {len(divs)}, line ratings: {len(lines)}")


def delete_league(id_league: int) -> dict:
    """Remove a league and everything that hangs off it. Players kept only if they still appear elsewhere."""
    c = db.get_db_conn()
    counts = {}
    def run(label, sql):
        counts[label] = c.execute(sql, (id_league,)).rowcount
    run("sets", "delete from raw.match_line_set where id_line in (select l.id_line from raw.match_line l join raw.match m using(id_schedule) where m.id_league = ?)")
    run("line players", "delete from raw.match_line_player where id_line in (select l.id_line from raw.match_line l join raw.match m using(id_schedule) where m.id_league = ?)")
    run("lines", "delete from raw.match_line where id_schedule in (select id_schedule from raw.match where id_league = ?)")
    run("matches", "delete from raw.match where id_league = ?")
    run("player seasons", "delete from raw.player_season where id_season in (select id_season from raw.season where id_league = ?)")
    run("team seasons", "delete from raw.team_season where id_season in (select id_season from raw.season where id_league = ?)")
    run("teams", "delete from raw.team where id_league = ?")
    run("divisions", "delete from raw.division where id_league = ?")
    run("division groups", "delete from raw.division_group where id_league = ?")
    run("locations", "delete from raw.location where id_league = ?")
    run("division ratings", "delete from raw.division_rating where id_league = ?")
    run("line ratings", "delete from raw.division_line_rating where id_league = ?")
    run("seasons", "delete from raw.season where id_league = ?")
    run("league", "delete from raw.league where id_league = ?")
    counts["orphan players"] = c.execute("delete from raw.player where id_player not in (select id_player from raw.player_season)"
                                         " and id_player not in (select id_player from raw.match_line_player where id_player is not null)").rowcount
    counts["orphan aliases"] = c.execute("delete from raw.player_alias where id_player not in (select id_player from raw.player)").rowcount
    c.commit()
    _log(f"deleted league {id_league}: " + ", ".join(f"{v} {k}" for k, v in counts.items() if v))
    return counts
