import discord
from discord.ext import commands, tasks
import asyncpraw
import ptn.missionalertbot.constants as constants

conf = constants.get_constant(_production)

flair_mission_start = conf['MISSION_START']
flair_mission_stop = conf['MISSION_STOP']

# channel IDs
trade_alerts_id = conf['TRADE_ALERTS_ID']
wine_alerts_loading_id = conf['WINE_ALERTS_LOADING_ID']
wine_alerts_unloading_id = conf['WINE_ALERTS_UNLOADING_ID']

bot_spam_id = conf['BOT_SPAM_CHANNEL']
to_subreddit = conf['SUB_REDDIT']
cc_cat_id = conf['CC_CAT']
trade_cat_id = conf['TRADE_CAT']
archive_cat_id = conf['ARCHIVE_CAT']

# role IDs
hauler_role_id = conf['HAULER_ROLE']
cc_role_id = conf['CC_ROLE']
cteam_role_id = conf['CTEAM_ROLE']
certcarrier_role_id = conf['CERTCARRIER_ROLE']
rescarrier_role_id = conf['RESCARRIER_ROLE']

# emoji IDs
upvote_emoji = conf['UPVOTE_EMOJI']

# channel removal timers
seconds_short = conf['SECONDS_SHORT']
seconds_long = conf['SECONDS_LONG']


# create reddit instance
reddit = asyncpraw.Reddit('bot1')



# monitor reddit comments
async def _monitor_reddit_comments():
    print("Reddit monitor started")
    while True:
        try:
            # TODO: what happens if there's an error in this process, e.g. reddit is down?

            comment_channel = bot.get_channel(conf['REDDIT_CHANNEL'])
            # establish a comment stream to the subreddit using async praw
            subreddit = await reddit.subreddit(to_subreddit)
            async for comment in subreddit.stream.comments(skip_existing=True):
                print(f"New reddit comment: {comment}. Is_submitter is {comment.is_submitter}")
                # ignore comments from the bot / post author
                if not comment.is_submitter:
                    # log some data
                    print(f"{comment.author} wrote:\n {comment.body}\nAt: {comment.permalink}\nIn: {comment.submission}")

                    # get a submission object so we can interrogate it for the parent post title
                    submission = await reddit.submission(comment.submission)

                    # lookup the parent post ID with the mission database
                    mission_db.execute(f"SELECT * FROM missions WHERE "
                                    f"reddit_post_id = '{comment.submission}' ")
                    
                    print('DB command ran, go fetch the result')
                    mission_data = MissionData(mission_db.fetchone())

                    if not mission_data:
                        print("No match in mission DB, mission must be complete.")

                        embed = discord.Embed(title=f"{submission.title}",
                                            description=f"This mission is **COMPLETED**.\n\nComment by **{comment.author}**\n{comment.body}"
                                                        f"\n\nTo view this comment click here:\nhttps://www.reddit.com{comment.permalink}",
                                                        color=constants.EMBED_COLOUR_QU)
                    
                    elif mission_data:
                        # mission is active, we'll get info from the db and ping the CCO
                        print(f'Found mission data: {mission_data}')

                        # now we need to lookup the carrier data in the db
                        carrier_data = find_carrier(mission_data.carrier_name, CarrierDbFields.longname.name)
                        
                        # We can't easily moderate Reddit comments so we'll post it to a CCO-only channel
                        
                        await comment_channel.send(f"<@{carrier_data.ownerid}>, your Reddit trade post has received a new comment:")
                        embed = discord.Embed(title=f"{submission.title}",
                                            description=f"This mission is **IN PROGRESS**.\n\nComment by **{comment.author}**\n{comment.body}"
                                                        f"\n\nTo view this comment click here:\nhttps://www.reddit.com{comment.permalink}",
                                                        color=constants.EMBED_COLOUR_REDDIT)

                    await comment_channel.send(embed=embed)
                    print("Sent comment to channel")
        except Exception as e:
            print(f"Error while monitoring {to_subreddit} for comments: {e}")


# lasttrade task loop:
# Every 24 hours, check the timestamp of the last trade for all carriers and remove
# 'Certified Carrier' role from owner if there has been no trade for 28 days.
# If not already present, add 'Fleet Reserve' role to the owner.
@tasks.loop(hours=24)
async def lasttrade_cron():
    print(f"last trade cron running.")
    try:
        # get roles
        guild = bot.get_guild(bot_guild_id)
        cc_role = discord.utils.get(guild.roles, id=certcarrier_role_id)
        fr_role = discord.utils.get(guild.roles, id=rescarrier_role_id)
        # get spam channel
        spamchannel = bot.get_channel(bot_spam_id)
        # calculate epoch for 28 days ago
        now = datetime.now(tz=timezone.utc)
        lasttrade_max = now - timedelta(days=28)
        # get carriers who last traded >28 days ago
        # for owners with multiple carriers look at only the most recently used
        carrier_db.execute(f'''
                            SELECT p_ID,shortname,ownerid,max(lasttrade)
                            FROM carriers WHERE lasttrade < {int(lasttrade_max.timestamp())}
                            GROUP BY ownerid
                            ''')
        carriers = [CarrierData(carrier) for carrier in carrier_db.fetchall()]
        for carrier_data in carriers:
            # check roles on owners, remove/add as needed.
            last_traded = datetime.fromtimestamp(carrier_data.lasttrade).strftime('%Y-%m-%d %H:%M:%S')
            print(f"Processing carrier '{carrier_data.carrier_short_name}'. Last traded: {last_traded}")
            owner = guild.get_member(carrier_data.ownerid)
            if owner:
                if cc_role in owner.roles:
                    print(f"{owner.name} has the Certified Carrier role, removing.")
                    await owner.remove_roles(cc_role)
                    await spamchannel.send(f"{owner.name} has been removed from the Certified Carrier role due to inactivity.")
                    # notify by DM
                    owner_dm = await bot.fetch_user(carrier_data.ownerid)
                    await owner_dm.send(f"Ahoy CMDR! Your last PTN Fleet Carrier trade was more than 28 days ago at {last_traded} so you have been automatically marked as inactive and placed in the PTN Fleet Reserve. **You can visit <#939919613209223270> at any time to mark yourself as active and return to trading**. o7 CMDR!")
                    print(f"Notified {owner.name} by DM.")
                if fr_role not in owner.roles:
                    print(f"{owner.name} does not have the Fleet Reserve role, adding.")
                    await owner.add_roles(fr_role)
                    await spamchannel.send(f"{owner.name} has been added to the Fleet Reserve role.")
            else:
                print(f"Carrier owner id {carrier_data.ownerid} is invalid, skipping.")
                await spamchannel.send(f"Owner of {carrier_data.carrier_short_name} with ID {carrier_data.ownerid} is invalid. "
                                        "Cannot process lasttrade_cron for this carrier.")
        print("All carriers have been processed.")
    except Exception as e:
        print(f"last trade cron failed: {e}")
        pass