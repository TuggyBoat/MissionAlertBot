Before deployment:
- update env file to new token names MAB_BOT_DISCORD_TOKEN_PROD and MAB_BOT_DISCORD_TOKEN_TESTING
- update service .conf to new variable name PTN_MAB_BOT_PRODUCTION (`sudo vim /etc/systemd/system/missionalertbot.service.d/override.conf`)