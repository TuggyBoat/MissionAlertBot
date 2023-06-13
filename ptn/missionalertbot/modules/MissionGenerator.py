"""
MissionGenerator.py

Functions relating to mission generation, management, and clean-up.

Dependencies: constants, database, helpers, Embeds, ImageHandling, MissionCleaner

TODO: gen_mission.returnflag, gracefully exit if generation fails (remove posts etc)

"""
# import libraries
import aiohttp
import asyncio
import os
import pickle
from PIL import Image
import random
from typing import Union

# import discord.py
import discord
from discord import Webhook
from discord.errors import HTTPException, Forbidden, NotFound

# import local classes
from ptn.missionalertbot.classes.MissionData import MissionData
from ptn.missionalertbot.classes.MissionParams import MissionParams

# import local constants
import ptn.missionalertbot.constants as constants
from ptn.missionalertbot.constants import bot, wine_alerts_loading_channel, wine_alerts_unloading_channel, trade_alerts_channel, get_reddit, sub_reddit, \
    reddit_flair_mission_start, seconds_short, sub_reddit, channel_upvotes, upvote_emoji, hauler_role, trade_cat, get_guild, get_overwrite_perms, ptn_logo_discord

# import local modules
from ptn.missionalertbot.database.database import backup_database, mission_db, missions_conn, find_carrier, mark_cleanup_channel, CarrierDbFields, \
    find_commodity, find_mission, carrier_db, carriers_conn, find_webhook_from_owner
from ptn.missionalertbot.modules.DateString import get_formatted_date_string
from ptn.missionalertbot.modules.Embeds import _mission_summary_embed
from ptn.missionalertbot.modules.helpers import lock_mission_channel, carrier_channel_lock
from ptn.missionalertbot.modules.ImageHandling import assign_carrier_image, create_carrier_reddit_mission_image, create_carrier_discord_mission_image
from ptn.missionalertbot.modules.MissionCleaner import remove_carrier_channel
from ptn.missionalertbot.modules.TextGen import txt_create_discord, txt_create_reddit_body, txt_create_reddit_title


# a class to hold all our Discord embeds
class DiscordEmbeds:
    def __init__(self, buy_embed, sell_embed, info_embed, help_embed, owner_text_embed, webhook_info_embed):
        self.buy_embed = buy_embed
        self.sell_embed = sell_embed
        self.info_embed = info_embed
        self.help_embed = help_embed
        self.owner_text_embed = owner_text_embed
        self.webhook_info_embed = webhook_info_embed




"""
Mission generator helpers

"""
async def return_discord_alert_embed(interaction, mission_params):
    if mission_params.mission_type == 'load':
        embed = discord.Embed(description=mission_params.discord_text, color=constants.EMBED_COLOUR_LOADING)
    else:
        embed = discord.Embed(description=mission_params.discord_text, color=constants.EMBED_COLOUR_UNLOADING)
    embed.set_author(name=interaction.user.display_name, icon_url=interaction.user.display_avatar)
    return embed


async def return_discord_channel_embeds(mission_params):
    # generates embeds used for the PTN carrier channel as well as any webhooks

    # define owner avatar
    owner = await bot.fetch_user(mission_params.carrier_data.ownerid)
    owner_name = owner.display_name
    owner_avatar = owner.display_avatar

    # define embed content
    if mission_params.mission_type == 'load': # embeds for a loading mission
        buy_description=f"📌 Station: **{mission_params.station.upper()}**" \
                        f"\n🌟 System: **{mission_params.system.upper()}**" \
                        f"\n📦 Commodity: **{mission_params.commodity_data.name.upper()}**"
        
        buy_thumb = constants.ICON_BUY

        sell_description=f"🎯 Fleet Carrier: **{mission_params.carrier_data.carrier_long_name}**" \
                         f"\n🔢 Carrier ID: **{mission_params.carrier_data.carrier_identifier}**" \
                         f"\n💰 Profit: **{mission_params.profit}K PER TON**" \
                         f"\n📥 Demand: **{mission_params.demand.upper()} TONS**"
        
        sell_thumb = ptn_logo_discord()

        embed_colour = constants.EMBED_COLOUR_LOADING

    else: # embeds for an unloading mission
        buy_description=f"🎯 Fleet Carrier: **{mission_params.carrier_data.carrier_long_name}**" \
                        f"\n🔢 Carrier ID: **{mission_params.carrier_data.carrier_identifier}**" \
                        f"\n🌟 System: **{mission_params.system.upper()}**" \
                        f"\n📦 Commodity: **{mission_params.commodity_data.name.upper()}**"

        buy_thumb = ptn_logo_discord()

        sell_description=f"📌 Station: **{mission_params.station.upper()}**" \
                         f"\n💰 Profit: **{mission_params.profit}K PER TON**" \
                         f"\n📥 Demand: **{mission_params.demand.upper()} TONS**"
        
        sell_thumb = constants.ICON_SELL

        embed_colour = constants.EMBED_COLOUR_UNLOADING

    # desc used by the local PTN additional info embed
    additional_info_description = f"💎 Carrier Owner: <@{mission_params.carrier_data.ownerid}>" \
                                  f"\n🔤 Carrier information: 👆 </info:849040914948554766>" \
                                  f"\n📊 Stock information: `;stock {mission_params.carrier_data.carrier_short_name}`\n\n"

    # desc used by the local PTN help embed
    help_description = "✅ Use `m.complete` in this channel if the mission is completed, or unable to be completed (e.g. because of a station price change, or supply exhaustion)." \
                       "\n\n💡 Need help? Here's our [complete guide to PTN trade missions](https://pilotstradenetwork.com/fleet-carrier-trade-missions/)."

    # desc used for sending RP text
    owner_text_description = mission_params.rp_text

    # desc used by the webhook additional info embed    
    webhook_info_description = f"💎 Carrier Owner: <@{mission_params.carrier_data.ownerid}>" \
                               f"\n🔤 [PTN Discord](https://discord.gg/ptn)" \
                                "\n💡 [PTN trade mission guide](https://pilotstradenetwork.com/fleet-carrier-trade-missions/)"

    buy_embed = discord.Embed(
        title="BUY FROM",
        description=buy_description,
        color=embed_colour
    )
    buy_embed.set_image(url=constants.BLANKLINE_400PX)
    buy_embed.set_thumbnail(url=buy_thumb)

    sell_embed = discord.Embed(
        title="SELL TO",
        description=sell_description,
        color=embed_colour
    )
    sell_embed.set_image(url=constants.BLANKLINE_400PX)
    sell_embed.set_thumbnail(url=sell_thumb)

    info_embed = discord.Embed(
        title="ADDITIONAL INFORMATION",
        description=additional_info_description,
        color=embed_colour
    )
    info_embed.set_image(url=constants.BLANKLINE_400PX)
    info_embed.set_thumbnail(url=owner_avatar)
    
    help_embed = discord.Embed(
        description=help_description,
        color=embed_colour
    )
    help_embed.set_image(url=constants.BLANKLINE_400PX)

    owner_text_embed = discord.Embed(
        title=f"MESSAGE FROM {owner_name}",
        description=owner_text_description,
        color=constants.EMBED_COLOUR_RP
    )
    owner_text_embed.set_image(url=constants.BLANKLINE_400PX)
    owner_text_embed.set_thumbnail(url=constants.ICON_DATA)

    webhook_info_embed = discord.Embed(
        title="ADDITIONAL INFORMATION",
        description=webhook_info_description,
        color=embed_colour
    )
    webhook_info_embed.set_image(url=constants.BLANKLINE_400PX)
    webhook_info_embed.set_thumbnail(url=owner_avatar)

    discord_embeds = DiscordEmbeds(buy_embed, sell_embed, info_embed, help_embed, owner_text_embed, webhook_info_embed)

    mission_params.discord_embeds = discord_embeds

    return discord_embeds


async def send_mission_to_discord(interaction, mission_params):
    print("User used option d, creating mission channel")

    mission_params.mission_temp_channel_id = await create_mission_temp_channel(interaction, mission_params.carrier_data.discord_channel, mission_params.carrier_data.ownerid, mission_params.carrier_data.carrier_short_name)
    mission_temp_channel = bot.get_channel(mission_params.mission_temp_channel_id)

    # Recreate this text since we know the channel id
    mission_params.discord_text = txt_create_discord(mission_params)
    message_send = await interaction.channel.send("**Sending to Discord...**")
    try:
        # send trade alert to trade alerts channel, or to wine alerts channel if loading wine
        if mission_params.commodity_data.name.title() == "Wine":
            if mission_params.mission_type == 'load':
                channel = bot.get_channel(wine_alerts_loading_channel())
                channelId = wine_alerts_loading_channel()
            else:   # unloading block
                channel = bot.get_channel(wine_alerts_unloading_channel())
                channelId = wine_alerts_unloading_channel()
        else:
            channel = bot.get_channel(trade_alerts_channel())
            channelId = trade_alerts_channel()

        embed = await return_discord_alert_embed(interaction, mission_params)

        trade_alert_msg = await channel.send(embed=embed)
        mission_params.discord_alert_id = trade_alert_msg.id

        discord_file = discord.File(mission_params.discord_img_name, filename="image.png")

        print("Defining Discord embeds...")
        discord_embeds = await return_discord_channel_embeds(mission_params)

        send_embeds = [discord_embeds.buy_embed, discord_embeds.sell_embed, discord_embeds.info_embed, discord_embeds.help_embed]

        print("Checking for RP status...")
        if mission_params.rp: send_embeds.append(discord_embeds.owner_text_embed)

        print("Sending image and embeds...")
        # pin the carrier trade msg sent by the bot
        pin_msg = await mission_temp_channel.send(file=discord_file, embeds=send_embeds)
        print("Pinning sent message...")
        await pin_msg.pin()
        print("Feeding back to user...")
        embed = discord.Embed(title=f"Discord trade alerts sent for {mission_params.carrier_data.carrier_long_name}",
                            description=f"Check <#{channelId}> for trade alert and "
                                        f"<#{mission_params.mission_temp_channel_id}> for image.",
                            color=constants.EMBED_COLOUR_DISCORD)
        await interaction.channel.send(embed=embed)
        await message_send.delete()

        if mission_params.edmc_off:
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

            embed = discord.Embed(title=f"EDMC OFF messages sent", description='External posts (Reddit, Webhooks) will be skipped',
                        color=constants.EMBED_COLOUR_DISCORD)
            await interaction.channel.send(embed=embed)

            print('Reacting to #official-trade-alerts message with EDMC OFF')
            for r in ["🇪","🇩","🇲","🇨","📴"]:
                await trade_alert_msg.add_reaction(r)

        submit_mission = True

        return submit_mission, mission_temp_channel

    except Exception as e:
        print(f"Error sending to Discord: {e}")
        await interaction.channel.send(f"Error sending to Discord: {e}\nAttempting to continue with mission gen...")


async def send_mission_to_subreddit(interaction, mission_params):
    print("User used option r")
    # profit is a float, not an int.
    if float(mission_params.profit) < 10:
        print(f'Not posting the mission from {interaction.user} to reddit due to low profit margin <10k/t.')
        await interaction.channel.send(f'Skipped Reddit posting due to profit margin of {mission_params.profit}k/t being below the PTN 10k/t '
                    f'minimum. (Did you try to post a Wine load?)')
    else:
        message_send = await interaction.channel.send("**Sending to Reddit...**")

        try:

            # post to reddit
            reddit = await get_reddit()
            subreddit = await reddit.subreddit(sub_reddit())
            submission = await subreddit.submit_image(mission_params.reddit_title, image_path=mission_params.reddit_img_name,
                                                    flair_id=reddit_flair_mission_start)
            mission_params.reddit_post_url = submission.permalink
            mission_params.reddit_post_id = submission.id
            if mission_params.rp:
                comment = await submission.reply(f"> {mission_params.rp_text}\n\n&#x200B;\n\n{mission_params.reddit_body}")
            else:
                comment = await submission.reply(mission_params.reddit_body)
            mission_params.reddit_comment_url = comment.permalink
            mission_params.reddit_comment_id = comment.id
            embed = discord.Embed(title=f"Reddit trade alert sent for {mission_params.carrier_data.carrier_long_name}",
                                description=f"https://www.reddit.com{mission_params.reddit_post_url}",
                                color=constants.EMBED_COLOUR_REDDIT)
            await interaction.channel.send(embed=embed)
            await message_send.delete()
            embed = discord.Embed(title=f"{mission_params.carrier_data.carrier_long_name} REQUIRES YOUR UPDOOTS",
                                description=f"https://www.reddit.com{mission_params.reddit_post_url}",
                                color=constants.EMBED_COLOUR_REDDIT)
            channel = bot.get_channel(channel_upvotes())
            upvote_message = await channel.send(embed=embed)
            emoji = bot.get_emoji(upvote_emoji())
            await upvote_message.add_reaction(emoji)
            return
        except Exception as e:
            print(f"Error posting to Reddit: {e}")
            await interaction.channel.send(f"Error posting to Reddit: {e}\nAttempting to continue with rest of mission gen...")


async def send_mission_to_webhook(interaction, mission_params):
    print("User used option w")

    print("Defining Discord embeds...")
    discord_embeds = mission_params.discord_embeds
    webhook_embeds = [discord_embeds.buy_embed, discord_embeds.sell_embed, discord_embeds.webhook_info_embed]

    if mission_params.rp: webhook_embeds.append(discord_embeds.owner_text_embed)

    async with aiohttp.ClientSession() as session: # send messages to each webhook URL
        for webhook_url, webhook_name in zip(mission_params.webhook_urls, mission_params.webhook_names):
            print(f"Sending webhook to {webhook_url}")
            # insert webhook URL
            webhook = Webhook.from_url(webhook_url, session=session, client=bot)

            discord_file = discord.File(mission_params.discord_img_name, filename="image.png")

            # send embeds and image to webhook
            webhook_sent = await webhook.send(file=discord_file, embeds=webhook_embeds, username='Pilots Trade Network', avatar_url=bot.user.avatar.url, wait=True)
            """
            To return to the message later, we need its ID which is the .id attribute
            By default, the object returned from webhook.send is only partial, which limits what we can do with it.
            To access all its attributes and methods like a regular sent message, we first have to fetch it using its ID.
            """
            mission_params.webhook_msg_ids.append(webhook_sent.id) # add the message ID to our MissionParams
            mission_params.webhook_jump_urls.append(webhook_sent.jump_url) # add the jump_url to our MissionParams for convenience

            print(f"Sent webhook trade alert with ID {webhook_sent.id} for webhook URL {webhook_url}")

            embed = discord.Embed(title=f"Webhook trade alert sent for {mission_params.carrier_data.carrier_long_name}:",
                                  description=f"Sent to your webhook **{webhook_name}**: {webhook_sent.jump_url}",
                                  color=constants.EMBED_COLOUR_DISCORD)

            await interaction.channel.send(embed=embed)


async def send_mission_text_to_user(interaction, mission_params):
    print("User used option t")
    embed = discord.Embed(title="Trade Alert (Discord)", description=f"`{mission_params.discord_text}`",
                        color=constants.EMBED_COLOUR_DISCORD)
    await interaction.channel.send(embed=embed)
    if mission_params.rp:
        embed = discord.Embed(title="Roleplay Text (Discord)", description=f"`>>> {mission_params.rp_text}`",
                            color=constants.EMBED_COLOUR_DISCORD)
        await interaction.channel.send(embed=embed)

    embed = discord.Embed(title="Reddit Post Title", description=f"`{mission_params.reddit_title}`",
                        color=constants.EMBED_COLOUR_REDDIT)
    await interaction.channel.send(embed=embed)
    if mission_params.rp:
        embed = discord.Embed(title="Reddit Post Body - PASTE INTO MARKDOWN MODE",
                            description=f"```> {mission_params.rp_text}\n\n{mission_params.reddit_body}```",
                            color=constants.EMBED_COLOUR_REDDIT)
    else:
        embed = discord.Embed(title="Reddit Post Body - PASTE INTO MARKDOWN MODE",
                            description=f"```{mission_params.reddit_body}```", color=constants.EMBED_COLOUR_REDDIT)
    embed.set_footer(text="**REMEMBER TO USE MARKDOWN MODE WHEN PASTING TEXT TO REDDIT.**")
    await interaction.channel.send(embed=embed)
    await interaction.channel.send(file=discord.File(mission_params.reddit_img_name))

    embed = discord.Embed(title=f"Alert Generation Complete for {mission_params.carrier_data.carrier_long_name}",
                        description="Paste Reddit content into **MARKDOWN MODE** in the editor. You can swap "
                                    "back to Fancy Pants afterwards and make any changes/additions or embed "
                                    "the image.\n\nBest practice for Reddit is an image post with a top level"
                                    " comment that contains the text version of the advert. This ensures the "
                                    "image displays with highest possible compatibility across platforms and "
                                    "apps. When mission complete, flag the post as *Spoiler* to prevent "
                                    "image showing and add a comment to inform.",
                        color=constants.EMBED_COLOUR_OK)
    await interaction.channel.send(embed=embed)
    return


"""
Mission generation

The core of MAB: its mission generator

"""

# mission generator called by loading/unloading commands
async def gen_mission(interaction, carrier_name_search_term: str, commodity_search_term: str, system: str, station: str,
                    profit: Union[int, float], pads: str, demand: str, rp: str, mission_type: str):
    current_channel = interaction.channel

    print(f'Mission generation type: {mission_type} with RP: {rp}, requested by {interaction.user}. Request triggered from '
        f'channel {current_channel}.')

    if pads.upper() not in ['M', 'L']:
        # In case a user provides some junk for pads size, gate it
        print(f'Exiting mission generation requested by {interaction.user} as pad size is invalid, provided: {pads}')
        return await interaction.channel.send(f'Sorry, your pad size is not L or M. Provided: {pads}. Mission generation cancelled.')

    mission_params = MissionParams(carrier_name_search_term, commodity_search_term, system, station,
                    profit, pads, demand, rp, mission_type)
    mission_params.print_values()

    # check if commodity can be found, exit gracefully if not
    # gen_mission.returnflag = False
    commodity_data = await find_commodity(commodity_search_term, interaction)
    # if not gen_mission.returnflag:
        #return # we've already given the user feedback on why there's a problem, we just want to quit gracefully now
    if not commodity_data:
        raise ValueError('Missing commodity data')
    mission_params.commodity_data = commodity_data
    
    # check if the user has any webhooks
    webhook_data = find_webhook_from_owner(interaction.user.id)
    if webhook_data:
        for webhook in webhook_data:
            mission_params.webhook_urls.append(webhook.webhook_url)
            mission_params.webhook_names.append(webhook.webhook_name)

    # check if the carrier can be found, exit gracefully if not
    carrier_data = find_carrier(carrier_name_search_term, CarrierDbFields.longname.name)
    if not carrier_data:
        return await interaction.channel.send(f"No carrier found for {carrier_name_search_term}. You can use `/find` or `/owner` to search for carrier names.")
    mission_params.carrier_data = carrier_data

    # check carrier isn't already on a mission TODO change to ID lookup
    mission_data = find_mission(carrier_data.carrier_long_name, "carrier")
    if mission_data:
        embed = discord.Embed(title="Error",
                            description=f"{mission_data.carrier_name} is already on a mission, please "
                                        f"use **m.done** to mark it complete before starting a new mission.",
                            color=constants.EMBED_COLOUR_ERROR)
        await interaction.channel.send(embed=embed)
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
        await interaction.channel.send(embed=embed)
        await assign_carrier_image(interaction, carrier_data.carrier_long_name)
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
            await interaction.channel.send(embed=embed)
            return

    # TODO: This method is way too long, break it up into logical steps.



    try: # this try/except pair is to try and ensure the channel lock is released if something breaks during mission gen
        # otherwise the bot freezes next time the lock is attempted

        embed = discord.Embed(title="Generating and fetching mission alerts...", color=constants.EMBED_COLOUR_QU)
        message_gen = await interaction.channel.send(embed=embed)

        def check_confirm(message):
            # use all to verify that all the characters in the message content are present in the allowed list (dtrx).
            # Anything outwith this grouping will cause all to fail. Use set to throw away any duplicate objects.
            # not sure if the msg.content can ever be None, but lets gate it anyway
            return message.content and message.author == interaction.user and message.channel == interaction.channel and \
                all(character in check_characters for character in set(message.content.lower()))

        def check_rp(message):
            return message.author == interaction.user and message.channel == interaction.channel

        async def default_timeout_message(location):
            await interaction.channel.send(f"**Mission generation cancelled (waiting too long for user input)** ({location})")


        # gen_mission.returnflag = False
        # mission_temp_channel_id = await create_mission_temp_channel(interaction, carrier_data.discord_channel, carrier_data.ownerid)
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
            message_rp = await interaction.channel.send(embed=embed)

            try:

                message_rp_text = await bot.wait_for("message", check=check_rp, timeout=120)
                mission_params.rp_text = message_rp_text.content

            except asyncio.TimeoutError:
                await default_timeout_message('rp')
                return

        # Options that should create a mission db entry will change this to True
        submit_mission = False

        # generate the mission elements

        mission_params.timestamp = get_formatted_date_string()[2]

        mission_params.discord_img_name = await create_carrier_discord_mission_image(mission_params)
        mission_params.discord_text = txt_create_discord(mission_params)
        print("Defined discord elements")

        mission_params.reddit_title = txt_create_reddit_title(mission_params)
        mission_params.reddit_body = txt_create_reddit_body(mission_params)
        mission_params.reddit_img_name = await create_carrier_reddit_mission_image(mission_params)
        print("Defined Reddit elements")

        # check they're happy with output and offer to send
        embed = discord.Embed(title=f"Mission pending for {carrier_data.carrier_long_name}",
                            color=constants.EMBED_COLOUR_OK)
        embed.add_field(name="Mission type", value=f"{mission_type.title()}ing", inline=True)
        embed.add_field(name="Commodity", value=f"{demand} of {commodity_data.name.title()} at {profit}k/unit", inline=True)
        embed.add_field(name="Location",
                        value=f"{station.upper()} station ({pads.upper()}-pads) in system {system.upper()}", inline=True)
        if rp:
            await message_rp.delete()
            await message_rp_text.delete()
            embed.add_field(name="Roleplay text", value=mission_params.rp_text, inline=False)
        message_pending = await interaction.channel.send(embed=embed)
        await message_gen.delete()
        print("Output check displayed")

        embed = discord.Embed(title="Where would you like to send the alert?",
                            description="- (**d**)iscord\n- (**r**)eddit\n- (**w**)ebhooks\n- (**t**)ext for copy/pasting\n\nInput (**x**) to cancel.\n\n"
                            "Additional flags:\n- (**n**) to notify PTN Haulers by role ping\n- (**e**) to flag your mission as EDMC-OFF (this will disable external alert sending).",
                            color=constants.EMBED_COLOUR_QU)
        embed.set_footer(text="Enter all that apply, e.g. **drn** will send alerts to Discord and Reddit and notify PTN Haulers.")
        message_confirm = await interaction.channel.send(embed=embed)
        print("Prompted user for alert destination")

        try:
            check_characters = 'dertnwx'
            msg = await bot.wait_for("message", check=check_confirm, timeout=30)
            edmc_off = True if "e" in msg.content.lower() else False

            if "x" in msg.content.lower():
                async with interaction.channel.typing():
                    # immediately stop if there's an x anywhere in the message, even if there are other proper inputs
                    message_cancelled = await interaction.channel.send("**Mission creation cancelled.**")
                    await msg.delete()
                    await message_confirm.delete()
                    print("User cancelled mission generation")
                    return

            if "t" in msg.content.lower(): # send full text to mission gen channel
                async with interaction.channel.typing():
                    await send_mission_text_to_user(interaction, mission_params)

            if "d" in msg.content.lower(): # send to discord and save to mission database
                async with interaction.channel.typing():
                    submit_mission, mission_temp_channel = await send_mission_to_discord(interaction, mission_params)

                if "r" in msg.content.lower() and not edmc_off: # send to subreddit
                    async with interaction.channel.typing():
                        await send_mission_to_subreddit(interaction, mission_params)

                if "w" in msg.content.lower() and "d" in msg.content.lower() and not edmc_off: # send to webhook
                    async with interaction.channel.typing():
                        await send_mission_to_webhook(interaction, mission_params)

                if "n" in msg.content.lower() and "d" in msg.content.lower(): # notify haulers with role ping
                    async with interaction.channel.typing():
                        print("User used option n")

                        ping_role_id = hauler_role()
                        await mission_temp_channel.send(f"<@&{ping_role_id}>: {mission_params.discord_text}")

                        embed = discord.Embed(title=f"Mission notification sent for {carrier_data.carrier_long_name}",
                                    description=f"Pinged <@&{ping_role_id}> in <#{mission_params.mission_temp_channel_id}>",
                                    color=constants.EMBED_COLOUR_DISCORD)
                        await interaction.channel.send(embed=embed)

            else: # for mission gen to work and be stored in the database, the d option MUST be selected.
                embed = discord.Embed(title="ERROR: Mission generation cancelled",
                                      description="You must include the **d**iscord option to use role pings or send external alerts (Reddit, Webhooks).",
                                      color=constants.EMBED_COLOUR_ERROR)
                await interaction.channel.send(embed=embed)

        except asyncio.TimeoutError:
            await default_timeout_message('notification_type_decision')
            try:
                if mission_params.mission_temp_channel_id:
                    carrier_channel_lock.release()
                    print("Channel lock released")
            finally:
                if mission_params.mission_temp_channel_id:
                    await remove_carrier_channel(mission_params.mission_temp_channel_id, seconds_short)
            return

        print("All options worked through, now clean up")

        # now clear up by deleting the prompt message and user response
        try:
            await msg.delete()
            await message_confirm.delete()
        except Exception as e:
            print(f"Error during clearup: {e}")
            await interaction.channel.send(f"Oops, error detected: {e}\nAttempting to continue with mission gen.")

        if submit_mission:
            await mission_add(mission_params)
            await mission_generation_complete(interaction, mission_params, message_pending)
        cleanup_temp_image_file(mission_params.discord_img_name)
        cleanup_temp_image_file(mission_params.reddit_img_name)
        if mission_params.mission_temp_channel_id:
            await mark_cleanup_channel(mission_params.mission_temp_channel_id, 0)

        print("Reached end of mission generator")
        return
    except Exception as e:
        await interaction.channel.send("Oh no! Something went wrong :( Mission generation aborted.")
        await interaction.channel.send(e)
        print("Something went wrong with mission generation :(")
        print(e)
        carrier_channel_lock.release()
        if mission_params.mission_temp_channel_id:
            await remove_carrier_channel(mission_params.mission_temp_channel_id, seconds_short)


async def create_mission_temp_channel(interaction, discord_channel, owner_id, shortname):
    # create the carrier's channel for the mission

    # first check whether channel already exists

    mission_temp_channel = discord.utils.get(interaction.guild.channels, name=discord_channel)

    # we need to lock the channel to stop it being deleted mid process
    print("Waiting for Mission Generator channel lock...")
    lockwait_msg = await interaction.channel.send("Waiting for channel lock to become available...")
    try:
        await asyncio.wait_for(lock_mission_channel(), timeout=10)
    except asyncio.TimeoutError:
        print("We couldn't get a channel lock after 10 seconds, let's abort rather than wait around.")
        return await interaction.channel.send("Error: Channel lock could not be acquired, please try again. If the problem persists please contact an Admin.")

    await lockwait_msg.delete()

    if mission_temp_channel:
        # channel exists, so reuse it
        mission_temp_channel_id = mission_temp_channel.id
        await interaction.channel.send(f"Found existing mission channel <#{mission_temp_channel_id}>.")
        print(f"Found existing {mission_temp_channel}")
    else:
        # channel does not exist, create it

        topic = f"Use \";stock {shortname}\" to retrieve stock levels for this carrier."

        category = discord.utils.get(interaction.guild.categories, id=trade_cat())
        mission_temp_channel = await interaction.guild.create_text_channel(discord_channel, category=category, topic=topic)
        mission_temp_channel_id = mission_temp_channel.id
        print(f"Created {mission_temp_channel}")

    print(f'Channels: {interaction.guild.channels}')

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
async def mission_add(mission_params):
    backup_database('missions')  # backup the missions database before going any further

    # pickle the mission_params
    pickled_mission_params = pickle.dumps(mission_params)

    print("Called mission_add to write to database")
    mission_db.execute(''' INSERT INTO missions VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?) ''', (
        mission_params.carrier_data.carrier_long_name, mission_params.carrier_data.carrier_identifier, mission_params.mission_temp_channel_id,
        mission_params.commodity_data.name.title(), mission_params.mission_type.lower(), mission_params.system.title(), mission_params.station.title(),
        mission_params.profit, mission_params.pads.upper(), mission_params.demand, mission_params.rp_text, mission_params.reddit_post_id,
        mission_params.reddit_post_url, mission_params.reddit_comment_id, mission_params.reddit_comment_url, mission_params.discord_alert_id, pickled_mission_params
    ))
    missions_conn.commit()
    print("Mission added to db")

    print("Updating last trade timestamp for carrier")
    carrier_db.execute(''' UPDATE carriers SET lasttrade=strftime('%s','now') WHERE p_ID=? ''', ( [ mission_params.carrier_data.pid ] ))
    carriers_conn.commit()

    # now we can release the channel lock
    if mission_params.mission_temp_channel_id:
        carrier_channel_lock.release()
        print("Channel lock released")
    return


async def mission_generation_complete(interaction, mission_params, message_pending):

    # fetch data we just committed back

    mission_db.execute('''SELECT * FROM missions WHERE carrier LIKE (?)''',
                        ('%' + mission_params.carrier_data.carrier_long_name + '%',))
    print('DB command ran, go fetch the result')
    mission_data = MissionData(mission_db.fetchone())
    print(f'Found mission data: {mission_data}')

    # return result to user

    embed_colour = constants.EMBED_COLOUR_LOADING if mission_data.mission_type == 'load' else \
        constants.EMBED_COLOUR_UNLOADING

    mission_description = ''
    if mission_data.rp_text and mission_data.rp_text != 'NULL':
        mission_description = f"> {mission_data.rp_text}"

    embed = discord.Embed(title=f"{mission_data.mission_type.upper()}ING {mission_data.carrier_name} ({mission_data.carrier_identifier})",
                            description=mission_description, color=embed_colour)

    embed = _mission_summary_embed(mission_data, embed)

    embed.set_footer(text="You can use m.done <carrier> to mark the mission complete.")

    await interaction.channel.send(embed=embed)
    await message_pending.delete()
    print("Mission generation complete")
    return