"""
MissionEditor.py

Function for editing an active mission.

Dependencies: constants, database, ImageHandling, TextGen, MissionGenerator
"""
# import libraries
import aiohttp
import asyncio
import typing

# import discord.py
import discord
from discord import Webhook
from discord.ui import View, Modal

# import local constants
import ptn.missionalertbot.constants as constants
from ptn.missionalertbot.constants import bot, bot_spam_channel, get_reddit, upvote_emoji, wineloader_role, hauler_role

# import local modules
from ptn.missionalertbot.database.database import _update_mission_in_database
from ptn.missionalertbot.modules.ImageHandling import create_carrier_reddit_mission_image, create_carrier_discord_mission_image
from ptn.missionalertbot.modules.MissionGenerator import validate_pads, validate_profit, define_commodity, return_discord_alert_embed, return_discord_channel_embeds, \
    _mission_summary_embed, mission_generation_complete, cleanup_temp_image_file
from ptn.missionalertbot.modules.TextGen import txt_create_discord, txt_create_reddit_title, txt_create_reddit_body


class EditConfirmView(View):
    def __init__(self, mission_params, original_type, confirm_embed, author: typing.Union[discord.Member, discord.User], timeout=300):
        self.spamchannel = bot.get_channel(bot_spam_channel())
        self.confirm_embed = confirm_embed
        self.author = author
        self.original_type = original_type
        self.mission_params = mission_params
        super().__init__(timeout=timeout)

    @discord.ui.button(label="Confirm", style=discord.ButtonStyle.success, emoji="📢", custom_id="confirm")
    async def confirm_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        button.disabled=True
        print(f"{interaction.user.display_name} confirms mission update")

        try: # there's probably a better way to do this using an if statement
            self.clear_items()
            edit_embed = discord.Embed(
                description=f"Editing active mission for {self.mission_params.carrier_data.carrier_long_name}.",
                color=constants.EMBED_COLOUR_QU
            )
            self.mission_params.edit_embed = edit_embed
            await interaction.response.edit_message(embed=edit_embed, view=None)
        except Exception as e:
            print(e)

        await edit_discord_alerts(interaction, self.mission_params, self.spamchannel, self.original_type)
        await update_webhooks(interaction, self.mission_params, self.spamchannel, self.original_type)
        await update_reddit_post(interaction, self.mission_params, self.spamchannel)
        await update_mission_db(interaction, self.mission_params, self.spamchannel)

        try:
            print("Calling cleanup for temp files")
            cleanup_temp_image_file(self.mission_params.discord_img_name)
            cleanup_temp_image_file(self.mission_params.reddit_img_name)
        except Exception as e:
            print(e)

        await mission_generation_complete(interaction, self.mission_params)

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.danger, emoji="✖", custom_id="cancel")
    async def cancel_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        button.disabled=True

        cancelled_embed = discord.Embed(
            description="Mission update cancelled by user.",
            color=constants.EMBED_COLOUR_ERROR
        )
        self.mission_params.edit_embed = cancelled_embed

        try:
            self.clear_items()
            await interaction.response.edit_message(embed=cancelled_embed, view=None) # mission gen ends here
        except Exception as e:
            print(e)

    @discord.ui.button(label="Set Message", style=discord.ButtonStyle.secondary, emoji="✍", custom_id="message", row=2)
    async def message_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        print(f"{interaction.user.display_name} wants to add a message to their mission")
    
        await interaction.response.send_modal(AddMessageModal(self.mission_params, self.confirm_embed, view=self))

    @discord.ui.button(label="Remove Message", style=discord.ButtonStyle.secondary, emoji="🗑", custom_id="remove", row=2)
    async def remove_message_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        print(f"{interaction.user.display_name} wants to remopve their existing mission message")
        button.disabled=True
        print("Define empty embeds list")
        embeds = []
        print(embeds)
        try:
            embeds.append(self.confirm_embed)
        except Exception as e:
            print(e)

        try:
            if self.mission_params.cco_message_text:
                print(f"Message found: {self.mission_params.cco_message_text}")
                embed = discord.Embed(
                    title="Message will be removed:",
                    description=self.mission_params.cco_message_text,
                    color=constants.EMBED_COLOUR_RP
                )
                print("Defining new feedback embeds")

                embeds.append(embed)
                await interaction.response.edit_message(embeds=embeds)
                print("Set mission message to none")
                self.mission_params.cco_message_text = None

            else:
                print("No message found to remove")
                embed = discord.Embed(
                    description="No mission message found.",
                    color=constants.EMBED_COLOUR_ERROR
                )

                embeds.append(embed)
                await interaction.response.edit_message(embeds=embeds)

        except Exception as e:
            print(e)

    async def interaction_check(self, interaction: discord.Interaction): # only allow original command user to interact with buttons
        if interaction.user.id == self.author.id:
            return True
        else:
            embed = discord.Embed(
                description="Only the command author may use these interactions.",
                color=constants.EMBED_COLOUR_ERROR
            )
            embed.set_image(url='https://media1.tenor.com/images/939e397bf929b9768b24a8fa165301fe/tenor.gif?itemid=26077542')
            embed.set_footer(text="Seriously, are you 4? 🙄")
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return False

    async def on_timeout(self):
        print("Mission edit view timed out")
        # return a message to the user that the interaction has timed out
        timeout_embed = discord.Embed(
            description="Timed out.",
            color=constants.EMBED_COLOUR_ERROR
        )

        # remove buttons
        self.clear_items()

        if not self.mission_params.edit_embed:
            embed = timeout_embed
        else:
            embed = self.mission_params.edit_embed
        try:
            await self.message.edit(embed=embed, view=self) # mission gen ends here
        except Exception as e:
            print(e)


# modal for message button
class AddMessageModal(Modal):
    def __init__(self, mission_params, confirm_embed, view, title = 'Add message to mission', timeout = None) -> None:
        self.confirm_embed = confirm_embed
        self.mission_params = mission_params
        self.view = view
        super().__init__(title=title, timeout=timeout)

    message = discord.ui.TextInput(
        label='Enter your message below.',
        style=discord.TextStyle.long,
        placeholder='Normal Discord markdown works, but mentions and custom emojis require full code.',
        required=True,
        max_length=4000,
    )

    async def on_submit(self, interaction: discord.Interaction):
        print("Message submitted")
        print(self.message.value)
        self.mission_params.cco_message_text = self.message.value
        """
        While self.message returns the inputted text if printed, it is actually a class holding
        all the attributes of the TextInput. View shows only the text the user inputted.

        This is important because it is a weak instance and cannot be pickled with mission_params,
        and we only want the value pickled anyway
        """
        print(self.mission_params.cco_message_text)
        message_embed = discord.Embed(
            title="Message added",
            description=self.mission_params.cco_message_text,
            color=constants.EMBED_COLOUR_RP
        )

        embeds = []
        embeds.append(self.confirm_embed)
        embeds.append(message_embed)

        try:
            await interaction.response.edit_message(embeds=embeds, view=self.view)

        except Exception as e:
            print(e)


async def edit_active_mission(interaction: discord.Interaction, mission_params, original_commodity, original_type):
    print("Called edit_active_mission")
    mission_params.returnflag = True

    # validate profit
    print("Validating profit")
    await validate_profit(interaction, mission_params)

    # validate pads
    print("Validating pad size")
    await validate_pads(interaction, mission_params)

    # find commodity
    print("Finding commodity")
    await define_commodity(interaction, mission_params)

    print(original_commodity, mission_params.commodity_name)
    if original_commodity != mission_params.commodity_name:
        if original_commodity == 'Wine': await commodity_wine_error(interaction, mission_params)
        elif mission_params.commodity_name == 'Wine': await commodity_wine_error(interaction, mission_params)
        else:
            print("Not wine, not problem 👍")

    if not mission_params.returnflag:
        embed = discord.Embed(
            description="Mission edit could not continue.",
            color=constants.EMBED_COLOUR_ERROR
        )
        mission_params.edit_embed = embed
        await interaction.response.send_message(embed=embed)
        return

    confirm_embed = discord.Embed(
        title=f"{mission_params.mission_type.upper()}ING: {mission_params.carrier_data.carrier_long_name}",
        description=f"Please confirm updated mission details for {mission_params.carrier_data.carrier_long_name}.",
        color=constants.EMBED_COLOUR_QU
    )
    thumb_url = constants.ICON_FC_LOADING if mission_params.mission_type == 'load' else constants.ICON_FC_UNLOADING
    confirm_embed.set_thumbnail(url=thumb_url)

    confirm_embed = _mission_summary_embed(mission_params, confirm_embed)

    mission_params.edit_embed = None

    view = EditConfirmView(mission_params, original_type, confirm_embed, interaction.user) # confirm/cancel buttons

    await interaction.response.send_message(embed=confirm_embed, view=view)

    view.message = await interaction.original_response()

    # TODO: insert confirmation summary dialog with buttons

    # no errors from checks, proceed
    # TODO: requires and returns for below funcs



async def edit_discord_alerts(interaction: discord.Interaction, mission_params, spamchannel, original_type):
    print("Updating Discord alert...")

    async with interaction.channel.typing():
        try:
            # find alerts channel
            if mission_params.commodity_name.title() == "Wine":
                if mission_params.mission_type == 'load':
                    alerts_channel = bot.get_channel(mission_params.channel_defs.wine_loading_channel_actual)
                else:   # unloading block
                    alerts_channel = bot.get_channel(mission_params.channel_defs.wine_unloading_channel_actual)
            else:
                alerts_channel = bot.get_channel(mission_params.channel_defs.alerts_channel_actual)

            print(alerts_channel)
            print(mission_params.discord_alert_id)

            # get message object from trade alerts
            print("Fetch alerts message from Discord by ID")
            discord_alert_msg = await alerts_channel.fetch_message(mission_params.discord_alert_id)

            # get new trade alert message
            print("Create new alert text and embed")
            mission_params.discord_text = txt_create_discord(mission_params)
            embed = await return_discord_alert_embed(interaction, mission_params)

            # edit in new trade alert message
            try:
                print("Edit alert message")
                await discord_alert_msg.edit(embed=embed)
            except Exception as e:
                print(e)
                embed=discord.Embed(description=f"Error editing discord alert: {e}", color=constants.EMBED_COLOUR_ERROR)
                await spamchannel.send(embed=embed)

            print("Updating Discord channel embeds...")
            # get message object from carrier channel
            carrier_channel = bot.get_channel(mission_params.mission_temp_channel_id)
            discord_channel_msg = await carrier_channel.fetch_message(mission_params.discord_msg_id)
            if mission_params.notify_msg_id:
                discord_notify_msg = await carrier_channel.fetch_message(mission_params.notify_msg_id)

            # get new channel embeds from Mission Generator
            print("Get new channel embeds from Mission Generator")
            discord_embeds = await return_discord_channel_embeds(mission_params) # this function saves embeds to mission_params too

            send_embeds = [discord_embeds.buy_embed, discord_embeds.sell_embed, discord_embeds.info_embed, discord_embeds.help_embed]

            print("Checking for cco_message_text status...")
            if mission_params.cco_message_text is not None: send_embeds.append(discord_embeds.owner_text_embed)

            if mission_params.notify_msg_id:
                ping_role_id = wineloader_role() if mission_params.commodity_name == 'Wine' else hauler_role()
                await discord_notify_msg.edit(content=f"<@&{ping_role_id}>: {mission_params.discord_text}")

            print("Checking mission_type status...")
            if original_type != mission_params.mission_type:
                try:
                    print(f"Type changed to {mission_params.mission_type} (from {original_type}), creating new image")
                    mission_params.discord_img_name = await create_carrier_discord_mission_image(mission_params)

                    file = discord.File(mission_params.discord_img_name, filename="image.png")
                    print(file)

                    print("Uploading new image...")
                    # await discord_channel_msg.add_files(file)

                    print("Editing Discord channel message...")
                    await discord_channel_msg.edit(content=mission_params.discord_msg_content, embeds=send_embeds, attachments=[file])

                except Exception as e:
                    print(e)

            else:
                print("Editing Discord channel message...")
                await discord_channel_msg.edit(content=mission_params.discord_msg_content, embeds=send_embeds)

        except Exception as e:
            print(e)

        try:
            updated_message = await discord_channel_msg.edit(embeds=send_embeds)
            print("Feeding back to user...")
            embed = discord.Embed(
                title=f"Discord trade alerts updated for {mission_params.carrier_data.carrier_long_name}",
                description=f"Check <#{alerts_channel.id}> for trade alert and "
                            f"<#{mission_params.mission_temp_channel_id}> for image.",
                color=constants.EMBED_COLOUR_DISCORD
            )
            embed.set_thumbnail(url=constants.ICON_DISCORD_CIRCLE)
            await interaction.channel.send(embed=embed)
        except Exception as e:
            print(e)
            embed=discord.Embed(description=f"Error editing discord channel message: {e}", color=constants.EMBED_COLOUR_ERROR)
            await spamchannel.send(embed=embed)


async def update_webhooks(interaction: discord.Interaction, mission_params, spamchannel, original_type):
    print("Updating webhooks...")
    async with interaction.channel.typing():
        if mission_params.webhook_urls and mission_params.webhook_msg_ids and mission_params.webhook_jump_urls:

            print("Defining Discord embeds...")
            discord_embeds = mission_params.discord_embeds
            webhook_embeds = [discord_embeds.buy_embed, discord_embeds.sell_embed, discord_embeds.webhook_info_embed]

            if mission_params.cco_message_text: webhook_embeds.append(discord_embeds.owner_text_embed)

            for webhook_name, webhook_url, webhook_msg_id, webhook_jump_url in zip(mission_params.webhook_names, mission_params.webhook_urls, mission_params.webhook_msg_ids, mission_params.webhook_jump_urls):
                try: 
                    async with aiohttp.ClientSession() as session:
                        print(f"Fetching webhook for {webhook_url} with jumpurl {webhook_jump_url} and ID {webhook_msg_id}")
                        webhook = Webhook.from_url(webhook_url, session=session, client=bot)
                        print("Fetching webhook message object")
                        webhook_msg = await webhook.fetch_message(webhook_msg_id)

                        if original_type != mission_params.mission_type:
                            # type has changed, need to change image too
                            try:
                                print(f"Type changed to {mission_params.mission_type} (from {original_type}), creating new image")
                                mission_params.discord_img_name = await create_carrier_discord_mission_image(mission_params)

                                file = discord.File(mission_params.discord_img_name, filename="image.png")
                                print(file)

                                print("Uploading new image...")
                                # await discord_channel_msg.add_files(file)

                                print("Editing Discord channel message...")
                                await webhook_msg.edit(embeds=webhook_embeds, attachments=[file])
                            
                            except Exception as e:
                                print(e)

                        else:
                            # don't need to change image
                            print("Editing webhook message...")
                            await webhook_msg.edit(embeds=webhook_embeds)

                        print("Feeding back to user...")
                        embed = discord.Embed(
                            title=f"Webhook alert updated for {mission_params.carrier_data.carrier_long_name}",
                            description=f"Sent to your webhook **{webhook_name}**: {webhook_jump_url}",
                            color=constants.EMBED_COLOUR_DISCORD
                        )
                        embed.set_thumbnail(url=constants.ICON_WEBHOOK_PTN)
                        await interaction.channel.send(embed=embed)

                except Exception as e:
                    print(f"Failed updating webhook message {webhook_jump_url} with URL {webhook_url}: {e}")
                    embed=discord.Embed(description=f"Failed updating webhook message {webhook_jump_url} with URL {webhook_url}: {e}", color=constants.EMBED_COLOUR_ERROR)
                    await spamchannel.send(embed=embed)


async def update_reddit_post(interaction: discord.Interaction, mission_params, spamchannel):
    print("Updating Reddit post")
    async with interaction.channel.typing():
        if not mission_params.reddit_post_id:
            return

        print("Generating new Reddit texts and image...")
        mission_params.reddit_title = txt_create_reddit_title(mission_params)
        mission_params.reddit_body = txt_create_reddit_body(mission_params)
        mission_params.reddit_img_name = await create_carrier_reddit_mission_image(mission_params)

        original_reddit_post_id = mission_params.reddit_post_id
        print(original_reddit_post_id)

        try:
            # post to reddit
            print("Sending new Reddit post")
            reddit = await get_reddit()
            subreddit = await reddit.subreddit(mission_params.channel_defs.sub_reddit_actual)
            submission = await subreddit.submit_image(mission_params.reddit_title, image_path=mission_params.reddit_img_name,
                                                    flair_id=mission_params.channel_defs.reddit_flair_in_progress)
            # save new mission_params
            print(f"Original post ID: {original_reddit_post_id}")

            mission_params.reddit_post_url = submission.permalink
            mission_params.reddit_post_id = submission.id
            print(f"New post ID: {mission_params.reddit_post_id}")

            if mission_params.cco_message_text:
                comment = await submission.reply(f"> {mission_params.cco_message_text}\n\n&#x200B;\n\n{mission_params.reddit_body}")
            else:
                comment = await submission.reply(mission_params.reddit_body)

            # save new params
            mission_params.reddit_comment_url = comment.permalink
            mission_params.reddit_comment_id = comment.id
            print(f"New comment ID: {mission_params.reddit_comment_id}")

            # feed back to user
            embed = discord.Embed(
                title=f"Reddit trade alert sent for {mission_params.carrier_data.carrier_long_name}",
                description=f"https://www.reddit.com{mission_params.reddit_post_url}",
                color=constants.EMBED_COLOUR_REDDIT)
            embed.set_thumbnail(url=constants.ICON_REDDIT)
            await interaction.channel.send(embed=embed)
            embed = discord.Embed(title=f"{mission_params.carrier_data.carrier_long_name} REQUIRES YOUR UPDOOTS",
                                description=f"https://www.reddit.com{mission_params.reddit_post_url}",
                                color=constants.EMBED_COLOUR_REDDIT)
            channel = bot.get_channel(mission_params.channel_defs.upvotes_channel_actual)
            upvote_message = await channel.send(embed=embed)
            emoji = bot.get_emoji(upvote_emoji())
            await upvote_message.add_reaction(emoji)

        except Exception as e:
            print(f"Error posting to Reddit: {e}")
            reddit_error_embed = discord.Embed(
                description=f"❌ Could not send to Reddit. {e}",
                color=constants.EMBED_COLOUR_ERROR
            )
            reddit_error_embed.set_footer(text="Attempting to continue with updates.")
            await interaction.channel.send(embed=reddit_error_embed)
            embed=discord.Embed(description=f"Error sending updated Reddit post: {e}", color=constants.EMBED_COLOUR_ERROR)
            await spamchannel.send(embed=embed)

        # now update the original post
        try:
            print("Updating old Reddit post")
            print(original_reddit_post_id)
            reddit_edit_text = f"**MISSION UPDATED**\n\nNew mission details [here]({mission_params.reddit_post_url})."
            original_post = await reddit.submission(original_reddit_post_id)
            print("Sending comment reply")
            await original_post.reply(reddit_edit_text)
            # mark original post as spoiler, change its flair
            print("Marking spoiler and setting flair")
            await original_post.flair.select(mission_params.channel_defs.reddit_flair_completed)
            await original_post.mod.spoiler()
        except Exception as e:
            embed=discord.Embed(description=f"❌ Couldn't send comment to original Reddit post: {e}", color=constants.EMBED_COLOUR_ERROR)
            embed.set_footer(text="Attempting to continue with updates.")
            await interaction.channel.send(embed=embed)
            embed=discord.Embed(description=f"Error sending comment to old Reddit post on mission update: {e}", color=constants.EMBED_COLOUR_ERROR)
            await spamchannel.send(embed=embed)


async def update_mission_db(interaction: discord.Interaction, mission_params, spamchannel):
    print("Attemping to update database")
    async with interaction.channel.typing():
        try:
            await _update_mission_in_database(mission_params)
        except Exception as e:
            embed=discord.Embed(description=f"Error updating mission database: {e}", color=constants.EMBED_COLOUR_ERROR)
            await spamchannel.send(embed=embed)
            await interaction.channel.send(embed=embed)


async def commodity_wine_error(interaction: discord.Interaction, mission_params):
    print("user tried to change commodity to or from wine")
    embed = discord.Embed(
        description="❌ Sorry, you cannot change commodity to or from Wine.",
        color=constants.EMBED_COLOUR_ERROR
    )
    mission_params.returnflag = False
    return await interaction.channel.send(embed=embed)