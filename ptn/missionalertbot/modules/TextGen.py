"""
TextGen.py

Functions to generate formatted texts for use by the bot.

Dependencies: constants, DateString
"""

# import local constants
import ptn.missionalertbot.constants as constants

# import local libraries
from ptn.missionalertbot.modules.DateString import get_formatted_date_string



"""
TEXT GEN FUNCTIONS
"""


def txt_create_discord(mission_params):
    discord_channel = f"<#{mission_params.mission_temp_channel_id}>" if mission_params.mission_temp_channel_id else f"#{mission_params.carrier_data.discord_channel}"
    discord_text = (
        f"{'**★ EDMC-OFF MISSION! ★** : ' if mission_params.edmc_off else ''}"
        f"{discord_channel} {'load' if mission_params.mission_type == 'load' else 'unload'}ing "
        f"{mission_params.commodity_data.name} "
        f"{'from' if mission_params.mission_type == 'load' else 'to'} **{mission_params.station.upper()}** station in system "
        f"**{mission_params.system.upper()}** : {mission_params.profit}k per unit profit : "
        f"{mission_params.demand} {'demand' if mission_params.mission_type == 'load' else 'supply'} : {mission_params.pads.upper()}-pads"
        f".{mission_params.eta_text}"
    )
    return discord_text


def txt_create_reddit_title(mission_params):
    reddit_title = (
        f"P.T.N. TRADE MISSION: "
        f"P.T.N. News - Trade mission - {mission_params.carrier_data.carrier_long_name} {mission_params.carrier_data.carrier_identifier}" \
                   f" - {get_formatted_date_string()[0]}"
    )
    return reddit_title


def txt_create_reddit_body(mission_params):

    if mission_params.mission_type == 'load':
        reddit_body = (
            f"    INCOMING WIDEBAND TRANSMISSION: P.T.N. CARRIER LOADING MISSION IN PROGRESS\n"
            f"\n\n"
            f"**BUY FROM**: station **{mission_params.station.upper()}** ({mission_params.pads.upper()}-pads) in system **{mission_params.system.upper()}**\n\n**COMMODITY**: "
            f"{mission_params.commodity_data.name}\n\n&#x200B;\n\n**SELL TO**: Fleet Carrier **{mission_params.carrier_data.carrier_long_name} "
            f"{mission_params.carrier_data.carrier_identifier}{mission_params.eta_text}**\n\n**PROFIT**: {mission_params.profit}k/unit : {mission_params.demand} "
            f"demand\n\n\n\n[Join us on Discord]({constants.REDDIT_DISCORD_LINK_URL}) for "
            f"mission updates and discussion, channel **#{mission_params.carrier_data.discord_channel}**.")
    else:
        reddit_body = (
            f"    INCOMING WIDEBAND TRANSMISSION: P.T.N. CARRIER UNLOADING MISSION IN PROGRESS\n"
            f"\n\n"
            f"**BUY FROM**: Fleet Carrier **{mission_params.carrier_data.carrier_long_name} {mission_params.carrier_data.carrier_identifier}{mission_params.eta_text}**"
            f"\n\n**COMMODITY**: {mission_params.commodity_data.name}\n\n&#x200B;\n\n**SELL TO**: station "
            f"**{mission_params.station.upper()}** ({mission_params.pads.upper()}-pads) in system **{mission_params.system.upper()}**\n\n**PROFIT**: {mission_params.profit}k/unit "
            f": {mission_params.demand} supply\n\n\n\n[Join us on Discord]({constants.REDDIT_DISCORD_LINK_URL}) for mission updates"
            f" and discussion, channel **#{mission_params.carrier_data.discord_channel}**.")
    return reddit_body