"""
Commands relating to carrier stock tracking.

"""

# libraries
import asyncio
import json
import re
import requests
from texttable import Texttable # TODO: remove this dependency
import traceback

# discord.py
import discord
from discord import app_commands
from discord.app_commands import Group, command, describe
from discord.ext import commands

# local constants
import ptn.missionalertbot.constants as constants
from ptn.missionalertbot.constants import bot, certcarrier_role, trainee_role, rescarrier_role, mission_command_channel, training_mission_command_channel

# local modules
from ptn.missionalertbot.modules.helpers import check_roles, check_command_channel, flexible_carrier_search_term
from ptn.missionalertbot.modules.StockHelpers import get_fc_stock
from ptn.missionalertbot.modules.ErrorHandler import on_app_command_error, on_generic_error, CustomError, GenericError


# initialise the Cog and attach our global error handler
class StockTracker(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # custom global error handler
    # attaching the handler when the cog is loaded
    # and storing the old handler
    def cog_load(self):
        tree = self.bot.tree
        self._old_tree_error = tree.on_error
        tree.on_error = on_app_command_error

    # detaching the handler when the cog is unloaded
    def cog_unload(self):
        tree = self.bot.tree
        tree.on_error = self._old_tree_error


    @app_commands.command(name='stock', description='Returns stock of a PTN carrier.')
    @app_commands.describe(
           carrier = "A unique fragment of the Fleet Carrier name you want to search for.",
           source = "Choose data source between Frontier API or Inara. Defaults to Frontier API."
        )
    @app_commands.choices(source=[
        discord.app_commands.Choice(name='Frontier API', value='capi'),
        discord.app_commands.Choice(name='Inara', value='inara')
        ])
    async def stock(self, interaction: discord.Interaction, carrier: str = None, source: str = 'capi'):
        carrier_string = f' for carrier {carrier}' if carrier else ''
        source_string = f' from source {source}'
        print(f"📈 Stock check called by {interaction.user} in {interaction.channel}" + carrier_string + source_string)

        try:
            embed = discord.Embed(
                description="⏳ Please wait a moment...",
                color=constants.EMBED_COLOUR_QU
            )

            await interaction.response.send_message(embed=embed)


            # attempt to find matching carrier data
            carrier_data = flexible_carrier_search_term(carrier)
            
            if not carrier_data:  # error condition
                print(f"❌ No carrier found matching search term {carrier}")
                carrier_error_embed = discord.Embed(
                    description=f"❌ No carrier found for '**{carrier}**'. Use `/owner` to see a list of your carriers. If it's not in the list, ask an Admin to add it for you.",
                    color=constants.EMBED_COLOUR_ERROR
                )
                return await interaction.edit_original_response(embed=carrier_error_embed)

            # fetch stock levels

            fcname = carrier_data.carrier_long_name

            try:
                stn_data = get_fc_stock(carrier_data.carrier_identifier, source)
            except Exception as e:
                try:
                    error = f"Error getting data for carrier {carrier_data.carrier_identifier}: {e}"
                    raise CustomError(error)
                except Exception as e:
                    await on_generic_error(interaction, e)
                    traceback.print_exc()
                    stn_data = False

            if stn_data is False:
                embed.description = f"📉 No market data for {carrier_data.carrier_long_name}."
                embed.color=constants.EMBED_COLOUR_QU
                await interaction.edit_original_response(embed=embed)
                return

            com_data = stn_data['commodities']
            loc_data = stn_data['name']
            if com_data == []:
                embed.description = f"📉 No market data for {carrier_data.carrier_long_name}."
                embed.color=constants.EMBED_COLOUR_QU
                await interaction.edit_original_response(embed=embed)
                return

            table = Texttable()
            table.set_cols_align(["l", "r", "r"])
            table.set_cols_valign(["m", "m", "m"])
            table.set_cols_dtype(['t', 'i', 'i'])
            #table.set_deco(Texttable.HEADER | Texttable.HLINES)
            table.set_deco(Texttable.HEADER)
            table.header(["Commodity", "Amount", "Demand"])

            for com in com_data:
                if com['stock'] != 0 or com['demand'] != 0:
                    table.add_row([com['name'], com['stock'], com['demand']])

            msg = "```%s```\n" % ( table.draw() )

            embed = discord.Embed()
            embed.add_field(name = f"{fcname} ({stn_data['sName']}) stock", value = msg, inline = False)
            embed.add_field(name = 'FC Location', value = loc_data, inline = False)
            embed.set_footer(text = f"Data last updated: {stn_data['market_updated']}\nNumbers out of wack? Ensure EDMC is running!")

            await interaction.edit_original_response(embed=embed)

        except Exception as e:
            try:
                raise GenericError(e)
            except Exception as e:
                traceback.print_exc()
                await on_generic_error(interaction, e)






"""@bot.command(name='list', help='Lists all tracked carriers. \n'
                               'Filter: use "wmm" to show only wmm-tracked carriers.')
async def fclist(ctx, Filter=None):
    names = []
    for fc_code, fc_data in FCDATA.items():
        if Filter and 'wmm' not in fc_data:
            continue
        if 'wmm' in fc_data:
            names.append("%s (%s) - WMM" % ( fc_data['FCName'], fc_code))
        else:
            names.append("%s (%s)" % ( fc_data['FCName'], fc_code))
    if not names:
        names = ['No Fleet Carriers are being tracked, add one!']
    print('Listing active carriers')

    carriers = sorted(names)  # Joining the list with newline as the delimeter

    def validate_response(react, user):
        return user == ctx.author and str(react.emoji) in ["◀️", "▶️"]
        # This makes sure nobody except the command sender can interact with the "menu"

    pages = [page for page in chunk(carriers)]

    max_pages = len(pages)
    current_page = 1

    embed = discord.Embed(title=f"{len(carriers)} Tracked Fleet Carriers, Page: #{current_page} of {max_pages}")
    embed.add_field(name = 'Carrier Names', value = '\n'.join(pages[0]))

    # Now go send it and wait on a reaction
    message = await ctx.send(embed=embed)

    # From page 0 we can only go forwards
    if max_pages > 1:
        await message.add_reaction("▶️")

    # 60 seconds time out gets raised by Asyncio
    while True:
        try:
            reaction, user = await bot.wait_for('reaction_add', timeout=60, check=validate_response)
            if str(reaction.emoji) == "▶️" and current_page != max_pages:

                print(f'{ctx.author} requested to go forward a page.')
                current_page += 1   # Forward a page
                new_embed = discord.Embed(title=f"{len(carriers)} Tracked Fleet Carriers, Page: #{current_page} of {max_pages}")
                new_embed.add_field(name='Carrier Names', value='\n'.join(pages[current_page-1]))
                await message.edit(embed=new_embed)

                await message.add_reaction("◀️")
                if current_page == 2:
                    await message.clear_reaction("▶️")
                    await message.add_reaction("▶️")
                elif current_page == max_pages:
                    await message.clear_reaction("▶️")
                else:
                    await message.remove_reaction(reaction, user)

            elif str(reaction.emoji) == "◀️" and current_page > 1:
                print(f'{ctx.author} requested to go back a page.')
                current_page -= 1   # Go back a page

                new_embed = discord.Embed(title=f"{len(carriers)} Tracked Fleet Carriers, Page: #{current_page} of {max_pages}")
                new_embed.add_field(name='Carrier Names', value='\n'.join(pages[current_page-1]))


                await message.edit(embed=new_embed)
                # Ok now we can go forwards, check if we can also go backwards still
                if current_page == 1:
                    await message.clear_reaction("◀️")

                await message.remove_reaction(reaction, user)
                await message.add_reaction("▶️")
            else:
                # It should be impossible to hit this part, but lets gate it just in case.
                print(f'HAL9000 error: {ctx.author} ended in a random state while trying to handle: {reaction.emoji} '
                      f'and on page: {current_page}.')
                # HAl-9000 error response.
                error_embed = discord.Embed(title=f"I'm sorry {ctx.author}, I'm afraid I can't do that.")
                await message.edit(embed=error_embed)
                await message.remove_reaction(reaction, user)

        except asyncio.TimeoutError:
            print(f'Timeout hit during carrier request by: {ctx.author}')
            await ctx.send(f'Closed the active carrier list request from: {ctx.author} due to no input in 60 seconds.')
            await message.delete()
            break
"""