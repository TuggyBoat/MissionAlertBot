from ptn.missionalertbot.botcommands.DiscordBotCommands import DiscordBotCommands
from ptn.missionalertbot.constants import bot, TOKEN, _production

print(f'MissionAlertBot is connecting against production: {_production}.')


def run():
    """
    Logic to build the bot and run the script.

    :returns: None
    """
    bot.add_cog(DiscordBotCommands())
    bot.start()


if __name__ == '__main__':
    run()
