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


def txt_create_discord(carrier_data, mission_type, commodity, station, system, profit, pads, demand, eta_text, mission_temp_channel_id, edmc_off, legacy):
    discord_channel = f"<#{mission_temp_channel_id}>" if mission_temp_channel_id else f"#{carrier_data.discord_channel}"
    discord_text = (
        f"{'**◄ LEGACY UNIVERSE ►** : ' if legacy else ''}"
        f"{'**★ EDMC-OFF MISSION! ★** : ' if edmc_off else ''}"
        f"{discord_channel} {'load' if mission_type == 'load' else 'unload'}ing "
        f"{commodity.name} "
        f"{'from' if mission_type == 'load' else 'to'} **{station.upper()}** station in system "
        f"**{system.upper()}** : {profit}k per unit profit : "
        f"{demand} {'demand' if mission_type == 'load' else 'supply'} : {pads.upper()}-pads"
        f".{eta_text}"
    )
    return discord_text


def txt_create_reddit_title(carrier_data, legacy):
    reddit_title = (
        f"{'◄ LEGACY UNIVERSE ► : ' if legacy else ''}"
        f"P.T.N. TRADE MISSION: "
        f"P.T.N. News - Trade mission - {carrier_data.carrier_long_name} {carrier_data.carrier_identifier}" \
                   f" - {get_formatted_date_string()[0]}"
    )
    return reddit_title


def txt_create_reddit_body(carrier_data, mission_type, commodity, station, system, profit, pads, demand, eta_text, legacy):

    if mission_type == 'load':
        reddit_body = (
            f"    INCOMING WIDEBAND TRANSMISSION: P.T.N. CARRIER LOADING MISSION IN PROGRESS\n"
            f"{'**◄ LEGACY UNIVERSE ►**' if legacy else ''}"
            f"\n\n"
            f"**BUY FROM**: station **{station.upper()}** ({pads.upper()}-pads) in system **{system.upper()}**\n\n**COMMODITY**: "
            f"{commodity.name}\n\n&#x200B;\n\n**SELL TO**: Fleet Carrier **{carrier_data.carrier_long_name} "
            f"{carrier_data.carrier_identifier}{eta_text}**\n\n**PROFIT**: {profit}k/unit : {demand} "
            f"demand\n\n\n\n[Join us on Discord]({constants.REDDIT_DISCORD_LINK_URL}) for "
            f"mission updates and discussion, channel **#{carrier_data.discord_channel}**.")
    else:
        reddit_body = (
            f"    INCOMING WIDEBAND TRANSMISSION: P.T.N. CARRIER UNLOADING MISSION IN PROGRESS\n"
            f"{'**◄ LEGACY UNIVERSE ►** : ' if legacy else ''}"
            f"\n\n"
            f"**BUY FROM**: Fleet Carrier **{carrier_data.carrier_long_name} {carrier_data.carrier_identifier}{eta_text}**"
            f"\n\n**COMMODITY**: {commodity.name}\n\n&#x200B;\n\n**SELL TO**: station "
            f"**{station.upper()}** ({pads.upper()}-pads) in system **{system.upper()}**\n\n**PROFIT**: {profit}k/unit "
            f": {demand} supply\n\n\n\n[Join us on Discord]({constants.REDDIT_DISCORD_LINK_URL}) for mission updates"
            f" and discussion, channel **#{carrier_data.discord_channel}**.")
    return reddit_body