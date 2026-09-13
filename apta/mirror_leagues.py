import hashlib
import os
import sys

from apta_data import *
from apta_transform import *
from apta_utils import *



def generate_private_payload(params={}):
    headers= {'Content-Type': 'application/json'}
    endpoint=params['endpoint']
    rvalue=None

    APTAKEY=os.environ["API_KEY"].encode()
    APIURL=os.environ['API_URL']
    API_PAYLOAD = { 'mod' : os.environ['API_MODULE'] }

    if endpoint=="leagues":
        payload=API_PAYLOAD.copy()
        payload['action']=hashlib.sha256(b"leagues"+APTAKEY).hexdigest()

        rvalue=payload
    if endpoint in ["matches","elolines","elodivs","players"]:
        season=params['season']
        payload=API_PAYLOAD.copy()

        payload['sider']=season
        payload['action']=hashlib.sha256(season.encode()+b"seasondata"+APTAKEY).hexdigest()


        rvalue=payload
    if endpoint in ["tours"]:
        league=params['league']
        payload=API_PAYLOAD.copy()

        payload['lider']=league
        payload['action']=hashlib.sha256(league.encode()+b"tours"+APTAKEY).hexdigest()


        rvalue=payload
    if endpoint in ["seasons"]:
        league=params['league']
        payload=API_PAYLOAD.copy()

        payload['lider']=league
        payload['action']=hashlib.sha256(league.encode()+b"seasons"+APTAKEY).hexdigest()


        rvalue=payload
    if endpoint=="divisions":
        season=params['season']
        payload=API_PAYLOAD.copy()

        payload['sider']=season
        payload['action']=hashlib.sha256(season.encode()+b"divisions"+APTAKEY).hexdigest()

        rvalue=payload
    return (APIURL,payload)


if __name__ == "__main__":
    PlatformTennisAPI=APTA_Data(debug=True,param_transformer=generate_private_payload)
    leagues=fetch_and_save_file("leagues.json",lambda: PlatformTennisAPI.get_leagues() )

    league_list=[ league['PSLeagueID'] for league in leagues]
    if len(sys.argv) > 1:
        league_list=sys.argv[1:]

    for leagueid in league_list:
        league_data=APTA_League_Data(league=leagueid,dock=PlatformTennisAPI)
        league_data.mirror_api(transform=False,output=[],fetch_function=fetch_and_save_file)