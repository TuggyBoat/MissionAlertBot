"""
Various functions relating to image manipulation.

Dependencies: constants, database, DateString
"""

# import libraries
import asyncio
import os
from PIL import Image, ImageFont, ImageDraw
import random
import shutil
import tempfile

# import discord.py
import discord

# import local constants
import ptn.missionalertbot.constants as constants
from ptn.missionalertbot.constants import bot, REG_FONT, NAME_FONT, TITLE_FONT, NORMAL_FONT, FIELD_FONT

# import local modules
from ptn.missionalertbot.modules.DateString import get_formatted_date_string
from ptn.missionalertbot.database.database import find_carrier, CarrierDbFields


# function to overlay carrier image with background template
async def _overlay_mission_image(carrier_data):
    print("Called mission image overlay function")
    """
    template:       the background image with logo, frame elements etc
    carrier_image:  the inset image optionally created by the Carrier Owner
    """
    template = Image.open(os.path.join(constants.RESOURCE_PATH, "template.png"))
    carrier_image_filename = carrier_data.carrier_short_name + '.png'
    carrier_image = Image.open(os.path.join(constants.IMAGE_PATH, carrier_image_filename))
    template.paste(carrier_image, (47,13))
    return template


# function to create image for loading
async def create_carrier_mission_image(carrier_data, commodity, system, station, profit, pads, demand, mission_type):
    print("Called mission image generator")
    """
    Builds the carrier image and returns the relative path.
    """

    template = await _overlay_mission_image(carrier_data)

    image_editable = ImageDraw.Draw(template)

    mission_action = 'LOADING' if mission_type == 'load' else 'UNLOADING'
    image_editable.text((46, 304), "PILOTS TRADE NETWORK", (255, 255, 255), font=TITLE_FONT)
    image_editable.text((46, 327), f"CARRIER {mission_action} MISSION", (191, 53, 57), font=TITLE_FONT)
    image_editable.text((46, 366), "FLEET CARRIER " + carrier_data.carrier_identifier, (0, 217, 255), font=REG_FONT)
    image_editable.text((46, 382), carrier_data.carrier_long_name, (0, 217, 255), font=NAME_FONT)
    image_editable.text((46, 439), "COMMODITY:", (255, 255, 255), font=FIELD_FONT)
    image_editable.text((170, 439), commodity.name.upper(), (255, 255, 255), font=NORMAL_FONT)
    image_editable.text((46, 477), "SYSTEM:", (255, 255, 255), font=FIELD_FONT)
    image_editable.text((170, 477), system.upper(), (255, 255, 255), font=NORMAL_FONT)
    image_editable.text((46, 514), "STATION:", (255, 255, 255), font=FIELD_FONT)
    image_editable.text((170, 514), f"{station.upper()} ({pads.upper()} pads)", (255, 255, 255), font=NORMAL_FONT)
    image_editable.text((46, 552), "PROFIT:", (255, 255, 255), font=FIELD_FONT)
    image_editable.text((170, 552), f"{profit}k per unit, {demand} units", (255, 255, 255), font=NORMAL_FONT)

    # Check if this will work fine, we might need to delete=False and clean it ourselves
    result_name = tempfile.NamedTemporaryFile(suffix='.png', delete=False)
    print(f'Saving temporary mission file for carrier: {carrier_data.carrier_long_name} to: {result_name.name}')
    template.save(result_name.name)
    return result_name.name


# used by mission generator
def cleanup_temp_image_file(file_name):
    """
    Takes an input file path and removes it.

    :param str file_name: The file path
    :returns: None
    """
    try:
        print(f'Deleting the temp file at: {file_name}')
        os.remove(file_name)
    except Exception as e:
        print(f'There was a problem removing the temp image file located {file_name}')
        print(e)


# function to assign or change a carrier image file
async def assign_carrier_image(ctx, lookname):
    print('assign_carrier_image called')
    carrier_data = find_carrier(lookname, CarrierDbFields.longname.name)

    # check carrier exists
    if not carrier_data:
        await ctx.send(f"Sorry, no carrier found matching \"{lookname}\". Try using `/find` or `/owner`.")
        return print(f"No carrier found for {lookname}")

    # define image requiremenets
    true_size = (506, 285)
    true_width, true_height = true_size
    true_aspect = true_width / true_height
    legacy_message, noimage_message = False, False

    newimage_description = ("The mission image helps give your Fleet Carrier trade missions a distinct visual identity. "
                            " You only need to upload an image once. This will be inserted into the slot in the "
                            "mission image template.\n\n"
                            "• It is recommended to use in-game screenshots showing **scenery** and/or "
                            "**your Fleet Carrier**. You may also wish to add a **logo** or **emblem** for your Fleet "
                            "Carrier if you have one.\n"
                            "• Images will be cropped to 16:9 and resized to 506x285 if not already.\n"
                            "• You can use `m.carrier_image <yourcarrier>` at any time to change your image.\n\n"
                            "**You can upload your image now to change it**.\n"
                            "Alternatively, input \"**x**\" to cancel, or \"**p**\" to use a random placeholder with PTN logo.\n\n"
                            "**You must have a valid image to generate a mission**.")

    # see if there's an image for this carrier already
    # newly added carriers have no image (by intention - we want CCOs to engage with this aspect of the job!)

    # define the path to the carrier image
    image_name = carrier_data.carrier_short_name + '.png'
    print(f"image name defined as {image_name}")
    image_path = os.path.join(constants.IMAGE_PATH, image_name)

    # define backup path
    backup_image_name = carrier_data.carrier_short_name + '.' + get_formatted_date_string()[1] + '.png'
    print(f"backup image name defined as {backup_image_name}")
    backup_path = os.path.join(constants.IMAGE_PATH, 'old', backup_image_name)

    try:
        print(f"Looking for existing image at {image_path}")
        file = discord.File(image_path, filename="image.png")
    except:
        file = None

    if file:
        # we found an existing image, so show it to the user
        print("Found image")
        embed = discord.Embed(title=f"{carrier_data.carrier_long_name} MISSION IMAGE",
                                color=constants.EMBED_COLOUR_QU)
        embed.set_image(url="attachment://image.png")
        await ctx.send(file=file, embed=embed)
        image_exists = True



        # check if it's a legacy image - if it is, we want them to replace it
        print(f'opening {image_path} to check if it\'s a valid image')
        image = Image.open(image_path)
        valid_image = image.size == true_size

    else:
        # no image found
        print("No existing image found")
        image_exists, valid_image = False, False

    if valid_image:
        # an image exists and is the right size, user is not nagged to change it
        embed = discord.Embed(title="Change carrier's mission image?",
                                    description="If you want to replace this image you can upload the new image now. "
                                                "Images will be automatically cropped to 16:9 and resized to 506x285.\n\n"
                                                "**To continue without changing**:         Input \"**x**\" or wait 60 seconds\n"
                                                "**To switch to a random PTN logo image**: Input \"**p**\"",
                                    color=constants.EMBED_COLOUR_QU)

    elif not valid_image and not image_exists:
        # there's no mission image, prompt the user to upload one or use a PTN placeholder
        file = discord.File(os.path.join(constants.RESOURCE_PATH, "template.png"), filename="image.png")
        embed = discord.Embed(title=f"NO MISSION IMAGE FOUND",
                                color=constants.EMBED_COLOUR_QU)
        embed.set_image(url="attachment://image.png")
        noimage_message = await ctx.send(file=file, embed=embed)
        embed = discord.Embed(title="Upload a mission image",
                            description=newimage_description, color=constants.EMBED_COLOUR_QU)

    elif not valid_image and image_exists:
        # there's an image but it's outdated, prompt them to change it
        embed = discord.Embed(title="WARNING: LEGACY MISSION IMAGE DETECTED",
                            description="The mission image format has changed. You must upload a new image to continue"
                                                " to use the Mission Generator.",
                                        color=constants.EMBED_COLOUR_ERROR)
        legacy_message = await ctx.send(embed=embed)
        embed = discord.Embed(title="Upload a mission image",
                            description=newimage_description, color=constants.EMBED_COLOUR_QU)

    # send the embed we created
    message_upload_now = await ctx.send(embed=embed)

    # function to check user's response
    def check(message_to_check):
        return message_to_check.author == ctx.author and message_to_check.channel == ctx.channel

    try:
        # now we process the user's response
        message = await bot.wait_for("message", check=check, timeout=60)
        if message.content.lower() == "x": # user backed out without making changes
            embed = discord.Embed(description="No changes made.",
                                    color=constants.EMBED_COLOUR_OK)
            await ctx.send(embed=embed)
            await message.delete()
            await message_upload_now.delete()
            if noimage_message:
                await noimage_message.delete()
            return

        elif message.content.lower() == "p": # user wants to use a placeholder image
            print("User wants default image")
            try:
                # first backup any existing image
                shutil.move(image_path, backup_path)
            except:
                pass
            try:
                # select a random image from our default image library so not every carrier is the same
                default_img = random.choice(os.listdir(constants.DEF_IMAGE_PATH))
                shutil.copy(os.path.join(constants.DEF_IMAGE_PATH, default_img), image_path)
            except Exception as e:
                print(e)

        elif message.attachments: # user has uploaded something, let's hope it's an image :))
            # first backup any existing image
            try:
                shutil.move(image_path, backup_path)
            except:
                pass
            # now process our attachment
            for attachment in message.attachments:
                # there can only be one attachment per message
                await attachment.save(attachment.filename)

                """
                Now we need to check the image's size and aspect ratio so we can trim it down without the user
                requiring any image editing skills. This is a bit involved. We need to compare both aspect
                ratio and size to our desired values and fix them in that order. Aspect correction requires
                figuring out whether the image is too tall or too wide, then centering the crop correctly.
                Size correction takes place after aspect correction and is super simple.
                """

                print("Checking image size")
                try:
                    image = Image.open(attachment.filename)
                except Exception as e: # they uploaded something daft
                    print(e)
                    await ctx.send("Sorry, I don't recognise that as an image file. Upload aborted.")
                    return await message_upload_now.delete()

                # now we check the image dimensions and aspect ratio
                upload_width, upload_height = image.size
                print(f"{upload_width}, {upload_height}")
                upload_size = (upload_width, upload_height)
                upload_aspect = upload_width / upload_height

                if not upload_aspect == true_aspect:
                    print(f"Image aspect ratio of {upload_aspect} requires adjustment")
                    # check largest dimension
                    if upload_aspect > true_aspect:
                        print("Image is too wide")
                        # image is too wide, we'll crop width to maintain height
                        new_width = upload_height * true_aspect
                        new_height = upload_height
                    else:
                        print("Image is too high")
                        # image is too high, we'll crop height to maintain width
                        new_height = upload_width / true_aspect
                        new_width = upload_width
                    # now perform the incision. Nurse: scalpel!
                    crop_width = upload_width - new_width
                    crop_height = upload_height - new_height
                    left = 0.5 * crop_width
                    top = 0.5 * crop_height
                    right = 0.5 * crop_width + new_width
                    bottom = 0.5 * crop_height + new_height
                    print(left, top, right, bottom)
                    image = image.crop((left, top, right, bottom))
                    print(f"Cropped image to {new_width} x {new_height}")
                    upload_size = (new_width, new_height)
                # now check its size
                if not upload_size == true_size:
                    print("Image requires resizing")
                    image = image.resize((true_size))

            # now we can save the image
            image.save(image_path)

            # remove the downloaded attachment
            try:
                image.close()
                os.remove(attachment.filename)
            except Exception as e:
                print(f"Error deleting file {attachment.filename}: {e}")

        # now we can show the user the result in situ
        in_image = await _overlay_mission_image(carrier_data)
        result_name = tempfile.NamedTemporaryFile(suffix='.png', delete=False)
        print(f'Saving temporary mission image preview file for carrier: {carrier_data.carrier_long_name} to: {result_name.name}')
        in_image.save(result_name.name)

        file = discord.File(result_name.name, filename="image.png")
        embed = discord.Embed(title=f"{carrier_data.carrier_long_name}",
                                description="Mission image updated.", color=constants.EMBED_COLOUR_OK)
        embed.set_image(url="attachment://image.png")
        await ctx.send(file=file, embed=embed)
        print("Sent result to user")
        await message.delete()
        await message_upload_now.delete()
        if noimage_message:
            await noimage_message.delete()
        # only delete legacy warning if user uploaded valid new file
        if legacy_message:
            await legacy_message.delete()
        print("Tidied up our prompt messages")

        # cleanup the tempfile
        result_name.close()
        os.unlink(result_name.name)
        print("Removed the tempfile")

        print(f"{ctx.author} updated carrier image for {carrier_data.carrier_long_name}")

    except asyncio.TimeoutError:
        embed = discord.Embed(description="No changes made (no response from user).",
                                color=constants.EMBED_COLOUR_OK)
        await ctx.send(embed=embed)
        await message_upload_now.delete()
        return