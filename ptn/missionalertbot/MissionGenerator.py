# generates missions from user input
import asyncio
from ptn.missionalertbot.GetFormattedDateString import get_formatted_date_string
import ptn.missionalertbot.constants as constants


"""
Text generation functions
"""

def txt_create_discord(carrier_data, mission_type, commodity, station, system, profit, pads, demand, eta_text, mission_temp_channel_id):
    discord_text = f"<#{mission_temp_channel_id}> {'load' if mission_type == 'load' else 'unload'}ing " \
                   f"{commodity.name} " \
                   f"{'from' if mission_type == 'load' else 'to'} **{station.upper()}** station in system " \
                   f"**{system.upper()}** : {profit}k per unit profit : "\
                   f"{demand} {'demand' if mission_type == 'load' else 'supply'} : {pads.upper()}-pads" \
                   f".{eta_text}"
    return discord_text


def txt_create_reddit_title(carrier_data):
    reddit_title = f"P.T.N. News - Trade mission - {carrier_data.carrier_long_name} {carrier_data.carrier_identifier}" \
                   f" - {get_formatted_date_string()[0]}"
    return reddit_title


def txt_create_reddit_body(carrier_data, mission_type, commodity, station, system, profit, pads, demand, eta_text):

    if mission_type == 'load':
        reddit_body = (
            f"    INCOMING WIDEBAND TRANSMISSION: P.T.N. CARRIER LOADING MISSION IN PROGRESS\n\n**BUY FROM**: station "
            f"**{station.upper()}** ({pads.upper()}-pads) in system **{system.upper()}**\n\n**COMMODITY**: "
            f"{commodity.name}\n\n&#x200B;\n\n**SELL TO**: Fleet Carrier **{carrier_data.carrier_long_name} "
            f"{carrier_data.carrier_identifier}{eta_text}**\n\n**PROFIT**: {profit}k/unit : {demand} "
            f"demand\n\n\n\n[Join us on Discord]({constants.REDDIT_DISCORD_LINK_URL}) for "
            f"mission updates and discussion, channel **#{carrier_data.discord_channel}**.")
    else:
        reddit_body = (
            f"    INCOMING WIDEBAND TRANSMISSION: P.T.N. CARRIER UNLOADING MISSION IN PROGRESS\n\n**BUY FROM**: Fleet "
            f"Carrier **{carrier_data.carrier_long_name} {carrier_data.carrier_identifier}{eta_text}**"
            f"\n\n**COMMODITY**: {commodity.name}\n\n&#x200B;\n\n**SELL TO**: station "
            f"**{station.upper()}** ({pads.upper()}-pads) in system **{system.upper()}**\n\n**PROFIT**: {profit}k/unit "
            f": {demand} supply\n\n\n\n[Join us on Discord]({constants.REDDIT_DISCORD_LINK_URL}) for mission updates"
            f" and discussion, channel **#{carrier_data.discord_channel}**.")
    return reddit_body


# channel lock function
carrier_channel_lock = asyncio.Lock()

async def lock_mission_channel():
    print("Attempting channel lock...")
    await carrier_channel_lock.acquire()
    print("Channel lock acquired.")

