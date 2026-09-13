"""SQLite storage layer for the paddle datahub.

Tables live in one SQLite file, attached under the schema name ``raw`` so
queries read ``raw.match``, ``raw.player`` ...  The file defaults to
``paddle.sqlite`` next to this package; override with the PADDLE_DB env var.

Entity model (see README / data-model notes):

    league 1-* season
    league 1-* location            (clubs; league-level, not per season)
    league 1-* division_group 1-* division
    league 1-* team                (team ids persist across seasons)
    team   1-* team_season *-1 season, *-1 division
    player 1-* player_season *-1 season      (player ids are global)
    player 1-* player_alias
    season 1-* match 1-* match_line 1-* match_line_player / match_line_set
    division 1-* division_rating (per season), division_line_rating
"""
from __future__ import annotations

import os
import sqlite3
from pathlib import Path
from typing import Any, Iterable, Sequence

import pandas as pd

DEFAULT_DB = Path(__file__).resolve().parent.parent / "paddle.sqlite"

_conn: sqlite3.Connection | None = None


def db_path() -> Path:
    return Path(os.environ.get("PADDLE_DB", DEFAULT_DB))


def get_db_conn() -> sqlite3.Connection:
    """One shared connection; the data file is attached as schema ``raw``."""
    global _conn
    if _conn is None:
        _conn = sqlite3.connect(":memory:")
        _conn.execute("ATTACH DATABASE ? AS raw", (str(db_path()),))
        init_schema(_conn)
    return _conn


def close() -> None:
    global _conn
    if _conn is not None:
        _conn.commit()
        _conn.close()
        _conn = None


SCHEMA = """
-- ----------------------------------------------------------------- reference
CREATE TABLE IF NOT EXISTS raw.league (
    id_league       INTEGER PRIMARY KEY,
    nm_league       TEXT,
    nm_league_short TEXT
);
CREATE TABLE IF NOT EXISTS raw.season (
    id_season   INTEGER PRIMARY KEY,
    id_league   INTEGER NOT NULL REFERENCES league(id_league),
    nm_season   TEXT
);
-- clubs. The feed sends them per season but always with SeasonID = 0: they belong to the league.
CREATE TABLE IF NOT EXISTS raw.location (
    id_location     INTEGER PRIMARY KEY,
    id_league       INTEGER REFERENCES league(id_league),
    nm_club         TEXT,
    cd_club         TEXT,
    id_club_url     TEXT,
    ad_club         TEXT,
    nm_city         TEXT,
    nm_state        TEXT,
    id_zip          TEXT,
    ct_hard_courts  INTEGER,
    ct_clay_courts  INTEGER,
    ct_indoor_courts INTEGER,
    id_rep          INTEGER,
    nm_rep_role     TEXT
);
-- division ids and group ids persist from season to season: league-level, like teams.
CREATE TABLE IF NOT EXISTS raw.division_group (
    id_division_group   INTEGER PRIMARY KEY,
    id_league           INTEGER REFERENCES league(id_league),
    nm_division_group   TEXT
);
CREATE TABLE IF NOT EXISTS raw.division (
    id_division         INTEGER PRIMARY KEY,
    id_division_group   INTEGER REFERENCES division_group(id_division_group),
    id_league           INTEGER REFERENCES league(id_league),
    nm_division         TEXT
);
CREATE TABLE IF NOT EXISTS raw.team (
    id_team     INTEGER PRIMARY KEY,
    id_league   INTEGER REFERENCES league(id_league),
    id_location INTEGER REFERENCES location(id_location),
    nm_team     TEXT                                   -- most recent name seen
);
-- one row per team per season it played in: the division it was placed in, captains, name that year
CREATE TABLE IF NOT EXISTS raw.team_season (
    id_team         INTEGER REFERENCES team(id_team),
    id_season       INTEGER REFERENCES season(id_season),
    id_division     INTEGER REFERENCES division(id_division),
    nm_team         TEXT,
    id_captain      INTEGER,
    id_co_captain   INTEGER,
    am_points       TEXT,
    PRIMARY KEY (id_team, id_season)
);
-- players are global (same id in every league and season)
CREATE TABLE IF NOT EXISTS raw.player (
    id_player   INTEGER PRIMARY KEY,
    nm_player   TEXT,
    cd_gender   TEXT
);
-- registration of a player in a season: club, and the season-start rating
CREATE TABLE IF NOT EXISTS raw.player_season (
    id_player       INTEGER REFERENCES player(id_player),
    id_season       INTEGER REFERENCES season(id_season),
    id_location     INTEGER REFERENCES location(id_location),
    am_rating_start REAL,                                -- feed: Info.ELOStartRate (PTI-style, lower = stronger)
    PRIMARY KEY (id_player, id_season)
);
-- other ids the same person has appeared under (duplicate accounts merged by the site)
CREATE TABLE IF NOT EXISTS raw.player_alias (
    id_player       INTEGER REFERENCES player(id_player),
    id_player_alias INTEGER,
    PRIMARY KEY (id_player, id_player_alias)
);
-- ----------------------------------------------------------------- results
-- a fixture: two teams on a date (league play), or a stand-alone rated match (tournament/non-league:
-- negative id_schedule, no teams, exactly one line)
CREATE TABLE IF NOT EXISTS raw.match (
    id_schedule     INTEGER PRIMARY KEY,
    id_season       INTEGER REFERENCES season(id_season),
    id_league       INTEGER REFERENCES league(id_league),
    ts_match        INTEGER,                             -- unix seconds from the feed
    dt_match        TEXT,                                -- YYYY-MM-DD (local, from ts_match)
    id_team_home    INTEGER REFERENCES team(id_team),    -- NULL when feed sends 0 / none
    id_team_away    INTEGER REFERENCES team(id_team),
    is_bye          INTEGER NOT NULL DEFAULT 0,
    is_league       INTEGER NOT NULL DEFAULT 1           -- 0 = tournament / non-league rated match
);
-- one court (line) of a fixture: two home players vs two away players
CREATE TABLE IF NOT EXISTS raw.match_line (
    id_line         INTEGER PRIMARY KEY,
    id_schedule     INTEGER REFERENCES match(id_schedule),
    no_line         INTEGER,
    id_division     INTEGER REFERENCES division(id_division),   -- NULL for non-league matches
    cd_winner       INTEGER REFERENCES winner_code(cd_winner)
);
CREATE TABLE IF NOT EXISTS raw.match_line_player (
    id_line     INTEGER REFERENCES match_line(id_line),
    cd_side     TEXT NOT NULL CHECK (cd_side IN ('h','a')),
    no_slot     INTEGER NOT NULL CHECK (no_slot IN (1,2)),
    id_player   INTEGER REFERENCES player(id_player),          -- NULL when the feed sends 0 / N/A
    nm_player   TEXT,                                          -- name as printed on the line
    PRIMARY KEY (id_line, cd_side, no_slot)
);
CREATE TABLE IF NOT EXISTS raw.match_line_set (
    id_set          INTEGER PRIMARY KEY,
    id_line         INTEGER REFERENCES match_line(id_line),
    no_set          INTEGER,
    am_games_home   INTEGER,
    am_games_away   INTEGER,
    am_tb_home      INTEGER,                              -- tiebreak points (0 when no tiebreak)
    am_tb_away      INTEGER
);
CREATE TABLE IF NOT EXISTS raw.winner_code (
    cd_winner   INTEGER PRIMARY KEY,
    ds_winner   TEXT,
    cd_result   TEXT      -- 'home' / 'away' / 'none'
);
INSERT OR REPLACE INTO raw.winner_code VALUES
    (0,  'not played / not reported',                        'none'),
    (1,  'home won',                                         'home'),
    (2,  'away won',                                         'away'),
    (3,  'home won - away forfeit (inferred: away players blank)',   'home'),
    (4,  'away won - home forfeit (inferred: home players blank)',   'away'),
    (5,  'home won - away default, scored 6-0 6-0 (inferred)',       'home'),
    (6,  'away won - home default, scored 0-6 0-6 (inferred)',       'away'),
    (7,  'home won - retired / incomplete (inferred: partial score)', 'home'),
    (8,  'away won - retired / incomplete (inferred: partial score)', 'away'),
    (9,  'unknown (rare)',                                   'none'),
    (10, 'double forfeit - both sides blank (inferred)',     'none'),
    (11, 'unknown (rare, no scores)',                        'none');
-- ----------------------------------------------------------------- ratings (elodivs.json / elolines.json)
CREATE TABLE IF NOT EXISTS raw.division_rating (
    id_league       INTEGER,
    id_season       INTEGER,
    id_division     INTEGER,
    am_rating       REAL,
    am_mean_played  REAL,
    am_median_played REAL,
    PRIMARY KEY (id_league, id_season, id_division)
);
CREATE TABLE IF NOT EXISTS raw.division_line_rating (
    id_league   INTEGER,
    id_season   INTEGER,
    id_division INTEGER,
    no_line     INTEGER,
    am_rating   REAL,
    PRIMARY KEY (id_league, id_season, id_division, no_line)
);
-- ----------------------------------------------------------------- indexes
CREATE INDEX IF NOT EXISTS raw.ix_season_league       ON season (id_league);
CREATE INDEX IF NOT EXISTS raw.ix_team_season_season  ON team_season (id_season, id_division);
CREATE INDEX IF NOT EXISTS raw.ix_player_season_season ON player_season (id_season);
CREATE INDEX IF NOT EXISTS raw.ix_match_season        ON match (id_season, dt_match);
CREATE INDEX IF NOT EXISTS raw.ix_match_teams         ON match (id_team_home, id_team_away);
CREATE INDEX IF NOT EXISTS raw.ix_line_schedule       ON match_line (id_schedule);
CREATE INDEX IF NOT EXISTS raw.ix_line_player_player  ON match_line_player (id_player);
CREATE INDEX IF NOT EXISTS raw.ix_set_line            ON match_line_set (id_line);
-- ----------------------------------------------------------------- convenience views
-- one row per line with teams, players, set scores and the result from the home side's view
CREATE VIEW IF NOT EXISTS raw.v_line AS
SELECT  m.id_schedule, m.id_season, s.nm_season, m.id_league, m.dt_match, m.is_league,
        l.id_line, l.no_line, l.id_division, d.nm_division,
        m.id_team_home, th.nm_team AS nm_team_home, m.id_team_away, ta.nm_team AS nm_team_away,
        h1.id_player AS id_h1, h1.nm_player AS nm_h1, h2.id_player AS id_h2, h2.nm_player AS nm_h2,
        a1.id_player AS id_a1, a1.nm_player AS nm_a1, a2.id_player AS id_a2, a2.nm_player AS nm_a2,
        l.cd_winner, w.cd_result, w.ds_winner,
        (SELECT group_concat(am_games_home || '-' || am_games_away, ' ')
           FROM (SELECT * FROM match_line_set x WHERE x.id_line = l.id_line
                   AND NOT (am_games_home = 0 AND am_games_away = 0) ORDER BY no_set)) AS score,
        (SELECT sum(am_games_home) FROM match_line_set x WHERE x.id_line = l.id_line) AS games_home,
        (SELECT sum(am_games_away) FROM match_line_set x WHERE x.id_line = l.id_line) AS games_away
FROM match_line l
JOIN match m            ON m.id_schedule = l.id_schedule
LEFT JOIN season s      ON s.id_season = m.id_season
LEFT JOIN division d    ON d.id_division = l.id_division
LEFT JOIN team_season th ON th.id_team = m.id_team_home AND th.id_season = m.id_season
LEFT JOIN team_season ta ON ta.id_team = m.id_team_away AND ta.id_season = m.id_season
LEFT JOIN match_line_player h1 ON h1.id_line = l.id_line AND h1.cd_side = 'h' AND h1.no_slot = 1
LEFT JOIN match_line_player h2 ON h2.id_line = l.id_line AND h2.cd_side = 'h' AND h2.no_slot = 2
LEFT JOIN match_line_player a1 ON a1.id_line = l.id_line AND a1.cd_side = 'a' AND a1.no_slot = 1
LEFT JOIN match_line_player a2 ON a2.id_line = l.id_line AND a2.cd_side = 'a' AND a2.no_slot = 2
LEFT JOIN winner_code w ON w.cd_winner = l.cd_winner;

-- one row per player per line: the long form for player stats (won = 1/0/NULL)
CREATE VIEW IF NOT EXISTS raw.v_player_line AS
SELECT  p.id_player, p.nm_player, p.cd_side, p.no_slot,
        v.id_line, v.no_line, v.id_schedule, v.id_season, v.nm_season, v.id_league, v.dt_match, v.is_league,
        v.id_division, v.nm_division,
        CASE p.cd_side WHEN 'h' THEN v.id_team_home ELSE v.id_team_away END AS id_team,
        CASE p.cd_side WHEN 'h' THEN v.nm_team_home ELSE v.nm_team_away END AS nm_team,
        CASE p.cd_side WHEN 'h' THEN v.id_team_away ELSE v.id_team_home END AS id_opponent_team,
        CASE p.cd_side WHEN 'h' THEN v.nm_team_away ELSE v.nm_team_home END AS nm_opponent_team,
        CASE p.cd_side WHEN 'h' THEN v.games_home ELSE v.games_away END AS games_for,
        CASE p.cd_side WHEN 'h' THEN v.games_away ELSE v.games_home END AS games_against,
        CASE v.cd_result WHEN 'none' THEN NULL
             WHEN 'home' THEN (p.cd_side = 'h') WHEN 'away' THEN (p.cd_side = 'a') END AS won,
        v.cd_winner, v.score
FROM match_line_player p
JOIN v_line v ON v.id_line = p.id_line
WHERE p.id_player IS NOT NULL;
"""


def init_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(SCHEMA)
    conn.commit()


def exec_sql(sql: str, params: Sequence[Any] = ()) -> None:
    conn = get_db_conn()
    conn.execute(sql, params)
    conn.commit()


def exec_many(sql: str, rows: Iterable[Sequence[Any]]) -> int:
    """Run one parameterised statement for every row, in a single transaction."""
    conn = get_db_conn()
    cur = conn.executemany(sql, rows)
    conn.commit()
    return cur.rowcount


def get_df(sql: str, params: Sequence[Any] = ()) -> pd.DataFrame:
    return pd.read_sql_query(sql, get_db_conn(), params=params)
