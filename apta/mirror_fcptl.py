import sys
from apta_data import * 
from apta_transform import *
from apta_utils import *    


if __name__ == "__main__":
    for leagueid in sys.argv[1:]:
        league_data=APTA_League_Data(league=leagueid,dock=APTA_Data(debug=True)) # ,param_transformer=generate_paddlescores_payload))
        if not path.exists("{}.sqlite".format(leagueid)):
            league_data.mirror_api(transform=False,fetch_function=fetch_and_save_file)
            #league_data.mirror_api(transform=True,output=['csv','sqlite'],fetch_function=fetch_and_save_file)
        



# Here's how to mirror the whole data set

# PlatformTennisAPI=APTA_Data(debug=True)
# leagues=PlatformTennisAPI.get_leagues()

# df=pd.json_normalize(leagues)
# save_df_tosqlite("apta.sqlite","leagues",df)

# for leagueid in [ league['PSLeagueID'] for league in leagues]:
#     league_data=APTA_League_Data(league=leagueid,dock=PlatformTennisAPI)
#     if not path.exists("{}.sqlite".format(leagueid)):
#         league_data.mirror_api(transform=True,output=['csv','sqlite'])