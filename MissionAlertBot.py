# MissionAlertBot.py
# Discord bot to help PTN Carrier Owners post trade missions to Discord and Reddit
# By Charles Tosh 17 March 2021
# Additional contributions by Alexander Leidinger
# Discord Developer Portal: https://discord.com/developers/applications/822146046934384640/information
# Git repo: https://github.com/PilotsTradeNetwork/MissionAlertBot
import ast
import copy
import tempfile
from itertools import islice
from math import ceil

from PIL import Image, ImageFont, ImageDraw
import os
import sys
import discord
import sqlite3
import asyncpraw
import asyncio
import shutil
from discord import channel
from discord.errors import HTTPException, InvalidArgument, Forbidden, NotFound
from discord.ext import commands
from discord.utils import get
from discord_slash import SlashCommand, SlashContext
from datetime import datetime
from datetime import timezone
from dotenv import load_dotenv
from dateutil.relativedelta import relativedelta
import constants
import random
#
#                       INIT STUFF
#

# Ast will parse a value into a python type, but if you try to give a boolean its going to get into problems. Just use
# a string and be consistent.
from CarrierData import CarrierData
from Commodity import Commodity
from MissionData import MissionData
from CommunityCarrierData import CommunityCarrierData

_production = ast.literal_eval(os.environ.get('PTN_MISSION_ALERT_SERVICE', 'False'))

# We need some locks to we wait on the DB queries
carrier_db_lock = asyncio.Lock()
mission_db_lock = asyncio.Lock()
carrier_channel_lock = asyncio.Lock()

# setting some variables, you can toggle between production and test by setting an env variable flag now,
# PTN-MISSION-ALERT-SERVICE
conf = constants.get_constant(_production)

bot_guild_id = int(conf['BOT_GUILD'])

flair_mission_start = conf['MISSION_START']
flair_mission_stop = conf['MISSION_STOP']

# channel IDs
trade_alerts_id = conf['TRADE_ALERTS_ID']
wine_alerts_id = conf['WINE_ALERTS_ID']
bot_spam_id = conf['BOT_SPAM_CHANNEL']
to_subreddit = conf['SUB_REDDIT']
cc_cat_id = conf['CC_CAT']
trade_cat_id = conf['TRADE_CAT']
archive_cat_id = conf['ARCHIVE_CAT']

# role IDs
hauler_role_id = conf['HAULER_ROLE']
cc_role_id = conf['CC_ROLE']

# emoji IDs
upvote_emoji = conf['UPVOTE_EMOJI']

# channel removal timers
seconds_short = conf['SECONDS_SHORT']
seconds_long = conf['SECONDS_LONG']

# Get the discord token from the local .env file. Deliberately not hosted in the repo or Discord takes the bot down
# because the keys are exposed. DO NOT HOST IN THE REPO. Seriously do not do it ...
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN_PROD') if _production else os.getenv('DISCORD_TOKEN_TESTING')

# create reddit instance
reddit = asyncpraw.Reddit('bot1')

# connect to sqlite carrier database
carriers_conn = sqlite3.connect('carriers.db')
carriers_conn.row_factory = sqlite3.Row
carrier_db = carriers_conn.cursor()

# connect to sqlite missions database
missions_conn = sqlite3.connect('missions.db')
missions_conn.row_factory = sqlite3.Row
mission_db = missions_conn.cursor()

# channel go boom gifs

byebye_gifs = [
    'https://tenor.com/view/explosion-gi-joe-a-real-american-hero-amusement-park-of-terror-the-revenge-of-cobra-boom-gif-17284145',
    'https://tenor.com/view/ice-cube-bye-felicia-bye-gif-8310816',
    'https://tenor.com/view/madagscar-penguins-kaboom-gif-9833865',
    'https://tenor.com/view/boom-explosion-moonbeam-city-gif-20743300',
]

boom_gifs = [
    'https://tenor.com/view/explosion-gi-joe-a-real-american-hero-amusement-park-of-terror-the-revenge-of-cobra-boom-gif-17284145',
    'https://tenor.com/view/ice-cube-bye-felicia-bye-gif-8310816',
    'https://c.tenor.com/v_d_Flu6pY0AAAAM/countdown-lastseconds.gif',
    'https://tenor.com/view/final-countdown-countdown-europe-counting-music-video-gif-4789617',
    'https://tenor.com/view/self-destruct-mission-impossible-conversation-tape-match-gif-20113224',
    'https://tenor.com/view/madagscar-penguins-kaboom-gif-9833865',
    'https://tenor.com/view/boom-explosion-moonbeam-city-gif-20743300',
]

hello_gifs = [
    'https://tenor.com/view/hello-there-hi-there-greetings-gif-9442662',
    'https://tenor.com/view/hey-tom-hanks-forrest-gump-gif-5114770',
    'https://tenor.com/view/hello-there-baby-yoda-mandolorian-hello-gif-20136589',
    'https://tenor.com/view/oh-hello-there-sassy-fab-gif-14129058',
    'https://tenor.com/view/world-star-hey-girl-hey-there-when-you-see-your-crush-feeling-yourself-gif-10605207',
    'https://tenor.com/view/bye-jim-carrey-ciao-gif-5139786',
    'https://tenor.com/view/hi-friends-baby-goat-saying-hello-saying-hi-hi-neighbor-gif-14737423',
]

error_gifs = [
    'https://tenor.com/view/beaker-fire-shit-omg-disaster-gif-4767835',
    'https://tenor.com/view/naked-gun-explosion-disaster-nothing-to-see-here-please-disperse-gif-13867629',
    'https://tenor.com/view/spongebob-patrick-panic-run-scream-gif-4656335',
    'https://tenor.com/view/angry-panda-rage-mad-gif-11780191',
]

#
#                       DATABASE STUFF
#


print('MissionAlertBot starting')
print(f'Configuring to run against: {"Production" if _production else "Testing"} env.')


# create carrier record if necessary (only needed on first run)
def check_database_table_exists(table_name, database):
    """
    Checks whether a carrier exists in the database already.

    :param str table_name:  The database string name to create.
    :param sqlite.Connection.cursor database: The database to connect againt.
    :returns: A boolean state, True if it exists, else False
    :rtype: bool
    """
    database.execute('''SELECT count(name) FROM sqlite_master WHERE TYPE = 'table' AND name = '{}' '''.format(
        table_name))
    return bool(database.fetchone()[0])


print('Starting up - checking carriers database if it exists or not')
if not check_database_table_exists('carriers', carrier_db):
    print('Carriers database missing - creating it now')

    if os.path.exists(os.path.join(os.getcwd(), 'db_sql', 'carriers_dump.sql')):
        # recreate from backup file
        print('Recreating database from backup ...')
        with open(os.path.join(os.getcwd(), 'db_sql', 'carriers_dump.sql')) as f:
            sql_script = f.read()
            carrier_db.executescript(sql_script)

        # print('Loaded the following data: ')
        # carrier_db.execute('''SELECT * from carriers ''')
        # for e in carrier_db.fetchall():
        #     print(f'\t {CarrierData(e)}')
    else:
        # Create a new version
        print('No backup found - Creating empty database')
        carrier_db.execute('''
            CREATE TABLE carriers( 
                p_ID INTEGER PRIMARY KEY AUTOINCREMENT,
                shortname TEXT NOT NULL UNIQUE, 
                longname TEXT NOT NULL, 
                cid TEXT NOT NULL, 
                discordchannel TEXT NOT NULL,
                channelid INT,
                ownerid INT
            ) 
        ''')
else:
    print('Carrier database exists, do nothing')

print('Starting up - checking community_carriers database if it exists or not')
# create Community Carriers table if necessary
if not check_database_table_exists('community_carriers', carrier_db):
    print('Community Carriers database missing - creating it now')

    if os.path.exists(os.path.join(os.getcwd(), 'db_sql', 'community_carriers_dump.sql')):
        # recreate from backup file
        print('Recreating database from backup ...')
        with open(os.path.join(os.getcwd(), 'db_sql', 'community_carriers_dump.sql')) as f:
            sql_script = f.read()
            carrier_db.executescript(sql_script)

        # print('Loaded the following data: ')
        # carrier_db.execute('''SELECT * from carriers ''')
        # for e in carrier_db.fetchall():
        #     print(f'\t {CarrierData(e)}')
    else:
        # Create a new version
        print('No backup found - Creating empty database')
        carrier_db.execute('''
            CREATE TABLE community_carriers( 
                ownerid INT NOT NULL UNIQUE,
                channelid INT NOT NULL UNIQUE
            ) 
        ''')
else:
    print('Community Carrier database exists, do nothing')

print('Starting up - checking missions database if it exists or not')
# create missions db if necessary
if not check_database_table_exists('missions', mission_db):
    print('Mission database missing - creating it now')

    if os.path.exists(os.path.join(os.getcwd(), 'db_sql', 'missions_dump.sql')):
        # recreate from backup file
        print('Recreating mission db database from backup ...')
        with open(os.path.join(os.getcwd(), 'db_sql', 'missions_dump.sql')) as f:
            sql_script = f.read()
            mission_db.executescript(sql_script)

        # print('Loaded the following data: ')
        # mission_db.execute('''SELECT * from missions ''')
        # for e in mission_db.fetchall():
        #     print(f'\t {MissionData(e)}')

    else:
        # Create a new version
        print('No backup found - Creating empty database')
        mission_db.execute('''
            CREATE TABLE missions(
                "carrier"	TEXT NOT NULL UNIQUE,
                "cid"	TEXT,
                "channelid"	INT,
                "commodity"	TEXT,
                "missiontype"	TEXT,
                "system"	TEXT NOT NULL,
                "station"	TEXT,
                "profit"	INTEGER,
                "pad"	TEXT,
                "demand"    TEXT,
                "rp_text"	TEXT,
                "reddit_post_id"	TEXT,
                "reddit_post_url"	TEXT,
                "reddit_comment_id"	TEXT,
                "reddit_comment_url"	TEXT,
                "discord_alert_id"	INT
            )
        ''')
else:
    print('Mission database exists, do nothing')


def dump_database_test(database_name):
    """
    Dumps the database object to a .sql text file while backing up the database. Used just to get something we can
    recreate the database from.  This will only store the last state and should periodically be committed to the repo
    from the bot.

    :param str database_name: The DB name to connect against.
    :returns: None
    :raises ValueError: if the db name is unknown
    """
    # We only have 2 databases today, carriers and missions, though this could really just be 2 tables in a single
    # database at some stage.

    if database_name == 'missions':
        connection = missions_conn
    elif database_name == 'carriers':
        connection = carriers_conn
    else:
        raise ValueError(f'Unknown DB dump handling for: {database_name}')

    with open(f'db_sql/{database_name}_dump.sql', 'w') as f:
        for line in connection.iterdump():
            f.write(line)


# function to backup carrier database
def backup_database(database_name):
    """
    Creates a backup of the requested database into .backup/db_name.datetimestamp.db

    :param str database_name: The database name to back up
    :rtype: None
    """
    dt_file_string = get_formatted_date_string()[1]
    if not os.path.exists(os.path.join(os.getcwd(), 'backup')):
        # make sure the backup folder exists first
        os.mkdir(os.path.join(os.getcwd(), 'backup'))

    shutil.copy(f'{database_name}.db', f'backup/{database_name}.{dt_file_string}.db')
    print(f'Backed up {database_name}.db at {dt_file_string}')
    dump_database_test(database_name)


# function to add carrier, being sure to correct case
async def add_carrier_to_database(short_name, long_name, carrier_id, channel, channel_id, owner_id):
    """
    Inserts a carrier's details into the database.

    :param str short_name: The carriers shortname reference
    :param str long_name: The carriers full name description
    :param str carrier_id: The carriers ID value from the game
    :param str discord_channel: The carriers discord channel
    :param int channel_id: The discord channel ID for the carrier
    :returns: None
    """
    await carrier_db_lock.acquire()
    try:
        carrier_db.execute(''' INSERT INTO carriers VALUES(NULL, ?, ?, ?, ?, ?, ?) ''',
                           (short_name.lower(), long_name.upper(), carrier_id.upper(), channel, channel_id, owner_id))
        carriers_conn.commit()
    finally:
        carrier_db_lock.release()
        # copy the blank bitmap to the new carrier's name to serve until unique image uploaded
        shutil.copy('bitmap.png', f'images/{short_name.lower()}.png')


# function to remove a carrier
async def delete_carrier_from_db(p_id):
    carrier = find_carrier_from_pid(p_id)
    try:
        await carrier_db_lock.acquire()
        carrier_db.execute(f"DELETE FROM carriers WHERE p_ID = {p_id}")
        carriers_conn.commit()
    finally:
        carrier_db_lock.release()
    # archive the removed carrier's image by appending date and time of deletion to it
    try:
        shutil.move(f'images/{carrier.carrier_short_name}.png',
                    f'images/old/{carrier.carrier_short_name}.{get_formatted_date_string()[1]}.png')
    except:
        errormsg = 'Unable to backup image file, perhaps it never existed?'
        print(errormsg)
        return errormsg

    return


# function to remove a community carrier
async def delete_community_carrier_from_db(ownerid):
    carrier = find_community_carrier_with_owner_id(ownerid)
    try:
        await carrier_db_lock.acquire()
        carrier_db.execute(f"DELETE FROM community_carriers WHERE ownerid = {ownerid}")
        carriers_conn.commit()
    finally:
        carrier_db_lock.release()
    return


# function to remove all carriers, not currently used by any bot command
def _delete_all_from_database(database):
    """
    Removes all the entries from the database.

    :returns: None
    """
    carrier_db.execute(f"DELETE FROM {database}")
    carriers_conn.commit()


# function to search for a carrier by longname
def find_carrier_from_long_name(find_long_name):
    """
    Finds any carriers matching a long name

    :param str find_long_name: A short name of the carrier.
    :returns: CarrierData object for the exact match
    :rtype: CarrierData
    """
    # TODO: This needs to check an exact not a `LIKE`
    carrier_db.execute(
        f"SELECT * FROM carriers WHERE longname LIKE (?)",
        (f'%{find_long_name}%',))
    carrier_data = CarrierData(carrier_db.fetchone())
    print(f"FC {carrier_data.pid} is {carrier_data.carrier_long_name} {carrier_data.carrier_identifier} called by "
          f"shortname {carrier_data.carrier_short_name} with channel #{carrier_data.discord_channel} called "
          f"from find_carrier_from_pid.")
    return carrier_data

# find carriers from long name - temporary solution for m.find
# TODO: make every carrier longname search prompt with multiple results and use this function
def find_carrier_from_long_name_multiple(find_long_name):
    """
    Finds any carriers matching a long name

    :param str find_long_name: A short name of the carrier.
    :returns: CarrierData object for the exact match
    :rtype: CarrierData
    """
    carrier_db.execute(
        f"SELECT * FROM carriers WHERE longname LIKE (?)",
        (f'%{find_long_name}%',))
    carriers = [CarrierData(carrier) for carrier in carrier_db.fetchall()]
    for carrier_data in carriers:
        print(f"FC {carrier_data.pid} is {carrier_data.carrier_long_name} {carrier_data.carrier_identifier} called by "
              f"shortname {carrier_data.carrier_short_name} with channel #{carrier_data.discord_channel} called from "
              f"find_carrier_from_long_name.")

    return carriers


def find_carrier_with_owner_id(ownerid):
    """
    Returns all carriers matching the ownerid

    :param int ownerid: The owner id to match
    :returns: A list of carrier data objects
    :rtype: list[CarrierData]
    """
    carrier_db.execute(
        "SELECT * FROM carriers WHERE ownerid LIKE (?)", (f'%{ownerid}%',)
    )
    carrier_data = [CarrierData(carrier) for carrier in carrier_db.fetchall()]
    for carrier in carrier_data:
        print(f"FC {carrier.pid} is {carrier.carrier_long_name} {carrier.carrier_identifier} called by "
              f"shortname {carrier.carrier_short_name} with channel <#{carrier.channel_id}> "
              f"and owner {carrier.ownerid} called from find_carrier_with_owner_id.")

    return carrier_data


def find_community_carrier_with_owner_id(ownerid):
    """
    Returns channel and owner matching the ownerid

    :param int ownerid: The owner id to match
    :returns: A list of community carrier data objects
    :rtype: list[CommunityCarrierData]
    """
    carrier_db.execute(f"SELECT * FROM community_carriers WHERE "
                       f"ownerid = {ownerid} ")
    community_carrier_data = [CommunityCarrierData(community_carrier) for community_carrier in carrier_db.fetchall()]
    for community_carrier in community_carrier_data:
        print(f"{community_carrier.owner_id} owns channel {community_carrier.channel_id}" 
              f" called from find_carrier_with_owner_id.")

    return community_carrier_data

# function to search for a carrier by shortname
def find_carrier_from_short_name(find_short_name):
    """
    Finds any carriers matching a short name

    :param str find_short_name: A short name of the carrier.
    :returns: List of CarrierData
    :rtype: list[CarrierData]
    """
    carrier_db.execute(f"SELECT * FROM carriers WHERE shortname LIKE (?)", (f'%{find_short_name}%',))
    carriers = [CarrierData(carrier) for carrier in carrier_db.fetchall()]
    for carrier_data in carriers:
        print(f"FC {carrier_data.pid} is {carrier_data.carrier_long_name} {carrier_data.carrier_identifier} called by "
              f"shortname {carrier_data.carrier_short_name} with channel #{carrier_data.discord_channel} called from "
              f"find_carrier_from_short_name.")

    return carriers


# function to search for a carrier by p_ID
def find_carrier_from_pid(db_id):
    carrier_db.execute(f"SELECT * FROM carriers WHERE p_ID = {db_id}")
    carrier_data = CarrierData(carrier_db.fetchone())
    print(f"FC {carrier_data.pid} is {carrier_data.carrier_long_name} {carrier_data.carrier_identifier} called by "
          f"shortname {carrier_data.carrier_short_name} with channel #{carrier_data.discord_channel} called "
          f"from find_carrier_from_pid.")
    return carrier_data


# function to search for a commodity by name or partial name
async def find_commodity(commodity_search_term, ctx):
    # TODO: Where do we get set up this database? it is searching for things, but what is the source of the data, do
    #  we update it periodically?

    commodity, is_error = False, False
    print(f'Searching for commodity against match "{commodity_search_term}" requested by {ctx.author}')

    carrier_db.execute(
        f"SELECT * FROM commodities WHERE commodity LIKE (?)",
        (f'%{commodity_search_term}%',))

    commodities = [Commodity(commodity) for commodity in carrier_db.fetchall()]
    commodity = None
    if not commodities:
        print('No commodities found for request')
        await ctx.send(f"No commodities found for {commodity_search_term}")
        is_error = True
        # Did not find anything, short-circuit out of the next block
        return commodity, is_error
    elif len(commodities) == 1:
        print('Single commodity found, returning that directly')
        # if only 1 match, just assign it directly
        commodity = commodities[0]
    elif len(commodities) > 3:
        # If we ever get into a scenario where more than 3 commodities can be found with the same search directly, then
        # we need to revisit this limit
        is_error = True
        print(f'More than 3 commodities found for: "{commodity_search_term}", {ctx.author} needs to search better.')
        await ctx.send(f'Please narrow down your commodity search, we found {len(commodities)} matches for your '
                       f'input choice: "{commodity_search_term}"')
        return commodity, is_error  # Just return None here and let the calling method figure out what is needed to happen
    else:
        print(f'Between 1 and 3 commodities found for: "{commodity_search_term}", asking {ctx.author} which they want.')
        # The database runs a partial match, in the case we have more than 1 ask the user which they want.
        # here we have less than 3, but more than 1 match
        embed = discord.Embed(title=f"Multiple commodities found for input: {commodity_search_term}", color=constants.EMBED_COLOUR_OK)

        count = 0
        response = None  # just in case we try to do something before it is assigned, give it a value of None
        for commodity in commodities:
            count += 1
            embed.add_field(name=f'{count}', value=f"{commodity.name}", inline=True)

        embed.set_footer(text='Please select the commodity with 1, 2 or 3')

        def check(message):
            return message.author == ctx.author and message.channel == ctx.channel and \
                   len(message.content) == 1 and message.content.lower() in ["1", "2", "3"]

        message_confirm = await ctx.send(embed=embed)
        try:
            # Wait on the user input, this might be better by using a reaction?
            response = await bot.wait_for("message", check=check, timeout=15)
            print(f'{ctx.author} responded with: "{response.content}", type: {type(response.content)}.')
            index = int(response.content) - 1  # Users count from 1, computers count from 0
            commodity = commodities[index]
        except asyncio.TimeoutError:
            await ctx.send("Commodity selection timed out. Cancelling.")
            print('User failed to respond in time')
            is_error = True
            pass
        await message_confirm.delete()
        if response:
            await response.delete()
    if commodity:
        print(f"Commodity {commodity.name} avgsell {commodity.average_sell} avgbuy {commodity.average_buy} "
              f"maxsell {commodity.max_sell} minbuy {commodity.min_buy} maxprofit {commodity.max_profit}")
    return commodity, is_error

#
#                       IMAGE GEN STUFF
#


# defining fonts for pillow use
reg_font = ImageFont.truetype('font/Exo/static/Exo-Light.ttf', 16)
name_font = ImageFont.truetype('font/Exo/static/Exo-ExtraBold.ttf', 34)
title_font = ImageFont.truetype('font/Exo/static/Exo-ExtraBold.ttf', 26)
normal_font = ImageFont.truetype('font/Exo/static/Exo-Medium.ttf', 18)
field_font = ImageFont.truetype('font/Exo/static/Exo-Light.ttf', 18)


# get date and time
def get_formatted_date_string():
    """
    Returns a tuple of the Elite Dangerous Time and the current real world time.

    :rtype: tuple
    """
    dt_now = datetime.now(tz=timezone.utc)
    # elite_time_string is the Elite Dangerous time this is running in, today plus 1286 years
    elite_time_string = (dt_now + relativedelta(years=1286)).strftime("%d %B %Y %H:%M %Z")
    current_time_string = dt_now.strftime("%Y%m%d %H%M%S")
    return elite_time_string, current_time_string


# function to create image for loading
def create_carrier_mission_image(carrier_data, commodity, system, station, profit, pads, demand, mission_type):
    """
    Builds the carrier image and returns the relative path
    """
    my_image = Image.open(f"images/{carrier_data.carrier_short_name}.png")
    image_editable = ImageDraw.Draw(my_image)
    mission_action = 'LOADING' if mission_type == 'load' else 'UNLOADING'
    image_editable.text((27, 150), "PILOTS TRADE NETWORK", (255, 255, 255), font=title_font)
    image_editable.text((27, 180), f"CARRIER {mission_action} MISSION", (191, 53, 57), font=title_font)
    image_editable.text((27, 235), "FLEET CARRIER " + carrier_data.carrier_identifier, (0, 217, 255), font=reg_font)
    image_editable.text((27, 250), carrier_data.carrier_long_name, (0, 217, 255), font=name_font)
    image_editable.text((27, 320), "COMMODITY:", (255, 255, 255), font=field_font)
    image_editable.text((150, 320), commodity.name.upper(), (255, 255, 255), font=normal_font)
    image_editable.text((27, 360), "SYSTEM:", (255, 255, 255), font=field_font)
    image_editable.text((150, 360), system.upper(), (255, 255, 255), font=normal_font)
    image_editable.text((27, 400), "STATION:", (255, 255, 255), font=field_font)
    image_editable.text((150, 400), f"{station.upper()} ({pads.upper()} pads)", (255, 255, 255), font=normal_font)
    image_editable.text((27, 440), "PROFIT:", (255, 255, 255), font=field_font)
    image_editable.text((150, 440), f"{profit}k per unit, {demand} units", (255, 255, 255), font=normal_font)

    # Check if this will work fine, we might need to delete=False and clean it ourselves
    result_name = tempfile.NamedTemporaryFile(suffix='.png', delete=False)
    print(f'Saving temporary mission file for carrier: {carrier_data.carrier_long_name} to: {result_name.name}')
    my_image.save(result_name.name)
    return result_name.name


#
#                       TEXT GEN FUNCTIONS
#

def txt_create_discord(carrier_data, mission_type, commodity, station, system, profit, pads, demand, eta_text, mission_temp_channel_id):
    discord_text = f"<#{mission_temp_channel_id}> {'load' if mission_type == 'load' else 'unload'}ing " \
                   f"{commodity.name} " \
                   f"{'from' if mission_type == 'load' else 'to'} **{station.upper()}** station in system " \
                   f"**{system.upper()}** : {profit}k per unit profit : "\
                   f"{demand} {'demand' if mission_type == 'load' else 'supply'} : {pads.upper()}-pads" \
                   f".{eta_text}"
    return discord_text


def txt_create_reddit_title(carrier_data):
    reddit_title = f"P.T.N. News - Trade mission - {carrier_data.carrier_long_name} {carrier_data.carrier_identifier}" \
                   f" - {get_formatted_date_string()[0]}"
    return reddit_title


def txt_create_reddit_body(carrier_data, mission_type, commodity, station, system, profit, pads, demand, eta_text):

    if mission_type == 'load':
        reddit_body = (
            f"    INCOMING WIDEBAND TRANSMISSION: P.T.N. CARRIER LOADING MISSION IN PROGRESS\n\n**BUY FROM**: station "
            f"**{station.upper()}** ({pads.upper()}-pads) in system **{system.upper()}**\n\n**COMMODITY**: "
            f"{commodity.name}\n\n&#x200B;\n\n**SELL TO**: Fleet Carrier **{carrier_data.carrier_long_name} "
            f"{carrier_data.carrier_identifier}{eta_text}**\n\n**PROFIT**: {profit}k/unit : {demand} "
            f"demand\n\n\n\n[Join us on Discord]({constants.REDDIT_DISCORD_LINK_URL}) for "
            f"mission updates and discussion, channel **#{carrier_data.discord_channel}**.")
    else:
        reddit_body = (
            f"    INCOMING WIDEBAND TRANSMISSION: P.T.N. CARRIER UNLOADING MISSION IN PROGRESS\n\n**BUY FROM**: Fleet "
            f"Carrier **{carrier_data.carrier_long_name} {carrier_data.carrier_identifier}{eta_text}**"
            f"\n\n**COMMODITY**: {commodity.name}\n\n&#x200B;\n\n**SELL TO**: station "
            f"**{station.upper()}** ({pads.upper()}-pads) in system **{system.upper()}**\n\n**PROFIT**: {profit}k/unit "
            f": {demand} supply\n\n\n\n[Join us on Discord]({constants.REDDIT_DISCORD_LINK_URL}) for mission updates"
            f" and discussion, channel **#{carrier_data.discord_channel}**.")
    return reddit_body

#
#                       OTHER
#


# function to stop and quit
def user_exit():
    sys.exit("User requested exit.")


#
#                       BOT STUFF STARTS HERE
#

bot = commands.Bot(command_prefix='m.', intents=discord.Intents.all())
slash = SlashCommand(bot, sync_commands=True)

@bot.event
async def on_ready():
    print(f'{bot.user.name} has connected to Discord!')


#
#                       LOAD/UNLOAD COMMANDS
#

# load commands
@bot.command(name='load', help='Generate details for a loading mission and optionally broadcast to Discord.\n'
                               '\n'
                               'carrier_name_search_term should be a unique part of your carrier\'s name. (Use quotes if spaces are required)\n'
                               'commodity_name_partial should be a unique part of any commodity\'s name.\n'
                               'System and Station names should be enclosed in quotes if they contain spaces.\n'
                               'Profit should be expressed as a simple number e.g. enter 10 for 10k/unit profit.\n'
                               'Pad size should be expressed as L or M.\n'
                               'Demand should be expressed as an absolute number e.g. 20k, 20,000, etc.\n'
                               'ETA is optional and should be expressed as a number of minutes e.g. 15.\n'
                               'Case is automatically corrected for all inputs.')
@commands.has_role('Certified Carrier')
async def load(ctx, carrier_name_search_term, commodity_search_term, system, station, profit, pads, demand, eta=None):
    rp = False
    mission_type = 'load'
    await gen_mission(ctx, carrier_name_search_term, commodity_search_term, system, station, profit, pads, demand, rp, mission_type,
                      eta)


@bot.command(name="loadrp", help='Same as load command but prompts user to enter roleplay text\n'
                                 'This is added to the Reddit comment as as a quote above the mission details\n'
                                 'and sent to the carrier\'s Discord channel in quote format if those options are '
                                 'chosen')
@commands.has_role('Certified Carrier')
async def loadrp(ctx, carrier_name_search_term, commodity_search_term, system, station, profit, pads, demand, eta=None):
    rp = True
    mission_type = 'load'
    await gen_mission(ctx, carrier_name_search_term, commodity_search_term, system, station, profit, pads, demand, rp, mission_type,
                      eta)


# unload commands
@bot.command(name='unload', help='Generate details for an unloading mission.\n'
                                 '\n'
                                 'carrier_name_search_term should be a unique part of your carrier\'s name. (Use quotes if spaces are required)\n'
                                 'commodity_name_partial should be a unique part of any commodity\'s name.\n'
                                 'System and Station names should be enclosed in quotes if they contain spaces.\n'
                                 'Profit should be expressed as a simple number e.g. enter 10 for 10k/unit profit.\n'
                                 'Pad size should be expressed as L or M.\n'
                                 'Supply should be expressed as an absolute number e.g. 20k, 20,000, etc.\n'
                                 'ETA is optional and should be expressed as a number of minutes e.g. 15.\n'
                                 'Case is automatically corrected for all inputs.')
@commands.has_role('Certified Carrier')
async def unload(ctx, carrier_name_search_term, commodity_search_term, system, station, profit, pads, supply, eta=None):
    rp = False
    mission_type = 'unload'
    await gen_mission(ctx, carrier_name_search_term, commodity_search_term, system, station, profit, pads, supply, rp, mission_type,
                      eta)


@bot.command(name="unloadrp", help='Same as unload command but prompts user to enter roleplay text\n'
                                   'This is added to the Reddit comment as as a quote above the mission details\n'
                                   'and sent to the carrier\'s Discord channel in quote format if those options are '
                                   'chosen')
@commands.has_role('Certified Carrier')
async def unloadrp(ctx, carrier_name_search_term, commodity_search_term, system, station, profit, pads, demand, eta=None):
    rp = True
    mission_type = 'unload'
    await gen_mission(ctx, carrier_name_search_term, commodity_search_term, system, station, profit, pads, demand, rp, mission_type,
                      eta)


# mission generator called by loading/unloading commands
async def gen_mission(ctx, carrier_name_search_term, commodity_search_term, system, station, profit, pads, demand, rp, mission_type,
                      eta):
    # Check we are in the designated mission channel, if not go no farther.
    mission_gen_channel = bot.get_channel(conf['MISSION_CHANNEL'])
    current_channel = ctx.channel

    print(f'Mission generation type: {mission_type} with RP: {rp}, requested by {ctx.author}. Request triggered from '
          f'channel {current_channel}.')

    if current_channel != mission_gen_channel:
        # problem, wrong channel, no progress
        return await ctx.send(f'Sorry, you can only run this command out of: {mission_gen_channel}.')
    if pads.upper() not in ['M', 'L']:
        # In case a user provides some junk for pads size, gate it
        print(f'Exiting mission generation requested by {ctx.author} as pad size is invalid, provided: {pads}')
        return await ctx.send(f'Sorry, your pad size is not L or M. Provided: {pads}. Mission generation cancelled.')

    # check if commodity can be found, exit gracefully if not
    commreturn = await find_commodity(commodity_search_term, ctx)
    (commodity_data, is_error) = commreturn
    if is_error:
        return # we've already given the user feedback on why there's a problem, we just want to quit gracefully now
    if not commodity_data:
        raise ValueError('Missing commodity data')

    # check if the carrier can be found, exit gracefully if not
    carrier_data = find_carrier_from_long_name(carrier_name_search_term)
    if not carrier_data:
        return await ctx.send(f"No carrier found for {carrier_name_search_term}. You can use `/find` or `/owner` to search for carrier names.")

    print("Waiting for channel lock...")
    await carrier_channel_lock.acquire()
    print("Channel lock acquired")

    # TODO: This method is way too long, break it up into logical steps.

    try: # this try/except pair is to try and ensure the channel lock is released if something breaks during mission gen
         # otherwise the bot freezes next time the lock is attempted
        
        # None-strings, should hopefully not break the database. If it does revert these to 'NULL'
        rp_text = None
        reddit_post_id = None
        reddit_post_url = None
        reddit_comment_id = None
        reddit_comment_url = None
        discord_alert_id = None

        eta_text = f" (ETA {eta} minutes)" if eta else ""

        embed = discord.Embed(title="Generating and fetching mission alerts...", color=constants.EMBED_COLOUR_QU)
        message_gen = await ctx.send(embed=embed)

        mission_db.execute(f'''SELECT * FROM missions WHERE carrier LIKE (?)''', ('%' + carrier_name_search_term + '%',))
        mission_data = MissionData(mission_db.fetchone())
        if mission_data:
            embed = discord.Embed(title="Error",
                                description=f"{mission_data.carrier_name} is already on a mission, please "
                                            f"use **m.done** to mark it complete before starting a new mission.",
                                color=constants.EMBED_COLOUR_ERROR)
            await ctx.send(embed=embed)
            return  # We want to stop here, so go exit out

        def check_confirm(message):
            # use all to verify that all the characters in the message content are present in the allowed list (dtrx).
            # Anything outwith this grouping will cause all to fail. Use set to throw away any duplicate objects.
            # not sure if the msg.content can ever be None, but lets gate it anyway
            return message.content and message.author == ctx.author and message.channel == ctx.channel and \
                all(character in 'drtnx' for character in set(message.content.lower()))

        def check_rp(message):
            return message.author == ctx.author and message.channel == ctx.channel

        mission_temp_channel_id = await create_mission_temp_channel(ctx, carrier_data.discord_channel, carrier_data.ownerid)

        if rp:
            embed = discord.Embed(title="Input roleplay text",
                                description="Roleplay text is sent in quote style like this:\n\n> This is a quote!"
                                            "\n\nYou can use all regular Markdown formatting. If the 'send to Discord' "
                                            "option is chosen, your quote will be broadcast to your carrier's channel "
                                            "following its mission image. If the 'send to Reddit' option is chosen, "
                                            "the quote is inserted above the mission details in the top-level comment.",
                                color=constants.EMBED_COLOUR_RP)
            message_rp = await ctx.send(embed=embed)

            try:

                message_rp_text = await bot.wait_for("message", check=check_rp, timeout=120)
                rp_text = message_rp_text.content

            except asyncio.TimeoutError:
                await ctx.send("**Mission generation cancelled (waiting too long for user input)**")
                try:
                    carrier_channel_lock.release()
                    print("Channel lock released")
                finally:
                    await remove_carrier_channel(mission_temp_channel_id, seconds_short)
                await message_rp.delete()
                return

        # generate the mission elements

        file_name = create_carrier_mission_image(carrier_data, commodity_data, system, station, profit, pads, demand,
                                                mission_type)
        discord_text = txt_create_discord(carrier_data, mission_type, commodity_data, station, system, profit, pads,
                                        demand, eta_text, mission_temp_channel_id)
        print("Generated discord elements")
        reddit_title = txt_create_reddit_title(carrier_data)
        reddit_body = txt_create_reddit_body(carrier_data, mission_type, commodity_data, station, system, profit, pads,
                                            demand, eta_text)
        print("Generated Reddit elements")

        # check they're happy with output and offer to send
        embed = discord.Embed(title=f"Mission pending for {carrier_data.carrier_long_name}{eta_text}",
                            color=constants.EMBED_COLOUR_OK)
        embed.add_field(name="Mission type", value=f"{mission_type.title()}ing", inline=True)
        embed.add_field(name="Commodity", value=f"{demand} of {commodity_data.name.title()} at {profit}k/unit", inline=True)
        embed.add_field(name="Location",
                        value=f"{station.upper()} station ({pads.upper()}-pads) in system {system.upper()}", inline=True)
        if rp:
            await message_rp.delete()
            await message_rp_text.delete()
            embed.add_field(name="Roleplay text", value=rp_text, inline=False)
        message_pending = await ctx.send(embed=embed)
        await message_gen.delete()
        print("Output check displayed")

        embed = discord.Embed(title="Where would you like to send the alert?",
                            description="(**d**)iscord, (**r**)eddit, (**t**)ext for copy/pasting or (**x**) to cancel\n"
                            "Use (**n**) to also notify PTN Haulers.",
                            color=constants.EMBED_COLOUR_QU)
        embed.set_footer(text="Enter all that apply, e.g. **drn** will send alerts to Discord and Reddit and notify PTN Haulers.")
        message_confirm = await ctx.send(embed=embed)
        print("Prompted user for alert destination")

        try:
            msg = await bot.wait_for("message", check=check_confirm, timeout=30)

            if "x" in msg.content.lower():
                # immediately stop if there's an x anywhere in the message, even if there are other proper inputs
                message_cancelled = await ctx.send("**Mission creation cancelled.**")
                # remove the channel we just created
                try:
                    carrier_channel_lock.release()
                    print("Channel lock released")
                finally:
                    await remove_carrier_channel(mission_temp_channel_id, seconds_short)
                await msg.delete()
                await message_confirm.delete()
                print("User cancelled mission generation")
                return

            if "t" in msg.content.lower():
                print("User used option t")
                embed = discord.Embed(title="Trade Alert (Discord)", description=f"`{discord_text}`",
                                    color=constants.EMBED_COLOUR_DISCORD)
                await ctx.send(embed=embed)
                if rp:
                    embed = discord.Embed(title="Roleplay Text (Discord)", description=f"`> {rp_text}`",
                                        color=constants.EMBED_COLOUR_DISCORD)
                    await ctx.send(embed=embed)

                embed = discord.Embed(title="Reddit Post Title", description=f"`{reddit_title}`",
                                    color=constants.EMBED_COLOUR_REDDIT)
                await ctx.send(embed=embed)
                if rp:
                    embed = discord.Embed(title="Reddit Post Body - PASTE INTO MARKDOWN MODE",
                                        description=f"```> {rp_text}\n\n{reddit_body}```",
                                        color=constants.EMBED_COLOUR_REDDIT)
                else:
                    embed = discord.Embed(title="Reddit Post Body - PASTE INTO MARKDOWN MODE",
                                        description=f"```{reddit_body}```", color=constants.EMBED_COLOUR_REDDIT)
                embed.set_footer(text="**REMEMBER TO USE MARKDOWN MODE WHEN PASTING TEXT TO REDDIT.**")
                await ctx.send(embed=embed)
                await ctx.send(file=discord.File(file_name))

                embed = discord.Embed(title=f"Alert Generation Complete for {carrier_data.carrier_long_name}",
                                    description="Paste Reddit content into **MARKDOWN MODE** in the editor. You can swap "
                                                "back to Fancy Pants afterwards and make any changes/additions or embed "
                                                "the image.\n\nBest practice for Reddit is an image post with a top level"
                                                " comment that contains the text version of the advert. This ensures the "
                                                "image displays with highest possible compatibility across platforms and "
                                                "apps. When mission complete, flag the post as *Spoiler* to prevent "
                                                "image showing and add a comment to inform.",
                                    color=constants.EMBED_COLOUR_OK)
                await ctx.send(embed=embed)

            if "d" in msg.content.lower():
                print("User used option d")
                message_send = await ctx.send("**Sending to Discord...**")

                # send trade alert to trade alerts channel, or to wine alerts channel if loading wine
                if commodity_data.name.title() == "Wine":
                    channel = bot.get_channel(wine_alerts_id)
                    channelId = wine_alerts_id
                else:
                    channel = bot.get_channel(trade_alerts_id)
                    channelId = trade_alerts_id
                    
                if mission_type == 'load':
                    embed = discord.Embed(description=discord_text, color=constants.EMBED_COLOUR_LOADING)
                else:
                    embed = discord.Embed(description=discord_text, color=constants.EMBED_COLOUR_UNLOADING)

                trade_alert_msg = await channel.send(embed=embed)
                discord_alert_id = trade_alert_msg.id

                channel = bot.get_channel(mission_temp_channel_id)

                discord_file = discord.File(file_name, filename="image.png")

                embed_colour = constants.EMBED_COLOUR_LOADING if mission_type == 'load' \
                    else constants.EMBED_COLOUR_UNLOADING
                embed = discord.Embed(title="P.T.N TRADE MISSION STARTING",
                                    description=f"> {rp_text}" if rp else "", color=embed_colour)

                embed.add_field(name="Destination", value=f"Station: {station.upper()}\nSystem: {system.upper()}", inline=True)
                if eta:
                    embed.add_field(name="ETA", value=f"{eta} minutes", inline=True)
            
                embed.set_image(url="attachment://image.png")
                embed.set_footer(
                    text="m.complete will mark this mission complete\n/mission will show this mission info\n/missions "
                        "will show all current trade missions")
                await channel.send(file=discord_file, embed=embed)
                embed = discord.Embed(title=f"Discord trade alerts sent for {carrier_data.carrier_long_name}",
                                    description=f"Check <#{channelId}> for trade alert and "
                                                f"<#{mission_temp_channel_id}> for image.",
                                    color=constants.EMBED_COLOUR_DISCORD)
                await ctx.send(embed=embed)
                await message_send.delete()

            if "r" in msg.content.lower():
                print("User used option r")
                # profit is a float, not an int.
                if float(profit) < 10:
                    print(f'Not posting the mission from {ctx.author} to reddit due to low profit margin <10k/t.')
                    await ctx.send(f'Skipped Reddit posting due to profit margin of {profit}k/t being below the PTN 10k/t '
                                f'minimum. (Did you try to post a Wine load?)')
                else:
                    message_send = await ctx.send("**Sending to Reddit...**")

                    # post to reddit
                    subreddit = await reddit.subreddit(to_subreddit)
                    submission = await subreddit.submit_image(reddit_title, image_path=file_name,
                                                            flair_id=flair_mission_start)
                    reddit_post_url = submission.permalink
                    reddit_post_id = submission.id
                    if rp:
                        comment = await submission.reply(f"> {rp_text}\n\n&#x200B;\n\n{reddit_body}")
                    else:
                        comment = await submission.reply(reddit_body)
                    reddit_comment_url = comment.permalink
                    reddit_comment_id = comment.id
                    embed = discord.Embed(title=f"Reddit trade alert sent for {carrier_data.carrier_long_name}",
                                        description=f"https://www.reddit.com{reddit_post_url}",
                                        color=constants.EMBED_COLOUR_REDDIT)
                    await ctx.send(embed=embed)
                    await message_send.delete()
                    embed = discord.Embed(title=f"{carrier_data.carrier_long_name} REQUIRES YOUR UPDOOTS",
                                        description=f"https://www.reddit.com{reddit_post_url}",
                                        color=constants.EMBED_COLOUR_REDDIT)
                    channel = bot.get_channel(conf['CHANNEL_UPVOTES'])
                    upvote_message = await channel.send(embed=embed)
                    emoji = bot.get_emoji(upvote_emoji)
                    await upvote_message.add_reaction(emoji)

            if "n" in msg.content.lower():
                print("User used option n")

                # get carrier's channel object

                channel = bot.get_channel(mission_temp_channel_id)

                await channel.send(f"<@&{hauler_role_id}>: {discord_text}")

                embed = discord.Embed(title=f"Mission notification sent for {carrier_data.carrier_long_name}",
                            description=f"Pinged <@&{hauler_role_id}> in <#{mission_temp_channel_id}>",
                            color=constants.EMBED_COLOUR_DISCORD)
                await ctx.send(embed=embed)
        except asyncio.TimeoutError:
            await ctx.send("**Mission not generated or broadcast (no valid response from user).**")
            try:
                carrier_channel_lock.release()
                print("Channel lock released")
            finally:
                await remove_carrier_channel(mission_temp_channel_id, seconds_short)
            return

        print("All options worked through, now clean up")

        # now clear up by deleting the prompt message and user response
        await msg.delete()
        await message_confirm.delete()
        await mission_add(ctx, carrier_data, commodity_data, mission_type, system, station, profit, pads, demand,
                        rp_text, reddit_post_id, reddit_post_url, reddit_comment_id, reddit_comment_url, discord_alert_id, mission_temp_channel_id)
        await mission_generation_complete(ctx, carrier_data, message_pending, eta_text)
        cleanup_temp_image_file(file_name)
        print("Reached end of mission generator")
        return
    except Exception as e:
        await ctx.send("Oh no! Something went wrong :( Mission generation aborted.")
        await ctx.send(e)
        print("Something went wrong with mission generation :(")
        print(e)
        carrier_channel_lock.release()
        await remove_carrier_channel(mission_temp_channel_id, seconds_short)




async def create_mission_temp_channel(ctx, discord_channel, owner_id):
    # create the carrier's channel for the mission

    # first check whether channel already exists

    mission_temp_channel = discord.utils.get(ctx.guild.channels, name=discord_channel)

    if mission_temp_channel:
        # channel exists, so reuse it
        mission_temp_channel_id = mission_temp_channel.id
        await ctx.send(f"Found existing mission channel <#{mission_temp_channel_id}>.")
        print(f"Found existing {mission_temp_channel}")
    else:
        # channel does not exist, create it
        category = discord.utils.get(ctx.guild.categories, id=trade_cat_id)
        mission_temp_channel = await ctx.guild.create_text_channel(discord_channel, category=category)
        mission_temp_channel_id = mission_temp_channel.id
        print(f"Created {mission_temp_channel}")

    print(f'Channels: {ctx.guild.channels}')

    if not mission_temp_channel:
        raise EnvironmentError(f'Could not create carrier channel {discord_channel}')

    # find carrier owner as a user object

    try:
        owner = await bot.fetch_user(owner_id)
        print(f"Owner identified as {owner.display_name}")
    except:
        raise EnvironmentError(f'Could not find Discord user matching ID {owner_id}')

    # add owner to channel permissions

    try:
        await mission_temp_channel.set_permissions(owner, read_messages=True,
                                            manage_channels=True,
                                            manage_roles=True,
                                            manage_webhooks=True,
                                            create_instant_invite=True,
                                            send_messages=True,
                                            embed_links=True,
                                            attach_files=True,
                                            add_reactions=True,
                                            external_emojis=True,
                                            manage_messages=True,
                                            read_message_history=True,
                                            use_slash_commands=True)
        print(f"Set permissions for {owner} in {mission_temp_channel}")
    except Forbidden:
        raise EnvironmentError(f"Could not set channel permissions for {owner.display_name} in {mission_temp_channel}, reason: Bot does not have permissions to edit channel specific permissions.")
    except NotFound:
        raise EnvironmentError(f"Could not set channel permissions for {owner.display_name} in {mission_temp_channel}, reason: The role or member being edited is not part of the guild.")
    except HTTPException:
        raise EnvironmentError(f"Could not set channel permissions for {owner.display_name} in {mission_temp_channel}, reason: Editing channel specific permissions failed.")
    except InvalidArgument:
        raise EnvironmentError(f"Could not set channel permissions for {owner.display_name} in {mission_temp_channel}, reason: The overwrite parameter invalid or the target type was not Role or Member.")
    except:
        raise EnvironmentError(f'Could not set channel permissions for {owner.display_name} in {mission_temp_channel}')

    # send the channel back to the mission generator as a channel id

    return mission_temp_channel_id


def cleanup_temp_image_file(file_name):
    """
    Takes an input file path and removes it.

    :param str file_name: The file path
    :returns: None
    """
    # Now we delete the temp file, clean up after ourselves!
    try:
        print(f'Deleting the carriers temp file at: {file_name}')
        os.remove(file_name)
    except Exception as e:
        print(f'There was a problem removing the carrier image file located {file_name}')
        print(e)


#
#                       MISSION DB
#
# add mission to DB, called from mission generator
async def mission_add(ctx, carrier_data, commodity_data, mission_type, system, station, profit, pads, demand,
                      rp_text, reddit_post_id, reddit_post_url, reddit_comment_id, reddit_comment_url, discord_alert_id, mission_temp_channel_id):
    backup_database('missions')  # backup the missions database before going any further

    print("Called mission_add to write to database")
    mission_db.execute(''' INSERT INTO missions VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?) ''', (
        carrier_data.carrier_long_name, carrier_data.carrier_identifier, mission_temp_channel_id,
        commodity_data.name.title(), mission_type.lower(), system.title(), station.title(), profit, pads.upper(),
        demand, rp_text, reddit_post_id, reddit_post_url, reddit_comment_id, reddit_comment_url, discord_alert_id
    ))
    missions_conn.commit()
    print("Mission added to db")

    # now we can release the channel lock
    carrier_channel_lock.release()
    print("Channel lock released")
    return

async def mission_generation_complete(ctx, carrier_data, message_pending, eta_text):

    # fetch data we just committed back

    mission_db.execute('''SELECT * FROM missions WHERE carrier LIKE (?)''',
                        ('%' + carrier_data.carrier_long_name + '%',))
    print('DB command ran, go fetch the result')
    mission_data = MissionData(mission_db.fetchone())
    print(f'Found mission data: {mission_data}')

    # return result to user

    embed_colour = constants.EMBED_COLOUR_LOADING if mission_data.mission_type == 'load' else \
        constants.EMBED_COLOUR_UNLOADING

    mission_description = ''
    if mission_data.rp_text and mission_data.rp_text != 'NULL':
        mission_description = f"> {mission_data.rp_text}"

    embed = discord.Embed(title=f"{mission_data.mission_type.upper()}ING {mission_data.carrier_name} ({mission_data.carrier_identifier}) {eta_text}",
                            description=mission_description, color=embed_colour)

    embed = _mission_summary_embed(mission_data, embed)

    embed.set_footer(text="You can use m.done <carrier> to mark the mission complete.")

    await ctx.send(embed=embed)
    await message_pending.delete()
    print("Mission generation complete")
    return


# list active carrier trade mission from DB
@bot.command(name='ission', help="Show carrier's active trade mission.")
async def ission(ctx):
    # take a note channel ID
    msg_ctx_name = ctx.channel.name
    # look for a match for the channel name in the carrier DB
    # TODO: this should be a separate function to search by carrier channel name
    carrier_db.execute(f"SELECT * FROM carriers WHERE "
                       f"discordchannel = {msg_ctx_name}")
    carrier_data = CarrierData(carrier_db.fetchone())
    print(f'Mission command carrier_data: {carrier_data}')
    if not carrier_data.discord_channel:
        # if there's no channel match, return an error
        embed = discord.Embed(description="Try again in the carrier's mission channel.", color=constants.EMBED_COLOUR_QU)
        await ctx.send(embed=embed)
        return
    else:
        print(f'Searching if carrier ({carrier_data.carrier_long_name}) has active mission.')
        # now look to see if the carrier is on an active mission
        mission_db.execute('''SELECT * FROM missions WHERE carrier LIKE (?)''',
                           ('%' + carrier_data.carrier_long_name + '%',))
        print('DB command ran, go fetch the result')
        mission_data = MissionData(mission_db.fetchone())
        print(f'Found mission data: {mission_data}')

        if not mission_data:
            # if there's no result, return an error
            embed = discord.Embed(description=f"**{carrier_data.carrier_long_name}** doesn't seem to be on a trade"
                                              f" mission right now.",
                                  color=constants.EMBED_COLOUR_OK)
            await ctx.send(embed=embed)
        else:
            # user is in correct channel and carrier is on a mission, so show the current trade mission for selected
            # carrier
            embed_colour = constants.EMBED_COLOUR_LOADING if mission_data.mission_type == 'load' else \
                constants.EMBED_COLOUR_UNLOADING

            mission_description = ''
            if mission_data.rp_text and mission_data.rp_text != 'NULL':
                mission_description = f"> {mission_data.rp_text}"

            embed = discord.Embed(title=f"{mission_data.mission_type.upper()}ING {mission_data.carrier_name} ({mission_data.carrier_identifier})",
                                  description=mission_description, color=embed_colour)

            embed = _mission_summary_embed(mission_data, embed)

            embed.set_footer(text="You can use m.complete if the mission is complete.")

            await ctx.send(embed=embed)
            return

def _mission_summary_embed(mission_data, embed):
    embed.add_field(name="System", value=f"{mission_data.system.upper()}", inline=True)
    embed.add_field(name="Station", value=f"{mission_data.station.upper()} ({mission_data.pad_size}-pads)",
                    inline=True)
    embed.add_field(name="Commodity", value=f"{mission_data.commodity.upper()}", inline=True)
    embed.add_field(name="Quantity and profit",
                    value=f"{mission_data.demand} units at {mission_data.profit}k profit per unit", inline=True)
    return embed


# find what fleet carriers are owned by a user - private slash command
@slash.slash(name="owner", guild_ids=[bot_guild_id],
             description="Private command: Use with @User to find out what fleet carriers that user owns.")
async def _owner(ctx: SlashContext, at_owner_discord):

    # strip off the guff and get us a pure owner ID
    stripped_owner = at_owner_discord.replace('<', '').replace('>', '').replace('!', '').replace('@', '')

    print(f"{ctx.author} used /owner in {ctx.channel} to find carriers owned by user with ID {stripped_owner}")

    try:
        owner = await bot.fetch_user(stripped_owner)
        print(f"Found user as {owner.display_name}")
    except HTTPException:
        await ctx.send("Couldn't find any users by that name.", hidden=True)
        raise EnvironmentError(f'Could not find Discord user matching ID {at_owner_discord} ({stripped_owner})')

    try:
        # look for matches for the owner ID in the carrier DB
        carrier_list = find_carrier_with_owner_id(stripped_owner)

        if not carrier_list:
            await ctx.send(f"No carriers found owned by <@{stripped_owner}>", hidden=True) 
            return print(f"No carriers found for owner {owner.id}")

        embed = discord.Embed(description=f"Showing registered Fleet Carriers owned by <@{stripped_owner}>:",
                              color=constants.EMBED_COLOUR_OK)
      
        for carrier_data in carrier_list:
            embed.add_field(name=f"{carrier_data.carrier_long_name} ({carrier_data.carrier_identifier})",
                            value=f"Channel Name: #{carrier_data.discord_channel}",
                            inline=False)

        await ctx.send(embed=embed, hidden=True)

    except TypeError as e:
        print('Error: {}'.format(e))


# mission slash command - private, non spammy
@slash.slash(name="mission", guild_ids=[bot_guild_id],
             description="Private command: Use in a Fleet Carrier's channel to display its current mission.")
async def _mission(ctx: SlashContext):

    print(f"{ctx.author} asked for active mission in <#{ctx.channel.id}> (used /mission)")

    # take a note channel name
    msg_ctx_name = ctx.channel.name

    # look for a match for the channel name in the carrier DB
    # TODO: This should be a separate function to search by carrier channel name
    carrier_db.execute(f"SELECT * FROM carriers WHERE "
                       f"discordchannel = '{msg_ctx_name}' ;")
    carrier_data = CarrierData(carrier_db.fetchone())
    print(f'Mission command carrier_data: {carrier_data}')
    if not carrier_data.discord_channel:
        # if there's no channel match, return an error
        embed = discord.Embed(description="Try again in a **🚛Trade Carriers** channel.", color=constants.EMBED_COLOUR_QU)
        await ctx.send(embed=embed, hidden=True)
        return
    else:
        print(f'Searching if carrier ({carrier_data.carrier_long_name}) has active mission.')
        # now look to see if the carrier is on an active mission
        mission_db.execute('''SELECT * FROM missions WHERE carrier LIKE (?)''',
                           ('%' + carrier_data.carrier_long_name + '%',))
        print('DB command ran, go fetch the result')
        mission_data = MissionData(mission_db.fetchone())
        print(f'Found mission data: {mission_data}')

        if not mission_data:
            # if there's no result, return an error
            embed = discord.Embed(description=f"**{carrier_data.carrier_long_name}** doesn't seem to be on a trade"
                                              f" mission right now.",
                                  color=constants.EMBED_COLOUR_OK)
            await ctx.send(embed=embed, hidden=True)
        else:
            # user is in correct channel and carrier is on a mission, so show the current trade mission for selected
            # carrier
            embed_colour = constants.EMBED_COLOUR_LOADING if mission_data.mission_type == 'load' else \
                constants.EMBED_COLOUR_UNLOADING

            mission_description = ''
            if mission_data.rp_text and mission_data.rp_text != 'NULL':
                mission_description = f"> {mission_data.rp_text}"

            embed = discord.Embed(title=f"{mission_data.mission_type.upper()}ING {mission_data.carrier_name} ({mission_data.carrier_identifier})",
                                  description=mission_description, color=embed_colour)

            embed = _mission_summary_embed(mission_data, embed)

            embed.set_footer(text="You can use m.complete if the mission is complete.")

            await ctx.send(embed=embed, hidden=True)
            return


# list all active carrier trade missions from DB
@bot.command(name='issions', help='List all active trade missions.')
async def issions(ctx):

    print(f'User {ctx.author} asked for all active missions.')

    co_role = discord.utils.get(ctx.guild.roles, name='Certified Carrier')
    print(f'Check is user has role: "{co_role}"')
    print(f'User has roles: {ctx.author.roles}')

    print(f'Generating full unloading mission list requested by: {ctx.author}')
    mission_db.execute('''SELECT * FROM missions WHERE missiontype="unload";''')
    unload_records = [MissionData(mission_data) for mission_data in mission_db.fetchall()]

    mission_db.execute('''SELECT * FROM missions WHERE missiontype="load";''')
    print(f'Generating full loading mission list requested by: {ctx.author}')
    load_records = [MissionData(mission_data) for mission_data in mission_db.fetchall()]

    # If used by a non-carrier owner, link the total mission count and point to trade alerts.
    if co_role not in ctx.author.roles:
        print(f'User {ctx.author} does not have the required CO role, sending them to trade alerts.')
        # Sorry user, you need to go to trade alerts.
        trade_channel = bot.get_channel(trade_alerts_id)
        number_of_missions = len(load_records) + len(unload_records)

        description_text = f'For full details of all current trade missions follow the link to <#{trade_channel.id}>'
        if not number_of_missions:
            description_text = f'Currently no active missions listed in: <#{trade_channel.id}>'

        embed = discord.Embed(
            title=f"{number_of_missions} P.T.N Fleet Carrier missions in progress:",
            description=description_text,
            color=constants.EMBED_COLOUR_LOADING
        )

        return await ctx.send(embed=embed)

    print(f'User {ctx.author} has the required CO role, dumping all the missions here.')
    embed = discord.Embed(title=f"{len(load_records)} P.T.N Fleet Carrier LOADING missions in progress:",
                          color=constants.EMBED_COLOUR_LOADING)
    embed = _format_missions_embedd(load_records, embed)
    await ctx.send(embed=embed)

    embed = discord.Embed(title=f"{len(unload_records)} P.T.N Fleet Carrier UNLOADING missions in progress:",
                          color=constants.EMBED_COLOUR_UNLOADING)
    embed = _format_missions_embedd(unload_records, embed)
    await ctx.send(embed=embed)


def _format_missions_embedd(mission_data_list, embed):
    """
    Loop over a set of records and add certain fields to the message.
    """
    for mission_data in mission_data_list:
        embed.add_field(name=f"{mission_data.carrier_name}", value=f"<#{mission_data.channel_id}>", inline=True)
        embed.add_field(name=f"{mission_data.commodity}",
                        value=f"{mission_data.demand} at {mission_data.profit}k/unit", inline=True)
        embed.add_field(name=f"{mission_data.system.upper()} system",
                        value=f"{mission_data.station} ({mission_data.pad_size}-pads)", inline=True)
    return embed

# missions slash command - private, non-spammy
@slash.slash(name="missions", guild_ids=[bot_guild_id],
             description="Private command: Display all missions in progress.")
async def _missions(ctx: SlashContext):

    print(f'User {ctx.author} asked for all active missions via /missions in {ctx.channel}.')

    print(f'Generating full unloading mission list requested by: {ctx.author}')
    mission_db.execute('''SELECT * FROM missions WHERE missiontype="unload";''')
    unload_records = [MissionData(mission_data) for mission_data in mission_db.fetchall()]

    mission_db.execute('''SELECT * FROM missions WHERE missiontype="load";''')
    print(f'Generating full loading mission list requested by: {ctx.author}')
    load_records = [MissionData(mission_data) for mission_data in mission_db.fetchall()]

    trade_channel = bot.get_channel(trade_alerts_id)
    number_of_missions = len(load_records) + len(unload_records)

    description_text = f'For full details of all current trade missions follow the link to <#{trade_channel.id}>'
    if not number_of_missions:
        description_text = f'Currently no active missions listed in <#{trade_channel.id}>'

    embed = discord.Embed(
        title=f"{number_of_missions} P.T.N Fleet Carrier missions in progress:",
        description=description_text,
        color=constants.EMBED_COLOUR_LOADING
    )

    await ctx.send(embed=embed, hidden=True)

    if not number_of_missions:
        return
    else:

        embed = discord.Embed(title=f"{len(load_records)} P.T.N Fleet Carrier LOADING missions in progress:",
                            color=constants.EMBED_COLOUR_LOADING)
        embed = _format_missions_embedd(load_records, embed)
        await ctx.send(embed=embed, hidden=True)

        embed = discord.Embed(title=f"{len(unload_records)} P.T.N Fleet Carrier UNLOADING missions in progress:",
                            color=constants.EMBED_COLOUR_UNLOADING)
        embed = _format_missions_embedd(unload_records, embed)
        await ctx.send(embed=embed, hidden=True)


# CO command to quickly mark mission as complete, optionally send some RP text
@bot.command(name='done', help='Marks a mission as complete for specified carrier.\n'
                               'Deletes trade alert in Discord and sends messages to carrier channel and reddit if '
                               'appropriate.\n\nAnything put in quotes after the carrier name will be treated as a '
                               'quote to be sent along with the completion notice. This can be used for RP if desired.')
@commands.has_role('Certified Carrier')
async def done(ctx, carrier_name_search_term, rp=None):

    # Check we are in the designated mission channel, if not go no farther.
    mission_gen_channel = bot.get_channel(conf['MISSION_CHANNEL'])
    current_channel = ctx.channel

    print(f'Request received from {ctx.author} to mark the mission of {carrier_name_search_term} as done from channel: '
          f'{current_channel}')

    if current_channel != mission_gen_channel:
        # problem, wrong channel, no progress
        return await ctx.send(f'Sorry, you can only run this command out of: <#{mission_gen_channel.id}>.')

    mission_db.execute(f'''SELECT * FROM missions WHERE carrier LIKE (?)''', ('%' + carrier_name_search_term + '%',))
    mission_data = MissionData(mission_db.fetchone())
    if not mission_data:
        embed = discord.Embed(
            description=f"**ERROR**: no trade missions found for carriers matching \"**{carrier_name_search_term}\"**.",
            color=constants.EMBED_COLOUR_ERROR)
        await ctx.send(embed=embed)

    else:
        backup_database('missions')  # backup the missions database before going any further

        # fill in some info for messages
        desc_msg = f"> {rp}\n\n" if rp else ""

        # delete Discord trade alert
        if mission_data.discord_alert_id and mission_data.discord_alert_id != 'NULL':
            try:  # try in case it's already been deleted, which doesn't matter to us in the slightest but we don't
                # want it messing up the rest of the function

                # first check if it's Wine, in which case it went to the booze cruise channel
                if mission_data.commodity.title() == "Wine":
                    channel = bot.get_channel(wine_alerts_id)
                else:
                    channel = bot.get_channel(trade_alerts_id)

                discord_alert_id = mission_data.discord_alert_id
                msg = await channel.fetch_message(discord_alert_id)
                await msg.delete()
            except:
                await ctx.send("Looks like this mission alert was already deleted. Not to worry.")

            # send Discord carrier channel updates
            channel = bot.get_channel(mission_data.channel_id)
            embed = discord.Embed(title=f"{mission_data.carrier_name} MISSION COMPLETE", description=f"{desc_msg}",
                                  color=constants.EMBED_COLOUR_OK)
            embed.set_footer(text=f"This mission channel will be removed in {seconds_long//60} minutes.")
            await channel.send(embed=embed)

        # add comment to Reddit post
        if mission_data.reddit_post_id and mission_data.reddit_post_id != 'NULL':
            try:  # try in case Reddit is down
                reddit_post_id = mission_data.reddit_post_id
                await reddit.subreddit(to_subreddit)
                submission = await reddit.submission(reddit_post_id)
                await submission.reply(
                    f"    INCOMING WIDEBAND TRANSMISSION: P.T.N. CARRIER MISSION UPDATE\n\n**"
                    f"{mission_data.carrier_name}** mission complete. o7 CMDRs!\n\n{desc_msg}")

                # mark original post as spoiler, change its flair
                await submission.flair.select(flair_mission_stop)
                await submission.mod.spoiler()
            except:
                await ctx.send("Failed updating Reddit :(")

        # delete mission entry from db
        mission_db.execute(f'''DELETE FROM missions WHERE carrier LIKE (?)''', ('%' + carrier_name_search_term + '%',))
        missions_conn.commit()

        embed = discord.Embed(title=f"Mission complete for {mission_data.carrier_name}",
                              description=f"{desc_msg}Updated any sent alerts and removed from mission list.",
                              color=constants.EMBED_COLOUR_OK)
        await ctx.send(embed=embed)

        # remove channel
        await remove_carrier_channel(mission_data.channel_id, seconds_long)

        return


async def remove_carrier_channel(mission_channel_id, seconds):
    # get channel ID to remove
    delchannel = bot.get_channel(mission_channel_id)

    # start a timer
    print(f"Starting {seconds} second countdown for deletion of {delchannel}")
    await asyncio.sleep(seconds)
    print("Channel removal timer complete")

    try:
        # acquire channel lock
        print("Waiting for channel lock")
        await carrier_channel_lock.acquire()
        print("Channel lock acquired")

        # check whether channel is in-use for a new mission
        mission_db.execute(f"SELECT * FROM missions WHERE "
                        f"channelid = {mission_channel_id}")
        mission_data = MissionData(mission_db.fetchone())
        print(f'Mission data from remove_carrier_channel: {mission_data}')

        if mission_data:
            # abort abort abort
            print(f'New mission underway in this channel, aborting removal')
        else:
            # delete channel after a parting gift
            gif = random.choice(boom_gifs)
            await delchannel.send(gif)
            await asyncio.sleep(5)
            await delchannel.delete()
            print(f'Deleted {delchannel}')
    finally:
        # now release the channel lock
        carrier_channel_lock.release()
        print("Channel lock released")
        return


# a command for users to mark a carrier mission complete from within the carrier channel
@bot.command(name='complete', help="Use in a carrier's channel to mark the current trade mission complete.")
async def complete(ctx):

    # take a note of user ID and channel name and ID
    msg_ctx_name = ctx.channel.name
    msg_ctx_id = ctx.channel.id
    msg_usr_id = ctx.author.id

    # look for a match for the channel name in the carrier DB
    # TODO: separate into separate function
    carrier_db.execute(f"SELECT * FROM carriers WHERE "
                       f"discordchannel = '{msg_ctx_name}' ;")
    carrier_data = CarrierData(carrier_db.fetchone())
    if not carrier_data:
        # if there's no channel match, return an error
        embed = discord.Embed(description="**You need to be in a carrier's channel to mark its mission as complete.**",
                              color=constants.EMBED_COLOUR_ERROR)
        await ctx.send(embed=embed)
        return
    else:
        backup_database('missions')  # backup the missions database before going any further

        # now look to see if the carrier is on an active mission
        mission_db.execute(f"SELECT * FROM missions WHERE "
                           f"channelid = {msg_ctx_id} ")
        mission_data = MissionData(mission_db.fetchone())
        if not mission_data:
            # if there's no result, return an error
            embed = discord.Embed(description=f"**{carrier_data.carrier_long_name} doesn't seem to be on a trade "
                                              f"mission right now.**",
                                  color=constants.EMBED_COLOUR_ERROR)
            await ctx.send(embed=embed)

        else:
            # user is in correct channel and carrier is on a mission, so check whether user is sure they want to proceed
            embed = discord.Embed(
                description=f"Please confirm that **{mission_data.carrier_name}** has been fully "
                            f"{mission_data.mission_type}ed : **y** / **n**",
                color=constants.EMBED_COLOUR_QU)
            # embed.set_footer(text="For other issues (e.g. station price changes) please @ the Carrier Owner
            # directly.")
            await ctx.send(embed=embed)

            def check(message):
                return message.author == ctx.author and message.channel == ctx.channel and \
                       message.content.lower() in ["y", "n"]

            try:
                msg = await bot.wait_for("message", check=check, timeout=30)
                if msg.content.lower() == "n":
                    # whoops lol actually no
                    embed = discord.Embed(description="OK, mission will remain listed as in-progress.",
                                          color=constants.EMBED_COLOUR_OK)
                    await ctx.send(embed=embed)
                    return
                elif msg.content.lower() == "y":
                    # they said yes!
                    embed = discord.Embed(title=f"{mission_data.carrier_name} MISSION COMPLETE",
                                          description=f"<@{msg_usr_id}> reports mission complete! **This mission channel will be removed in {seconds_long//60} minutes.**",
                                          color=constants.EMBED_COLOUR_OK)
                    await ctx.send(embed=embed)
                    await ctx.send(f"Notifying carrier owner: <@{carrier_data.ownerid}>")

                    # notify owner by DM
                    user = bot.get_user(carrier_data.ownerid)
                    await user.send(f"Ahoy CMDR! The trade mission for your Fleet Carrier **{carrier_data.carrier_long_name}** has been marked as complete by {ctx.author.display_name}. Its mission channel will be removed in {seconds_long//60} minutes unless a new mission is started.")

                    # record command user in bot-spam
                    channel = bot.get_channel(bot_spam_id)
                    await channel.send(f"{ctx.author} used m.complete in #{carrier_data.discord_channel}")
                    # now we need to go do all the mission cleanup stuff

                    # delete Discord trade alert
                    if mission_data.discord_alert_id and mission_data.discord_alert_id != 'NULL':
                        try:
                            # check if it's Wine, in which case it went to the booze cruise channel
                            if mission_data.commodity.title() == "Wine":
                                channel = bot.get_channel(wine_alerts_id)
                            else:
                                channel = bot.get_channel(trade_alerts_id)
                            msg = await channel.fetch_message(mission_data.discord_alert_id)
                            await msg.delete()
                        except:
                            print(f"Looks like this mission alert for {mission_data.carrier_name} was already deleted"
                                  f" by someone else")

                    # add comment to Reddit post
                    if mission_data.reddit_post_id and mission_data.reddit_post_id != 'NULL':
                        try:
                            await reddit.subreddit(to_subreddit)
                            submission = await reddit.submission(mission_data.reddit_post_id)
                            await submission.reply(
                                f"    INCOMING WIDEBAND TRANSMISSION: P.T.N. CARRIER MISSION UPDATE\n\n"
                                f"**{mission_data.carrier_name}** mission complete. o7 CMDRs!\n\n\n\n*"
                                f"Reported on PTN Discord by {ctx.author.display_name}*")

                            # mark original post as spoiler, change its flair
                            await submission.flair.select(flair_mission_stop)
                            await submission.mod.spoiler()
                        except:
                            print(f"Reddit post failed to update for {mission_data.carrier_name}")

                    # delete mission entry from db
                    mission_db.execute(f'''DELETE FROM missions WHERE carrier LIKE (?)''',
                                       ('%' + mission_data.carrier_name + '%',))
                    missions_conn.commit()

                    # remove channel
                    await remove_carrier_channel(mission_data.channel_id, seconds_long)
                    return

            except asyncio.TimeoutError:
                embed = discord.Embed(description="No response, mission will remain listed as in-progress.")
                await ctx.send(embed=embed)



#
#                       UTILITY COMMANDS
#

# backup databases
@bot.command(name='backup', help='Backs up the carrier and mission databases.')
@commands.has_role('Admin')
async def backup(ctx):

    # make sure we are in the right channel
    bot_command_channel = bot.get_channel(conf['BOT_COMMAND_CHANNEL'])
    current_channel = ctx.channel
    if current_channel != bot_command_channel:
        # problem, wrong channel, no progress
        return await ctx.send(f'Sorry, you can only run this command out of: {bot_command_channel}.')

    print(f"{ctx.author} requested a manual DB backup")
    backup_database('missions') 
    backup_database('carriers') 
    await ctx.send("Database backup complete.")


@slash.slash(name="info", guild_ids=[bot_guild_id],
             description="Private command: Use in a Fleet Carrier's channel to show information about it.")
async def _info(ctx: SlashContext):

    print(f'/info command carrier_data called by {ctx.author} in {ctx.channel}')

    # take a note of channel name and ID
    msg_ctx_name = ctx.channel.name
    msg_ctx_id = ctx.channel.id

    # look for a match for the ID in the community carrier database
    carrier_db.execute(f"SELECT * FROM community_carriers WHERE "
                       f"channelid = {msg_ctx_id}")
    community_carrier_data = CommunityCarrierData(carrier_db.fetchone())

    if community_carrier_data:
        embed = discord.Embed(title="COMMUNITY CARRIER CHANNEL",
                              description=f"<#{ctx.channel.id}> is a <@&{cc_role_id}> channel "
                                          f"registered to <@{community_carrier_data.owner_id}>.\n\n"
                                          f"Community Carrier channels are for community building and events and "
                                          f"may be used for multiple Fleet Carriers. See channel pins and description "
                                          f"more information.", color=constants.EMBED_COLOUR_OK)
        await ctx.send(embed=embed, hidden=True)
        return # if it was a Community Carrier, we're done and gone. Otherwise we keep looking.

    # now look for a match for the channel name in the carrier DB
    carrier_db.execute(f"SELECT * FROM carriers WHERE "
                       f"discordchannel = '{msg_ctx_name}' ;")
    carrier_data = CarrierData(carrier_db.fetchone())

    if not carrier_data.discord_channel:
        print(f"/info failed, {ctx.channel} doesn't seem to be a carrier channel")
        # if there's no channel match, return an error
        embed = discord.Embed(description="Try again in a **🚛Trade Carriers** channel.", color=constants.EMBED_COLOUR_QU)
        await ctx.send(embed=embed, hidden=True)
        return
    else:
        print(f'Found data: {carrier_data}')
        embed = discord.Embed(title=f"Welcome to {carrier_data.carrier_long_name} ({carrier_data.carrier_identifier})", color=constants.EMBED_COLOUR_OK)
        embed = _add_common_embed_fields(embed, carrier_data)
        return await ctx.send(embed=embed, hidden=True)


@slash.slash(name="find", guild_ids=[bot_guild_id],
             description="Private command: Search for a fleet carrier by partial match for its name.")
async def _find(ctx: SlashContext, carrier_name_search_term):

    print(f"{ctx.author} used /find for '{carrier_name_search_term}' in {ctx.channel}")

    try:
        carrier_data = find_carrier_from_long_name(carrier_name_search_term)
        if carrier_data:
            print(f"Found {carrier_data}")
            embed = discord.Embed(title="Fleet Carrier Search Result",
                                  description=f"Displaying first match for {carrier_name_search_term}", color=constants.EMBED_COLOUR_OK)
            embed = _add_common_embed_fields(embed, carrier_data)
            return await ctx.send(embed=embed, hidden=True)
          
    except TypeError as e:
        print('Error in carrier long search: {}'.format(e))
    await ctx.send(f'No result for {carrier_name_search_term}.', hidden=True)


# list FCs
@bot.command(name='carrier_list', help='List all Fleet Carriers in the database. This times out after 60 seconds')
async def carrier_list(ctx):

    print(f'Carrier List requested by user: {ctx.author}')

    carrier_db.execute(f"SELECT * FROM carriers")
    carriers = [CarrierData(carrier) for carrier in carrier_db.fetchall()]

    def chunk(chunk_list, max_size=10):
        """
        Take an input list, and an expected max_size.

        :returns: A chunked list that is yielded back to the caller
        :rtype: iterator
        """
        for i in range(0, len(chunk_list), max_size):
            yield chunk_list[i:i + max_size]

    def validate_response(react, user):
        return user == ctx.author and str(react.emoji) in ["◀️", "▶️"]
        # This makes sure nobody except the command sender can interact with the "menu"

    # TODO: should pages just be a list of embed_fields we want to add?
    pages = [page for page in chunk(carriers)]

    max_pages = len(pages)
    current_page = 1

    embed = discord.Embed(title=f"{len(carriers)} Registered Fleet Carriers Page:#{current_page} of {max_pages}")
    count = 0   # Track the overall count for all carriers
    # Go populate page 0 by default
    for carrier in pages[0]:
        count += 1
        embed.add_field(name=f"{count}: {carrier.carrier_long_name} ({carrier.carrier_identifier})",
                        value=f"<@{carrier.ownerid}>", inline=False)
    # Now go send it and wait on a reaction
    message = await ctx.send(embed=embed)

    # From page 0 we can only go forwards
    await message.add_reaction("▶️")

    # 60 seconds time out gets raised by Asyncio
    while True:
        try:
            reaction, user = await bot.wait_for('reaction_add', timeout=60, check=validate_response)
            if str(reaction.emoji) == "▶️" and current_page != max_pages:

                print(f'{ctx.author} requested to go forward a page.')
                current_page += 1   # Forward a page
                new_embed = discord.Embed(title=f"{len(carriers)} Registered Fleet Carriers Page:{current_page}")
                for carrier in pages[current_page-1]:
                    # Page -1 as humans think page 1, 2, but python thinks 0, 1, 2
                    count += 1
                    new_embed.add_field(name=f"{count}: {carrier.carrier_long_name} ({carrier.carrier_identifier})",
                                        value=f"<@{carrier.ownerid}>", inline=False)

                await message.edit(embed=new_embed)

                # Ok now we can go back, check if we can also go forwards still
                if current_page == max_pages:
                    await message.clear_reaction("▶️")

                await message.remove_reaction(reaction, user)
                await message.add_reaction("◀️")

            elif str(reaction.emoji) == "◀️" and current_page > 1:
                print(f'{ctx.author} requested to go back a page.')
                current_page -= 1   # Go back a page

                new_embed = discord.Embed(title=f"{len(carriers)} Registered Fleet Carriers Page:{current_page}")
                # Start by counting back however many carriers are in the current page, minus the new page, that way
                # when we start a 3rd page we don't end up in problems
                count -= len(pages[current_page - 1])
                count -= len(pages[current_page])

                for carrier in pages[current_page - 1]:
                    # Page -1 as humans think page 1, 2, but python thinks 0, 1, 2
                    count += 1
                    new_embed.add_field(name=f"{count}: {carrier.carrier_long_name} ({carrier.carrier_identifier})",
                                        value=f"<@{carrier.ownerid}>", inline=False)

                await message.edit(embed=new_embed)
                # Ok now we can go forwards, check if we can also go backwards still
                if current_page == 1:
                    await message.clear_reaction("◀️")

                await message.remove_reaction(reaction, user)
                await message.add_reaction("▶️")
            else:
                # It should be impossible to hit this part, but lets gate it just in case.
                print(f'HAL9000 error: {ctx.author} ended in a random state while trying to handle: {reaction.emoji} '
                      f'and on page: {current_page}.')
                # HAl-9000 error response.
                error_embed = discord.Embed(title=f"I'm sorry {ctx.author}, I'm afraid I can't do that.")
                await message.edit(embed=error_embed)
                await message.remove_reaction(reaction, user)

        except asyncio.TimeoutError:
            print(f'Timeout hit during carrier request by: {ctx.author}')
            await ctx.send(f'Closed the active carrier list request from: {ctx.author} due to no input in 60 seconds.')
            await message.delete()
            break


# add FC to database
@bot.command(name='carrier_add', help='Add a Fleet Carrier to the database:\n'
                                      '\n'
                                      '<short_name> is used as a filename and should be a short one-word string with no special characters\n'
                                      '<long_name> is the carrier\'s full name including P.T.N. etc - surround this '
                                      'with quotes.\n'
                                      '<carrier_id> is the carrier\'s unique identifier in the format ABC-XYZ\n'
                                      '<owner_id> is the owner\'s Discord ID')
@commands.has_role('Admin')
async def carrier_add(ctx, short_name, long_name, carrier_id, owner_id):

    # make sure we are in the right channel
    bot_command_channel = bot.get_channel(conf['BOT_COMMAND_CHANNEL'])
    current_channel = ctx.channel
    if current_channel != bot_command_channel:
        # problem, wrong channel, no progress
        return await ctx.send(f'Sorry, you can only run this command out of: {bot_command_channel}.')

    # Only add to the carrier DB if it does not exist, if it does exist then the user should not be adding it.
    carrier_data = find_carrier_from_long_name(long_name)
    if carrier_data:
        # Carrier exists already, go skip it.
        print(f'Request recieved from {ctx.author} to add a carrier that already exists in the database ({long_name}).')

        embed = discord.Embed(title="Fleet carrier already exists, use m.carrier_edit to change its details.",
                              description=f"Carrier data matched for {long_name}", color=constants.EMBED_COLOUR_OK)
        embed = _add_common_embed_fields(embed, carrier_data)
        return await ctx.send(embed=embed)

    backup_database('carriers')  # backup the carriers database before going any further

    # TODO: If command fails at any stage, reset roles and channels to previous state before exiting

    # first generate a string to use for the carrier's channel name based on its long name

    stripped_name = long_name.replace(' ', '-').replace('.', '')

    # find carrier owner as a user object

    try:
        owner = await bot.fetch_user(owner_id)
        print(f"Owner identified as {owner.display_name}")
    except:
        raise EnvironmentError(f'Could not find Discord user matching ID {owner_id}')

    # finally, send all the info to the db
    await add_carrier_to_database(short_name, long_name, carrier_id, stripped_name.lower(), 0, owner_id)

    carrier_data = find_carrier_from_long_name(long_name)
    await ctx.send(
        f"Added **{carrier_data.carrier_long_name.upper()}** **{carrier_data.carrier_identifier.upper()}** "
        f"with shortname **{carrier_data.carrier_short_name.lower()}**, channel "
        f"**#{carrier_data.discord_channel}** "
        f"owned by <@{owner_id}> at ID **{carrier_data.pid}**")


# remove FC from database
@bot.command(name='carrier_del', help='Delete a Fleet Carrier from the database using its database entry ID#.')
@commands.has_role('Admin')
async def carrier_del(ctx, db_id):

    # make sure we are in the right channel
    bot_command_channel = bot.get_channel(conf['BOT_COMMAND_CHANNEL'])
    current_channel = ctx.channel
    if current_channel != bot_command_channel:
        # problem, wrong channel, no progress
        return await ctx.send(f'Sorry, you can only run this command out of: {bot_command_channel}.')

    try:
        carrier_data = find_carrier_from_pid(db_id)
        if carrier_data:
            embed = discord.Embed(title="Delete Fleet Carrier", description=f"Result for {db_id}",
                                  color=constants.EMBED_COLOUR_OK)
            embed = _add_common_embed_fields(embed, carrier_data)
            await ctx.send(embed=embed)

            embed = discord.Embed(title="Proceed with deletion?", description="y/n", color=constants.EMBED_COLOUR_OK)
            await ctx.send(embed=embed)

            def check(message):
                return message.author == ctx.author and message.channel == ctx.channel and \
                       message.content.lower() in ["y", "n"]

            # TODO: Prompt user whether to also delete the carrier's channel and crew role

            try:
                msg = await bot.wait_for("message", check=check, timeout=30)
                if msg.content.lower() == "n":
                    embed=discord.Embed(description="Deletion cancelled.", color=constants.EMBED_COLOUR_OK)
                    await ctx.send(embed=embed)
                    return
                elif msg.content.lower() == "y":
                    try:
                        error_msg = await delete_carrier_from_db(db_id)
                        if error_msg:
                            return await ctx.send(error_msg)

                        embed = discord.Embed(description=f"Fleet carrier #{carrier_data.pid} deleted.",
                                              color=constants.EMBED_COLOUR_OK)
                        return await ctx.send(embed=embed)
                    except Exception as e:
                        return ctx.send(f'Something went wrong, go tell the bot team "computer said: {e}"')

            except asyncio.TimeoutError:
                return await ctx.send("**Cancelled - timed out**")

    except TypeError as e:
        print(f'Error while finding carrier to delete: {e}.')
    await ctx.send(f"Couldn't find a carrier with ID #{db_id}.")


# change FC background image
@bot.command(name='carrier_image', help='Change the background image for the specified carrier:\n\n'
                                        'Use on its own to receive a blank template image.\n'
                                        'Use with carrier\'s name as argument to check the '
                                        'carrier\'s image or begin upload of a new image.')
@commands.has_role('Certified Carrier')
async def carrier_image(ctx, lookname=None):
    if not lookname:
        print(f"{ctx.author} called m.carrier_image without argument")
        file = discord.File(f"blank.png", filename="image.png")
        embed = discord.Embed(title=f"Instructions to create your own custom carrier mission image",
                              description="1. Copy the below image into your editor of choice\n(GIMP and Inkscape are both free)\n"
                                          "Make sure it's 500x500 pixels.\n"
                                          "2. Create a new layer underneath the image\n"
                                          "3. Arrange your chosen background image on your new background layer\n"
                                          "4. Save it and use `m.carrier_image <carriername>` to upload it.",
                              color=constants.EMBED_COLOUR_OK)
        embed.set_image(url="attachment://image.png")
        await ctx.send(file=file, embed=embed)
    else:
        print(f"{ctx.author} called m.carrier_image for {lookname}")
        carrier_data = find_carrier_from_long_name(lookname)
        file = discord.File(f"images/{carrier_data.carrier_short_name}.png", filename="image.png")
        embed = discord.Embed(title=f"{carrier_data.carrier_long_name} MISSION IMAGE",
                              color=constants.EMBED_COLOUR_QU)
        embed.set_image(url="attachment://image.png")
        await ctx.send(file=file, embed=embed)
        embed = discord.Embed(title="Change carrier's mission image?",
                              description="If you want to replace this image you can upload the new image now.\n\n"
                                          "To get a blank image template use `m.carrier_image` on its own.\n\n"
                                          "Images should be 500x500 pixels, in .png format, and based on the standard PTN image template from `m.carrier_image`.\n\n"
                                          "Input \"x\" or wait 60 seconds if you don't want to upload and just want to view.",
                              color=constants.EMBED_COLOUR_QU)
        message_upload_now = await ctx.send(embed=embed)

        def check(message_to_check):
            return message_to_check.author == ctx.author and message_to_check.channel == ctx.channel

        try:
            message = await bot.wait_for("message", check=check, timeout=60)
            if message.attachments:
                shutil.move(f'images/{carrier_data.carrier_short_name}.png',
                            f'images/old/{carrier_data.carrier_short_name}.{get_formatted_date_string()[1]}.png')
                for attachment in message.attachments:
                    await attachment.save(f"images/{carrier_data.carrier_short_name}.png")
                file = discord.File(f"images/{carrier_data.carrier_short_name}.png", filename="image.png")
                embed = discord.Embed(title=f"{carrier_data.carrier_long_name}",
                                      description="Background image updated.", color=constants.EMBED_COLOUR_OK)
                embed.set_image(url="attachment://image.png")
                await ctx.send(file=file, embed=embed)
                await message.delete()
                await message_upload_now.delete()
                print(f"{ctx.author} updated carrier image for {carrier_data.carrier_long_name}")
            elif message.content.lower() == "x":
                embed = discord.Embed(description="Existing image retained.",
                                      color=constants.EMBED_COLOUR_OK)
                await ctx.send(embed=embed)
                await message.delete()
                await message_upload_now.delete()
                return
        except asyncio.TimeoutError:
            embed = discord.Embed(description="Existing image retained (no response from user).",
                                  color=constants.EMBED_COLOUR_OK)
            await ctx.send(embed=embed)
            await message_upload_now.delete()
            return


# find FC based on shortname
@bot.command(name='findshort', help='DEPRECATED. Use to find a carrier by searching for its image file name (shortname).\n'
                                    '\n'
                                    'Syntax: m.findshort <search_term>\n'
                                    '\n'
                                    'Partial matches will work but only if they incorporate part of the shortname.\n'
                                    'To find a carrier based on a match with part of its full name, use the /find '
                                    'command.')
async def findshort(ctx, shortname_search_term):
    try:
        carriers = find_carrier_from_short_name(shortname_search_term)
        if carriers:
            carrier_data = None

            if len(carriers) == 1:
                print('Single carrier found, returning that directly')
                # if only 1 match, just assign it directly
                carrier_data = carriers[0]
            elif len(carriers) > 3:
                # If we ever get into a scenario where more than 3 commodities can be found with the same search
                # directly, then we need to revisit this limit
                print(f'More than 3 carriers found for: "{shortname_search_term}", {ctx.author} needs to search better.')
                await ctx.send(f'Please narrow down your search, we found {len(carriers)} matches for your '
                               f'input choice: "{shortname_search_term}"')
                return None  # Just return None here and let the calling method figure out what is needed to happen
            else:
                print(f'Between 1 and 3 carriers found for: "{shortname_search_term}", asking {ctx.author} which they want.')
                # The database runs a partial match, in the case we have more than 1 ask the user which they want.
                # here we have less than 3, but more than 1 match
                embed = discord.Embed(title=f"Multiple carriers ({len(carriers)}) found for input: {shortname_search_term}",
                                      color=constants.EMBED_COLOUR_OK)

                count = 0
                response = None  # just in case we try to do something before it is assigned, give it a value of None
                for carrier in carriers:
                    count += 1
                    embed.add_field(name='Carrier Name', value=f'{carrier.carrier_long_name}', inline=True)

                embed.set_footer(text='Please select the carrier with 1, 2 or 3')

                def check(message):
                    return message.author == ctx.author and message.channel == ctx.channel and \
                           len(message.content) == 1 and message.content.lower() in ["1", "2", "3"]

                message_confirm = await ctx.send(embed=embed)
                try:
                    # Wait on the user input, this might be better by using a reaction?
                    response = await bot.wait_for("message", check=check, timeout=15)
                    print(f'{ctx.author} responded with: "{response.content}", type: {type(response.content)}.')
                    index = int(response.content) - 1  # Users count from 1, computers count from 0
                    carrier_data = carriers[index]
                except asyncio.TimeoutError:
                    print('User failed to respond in time')
                    pass
                await message_confirm.delete()
                if response:
                    await response.delete()

            if carrier_data:
                embed = discord.Embed(title="Fleet Carrier Shortname Search Result",
                                      description=f"Displaying first match for {shortname_search_term}",
                                      color=constants.EMBED_COLOUR_OK)
                embed = _add_common_embed_fields(embed, carrier_data)
                return await ctx.send(embed=embed)
    except TypeError as e:
        print('Error in carrier search: {}'.format(e))
    await ctx.send(f'No result for {shortname_search_term}.')


def _add_common_embed_fields(embed, carrier_data):
    embed.add_field(name="Carrier Name", value=f"{carrier_data.carrier_long_name}", inline=True)
    embed.add_field(name="Carrier ID", value=f"{carrier_data.carrier_identifier}", inline=True)
    embed.add_field(name="Database Entry", value=f"{carrier_data.pid}", inline=True)
    embed.add_field(name="Discord Channel", value=f"#{carrier_data.discord_channel}", inline=True)
    embed.add_field(name="Owner", value=f"<@{carrier_data.ownerid}>", inline=True)
    embed.add_field(name="Shortname", value=f"{carrier_data.carrier_short_name}", inline=True)
    # shortname is not relevant to users and will be auto-generated in future
    return embed


# find FC based on longname
@bot.command(name='find', help='Find a carrier based on a partial match with any part of its full name\n'
                               '\n'
                               'Syntax: m.find <search_term>')
async def find(ctx, carrier_name_search_term):
    try:
        carriers = find_carrier_from_long_name_multiple(carrier_name_search_term)
        if carriers:
            carrier_data = None

            if len(carriers) == 1:
                print('Single carrier found, returning that directly')
                # if only 1 match, just assign it directly
                carrier_data = carriers[0]
            elif len(carriers) > 3:
                # If we ever get into a scenario where more than 3 commodities can be found with the same search
                # directly, then we need to revisit this limit
                print(f'More than 3 carriers found for: "{carrier_name_search_term}", {ctx.author} needs to search better.')
                await ctx.send(f'Please narrow down your search, we found {len(carriers)} matches for your '
                               f'input choice: "{carrier_name_search_term}"')
                return None  # Just return None here and let the calling method figure out what is needed to happen
            else:
                print(f'Between 1 and 3 carriers found for: "{carrier_name_search_term}", asking {ctx.author} which they want.')
                # The database runs a partial match, in the case we have more than 1 ask the user which they want.
                # here we have less than 3, but more than 1 match
                embed = discord.Embed(title=f"Multiple carriers ({len(carriers)}) found for input: {carrier_name_search_term}",
                                      color=constants.EMBED_COLOUR_OK)

                count = 0
                response = None  # just in case we try to do something before it is assigned, give it a value of None
                for carrier in carriers:
                    count += 1
                    embed.add_field(name='Carrier Name', value=f'{carrier.carrier_long_name}', inline=True)

                embed.set_footer(text='Please select the carrier with 1, 2 or 3')

                def check(message):
                    return message.author == ctx.author and message.channel == ctx.channel and \
                           len(message.content) == 1 and message.content.lower() in ["1", "2", "3"]

                message_confirm = await ctx.send(embed=embed)
                try:
                    # Wait on the user input, this might be better by using a reaction?
                    response = await bot.wait_for("message", check=check, timeout=15)
                    print(f'{ctx.author} responded with: "{response.content}", type: {type(response.content)}.')
                    index = int(response.content) - 1  # Users count from 1, computers count from 0
                    carrier_data = carriers[index]
                except asyncio.TimeoutError:
                    print('User failed to respond in time')
                    pass
                await message_confirm.delete()
                if response:
                    await response.delete()

            if carrier_data:
                embed = discord.Embed(title="Fleet Carrier Search Result",
                                      description=f"Displaying match for {carrier_name_search_term}",
                                      color=constants.EMBED_COLOUR_OK)
                embed = _add_common_embed_fields(embed, carrier_data)
                return await ctx.send(embed=embed)
    except TypeError as e:
        print('Error in carrier search: {}'.format(e))
    await ctx.send(f'No result for {carrier_name_search_term}.')


# find FC based on ID
@bot.command(name='findid', help='Find a carrier based on its database ID\n'
                                 'Syntax: findid <integer>')
async def findid(ctx, db_id):
    try:
        if not isinstance(db_id, int):
            try:
                db_id = int(db_id)
                # Someone passed in a non integer, because this gets passed in with the wrapped quotation marks, it is
                # probably impossible to convert. Just go return an error and call the user an fool of a took
            except ValueError:
                return await ctx.send(
                    f'Computer says "The input must be a valid integer, you gave us a {type(db_id)} with value: '
                    f'{db_id}"')
        carrier_data = find_carrier_from_pid(db_id)
        if carrier_data:
            embed = discord.Embed(title="Fleet Carrier DB# Search Result",
                                  description=f"Displaying carrier with DB# {carrier_data.pid}",
                                  color=constants.EMBED_COLOUR_OK)
            embed = _add_common_embed_fields(embed, carrier_data)
            await ctx.send(embed=embed)
            return  # We exit here

    except TypeError as e:
        print('Error in carrier findid search: {}'.format(e))
    await ctx.send(f'No result for {db_id}.')


# find commodity
@bot.command(name='findcomm', help='Find a commodity based on a search term\n'
                                   'If a term has too many possible matches try a longer search term.\n')
async def search_for_commodity(ctx, commodity_search_term):
    print(f'search_for_commodity called by {ctx.author} to search for {commodity_search_term}')
    try:
        commodity = await find_commodity(commodity_search_term, ctx)
        if commodity:
            return await ctx.send(commodity)
    except:
        # Catch any exception
        pass
    await ctx.send(f'No such commodity found for: "{commodity_search_term}".')


@bot.command(name='carrier_edit', help='Edit a specific carrier in the database by providing specific inputs')
@commands.has_role('Admin')
async def edit_carrier(ctx, carrier_name_search_term):
    """
    Edits a carriers information in the database. Provide a carrier name that can be partially matched and follow the
    steps.

    :param discord.ext.commands.Context ctx: The discord context
    :param str carrier_name_search_term: The carrier name to find
    :returns: None
    """
    print(f'edit_carrier called by {ctx.author} to update the carrier: {carrier_name_search_term} from channel: {ctx.channel}')

    # make sure we are in the right channel
    bot_command_channel = bot.get_channel(conf['BOT_COMMAND_CHANNEL'])
    current_channel = ctx.channel
    if current_channel != bot_command_channel:
        # problem, wrong channel, no progress
        return await ctx.send(f'Sorry, you can only run this command out of: {bot_command_channel}.')

    # Go fetch the carrier details by searching for the name

    carrier_data = copy.copy(find_carrier_from_long_name(carrier_name_search_term))
    print(carrier_data)
    if carrier_data:
        embed = discord.Embed(title=f"Edit DB request received.",
                              description=f"Editing starting for {carrier_data.carrier_long_name} requested by "
                                          f"{ctx.author}",
                              color=constants.EMBED_COLOUR_OK)
        embed = _configure_all_carrier_detail_embed(embed, carrier_data)

        # Store this, we might want to update it later
        initial_message = await ctx.send(embed=embed)
        edit_carrier_data = await _determine_db_fields_to_edit(ctx, carrier_data)
        if not edit_carrier_data:
            # The determination told the user there was an error. Wipe the original message and move on
            initial_message.delete()
            return

        # Now we know what fields to edit, go do something with them, first display them to the user
        edited_embed = discord.Embed(title=f"Please validate the inputs are correct",
                                     description=f"Validate the new settings for {carrier_data.carrier_long_name}",
                                     color=constants.EMBED_COLOUR_OK)
        edited_embed = _configure_all_carrier_detail_embed(edited_embed, edit_carrier_data)
        edit_send = await ctx.send(embed=edited_embed)

        # Get the user to agree before we write
        confirm_embed = discord.Embed(title="Confirm you want to write these values to the database please",
                                      description="Yes or No.", color=constants.EMBED_COLOUR_QU)
        confirm_embed.set_footer(text='y/n - yes, no.')
        message_confirm = await ctx.send(embed=confirm_embed)

        def check_confirm(message):
            return message.content and message.author == ctx.author and message.channel == ctx.channel and \
                   all(character in 'yn' for character in set(message.content.lower())) and len(message.content) == 1

        try:

            msg = await bot.wait_for("message", check=check_confirm, timeout=30)
            if "n" in msg.content.lower():
                print(f'User {ctx.author} requested to cancel the edit operation.')
                # immediately stop if there's an x anywhere in the message, even if there are other proper inputs
                await ctx.send("**Edit operation cancelled by the user.**")
                await msg.delete()
                await message_confirm.delete()
                await edit_send.delete()
                await initial_message.delete()
                return None  # Exit the check logic

            elif 'y' in msg.content.lower():
                await ctx.send("**Writing the values now ...**")
                await message_confirm.delete()
                await msg.delete()
                await edit_send.delete()
        except asyncio.TimeoutError:
            await ctx.send("**Write operation from {ctx.author} timed out.**")
            await edit_send.delete()
            await message_confirm.delete()
            await initial_message.delete()
            return None  # Exit the check logic

        # Go update the details to the database
        await _update_carrier_details_in_database(ctx, edit_carrier_data, carrier_data.carrier_long_name)

        # Double check if we need to edit the carrier shortname, if so then we also need to edit the backup image
        if edit_carrier_data.carrier_short_name != carrier_data.carrier_short_name:
            print('Renaming the carriers image')
            os.rename(
                f'images/{carrier_data.carrier_short_name}.png',
                f'images/{edit_carrier_data.carrier_short_name}.png'
            )
            print(f'Carrier image renamed from: images/{carrier_data.carrier_short_name}.png to '
                  f'images/{edit_carrier_data.carrier_short_name}.png')

        # Go grab the details again, make sure it is correct and display to the user
        updated_carrier_data = find_carrier_from_long_name(edit_carrier_data.carrier_long_name)
        if updated_carrier_data:
            embed = discord.Embed(title=f"Reading the settings from DB:",
                                  description=f"Double check and re-run if incorrect the settings for old name: "
                                              f"{carrier_data.carrier_long_name}",
                                  color=constants.EMBED_COLOUR_OK)
            embed = _configure_all_carrier_detail_embed(embed, updated_carrier_data)
            await initial_message.delete()
            return await ctx.send(embed=embed)
        else:
            await ctx.send('We did not find the new database entry - that is not good.')

    else:
        return await ctx.send(f'No result found for the carrier: "{carrier_name_search_term}".')


async def _update_carrier_details_in_database(ctx, carrier_data, original_name):
    """
    Updates the carrier details into the database. It first ensures that the discord channel actually exists, if it
    does not then you are getting an error back.

    :param discord.ext.commands.Context ctx: The discord context
    :param CarrierData carrier_data: The carrier data to write
    :param str original_name: The original carrier name, needed so we can find it in the database
    """
    backup_database('carriers')  # backup the carriers database before going any further

    # TODO: Write to the database
    await carrier_db_lock.acquire()
    try:

        data = (
            carrier_data.carrier_short_name,
            carrier_data.carrier_long_name,
            carrier_data.carrier_identifier,
            carrier_data.discord_channel,
            carrier_data.channel_id,
            carrier_data.ownerid,
            f'%{original_name}%'
        )
        # Handy number to print out what the database connection is actually doing
        carriers_conn.set_trace_callback(print)
        carrier_db.execute(
            ''' UPDATE carriers 
            SET shortname=?, longname=?, cid=?, discordchannel=?, channelid=?, ownerid=?
            WHERE longname LIKE (?) ''', data
        )

        carriers_conn.commit()
    finally:
        carrier_db_lock.release()


async def _determine_db_fields_to_edit(ctx, carrier_data):
    """
    Loop through a dummy CarrierData object and see if the user wants to update any of the fields.

    :param discord.ext.commands.Context ctx: The discord context object
    :param CarrierData carrier_data: The carriers data you want to edit.
    :returns: A carrier data object to edit into the database
    :rtype: CarrierData
    """
    # We operate and return from this a copy of the object, not the object itself. Else things outside this also get
    # affected. Because python uses pass by reference, and this is a mutable object, things can go wrong.
    new_carrier_data = copy.copy(carrier_data)

    embed = discord.Embed(title=f"Edit DB request in progress ...",
                          description=f"Editing in progress for {carrier_data.carrier_long_name}",
                          color=constants.EMBED_COLOUR_OK)

    def check_confirm(message):
        return message.content and message.author == ctx.author and message.channel == ctx.channel and \
            all(character in 'ynx' for character in set(message.content.lower())) and len(message.content) == 1

    def check_user(message):
        return message.content and message.author == ctx.author and message.channel == ctx.channel

    # These two are used below, initial value so we can wipe the message out if needed
    message_confirm = None  # type: discord.Message
    msg = None  # type: discord.Message

    for field in vars(carrier_data):

        # Remove any pre-existing messages/responses if they were present.
        if message_confirm:
            await message_confirm.delete()
        if msg:
            await msg.delete()

        if field == 'pid':
            # We cant edit the DB ID here, so skip over it.
            # TODO: DB ID uses autoincrement, we probably want our own index if we want to use this.
            continue

        print(f'Looking to see if the user wants to edit the field {field} for carrier: '
              f'{carrier_data.carrier_long_name}')

        # Go ask the user for each one if they want to update, and if yes then to what.
        embed.add_field(name=f'Do you want to update the carriers: "{field}" value?',
                        value=f'Current Value: "{getattr(carrier_data, field)}"', inline=True)
        embed.set_footer(text='y/n/x - yes, no or cancel the operation')
        message_confirm = await ctx.send(embed=embed)

        try:
            msg = await bot.wait_for("message", check=check_confirm, timeout=30)
            if "x" in msg.content.lower():
                print(f'User {ctx.author} requested to cancel the edit operation.')
                # immediately stop if there's an x anywhere in the message, even if there are other proper inputs
                await ctx.send("**Edit operation cancelled by the user.**")
                await msg.delete()
                await message_confirm.delete()
                return None  # Exit the check logic

            elif 'n' in msg.content.lower():
                # Log a message and skip over
                print(f'User {ctx.author} does not want to edit the field: {field}')
                # We do not care, just move on
            elif 'y' in msg.content.lower():
                # Remove this, we re-assign it now.
                await msg.delete()
                await message_confirm.delete()

                # Log a message and skip over
                print(f'User {ctx.author} wants to edit the field: {field}')
                embed.remove_field(0)   # Remove the current field, add a new one and resend

                embed.add_field(name=f'What is the new value for: {field}?', value='Type your response now.')
                embed.set_footer()   # Clear the foot as well
                message_confirm = await ctx.send(embed=embed)

                msg = await bot.wait_for("message", check=check_user, timeout=30)
                print(f'Setting the value for {new_carrier_data.carrier_long_name} filed {field} to '
                      f'"{msg.content.strip()}"')

                # Use setattr to change the value of the variable field object to the user input
                setattr(new_carrier_data, field, msg.content.strip())
            else:
                print(f'{ctx.author} provided the invalid input: {msg.content} from object: {ctx}.')
                # Should never be hitting this as we gate the message
                await ctx.send(f"**I cannot do anything with that entry '{msg.content}', please stick to y, n or x.**")
                return None  # Break condition just in case
        except asyncio.TimeoutError:
            print(f'Carrier edit requested by {ctx.author} timed out. Context: {ctx}')
            await ctx.send("**Edit operation timed out (no valid response from user).**")
            await message_confirm.delete()
            return None

        # Remove the previous field so we have things in a nice view
        embed.remove_field(0)

    print(f'Current tracking of carrier data: {carrier_data}')
    # If the current thing is the same as the old thing, why did we bother?
    if new_carrier_data == carrier_data:
        print(f'User {ctx.author} went through the whole process and does not want to edit anything.')
        await ctx.send("**After all those button clicks you did not want to edit anything, fun.**")
        return None

    print(f'Carrier data now looks like:')
    print(f'\t Initial: {carrier_data}')
    print(f'\t Initial: {new_carrier_data}')

    return new_carrier_data


def _configure_all_carrier_detail_embed(embed, carrier_data):
    """
    Adds all the common fields to a message embed and returns the embed.

    :param discord.Embed embed: The original embed to edit.
    :param CarrierData carrier_data: The carrier data to use for populating the embed
    :returns: The embeded message
    """
    embed.add_field(name='Carrier Name', value=f'{carrier_data.carrier_long_name}', inline=True)
    embed.add_field(name='Carrier Identifier', value=f'{carrier_data.carrier_identifier}', inline=True)
    embed.add_field(name='Short Name', value=f'{carrier_data.carrier_short_name}', inline=True)
    embed.add_field(name='Discord Channel', value=f'#{carrier_data.discord_channel}', inline=True)
    embed.add_field(name='Carrier Owner', value=f'<@{carrier_data.ownerid}>', inline=True)
    embed.add_field(name='DB ID', value=f'{carrier_data.pid}', inline=True)
    embed.set_footer(text="Note: DB ID is not an editable field.")
    return embed


#
#                       COMMUNITY CARRIER COMMANDS
#

@bot.command(name='cc', help='Create a new Community Carrier channel. Limit is one per user.\n'
                             'Format: m.cc @owner channel-name\n'
                             'The owner will receive the @Community Carrier role\n'
                             'as well as full permissions in the channel.')
@commands.has_any_role('Community Team', 'Mod', 'Admin', 'Council')
async def cc(ctx, owner: discord.Member, channel_name):

    # TODO:
    # - embeds instead of normal messages for all cc interactions?
    # - tidy up messages after actions complete?

    stripped_channel_name = channel_name.replace(' ', '-').replace('.', '').replace('#', '')
    print(f"{ctx.author} used m.cc")

    # first check the user isn't already in the DB, if they are, then stop
    community_carrier_data = find_community_carrier_with_owner_id(owner.id)
    if community_carrier_data:
        # TODO: this should be fetchone() not fetchall but I can't make it work otherwise
        for community_carrier in community_carrier_data:
            print(f"Found data: {community_carrier.owner_id} owner of {community_carrier.channel_id}")
            await ctx.send(f"User {owner.name} is already registered as a Community Carrier with channel <#{community_carrier.channel_id}>")
            return
        
    # get the CC category as a discord channel category object
    category = discord.utils.get(ctx.guild.categories, id=cc_cat_id)

    def check(message):
        return message.author == ctx.author and message.channel == ctx.channel and \
                                 message.content.lower() in ["y", "n"]

# first check whether a channel already exists with that name

    new_channel = discord.utils.get(ctx.guild.channels, name=stripped_channel_name)

    if new_channel:
        print(f"Channel {new_channel} already exists.")
        # channel exists, ask if they want to use it
        await ctx.send(f"Channel already exists: <#{new_channel.id}>. Do you wish to use this existing channel? **y**/**n**")
        try:
            msg = await bot.wait_for("message", check=check, timeout=60)
            if msg.content.lower() == "n":
                await ctx.send("OK, cancelling.")
                return
            elif msg.content.lower() == "y":
                # they want to use the existing channel, so we have to move it to the right category
                print(f"Using existing channel {new_channel} and making {owner.name} its owner.")
                try:
                    await new_channel.edit(category=category)
                    await ctx.send(f"Channel moved to {category.name}.")
                except Exception as e:
                    await ctx.send(f"Error: {e}")
                    print(e)
                    return
        except asyncio.TimeoutError:
            await ctx.send("Cancelled: no response.")
            return
    else:
        # channel does not exist, ask user if they want to create it
        await ctx.send(f"Create the channel #{stripped_channel_name} owned by {owner.display_name}? **y**/**n**")
        try:
            msg = await bot.wait_for("message", check=check, timeout=30)
            if msg.content.lower() == "n":
                await ctx.send("OK, cancelling.")
                print("User cancelled cc command.")
                return
            elif msg.content.lower() == "y":
                # create the channel
                    new_channel = await ctx.guild.create_text_channel(stripped_channel_name, category=category)
                    print(f"Created {new_channel}")

                    print(f'Channels: {ctx.guild.channels}')

                    if not new_channel:
                        raise EnvironmentError(f'Could not create carrier channel {stripped_channel_name}')
        except asyncio.TimeoutError:
            await ctx.send("Cancelled: no response.")
            return

    # now we have the channel and it's in the correct category, we need to give the user CC role and add channel permissions

    role = discord.utils.get(ctx.guild.roles, id=cc_role_id)
    print(cc_role_id)
    print(role)

    try:
        await owner.add_roles(role)
        print(f"Added Community Carrier role to {owner}")
    except Exception as e:
        print(e)
        await ctx.send(f"Failed adding role to {owner}: {e}")

    # add owner to channel permissions

    try:
        # first make sure it has the default permissions for the CC category
        await new_channel.edit(sync_permissions=True)
        print("Synced permissions with parent category")
        # now add the owner with superpermissions
        await new_channel.set_permissions(owner, read_messages=True,
                                            manage_channels=True,
                                            manage_roles=True,
                                            manage_webhooks=True,
                                            create_instant_invite=True,
                                            send_messages=True,
                                            embed_links=True,
                                            attach_files=True,
                                            add_reactions=True,
                                            external_emojis=True,
                                            manage_messages=True,
                                            read_message_history=True,
                                            use_slash_commands=True)
        print(f"Set permissions for {owner} in {new_channel}")
    except Forbidden:
        raise EnvironmentError(f"Could not set channel permissions for {owner.display_name} in {new_channel}, reason: Bot does not have permissions to edit channel specific permissions.")
    except NotFound:
        raise EnvironmentError(f"Could not set channel permissions for {owner.display_name} in {new_channel}, reason: The role or member being edited is not part of the guild.")
    except HTTPException:
        raise EnvironmentError(f"Could not set channel permissions for {owner.display_name} in {new_channel}, reason: Editing channel specific permissions failed.")
    except InvalidArgument:
        raise EnvironmentError(f"Could not set channel permissions for {owner.display_name} in {new_channel}, reason: The overwrite parameter invalid or the target type was not Role or Member.")
    except:
        raise EnvironmentError(f'Could not set channel permissions for {owner.display_name} in {new_channel}')

    # now we enter it into the community carriers table
    print("Locking carrier db...")
    await carrier_db_lock.acquire()
    print("Carrier DB locked.")
    try:
        carrier_db.execute(''' INSERT INTO community_carriers VALUES(?, ?) ''',
                           (owner.id, new_channel.id))
        carriers_conn.commit()
        print("Added new community carrier to database")
    finally:
        print("Unlocking carrier db...")
        carrier_db_lock.release()
        print("Carrier DB unlocked.")

    # tell the user what's going on
    embed = discord.Embed(description=f"<@{owner.id}> is now a <@&{cc_role_id}> and owns <#{new_channel.id}>.\n\nNote channels may be freely renamed without affecting registration.", color=constants.EMBED_COLOUR_OK)
    await ctx.send(embed=embed)

    # add a note in bot_spam
    channel = bot.get_channel(bot_spam_id)
    await channel.send(f"{ctx.author} used m.cc in <#{ctx.channel.id}> to add {owner.name} as a Community Carrier with channel <#{new_channel.id}>")

    return



# list all community carriers
@bot.command(name='cc_list', help='List all Community Carriers.')
@commands.has_any_role('Community Team', 'Mod', 'Admin', 'Council')
async def cc_list(ctx):
    carrier_db.execute(f"SELECT * FROM community_carriers")
    community_carriers = [CommunityCarrierData(carrier) for carrier in carrier_db.fetchall()]

    def chunk(chunk_list, max_size=10):
        """
        Take an input list, and an expected max_size.

        :returns: A chunked list that is yielded back to the caller
        :rtype: iterator
        """
        for i in range(0, len(chunk_list), max_size):
            yield chunk_list[i:i + max_size]

    def validate_response(react, user):
        return user == ctx.author and str(react.emoji) in ["◀️", "▶️"]
        # This makes sure nobody except the command sender can interact with the "menu"

    # TODO: should pages just be a list of embed_fields we want to add?
    pages = [page for page in chunk(community_carriers)]

    max_pages = len(pages)
    current_page = 1

    embed = discord.Embed(title=f"{len(community_carriers)} Registered Community Carriers Page:#{current_page} of {max_pages}")
    count = 0   # Track the overall count for all carriers
    # Go populate page 0 by default
    for community_carriers in pages[0]:
        count += 1
        embed.add_field(name="\u200b",
                        value=f"{count}: <@{community_carriers.owner_id}> owns <#{community_carriers.channel_id}>", inline=False)
    # Now go send it and wait on a reaction
    message = await ctx.send(embed=embed)

    # From page 0 we can only go forwards
    if not current_page == max_pages: await message.add_reaction("▶️")

    # 60 seconds time out gets raised by Asyncio
    while True:
        try:
            reaction, user = await bot.wait_for('reaction_add', timeout=60, check=validate_response)
            if str(reaction.emoji) == "▶️" and current_page != max_pages:

                print(f'{ctx.author} requested to go forward a page.')
                current_page += 1   # Forward a page
                new_embed = discord.Embed(title=f"{len(community_carriers)} Registered Community Carriers Page:{current_page}")
                for community_carriers in pages[current_page-1]:
                    # Page -1 as humans think page 1, 2, but python thinks 0, 1, 2
                    count += 1
                    new_embed.add_field(name="\u200b",
                                        value=f"{count}: <@{community_carriers.owner_id}> owns <#{community_carriers.channel_id}>", inline=False)

                await message.edit(embed=new_embed)

                # Ok now we can go back, check if we can also go forwards still
                if current_page == max_pages:
                    await message.clear_reaction("▶️")

                await message.remove_reaction(reaction, user)
                await message.add_reaction("◀️")

            elif str(reaction.emoji) == "◀️" and current_page > 1:
                print(f'{ctx.author} requested to go back a page.')
                current_page -= 1   # Go back a page

                new_embed = discord.Embed(title=f"{len(community_carriers)} Registered Community Carriers Page:{current_page}")
                # Start by counting back however many carriers are in the current page, minus the new page, that way
                # when we start a 3rd page we don't end up in problems
                count -= len(pages[current_page - 1])
                count -= len(pages[current_page])

                for community_carriers in pages[current_page - 1]:
                    # Page -1 as humans think page 1, 2, but python thinks 0, 1, 2
                    count += 1
                    new_embed.add_field(name="\u200b",
                                        value=f"{count}: <@{community_carriers.owner_id}> owns <#{community_carriers.channel_id}>", inline=False)

                await message.edit(embed=new_embed)
                # Ok now we can go forwards, check if we can also go backwards still
                if current_page == 1:
                    await message.clear_reaction("◀️")

                await message.remove_reaction(reaction, user)
                await message.add_reaction("▶️")
            else:
                # It should be impossible to hit this part, but lets gate it just in case.
                print(f'HAL9000 error: {ctx.author} ended in a random state while trying to handle: {reaction.emoji} '
                      f'and on page: {current_page}.')
                # HAl-9000 error response.
                error_embed = discord.Embed(title=f"I'm sorry {ctx.author}, I'm afraid I can't do that.")
                await message.edit(embed=error_embed)
                await message.remove_reaction(reaction, user)

        except asyncio.TimeoutError:
            print(f'Timeout hit during community carrier request by: {ctx.author}')
            await ctx.send(f'Closed the active community carrier list request from: {ctx.author} due to no input in 60 seconds.')
            await message.delete()
            break    


# find a community carrier channel by owner
@bot.command(name='cc_owner', help='Search for an owner in the Community Carrier database.\n'
                             'Format: m.cc_owner @owner\n')
@commands.has_any_role('Community Team', 'Mod', 'Admin', 'Council')
async def cc_owner(ctx, owner: discord.User):
    community_carrier_data = find_community_carrier_with_owner_id(owner.id)
    if community_carrier_data:
        # TODO: this should be fetchone() not fetchall but I can't make it work otherwise
        for community_carrier in community_carrier_data:
            print(f"Found data: {community_carrier.owner_id} owner of {community_carrier.channel_id}")
            await ctx.send(f"User {owner.name} is registered as a Community Carrier with channel <#{community_carrier.channel_id}>")
            return
    else:
        await ctx.send(f"No Community Carrier registered to {owner.name}")


# delete a Community Carrier
@bot.command(name='cc_del', help='Delete a Community Carrier.\n'
                             'Format: m.cc_del @owner\n')
@commands.has_any_role('Community Team', 'Mod', 'Admin', 'Council')
async def cc_del(ctx, owner: discord.Member):
    print(f"{ctx.author} called cc_del command for {owner}")

    def check(message):
        return message.author == ctx.author and message.channel == ctx.channel and \
                                 message.content.lower() in ["y", "n"]
    def check2(message):
        return message.author == ctx.author and message.channel == ctx.channel and \
                                 message.content.lower() in ["d", "a"]

    # search for the user's database entry
    community_carrier_data = find_community_carrier_with_owner_id(owner.id)
    if not community_carrier_data:
        await ctx.send(f"No Community Carrier registered to {owner.name}")
        return
    elif community_carrier_data:
        # TODO: this should be fetchone() not fetchall but I can't make it work otherwise
        for community_carrier in community_carrier_data:
            print(f"Found data: {community_carrier.owner_id} owner of {community_carrier.channel_id}")
            channel_id = community_carrier.channel_id
            await ctx.send(f"User {owner.name} is registered as a Community Carrier with channel <#{channel_id}>")

    await ctx.send("Remove Community Carrier role and de-register user? **y**/**n**")
    try:
        msg = await bot.wait_for("message", check=check, timeout=30)
        if msg.content.lower() == "n":
            await ctx.send("OK, cancelling.")
            print("User cancelled cc_del command.")
            return
        elif msg.content.lower() == "y":
            print("User wants to proceed with removal.")

    except asyncio.TimeoutError:
        await ctx.send("Cancelled: no response.")
        return
    
    await ctx.send(f"Would you like to (**d**)elete or (**a**)archive <#{channel_id}>?")
    try:
        msg = await bot.wait_for("message", check=check2, timeout=30)
        if msg.content.lower() == "a":
            delete = 0
            print("User chose to archive channel.")
            
        elif msg.content.lower() == "d":
            delete = 1
            print("User wants to delete channel.")
            await ctx.send("Deleted channels are gone forever, like tears in rain. Are you sure you want to delete? **y**/**n**")
            try:
                msg = await bot.wait_for("message", check=check, timeout=30)
                if msg.content.lower() == "n":
                    await ctx.send("OK, cancelling.")
                    print("User cancelled cc_del command.")
                    return
                elif msg.content.lower() == "y":
                    print("User wants to proceed with removal.")
                    await ctx.send("OK, have it your way hoss.")

            except asyncio.TimeoutError:
                await ctx.send("Cancelled: no response.")
                return

    except asyncio.TimeoutError:
        await ctx.send("Cancelled: no response.")
        return

    # now we do the thing
    # remove the database entry
    try:
        error_msg = await delete_community_carrier_from_db(owner.id)
        if error_msg:
            return await ctx.send(error_msg)

        print("User DB entry removed.")
    except Exception as e:
        return await ctx.send(f'Something went wrong, go tell the bot team "computer said: {e}"')

    # now remove the Discord role from the user

    role = discord.utils.get(ctx.guild.roles, id=cc_role_id)

    try:
        await owner.remove_roles(role)
        print(f"Removed Community Carrier role from {owner}")
    except Exception as e:
        print(e)
        await ctx.send(f"Failed removing role from {owner}: {e}")

    channel = bot.get_channel(channel_id)
    category = discord.utils.get(ctx.guild.categories, id=archive_cat_id)

    if not delete:
        # archive the channel and reset its permissions
        try:
            await channel.edit(category=category)
            print("moved channel to archive")
            # now make sure it has the default permissions for the archive category
            await channel.edit(sync_permissions=True)
            print("Synced permissions")

            await ctx.send(f"{owner.name} removed from database and <#{channel_id}> archived.")

            # notify in bot_spam
            channel = bot.get_channel(bot_spam_id)
            await channel.send(f"{ctx.author} used m.cc_del in <#{ctx.channel.id}> to remove {owner.name} as a Community Carrier. Channel <#{channel_id} was archived.")
            return
        except Exception as e:
            print(e)
            return await ctx.send(f"Error, channel not archived: {e}")

    elif delete:
        # delete the channel
        try:
            await channel.delete()
            print(f'Deleted {channel}')
            gif = random.choice(byebye_gifs)
            await ctx.send(gif)
            await ctx.send(f"{owner.name} removed from database and #{channel} deleted.")

            # notify in bot_spam
            channel = bot.get_channel(bot_spam_id)
            await channel.send(f"{ctx.author} used m.cc_del in <#{ctx.channel.id}> to remove {owner.name} as a Community Carrier. Channel #{channel} was deleted.")
            return
        except Exception as e:
            print(e)
            return await ctx.send(f"Error, channel not deleted: {e}")



# ping the bot
@bot.command(name='ping', help='Ping the bot')
@commands.has_role('Certified Carrier')
async def ping(ctx):
    gif = random.choice(hello_gifs)
    await ctx.send(gif)
    # await ctx.send("**PING? PONG!**")


# quit the bot
@bot.command(name='stopquit', help="Stops the bots process on the VM, ending all functions.")
@commands.has_role('Admin')
async def stopquit(ctx):
    await ctx.send(f"k thx bye")
    await user_exit()


#
# error handling
#
@bot.event
async def on_command_error(ctx, error):
    gif = random.choice(error_gifs)
    if isinstance(error, commands.BadArgument):
        await ctx.send('**Bad argument!**')
    elif isinstance(error, commands.CommandNotFound):
        await ctx.send("**Invalid command.**")
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send('**Please include all required parameters.** Use m.help <command> for details.')
    elif isinstance(error, commands.MissingPermissions):
        await ctx.send('**You must be a Carrier Owner to use this command.**')
    else:
        await ctx.send(gif)
        await ctx.send(f"Sorry, that didn't work. Check your syntax and permissions, error: {error}")


bot.run(TOKEN)
