"""
Commands for use by CCOs 

"""
# import libraries
from typing import Union

# import discord.py
import discord
from discord.ext import commands

# import local classes

# import local constants
import ptn.missionalertbot.constants as constants
from ptn.missionalertbot.constants import bot, mission_command_channel, certcarrier_role, trainee_role, seconds_long, rescarrier_role

# import local modules
from ptn.missionalertbot.database.database import find_mission
from ptn.missionalertbot.modules.helpers import on_app_command_error, check_text_command_channel
from ptn.missionalertbot.modules.ImageHandling import assign_carrier_image
from ptn.missionalertbot.modules.MissionGenerator import gen_mission, _cleanup_completed_mission


"""
CERTIFIED CARRIER OWNER COMMANDS

carrier_image - CCO
done - CCO/mission
load - CCO/mission
loadlegacy - CCO/mission
loadrp - CCO/mission
loadrplegacy - CCO/mission
unload - CCO/mission
unloadlegacy - CCO/mission
unloadrp - CCO/mission
unloadrplegacy - CCO/mission

"""


# initialise the Cog and attach our global error handler
class CCOCommands(commands.Cog):
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
    Load/unload commands
    """

    # load commands
    @commands.command(name='load', help='Generate details for a loading mission and optionally broadcast.\n'
                                '\n'
                                'carrier_name_search_term should be a unique part of your carrier\'s name. (Use quotes if spaces are required)\n'
                                'commodity_name_partial should be a unique part of any commodity\'s name.\n'
                                'System and Station names should be enclosed in quotes if they contain spaces.\n'
                                'Profit should be expressed as a simple number e.g. enter 10 for 10k/unit profit.\n'
                                'Pad size should be expressed as L or M.\n'
                                'Demand should be expressed as an absolute number e.g. 20k, 20,000, etc.\n'
                                'ETA is optional and should be expressed as a number of minutes e.g. 15.\n'
                                'Case is automatically corrected for all inputs.')
    @commands.has_any_role(*[certcarrier_role(), trainee_role()])
    @check_text_command_channel(mission_command_channel())
    async def load(self, ctx, carrier_name_search_term: str, commodity_search_term: str, system: str, station: str,
                profit: Union[int, float], pads: str, demand: str, eta: str = None):
        rp = False
        mission_type = 'load'
        legacy = False
        await gen_mission(ctx, carrier_name_search_term, commodity_search_term, system, station, profit, pads, demand,
                        rp, mission_type, eta, legacy)


    @commands.command(name="loadrp", help='Same as load command but prompts user to enter roleplay text\n'
                                    'This is added to the Reddit comment as as a quote above the mission details\n'
                                    'and sent to the carrier\'s Discord channel in quote format if those options are '
                                    'chosen')
    @commands.has_any_role(*[certcarrier_role(), trainee_role()])
    @check_text_command_channel(mission_command_channel())
    async def loadrp(self, ctx, carrier_name_search_term: str, commodity_search_term: str, system: str, station: str,
                    profit: Union[int, float], pads: str, demand: str, eta: str = None):
        rp = True
        mission_type = 'load'
        legacy = False
        await gen_mission(ctx, carrier_name_search_term, commodity_search_term, system, station, profit, pads, demand,
                        rp, mission_type, eta, legacy)


    # legacy load commands
    @commands.command(name='loadlegacy', help='Generate details for a LEGACY loading mission and optionally broadcast.\n'
                                '\n'
                                'carrier_name_search_term should be a unique part of your carrier\'s name. (Use quotes if spaces are required)\n'
                                'commodity_name_partial should be a unique part of any commodity\'s name.\n'
                                'System and Station names should be enclosed in quotes if they contain spaces.\n'
                                'Profit should be expressed as a simple number e.g. enter 10 for 10k/unit profit.\n'
                                'Pad size should be expressed as L or M.\n'
                                'Demand should be expressed as an absolute number e.g. 20k, 20,000, etc.\n'
                                'ETA is optional and should be expressed as a number of minutes e.g. 15.\n'
                                'Case is automatically corrected for all inputs.')
    @commands.has_any_role(*[certcarrier_role(), trainee_role()])
    @check_text_command_channel(mission_command_channel())
    async def loadlegacy(self, ctx, carrier_name_search_term: str, commodity_search_term: str, system: str, station: str,
                profit: Union[int, float], pads: str, demand: str, eta: str = None):
        rp = False
        mission_type = 'load'
        legacy = True
        await gen_mission(ctx, carrier_name_search_term, commodity_search_term, system, station, profit, pads, demand,
                        rp, mission_type, eta, legacy)


    @commands.command(name="loadrplegacy", help='Same as load command but prompts user to enter roleplay text\n'
                                    'This is added to the Reddit comment as as a quote above the mission details\n'
                                    'and sent to the carrier\'s Discord channel in quote format if those options are '
                                    'chosen')
    @commands.has_any_role(*[certcarrier_role(), trainee_role()])
    @check_text_command_channel(mission_command_channel())
    async def loadrplegacy(self, ctx, carrier_name_search_term: str, commodity_search_term: str, system: str, station: str,
                    profit: Union[int, float], pads: str, demand: str, eta: str = None):
        rp = True
        mission_type = 'load'
        legacy = True
        await gen_mission(ctx, carrier_name_search_term, commodity_search_term, system, station, profit, pads, demand,
                        rp, mission_type, eta, legacy)


    # unload commands
    @commands.command(name='unload', help='Generate details for an unloading mission.\n'
                                    '\n'
                                    'carrier_name_search_term should be a unique part of your carrier\'s name. (Use quotes if spaces are required)\n'
                                    'commodity_name_partial should be a unique part of any commodity\'s name.\n'
                                    'System and Station names should be enclosed in quotes if they contain spaces.\n'
                                    'Profit should be expressed as a simple number e.g. enter 10 for 10k/unit profit.\n'
                                    'Pad size should be expressed as L or M.\n'
                                    'Supply should be expressed as an absolute number e.g. 20k, 20,000, etc.\n'
                                    'ETA is optional and should be expressed as a number of minutes e.g. 15.\n'
                                    'Case is automatically corrected for all inputs.')
    @commands.has_any_role(*[certcarrier_role(), trainee_role()])
    @check_text_command_channel(mission_command_channel())
    async def unload(self, ctx, carrier_name_search_term: str, commodity_search_term: str, system: str, station: str,
                    profit: Union[int, float], pads: str, supply: str, eta: str = None):
        rp = False
        mission_type = 'unload'
        legacy = False
        await gen_mission(ctx, carrier_name_search_term, commodity_search_term, system, station, profit, pads, supply, rp,
                        mission_type, eta, legacy)


    @commands.command(name="unloadrp", help='Same as unload command but prompts user to enter roleplay text\n'
                                    'This is added to the Reddit comment as as a quote above the mission details\n'
                                    'and sent to the carrier\'s Discord channel in quote format if those options are '
                                    'chosen')
    @commands.has_any_role(*[certcarrier_role(), trainee_role()])
    @check_text_command_channel(mission_command_channel())
    async def unloadrp(self, ctx, carrier_name_search_term: str, commodity_search_term: str, system: str, station: str,
                    profit: Union[int, float], pads: str, demand: str, eta: str = None):

        rp = True
        mission_type = 'unload'
        legacy = False
        await gen_mission(ctx, carrier_name_search_term, commodity_search_term, system, station, profit, pads, demand,
                        rp, mission_type, eta, legacy)


    # legacy unload commands
    @commands.command(name='unloadlegacy', help='Generate details for a LEGACY unloading mission.\n'
                                    '\n'
                                    'carrier_name_search_term should be a unique part of your carrier\'s name. (Use quotes if spaces are required)\n'
                                    'commodity_name_partial should be a unique part of any commodity\'s name.\n'
                                    'System and Station names should be enclosed in quotes if they contain spaces.\n'
                                    'Profit should be expressed as a simple number e.g. enter 10 for 10k/unit profit.\n'
                                    'Pad size should be expressed as L or M.\n'
                                    'Supply should be expressed as an absolute number e.g. 20k, 20,000, etc.\n'
                                    'ETA is optional and should be expressed as a number of minutes e.g. 15.\n'
                                    'Case is automatically corrected for all inputs.')
    @commands.has_any_role(*[certcarrier_role(), trainee_role()])
    @check_text_command_channel(mission_command_channel())
    async def unloadlegacy(self, ctx, carrier_name_search_term: str, commodity_search_term: str, system: str, station: str,
                    profit: Union[int, float], pads: str, supply: str, eta: str = None):
        rp = False
        mission_type = 'unload'
        legacy = True
        await gen_mission(ctx, carrier_name_search_term, commodity_search_term, system, station, profit, pads, supply, rp,
                        mission_type, eta, legacy)


    @commands.command(name="unloadrplegacy", help='Same as unload command but prompts user to enter roleplay text\n'
                                    'This is added to the Reddit comment as as a quote above the mission details\n'
                                    'and sent to the carrier\'s Discord channel in quote format if those options are '
                                    'chosen')
    @commands.has_any_role(*[certcarrier_role(), trainee_role()])
    @check_text_command_channel(mission_command_channel())
    async def unloadrplegacy(self, ctx, carrier_name_search_term: str, commodity_search_term: str, system: str, station: str,
                    profit: Union[int, float], pads: str, demand: str, eta: str = None):
        rp = True
        mission_type = 'unload'
        legacy = True
        await gen_mission(ctx, carrier_name_search_term, commodity_search_term, system, station, profit, pads, demand,
                        rp, mission_type, eta, legacy)



    """
    CCO mission complete command
    """


    # CO command to quickly mark mission as complete, optionally send some RP text
    @commands.command(name='done', help='Marks a mission as complete for specified carrier.\n\n'
                                'Deletes trade alert in Discord and sends messages to carrier channel, reddit and owner if '
                                'appropriate.\n\nAnything after the carrier name will be treated as a '
                                'quote to be sent along with the completion notice. This can be used for RP if desired.')
    @commands.has_any_role(*[certcarrier_role(), trainee_role(), rescarrier_role()])
    @check_text_command_channel(mission_command_channel())
    async def done(self, ctx, carrier_name_search_term: str, *, rp: str = None):
        async with ctx.typing():

            current_channel = ctx.channel

            print(f'Request received from {ctx.author} to mark the mission of {carrier_name_search_term} as done from channel: '
                f'{current_channel}')

            mission_data = find_mission(carrier_name_search_term, "carrier")
            if not mission_data:
                embed = discord.Embed(
                    description=f"**ERROR**: no trade missions found for carriers matching \"**{carrier_name_search_term}\"**.",
                    color=constants.EMBED_COLOUR_ERROR)
                return await ctx.send(embed=embed)

            else:
                pass

        # fill in some info for messages
        desc_msg = f"> {rp}\n" if rp else ""
        reddit_complete_text = f"    INCOMING WIDEBAND TRANSMISSION: P.T.N. CARRIER MISSION UPDATE\n\n**{mission_data.carrier_name}** mission complete. o7 CMDRs!\n\n{desc_msg}"
        discord_complete_embed = discord.Embed(title=f"{mission_data.carrier_name} MISSION COMPLETE", description=f"{desc_msg}",
                                color=constants.EMBED_COLOUR_OK)
        discord_complete_embed.set_footer(text=f"This mission channel will be removed in {seconds_long()//60} minutes.")

        await _cleanup_completed_mission(ctx, mission_data, reddit_complete_text, discord_complete_embed, desc_msg)

        return


    """
    Change FC image command
    """


    # change FC background image
    @commands.command(name='carrier_image', help='Change the background image for the specified carrier:\n\n'
                                            'Use with carrier\'s name as argument to check the '
                                            'carrier\'s image or begin upload of a new image.')
    @commands.has_any_role(*[certcarrier_role(), trainee_role()])
    @check_text_command_channel(mission_command_channel())
    async def carrier_image(self, ctx, lookname):
        print(f"{ctx.author} called m.carrier_image for {lookname}")

        await assign_carrier_image(ctx, lookname)

        return
