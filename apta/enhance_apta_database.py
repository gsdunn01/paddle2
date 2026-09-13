import sqlite3
import pandas as pd

# function to unchain the inconsistent player mappings to minimal set 
# returns a player dict that maps ALIAS -> Unique ID (minimum alias)  
def fully_unchain(mapping):
    def unchain(mapping):
        # Input:  Dict of ID -> List of IDs
        # Output: Dict combining chained IDs (1-level) 
        newmapping={}
        skip=[]
        for k,varray in mapping.items():
            if k not in skip:
                for v in varray:
                    if v in mapping:
                        newmapping[k]=list(set(mapping[k]) | set(mapping[k]))
                        skip.append(v)
                    else: 
                        newmapping[k]=mapping[k]
        return newmapping

    # iteratively unchain until we no longer reduce the number of linked sets   
    numkeys=len(mapping.keys())
    while numkeys>0:
        print(f"Number of Keys: {numkeys}")
        mapping=unchain(mapping)
        if numkeys==len(mapping.keys()):
            break;
        else:
            numkeys=len(mapping.keys())
            
    #generate final lookup table
            
    final_lookup_table={}
    for k,v in mapping.items():
        uniqueid=min(v)
        for alias in v:
            final_lookup_table[alias]=uniqueid  
            
    return final_lookup_table



def add_player_id_map(conn, player_dict):
    cur=conn.cursor()
    cur.execute("drop table if exists player_id_map")
    cur.execute("create table player_id_map (alias INTEGER PRIMARY KEY, playerid INTEGER)")
    cur.executemany("insert into player_id_map values (?,?);", list(player_dict.items()))
    print(f"{cur.rowcount} rows inserted")
    cur.close()



def add_unified_views(database_path):
    conn = sqlite3.connect(database_path)

    # READ the paddlescores players table data
    df=pd.read_sql('SELECT playerID,json_each.value as value FROM players,json_each(matches)', conn) 
    mapping={}
    for k,v in zip(df['PlayerID'],df['value']):
        if k in mapping:
            if v not in mapping[k]:
                mapping[k].append(v)
        else:
            mapping[k]=[v]
            
    player_dict=fully_unchain(mapping)
    add_player_id_map(conn,player_dict)
    create_matches_unified_view(conn)
    create_byplayers_unified_view(conn)
    conn.commit()
    conn.close()



def create_matches_unified_view(conn):
    cur=conn.cursor()
    cur.execute('DROP VIEW IF EXISTS "matches_unified"')
    cur.execute(""" CREATE VIEW "matches_unified" AS SELECT
                "Bye", "Date", "DivisionID", "LineID", "LineNumber", "Main", 
                "Player1AELOConfidence", "Player1AELOEnd", "Player1AELOScale", "Player1AELOStart", p1a.playerid "Player1AID", "Player1AName", 
                "Player1HELOConfidence", "Player1HELOEnd", "Player1HELOScale", "Player1HELOStart", p1h.playerid "Player1HID", "Player1HName", 
                "Player2AELOConfidence", "Player2AELOEnd", "Player2AELOScale", "Player2AELOStart", p2a.playerid "Player2AID", "Player2AName", 
                "Player2HELOConfidence", "Player2HELOEnd", "Player2HELOScale", "Player2HELOStart", p2h.playerid "Player2HID", "Player2HName", 
                "ScheduleID", "Set1.SetID", "Set1.SetNumber", "Set1.T1TieBreak", "Set1.T2TieBreak", "Set1.Team1Score", "Set1.Team2Score", "Set2.SetID", "Set2.SetNumber", "Set2.T1TieBreak", "Set2.T2TieBreak", "Set2.Team1Score", "Set2.Team2Score", "Set3.SetID", "Set3.SetNumber", "Set3.T1TieBreak", "Set3.T2TieBreak", "Set3.Team1Score", "Set3.Team2Score", "Set4.SetID", "Set4.SetNumber", "Set4.T1TieBreak", "Set4.T2TieBreak", "Set4.Team1Score", "Set4.Team2Score", "Set5.SetID", "Set5.SetNumber", "Set5.T1TieBreak", "Set5.T2TieBreak", "Set5.Team1Score", "Set5.Team2Score", "Team1", "Team1ID", "Team2", "Team2ID", "Winner", "match.DivisionID", "SeasonID", "LeagueID"

                from matches
                inner join player_id_map p1a on (p1a.alias = player1aid)
                inner join player_id_map p2a on (p2a.alias = player2aid)
                inner join player_id_map p1h on (p1h.alias = player1hid)
                inner join player_id_map p2h on (p2h.alias = player2hid);
                """)
    cur.close()

def create_byplayers_unified_view(conn):
    cur=conn.cursor()
    cur.execute('DROP VIEW IF EXISTS "byplayers_unified"')
    cur.execute("""
            CREATE VIEW "byplayers_unified" AS select date,ScheduleID,LineNumber,SeasonID,LeagueID,
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
                    
                    Team2ID TeamID, Team1ID OppTeamID,

                    Player1AELOStart+Player2AELOStart TeamPTI,
                    Player1AELOEnd+Player2AELOEnd TeamPTIEnd,
                    case when Player1AName < Player2AName THEN Player1AName|| '/' || Player2AName ELSE Player2AName|| '/' || Player1AName END  Partnership,
                    
                    Player1HELOStart+Player2HELOStart OppPTI,
                    Player1HELOEnd+Player2HELOEnd OppPTIEnd,
                    case when Player1HName < Player2HName THEN Player1HName|| '/' || Player2HName ELSE Player2HName|| '/' || Player1HName END Opponent
                    
                    from matches_unified
                    Union All
                    select date,ScheduleID,LineNumber,SeasonID,LeagueID,
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
                    
                    Team2ID TeamID, Team1ID OppTeamID,

                    Player1AELOStart+Player2AELOStart TeamPTI,
                    Player1AELOEnd+Player2AELOEnd TeamPTIEnd,
                    case when Player1AName < Player2AName THEN Player1AName|| '/' || Player2AName ELSE Player2AName|| '/' || Player1AName END Partnership,
                    
                    Player1HELOStart+Player2HELOStart OppPTI,
                    Player1HELOEnd+Player2HELOEnd OppPTIEnd,
                    case when Player1HName < Player2HName THEN Player1HName|| '/' || Player2HName ELSE Player2HName|| '/' || Player1HName END Opponent
                    
                    from matches_unified
                    Union All
                    select date,ScheduleID,LineNumber,SeasonID,LeagueID,
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
                    
                    Team1ID TeamID, Team2ID OppTeamID,

                    Player1HELOStart+Player2HELOStart TeamPTI,
                    Player1HELOEnd+Player2HELOEnd TeamPTIEnd,
                    case when Player1HName < Player2HName THEN Player1HName|| '/' || Player2HName ELSE Player2HName|| '/' || Player1HName END Partnership,
                    
                    Player1AELOStart+Player2AELOStart OppPTI,
                    Player1AELOEnd+Player2AELOEnd OppPTIEnd,
                    case when Player1AName < Player2AName THEN Player1AName|| '/' || Player2AName ELSE Player2AName|| '/' || Player1AName END Opponent
                    
                    from matches_unified
                    Union All
                    select date,ScheduleID,LineNumber,SeasonID,LeagueID,
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
                    
                    Team1ID TeamID, Team2ID OppTeamID,

                    Player1HELOStart+Player2HELOStart TeamPTI,
                    Player1HELOEnd+Player2HELOEnd TeamPTIEnd,
                    case when Player1HName < Player2HName THEN Player1HName|| '/' || Player2HName ELSE Player2HName|| '/' || Player1HName END Partnership,
                    
                    Player1AELOStart+Player2AELOStart OppPTI,
                    Player1AELOEnd+Player2AELOEnd OppPTIEnd,
                    case when Player1AName < Player2AName THEN Player1AName|| '/' || Player2AName ELSE Player2AName|| '/' || Player1AName END Opponent
                    
                    from matches_unified
                    """)
    cur.close()

def implied_confidence_resets(database_path):
    query="""CREATE VIEW "implied_confidence_resets" AS select PlayerID, Min(PlayerConfidence) as PlayerConfidence, strftime("%Y-%m-%d",Min(Date),"-1 day") as Date, Min(ScheduleID) as ScheduleID

                from (
                        select PlayerID, PlayerConfidence, Max(Date) as Date, Max(ScheduleID) as ScheduleID, Count(Distinct ScheduleID) as Dups from byplayers_unified 

                        where PlayerConfidence < 100 and PlayerConfidence >0
                        group by PlayerID, PlayerConfidence
                        having Dups >1
                        order by PlayerID, PlayerConfidence, Date, ScheduleID 
                    )
                Group by PlayerID"""
    conn = sqlite3.connect(database_path)
    conn.execute('drop view if exists implied_confidence_resets;')
    conn.execute(query)
    conn.commit()
    conn.close()

def implied_player_start_ratings(database_path):
    conn.execute('drop view if exists implied_player_start_ratings;')
    query="""CREATE VIEW "implied_player_start_ratings" AS select names.PlayerName, names.playerid, pti.PTIEND 
            from 
                (select Distinct PlayerID, 
                        first_value(PlayerPTIEnd) over ( partition by PlayerID order by playerid asc, date desc,scheduleid desc) as PTIEnd 
                    from byplayers_unified 
                    where 
                        PLayerPTIEnd is not null and 
                        playerid in (select distinct playerid from byplayers_unified where leagueid=:leagueid)  
                ) pti
                inner join player_names_unified names on (pti.playerid = names.playerid)
                
            order by 
                names.PlayerName"""
    conn = sqlite3.connect(database_path)
    conn.execute(query)
    conn.commit()
    conn.close()

def create_player_name_table(database_path):
    conn = sqlite3.connect(database_path)
    conn.execute('drop table if exists player_names_unified;')
    conn.execute("""Create Table player_names_unified  as select Distinct PlayerID, 
                    first_value(PlayerName) over (partition by PlayerID order by PlayerID,NumMatches desc) as PlayerName
                from 
                    (select PlayerID, PlayerName, count(*) NumMatches from byplayers_unified group by Playerid, Playername );
                """)
    conn.execute('Create unique index name_playerid_primary on player_names_unified ( playerid asc);')
    conn.commit()
    conn.close()


def enhance_apta_database(database):
    add_unified_views(database)
    implied_confidence_resets(database)
    create_player_name_table(database)


import sys

if __name__ == "__main__":
   for database in sys.argv[1:]:
        print(database)
        enhance_apta_database(database)