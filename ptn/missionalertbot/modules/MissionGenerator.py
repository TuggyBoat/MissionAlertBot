"""
MissionGenerator.py

Functions relating to mission generation, management, and clean-up.

Dependencies: constants, database, helpers, Embeds, ImageHandling

TODO: gen_mission.returnflag, gracefully exit if generation fails (remove posts etc), better ctx.typing() placement

"""
# import libraries
import asyncio
import os
from PIL import Image
import random
from typing import Union

# import discord.py
import discord
from discord.errors import HTTPException, Forbidden, NotFound

# import local classes
from ptn.missionalertbot.classes.MissionData import MissionData

# import local constants
import ptn.missionalertbot.constants as constants
from ptn.missionalertbot.constants import bot, bot_spam_channel, wine_alerts_loading_channel, wine_alerts_unloading_channel, trade_alerts_channel, legacy_alerts_channel, get_reddit, sub_reddit, \
    reddit_flair_mission_stop, reddit_flair_mission_start, seconds_short, seconds_long, sub_reddit, channel_upvotes, upvote_emoji, legacy_hauler_role, hauler_role, \
    trade_cat, get_guild, get_overwrite_perms, mission_command_channel

# import local modules
from ptn.missionalertbot.database.database import remove_channel_cleanup_entry, backup_database, mission_db, missions_conn, find_carrier, mark_cleanup_channel, CarrierDbFields, \
    find_commodity, find_mission, carrier_db, carriers_conn
from ptn.missionalertbot.modules.Embeds import _mission_summary_embed
from ptn.missionalertbot.modules.helpers import lock_mission_channel, carrier_channel_lock, clean_up_pins
from ptn.missionalertbot.modules.ImageHandling import assign_carrier_image, create_carrier_mission_image
from ptn.missionalertbot.modules.TextGen import txt_create_discord, txt_create_reddit_body, txt_create_reddit_title


"""
MISSION COMPLETE & CLEANUP
"""

# clean up a completed mission
async def _cleanup_completed_mission(ctx, mission_data, reddit_complete_text, discord_complete_embed, desc_msg):
        print("called _cleanup_completed_mission")

        async with ctx.typing():
            completed_mission_channel = bot.get_channel(mission_data.channel_id)
            mission_gen_channel = bot.get_channel(mission_command_channel())
            if ctx.channel.id == mission_gen_channel.id: # tells us whether m.done was used or m.complete
                m_done = True
                print("Processing mission complete by m.done")
            else:
                m_done = False
                print("Processing mission complete by m.complete")

            backup_database('missions')  # backup the missions database before going any further

            # delete Discord trade alert
            print("Delete Discord trade alert...")
            if mission_data.discord_alert_id and mission_data.discord_alert_id != 'NULL':
                try:  # try in case it's already been deleted, which doesn't matter to us in the slightest but we don't
                    # want it messing up the rest of the function

                    # first check if it's Wine, in which case it went to the booze cruise channel
                    if mission_data.commodity.title() == "Wine":
                        if mission_data.mission_type == 'load':
                            alert_channel = bot.get_channel(wine_alerts_loading_channel())
                        else:
                            alert_channel = bot.get_channel(wine_alerts_unloading_channel())
                    else:
                        alert_channel = bot.get_channel(trade_alerts_channel())

                    discord_alert_id = mission_data.discord_alert_id

                    try: # shitty hacky message of incorporating legacy trades without extra DB fields
                        msg = await alert_channel.fetch_message(discord_alert_id)
                        await msg.delete()
                    except: # if it can't find a message in the normal channel it'll look in legacy instead
                        alert_channel = bot.get_channel(legacy_alerts_channel())
                        msg = await alert_channel.fetch_message(discord_alert_id)
                        await msg.delete()

                except:
                    print(f"Looks like this mission alert for {mission_data.carrier_name} was already deleted"
                        f" by someone else. We'll keep going anyway.")

                # send Discord carrier channel updates
                # try in case channel already deleted
                try:
                    await completed_mission_channel.send(embed=discord_complete_embed)
                except:
                    print(f"Unable to send completion message for {mission_data.carrier_name}, maybe channel deleted?")

            # add comment to Reddit post
            print("Add comment to Reddit post...")
            if mission_data.reddit_post_id and mission_data.reddit_post_id != 'NULL':
                try:  # try in case Reddit is down
                    reddit_post_id = mission_data.reddit_post_id
                    reddit = await get_reddit()
                    await reddit.subreddit(sub_reddit())
                    submission = await reddit.submission(reddit_post_id)
                    await submission.reply(reddit_complete_text)
                    # mark original post as spoiler, change its flair
                    await submission.flair.select(reddit_flair_mission_stop())
                    await submission.mod.spoiler()
                except:
                    await ctx.send("Failed updating Reddit :(")

            # delete mission entry from db
            print("Remove from mission database...")
            mission_db.execute(f'''DELETE FROM missions WHERE carrier LIKE (?)''', ('%' + mission_data.carrier_name + '%',))
            missions_conn.commit()

            await clean_up_pins(completed_mission_channel)

            # command feedback
            print("Send command feedback to user")
            spamchannel = bot.get_channel(bot_spam_channel())
            embed = discord.Embed(title=f"Mission complete for {mission_data.carrier_name}",
                                description=f"{ctx.author} marked the mission complete in #{ctx.channel.name}",
                                color=constants.EMBED_COLOUR_OK)
            await spamchannel.send(embed=embed)
            if m_done:
                # notify user in mission gen channel
                embed = discord.Embed(title=f"Mission complete for {mission_data.carrier_name}",
                                    description=f"{desc_msg}",
                                    color=constants.EMBED_COLOUR_OK)
                embed.set_footer(text="Updated any sent alerts and removed from mission list.")
                await ctx.send(embed=embed)

            # notify owner if not command author
            carrier_data = find_carrier(mission_data.carrier_name, CarrierDbFields.longname.name)
            if not ctx.author.id == carrier_data.ownerid:
                print("Notify carrier owner")
                # notify in channel - not sure this is needed anymore, leaving out for now
                # await ctx.send(f"Notifying carrier owner: <@{carrier_data.ownerid}>")

                # notify by DM
                owner = await bot.fetch_user(carrier_data.ownerid)
                #chnaged to if there is rp text not if it was m.done
                if desc_msg != "":
                    """
                    desc_msg converts rp text received by m.done into a format that can be inserted directly into messages
                    without having to change the message's format depending on whether it exists or not. This was primarily
                    intended for CCOs to be able to send a message to their channel via the bot on mission completion.

                    Now it's pulling double-duty as a way for other CCOs to notify the owner why they used m.done on a
                    mission that wasn't theirs. In this case it's still useful for that information to be sent to the channel
                    (e.g. "Supply exhausted", "tick changed prices", etc)

                    desc_msg is "" if received from empty rp argument, so reason converts it to None if empty and adds a line break.
                    This can probably be reworked to be neater and use fewer than 3 separate variables for one short message in the future.
                    """
                    reason = f"\n{desc_msg}" if desc_msg else None
                    await owner.send(f"Ahoy CMDR! {ctx.author.display_name} has concluded the trade mission for your Fleet Carrier **{carrier_data.carrier_long_name}**. **Reason given**: {reason}\nIts mission channel will be removed in {seconds_long()//60} minutes unless a new mission is started.")
                else:
                    await owner.send(f"Ahoy CMDR! The trade mission for your Fleet Carrier **{carrier_data.carrier_long_name}** has been marked as complete by {ctx.author.display_name}. Its mission channel will be removed in {seconds_long()//60} minutes unless a new mission is started.")

        # remove channel
        await mark_cleanup_channel(mission_data.channel_id, 1)
        await remove_carrier_channel(mission_data.channel_id, seconds_long())

        return


async def remove_carrier_channel(completed_mission_channel_id, seconds):
    # get channel ID to remove
    delchannel = bot.get_channel(completed_mission_channel_id)
    spamchannel = bot.get_channel(bot_spam_channel())

    # start a timer
    print(f"Starting {seconds} second countdown for deletion of {delchannel}")
    await asyncio.sleep(seconds)
    print("Channel removal timer complete")

    try:
        # try to acquire a channel lock, if unsuccessful after a period of time, abort and throw up an error
        try:
            await asyncio.wait_for(lock_mission_channel(), timeout=120)
        except asyncio.TimeoutError:
            print(f"No channel lock available for {delchannel}")
            return await spamchannel.send(f"<@211891698551226368> WARNING: No channel lock available on {delchannel} after 120 seconds. Deletion aborted.")

        # this is clunky but we want to know if a channel lock is because it's about to be deleted
        global deletion_in_progress
        deletion_in_progress = True

        # check whether channel is in-use for a new mission
        mission_db.execute(f"SELECT * FROM missions WHERE "
                        f"channelid = {completed_mission_channel_id}")
        mission_data = MissionData(mission_db.fetchone())
        print(f'Mission data from remove_carrier_channel: {mission_data}')

        if mission_data:
            # abort abort abort
            print(f'New mission underway in this channel, aborting removal')
        else:
            # delete channel after a parting gift
            gif = random.choice(constants.boom_gifs)
            try:
                await delchannel.send(gif)
                await asyncio.sleep(5)
                await delchannel.delete()
                print(f'Deleted {delchannel}')
                await remove_channel_cleanup_entry(completed_mission_channel_id)

            except Forbidden:
                raise EnvironmentError(f"Could not delete {delchannel}, reason: Bot does not have permission.")
            except NotFound:
                print("Channel appears to have been deleted by someone else, we'll just continue on.")
                await spamchannel.send(f"Channel {delchannel} could not be deleted because it doesn't exist.")
    finally:
        # now release the channel lock
        carrier_channel_lock.release()
        deletion_in_progress = False
        print("Channel lock released")
        return


async def cleanup_trade_channel(channel):
    """
    This function is called on bot.on_ready() to clean up any channels
    that had their timer lost during bot stop/restart
    """
    print(f"Sending channel {channel['channelid']} for removal")
    await remove_carrier_channel(channel['channelid'], seconds_long())
    return


"""
Mission generation

The core of MAB: its mission generator

"""

# mission generator called by loading/unloading commands
async def gen_mission(ctx, carrier_name_search_term: str, commodity_search_term: str, system: str, station: str,
                    profit: Union[int, float], pads: str, demand: str, rp: str, mission_type: str,
                    eta: str, legacy):
    current_channel = ctx.channel
    async with ctx.typing():

        print(f'Mission generation type: {mission_type} with RP: {rp}, requested by {ctx.author}. Request triggered from '
            f'channel {current_channel}.')

        if pads.upper() not in ['M', 'L']:
            # In case a user provides some junk for pads size, gate it
            print(f'Exiting mission generation requested by {ctx.author} as pad size is invalid, provided: {pads}')
            return await ctx.send(f'Sorry, your pad size is not L or M. Provided: {pads}. Mission generation cancelled.')

        # check if commodity can be found, exit gracefully if not
        # gen_mission.returnflag = False
        commodity_data = await find_commodity(commodity_search_term, ctx)
        # if not gen_mission.returnflag:
            #return # we've already given the user feedback on why there's a problem, we just want to quit gracefully now
        if not commodity_data:
            raise ValueError('Missing commodity data')

        # check if the carrier can be found, exit gracefully if not
        carrier_data = find_carrier(carrier_name_search_term, CarrierDbFields.longname.name)
        if not carrier_data:
            return await ctx.send(f"No carrier found for {carrier_name_search_term}. You can use `/find` or `/owner` to search for carrier names.")

        # check carrier isn't already on a mission
        mission_data = find_mission(carrier_data.carrier_long_name, "carrier")
        if mission_data:
            embed = discord.Embed(title="Error",
                                description=f"{mission_data.carrier_name} is already on a mission, please "
                                            f"use **m.done** to mark it complete before starting a new mission.",
                                color=constants.EMBED_COLOUR_ERROR)
            await ctx.send(embed=embed)
            return  # We want to stop here, so go exit out

        # check if the carrier has an associated image
        image_name = carrier_data.carrier_short_name + '.png'
        image_path = os.path.join(constants.IMAGE_PATH, image_name)
        if os.path.isfile(image_path):
            print("Carrier mission image found, checking size...")
            image = Image.open(image_path)
            image_is_good = image.size == (506, 285)
        else:
            image_is_good = False
        if not image_is_good:
            print(f"No valid carrier image found for {carrier_data.carrier_long_name}")
            # send the user to upload an image
            embed = discord.Embed(description="**YOUR FLEET CARRIER MUST HAVE A VALID MISSION IMAGE TO CONTINUE**.", color=constants.EMBED_COLOUR_QU)
            await ctx.send(embed=embed)
            await assign_carrier_image(ctx, carrier_data.carrier_long_name)
            # OK, let's see if they fixed the problem. Once again we check the image exists and is the right size
            if os.path.isfile(image_path):
                print("Found an image file, checking size")
                image = Image.open(image_path)
                image_is_good = image.size == (506, 285)
            else:
                image_is_good = False
            if not image_is_good:
                print("Still no good image, aborting")
                embed = discord.Embed(description="**ERROR**: You must have a valid mission image to continue.", color=constants.EMBED_COLOUR_ERROR)
                await ctx.send(embed=embed)
                return

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
            mission_temp_channel_id = None
            check_characters = None
            edmc_off = False


            eta_text = f" (ETA {eta} minutes)" if eta else ""

            embed = discord.Embed(title="Generating and fetching mission alerts...", color=constants.EMBED_COLOUR_QU)
            message_gen = await ctx.send(embed=embed)

            def check_confirm(message):
                # use all to verify that all the characters in the message content are present in the allowed list (dtrx).
                # Anything outwith this grouping will cause all to fail. Use set to throw away any duplicate objects.
                # not sure if the msg.content can ever be None, but lets gate it anyway
                return message.content and message.author == ctx.author and message.channel == ctx.channel and \
                    all(character in check_characters for character in set(message.content.lower()))

            def check_rp(message):
                return message.author == ctx.author and message.channel == ctx.channel

            async def default_timeout_message(location):
                await ctx.send(f"**Mission generation cancelled (waiting too long for user input)** ({location})")


            # gen_mission.returnflag = False
            # mission_temp_channel_id = await create_mission_temp_channel(ctx, carrier_data.discord_channel, carrier_data.ownerid)
            # mission_temp_channel = bot.get_channel(mission_temp_channel_id)
            # # flag is set to True if mission channel creation is successful
            # if not gen_mission.returnflag:
            #     return # we've already notified the user

            # beyond this point any exits need to release the channel lock

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
                    await default_timeout_message('rp')
                    return

            # Options that should create a mission db entry will change this to True
            submit_mission = False

            # generate the mission elements

            file_name = await create_carrier_mission_image(carrier_data, commodity_data, system, station, profit, pads, demand,
                                                    mission_type)
            discord_text = txt_create_discord(carrier_data, mission_type, commodity_data, station, system, profit, pads,
                            demand, eta_text, mission_temp_channel_id, edmc_off, legacy)
            print("Generated discord elements")
            reddit_title = txt_create_reddit_title(carrier_data, legacy)
            reddit_body = txt_create_reddit_body(carrier_data, mission_type, commodity_data, station, system, profit, pads,
                                                demand, eta_text, legacy)
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
                                "You can also use (**n**) to also notify PTN Haulers, and (**e**) to flag your mission as EDMC-OFF.",
                                color=constants.EMBED_COLOUR_QU)
            embed.set_footer(text="Enter all that apply, e.g. **drn** will send alerts to Discord and Reddit and notify PTN Haulers.")
            message_confirm = await ctx.send(embed=embed)
            print("Prompted user for alert destination")

            try:
                check_characters = 'dertnx'
                msg = await bot.wait_for("message", check=check_confirm, timeout=30)
                edmc_off = True if "e" in msg.content.lower() else False

                if "x" in msg.content.lower():
                    # immediately stop if there's an x anywhere in the message, even if there are other proper inputs
                    message_cancelled = await ctx.send("**Mission creation cancelled.**")
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
                        embed = discord.Embed(title="Roleplay Text (Discord)", description=f"`>>> {rp_text}`",
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
                    print("User used option d, creating mission channel")

                    mission_temp_channel_id = await create_mission_temp_channel(ctx, carrier_data.discord_channel, carrier_data.ownerid, carrier_data.carrier_short_name)
                    mission_temp_channel = bot.get_channel(mission_temp_channel_id)

                    # Recreate this text since we know the channel id
                    discord_text = txt_create_discord(carrier_data, mission_type, commodity_data, station, system, profit, pads,
                                    demand, eta_text, mission_temp_channel_id, edmc_off, legacy)
                    message_send = await ctx.send("**Sending to Discord...**")
                    try:
                        # send trade alert to trade alerts channel, or to wine alerts channel if loading wine
                        if commodity_data.name.title() == "Wine":
                            if mission_type == 'load':
                                channel = bot.get_channel(wine_alerts_loading_channel())
                                channelId = wine_alerts_loading_channel()
                            else:   # unloading block
                                channel = bot.get_channel(wine_alerts_unloading_channel())
                                channelId = wine_alerts_unloading_channel()
                        else:
                            if legacy:
                                channel = bot.get_channel(legacy_alerts_channel())
                                channelId = legacy_alerts_channel()
                            else:
                                channel = bot.get_channel(trade_alerts_channel())
                                channelId = trade_alerts_channel()

                        if mission_type == 'load':
                            embed = discord.Embed(description=discord_text, color=constants.EMBED_COLOUR_LOADING)
                        else:
                            embed = discord.Embed(description=discord_text, color=constants.EMBED_COLOUR_UNLOADING)
                        embed.set_author(name=ctx.author.display_name, icon_url=ctx.author.display_avatar)

                        trade_alert_msg = await channel.send(embed=embed)
                        discord_alert_id = trade_alert_msg.id

                        discord_file = discord.File(file_name, filename="image.png")

                        embed_colour = constants.EMBED_COLOUR_LOADING if mission_type == 'load' \
                            else constants.EMBED_COLOUR_UNLOADING
                        embed = discord.Embed(title="P.T.N TRADE MISSION STARTING",
                                            description=f">>> {rp_text}" if rp else "", color=embed_colour)

                        embed.add_field(name="Destination", value=f"Station: {station.upper()}\nSystem: {system.upper()}", inline=True)
                        embed.add_field(name="Carrier Owner", value=f"<@{carrier_data.ownerid}>")
                        if eta:
                            embed.add_field(name="ETA", value=f"{eta} minutes", inline=False)

                        embed.set_image(url="attachment://image.png")
                        stock_field = f'\n;stock {carrier_data.carrier_short_name} will show carrier market data'
                        embed.set_footer(
                            text=
                                f"m.complete will mark this mission complete"
                                f"{stock_field if not legacy else ''}"
                                f"\n/info will show this carrier's details")
                        # pin the carrier trade msg sent by the bot
                        pin_msg = await mission_temp_channel.send(file=discord_file, embed=embed)
                        await pin_msg.pin()
                        embed = discord.Embed(title=f"Discord trade alerts sent for {carrier_data.carrier_long_name}",
                                            description=f"Check <#{channelId}> for trade alert and "
                                                        f"<#{mission_temp_channel_id}> for image.",
                                            color=constants.EMBED_COLOUR_DISCORD)
                        await ctx.send(embed=embed)
                        await message_send.delete()
                        submit_mission = True
                    except Exception as e:
                        print(f"Error sending to Discord: {e}")
                        await ctx.send(f"Error sending to Discord: {e}\nAttempting to continue with mission gen...")

                if "r" in msg.content.lower() and not edmc_off:
                    print("User used option r")
                    # profit is a float, not an int.
                    if float(profit) < 10:
                        print(f'Not posting the mission from {ctx.author} to reddit due to low profit margin <10k/t.')
                        await ctx.send(f'Skipped Reddit posting due to profit margin of {profit}k/t being below the PTN 10k/t '
                                    f'minimum. (Did you try to post a Wine load?)')
                    else:
                        message_send = await ctx.send("**Sending to Reddit...**")

                        try:

                            # post to reddit
                            reddit = await get_reddit()
                            subreddit = await reddit.subreddit(sub_reddit())
                            submission = await subreddit.submit_image(reddit_title, image_path=file_name,
                                                                    flair_id=reddit_flair_mission_start)
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
                            channel = bot.get_channel(channel_upvotes())
                            upvote_message = await channel.send(embed=embed)
                            emoji = bot.get_emoji(upvote_emoji())
                            await upvote_message.add_reaction(emoji)
                            submit_mission = True
                        except Exception as e:
                            print(f"Error posting to Reddit: {e}")
                            await ctx.send(f"Error posting to Reddit: {e}\nAttempting to continue with rest of mission gen...")

                if "n" in msg.content.lower() and "d" in msg.content.lower():
                    print("User used option n")

                    ping_role_id = legacy_hauler_role() if legacy else hauler_role()
                    await mission_temp_channel.send(f"<@&{ping_role_id}>: {discord_text}")

                    embed = discord.Embed(title=f"Mission notification sent for {carrier_data.carrier_long_name}",
                                description=f"Pinged <@&{ping_role_id}> in <#{mission_temp_channel_id}>",
                                color=constants.EMBED_COLOUR_DISCORD)
                    await ctx.send(embed=embed)

                if "e" in msg.content.lower() and "d" in msg.content.lower():
                    print('Sending EDMC OFF messages to haulers')
                    embed = discord.Embed(title='PLEASE STOP ALL 3RD PARTY SOFTWARE: EDMC, EDDISCOVERY, ETC',
                            description=("Maximising our haulers' profits for this mission means keeping market data at this station"
                                    " **a secret**! For this reason **please disable/exit all journal reporting plugins/programs**"
                                    " and leave them off until all missions at this location are complete. Thanks CMDRs!"),
                            color=constants.EMBED_COLOUR_REDDIT)
                    edmc_file_name = f'edmc_off_{random.randint(1,2)}.png'
                    edmc_path = os.path.join(constants.EDMC_OFF_PATH, edmc_file_name)
                    edmc_file = discord.File(edmc_path, filename="image.png")

                    embed.set_image(url="attachment://image.png")
                    pin_edmc = await mission_temp_channel.send(file=edmc_file, embed=embed)
                    await pin_edmc.pin()

                    embed = discord.Embed(title=f"EDMC OFF messages sent", description='Reddit posts will be skipped',
                                color=constants.EMBED_COLOUR_DISCORD)
                    await ctx.send(embed=embed)

                    print('Reacting to #official-trade-alerts message with EDMC OFF')
                    for r in ["🇪","🇩","🇲","🇨","📴"]:
                        await trade_alert_msg.add_reaction(r)

            except asyncio.TimeoutError:
                await default_timeout_message('notification_type_decision')
                try:
                    if mission_temp_channel_id:
                        carrier_channel_lock.release()
                        print("Channel lock released")
                finally:
                    if mission_temp_channel_id:
                        await remove_carrier_channel(mission_temp_channel_id, seconds_short)
                return

            print("All options worked through, now clean up")

            # now clear up by deleting the prompt message and user response
            try:
                await msg.delete()
                await message_confirm.delete()
            except Exception as e:
                print(f"Error during clearup: {e}")
                await ctx.send(f"Oops, error detected: {e}\nAttempting to continue with mission gen.")

            if submit_mission:
                await mission_add(ctx, carrier_data, commodity_data, mission_type, system, station, profit, pads, demand,
                            rp_text, reddit_post_id, reddit_post_url, reddit_comment_id, reddit_comment_url, discord_alert_id, mission_temp_channel_id)
                await mission_generation_complete(ctx, carrier_data, message_pending, eta_text)
            cleanup_temp_image_file(file_name)
            if mission_temp_channel_id:
                await mark_cleanup_channel(mission_temp_channel_id, 0)

            print("Reached end of mission generator")
            return
        except Exception as e:
            await ctx.send("Oh no! Something went wrong :( Mission generation aborted.")
            await ctx.send(e)
            print("Something went wrong with mission generation :(")
            print(e)
            carrier_channel_lock.release()
            if mission_temp_channel_id:
                await remove_carrier_channel(mission_temp_channel_id, seconds_short)


async def create_mission_temp_channel(ctx, discord_channel, owner_id, shortname):
    # create the carrier's channel for the mission

    # first check whether channel already exists

    mission_temp_channel = discord.utils.get(ctx.guild.channels, name=discord_channel)

    # we need to lock the channel to stop it being deleted mid process
    print("Waiting for Mission Generator channel lock...")
    lockwait_msg = await ctx.send("Waiting for channel lock to become available...")
    try:
        await asyncio.wait_for(lock_mission_channel(), timeout=10)
    except asyncio.TimeoutError:
        print("We couldn't get a channel lock after 10 seconds, let's abort rather than wait around.")
        return await ctx.send("Error: Channel lock could not be acquired, please try again. If the problem persists please contact an Admin.")

    await lockwait_msg.delete()

    if mission_temp_channel:
        # channel exists, so reuse it
        mission_temp_channel_id = mission_temp_channel.id
        await ctx.send(f"Found existing mission channel <#{mission_temp_channel_id}>.")
        print(f"Found existing {mission_temp_channel}")
    else:
        # channel does not exist, create it

        topic = f"Use \";stock {shortname}\" to retrieve stock levels for this carrier."

        category = discord.utils.get(ctx.guild.categories, id=trade_cat())
        mission_temp_channel = await ctx.guild.create_text_channel(discord_channel, category=category, topic=topic)
        mission_temp_channel_id = mission_temp_channel.id
        print(f"Created {mission_temp_channel}")

    print(f'Channels: {ctx.guild.channels}')

    if not mission_temp_channel:
        raise EnvironmentError(f'Could not create carrier channel {discord_channel}')

    # we made it this far, we can change the returnflag
    gen_mission.returnflag = True

    # find carrier owner as a user object
    guild = await get_guild()
    try:
        member = await guild.fetch_member(owner_id)
        print(f"Owner identified as {member.display_name}")
    except:
        raise EnvironmentError(f'Could not find Discord user matching ID {owner_id}')

    overwrite = await get_overwrite_perms()

    try:
        # first make sure it has the default permissions for the category
        await mission_temp_channel.edit(sync_permissions=True)
        print("Synced permissions with parent category")
        # now add the owner with superpermissions
        await mission_temp_channel.set_permissions(member, overwrite=overwrite)
        print(f"Set permissions for {member} in {mission_temp_channel}")
    except Forbidden:
        raise EnvironmentError(f"Could not set channel permissions in {mission_temp_channel}, reason: Bot does not have permissions to edit channel specific permissions.")
    except NotFound:
        raise EnvironmentError(f"Could not set channel permissions in {mission_temp_channel}, reason: The role or member being edited is not part of the guild.")
    except HTTPException:
        raise EnvironmentError(f"Could not set channel permissions in {mission_temp_channel}, reason: Editing channel specific permissions failed.")
    except (TypeError, ValueError):
        raise EnvironmentError(f"Could not set channel permissions in {mission_temp_channel}, reason: The overwrite parameter invalid or the target type was not Role or Member.")
    except:
        raise EnvironmentError(f'Could not set channel permissions in {mission_temp_channel}')

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
        print(f'Deleting the temp file at: {file_name}')
        os.remove(file_name)
    except Exception as e:
        print(f'There was a problem removing the temp image file located {file_name}')
        print(e)


"""
Mission database
"""


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

    print("Updating last trade timestamp for carrier")
    carrier_db.execute(''' UPDATE carriers SET lasttrade=strftime('%s','now') WHERE p_ID=? ''', ( [ carrier_data.pid ] ))
    carriers_conn.commit()

    # now we can release the channel lock
    if mission_temp_channel_id:
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