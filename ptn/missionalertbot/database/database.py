# functions to build and backup database
import os
import sqlite3
import asyncio
import shutil
import enum
import discord
from datetime import datetime
from datetime import timezone
# from ptn.missionalertbot.constants import none
from ptn.missionalertbot.GetFormattedDateString import get_formatted_date_string
from ptn.missionalertbot.CarrierData import CarrierData
from ptn.missionalertbot.MissionData import MissionData
from ptn.missionalertbot.CommunityCarrierData import CommunityCarrierData
from ptn.missionalertbot.NomineesData import NomineesData
import ptn.missionalertbot.constants as constants

# connect to sqlite carrier database
carriers_conn = sqlite3.connect('carriers.db')
carriers_conn.row_factory = sqlite3.Row
carrier_db = carriers_conn.cursor()

# connect to sqlite missions database
missions_conn = sqlite3.connect('missions.db')
missions_conn.row_factory = sqlite3.Row
mission_db = missions_conn.cursor()

# We need some locks to we wait on the DB queries
carrier_db_lock = asyncio.Lock()
mission_db_lock = asyncio.Lock()
carrier_channel_lock = asyncio.Lock()


# dump db to .sql file
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

# used by database startup
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

# used by database startup
def check_table_column_exists(column_name, table_name, database):
    """
    Checks whether a column exists in a table for a database.

    :param str column_name: The column name to check for.
    :param str table_name: The table to check for the column in.
    :param sqlite.Connection.cursor database: The database to connect against.
    :type: bool
    """
    database.execute('''SELECT COUNT(name) FROM pragma_table_info('{}') WHERE name='{}' '''.format(
        table_name, column_name))
    return bool(database.fetchone()[0])


# build the databases from scratch if needed
def build_database_on_startup():
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
                    ownerid INT,
                    lasttrade INT NOT NULL DEFAULT (cast(strftime('%s','now') as int))
                ) 
            ''')
    else:
        print('Carrier database exists, do nothing')

    print('Starting up - checking if carriers database has new "lasttrade" column or not')
    if not check_table_column_exists('lasttrade', 'carriers', carrier_db):
        """
        In order to create the new 'lasttrade' column, a new table has to be created because
        SQLite does not allow adding a new column with a non-constant value.
        We then copy data from table to table, and rename them into place.
        We will leave the backup table in case something goes wrong.
        There is not enough try/catch here to be perfect. sorry.
        """ 
        temp_ts = int(datetime.now(tz=timezone.utc).timestamp())
        temp_carriers_table = 'carriers_lasttrade_%s' % temp_ts
        backup_carriers_table = 'carriers_backup_%s' % temp_ts
        print(f'"lasttrade" column missing from carriers database, creating new temp table: {temp_carriers_table}')
        # create new temp table with new column for lasttrade.
        carrier_db.execute('''
            CREATE TABLE {}(
                p_ID INTEGER PRIMARY KEY AUTOINCREMENT,
                shortname TEXT NOT NULL UNIQUE,
                longname TEXT NOT NULL,
                cid TEXT NOT NULL,
                discordchannel TEXT NOT NULL,
                channelid INT,
                ownerid INT,
                lasttrade INT default (cast(strftime('%s','now') as int))
            )
        '''.format(temp_carriers_table))
        # copy data from carriers table to new temp table.
        print('Copying carrier data to new table.')
        carrier_db.execute('''INSERT INTO {}(p_ID, shortname, longname, cid, discordchannel, channelid, ownerid) select * from carriers'''.format(temp_carriers_table))
        # rename old table and keep as backup just in case.
        print(f'Renaming current carriers table to "{backup_carriers_table}"')
        carrier_db.execute('''ALTER TABLE carriers RENAME TO {}'''.format(backup_carriers_table))
        # rename temp table as original.
        print(f'Renaming "{temp_carriers_table}" temp table to "carriers"')
        carrier_db.execute('''ALTER TABLE {} RENAME TO carriers'''.format(temp_carriers_table))
        print('Operation complete.')
        carriers_conn.commit()


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
                    channelid INT NOT NULL UNIQUE,
                    roleid INT NOT NULL UNIQUE
                ) 
            ''')
    else:
        print('Community Carrier database exists, do nothing')

    print('Starting up - checking if community carriers database has new "roleid" column or not')
    if not check_table_column_exists('roleid', 'community_carriers', carrier_db):
        """
        In order to create the new column, a new table has to be created because
        SQLite does not allow adding a new column with a non-constant value.
        We then copy data from table to table, and rename them into place.
        We will leave the backup table in case something goes wrong.
        There is not enough try/catch here to be perfect. sorry. (that's OK Durzo, thanks for the code!)
        """ 
        temp_ts = int(datetime.now(tz=timezone.utc).timestamp())
        temp_carriers_table = 'community_carriers_newcolumn_%s' % temp_ts
        backup_carriers_table = 'community_carriers_backup_%s' % temp_ts
        print(f'roleid column missing from carriers database, creating new temp table: {temp_carriers_table}')
        # create new temp table with new column for lasttrade.
        carrier_db.execute('''
            CREATE TABLE {}(
                    ownerid INT NOT NULL UNIQUE,
                    channelid INT NOT NULL UNIQUE,
                    roleid INT UNIQUE
            )
        '''.format(temp_carriers_table))
        # copy data from community_carriers table to new temp table.
        print('Copying community_carriers data to new table.')
        carrier_db.execute('''INSERT INTO {}(ownerid, channelid) select * from community_carriers'''.format(temp_carriers_table))
        # rename old table and keep as backup just in case.
        print(f'Renaming current community_carriers table to "{backup_carriers_table}"')
        carrier_db.execute('''ALTER TABLE community_carriers RENAME TO {}'''.format(backup_carriers_table))
        # rename temp table as original.
        print(f'Renaming "{temp_carriers_table}" temp table to "community_carriers"')
        carrier_db.execute('''ALTER TABLE {} RENAME TO community_carriers'''.format(temp_carriers_table))
        print('Operation complete.')
        carriers_conn.commit()


    print('Starting up - checking nominees database if it exists or not')
    # create nominees table if necessary
    if not check_database_table_exists('nominees', carrier_db):
        print('Nominees database missing - creating it now')

        if os.path.exists(os.path.join(os.getcwd(), 'db_sql', 'nominees_dump.sql')):
            # recreate from backup file
            print('Recreating database from backup ...')
            with open(os.path.join(os.getcwd(), 'db_sql', 'nominees_dump.sql')) as f:
                sql_script = f.read()
                carrier_db.executescript(sql_script)

        else:
            # Create a new version
            print('No backup found - Creating empty database')
            carrier_db.execute('''
                CREATE TABLE nominees( 
                    nominatorid INT NOT NULL,
                    pillarid INT NOT NULL,
                    note TEXT
                ) 
            ''')
    else:
        print('Nominees database exists, do nothing')


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


"""
Functions to search or edit the databases
"""

# class for CCO Carrier database
class CarrierDbFields(enum.Enum):
    longname = 'longname'
    shortname = 'shortname'
    cid = 'cid'
    channelname = 'discordchannel'
    channelid = 'channelid'
    ownerid = 'ownerid'
    lasttrade = 'lasttrade'
    p_id = 'p_ID'

# class for CC database
class CCDbFields(enum.Enum):
    ownerid = 'ownerid'
    channelid = 'channelid'
    roleid = 'roleid'

# function to remove a carrier
async def delete_carrier_from_db(p_id):
    carrier = find_carrier(p_id, CarrierDbFields.p_id.name)
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
    try:
        await carrier_db_lock.acquire()
        carrier_db.execute(f"DELETE FROM community_carriers WHERE ownerid = {ownerid}")
        carriers_conn.commit()
    finally:
        carrier_db_lock.release()
    return


# remove a nominee from the database
async def delete_nominee_from_db(pillarid):
    try:
        await carrier_db_lock.acquire()
        carrier_db.execute(f"DELETE FROM nominees WHERE pillarid = {pillarid}")
        carriers_conn.commit()
    finally:
        carrier_db_lock.release()
    return


# function to remove a nominee
async def delete_nominee_by_nominator(nomid, pillarid):
    print("Attempting to delete {nomid} {pillarid} match.")
    try:
        await carrier_db_lock.acquire()
        carrier_db.execute(f"DELETE FROM nominees WHERE nominatorid = {nomid} AND pillarid = {pillarid}")
        carriers_conn.commit()
    finally:
        carrier_db_lock.release()
    return print("Deleted")


# function to remove all carriers, not currently used by any bot command
def _delete_all_from_database(database):
    """
    Removes all the entries from the database.

    :returns: None
    """
    carrier_db.execute(f"DELETE FROM {database}")
    carriers_conn.commit()


# function to search for a carrier
def find_carrier(searchterm, searchfield):
    """
    Finds any carriers from the specified column matching the given searchterm.

    :param searchterm: Search term to match
    :param searchfield: DB column to match against
    :returns: A single CarrierData object
    :rtype: CarrierData
    """
    # TODO: This needs to check an exact not a `LIKE`
    carrier_db.execute(
        f"SELECT * FROM carriers WHERE {searchfield} LIKE (?)", (f'%{searchterm}%',)
        )
    carrier_data = CarrierData(carrier_db.fetchone())
    print(f"FC {carrier_data.pid} is {carrier_data.carrier_long_name} {carrier_data.carrier_identifier} called by "
          f"shortname {carrier_data.carrier_short_name} with channel #{carrier_data.discord_channel} called "
          f"from find_carrier.")
    return carrier_data


# used to find carriers if we expect multiple results for a search term
# TODO: make every carrier longname search prompt with multiple results and use this function
def find_carriers_mult(searchterm, searchfield):
    """
    Returns all carriers matching the searchterm from the searchfield

    :param searchterm: The searchterm to match
    :param searchfield: The db field to match against
    :returns: A list of carrier data objects
    :rtype: list[CarrierData]
    """
    carrier_db.execute(
        f"SELECT * FROM carriers WHERE {searchfield} LIKE (?)", (f'%{searchterm}%',)
    )
    carrier_data = [CarrierData(carrier) for carrier in carrier_db.fetchall()]
    for carrier in carrier_data:
        print(f"FC {carrier.pid} is {carrier.carrier_long_name} {carrier.carrier_identifier} called by "
              f"shortname {carrier.carrier_short_name} with channel <#{carrier.channel_id}> "
              f"and owner {carrier.ownerid} called from find_carriers_mult.")

    return carrier_data


def find_community_carrier(searchterm, searchfield):
    """
    Returns channel owner and role matching the ownerid

    :param str searchterm: The searchterm to match
    :param str searchfield: The db column to match against
    :returns: A list of community carrier data objects
    :rtype: list[CommunityCarrierData]
    """
    carrier_db.execute(f"SELECT * FROM community_carriers WHERE "
                       f"{searchfield} = {searchterm} ")
    community_carrier_data = [CommunityCarrierData(community_carrier) for community_carrier in carrier_db.fetchall()]
    for community_carrier in community_carrier_data:
        print(f"{community_carrier.owner_id} owns channel {community_carrier.channel_id}" 
              f" called from find_community_carrier.")

    return community_carrier_data


def find_nominee_with_id(pillarid):
    """
    Returns nominee, nominator and note matching the nominee's user ID

    :param int pillarid: The user id to match
    :returns: A list of nominees data objects
    :rtype: list[NomineesData]
    """
    carrier_db.execute(f"SELECT * FROM nominees WHERE "
                       f"pillarid = {pillarid} ")
    nominees_data = [NomineesData(nominees) for nominees in carrier_db.fetchall()]
    for nominees in nominees_data:
        print(f"{nominees.pillar_id} nominated by {nominees.nom_id} for reason {nominees.note}" 
              f" called from find_nominee_with_id.")

    return nominees_data


def find_nominator_with_id(nomid):
    """
    Returns nominee, nominator and note matching the nominator's user ID

    :param int nomid: The user id to match
    :returns: A list of nominees data objects
    :rtype: list[NomineesData]
    """
    carrier_db.execute(f"SELECT * FROM nominees WHERE "
                       f"nominatorid = {nomid} ")
    nominees_data = [NomineesData(nominees) for nominees in carrier_db.fetchall()]
    for nominees in nominees_data:
        print(f"{nominees.nom_id} nominated {nominees.pillar_id} for reason {nominees.note}" 
              f" called from find_nominee_with_id.")

    return nominees_data


# search the mission database
def find_mission(searchterm, searchfield):
    print("called find_mission")
    """
    Searches the mission database for ongoing missions

    :param str searchterm: the searchterm to match
    :param str searchfield: the DB column to match against
    :returns: list[mission data]
    """
    mission_db.execute(f'''SELECT * FROM missions WHERE {searchfield} LIKE (?)''',
                        (f'%{searchterm}%',))
    mission_data = MissionData(mission_db.fetchone())
    print(f'Found mission data: {mission_data}')
    return mission_data


# check if a carrier is for a registered PTN fleet carrier
async def _is_carrier_channel(carrier_data):
    if not carrier_data.discord_channel:
        # if there's no channel match, return an error
        embed = discord.Embed(description="Try again in a **🚛Trade Carriers** channel.", color=constants.EMBED_COLOUR_QU)
        return embed
    else:
        return