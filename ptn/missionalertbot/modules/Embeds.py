"""
A module containing embeds that are required by multiple functions.

STATUS: This file is complete, but needs to be imported into modules that use it
"""

# import libraries
import os
from datetime import timezone, datetime

# import discord.py
import discord

# import local classes
import ptn.missionalertbot.classes.CarrierData as CarrierData

# import local constants
import ptn.missionalertbot.constants as constants

#import local modules
from ptn.missionalertbot.database.database import find_mission


# return an embed featuring either the active mission or the not found message
async def _is_mission_active_embed(carrier_data):
    print("Called _is_mission_active_embed")
    # look to see if the carrier is on an active mission
    mission_data = find_mission(carrier_data.carrier_long_name, "carrier")

    if not mission_data:
        # if there's no result, make our embed tell the user this
        embed = discord.Embed(description=f"**{carrier_data.carrier_long_name}** doesn't seem to be on a trade"
                                            f" mission right now.",
                                color=constants.EMBED_COLOUR_OK)
        return embed

    # mission data exists so format it for the user as an embed

    embed_colour = constants.EMBED_COLOUR_LOADING if mission_data.mission_type == 'load' else \
        constants.EMBED_COLOUR_UNLOADING

    mission_description = mission_data.rp_text if not mission_data.rp_text == None else ''

    embed = discord.Embed(title=f"{mission_data.mission_type.upper()}ING {mission_data.carrier_name} ({mission_data.carrier_identifier})",
                            description=mission_description, color=embed_colour)

    embed = _mission_summary_embed(mission_data, embed)

    embed.set_footer(text="You can use /mission complete if the mission is complete.")
    return embed


# return an embed summarising a mission database entry
def _mission_summary_embed(mission_data, embed):
    embed.add_field(name="System", value=f"{mission_data.system.upper()}", inline=True)
    embed.add_field(name="Station", value=f"{mission_data.station.upper()} ({mission_data.pad_size}-pads)",
                    inline=True)
    embed.add_field(name="Commodity", value=f"{mission_data.commodity.upper()}", inline=True)
    embed.add_field(name="Quantity and profit",
                    value=f"{mission_data.demand} units at {mission_data.profit}k profit per unit", inline=True)
    return embed


# return an embed summarising all missions of the defined type (for /missions)
def _format_missions_embed(mission_data_list, embed):
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


# returns an embed showing all fields from an entry in the carrier database
async def _configure_all_carrier_detail_embed(embed, carrier_data: CarrierData):
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


# embed generator for send_notice commands
async def _generate_cc_notice_embed(channel_id, user, avatar, title, message, image_url):
    print(f"generating embed for CC notice in channel {channel_id}")

    thumb_file = None

    print(f"Looking for CC image in {constants.CC_IMAGE_PATH}...")

    if os.path.isfile(f"{constants.CC_IMAGE_PATH}/{channel_id}.png"):
        print(f"Found CC image file {constants.CC_IMAGE_PATH}/{channel_id}.png")
        thumb_file = discord.File(f'{constants.CC_IMAGE_PATH}/{channel_id}.png', filename='image.png')
        print(thumb_file)

    embed = discord.Embed(title=title, description=message, color=constants.EMBED_COLOUR_QU)
    embed.set_author(name=user, icon_url=avatar)
    embed.set_image(url=image_url)
    if thumb_file: embed.set_thumbnail(url='attachment://image.png')
    embed.timestamp= datetime.now(tz=timezone.utc)
    embed.set_footer(text="Use \"/notify_me\" in this channel to sign up for future notifications."
                    "\nYou can opt out at any time by using \"/notify_me\" again.")

    return embed, thumb_file

# add common embed fields for carrier info
def _add_common_embed_fields(embed, carrier_data, ctx_interaction):
    embed.add_field(name="Carrier Name", value=f"{carrier_data.carrier_long_name}", inline=True)
    embed.add_field(name="Carrier ID", value=f"{carrier_data.carrier_identifier}", inline=True)
    embed.add_field(name="Database Entry", value=f"{carrier_data.pid}", inline=True)

    # make the channel field a clickable link if there's an active channel by that name
    channel = discord.utils.get(ctx_interaction.guild.channels, name=carrier_data.discord_channel)
    discord_channel = f"<#{channel.id}>" if channel else f"#{carrier_data.discord_channel}"
    embed.add_field(name="Discord Channel", value=f"{discord_channel}", inline=True)

    embed.add_field(name="Owner", value=f"<@{carrier_data.ownerid}>", inline=True)
    embed.add_field(name="Market Data", value=f"`;stock {carrier_data.carrier_short_name}`", inline=True)
    embed.add_field(name="Last Trade", value=f"<t:{carrier_data.lasttrade}> (<t:{carrier_data.lasttrade}:R>)", inline=True)
    # shortname is not relevant to users and will be auto-generated in future
    return embed