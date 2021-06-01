# Production variables
PROD_FLAIR_MISSION_START = "d01e6808-9235-11eb-9cc0-0eb650439ee7"
PROD_FLAIR_MISSION_STOP = "eea2d818-9235-11eb-b86f-0e50eec082f5"

PROD_DISCORD_GUILD = 800080948716503040 # PTN Discord server
PROD_TRADE_ALERTS_ID = 801798469189763073  # trade alerts channel ID for PTN main server
PROD_SUB_REDDIT = "PilotsTradeNetwork"  # subreddit for live
PROD_CHANNEL_UPVOTES = 828279034387103744    # The ID for the updoots channel
PROD_MISSION_CHANNEL = 822603169104265276    # The ID for the production mission channel
PROD_BOT_COMMAND_CHANNEL = 802523724674891826   # Bot backend commands are locked to a channel
PROD_BOT_SPAM_CHANNEL = 801258393205604372 # Certain bot logging messages go here
PROD_UPVOTE_EMOJI = 828287733227192403 # upvote emoji on live server

# Testing variables

# reddit flair IDs - testing sub
TEST_FLAIR_MISSION_START = "3cbb1ab6-8e8e-11eb-93a1-0e0f446bc1b7"
TEST_FLAIR_MISSION_STOP = "4242a2e2-8e8e-11eb-b443-0e664851dbff"

TEST_DISCORD_GUILD = 818174236480897055 # test Discord server
TEST_TRADE_ALERTS_ID = 843252609057423361  # trade alerts channel ID for PTN test server
TEST_SUB_REDDIT = "PTNBotTesting"  # subreddit for testing
TEST_CHANNEL_UPVOTES = 839918504676294666    # The ID for the updoots channel on test
TEST_MISSION_CHANNEL = 842138710651961364    # The ID for the production mission channel
TEST_BOT_COMMAND_CHANNEL = 842152343441375283   # Bot backend commands are locked to a channel
TEST_BOT_SPAM_CHANNEL = 842525081858867211 # Bot logging messages on the test server
TEST_UPVOTE_EMOJI = 849388681382068225 # upvote emoji on test server

EMBED_COLOUR_LOADING = 0x80ffff         # blue
EMBED_COLOUR_UNLOADING = 0x80ff80       # green
EMBED_COLOUR_REDDIT = 0xff0000          # red
EMBED_COLOUR_DISCORD = 0x8080ff         # purple
EMBED_COLOUR_RP = 0xff00ff              # pink
EMBED_COLOUR_ERROR = 0x800000           # dark red
EMBED_COLOUR_QU = 0x80ffff              # same as loading
EMBED_COLOUR_OK = 0x80ff80              # same as unloading

REDDIT_DISCORD_LINK_URL = \
    'https://www.reddit.com/r/PilotsTradeNetwork/comments/l0y7dk/pilots_trade_network_intergalactic_discord_server/'


def get_constant(production: bool):
    """
    Function takes a boolean and returns a dict containing the various parameters for that object.

    :param bool production: Whether you want the production or test environment variable
    :returns: The constant object. Returns are strings, with exception of Trade alerts which are ints
    :rtype: dict
    """
    if production:
        result = {
            'MISSION_START': PROD_FLAIR_MISSION_START,
            'MISSION_STOP': PROD_FLAIR_MISSION_STOP,
            'BOT_GUILD': PROD_DISCORD_GUILD,
            'SUB_REDDIT': PROD_SUB_REDDIT,
            'TRADE_ALERTS_ID': PROD_TRADE_ALERTS_ID,
            'CHANNEL_UPVOTES': PROD_CHANNEL_UPVOTES,
            'MISSION_CHANNEL': PROD_MISSION_CHANNEL,
            'BOT_COMMAND_CHANNEL': PROD_BOT_COMMAND_CHANNEL,
            'BOT_SPAM_CHANNEL': PROD_BOT_SPAM_CHANNEL,
            'UPVOTE_EMOJI': PROD_UPVOTE_EMOJI
        }
    else:
        result = {
            'MISSION_START': TEST_FLAIR_MISSION_START,
            'MISSION_STOP': TEST_FLAIR_MISSION_STOP,
            'BOT_GUILD': TEST_DISCORD_GUILD,
            'SUB_REDDIT': TEST_SUB_REDDIT,
            'TRADE_ALERTS_ID': TEST_TRADE_ALERTS_ID,
            'CHANNEL_UPVOTES': TEST_CHANNEL_UPVOTES,
            'MISSION_CHANNEL': TEST_MISSION_CHANNEL,
            'BOT_COMMAND_CHANNEL': TEST_BOT_COMMAND_CHANNEL,
            'BOT_SPAM_CHANNEL': TEST_BOT_SPAM_CHANNEL,
            'UPVOTE_EMOJI': TEST_UPVOTE_EMOJI
        }

    return result
