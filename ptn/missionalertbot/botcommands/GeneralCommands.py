"""
A Cog for general bot commands that don't fit in other categories.

Refactor Status: COMPLETE

"""

# libraries
import asyncio
from datetime import datetime, timezone
import random

# discord.py
import discord
from discord.ext import commands
from discord import app_commands

# local classes
from ptn.missionalertbot.classes.MissionData import MissionData

# local constants
from ptn.missionalertbot._metadata import __version__
import ptn.missionalertbot.constants as constants
from ptn.missionalertbot.constants import bot, bot_command_channel, bot_dev_channel, cmentor_role, certcarrier_role, \
    admin_role, dev_role, trade_alerts_channel, seconds_long, mod_role, cpillar_role, bot_spam_channel

# local modules
from ptn.missionalertbot.database.database import get_trade_channels_on_startup, backup_database, find_carrier, find_mission, _is_carrier_channel, \
    mission_db, carrier_db, carrier_db_lock, carriers_conn, find_nominator_with_id, delete_nominee_by_nominator, find_community_carrier, CCDbFields
from ptn.missionalertbot.modules.Embeds import _is_mission_active_embed, _format_missions_embed
from ptn.missionalertbot.modules.helpers import bot_exit, carrier_channel_lock, check_roles, check_command_channel, on_app_command_error
from ptn.missionalertbot.modules.BackgroundTasks import lasttrade_cron, _monitor_reddit_comments
from ptn.missionalertbot.modules.MissionGenerator import _cleanup_completed_mission, cleanup_trade_channel


"""
A primitive global error handler for text commands.

returns: error message to user and log
"""

@bot.listen()
async def on_command_error(ctx, error):
    gif = random.choice(constants.error_gifs)
    if isinstance(error, commands.BadArgument):
        await ctx.send(f'**Bad argument!** {error}')
        print({error})
    elif isinstance(error, commands.CommandNotFound):
        await ctx.send("**Invalid command.**")
        print({error})
    elif isinstance(error, commands.MissingRequiredArgument):
        print({error})
        await ctx.send("**Sorry, that didn't work**.\n• Check you've included all required arguments. Use `m.help <command>` for details."
                       "\n• If using quotation marks, check they're opened *and* closed, and are in the proper place.\n• Check quotation"
                       " marks are of the same type, i.e. all straight or matching open/close smartquotes.")
    elif isinstance(error, commands.MissingPermissions):
        print({error})
        await ctx.send('**You must be a Carrier Owner to use this command.**')
    else:
        await ctx.send(gif)
        print({error})
        await ctx.send(f"Sorry, that didn't work: {error}")


"""
GENERAL BOT COMMANDS

GENERAL - ADMIN ONLY
backup - admin/database
cron_status - admin
ping - admin
/greet - elevated roles
stopquit - admin
unlock_override - admin/missions

GENERAL - USER-FACING
ission - mission
issions - mission
complete - mission
/mission - mission
/missions - mission
/nominate - general/community
/nominate_remove - general/community
/notify_me - general/community

"""

class GeneralCommands(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # custom global error handler
    # attaching the handler when the cog is loaded
    # and storing the old handler
    # this is required for option 1
    def cog_load(self):
        tree = self.bot.tree
        self._old_tree_error = tree.on_error
        tree.on_error = on_app_command_error

    # detaching the handler when the cog is unloaded
    def cog_unload(self):
        tree = self.bot.tree
        tree.on_error = self._old_tree_error


    """
    LISTENERS

    """


    # processed when the bot connects to Discord
    @commands.Cog.listener()
    async def on_ready(self):
        print(f'{bot.user.name} has connected to Discord!')
        devchannel = bot.get_channel(bot_dev_channel())
        embed = discord.Embed(title="MISSION ALERT BOT ONLINE", description=f"<@{bot.user.id}> connected, version **{__version__}**.", color=constants.EMBED_COLOUR_OK)
        embed.set_image(url=random.choice(constants.hello_gifs))
        await devchannel.send(embed=embed)

        # define our background tasks
        reddit_task = asyncio.create_task(_monitor_reddit_comments())
        # Check if any trade channels were not deleted before bot restart/stop
        cleanup_channels = await get_trade_channels_on_startup()
        for channel in cleanup_channels:
            asyncio.create_task(cleanup_trade_channel(channel))
        # start the lasttrade_cron loop.
        await lasttrade_cron.start()
        # start monitoring reddit comments
        await reddit_task


    # processed on disconnect
    @commands.Cog.listener()
    async def on_disconnect(self):
        print(f'Mission Alert Bot has disconnected from discord server, version: {__version__}.')


    # pin listener
    @commands.Cog.listener()
    async def on_guild_channel_pins_update(self, channel, last_pin):
        print("on_guild_channel_pins_update triggered")
        """
        Delete the system message informing you a message was pinned in this channel
        Watches every public channel in the guild (discord)
        """
        async for msg in channel.history(limit=200):
            if msg.type is discord.MessageType.pins_add and msg.author == bot.user:
                print(f"Detected bot pin notification message in {channel.name}, deleting")
                await msg.delete()


    """
    ADMIN COMMANDS
    """


    # ping command
    @commands.command(name='ping', help='Ping the bot')
    @commands.has_any_role(*constants.any_elevated_role)
    async def ping(self, ctx):
        print(f"{ctx.author} used PING in {ctx.channel.name}")
        gif = random.choice(constants.hello_gifs)
        await ctx.send(gif)


    # greet slash command - same as ping but without visible interaction
    @app_commands.command(name="greet",
                          description="Ask the bot to send a greeting to the current channel.")
    @check_roles(constants.any_elevated_role)
    async def _greet(self, interaction: discord.Interaction):
        print(f"{interaction.user.name} used /greet in {interaction.channel}")
        await interaction.response.send_message("Ok, saying hi for you!", ephemeral=True)
        gif = random.choice(constants.hello_gifs)
        await interaction.channel.send(gif)


    # sync slash commands - must be done whenever the bot has appcommands added/removed
    @commands.command(name='sync', help='Synchronise bot interactions with server')
    @commands.has_any_role(*constants.any_elevated_role)
    async def sync(self, ctx):
        async with ctx.typing():
            try:
                bot.tree.copy_global_to(guild=constants.guild_obj)
                await bot.tree.sync(guild=constants.guild_obj)
                print("Synchronised bot tree.")
                await ctx.send("Synchronised bot tree.")
            except Exception as e:
                print(f"Tree sync failed: {e}.")
                return await ctx.send(f"Failed to sync bot tree: {e}")


    @commands.command(name='unlock_override', help='Unlock the channel lock manually after Sheriff Benguin breaks it.')
    @check_roles([admin_role(), dev_role()])
    async def unlock_override(self, ctx):

        print(f"{ctx.author} called manual channel_lock release in {ctx.channel}")
        if not carrier_channel_lock.locked():
            return await ctx.send("Channel lock is not set.")

        await ctx.send("Make sure nobody is using the Mission Generator before proceeding.")
        global deletion_in_progress

        # this global variable is set when the channel deletion function acquires its lock
        if deletion_in_progress:
            await ctx.send("Lock appears to be set from a channel deletion task underway. This usually takes ~10 seconds per channel."
                        " Please make sure no mission channels are about to be deleted. Deletion occurs 15 minutes after `m.complete`"
                        " or `m.done` or 2 minutes following using a mission generator command without generating a mission "
                        "(i.e. by error or user abort).")

        await ctx.send("Do you still want to proceed? **y**/**n**")

        def check(message):
            return message.author == ctx.author and message.channel == ctx.channel and \
                                        message.content.lower() in ["y", "n"]

        try:
            msg = await bot.wait_for("message", check=check, timeout=30)
            if msg.content.lower() == "n":
                await ctx.send("Manual lock release aborted.")
                print("User cancelled manual unlock command.")
                return
            elif msg.content.lower() == "y":
                print("User wants to manually release channel lock.")

        except asyncio.TimeoutError:
            await ctx.send("**Cancelled**: no response.")
            return

        await ctx.send("OK. Releasing channel lock.")
        carrier_channel_lock.release()

        deletion_in_progress = False
        print("Channel lock manually released.")


    # a command to check the cron status for Fleet Reserve status
    @commands.command(name='cron_status', help='Check the status of the lasttrade cron task')
    @check_roles([admin_role(), dev_role()])
    async def cron_status(self, ctx):

        if not lasttrade_cron.is_running() or lasttrade_cron.failed():
            print("lasttrade cron task has failed, restarting.")
            await ctx.send('lasttrade cron task has failed, restarting...')
            lasttrade_cron.restart()
        else:
            nextrun = lasttrade_cron.next_iteration - datetime.now(tz=timezone.utc)
            await ctx.send(f'lasttrade cron task is running. Next run in {str(nextrun)}')

    # backup databases
    @commands.command(name='backup', help='Backs up the carrier and mission databases.')
    @check_roles([admin_role()])
    @check_command_channel(bot_command_channel())
    async def backup(self, ctx):
        print(f"{ctx.author} requested a manual DB backup")
        backup_database('missions')
        backup_database('carriers')
        await ctx.send("Database backup complete.")


    # forceably quit the bot
    # TODO: make this graceful
    @commands.command(name='stopquit', help="Stops the bots process on the VM, ending all functions.")
    @check_roles([admin_role()])
    @check_command_channel(bot_command_channel())
    async def stopquit(self, ctx):
        await ctx.send(f"k thx bye")
        bot_exit()


    """
    GENERAL USER COMMANDS
    """

    """
    Mission list commands
    """

    # list active carrier trade mission from DB
    @commands.command(name='ission', help="Show carrier's active trade mission.")
    async def ission(self, ctx):

        # this is the spammy version of the command, prints details to open channel

        # take a note of the channel name
        msg_ctx_name = ctx.channel.name

        carrier_data = find_carrier(msg_ctx_name, "discordchannel")
        embed = await _is_carrier_channel(carrier_data)

        if not embed:
            embed = await _is_mission_active_embed(carrier_data)

        await ctx.send(embed=embed)
        return
    
    # mission slash command - private, non spammy
    @app_commands.command(name="mission",
        description="Private command: Use in a Fleet Carrier's channel to display its current mission.")
    async def _mission(self, interaction: discord.Interaction):

        print(f"{interaction.user} asked for active mission in <#{interaction.channel}> (used /mission)")

        # take a note of the channel name
        msg_channel_name = interaction.channel.name

        carrier_data = find_carrier(msg_channel_name, "discordchannel")
        embed = await _is_carrier_channel(carrier_data)

        if not embed:
            embed = await _is_mission_active_embed(carrier_data)

        await interaction.response.send_message(embed=embed, ephemeral=True)
        return


    # list all active carrier trade missions from DB
    @commands.command(name='issions', help='List all active trade missions.')
    async def issions(self, ctx):

        print(f'User {ctx.author} asked for all active missions.')

        co_role = discord.utils.get(ctx.guild.roles, id=certcarrier_role())
        print(f'Check if user has role: "{co_role}"')
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
            trade_channel = bot.get_channel(trade_alerts_channel())
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
        embed = _format_missions_embed(load_records, embed)
        await ctx.send(embed=embed)

        embed = discord.Embed(title=f"{len(unload_records)} P.T.N Fleet Carrier UNLOADING missions in progress:",
                            color=constants.EMBED_COLOUR_UNLOADING)
        embed = _format_missions_embed(unload_records, embed)
        await ctx.send(embed=embed)


    # missions slash command - private, non-spammy
    @app_commands.command(name="missions",
        description="Private command: Display all missions in progress.")
    async def _missions(self, interaction: discord.Interaction):

        print(f'User {interaction.user} asked for all active missions via /missions in {interaction.channel}.')

        print(f'Generating full unloading mission list requested by: {interaction.user}')
        mission_db.execute('''SELECT * FROM missions WHERE missiontype="unload";''')
        unload_records = [MissionData(mission_data) for mission_data in mission_db.fetchall()]

        mission_db.execute('''SELECT * FROM missions WHERE missiontype="load";''')
        print(f'Generating full loading mission list requested by: {interaction.user}')
        load_records = [MissionData(mission_data) for mission_data in mission_db.fetchall()]

        trade_channel = bot.get_channel(trade_alerts_channel())
        number_of_missions = len(load_records) + len(unload_records)

        description_text = f'For full details of all current trade missions follow the link to <#{trade_channel.id}>'
        if not number_of_missions:
            description_text = f'Currently no active missions listed in <#{trade_channel.id}>'

        embed = discord.Embed(
            title=f"{number_of_missions} P.T.N Fleet Carrier missions in progress:",
            description=description_text,
            color=constants.EMBED_COLOUR_LOADING
        )

        await interaction.response.send_message(embed=embed, ephemeral=True)

        if not number_of_missions:
            return
        else:

            embed = discord.Embed(title=f"{len(load_records)} P.T.N Fleet Carrier LOADING missions in progress:",
                                color=constants.EMBED_COLOUR_LOADING)
            embed = _format_missions_embed(load_records, embed)
            await interaction.followup.send(embed=embed, ephemeral=True)

            embed = discord.Embed(title=f"{len(unload_records)} P.T.N Fleet Carrier UNLOADING missions in progress:",
                                color=constants.EMBED_COLOUR_UNLOADING)
            embed = _format_missions_embed(unload_records, embed)
            await interaction.followup.send(embed=embed, ephemeral=True)


    # a command for users to mark a carrier mission complete from within the carrier channel
    # TODO: slashify with button prompts
    @commands.command(name='complete', help="Use in a carrier's channel to mark the current trade mission complete.")
    async def complete(self, ctx, *, comment: str = None):

        print(f"m.complete called in {ctx.channel} by {ctx.author}")

        # look for a match for the channel name in the carrier DB
        print("Looking for carrier by channel name match")
        carrier_data = find_carrier(ctx.channel.name, "discordchannel")
        if not carrier_data:
            # if there's no channel match, return an error
            embed = discord.Embed(description="**You need to be in a carrier's channel to mark its mission as complete.**",
                                color=constants.EMBED_COLOUR_ERROR)
            await ctx.send(embed=embed)
            return

        # now look to see if the carrier is on an active mission
        print("Looking for mission by channel ID match")
        mission_data = find_mission(ctx.channel.id, "channelid")
        if not mission_data:
            # if there's no result, return an error
            embed = discord.Embed(description=f"**{carrier_data.carrier_long_name} doesn't seem to be on a trade "
                                                f"mission right now.**",
                                    color=constants.EMBED_COLOUR_ERROR)
            return await ctx.send(embed=embed)


        # user is in correct channel and carrier is on a mission, so check whether user is sure they want to proceed
        print("Send user confirm prompt")
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
                print("User responded no")
                embed = discord.Embed(description="OK, mission will remain listed as in-progress.",
                                        color=constants.EMBED_COLOUR_OK)
                await ctx.send(embed=embed)
                return
            elif msg.content.lower() == "y":
                # they said yes!
                print("User responded yes")
                reddit_complete_text = f"    INCOMING WIDEBAND TRANSMISSION: P.T.N. CARRIER MISSION UPDATE\n\n**" \
                                    f"{mission_data.carrier_name}** mission complete. o7 CMDRs!\n\n\n\n*Reported on " \
                                    f"PTN Discord by {ctx.author.display_name}*"
                discord_complete_embed = discord.Embed(title=f"{mission_data.carrier_name} MISSION COMPLETE",
                                                    description=f"<@{ctx.author.id}> reports mission complete! **This mission channel will be removed in {(seconds_long())//60} minutes.**",
                                                    color=constants.EMBED_COLOUR_OK)
                print("Sending to _cleanup_completed_mission")
                desc_msg = f"> {comment}\n" if comment else ""
                await _cleanup_completed_mission(ctx, mission_data, reddit_complete_text, discord_complete_embed, desc_msg)

        except asyncio.TimeoutError:
            embed = discord.Embed(description="No response, mission will remain listed as in-progress.")
            await ctx.send(embed=embed)


    # public command to nominate a user for CP
    @app_commands.command(name="nominate",
                          description="Private command: Nominate an @member to become a Community Pillar.")
    @app_commands.describe(user='An @mention of the user you want to nominate.',
                           reason='A short explanation of why they deserve your nomination.')
    async def nominate(self, interaction: discord.Interaction, user: discord.Member, *, reason: str):

        # first check the user is not nominating themselves because seriously dude

        if interaction.user.id == user.id:
            print(f"{interaction.user} tried to nominate themselves for Community Pillar :]")
            return await interaction.response.send_message("You can't nominate yourself! But congrats on the positive self-esteem :)", ephemeral=True)

        #Skip nominating Cpillar|Cmentor|Council|Mod
        for avoid_role in [cpillar_role(), cmentor_role(), admin_role(), mod_role()]:
            if user.get_role(avoid_role):
                print(f"{interaction.user} tried to nominate a Cpillar|Cmentor|Council|Mod : {user.name}")
                return await interaction.response.send_message(
                    (f"You can't nominate an existing <@&{cpillar_role()}>,"
                    f" <@&{cmentor_role()}>, <@&{admin_role()}> or <@&{mod_role()}>."
                    " But we appreciate your nomination attempt!"),
                    ephemeral=True)

        print(f"{interaction.user} wants to nominate {user}")
        spamchannel = bot.get_channel(bot_spam_channel())

        # first check this user has not already nominated the same person
        nominees_data = find_nominator_with_id(interaction.user.id)
        if nominees_data:
            for nominees in nominees_data:
                if nominees.pillar_id == user.id:
                    print("This user already nommed this dude")
                    embed = discord.Embed(title="Nomination Failed", description=f"You've already nominated <@{user.id}> for reason **{nominees.note}**.\n\n"
                                                                                f"You can nominate any number of users, but only once for each user.", color=constants.EMBED_COLOUR_ERROR)
                    await interaction.response.send_message(embed=embed, ephemeral=True)
                    return

        print("No matching nomination, proceeding")

        # enter nomination into nominees db
        try:
            print("Locking carrier db...")
            await carrier_db_lock.acquire()
            print("Carrier DB locked.")
            try:
                carrier_db.execute(''' INSERT INTO nominees VALUES(?, ?, ?) ''',
                                (interaction.user.id, user.id, reason))
                carriers_conn.commit()
                print("Registered nomination to database")
            finally:
                print("Unlocking carrier db...")
                carrier_db_lock.release()
                print("Carrier DB unlocked.")
        except Exception as e:
            await interaction.response.send_message("Sorry, something went wrong and developers have been notified.", ephemeral=True)
            # notify in bot_spam
            await spamchannel.send(f"Error on /nominate by {interaction.user}: {e}")
            return print(f"Error on /nominate by {interaction.user}: {e}")

        # notify user of success
        embed = discord.Embed(title="Nomination Successful", description=f"Thank you! You've nominated <@{user.id}> "
                                    f"to become a Community Pillar.\n\nReason: **{reason}**", color=constants.EMBED_COLOUR_OK)
        await interaction.response.send_message(embed=embed, ephemeral=True)

        # also tell bot-spam
        await spamchannel.send(f"<@{user.id}> was nominated for Community Pillar.")
        return print("Nomination successful")
    

    # public command to remove a previously submitted nomination
    @app_commands.command(name="nominate_remove",
                          description="Private command: Remove your Pillar nomination for a user.")
    @app_commands.describe(user='An @mention of the user you wish to remove your nomination for.')
    async def nominate_remove(self, interaction: discord.Interaction, user: discord.Member):

        print(f"{interaction.user} wants to un-nominate {user}")

        # find the nomination
        nominees_data = find_nominator_with_id(interaction.user.id)
        if nominees_data:
            for nominees in nominees_data:
                if nominees.pillar_id == user.id:
                    await delete_nominee_by_nominator(interaction.user.id, user.id)
                    embed = discord.Embed(title="Nomination Removed", description=f"Your nomination for <@{user.id}> "
                                            f"has been removed. If they're being a jerk, consider reporting privately "
                                            f"to a <@&{mod_role()}> or <@&{admin_role()}> member.", color=constants.EMBED_COLOUR_OK)
                    await interaction.response.send_message(embed=embed, ephemeral=True)

                    # notify bot-spam
                    spamchannel = bot.get_channel(bot_spam_channel())
                    await spamchannel.send(f"A nomination for <@{user.id}> was withdrawn.")
                    return

        # otherwise return an error
        print("No such nomination")
        return await interaction.response.send_message("No nomination found by you for that user.", ephemeral=True)
    

    # sign up for a Community Carrier's notification role
    # TODO TEST
    @app_commands.command(name="notify_me",
                          description="Private command: Use in a COMMUNITY CHANNEL to opt in/out to receive its notifications.")
    async def notify_me(self, interaction: discord.Interaction):
        print(f"{interaction.user.name} used /notify_me in {interaction.channel.name}")

        # note channel ID
        msg_channel_id = interaction.channel.id

        # define spamchannel
        spamchannel = bot.get_channel(bot_spam_channel())

        # look for a match for the channel ID in the community carrier DB
        community_carrier_data = find_community_carrier(msg_channel_id, CCDbFields.channelid.name)

        if not community_carrier_data:
            # if there's no channel match, return an error
            embed = discord.Embed(description="Please try again in a Community Channel.", color=constants.EMBED_COLOUR_ERROR)
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        elif community_carrier_data:
            # TODO: this should be fetchone() not fetchall but I can't make it work otherwise
            for community_carrier in community_carrier_data:
                print(f"Found data: {community_carrier.owner_id} owner of {community_carrier.channel_id}")
                channel_id = community_carrier.channel_id
                role_id = community_carrier.role_id
                owner_id = community_carrier.owner_id

        # we're in a carrier's channel so try to match its role ID with a server role
        print(f"/notify used in channel for {channel_id}")
        notify_role = discord.utils.get(interaction.guild.roles, id=role_id)

        # check if role actually exists
        if not notify_role:
            await interaction.response.send_message("Sorry, I couldn't find a notification role for this channel. Please report this to an Admin.", ephemeral=True)
            await spamchannel.send(f"**ERROR**: {interaction.user} tried to use `/notify_me` in <#{interaction.channel.id}> but received an error (role does not exist).")
            print(f"No role found matching {interaction.channel}")
            return

        # check if user has this role
        print(f'Check whether user has role: "{notify_role}"')
        print(f'User has roles: {interaction.user.roles}')
        if notify_role not in interaction.user.roles:
            # they don't so give it to them
            await interaction.user.add_roles(notify_role)
            embed = discord.Embed(title=f"You've signed up for notifications for {interaction.channel.name}!",
                                    description=f"You'll receive notifications from <@{owner_id}> or "
                                                f"<@&{cmentor_role()}>s about this event or channel's activity. You can cancel at any"
                                                f" time by using `/notify_me` again in this channel.", color=constants.EMBED_COLOUR_OK)
            await interaction.response.send_message(embed=embed, ephemeral=True)
        else:
            # they do so take it from them
            await interaction.user.remove_roles(notify_role)
            embed = discord.Embed(title=f"You've cancelled notifications for {interaction.channel.name}.",
                                    description="You'll no longer receive notifications about this event or channel's activity."
                                                " You can sign up again at any time by using `/notify_me` in this channel.",
                                                color=constants.EMBED_COLOUR_QU)
            await interaction.response.send_message(embed=embed, ephemeral=True)