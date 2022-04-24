# common embeds and fields
import discord
from ptn.missionalertbot.database.database import find_mission
import ptn.missionalertbot.constants as constants


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

    mission_description = ''
    if mission_data.rp_text and mission_data.rp_text != 'NULL':
        mission_description = f"> {mission_data.rp_text}"

    embed = discord.Embed(title=f"{mission_data.mission_type.upper()}ING {mission_data.carrier_name} ({mission_data.carrier_identifier})",
                            description=mission_description, color=embed_colour)

    embed = _mission_summary_embed(mission_data, embed)

    embed.set_footer(text="You can use m.complete if the mission is complete.")
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

# return an embed summarising a carrier database entry
def _add_common_embed_fields(embed, carrier_data):
    embed.add_field(name="Carrier Name", value=f"{carrier_data.carrier_long_name}", inline=True)
    embed.add_field(name="Carrier ID", value=f"{carrier_data.carrier_identifier}", inline=True)
    embed.add_field(name="Database Entry", value=f"{carrier_data.pid}", inline=True)
    embed.add_field(name="Discord Channel", value=f"#{carrier_data.discord_channel}", inline=True)
    embed.add_field(name="Owner", value=f"<@{carrier_data.ownerid}>", inline=True)
    embed.add_field(name="Shortname", value=f"{carrier_data.carrier_short_name}", inline=True)
    embed.add_field(name="Last Trade", value=f"<t:{carrier_data.lasttrade}> (<t:{carrier_data.lasttrade}:R>)", inline=True)
    # shortname is not relevant to users and will be auto-generated in future
    return embed