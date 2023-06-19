"""
Constants used throughout MAB.

Depends on: nothing
Modules are imported according to the following hierarchy:
constants -> database -> helpers/embeds -> Views -> commands

"""

# libraries
import ast
import asyncpraw
import os
import discord
from discord.ext import commands
from dotenv import load_dotenv
from PIL import ImageFont
from time import strftime


# Define whether the bot is in testing or live mode. Default is testing mode.
_production = ast.literal_eval(os.environ.get('PTN_MISSION_ALERT_SERVICE', 'False'))


# define paths
# TODO - check these all work in both live and testing, particularly default / fonts
TESTING_DATA_PATH = os.path.join(os.getcwd(), 'ptn', 'missionalertbot', 'data') # defines the path for use in a local testing environment
DATA_DIR = os.getenv('PTN_MAB_DATA_DIR', TESTING_DATA_PATH)
TESTING_RESOURCE_PATH = os.path.join(os.getcwd(), 'ptn', 'missionalertbot', 'resources') # defines the path for static resources in the local testing environment
RESOURCE_DIR = os.getenv('PTN_MAB_RESOURCE_DIR', TESTING_RESOURCE_PATH)

# database paths
DB_PATH = os.path.join(DATA_DIR, 'database')
CARRIERS_DB_PATH = os.path.join(DATA_DIR, 'database', 'carriers.db')
MISSIONS_DB_PATH = os.path.join(DATA_DIR, 'database', 'missions.db')
BACKUP_DB_PATH = os.path.join(DATA_DIR, 'database', 'backups')
SQL_PATH = os.path.join(DATA_DIR, 'database', 'db_sql')

# image paths
IMAGE_PATH = os.path.join(DATA_DIR, 'images')
CC_IMAGE_PATH = os.path.join(DATA_DIR, 'images', 'cc')

# static resource paths
RESOURCE_PATH = os.path.join(RESOURCE_DIR)
DEF_IMAGE_PATH = os.path.join(RESOURCE_DIR, 'default')
EDMC_OFF_PATH = os.path.join(RESOURCE_DIR, 'edmc_off')
FONT_PATH = os.path.join(RESOURCE_DIR, 'font')


# Get the discord token from the local .env file. Deliberately not hosted in the repo or Discord takes the bot down
# because the keys are exposed. DO NOT HOST IN THE PUBLIC REPO.
# load_dotenv(os.path.join(DATA_DIR, '.env'))
load_dotenv(os.path.join(DATA_DIR, '.env'))


# define bot token
TOKEN = os.getenv('MAB_BOT_DISCORD_TOKEN_PROD') if _production else os.getenv('MAB_BOT_DISCORD_TOKEN_TESTING')


# define bot object
bot = commands.Bot(command_prefix='m.', intents=discord.Intents.all())


# Production variables
PROD_FLAIR_MISSION_START = "d01e6808-9235-11eb-9cc0-0eb650439ee7"
PROD_FLAIR_MISSION_STOP = "eea2d818-9235-11eb-b86f-0e50eec082f5"
PROD_DISCORD_GUILD = 800080948716503040 # PTN Discord server
PROD_TRADE_ALERTS_ID = 801798469189763073  # trade alerts channel ID for PTN main server
PROD_WINE_ALERTS_LOADING_ID = 849249916676603944 # booze alerts channel ID for PTN main server [loading]
PROD_WINE_ALERTS_UNLOADING_ID = 932918003639648306 # booze alerts channel ID for PTN main server [unloading]
PROD_SUB_REDDIT = "PilotsTradeNetwork"  # subreddit for live
PROD_CHANNEL_UPVOTES = 828279034387103744    # The ID for the updoots channel
PROD_REDDIT_CHANNEL = 878029150336720936 # the ID for the Reddit Comments channel
PROD_MISSION_COMMAND_CHANNEL = 822603169104265276    # The ID for the production mission channel
PROD_BOT_COMMAND_CHANNEL = 802523724674891826   # Bot backend commands are locked to a channel
PROD_CTEAM_BOT_CHANNEL = 895083178761547806 # bot command channel for cteam only
PROD_BOT_SPAM_CHANNEL = 801258393205604372 # Certain bot logging messages go here
PROD_DEV_CHANNEL = 827656814911815702 # Development channel for MAB on live
PROD_UPVOTE_EMOJI = 828287733227192403 # upvote emoji on live server
PROD_O7_EMOJI = 806138784294371368 # o7 emoji on live server
PROD_HAULER_ROLE = 875313960834965544 # hauler role ID on live server
PROD_WINELOADER_ROLE = 881809680765165578 # wine loader role on live
PROD_CC_ROLE = 869340261057196072 # CC role on live server
PROD_CC_CAT = 877107894452117544 # Community Carrier category on live server
PROD_ADMIN_ROLE = 800091021852803072 # MAB Bot Admin role on live server (currently @Council)
PROD_CMENTOR_ROLE = 863521103434350613 # Community Mentor role on live server
PROD_CERTCARRIER_ROLE = 800091463160430654 # Certified Carrier role on live server
PROD_RESCARRIER_ROLE = 929985255903998002 # Fleet Reserve Carrier role on live server
PROD_TRAINEE_ROLE = 800439864797167637 # CCO Trainee role on live server
PROD_CPILLAR_ROLE = 863789660425027624 # Community Pillar role on live server
PROD_DEV_ROLE = 812988180210909214 # Developer role ID on live
PROD_MOD_ROLE = 813814494563401780 # Mod role ID on Live
PROD_TRADE_CAT = 801558838414409738 # Trade Carrier category on live server
PROD_ARCHIVE_CAT = 1048957416781393970 # Archive category on live server
PROD_SECONDS_SHORT = 120
PROD_SECONDS_LONG = 900
# Training mode - production
PROD_TRAINING_CATEGORY = 1120269131476901938
PROD_TRAINING_MISSION_COMMAND_CHANNEL = 1120269354949419030
PROD_TRAINING_CHANNEL_UPVOTES = 1120269388742918165
PROD_TRAINING_WEBHOOKS_CHANNEL = 1120270467526316102
PROD_TRAINING_TRADE_ALERTS_ID = 1120269302436741190
PROD_TRAINING_WINE_CHANNEL = 1120269435471667320

# Testing variables

# reddit flair IDs - testing sub
TEST_FLAIR_MISSION_START = "3cbb1ab6-8e8e-11eb-93a1-0e0f446bc1b7"
TEST_FLAIR_MISSION_STOP = "4242a2e2-8e8e-11eb-b443-0e664851dbff"
TEST_DISCORD_GUILD = 818174236480897055 # test Discord server
TEST_TRADE_ALERTS_ID = 843252609057423361  # trade alerts channel ID for PTN test server
TEST_WINE_ALERTS_LOADING_ID = 870425638127943700 # booze alerts channel ID for PTN test server [loading]
TEST_WINE_ALERTS_UNLOADING_ID = 870425638127943700 # booze alerts channel ID for PTN test server [unloading]
TEST_SUB_REDDIT = "PTNBotTesting"  # subreddit for testing
TEST_CHANNEL_UPVOTES = 839918504676294666    # The ID for the updoots channel on test
TEST_REDDIT_CHANNEL = 878029350933520484 # the ID for the Reddit Comments channel
TEST_MISSION_COMMAND_CHANNEL = 842138710651961364    # The ID for the production mission channel
TEST_BOT_COMMAND_CHANNEL = 842152343441375283   # Bot backend commands are locked to a channel
TEST_CTEAM_BOT_CHANNEL = 842152343441375283 # bot command channel for cteam only
TEST_BOT_SPAM_CHANNEL = 842525081858867211 # Bot logging messages on the test server
TEST_DEV_CHANNEL = 1063765215457583164 # Development channel for MAB on test
TEST_UPVOTE_EMOJI = 849388681382068225 # upvote emoji on test server
TEST_O7_EMOJI = 903744117144698950 # o7 emoji on test server
TEST_HAULER_ROLE = 875439909102575647 # hauler role ID on test server
TEST_WINELOADER_ROLE = 1119189364522623068 # wine loader role on test
TEST_CC_ROLE = 877220476827619399 # CC role on test server
TEST_CC_CAT = 877108931699310592 # Community Carrier category on test server
TEST_ADMIN_ROLE = 836367194979041351 # Bot Admin role on test server
TEST_MOD_ROLE = 903292469049974845 # Mod role on test server
TEST_CMENTOR_ROLE = 877586763672072193 # Community Mentor role on test server
TEST_CERTCARRIER_ROLE = 822999970012463154 # Certified Carrier role on test server
TEST_RESCARRIER_ROLE = 947520552766152744 # Fleet Reserve Carrier role on test server
TEST_TRAINEE_ROLE = 1048912218344923187 # CCO Trainee role on test server
TEST_CPILLAR_ROLE = 903289927184314388 # Community Pillar role on test server
TEST_DEV_ROLE = 1048913812163678278 # Dev role ID on test
TEST_TRADE_CAT = 876569219259580436 # Trade Carrier category on live server
TEST_ARCHIVE_CAT = 877244591579992144 # Archive category on live server
TEST_SECONDS_SHORT = 5
TEST_SECONDS_LONG = 10
# Training mode - test
TEST_TRAINING_CATEGORY = 1120268080912810014
TEST_TRAINING_MISSION_COMMAND_CHANNEL = 1120268484455174215
TEST_TRAINING_CHANNEL_UPVOTES = 1120268580731240519
TEST_TRAINING_WEBHOOKS_CHANNEL = 1120270731889082419
TEST_TRAINING_TRADE_ALERTS_ID = 1120268308780957696
TEST_TRAINING_WINE_CHANNEL = 1120268357447462962


EMBED_COLOUR_LOADING = 0x00d9ff         # PTN faded blue
EMBED_COLOUR_UNLOADING = 0x80ff80       # PTN emph blue
EMBED_COLOUR_REDDIT = 0xff0000          # red
EMBED_COLOUR_DISCORD = 0x8080ff         # purple
EMBED_COLOUR_RP = 0xe63946              # PTN red
EMBED_COLOUR_ERROR = 0x800000           # dark red
EMBED_COLOUR_QU = 0x00d9ff              # que?
EMBED_COLOUR_OK = 0x80ff80              # we're good here thanks, how are you?


# defining fonts for pillow use
REG_FONT = ImageFont.truetype(os.path.join(FONT_PATH, 'Exo/static/Exo-Light.ttf'), 16)
NAME_FONT = ImageFont.truetype(os.path.join(FONT_PATH, 'Exo/static/Exo-ExtraBold.ttf'), 29)
TITLE_FONT = ImageFont.truetype(os.path.join(FONT_PATH, 'Exo/static/Exo-ExtraBold.ttf'), 22)
NORMAL_FONT = ImageFont.truetype(os.path.join(FONT_PATH, 'Exo/static/Exo-Medium.ttf'), 18)
FIELD_FONT = ImageFont.truetype(os.path.join(FONT_PATH, 'Exo/static/Exo-Light.ttf'), 18)
DISCORD_NAME_FONT = ImageFont.truetype(os.path.join(FONT_PATH, 'Exo/static/Exo-ExtraBold.ttf'), 27)
DISCORD_ID_FONT = ImageFont.truetype(os.path.join(FONT_PATH, 'Exo/static/Exo-Medium.ttf'), 16)


# a list of common commodities for autocomplete
commodities_common = [
    "Agronomic Treatment",
    "Bauxite",
    "Bertrandite",
    "Gold",
    "Indite",
    "Silver",
    "Tritium",
    "Wine"
]


# random gifs and images

byebye_gifs = [
    'https://media.tenor.com/gRgywxwuxb0AAAAd/explosion-gi-joe-a-real-american-hero.gif',
    'https://media.tenor.com/a7LMG-8ldlAAAAAC/ice-cube-bye-felicia.gif',
    'https://media.tenor.com/SqrZAbYtcq0AAAAC/madagscar-penguins.gif',
    'https://media.tenor.com/ctCdr1R4ga4AAAAC/boom-explosion.gif'
]

boom_gifs = [
    'https://media.tenor.com/xGJ5PEQ9lLYAAAAC/self-destruction-imminent-please-evacuate.gif'
    'https://media.tenor.com/gRgywxwuxb0AAAAd/explosion-gi-joe-a-real-american-hero.gif',
    'https://media.tenor.com/a7LMG-8ldlAAAAAC/ice-cube-bye-felicia.gif',
    'https://media.tenor.com/v_d_Flu6pY0AAAAC/countdown-lastseconds.gif',
    'https://media.tenor.com/Ijf5y9BUgg8AAAAC/final-countdown-countdown.gif',
    'https://media.tenor.com/apADIQqKnSEAAAAC/self-destruct-mission-impossible.gif',
    'https://media.tenor.com/ctCdr1R4ga4AAAAC/boom-explosion.gif'
]

hello_gifs = [
    'https://media.tenor.com/DSG9ZID25nsAAAAC/hello-there-general-kenobi.gif', # obi wan
    'https://media.tenor.com/uNQvTg9Tk_QAAAAC/hey-tom-hanks.gif', # tom hanks
    'https://media.tenor.com/-z2KfO5zAckAAAAC/hello-there-baby-yoda.gif', # baby yoda
    'https://media.tenor.com/iZPmuJ0KON8AAAAd/hello-there.gif', # toddler
    'https://media.tenor.com/KKvpO702avgAAAAC/hey-hay.gif', # rollerskates
    'https://media.tenor.com/pE2UP8CBBuwAAAAC/jim-carrey-funny.gif', # jim carrey
    'https://media.tenor.com/-UiIDx_KNUUAAAAd/hi-friends-baby-goat.gif' # goat
]

error_gifs = [
    'https://tenor.com/view/beaker-fire-shit-omg-disaster-gif-4767835',
    'https://tenor.com/view/nothingtosee-disperse-casual-explosion-gif-4545906',
    'https://tenor.com/view/spongebob-patrick-panic-run-scream-gif-4656335',
    'https://tenor.com/view/angry-panda-rage-mad-gif-11780191'
]

current_month = strftime('%B')

# logo URLs from website
PTN_LOGO_DARK_TEXT_TRANSPARENT = 'https://pilotstradenetwork.com/wp-content/uploads/2021/08/PTN_Dark_wText.png'
PTN_LOGO_PRIDE_TEXT_TRANSPARENT = 'https://pilotstradenetwork.com/wp-content/uploads/2023/06/PTN_Pride_2022_transparent_wText.png'

PTN_LOGO_DISCORD_BG = 'https://pilotstradenetwork.com/wp-content/uploads/2021/08/PTN_Discord_Icon.png'
PTN_LOGO_DISCORD_BG_PRIDE = 'https://pilotstradenetwork.com/wp-content/uploads/2023/06/discord-logo-pride-2023-cropped.png'

def ptn_logo_full():
  return PTN_LOGO_PRIDE_TEXT_TRANSPARENT if current_month == 'June' else PTN_LOGO_DARK_TEXT_TRANSPARENT

def ptn_logo_discord():
  return PTN_LOGO_DISCORD_BG_PRIDE if current_month == 'June' else PTN_LOGO_DISCORD_BG

# mission template filenames
reddit_template = 'reddit_template.png'
reddit_template_pride = 'reddit_template_pride.png'

def mission_template_filename():
  return reddit_template_pride if current_month == 'June' else reddit_template

DISCORD_TEMPLATE = 'discord_template.png'

# images and icons used in mission embeds
BLANKLINE_400PX = 'https://pilotstradenetwork.com/wp-content/uploads/2023/01/400x1-00000000.png'
ICON_BUY = 'https://pilotstradenetwork.com/wp-content/uploads/2023/05/Trade.png'
ICON_SELL = 'https://pilotstradenetwork.com/wp-content/uploads/2023/06/Credit.png'
ICON_DATA = 'https://pilotstradenetwork.com/wp-content/uploads/2023/06/Data.png'
ICON_DISCORD_CIRCLE = 'https://pilotstradenetwork.com/wp-content/uploads/2023/06/discord-icon-in-circle.png'
ICON_DISCORD_PING = 'https://pilotstradenetwork.com/wp-content/uploads/2023/06/discord-notification-dot-icon.png'
ICON_REDDIT = 'https://pilotstradenetwork.com/wp-content/uploads/2023/06/reddit-logo.png'
ICON_WEBHOOK_PTN = 'https://pilotstradenetwork.com/wp-content/uploads/2023/06/discord-webhook-icon-in-circle.png'
ICON_FC_LOADING = 'https://pilotstradenetwork.com/wp-content/uploads/2023/06/fc_loading_thick_sihmm.png'
ICON_FC_UNLOADING = 'https://pilotstradenetwork.com/wp-content/uploads/2023/06/fc_unloading_thick_sihmm.png'
ICON_EDMC_OFF = 'https://pilotstradenetwork.com/wp-content/uploads/2023/06/edmc_off_2.jpg'
ICON_FC_COMPLETE = 'https://pilotstradenetwork.com/wp-content/uploads/2023/05/fc_complete.png'
ICON_FC_EMPTY = 'https://pilotstradenetwork.com/wp-content/uploads/2023/06/fc_empty.png'


# discord direct invite URL
DISCORD_INVITE_URL = 'https://discord.gg/ptn'

# link to our Discord by way of Josh's original post on Reddit
REDDIT_DISCORD_LINK_URL = \
    'https://www.reddit.com/r/PilotsTradeNetwork/comments/l0y7dk/pilots_trade_network_intergalactic_discord_server/'


# define constants based on prod or test environment
def reddit_flair_mission_start():
  return PROD_FLAIR_MISSION_START if _production else TEST_FLAIR_MISSION_START

def reddit_flair_mission_stop():
  return PROD_FLAIR_MISSION_STOP if _production else TEST_FLAIR_MISSION_STOP

def bot_guild():
  return PROD_DISCORD_GUILD if _production else TEST_DISCORD_GUILD

guild_obj = discord.Object(bot_guild())

def sub_reddit():
  return PROD_SUB_REDDIT if _production else TEST_SUB_REDDIT

def trade_alerts_channel():
  return PROD_TRADE_ALERTS_ID if _production else TEST_TRADE_ALERTS_ID

def wine_alerts_loading_channel():
  return PROD_WINE_ALERTS_LOADING_ID if _production else TEST_WINE_ALERTS_LOADING_ID

def wine_alerts_unloading_channel():
  return PROD_WINE_ALERTS_UNLOADING_ID if _production else TEST_WINE_ALERTS_UNLOADING_ID

def channel_upvotes():
  return PROD_CHANNEL_UPVOTES if _production else TEST_CHANNEL_UPVOTES

def reddit_channel():
  return PROD_REDDIT_CHANNEL if _production else TEST_REDDIT_CHANNEL

def mission_command_channel():
  return PROD_MISSION_COMMAND_CHANNEL if _production else TEST_MISSION_COMMAND_CHANNEL

def bot_command_channel():
  return PROD_BOT_COMMAND_CHANNEL if _production else TEST_BOT_COMMAND_CHANNEL

def cteam_bot_channel(): # formerly admin_bot_channel / ADMIN_BOT_CHANNEL
  return PROD_CTEAM_BOT_CHANNEL if _production else TEST_CTEAM_BOT_CHANNEL

def bot_spam_channel():
  return PROD_BOT_SPAM_CHANNEL if _production else TEST_BOT_SPAM_CHANNEL

def bot_dev_channel():
  return PROD_DEV_CHANNEL if _production else TEST_DEV_CHANNEL

def upvote_emoji():
  return PROD_UPVOTE_EMOJI if _production else TEST_UPVOTE_EMOJI

def o7_emoji():
  return PROD_O7_EMOJI if _production else TEST_O7_EMOJI

def hauler_role():
  return PROD_HAULER_ROLE if _production else TEST_HAULER_ROLE

def wineloader_role():
  return PROD_WINELOADER_ROLE if _production else TEST_WINELOADER_ROLE

def cc_role():
  return PROD_CC_ROLE if _production else TEST_CC_ROLE

def cc_cat():
  return PROD_CC_CAT if _production else TEST_CC_CAT

def admin_role():
  return PROD_ADMIN_ROLE if _production else TEST_ADMIN_ROLE

def mod_role():
  return PROD_MOD_ROLE if _production else TEST_MOD_ROLE

def cmentor_role():
  return PROD_CMENTOR_ROLE if _production else TEST_CMENTOR_ROLE

def certcarrier_role():
  return PROD_CERTCARRIER_ROLE if _production else TEST_CERTCARRIER_ROLE

def rescarrier_role():
  return PROD_RESCARRIER_ROLE if _production else TEST_RESCARRIER_ROLE

def trainee_role():
  return PROD_TRAINEE_ROLE if _production else TEST_TRAINEE_ROLE

def cpillar_role():
  return PROD_CPILLAR_ROLE if _production else TEST_CPILLAR_ROLE

def dev_role():
  return PROD_DEV_ROLE if _production else TEST_DEV_ROLE

def trade_cat():
  return PROD_TRADE_CAT if _production else TEST_TRADE_CAT

def archive_cat():
  return PROD_ARCHIVE_CAT if _production else TEST_ARCHIVE_CAT

def seconds_short():
  return PROD_SECONDS_SHORT if _production else TEST_SECONDS_SHORT

def seconds_long():
  return PROD_SECONDS_LONG if _production else TEST_SECONDS_LONG


any_elevated_role = [cc_role(), cmentor_role(), certcarrier_role(), rescarrier_role(), admin_role(), trainee_role(), dev_role()]


async def get_reddit():
    """
    Return reddit instance
    discord.py complains if an async resource is not initialized
    inside async
    """
    return asyncpraw.Reddit('bot1')


async def get_overwrite_perms():
    """
    Default permission set for all temporary channel managers (CCOs, CCs)
    """
    overwrite = discord.PermissionOverwrite()
    overwrite.read_messages = True
    overwrite.manage_channels = True
    overwrite.manage_roles = True
    overwrite.manage_webhooks = True
    overwrite.create_instant_invite = True
    overwrite.send_messages = True
    overwrite.embed_links = True
    overwrite.attach_files = True
    overwrite.add_reactions = True
    overwrite.external_emojis = True
    overwrite.manage_messages = True
    overwrite.read_message_history = True
    overwrite.use_application_commands = True
    return overwrite


async def get_guild():
    """
    Return bot guild instance for use in get_member()
    """
    return bot.get_guild(bot_guild())