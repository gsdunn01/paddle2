import hashlib
import json
import pandas as pd
from collections.abc import Mapping
from os import path
from apta_data import *
from apta_utils import *

#helper functions

def _get_factory(f, kwargs):
    factory = kwargs.pop('factory', dict)
    if kwargs:
        raise TypeError("{}() got an unexpected keyword argument "
                        "'{}'".format(f.__name__, kwargs.popitem()[0]))
    return factory

def merge(*dicts, **kwargs):
    """ Merge a collection of dictionaries

    >>> merge({1: 'one'}, {2: 'two'})
    {1: 'one', 2: 'two'}

    Later dictionaries have precedence

    >>> merge({1: 2, 3: 4}, {3: 3, 4: 4})
    {1: 2, 3: 3, 4: 4}

    See Also:
        merge_with
    """
    if len(dicts) == 1 and not isinstance(dicts[0], Mapping):
        dicts = dicts[0]
    factory = _get_factory(merge, kwargs)

    rv = factory()
    for d in dicts:
        rv.update(d)
    return rv

def fetch_and_save_file(filename,fetcher,load=True):
    
    jsondata=fetcher()
    if jsondata:
        with open(filename,"w") as f:
            f.write(json.dumps(jsondata,indent=3))

    return jsondata

def fetch_with_file_cache(filename,fetcher,load=True):
    if not path.exists(filename):
        jsondata=fetcher()
        if jsondata:
            with open(filename,"w") as f:
                f.write(json.dumps(jsondata,indent=3))
    else:
        with open(filename,"r") as f:
            jsondata=json.load(f)
    return jsondata

def json_compare(old,new,name):
    oldhash=hashlib.sha256(json.dumps(old,indent=3).encode()).hexdigest()
    newhash=hashlib.sha256(json.dumps(new,indent=3).encode()).hexdigest()
    
    print(f"{name} {'changed' if oldhash != newhash else 'unchanged'}.")
    
def fetch_and_compare(filename,fetcher,load=True):
    jsondata=fetcher()
    new_filecontents=json.dumps(jsondata,indent=3)
    
    if not path.exists(filename):
        with open(filename,"w") as f:
            f.write(json.dumps(jsondata,indent=3))
    else:
        with open(filename,"r") as f:
            old_filecontents=f.read()
            new_hash=hashlib.sha256(new_filecontents.encode()).hexdigest()
            old_hash=hashlib.sha256(old_filecontents.encode()).hexdigest()
            
            if new_hash != old_hash:
                print(f"{filename} data changed")
            else:
                print(f"{filename} data unchanged")
        
    return jsondata

def double_fetch(filename,fetcher,load=True):
    jsondata=fetcher()
    
    if not path.exists(filename):
        with open(filename,"w") as f:
            f.write(json.dumps(jsondata,indent=3))
    else:
        with open(filename,"r") as f:
            old_filecontents=f.read()
            filedata=json.loads(old_filecontents)
            
        
    return (jsondata,filedata)

def redundant_columns(df):
    return [ colN for (colN,colS) in [ (df.columns[i*2],df.columns[i*2+1]) for i in range(len(df.columns)//2)] if df[colN].isnull().all() or df[df[colN]!=df[colS]].shape[0] == 0]

def numeric_columns(df):
    return [column for column in df.columns if column.isnumeric()]

class APTA_League_Data:
    def __init__(self,league,dock= None):
        self.league=league
        self.season_list=None
        self.raw_match_data=[]
        if dock:
            self.dock=dock
        else:
            self.dock=APTA_Data(debug=False)
            
    def get_seasons(self):
        return self.dock.get_seasons(self.league)
    
    def get_tournaments(self):
        return self.dock.get_tournaments(self.league)
        
    def get_players(self,seasonid):
        matches= self.dock.get_players(self.league,seasonid)
        if not matches:
            return {}
        
        rvalue={}
        for key in matches.keys():
            if key in ['Users']:
                rvalue[key]=matches[key]

        return rvalue

    def get_matches(self,seasonid):
        matches= self.dock.get_matches(self.league,seasonid)
        if not matches:
            return {}
        
        rvalue={}
        for key in matches.keys():
            if key in ['Matches']:
                rvalue[key]=matches[key]

        return rvalue
    
    def get_elolines(self,seasonid):
        matches= self.dock.get_elolines(self.league,seasonid)
        if not matches:
            return {}
        
        rvalue={}
        for key in matches.keys():
            if key in ['ELOLines']:
                rvalue[key]=matches[key]      

        return rvalue

    def get_elodivs(self,seasonid):
        matches= self.dock.get_elodivs(self.league,seasonid)
        if not matches:
            return {}

        rvalue={}
        for key in matches.keys():
            if key in ['ELODivs']:
                rvalue[key]=matches[key]      

        return rvalue

    def get_divisions(self,seasonid):
        return self.dock.get_divisions(self.league,seasonid)
    
    def get_season_list(self):
        if not self.season_list:
            seasons_data=self.dock.get_seasons(self.league)
            if not seasons_data:
                return []
            else:
                self.season_list=["{}".format(season['SeasonID']) for season in seasons_data]
            
            return self.season_list
        else:
            return self.season_list
            
    def load_match_data(self, seasonid_list=[]):
        self.raw_match_data=[]
        for seasonid in seasonid_list:
            self.raw_match_data=self.raw_match_data+(self.dock.get_matches(self.league,seasonid)['Matches'])
        
        return self.raw_match_data
    
    def transform_simple_data(self,data):
        if not data:
            return pd.DataFrame()
        
        df=pd.DataFrame(data)
        
        dropcolumns=numeric_columns(df)
        return df.drop(dropcolumns,axis=1) 
    
    def transform_users_data(self,users_data,leagueid=None,seasonid=None):
        if not users_data:
            return pd.DataFrame()
        
        df=pd.DataFrame(users_data.values())
        info=pd.json_normalize(df['Info'])

        df=pd.concat([df.drop(['Info'],axis=1),info],axis=1)
        df.index=users_data.keys()

        df=df.drop([col for col in df.columns if col.isnumeric()],axis=1)
        
        if seasonid and 'SeasonID' not in df.columns:
            df['SeasonID']=seasonid
        if leagueid and 'LeagueID' not in df.columns:
            df['LeagueID']=leagueid
            
        df['Matches']=df['Matches'].astype(str)
        
        return df
    
    def transform_locations_data(self,division_data,seasonid=None):
        if not division_data:
            return pd.DataFrame()

        df=pd.DataFrame(division_data['Locations'])     
        
        if seasonid:
            df['2']=seasonid
            df['SeasonID']=seasonid

        dropcolumns=numeric_columns(df)
        return df.drop(dropcolumns,axis=1) 

    def transform_tournament_data(self, tours ):
        rvalue={}

        def tournaments_from_tours(tour_data):
            return [ tournament for tournament in tour_data.values() if "TournamentID" in tournament.keys()]

        def levels_from_tours(tour_data):
            return sum([ list(tournament['Levels'].values()) if type(tournament['Levels']) is dict else tournament['Levels'] for tournament in tour_data.values() if "Levels" in tournament.keys()],[])

        def level_restructure(inputDict):
            rvalue=inputDict.copy()
            if type(rvalue['Matches']) is dict:
                rvalue['Matches']=list(rvalue['Matches'].values())
                for match in rvalue['Matches']:
                    if type(match['Lines']) is dict:
                        match['Lines']=list(match['Lines'].values())
            return rvalue

        if 'Tours' in tours.keys()  and len(tours['Tours']) > 0:
            tournament_df=pd.json_normalize(tournaments_from_tours(tours['Tours']))
            if 'Levels' in tournament_df.columns:
                tournament_df.drop('Levels',axis=1,inplace=True)
            if tournament_df.shape[0]:
                for datefield in [ field for field in tournament_df.columns if "Date" in field]:
                    tournament_df[datefield]=pd.to_datetime(tournament_df[datefield],unit="s")
                rvalue['tournaments']=tournament_df
            

            levels_data=[ level_restructure(level) for level in levels_from_tours(tours['Tours'])]
            levels_df=pd.json_normalize(levels_data,max_level=0)
            if levels_df.shape[0]:
                rvalue['tournament_levels']=levels_df
            
            if 'Matches' in levels_df.columns:
                levels_df.drop("Matches",axis=1,inplace=True)
                match_df=pd.json_normalize(levels_data,record_path="Matches",max_level=1)
                match_columns=list(match_df.columns)
                if 'Lines' in match_columns:
                    match_columns.remove("Lines")
                    match_df['Lines']=match_df['Lines'].astype(str)
                if match_df.shape[0]:
                    for datefield in [ field for field in match_df.columns if "Date" in field]:
                        match_df[datefield]=pd.to_datetime(match_df[datefield],unit="s")
                    rvalue['tournament_matches']=match_df
            
        return rvalue
    
    def transform_divisions_data(self,division_data,leagueid=None,seasonid=None):
        df=pd.DataFrame()
        
        if not division_data:
            return df
        
        division_data.pop('Locations')
        structuredata=[]
        for groupid in division_data.keys():
            division_data[groupid].pop('DivGroupName')
            df=pd.json_normalize(division_data[groupid]['Divisions'].values(),record_path="Teams")
            structuredata.append(df)
        if len(structuredata)>0:
            df=pd.concat(structuredata)
        
        #ugly hack
        if '16' in df.columns:
            df=df.drop(['16'],axis=1)
        
        if seasonid and 'SeasonID' not in df.columns:
            df['SeasonID']=seasonid
        if leagueid and 'LeagueID' not in df.columns:
            df['LeagueID']=leagueid
        
        dropcolumns=numeric_columns(df)
        return df.drop(dropcolumns,axis=1) 
    
    def transform_raw_match_data(self,jsondata=None,leagueid=None,seasonid=None):
        if not jsondata:
            jsondata=self.raw_match_data
            
        if not jsondata:
            return pd.DataFrame()
        
        seasondata=jsondata
        
        # Get Columns from JSON Data
        df=pd.json_normalize(seasondata)
        savecolumns=list(df.columns)
        if 'Lines' in savecolumns:
            savecolumns.remove('Lines')


        # Load Match Data by Line
        df=pd.json_normalize(seasondata,record_path="Lines",meta=savecolumns,meta_prefix='match.',errors='ignore')

        # Restore Match Columns not overwritten by Line Details
        nameChanges={ "match." + columnName: columnName for columnName in savecolumns if columnName not in df.columns }
        df.rename(columns=nameChanges, inplace=True)

        #Explode "Sets" column into individual columns
        def rename_columns(df,prefix):
            df.columns=[ f"{prefix}.{col}" for col in list(df.columns)]
            return df

        if "Sets" in list(df.columns):
            setdata=pd.json_normalize(df['Sets'])
            df=pd.concat([df.drop(['Sets'],axis=1)]+[rename_columns(pd.json_normalize(setdata[col].fillna({'':""})),f"Set{1+col}") for col in list(setdata.columns)],axis=1)

        # Convert Date Column to Datetime
        if "Date" in list(df.columns):
          df['Date']=pd.to_datetime(df['Date'],unit="s")
          df.dropna(subset=['Date'])

        # Cleanup Spaces in Names

        for namefield in [field for field in df.columns if "Name" in field]:
            df[namefield]=df[namefield].replace(r'\s+',' ',regex=True)


        # Sort Columns
        df.drop_duplicates(inplace=True)
        df=df[sorted(list(df.columns))] 
        
        if ("ScheduleID" in list(df.columns)) and ("LineNumber" in list(df.columns)):
            df=df.sort_values(by=['ScheduleID','LineNumber']).reset_index(drop=True)
        
        if seasonid and 'SeasonID' not in df.columns:
            df['SeasonID']=seasonid
        if leagueid and 'LeagueID' not in df.columns:
            df['LeagueID']=leagueid

        return df       

    def mirror_api(self,transform=False,output=['csv'],output_func=None,fetch_function=fetch_with_file_cache):
     
        season_data=fetch_function("{}_seasons.json".format(self.league), lambda: self.get_seasons())
        tournament_data=fetch_function("{}_tournaments.json".format(self.league), lambda: self.get_tournaments())
        
        league_tables={}
        league_tables=self.transform_tournament_data(tournament_data)
        league_tables['seasons']=pd.json_normalize(season_data) 
        league_tables['seasons']['leagueid']=self.league

        if 'sqlite' in output:
            def dbInitConnect(dbfilename):
                if not path.exists(dbfilename):
                    new_apta_sqlite(dbfilename)
                return sqlite3.connect(dbfilename)

            leagueDB=dbInitConnect(f"{self.league}.sqlite")
            unifiedDB=dbInitConnect("apta.sqlite")

        

        # serialize leaguelevel data
                
        if transform:
            for (tablename,df) in league_tables.items():
                if 'csv' in output:
                    df.to_csv("{}_{}.csv".format(self.league,tablename),index=False)
                if 'sqlite' in output:
                    save_to_sqlite(df,tablename,self.league,"",leagueDB)
                    save_to_sqlite(df,tablename,self.league,"",unifiedDB)
                if output_func:
                    output_func(df,tablename,self.league,"")


        #loop through seasons
        for seasonid in ["{}".format(season['SeasonID']) for season in reversed(season_data)]:
            division_data=fetch_function("{}_{}_divisions.json".format(self.league,seasonid), lambda :  self.get_divisions(seasonid) )
            match_data=fetch_function("{}_{}_matches.json".format(self.league,seasonid),  lambda: self.get_matches(seasonid) )
            users_data=fetch_function("{}_{}_players.json".format(self.league,seasonid),  lambda: self.get_players(seasonid) )
            elolines=fetch_function("elolines.json", lambda : self.get_elolines(seasonid))
            elodivs=fetch_function("elodivs.json", lambda : self.get_elodivs(seasonid))
            
            

            if transform:
                tables={}
                if match_data:
                    tables['matches']  =self.transform_raw_match_data(match_data['Matches'],self.league,seasonid)
                if users_data:
                    tables['players']  =self.transform_users_data(users_data['Users'],self.league,seasonid)
                if elolines:
                    tables['elolines'] =self.transform_simple_data(elolines['ELOLines'])
                if elodivs:
                    tables['elodivs']  =self.transform_simple_data(elodivs['ELODivs'])
                
                tables['locations']=self.transform_locations_data(division_data,seasonid)
                tables['divisions']=self.transform_divisions_data(division_data,self.league,seasonid)
                
                
                
                for (tablename,df) in tables.items():
                    if 'csv' in output:
                        if tablename in ['elolines','elodivs']:
                            df.to_csv("{}.csv".format(tablename),index=False)
                        else:
                            df.to_csv("{}_{}_{}.csv".format(self.league,seasonid,tablename),index=False)
                    if 'sqlite' in output:
                        save_to_sqlite(df,tablename,self.league,seasonid,leagueDB)
                        save_to_sqlite(df,tablename,self.league,seasonid,unifiedDB)
                    if output_func:
                        output_func(df,tablename,self.league,seasonid)
        
        if 'sqlite' in output:
            leagueDB.close()
            unifiedDB.close()
                
        
    def transform_api(self):
        league=self.league
        season_list=self.get_season_list()
        for season in season_list:
            self.load_match_data([season])
            self.transform_raw_match_data().to_csv("{}_{}_matches.csv".format(league,season),index=False)
