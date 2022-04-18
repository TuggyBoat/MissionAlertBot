import os
import sys

from discord.ext import commands, tasks

from ptn.adroomba.constants import get_bot_control_channel, get_trades_channel, get_task_interval, get_task_msg_expire, bot
from ptn.adroomba._metadata import __version__

from datetime import datetime, timezone, timedelta

class DiscordBotCommands(commands.Cog):
    """
    This class is a collection of generic blocks used throughout the booze bot.
    """

    @commands.Cog.listener()
    async def on_ready(self):
        """
        We create a listener for the connection event.

        :returns: None
        """
        print(f'{bot.user.name} has connected to Discord server version: {__version__}')
        bot_channel = bot.get_channel(get_bot_control_channel())
        await bot_channel.send(f'{bot.user.name} has connected to Discord server version: {__version__}')
        await self.start_roomba_task()

    @commands.Cog.listener()
    async def on_disconnect(self):
        print(f'AdRoomba has disconnected from discord server, version: {__version__}.')

    @commands.command(name='ping', help='Ping the bot')
    @commands.has_role('Admin')
    async def ping(self, ctx):
        """
        Ping the bot and get a response

        :param discord.Context ctx: The Discord context object
        :returns: None
        """
        await ctx.send(f"**{bot.user.name} is here!**")

    # quit the bot
    @commands.command(name='exit', help="Stops the bots process on the VM, ending all functions.")
    @commands.has_role('Admin')
    async def exit(self, ctx):
        """
        Stop-quit command for the bot.

        :param discord.ext.commands.Context ctx: The Discord context object
        :returns: None
        """
        print(f'User {ctx.author} requested to exit')
        await ctx.send(f"k thx bye")
        await sys.exit("User requested exit.")

    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        """
        A listener that fires off on a particular error case.

        :param discord.ext.commands.Context ctx: The discord context object
        :param discord.ext.commands.errors error: The error object
        :returns: None
        """
        if isinstance(error, commands.BadArgument):
            await ctx.send('**Bad argument!**')
        elif isinstance(error, commands.CommandNotFound):
            await ctx.send("**Invalid command.**")
        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.send('**Please include all required parameters.** Use r.help <command> for details.')
        elif isinstance(error, commands.MissingPermissions):
            await ctx.send('**You must be a Carrier Owner to use this command.**')
        else:
            await ctx.send(f"Sorry, that didn't work. Check your syntax and permissions, error: {error}")

    @commands.command(name='update', help="Restarts the bot.")
    @commands.has_role('Admin')
    async def update(self, ctx):
        """
        Restarts the application for updates to take affect on the local system.
        """
        print(f'Restarting the application to perform updates requested by {ctx.author}')
        os.execv(sys.executable, ['python'] + sys.argv)

    @commands.command(name='version', help="Logs the bot version")
    @commands.has_role('Admin')
    async def version(self, ctx):
        """
        Logs the bot version

        :param discord.ext.commands.Context ctx: The Discord context object
        :returns: None
        """
        print(f'User {ctx.author} requested the version: {__version__}.')
        await ctx.send(f"{bot.user.name} is on version: {__version__}.")

    @tasks.loop(seconds=get_task_interval())
    async def clear_trade_history(self, channel, max_age=get_task_msg_expire()):
        # clear all messages older than 60 seconds that are not pinned from the channel history
        async for message in channel.history(limit=None, oldest_first=True):
            if not message.pinned:
                try:
                    if message.created_at < (datetime.now(timezone.utc) - timedelta(seconds=max_age)):
                        await message.delete()
                except TypeError:
                    # TZ bug in discord.py, this is fixed in discord.py >2.0.0
                    if message.created_at < (datetime.now() - timedelta(seconds=max_age)):
                        await message.delete()
                except Exception as e:
                    bot_channel = bot.get_channel(get_bot_control_channel())
                    await bot_channel.send(f'Something has gone horribly wrong with the clear_trade_history task: {e}')

    async def start_roomba_task(self):
        if self.clear_trade_history.is_running():
            print("start_roomba_task: task is_running(), cannot start.")
            return False
        trades_channel = bot.get_channel(get_trades_channel())
        print("Starting clear_trades_history background task")
        self.clear_trade_history.start(trades_channel)

    @commands.command(name='status', help='Check the background task status')
    @commands.has_any_role('Bot Handler', 'Admin')
    async def status(self, ctx):
        if not self.clear_trade_history.is_running() or self.clear_trade_history.failed():
            await ctx.send(f'background task has failed, restarting...')
            await self.start_roomba_task()
        else:
            await ctx.send(f'background task is running. task interval is {get_task_interval()} seconds. message expiry is {get_task_msg_expire()} seconds.')