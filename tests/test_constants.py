from constants import get_constant, PROD_FLAIR_MISSION_START, PROD_FLAIR_MISSION_STOP, PROD_TRADE_ALERTS_ID, \
    PROD_SUB_REDDIT, TEST_FLAIR_MISSION_START, TEST_FLAIR_MISSION_STOP, TEST_TRADE_ALERTS_ID, TEST_SUB_REDDIT, \
    PROD_CHANNEL_UPVOTES, TEST_CHANNEL_UPVOTES, PROD_BOT_COMMAND_CHANNEL, TEST_BOT_COMMAND_CHANNEL, \
    PROD_MISSION_CHANNEL, TEST_MISSION_CHANNEL


def test_production_values():
    config = get_constant(True)

    assert config['MISSION_START'] is PROD_FLAIR_MISSION_START
    assert config['MISSION_STOP'] is PROD_FLAIR_MISSION_STOP

    # trade alerts channel ID
    assert config['TRADE_ALERTS_ID'] is PROD_TRADE_ALERTS_ID
    assert config['SUB_REDDIT'] is PROD_SUB_REDDIT
    assert config['CHANNEL_UPVOTES'] is PROD_CHANNEL_UPVOTES
    assert config['MISSION_CHANNEL'] is PROD_MISSION_CHANNEL
    assert config['BOT_COMMAND_CHANNEL'] is PROD_BOT_COMMAND_CHANNEL


def test_testing_server_values():
    config = get_constant(False)

    assert config['MISSION_START'] is TEST_FLAIR_MISSION_START
    assert config['MISSION_STOP'] is TEST_FLAIR_MISSION_STOP

    # trade alerts channel ID
    assert config['TRADE_ALERTS_ID'] is TEST_TRADE_ALERTS_ID
    assert config['SUB_REDDIT'] is TEST_SUB_REDDIT
    assert config['CHANNEL_UPVOTES'] is TEST_CHANNEL_UPVOTES
    assert config['MISSION_CHANNEL'] is TEST_MISSION_CHANNEL
    assert config['BOT_COMMAND_CHANNEL'] is TEST_BOT_COMMAND_CHANNEL
