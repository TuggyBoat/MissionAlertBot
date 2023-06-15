"""
Commands for use by CCOs 

"""
# import libraries
from typing import Union

# import discord.py
import discord
from discord import app_commands
from discord.app_commands import Group, command, describe
from discord.ext import commands
from discord.ext.commands import GroupCog

# import local classes
from ptn.missionalertbot.classes.MissionParams import MissionParams

# import local constants
import ptn.missionalertbot.constants as constants
from ptn.missionalertbot.constants import bot, mission_command_channel, certcarrier_role, trainee_role, seconds_long, rescarrier_role, commodities_common

# import local modules
from ptn.missionalertbot.database.database import find_mission
from ptn.missionalertbot.modules.helpers import on_app_command_error, check_text_command_channel, convert_str_to_float_or_int, check_command_channel, check_roles
from ptn.missionalertbot.modules.ImageHandling import assign_carrier_image
from ptn.missionalertbot.modules.MissionGenerator import gen_mission
from ptn.missionalertbot.modules.MissionCleaner import _cleanup_completed_mission


"""
CERTIFIED CARRIER OWNER COMMANDS

carrier_image - CCO
done - alias of cco_complete
complete - CCO/mission
load - CCO/mission
loadrp - CCO/mission
unload - CCO/mission
unloadrp - CCO/mission

"""

async def cco_mission_complete(interaction, carrier, message):
    current_channel = interaction.channel

    print(f'Request received from {interaction.user.display_name} to mark the mission of {carrier} as done from channel: '
        f'{current_channel}')

    mission_data = find_mission(carrier, "carrier")
    if not mission_data:
        embed = discord.Embed(
            description=f"**ERROR**: no trade missions found for carriers matching \"**{carrier}\"**.",
            color=constants.EMBED_COLOUR_ERROR)
        return await interaction.response.send_message(embed=embed, ephemeral=True)

    else:
        embed = discord.Embed(
            description=f"Closing mission for **{mission_data.carrier_name}**...",
            color=constants.EMBED_COLOUR_QU
        )
        await interaction.response.send_message(embed=embed)

    # fill in some info for messages
    formatted_message = f"> {message}\n" if message else ""
    reddit_complete_text = f"    INCOMING WIDEBAND TRANSMISSION: P.T.N. CARRIER MISSION UPDATE\n\n**{mission_data.carrier_name}** mission complete. o7 CMDRs!\n\n{formatted_message}"
    discord_complete_embed = discord.Embed(title=f"{mission_data.carrier_name} MISSION COMPLETE", description=f"{formatted_message}",
                            color=constants.EMBED_COLOUR_OK)
    discord_complete_embed.set_footer(text=f"This mission channel will be removed in {seconds_long()//60} minutes.")

    await _cleanup_completed_mission(interaction, mission_data, reddit_complete_text, discord_complete_embed, formatted_message)

    return


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

    cco_group = Group(name='cco', description='CCO commands')

    # load subcommand
    @cco_group.command(name='load', description='Generate a Fleet Carrier loading mission.')
    @describe(
        carrier = "A unique fragment of the carrier name you want to search for.",
        commodity = "The commodity you want to load.",
        system = "The system your mission takes place in.",
        station = "The station the Fleet Carrier is loading from.",
        profit = 'The profit offered in thousands of credits, e.g. for 10k credits per ton enter \'10\'',
        pads = 'The size of the largest landing pad available at the station.',
        demand = 'The total demand for the commodity on the Fleet Carrier.'
        )
    @check_roles([certcarrier_role(), trainee_role(), rescarrier_role()])
    @check_command_channel(mission_command_channel())
    async def load(self, interaction: discord.Interaction, carrier: str, commodity: str, system: str, station: str,
                profit: str, pads: str, demand: str):
        mission_type = 'load'

        embed = discord.Embed(
            title="COPY/PASTE TEXT FOR THIS COMMAND",
            description=f"```/cco load carrier:{carrier} commodity:{commodity} system:{system} station:{station}"
                        f" profit:{profit} pads:{pads} demand:{demand}```",
            color=constants.EMBED_COLOUR_QU
        )

        await interaction.response.send_message(embed=embed)

        # convert profit from STR to an INT or FLOAT
        profit = convert_str_to_float_or_int(profit)

        params_dict = dict(carrier_name_search_term = carrier, commodity_search_term = commodity, system = system, station = station,
                           profit = profit, pads = pads, demand = demand, mission_type = mission_type)

        mission_params = MissionParams(params_dict)

        await gen_mission(interaction, mission_params)


    # unload subcommand
    @cco_group.command(name='unload', description='Generate a Fleet Carrier unloading mission.')
    @describe(
        carrier = "A unique fragment of the Fleet Carrier name you want to search for.",
        commodity = "The commodity you want to unload.",
        system = "The system your mission takes place in.",
        station = "The station the Fleet Carrier is unloading to.",
        profit = 'The profit offered in thousands of credits, e.g. for 10k credits per ton enter \'10\'',
        pads = 'The size of the largest landing pad available at the station.',
        supply = 'The total amount of the commodity available to buy on the Fleet Carrier.'
        )
    @check_roles([certcarrier_role(), trainee_role(), rescarrier_role()])
    @check_command_channel(mission_command_channel())
    async def unload(self, interaction: discord.Interaction, carrier: str, commodity: str, system: str, station: str,
                profit: str, pads: str, supply: str):
        mission_type = 'unload'

        embed = discord.Embed(
            title="COPY/PASTE TEXT FOR THIS COMMAND",
            description=f"```/cco unload carrier:{carrier} commodity:{commodity} system:{system} station:{station}"
                        f" profit:{profit} pads:{pads} supply:{supply}```",
            color=constants.EMBED_COLOUR_QU
        )

        await interaction.response.send_message(embed=embed)

        # convert profit from STR to an INT or FLOAT
        profit = convert_str_to_float_or_int(profit)

        params_dict = dict(carrier = carrier, commodity = commodity, system = system, station = station,
                           profit = profit, pads = pads, demand = supply, mission_type = mission_type)

        mission_params = MissionParams(params_dict)

        await gen_mission(interaction, mission_params)


    # autocomplete common commodities
    @load.autocomplete("commodity")
    @unload.autocomplete("commodity")
    async def commodity_autocomplete(self, interaction: discord.Interaction, current: str):
        commodities = [] # define the list we will return
        for commodity in commodities_common: # iterate through our common commodities to append them as Choice options to our return list
            commodities.append(app_commands.Choice(name=commodity, value=commodity))
        return commodities # return the list of Choices
    
    # autocomplete pads
    @load.autocomplete("pads")
    @unload.autocomplete("pads")
    async def commodity_autocomplete(self, interaction: discord.Interaction, current: str):
        pads = []
        pads.append(app_commands.Choice(name="Large", value="L"))
        pads.append(app_commands.Choice(name="Medium", value="M"))
        return pads

    """
    CCO mission complete command
    """
    # alias for cco complete
    @cco_group.command(name='done', description='Alias for /cco complete.')
    @describe(message='A message to send to the mission channel and carrier\'s owner')
    @check_roles([certcarrier_role(), trainee_role(), rescarrier_role()])
    @check_command_channel(mission_command_channel())
    async def done(self, interaction: discord.Interaction, carrier: str, *, message: str = None):
        await cco_mission_complete(interaction, carrier, message)

    # CCO command to quickly mark mission as complete, optionally send a reason
    @cco_group.command(name='complete', description='Marks a mission as complete for specified carrier.')
    @describe(message='A message to send to the mission channel and carrier\'s owner')
    @check_roles([certcarrier_role(), trainee_role(), rescarrier_role()])
    @check_command_channel(mission_command_channel())
    async def complete(self, interaction: discord.Interaction, carrier: str, *, message: str = None):
        await cco_mission_complete(interaction, carrier, message)


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
