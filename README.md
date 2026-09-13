# paddle datahub

Pulls platform-tennis league data from `data.platform.tennis` into a local SQLite
file, `datahub/paddle.sqlite`. No SQL Server needed.

## Setup (Windows)

```
cd datahub
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

## Run

```
python main.py leagues                        # league + season list (seconds)
python main.py all --league 202 --latest 2    # one league, two most recent seasons
python main.py all --league 202 --season 6359 # one league, one season
python main.py matches --league 202 --latest 1
python main.py ratings --league 202           # division / line ratings
python main.py all                            # every league and season (slow)
```

`all` = leagues, seasons, locations, divisions, teams, players, matches, ratings.
Re-running is safe: rows are upserted by id. Note that the newest season of a
league usually exists in the feed before any matches are played, so `--latest 1`
can come back empty; use `--latest 2`.

## Data model

```
league ─┬─< season ──< match ──< match_line ─┬─< match_line_player >── player ──< player_alias
        ├─< location                         └─< match_line_set              └──< player_season >── season
        ├─< division_group ──< division ──< team_season >── team >── location
        └─< team
division ──< division_rating (per season), division_line_rating (per season, per line)
```

Key facts learned from the raw feeds (see the data-model page for detail):

* **Team, division, division-group and location ids persist across seasons** –
  they are league-level entities. A team's placement in a division, its captain
  and its name for a given year live in `team_season`.
* **Player ids are global** (same id in every league and season). `player_season`
  is the yearly registration: club and the season-start rating
  (`am_rating_start`, the feed's `ELOStartRate`, PTI-style: lower is stronger).
  `player_alias` holds other ids the site has merged into that player.
* **A match is a fixture** (home team vs away team on a date) with usually four
  `match_line`s. Lines with a **negative `id_schedule`** are stand-alone rated
  matches (tournament / non-league play): no teams, one line; `is_league = 0`.
* `cd_winner` is a code, decoded in `winner_code`: 1/2 home/away won; 3–6 forfeit
  or default; 7/8 retired; 0 unreported. Only 1 and 2 are clean results.
* Set rows are padded to 3 (sometimes 5) per line; unplayed sets are 0-0.
  `am_tb_*` are tiebreak points (a 10-point match tiebreak shows as 1-0 with the
  tiebreak points).
* The per-player ELO fields in the match feed are always null; ratings come
  from the global `elodivs.json` / `elolines.json` files (`division_rating`,
  `division_line_rating`).

Views: `v_line` (one row per line with teams, players, score, result) and
`v_player_line` (one row per player per line, with `won` 1/0/NULL) are the
easiest starting points:

```python
import utils.db as db
db.get_df("select nm_player, sum(won) w, count(*) n from raw.v_player_line where id_season = 6359 group by 1 order by w desc")
```

`utils/sql_odbc.py` and `base_classes.py` are from the old SQL Server version and are no longer used.

## Dashboard

`python build_dashboard.py` writes `dashboard.html` — a self-contained page
(data embedded) with standings, a fixture/score search, and club and player
records. Open it in any browser; re-run it after refreshing the database.
`python build_dashboard.py --split dashboard_site` writes `index.html` plus one
`data/league_<id>.json` per league, loaded on demand — use that for hosting.
The page is generated from `dashboard_template.html`.

## Loaded so far

Full history of NJ Men's Platform Tennis Association (475) and NJ Partners
Paddle League (497). Rebuild from the feed in a couple of minutes:

```
python main.py all --league 475
python main.py all --league 497
python build_dashboard.py
```

`python main.py delete --league <id>` removes a league and everything under it.

## Fairmount app (iPhone)

`python build_fairmount.py` builds the club-centric mobile app into
`fairmount_site/` (`index.html` + `data/league.js`) from the NJ Men's league
data: club record, official PTI ratings (from `pti_scrape.json`, scraped from
the league's Ratings page on njflex.tenniscores.com), PTI-based odds for
upcoming or projected matches, auto-written recaps, the rules page
(`rules_njmpta.json`), an assistant, and complete player histories.
Players the league has not published a PTI for get an estimate ("est.")
fitted from results against rated players. `--single fairmount.html` writes a
one-file version. Change `LEAGUE` / `CLUB_LOC` at the top of the script to
point it at another club. To host it yourself, upload the `fairmount_site`
folder (index.html + data/) to any static host (Netlify Drop, GitHub Pages,
Cloudflare Pages).
