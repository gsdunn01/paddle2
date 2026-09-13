from os import path
import pandas as pd
import sqlite3
from contextlib import closing
import pandas as pd
import numpy as np

def sqlite_table_exists(conn,table_name):
    c = conn.cursor()                
    #get the count of tables with the name
    c.execute(f" SELECT count(*) FROM {table_name}")

    #if the count is 1, then table exists
    if c.fetchone()[0]>0 : 
        rvalue= True
    else :
        rvalue= False

    conn.commit()  

    return rvalue
    




def save_tosqlite(df, name, league="", season="",db=None):
    if df.empty:
        return
    
    
    dbfilename="{}.sqlite".format(league) if not db else db

    if not path.exists(dbfilename):
        new_apta_sqlite(dbfilename)

    with closing(sqlite3.connect(dbfilename)) as sql_conn:
        save_to_sqlite(df,name,league,season,sql_conn)

def save_to_sqlite(df, name, league, season, sql_conn):
    print([name,league,season])
        
    if name in ['matches','players','divisions','locations','seasons',"tournaments","tournament_levels","tournament_matches"]:
        try:
            df.to_sql(name,sql_conn,if_exists='append', method='multi',chunksize=100,index=False)
        except Exception as error:
            print(error)
            data = pd.read_sql('SELECT * FROM {}'.format(name), sql_conn)
            df2 = pd.concat([df,data])
            if 'Date' in df2.columns:
                df2['Date']=pd.to_datetime(df2['Date'])
            df2.to_sql(name,sql_conn,if_exists='replace', index=False)
    else:
        if not sqlite_table_exists(sql_conn,name):
            df.to_sql(name,sql_conn,if_exists='replace',index=False)

#create unified APTA sqlite database
def save_to_league_and_unified_db(a,b,c="",d=None):
    save_tosqlite(a,b,c,d)
    save_tosqlite(a,b,c,d,db="apta.sqlite")


def diff_pd(df1, df2):
    """Identify differences between two pandas DataFrames"""
    assert (df1.columns == df2.columns).all(), \
        "DataFrame column names are different"
    if any(df1.dtypes != df2.dtypes):
        "Data Types are different, trying to convert"
        df2 = df2.astype(df1.dtypes)
    if df1.equals(df2):
        return None
    else:
        # need to account for np.nan != np.nan returning True
        diff_mask = (df1 != df2) & ~(df1.isnull() & df2.isnull())
        ne_stacked = diff_mask.stack()
        changed = ne_stacked[ne_stacked]
        changed.index.names = ['id', 'col']
        difference_locations = np.where(diff_mask)
        changed_from = df1.values[difference_locations]
        changed_to = df2.values[difference_locations]
        return pd.DataFrame({'from': changed_from, 'to': changed_to}, index=changed.index)


def save_df_tosqlite(dbfilename,table_name,df):
    if not path.exists(dbfilename):
        new_apta_sqlite(dbfilename)

    with closing(sqlite3.connect(dbfilename)) as sql_conn:
        df.to_sql(table_name,sql_conn,if_exists='replace', index=False)
 

def new_apta_sqlite(dbfilename):
    
    with closing(sqlite3.connect(dbfilename)) as sql_conn:
        statements=[]
        c=sql_conn.cursor()
        statements.append("""
        CREATE TABLE "matches" (
                "Bye" BOOLEAN,
                "Date" TIMESTAMP,
                "DivisionID" NUMERIC,
                "LineID" NUMERIC,
                "LineNumber" NUMERIC,
                "Main" BOOLEAN,
                "Player1AELOConfidence" NUMERIC,
                "Player1AELOEnd" NUMERIC,
                "Player1AELOScale" NUMERIC,
                "Player1AELOStart" NUMERIC,
                "Player1AID" NUMERIC,
                "Player1AName" TEXT,
                "Player1HELOConfidence" NUMERIC,
                "Player1HELOEnd" NUMERIC,
                "Player1HELOScale" NUMERIC,
                "Player1HELOStart" NUMERIC,
                "Player1HID" NUMERIC,
                "Player1HName" TEXT,
                "Player2AELOConfidence" NUMERIC,
                "Player2AELOEnd" NUMERIC,
                "Player2AELOScale" NUMERIC,
                "Player2AELOStart" NUMERIC,
                "Player2AID" NUMERIC,
                "Player2AName" TEXT,
                "Player2HELOConfidence" NUMERIC,
                "Player2HELOEnd" NUMERIC,
                "Player2HELOScale" NUMERIC,
                "Player2HELOStart" NUMERIC,
                "Player2HID" NUMERIC,
                "Player2HName" TEXT,
                "ScheduleID" INTEGER,
                "Set1.SetID" NUMERIC,
                "Set1.SetNumber" NUMERIC,
                "Set1.T1TieBreak" NUMERIC,
                "Set1.T2TieBreak" NUMERIC,
                "Set1.Team1Score" NUMERIC,
                "Set1.Team2Score" NUMERIC,
                "Set2.SetID" NUMERIC,
                "Set2.SetNumber" NUMERIC,
                "Set2.T1TieBreak" NUMERIC,
                "Set2.T2TieBreak" NUMERIC,
                "Set2.Team1Score" NUMERIC,
                "Set2.Team2Score" NUMERIC,
                "Set3.SetID" NUMERIC,
                "Set3.SetNumber" NUMERIC,
                "Set3.T1TieBreak" NUMERIC,
                "Set3.T2TieBreak" NUMERIC,
                "Set3.Team1Score" NUMERIC,
                "Set3.Team2Score" NUMERIC,
                "Set4.SetID" NUMERIC,
                "Set4.SetNumber" NUMERIC,
                "Set4.T1TieBreak" NUMERIC,
                "Set4.T2TieBreak" NUMERIC,
                "Set4.Team1Score" NUMERIC,
                "Set4.Team2Score" NUMERIC,
                "Set5.SetID" NUMERIC,
                "Set5.SetNumber" NUMERIC,
                "Set5.T1TieBreak" NUMERIC,
                "Set5.T2TieBreak" NUMERIC,
                "Set5.Team1Score" NUMERIC,
                "Set5.Team2Score" NUMERIC,
                "Team1" TEXT,
                "Team1ID" NUMERIC,
                "Team2" TEXT,
                "Team2ID" NUMERIC,
                "Winner" NUMERIC,
                "match.DivisionID" NUMERIC,
                "SeasonID" NUMERIC,
                "LeagueID" NUMERIC
                )
        """)

        statements.append("""
        CREATE TABLE "players" (
            "Matches" TEXT,
            "LocationID" NUMERIC,
            "PlayerName" TEXT,
            "Gender" TEXT,
            "PlayerID" INTEGER,
            "ELOStartRate" NUMERIC,
            "SeasonID" NUMERIC,
            "LeagueID" NUMERIC
            )
        """)

        statements.append("""
 
            CREATE TABLE "seasons" (
            "SeasonID" NUMERIC,
            "SeasonName" TEXT,
            "LeagueID" NUMERIC
            )
        """)
        statements.append("""
            CREATE TABLE "divisions" (
                "TeamID" NUMERIC,
                "SeasonID" NUMERIC,
                "CaptainID" NUMERIC,
                "CoCaptainID" NUMERIC,
                "DivisionID" NUMERIC,
                "LocationID" NUMERIC,
                "LeagueID" NUMERIC,
                "TeamName" TEXT,
                "DivName" TEXT,
                "DivGroupName" TEXT,
                "DivGroupID" NUMERIC,
                "Points" NUMERIC,
                "StandingsPlacement" NUMERIC,
                "SubLeagueID" TEXT,
                "AcceptedRosterID" NUMERIC,
                "Hidden" TEXT,
                "StagingStatus" TEXT,
                "LastStageTime" TIMESTAMP,
                "LastStageCapt" NUMERIC,
                "PenaltyPoints" NUMERIC,
                "ScheduleBias" NUMERIC,
                "UniqueID" TEXT,
                "ScheduleNotes" TEXT,
                "RostersReceived" TEXT,
                "Subdivision" TEXT,
                "TeamAbbr" TEXT,
                "ShowTSRatingDiv" NUMERIC
            )
        """)
        statements.append("""
            CREATE TABLE "leagues" (
                "PSLeagueID" NUMERIC,
                "PSName" TEXT,
                "PSLLName" TEXT,
                "PSLLName2" TEXT
                )

        """)
        statements.append("""
            CREATE TABLE "locations" (
                "LocationID" NUMERIC,
                "LeagueID" NUMERIC,
                "SeasonID" NUMERIC,
                "RepID" NUMERIC,
                "RepDescription" TEXT,
                "LocAbbr" TEXT,
                "ClubName" TEXT,
                "ClubURL" TEXT,
                "HardCourts" TEXT,
                "ClayCourts" TEXT,
                "IndoorCourts" TEXT,
                "Phone" TEXT,
                "Fax" TEXT,
                "Address" TEXT,
                "Directions" TEXT,
                "Notes" TEXT,
                "ClubAddress" TEXT,
                
                "ClubCity" TEXT,
                
                "ClubState" TEXT,
                
                "ClubZip" TEXT,
                
                "PriceDesc" TEXT,
                
                "Price" TEXT,
                "UseMapquest" TEXT,
                "TotalCourts" TEXT,
                
                "OtherLocationID" NUMERIC,
                "TournamentID" NUMERIC,
                "TournamentUserID" NUMERIC
                )

        """)
        statements.append("""
            CREATE TABLE "elodivs" (
                "LeagueID" NUMERIC,
                "SeasonID" NUMERIC,
                "DivisionID" NUMERIC,
                "Rating" NUMERIC,
                
                "MeanPlayed" NUMERIC,
                
                "MedianPlayed" NUMERIC
                )

        """)
        statements.append("""
            CREATE TABLE "elolines" (
                "LeagueID" NUMERIC,
                "SeasonID" NUMERIC,
                "DivisionID" NUMERIC,
                "LineNumber" NUMERIC,
                "Rating" NUMERIC
                )

        """)
        statements.append("""
            CREATE VIEW "ByPlayers" AS select date,ScheduleID,LineID,LineNumber,SeasonID,LeagueID,
                    "Player1AELOConfidence" as PlayerConfidence,
                    "Player1AELOEnd" as PlayerPTIEnd,
                    "Player1AELOScale" PlayerScale,
                    "Player1AELOStart" PlayerPTI,
                    "Player1AID" PlayerID,
                    "Player1AName" PlayerName,
                    
                    "Player2AELOConfidence" PartnerConfidence,
                    "Player2AELOEnd" PartnerPTIEnd,
                    "Player2AELOScale" PartnerScale,
                    "Player2AELOStart" PartnerPTI,
                    "Player2AID" PartnerID,
                    "Player2AName" PartnerName,
                    
                    Player1AELOStart+Player2AELOStart TeamPTI,
                    Player1AELOEnd+Player2AELOEnd TeamPTIEnd,
                    case when Player1AName < Player2AName THEN Player1AName|| '/' || Player2AName ELSE Player2AName|| '/' || Player1AName END  Partnership,
                    
                    Player1HELOStart+Player2HELOStart OppPTI,
                    Player1HELOEnd+Player2HELOEnd OppPTIEnd,
                    case when Player1HName < Player2HName THEN Player1HName|| '/' || Player2HName ELSE Player2HName|| '/' || Player1HName END Opponent
                    
                    from matches
                    Union All
                    select date,ScheduleID,LineNumber,LineID,SeasonID,LeagueID,
                    "Player2AELOConfidence" as PlayerConfidence,
                    "Player2AELOEnd" as PlayerPTIEnd,
                    "Player2AELOScale" PlayerScale,
                    "Player2AELOStart" PlayerPTI,
                    "Player2AID" PlayerID,
                    "Player2AName" PlayerName,
                    
                    "Player1AELOConfidence" PartnerConfidence,
                    "Player1AELOEnd" PartnerPTIEnd,
                    "Player1AELOScale" PartnerScale,
                    "Player1AELOStart" PartnerPTI,
                    "Player1AID" PartnerID,
                    "Player1AName" PartnerName,
                    
                    Player1AELOStart+Player2AELOStart TeamPTI,
                    Player1AELOEnd+Player2AELOEnd TeamPTIEnd,
                    case when Player1AName < Player2AName THEN Player1AName|| '/' || Player2AName ELSE Player2AName|| '/' || Player1AName END Partnership,
                    
                    Player1HELOStart+Player2HELOStart OppPTI,
                    Player1HELOEnd+Player2HELOEnd OppPTIEnd,
                    case when Player1HName < Player2HName THEN Player1HName|| '/' || Player2HName ELSE Player2HName|| '/' || Player1HName END Opponent
                    
                    from matches
                    Union All
                    select date,ScheduleID,LineNumber,LineID,SeasonID,LeagueID,
                    "Player1HELOConfidence" as PlayerConfidence,
                    "Player1HELOEnd" as PlayerPTIEnd,
                    "Player1HELOScale" PlayerScale,
                    "Player1HELOStart" PlayerPTI,
                    "Player1HID" PlayerID,
                    "Player1HName" PlayerName,
                    
                    "Player2HELOConfidence" PartnerConfidence,
                    "Player2HELOEnd" PartnerPTIEnd,
                    "Player2HELOScale" PartnerScale,
                    "Player2HELOStart" PartnerPTI,
                    "Player2HID" PartnerID,
                    "Player2HName" PartnerName,
                    
                    Player1HELOStart+Player2HELOStart TeamPTI,
                    Player1HELOEnd+Player2HELOEnd TeamPTIEnd,
                    case when Player1HName < Player2HName THEN Player1HName|| '/' || Player2HName ELSE Player2HName|| '/' || Player1HName END Partnership,
                    
                    Player1AELOStart+Player2AELOStart OppPTI,
                    Player1AELOEnd+Player2AELOEnd OppPTIEnd,
                    case when Player1AName < Player2AName THEN Player1AName|| '/' || Player2AName ELSE Player2AName|| '/' || Player1AName END Opponent
                    
                    from matches
                    Union All
                    select date,ScheduleID,LineNumber,LineID,SeasonID,LeagueID,
                    "Player2HELOConfidence" as PlayerConfidence,
                    "Player2HELOEnd" as PlayerPTIEnd,
                    "Player2HELOScale" PlayerScale,
                    "Player2HELOStart" PlayerPTI,
                    "Player2HID" PlayerID,
                    "Player2HName" PlayerName,
                    
                    "Player1HELOConfidence" PartnerConfidence,
                    "Player1HELOEnd" PartnerPTIEnd,
                    "Player1HELOScale" PartnerScale,
                    "Player1HELOStart" PartnerPTI,
                    "Player1HID" PartnerID,
                    "Player1HName" PartnerName,
                    
                    Player1HELOStart+Player2HELOStart TeamPTI,
                    Player1HELOEnd+Player2HELOEnd TeamPTIEnd,
                    case when Player1HName < Player2HName THEN Player1HName|| '/' || Player2HName ELSE Player2HName|| '/' || Player1HName END Partnership,
                    
                    Player1AELOStart+Player2AELOStart OppPTI,
                    Player1AELOEnd+Player2AELOEnd OppPTIEnd,
                    case when Player1AName < Player2AName THEN Player1AName|| '/' || Player2AName ELSE Player2AName|| '/' || Player1AName END Opponent
                    
                    from matches
        """)
        statements.append("""
        CREATE VIEW "tournament_schedules" AS select Distinct t.Name, t.StartDate, LevelName, CompassLocation, BottomDepth as "Round", ScheduleID, t.tournamentid, l.levelid from tournament_matches m
            left join tournament_levels l on (m.levelID=l.levelid)
            left join tournaments t on (l.TournamentID = t.tournamentid)

        """)        
        statements.append("""

        """)

        for statement in statements:
            c.execute(statement)

        sql_conn.commit()