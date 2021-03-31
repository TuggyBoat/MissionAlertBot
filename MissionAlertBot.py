# MissionAlertBot.py
# Discord bot to help PTN Carrier Owners post trade missions to Discord and Reddit
# By Charles Tosh 17 March 2021
# Additional contributions by Alexander Leidinger
# Discord Developer Portal: https://discord.com/developers/applications/822146046934384640/information
# Git repo: https://github.com/cimspin/MissionAlertBot

from PIL import Image, ImageFont, ImageDraw
import os
import sys
import discord
import sqlite3
import asyncpraw
import asyncio
import shutil
from dotenv import load_dotenv
from discord.ext import commands
from datetime import datetime
from datetime import timezone

#
#                       INIT STUFF
#

# load Discord token from .env - allows bot to connect to Discord
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

# setting some variables
# reddit flair IDs - testing sub
#flair_mission_start="3cbb1ab6-8e8e-11eb-93a1-0e0f446bc1b7"
#flair_mission_stop="4242a2e2-8e8e-11eb-b443-0e664851dbff"
# reddit flair IDs - main sub
flair_mission_start="d01e6808-9235-11eb-9cc0-0eb650439ee7"
flair_mission_stop="eea2d818-9235-11eb-b86f-0e50eec082f5"
# trade alerts channel ID for PTN main server
trade_alerts_id = 801798469189763073
# trade alerts channel ID for PTN test server
#trade_alerts_id = 824383348628783144
# subreddit for testing
#to_subreddit = "PTNBotTesting"
# subreddit for live
to_subreddit = "PilotsTradeNetwork"
embed_colour_loading = 0x80ffff # blue
embed_colour_unloading = 0x80ff80 # green
embed_color_reddit = 0xff0000 # red
embed_color_discord = 0x8080ff # purple
embed_color_rp = 0xff00ff # pink
embed_color_error = 0x800000 # dark red
embed_color_qu = 0x80ffff # same as loading
embed_color_ok = 0x80ff80 # same as unloading

# create reddit instance
reddit = asyncpraw.Reddit('bot1')

# connect to sqlite carrier database
conn = sqlite3.connect('carriers.db') 
conn.row_factory = sqlite3.Row
c = conn.cursor()

# connect to sqlite missions database
conm = sqlite3.connect('missions.db')
conm.row_factory = sqlite3.Row
cm = conm.cursor()





#
#                       DATABASE STUFF
#

# create carrier record if necessary (only needed on first run)
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
            discordchannel TEXT NOT NULL,
            channelid INT 
        ) 
    ''')

# create missions db if necessary
def table_exists(table_name): 
    cm.execute('''SELECT count(name) FROM sqlite_master WHERE TYPE = 'table' AND name = '{}' '''.format(table_name)) 
    if cm.fetchone()[0] == 1: 
        return True 
    return False

if not table_exists('missions'): 
    conm.execute('''
        CREATE TABLE missions(
            "carrier"	TEXT NOT NULL UNIQUE,
            "cid"	TEXT,
            "channelid"	INTEGER,
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

# function to add carrier, being sure to correct case
def defcarrier_add(shortname, longname, cid, discordchannel, channelid): 
    c.execute(''' INSERT INTO carriers VALUES(NULL, ?, ?, ?, ?, ?) ''', (shortname.lower(), longname.upper(), cid.upper(), discordchannel.lower(), channelid)) 
    conn.commit()
    # copy the blank bitmap to the new carrier's name to serve until unique image uploaded
    shutil.copy('bitmap.png', f'images/{shortname.lower()}.png')
    # os.system(f'cp bitmap.png images/{shortname}.png')

# function to remove a carrier
def defcarrier_del(p_ID):
    c.execute(f"DELETE FROM carriers WHERE p_ID = {p_ID}")
    conn.commit()
    defget_datetime()
    # archive the removed carrier's image by appending date and time of deletion to it
    shutil.move(f'images/{shortname}.png', f'images/old/{shortname}.{dt_file_string}.png')
    #os.system(f'mv {shortname}.png {shortname}.{dt_file_string}.png')

# function to remove all carriers, not currently used by any bot command
def defdelete_all_carriers(): 
    c.execute(f"DELETE FROM carriers") 
    conn.commit()

# function to search for a carrier by longname
def defcarrier_findlong(looklong):
    c.execute(f"SELECT p_ID, shortname, longname, cid, discordchannel, channelid FROM carriers WHERE longname LIKE (?)", ('%'+looklong+'%',))
    result = c.fetchone()
    global p_ID, shortname, longname, cid, discordchannel, channelid
    p_ID, shortname, longname, cid, discordchannel, channelid = result['p_ID'],result['shortname'],result['longname'],result['cid'],result['discordchannel'],result['channelid']
    print(f"FC {p_ID} is {longname} {cid} called by shortname {shortname} with channel <#{channelid}>")

# function to search for a carrier by shortname
def defcarrier_findshort(lookshort):
    c.execute(f"SELECT p_ID, shortname, longname, cid, discordchannel FROM carriers WHERE shortname LIKE (?)", ('%'+lookshort+'%',))
    result = c.fetchone()
    global p_ID, shortname, longname, cid, discordchannel, channelid
    p_ID, shortname, longname, cid, discordchannel, channelid = result['p_ID'],result['shortname'],result['longname'],result['cid'],result['discordchannel'],result['channelid']
    print(f"FC {p_ID} is {longname} {cid} called by shortname {shortname} with channel <#{channelid}>")

# function to search for a carrier by p_ID
def defcarrier_findpid(lookid):
    c.execute(f"SELECT p_ID, shortname, longname, cid, discordchannel FROM carriers WHERE p_ID = {lookid}")
    result = c.fetchone()
    global p_ID, shortname, longname, cid, discordchannel, channelid
    p_ID, shortname, longname, cid, discordchannel, channelid = result['p_ID'],result['shortname'],result['longname'],result['cid'],result['discordchannel'],result['channelid']
    print(f"FC {p_ID} is {longname} {cid} called by shortname {shortname} with channel <#{channelid}>")

# function to search for a commodity by name or partial name
def defcomm_find(lookfor):
    c.execute(f"SELECT commodity, avgsell, avgbuy, maxsell, minbuy, maxprofit FROM commodities WHERE commodity LIKE (?)", ('%'+lookfor+'%',))
    result = c.fetchone()
    global commodity, avgsell, avgbuy, maxsell, minbuy, maxprofit
    commodity, avgsell, avgbuy, maxsell, minbuy, maxprofit = result['commodity'],result['avgsell'],result['avgbuy'],result['maxsell'],result['minbuy'],result['maxprofit']
    print(f"Commodity {commodity} avgsell {avgsell} avgbuy {avgbuy} maxsell {maxsell} minbuy {minbuy} maxprofit {maxprofit}")


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
def defget_datetime():
    dt_now = datetime.now(tz=timezone.utc)
    global dt_string, dt_file_string
    dt_string = dt_now.strftime("%d %B" + " 3307" + " %H%M")
    dt_file_string = dt_now.strftime("%Y%m%d %H%M%S")

# function to create image for loading
def defcreateimage_load(carriername, carrierreg, commodity, system, station, profit, pads, demand):
    my_image = Image.open(f"images/{shortname}.png")
    image_editable = ImageDraw.Draw(my_image)
    image_editable.text((27,150), "PILOTS TRADE NETWORK", (255, 255, 255), font=title_font)
    image_editable.text((27,180), "CARRIER LOADING MISSION", (191, 53, 57), font=title_font)
    image_editable.text((27,235), "FLEET CARRIER " + cid, (0, 217, 255), font=reg_font)
    image_editable.text((27,250), longname, (0, 217, 255), font=name_font)
    image_editable.text((27,320), "COMMODITY:", (255, 255, 255), font=field_font)
    image_editable.text((150,320), commodity.upper(), (255, 255, 255), font=normal_font)
    image_editable.text((27,360), "SYSTEM:", (255, 255, 255), font=field_font)
    image_editable.text((150,360), system.upper(), (255, 255, 255), font=normal_font)
    image_editable.text((27,400), "STATION:", (255, 255, 255), font=field_font)
    image_editable.text((150,400), f"{station.upper()} ({pads.upper()})", (255, 255, 255), font=normal_font)
    image_editable.text((27,440), "PROFIT:", (255, 255, 255), font=field_font)
    image_editable.text((150,440), f"{profit}k per unit, {demand} units", (255, 255, 255), font=normal_font)
    my_image.save("result.png")

# function to create image for unloading
def defcreateimage_unload(carriername, carrierreg, commodity, system, station, profit, pads, demand):
    my_image = Image.open(f"images/{shortname}.png")
    image_editable = ImageDraw.Draw(my_image)
    image_editable.text((27,150), "PILOTS TRADE NETWORK", (255, 255, 255), font=title_font)
    image_editable.text((27,180), "CARRIER UNLOADING MISSION", (191, 53, 57), font=title_font)
    image_editable.text((27,235), "FLEET CARRIER " + cid, (0, 217, 255), font=reg_font)
    image_editable.text((27,250), longname, (0, 217, 255), font=name_font)
    image_editable.text((27,320), "COMMODITY:", (255, 255, 255), font=field_font)
    image_editable.text((150,320), commodity.upper(), (255, 255, 255), font=normal_font)
    image_editable.text((27,360), "SYSTEM:", (255, 255, 255), font=field_font)
    image_editable.text((150,360), system.upper(), (255, 255, 255), font=normal_font)
    image_editable.text((27,400), "STATION:", (255, 255, 255), font=field_font)
    image_editable.text((150,400), f"{station.upper()} ({pads.upper()})", (255, 255, 255), font=normal_font)
    image_editable.text((27,440), "PROFIT:", (255, 255, 255), font=field_font)
    image_editable.text((150,440), f"{profit}k per unit, {demand} units", (255, 255, 255), font=normal_font)
    my_image.save("result.png")



#
#                       TEXT GEN FUNCTIONS
#

def txt_create_discord(mission_type, commodity, station, system, profit, pads, demand, eta_text):
    global discord_text
    if mission_type == 'load':
        discord_text=(f"<#{channelid}> loading {commodity} from **{station.upper()}** station in system **{system.upper()}** : {profit}k per unit profit : {demand} demand : {pads.upper()}-pads.{eta_text}")
    else:
        discord_text=(f"<#{channelid}> unloading {commodity} to **{station.upper()}** station in system **{system.upper()}** : {profit}k per unit profit : {demand} supply : {pads.upper()}-pads.{eta_text}")
    
    return discord_text

def txt_create_reddit_title():
    global reddit_title
    reddit_title=(f"P.T.N. News - Trade mission - {longname} {cid} - {dt_string} UTC")
    
    return reddit_title

def txt_create_reddit_body(mission_type, commodity, station, system, profit, pads, demand, eta_text):
    global reddit_body
    if mission_type == 'load': 
        reddit_body=(f"    INCOMING WIDEBAND TRANSMISSION: P.T.N. CARRIER UNLOADING MISSION IN PROGRESS\n\n**BUY FROM**: station **{station.upper()}** in system **{system.upper()}** ({pads.upper()}-pads)\n\n**COMMODITY**: {commodity}\n\n&#x200B;\n\n**SELL TO**: Fleet Carrier **{longname} {cid}{eta_text}**\n\n**PROFIT**: {profit}k/unit : {demand} demand\n\n\n\n[Join us on Discord](https://www.reddit.com/r/PilotsTradeNetwork/comments/l0y7dk/pilots_trade_network_intergalactic_discord_server/) for mission updates and discussion, channel **#{discordchannel}**.")
    else:
        reddit_body=(f"    INCOMING WIDEBAND TRANSMISSION: P.T.N. CARRIER UNLOADING MISSION IN PROGRESS\n\n**BUY FROM**: Fleet Carrier **{longname} {cid}{eta_text}**\n\n**COMMODITY**: {commodity}\n\n&#x200B;\n\n**SELL TO**: station **{station.upper()}** in system **{system.upper()}** ({pads.upper()}-pads)\n\n**PROFIT**: {profit}k/unit : {demand} supply\n\n\n\n[Join us on Discord](https://www.reddit.com/r/PilotsTradeNetwork/comments/l0y7dk/pilots_trade_network_intergalactic_discord_server/) for mission updates and discussion, channel **#{discordchannel}**.")
    return reddit_body

def txt_create_reddit_info():
	return discord.Embed(title=f"Mission Generation Complete for {longname}", description="Paste Reddit content into **MARKDOWN MODE** in the editor. You can swap back to Fancy Pants afterwards and make any changes/additions or embed the image.\n\nBest practice for Reddit is an image post with a top level comment that contains the text version of the advert. This ensures the image displays with highest possible compatibility across platforms and apps. When mission complete, flag the post as *Spoiler* to prevent image showing and add a comment to inform.", color=embed_color_ok)



#
#                       OTHER
#

# function to stop and quit
def defquit():
    sys.exit("User requested exit.")


#
#                       BOT STUFF STARTS HERE
#

bot = commands.Bot(command_prefix='m.')

@bot.event
async def on_ready():
    print(f'{bot.user.name} has connected to Discord!')

#
#                       LOAD/UNLOAD COMMANDS
#

# load commands
@bot.command(name='load', help='Generate details for a loading mission and optionally broadcast to Discord.\n'
                               '\n'
                               '<lookname> is the carrier\'s shortname.\n'
                               '<commshort> is the commodity shortened to anything that will still successfully search, e.g. agro\n'
                               '<system> should be in quotes\n'
                               '<station> should also be in quotes\n'
                               '<profit> is a number of thousands without the k\n'
                               '<pads> is the largest pad size available (M for outposts, L for everything else)'
                               '<demand> is how much your carrier is buying'
                               '\n'
                               'Case is automatically corrected for all inputs.')
@commands.has_role('Carrier Owner')
async def load(ctx, lookname, commshort, system, station, profit, pads, demand, eta=None):
    rp = False
    mission_type = 'load'
    await gen_mission(ctx, lookname, commshort, system, station, profit, pads, demand, rp, mission_type, eta)

@bot.command(name="loadrp", help='Same as load command but prompts user to enter roleplay text\n'
                                'This is added to the Reddit comment as as a quote above the mission details\n'
                                'and sent to the carrier\'s Discord channel in quote format if those options are chosen')
@commands.has_role('Carrier Owner')
async def loadrp(ctx, lookname, commshort, system, station, profit, pads, demand, eta=None):
    rp = True
    mission_type = 'load'
    await gen_mission(ctx, lookname, commshort, system, station, profit, pads, demand, rp, mission_type, eta)

# unload commands
@bot.command(name='unload', help='Generate details for an unloading mission.\n'
                                 '\n'
                                 '<lookname> is the carrier\'s shortname.\n'
                                 '<commshort> is the commodity shortened to anything that will still successfully search, e.g. agro\n'
                                 '<system> should be in quotes\n'
                                 '<station> should also be in quotes\n'
                                 '<profit> is a number of thousands without the k\n'
                                 '<pads> is the largest pad size available (M for outposts, L for everything else)'
                                 '<demand> is how much your carrier is buying'
                                 '\n'
                                 'Case is automatically corrected for all inputs.')
@commands.has_role('Carrier Owner')
async def unload(ctx, lookname, commshort, system, station, profit, pads, demand, eta=None):
    rp = False
    mission_type = 'unload'
    await gen_mission(ctx, lookname, commshort, system, station, profit, pads, demand, rp, mission_type, eta)


@bot.command(name="unloadrp", help='Same as unload command but prompts user to enter roleplay text\n'
                                'This is added to the Reddit comment as as a quote above the mission details\n'
                                'and sent to the carrier\'s Discord channel in quote format if those options are chosen')
@commands.has_role('Carrier Owner')
async def unloadrp(ctx, lookname, commshort, system, station, profit, pads, demand, eta=None):
    rp = True
    mission_type = 'unload'
    await gen_mission(ctx, lookname, commshort, system, station, profit, pads, demand, rp, mission_type, eta)


# mission generator called by loading/unloading commands
async def gen_mission(ctx, lookname, commshort, system, station, profit, pads, demand, rp, mission_type, eta):

    rp_text = reddit_post_id = reddit_post_url = reddit_comment_id = reddit_comment_url = discord_alert_id = "NULL"
    eta_text = f" (ETA {eta} minutes)" if eta else ""
        
    embed=discord.Embed(title="Generating and fetching mission alerts...", color=embed_color_qu)
    message_gen = await ctx.send(embed=embed)

    cm.execute(f'''SELECT carrier FROM missions WHERE carrier LIKE (?)''', ('%'+lookname+'%',))
    result = cm.fetchone()
    if result:
        embed=discord.Embed(title="Error", description=f"{result['carrier']} is already on a mission, please use **m.done** to mark it complete before starting a new mission.", color=embed_color_error)
        await ctx.send(embed=embed)
        return
    
    def check(msg):
        return msg.author == ctx.author and msg.channel == ctx.channel

    if rp:
        embed=discord.Embed(title="Input roleplay text", description="Roleplay text is sent in quote style like this:\n\n> This is a quote!\n\nYou can use all regular Markdown formatting. If the \"send to Discord\" option is chosen, your quote will be broadcast to your carrier's channel following its mission image. If the \"send to Reddit\" option is chosen, the quote is inserted above the mission details in the top-level comment.", color=embed_color_rp)
        message_rp = await ctx.send(embed=embed)

        try:

            message_rp_text = await bot.wait_for("message", check=check, timeout=120)
            rp_text = message_rp_text.content

        except asyncio.TimeoutError:
            await ctx.send("**Mission generation cancelled (waiting too long for user input)**")
            await message_rp.delete()
            return


    # generate the mission elements
    defcomm_find(commshort)
    defcarrier_findlong(lookname)
    if mission_type == 'load':
        defcreateimage_load(longname, cid, commodity, system, station, profit, pads, demand)
    else:
        defcreateimage_unload(longname, cid, commodity, system, station, profit, pads, demand)
    defget_datetime()
    txt_create_discord(mission_type, commodity, station, system, profit, pads, demand, eta_text)
    txt_create_reddit_title()
    txt_create_reddit_body(mission_type, commodity, station, system, profit, pads, demand, eta_text)
    
    # check they're happy with output and offer to send
    embed=discord.Embed(title=f"Mission pending for {longname}{eta_text}", color=embed_color_ok)
    embed.add_field(name="Mission type", value=f"{mission_type.title()}ing", inline=True)
    embed.add_field(name="Commodity", value=f"{demand} of {commodity.title()} at {profit}k/unit", inline=True)
    embed.add_field(name="Location", value=f"{station.upper()} station in system {system.upper()} with {pads.upper()}-pads", inline=True)
    if rp:
        await message_rp.delete()
        await message_rp_text.delete()
        embed.add_field(name="Roleplay text",value=rp_text, inline=False)
    message_pending = await ctx.send(embed=embed)
    await message_gen.delete()
    
    embed=discord.Embed(title="Where would you like to send the alert?", description="(**d**)iscord, (**r**)eddit, (**t**)ext for copy/pasting or e(**x**)it and cancel", color=embed_color_qu)
    embed.set_footer(text="Enter all that apply, e.g. **drt** will print text and send alerts to Discord and Reddit.")
    message_confirm = await ctx.send(embed=embed)

    try:
        msg = await bot.wait_for("message", check=check, timeout=30)

        if "x" in msg.content.lower():
            # immediately stop if there's an x anywhere in the message, even if there are other proper inputs
            message_cancelled = await ctx.send("**Broadcast cancelled.**")
            await msg.delete()
            await message_confirm.delete()
            return

        if "t" in msg.content.lower():

            embed=discord.Embed(title="Trade Alert (Discord)", description=f"`{discord_text}`", color=embed_color_discord)
            await ctx.send(embed=embed)
            if rp:
                embed=discord.Embed(title="Roleplay Text (Discord)", description=f"`> {rp_text}`", color=embed_color_discord)
                await ctx.send(embed=embed)

            embed=discord.Embed(title="Reddit Post Title", description=f"`{reddit_title}`", color=embed_color_reddit)
            await ctx.send(embed=embed)
            if rp:
                embed=discord.Embed(title="Reddit Post Body - PASTE INTO MARKDOWN MODE", description=f"```> {rp_text}\n\n{reddit_body}```", color=embed_color_reddit)
            else:
                embed=discord.Embed(title="Reddit Post Body - PASTE INTO MARKDOWN MODE", description=f"```{reddit_body}```", color=embed_color_reddit)
            embed.set_footer(text="**REMEMBER TO USE MARKDOWN MODE WHEN PASTING TEXT TO REDDIT.**")
            await ctx.send(embed=embed)
            await ctx.send(file=discord.File('result.png'))
            embed=discord.Embed(title=f"Mission Generation Complete for {longname}", description="Paste Reddit content into **MARKDOWN MODE** in the editor. You can swap back to Fancy Pants afterwards and make any changes/additions or embed the image.\n\nBest practice for Reddit is an image post with a top level comment that contains the text version of the advert. This ensures the image displays with highest possible compatibility across platforms and apps. When mission complete, flag the post as *Spoiler* to prevent image showing and add a comment to inform.", color=embed_color_ok)
            await ctx.send(embed=embed)

        if "d" in msg.content.lower():
            message_send = await ctx.send("**Sending to Discord...**")

            # send trade alert to trade alerts channel
            channel = bot.get_channel(trade_alerts_id)


            if mission_type == 'load':
                embed=discord.Embed(description=discord_text, color=embed_colour_loading)
            else:
                embed=discord.Embed(description=discord_text, color=embed_colour_unloading)
            # old footer hashed out but can be used if desired
            #embed.set_footer(text="Add a reaction to show you're working this mission! React with 💯 if loading is complete.")
            trade_alert_msg = await channel.send(embed=embed)
            discord_alert_id = trade_alert_msg.id

            channel = bot.get_channel(channelid)
            #channel = bot.get_channel(824383348628783144) # this for TEST SERVER only
            file = discord.File("result.png", filename="image.png")
            if mission_type == 'load':
                if rp:
                    embed=discord.Embed(title="P.T.N TRADE MISSION STARTING", description=f"> {rp_text}", color=embed_colour_loading)
                else:
                    embed=discord.Embed(title="P.T.N TRADE MISSION STARTING", color=embed_colour_loading)

            else:
                if rp:
                    embed=discord.Embed(title="P.T.N TRADE MISSION STARTING", description=f"> {rp_text}", color=embed_colour_unloading)
                else:
                    embed=discord.Embed(title="P.T.N TRADE MISSION STARTING", color=embed_colour_unloading)
            embed.set_image(url="attachment://image.png")
            embed.set_footer(text="m.complete will mark this mission complete\nm.ission will display info to channel\nm.issions will list trade missions for all carriers.")
            await channel.send(file=file, embed=embed)
            
            
            embed=discord.Embed(title=f"Discord trade alerts sent for {longname}", description=f"Check <#{trade_alerts_id}> for trade alert and <#{channelid}> for image.", color=embed_color_discord)
            await ctx.send(embed=embed)
            await message_send.delete()

        if "r" in msg.content.lower():
            message_send = await ctx.send("**Sending to Reddit...**")

            # post to reddit
            flair_id=flair_mission_start
            subreddit = await reddit.subreddit(to_subreddit)
            submission = await subreddit.submit_image(reddit_title, image_path="result.png", flair_id=flair_id)
            reddit_post_url = submission.permalink
            reddit_post_id = submission.id
            if rp:
                comment = await submission.reply(f"> {rp_text}\n\n&#x200B;\n\n{reddit_body}")
            else:
                comment = await submission.reply(reddit_body)
            reddit_comment_url = comment.permalink
            reddit_comment_id = comment.id
            embed=discord.Embed(title=f"Reddit trade alert sent for {longname}", description=f"https://www.reddit.com{reddit_post_url}", color=embed_color_reddit)
            await ctx.send(embed=embed)
            await message_send.delete()
        
    except asyncio.TimeoutError:
        await ctx.send("**Mission did not broadcast (no valid response from user).**")
        return

    # now clear up by deleting the prompt message and user response
    await msg.delete()
    await message_confirm.delete()
    await mission_add(ctx, longname, cid, channelid, commodity, mission_type, system, station, profit, pads, demand, rp_text, reddit_post_id, reddit_post_url, reddit_comment_id, reddit_comment_url, discord_alert_id, rp, message_pending, eta_text)
    



#
#                       DIRECT TO CHANNEL COMMANDS (deprecated, merged with normal load/unload commands)
#

# load direct to channel
@bot.command(name='loadsend', help='Deprecated, now identical to m.load.')
@commands.has_role('Carrier Owner')
async def loadsend(ctx, lookname, commshort, system, station, profit, pads, demand, eta=None):
    await load(ctx, lookname, commshort, system, station, profit, pads, demand, eta=None)


# unload direct to channel
@bot.command(name='unloadsend', help='Deprecated, now identical to m.unload.')
@commands.has_role('Carrier Owner')
async def unloadsend(ctx, lookname, commshort, system, station, profit, pads, demand, eta=None):
    await unload(ctx, lookname, commshort, system, station, profit, pads, demand, eta=None)

#
#                       MISSION DB
#


# add mission to DB, called from mission generator
async def mission_add(ctx, longname, cid, channelid, commodity, mission_type, system, station, profit, pads, demand, rp_text, reddit_post_id, reddit_post_url, reddit_comment_id, reddit_comment_url, discord_alert_id, rp, message_pending, eta_text):
    cm.execute(''' INSERT INTO missions VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?) ''', (longname, cid, channelid, commodity.title(), mission_type.lower(), system.title(), station.title(), profit, pads.upper(), demand, rp_text, reddit_post_id, reddit_post_url, reddit_comment_id, reddit_comment_url, discord_alert_id))
    conm.commit()
    if mission_type == 'load':
        embed=discord.Embed(title=f"Mission now in progress for {longname}{eta_text}", description="Use **m.done** to mark complete and **m.issions** to list all active missions.", color=embed_colour_loading)
    else:
        embed=discord.Embed(title=f"Mission now in progress for {longname}{eta_text}", description="Use **m.done** to mark complete and **m.issions** to list all active missions.", color=embed_colour_unloading)
    file = discord.File("result.png", filename="image.png")
    embed.set_image(url="attachment://image.png")
    embed.add_field(name="Type", value=f"{mission_type.title()}ing", inline=True)
    embed.add_field(name="Commodity", value=f"{demand} of {commodity.title()} at {profit}k/unit", inline=True)
    embed.add_field(name="Location", value=f"{station.upper()} station in system {system.upper()} with {pads.upper()}-pads", inline=True)
    embed.set_footer(text="Remember to use m.done when mission is complete.")
    if rp:
        embed.add_field(name="Roleplay text",value=rp_text, inline=False)
    message_in_progress = await ctx.send(file=file, embed=embed)
    await message_pending.delete()
    
# list active carrier trade mission from DB
@bot.command(name='ission', help='Show carrier\'s active trade mission.')
async def ission(ctx):
# take a note channel ID
    msg_ctx_id = ctx.channel.id
    # look for a match for the channel ID in the carrier DB
    c.execute(f"SELECT longname, cid FROM carriers WHERE channelid = {msg_ctx_id}")
    result = c.fetchone()
    if not result:
        # if there's no channel match, return an error
        embed=discord.Embed(description="Try again in the carrier's channel.", color=embed_color_qu)
        await ctx.send(embed=embed)
        return
    else:
        carrier, cid = result['longname'], result['cid']
        # now look to see if the carrier is on an active mission
        cm.execute('''SELECT * FROM missions WHERE carrier LIKE (?)''', ('%'+carrier+'%',))
        result = cm.fetchone()
        if not result:
            # if there's no result, return an error
            embed=discord.Embed(description=f"**{carrier}** doesn't seem to be on a trade mission right now.", color=embed_color_ok)
            await ctx.send(embed=embed)
        else:
            # user is in correct channel and carrier is on a mission, so show the current trade mission for selected carrier
            carrier, commodity, missiontype, system, station, profit, pads, demand, rp_text = result['carrier'], result['commodity'], result['missiontype'], result['system'], result['station'], result['profit'], result['pad'], result['demand'], result['rp_text']
            if missiontype == 'load':
                if rp_text == 'NULL':
                    embed=discord.Embed(title=f"{carrier} ({cid}) on LOADING mission", color=embed_colour_loading)
                else:
                    embed=discord.Embed(title=f"{carrier} ({cid}) on LOADING mission", description=f"> {rp_text}", color=embed_colour_loading)
            else:
                if rp_text == 'NULL':
                    embed=discord.Embed(title=f"{carrier} ({cid}) on UNLOADING mission", color=embed_colour_unloading)
                else:
                    embed=discord.Embed(title=f"{carrier} ({cid}) on UNLOADING mission", description=f"> {rp_text}", color=embed_colour_unloading)
            embed.add_field(name=f"{system.upper()}", value="*System*", inline=True)
            embed.add_field(name=f"{station.upper()} ({pads}-pads)", value="*Station*", inline=True)
            embed.add_field(name=f"{commodity.upper()}", value="*Commodity*", inline=True)
            embed.add_field(name=f"{demand} units at {profit}k profit per unit", value="*Quantity and profit*", inline=True)
            embed.set_footer(text="You can use m.complete if the mission is complete.")

            await ctx.send(embed=embed)
            return

# list all active carrier trade missions from DB
@bot.command(name='issions', help='List all active trade missions.')
async def issions(ctx):
    cm.execute('''SELECT * FROM missions WHERE missiontype="load";''')
    records = cm.fetchall()
    embed=discord.Embed(title=f"{len(records)} P.T.N Fleet Carrier LOADING missions in progress:", color=embed_colour_loading)
    for row in records:
        embed.add_field(name=f"{row[0]}", value=f"<#{row[2]}>", inline=True)
        embed.add_field(name=f"{row[3]}", value=f"{row[9]} at {row[7]}k/unit", inline=True)
        embed.add_field(name=f"{row[5].upper()} system", value=f"{row[6]} ({row[8]}-pads)", inline=True)
    await ctx.send(embed=embed)
    cm.execute('''SELECT * FROM missions WHERE missiontype="unload";''')
    records = cm.fetchall()
    embed=discord.Embed(title=f"{len(records)} P.T.N Fleet Carrier UNLOADING missions in progress:", color=embed_colour_unloading)
    for row in records:
        embed.add_field(name=f"{row[0]}", value=f"<#{row[2]}>", inline=True)
        embed.add_field(name=f"{row[3]}", value=f"{row[9]} at {row[7]}k/unit", inline=True)
        embed.add_field(name=f"{row[5].upper()} system", value=f"{row[6]} ({row[8]}-pads)", inline=True)
    await ctx.send(embed=embed)

# CO command to quickly mark mission as complete, optionally send some RP text
@bot.command(name='done', help='Marks a mission as complete for specified carrier.\n'
                               'Deletes trade alert in Discord and sends messages to carrier channel and reddit if appropriate.\n\n'
                               'Anything put in quotes after the carrier name will be treated as a quote to be sent along with the completion notice. This can be used for RP if desired.')
@commands.has_role('Carrier Owner')
async def done(ctx, lookname, rp=None):
    cm.execute(f'''SELECT * FROM missions WHERE carrier LIKE (?)''', ('%'+lookname+'%',))
    result = cm.fetchone()
    if not result:
        embed=discord.Embed(description=f"**ERROR**: no trade missions found for carriers matching \"**{lookname}\"**.", color=embed_color_error)
        await ctx.send(embed=embed)   

    else:
        # fill in some info for messages
        carrier = result['carrier']
        desc_msg = f"> {rp}\n\n" if rp else ""
                
        # delete Discord trade alert
        if not result['discord_alert_id'] == 'NULL':
            try: # try in case it's already been deleted, which doesn't matter to us in the slightest but we don't want it messing up the rest of the function
                discord_alert_id = result['discord_alert_id']
                channel = bot.get_channel(trade_alerts_id)
                msg = await channel.fetch_message(discord_alert_id)
                await msg.delete()
            except:
                print("Looks like this mission alert was already deleted by someone else")

        # send Discord carrier channel updates
            channelid = result['channelid']
            channel = bot.get_channel(channelid)
            embed=discord.Embed(title=f"{carrier} MISSION COMPLETE", description=f"{desc_msg}", color=embed_color_ok)
            await channel.send(embed=embed)
        
        # add comment to Reddit post
        if not result['reddit_post_id'] == 'NULL':
            reddit_post_id = result['reddit_post_id']
            subreddit = await reddit.subreddit(to_subreddit)
            submission = await reddit.submission(reddit_post_id)
            await submission.reply(f"    INCOMING WIDEBAND TRANSMISSION: P.T.N. CARRIER MISSION UPDATE\n\n**{carrier}** mission complete. o7 CMDRs!\n\n{desc_msg}")

        # mark original post as spoiler, change its flair
            await submission.flair.select(flair_mission_stop)
            await submission.mod.spoiler()
        
        # delete mission entry from db
        cm.execute(f'''DELETE FROM missions WHERE carrier LIKE (?)''', ('%'+lookname+'%',))
        conm.commit()
        
        embed=discord.Embed(title=f"Mission complete for {carrier}", description=f"{desc_msg}Updated any sent alerts and removed from mission list.", color=embed_color_ok)
        await ctx.send(embed=embed)
        return



# a command for users to mark a carrier mission complete from within the carrier channel
@bot.command(name='complete', help='Use in a carrier\'s channel to mark the current trade mission complete.')
async def complete(ctx):
    # take a note of user and channel ID
    msg_ctx_id = ctx.channel.id
    msg_usr_id = ctx.author.id
    # look for a match for the channel ID in the carrier DB
    c.execute(f"SELECT longname FROM carriers WHERE channelid = {msg_ctx_id}")
    result = c.fetchone()
    if not result:
        # if there's no channel match, return an error
        embed=discord.Embed(description="**You need to be in a carrier's channel to mark its mission as complete.**", color=embed_color_error)
        await ctx.send(embed=embed)
        return
    else:
        carrier = result['longname']
        # now look to see if the carrier is on an active mission
        cm.execute('''SELECT * FROM missions WHERE carrier LIKE (?)''', ('%'+carrier+'%',))
        result = cm.fetchone()
        if not result:
            # if there's no result, return an error
            embed=discord.Embed(description=f"**{carrier} doesn't seem to be on a trade mission right now.**", color=embed_color_error)
            await ctx.send(embed=embed)
        else:
            # user is in correct channel and carrier is on a mission, so check whether user is sure they want to proceed
            carrier_mission, station, missiontype = result['carrier'], result['station'], result['missiontype']
            embed=discord.Embed(description=f"Please confirm that **{carrier}** has been fully {missiontype}ed : **y** / **n**", color=embed_color_qu)
            #embed.set_footer(text="For other issues (e.g. station price changes) please @ the Carrier Owner directly.")
            msg_confirm = await ctx.send(embed=embed)
            def check(msg):
                return msg.author == ctx.author and msg.channel == ctx.channel and \
                msg.content.lower() in ["y", "n"]

            try:
                msg = await bot.wait_for("message", check=check, timeout=30)
                if msg.content.lower() == "n":
                    embed=discord.Embed(description="OK, mission will remain listed as in-progress.", color=embed_color_ok)
                    await ctx.send(embed=embed)
                    return
                elif msg.content.lower() == "y":
                    embed=discord.Embed(title=f"{carrier} MISSION COMPLETE", description=f"<@{msg_usr_id}> reports that mission is complete!", color=embed_color_ok)
                    await ctx.send(embed=embed)
                    # now we need to go do all the mission cleanup stuff

                    # delete Discord trade alert
                    if not result['discord_alert_id'] == 'NULL':
                        try:
                            discord_alert_id = result['discord_alert_id']
                            channel = bot.get_channel(trade_alerts_id)
                            msg = await channel.fetch_message(discord_alert_id)
                            await msg.delete()
                        except:
                            print("Looks like this mission alert was already deleted by someone else")

                    # add comment to Reddit post
                    if not result['reddit_post_id'] == 'NULL':
                        reddit_post_id = result['reddit_post_id']
                        subreddit = await reddit.subreddit(to_subreddit)
                        submission = await reddit.submission(reddit_post_id)
                        await submission.reply(f"    INCOMING WIDEBAND TRANSMISSION: P.T.N. CARRIER MISSION UPDATE\n\n**{carrier}** mission complete. o7 CMDRs!\n\n\n\n*Reported on PTN Discord by {ctx.author.display_name}*")

                    # mark original post as spoiler, change its flair
                        await submission.flair.select(flair_mission_stop)
                        await submission.mod.spoiler()

                    # delete mission entry from db
                    cm.execute(f'''DELETE FROM missions WHERE carrier LIKE (?)''', ('%'+carrier+'%',))
                    conm.commit()
                        

            except asyncio.TimeoutError:
                embed=discord.Embed(description="No response, mission will remain listed as in-progress.")
                await ctx.send(embed=embed)




                    




#
#                       UTILITY COMMANDS
#

# list FCs
@bot.command(name='carrier_list', help='List all Fleet Carriers in the database.')
async def carrier_list(ctx):
    c.execute(f"SELECT * FROM carriers")
    records = c.fetchall()
    embed=discord.Embed(title=f"{len(records)} Registered Fleet Carriers")
    for row in records:
        embed.add_field(name=f"{row[0]}: {row[2]} ({row[3]})", value=f"<#{row[5]}>", inline=False)
    await ctx.send(embed=embed)


# add FC to database
@bot.command(name='carrier_add', help='Add a Fleet Carrier to the database:\n'
                                      '\n'
                                      '<shortname> should be a short one-word string as you\'ll be typing it a lot\n'
                                      '<longname> is the carrier\'s full name including P.T.N. etc - surround this with quotes.\n'
                                      '<cid> is the carrier\'s unique identifier in the format ABC-XYZ\n'
                                      '<discordchannel> is the carrier\'s discord channel in the format ptn-carriername\n'
                                      'do NOT include the # at the start of the channel name!')
@commands.has_role('Carrier Owner')
async def carrier_add(ctx, shortname, longname, cid, discordchannel):
    channel = discord.utils.get(ctx.guild.channels, name=discordchannel)
    channelid = channel.id
    defcarrier_add(shortname, longname, cid, discordchannel, channelid)
    defcarrier_findlong(longname)
    await ctx.send(f"Added **{longname.upper()}** **{cid.upper()}** with shortname **{shortname.lower()}** and channel **<#{channelid}>** at ID **{p_ID}**")

# remove FC from database
@bot.command(name='carrier_del', help='Delete a Fleet Carrier from the database using its ID.\n'
                                      'Use the findid command to check before deleting.')
@commands.has_role('Carrier Owner')
async def carrier_del(ctx, p_ID):
    defcarrier_del(p_ID)
    await ctx.send(f"Attempted to remove carrier number {p_ID}")

# change FC background image
@bot.command(name='carrier_image', help='Change the background image for the specified carrier.')
@commands.has_role('Carrier Owner')
async def carrier_image(ctx, lookname):
    defcarrier_findlong(lookname)
    defget_datetime()
    file = discord.File(f"images/{shortname}.png", filename="image.png")
    embed=discord.Embed(title=f"Change background image for {longname}", description="Please upload your image now. Images should be 500x500, in .png format, and based on the standard PTN image template. Or input **x** to cancel.", color=embed_color_qu)
    embed.set_image(url="attachment://image.png")
    message_upload_now = await ctx.send(file=file, embed=embed)
    def check(message):
        return message.author == ctx.author and message.channel == ctx.channel
    try:
        message = await bot.wait_for("message", check=check, timeout=30)
        if message.attachments:
            shutil.move(f'images/{shortname}.png', f'images/old/{shortname}.{dt_file_string}.png')
            for attachment in message.attachments:
                await attachment.save(f"images/{shortname}.png")
            file = discord.File(f"images/{shortname}.png", filename="image.png")
            embed=discord.Embed(title=f"{longname}", description="Background image updated.", color=embed_color_ok)
            embed.set_image(url="attachment://image.png")
            await ctx.send(file=file, embed=embed)
            await message.delete()
            await message_upload_now.delete()
        elif message.content.lower() == "x":
            await ctx.send("**Cancelled**")
            await message.delete()
            await message_upload_now.delete()
            return
    except asyncio.TimeoutError:
        await ctx.send("**Cancelled - timed out**")
        await message_upload_now.delete()
        return
        
    




# find FC based on shortname
@bot.command(name='findshort', help='Find a carrier based on its shortname.\n'
                               '\n'
                               'Syntax: findshort <string>\n'
                               '\n'
                               'Partial matches will work but only if they incorporate part of the shortname.\n'
                               'To find a carrier based on a match with part of its full name, use the findlong command.')
async def findshort(ctx, lookshort):
    try:
        defcarrier_findshort(lookshort)
        #await ctx.send(f"FC {p_ID} is **{longname} {cid}** called by shortname **{shortname}** with channel **#{discordchannel}**")
        embed=discord.Embed(title="Fleet Carrier Shortname Search Result", description=f"Displaying first match for {lookshort}", color=embed_color_ok)
        embed.add_field(name="Carrier Name", value=f"{longname}", inline=True)
        embed.add_field(name="Carrier ID", value=f"{cid}", inline=True)
        embed.add_field(name="Shortname", value=f"{shortname}", inline=True)
        embed.add_field(name="Discord Channel", value=f"#{discordchannel}", inline=True)
        embed.add_field(name="Database Entry", value=f"{p_ID}", inline=True)
        await ctx.send(embed=embed)
    except TypeError:
        await ctx.send(f'No result for {lookshort}.')

# find FC based on longname
@bot.command(name='find', help='Find a carrier based on a partial match with any part of its full name\n'
                                   '\n'
                                   'Syntax: find <string>\n'
                                   '\n'
                                   'If there are multiple carriers with similar names, only the first on the list will return.')
async def find(ctx, looklong):
    try:
        defcarrier_findlong(looklong)
        #await ctx.send(f"FC {p_ID} is **{longname} {cid}** called by shortname **{shortname}** with channel **#{discordchannel}**")
        embed=discord.Embed(title="Fleet Carrier Search Result", description=f"Displaying first match for {looklong}", color=embed_color_ok)
        embed.add_field(name="Carrier Name", value=f"{longname}", inline=True)
        embed.add_field(name="Carrier ID", value=f"{cid}", inline=True)
        embed.add_field(name="Shortname", value=f"{shortname}", inline=True)
        embed.add_field(name="Discord Channel", value=f"<#{channelid}>", inline=True)
        embed.add_field(name="Database Entry", value=f"{p_ID}", inline=True)
        await ctx.send(embed=embed)
    except TypeError:
        await ctx.send(f'No result for {looklong}.')

# find FC based on ID
@bot.command(name='findid', help='Find a carrier based on its database ID\n'
                                 'Syntax: findid <integer>')
async def findid(ctx, lookid):
    try:
        defcarrier_findpid(lookid)
        #await ctx.send(f"FC {p_ID} is **{longname} {cid}** called by shortname **{shortname}** with channel **{discordchannel}**")
        embed=discord.Embed(title="Fleet Carrier DB# Search Result", description=f"Displaying carrier with DB# {p_ID}", color=embed_color_ok)
        embed.add_field(name="Carrier Name", value=f"{longname}", inline=True)
        embed.add_field(name="Carrier ID", value=f"{cid}", inline=True)
        embed.add_field(name="Shortname", value=f"{shortname}", inline=True)
        embed.add_field(name="Discord Channel", value=f"#{discordchannel}", inline=True)
        embed.add_field(name="Database Entry", value=f"{p_ID}", inline=True)
        await ctx.send(embed=embed)
    except TypeError:
        await ctx.send(f'No result for {lookid}.')

# find commodity
@bot.command(name='findcomm', help='Find a commodity based on a search term\n'
                                   'Any term which has multiple partial matches will return the first result.\n'
                                   'In this case make your term more specific.\n'
                                   'e.g. searching for "plat" will return Reinforced Mounting Plate as it\'s higher up the list.\n'
                                   'To find Platinum, you\'d have to type at least "plati".')
async def findshort(ctx, lookfor):
    defcomm_find(lookfor)
    await ctx.send(f"Commodity {commodity} avgsell {avgsell} avgbuy {avgbuy} maxsell {maxsell} minbuy {minbuy} maxprofit {maxprofit}")

# ping the bot
@bot.command(name='ping', help='Ping the bot')
@commands.has_role('Carrier Owner')
async def ping(ctx):
    await ctx.send("**PING? PONG!**")

# quit the bot
@bot.command(name='stopquit', help='Stops the bot\'s process on the VM, ending all functions.')
@commands.has_role('Admin')
async def stopquit(ctx):
    await ctx.send(f"k thx bye")
    await defquit()

    

#
# error handling
#
@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.BadArgument):
        await ctx.send('**Bad argument!**')
    if isinstance(error, commands.CommandNotFound):
        await ctx.send("**Invalid command.**")
    if isinstance(error, commands.MissingRequiredArgument):
        await ctx.send('**Please include all required parameters.** Use m.help <command> for details.')
    if isinstance(error, commands.MissingPermissions):
        await ctx.send('**You must be a Carrier Owner to use this command.**')
    else:
        await ctx.send('Sorry, that didn\'t work. Check your syntax and permissions.')

bot.run(TOKEN)
