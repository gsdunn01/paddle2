import pandas as pd
import numpy as np
from scipy.stats import linregress
import math
import sqlite3
pd.options.display.max_columns = None
pd.options.display.max_rows = 20
print(f' Using Pandas version {pd.__version__}')

startDate= '2021-08-15'     # the date indicating the start period for new players.  Only those players whose first game was *after* this day are considered new.
matchCount = 4              # minimum number of matches played after 'StartDate' to be considered for PPL treatment.

# This is basically Demian's view, with LineNumber added in.
byplayer_unifiedSQL = """
                    select date,ScheduleID,LineID, LineNumber,SeasonID,LeagueID,
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
                    select date,ScheduleID,LineID, LineNumber,SeasonID,LeagueID,
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
                    select date,ScheduleID,LineID, LineNumber,SeasonID,LeagueID,
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
                    select date,ScheduleID,LineID, LineNumber,SeasonID,LeagueID,
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
"""


# Read sqlite query results into a pandas DataFrame
con = sqlite3.connect("apta.sqlite")
byplayer_unified=pd.read_sql_query(byplayer_unifiedSQL, con)

# add in an ordinal date - used later for regression
byplayer_unified['Date']=pd.to_datetime(byplayer_unified['Date'])
byplayer_unified['ord']=byplayer_unified['Date'].apply(lambda x: x.timestamp())

# For debugging, limit to single league
# byplayer_unified=byplayer_unified[byplayer_unified.LeagueID == 535 ]

# filter out where byplayer_unified is > 0
byplayer_unified=byplayer_unified[byplayer_unified.PlayerScale > 0 ]

matches_unified=pd.read_sql_query('select * from matches_unified order by Date ', con)

con.close()


def actual_score(match, winBonus=1/3.0):
	# TODO: Talk to Demian about Winner codes
	team1games = sum([int(match[field]) for field in match.keys() if "Team1Score" in field and pd.notna(match[field])])
	team2games = sum([int(match[field]) for field in match.keys() if "Team2Score" in field and pd.notna(match[field])])

	if (team1games + team2games) > 0:

		percentgames = team1games / (team1games + team2games)
		actual = -1
		# Joel Wollman has argued that Win Bonuses should not be considered because they might bias winning too much.
		if match['Winner'] in [1, 7]:
			actual = winBonus + ((1 - winBonus) * percentgames)
		elif match['Winner'] in [9]:
			actual = percentgames
		elif match['Winner'] in [2, 8, 14]:
			actual = percentgames # 2.0 * percentgames / 3.0
		# introduce two 'hacks' to avoid the problem surfaced by John Waltrous.
		# When actuals come out 0 or 100%, we have a divide by zero problem in PTI algorithm.
		if actual == 0:
			return round(0.5 / 12, 4)  # give team1 half a game when they lose 0-6, 0-6
		if actual == 1:
			return round(11.5 / 12, 4)  # take away half a game when winning 6-0, 6-0
		if actual > 0:
			return round(actual, 4)

	return np.nan

# The function TeamPlayedLikeDelta starts with some algebra that reverses the normal PTI formula.
# Instead of going from PTIDelta to Expected, it goes the other way around, from Expected to PTIDelta.
# This allows us to figure out what the Team PTI Delta would have to have been to predict the exact (Actual) outcome.
# If we assume that the team, on that day, played above/below their level, then that "TeamPlayedLike" is easily figured out.
# Finally, if we assume the 'team' played that way entirely due to one player's performance, then that player had a "playedLikePTI" on that day.
# This is a long winded way of saying that using this 'playedLike' number in the original calculator would yield no PTI Movement for the match.
# There's been some talk that this prejudices 'wins' by not accounting for the win bonus, but that's not addressed here.
def TeamPlayedLikeDelta(x):
    "Paul Low's idea about expressing PTIDiff as a PTI_PlayedLike on a certain day.  Effectively, had the player had this PTI going into the match, the Diff would have been zero."
    if np.isnan(x.ActualScore):
        return np.nan
    # Solving for 'playedLikePTI' means taking Actual Percentage, treating it like Expected, and figuring out what the implied PTI delta would've been such that Actual = Expected.
    ExpectedPct=float(x.ActualScore)
    try:
        PTIDelta=(24*math.log10((1/ExpectedPct) - 1))
    except:
        return pd.NA
    return PTIDelta

def linesApart(x):
	"A utility function to calculate when two lines are more or less parallel, but separated by some distance.  Useful for when you're trying to filter out a PPL that is meaningfully and consistently higher/lower than the true PTI."
	PLStart = x.RegressPL_PTI.intercept + x.RegressPL_PTI.slope *x.earliest.timestamp()
	PLEnd   = x.RegressPL_PTI.intercept + x.RegressPL_PTI.slope *x.latest.timestamp()
	PStart  = x.RegressPTI.intercept + x.RegressPTI.slope *x.earliest.timestamp()
	PEnd    = x.RegressPTI.intercept + x.RegressPTI.slope *x.latest.timestamp()
	if (PStart - PLStart > 5) and (PEnd - PLEnd > 5):
		return True
	else:
		return False

# Bring 'ActualScore' from matches_unified over to byplayer_unified
# TODO: ask Demian to include actual scores in byplayer_unified view
matches_unified['ActualScore'] = matches_unified.apply(lambda x: actual_score(x, winBonus=1/3.0), axis=1)

p1=matches_unified[['ScheduleID', 'LineID', 'Player1AID', 'Player1AELOStart','ActualScore']].rename(columns={'Player1AID':'PlayerID', 'Player1AELOStart':'PlayerELOStart'})
p2=matches_unified[['ScheduleID', 'LineID', 'Player2AID', 'Player2AELOStart','ActualScore']].rename(columns={'Player2AID':'PlayerID', 'Player2AELOStart':'PlayerELOStart'})
p3=matches_unified[['ScheduleID', 'LineID', 'Player1HID', 'Player1HELOStart','ActualScore']].rename(columns={'Player1HID':'PlayerID', 'Player1HELOStart':'PlayerELOStart'})
p4=matches_unified[['ScheduleID', 'LineID', 'Player2HID', 'Player2HELOStart','ActualScore']].rename(columns={'Player2HID':'PlayerID', 'Player2HELOStart':'PlayerELOStart'})

p1['ActualScore'] = round((1.0 - p1['ActualScore']),4)
p2['ActualScore'] = round((1.0 - p2['ActualScore']),4)
actualScores=pd.concat([p1,p2,p3,p4], ignore_index=True)
byplayer_unified=byplayer_unified.merge(actualScores, on=['PlayerID', 'ScheduleID', 'LineID'])

byplayer_unified['PPLMatchScale'] = byplayer_unified['PlayerScale'].clip(0,1) # JW's version of weighted sum.  Any scale > 1 should be considered 1.


byplayer_unified['TeamPlayedLikeDelta']     =  byplayer_unified.apply(lambda x: TeamPlayedLikeDelta(x), axis=1)
byplayer_unified['TeamPlayedLike']          =  byplayer_unified['OppPTI'] + byplayer_unified['TeamPlayedLikeDelta']
byplayer_unified['PlayerPlayedLike100']     = (byplayer_unified['PlayerELOStart'] + 1.00 *(byplayer_unified['TeamPlayedLike'] - byplayer_unified['TeamPTI'])).dropna().astype('float')
byplayer_unified['PlayerPlayedLike50']      = (byplayer_unified['PlayerELOStart'] + 0.50 *(byplayer_unified['TeamPlayedLike'] - byplayer_unified['TeamPTI'])).dropna().astype('float')
byplayer_unified['PlayerPlayedLike67']      = (byplayer_unified['PlayerELOStart'] + 0.67 *(byplayer_unified['TeamPlayedLike'] - byplayer_unified['TeamPTI'])).dropna().astype('float')

# Which players are showing unusually high improvement rates?  (change ascending to False to see who is worsening unusually fast!)
# By turning date into an 'ordinal' number, this is basically a classic y=mx+b line, with m being the slope of how quickly PTI is moving.
 #playerSlopesPTI=byplayer_unified.groupby('PlayerID').apply(lambda v: linregress(v.ord, v.PlayerPTIEnd)).dropna().to_frame()
#playerSlopesPTI.columns=['RegressPTI']
#playerSlopesPLPTI=byplayer_unified.groupby('PlayerID').apply(lambda v: linregress(v.ord, v.PlayerPlayedLike67)).dropna().to_frame()
#playerSlopesPLPTI.columns=['RegressPL_PTI']
playerStats=byplayer_unified.sort_values(by=['Date']).groupby('PlayerID').agg(
totalMatches=('Date', 'count'),
totalMatchesScaled = ('PPLMatchScale', 'sum'),  # Not sure what do with PlayerScale at this point.  <0?  >1?
earliest=('Date', 'min'),
latest=('Date', 'max'),
homeLeague=('LeagueID', (lambda x:x.value_counts().index[0])),
PPL67Avg = ('PlayerPlayedLike67', 'mean'),
PPL67_Avg_5 = ('PlayerPlayedLike67', (lambda x:x[0:5].mean())),
PPL67_Avg_8 = ('PlayerPlayedLike67', (lambda x:x[0:8].mean())),
PPL67_Avg_16 = ('PlayerPlayedLike67', (lambda x:x[0:16].mean())),
playerName=('PlayerName', 'first'),
startingPTI=('PlayerELOStart', 'first'),
endingPTI=('PlayerPTIEnd', 'last')
)

playerStats['PTIChange'] = playerStats['endingPTI'] - playerStats['startingPTI']
playerStats['ChgPerMatch'] = playerStats['PTIChange']/playerStats['totalMatches']

# playerStats=pd.concat([playerStats, playerSlopesPTI, playerSlopesPLPTI], axis=1)
# Assign a home league:
byplayer_unified=byplayer_unified.merge(playerStats['homeLeague'], left_on='PlayerID', right_index=True)

# Add in slope, intercept, timeSpan ..., remove for now as iteration is time consuming.
#for p in playerStats.itertuples():
#    playerStats.loc[p.Index, 'PTISlope'] = p.RegressPTI.slope
#    playerStats.loc[p.Index, 'RecStartPTI'] = p.RegressPL_PTI.intercept + p.RegressPL_PTI.slope *p.earliest.timestamp()  # Recommended Start PTI determined from Linear Regression.
#playerStats['span'] = playerStats['latest'] - playerStats['earliest']
#playerStats['linesApart'] = playerStats.apply(lambda x: linesApart(x), axis=1)

OutputFormat = ['homeLeague','playerName', 'earliest','latest','totalMatches','totalMatchesScaled',
                'PPL67Avg','PPL67_Avg_5','PPL67_Avg_8','PPL67_Avg_16','startingPTI','endingPTI','PTIChange','ChgPerMatch']

#  Round to 2..

roundCols= ['PPL67Avg','PPL67_Avg_5','PPL67_Avg_8','PPL67_Avg_16','startingPTI','endingPTI','PTIChange','ChgPerMatch']
playerStats[roundCols] = playerStats[roundCols].round(2)
#  Write out all the Stats of Relevant Players to a file.
playerStats[(playerStats.earliest > startDate)
            & (playerStats['totalMatches'] >= matchCount)][OutputFormat].to_excel('playerStats.xlsx')
			#& (playerStats.span > pd.Timedelta('60 days'))
           # & (playerStats.homeLeague == 450)
            #& (playerStats.PTISlope < SlopeThresh)
            #& (playerStats.linesApart)
            #  ].dropna(subset=['RecStartPTI']).sort_values(by='PTISlope').to_csv('playerStats.csv')
			#].sort_values(by='PTISlope').to_csv('playerStats.csv')


# Write out the 'played like' data to a file, too.
byplayer_unified[(byplayer_unified.Date > startDate)].to_csv('byPlayerData.csv.gz', index=False)

print(playerStats.groupby('homeLeague')['playerName'].count())