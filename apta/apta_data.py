import json
import requests
import requests_cache
import logging

requests_cache.install_cache("cache",backend="sqlite",expire_after=120,match_headers=True)
# print("Installed Cache",requests_cache.is_installed())

# import logging

# logging.basicConfig(level='WARNING')
# logging.getLogger('requests_cache').setLevel('DEBUG')

def generate_json_url(params={}):
    base_url="http://data.platform.tennis/"

    endpoint=params['endpoint']

    if endpoint in ["leagues","elolines","elodivs"]:
        rvalue=base_url+"{}.json".format(endpoint)
    if endpoint=="seasons":
        league=params['league']
        rvalue = base_url+"{}_{}.json".format(league,endpoint)
    if endpoint=="tours":
        league=params['league']
        rvalue = base_url+"{}_tournaments.json".format(league)
    if endpoint in ["matches","divisions","players"]:
        league=params['league']
        season=params['season']
        rvalue = base_url+"{}_{}_{}.json".format(league,season,endpoint)
        
    return (rvalue,None)

class APTA_Data:
    def __init__(self, debug=False, param_transformer=generate_json_url):
        self.param_transform=param_transformer
        self.debug=debug
        
        
    def api_fetch(self,params= None):
        (url,payload)=self.param_transform(params)
        # if self.debug:
        #     print(url)

        if payload:
            # if self.debug:
            #     print(payload)
            response=requests.get(url,params=payload)
        else:
            response=requests.get(url)
        
        
        if self.debug:
            print(response.url, response.from_cache)

        # requests_cache.remove_expired_responses()

        return response
    
    def response_to_json(self,response):
        if ((response.status_code == 200) and len(response.content) > 0):
            return json.loads(response.content.decode('utf-8'))
        
        print('[!] HTTP {0} calling [{1}]'.format(response.status_code, response.url))
        return None
    
    def get_leagues_raw(self):
        return self.api_fetch({'endpoint':'leagues'})
    
    def get_leagues(self):
        return self.response_to_json(self.get_leagues_raw())

    def get_tournaments_raw(self,leagueid):
        return self.api_fetch({'endpoint':'tours','league':leagueid})
    
    def get_tournaments(self,leagueid):
        return self.response_to_json(self.get_tournaments_raw(leagueid))
        
    def get_seasons_raw(self,leagueid):
        return self.api_fetch({'endpoint':'seasons','league':leagueid})
    
    def get_seasons(self,leagueid):
        return self.response_to_json(self.get_seasons_raw(leagueid))
    
    def get_matches_raw(self,leagueid,seasonid):
        return self.api_fetch({'endpoint':'matches','league':leagueid,'season':seasonid})

    def get_matches(self,leagueid,seasonid):
        return self.response_to_json(self.get_matches_raw(leagueid,seasonid))

    def get_divisions_raw(self,leagueid,seasonid):
        return self.api_fetch({'endpoint':'divisions','league':leagueid,'season':seasonid})
    
    def get_divisions(self,leagueid,seasonid):
        return self.response_to_json(self.get_divisions_raw(leagueid,seasonid))

    def get_elolines_raw(self,leagueid,seasonid):
        return self.api_fetch({'endpoint':'elolines','league':leagueid,'season':seasonid})

    def get_elolines(self,leagueid,seasonid):
        return self.response_to_json(self.get_elolines_raw(leagueid,seasonid))

    def get_elodivs_raw(self,leagueid,seasonid):
        return self.api_fetch({'endpoint':'elodivs','league':leagueid,'season':seasonid})

    def get_elodivs(self,leagueid,seasonid):
        return self.response_to_json(self.get_elodivs_raw(leagueid,seasonid))

    def get_players_raw(self,leagueid,seasonid):
        return self.api_fetch({'endpoint':'players','league':leagueid,'season':seasonid})

    def get_players(self,leagueid,seasonid):
        return self.response_to_json(self.get_players_raw(leagueid,seasonid))

