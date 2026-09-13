"""A dummy docstring."""
from dataclasses import dataclass
from typing import Any

@dataclass
class Location(object):
    """A dummy docstring."""
    id_loc: int
    id_league: int
    id_season: int
    id_rep: int
    nm_rep: str
    id_loc_code: str
    nm_club: str
    id_club_url: str
    ct_hard_cts: int
    nm_city: str
    nm_state: str
    id_zip: str

@dataclass
class Division(object):
    """A dummy docstring."""
    id_div: int
    nm_div: str
    id_div_group: int
    nm_div_group: int
    id_season: int
    id_league: int

@dataclass
class Team(object):
    """A dummy docstring."""
    id_team: int
    nm_team: str    
    id_captain: int
    id_captain_co: int    
    id_location: int
    id_league: int
    id_season: int    
    id_div: int
    nm_div: str
    id_div_group: int
    nm_div_group: str    
    id_points: str

@dataclass
class Player(object):
    """A dummy docstring."""
    id_player: int
    nm_player: str
    id_location: int
    id_gender: str
    id_league: int
    id_season: int
    id_player_list: list

@dataclass
class MatchLineSet(object):
    """A dummy docstring."""
    id_set: int
    id_set_number: int
    am_score_t1: int
    am_score_t2: int
    am_tie_break_t1: float
    am_tie_break_t2: float

@dataclass
class MatchLine(object):
    """This is a paddle match."""
    raw_dict: dict[Any, Any]
    match_line_sets: dict[int, MatchLineSet]
    def __init__(self, rawdict) -> None:
        self.raw_dict=rawdict
        self.match_line_sets = dict()
        pass


@dataclass
class MatchTest(object):
    """This is a collection of paddle matches. Like 4 lines playing in a league week."""
    id_schedule: int    
    nm_team1: str
    id_date: int = -1
    def __init__(self, schedule: int):
        self.id_schedule=schedule
    

@dataclass
class Match(object):
    """This is a collection of paddle matches. Like 4 lines playing in a league week."""
    id_schedule: int
    id_date: int
    nm_team1: str
    id_team1: int
    nm_team2: str
    id_team2: int
    id_bye: str
    id_league: int
    id_season: int
    match_lines: dict[int, MatchLine]

@dataclass
class Season(object):
    """A dummy docstring."""
    id_season: int
    nm_season: str
    id_league: int
    matches: dict[int, Match]

@dataclass
class League(object):
    """A dummy docstring."""
    id_league: int
    nm_league: str
    nm_league2: str
    id_league_code: str
    seasons: dict[int, Season]
