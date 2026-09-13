from apta_data import *
from apta_utils import *
from apta_transform import *
from utils.sql_odbc import *



def save_league_data():
    PlatformTennisAPI=APTA_Data(debug=True)
    leagues=PlatformTennisAPI.get_leagues()