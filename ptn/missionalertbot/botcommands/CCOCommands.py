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

# import local constants
import ptn.missionalertbot.constants as constants
from ptn.missionalertbot.constants import bot, mission_command_channel, certcarrier_role, trainee_role, seconds_long, rescarrier_role

# import local modules
from ptn.missionalertbot.database.database import find_mission
from ptn.missionalertbot.modules.helpers import on_app_command_error, check_text_command_channel, convert_str_to_float_or_int, check_command_channel, check_roles
from ptn.missionalertbot.modules.ImageHandling import assign_carrier_image
from ptn.missionalertbot.modules.MissionGenerator import gen_mission
from ptn.missionalertbot.modules.MissionCleaner import _cleanup_completed_mission


"""
CERTIFIED CARRIER OWNER COMMANDS

carrier_image - CCO
done - CCO/mission
load - CCO/mission
loadrp - CCO/mission
unload - CCO/mission
unloadrp - CCO/mission

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

    cco_group = Group(name='cco', description='CCO commands')

    # load subcommand
    @cco_group.command(name='load', description='Generate a Fleet Carrier loading mission.')
    @describe(
        carrier = "A unique fragment of the carrier name you want to search for.",
        commodity = "A unique fragment of the commodity name you want to search for.",
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
        rp = False
        mission_type = 'load'

        # convert profit from STR to an INT or FLOAT
        profit = convert_str_to_float_or_int(profit)

        await gen_mission(interaction, carrier, commodity, system, station, profit, pads, demand,
                        rp, mission_type)


    # unload subcommand
    @cco_group.command(name='unload', description='Generate a Fleet Carrier unloading mission.')
    @describe(
        carrier = "A unique fragment of the Fleet Carrier name you want to search for.",
        commodity = "A unique fragment of the commodity name you want to search for.",
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
        rp = False
        mission_type = 'unload'

        # convert profit from STR to an INT or FLOAT
        profit = convert_str_to_float_or_int(profit)

        await gen_mission(interaction, carrier, commodity, system, station, profit, pads, supply, rp,
                        mission_type)


    """
    CCO mission complete command
    """


    # CO command to quickly mark mission as complete, optionally send some RP text
    @cco_group.command(name='done', description='Marks a mission as complete for specified carrier.')
    @describe()
    @check_roles([certcarrier_role(), trainee_role(), rescarrier_role()])
    @check_command_channel(mission_command_channel())
    async def done(self, interaction: discord.Interaction, carrier: str, *, message: str = None):
        async with interaction.channel.typing():

            current_channel = interaction.channel

            print(f'Request received from {interaction.user.display_name} to mark the mission of {carrier} as done from channel: '
                f'{current_channel}')

            mission_data = find_mission(carrier, "carrier")
            if not mission_data:
                embed = discord.Embed(
                    description=f"**ERROR**: no trade missions found for carriers matching \"**{carrier}\"**.",
                    color=constants.EMBED_COLOUR_ERROR)
                return await interaction.response.send_message(embed=embed)

            else:
                embed = discord.Embed(
                    description=f"Closing mission for {mission_data.carrier_name}...",
                    color=constants.EMBED_COLOUR_QU
                )
                await interaction.response.send_message(embed=embed)

        # fill in some info for messages
        desc_msg = f"> {message}\n" if message else ""
        reddit_complete_text = f"    INCOMING WIDEBAND TRANSMISSION: P.T.N. CARRIER MISSION UPDATE\n\n**{mission_data.carrier_name}** mission complete. o7 CMDRs!\n\n{desc_msg}"
        discord_complete_embed = discord.Embed(title=f"{mission_data.carrier_name} MISSION COMPLETE", description=f"{desc_msg}",
                                color=constants.EMBED_COLOUR_OK)
        discord_complete_embed.set_footer(text=f"This mission channel will be removed in {seconds_long()//60} minutes.")

        embed = await _cleanup_completed_mission(interaction, mission_data, reddit_complete_text, discord_complete_embed, desc_msg)

        # notify user in mission gen channel

        await interaction.edit_original_response(embed=embed)

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
