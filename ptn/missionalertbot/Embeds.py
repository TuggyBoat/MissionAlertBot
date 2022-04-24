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


