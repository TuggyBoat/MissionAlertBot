"""
MissionCleaner.py

Functions relating to mission clean-up.

Dependencies: constants, database, helpers

"""
# import libraries
import aiohttp
import asyncio
import random

# import discord.py
import discord
from discord import Webhook
from discord.errors import Forbidden, NotFound

# import local classes
from ptn.missionalertbot.classes.MissionData import MissionData

# import local constants
import ptn.missionalertbot.constants as constants
from ptn.missionalertbot.constants import bot, bot_spam_channel, wine_alerts_loading_channel, wine_alerts_unloading_channel, trade_alerts_channel, get_reddit, sub_reddit, \
    reddit_flair_mission_stop, seconds_long, sub_reddit, mission_command_channel, ptn_logo_discord

# import local modules
from ptn.missionalertbot.database.database import remove_channel_cleanup_entry, backup_database, mission_db, missions_conn, find_carrier, mark_cleanup_channel, CarrierDbFields
from ptn.missionalertbot.modules.helpers import lock_mission_channel, carrier_channel_lock, clean_up_pins


"""
MISSION COMPLETE & CLEANUP
"""

# clean up a completed mission
async def _cleanup_completed_mission(interaction, mission_data, reddit_complete_text, discord_complete_embed, desc_msg):
        print("called _cleanup_completed_mission")

        mission_params = mission_data.mission_params

        feedback_embed = discord.Embed(title=f"Mission complete for {mission_data.carrier_name}",
                            description=f"{desc_msg}",
                            color=constants.EMBED_COLOUR_OK)
        feedback_embed.set_footer(text="Updated sent alerts and removed from mission list.")

        async with interaction.channel.typing():
            completed_mission_channel = bot.get_channel(mission_data.channel_id)
            mission_gen_channel = bot.get_channel(mission_command_channel())
            if interaction.channel.id == mission_gen_channel.id: # tells us whether m.done was used or m.complete
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

                    try:
                        msg = await alert_channel.fetch_message(discord_alert_id)
                        await msg.delete()
                    except:
                        print("No alert found, maybe user deleted it?")

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
                    feedback_embed.add_field(name="Error", value="Failed updating Reddit :(")


            # update webhooks
            print("Update sent webhooks...")
            if mission_params.webhook_urls and mission_params.webhook_msg_ids and mission_params.webhook_jump_urls:
                for webhook_url, webhook_msg_id, webhook_jump_url in zip(mission_params.webhook_urls, mission_params.webhook_msg_ids, mission_params.webhook_jump_urls):
                    try: 
                        async with aiohttp.ClientSession() as session:
                            print(f"Fetching webhook for {webhook_url} with jumpurl {webhook_jump_url} and ID {webhook_msg_id}")
                            webhook = Webhook.from_url(webhook_url, session=session, client=bot)
                            webhook_msg = await webhook.fetch_message(webhook_msg_id)

                            # edit the original message
                            print("Editing original webhook message...")
                            embed = discord.Embed(title="PTN TRADE MISSION COMPLETED",
                                                  description=f"**{mission_params.carrier_data.carrier_long_name}** finished {mission_params.mission_type}ing "
                                                              f"{mission_params.commodity_data.name} from **{mission_params.station}** in **{mission_params.system}**.",
                                                  color=constants.EMBED_COLOUR_QU)
                            embed.set_footer(text=f"Join {constants.DISCORD_INVITE_URL} for more trade opportunities.")
                            embed.set_thumbnail(url=ptn_logo_discord())
                            await webhook_msg.remove_attachments(webhook_msg.attachments)
                            await webhook_msg.edit(embed=embed)

                            reason = f"\n\n{desc_msg}" if desc_msg else ""

                            print("Sending webhook update message...")
                            # send a new message to update the target channel
                            embed = discord.Embed(title="PTN TRADE MISSION COMPLETED",
                                                  description=f"The mission {webhook_jump_url} posted at <t:{mission_params.timestamp}:f> (<t:{mission_params.timestamp}:R> "
                                                              f"has been marked as completed on the [PTN Discord]({constants.DISCORD_INVITE_URL}).{reason}",
                                                  color=constants.EMBED_COLOUR_OK)
                            await webhook.send(embed=embed, username='Pilots Trade Network', avatar_url=bot.user.avatar.url, wait=True)

                    except Exception as e:
                        print(f"Failed updating webhook message {webhook_jump_url} with URL {webhook_url}: {e}")
                        await feedback_embed.add_field(name="Error", value=f"Failed updating webhook message {webhook_jump_url} with URL {webhook_url}: {e}")


            # delete mission entry from db
            print("Remove from mission database...")
            mission_db.execute(f'''DELETE FROM missions WHERE carrier LIKE (?)''', ('%' + mission_data.carrier_name + '%',))
            missions_conn.commit()

            await clean_up_pins(completed_mission_channel)

            # command feedback
            print("Send command feedback to user")
            spamchannel = bot.get_channel(bot_spam_channel())
            embed = discord.Embed(title=f"Mission complete for {mission_data.carrier_name}",
                                description=f"{interaction.user} marked the mission complete in #{interaction.channel.name}",
                                color=constants.EMBED_COLOUR_OK)
            await spamchannel.send(embed=embed)

            # notify owner if not command user
            carrier_data = find_carrier(mission_data.carrier_name, CarrierDbFields.longname.name)
            if not interaction.user.id == carrier_data.ownerid:
                print("Notify carrier owner")
                # notify in channel - not sure this is needed anymore, leaving out for now
                # await interaction.channel.send(f"Notifying carrier owner: <@{carrier_data.ownerid}>")

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
                    reason = f"\n{desc_msg}" if desc_msg else ""
                    await owner.send(f"Ahoy CMDR! {interaction.user.display_name} has concluded the trade mission for your Fleet Carrier **{carrier_data.carrier_long_name}**. **Reason given**: {reason}\nIts mission channel will be removed in {seconds_long()//60} minutes unless a new mission is started.")
                else:
                    await owner.send(f"Ahoy CMDR! The trade mission for your Fleet Carrier **{carrier_data.carrier_long_name}** has been marked as complete by {interaction.user.display_name}. Its mission channel will be removed in {seconds_long()//60} minutes unless a new mission is started.")

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