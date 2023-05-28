from ptn.missionalertbot.botcommands.CCOCommands import CCOCommands
from ptn.missionalertbot.botcommands.CTeamCommands import CTeamCommands
from ptn.missionalertbot.botcommands.DatabaseInteraction import DatabaseInteraction
from ptn.missionalertbot.botcommands.GeneralCommands import GeneralCommands
# from ptn.missionalertbot.botcommands.Helper import Helper
# ^ for when we transition to full slash commands
from ptn.missionalertbot.constants import bot, TOKEN, _production
from ptn.missionalertbot.database.database import build_database_on_startup



print(f'Mission Alert Bot is connecting against production: {_production}.')


def run():
    """
    Logic to build the bot and run the script.

    :returns: None
    """
    build_database_on_startup()
    bot.add_cog(CCOCommands(bot))
    bot.add_cog(CTeamCommands())
    bot.add_cog(DatabaseInteraction())
    bot.add_cog(GeneralCommands())
    # bot.add_cog(Helper())
    bot.run(TOKEN)


if __name__ == '__main__':
    run()