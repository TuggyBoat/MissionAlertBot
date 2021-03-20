# MissionAlertBot.py
from PIL import Image, ImageFont, ImageDraw
import os
import discord
import sqlite3
from dotenv import load_dotenv
from discord.ext import commands
from datetime import datetime
from datetime import timezone

# connect to sqlite db
conn = sqlite3.connect('carriers.db') 
conn.row_factory = sqlite3.Row
c = conn.cursor()

# create record if necessary
def table_exists(table_name): 
    c.execute('''SELECT count(name) FROM sqlite_master WHERE TYPE = 'table' AND name = '{}' '''.format(table_name)) 
    if c.fetchone()[0] == 1: 
        return True 
    return False

if not table_exists('carriers'): 
    c.execute('''
        CREATE TABLE carriers( 
            p_ID INTEGER PRIMARY KEY AUTOINCREMENT,
            shortname TEXT NOT NULL UNIQUE, 
            longname TEXT NOT NULL, 
            cid TEXT NOT NULL, 
            discordchannel TEXT NOT NULL 
        ) 
    ''')

# add carrier, being sure to correct case
def defcarrier_add(shortname, longname, cid, discordchannel): 
    c.execute(''' INSERT INTO carriers VALUES(NULL, ?, ?, ?, ?) ''', (shortname.lower(), longname.upper(), cid.upper(), discordchannel.lower())) 
    conn.commit()

# remove a carrier
def defcarrier_del(p_ID):
    c.execute(f"DELETE FROM carriers WHERE p_ID = {p_ID}")
    conn.commit()

# remove all carriers
def defdelete_all_carriers(): 
    c.execute(f"DELETE FROM carriers") 
    conn.commit()

# list carriers - this doesn't work as-is with row_factory
def defcarriers_list(): 
    c.execute('''SELECT * FROM carriers''') 
    data = [] 
    for row in c.fetchall(): 
        data.append(row) 
    return data

# search for a carrier by longname
def defcarrier_findlong(looklong):
    c.execute(f"SELECT p_ID, shortname, longname, cid, discordchannel FROM carriers WHERE longname LIKE (?)", ('%'+looklong+'%',))
    result = c.fetchone()
    global p_ID, shortname, longname, cid, discordchannel
    p_ID, shortname, longname, cid, discordchannel = result['p_ID'],result['shortname'],result['longname'],result['cid'],result['discordchannel']
    print(f"FC {p_ID} is {longname} {cid} called by shortname {shortname} with channel {discordchannel}")

# search for a carrier by shortname
def defcarrier_findshort(lookshort):
    c.execute(f"SELECT p_ID, shortname, longname, cid, discordchannel FROM carriers WHERE shortname LIKE (?)", ('%'+lookshort+'%',))
    result = c.fetchone()
    global p_ID, shortname, longname, cid, discordchannel
    p_ID, shortname, longname, cid, discordchannel = result['p_ID'],result['shortname'],result['longname'],result['cid'],result['discordchannel']
    print(f"FC {p_ID} is {longname} {cid} called by shortname {shortname} with channel {discordchannel}")

# search for a carrier by p_ID
def defcarrier_findpid(lookid):
    c.execute(f"SELECT p_ID, shortname, longname, cid, discordchannel FROM carriers WHERE p_ID = {lookid}")
    result = c.fetchone()
    global p_ID, shortname, longname, cid, discordchannel
    p_ID, shortname, longname, cid, discordchannel = result['p_ID'],result['shortname'],result['longname'],result['cid'],result['discordchannel']
    print(f"FC {p_ID} is {longname} {cid} called by shortname {shortname} with channel {discordchannel}")

# search for a commodity by name or partial name
def defcomm_find(lookfor):
    c.execute(f"SELECT commodity, avgsell, avgbuy, maxsell, minbuy, maxprofit FROM commodities WHERE commodity LIKE (?)", ('%'+lookfor+'%',))
    result = c.fetchone()
    global commodity, avgsell, avgbuy, maxsell, minbuy, maxprofit
    commodity, avgsell, avgbuy, maxsell, minbuy, maxprofit = result['commodity'],result['avgsell'],result['avgbuy'],result['maxsell'],result['minbuy'],result['maxprofit']
    print(f"Commodity {commodity} avgsell {avgsell} avgbuy {avgbuy} maxsell {maxsell} minbuy {minbuy} maxprofit {maxprofit}")

# function to load token from .env
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

# details of fonts to be used
reg_font = ImageFont.truetype('font/Exo/static/Exo-Light.ttf', 16)
name_font = ImageFont.truetype('font/Exo/static/Exo-ExtraBold.ttf', 34)
title_font = ImageFont.truetype('font/Exo/static/Exo-ExtraBold.ttf', 26)
normal_font = ImageFont.truetype('font/Exo/static/Exo-Medium.ttf', 20)
field_font = ImageFont.truetype('font/Exo/static/Exo-Light.ttf', 20)

# get date and time
def defget_datetime():
    dt_now = datetime.now(tz=timezone.utc)
    global dt_string
    dt_string = dt_now.strftime("%d %B" + " 3307" + " %H:%M")

# function to create image for loading
def defcreateimage_load(carriername, carrierreg, commodity, system, station, profit):
    my_image = Image.open("bitmap.png")
    image_editable = ImageDraw.Draw(my_image)
    image_editable.text((27,150), "PILOTS TRADE NETWORK", (255, 255, 255), font=title_font)
    image_editable.text((27,180), "CARRIER LOADING MISSION", (191, 53, 57), font=title_font)
    image_editable.text((27,235), "FLEET CARRIER " + cid, (0, 217, 255), font=reg_font)
    image_editable.text((27,250), longname, (0, 217, 255), font=name_font)
    image_editable.text((27,330), "COMMODITY:", (255, 255, 255), font=field_font)
    image_editable.text((170,330), commodity.upper(), (255, 255, 255), font=normal_font)
    image_editable.text((27,370), "SYSTEM:", (255, 255, 255), font=field_font)
    image_editable.text((170,370), system.upper(), (255, 255, 255), font=normal_font)
    image_editable.text((27,410), "STATION:", (255, 255, 255), font=field_font)
    image_editable.text((170,410), station.upper(), (255, 255, 255), font=normal_font)
    image_editable.text((27,450), "PROFIT:", (255, 255, 255), font=field_font)
    image_editable.text((170,450), profit + "k per unit", (255, 255, 255), font=normal_font)
    my_image.save("result.png")

# function to create image for unloading
def defcreateimage_unload(carriername, carrierreg, commodity, system, station, profit):
    my_image = Image.open("bitmap.png")
    image_editable = ImageDraw.Draw(my_image)
    image_editable.text((27,150), "PILOTS TRADE NETWORK", (255, 255, 255), font=title_font)
    image_editable.text((27,180), "CARRIER UNLOADING MISSION", (191, 53, 57), font=title_font)
    image_editable.text((27,235), "FLEET CARRIER " + cid, (0, 217, 255), font=reg_font)
    image_editable.text((27,250), longname, (0, 217, 255), font=name_font)
    image_editable.text((27,330), "COMMODITY:", (255, 255, 255), font=field_font)
    image_editable.text((170,330), commodity.upper(), (255, 255, 255), font=normal_font)
    image_editable.text((27,370), "SYSTEM:", (255, 255, 255), font=field_font)
    image_editable.text((170,370), system.upper(), (255, 255, 255), font=normal_font)
    image_editable.text((27,410), "STATION:", (255, 255, 255), font=field_font)
    image_editable.text((170,410), station.upper(), (255, 255, 255), font=normal_font)
    image_editable.text((27,450), "PROFIT:", (255, 255, 255), font=field_font)
    image_editable.text((170,450), profit + "k per unit", (255, 255, 255), font=normal_font)
    my_image.save("result.png")

# store a new FC to the database


# search database for FC and return details


# bot loading
bot = commands.Bot(command_prefix='m.')

@bot.event
async def on_ready():
    print(f'{bot.user.name} has connected to Discord!')

# take input from a load command and send it to the image creation function above, then output details as text
@bot.command(name='load', help='Generate details for a loading mission.\n'
                               '\n'
                               '<lookshort> is the carrier\'s shortname.\n'
                               '<commshort> is the commodity shortened to anything that will still successfully search, e.g. agro\n'
                               '<system> should be in quotes\n'
                               '<station> should also be in quotes\n'
                               '<profit> is a number of thousands without the k\n'
                               '\n'
                               'Case is automatically corrected for all inputs.')
async def load(ctx, lookshort, commshort, system, station, profit):
    defcomm_find(commshort)
    defcarrier_findshort(lookshort)
    defcreateimage_load(longname, cid, commodity, system, station, profit)
    defget_datetime()

    embed=discord.Embed(title="Generating and fetching mission alerts...", description="For Reddit posts, text should be copied and pasted into the Markdown editor. You can switch to Fancy Pants mode afterwards to make changes.", color=0x80ff80)
    await ctx.send(embed=embed)

    embed=discord.Embed(title="Trade Alert (Discord)", description=f"`{discordchannel} loading {commodity} from **{station.upper()}** station in **{system.upper()}**, {profit}k per unit profit`", color=0x80ffff)
    await ctx.send(embed=embed)

    embed=discord.Embed(title="Reddit Post Title", description=f"`*** P.T.N. News - Trade mission - {longname} {cid} - {dt_string} ***`", color=0xff0000)
    await ctx.send(embed=embed)

    embed=discord.Embed(title="Reddit Post Body - PASTE INTO MARKDOWN MODE", description=f"`    INCOMING WIDEBAND TRANSMISSION: P.T.N. CARRIER LOADING MISSION IN PROGRESS\n\n**BUY FROM**: station **{station.upper()}** in system **{system.upper()}**\n\n**COMMODITY**: {commodity}\n\n&#x200B;\n\n**SELL TO**: Fleet Carrier **{longname} {cid}**\n\n**PROFIT**: {profit}k/unit\n\n\n\n[Join us on Discord](https://www.reddit.com/r/PilotsTradeNetwork/comments/l0y7dk/pilots_trade_network_intergalactic_discord_server/) for mission updates and discussion.`", color=0x800000)
    embed.set_footer(text="**SWAP TO MARKDOWN MODE BEFORE PASTING TEXT TO REDDIT.**\nYou can swap back to Fancy Pants mode after pasting. If you want to embed the image in the Reddit post, just swap to Fancy Pants and drag it in. You can also add additional content such as RP quotes, etc, by using Fancy Pants mode after pasting.")
    await ctx.send(embed=embed)

    await ctx.send(file=discord.File('result.png'))

    
    #await ctx.send(f"**TRADE ALERT (DISCORD)**:\n`{longname} loading {commodity} from **{station.upper()}** station in ** {system.upper()}**, {profit}k per unit profit`")
    #await ctx.send(f"**REDDIT TITLE**:\n `*** P.T.N. News - Trade mission - {longname} {cid} - {dt_string}`")
    #await ctx.send(f"**REDDIT TEXT**:\n`    INCOMING WIDEBAND TRANSMISSION: P.T.N. CARRIER LOADING MISSION IN PROGRESS\n\n**BUY FROM**: station ** {station.upper()}** in system **{system.upper()}**\n\n**COMMODITY**: {commodity}\n\n&#x200B;\n\n**SELL TO**: Fleet Carrier **{longname} {cid}**\n\n**PROFIT**: {profit}k/unit\n\n\n\n[Join us on Discord](https://www.reddit.com/r/PilotsTradeNetwork/comments/l0y7dk/pilots_trade_network_intergalactic_discord_server/) for mission updates and discussion.`")

# unload command
@bot.command(name='unload', help='Generate details for an unloading mission.\n'
                                 '\n'
                                 '<lookshort> is the carrier\'s shortname.\n'
                                 '<commshort> is the commodity shortened to anything that will still successfully search, e.g. agro\n'
                                 '<system> should be in quotes\n'
                                 '<station> should also be in quotes\n'
                                 '<profit> is a number of thousands without the k\n'
                                 '\n'
                                 'Case is automatically corrected for all inputs.')
async def unload(ctx, lookshort, commshort, system, station, profit):
    defcomm_find(commshort)
    defcarrier_findshort(lookshort)
    defcreateimage_unload(longname, cid, commodity, system, station, profit)
    defget_datetime()

    embed=discord.Embed(title="Generating and fetching mission alerts...", description="For Reddit posts, text should be copied and pasted into the **Markdown editor**. You can switch to Fancy Pants mode afterwards to make changes.", color=0x80ff80)
    await ctx.send(embed=embed)
  
    embed=discord.Embed(title="Trade Alert (Discord)", description=f"`{discordchannel} unloading {commodity} to **{station.upper()}** station in **{system.upper()}**, {profit}k per unit profit`", color=0x80ffff)
    await ctx.send(embed=embed)

    embed=discord.Embed(title="Reddit Post Title", description=f"`*** P.T.N. News - Trade mission - {longname} {cid} - {dt_string} ***`", color=0xff0000)
    await ctx.send(embed=embed)

    embed=discord.Embed(title="Reddit Post Body - PASTE INTO MARKDOWN MODE", description=f"`    INCOMING WIDEBAND TRANSMISSION: P.T.N. CARRIER LOADING MISSION IN PROGRESS\n\n**BUY FROM**: Fleet Carrier **{longname} {cid}**\n\n**COMMODITY**: {commodity}\n\n&#x200B;\n\n**SELL TO**: station **{station.upper()}** in system **{system.upper()}**\n\n**PROFIT**: {profit}k/unit\n\n\n\n[Join us on Discord](https://www.reddit.com/r/PilotsTradeNetwork/comments/l0y7dk/pilots_trade_network_intergalactic_discord_server/) for mission updates and discussion.`", color=0x800000)
    embed.set_footer(text="**SWAP TO MARKDOWN MODE BEFORE PASTING TEXT TO REDDIT.**\nYou can swap back to Fancy Pants mode after pasting. If you want to embed the image in the Reddit post, just swap to Fancy Pants and drag it in. You can also add additional content such as RP quotes, etc, by using Fancy Pants mode after pasting.")
    await ctx.send(embed=embed)

    await ctx.send(file=discord.File('result.png'))

    #await ctx.send(file=discord.File('result.png'))
    #await ctx.send(f"**TRADE ALERT (DISCORD)**:\n`{longname} unloading {commodity} to **{station.upper()}** station in ** {system.upper()}**, {profit}k per unit profit`")
    #await ctx.send(f"**REDDIT TITLE**:\n `*** P.T.N. News - Trade mission - {longname} {cid} - {dt_string}`")
    #await ctx.send(f"**REDDIT TEXT**:\n`    INCOMING WIDEBAND TRANSMISSION: P.T.N. CARRIER LOADING MISSION IN PROGRESS\n\n**BUY FROM**: Fleet Carrier **{longname} {cid}**\n\n**COMMODITY**: {commodity}\n\n&#x200B;\n\n**SELL TO**: station ** {station.upper()}** in system **{system.upper()}**\n\n**PROFIT**: {profit}k/unit\n\n\n\n[Join us on Discord](https://www.reddit.com/r/PilotsTradeNetwork/comments/l0y7dk/pilots_trade_network_intergalactic_discord_server/) for mission updates and discussion.`")

# add FC to database
@bot.command(name='carrier_add', help='Add a Fleet Carrier to the database:\n'
                                      '\n'
                                      '<shortname> should be a short one-word string as you\'ll be typing it a lot\n'
                                      '<longname> is the carrier\'s full name including P.T.N. etc - surround this with quotes.\n'
                                      '<cid> is the carrier\'s unique identifier in the format ABC-XYZ\n'
                                      '<discordchannel> is the carrier\'s discord channel in the format #ptn-carriername\n')
async def carrier_add(ctx, shortname, longname, cid, discordchannel):
    defcarrier_add(shortname, longname, cid, discordchannel)
    defcarrier_findshort(shortname)
    await ctx.send(f"Added **{longname.upper()}** **{cid.upper()}** with shortname **{shortname.lower()}** and channel **{discordchannel.lower()}** at ID **{p_ID}**")

# remove FC from database
@bot.command(name='carrier_del', help='Delete a Fleet Carrier from the database using its ID.\n'
                                      'Use the findid command to check before deleting.')
async def carrier_del(ctx, p_ID):
    defcarrier_del(p_ID)
    await ctx.send(f"Attempted to remove carrier number {p_ID}")

# find FC based on shortname
@bot.command(name='find', help='Find a carrier based on its shortname.\n'
                               '\n'
                               'Syntax: findshort <string>\n'
                               '\n'
                               'Partial matches will work but only if they incorporate part of the shortname.\n'
                               'To find a carrier based on a match with part of its full name, use the findlong command.')
async def find(ctx, lookshort):
    defcarrier_findshort(lookshort)
    await ctx.send(f"FC {p_ID} is **{longname} {cid}** called by shortname **{shortname}** with channel **{discordchannel}**")

# find FC based on shortname
@bot.command(name='findlong', help='Find a carrier based on a partial match with any part of its full name\n'
                                   '\n'
                                   'Syntax: findshort <string>\n'
                                   '\n'
                                   'If there are multiple carriers with similar names, only the first on the list will return.')
async def findlong(ctx, looklong):
    defcarrier_findlong(looklong)
    await ctx.send(f"FC {p_ID} is **{longname} {cid}** called by shortname **{shortname}** with channel **{discordchannel}**")

# find FC based on ID
@bot.command(name='findid', help='Find a carrier based on its database ID\n'
                                 'Syntax: findid <integer>')
async def findid(ctx, lookid):
    defcarrier_findpid(lookid)
    await ctx.send(f"FC {p_ID} is **{longname} {cid}** called by shortname **{shortname}** with channel **{discordchannel}**")

# find commodity
@bot.command(name='findcomm', help='Find a commodity based on a search term\n'
                                   'Any term which has multiple partial matches will return the first result.\n'
                                   'In this case make your term more specific.\n'
                                   'e.g. searching for "plat" will return Reinforced Mounting Plate as it\'s higher up the list.\n'
                                   'To find Platinum, you\'d have to type at least "plati".')
async def findshort(ctx, lookfor):
    defcomm_find(lookfor)
    await ctx.send(f"Commodity {commodity} avgsell {avgsell} avgbuy {avgbuy} maxsell {maxsell} minbuy {minbuy} maxprofit {maxprofit}")

bot.run(TOKEN)
