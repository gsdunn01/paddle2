"""A dummy docstring."""
#from distutils.log import debug
from __future__ import division
from typing import Any
import json
import requests

def call_api(params: dict[str,str] = dict()) -> Any:
    """."""
    base_url = "http://data.platform.tennis/"
    cmd: str = params["cmd"]
    id_league: int = -1
    id_season: int = -1
    
    if "id_league" in params.keys():
        id_league=int(params["id_league"] or -1)    
    
    if "id_season" in params.keys():
        id_season=int(params["id_season"] or -1)    
    
    url: str = base_url
    
    if cmd in ["leagues", "elolines", "elodivs"]:
        url +=  f"{cmd}.json"
    if cmd == "seasons":
        url += f"{id_league}_{cmd}.json"
    if cmd in ["matches","divisions","players"]:
        url +=  f"{id_league}_{id_season}_{cmd}.json"
    if cmd == "tours":
        url += f"{id_league}_tournaments.json"
        
    response = requests.get(url, timeout=30)
    if ((response.status_code == 200) and len(response.content) > 0):
        return json.loads(response.content.decode('utf-8'))

    print(f"[!] HTTP {response.url} calling [{response.url}]")
    return None
    