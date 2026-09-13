import sqlite3
import pandas as pd
from contextlib import closing

pti_for_recent_season_players="""select names.PlayerName, names.playerid, pti.PTIEND 
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


playcount_by_team="""select PlayerName, l.ClubName, s.SeasonID, s.SeasonName, d.DivGroupName, d.DivName, d.TeamName,  NumMatches , p.PTIEnd PTI
from
	(select PlayerID, PlayerName, LeagueID, SeasonID, TeamID, count(distinct scheduleid) NumMatches from byplayers_unified where PlayerID is not 0 group by PlayerID, LeagueID, SeasonID, TeamID order by NumMatches Desc) m
	  join divisions d on ( m.SeasonID=d.SeasonID and m.TeamID=d.TeamID and m.leagueid=d.LeagueID)
	left  join locations l on (d.locationID = l.locationID and m.SeasonID=l.SeasonID)
    left  join seasons s on (m.SeasonID=s.seasonID and m.leagueid=s.leagueid)
	left join (select Distinct PlayerID, first_value(PlayerPTIEnd) over ( partition by PlayerID order by playerid asc, date desc) as PTIEnd from byplayers_unified where PLayerPTIEnd is not null) p on (m.playerid = p.playerid)
where m.teamid is not null and m.teamid is not 0 and m.leagueid=:leagueid
order by PlayerName, m.SeasonID, l.ClubName,d.DivGroupName, d.DivName"""

reports=[
		{'leagueid':507,'outputfile':"507_pti.csv",'query':pti_for_recent_season_players},
		{'leagueid':512,'outputfile':"512_pti.csv",'query':pti_for_recent_season_players},
		{'leagueid':512,'outputfile':"512_playcount.csv",'query':playcount_by_team},
		{'leagueid':450,'outputfile':"450_playcount.csv",'query':playcount_by_team},
		{'leagueid':467,'outputfile':"467_playcount.csv",'query':playcount_by_team}
		]


def run_reports(database):
    
    with closing(sqlite3.connect(database)) as sql_conn:
        for report in reports:
            df=pd.read_sql(report['query'],sql_conn,params=report)
            df.to_csv(report['outputfile'],index=False)

if __name__ == "__main__":
    run_reports("apta.sqlite")
