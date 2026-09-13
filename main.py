"""Refresh the paddle database from data.platform.tennis.

Examples (run from the datahub folder):

    python main.py leagues                        # league + season list only (seconds)
    python main.py all --league 202 --latest 2    # one league, its two most recent seasons
    python main.py all --league 202 --season 6359 # one league, one season
    python main.py matches --league 202 --latest 1
    python main.py ratings --league 202           # division / line ratings (elodivs, elolines)
    python main.py delete --league 202            # remove a league and all its data
    python main.py all                            # every league and season (slow)

Re-running is safe: rows are upserted by id.
The database is datahub/paddle.sqlite (override with the PADDLE_DB env var).
"""
from __future__ import annotations

import argparse

import main_classes as raw
import utils.db as db


def _scoped(args: argparse.Namespace, refresh_leagues: bool) -> raw.PSRaw:
    ps = raw.PSRaw()
    if refresh_leagues:
        ps.load_leagues(args.league or 0)
    else:
        ps.load_seasons_from_db(args.league)
    if args.season:
        ps.restrict_seasons(args.season)
    elif args.latest:
        ps.latest_seasons(args.latest)
    print(f"seasons in scope: {len(ps.season_league)}")
    return ps


def cmd_leagues(args):
    _scoped(args, True)


def cmd_all(args):
    ps = _scoped(args, True)
    ps.load_divisions()
    ps.load_players()
    ps.load_matches()
    ps.load_ratings()


def cmd_divisions(args):
    _scoped(args, False).load_divisions()


def cmd_players(args):
    _scoped(args, False).load_players()


def cmd_matches(args):
    ps = _scoped(args, False)
    ps.load_players()
    ps.load_matches()


def cmd_ratings(args):
    _scoped(args, False).load_ratings()


def cmd_delete(args):
    if not args.league:
        raise SystemExit("delete needs --league <id>")
    raw.delete_league(args.league)
    db.get_db_conn().execute("VACUUM raw")


COMMANDS = {"leagues": cmd_leagues, "all": cmd_all, "divisions": cmd_divisions,
            "players": cmd_players, "matches": cmd_matches, "ratings": cmd_ratings, "delete": cmd_delete}


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("command", choices=COMMANDS, help="what to refresh")
    p.add_argument("--league", type=int, help="only this league id (e.g. 202)")
    p.add_argument("--season", type=int, action="append", help="only this season id (repeatable)")
    p.add_argument("--latest", type=int, metavar="N", help="only the N most recent seasons per league")
    args = p.parse_args()
    if args.command not in ("leagues", "ratings", "delete") and not (args.league or args.season or args.latest):
        print("No filter given: this pulls every season of every league and can take a long time. Ctrl-C to stop.")
    try:
        COMMANDS[args.command](args)
    finally:
        db.close()
    print(f"done -> {db.db_path()}")


if __name__ == "__main__":
    main()
